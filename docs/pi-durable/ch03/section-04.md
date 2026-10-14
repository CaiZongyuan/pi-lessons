---
title: "重置、交接与头指针"
---

<div class="section-kicker">PI DURABLE / 3.4 · P. 46</div>

# 重置、交接与头指针

---

> 头指针将模型上下文的起点向前移动，而不删除任何内容；重置、交接和压缩都采用这一机制。
> 
> 

有时，模型应该忘掉一些内容。<strong>上下文窗口已经用满，或用户希望在同一任务上重新开始。Pi Durable 绝不删除旧消息；它只是告诉模型从后面的位置开始读取。</strong>本节结束后，你就能开启一个全新上下文，可以附带交接说明，也可以不带，并能预测模型下一步看到什么。

## 什么是头指针



<strong>头指针是一个条目字段，含义是“模型上下文从这里开始”</strong>（`src/types.ts`）。<strong>带有该字段的条目称为头指针标记。只有最新的标记有效，上下文推导会把这个标记条目放到最前面</strong>（规则 1、2 和 5，原书第40页）。<strong>更早的条目仍留在存储中，只是不再发送</strong>（spec §2\.1）。



头指针有两种指向方式：

- 向后指向保留的条目：压缩摘要的头指针指向它保留的第一个条目。上下文变成“摘要，然后是保留的尾部”（压缩，原书第97页）

- 指向自身：重置条目的头指针指向它自己。上下文变成重置条目本身，以及此后出现的所有内容

## `reset()` 与交接



`Conversation.reset(handoff, context)` 开启一个新上下文。它会提交一个 `head: "self"` 的 `pi.reset` 条目。如果传入交接文本，该条目会将其作为用户消息携带（spec §2\.2）：

- `reset(text)`：模型的上下文变成这一条消息。下图阶段 4 中的文本为：`"We were doing arithmetic for Ada. Continue from 5+5."`

- `reset(undefined)`：条目不含消息，因此下一次输入到来之前，上下文为空（`research/capture/extra-p23/heads.txt`）



重置与其他写入一样进入队列。如果对话空闲，它立即落入对话；如果运行处于活动状态，它会等待下一个边界，也就是模型步骤和工具步骤之间的安全点（提交请求与收件箱，原书第84页）。若在工具轮次期间落入对话，就会结束运行，并将该运行的输入报告为未回答，原因为 `reset`。若在回答之后落入，则不会改变已经给出的回答（spec §6）。`reset()` 在提交请求提交后即返回，而不是等到条目真正落入对话；请观察对话来确认。



下图跟踪了一个采集对话的五个阶段：三个问题、一次压缩、又一个轮次、一次重置，以及最后一个带修正的轮次。

<BookFigure id="D.3.4" :show-caption="false" />

> 头指针将上下文起点向前移动；每个条目都仍被存储。来源为 `research/capture/context.txt` 的阶段 1–5；其中的 `context().entries` 行直接复制自该文件。
> 
> 



工具也可以请求相同操作。如果其结果的 `control` 携带 `handoff: string`，那么工具轮次结束时，运行会以一个包含该文本的 `pi.reset` 条目结束，“与 `reset(handoff)` 写入的内容完全相同”（spec §7\.3）。如果多个工具都提出交接请求，则按调用顺序，以最后一个为准。

## 过时的头指针写入



头指针只能向前移动。若一次头指针写入指向当前起点之前，就会重新带回已被切掉的历史，因此系统会以过时为由拒绝它：提交请求以未回答状态结束，原因为 `stale`，并且不写入任何内容（spec §6）。重置的头指针指向自身，因此永远不会过时。



在 \#9 处重置后的两次头指针写入；来源：`research/capture/extra-p23/heads.txt`

```bash
context entries: [#9 pi.reset, #11 pi.user]

write with head=#8 (before the start): status "unanswered", reason "stale"
write with head=#11 (inside the range): status "done", entry 13
context entries now: [#13 app.summary head=11, #11 pi.user]

stored entries (newest first), nothing deleted:
    [#15 pi.reset, #13 app.summary, #11 pi.user, #9 pi.reset, #8 pi.assistant, #7 pi.user]
```

> 同样的规则也用于裁决相互竞争的压缩：会将起点向后移动的摘要以 `stale` 结束（压缩，原书第97页）。
> 
> 

## 头指针绝不会做什么



- 删除内容：上面的每个条目仍被存储，`entries()` 仍会返回它们。你仍然可以在旧条目处分叉

- 更改提供商 ID：重置和压缩会保留对话的 `pi.provider` 会话 ID（spec §2\.2）

- 丢失系统提示词：头指针变动之后，下一次请求会写入一个全新的完整 `pi.system` 条目（系统提示词，原书第115页）



> <strong>这对你意味着什么：</strong>
> 
> - 使用 `reset(text)` 重新开始，同时告诉模型上次进行到了哪里
> 
> - 通过写入提交请求写入自定义头指针条目，而不是直接调用 `tx.appendEntry()`。只有提交请求路径会检查头指针是否过时，直接写入可能让已挂载的视图落后于当前状态（spec §12）
> 
> - 如果写入以 `stale` 结束，说明更新的头指针已经越过它的目标。请根据当前上下文重新计算
> 
> 



> 来源：spec §2\.1、§2\.2（`reset`、`pi.provider`）、§6、§7\.3、§7\.4、§8\.1、§12；`src/types.ts`（`EntryRecord.head`）；`src/harness/harness.ts`（`reset`）；`src/harness/submissions.ts`；`src/harness/inbox.ts`；`src/harness/generation.ts`；`src/harness/types.ts`（`ToolControl`）；`research/capture/context.txt`；`research/capture/extra-p23/heads.txt`。
> 
>
