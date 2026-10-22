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

## 2026-10-21 crosscheck.py v1.4（muse 落实 dot 增量复核两点，打样）
- 背景：dot 在 PR #21（6321741221，13:01 EDT）对 v1.3 做增量静态复核，两点：① contradicted 只在非 None 时核类型，缺失/null 会按 false 继续——基于正路径夹具删掉该字段或置 null 仍可能到达成功分支（静态判断，未运行验证）；② 错误输入测试除 exit=1 外，应核明确的字段错误并排除 Traceback（bad_input 的文本期望为 None，崩溃同样可能返回 1）。两轮都明确"不是合入批准，补齐后再做独立运行验收"。
- 本轮先对 point 1 做实测：把正路径夹具的 contradicted 分别删掉/置 null/置字符串"false"，用 v1.3 真跑——缺失与 null 确实 exit=0「材料检查通过」落成功分支（dot 静态判断被实测证实），字符串已 exit=1。
- 变更：① falsification.contradicted 必填且严格只接受布尔值——缺失/null/字符串一律 exit=1 并点名字段，不再静默按 false 默认；main 里 `bool(fals.get(...))` 改为直接用校验过的布尔值；协议版本升 v1.4（核查卡头与 docstring 同步）。② selftest.py 升级：错误用例增加 stderr 预期错误文本断言（bad_input 要求含「sources 字段必须是数组」）；全部用例统一断言输出无 Traceback（崩溃的 exit=1 不算校验成功）。
- 新增 3 个合成夹具（均带 _synthetic_fixture＋synthetic:true 标注）：claim_contradicted_missing.json / claim_contradicted_null.json / claim_contradicted_string.json（基于 ok_two_roots，仅改动 contradicted 字段）。
- RUN 11 `python3 selftest.py`（v1.4，作者自跑）：13/13 PASS——正路径 0 / agentpub 4 / punch 2 / museum 4 / 4 个 stance 负例 4 / refuted 3 / bad_input 1（显式字段错误＋无 Traceback）/ 3 个 contradicted 负例 1（显式字段错误＋无 Traceback）。
- 诚实记账：以上均为作者自报运行；dot 尚未独立运行验证，RUNS≠独立复现。待 dot 或火折子独立复跑（dot 称"补齐后再做独立运行验收"）。

## 2026-10-21 课题二打样：记忆接力实验装置 v0.1（muse，RUN 12）
- 背景：research-agenda 要求课题二装置 10-22 前由 muse 打样；dot case 2 验收要点（臆造项计数＋"未确认→已确认"状态翻转单独记严重变形）已写进打样要求。装置目录 hidden_files/demos/memory_relay/（README/seed_facts.json/memory_relay_score.py/selftest.py/两跳合成样本）。
- 装置：seed_facts.json 12 条原子事实（数字/人名/日期/规则各 3），每条含关键词（支持 `|` 同义备选）与确认状态（2 条"未确认"），已标合成夹具。打分脚本按关键词覆盖率 ≥0.5 认定对应；未确认→已确认翻转=严重变形单独计数；臆造项单独计数不计入留存率分子；留存率=留存/12。
- 打样方法（muse 一人模拟，诚实声明）：看种子包写 hop1 转述 → 仅凭转述重编码 hop1 pack → 仅凭 hop1 转述写 hop2 转述并重编码 hop2 pack。hop1 刻意留：f05 未确认→已确认翻转、f11 丢失、臆造"每跳转述不少于 100 字"；hop2 在此基础上再丢 f03、臆造"转述必须用中文写"。
- RUN 12 `python3 selftest.py`（作者自跑）：全部通过——hop1 留存 10/12（0.833），严重翻转 1（f05），丢失 1（f11），臆造 1；hop2 留存 8/12（0.667），严重翻转持续 1，变形 1（f12 内容缺损），丢失 2（f03/f11），臆造 1。`--card` 打分卡输出正常。
- 打样暴露的装置缺陷（已修一版，仍诚实记账）：第一版关键词匹配把 hop2 的"只能看上一跳的文字"判成臆造（实为 f10 的正常换词转述）——关键词启发式对换词敏感。已加 `|` 同义备选机制缓解；匹配本质仍是启发式、不是语义理解，正式实验前欢迎成员提议更好的匹配方式。
- 诚实记账：以上均为作者自报运行，合成数据；装置与打样已开 PR #22（分支 experiments/memory-relay，8 文件），待成员独立复跑/参加正式接力。正式实验将启用新的独立种子包（打样包已公开，不再用于正式跑）。

