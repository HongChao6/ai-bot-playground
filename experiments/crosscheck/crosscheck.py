#!/usr/bin/env python3
"""crosscheck.py —— 多 bot 交叉核实协议 v1.3（可执行版）

把社区里沉淀的核实方法论编码成判定规则：
- 四栏法：结论 / 证据在哪 / 什么能证伪我 / 还差什么
- 来源独立 + 路径独立：按 origin 归并来源根（同源转载合并计 1 根），不是数链接
- 证真 vs 证伪：必须实际做过一次推翻尝试；过关只算"按材料未被推翻"
- 支持根门槛（dot 复核 6320351297 point 1）：判定门槛只计算根立场=support
  的来源根（要求 ≥2）；neutral / 未声明立场的根只计材料，不计入支持门槛
- 成功标签（dot 复核 6320351297 point 2）：「已核实（未被推翻）」已改名
  「材料检查通过（未被推翻）」，与实际检查范围（提交材料检查）一致；
  机器可读状态 = 判定文本 + 退出码，不再靠免责声明补齐语义
- 严格输入校验（dot 复核 6320351297 point 3）：类型错 → exit=1 输入错误

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
输出：Markdown 四栏核查卡 + 判定。
退出码：0=材料检查通过（未被推翻），2=未核实，3=被推翻，
        4=待核（含证据冲突与材料存疑），1=输入错误。
判定顺序：输入错误 > 被推翻（证伪已推翻）> 证据冲突／待核 >
          待核（材料存疑）> 未核实（支持根不足或材料缺口）。
"""
import json
import sys

VALID_STANCES = {"support", "contradict", "neutral"}


def die(msg: str) -> int:
    print(f"输入错误：{msg}", file=sys.stderr)
    return 1


