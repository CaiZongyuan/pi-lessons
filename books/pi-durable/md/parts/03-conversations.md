<img src="/pi-lessons/_assets/pi-durable/03-conversations/fig-3.1.png" alt="ANATOMY OF AN ENTRY
A N A T O M Y" loading="lazy">

*一个条目把模型看到的内容、应用看到的内容以及上下文从哪里开始分开存放。research/capture/context.txt 的第 20 条条目，由一次手动压缩写入；摘要文本在三个词之后被截断。*

<a id="sec-3-1"></a>

## 3.1 条目与内置种类

<p class="lede">条目是记录中一行不可变的数据，其中为模型读取的内容、为你的代码读取的内容以及模型上下文的起点分别设了独立字段。</p>
聊天记录就是一份发生过的事情的清单：一个提问、一次回答、一个工具结果。Pi Durable 把每一项都存成条目，之后绝不修改。读完本节，你就能读取任意已存条目、判断它是谁写入的，并添加自己的条目种类。

### 一条记录，三个读者

一个会话就是一份记录，而条目是其中「一条不可变的记录条目」（规范 §1）。每个条目由系统的三个不同部分读取，各自读自己的字段：模型读取 `model`：这条条目为下一次请求添加的消息。你的代码读取 `data`：模型永远看不到的 JSON。上下文构建读取 `head` 和 `edits`：模型的上下文从哪里开始，以及哪些较早的条目要隐藏或替换。已存储的内容不会被改写。

<aside class="note">一个条目把模型看到的内容、应用看到的内容以及上下文从哪里开始分开存放。research/capture/context.txt 的第 20 条条目，由一次手动压缩写入；摘要文本在三个词之后被截断。</aside>
<aside class="note">`id` 一个 `EntryId`，在整个 `Session` 内有序；`conversationId` 该条目所属的会话；`Session` `kind` 指明条目是什么的字符串；`writer` 是否为 `model`？面向模型的消息，用于展示或记账时不存在；`writer` 是否为 `data`？面向视图、扩展和你的代码的 JSON；`writer` 是否为 `head`？模型上下文从此刻起的第一个条目，`writer` 为 `"self"` 表示该条目自身；`edits`？仅在上下文里隐藏或替换较早的条目；`writer` 是否为 `byTaskId`？其提交追加了它的任务；`Session`　以上是 `EntryRecord` 的字段，改写自 src/types.ts 中的字段注释。</aside>
条目在一次提交中写入，也就是一次原子保存：其中的内容要么一起存下，要么都不存。你永远不需要设置 `id`、`conversationId` 或 `byTaskId`。`tx.appendEntry()` 会填好它们，并把 `head: "self"` 换成新的 ID。因此 `byTaskId` 是记录哪个任务写了该条目的可靠依据。你从宿主用 `Conversation.commit()` 追加的条目没有这些字段。

### 内置种类

`Harness` 会写入六种种类。每一种都作为带类型的 Entry token 导出（src/entries.ts）。其中只有两种携带 `data`（规范 §8.1）。

<aside class="note">`pi.user` 一条用户消息 —— 提交项；`pi.assistant` 一条助手消息，任意停止原因 —— 生成；`pi.system` 一条系统消息，作为一次变更 —— 生成，位于请求之前；`pi.tool-result` 一条工具结果消息 `{ diagnostics }` 工具任务；`pi.reset` 无内容，或作为用户消息的交接 —— `reset()`、某个工具的交接；`pi.compaction` 作为用户消息的摘要 `{ reason }` 压缩。来自规范 §8.1 和 src/entries.ts。对应的 token 是 `UserEntry`、`AssistantEntry`、`SystemEntry`、`ToolResultEntry`、`ResetEntry` 和 `CompactionEntry`。</aside>
`pi.assistant` 记录每一次回复，包括失败：「回答、带着错误文本和用量的失败尝试，以及被转换的、停止原因为 `aborted` 的部分回复」（规范 §8.1）。记录不隐藏任何东西，所以花掉的每个 token 都仍然可见。上下文构建随后会把失败的那些排除在后续请求之外（上下文推导（第 40 页））。系统条目是变更，不是头部　一个 `pi.system` 条目并不保存整份提示词。它保存的是在记录的某个位置上对提示词和工具列表的一次变更。下面是某次被捕获运行的第一个：

