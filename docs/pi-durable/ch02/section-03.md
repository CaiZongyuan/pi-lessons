---
title: "提交失败时会怎样"
---

<div class="section-kicker">PI DURABLE / 2.3 · P. 33</div>

# 提交失败时会怎样

---

> 失败发生的位置决定其结果：在存储之前，是普通回滚；在存储内部，则要么是保证无写入的拒绝，要么是致命的不确定性。
> 
> 

<strong>大多数失败的提交都无害：没有存储任何内容，你可以继续工作。但有一种失败并非如此。如果存储失败时有可能已经保存了该批写入，Session 就会停止接收工作，直到你关闭它并重新打开存储。</strong>本节介绍如何区分这些情况，以及分别应当如何处理。

## 三种结果



提交可能在五个位置失败，而每种失败最终都会落入三种结果之一：回滚、被存储拒绝或中毒。不变量 8 明确了这一区分：“不确定的存储失败会使已打开的 Session 发生致命故障。它不会发布任何内容，且必须重新打开。准备和检查点失败发生在存储接纳之前，会正常回滚。”见 `spec §1`。



<BookFigure id="D.2.4" :show-caption="false" />

> Storage 接纳之前的失败会回滚；Storage 结果不确定，或 Storage 已提交之后的采纳失败，都会使 Session 中毒。底部一行说明了各情况下接下来该做什么。分支依据 `src/session/session.ts` 和 `src/session/transaction.ts`。
> 
> 



捕获的失败运行在一个普通 Session 上展示了每种结果；其底层是 `MemoryStorage`，可以人为使其下一次提交失败：

```bash
$ node --conditions=source --experimental-strip-types test/capture-p23-context.ts
read after write -> ReadAfterWrite: Tx.conversation() cannot read tables after the first table write
callback throws -> Error: validation failed
empty commit -> ok "nothing written"
storage rejects -> StorageRejected: rejected before any durable effect
next commit -> ok {"kind":"app.note","data":"after rejection","id":6,"conversationId":2}
uncertain storage failure -> Error: disk vanished
next commit -> Error: Session is poisoned by a failed commit after storage admission;
reopen it (cause: Error: disk vanished)
snapshot -> Error: Session is poisoned by a failed commit after storage admission; ...
close -> ok undefined
```



来自 `research/capture/extra-p23/commit-failures.txt`；较长的中毒错误行已换行，第二条同类消息有所删节。存储拒绝和之前的两次失败消耗了 ID 3–5。

## 存储之前：普通回滚



五个失败位置中有三个发生在存储之前：回调本身、settle（仍有待完成的 `tx` 调用）和 prepare（批次检查）。其中任何一步失败，都会丢弃所有变更，并重新抛出原始错误。见 `src/session/transaction.ts`。这包括你自己抛出的异常、`ReadAfterWrite`、草稿中的非 JSON 值，以及指向不存在的对话或任务的引用（`Conversation N does not exist`）。



回滚是完整的。没有任何内容被存储，也没有任何内容被发布，每个文档都保留原先的值。有一个测试让修改了两个文档的提交失败；之后读取两个文档，结果都与之前相同，而下一次提交正常工作。见 `test/session-documents.test.ts`。唯一留下的痕迹是 ID 序列中的间隙。见记录与 ID（原书第25页）。



在任务内部，回滚的提交通常会结束该任务。如果阶段处理函数让错误向外传播，任务就以 `faulted` 结束。见阶段、步骤与进度（原书第67页）。在一个捕获场景中，某个任务试图在结束自身的同一次提交中创建归自己所有的工作；批次检查以 `Task owner 12 is completing` 拒绝它，随后任务以 `faulted` 结束，该提交没有存储任何内容。见 `research/capture/NOTES.md`（笔记 6）。

## 存储内部：拒绝或不确定



批次一旦交给 `Storage.commit()`，Session 就不能再作任何假设。存储契约定义了唯一安全的例外：“StorageRejected 表示一个批次在产生任何持久化效果之前就已被拒绝，保证没有提交。Session 会正常回滚这样的批次；Storage 接纳之后的未知失败仍然是致命的，因为其提交状态不确定。”见 `spec §10`。后端只在能够证明失败没有产生任何效果时才使用它。例如，SQLite 会将失败的分叉复制报告为 `Document copy N was rejected`。见 `src/storage/sqlite/storage.ts`。



任何其他存储错误都会使 Session 中毒：它把自身标记为不可用。存储刚刚成功之后，Session 在换入新值时发生失败，也会导致同样的结果，因为这时存储已经持有一次提交，而内存尚未反映它。见 `src/session/session.ts`。



