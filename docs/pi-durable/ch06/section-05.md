---
title: "压缩"
---

<div class="section-kicker">PI DURABLE / 6.5 · P. 97</div>

# 压缩

---

> 压缩用一段摘要替换模型所见内容中最旧的部分；不会删除任何内容，而截断位置推进得最远的摘要胜出。
> 
> 

长对话会超出模型的上下文窗口。压缩要求模型总结最旧的部分，然后用摘要代替这部分内容发送。完整历史仍保留在存储中；缩短的只是模型看到的内容。读完本节，你就能设置 token 预算，判断哪些压缩会让运行等待，并预测两个相互竞争的摘要哪一个会胜出。

## 压缩会写入什么



一次压缩是一个 `pi.compaction` 任务。它选择上下文的一段前缀，请模型对其总结，并添加一个摘要条目。条目的 head 指向第一个逐字保留的条目，因此模型的上下文现在从摘要开始，再从那里继续（头指针，原书第46页）。在这份采集记录中，三个问题回答完毕后执行了 `compact()`，而此时第四个回答正在写入。



摘要条目 25，来源：`research/capture/extra-p6/compaction.txt`

```json
{
    "kind": "pi.compaction", "id": 25, "head": 14,
    "model": [
    {
    "role": "user",
    "content": [
    { "type": "text", "text": "The conversation history before this point was compacted into the following summary:\n\n<summary>\n## Goal\nPlan a week in Lisbon.\n</summary>" }],
    ...
    }],
    "data": { "reason": "manual" },
    "byTaskId": 21
}
```

> 摘要文本在原书中折行为三行；timestamp 和 conversationId 已省略。对话当时忙碌，因此摘要以 write 提交请求 `compaction:22` 的形式在收件箱中等待，由正在运行的 generation，即任务 21，将它放入对话记录。
> 
> 

## 三种启动方式



|<strong>由谁启动</strong>|<strong>reason</strong>|<strong>运行会等待吗</strong>|<strong>摘要如何进入对话记录</strong>|
|---|---|---|---|
|你调用 `Conversation.compact()`|`manual`|否|作为 write 提交请求|
|generation，达到后台预算|`threshold`|否|作为 write 提交请求|
|generation，达到阻塞预算|`threshold`|是|直接追加|
|generation，上下文过长|`overflow`|是|直接追加|

> 规范 §8\.7；`src/harness/compaction.ts`。
> 
> 



最后一列是一条安全规则。运行中的 generation 不能在执行期间被改变其对话记录。阻塞压缩可以直接追加，因为等待它的正是它所属的 generation。其他摘要都像普通 write 一样提交，在下一个边界进入对话记录；如果对话空闲，则立即进入（提交请求，原书第84页）。非阻塞压缩绝不会让对话变为忙碌；执行期间，它显示在 `pi.live.compactions` 中。

## generation 何时压缩



在 prepare 中，generation 估算即将发送的请求大小，并与 `settings.compaction` 中的两个预算比较。



<BookFigure id="D.6.6" :show-caption="false" />

> 两个预算决定 generation 何时压缩；`keepRecentTokens` 决定截断位置。数字来自示例 25，使用一个上下文窗口为 3000 token 的测试模型。默认值为 reserveTokens 16384、backgroundTokens 32768、keepRecentTokens 20000。下方一行是示意图：从后向前计数时落在工具结果中，所以截断点移到下一条消息，最终保留不到 400 token。
> 
> 



- 阻塞：超过 `contextWindow − reserveTokens` 时，generation 启动压缩并等待结束，然后再次 prepare；无论压缩结果如何，都会发送请求

- 后台：超过上述界线再减去 backgroundTokens 的阈值时，generation 在后台启动压缩，不等待就发送请求。`backgroundTokens: 0` 会关闭此行为

    

截断位置通过从最新条目向前计数来选择，直到保留 keepRecentTokens 为止。随后，它会落在下一条用户或助手消息上，绝不会落在工具结果上，因此保留的助手消息也会保留其工具结果。如果整个上下文小于 keepRecentTokens，就不做任何压缩。



过长的上下文有一次补救机会。如果提供商因请求过长而拒绝，generation 会压缩，并再次准备同一次 attempt。一个 generation 最多压缩一次，因此第二次溢出会以 `model_error` 使运行失败。运行记录 25 展示了这一点：它的最后一个轮次先因达到阻塞预算而压缩，然后遇到溢出并失败。

## 摘要相互竞争时



压缩之间从不协调；多个压缩可以同时执行。决定胜者的只有收件箱的过时头指针规则（原书第84页）。如果摘要的截断点比当前上下文起点更早，它会结算为 stale。如果截断点位于当前起点或其后，就会被放入，无论何时启动。



<BookFigure id="D.6.7" :show-caption="false" />

> 压缩之间从不协调；截断点早于当前上下文起点的摘要会过时。这是规范 §6 的详细示例。阴影线标出各摘要替换的部分；虚线表示 A 进入对话记录后的上下文起点。
> 
> 

## 细节



- 摘要请求：没有工具，使用将工具结果截短到 2000 个字符的对话记录，以及你传给 `compact()` 的任何额外指令。只有正常停止且带有文本的结果才算摘要。可重试错误按 settings 中的 retry 策略重试。`beforeCompact` 钩子可以拒绝压缩，也可以提供自己的摘要（钩子，原书第109页）

- 中止：`Conversation.abort()`（Esc 键）会中止手动压缩。后台压缩会继续，除非传入 `{ background: true }` 或调用 `abortTask()`。阻塞压缩会随它所属的 generation 一起停止

- 压缩期间编辑：压缩执行期间放入的应用编辑或 head，可能在摘要进入对话记录时丢失或被撤销，见规范 §12



> <strong>这对你意味着什么：</strong>
> 
> - 默认值适用于大窗口。对于小窗口，应让 keepRecentTokens 远低于阻塞界线，否则还没压缩任何内容，上下文就可能溢出
> 
> - 随时都可以调用 `compact()`；它绝不会阻塞运行
> 
> - 应在压缩之前放入应用编辑，不要在压缩期间进行
> 
> - 每次摘要尝试都要付费，即使最终变为 stale 也不例外
> 
> 



> 来源：规范 §6、§8\.3、§8\.7、§12；`src/harness/compaction.ts`；`src/harness/generation.ts`；`src/harness/live.ts`（`CompactionStatus`）；`src/harness/agent.ts`（`DEFAULT_COMPACTION_POLICY`）；README §Compaction；`docs/pico-v5-handoff.md` §20；`test/harness-compaction.test.ts`；示例 25；运行记录 25；`research/capture/extra-p6/compaction.txt`
> 
>
