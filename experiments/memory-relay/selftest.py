#!/usr/bin/env python3
"""selftest.py —— memory_relay_score.py 的回归断言（muse 打样）。
预期值是作者写合成样本时的声明，不是独立验证；正式实验前欢迎成员改写/加例。
全部通过才 exit=0。
"""
import json
import subprocess
import sys

CASES = [
    # (hop_pack, 期望 stats 关键字段)
    ("hop1_pack.json", {"retained": 10, "deformed": 1, "lost": 1, "fabricated": 1,
                        "severe_flips": 1, "retention_rate": 0.833}),
    ("hop2_pack.json", {"retained": 8, "deformed": 2, "lost": 2, "fabricated": 1,
                        "severe_flips": 1, "retention_rate": 0.667}),
]

fails = []
for pack, expect in CASES:
    r = subprocess.run([sys.executable, "memory_relay_score.py",
                        "seed_facts.json", pack],
                       capture_output=True, text=True)
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
r = subprocess.run([sys.executable, "memory_relay_score.py",
                    "seed_facts.json", "hop1_pack.json"],
                   capture_output=True, text=True)
hop = json.loads(r.stdout)["hops"][0]
if "f05" not in hop["severe_flips"]:
    fails.append("hop1: f05 未确认->已确认 应记严重翻转")
if not any("每跳转述不少于 100 字" in x for x in hop["fabricated"]):
    fails.append("hop1: 臆造项应被单独计数")
if hop["stats"]["retained"] + hop["stats"]["deformed"] + hop["stats"]["lost"] != 12:
    fails.append("hop1: 留存+变形+丢失 应等于种子总数 12")

if fails:
    print("FAIL:")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("selftest: 全部通过（%d 个 hop 样本 + 3 条行为断言；预期值为作者声明，非独立验证）" % len(CASES))
