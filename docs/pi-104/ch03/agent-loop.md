---
title: "智能体循环"
description: "Pi 1.0.4 · 3.1 · 原书第 49–56 页"
---

<div class="section-kicker">3.1 / THE AGENT LOOP</div>

# 智能体循环

---

<strong>`pi-agent-core` 中的循环是一个自身不保存状态的函数：它以流式方式获取响应，运行工具调用，只要工具结果或排队消息仍有内容需要发送，就再次循环。它没有轮次上限。</strong>



<strong>Pi 在对话期间发出的每一次模型调用，都经过同一个函数：agent/agent-loop.ts 中的 `runLoop`。</strong>本节先介绍用于配置循环的类型，再逐个状态走读循环，区分向它提供消息的两个队列，最后跟踪一批工具调用的准备、执行和结果排序过程。“智能体事件与 Agent 类”（原书第57页）列出了它发出的事件；“AgentSession：组装运行时”（原书第61页）展示了编码智能体如何填充它的钩子。

## 包及其类型



@earendil-works/pi-agent-core 1.0.4 由六个文件组成，共 2,513 行，其中非空行 2,281 行（research/out/stats.txt）。它分为两层：无状态循环接收上下文和配置并发出事件；有状态的 Agent 类持有对话记录和两个队列。

|<strong>文件</strong>|<strong>行数</strong>|<strong>内容</strong>|
|---|---|---|
|agent/types.ts|529|StreamFn、AgentLoopConfig、AgentMessage、AgentTool、AgentEvent、钩子类型|
|agent/agent-loop.ts|940|agentLoop、agentLoopContinue、runLoop、工具执行、runToolCall|
|agent/agent.ts|613|Agent：状态归约器、Steering与follow-up队列、运行生命周期|
|agent/proxy.ts|406|streamProxy：供通过自有服务器转发模型调用的应用使用的 StreamFn|
|agent/stream-fn.ts|20|setDefaultStreamFn、getDefaultStreamFn|
|agent/index.ts|5|重新导出；不导出 getDefaultStreamFn|



整个运行时集中在三个文件中。行数由 28dcce2 版本上的 `wc -l` 得出。



循环从不直接调用提供商。它调用 `StreamFn`（agent/types.ts:33），其形式与 pi-ai 中的 `streamSimple` 相同（“流式事件协议”，原书第30页）。类型上写明了契约：流函数“不得因请求、模型或运行时故障而抛出异常或返回被拒绝的 Promise”；故障以最终消息的形式到达，其 stopReason 为 "error" 或 "aborted"。循环传入的是规范化后的对话记录，其中“系统提示词和工具声明由对话记录中的系统消息承载，绝不由 context.systemPrompt 或 context.tools 承载”（agent/types.ts:23）。



消息是一个开放联合类型。`AgentMessage` 为 `Message | CustomAgentMessages[keyof CustomAgentMessages]`，而 `CustomAgentMessages` 是一个空接口，应用通过声明合并来扩展它（agent/types.ts:365）。编码智能体以这种方式添加了四种角色（“AgentSession：组装运行时”，原书第61页）。



工具由 pi-ai 的 Tool 加上运行时执行它所需的信息构成（agent/types.ts:464）：

- `label`：供 UI 使用的人类可读名称

- `prepareArguments?(args)`：在模式校验之前，应用于原始参数的兼容性适配层

- `outputSchema?`：成功结果中 structuredContent 的 JSON Schema

- `execute(toolCallId, params, signal?, onUpdate?)`：返回 `AgentToolResult`，包含供模型使用的 content、供日志和 UI 使用的 details、可选的 structuredContent（不发送给模型）、usage、isError 和 terminate。Promise 结束后的 onUpdate 调用会被忽略（agent/types.ts:458）

- `replay?`："never" 或 "safe"，用于结果未知的副作用的恢复策略

- `executionMode?`："sequential" 或 "parallel"，按工具覆盖整批执行模式

    

`AgentLoopConfig` 继承 `SimpleStreamOptions`，并承载所有钩子（agent/types.ts:193）。思考级别通过继承来的 reasoning 字段传递，其中 "off" 存储为 undefined。

