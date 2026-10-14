---
title: "基值、增量与迁移"
---

<div class="section-kicker">PI DURABLE / 4.3 · P. 56</div>

# 基值、增量与迁移

---

> 存储用偶尔写入的基值，也就是完整值副本，加上其间的小幅编辑来保存文档；你的定义决定何时写入基值。
> 
> 

每次变更都保存整个文档会浪费空间。只保存编辑又会让读取越来越慢，因为每次读取都需要重放全部编辑。Pi Durable 大多数时候存储编辑，偶尔存储一份完整副本，称为基值。本节结束后，你就能读懂存储转储中的文档行，选择何时写入基值，并安全地改变文档结构。

## 两种记录



每一项已存储的变更都属于以下两种之一（`src/types.ts`，`DocumentContent`）：

- 基值：整个值。在创建文档、版本变更，或 `checkpointWhen()` 返回 `true` 时写入

- 增量：本次提交产生的编辑列表，形式为 Chord 操作。其他每次变更都写入增量。Chord 根据普通的草稿编辑生成这些操作；你不需要手工编写



没有改变任何内容的提交不会写入内容。两种记录都会记下写入时使用的定义版本。采集记录对两个文档执行了五次提交，两者都使用同一条规则：`info.deltasSinceBase >= 2`。`app.todos`（ID 4）是可回溯文档，`app.draft`（ID 5）则只保留最新值。



五次提交后的 `document_revisions`；来源：`research/capture/extra-p4/documents.txt`

<BookFigure id="D.4.4" :show-caption="false" />



SQLite 行，每个已存储的变更占一行。`"p"` 表示数组拼接操作（路径、索引、删除数量、项目），`"s"` 表示设置一个值。



读取时，先找到最新基值，再按顺序应用此后的每个增量。ID 5 在 seq 5 之前没有记录，因为只保留最新值的文档一旦写入基值，存储就可以删除所有更早的记录。



<BookFigure id="D.4.5" :show-caption="false" />

> 读取从最新基值开始，并重放之后的增量；只有可回溯文档会保留更早的记录。数据行来自 `research/capture/extra-p4/documents.txt`。Seq 7 是一次分叉，没有为 ID 4 写入任何内容；seq 8 和 9 来自下文的迁移。
> 
> 

## 检查点判定函数



每次普通变更都会调用一次 `checkpointWhen(value, ops, info)`。若返回 `true`，该变更就存为基值。`info.deltasSinceBase` 是从上一个基值起的增量数量，不包括本次变更；Session 会跟踪它，因此检查时不需要读取存储。采集记录中，规则依次看到 0、1、2，因此 seq 5 成为基值。如果判定函数抛出异常，整个提交都会失败。



两种写法都很实用。一种使用数量，例如 `info.deltasSinceBase >= 31`，为读取需要重放的增量数量设置上限。另一种检查状态，例如 `pi.live` 的做法：每当文档回到较小的静止值，就写入一个基值。这一选择只影响存储：无论选哪种方式，观察者和视图接收到的编辑都相同（8\.1，原书第125页）。



<aside class="manual-callout callout-warning durable-callout" role="note" data-source-page="57">

<strong>没有检查点，就没有上限</strong>

没有 `checkpointWhen` 时，文档只在创建时存储一个基值，此后永远存储增量。读取会越来越慢，存储“在文档存活期间可能无限增长”（spec §12）。存储绝不会自行生成基值（spec §3\.5）。

</aside>

## 基值允许存储删除哪些内容



对于只保留最新值的文档、Session 文档或任务文档，基值会让所有更早的记录失去用途，三种存储后端都会删除它们。此类文档退役时，其全部记录也会删除。可回溯文档则保留所有记录，因为旧值必须仍可读取（spec §3\.5）。



这正是 `snapshotAsOf()` 能够工作的原因。在 `app.todos` 中，条目 6（写于 seq 3）时的值由基值 2 加增量 3 得到：`{"items":["write docs","fix build"]}`。对 `app.draft` 发起同样调用则失败，错误为 `Document 5 does not retain historical content`。

