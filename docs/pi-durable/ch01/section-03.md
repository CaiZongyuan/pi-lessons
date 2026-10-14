---
title: "核心规则及其不变量"
---

<div class="section-kicker">PI DURABLE / 1.3 · P. 16</div>

# 核心规则及其不变量

---

一句话定义了整个系统：将一切一起commit，绝不展示未commit的内容。八个不变量确保这句话成立。



<strong>整个设计可以归结为一个理念：commit之前，什么都不算数。commit是一次原子保存：其中所有内容要么一起存储，要么全都不存储。如果屏幕上已经显示出来，崩溃就不能让它消失。</strong>本节阐明这条规则，定义本书后续使用的术语，并解释使该规则成立的八项保证。

## 规则



规范在引入任何类型之前，就用两句话说明了完整设计：

<aside class="manual-callout callout-rule durable-callout" role="note" data-source-page="16">

<strong>核心规则</strong>

<strong>“Session 以原子方式commit不可变条目、完整任务记录，以及由 Chord 跟踪的文档。只有已commit的状态才是可观察的。”</strong>

</aside>




第一句说明commit包含什么：对话记录、任务记录和文档变更，作为一个整体写入。第二句说明其他内容都不可见。<strong>屏幕、等待者、观察订阅以及调度器本身，读取的都是已commit状态，不存在旁路。</strong>见规范前言。<strong>可以把它理解为一扇门：每次变更都经过commit，每个观察者都位于门后。</strong>



<BookFigure id="D.1.3" :show-caption="false" />

> 每个可见变更都经过变更串行队列上的一次commit；副作用只有通过commit才能到达观察者。阶段名称遵循 `spec §4`：从回调到发布，全程持有该队列。
> 
> 

## 术语



规范在 §1 中一次性定义了所有名词。本书后续始终严格按以下含义使用它们。

|术语及定义|
|---|
|<strong>Session（会话）</strong>：拥有一条变更串行队列、对话、条目、任务、commit请求和文档|
|<strong>Conversation（对话）</strong>：一个对话记录作用域。它可以从另一个对话分叉|
|<strong>Entry（条目）</strong>：一条不可变的对话记录|
|<strong>Task（任务）</strong>：附属于一个对话的持久化状态机|
|<strong>Document（文档）</strong>：应用的 JSON 状态，与对话或任务一起保存|
|<strong>Definition（定义）</strong>：为文档命名，并设定其初始值和存储规则的 TypeScript 声明|
|<strong>Source（源）</strong>：已保存文档更新的只读流|
|<strong>Turn（轮次）</strong>：一次助手响应及其发起的工具调用|
|<strong>Run（运行）</strong>：从一个已接纳输入到最终答案之间的一系列轮次。运行处于活动状态时，对话为忙碌状态|

## 八个不变量



接着，`spec §1` 列出了八个“必需的不变量”。每个不变量都封堵了一种特定的故障。下表简要引用这些不变量，后面的段落解释各自带来的保障。

|<strong>编号</strong>|<strong>不变量（SPEC §1）</strong>|<strong>缺少它会怎样</strong>|
|---|---|---|
|1|一次commit在所有记录与文档写入之间具有原子性|工具调用已经存储，却没有相应任务|
|2|文档更新只在其存储commit成功后才会发布|屏幕显示出崩溃后会消失的状态|
|3|所有可见进度都是持久化的；不存在易失性发布路径|流式显示的文本，在重新打开后却从未存在|
|4|外部副作用不在变更事务内部运行|一个缓慢调用阻塞所有对话|
|5|条目和 ID 不可变，且绝不复用|引用指向错误的记录|
|6|回调结束时撤销草稿；值会被复制，且必须是严格 JSON|写入绕过commit|
|7|在操作结算与状态采纳期间始终持有队列；用户回调稍后在队列之外运行|在尚未采纳的状态之上构建下一次commit|
|8|不确定的存储失败会使已打开的 Session 发生致命故障|内存和磁盘悄然分歧|

### 1 · 记录与文档之间的原子性



