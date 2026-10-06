A stateless loop that alternates model turns and tool runs, wrapped by a session that persists every step.

## 3.1 The agent loop

The loop in pi-agent-core is onefunction with no state ofits own: it streams a response, runs the tool calls, and goes round again while tool results or queued messages give it something to send. It has no turn limit.

Every model call Pi makes during a conversation goes through one function, run Loop in agent/agent-loop.ts. This section gives the types the loop is configured with, walks the loop state by state, separates the two message queues that feed it, and follows a batch of tool calls through preparation, execution and result ordering. agent events and the Agent class (p. 57) lists the events it emits; AgentSession: wiring the runtime (p. 61) shows how the coding agent fills in its hooks.

## The package and its types

@earendil-works/pi-agent-core 1.0.4 is six files and 2,513 lines (2,281 non-blank research/out/stats.txt). It has two layers: a stateless loop that takes a context and a config and emits events, and a stateful Agent class that owns a transcript and two queues.

<table><tr><td>FILE</td><td>LINES</td><td>CONTENTS</td></tr><tr><td>agent/types.ts</td><td>529</td><td>StreamFn, AgentLoopConfig, AgentMessage, AgentTool, AgentEvent, hook types</td></tr><tr><td>agent/agent-loop.ts</td><td>940</td><td>agent Loop, agentLoopContinue, run Loop, tool execution, runToolCall</td></tr><tr><td>agent/agent.ts</td><td>613</td><td>Agent: state reducer, steering and follow-up queues, run lifecycle</td></tr><tr><td>agent/proxy.ts</td><td>406</td><td>stream Proxy, a StreamFn for apps that route model calls through their own server</td></tr><tr><td>agent/stream-fn.ts</td><td>20</td><td>setDefaultStreamFn, getDefaultStreamFn</td></tr><tr><td>agent/index.ts</td><td>5</td><td>re-exports; getDefaultStreamFn is not exported</td></tr></table>

Three files hold the whole runtime. Line counts from wc -l at 28dcce2.

The loop never calls a provider directly. It calls a StreamFn agent/types.ts:33, which has the shape of stream Simple in pi-ai (the streaming event protocol (p. 30)). The contract is written on the type: a stream function “Must not throw or return a rejected promise for request/model/runtime failures”; a failure arrives as a final message with stop Reason "error" or "aborted". The loop passes a normalised transcript in which “the system prompt and tool declarations are carried by the transcript’s system messages, never by context.system Prompt or context.tools” agent/types.ts:23.

Messages are an open union. AgentMessage is Message | CustomAgentMessages[keyof CustomAgentMessages], and CustomAgentMessages is an empty interface that applications extend by declaration merging agent/types.ts:365. The coding agent adds four roles this way (AgentSession: wiring the runtime (p. 61)).

A tool is a pi-ai Tool plus what the runtime needs to run it agent/types.ts:464:

label: human-readable name for the UI.

prepare Arguments?(args): a compatibility shim applied to the raw arguments before schema validation.

output Schema?: JSON Schema of structured Content in successful results.

execute(toolCallId, params, signal?, onUpdate?): returns an AgentToolResult: content for the model, details for logs and UI, optional structured Content (not sent to the model), usage, isError and terminate. Calls to onUpdate after the promise settles are ignored agent/types.ts:458.

replay?: "never" or "safe", the recovery policy for an efect whose outcome is unknown.

execution Mode?: "sequential" or "parallel", a per-tool override of the batch mode.

AgentLoopConfig extends SimpleStreamOptions and carries every hook agent/types.ts:193. The thinking level travels in the inherited reasoning field, where "off" is stored as undefined.

<table><tr><td>FIELD</td><td>CALLED</td><td>CONTRACT</td></tr><tr><td>model</td><td>—</td><td>model for the next request</td></tr><tr><td>convertToLlm(messages)</td><td>before every request</td><td>AgentMessage[] → Message[ ]; drop UI-only messages; must not throw</td></tr><tr><td>transform Context?(messages, signal)</td><td>before convertToLlm</td><td>prune or inject at the AgentMessage level; must not throw</td></tr><tr><td>getApiKey?(provider)</td><td>before every request</td><td>resolves expiring tokens; must not throw</td></tr><tr><td>prepare Request?</td><td>before every request, including the first</td><td>may replace context, model and thinking level for this and later requests</td></tr><tr><td>prepareNextTurn?</td><td>after turn_end, before the next turn_start</td><td>returns {context?, messages?, model?, thinking Level?}</td></tr><tr><td>finish Turn?</td><td>after tool results, before turn_end</td><td>returns {action: &quot;continue&quot;}, {action: &quot;end&quot;} or nothing</td></tr><tr><td>getSteeringMessages?</td><td>loop start, after each turn, after prepareNextTurn</td><td>drains the steering queue</td></tr><tr><td>getFollowUpMessages?</td><td>when the inner loop would exit</td><td>drains the follow-up queue</td></tr><tr><td>tool Execution?</td><td>—</td><td>&quot;parallel&quot; (default) or &quot;sequential&quot;</td></tr><tr><td>beforeToolCall? /afterToolCall?</td><td>per tool call</td><td>block a call; override fields of its result</td></tr></table>

Every hook is optional except convertToLlm. From AgentLoopConfig in agent/types.ts:193–342.

## The loop, state by state

