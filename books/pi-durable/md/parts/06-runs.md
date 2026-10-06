<a id="sec-6-1"></a>

## 6.1 提交项与收件箱

> 每条消息在你发出的瞬间就被提交；会话繁忙时它会排队，由一个边界决定它何时落地。

用户在智能体还在回答第一条消息时又打了第二条。它该打断、等待，还是被拒绝？如果进程下一秒就死了，这条消息会丢吗？Pi Durable 用一条规则回答：一条消息在被做任何其他事情之前就已提交。一次提交是一次原子保存：其中的内容要么一起存下，要么都不存。读完本节，你就能预测在任意时刻发出的消息会遭遇什么，并选择繁忙的会话该怎样对待它。

### 提交项的两种

提交项是你交给某个会话的东西的持久记录。它有两种。输入是一条用户消息；它可能开启一次运行，以及为回答它而进行的模型调用和工具调用。写入是不向模型问任何问题、就往记录里加一个条目，比如来自你应用的一条备注。`Conversation.submit()` 用一次提交写下这条记录，并返回一个提交项句柄。句柄上有 `status()`、`wait()` 和 `abort()`。

:::note
`SubmissionDraft` `src/harness/types.ts` `TS`
:::

```
type SubmissionDraft = { requestId?: string } & (
| { type: "input"; content: UserInput;
whenBusy?: "steer" | "followUp" | "reject" }
| { type: "write"; entry: EntryDraft });
```

:::note
已简化：源码把每个字段标记为 `readonly`，并加上 `never` 字段把两个分支区分开。
:::

### 提交项的去向

提交项处于四种状态之一。等待期间它是 queued。输入一旦消息进入记录、且有一次运行正在回答它，就变成 placed。有了自己的条目——对输入来说还有了答案——就是 done。结束时没有答案就是 unanswered；reason 说明原因。`wait()` 只在 done 或 unanswered 时兑现。

<img src="/pi-lessons/_assets/pi-durable/06-runs/fig-6.1.png" alt="THE SUBMISSION LIFECYCLE
S T A T E" loading="lazy">

*提交项会排队、placed 或落定；只有输入才会被 placed。取自 `src/harness/submissions.ts`、`inbox.ts` 和 `live.ts`；reason 取自 spec §6 和 §8.3。玫红色箭头表示没有答案就结束。*

它走哪条路取决于一个问题：会话是否繁忙？只要有一次运行正在进行，会话就是繁忙的（运行控制（p. 88））。

:::note
`idle`，没有排队：输入被 placed 并开启一次运行；写入被追加并 `done`。`busy`，或已有其他项排队：提交项在收件箱中排队。
:::

```
busy, with whenBusy: "reject" nothing is written; submit() throws ConversationBusy
a requestId already used nothing is written; you get the existing submission back From src/harness/submissions.ts and the admission table of spec §6. A write that would undo a reset is the one exception; see Details below.
```

`requestId` 检查让重试变得安全。如果一次提交超时或进程重启，用同一个 ID 再发一次，你拿回的是同一个提交项，而不是第二份副本。这个 ID 的作用域是一个会话。

### 收件箱

排队的提交项在 `pi.inbox` 里等待，它是一个小型内置文档，每个会话一个（内置文档（p. 60））；分叉开始时它为空。每个项都有一个 mode，说明它可以何时落地。`steer`——「在智能体当前的工具调用一结束就告诉它」。这条消息加入正在进行的运行。`followUp`——「在当前回答之后处理这个」。这条消息开启下一次运行。这是默认的 `whenBusy`。`write`——一项排队的写入。它在下一个机会落地，早于任何用户消息。

<img src="/pi-lessons/_assets/pi-durable/06-runs/fig-6.2.png" alt="TWO BOUNDARIES, ONE INBOX
F L O W" loading="lazy">

*一个 `postTools` 边界接收写入和 steer；只有 final 边界接收 follow-up。一次工具调用占住第一次运行，同时一个 follow-up、一个 steer 和一条备注在排队；每条连接线把一个排队项连到它变成的条目。回答 21 与 final 边界在同一次提交里被追加，而不是从收件箱取出。ID、序号和 `pi.live.run` 取值来自 `research/capture/inbox-steps.txt`。*

### 边界：排队项何时落地

边界就是排队项进入记录的那次提交。有两种。`postTools` 边界在运行仍在进行时、一轮工具调用之后运行。final 边界在一次运行成功结束时运行。

:::note
`postTools`：`all` 全部接收／取第一个／其余不加入当前运行。`final`：`all` 全部接收／取第一个／第一个开启一次新运行。spec §6；`src/harness/inbox.ts`。把 `steeringMode` 或 `followUpMode` 设为 `"all"`，就会取该 mode 的每一项而不是第一项（两者默认都是 `"one-at-a-time"`）。一次排队的重置会把 `postTools` 边界变成 final 边界（见下文「详解」）。向仍然有排队项的空闲会话提交时，会排在它们之后，并立即运行一次 final 边界（`src/harness/submissions.ts`）。
:::

