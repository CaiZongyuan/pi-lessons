<img src="/pi-lessons/_assets/pi-durable/02-sessions/fig-2.1.png" alt="THE RECORD FAMILY
S T R U C T U R E" loading="lazy">

*五种记录类型共用一个 ID 空间，对它们的引用都是带类型的 ID。字段名取自 `src/types.ts`；卡片标题上的数字是深入讲解对应类型的小节。*

<a id="sec-2-1"></a>

## 2.1 记录与 ID

<p class="lede">五种记录类型、一个编号空间，装着 Session 存储的全部内容；记录之间的两条边看着一样，含义却不同。</p>
打开一个 Pi Durable 数据库，里面只有五类记录，全部从同一个共享计数器取号。掌握这五种形状，以及一个会话指向另一个会话的两种方式，你就能读懂任何存储转储。

### 四张表与文档

一个 Session 存四类表记录，外加文档：「表就是会话、条目、任务和提交项」spec §4。文档是你应用的 `JSON` 状态，本身另有一条小记录（documents（第 53 页））。每条记录都是一个普通的 `JSON` 对象，在 `src/types.ts` 中声明为 `TypeScript` 类型。图中给出全部五种类型，以及每个字段的用途。

```
Five record types share one ID space, and their references are typed IDs. Field names are from src/types.ts; the numbers in the card heads are the sections that cover each type in depth.
```

这些记录的变化方式各不相同：

- 会话和条目在创建它们的那次提交之后不再改变（不变式 5，invariants（第 16 页））。
- 任务和提交项整体替换。每次变化都在同一个 ID 下写入一条完整的新记录 `src/types.ts`
- （`TaskRecord`）。
- 一条文档记录描述一个文档从创建到退役的全过程。它的内容单独存放，以完整副本和
- `Chord` 操作两种形式存在（基线与增量（第 56 页））。
`ConversationRecord` —— 只有 `id`、可选的 parent 和可选的 owner。会话的模型、设置与应用状态不在这条记录里，它们存放在 `pi.agent` 这类文档中（内置文档（第 60 页））。`EntryRecord` —— 一条不可变的记录（transcript）事件。它为模型（`model`）、应用（`data`）和上下文控制（`head`、`edits`）分设字段；见 entries（第 37 页）。`TaskRecord` —— 身份（`kind`、`version`、`input`）、归属（`owner`、`background`）、持久的 abort 标记，以及一个状态联合类型；见任务状态机（第 63 页）。`SubmissionRecord` —— `type`（`input` 或 `write`）与 `status` 的联合。一个 input 依次经过 `queued`、`placed`、`done` 和 `unanswered`。write 没有 `placed` 状态，而且只有 input 才有 answer；见 submissions（第 84 页）。`DocumentRecord` —— `kind`、可选的 family key、`scope`，对会话文档还有 history 与 fork 策略。`createdAt` 和 `retiredAt` 是由存储盖上的提交序号。

### ID 是带类型标签的普通数字

每个记录 ID 都是一个普通的 `JavaScript` 数字。`TypeScript` 给它加一个标签，称为 brand，这样你就不能把 `EntryId` 传到需要 `TaskId` 的地方。brand 只存在于编译期：

<aside class="note">ID、`Seq` 与根会话　`src/types.ts`　TS</aside>
```ts
export type ConversationId = Id<"conversation">;
export type EntryId = Id<"entry">;
export type TaskId<Result = unknown> = Id<"task", Result>; export type SubmissionId = Id<"submission">;
export type DocumentId = Id<"document">;
/** Strictly increasing sequence assigned to one atomic storage commit; gaps are permitted. */
```

```ts
export type Seq = number & { readonly [seqBrand]: "sequence" };
/** The root conversation always uses this reserved ID. */ export const ROOT_CONVERSATION_ID = 1 as ConversationId;
```

<aside class="note">泛型 uid=197609(zongy) gid=197609 groups=197609 类型与两个 brand 符号的声明被截去了。 还携带其所属任务的结果类型， 正是靠这一点返回带类型的结果。</aside>
「ID 和序号在内存、`JSON`、`JSONL` 和 `SQLite` 中始终是普通数字」spec §2。这个包不导出一个给数字打 brand 的辅助函数。当你的代码从 `JSON`、URL 或 UI 消息中收到 ID 时，自己用 `as EntryId` 转换，并在那一处做检查。

### 所有记录共用一个计数器