There are two entry points. agent Loop(prompts, context, config, signal, streamFn) agent/agent-loop.ts:38 starts from new prompt messages and returns an EventStream<AgentEvent, AgentMessage[]>. agentLoopContinue(...) agent/agent-loop.ts:71 resumes from the existing context; it throws Cannot continue: no messages in context on an empty context and Cannot continue from message role: assistant when the last message is an assistant reply. Both have run… variants that take an event sink instead of returning a stream, and Agent uses those.

runAgentLoop agent/agent-loop.ts:102 declares any tool changes in front of the prompts, emits agent_start and turn_start, emits message_start and message_end for each prompt message, and hands over to run Loop agent/agent-

![](images/506c08668659c0d65ec99e027f2a8378392c0708c5bbe67892657732bfde0901.jpg)
The loop goes round while something needs a response, and stops only in three places. One run Loop call in agent/agent-loop.ts, schematic; numbers are line numbers at 28dcce2. The heavy amber arrows are the two ways back: the inner loop (tool results or steering) and the outer loop (follow-ups, or a finish Turn that asked to continue). The rose exit is the only one that skips the queues.

Read Fig. 3.1 (p. 51) top to bottom for one turn. The first pass skips prepareNextTurn, because runAgentLoop already emitted turn_start. Every later pass runs it, then emits its own turn_start. Pending messages are injected through declareToolChanges agent/agent-loop.ts:333, which compares the tools the runtime can execute (context.tools) with the tools the transcript has declared. A diference becomes tools Added or tools Removed on a system message: folded into a pending system message if there is one, otherwise a new empty-content system message inserted before the first non-system message. No diference, no message.

The model boundary is streamAssistantResponse agent/agent-loop.ts:381, and it is short enough to quote:

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

The provider start event pushes the partial message into the context and emits message_start. Each of the nine block events (text_*, thinking_*, toolcall_*) replaces the last message and emits message_update with the raw assistantMessageEvent. done and error await response.result(), stamp thinking Level on the final message, and emit message_end agent/agent-loop.ts:409.

The consequences are worth stating once:

A turn is one assistant response plus its tool calls and results. The AgentEvent type says so in a comment agent/types.ts:518.

Tool results feed back by being pushed onto current Context.messages agent/agent-loop.ts:274. The next pass streams a new response with them in context.

There is no turn limit. Nothing in run Loop counts turns.

The loop stops in exactly three places: a response with stop Reason "error" or "aborted" agent/agent-loop.ts:245; a finish Turn that returns {action: "end"} agent/agent-loop.ts:289; and a pass with no unterminated tool results, no steering, no follow-ups and no explicit continuation agent/agent-loop.ts:317.

On the error exit finish Turn still runs, but its decision is ignored; turn_end and agent_end follow at once agent/agentloop.ts:252.

## F O O T G U N
A response cut of by the output limit can carry tool calls whose arguments parse and validate but are incomplete. When stop Reason is "length", the loop runs none of them. Each gets the error result Tool call "<name>" was not executed: the response hit the output token limit, so its arguments may be truncated. Re-issue the tool call with complete arguments. agent/agent-loop.ts:493. The model sees errors, not results, and the loop goes round again.

## Steering versus follow-up

Two queues feed the loop from outside a run. Both hold AgentMessages and are drained by the hooks getSteeringMessages and getFollowUpMessages, which Agent wires to PendingMessageQueue instances agent/agent.ts:496. They difer only in where the loop polls them.

<table><tr><td></td><td>STEERING</td><td>FOLLOW-UP</td></tr><tr><td>API</td><td>agent.steer(msg)</td><td>agent.followUp(msg)</td></tr><tr><td>Intent</td><td>“to be injected after the current assistant turn finishes”agent/agent.ts:298</td><td>“run only after the agent would otherwise stop”agent/agent.ts:303</td></tr><tr><td>Polled at</td><td>loop start :176; after every turn_end :295; after prepareNextTurn if the last poll was empty :204</td><td>when the inner loop exits :302</td></tr><tr><td>Interrupts the current tool calls</td><td>no; “Tool calls from the current assistant message are not skipped”agent/types.ts:287</td><td>no</td></tr><tr><td>Interactive key</td><td>Enter while streaming</td><td>Alt+Enter (Ctrl+Q on Windows)</td></tr><tr><td>Drain mode</td><td>steering Mode: &quot;one-at-a-time&quot; (default) or &quot;all&quot;</td><td>followUpMode: the same</td></tr></table>

Steering waits for the current turn’s tools; follow-ups wait for the whole run. Poll sites from agent/agent-loop.ts; keys from app.message.followUp in CA/src/core/keybindings.ts:134 and the submit handler in CA/src/modes/interactive/interactive-mode.ts:3358.

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
PendingMessageQueue.peek and drain, lines 159–169, unchanged.

The re-poll after prepareNextTurn exists because that hook can run for seconds: the coding agent compacts there (compaction and branch summaries (p. 92)). The source explains the guard: “Only poll again if the earlier poll returned nothing; otherwise one-at-a-time mode would deliver two messages in this turn” agent/agent-loop.ts:202.

The capture kit queued one steering message and one follow-up from inside a running tool, then let the loop finish research/out/agent-loop-queues.txt. Steering entered as the user message of turn 2, straight after the tool results; the follow-up waited until turn 2 had produced a plain answer, then opened turn 3. One agent.prompt() produced three turns and one agent_end with 8 new messages.

## Tool execution

