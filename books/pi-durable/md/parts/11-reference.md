:::note
R.1 Harness 与会话 API 172 R.2 内置 kind 179 R.3 设置与默认值 180 R.4 错误与原因 183 R.5 术语表 185 R.6 资料来源 187 R.7 插图索引 189
:::

<a id="sec-R-1"></a>

## R.1 Harness 与会话 API

> 包根及其各子路径上的每一个公开入口，附上它的返回值和书中讲解它的那一节。

用这些表找到某个方法以及讲解它的那一节。签名经过缩短：`ctx` 是每个异步方法都接收的取消用 `Context`，类型参数已省略。事实来源是 `src/index.ts` 及其重新导出的文件。

### 包根：函数与类

:::note
`Harness.open (storage, options, ctx)` 在一个 storage 上打开 Harness；若注册表缺少内置任务则抛出 1.2 (p. 13)
:::

```
createRegistry () a new registry; it already holds the built-in tasks 7.1
```

:::note
(p. 103)
:::

```
createSession (storage) a bare Session: storage and commits, no agent machinery
```

:::note
2.2 (p. 29)
:::

```
MemoryStorage new MemoryStorage() in-memory storage, lost on exit; good for tests 9.4
```

:::note
(p. 152) `defineDoc (definition)` 声明一个文档 kind（每个 owner 一个）4.1 (p. 50) `defineDocFamily (definition)` 声明一个带许多带键成员的文档 kind 4.2 (p. 53)
:::

```
defineEntry (kind) declare an entry kind, with an is() type check 3.1
(p. 37) defineTask (definition) declare a durable task; register it through an extension 5.1 (p. 63) defineExtension (extension) declare an extension (adds types only) 7.1 (p. 103) defineTool (tool) declare a tool; args are typed from parameters 7.4 (p. 112)
```

```
section (key, render, { tag }?) declare a system-prompt section; wrapped in <key> tags unless tag: false
7.5 (p. 115) hook (task, handlers) attach handlers to a built-in or custom task, matched by name 7.3 (p. 109) wrapTool (tool, wrapper) wrap the tool with that name wherever the extension is selected 7.4 (p. 112) wrapSection (key, wrapper) wrap the section with that key 7.5 (p. 115) configure (tx, conversationId, change) change a conversation’s agent inside a commit you already have 7.2 (p. 106) watchEvents (harness, conversationId, ctx) stream of agent events (runs, turns, messages, tool calls); experimental 8.3 (p. 133) ReadAfterWrite, StorageRejected, ConversationBusy error classes see errors and reasons (p. 183) 2.3 (p. 33)
```

### 包根：词元与常量

:::note
`UserEntry`、`AssistantEntry`、`SystemEntry` 条目词元 `pi.user`、`pi.assistant`、`pi.system` 3.1 (p. 37) `ToolResultEntry`、`ResetEntry`、`CompactionEntry` 条目词元 `pi.tool-result`、`pi.reset`、`pi.compaction` 3.1 (p. 37) `AgentDoc`、`ProviderDoc`、`LiveDoc` 文档词元 `pi.agent`、`pi.provider`、`pi.live` 4.4 (p. 60) `InboxDoc`、`UsageDoc` 文档词元 `pi.inbox`、`pi.usage` 4.4 (p. 60) `GenerationTask`、`ToolTask`、`CompactionTask` 任务词元 `pi.generation`、`pi.tool`、`pi.compaction` R.2 (p. 179) `ROOT_CONVERSATION_ID` 常量 1 2.1 (p. 25) `DEFAULT_RETRY_POLICY` 常量 见设置与默认值 (p. 180) 6.3 (p. 91) `DEFAULT_COMPACTION_POLICY` 常量 见设置与默认值 (p. 180) 6.5 (p. 97) `DEFAULT_PROGRESS_POLICY` 常量 见设置与默认值 (p. 180) 6.2 (p. 88)
:::

### 子路径导出

:::note
`…/env` `ExecutionEnv`、`FileSystem`、`Shell`、`FileError`、`ExecutionError`、按行扫描的辅助函数 9.5 (p. 155) `…/env/node` `NodeExecutionEnv` 9.5 (p. 155) `…/tools` `CodingTools`、`createReadTool`、`createWriteTool`、`createEditTool`、`createBashTool` 7.4 (p. 112) `…/storage/memory` `MemoryStorage` 9.4 (p. 152) `…/storage/sqlite` `SqliteStorage`、`SqliteDatabase`、`applySqliteMigrations`、`SQLITE_MIGRATIONS` 9.2 (p. 144) `…/storage/sqlite/node` `openNodeSqliteStorage`、`openNodeSqliteDatabase` 9.2 (p. 144) `…/storage/jsonl` `JsonlStorage`、`JsonlCorruptionError`、`JsonlStoragePoisonedError` 9.3 (p. 148) `…/storage/jsonl/node` `openNodeJsonlStorage(directory, ctx, { fsync }?)` 9.3 (p. 148) `…/testing` `registerStorageConformance`、`registerEnvConformance`、`createStorageConformance`、`createEnvConformance` 9.4 (p. 152) `…` 代表 `@earendil-works/pi-durable`。取自 `package.json` 的 exports 字段和各子路径的 index 文件。
:::