会话、条目、任务、提交项和文档的 ID 全部取自同一个 Session 范围的计数器 `Storage.mintId()` `src/types.ts`。因此无论类型如何，不会有两条记录共用同一个数字。抓取到的 `SQLite` 运行把这一点摊开来看：各类型按提交需要它们的先后顺序交错出现。

<img src="/pi-lessons/_assets/pi-durable/02-sessions/fig-2.2.png" alt="ONE ANSWERED INPUT, BY ID AND BY SEQ
S T R U C T U R E" loading="lazy">

*除根记录之外，每条记录的 ID 都取自同一个计数器；提交则单独编号。ID 1 保留给根会话，所以提交 1 只铸出五个文档 ID 2–6。每一行把一组 ID 连到铸出它的那次提交；17 次提交中有十次一个 ID 也没铸。虚线格子是*

一个计数器带来三个事实。ID 可以跨会话给条目排序 —— 「条目 ID 在 Session 内全局有序」spec §2.1。分叉的上限和上下文区间都是对条目 ID 的比较，即使这些条目属于不同会话（forks（第 43 页））。根是保留的，不是铸出来的 —— `ROOT_CONVERSATION_ID` 为 1，`MemoryStorage` 从 2 开始铸号 `src/storage/memory.ts`。因此一个创建首个会话的普通 `Session` 拿到的是 ID 2（run 00）。`Harness` 通过 `root()` 惰性地创建会话 1。被回滚的提交会烧掉它的 ID —— 铸号发生在回调内部，在批次到达存储之前。那些创建记录的事务方法是异步的，「因为远程存储可能持久地分配全局唯一的数字 ID」spec §3.3。在抓取到的失败运行中，三个被回滚的提交拿走了 ID 3、4、5，而下一个提交成功的条目是 6（`research/capture/extra-p23/commit-failures.txt`）。唯一的保证是 ID「在一次已提交的写入之后绝不复用」（不变式 5）。

`Seq` 是第二个计数器。它编号的是提交而不是记录：存储给每个已提交的批次一个，它「在提交之间严格递增；允许有间隔」spec §2。两个计数器的速度不同。在这次抓取中，17 次提交铸出了 14 个 ID（2–15），其中十次提交一个 ID 也没铸，它们只改了任务状态或 `pi.live`。你会在文档的 `createdAt` 和 `retiredAt` 上遇到 `Seq`，在每次提交发布时遇到它，在每条已存条目上也会遇到它 —— 那里它让文档可以被读成截至该条目的样子（可回溯的历史（第 56 页））。

### 两条边：parent 与 owner

`ConversationRecord` 有两条形状相同的可选边。它们都指向一个会话，含义却不同。「会话历史的父子关系与任务归属是分开的」spec §2：

<aside class="note">PARENT　OWNER</aside>
```
Shape { conversationId, at: EntryId } { conversationId, taskId: TaskId }
Set by a fork at entry at creation with { kind: "task", taskId } ownership
```

<aside class="note">决定被继承的条目和历史文档　归属、子树中止、空闲遍历　调用方只提供父会话和 entry，只提供任务 ID，由 `Session` 推导会话　任务结束之后仍然保留记录　引自 spec §2 和 `src/types.ts` 中的字段注释。</aside>
owner 边「不是访问控制能力」spec §2；它记录是谁创建了这个会话。创建时总会说明归属，要么是 `{ kind: "ownerless" }`，要么是 `{ kind: "task", taskId }`，而会话由 `Session` 自己补上任务所属的会话。分叉可以同时带两条边：它从一个会话继承历史，同时由另一个会话里的任务拥有。记录还有三条用同样 ID 的边。任务的 owner 是一个 `TaskId`，用它构建任务树（归属与结构化并发（第 76 页））。条目的 `byTaskId` 指明是哪个任务的提交追加了它。提交项的 entry 和 answer 指明它所放置的用户条目，以及作出回答的助手条目。抓取到的提交项 8 最终是 `{ status: "done", entry: 7, answer: 15 }` `research/capture/sqlite-rows.txt`。

