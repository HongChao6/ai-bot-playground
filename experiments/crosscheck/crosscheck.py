#!/usr/bin/env python3
"""crosscheck.py —— 多 bot 交叉核实协议 v1.1（可执行版）

把社区里沉淀的核实方法论编码成判定规则：
- 四栏法：结论 / 证据在哪 / 什么能证伪我 / 还差什么
- 来源独立 + 路径独立：至少 2 个独立来源根（同源转载合并计 1），不是数链接
- 证真 vs 证伪：必须实际做过一次推翻尝试；"过关"只算"未被推翻"，不算"证明为真"
- v1.1 新增（dot 验收反例驱动）：origin 字段（同源合并计根）、stance 字段
  （support/contradict/neutral）、证据冲突判"证据冲突／待核"、独立性未知单列不自动算独立

用法：python3 crosscheck.py claim.json
输入 JSON：
{
  "claim": "待核结论原文",
  "sources": [{"path": "渠道标识（如 news-site / field-record）",
               "ref": "确切出处（域名/页名/文档名）",
               "quote": "一手证据摘录",
               "origin": "原始出处（同一份公告/通稿的各转载填同一 origin）",
               "stance": "support | contradict | neutral（这条证据对结论的立场）",
               "as_of": "适用日期（可选，透出到核查卡）"}],
  "falsification": {"attempt": "我用什么方法试图推翻它",
                    "result": "尝试结果",
                    "contradicted": false}
}
输出：Markdown 四栏核查卡 + 判定（已核实（未被推翻）/ 未核实 / 被推翻 / 证据冲突／待核）。
退出码：0=已核实（未被推翻），2=未核实，3=被推翻，4=证据冲突／待核，1=输入错误。
"""
import json
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python3 crosscheck.py claim.json", file=sys.stderr)
        return 1
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"读不进 claim 文件：{e}", file=sys.stderr)
        return 1

    claim = (data.get("claim") or "").strip()
    sources = data.get("sources") or []
    fals = data.get("falsification") or {}
    if not claim:
        print("缺 claim 字段", file=sys.stderr)
        return 1

    gaps = []  # 还差什么
    unknown = []  # 独立性未知的来源（单列，不计入来源根）

    # v1.1：按 origin 归并来源根；origin 缺失/含"未知" → 独立性未知，不自动算独立，
    # 每个未知来源自成一条"未知"项，绝不合并
    roots = {}  # origin -> [sources]
    for i, s in enumerate(sources, 1):
        origin = (s.get("origin") or "").strip()
        if not origin or "未知" in origin or "unknown" in origin.lower():
            unknown.append((i, s))
            continue
        roots.setdefault(origin, []).append((i, s))

    n_roots = len(roots)
    if n_roots < 2:
        gaps.append(f"独立来源根只有 {n_roots} 个，协议要求 ≥2 个（同源转载合并计 1 条根）")
    for i, s in unknown:
        gaps.append(f"来源 {i}（{s.get('ref', '?')}）独立性未知，未计入来源根")
    for i, s in enumerate(sources, 1):
        if not (s.get("quote") or "").strip():
            gaps.append(f"来源 {i}（{s.get('ref', '?')}）没有一手证据摘录")
        if not (s.get("ref") or "").strip():
            gaps.append(f"来源 {i} 没有确切出处标识")
        if not (s.get("origin") or "").strip():
            gaps.append(f"来源 {i}（{s.get('ref', '?')}）未声明 origin（原始出处），无法判断是否同源")
    if not (fals.get("attempt") or "").strip():
        gaps.append("没有做证伪尝试（只找支持证据不算核实）")
    if not (fals.get("result") or "").strip():
        gaps.append("证伪尝试没有记录结果")

    # v1.1：独立来源根之间立场对立 → 证据冲突，不靠票数判真
    stances = set()
    for origin, members in roots.items():
        root_stances = { (s.get("stance") or "neutral").strip() for _, s in members }
        if "contradict" in root_stances:
            stances.add("contradict")
        elif "support" in root_stances:
            stances.add("support")
    conflict = ("contradict" in stances and "support" in stances)

    contradicted = bool(fals.get("contradicted"))
    if contradicted:
        verdict, code = "被推翻", 3
    elif conflict:
        verdict, code = "证据冲突／待核", 4
        gaps.append("独立来源根之间证据对立，需保留适用日期与原文位置继续核实，不能按多数票判真")
    elif gaps:
        verdict, code = "未核实", 2
    else:
        verdict, code = "已核实（未被推翻）", 0

    print("## 核查卡（协议 v1.1）\n")
    print(f"**结论**：{claim}\n")
    print(f"**来源根**：{n_roots} 个（共 {len(sources)} 条证据；同源转载合并计 1 条根）")
    if roots:
        for origin, members in roots.items():
            mem_stances = { (s.get("stance") or "neutral").strip() for _, s in members }
            dates = sorted({ (s.get("as_of") or "").strip() for _, s in members if (s.get("as_of") or "").strip() })
            print(f"- 根「{origin}」：{len(members)} 条证据，立场={','.join(sorted(mem_stances))}" +
                  (f"，适用日期={','.join(dates)}" if dates else ""))
    if unknown:
        print("**独立性未知**（未计入来源根）：")
        for i, s in unknown:
            print(f"- 来源 {i} {s.get('ref', '?')}：「{(s.get('quote') or '（无摘录）').strip() or '（无摘录）'}」")
    print("\n**证据在哪**：")
    if sources:
        for i, s in enumerate(sources, 1):
            origin = (s.get("origin") or "").strip() or "（独立性未知）"
            print(f"- [来源 {i}·{s.get('path', '?')}] {s.get('ref', '?')}：「{(s.get('quote') or '（无摘录）').strip() or '（无摘录）'}」"
                  f"（origin：{origin}）")
    else:
        print("- （无）")
    print(f"\n**证伪尝试**：{fals.get('attempt', '（未做）')}")
    print(f"**尝试结果**：{fals.get('result', '（未记录）')}")
    print("\n**还差什么**：")
    if gaps:
        for g in gaps:
            print(f"- {g}")
    else:
        print("- 无缺口（按本协议口径）")
    print(f"\n**判定**：{verdict}")
    return code


if __name__ == "__main__":
    sys.exit(main())
