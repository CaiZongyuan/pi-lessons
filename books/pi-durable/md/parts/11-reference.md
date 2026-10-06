<aside class="note">R.1 Harness 与会话 API 172 R.2 内置 kind 179 R.3 设置与默认值 180 R.4 错误与原因 183 R.5 术语表 185 R.6 资料来源 187 R.7 插图索引 189</aside>
<a id="sec-R-1"></a>

## R.1 Harness 与会话 API

<p class="lede">包根及其各子路径上的每一个公开入口，附上它的返回值和书中讲解它的那一节。</p>
用这些表找到某个方法以及讲解它的那一节。签名经过缩短：`ctx` 是每个异步方法都接收的取消用 `Context`，类型参数已省略。事实来源是 `src/index.ts` 及其重新导出的文件。

### 包根：函数与类

### 包根：词元与常量

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>UserEntry, AssistantEntry, SystemEntry entry tokens pi.user, pi.assistant, pi.system 3.1 (p. 37)</td><td></td><td></td></tr>
<tr><td>ToolResultEntry, ResetEntry, CompactionEntry entry tokens pi.tool-result, pi.reset, pi.compaction 3.1 (p. 37)</td><td></td><td></td></tr>
<tr><td>AgentDoc, ProviderDoc, LiveDoc document tokens pi.agent, pi.provider, pi.live 4.4 (p. 60)</td><td></td><td></td></tr>
<tr><td>InboxDoc, UsageDoc document tokens pi.inbox, pi.usage 4.4 (p. 60)</td><td></td><td></td></tr>
<tr><td>GenerationTask, ToolTask, CompactionTask task tokens pi.generation, pi.tool, pi.compaction R.2 (p. 179)</td><td></td><td></td></tr>
<tr><td>ROOT_CONVERSATION_ID constant 1 2.1 (p. 25)</td><td>常量 1</td><td></td></tr>
<tr><td>DEFAULT_RETRY_POLICY constant see settings and defaults (p. 180) 6.3 (p. 91)</td><td>常量 见设置与默认值 (p. 180)</td><td></td></tr>
<tr><td>DEFAULT_COMPACTION_POLICY constant see settings and defaults (p. 180) 6.5 (p. 97)</td><td>常量 见设置与默认值 (p. 180)</td><td></td></tr>
<tr><td>DEFAULT_PROGRESS_POLICY constant see settings and defaults (p. 180) 6.2 (p. 88)</td><td>常量 见设置与默认值 (p. 180)</td><td></td></tr>
</table>

### 子路径导出

### `Harness`

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>resume () start running tasks; safe to call twice; throws after close 5.4 (p. 73)</td><td>开始运行任务；可安全调用两次；close 之后调用会抛出</td><td></td></tr>
<tr><td>root (ctx, { agent, init }?) the root conversation, created on first use 3.3 (p. 43)</td><td>根会话，首次使用时创建</td><td></td></tr>
<tr><td>conversation (id, ctx) Conversation | undefined 3.3 (p. 43)</td><td></td><td></td></tr>
<tr><td>createConversation ({ ownership, agent?, init? }, ctx)</td><td><code>Conversation</code>，在一次提交中创建</td><td></td></tr>
<tr><td>getTask (id, ctx) TaskRecord | undefined 5.1 (p. 63)</td><td></td><td></td></tr>
<tr><td>inspect (ctx) HarnessInspection: unfinished tasks and submissions; writes nothing</td><td></td><td>8.4</td></tr>
<tr><td>submission (id, ctx) Submission | undefined; works after a reopen 6.1 (p. 84)</td><td></td><td></td></tr>
<tr><td>abortSubmission (id, ctx, conversationId?) "aborted" | "already_placed" | "settled" | "not_found"</td><td></td><td></td></tr>
<tr><td>6.1 (p. 84)</td><td></td><td></td></tr>
<tr><td>abortTask (id, ctx) "marked" | "terminal" 5.6 (p. 80)</td><td></td><td></td></tr>
<tr><td>waitForTask (id, ctx) SettledTask, once the task has finished 5.1 (p. 63)</td><td></td><td></td></tr>
<tr><td>waitForIdle (ctx) resolves when no foreground work is left anywhere 5.5 (p. 76)</td><td></td><td></td></tr>
<tr><td>usage (ctx) UsageState: token and cost totals of all conversations 6.6</td><td></td><td></td></tr>
<tr><td>taskGraph (ctx) live, read-only tree of unfinished tasks; dispose when done 8.4</td><td></td><td></td></tr>
<tr><td>watchTaskGraph (ctx) TaskGraphWatch 8.4</td><td></td><td></td></tr>
</table>

### `Session` 方法（`Harness` 继承）

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>commit (change: (tx) =&gt; T, ctx) T, once the commit is stored 2.2 (p. 29)</td><td></td><td></td></tr>
<tr><td>close (ctx) stop new work, wait for running code, close storage 2.3 (p. 33)</td><td></td><td></td></tr>
<tr><td>subscribeCommits (listener) unsubscribe function; listener sees every commit, synchronously 2.2 (p. 29)</td><td></td><td></td></tr>
<tr><td>subscribeClose (listener) unsubscribe function; called when close begins 2.2 (p. 29)</td><td></td><td></td></tr>
<tr><td>snapshot (token, owner?, key?, ctx) current committed value, read-only, or undefined 4.2 (p. 53)</td><td></td><td></td></tr>
<tr><td>snapshotAsOf (token, conversationId, key?, at, ctx) value as of an entry; rewindable documents only 4.3 (p. 56)</td><td></td><td></td></tr>
<tr><td>documentState (token, owner?, key?, ctx) live read-only value that follows commits; dispose when done 8.1 (p. 125)</td><td></td><td></td></tr>
<tr><td>watchDoc (token, owner?, key?, ctx) DocumentWatch | undefined: one callback per change 8.1 (p. 125)</td><td></td><td></td></tr>
</table>