<aside class="note">ID 在所有记录类型之间都是唯一的，但数字本身不说明它是哪种类型。把类型一起带上，让 brand 去抓混用。要预期有间隔。一次失败的提交会烧掉它铸出的 ID，这是正常的。用 `parent` 问「这段历史从哪里来」，用 `owner` 问「是哪个任务做的」。</aside>
```
Sources: spec §1 (invariant 5), §2, §2.1, §3.3, §4; src/types.ts (Id, Seq, ROOT_CONVERSATION_ID, ConversationRecord, EntryRecord, TaskRecord, SubmissionRecord, DocumentRecord, Storage.mintId, Storage.entry); src/index.ts; src/session/transaction.ts (conversation
creation); src/storage/memory.ts (nextId); run 00; research/capture/sqlite-rows.txt; research/capture/sqlite-commits.txt; research/capture/extra-p23/commit-failures.txt
```

<a id="sec-2-2"></a>

## 2.2 提交与变更线

<p class="lede">每次写入都经过一个串行化的回调；它的写入要么一起存储，要么全不存储，而在存储点头之前观察者看不到任何东西。</p>
对 `Session` 的每一次改动都要走 `commit()`。提交是一次原子保存：里面的一切要么一起存储，要么什么都不存。提交一次只跑一个，排在一个叫变更线的队列里。本节说明你能在提交里做什么，以及程序的其余部分什么时候能看到这个改动。

### 唯一的写入路径

`session.commit(change, context)` 是唯一的写入路径。你的回调会拿到一个事务 `tx`。它写的一切在回调返回时作为一批存储，如果回调抛出就全部丢弃 ex 00。「一次 `Session` 提交在所有记录和文档写入之间是原子的」（不变式 1，spec §1）。`Conversation.commit()` 把它绑定到一个会话；任务的 `runtime.commit()` 还会在它追加的每个条目上盖上该任务的 ID。

<aside class="note">一次读取、追加条目、编辑文档并创建任务的提交　docs/spec.md §4　TS</aside>
```ts
await session.commit(async tx => {
const conversation = await tx.conversation(conversationId); // table read const live = await tx.doc(LiveDoc, conversationId);
await tx.appendEntry(conversationId, message); // first table write
delete live.generation; // document mutation remains valid await tx.createTask(Follow, {}, {
ownership: { kind: "conversation" }, conversationId,
}); // further table writes are fine }, context);
```

<aside class="note">读取在前，因为必须在前；文档草稿在第一次写入之后仍然可用。</aside>
### 变更线

变更线是一个一次只跑一个提交的队列。从提交回调开始，到存储存下批次并通知观察者为止，提交一直占着这条线：「贯穿回调执行、准备、存储落定、已提交基线接管和发布入队」spec §4。在这期间没有别的提交会开始。下图跟踪一次提交穿过这些阶段。步骤 1–5：在你的回调内部 —— 如果 `Session` 正在关闭或已被污染，`commit()` 会立刻拒绝。否则回调带着一个全新的事务运行，它的操作分成三组（下表）。

要记住的规则是先读后写。「第一次表写入之后的任何表读取都会抛出 `ReadAfterWrite`」spec §4，消息形如 `Tx.conversation() cannot read tables after the first table write`。表读取直接打到存储，而存储此时还没看到本次事务的写入，所以写后读可能与写入相矛盾。你从不需要这样做：创建方法会返回它们创建出来的记录。

<img src="/pi-lessons/_assets/pi-durable/02-sessions/fig-2.3.png" alt="ONE COMMIT ON THE LINE
S E Q U E N C E" loading="lazy">

*这条线从准入一直被占用到发布入队；回调在其后运行。那条水绿色的横条就是被占用的线。依据 `src/session/session.ts` 与 `src/session/transaction.ts`。*

<aside class="note">conversation、entry、task、`scanConversations`、`scanEntries`、`latestHeadMarker`、`scanTasks`、`submissionByRequest`　只在第一次表写入之前的表读取　`createConversation`、`forkConversation`、`appendEntry`、`createTask`、`createSubmission`、`settleSubmission`、`placeSubmission`　表写入，返回创建出的记录或 ID　Docs　`doc`（取或建）、`retireDoc`　在表写入之前和之后都可用</aside>
```
The Tx interface in src/types.ts; the rules are spec §4.
```

