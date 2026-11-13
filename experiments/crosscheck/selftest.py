#!/usr/bin/env python3
"""selftest.py —— crosscheck.py 的断言式自检（dot 复核 6320351297 point 3）

逐个 fixture 运行 crosscheck.py，断言退出码与判定文本：
- 全部通过才 exit=0，否则 exit=1 并列出失败项。
- 断言里的预期值是作者在写 fixture 时声明的，不是独立测试通过；
  独立复跑由其他成员按 RUNS.md 记录（作者自报 ≠ 独立验证）。
- 输入错误用例断言 exit=1；并断言 stderr 里有命名字段的错误文本、
  全程无 Traceback（dot 复核 6321741221 point 2：异常崩溃同样可能
  返回 1，不能据此算校验成功）。
- 夹具防漂移：fixtures.manifest.json（脚本生成、不手抄）锁定全部
  fixture 的字节数＋SHA256，断言当前文件与锁定值一致；夹具被改动
  则 selftest 直接红（dot 2026-10-31 00:34 独立字节核对抓出作者手抄
  哈希 typo 的后续：锁定从帖子断言搬进代码）。
- 防漂移自身的健壮性（dot PR #21 6541300246，2026-10-31 04:45）：
  check_manifest() 对清单结构做类型检查（顶层对象／fixtures 对象／
  单条记录对象＋字段类型），文件读取异常也转成明确失败；任何结构
  问题都返回点名的「FAIL fixtures.manifest：…」，不抛异常、
  不带 Traceback。负例在断言 15–20 用临时目录进程内验证。

用法：python3 selftest.py [crosscheck.py 所在目录，默认本脚本同目录]
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(sys.argv[1]) if len(sys.argv) > 2 - 1 and len(sys.argv) > 1 else None
HERE = BASE or Path(__file__).resolve().parent
EXE = str(HERE / "crosscheck.py")

# (fixture, 预期退出码, 判定文本应包含, 说明, 预期 stderr 应包含的错误文本)
# 最后一个字段仅用于错误用例（exit=1）：断言命名字段的明确错误，
# 并与下面的 Traceback 检查配合，排除"崩溃也返回 1"的误判。
CASES = [
    ("claim_ok_two_roots.json", 0, "材料检查通过", "正路径：2 个支持根＋材料齐全", None),
    ("claim_agentpub.json", 4, "材料存疑", "无来源根、无明确支持 → 材料存疑", None),
    ("claim_punch.json", 2, "未核实", "只有 1 个支持根＋2 条未知出处，不足 ≥2 支持根", None),
    ("claim_museum.json", 4, "证据冲突", "支持根与反对根并存", None),
    ("claim_stance_all_contradict.json", 4, "材料存疑", "全反对，无支持", None),
    ("claim_stance_all_neutral.json", 4, "材料存疑", "全中立，无明确支持", None),
    ("claim_stance_illegal.json", 4, "材料存疑", "非法立场值", None),
    ("claim_stance_intraroot.json", 4, "材料存疑", "同根内立场矛盾", None),
    ("claim_refuted.json", 3, "被推翻", "证伪尝试已推翻结论", None),
    ("claim_bad_input.json", 1, None, "输入错误：sources 不是数组 → exit=1", "sources 字段必须是数组"),
    ("claim_contradicted_missing.json", 1, None, "输入错误：contradicted 缺失 → exit=1",
     "falsification.contradicted 必须显式声明"),
    ("claim_contradicted_null.json", 1, None, "输入错误：contradicted 为 null → exit=1",
     "falsification.contradicted 必须显式声明"),
    ("claim_contradicted_string.json", 1, None, "输入错误：contradicted 是字符串 → exit=1",
     "falsification.contradicted 必须显式声明"),
]

# (标签, manifest 文本（None=文件缺失）, detail 应包含的点名文本, 说明)
# 负例在临时目录进程内调用 check_manifest()：必须返回 (False, 点名文本)，
# 不能抛异常（dot 6541300246：结构问题不能靠 AttributeError 崩溃带过，
# 必须落到点名的 FAIL fixtures.manifest）。
MANIFEST_NEGATIVE = [
    ("top_array", "[]",
     "顶层必须是对象", "manifest 是合法 JSON 数组：.get() 会崩，须点名失败"),
    ("fixtures_not_object", '{"fixtures": ["x"]}',
     "fixtures 必须是对象", "fixtures 是数组：.items() 会崩，须点名失败"),
    ("fixtures_missing", '{}',
     "fixtures 必须是对象", "fixtures 键缺失：不能静默按空清单过，须点名失败"),
    ("record_not_object", '{"fixtures": {"a.json": "oops"}}',
     "记录必须是对象", "单条记录是字符串：want.get() 会崩，须点名失败"),
    ("record_field_type", '{"fixtures": {"a.json": {"bytes": "12", "sha256": 1}}}',
     "记录字段类型错误", "bytes 不是整数／sha256 不是字符串，须点名失败"),
    ("manifest_missing", None,
     "manifest 文件缺失", "manifest 文件不存在，须点名失败"),
    ("manifest_bad_json", "not json{{{",
     "manifest 解析失败", "manifest 不是合法 JSON，须点名失败"),
]


def run_one(fixture: str):
    p = subprocess.run(
        [sys.executable, EXE, str(HERE / fixture)],
        capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout + p.stderr


def main() -> int:
    failures = []
    for fixture, want_code, want_text, why, want_err in CASES:
        code, out = run_one(fixture)
        verdict_line = next((l for l in out.splitlines()
                             if l.startswith("**判定**")), "（无判定行）")
        ok = (code == want_code) and (want_text is None or want_text in verdict_line)
        detail = verdict_line
        if want_err is not None:
            # point 2：必须有命名字段的明确错误，且不能是 Traceback 崩溃
            if want_err not in out:
                ok = False
                detail = f"stderr 缺少预期错误文本「{want_err}」"
        if "Traceback (most recent call last)" in out:
            ok = False
            detail = "输出含 Traceback：崩溃导致的退出码不算校验成功"
        if not ok:
            failures.append((fixture, want_code, code, why))
            print(f"FAIL {fixture}：预期 exit={want_code}（{why}），实际 exit={code}；{detail}")
        else:
            print(f"PASS {fixture}：exit={code}（{why}）")
    # 夹具防漂移：manifest 由脚本生成，断言全部 fixture 字节与锁定值一致
    man_ok, man_detail = check_manifest()
    if man_ok:
        print(f"PASS fixtures.manifest：{man_detail}")
    else:
        failures.append(("fixtures.manifest", "-", "-", "夹具字节与锁定值不一致"))
        print(f"FAIL fixtures.manifest：{man_detail}")
    # 防漂移自身的负例：结构问题必须点名失败，不能抛异常
    for tag, text, want_phrase, why in MANIFEST_NEGATIVE:
        with tempfile.TemporaryDirectory(prefix="manneg_") as td:
            base = Path(td)
            if text is not None:
                (base / "fixtures.manifest.json").write_text(text, encoding="utf-8")
            try:
                ok, detail = check_manifest(base)
            except Exception as e:  # noqa: BLE001 —— 抛异常即失败
                failures.append((f"manifest 负例 {tag}", "-", "-", why))
                print(f"FAIL manifest 负例 {tag}：抛异常 {type(e).__name__}（{why}）；"
                      f"应返回点名失败，不抛异常")
                continue
            if (not ok) and want_phrase in detail:
                print(f"PASS manifest 负例 {tag}：{why} → {detail[:60]}")
            else:
                failures.append((f"manifest 负例 {tag}", "-", "-", why))
                print(f"FAIL manifest 负例 {tag}：{why}；应返回 ok=False 且 detail 含"
                      f"「{want_phrase}」，实际 ok={ok} detail={detail[:80]}")
    total = len(CASES) + 1 + len(MANIFEST_NEGATIVE)
    if failures:
        print(f"\n{len(failures)} 个断言失败，见上。")
        return 1
    print(f"\n全部 {total} 个断言通过（作者自跑；独立复跑见 RUNS.md）。")
    return 0


def check_manifest(base=None):
    """断言 experiments/crosscheck 下全部 claim_*.json 与
    fixtures.manifest.json 的锁定值（字节数＋SHA256）一致。

    base：清单与夹具所在目录，默认脚本同目录（断言 14）；
    负例（断言 15–20）传入临时目录做结构破坏测试。

    任何结构／类型／读取问题都返回 (False, 点名失败文本)，
    绝不抛异常：失败行统一由 main() 打成
    「FAIL fixtures.manifest：…」（dot PR #21 6541300246）。
    """
    base = HERE if base is None else Path(base)
    man_path = base / "fixtures.manifest.json"
    if not man_path.exists():
        return False, "manifest 文件缺失（fixtures.manifest.json）"
    try:
        man = json.loads(man_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 —— 读不出 manifest 本身就是失败
        return False, f"manifest 解析失败：{e}"
    if not isinstance(man, dict):
        return False, f"manifest 顶层必须是对象（得到 {type(man).__name__}）"
    locked = man.get("fixtures")
    if not isinstance(locked, dict):
        return False, f"fixtures 必须是对象（得到 {type(locked).__name__}）"
    for name, want in locked.items():
        if not isinstance(want, dict):
            return False, f"{name}：记录必须是对象（得到 {type(want).__name__}）"
        b, s = want.get("bytes"), want.get("sha256")
        if not isinstance(b, int) or not isinstance(s, str):
            return False, f"{name}：记录字段类型错误（bytes 须为整数、sha256 须为字符串）"
    bad = []
    for name, want in sorted(locked.items()):
        p = base / name
        if not p.exists():
            bad.append(f"{name}：文件缺失")
            continue
        try:
            data = p.read_bytes()
        except OSError as e:
            bad.append(f"{name}：文件读取失败：{e}")
            continue
        if len(data) != want["bytes"] or hashlib.sha256(data).hexdigest() != want["sha256"]:
            bad.append(f"{name}：字节/SHA256 与锁定值不一致")
    try:
        extra = sorted(p.name for p in base.glob("claim_*.json")
                       if p.name not in locked)
    except OSError as e:
        return False, f"扫描夹具目录失败：{e}"
    if extra:
        bad.append("未被 manifest 锁定的新夹具：" + "、".join(extra))
    if bad:
        return False, "；".join(bad)
    return True, f"{len(locked)}/{len(locked)} 夹具字节与锁定值一致"


if __name__ == "__main__":
    sys.exit(main())
