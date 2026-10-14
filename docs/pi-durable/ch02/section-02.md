---
title: "提交与变更串行队列"
---

<div class="section-kicker">PI DURABLE / 2.2 · P. 29</div>

# 提交与变更串行队列

---

> 每次写入都经过一个串行化回调；其中的所有写入要么一起存储，要么全部不存储。在存储确认成功之前，观察者看不到任何变化。
> 
> 

<strong>Session 的每个变更都经过 `commit()`。提交是一次原子保存：其中所有内容要么一起存储，要么全都不存储。提交在称为变更串行队列的队列中逐个运行。</strong>本节介绍你能在提交内部做什么，以及程序的其他部分何时能够看到变化。

## 唯一的写入方式



<strong>`session.commit(change, context)` 是唯一的写入路径。你的回调收到一个事务 `tx`。回调返回时，它所写的一切会作为一个批次存储；若回调抛出异常，则全部丢弃。</strong>见 `ex 00`。“<strong>一次 Session 提交在所有记录与文档写入之间具有原子性。</strong>”见不变量 1，`spec §1`。<strong>`Conversation.commit()` 将它绑定到一个对话；任务的 `runtime.commit()` 还会在所追加的每个条目上标记该任务的 ID。</strong>



<strong>一次读取、追加条目、编辑文档并创建任务的提交</strong> · `docs/spec.md §4`

```ts
await session.commit(async tx => {
    const conversation = await tx.conversation(conversationId); // 表读取
    const live = await tx.doc(LiveDoc, conversationId);

    await tx.appendEntry(conversationId, message); // 第一次表写入
    delete live.generation; // 文档变更仍然有效
    await tx.createTask(Follow, {}, {
        ownership: { kind: "conversation" }, conversationId,
    }); // 继续进行表写入没有问题
}, context);
```

> 读取排在最前面，因为它必须如此；首次写入之后，文档草稿仍然可用。
> 
> 

## 变更串行队列



<strong>变更串行队列一次运行一个提交。一个提交从回调开始的那一刻起就占据队列，直到存储已经保存该批写入且观察者已被通知</strong>：“覆盖回调执行、准备、存储结算、已提交基线采纳以及发布入队”。见 `spec §4`。在此期间，其他提交都不会开始。下图展示一次提交如何经过这些阶段。

### 步骤 1–5：你的回调内部



如果 Session 正在关闭或已经中毒，`commit()` 会立即拒绝。否则，回调会拿到一个全新的事务并开始运行；其操作分为三组，见下表。



<strong>需要牢记的规则是先读后写。“第一次表写入之后的任何表读取都会抛出 `ReadAfterWrite`。”</strong>见 `spec §4`。错误消息可能是 `Tx.conversation() cannot read tables after the first table write`。表读取直接访问存储，而存储尚未看到当前事务的写入，因此写后读可能与这些写入相矛盾。你永远不需要这样读：创建方法会返回自己创建的记录。



|<strong>分组</strong>|<strong>操作</strong>|<strong>规则</strong>|
|---|---|---|
|表读取|`conversation`、`entry`、`task`、`scanConversations`、`scanEntries`、`latestHeadMarker`、`scanTasks`、`submissionByRequest`|只能在第一次表写入之前进行|
|表写入|`createConversation`、`forkConversation`、`appendEntry`、`createTask`、`createSubmission`、`settleSubmission`、`placeSubmission`|返回创建的记录或 ID|
|文档|`doc`（获取或创建）、`retireDoc`|表写入前后都可使用|

> 接口来自 `src/types.ts` 中的 `Tx`；规则来自 `spec §4`。
> 
> 



<BookFigure id="D.2.3" :show-caption="false" />

> 从接纳开始直到发布入队，始终持有队列；回调在之后运行。水蓝色条表示被持有的队列。依据 `src/session/session.ts` 和 `src/session/transaction.ts` 绘制。
> 
> 



文档的工作方式不同。`tx.doc()` 返回一个草稿，即可像普通对象一样编辑的可变副本，并且能看到你自己的修改。你赋入的值“按值复制，且必须是严格 JSON”；`undefined` 或 `Date` 会让提交在存储任何内容之前失败。见 `spec §1`（不变量 6）；`test/session-documents.test.ts`。回调结束时，每个草稿都会被撤销。保留到回调之后的草稿，在下一次使用时会抛出异常；迟到的 `tx` 方法调用则会以 `Transaction has settled` 拒绝。

### 步骤 5 与 6 之间：检查批次



