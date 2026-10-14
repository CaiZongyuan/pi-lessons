---
title: "条目与内置种类"
---

<div class="section-kicker">PI DURABLE / 3.1 · P. 37</div>

# 条目与内置种类

---

> 条目是对话记录中不可变的一行，分别用不同字段保存模型读取的内容、代码读取的内容，以及模型上下文的起点。
> 
> 

<strong>聊天记录是一系列已发生的事情：一个问题、一个回答、一个工具结果。Pi Durable 将每件事存为一个条目，此后绝不修改。</strong>本节结束后，你就能读懂任何已存储的条目，判断是谁写入的，并添加自己的条目种类。

## 一条记录，三种读者



一个对话 conversation 对应一份对话记录  transcript，条目  entry 就是其中“一条不可变的对话记录”（spec §1）。系统的三个不同部分都会读取条目，但各自读取不同字段：

- 模型读取 `model`：该条目为下一次请求添加的消息

- 你的代码读取 `data`：模型永远看不到的 JSON

- 上下文构建逻辑读取 `head` 和 `edits`：模型上下文从哪里开始，以及隐藏或替换哪些早先条目。已存储的内容不会被重写



<BookFigure id="D.3.1" :show-caption="false" />

> 条目将模型看到的内容、应用看到的内容和上下文的起点彼此分开。这是 `research/capture/context.txt` 中的条目 20，由一次手动压缩写入；摘要文本仅保留了前三个词。
> 
> 



<strong>结构说明：</strong>

1. `kind`：这里是内置种类；你自己的种类可以是任意字符串

2. `model`：该条目添加到上下文中的 `Message[]`；缺省时不添加消息

3. `data`：供应用使用的 JSON；永远不会发送给模型

4. `id` · `conversationId`：由 Session 在追加条目时分配

5. `head`：上下文先放本条目，再放 \#18 起的条目；条目 7–15 仍然保留在存储中

6. `byTaskId`：压缩任务 19；宿主写入的条目没有此字段



|<strong>字段</strong>|<strong>保存的内容</strong>|<strong>设置方</strong>|
|---|---|---|
|`id`|一个 `EntryId`，在整个 Session 内有序|Session|
|`conversationId`|所属对话|Session|
|`kind`|表明条目种类的字符串|写入方|
|`model?`|给模型的消息；仅用于显示或记账时缺省|写入方|
|`data?`|供视图、扩展和你的代码使用的 JSON|写入方|
|`head?`|从现在起模型上下文的第一个条目|写入方；`"self"` 表示本条目|
|`edits?`|仅在上下文中隐藏或替换早先条目|写入方|
|`byTaskId?`|在其提交中追加该条目的任务|Session|

> `EntryRecord` 的字段，改述自 `src/types.ts` 中的字段注释。
> 
> 



条目是在一次提交中写入的。提交是原子保存：其中所有内容要么一并存储，要么全部不存储。你绝不需要设置 `id`、`conversationId` 或 `byTaskId`。`tx.appendEntry()` 会填入这些字段，并将 `head: "self"` 转成新分配的 ID。因此，`byTaskId` 能可靠地记录条目由哪个任务写入。通过宿主的 `Conversation.commit()` 追加的条目没有这个字段。

## 内置种类



Harness 会写入六种条目。每一种都作为带类型的 `Entry` 令牌导出（`src/entries.ts`）。其中只有两种携带 `data`（spec §8\.1）。

|<strong>种类</strong>|<strong>`model`</strong>|<strong>`data`</strong>|<strong>写入方</strong>|
|---|---|---|---|
|`pi.user`|一条用户消息|—|提交请求|
|`pi.assistant`|一条助手消息，停止原因不限|—|生成任务|
|`pi.system`|一条表示变更的系统消息|—|生成任务，在发送请求之前|
|`pi.tool-result`|一条工具结果消息|`{ diagnostics }`|工具任务|
|`pi.reset`|无消息，或将交接文本作为用户消息|—|`reset()`、工具的交接|
|`pi.compaction`|将摘要作为用户消息|`{ reason }`|压缩任务|

> 来源：spec §8\.1 和 `src/entries.ts`。这些令牌分别为 `UserEntry`、`AssistantEntry`、`SystemEntry`、`ToolResultEntry`、`ResetEntry` 和 `CompactionEntry`。
> 
> 



`pi.assistant` 记录每一次响应，包括失败：“回答、带有错误文本和用量的失败尝试，以及转换后停止原因为 `aborted` 的部分响应”（spec §8\.1）。对话记录不会隐去任何内容，因此花掉的每个 token 都清晰可见。随后构建上下文时，会将失败的响应排除在后续请求之外（上下文推导，原书第40页）。

## 系统条目记录变更，而不是头部



`pi.system` 条目不保存完整提示词，而是在对话记录的某个位置保存提示词和工具列表的变更。下面是一次采集运行中的首个系统条目：



条目 10，对话中的第一个 `pi.system`；来源：`research/capture/sqlite-rows.txt`

```json
{
    "kind": "pi.system",
    "model": [
        {
            "role": "system",
            "content": "",
            "sections": { "preamble": "You are a terse assistant." },
            "toolsAdded": [ { "name": "count", "description": "Count from 1 to n, ..., ... } ],
            "timestamp": 1791211974788
        }
    ],
    "id": 10, "conversationId": 1, "byTaskId": 9m
}
```

> 已调整顺序并合并排版；工具的描述和参数模式经过截断。
> 
> 



每个命名区段都会被添加或替换，`null` 则用于移除区段。工具也以相同方式移除和添加。按顺序重放每个系统条目，就能得到当前的提示词和工具集（spec §2）。Harness 只会在提示词或工具实际变化时写入新的 `pi.system` 条目，因此一个稳定的对话只会有一个这样的条目。完整说明见系统提示词（原书第115页）。

## 自定义种类



任何非空字符串都是有效的 `kind`。`defineEntry()` 将它变成带类型的令牌；追加和读取时，令牌为 `data` 提供类型：



带类型的应用条目；来源：`src/entries.ts` · `src/types.ts`

```ts
const NoteEntry = defineEntry<{ text: string }>("app.note");

// 没有 `model`，因此模型永远看不到它。
await root.commit(
    (tx) => tx.appendEntry(NoteEntry, root.id, { data: { text: "user pinned b.md" } }),
    context,
);

// 条目 `id` 不存在或种类不符时，返回 undefined。
const note = await harness.commit((tx) => tx.entry(NoteEntry, id), context);
```

> `app.note` 是本书使用的示例种类。令牌的 `is()` 类型守卫可根据种类收窄任意条目的类型。
> 
> 



按读者选择字段。模型必须看到的内容放入 `model`；只有代码需要的内容放入 `data`。只带 `edits` 的条目很常见：采集记录中的 `app.correction` 会在上下文中替换一个早先的回答，而不添加自己的消息（`research/capture/context.txt`，阶段 5）。



> <strong>这对你意味着什么：</strong>
> 
> - 将面向模型的文本放入 `model`，其余内容放入 `data`
> 
> - 永远不要修改条目；应追加一个带 `edits` 的新条目
> 
> - 调试时，通过 `byTaskId` 查看哪个任务写入了条目
> 
> - 运行处于活动状态时，要通过写入提交请求添加条目，不要直接追加（spec §12；提交请求，原书第84页）
> 
>