边界先落写入，再落用户消息，各自按提交的顺序。因此一条排在重置或压缩摘要之前排队的消息会落在它之后，模型在新上下文里读到它。

:::note
一个 `postTools` 边界接收写入和 steer；只有 final 边界接收 follow-up。一次工具调用占住第一次运行，同时一个 follow-up、一个 steer 和一条备注在排队；每条连接线把一个排队项连到它变成的条目。回答 21 与 final 边界在同一次提交里被追加，而不是从收件箱取出。ID、序号和 `pi.live.run` 取值来自 `research/capture/inbox-steps.txt`。
:::

### 撤回、失败与崩溃

`Submission.abort()` 撤回一个仍在排队的提交项。它以 `unanswered` 落定，reason 为 `aborted`，调用返回 `"aborted"`。一旦 placed 就太晚了：调用返回 `"already_placed"`，如果已经结束则返回 `"settled"`。`Conversation.abort()` 撤回每一个排队的输入，但保留排队的写入。只有成功的运行才会应用 final 边界。失败或被中止的运行把自己的输入以 `unanswered` 落定，并不碰收件箱。

:::note
排队的 follow-up 会留在收件箱里，它们的 `wait()` 也不会兑现，直到有别的东西被提交或者你撤回它们。下一次提交会排在它们之后，于是更早的那个 follow-up 先运行（`test/harness-inbox.test.ts`）。
:::

崩溃不改变这一切：每条记录和每个收件箱项都已经提交。重新打开后，排队的 follow-up 在被中断的运行结束时仍会运行。只有内存里的等待者丢失了。用 `harness.submission(id)` 取一个新句柄，在它上面等待。详解：会移动头指针的写入 一次写入可以设置头指针，它决定模型的上下文从哪里开始（重置、交接与头指针（p. 46））。一个指向早于当前起点的头指针，会把已被重置或摘要切断的历史带回来。这样的写入是 stale 的：无论它是在空闲时提交的，还是抵达了某个边界，都以 `unanswered` 落定，reason 为 `stale`。重置（`head: "self"`）永远不是 stale。如果一个 `postTools` 边界取到一次重置，它就当作 final 边界，而当前运行的输入以 reason `reset` 落定，因为它们的上下文在答案之前就被切断了。压缩依赖的是同一条规则（压缩（p. 97））。

:::note
任何你可能重试的 `submit()` 都带上 `requestId`。按消息选择 `whenBusy`：要让智能体在运行中途看到纠正用 `steer`，下一个问题用 `followUp`，界面该拒绝时用 `reject`。运行失败后，重新提交或撤回排队的 follow-up；不要永远等它们。重启之后，用 `harness.submission(id)` 取回句柄。
:::

```
Sources: spec §6; src/harness/submissions.ts; src/harness/inbox.ts; src/harness/types.ts (SubmissionDraft, Submission, QueueMode); src/types.ts (SubmissionRecord); src/harness/agent.ts (resolveSettings); src/harness/generation.ts; README §Busy Conversations; test/harness-inbox.test.ts; test/harness-submissions.test.ts; ex 20; run 20; research/capture/inbox-steps.txt
```

<a id="sec-6-2"></a>

## 6.2 运行控制与实时文档

> 一个小文档说明会话是否繁忙，并展示答案和工具输出形成的过程；崩溃只丢失上一次

> 成功提交之后的进展。这个间隔可以超过配置值。

智能体工作时，有两个问题要紧。会话是否繁忙？以及屏幕上此刻该显示什么：写了一半的答案，还是工具滚动的输出？两个答案都在同一个文档 `pi.live` 里。它和其他一切一样被提交，所以晚连接的界面，或者重启的进程，看到的是同一幅画面。读完本节，你就能读 `pi.live` 并说出会话是否繁忙、用户看到什么，以及崩溃会丢失什么。

### 结构

`pi.live` 是一个内置文档，每个会话一个。每个字段都是可选的；空闲会话的取值是 `{}`。

:::note
`LiveState`，已简化 `src/harness/live.ts` `TS`
:::

```
type LiveState = {
run?: { taskId: TaskId; inputs: SubmissionId[] }; // present while busy generation?: { // the model call in progress
attempt: number;
message?: AssistantMessage; // the answer so far retry?: { at: number; error: string }; // waiting to retry
deferred?: { pollAt: number }; // provider answers later
}; tools?: ToolSlot[]; // this round's tool calls
compactions?: CompactionStatus[]; // see 6.5
};
```

:::note
存储的消息是 `AssistantMessage` 的 JSON 形式。每个 `ToolSlot` 显示一次调用：它的 `callId`、名称，状态为 `pending`、`running` 或 `done`，以及
:::

:::note
到目前为止的输出，以及 `done` 之后的结果条目。
:::

### 运行控制：busy 标志

