---
title: "SQLite"
---

<div class="section-kicker">PI DURABLE / 9.2 · P. 144</div>

# SQLite

---

> 一个 SQL 事务对应一次提交；每条记录都以完整 JSON 保存，旁边只有查询所需的少量列。
> 
> 

SQLite 把整个 Session 保存在一个文件中。对于必须经受重启而保留的内容，它就是应选的后端。读完本节，你就能打开数据库、用普通 SQLite 客户端找到任意记录、预测崩溃或断电的代价，并在 Node 之外运行同一个后端。

## 打开文件



来自 @earendil\-works/pi\-durable/storage/sqlite/node 的 openNodeSqliteStorage\(path, options\) 会创建父目录，并使用 Node 内置的 node:sqlite 打开文件。它启用预写日志（journal\_mode = WAL，synchronous = NORMAL），并应用所有待执行的模式迁移，见 src/storage/sqlite/node\.ts。

|<strong>选项</strong>|<strong>默认值</strong>|<strong>效果</strong>|
|---|---|---|
|walAutoCheckpointPages|1,000|WAL 自动检查点阈值，以页为单位；0 表示禁用|
|busyTimeoutMs|5,000|等待另一个连接所持锁的时长（SQLite 自身默认值为0）|

> 来源：NodeSqliteStorageOptions，src/storage/sqlite/node\.ts。
> 
> 



这些设置决定哪些内容能在故障后保留。“WAL 模式配合 synchronous = NORMAL：提交可以经受进程崩溃；最新的提交可能因断电或宿主机故障而丢失”，见 README §Storage。一个 SQL 事务对应一次提交，因此进程在提交中途终止，只会留下完整提交或完全不留下，见 spec §11\.2。close\(\) 会把预写日志合并回文件。关闭之后，捕获中只剩一个 session\.sqlite，没有 WAL 文件，见 research/capture/extra\-p9/sqlite\-revisions\.txt。

## 九张表



每张记录表都有相同的形态：少量用于查询过滤的列，以及一个以 JSON 保存完整记录的 record 列。读取只选择 record 并解析它。其他列都是在同一条语句中从记录复制写入的，因此 JSON 始终是真实依据。



<BookFigure id="D.9.2" :show-caption="false" />

> 每张记录表都从 JSON 记录中提取查询列；文档内容独立存放，每次改变它的提交各占一行。图中包含 research/capture/sqlite\-schema\.sql 的全部九张表；“idx”标记被索引使用的列。记账值来自一个轮次之后的 research/capture/sqlite\-rows\.txt。
> 
> 



tasks 表及其索引，来源：research/capture/sqlite\-schema\.sql：

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'waiting', 'completing', 'terminal')),
    abort_requested INTEGER NOT NULL CHECK (abort_requested IN (0, 1)),
    background INTEGER NOT NULL CHECK (background IN (0, 1)),
    record TEXT NOT NULL CHECK (json_valid(record))
) STRICT;

