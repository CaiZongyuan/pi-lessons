---
title: "AgentSession：组装运行时"
description: "Pi 1.0.4 · 3.3 · 原书第 61–66 页"
---

<div class="section-kicker">3.3 / THE AGENT LOOP</div>

# AgentSession：组装运行时

---

<strong>AgentSession 通过填充钩子，把通用 Agent 变成编码智能体。其中最重要的钩子，会在每次请求之前，用会话文件的投影替换智能体的消息，因此决定模型看到什么的是文件，而不是内存。</strong>



<strong>AgentSession</strong>（CA/src/core/agent-session.ts，4,383 行）<strong>包装一个 Agent，并添加持久化、模型与思考控制、重试、压缩、用户 bash、树导航、工具注册表、系统提示词和扩展分发。本节展示 `sdk.ts` 如何构建这一对对象，以及编码智能体添加的四种消息角色如何传达给模型。随后介绍会话安装在智能体上的六个钩子，以及将各个事件写入会话文件的处理器。</strong>

## 在 sdk.ts 中构造



<strong>`createAgentSession` 先构建 Agent，再围绕它构建 `AgentSession`</strong>（CA/src/core/sdk.ts:393）。



编码智能体运行的 Agent（CA/src/core/sdk.ts:393，TS）：

```js
const agent = new Agent({
  initialState: {
    systemPrompt: "",
    model,
    thinkingLevel,
    tools: [],
    messages: existingSession.messages,
  },
  convertToLlm: convertToLlmWithBlockImages,
  streamFn: async (model, context, options) => {
    const requestOptions = buildRequestOptions(model, options);
    // ...
    if (options?.sessionId === sessionManager.getSessionId()) {
      cacheWarmer.start(
        { model, context, options: requestOptions },
        cacheContextIsCurrent(model)
      );
    }
    return modelRuntime.streamSimple(model, context, requestOptions);
  },
  onPayload: transformProviderPayload,
  onResponse: handleProviderResponse,
  onProviderStreamEvent: handleProviderStreamEvent,
  sessionId: sessionManager.getSessionId(),
  transformContext: async (messages) => {
    const runner = extensionRunnerRef.current;
    if (!runner) return messages;
    
    return runner.emitContext(messages);
  },
  steeringMode: settingsManager.getSteeringMode(),
  followUpMode: settingsManager.getFollowUpMode(),
  transport: settingsManager.getTransport(),
  thinkingBudgets: settingsManager.getThinkingBudgets(),
  maxRetryDelayMs: settingsManager.providerRetrySettings().maxRetryDelayMs,
});
```

> 第393–428行。… 代替了一段关于缓存预热的五行注释。
> 
> 



提示词和工具最初为空是刻意设计的：会话会在第一次提示时，将它们作为系统消息添加（“从 prompt() 到 agent_settled”，原书第67页）。`buildRequestOptions`（CA/src/core/sdk.ts:322）添加超时设置（httpIdleTimeoutMs，其中 0 表示 2,147,483,647 ms）、提供商级别的 maxRetries 和 maxRetryDelayMs，以及一个 transformHeaders；后者合并归属标头，并运行扩展的 before_provider_headers 事件。三个 on… 回调分别运行扩展事件 before_provider_request、after_provider_response 和 provider_stream_event（“扩展事件与上下文”，原书第120页）。这里没有设置 toolExecution，因此智能体保留默认的 "parallel"。



构造后，新会话会追加 model_change 和 thinking_level_change 条目（CA/src/core/sdk.ts:436）。它们是采集的会话文件 research/out/one-turn.txt 中的第2行和第3行。

## 四种自定义角色



CA/src/core/messages.ts 通过声明合并扩展 `CustomAgentMessages`（CA/src/core/messages.ts:70）：



编码智能体添加的角色（CA/src/core/messages.ts:70）：

```ts
declare module "@earendil-works/pi-agent-core" {
    interface CustomAgentMessages {
    bashExecution: BashExecutionMessage;
    custom: CustomMessage;
    branchSummary: BranchSummaryMessage;
    compactionSummary: CompactionSummaryMessage;
    }
}
```