### `Harness`

:::note
`resume ()` 开始运行任务；可安全调用两次；close 之后调用会抛出 5.4 (p. 73) `root (ctx, { agent, init }?)` 根会话，首次使用时创建 3.3 (p. 43) `conversation (id, ctx)` `Conversation` | `undefined` 3.3 (p. 43) `createConversation ({ ownership, agent?, init? }, ctx)` `Conversation`，在一次提交中创建 3.3 (p. 43) `getTask (id, ctx)` `TaskRecord` | `undefined` 5.1 (p. 63)
:::

```
inspect (ctx) HarnessInspection: unfinished tasks and submissions; writes nothing
8.4 (p. 137) submission (id, ctx) Submission | undefined; works after a reopen 6.1 (p. 84) abortSubmission (id, ctx, conversationId?) "aborted" | "already_placed" | "settled" | "not_found" 6.1 (p. 84) abortTask (id, ctx) "marked" | "terminal" 5.6 (p. 80) waitForTask (id, ctx) SettledTask, once the task has finished 5.1 (p. 63) waitForIdle (ctx) resolves when no foreground work is left anywhere 5.5 (p. 76)
```

```
usage (ctx) UsageState: token and cost totals of all conversations 6.6
(p. 100) taskGraph (ctx) live, read-only tree of unfinished tasks; dispose when done 8.4 (p. 137) watchTaskGraph (ctx) TaskGraphWatch 8.4 (p. 137)
```

### `Session` 方法（`Harness` 继承）

```ts
commit (change: (tx) => T, ctx) T, once the commit is stored 2.2 (p. 29)
close (ctx) stop new work, wait for running code, close storage 2.3 (p. 33)
subscribeCommits (listener) unsubscribe function; listener sees every commit, synchronously 2.2 (p. 29)
subscribeClose (listener) unsubscribe function; called when close begins 2.2 (p. 29)
snapshot (token, owner?, key?, ctx) current committed value, read-only, or undefined 4.2 (p. 53) snapshotAsOf (token, conversationId, key?, at, ctx) value as of an entry; rewindable documents only 4.3 (p. 56) documentState (token, owner?, key?, ctx) live read-only value that follows commits; dispose when done 8.1 (p. 125)
```

```
watchDoc (token, owner?, key?, ctx) DocumentWatch | undefined: one callback per change 8.1 (p. 125)
```

:::note
`owner` 参数按词元的作用域是会话 ID 或任务 ID，`Session` 作用域下不存在；`key` 只对族有效。
:::

### `Conversation`

:::note
`id` 属性 `ConversationId`；用它比较会话 3.3 (p. 43) `agent (ctx)` 它现在会带着运行的 `Agent`；不写入任何东西 7.2 (p. 106) `configure (change, ctx)` 在它自己的提交里更改模型、工具、扩展或 cwd 7.2 (p. 106) `submit (draft, ctx)` 输入提交之后的 `Submission` 6.1 (p. 84) `reset (handoff?, ctx)` 开始一份全新的上下文，可带一条交接消息 3.4 (p. 46) `compact (instructions?, ctx)` 摘要任务的 `TaskId<CompactionResult>` 6.5 (p. 97)
:::

```
commit (change, ctx) a commit where new tasks default to this conversation 2.2 (p. 29)
context (ctx) ContextView: active entries and the messages the model will see 3.2 (p. 40)
```

:::note
`entries (query, limit, cursor, ctx)` 一页条目，最新在前，包含继承来的 3.1 (p. 37)
:::

```
fork (at, { ownership, agent?, init? }, ctx) the new Conversation 3.3 (p. 43)
abort (ctx, { background }?) stop running work and withdraw queued inputs; resolves when idle 5.6 (p. 80) waitForIdle (ctx) resolves when no foreground work is left 5.5 (p. 76) viewState (ctx) live read-only ConversationView for a UI 8.2 (p. 129)
```

```
watch (ctx) ConversationWatch: one callback per change 8.2 (p. 129)
```

### `Submission` 与 `ConversationHandle`

:::note
`Submission.id` 属性 `SubmissionId`；留存它以便重启之后找回该提交项 6.1 (p. 84) `Submission.status (ctx)` 当前的已存储记录 6.1 (p. 84) `Submission.wait (ctx)` 完成或无人应答之后的记录 6.1 (p. 84) `Submission.abort (ctx)` `"aborted"` | `"already_placed"` | `"settled"` 6.1 (p. 84) `ConversationHandle.submit (inputDraft, ctx)` 从任务内部提交用户输入；不写入 7.7 (p. 121) `ConversationHandle.abort (ctx, { background }?)` 同 `Conversation.abort` 7.7 (p. 121) `ConversationHandle.waitForIdle (ctx)` 同 `Conversation.waitForIdle` 7.7 (p. 121) `ConversationHandle` 来自 `runtime.conversation()` 或 `api.conversation()`，并在这次调用结束后失效。
:::

