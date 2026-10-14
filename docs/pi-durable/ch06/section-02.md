---
title: "运行控制与实时文档"
---

<div class="section-kicker">PI DURABLE / 6.2 · P. 88</div>

# 运行控制与实时文档

---

> 一个小文档就能表明对话是否忙碌，并展示正在形成的回答和工具输出；崩溃只会丢失上一次成功提交之后的进度。这段间隔可能超过配置的时间间隔。
> 
> 

<strong>智能体工作时，有两个问题很重要：对话忙碌吗？屏幕此刻该展示什么，是写到一半的回答，还是工具不断滚动的输出？两个答案都在同一个文档 `pi.live` 中。和其他内容一样，它也会提交，因此，较晚连接的界面或重启后的进程看到的是同一幅状态图景。</strong>读完本节，你就能读取 `pi.live`，判断对话是否忙碌、用户看到什么，以及崩溃会丢失什么。

## 结构



`pi.live` 是内置文档，每个对话各有一个。每个字段都是可选的；空闲对话的值为 `{}`。



`LiveState`，简化版本，来源：`src/harness/live.ts`

```ts
type LiveState = {
    run?: { taskId: TaskId; inputs: SubmissionId[] }; // 忙碌时存在
    generation?: { // 正在进行的模型调用
        attempt: number;
        message?: AssistantMessage; // 目前为止的回答
        retry?: { at: number; error: string }; // 等待重试
        deferred?: { pollAt: number }; // 提供商稍后回答
    };
    tools?: ToolSlot[]; // 本轮工具调用
    compactions?: CompactionStatus[]; // 参见 6.5
};
```

> 存储的 message 是 `AssistantMessage` 的 JSON 形式。每个 `ToolSlot` 展示一次调用：它的 `callId`、name、值为 `pending`、`running` 或 `done` 的 status、目前为止的 output，以及完成后的结果 entry。
> 
> 

## 运行控制：忙碌标记



<strong>run 就是锁。只要 run 存在，对话就忙碌；`submit()` 不检查其他任何内容</strong>（提交请求，原书第84页）。<strong>inputs 列出本次运行将回答的提交请求。taskId 指定负责回答这些请求的 generation，也就是正在进行当前模型调用的任务</strong>（生成，原书第91页）。



<strong>一次运行是一串 generation，每个轮次一个。轮次之间会交接这把锁，绝不释放：旧 generation 在同一次提交中创建下一个 generation，并改写 taskId。此时进入的 steer 会追加到 inputs 中。运行结束时，一次提交会结算所有列出的 input，并删除 run、generation 和 tools。</strong>



<BookFigure id="D.6.3" :show-caption="false" />

> `pi.live` 在整个运行期间保存运行控制信息，而实时进度只在有工作执行时存在。示例包含一次输入、一次打印五行内容的 count 工具调用和一次回答；时间来自 `research/capture/extra-p6/live-run.txt`。（1）提交时设置 run；（2）模型请求工具，于是 generation 让位于 tools；（3）这一轮把 run 交给 generation 14；（4）回答完成后清除一切。
> 
> 

## 实时进度及其代价



generation 和 tools 的存在，是为了让界面展示正在形成的回答和工具输出。它们是普通的已提交状态，像其他文档一样发布（对话视图，原书第129页）。<strong>每次更新都是一次提交，因此更新会受到节流限制。</strong>`settings.progress` 有两个时间间隔，默认均为 100 ms：

- `partialIntervalMs`：流式回答多久提交一次。在采集记录中，第一个部分回答在请求开始后 103 ms 提交

- `outputIntervalMs`：工具输出多久提交一次。一段静默之后的第一行会立即提交；之后的写入至少间隔一个时间间隔，输出较大时还会更久



使用远程存储的宿主可以调大这两个间隔，让进度以更大的步幅显示。文档会保持小巧：只要没有工作正在执行，就会把它存储为完整快照，因此它的变更历史绝不会超过一次模型调用或一轮工具调用的范围（基值与增量，原书第56页）。

## 崩溃留下什么



崩溃会丢失尚未提交的回答文本或工具输出。自上一次成功提交以来的间隔可能超过配置的进度间隔。在崩溃采集记录中，进程在最后一次输出提交约 50 ms 后被终止，因此 deploy 槽位仍保存着它打印过的全部六行。



对话 1 在 `SIGKILL` 之后的 `pi.live`，来源：`research/capture/crash-reopen-tasks.txt`

```json
{
    "run": { "taskId": 15, "inputs": [14] },
    "tools": [
    {
    "callId": "deploy-1", "name": "deploy", "taskId": 22,
    "status": "running",
    "output": "deploy site: step 1/10 (pid 98319)\n ... step 6/10 (pid 98319)\n"
    }
    ]
}
```

> 输出的第 2–5 行已省略。对话仍然忙碌；在恢复流程确定发生了什么之前，没有任何内容回答 input 14。
> 
> 



恢复会将这些进度转化为对话记录，绝不会悄悄抹去它们。已经提交的部分回答会变为一个 aborted 助手条目，因此对话记录和界面保留了它已经开始说出的内容。之后的模型请求会排除这个被中止的回答。正在运行的工具，其已提交输出会成为 interrupted 结果的正文；如果进行安全重跑，则会先清除输出（工具调用与重放，原书第94页）。

## 细节：各字段何时设置和清除



|<strong>字段</strong>|<strong>何时设置</strong>|<strong>何时清除</strong>|
|---|---|---|
|`run`|运行开始|运行结束，无论经由哪条路径|
|`generation`|模型请求开始、等待重试或等待延迟回答|响应处理完毕，或运行结束|
|`tools`|模型请求工具|本轮结束，或运行结束|
|`compactions`|压缩开始|压缩结束|



规范 §8\.2；`src/harness/live.ts`、`generation.ts`、`tool.ts`、`compaction.ts`。如果调度器放弃某个运行任务（`faulted` 或 `orphaned`，参见中止、故障与孤儿任务，原书第80页），同一次提交会将其 input 结算为 `unanswered`，并清除相应字段。



> <strong>这对你意味着什么：</strong>
> 
> - 用 run 驱动忙碌指示，用 generation 和 tools 驱动流式视图
> 
> - 使用慢速或远程存储时，调大 `settings.progress` 的时间间隔
> 
> - 崩溃会丢失未提交的进度，而且没有固定的时间上界；已保存的运行则会保留下来
> 
>