`run` 就是那把锁。只要 `run` 存在，会话就恰好是繁忙的，`submit()` 不检查别的（提交项（p. 84））。`inputs` 列出这次运行将要回答的提交项。`taskId` 指出负责回答它们的生成，也就是发起当前模型调用的那个任务（生成（p. 91））。一次运行是一条生成的链，每个轮次一条。轮次之间锁是移交，而不是释放：旧的生成创建下一个生成，并在同一次提交里改写 `taskId`。在那一刻落地的 steer 会被追加到 `inputs`。运行结束时，一次提交让列出的每个输入落定，并删除 `run`、`generation` 和 `tools`。

<img src="/pi-lessons/_assets/pi-durable/06-runs/fig-6.3.png" alt="PI.LIVE OVER ONE RUN
T I M E L I N E" loading="lazy">

*`pi.live` 在整个运行期间持有运行控制，只在有东西正在运行时才持有实时进展。一次输入、一次打印五行内容的 `count` 工具调用、一个答案；时间取自 `research/capture/extra-p6/live-run.txt`。(1) 提交设置 `run`；(2) 模型要这个工具，于是 `generation` 让位给 `tools`；(3) 这一轮把 `run` 交给 generation 14；(4) 回答清空一切。*

### 实时进展，及其代价

`generation` 和 `tools` 的存在，是为了让界面能展示答案和工具输出形成的过程。它们就是普通的已提交状态，像任何其他文档一样发布（会话视图（p. 129））。每次更新都是一次提交，所以更新被节流。`settings.progress` 有两个间隔，默认都是 100 ms：`partialIntervalMs`——流式答案多久提交一次。在那次抓取中，第一个分片在请求开始后 103 ms 落地。

`outputIntervalMs`——工具输出多久提交一次。安静一阵之后的第一行会立即提交；随后的写入至少间隔一个间隔，输出越大就隔得越开。

用远程存储的宿主可以调高这两个间隔，用更大的步长展示进展。这个文档始终很小：只要没有东西在运行，它就作为一份完整快照存储，所以它的变更历史不会超过一次模型调用或一轮工具（基线与增量（p. 56））。

### 崩溃留下什么

崩溃会丢失尚未提交的答案文本或工具输出。自上一次成功提交以来的间隔可以超过配置的进展间隔。在那次崩溃抓取中，进程在最后一次输出提交后约 50 ms 被杀死，所以 deploy 那个槽位仍然保留着它打印过的全部六行。

:::note
会话 1，`SIGKILL` 之后的 `pi.live` `research/capture/crash-reopen-tasks.txt` `JSON`
:::

```json
{
"run": { "taskId": 15, "inputs": [14] },
"tools": [{
"callId": "deploy-1", "name": "deploy", "taskId": 22, "status": "running",
"output": "deploy site: step 1/10 (pid 98319)\n … step 6/10 (pid 98319)\n"
}]
```

```
}
```

:::note
输出的第 2–5 行被省略。会话仍然繁忙；在恢复判定发生了什么之前，没有东西回答输入 14。
:::

恢复会把这些进展变成记录，而不是变成沉默。一个已提交的分片答案变成一条 `aborted` 的助手条目，于是记录和界面保留住了它已经开始说的内容。后续的模型请求会排除那条 `aborted` 的答案。一个运行中工具的已提交输出会成为一条 `interrupted` 结果的正文，或者在安全重跑之前被清除（工具调用与重放（p. 94））。

详解：谁设置并清除每个字段

:::note
`run`：一次运行开始时设置；运行结束时，在每条路径上清除。`generation`：一次模型请求开始、等待重试、或等待一个延迟答案时设置；响应被处理或运行结束时清除。`tools`：模型要工具时设置；这一轮结束或运行结束时清除。`compactions`：一次压缩开始时设置；结束时清除。spec §8.2；`src/harness/live.ts`、`generation.ts`、`tool.ts`、`compaction.ts`。如果调度器放弃了一个运行任务（`faulted` 或 `orphaned`，中止、故障与孤儿（p. 80）），同一次提交会让它的输入以 `unanswered` 落定并清除它的字段。
:::

:::note
用 `run` 驱动繁忙指示，用 `generation` 和 `tools` 驱动流式视图。在缓慢或远程的存储上，调高 `settings.progress` 的间隔。崩溃丢失未提交的进展，没有固定的时间上界，而保存下来的 `run` 依然存在。
:::

```
Sources: spec §6, §8.2, §12; src/harness/live.ts; src/harness/generation.ts; src/harness/tool.ts; src/harness/output.ts;
src/harness/agent.ts (DEFAULT_PROGRESS_POLICY); src/harness/types.ts (ProgressPolicy); CHANGELOG 1.0.3; test/harness-live-deltas.test.ts; test/harness-generation.test.ts; research/capture/extra-p6/live-run.txt; research/capture/inbox-steps.txt; research/capture/crash-before.txt; research/capture/crash-reopen-tasks.txt
```

<img src="/pi-lessons/_assets/pi-durable/06-runs/fig-6.4.png" alt="THE PHASES OF PI.GENERATION
S T A T E" loading="lazy">