|<strong>字段</strong>|<strong>调用时机</strong>|<strong>契约</strong>|
|---|---|---|
|`model`|—|下一次请求使用的模型|
|`convertToLlm(messages)`|每次请求之前|`AgentMessage[] → Message[]`；丢弃仅供 UI 使用的消息；不得抛出异常|
|`transformContext?(messages, signal)`|convertToLlm 之前|在 AgentMessage 层级裁剪或注入消息；不得抛出异常|
|`getApiKey?(provider)`|每次请求之前|解析会过期的令牌；不得抛出异常|
|`prepareRequest?`|每次请求之前，包括第一次|可以替换本次及后续请求的上下文、模型和思考级别|
|`prepareNextTurn?`|turn_end 之后、下一个 turn_start 之前|返回 {context?, messages?, model?, thinkingLevel?}|
|`finishTurn?`|工具结果之后、turn_end 之前|返回 {action: "continue"}、{action: "end"} 或不返回任何内容|
|`getSteeringMessages?`|循环开始时、每个轮次之后、prepareNextTurn 之后|取出并清除Steering队列中的待处理消息|
|`getFollowUpMessages?`|内层循环即将退出时|取出并清除follow-up队列中的待处理消息|
|`toolExecution?`|—|"parallel"（默认）或 "sequential"|
|`beforeToolCall? / afterToolCall?`|每次工具调用|阻止调用；覆盖结果中的字段|



除 convertToLlm 外，每个钩子都是可选的。依据 agent/types.ts:193–342 中的 AgentLoopConfig。

## 逐个状态走读循环



有两个入口：

- `agentLoop(prompts, context, config, signal, streamFn)`（agent/agent-loop.ts:38）从新的提示消息开始，返回 `EventStream<AgentEvent, AgentMessage[]>`。

- `agentLoopContinue(...)`（agent/agent-loop.ts:71）从现有上下文恢复；上下文为空时，它抛出 `Cannot continue: no messages in context`；最后一条消息是助手回复时，它抛出 `Cannot continue from message role: assistant`。

两者都有 run… 变体，这些变体接收事件接收器，而不是返回流，Agent 使用的就是这些变体。



<strong>`runAgentLoop`（agent/agent-loop.ts:102）在提示消息之前声明所有工具变更，发出 `agent_start` 和 `turn_start`，再为每条提示消息发出 `message_start` 和 `message_end`，然后将控制权交给 runLoop</strong>（原文此处的源码引用截断为 `agent/agent-`）。



<BookFigure id="3.1" />

> 只要还有内容需要响应，循环就会继续；它只在三个位置停止。这是 agent/agent-loop.ts 中一次 runLoop 调用的示意图；数字为 28dcce2 版本的行号。粗琥珀色箭头表示两条返回路径：内层循环（工具结果或Steering）和外层循环（follow-up，或要求继续的 finishTurn）。玫瑰色出口是唯一跳过队列的出口。
> 
> 



按从上到下的顺序阅读图3.1（原书第51页），即可跟踪一个轮次。第一次经过时跳过 `prepareNextTurn`，因为 `runAgentLoop` 已经发出了 `turn_start`。此后每次经过都会运行它，再发出自己的 `turn_start`。待处理消息通过 `declareToolChanges`（agent/agent-loop.ts:333）注入；该函数比较运行时能够执行的工具（context.tools）与对话记录中已声明的工具。差异会转化为系统消息上的 `toolsAdded` 或 `toolsRemoved`：若已有待处理的系统消息，就合并进去；否则，在第一条非系统消息之前插入一条内容为空的新系统消息。没有差异，就没有消息。



模型边界是 `streamAssistantResponse`（agent/agent-loop.ts:381），它足够简短，可以直接引用：

```js
// Apply context transform if configured (AgentMessage[] → AgentMessage[])
let messages = context.messages;
if (config.transformContext) {
    messages = await config.transformContext(messages, signal);
}

// Convert to LLM-compatible messages (AgentMessage[] → Message[])
const llmMessages = await config.convertToLlm(messages);

const llmContext = normalizeContext({ messages: llmMessages});

// Resolve API key (important for expiring tokens)
const resolvedApiKey =
(config.getApiKey ? await config.getApiKey(config.model.provider) : undefined) ||
config.apiKey;

const response = await streamFunction(config.model, llmContext, {
    ...config,
    apiKey: resolvedApiKey,
    signal,
});
```