executeToolCalls agent/agent-loop.ts:508 picks a mode per batch. It runs sequentially when config.tool Execution === "sequential" or when any called tool declares execution Mode: "sequential"; otherwise in parallel, the default.

Every call is first prepared by prepareToolCall agent/agent-loop.ts:707, in order:

1. Find the tool by name. Unknown → error result Tool <name> not found.

2. Apply prepare Arguments, then validateToolArguments. A thrown error becomes the error text.

3. Call beforeToolCall. If the signal aborted meanwhile → Operation aborted. {block: true} → error result with reason, default Tool execution was blocked.

Any of those outcomes is immediate: the call never executes. Otherwise execute runs, and a thrown error becomes an isError: true result agent/agent-loop.ts:841. afterToolCall then overrides the result field by field: content, details, usage, terminate, structured Content and isError agent/agent-loop.ts:877. Replacing content without returning structured Content drops structured Content, “because it may no longer match the content” agent/types.ts:85.

![](images/371ca77ebc55e6518d138c5e32fad9bb137a8df7051ead095d0eb568a09854b6.jpg)

Preflight is sequential, execution is concurrent, and results come back in source order. Events 7–15 of research/out/agent-loop-queues.txt: the faux model asked for slow (id A) then fast (id B). tool_execution_end follows completion order (B before A); the tool Result messages follow the order of the calls in the assistant message (A before B). An immediate outcome emits its tool_execution_end during preflight.

In sequential mode each call runs start → prepare → execute → finalize → tool_execution_end → tool Result message before the next begins, and the batch stops early if the signal aborts agent/agent-loop.ts:575.

A batch ends the run early only if “every finalized tool result in the batch” sets terminate: true agent/agent-loop.ts:689. One result without it keeps the loop going.

runToolCall(tool Call, options) agent/agent-loop.ts:810 runs the same prepare → execute → finalize pipeline but “Emits no events and adds no messages”. The coding agent uses it for calls a tool makes through ctx.execute Tool() (extensions, loading and the API (p. 113)), which is how codemode runs its nested calls with the same permission hooks (codemode (p. 151)).

W H A T T H I S M E A N S F O R Y O U

Never throw from a StreamFn, convertToLlm, transform Context or a queue hook; return a failed message or a safe fallback.

Expect several tool_execution_end events in any order; match them by toolCallId, and read results in source order from the tool Result messages.

Use steering to redirect after the current tools finish, and follow-up to queue work for when the agent would stop.

Bound long runs yourself, in finish Turn or by aborting: the loop has no turn limit.

Sources: agent/types.ts (StreamFn, AgentTool, AgentToolResult, AfterToolCallResult, AgentLoopConfig, CustomAgentMessages, AgentEvent); agent/agent-loop.ts (agent Loop, agentLoopContinue, runAgentLoop, run Loop, declareToolChanges, streamAssistantResponse, failToolCallsFromTruncatedMessage, executeToolCalls, executeToolCallsSequential, executeToolCallsParallel, prepareToolCall, finalizeExecutedToolCall, shouldTerminateToolBatch, runToolCall); agent/agent.ts (PendingMessageQueue, createLoopConfig); agent/index.ts; CA/src/core/keybindings.ts:134; CA/src/modes/interactive/interactive-mode.ts:3358, 4435; CA/src/extensions/codemode/execute.ts:405; research/capture/agent-loop-queues.mjs; research/out/agent-loop-queues.txt; research/out/stats.txt

## 3.2 Agent events and the Agent class

Ten event types describe every run, nested as run, turn and message. The Agent class updates its statefrom each event before any listener sees it, and it stays busy until the last agent_end listener returns.

Everything that watches Pi work — the terminal UI, JSON and RPC output, extensions, the session file — is driven by one event stream. This section lists the ten AgentEvent types with their payloads and shows the order they arrive in from a real run. It then describes the Agent class that emits them: its defaults, its prompt and continue rules, its state reducer, and how it closes a run that threw.

## The ten events

AgentEvent is a discriminated union of ten members agent/types.ts:514. They come in three nested lifecycles and one tool lifecycle.

<table><tr><td>EVENT</td><td>PAYLOAD</td><td>EMITTED</td></tr><tr><td>agent_start</td><td>—</td><td>once, first event of a run</td></tr><tr><td>agent_end</td><td>messages: AgentMessage[]</td><td>once, last event of a run; messages are the run&#x27;s new messages</td></tr><tr><td>turn_start</td><td>—</td><td>before each assistant response</td></tr><tr><td>turn_end</td><td>message: AgentMessage, tool Results: ToolResultMessage[]</td><td>after the response and all its tool results</td></tr><tr><td>message_start</td><td>message: AgentMessage</td><td>for system, user, assistant, tool Result and custom messages</td></tr><tr><td>message_update</td><td>message, assistantMessageEvent: AssistantMessageEvent</td><td>assistant messages only, once per streamed block event</td></tr><tr><td>message_end</td><td>message: AgentMessage</td><td>when the message is final</td></tr><tr><td>tool_execution_start</td><td>toolCallId, tool Name, args</td><td>before a call is prepared</td></tr><tr><td>tool_execution_update</td><td>toolCallId, tool Name, args, partial Result</td><td>each onUpdate from a running tool</td></tr><tr><td>tool_execution_end</td><td>toolCallId, tool Name, result, isError</td><td>after afterToolCall, in completion order</td></tr></table>

Only assistant messages stream; every other message arrives as a start/end pair. From AgentEvent in agent/types.ts:514–529; emission sites in agent/agentloop.ts.

