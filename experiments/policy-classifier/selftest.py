#!/usr/bin/env python3
"""课题三 demo 自检：预期分类断言＋输入校验负例（作者声明预期，非独立验证）"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
CASES = [
    # (fixture 名, 预期退出码, stderr 应含, 判定说明)
    ("scenarios.json", 0, None, "5 条合成场景应全部通过且与 expected 一致"),
    ("bad_scenarios_type.json", 1, "attributes", "属性非布尔值→exit=1 点名字段"),
    ("bad_scenarios_unknown_attr.json", 1, "未知属性", "未知属性→exit=1 点名字段"),
    ("bad_scenarios_missing_field.json", 1, "缺少必填字段", "缺字段→exit=1 点名字段"),
]

# 负例夹具：基于 scenarios.json 改一处
def build_fixtures():
    base = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))
    import copy
    b1 = copy.deepcopy(base)
    b1["scenarios"][0]["attributes"]["involves_money"] = "yes"  # 非布尔
    (HERE / "bad_scenarios_type.json").write_text(json.dumps(b1), encoding="utf-8")
    b2 = copy.deepcopy(base)
    b2["scenarios"][0]["attributes"]["mystery_flag"] = True  # 未知属性
    (HERE / "bad_scenarios_unknown_attr.json").write_text(json.dumps(b2), encoding="utf-8")
    b3 = copy.deepcopy(base)
    del b3["scenarios"][0]["expected"]  # 缺字段
    (HERE / "bad_scenarios_missing_field.json").write_text(json.dumps(b3), encoding="utf-8")


def run(fixture):
    p = subprocess.run([sys.executable, str(HERE / "classify.py"),
                        str(HERE / "autonomy_policy.yaml"), str(HERE / fixture)],
                       capture_output=True, text=True, cwd=str(HERE))
    return p


def main():
    build_fixtures()
    expected_map = {"s01": "auto", "s02": "log", "s03": "never", "s04": "never", "s05": "never"}
    fails = []

    for fixture, code, stderr_needle, note in CASES:
        p = run(fixture)
        ok = True
        if p.returncode != code:
            ok = False; reason = f"退出码 {p.returncode}≠{code}"
        elif "Traceback" in (p.stdout + p.stderr):
            ok = False; reason = "出现 Traceback"
        elif stderr_needle and stderr_needle not in p.stderr:
            ok = False; reason = f"stderr 缺少 {stderr_needle!r}"
        else:
            reason = ""
        if ok and fixture == "scenarios.json":
            for sid, exp in expected_map.items():
                if f"[{sid}]" not in p.stdout:
                    ok = False; reason = f"输出缺场景 {sid}"; break
            # 每条都应"一致"且无漏判/过度拦截
            if "比对=一致" not in p.stdout or p.stdout.count("比对=一致") != 5:
                ok = False; reason = "5 条未全判一致"
            if "漏判（应严判宽，共 0）" not in p.stdout or "过度拦截（应宽判严，共 0）" not in p.stdout:
                ok = False; reason = "漏判/过度拦截计数非 0"
        print(("PASS" if ok else "FAIL") + f" {fixture}：{note}" + (f" —— {reason}" if not ok else ""))
        if not ok:
            fails.append(fixture)

    # 清理负例夹具（自检产物，不进仓库）
    for f in ("bad_scenarios_type.json", "bad_scenarios_unknown_attr.json", "bad_scenarios_missing_field.json"):
        (HERE / f).unlink(missing_ok=True)

    if fails:
        print(f"\n{len(fails)} 个用例失败：{fails}")
        sys.exit(1)
    print("\n全部通过（作者自检；预期值为作者声明，非独立验证）")


if __name__ == "__main__":
    main()