<aside class="note">条目 10，某会话的第一个 `pi.system`　research/capture/sqlite-rows.txt JSON</aside>
```json
{
"kind": "pi.system",
"model": [{
"role": "system", "content": "",
"sections": { "preamble": "You are a terse assistant." },
"toolsAdded": [{ "name": "count", "description": "Count from 1 to n, …", … }],
"timestamp": 1791211974788 }],
"id": 10, "conversationId": 1, "byTaskId": 9
}
```

<aside class="note">重新排序并合并；该工具的描述和参数 schema 已被截去。</aside>
每个具名 section 会被新增或替换，`null` 则移除某个 section。工具的增删方式相同。按顺序重放所有系统条目，就得到当前的提示词和工具集合（规范 §2）。`Harness` 只在提示词或工具真正发生变化时才写入新的 `pi.system` 条目，所以一个稳定的会话只有一个。完整故事见系统提示词（第 115 页）。

### 你自己的种类

任何非空字符串都是合法的种类。`defineEntry()` 把它变成一个带类型的 token，当你追加和读取时，这个 token 会为 `data` 提供类型：

<aside class="note">一个带类型的应用条目　src/entries.ts · src/types.ts (Tx) TS</aside>
```ts
const NoteEntry = defineEntry<{ text: string }>("app.note");
```

<aside class="note">// 没有 `model`，所以模型永远看不到它。</aside>
```ts
await root.commit(
(tx) => tx.appendEntry(NoteEntry, root.id, { data: { text: "user pinned b.md" } }), context,
);
```

<aside class="note">// 当条目 `id` 不存在或属于其他种类时为 undefined。</aside>
```ts
const note = await harness.commit((tx) => tx.entry(NoteEntry, id), context);
```

<aside class="note">`app.note` 是本书的示例种类。该 token 的 `is()` 守卫按种类收窄任意条目。</aside>
按读者选择字段。模型必须看到的放进 `model`；只有你的代码需要的放进 `data`。只有 `edits` 的条目很常见：捕获到的 `app.correction` 在上下文里替换了一条较早的回答，自身不添加任何消息（research/capture/context.txt，第 5 阶段）。

<aside class="note">面向模型的文本放进 `model`，其余一切放进 `data`。永远不要修改条目，而是追加一条新的并带上 `edits`。调试时用 `byTaskId` 看哪个任务写了某个条目。运行进行中时，用写提交项添加条目，而不是裸 `append`（规范 §12（提交项（第 84 页）））。</aside>
```
Sources: spec §1, §2, §8.1, §12; src/types.ts (EntryRecord, EntryDraft, Tx.appendEntry, Tx.entry); src/entries.ts; src/harness/types.ts (CompactionReason); src/session/transaction.ts; research/capture/context.txt; research/capture/sqlite-rows.txt
```

<a id="sec-3-2"></a>

## 3.2 从记录到模型上下文

<p class="lede">记录保存了发生过的一切；九条固定规则把它变成供应商会接受的请求，而不重写任何已存储的内容。</p>
真实的记录是杂乱的。一条回复被崩溃截断。某个工具调用从未拿到结果。两个结果乱序到达，中间还夹着一条用户消息。原样发出去，供应商会拒绝它。读完本节，你就能在请求钩子改动之前，逐条预测已提交的历史如何变成模型上下文。

### 一份记录的两种读法

已存储的记录只会增长。上下文是模型看到的东西，每次都从那段历史重新计算。`Conversation.context()` 并排展示两种读法（src/harness/types.ts（`ContextView`））：`entries` —— 活跃范围内的原始条目，UI 展示这些。`messages` —— 从已提交历史推导出的消息，位于准备阶段的更新和请求钩子之前。`head` —— 决定范围起点的条目，如果有的话。`contributions` —— 每个条目各自添加了什么，位于工具结果被重排之前。调试时很有用。

