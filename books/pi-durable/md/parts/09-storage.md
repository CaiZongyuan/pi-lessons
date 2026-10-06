<img src="/pi-lessons/_assets/pi-durable/09-storage/fig-9.1.png" alt="THE STORAGE INTERFACE
S T R U C T U R E" loading="lazy">

*Session 存储的一切都经过一次调用；它读取的一切都是按键查找或游标扫描。图中是 `src/types.ts` 里 Storage 的八种写入类型与方法。*

<a id="sec-9-1"></a>

## 9.1 存储契约

<p class="lede">存储要么完整保存每一次提交，要么什么都不保存，并响应查找和分页扫描；其余规则都归 Session。</p>
Session 提交的一切最终都进入存储：一个 SQLite 文件、一个文本文件目录，或内存。提交是一次原子保存：其中的内容要么一起存下，要么都不存。存储必须让每次提交保持这种状态，并响应精确查找和分页扫描。这几乎就是 Pi Durable 对它的全部要求。读完本节，你就能说出存储承诺了什么、哪些规则改归 Session，以及提交失败时该怎么办。

### 一个职责狭窄的小接口

后端就是任何实现了 `src/types.ts` 中 Storage 接口的对象。包里附带三个：`SqliteStorage`、`JsonlStorage` 和 `MemoryStorage`（SQLite（见第 144 页）、JSONL（见第 148 页）、内存（见第 152 页））。你挑一个交给 Harness。此后只有 Session 会调用它，每次写入都走一次提交（提交与变更线，见第 29 页）。

这样的分工是有意为之。Session 检查语义：记录是否合法、引用、祖先关系和任务状态转移。存储只检查它能独立检查的东西：一个批次是否原子、ID 是否唯一、不可变记录是否保持不可变，以及它交还的是副本（`src/types.ts`）。存储从不看到文档定义；它按给定的方式存储文档编辑，只在响应读取时重放它们。Session 本身已经一次只跑一个提交，所以后端不需要自己的锁（spec §10）。

<aside class="note">Session 存储的一切都经过一次调用；它读取的一切都是按键查找或游标扫描。图中是 `src/types.ts` 里 Storage 的八种写入类型与方法。所示的游标是三个已发布后端都采用的形态。</aside>
### 唯一的写入：提交

`commit(writes, context)` 原子地存储一批写入，并返回它的 `Seq`，即该提交的序号。序号「严格递增，但可能有间隔」，而一旦 `commit()` resolve，之后的每次读取都能看到这一批（spec §10）。存储把序号盖在它保存的内容上。正是这样，文档后来才能被读回某个条目写入时的样子（基线、增量与迁移，见第 56 页）。

```
conversation value: ConversationRecord a new immutable record
entry value: EntryRecord a new immutable record and its commit sequence
task value: TaskRecord the complete record, replacing the previous one
submission value: SubmissionRecord the complete record, replacing the previous one
document.create record, content (a base) a new incarnation, stamped createdAt
document.copy record, source: { id, at } a new incarnation that starts from the source’s committed value
document.change id, content (base or delta) one more revision document.retire id the incarnation, stamped retiredAt The StorageWrite union in src/types.ts. A base is a document’s complete value; a delta is a batch of Chord operations on top of the previous revision.
```

提交失败时：只有一种失败是安全的。`StorageRejected` 「意味着某批次在任何持久效果发生之前就被拒绝，并且保证没有提交」。Session 会回滚并继续。`commit()` 抛出的任何其他错误都会毒化 Session：它再也无法知道该批次是否已存储，于是拒绝后续提交（spec §10）。毒化对你的宿主意味着什么，见「提交失败时」（第 33 页）。

### 读取：按键查找与分页扫描

按键查找返回一条记录，或 `undefined`。扫描返回一页 `{ items, next? }`；把 `next` 传回去即可取下一页。游标是不透明的：只能把它传回同一存储上的同一次扫描（spec §10）。Harness 每页读 256 项，而它发起的每次读取背后都有索引（spec §10）。

