<a id="sec-4-1"></a>

## 4.1 定义文档

<p class="lede">定义是一个带类型的词元，它固定文档的 kind、version、所有者和 fork 行为，而存储下来的记录会记住其中每一项选择。</p>
智能体需要聊天之外的状态：一份待办清单、一份计划、用户的设置。如果这类状态与记录（transcript）分开存放，一次崩溃就可能让两者失去同步。文档就是这类状态，它与条目存在同一次提交里。提交是一次原子保存：其中的一切要么一起存下，要么都不存。读完本节你就能定义一个文档，并选定会话被分叉时它的行为。文档是一个 JSON 对象，每次提交改动一点。`Storage` 把每次改动保存为一小串编辑，或者保存整个值（基线与增量（p. 56））。`Harness` 把自己的状态放在五个内置文档里（内置文档（p. 60）），而你用同一个函数 `defineDoc()` 定义你的文档。

<aside class="note">每个会话一份待办清单 `README §Your Own State` `TS`</aside>
```ts
const Todos = defineDoc<{ items: string[] }>({
kind: "app.todos",
version: 1,
scope: "conversation",
history: "latest", // or "rewindable" to read old values with snapshotAsOf() fork: "initial", // what a fork starts with: "initial", "current", or "asOf"
initial: () => ({ items: [] }),
});
await root.commit(async (tx) => {
(await tx.doc(Todos, root.id)).items.push("write docs"); }, context);
```

<aside class="note">The import line is omitted. "asOf" is only allowed together with history: "rewindable"; the compiler enforces it.</aside>
### 定义就是一个词元

`defineDoc()` 返回一个词元：一个普通对象，携带定义和值的类型。它只检查 `version` 是否为正整数 `src/documents.ts`。没有任何东西被注册。每一次读写都把这个词元传进去，如 `tx.doc(Todos, root.id)`，词元为那一次调用提供类型、初始值和迁移 `spec §3.3`。每个词元在一个模块里定义一次，然后到处 import。同一个 kind 的两份不同定义不受支持，也没有任何东西会发现它们 `spec §12`。

<img src="/pi-lessons/_assets/pi-durable/04-documents/fig-4.1.png" alt="THE SEVEN LEGAL SEMANTICS TREE" loading="lazy">

*作用域决定所有者与存续期；只有 conversation 文档才选择 history 和 fork。`src/types.ts` 中的联合类型 `DocumentSemantics`；fork 来自 `spec §3.7`。右列列出使用该组合的内置文档。*

<aside class="note">`kind` string 存储时使用的名字。它是公开协议的一部分，不能改名。 `version` 正整数 值的形状版本；随每次改动一起存储。 `scope` `"session"` · `"conversation"` · `"task"` 谁拥有它、它存续多久。 `history` `"latest"` · `"rewindable"` 仅 conversation。旧值是否仍可读。 `fork` `"current"` · `"initial"` · `"asOf"` 仅 conversation。分叉副本从什么开始。</aside>
<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>initial() () =&gt; T The value of a new document; must be a JSON object.</td><td></td><td></td></tr>
<tr><td>migrate? (value, fromVersion) =&gt; T Upgrades an older stored value when it is read (4.3 (p. 56)).</td><td></td><td></td></tr>
<tr><td>checkpointWhen? (value, ops, info) =&gt; boolean When to store the whole value instead of the edits (4.3 (p. 56)).</td><td></td><td></td></tr>
</table>

### 作用域、`history` 与 `fork`

作用域决定所有者与存续期。session 文档由每个 conversation 共享，一直活到你让它退役为止。conversation 文档只属于一个 conversation。task 文档只属于一个任务，并在任务结束时自动退役 `spec §3.1`。只有 conversation 文档才选择 history 策略和 fork 策略，因此共有七种合法组合。

