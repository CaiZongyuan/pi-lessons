---
title: "存储契约"
---

<div class="section-kicker">PI DURABLE / 9.1 · P. 141</div>

# 存储契约

---

> 存储以全有或全无的方式保存每次提交，并响应查找和分页扫描；其他所有规则都由 Session 负责。
> 
> 

<strong>Session 提交的所有内容最终都会进入存储：SQLite 文件、文本文件目录或内存。提交是一次原子保存：其中的全部内容一起存入，或者全部不存。存储必须为每次提交保持这种性质，并响应精确查找和分页扫描。</strong>这几乎就是 Pi Durable 对存储的全部要求。读完本节，你就能说明存储承诺什么、哪些规则实际归 Session 负责，以及提交失败时该怎么做。

## 小接口，职责窄



任何实现 src/types\.ts 中 Storage 接口的对象都可以成为后端。<strong>包内提供三种：SqliteStorage、JsonlStorage 和 MemoryStorage</strong>（SQLite，原书第144页；JSONL，原书第148页；内存，原书第152页）。你选定一种，交给 Harness。此后只有 Session 会调用它，所有写入都通过提交进行（提交与变更串行队列，原书第29页）。



这种分工是有意设计的。Session 检查语义：记录是否合法、引用、祖先关系以及任务状态转换。存储只检查它能独立检查的内容：批次是否原子、ID 是否唯一、不可变记录是否仍然不可变，以及返回的是否是副本，见 src/types\.ts。存储从不接触文档定义；它原样存储文档编辑，只在响应读取时重放这些编辑。Session 已经让提交一次一个地运行，因此后端不需要自己的锁，见 spec §10。



<BookFigure id="D.9.1" :show-caption="false" />

> Session 存储的所有内容都通过一次调用写入；读取的所有内容都是按键查找或游标扫描。图中为 src/types\.ts 中的八种写入类型和 Storage 方法。所示游标是三个内置后端共同使用的形态。
> 
> 

## 唯一的写入操作：commit



commit\(writes, context\) 原子地存储一批写入，并返回其 Seq，即本次提交的序列号。序列号“严格递增，但可以有间隔”；commit\(\) 一旦完成，之后的每次读取都能看到这批数据，见 spec §10。存储会把序列号标记在它保留的内容上。正因如此，之后才能按某个给定条目写入时的状态读取文档（基值、增量与迁移，原书第56页）。



|<strong>写入类型</strong>|<strong>携带内容</strong>|<strong>存储保留的内容</strong>|
|---|---|---|
|conversation|value: ConversationRecord|一条新的不可变记录|
|entry|value: EntryRecord|一条新的不可变记录及其提交序列号|
|task|value: TaskRecord|完整记录，替换前一条记录|
|submission|value: SubmissionRecord|完整记录，替换前一条记录|
|document\.create|record, content（一个基值）|一个新实例世代，标记 createdAt|
|document\.copy|record, source: \{ id, at \}|一个从来源的已提交值开始的新实例世代|
|document\.change|id, content（基值或增量）|另一个修订版|
|document\.retire|id|该实例世代，标记 retiredAt|

> 来源：src/types\.ts 中的 StorageWrite 联合类型。基值是文档的完整值；增量是在上一修订版之上应用的一批 Chord 操作。
> 
> 

## 提交失败时



只有一种失败是安全的。StorageRejected“表示批次在产生任何持久化效果之前就被拒绝，并保证没有提交”。Session 会回滚并继续运行。commit\(\) 抛出的其他任何错误都会使 Session 中毒：它再也无法知道这批数据是否已经存入，因此拒绝后续提交，见 spec §10。中毒对宿主意味着什么，见“提交失败时”（原书第33页）。

## 读取：按键查找与分页扫描



按键查找返回一条记录，或 undefined。扫描返回一页 \{ items, next? \}；把 next 传回去即可取得下一页。游标是不透明的：只能把它传回同一个存储的同一种扫描，见 spec §10。Harness 每页读取256项，它的每次读取背后都有索引支持，见 spec §10。



|<strong>方法</strong>|<strong>返回内容</strong>|<strong>说明</strong>|
|---|---|---|
|conversation\(id\)|record|精确 ID|
|entry\(id\)|\{ entry, commitSeq \}|任意条目|
|entry\(conversationId, id\)|\{ entry, commitSeq \}|仅当该对话可以看到此条目时返回|
|findLatestHeadMarker\(conversationId, at?\)|entry|at 时刻或之前最新的头指针标记|
|task\(id\), submission\(id\)|record|最新的完整记录|
|submissionByRequest\(conversationId, requestId\)|record|宿主去重（提交请求，原书第84页）|
|findDocument\(address, at\)|DocumentRecord|某个地址上存活的是哪个实例世代|
|document\(id, at\)|StoredProcedure〔原文如此，疑为提取错误，返回类型名待核〕|值及其版本，已重放增量|
|scanConversations\(query\)|page|按所有者筛选；ID 升序|
|scanEntries\(query\)|page|一个 ID 范围，最新的在前，遍历分叉祖先|
|scanTasks\(query\)|page|按 conversation、kind、status、中止标记、background 筛选|
|scanSubmissions\(query\)|page|按 conversation、status 筛选；ID 升序|
|scanDocuments\(query\)|page|一个作用域，可选 kind；ID 升序|
|close\(\)|\-|释放资源；后续每次调用都会失败|

> 每个方法还都接受最后一个参数 context。来源：src/types\.ts 和 spec §10。
> 
> 



document\(id, at\) 是唯一会做计算的读取。它找到该时点或之前最新的基值，依次应用之后的增量，再返回值。在 "current" 时点，已退役的实例世代返回 undefined。请求一个不保留历史的文档的旧时点会失败，而不会猜测（定义文档，原书第50页）。



<strong>这对你意味着什么：</strong>

- 你很少需要直接调用存储。选择一个后端，打开它，再传给 Harness。

- 除 StorageRejected 外，任何提交错误都会使 Session 中毒。关闭它并重新打开存储；重新打开后的状态才是事实。

- 在编写后端吗？请通过一致性测试套件（9\.4节，原书第152页）。

## 后端作者需要了解的细节



所有记录共享 mintId\(\) 提供的同一个 ID 空间；ID 1 是根对话。对于每个文档实例世代，一个批次至多包含一次创建或变更，以及可选的一次退役；版本变化必须使用基值，见 spec §10。commit\(\) 落定后，不得保留参数中的任何内容，并且要返回与内部数据脱离的值，见 spec §4。
