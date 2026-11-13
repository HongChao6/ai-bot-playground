#!/usr/bin/env python3
"""联合复跑一致性汇总工具（课题一，muse 记账用）。

输入：成员独立复跑回帖的 JSON 数组，每条格式：
  {"member": "火折子", "fixture": "claim_joint_dot_numeric.json", "fixture_rev": 2,
   "commit": "b178931d", "exit_code": 0,
   "verdict": "材料检查通过（未被推翻）",
   "independent": true, "seen_author_records": "没看过"}

两个声明字段语义分开（dot 6829784060 指出旧版共用一个含混布尔量）：
- independent（bool）：本人是否实际独立运行（非转抄他人输出）。
  必须是 JSON 布尔值；字符串 "false"/"true"、数字、null 一律拒绝并点名字段。
- seen_author_records（"看过"/"没看过"）：是否看过作者运行记录。
  看过／没看过都可计入汇总，仅用于分析"看过答案再跑"的偏差。

输出：按 fixture 分组的一致性汇总表。
- 同一 fixture 的所有报告 exit_code 必须全等，verdict 文本归一化后必须全等，
  否则标"不一致"，程序 exit=1（exit=0 表示全部一致）。
- 计入汇总的报告 <2 条时不判定「总体一致」：改印「样本不足」并 exit=2
  （验收门槛 ≥2 位成员独立复跑；0 条或 1 条时的「一致」是空转／平凡真，见 RUN 509）。
- fixture_rev/commit 不一致只警告不挡结论（材料版本问题另记账）。
- 未计入汇总的报告单独列入"待补"清单并注明原因：
  缺独立声明／非独立运行／缺看过／没看过声明；补上后重新汇总即计入。
  待补不挡其他已计入报告的一致性判定。
  待补行同时印出该条的 exit 码与判定（待补行内部也可能分歧，只印名字会藏起来，见 RUN 529）。
- 输入结构非法（顶层非数组、记录非对象、字段类型不对、seen 取值非法）
  一律 exit=2 并点名字段，拒绝运行，不抛 Traceback。
- 本工具只汇总报告内容，不证明材料中结论为真（与 dot 口径一致）。

用法：
  python3 joint_rerun_tally.py reports.json
  python3 joint_rerun_tally.py --selftest   # 合成样本验证工具自身，数据为虚构
"""
import json
import sys

EXPECTED_COMMIT = "b178931d"
EXPECTED_FIXTURE_REV = 2
SEEN_VALUES = ("看过", "没看过")


class FieldError(ValueError):
    """输入结构非法：message 已含字段名。"""


def normalize_verdict(v: str) -> str:
    """verdict 归一化：去空白，统一括号口径。"""
    v = (v or "").strip()
    v = v.replace("(", "（").replace(")", "）")
    return v


def _need_str(record, field):
    v = record.get(field)
    if not isinstance(v, str) or not v.strip():
        raise FieldError(f"字段错误 [{field}]：须为非空字符串，得 {v!r}")
    return v


def _need_int(record, field):
    v = record.get(field)
    if type(v) is not int:
        raise FieldError(f"字段错误 [{field}]：须为整数，得 {v!r}")
    return v


def validate_reports(reports):
    """结构校验：非法即抛 FieldError（点名字段），不返回半成品。"""
    if not isinstance(reports, list):
        raise FieldError(f"字段错误 [顶层]：须为 JSON 数组，得 {type(reports).__name__}")
    for i, r in enumerate(reports):
        if not isinstance(r, dict):
            raise FieldError(f"字段错误 [reports[{i}]]：须为对象，得 {type(r).__name__}")
        _need_str(r, "member")
        _need_str(r, "fixture")
        _need_int(r, "fixture_rev")
        _need_str(r, "commit")
        _need_int(r, "exit_code")
        _need_str(r, "verdict")
        if "independent" in r and type(r["independent"]) is not bool:
            raise FieldError(
                f"字段错误 [independent]：须为 JSON 布尔值，得 {r['independent']!r}"
            )
        if "seen_author_records" in r and r["seen_author_records"] not in SEEN_VALUES:
            raise FieldError(
                "字段错误 [seen_author_records]：须为“看过”或“没看过”，"
                f"得 {r['seen_author_records']!r}"
            )


def tally(reports):
    """返回 (rows, all_consistent, warnings, pending)。
    rows 为已计入报告的汇总行；pending 为 [(report, reason)] 未计入清单。"""
    validate_reports(reports)
    counted = []
    pending = []
    for r in reports:
        if "independent" not in r:
            pending.append((r, "缺独立声明（本人是否实际运行），请补充"))
        elif r["independent"] is False:
            pending.append((r, "非独立运行（本人未实际运行），不计入"))
        elif "seen_author_records" not in r:
            pending.append((r, "缺看过／没看过声明，请补充"))
        else:
            counted.append(r)

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
        seen = sorted({r.get("seen_author_records") for r in rs})
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
                "seen": seen,
                "consistent": consistent,
            }
        )
    return rows, all_consistent, warnings, pending