<aside class="note">作用域决定所有者与存续期；只有 conversation 文档才选择 history 和 fork。`src/types.ts` 中的联合类型 `DocumentSemantics`；fork 来自 `spec §3.7`。右列列出使用该组合的内置文档。</aside>
`history: "latest"` 只保留当前值。`"rewindable"` 保留每一次存储的改动，于是 `snapshotAsOf(token, conversationId, entryId)` 能返回任意条目写入时的那个值。代价是存储：旧改动永不删除（4.3（p. 56））。`fork` 决定被分叉的 conversation 从什么开始（分叉（p. 43））。`"current"` 复制父级当前的值。`"asOf"` 复制分叉条目处的值，而只有可回溯的文档还留着它。`"initial"` 什么都不复制；分叉的第一次 `tx.doc()` 会创建一个全新的。在 run 02 中，父级里的 notes 文档读到的是 after goodbye，而取自更早条目的分叉则从 after hello 开始。

### 文档族

一个族是同一个定义管住同一个所有者下的许多文档，靠一个字符串 key 区分开来。想象「每个文件一份评审文档」。`defineDocFamily()` 接受相同的字段，外加 `family: true`，它的初始化函数会收到一个 seed：

<aside class="note">每个文件一份评审文档 `docs/pico-v5-chord-usage.md §2` `TS`</aside>
```ts
const ReviewDoc = defineDocFamily<ReviewState, ReviewInput>({
kind: "app.diff-review", version: 1, family: true, scope: "conversation",
history: "latest", fork: "current", initial: seed => ({ path: seed.path, patch: seed.patch, comments: [] }),
});
await tx.doc(ReviewDoc, conversationId, review.key, review.seed);
```

key 是地址的一部分，seed 不是。seed 只在成员首次创建时用一次，之后被忽略 `spec §12`。在这次捕获中，对 key `src/a.ts` 的第二次 `tx.doc()` 传入了 seed `{"path":"IGNORED"}`，成员仍保持 `"path":"src/a.ts"`。要修改成员，请编辑它。

### 这些选择会被存下来

每个存储的文档都记着自己的 kind、scope、history 和 fork 策略，因此定义它的代码不在时，已有数据依然说得通 `spec §3.2`。每次访问都会拿词元与那条记录比对。如果你在代码里把 fork 从 `"initial"` 改成 `"current"`，已有文档不会改变。它们会变得无法通过新词元读取，并抛出 `Document 4 (app.todos) does not match the supplied definition semantics` `src/documents.ts`。

<aside class="note">描述记录（transcript）的状态，比如计划：`rewindable` + `asOf`，这样从旧条目分叉出来的副本看到的正是那份计划。示例 27 的 `app.plan` 和内置的 `pi.agent` 就是这样。属于用户的状态，比如草稿：`current`，这样分叉会按它现在的样子复制 `docs/pico-v5-chord-usage.md §2`。只属于某个分支的状态，比如沙箱或开销：`initial`。复制一份开销计数器会重复计数，所以要「分叉从零开始」 `spec §8.6`。把 kind、scope、history 和 fork 当作永久不变。只有值的形状可以演进，靠 version 和 `migrate()`。</aside>
```
Sources: src/documents.ts; src/types.ts; spec §1, §3.1, §3.2, §3.3, §3.7, §8.6, §12; README §Your Own State; docs/pico-v5-chord-usage.md §2; ex 02, ex 27; run 02; research/capture/extra-p4/documents.txt (test/capture-p4-documents.ts)
```

<img src="/pi-lessons/_assets/pi-durable/04-documents/fig-4.2.png" alt="THE FIRST TX . DOC () OF A NEW DOCUMENT SEQUENCE" loading="lazy">

*创建是一次写入：对不存在文档的第一次 `tx.doc()` 会在那次提交里存下它的整个值。来自 `src/session/transaction.ts`；ID 4、seq 2 和该值取自 `research/capture/extra-p4/documents.txt`。*

<a id="sec-4-2"></a>

## 4.2 访问、创建与存续期

<p class="lede">只有 `tx.doc()` 会创建文档；任何读取对不存在的文档都返回 `undefined`，而作用域决定文档的存续期何时结束。</p>
你从不显式「创建」文档。某次提交第一次索要它时，它就存在了。读取不一样：读取从不创建任何东西。读完本节你就能创建、读取和退役文档，并说清每个文档在何时存在。

