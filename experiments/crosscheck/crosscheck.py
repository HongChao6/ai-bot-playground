#!/usr/bin/env python3
"""crosscheck.py —— 多 bot 交叉核实协议 v1（可执行版）

把社区里沉淀的核实方法论编码成判定规则：
- 四栏法：结论 / 证据在哪 / 什么能证伪我 / 还差什么
- 来源独立 + 路径独立：至少 2 条来源、至少 2 条互不依赖的核查路径
- 证真 vs 证伪：必须实际做过一次推翻尝试；"过关"只算"未被推翻"，不算"证明为真"

用法：python3 crosscheck.py claim.json
输入 JSON：
{
  "claim": "待核结论原文",
  "sources": [{"path": "路径标识（如 official-docs / wire-report）",
               "ref": "确切出处（域名/页名/文档名）",
               "quote": "一手证据摘录"}],
  "falsification": {"attempt": "我用什么方法试图推翻它",
                    "result": "尝试结果",
                    "contradicted": false}
}
输出：Markdown 四栏核查卡 + 判定（已核实（未被推翻）/ 未核实 / 被推翻）。
退出码：0=已核实（未被推翻），2=未核实，3=被推翻，1=输入错误。
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

    paths = {s.get("path") for s in sources if s.get("path")}
    if len(sources) < 2:
        gaps.append(f"来源只有 {len(sources)} 条，协议要求 ≥2 条")
    if len(paths) < 2:
        gaps.append(f"独立核查路径只有 {len(paths)} 条，协议要求 ≥2 条互不依赖的路径")
    for i, s in enumerate(sources, 1):
        if not (s.get("quote") or "").strip():
            gaps.append(f"来源 {i}（{s.get('ref', '?')}）没有一手证据摘录")
        if not (s.get("ref") or "").strip():
            gaps.append(f"来源 {i} 没有确切出处标识")
    if not (fals.get("attempt") or "").strip():
        gaps.append("没有做证伪尝试（只找支持证据不算核实）")
    if not (fals.get("result") or "").strip():
        gaps.append("证伪尝试没有记录结果")

    contradicted = bool(fals.get("contradicted"))
    if contradicted:
        verdict, code = "被推翻", 3
    elif gaps:
        verdict, code = "未核实", 2
    else:
        verdict, code = "已核实（未被推翻）", 0

    print(f"## 核查卡\n")
    print(f"**结论**：{claim}\n")
    print("**证据在哪**：")
    if sources:
        for s in sources:
            print(f"- [{s.get('path', '?')}] {s.get('ref', '?')}：「{s.get('quote', '（无摘录）')}」")
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
