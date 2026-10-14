---
title: "Harness 与 Conversation API"
---

<div class="section-kicker">PI DURABLE / R.1 · P. 172</div>

# Harness 与 Conversation API



包根路径及其子路径的每一个公开入口，以及它的返回内容和本书中的说明位置。



用这些表格查找方法，以及解释它的章节。签名有所简化：`ctx` 是每个异步方法都接收的取消 `Context`，类型参数则被省略。权威依据是 `src/index.ts` 及其重新导出的文件。



## 包根路径：函数与类



|导出|签名|作用|参见|
|---|---|---|---|
|`Harness.open`|`(storage, options, ctx)`|在一份存储上打开 Harness；如果注册表缺少内置任务，就抛出异常|1\.2（原书第13页）|
|`createRegistry`|`()`|新建注册表；其中已包含内置任务|7\.1（原书第103页）|
|`createSession`|`(storage)`|裸 Session：只有存储和提交，没有智能体运行机制|2\.2（原书第29页）|
|`MemoryStorage`|`new MemoryStorage()`|内存存储，退出即丢失；适合测试|9\.4（原书第152页）|
|`defineDoc`|`(definition)`|声明一种文档种类（每个所有者一份）|4\.1（原书第50页）|
|`defineDocFamily`|`(definition)`|声明一种拥有多个带键成员的文档种类|4\.2（原书第53页）|
|`defineEntry`|`(kind)`|声明一种条目种类，并带有 `is()` 类型检查|3\.1（原书第37页）|
|`defineTask`|`(definition)`|声明一个持久化任务；通过扩展注册它|5\.1（原书第63页）|
|`defineExtension`|`(extension)`|声明一个扩展（只添加类型）|7\.1（原书第103页）|
|`defineTool`|`(tool)`|声明一个工具；`args` 的类型由 `parameters` 推导|7\.4（原书第112页）|
|`section`|`(key, render, { tag })`|声明一个系统提示词区段；除非 `tag: false`，否则包裹在标签中|7\.5（原书第115页）|
|`hook`|`(task, handlers)`|按名称匹配，为内置或自定义任务附加处理器|7\.3（原书第109页）|
|`wrapTool`|`(tool, wrapper)`|在扩展被选中的所有位置，包装该名称对应的工具|7\.4（原书第112页）|
|`wrapSection`|`(key, wrapper)`|包装该键对应的提示词区段|7\.5（原书第115页）|
|`configure`|`(tx, conversationId, change)`|在你已有的提交内部更改对话的智能体|7\.2（原书第106页）|
|`watchEvents`|`(harness, conversationId, ctx)`|智能体事件流（运行、轮次、消息、工具调用）；实验性功能|8\.3（原书第133页）|
|`ReadAfterWrite, StorageRejected, ConversationBusy`|错误类|参见“错误与原因”（原书第183页）|2\.3（原书第33页）|



## 包根路径：标记与常量



|导出|类型|值|参见|
|---|---|---|---|
|`UserEntry, AssistantEntry, SystemEntry`|条目标记|`pi.user, pi.assistant, pi.system`|3\.1（原书第37页）|
|`ToolResultEntry, ResetEntry, CompactionEntry`|条目标记|`pi.tool-result, pi.reset, pi.compaction`|3\.1（原书第37页）|
|`AgentDoc, ProviderDoc, LiveDoc`|文档标记|`pi.agent, pi.provider, pi.live`|4\.4（原书第60页）|
|`InboxDoc, UsageDoc`|文档标记|`pi.inbox, pi.usage`|4\.4（原书第60页）|
|`GenerationTask, ToolTask, CompactionTask`|任务标记|`pi.generation, pi.tool, pi.compaction`|R\.2（原书第179页）|
|`ROOT_CONVERSATION_ID`|常量|`1`|2\.1（原书第25页）|
|`DEFAULT_RETRY_POLICY`|常量|参见“设置与默认值”（原书第180页）|6\.3（原书第91页）|
|`DEFAULT_COMPACTION_POLICY`|常量|参见“设置与默认值”（原书第180页）|6\.5（原书第97页）|
|`DEFAULT_PROGRESS_POLICY`|常量|参见“设置与默认值”（原书第180页）|6\.2（原书第88页）|



## 子路径导出



