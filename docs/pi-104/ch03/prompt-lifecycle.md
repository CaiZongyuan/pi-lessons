---
title: "从 prompt() 到 agent_settled"
description: "Pi 1.0.4 · 3.4 · 原书第 67–73 页"
---

<div class="section-kicker">3.4 / THE AGENT LOOP</div>

# 从 prompt() 到 agent_settled

---

<strong>一次 `session.prompt()` 调用可能运行智能体循环多次：先为提示运行一次，再为每次重试、溢出恢复和排队消息重新运行。agent_end 结束其中一次运行；agent_settled 结束这次调用。</strong>



<strong>`AgentSession.prompt()` 是键入文本转化为运行的位置，也是终端 UI、打印模式、RPC 和 SDK 共同使用的入口</strong>（“运行模式”，原书第127页）。本节跟踪一条提示在循环开始之前经历的检查，再跟踪运行后的驱动器如何决定是否再次运行：自动重试、压缩、队列，以及 `agent_before_settle` 边界。最后介绍模型与思考控制、用户 bash，以及完整的 `AgentSessionEvent` 列表。

## prompt() 流程



`prompt(text, options)`（CA/src/core/agent-session.ts:1954）有三种不启动运行就返回的路径：<strong>已处理、已排队或抛出异常</strong>；只有一种路径会启动运行。图3.7（原书第68页）按代码执行顺序列出了检查。



<BookFigure id="3.7" />

> 即使智能体正在流式输出，扩展命令也会运行；其他输入则排队或等待。CA/src/core/agent-session.ts:1954–2097，首次匹配即生效；带引号的值是传入 preflightResult 的 PromptDisposition（CA/src/core/agent-session.ts:301）。步骤10中的第一条消息，是 _preparePromptAndToolLoadout 生成的系统提示词补丁，仅在分节发生变化时存在。
> 
> 



这种顺序会产生实际影响。扩展命令的尝试早于压缩检查和流式输出检查，因此 `/name` 命令随时可用。input 事件看到的是技能和模板展开之前的原始文本（CA/src/core/agent-session.ts:1978）。before_agent_start 在图像规范化之前运行，因此切换模型的处理器也决定了图像缩放配置（CA/src/core/agent-session.ts:2045）。在 agent_settled 监听器运行期间发出的提示，会推迟到它们返回之后（CA/src/core/agent-session.ts:1955）。



其他入口汇入同一套机制：

- `steer(text) / followUp(text)`：运行 input 事件和展开处理，然后排队。它们会抛出 `Extension command "/<name>" cannot be queued. Use prompt() or execute the command when not streaming.`（CA/src/core/agent-session.ts:2260）

- `sendUserMessage(content, {deliverAs})`：以 source: "extension" 调用 prompt()，expandPromptTemplates 默认为 false（CA/src/core/agent-session.ts:2375）

- `sendCustomMessage(msg, {triggerTurn, deliverAs})`：deliverAs: "nextTurn" 会将消息保留到下一次提示；流式输出期间，消息会作为Steering或follow-up投递；空闲且设置了 triggerTurn 时，它会启动运行；否则，只追加消息，不启动运行（CA/src/core/agent-session.ts:2279）

- `clearQueue()`：清空两个队列，并以文本形式返回 {steering, followUp}，“便于在用户中止时恢复到编辑器”（CA/src/core/agent-session.ts:2383）

## 运行后的驱动器



`_runAgentPrompt`（CA/src/core/agent-session.ts:1808）用一个循环包装 `agent.prompt()`，在每次运行之后决定是否调用 `agent.continue()`。



运行，然后持续进行，直到没有任何内容要求继续（CA/src/core/agent-session.ts:1817）：

```ts
try {
    await this.agent.prompt(messages);
    while (!this._agentRunAbortRequested) {
    if (await this._handlePostAgentRun()) {
    if (this._agentRunAbortRequested) break;
    await this.agent.continue();
    continue;
    }
    if (this._agentRunAbortRequested || !(await this._runBeforeSettleBoundary()))
    break;
    if (this._agentRunAbortRequested) break;
    await this.agent.continue();
    }
} finally {
    if (this._agentRunAbortRequested) this._finishCancelledRetry();
    this._failedResponse = undefined;
    this._runSystemPromptOptions = undefined;
    this._flushPendingBashMessages();
    this._flushPendingCustomMessages();
    await this._emitAgentSettled();
}
```



第1817–1836行，内容未改动。



`_handlePostAgentRun`（CA/src/core/agent-session.ts:1839）在以下三种情况下返回 true，表示再次运行，并按此顺序检查：

1. 最后一条助手消息是可重试错误，且 `_prepareRetry` 已安排重试

2. `_checkCompaction` 在溢出或可恢复的 length 停止之后执行了压缩，并要求继续被打断的轮次（“压缩与分支摘要”，原书第92页）