message_update carries the pi-ai event that caused it (text_delta, toolcall_end and so on, the streaming event protocol (p. 30)) and a shallow copy of the partial message. agent_end is the last event of a run, but the type’s own comment warns that awaited listeners “for that event are still part of run settlement. The agent becomes idle only after those listeners finish” agent/types.ts:510.

## The order, from a real run

The capture kit ran one prompt through a real AgentSession with the faux provider: the model reads hello.txt with one read call, then answers research/out/one-turn.txt. The subscriber saw 29 events. Fig. 3.3 (p. 58) shows them as the loop nests them.

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

A run is turns, a turn is messages, and tools sit between the assistant message and its results. The event stream of research/out/one-turn.txt, indented by lifecycle; 28 AgentEvents plus the session’s agent_settled. The number of text_delta events changes from run to run; the order does not. No tool_execution_update appears because read reports no partial results.

With two tool calls the skeleton holds, with the refinements shown in Fig. 3.2 (p. 55). In parallel mode all tool_execution_start events come before any tool_execution_end, and ends arrive in completion order. The tool Result messages follow in the order the calls appear in the assistant message. A steering message appears as a message_start/message_end pair for a user message right after the next turn_start; a tool-change declaration appears the same way as a system message research/out/agent-loop-queues.txt.

The first system message in the capture is not the system prompt seeded at construction. The coding agent constructs its Agent with an empty prompt and no tools, so no seed message exists. The first prompt carries a system message holding the prompt sections and tools Added for the four default tools; it is line 4 of the session file in the same capture (sessions, the JSONL tree (p. 86)).

## The Agent class

Agent agent/agent.ts:188 owns a transcript, the two queues of the agent loop (p. 49), a set of listeners and at most one active run. It turns its own fields into an AgentLoopConfig for every run agent/agent.ts:467 and passes process Events as the loop’s event sink.

<table><tr><td>OPTION</td><td>DEFAULT</td><td>SEE</td></tr><tr><td>convertToLlm</td><td>keeps system, user, assistant, tool Result; drops every other role</td><td>agent/agent.ts:38</td></tr><tr><td>streamFn</td><td>getDefaultStreamFn(), which throws No default stream function configured.Pass streamFn explicitly or call setDefaultStreamFn().</td><td>agent/stream-fn.ts:15</td></tr><tr><td>steering Mode,followUpMode</td><td>&quot;one-at-a-time&quot;</td><td>agent/agent.ts:247</td></tr><tr><td>transport</td><td>&quot;auto&quot;</td><td>agent/agent.ts:251</td></tr><tr><td>tool Execution</td><td>&quot;parallel&quot;</td><td>agent/agent.ts:253</td></tr><tr><td>initial State.model</td><td>a placeholder with id &quot;unknown&quot; and a context window of 0</td><td>agent/agent.ts:57</td></tr><tr><td>initial State.thinking Level</td><td>&quot;off&quot;</td><td>agent/agent.ts:93</td></tr></table>

An Agent built with no options has no model and no way to call one. Constructor at agent/agent.ts:230–254.

If initial State.messages does not start with a system message, createInitialSystemMessage(system Prompt, tools) is prepended, unless both are empty agent/agent.ts:85. state.system Prompt is a getter that replays the transcript’s system messages; there is no setter. Assigning state.tools or state.messages copies the top-level array agent/agent.ts:97. Two methods start a run:

prompt(input, images?) accepts a string, one message or an array. During a run it throws Agent is already processing a prompt. Use steer() or followUp() to queue messages, or wait for completion. agent/agent.ts:376.

continue() throws No messages to continue from if the transcript holds only system messages. If the last message is an assistant reply, it drains the steering queue and runs those messages; failing that, the follow-up queue; failing both, it throws Cannot continue from message role: assistant. Otherwise it calls runAgentLoopContinue agent/agent.ts:384.

![](images/e8bc6bb7a3a0ec0a6e98933690c3dcddfc52cca0369379c1709b4ca02bbc36ce.jpg)
isStreaming is cleared after the last listener returns, not when agent_end is emitted. agent/agent.ts, schematic; numbers are line numbers. Step 3 runs once per event. Step 4 runs in the catch and emits the closing events itself; step 5 runs in finally.

process Events agent/agent.ts:565 first reduces state, then awaits every listener in subscription order. A slow listener therefore slows the loop.

<table><tr><td>EVENT</td><td>STATE CHANGE</td></tr><tr><td>message_start, message_update</td><td>streaming Message = the message</td></tr><tr><td>message_end</td><td>streaming Message cleared; message pushed onto messages</td></tr><tr><td>tool_execution_start</td><td>toolCallId added to pendingToolCalls (a new Set)</td></tr><tr><td>tool_execution_end</td><td>toolCallId removed from pendingToolCalls (a new Set)</td></tr><tr><td>turn_end</td><td>error Message set if the assistant message has one</td></tr><tr><td>agent_end</td><td>streaming Message cleared</td></tr></table>

State is updated before listeners run, so a listener always reads the post-event state. process Events at agent/agent.ts:565–603.

handleRunFailure agent/agent.ts:532 covers a run that throws, for example from a hook that broke its no-throw contract. It builds an assistant message with empty text, zero usage, stop Reason "aborted" if the signal fired and "error" otherwise, and the thrown message as error Message. Then it emits message_start, message_end, turn_end and agent_end for it, so subscribers always see a closed run.

