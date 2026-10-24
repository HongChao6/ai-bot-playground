#!/usr/bin/env python3
"""课题三 demo 自检 v1.1：预期分类断言＋输入校验负例（作者声明预期，非独立验证）

v1.1 新增（dot 6327665689 验收要求）：
- 缺项不得默认 false：scen_bad_missing_attr（删单个属性）/ scen_bad_empty_attrs（空 attributes）
  → exit=1、点名字段、无 Traceback
- categories 类型先行校验：policy_bad_categories_null / policy_bad_categories_list
  → exit=1、点名 categories、无 Traceback
- 漏判/过度拦截核心分支覆盖：scen_miss_overblock（s_miss 刻意漏判、s_over 刻意过度拦截）
"""
import json
import subprocess
import sys
import copy
from pathlib import Path

HERE = Path(__file__).parent
CASES = [
    # (fixture 名, 预期退出码, stderr 应含, 判定说明)
    ("scenarios.json", 0, None, "5 条合成场景应全部通过且与 expected 一致"),
    ("bad_scenarios_type.json", 1, "attributes", "属性非布尔值→exit=1 点名字段"),
    ("bad_scenarios_unknown_attr.json", 1, "未知属性", "未知属性→exit=1 点名字段"),
    ("bad_scenarios_missing_field.json", 1, "缺少必填字段", "缺字段→exit=1 点名字段"),
    # v1.1：缺项不得默认 false（dot 6327665689 point 1）
    ("scen_bad_missing_attr.json", 1, "involves_money", "缺单个必填属性→exit=1 点名该属性"),
    ("scen_bad_empty_attrs.json", 1, "缺少必填属性", "空 attributes→exit=1 点名缺失属性"),
]


def build_fixtures():
    base = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))
    b1 = copy.deepcopy(base)
    b1["scenarios"][0]["attributes"]["involves_money"] = "yes"  # 非布尔
    (HERE / "bad_scenarios_type.json").write_text(json.dumps(b1), encoding="utf-8")
    b2 = copy.deepcopy(base)
    b2["scenarios"][0]["attributes"]["mystery_flag"] = True  # 未知属性
    (HERE / "bad_scenarios_unknown_attr.json").write_text(json.dumps(b2), encoding="utf-8")
    b3 = copy.deepcopy(base)
    del b3["scenarios"][0]["expected"]  # 缺字段
    (HERE / "bad_scenarios_missing_field.json").write_text(json.dumps(b3), encoding="utf-8")


def run(policy, fixture):
    p = subprocess.run([sys.executable, str(HERE / "classify.py"),
                        str(HERE / policy), str(HERE / fixture)],
                       capture_output=True, text=True, cwd=str(HERE))
    return p


def check(p, code, stderr_needle):
    if p.returncode != code:
        return False, f"退出码 {p.returncode}≠{code}"
    if "Traceback" in (p.stdout + p.stderr):
        return False, "出现 Traceback"
    if stderr_needle and stderr_needle not in p.stderr:
        return False, f"stderr 缺少 {stderr_needle!r}"
    return True, ""


def main():
    build_fixtures()
    expected_map = {"s01": "auto", "s02": "log", "s03": "never", "s04": "never", "s05": "never"}
    fails = []

    for fixture, code, stderr_needle, note in CASES:
        p = run("autonomy_policy.yaml", fixture)
        ok, reason = check(p, code, stderr_needle)
        if ok and fixture == "scenarios.json":
            for sid in expected_map:
                if f"[{sid}]" not in p.stdout:
                    ok, reason = False, f"输出缺场景 {sid}"; break
            if ok and ("比对=一致" not in p.stdout or p.stdout.count("比对=一致") != 5):
                ok, reason = False, "5 条未全判一致"
            if ok and ("漏判（应严判宽，共 0）" not in p.stdout
                       or "过度拦截（应宽判严，共 0）" not in p.stdout):
                ok, reason = False, "漏判/过度拦截计数非 0"
        print(("PASS" if ok else "FAIL") + f" {fixture}：{note}" + (f" —— {reason}" if not ok else ""))
        if not ok:
            fails.append(fixture)

    # v1.1：categories 类型负例（dot 6327665689 point 2）
    for pol, needle, note in [
        ("policy_bad_categories_null.yaml", "categories", "categories: null→exit=1 点名 categories"),
        ("policy_bad_categories_list.yaml", "categories", "categories 非 mapping→exit=1 点名 categories"),
    ]:
        p = run(pol, "scenarios.json")
        ok, reason = check(p, 1, needle)
        print(("PASS" if ok else "FAIL") + f" {pol}：{note}" + (f" —— {reason}" if not ok else ""))
        if not ok:
            fails.append(pol)

    # v1.1：漏判/过度拦截核心分支覆盖（dot 6327665689 point 3）
    p = run("autonomy_policy.yaml", "scen_miss_overblock.json")
    ok, reason = check(p, 0, None)
    if ok:
        if "漏判（应严判宽，共 1）：['s_miss']" not in p.stdout:
            ok, reason = False, "漏判清单应为 ['s_miss']"
        elif "过度拦截（应宽判严，共 1）：['s_over']" not in p.stdout:
            ok, reason = False, "过度拦截清单应为 ['s_over']"
        elif "[s_miss]" not in p.stdout or "比对=漏判" not in p.stdout:
            ok, reason = False, "s_miss 应判漏判"
        elif "[s_over]" not in p.stdout or "比对=过度拦截" not in p.stdout:
            ok, reason = False, "s_over 应判过度拦截"
    print(("PASS" if ok else "FAIL") + " scen_miss_overblock.json：刻意漏判 s_miss＋过度拦截 s_over，各 1 条"
          + (f" —— {reason}" if not ok else ""))
    if not ok:
        fails.append("scen_miss_overblock.json")

    # 清理自检动态产物（不进仓库）
    for f in ("bad_scenarios_type.json", "bad_scenarios_unknown_attr.json", "bad_scenarios_missing_field.json"):
        (HERE / f).unlink(missing_ok=True)

    if fails:
        print(f"\n{len(fails)} 个用例失败：{fails}")
        sys.exit(1)
    print("\n全部通过（作者自检 v1.1；预期值为作者声明，非独立验证）")


if __name__ == "__main__":
    main()
