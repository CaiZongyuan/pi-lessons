---
title: "一次输入得到回答的全过程"
---

<div class="section-kicker">PI DURABLE / 1.4 · P. 19</div>

# 一次输入得到回答的全过程

---

> 一个问题、一次工具调用和一个答案，需要十七次commit；按顺序读完这些commit，也就读懂了整个harness。
> 
> 



用户提出“Count to 3\.”，模型调用 `count` 工具，然后给出回答。这一小段交互需要十七次commit。本节按顺序走过这些commit，让你能够阅读任何commit日志，说清楚每一行由谁写入、为什么写入，以及如果恰好在那一刻崩溃，会留下什么。

## 这次运行



README 的 Quick Start 是最小的宿主示例。它在存储之上打开一个 Harness，获取根对话，commit输入，然后等待答案：



<strong>快速开始，节选</strong> · `README.md §Quick Start`

```js
const harness = await Harness.open(
    new MemoryStorage(), { models, registry: createRegistry() }, context
);
const root = await harness.root(context, {
    agent: { model: { provider: "openai", modelId: "gpt-6-sol" } },
});

const submission = await root.submit(
    { type: "input", content: "What is the capital of France?" }, context);
const settled = await submission.wait(context);
// settled.answer 是作出回答的 pi.assistant 条目的 ID
await harness.close(context);
```

> 此处省略了导入、模型设置和读回答案的代码。输入变为 `done` 或 `unanswered` 时，`wait()` 即兑现。
> 
> 



捕获脚本在 SQLite 上执行相同步骤，因此每次commit都可以作为行记录读回。见 `research/capture/scripts/one-turn.ts`。faux 模型以 `{n: 3}` 调用 `count` 工具，然后回答“I counted 1, 2, 3\.”。工具通过 `api.output()` 打印三行，并返回 `{}`。一个 `subscribeCommits()` 监听者会记录每次commit。



下面两幅图展示这次运行。每个编号箭头都是一次commit，编号就是该commit在存储中的 `seq`。

### commit 1–2：先有对话，再有输入



<strong>`root()` 在commit 1 中创建根对话。同一次commit还创建其五个内置文档，ID 为 2 到 6：`pi.live`、`pi.inbox`、`pi.usage`、`pi.provider` 和 `pi.agent`。</strong>见 `src/harness/harness.ts`（`conversationCreated`）。智能体文档存储模型选择 `faux/faux-1`。打开 Harness 时也运行过一次commit，用于协调处理运行中的任务，但它没有任何写入。没有写入的commit会被丢弃，不占用序号。见 `src/session/session.ts`。



<strong>`submit()` 是commit 2，也是让输入持久化的那次commit。对话当前空闲，所以接纳操作会在一次commit中做三件事。</strong>见 `src/harness/submissions.ts`（`admitSubmission`）。<strong>它追加一个 `pi.user` 条目 7，创建状态为 `placed` 且 `entry: 7` 的commit请求 8，并启动一次运行：创建生成任务 9，将 `pi.live.run` 设为 `{"taskId": 9, "inputs": [8]}`。从此刻起，对话变为忙碌，因为“忙碌”的定义就是存在 `pi.live.run`。</strong>见运行控制（原书第88页）。<strong>此次commit之后的崩溃，不会丢失用户输入的任何内容。以相同 `requestId` 重新commit，会返回commit请求 8，而不是创建新的commit请求。</strong>



<BookFigure id="D.1.4" :show-caption="false" />

> commit 1–8 将输入从 `submit()` 推进到工具调用意图已持久化的状态。依据 `research/capture/sqlite-commits.txt`；文档操作来自 `research/capture/extra-p1/sqlite-commit-ops.txt`。
> 
> 

### commit 3–6：第一次生成



<strong>commit 3 是调度器在工作。它将任务 9 从 `pending` 改写为 `running`，以此预留任务，但不改变其检查点 `{phase: "prepare", attempt: 1}`。</strong>见调度器（原书第73页）。这次运行中的每个任务，都以这样的预留commit开始。



<strong>`prepare` 阶段渲染系统提示词和工具列表，并将其作为 `pi.system` 条目 10 commit；其中包含 preamble 节和 `count` 工具。同一次commit，即commit 4，还将任务移到 `request` 阶段，并记录模型、思考级别和条目 10 这一截止点。`request` 阶段首先commit `pi.live.generation = {attempt: 1}`（commit 5），然后在队列之外调用 `models.streamSimple()`。</strong>faux 流在 100 ms 的节流窗口内就已结束，因此没有commit部分响应。较慢的流会在这里增加经过节流的部分响应commit。见生成（原书第91页）。



响应以 `toolUse` 为停止原因结束。commit 6 是本轮的转折点。它将响应写为 `pi.assistant` 条目 11，并将其用量计入 `pi.usage`。它创建归任务 9 所有的工具任务 12，在 `pi.live.tools` 中列出该调用，并将任务 9 改为等待 `[12]`，策略为 `allSettled`。见 `src/harness/generation.ts`（`startToolRound`）。如果在commit 6 之后崩溃，重新打开时调用已经记录，其任务为 `pending`，因此工具会运行。如果在此之前崩溃，重新打开时处于 `request` 阶段，模型调用会直接重新发起。

### commit 7–8：先有意图，再执行副作用



commit 7 预留任务 12。接着，它的 `call` 阶段从条目 11 读取调用，解析工具、验证参数，并运行所有 `beforeTool` 钩子。然后，在执行任何工具代码之前，它先commit意图，即commit 8：