## 版本与迁移



要改变文档结构，请提高 `version` 并添加 `migrate()`。每条记录都存有其版本，每次读取都会将它与token的版本比较（spec §3\.6）：

|<strong>存储的版本</strong>|<strong>发生什么</strong>|
|---|---|
|与token版本相同|按存储原样使用该值|
|较旧，且token有 `migrate`|`migrate(value, storedVersion)` 返回当前结构|
|较旧，没有 `migrate`|抛出 `requires migration from version 1`|
|比token版本更新|抛出 `has newer version 2 than 1`|

> 来源：`src/documents.ts` 和 spec §3\.6。
> 
> 



采集记录将 `app.todos` 从字符串列表改成了对象列表：



版本 2 的token；来源：`test/capture-p4-documents.ts`

```ts
const TodosNext = defineDoc<TodosV2>({
    kind: "app.todos", version: 2,
    scope: "conversation", history: "rewindable", fork: "asOf",
    initial: () => ({ items: [] }),
    migrate: (value, fromVersion) => {
        if (fromVersion != 1) throw new Error(`no migration from ${fromVersion}`);
        return { items: (value.items as string[]).map((text) => ({ text, done: false })) };
    },
});
```

> `kind`、`scope`、`history` 和 `fork` 均保持不变；改变的只有结构和版本。采集代码中的 `checkpointWhen` 行已省略。
> 
> 



迁移在使用文档时发生，绝不会批量执行。通过新token调用 `snapshot()`，会返回迁移后的值，但不写入任何内容。第一次通过新token写入时，会存储版本 2 的基值（seq 8）。此后，旧的版本 1 token会因 `has newer version 2 than 1` 而失败，因此代码一旦回滚到这次写入之前的版本，就无法再打开该文档。旧的版本 1 记录仍然保留，通过新token调用 `snapshotAsOf()` 时，会即时迁移这些记录。

## 分叉会复制文档



在条目 7 处对对话 2 分叉时，会按每个文档自身的策略复制它们：

<BookFigure id="D.4.6" :show-caption="false" />

> 分叉按照每个对话文档自身的策略复制它，形成一个带有单个基值的新实例世代。ID、序号和值来自 `research/capture/extra-p4/documents.txt`；策略来自 spec §3\.7。
> 
> 



每个副本都是全新且独立的文档，具有新的 ID 和一个基值（spec §3\.7）。复制由存储自行完成；远程后端会在服务端完成复制。副本保留已存储的版本，子对话在自己首次使用时再迁移。复制的是已提交值，因此有一条限制：执行分叉的提交不能同时修改父对话采用 `current` 策略的文档，否则会失败并报错 `Cannot fork conversation 2 while changing its current-policy documents`。请先提交父对话的变更（`src/session/transaction.ts`）。



> <strong>这对你意味着什么：</strong>
> 
> - 为每个长期存活的文档提供 `checkpointWhen`。按增量数量判定，例如规范中的 `info.deltasSinceBase >= 31`，是最简单的规则
> 
> - 通过新版本和 `migrate()` 改变文档结构。永远不要重命名它的 `kind`：新名称查不到旧文档，会在旧文档旁创建一个空文档。重命名需要显式复制并退役旧文档（spec §12）
> 
> - 只有需要旧值时才选择 `rewindable`。它永远不会释放空间
> 
> 



> 来源：`src/types.ts`（`DocumentContent`、`CheckpointInfo`）；`src/documents.ts`；`src/session/transaction.ts`；`src/session/session.ts`（`snapshotAsOf`）；`src/session/forks.ts`；`src/storage/sqlite/storage.ts`；spec §3\.2、§3\.5–3\.7、§12；`docs/pico-v5-handoff.md` §10；`test/session-checkpoints-migrations.test.ts`；`research/capture/extra-p4/documents.txt`、`document-publications.txt`（`test/capture-p4-documents.ts`）。
> 
>
