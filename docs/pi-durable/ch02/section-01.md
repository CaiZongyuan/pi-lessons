---
title: "记录与 ID"
---

<div class="section-kicker">PI DURABLE / 2.1 · P. 25</div>

# 记录与 ID

---

五种记录类型和一个编号空间，容纳了 Session 存储的一切；记录之间有两种看起来相似、含义却不同的关联。



<strong>打开一个 Pi Durable 数据库，你只会发现五类记录，它们都从同一个计数器获取编号。</strong>掌握这五种结构，以及一个对话指向另一个对话的两种方式，就能读懂任何存储转储。

## 四张表与文档



<strong>Session 存储四类表记录，外加文档：“表包括 conversations、entries、tasks 和 submissions。”</strong>见 `spec §4`。文档是应用的 JSON 状态，也有一条小型的自身记录。见文档（原书第53页）。每条记录都是一个普通 JSON 对象，在 `src/types.ts` 中声明为 TypeScript 类型。下图展示了全部五种记录，以及每个字段的用途。



<BookFigure id="D.2.1" :show-caption="false" />

> 五种记录类型共享一个 ID 空间，它们的引用是带类型的 ID。字段名来自 `src/types.ts`；卡片标题中的数字是深入介绍各类型的章节号。
> 
> 



记录的变化方式有所不同：

- 对话和条目在创建它们的提交之后就不再变化。见不变量 5，以及不变量（原书第16页）

- 任务和提交请求是整条替换的。每次变化都在同一个 ID 下写入一条完整的新记录。见 `src/types.ts`（`TaskRecord`）

- 文档记录描述一个文档从创建到退役的全过程。其内容另行存储，形式为完整副本和 Chord 操作。见基值与增量（原书第56页）



- <strong>ConversationRecord</strong>：只有 `id`，以及可选的 `parent` 和 `owner`。对话的模型、设置和应用状态不在这条记录中。它们位于 `pi.agent` 等文档中。见内置文档（原书第60页）。

- <strong>EntryRecord</strong>：一个不可变的对话记录事件。它分别为模型（`model`）、应用（`data`）以及上下文控制（`head`、`edits`）设置独立字段。见条目（原书第37页）。

- <strong>TaskRecord</strong>：包含身份（`kind`、`version`、`input`）、所有权（`owner`、`background`）、持久化中止标记，以及一个状态联合类型。见作为状态机的任务（原书第63页）。

- <strong>SubmissionRecord</strong>：由 `type`（`input` 或 `write`）与 `status` 构成的联合类型。输入会经过 `queued`、`placed`、`done` 和 `unanswered` 状态。写入没有 `placed` 状态，只有输入才有 `answer`。见提交请求（原书第84页）。

- <strong>DocumentRecord</strong>：包含 `kind`、可选的文档族 `key`、`scope`，以及对话文档所用的 `history` 和 `fork` 策略。`createdAt` 和 `retiredAt` 是由存储盖章的提交序号。

## ID 是带类型标签的普通数字



每个记录 ID 都是一个普通的 JavaScript 数字。TypeScript 添加了一个称为品牌（brand）的标签，让你无法把 `EntryId` 传给要求 `TaskId` 的地方。品牌只存在于编译期：



<strong>ID、Seq 与根对话</strong> · `src/types.ts`

```ts
export type ConversationId = Id<"conversation">;
export type EntryId = Id<"entry">;
export type TaskId<Result = unknown> = Id<"task", Result>;
export type SubmissionId = Id<"submission">;
export type DocumentId = Id<"document">;

/** 分配给一次原子存储提交的严格递增序号；允许存在间隙。 */
export type Seq = number & { readonly [seqBrand]: "sequence" };

/** 根对话始终使用这个保留 ID。 */
export const ROOT_CONVERSATION_ID = 1 as ConversationId;
```

> 此处省略了泛型 `Id` 类型和两个品牌符号的声明。`TaskId` 还携带其任务的结果类型，因此 `waitForTask()` 能返回带类型的结果。
> 
> 



“ID 和序号在内存、JSON、JSONL 和 SQLite 中始终都是普通数字。”见 `spec §2`。软件包没有导出给数字添加品牌的辅助函数。代码从 JSON、URL 或 UI 消息接收 ID 时，请自行使用 `as EntryId` 进行类型断言，并在该处检查它。

## 所有记录共用一个计数器



<strong>对话、条目、任务、提交请求和文档，都从 Session 范围内的同一个计数器 `Storage.mintId()` 获取 ID。</strong>见 `src/types.ts`。因此，<strong>无论类型如何，任何两条记录都不会拥有相同编号。</strong>SQLite 捕获运行直观展示了这一点：各类型按照提交需要它们的顺序交错出现。