<strong>commit 8 之后的工具任务 12</strong> · `research/capture/sqlite-rows-midrun.txt` · JSON（节选）

```json
{
  "id": 12,
  "kind": "pi.tool",
  ...
  "input": { "assistant": 11, "callId": "call-1" },
  "owner": 9,
  ...
  "state": {
    "status": "running",
    "checkpoint": {
      "phase": "execute",
      "arguments": { "n": 3 },
      "replay": "unsafe"
    }
  }
}
```

> 这是在 `execute()` 运行时，通过第二个连接读取的 tasks 行；省略了 `conversationId`、`version` 和两个布尔标志。`count` 没有声明 `replay`，因此存储的策略为 `"unsafe"`。
> 
> 



正是这条记录，使工具执行中途的崩溃能够恢复。只有恢复流程才会单独进入 `execute` 阶段。如果后续进程发现任务处于这个阶段，工具就可能已经运行；存储的 `replay` 决定是再次执行，还是写入被中断的错误结果。见 `src/harness/tool.ts`。1\.1 节（原书第10页）中的 `deploy` 正是这种情况。

### commit 9–11：先输出，再写入结果



工具输出作为进度commit，默认至少间隔 100 ms。commit 9 将 `pi.live.tools[0].output` 设为 `"1\n"`；commit 10 追加 `"2\n3\n"`。观察者看到输出逐渐增长；<strong>若发生崩溃，只会丢失自上次成功的进度commit以来的输出。</strong>这个间隔没有固定的时间上限。`execute()` 返回时，commit 11 追加 `pi.tool-result` 条目 13，内容为 `"1\n2\n3\n"`，并使任务 12 进入终态，结果为 `{status: "completed", result: {entryId: 13}}`。



<BookFigure id="D.1.5" :show-caption="false" />

> commit 9–17 承载工具输出、结果、第二次生成和答案。琥珀色箭头表示仅涉及任务的commit：预留，以及提示词未发生变化时移到 `request` 阶段的操作。
> 
> 

### commit 12–17：第二次生成与答案



任务 12 已进入终态，因此任务 9 的等待结束。commit 12 在 `tools` 阶段预留它。工具执行期间发送的排队写入和引导消息，会在这一阶段被放入对话。见收件箱（原书第84页）。然后，它交接这次运行：commit 13 创建生成任务 14，将 `pi.live.run.taskId` 移到 14，清除工具执行轮，并以 `completed` 状态结束任务 9，其结果为 `result: {entryId: 11}`。见 `src/harness/generation.ts`（`finishToolRound`）。



生成任务 14 重复第一次生成的各个阶段，只有一点不同。它的 `prepare` 阶段发现提示词与工具没有变化，因此不追加 `pi.system` 条目，commit 15 只将任务移到 `request` 阶段。系统条目是按位置记录的增量，只有发生变化时才会发送。见系统提示词（原书第115页）。commit 16 在 `pi.live` 中标记本次尝试，模型随后以停止原因 `stop` 作答。



commit 17 一次完成所有收尾工作。它将答案追加为 `pi.assistant` 条目 15，并把commit请求 8 结算为 `done`，设置 `answer: 15`。它使任务 14 进入终态，删除 `pi.live.run` 和 `pi.live.generation`，让对话再次空闲，并将第二个响应的词元数计入 `pi.usage`。Submissions 组件在commit发布时看到已结算的记录，随后兑现宿主的 `wait()`。

## 完整日志



|<strong>SEQ</strong>|<strong>写入的记录</strong>|<strong>文档</strong>|<strong>写入方</strong>|
|---|---|---|---|
|1|对话 1|创建 2–6|`root()`|
|2|条目 7 `pi.user`；commit请求 8 `placed`；任务 9 `pending`|`pi.live`|`submit()`|
|3|任务 9 `running` · `prepare`|—|调度器|
|4|条目 10 `pi.system`；任务 9 · `request`|—|生成任务 9|
|5|—|`pi.live`|生成任务 9|
|6|条目 11 `pi.assistant`；任务 9 `waiting`；任务 12 `pending`|`pi.live`、`pi.usage`|生成任务 9|
|7|任务 12 `running` · `call`|—|调度器|
|8|任务 12 · `execute`|`pi.live`|工具任务 12|
|9、10|—|`pi.live`|工具任务 12 的进度|
|11|条目 13 `pi.tool-result`；任务 12 `terminal`|`pi.live`|工具任务 12|
|12|任务 9 `running` · `tools`|—|调度器|
|13|任务 14 `pending`；任务 9 `terminal`|`pi.live`|生成任务 9|
|14|任务 14 `running` · `prepare`|—|调度器|
|15|任务 14 · `request`|—|生成任务 14|
|16|—|`pi.live`|生成任务 14|
|17|条目 15 `pi.assistant`；commit请求 8 `done`；任务 14 `terminal`|`pi.live`、`pi.usage`|生成任务 14|

> 这是 `research/capture/sqlite-commits.txt` 中的每一次commit；JSONL 运行也有相同的十七次commit。
> 
> 



> <strong>这对你意味着什么：</strong>
> 
> - 从commit 2 起，用户文本就已安全保存；使用相同 `requestId` 重新commit，不会造成重复
> 
> - 工具的意图在任何工具代码运行之前就已commit（commit 8），因此恢复流程总能知道调用可能已经开始
> 
> - 不会有任何commit留下一个答案却没有结算其commit请求，也不会留下一个工具调用却没有相应任务。在任意一行之后终止进程，重新打开时都知道接下来该做什么
> 
>