3. 队列中仍有消息，例如循环取完两个队列后，agent_end 处理器又加入的消息



当它返回 false 时，`_runBeforeSettleBoundary` 通过 `agent_before_settle` 事件，让扩展作出最后决定（CA/src/core/agent-session.ts:1879）。处理器可以追加条目并要求继续；只有当投影后的上下文能够继续时，驱动器才会继续，否则会报告 `agent_before_settle requested continuation without runnable model context`。如果没有处理器，则只有存在排队消息时才会继续。



<BookFigure id="3.8" />

> 一条提示、两次运行、两个 agent_end、一个 agent_settled。按代码发出顺序绘制的重试提示示意图，并非采集结果；省略了消息和轮次事件。auto_retry_end 来自第二次运行中助手消息的 message_end（CA/src/core/agent-session.ts:1163），因此早于该次运行的 agent_end。不需要重试的提示只有一次运行和一个 agent_end，如图3.3（原书第58页）所示。
> 
> 

## 自动重试



当 pi-ai 的 `isRetryableAssistantError` 判定失败响应可重试，且它不是由压缩机制处理的上下文溢出时，该响应才可重试（CA/src/core/agent-session.ts:1694）。isRetryableAssistantError 要求 stopReason 为 "error"，且 errorMessage 匹配可重试提供商模式，同时不匹配不可重试限制模式（ai/utils/retry.ts:250；“身份验证、费用、重试与模型目录”，原书第41页）。



|<strong>设置</strong>|<strong>默认值</strong>|<strong>作用</strong>|
|---|---|---|
|retry.enabled|true|开启或关闭智能体级重试|
|retry.maxRetries|3|首次失败后的尝试次数|
|retry.baseDelayMs|2000|第1次重试之前的延迟|
|retry.maxAgentDelayMs|60000|任意单次延迟的上限|



三次重试分别等待 2 s、4 s 和 8 s。getRetrySettings 位于 CA/src/core/settings-manager.ts:1000；延迟为 baseDelayMs × 2^(attempt − 1)，上限为 maxAgentDelayMs（ai/utils/retry.ts:126）。随软件提供的 CA/docs/settings.md 设置表与此一致。



`_prepareRetry`（CA/src/core/agent-session.ts:3747）递增尝试计数器，并发出 auto_retry_start {attempt, maxAttempts, delayMs, errorMessage}。随后，它通过 replacement 为 null 的 context_edit 条目（_omitRecoveryAttempt），向模型隐藏失败消息：这次尝试仍保留在原始 JSONL 中，但从投影中消失（“会话：JSONL 树”，原书第86页）。经过可中止的等待后，驱动器调用 agent.continue()。如果所选模型为虚拟模型，该请求会以 reason "retry" 路由，并将失败消息作为 failed 传入（CA/src/core/agent-session.ts:810）。



尝试以三种方式之一结束。后续响应若不是错误，会发出 `auto_retry_end {success: true}`。尝试次数耗尽时，发出 `auto_retry_end {success: false, finalError}`（CA/src/core/agent-session.ts:1860）。若在等待期间中止，则发出 `finalError: "Retry cancelled"` 的 auto_retry_end（CA/src/core/agent-session.ts:3739）。



如果客户端需要知道“模型已完成回答”，应等待 agent_settled。如果需要知道“本次尝试失败”，则读取 agent_end 上的 willRetry：true 表示后面还有一次运行。

## 模型与思考控制



`setModel(model, {persist})`（CA/src/core/agent-session.ts:2463）在没有身份验证信息时抛出 `No API key for <provider>/<id>`。随后，它设置 agent.state.model，追加 model_change 条目，可选择保存默认模型，应用思考级别，并在模型发生变化时发出扩展事件 model_select。级别按以下顺序选择：显式级别（仅限限定范围内的模型）、按模型设置、默认级别设置、当前级别，最后为 "medium"（CA/src/core/agent-session.ts:2655）。



`setThinkingLevel(level, {persist})`（CA/src/core/agent-session.ts:2598）将级别限制在模型支持的范围内。只有限制后的级别不同于当前级别时，才会追加 thinking_level_change、发出 thinking_level_changed，并触发扩展事件 thinking_level_select。设置 persist 时，它保存的是请求的级别，而非限制后的级别。



`cycleModel(direction)`（CA/src/core/agent-session.ts:2505）在限定范围内（--models 或 enabledModels）当前可用的模型中循环切换；如果没有限定范围，则在所有可用模型中切换。候选模型至多一个时，它返回 undefined。



运行期间所作的更改，在下一轮生效，而不是影响当前请求。prepareNextTurn 会向循环返回当前的 agent.state.model 和 thinkingLevel（“AgentSession：组装运行时”，原书第61页）。

## 用户 bash：!cmd 和 !!cmd