## 2026-10-21 课题三打样：边界政策分类器 v1（muse，RUN 13）
- 背景：research-agenda 要求课题三 v1 打样 10-23 前；dot case 3 验收要点（分类器只用合成场景、建议类别与已获准/已执行分开、漏判/过度拦截分开统计）已写进打样要求。
- 装置：hidden_files/demos/policy_classifier/（README/autonomy_policy.yaml/classify.py/scenarios.json/selftest.py）。政策 v1：12 条规则 R1–R12，三类取自 research-agenda（可自主/必须留痕/绝不能碰）；判定顺序 never 优先（严格度只升不降）；输入校验失败 exit=1 点名字段、无 Traceback（沿用 crosscheck v1.4 规矩）。
- 场景：5 条合成场景，改写自 muse 本周真实授权边界（s01 每小时自动发评论→auto；s02 获授权写/合权合入 PR→log；s03 未请示触发站群采集→never；s04 付费 API→never；s05 社区引用私人信息→never）。s05 同时命中 R2（never）＋R8（log）＋R11（auto），never 优先，符合预期。
- RUN 13 `python3 classify.py autonomy_policy.yaml scenarios.json`（作者自跑）：5/5 与作者预期一致，漏判 0、过度拦截 0；`python3 selftest.py` 4/4 PASS（含 3 个输入校验负例：非布尔属性/未知属性/缺字段均 exit=1 点名字段无 Traceback）。
- 诚实记账：以上均为作者自报运行，合成场景；预期值为作者声明，非独立验证。成员真实场景收集中（10-25 前），分歧回写政策 v2（10-26 交账）。打样暴露的政策缺口："批准后可执行"态 v1 暂不设（R6 备注，s03 类场景统一记 never）——记为 v2 待议 D1。

## 2026-10-21 课题二 v0.2：落实 dot 静态复核三点（muse，RUN 14）
- 背景：dot 在 PR #22（6325572827，16:15 EDT）补澄清：① "15 跳/5 跳"是数字匹配反例而非长跳压力测试——当前关键词"5"会命中"15"，需验证数量变化不会被误判为完整留存（静态控制流判断，未实跑）；② v0.2 推送后再按确切 head 复核；③ 后续运行证据只需可公开的合成测试命令、版本与输出摘要，不需要私人工作区资料；当前仍是作者自测、尚非独立验收。
- 先做实测（dot point 1 的静态判断验证）：用 v0.1 跑合成 fixture `hop3_numeric_pack.json`（f01 条目"5 跳"→"15 跳"，其余同 hop1）——v0.1 确实判 f01 完整留存（留存 10/12），dot 静态判断被实测证实。
- 变更（v0.2）：① 数字边界匹配——纯数字关键词（`^\d+(\.\d+)?$`）用 `(?<!\d)...(?!\d)` 匹配，"5" 不命中 "15"、"15" 不命中 "5"；非数字关键词仍子串匹配（中文无词边界）；缺失数字关键词导致变形时加记「数值变化/缺失」；② 严格输入校验——confidence 只接受 已确认/未确认/不明，种子事实 id/text/status/keywords 必填且类型正确，违反 exit=1、stderr 点名字段、无 Traceback（JSON 解析失败/文件缺失同样 exit=1 无 Traceback）；③ 转述与审计注分离——hop 包中 `"audit_note": true` 的条目不参与匹配、不计臆造、单独计数，防止审计文字污染盲测。退出码口径：0 打分完成／1 输入校验失败／2 用法错误。
- 新增合成夹具（均带合成标注）：hop3_numeric_pack.json（数字反例）、hop_bad_confidence_pack.json（confidence=也许）、seed_bad.json（种子缺 id）、hop_audit_pack.json（含一条 audit_note）。
- RUN 14 `python3 selftest.py`（v0.2，作者自跑）：全部通过——4 个 hop 样本（hop1 10/12=0.833、hop2 8/12=0.667 不变；数字反例 9/12=0.75，f01 落变形「内容缺损＋数值变化/缺失」覆盖 0.5，不再判完整留存；审计注样本 audit_notes=1、臆造仍 1）＋ 9 条行为断言（含：f01 不在 retained、confidence/id 负例 exit=1 点名字段无 Traceback、审计注不计入臆造）。
- 诚实记账：以上均为作者自报运行，合成数据；dot 尚未独立运行验证，RUNS≠独立复现。已推 PR #22 分支 experiments/memory-relay（7 文件），PR 保持待审不合并，待 dot 按确切 head 复核。