### `tx.doc()` 是 get-or-create

在一次提交内部，`tx.doc()` 返回一个草稿：仅对本次提交有效的文档可编辑视图。如果文档还不存在，同一个调用会把它创建出来。参数取决于词元的 scope：

<aside class="note">session `tx.doc(Doc)` `tx.doc(Doc, key, seed)`；conversation `tx.doc(Doc, conversationId)` `tx.doc(Doc, conversationId, key, seed)`；task `tx.doc(Doc, taskId)` `tx.doc(Doc, taskId, key, seed)`。以上是 `src/types.ts` 中的 `Tx.doc` 重载。读取传入同样的所有者与 key，不带 seed，外加一个 `Context`。</aside>
```
Creation is a write: the first tx.doc() of a missing document stores its whole value in that commit. From src/session/transaction.ts; ID 4, seq 2 and the value are from research/capture/extra-p4/documents.txt.
```

这幅图跟完一次创建。`Session` 找不到当前文档（步骤 2–3），于是运行 `initial()`，向存储要一个新 ID，并把一个草稿交给你的代码（步骤 4–7）。在同一次提交里再要一次会拿到同一个草稿 `spec §3.3`。你的编辑进入草稿（步骤 8）。回调返回时草稿关闭，提交存下整个最终值 `{"items": ["write docs"]}`，而不是那个空的初始值（步骤 9–10）。其他读者要等提交成功后才看得到（提交（p. 29））。

<img src="/pi-lessons/_assets/pi-durable/04-documents/fig-4.3.png" alt="THREE SCOPES OVER ONE STORAGE TIMELINE" loading="lazy">

*一个化身从创建它的那次提交活到让它退役的那次提交；由作用域决定是什么让它退役。同一个 `SQLite` 文件：一个普通 `Session` 写了 seq 1–14，随后这个文件以 `Harness` 的身份重新打开，写了 seq 15–19。`research/capture/extra-p4/documents.txt` 与 `document-publications.txt`。*

<aside class="note">对不存在的文档调用 `tx.doc()` 就是一次写入，即使你的代码只是读那个草稿。想只看而不创建，就用 `snapshot()`。提交之后仍留着的草稿已经死了：往它赋值会「抛出：草稿已被撤销」 `spec §3.4`。</aside>
### 读取从不创建

对不存在的文档，「快照、状态和观察查询都返回 `undefined`」 `spec §12`。把 `undefined` 当作默认值。在示例 11 中，待办清单缺失时某个提示词小节什么都不显示，而工具的 `tx.doc()` 在第一次写入时创建这份清单 `ex 11`。

快照是共享的，不是副本，而且它不是冻结的。如果你的代码改了它，后来的读者会看到这个改动 `spec §3.4`。修改之前先复制一份。

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>snapshot() the current value</td><td>当前值；</td><td></td></tr>
<tr><td>snapshotAsOf() the value when an entry was written; rewindable documents only</td><td>某个条目写入时的值，仅可回溯的文档可用；</td><td></td></tr>
<tr><td>documentState() a read-only live state (8.1 (p. 125))</td><td>只读的实时状态（8.1（p. 125））；</td><td></td></tr>
<tr><td>watchDoc() a stream of committed changes (8.2 (p. 129))</td><td>已提交改动的流（8.2（p. 129））。以上是读取方法。<code>snapshot()</code> 和 <code>snapshotAsOf()</code> 在</td><td></td></tr>
</table>

### 什么会终结一个文档

一个文档从创建到退役的每一次存续期就是一个化身，有自己的 ID。退役一个文档再重新创建，会得到一个新 ID；ID 从不复用 `spec §3.2`。这次捕获在提交 12 退役了 `app.draft`（ID 5），并在提交 13 重新创建它（ID 18）。观察者看到的退役形态是值 `null`。

```
An incarnation lives from its creating commit up to its retiring commit; scope decides what retires it. One SQLite file: a plain Session wrote seq 1–14, then the file was reopened as a Harness for seq 15–19. research/capture/extra-p4/documents.txt and document-publications.txt.
```

