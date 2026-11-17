#!/usr/bin/env python3
"""selftest.py —— memory_relay_score.py 的回归断言（muse 打样）。
预期值是作者写合成样本时的声明，不是独立验证；正式实验前欢迎成员改写/加例。
全部通过才 exit=0。v0.2 新增：数字边界匹配、严格输入校验负例、审计注分离。
v0.3 新增：5/5.5 边界、数字否定 guard、类型先校验后查枚举、顶层类型校验、
confidence 缺失政策断言（缺失=允许，按"不明"处理）。
v0.4（dot 6327630900）：路径全部改为相对 __file__（仓库根独立复跑可用），
confidence 缺省语义补匹配已确认事实的样本——f01 缺 confidence 应落
"置信降级"而非留存。
v0.5（执行 #6 6914117154 的 A）：中文数字写法归一化——hop_cn_numeral_pack.json
（f01 五跳／f02 二十四小时／f03 零点六）应与 hop1 基线一致留存 10/12。
v0.5.1（dot 6937317802 静态推演＋muse 真跑证实）：逐位写法——纯数字字连续出现
按逐位拼接，「二零二六」= 2026（旧逻辑逐字覆盖 num 会算成 6）；hop_cn_year_pack.json
（f07 写「二零二六年十月二十二日」）仍为变形 0.67：逐位数字本身已修好，但完整日期
关键词 2026-10-22 含年/月/日分隔符、无法整串匹配——该分隔符缺口与中文数字无关，
阿拉伯写法「2026年10月22日」同样 0.67（对照实证），记为已知局限，不修。
"""
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
SCRIPT = str(BASE / "memory_relay_score.py")


def F(name):
    return str(BASE / name)


CASES = [
    # (hop_pack, 期望 stats 关键字段)
    ("hop1_pack.json", {"retained": 10, "deformed": 1, "lost": 1, "fabricated": 1,
                        "severe_flips": 1, "retention_rate": 0.833, "audit_notes": 0}),
    ("hop2_pack.json", {"retained": 8, "deformed": 2, "lost": 2, "fabricated": 1,
                        "severe_flips": 1, "retention_rate": 0.667, "audit_notes": 0}),
    # 数字反例：5 跳被写成 15 跳，不应再判完整留存
    ("hop3_numeric_pack.json", {"retained": 9, "deformed": 2, "lost": 1, "fabricated": 1,
                                "severe_flips": 1, "retention_rate": 0.75, "audit_notes": 0}),
    # 审计注条目：不参与匹配、不计臆造
    ("hop_audit_pack.json", {"retained": 10, "deformed": 1, "lost": 1, "fabricated": 1,
                             "severe_flips": 1, "retention_rate": 0.833, "audit_notes": 1}),
    # 5/5.5 边界：整数关键词"5"不应命中"5.5"（dot 6326331117）
    ("hop3_numeric55_pack.json", {"retained": 9, "deformed": 2, "lost": 1, "fabricated": 1,
                                  "severe_flips": 1, "retention_rate": 0.75, "audit_notes": 0}),
    # 否定表达反例："根本没有5跳" 不算记住 "5跳"（dot 6326331117）
    ("hop_negation_pack.json", {"retained": 9, "deformed": 2, "lost": 1, "fabricated": 1,
                                "severe_flips": 1, "retention_rate": 0.75, "audit_notes": 0}),
    # confidence 缺失：允许，按"不明"处理，统计与 hop1 一致
    ("hop_missing_conf_pack.json", {"retained": 10, "deformed": 1, "lost": 1, "fabricated": 1,
                                    "severe_flips": 1, "retention_rate": 0.833, "audit_notes": 0}),
    # confidence 缺省语义：f01（已确认）匹配条目缺 confidence → 置信降级，
    # 不是留存（dot 6327630900）
    ("hop_missing_conf_matched_pack.json", {"retained": 9, "deformed": 2, "lost": 1, "fabricated": 1,
                                            "severe_flips": 1, "retention_rate": 0.75, "audit_notes": 0}),
    # 中文数字归一化（v0.5，执行 #6 6914117154 的 A）：五跳／二十四小时／零点六
    # 应与 hop1 基线一致留存 10/12（v0.4 下为 7/12）
    ("hop_cn_numeral_pack.json", {"retained": 10, "deformed": 1, "lost": 1, "fabricated": 1,
                                  "severe_flips": 1, "retention_rate": 0.833, "audit_notes": 0}),
    # 逐位年份写法（v0.5.1，dot 6937317802）：f07 写「二零二六年十月二十二日」，
    # 数字本身已逐位转成 2026，但完整日期关键词因年/月/日分隔符无法整串匹配，
    # 仍落变形 0.67、留存 9/12——此为已知局限的当前行为，不是修复目标
    ("hop_cn_year_pack.json", {"retained": 9, "deformed": 2, "lost": 1, "fabricated": 1,
                               "severe_flips": 1, "retention_rate": 0.75, "audit_notes": 0}),
]