### 九条规则

规范把推导过程定义为九条有序规则（规范 §2.1）。右列指向下面的实例。

<aside class="note">1 找到最新的、带 `head` 的条目。　#20　2 上下文从该 `head` 开始，若无则从头开始。　#10　3 从那里读到末尾的每一条条目。　#10–#20</aside>
```
4 Apply edits: the newest edit of an entry wins; omit hides it, replace swaps its messages. #19 replaces #11
5 Put the head entry first, then the others in order. #20 first 6 Keep every system message where it was written. #10 kept 7 Move each call’s results directly after the assistant message that made the call, in call order. #16, #14 after #13 8 Add an error result for every call that has none; drop results with no call. call-c 9 Leave out entries with no model, and assistant messages that stopped as aborted, error or deferred. #12, #18 Paraphrased from spec §2.1.
```

### 一个实例

这份记录是逐条写入、再用 `context()` 读回来的。一个智能体被要求修复两个文件。一条回复被中止。两次读取乱序返回，中间夹着一条用户消息。第三次读取始终没完成。应用随后添加了一条备注，纠正了用户的措辞，并写入一份其 `head` 跳过了开头那段对话的摘要。

<img src="/pi-lessons/_assets/pi-durable/03-conversations/fig-3.2.png" alt="ONE TRANSCRIPT, TWO READINGS
F L O W" loading="lazy">

*上下文推导把一份已存储的记录读成九条请求消息。条目 #8–#20 和推导出的消息取自 research/capture/extra-p23/context-derivation.txt。画阴影线的条目位于 `head` 范围之前；虚线条目在范围内，但不贡献任何消息。画得更深的第 9 条消息没有对应条目：因为 call-c 没有存储结果，推导过程合成了它。*

```
Context derivation reads a stored transcript as nine request messages. Entries #8–#20 and the derived messages are from research/capture/extra-p23/context-derivation.txt. Hatched entries lie before the head’s range; dashed ones are in the range but contribute no message. Message 9, drawn deeper, has no entry: derivation synthesizes it because call-c has no stored result.
```

范围（规则 1–3）。最新的带 `head` 的条目是摘要 #20，而它的 `head` 是 #10。所以上下文覆盖 #10 到 #20。条目 #8 和 #9 仍然存储、仍然可读；只是不会被发送。编辑（规则 4）。#19 替换 #11。消息 3 是纠正后的文本「Fix the typos in a.md and b.md」，而不是原文。只有落在范围内的 `edit` 才算数。

顺序（规则 5 和 6）。摘要 #20 成为消息 1。系统条目 #10 留在原处，作为消息 2。被排除的（规则 9）。被中止的回复 #12 和备注 #18 什么都不添加。#19 也不添加，它只做编辑。工具结果（规则 7 和 8）。#13 先调用 call-a，再调用 call-b。它们的结果 #16 和 #14 向前移动，紧跟在 #13 之后，按调用顺序，并排在用户消息 #15 之前。最后一条助手消息 #17 调用了 call-c 却没有任何回应，于是为它补出一个结果：

<aside class="note">消息 9，为 call-c 合成　research/capture/extra-p23/context-derivation.txt JSON</aside>
```json
{
"role": "toolResult",
"toolCallId": "call-c",
"toolName": "read", "content": [{ "type": "text",
"text": "Tool result unavailable: history ends before this call completed." }],
"isError": true,
"details": { "reason": "missing_result" }, "timestamp": 1791300010000
}
```

<aside class="note">文本和 `details` 固定在 src/harness/context.ts 中。`timestamp` 复制自发出该调用的那条助手消息。</aside>
### 这些规则为何存在

每条规则都处理一种持久记录可能正当处于的状态。崩溃与中止 —— 被中断的回复会存成一条 `aborted` 的 `pi.assistant` 条目（生成（第 91 页））。规则 9 把它的半截文本以及其中的工具调用排除在后续请求之外。被中断的工具 —— 失败或被放弃的工具任务不写入结果。规则 8 告诉模型该调用没有完成（规范 §5.4）。并行工具与引导 —— 结果按完成顺序落地，用户可以在它们之间插入引导（提交项与收件箱（第 84 页））。供应商要求结果紧跟在对应调用之后；规则 7 恢复了这一点。分叉 —— 在调用与其结果之间分出的分叉继承调用，但不继承结果。示例 09 在一条带两次调用的助手消息处分叉；该分叉的上下文以两个错误结果结尾（run 09）。