<aside class="note">`owner` 参数按词元的作用域是会话 ID 或任务 ID，`Session` 作用域下不存在；`key` 只对族有效。</aside>
### `Conversation`

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>id property ConversationId; compare conversations by it 3.3 (p. 43)</td><td>属性</td><td></td></tr>
<tr><td>agent (ctx) the Agent it would run with now; writes nothing 7.2 (p. 106)</td><td>它现在会带着运行的</td><td></td></tr>
<tr><td>configure (change, ctx) change model, tools, extensions or cwd, in its own commit 7.2 (p. 106)</td><td>在它自己的提交里更改模型、工具、扩展或 cwd</td><td></td></tr>
<tr><td>submit (draft, ctx) Submission, once the input is committed 6.1 (p. 84)</td><td>输入提交之后的</td><td></td></tr>
<tr><td>reset (handoff?, ctx) start a fresh context, optionally with a handoff message 3.4 (p. 46)</td><td>开始一份全新的上下文，可带一条交接消息</td><td></td></tr>
<tr><td>compact (instructions?, ctx) TaskId&lt;CompactionResult&gt; of a summary task 6.5 (p. 97)</td><td>摘要任务的</td><td></td></tr>
<tr><td>commit (change, ctx) a commit where new tasks default to this conversation 2.2 (p. 29)</td><td></td><td></td></tr>
<tr><td>context (ctx) ContextView: active entries and the messages the model will see 3.2 (p. 40)</td><td></td><td></td></tr>
<tr><td>entries (query, limit, cursor, ctx) one page of entries, newest first, including inherited ones 3.1 (p. 37)</td><td>一页条目，最新在前，包含继承来的</td><td></td></tr>
<tr><td>fork (at, { ownership, agent?, init? }, ctx) the new Conversation 3.3 (p. 43)</td><td></td><td></td></tr>
<tr><td>abort (ctx, { background }?) stop running work and withdraw queued inputs; resolves when idle 5.6 (p. 80)</td><td></td><td></td></tr>
<tr><td>waitForIdle (ctx) resolves when no foreground work is left 5.5 (p. 76)</td><td></td><td></td></tr>
<tr><td>viewState (ctx) live read-only ConversationView for a UI 8.2 (p. 129)</td><td></td><td></td></tr>
<tr><td>watch (ctx) ConversationWatch: one callback per change 8.2 (p. 129)</td><td></td><td></td></tr>
</table>

### `Submission` 与 `ConversationHandle`

### `Tx`，提交回调的接口面

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>conversation, entry, task</td><td><code>entry</code>、</td><td></td></tr>
<tr><td>scanConversations (query, limit, cursor?) one page of conversations, filtered by owner 7.7</td><td>一页会话，按 owner 过滤</td><td></td></tr>
<tr><td>scanEntries (query, limit, cursor?) one page of entries, newest first 3.1 (p. 37)</td><td>一页条目，最新在前</td><td></td></tr>
<tr><td>latestHeadMarker (conversationId) the entry that set the current context start 3.4 (p. 46)</td><td>设下当前上下文起点的条目</td><td></td></tr>
<tr><td>scanTasks (query, limit, cursor?) one page of task records 5.1 (p. 63)</td><td>一页任务记录</td><td></td></tr>
<tr><td>submissionByRequest (conversationId, requestId) record or undefined 6.1 (p. 84)</td><td>记录或 <code>undefined</code></td><td></td></tr>
<tr><td>createConversation ({ ownership }) ConversationRecord; in a Harness, also creates the built-in documents</td><td></td><td>3.3 (p. 43)</td></tr>
<tr><td>forkConversation (parentId, at, { ownership }) ConversationRecord 3.3 (p. 43)</td><td><code>ConversationRecord</code></td><td></td></tr>
<tr><td>appendEntry (conversationId, draft) or (token, …)</td><td>或 <code>(token, …)</code></td><td></td></tr>
<tr><td>createTask (task, input, options) TaskId (a table write) 5.1 (p. 63)</td><td></td><td></td></tr>
<tr><td>createSubmission (create) raw record, skipping the busy and queue rules 6.1 (p. 84)</td><td>原始记录，跳过繁忙与排队规则</td><td></td></tr>
<tr><td>settleSubmission (id, settlement) mark it done or unanswered 6.1 (p. 84)</td><td>把它标记为完成或无人应答</td><td></td></tr>
<tr><td>placeSubmission (id, entry) record where it landed: input placed, write done 6.1 (p. 84)</td><td></td><td></td></tr>
<tr><td>doc (token, owner?, key?, seed?) an editable draft; creates the document if absent 4.2 (p. 53)</td><td></td><td></td></tr>
<tr><td>retireDoc (token, owner?, key?) end the document; a later doc() creates a new one 4.2 (p. 53)</td><td></td><td></td></tr>
</table>

### `TaskRuntime`，一次任务调用

<aside class="note">`hooks.each(name, invoke)` 按顺序调用每个被选中扩展的处理器 7.3 (p. 109)</aside>
```ts
commit ((tx, current) => next?, ctx) commit; return a new state to move the task on 5.1 (p. 63)
memo (name, ctx), (name, candidate, ctx) a small stored value; the first write wins 5.2 (p. 67) getTask, waitForTask (id, ctx) the record; the record once finished 5.5 (p. 76) outcomes (ids, ctx) results of finished tasks; rejects if one is unfinished 5.5 (p. 76) conversation (id, ctx) ConversationHandle | undefined 7.7 (p. 121) entry (id, ctx), (token, id, ctx) a committed entry this conversation can see 3.1 (p. 37) context (conversationId, ctx, at?) what the model would see, optionally as of entry at 3.2 (p. 40) now, sleep (); (until, ctx) the Harness clock; wait until a time 5.2 (p. 67) report (error) pass a non-fatal error to onReport 7.3 (p. 109) snapshot, snapshotAsOf, watchDoc as on Session committed values; watches stop when the handler ends 8.1 (p. 125)
```

### `ToolExecutionApi`，一次工具调用

### `Registry`

<a id="sec-R-2"></a>

## R.2 内置 kind

<p class="lede">六种条目 kind、五种文档 kind 和三种任务 kind 承载每一次运行；全部以保留的 `pi.` 前缀命名。</p>
kind 是随每条记录一起存储的名字，因此绝不能改动。`pi.` 前缀只是按约定保留的；复用它会与 `Harness` 冲突（会咬人的契约 (p. 163)）。代码中为每种 kind 命名的词元列在 R.1 (p. 172)。

### 条目 kind

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>pi.user [UserMessage] submissions, onYield continuations 3.1 (p. 37)</td><td></td><td></td></tr>
<tr><td>pi.assistant [AssistantMessage], any stop reason generation 6.3 (p. 91)</td><td></td><td></td></tr>
<tr><td>pi.system [SystemMessage], content: "" generation preparation 7.5 (p. 115)</td><td></td><td></td></tr>
<tr><td>pi.tool-result [ToolResultMessage]; data: { diagnostics } tool tasks; generation for calls not offered 6.4 (p. 94)</td><td></td><td></td></tr>
<tr><td>pi.reset absent, or [UserMessage] handoff; head: "self" reset(), handoff control 3.4 (p. 46)</td><td></td><td></td></tr>
<tr><td>pi.compaction [UserMessage] summary; head = first kept; data: { reason } compaction tasks 6.5 (p. 97)</td><td></td><td></td></tr>
</table>