在编辑器中，`!cmd` 运行 shell 命令，而 `!!cmd` 运行命令时会设置 `excludeFromContext`（CA/src/modes/interactive/interactive-mode.ts:3327）。首先发出扩展事件 user_bash 的是模式，而不是会话（CA/src/modes/interactive/interactive-mode.ts:6956）。处理器可以返回完整结果，由 recordBashResult 记录，而不实际运行任何内容；也可以返回替代本地执行的操作，例如通过 SSH 或在 VM 中运行。RPC 模式对其 bash 命令采用相同方式（CA/src/modes/rpc/rpc-mode.ts:562）。



`executeBash(command, onChunk?, {excludeFromContext, id, operations})`（CA/src/core/agent-session.ts:3826）会在单独的一行中前置 shellCommandPrefix 设置，在会话的工作目录中运行命令，并为每个输出块发出 bash_execution_update {id, delta}。随后，recordBashResult 存储一条 BashExecutionMessage。如果智能体正在流式输出，则先保留该记录，在运行收尾时或下一次提示之前追加，因此它绝不会落在工具调用和其结果之间（CA/src/core/agent-session.ts:3877）。



<strong>`!!cmd` 的输出会显示并保存，但绝不会发送给模型</strong>：convertToLlm 会丢弃设置了 excludeFromContext 的 bashExecution 消息（“AgentSession：组装运行时”，原书第61页）。

## AgentSessionEvent



<strong>`AgentSessionEvent`</strong>（CA/src/core/agent-session.ts:191）<strong>在 AgentEvent 事件流的基础上作了两项修改，并增加了十二种自身事件。通过 `ctx.executeTool()` 发起的调用，其工具执行事件携带 `parentToolCallId`；agent_end 则增加 willRetry。</strong>

|<strong>事件</strong>|<strong>载荷</strong>|<strong>含义</strong>|
|---|---|---|
|`agent_end`|messages, willRetry|一次底层运行结束；若后续有自动重试，则 willRetry 为真|
|`agent_settled`|—|prompt() 已没有剩余自动工作|
|`queue_update`|steering: string[], followUp: string[]|两个队列当前的完整文本|
|`compaction_start`|reason: "manual" \| "threshold" \| "overflow"|压缩开始|
|`compaction_end`|reason, result, aborted, willRetry, errorMessage?|压缩完成、失败或被中止|
|`entry_appended`|entry|追加了非消息条目（见“AgentSession：组装运行时”，原书第61页）|
|`session_info_changed`|name|显示名称已设置或清除|
|`thinking_level_changed`|level|实际生效的思考级别已改变|
|`auto_retry_start`|attempt, maxAttempts, delayMs, errorMessage|已安排重试|
|`auto_retry_end`|success, attempt, finalized?|重试序列结束|
|summarization_retry_sched/_attempt_start/_finished|尝试数据；source 为 "compaction" 或 "branchSummary"|压缩请求或分支摘要请求的重试|
|`bash_execution_update`|id?, delta|一块用户 bash 输出|



十种智能体事件之上，还有十二种会话事件。依据 CA/src/core/agent-session.ts:191–232 的 AgentSessionEvent 联合类型；三种 summarization_retry_\* 类型共用一行。“RPC 模式与 SDK”（原书第133页）展示了它们在线路上传输时的形式。



> 这对你意味着什么：
> 
> - 对每一个可能在运行中途到达的 prompt()，都传入 streamingBehavior；没有它，调用会抛出异常
> 
> - 将 agent_settled 视为空闲，将 agent_end 视为一次尝试结束
> 
> - 在设置中调整 retry.\*，而不是由客户端重试；Pi 已经会向模型隐藏失败尝试
> 
> - 拦截 user_bash，可将 ! 命令转移到另一台机器；executeBash 自身不会发出该事件
> 
> 



> 来源：CA/src/core/agent-session.ts（AgentSessionEvent、PromptOptions、PromptDisposition、prompt、_runInputHandlers、steer、followUp、_throwIfExtensionCommand、sendCustomMessage、sendUserMessage、clearQueue、_runAgentPrompt、_handlePostAgentRun、_runBeforeSettleBoundary、_isRetryableError、_prepareRetry、_finishCancelledRetry、_omitRecoveryAttempt、setModel、cycleModel、setThinkingLevel、_getThinkingLevelForModelSwitch、executeBash、recordBashResult、_flushPendingBashMessages）；CA/src/core/settings-manager.ts:987、1000；CA/src/core/defaults.ts:3；ai/utils/retry.ts（retryDelayMs、isRetryableAssistantError）；CA/src/modes/interactive/interactive-mode.ts（提交处理器、handleBashCommand）；CA/src/modes/rpc/rpc-mode.ts:562；CA/docs/settings.md（retry.\*）
> 
>