*一次生成依次准备、调用模型、对响应分类，然后结束或循环。取自 `src/harness/generation.ts`。琥珀色方框是任务的各个阶段；`request` 和 `poll` 调用供应商。白色方框是任务的结束方式。虚线方框是任务在等待它自己拥有的一次压缩，之后它以同一个 attempt 重新准备。工具轮之后任务完成，由一个新的生成接管这次运行。未画出：中止，它可以结束任何阶段中的任务；以及缺失的模型，它会在 `prepare`、`request` 或 `poll` 中让任务以 `no_model` 失败。*

<a id="sec-6-3"></a>

## 6.3 生成

> 每次模型调用在发出之前都保存自己的模型、选项和记录截止点。恢复会重建那份上下文，并再次运行请求钩子。

调用模型是智能体中缓慢、昂贵且容易失败的一步。供应商可能返回 503，上下文可能太长，进程也可能在流式输出中途死去。Pi Durable 把每次模型调用作为一个持久任务运行，称为一次生成。它提交模型、选项和记录截止点。崩溃之后，它从这些记录重建请求，然后重新运行请求钩子。读完本节，你就能跟随一次模型调用走过它的各个阶段，读出它的重试状态，并说出每个阶段崩溃的代价。

### 一次生成，一个轮次

一次生成是一个 `pi.generation` 任务（阶段与步骤（p. 67））。它发起一次模型调用，决定接下来发生什么，并拥有自己轮次里的工具调用。一次运行是一条生成的链，把运行控制从一次传给下一次（运行控制（p. 88））。

```
One generation prepares, calls the model, classifies the response, and ends or loops. From src/harness/generation.ts. Amber boxes are the task’s phases; request and poll call the provider. White boxes are how the task ends. The dashed box is the task waiting on a compaction it owns, after which it prepares again with the same attempt. After the tool round the task completes and a new generation takes the run. Not drawn: an abort, which can end the task in any phase, and a missing model, which fails it with no_model in prepare, request or poll.
prepare builds the system prompt and tool list; checks the compaction budgets the attempt number request calls the model and streams the answer the model, thinking level, stream options and cutoff retry waits out the backoff the time to wake, until poll waits for a provider that answers later the provider’s handle and pollAt tools waits for the round’s tool calls the assistant entry and the tool task IDs
```

```
The GenerationCheckpoint union in src/harness/generation.ts. Every task starts at { phase: "prepare", attempt: 1 }.
```

### 先准备，再发送

`prepare` 读取会话的 agent 和 settings（每会话的 agent（p. 106））。没有可用模型时，运行以 reason `no_model` 失败。它渲染系统提示词（系统提示词（p. 115）），并检查上下文是否需要先压缩（压缩（p. 97））。然后一次提交进入 `request`，并钉住模型、选项和记录 cutoff。`cutoff` 是请求所包含的最新记录条目。恢复会用保存下来的模型和选项，重建截至 `cutoff` 的已提交上下文。接着它重新运行 `beforeRequest` 钩子：它们对消息的替换不会被保存，在重放时可能改变。被改动过的 agent，其模型和选项从下一次 `prepare` 起生效，而每次重试都会经过 `prepare`。`request` 构建消息，让 `beforeRequest` 钩子调整它们（钩子（p. 109）），然后流式输出响应。分片答案按实时文档的节流提交（p. 88）。每个请求都带一个 `sessionId`：每个会话一个 ID，保存在内置的 `pi.provider` 文档里。供应商用它做提示词缓存。它能挺过重启、重试、重置和模型更换；分叉会拿到一个新的。

### 响应决定了什么

每个响应都作为一条 `pi.assistant` 条目被追加，并记录它的开销（用量（p. 100）），失败也不例外。后续请求会把失败和被中止的消息排除在外（从记录到上下文（p. 40））。停止原因决定下一步。

:::note
工具调用（`toolUse`）：运行工具轮（工具调用（p. 94））。一个答案（`stop` 或 `length`）：回答这些输入；运行 final 边界。
:::

```
an error: context too long compact once, then prepare again
an error the provider may recover from wait, then retry any other error, or aborted inputs settle unanswered with model_error; the run fails
```

```
deferred: “come back later” poll after pollAfterMs, 5000 ms by default
src/harness/generation.ts. A toolUse response with no calls counts as an answer. The too-long rescue needs compaction enabled and a place to cut; without them, or on a second overflow, the run fails with model_error.
```

一个答案可以被延长。在它让输入落定之前，`onYield` 钩子可以返回 `{ continue }`，带上更多用户内容。运行随后带着那条消息继续，输入保持未落定。只有当同一个边界上没有排队用户消息或重置要落地时，这才适用。

### 重试与迟到的答案

重试策略是 `settings.retry`。默认在第一次尝试之后允许 3 次重试，从 2000 ms 开始逐次翻倍，上限 60 000 ms。哪些错误可以重试由 `pi-ai` 决定。上下文太长绝不会这样重试；只有压缩能让它装得下。

:::note
一次 503，一次 50 ms 的退避，然后是答案 `research/capture/extra-p6/retry.txt` `TEXT`
:::