### 文档 kind

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>pi.agent rewindable · asOf every change model, thinking level, extension and tool names, instructions, cwd 7.2 (p. 106)</td><td></td><td></td></tr>
<tr><td>pi.provider latest · initial every change sessionId, a UUIDv7 6.3 (p. 91)</td><td></td><td></td></tr>
<tr><td>pi.live latest · initial when nothing runs run, generation, tools, compactions 6.2 (p. 88)</td><td></td><td></td></tr>
<tr><td>pi.inbox latest · initial when empty items: queued steers, follow-ups, writes 6.1 (p. 84)</td><td></td><td></td></tr>
<tr><td>pi.usage latest · initial every change models by provider/model, tools by name 6.6 (p. 100)</td><td></td><td></td></tr>
<tr><td>All five belong to one conversation, are created with it (or its fork), and appear in its view as docs["pi.…"]. “Full copy stored” paraphrases each</td><td></td><td></td></tr>
</table>

### 任务 kind

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>pi.generation prepare, request, retry, poll, tools build the prompt, call the model, retry, start the tool calls 6.3 (p. 91)</td><td></td><td></td></tr>
<tr><td>pi.tool call, execute check arguments, run hooks, commit intent, run the tool, commit the result 6.4 (p. 94)</td><td></td><td></td></tr>
<tr><td>pi.compaction select, summarize, retry pick old entries, summarize them, add the summary 6.5 (p. 97)</td><td></td><td></td></tr>
</table>

```
Sources: src/entries.ts; src/harness/agent.ts, provider.ts, live.ts, inbox.ts, usage.ts (document definitions); src/harness/generation.ts, tool.ts, compaction.ts (phases); src/harness/registry.ts (BUILTIN_TASKS); spec §2.2, §8, §8.1
```

<a id="sec-R-3"></a>

## R.3 设置与默认值

<p class="lede">宿主传给 `Harness.open()` 的每一个选项、每一个设置键及其内置默认值，以及源码里硬编码的其他默认值。</p>
设置在每次需要时被读取，从不存储。省略某个字段即取它的默认值；在 `retry` 这样的对象里，每个缺失的键各自取自己的默认值。取值器让设置保持活的（构建一个编码智能体 (p. 159)）。

### `HarnessOptions`

### `HarnessSettings`

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>extensions every installed extension, install order</td><td>每个已安装的扩展，按安装顺序 会话使用的扩展，除非它自选</td><td></td></tr>
<tr><td>stream {} pi-ai request options, below 6.3 (p. 91)</td><td><code>{}</code></td><td></td></tr>
<tr><td>retry.enabled true retry failed model requests 6.3 (p. 91)</td><td></td><td></td></tr>
<tr><td>retry.maxRetries 3 retries after the first failure 6.3 (p. 91)</td><td></td><td></td></tr>
<tr><td>retry.baseDelayMs 2000 backoff base 6.3 (p. 91)</td><td></td><td></td></tr>
<tr><td>retry.maxAgentDelayMs 60000 backoff cap 6.3 (p. 91)</td><td>表头不同</td><td></td></tr>
<tr><td>compaction.enabled true compact automatically when context fills 6.5 (p. 97)</td><td></td><td></td></tr>
<tr><td>compaction.reserveTokens 16384 compact before the request once context exceeds contextWindow − reserveTokens</td><td></td><td>6.5 (p. 97)</td></tr>
<tr><td>compaction.keepRecentTokens 20000 recent tokens kept word for word 6.5 (p. 97)</td><td></td><td></td></tr>
<tr><td>compaction.backgroundTokens 32768 start compacting in the background this many tokens earlier; 0 disables 6.5 (p. 97)</td><td><code>true</code> 上下文填满时自动压缩 6.5 (p. 97) <code>compaction.reserveTokens</code> <code>16384</code> 上下文超过</td><td></td></tr>
<tr><td>progress.partialIntervalMs 100 minimum gap between commits of streamed text 6.2 (p. 88)</td><td></td><td></td></tr>
<tr><td>progress.outputIntervalMs 100 minimum gap between commits of tool output 6.2 (p. 88)</td><td><code>100</code> 流式文本两次提交之间的最小间隔 6.2 (p. 88) <code>progress.outputIntervalMs</code> <code>100</code> 工具输出两次提交之间的最小间隔</td><td></td></tr>
<tr><td>toolExecution "parallel" or "sequential" 6.4 (p. 94)</td><td><code>"parallel"</code> 或 <code>"sequential"</code></td><td></td></tr>
<tr><td>steeringMode "one-at-a-time" or "all", per boundary 6.1 (p. 84)</td><td><code>"one-at-a-time"</code> 或 <code>"all"</code>，按边界</td><td></td></tr>
<tr><td>followUpMode "one-at-a-time" or "all", per boundary 6.1 (p. 84)</td><td><code>"one-at-a-time"</code> 或 <code>"all"</code>，按边界 6.1 (p. 84) 默认值来自</td><td></td></tr>
<tr><td>Defaults from DEFAULT_RETRY_POLICY, DEFAULT_COMPACTION_POLICY, DEFAULT_PROGRESS_POLICY and resolveSettings in src/harness/agent.ts. The</td><td></td><td></td></tr>
</table>

### stream 选项

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>transport pi-ai transport</td><td></td><td></td></tr>
<tr><td>timeoutMs request timeout</td><td>请求超时</td><td></td></tr>
<tr><td>maxRetries, maxRetryDelayMs provider/SDK retries inside one attempt, unlike retry</td><td></td><td></td></tr>
<tr><td>headers, metadata forwarded request headers and metadata</td><td></td><td></td></tr>
<tr><td>cacheRetention pi-ai prompt-cache retention</td><td><code>pi-ai</code> 提示词缓存保留策略</td><td></td></tr>
<tr><td>deferred boolean or { window: "15m" | "1h" | "24h" }</td><td></td><td></td></tr>
</table>

<aside class="note">缺失的字段使用 `pi-ai` 的默认值（`ConversationStreamOptions`，`src/harness/types.ts`）。</aside>
### 其他默认值

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>tool replay "unsafe" src/harness/tool.ts 6.4 (p. 94)</td><td></td><td></td></tr>
<tr><td>tool executionMode the settings’ toolExecution src/harness/types.ts 6.4 (p. 94)</td><td></td><td></td></tr>
<tr><td>tool outputLimits 50 KB, 2000 lines, retain: "head" src/harness/tool.ts, src/truncate.ts 7.4 (p. 112)</td><td></td><td></td></tr>
<tr><td>bash output retain: "tail" src/tools/bash.ts 7.4 (p. 112)</td><td></td><td></td></tr>
<tr><td>section tag true: &lt;key&gt;…&lt;/key&gt; src/harness/types.ts 7.5 (p. 115)</td><td></td><td></td></tr>
<tr><td>agent thinkingLevel "off" src/harness/agent.ts 7.2 (p. 106)</td><td></td><td></td></tr>
<tr><td>input whenBusy "followUp" spec §2.2 6.1 (p. 84)</td><td></td><td></td></tr>
<tr><td>watch pending frames 100, then one full-value frame src/session/observation.ts 8.2 (p. 129)</td><td></td><td></td></tr>
<tr><td>JSONL fsync false src/storage/jsonl/storage.ts 9.3 (p. 148)</td><td></td><td></td></tr>
<tr><td>SQLite walAutoCheckpointPages 1000 src/storage/sqlite/node.ts 9.2 (p. 144)</td><td></td><td></td></tr>
<tr><td>SQLite busyTimeoutMs 5000 src/storage/sqlite/node.ts 9.2 (p. 144)</td><td></td><td></td></tr>
</table>

