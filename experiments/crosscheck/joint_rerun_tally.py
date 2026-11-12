#!/usr/bin/env python3
"""联合复跑一致性汇总工具（课题一，muse 记账用）。

输入：成员独立复跑回帖的 JSON 数组，每条格式：
  {"member": "火折子", "fixture": "claim_joint_dot_numeric.json", "fixture_rev": 2,
   "commit": "b178931d", "exit_code": 0,
   "verdict": "材料检查通过（未被推翻）", "independent": true}

输出：按 fixture 分组的一致性汇总表。
- 同一 fixture 的所有报告 exit_code 必须全等，verdict 文本归一化后必须全等，
  否则标"不一致"，程序 exit=1（exit=0 表示全部一致）。
- fixture_rev/commit 不一致只警告不挡结论（材料版本问题另记账）。
- 缺独立声明（independent 缺失或为 false）的报告不计入一致性汇总，
  单独列入"待补"清单（请报告人补一句是否看过作者运行记录），
  不挡其他已计入报告的一致性判定；补上声明后重新汇总即计入。
- 本工具只汇总报告内容，不证明材料中结论为真（与 dot 口径一致）。

用法：
  python3 joint_rerun_tally.py reports.json
  python3 joint_rerun_tally.py --selftest   # 合成样本验证工具自身，数据为虚构
"""
import json
import sys

EXPECTED_COMMIT = "b178931d"
EXPECTED_FIXTURE_REV = 2


def normalize_verdict(v: str) -> str:
    """verdict 归一化：去空白，统一括号口径。"""
    v = (v or "").strip()
    v = v.replace("(", "（").replace(")", "）")
    return v


def tally(reports):
    """返回 (rows, all_consistent, warnings, pending)。
    rows 为已计入报告的汇总行；pending 为缺独立声明、未计入汇总的报告。"""
    counted = [r for r in reports if r.get("independent")]
    pending = [r for r in reports if not r.get("independent")]

    by_fixture = {}
    for r in counted:
        by_fixture.setdefault(r.get("fixture"), []).append(r)

    rows = []
    warnings = []
    all_consistent = True
    for fixture, rs in sorted(by_fixture.items()):
        for r in rs:
            if r.get("commit") != EXPECTED_COMMIT:
                warnings.append(
                    f"{r.get('member')}/{fixture}: commit={r.get('commit')} "
                    f"≠固定 {EXPECTED_COMMIT}，材料版本待核"
                )
            if r.get("fixture_rev") != EXPECTED_FIXTURE_REV:
                warnings.append(
                    f"{r.get('member')}/{fixture}: fixture_rev={r.get('fixture_rev')} "
                    f"≠ {EXPECTED_FIXTURE_REV}，夹具版本待核"
                )

        exit_codes = {r.get("exit_code") for r in rs}
        verdicts = {normalize_verdict(r.get("verdict")) for r in rs}
        members = [r.get("member") for r in rs]
        consistent = len(rs) >= 1 and len(exit_codes) == 1 and len(verdicts) == 1
        if not consistent:
            all_consistent = False
        rows.append(
            {
                "fixture": fixture,
                "n": len(rs),
                "members": members,
                "exit_codes": sorted(exit_codes, key=lambda x: (x is None, x)),
                "verdicts": sorted(verdicts),
                "consistent": consistent,
            }
        )
    return rows, all_consistent, warnings, pending


def print_table(rows):
    print(f"{'fixture':38} {'n':>2} {'exit_codes':12} {'一致':6} verdict")
    for r in rows:
        print(
            f"{r['fixture']:38} {r['n']:>2} "
            f"{str(r['exit_codes']):12} "
            f"{'一致' if r['consistent'] else '不一致'} "
            f"{' / '.join(r['verdicts'])}"
        )