F O O T G U N

A synthesised failure run is not a well-formed run. handleRunFailure emits no agent_start or turn_start, and its agent_end carries only the failure message, not the messages the run produced before it threw. A subscriber that pairs starts with ends, or rebuilds the transcript from agent_end.messages, has to handle this case.

abort() aborts the active run’s signal. waitForIdle() resolves when the run and all its listeners have finished. reset() throws during a run; otherwise it keeps only the current system message and clears both queues agent/agent.ts:355.

W H A T T H I S M E A N S F O R Y O U

Use agent_end to learn that the loop has stopped emitting, and waitForIdle() to learn that the agent is idle.

Keep listeners fast: each one is awaited before the loop takes its next step.

Read tool results from message_end events with role tool Result, not from tool_execution_end, when order matters.

Inside a coding-agent session, wait for agent_settled (from prompt() to agent_settled (p. 67)), not agent_end.

Sources: agent/types.ts (AgentEvent, AgentState); agent/agent.ts (defaultConvertToLlm, DEFAULT_MODEL, createMutableAgentState, Agent constructor, prompt, continue, reset, createLoopConfig, runWithLifecycle, handleRunFailure, finish Run, process Events); agent/stream-fn.ts (getDefaultStreamFn); agent/agent-loop.ts (emission sites); ai/utils/transcript.ts (createInitialSystemMessage); CA/src/core/sdk.ts:393; research/capture/one-turn.mjs; research/out/one-turn.txt (§events, §session-jsonl); research/capture/agent-loop-queues.mjs; research/out/agent-loopqueues.txt

#### 3.3 Agent Session: wiring the runtime

AgentSession turns the generic Agent into a coding agent byfilling its hooks. The hook that matters most replaces the agent's messages with a projection of the sessionfile before every request, so thefile, not memory, decides what the model sees.

AgentSession (CA/src/core/agent-session.ts, 4,383 lines) wraps one Agent and adds persistence, model and thinking control, retry, compaction, user bash, tree navigation, the tool registry, the system prompt and extension dispatch. This section shows how sdk.ts builds the pair and how the four message roles the coding agent adds reach the model. It then covers the six hooks the session installs on the agent and the handler that writes each event to the session file.

## Construction in sdk.ts

createAgentSession builds the Agent first and the AgentSession around it CA/src/core/sdk.ts:393.

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
Lines 393–428. The … replaces a five-line comment on cache warming.

The prompt and tools start empty on purpose: the session adds them as a system message with the first prompt (from prompt() to agent_settled (p. 67)). buildRequestOptions CA/src/core/sdk.ts:322 adds the timeout (httpIdleTimeoutMs, where 0 means 2,147,483,647 ms), provider-level max Retries and maxRetryDelayMs, and a transform Headers that merges attribution headers and runs the extension before_provider_headers event. The three on… callbacks run the extension events before_provider_request, after_provider_response and provider_stream_event (extension events and contexts (p. 120)). tool Execution is not set, so the agent keeps the default "parallel".

After construction, a new session appends model_change and thinking_level_change entries CA/src/core/sdk.ts:436. They are lines 2 and 3 of the captured session file research/out/one-turn.txt.

## Four custom roles

CA/src/core/messages.ts extends CustomAgentMessages by declaration merging CA/src/core/messages.ts:70:

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

Lines 70–77, unchanged.

convertToLlm CA/src/core/messages.ts:148 turns each of them into a user message:

<table><tr><td>ROLE</td><td>SOURCE</td><td>BECOMES FOR THE MODEL</td></tr><tr><td>bash Execution</td><td>user ! cmd</td><td>user text: Ran, the command in backticks, the output in a fenced block or (no output), then (command cancelled) or Command exited with code N, then [Output truncated. Full output: path]; dropped under !! cmd</td></tr><tr><td>custom</td><td>extensions</td><td>user message with the same content; a string becomes one text block</td></tr><tr><td>branch Summary</td><td>tree navigation</td><td>usertext The following is a summary of a branch that this conversation came back from: +...&lt;/summary&gt;</td></tr><tr><td>compaction Summary</td><td>compaction</td><td>usertext The conversation history before this point was compacted into the following summary: +...&lt;/summary&gt;</td></tr><tr><td>system, user, assistant, tool Result</td><td>the loop</td><td>passed through</td></tr></table>

Every coding-agent role reaches the model as a user message, or not at all. bashExecutionToText and convertToLlm in CA/src/core/messages.ts:82–196; the prefixes are the constants at lines 11–24.

sdk.ts wraps this function once more. When the images.block Images setting is on, every image block in a user or tool-result message becomes the text Image reading is disabled., with consecutive placeholders collapsed into one CA/src/core/sdk.ts:279. The setting is read on every call, so a change takes efect on the next request.

## Six hooks on the Agent

The constructor subscribes to the agent and installs six hooks, in this order CA/src/core/agent-session.ts:501:

![](images/a509b3dc8609f57f0a351c8b0244076f63b57ba2b582f2e25dd1cb4c3d69aedb.jpg)
The session owns the agent’s hooks; the agent owns nothing but the loop. CA/src/core/agent-session.ts, constructor at lines 474–514; numbers are the line of each installer. Each installer keeps the previous hook and calls it, so the two transform Context projections run after the extension context handler set in sdk.ts. The highlighted hook is the one that makes the session file canonical.