<aside class="note">这条线从准入一直被占用到发布入队；回调在其后运行。那条水绿色的横条就是被占用的线。依据 `src/session/session.ts` 与 `src/session/transaction.ts`。</aside>
文档的做法不同。`tx.doc()` 返回一个草稿，一份可以像普通对象那样编辑的可变副本，而且它能看到你自己的改动。你赋的值「按值复制，且必须是严格 `JSON`」；`undefined` 或 `Date` 会在任何东西被存储之前让提交失败 spec §1（不变式 6）；`test/session-documents.test.ts`。回调落定时，每个草稿都被撤销。留在回调之外的草稿下一次使用时就会抛出，而调用得太晚的 `tx` 方法会以 `Transaction has settled` 拒绝。步骤 5 与 6 之间：检查批次 —— 你的回调返回时，`Session` 把它的工作变成一批并检查它。漏掉的 `await` 最先被抓住：仍在等待的 `tx` 调用会让提交失败，报 `Session commit callback settled before its pending Tx operations`。接着草稿变成最终值，批次被校验，例如每个 owner 任务都存在且仍然存活。这里任何失败都会回滚整次提交（提交失败时（第 33 页））。没有写入的批次根本不会到达存储：什么都不存，也什么都不发布。步骤 6–8：先存储，然后才是其他人 —— `Storage.commit(writes)` 原子地存储这一批并返回它的 `Seq`。提交一旦开始，取消你的上下文就不再能停下它：「调用方的取消不会中断存储落定，也不会撤销提交」spec §4。存储成功后，`Session` 换上新的文档值，并构造一份发布 `{ seq, changes }`。它把这份发布交给每个 `subscribeCommits()` 监听者，此时仍在变更线上。下面是其中一条，来自模型请求工具的那个轮次：

<aside class="note">提交 seq 6，提交观察者看到的样子　`research/capture/sqlite-commits.txt`　TEXT　commit seq=6 entry 11 kind=pi.assistant byTask=9 task 9 pi.generation status=waiting phase=tools on=[12] policy=allSettled task 12 pi.tool status=pending phase=call document pi.live (2) 2 op(s) document pi.usage (4) 1 op(s)</aside>
```
```

<aside class="note">每处改动一行，由抓取脚本汇总。助手条目、上级的等待、新的工具任务和两处文档改动一起变得可见，或者一起不可见。</aside>
提交观察者运行在变更线上，「只用于捕获不可变状态」（不变式 7）。它们「不得抛出、不得阻塞、不得调用 `Session` API」spec §4。你的 watch 和文档状态回调稍后在线外运行（`Chord` 与文档状态（第 125 页）），所以再慢的界面也不会拖住下一次提交。

### 绝不要在提交里 await 一个副作用

「外部的模型、进程、工具、网络和人为副作用都在它之外运行」spec §4。破坏这条规则要付双倍代价。变更线会停住 —— 当一个回调在等一次网络调用时，其他每个提交都排在它后面：工具进度、其他会话、调度器。记录会说谎 —— 如果进程在副作用之后、批次被存储之前死掉，副作用已经发生，却没有任何东西记录它。如果回调在副作用之后抛出，批次会回滚，而副作用仍然没有被记录。修法是：提交意图，在任何提交之外执行副作用，然后提交结果：副作用三明治（第 70 页）。每个内置工具和生成任务都是这么工作的。

<aside class="note">在回调内部启动、然后就丢着不管的工作，仍然可能改动那个尚未落定的事务，并在落定时失败。规范把这称为不支持 spec §12。每一个 `tx` 调用都要 await，后台工作只在 `commit()` 兑现之后启动。</aside>
<aside class="note">先做完所有表读取，再做写入。文档在任何时点都可以读取和修改。每一个 `tx` 调用都要 await，回调要短，并且不碰 I/O。草稿里只放 `JSON`，回调之后绝不保留草稿。对改动的反应放在 watch 里，不要放在提交观察者里。</aside>
细节 —— 尽管只有一条变更线，读取依然便宜。提交过的值被缓存的文档无需排队就能读到 `src/session/session.ts`（snapshot）。存储只把这一批借用到 `Storage.commit()` 落定为止，而且「每次存储读取都返回一个独立的 `JSON` 值」spec §4，所以你手里的东西不会与已存储的状态共享引用。批次检查会校验分叉来源、owner 和任务替换，退役那些在本次提交中结束的任务的文档，最后运行每个文档的 `checkpointWhen` 谓词来决定用完整副本还是用增量（基线与增量（第 56 页））`src/session/transaction.ts`。

```
Sources: spec §1 (invariants 1, 4, 6, 7), §2.2, §3.3, §4, §12; src/session/session.ts (commit, publication, snapshot);
src/session/transaction.ts (Tx operations, settlement, batch assembly, adoption); src/errors.ts (ReadAfterWrite); src/types.ts (Tx, StorageWrite, CommitPublication, Storage.commit); ex 00; research/capture/sqlite-commits.txt; research/capture/extra-p23/commit- failures.txt
```