<aside class="note">`conversation(id)` → record —— 精确 ID / `entry(id)` → `{ entry, commitSeq }` —— 任意条目 / `entry(conversationId, id)` → `{ entry, commitSeq }` —— 仅当那个会话能看到它 / `findLatestHeadMarker(conversationId, at?)` → entry —— `at` 或之前最新的头指针标记 / `task(id)`、`submission(id)` → record —— 最新的完整记录 / `submissionByRequest(conversationId, requestId)` → record —— 宿主去重（提交项，见第 84 页）/ `findDocument(address, at)` → DocumentRecord —— 某个地址上存续的化身 / `document(id, at)` → StoredDocument —— 该值、其版本、已重放的增量 / `scanConversations(query)` → page —— 按 owner 分页；ID 升序 / `scanEntries(query)` → page —— 一个 ID 区间，最新在前，穿过 fork 祖先 / `scanTasks(query)` → page —— 按会话、kind、status、中止标记、background 分页 / `scanSubmissions(query)` → page —— 按会话、status；ID 升序 / `scanDocuments(query)` → page —— 一个作用域，可选 kind；ID 升序 / `close()` —— 释放资源；之后所有调用都失败。每个方法还接受最后一个 context 参数。`src/types.ts` 与 spec §10。</aside>
`document(id, at)` 是唯一需要计算的读取。它找到该时点或之前最新的基线，按序应用其后的增量，然后返回值。在 `"current"` 处，已退场的化身返回 `undefined`。若一个不保留历史的文档被问到旧的时点，则直接失败而不是猜测（定义文档，见第 50 页）。

<aside class="note">你很少自己调用存储。挑一个后端，打开它，交给 Harness。除 `StorageRejected` 之外的提交错误会毒化 Session。把它关掉再重新打开存储；重新打开后的状态才是真相。要写一个后端？把一致性测试套件传进去（9.4，见第 152 页）。</aside>
后端作者需要知道的细节：所有记录共享同一个 ID 空间，来自 `mintId()`；ID 1 是根会话。一个批次对每个文档化身最多包含一次 create 或 change，外加一次可选的退场，且版本变更必须是基线（spec §10）。`commit()` 结束之后不要保留参数里的任何东西，并返回彼此独立的值（spec §4）。

```
Sources: spec §4, §10; src/types.ts (Storage, StorageWrite); src/session/session.ts; src/harness/context.ts; src/storage/memory.ts;
src/storage/sqlite/storage.ts; src/testing/storage-conformance.ts; docs/pico-v5-handoff.md §1–2
```

<a id="sec-9-2"></a>

## 9.2 SQLite

<p class="lede">一个 SQL 事务就是一次提交；每条记录都以 JSON 完整保存，查询所需的少数几列放在旁边。</p>
SQLite 把整个 Session 装在一个文件里。任何必须跨重启存活的东西都该用它。读完本节，你就能打开一个数据库、用普通的 SQLite 客户端找到任意一条记录、预判一次崩溃或断电会损失什么，并在 Node 之外运行同一个后端。

### 打开文件

`openNodeSqliteStorage(path, options)` 来自 `@earendil-works/pi-durable/storage/sqlite/node`，它会创建父目录，并用 Node 内置的 `node:sqlite` 打开文件。它开启预写日志（`journal_mode = WAL`、`synchronous = NORMAL`），并应用任何待执行的 schema 迁移（`src/storage/sqlite/node.ts`）。

<aside class="note">`walAutoCheckpointPages` 1,000 —— WAL 自动检查点阈值，单位为页；0 表示关闭 / `busyTimeoutMs` 5,000 —— 等待其他连接释放锁的时长（SQLite 自身的默认值是 0）。`NodeSqliteStorageOptions`，`src/storage/sqlite/node.ts`。</aside>
这些设置决定了什么能存活。「WAL 模式且 `synchronous = NORMAL`：提交可挺过进程崩溃；最新的可能在断电或宿主故障时丢失」（README §Storage）。一个 SQL 事务就是一次提交，所以进程若在提交中途死掉，结果是全有或全无（spec §11.2）。`close()` 会把预写日志折回文件里。close 之后，采集结果显示只有一个 `session.sqlite`，没有 WAL 文件（`research/capture/extra-p9/sqlite-revisions.txt`）。

### 九张表

每张记录表的形状都相同：几列供查询过滤，外加一个 `record` 列，以 JSON 保存完整记录。读取时只 select `record` 并解析它。其余列是同一条语句里从记录写出的副本，所以 JSON 永远是真相。

<img src="/pi-lessons/_assets/pi-durable/09-storage/fig-9.2.png" alt="THE SQLITE SCHEMA
S T R U C T U R E" loading="lazy">

*每张记录表都把查询列从 JSON 记录里提出来；文档内容单独存放，每次改动它的提交占一行。图中是 `research/capture/sqlite-schema.sql` 的全部九张表；「idx」标出被索引使用的列。记账类数值取自 `research/capture/sqlite-rows.txt`，在一个轮次之后。*