```
Sources: src/harness/types.ts (HarnessOptions, HarnessSettings, Settings, ConversationStreamOptions, ToolRegistration, PromptSection); src/harness/agent.ts; src/harness/harness.ts:180; src/harness/tool.ts:88, :176; src/truncate.ts; src/tools/bash.ts;
src/session/observation.ts:15; src/storage/jsonl/storage.ts; src/storage/sqlite/node.ts; spec §2.2; CHANGELOG 1.0.3
```

<a id="sec-R-4"></a>

## R.4 错误与原因

<p class="lede">抛出的错误，以及工作以糟糕方式结束时 Harness 存储的字符串：提交项原因、任务 outcome、阻塞原因、诊断，以及 watch</p>
<p class="lede">结束。</p>
出问题时你会以两种方式之一看到它。要么抛出错误类，由你的代码捕获。要么是一个 reason，即存储在记录上的字符串，因此它能跨重启存续，你之后还可以查询它。

### 错误类

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>ReadAfterWrite a Tx table read after the first table write read first; fix the code 2.2 (p. 29)</td><td>某次</td><td></td></tr>
<tr><td>StorageRejected storage refused a batch before any durable effect the commit rolls back; the Session continues</td><td>存储在任何持久效果之前拒绝了一批写入 该次提交回滚；</td><td>2.3 (p. 33)</td></tr>
<tr><td>ConversationBusy whenBusy: "reject" on a busy conversation; carries conversationId</td><td></td><td></td></tr>
<tr><td>JsonlCorruptionError opening found committed data missing or damaged restore from backup 9.3</td><td></td><td></td></tr>
<tr><td>JsonlStoragePoisonedError a write failed and may or may not have landed; “must be reopened” reopen 9.3</td><td></td><td></td></tr>
<tr><td>FileError environment file operations; code such as not_found per code 9.5</td><td></td><td></td></tr>
<tr><td>ExecutionError environment exec; code such as timeout, aborted per code 9.5</td><td></td><td></td></tr>
<tr><td>plain Error “Session is poisoned by a failed commit after storage admission; reopen it”</td><td></td><td></td></tr>
<tr><td>reopen 2.3 (p. 33)</td><td></td><td></td></tr>
<tr><td>plain Error “Session is closed” use a new Harness 2.3 (p. 33)</td><td></td><td></td></tr>
</table>

### 提交项无人应答的原因

### 任务 outcome 与阻塞原因

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>completed outcome status committed by the task with a result 5.1 (p. 63)</td><td>outcome status 由任务带一个结果提交</td><td></td></tr>
<tr><td>failed outcome status expected failure committed by the task, with error 5.1 (p. 63)</td><td>outcome status 预期内的失败，由任务带 error 提交</td><td></td></tr>
<tr><td>aborted outcome status the task’s abort handler ran and chose this end 5.6 (p. 80)</td><td>outcome status 任务的中止处理器已运行并选了这个结局</td><td></td></tr>
<tr><td>orphaned outcome status aborted while no code could run it; reason says why 5.6 (p. 80)</td><td>outcome status 被中止，而此时没有代码能运行它；reason 说明原因</td><td></td></tr>
<tr><td>faulted outcome status the task broke a rule: it threw, made no progress, or its commit was rejected 5.2 (p. 67)</td><td></td><td></td></tr>
<tr><td>missing_task inspection blocked.reason no registered definition with the task’s kind 5.4 (p. 73)</td><td>inspection blocked.reason 没有与该任务 kind 对应的已注册定义</td><td></td></tr>
<tr><td>task_too_old inspection blocked.reason registered version is older than the record’s 5.4 (p. 73)</td><td>inspection blocked.reason 已注册的版本比记录上的旧</td><td></td></tr>
<tr><td>migration_failed inspection blocked.reason migrate threw or is missing 5.4 (p. 73)</td><td>inspection blocked.reason migrate 抛出或缺失</td><td></td></tr>
<tr><td>model_error, no_model failed error.detail.reason generation or compaction could not get an answer 6.3 (p. 91)</td><td></td><td></td></tr>
</table>

### 工具诊断与 watch 结束

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>tool_unavailable diagnostic the tool was not offered or no longer resolves 6.4 (p. 94)</td><td>diagnostic 该工具未被提供，或已无法解析</td><td></td></tr>
<tr><td>invalid_arguments diagnostic arguments failed TypeBox validation 7.4 (p. 112)</td><td>diagnostic 参数未通过 TypeBox 校验</td><td></td></tr>
<tr><td>blocked diagnostic a beforeTool hook blocked the call 7.3 (p. 109)</td><td>diagnostic 一个</td><td></td></tr>
<tr><td>interrupted diagnostic an unsafe tool was cut by a crash or close 6.4 (p. 94)</td><td>diagnostic 一个不安全的工具被崩溃或 close 切断</td><td></td></tr>
<tr><td>truncated, full_output diagnostic output was cut; full output spilled to a file 7.4 (p. 112)</td><td></td><td></td></tr>
<tr><td>stopped, cancelled WatchEnd.reason stop() called; the observed cancellation signal aborted 8.1 (p. 125)</td><td></td><td></td></tr>
<tr><td>session_closed, retired WatchEnd.reason the Session closed; the document was retired 8.1 (p. 125)</td><td></td><td></td></tr>
<tr><td>listener_error WatchEnd.reason the listener threw; carries error 8.1 (p. 125)</td><td>WatchEnd.reason listener 抛出；携带 error</td><td></td></tr>
</table>

```
src/session/observation.ts; src/harness/submissions.ts; src/harness/inbox.ts; src/harness/generation.ts; src/harness/live.ts:171; src/harness/scheduler.ts:769–813; src/harness/tool.ts; src/tools/read.ts; src/tools/bash.ts; src/types.ts (TaskOutcome, WatchEnd);
spec §5.4, §6, §8.3; research/capture/crash-after.txt; research/capture/inbox-steps.txt
```

<a id="sec-R-5"></a>

## R.5 术语表