fails = []


def run(args):
    return subprocess.run([sys.executable, SCRIPT] + args,
                          capture_output=True, text=True)


for pack, expect in CASES:
    r = run([F("seed_facts.json"), F(pack)])
    if r.returncode != 0:
        fails.append(f"{pack}: scorer exit={r.returncode}, stderr={r.stderr[:120]}")
        continue
    stats = json.loads(r.stdout)["hops"][0]["stats"]
    for k, v in expect.items():
        if stats[k] != v:
            fails.append(f"{pack}: {k} 期望 {v}，实际 {stats[k]}")
    if "Traceback" in (r.stdout + r.stderr):
        fails.append(f"{pack}: 输出含 Traceback")

# 行为断言：dot 验收要点
r = run([F("seed_facts.json"), F("hop1_pack.json")])
hop = json.loads(r.stdout)["hops"][0]
if "f05" not in hop["severe_flips"]:
    fails.append("hop1: f05 未确认->已确认 应记严重翻转")
if not any("每跳转述不少于 100 字" in x for x in hop["fabricated"]):
    fails.append("hop1: 臆造项应被单独计数")
if hop["stats"]["retained"] + hop["stats"]["deformed"] + hop["stats"]["lost"] != 12:
    fails.append("hop1: 留存+变形+丢失 应等于种子总数 12")

# 行为断言：数字边界（dot 15跳/5跳反例）
r = run([F("seed_facts.json"), F("hop3_numeric_pack.json")])
hop = json.loads(r.stdout)["hops"][0]
if "f01" in hop["retained"]:
    fails.append("数字反例: 15跳 不应被判为 f01（5跳）的完整留存")
deformed_ids = {d["id"] for d in hop["deformed"]}
if "f01" not in deformed_ids:
    fails.append("数字反例: f01 应落入变形")
kinds = " ".join("/".join(d.get("kinds", [])) for d in hop["deformed"] if d["id"] == "f01")
if "数值变化/缺失" not in kinds:
    fails.append("数字反例: f01 变形种类应标注 数值变化/缺失")

# 行为断言：严格输入校验负例（exit=1、点名字段、无 Traceback）
r = run([F("seed_facts.json"), F("hop_bad_confidence_pack.json")])
if r.returncode != 1:
    fails.append(f"校验负例: confidence 非法 应 exit=1，实际 exit={r.returncode}")
if "confidence" not in r.stderr:
    fails.append("校验负例: stderr 应点名 confidence 字段")
if "Traceback" in (r.stdout + r.stderr):
    fails.append("校验负例: 输出不应含 Traceback")

r = run([F("seed_bad.json"), F("hop1_pack.json")])
if r.returncode != 1:
    fails.append(f"校验负例: 种子缺 id 应 exit=1，实际 exit={r.returncode}")
if "id" not in r.stderr:
    fails.append("校验负例: stderr 应点名 id 字段")
if "Traceback" in (r.stdout + r.stderr):
    fails.append("校验负例: 输出不应含 Traceback")

# 行为断言：审计注分离
r = run([F("seed_facts.json"), F("hop_audit_pack.json")])
hop = json.loads(r.stdout)["hops"][0]
if hop["stats"]["audit_notes"] != 1:
    fails.append("审计注: 应单独计数 1")
if any("审计注" in x for x in hop["fabricated"]):
    fails.append("审计注: 不应被计入臆造")

# 行为断言：5/5.5 边界（dot 6326331117）
r = run([F("seed_facts.json"), F("hop3_numeric55_pack.json")])
hop = json.loads(r.stdout)["hops"][0]
if "f01" in hop["retained"]:
    fails.append("5/5.5 反例: 5.5跳 不应被判为 f01（5跳）的完整留存")
deformed_ids = {d["id"] for d in hop["deformed"]}
if "f01" not in deformed_ids:
    fails.append("5/5.5 反例: f01 应落入变形")
kinds = " ".join("/".join(d.get("kinds", [])) for d in hop["deformed"] if d["id"] == "f01")
if "数值变化/缺失" not in kinds:
    fails.append("5/5.5 反例: f01 变形种类应标注 数值变化/缺失")

# 行为断言：否定表达反例（dot 6326331117）
r = run([F("seed_facts.json"), F("hop_negation_pack.json")])
hop = json.loads(r.stdout)["hops"][0]
if "f01" in hop["retained"]:
    fails.append("否定反例: '根本没有5跳' 不应被判为 f01 的留存")

# 行为断言：非数字键否定已知局限实证（RUN 176）：f10 全部三关键词字面命中
# （"上一跳／转述文本／不能回看"），但转述明示豁免规则——关键词启发式无法区分
# "陈述禁止"与"豁免禁止"，脚本判留存，人工应判变形（RUN 45 同类分歧模式）
r = run([F("seed_facts.json"), F("hop_negation_rule_pack.json")])
hop = json.loads(r.stdout)["hops"][0]
if "f10" not in hop["retained"]:
    fails.append("非数字否定局限: '不能回看……可以不遵守' 下 f10 应（按脚本当前行为）计入留存——此为已知局限，不是正确判定")

