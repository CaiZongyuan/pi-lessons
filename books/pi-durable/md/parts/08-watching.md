<a id="sec-8-1"></a>

## 8.1 Chord 与文档状态

<p class="lede">观察者看到的是一个文档的一连串只读值，每个值都带着产生它的确切编辑，而且绝不会看到存储里没有的东西。</p>
展示文档的面板必须与文档保持同步。当工具更新任务列表时，面板就该跟着变。崩溃之后，它显示的正是已提交的内容。提交是一次原子保存：其中的一切要么一起存储，要么都不存。Pi Durable 只把已提交的变更交给观察者：每一次变更都是一个新的只读值，加上产生它的那份简短编辑清单。读完本节，你就能把一个文档接到界面上，并说清当文档被退役、被迁移或进程死亡时它会显示什么。

### 观察者收到什么

文档构建在 Chord（`@earendil-works/chord`）之上，这是一个用于复制式 JSON 状态的小库。要观察一个文档，你需要它的两个概念（基线与增量（p. 56））：Revision（修订）—— 一个不可变的 JSON 值，每次改变文档的提交都会产生一个新的。Operations（操作）—— 从一个修订到下一个修订的确切编辑，写成小元组；另一处的副本应用它们即可保持同步。观察者只读。Pi Durable 是唯一的写入者，被观察的状态没有任何能修改它的方法 spec §9.1。每个操作都是一个元组：一个单字母名称，然后是通往该值的键与数组下标构成的路径。

<aside class="note">`["r", value]` 替换整个值；`["s", path, value]` 设置一个属性或数组元素；`["d", path]` 删除一个属性或数组元素；`["a", path, text]` 追加到字符串；`["t", path, count]` 从字符串前端移除 count 个 UTF-16 码元；`["p", path, index, remove, items]` 拼接数组</aside>
```json
["m", path, permutation] Reorder an array: new[i] = old[permutation[i]]
```

<aside class="note">摘自 `research/pi/packages/chord/src/delta/README.md`。同一个变更可以用不同的元组写出，一次大编辑也可能以单个 `s` 或 `r` 到达。只有结果值是有保证的。</aside>
### 观察一个文档的两种方式

<aside class="note">`watchDoc()`：一个供你订阅的只读状态。它以当前值开始，并在每次提交之后调用你的监听器。用它驱动界面。帧流：每次提交一帧，包含新值、它的操作以及该提交的 Context；你的回调每次处理一帧。用它按序转发变更（观察契约（p. 129））。</aside>
两者接受的参数与 `snapshot()` 相同，并且有两条规则同时成立。其一是观察从不创建：文档不存在时返回 `undefined`，只有 `tx.doc()` 会创建（访问与创建（p. 53））。其二是观察者只跟随一个化身，也就是它当初附着的那份存储副本；如果该文档被退役后重新创建，观察者不会跟过去。

<img src="/pi-lessons/_assets/pi-durable/08-watching/fig-8.1.png" alt="FROM COMMIT TO CHORD STATE
S E Q U E N C E" loading="lazy">

*文档状态只有在存储持有某次提交之后才会看到它；你的监听器在 `commit()` 兑现之前于一个微任务中运行。第 1 步运行在 Session 的变更线上，因此从取到首个值到完成附着之间不可能有提交插进来；`subscribe()` 随后立刻把该值作为 `hydrate` 0 投递。*

这就是本书的核心规则从读取一侧看到的样子：在存储持有某次提交之前，没有任何东西会到达观察者。你的监听器在该提交在线上的工作之后的一个微任务中运行，在 `commit()` 兑现之前。只有监听器中异步的那部分会离线运行——一个缓慢的同步监听器确实会拖慢下一次提交，所以把长活儿交给一个 promise spec §1。附着会排在更早的提交之后，因此首个值已经包含了它们全部。你绝不会收到尚未见过的修订的操作 spec §9.1。

### `documentState()` 的用法

示例 4 创建一个文本为 "first" 的会话文档，附上一个状态并提交一次变更。

<img src="/pi-lessons/_assets/pi-durable/08-watching/fig-8.2.png" alt="ONE DOCUMENT’S REVISIONS
A N A T O M Y" loading="lazy">