The tool hooks map Pi’s extension events onto the loop’s hook contract. _beforeToolCall returns whatever the extension tool_call handlers return, so {block: true} blocks the call; an extension that throws a non-Error is rethrown as Extension failed, blocking execution: … CA/src/core/agent-session.ts:667. _afterToolCall runs the tool_result handlers, then normalises images in the content, including images an extension injected CA/src/core/agent-session.ts:692.

The request projection is the invariant. Before every request, prepare Request builds a projection of the session file and replaces the context’s messages with it CA/src/core/agent-session.ts:781. The projection is what sessions, the JSONL tree (p. 86) describes: the current branch, after compaction and context_edit entries. When the selected model is virtual, the same hook asks the model runtime to route this one request, and compacts first if the routed model’s window is exceeded CA/src/core/agent-session.ts:802.

## F O O T G U N
Assigning session.agent.state.messages does not change what the model sees. The next prepare Request discards the agent’s messages in favour of the session projection. To change the context, append entries through the session (a custom message, a context_edit, a compaction), then call session.refresh Context() if you need agent.state.messages to match before the next request.

prepareNextTurn does the between-turn work CA/src/core/agent-session.ts:892. It rebuilds the context from the projection, compacting first if the threshold is crossed (compaction and branch summaries (p. 92)). It difs the system-prompt sections against the transcript, returns a patch message if they changed, and applies the tool loadout. Last, it returns this.agent.state.model and thinking Level: this is how a model switch made mid-run reaches the next turn.

## Persistence in _handle Agent Event

_handleAgentEvent CA/src/core/agent-session.ts:1090 is the agent listener installed first. For each event it does six things in a fixed order:

![](images/c824ce847e30605d755a5ce8a830f61a35947a5b239c6bd49569d6a0551b1c22.jpg)

Listeners see a message before it is on disk. CA/src/core/agent-session.ts:1090–1183. Extensions run first and are awaited; public listeners are called synchronously; the session file is written last. An extension message_end handler that returns a replacement mutates the message in place, so the replacement is what step 5 persists.

Step 5 appends system, user, assistant and tool Result messages with append Message, and custom messages with appendCustomMessageEntry CA/src/core/agent-session.ts:1134. The other three roles are written elsewhere: bash results by recordBashResult, summaries by compaction and tree navigation. A successful assistant message (any stop Reason but "error") after a retry emits auto_retry_end with success: true and resets the retry counter CA/src/core/agentsession.ts:1163.

Step 6 exists because providers that validate message order reject a message between a tool call and its result. A custom message sent mid-run with trigger Turn: false is held in _pendingCustomMessages and appended at turn_end, after the turn’s tool results CA/src/core/agent-session.ts:2306.

## D O C ≠ C O D E

docs/json.md says entry_appended fires when “An extension appended a custom session entry through pi.append Entry().” The code emits it from five places: append Entry CA/src/core/agent-session.ts:3396, extension boundary drafts CA/src/core/agentsession.ts:1015, the context_edit entries that hide a failed attempt CA/src/core/agent-session.ts:1237, virtual-model state CA/src/core/agent-session.ts:822 and the cache warmer CA/src/core/agent-session.ts:485. It is never emitted for message entries: the capture appended five message entries during one prompt and emitted no entry_appended research/out/oneturn.txt.

## W H A T T H I S M E A N S F O R Y O U
Change what the model sees by appending session entries, never by editing agent.state.messages.

Do not read the session file from a message_end listener and expect that message to be there yet.

Use the extension message_end result to rewrite a message before it is persisted.

Watch message_end for message entries; entry_appended covers only the other kinds.

Sources: CA/src/core/sdk.ts (convertToLlmWithBlockImages, buildRequestOptions, new Agent, initial model_change/thinking_level_change); CA/src/core/messages.ts (BashExecutionMessage, CustomMessage, BranchSummaryMessage, CompactionSummaryMessage, bashExecutionToText, convertToLlm); CA/src/core/agent-session.ts (constructor, _installAgentToolHooks, _beforeToolCall, _afterToolCall, _installAgentRequestProjection, _installAgentBoundaryHooks, _installAgentNextTurnRefresh, _installHiddenDeclarationsProjection, _installAgentForcedPromptProjection, _handleAgentEvent, _emitExtensionEvent, sendCustomMessage, append Entry binding); CA/docs/json.md (Queue and state events); research/out/one-turn.txt (§events, §session-jsonl)

# 3.4 From prompt() to agent_settled

One call to session.prompt() can run the agent loop several times: once for the prompt, then again for each retry, overflow recovery and queued message. agent_end closes one of those runs; agent_settled closes the call.

AgentSession.prompt() is where typed text becomes a run, and it is the entry point the terminal UI, print mode, RPC and the SDK all share (run modes (p. 127)). This section follows a prompt through the checks before the loop starts, then through the post-run driver that decides whether to run again: automatic retry, compaction, queues and the agent_before_settle boundary. It ends with model and thinking control, user bash, and the full list of AgentSessionEvents.

## The prompt() pipeline

prompt(text, options) CA/src/core/agent-session.ts:1954 returns without starting a run in three ways — handled, queued or thrown — and starts one in a single way. Fig. 3.7 (p. 68) lists the checks in the order the code makes them.

![](images/1b2bcee55f1cf0fe22b479e2f9e0b1ad9751373b89b3f7dc0c6fa56fa86bf6e4.jpg)