提供商的 start 事件将部分消息推入上下文，并发出 `message_start`。九种块事件（text_\*、thinking_\*、toolcall_\*）中的每一种都会替换最后一条消息，并随原始 `assistantMessageEvent` 发出 `message_update`。done 和 error 会等待 `response.result()`，在最终消息上写入 `thinkingLevel`，并发出 `message_end`（agent/agent-loop.ts:409）。



这些结果值得集中说明一次：

- 一个轮次是一次助手响应，加上它的工具调用及结果。AgentEvent 类型的注释明确这样说明（agent/types.ts:518）

- 工具结果通过推入 `currentContext.messages` 反馈回来（agent/agent-loop.ts:274）。下一次经过循环时，会把它们放在上下文中，以流式方式获取新的响应

- 没有轮次上限。`runLoop` 中没有任何轮次计数逻辑

- 循环恰好在三个位置停止：响应的 `stopReason` 为 "error" 或 "aborted"（agent/agent-loop.ts:245）；finishTurn 返回 {action: "end"}（agent/agent-loop.ts:289）；以及某次经过时，没有未终止的工具结果、没有Steering、没有follow-up，也没有显式继续的要求（agent/agent-loop.ts:317）

- 在错误出口，finishTurn 仍会运行，但其决定会被忽略；紧接着就会发出 turn_end 和 agent_end（agent/agent-loop.ts:252）



> <strong>易踩的坑</strong>
> 
> 被输出上限截断的响应，可能包含参数能够解析并通过校验、但实际并不完整的工具调用。当 stopReason 为 "length" 时，循环不会运行其中任何调用。每个调用都会得到错误结果：`Tool call "<name>" was not executed: the response hit the output token limit, so its arguments may be truncated. Re-issue the tool call with complete arguments.`（agent/agent-loop.ts:493）。模型看到的是错误，而非执行结果，循环会再次运行。
> 
> 

## Steering与follow-up



两个队列从运行之外向循环提供消息。它们都存放 `AgentMessage`，由 `getSteeringMessages` 和 `getFollowUpMessages` 钩子取出待处理消息；Agent 将这两个钩子连接到 `PendingMessageQueue` 实例（agent/agent.ts:496）。它们唯一的区别，是循环轮询它们的位置。

|<strong>项目</strong>|<strong>Steering</strong>|<strong>follow-up</strong>|
|---|---|---|
|API|agent.steer(msg)|agent.followUp(msg)|
|用途|“在当前助手轮次结束后注入”（agent/agent.ts:298）|“仅在智能体原本即将停止后运行”（agent/agent.ts:303）|
|轮询位置|循环开始时 :176；每个 turn_end 之后 :295；若上次轮询为空，则在 prepareNextTurn 之后 :204|内层循环退出时 :302|
|是否打断当前工具调用|否；“不会跳过当前助手消息中的工具调用”（agent/types.ts:287）|否|
|交互快捷键|流式输出时按 Enter|Alt+Enter（Windows 上为 Ctrl+Q）|
|取出模式|steeringMode："one-at-a-time"（默认）或 "all"|followUpMode：相同|



<strong>Steering等待当前轮次的工具完成；follow-up等待整个运行(run)结束。</strong>轮询位置来自 agent/agent-loop.ts；快捷键来自 CA/src/core/keybindings.ts:134 中的 `app.message.followUp`，以及 CA/src/modes/interactive/interactive-mode.ts:3358 中的提交处理器。



`one-at-a-time` 表示每个取出点只取出一条消息（agent/agent.ts:159，TS）。

```ts
peek(): AgentMessage[] {
    if (this.mode === "all") return this.messages.slice();
    const first = this.messages[0];
    return first ? [first] : [];
}

drain(): AgentMessage[] {
    const drained = this.peek();
    this.messages = this.messages.slice(drained.length);
    return drained;
}
```



`PendingMessageQueue.peek` 和 drain，第159–169行，内容未改动。



`prepareNextTurn` 之后再次轮询，是因为这个钩子可能运行数秒：编码智能体在那里进行压缩（“压缩与分支摘要”，原书第92页）。源码解释了这项保护：“只有前一次轮询没有返回任何内容时才再次轮询；否则，one-at-a-time 模式会在此轮次交付两条消息”（agent/agent-loop.ts:202）。