*每次提交都产生一个新的不可变修订，以及产生它的确切操作。一个以 Session 为作用域的 `app.board`，通过*

<aside class="note">文档状态被观察，从首个值到一次更新。`test/examples/04-chord-state.ts` TS</aside>
```ts
const notesState = await session.documentState(Notes, chat.id, context); const stopNotes = notesState.subscribe((value, _deliveryContext, delivery) => {
console.log("Chord notes:", delivery.kind, delivery.sequence, value);
}); await session.commit(async (tx) => {
(await tx.doc(Notes, chat.id)).text = "published through Chord";
}, context);
$ node --conditions=source --experimental-strip-types test/examples/04-chord-state.ts
```

```
Chord notes: hydrate 0 { text: 'first' }
Chord notes: update 1 { text: 'published through Chord' }
```

<aside class="note">`Notes` 的定义、创建它的那次提交、`undefined` 检查以及末尾的 `stopNotes()` 和 `dispose()` 均已省略。`subscribe` 立刻把当前值作为 `hydrate` 投递，然后每次提交一次 `update`。输出来自 run 04。</aside>
`delivery.sequence` 从 0 开始计数这个状态自己的投递次数。它不是提交编号，也没有任何东西存储它 spec §9.1。同一文档上的两个状态彼此独立。释放其中一个只停掉那个观察者，绝不会停掉文档。

### 修订不可变且共享

你收到的每个值都是 Session 永远不会改变的修订。某次提交没碰到的部分是与上一个修订共享的，不是复制的。在下一图背后的捕获中，改标题产生了一个新的根，但 `V2.cards` 与 `V1.cards` 是同一个数组对象。

<aside class="note">每次提交都产生一个新的不可变修订，以及产生它的确切操作。一个以 Session 为作用域的 `app.board`，同时通过 `documentState()` 和 `watchDoc()` 被观察；退役之前还有 101 次提交。值、操作、序列以及共享性检查均来自 `research/capture/extra-p8/doc-observation.txt`。</aside>
共享让发布变得廉价，但没有任何东西被冻结。如果你的代码改动了收到的值，它会悄悄破坏 Session 的副本以及其他每个观察者的副本。需要编辑时先复制 spec §12。要在另一个进程里保留一份副本，就从首个值出发，用 Chord 的 `applyImmutable(value, ops)` 按序应用每一批操作。测试套件会检查这能重建每个投递过的值 `test/session-watches.test.ts`。

### 退役、版本、关闭与崩溃

退役 —— 最后一帧是 `[["r", null]]`。此时状态读到的是 `null`，绝不会读到过期数据。观察流会投递这一帧，并以 `retired` 为 reason 结束；要看到重新创建的文档，请再次附着。新版本 —— 当一次提交以不同的定义版本存储该文档时，观察者收到的是整个新值，形如 `["r", value]`，而不是对它并不具备的形状施加操作 `src/session/session.ts`。Session 关闭 —— 每个状态和观察流都结束，状态保留它最后的值 spec §2.2。崩溃 —— 状态和观察流活在内存里，随进程一同死亡；重新打开之后请再次附着，新状态从已提交的内容开始 spec §9.1。界面在崩溃中不会丢失它显示过的任何东西，因为它显示的始终只是已提交的数据；不过自上次成功提交以来的进度可能消失，而默认的 100 ms 最小间隔并不限制这种丢失（实时文档（p. 88））。

<aside class="note">用 `documentState()` 驱动界面。它只显示已提交的数据，因此崩溃之后无需额外工作就是正确的。绝不要改动你收到的值，先复制。把 `["r", …]` 视为「全部替换」——它会在退役、版本变更和溢出时到达。退役或重新打开之后请再次附着；观察者绝不会迁移到新的化身。要通过 Chord 服务为远程客户端服务，请遵循 `docs/pico-v5-chord-usage.md`。</aside>
```
Sources: spec §1, §2.2, §9.1, §12; src/session/observation.ts; src/session/session.ts (documentState, watchDoc, observedOperations); src/types.ts (DocumentState); docs/pico-v5-chord-usage.md; research/pi/packages/chord/src/delta/README.md; test/session-states.test.ts; test/session-watches.test.ts; ex 04; run 04; research/capture/extra-p8/doc-observation.txt (script test/capture-p8-observe.ts)
```

