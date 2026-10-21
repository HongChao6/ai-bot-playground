#!/usr/bin/env python3
"""memory_relay_score.py -- 课题二「bot 记忆与连续性实测」实验装置的打分脚本。

用法:
    python3 memory_relay_score.py seed_facts.json hop1_pack.json [hop2_pack.json ...] [--card]

输入:
    seed_facts.json -- 种子事实包（12 条原子事实，每条含 id/类别/原文/关键词/确认状态）。
    hopN_pack.json -- 某一跳 bot 的重编码包:
        {"hop": 1, "by": "muse", "pack": [{"text": "...", "confidence": "已确认|未确认|不明",
          "audit_note": false}, ...]}
        每一跳只能看上一跳的转述文本（hopN_retelling.txt），独立重编码，不得回看种子包。
        带 "audit_note": true 的条目是审计注（打分人/裁判写的说明），不参与匹配、
        不计臆造、单独计数——防止审计文字污染盲测（dot 验收要求）。

评分规则（muse 打样版 v0.2，欢迎在 #6 议清后改）:
  - 关键词匹配：hop 文本命中种子事实关键词 >= 50% 即认定对应（关键词支持 | 同义备选）；关键词全部命中
    且置信度无升降 -> 留存；部分命中 -> 变形（内容缺损）。
  - 数字边界匹配（v0.2，dot 验收要求）：纯数字关键词（5、24、0.6、20261022 等）用数字边界
    匹配，不做裸子串匹配——"5" 不命中 "15"、"15" 不命中 "5"。非数字关键词仍用子串匹配
    （中文无词边界，数字边界只保证数值不串位）。覆盖 <1 且缺失的关键词是数字时，
    变形种类加记「数值变化/缺失」。
  - 未确认->已确认 的状态翻转 = 严重变形（dot 验收要求，单独计数）。
  - 已确认->未确认/不明 = 变形（置信降级）。
  - 无对应种子事实的 hop 条目 = 臆造项，单独计数，不计入留存率分子。
  - 留存率 = 留存条数 / 种子事实总数。
  - 严格输入校验（v0.2，dot 验收要求）：confidence 只接受 已确认/未确认/不明；
    种子事实 id/text/status/keywords 必填且类型正确；违反 -> stderr 点名字段、exit=1、
    无 Traceback。

输出：JSON（默认）或 --card 生成 Markdown 核查卡。
退出码：0 打分完成；1 输入校验失败；2 用法错误。
诚实声明：本脚本的匹配算法是关键词启发式，不是语义理解；分数只反映"按此规则"的
测量结果，不证明 bot 的真实记忆能力。
"""
import json
import re
import sys

MATCH_THRESHOLD = 0.5

PUNCT = re.compile(r"[\s ，。、；：…—\-\"'""''（）()【】《》!！?？·]+")
DIGIT_PART = re.compile(r"^\d+(\.\d+)?$")

VALID_CONF = {"已确认", "未确认", "不明"}
VALID_STATUS = {"已确认", "未确认"}


class InputError(Exception):
    """输入格式错误（校验失败），非程序崩溃。"""


def norm(s):
    return PUNCT.sub("", s or "")


def part_matches(part, text):
    """数字纯键用数字边界匹配（防 5 命中 15），其余子串匹配。"""
    if DIGIT_PART.match(part):
        return re.search(r"(?<!\d)" + re.escape(part) + r"(?!\d)", text) is not None
    return part in text


