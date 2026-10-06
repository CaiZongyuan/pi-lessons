A stateless loop that alternates model turns and tool runs, wrapped by a session that persists every step.

一个无状态循环，在模型轮次和工具执行之间交替，外面包一层会话，把每一步都持久化下来。

## 3.1 The agent loop

## 3.1 智能体循环

The loop in pi-agent-core is onefunction with no state ofits own: it streams a response, runs the tool calls, and goes round again while tool results or queued messages give it something to send. It has no turn limit.

pi-agent-core 里的这个循环是一个自身不持有任何状态的函数：它流式输出一段响应，执行这些工具调用，只要工具结果或队列里的消息让它有东西可发，就再转一圈。它没有轮次上限。

Every model call Pi makes during a conversation goes through one function, run Loop in agent/agent-loop.ts. This section gives the types the loop is configured with, walks the loop state by state, separates the two message queues that feed it, and follows a batch of tool calls through preparation, execution and result ordering. agent events and the Agent class (p. 57) lists the events it emits; AgentSession: wiring the runtime (p. 61) shows how the coding agent fills in its hooks.

Pi 在一次对话中发出的每一次模型调用，都经过同一个函数——agent/agent-loop.ts 里的 run Loop。本节先给出配置这个循环所需的类型，再逐个状态地走一遍循环，把喂给它的两个消息队列分开来讲，最后跟着一批工具调用走完准备、执行和结果排序的全过程。「智能体事件与 Agent 类」（第 57 页）列出了它发出的事件；「AgentSession：接好运行时」（第 61 页）展示编码智能体如何填入自己的钩子。

## The package and its types

## 这个包及其类型

@earendil-works/pi-agent-core 1.0.4 is six files and 2,513 lines (2,281 non-blank research/out/stats.txt). It has two layers: a stateless loop that takes a context and a config and emits events, and a stateful Agent class that owns a transcript and two queues.

@earendil-works/pi-agent-core 1.0.4 是六个文件、2,513 行（其中 2,281 行非空，见 research/out/stats.txt）。它有两层：一层是无状态循环，接收一个 context 和一份 config 并发出事件；另一层是有状态的 Agent 类，持有一份记录（transcript）和两个队列。

<table><tr><td>文件</td><td>行数</td><td>内容</td></tr><tr><td>agent/types.ts</td><td>529</td><td>StreamFn、AgentLoopConfig、AgentMessage、AgentTool、AgentEvent、钩子类型</td></tr><tr><td>agent/agent-loop.ts</td><td>940</td><td>agent Loop、agentLoopContinue、run Loop、工具执行、runToolCall</td></tr><tr><td>agent/agent.ts</td><td>613</td><td>Agent：状态归约器、转向队列与后续队列、运行生命周期</td></tr><tr><td>agent/proxy.ts</td><td>406</td><td>stream Proxy，一个供把模型调用路由到自建服务器的应用使用的 StreamFn</td></tr><tr><td>agent/stream-fn.ts</td><td>20</td><td>setDefaultStreamFn、getDefaultStreamFn</td></tr><tr><td>agent/index.ts</td><td>5</td><td>再导出；getDefaultStreamFn 未导出</td></tr></table>

Three files hold the whole runtime. Line counts from wc -l at 28dcce2.

整个运行时都在这三个文件里。行数取自 28dcce2 的 wc -l。

The loop never calls a provider directly. It calls a StreamFn agent/types.ts:33, which has the shape of stream Simple in pi-ai (the streaming event protocol (p. 30)). The contract is written on the type: a stream function “Must not throw or return a rejected promise for request/model/runtime failures”; a failure arrives as a final message with stop Reason "error" or "aborted". The loop passes a normalised transcript in which “the system prompt and tool declarations are carried by the transcript’s system messages, never by context.system Prompt or context.tools” agent/types.ts:23.

这个循环从不直接调用供应商。它调用的是一个 StreamFn（agent/types.ts:33），形态与 pi-ai 里的 stream Simple 相同，也就是流式事件协议（见第 30 页）。契约写在类型上：流式函数“Must not throw or return a rejected promise for request/model/runtime failures”；失败以一条最终消息的形式到达，它的 stop Reason 是“error”或“aborted”。循环传入的是一份规范化过的记录，其中“the system prompt and tool declarations are carried by the transcript’s system messages, never by context.system Prompt or context.tools”（agent/types.ts:23）。

Messages are an open union. AgentMessage is Message | CustomAgentMessages[keyof CustomAgentMessages], and CustomAgentMessages is an empty interface that applications extend by declaration merging agent/types.ts:365. The coding agent adds four roles this way (AgentSession: wiring the runtime (p. 61)).

消息是一个开放联合类型。AgentMessage 是 Message | CustomAgentMessages[keyof CustomAgentMessages]，而 CustomAgentMessages 是一个空接口，应用通过声明合并来扩展它（agent/types.ts:365）。编码智能体正是用这种方式增加了四个角色（见「AgentSession：接好运行时」，第 61 页）。

A tool is a pi-ai Tool plus what the runtime needs to run it agent/types.ts:464:

一个工具就是一个 pi-ai Tool，再加上运行时运行它所需要的东西（agent/types.ts:464）：

label: human-readable name for the UI.

label：给 UI 用的可读名称。

prepare Arguments?(args): a compatibility shim applied to the raw arguments before schema validation.

prepare Arguments?(args)：一个兼容性补丁，在 schema 校验之前施加到原始参数上。

output Schema?: JSON Schema of structured Content in successful results.

output Schema?：成功结果中结构化 Content 的 JSON Schema。

execute(toolCallId, params, signal?, onUpdate?): returns an AgentToolResult: content for the model, details for logs and UI, optional structured Content (not sent to the model), usage, isError and terminate. Calls to onUpdate after the promise settles are ignored agent/types.ts:458.

execute(toolCallId, params, signal?, onUpdate?)：返回一个 AgentToolResult：content 给模型，details 给日志和 UI，可选的 structured Content（不发给模型），以及 usage、isError 和 terminate。promise 落定之后再调用 onUpdate 会被忽略（agent/types.ts:458）。

replay?: "never" or "safe", the recovery policy for an efect whose outcome is unknown.

replay?：`“never”` 或 `“safe”`，用于结果未知的副作用的恢复策略。

execution Mode?: "sequential" or "parallel", a per-tool override of the batch mode.

execution Mode?：`“sequential”` 或 `“parallel”`，对批次模式的逐工具覆盖。

AgentLoopConfig extends SimpleStreamOptions and carries every hook agent/types.ts:193. The thinking level travels in the inherited reasoning field, where "off" is stored as undefined.

AgentLoopConfig 继承 SimpleStreamOptions，并携带全部钩子（agent/types.ts:193）。思考等级放在继承来的 reasoning 字段里，其中“off”存为 undefined。

<table><tr><td>字段</td><td>调用时机</td><td>约定</td></tr><tr><td>model</td><td>—</td><td>下一次请求使用的 model</td></tr><tr><td>convertToLlm(messages)</td><td>每次请求之前</td><td>AgentMessage[] → Message[]；丢掉仅供 UI 的消息；不得抛错</td></tr><tr><td>transform Context?(messages, signal)</td><td>在 convertToLlm 之前</td><td>在 AgentMessage 层裁剪或注入；不得抛错</td></tr><tr><td>getApiKey?(provider)</td><td>每次请求之前</td><td>解析会过期的 token；不得抛错</td></tr><tr><td>prepare Request?</td><td>每次请求之前，包括第一次</td><td>可以为本次及之后的请求替换 context、model 和思考等级</td></tr><tr><td>prepareNextTurn?</td><td>turn_end 之后、下一个 turn_start 之前</td><td>返回 {context?, messages?, model?, thinking Level?}</td></tr><tr><td>finish Turn?</td><td>工具结果之后、turn_end 之前</td><td>返回 {action: &quot;continue&quot;}、{action: &quot;end&quot;}，或者什么都不返回</td></tr><tr><td>getSteeringMessages?</td><td>循环开始、每个轮次之后、prepareNextTurn 之后</td><td>取空转向队列</td></tr><tr><td>getFollowUpMessages?</td><td>内层循环将要退出时</td><td>取空后续队列</td></tr><tr><td>tool Execution?</td><td>—</td><td>&quot;parallel&quot;（默认）或 &quot;sequential&quot;</td></tr><tr><td>beforeToolCall? /afterToolCall?</td><td>每次工具调用</td><td>阻断一次调用；覆盖其结果的字段</td></tr></table>

Every hook is optional except convertToLlm. From AgentLoopConfig in agent/types.ts:193–342.

除了 convertToLlm，每个钩子都是可选的。摘自 agent/types.ts:193–342 的 AgentLoopConfig。

## The loop, state by state

## 逐状态看这个循环

There are two entry points. agent Loop(prompts, context, config, signal, streamFn) agent/agent-loop.ts:38 starts from new prompt messages and returns an EventStream<AgentEvent, AgentMessage[]>. agentLoopContinue(...) agent/agent-loop.ts:71 resumes from the existing context; it throws Cannot continue: no messages in context on an empty context and Cannot continue from message role: assistant when the last message is an assistant reply. Both have run… variants that take an event sink instead of returning a stream, and Agent uses those.

这里有两个入口。agent Loop(prompts, context, config, signal, streamFn)（agent/agent-loop.ts:38）从新的提示词消息出发，返回一个 EventStream<AgentEvent, AgentMessage[]>。agentLoopContinue(...)（agent/agent-loop.ts:71）从已有的 context 接着跑；context 为空时它抛出 Cannot continue: no messages in context，最后一条消息是助手回复时它抛出 Cannot continue from message role: assistant。两者都有 run… 变体，接受一个事件 sink 而不是返回流，Agent 用的就是这些变体。

runAgentLoop agent/agent-loop.ts:102 declares any tool changes in front of the prompts, emits agent_start and turn_start, emits message_start and message_end for each prompt message, and hands over to run Loop agent/agent-

runAgentLoop（agent/agent-loop.ts:102）在提示词之前声明任何工具变更，发出 agent_start 和 turn_start，为每条提示词消息发出 message_start 和 message_end，然后把接力棒交给 agent/agent- 里的 run Loop

![](images/506c08668659c0d65ec99e027f2a8378392c0708c5bbe67892657732bfde0901.jpg)

The loop goes round while something needs a response, and stops only in three places. One run Loop call in agent/agent-loop.ts, schematic; numbers are line numbers at 28dcce2. The heavy amber arrows are the two ways back: the inner loop (tool results or steering) and the outer loop (follow-ups, or a finish Turn that asked to continue). The rose exit is the only one that skips the queues.