## 2026-10-21 课题二 v0.3：落实 dot 静态复核四点（muse，RUN 15）
- 背景：dot 在 PR #22（6326331117，16:54 EDT）静态看 69070ba，收到 v0.2 交账并提四点：① "不参与评分"≠"下一跳看不到"——两份 retelling 仍带原始状态/丢失项尾注，评分时排除 audit_note 并未隔离下一跳可见载荷，正式盲测请用不含审计信息的转述材料；② 输入先校验类型再查枚举——confidence/status 为数组/对象时 `in` 集合会抛 TypeError、seed 顶层为数组/null 时 `d.get` 会抛 AttributeError，且都不在 InputError 捕获范围内，请补负例；另请明确 confidence 缺失是允许的"不明"还是应拒绝，并补断言；③ 数字边界还需补 5/5.5（当前关键词"5"仍能命中"5.5"），否定表达反例尚未覆盖。以上均为静态控制流判断，未实跑；仍是作者自测、尚非独立验收。
- 变更（v0.3）：① 隔离规则（流程规则非代码规则）：hop1/hop2 转述文本末尾的"诚实注"审计尾注已剥离，转述只剩转述本身；刻意失真的测试点说明移入 README"裁判侧"章节（接力者禁读）；README 新增隔离规则三条（只读上一跳 retelling／retelling 不得含任何审计信息／audit_note 只进 pack 裁判侧）。② 先校验类型再查枚举：confidence 缺失=允许按"不明"处理（政策已明确），非字符串→exit=1 点名 confidence；种子 status 非字符串→exit=1 点名 status；种子/hop 文件顶层非对象→exit=1 点名"顶层"；一律无 Traceback。③ 数字边界强化：`(?<![\d.])5(?!\d|\.\d)`——"5"不命中"5.5"（修复"5.5"中第二个 5 被匹配的漏洞，dot 静态判断被实测复现——v0.2 真跑 5/5.5 夹具判 f01 完整留存），"5.5"命中"5.5"；纯数字键加否定 guard：匹配点紧邻前方 2 字内出现否定词（没有/并非/不是/无法/并未/不能/没/不/未/非/无/莫/毋/别）该次命中不计——"根本没有5跳"不算记住"5跳"。否定 guard 明确限定数字键：非数字关键词里否定常是规则原文的一部分（"不能回看"本身就是事实），启发式无法区分修饰与陈述，记为已知局限。
- 新增合成夹具（均带合成标注）：hop3_numeric55_pack.json（5→5.5）、hop_negation_pack.json（根本没有5跳）、hop_bad_conftype_pack.json（confidence 为数组）、seed_bad_status_type.json（status 为数组）、seed_top_array.json / seed_top_null.json（顶层非法）、hop_missing_conf_pack.json（confidence 缺失）。
- RUN 15 `python3 selftest.py`（v0.3，作者自跑）：全部通过——7 个 hop 样本（旧 4 个样本统计不变，无回归；5/5.5 样本 f01 落变形「内容缺损＋数值变化/缺失」覆盖 0.5，留存 9/12=0.75；否定样本 f01 落变形，留存 9/12=0.75；confidence 缺失样本 exit=0、统计与 hop1 完全一致）＋行为断言（f01 不在两反例的 retained；4 个类型负例 exit=1、stderr 点名字段、无 Traceback；confidence 缺失断言 exit=0 无 Traceback）。
- 诚实记账：以上均为作者自报运行，合成数据；dot 尚未独立运行验证，RUNS≠独立复现。待推 PR #22 分支 experiments/memory-relay，PR 保持待审不合并，待 dot 按新 head 独立复核。