<a id="sec-8-2"></a>

## 8.2 会话视图与 `watch()`

<p class="lede">一个值同时承载某个会话的记录（transcript）和当前正在运行的东西；它只在提交落地时改变，而你可以把它读作一个状态，</p>
<p class="lede">或者一帧帧的流。</p>
聊天界面需要两样东西：记录，以及此刻正在发生的事，比如模型正在流式输出文本，或某个工具正在打印输出。会话视图把两者放进同一个只读值，只在提交落地时才改变。读完本节，你就能渲染它、让远程副本与之同步，并预测一个缓慢或迟到的客户端会看到什么。

### 视图承载什么

视图就是存储数据的一个普通集合，没有任何计算或过滤。这是捕获中那个会话在运行开始之前的视图。

<aside class="note">`watch.value`（附着时）。`research/capture/watch-ops.txt` JSON</aside>
```json
{
"conversation": { "id": 1 },
"entries": [],
"docs": {
"pi.agent": { "model": { "provider": "faux", "modelId": "faux-1" } },
"pi.live": {},
"pi.inbox": { "items": [] },
"pi.provider": { "sessionId": "01a10c8d-c25d-72c3-83b8-8dc6cf418d86" }, "pi.usage": { "models": {}, "tools": {} }
}
}
```

<aside class="note">每个文档被折叠到一行。`pi.live` 是 `{}`，因为还没有任何东西在运行。</aside>
`conversation` —— 会话记录，若有父级和所有者则带上它们（记录与 ID（p. 25））。`entries` —— 按存储形式给出的活动记录：最新的头指针标记，然后是从其头目标到当前尾部的所有非头指针条目；这些是记录，不是模型的上下文（从记录到模型上下文（p. 40））。`docs` —— 五个内置文档，按 kind 为键（内置文档（p. 60））；文档不存在就表现为该键不存在。这些 kind 及其字段是公开协议。你自己的文档 kind 不在视图里，要用 `documentState()` 观察它们 spec §9.3。

### 视图如何变化

Harness 为每个会话维护一个共享视图。它在首次使用时从存储构建，并在最后一个观察者离开时被丢弃 `src/harness/view.ts`。每次触及该会话的提交都产生一帧：一批把旧视图变成新视图的操作。

<img src="/pi-lessons/_assets/pi-durable/08-watching/fig-8.3.png" alt="FROM A COMMIT TO A VIEW FRAME
F L O W" loading="lazy">

*一个视图帧就是该提交的文档变更，随后是它的新条目，全部改写成通往同一个值的路径。取自 `src/harness/view.ts` 中的 `advance()`。第一行是 `research/capture/watch-ops.txt` 的第 3 帧；第 1 帧展示了顺序：先设置 `pi.live`，再对条目 7 做拼接。*

```
A view frame is the commit’s document changes, then its new entries, rewritten as paths into one value. From advance() in src/harness/view.ts. The first row is frame 3 of research/capture/watch-ops.txt; frame 1 shows the order, a pi.live set before the splice of entry 7.
```

下面是那一帧，它了结了一个工具。五个操作一起落地：该槽位的状态和条目、两处对其进度的删除，以及被拼接进来的结果条目。

<aside class="note">第 14 帧：一次提交了结一个工具。`research/capture/watch-ops.txt` JSON：`[["s", ["docs", "pi.live", "tools", 0, "status"], "done"], ["s", ["docs", "pi.live", "tools", 0, "entry"], 13], ["d", ["docs", "pi.live", "tools", 0, "output"]],`</aside>
```json
["d", ["docs", "pi.live", "tools", 0, "details"]], ["p", ["entries"], 3, 0, [{ "kind": "pi.tool-result", "id": 13, … }]]
```