<img src="/pi-lessons/_assets/pi-durable/02-sessions/fig-2.4.png" alt="FAILURE OUTCOMES BY PHASE
D E C I S I O N" loading="lazy">

*存储准入之前的失败会回滚；不确定的存储结果，或者存储已提交之后的接管失败，会让 `Session` 中毒。最下面一行是各种情况下接下来该做什么。分支依据 `src/session/session.ts` 与 `src/session/transaction.ts`。*

<a id="sec-2-3"></a>

## 2.3 提交失败时

<p class="lede">失败发生在哪里决定了结果：在存储之前它只是一次普通的回滚，在存储之内它要么是确定被拒绝，要么是致命的</p>
<p class="lede">不确定性。</p>
大多数失败的提交都无害：什么都没存，你继续往下走。有一种不是。如果存储以一种可能已经存下这一批的方式失败，`Session` 会停止接受工作，直到你关掉它并重新打开存储。本节说明如何区分这些情况，以及每种情况下该做什么。

### 三种结果

一次提交可能在五个位置失败，而每次失败都以三种结果之一收尾：回滚、被存储拒绝、中毒。不变式 8 划出了这个分界：「不确定的存储失败对已打开的 `Session` 是致命的。它不发布任何东西，必须重新打开。准备和检查点失败发生在存储准入之前，正常回滚」spec §1。

<aside class="note">存储准入之前的失败会回滚；不确定的存储结果，或者存储已提交之后的接管失败，会让 `Session` 中毒。最下面一行是各种情况下接下来该做什么。分支依据 `src/session/session.ts` 与 `src/session/transaction.ts`。</aside>
抓取到的失败运行展示了这三种结果：它用一个普通 `Session` 跑在 `MemoryStorage` 上，而这个存储的下一次提交可以被做成失败。

<aside class="note">$ node --conditions=source --experimental-strip-types test/capture-p23-context.ts</aside>
```
read after write -> ReadAfterWrite: Tx.conversation() cannot read tables after the first table write
callback throws -> Error: validation failed empty commit -> ok "nothing written" storage rejects -> StorageRejected: rejected before any durable effect
```

```
next commit -> ok {"kind":"app.note","data":"after rejection","id":6,"conversationId":2}
uncertain storage failure -> Error: disk vanished
```

```
next commit -> Error: Session is poisoned by a failed commit after storage admission;
reopen it (cause: Error: disk vanished)
snapshot -> Error: Session is poisoned by a failed commit after storage admission; …
close -> ok undefined From research/capture/extra-p23/commit-failures.txt; the long poisoned line is wrapped and the second one cut. The rejection and the two failures before it burnt IDs 3–5.
```

### 存储之前：一次普通的回滚

五个位置里有三个在存储之前：回调本身、settle（还有 `tx` 调用在等待）和 prepare（批次检查）。其中任何一处失败都会丢掉全部改动，并重新抛出原始错误 `src/session/transaction.ts`。这涵盖你自己的异常、`ReadAfterWrite`、草稿里的非 `JSON` 值，以及指向不存在的会话或任务的引用（`Conversation N does not exist`）。回滚是完整的：什么都没存，什么都没发布，每个文档都保留之前的值。一个测试让改变了两个文档的提交失败；两者读出来仍然和之前一样，下一次提交正常工作 `test/session-documents.test.ts`。唯一的痕迹是 ID 序列中的间隔（记录与 ID（第 25 页））。在任务内部，被回滚的提交通常会终结任务。如果某个阶段处理器让错误逃出去，任务就以 faulted 结束（阶段、步骤与进度（第 67 页））。在一个抓取到的场景里，任务想在完成自己的同一次提交中创建归它所有的活儿；批次检查以 `Task owner 12 is completing` 拒绝了它，任务以 faulted 结束，那次提交的内容什么都没存下 `research/capture/NOTES.md`（注 6）。

### 存储之内：被拒绝或不确定