中毒的 Session 会拒绝一切依赖其状态的操作。之后的每次提交、`snapshot()`、`state`、`watch` 和队列读取，都会抛出 `Session is poisoned by a failed commit after storage admission; reopen it`，并将原始错误作为 `cause`。见 `src/session/session.ts`。失败批次中的任何内容都不会发布，因此没有观察者会看到一个可能并不存在的值。见 `test/session-documents.test.ts`。



Session 不会重试，因为两种猜测都不安全。如果批次已经提交，内存就落后于存储；如果没有提交，在内存中应用它就会发布一个并不存在的变更。只有存储知道事实，而新的 Session 会准确读取它实际保存的内容。“不要捕获错误后继续使用它。”见 `spec §12`。JSONL 存储在一次不确定的追加之后，也会使自身中毒。见 JSONL（原书第148页）。



|<strong>错误</strong>|<strong>抛出时机</strong>|<strong>此后 Session 的状态</strong>|
|---|---|---|
|`ReadAfterWrite`|表写入之后进行表读取|可用|
|`...settled before its pending Tx operations`|回调过早返回|可用|
|`Transaction has settled`|结算之后使用 Tx 或草稿|可用|
|`StorageRejected`|存储中，在任何持久化效果之前|可用|
|其他任何存储错误|存储中，结果未知|中毒|
|采纳错误|存储已经提交之后|中毒|
|`Session is closed`|`close()` 开始后的任何调用|关闭中|

> 消息来自 `src/errors.ts`、`src/session/session.ts` 和 `src/session/transaction.ts`。第三个导出的错误类 `ConversationBusy` 是一种接纳结果，不是提交失败。见提交请求（原书第84页）。
> 
> 

## 先关闭，再重新打开



恢复从 `close()` 开始；即便 Session 已中毒，它也能工作。它按固定顺序运行。见 `spec §2.2`：

1. <strong>封闭接纳</strong>：立即关闭接纳入口。新的提交和读取以 `Session is closed` 拒绝；Harness 还会拒绝新的对话操作和提交请求操作

2. <strong>通知</strong>：同步运行 `subscribeClose()` 监听者。Harness 在这里停止观察订阅，并向任务调用发出信号；每个文档状态和观察订阅都保留最后一个值

3. <strong>等待汇合</strong>：Harness 等待任务、工具和钩子调用返回，“包括忽略自身信号的代码”。见调度器（原书第73页）

4. <strong>结算</strong>：封闭接纳之前已获接纳的提交，会在队列上完成。随后队列清除监听者和缓存，并关闭存储



“关闭不会写入任何任务结果。”见 `spec §2.2`。运行中的任务在存储中仍保持 `running`，与进程终止完全一样。`close()` 兑现之后，“新的 Harness 可以打开同一个 Storage”。



重新打开，就是对同一个存储执行普通的 `Harness.open()`。它只会发现已经提交的内容，并将遗留下来的 `running` 任务改回 `pending`。见调度器（原书第73页）。请获取新句柄；旧句柄已经失效。如果某个任务在意图提交后被重新打开，它可能已经执行过副作用；这正是副作用三明治（原书第70页）处理的情形。



<aside class="manual-callout callout-note durable-callout" role="note" data-source-page="35">

<strong>如果进程终止</strong>

在 `Storage.commit()` 内部发生崩溃，就是一种不确定情形，只不过已经没有进程可以被标记为中毒。SQLite 将每次提交存储在一个 SQL 事务中；JSONL 则只在其侧文件写好之后才发布提交标记。无论哪种方式，重新打开时，该批写入要么完整存在，要么完全不存在。见 SQLite（原书第144页）、JSONL（原书第148页）。

</aside>




> <strong>这对你意味着什么</strong>
> 
> - 除非 Session 已经中毒，否则应将抛出异常的提交视为“什么也没发生”
> 
> - 绝不要捕获中毒错误后继续工作。关闭 Harness，然后重新打开存储
> 
> - 如果你编写存储后端，只有在能够证明没有存储任何内容时，才抛出 `StorageRejected`
> 
> 



> 来源：`spec §1`（不变量 8）、§2\.2（关闭与重新打开）、§4、§10、§12；`src/session/session.ts`（`commit`、中毒检查、`close`）；`src/session/transaction.ts`（失败与成功结算、批次组装）；`src/errors.ts`；`src/storage/sqlite/storage.ts`（文档复制拒绝）；`test/session-documents.test.ts`（回滚与中毒测试）；`test/session-forks.test.ts`（`StorageRejected` 回滚）；`research/capture/extra-p23/commit-failures.txt`；`research/capture/NOTES.md`（笔记 1 和 6）
> 
>
