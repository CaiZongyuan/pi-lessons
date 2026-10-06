One event protocol in front of every vendor, so the rest of Pi never

sees a wire format.

![](images/37f527975d2723eedc8606a650350583c634fce7a3f2a0cb9e8b277d110f4afc.jpg)

## 2.1 Providers and models

A provider owns a vendor's models, auth and wireformat; a Models collection owns nothing but the routing. Everything above pi-ai talks to the collection and never learns which of 42 providers answered.

@earendil-works/pi-ai turns “a model plus a conversation” into one stream of events, whichever vendor sits behind it. This section names its two layers, the package entry points, and the core types every later part reuses: messages, content blocks, tools, models and thinking levels. It ends with the design choice that shapes the rest of Pi: the system prompt and the tool list live inside the transcript, not beside it.

#### Two layers: Provider and Models

The package has 151 source files and 23,581 non-blank lines, not counting 420 lines of generated catalog wrappers research/out/stats.txt §package-lines. Its runtime model has two layers, both declared in one file ai/models.ts.

F I G . 2 . 1 P I - A I I N O N E P A G E

L A Y E R S

↓ models.stream(model, context, options)

Models · create Models() normalize Context() → lazy Stream() → requireChatProvider → apply Auth (credential store, then ambient env) → header merge

↓ provider.stream(request Model, transcript, request Options)

↓ lazy Api: import api/<api-id>.ts on first use

anthropicmessages

openaicompletions openairesponses

google-* bedrockconversestream

… 10 chat APIs

↓ HTTP · SSE · WebSocket

vendor endpoint

