---
title: "内置种类"
---

<div class="section-kicker">PI DURABLE / R.2 · P. 179</div>

# 内置种类



六种条目、五种文档和三种任务承载着每一次运行；它们全部使用保留的 `pi.` 前缀命名。



种类是随每条记录一起存储的名称，因此绝不能改变。`pi.` 前缀只是约定上保留；重复使用它会与 Harness 冲突，参见“容易踩坑的契约”（原书第163页）。代码中用来命名各个种类的标记列于 R\.1（原书第172页）。



## 条目种类



|种类|模型消息|写入者|参见|
|---|---|---|---|
|`pi.user`|`[UserMessage]`|提交请求、`onYield` 的继续运行|3\.1（原书第37页）|
|`pi.assistant`|`[AssistantMessage]`，任何停止原因|生成任务|6\.3（原书第91页）|
|`pi.system`|`[SystemMessage]`，`content: ""`|生成准备阶段|7\.5（原书第115页）|
|`pi.tool-result`|`[ToolResultMessage]`；`data: { diagnostics }`|工具任务；对于未提供的调用，由生成任务写入|6\.4（原书第94页）|
|`pi.reset`|无，或作为交接的 `[UserMessage]`；`head: "self"`|`reset()`、交接控制|3\.4（原书第46页）|
|`pi.compaction`|`[UserMessage]` 摘要；`head` = 第一个保留条目；`data: { reason }`|压缩任务|6\.5（原书第97页）|



## 文档种类



|种类|历史 · 分叉|何时存储完整副本|保存内容|参见|
|---|---|---|---|---|
|`pi.agent`|`rewindable · asOf`|每次变更|模型、思考级别、扩展和工具名称、指令、`cwd`|7\.2（原书第106页）|
|`pi.provider`|`latest · initial`|每次变更|`sessionId`，一个 UUIDv7|6\.3（原书第91页）|
|`pi.live`|`latest · initial`|没有任何运行中的工作时|运行、生成、工具、压缩|6\.2（原书第88页）|
|`pi.inbox`|`latest · initial`|为空时|`items`：排队中的引导输入、后续输入、写入|6\.1（原书第84页）|
|`pi.usage`|`latest · initial`|每次变更|按提供商／模型划分的模型用量，按名称划分的工具用量|6\.6（原书第100页）|



这五个文档都归属于一段对话，与该对话（或其分叉）一起创建，并以 `docs["pi.…"]` 的形式出现在其视图中。“何时存储完整副本”转述了各自的 `checkpointWhen`；两次副本之间只存储变更。



## 任务种类



|种类|阶段|职责|参见|
|---|---|---|---|
|`pi.generation`|`prepare, request, retry, poll, tools`|构造提示词、调用模型、重试、启动工具调用|6\.3（原书第91页）|
|`pi.tool`|`call, execute`|检查参数、运行钩子、提交意图、运行工具、提交结果|6\.4（原书第94页）|
|`pi.compaction`|`select, summarize, retry`|选择旧条目、生成摘要、添加摘要|6\.5（原书第97页）|



每个注册表都包含这三个任务；不能移除或替换它们。



来源：`src/entries.ts`；`src/harness/agent.ts, provider.ts, live.ts, inbox.ts, usage.ts`（文档定义）；`src/harness/generation.ts, tool.ts, compaction.ts`（阶段）；`src/harness/registry.ts`（`BUILTIN_TASKS`）；spec §2\.2、§8、§8\.1。
