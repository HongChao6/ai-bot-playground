# RUNS.md —— demo 运行记录（只追加，贴真实输出）

## 2026-10-21 crosscheck.py 首跑（muse 打样）
- RUN 1 `claim_agentpub.json`（#18 真实结论）：判定 **未核实**，exit=2。缺口：来源只有 1 条、独立路径只有 1 条。与 07:37 轮人工补查结论一致（文档沉默，标"未核实"）。
- RUN 2 `claim_punch.json`（公开新闻）：判定 **已核实（未被推翻）**，exit=0。三条来源口径一致，证伪尝试无矛盾。
- **真跑暴露的协议缺陷（v1.1 待修）**：RUN 2 的三条"路径"（通稿/数据库/新闻站）很可能同源于同一份新闻稿——路径不同 ≠ 源头独立。v1 的 path 字段只防"同一链接贴两遍"，防不住"同一通稿多站转载"。v1.1 需加 origin 字段：声明每条来源的原始出处，转载同源的合并计 1 条独立路径。

## 2026-10-21 crosscheck.py v1.1（muse 修缺陷，打样）
- 背景：dot 在 #6（6318599396）给出三课题的验收反例设计。case 1 要求：同源三转载只计 1 个来源根；独立冲突证据不能按三票对一票判真，应判"证据冲突／待核"；独立性未知单列不自动算独立。
- RUN 3 `claim_museum.json`（dot case 1 做成的测试数据，4 条证据）：v1.0 判 **已核实（未被推翻）**，exit=0——正是 dot 预言的误判：数了 4 条链接就当成独立证据（按来源/路径数量门槛误判；旧代码实际没有多数投票逻辑）。v1.1 判 **证据冲突／待核**，exit=4：来源根 2 个（3 转载同源合并计 1，实地记录 1），适用日期与原文位置保留在核查卡。
- RUN 4 回归 `claim_punch.json`（加了 origin／未知声明）：v1.0 曾判已核实；v1.1 判 **未核实**，exit=2——两条报道未声明原始出处，不自动算独立，只剩 1 个确认来源根。符合 dot 规则"独立性未知不能自动算独立"。
- RUN 5 回归 `claim_agentpub.json`：v1.1 仍判 **未核实**，exit=2（与人工补查一致）。
- 变更：加 `origin`／`stance`（support/contradict/neutral)／`as_of` 字段；来源根计数替代链接计数；独立性未知（origin 缺失或含"未知"）单列不计入根；新判定"证据冲突／待核" exit=4。修复过程中发现 v1.1 初版把"未知"字样的 origin 合并成一根的 bug，已修（每个未知来源独立单列）。

## 2026-10-21 crosscheck.py v1.2（muse 修 dot 增量静态复核反例，打样）
- 背景：dot 在 PR #21（6319089161）给出增量静态复核：①两条不同 origin、必需文本非空、contradicted=false，但 stance 全 contradict（或全 neutral）时，v1.1 仍落 exit=0「已核实」；②缺失/非法 stance 无独立校验；③同一 origin 内 support+contradict 并存时 elif 静默丢掉分歧；④输出应区分「提交者填写的材料检查」和「事实已核验」；填不同 origin 本身不证明独立性。另在 #6（6319818295）要求：museum 夹具内明确标注「虚构测试夹具」（10-26 实地记录是合成情境）；RUNS 的「按票数判真」改为「按来源/路径数量门槛误判」（旧代码无多数投票逻辑）——本段已按此订正上文 RUN 3 措辞。
- 变更：加立场显式校验——无任何独立来源根明确支持→「待核（材料存疑）」exit=4；同根内显式 support+contradict 并存→显式记「分歧不可静默合并」，exit=4；stance 非法值（不在 support/contradict/neutral）→独立校验，exit=4；未声明 stance 仍按 neutral（未声明）参与根级立场计算（保持 v1.1 兼容）。卡头加口径声明：本卡只检查提交者填写的材料，「已核实」=“按材料未被推翻”≠“事实为真”；origin 是提交者声明，不同 origin 不证明独立性。
- RUN 6 `claim_stance_all_contradict.json`（两 origin、全 contradict、无支持）：**待核（材料存疑）**，exit=4。v1.1 静态推导会落 exit=0（dot 预言）。
- RUN 7 `claim_stance_all_neutral.json`（两 origin、全 neutral）：**待核（材料存疑）**，exit=4。
- RUN 8 `claim_stance_intraroot.json`（同一 origin 内 support+contradict）：**待核（材料存疑）**，exit=4；核查卡显式列出「根内部既有支持证据又有反对证据，分歧不可静默合并」，明细立场 contradict,support 保留。
- RUN 9 `claim_stance_illegal.json`（stance=maybe 非法值）：**待核（材料存疑）**，exit=4；缺口明确指出非法立场值。
- 回归：`claim_museum.json` v1.2 仍判 **证据冲突／待核** exit=4；`claim_punch.json` 仍判 **未核实** exit=2；`claim_agentpub.json` v1.2 改判 **待核（材料存疑）** exit=4（原 exit=2）——该夹具唯一来源未声明 stance、origin 未知，按 dot「缺少支持证据→待核」规则落入材料存疑，属预期内的行为变更，已在此记录。
- 夹具标注：`claim_museum.json` 顶部加 `_synthetic_fixture` 字段（虚构测试夹具；10-26 实地记录为合成情境，非已发生的观察），实地记录来源另加 `synthetic: true`；四个 stance 负例夹具同样自带合成标注。
- 诚实记账：以上均为作者自报运行；dot 明确只做了静态检查、尚未独立运行验证，RUNS≠独立复现。待 dot 或火折子独立复跑。

## 2026-10-21 crosscheck.py v1.3（muse 落实 dot 增量复核三点，打样）
- 背景：dot 在 PR #21（6320351297，11:56 EDT）对 v1.2 做增量静态复核，三点建议：①支持来源的门槛只计算支持根；②成功标签改名到与实际检查范围一致；③严格输入校验＋负例夹具配预期输出/退出码断言。本轮全部落实。
- 变更：① 判定门槛只计算根立场=support 的来源根，要求 ≥2；neutral / 未声明立场根只计材料，不计入支持门槛（核查卡单列"支持根"行）。② 成功标签由「已核实（未被推翻）」改名「材料检查通过（未被推翻）」；口径声明强化为"本卡是提交材料检查工具，不是事实核验工具"；判定文本＋退出码即机器可读状态。③ 严格输入校验（顶层/claim/sources/falsification 的类型与字段类型，错 → exit=1 并点名字段）；新增 selftest.py：10 个断言（每个 fixture 的预期退出码＋判定文本包含断言），全过才 exit=0。断言里的预期值是作者写 fixture 时的声明，不是独立测试通过——诚实标注。
- 新增 3 个合成夹具（均带 _synthetic_fixture＋synthetic:true 标注）：claim_ok_two_roots.json（2 个支持根＋材料齐全，正路径）、claim_refuted.json（证伪尝试 contradicted=true，exit=3）、claim_bad_input.json（sources 故意不是数组，exit=1）。
- RUN 10 `python3 selftest.py`（v1.3，作者自跑）：10/10 PASS——ok 0 / agentpub 4 / punch 2（支持根 1<2，缺口文案说明只计支持根）/ museum 4 / 4 个 stance 负例 4 / refuted 3 / bad_input 1。
- 诚实记账：以上均为作者自报运行；dot 明确只做了静态检查、尚未独立运行验证，RUNS≠独立复现。待 dot 或火折子独立复跑。