只要还有东西需要响应，循环就一直转下去，并且只在三个地方停下。agent/agent-loop.ts 中的一次 run Loop 调用，示意图；图中的数字是 28dcce2 的行号。粗琥珀色箭头是两条回边：内层循环（工具结果或转向）和外层循环（后续消息，或某个要求继续的 finish Turn）。玫红色的出口是唯一会跳过队列的那一个。

Read Fig. 3.1 (p. 51) top to bottom for one turn. The first pass skips prepareNextTurn, because runAgentLoop already emitted turn_start. Every later pass runs it, then emits its own turn_start. Pending messages are injected through declareToolChanges agent/agent-loop.ts:333, which compares the tools the runtime can execute (context.tools) with the tools the transcript has declared. A diference becomes tools Added or tools Removed on a system message: folded into a pending system message if there is one, otherwise a new empty-content system message inserted before the first non-system message. No diference, no message.

自上而下读图 3.1（第 51 页）就是一个轮次。第一次经过会跳过 prepareNextTurn，因为 runAgentLoop 已经发出过 turn_start。之后每一次经过都会执行它，然后发出自己的 turn_start。待处理的消息通过 declareToolChanges（agent/agent-loop.ts:333）注入，它把运行时能执行的工具（context.tools）与记录里已经声明过的工具做比较。有差异就在一条系统消息上生成 tools Added 或 tools Removed：如果已经有一条待处理的系统消息就并进去，否则新建一条内容为空的系统消息，插在第一条非系统消息之前。没有差异就没有消息。

The model boundary is streamAssistantResponse agent/agent-loop.ts:381, and it is short enough to quote:

模型的边界是 streamAssistantResponse（agent/agent-loop.ts:381），它短到可以直接引用：

```javascript
// Apply context transform if configured (AgentMessage[] → AgentMessage[])
let messages = context.messages;
if (config.transform Context) {
    messages = await config.transform Context(messages, signal);
}

// Convert to LLM-compatible messages (AgentMessage[] → Message[])
const llm Messages = await config.convertToLlm(messages);

const llm Context = normalize Context({ messages: llm Messages});

// Resolve API key (important for expiring tokens)
const resolvedApiKey =
(config.getApiKey ? await config.getApiKey(config.model.provider) : undefined) ||
config.api Key;

const response = await stream Function(config.model, llm Context, {
    ...config,
    api Key: resolvedApiKey,
    signal,
});
```

```txt
Lines 388–407, unchanged.
```

上面第 388–407 行，未改动。

The provider start event pushes the partial message into the context and emits message_start. Each of the nine block events (text_*, thinking_*, toolcall_*) replaces the last message and emits message_update with the raw assistantMessageEvent. done and error await response.result(), stamp thinking Level on the final message, and emit message_end agent/agent-loop.ts:409.

供应商的 start 事件把部分消息推进 context 并发出 message_start。九个块事件（text_*、thinking_*、toolcall_*）中的每一个都会替换最后一条消息，并带着原始的 assistantMessageEvent 发出 message_update。done 和 error 会 await response.result()，在最终消息上盖上 thinking Level，然后发出 message_end（agent/agent-loop.ts:409）。

The consequences are worth stating once:

由此带来的几点值得单独说清楚：

A turn is one assistant response plus its tool calls and results. The AgentEvent type says so in a comment agent/types.ts:518.

一个轮次就是一段助手响应加上它的工具调用和结果。AgentEvent 类型里有一条注释就是这么写的（agent/types.ts:518）。

Tool results feed back by being pushed onto current Context.messages agent/agent-loop.ts:274. The next pass streams a new response with them in context.

工具结果通过推进 current Context.messages 回流（agent/agent-loop.ts:274）。下一次经过会把它们带着在 context 里流式输出一段新响应。

There is no turn limit. Nothing in run Loop counts turns.

没有轮次上限。run Loop 里没有任何东西在数轮次。

The loop stops in exactly three places: a response with stop Reason "error" or "aborted" agent/agent-loop.ts:245; a finish Turn that returns {action: "end"} agent/agent-loop.ts:289; and a pass with no unterminated tool results, no steering, no follow-ups and no explicit continuation agent/agent-loop.ts:317.

循环恰好在三处停下：stop Reason 为“error”或“aborted”的响应（agent/agent-loop.ts:245）；返回 {action: “end”} 的 finish Turn（agent/agent-loop.ts:289）；以及一次经过中既没有尚未了结的工具结果，也没有转向、没有后续消息、也没有显式要求继续（agent/agent-loop.ts:317）。

On the error exit finish Turn still runs, but its decision is ignored; turn_end and agent_end follow at once agent/agentloop.ts:252.

走错误出口时 finish Turn 仍然会执行，但它的决定被忽略；turn_end 和 agent_end 紧接着发出（agent/agentloop.ts:252）。

## F O O T G U N

## 陷阱

A response cut of by the output limit can carry tool calls whose arguments parse and validate but are incomplete. When stop Reason is "length", the loop runs none of them. Each gets the error result Tool call "<name>" was not executed: the response hit the output token limit, so its arguments may be truncated. Re-issue the tool call with complete arguments. agent/agent-loop.ts:493. The model sees errors, not results, and the loop goes round again.

被输出上限截断的响应里可能带着一些工具调用，它们的参数能解析、能通过校验，但并不完整。当 stop Reason 是“length”时，循环一个也不会执行。每个调用都会拿到这条错误结果：Tool call “<name>” was not executed: the response hit the output token limit, so its arguments may be truncated. Re-issue the tool call with complete arguments.（agent/agent-loop.ts:493）。模型看到的是错误而不是结果，然后循环再转一圈。

## Steering versus follow-up

## 转向与后续消息

Two queues feed the loop from outside a run. Both hold AgentMessages and are drained by the hooks getSteeringMessages and getFollowUpMessages, which Agent wires to PendingMessageQueue instances agent/agent.ts:496. They difer only in where the loop polls them.

有两个队列从一次运行之外给循环供料。两者都存着 AgentMessage，由钩子 getSteeringMessages 和 getFollowUpMessages 取空，Agent 把它们接到 PendingMessageQueue 实例上（agent/agent.ts:496）。它们唯一的区别在于循环在哪里轮询它们。

<table><tr><td></td><td>转向</td><td>后续</td></tr><tr><td>API</td><td>agent.steer(msg)</td><td>agent.followUp(msg)</td></tr><tr><td>意图</td><td>“当前助手轮次结束后注入”agent/agent.ts:298</td><td>“只在智能体本来要停止时才运行”agent/agent.ts:303</td></tr><tr><td>轮询时机</td><td>循环开始 :176；每个 turn_end 之后 :295；prepareNextTurn 之后，如果上一次轮询是空的 :204</td><td>内层循环退出时 :302</td></tr><tr><td>是否打断当前工具调用</td><td>否；“当前助手消息发起的工具调用不会被跳过”agent/types.ts:287</td><td>否</td></tr><tr><td>交互按键</td><td>流式输出时按 Enter</td><td>Alt+Enter（Windows 上是 Ctrl+Q）</td></tr><tr><td>取空模式</td><td>steering Mode: &quot;one-at-a-time&quot;（默认）或 &quot;all&quot;</td><td>followUpMode：同上</td></tr></table>

Steering waits for the current turn’s tools; follow-ups wait for the whole run. Poll sites from agent/agent-loop.ts; keys from app.message.followUp in CA/src/core/keybindings.ts:134 and the submit handler in CA/src/modes/interactive/interactive-mode.ts:3358.

转向要等当前轮次的工具跑完；后续消息要等整次运行结束。轮询位置取自 agent/agent-loop.ts；按键取自 CA/src/core/keybindings.ts:134 里的 app.message.followUp，以及 CA/src/modes/interactive/interactive-mode.ts:3358 里的提交处理器。