|导入路径|主要导出|参见|
|---|---|---|
|`.../env`|`ExecutionEnv, FileSystem, Shell, FileError, ExecutionError`，行扫描辅助函数|9\.5（原书第155页）|
|`.../env/node`|`NodeExecutionEnv`|9\.5（原书第155页）|
|`.../tools`|`CodingTools, createReadTool, createWriteTool, createEditTool, createBashTool`|7\.4（原书第112页）|
|`.../storage/memory`|`MemoryStorage`|9\.4（原书第152页）|
|`.../storage/sqlite`|`SqliteStorage, SqliteDatabase, applySqliteMigrations, SQLite_MIGRATIONS`|9\.2（原书第144页）|
|`.../storage/sqlite/node`|`openNodeSqliteStorage, openNodeSqliteDatabase`|9\.2（原书第144页）|
|`.../storage/jsonl`|`JsonlStorage, JsonlCorruptionError, JsonlStoragePoisonedError`|9\.3（原书第148页）|
|`.../storage/jsonl/node`|`openNodeJsonlStorage(directory, ctx, { fsync }?)`|9\.3（原书第148页）|
|`.../testing`|`registerStorageConformance, registerEnvConformance, createStorageConformance, createEnvConformance`|9\.4（原书第152页）|



`…` 代表 `@earendil-works/pi-durable`。依据 `package.json` 的导出和每个子路径的索引文件。



## Harness



|方法|签名|返回内容|参见|
|---|---|---|---|
|`resume`|`()`|开始运行任务；调用两次也是安全的；关闭后调用会抛出异常|5\.4（原书第73页）|
|`root`|`(ctx, { agent, init }?)`|根对话，首次使用时创建|3\.3（原书第43页）|
|`conversation`|`(id, ctx)`|`Conversation \| undefined`|3\.3（原书第43页）|
|`createConversation`|`({ ownership, agent?, init? }, ctx)`|`Conversation`，在一次提交中创建|3\.3（原书第43页）|
|`getTask`|`(id, ctx)`|`TaskRecord \| undefined`|5\.1（原书第63页）|
|`inspect`|`(ctx)`|`HarnessInspection`：未完成的任务和提交请求；不写入任何内容|8\.4（原书第137页）|
|`submission`|`(id, ctx)`|`Submission \| undefined`；重新打开后仍可使用|6\.1（原书第84页）|
|`abortSubmission`|`(id, ctx, conversationId?)`|`"aborted" \| "already_placed" \| "settled" \| "not_found"`|6\.1（原书第84页）|
|`abortTask`|`(id, ctx)`|`"marked" \| "terminal"`|5\.6（原书第80页）|
|`waitForTask`|`(id, ctx)`|任务结束后的 `SettledTask`|5\.1（原书第63页）|
|`waitForIdle`|`(ctx)`|所有位置都没有剩余前台工作时完成|5\.5（原书第76页）|
|`usage`|`(ctx)`|`UsageState`：所有对话的 token 和费用总计|6\.6（原书第100页）|
|`taskGraph`|`(ctx)`|未完成任务的实时只读树；使用完毕后需释放|8\.4（原书第137页）|
|`watchTaskGraph`|`(ctx)`|`TaskGraphWatch`|8\.4（原书第137页）|



## Session 方法（由 Harness 继承）



|方法|签名|返回内容|参见|
|---|---|---|---|
|`commit`|`(change: (tx) => T, ctx)`|提交存储后返回 `T`|2\.2（原书第29页）|
|`close`|`(ctx)`|停止接收新工作，等待正在执行的代码，然后关闭存储|2\.3（原书第33页）|
|`subscribeCommits`|`(listener)`|取消订阅函数；监听器同步看到每一次提交|2\.2（原书第29页）|
|`subscribeClose`|`(listener)`|取消订阅函数；开始关闭时调用监听器|2\.2（原书第29页）|
|`snapshot`|`(token, owner?, key?, ctx)`|当前已提交值，只读；也可能为 `undefined`|4\.2（原书第53页）|
|`snapshotAsOf`|`(token, conversationId, key?, at, ctx)`|某个条目时刻的值；仅适用于可回溯文档|4\.3（原书第56页）|
|`documentState`|`(token, owner?, key?, ctx)`|跟随提交变化的实时只读值；使用完毕后需释放|8\.1（原书第125页）|
|`watchDoc`|`(token, owner?, key?, ctx)`|`DocumentWatch \| undefined`：每次变更调用一次回调|8\.1（原书第125页）|



`owner` 参数根据标记的作用域，取对话 ID 或任务 ID；Session 作用域不提供该参数。`key` 用于文档族。



## Conversation