### `Tx`，提交回调的接口面

:::note
(id); `entry(token, id)` 该记录或 `undefined`（一次表读取）2.2 (p. 29) `conversation`、`entry`、`task` `scanConversations (query, limit, cursor?)` 一页会话，按 owner 过滤 7.7 (p. 121) `scanEntries (query, limit, cursor?)` 一页条目，最新在前 3.1 (p. 37) `latestHeadMarker (conversationId)` 设下当前上下文起点的条目 3.4 (p. 46) `scanTasks (query, limit, cursor?)` 一页任务记录 5.1 (p. 63) `submissionByRequest (conversationId, requestId)` 记录或 `undefined` 6.1 (p. 84) `createConversation ({ ownership })` `ConversationRecord`；在 `Harness` 中还会创建内置文档 3.3 (p. 43) `forkConversation (parentId, at, { ownership })` `ConversationRecord` 3.3 (p. 43) `appendEntry (conversationId, draft)` 或 `(token, …)` `EntryRecord`（一次表写入）3.1 (p. 37) `createTask (task, input, options)` `TaskId`（一次表写入）5.1 (p. 63) `createSubmission (create)` 原始记录，跳过繁忙与排队规则 6.1 (p. 84) `settleSubmission (id, settlement)` 把它标记为完成或无人应答 6.1 (p. 84)
:::

```
placeSubmission (id, entry) record where it landed: input placed, write done 6.1 (p. 84)
doc (token, owner?, key?, seed?) an editable draft; creates the document if absent 4.2 (p. 53)
```

```
retireDoc (token, owner?, key?) end the document; a later doc() creates a new one 4.2 (p. 53)
```

### `TaskRuntime`，一次任务调用

:::note
`taskId`、`conversationId` 属性 该任务及其会话的身份 5.1 (p. 63)
:::

```
signal property AbortSignal: fires on abort, close, or when this run of the handler ends 5.6 (p. 80)
registry property the registry as it was when this phase started 7.6 (p. 118) settings, models properties settings re-read on each access; pi-ai Models 7.2 (p. 106) agent (ctx) the conversation’s Agent, fixed for this phase 7.2 (p. 106) env (ctx) the conversation’s environment, or undefined 9.5 (p. 155)
```

:::note
`hooks.each(name, invoke)` 按顺序调用每个被选中扩展的处理器 7.3 (p. 109)
:::

```ts
commit ((tx, current) => next?, ctx) commit; return a new state to move the task on 5.1 (p. 63)
memo (name, ctx), (name, candidate, ctx) a small stored value; the first write wins 5.2 (p. 67) getTask, waitForTask (id, ctx) the record; the record once finished 5.5 (p. 76) outcomes (ids, ctx) results of finished tasks; rejects if one is unfinished 5.5 (p. 76) conversation (id, ctx) ConversationHandle | undefined 7.7 (p. 121) entry (id, ctx), (token, id, ctx) a committed entry this conversation can see 3.1 (p. 37) context (conversationId, ctx, at?) what the model would see, optionally as of entry at 3.2 (p. 40) now, sleep (); (until, ctx) the Harness clock; wait until a time 5.2 (p. 67) report (error) pass a non-fatal error to onReport 7.3 (p. 109) snapshot, snapshotAsOf, watchDoc as on Session committed values; watches stop when the handler ends 8.1 (p. 125)
```

### `ToolExecutionApi`，一次工具调用

:::note
`taskId`、`conversationId`、`callId` 属性 该工具任务、它的会话，以及模型的调用 ID 7.4 (p. 112) `registry` 属性 本次调用时的注册表 7.6 (p. 118) `agent (ctx)` 发起调用的会话的 `Agent` 7.2 (p. 106) `env` 属性 为本次调用构建，或 `undefined` 9.5 (p. 155) `output (chunk, skipped?)` 运行期间把输出流向 UI 7.4 (p. 112) `outputWindow` 属性 保留多少输出尾部、多久提交一次，或 `undefined` 9.5 (p. 155) `diagnostic (diagnostic)` 加一条模型会随结果看到的说明 7.4 (p. 112) `details (value, ctx)` 替换运行期间展示的结构化详情 7.4 (p. 112) `commit (change, ctx)` 代这次工具调用所做的一次提交 7.4 (p. 112) `memo` 同 `TaskRuntime`：一个小的存储值；先写入者胜 5.2 (p. 67) `createTask (task, input, options, ctx)` 子任务的 `TaskId` 5.5 (p. 76) `getTask`、`waitForTask (id, ctx)` 该记录；结束之后的记录 5.5 (p. 76) `conversation (id, ctx)` `ConversationHandle` | `undefined` 7.7 (p. 121) `snapshot`、`snapshotAsOf`、`watchDoc` 同 `Session` 上的已提交值 8.1 (p. 125)
:::

