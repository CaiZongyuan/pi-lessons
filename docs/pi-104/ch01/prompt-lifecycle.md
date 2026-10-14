---
title: 一个提示的生命周期
---

<div class="section-kicker">1.3 / MODEL</div>

# 一个提示的生命周期

---

回答一个需要读取一次文件的问题，会产生两次模型调用、29 个会话事件和 8 行 JSONL。提示先写入磁盘，再送达模型；运行到 `agent_settled` 才结束，而不是到 `agent_end` 就结束。



你输入“What does hello\.txt say?”（`hello.txt` 写了什么？），然后按 Enter。在回答出现之前，Pi 已经运行了扩展钩子、写入会话文件、调用模型两次、读取文件，并又追加了三行。本节通过与源代码核对的 22 个步骤，追踪这一输入在稳定版 CLI 中的全过程。随后展示采集工具包针对同一交互记录下来的真实事件流和会话文件。每一步都指出详细解释该步骤的章节；请先读本节，将它作为地图。

## 样本



采集工具包使用 `pi-ai` 的 `faux` 提供商驱动真实的 `AgentSession`，因此不涉及网络或 API 密钥（`research/capture/one-turn.mjs`）。`faux` 模型按脚本给出两次回复。第一次是文本“Reading it\.”，加上针对 `hello.txt` 的 `read` 调用，停止原因为 `toolUse`。第二次是“It says: Hello from the capture kit\.”。脚本订阅会话，调用 `session.prompt()`，将每个事件及会话文件的每一行转储到 `research/out/one-turn.txt`。它在 Node 26\.10\.0 下运行，使用从 `28dcce2` 构建的 `pi-coding-agent` 1\.0\.4。在交互式 CLI 中，同一个 `session.prompt()` 调用来自编辑器；下面的步骤就从这里开始。

## 进入循环：步骤 1–12



模型看到提示之前，提示已经写入磁盘。这是稳定版 CLI 处理一个提示的步骤 1–12。实线箭头表示调用，虚线箭头表示提供商流，点线箭头表示递交给 `AgentSession` 的智能体事件。依据提交 `28dcce2` 的 `CA/src/core/agent-session.ts`、`agent/agent-loop.ts` 和 `CA/src/core/model-runtime.ts` 核验。示意图。



<BookFigure id="1.4" />

> 一个提示进入智能体循环的步骤 1–12
> 
> 

### <strong>1 · 提交</strong>



编辑器的 `onSubmit` 自行处理内置斜杠命令和以 `!` 开头的 bash 行。其他内容进入 `InteractiveMode` 的主循环，它会等待 `session.prompt(userInput)`（`CA/src/modes/interactive/interactive-mode.ts:1247`）。Print、JSON 和 RPC 模式调用同一个方法，见运行模式（原书第 127 页）。

### <strong>2 · 提示处理流水线</strong>



`AgentSession.prompt()` 按固定顺序执行（`CA/src/core/agent-session.ts:1954`）。若输入是 `/foo` 这样的扩展命令，执行后直接返回。然后输入处理器可以改写或消费文本。接着展开技能命令和提示模板。如果已有运行正在流式输出，文本会作为引导消息或后续消息入队，`prompt()` 随即返回。否则，会检查模型及其身份验证，检查上一个回答是否需要压缩，再运行 `before_agent_start` 处理器；这些处理器可以添加消息或替换系统提示（`CA/src/core/agent-session.ts:2048`）。各阶段见“从 `prompt()` 到 `agent_settled`”（原书第 67 页），各钩子见“扩展事件与上下文”（原书第 120 页）。

### <strong>3 · 交接</strong>



<strong>`prompt()` 构建用户消息；</strong>若系统提示的分节与对话记录中的不同，则在前面插入一条系统消息（`CA/src/core/agent-session.ts:2091`）。它在 `_runAgentPrompt` 内调用 `agent.prompt(messages)`（`CA/src/core/agent-session.ts:1818`）。系统提示是对话记录中的一条消息，而非请求字段，见系统提示词构建（原书第 75 页）。

### <strong>4 · 循环开始</strong>



<strong>`runAgentLoop` 将该系统消息上的工具变化声明为 `toolsAdded`，随后发出 `agent_start`、`turn_start`，以及每条新消息各自的一对 `message_start` / `message_end`</strong>（`agent/agent-loop.ts:117`）。循环本身见智能体循环（原书第 49 页），事件见智能体事件与 `Agent` 类（原书第 57 页）。

### <strong>5 · 第一次写入</strong>