```
seq 4 task 9 {"phase": "request", "attempt": 1, "cutoff": 7, …} seq 6 entry 10 pi.assistant, stopReason "error"
task 9 {"phase": "retry", "attempt": 1, "until": 1791211854633}
pi.live generation.retry = {"at": …, "error": "503 service unavailable"} seq 7 task 9 {"phase": "prepare", "attempt": 2}
seq 8 task 9 {"phase": "request", "attempt": 2, "cutoff": 10, …}
seq 9 entry 11 pi.assistant; submission 8 done; task 9 completed
```

```
Run with settings.retry.baseDelayMs = 50; some commits are elided. The second request’s cutoff includes the error entry, which the context then leaves out.
```

两种等待都能挺过重启。`retry` 睡到已提交的 `until` 为止，所以重新打开的进程会走完剩余的退避，而不是从头开始。`poll` 服务那些更晚回答的供应商：它睡到 `pollAt`，再问一次，并像处理流式响应那样处理结果。在 `poll` 期间中止，还会请供应商取消该请求。

### 每个阶段崩溃的代价

:::note
`prepare`：准备，从同一份记录重来。`request`：分片答案已提交——该分片变成一条 `aborted` 条目；保存的上下文被重建，请求钩子再次运行。`retry` 或 `poll`：等待的剩余部分。`tools`：这一轮的结束（工具轮（p. 94））。`test/harness-generation-recovery.test.ts` 和 `test/harness-tools-recovery.test.ts`。如果重启后钉住的模型已经不在，运行以 `no_model` 失败。
:::

一次被中断的请求可能被付两次费：供应商也许在崩溃之前已经做完了工作，而重发又做了一遍。已提交的分片带着自己的用量，所以账本会计入崩溃之前已流式输出的部分。

:::note
重发保留保存下来的模型和选项，但会重新运行请求钩子。如果你需要完全相同的消息，就让钩子的输出保持稳定。调整 `settings.retry`；`maxRetries` 计的是第一次尝试之后的重试次数。为「请求中途崩溃后偶发的双重计费」留出预算。
:::

```
Sources: spec §8, §8.3; src/harness/generation.ts; src/harness/provider.ts; src/harness/agent.ts (DEFAULT_RETRY_POLICY);
src/harness/types.ts (GenerationHooks, ConversationRetryPolicy); research/pi/packages/ai/src/utils/retry.ts; README §Persist and Resume; test/harness-generation.test.ts; test/harness-generation-recovery.test.ts; research/capture/extra-p6/retry.txt
```

<a id="sec-6-4"></a>

## 6.4 工具调用与重放

> 每次工具调用在运行之前都提交它的意图；崩溃之后，只有被声明为可安全重复的工具才会再运行，其余每一个都被报告为

> `interrupted`。

你的智能体调用了一个部署工具，进程在执行到一半时被杀死。重启之后，它该不该再部署一次？跑两次可能是灾难；悄悄忘掉它同样糟糕。Pi Durable 从不猜测。它提交「这次调用即将运行」这个事实，崩溃之后只重跑那些你声明为可安全重复的工具。其余每一次调用都作为 `interrupted` 报告给模型。读完本节，你就能判断一个工具该不该重放：`"safe"`，并预测崩溃之后模型看到什么。

### 每次调用一个任务

模型发起的每次工具调用都成为自己的 `pi.tool` 任务，由收到这次调用的生成拥有。这个任务有两个阶段。

:::note
`ToolTaskCheckpoint` `src/harness/tool.ts` `TS` `type ToolTaskCheckpoint =`
:::

```
| { phase: "call" }
// committed just before execute(): the final arguments and the replay policy
| { phase: "execute"; arguments: JsonObject; replay: "safe" | "unsafe" };
```

一次调用经过这些步骤：1. 按名字找到工具，并按它的 schema 检查参数。2. 运行 `beforeTool` 钩子，它们可以阻止这次调用或改变它的参数（钩子（p. 109））。3. 提交意图：阶段 `execute`，带上最终的参数和工具的重放策略，默认 `"unsafe"`

- ，除非工具另有说明。
4. 运行 `execute()`，然后运行 `afterTool` 钩子。5. 提交结果：一条 `pi.tool-result` 条目，任务结束。这就是第 5 部分的效果三明治（p. 70）：意图、效果、结果。在第 3 步之前失败的调用从未碰到外部世界，所以它立刻得到一个错误结果。无论发生了什么，运行都会带着一条结果条目继续：模型看到错误，并决定怎么做。

### 崩溃之后的重放

重启之后，一个被发现处于 `execute` 的工具任务只知道一件事：效果可能已经开始。规则很简单。只有当保存的策略和工具当前的策略都安全时，工具才会再跑一次。否则该任务提交一条 `interrupted` 错误结果，它由工具已经报告过的输出构成，并且不运行工具。那次抓取让两个会话里的两个慢速工具同时运行，在两者都在打印时杀死进程，然后在新进程里恢复。`deploy` 没有设置重放，所以它是不安全的；`fetch_report` 声明 `replay: "safe"`。

<img src="/pi-lessons/_assets/pi-durable/06-runs/fig-6.5.png" alt="A CRASH IN THE MIDDLE OF TWO TOOL CALLS
S E Q U E N C E" loading="lazy">

