#!/usr/bin/env python3
"""课题三：v2 对比卡生成器（《v2 对比协议》草案 v0.2 的可执行落实，muse 草案）

对比 A（基线）与 B（改动后）两组 classify 运行，按协议逐项输出对比卡：
- "比较条件变化"单列一栏：只有"共同且输入未变"的案例才做前后对照；
  新增／删除／改写输入的案例另看覆盖，不与对照组的一致率混比。
- 一致数变化时只给"归因检查线索"三栏（规则/实现/预期是否变化），
  默认"多因素／尚不能归因"；三分是检查线索，不是必须填满的结论。
- 本脚本绝不自动写因果结论——RUN 52 教训："一致数变化即条文改动的真实影响"
  是草率写法，已撤回（dot 6375993807）。
- 范围说明（dot 6378908461）：A/B 两边复用同一个已导入的 classify.py（同一实现），
  因此本脚本做的是"同实现下的政策/场景输入对照"，不是两份历史实现或
  历史运行已经验收的比较；无需为此扩大协议或提供私有材料。

用法：
    python3 compare_runs.py <policyA> <scenariosA> <policyB> <scenariosB> [--out card.json]
退出码：0＝对比卡已生成（对比卡本身不代表任何核实结论；运行均为作者自报，
dot 6375003210 明确"所述 7/7 运行我尚未独立核验"）。
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import classify as clf  # noqa: E402  # 复用 classify.py 的 load/classify/verdict，不改 demo 本体

UNATTRIBUTED = "多因素／尚不能归因"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(scenario):
    # "输入"指供给分类器的案例本身；"expected"是作者预期标签，单列为"归因检查线索"
    # 的"预期变化"一栏，不算输入变化（dot 6375993807：预期变只记"作者预期变更"）。
    body = {k: v for k, v in scenario.items() if k != "expected"}
    return json.dumps(body, ensure_ascii=False, sort_keys=True)


def run_side(policy_path, scen_path):
    pol, known = clf.load_policy(policy_path)
    scenarios = clf.load_scenarios(scen_path, known)
    # dot 6378908461：第 47–55 行用案例 ID 作字典键，load_scenarios 没有唯一性检查；
    # 重复 ID 会被后项静默覆盖、缩小共同案例数和分母。在生成字典前拒绝重复 ID，
    # 点名 id 字段与重复值，不改 classify.py 的载荷校验口径。
    seen, dups = set(), set()
    for s in scenarios:
        sid = s["id"]
        if sid in seen:
            dups.add(sid)
        seen.add(sid)
    if dups:
        print(f"输入错误：{scen_path} 存在重复的 id 字段（案例 ID 不唯一）："
              f"{sorted(dups)}；请先去重再对比", file=sys.stderr)
        sys.exit(1)
    rows = {}
    for s in scenarios:
        suggested, fired = clf.classify(s, pol["rules"])
        rows[s["id"]] = {
            "suggested": suggested,
            "fired_rules": fired,
            "expected": s["expected"],
            "input_canon": canon(s),
        }
    return {
        "policy_hash": sha256(policy_path),
        "scen_hash": sha256(scen_path),
        "impl_hash": sha256(HERE / "classify.py"),
        "rows": rows,
    }


def main():
    argv = sys.argv[1:]
    out_path = None
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 >= len(argv):
            print("用法：python3 compare_runs.py <policyA> <scenariosA> <policyB> <scenariosB> [--out card.json]",
                  file=sys.stderr)
            sys.exit(1)
        out_path = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if len(argv) != 4:
        print("用法：python3 compare_runs.py <policyA> <scenariosA> <policyB> <scenariosB> [--out card.json]",
              file=sys.stderr)
        sys.exit(1)
    args = argv

    a = run_side(args[0], args[1])
    b = run_side(args[2], args[3])
    ids_a, ids_b = set(a["rows"]), set(b["rows"])
    common = sorted(ids_a & ids_b)
    added = sorted(ids_b - ids_a)
    removed = sorted(ids_a - ids_b)

    policy_changed = a["policy_hash"] != b["policy_hash"]
    impl_changed = a["impl_hash"] != b["impl_hash"]

    card_rows = []
    n_cmp, n_same = 0, 0
    for sid in common:
        ra, rb = a["rows"][sid], b["rows"][sid]
        input_unchanged = ra["input_canon"] == rb["input_canon"]
        expected_changed = ra["expected"] != rb["expected"]
        suggested_changed = ra["suggested"] != rb["suggested"]
        if input_unchanged:
            n_cmp += 1
            n_same += (ra["suggested"] == rb["suggested"])
            condition = "输入未变（可前后对照）"
        else:
            condition = "输入已改写（另看覆盖，不混入对照组一致率）"
        clues = {"规则变化": policy_changed, "实现变化": impl_changed, "预期变化": expected_changed}
        # dot 6378908461：第 95–105 行 suggested 不变就写"无变化项"，但 expected 单独变化
        # 可能改变与作者预期的一致结果。改写为"建议类别未变"更准确；expected 变单独保留
        # 一条"作者预期变更"的独立说明，不能读成规则改进。
        attribution = "建议类别未变" if not suggested_changed else UNATTRIBUTED
        expected_note = ("作者预期变更（独立说明，不读作规则改进）"
                         if expected_changed else "")
        card_rows.append({
            "id": sid,
            "比较条件变化": condition,
            "A_suggested": ra["suggested"], "B_suggested": rb["suggested"],
            "A_expected": ra["expected"], "B_expected": rb["expected"],
            "A_fired": ra["fired_rules"], "B_fired": rb["fired_rules"],
            "归因检查线索": clues,
            "归因项": attribution,
            "预期说明": expected_note,
        })

    card = {
        "meta": {
            "协议": "v2_comparison_protocol.md v0.2（候选附件，随政策 v2 生效后冻结）",
            "A": {"policy": args[0], "policy_hash": a["policy_hash"][:12],
                  "scenarios": args[1], "scen_hash": a["scen_hash"][:12]},
            "B": {"policy": args[2], "policy_hash": b["policy_hash"][:12],
                  "scenarios": args[3], "scen_hash": b["scen_hash"][:12]},
            "实现": {"classify.py": a["impl_hash"][:12], "A与B一致": not impl_changed,
                     "python": sys.version.split()[0]},
            "诚实边界": "本卡仅记录两组自报运行的对照；不自动归因；独立核验待成员完成。",
            "范围": "A/B 复用同一个已导入的 classify.py（同一实现）；本卡是同实现下的政策/场景"
                    "输入对照，不是两份已验收的历史实现或历史运行的比较（dot 6378908461）。",
        },
        "对照组": {"共同案例数": len(common), "其中输入未变": n_cmp,
                   "建议类别前后一致": f"{n_same}/{n_cmp}",
                   "禁止的写法": "一致数变化不直接记为条文影响（dot 6375993807）"},
        "覆盖组（另看，不混入一致率）": {"新增案例": added, "删除案例": removed},
        "逐例": card_rows,
    }

    if out_path:
        Path(out_path).write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")

    print("== v2 对比卡 ==")
    print(f"  对照组：共同 {len(common)} 例，其中输入未变 {n_cmp} 例，建议类别一致 {n_same}/{n_cmp}")
    print(f"  覆盖组（另看）：新增 {added or '无'}，删除 {removed or '无'}")
    print(f"  规则变化：{policy_changed}｜实现变化：{impl_changed}｜Python {sys.version.split()[0]}")
    for r in card_rows:
        extra = f"｜{r['预期说明']}" if r["预期说明"] else ""
        print(f"  [{r['id']}] {r['比较条件变化']}｜A={r['A_suggested']} B={r['B_suggested']}｜"
              f"预期 {r['A_expected']}→{r['B_expected']}｜归因项：{r['归因项']}{extra}")
    print("  禁止的写法：一致数变化不直接记为条文影响。以上均为作者自报运行。")


if __name__ == "__main__":
    main()