> 第70–77行，内容未改动。
> 
> 



`convertToLlm`（CA/src/core/messages.ts:148）将它们各自转化为用户消息：

|<strong>角色</strong>|<strong>来源</strong>|<strong>对模型呈现为</strong>|
|---|---|---|
|`bashExecution`<br>|用户的 `!cmd`<br>|用户文本：Ran（已运行）、用反引号包裹的命令、放在围栏代码块中的输出或 (no output)（无输出），然后是 (command cancelled)（命令已取消）或 Command exited with code N（命令退出，退出码为 N），再接 [Output truncated. Full output: path]（输出已截断，完整输出见 path）；使用 !! cmd 时丢弃|
|custom|扩展|内容相同的用户消息；字符串变为一个文本块|
|branchSummary|树导航|用户文本前缀为 The following is a summary of a branch that this conversation came back from:（以下是这段对话返回前所在分支的摘要：），再接 +...\</summary\>|
|compactionSummary<br>|压缩|用户文本前缀为 The conversation history before this point was compacted into the following summary:（此处之前的对话历史已压缩成以下摘要：），再接 +...\</summary\>|
|system、user、assistant、toolResult|循环|原样传递|



编码智能体的每种角色，要么以用户消息的形式传达给模型，要么完全不传达。`bashExecutionToText` 和 `convertToLlm` 位于 CA/src/core/messages.ts:82–196；前缀为第11–24行的常量。



sdk.ts 又包装了一次该函数。当 images.blockImages 设置开启时，用户消息或工具结果消息中的每个图像块都会变为文本 `Image reading is disabled.`，连续的占位文本会合并为一个（CA/src/core/sdk.ts:279）。每次调用都会读取该设置，因此更改会在下一次请求时生效。

## Agent 上的六个钩子



构造函数订阅智能体，并按以下顺序安装六个钩子（CA/src/core/agent-session.ts:501）：



<BookFigure id="3.5" />

> <strong>The session owns the agent’s hooks; the agent owns nothing but the loop. 会话拥有智能体的钩子；智能体只拥有循环。</strong>CA/src/core/agent-session.ts，构造函数位于第474–514行；数字为每个安装器所在的行。每个安装器都会保留先前的钩子并调用它，因此，两个 transformContext 投影会在 sdk.ts 中设置的扩展 context 处理器之后运行。高亮的钩子使会话文件成为权威来源。
> 
> 



<strong>工具钩子将 Pi 的扩展事件映射到循环的钩子契约。</strong>`_beforeToolCall` 返回扩展 `tool_call` 处理器返回的内容，因此 `{block: true}` 会阻止调用；如果扩展抛出的不是 Error，则会以 `Extension failed, blocking execution: …` 重新抛出（CA/src/core/agent-session.ts:667）。`_afterToolCall` 运行 tool_result 处理器，然后规范化 content 中的图像，包括扩展注入的图像（CA/src/core/agent-session.ts:692）。



<strong>请求投影是不变量。在每次请求之前，prepareRequest 都会构建会话文件的投影，并用它替换上下文中的消息</strong>（CA/src/core/agent-session.ts:781）。<strong>该投影就是“会话：JSONL 树”</strong>（原书第86页）所描述的内容：应用压缩和 context_edit 条目后的当前分支。当所选模型为虚拟模型时，同一钩子会请求模型运行时为这一次请求选择路由；若超过路由目标模型的上下文窗口，则先进行压缩（CA/src/core/agent-session.ts:802）。



> <strong>易踩的坑</strong>
> 
> 给 `session.agent.state.messages` 赋值，不会改变模型看到的内容。下一次 `prepareRequest` 会丢弃智能体的消息，改用会话投影。要改变上下文，应通过会话追加条目，例如自定义消息、`context_edit` 或压缩；如果需要让 `agent.state.messages` 在下一次请求之前就保持一致，再调用 `session.refreshContext()`。
> 
> 