*调用中途崩溃之后，安全的工具会再跑一次，不安全的则被报告为 `interrupted`。序号取自 `research/capture/crash-before.txt` 和 `crash-after.txt`；时间用的是测试父进程的时钟。在那次抓取里，两个工具的输出提交是交错的。*

会话 1 中的模型随后收到这个结果：

:::note
条目 25，被中断的 deploy `research/capture/crash-after.txt` `JSON`
:::

```json
{
"role": "toolResult", "toolCallId": "deploy-1", "toolName": "deploy", "content": [
{ "type": "text", "text": "deploy site: step 1/10 (pid 98319)\n …" },
{ "type": "text", "text":
"<harness>\n[error] Tool deploy was interrupted and may have partially run\n</harness>" }
```

:::note
],
:::

```
"isError": true, "timestamp": 1791211977057
}
```

:::note
条目 `model` 数组里的那条消息。第一个文本部分包含全部六行已提交的输出；第 2–6 行被省略。该条目还在 `data.diagnostics` 里存有诊断信息，`code` 为 `interrupted`。
:::

任务 22 以 `failed` 结束，运行继续：下一个生成回答「Tool deploy FAILED」。在会话 7 里，安全的工具先清掉它旧的输出，然后在新进程中跑完十个步骤，以条目 28 完成。两个输入都以 `done` 结束。选择策略 `replay: "safe"` 是一个承诺：跑两次效果无害——一次读取、一次幂等写入，或者一次远端会遵守幂等键的写入（效果三明治（p. 70））。其他任何东西都该保持不安全，好让模型得到一句诚实的「可能只跑了一部分」。有三个细节让这条规则比看上去更严：两个策略都要看——一个被改成不安全的工具不会被重跑，一个存为不安全、而其工具后来变安全的调用同样不会被重跑。工具缺失——对该会话不再可用的工具算作不安全。新的环境——重跑会再次从会话当前的工作目录构建它的环境，而工作目录可能已经变了（执行环境（p. 155））。

第 3 步之前的崩溃代价更小。任务仍处于 `call`，所以整个调用从头跑一次，`beforeTool` 也一样。

### 工具轮

工具轮就是一次模型响应里的全部调用。默认并行运行，一个失败的调用绝不会取消其他调用。当 `settings.toolExecution` 为 `"sequential"`，或任何被调用的工具声明了 `executionMode: "sequential"` 时，这一轮一次只跑一个调用。当每个调用都结束时，生成提交一次。一个工具结果可以引导那次提交（定义工具（p. 112））：

`terminate`——不再发起模型调用就结束运行，但只有当这一轮里每个调用都这么要求时。`handoff`——把上下文重置为一段交接文本并结束运行（重置与交接（p. 46））。`addTools`——从下一轮起提供更多工具。否则运行一次 `postTools` 边界，由一个新的生成接管这次运行。如果运行在轮中途被中止，从未开始的调用会得到一个 `aborted` 结果。详解：Harness 写入的错误结果

:::note
`tool_unavailable`：该工具没有被提供，或已不存在 `completed`。`invalid_arguments`：参数不符合 schema，在 `beforeTool` 之前或之后 `completed`。`blocked`：一个 `beforeTool` 钩子阻止或抛出 `completed`。`tool_error`：`execute()` 抛出，或它的环境无法构建 `failed`。`interrupted`：调用中途崩溃且没有安全策略 `failed`。`aborted`：调用被中止 `aborted`。
:::

```
src/harness/tool.ts and generation.ts. Each result has isError: true; the last three keep the output reported so far. A task that ends failed or aborted also
```

:::note
中止这次调用所拥有的任何会话（所有权（p. 76））。
:::

:::note
只有在跑两次无害时，才把工具标记为 `replay: "safe"`。用 `output` 边走边报告进展：调用被中断时，模型看到的就是它。一个在崩溃后也必须做出同样决定的 `beforeTool` 钩子，应当把它的决定存进备忘（备忘（p. 67））。
:::

```
Sources: spec §7.3, §8.4, §8.5, §12; src/harness/tool.ts; src/harness/generation.ts; src/harness/agent.ts; src/harness/types.ts
(ToolRegistration, ToolControl, ToolHooks); README §Tools; test/harness-tools.test.ts; test/harness-tools-recovery.test.ts; research/capture/crash-README.md; research/capture/crash-before.txt; research/capture/crash-reopen-tasks.txt; research/capture/crash-after.txt
```

<a id="sec-6-5"></a>

## 6.5 压缩

> 压缩用一段摘要替换模型所见内容中最老的那部分；什么都没有被删除，而切得最靠前的摘要胜出。

长会话会超出模型的上下文窗口。压缩让模型总结最老的那部分，然后代之以这段摘要发送。完整历史仍留在存储里；只有模型看到的东西变短了。读完本节，你就能设定 token 预算、分辨哪些压缩会让一次运行等待，并预测两个互相竞争的摘要中哪一个胜出。

### 压缩写下什么

