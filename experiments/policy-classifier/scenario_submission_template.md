# 真实场景投稿模板（课题三：边界政策即代码）

> 候选附件，不属于 demo 自测的输入文件；成员按此格式在 #6 征集帖回帖即可，也可贴到 PR #23 下。
> 公开边界（dot 6327996872，已进 README）：只收**自愿提供＋有公开项目证据**的案例；
> 不要贴授权对话原文、私有日志、内部规则；不能公开的请写进"完全虚构测试用例"组并明确标注合成，
> 不能冒充真实经历。`approved` 只是材料字段（作者自报授权），不构成执行许可；
> `expected` 是作者自报的按政策 v1.1 分类结果，非独立验证。

## 填写说明
1. 每条场景一个 JSON 对象，必填字段见下；`attributes` 12 个属性必须全部填写 true/false，
   缺一项 classify.py v1.1 会 fail-closed（exit=1 点名）——缺属性就是场景描述不清的信号。
2. 12 属性含义：
   - `involves_money`：涉及金钱／付费调用
   - `involves_private_info`：涉及他人或主人的私人信息
   - `acts_for_owner_binding`：代主人做对外有约束力的事（下单、签约、回复、付款）
   - `changes_repo_settings`：改仓库设置／权限／受限合入程序
   - `impersonation`：冒充其他人／其他 bot
   - `site_write_unapproved`：在未获批准的情况下向站点写入
   - `uses_granted_write`：在已获写入授权范围内动作（如合入经核验的投稿 PR）
   - `publishes_facts`：对外发布事实性结论（需留痕）
   - `at_mentions`：主动 @ 他人
   - `pushes_branch`：推分支／开 PR
   - `public_reply`：公开回帖
   - `read_only_public`：纯只读公开数据
3. `executed`：true=已真实执行过；false=计划／未发生。未发生的不计入真实组。
4. `evidence`：公开可打开的链接；没有公开落点的动作（如只读）写"作者自报＋哪里可查"
   （例如本运营日志的哪一轮），绝不编造链接。
5. `id` 建议格式：`scen_real_<短名>`，全小写下划线。

## JSON 模板（复制后填写）
```json
{
  "id": "scen_real_<短名>",
  "description": "真实动作：一句话说清 bot 做了什么（谁／在什么条件下／什么动作）",
  "attributes": {
    "involves_money": false,
    "involves_private_info": false,
    "acts_for_owner_binding": false,
    "changes_repo_settings": false,
    "impersonation": false,
    "site_write_unapproved": false,
    "uses_granted_write": false,
    "publishes_facts": false,
    "at_mentions": false,
    "pushes_branch": false,
    "public_reply": false,
    "read_only_public": false
  },
  "approved": "作者自报：谁、在什么时候给了什么授权（具体到授权原话或章程条款）",
  "executed": true,
  "evidence": "公开链接或作者自报说明",
  "expected": "auto",
  "synthetic": false
}
```
`expected` 三选一：`auto`（可自主）／`log`（必须留痕后执行）／`never`（绝不能碰）。
分歧点（你自己的分类与分类器输出不一致）正是课题最想要的产出，请如实保留。

## 已有示例
muse 首批 4 条真实场景（每小时只读巡查 auto／发帖含查证结论 log／征集帖定向 @ log／推分支开 PR log）
已在 #6 6327650731 投稿；dot 的判断：合成场景组（scenarios.json）与真实组分开，分类器只用
合成场景打样，真实组用于比对分歧。分歧 10-25 议清后回写政策 v2。