### `Registry`

:::note
`install (extension)` 添加一个扩展，或替换同名的那个；立即生效 7.1 (p. 103) `uninstall (extension)` 移除那个名字的扩展 7.1 (p. 103) `snapshot ()` 当前已安装内容的冻结视图 7.1 (p. 103)
:::

```ts
subscribe (listener) unsubscribe function; called after every change 7.6 (p. 118)
snapshot installed, extension (); (name) extensions in install order; one by name 7.1 (p. 103) snapshot tools, sections () every installed tool or section with its extension 7.1 (p. 103) snapshot tasks, task (); (name) built-in and installed task definitions 5.4 (p. 73)
```

```
Sources: src/index.ts; src/types.ts (Tx, Session, TaskRuntime, Storage); src/harness/types.ts (Conversation, Harness, Submission,
```

:::note
`ConversationHandle`、`ToolExecutionApi`、`Registry`）；`src/harness/harness.ts`（`Harness.open`）；`src/harness/define.ts`；`src/harness/registry.ts`；`package.json` 的 exports；spec §2.2
:::

<a id="sec-R-2"></a>

## R.2 内置 kind

> 六种条目 kind、五种文档 kind 和三种任务 kind 承载每一次运行；全部以保留的 `pi.` 前缀命名。

kind 是随每条记录一起存储的名字，因此绝不能改动。`pi.` 前缀只是按约定保留的；复用它会与 `Harness` 冲突（会咬人的契约 (p. 163)）。代码中为每种 kind 命名的词元列在 R.1 (p. 172)。

### 条目 kind

:::note
`pi.user` `[UserMessage]` 提交项、`onYield` 续延 3.1 (p. 37) `pi.assistant` `[AssistantMessage]`、任意停止原因 生成 6.3 (p. 91)
:::

```
pi.system [SystemMessage], content: "" generation preparation 7.5 (p. 115)
pi.tool-result [ToolResultMessage]; data: { diagnostics } tool tasks; generation for calls not offered 6.4 (p. 94)
pi.reset absent, or [UserMessage] handoff; head: "self" reset(), handoff control 3.4 (p. 46)
pi.compaction [UserMessage] summary; head = first kept; data: { reason } compaction tasks 6.5 (p. 97)
```

### 文档 kind

:::note
`pi.agent` `rewindable` · `asOf` 每次变化 模型、思考级别、扩展与工具名、指令、cwd 7.2 (p. 106) `pi.provider` `latest` · `initial` 每次变化 sessionId，一个 UUIDv7 6.3 (p. 91) `pi.live` `latest` · `initial` 没有东西在运行时 运行、生成、工具、压缩 6.2 (p. 88)
:::

```
pi.inbox latest · initial when empty items: queued steers, follow-ups, writes 6.1 (p. 84)
pi.usage latest · initial every change models by provider/model, tools by name 6.6 (p. 100) All five belong to one conversation, are created with it (or its fork), and appear in its view as docs["pi.…"]. “Full copy stored” paraphrases each checkpointWhen; between copies only changes are stored.
```

### 任务 kind

:::note
`pi.generation` `prepare`、`request`、`retry`、`poll`、`tools` 构建提示词、调用模型、重试、启动工具调用 6.3 (p. 91) `pi.tool` `call`、`execute` 检查参数、运行钩子、提交意图、运行工具、提交结果 6.4 (p. 94) `pi.compaction` `select`、`summarize`、`retry` 挑选旧条目、对它们做摘要、加入摘要 6.5 (p. 97) 每个注册表都持有这三个任务；它们不能被移除或替换。
:::

```
Sources: src/entries.ts; src/harness/agent.ts, provider.ts, live.ts, inbox.ts, usage.ts (document definitions); src/harness/generation.ts, tool.ts, compaction.ts (phases); src/harness/registry.ts (BUILTIN_TASKS); spec §2.2, §8, §8.1
```

<a id="sec-R-3"></a>

## R.3 设置与默认值

> 宿主传给 `Harness.open()` 的每一个选项、每一个设置键及其内置默认值，以及源码里硬编码的其他默认值。

设置在每次需要时被读取，从不存储。省略某个字段即取它的默认值；在 `retry` 这样的对象里，每个缺失的键各自取自己的默认值。取值器让设置保持活的（构建一个编码智能体 (p. 159)）。

### `HarnessOptions`

:::note
`models` `pi-ai` 的 `Models` 必填 6.3 (p. 91) `registry` `RegistryReader` 必填；必须持有内置任务 7.1 (p. 103) `settings` `HarnessSettings` 每个字段都取默认值 7.2 (p. 106)
:::

```
env (target, ctx) => ExecutionEnv | undefined none: no environment 9.5 (p. 155)
conversationCreated (tx, record) => void none 4.2 (p. 53) now () => number Date.now 5.2 (p. 67) onReport (error) => void none; must not throw 7.3 (p. 109)
```

