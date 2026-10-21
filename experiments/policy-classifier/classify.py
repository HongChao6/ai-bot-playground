#!/usr/bin/env python3
"""课题三 demo：边界政策分类器 v1.1（muse 打样）

输入：autonomy_policy.yaml（政策条文）＋ scenarios.json（合成场景）
输出：每条场景的分类卡（建议类别 suggested＋触发规则＋已获准/已执行分开记录）
      ＋分歧清单（漏判/过度拦截分开统计——按 dot case 3 要求）

判定顺序：never 规则任一命中→never；否则 log 规则任一命中→log；否则→auto。
v1.1 fail-closed（dot 6327665689）：属性必填（缺项不得默认 false）；
categories 先做 mapping 类型检查；先类型后语义。
口径：本脚本只做"按条文分类"，条文本身的正确性不在此验证（见政策文件头）。
输入校验失败→exit=1 并点名字段，无 Traceback（沿用 crosscheck v1.4 规矩）。
"""
import json
import sys

try:
    import yaml
except ImportError:
    print("错误：缺少 pyyaml（policy 字段：autonomy_policy.yaml 无法解析）", file=sys.stderr)
    sys.exit(1)

CATEGORIES = ("auto", "log", "never")
STRICT = {"auto": 0, "log": 1, "never": 2}


class ValidationError(Exception):
    pass


def fail(field, msg):
    raise ValidationError(f"字段错误 [{field}]：{msg}")


def load_policy(path):
    try:
        with open(path, encoding="utf-8") as f:
            pol = yaml.safe_load(f)
    except FileNotFoundError:
        fail("autonomy_policy.yaml", "文件不存在")
    except Exception as e:
        fail("autonomy_policy.yaml", f"YAML 解析失败：{e}")
    if not isinstance(pol, dict):
        fail("autonomy_policy.yaml", "顶层必须是 mapping")
    # v1.1：categories 先做 mapping 类型检查（dot 6327665689）——
    # categories: null 时 `c not in None` 会抛 TypeError 绕过 ValidationError。
    cats = pol.get("categories")
    if not isinstance(cats, dict):
        fail("categories", f"必须是 mapping，实际是 {type(cats).__name__}")
    for c in CATEGORIES:
        if c not in cats:
            fail("categories", f"缺少类别 {c}")
    rules = pol.get("rules")
    if not isinstance(rules, list) or not rules:
        fail("rules", "必须是数组且非空")
    known_attrs = set()
    for i, r in enumerate(rules):
        tag = f"rules[{i}]"
        if not isinstance(r, dict):
            fail(tag, "必须是 mapping")
        for k in ("id", "category", "text", "when"):
            if k not in r:
                fail(tag, f"缺少必填键 {k}")
        if r["category"] not in CATEGORIES:
            fail(f"{tag}.category", f"非法类别 {r['category']!r}")
        if not isinstance(r["when"], list) or not all(isinstance(w, str) for w in r["when"]):
            fail(f"{tag}.when", "必须是字符串数组")
        known_attrs.update(r["when"])
    return pol, known_attrs


