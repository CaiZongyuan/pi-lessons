---
title: "访问、创建与生命周期"
---

<div class="section-kicker">PI DURABLE / 4.2 · P. 53</div>

# 访问、创建与生命周期

---

> 只有 `tx.doc()` 会创建文档；所有读取操作对不存在的文档都返回 `undefined`，而作用域决定文档的生命何时结束。
> 
> 

<strong>你永远不需要显式“创建”文档。一次提交首次请求它时，它就存在了。读取则不同：读取绝不创建任何东西。本节结束后，你就能创建、读取和退役文档，并说明各个文档何时存在。</strong>

## `tx.doc()` 是获取或创建



在一次提交内，`tx.doc()` 返回一个草稿：只在本次提交内可编辑的文档视图。如果文档尚不存在，同一次调用会将它创建出来。参数取决于token的作用域：

|<strong>作用域</strong>|<strong>单个文档</strong>|<strong>文档族成员</strong>|
|---|---|---|
|`session`|`tx.doc(Doc)`|`tx.doc(Doc, key, seed)`|
|`conversation`|`tx.doc(Doc, conversationId)`|`tx.doc(Doc, conversationId, key, seed)`|
|`task`|`tx.doc(Doc, taskId)`|`tx.doc(Doc, taskId, key, seed)`|

> 来源为 `src/types.ts` 中 `Tx.doc` 的重载。读取操作接收同样的所有者和键，但不接收种子，另外还接收一个 `Context`。
> 
> 



<BookFigure id="D.4.2" :show-caption="false" />

> 创建就是写入：对不存在文档的第一次 `tx.doc()` 调用会在该提交中存储它的完整值。来源：`src/session/transaction.ts`；ID 4、seq 2 及该值来自 `research/capture/extra-p4/documents.txt`。
> 
> 



图中跟踪了一次创建过程。Session 找不到当前文档（步骤 2–3），于是运行 `initial()`、向存储申请新 ID，然后把一个草稿交给你的代码（步骤 4–7）。在同一次提交中再次请求，会得到同一个草稿（spec §3\.3）。你的编辑进入草稿（步骤 8）。回调返回时，草稿被关闭，提交存储的是完整的最终值 `{"items": ["write docs"]}`，而不是最初的空值（步骤 9–10）。只有提交成功后，其他读取方才能看到它（提交，原书第29页）。



<aside class="manual-callout callout-warning durable-callout" role="note" data-source-page="54">

<strong>读取也会写入</strong>

对不存在的文档调用 `tx.doc()` 就是一次写入，即便代码只读取草稿也一样。若只想查看而不创建，请使用 `snapshot()`。提交结束后仍被保留的草稿已经失效：向它赋值会“抛出异常：草稿已被撤销”（spec §3\.4）。

</aside>

## 读取绝不创建



对于不存在的文档，“snapshot、state 和 watch 查询均返回 `undefined`”（spec §12）。将 `undefined` 视为默认值。在示例 11 中，待办清单不存在时，提示词区段不显示任何内容；工具首次写入时，才由 `tx.doc()` 创建清单（示例 11）。



|<strong>方法</strong>|<strong>返回内容</strong>|
|---|---|
|`snapshot()`|当前值|
|`snapshotAsOf()`|写入某个条目时的值；仅适用于可回溯文档|
|`documentState()`|只读的实时状态（8\.1，原书第125页）|
|`watchDoc()`|已提交变更的流（8\.2，原书第129页）|



以上为读取方法。Session、Harness、任务、工具和钩子都可以使用 `snapshot()` 和 `snapshotAsOf()`（`src/types.ts`、`src/harness/types.ts`）。



快照是共享的，而不是复制的，也没有被冻结。如果代码修改了它，后续读取方会看到该变更（spec §3\.4）。修改前先复制。

## 什么会结束文档的生命



文档从创建到退役的每一段生命称为一个实例世代，各有自己的 ID。将文档退役后重新创建，会获得新的 ID；ID 永远不会复用（spec §3\.2）。采集记录在提交 12 中将 `app.draft`（ID 5）退役，又在提交 13 中重新创建了它（ID 18）。观察者看到退役时，得到的值为 `null`。



<BookFigure id="D.4.3" :show-caption="false" />

> 一个实例世代从创建它的提交起，一直存活到将其退役的提交；作用域决定什么会让它退役。同一个 SQLite 文件先由普通 Session 写入 seq 1–14，再以 Harness 重新打开并写入 seq 15–19。来源：`research/capture/extra-p4/documents.txt` 和 `document-publications.txt`。
> 
>