<strong>`AgentSession` 接收每个智能体事件，先传给扩展，再传给订阅者；遇到 `message_end` 时将消息追加到会话</strong>（`CA/src/core/agent-session.ts:1127`）。<strong>只有出现用户或助手消息后，会话文件才会存在</strong>（`CA/src/core/session-manager.ts:1166`）。<strong>在用户消息的 `message_end` 时，`SessionManager` 创建文件，将此前保留在内存中的五个条目一次写入</strong>，见会话：JSONL 树（原书第 86 页）。

### <strong>6 · 请求投影</strong>



<strong>每次调用模型之前，循环都会调用 `prepareRequest`</strong>（`agent/agent-loop.ts:219`）。<strong>`AgentSession` 安装的实现会用会话树的一份投影替换上下文</strong>（`CA/src/core/agent-session.ts:781`）。<strong>压缩摘要和上下文编辑就在这个投影中生效</strong>，见压缩与分支摘要（原书第 92 页）。

### <strong>7 · 上下文钩子</strong>



`streamAssistantResponse` 先将消息交给 `transformContext`，再交给 `convertToLlm`（`agent/agent-loop.ts:390`）。在 CLI 中，`transformContext` 发出 `context` 扩展事件（`CA/src/core/sdk.ts:418`）。

### <strong>8–9 · 模型调用</strong>



<strong>循环调用流式函数</strong>（`agent/agent-loop.ts:403`）；<strong>SDK 将该函数连接到 `modelRuntime.streamSimple`</strong>（`CA/src/core/sdk.ts:412`）。<strong>`ModelRuntime` 解析提供商及其凭据，再将请求交给提供商的 `streamSimple`</strong>（`CA/src/core/model-runtime.ts:739`）。提供商通过 HTTP 使用十种传输 API 之一进行通信，见提供商与模型（原书第 24 页）、传输 API 与跨提供商交接（原书第 36 页），以及身份验证、费用、重试与模型目录（原书第 41 页）。

### <strong>10–11 · 流式输出</strong>



<strong>提供商返回 `AssistantMessageEvent`：先是 `start`，然后是 `text_*`、`thinking_*` 和 `toolcall_*` 增量，最后是 `done` 或 `error`</strong>，见流式事件协议（原书第 30 页）。<strong>循环将 `start` 转为 `message_start`，将每个增量转为 `message_update`，将 `done` 转为 `message_end`</strong>（`agent/agent-loop.ts:414`）。

### <strong>12 · 第二次写入</strong>



在助手消息的 `message_end` 时，`AgentSession` 将它作为第 6 行追加（`CA/src/core/agent-session.ts:1149`）。

## 经过工具并退出：步骤 13–22



<strong>一次运行在 `agent_settled` 时结束，而不是 `agent_end`。步骤 13–22。`tool_call` 和 `tool_result` 通过 `AgentSession` 安装到智能体上的 `beforeToolCall` 和 `afterToolCall` 钩子到达扩展</strong>（`CA/src/core/agent-session.ts:640`）；图中从调用这些钩子的循环画出箭头。依据提交 `28dcce2` 的 `agent/agent-loop.ts` 与 `CA/src/core/agent-session.ts` 核验。示意图。



<BookFigure id="1.5" />

> 一个提示的工具执行与收束步骤 13–22
> 
> 

### <strong>13–17 · 一批工具调用</strong>



<strong>循环收集回答中的 `toolCall` 块。除非智能体被设置为顺序执行，或者某个被调用工具声明 `executionMode: "sequential"`，否则它们并行运行（`agent/agent-loop.ts:519`）；默认值是 `"parallel"`（`agent/agent.ts:253`）。</strong>对每个调用，循环发出 `tool_execution_start`，验证参数，再运行 `beforeToolCall`，由它触发 `tool_call` 扩展事件；若返回 `{ block: true }`，就直接生成错误结果，不执行工具（`agent/agent-loop.ts:727`）。`execute()` 之后，`afterToolCall` 触发 `tool_result`；其处理器可替换 `content`、`details` 或 `isError`（`agent/agent-loop.ts:864`）。随后是 `tool_execution_end`，以及结果消息的 `message_start` / `message_end`。`read` 工具与其他七个工具见内置工具（原书第 81 页）。

### <strong>18 · 第三次写入</strong>



工具结果是第 7 行。

### <strong>19 · 下一轮次</strong>



<strong>`turn_end` 结束当前轮次</strong>（`agent/agent-loop.ts:287`）。因为回答包含工具调用，内层循环再次运行。步骤 6–12 重复之前，`prepareNextTurn` 给 `AgentSession` 一个压缩和刷新系统提示的机会（`CA/src/core/agent-session.ts:892`）。第二次回答没有工具调用，因此是最后一次回答；它成为第 8 行。

### <strong>20 · 循环结束</strong>