def check_types(data) -> str | None:
    """严格输入校验；返回错误描述，无错返回 None。"""
    if not isinstance(data, dict):
        return "顶层必须是 JSON 对象"
    claim = data.get("claim")
    if not isinstance(claim, str) or not claim.strip():
        return "claim 字段必须是非空字符串"
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        return "sources 字段必须是数组"
    for i, s in enumerate(sources, 1):
        if not isinstance(s, dict):
            return f"sources[{i}] 必须是对象"
        for field in ("path", "ref", "quote", "origin", "stance", "as_of"):
            v = s.get(field)
            if v is not None and not isinstance(v, str):
                return f"sources[{i}].{field} 必须是字符串"
        if s.get("_synthetic_fixture") is not None and not isinstance(
                s.get("_synthetic_fixture"), str):
            return f"sources[{i}]._synthetic_fixture 必须是字符串"
    fals = data.get("falsification", {})
    if not isinstance(fals, dict):
        return "falsification 字段必须是对象"
    for field in ("attempt", "result"):
        v = fals.get(field)
        if v is not None and not isinstance(v, str):
            return f"falsification.{field} 必须是字符串"
    if fals.get("contradicted") is not None and not isinstance(
            fals.get("contradicted"), bool):
        return "falsification.contradicted 必须是布尔值"
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python3 crosscheck.py claim.json", file=sys.stderr)
        return 1
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"读不进 claim 文件：文件不存在：{sys.argv[1]}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"读不进 claim 文件：JSON 解析失败：{e}", file=sys.stderr)
        return 1

    err = check_types(data)
    if err:
        return die(err)

    claim = data["claim"].strip()
    sources = data.get("sources") or []
    fals = data.get("falsification") or {}

    gaps = []  # 还差什么
    unknown = []  # 独立性未知的来源（单列，不计入来源根）

    # 按 origin 归并来源根；origin 缺失/含"未知" → 独立性未知，不自动算独立，
    # 每个未知来源自成一条"未知"项，绝不合并
    roots = {}  # origin -> [sources]
    for i, s in enumerate(sources, 1):
        origin = (s.get("origin") or "").strip()
        if not origin or "未知" in origin or "unknown" in origin.lower():
            unknown.append((i, s))
            continue
        roots.setdefault(origin, []).append((i, s))

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

    # 立场显式校验——无支持证据 / 同根内立场矛盾 / 非法立场值，
    # 一律判"待核（材料存疑）"，不再静默落到 exit=0
    material_doubt = []  # 待核（材料存疑）的原因，exit=4
    root_stance_map = {}  # origin -> 根级立场（基于显式立场）
    for origin, members in roots.items():
        explicit = []
        for _, s in members:
            raw = s.get("stance")
            if raw is None or not str(raw).strip():
                continue  # 未声明 stance：按 neutral（未声明）参与根级立场计算
            v = str(raw).strip()
            if v not in VALID_STANCES:
                material_doubt.append(
                    f"来源「{s.get('ref', '?')}」的立场值非法（{v!r}），"
                    "只接受 support / contradict / neutral")
            else:
                explicit.append(v)
        if "support" in explicit and "contradict" in explicit:
            # 同一 origin 内既有支持又有反对：显式记下，不许 elif 静默合并掉分歧
            material_doubt.append(
                f"来源根「{origin}」内部既有支持证据又有反对证据，分歧不可静默合并")
        if "contradict" in explicit:
            root_stance_map[origin] = "contradict"
        elif "support" in explicit:
            root_stance_map[origin] = "support"
        else:
            root_stance_map[origin] = "neutral"
    stances = set(root_stance_map.values())
    conflict = ("contradict" in stances and "support" in stances)
    if "support" not in stances:
        material_doubt.append(
            "没有任何独立来源根明确支持该结论（只有反对 / 中立证据），材料不足以核实")

    # v1.3（dot 复核 point 1）：支持门槛只计算支持根；
    # neutral / 未声明立场根只计材料，不计入支持门槛
    n_support_roots = sum(1 for r in root_stance_map.values() if r == "support")

    contradicted = bool(fals.get("contradicted"))
    if contradicted:
        verdict, code = "被推翻", 3
    elif conflict:
        verdict, code = "证据冲突／待核", 4
        gaps.append("独立来源根之间证据对立，需保留适用日期与原文位置继续核实，不能按证据数量判真")
    elif material_doubt:
        verdict, code = "待核（材料存疑）", 4
        gaps.extend(material_doubt)
    elif n_support_roots < 2:
        verdict, code = "未核实", 2
        gaps.append(
            f"明确支持的独立来源根只有 {n_support_roots} 个，协议要求 ≥2 "
            "（只计算根立场=support 的根；neutral / 未声明立场根只计材料，不计入支持门槛）")
    elif gaps:
        verdict, code = "未核实", 2
    else:
        verdict, code = "材料检查通过（未被推翻）", 0

    print("## 核查卡（协议 v1.3）\n")
    print(f"**结论**：{claim}\n")
    print("**口径声明**：本卡是「提交材料检查工具」，不是事实核验工具：它只检查"
          "提交者填写的材料（字段齐全性／声明的来源独立性／立场一致性）。"
          "判定「材料检查通过（未被推翻）」= 按提交材料通过了本协议检查，"
          "不是“事实为真”。origin 是提交者声明：填了不同 origin 本身不证明独立性，"
          "来源根计数基于声明分组。\n")
    print(f"**来源根**：共 {len(roots)} 个（共 {len(sources)} 条证据；同源转载合并计 1 条根）")
    print(f"**支持根**：{n_support_roots} 个（判定门槛要求 ≥2，只计算根立场=support 的根；"
          "neutral / 未声明立场根只计材料）")
    if roots:
        for origin, members in roots.items():
            shown = sorted({str(s.get("stance")).strip()
                            if str(s.get("stance") or "").strip()
                            else "neutral（未声明）" for _, s in members})
            dates = sorted({(s.get("as_of") or "").strip() for _, s in members
                            if (s.get("as_of") or "").strip()})
            print(f"- 根「{origin}」：{len(members)} 条证据，根立场={root_stance_map[origin]}"
                  f"（明细：{','.join(shown)}）" +
                  (f"，适用日期={','.join(dates)}" if dates else ""))
    if unknown:
        print("**独立性未知**（未计入来源根）：")
        for i, s in unknown:
            print(f"- 来源 {i} {s.get('ref', '?')}：「{(s.get('quote') or '（无摘录）').strip() or '（无摘录）'}」")
    print("\n**证据在哪**：")
    if sources:
        for i, s in enumerate(sources, 1):
            origin = (s.get("origin") or "").strip() or "（独立性未知）"
            print(f"- [来源 {i}·{s.get('path', '?')}] {s.get('ref', '?')}："
                  f"「{(s.get('quote') or '（无摘录）').strip() or '（无摘录）'}」"
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
