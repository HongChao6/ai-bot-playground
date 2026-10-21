#!/usr/bin/env python3
"""selftest.py —— crosscheck.py 的断言式自检（dot 复核 6320351297 point 3）

逐个 fixture 运行 crosscheck.py，断言退出码与判定文本：
- 全部通过才 exit=0，否则 exit=1 并列出失败项。
- 断言里的预期值是作者在写 fixture 时声明的，不是独立测试通过；
  独立复跑由其他成员按 RUNS.md 记录（作者自报 ≠ 独立验证）。
- 输入错误用例断言 exit=1；并断言 stderr 里有命名字段的错误文本、
  全程无 Traceback（dot 复核 6321741221 point 2：异常崩溃同样可能
  返回 1，不能据此算校验成功）。

用法：python3 selftest.py [crosscheck.py 所在目录，默认本脚本同目录]
"""
import subprocess
import sys
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
    if failures:
        print(f"\n{len(failures)} 个断言失败，见上。")
        return 1
    print(f"\n全部 {len(CASES)} 个断言通过（作者自跑；独立复跑见 RUNS.md）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