当不再有工具调用、引导消息或后续消息时，循环发出 `agent_end`（`agent/agent-loop.ts:320`）。`AgentSession` 为订阅者在该事件上附加 `willRetry`（`CA/src/core/agent-session.ts:1128`）。

### <strong>21 · 循环之后</strong>



此时 `_runAgentPrompt` 还不会返回。它先检查最后一次回答是否存在可重试错误，然后检查压缩，再检查队列中的消息；只要其中任何一项需要再次运行，就调用 `agent.continue()`（`CA/src/core/agent-session.ts:1839`）。最后，`agent_before_settle` 处理器可以请求继续（`CA/src/core/agent-session.ts:1879`）。这些分支见 `AgentSession`：组装运行时（原书第 61 页）和压缩与分支摘要（原书第 92 页）。

### <strong>22 · 收束</strong>



在 `finally` 块内，`_emitAgentSettled` 先向扩展、再向订阅者发出 `agent_settled`（`CA/src/core/agent-session.ts:1066`），随后 `session.prompt()` 完成。

## 采集到的事件流



这次采集从一次 `session.prompt()` 调用中记录了 29 个事件。每个都是递交给 `session.subscribe()` 的 `AgentSessionEvent`。



<p class="table-caption" data-figure="1.6">FIG. 1.6 · 一个回答完成的提示，逐事件查看 · 原书第 20 页</p>

|<strong>序号</strong>|<strong>毫秒</strong>|<strong>事件</strong>|<strong>详情</strong>|<strong>磁盘上的状态</strong>|<strong>步骤</strong>|
|---|---|---|---|---|---|
|1|1|`agent_start`|||4|
|2|1|`turn_start`|轮次 1||4|
|3–4|1|`message_start` · `message_end`|`system`|保留在内存中|4–5|
|5–6|1|`message_start` · `message_end`|`user`|创建文件：第 1–5 行|4–5|
|7|2|`message_start`|`assistant`||11|
|8–13|2|`message_update` ×6|`text_start` · `text_delta` · `text_end` · `toolcall_start` · `toolcall_delta` · `toolcall_end`||11|
|14|2|`message_end`|`assistant`，`toolUse`|第 6 行|12|
|15|2|`tool_execution_start`|`read`||13|
|16|4|`tool_execution_end`|`read`||17|
|17–18|4|`message_start` · `message_end`|`toolResult`|第 7 行|17–18|
|19|4|`turn_end`|轮次 1||19|
|20|4|`turn_start`|轮次 2||19|
|21|4|`message_start`|`assistant`||11|
|22–25|4|`message_update` ×4|`text_start` · `text_delta` ×2 · `text_end`||11|
|26|4|`message_end`|`assistant`，`stop`|第 8 行|12|
|27|4|`turn_end`|轮次 2||19|
|28|4|`agent_end`|||20|
|29|5|`agent_settled`|||22|



两个轮次，29 个事件，四次写入。“毫秒”是自订阅开始经过的时间。整个运行只耗时 5 毫秒，因为 `faux` 模型按脚本作答；换成真实提供商，事件 7–14 和 21–26 需要等待网络。“步骤”指向图 1\.4（原书第 16 页）与图 1\.5（原书第 18 页）。数据来自 `research/out/one-turn.txt`（`§events`）。每次运行的 `text_delta` 事件数量会变化；事件顺序不会变化。



轮次是循环的基本单位：每个轮次包含一次模型响应，以及该响应所调用的工具。轮次 1 覆盖事件 2–19，轮次 2 覆盖事件 20–27。29 个事件中有十个是 `message_update`，TUI 根据这串增量流重绘。步骤 2、7、14、16 和 21 中的钩子都不会出现在这份列表里。`input`、`before_agent_start`、`context`、`tool_call`、`tool_result` 和 `agent_before_settle` 只分发给 `ExtensionRunner`，并且其中几个在没有注册处理器时会跳过（`CA/src/core/agent-session.ts:651`）。`session.subscribe()` 监听器永远看不到它们，见扩展事件与上下文（原书第 120 页）。

## 磁盘上的八行



会话文件有八行，每行一个 JSON 对象（`research/out/one-turn.txt` 的 `§session-jsonl`）。前三行描述会话，后五行是对话。

|<strong>行</strong>|<strong>类型</strong>|<strong>ID ← 父条目</strong>|<strong>写入时机</strong>|
|---|---|---|---|
|1|`session`，版本 3|`01a10e5a-...`（会话 ID）|事件 6|
|2|`model_change`，`faux/faux-1`|`2cd13c47 ← null`|事件 6|
|3|`thinking_level_change`，`off`|`f99fc4be ← 2cd13c47`|事件 6|
|4|`message`，`system`：5 个分节，4 个 `toolsAdded`|`ff9b46f6 ← f99fc4be`|事件 6|
|5|`message`，`user`|`dd741bf1 ← ff9b46f6`|事件 6|
|<strong>6</strong>|<strong>`message`，`assistant`，`stopReason: "toolUse"`</strong>|<strong>`0f939fd7 ← dd741bf1`</strong>|<strong>事件 14</strong>|
|7|`message`，`toolResult`，`toolCallId: "call_1"`|`81cb0f01 ← 0f939fd7`|事件 18|
|8|`message`，`assistant`，`stopReason: "stop"`|`01f5647e ← 81cb0f01`|事件 26|