采集工具在一个正在运行的工具内部，将一条Steering和一条follow-up放入队列，随后让循环完成（research/out/agent-loop-queues.txt）。Steering作为第2轮的用户消息进入，紧跟在工具结果之后；follow-up则等到第2轮产生普通回答后，才开启第3轮。一次 agent.prompt() 产生了三个轮次，以及一个携带 8 条新消息的 agent_end。

## 工具执行



`executeToolCalls`（agent/agent-loop.ts:508）为每一批调用选择执行模式。当 `config.toolExecution === "sequential"`，或任一被调用工具声明了 executionMode: "sequential" 时，按顺序执行；否则采用默认的并行执行。



每次调用首先由 `prepareToolCall`（agent/agent-loop.ts:707）依次完成准备：

1. 按名称查找工具。未知工具 → 错误结果 `Tool <name> not found`

2. 应用 prepareArguments，再运行 validateToolArguments。抛出的错误会成为错误文本

3. 调用 beforeToolCall。如果此时信号已中止 → `Operation aborted`。{block: true} → 带有 reason 的错误结果，默认文本为 `Tool execution was blocked`



上述任一结果都会立即返回：调用根本不会执行。否则，execute 会运行，抛出的错误会变成 isError: true 的结果（agent/agent-loop.ts:841）。随后，afterToolCall 逐字段覆盖结果：content、details、usage、terminate、structuredContent 和 isError（agent/agent-loop.ts:877）。若替换 content 却没有返回 structuredContent，则会丢弃 structuredContent，“因为它可能不再与内容匹配”（agent/types.ts:85）。



<BookFigure id="3.2" />

> 预检按顺序进行，执行并发进行，结果按原始顺序返回。research/out/agent-loop-queues.txt 的事件7–15：faux 模型先请求 slow（id A），再请求 fast（id B）。tool_execution_end 遵循完成顺序（B 在 A 之前）；toolResult 消息遵循助手消息中调用的顺序（A 在 B 之前）。立即产生的结果会在预检期间发出其 tool_execution_end。
> 
> 



在顺序模式下，每次调用都会完成 `start → prepare → execute → finalize → tool_execution_end → toolResult 消息`，下一次调用才开始；若信号中止，整批调用会提前停止（agent/agent-loop.ts:575）。



只有当“一批调用中每个已最终确定的工具结果”都设置了 terminate: true 时，这一批调用才会提前结束运行（agent/agent-loop.ts:689）。只要有一个结果没有设置它，循环就会继续。



`runToolCall(toolCall, options)`（agent/agent-loop.ts:810）运行相同的 prepare → execute → finalize 流程，但“不发出事件，也不添加消息”。编码智能体将它用于工具通过 ctx.executeTool() 发起的调用（“扩展、加载与 API”，原书第113页）；codemode 正是通过这种方式，使用相同的权限钩子来运行嵌套调用（“codemode”，原书第151页）。



> 这对你意味着什么：
> 
> - 绝不要在 StreamFn、convertToLlm、transformContext 或队列钩子中抛出异常；应返回失败消息或安全的回退结果
> 
> - 要预期多个 `tool_execution_end` 事件可能按任意顺序到达；通过 toolCallId 匹配它们，并从 toolResult 消息中按原始顺序读取结果
> 
> - 使用Steering，在当前工具完成后改变方向；使用follow-up，将工作排队到智能体原本即将停止时执行
> 
> - 在 finishTurn 中或通过中止来自行限制长时间运行：循环没有轮次上限
> 
> 



> 来源：agent/types.ts（StreamFn、AgentTool、AgentToolResult、AfterToolCallResult、AgentLoopConfig、CustomAgentMessages、AgentEvent）；agent/agent-loop.ts（agentLoop、agentLoopContinue、runAgentLoop、runLoop、declareToolChanges、streamAssistantResponse、failToolCallsFromTruncatedMessage、executeToolCalls、executeToolCallsSequential、executeToolCallsParallel、prepareToolCall、finalizeExecutedToolCall、shouldTerminateToolBatch、runToolCall）；agent/agent.ts（PendingMessageQueue、createLoopConfig）；agent/index.ts；CA/src/core/keybindings.ts:134；CA/src/modes/interactive/interactive-mode.ts:3358、4435；CA/src/extensions/codemode/execute.ts:405；research/capture/agent-loop-queues.mjs；research/out/agent-loop-queues.txt；research/out/stats.txt
> 
>