def load_seed(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        raise InputError(f"打不开种子文件：{path}")
    except json.JSONDecodeError as e:
        raise InputError(f"种子文件 {path} 不是合法 JSON：第 {e.lineno} 行附近")
    facts = d.get("facts")
    validate_seed(facts)
    return facts


def validate_seed(facts):
    if not isinstance(facts, list) or not facts:
        raise InputError("seed_facts.json: facts 必须是非空数组")
    for i, f in enumerate(facts):
        loc = f"种子事实[{i}]"
        if not isinstance(f, dict):
            raise InputError(f"{loc} 必须是对象")
        for field in ("id", "text", "status", "keywords"):
            if field not in f:
                raise InputError(f"{loc} 缺字段：{field}")
        if not isinstance(f["id"], str) or not f["id"]:
            raise InputError(f"{loc} 的 id 必须是非空字符串")
        if not isinstance(f["text"], str) or not f["text"]:
            raise InputError(f"{loc} 的 text 必须是非空字符串")
        if f["status"] not in VALID_STATUS:
            raise InputError(f"{loc} 的 status 非法：{f.get('status')!r}，只能是 已确认/未确认")
        kws = f["keywords"]
        if not isinstance(kws, list) or not kws or not all(isinstance(k, str) and k for k in kws):
            raise InputError(f"{loc} 的 keywords 必须是非空字符串数组")


def load_hop(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        raise InputError(f"打不开 hop 文件：{path}")
    except json.JSONDecodeError as e:
        raise InputError(f"hop 文件 {path} 不是合法 JSON：第 {e.lineno} 行附近")
    if not isinstance(d, dict):
        raise InputError(f"hop 文件 {path} 顶层必须是对象")
    hop_no, by, pack = d.get("hop", "?"), d.get("by", "?"), d.get("pack")
    validate_hop(path, hop_no, pack)
    return hop_no, by, pack


def validate_hop(path, hop_no, pack):
    loc = f"hop{hop_no}_pack({path})"
    if not isinstance(pack, list):
        raise InputError(f"{loc}：pack 必须是数组")
    for i, e in enumerate(pack):
        eloc = f"{loc} 条目[{i}]"
        if not isinstance(e, dict):
            raise InputError(f"{eloc} 必须是对象")
        if "text" not in e or not isinstance(e["text"], str) or not e["text"]:
            raise InputError(f"{eloc} 缺 text 或 text 非字符串")
        conf = e.get("confidence", "不明")
        if conf not in VALID_CONF:
            raise InputError(f"{eloc} 的 confidence 非法：{conf!r}，只能是 已确认/未确认/不明")
        if "audit_note" in e and not isinstance(e["audit_note"], bool):
            raise InputError(f"{eloc} 的 audit_note 必须是布尔值")


def coverage_detail(seed_fact, hop_text):
    """返回 (覆盖率, 缺失的数字关键词列表)。关键词支持 | 同义备选；数字纯键用边界匹配。"""
    kws = [norm(k) for k in seed_fact.get("keywords", [])]
    t = norm(hop_text)
    if not kws:
        return 0.0, []
    missed_numeric = []
    hit = 0
    for k in kws:
        parts = [p for p in k.split("|") if p]
        matched = any(part_matches(p, t) for p in parts)
        if matched:
            hit += 1
        elif any(DIGIT_PART.match(p) for p in parts):
            missed_numeric.append(k)
    return hit / len(kws), missed_numeric


def score_hop(seed, hop_no, by, pack):
    # 审计注条目先摘出来：不参与匹配、不计臆造、单独计数。
    audit_notes = [hf.get("text", "") for hf in pack if hf.get("audit_note", False)]
    items = [hf for hf in pack if not hf.get("audit_note", False)]
    used = set()
    retained, deformed, lost, fabricated = [], [], [], []
    severe_flips = []
    for sf in seed:
        best, best_cov, best_missed = None, 0.0, []
        for i, hf in enumerate(items):
            if i in used:
                continue
            c, missed = coverage_detail(sf, hf.get("text", ""))
            if c > best_cov:
                best, best_cov, best_missed = i, c, missed
        sid = sf["id"]
        if best is None or best_cov < MATCH_THRESHOLD:
            lost.append({"id": sid, "seed": sf["text"], "best_coverage": round(best_cov, 2)})
            continue
        used.add(best)
        hf = items[best]
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
            if best_missed:
                kinds.append("数值变化/缺失")
            if flip_up:
                kinds.append("严重变形：未确认->已确认")
            if downgrade:
                kinds.append("置信降级")
            deformed.append({"id": sid, "kinds": kinds, "coverage": round(best_cov, 2),
                             "seed": sf["text"], "hop_text": hf.get("text", "")})
    for i, hf in enumerate(items):
        if i not in used:
            fabricated.append(hf.get("text", ""))
    total = len(seed)
    rate = len(retained) / total if total else 0.0
    return {
        "hop": hop_no, "by": by,
        "retained": retained, "deformed": deformed, "lost": lost,
        "fabricated": fabricated, "severe_flips": severe_flips,
        "audit_notes": audit_notes,
        "stats": {
            "seed_total": total,
            "retained": len(retained), "deformed": len(deformed),
            "lost": len(lost), "fabricated": len(fabricated),
            "severe_flips": len(severe_flips),
            "audit_notes": len(audit_notes),
            "retention_rate": round(rate, 3),
        },
    }


def card(seed, results):
    lines = ["# 记忆接力打分卡（muse 打样，合成数据）", ""]
    for r in results:
        s = r["stats"]
        lines.append("## 第 %s 跳（%s）" % (r["hop"], r["by"]))
        lines.append("- 留存 %s/%s，留存率 %s" % (s["retained"], s["seed_total"], s["retention_rate"]))
        lines.append("- 变形 %s（严重翻转 %s）｜丢失 %s｜臆造 %s｜审计注 %s" % (
            s["deformed"], s["severe_flips"], s["lost"], s["fabricated"], s["audit_notes"]))
        for d in r["deformed"]:
            lines.append("  - 变形 %s（%s，覆盖 %s）：%s" % (
                d["id"], "/".join(d["kinds"]), d["coverage"], d["hop_text"]))
        for l in r["lost"]:
            lines.append("  - 丢失 %s：%s" % (l["id"], l["seed"]))
        for fb in r["fabricated"]:
            lines.append("  - 臆造：%s" % fb)
        lines.append("")
    lines.append("口径：关键词启发式匹配（数字纯键用数字边界），分数仅为按规则测量；以上均为合成打样，非成员真实参与。")
    return "\n".join(lines)


def main(argv):
    card_mode = "--card" in argv
    paths = [a for a in argv if a != "--card"]
    if len(paths) < 2:
        print("用法: memory_relay_score.py seed_facts.json hop1_pack.json [hop2_pack.json ...] [--card]",
              file=sys.stderr)
        return 2
    try:
        seed = load_seed(paths[0])
        results = []
        for p in paths[1:]:
            hop_no, by, pack = load_hop(p)
            results.append(score_hop(seed, hop_no, by, pack))
    except InputError as e:
        print(f"输入错误：{e}", file=sys.stderr)
        return 1
    if card_mode:
        print(card(seed, results))
    else:
        print(json.dumps({"seed_total": len(seed), "hops": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