每个条目都指明父条目，所以这八行构成一棵树的一条分支。新建会话时，第 2、3 行由 `createAgentSession` 追加到内存中（`CA/src/core/sdk.ts:436`）；它们和第 5 行一起写入文件。`version` 来自 `CURRENT_SESSION_VERSION`（`CA/src/core/session-manager.ts:41`）。数据来自 `research/out/one-turn.txt`（`§session-jsonl`）。



第 6 行包含完整的第一次回答：文本、工具调用、生成它的模型、用量，以及停止原因。



<strong>第 6 行：第一次回答及其工具调用 · `research/out/one-turn.txt` · JSONL</strong>

```json
{
  "type": "message",
  "id": "0f939fd7",
  "parentId": "dd741bf1",
  "timestamp": "2026-10-05T23:16:41.752Z",
  "message": {
    "role": "assistant",
    "content": [
      { "type": "text", "text": "Reading it." },
      { "type": "toolCall", "id": "call_1", "name": "read", "arguments": { "path": "hello.txt" } }
    ],
    "api": "faux",
    "provider": "faux",
    "model": "faux-1",
    "usage": { ... },
    "stopReason": "toolUse",
    "timestamp": 1791242201744,
    "thinkingLevel": "off"
  }
}
```



节选自 `§session-jsonl` 的第 6 行。省略了 `usage` 对象（token 数量，以及 `faux` 提供商的零费用），并将两个内容块各排成一行；键保留存储时的顺序。



条目中有两个时间戳。外层的 `timestamp` 是 `SessionManager` 追加条目时写入的 ISO 字符串。内层的 `message.timestamp` 是自纪元起的毫秒数，由消息的创建者设置，此处即 `faux` 提供商。会话：JSONL 树（原书第 86 页）会逐字段解释每种条目类型。



> <strong>易踩的坑</strong>
> 
> `agent_end` 不是一次运行的终点。在它之后，`AgentSession` 还可能重试失败响应、压缩后继续，或为排队消息启动新一轮运行；这一切仍然发生在同一次 `prompt()` 调用内。等待空闲状态的代码必须等待 `agent_settled`，或等待 `session.prompt()` 完成。把 `agent_end` 视作最终结束前，要先检查它的 `willRetry`。
> 
> 



> <strong>验证</strong>
> 
> 在 `books/pi` 中，针对已构建的检出版本运行 `HOME=$(mktemp -d) node research/capture/one-turn.mjs`。它会打印事件列表，并重写 `research/out/one-turn.txt`。使用空的 `HOME`，可避免你自己的设置和技能影响此次运行。
> 
> 



> 来源：`CA/src/modes/interactive/interactive-mode.ts`（`onSubmit`、运行循环）；`CA/src/modes/print-mode.ts`；`CA/src/modes/rpc/rpc-mode.ts`（`prompt` 命令）。`CA/src/core/agent-session.ts`（`prompt`、`_runAgentPrompt`、`_handleAgentEvent`、`_emitExtensionEvent`、`_installAgentRequestProjection`、`_installAgentToolHooks`）。`CA/src/core/agent-session.ts`（`_beforeToolCall`、`_afterToolCall`、`_installAgentNextTurnRefresh`、`_handlePostAgentRun`、`_runBeforeSettleBoundary`、`_emitAgentSettled`、`AgentSessionEvent`）。`CA/src/core/sdk.ts`（`createAgentSession`：`new Agent`、`streamFn`、`transformContext`、初始条目）；`CA/src/core/model-runtime.ts`（`streamSimple`、`prepareRequest`）。`CA/src/core/session-manager.ts`（`_hasConversation`、`_persist`、`appendMessage`、`CURRENT_SESSION_VERSION`）。`agent/agent.ts`（`prompt`、`toolExecution`、`processEvents`）；`agent/agent-loop.ts`（`runAgentLoop`、`runLoop`、`streamAssistantResponse`、`executeToolCalls`、`prepareToolCall`、`finalizeExecutedToolCall`）。`agent/types.ts`（`AgentEvent`）；`research/capture/one-turn.mjs`；`research/out/one-turn.txt`（`§versions`、`§events`、`§session-jsonl`）。
> 
>