一次commit对应一次 `Storage.commit(writes)` 调用，要么存储全部写入，要么一条也不存储。见 `src/session/session.ts`。在单轮捕获中，commit 6 写入包含工具调用的助手条目，将生成任务 9 移到 `waiting`，创建工具任务 12，并更新两个文档。如果拆成两次写入，两者之间的崩溃就会留下一个永远不会有任务去执行的工具调用。

### 2 和 3 · 存储之后才能发布



Session 只有在 `Storage.commit()` 返回且新修订已被采纳之后，才会发布commit。不变量 3 排除了另一条路径：没有commit，就没有任何显示内容的办法。因此，部分回答和工具输出也会commit，并由 `settings.progress` 进行节流。其中每次commit都是一次存储写入；这就是确保屏幕永远不会显示任何可能被崩溃夺走的内容所付出的代价。见 `src/harness/generation.ts`（`streamResponse`）。

### 4 · 副作用留在队列之外



“外部模型、进程、工具、网络和人工副作用都在其外部运行。”见 `spec §4`。一个 Harness 的所有对话共享一条变更串行队列，因此在commit内部等待模型调用，会阻塞其他所有commit，直到该调用返回。更糟的是，commit的内容会依赖一个无法撤销的副作用。工具任务展示了这一模式：commit意图，在队列之外运行 `execute()`，然后commit结果。见副作用三明治（原书第70页）。

### 5 · 条目不可变，ID 永不复用



所有记录类型共享同一个 ID 空间。在 SQLite 捕获中，对话 1、文档 2 到 6、条目 7、commit请求 8 和任务 9，都来自同一个计数器。见 `research/capture/sqlite-rows.txt`（`record_ids`）。记录通过 ID 互相指向：工具任务 12 的输入为 `{"assistant": 11, "callId": "call-1"}`，commit请求 8 的答案是条目 15。如果 ID 可以复用，或条目可以改写，这些指针的含义就会悄然改变。即便是一次故障commit已经领取的 ID，也仍然视为已使用。见 `research/capture/NOTES.md §6`。

### 6 · 草稿与其回调同时失效



在commit内部，`tx.doc()` 返回可变草稿。回调结束时，Session 会“同步准备或中止每个打开的变更”，随后撤销草稿。有一个测试在commit结束后仍保留草稿，并检查此时读取或写入它都会抛出异常。见 `test/session-documents.test.ts` 中的“revokes escaped drafts”测试。没有这项保障，一个游离引用就可能在任何commit之外修改文档，从而破坏规则。

### 7 · 队列覆盖存储与采纳阶段



队列会一直保持占用，直到存储操作结算且新修订被采纳。因此，下一次commit总是从上一次已存储的状态开始。commit观察者在队列上运行，但仅用于捕获不可变值。你的观察订阅回调和文档状态回调稍后才会在队列之外运行，因此缓慢的 UI 无法阻塞harness。见commit与变更串行队列（原书第29页）。

### 8 · 不确定的失败会使 Session 中毒



如果一次存储错误可能已经写入了一些内容，内存就无法知道磁盘究竟保存了什么。此时，Session 会拒绝之后的每次调用，并给出：“Session is poisoned by a failed commit after storage admission; reopen it”（Session 在存储接纳之后因commit失败而中毒；请重新打开它）。见 `src/session/session.ts`。只有 `StorageRejected` 保证完全没有写入，也只有它允许 Session 继续工作。准备阶段的失败，例如草稿含有非 JSON 值，发生在存储看到这批写入之前，因此会正常回滚。见commit失败时会怎样（原书第33页）。



> <strong>这对你意味着什么：</strong>
> 
> - 对任何设计都问一个问题：你展示或据以行动的状态，是否已经commit？如果没有，它就还不存在
> 
> - 将相关内容放在一次commit中修改，这样崩溃永远无法将它们拆开
> 
> - 绝不要在commit回调内部调用模型、工具或网络
> 
> - 如果存储失败且可能已经写入，请关闭并重新打开，不要重试
> 
>