<aside class="note">要看模型将收到什么，调用 `context()` 并读取 `messages`。不要自己从条目重建。崩溃永远不会产生无效请求，所以记录不需要任何清理代码。读取 context 永不写入。同一份记录读两次得到相同的消息。</aside>
```
Sources: spec §2.1, §2.2 (ContextView), §5.4, §8.1; src/harness/context.ts; src/harness/types.ts (ContextView); ex 09; run 09; research/capture/extra-p23/context-derivation.txt (script test/capture-p23-context.ts)
```

<a id="sec-3-3"></a>

## 3.3 分叉与被拥有的会话

<p class="lede">分叉从某一条目处分支出一个会话，并共享它之前的历史；被拥有的会话属于某个任务，所以中止该任务时会影响到它。</p>
用户想回到较早的一条消息、换个做法，同时保留原来的版本。智能体想为子智能体开一段旁支对话。两者都是新会话。读完本节，你就能创建这两种会话，并预测它们各自看到什么。

### 获得会话的四种方式

<aside class="note">`harness.root(context, options)`　会话 1，首次调用时创建；之后的调用不写入任何东西</aside>
```
harness.createConversation(options, context) a new, empty conversation; ownership is required
conversation.fork(at, options, context) a branch that shares history up to entry at tx.createConversation(), tx.forkConversation() the same, inside any commit, such as a tool’s From spec §2.2 and src/harness/harness.ts. The options are ownership, agent and init.
```

创建是一次提交。它会写入该会话、它的五份内置文档（内置文档（第 60 页））、任何 agent 设置，以及你的 `init(tx, id)` 写入的内容。不会出现创建了一半的状态（规范 §2.2）。创建会话和发送它的第一条消息是两个独立的调用。如果你的进程可能在两者之间崩溃，就在 `init` 里写一个键以便再次找到该会话，然后用带请求 ID 的提交项提交，这样重试不会被发送两次（规范 §2.2）。

### 分叉

分叉是一个新会话，从父会话的某一条目 E 开始。它的记录保存 `parent: { conversationId, at }`。不会复制任何内容。分叉先看到自己的条目，然后是父会话直到 E 的条目，再上是祖父会话直到它自己的 cap，如此类推（规范 §2.1、§3.7）。每一层祖先的条目都在向上路径上最小的那个 cap 处截断。

<aside class="note">$ node --conditions=source --experimental-strip-types test/capture-p23-context.ts</aside>
```
root 1: #9:"three" #8:"two" #7:"one"
fork 10: #16:"fork-only" #8:"two" #7:"one"
grand 17: #23:"grandchild-only" #7:"one"
fork2 24: #16:"fork-only" #8:"two" #7:"one"
grand.fork(#9) -> Entry 9 is not visible from conversation 17 From research/capture/extra-p23/forks.txt; entries newest first. Conversation 17 cannot see #9, so it cannot fork there.
```

`head` 也会跨分叉传递。在压缩之后分出的分叉，其上下文从父会话的摘要开始（research/capture/context.txt，第 6 阶段）。在工具调用与其结果之间分出的分叉，其上下文中会得到一个错误结果（上下文推导（第 40 页））。

<img src="/pi-lessons/_assets/pi-durable/03-conversations/fig-3.3.png" alt="FORKS, CAPS AND AN OWNED CONVERSATION
T R E E" loading="lazy">

*分叉先看到自己的条目，然后是每一层祖先直到 `parent.at` cap 为止的条目。会话 32 没有父会话；住在会话 1 中的任务 31 拥有它。会话、条目与可见性取自 research/capture/extra-p23/forks.txt。*

分叉继承什么