一次压缩是一个 `pi.compaction` 任务。它挑出上下文的一个前缀，让模型总结它，并加入一条摘要条目。该条目的头指针是第一条逐字保留的条目，于是模型的上下文现在从摘要开始，从那里继续（头指针（p. 46））。在这次抓取中，`compact()` 在三个问题都回答完之后运行，而第四个答案正在被写入。

:::note
摘要条目 25 `research/capture/extra-p6/compaction.txt` `JSON`
:::

```json
{
"kind": "pi.compaction", "id": 25, "head": 14, "model": [{
"role": "user",
"content": [{ "type": "text", "text": "The conversation history before this point was
compacted into the following summary:\n\n<summary>\n## Goal\nPlan a week in Lisbon.\n</summary>" }], …
```

```
}], "data": { "reason": "manual" },
"byTaskId": 21
}
```

:::note
摘要文本被折成三行；时间戳和 `conversationId` 被省略。会话当时繁忙，所以摘要作为写入提交项 `compaction:22` 在收件箱里等待，而正在运行的生成（任务 21）把它 placed 了。
:::

### 三种启动方式

:::note
你，用 `Conversation.compact()`：手动 否 作为写入提交项。生成，背景预算阈值 否 作为写入提交项。生成，阻塞预算阈值 是 直接追加。生成，上下文过长溢出 是 直接追加。spec §8.7；`src/harness/compaction.ts`。
:::

最后一列是一条安全规则。一个正在运行的 generation 不能眼看着自己的记录在脚下被改动。阻塞式压缩可以直接追加，因为等待它的正是它自己的生成。其他任何摘要都像任何写入一样被提交，在下一个边界落地；如果会话空闲，则立即落地（提交项（p. 84））。非阻塞压缩绝不会让会话变繁忙；它运行时显示在 `pi.live.compactions` 里。

<img src="/pi-lessons/_assets/pi-durable/06-runs/fig-6.6.png" alt="BUDGETS ON ONE TOKEN AXIS
S T R U C T U R E" loading="lazy">

*两个预算决定生成何时压缩；`keepRecentTokens` 决定切口落在哪里。数字取自 ex 25，一个上下文窗口 3000 token 的测试模型。默认值是 `reserveTokens` 16384、`backgroundTokens` 32768 和 `keepRecentTokens` 20000。下面一行是示意的：往回数落在一条工具结果里，于是切口移到下一条消息，留下的不足 400 token。*

### 生成何时压缩

在 `prepare` 里，生成估算它即将发出的请求有多大，并把它与 `settings.compaction` 的两个预算比较。

```
Two budgets decide when generation compacts; keepRecentTokens decides where the cut falls. Numbers from ex 25, a test model with a 3000-token window. The defaults are reserveTokens 16384, backgroundTokens 32768 and keepRecentTokens 20000. The lower row is schematic: counting back lands in a tool result, so the cut moves to the next message and fewer than 400 tokens stay.
```

阻塞——超过 `contextWindow − reserveTokens` 时，生成启动一次压缩并等待它，然后重新准备，无论结果如何都发出请求。背景——超过那条线减去 `backgroundTokens` 时，生成在后台启动一次压缩，不等待就发出请求。`backgroundTokens: 0` 会关掉这一项。切口是从最新条目往回数，直到保住 `keepRecentTokens` 为止。然后它落在下一条用户或助手消息上，绝不落在工具结果上，于是被保留的助手消息保留了它的工具结果。如果整个上下文小于 `keepRecentTokens`，就什么都不压缩。上下文太长有且只有一次补救。当供应商以太长为由拒绝一个请求时，生成压缩一次，并以同一个 attempt 重新准备。一次生成最多压缩一次，所以第二次溢出会让运行以 `model_error` 失败。run 25 展示了这一点：它最后一个轮次在阻塞预算上压缩，随后撞上溢出并失败。

### 当摘要互相竞争

压缩之间从不协调；好几个可以同时运行。唯有收件箱的 stale 头指针规则（p. 84）决定胜者。切口早于上下文当前起点的摘要以 `stale` 落定。切口在其处或之后的摘要则被 placed，无论它是什么时候开始的。

<img src="/pi-lessons/_assets/pi-durable/06-runs/fig-6.7.png" alt="TWO COMPACTIONS, ONE WINNER
C O M P A R I S O N" loading="lazy">

*压缩之间从不协调；切口早于上下文当前起点的摘要就是 stale 的。这里是 spec §6 中的示例。影线标出每个摘要替换掉的内容；虚线是 A 落地之后的上下文起点。*

详解 摘要请求——不带工具，记录里的工具结果被截到 2000 字符，以及你传给 `compact()` 的任何额外指令。只有带文本的干净停止才算一次摘要。可重试的错误按 `settings.retry` 重试。`beforeCompact` 钩子可以拒绝这次压缩，或给出自己的摘要（钩子（p. 109））。中止——`Conversation.abort()`（Esc 键）会中止一次手动压缩。后台压缩会继续下去，除非你传入 `{ background: true }` 或调用 `abortTask()`。阻塞式压缩随它的生成一起停下。压缩期间的编辑——压缩运行时插入的应用内编辑或头指针，可能在摘要落地时丢失或被撤销。spec §12。