<aside class="note">]` 条目内容已省略。该槽位在插入条目 13 的同一帧里就指向它，因此渲染器绝不会看到悬空引用。</aside>
按顺序应用一帧的操作，它们不是最小的。帧没有触及的视图部分保持为同一批对象。只追加一个条目的帧会保留同一个 `docs` 对象，因此渲染器可以比较引用来跳过工作 `test/harness-view.test.ts`。

### 消费它的两种方式

<aside class="note">`viewState()`：一个 Chord 状态，和 `documentState()` 一样。当在同一进程中只需要最新值时用它，例如每次更新都重绘的终端界面。`watch()`：帧流。用它在跨进程边界处保留一份副本——先发送一次 `watch.value`，此后按序发送每帧的操作，另一侧用 `applyImmutable()` 应用它们。</aside>
重连时，启动一个新的观察流并再次发送它的值。示例 19 加 `--ops` 打印的正是这样的流：先是视图，然后每次提交一行操作。观察契约——`watch()`、`watchDoc()` 和 `watchTaskGraph()` 都返回一个 `WatchHandle`，遵循同样五条规则。1. 先读 `watch.value`，它保存起始值；在 `start()` 之前提交的帧会在缓冲区里等待。2. 只调用一次 `start(listener)`，它绝不会同步调用监听器；第二次调用 `start()`，或在该观察流已结束之后调用，

- 都会抛错。
3. 同一时刻只有一个回调。每个回调收到 `(value, ops, context)`，下一个要等你的 promise 兑现后才开始。提交绝不

- 等待你。
4. 这个 context 是该提交的 context，但不含其中止信号；你的监听器启动的工作由你自己负责中止。5. `stop()` 可以重复调用，它丢弃待投递的帧，并返回该观察流是如何结束。已经在运行的回调不会

- 被中止。
<img src="/pi-lessons/_assets/pi-durable/08-watching/fig-8.4.png" alt="A SLOW CONSUMER’S BUFFER
S T A T E" loading="lazy">

*一个观察流保留 100 个未投递的帧；下一次提交会用最新值把它们全部替换掉。正在投递的那个帧永远不会被替换。规则出自 spec §9.2 和 `src/session/observation.ts`。一个测试在 `start()` 之前提交 101 个条目，收到的只有一帧 `[["r", view]]`，其中包含全部 101 个条目。*

<aside class="note">`stopped` —— 调用了 `stop()`；`cancelled` —— 附着时传入的 Context 被中止；`session_closed` —— Session 开始关闭；`retired` —— 已退役文档的 null 帧被投递；`listener_error` —— 你的监听器抛错，带有 `error`，且只有该观察流结束 `src/types.ts`（`WatchEnd`）。以最先出现的 reason 为准。在任务或工具内部打开的观察流，也会在那次调用结束时停止（`src/harness/scheduler.ts`）。</aside>
### 缓慢与迟到的消费者

观察流从不让提交等待。如果你的监听器落后超过 100 帧，等待中的帧会被丢弃，换成一帧持有最新值的帧。

<aside class="note">一个观察流保留 100 个未投递的帧；下一次提交会用最新值把它们全部替换掉。正在投递的那个帧永远不会被替换。规则出自 spec §9.2 和 `src/session/observation.ts`。一个测试在 `start()` 之前提交 101 个条目，收到的只有一帧 `[["r", view]]`，其中包含全部 101 个条目。</aside>
替换用的是 `[["r", newest]]`，所以应用操作的代码不需要特殊处理。代价是某些中间状态永远不会被投递：观察流展示的是事情最终停在哪里，而不是每一步。如果你需要每一次转变，就把每一次都记录为条目或写进文档；要获取某一次输入的结果，用 `Submission.wait()`（提交项与收件箱（p. 84））。

迟到加入或重连的客户端从当前视图开始，不会重放任何东西。示例 21 在一个每 100 ms 打印一行的工具执行到一半时附着：

<aside class="note">$ node --conditions=source --experimental-strip-types test/examples/21-late-join.ts</aside>
```
view entries: [ 'pi.user', 'pi.system', 'pi.assistant' ]
view tool slot: running "1\n2\n3\n4\n5\n"
view output now: "1\n2\n3\n4\n5\n"
snapshot tools: [ 'count running' ]
view output now: "1\n2\n3\n4\n5\n6\n"
event output now: "1\n2\n3\n4\n5\n6\n"
```

<aside class="note">摘自 `research/runs/21-late-join.txt` 的开头几行。视图里已经包含了已提交的输出；8.3（p. 133）中的事件流也从同一状态开始。</aside>
迟到的客户端看到五行，是因为每一行都已被提交。工具进度的默认最小提交间隔是 100 ms（`settings.progress`）。崩溃会丢失自上次成功提交以来的进度，而这个间隔可能更长（运行控制与实时文档（p. 88））。

<aside class="note">同一进程、只需要最新值：`viewState()`。远程副本：`watch()` 加 `applyImmutable()`。在流的任何位置都要把 `["r", value]` 当作整体替换。不要把观察流当审计日志用——请用条目、文档或 `Submission.wait()`。重连时再次附着并重发 `watch.value`。</aside>
```
Sources: spec §2.2, §9.2, §9.3, §12; README §Watching a Conversation; src/harness/view.ts; src/session/observation.ts; src/types.ts (WatchHandle, WatchEnd); src/harness/scheduler.ts; test/harness-view.test.ts; test/session-watches.test.ts; ex 19; ex 21; run 21;
research/capture/watch-ops.txt; research/capture/NOTES.md (note 14)
```

<a id="sec-8-3"></a>

## 8.3 智能体事件

<p class="lede">一个实验性适配器把每次提交变成一批编码智能体事件：快照即状态，而每一批都是对状态的一次变更。</p>
你可能已经有读取编码智能体事件的代码，比如 `message_start` 和 `tool_execution_update`：一份 JSON 日志、一个 CLI、一个界面。`watchEvents()` 从 Pi Durable 的提交中产生这些事件。读完本节，你就能消费这条流、从增量重建流式文本，并知道它可能跳过哪些步骤。

### 附着

`watchEvents(harness, conversationId, context)` 从包根导出，并标记为实验性：它的协议可能变化。它返回一条流，带有快照（起始状态）、`start(listener)`、`stop()` 和 `closed`。它遵循 8.2（p. 129）中的观察规则：同一时刻一批，提交绝不等待 `src/harness/events.ts`。快照承载该会话的条目、运行中的工具、压缩、收件箱、agent 和 usage；运行进行中时还承载 run 和 generation、流式消息或一次重试等待 `research/capture/agent-events.txt`。一个事件只在其对应提交使其成立之后才发出 spec §9.4。这条流只覆盖一个会话——子智能体的工作只表现为父级的工具调用，要看到它内部请对子会话再附着一条流（子智能体（p. 121））。

### 一次提交，一批事件

每次提交最多产生一批事件。下表跟随捕获中的一次轮次：模型思考、调用 `count {n: 3}`，然后作答。一次生成就是一次模型调用，以任务的方式运行。

<aside class="note">1 用户消息已提交；运行开始 `message_start`、`message_end`、`submission`、`run_start`、`turn_start`；2 系统提示词条目 `message_start`、`message_end`；3 该生成的第 1 次尝试开始：无；4 第一个流式分片 `message_start`；5–7 思考与文本逐块流入，每个都发 `message_update`；8 助手消息已提交；工具调用入队 `message_end`、`usage_changed`；9 该工具开始运行 `tool_execution_start`；10–13 工具输出与细节，每个都发 `tool_execution_update`；14 工具完成；其结果条目已提交 `tool_execution_end`、`message_start`、`message_end`；15 下一次生成取代上一次 `turn_end`、`turn_start`；16 第 1 次尝试开始：无；17–19 回答流入 `message_start`、`message_update` ×2；20 回答已提交；运行结束 `message_end`、`turn_end`、`run_end`、`submission`、`usage_changed`。`research/capture/watch-ops.txt`（20 帧）与 `agent-events.txt`（18 批），来自 `test/capture/view-ops.ts` 的一次运行。</aside>
第 3 次和第 16 次提交不产生任何批次：开始一次尝试并没有改变任何事件所描述的东西。工具的开始要等到第 9 次提交，也就是调用真正运行时才发出。在第 15 次提交里，一次生成结束、另一次开始，因此 `turn_end` 和 `turn_start` 共处一批。批次内部的顺序是固定的，且与编码智能体一致：先是进展，然后是新条目，然后是结束，开头放在最后——所以一个工具的结束紧挨在它的结果消息之前，而一个已完成的运行会在下一个开始之前结束。

<img src="/pi-lessons/_assets/pi-durable/08-watching/fig-8.5.png" alt="THE ORDER OF ONE BATCH
S T R U C T U R E" loading="lazy">

*一批之内，先是进展，然后是条目，然后是结束，开头放在最后。右图：测试所期望的那一批，来自一次提交——它结束了一个运行，并把排队的后续任务作为下一个运行启动（`test/harness-events.test.ts`）。*

```
```

<aside class="note">一批之内，先是进展，然后是条目，然后是结束，开头放在最后。右图：测试所期望的那一批，来自一次提交——它结束了一个运行，并把排队的后续任务作为下一个运行启动（`test/harness-events.test.ts`）。</aside>
### 每个事件的含义

<aside class="note">`run_start` / `run_end` —— 开始或结束一次运行；加入正在运行之中运行的引导输入不算新运行。`turn_start` / `turn_end` —— 让运行进入新的一次生成 / 提交某次生成的结果。`message_start` / `message_end` —— 提交某次尝试的第一个流式分片，或提交一条本来没有分片的消息条目 / 追加一条带模型消息的条目。`message_update` —— 改动流式分片，携带 usage 和 changes。`entry_appended` —— 追加一条不含模型消息的条目，例如一条普通的 `pi.reset`。`tool_execution_*` —— 开始一次工具调用 / 改动它的输出、细节或诊断信息 / 结束它，或随其运行一起丢弃它。`submission` —— 写入本会话的一条提交项记录。`inbox_update`、`agent_changed`、`usage_changed` —— 改动对应文档。`auto_retry_start` / `_end`、`deferred_poll` —— 开始或结束一次重试等待；调度或移动一个延迟轮询。`task_failed` —— 以 `faulted` 或 `orphaned` 了结会话中的某个任务。`compaction_start` / `_end` —— 开始或完成一次压缩。spec §9.4；`src/harness/events.ts`。</aside>
每个 `message_start` 都会得到一个 `message_end`，即使运行在流式中途被中止。分片只有在有了内容之后才会被提交，而每一条清除分片的内置路径也会追加那条已完成的条目。跨崩溃也是同样的：重新打开时，generation 会把残留的分片变成一条已中止的 `pi.assistant` 条目（生成（p. 91）），流则以此结束那条消息 spec §9.4；`test/harness-events.test.ts`。

### 增量，而非值

`message_update` 只携带流式消息中发生变化的部分。追加的文本以 `text_delta` 或 `thinking_delta` 到达，追加的工具参数以 `toolcall_delta` 到达，新的内容块以 `*_start` 到达。任何其他改动都会重发整个块或整条消息。一个分片的十次提交花费的是十个小事件，而不是十份副本 spec §9.4。

<aside class="note">第 6 次提交的那一批。`research/capture/agent-events.txt` JSON</aside>
```json
{
"type": "message_update",
"usage": { "input": 56, "output": 19, … }, "changes": [
{ "type": "text_start", "contentIndex": 1, "block": { "type": "text", "text": "" } },
{ "type": "thinking_delta", "contentIndex": 0, "delta": "use the tool." }
] }
```

<aside class="note">两个视图操作变成两个 changes，按序排列。usage 字段已省略。</aside>
工具输出的工作方式相同。输出被整体替换时，`tool_execution_update.output` 是 `{ set }`；当旧文本从开头被裁掉、新文本被追加时，则是 `{ trimStart?, append? }`。捕获中第一行显示为 `{"set":"1\n"}`，之后是 `{"append":"2\n"}`。示例 21 用这种方式重建输出：

<aside class="note">应用输出更新。`test/examples/21-late-join.ts` TS</aside>
```ts
let output = stream.snapshot.tools[0]?.output ?? ""; stream.start(async (events) => {
for (const event of events) {
if (event.type === "tool_execution_update" && event.output !== undefined) {
output = "set" in event.output
```

<aside class="note">? event.output.set</aside>
```
: output.slice(event.output.trimStart ?? 0) + (event.output.append ?? "");
} }
});
```

<aside class="note">示例中已省略。被移除的 details 以 `null` 到达，例如可重放工具重启时（6.4（p. 94））。</aside>
### 落后

和观察流一样，这条流最多保留 100 个未投递的批次。溢出时，它们会被最新视图的一份快照替换，其中包含流式分片 `test/harness-events.test.ts`。

<aside class="note">快照可能在任何时刻到达，不只是在最初——把你的状态重置为它。事件用于动画和日志行；持久的那份画面要从视图渲染 spec §9.4。示例 19 用 `--events` 打印一次运行。不要指望看到每个事件，结果请用 `Submission.wait()`。一条流只覆盖一个会话，子会话要分别附着。</aside>
```
Sources: spec §9.4; README §Agent Events (Experimental); src/harness/events.ts; test/harness-events.test.ts; ex 19; ex 21; run 21; research/capture/watch-ops.txt, agent-events.txt
```

<a id="sec-8-4"></a>

## 8.4 任务图与 `inspect()`

<p class="lede">任务图按提交的形态展示每个存活的任务；`inspect()` 补上在你当前这份注册表下调度器会对每个任务做什么。</p>
当一次运行看起来卡住时，原因通常是某个任务在等某件记录里看不到的事。有两个只读工具能让你看到这些任务：`taskGraph()` 是给任务面板用的实时值，`inspect()` 是一次性诊断，还会说明某个任务为何跑不起来。读完本节，你就能从「什么都没发生」走到那个任务和那个原因。

### 一个节点

任务图是一个值 `{ tasks }`，以任务 ID 为键。每个节点是存储的任务记录减去它的载荷：没有 input、检查点数据、结果数据或 memo。

<aside class="note">任务图中一个处于 `waiting` 的任务。`research/capture/extra-p8/inspect-vs-graph.txt` JSON</aside>
```
"8": {
"id": 8,
"kind": "app.join", "conversationId": 1,
"background": false,
"abortRequested": false,
"state": { "status": "waiting", "phase": "done", "on": [7], "policy": "allSettled" }, "conversations": []
}
No owner key: a conversation owns this task. A node owned by another task carries "owner": <TaskId>. abortRequested turns true in the commit that aborts the task.
pending phase Committed and not yet picked up; also every task that was running when the process died, until it runs again running phase Picked up by the scheduler in this process waiting phase, on, policy The stored wait, exactly as committed completing outcome Finished, holding its outcome until its owned work ends src/harness/task-graph.ts; spec §9.5. Statuses are defined in tasks as state machines (p. 63).
```

### 任务图如何变化

一个节点在创建其任务的那次提交中出现，在结束它的那次提交中消失。不改变任何节点的提交（例如写一条 memo）不产生任何帧。任务图展示的是已提交的事实，所以要带着三条规则来读它；紧随其后的图展示了第一条规则在一个真实帧中的样子。`on` 是存储的——它列出等待所命名的每个任务，包括已完成的，`inspect()` 告诉你哪些还活着。`running` 指的是本进程——重新打开 Harness 会把仍然存活的 running 任务变回 `pending`（调度器（p. 73）），它们会显示为 `pending` 直到再次被领走。只列存活任务——一旦某个后台子智能体的任务结束，就没有节点再列出它的会话；要把后续任务放到那里，请用该会话的 owner，会话视图也携带它（子智能体（p. 121））。

<img src="/pi-lessons/_assets/pi-durable/08-watching/fig-8.6.png" alt="TWO FRAMES OF THE TASK GRAPH
T R E E" loading="lazy">

*任务图是实时的所有权树；一个已完成的任务在结束它的那次提交中离开这棵树。`research/capture/task-graph.txt` 中场景 A 的第 6 帧和第 7 帧：一个 order 以 `failFast` 等待三个 pack，第一个完成的 pack 被删除，而该 order 存储的 `on` 仍然列着它。会话方框由 `conversationId` 画出；任务图只持有任务节点。*

```
The task graph is the live ownership tree; a finished task leaves it in the commit that ends it. Frames 6 and 7 of scenario A in research/capture/task-graph.txt: an order waits failFast on three packs, and the first pack to finish is deleted while the order’s stored on still names it. The conversation box is drawn from conversationId; the graph holds task nodes only.
```

`taskGraph()` 返回一个 Chord 状态；`watchTaskGraph()` 返回一个遵循 8.2（p. 129）规则的观察流。两者都不会启动调度，因此查看者可以附着到一个已暂停的 Harness 上而不开始任何工作 spec §9.5。

### `inspect()`：调度器会做什么

`harness.inspect(context)` 不写任何东西，也不运行任何任务代码。它返回调度状态（在第一次 `resume()` 之前是 `paused`、`running` 或 `closing`）、每个存活任务的完整记录与一个推导出的状态，以及排队中和已放置的提交项。

<aside class="note">`running` —— 它的代码正在本进程中运行。`completing` —— 它的结果被持有，直到它所拥有的工作结束。`waiting`、`on` —— 它仍在等待的存活任务。</aside>
```
blocked, reason No installed definition can run it: missing_task, task_too_old, or migration_failed (with error)
ready, migrates The next scheduling pass picks it up; migrates when a newer definition will migrate it first src/harness/scheduler.ts. migration_failed appears only after the scheduler tried; inspection never runs a migration.
```

<img src="/pi-lessons/_assets/pi-durable/08-watching/fig-8.7.png" alt="ONE SET OF TASKS, TWO READINGS
C O M P A R I S O N" loading="lazy">

*任务图展示已提交的内容；`inspect()` 补上在这份注册表下调度器会做什么。一次提交创建四个任务，在闸门运行期间读取。`app.legacy` 由版本 2 的定义存储，而只安装了版本 1；`app.retired` 未安装。摘自 `research/capture/extra-p8/inspect-vs-graph.txt`。*

任务图无法显示 `blocked`，因为没有任何东西存储它。被阻塞任务的记录就是普通的 `pending` 或 `waiting` 记录，它永远不会自行结束。安装一个能运行它的定义，或者中止它：在捕获中，`abortTask()` 一次性把两个被阻塞的任务以 `orphaned` 了结，并以被阻塞的原因作为结果的 reason。

### 从「什么都没发生」到一个原因

1. `scheduling` 处于 `paused`：还没有人调用 `resume()`，也没有调用会启动它的东西，比如 `submit()` 或 `waitForIdle()`。只

- 读型查看者永远不会启动它。
2. 某个任务被阻塞：注册表缺少它的 kind，或持有的是一个较旧的版本。修好安装，或者中止该任务，让它以

- `orphaned` 了结（调度器（p. 73））。
3. 某个任务正在等待：顺着它的 `on` 走到那些存活任务，重复上面的检查。一个已中止的任务会先等待它所拥有的工作（中止、故障与

- 孤儿（p. 80））。
4. 某个任务正在收尾：它自己的工作做完了，它所拥有的工作还没有；在任务图中找到那些被拥有的节点（所有权与

- 结构化并发（p. 76））。
5. 某个任务正在运行：它的代码处于活动状态。对生成和工具来说，会话视图中的 `pi.live` 显示这次尝试、重试

- 等待或工具输出（实时文档（p. 88））。
排队的提交项要等它前面的运行；已放置的提交项属于某个尚未作答的运行（6.1（p. 84））。已完成的任务不在 `inspect()` 里，用 `getTask()` 读取它们。

```
Sources: spec §2.2 (inspect()), §5.4, §9.5; README §Task Graph; src/harness/task-graph.ts; src/harness/harness.ts (inspect, taskGraph,
watchTaskGraph); src/harness/types.ts (TaskInspection, HarnessInspection); src/harness/scheduler.ts; test/harness-task-graph.test.ts; test/harness-inspect.test.ts; research/capture/task-graph.txt; research/capture/NOTES.md (note 9); research/capture/extra-p8/inspect- vs-graph.txt (script test/capture-p8-observe.ts)
```