<BookFigure id="D.2.2" :show-caption="false" />

> <strong>除根对话外，每条记录都从同一个计数器取得 ID；</strong>提交则另行编号。ID 1 保留给根对话，因此提交 1 只分配五个文档 ID，即 2–6。每条线将一组 ID 连接到分配它们的提交；17 次提交中有十次没有分配任何 ID。虚线单元格是 `durable_metadata` 中的 `next_id` 和 `next_seq`。ID 和类型来自 `research/capture/sqlite-rows.txt` 的 `record_ids`，提交来自 `research/capture/sqlite-commits.txt`。
> 
> 



一个计数器带来三个事实：

- <strong>ID 在不同对话之间为条目排序</strong>：“条目 ID 在 Session 内全局有效且有序。”见 `spec §2.1`。分叉上限和上下文范围都通过条目 ID 比较来确定，即使条目属于不同对话也一样。见分叉（原书第43页）。

- <strong>根对话 ID 是保留的，不是分配出来的</strong>：`ROOT_CONVERSATION_ID` 为 1，`MemoryStorage` 从 2 开始分配。见 `src/storage/memory.ts`。因此，普通 Session 创建的第一个对话得到的是 ID 2（`run 00`）。Harness 通过 `root()` 按需创建对话 1。

- <strong>回滚的提交也会消耗已分配的 ID</strong>：ID 分配发生在回调内部，早于该批写入到达存储。创建记录的事务方法是异步的，“因为远程存储可能以持久化方式分配全局唯一的数字 ID”。见 `spec §3.3`。在捕获的失败运行中，三次回滚提交领取了 ID 3、4 和 5，下一个成功提交的条目则是 6。见 `research/capture/extra-p23/commit-failures.txt`。保证仅限于：ID“在已提交的写入之后绝不复用”（不变量 5）。



`Seq` 是第二个计数器。它为提交编号，而不是为记录编号：存储会为每个已提交批次分配一个序号，且“在提交之间严格递增；允许存在间隙”。见 `spec §2`。两个计数器推进的速度不同。在捕获中，17 次提交分配了 14 个 ID（2–15）；其中十次提交根本没有分配 ID，只改变了任务状态或 `pi.live`。你会在文档的 `createdAt` 和 `retiredAt`、每次提交发布，以及每条已存储条目上遇到 `Seq`。在条目上，它让文档能够按该条目时刻的状态读取。见可回溯历史（原书第56页）。

## 两种关联：parent 与 owner



`ConversationRecord` 有两种形状相同的可选关联。两者都指向一个对话，但含义不同。“对话的历史父子关系与任务所有权彼此分离。”见 `spec §2`：

|<strong>项目</strong>|<strong>PARENT</strong>|<strong>OWNER</strong>|
|---|---|---|
|结构|`{ conversationId, at: EntryId }`|`{ conversationId, taskId: TaskId }`|
|设置来源|在条目 `at` 处分叉|使用 `{ kind: "task", taskId }` 所有权创建|
|控制内容|继承的条目与历史文档|归因、子树中止、空闲遍历|
|调用者提供|父对话与条目|只提供任务 ID；Session 推导出对话|
|任务结束之后|—|仍保留在记录中|

> 依据 `spec §2` 和 `src/types.ts` 中的字段注释。
> 
> 



<strong>`owner` 关联“不是访问控制能力”。</strong>见 `spec §2`；它记录谁创建了这个对话。<strong>创建时始终要声明所有权，要么是 `{ kind: "ownerless" }`，要么是 `{ kind: "task", taskId }`，Session 会自行填入任务所属的对话。分叉可以同时带有这两种关联：它从一个对话继承历史，同时归另一个对话中的某个任务所有。</strong>



记录还有三种使用相同 ID 的关联。任务的 `owner` 是一个 `TaskId`，由此构成任务树。见所有权与结构化并发（原书第76页）。条目的 `byTaskId` 指出通过提交追加它的任务。提交请求的 `entry` 和 `answer` 分别指出它放入的用户条目，以及回答它的助手条目。捕获中的提交请求 8 最终变为 `{ status: "done", entry: 7, answer: 15 }`。见 `research/capture/sqlite-rows.txt`。



> <strong>这对你意味着什么：</strong>
> 
> - ID 在所有记录类型之间唯一，但数字本身不能说明记录属于哪种类型。将类型与 ID 一起保留，让品牌类型帮助发现混用
> 
> - 预期会有间隙。失败的提交会消耗它已分配的 ID，这是正常现象
> 
> - 用 `parent` 回答“这段历史来自哪里”，用 `owner` 回答“哪个任务创建了它”
> 
>
