---
title: "智能体事件与 Agent 类"
description: "Pi 1.0.4 · 3.2 · 原书第 57–60 页"
---

<div class="section-kicker">3.2 / THE AGENT LOOP</div>

# 智能体事件与 Agent 类

---

十种事件类型描述每一次运行，按运行、轮次和消息嵌套。Agent 类会在任何监听器看到事件之前，根据该事件更新自身状态；直到最后一个 agent_end 监听器返回之前，它都保持忙碌。



所有观察 Pi 工作的组件，包括终端 UI、JSON 和 RPC 输出、扩展、会话文件，都由同一条事件流驱动。本节列出十种 AgentEvent 类型及其载荷，并通过一次真实运行展示它们的到达顺序。随后介绍发出这些事件的 Agent 类：它的默认值、prompt 和 continue 规则、状态归约器，以及它如何收尾一次抛出异常的运行。

## 十种事件



<strong>AgentEvent 是包含十个成员的可辨识联合类型</strong>（agent/types.ts:514）。它们分布于三个嵌套生命周期和一个工具生命周期中。

|<strong>事件</strong>|<strong>载荷</strong>|<strong>发出时机</strong>|
|---|---|---|
|`agent_start`|—|一次；运行的第一个事件|
|`agent_end`|messages: AgentMessage[]|一次；运行的最后一个事件；messages 为本次运行的新消息|
|`turn_start`|—|每次助手响应之前|
|`turn_end`|message: AgentMessage, toolResults: ToolResultMessage[]|响应及其所有工具结果之后|
|`message_start`|message: AgentMessage|用于 system、user、assistant、toolResult 和自定义消息|
|`message_update`|message, assistantMessageEvent: AssistantMessageEvent|仅用于助手消息；每个流式块事件对应一次|
|`message_end`|message: AgentMessage|消息最终确定时|
|`tool_execution_start`|toolCallId, toolName, args|调用准备之前|
|`tool_execution_update`|toolCallId, toolName, args, partialResult|正在运行的工具每次调用 onUpdate 时|
|`tool_execution_end`|toolCallId, toolName, result, isError|afterToolCall 之后，按完成顺序|



只有助手消息以流式方式传递；其他消息都以 start/end 对的形式到达。依据 agent/types.ts:514–529 中的 AgentEvent；发出位置位于 agent/agent-loop.ts。



`message_update` 携带触发它的 pi-ai 事件（text_delta、toolcall_end 等，见“流式事件协议”，原书第30页），以及部分消息的浅拷贝。agent_end 是运行的最后一个事件，但该类型自己的注释提醒说：被等待的“该事件监听器仍属于运行收尾的一部分。只有这些监听器结束后，智能体才会变为空闲”（agent/types.ts:510）。

## 一次真实运行中的顺序



采集工具使用 faux 提供商，通过真实的 AgentSession 运行了一条提示：模型用一次 read 调用读取 hello.txt，然后回答（research/out/one-turn.txt）。订阅者看到了 29 个事件。图3.3（原书第58页）按循环中的嵌套关系展示这些事件。



<BookFigure id="3.3" />

> <strong>A run is turns, a turn is messages, and tools sit between the assistant message and its results.</strong> <strong>一次运行由多个轮次组成，一个轮次由多条消息组成，工具位于助手消息及其结果之间。</strong>这是 research/out/one-turn.txt 中的事件流，按生命周期缩进；包含 28 个 AgentEvent，加上会话的 `agent_settled`。`text_delta` 事件的数量因运行而异，顺序则不变。没有出现 `tool_execution_update`，因为 read 不报告部分结果。
> 
> 



有两次工具调用时，整体框架不变，只增加图3.2（原书第55页）所示的细节。<strong>在并行模式下，所有 `tool_execution_start` 事件都先于任何 `tool_execution_end` 事件，结束事件按完成顺序到达。</strong>随后，<strong>`toolResult` 消息按调用在助手消息中出现的顺序到达。Steering会在下一个 turn_start 之后，立即作为用户消息的 message_start/message_end 对出现；工具变更声明也以相同方式作为系统消息出现</strong>（research/out/agent-loop-queues.txt）。



采集结果中的第一条系统消息，并不是构造时预置的系统提示词。编码智能体使用空提示词且不带工具来构造 Agent，因此不存在预置消息。第一条提示携带了一条系统消息，其中包含提示词分节，以及四个默认工具的 toolsAdded；它是同一采集结果中会话文件的第4行（“会话：JSONL 树”，原书第86页）。

## Agent 类



Agent（agent/agent.ts:188）持有对话记录、“智能体循环”（原书第49页）中的两个队列、一组监听器，以及至多一次正在进行的运行。每次运行时，它将自身字段转化为 AgentLoopConfig（agent/agent.ts:467），并将 processEvents 传入，作为循环的事件接收器。