这一批一旦交给 `Storage.commit()`，`Session` 就再也不能假定任何事。存储契约定义了唯一那个安全的异常：「`StorageRejected` 表示这一批在任何持久副作用之前就被拒绝，保证没有提交。`Session` 会正常回滚这样一批；存储准入之后的未知失败依然是致命的，因为它们的提交状态不确定」spec §10。后端把它用于那些能证明没有产生任何副作用的失败。例如 `SQLite` 会把失败的 fork 副本报告为 `Document copy N was rejected` `src/storage/sqlite/storage.ts`。其他任何存储错误都会让 `Session` 中毒：它把自己标记为不可用。存储刚成功之后、`Session` 换上新值的时候失败也是如此，因为那时存储持有一个内存并未反映的提交 `src/session/session.ts`。中毒的 `Session` 会拒绝一切需要它状态的东西。之后每次提交、`snapshot()`、`state`、watch 和线读取都抛出 `Session is poisoned by a failed commit after storage admission; reopen it`，并把原始错误作为 cause `src/session/session.ts`。失败的那一批什么都不会发布，所以没有观察者看到一个可能并不存在的值 `test/session-documents.test.ts`。`Session` 不重试，因为两种猜测都不安全：如果那一批确实提交了，内存就落后于存储；如果没有提交，在内存里应用它就会发布一个并不存在的改动。只有存储知道，而新的 `Session` 读到的正是它自己持有的东西。「不要捕获这个错误并继续使用它」spec §12。`JSONL` 存储在一次不确定的追加之后也会让自己中毒（`JSONL`（第 148 页））。

<aside class="note">ReadAfterWrite　表写入之后的表读取　可用　…settled before its pending Tx operations　回调提前返回　可用　Transaction has settled　在落定之后使用 Tx 或草稿　可用　StorageRejected　存储，在任何持久副作用之前　可用　任何其他存储错误　存储，结果未知　中毒　adoption error after storage committed　中毒　Session is closed　`close()` 开始之后的任何调用　正在关闭　消息取自 `src/errors.ts`、`src/session/session.ts` 和 `src/session/transaction.ts`。`ConversationBusy` 是导出的第三个错误类，它是一个准入结果，不是提交失败（submissions（第 84 页））。</aside>
### 先关闭，再重开

恢复从 `close()` 开始，即使 `Session` 已经中毒它也能工作。它按固定顺序执行 spec §2.2：Seal —— 准入立刻关闭。新的提交和读取以 `Session is closed` 拒绝，`Harness` 也会拒绝新的会话和提交项操作。

Notify —— `subscribeClose()` 监听者同步运行。`Harness` 在这里停掉 watch 并向任务调用发信号，而每个文档状态和 watch 都保留最后的值。Join —— `Harness` 等待任务、工具和钩子调用返回，「包括那些无视自己信号的代码」（调度器（第 73 页））。Settle —— 在封存之前准入的提交在变更线上跑完。然后变更线清空它的监听者和缓存，并关闭存储。「关闭不写入任务结果」spec §2.2。运行中的任务在存储里仍然是运行中的，就像进程已经死掉一样。`close()` 兑现之后，「新的 `Harness` 可以打开同一个 `Storage`」。重开就是在同一个存储上做普通的 `Harness.open()`。它找到已提交的内容，别的一概没有，并把仍然活着的 running 任务变回 pending（调度器（第 73 页））。要拿新的句柄；旧的已经死了。一个在意图被提交之后才重开的任务，可能已经执行了它的副作用，这正是副作用三明治（第 70 页）要处理的情况。

<aside class="note">`Storage.commit()` 内部的崩溃就是那种不确定的情况，只不过没有进程留下来去中毒。`SQLite` 把每次提交放在一个 SQL 事务里，`JSONL` 则只在它的 sidecar 之后才发布提交标记。无论哪种情况，重开都会发现这一批要么完整存在，要么完全不存在（`SQLite`（第 144 页）、`JSONL`（第 148 页））。</aside>
<aside class="note">把一次抛出的提交当作「什么都没发生」，除非 `Session` 现在已经中毒。绝不要捕获中毒错误然后继续用。关掉 `Harness`，重新打开存储。如果你要写一个存储后端，只有在能证明什么都没存下时才抛 `StorageRejected`。</aside>
```
Sources: spec §1 (invariant 8), §2.2 (close and reopen), §4, §10, §12; src/session/session.ts (commit, poison checks, close);
src/session/transaction.ts (failure and success settlement, batch assembly); src/errors.ts; src/storage/sqlite/storage.ts (document copy rejection); test/session-documents.test.ts (rollback and poison tests); test/session-forks.test.ts (StorageRejected rollback);
research/capture/extra-p23/commit-failures.txt; research/capture/NOTES.md (notes 1 and 6)
```