```typescript one-at-a-time means one message per drain point agent/agent.ts:159 TS

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

one-at-a-time 的意思是每个取空点只取一条消息（agent/agent.ts:159）。

PendingMessageQueue.peek and drain, lines 159–169, unchanged.

上面是 PendingMessageQueue 的 peek 和 drain，第 159–169 行，未改动。

The re-poll after prepareNextTurn exists because that hook can run for seconds: the coding agent compacts there (compaction and branch summaries (p. 92)). The source explains the guard: “Only poll again if the earlier poll returned nothing; otherwise one-at-a-time mode would deliver two messages in this turn” agent/agent-loop.ts:202.

prepareNextTurn 之后要再轮询一次，是因为这个钩子可能跑上好几秒：编码智能体会在那里做压缩（「压缩与分支摘要」，第 92 页）。源码解释了这个守卫条件：“只有在上一次轮询什么都没返回时才再轮询一次；否则 one-at-a-time 模式会在这个轮次里送出两条消息” agent/agent-loop.ts:202。

The capture kit queued one steering message and one follow-up from inside a running tool, then let the loop finish research/out/agent-loop-queues.txt. Steering entered as the user message of turn 2, straight after the tool results; the follow-up waited until turn 2 had produced a plain answer, then opened turn 3. One agent.prompt() produced three turns and one agent_end with 8 new messages.

采集套件从一次正在执行的工具内部往队列里放了一条转向消息和一条后续消息，然后让循环跑完（research/out/agent-loop-queues.txt）。转向消息紧跟在工具结果之后，作为第 2 轮的用户消息进入；后续消息一直等到第 2 轮给出一个普通回答，才开启第 3 轮。一次 agent.prompt() 产生了三个轮次、一次 agent_end 和 8 条新消息。

## Tool execution

## 工具执行

executeToolCalls agent/agent-loop.ts:508 picks a mode per batch. It runs sequentially when config.tool Execution === "sequential" or when any called tool declares execution Mode: "sequential"; otherwise in parallel, the default.

executeToolCalls（agent/agent-loop.ts:508）为每一批挑选一种模式。当 config.tool Execution === “sequential”，或者任何被调用的工具声明了 execution Mode: “sequential”时，它顺序执行；否则并行执行，那是默认。

Every call is first prepared by prepareToolCall agent/agent-loop.ts:707, in order:

每次调用都先由 prepareToolCall（agent/agent-loop.ts:707）按以下顺序准备：

1. Find the tool by name. Unknown → error result Tool <name> not found.

1. 按名字查找工具。找不到 → 错误结果 Tool <name> not found。

2. Apply prepare Arguments, then validateToolArguments. A thrown error becomes the error text.

2. 应用 prepare Arguments，然后 validateToolArguments。抛出的错误变成错误文本。

3. Call beforeToolCall. If the signal aborted meanwhile → Operation aborted. {block: true} → error result with reason, default Tool execution was blocked.

3. 调用 beforeToolCall。如果这期间 signal 被中止 → Operation aborted。{block: true} → 带原因的错误结果，默认原因是 Tool execution was blocked。

Any of those outcomes is immediate: the call never executes. Otherwise execute runs, and a thrown error becomes an isError: true result agent/agent-loop.ts:841. afterToolCall then overrides the result field by field: content, details, usage, terminate, structured Content and isError agent/agent-loop.ts:877. Replacing content without returning structured Content drops structured Content, “because it may no longer match the content” agent/types.ts:85.

上面任何一种结果都是立即生效的：该调用绝不执行。否则就执行 execute，抛出的错误变成 isError: true 的结果（agent/agent-loop.ts:841）。随后 afterToolCall 逐字段覆盖结果：content、details、usage、terminate、structured Content 和 isError（agent/agent-loop.ts:877）。如果替换了 content 却没有返回 structured Content，结构化内容就丢了，“because it may no longer match the content”（agent/types.ts:85）。

![](images/371ca77ebc55e6518d138c5e32fad9bb137a8df7051ead095d0eb568a09854b6.jpg)

Preflight is sequential, execution is concurrent, and results come back in source order. Events 7–15 of research/out/agent-loop-queues.txt: the faux model asked for slow (id A) then fast (id B). tool_execution_end follows completion order (B before A); the tool Result messages follow the order of the calls in the assistant message (A before B). An immediate outcome emits its tool_execution_end during preflight.

预检是顺序的，执行是并发的，而结果按源码顺序返回。取自 research/out/agent-loop-queues.txt 的事件 7–15：faux 供应商先要了 slow（id A），再要了 fast（id B）。tool_execution_end 按完成顺序排列（B 在 A 之前）；工具结果消息则按助手消息里调用的顺序排列（A 在 B 之前）。立即返回的结果会在预检阶段就发出它的 tool_execution_end。

In sequential mode each call runs start → prepare → execute → finalize → tool_execution_end → tool Result message before the next begins, and the batch stops early if the signal aborts agent/agent-loop.ts:575.

在顺序模式下，每次调用都会走完 start → prepare → execute → finalize → tool_execution_end → 工具结果消息，然后才开始下一次；如果 signal 被中止，整批会提前停止（agent/agent-loop.ts:575）。

A batch ends the run early only if “every finalized tool result in the batch” sets terminate: true agent/agent-loop.ts:689. One result without it keeps the loop going.

只有当“批次里每一个已定稿的工具结果”都设置了 terminate: true 时，一批工具才会提前结束这次运行（agent/agent-loop.ts:689）。只要有一个结果没设，循环就继续。

runToolCall(tool Call, options) agent/agent-loop.ts:810 runs the same prepare → execute → finalize pipeline but “Emits no events and adds no messages”. The coding agent uses it for calls a tool makes through ctx.execute Tool() (extensions, loading and the API (p. 113)), which is how codemode runs its nested calls with the same permission hooks (codemode (p. 151)).

runToolCall(tool Call, options)（agent/agent-loop.ts:810）跑的是同一套 prepare → execute → finalize 流水线，但“Emits no events and adds no messages”。编码智能体把它用在工具通过 ctx.execute Tool() 发起的调用上（见「扩展、加载与 API」，第 113 页），codemode 也就是这样用同一套权限钩子来跑它的嵌套调用（见 codemode，第 151 页）。

## W H A T T H I S M E A N S F O R Y O U

## 这对你意味着什么

Never throw from a StreamFn, convertToLlm, transform Context or a queue hook; return a failed message or a safe fallback.

永远不要从 StreamFn、convertToLlm、transform Context 或队列钩子里抛错；返回一个失败消息，或者一个安全的兜底值。

Expect several tool_execution_end events in any order; match them by toolCallId, and read results in source order from the tool Result messages.

预期会收到若干个 tool_execution_end，顺序任意；用 toolCallId 把它们一一对上，并从工具结果消息里按源码顺序读取结果。

Use steering to redirect after the current tools finish, and follow-up to queue work for when the agent would stop.

用转向在当前工具跑完之后改变方向，用后续消息为智能体将要停止的那一刻排队工作。

Bound long runs yourself, in finish Turn or by aborting: the loop has no turn limit.

长时间运行要自己设上限，做法是在 finish Turn 里限制，或者直接中止：循环没有轮次上限。

Sources: agent/types.ts (StreamFn, AgentTool, AgentToolResult, AfterToolCallResult, AgentLoopConfig, CustomAgentMessages, AgentEvent); agent/agent-loop.ts (agent Loop, agentLoopContinue, runAgentLoop, run Loop, declareToolChanges, streamAssistantResponse, failToolCallsFromTruncatedMessage, executeToolCalls, executeToolCallsSequential, executeToolCallsParallel, prepareToolCall, finalizeExecutedToolCall, shouldTerminateToolBatch, runToolCall); agent/agent.ts (PendingMessageQueue, createLoopConfig); agent/index.ts; CA/src/core/keybindings.ts:134; CA/src/modes/interactive/interactive-mode.ts:3358, 4435; CA/src/extensions/codemode/execute.ts:405; research/capture/agent-loop-queues.mjs; research/out/agent-loop-queues.txt; research/out/stats.txt

来源：agent/types.ts（StreamFn、AgentTool、AgentToolResult、AfterToolCallResult、AgentLoopConfig、CustomAgentMessages、AgentEvent）；agent/agent-loop.ts（agent Loop、agentLoopContinue、runAgentLoop、run Loop、declareToolChanges、streamAssistantResponse、failToolCallsFromTruncatedMessage、executeToolCalls、executeToolCallsSequential、executeToolCallsParallel、prepareToolCall、finalizeExecutedToolCall、shouldTerminateToolBatch、runToolCall）；agent/agent.ts（PendingMessageQueue、createLoopConfig）；agent/index.ts；CA/src/core/keybindings.ts:134；CA/src/modes/interactive/interactive-mode.ts:3358, 4435；CA/src/extensions/codemode/execute.ts:405；research/capture/agent-loop-queues.mjs；research/out/agent-loop-queues.txt；research/out/stats.txt

## 3.2 Agent events and the Agent class

## 3.2 智能体事件与 Agent 类

Ten event types describe every run, nested as run, turn and message. The Agent class updates its statefrom each event before any listener sees it, and it stays busy until the last agent_end listener returns.

十种事件类型描述了每一次运行，按运行、轮次、消息三层嵌套。Agent 类在任何一个监听器看到某个事件之前，先用自己的状态更新处理这个事件；而且它会一直处于忙碌状态，直到最后一个 agent_end 监听器返回。

Everything that watches Pi work — the terminal UI, JSON and RPC output, extensions, the session file — is driven by one event stream. This section lists the ten AgentEvent types with their payloads and shows the order they arrive in from a real run. It then describes the Agent class that emits them: its defaults, its prompt and continue rules, its state reducer, and how it closes a run that threw.

所有观察 Pi 干活的东西——终端 UI、JSON 与 RPC 输出、扩展、会话文件——都由同一条事件流驱动。本节列出这十种 AgentEvent 类型及其载荷，并展示它们在一次真实运行中的到达顺序。随后描述发出这些事件的 Agent 类：它的默认值、它的 prompt 与 continue 规则、它的状态归约器，以及它如何收尾一次抛了异常的运行。

## The ten events

## 这十种事件

AgentEvent is a discriminated union of ten members agent/types.ts:514. They come in three nested lifecycles and one tool lifecycle.

AgentEvent 是由十个成员构成的区分联合类型（agent/types.ts:514）。它们分属三层嵌套的生命周期，外加一条工具生命周期。

<table><tr><td>事件</td><td>载荷</td><td>发出时机</td></tr><tr><td>agent_start</td><td>—</td><td>一次，运行中的第一个事件</td></tr><tr><td>agent_end</td><td>messages: AgentMessage[]</td><td>一次，运行中的最后一个事件；messages 是这次运行新增的消息</td></tr><tr><td>turn_start</td><td>—</td><td>每段助手响应之前</td></tr><tr><td>turn_end</td><td>message: AgentMessage, tool Results: ToolResultMessage[]</td><td>响应及其全部工具结果之后</td></tr><tr><td>message_start</td><td>message: AgentMessage</td><td>用于 system、user、assistant、tool Result 和自定义消息</td></tr><tr><td>message_update</td><td>message, assistantMessageEvent: AssistantMessageEvent</td><td>仅助手消息，每个流式块事件一次</td></tr><tr><td>message_end</td><td>message: AgentMessage</td><td>消息定稿时</td></tr><tr><td>tool_execution_start</td><td>toolCallId, tool Name, args</td><td>一次调用被准备之前</td></tr><tr><td>tool_execution_update</td><td>toolCallId, tool Name, args, partial Result</td><td>运行中的工具每次 onUpdate</td></tr><tr><td>tool_execution_end</td><td>toolCallId, tool Name, result, isError</td><td>afterToolCall 之后，按完成顺序</td></tr></table>

Only assistant messages stream; every other message arrives as a start/end pair. From AgentEvent in agent/types.ts:514–529; emission sites in agent/agentloop.ts.

只有助手消息是流式的；其他每一种消息都以 start/end 一对的形式到达。出自 agent/types.ts:514–529 的 AgentEvent；发出位置在 agent/agentloop.ts。

message_update carries the pi-ai event that caused it (text_delta, toolcall_end and so on, the streaming event protocol (p. 30)) and a shallow copy of the partial message. agent_end is the last event of a run, but the type’s own comment warns that awaited listeners “for that event are still part of run settlement. The agent becomes idle only after those listeners finish” agent/types.ts:510.

message_update 携带引发它的那个 pi-ai 事件（text_delta、toolcall_end 等等，也就是流式事件协议，见第 30 页），以及那条部分消息的浅拷贝。agent_end 是一次运行的最后一个事件，但这个类型自己的注释提醒说，被 await 的监听器“for that event are still part of run settlement. The agent becomes idle only after those listeners finish”（agent/types.ts:510）。

## The order, from a real run

## 顺序：来自一次真实运行

The capture kit ran one prompt through a real AgentSession with the faux provider: the model reads hello.txt with one read call, then answers research/out/one-turn.txt. The subscriber saw 29 events. Fig. 3.3 (p. 58) shows them as the loop nests them.

采集套件用 faux 供应商把一条提示词跑过了一个真实的 AgentSession：模型用一次 read 调用读取 hello.txt，然后作答，结果见 research/out/one-turn.txt。订阅者看到 29 个事件。图 3.3（第 58 页）按循环的嵌套方式展示了它们。

```txt
FIG. 3.3 ONE PROMPT, ONE TOOL CALL, 29 EVENTS