One collection, many providers, one wire file per API. The collection resolves auth and routes; a provider owns its catalog and auth; an API module speaks one vendor protocol and is imported only on first use. Schematic, from ai/models.ts (create Models, create Provider), ai/api/lazy.ts and ai/api/*.lazy.ts.

A Provider is one runtime unit ai/models.ts:149. It carries id, name, optional base Url and headers, a required auth: ProviderAuth, a synchronous get Models(), and the two chat operations stream and stream Simple. The optional members are getAllModels, refresh Models, filter Models, filterAllModels, fetch Deferred, cancel Deferred, generate Images and classify. get Models() “Must not throw”; the collection treats a throwing provider as one with no models ai/models.ts:429.

A Models collection is built by create Models({ credentials?, models Store?, auth Context? }) ai/models.ts:990. Without arguments it uses an in-memory credential store, an in-memory models store and the default auth context ai/models.ts:398. The collection holds providers in a map keyed by id, resolves auth, normalises the context and delegates each request to the provider that owns the model. Its methods group into five families ai/models.ts:249:

<table><tr><td>FAMILY</td><td>METHODS</td><td>NOTES</td></tr><tr><td>Providers</td><td>get Providers,provider</td><td>MutableModels adds set Provider (upsert by id),delete Provider,clear Providers</td></tr><tr><td>Catalog reads</td><td>Models, get Model, modelsOfType, modelOfType, getAllModels, refresh</td><td>sync reads of last-known lists; refresh updates dynamic providers</td></tr><tr><td>Availability and auth</td><td>check Auth, get Available, getAvailableOfType, getAllAvailable, get Auth, login, logout</td><td>see auth, cost, retries and the catalog (p. 41)</td></tr><tr><td>Chat</td><td>stream, complete, stream Simple, complete Simple, stream Deferred, fetch Deferred, cancel Deferred</td><td>complete* await stream*().result()</td></tr><tr><td>One-shot</td><td>generate Images, classify</td><td>never reject; failures return an error result</td></tr></table>

Twenty-four methods, one routing rule: the model’s provider field picks the provider. From ai/models.ts:249–365 (interfaces Models, MutableModels).

Each API implementation lives in ai/api/<api-id>.ts and exports stream and stream Simple ai/types.ts:288. A sibling <api-id>.lazy.ts wraps it in lazy Api(() => import(...)), so a vendor SDK loads only when its first request is made ai/api/lazy.ts. Bedrock goes one step further and imports through a variable specifier, so bundlers cannot follow it into the Node-only AWS SDK ai/api/bedrock-converse-stream.lazy.ts.

Provider factories are thin. This is one in full:

```typescript
a complete provider factory packages/ai/src/providers/groq.ts TS export function groq Provider(): Provider<"openai-completions"> { return create Provider({
    id: "groq",
    name: "Groq",
    base Url: "https://api.groq.com/openai/v1",
    auth: { api Key: envApiKeyAuth("Groq API key", ["GROQ_API_KEY"]) },
    models: Object.values(GROQ_MODELS),
    api: openAICompletionsApi(),
    });
}
```
The four import lines above the function are cut.

create Provider accepts either one api for every chat model or a map keyed by model.api for mixed providers ai/models.ts:1024. GitHub Copilot, OpenCode and OpenRouter use the map form: their catalogs mix Anthropic, OpenAI Completions and OpenAI Responses models ai/providers/github-copilot.ts. A model whose api has no entry does not throw; its stream ends with Provider <id> has no API implementation for "<api>" ai/models.ts:1077. A provider with no api, images or classifiers at all is rejected at construction ai/models.ts:1051.

## Entry points

The package exports nine subpaths packages/ai/package.json (exports). Only ./compat and the image registration modules are declared side-efectful.

```txt
SUBPATH WHAT IT HOLDS
. Core, side-effect free: types, create Models, create Provider, the faux provider, transcript, retry, overflow and validation utilities
./models The model runtime alone (ai/models.ts)
./providers/* One factory per provider; ./providers/all adds builtin Providers(), builtin Models() and getBuiltinModel()
./api/* API implementations and their *.lazy wrappers
./utils/* Individual utility modules
./compat The old global API: stream, complete, UrModel, registerApiProvider, registerFauxProvider ... Labelled temporary
./oauth OAuth types for extensions, type-only
./bun-oauth Statically bundled OAuth flows for the standalone Bun binary
./bedrock-provider The Bedrock module as a static import, for the Bun binary
```

The root import is the light one. . loads no catalog and no provider; ./providers/all loads all 42. From packages/ai/package.json and ai/index.ts (header comment).

The README’s quick start uses the heavy path:

```javascript every provider, one model, one stream packages/ai/README.md TS
import { builtin Models } from '@earendil-works/pi-ai/providers/all';
// A Models collection with every built-in provider registered const models = builtin Models();
// Sync lookup against the collection const model = models.get Model('openai', 'gpt-4o-mini')!;
...
const s = models.stream(model, context);
```

Cut from README §Quick Start: the Type/Context/Tool import and the construction of context with one get_time tool are replaced by …. gpt-4o-mini is one of 44 entries in the pinned OpenAI catalog.

Extensions that import @earendil-works/pi-ai do not get the root. The coding agent’s virtual module map resolves that specifier, and the old @mariozechner/pi-ai name, to ./compat CA/src/core/extensions/virtual-modules.ts:26. Code written for an extension sees the legacy global API; code written against the npm package sees create Models(). See extensions, loading and the API (p. 113).

## Messages and content blocks

Four content block types and four message roles carry every conversation ai/types.ts:397.

<table><tr><td>BLOCK</td><td>FIELDS</td><td>NOTES</td></tr><tr><td>TextContent</td><td>type: &quot;text&quot;, text, text Signature?</td><td>signature holds provider message metadata, such as an OpenAI Responses message id</td></tr><tr><td>ThinkingContent</td><td>type: &quot;thinking&quot;, thinking, thinking Signature?, redacted?</td><td>signature is opaque replay data; when redacted, the encrypted payload sits in the signature</td></tr><tr><td>ImageContent</td><td>type: &quot;image&quot;, data (base64), mime Type</td><td>user and tool-result content only</td></tr><tr><td>ToolCall</td><td>type: &quot;tool Call&quot;, id, name, arguments: JsonObject, thought Signature?, namespace?</td><td>thought Signature is Google&#x27;s; namespace is OpenAI Responses&#x27;</td></tr></table>

Assistant content is text, thinking and tool calls; user content is text and images. From ai/types.ts:397–427.

SystemMessage ai/types.ts:524 — role: "system", content: string | TextContent[], sections?: Record<string, string | null>, tools Added?: Tool[], tools Removed?: ToolReference[], timestamp. The leading one is the system prompt; later ones change it.

```typescript
UserMessage ai/types.ts:542 — role: "user", content: string | (TextContent | ImageContent)[], timestamp.
```

AssistantMessage ai/types.ts:548 — content, the api, provider and model that produced it, usage, stop Reason, timestamp; optionally response Model (when the vendor served a diferent model), responseId, providerThinkingLevel, thinking Level, diagnostics, deferred, error Message, rawStopReason and end Turn.

ToolResultMessage ai/types.ts:596 — role: "tool Result", toolCallId, tool Name, content: (TextContent | ImageContent)[], isError, timestamp; optionally details, usage and nested Calls. nested Calls is kept for the session record and “not sent to the model”.

Usage ai/types.ts:429 — input, output, cache Read, cache Write, optional cacheWrite1h (Anthropic only) and reasoning (a subset of output), total Tokens, and cost with the same four parts plus total, in dollars.

StopReason ai/types.ts:452 — "pending" | "stop" | "length" | "tool Use" | "error" | "aborted" | "deferred". pending exists only while a stream is open.

Message is the union of the four roles ai/types.ts:612. The real assistant message on line 6 of the one-turn capture has every required field and one optional one, thinking Level research/out/one-turn.txt §session-jsonl.

## Tools, models and thinking levels

A Tool is name, description, a TypeBox parameters schema and an optional constrained Sampling setting ai/types.ts:717. That setting is false, { type: "json_schema", strict: "prefer" | "require" }, or { type: "grammar", variants } with openai_lark and openai_regex encodings. The built-in tools in the one-turn capture all declare json_schema with strict: "prefer" research/out/one-turn.txt §session-jsonl, line 4.

validateToolArguments(tool, tool Call) checks a call before it runs ai/utils/validation.ts:317. It clones the arguments, normalises optional nulls, runs TypeBox Value.Convert for coercion, applies JSON-schema coercion when the schema is not a TypeBox object, and checks. A failure throws Validation failed for tool "<name>": followed by one - path: message line per error and the received arguments as indented JSON.

Every catalog entry shares BaseModel: id, name, api, provider, base Url, input ("text", "image"), optional input Limits, cost and optional headers ai/types.ts:1099. A chat Model adds the fields below ai/types.ts:1113. ImageModel (type: "image", output) and ClassifierModel (type: "classifier", context Window) extend the same base.

<table><tr><td>FIELD</td><td>TYPE</td><td>MEANING</td></tr><tr><td>type</td><td>&quot;chat&quot;, optional</td><td>absent means chat</td></tr><tr><td>reasoning</td><td>boolean</td><td>whether thinking levels apply</td></tr><tr><td>thinkingLevelMap</td><td>Partial&lt;Recordレベル, string | null&gt;&gt;</td><td>provider value per Pi level; null = unsupported</td></tr><tr><td>prompt Cache</td><td>{ short?, long? } seconds</td><td>unset when cache lifetime is unknown</td></tr><tr><td>context Window,max Tokens</td><td>number</td><td>input window and output ceiling</td></tr><tr><td>cost</td><td>{ input, output, cache Read, cache Write, tiers? }</td><td>dollars per million tokens; see auth, cost, retries and the catalog (p. 41)</td></tr><tr><td>sampling Params, samplingParamsByThinkingLevel</td><td>records</td><td>merged into OpenAI-compatible request bodies</td></tr><tr><td>compat</td><td>one of five compat interfaces, chosen by api</td><td>per-model overrides of auto-detection</td></tr></table>

Limits, prices and quirks travel with the model. Adapters read the window, ceiling, cost and compat flags from the record they are handed. From ai/types.ts:1098–1172.

Pi has seven thinking levels: off, then ThinkingLevel = minimal, low, medium, high, xhigh, max ai/types.ts:85. getSupportedThinkingLevels(model) returns ["off"] for a model with reasoning: false ai/models.ts:1222. Otherwise it returns every level from off to high that is not mapped to null, plus xhigh and max only when the map names them. clampThinkingLevel keeps a supported level, else searches upward for the next supported one, else downward ai/models.ts:1233. A request for xhigh on a model without it becomes max when the map names max, and high otherwise.

Token-budget providers translate levels with DEFAULT_THINKING_BUDGETS: minimal 1,024, low 2,048, medium 8,192, high 16,384 tokens ai/api/simple-options.ts:70. xhigh and max use the high budget ai/api/simple-options.ts:77. When a budget shares the output ceiling, at least MIN_ANSWER_TOKENS = 1,024 tokens stay free for the answer ai/api/simple-options.ts:68.

## The system prompt lives in the transcript

Callers pass a Context: system Prompt?, messages, tools? ai/types.ts:734. Providers never see it. They receive a branded TranscriptContext that only normalize Context() can produce ai/types.ts:748. normalize Context folds the prompt and tools into a leading SystemMessage with content: system Prompt ?? "", tools Added: tools and timestamp: 0 ai/utils/transcript.ts:30. When both the prompt and the tool list are empty, it adds nothing, so an empty transcript stays empty ai/utils/transcript.ts:10.

Later system messages change the prompt in three ways. content appends instructions. sections replaces named sections, and null removes one. tools Added and tools Removed change the tool set. getCurrentSystemMessage and getCurrentTools replay the system messages one by one to get the current state ai/utils/transcript.ts:58.

![](images/d379ad35af3681a1fa59d90499f3ac549dd0ef917c6c110b8954d0f0d5b36840.jpg)

Appending keeps the cached prefix; collapsing rewrites it. resolve Transcript keeps later system messages in place only when the model’s compat says it accepts them; otherwise the replayed state leads and every later system message is dropped. Schematic, from ai/utils/transcript.ts:108–120 and ai/utils/text.ts (renderSystemMessageUpdate).

For a model that accepts system messages mid-conversation, a later one is sent where it stands. Section changes are framed as Updated system prompt section "<name>": followed by the value, or Removed system prompt section "<name>". ai/utils/text.ts:28. For every other model, collapseSystemMessages folds the replayed state into one leading message ai/utils/transcript.ts:108. The Google adapters always collapse ai/api/google-shared.ts:193. The compat flag supportsMidConvoSystemMessages defaults to false and is enabled by the generated catalog only for “verified models” ai/types.ts:847.

The reason for the design is the prompt cache. Changing a tool or a prompt section appends a message instead of rewriting the head of the request, so a provider that caches prefixes keeps its cache. The coding agent builds its prompt as named sections for this reason; see system prompt construction (p. 75).

W H A T T H I S M E A N S F O R Y O U

Import from @earendil-works/pi-ai for types and create Models; import single factories from ./providers/<id> when bundle size matters.

Treat AssistantMessage.provider, api and model as part of the record: replay rules in wire APIs and cross-provider hand-of(p. 36) depend on all three.

Change prompts and tools by appending system messages, not by editing the first one.

Use clampThinkingLevel before showing a level to a user; a model may support fewer than seven.

Sources: ai/models.ts (Provider :149, Models :249, MutableModels :360, ModelsImpl, create Models :990, create Provider :1039, getSupportedThinkingLevels :1222, clampThinkingLevel :1233). ai/types.ts (KnownApi :17, ThinkingLevel :85, content blocks :397–427, Usage :429, StopReason :452, messages :524–612, Tool :717, Context :734, TranscriptContext :748, compat :847, BaseModel/Model :1099–1146); ai/utils/transcript.ts (normalize Context, getCurrentSystemMessage, collapseSystemMessages, resolve Transcript). ai/utils/text.ts (renderSystemMessageUpdate); ai/utils/validation.ts:317; ai/api/simple-options.ts; ai/api/lazy.ts; ai/api/bedrock-converse-stream.lazy.ts; ai/providers/groq.ts; ai/index.ts; packages/ai/package.json (exports, side Effects); packages/ai/README.md §Quick Start; CA/src/core/extensions/virtualmodules.ts; research/out/stats.txt; research/out/one-turn.txt

## 2.2 The streaming event protocol

Every request in Pi returns the same stream of twelve event types, whatever the vendor. Failures do not throw; they arrive as the last event, and the stream is returned before auth is even resolved.

The agent loop, the TUI, RPC clients and extensions all read one protocol: AssistantMessageEvent. This section lists its events, states the ordering contract and draws it, and shows a real event stream captured from the faux provider. It then follows one models.stream() call from the caller to the adapter: lazy setup, auth, header merge and the options stream Simple adds.

## Twelve events

Every chat call returns an AssistantMessageEventStream ai/utils/event-stream.ts. It is an async iterable of events and also has result(): Promise<AssistantMessage>, which resolves with the message carried by the terminal done or error event. Events pushed after the terminal one are dropped.

<table><tr><td>EVENT</td><td>PAYLOAD BESIDES partial</td><td>MEANING</td></tr><tr><td>start</td><td>—</td><td>the vendor accepted the request; partial is the empty message, stop Reason: &quot;pending&quot;</td></tr><tr><td>text_start</td><td>content Index</td><td>a text block was appended at that index, empty</td></tr><tr><td>text_delta</td><td>content Index, delta</td><td>text appended to the block</td></tr><tr><td>text_end</td><td>content Index, content</td><td>the block&#x27;s final text</td></tr><tr><td>thinking_start · _delta · _end</td><td>as for text</td><td>the same three steps for a thinking block</td></tr><tr><td>toolcall_start</td><td>content Index</td><td>a tool-call block was appended</td></tr><tr><td>toolcall_delta</td><td>content Index, delta</td><td>a raw fragment of the arguments JSON</td></tr><tr><td>toolcall_end</td><td>content Index, tool Call</td><td>the parsed, final ToolCall</td></tr><tr><td>done</td><td>reason, message (no partial)</td><td>reason is stop, length, tool Use or deferred</td></tr><tr><td>error</td><td>reason, error (no partial)</td><td>reason is aborted or error; error is the final message</td></tr></table>

Three block kinds × start, delta, end, plus one opening and two closing events. From ai/types.ts:769–785.

The contract is written above the type:

## C O R E R U L E
“Successful streams emit start before partial updates and terminate with done. A stream may terminate directly with error when request setup fails before generation starts; after start, failures also terminate with . Direct calls throw synchronously when request auth is missing. Updates and must never appear before start.” ai/types.ts:753

![](images/b67d88ded7077be74f92f6157217a9c60d91fe5937b83f304c1f63419a93259a.jpg)
One opening, any number of blocks, exactly one terminal event. The second row is the path the CORE RULE allows: an error with no start. Schematic, from ai/types.ts:753–785; every transition was observed in research/out/streaming-protocol-events.txt.

Four rules come with the grammar ai/types.ts:762.

partial is live, not a snapshot. It is “the shared live response-so-far helper, not an event-time snapshot”. The Anthropic adapter pushes the same output object with every event ai/api/anthropic-messages.ts:658. Copy it if you need the state at one event.

Text and thinking grow only by deltas. Their blocks “are empty when their *_start event is emitted and grow only through their corresponding *_delta events until the authoritative *_end”. Redacted thinking is the exception: it “may be complete at start and emit no deltas”.

Tool-call arguments are always an object. toolcall_delta.delta is a raw JSON fragment. Adapters keep the concatenated string and re-parse it on each delta with parseStreamingJson, which tries JSON.parse with repair, then partial-json, then partial-json on the repaired string, and returns {} instead of throwing ai/utils/json-parse.ts:104.

Errors after the return are events, not exceptions. “Error termination must produce an AssistantMessage with stop Reason “error” or “aborted” and error Message, emitted via the stream protocol” ai/types.ts:371.

## A real stream

The capture kit scripts the faux provider (see auth, cost, retries and the catalog (p. 41)) with one thinking block, one text block and one tool call, and prints every event it receives through models.stream(). Token size is fixed at 4 tokens, so each delta carries 16 characters and the run is deterministic research/capture/streaming-protocol-events.mjs.

```txt
### $success (thinking + text + tool Call → done)
    1 start    · stop Reason=pending
    2 thinking_start [0] · stop Reason=pending
    3 thinking_delta [0] delta="The user wants t" · stop Reason=pending
    4 thinking_delta [0] delta="he file." · stop Reason=pending
    5 thinking_end [0] content="The user wants the file." · stop Reason=pending
    6 text_start [1] · stop Reason=pending
    7 text_delta [1] delta="Reading hello.tx" · stop Reason=pending
    8 text_delta [1] delta="t." · stop Reason=pending
    9 text_end [1] content="Reading hello.txt." · stop Reason=pending
    10 toolcall_start [2] · stop Reason=pending
    11 toolcall_delta [2] delta="{{\"path\":\"hello.t" · stop Reason=pending
    12 toolcall_delta [2] delta="xt\"}" · stop Reason=pending
    13 toolcall_end [2] tool Call={"id":"call_1","name":"read","arguments":{"path":"hello.txt"}} · stop Reason=pending
    14 done    reason=tool Use · stop Reason=tool Use
    result(): stop Reason=tool Use blocks=["thinking","text","tool Call"]

### $no-response (faux queue empty → error, no start)
    1 error    reason=error · stop Reason=error error Message="No more faux responses queued"
### $unconfigured (Provider is not configured → error, no start)
    1 error    reason=error · stop Reason=error error Message="Provider is not configured: nokey"
### $abort (signal aborted after first text_delta)
    1 start    · stop Reason=pending
    2 text_start [0] · stop Reason=pending
    3 text_delta [0] delta="This answer is l" · stop Reason=pending
    4 text_delta [0] delta="ong enough to be" · stop Reason=pending
    5 text_delta [0] delta=" cut off in the " · stop Reason=pending
    6 text_delta [0] delta="middle of stream" · stop Reason=pending
    7 error    reason=aborted · stop Reason=aborted error Message="Request was aborted"
    result(): stop Reason=aborted text="This answer is long enough to be cut off in the middle of stream"
```

Read the success run as the grammar in Fig. 2.3 (p. 31) walked once: one start, three blocks at indices 0, 1 and 2, one done. The tool call’s 20-character arguments arrive as two fragments, and only toolcall_end carries the parsed object. The same shape reaches the agent loop wrapped in message_update events; the one-turn capture shows it from that side research/out/oneturn.txt §events.

The next two runs end before start. An empty response queue and an unconfigured provider both produce a single error. The abort run shows two things. Deltas already queued when the signal fires are still delivered: the consumer aborted on event 3, the first delta, and received three more. The final message keeps the text streamed so far, and stop Reason is aborted, not error.

## F O O T G U N
The synchronous throw in the CORE RULE applies only when you call an adapter’s stream Simple() directly; the Anthropic adapter calls assertRequestAuth before it creates a stream ai/api/anthropic-messages.ts:933. Through Models, the same missing key is an error event, as the unconfigured run shows, because Models builds the stream first and resolves auth behind it. Code that handles both paths needs a try around the call and an error branch in the loop.

## How an adapter builds the message

The adapters share one six-step pattern, and the Anthropic adapter shows it in full ai/api/anthropic-messages.ts:571.

1. Create output with empty content, zero usage and stop Reason: "pending" ai/api/anthropic-messages.ts:582.

2. Send the request through retryProviderRequest, call onResponse with the status and headers, then push start ai/api/anthropic-messages.ts:649.

3. For each vendor block, push a block carrying scratch fields (index, partial Json) and emit *_start. Mutate it and emit *_delta. At the vendor’s block stop, delete the scratch fields and emit *_end.

4. Update usage whenever the vendor reports it, and call calculate Cost after each update ai/api/anthropicmessages.ts:688.

5. At the end, throw if the signal was aborted, if stop Reason is still pending (“Anthropic stream ended without a stop reason”), or if the vendor mapped the stop to error or aborted. Otherwise push done ai/api/anthropic-messages.ts:861.

6. In catch, strip the scratch fields, set stop Reason to aborted when the signal fired and error otherwise, set error Message, and push error ai/api/anthropic-messages.ts:887.

Because step 6 runs after any partial output, an errored or aborted message keeps its partial content and usage. wire APIs and cross-provider hand-of (p. 36) shows why such a message never reaches a model again.

For storage and replay, assistant-message-frame.ts defines AssistantMessageFrame: the same events without partial, with start carrying a cloned message, and one extra frame, toolcall_checkpoint { json }. Some adapters put initial arguments in toolcall_start and then stream the JSON again from empty; the encoder holds those deltas back and emits one checkpoint when they catch up with the snapshot ai/utils/assistant-message-frame.ts:236.

AssistantMessageFrameEncoder rejects out-of-order input, for example “Assistant message done event appears before start” ai/utils/assistant-message-frame.ts:153. reduceAssistantMessageFrames rebuilds the message ai/utils/assistantmessage-frame.ts:372. Terminal settlement “is intentionally excluded and must be persisted separately”.

## Request dispatch

Models.stream() returns its stream synchronously and does the rest behind it ai/models.ts:876.

![](images/596640f73bcf1817bde1657db33b594c679a76a52d9b33fd16a4a9ff3c366ab3.jpg)

The caller holds a stream before auth is resolved. Steps 1–2 happen inside Models; any throw in step 2, such as “Provider is not configured”, becomes a single error event. From ai/models.ts:876–890 (stream), :842–874 (apply Auth) and ai/api/lazy.ts (lazy Stream, forward Stream).

apply Auth builds the provider request ai/models.ts:842. It calls get Auth(model) with the request’s api Key, env and signal, throws ModelsError("auth", "Provider is not configured: <id>") when nothing resolves, and then assembles four things.

api Key — options.api Key ?? auth.api Key. An explicit key wins per request.

headers — merged case-insensitively in a fixed order, later sources overriding earlier ones: provider auth headers → model.headers (inside get Auth) → options.headers → options.transform Headers(), a hook that only Models accepts and strips before dispatch ai/models.ts:751 ai/models.ts:866.

env — the resolved credential’s provider-scoped values, overlaid by options.env.

base Url — auth.base Url, when set, replaces model.base Url for this request. GitHub Copilot’s OAuth toAuth derives it from the proxy-ep field of the Copilot token ai/auth/oauth/github-copilot.ts:65.

The capture kit sends one request through a spy provider to watch the merge research/capture/streaming-protocol-events.mjs:

```javascript auth.headers {"X-Auth":"auth","X-Model":"auth","X-Req":"auth","X-Drop":"auth"}
model.headers {"x-model":"model","X-Req":"model"}
options.headers {"x-req":"request","x-drop":null}
transform Headers received {"X-Auth":"auth","x-model":"model","x-req":"request","x-drop":null}
provider.stream headers={"X-Auth":"auth","x-model":"model","x-req":"request","x-drop":null,"X-
Last":"transform"} api Key="k-auth"
```

Three details are visible. A later source replaces an earlier header whatever its case, and the later spelling wins: X-Model arrives as x-model. A null value survives the merge; it is the adapter that drops it, because “A null value suppresses a provider/API default header with the same name” ai/types.ts:166. Provider.headers takes no part: Models never reads it ai/models.ts:842.

stream Simple adds one more layer. Adapters turn its provider-neutral options into their own with buildBaseOptions ai/api/simple-options.ts:36. It clamps max Tokens to context Window − estimated context tokens − 4,096, never below 1 ai/api/simple-options.ts:18. It merges sampling parameters as model.sampling Params, then samplingParamsByThinkingLevel[level] for the clamped level, then the request’s own, each key overriding the last ai/api/simple-options.ts:24. Only the OpenAI-compatible adapters send them ai/types.ts:202. The estimate is the one auth, cost, retries and the catalog (p. 41) describes.

W H A T T H I S M E A N S F O R Y O U

Handle error as a normal terminal event; check stop Reason on the result, not a try.

Clone partial if you keep it; the next event mutates it.

Render tool-call progress from partial.content[i].arguments, not by concatenating delta.

Put per-request headers in options.headers; use null to remove a default.

Sources: ai/types.ts (StreamOptions :189, contract :362–377, event protocol :753–785); ai/utils/event-stream.ts (EventStream, AssistantMessageEventStream); ai/utils/json-parse.ts:104 (parseStreamingJson); ai/utils/assistant-messageframe.ts (AssistantMessageFrame, AssistantMessageFrameEncoder, reduceAssistantMessageFrames); ai/api/anthropicmessages.ts (stream :571–901, stream Simple :928, create Client); ai/api/lazy.ts (lazy Stream, lazy Api). ai/models.ts (merge Headers :373, get Auth :742, apply Auth :842, stream :876); ai/api/simple-options.ts (clampMaxTokensToContext, resolveSamplingParams, buildBaseOptions); ai/auth/oauth/github-copilot.ts; research/capture/streaming-protocolevents.mjs; research/out/streaming-protocol-events.txt; research/out/one-turn.txt §events

# 2.3 Wire APIs and cross-provider hand-off

Ten adapter files translate one transcript into ten vendor protocols. Before any of them sends a byte, one shared function rewrites history so that a conversation started on one model can continue on another.

A session can start on Claude, switch to GPT halfway and finish on Gemini. That works only if every adapter can accept history written by every other. This section lists the ten chat wire APIs and what each does that the others do not, the replay data each keeps in its signatures, and Anthropic’s OAuth mode. It ends with transform Messages, the function that makes the switch safe, run on a real history.

## Ten chat APIs

KnownApi names ten chat protocols ai/types.ts:17. Each has one implementation file under ai/api/ and a .lazy.ts wrapper; the factory files under ai/providers/ import the wrappers they need research/out/stats.txt §api-files.

<table><tr><td>API</td><td>FILE · LINES</td><td>IMPORTED BY</td><td>WHAT IS SPECIFIC TO IT</td></tr><tr><td>anthropic-messages</td><td>anthropic-messages.ts·1,639</td><td>anthropic, kimi-coding, minimax, minimax-cn; also cloudflare-ai-gateway, fireworks, github-copilot, opencode, opencode-go, openrouter, vercel-ai-gateway</td><td>Own SSE parser. cache_control on the system blocks, the last tool and the last user or system message. Adaptive or budget thinking. Tool ids rewritten to [a-zA-Z0-9_-], at most 64 characters. Consecutive tool results sent as one user message. Server-side fallback models.</td></tr><tr><td>openai-completions</td><td>openai-completions.ts·1,734</td><td>27 factories, including groq, deepseek, cerebras, together, zai, xiaomi, qwen</td><td>detect Compat() from provider id and base Url, overridden per field by model.compat. Eleven thinking Formats. Reasoning read from reasoning_content, reasoning or reasoning_text. Tool ids at most 40 characters.</td></tr><tr><td>openai-responses</td><td>openai-responses.ts·419, shared·809</td><td>openai, xai, meta; also cloudflare-ai-gateway, github-copilot, opencode, opencode-go</td><td>store: false. prompt_cache_key from sessionId. Requests reasoning. encrypted_content. Tool ids call_id|item_id. developer role for reasoning models. Service-tier pricing.</td></tr><tr><td>azure-openai-responses</td><td>azure-openai-responses.ts·249, config·107</td><td>azure</td><td>AZURE_OPENAI_BASE_URL or AZURE_OPENAI_RESOURCE_NAME; AZURE_OPENAI_API_VERSION, default v1; AZURE_OPENAI_DEPLOYMENT_NAME_MAP as model=deployment pairs.</td></tr><tr><td>openai-codex-responses</td><td>openai-codex-responses.ts·1,697</td><td>openai-codex</td><td>ChatGPT subscription backend at chatgpt.com/backend-api/codex/responses. WebSocket per session: 5 min idle, 55 min maximum age, previous_response_id continuation. SSE fallback, with zstd-compressed request bodies when the runtime has zstdCompressSync.</td></tr><tr><td>google-generative-ai</td><td>google-generative-ai.ts·471, shared·515</td><td>google; also opencode</td><td>No mid-conversation system messages: always collapsed. thinking Level or thinking Budget by model. Thought signatures replayed only for the same provider and model, and only when valid base64. Missing tool ids generated.</td></tr><tr><td>google-vertex</td><td>google-vertex.ts·554, shared·515</td><td>google-vertex</td><td>As above, with Vertex auth.</td></tr></table>

Wire APIs and cross-provider hand-of

<table><tr><td>bedrock-converse-stream</td><td>bedrock-converse-stream.ts·1,373</td><td>amazon-bedrock</td><td>Node only, loaded through a variable specifier. Custom headers added by Smithy build middleware, so SigV4 covers them; x-amz-*-, authorization and host are skipped. cache Point only for caching-capable Claude models or AWS_BEDROCK_FORCE_CACHE=1. Redacted reasoning stored as base64.</td></tr><tr><td>mistral-conversations</td><td>mistral-conversations.ts·937</td><td>mistral</td><td>Tool call ids exactly 9 alphanumeric characters.</td></tr><tr><td>pi-messages</td><td>pi-messages.ts·444</td><td>radius; any custom backend</td><td>Pi&#x27;s own protocol: one POST of { model, context, options } to/messages, answered with SSE PiMessagesEvents.</td></tr></table>

One file per protocol, many providers per file. openai-completions alone is imported by 27 of the 42 factories. “Imported by” is the factory files that import the API’s lazy wrapper; a factory that imports several picks one per model through model.api. Line counts from wc -l at the pinned commit. Behaviours from ai/api/anthropic-messages.ts:1291, :1463; openai-completions.ts:273, :1211, :1593; openai-responses.ts:334–379. Also openai-responses-shared.ts:167, :215; azure-openai-config.ts; openai-codex-responses.ts:52, :218, :866–867. Also google-shared.ts:146–159; google-generative-ai.ts:196–200; bedrock-conversestream.ts:462–493, :870–880; mistral-conversations.ts:28.

Three more API families exist outside the chat path. openrouter-images generates images. typesafe-system-one, cloudflare-workers-ai-system-one and lama-cpp-classify are classifier APIs ai/types.ts:31 ai/types.ts:35. They are reached through generate Images and classify, never through stream.

The OpenAI Completions adapter is the one most providers share, so it carries the most switches. detect Compat recognises z.ai, Together, Moonshot, OpenRouter, Cloudflare, NVIDIA, Ant Ling, Cerebras, DeepSeek and others by provider id or URL fragment ai/api/openai-completions.ts:1593. Each detected value is a default that a field of model.compat replaces ai/api/openai-completions.ts:1710. The eleven thinking formats are openai, openrouter, deepseek, together, baseten, zai, qwen, chat-template, qwen-chat-template, string-thinking and ant-ling ai/types.ts:813. Custom endpoints configure the same fields in models.json; see configuration, models and auth (p. 99).

## Replay data in signatures

Reasoning models want their own reasoning back on the next turn, often encrypted. Pi keeps it in the signature fields of the content blocks, in a format that belongs to the API that wrote it.

<table><tr><td>API</td><td>thinking Signature HOLDS</td><td>OTHER SIGNATURES</td></tr><tr><td>anthropic-messages</td><td>Anthropic&#x27;s signature string, or the opaque data of a redacted_thinking block</td><td>—</td></tr><tr><td>openai-responses and relatives</td><td>the reasoning item serialised as JSON, including encrypted_content</td><td>text Signature: the message id or a TextSignatureV1 JSON</td></tr><tr><td>openai-completions</td><td>the name of the reasoning field it came from (reasoning_content,...), or serialised reasoning_details</td><td>—</td></tr><tr><td>bedrock-converse-stream</td><td>the signature, or base64 of the redacted bytes</td><td>—</td></tr><tr><td>google-*</td><td>the base64 thought signature</td><td>text Signature on text parts, thought Signature on tool calls</td></tr></table>

A signature is only meaningful to the API that wrote it. That is why Fig. 2.5 (p. 38) keeps signatures for the same model and drops them otherwise. From ai/api/anthropic-messages.ts:704–722, openai-responses-shared.ts:265, :692, openai-completions.ts:336, :1339–1347, bedrock-converse-stream.ts:655–691, google-shared.ts:231–266, ai/types.ts:391–427.

History is rewritten for the target model, never for the source. “Same model” means all three of provider, api and model match the target. Steps 0–3 run per message in a first pass; 4–5 run in a second pass that also holds a system message found between a call and its results until the results are out. From ai/api/transform-messages.ts:35–235.

## Anthropic OAuth mode

A Claude Pro or Max login stores an OAuth token, and the adapter recognises it by the substring sk-ant-oat ai/api/anthropicmessages.ts:978. With such a key it changes five things.

It sends the token as a Bearer auth Token, with user-agent: claude-cli/2.1.280 and x-app: cli ai/api/anthropicmessages.ts:1014.

It adds the betas claude-code-20250219 and oauth-2025-04-20, unless the caller set anthropic-beta explicitly ai/api/anthropic-messages.ts:1106.

It sends You are Claude Code, Anthropic's official CLI for Claude. as the first system block, ahead of Pi’s own prompt ai/api/anthropic-messages.ts:1167.

It renames tools to Claude Code’s casing on the way out: Read, Write, Edit, Bash, Grep, Glob and eleven more ai/api/anthropic-messages.ts:101.

It maps the names back on the way in, by case-insensitive match against the current tool list ai/api/anthropicmessages.ts:127.

The source labels this block “Stealth mode: Mimic Claude Code’s tool naming exactly” ai/api/anthropic-messages.ts:95.

#### Cross-provider hand-off: transform Messages

Nine of the ten chat adapters pass history through transform Messages(messages, model, normalizeToolCallId?) before converting it ai/api/transform-messages.ts:64. The six call sites cover Anthropic, Bedrock, both Google APIs through google-shared.ts, Mistral, OpenAI Completions, and the three Responses APIs through openai-responses-shared.ts ai/api/openai-responses-shared.ts:179. pi-messages does not call it: it posts the transcript as it is, and the backend owns the conversion ai/api/pi-messages.ts:5.

F I G . 2 . 5 W H A T T R A N S F O R M M E S S A G E S D O E S T O H I S T O R Y
![](images/f01be39d738f20df6896f3bcc7b5a0a139e0e51ec70c58bb341ee2bb283f2c6b.jpg)

The capture kit runs transform Messages on a five-message history written by openai/gpt-5 through openai-responses, once for the same model and once for a text-only Anthropic model with Anthropic’s id normaliser research/capture/wire-apistransform.mjs.

```txt
### $input (5 messages, written by openai/gpt-5)
1. user ["Look at this.", "<image>"]
2. assistant(tool Use) [{"thinking":"Need to read two files.", "sig":true,"redacted":false}, {"thinking":"[Reasoning redacted]", "sig":true,"redacted":true}, {"text":"Reading.", "sig":true}, {"tool Call":"call_abc|fc_0123456789"}, {"tool Call":"call_def|fc_9876543210"}
3. tool Result call_abc|fc_0123456789 isError=false ["A"]
4. assistant(aborted) [{"text":"Half an ans","sig":false}]
5. user "Go on."

### $same-model (openai/gpt-5, images supported) → 5 messages
1. user ["Look at this.", "<image>"]
2. assistant(tool Use) [{"thinking":"Need to read two files.", "sig":true,"redacted":false}, {"thinking":"[Reasoning redacted]", "sig":true,"redacted":true}, {"text":"Reading.", "sig":true}, {"tool Call":"call_abc|fc_0123456789"}, {"tool Call":"call_def|fc_987543210"}
3. tool Result call_abc|fc_0123456789 isError=false ["A"]
4. tool Result call_def|fc_9876543210 isError=true ["No result provided"]
5. user "Go on."

### $cross-model (anthropic/clau de-x, text only, Anthropic id normaliser) → 5 messages
1. user ["Look at this.", "(image omitted: model does not support images)]
2. assistant(tool Use) [{"text":"Need to read two files.", "sig":false}, {"text":"Reading.", "sig":false}, {"tool Call":"call_abc_fc_0123456789"}, {"tool Call":"call_def_fc_9876543210"}
3. tool Result call_abc_fc_0123456789 isError=false ["A"]
4. tool Result call_def_fc_9876543210 isError=true ["No result provided"]
5. user "Go on."
```

Both runs drop the aborted message 4 and insert a failed result for call_def, which never got one; the second pass does that for every target. Only the cross-model run touches content. The image becomes the placeholder text. The visible thinking becomes a plain text block, the redacted block disappears, and both signatures go. The pipe in each OpenAI Responses id becomes _, and the surviving tool result is remapped to the new id.

```txt
DOC ≠ CODE
```

The README says assistant messages from other providers “have their thinking blocks converted to text with <thinking> tags” packages/ai/README.md:1525. The code emits a plain text block with no tags ai/api/transform-messages.ts:113. The same README section says user and tool-result messages pass “unchanged” and tool calls are “preserved unchanged”; the capture above shows images replaced and ids rewritten. The requiresThinkingAsText compat flag repeats the mismatch: its doc comment promises “<thinking> delimiters” ai/types.ts:808, and the adapter’s own comment reads “plain text (no tags to avoid model mimicking them)” ai/api/openai-completions.ts:1324.

```txt
WHAT THIS MEANS FOR YOU
```

Switch models mid-session freely; history is rewritten per request and the stored session is untouched.

Expect the new model to see earlier reasoning as ordinary assistant text, and redacted reasoning not at all.

Do not rely on an aborted or failed turn being visible to the next request; it is skipped.

When you write a custom backend for pi-messages, do the hand-of rewriting yourself.

Sources: ai/types.ts:17–37 (KnownApi, image and classifier APIs), :391–427, :808, :813. ai/api/transform-messages.ts (transform Messages, downgradeUnsupportedImages). ai/api/anthropic-messages.ts (claudeCodeTools :95–131, create Client :982, getBetaFeatures :1080, build Params :1160–1195, normalizeToolCallId :1290, convert Messages :1463, cache control :1483). ai/api/openai-completions.ts (detect Compat :1593, normalizeToolCallId :1205, requiresThinkingAsText :1323). ai/api/openai-responses.ts; ai/api/openai-responses-shared.ts; ai/api/azure-openai-config.ts; ai/api/openai-codexresponses.ts. ai/api/google-shared.ts; ai/api/google-generative-ai.ts; ai/api/bedrock-converse-stream.ts; ai/api/mistralconversations.ts; ai/api/pi-messages.ts. ai/providers/*.ts (lazy API imports); packages/ai/README.md:1520–1527; research/capture/wire-apis-transform.mjs; research/out/wire-apis-transform.txt; research/out/stats.txt §api-files

## 2.4 Auth, cost, retries and the catalog

Every request needs a credential, a price list and a policyforfailure. pi-ai keeps a stored credential in charge ofits provider, prices tokensfrom a generated catalog of1,620 models, and retries only what a classifier calls transient.

The previous three sections followed a request that succeeds. This one covers what surrounds it: how a usage block becomes dollars, where a credential comes from and when it is refreshed, and which failures are retried. It ends with where the model catalog comes from and the faux provider that lets all of it run ofline.

## Cost

calculate Cost(model, usage) turns token counts into dollars, writes them into usage.cost and returns that object ai/models.ts:1198. Adapters call it after every usage update, so a stream’s partial carries a running cost.

```typescript tokens to dollars packages/ai/src/models.ts TS

export function calculate Cost(model: AnyModel, usage: Usage): Usage["cost"] {
    const input Tokens = usage.input + usage.cache Read + usage.cache Write;
    let rates: ModelCostRates = model.cost;
    let matched Threshold = -1;
    for (const tier of model.cost.tiers ?? []) {
    if (input Tokens > tier.inputTokensAbove && tier.inputTokensAbove > matched Threshold) {
    rates = tier;
    matched Threshold = tier.inputTokensAbove;
    }
    }

    // Anthropic charges 2x base input for 1h cache writes.
    const long Write = usage.cacheWrite1h ?? 0;
    const short Write = usage.cache Write - long Write;
    usage.cost.input = (rates.input / 1000000) * usage.input;
    usage.cost.output = (rates.output / 1000000) * usage.output;
    usage.cost.cache Read = (rates.cache Read / 1000000) * usage.cache Read;
    usage.cost.cache Write = (rates.cache Write * short Write + rates.input * 2 * long Write) / 1000000;
    usage.cost.total = usage.cost.input + usage.cost.output + usage.cost.cache Read + usage.cost.cache Write;
    return usage.cost;
}
```
Complete function, lines 1198–1218.

Rates are dollars per million tokens ai/types.ts:1058. A tier applies when the request’s whole input — fresh, cache-read and cache-written tokens together — exceeds its threshold, and then it prices every part of the request, output included ai/types.ts:1071. The capture kit priced four usage blocks against the pinned catalog research/capture/auth-cost-retriescost.mjs:

```txt anthropic/claudе-opus-5-5 rates={"input":4,"output":20,"cache Read":0.2,"cache Write":5}
usage input=2000 output=1000 cache Read=100000 cache Write=20000
cost input=$0.008000 output=$0.020000 cache Read=$0.020000 cache Write=$0.100000 total=$0.148000
usage ... cache Write=20000 cacheWrite1h=20000
cost input=$0.008000 output=$0.020000 cache Read=$0.020000 cache Write=$0.160000 total=$0.208000
openai/gpt-5.5 rates={"input":5,"output":30,"cache Read":0.5,"cache Write":0,"tiers":[{"inputTokensAbove":272000,"input":10,"output":45,"cache Read":1,"cache Write":0}]}
usage input=72000 output=1000 cache Read=200000 cache Write=0
cost input=$0.360000 output=$0.030000 cache Read=$0.100000 cache Write=$0.000000 total=$0.490000
usage input=72001 output=1000 cache Read=200000 cache Write=0
cost input=$0.720010 output=$0.045000 cache Read=$0.200000 cache Write=$0.000000 total=$0.965010
```

Two lessons are in those numbers. Writing 20,000 tokens to Anthropic’s one-hour cache costs \$0.16 instead of \$0.10, because it is priced at twice the input rate, not at the cache-write rate. And one more input token on gpt-5.5 moves 272,001 tokens past the threshold and nearly doubles the bill, from \$0.49 to \$0.97: the higher tier reprices the whole request.

The OpenAI Responses and Codex adapters then scale all four parts by the service tier the response reports: flex × 0.5, priority × 2, and × 2.5 for gpt-5.5 ai/api/openai-responses.ts:391 ai/api/openai-codex-responses.ts:602. The Responses adapter treats fast like priority.

## Credentials and their resolution

Auth has two halves: what is stored, and what each provider knows how to resolve ai/auth/types.ts.

Credential — “One type-tagged credential per provider — the shape of today’s auth.json” ai/auth/types.ts:36. Either ApiKeyCredential { type: "api_key", key?, env? } or OAuthCredential { type: "oauth", refresh, access, expires, … }.

CredentialStore — app-owned storage keyed by provider id, with read, list, modify and delete ai/auth/types.ts:65. modify(providerId, fn) “is the only write path”, serialised per provider and across processes where the backing store supports a lock. The coding agent’s auth.json is one implementation; see configuration, models and auth (p. 99).

ProviderAuth — { api Key?: ApiKeyAuth, oauth?: OAuthAuth }, at least one present ai/auth/types.ts:247. ApiKeyAuth.resolve() merges the stored key with ambient sources and returns undefined when the provider is unconfigured. OAuthAuth splits refresh (a network call) from toAuth (a pure derivation of request auth from a valid credential).

ModelAuth — what resolution produces: api Key?, headers?, base Url? ai/auth/types.ts:7. “If a value cannot be expressed as api Key, headers, or base Url, it is provider config, not auth.”

resolveProviderAuth decides which source wins ai/auth/resolve.ts:33. Its header comment states the policy: “A stored credential owns the provider: ambient/env is consulted only when nothing is stored. No silent env fallback after a failed refresh or for a credential type without a matching handler.”

![](images/abab912fae2e45e7a4a7c1a31b352493f95db6cf3365f2c3eee293d8df5a1e42.jpg)
Nothing stored is the only path to the environment. A stored credential of the wrong type yields “not configured”, not an environment key. First match wins, top to bottom. From ai/auth/resolve.ts:46–93.

An OAuth token is refreshed when it expires within five minutes, or within a longer window the caller asks for ai/auth/resolve.ts:169. The refresh runs inside credentials.modify(), re-checks expiry under the lock so that concurrent requests and processes refresh once, and is bounded by a 15-second timeout ai/auth/resolve.ts:119. The caller’s abort signal cancels only the wait for the lock: once a refresh has started, “the provider may already have rotated the refresh token”, and cancelling it “could discard the only valid refresh token” ai/auth/resolve.ts:110. A failed refresh surfaces as ModelsError code oauth, with the stored credential kept for a retry ai/models.ts:301.

Ambient keys come from one variable per provider ai/env-api-keys.ts:73:

<table><tr><td>PROVIDERS</td><td>VARIABLE</td></tr><tr><td>anthropic</td><td>ANTHROPIC_OAUTH_TOKEN, ANTHROPIC_API_KEY; ANTHROPIC_AUTH_TOKEN is discovered but must be sent as Authorization: Bearer</td></tr><tr><td>openai · azure · google · google-vertex</td><td>OPENAI_API_KEY · AZURE_OPENAI_API_KEY · GEMINI_API_KEY · GOOGLE_CLOUD_API_KEY</td></tr><tr><td>github-copilot · xai · groq · cerebras · mistral</td><td>COPILOT_GITHUB_TOKEN · XAI_API_KEY · GROQ_API_KEY · CEREBRAS_API_KEY · MISTRAL_API_KEY</td></tr><tr><td>openrouter · vercel-ai-gateway · deepseek · nvidia</td><td>OPENROUTER_API_KEY · AI_GATEWAY_API_KEY · DEEPSEEK_API_KEY · NVIDIA_API_KEY</td></tr><tr><td>together · baseten · huggingface · fireworks</td><td>TOGETHER_API_KEY · BASETEN_API_KEY · HF_TOKEN · FIREWORKS_API_KEY</td></tr><tr><td>moonshotai, moonshotai-cn · zai · zai-coding-cn</td><td>MOONSHOT_API_KEY · ZAI_API_KEY · ZAI_CODING_CN_API_KEY</td></tr><tr><td>minimax · minimax-cn · kimi-coding · meta</td><td>MINIMAX_API_KEY · MINIMAX_CN_API_KEY · KIMI_API_KEY · META_API_KEY</td></tr><tr><td>opencode, opencode-go · radius · typesafe · ant-ling</td><td>OPENCODE_API_KEY · RADIUS_API_KEY · TYPESAFE_API_KEY · ANT_LING_API_KEY</td></tr><tr><td>cloudflare-workers-ai, cloudflare-ai-gateway</td><td>CLOUDFLARE_API_KEY, plus CLOUDFLARE_ACCOUNT_ID and, for the gateway, CLOUDFLARE_GATEWAY_ID</td></tr><tr><td>qwen-token-plan (and -individual) · qwen-token-plan-cn</td><td>QWEN_TOKEN_PLAN_API_KEY · QWEN_TOKEN_PLAN_CN_API_KEY</td></tr><tr><td>xiaomi · xiaomi-token-plan-cn/-ams/-sgp</td><td>XIAOMI_API_KEY · XIAOMI_TOKEN_PLAN_CN_API_KEY, _AMS_, _SGP_</td></tr></table>

Forty of the 42 providers have an API-key variable; amazon-bedrock and openai-codex have none. Google Vertex also accepts Application Default Credentials with GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION; Bedrock accepts AWS_PROFILE, an access-key pair, AWS_BEARER_TOKEN_BEDROCK, ECS containe credentials or AWS_WEB_IDENTITY_TOKEN_FILE. From ai/env-api-keys.ts:73–127, :160–190, ai/providers/cloudflare-auth.ts. The full list with the coding agent’s own variables is in environment variables (p. 185).

Nine providers also ofer an OAuth login. The flows load lazily, through a variable import specifier, so bundles do not pull in Node-only callback servers ai/auth/oauth/load.ts.

<table><tr><td>PROVIDER</td><td>FLOW</td><td>DETAIL</td></tr><tr><td>anthropic</td><td>PKCE authorisation code</td><td>claude.ai/oauth/authorize; callback on port 53692, or a pasted code</td></tr><tr><td>openai-codex</td><td>PKCE, or device code</td><td>auth.openai.com; redirect localhost:1455/auth/callback; accountId read from the token&#x27;s chatgpt_account_id claim</td></tr><tr><td>openai (&quot;Sign in with ChatGPT&quot;)</td><td>PKCE with a dynamically registered client</td><td>callback on 127.0.0.1:1455</td></tr><tr><td>github-copilot</td><td>device code, then a Copilot token</td><td>toAuth takes base Url from the token&#x27;s proxy-ep; enterprise domains supported</td></tr><tr><td>openrouter</td><td>PKCE, then key exchange</td><td>the stored key never expires (expires: Number.MAX_SAFE_INTEGER)</td></tr><tr><td>kimi-coding · xai</td><td>device code</td><td>RFC 8628 device grant</td></tr><tr><td>meta</td><td>device code, then API-key mint</td><td>minted keys &quot;live about a day&quot;; refresh re-mints</td></tr><tr><td>radius</td><td>PKCE on 127.0.0.1:1456, or device code</td><td>per gateway</td></tr></table>

Every OAuth flow ends in the same OAuthCredential, and toAuth turns it into an API key, headers or a base URL. From ai/auth/oauth/*.ts (anthropic :15–20, openai-codex :23–26, :313, openai-chatgpt :16–25, github-copilot :60–85, openrouter :109, meta :7–12, radius :18–19).

## Retries, errors, overflow and abort

Failures are handled in two layers, and pi-ai supplies both.

Provider-level retry is retryProviderRequest ai/utils/provider-retry.ts:105. It reproduces the retry policy of the OpenAI and Anthropic SDKs, but with a sleep that the abort signal interrupts; the SDKs’ own timers ignore it, so adapters call the SDKs with max Retries: 0 and wrap the request ai/api/anthropic-messages.ts:647. It retries when the response header x-shouldretry is true, when there is no status, or on 408, 409, 429 and any status of 500 or above. The delay comes from retryafter-ms, then retry-after (seconds or a date), else min(0.5 × 2^i, 8) seconds less up to 25% jitter. A server-requested delay above maxRetryDelayMs (default 60,000) fails at once with Server requested <n>s retry delay (max: <m>s). so that the outer layer can show it. The attempt count defaults to options.max Retries ?? 0 ai/utils/providerretry.ts:109. Eight adapter files use it; Bedrock, Codex, Mistral and pi-messages do not.

Agent-level retry re-runs a whole assistant turn. isRetryableAssistantError looks only at stop Reason: "error" messages, rejects non-retryable patterns first, then accepts retryable ones ai/utils/retry.ts:250. The non-retryable list is quota and billing: insufficient_quota, quota exceeded, billing, OpenCode usage limits, ChatGPT subscription limits ai/utils/retry.ts:7. The retryable list covers overload, rate limits, 5xx codes, network and socket errors, WebSocket closes, premature stream ends such as “stream ended before message_stop”, and the retry-delay message above ai/utils/retry.ts:30. retryAssistantCall waits baseDelayMs × 2^(attempt−1), capped at 60 seconds by default, and never retries an abort ai/utils/retry.ts:126. The coding agent applies the classifier in AgentSession CA/src/core/agentsession.ts:52 and retryAssistantCall in compaction CA/src/core/compaction/compaction.ts:638; see AgentSession: wiring the runtime (p. 61).

Context overflow is a third verdict, checked before retry. isContextOverflow(message, context Window?) returns true in three cases ai/utils/overflow.ts:137:

1. stop Reason: "error" and the message matches one of 25 vendor patterns, such as prompt is too long, exceeds the context window or maximum context length is \d+ tokens, unless it also matches a throttling or rate-limit pattern. Cerebras’ body-less 400/413 counts too.

2. Silent overflow: stop Reason: "stop" with input + cache Read above the window, as z.ai does.

3. Length overflow: stop Reason: "length", zero output, and input + cache Read at 99% of the window or more, as Xiaomi MiMo does.

The capture kit ran both classifiers on sample messages, with a 200,000-token window:

```txt anthropic overflow overflow=true retryable=false bedrock throttling overflow=false retryable=false raw ThrottlingException overflow=true retryable=false overloaded overflow=false retryable=true quota overflow=false retryable=false retry-delay cap overflow=false retryable=true cerebras bodyless overflow=true retryable=false silent overflow (stop) overflow=true retryable=false length, zero output, 99% overflow=true retryable=false
```

## F O O T G U N
A Bedrock throttling error is neither retried nor treated as overflow. The adapter formats it as Throttling error: Too many tokens, please wait… ai/api/bedrock-converse-stream.ts:375. The overflow check excludes that prefix, and no retryable pattern matches “throttling”, so the turn fails. If the exclusion ever sees the raw SDK text ThrottlingException: Too many tokens…, /too many tokens/i fires and the turn is reported as a full context. Both rows above are from research/out/auth-costretries-cost.txt.

Overflow recovery needs a token count, and pi-ai estimates one without a tokenizer ai/utils/estimate.ts. It counts 4 characters per token and 4,800 characters per image. The context estimate is the usage of the last assistant message that succeeded and postdates every earlier message, plus an estimate of the messages after it ai/utils/estimate.ts:97. compaction and branch summaries (p. 92) keeps its own copy of the same method for agent messages

CA/src/core/compaction/compaction.ts:196; the streaming event protocol (p. 30) showed buildBaseOptions using it to clamp max Tokens.

Abort passes the caller’s signal to the SDK or fetch. An aborted message keeps the content and usage streamed so far, as the abort run in the streaming event protocol (p. 30) shows. It is skipped by the context estimate and by transform Messages on replay (wire APIs and cross-provider hand-of (p. 36)).

## The model catalog

The built-in catalog is generated, not written.

![](images/fe5edbe8d0cca833a94b79eb15292701a3aa17dcc7709a1bbd8f6f0552765199.jpg)
1,620 catalog entries: 1,537 chat, 60 image and 23 classifier models. npm run build runs generate-models before tsc; build:offline reuses the data. Counted from src/providers/data/.json at the pinned build; pipeline from packages/ai/package.json (scripts), scripts/generate-models.ts:1292–1771, src/providers/.models.ts and ai/providers/all.ts:136–191.

Each data file is grouped by API, then keyed "<type>:<id>"; groq.json begins {"openai-completions":{"chat:lama-3.1-8b-instant":{…}}} packages/ai/src/providers/data/groq.json. The type-level ChatModelCatalog maps those keys to literal types ai/model-catalog.ts:30, so getBuiltinModel("anthropic", "<id>") is typed per model ai/providers/all.ts:62. The repository’s agent rules forbid hand edits: “Never modify

packages/ai/src/models.generated.ts directly; update packages/ai/scripts/generate-models.ts instead, then regenerate” AGENTS.md.

Dynamic providers fetch their list at runtime. Radius implements refresh Models ai/providers/radius.ts:49;

create Provider ofers the same through fetch Models, publishing results through a generation check so that a superseded refresh cannot overwrite a newer one ai/models.ts:1091 ai/models.ts:503. Results persist through a ModelsStore ai/modelsstore.ts:22. The coding agent stores them in models-store.json in the agent directory, \~/.pi/agent by default CA/src/core/models-store.ts:52.

## The faux provider

faux Provider(options) is a real provider with scripted answers ai/providers/faux.ts:687. Every capture in this book uses it. It registers model faux-1 at http://localhost:0, zero prices, and an API-key auth that always resolves, so it needs no key ai/providers/faux.ts:24.

Responses — a queue set with set Responses or append Responses. Each step is an AssistantMessage built with fauxAssistantMessage, faux Text, faux Thinking and fauxToolCall, or a factory that receives the context, options, call state and model. An empty queue ends the stream with No more faux responses queued.

Streaming — each block is split into chunks of token Size tokens, 3–5 by default at 4 characters per token, and emitted as real deltas ai/providers/faux.ts:270. tokensPerSecond paces them; without it they are emitted as fast as the consumer reads.

Prompt caching — with a sessionId and cache Retention other than none, usage counts the common prefix with the previous prompt of that session as cache Read and the rest as cache Write ai/providers/faux.ts:230. The one-turn capture shows it: the first call writes 1,468 tokens, the second reads those 1,468 and writes 24 research/out/one-turn.txt §sessionjsonl.

Deferred responses — with deferred in the options, the stream ends with stop Reason: "deferred" and a handle; fetch Deferred returns the scripted answer after pending Fetches polls. It is the only built-in provider that implements fetch Deferred and cancel Deferred.

The coding agent’s test suite runs on it through the compat helper registerFauxProvider CA/test/suite/harness.ts:18, and the repository rules require it: “For packages/coding-agent/test/suite/, use test/suite/harness.ts + the faux provider. No real provider APIs, keys, or paid tokens” AGENTS.md.

W H A T T H I S M E A N S F O R Y O U

Remove a stored credential before expecting an environment key to take efect.

Set max Retries explicitly if you want provider-level retries outside the coding agent; pi-ai’s default is none.

Check isContextOverflow before isRetryableAssistantError: overflow wants compaction, not a retry.

Read usage.cost as an estimate from the catalog price, adjusted only for tiers, one-hour cache writes and OpenAI service tiers.

Test against faux Provider; it exercises the same event protocol as a vendor.

Sources: ai/models.ts (calculate Cost :1198, get Auth :742, refresh :551, publishProviderModels :503, create Provider :1039). ai/types.ts:1058–1073. ai/api/openai-responses.ts:391–419; ai/api/openai-codex-responses.ts:602–630. ai/auth/types.ts; ai/auth/resolve.ts; ai/auth/helpers.ts (envApiKeyAuth); ai/auth/oauth/*.ts. ai/env-api-keys.ts; ai/providers/cloudflare-auth.ts. ai/utils/provider-retry.ts; ai/utils/retry.ts; ai/utils/overflow.ts; ai/utils/estimate.ts; ai/api/bedrock-converse-stream.ts:375–410. scripts/generate-models.ts; ai/model-catalog.ts; ai/models.generated.ts; ai/providers/all.ts; ai/models-store.ts; CA/src/core/models-store.ts. ai/providers/faux.ts; CA/test/suite/harness.ts; AGENTS.md. research/capture/auth-cost-retries-cost.mjs; research/out/auth-cost-retriescost.txt; research/out/one-turn.txt

![](images/db1675e7b25e62706124c97222520d2e953aeffeac0035daf172db669fbe09ac.jpg)