Extension commands run even while the agent streams; everything else queues or waits. CA/src/core/agent-session.ts:1954–2097, first match wins; the quoted values are the PromptDisposition passed to preflight Result CA/src/core/agent-session.ts:301. Step 10’s first message is the system-prompt patch from _preparePromptAndToolLoadout, present only when the sections changed.

The order has consequences. Extension commands are tried before the compaction check and the streaming check, so /name commands work at any time. The input event sees the raw text before skill and template expansion CA/src/core/agentsession.ts:1978. before_agent_start runs before image normalisation, so a handler that switches the model also chooses the resize profile CA/src/core/agent-session.ts:2045. A prompt issued while agent_settled listeners are running is deferred until they return CA/src/core/agent-session.ts:1955.

The other entry points funnel into the same machinery:

steer(text) / followUp(text): run the input event and expansion, then queue. They throw Extension command "/<name>" cannot be queued. Use prompt() or execute the command when not streaming. CA/src/core/agentsession.ts:2260.

sendUserMessage(content, {deliverAs}): prompt() with source: "extension" and expandPromptTemplates defaulting to false CA/src/core/agent-session.ts:2375.

sendCustomMessage(msg, {trigger Turn, deliverAs}): deliverAs: "next Turn" holds the message for the next prompt; while streaming it is steered or followed up; idle with trigger Turn it starts a run; otherwise it is appended without a run CA/src/core/agent-session.ts:2279.

clear Queue(): empties both queues and returns {steering, followUp} as text, “Useful for restoring to editor when user aborts” CA/src/core/agent-session.ts:2383.

## The post-run driver

_runAgentPrompt CA/src/core/agent-session.ts:1808 wraps agent.prompt() in a loop that decides, after each run, whether to call agent.continue().

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
Lines 1817–1836, unchanged.

_handlePostAgentRun CA/src/core/agent-session.ts:1839 returns true, meaning run again, in three cases, checked in order:

1. The last assistant message is a retryable error and _prepareRetry scheduled a retry.

2. _checkCompaction compacted after an overflow or a recoverable length stop and wants the interrupted turn continued (compaction and branch summaries (p. 92)).

3. Messages are still queued, for example ones an agent_end handler queued after the loop drained both queues.

When it returns false, _runBeforeSettleBoundary gives extensions the last word through the agent_before_settle event CA/src/core/agent-session.ts:1879. A handler can append entries and ask to continue; the driver continues only if the projected context can be continued, and otherwise reports agent_before_settle requested continuation without runnable model context. With no handlers, it continues only if messages are queued.

2

![](images/e3410b7d27090b20874367ff276a1b8c57f7af9dd20a2e2e49073ccb89b8590b.jpg)

One prompt, two runs, two agent_ends, one agent_settled. A retried prompt in the order the code emits it, schematic, not a capture; message and turn events are left out. auto_retry_end comes from the second run’s assistant message_end CA/src/core/agent-session.ts:1163, so it precedes that run’s agent_end. A prompt that needs no retry has one run and one agent_end, as in Fig. 3.3 (p. 58).

## Automatic retry

A failed response is retryable when pi-ai’s isRetryableAssistantError says so and it is not a context overflow, which compaction handles instead CA/src/core/agent-session.ts:1694. isRetryableAssistantError requires stop Reason "error" and an error Message that matches the retryable-provider pattern and not the non-retryable-limit pattern ai/utils/retry.ts:250 (auth, cost, retries and the catalog (p. 41)).

<table><tr><td>SETTING</td><td>DEFAULT</td><td>EFFECT</td></tr><tr><td>retry.enabled</td><td>true</td><td>agent-level retry on or off</td></tr><tr><td>retry.max Retries</td><td>3</td><td>attempts after the first failure</td></tr><tr><td>retry.baseDelayMs</td><td>2000</td><td>delay before attempt 1</td></tr><tr><td>retry.maxAgentDelayMs</td><td>60000</td><td>cap on any one delay</td></tr></table>

Three retries wait 2 s, 4 s and 8 s. getRetrySettings in CA/src/core/settings-manager.ts:1000; the delay is baseDelayMs × 2^(attempt − 1), capped at maxAgentDelayMs ai/utils/retry.ts:126. The shipped settings table in CA/docs/settings.md agrees.

_prepareRetry CA/src/core/agent-session.ts:3747 increments the attempt counter and emits auto_retry_start {attempt, max Attempts, delayMs, error Message}. It then hides the failed message from the model with a context_edit entry whose replacement is null (_omitRecoveryAttempt): the attempt stays in the raw JSONL and disappears from the projection (sessions, the JSONL tree (p. 86)). After an abortable sleep, the driver calls agent.continue(). If the selected model is virtual, that request is routed with reason "retry" and the failed message as failed CA/src/core/agentsession.ts:810.

The attempt ends one of three ways. A later response that is not an error emits auto_retry_end {success: true}. Running out of attempts emits auto_retry_end {success: false, final Error} CA/src/core/agent-session.ts:1860. An abort during the sleep emits auto_retry_end with final Error: "Retry cancelled" CA/src/core/agent-session.ts:3739.

If your client needs “the model has finished answering”, wait for agent_settled. If it needs “this attempt failed”, read will Retry on agent_end: true means another run follows.

## Model and thinking control

set Model(model, {persist}) CA/src/core/agent-session.ts:2463 throws No API key for <provider>/<id> without auth. It then sets agent.state.model, appends a model_change entry, optionally saves the default model, applies a thinking level and emits the extension event model_select if the model changed. The level is chosen in this order: an explicit level (scoped models only), the per-model setting, the default-level setting, the current level, and finally "medium" CA/src/core/agent-session.ts:2655.

