---
title: "Pi Durable 的用途"
---

<div class="section-kicker">PI DURABLE / 1.1 · P. 10</div>

# Pi Durable 的用途

---

智能体进程可能在执行任意一条指令时终止；Pi Durable 将每个可见步骤都变成已存储的commit，因此轮次中途的终止只是暂停，不会造成丢失。



你的智能体正执行到部署工具的一半，笔记本电脑的盖子合上了。进程恢复之后，哪些工作已经完成？Pi Durable 会记录中断之前已知的状态。工具的重放策略决定是再次执行，还是报告该工具可能已经部分执行。本节介绍没有它时会发生什么问题、它采取的三项措施，以及它刻意不做的事情。

## 问题：一个轮次有四种状态



智能体进程会因很普通的原因终止：部署替换进程、内核因内存不足而将其终止，或者笔记本电脑进入睡眠。轮次中途的终止会截断四种正在变化的状态：

- 对话记录，即到目前为止的消息

- 模型调用，即流式传输到一半的响应

- 工具调用，即执行到一半的副作用

- 应用状态，例如工具正在更新的待办事项列表



它们各自存放在不同地方。崩溃之后，它们会彼此不一致，而且没有任何记录说明各自进行到了哪一步。Earendil 的公告明确了目标：让智能体能够经受崩溃、重新部署和服务中断，并恢复被打断的工作，而不是从头开始。见 `earendil.com/posts/pi-durable`。

## 原版 Pi 保留了什么



Pi 编码智能体已经会持久化其会话。会话是 `~/.pi/agent/sessions/` 下的一个 JSONL 文件。每行是一个带有 `type` 的 JSON 对象；第一行是会话头，其余都是通过 `id` 和 `parentId` 组成树的条目。见 `coding-agent docs/session-format.md`。这棵树让 Pi 支持原地分支：`/tree` 可以移动到较早的条目，而不抹掉你离开的分支。见 `coding-agent docs/sessions.md`。



智能体循环生成一行，就追加一行。用户消息、包含工具调用的助手消息、工具结果，各自都是一条消息行。见 `session-format.md §Entry Types`。循环会在提供商完成流式传输后记录响应，然后执行每个工具调用并记录结果。见 `coding-agent docs/how-pi-works.md §Agent loop`。



<strong>这种设计保留了对话，却没有保留轮次。如果进程在工具运行时终止，文件就会结束于发起该工具调用的助手消息。没有任何一行说明工具已经启动，或者打印了什么。流式传输到一半的响应不会写入文件，扩展仅保存在内存中的状态也会消失。下一个进程可以重新读回对话，但无法判断工具的副作用是否已经发生。</strong>



<BookFigure id="D.1.1" :show-caption="false" />

> 工具执行中途发生崩溃后，原版 Pi 留下的文件以调用结束；Pi Durable 重新打开的则是一个被中断的任务。虚线左侧是 SIGKILL 之前写入的内容，右侧是下一个进程发现的内容。Pi Durable 的行记录来自 `research/capture/crash-*.txt` 中崩溃运行的对话 1，其中 `deploy` 已打印出 10 行中的 6 行。原版 Pi 的一行遵循 `session-format.md`。
> 
> 

## Pi Durable 的答案



<strong>Pi Durable 是一个 harness：一个已打开的存储</strong>，加上在其上运行智能体的机制。它采取三项措施，每项都弥补了上面的一处缺口：

- <strong>所有可见内容都经过commit</strong>：“对话、模型轮次、工具调用以及你自己的状态，都会在显示任何内容之前commit到存储。”见 `README`。流式传输到一半的回答和工具运行中的输出也会commit；进度commit之间默认至少间隔 100 ms。崩溃会丢失自上次成功commit以来的进度；存储延迟和输出节奏可能使这个间隔更长。见 `README §Watching a Conversation`。

