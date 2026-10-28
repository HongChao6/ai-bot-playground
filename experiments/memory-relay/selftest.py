#!/usr/bin/env python3
"""selftest.py —— memory_relay_score.py 的回归断言（muse 打样）。
预期值是作者写合成样本时的声明，不是独立验证；正式实验前欢迎成员改写/加例。
全部通过才 exit=0。v0.2 新增：数字边界匹配、严格输入校验负例、审计注分离。
v0.3 新增：5/5.5 边界、数字否定 guard、类型先校验后查枚举、顶层类型校验、
confidence 缺失政策断言（缺失=允许，按"不明"处理）。
v0.4（dot 6327630900）：路径全部改为相对 __file__（仓库根独立复跑可用），
confidence 缺省语义补匹配已确认事实的样本——f01 缺 confidence 应落
"置信降级"而非留存。
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

if fails:
    print("FAIL:")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("selftest: 全部通过（%d 个 hop 样本 + 行为断言；预期值为作者声明，非独立验证）" % len(CASES))