def load_scenarios(path, known_attrs):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        fail("scenarios.json", "文件不存在")
    except json.JSONDecodeError as e:
        fail("scenarios.json", f"JSON 解析失败：{e}")
    if not isinstance(data, dict) or not isinstance(data.get("scenarios"), list):
        fail("scenarios.json", "顶层须含 scenarios 数组")
    out = []
    for i, s in enumerate(data["scenarios"]):
        tag = f"scenarios[{i}]"
        if not isinstance(s, dict):
            fail(tag, "必须是 object")
        for k in ("id", "description", "attributes", "approved", "executed", "expected"):
            if k not in s:
                fail(tag, f"缺少必填字段 {k}")
        if s["expected"] not in CATEGORIES:
            fail(f"{tag}.expected", f"非法类别 {s['expected']!r}")
        if not isinstance(s["executed"], bool):
            fail(f"{tag}.executed", "必须是布尔值")
        attrs = s["attributes"]
        if not isinstance(attrs, dict):
            fail(f"{tag}.attributes", "必须是 object")
        for k, v in attrs.items():
            if k not in known_attrs:
                fail(f"{tag}.attributes.{k}", f"未知属性（政策未定义）：{k}")
            if not isinstance(v, bool):
                fail(f"{tag}.attributes.{k}", "必须是布尔值")
        # v1.1：属性必填，缺项不得默认 false（dot 6327665689）——
        # "把未知当安全"：删掉 s04 唯一的 true 属性 involves_money 会静默落 auto，
        # 实测证实（v1.0）。缺项一律 fail closed，点名缺失属性。
        missing = sorted(known_attrs - set(attrs.keys()))
        if missing:
            fail(f"{tag}.attributes", f"缺少必填属性：{missing}（缺项不得默认 false）")
        out.append(s)
    return out


def classify(scenario, rules):
    attrs = scenario["attributes"]
    fired = []
    suggested = "auto"
    for rule in rules:
        if any(attrs.get(w, False) for w in rule["when"]):
            fired.append(rule["id"])
            if STRICT[rule["category"]] > STRICT[suggested]:
                suggested = rule["category"]
    # 严格度只升不降：never 任一命中即 never（见政策文件"判定顺序"）
    return suggested, fired


def verdict(suggested, expected):
    if suggested == expected:
        return "一致"
    if STRICT[suggested] < STRICT[expected]:
        return "漏判"  # 分类器比应有类别更宽松：危险方向
    return "过度拦截"  # 分类器比应有类别更严：多要审批/多拦截


def main():
    if len(sys.argv) != 3:
        print("用法：python3 classify.py autonomy_policy.yaml scenarios.json", file=sys.stderr)
        sys.exit(1)
    try:
        policy, known_attrs = load_policy(sys.argv[1])
        scenarios = load_scenarios(sys.argv[2], known_attrs)
    except ValidationError as e:
        print(f"输入校验失败：{e}", file=sys.stderr)
        sys.exit(1)

    rules = policy["rules"]
    cards = []
    misses, overblocks = [], []
    for s in scenarios:
        suggested, fired = classify(s, rules)
        v = verdict(suggested, s["expected"])
        if v == "漏判":
            misses.append(s["id"])
        elif v == "过度拦截":
            overblocks.append(s["id"])
        cards.append({
            "id": s["id"],
            "description": s["description"],
            "suggested": suggested,
            "fired_rules": fired,
            "expected": s["expected"],
            "verdict": v,
            "approved": s["approved"],    # 已获准：与建议类别分开记录
            "executed": s["executed"],    # 已执行：与建议类别分开记录
            "synthetic": s.get("synthetic", False),
        })

    print("== 场景分类卡（政策 v1，合成场景） ==")
    for c in cards:
        print(f"[{c['id']}] {c['description']}")
        print(f"  建议类别 suggested={c['suggested']}（触发规则 {c['fired_rules'] or '无→默认 auto'}）"
              f"｜作者预期 expected={c['expected']}｜比对={c['verdict']}")
        print(f"  已获准 approved={c['approved']}｜已执行 executed={c['executed']}｜合成={c['synthetic']}")
    print()
    print("== 分歧清单（漏判/过度拦截分开统计） ==")
    print(f"  漏判（应严判宽，共 {len(misses)}）：{misses or '无'}")
    print(f"  过度拦截（应宽判严，共 {len(overblocks)}）：{overblocks or '无'}")
    print()
    print(f"共 {len(cards)} 条场景，{sum(1 for c in cards if c['verdict']=='一致')} 条一致。"
          "以上均为作者自报运行；条文争议与成员真实场景收集中（10-25 前），分歧将回写政策 v2。")


if __name__ == "__main__":
    main()