### `HarnessSettings`

:::note
`extensions` 每个已安装的扩展，按安装顺序 会话使用的扩展，除非它自选 7.2 (p. 106) `stream` `{}` `pi-ai` 的请求选项，见下 6.3 (p. 91) `retry.enabled` `true` 重试失败的模型请求 6.3 (p. 91) `retry.maxRetries` `3` 首次失败之后的重试次数 6.3 (p. 91) `retry.baseDelayMs` `2000` 退避基数 6.3 (p. 91) `retry.maxAgentDelayMs` `60000` 退避上限 6.3 (p. 91) `compaction.enabled` `true` 上下文填满时自动压缩 6.5 (p. 97) `compaction.reserveTokens` `16384` 上下文超过 `contextWindow` − `reserveTokens` 后在请求前压缩 6.5 (p. 97) `compaction.keepRecentTokens` `20000` 逐字保留的最近 token 数 6.5 (p. 97) `compaction.backgroundTokens` `32768` 提前这么多 token 就在后台开始压缩；`0` 表示禁用 6.5 (p. 97) `progress.partialIntervalMs` `100` 流式文本两次提交之间的最小间隔 6.2 (p. 88) `progress.outputIntervalMs` `100` 工具输出两次提交之间的最小间隔 6.2 (p. 88) `toolExecution` `"parallel"` 或 `"sequential"` 6.4 (p. 94) `steeringMode` `"one-at-a-time"` 或 `"all"`，按边界 6.1 (p. 84) `followUpMode` `"one-at-a-time"` 或 `"all"`，按边界 6.1 (p. 84) 默认值来自 `DEFAULT_RETRY_POLICY`、`DEFAULT_COMPACTION_POLICY`、`DEFAULT_PROGRESS_POLICY` 以及 `src/harness/agent.ts` 中的 `resolveSettings`。spec 里的 `HarnessSettings` 列表漏了 `progress`；源码和 CHANGELOG 1.0.3 都包含它。
:::

### stream 选项

:::note
KEY MEANING `transport` `pi-ai` 传输方式 `timeoutMs` 请求超时 `maxRetries`、`maxRetryDelayMs` 供应商/SDK 在一次尝试内部的重试，与 `retry` 表头不同 `metadata` 转发的请求头与元数据 `cacheRetention` `pi-ai` 提示词缓存保留策略
:::

```
deferred boolean or { window: "15m" | "1h" | "24h" }
```

:::note
缺失的字段使用 `pi-ai` 的默认值（`ConversationStreamOptions`，`src/harness/types.ts`）。
:::

### 其他默认值

:::note
`tool` `replay` `"unsafe"` `src/harness/tool.ts` 6.4 (p. 94) `tool` `executionMode` 设置里的 `toolExecution` `src/harness/types.ts` 6.4 (p. 94)
:::

```
tool outputLimits 50 KB, 2000 lines, retain: "head" src/harness/tool.ts, src/truncate.ts 7.4 (p. 112)
bash output retain: "tail" src/tools/bash.ts 7.4 (p. 112)
section tag true: <key>…</key> src/harness/types.ts 7.5 (p. 115)
```

:::note
`agent` `thinkingLevel` `"off"` `src/harness/agent.ts` 7.2 (p. 106) `input` `whenBusy` `"followUp"` spec §2.2 6.1 (p. 84) `watch` `pending` 帧 `100`，随后一帧完整值 `src/session/observation.ts` 8.2 (p. 129) `JSONL` `fsync` `false` `src/storage/jsonl/storage.ts` 9.3 (p. 148) `SQLite` `walAutoCheckpointPages` `1000` `src/storage/sqlite/node.ts` 9.2 (p. 144) `SQLite` `busyTimeoutMs` `5000` `src/storage/sqlite/node.ts` 9.2 (p. 144)
:::

```
Sources: src/harness/types.ts (HarnessOptions, HarnessSettings, Settings, ConversationStreamOptions, ToolRegistration, PromptSection); src/harness/agent.ts; src/harness/harness.ts:180; src/harness/tool.ts:88, :176; src/truncate.ts; src/tools/bash.ts;
src/session/observation.ts:15; src/storage/jsonl/storage.ts; src/storage/sqlite/node.ts; spec §2.2; CHANGELOG 1.0.3
```

<a id="sec-R-4"></a>

## R.4 错误与原因

> 抛出的错误，以及工作以糟糕方式结束时 Harness 存储的字符串：提交项原因、任务 outcome、阻塞原因、诊断，以及 watch

> 结束。

出问题时你会以两种方式之一看到它。要么抛出错误类，由你的代码捕获。要么是一个 reason，即存储在记录上的字符串，因此它能跨重启存续，你之后还可以查询它。

### 错误类

:::note
`ReadAfterWrite` 某次 `Tx` 在第一次表写入之后又做了表读取 先读；修好代码 2.2 (p. 29) `StorageRejected` 存储在任何持久效果之前拒绝了一批写入 该次提交回滚；`Session` 继续 2.3 (p. 33)
:::