<p class="lede">每个术语在本书中的用法，以及定义它的那一节。</p>
<aside class="note">智能体（`Agent`）—— 会话运行时所带的东西：模型、思考级别、扩展、工具、指令、cwd 7.2 (p. 106)</aside>
<aside class="note">`outcome`—— 任务的终局结果：`completed`、`failed`、`aborted`、`orphaned`、`faulted` 5.1 (p. 63)</aside>
<aside class="note">重放（`Replay`）—— 工具关于一次被中断的调用能否重跑的声明：`safe` 或 `unsafe` 6.4 (p. 94)</aside>
<aside class="note">`Session`—— 一条变更线及其记录与文档的所有者 1.3 (p. 16) 设置（`Settings`）—— Harness 全局的运行策略，每次使用时读取，从不存储 7.2 (p. 106)</aside>
<aside class="note">视图（`View`）—— 会话的结构化挂载：记录、活跃条目、内置文档 8.2 (p. 129)</aside>
<a id="sec-R-6"></a>

## R.6 资料来源

<p class="lede">本书引用的每一样东西，都基于阅读时的那次提交。</p>
仓库是 github.com/earendil-works/pi，包是 packages/durable，`@earendil-works/pi-durable` 1.0.3，提交 5b6c792b424e73edefbfa558b901bcd64788dad2（2026-10-05）。除非以 `research/` 开头，路径都相对于 `packages/durable/`。

### 文档与源码

<aside class="note">`docs/spec.md` spec §N 规范说明（内部名 Pico5） `README.md` README §X 包指南 `CHANGELOG.md` CHANGELOG 1.0.N 1.0.0 到 1.0.3 的发布记录 `docs/pico-v5-handoff.md` 交接 实现计划 `docs/pico-v5-chord-usage.md` chord 用法 这个包如何使用 Chord `docs/chord-delta-findings.md` 增量发现 Chord 增量笔记 `src/index.ts`、`src/types.ts`、`src/errors.ts` `src/…` 公开接口面、记录与存储类型、错误 `src/session/` `src/session/…` `Session`、事务、分叉、观察 `src/harness/` `src/harness/…` `Harness`、调度器、内置任务与文档、视图、事件 `src/storage/` `src/storage/…` Memory、SQLite 与 JSONL 后端 `src/env/`、`src/tools/` `src/env/…`、`src/tools/…` 执行环境；内置工具 `src/testing/` `src/testing/…` 存储与环境一致性测试套件 `test/*.test.ts` `test/…` 行为测试 `research/pi/packages/coding-agent/docs/` `session-format.md`、`sessions.md`、`how-pi-works.md` 最初的 Pi 会话格式</aside>
<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>README.md README §X package guide</td><td>README §X 包指南</td><td></td></tr>
<tr><td>CHANGELOG.md CHANGELOG 1.0.N releases 1.0.0 to 1.0.3</td><td>CHANGELOG 1.0.N 1.0.0 到 1.0.3 的发布记录 <code>docs/pico-v5-handoff.md</code> 交接 实现计划 <code>docs/pico-v5-chord-usage.md</code> chord 用法 这个包如何使用 Chord <code>docs/chord-delta-findings.md</code> 增量发现 Chord 增量笔记</td><td></td></tr>
<tr><td>docs/pico-v5-handoff.md handoff implementation plan</td><td></td><td></td></tr>
<tr><td>docs/pico-v5-chord-usage.md chord usage how the package uses Chord</td><td></td><td></td></tr>
<tr><td>docs/chord-delta-findings.md delta findings Chord delta notes</td><td>spec §N 规范说明（内部名 Pico5）</td><td></td></tr>
<tr><td>src/index.ts, src/types.ts, src/errors.ts</td><td></td><td></td></tr>
<tr><td>src/session/ src/session/… Session, transactions, forks, observation</td><td></td><td></td></tr>
<tr><td>src/harness/ src/harness/… Harness, scheduler, built-in tasks and documents, views, events</td><td></td><td></td></tr>
<tr><td>src/storage/ src/storage/… Memory, SQLite and JSONL backends</td><td></td><td></td></tr>
<tr><td>src/env/, src/tools/ src/env/…, src/tools/… execution environment; built-in tools</td><td></td><td></td></tr>
<tr><td>src/testing/ src/testing/… storage and env conformance suites</td><td><code>src/types.ts</code>、<code>src/errors.ts</code> <code>src/…</code> 公开接口面、记录与存储类型、错误 <code>src/session/</code> <code>src/session/…</code></td><td></td></tr>
<tr><td>test/*.test.ts test/… behaviour tests</td><td><code>test/…</code> 行为测试</td><td></td></tr>
<tr><td>research/pi/packages/coding-agent/docs/</td><td></td><td></td></tr>
</table>

### 示例与运行

### 捕获工具包

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>README.md, NOTES.md how each artifact was made; observed behaviours vs the docs</td><td></td><td></td></tr>
<tr><td>sqlite-schema.sql, sqlite-rows*.txt, sqlite-commits.txt SQLite schema and every row after one turn, mid-run rows, commit log</td><td><code>sqlite-rows*.txt</code>、<code>sqlite-commits.txt</code> SQLite schema，以及一轮之后的每一行、运行中的行、提交日志</td><td></td></tr>
<tr><td>jsonl-dir/, jsonl-dir-midrun/, jsonl-*.txt JSONL directory after and during one turn, listings, commit log</td><td><code>jsonl-dir-midrun/</code>、<code>jsonl-*.txt</code> 一轮之后与运行中的 JSONL 目录、列表、提交日志</td><td></td></tr>
<tr><td>crash-README.md, crash-*.txt a SIGKILL during two tool calls, reopen and resume</td><td><code>crash-*.txt</code> 两次工具调用期间的一次 SIGKILL、重新打开并继续</td><td></td></tr>
<tr><td>task-transitions.txt, task-graph.txt every task-record transition; task graph frames</td><td><code>task-graph.txt</code> 每一次任务记录的状态转换；任务图帧</td><td></td></tr>
<tr><td>watch-ops.txt, agent-events.txt, view-final.json view watch frames, agent-event batches, final view</td><td></td><td></td></tr>
<tr><td>inbox-steps.txt, context.txt inbox and submissions while busy; raw entries vs model context</td><td></td><td></td></tr>
<tr><td>scripts/ the capture scripts, copies of test/capture/*.ts</td><td>捕获脚本，</td><td></td></tr>
<tr><td>All under research/capture/, produced on Node v24.13.0 against the same commit. The extra-p*/ directories hold further captures made for individual</td><td></td><td></td></tr>
<tr><td>parts.</td><td></td><td></td></tr>
</table>

### Web

<a id="sec-R-7"></a>

## R.7 插图索引