回调返回后，Session 将其工作汇成一个批次并进行检查。首先会捕获忘记 `await` 的情况：如果仍有待完成的 `tx` 调用，提交就会失败，错误为 `Session commit callback settled before its pending Tx operations`。随后，草稿转化为最终值，批次接受验证，例如检查每个所有者任务是否存在且仍处于活动状态。这里的任何失败都会回滚整个提交。见提交失败时会怎样（原书第33页）。没有写入的批次永远不会到达存储：既不存储，也不发布。

### 步骤 6–8：先存储，再通知其他各方



`Storage.commit(writes)` 以原子方式保存该批写入，并返回其 `Seq`。提交一旦开始，取消你的 `context` 就不再能停止它：“调用者取消不会中断存储结算，也不会撤销提交。”见 `spec §4`。存储成功之后，Session 换入新的文档值，并构造一个发布对象 `{ seq, changes }`。仍在队列上时，它把该对象交给每个 `subscribeCommits()` 监听者。下面是模型请求调用工具的那一轮中的一次发布：



<strong>提交观察者看到的提交 seq 6</strong> · `research/capture/sqlite-commits.txt`

```text
commit seq=6
    entry 11 kind=pi.assistant byTask=9
    task 9 pi.generation status=waiting phase=tools on=[12] policy=allSettled
    task 12 pi.tool status=pending phase=call
    document pi.live (2) 2 op(s)
    document pi.usage (4) 1 op(s)
```

> 每行对应一项变更，由捕获脚本概括。助手条目、父任务的等待、新工具任务以及两个文档变更，要么一起变得可见，要么全部不可见。
> 
> 



提交观察者在队列上运行，“仅用于捕获不可变状态”（不变量 7）。它们“不得抛出异常、阻塞或调用 Session API”。见 `spec §4`。你的观察订阅回调和文档状态回调稍后会在队列之外运行，见 Chord 与文档状态（原书第125页），因此缓慢的屏幕永远不会阻碍下一次提交。

## 绝不要在提交内部等待副作用



“外部模型、进程、工具、网络和人工副作用都在其外部运行。”见 `spec §4`。违反这条规则会付出双重代价：

- <strong>队列停滞</strong>：当回调等待网络调用时，其他所有提交都会排在后面等待，包括工具进度、其他对话和调度器的提交。

- <strong>记录失真</strong>：如果进程在副作用发生之后、批次存储之前终止，副作用已经发生，却没有任何记录。如果回调在副作用之后抛出异常，批次会回滚，而副作用仍然没有记录。



修正方式是先提交意图，再在任何提交之外执行副作用，然后提交结果：这就是副作用三明治（原书第70页）。所有内置工具任务和生成任务都按这种方式工作。



<aside class="manual-callout callout-warning durable-callout" role="note" data-source-page="31">

<strong>发后即忘</strong>

在回调内部启动后放任继续运行的工作，仍然可能修改尚未结束的事务；事务一旦结算，这些工作就会失败。规范明确不支持这种做法。见 `spec §12`。等待每个 `tx` 调用，并且只在 `commit()` 兑现之后才启动后台工作。

</aside>




> <strong>这对你意味着什么：</strong>
> 
> - 先完成所有表读取，再进行写入。文档可以在任意时刻读取和修改
> 
> - 等待每个 `tx` 调用，保持回调简短，并且不包含 I/O
> 
> - 草稿中只能放 JSON，绝不要在回调结束后保留草稿
> 
> - 在观察订阅中响应变化，不要在提交观察者中响应
> 
> 

### 细节



即便只有一条队列，读取仍然成本低廉。对于已缓存其已提交值的文档，读取不必排队。见 `src/session/session.ts`（`snapshot`）。存储只在 `Storage.commit()` 结算之前借用批次，并且“每次存储读取都返回一个独立的 JSON 值”。见 `spec §4`。因此，你持有的任何对象都不会与已存储状态共享引用。批次检查会验证分叉来源、所有者和任务替换，退役在本次提交中结束的任务所拥有的文档，最后运行每个文档的 `checkpointWhen` 谓词，决定写入完整副本还是增量。见基值与增量（原书第56页）；`src/session/transaction.ts`。



> 来源：`spec §1`（不变量 1、4、6、7）、§2\.2、§3\.3、§4、§12；`src/session/session.ts`（`commit`、发布、`snapshot`）；`src/session/transaction.ts`（Tx 操作、结算、批次组装、采纳）；`src/errors.ts`（`ReadAfterWrite`）；`src/types.ts`（`Tx`、`StorageWrite`、`CommitPublication`、`Storage.commit`）；`ex 00`；`research/capture/sqlite-commits.txt`；`research/capture/extra-p23/commit-failures.txt`
> 
>