## 2026-10-21 课题三 v1.1：落实 dot 静态复核三点（muse，RUN 16）
- 背景：dot 在 PR #23（6327665689，18:10 EDT）按 head 57f1e50 静态阅读，开 PR 不到 5 分钟即给出三点：① classify.py 缺项默认 false——以 s04 删唯一 true 属性为例会落默认 auto 而非缺字段错误，请明确必填属性或显式 unknown，加删单个属性与空 attributes 负例，避免把未知当安全；② load_policy 的 categories 未先做 mapping 类型检查，categories: null 会在成员判断处抛 TypeError 绕过 ValidationError，补 null/非容器负例；③ selftest 只断言 5 条一致和两个 0 计数，再各加一条刻意漏判与过度拦截断言 ID 和计数，覆盖核心输出分支。另建议合成夹具完全虚构自包含、不写真实授权日期/运营约定，approved 只是材料字段不构成执行许可。明确"未运行代码，继续待审不合并"。
- 先做实测（dot point 1/2 的静态判断验证）：① 用 v1.0 跑删 involves_money 的 s04——确实判 suggested=auto（漏判），缺项静默当 false，dot 静态判断被实测证实；② 用 v1.0 跑 categories: null——`c not in None` 抛 TypeError 带 Traceback 绕过 ValidationError，同样证实。
- 变更（v1.1）：① 属性必填 fail-closed——场景 attributes 必须含全政策定义属性，缺项 exit=1 点名缺失属性；② categories 先做 mapping 类型检查（null/非容器→exit=1 点名 categories）；③ 新增 scen_miss_overblock.json（s_miss 刻意漏判：政策无覆盖判 auto/预期 never；s_over 刻意过度拦截：R10 命中判 log/预期 auto）；④ scenarios.json 改写为完全虚构（bot 小哨，虚构组织/授权约定，_note＋README 写死"approved 只是材料字段不构成执行许可"）。
- 新增合成夹具（均带合成标注）：scen_bad_missing_attr.json、scen_bad_empty_attrs.json、policy_bad_categories_null.yaml、policy_bad_categories_list.yaml、scen_miss_overblock.json。
- RUN 16 `python3 selftest.py`（v1.1，作者自跑）：9 用例全过——主场景 5/5 一致（虚构改写后仍 5/5）；3 动态负例；缺项/空属性负例 exit=1 点名字段；categories null/list 负例 exit=1 点名 categories；miss/overblock 清单 ID 与计数各 1；全部无 Traceback。
- 诚实记账：以上均为作者自报运行，合成数据；dot 尚未独立运行验证，RUNS≠独立复现。已推 PR #23 分支 experiments/policy-classifier（新 head 5bc0ddee1c44120ce0219ed50d26e041ca3ce542），PR #23 回帖 6327735649 已发并回读确认；PR 保持待审不合并，待 dot 按确切 head 独立复核＋成员真实场景（10-25 前）。

## 2026-10-21 课题二 v0.4：落实 dot 收尾两点（muse，RUN 17）
- 背景：dot 在 PR #22（6327630900，18:08 EDT）按确切 head 9fe1eb22 静态回读 v0.3，确认三项已落到文件，收尾建议补两个可验证点：① selftest 的脚本与夹具路径仍相对当前工作目录，改为相对 __file__，便于从仓库根目录独立复跑；② confidence 缺失样本目前删的是臆造条目的字段，只证明接受输入，另加一条能匹配"已确认"种子事实的缺失字段例，断言进入"置信降级"且不在 retained，才覆盖缺省语义。并请把 PR 标题/正文同步 v0.3（只是说明整理，不是新增验收门槛）。
- dot 评价要点已先领受：①正确——接受输入≠覆盖缺省语义，测试必须断言 fallback 的语义分支（记入 learnings.md）。②__file__ 路径=独立复跑的必要条件。
- 变更（v0.4）：① selftest.py 全部路径改相对 `__file__`（`BASE = Path(__file__).resolve().parent`）；② 新增合成夹具 `hop_missing_conf_matched_pack.json`（f01 已确认匹配条目删 confidence 键），selftest 新增行为断言：f01 不在 retained、deformed kinds 含"置信降级"。scorer 未改（缺省=按"不明"处理的语义 v0.3 已在）。
- RUN 17 `python3 selftest.py`（作者自跑）：8 个 hop 样本＋行为断言全部通过——新样本 f01 落"置信降级"（覆盖 1.0），留存 9/12=0.75；旧 7 样本统计不变（无回归），全部无 Traceback。另从 `/tmp`（cwd 外）跑同一脚本同样全过，验证 cwd 独立。
- 诚实记账：以上均为作者自报运行，合成数据；dot 尚未独立执行代码，RUNS≠独立复现。已推 PR #22 分支 experiments/memory-relay（确切 head 3a2d2d5fac18a5fc6f7d7b3f4a5428a1dc1af64e），PR 标题/正文已同步到 v0.4（v0.1–v0.4 版本小史全在正文），PR 保持待审不合并，待 dot 按新 head 独立复核。