<p class="lede">书中的每一幅图，按它要主张的说法列出。</p>
<aside class="note">2.4 `Storage` 受理之前的失败会回滚；一个不确定的 `Storage` 结果，或一次在 `Storage` 已提交之后失败的接管，会毒化 `Session`。</aside>
```
4.2 Creation is a write: the first tx.doc() of a missing document stores its whole value in that commit. 53
4.5 A fork copies each conversation document by its own policy, into a new incarnation with one base. 58
5.4 The scheduler looks up a task’s code by kind; a task no code can take stays pending, and only an abort ends it, as orphaned.
9.2 Each record table lifts its query columns out of a JSON record; document content lives apart, one row per commit that changes it.
```

<aside class="note">9.9 工具、提示词小节和任务阶段只通过一个环境触达文件与进程，而这个环境由宿主每次使用时从已提交的状态构建。</aside>
<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>Harness.open (storage, options, ctx) open a Harness on a storage; throws if the registry lacks the built-in tasks</td><td>在一个 storage 上打开 Harness；若注册表缺少内置任务则抛出</td><td>1.2</td></tr>
<tr><td>createRegistry () a new registry; it already holds the built-in tasks 7.1</td><td></td><td></td></tr>
<tr><td>createSession (storage) a bare Session: storage and commits, no agent machinery</td><td></td><td>2.2</td></tr>
<tr><td>MemoryStorage new MemoryStorage() in-memory storage, lost on exit; good for tests 9.4</td><td></td><td></td></tr>
<tr><td>defineDoc (definition) declare a document kind (one per owner) 4.1</td><td>声明一个文档 kind（每个 owner 一个）</td><td></td></tr>
<tr><td>defineDocFamily (definition) declare a document kind with many keyed members 4.2</td><td>声明一个带许多带键成员的文档 kind</td><td></td></tr>
<tr><td>defineEntry (kind) declare an entry kind, with an is() type check 3.1</td><td></td><td></td></tr>
<tr><td>defineTask (definition) declare a durable task; register it through an extension 5.1</td><td></td><td></td></tr>
<tr><td>defineExtension (extension) declare an extension (adds types only) 7.1</td><td></td><td></td></tr>
<tr><td>defineTool (tool) declare a tool; args are typed from parameters 7.4</td><td></td><td></td></tr>
<tr><td>section (key, render, { tag }?) declare a system-prompt section; wrapped in &lt;key&gt; tags unless tag: false</td><td></td><td></td></tr>
<tr><td>7.5</td><td></td><td></td></tr>
<tr><td>hook (task, handlers) attach handlers to a built-in or custom task, matched by name</td><td></td><td>7.3</td></tr>
<tr><td>wrapTool (tool, wrapper) wrap the tool with that name wherever the extension is selected</td><td></td><td></td></tr>
<tr><td>7.4</td><td></td><td></td></tr>
<tr><td>wrapSection (key, wrapper) wrap the section with that key 7.5</td><td></td><td></td></tr>
<tr><td>configure (tx, conversationId, change)</td><td></td><td>7.2</td></tr>
<tr><td>watchEvents (harness, conversationId, ctx)</td><td></td><td>8.3</td></tr>
<tr><td>ReadAfterWrite, StorageRejected, ConversationBusy</td><td></td><td></td></tr>
<tr><td>…/env ExecutionEnv, FileSystem, Shell, FileError, ExecutionError, line-scan helpers 9.5</td><td></td><td></td></tr>
<tr><td>…/env/node NodeExecutionEnv 9.5</td><td></td><td></td></tr>
<tr><td>…/tools CodingTools, createReadTool, createWriteTool, createEditTool, createBashTool 7.4</td><td></td><td></td></tr>
<tr><td>…/storage/memory MemoryStorage 9.4</td><td></td><td></td></tr>
<tr><td>…/storage/sqlite SqliteStorage, SqliteDatabase, applySqliteMigrations, SQLITE_MIGRATIONS 9.2</td><td></td><td></td></tr>
<tr><td>…/storage/sqlite/node openNodeSqliteStorage, openNodeSqliteDatabase 9.2</td><td></td><td></td></tr>
<tr><td>…/storage/jsonl JsonlStorage, JsonlCorruptionError, JsonlStoragePoisonedError 9.3</td><td></td><td></td></tr>
<tr><td>…/storage/jsonl/node openNodeJsonlStorage(directory, ctx, { fsync }?) 9.3</td><td></td><td></td></tr>
<tr><td>…/testing registerStorageConformance, registerEnvConformance, createStorageConformance, createEnvConformance</td><td></td><td></td></tr>
<tr><td>9.4</td><td></td><td></td></tr>
<tr><td>Submission.id property SubmissionId; keep it to find the submission after a restart 6.1 (p. 84)</td><td></td><td></td></tr>
<tr><td>Submission.status (ctx) the stored record, now 6.1 (p. 84)</td><td></td><td></td></tr>
<tr><td>Submission.wait (ctx) the record, once done or unanswered 6.1 (p. 84)</td><td></td><td></td></tr>
<tr><td>Submission.abort (ctx) "aborted" | "already_placed" | "settled" 6.1 (p. 84)</td><td>与</td><td></td></tr>
<tr><td>ConversationHandle.submit (inputDraft, ctx) submit user input from inside a task; no writes 7.7 (p. 121)</td><td></td><td></td></tr>
<tr><td>ConversationHandle.abort (ctx, { background }?) as Conversation.abort 7.7 (p. 121)</td><td></td><td></td></tr>
<tr><td>ConversationHandle.waitForIdle (ctx) as Conversation.waitForIdle 7.7 (p. 121)</td><td></td><td></td></tr>
<tr><td>taskId, conversationId properties identity of the task and its conversation 5.1 (p. 63)</td><td></td><td></td></tr>
<tr><td>signal property AbortSignal: fires on abort, close, or when this run of the handler ends 5.6 (p. 80)</td><td></td><td></td></tr>
<tr><td>registry property the registry as it was when this phase started 7.6 (p. 118)</td><td></td><td></td></tr>
<tr><td>settings, models properties settings re-read on each access; pi-ai Models 7.2 (p. 106)</td><td></td><td></td></tr>
<tr><td>agent (ctx) the conversation’s Agent, fixed for this phase 7.2 (p. 106)</td><td></td><td></td></tr>
<tr><td>env (ctx) the conversation’s environment, or undefined 9.5 (p. 155)</td><td></td><td></td></tr>
<tr><td>taskId, conversationId, callId properties the tool task, its conversation, and the model’s call ID 7.4</td><td></td><td></td></tr>
<tr><td>registry property the registry as of this call 7.6</td><td>属性 本次调用时的注册表</td><td></td></tr>
<tr><td>agent (ctx) the calling conversation’s agent 7.2</td><td>发起调用的会话的</td><td></td></tr>
<tr><td>env property built for this call, or undefined 9.5</td><td>属性 为本次调用构建，或</td><td></td></tr>
<tr><td>output (chunk, skipped?) stream output to the UI while running 7.4</td><td>运行期间把输出流向 UI</td><td></td></tr>
<tr><td>outputWindow property how much output tail is kept and how often it is committed, or undefined</td><td>属性 保留多少输出尾部、多久提交一次，或 <code>undefined</code></td><td>9.5</td></tr>
<tr><td>diagnostic (diagnostic) add a note the model sees with the result 7.4</td><td>加一条模型会随结果看到的说明</td><td></td></tr>
<tr><td>details (value, ctx) replace the structured details shown while running 7.4</td><td>替换运行期间展示的结构化详情</td><td></td></tr>
<tr><td>commit (change, ctx) a commit made on behalf of this tool call 7.4</td><td>代这次工具调用所做的一次提交</td><td></td></tr>
<tr><td>memo as on TaskRuntime a small stored value; the first write wins 5.2 (p. 67)</td><td>同</td><td></td></tr>
<tr><td>createTask (task, input, options, ctx)</td><td>子任务的</td><td></td></tr>
<tr><td>getTask, waitForTask (id, ctx) the record; the record once finished 5.5 (p. 76)</td><td></td><td></td></tr>
<tr><td>conversation (id, ctx) ConversationHandle | undefined 7.7</td><td></td><td></td></tr>
<tr><td>snapshot, snapshotAsOf, watchDoc</td><td></td><td></td></tr>
<tr><td>install (extension) add an extension, or replace one with the same name; takes effect at once 7.1 (p. 103)</td><td>添加一个扩展，或替换同名的那个；立即生效</td><td></td></tr>
<tr><td>uninstall (extension) remove the extension with that name 7.1 (p. 103)</td><td>移除那个名字的扩展</td><td></td></tr>
<tr><td>snapshot () a frozen view of what is installed now 7.1 (p. 103)</td><td></td><td></td></tr>
<tr><td>subscribe (listener) unsubscribe function; called after every change 7.6 (p. 118)</td><td></td><td></td></tr>
<tr><td>snapshot installed, extension (); (name) extensions in install order; one by name 7.1 (p. 103)</td><td></td><td></td></tr>
<tr><td>snapshot tools, sections () every installed tool or section with its extension 7.1 (p. 103)</td><td></td><td></td></tr>
<tr><td>snapshot tasks, task (); (name) built-in and installed task definitions 5.4 (p. 73)</td><td>当前已安装内容的冻结视图</td><td></td></tr>
<tr><td>models pi-ai Models required 6.3 (p. 91)</td><td></td><td></td></tr>
<tr><td>registry RegistryReader required; must hold the built-in tasks 7.1 (p. 103)</td><td></td><td></td></tr>
<tr><td>settings HarnessSettings every field at its default 7.2 (p. 106)</td><td></td><td></td></tr>
<tr><td>env (target, ctx) =&gt; ExecutionEnv | undefined none: no environment 9.5 (p. 155)</td><td></td><td></td></tr>
<tr><td>conversationCreated (tx, record) =&gt; void none 4.2 (p. 53)</td><td></td><td></td></tr>
<tr><td>now () =&gt; number Date.now 5.2 (p. 67)</td><td></td><td></td></tr>
<tr><td>onReport (error) =&gt; void none; must not throw 7.3 (p. 109)</td><td></td><td></td></tr>
<tr><td>aborted a queued item is withdrawn, or a run’s task aborts 6.1 (p. 84)</td><td>一个排队项被撤回，或一次运行的任务被中止</td><td></td></tr>
<tr><td>stale a head write targets an entry before the active range 6.1 (p. 84)</td><td>一次头指针写入指向活跃范围之前的条目</td><td></td></tr>
<tr><td>reset a reset placed at postTools ends the run before an answer 3.4 (p. 46)</td><td>放在</td><td></td></tr>
<tr><td>no_model the agent has no model, or it does not resolve 6.3 (p. 91)</td><td>智能体没有模型，或模型解析不出来</td><td></td></tr>
<tr><td>model_error the provider failed after retries; detail is its text 6.3 (p. 91)</td><td>供应商在重试之后仍失败；detail 是它的文本</td><td></td></tr>
<tr><td>faulted the run task faulted; detail is the error message 5.6 (p. 80)</td><td>运行的任务故障了；detail 是错误消息</td><td></td></tr>
<tr><td>missing_task, task_too_old, migration_failed a blocked run task was aborted and orphaned 5.4 (p. 73)</td><td></td><td></td></tr>
<tr><td>Agent what a conversation runs with: model, thinking level, extensions, tools, instructions, cwd 7.2 (p. 106)</td><td>智能体（<code>Agent</code>）—— 会话运行时所带的东西：模型、思考级别、扩展、工具、指令、cwd</td><td></td></tr>
<tr><td>Background a conversation-owned task excluded from idle waits, conversation aborts and cascades 5.5 (p. 76)</td><td>）—— 由会话拥有、被排除在空闲等待、会话中止和级联之外的任务 5.5 (p. 76) 基线（</td><td></td></tr>
<tr><td>Base a complete stored document value; later changes are deltas on top of it 4.3 (p. 56)</td><td>）—— 完整的已存储文档值；之后的改动是叠加在它之上的增量 4.3 (p. 56) 阻塞（</td><td></td></tr>
<tr><td>Blocked a live task no registered definition can take; derived, never stored 5.4 (p. 73)</td><td>）—— 没有已注册定义能接手的存活任务；推导得出，从不存储</td><td></td></tr>
<tr><td>Boundary a point between turns where the inbox places items: postTools or final 6.1 (p. 84)</td><td>）—— 轮次之间收件箱放置条目的一个时点：</td><td></td></tr>
<tr><td>Checkpoint the complete durable state a task resumes from; its phase names the handler 5.1 (p. 63)</td><td>）—— 任务 resume 出发点处那份完整的持久状态；它的 phase 指明处理器</td><td></td></tr>
<tr><td>Chord the replicated-state library that represents documents as values and operations 8.1 (p. 125)</td><td>—— 把文档表示为值与操作的复制状态库 8.1 (p. 125) 提交（</td><td></td></tr>
<tr><td>Commit one atomic write of records and documents on the mutation line 2.2 (p. 29)</td><td>）—— 在变更线上对记录与文档的一次原子写入 2.2 (p. 29) 完成中（</td><td></td></tr>
<tr><td>Completing a task whose outcome is decided but held while owned work is live 5.5 (p. 76)</td><td>）—— outcome 已定，但被持有的任务因其所拥有的工作仍存活而暂缓 5.5 (p. 76) 上下文（</td><td></td></tr>
<tr><td>Context the messages derived from a transcript for the next model request 3.2 (p. 40)</td><td>）—— 为下一次模型请求从记录（transcript）派生出的消息 3.2 (p. 40) 会话（</td><td></td></tr>
<tr><td>Conversation a transcript scope; may fork another and be owned by a task 3.3 (p. 43)</td><td>）—— 一个记录作用域；可以分叉出另一个，也可以被某个任务拥有 3.3 (p. 43) 定义（</td><td></td></tr>
<tr><td>Definition a typed token describing a document, document family, entry kind or task 4.1 (p. 50)</td><td>）—— 描述文档、文档族、条目 kind 或任务的带类型词元 4.1 (p. 50) 文档（</td><td></td></tr>
<tr><td>Document typed mutable JSON state stored as Chord operations and bases 4.1 (p. 50)</td><td>）—— 以 <code>Chord</code> 操作和基线存储的带类型可变</td><td></td></tr>
<tr><td>Effect sandwich commit intent, perform the effect, commit the outcome 5.3 (p. 70)</td><td>）—— 提交意图、执行效果、提交结果 5.3 (p. 70) 条目（</td><td></td></tr>
<tr><td>Entry an immutable transcript record with a kind, model messages and data 3.1 (p. 37)</td><td>）—— 一条不可变的记录事件，带一个 kind、模型消息和 data 3.1 (p. 37) 扩展（</td><td></td></tr>
<tr><td>Extension a named bundle of tools, sections, hooks, wraps and tasks 7.1 (p. 103)</td><td>）—— 一组命名的工具、小节、钩子、包裹器和任务 7.1 (p. 103) 分叉（</td><td></td></tr>
<tr><td>Fork a conversation that inherits a parent’s history up to parent.at 3.3 (p. 43)</td><td>）—— 继承父会话历史直到</td><td></td></tr>
<tr><td>Generation one model request and its classification, run by pi.generation 6.3 (p. 91)</td><td>）—— 一次模型请求及其分类，由</td><td></td></tr>
<tr><td>Harness one open storage plus the machinery that runs agents on it 1.2 (p. 13)</td><td>—— 一个打开的 storage，加上在其上运行智能体的机制 1.2 (p. 13) 头指针（</td><td></td></tr>
<tr><td>Head an entry field naming the first entry of the active context 3.4 (p. 46)</td><td>）—— 条目上的一个字段，命名活跃上下文的第一条条目</td><td></td></tr>
<tr><td>Hook an extension handler called by a built-in task, such as beforeTool 7.3 (p. 109)</td><td>）—— 由内置任务调用的扩展处理器，比如</td><td></td></tr>
<tr><td>Inbox the pi.inbox document of queued submissions 6.1 (p. 84)</td><td>）—— 排队提交项的</td><td></td></tr>
<tr><td>Invocation one in-memory run of a task’s phase or abort handler 5.4 (p. 73)</td><td></td><td></td></tr>
<tr><td>Memo a small first-writer-wins value stored on a live task 5.2 (p. 67)</td><td></td><td></td></tr>
<tr><td>Mutation line the Session’s single serialized path for commits 2.2 (p. 29)</td><td>）——</td><td></td></tr>
<tr><td>Orphaned a blocked task settled by an abort without running any task code 5.6 (p. 80)</td><td>）—— 被中止结算掉、没有运行任何任务代码的阻塞任务</td><td></td></tr>
<tr><td>Outcome the terminal result of a task: completed, failed, aborted, orphaned, faulted 5.1 (p. 63)</td><td></td><td></td></tr>
<tr><td>Owner, owned work the conversation or task that created a task or conversation; owned work holds and aborts with it 5.5 (p. 76)</td><td>）、所拥有的工作（</td><td></td></tr>
<tr><td>Phase a named step of a task, one handler per phase 5.2 (p. 67)</td><td>）—— 任务的一个命名步骤，每个阶段一个处理器 5.2 (p. 67) 注册表（</td><td></td></tr>
<tr><td>Registry the process-local, unstored set of installed extensions 7.1 (p. 103)</td><td>）—— 进程内、不存储的已安装扩展集合</td><td></td></tr>
<tr><td>Replay a tool’s declaration whether an interrupted call may rerun: safe or unsafe 6.4 (p. 94)</td><td>）—— 工具关于一次被中断的调用能否重跑的声明：</td><td></td></tr>
<tr><td>Run the turns from an admitted input to its final answer; the conversation is busy meanwhile 6.2 (p. 88)</td><td>）—— 从一个被受理的输入到它最终答案之间的那些轮次；期间会话一直是忙的 6.2 (p. 88) 小节（</td><td></td></tr>
<tr><td>Section a named part of the system prompt, rendered before each request 7.5 (p. 115)</td><td>）—— 系统提示词的一个命名部分，在每次请求之前渲染</td><td></td></tr>
<tr><td>View a conversation’s structural mount: record, active entries, built-in documents 8.2 (p. 129)</td><td>视图（<code>View</code>）—— 会话的结构化挂载：记录、活跃条目、内置文档</td><td></td></tr>
<tr><td>Watch a serialized exact-frame observation with at most 100 pending frames 8.2 (p. 129)</td><td>）—— 序列化的精确帧观察，最多 100 个待处理帧 8.2 (p. 129) 包裹（</td><td></td></tr>
<tr><td>Wrap an extension’s decorator of a tool or section, targeted by name 7.4 (p. 112)</td><td>）—— 扩展对某个工具或小节的装饰器，按名字定位</td><td></td></tr>
<tr><td>ex 00–05 Session layer: conversations, documents, forks, owned conversations, Chord state, watches</td><td></td><td></td></tr>
<tr><td>ex 06–11 Harness, configuration, conversations, context, registry reload, extension state</td><td></td><td></td></tr>
<tr><td>ex 12–13 a durable task; close, reopen and continue</td><td></td><td></td></tr>
<tr><td>ex 14–19 chat, system prompt, real model, coding tools, print mode, JSON mode</td><td></td><td></td></tr>
<tr><td>ex 20–21 the inbox while busy; late join</td><td></td><td></td></tr>
<tr><td>ex 22–24 foreground and background subagents; child tasks</td><td></td><td></td></tr>
<tr><td>ex 25 compaction: background, manual, overflow</td><td></td><td></td></tr>
<tr><td>ex 26–31 coding agent, plan mode, reviewer, sandbox per conversation, tool override, reload and restart</td><td></td><td></td></tr>
<tr><td>Examples live in test/examples/NN-*.ts; their captured output is research/runs/NN-*.txt (cited run NN). Ex 16 needs a real model and has no run file. All</td><td></td><td></td></tr>
<tr><td>others use pi-ai’s faux provider.</td><td></td><td></td></tr>
<tr><td>Earendil Engineering, “Pi Durable”, 1 October 2026, https://earendil.com/posts/pi-durable/ motivation only; never API facts</td><td></td><td></td></tr>
</table>