<aside class="note">the `tasks` 表及其索引（`research/capture/sqlite-schema.sql`）　SQL　CREATE TABLE tasks ( id INTEGER PRIMARY KEY, conversation_id INTEGER NOT NULL, kind TEXT NOT NULL CHECK (status IN ('pending', 'running', 'waiting', 'completing', 'terminal')), abort_requested INTEGER NOT NULL CHECK (abort_requested IN (0, 1)), background INTEGER NOT NULL CHECK (background IN (0, 1)), record TEXT NOT NULL CHECK (json_valid(record))</aside>
```
) STRICT;
CREATE INDEX tasks_by_status ON tasks (status, id); CREATE INDEX tasks_by_conversation ON tasks (conversation_id, id);
```

<aside class="note">……另外三个索引，分别在 kind、abort_requested 和 background 上，此处省略。每个索引都以 id 结尾，因此扫描按 ID 顺序分页。</aside>
会话与条目永不改变，所以它们只是普通插入，同一 ID 第二次写入会失败。任务与提交项则原地替换：「活跃的任务状态转移替换一行。终态任务保留为小记录」（spec §11.2）。运行途中，采集结果显示第 9 代任务在等待第 12 个工具，后者正在运行。运行结束后，两行都是终态，只保留一个结果（`research/capture/sqlite-rows-midrun.txt`、`sqlite-rows.txt`）。手动读取文件

- 带索引的字符串以 JSON 编码存储：一个任务的 kind 列读出来是 `"\"pi.generation\""`。这样能让特殊 Unicode
- 在各种 SQLite 绑定下都无损（`src/storage/sqlite/storage.ts`）。
- `durable_metadata.next_id` 是 TEXT（"16"），因为 `node:sqlite` 拒绝超出 JavaScript 安全范围的整数。
- `record_ids` 为每个已提交的 ID 保存一行，连同它的记录类型。正是它让 ID 空间成为全局的。
<img src="/pi-lessons/_assets/pi-durable/09-storage/fig-9.3.png" alt="REVISIONS OF TWO DOCUMENTS
T I M E L I N E" loading="lazy">

*可回溯的文档保留每一个修订；只保留当前值的文档在基线提交时丢弃较旧的行。行与读取结果取自 `research/capture/extra-p9/sqlite-revisions.txt`：两个 app 文档在同一批提交中被改动，seq 2–7。*

### 一次提交，一个事务

`SqliteStorage.commit()` 先在内存里检查文档命令，然后运行一个 SQL 事务：读出下一个序号，检查每个新 ID 与文档命令，写入各行，并推进计数器。如果任何环节抛出异常，事务回滚，那个序号也不会被用掉（`src/storage/sqlite/storage.ts`）。`mintId()` 是内存计数器，不是写入。由一个后来失败的事务铸出的 ID，在重新打开后可能再次发出。这是安全的：只有已提交写入中的 ID 才绝不可复用（不变式 5，见第 16 页）。

### 文档修订

文档内容存放在 document_revisions，每个文档每次改动它的提交占一行。一行要么是基线，保存完整值；要么是增量，保存 Chord 操作。要读取一个文档，SQLite 找到该时点或之前最新的基线，在同一个事务内应用其后的增量，这样并发提交无法调包基线（`src/storage/sqlite/storage.ts`）。

```
A rewindable document keeps every revision; a current-only document drops its older rows when a base commits. Rows and reads from research/capture/extra-p9/sqlite-revisions.txt: two app documents changed in the same commits, seq 2–7.
```

是否保留历史取决于文档。可回溯的文档保留每一行，因此 `document(2, 4)` 会从 2 处的基线加两个增量重建出 seq 4 时的值。其他文档都只保留当前值：新基线提交时，同一个事务会删除它较旧的行。这就是那一轮运行中每个内置文档最终都只剩一行基线的原因（`research/capture/sqlite-rows.txt`）。这里每一次读取都是索引查找；采集到的查询计划显示没有表扫描（`research/capture/extra-p9/sqlite-revisions.txt`）。

### Node 之外

SQLite 内核不需要任何 Node API。`SqliteStorage.open(db)` 来自 `@earendil-works/pi-durable/storage/sqlite`，接受任何实现了 SqliteDatabase 的对象。这样同一个后端就能在任何有人写小型适配器的地方运行，「例如在 Bun 上或在 Cloudflare Durable Objects 中」（README §Storage）。

<aside class="note">适配器要实现的外观（`src/storage/sqlite/database.ts`）　TS</aside>
```ts
export interface SqliteExecutor {
exec(sql: string): Promise<void>; run(sql: string, ...params: SqliteValue[]): Promise<void>;
get<T extends object>(sql: string, ...params: SqliteValue[]): Promise<T | undefined>;
all<T extends object>(sql: string, ...params: SqliteValue[]): Promise<T[]>;
}
export interface SqliteDatabase extends SqliteExecutor {
transaction<T>(callback: (transaction: SqliteExecutor) => Promise<T>): Promise<T>; close(): Promise<void>;
}
```

<aside class="note">文档注释和 SqliteValue 类型（`null`、`number`、`bigint`、`string` 或字节）此处省略。</aside>
适配器的规则简短但严格。在事务内部，只能使用回调收到的那个句柄；回调结束后它就失效了。其他工作要等事务完成，所以在回调内部调用数据库本身永远不会 settle。如果回调 reject，就回滚并以同一个错误 reject。如果回滚也失败，就以另一个错误 reject，比如一个 AggregateError，「以免调用方把回调错误误认为已保证回滚」（`src/storage/sqlite/database.ts`）。Schema 变更是有版本号的迁移，在文件打开时于一个事务内应用。目前只有一个，版本 1。由更新版本包写出的文件会被拒绝（「Durable SQLite schema version 2 is newer than supported version 1」），迁移失败则回滚且数据完好（`src/storage/sqlite/migrations.ts`；`test/sqlite-migrations.test.ts`）。

<aside class="note">「同一时刻只有一个进程拥有一个存储；没有跨进程锁」（README §Storage）。每个 SqliteStorage 都从自己的计数器铸出 ID，所以两个进程操作同一个文件可能铸出相同的 ID。于是第二次提交会失败并毒化那个 Session，或者悄悄替换掉另一个进程的任务或提交项。只运行单一所有者是宿主的职责（限制与非目标，见第 168 页）。</aside>
<aside class="note">任何长期存在的东西都用 SQLite。进程崩溃不会丢失任何已提交内容；断电可能丢掉最新的提交。调试时，用任意 SQLite 客户端打开文件并读 record 列。在其他运行时上，写一个 SqliteDatabase 适配器并对它跑一致性测试套件。</aside>
```
Sources: spec §4, §11.2; README §Storage; src/storage/sqlite/{storage,node,database,migrations}.ts; test/sqlite-storage.test.ts;
test/sqlite-facade.test.ts; test/sqlite-migrations.test.ts; research/capture/sqlite-schema.sql, sqlite-rows.txt, sqlite-rows-midrun.txt; research/capture/extra-p9/sqlite-revisions.txt
```

<a id="sec-9-3"></a>

## 9.3 JSONL

<p class="lede">先写边车记录，再在 main.jsonl 写一个标记：标记存在，提交就存在。</p>
JSONL 存储是一个纯文本文件目录，你可以用 cat 直接读。它适合开发和调试，那里看得见每条记录比速度更重要。读完本节，你就能读这些文件、说出一次崩溃可能损失什么，并决定是否打开 fsync。

### 目录

`openNodeJsonlStorage(directory, context, options)` 来自 /storage/jsonl/node，打开或创建该目录。在其他运行时上，/storage/jsonl 里的 `JsonlStorage.open(directory, fs, context, options)` 通过任意 FileSystem 做同样的事（执行环境，见第 155 页）。每一行是一个 JSON 对象，分布在三类文件中（spec §11.3）：main.jsonl —— 每次提交一行标记，只增不减。doc-<id>.jsonl —— 一个文档的内容：它的基线与增量。task-<id>.jsonl —— 一个活跃任务先后留下的记录，任务结束时被删除。文档文件和任务文件是边车：它们保存体积大、易变的数据。标记完整携带小记录，比如条目和任务的最终记录；其余它只携带一个指针：一个文件加上一个序位，后者从 0 起为该提交的边车行编号（`src/storage/jsonl/storage.ts`）。

<img src="/pi-lessons/_assets/pi-durable/09-storage/fig-9.4.png" alt="ONE COMMIT, ONE MARKER, FOUR SIDECARS
A N A T O M Y" loading="lazy">

*一次 JSONL 提交就是 main.jsonl 里的一个标记，它按提交序号和序位指明自己的边车记录。图中是那一轮运行中计数工具运行时刻复制出的第 6 次提交：`research/capture/jsonl-dir-midrun/`。助手条目随标记一起走；两个任务和两个文档住在边车里。*

```
A JSONL commit is one marker in main.jsonl that names its sidecar records by sequence and ordinal. Commit 6 of the one-turn run, copied while the count tool was running: research/capture/jsonl-dir-midrun/. The assistant entry rides in the marker; the two tasks and two documents live in sidecars.
```

<aside class="note">第 6 次提交的标记（`research/capture/jsonl-dir-midrun/main.jsonl` 第 6 行）　JSON</aside>
```json
{
"format": 1, "type": "commit", "seq": 6,
"writes": [
{ "type": "entry", "value": { "model": [ … ], "kind": "pi.assistant", "id": 11,
"conversationId": 1, "byTaskId": 9 } },
{ "type": "task.sidecar", "id": 9, "ordinal": 0 },
{ "type": "task.sidecar", "id": 12, "ordinal": 1 }, { "type": "document.change", "id": 2, "ordinal": 2 },
{ "type": "document.change", "id": 4, "ordinal": 3 }
] }
```

<aside class="note">已做美化排版；在磁盘上是一行。条目的 model 消息已省略。</aside>
该轮结束后，两个任务文件都不见了，doc-2.jsonl 只剩一个基线（`research/capture/jsonl-files.txt`）。两件事都是下面要讲的回收做的。

### 发布

每次提交都遵循同样的三步（spec §11.3）：1. 把该提交的记录追加到每个受影响的边车；2. 向 main.jsonl 追加一条完整的标记，列出那些记录；3. 只有到这时才让该提交对读取可见。

<img src="/pi-lessons/_assets/pi-durable/09-storage/fig-9.5.png" alt="PUBLICATION AND RECLAMATION
S E Q U E N C E" loading="lazy">

*边车记录先落盘，标记把它们变成一次提交，回收只在发布之后运行。图中是一次为只保留当前值的文档写入新基线的提交，文件顺序由 `test/jsonl-storage.test.ts` 断言；第 2、5、7 步仅在 `fsync: true` 时发生。*

```
Sidecar records land first, the marker makes them a commit, and reclamation runs only after publication. A commit that writes a new base for a current-only document, in the file order asserted by test/jsonl-storage.test.ts; steps 2, 5 and 7 happen only with fsync: true.
```

未通过校验的批次不会触碰任何文件。一旦开始写入，任何追加或刷新失败都会毒化后端：每次调用都以 JsonlStoragePoisonedError reject，直到你重新打开；Session 也会被毒化（2.3，见第 33 页）。

fsync 选项决定什么能存活，默认为 false。不开启它，JSONL 能挺过进程崩溃，但挺不过断电、内核或磁盘故障。开启 `fsync: true` 后，每个边车会在其标记写入之前被刷新到磁盘。最新的提交在断电时仍可能消失，「但一个存活的标记不应越过它的边车数据」（spec §11.3）。

```
two new documents append ×2, append main append ×2, flush ×2, append main
```

<aside class="note">任务结束　append main，remove sidecar　append main，flush main，remove sidecar　每次提交的文件操作，取自 `test/jsonl-storage.test.ts`。</aside>
### 恢复

打开一个目录就是一次恢复过程，规则很短（spec §11.3；`src/storage/jsonl/storage.ts`）：残缺行 —— 文件末尾没有换行的部分会被截回最后一个换行处。未确认的记录 —— 只有被标记指名的边车行才算数，末尾未确认的行被截掉。损坏 —— 一条已确认的行若缺失、乱序，或位于未确认行之后，打开会以 JsonlCorruptionError 失败（除非后续一个基线让它变得无关紧要）。没有任何机制会修复它（spec §13）。残留 —— 被中断的回收留下的文件会被删除，任何仍欠着的回收会被补做。

<img src="/pi-lessons/_assets/pi-durable/09-storage/fig-9.6.png" alt="A TORN MARKER, BEFORE AND AFTER OPEN
C O M P A R I S O N" loading="lazy">

*打开一个 JSONL 目录会截掉残缺的标记，以及每一条没有标记确认的边车记录。`research/capture/extra-p9/jsonl-crash.txt`。*

在采集中，第 4 次提交本应把一个计数器设为 2 并把一个任务推进到 effect 阶段。它的边车行已经写入，但标记残缺。重新打开截掉了这三者：计数器读作 {"n":1}，任务仍处于 intent 阶段的 running，下一次提交又拿到 seq 4（`research/capture/extra-p9/jsonl-crash.txt`）。第 4 次提交从未发生，所以重新打开的 Harness 会再跑一遍 intent 阶段（5.3，见第 70 页）。

### 回收

回收会删除那些因更新的基线、退场或已完成的任务而变得多余的边车行，且只在该提交之后（spec §11.3）。可回溯的文档永不回收。如果回收失败，提交仍保持已发布状态，下一次打开会补完这件事（`src/storage/jsonl/storage.ts`）。

<aside class="note">进程崩溃绝不会留下半个提交。标记行完整，提交就存在。如果文件必须挺过断电并保持一致状态，打开 fsync: true。在大型存储上打开会很慢（9.4，见第 152 页）。</aside>
```
Sources: spec §11.3, §12, §13; src/storage/jsonl/storage.ts; test/jsonl-storage.test.ts; research/capture/jsonl-dir-midrun/, jsonl-files.txt; research/capture/extra-p9/jsonl-crash.txt
```

<a id="sec-9-4"></a>

## 9.4 内存、一致性与可移植性

<p class="lede">MemoryStorage 定义了每个后端的含义，一套共享测试套件来检验它，而存储内核在任何能写适配器的地方都能运行。</p>
这三个后端之所以可以互换，是因为它们都被同一份参考实现和同一套测试套件约束。读完本节，你就能根据实测代价挑选后端、用共享套件测试自己的后端，并在 Node 以外的运行时上运行存储。

### MemoryStorage 是参考实现

内存存储定义了其他后端必须做到的事。它复制自己保存的每一条记录和返回的每一条记录：「这是刻意模拟 SQLite 编解码和 JSONL 序列化自然形成的所有权边界」（spec §11.1）。因此，修改自己读到的记录的调用方无法改动存储，无论在内存里还是在磁盘上。内存存储对文档历史的保留或丢弃，也与持久后端完全一致。一个读取只保留当前值的文档旧时点的测试，在内存上和在 SQLite 上一样会失败。内存存储不持久化任何东西。用它做测试、示例和短生命周期的 Session。test/examples 中的大多数示例跑在它上面；恢复与重启示例（ex 13、23、24、31）用 SQLite，ex 17 用 JSONL。JSONL 内部也用内存存储来响应每次读取（`src/storage/jsonl/storage.ts`）。

### 一致性测试套件

自定义后端靠通过已发布后端所通过的那套套件来证明自己。它从 `@earendil-works/pi-durable/testing` 导出，可在任何兼容 Vitest 或 Jest 的运行器下运行：

<aside class="note">运行存储测试套件（README §Storage）　TS</aside>
```ts
import { registerStorageConformance } from "@earendil-works/pi-durable/testing";
import { describe, expect, it } from "vitest";
registerStorageConformance({ describe, expect, it }, "My Storage", async (use) => {
const storage = await openMyStorage(); try {
await use(storage);
} finally {
await closeMyStorage(storage);
}
});
```

<aside class="note">每个用例恰好调用 use 一次，且传入一个全新的空存储。</aside>
这套套件有 23 个用例。它们覆盖 ID 空间、原子批次与彼此独立的值、条目与 fork、会话与任务扫描、提交项、文档历史与地址，以及无损的字符串键（`src/testing/storage-conformance.ts`）。这个包会跑五遍：在内存、SQLite 和 JSONL 上，以及在每次提交后关闭并重新打开的 SQLite 和 JSONL 上。这套套件锁定的是含义，不是机制。崩溃恢复、刷新顺序和查询计划是按后端分别测试的，自定义后端需要自己补上这些测试。

<img src="/pi-lessons/_assets/pi-durable/09-storage/fig-9.7.png" alt="ENTRY POINTS AND WHAT THEY NEED
L A Y E R S" loading="lazy">

*SQLite 和 JSONL 的内核是可移植的；只有它们的 Node 适配器会碰 Node API。图中是 package.json 的子路径导出；两个内核也都接受你自己写的适配器。这条边界由 `test/storage-runtime-boundary.test.ts` 强制，它遍历每个入口点的导入。*

### 可移植内核，Node 适配器

<aside class="note">SQLite 和 JSONL 的内核是可移植的；只有它们的 Node 适配器会碰 Node API。图中是 package.json 的子路径导出；两个内核也都接受你自己写的适配器。这条边界由 `test/storage-runtime-boundary.test.ts` 强制，它遍历每个入口点的导入。</aside>
这种划分由一个测试强制。/storage/sqlite、/storage/jsonl 和 /env 不得导入任何 node: 模块，哪怕间接导入也不行。只有 /storage/sqlite/node 和 /storage/jsonl/node 是 Node 专属的。要在其他运行时上运行，就给 `SqliteStorage.open()` 一个 SqliteDatabase（SQLite，见第 144 页），或给 `JsonlStorage.open()` 一个 FileSystem（执行环境，见第 155 页）。

### 实测代价

这个包附带一个基准测试，在三个后端上跑相同的读写：`npm run bench:storage`。它的数据集含 1,000 条条目、300 个任务和 300 个文档。图中是它在 Apple M3 Max、Node 24.13.0 上跑一次得到的三行结果。

<img src="/pi-lessons/_assets/pi-durable/09-storage/fig-9.8.png" alt="THREE COSTS, THREE BACKENDS
C O M P A R I S O N" loading="lazy">

*JSONL 的读取和内存一样快，因为它就是内存；代价出现在每次提交和打开时。均值取自 `research/capture/extra-p9/bench-storage.txt`（Apple M3 Max、macOS 26.2、Node 24.13.0、2026-10-05）。提交与重新打开两行各 20 个样本，误差为 ±8–66%。每个面板有自己的刻度。*

这些数字源自各自的设计。JSONL 从内存响应读取，所以一次精确的条目查找代价与在内存上相同：0.44 µs，而 SQLite 是 2.85 µs。一次 JSONL 提交要追加到好几个文件，792 µs，而 SQLite 是 120 µs。打开一个 JSONL 目录要重放每个标记，这个数据集是 249 ms，而 SQLite 打开并完成首次读取用了 1.33 ms。规模十倍时，SQLite 占用 0.22 MiB 堆；JSONL 和内存各占超过 7 MiB（`research/capture/extra-p9/bench-storage-memory.txt`）。

<aside class="note">memory 无持久化；堆随存储增长；适合测试、示例和短会话 / SQLite 进程崩溃无损失；读取较慢；堆小；打开快；适合任何长期存在的东西 / JSONL 进程崩溃无损失；配合 fsync 断电也保持一致；提交慢；整个存储在内存里；打开时重放；适合调试与可读文件。本节及前两节的小结。</aside>
不同机器上的时间数字不可比较。要比较你自己的后端，使用从 /testing 导出的各个场景（`seedStorageBenchmark()` 以及读、写基准列表），并在一个进程里运行每个候选者，就像这个包的 `test/storage.bench.ts` 所做的那样。

<aside class="note">默认用 SQLite；测试中用内存；想读文件时用 JSONL。无论选哪个，一个存储只跑一个进程。没有后端会针对第二个进程加锁。自定义后端必须通过那 23 个用例，外加自己的崩溃测试。</aside>
```
Sources: spec §11.1; README §Storage, §Examples; src/storage/memory.ts; src/storage/jsonl/storage.ts; src/testing/{storage-conformance, runner,storage-benchmark}.ts; test/storage.bench.ts; test/memory-storage.test.ts; test/sqlite-storage.test.ts; test/jsonl-storage.test.ts; test/storage-runtime-boundary.test.ts; package.json; research/capture/extra-p9/bench-storage.txt, bench-
```

<aside class="note">storage-memory.txt</aside>
<img src="/pi-lessons/_assets/pi-durable/09-storage/fig-9.9.png" alt="THE ENVIRONMENT BOUNDARY
F L O W" loading="lazy">

*工具、提示词段落和任务阶段只能通过一个环境触达文件与进程，而这个环境由宿主每次使用时依据已提交状态构建。调用方见 README §Environment 和 `src/harness/{tool,generation,scheduler}.ts`；目标见 `src/harness/types.ts`。*

<a id="sec-9-5"></a>

## 9.5 执行环境

<p class="lede">工具只通过宿主为每次使用构建的 ExecutionEnv 触达文件与进程，所以会话在哪里运行是宿主的决定，不是工具的。</p>
你的智能体工具读文件、跑命令。执行环境决定在哪里：你自己的磁盘、每用户一个沙箱目录，或一个远程容器。工具从不直接接触机器；它们通过一个 ExecutionEnv，由宿主在每次需要时构建。读完本节，你就能给每个会话一个自己的沙箱、为远程宿主实现这个接口，并知道内置工具期待什么。

### 每次使用时构建

宿主提供一个函数，HarnessOptions.env。Harness 在任何工作需要环境时才调用它，绝不在 Session 那一行调用，且它可以是 async（`src/harness/types.ts`）。它会收到 conversationId、该会话的工作目录 cwd（如果它的 pi.agent 文档里设置了的话，见每会话智能体，第 106 页），以及 read，后者用于读取已提交的文档。

<aside class="note">工具、提示词段落和任务阶段只能通过一个环境触达文件与进程，而这个环境由宿主每次使用时依据已提交状态构建。调用方见 README §Environment 和 `src/harness/{tool,generation,scheduler}.ts`；目标见 `src/harness/types.ts`。</aside>
有三类工作会索要它。工具调用通过 api.env 接收它（定义工具，见第 112 页）。系统提示词的一个段落通过 input.env 接收它（系统提示词，见第 115 页）。任何任务阶段都可以用 runtime.env() 索取。允许返回 undefined：此时内置工具会以一个错误结果失败，「没有配置执行环境」。env 抛出的异常同样会变成该工具调用的错误结果（README §Environment；`src/tools/env.ts`）。因为环境是每次使用时构建的，崩溃后重跑的工具调用会拿到一个全新的环境，「带着该会话当前的 cwd，可能与第一次尝试不同」（spec §12）。只依据已提交状态构建它，如示例 29 那样为每个会话配一个自己的沙箱：

<aside class="note">每个会话一个沙箱（`test/examples/29-sandbox-per-conversation.ts`）　TS</aside>
```ts
const harness = await Harness.open(
new MemoryStorage(),
{
models, registry, // Committed reads only; a conversation without a sandbox gets no environment,
```

```ts
// so its tools fail cleanly. env: async ({ conversationId, read }, envContext) => {
const sandbox = await read.snapshot(Sandbox, conversationId, envContext);
return sandbox?.path === undefined
```

<aside class="note">? undefined</aside>
```
: new NodeExecutionEnv({ cwd: sandbox.path });
}, }, context,
```

```
);
$ node --conditions=source --experimental-strip-types test/examples/29-sandbox-per-conversation.ts alice's sandbox: from alice bob's sandbox: from bob Sandbox is an app document set when each conversation is created. Both conversations ran the same write tool, and each note landed in its own directory (run 29). The ternary is rewrapped to fit the page.
```

### 接口

ExecutionEnv 是一个 FileSystem 加一个 Shell，来自 `@earendil-works/pi-durable/env`。每个操作都返回结果而不抛出：`{ ok: true, value }` 或 `{ ok: false, error }`，其中 error 带一个 code，比如 not_found 或 timeout（`src/env/index.ts`）。

<aside class="note">identity id、cwd / paths absolutePath、joinPath、canonicalPath、exists / read readTextFile、readTextLines、openTextLineReader、readBinaryFile、openBinaryReader / write writeFile、appendFile、truncateFile、flushFile、renameFile / directories fileInfo、listDir、openDirReader、createDir、remove / temporary createTempDir、createTempFile、cleanup / changes watch　`src/env/index.ts`。truncateFile 和 flushFile 是为 JSONL 存储准备的。</aside>
id 指明文件命名空间：「相同的 id 无论 cwd 是什么，都看到相同路径上的相同文件」（`src/env/index.ts`）。每个本地 NodeExecutionEnv 都用 "node:local"；每个容器或远程宿主都需要自己的。id 让宿主可以为每次调用构建一个新的环境对象。内置的编辑与写工具在同一个文件上仍然是轮流的，因为它们按 id 加路径排队。那条队列是进程内的，「不是针对 bash 或其他进程的锁」（`src/tools/file-mutation-queue.ts`）。

### 运行命令

`exec(command, options, context)` 接受字符串或数组。字符串通过 shell 运行；NodeExecutionEnv 用 bash，回退到 sh -c。数组则直接运行 command[0]，其余作为它的参数，因此原样传到程序（`src/env/index.ts`；`src/env/node.ts`）。当参数来自模型或用户时，优先用数组形式。在 NodeExecutionEnv 中，timeout 的单位是秒，非零退出是一个成功结果，带上它的 exitCode。onOutput 接收每一个数据块，标记为 stdout 或 stderr。中止 context 会杀掉那条命令；cleanup() 在关闭时杀掉所有残留。

<img src="/pi-lessons/_assets/pi-durable/09-storage/fig-9.10.png" alt="A WINDOWED EXEC
S T R U C T U R E" loading="lazy">

*带窗口的 exec 可能丢弃调用方本来也会丢弃的输出，并精确统计自己丢弃了多少。info.skipped 的规则（`src/env/index.ts`）以及一致性用例中通过一个 200 字节、5 行的窗口打印 2,000 行的那一条。*

### 输出窗口

只保留命令输出末尾的工具可以明说这一点，远程环境随后就能跳过发送其余部分。调用方传入一个窗口（maxBytes、maxLines 以及节奏限制）。环境可以丢弃该末尾之外的输出，并在下一个数据块上用 info.skipped 报告丢弃了什么（`src/env/index.ts`；CHANGELOG 1.0.3）。

<aside class="note">带窗口的 exec 可能丢弃调用方本来也会丢弃的输出，并精确统计自己丢弃了多少。info.skipped 的规则（`src/env/index.ts`）以及一致性用例中通过一个 200 字节、5 行的窗口打印 2,000 行的那一条。</aside>
跳过是安全的，靠的是一条规则：紧跟跳过之后的数据块总是多于窗口，所以被丢弃的文本永远不可能属于保留的末尾。内置 bash 工具使用窗口（`src/harness/tool.ts`；`src/tools/bash.ts`）。NodeExecutionEnv 忽略 window 并送出全部内容；窗口在输出跨越网络时才划算。会变换输出的工具包装器必须关掉窗口，否则被跳过的文本会绕过它的变换（定义工具，见第 112 页）。

<aside class="note">要隔离会话，就从 HarnessOptions.env 为每个会话返回不同的环境。返回 undefined 会关掉文件与 shell 工具。只依据已提交状态构建环境：崩溃后重跑会重新构建。自定义环境要实现 FileSystem 和 Shell，以结果形式返回失败，给每个文件命名空间自己的 id，并运行来自 /testing 的 `registerEnvConformance`，它有 21 个用例。</aside>
细节：1.0.3 新增的能力。1.0.3 把四项能力设为必需，因此自定义环境必须补上它们（CHANGELOG 1.0.3）。openBinaryReader(path, { noFollow? }) 按位置读取一个已打开的文件，它的 scanLines() 一趟就能找到一段行；read 工具两者都用。openDirReader(path) 分页遍历目录。watch(targets, onChange) 报告变化的路径、溢出（需全部重扫）或错误。而 exec 接受数组形式。

```
Sources: spec §12 (environment on recovery); README §Environment; CHANGELOG 1.0.3; src/env/{index,node,node-watch}.ts; src/harness/{types,harness,tool}.ts; src/tools/{env,bash,file-mutation-queue}.ts; src/testing/env-conformance.ts; ex 29, run 29
```