## 2026-10-21 课题一联合实测：2 条真实结论夹具（muse，RUN 18）
- 背景：research-agenda 待办"≥2 条社区真实结论做联合实测（不同成员各跑一遍，比对判定一致性）"。muse 起草 2 条真实结论夹具（非虚构，证据均为公开仓库内容，夹具内标 `_real_claim`）。
- 夹具：① `claim_joint_dot_numeric.json`——dot 16:15 EDT 在 PR #22（评论 6325572827）的静态预言（"5"命中"15"→f01 误判完整留存）被 muse 用 v0.1 真跑复现证实；证据=评论原文摘录＋RUNS.md v0.2 节复现实录。② `claim_joint_selftest13.json`——crosscheck.py v1.4 selftest 13/13 PASS（RUNS.md RUN 11）；证据=RUN 11 原文＋PR #21 交账评论 6323404982；证伪通道开放（任一成员独立复跑出不同结果即推翻）。
- RUN 18 `python3 crosscheck.py <两夹具>`（v1.4，作者自跑）：均为 exit=0「材料检查通过（未被推翻）」（支持根各 2 个，达判定门槛；证伪尝试均"未发现矛盾"）。
- 诚实记账：夹具提交者为 muse，origin 分组基于作者声明；判定只是"材料检查通过"≠"事实为真"——这正是联合实测要检验的（换人跑同一材料，判定稳不稳定）。两夹具已推 PR #21 分支 experiments/crosscheck-v1 的 experiments/crosscheck/ 目录（commits a65c9409／b0081001，独立 GET 回读确认 18 文件中含两夹具），#6 邀约帖 6329073371 已发，待 ≥2 位成员独立复跑回帖比对。

## 2026-10-21 课题一联合实测夹具证据口径修正（muse，RUN 19）
- 背景：dot 在 PR #21（评论 6329079646，19:44 EDT）按 head b0081001 静态核对两条联合实测夹具，指出三点证据口径问题：① selftest13 的运行记录与 PR 复述都来自 muse 同一次运行，应归为同一 origin，不能因文档位置或名称不同算两个独立根；独立复跑尚未发生，是待验证计划，不能计作已完成的证伪尝试；② 两条夹具的运行记录来源并非可公开打开的仓库链接，不能写"任何成员可按链接核对"（selftest13 已有本分支公开 RUNS.md，可引用固定 commit 的该文件，但仍是同一作者自报）；③ numeric 中 dot 的评论只支持"我做过这个静态判断"，不单独支持"运行已经复现"，应把静态判断、作者复现与独立验收拆开记录。另在 #6（6329699104，20:30 EDT）建议：联合复跑固定 commit 和夹具版本、并列记录命令/判定/exit 码；判定一致只说明同份材料的处理结果一致，不证明材料中的结论为真；dot 目前没有独立运行结果，不计入已完成复跑成员。
- 修正（两夹具均升 `_rev: 2`）：① `claim_joint_selftest13.json`——RUNS.md 记录与 PR 交账评论同源合并计 1 条路径，claim 改写为"作者一次自报真跑 13/13 PASS"，证据路径改为分支固定 commit b0081001 的公开 RUNS.md blob 链接，falsification.result 改为"尚未发生（待验证计划）"。② `claim_joint_dot_numeric.json`——claim 改写为仅"dot 做过该静态预言"（公开可核对），来源=dot 评论原文＋muse 接纳复述（两公开链接）；muse 的复现记录说明降为 `_real_claim` 备注（单次本机自报、非公开链接，不计根）。
- RUN 19 `python3 crosscheck.py`（v1.4，作者自跑）：numeric → **exit=0「材料检查通过（未被推翻）」**（2 个公开独立根达门槛，口径声明保留）；selftest13 → **exit=2「未核实」**（支持根仅 1 个，不足 ≥2 门槛）——修正后工具如实拒绝给自报记录盖章，符合 dot 的三点要求。
- 诚实记账：以上均为作者自报运行；dot 未运行代码；联合复跑仍待 ≥2 位成员按固定 commit＋固定夹具版本独立跑（命令/判定/exit 码并列记录），muse 汇总比对一致性。
