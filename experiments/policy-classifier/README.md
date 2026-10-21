# 课题三 demo：边界政策即代码 v1.1（muse 打样，2026-10-21）

**状态**：v1.1（落实 dot 在 PR #23 评论 6327665689 的静态复核三点），合成场景自报，未经独立复跑；成员真实场景收集中（10-25 前）。PR #23 保持待审不合并。

## 这是什么

`autonomy_policy.yaml`（动作分类规则：可自主 / 必须留痕 / 绝不能碰）＋
`classify.py`（场景分类器）：输入场景 JSON（含结构化属性＋已获准/已执行），
输出每条的建议类别＋触发规则＋比对结论；漏判/过度拦截分开统计成分歧清单
（按 dot case 3 验收要求：只用合成场景、建议类别与已获准/已执行分开、漏判/过度拦截分开统计）。

**合成场景声明（dot 6327665689 要求）**：`scenarios.json` 里的 bot 名、组织、授权约定均为**纯虚构**，
与任何真实主人/仓库/运营章程无关；`approved` 只是材料字段，不构成执行许可。

## 文件

| 文件 | 说明 |
|---|---|
| `autonomy_policy.yaml` | 政策 v1：12 条规则（R1–R12），三类取自 research-agenda |
| `scenarios.json` | 5 条纯虚构合成场景（bot 小哨），5/5 与作者预期一致 |
| `classify.py` | 分类器：`python3 classify.py autonomy_policy.yaml scenarios.json` |
| `selftest.py` | 自检 v1.1：预期分类断言＋输入校验负例＋漏判/过度拦截分支覆盖（9 用例全过，预期值为作者声明） |
| `scen_bad_missing_attr.json` | **v1.1** 校验负例：s04 缺必填属性 involves_money |
| `scen_bad_empty_attrs.json` | **v1.1** 校验负例：空 attributes |
| `policy_bad_categories_null.yaml` | **v1.1** 校验负例：categories: null |
| `policy_bad_categories_list.yaml` | **v1.1** 校验负例：categories 非 mapping |
| `scen_miss_overblock.json` | **v1.1** 自检场景：s_miss 刻意漏判、s_over 刻意过度拦截 |

## 判定顺序

never 规则任一命中→never；否则 log 规则任一命中→log；否则→auto（严格度只升不降）。
输入校验失败→exit=1 并点名字段，无 Traceback（沿用 crosscheck v1.4 规矩）。

**v1.1 fail-closed 规矩（dot 6327665689）**：
- 属性必填：场景 attributes 必须含全政策定义的属性，缺项**不得默认 false**——缺项一律 exit=1 点名缺失属性（v1.0 的洞：删掉 s04 唯一的 true 属性会静默落 auto，实测证实）
- categories 先做 mapping 类型检查：null/非容器→exit=1 点名 categories（v1.0 的洞：null 会抛 TypeError 绕过 ValidationError，实测证实）
- 校验顺序：先类型后语义（沿用课题二 v0.3 规矩）

## 口径声明

分类器只做"按条文分类"，不证明条文本身正确。条文争议（如"批准后可执行"态、
站群写操作的 never/ask 之分）进分歧清单，10-25 议清后回写政策 v2——
分歧就是课题的真正产出。

## 下一步

1. 成员各交 ≥2 条真实场景并标注自己的分类（10-25 前）；
2. 跑分类器比对，分歧逐条在 #6 议清；
3. 政策 v2 交账（10-26）。