|方法|签名|返回内容|参见|
|---|---|---|---|
|`id`|属性|`ConversationId`；用它比较对话|3\.3（原书第43页）|
|`agent`|`(ctx)`|此刻运行时会使用的 `Agent`；不写入任何内容|7\.2（原书第106页）|
|`configure`|`(change, ctx)`|在独立提交中，更改模型、工具、扩展或 `cwd`|7\.2（原书第106页）|
|`submit`|`(draft, ctx)`|输入提交后返回 `Submission`|6\.1（原书第84页）|
|`reset`|`(handoff?, ctx)`|开始一个新的上下文，可选择携带交接消息|3\.4（原书第46页）|
|`compact`|`(instructions?, ctx)`|摘要任务的 `TaskId<CompactionResult>`|6\.5（原书第97页）|
|`commit`|`(change, ctx)`|一次提交，其中新建任务默认归属于此对话|2\.2（原书第29页）|
|`context`|`(ctx)`|`ContextView`：活动条目，以及模型将看到的消息|3\.2（原书第40页）|
|`entries`|`(query, limit, cursor, ctx)`|一页条目，最新的在前，包括继承的条目|3\.1（原书第37页）|
|`fork`|`(at, { ownership, agent?, init? }, ctx)`|新的 `Conversation`|3\.3（原书第43页）|
|`abort`|`(ctx, { background }?)`|停止正在运行的工作，并撤回排队输入；空闲时完成|5\.6（原书第80页）|
|`waitForIdle`|`(ctx)`|没有剩余前台工作时完成|5\.5（原书第76页）|
|`viewState`|`(ctx)`|供 UI 使用的实时只读 `ConversationView`|8\.2（原书第129页）|
|`watch`|`(ctx)`|`ConversationWatch`：每次变更调用一次回调|8\.2（原书第129页）|



## Submission 与 ConversationHandle



|成员|签名|返回内容|参见|
|---|---|---|---|
|`Submission.id`|属性|`SubmissionId`；保留它，以便重启后找到提交请求|6\.1（原书第84页）|
|`Submission.status`|`(ctx)`|此刻的已存储记录|6\.1（原书第84页）|
|`Submission.wait`|`(ctx)`|达到 `done` 或 `unanswered` 后的记录|6\.1（原书第84页）|
|`Submission.abort`|`(ctx)`|`"aborted" \| "already_placed" \| "settled"`|6\.1（原书第84页）|
|`ConversationHandle.submit`|`(inputDraft, ctx)`|从任务内部提交用户输入；不支持 `write` 提交请求|7\.7（原书第121页）|
|`ConversationHandle.abort`|`(ctx, { background }?)`|同 `Conversation.abort`|7\.7（原书第121页）|
|`ConversationHandle.waitForIdle`|`(ctx)`|同 `Conversation.waitForIdle`|7\.7（原书第121页）|



`ConversationHandle` 来自 `runtime.conversation()` 或 `api.conversation()`，并在本次调用结束后拒绝操作。



## Tx：提交回调的接口



|方法|签名|返回内容|参见|
|---|---|---|---|
|`conversation, entry, task`|`(id)`；`entry(token, id)`|对应记录或 `undefined`（读表）|2\.2（原书第29页）|
|`scanConversations`|`(query, limit, cursor?)`|一页对话，按所有者过滤|7\.7（原书第121页）|
|`scanEntries`|`(query, limit, cursor?)`|一页条目，最新的在前|3\.1（原书第37页）|
|`latestHeadMarker`|`(conversationId)`|设定当前上下文起点的条目|3\.4（原书第46页）|
|`scanTasks`|`(query, limit, cursor?)`|一页任务记录|5\.1（原书第63页）|
|`submissionByRequest`|`(conversationId, requestId)`|记录或 `undefined`|6\.1（原书第84页）|
|`createConversation`|`({ ownership })`|`ConversationRecord`；在 Harness 中还会创建内置文档|3\.3（原书第43页）|
|`forkConversation`|`(parentId, at, { ownership })`|`ConversationRecord`|3\.3（原书第43页）|
|`appendEntry`|`(conversationId, draft)` 或 `(token, ...)`|`EntryRecord`（写表）|3\.1（原书第37页）|
|`createTask`|`(task, input, options)`|`TaskId`（写表）|5\.1（原书第63页）|
|`createSubmission`|`(create)`|原始记录，跳过繁忙和队列规则|6\.1（原书第84页）|
|`settleSubmission`|`(id, settlement)`|将它标记为 `done` 或 `unanswered`|6\.1（原书第84页）|
|`placeSubmission`|`(id, entry)`|记录它的落点：输入变为 `placed`，写入变为 `done`|6\.1（原书第84页）|
|`doc`|`(token, owner?, key?, seed?)`|可编辑草稿；文档不存在时会创建|4\.2（原书第53页）|
|`retireDoc`|`(token, owner?, key?)`|结束该文档；之后的 `doc()` 会创建新文档|4\.2（原书第53页）|



## TaskRuntime：一次任务调用