agent_start
| turn_start turn 1
| message_start · message_end system prompt sections + tools Added
| message_start · message_end user "What does hello.txt say?"
| message_start assistant
| message_update ×6 text_start · text_delta · text_end · toolcall_start · toolcall_delta · toolcall_end
| message_end assistant stop Reason tool Use
| tool_execution_start read
| tool_execution_end read
| message_start · message_end tool Result
| turn_end assistant tool Results: [call_1]
| turn_start turn 2
| message_start assistant
| message_update ×4 text_start · text_delta ×2 · text_end
| message_end assistant stop Reason stop turn_end assistant agent_end agent_settled AgentSession only, after the run
```

S T R U C T U R E

结构

A run is turns, a turn is messages, and tools sit between the assistant message and its results. The event stream of research/out/one-turn.txt, indented by lifecycle; 28 AgentEvents plus the session’s agent_settled. The number of text_delta events changes from run to run; the order does not. No tool_execution_update appears because read reports no partial results.

一次运行由轮次组成，一个轮次由消息组成，而工具夹在助手消息和它的结果之间。图中是 research/out/one-turn.txt 的事件流，按生命周期缩进；28 个 AgentEvent，加上会话自己的 agent_settled。text_delta 事件的数量每次运行都会变，顺序不会。这里没有 tool_execution_update，因为 read 不上报部分结果。

With two tool calls the skeleton holds, with the refinements shown in Fig. 3.2 (p. 55). In parallel mode all tool_execution_start events come before any tool_execution_end, and ends arrive in completion order. The tool Result messages follow in the order the calls appear in the assistant message. A steering message appears as a message_start/message_end pair for a user message right after the next turn_start; a tool-change declaration appears the same way as a system message research/out/agent-loop-queues.txt.

有两个工具调用时骨架仍然成立，只是细节更多，如图 3.2（第 55 页）所示。在并行模式下，所有 tool_execution_start 事件都排在任何 tool_execution_end 之前，而 end 按完成顺序到达。工具结果消息则按调用在助手消息中出现的顺序排列。一条转向消息表现为紧跟在下一个 turn_start 之后的一对 message_start/message_end，其中是一条 user 消息；一条工具变更声明同样如此，只不过是一条 system 消息（research/out/agent-loop-queues.txt）。

The first system message in the capture is not the system prompt seeded at construction. The coding agent constructs its Agent with an empty prompt and no tools, so no seed message exists. The first prompt carries a system message holding the prompt sections and tools Added for the four default tools; it is line 4 of the session file in the same capture (sessions, the JSONL tree (p. 86)).

这次采集里的第一条 system 消息并不是构造时种下的系统提示词。编码智能体是用空提示词、无工具来构造 Agent 的，所以并不存在种子消息。第一条提示词带来一条 system 消息，里面装着提示词各节和四个默认工具的 tools Added；它是同一次采集中会话文件的第 4 行（见「会话：JSONL 树」，第 86 页）。

## The Agent class

## Agent 类

Agent agent/agent.ts:188 owns a transcript, the two queues of the agent loop (p. 49), a set of listeners and at most one active run. It turns its own fields into an AgentLoopConfig for every run agent/agent.ts:467 and passes process Events as the loop’s event sink.

Agent（agent/agent.ts:188）持有一份记录、智能体循环（第 49 页）的那两个队列、一组监听器，以及至多一次正在进行的运行。它在每次运行前把自己的字段转成一份 AgentLoopConfig（agent/agent.ts:467），并把 process Events 作为循环的事件 sink 传进去。

<table><tr><td>选项</td><td>默认值</td><td>参见</td></tr><tr><td>convertToLlm</td><td>保留 system、user、assistant、tool Result，丢掉其他所有角色</td><td>agent/agent.ts:38</td></tr><tr><td>streamFn</td><td>getDefaultStreamFn()，它会抛出 No default stream function configured.Pass streamFn explicitly or call setDefaultStreamFn().</td><td>agent/stream-fn.ts:15</td></tr><tr><td>steering Mode,followUpMode</td><td>&quot;one-at-a-time&quot;</td><td>agent/agent.ts:247</td></tr><tr><td>transport</td><td>&quot;auto&quot;</td><td>agent/agent.ts:251</td></tr><tr><td>tool Execution</td><td>&quot;parallel&quot;</td><td>agent/agent.ts:253</td></tr><tr><td>initial State.model</td><td>一个 id 为 &quot;unknown&quot;、上下文窗口为 0 的占位模型</td><td>agent/agent.ts:57</td></tr><tr><td>initial State.thinking Level</td><td>&quot;off&quot;</td><td>agent/agent.ts:93</td></tr></table>

An Agent built with no options has no model and no way to call one. Constructor at agent/agent.ts:230–254.

一个不带任何选项构造出来的 Agent 既没有模型，也没有调用模型的办法。构造器在 agent/agent.ts:230–254。

If initial State.messages does not start with a system message, createInitialSystemMessage(system Prompt, tools) is prepended, unless both are empty agent/agent.ts:85. state.system Prompt is a getter that replays the transcript’s system messages; there is no setter. Assigning state.tools or state.messages copies the top-level array agent/agent.ts:97. Two methods start a run:

如果 initial State.messages 不是以一条 system 消息开头，就会前置 createInitialSystemMessage(system Prompt, tools)，除非两者都为空（agent/agent.ts:85）。state.system Prompt 是一个 getter，它重放记录里的 system 消息；没有 setter。给 state.tools 或 state.messages 赋值会复制顶层数组（agent/agent.ts:97）。有两个方法可以启动一次运行：

prompt(input, images?) accepts a string, one message or an array. During a run it throws Agent is already processing a prompt. Use steer() or followUp() to queue messages, or wait for completion. agent/agent.ts:376.

prompt(input, images?) 接受一个字符串、一条消息或一个数组。在运行过程中它会抛出 Agent is already processing a prompt。想排消息就用 steer() 或 followUp()，或者等这次运行结束。agent/agent.ts:376。

continue() throws No messages to continue from if the transcript holds only system messages. If the last message is an assistant reply, it drains the steering queue and runs those messages; failing that, the follow-up queue; failing both, it throws Cannot continue from message role: assistant. Otherwise it calls runAgentLoopContinue agent/agent.ts:384.

如果记录里只有 system 消息，continue() 会抛出 No messages to continue from。如果最后一条消息是助手回复，它会去取空转向队列并运行那些消息；取不到就退向后续队列；两者都空就抛出 Cannot continue from message role: assistant。否则它调用 runAgentLoopContinue（agent/agent.ts:384）。

![](images/e8bc6bb7a3a0ec0a6e98933690c3dcddfc52cca0369379c1709b4ca02bbc36ce.jpg)

isStreaming is cleared after the last listener returns, not when agent_end is emitted. agent/agent.ts, schematic; numbers are line numbers. Step 3 runs once per event. Step 4 runs in the catch and emits the closing events itself; step 5 runs in finally.

isStreaming 是在最后一个监听器返回之后才清除的，而不是在 agent_end 发出时。agent/agent.ts，示意图；图中数字是行号。第 3 步每个事件运行一次。第 4 步在 catch 里运行，自己发出收尾事件；第 5 步在 finally 里运行。

process Events agent/agent.ts:565 first reduces state, then awaits every listener in subscription order. A slow listener therefore slows the loop.

process Events（agent/agent.ts:565）先归约状态，然后按订阅顺序 await 每一个监听器。所以监听器慢就会拖慢循环。

<table><tr><td>事件</td><td>状态变化</td></tr><tr><td>message_start, message_update</td><td>streaming Message = 该消息</td></tr><tr><td>message_end</td><td>清空 streaming Message；把消息推进 messages</td></tr><tr><td>tool_execution_start</td><td>把 toolCallId 加进 pendingToolCalls（一个新 Set）</td></tr><tr><td>tool_execution_end</td><td>把 toolCallId 从 pendingToolCalls 移除（一个新 Set）</td></tr><tr><td>turn_end</td><td>如果助手消息带 error Message 就设置它</td></tr><tr><td>agent_end</td><td>清空 streaming Message</td></tr></table>

State is updated before listeners run, so a listener always reads the post-event state. process Events at agent/agent.ts:565–603.

状态在监听器运行之前就更新，所以监听器读到的永远是事件之后的状态。process Events 在 agent/agent.ts:565–603。

handleRunFailure agent/agent.ts:532 covers a run that throws, for example from a hook that broke its no-throw contract. It builds an assistant message with empty text, zero usage, stop Reason "aborted" if the signal fired and "error" otherwise, and the thrown message as error Message. Then it emits message_start, message_end, turn_end and agent_end for it, so subscribers always see a closed run.

handleRunFailure（agent/agent.ts:532）处理一次抛了异常的运行，例如某个钩子违反了不抛错的约定。它构造一条助手消息：文本为空、usage 为零，signal 触发过则 stop Reason 为 "aborted"，否则为 "error"，并把抛出的消息作为 error Message。然后为它发出 message_start、message_end、turn_end 和 agent_end，好让订阅者看到的总是一次闭合的运行。

F O O T G U N

陷阱

A synthesised failure run is not a well-formed run. handleRunFailure emits no agent_start or turn_start, and its agent_end carries only the failure message, not the messages the run produced before it threw. A subscriber that pairs starts with ends, or rebuilds the transcript from agent_end.messages, has to handle this case.

一次凭空合成出来的失败运行并不是一次格式良好的运行。handleRunFailure 不发 agent_start，也不发 turn_start，它发出的 agent_end 只带失败消息，不带这次运行在抛错之前产生的那些消息。凡是把 start 与 end 配对、或者从 agent_end.messages 重建记录的订阅者，都必须处理这种情况。

abort() aborts the active run’s signal. waitForIdle() resolves when the run and all its listeners have finished. reset() throws during a run; otherwise it keeps only the current system message and clears both queues agent/agent.ts:355.

abort() 会中止当前运行的 signal。waitForIdle() 在这次运行及其所有监听器都结束后 resolve。reset() 在运行期间调用会抛错；否则它只保留当前的 system 消息，并清空两个队列（agent/agent.ts:355）。

W H A T T H I S M E A N S F O R Y O U

这对你意味着什么

Use agent_end to learn that the loop has stopped emitting, and waitForIdle() to learn that the agent is idle.

用 agent_end 判断循环已经不再发出事件，用 waitForIdle() 判断智能体已经空闲。

Keep listeners fast: each one is awaited before the loop takes its next step.

让监听器保持快速：每一个都在循环进入下一步之前被 await。

Read tool results from message_end events with role tool Result, not from tool_execution_end, when order matters.

顺序重要时，从 role 为 tool Result 的 message_end 事件读工具结果，而不是从 tool_execution_end 读。

Inside a coding-agent session, wait for agent_settled (from prompt() to agent_settled (p. 67)), not agent_end.

在编码智能体会话内部，要等 agent_settled（见「从 prompt() 到 agent_settled」，第 67 页），而不是 agent_end。

Sources: agent/types.ts (AgentEvent, AgentState); agent/agent.ts (defaultConvertToLlm, DEFAULT_MODEL, createMutableAgentState, Agent constructor, prompt, continue, reset, createLoopConfig, runWithLifecycle, handleRunFailure, finish Run, process Events); agent/stream-fn.ts (getDefaultStreamFn); agent/agent-loop.ts (emission sites); ai/utils/transcript.ts (createInitialSystemMessage); CA/src/core/sdk.ts:393; research/capture/one-turn.mjs; research/out/one-turn.txt (§events, §session-jsonl); research/capture/agent-loop-queues.mjs; research/out/agent-loopqueues.txt

来源：agent/types.ts（AgentEvent、AgentState）；agent/agent.ts（defaultConvertToLlm、DEFAULT_MODEL、createMutableAgentState、Agent 构造器、prompt、continue、reset、createLoopConfig、runWithLifecycle、handleRunFailure、finish Run、process Events）；agent/stream-fn.ts（getDefaultStreamFn）；agent/agent-loop.ts（各发出位置）；ai/utils/transcript.ts（createInitialSystemMessage）；CA/src/core/sdk.ts:393；research/capture/one-turn.mjs；research/out/one-turn.txt（§events、§session-jsonl）；research/capture/agent-loop-queues.mjs；research/out/agent-loopqueues.txt

#### 3.3 Agent Session: wiring the runtime

#### 3.3 AgentSession：接好运行时

AgentSession turns the generic Agent into a coding agent byfilling its hooks. The hook that matters most replaces the agent's messages with a projection of the sessionfile before every request, so thefile, not memory, decides what the model sees.

AgentSession 通过填满 Agent 的各个钩子，把通用的 Agent 变成一个编码智能体。其中最关键的钩子在每次请求之前，用会话文件的一份投影替换掉智能体的 messages，于是决定模型看到什么的是文件，而不是内存。

AgentSession (CA/src/core/agent-session.ts, 4,383 lines) wraps one Agent and adds persistence, model and thinking control, retry, compaction, user bash, tree navigation, the tool registry, the system prompt and extension dispatch. This section shows how sdk.ts builds the pair and how the four message roles the coding agent adds reach the model. It then covers the six hooks the session installs on the agent and the handler that writes each event to the session file.

AgentSession（CA/src/core/agent-session.ts，4,383 行）包住一个 Agent，并加上持久化、模型与思考控制、重试、压缩、用户 bash、树导航、工具注册表、系统提示词和扩展分发。本节展示 sdk.ts 如何构建这一对，以及编码智能体新增的那四个消息角色如何抵达模型。随后会讲会话安装在智能体上的六个钩子，以及把每个事件写进会话文件的处理器。

## Construction in sdk.ts

## 在 sdk.ts 里构造

createAgentSession builds the Agent first and the AgentSession around it CA/src/core/sdk.ts:393.

createAgentSession 先构建 Agent，再把 AgentSession 包在外面（CA/src/core/sdk.ts:393）。

```javascript the Agent the coding agent runs CA/src/core/sdk.ts:393 TS
const agent = new Agent({
    initial State: {
    system Prompt: "",
    model,
    thinking Level,
    tools: [],
    messages: existing Session.messages,
    },
    convertToLlm: convertToLlmWithBlockImages,
    streamFn: async (model, context, options) => {
    const request Options = buildRequestOptions(model, options);
    ...
    if (options?.sessionId === session Manager.getSessionId()) {
    cache Warmer.start({ model, context, options: request Options }, cacheContextIsCurrent(model));
    }
    return model Runtime.stream Simple(model, context, request Options);
    },
    onPayload: transformProviderPayload,
    onResponse: handleProviderResponse,
    onProviderStreamEvent: handleProviderStreamEvent,
    sessionId: session Manager.getSessionId(),
    transform Context: async (messages) => {
    const runner = extensionRunnerRef.current;
    if (!runner) return messages;
    return runner.emit Context(messages);
    },
    steering Mode: settings Manager.getSteeringMode(),
    followUpMode: settings Manager.getFollowUpMode(),
    transport: settings Manager.get Transport(),
    thinking Budgets: settings Manager.getThinkingBudgets(),
    maxRetryDelayMs: settings Manager.providerRetrySettings().maxRetryDelayMs,
});
```

上面是编码智能体所运行的 Agent（CA/src/core/sdk.ts:393）。

Lines 393–428. The … replaces a five-line comment on cache warming.

第 393–428 行。省略号替代了一段关于缓存预热的五行注释。

The prompt and tools start empty on purpose: the session adds them as a system message with the first prompt (from prompt() to agent_settled (p. 67)). buildRequestOptions CA/src/core/sdk.ts:322 adds the timeout (httpIdleTimeoutMs, where 0 means 2,147,483,647 ms), provider-level max Retries and maxRetryDelayMs, and a transform Headers that merges attribution headers and runs the extension before_provider_headers event. The three on… callbacks run the extension events before_provider_request, after_provider_response and provider_stream_event (extension events and contexts (p. 120)). tool Execution is not set, so the agent keeps the default "parallel".

提示词和工具故意从头就是空的：会话会在第一条提示词时把它们作为一条 system 消息加进去（见「从 prompt() 到 agent_settled」，第 67 页）。buildRequestOptions（CA/src/core/sdk.ts:322）加上超时（httpIdleTimeoutMs，其中 0 表示 2,147,483,647 毫秒）、供应商层的 max Retries 和 maxRetryDelayMs，以及一个 transform Headers，它会合并归因 header 并运行扩展的 before_provider_headers 事件。那三个 on… 回调运行的是扩展事件 before_provider_request、after_provider_response 和 provider_stream_event（见「扩展事件与上下文」，第 120 页）。tool Execution 没有设置，所以智能体保留默认的 "parallel"。

After construction, a new session appends model_change and thinking_level_change entries CA/src/core/sdk.ts:436. They are lines 2 and 3 of the captured session file research/out/one-turn.txt.

构造之后，一个新会话会追加 model_change 和 thinking_level_change 条目（CA/src/core/sdk.ts:436）。它们是所采集会话文件 research/out/one-turn.txt 的第 2、3 行。

## Four custom roles

## 四个自定义角色

CA/src/core/messages.ts extends CustomAgentMessages by declaration merging CA/src/core/messages.ts:70:

CA/src/core/messages.ts 通过声明合并扩展 CustomAgentMessages（CA/src/core/messages.ts:70）：

```txt the roles the coding agent adds CA/src/core/messages.ts:70 TS