<aside class="note">共享到 E 为止的条目，绝不复制</aside>
```
fork: "asOf" documents a copy of the parent’s value at E
fork: "current" documents a copy of the parent’s value now
fork: "initial" documents nothing; created fresh on first use
pi.agent the parent’s agent settings as of E
```

```
pi.provider a new provider session ID, never the parent’s
```

<aside class="note">live state、inbox、usage 为空；任务和任务文档绝不复制；`Session` 文档共享，不复制　来自规范 §2.2、§3.7。文档分叉策略见定义文档（第 50 页）。</aside>
这次捕获展示了 `asOf` 规则。根会话的 agent 指令在写入 #8 时是 "v1: be brief"，后来变成了 "v2: be thorough"。在 #8 处分出的分叉以 v1 开头，并且拥有自己的供应商 session ID（research/capture/extra-p23/forks.txt）。

### 被拥有的会话

被拥有的会话属于某个任务。用 `{ kind: "task", taskId }` 所有权创建它；记录随后会保存 `owner: { conversationId, taskId }`。任务可以在同一次提交中创建：

<aside class="note">一个任务和它拥有的会话，在一次提交中完成　test/capture-p23-context.ts TS</aside>
```ts
const owned = await harness.commit(async (tx) => {
const taskId = await tx.createTask(Supervisor, null, {
ownership: { kind: "conversation" }, conversationId: root.id, background: true,
}); const child = await tx.createConversation({ ownership: { kind: "task", taskId } });
return { taskId, child };
}, context);
// child: {"id":32,"owner":{"conversationId":1,"taskId":31}}
```

<aside class="note">注释是 research/capture/extra-p23/forks.txt 里捕获到的输出。</aside>
所有权说的是工作，不是历史。被拥有的会话从空开始。它会拿到拥有者会话 agent 设置的一次性副本；之后那里的变更不会传递给它（规范 §2.2）。owner 这条边的作用是把两者为中止和空闲等待连接起来。中止该任务会影响到会话中非后台的工作，而等待任务转为空闲也包含这些工作（所有权与结构化并发（第 76 页））。子智能体正是建立在这之上（子智能体（第 121 页））。拥有者必须存活。正在结束、已经结束或正在被中止的任务无法获得新的会话，即使在同一次提交中也不行（规范 §3.3）。

<aside class="note">「从这里重试」用分叉，原会话不受影响。应当随任务一起停止的工作，用被拥有的会话，例如子智能体。有意为每份文档选定分叉策略；它决定一条分支以什么开始。</aside>
```
Sources: spec §2, §2.1, §2.2, §3.3, §3.7; src/harness/harness.ts (root, createConversation, fork); src/harness/agent.ts (createAgent); src/session/transaction.ts; src/session/forks.ts; ex 03; run 09; research/capture/extra-p23/forks.txt; research/capture/context.txt
```

<a id="sec-3-4"></a>

## 3.4 重置、交接与头指针

<p class="lede">头指针把模型上下文的起点向前移动，而不删除任何东西；重置、交接和压缩都以这种方式工作。</p>
有时候模型应该忘掉一些事。上下文窗口满了，或者用户想在同一个任务上重新开始。Pi Durable 永远不删除旧消息；它只是告诉模型从更靠后的位置开始读。读完本节，你就能开启一段全新的上下文，带或不带交接备注，并预测模型接下来看到什么。

### 头指针是什么

头指针是一个条目字段，表示「模型的上下文从这里开始」（src/types.ts）。带有它的条目就是头指针标记。只有最新的标记有效，上下文推导会把它放在最前（规则 1、2 和 5（第 40 页））。更早的条目仍留在存储里；只是不再被发送（规范 §2.1）。指向头指针有两种方式：回指某个被保留的条目 —— 一份压缩摘要会头指针它保留的第一条条目。上下文变成「摘要，然后是被保留的尾部」（压缩（第 97 页））。

指向自身 —— 重置会头指针它自己。上下文变成只有那一条重置条目，加上它之后的所有内容。

### reset() 与交接