def print_table(rows):
    print(f"{'fixture':38} {'n':>2} {'exit_codes':12} {'一致':6} {'看过/没看过':14} verdict")
    for r in rows:
        print(
            f"{r['fixture']:38} {r['n']:>2} "
            f"{str(r['exit_codes']):12} "
            f"{'一致' if r['consistent'] else '不一致'} "
            f"{'/'.join(r['seen']):14} "
            f"{' / '.join(r['verdicts'])}"
        )


def _base_report(**over):
    r = {"member": "甲", "fixture": "f1.json", "fixture_rev": 2,
         "commit": EXPECTED_COMMIT, "exit_code": 0,
         "verdict": "材料检查通过（未被推翻）",
         "independent": True, "seen_author_records": "没看过"}
    r.update(over)
    return r


def selftest():
    """合成样本（虚构数据）验证工具自身的分支与校验。"""
    passed = 0
    total = 0

    def check(name, fn):
        nonlocal passed, total
        total += 1
        fn()
        passed += 1

    def expect_field_error(name, reports, field_substr):
        def fn():
            try:
                tally(reports)
            except FieldError as e:
                assert field_substr in str(e), f"{name}: 报错未点名 {field_substr}，得 {e}"
                return
            raise AssertionError(f"{name}: 非法输入未被拒绝")
        check(name, fn)

    # 一致：两名成员 exit 码与判定全同；看过／没看过都可计入
    def t_consistent():
        rows, ok, warnings, pending = tally([
            _base_report(member="甲", seen_author_records="没看过"),
            _base_report(member="乙", seen_author_records="看过"),
        ])
        assert ok is True and len(rows) == 1 and rows[0]["n"] == 2
        assert rows[0]["seen"] == ["没看过", "看过"], "看过/没看过应同列"
    check("consistent", t_consistent)

    # 不一致：exit 码分歧
    def t_exit_mismatch():
        rows, ok, warnings, pending = tally([
            _base_report(member="甲"),
            _base_report(member="乙", exit_code=2, verdict="未核实"),
        ])
        assert ok is False
    check("exit_mismatch", t_exit_mismatch)

    # 不一致：判定文本分歧（exit 码相同）
    def t_verdict_mismatch():
        rows, ok, warnings, pending = tally([
            _base_report(member="甲", exit_code=2, verdict="未核实"),
            _base_report(member="乙", exit_code=2, verdict="未核实（支持根不足）"),
        ])
        assert ok is False
    check("verdict_mismatch", t_verdict_mismatch)

    # 缺独立声明的报告不计入汇总、单独列待补：计入的两条一致，
    # 待补那条 exit 码不同也不影响一致性判定。
    def t_missing_independent():
        rows, ok, warnings, pending = tally([
            _base_report(member="甲"),
            _base_report(member="乙"),
            {"member": "丙", "fixture": "f1.json", "fixture_rev": 2,
             "commit": EXPECTED_COMMIT, "exit_code": 2,
             "verdict": "未核实", "seen_author_records": "没看过"},
        ])
        assert ok is True and len(rows) == 1 and rows[0]["n"] == 2, "缺声明排除失败"
        assert len(pending) == 1 and pending[0][0]["member"] == "丙", "待补清单失败"
        assert "缺独立声明" in pending[0][1], "待补原因应点名缺独立声明"
    check("missing_independent", t_missing_independent)

    # 待补行印出该条的 exit 码与判定（RUN 529「补」：待补两条自己还分歧，
    # 只印名字会把丙 exit 2 与丁 exit 0 的分歧藏起来）。
    def t_pending_prints_exit_verdict():
        import io as _io
        import tempfile as _tf
        from contextlib import redirect_stdout as _ro
        reports = [
            _base_report(member="甲", seen_author_records="没看过"),
            _base_report(member="乙", seen_author_records="看过"),
            {"member": "丙", "fixture": "f1.json", "fixture_rev": 2,
             "commit": EXPECTED_COMMIT, "exit_code": 2,
             "verdict": "未核实", "seen_author_records": "没看过"},
            {"member": "丁", "fixture": "f1.json", "fixture_rev": 2,
             "commit": EXPECTED_COMMIT, "exit_code": 0,
             "verdict": "材料检查通过（未被推翻）",
             "seen_author_records": "没看过"},
        ]
        with _tf.NamedTemporaryFile("w", suffix=".json", delete=False,
                                    encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False)
            path = f.name
        buf = _io.StringIO()
        with _ro(buf):
            code = main([path])
        out = buf.getvalue()
        assert code == 0, f"双待补四人单应 exit=0，得 {code}"
        assert "待补：丙/f1.json" in out and "exit=2" in out \
            and "未核实" in out, "待补行应印丙的 exit 码与判定"
        assert "待补：丁/f1.json" in out and "exit=0" in out \
            and "材料检查通过（未被推翻）" in out, "待补行应印丁的 exit 码与判定"
    check("pending_prints_exit_verdict", t_pending_prints_exit_verdict)

    # independent 为 false：非独立运行，不计入
    def t_not_independent():
        rows, ok, warnings, pending = tally([
            _base_report(member="甲"),
            _base_report(member="乙", independent=False),
        ])
        assert ok is True and rows[0]["n"] == 1 and len(pending) == 1
        assert "非独立运行" in pending[0][1]
    check("not_independent", t_not_independent)

    # 缺看过／没看过声明：待补，不计入
    def t_missing_seen():
        r = _base_report(member="乙")
        del r["seen_author_records"]
        rows, ok, warnings, pending = tally([_base_report(member="甲"), r])
        assert ok is True and rows[0]["n"] == 1 and len(pending) == 1
        assert "缺看过" in pending[0][1]
    check("missing_seen", t_missing_seen)

    # 全部待补：无计入行、全部待补，不误判为不一致。
    def t_all_pending():
        r = _base_report(member="丙", exit_code=2, verdict="未核实")
        del r["independent"]
        rows, ok, warnings, pending = tally([r])
        assert rows == [] and ok is True and len(pending) == 1, "全待补分支失败"
    check("all_pending", t_all_pending)

    # 计入 <2 条时 CLI 印「样本不足」并 exit=2，不再判「总体一致：是」
    # （RUN 510 的 A 选项：空转护栏）
    def t_insufficient_sample():
        import io as _io
        import tempfile as _tf
        from contextlib import redirect_stdout as _ro
        for reports in ([], [_base_report(member="甲")]):
            with _tf.NamedTemporaryFile("w", suffix=".json", delete=False,
                                        encoding="utf-8") as f:
                json.dump(reports, f, ensure_ascii=False)
                path = f.name
            buf = _io.StringIO()
            with _ro(buf):
                code = main([path])
            assert code == 2, f"样本不足应 exit=2，得 {code}"
            assert "样本不足" in buf.getvalue(), "应印「样本不足」"
            assert "总体一致：是" not in buf.getvalue(), \
                "样本不足时不应印「总体一致：是」"
    check("insufficient_sample", t_insufficient_sample)

    # 非法结构一律拒绝并点名字段（dot 6829784060 第二点）
    expect_field_error("string_false_independent",
                       [_base_report(independent="false")], "[independent]")
    expect_field_error("non_object_record", ["just-a-string"], "[reports[0]]")
    expect_field_error("non_string_verdict",
                       [_base_report(verdict=123)], "[verdict]")
    expect_field_error("top_level_not_array", {"member": "甲"}, "[顶层]")
    expect_field_error("string_exit_code",
                       [_base_report(exit_code="0")], "[exit_code]")
    expect_field_error("bad_seen_value",
                       [_base_report(seen_author_records="看过作者")],
                       "[seen_author_records]")

    print(f"selftest: {passed}/{total} PASS（合成虚构样本，仅验证工具自身分支）")
    return 0


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    if len(argv) != 1:
        print(__doc__)
        return 2
    try:
        with open(argv[0], encoding="utf-8") as f:
            reports = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"字段错误 [输入文件]：无法读取或解析 JSON：{e}", file=sys.stderr)
        return 2
    try:
        rows, all_consistent, warnings, pending = tally(reports)
    except FieldError as e:
        print(str(e), file=sys.stderr)
        return 2
    print_table(rows)
    print()
    print(f"成员报告数：{len(reports)}，计入汇总：{len(reports) - len(pending)}，"
          f"待补（缺声明／非独立运行）：{len(pending)}，fixture 数：{len(rows)}")
    for p, reason in pending:
        print(f"待补：{p.get('member')}/{p.get('fixture')}：{reason}；"
              f"exit={p.get('exit_code')}，判定={normalize_verdict(str(p.get('verdict')))}，未计入汇总")
    for w in warnings:
        print(f"警告：{w}")
    counted = len(reports) - len(pending)
    if counted < 2:
        print(f"样本不足：计入汇总的报告只有 {counted} 条，"
              "至少需要 2 条独立报告才能判定一致"
              "（验收门槛 ≥2 位成员独立复跑），不判定「总体一致」")
        return 2
    print(f"总体一致：{'是' if all_consistent else '否'}")
    print("注：一致仅说明同份材料的处理结果一致，不证明材料中结论为真。")
    return 0 if all_consistent else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
