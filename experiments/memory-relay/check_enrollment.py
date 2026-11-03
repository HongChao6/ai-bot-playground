#!/usr/bin/env python3
"""课题二报名记账口径检查脚本（草稿工具，不作为报名门槛）。
口径：报名记账三项（所选角色／确切协议与清单版本链接／允许输入，缺项记"待补充"）
     ＋暴露单列一栏（本人自述"无／不确定／已知接触范围"；未说明记"待本人补充"，不代填）。
依据 dot 15:37 轮澄清（#6 6349396296）。
用法：python3 check_enrollment.py <回帖markdown文件>
exit=0：三项齐全且暴露有自述；exit=2：有缺项（只报告，不判定资格）。
"""
import re, sys, json


def _near(text, m, before=60, after=10):
    return text[max(0, m.start() - before):m.start() + after]


def check(text):
    missing = []
    # ① 所选角色 A/B/C
    role = re.search(r"(?:所选角色|报名)\s*[：:]\s*([ABC])\s*跳?", text)
    if not role:
        missing.append("所选角色（A/B/C 跳）：待补充")
    # ② 确切协议与清单版本链接（两条：冻结办法 + 人工评分清单；
    #    接受完整 URL 或 "#6 6336816965" 式帖子引用，成员真实写法以后者为主）
    links = list(re.finditer(r"https://github\.com/\S+|#\d+\s+\d{10,}", text))
    has_freeze = any("冻结" in _near(text, m) for m in links)
    has_checklist = any(("清单" in _near(text, m)) or ("评分" in _near(text, m)) for m in links)
    if not links:
        missing.append("版本链接（冻结办法 v0.2＋人工评分清单 v0.1 的帖链接）：待补充")
    elif not (has_freeze and has_checklist):
        missing.append("版本链接不全（需冻结办法与评分清单两条确切链接）：待补充")
    # ③ 允许输入
    allow = re.search(r"允许输入\s*[：:]\s*(.+)", text)
    if not allow or len(allow.group(1).strip()) < 4:
        missing.append("允许输入（允许读取的材料清单）：待补充")
    # ④ 暴露一栏
    exposure = re.search(r"暴露(?:自述)?\s*[：:]\s*(.+)", text)
    if not exposure or not exposure.group(1).strip():
        missing.append("暴露情况：待本人补充（不代填）")
    return (role.group(1) if role else None), missing


def main():
    if len(sys.argv) != 2:
        print("用法：python3 check_enrollment.py <回帖markdown文件>", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        text = f.read()
    role, missing = check(text)
    report = {"role": role, "missing": missing, "complete": not missing}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if not missing else 2)


if __name__ == "__main__":
    main()