CREATE INDEX tasks_by_status ON tasks (status, id);
CREATE INDEX tasks_by_conversation ON tasks (conversation_id, id);
```



这里省略了另外三个分别针对 kind、abort\_requested 和 background 的索引。每个索引都以 id 结尾，因此扫描按 ID 顺序分页。



对话和条目从不改变，因此只使用普通插入，对同一 ID 的第二次写入会失败。任务和提交请求则原地替换：“存活任务的状态转换会替换一行。终态任务作为小型记录保留”，见 spec §11\.2。运行期间的捕获显示，生成任务9正在等待工具任务12，而后者正在运行。运行结束后，两行都变为 terminal，并且只保留一个结果，见 research/capture/sqlite\-rows\-midrun\.txt、sqlite\-rows\.txt。

## 手工读取文件



被索引的字符串以 JSON 编码形式保存：任务的 kind 列读出来是 `"\"pi.generation\""`。这能让特殊 Unicode 字符在不同 SQLite 绑定之间保持无损，见 src/storage/sqlite/storage\.ts。



durable\_metadata\.next\_id 的类型是 TEXT（"16"），因为 node:sqlite 会拒绝超出 JavaScript 安全范围的整数。



record\_ids 为每个已提交 ID 保存一行，连同其记录类型。正是它让 ID 空间保持全局统一。

## 一次提交，一个事务



SqliteStorage\.commit\(\) 先在内存中检查文档命令，再执行一个 SQL 事务：读取下一个序列号，检查每个新 ID 和文档命令，写入各行，并推进计数器。如果任何一步抛出异常，事务就会回滚，也不会消耗序列号，见 src/storage/sqlite/storage\.ts。



mintId\(\) 是一个内存计数器，不是写入操作。后来失败的事务所分配的 ID，可能在重新打开后再次分配。这是安全的：只有已提交写入中的 ID 才必须永不复用（不变量5，原书第16页）。

## 文档修订版



文档内容保存在 document\_revisions 中，每个文档在每次改变它的提交中各占一行。一行要么是保存完整值的基值，要么是保存 Chord 操作的增量。读取文档时，SQLite 找到该时点或之前最新的基值，然后应用它之后的增量；这一切在同一个事务中完成，因此并发提交无法替换基值，见 src/storage/sqlite/storage\.ts。



<BookFigure id="D.9.3" :show-caption="false" />

> 可回溯文档保留每个修订版；仅保留当前状态的文档在提交基值时丢弃旧行。图中的行和读取来自 research/capture/extra\-p9/sqlite\-revisions\.txt：两个应用文档在相同的提交中发生变化，seq 为2–7。
> 
> 



是否保留历史取决于文档。可回溯文档保留每一行，因此 document\(2, 4\) 可以从 seq 2 的基值和两个增量重建 seq 4 时的值。其他所有文档都仅保留当前状态：新基值提交时，同一个事务会删除它的旧行。这就是一次轮次运行结束后，每个内置文档都只剩一行基值的原因，见 research/capture/sqlite\-rows\.txt。每次这样的读取都是索引查找；捕获中的查询计划没有显示任何全表扫描，见 research/capture/extra\-p9/sqlite\-revisions\.txt。

## Node 之外



SQLite 核心不需要任何 Node API。来自 @earendil\-works/pi\-durable/storage/sqlite 的 SqliteStorage\.open\(db\) 接受任何实现 SqliteDatabase 的对象。只要有人编写一个小型适配器，同一个后端就能在那里运行，“例如 Bun 或 Cloudflare Durable Objects”，见 README §Storage。



适配器实现的门面接口，来源：src/storage/sqlite/database\.ts：

```ts
export interface SqliteExecutor {
    exec(sql: string): Promise<void>;
    run(sql: string, ...params: SqliteValue[]): Promise<void>;
    get<T extends object>(sql: string, ...params: SqliteValue[]): Promise<T | undefined>;
    all<T extends object>(sql: string, ...params: SqliteValue[]): Promise<T[]>;
}

export interface SqliteDatabase extends SqliteExecutor {
    transaction<T>(callback: (transaction: SqliteExecutor) => Promise<T>): Promise<T>;
    close(): Promise<void>;
}
```

文档注释和 SqliteValue 类型（null、number、bigint、string 或 bytes）已省略。



适配器的规则很少，但很严格。在事务内部，只能使用回调收到的句柄；回调落定后，该句柄就失效。其他工作会一直等到事务完成，因此在回调内部直接调用数据库本身，调用永远不会落定。如果回调拒绝，就回滚并以同一个错误拒绝。如果回滚也失败，则要以另一个错误拒绝，例如 AggregateError，“以免调用方误把回调错误当作已保证回滚”，见 src/storage/sqlite/database\.ts。



模式变更是带版本的迁移，在文件打开时于一个事务中应用。目前只有一个版本，即版本1。较新包写入的文件会被拒绝（“Durable SQLite schema version 2 is newer than supported version 1”）；迁移失败会回滚，数据保持完整，见 src/storage/sqlite/migrations\.ts；test/sqlite\-migrations\.test\.ts。



<aside class="manual-callout callout-warning durable-callout" role="note" data-source-page="147">

<strong>单一进程</strong>

“同一时间，一个存储只由一个进程拥有；不存在跨进程锁”，见 README §Storage。每个 SqliteStorage 都从自己的计数器分配 ID，因此访问同一个文件的两个进程可能分配出同一个 ID。第二次提交随后会失败并使那个 Session 中毒，或者悄无声息地替换另一个进程的任务或提交请求。保证只有一个所有者运行，是宿主的职责（限制与非目标，原书第168页）。

</aside>



<strong>这对你意味着什么：</strong>

- 任何长期存在的内容都使用 SQLite。进程崩溃不会丢失已提交内容；断电可能丢失最新的提交。

- 调试时，用任意 SQLite 客户端打开文件，读取 record 列。

- 在其他运行时上，编写一个 SqliteDatabase 适配器，并针对它运行一致性测试套件。



> 来源：spec §4、§11\.2；README §Storage；src/storage/sqlite/\{storage,node,database,migrations\}\.ts；test/sqlite\-storage\.test\.ts；test/sqlite\-facade\.test\.ts；test/sqlite\-migrations\.test\.ts；research/capture/sqlite\-schema\.sql、sqlite\-rows\.txt、sqlite\-rows\-midrun\.txt；research/capture/extra\-p9/sqlite\-revisions\.txt。
> 
>