|成员|签名|返回内容|参见|
|---|---|---|---|
|`taskId, conversationId`|属性|任务及其所属对话的标识|5\.1（原书第63页）|
|`signal`|属性|`AbortSignal`：中止、关闭或本次处理器运行结束时触发|5\.6（原书第80页）|
|`registry`|属性|本阶段开始时的注册表|7\.6（原书第118页）|
|`settings, models`|属性|每次访问都重新读取的设置；pi\-ai 的 `Models`|7\.2（原书第106页）|
|`agent`|`(ctx)`|对话的 `Agent`，在本阶段内固定|7\.2（原书第106页）|
|`env`|`(ctx)`|对话的环境，或 `undefined`|9\.5（原书第155页）|
|`hooks`|`.each(name, invoke)`|按顺序调用每个已选扩展的处理器|7\.3（原书第109页）|
|`commit`|`((tx, current) => next?, ctx)`|提交；返回新状态以推进任务|5\.1（原书第63页）|
|`memo`|`(name, ctx), (name, candidate, ctx)`|一个已存储的小值；首次写入胜出|5\.2（原书第67页）|
|`getTask, waitForTask`|`(id, ctx)`|记录；完成后的记录|5\.5（原书第76页）|
|`outcomes`|`(ids, ctx)`|已完成任务的结果；如果有任务尚未完成，则拒绝|5\.5（原书第76页）|
|`conversation`|`(id, ctx)`|`ConversationHandle \| undefined`|7\.7（原书第121页）|
|`entry`|`(id, ctx), (token, id, ctx)`|此对话可见的已提交条目|3\.1（原书第37页）|
|`context`|`(conversationId, ctx, at?)`|模型会看到的内容；可选取条目 `at` 时刻的内容|3\.2（原书第40页）|
|`now, sleep`|`()`；`(until, ctx)`|Harness 的时钟；等待至某个时刻|5\.2（原书第67页）|
|`report`|`(error)`|将非致命错误传递给 `onReport`|7\.3（原书第109页）|
|`snapshot, snapshotAsOf, watchDoc`|同 Session|已提交值；处理器结束时监听停止|8\.1（原书第125页）|



## ToolExecutionApi：一次工具调用



|成员|签名|返回内容|参见|
|---|---|---|---|
|`taskId, conversationId, callId`|属性|工具任务、其所属对话，以及模型给出的调用 ID|7\.4（原书第112页）|
|`registry`|属性|本次调用时的注册表|7\.6（原书第118页）|
|`agent`|`(ctx)`|发起调用的对话所使用的智能体|7\.2（原书第106页）|
|`env`|属性|为本次调用构造的环境，或 `undefined`|9\.5（原书第155页）|
|`output`|`(chunk, skipped?)`|运行过程中向 UI 流式传送输出|7\.4（原书第112页）|
|`outputWindow`|属性|保留多少输出尾部，以及多长时间提交一次；也可能为 `undefined`|9\.5（原书第155页）|
|`diagnostic`|`(diagnostic)`|添加一条随结果一起供模型查看的备注|7\.4（原书第112页）|
|`details`|`(value, ctx)`|替换运行时显示的结构化详情|7\.4（原书第112页）|
|`commit`|`(change, ctx)`|代表本次工具调用所做的提交|7\.4（原书第112页）|
|`memo`|同 TaskRuntime|一个已存储的小值；首次写入胜出|5\.2（原书第67页）|
|`createTask`|`(task, input, options, ctx)`|子任务的 `TaskId`|5\.5（原书第76页）|
|`getTask, waitForTask`|`(id, ctx)`|记录；完成后的记录|5\.5（原书第76页）|
|`conversation`|`(id, ctx)`|`ConversationHandle \| undefined`|7\.7（原书第121页）|
|`snapshot, snapshotAsOf, watchDoc`|同 Session|已提交值|8\.1（原书第125页）|



## Registry



|成员|签名|返回内容|参见|
|---|---|---|---|
|`install`|`(extension)`|添加扩展，或替换同名扩展；立即生效|7\.1（原书第103页）|
|`uninstall`|`(extension)`|移除该名称的扩展|7\.1（原书第103页）|
|`snapshot`|`()`|当前已安装内容的冻结视图|7\.1（原书第103页）|
|`subscribe`|`(listener)`|取消订阅函数；每次变更后调用监听器|7\.6（原书第118页）|
|快照的 `installed, extension`|`()`；`(name)`|按安装顺序排列的扩展；按名称取得一个扩展|7\.1（原书第103页）|
|快照的 `tools, sections`|`()`|每个已安装的工具或提示词区段，连同其所属扩展|7\.1（原书第103页）|
|快照的 `tasks, task`|`()`；`(name)`|内置和已安装的任务定义|5\.4（原书第73页）|



来源：`src/index.ts`；`src/types.ts`（`Tx, Session, TaskRuntime, Storage`）；`src/harness/types.ts`（`Conversation, Harness, Submission, ConversationHandle, ToolExecutionApi, Registry`）；`src/harness/harness.ts`（`Harness.open`）；`src/harness/define.ts`；`src/harness/registry.ts`；`package.json` 的导出；spec §2\.2。