```
ConversationBusy whenBusy: "reject" on a busy conversation; carries conversationId
nothing was written 6.1 (p. 84) JsonlCorruptionError opening found committed data missing or damaged restore from backup 9.3 (p. 148) JsonlStoragePoisonedError a write failed and may or may not have landed; “must be reopened” reopen 9.3 (p. 148) FileError environment file operations; code such as not_found per code 9.5 (p. 155) ExecutionError environment exec; code such as timeout, aborted per code 9.5 (p. 155) plain Error “Session is poisoned by a failed commit after storage admission; reopen it” reopen 2.3 (p. 33)
```

```
plain Error “Session is closed” use a new Harness 2.3 (p. 33)
```

:::note
前三个从包根导出，JSONL 的错误从 `…/storage/jsonl` 导出，环境的错误从 `…/env` 导出。
:::

### 提交项无人应答的原因

:::note
`aborted` 一个排队项被撤回，或一次运行的任务被中止 6.1 (p. 84) `stale` 一次头指针写入指向活跃范围之前的条目 6.1 (p. 84) `reset` 放在 `postTools` 的重置在给出答案之前结束了运行 3.4 (p. 46) `no_model` 智能体没有模型，或模型解析不出来 6.3 (p. 91) `model_error` 供应商在重试之后仍失败；detail 是它的文本 6.3 (p. 91) `faulted` 运行的任务故障了；detail 是错误消息 5.6 (p. 80) `missing_task`、`task_too_old`、`migration_failed` 一个被阻塞的运行任务被中止并成了孤儿 5.4 (p. 73)
:::

### 任务 outcome 与阻塞原因

:::note
`completed` outcome status 由任务带一个结果提交 5.1 (p. 63) `failed` outcome status 预期内的失败，由任务带 error 提交 5.1 (p. 63) `aborted` outcome status 任务的中止处理器已运行并选了这个结局 5.6 (p. 80) `orphaned` outcome status 被中止，而此时没有代码能运行它；reason 说明原因 5.6 (p. 80)
:::

```
faulted outcome status the task broke a rule: it threw, made no progress, or its commit was rejected 5.2 (p. 67)
```

:::note
`missing_task` inspection blocked.reason 没有与该任务 kind 对应的已注册定义 5.4 (p. 73) `task_too_old` inspection blocked.reason 已注册的版本比记录上的旧 5.4 (p. 73) `migration_failed` inspection blocked.reason migrate 抛出或缺失 5.4 (p. 73) `model_error`、`no_model` failed error.detail.reason 生成或压缩拿不到答案 6.3 (p. 91) 阻塞原因在检查时推导得出，从不存储，直到某次中止把其中一个变成 orphaned 原因。
:::

### 工具诊断与 watch 结束

:::note
`tool_unavailable` diagnostic 该工具未被提供，或已无法解析 6.4 (p. 94) `invalid_arguments` diagnostic 参数未通过 TypeBox 校验 7.4 (p. 112) `blocked` diagnostic 一个 `beforeTool` 钩子拦下了这次调用 7.3 (p. 109) `interrupted` diagnostic 一个不安全的工具被崩溃或 close 切断 6.4 (p. 94) `truncated`、`full_output` diagnostic 输出被截断；完整输出溢写到文件 7.4 (p. 112) `stopped`、`cancelled` WatchEnd.reason 调用了 `stop()`；观察到的取消信号已中止 8.1 (p. 125) `session_closed`、`retired` WatchEnd.reason `Session` 已关闭；文档已退役 8.1 (p. 125) `listener_error` WatchEnd.reason listener 抛出；携带 error 8.1 (p. 125)
:::

```
Sources: src/errors.ts; src/storage/jsonl/storage.ts:81–94; src/env/index.ts:35–75; src/session/session.ts:539–546;
src/session/observation.ts; src/harness/submissions.ts; src/harness/inbox.ts; src/harness/generation.ts; src/harness/live.ts:171; src/harness/scheduler.ts:769–813; src/harness/tool.ts; src/tools/read.ts; src/tools/bash.ts; src/types.ts (TaskOutcome, WatchEnd);
spec §5.4, §6, §8.3; research/capture/crash-after.txt; research/capture/inbox-steps.txt
```

<a id="sec-R-5"></a>

## R.5 术语表

> 每个术语在本书中的用法，以及定义它的那一节。

```
```

:::note
智能体（`Agent`）—— 会话运行时所带的东西：模型、思考级别、扩展、工具、指令、cwd 7.2 (p. 106)
:::

:::note
后台（`Background`）—— 由会话拥有、被排除在空闲等待、会话中止和级联之外的任务 5.5 (p. 76) 基线（`Base`）—— 完整的已存储文档值；之后的改动是叠加在它之上的增量 4.3 (p. 56) 阻塞（`Blocked`）—— 没有已注册定义能接手的存活任务；推导得出，从不存储 5.4 (p. 73)
:::