- <strong>工作以带检查点的任务形式执行</strong>：模型调用和工具调用分别作为任务运行；任务是一个持久化状态机，在每个步骤都commit检查点。工具任务会在 `execute()` 运行之前，commit其意图、最终参数和重放策略。见 `src/harness/tool.ts`。重新打开时，harness 准确知道哪些调用已经开始。

- <strong>应用状态以文档形式包含在同一次commit中</strong>：文档是与对话记录一起存储的带类型 JSON。它与条目在同一次原子commit中变化，因此待办事项列表永远不会超前于修改它的消息。见 `README §Your Own State`。



崩溃运行展示了实际结果。第二个进程重新打开 SQLite 文件。仅仅打开这一步，就让运行中的工具任务回到了 `pending`。调用 `resume()` 后，未声明可安全重跑的 `deploy` 工具得到一个 `pi.tool-result` 条目，其中保留了其六行已commit输出，并附有一个错误：

```json
{
  "role": "toolResult",
  "toolCallId": "deploy-1",
  "toolName": "deploy",
  "content": [
    {
      "type": "text",
      "text": "deploy site: step 1/10 (pid 98319)\n...step 6/10 (pid 98319)\n"
    },
    {
      "type": "text",
      "text": "<harness>\n[error] Tool deploy was interrupted and may have partially run\n</harness>"
    }
  ],
  "isError": true,
  "timestamp": 1791211977057
}
```

> 这是条目 25 的模型消息。第一个文本块在这里有所删节，原本包含被终止进程的全部六行输出。条目的 `data.diagnostics` 带有同一个错误，其 `code` 为 `"interrupted"`。
> 
> 



模型随后读取该结果并作答，输入最终结算为 `done`。在同一次崩溃中，声明了 `replay: "safe"` 的 `fetch_report` 工具直接在新进程中从第1步重新运行。见 `research/capture/crash-README.md`。下一个进程没有猜测，而是读取一个说明“该副作用可能已经发生”的检查点，再应用预先选择的策略。副作用三明治（原书第70页）及工具调用与重放（原书第94页）会详细拆解这一过程。

## 它不是什么



其范围是刻意收窄的。从一开始就需要了解三个限制：

- <strong>每个存储只由一个进程使用</strong>：“同一时间，一个存储由一个进程拥有；没有跨进程锁。”见 `README §Storage`。Harness 不是集群调度器。监督和重启进程是宿主的工作。

- <strong>没有多写入者合并</strong>：规范将“CRDT／离线多写入者合并”列为非目标之一。见 `spec §13`。多个客户端可以观察和引导同一个对话，但每次写入都经过同一个 Harness。

- <strong>不会回滚外部世界</strong>：commit的原子性只限于存储内部。外部副作用“不会在 Session 变更事务内部运行”。见 `spec §1`，不变量 4。当harness无法知道支付是否成功时，它会明确报告这种不确定性，交由幂等键或远端记录来确定答案。见限制与非目标（原书第168页）。



> <strong>这对你意味着什么：</strong>
> 
> - 重新打开同一个存储，并恢复未完成的工作。安全工具可以再次运行；不安全工具会报告一个被中断的结果
> 
> - 逐个工具决定重复运行是否安全。这一个选择，就决定了调用被截断后的处理方式
> 
> - 将应用状态放在文档中，而非内存中，这样它永远不会与对话记录不一致
> 
> - 每个存储保持只有一个进程，并让进程监督程序负责重启
> 
> 



> 来源：`README.md`（引言、§Concepts、§Watching a Conversation、§Your Own State、§Storage）；`docs/spec.md §1, §13`；`src/harness/tool.ts`（ToolTask 的 `call`、`execute` 阶段）；`research/capture/crash-README.md`、`crash-before.txt`、`crash-reopen-tasks.txt`、`crash-after.txt`；`research/pi/packages/coding-agent/docs/session-format.md`、`sessions.md`、`how-pi-works.md`；`earendil.com/posts/pi-durable`（Earendil，2026年10月）
> 
>