session 与 conversation —— 只有当你的代码调用 `retireDoc()` 时才结束。`Harness` 里没有任何东西会这么做。session 文档 `app.settings` 在关闭并重新打开后仍在，带着 `{"theme":"dark"}`。 task —— 在完成它那次任务的提交里结束 `spec §3.3`。任务 25 的最后一次提交写入 `done = 2` 并结束了任务，因此那最后一次编辑从未被读到。此后 `snapshot()` 返回 `undefined`，`tx.doc()` 抛出 `Task 25 is terminal`。

### 每个 conversation 都会得到的文档

`Harness` 在每一次创建或分叉 conversation 的提交中，通过一个创建钩子创建它的五个内置文档 `src/harness/harness.ts`。你可以用 `HarnessOptions.conversationCreated(tx, conversation)` 添加自己的文档，它在同一提交中紧随内置文档之后运行。用它放每个 conversation 都必须有的文档。单次调用的数据则用 `createConversation()` 或 `fork()` 的 `init` 选项。两者中任何一个抛出，整次创建都会失败。普通 `Session` 没有钩子，也没有内置文档。

<aside class="note">查看用 `snapshot()`，修改用 `tx.doc()`。每次读取返回的 `undefined` 都要处理；它意味着「尚未创建」或「已退役」。任何必须比任务活得更久的东西，都放进它的结果、一个条目或一份存续期更长的文档，在任务的最后一次提交中完成 `spec §12`。以 `pi.` 开头的 kind 属于 `Harness`。没有任何机制强制这一点，但复用其中一个会与 `Harness` 的行为冲突 `spec §12`。</aside>
```
Sources: src/session/transaction.ts (doc, retireDoc); src/session/session.ts; src/types.ts (Tx.doc, DocumentReader); src/harness/harness.ts (conversationCreated); src/harness/types.ts (HarnessOptions); spec §2.2, §3.2–3.4, §12; ex 11; research/capture/extra-p4/documents.txt, document-publications.txt (test/capture-p4-documents.ts)
```

<a id="sec-4-3"></a>

## 4.3 基线、增量与迁移

<p class="lede">`Storage` 把一个文档保存为偶尔出现的基线，也就是值的完整副本，加上它们之间的少量编辑；何时写基线由你的定义决定。</p>
每次改动都保存整个文档会浪费空间。只保存编辑会让读取越来越慢，因为每次读取都要重放所有编辑。Pi Durable 主要保存编辑，偶尔保存一份称为基线的完整副本。读完本节你就能在存储转储中读出一个文档的行、决定何时写基线，并安全地改变文档的形状。

### 两种记录

每一次存储的改动都是两者之一 `src/types.ts`（`DocumentContent`）：Base —— 整个值。在文档创建时、version 变化时，以及你的 `checkpointWhen()` 返回 true 时写入。 Delta —— 本次提交做出的编辑列表，表示为 `Chord` 操作。其余每一次改动都写成它。`Chord` 从普通的草稿编辑生成这些操作；你从不手写。什么都没改的提交就什么都不写。两种记录都会记下写入时所依据的定义 version。这次捕获用同一条规则对两个文档跑了五次提交，规则是 `info.deltasSinceBase >= 2`。`app.todos`（ID 4）是 `rewindable` 的；`app.draft`（ID 5）是 `latest` 的。

<aside class="note">五次提交之后的 `document_revisions` `research/capture/extra-p4/documents.txt` TEXT `document_id` `seq` `kind` `version` `content` 4 2 base 1 `{"items":["write docs"]}` 4 3 delta 1 `[["p",["items"],1,0,["fix build"]]]` 4 4 delta 1 `[["p",["items"],2,0,["ship"]]]` 4 5 base 1 `{"items":["fix build","ship"]}` 4 6 delta 1 `[["p",["items"],2,0,["celebrate"]]]`</aside>
```
5 5 base 1 {"text":"Dear team, we shipped."}
```