```
```

:::note
边界（`Boundary`）—— 轮次之间收件箱放置条目的一个时点：`postTools` 或 `final` 6.1 (p. 84)
:::

:::note
检查点（`Checkpoint`）—— 任务 resume 出发点处那份完整的持久状态；它的 phase 指明处理器 5.1 (p. 63) `Chord`—— 把文档表示为值与操作的复制状态库 8.1 (p. 125) 提交（`Commit`）—— 在变更线上对记录与文档的一次原子写入 2.2 (p. 29) 完成中（`Completing`）—— outcome 已定，但被持有的任务因其所拥有的工作仍存活而暂缓 5.5 (p. 76) 上下文（`Context`）—— 为下一次模型请求从记录（transcript）派生出的消息 3.2 (p. 40) 会话（`Conversation`）—— 一个记录作用域；可以分叉出另一个，也可以被某个任务拥有 3.3 (p. 43) 定义（`Definition`）—— 描述文档、文档族、条目 kind 或任务的带类型词元 4.1 (p. 50) 文档（`Document`）—— 以 `Chord` 操作和基线存储的带类型可变 `JSON` 状态 4.1 (p. 50) 效果三明治（`Effect sandwich`）—— 提交意图、执行效果、提交结果 5.3 (p. 70) 条目（`Entry`）—— 一条不可变的记录事件，带一个 kind、模型消息和 data 3.1 (p. 37) 扩展（`Extension`）—— 一组命名的工具、小节、钩子、包裹器和任务 7.1 (p. 103) 分叉（`Fork`）—— 继承父会话历史直到 `parent.at` 的会话 3.3 (p. 43) 生成（`Generation`）—— 一次模型请求及其分类，由 `pi.generation` 运行 6.3 (p. 91) `Harness`—— 一个打开的 storage，加上在其上运行智能体的机制 1.2 (p. 13) 头指针（`Head`）—— 条目上的一个字段，命名活跃上下文的第一条条目 3.4 (p. 46)
:::

:::note
钩子（`Hook`）—— 由内置任务调用的扩展处理器，比如 `beforeTool` 7.3 (p. 109) 收件箱（`Inbox`）—— 排队提交项的 `pi.inbox` 文档 6.1 (p. 84) `invocation`—— 任务某个 phase 或中止处理器在内存中的一次运行 5.4 (p. 73) `memo`—— 存在存活任务上的小型先写入者胜值 5.2 (p. 67) 变更线（`Mutation line`）—— `Session` 用于提交的单条串行化路径 2.2 (p. 29) 孤儿（`Orphaned`）—— 被中止结算掉、没有运行任何任务代码的阻塞任务 5.6 (p. 80)
:::

```
```

:::note
`outcome`—— 任务的终局结果：`completed`、`failed`、`aborted`、`orphaned`、`faulted` 5.1 (p. 63)
:::

:::note
所有者（`Owner`）、所拥有的工作（`owned work`）—— 创建某个任务或会话的会话或任务；所拥有的工作随它一起被持有、随它一起中止 5.5 (p. 76) 阶段（`Phase`）—— 任务的一个命名步骤，每个阶段一个处理器 5.2 (p. 67) 注册表（`Registry`）—— 进程内、不存储的已安装扩展集合 7.1 (p. 103)
:::

```
```

:::note
重放（`Replay`）—— 工具关于一次被中断的调用能否重跑的声明：`safe` 或 `unsafe` 6.4 (p. 94)
:::

:::note
运行（`Run`）—— 从一个被受理的输入到它最终答案之间的那些轮次；期间会话一直是忙的 6.2 (p. 88) 小节（`Section`）—— 系统提示词的一个命名部分，在每次请求之前渲染 7.5 (p. 115)
:::

:::note
`Session`—— 一条变更线及其记录与文档的所有者 1.3 (p. 16) 设置（`Settings`）—— Harness 全局的运行策略，每次使用时读取，从不存储 7.2 (p. 106)
:::

```
```

:::note
`Storage`—— 原子地持久化提交的后端：Memory、SQLite、JSONL 9.1 (p. 141)
:::

:::note
提交项（`Submission`）—— 一个被受理的用户输入或条目写入，宿主可以等它 6.1 (p. 84) 任务（`Task`）—— 附着在一个会话上的持久状态机 5.1 (p. 63) 工具调用（`Tool call`）—— 一次运行工具的模型请求，由 `pi.tool` 任务执行 6.4 (p. 94) 轮次（`Turn`）—— 一次助手回复及它发起的工具调用 1.3 (p. 16)
:::

```
```

:::note
视图（`View`）—— 会话的结构化挂载：记录、活跃条目、内置文档 8.2 (p. 129)
:::

:::note
观察（`Watch`）—— 序列化的精确帧观察，最多 100 个待处理帧 8.2 (p. 129) 包裹（`Wrap`）—— 扩展对某个工具或小节的装饰器，按名字定位 7.4 (p. 112)
:::

