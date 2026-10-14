---
title: "工具调用与重放"
---

<div class="section-kicker">PI DURABLE / 6.4 · P. 94</div>

# 工具调用与重放

---

> 每次工具调用都会先提交意图，再执行；崩溃后，只有声明可安全重复的工具才会再次运行，其余工具都会被报告为已中断。
> 
> 

智能体调用了 deploy 工具，进程却在中途被终止。重启时应该再部署一次吗？运行两次可能造成灾难；悄悄遗忘也同样糟糕。Pi Durable 从不猜测。它会提交“调用即将运行”这一事实；崩溃后，仅重新运行你声明可安全重复的工具。其他所有调用都会向模型报告为已中断。读完本节，你就能决定某个工具是否应该设置 `replay: "safe"`，并预测崩溃后模型会看到什么。

## 每次调用一个任务



模型发起的每次工具调用都会成为独立的 `pi.tool` 任务，由接收到该调用的 generation 拥有。这个任务有两个阶段。



`ToolTaskCheckpoint`，来源：`src/harness/tool.ts`

```ts
type ToolTaskCheckpoint =
| { phase: "call" }
// 在 execute() 之前立即提交：最终参数和重放策略
| { phase: "execute"; arguments: JsonObject; replay: "safe" | "unsafe" };
```



一次调用经过以下步骤：

1. 按名称查找工具，并根据其 schema 检查参数

2. 运行 `beforeTool` 钩子；它们可能阻止调用，或更改参数（钩子，原书第109页）

3. 提交意图：阶段为 execute，附带最终参数和工具的重放策略；除非工具另有声明，否则为 `"unsafe"`

4. 运行 `execute()`，然后运行 `afterTool` 钩子

5. 提交结果：一个 `pi.tool-result` 条目，任务结束

    

这就是第 5 章的“副作用三明治”（原书第70页）：意图、副作用、结果。在第 3 步之前失败的调用绝不会触及外部世界，因此会立即得到一个错误结果。无论发生什么，运行都会带着一个结果条目继续：模型看到错误，并决定接下来做什么。

## 崩溃后的重放



重启后，如果发现工具任务处于 execute，它只知道一件事：副作用可能已经开始发生。规则很简单。只有存储的策略和工具当前的策略都为 safe，工具才会再次运行。否则，任务会用工具此前已经报告的输出构建一个 interrupted 错误结果并提交，不再运行工具。



采集记录在两个对话中运行两个慢工具，在两者都在打印内容时终止进程，然后在新进程中恢复。deploy 没有设置 replay，因此是不安全的；`fetch_report` 声明了 `replay: "safe"`。



<BookFigure id="D.6.5" :show-caption="false" />

> 调用中途崩溃后，安全工具会再次运行，不安全工具会被报告为已中断。序列号来自 `research/capture/crash-before.txt` 和 `crash-after.txt`；时间采用测试父进程的时钟。在采集记录中，两个工具的输出提交相互交错。
> 
> 



随后，对话 1 中的模型接收到以下结果：



条目 25，被中断的 deploy，来源：`research/capture/crash-after.txt`

```json
{
    "role": "toolResult", "toolCallId": "deploy-1", "toolName": "deploy",
    "content": [
    { "type": "text", "text": "deploy site: step 1/10 (pid 98319)\n ..." },
    { "type": "text", "text": "<harness>\n[error] Tool deploy was interrupted and may have partially run\n</harness>" }
    ],
    "isError": true,
    "timestamp": 1791211977057
}
```



这是该条目 model 数组内的消息。第一个文本部分保存了全部六行已提交输出；第 2–6 行在此省略。条目还在 `data.diagnostics` 中保存了诊断信息，其 code 为 interrupted。



任务 22 以 failed 结束，而运行继续：下一个 generation 回答 “Tool deploy FAILED”。在对话 7 中，安全工具先清空旧输出，然后在新进程中执行全部十个步骤，并以条目 28 完成。两个 input 最终都变为 done。

## 选择策略



`replay: "safe"` 是一种承诺：执行两次该副作用不会造成危害，例如读取、幂等写入，或者带有远端认可的幂等键的写入（副作用三明治，原书第70页）。其他情况都应保持 unsafe，并诚实地告诉模型“可能已经部分执行”。三个细节让这条规则比表面上更严格：

- 两份策略都要满足：工具若改成 unsafe，就不会重跑；存储为 unsafe 的调用，即使工具后来改成 safe，也不会重跑

- 工具缺失：对话已无法使用的工具按 unsafe 处理

- 新的环境：重跑时会根据对话当前的工作目录重新构建环境，而目录可能已经改变（执行环境，原书第155页）

    

第 3 步之前崩溃的代价较小。任务仍处于 call，因此整个调用会从头运行一次，包括 `beforeTool`。

## 工具轮次



一个工具轮次就是一次模型响应中的所有调用。默认情况下它们并行运行；一个调用失败，绝不会取消其他调用。如果设置中的 toolExecution 为 `"sequential"`，或者任意被调用工具声明了 `executionMode: "sequential"`，本轮就会逐个执行调用。每个调用都结束后，generation 提交一次。工具结果可以影响这次提交（定义工具，原书第112页）：

- `terminate`：结束运行，不再调用模型，但前提是本轮每次调用都提出这一要求

- `handoff`：将上下文重置为交接文本，并结束运行（重置与交接，原书第46页）

- `addTools`：从下一轮次开始提供更多工具

    

否则，就会执行一次 postTools 边界，由新的 generation 接管运行。如果运行在本轮中途中止，尚未开始的调用会得到 aborted 结果。

## 细节：Harness 写入的错误结果



|<strong>诊断代码</strong>|<strong>何时出现</strong>|<strong>任务的结束状态</strong>|
|---|---|---|
|`tool_unavailable`|工具未提供给模型，或已不存在|`completed`|
|`invalid_arguments`|在 beforeTool 之前或之后，参数不符合 schema|`completed`|
|`blocked`|beforeTool 钩子阻止调用或抛出异常|`completed`|
|`tool_error`|execute\(\) 抛出异常，或无法构建其环境|`failed`|
|`interrupted`|调用中途崩溃，且没有安全策略|`failed`|
|`aborted`|调用被中止|`aborted`|

> `src/harness/tool.ts` 和 `generation.ts`。每个结果都带有 `isError: true`；最后三种会保留此前已经报告的输出。以 failed 或 aborted 结束的任务，也会中止该调用拥有的所有对话（所有权，原书第76页）。
> 
> 



> <strong>这对你意味着什么：</strong>
> 
> - 只有运行两次不会造成危害时，才将工具标记为 `replay: "safe"`
> 
> - 边执行边用 output 报告进度：调用被中断时，这就是模型看到的内容
> 
> - 如果 beforeTool 钩子在崩溃后必须作出相同决定，应把决定存入 memo（备忘，原书第67页）
> 
> 



> 来源：规范 §7\.3、§8\.4、§8\.5、§12；`src/harness/tool.ts`；`src/harness/generation.ts`；`src/harness/agent.ts`；`src/harness/types.ts`（`ToolRegistration`、`ToolControl`、`ToolHooks`）；README §Tools；`test/harness-tools.test.ts`；`test/harness-tools-recovery.test.ts`；`research/capture/crash-README.md`；`research/capture/crash-before.txt`；`research/capture/crash-reopen-tasks.txt`；`research/capture/crash-after.txt`
> 
>
