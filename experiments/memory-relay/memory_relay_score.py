#!/usr/bin/env python3
"""memory_relay_score.py -- 课题二「bot 记忆与连续性实测」实验装置的打分脚本。

用法:
    python3 memory_relay_score.py seed_facts.json hop1_pack.json [hop2_pack.json ...] [--card]

输入:
    seed_facts.json -- 种子事实包（12 条原子事实，每条含 id/类别/原文/关键词/确认状态）。
    hopN_pack.json -- 某一跳 bot 的重编码包:
        {"hop": 1, "by": "muse", "pack": [{"text": "...", "confidence": "已确认|未确认|不明"}, ...]}
        每一跳只能看上一跳的转述文本（hopN_retelling.txt），独立重编码，不得回看种子包。

评分规则（muse 打样版 v0.1，欢迎在 #6 议清后改）:
  - 关键词匹配：hop 文本命中种子事实关键词 >= 50% 即认定对应（关键词支持 | 同义备选）；关键词全部命中
    且置信度无升降 -> 留存；部分命中 -> 变形（内容缺损）。
  - 未确认->已确认 的状态翻转 = 严重变形（dot 验收要求，单独计数）。
  - 已确认->未确认/不明 = 变形（置信降级）。
  - 无对应种子事实的 hop 条目 = 臆造项，单独计数，不计入留存率分子。
  - 留存率 = 留存条数 / 种子事实总数。

输出：JSON（默认）或 --card 生成 Markdown 核查卡。退出码恒为 0（打分工具不做判定）。
诚实声明：本脚本的匹配算法是关键词启发式，不是语义理解；分数只反映"按此规则"的
测量结果，不证明 bot 的真实记忆能力。
"""
import json
import re
import sys

MATCH_THRESHOLD = 0.5

PUNCT = re.compile(r"[\s\xa0，。、；：…—\-\"'""''（）()【】《》!！?？·]+")


def norm(s):
    return PUNCT.sub("", s or "")


def load_seed(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d.get("facts", [])


def load_hop(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d.get("hop", "?"), d.get("by", "?"), d.get("pack", [])


def coverage(seed_fact, hop_text):
    # 关键词支持同义备选："a|b|c" 命中任一即算该关键词命中（容忍正常转述换词）
    kws = [norm(k) for k in seed_fact.get("keywords", [])]
    t = norm(hop_text)
    if not kws:
        return 0.0
    def hit_kw(k):
        return any(part and part in t for part in k.split("|"))
    hit = sum(1 for k in kws if hit_kw(k))
    return hit / len(kws)


def score_hop(seed, hop_no, by, pack):
    used = set()
    retained, deformed, lost, fabricated = [], [], [], []
    severe_flips = []
    for sf in seed:
        best, best_cov = None, 0.0
        for i, hf in enumerate(pack):
            if i in used:
                continue
            c = coverage(sf, hf.get("text", ""))
            if c > best_cov:
                best, best_cov = i, c
        sid = sf["id"]
        if best is None or best_cov < MATCH_THRESHOLD:
            lost.append({"id": sid, "seed": sf["text"], "best_coverage": round(best_cov, 2)})
            continue
        used.add(best)
        hf = pack[best]
        seed_status = sf.get("status", "")
        hop_conf = hf.get("confidence", "不明")
        flip_up = seed_status == "未确认" and hop_conf == "已确认"
        downgrade = seed_status == "已确认" and hop_conf in ("未确认", "不明")
        if flip_up:
            severe_flips.append(sid)
        if best_cov >= 1.0 and not flip_up and not downgrade:
            retained.append(sid)
        else:
            kinds = []
            if best_cov < 1.0:
                kinds.append("内容缺损")
            if flip_up:
                kinds.append("严重变形：未确认->已确认")
            if downgrade:
                kinds.append("置信降级")
            deformed.append({"id": sid, "kinds": kinds, "coverage": round(best_cov, 2),
                             "seed": sf["text"], "hop_text": hf.get("text", "")})
    for i, hf in enumerate(pack):
        if i not in used:
            fabricated.append(hf.get("text", ""))
    total = len(seed)
    rate = len(retained) / total if total else 0.0
    return {
        "hop": hop_no, "by": by,
        "retained": retained, "deformed": deformed, "lost": lost,
        "fabricated": fabricated, "severe_flips": severe_flips,
        "stats": {
            "seed_total": total,
            "retained": len(retained), "deformed": len(deformed),
            "lost": len(lost), "fabricated": len(fabricated),
            "severe_flips": len(severe_flips),
            "retention_rate": round(rate, 3),
        },
    }


def card(seed, results):
    lines = ["# 记忆接力打分卡（muse 打样，合成数据）", ""]
    for r in results:
        s = r["stats"]
        lines.append("## 第 %s 跳（%s）" % (r["hop"], r["by"]))
        lines.append("- 留存 %s/%s，留存率 %s" % (s["retained"], s["seed_total"], s["retention_rate"]))
        lines.append("- 变形 %s（严重翻转 %s）｜丢失 %s｜臆造 %s" % (
            s["deformed"], s["severe_flips"], s["lost"], s["fabricated"]))
        for d in r["deformed"]:
            lines.append("  - 变形 %s（%s，覆盖 %s）：%s" % (
                d["id"], "/".join(d["kinds"]), d["coverage"], d["hop_text"]))
        for l in r["lost"]:
            lines.append("  - 丢失 %s：%s" % (l["id"], l["seed"]))
        for fb in r["fabricated"]:
            lines.append("  - 臆造：%s" % fb)
        lines.append("")
    lines.append("口径：关键词启发式匹配，分数仅为按规则测量；以上均为合成打样，非成员真实参与。")
    return "\n".join(lines)


def main(argv):
    card_mode = "--card" in argv
    paths = [a for a in argv if a != "--card"]
    if len(paths) < 2:
        print("用法: memory_relay_score.py seed_facts.json hop1_pack.json [hop2_pack.json ...] [--card]",
              file=sys.stderr)
        return 2
    seed = load_seed(paths[0])
    results = []
    for p in paths[1:]:
        hop_no, by, pack = load_hop(p)
        results.append(score_hop(seed, hop_no, by, pack))
    if card_mode:
        print(card(seed, results))
    else:
        print(json.dumps({"seed_total": len(seed), "hops": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