```
Sources: spec §1 (terms); README §Concepts; src/types.ts; src/harness/types.ts; AUTHORING.md canonical terms
```

<a id="sec-R-6"></a>

## R.6 资料来源

> 本书引用的每一样东西，都基于阅读时的那次提交。

仓库是 github.com/earendil-works/pi，包是 packages/durable，`@earendil-works/pi-durable` 1.0.3，提交 5b6c792b424e73edefbfa558b901bcd64788dad2（2026-10-05）。除非以 `research/` 开头，路径都相对于 `packages/durable/`。

### 文档与源码

:::note
`docs/spec.md` spec §N 规范说明（内部名 Pico5） `README.md` README §X 包指南 `CHANGELOG.md` CHANGELOG 1.0.N 1.0.0 到 1.0.3 的发布记录 `docs/pico-v5-handoff.md` 交接 实现计划 `docs/pico-v5-chord-usage.md` chord 用法 这个包如何使用 Chord `docs/chord-delta-findings.md` 增量发现 Chord 增量笔记 `src/index.ts`、`src/types.ts`、`src/errors.ts` `src/…` 公开接口面、记录与存储类型、错误 `src/session/` `src/session/…` `Session`、事务、分叉、观察 `src/harness/` `src/harness/…` `Harness`、调度器、内置任务与文档、视图、事件 `src/storage/` `src/storage/…` Memory、SQLite 与 JSONL 后端 `src/env/`、`src/tools/` `src/env/…`、`src/tools/…` 执行环境；内置工具 `src/testing/` `src/testing/…` 存储与环境一致性测试套件 `test/*.test.ts` `test/…` 行为测试 `research/pi/packages/coding-agent/docs/` `session-format.md`、`sessions.md`、`how-pi-works.md` 最初的 Pi 会话格式
:::

### 示例与运行

```
ex 00–05 Session layer: conversations, documents, forks, owned conversations, Chord state, watches
ex 06–11 Harness, configuration, conversations, context, registry reload, extension state ex 12–13 a durable task; close, reopen and continue ex 14–19 chat, system prompt, real model, coding tools, print mode, JSON mode ex 20–21 the inbox while busy; late join ex 22–24 foreground and background subagents; child tasks
```

```
ex 25 compaction: background, manual, overflow
ex 26–31 coding agent, plan mode, reviewer, sandbox per conversation, tool override, reload and restart Examples live in test/examples/NN-*.ts; their captured output is research/runs/NN-*.txt (cited run NN). Ex 16 needs a real model and has no run file. All others use pi-ai’s faux provider.
```

### 捕获工具包

:::note
`README.md`、`NOTES.md` 每件产物是怎么做的；观察到的行为与文档的对照 `sqlite-schema.sql`、`sqlite-rows*.txt`、`sqlite-commits.txt` SQLite schema，以及一轮之后的每一行、运行中的行、提交日志 `jsonl-dir/`、`jsonl-dir-midrun/`、`jsonl-*.txt` 一轮之后与运行中的 JSONL 目录、列表、提交日志 `crash-README.md`、`crash-*.txt` 两次工具调用期间的一次 SIGKILL、重新打开并继续 `task-transitions.txt`、`task-graph.txt` 每一次任务记录的状态转换；任务图帧 `watch-ops.txt`、`agent-events.txt`、`view-final.json` 视图观察帧、智能体事件批次、最终视图 `inbox-steps.txt`、`context.txt` 忙时的收件箱与提交项；原始条目与模型上下文的对照 `scripts/` 捕获脚本，`test/capture/*.ts` 的副本 全部位于 `research/capture/`，在 Node v24.13.0 上针对同一个提交产出。`extra-p*/` 目录存放为各个部分另外做的捕获。
:::

### Web

:::note
Earendil Engineering，《Pi Durable》，2026 年 10 月 1 日，https://earendil.com/posts/pi-durable/ 仅作动机；绝不作为 API 事实来源
:::

```
Sources: package.json; README §Examples, §Design Documents; research/capture/README.md; research/runs/
```

<a id="sec-R-7"></a>

## R.7 插图索引

> 书中的每一幅图，按它要主张的说法列出。

:::note
2.4 `Storage` 受理之前的失败会回滚；一个不确定的 `Storage` 结果，或一次在 `Storage` 已提交之后失败的接管，会毒化 `Session`。
:::

```
4.2 Creation is a write: the first tx.doc() of a missing document stores its whole value in that commit. 53
4.5 A fork copies each conversation document by its own policy, into a new incarnation with one base. 58
5.4 The scheduler looks up a task’s code by kind; a task no code can take stays pending, and only an abort ends it, as orphaned.
9.2 Each record table lifts its query columns out of a JSON record; document content lives apart, one row per commit that changes it.
```

:::note
9.9 工具、提示词小节和任务阶段只通过一个环境触达文件与进程，而这个环境由宿主每次使用时从已提交的状态构建。
:::