:::note
这些默认值适合大窗口。对于小窗口，要让 `keepRecentTokens` 远低于阻塞线，否则上下文可能在任何压缩发生之前就溢出。任何时候都可以调用 `compact()`；它从不阻塞运行。把应用内编辑放在压缩之前，而不是压缩之中。每一次摘要尝试都要付费，即使它最终以 stale 结束。
:::

```
Sources: spec §6, §8.3, §8.7, §12; src/harness/compaction.ts; src/harness/generation.ts; src/harness/live.ts (CompactionStatus);
src/harness/agent.ts (DEFAULT_COMPACTION_POLICY); README §Compaction; docs/pico-v5-handoff.md §20; test/harness-compaction.test.ts; ex 25; run 25; research/capture/extra-p6/compaction.txt
```

<a id="sec-6-6"></a>

## 6.6 用量与成本

> 开销与导致它的那次响应记录在同一次提交里，所以账本和记录永远不会不一致。

到目前为止这次会话花了多少？`pi.usage` 给出答案。账本与每次模型响应在同一次提交里更新，所以即使崩溃之后它也与记录完全吻合。读完本节，你就能读账本、说出它计的是哪些尝试，并在不重复计算任何东西的前提下汇总多个会话的开销。

### 账本

`pi.usage` 是一个内置文档，每个会话一个，包含两个映射。`models` 以 `"provider/model"` 为键。`tools` 以工具名为键，用于那些为自己的模型调用付费的工具。每个值都是一条 `pi-ai` 的 `Usage` 记录，与每条助手消息携带的形状相同。分叉从零开始。

:::note
一次工具调用和一次回答之后的 `pi.usage` `research/capture/extra-p6/live-run.txt` `JSON`
:::

```json
{
"models": {
"faux/faux-1": {
"input": 74, "output": 15, "cacheRead": 54, "cacheWrite": 75, "totalTokens": 218,
"cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0 }
} },
```

```
"tools": {}
}
```

:::note
两次响应之和：调用工具的那一次（118 token）和最终答案。测试供应商报告的成本为零。
:::

token 计数——`input`、`output`、`cacheRead`、`cacheWrite` 和 `totalTokens`，始终存在。可选计数——`cacheWrite1h`（保留一小时有效期的缓存写入）和 `reasoning`（花在思考上的输出），取决于供应商是否报告。`cost`——相同的分桶再加上 `total`，由 `pi-ai` 按该模型定价。账本是一个累计和。逐轮的开销仍然在记录里：每个助手条目都带着自己的用量。

### 什么会被计入

用量记录在追加该响应的那次提交里，绝不在之后。

```
every model response: answers, tool calls, failed attempts models
a partial answer committed before a crash or abort models every summary attempt, even one that fails or ends stale models a tool result that reports usage tools[name] spec §8.6; src/harness/usage.ts, called from generation.ts, tool.ts and compaction.ts.
```

失败和被中止的尝试也计入，因为供应商已经为此收了费。在任何东西提交之前就被切断的尝试没有响应，所以什么都不计入；重发在给出答案时才计入。

<img src="/pi-lessons/_assets/pi-durable/06-runs/fig-6.8.png" alt="WHERE SPEND LANDS
S T R U C T U R E" loading="lazy">

*开销只被记录一次，记在产生它的那次会话里，记在记录该响应的那次提交中。写入方取自 spec §8.6；`models` 总数取自 `research/capture/extra-p6/live-run.txt`。虚线路径是 spec §12 里说的重复计数。*

### 跨会话的合计

每个会话只计算自己的开销。`harness.usage()` 把每个会话的账本加成一个总数；没有任何地方存储这个总数。需要其他总数时——比如一棵子智能体树——自己在 `scanConversations()` 上把账本加起来。

:::note
开销只被记录一次，记在产生它的那次会话里，记在记录该响应的那次提交中。写入方取自 spec §8.6；`models` 总数取自 `research/capture/extra-p6/live-run.txt`。虚线路径是 spec §12 里说的重复计数。
:::

:::note
在自有会话中运行子智能体的工具，不应在结果的 `usage` 里报告那个会话的开销。子会话的 `pi.usage` 已经计了它，所以 `harness.usage()` 会算两次（子智能体（p. 121））。
:::

界面像读任何其他文档一样读这个账本，走会话视图的 `docs["pi.usage"]`（会话视图（p. 129））。

:::note
逐会话的开销从 `pi.usage` 读，总计从 `harness.usage()` 读。只报告工具直接付费的那部分开销。工具名是数据：用 `Object.entries()` 读这些映射，不要用属性访问，以防某个工具名叫 `__proto__`。
:::

```
Sources: spec §8.6, §12; src/harness/usage.ts; src/harness/generation.ts; src/harness/tool.ts; src/harness/compaction.ts; src/harness/harness.ts (usage); README §Usage and Cost; test/harness-inbox.test.ts (describe “usage”); test/harness-
compaction.test.ts; research/capture/extra-p6/live-run.txt
```