`Conversation.reset(handoff, context)` 开启一段新的上下文。它提交一条 `head: "self"` 的 `pi.reset` 条目。如果你传入交接文本，该条目会把它作为一条用户消息携带（规范 §2.2）。`reset(text)` —— 模型的上下文变成那一条消息。在下图第 4 阶段中："We were doing arithmetic

<aside class="note">for Ada. Continue from 5+5."</aside>
`reset(undefined)` —— 该条目没有消息，所以上下文为空，直到下一次输入（research/capture/extra-p23/heads.txt）。重置和其他写入一样排队。如果会话空闲，它立刻落地；如果有运行正在进行，它会等到下一个边界，也就是模型步与工具步之间的安全点（提交项与收件箱（第 84 页））。在工具轮次中落地会结束该运行，并把它的输入按 reason `reset` 报告为未答复；在一次回答之后落地则不改变那次回答（规范 §6）。`reset()` 在提交项被提交后返回，而不是在条目落地时返回；要看到它落地，请观察该会话。下图跟踪一段被捕获的会话经过五个阶段：三个提问、一次压缩、一轮对话、一次重置，以及最后一轮带纠正的对话。

<img src="/pi-lessons/_assets/pi-durable/03-conversations/fig-3.4.png" alt="THE ACTIVE RANGE MOVING WITH HEADS
T I M E L I N E" loading="lazy">

*头指针把上下文的起点向前移动；每个条目都仍然保留。research/capture/context.txt 的第 1–5 阶段；`context().entries` 各行直接取自它。*

工具也可以要求同样的事。如果其结果的控制信息带有 `handoff: string`，那么工具轮次结束时，运行会结束并留下一条持有该文本的 `pi.reset` 条目，「与 `reset(handoff)` 写入的内容完全一致」（规范 §7.3）。如果多个工具都提出要求，按调用顺序以最后一个为准。

### 过期的头指针写入

头指针只能向前移动。指向当前起点之前的头指针写入会把已被截掉的历史带回来，所以它会以过期为由被拒绝：按 reason `stale` 结算为未答复，并且不写入任何东西（规范 §6）。重置会头指针它自己，所以永不过期。

<aside class="note">在 #9 处重置之后的两次头指针写入　research/capture/extra-p23/heads.txt TEXT</aside>
```
context entries: [#9 pi.reset, #11 pi.user]
write with head=#8 (before the start): status "unanswered", reason "stale"
write with head=#11 (inside the range): status "done", entry 13 context entries now: [#13 app.summary head=11, #11 pi.user]
```

<aside class="note">存储的条目（最新在前），没有删除任何东西：[#15 pi.reset, #13 app.summary, #11 pi.user, #9 pi.reset, #8 pi.assistant, #7 pi.user]　提交项记录已缩短为只保留状态。#15 是之后一次普通的 `reset()`。</aside>
同一条规则也用来在相互竞争的压缩之间做决定：会把起点往回移的摘要会按 `stale` 结算（压缩（第 97 页））。

头指针绝不会做的事　删除 —— 上面每个条目都仍然存储，`entries()` 仍然返回它们，你仍然可以在旧条目处分叉。改变供应商 ID —— 重置和压缩会保留会话的 `pi.provider` session ID（规范 §2.2）。丢失系统提示词 —— 在一个头指针之后，下一个请求会写入一条全新的、完整的 `pi.system` 条目（系统提示词（第 115 页））。

<aside class="note">用 `reset(text)` 开启全新上下文，同时告诉模型它停在哪里。通过写提交项写入自己的头指针条目，而不是裸的 `tx.appendEntry()`。只有提交项路径会检查过期的头指针，裸写入可能让已挂载的视图过期（规范 §12）。如果一次写入以过期结束，说明更新的头指针已经越过了它的目标，请从当前上下文重新计算。</aside>
```
Sources: spec §2.1, §2.2 (reset, pi.provider), §6, §7.3, §7.4, §8.1, §12; src/types.ts (EntryRecord.head); src/harness/harness.ts (reset); src/harness/submissions.ts; src/harness/inbox.ts; src/harness/generation.ts; src/harness/types.ts (ToolControl);
research/capture/context.txt; research/capture/extra-p23/heads.txt
```
