---
title: "智能体事件"
---

<div class="section-kicker">PI DURABLE / 8.3 · P. 133</div>

# 智能体事件

---

> 一个实验性适配器把每次提交转换为一批编码智能体事件：快照是状态，每一批事件都是对该状态的一次变更。
> 
> 

你可能已经有读取编码智能体事件的代码，例如读取 message\_start 和 tool\_execution\_update 的 JSON 日志、CLI 或 UI。watchEvents\(\) 会从 Pi Durable 的提交中生成这些事件。读完本节，你就能使用这个事件流、从增量中重建流式文本，并了解它可能跳过哪些步骤。

## 附着



watchEvents\(harness, conversationId, context\) 从包的根入口导出，并被标为实验性：它的协议可能变化。它返回一个流，包含 snapshot（起始状态）、start\(listener\)、stop\(\) 和 closed。它遵守8\.2节（原书第129页）的监听规则：每次交付一批事件，提交绝不会等待，见 src/harness/events\.ts。



快照包含对话的条目、正在运行的工具、压缩、收件箱、智能体和用量。运行尚未结束时，还会包含 run 和 generation、正在流式输出的消息或重试等待，见 research/capture/agent\-events\.txt。



只有在使事件成立的那次提交完成之后，事件才会被发出，见 spec §9\.4。事件流只覆盖一段对话。子智能体的工作只会以父级工具调用的形式出现；若要查看内部情况，需要为子对话附着第二个事件流（子智能体，原书第121页）。

## 一次提交，一批事件



每次提交至多产生一批事件。下表展示了捕获中的一个轮次：模型思考，调用 count \{n: 3\}，然后回答。一次生成就是一次模型调用，以任务形式运行。

|<strong>提交</strong>|<strong>发生了什么变化</strong>|<strong>事件批次</strong>|
|---|---|---|
|1|用户消息已提交；运行开始|message\_start, message\_end, submission, run\_start, turn\_start|
|2|系统提示词条目|message\_start, message\_end|
|3|生成的第1次尝试开始|无|
|4|第一个流式部分内容|message\_start|
|5\-7|思考和文本流入|每次各有一个 message\_update|
|8|助手消息已提交；工具调用进入队列|message\_end, usage\_changed|
|9|工具开始运行|tool\_execution\_start|
|10\-13|工具输出和详情|每次各有一个 tool\_execution\_update|
|14|工具完成；其结果条目已提交|tool\_execution\_end, message\_start, message\_end|
|15|下一次生成替换第一次生成|turn\_end, turn\_start|
|16|第1次尝试开始|无|
|17\-19|回答流入|message\_start, message\_update ×2|
|20|回答已提交；运行结束|message\_end, turn\_end, run\_end, submission, usage\_changed|

> 来源：research/capture/watch\-ops\.txt（20帧）和 agent\-events\.txt（18批事件），它们来自 test/capture/view\-ops\.ts 的同一次运行。
> 
> 



提交3和16没有产生事件批次：开始一次尝试，并不会改变事件所描述的任何内容。工具开始事件要等到提交9，即调用实际运行时才出现。在提交15中，一次生成结束，下一次生成开始，因此轮次结束和轮次开始共处同一批次。



批次内部的顺序固定，并与编码智能体保持一致。先进度，再新条目，再结束，最后才是开始。因此，工具结束事件紧挨着其结果消息之前出现；一次已完成的运行会在下一次运行开始之前结束。



<BookFigure id="D.8.5" :show-caption="false" />

> 同一批次中，先进度，再条目，再结束，最后是开始。右侧：一次提交对某次运行给出回答，并把排队的后续输入作为下一次运行启动；图中是测试对此预期的事件批次（test/harness\-events\.test\.ts）。
> 
> 

## 每个事件的含义



|<strong>事件</strong>|<strong>在提交执行以下操作时发出</strong>|
|---|---|
|run\_start/run\_end|开始或结束一次运行。加入现有运行的引导输入并不是一次新的运行|
|turn\_start/turn\_end|把运行推进到一次新的生成／提交某次生成的结果|
|message\_start/message\_end|提交某次尝试的第一个流式部分内容，或提交一个此前没有流式部分内容的消息条目／追加一个包含模型消息的条目|
|message\_update|改变流式部分内容；携带 usage 和 changes|
|entry\_appended|追加一个不含模型消息的条目，例如普通的 pi\.reset|
|tool\_execution\_\*|启动一个工具调用／改变其 output、details 或 diagnostics／完成它，或随所属运行一起丢弃它|
|submission|写入属于这段对话的提交请求记录|
|inbox\_update, agent\_changed, usage\_changed|改变相应文档|
|auto\_retry\_start/\_end, deferred\_poll|开始或结束一次重试等待；安排或调整一次延迟轮询|
|task\_failed|将对话中的某个任务以 faulted 或 orphaned 状态完成|
|compaction\_start/\_end|开始或完成一次压缩|

> 来源：spec §9\.4；src/harness/events\.ts。
> 
> 



每个 message\_start 都会得到一个 message\_end，即使运行在流式输出途中被中止也是如此。只有已有内容时，部分内容才会被提交；每条清除它的内置路径也都会追加已结束的条目。崩溃前后同样如此：重新打开时，生成逻辑把残留的部分内容转成一个已中止的 pi\.assistant 条目（生成，原书第91页），事件流会据此结束消息，见 spec §9\.4；test/harness\-events\.test\.ts。

## 交付增量，而非完整值



message\_update 只携带流式消息中发生变化的内容。追加文本以 text\_delta 或 thinking\_delta 到达，追加的工具参数以 toolcall\_delta 到达，新内容块以 \*\_start 到达。其他任何变化都会重新发送整个内容块或整条消息。部分内容经历十次提交，产生的是十个小事件，而不是十份副本，见 spec §9\.4。



提交6的事件批次，来源：research/capture/agent\-events\.txt：

```json
{
    "type": "message_update",
    "usage": { "input": 56, "output": 19, ... },
    "changes": [
        { "type": "text_start", "contentIndex": 1, "block": { "type": "text", "text": "" } },
        { "type": "thinking_delta", "contentIndex": 0, "delta": "use the tool." }
    ]
}
```

> 两个视图操作按顺序变成两个 changes。usage 字段有所省略。
> 
> 



工具输出的处理方式相同。输出被替换时，tool\_execution\_update\.output 是 \{ set \}；从开头裁去旧文本并追加新文本时，它是 \{ trimStart?, append? \}。捕获中，第一行对应 `{"set":"1\n"}`，之后对应 `{"append":"2\n"}`。示例21这样重建输出：



应用输出更新，来源：test/examples/21\-late\-join\.ts：

```ts
let output = stream.snapshot.tools[0]?.output ?? "";
stream.start(async (events) => {
    for (const event of events) {
        if (event.type === "tool_execution_update" && event.output !== undefined) {
            output = "set" in event.output
                ? event.output.set
                : output.slice(event.output.trimStart ?? 0) + (event.output.append ?? "");
        }
    }
});
```

> 此代码从示例中裁剪而来。被删除的 details 以 null 到达，例如可安全重放的工具重新启动时（6\.4节，原书第94页）。
> 
> 

## 落后时会怎样



与监听一样，事件流最多保留100个尚未交付的批次。溢出时，它们会被一个最新视图的快照替换，其中包括正在流式输出的部分内容，见 test/harness\-events\.test\.ts。