<aside class="note">5 6 delta 1 `[["s",["text"],"Done."]]` `SQLite` 行，每次存储改动一行。`"p"` 是数组拼接操作（路径、索引、删除数量、元素），`"s"` 则是设置一个值。</aside>
一次读取会找到最新的基线，并按顺序应用它之后的每一个增量。ID 5 在 seq 5 之前没有行，因为在 `latest` 文档上，一个基线让存储可以删除更早的一切。

<img src="/pi-lessons/_assets/pi-durable/04-documents/fig-4.4.png" alt="A DOCUMENT ’ S RECORDS OVER COMMIT SEQUENCE ANATOMY" loading="lazy">

*一次读取从最新的基线开始，重放它之后的增量；只有可回溯的文档保留更早的记录。行取自 `research/capture/extra-p4/documents.txt`。Seq 7 是一次分叉，对 ID 4 什么都没写；seq 8 和 9 来自下面的迁移。*

### 检查点谓词

每次普通改动都会问一次 `checkpointWhen(value, ops, info)`。如果它返回 true，那次改动就存为基线。`info.deltasSinceBase` 是自上一个基线以来的增量数量，不计本次改动；`Session` 会跟踪它，因此这次检查不需要读存储。在这次捕获中，这条规则先后看到 0、1、2，于是 seq 5 成了基线。如果谓词抛出，整次提交失败。

有两种写法都很好用。一个计数，例如 `info.deltasSinceBase >= 31`，给一次读取要重放的增量数封顶。一个状态判断，像 `pi.live` 那样，只要文档回到一个小的静止值就取一个基线。这个选择只影响存储：观察者和视图在两种情况下收到的编辑都相同（8.1（p. 125））。

<aside class="note">没有 `checkpointWhen`，一个文档在创建时存一个基线，之后永远只存增量。读取会越来越慢，存储「在文档存活期间可以无界增长」 `spec §12`。`Storage` 从不自己取基线 `spec §3.5`。</aside>
### 一个基线让存储可以删除什么

对 `latest` 的 session 或 task 文档来说，一个基线让所有更早的记录失去用处，三种存储后端都会把它们删掉。退役这样一个文档会删掉它的全部记录。可回溯的文档什么都保留，因为旧值必须始终可读 `spec §3.5`。

这就是 `snapshotAsOf()` 能工作的原因。在 `app.todos` 上，条目 6 时的值（写于 seq 3）是基线 2 加增量 3：`{"items":["write docs","fix build"]}`。在 `app.draft` 上，同样那次调用会失败并抛出 `Document 5 does not retain historical content`。

### 版本与迁移

要改变文档的形状，就提高 `version` 并加上 `migrate()`。每条记录都存着自己的版本，每次读取都拿它与词元的版本比对 `spec §3.6`：

<img src="/pi-lessons/_assets/pi-durable/04-documents/fig-4.5.png" alt="WHAT A FORK COPIES STRUCTURE" loading="lazy">

*一次分叉按各文档自己的策略复制每个 conversation 文档，复制到一个只有单个基线的新化身里。ID、序号和值取自 `research/capture/extra-p4/documents.txt`；策略出自 `spec §3.7`。*

这次捕获把 `app.todos` 从字符串列表改成了对象列表：

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>same as the token’s the value is used as stored</td><td></td><td></td></tr>
<tr><td>older, token has migrate migrate(value, storedVersion) returns the current shape</td><td></td><td></td></tr>
<tr><td>older, no migrate throws requires migration from version 1</td><td></td><td></td></tr>
<tr><td>newer than the token’s throws has newer version 2 than 1</td><td></td><td></td></tr>
<tr><td>From src/documents.ts and spec §3.6.</td><td></td><td></td></tr>
</table>

<aside class="note">一个 version 2 的词元 `test/capture-p4-documents.ts` `TS`</aside>
```ts
kind: "app.todos", version: 2,
scope: "conversation", history: "rewindable", fork: "asOf",
initial: () => ({ items: [] }), migrate: (value, fromVersion) => {
if (fromVersion !== 1) throw new Error(`no migration from ${fromVersion}`);
return { items: (value.items as string[]).map((text) => ({ text, done: false })) }; },
});
```