|<strong>选项</strong>|<strong>默认值</strong>|<strong>参见</strong>|
|---|---|---|
|convertToLlm|保留 system、user、assistant、toolResult；丢弃其他所有角色|agent/agent.ts:38|
|streamFn|getDefaultStreamFn()，它会抛出 `No default stream function configured. Pass streamFn explicitly or call setDefaultStreamFn().`|agent/stream-fn.ts:15|
|steeringMode、followUpMode|"one-at-a-time"|agent/agent.ts:247|
|transport|"auto"|agent/agent.ts:251|
|toolExecution|"parallel"|agent/agent.ts:253|
|initialState.model|id 为 "unknown"、上下文窗口为 0 的占位模型|agent/agent.ts:57|
|initialState.thinkingLevel|"off"|agent/agent.ts:93|



不带选项构建的 Agent 没有模型，也没有调用模型的方式。构造函数位于 agent/agent.ts:230–254。



如果 `initialState.messages` 不是以系统消息开头，就会在前面添加 `createInitialSystemMessage(systemPrompt, tools)`，除非两者都为空（agent/agent.ts:85）。`state.systemPrompt` 是一个 getter，通过重放对话记录中的系统消息得到值；它没有 setter。给 `state.tools` 或 `state.messages` 赋值时，会复制顶层数组（agent/agent.ts:97）。有两个方法可以启动运行：

- `prompt(input, images?)` 接受字符串、单条消息或数组。若在运行期间调用，它会抛出 `Agent is already processing a prompt. Use steer() or followUp() to queue messages, or wait for completion.`（agent/agent.ts:376）

- `continue()` 在对话记录只有系统消息时抛出 `No messages to continue from`。如果最后一条消息是助手回复，它会取出并清除Steering队列中的待处理消息，再运行这些消息；如果没有，则尝试follow-up队列；如果两者都没有，则抛出 `Cannot continue from message role: assistant`。否则，它调用 `runAgentLoopContinue`（agent/agent.ts:384）

    

<BookFigure id="3.4" />

> isStreaming 在最后一个监听器返回后才会清除，而不是在发出 agent_end 时清除。agent/agent.ts 的示意图；数字为行号。步骤3对每个事件运行一次。步骤4在 catch 中运行，并自行发出收尾事件；步骤5在 finally 中运行。
> 
> 



`processEvents`（agent/agent.ts:565）先归约状态，再按订阅顺序等待每个监听器。因此，慢监听器会拖慢循环。

|<strong>事件</strong>|<strong>状态变化</strong>|
|---|---|
|`message_start`、`message_update`|`streamingMessage = 该消息`|
|`message_end`|<strong>清除 `streamingMessage`；将消息推入 messages</strong>|
|`tool_execution_start`|将 `toolCallId` 添加到 `pendingToolCalls`（一个新的 Set）|
|`tool_execution_end`|从 `pendingToolCalls`（一个新的 Set）中移除 toolCallId|
|`turn_end`|如果助手消息带有 errorMessage，就设置它|
|`agent_end`|清除 streamingMessage|



状态在监听器运行之前更新，因此监听器读到的始终是事件之后的状态。processEvents 位于 agent/agent.ts:565–603。



`handleRunFailure`（agent/agent.ts:532）处理抛出异常的运行，例如某个钩子违反了不得抛出异常的契约。它构建一条助手消息，文本为空、usage 为零；若中止信号已触发，stopReason 为 "aborted"，否则为 "error"；抛出的消息作为 errorMessage。随后，它为该消息发出 message_start、message_end、turn_end 和 agent_end，因此订阅者始终能看到运行被关闭。



> <strong>易踩的坑</strong>
> 
> 合成的失败运行，并不是一个结构完备的运行。handleRunFailure 不会发出 agent_start 或 turn_start，且它的 agent_end 只携带失败消息，不携带运行在抛出异常之前产生的消息。配对 start 和 end，或根据 agent_end.messages 重建对话记录的订阅者，必须处理这种情况。
> 
> 



`abort()` 中止当前运行的信号。waitForIdle() 在运行及其所有监听器都结束时完成。reset() 在运行期间会抛出异常；否则，它只保留当前系统消息，并清空两个队列（agent/agent.ts:355）。



> 这对你意味着什么：
> 
> - 通过 agent_end 了解循环已停止发出事件；通过 waitForIdle() 了解智能体已空闲
> 
> - 保持监听器快速执行：循环进入下一步之前，会逐个等待监听器
> 
> - 当顺序重要时，从 role 为 toolResult 的 message_end 事件读取工具结果，而不是从 tool_execution_end 读取
> 
> - 在编码智能体会话内部，等待 agent_settled（“从 prompt() 到 agent_settled”，原书第67页），而不是 agent_end
> 
> 



> 来源：agent/types.ts（AgentEvent、AgentState）；agent/agent.ts（defaultConvertToLlm、DEFAULT_MODEL、createMutableAgentState、Agent 构造函数、prompt、continue、reset、createLoopConfig、runWithLifecycle、handleRunFailure、finishRun、processEvents）；agent/stream-fn.ts（getDefaultStreamFn）；agent/agent-loop.ts（事件发出位置）；ai/utils/transcript.ts（createInitialSystemMessage）；CA/src/core/sdk.ts:393；research/capture/one-turn.mjs；research/out/one-turn.txt（§events、§session-jsonl）；research/capture/agent-loop-queues.mjs；research/out/agent-loop-queues.txt
> 
>