declare module "@earendil-works/pi-agent-core" {
    interface CustomAgentMessages {
    bash Execution: BashExecutionMessage;
    custom: CustomMessage;
    branch Summary: BranchSummaryMessage;
    compaction Summary: CompactionSummaryMessage;
    }
}
```

上面是编码智能体新增的角色（CA/src/core/messages.ts:70）。

Lines 70–77, unchanged.

第 70–77 行，未改动。

convertToLlm CA/src/core/messages.ts:148 turns each of them into a user message:

convertToLlm（CA/src/core/messages.ts:148）把它们各自变成一条 user 消息：

<table><tr><td>角色</td><td>来源</td><td>对模型而言变成</td></tr><tr><td>bash Execution</td><td>user ! cmd</td><td>一条 user 消息：先是 Ran、命令（放在反引号里）、输出（放在围栏代码块里，或 (no output)），然后是 (command cancelled) 或 Command exited with code N，最后是 [Output truncated. Full output: path]；在 !! cmd 下会被丢掉</td></tr><tr><td>custom</td><td>扩展</td><td>内容相同的 user 消息；字符串会变成一个文本块</td></tr><tr><td>branch Summary</td><td>树导航</td><td>一条 user 消息，内容为 The following is a summary of a branch that this conversation came back from: 加上 ...&lt;/summary&gt;</td></tr><tr><td>compaction Summary</td><td>压缩</td><td>一条 user 消息，内容为 The conversation history before this point was compacted into the following summary: 加上 ...&lt;/summary&gt;</td></tr><tr><td>system, user, assistant, tool Result</td><td>循环</td><td>原样透传</td></tr></table>

Every coding-agent role reaches the model as a user message, or not at all. bashExecutionToText and convertToLlm in CA/src/core/messages.ts:82–196; the prefixes are the constants at lines 11–24.

编码智能体的每一个角色，要么以一条 user 消息的形式抵达模型，要么根本到不了。CA/src/core/messages.ts:82–196 中的 bashExecutionToText 和 convertToLlm；那些前缀是第 11–24 行的常量。

sdk.ts wraps this function once more. When the images.block Images setting is on, every image block in a user or tool-result message becomes the text Image reading is disabled., with consecutive placeholders collapsed into one CA/src/core/sdk.ts:279. The setting is read on every call, so a change takes efect on the next request.

sdk.ts 又把这个函数包了一层。当 images.blockImages 设置打开时，user 消息或工具结果消息里的每一个图像块都会变成文本 Image reading is disabled.，连续的占位符会合并成一个（CA/src/core/sdk.ts:279）。这个设置每次调用都会重新读取，所以改动会在下一次请求时生效。

## Six hooks on the Agent

## Agent 上的六个钩子

The constructor subscribes to the agent and installs six hooks, in this order CA/src/core/agent-session.ts:501:

构造函数订阅智能体，并按下面的顺序安装六个钩子（CA/src/core/agent-session.ts:501）：

![](images/a509b3dc8609f57f0a351c8b0244076f63b57ba2b582f2e25dd1cb4c3d69aedb.jpg)

The session owns the agent’s hooks; the agent owns nothing but the loop. CA/src/core/agent-session.ts, constructor at lines 474–514; numbers are the line of each installer. Each installer keeps the previous hook and calls it, so the two transform Context projections run after the extension context handler set in sdk.ts. The highlighted hook is the one that makes the session file canonical.

会话拥有智能体的钩子；智能体除了循环之外什么都不拥有。CA/src/core/agent-session.ts，构造函数在第 474–514 行；图中数字是每个安装器的行号。每个安装器都会保存上一个钩子并调用它，所以两个 transform Context 投影都跑在 sdk.ts 里设置的扩展上下文处理器之后。被高亮的那个钩子，就是让会话文件成为权威来源的那一个。

The tool hooks map Pi’s extension events onto the loop’s hook contract. _beforeToolCall returns whatever the extension tool_call handlers return, so {block: true} blocks the call; an extension that throws a non-Error is rethrown as Extension failed, blocking execution: … CA/src/core/agent-session.ts:667. _afterToolCall runs the tool_result handlers, then normalises images in the content, including images an extension injected CA/src/core/agent-session.ts:692.

工具钩子把 Pi 的扩展事件映射到循环的钩子约定上。_beforeToolCall 照原样返回扩展 tool_call 处理器的返回值，所以 {block: true} 会阻断这次调用；扩展抛出非 Error 的东西时，会被重新抛出为 Extension failed, blocking execution: …（CA/src/core/agent-session.ts:667）。_afterToolCall 先运行 tool_result 处理器，然后规范化内容里的图像，包括扩展注入的图像（CA/src/core/agent-session.ts:692）。

The request projection is the invariant. Before every request, prepare Request builds a projection of the session file and replaces the context’s messages with it CA/src/core/agent-session.ts:781. The projection is what sessions, the JSONL tree (p. 86) describes: the current branch, after compaction and context_edit entries. When the selected model is virtual, the same hook asks the model runtime to route this one request, and compacts first if the routed model’s window is exceeded CA/src/core/agent-session.ts:802.

请求投影就是那条不变式。每次请求之前，prepare Request 会构造一份会话文件的投影，并用它替换 context 里的 messages（CA/src/core/agent-session.ts:781）。这份投影就是「会话：JSONL 树」（第 86 页）所描述的东西：当前分支，扣除 compaction 和 context_edit 条目之后的结果。当选中的模型是虚拟模型时，同一个钩子会让模型运行时为这一次请求选路，并在所选模型的窗口被超出时先做一次压缩（CA/src/core/agent-session.ts:802）。

F O O T G U N

陷阱

Assigning session.agent.state.messages does not change what the model sees. The next prepare Request discards the agent’s messages in favour of the session projection. To change the context, append entries through the session (a custom message, a context_edit, a compaction), then call session.refresh Context() if you need agent.state.messages to match before the next request.

给 session.agent.state.messages 赋值并不会改变模型看到的东西。下一次 prepare Request 会丢掉智能体的 messages，改用会话的投影。要改变上下文，请通过会话追加条目（一条自定义消息、一个 context_edit、一次压缩），然后在需要 agent.state.messages 于下次请求前对齐时调用 session.refresh Context()。

prepareNextTurn does the between-turn work CA/src/core/agent-session.ts:892. It rebuilds the context from the projection, compacting first if the threshold is crossed (compaction and branch summaries (p. 92)). It difs the system-prompt sections against the transcript, returns a patch message if they changed, and applies the tool loadout. Last, it returns this.agent.state.model and thinking Level: this is how a model switch made mid-run reaches the next turn.

prepareNextTurn 负责轮次之间的工作（CA/src/core/agent-session.ts:892）。它从投影重建上下文，一旦越过阈值就先做压缩（「压缩与分支摘要」，第 92 页）。它把系统提示词的各节与记录做比对，若有变化就返回一条补丁消息，并施加工具配置。最后，它返回 this.agent.state.model 和 thinking Level：运行中途做的模型切换就是这样传到下一个轮次的。

## Persistence in _handle Agent Event

## _handleAgentEvent 中的持久化

_handleAgentEvent CA/src/core/agent-session.ts:1090 is the agent listener installed first. For each event it does six things in a fixed order:

_handleAgentEvent（CA/src/core/agent-session.ts:1090）是第一个安装的智能体监听器。对每个事件，它按固定顺序做六件事：

![](images/c824ce847e30605d755a5ce8a830f61a35947a5b239c6bd49569d6a0551b1c22.jpg)

Listeners see a message before it is on disk. CA/src/core/agent-session.ts:1090–1183. Extensions run first and are awaited; public listeners are called synchronously; the session file is written last. An extension message_end handler that returns a replacement mutates the message in place, so the replacement is what step 5 persists.

监听器看到一条消息时，它还没落盘。CA/src/core/agent-session.ts:1090–1183。扩展先运行并被 await；对外的监听器同步调用；会话文件最后才写。一个返回了替换内容的扩展 message_end 处理器会就地修改那条消息，所以第 5 步持久化下去的就是这个替换后的版本。

Step 5 appends system, user, assistant and tool Result messages with append Message, and custom messages with appendCustomMessageEntry CA/src/core/agent-session.ts:1134. The other three roles are written elsewhere: bash results by recordBashResult, summaries by compaction and tree navigation. A successful assistant message (any stop Reason but "error") after a retry emits auto_retry_end with success: true and resets the retry counter CA/src/core/agentsession.ts:1163.

第 5 步用 appendMessage 追加 system、user、assistant 和 tool Result 消息，用 appendCustomMessageEntry 追加自定义消息（CA/src/core/agent-session.ts:1134）。另外三个角色写在别处：bash 结果由 recordBashResult 写，摘要由压缩和树导航写。重试之后一条成功的助手消息（stop Reason 为任何值，只要不是 "error"）会发出带 success: true 的 auto_retry_end，并重置重试计数器（CA/src/core/agentsession.ts:1163）。

Step 6 exists because providers that validate message order reject a message between a tool call and its result. A custom message sent mid-run with trigger Turn: false is held in _pendingCustomMessages and appended at turn_end, after the turn’s tool results CA/src/core/agent-session.ts:2306.

第 6 步之所以存在，是因为那些校验消息顺序的供应商会拒绝出现在工具调用与其结果之间的消息。运行中途以 triggerTurn: false 发出的自定义消息会先存在 _pendingCustomMessages 里，在 turn_end 时、也就是该轮次的工具结果之后才追加（CA/src/core/agent-session.ts:2306）。

## D O C ≠ C O D E

文档 ≠ 代码

docs/json.md says entry_appended fires when “An extension appended a custom session entry through pi.append Entry().” The code emits it from five places: append Entry CA/src/core/agent-session.ts:3396, extension boundary drafts CA/src/core/agentsession.ts:1015, the context_edit entries that hide a failed attempt CA/src/core/agent-session.ts:1237, virtual-model state CA/src/core/agent-session.ts:822 and the cache warmer CA/src/core/agent-session.ts:485. It is never emitted for message entries: the capture appended five message entries during one prompt and emitted no entry_appended research/out/oneturn.txt.

docs/json.md 说 entry_appended 在“An extension appended a custom session entry through pi.appendEntry().”时触发。代码从五个地方发出它：appendEntry（CA/src/core/agent-session.ts:3396）、扩展边界草稿（CA/src/core/agentsession.ts:1015）、用于隐藏失败尝试的 context_edit 条目（CA/src/core/agent-session.ts:1237）、虚拟模型状态（CA/src/core/agent-session.ts:822）以及缓存预热器（CA/src/core/agent-session.ts:485）。它从不为消息条目发出：那次采集在一条提示词期间追加了五条消息条目，一个 entry_appended 也没发出（research/out/oneturn.txt）。

W H A T T H I S M E A N S F O R Y O U

这对你意味着什么

Change what the model sees by appending session entries, never by editing agent.state.messages.

要改变模型看到的东西，请追加会话条目，绝不要去编辑 agent.state.messages。

Do not read the session file from a message_end listener and expect that message to be there yet.

不要在 message_end 监听器里读会话文件，并指望那条消息已经在那儿了。

Use the extension message_end result to rewrite a message before it is persisted.

用扩展 message_end 的返回值，在一条消息被持久化之前改写它。

Watch message_end for message entries; entry_appended covers only the other kinds.

消息条目要盯 message_end；entry_appended 只覆盖其他种类。

Sources: CA/src/core/sdk.ts (convertToLlmWithBlockImages, buildRequestOptions, new Agent, initial model_change/thinking_level_change); CA/src/core/messages.ts (BashExecutionMessage, CustomMessage, BranchSummaryMessage, CompactionSummaryMessage, bashExecutionToText, convertToLlm); CA/src/core/agent-session.ts (constructor, _installAgentToolHooks, _beforeToolCall, _afterToolCall, _installAgentRequestProjection, _installAgentBoundaryHooks, _installAgentNextTurnRefresh, _installHiddenDeclarationsProjection, _installAgentForcedPromptProjection, _handleAgentEvent, _emitExtensionEvent, sendCustomMessage, append Entry binding); CA/docs/json.md (Queue and state events); research/out/one-turn.txt (§events, §session-jsonl)

来源：CA/src/core/sdk.ts（convertToLlmWithBlockImages、buildRequestOptions、new Agent、初始的 model_change/thinking_level_change）；CA/src/core/messages.ts（BashExecutionMessage、CustomMessage、BranchSummaryMessage、CompactionSummaryMessage、bashExecutionToText、convertToLlm）；CA/src/core/agent-session.ts（constructor、_installAgentToolHooks、_beforeToolCall、_afterToolCall、_installAgentRequestProjection、_installAgentBoundaryHooks、_installAgentNextTurnRefresh、_installHiddenDeclarationsProjection、_installAgentForcedPromptProjection、_handleAgentEvent、_emitExtensionEvent、sendCustomMessage、appendEntry 绑定）；CA/docs/json.md（队列与状态事件）；research/out/one-turn.txt（§events、§session-jsonl）

# 3.4 From prompt() to agent_settled

# 3.4 从 prompt() 到 agent_settled

One call to session.prompt() can run the agent loop several times: once for the prompt, then again for each retry, overflow recovery and queued message. agent_end closes one of those runs; agent_settled closes the call.

一次 session.prompt() 调用可以让智能体循环跑好几遍：一遍为这条提示词而跑，然后每次重试、每次溢出恢复、每条排队消息都要再跑一遍。agent_end 收尾的是其中某一遍运行；agent_settled 收尾的是这次调用。

AgentSession.prompt() is where typed text becomes a run, and it is the entry point the terminal UI, print mode, RPC and the SDK all share (run modes (p. 127)). This section follows a prompt through the checks before the loop starts, then through the post-run driver that decides whether to run again: automatic retry, compaction, queues and the agent_before_settle boundary. It ends with model and thinking control, user bash, and the full list of AgentSessionEvents.

AgentSession.prompt() 是打出来的文字变成一次运行的地方，也是终端 UI、打印模式、RPC 和 SDK 共同使用的入口（见「运行模式」，第 127 页）。本节沿着一条提示词，先看循环启动之前的各项检查，再看运行结束后的驱动逻辑——它决定要不要再跑一遍：自动重试、压缩、队列，以及 agent_before_settle 这道边界。最后讲模型与思考控制、用户 bash，以及 AgentSessionEvent 的完整清单。

## The prompt() pipeline

## prompt() 流水线

prompt(text, options) CA/src/core/agent-session.ts:1954 returns without starting a run in three ways — handled, queued or thrown — and starts one in a single way. Fig. 3.7 (p. 68) lists the checks in the order the code makes them.

prompt(text, options)（CA/src/core/agent-session.ts:1954）有三种不启动运行就返回的方式——被处理、被排队、或抛错——而启动运行的方式只有一种。图 3.7（第 68 页）按代码做出这些检查的顺序列出了它们。

![](images/1b2bcee55f1cf0fe22b479e2f9e0b1ad9751373b89b3f7dc0c6fa56fa86bf6e4.jpg)

Extension commands run even while the agent streams; everything else queues or waits. CA/src/core/agent-session.ts:1954–2097, first match wins; the quoted values are the PromptDisposition passed to preflight Result CA/src/core/agent-session.ts:301. Step 10’s first message is the system-prompt patch from _preparePromptAndToolLoadout, present only when the sections changed.

即使是智能体正在流式输出，扩展命令也会照常运行；其他一切都排队或等待。CA/src/core/agent-session.ts:1954–2097，先匹配者胜出；引号里的值是传给 preflightResult 的 PromptDisposition（CA/src/core/agent-session.ts:301）。第 10 步的第一条消息来自 _preparePromptAndToolLoadout 的系统提示词补丁，只有各节发生变化时才会出现。

The order has consequences. Extension commands are tried before the compaction check and the streaming check, so /name commands work at any time. The input event sees the raw text before skill and template expansion CA/src/core/agentsession.ts:1978. before_agent_start runs before image normalisation, so a handler that switches the model also chooses the resize profile CA/src/core/agent-session.ts:2045. A prompt issued while agent_settled listeners are running is deferred until they return CA/src/core/agent-session.ts:1955.

这个顺序会带来后果。扩展命令是在压缩检查和流式检查之前尝试的，所以 /name 命令在任何时候都能用。input 事件看到的是技能和模板展开之前的原始文本（CA/src/core/agentsession.ts:1978）。before_agent_start 跑在图像规范化之前，所以一个切换模型的处理器同时也决定了缩放配置（CA/src/core/agent-session.ts:2045）。在 agent_settled 监听器运行期间发出的提示词，会被推迟到它们返回之后（CA/src/core/agent-session.ts:1955）。

The other entry points funnel into the same machinery:

其他入口都汇入同一套机制：

steer(text) / followUp(text): run the input event and expansion, then queue. They throw Extension command "/<name>" cannot be queued. Use prompt() or execute the command when not streaming. CA/src/core/agentsession.ts:2260.

steer(text) / followUp(text)：先运行 input 事件和展开，然后排队。它们会抛出 Extension command "/<name>" cannot be queued. Use prompt() or execute the command when not streaming.。不在流式输出时，请改用 prompt() 或直接执行该命令（CA/src/core/agentsession.ts:2260）。

sendUserMessage(content, {deliverAs}): prompt() with source: "extension" and expandPromptTemplates defaulting to false CA/src/core/agent-session.ts:2375.

sendUserMessage(content, {deliverAs})：相当于 prompt() 带上 source: "extension"，而 expandPromptTemplates 默认为 false（CA/src/core/agent-session.ts:2375）。

sendCustomMessage(msg, {trigger Turn, deliverAs}): deliverAs: "next Turn" holds the message for the next prompt; while streaming it is steered or followed up; idle with trigger Turn it starts a run; otherwise it is appended without a run CA/src/core/agent-session.ts:2279.

sendCustomMessage(msg, {trigger Turn, deliverAs})：deliverAs: "next Turn" 会把消息留到下一条提示词；流式输出期间它会被转向或作为后续消息送出；空闲且带 triggerTurn 时它会启动一次运行；否则只追加而不运行（CA/src/core/agent-session.ts:2279）。

clear Queue(): empties both queues and returns {steering, followUp} as text, “Useful for restoring to editor when user aborts” CA/src/core/agent-session.ts:2383.

clearQueue()：清空两个队列，并以文本返回 {steering, followUp}，“Useful for restoring to editor when user aborts”（CA/src/core/agent-session.ts:2383）。

## The post-run driver

## 运行后的驱动逻辑

_runAgentPrompt CA/src/core/agent-session.ts:1808 wraps agent.prompt() in a loop that decides, after each run, whether to call agent.continue().

_runAgentPrompt（CA/src/core/agent-session.ts:1808）用一个循环把 agent.prompt() 包起来，每次运行结束后由它决定要不要调用 agent.continue()。

```typescript run, then keep going until nothing asks for more CA/src/core/agent-session.ts:1817 TS try {
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

上面先运行，然后一直继续，直到没有任何东西要求更多（CA/src/core/agent-session.ts:1817）。

Lines 1817–1836, unchanged.

第 1817–1836 行，未改动。

_handlePostAgentRun CA/src/core/agent-session.ts:1839 returns true, meaning run again, in three cases, checked in order:

_handlePostAgentRun（CA/src/core/agent-session.ts:1839）在三种情况下返回 true，意思是再跑一遍，按以下顺序检查：

1. The last assistant message is a retryable error and _prepareRetry scheduled a retry.

1. 最后一条助手消息是可重试的错误，而 _prepareRetry 已经排好了一次重试。

2. _checkCompaction compacted after an overflow or a recoverable length stop and wants the interrupted turn continued (compaction and branch summaries (p. 92)).

2. _checkCompaction 在溢出或一次可恢复的 length 停止之后做了压缩，并且希望把被打断的轮次继续下去（「压缩与分支摘要」，第 92 页）。

3. Messages are still queued, for example ones an agent_end handler queued after the loop drained both queues.

3. 仍有消息在排队，例如某个 agent_end 处理器在循环取空了两个队列之后又排进去的。

When it returns false, _runBeforeSettleBoundary gives extensions the last word through the agent_before_settle event CA/src/core/agent-session.ts:1879. A handler can append entries and ask to continue; the driver continues only if the projected context can be continued, and otherwise reports agent_before_settle requested continuation without runnable model context. With no handlers, it continues only if messages are queued.

当它返回 false 时，_runBeforeSettleBoundary 会通过 agent_before_settle 事件把最后的话语权交给扩展（CA/src/core/agent-session.ts:1879）。处理器可以追加条目并要求继续；只有当投影后的上下文可以继续时，驱动逻辑才会继续，否则它会报告 agent_before_settle requested continuation without runnable model context。没有处理器时，只有消息仍在排队它才会继续。

2

![](images/e3410b7d27090b20874367ff276a1b8c57f7af9dd20a2e2e49073ccb89b8590b.jpg)

One prompt, two runs, two agent_ends, one agent_settled. A retried prompt in the order the code emits it, schematic, not a capture; message and turn events are left out. auto_retry_end comes from the second run’s assistant message_end CA/src/core/agent-session.ts:1163, so it precedes that run’s agent_end. A prompt that needs no retry has one run and one agent_end, as in Fig. 3.3 (p. 58).

一条提示词、两次运行、两个 agent_end、一次 agent_settled。一条经过重试的提示词，按代码发出它的顺序绘制，示意图，不是采集结果；message 和 turn 事件都略去了。auto_retry_end 来自第二次运行的助手 message_end（CA/src/core/agent-session.ts:1163），所以它排在那次运行的 agent_end 之前。不需要重试的提示词只有一次运行和一个 agent_end，正如图 3.3（第 58 页）。

## Automatic retry

## 自动重试

A failed response is retryable when pi-ai’s isRetryableAssistantError says so and it is not a context overflow, which compaction handles instead CA/src/core/agent-session.ts:1694. isRetryableAssistantError requires stop Reason "error" and an error Message that matches the retryable-provider pattern and not the non-retryable-limit pattern ai/utils/retry.ts:250 (auth, cost, retries and the catalog (p. 41)).

一次失败的响应是否可重试，取决于 pi-ai 的 isRetryableAssistantError 怎么说，以及它不是上下文溢出——溢出由压缩来处理（CA/src/core/agent-session.ts:1694）。isRetryableAssistantError 要求 stopReason 为 "error"，并且 errorMessage 匹配可重试供应商的模式、且不匹配不可重试限额的模式（ai/utils/retry.ts:250，见「鉴权、成本、重试与目录」，第 41 页）。

<table><tr><td>设置项</td><td>默认值</td><td>作用</td></tr><tr><td>retry.enabled</td><td>true</td><td>智能体层的重试开关</td></tr><tr><td>retry.max Retries</td><td>3</td><td>首次失败之后的尝试次数</td></tr><tr><td>retry.baseDelayMs</td><td>2000</td><td>第 1 次尝试之前的延迟</td></tr><tr><td>retry.maxAgentDelayMs</td><td>60000</td><td>任意单次延迟的上限</td></tr></table>

Three retries wait 2 s, 4 s and 8 s. getRetrySettings in CA/src/core/settings-manager.ts:1000; the delay is baseDelayMs × 2^(attempt − 1), capped at maxAgentDelayMs ai/utils/retry.ts:126. The shipped settings table in CA/docs/settings.md agrees.

三次重试分别等待 2 秒、4 秒和 8 秒。getRetrySettings 在 CA/src/core/settings-manager.ts:1000；延迟是 baseDelayMs × 2^(attempt − 1)，以 maxAgentDelayMs 为上限（ai/utils/retry.ts:126）。CA/docs/settings.md 里随包发布的设置表与此一致。

_prepareRetry CA/src/core/agent-session.ts:3747 increments the attempt counter and emits auto_retry_start {attempt, max Attempts, delayMs, error Message}. It then hides the failed message from the model with a context_edit entry whose replacement is null (_omitRecoveryAttempt): the attempt stays in the raw JSONL and disappears from the projection (sessions, the JSONL tree (p. 86)). After an abortable sleep, the driver calls agent.continue(). If the selected model is virtual, that request is routed with reason "retry" and the failed message as failed CA/src/core/agentsession.ts:810.

_prepareRetry（CA/src/core/agent-session.ts:3747）递增尝试计数器并发出 auto_retry_start {attempt, max Attempts, delayMs, error Message}。接着它用一个 replacement 为 null 的 context_edit 条目把失败消息对模型藏起来（_omitRecoveryAttempt）：这次尝试仍留在原始 JSONL 里，但从投影中消失（见「会话：JSONL 树」，第 86 页）。在一次可中止的睡眠之后，驱动逻辑调用 agent.continue()。如果选中的模型是虚拟模型，这一次请求会以 reason "retry"、并把那条失败消息作为 failed 来选路（CA/src/core/agentsession.ts:810）。

The attempt ends one of three ways. A later response that is not an error emits auto_retry_end {success: true}. Running out of attempts emits auto_retry_end {success: false, final Error} CA/src/core/agent-session.ts:1860. An abort during the sleep emits auto_retry_end with final Error: "Retry cancelled" CA/src/core/agent-session.ts:3739.

这次尝试以三种方式之一结束。后面某次响应不是错误，就发出 auto_retry_end {success: true}。尝试次数用尽，就发出 auto_retry_end {success: false, final Error}（CA/src/core/agent-session.ts:1860）。睡眠期间被中止，就发出带 final Error: "Retry cancelled" 的 auto_retry_end（CA/src/core/agent-session.ts:3739）。

If your client needs “the model has finished answering”, wait for agent_settled. If it needs “this attempt failed”, read will Retry on agent_end: true means another run follows.

如果你的客户端需要知道“模型已经答完了”，就等 agent_settled。如果它需要知道“这次尝试失败了”，就读 agent_end 上的 willRetry：true 意味着后面还有一次运行。

## Model and thinking control

## 模型与思考控制

set Model(model, {persist}) CA/src/core/agent-session.ts:2463 throws No API key for <provider>/<id> without auth. It then sets agent.state.model, appends a model_change entry, optionally saves the default model, applies a thinking level and emits the extension event model_select if the model changed. The level is chosen in this order: an explicit level (scoped models only), the per-model setting, the default-level setting, the current level, and finally "medium" CA/src/core/agent-session.ts:2655.

setModel(model, {persist})（CA/src/core/agent-session.ts:2463）在没有鉴权的情况下抛出 No API key for <provider>/<id>。然后它设置 agent.state.model、追加一条 model_change 条目、可选地保存默认模型、应用一个思考等级，并在模型发生变化时发出扩展事件 model_select。等级按这个顺序挑选：显式给出的等级（仅限限定了范围的模型）、按模型的设置、默认等级的设置、当前等级，最后是 "medium"（CA/src/core/agent-session.ts:2655）。

setThinkingLevel(level, {persist}) CA/src/core/agent-session.ts:2598 clamps the level to what the model supports. Only if the clamped level difers from the current one does it append thinking_level_change, emit thinking_level_changed, and fire the extension event thinking_level_select. With persist it saves the requested level, not the clamped one.

setThinkingLevel(level, {persist})（CA/src/core/agent-session.ts:2598）会把等级限制到模型支持的范围内。只有当限制后的等级与当前等级不同，它才会追加 thinking_level_change、发出 thinking_level_changed，并触发扩展事件 thinking_level_select。带 persist 时，它保存的是请求的等级，而不是限制后的等级。

cycle Model(direction) CA/src/core/agent-session.ts:2505 cycles through the scoped models (--models or enabled Models) that are currently available, or through all available models when none are scoped. It returns undefined when there is at most one candidate.

cycleModel(direction)（CA/src/core/agent-session.ts:2505）在当前可用的限定范围模型（--models 或启用的 Models）之间轮换；没有限定范围时，则在所有可用模型之间轮换。候选最多只有一个时，它返回 undefined。

A change made during a run takes efect on the next turn, not the current request. prepareNextTurn returns the current agent.state.model and thinking Level to the loop (AgentSession: wiring the runtime (p. 61)).

运行期间做的改动会在下一个轮次生效，而不是当前这次请求。prepareNextTurn 把当前的 agent.state.model 和 thinking Level 返回给循环（见「AgentSession：接好运行时」，第 61 页）。

## User bash: !cmd and !!cmd

## 用户 bash：!cmd 与 !!cmd

In the editor, !cmd runs a shell command and !!cmd runs it with excludeFromContext

在编辑器里，!cmd 运行一条 shell 命令，!!cmd 则带上 excludeFromContext 运行它

CA/src/modes/interactive/interactive-mode.ts:3327. The mode, not the session, first emits the extension event user_bash CA/src/modes/interactive/interactive-mode.ts:6956. A handler can return a complete result, which is recorded with recordBashResult without running anything, or operations that replace local execution, for example to run over SSH or in a VM. RPC mode does the same for its bash command CA/src/modes/rpc/rpc-mode.ts:562.

（CA/src/modes/interactive/interactive-mode.ts:3327）。发出扩展事件 user_bash 的是模式层而不是会话（CA/src/modes/interactive/interactive-mode.ts:6956）。处理器可以返回一个完整结果，什么都不运行、直接用 recordBashResult 记录；也可以返回一批 operations 来取代本地执行，比如改在 SSH 上或虚拟机里运行。RPC 模式对它的 bash 命令做同样的事（CA/src/modes/rpc/rpc-mode.ts:562）。

execute Bash(command, onChunk?, {excludeFromContext, id, operations}) CA/src/core/agent-session.ts:3826 prepends the shellCommandPrefix setting on its own line, runs the command in the session’s working directory, and emits bash_execution_update {id, delta} for every chunk. recordBashResult then stores a BashExecutionMessage. If the agent is streaming, the record is held and appended when the run settles or before the next prompt, so it never lands between a tool call and its result CA/src/core/agent-session.ts:3877.

executeBash(command, onChunk?, {excludeFromContext, id, operations})（CA/src/core/agent-session.ts:3826）会先把 shellCommandPrefix 设置单独放在一行上，然后在会话的工作目录里运行命令，并为每个数据块发出 bash_execution_update {id, delta}。之后 recordBashResult 存下一条 BashExecutionMessage。如果智能体正在流式输出，这条记录会被暂存，等运行结束或下一条提示词到来时才追加，因此它绝不会落在工具调用与其结果之间（CA/src/core/agent-session.ts:3877）。

!!cmd output is shown and saved but never sent to the model: convertToLlm drops a bash Execution message with excludeFromContext set (AgentSession: wiring the runtime (p. 61)).

!!cmd 的输出会显示和保存，但绝不发给模型：convertToLlm 会丢掉设置了 excludeFromContext 的 bash Execution 消息（见「AgentSession：接好运行时」，第 61 页）。

## Agent Session Event

## AgentSessionEvent

AgentSessionEvent CA/src/core/agent-session.ts:191 is the AgentEvent stream with two changes, plus twelve event types of its own. Tool execution events of calls made through ctx.execute Tool() carry parentToolCallId, and agent_end gains will Retry.

AgentSessionEvent（CA/src/core/agent-session.ts:191）就是 AgentEvent 事件流加两处改动，再加它自己的十二种事件类型。通过 ctx.execute Tool() 发起的调用，其工具执行事件会带上 parentToolCallId；agent_end 则多了 willRetry。

<table><tr><td>事件</td><td>载荷</td><td>含义</td></tr><tr><td>agent_end</td><td>messages, will Retry</td><td>一次底层运行结束；如果后面还有自动重试，will Retry 为真</td></tr><tr><td>agent_settled</td><td>—</td><td>prompt() 没有自动的工作要做了</td></tr><tr><td>queue_update</td><td>steering: string[], followUp: string[]</td><td>两个队列当前的完整文本</td></tr><tr><td>compaction_start</td><td>reason: &quot;manual&quot; | &quot;threshold&quot; | &quot;overflow&quot;</td><td>压缩开始</td></tr><tr><td>compaction_end</td><td>reason, result, aborted, will Retry, error Message?</td><td>压缩结束、失败或被中止</td></tr><tr><td>entry_appended</td><td>entry</td><td>追加了一条非消息条目（见「AgentSession：接好运行时」，第 61 页）</td></tr><tr><td>session_info_changed</td><td>name</td><td>显示名被设置或清除</td></tr><tr><td>thinking_level_changed</td><td>level</td><td>实际生效的思考等级变了</td></tr><tr><td>auto_retry_start</td><td>attempt, max Attempts, delayMs, error Message</td><td>排好了一次重试</td></tr><tr><td>auto_retry_end</td><td>success, attempt, finalized?</td><td>重试序列结束</td></tr><tr><td>summarization_retry_sched/_attempt_start/_finished</td><td>attempts 数据；来源为 &quot;compaction&quot; 或 &quot;branch Summary&quot;</td><td>对压缩或分支摘要请求的重试</td></tr><tr><td>bash_execution_update</td><td>id?, delta</td><td>用户 bash 输出的一个数据块</td></tr></table>

Twelve session events sit on top of the ten agent events. From the AgentSessionEvent union at CA/src/core/agent-session.ts:191–232; the three summarization_retry_* types share a row. RPC mode and the SDK (p. 133) shows them on the wire.

十二种会话事件叠在十种智能体事件之上。出自 CA/src/core/agent-session.ts:191–232 的 AgentSessionEvent 联合类型；三个 summarization_retry_* 类型共用一行。见「RPC 模式与 SDK」（第 133 页），那里展示了它们在线路上的样子。

W H A T T H I S M E A N S F O R Y O U

这对你意味着什么

Pass streaming Behavior on every prompt() that can arrive mid-run; without it the call throws.

每一个可能在运行中途到达的 prompt() 都要传 streamingBehavior；不传就会抛错。

Treat agent_settled as idle and agent_end as one attempt.

把 agent_settled 当作空闲，把 agent_end 当作一次尝试。

Tune retry.* in settings rather than retrying in your client; Pi already hides the failed attempt from the model.

在设置里调 retry.*，而不是在你的客户端里重试；Pi 已经把失败的那次尝试对模型藏起来了。

Intercept user_bash to move ! commands to another machine; execute Bash itself does not emit it.

要把握 ! 命令挪到另一台机器上，就去拦截 user_bash；executeBash 自身并不发出它。

Sources: CA/src/core/agent-session.ts (AgentSessionEvent, PromptOptions, PromptDisposition, prompt, _runInputHandlers, steer, followUp, _throwIfExtensionCommand, sendCustomMessage, sendUserMessage, clear Queue, _runAgentPrompt, _handlePostAgentRun, _runBeforeSettleBoundary, _isRetryableError, _prepareRetry, _finishCancelledRetry, _omitRecoveryAttempt, set Model, cycle Model, setThinkingLevel, _getThinkingLevelForModelSwitch, execute Bash, recordBashResult, _flushPendingBashMessages); CA/src/core/settings-manager.ts:987, 1000; CA/src/core/defaults.ts:3; ai/utils/retry.ts (retryDelayMs, isRetryableAssistantError); CA/src/modes/interactive/interactive-mode.ts (submit handler, handleBashCommand); CA/src/modes/rpc/rpc-mode.ts:562; CA/docs/settings.md (retry.*)

来源：CA/src/core/agent-session.ts（AgentSessionEvent、PromptOptions、PromptDisposition、prompt、_runInputHandlers、steer、followUp、_throwIfExtensionCommand、sendCustomMessage、sendUserMessage、clearQueue、_runAgentPrompt、_handlePostAgentRun、_runBeforeSettleBoundary、_isRetryableError、_prepareRetry、_finishCancelledRetry、_omitRecoveryAttempt、setModel、cycleModel、setThinkingLevel、_getThinkingLevelForModelSwitch、executeBash、recordBashResult、_flushPendingBashMessages）；CA/src/core/settings-manager.ts:987, 1000；CA/src/core/defaults.ts:3；ai/utils/retry.ts（retryDelayMs、isRetryableAssistantError）；CA/src/modes/interactive/interactive-mode.ts（submit handler、handleBashCommand）；CA/src/modes/rpc/rpc-mode.ts:562；CA/docs/settings.md（retry.*）