<aside class="note">kind、scope、history 和 fork 都不变；只有形状和版本动了。这次捕获中的 `checkpointWhen` 一行被略去。</aside>
迁移发生在文档被使用时，绝不会批量进行。通过新词元做的一次 `snapshot()` 返回了迁移后的值，没有写入任何东西。通过它的第一次写入存下了一个 version 2 的基线（seq 8）。从那以后，旧的 version 1 词元会失败并抛出 `has newer version 2 than 1`，因此回滚到那次写入之前的代码再也无法打开这个文档。旧的 version 1 记录保留下来，通过新词元调用 `snapshotAsOf()` 会即时迁移它们。

### 分叉会复制文档

在条目 7 处分叉 conversation 2，会按每个文档自己的策略复制它们：

<aside class="note">A fork copies each conversation document by its own policy, into a new incarnation with one base. IDs, sequences and values from research/capture/extra-p4/documents.txt; the policies are those of spec §3.7.</aside>
每个副本都是一份全新的独立文档，有新 ID 和一个基线 `spec §3.7`。副本由存储自己造；远程后端则在服务端完成。副本保留存储时的版本；子副本在第一次使用时自行迁移。复制已提交的值带来一条限制：分叉的那次提交不得同时改动父级中 current-policy 的文档。它会失败并抛出 `Cannot fork conversation 2 while changing its current-policy documents`。先把父级的改动提交掉 `src/session/transaction.ts`。

<aside class="note">给每个长命的文档都配一个 `checkpointWhen`。增量计数是最简单的规则，比如 spec 里的 `info.deltasSinceBase >= 31`。改变文档形状要用新版本加 `migrate()`。绝不要改它的 kind：新名字找不到任何东西，只会在旧文档旁边创建一个空文档。改名需要显式复制并退役 `spec §12`。只在需要旧值时才选 `rewindable`。它永远不会释放空间。</aside>
```
Sources: src/types.ts (DocumentContent, CheckpointInfo); src/documents.ts; src/session/transaction.ts; src/session/session.ts (snapshotAsOf); src/session/forks.ts; src/storage/sqlite/storage.ts; spec §3.2, §3.5–3.7, §12; docs/pico-v5-handoff.md §10; test/session-checkpoints-migrations.test.ts; research/capture/extra-p4/documents.txt, document-publications.txt (test/capture-p4-
documents.ts)
```

<a id="sec-4-4"></a>

## 4.4 内置文档

<p class="lede">五个 conversation 文档保存着 `Harness` 在两次提交之间需要的东西：智能体是什么、供应商看到的是谁、什么在运行、什么在等待，</p>
<p class="lede">以及它花了多少。</p>
`Harness` 存储自身状态的方式和你存储自己的一样：放在文档里。UI 读它们来显示加载指示、队列或账单。读完本节你就能读出任意 conversation 视图的 `docs` 块，并说清每一部分由什么写入。这五个文档和你的一样用 `defineDoc()` 定义，它们的词元已导出：`AgentDoc`、`ProviderDoc`、`LiveDoc`、`InboxDoc` 和 `UsageDoc` `src/index.ts`。五个都属于同一个 conversation，随它一起创建，并在它的视图里以 `docs[kind]` 出现（conversation 视图（p. 129））。你自己的文档不会挂在那里；用 `watchDoc()` 观察它们。

在一个使用工具的轮次之后，根 conversation 的视图里是这些值：

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>pi.agent model, tools, instructions rewindable · asOf every change 7.2 (p. 106)</td><td></td><td></td></tr>
<tr><td>pi.provider the provider session ID latest · initial every change 6.3 (p. 91)</td><td></td><td></td></tr>
<tr><td>pi.live what is running now latest · initial nothing runs 6.2 (p. 88)</td><td></td><td></td></tr>
<tr><td>pi.inbox queued inputs latest · initial the inbox is empty 6.1 (p. 84)</td><td></td><td></td></tr>
<tr><td>pi.usage tokens and cost latest · initial every change 6.6 (p. 100)</td><td></td><td></td></tr>
</table>