setThinkingLevel(level, {persist}) CA/src/core/agent-session.ts:2598 clamps the level to what the model supports. Only if the clamped level difers from the current one does it append thinking_level_change, emit thinking_level_changed, and fire the extension event thinking_level_select. With persist it saves the requested level, not the clamped one.

cycle Model(direction) CA/src/core/agent-session.ts:2505 cycles through the scoped models (--models or enabled Models) that are currently available, or through all available models when none are scoped. It returns undefined when there is at most one candidate.

A change made during a run takes efect on the next turn, not the current request. prepareNextTurn returns the current agent.state.model and thinking Level to the loop (AgentSession: wiring the runtime (p. 61)).

## User bash: !cmd and !!cmd

In the editor, !cmd runs a shell command and !!cmd runs it with excludeFromContext

CA/src/modes/interactive/interactive-mode.ts:3327. The mode, not the session, first emits the extension event user_bash CA/src/modes/interactive/interactive-mode.ts:6956. A handler can return a complete result, which is recorded with recordBashResult without running anything, or operations that replace local execution, for example to run over SSH or in a VM. RPC mode does the same for its bash command CA/src/modes/rpc/rpc-mode.ts:562.

execute Bash(command, onChunk?, {excludeFromContext, id, operations}) CA/src/core/agent-session.ts:3826 prepends the shellCommandPrefix setting on its own line, runs the command in the session’s working directory, and emits bash_execution_update {id, delta} for every chunk. recordBashResult then stores a BashExecutionMessage. If the agent is streaming, the record is held and appended when the run settles or before the next prompt, so it never lands between a tool call and its result CA/src/core/agent-session.ts:3877.

!!cmd output is shown and saved but never sent to the model: convertToLlm drops a bash Execution message with excludeFromContext set (AgentSession: wiring the runtime (p. 61)).

## Agent Session Event

AgentSessionEvent CA/src/core/agent-session.ts:191 is the AgentEvent stream with two changes, plus twelve event types of its own. Tool execution events of calls made through ctx.execute Tool() carry parentToolCallId, and agent_end gains will Retry.

<table><tr><td>EVENT</td><td>PAYLOAD</td><td>MEANING</td></tr><tr><td>agent_end</td><td>messages, will Retry</td><td>one low-level run ended; will Retry if an automatic retry follows</td></tr><tr><td>agent_settled</td><td>—</td><td>prompt() has no automatic work left</td></tr><tr><td>queue_update</td><td>steering: string[], followUp: string[]</td><td>the whole current text of both queues</td></tr><tr><td>compaction_start</td><td>reason: &quot;manual&quot; | &quot;threshold&quot; | &quot;overflow&quot;</td><td>compaction began</td></tr><tr><td>compaction_end</td><td>reason, result, aborted, will Retry, error Message?</td><td>compaction finished, failed or was aborted</td></tr><tr><td>entry_appended</td><td>entry</td><td>a non-message entry was appended (see AgentSession: wiring the runtime (p. 61))</td></tr><tr><td>session_info_changed</td><td>name</td><td>display name set or cleared</td></tr><tr><td>thinking_level_changed</td><td>level</td><td>the effective thinking level changed</td></tr><tr><td>auto_retry_start</td><td>attempt, max Attempts, delayMs, error Message</td><td>a retry is scheduled</td></tr><tr><td>auto_retry_end</td><td>success, attempt, finalized?</td><td>the retry sequence ended</td></tr><tr><td>summarization_retry_sched/_attempt_start/_finished</td><td>attempt data; source &quot;compaction&quot; or &quot;branch Summary&quot;</td><td>retries of a compaction or branch-summary request</td></tr><tr><td>bash_execution_update</td><td>id?, delta</td><td>a chunk of user-bash output</td></tr></table>

Twelve session events sit on top of the ten agent events. From the AgentSessionEvent union at CA/src/core/agent-session.ts:191–232; the three summarization_retry_* types share a row. RPC mode and the SDK (p. 133) shows them on the wire.

W H A T T H I S M E A N S F O R Y O U

Pass streaming Behavior on every prompt() that can arrive mid-run; without it the call throws.

Treat agent_settled as idle and agent_end as one attempt.

Tune retry.* in settings rather than retrying in your client; Pi already hides the failed attempt from the model.

Intercept user_bash to move ! commands to another machine; execute Bash itself does not emit it.

Sources: CA/src/core/agent-session.ts (AgentSessionEvent, PromptOptions, PromptDisposition, prompt, _runInputHandlers, steer, followUp, _throwIfExtensionCommand, sendCustomMessage, sendUserMessage, clear Queue, _runAgentPrompt, _handlePostAgentRun, _runBeforeSettleBoundary, _isRetryableError, _prepareRetry, _finishCancelledRetry, _omitRecoveryAttempt, set Model, cycle Model, setThinkingLevel, _getThinkingLevelForModelSwitch, execute Bash, recordBashResult, _flushPendingBashMessages); CA/src/core/settings-manager.ts:987, 1000; CA/src/core/defaults.ts:3; ai/utils/retry.ts (retryDelayMs, isRetryableAssistantError); CA/src/modes/interactive/interactive-mode.ts (submit handler, handleBashCommand); CA/src/modes/rpc/rpc-mode.ts:562; CA/docs/settings.md (retry.*)