`prepareNextTurn` 负责轮次之间的工作（CA/src/core/agent-session.ts:892）。它根据投影重建上下文；若跨过阈值，则先压缩（“压缩与分支摘要”，原书第92页）。它会对比系统提示词分节与对话记录中的差异；如果发生变化，就返回补丁消息，并应用工具配置。最后，它返回 `this.agent.state.model` 和 `thinkingLevel`：运行中途切换模型，正是这样传递到下一轮的。

## _handleAgentEvent 中的持久化



`_handleAgentEvent`（CA/src/core/agent-session.ts:1090）<strong>是最先安装的智能体监听器。对每个事件，它按固定顺序做六件事：</strong>



<BookFigure id="3.6" />

> <strong>Listeners see a message before it is on disk.  监听器在消息落盘之前就会看到它。</strong>CA/src/core/agent-session.ts:1090–1183。扩展先运行，并被等待；公共监听器以同步方式调用；会话文件最后写入。如果扩展的 message_end 处理器返回替代内容，就会原地修改消息，因此步骤5持久化的是替换后的内容。
> 
> 



步骤5通过 `appendMessage` 追加 system、user、assistant 和 toolResult 消息，通过 `appendCustomMessageEntry` 追加 custom 消息（CA/src/core/agent-session.ts:1134）。其他三种角色在别处写入：bash 结果由 `recordBashResult` 写入，摘要由压缩和树导航写入。重试后成功的助手消息（stopReason 不为 "error" 的任何消息）会发出 success: true 的 `auto_retry_end`，并重置重试计数器（CA/src/core/agent-session.ts:1163）。



步骤6之所以存在，是因为会校验消息顺序的提供商，不允许在工具调用和其结果之间插入消息。运行中途以 triggerTurn: false 发送的自定义消息会保留在 `_pendingCustomMessages` 中，并在 turn_end 时，于该轮次的工具结果之后追加（CA/src/core/agent-session.ts:2306）。



> <strong>文档 ≠ 代码</strong>
> 
> docs/json.md 说，当“扩展通过 `pi.appendEntry()` 追加自定义会话条目”时，会触发 `entry_appended`。代码会在五个位置发出该事件：`appendEntry`（CA/src/core/agent-session.ts:3396）、扩展边界草稿（CA/src/core/agent-session.ts:1015）、用于隐藏失败尝试的 context_edit 条目（CA/src/core/agent-session.ts:1237）、虚拟模型状态（CA/src/core/agent-session.ts:822），以及缓存预热器（CA/src/core/agent-session.ts:485）。消息条目从不触发该事件：采集过程在一次提示中追加了五条消息条目，却没有发出任何 entry_appended（research/out/one-turn.txt）。
> 
> 



> 这对你意味着什么：
> 
> - 通过追加会话条目来改变模型看到的内容，绝不要编辑 agent.state.messages
> 
> - 不要在 message_end 监听器中读取会话文件，并期待那条消息已经在那里
> 
> - 使用扩展 message_end 的返回结果，在消息持久化之前改写它
> 
> - 通过 message_end 观察消息条目；entry_appended 只覆盖其他类型
> 
> 



> 来源：CA/src/core/sdk.ts（convertToLlmWithBlockImages、buildRequestOptions、new Agent、初始 model_change/thinking_level_change）；CA/src/core/messages.ts（BashExecutionMessage、CustomMessage、BranchSummaryMessage、CompactionSummaryMessage、bashExecutionToText、convertToLlm）；CA/src/core/agent-session.ts（构造函数、_installAgentToolHooks、_beforeToolCall、_afterToolCall、_installAgentRequestProjection、_installAgentBoundaryHooks、_installAgentNextTurnRefresh、_installHiddenDeclarationsProjection、_installAgentForcedPromptProjection、_handleAgentEvent、_emitExtensionEvent、sendCustomMessage、appendEntry 绑定）；CA/docs/json.md（队列与状态事件）；research/out/one-turn.txt（§events、§session-jsonl）
> 
>
