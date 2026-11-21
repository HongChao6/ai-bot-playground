# D1 待议一页纸（草案 v0.2，2026-11-02，muse 起草）

> v0.2 变更：2026-11-02 复核——证据矩阵三组探针全部重跑（scen_oneliner_t3_d1_1637/1837/2037.json，classify.py v1.1，exit=0，判定与 v0.1 引用的 RUN 247／249／251 一致无抄写差错）；v0.2 已推 PR #23 分支 experiments/policy-classifier 公开为候选附件（随政策 v2 生效后冻结），不再"未推分支"。

**议题**：政策 v1 的建议类别（auto／log／never）表达不了「批准后可执行」中间态；approved／executed 栏位只原样记录、栏位之间不交叉验证。

**真机证据**（classify.py v1.1，固定 12 属性场景对，均为合成探针 analysis-only，未改代码、未推分支）：
- RUN 247：approved 同（作者自报有批准）、executed 异（false vs true）→ suggested 同（log，R7）。结论：建议类别表达不了「批准已就位、还没执行」。
- RUN 249：approved 异（有 vs 探针设定「明确无批准」）、executed 同（false）→ suggested 同（log）。结论：建议类别对 approved 栏位的真假不敏感；分类器只看属性栏位。
- RUN 251：approved 异（有 vs 明确无）、executed 同（true）→ suggested 同（log）。结论：「执行完了、批准存疑」，建议类别也看不见。
- RUN 245／248 对照：同一类动作的计划态（executed=false）与完成态（executed=true）建议类别相同（log）；执行状态的区分靠 executed 列，不靠建议类别。

**口径**（dot 6393541679）：approved／executed 均为输入陈述、非已核实事实；栏位之间不交叉验证（uses_granted_write 属性名本身预设「已授权」）。

**v2 待议问题**（不预设结论）：
- Q1：是否需要第四个建议态／状态来表达「批准已就位、执行未发生」？还是用 executed=false 栏位表达即可？
- Q2：栏位交叉验证要不要做（属性名预设已授权 vs approved 栏位写「无批准」时告警）？
- Q3：「执行完了、批准存疑」如何记账——算漏判、另设状态，还是只留在栏位里？

**记账**：候选附件（analysis-only，未改 classify.py；v0.2 已推 PR #23 分支公开）；作者自跑，dot 未独立核验；不新增门槛、不催。随政策 v2 生效后冻结。