# 行为断言：confidence 缺失 = 允许，按"不明"处理（dot 6326331117）
r = run([F("seed_facts.json"), F("hop_missing_conf_pack.json")])
if r.returncode != 0:
    fails.append(f"缺失政策: confidence 缺失应允许，exit 应为 0，实际 exit={r.returncode}")
if "Traceback" in (r.stdout + r.stderr):
    fails.append("缺失政策: 输出不应含 Traceback")

# 行为断言：confidence 缺省语义——匹配已确认事实的条目缺 confidence
# 应落"置信降级"而非留存（dot 6327630900）
r = run([F("seed_facts.json"), F("hop_missing_conf_matched_pack.json")])
if r.returncode != 0:
    fails.append(f"缺省语义: 缺字段的匹配条目应被接受，exit 应为 0，实际 exit={r.returncode}")
else:
    hop = json.loads(r.stdout)["hops"][0]
    if "f01" in hop["retained"]:
        fails.append("缺省语义: 缺 confidence 的 f01 不应计入留存")
    f01_def = [d for d in hop["deformed"] if d["id"] == "f01"]
    if not f01_def:
        fails.append("缺省语义: f01 应落入变形")
    elif "置信降级" not in "/".join(f01_def[0].get("kinds", [])):
        fails.append("缺省语义: f01 变形种类应标注 置信降级")

# 行为断言：中文数字归一化（v0.5，执行 #6 6914117154 的 A）
r = run([F("seed_facts.json"), F("hop_cn_numeral_pack.json")])
hop = json.loads(r.stdout)["hops"][0]
for fid in ("f01", "f02", "f03"):
    if fid not in hop["retained"]:
        fails.append(f"中文数字归一化: {fid}（五跳／二十四小时／零点六）应计入留存")
if hop["stats"]["retention_rate"] != 0.833:
    fails.append("中文数字归一化: 留存率应与 hop1 基线一致为 0.833")

# 行为断言：类型先校验后查枚举（dot 6326331117）——一律 exit=1、点名字段、无 Traceback
type_cases = [
    ("hop_bad_conftype_pack.json", "confidence"),
    ("seed_bad_status_type.json", "status"),
    ("seed_top_array.json", "顶层"),
    ("seed_top_null.json", "顶层"),
]
seed_bad = {"hop_bad_conftype_pack.json": "seed_facts.json"}
for name, field in type_cases:
    seed = F("seed_bad_status_type.json") if name.startswith("seed_bad") else \
        F(name) if name.startswith("seed_top") else F("seed_facts.json")
    hop_pack = F("hop1_pack.json") if name.startswith("seed_") else F(name)
    r = run([seed, hop_pack])
    if r.returncode != 1:
        fails.append(f"类型校验 {name}: 应 exit=1，实际 exit={r.returncode}")
    if field not in r.stderr:
        fails.append(f"类型校验 {name}: stderr 应点名 {field}")
    if "Traceback" in (r.stdout + r.stderr):
        fails.append(f"类型校验 {name}: 输出不应含 Traceback")

# 行为断言：逐位写法（v0.5.1，dot 6937317802）——单元级：纯数字字连续出现
# 按逐位拼接；位值写法不受影响
sys.path.insert(0, str(BASE))
import memory_relay_score as mrs
if mrs._cn_int("二零二六") != 2026:
    fails.append("逐位写法: _cn_int('二零二六') 应为 2026")
if mrs.normalize_cn_numerals("二零二六年十月二十二日") != "2026年10月22日":
    fails.append("逐位写法: normalize('二零二六年十月二十二日') 应为 '2026年10月22日'")
for _w, _want in (("二十四", 24), ("一百二十三", 123), ("一万二千三百四十五", 12345), ("五", 5)):
    if mrs._cn_int(_w) != _want:
        fails.append(f"逐位写法: _cn_int('{_w}') 应为 {_want}（位值写法回归）")
if not mrs.part_matches(mrs.normalize_cn_numerals(mrs.norm("2026")),
                        mrs.normalize_cn_numerals(mrs.norm("装置打样在二零二六年。"))):
    fails.append("逐位写法: 关键词 2026 应对「二零二六」命中")
# 端到端：完整日期仍变形（分隔符缺口，已知局限）；年份数字本身不再是原因
r = run([F("seed_facts.json"), F("hop_cn_year_pack.json")])
hop = json.loads(r.stdout)["hops"][0]
f07_def = [d for d in hop["deformed"] if d["id"] == "f07"]
if not f07_def or f07_def[0]["coverage"] != 0.67:
    fails.append("逐位写法: f07（二零二六年十月二十二日）应落变形、覆盖 0.67（分隔符缺口）")

if fails:
    print("FAIL:")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("selftest: 全部通过（%d 个 hop 样本 + 行为断言；预期值为作者声明，非独立验证）" % len(CASES))