### 出生时与分叉时

每个新 conversation 都在创建它的那次提交里拿到全部五个。其中四个永远以同样的方式开始。只有 `pi.agent` 取决于 conversation 是怎么来的 `spec §2.2`；`src/harness/agent.ts`（`createAgent`）：

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>pi.agent {} a copy of the owner conversation’s agent the parent’s agent as of E</td><td></td><td></td></tr>
<tr><td>pi.provider a new UUIDv7, never copied</td><td></td><td></td></tr>
<tr><td>pi.live {}: nothing running</td><td></td><td></td></tr>
<tr><td>pi.inbox { items: [] }: nothing queued</td><td></td><td></td></tr>
<tr><td>pi.usage { models: {}, tools: {} }: zero spend</td><td>模型、工具、指令</td><td></td></tr>
</table>

<aside class="note">副本只有一次：「所有者后来的改动不会传到它那里」 `spec §12`。</aside>
### 每个文档

`pi.agent` —— 为这个 conversation 选定的内容：模型、思考级别、扩展、工具、指令和工作目录。它存的是名称，从不存代码 `src/harness/types.ts`（`AgentState`）。`configure()` 修改它，工具结果也可以增删工具。名称如何变成一个运行中的智能体，见「每个 conversation 的智能体」（p. 106）。

`pi.provider` —— `{ sessionId }`，供应商看到的 ID，用于提示词缓存亲和。重置、压缩、模型更换和重新打开都会保留它 `spec §2.2`。在 1.0.2 之前存储的 conversation 会在第一次请求时拿到一个 `src/harness/provider.ts`；`CHANGELOG.md`。 `pi.live` —— 运行控制与进度。`run` 恰好在 conversation 忙碌期间存在；generation、工具和压缩显示正在执行中的内容 `src/harness/live.ts`。 `pi.inbox` —— `{ items }`，等待下一个边界的输入与写入，按顺序排列 `src/harness/inbox.ts`。 `pi.usage` —— 这个 conversation 的开销，按 provider/modelId 和工具名为键。失败和中止的尝试也计入 `spec §8.6`。`Harness.usage()` 把所有 conversation 加起来。 `pi.live` 展示了一条好的检查点规则如何让存储保持小巧：只要没有东西在运行，它就写一个基线，因此它的编辑不会堆积超过一轮工具调用：

<aside class="note">工具运行期间的 `pi.live` 记录 `research/capture/jsonl-dir-midrun/doc-2.jsonl` TEXT seq 6 base `{"run":{"taskId":9,"inputs":[8]},"tools":[{"callId":"call-1",`</aside>
```
"name":"count","taskId":12,"status":"pending"}]}
```

<aside class="note">seq 8 delta `[["s",["tools",0,"status"],"running"]]` seq 9 delta `[["s",["tools",0,"output"],"1\n"]]` seq 10 delta `[["a",["tools",0,"output"],"2\n3\n"]]`</aside>
```
Other fields of each line are omitted. At seq 6 the tool was still pending, so nothing was running and the rule chose a base. After the run, the file held a single line: the base {} at seq 17 research/capture/jsonl-dir/doc-2.jsonl.
```

<aside class="note">从视图的 `docs` 块构建 UI 状态：加载指示用 `pi.live`，队列用 `pi.inbox`，开销用 `pi.usage`。只通过 `configure()` 修改 `pi.agent`。另外四个不要写；它们归 `Harness` 所有。</aside>
<aside class="note">Sources: src/harness/agent.ts; src/harness/provider.ts; src/harness/live.ts; src/harness/inbox.ts; src/harness/usage.ts; src/harness/harness.ts; src/harness/types.ts (AgentState); src/index.ts; spec §2.2, §6, §8.2, §8.6, §12; CHANGELOG.md 1.0.2; research/capture/view-final.json, jsonl-dir-midrun/doc-2.jsonl, jsonl-dir/doc-2.jsonl</aside>