def selftest():
    """合成样本（虚构数据）验证工具自身的三个分支。"""
    cases = [
        # 一致：两名成员 exit 码与判定全同
        (
            "consistent",
            [
                {"member": "甲", "fixture": "f1.json", "fixture_rev": 2,
                 "commit": EXPECTED_COMMIT, "exit_code": 0,
                 "verdict": "材料检查通过（未被推翻）", "independent": True},
                {"member": "乙", "fixture": "f1.json", "fixture_rev": 2,
                 "commit": EXPECTED_COMMIT, "exit_code": 0,
                 "verdict": "材料检查通过（未被推翻）", "independent": True},
            ],
            True,
        ),
        # 不一致：exit 码分歧
        (
            "exit_mismatch",
            [
                {"member": "甲", "fixture": "f1.json", "fixture_rev": 2,
                 "commit": EXPECTED_COMMIT, "exit_code": 0,
                 "verdict": "材料检查通过（未被推翻）", "independent": True},
                {"member": "乙", "fixture": "f1.json", "fixture_rev": 2,
                 "commit": EXPECTED_COMMIT, "exit_code": 2,
                 "verdict": "未核实", "independent": True},
            ],
            False,
        ),
        # 不一致：判定文本分歧（exit 码相同）
        (
            "verdict_mismatch",
            [
                {"member": "甲", "fixture": "f1.json", "fixture_rev": 2,
                 "commit": EXPECTED_COMMIT, "exit_code": 2,
                 "verdict": "未核实", "independent": True},
                {"member": "乙", "fixture": "f1.json", "fixture_rev": 2,
                 "commit": EXPECTED_COMMIT, "exit_code": 2,
                 "verdict": "未核实（支持根不足）", "independent": True},
            ],
            False,
        ),
    ]
    passed = 0
    for name, reports, expect_consistent in cases:
        rows, ok, warnings, pending = tally(reports)
        assert ok == expect_consistent, f"{name}: 期望 {expect_consistent}, 得 {ok}"
        passed += 1
    # 缺独立声明的报告不计入汇总、单独列待补：计入的两条一致，
    # 待补那条 exit 码不同也不影响一致性判定。
    rows, ok, warnings, pending = tally([
        {"member": "甲", "fixture": "f1.json", "fixture_rev": 2,
         "commit": EXPECTED_COMMIT, "exit_code": 0,
         "verdict": "材料检查通过（未被推翻）", "independent": True},
        {"member": "乙", "fixture": "f1.json", "fixture_rev": 2,
         "commit": EXPECTED_COMMIT, "exit_code": 0,
         "verdict": "材料检查通过（未被推翻）", "independent": True},
        {"member": "丙", "fixture": "f1.json", "fixture_rev": 2,
         "commit": EXPECTED_COMMIT, "exit_code": 2,
         "verdict": "未核实", "independent": False},
    ])
    assert ok is True and len(rows) == 1 and rows[0]["n"] == 2, "缺声明排除失败"
    assert len(pending) == 1 and pending[0]["member"] == "丙", "待补清单失败"
    passed += 1
    # 全部缺声明：无计入行、全部待补，不误判为不一致。
    rows, ok, warnings, pending = tally([
        {"member": "丙", "fixture": "f1.json", "fixture_rev": 2,
         "commit": EXPECTED_COMMIT, "exit_code": 2,
         "verdict": "未核实"},
    ])
    assert rows == [] and ok is True and len(pending) == 1, "全待补分支失败"
    passed += 1
    print(f"selftest: {passed}/{len(cases) + 2} PASS（合成虚构样本，仅验证工具自身分支）")
    return 0


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    if len(argv) != 1:
        print(__doc__)
        return 2
    with open(argv[0], encoding="utf-8") as f:
        reports = json.load(f)
    rows, all_consistent, warnings, pending = tally(reports)
    print_table(rows)
    print()
    print(f"成员报告数：{len(reports)}，计入汇总：{len(reports) - len(pending)}，"
          f"待补（缺独立声明）：{len(pending)}，fixture 数：{len(rows)}")
    for p in pending:
        print(f"待补：{p.get('member')}/{p.get('fixture')}：缺独立声明，"
              f"未计入汇总（请补一句是否看过作者运行记录）")
    for w in warnings:
        print(f"警告：{w}")
    print(f"总体一致：{'是' if all_consistent else '否'}")
    print("注：一致仅说明同份材料的处理结果一致，不证明材料中结论为真。")
    return 0 if all_consistent else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
