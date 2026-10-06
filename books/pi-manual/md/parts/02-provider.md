One event protocol in front of every vendor, so the rest of Pi never

sees a wire format.

在每个供应商前面都套一层统一的事件协议，这样 Pi 的其余部分就永远不必

看到各家不同的传输格式。

![](images/37f527975d2723eedc8606a650350583c634fce7a3f2a0cb9e8b277d110f4afc.jpg)

## 2.1 Providers and models

## 2.1 供应商与模型

A provider owns a vendor's models, auth and wireformat; a Models collection owns nothing but the routing. Everything above pi-ai talks to the collection and never learns which of 42 providers answered.

一个 Provider（供应商）拥有某家厂商的模型、鉴权方式和传输格式；Models 集合除了路由之外什么都不拥有。pi-ai 之上的一切都只与这个集合对话，永远不会知道 42 个供应商里究竟是哪一个作了回答。

@earendil-works/pi-ai turns “a model plus a conversation” into one stream of events, whichever vendor sits behind it. This section names its two layers, the package entry points, and the core types every later part reuses: messages, content blocks, tools, models and thinking levels. It ends with the design choice that shapes the rest of Pi: the system prompt and the tool list live inside the transcript, not beside it.

@earendil-works/pi-ai 把「一个模型加一段对话」变成一条统一的事件流，不管背后是哪家厂商。本节会介绍它的两层结构、各个包入口，以及后续每一部分都会复用的核心类型：消息、内容块、工具、模型和思考等级。最后会讲到那个塑造了 Pi 其余部分的设计选择：系统提示词和工具列表住在记录（transcript）里面，而不是并列放在旁边。

#### Two layers: Provider and Models

#### 两层：Provider 与 Models

The package has 151 source files and 23,581 non-blank lines, not counting 420 lines of generated catalog wrappers research/out/stats.txt §package-lines. Its runtime model has two layers, both declared in one file ai/models.ts.

这个包有 151 个源文件、23,581 行非空代码，不算 420 行生成的目录包装代码（research/out/stats.txt §package-lines）。它的运行时模型有两层，两层都在同一个文件 ai/models.ts 里声明。

F I G . 2 . 1 P I - A I I N O N E P A G E

图 2.1　PI-AI 的一个包

L A Y E R S

两层

↓ models.stream(model, context, options)

↓ provider.stream(request Model, transcript, request Options)

↓ lazy Api: import api/<api-id>.ts on first use

↓ lazy Api：首次使用时才 import api/<api-id>.ts

Models · create Models() normalize Context() → lazy Stream() → requireChatProvider → apply Auth (credential store, then ambient env) → header merge

Models · create Models() → normalize Context() → lazy Stream() → requireChatProvider → apply Auth（先查凭据存储，再查环境变量）→ 合并 header

anthropicmessages

anthropicmessages

openaicompletions openairesponses

openaicompletions openairesponses

google-* bedrockconversestream

google-* bedrockconversestream

… 10 chat APIs

……共 10 个对话 API

↓ HTTP · SSE · WebSocket

↓ HTTP · SSE · WebSocket

vendor endpoint

厂商端点

One collection, many providers, one wire file per API. The collection resolves auth and routes; a provider owns its catalog and auth; an API module speaks one vendor protocol and is imported only on first use. Schematic, from ai/models.ts (create Models, create Provider), ai/api/lazy.ts and ai/api/*.lazy.ts.

一个集合，多个供应商，每个 API 一个传输文件。集合负责解析鉴权并路由；供应商拥有自己的目录和鉴权；API 模块只讲一种厂商协议，且只在首次使用时才被导入。图示取自 ai/models.ts（create Models、create Provider）、ai/api/lazy.ts 和 ai/api/*.lazy.ts。

A Provider is one runtime unit ai/models.ts:149. It carries id, name, optional base Url and headers, a required auth: ProviderAuth, a synchronous get Models(), and the two chat operations stream and stream Simple. The optional members are getAllModels, refresh Models, filter Models, filterAllModels, fetch Deferred, cancel Deferred, generate Images and classify. get Models() “Must not throw”; the collection treats a throwing provider as one with no models ai/models.ts:429.

一个 Provider 是一个运行时单元（ai/models.ts:149）。它携带 id、name、可选的 base Url 和 headers、一个必需的 auth: ProviderAuth、一个同步的 get Models()，以及两个对话操作 stream 和 stream Simple。可选成员包括 getAllModels、refresh Models、filter Models、filterAllModels、fetch Deferred、cancel Deferred、generate Images 和 classify。get Models()「绝不能抛异常」；集合会把抛异常的供应商当作没有模型的供应商（ai/models.ts:429）。

A Models collection is built by create Models({ credentials?, models Store?, auth Context? }) ai/models.ts:990. Without arguments it uses an in-memory credential store, an in-memory models store and the default auth context ai/models.ts:398. The collection holds providers in a map keyed by id, resolves auth, normalises the context and delegates each request to the provider that owns the model. Its methods group into five families ai/models.ts:249:

Models 集合由 create Models({ credentials?, models Store?, auth Context? }) 构建（ai/models.ts:990）。不带参数时，它使用内存中的凭据存储、内存中的模型存储和默认的鉴权上下文（ai/models.ts:398）。集合把供应商放在一个以 id 为键的 map 里，解析鉴权、规范化上下文，并把每个请求委派给拥有该模型的供应商。它的方法可归为五类（ai/models.ts:249）：

<table><tr><td>类别</td><td>方法</td><td>备注</td></tr><tr><td>供应商</td><td>get Providers,provider</td><td>MutableModels 额外提供 set Provider（按 id upsert）、delete Provider、clear Providers</td></tr><tr><td>目录读取</td><td>Models, get Model, modelsOfType, modelOfType, getAllModels, refresh</td><td>同步读取最近已知的列表；refresh 更新动态供应商</td></tr><tr><td>可用性与鉴权</td><td>check Auth, get Available, getAvailableOfType, getAllAvailable, get Auth, login, logout</td><td>参见「鉴权、成本、重试与目录」（第 41 页）</td></tr><tr><td>对话</td><td>stream, complete, stream Simple, complete Simple, stream Deferred, fetch Deferred, cancel Deferred</td><td>complete* 内部就是 await stream*().result()</td></tr><tr><td>一次性</td><td>generate Images, classify</td><td>从不 reject；失败时返回一个错误结果</td></tr></table>

Twenty-four methods, one routing rule: the model’s provider field picks the provider. From ai/models.ts:249–365 (interfaces Models, MutableModels).

二十四个方法，一条路由规则：由模型的 provider 字段决定用哪个供应商。出自 ai/models.ts:249–365（接口 Models、MutableModels）。

Each API implementation lives in ai/api/<api-id>.ts and exports stream and stream Simple ai/types.ts:288. A sibling <api-id>.lazy.ts wraps it in lazy Api(() => import(...)), so a vendor SDK loads only when its first request is made ai/api/lazy.ts. Bedrock goes one step further and imports through a variable specifier, so bundlers cannot follow it into the Node-only AWS SDK ai/api/bedrock-converse-stream.lazy.ts.

每个 API 实现都放在 ai/api/<api-id>.ts，导出 stream 和 stream Simple（ai/types.ts:288）。同目录的 <api-id>.lazy.ts 用 lazy Api(() => import(...)) 把它包起来，这样某个厂商 SDK 只在第一次请求发出时才加载（ai/api/lazy.ts）。Bedrock 更进一步，它通过一个变量说明符来 import，这样打包器就无法跟进那个仅限 Node 的 AWS SDK（ai/api/bedrock-converse-stream.lazy.ts）。

Provider factories are thin. This is one in full:

供应商工厂都很薄。下面是一个完整例子：

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

函数上方的四行 import 被删去了。

create Provider accepts either one api for every chat model or a map keyed by model.api for mixed providers ai/models.ts:1024. GitHub Copilot, OpenCode and OpenRouter use the map form: their catalogs mix Anthropic, OpenAI Completions and OpenAI Responses models ai/providers/github-copilot.ts. A model whose api has no entry does not throw; its stream ends with Provider <id> has no API implementation for "<api>" ai/models.ts:1077. A provider with no api, images or classifiers at all is rejected at construction ai/models.ts:1051.

create Provider 既可以接受一个 api 供所有对话模型使用，也可以接受一个以 model.api 为键的 map，用于混合供应商（ai/models.ts:1024）。GitHub Copilot、OpenCode 和 OpenRouter 用的是 map 形式：它们的目录里混着 Anthropic、OpenAI Completions 和 OpenAI Responses 的模型（ai/providers/github-copilot.ts）。某个模型的 api 如果没有对应条目，并不会抛异常；它的流会以 Provider <id> has no API implementation for "<api>" 结束（ai/models.ts:1077）。而一个既无 api、无 images 也无 classifiers 的供应商，会在构造时被拒绝（ai/models.ts:1051）。

## Entry points

## 入口

The package exports nine subpaths packages/ai/package.json (exports). Only ./compat and the image registration modules are declared side-efectful.

这个包导出九条子路径（packages/ai/package.json 的 exports 字段）。只有 ./compat 和图像注册模块被声明为有副作用。

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

根导入是轻量的那一个。`.` 不加载任何目录和任何供应商；`./providers/all` 则加载全部 42 个。出自 packages/ai/package.json 和 ai/index.ts（头部注释）。

The README’s quick start uses the heavy path:

README 的快速上手用的是重的那条路径：

```javascript every provider, one model, one stream packages/ai/README.md TS
import { builtin Models } from '@earendil-works/pi-ai/providers/all';
// A Models collection with every built-in provider registered const models = builtin Models();
// Sync lookup against the collection const model = models.get Model('openai', 'gpt-4o-mini')!;
...
const s = models.stream(model, context);
```

Cut from README §Quick Start: the Type/Context/Tool import and the construction of context with one get_time tool are replaced by …. gpt-4o-mini is one of 44 entries in the pinned OpenAI catalog.

从 README §Quick Start 中删去了：Type/Context/Tool 的 import，以及用一个 get_time 工具构造 context 的那段代码，都用「……」代替。gpt-4o-mini 是固定版本 OpenAI 目录里 44 个条目之一。

Extensions that import @earendil-works/pi-ai do not get the root. The coding agent’s virtual module map resolves that specifier, and the old @mariozechner/pi-ai name, to ./compat CA/src/core/extensions/virtual-modules.ts:26. Code written for an extension sees the legacy global API; code written against the npm package sees create Models(). See extensions, loading and the API (p. 113).

导入 @earendil-works/pi-ai 的扩展拿不到根导出。编码智能体的虚拟模块映射会把那个说明符以及旧的 @mariozechner/pi-ai 名字一并解析到 ./compat（CA/src/core/extensions/virtual-modules.ts:26）。为扩展写的代码看到的是旧版全局 API；针对 npm 包写的代码看到的是 create Models()。参见「扩展、加载与 API」（第 113 页）。

## Messages and content blocks

## 消息与内容块

Four content block types and four message roles carry every conversation ai/types.ts:397.

四种内容块类型和四种消息角色承载了全部对话内容（ai/types.ts:397）。

<table><tr><td>块</td><td>字段</td><td>备注</td></tr><tr><td>TextContent</td><td>type: &quot;text&quot;, text, text Signature?</td><td>signature 保存供应商的消息元数据，例如 OpenAI Responses 的消息 id</td></tr><tr><td>ThinkingContent</td><td>type: &quot;thinking&quot;, thinking, thinking Signature?, redacted?</td><td>signature 是不透明的回放数据；当内容被涂黑时，加密后的载荷就放在 signature 里</td></tr><tr><td>ImageContent</td><td>type: &quot;image&quot;, data (base64), mime Type</td><td>只用于用户内容和工具结果内容</td></tr><tr><td>ToolCall</td><td>type: &quot;tool Call&quot;, id, name, arguments: JsonObject, thought Signature?, namespace?</td><td>thought Signature 是 Google 的；namespace 是 OpenAI Responses 的</td></tr></table>

Assistant content is text, thinking and tool calls; user content is text and images. From ai/types.ts:397–427.

助手内容是文本、思考和工具调用；用户内容是文本和图像。出自 ai/types.ts:397–427。

SystemMessage ai/types.ts:524 — role: "system", content: string | TextContent[], sections?: Record<string, string | null>, tools Added?: Tool[], tools Removed?: ToolReference[], timestamp. The leading one is the system prompt; later ones change it.

SystemMessage（ai/types.ts:524）—— role: "system"、content: string | TextContent[]、sections?: Record<string, string | null>、tools Added?: Tool[]、tools Removed?: ToolReference[]、timestamp。最前面的那条就是系统提示词，后面的那些用来修改它。

```typescript
UserMessage ai/types.ts:542 — role: "user", content: string | (TextContent | ImageContent)[], timestamp.
```

AssistantMessage ai/types.ts:548 — content, the api, provider and model that produced it, usage, stop Reason, timestamp; optionally response Model (when the vendor served a diferent model), responseId, providerThinkingLevel, thinking Level, diagnostics, deferred, error Message, rawStopReason and end Turn.

AssistantMessage（ai/types.ts:548）—— content、产出它的 api、provider 和 model、usage、stop Reason、timestamp；可选字段有 response Model（当厂商实际服务的是另一个模型时）、responseId、providerThinkingLevel、thinking Level、diagnostics、deferred、error Message、rawStopReason 和 end Turn。

ToolResultMessage ai/types.ts:596 — role: "tool Result", toolCallId, tool Name, content: (TextContent | ImageContent)[], isError, timestamp; optionally details, usage and nested Calls. nested Calls is kept for the session record and “not sent to the model”.

ToolResultMessage（ai/types.ts:596）—— role: "tool Result"、toolCallId、tool Name、content: (TextContent | ImageContent)[]、isError、timestamp；可选字段有 details、usage 和 nested Calls。nested Calls 是为会话记录保留的，「不会发给模型」。

Usage ai/types.ts:429 — input, output, cache Read, cache Write, optional cacheWrite1h (Anthropic only) and reasoning (a subset of output), total Tokens, and cost with the same four parts plus total, in dollars.

Usage（ai/types.ts:429）—— input、output、cache Read、cache Write、可选的 cacheWrite1h（仅 Anthropic）和 reasoning（output 的一个子集）、total Tokens，以及 cost（同样四部分再加上 total），单位是美元。

StopReason ai/types.ts:452 — "pending" | "stop" | "length" | "tool Use" | "error" | "aborted" | "deferred". pending exists only while a stream is open.

StopReason（ai/types.ts:452）—— "pending" | "stop" | "length" | "tool Use" | "error" | "aborted" | "deferred"。pending 只在流还开着的时候存在。

Message is the union of the four roles ai/types.ts:612. The real assistant message on line 6 of the one-turn capture has every required field and one optional one, thinking Level research/out/one-turn.txt §session-jsonl.

Message 是这四种角色的联合类型（ai/types.ts:612）。单轮捕获文件第 6 行里的那条真实助手消息包含了全部必需字段和一个可选字段 thinking Level（research/out/one-turn.txt §session-jsonl）。

## Tools, models and thinking levels

## 工具、模型与思考等级

A Tool is name, description, a TypeBox parameters schema and an optional constrained Sampling setting ai/types.ts:717. That setting is false, { type: "json_schema", strict: "prefer" | "require" }, or { type: "grammar", variants } with openai_lark and openai_regex encodings. The built-in tools in the one-turn capture all declare json_schema with strict: "prefer" research/out/one-turn.txt §session-jsonl, line 4.

一个 Tool 由 name、description、一个 TypeBox 参数 schema 和一个可选的受约束 Sampling 设置组成（ai/types.ts:717）。该设置是 false、`{ type: "json_schema", strict: "prefer" | "require" }`，或者带 openai_lark 与 openai_regex 两种编码的 `{ type: "grammar", variants }`。单轮捕获里的内置工具全部声明为 json_schema 加 strict: "prefer"（research/out/one-turn.txt §session-jsonl 第 4 行）。

validateToolArguments(tool, tool Call) checks a call before it runs ai/utils/validation.ts:317. It clones the arguments, normalises optional nulls, runs TypeBox Value.Convert for coercion, applies JSON-schema coercion when the schema is not a TypeBox object, and checks. A failure throws Validation failed for tool "<name>": followed by one - path: message line per error and the received arguments as indented JSON.

validateToolArguments(tool, tool Call) 会在一次工具调用真正运行前检查它（ai/utils/validation.ts:317）。它克隆参数、把可选的 null 归一化、运行 TypeBox 的 Value.Convert 做强制转换、在 schema 不是 TypeBox 对象时套用 JSON schema 的强制转换，然后做校验。校验失败会抛出 Validation failed for tool "<name>":，后面跟着每个错误一行「- 路径: 消息」，以及以缩进 JSON 呈现的收到的参数。

Every catalog entry shares BaseModel: id, name, api, provider, base Url, input ("text", "image"), optional input Limits, cost and optional headers ai/types.ts:1099. A chat Model adds the fields below ai/types.ts:1113. ImageModel (type: "image", output) and ClassifierModel (type: "classifier", context Window) extend the same base.

每个目录条目都共享 BaseModel：id、name、api、provider、base Url、input（"text"、"image"）、可选的 input Limits、cost 和可选的 headers（ai/types.ts:1099）。对话用的 Model 在此之上补充下列字段（ai/types.ts:1113）。ImageModel（type: "image"、output）和 ClassifierModel（type: "classifier"、context Window）扩展同一个基类。

<table><tr><td>字段</td><td>类型</td><td>含义</td></tr><tr><td>type</td><td>&quot;chat&quot;，可选</td><td>缺省即为对话</td></tr><tr><td>reasoning</td><td>boolean</td><td>是否适用思考等级</td></tr><tr><td>thinkingLevelMap</td><td>Partial&lt;Recordレベル, string | null&gt;&gt;</td><td>每个 Pi 等级对应的供应商取值；null 表示不支持</td></tr><tr><td>prompt Cache</td><td>{ short?, long? } 秒</td><td>缓存生命周期未知时不设置</td></tr><tr><td>context Window,max Tokens</td><td>number</td><td>输入窗口与输出上限</td></tr><tr><td>cost</td><td>{ input, output, cache Read, cache Write, tiers? }</td><td>每百万 token 的美元价格；参见「鉴权、成本、重试与目录」（第 41 页）</td></tr><tr><td>sampling Params, samplingParamsByThinkingLevel</td><td>记录</td><td>会被合并进 OpenAI 兼容的请求体</td></tr><tr><td>compat</td><td>五个 compat 接口之一，由 api 决定</td><td>对自动检测结果按模型做的覆盖</td></tr></table>

Limits, prices and quirks travel with the model. Adapters read the window, ceiling, cost and compat flags from the record they are handed. From ai/types.ts:1098–1172.

限额、价格和特殊之处都随模型一起走。适配器从交给它们的记录里读取窗口、上限、成本和 compat 标志。出自 ai/types.ts:1098–1172。

Pi has seven thinking levels: off, then ThinkingLevel = minimal, low, medium, high, xhigh, max ai/types.ts:85. getSupportedThinkingLevels(model) returns ["off"] for a model with reasoning: false ai/models.ts:1222. Otherwise it returns every level from off to high that is not mapped to null, plus xhigh and max only when the map names them. clampThinkingLevel keeps a supported level, else searches upward for the next supported one, else downward ai/models.ts:1233. A request for xhigh on a model without it becomes max when the map names max, and high otherwise.

Pi 有七个思考等级：off，以及 ThinkingLevel = minimal、low、medium、high、xhigh、max（ai/types.ts:85）。对 reasoning: false 的模型，getSupportedThinkingLevels(model) 返回 ["off"]（ai/models.ts:1222）。否则它返回从 off 到 high 之间所有未被映射为 null 的等级，另外只有当映射里点名了 xhigh 和 max 时才加上这两个。clampThinkingLevel 会保留一个受支持的等级，否则向上寻找下一个受支持的等级，再否则向下寻找（ai/models.ts:1233）。在不支持 xhigh 的模型上请求 xhigh 时，若映射里点名了 max 就变成 max，否则变成 high。

Token-budget providers translate levels with DEFAULT_THINKING_BUDGETS: minimal 1,024, low 2,048, medium 8,192, high 16,384 tokens ai/api/simple-options.ts:70. xhigh and max use the high budget ai/api/simple-options.ts:77. When a budget shares the output ceiling, at least MIN_ANSWER_TOKENS = 1,024 tokens stay free for the answer ai/api/simple-options.ts:68.

按 token 预算计费的供应商用 DEFAULT_THINKING_BUDGETS 来换算等级：minimal 1,024、low 2,048、medium 8,192、high 16,384 token（ai/api/simple-options.ts:70）。xhigh 和 max 使用 high 的预算（ai/api/simple-options.ts:77）。当预算与输出上限重合时，至少会为答案留出 MIN_ANSWER_TOKENS = 1,024 token（ai/api/simple-options.ts:68）。

## The system prompt lives in the transcript

## 系统提示词住在记录里

Callers pass a Context: system Prompt?, messages, tools? ai/types.ts:734. Providers never see it. They receive a branded TranscriptContext that only normalize Context() can produce ai/types.ts:748. normalize Context folds the prompt and tools into a leading SystemMessage with content: system Prompt ?? "", tools Added: tools and timestamp: 0 ai/utils/transcript.ts:30. When both the prompt and the tool list are empty, it adds nothing, so an empty transcript stays empty ai/utils/transcript.ts:10.

调用方传入一个 Context：system Prompt?、messages、tools?（ai/types.ts:734）。供应商从来看不到它。他们拿到的是一个带品牌标记的 TranscriptContext，只有 normalize Context() 能生成它（ai/types.ts:748）。normalize Context 把提示词和工具折叠进一条开头的 SystemMessage，其中 content: system Prompt ?? ""、tools Added: tools、timestamp: 0（ai/utils/transcript.ts:30）。当提示词和工具列表都为空时，它什么都不加，所以空的记录仍然是空的（ai/utils/transcript.ts:10）。

Later system messages change the prompt in three ways. content appends instructions. sections replaces named sections, and null removes one. tools Added and tools Removed change the tool set. getCurrentSystemMessage and getCurrentTools replay the system messages one by one to get the current state ai/utils/transcript.ts:58.

后续的系统消息通过三种方式修改提示词。content 追加指令。sections 替换具名小节，传 null 则删除某个小节。tools Added 和 tools Removed 改变工具集合。getCurrentSystemMessage 和 getCurrentTools 逐条重放系统消息，以得到当前状态（ai/utils/transcript.ts:58）。

![](images/d379ad35af3681a1fa59d90499f3ac549dd0ef917c6c110b8954d0f0d5b36840.jpg)

Appending keeps the cached prefix; collapsing rewrites it. resolve Transcript keeps later system messages in place only when the model’s compat says it accepts them; otherwise the replayed state leads and every later system message is dropped. Schematic, from ai/utils/transcript.ts:108–120 and ai/utils/text.ts (renderSystemMessageUpdate).

追加会保住已缓存的前缀；折叠则会重写它。resolve Transcript 只有在模型的 compat 表示接受这些消息时，才把后续系统消息留在原位；否则由重放得到的状态打头，所有后续系统消息都被丢弃。图示取自 ai/utils/transcript.ts:108–120 和 ai/utils/text.ts（renderSystemMessageUpdate）。

For a model that accepts system messages mid-conversation, a later one is sent where it stands. Section changes are framed as Updated system prompt section "<name>": followed by the value, or Removed system prompt section "<name>". ai/utils/text.ts:28. For every other model, collapseSystemMessages folds the replayed state into one leading message ai/utils/transcript.ts:108. The Google adapters always collapse ai/api/google-shared.ts:193. The compat flag supportsMidConvoSystemMessages defaults to false and is enabled by the generated catalog only for “verified models” ai/types.ts:847.

对于接受对话中途系统消息的模型，后续的那条会就地在它所在的位置发出。小节变更会被包装成 Updated system prompt section "<name>" 加值，或者 Removed system prompt section "<name>"（ai/utils/text.ts:28）。对其他所有模型，collapseSystemMessages 会把重放得到的状态折叠成一条开头的消息（ai/utils/transcript.ts:108）。Google 的适配器总是折叠（ai/api/google-shared.ts:193）。compat 标志 supportsMidConvoSystemMessages 默认为 false，只有生成的目录才对「已验证模型」把它打开（ai/types.ts:847）。

The reason for the design is the prompt cache. Changing a tool or a prompt section appends a message instead of rewriting the head of the request, so a provider that caches prefixes keeps its cache. The coding agent builds its prompt as named sections for this reason; see system prompt construction (p. 75).

这个设计的理由是提示词缓存。改动一个工具或一个提示词小节时，是追加一条消息，而不是重写请求的头部，这样会缓存前缀的供应商就能保住它的缓存。编码智能体正是出于这个原因才把提示词构造成具名小节的；参见「系统提示词的构建」（第 75 页）。

W H A T T H I S M E A N S F O R Y O U

这对你意味着什么

Import from @earendil-works/pi-ai for types and create Models; import single factories from ./providers/<id> when bundle size matters.

类型和 create Models 从 @earendil-works/pi-ai 导入；当打包体积要紧时，从 ./providers/<id> 导入单个工厂。

Treat AssistantMessage.provider, api and model as part of the record: replay rules in wire APIs and cross-provider hand-of(p. 36) depend on all three.

把 AssistantMessage 的 provider、api 和 model 当作记录的一部分：通信API 与跨供应商转交中的回放规则（第 36 页）依赖这三者。

Change prompts and tools by appending system messages, not by editing the first one.

通过追加系统消息来修改提示词和工具，而不是去编辑第一条。

Use clampThinkingLevel before showing a level to a user; a model may support fewer than seven.

在把某个等级展示给用户之前先调用 clampThinkingLevel；一个模型支持的等级可能少于七个。

Sources: ai/models.ts (Provider :149, Models :249, MutableModels :360, ModelsImpl, create Models :990, create Provider :1039, getSupportedThinkingLevels :1222, clampThinkingLevel :1233). ai/types.ts (KnownApi :17, ThinkingLevel :85, content blocks :397–427, Usage :429, StopReason :452, messages :524–612, Tool :717, Context :734, TranscriptContext :748, compat :847, BaseModel/Model :1099–1146); ai/utils/transcript.ts (normalize Context, getCurrentSystemMessage, collapseSystemMessages, resolve Transcript). ai/utils/text.ts (renderSystemMessageUpdate); ai/utils/validation.ts:317; ai/api/simple-options.ts; ai/api/lazy.ts; ai/api/bedrock-converse-stream.lazy.ts; ai/providers/groq.ts; ai/index.ts; packages/ai/package.json (exports, side Effects); packages/ai/README.md §Quick Start; CA/src/core/extensions/virtualmodules.ts; research/out/stats.txt; research/out/one-turn.txt

来源：ai/models.ts（Provider :149、Models :249、MutableModels :360、ModelsImpl、create Models :990、create Provider :1039、getSupportedThinkingLevels :1222、clampThinkingLevel :1233）。ai/types.ts（KnownApi :17、ThinkingLevel :85、内容块 :397–427、Usage :429、StopReason :452、各类消息 :524–612、Tool :717、Context :734、TranscriptContext :748、compat :847、BaseModel/Model :1099–1146）；ai/utils/transcript.ts（normalize Context、getCurrentSystemMessage、collapseSystemMessages、resolveTranscript）。ai/utils/text.ts（renderSystemMessageUpdate）；ai/utils/validation.ts:317；ai/api/simple-options.ts；ai/api/lazy.ts；ai/api/bedrock-converse-stream.lazy.ts；ai/providers/groq.ts；ai/index.ts；packages/ai/package.json（exports、side Effects）；packages/ai/README.md §Quick Start；CA/src/core/extensions/virtual-modules.ts；research/out/stats.txt；research/out/one-turn.txt

## 2.2 The streaming event protocol

## 2.2 流式事件协议

Every request in Pi returns the same stream of twelve event types, whatever the vendor. Failures do not throw; they arrive as the last event, and the stream is returned before auth is even resolved.

Pi 中的每个请求都返回同一条由十二种事件类型组成的流，不管厂商是谁。失败不会抛异常；它们作为最后一个事件到来，而且在鉴权都还没解析完时流就已经返回了。

The agent loop, the TUI, RPC clients and extensions all read one protocol: AssistantMessageEvent. This section lists its events, states the ordering contract and draws it, and shows a real event stream captured from the faux provider. It then follows one models.stream() call from the caller to the adapter: lazy setup, auth, header merge and the options stream Simple adds.

智能体循环、TUI、RPC 客户端和扩展读的都是同一套协议：AssistantMessageEvent。本节会列出它的事件，说明顺序约定并画出来，并展示一段从 faux 供应商捕获的真实事件流。然后它会跟随一次 models.stream() 调用，从调用方一路走到适配器：惰性初始化、鉴权、header 合并，以及 stream Simple 所补充的选项。

## Twelve events

## 十二种事件

Every chat call returns an AssistantMessageEventStream ai/utils/event-stream.ts. It is an async iterable of events and also has result(): Promise<AssistantMessage>, which resolves with the message carried by the terminal done or error event. Events pushed after the terminal one are dropped.

每次对话调用都返回一个 AssistantMessageEventStream（ai/utils/event-stream.ts）。它是一个事件的异步可迭代对象，同时还有 result(): Promise<AssistantMessage>，该 promise 以终止事件 done 或 error 所携带的消息 resolve。终止事件之后被推入的事件会被丢弃。

<table><tr><td>事件</td><td>除 partial 外的载荷</td><td>含义</td></tr><tr><td>start</td><td>—</td><td>厂商已接受请求；partial 是空消息，stop Reason: &quot;pending&quot;</td></tr><tr><td>text_start</td><td>content Index</td><td>在该索引处追加了一个文本块，初始为空</td></tr><tr><td>text_delta</td><td>content Index, delta</td><td>向该块追加文本</td></tr><tr><td>text_end</td><td>content Index, content</td><td>该块的最终文本</td></tr><tr><td>thinking_start · _delta · _end</td><td>与文本相同</td><td>思考块的同样三步</td></tr><tr><td>toolcall_start</td><td>content Index</td><td>追加了一个工具调用块</td></tr><tr><td>toolcall_delta</td><td>content Index, delta</td><td>参数 JSON 的原始片段</td></tr><tr><td>toolcall_end</td><td>content Index, tool Call</td><td>已解析的最终 ToolCall</td></tr><tr><td>done</td><td>reason, message（无 partial）</td><td>reason 是 stop、length、tool Use 或 deferred</td></tr><tr><td>error</td><td>reason, error（无 partial）</td><td>reason 是 aborted 或 error；error 是最终消息</td></tr></table>

Three block kinds × start, delta, end, plus one opening and two closing events. From ai/types.ts:769–785.

三种块类型 × start、delta、end，再加一个开场事件和两个收尾事件。出自 ai/types.ts:769–785。

The contract is written above the type:

这段约定写在类型定义的 above：

## C O R E R U L E

## 核心规则

“Successful streams emit start before partial updates and terminate with done. A stream may terminate directly with error when request setup fails before generation starts; after start, failures also terminate with . Direct calls throw synchronously when request auth is missing. Updates and must never appear before start.” ai/types.ts:753

「成功的流会先发出 start，然后才是 partial 更新，并以 done 终止。当请求在生成开始之前就 setup 失败时，流可以直接以 error 终止；在 start 之后，失败同样以 error 终止。直接调用时，如果请求鉴权缺失就同步抛出。各种更新和事件绝不能出现在 start 之前。」ai/types.ts:753

![](images/b67d88ded7077be74f92f6157217a9c60d91fe5937b83f304c1f63419a93259a.jpg)
One opening, any number of blocks, exactly one terminal event. The second row is the path the CORE RULE allows: an error with no start. Schematic, from ai/types.ts:753–785; every transition was observed in research/out/streaming-protocol-events.txt.

一个开场事件，数量不限的块，恰好一个终止事件。第二行就是核心规则所允许的路径：没有 start 直接来一个 error。图示取自 ai/types.ts:753–785；每一次状态转移都在 research/out/streaming-protocol-events.txt 中被观测到。

Four rules come with the grammar ai/types.ts:762.

这套语法还带来四条规则（ai/types.ts:762）。

partial is live, not a snapshot. It is “the shared live response-so-far helper, not an event-time snapshot”. The Anthropic adapter pushes the same output object with every event ai/api/anthropic-messages.ts:658. Copy it if you need the state at one event.

partial 是活的，不是快照。它是「共享的、实时反映迄今为止响应的辅助对象，而不是某一时刻的快照」。Anthropic 适配器在每个事件里推的都是同一个输出对象（ai/api/anthropic-messages.ts:658）。如果你需要某个事件时刻的状态，就复制一份。

Text and thinking grow only by deltas. Their blocks “are empty when their *_start event is emitted and grow only through their corresponding *_delta events until the authoritative *_end”. Redacted thinking is the exception: it “may be complete at start and emit no deltas”.

文本和思考只靠增量增长。它们的块「在发出各自的 *_start 事件时是空的，只通过对应的 *_delta 事件增长，直到权威的 *_end」。被涂黑的思考是例外：它「可能在 start 时就已完整，并且不发出任何增量」。

Tool-call arguments are always an object. toolcall_delta.delta is a raw JSON fragment. Adapters keep the concatenated string and re-parse it on each delta with parseStreamingJson, which tries JSON.parse with repair, then partial-json, then partial-json on the repaired string, and returns {} instead of throwing ai/utils/json-parse.ts:104.

工具调用的参数永远是一个对象。toolcall_delta.delta 是 JSON 的原始片段。适配器把拼接起来的字符串保存下来，并在每个增量上用 parseStreamingJson 重新解析它；该函数先尝试带修复的 JSON.parse，再尝试 partial-json，然后在修复后的字符串上再试 partial-json，失败时返回 `{}` 而不是抛异常（ai/utils/json-parse.ts:104）。

Errors after the return are events, not exceptions. “Error termination must produce an AssistantMessage with stop Reason “error” or “aborted” and error Message, emitted via the stream protocol” ai/types.ts:371.

返回之后的错误是事件，不是异常。「错误终止必须产生一条 AssistantMessage，其 stop Reason 为 "error" 或 "aborted"，并带有 error Message，通过流式协议发出」（ai/types.ts:371）。

## A real stream

## 一段真实的流

The capture kit scripts the faux provider (see auth, cost, retries and the catalog (p. 41)) with one thinking block, one text block and one tool call, and prints every event it receives through models.stream(). Token size is fixed at 4 tokens, so each delta carries 16 characters and the run is deterministic research/capture/streaming-protocol-events.mjs.

采集工具套件给 faux 供应商编排了脚本（参见「鉴权、成本、重试与目录」，第 41 页），内容是一个思考块、一个文本块和一次工具调用，并打印它通过 models.stream() 收到的每个事件。token 大小固定为 4 个 token，因此每个增量携带 16 个字符，整个运行是确定性的（research/capture/streaming-protocol-events.mjs）。

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

把这段成功运行当成图 2.3（第 31 页）里的语法走一遍：一个 start、索引 0、1、2 上的三个块、一个 done。那次工具调用的 20 个字符参数分两片到达，只有 toolcall_end 带着解析好的对象。同样形状的事件裹在 message_update 事件里到达智能体循环；单轮捕获从另一侧展示了它（research/out/one-turn.txt §events）。

The next two runs end before start. An empty response queue and an unconfigured provider both produce a single error. The abort run shows two things. Deltas already queued when the signal fires are still delivered: the consumer aborted on event 3, the first delta, and received three more. The final message keeps the text streamed so far, and stop Reason is aborted, not error.

接下来两次运行都在 start 之前就结束了。空的响应队列和未配置的供应商都只产生一个 error。abort 那次运行说明了两件事。信号触发时已经排队的增量仍会送达：消费方在第 3 个事件（也就是第一个增量）上中止，却还收到了三个。最终消息保留了到目前为止已流式输出的文本，stop Reason 是 aborted，不是 error。

## F O O T G U N

## 脚注

The synchronous throw in the CORE RULE applies only when you call an adapter’s stream Simple() directly; the Anthropic adapter calls assertRequestAuth before it creates a stream ai/api/anthropic-messages.ts:933. Through Models, the same missing key is an error event, as the unconfigured run shows, because Models builds the stream first and resolves auth behind it. Code that handles both paths needs a try around the call and an error branch in the loop.

核心规则里那个同步抛出，只在你直接调用某个适配器的 stream Simple() 时才适用；Anthropic 适配器在创建流之前会调用 assertRequestAuth（ai/api/anthropic-messages.ts:933）。而通过 Models 时，同样缺失的密钥会变成一个 error 事件，就像 unconfigured 那次运行展示的那样，因为 Models 先把流建好，鉴权解析藏在它后面。同时处理两条路径的代码，需要在调用外包一层 try，并在循环里加一个错误分支。

## How an adapter builds the message

## 适配器如何构建消息

The adapters share one six-step pattern, and the Anthropic adapter shows it in full ai/api/anthropic-messages.ts:571.

所有适配器共用一个六步模式，Anthropic 适配器完整展示了它（ai/api/anthropic-messages.ts:571）。

1. Create output with empty content, zero usage and stop Reason: "pending" ai/api/anthropic-messages.ts:582.

1. 创建 output，content 为空、usage 全零、stop Reason 为 "pending"（ai/api/anthropic-messages.ts:582）。

2. Send the request through retryProviderRequest, call onResponse with the status and headers, then push start ai/api/anthropic-messages.ts:649.

2. 通过 retryProviderRequest 发出请求，用状态码和 headers 调用 onResponse，然后 push start（ai/api/anthropic-messages.ts:649）。

3. For each vendor block, push a block carrying scratch fields (index, partial Json) and emit *_start. Mutate it and emit *_delta. At the vendor’s block stop, delete the scratch fields and emit *_end.

3. 对每个厂商块，push 一个带临时字段（index、partial Json）的块，并发出 *_start。修改它并发出 *_delta。到了厂商块的结束处，删掉那些临时字段并发出 *_end。

4. Update usage whenever the vendor reports it, and call calculate Cost after each update ai/api/anthropicmessages.ts:688.

4. 厂商每次上报 usage 就更新它，并在每次更新后调用 calculate Cost（ai/api/anthropic-messages.ts:688）。

5. At the end, throw if the signal was aborted, if stop Reason is still pending (“Anthropic stream ended without a stop reason”), or if the vendor mapped the stop to error or aborted. Otherwise push done ai/api/anthropic-messages.ts:861.

5. 结束时，如果信号已被中止、如果 stop Reason 仍是 pending（「Anthropic stream ended without a stop reason」），或者如果厂商把停止原因映射成了 error 或 aborted，就抛异常。否则 push done（ai/api/anthropic-messages.ts:861）。

6. In catch, strip the scratch fields, set stop Reason to aborted when the signal fired and error otherwise, set error Message, and push error ai/api/anthropic-messages.ts:887.

6. 在 catch 里，剥掉那些临时字段，信号触发时把 stop Reason 设为 aborted、否则设为 error，设置 error Message，然后 push error（ai/api/anthropic-messages.ts:887）。

Because step 6 runs after any partial output, an errored or aborted message keeps its partial content and usage. wire APIs and cross-provider hand-of (p. 36) shows why such a message never reaches a model again.

因为第 6 步发生在任何部分输出之后，出错或被中止的消息仍会保留它的部分内容和 usage。「通信API 与跨供应商转交」（第 36 页）会说明为什么这样的消息再也不会进入模型。

For storage and replay, assistant-message-frame.ts defines AssistantMessageFrame: the same events without partial, with start carrying a cloned message, and one extra frame, toolcall_checkpoint { json }. Some adapters put initial arguments in toolcall_start and then stream the JSON again from empty; the encoder holds those deltas back and emits one checkpoint when they catch up with the snapshot ai/utils/assistant-message-frame.ts:236.

为了存储和回放，assistant-message-frame.ts 定义了 AssistantMessageFrame：同样的事件但没有 partial，其中 start 携带一条克隆的消息，另外多出一种帧 toolcall_checkpoint { json }。有些适配器会把初始参数放进 toolcall_start，然后从空开始再把 JSON 流一遍；编码器会把那些增量压住，等到它们追平快照时发出一个 checkpoint（ai/utils/assistant-message-frame.ts:236）。

AssistantMessageFrameEncoder rejects out-of-order input, for example “Assistant message done event appears before start” ai/utils/assistant-message-frame.ts:153. reduceAssistantMessageFrames rebuilds the message ai/utils/assistantmessage-frame.ts:372. Terminal settlement “is intentionally excluded and must be persisted separately”.

AssistantMessageFrameEncoder 会拒绝乱序输入，例如「Assistant message done event appears before start」（ai/utils/assistant-message-frame.ts:153）。reduceAssistantMessageFrames 重建消息（ai/utils/assistant-message-frame.ts:372）。终止结算「被有意排除，必须单独持久化」。

## Request dispatch

## 请求分发

Models.stream() returns its stream synchronously and does the rest behind it ai/models.ts:876.

Models.stream() 同步返回它的流，其余工作都藏在后面做（ai/models.ts:876）。

![](images/596640f73bcf1817bde1657db33b594c679a76a52d9b33fd16a4a9ff3c366ab3.jpg)

The caller holds a stream before auth is resolved. Steps 1–2 happen inside Models; any throw in step 2, such as “Provider is not configured”, becomes a single error event. From ai/models.ts:876–890 (stream), :842–874 (apply Auth) and ai/api/lazy.ts (lazy Stream, forward Stream).

调用方在鉴权解析完成之前就拿到了流。第 1–2 步发生在 Models 内部；第 2 步里的任何抛出，比如「Provider is not configured」，都会变成单个 error 事件。出自 ai/models.ts:876–890（stream）、:842–874（apply Auth）和 ai/api/lazy.ts（lazyStream、forwardStream）。

apply Auth builds the provider request ai/models.ts:842. It calls get Auth(model) with the request’s api Key, env and signal, throws ModelsError("auth", "Provider is not configured: <id>") when nothing resolves, and then assembles four things.

applyAuth 构建供应商请求（ai/models.ts:842）。它带着请求的 apiKey、env 和 signal 调用 getAuth(model)，在什么都解析不出来时抛出 ModelsError("auth", "Provider is not configured: <id>")，然后组装四样东西。

api Key — options.api Key ?? auth.api Key. An explicit key wins per request.

apiKey —— options.apiKey ?? auth.apiKey。显式给出的密钥按请求优先。

headers — merged case-insensitively in a fixed order, later sources overriding earlier ones: provider auth headers → model.headers (inside get Auth) → options.headers → options.transform Headers(), a hook that only Models accepts and strips before dispatch ai/models.ts:751 ai/models.ts:866.

headers —— 按固定顺序以大小写不敏感的方式合并，后面的来源覆盖前面的：供应商鉴权 headers → model.headers（在 getAuth 内部）→ options.headers → options.transformHeaders()，后者是一个只有 Models 才接受的钩子，在分发前会被剥掉（ai/models.ts:751、ai/models.ts:866）。

env — the resolved credential’s provider-scoped values, overlaid by options.env.

env —— 已解析凭据中限定于该供应商范围的取值，再由 options.env 覆盖。

base Url — auth.base Url, when set, replaces model.base Url for this request. GitHub Copilot’s OAuth toAuth derives it from the proxy-ep field of the Copilot token ai/auth/oauth/github-copilot.ts:65.

baseUrl —— auth.baseUrl 若已设置，就在这个请求里替换 model.baseUrl。GitHub Copilot 的 OAuth toAuth 从 Copilot token 的 proxy-ep 字段推导它（ai/auth/oauth/github-copilot.ts:65）。

The capture kit sends one request through a spy provider to watch the merge research/capture/streaming-protocol-events.mjs:

采集工具套件通过一个间谍供应商发出一个请求，以观察这次合并（research/capture/streaming-protocol-events.mjs）：

```javascript auth.headers {"X-Auth":"auth","X-Model":"auth","X-Req":"auth","X-Drop":"auth"}
model.headers {"x-model":"model","X-Req":"model"}
options.headers {"x-req":"request","x-drop":null}
transform Headers received {"X-Auth":"auth","x-model":"model","x-req":"request","x-drop":null}
provider.stream headers={"X-Auth":"auth","x-model":"model","x-req":"request","x-drop":null,"X-
Last":"transform"} api Key="k-auth"
```

Three details are visible. A later source replaces an earlier header whatever its case, and the later spelling wins: X-Model arrives as x-model. A null value survives the merge; it is the adapter that drops it, because “A null value suppresses a provider/API default header with the same name” ai/types.ts:166. Provider.headers takes no part: Models never reads it ai/models.ts:842.

可以看到三个细节。后面的来源会替换前面的同名 header，不管大小写如何，而且后面的拼写获胜：X-Model 到手时变成了 x-model。null 值能在合并中存活下来；是适配器把它丢掉的，因为「null 值会抑制同名的供应商/API 默认 header」（ai/types.ts:166）。Provider.headers 不参与其中：Models 从不读它（ai/models.ts:842）。

stream Simple adds one more layer. Adapters turn its provider-neutral options into their own with buildBaseOptions ai/api/simple-options.ts:36. It clamps max Tokens to context Window − estimated context tokens − 4,096, never below 1 ai/api/simple-options.ts:18. It merges sampling parameters as model.sampling Params, then samplingParamsByThinkingLevel[level] for the clamped level, then the request’s own, each key overriding the last ai/api/simple-options.ts:24. Only the OpenAI-compatible adapters send them ai/types.ts:202. The estimate is the one auth, cost, retries and the catalog (p. 41) describes.

streamSimple 又加了一层。适配器用 buildBaseOptions 把它与供应商无关的选项转换成自己的选项（ai/api/simple-options.ts:36）。它把 maxTokens 夹到「contextWindow − 预估上下文 token − 4,096」，且不低于 1（ai/api/simple-options.ts:18）。它按 model.samplingParams、然后是夹后等级对应的 samplingParamsByThinkingLevel[level]、再是请求自身的顺序合并采样参数，每个键覆盖上一个（ai/api/simple-options.ts:24）。只有 OpenAI 兼容的适配器会发送它们（ai/types.ts:202）。那个预估值就是「鉴权、成本、重试与目录」（第 41 页）里描述的方法。

W H A T T H I S M E A N S F O R Y O U

这对你意味着什么

Handle error as a normal terminal event; check stop Reason on the result, not a try.

把 error 当作普通的终止事件处理；要检查 stop Reason 就查结果对象，而不是靠 try。

Clone partial if you keep it; the next event mutates it.

如果要保留 partial，就先克隆一份；下一个事件会修改它。

Render tool-call progress from partial.content[i].arguments, not by concatenating delta.

工具调用的进度要从 partial.content[i].arguments 渲染，而不是拼接 delta。

Put per-request headers in options.headers; use null to remove a default.

按请求的 header 放进 options.headers；用 null 移除某个默认值。

Sources: ai/types.ts (StreamOptions :189, contract :362–377, event protocol :753–785); ai/utils/event-stream.ts (EventStream, AssistantMessageEventStream); ai/utils/json-parse.ts:104 (parseStreamingJson); ai/utils/assistant-messageframe.ts (AssistantMessageFrame, AssistantMessageFrameEncoder, reduceAssistantMessageFrames); ai/api/anthropicmessages.ts (stream :571–901, stream Simple :928, create Client); ai/api/lazy.ts (lazy Stream, lazy Api). ai/models.ts (merge Headers :373, get Auth :742, apply Auth :842, stream :876); ai/api/simple-options.ts (clampMaxTokensToContext, resolveSamplingParams, buildBaseOptions); ai/auth/oauth/github-copilot.ts; research/capture/streaming-protocolevents.mjs; research/out/streaming-protocol-events.txt; research/out/one-turn.txt §events

来源：ai/types.ts（StreamOptions :189、约定 :362–377、事件协议 :753–785）；ai/utils/event-stream.ts（EventStream、AssistantMessageEventStream）；ai/utils/json-parse.ts:104（parseStreamingJson）；ai/utils/assistant-message-frame.ts（AssistantMessageFrame、AssistantMessageFrameEncoder、reduceAssistantMessageFrames）；ai/api/anthropic-messages.ts（stream :571–901、streamSimple :928、createClient）；ai/api/lazy.ts（lazyStream、lazyApi）。ai/models.ts（mergeHeaders :373、getAuth :742、applyAuth :842、stream :876）；ai/api/simple-options.ts（clampMaxTokensToContext、resolveSamplingParams、buildBaseOptions）；ai/auth/oauth/github-copilot.ts；research/capture/streaming-protocol-events.mjs；research/out/streaming-protocol-events.txt；research/out/one-turn.txt §events

# 2.3 Wire APIs and cross-provider hand-off

# 2.3 通信API 与跨供应商转交

Ten adapter files translate one transcript into ten vendor protocols. Before any of them sends a byte, one shared function rewrites history so that a conversation started on one model can continue on another.

十个适配器文件把同一份记录翻译成十种厂商协议。在它们发出任何一个字节之前，有一个共享函数会重写历史，好让一段起始于某个模型的对话能在另一个模型上继续。

A session can start on Claude, switch to GPT halfway and finish on Gemini. That works only if every adapter can accept history written by every other. This section lists the ten chat wire APIs and what each does that the others do not, the replay data each keeps in its signatures, and Anthropic’s OAuth mode. It ends with transform Messages, the function that makes the switch safe, run on a real history.

一个会话可以在 Claude 上开始，中途切到 GPT，最后在 Gemini 上结束。这只有在一个前提成立时才做得到：每个适配器都能接受其他所有适配器写下的历史。本节会列出这十个对话通信API，以及各自独有能力之处、各自在签名字段里保留的回放数据，还有 Anthropic 的 OAuth 模式。最后会讲 transformMessages——让切换变得安全的那个函数——并在一份真实历史上运行它。

## Ten chat APIs

## 十种对话 API

KnownApi names ten chat protocols ai/types.ts:17. Each has one implementation file under ai/api/ and a .lazy.ts wrapper; the factory files under ai/providers/ import the wrappers they need research/out/stats.txt §api-files.

KnownApi 列出了十种对话协议（ai/types.ts:17）。每种协议在 ai/api/ 下有一个实现文件和一个 .lazy.ts 包装；ai/providers/ 下的工厂文件按需导入这些包装（research/out/stats.txt §api-files）。

<table><tr><td>API</td><td>文件 · 行数</td><td>被谁导入</td><td>它独有的东西</td></tr><tr><td>anthropic-messages</td><td>anthropic-messages.ts·1,639</td><td>anthropic、kimi-coding、minimax、minimax-cn；另外还有 cloudflare-ai-gateway、fireworks、github-copilot、opencode、opencode-go、openrouter、vercel-ai-gateway</td><td>自带的 SSE 解析器。给系统块、最后一个工具以及最后一条用户或系统消息加 cache_control。自适应或预算式思考。工具 id 被重写为 [a-zA-Z0-9_-]，最多 64 个字符。连续的工具结果作为一条用户消息发出。服务端回退模型。</td></tr><tr><td>openai-completions</td><td>openai-completions.ts·1,734</td><td>27 个工厂，包括 groq、deepseek、cerebras、together、zai、xiaomi、qwen</td><td>根据 provider id 和 baseUrl 推断 detectCompat()，可由 model.compat 逐字段覆盖。十一种思考格式。推理从 reasoning_content、reasoning 或 reasoning_text 读取。工具 id 最多 40 个字符。</td></tr><tr><td>openai-responses</td><td>openai-responses.ts·419, shared·809</td><td>openai、xai、meta；另外还有 cloudflare-ai-gateway、github-copilot、opencode、opencode-go</td><td>store: false。prompt_cache_key 取自 sessionId。请求 reasoning。encrypted_content。工具 id 形如 call_id|item_id。推理模型使用 developer 角色。服务层级定价。</td></tr><tr><td>azure-openai-responses</td><td>azure-openai-responses.ts·249, config·107</td><td>azure</td><td>AZURE_OPENAI_BASE_URL 或 AZURE_OPENAI_RESOURCE_NAME；AZURE_OPENAI_API_VERSION，默认 v1；AZURE_OPENAI_DEPLOYMENT_NAME_MAP 以 model=deployment 成对的形式给出。</td></tr><tr><td>openai-codex-responses</td><td>openai-codex-responses.ts·1,697</td><td>openai-codex</td><td>ChatGPT 订阅后端，地址为 chatgpt.com/backend-api/codex/responses。每个会话一条 WebSocket：5 分钟空闲、55 分钟最长存活时间、用 previous_response_id 续接。SSE 作为回退，在运行时提供 zstdCompressSync 时使用 zstd 压缩的请求体。</td></tr><tr><td>google-generative-ai</td><td>google-generative-ai.ts·471, shared·515</td><td>google；另外还有 opencode</td><td>不支持对话中途的系统消息：总是折叠。thinkingLevel 或 thinkingBudget 由模型决定。思维签名只在同一供应商、同一模型且是有效 base64 时才回放。缺失的工具 id 会自动生成。</td></tr><tr><td>google-vertex</td><td>google-vertex.ts·554, shared·515</td><td>google-vertex</td><td>同上，但使用 Vertex 鉴权。</td></tr></table>

Wire APIs and cross-provider hand-of

通信API 与跨供应商转交

<table><tr><td>bedrock-converse-stream</td><td>bedrock-converse-stream.ts·1,373</td><td>amazon-bedrock</td><td>仅限 Node，通过变量说明符加载。自定义 header 由 Smithy build 中间件添加，因此 SigV4 会覆盖它们；x-amz-*-、authorization 和 host 被跳过。只有具备缓存能力的 Claude 模型才使用 cachePoint，或者设置 AWS_BEDROCK_FORCE_CACHE=1。被涂黑的推理以 base64 存储。</td></tr><tr><td>mistral-conversations</td><td>mistral-conversations.ts·937</td><td>mistral</td><td>工具调用 id 恰好是 9 个字母数字字符。</td></tr><tr><td>pi-messages</td><td>pi-messages.ts·444</td><td>radius；以及任何自定义后端</td><td>Pi 自己的协议：一次 POST 把 { model, context, options } 发到 /messages，用 SSE PiMessagesEvents 应答。</td></tr></table>

One file per protocol, many providers per file. openai-completions alone is imported by 27 of the 42 factories. “Imported by” is the factory files that import the API’s lazy wrapper; a factory that imports several picks one per model through model.api. Line counts from wc -l at the pinned commit. Behaviours from ai/api/anthropic-messages.ts:1291, :1463; openai-completions.ts:273, :1211, :1593; openai-responses.ts:334–379. Also openai-responses-shared.ts:167, :215; azure-openai-config.ts; openai-codex-responses.ts:52, :218, :866–867. Also google-shared.ts:146–159; google-generative-ai.ts:196–200; bedrock-conversestream.ts:462–493, :870–880; mistral-conversations.ts:28.

每个协议一个文件，一个文件可服务多个供应商。仅 openai-completions 就被 42 个工厂中的 27 个导入。「被谁导入」一栏列出的是导入该 API 惰性包装的工厂文件；导入多个 API 的工厂通过 model.api 为每个模型各选一个。行数来自固定 commit 处的 wc -l。行为取自 ai/api/anthropic-messages.ts:1291、:1463；openai-completions.ts:273、:1211、:1593；openai-responses.ts:334–379。另外还有 openai-responses-shared.ts:167、:215；azure-openai-config.ts；openai-codex-responses.ts:52、:218、:866–867。另有 google-shared.ts:146–159；google-generative-ai.ts:196–200；bedrock-converse-stream.ts:462–493、:870–880；mistral-conversations.ts:28。

Three more API families exist outside the chat path. openrouter-images generates images. typesafe-system-one, cloudflare-workers-ai-system-one and lama-cpp-classify are classifier APIs ai/types.ts:31 ai/types.ts:35. They are reached through generate Images and classify, never through stream.

对话路径之外还存在三族 API。openrouter-images 生成图像。typesafe-system-one、cloudflare-workers-ai-system-one 和 lama-cpp-classify 是分类 API（ai/types.ts:31、ai/types.ts:35）。它们通过 generateImages 和 classify 访问，绝不通过 stream。

The OpenAI Completions adapter is the one most providers share, so it carries the most switches. detect Compat recognises z.ai, Together, Moonshot, OpenRouter, Cloudflare, NVIDIA, Ant Ling, Cerebras, DeepSeek and others by provider id or URL fragment ai/api/openai-completions.ts:1593. Each detected value is a default that a field of model.compat replaces ai/api/openai-completions.ts:1710. The eleven thinking formats are openai, openrouter, deepseek, together, baseten, zai, qwen, chat-template, qwen-chat-template, string-thinking and ant-ling ai/types.ts:813. Custom endpoints configure the same fields in models.json; see configuration, models and auth (p. 99).

OpenAI Completions 适配器是大多数供应商共用的那个，因此它带的开关也最多。detectCompat 通过 provider id 或 URL 片段识别 z.ai、Together、Moonshot、OpenRouter、Cloudflare、NVIDIA、Ant Ling、Cerebras、DeepSeek 等（ai/api/openai-completions.ts:1593）。每个识别出来的值都是一个默认值，可以由 model.compat 的某个字段替换（ai/api/openai-completions.ts:1710）。十一种思考格式是 openai、openrouter、deepseek、together、baseten、zai、qwen、chat-template、qwen-chat-template、string-thinking 和 ant-ling（ai/types.ts:813）。自定义端点在 models.json 里配置同样的字段；参见「配置、模型与鉴权」（第 99 页）。

## Replay data in signatures

## 签名里的回放数据

Reasoning models want their own reasoning back on the next turn, often encrypted. Pi keeps it in the signature fields of the content blocks, in a format that belongs to the API that wrote it.

推理模型希望下一轮还能拿回自己的推理内容，通常是加密过的。Pi 把它保存在内容块的 signature 字段里，格式属于写下它的那个 API。

<table><tr><td>API</td><td>thinking Signature 保存什么</td><td>其他签名</td></tr><tr><td>anthropic-messages</td><td>Anthropic 的签名字符串，或 redacted_thinking 块的不透明数据</td><td>—</td></tr><tr><td>openai-responses 及其近亲</td><td>序列化为 JSON 的推理条目，含 encrypted_content</td><td>textSignature：消息 id，或一个 TextSignatureV1 JSON</td></tr><tr><td>openai-completions</td><td>它来自的那个推理字段名（reasoning_content、……），或序列化后的 reasoning_details</td><td>—</td></tr><tr><td>bedrock-converse-stream</td><td>签名，或被涂黑字节的 base64</td><td>—</td></tr><tr><td>google-*</td><td>base64 的思维签名</td><td>文本部分上的 textSignature，工具调用上的 thoughtSignature</td></tr></table>

A signature is only meaningful to the API that wrote it. That is why Fig. 2.5 (p. 38) keeps signatures for the same model and drops them otherwise. From ai/api/anthropic-messages.ts:704–722, openai-responses-shared.ts:265, :692, openai-completions.ts:336, :1339–1347, bedrock-converse-stream.ts:655–691, google-shared.ts:231–266, ai/types.ts:391–427.

一个签名只对写下它的那个 API 才有意义。这就是为什么图 2.5（第 38 页）对同一个模型保留签名、其他情况则丢弃它们。出自 ai/api/anthropic-messages.ts:704–722、openai-responses-shared.ts:265、:692、openai-completions.ts:336、:1339–1347、bedrock-converse-stream.ts:655–691、google-shared.ts:231–266、ai/types.ts:391–427。

History is rewritten for the target model, never for the source. “Same model” means all three of provider, api and model match the target. Steps 0–3 run per message in a first pass; 4–5 run in a second pass that also holds a system message found between a call and its results until the results are out. From ai/api/transform-messages.ts:35–235.

历史是为目标模型重写的，绝不为源模型重写。「同一个模型」意味着 provider、api、model 三者都与目标匹配。第 0–3 步在第一趟里逐条消息执行；第 4–5 步在第二趟里执行，第二趟还会把夹在一次调用与其结果之间的系统消息一直保留到结果发完为止。出自 ai/api/transform-messages.ts:35–235。

## Anthropic OAuth mode

## Anthropic 的 OAuth 模式

A Claude Pro or Max login stores an OAuth token, and the adapter recognises it by the substring sk-ant-oat ai/api/anthropicmessages.ts:978. With such a key it changes five things.

Claude Pro 或 Max 的登录会存下一个 OAuth token，适配器通过子串 sk-ant-oat 识别它（ai/api/anthropic-messages.ts:978）。带着这样的密钥，它会改变五件事。

It sends the token as a Bearer auth Token, with user-agent: claude-cli/2.1.280 and x-app: cli ai/api/anthropicmessages.ts:1014.

它把该 token 作为 Bearer authToken 发出，同时带上 user-agent: claude-cli/2.1.280 和 x-app: cli（ai/api/anthropic-messages.ts:1014）。

It adds the betas claude-code-20250219 and oauth-2025-04-20, unless the caller set anthropic-beta explicitly ai/api/anthropic-messages.ts:1106.

它会加上 beta 标记 claude-code-20250219 和 oauth-2025-04-20，除非调用方显式设置过 anthropic-beta（ai/api/anthropic-messages.ts:1106）。

It sends You are Claude Code, Anthropic's official CLI for Claude. as the first system block, ahead of Pi’s own prompt ai/api/anthropic-messages.ts:1167.

它会把 You are Claude Code, Anthropic's official CLI for Claude. 作为第一个系统块发出，排在 Pi 自己的提示词之前（ai/api/anthropic-messages.ts:1167）。

It renames tools to Claude Code’s casing on the way out: Read, Write, Edit, Bash, Grep, Glob and eleven more ai/api/anthropic-messages.ts:101.

它在发出时把工具重命名为 Claude Code 的大小写风格：Read、Write、Edit、Bash、Grep、Glob 以及另外十一个（ai/api/anthropic-messages.ts:101）。

It maps the names back on the way in, by case-insensitive match against the current tool list ai/api/anthropicmessages.ts:127.

它在收回时按大小写不敏感的方式与当前工具列表匹配，把名字映射回去（ai/api/anthropic-messages.ts:127）。

The source labels this block “Stealth mode: Mimic Claude Code’s tool naming exactly” ai/api/anthropic-messages.ts:95.

源码给这一段标注为「Stealth mode: Mimic Claude Code’s tool naming exactly」（ai/api/anthropic-messages.ts:95）。

#### Cross-provider hand-off: transform Messages

#### 跨供应商转交：transformMessages

Nine of the ten chat adapters pass history through transform Messages(messages, model, normalizeToolCallId?) before converting it ai/api/transform-messages.ts:64. The six call sites cover Anthropic, Bedrock, both Google APIs through google-shared.ts, Mistral, OpenAI Completions, and the three Responses APIs through openai-responses-shared.ts ai/api/openai-responses-shared.ts:179. pi-messages does not call it: it posts the transcript as it is, and the backend owns the conversion ai/api/pi-messages.ts:5.

十个对话适配器中有九个在转换之前，会把历史交给 transformMessages(messages, model, normalizeToolCallId?) 过一遍（ai/api/transform-messages.ts:64）。这六个调用点覆盖 Anthropic、Bedrock、经由 google-shared.ts 的两个 Google API、Mistral、OpenAI Completions，以及经由 openai-responses-shared.ts 的三个 Responses API（ai/api/openai-responses-shared.ts:179）。pi-messages 不调用它：它把记录原样 POST 出去，转换由后端负责（ai/api/pi-messages.ts:5）。

F I G . 2 . 5 W H A T T R A N S F O R M M E S S A G E S D O E S T O H I S T O R Y

图 2.5　transformMessages 对历史做了什么

![](images/f01be39d738f20df6896f3bcc7b5a0a139e0e51ec70c58bb341ee2bb283f2c6b.jpg)

The capture kit runs transform Messages on a five-message history written by openai/gpt-5 through openai-responses, once for the same model and once for a text-only Anthropic model with Anthropic’s id normaliser research/capture/wire-apistransform.mjs.

采集工具套件在一份由 openai/gpt-5 通过 openai-responses 写下的五条消息历史上运行 transformMessages，一次针对同一个模型，一次针对一个只支持文本的 Anthropic 模型并使用 Anthropic 的 id 归一化器（research/capture/wire-apis-transform.mjs）。

```txt
### $input (5 messages, written by openai/gpt-5)
1. user ["Look at this.", "<image>"]
2. assistant(tool Use) [{"thinking":"Need to read two files.", "sig":true,"redacted":false}, {"thinking":"[Reasoning redacted]", "sig":true,"redacted":true}, {"text":"Reading.", "sig":true}, {"tool Call":"call_abc|fc_0123456789"}, {"tool Call":"call_def|fc_9876543210"}
3. tool Result call_abc|fc_0123456789 isError=false ["A"]
4. assistant(aborted) [{"text":"Half an ans","sig":false}]
5. user "Go on."

### $same-model (openai/gpt-5, images supported) → 5 messages
1. user ["Look at this.", "<image>"]
2. assistant(tool Use) [{"thinking":"Need to read two two files.", "sig":true,"redacted":false}, {"thinking":"[Reasoning redacted]", "sig":true,"redacted":true}, {"text":"Reading.", "sig":true}, {"tool Call":"call_abc|fc_0123456789"}, {"tool Call":"call_def|fc_987543210"}
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

两次运行都丢掉了被中止的第 4 条消息，并为 call_def 插入了一条失败结果——它原本没有结果；第二趟会对每个目标都这么做。只有跨模型那次运行动了内容。图片变成了占位文本。可见的思考变成一个普通文本块，被涂黑的块消失，两个签名也都没了。OpenAI Responses 每个 id 中的竖线变成下划线，幸存的那条工具结果被重新映射到新 id 上。

```txt
DOC ≠ CODE
```

文档 ≠ 代码

The README says assistant messages from other providers “have their thinking blocks converted to text with <thinking> tags” packages/ai/README.md:1525. The code emits a plain text block with no tags ai/api/transform-messages.ts:113. The same README section says user and tool-result messages pass “unchanged” and tool calls are “preserved unchanged”; the capture above shows images replaced and ids rewritten. The requiresThinkingAsText compat flag repeats the mismatch: its doc comment promises “<thinking> delimiters” ai/types.ts:808, and the adapter’s own comment reads “plain text (no tags to avoid model mimicking them)” ai/api/openai-completions.ts:1324.

README 说来自其他供应商的助手消息「其思考块会被转换为带 `<thinking>` 标签的文本」（packages/ai/README.md:1525）。而代码发出的是一个不带任何标签的普通文本块（ai/api/transform-messages.ts:113）。README 同一节又说用户消息和工具结果消息「原样通过」，工具调用「保持不变」；上面那段捕获却显示图片被替换、id 被重写。requiresThinkingAsText 这个 compat 标志把同样的错位又重复了一遍：它的文档注释承诺有「`<thinking>` 分隔符」（ai/types.ts:808），而适配器自己的注释却写着「plain text (no tags to avoid model mimicking them)」（ai/api/openai-completions.ts:1324）。

```txt
WHAT THIS MEANS FOR YOU
```

这对你意味着什么

Switch models mid-session freely; history is rewritten per request and the stored session is untouched.

可以在会话中随意切换模型；历史是按请求重写的，存储的会话不受影响。

Expect the new model to see earlier reasoning as ordinary assistant text, and redacted reasoning not at all.

要预期新模型会把之前的推理看作普通的助手文本，而被涂黑的推理完全看不到。

Do not rely on an aborted or failed turn being visible to the next request; it is skipped.

不要指望被中止或失败的轮次对下一个请求可见；它会被跳过。

When you write a custom backend for pi-messages, do the hand-of rewriting yourself.

为 pi-messages 编写自定义后端时，转交的重写要自己做。

Sources: ai/types.ts:17–37 (KnownApi, image and classifier APIs), :391–427, :808, :813. ai/api/transform-messages.ts (transform Messages, downgradeUnsupportedImages). ai/api/anthropic-messages.ts (claudeCodeTools :95–131, create Client :982, getBetaFeatures :1080, build Params :1160–1195, normalizeToolCallId :1290, convert Messages :1463, cache control :1483). ai/api/openai-completions.ts (detect Compat :1593, normalizeToolCallId :1205, requiresThinkingAsText :1323). ai/api/openai-responses.ts; ai/api/openai-responses-shared.ts; ai/api/azure-openai-config.ts; ai/api/openai-codexresponses.ts. ai/api/google-shared.ts; ai/api/google-generative-ai.ts; ai/api/bedrock-converse-stream.ts; ai/api/mistralconversations.ts; ai/api/pi-messages.ts. ai/providers/*.ts (lazy API imports); packages/ai/README.md:1520–1527; research/capture/wire-apis-transform.mjs; research/out/wire-apis-transform.txt; research/out/stats.txt §api-files

来源：ai/types.ts:17–37（KnownApi、图像与分类 API）、:391–427、:808、:813。ai/api/transform-messages.ts（transformMessages、downgradeUnsupportedImages）。ai/api/anthropic-messages.ts（claudeCodeTools :95–131、createClient :982、getBetaFeatures :1080、buildParams :1160–1195、normalizeToolCallId :1290、convertMessages :1463、cache control :1483）。ai/api/openai-completions.ts（detectCompat :1593、normalizeToolCallId :1205、requiresThinkingAsText :1323）。ai/api/openai-responses.ts；ai/api/openai-responses-shared.ts；ai/api/azure-openai-config.ts；ai/api/openai-codex-responses.ts。ai/api/google-shared.ts；ai/api/google-generative-ai.ts；ai/api/bedrock-converse-stream.ts；ai/api/mistral-conversations.ts；ai/api/pi-messages.ts。ai/providers/*.ts（惰性 API 导入）；packages/ai/README.md:1520–1527；research/capture/wire-apis-transform.mjs；research/out/wire-apis-transform.txt；research/out/stats.txt §api-files

## 2.4 Auth, cost, retries and the catalog

## 2.4 鉴权、成本、重试与目录

Every request needs a credential, a price list and a policyforfailure. pi-ai keeps a stored credential in charge ofits provider, prices tokensfrom a generated catalog of1,620 models, and retries only what a classifier calls transient.

每个请求都需要一份凭据、一份价目表和一套失败处置策略。pi-ai 让已存储的凭据掌管它所属的供应商，用一份生成的、含 1,620 个模型的目录给 token 定价，并且只重试分类器判定为暂时性的失败。

The previous three sections followed a request that succeeds. This one covers what surrounds it: how a usage block becomes dollars, where a credential comes from and when it is refreshed, and which failures are retried. It ends with where the model catalog comes from and the faux provider that lets all of it run ofline.

前面三节跟随的是一次成功的请求。本节讲的是它周边的东西：一个 usage 块如何变成美元、凭据从哪来以及何时刷新、哪些失败会被重试。最后会讲模型目录从哪里来，以及让这一切能离线运行的 faux 供应商。

## Cost

## 成本

calculate Cost(model, usage) turns token counts into dollars, writes them into usage.cost and returns that object ai/models.ts:1198. Adapters call it after every usage update, so a stream’s partial carries a running cost.

calculateCost(model, usage) 把 token 计数换算成美元，写进 usage.cost 并返回该对象（ai/models.ts:1198）。适配器在每次 usage 更新后都会调用它，所以一条流的 partial 里带着滚动更新的成本。

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

完整函数，第 1198–1218 行。

Rates are dollars per million tokens ai/types.ts:1058. A tier applies when the request’s whole input — fresh, cache-read and cache-written tokens together — exceeds its threshold, and then it prices every part of the request, output included ai/types.ts:1071. The capture kit priced four usage blocks against the pinned catalog research/capture/auth-cost-retriescost.mjs:

费率是每百万 token 的美元数（ai/types.ts:1058）。当请求的全部输入——新鲜 token、缓存读 token 和缓存写 token 合计——超过某个档位的阈值时，该档位就生效，而它随后会给请求的每一部分定价，输出也包含在内（ai/types.ts:1071）。采集工具套件用固定版本的目录给四个 usage 块定了价（research/capture/auth-cost-retries-cost.mjs）：

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

这些数字里有两课。向 Anthropic 的一小时缓存写入 20,000 个 token 花费的是 0.16 美元而不是 0.10 美元，因为它按输入费率的两倍计价，而不是按缓存写费率计价。而 gpt-5.5 上多一个输入 token 就让 272,001 个 token 越过阈值，账单几乎翻倍，从 0.49 美元涨到 0.97 美元：更高的档位会把整个请求重新定价。

The OpenAI Responses and Codex adapters then scale all four parts by the service tier the response reports: flex × 0.5, priority × 2, and × 2.5 for gpt-5.5 ai/api/openai-responses.ts:391 ai/api/openai-codex-responses.ts:602. The Responses adapter treats fast like priority.

OpenAI Responses 和 Codex 的适配器随后会按响应上报的服务层级缩放这四部分：flex × 0.5、priority × 2，gpt-5.5 则 × 2.5（ai/api/openai-responses.ts:391、ai/api/openai-codex-responses.ts:602）。Responses 适配器把 fast 当作 priority 处理。

## Credentials and their resolution

## 凭据及其解析

Auth has two halves: what is stored, and what each provider knows how to resolve ai/auth/types.ts.

鉴权有两个半边：存了什么，以及每个供应商知道怎么解析它（ai/auth/types.ts）。

Credential — “One type-tagged credential per provider — the shape of today’s auth.json” ai/auth/types.ts:36. Either ApiKeyCredential { type: "api_key", key?, env? } or OAuthCredential { type: "oauth", refresh, access, expires, … }.

Credential ——「每个供应商一个带类型标记的凭据——就是今天 auth.json 的形状」（ai/auth/types.ts:36）。要么是 ApiKeyCredential { type: "api_key", key?, env? }，要么是 OAuthCredential { type: "oauth", refresh, access, expires, … }。

CredentialStore — app-owned storage keyed by provider id, with read, list, modify and delete ai/auth/types.ts:65. modify(providerId, fn) “is the only write path”, serialised per provider and across processes where the backing store supports a lock. The coding agent’s auth.json is one implementation; see configuration, models and auth (p. 99).

CredentialStore —— 由应用自己拥有的存储，以 provider id 为键，提供 read、list、modify 和 delete（ai/auth/types.ts:65）。modify(providerId, fn)「是唯一的写入路径」，在支持锁的底层存储上按供应商、按进程串行化。编码智能体的 auth.json 就是其中一种实现；参见「配置、模型与鉴权」（第 99 页）。

ProviderAuth — { api Key?: ApiKeyAuth, oauth?: OAuthAuth }, at least one present ai/auth/types.ts:247. ApiKeyAuth.resolve() merges the stored key with ambient sources and returns undefined when the provider is unconfigured. OAuthAuth splits refresh (a network call) from toAuth (a pure derivation of request auth from a valid credential).

ProviderAuth —— { apiKey?: ApiKeyAuth, oauth?: OAuthAuth }，两者至少存在一个（ai/auth/types.ts:247）。ApiKeyAuth.resolve() 把存储的密钥与环境中的来源合并，供应商未配置时返回 undefined。OAuthAuth 把 refresh（一次网络调用）和 toAuth（从有效凭据纯函数式地推导出请求鉴权）分开。

ModelAuth — what resolution produces: api Key?, headers?, base Url? ai/auth/types.ts:7. “If a value cannot be expressed as api Key, headers, or base Url, it is provider config, not auth.”

ModelAuth —— 解析的产物：apiKey?、headers?、baseUrl?（ai/auth/types.ts:7）。「如果某个值无法表达成 apiKey、headers 或 baseUrl，它就是供应商配置，而不是鉴权。」

resolveProviderAuth decides which source wins ai/auth/resolve.ts:33. Its header comment states the policy: “A stored credential owns the provider: ambient/env is consulted only when nothing is stored. No silent env fallback after a failed refresh or for a credential type without a matching handler.”

resolveProviderAuth 决定哪个来源获胜（ai/auth/resolve.ts:33）。它的头部注释陈述了策略：「已存储的凭据掌管该供应商：只有在什么都没存时才会去查环境变量/环境。刷新失败之后，或对于没有匹配处理器的凭据类型，都不会静默回退到环境变量。」

![](images/abab912fae2e45e7a4a7c1a31b352493f95db6cf3365f2c3eee293d8df5a1e42.jpg)
Nothing stored is the only path to the environment. A stored credential of the wrong type yields “not configured”, not an environment key. First match wins, top to bottom. From ai/auth/resolve.ts:46–93.

「什么都没存」是通往环境变量的唯一路径。类型不对的已存储凭据得到的是「未配置」，而不是一个环境变量密钥。自上而下，第一个匹配获胜。出自 ai/auth/resolve.ts:46–93。

An OAuth token is refreshed when it expires within five minutes, or within a longer window the caller asks for ai/auth/resolve.ts:169. The refresh runs inside credentials.modify(), re-checks expiry under the lock so that concurrent requests and processes refresh once, and is bounded by a 15-second timeout ai/auth/resolve.ts:119. The caller’s abort signal cancels only the wait for the lock: once a refresh has started, “the provider may already have rotated the refresh token”, and cancelling it “could discard the only valid refresh token” ai/auth/resolve.ts:110. A failed refresh surfaces as ModelsError code oauth, with the stored credential kept for a retry ai/models.ts:301.

当 OAuth token 在五分钟内到期，或在调用方要求的更长窗口内到期时，会被刷新（ai/auth/resolve.ts:169）。刷新在 credentials.modify() 内部执行，在锁下重新检查过期时间，使并发请求和并发进程只刷新一次，并且受 15 秒超时限制（ai/auth/resolve.ts:119）。调用方的中止信号只取消等待锁的那段时间：一旦刷新已经开始，「供应商可能已经轮换过 refresh token」，取消它「可能丢掉唯一有效的 refresh token」（ai/auth/resolve.ts:110）。刷新失败会以 ModelsError 的 oauth 代码呈现，并保留已存储的凭据以便重试（ai/models.ts:301）。

Ambient keys come from one variable per provider ai/env-api-keys.ts:73:

环境中的密钥来自每个供应商一个变量（ai/env-api-keys.ts:73）：

<table><tr><td>供应商</td><td>变量</td></tr><tr><td>anthropic</td><td>ANTHROPIC_OAUTH_TOKEN、ANTHROPIC_API_KEY；ANTHROPIC_AUTH_TOKEN 会被发现，但必须以 Authorization: Bearer 的形式发送</td></tr><tr><td>openai · azure · google · google-vertex</td><td>OPENAI_API_KEY · AZURE_OPENAI_API_KEY · GEMINI_API_KEY · GOOGLE_CLOUD_API_KEY</td></tr><tr><td>github-copilot · xai · groq · cerebras · mistral</td><td>COPILOT_GITHUB_TOKEN · XAI_API_KEY · GROQ_API_KEY · CEREBRAS_API_KEY · MISTRAL_API_KEY</td></tr><tr><td>openrouter · vercel-ai-gateway · deepseek · nvidia</td><td>OPENROUTER_API_KEY · AI_GATEWAY_API_KEY · DEEPSEEK_API_KEY · NVIDIA_API_KEY</td></tr><tr><td>together · baseten · huggingface · fireworks</td><td>TOGETHER_API_KEY · BASETEN_API_KEY · HF_TOKEN · FIREWORKS_API_KEY</td></tr><tr><td>moonshotai, moonshotai-cn · zai · zai-coding-cn</td><td>MOONSHOT_API_KEY · ZAI_API_KEY · ZAI_CODING_CN_API_KEY</td></tr><tr><td>minimax · minimax-cn · kimi-coding · meta</td><td>MINIMAX_API_KEY · MINIMAX_CN_API_KEY · KIMI_API_KEY · META_API_KEY</td></tr><tr><td>opencode, opencode-go · radius · typesafe · ant-ling</td><td>OPENCODE_API_KEY · RADIUS_API_KEY · TYPESAFE_API_KEY · ANT_LING_API_KEY</td></tr><tr><td>cloudflare-workers-ai, cloudflare-ai-gateway</td><td>CLOUDFLARE_API_KEY，另外还有 CLOUDFLARE_ACCOUNT_ID，网关还需要 CLOUDFLARE_GATEWAY_ID</td></tr><tr><td>qwen-token-plan（以及 -individual）· qwen-token-plan-cn</td><td>QWEN_TOKEN_PLAN_API_KEY · QWEN_TOKEN_PLAN_CN_API_KEY</td></tr><tr><td>xiaomi · xiaomi-token-plan-cn/-ams/-sgp</td><td>XIAOMI_API_KEY · XIAOMI_TOKEN_PLAN_CN_API_KEY、_AMS_、_SGP_</td></tr></table>

Forty of the 42 providers have an API-key variable; amazon-bedrock and openai-codex have none. Google Vertex also accepts Application Default Credentials with GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION; Bedrock accepts AWS_PROFILE, an access-key pair, AWS_BEARER_TOKEN_BEDROCK, ECS containe credentials or AWS_WEB_IDENTITY_TOKEN_FILE. From ai/env-api-keys.ts:73–127, :160–190, ai/providers/cloudflare-auth.ts. The full list with the coding agent’s own variables is in environment variables (p. 185).

42 个供应商中有 40 个有 API 密钥变量；amazon-bedrock 和 openai-codex 没有。Google Vertex 还接受配合 GOOGLE_CLOUD_PROJECT 和 GOOGLE_CLOUD_LOCATION 使用的 Application Default Credentials；Bedrock 接受 AWS_PROFILE、一对访问密钥、AWS_BEARER_TOKEN_BEDROCK、ECS 容器凭据或 AWS_WEB_IDENTITY_TOKEN_FILE。出自 ai/env-api-keys.ts:73–127、:160–190、ai/providers/cloudflare-auth.ts。含编码智能体自身变量的完整清单见「环境变量」（第 185 页）。

Nine providers also ofer an OAuth login. The flows load lazily, through a variable import specifier, so bundles do not pull in Node-only callback servers ai/auth/oauth/load.ts.

还有九个供应商提供 OAuth 登录。这些流程是惰性加载的，通过变量 import 说明符引入，因此打包产物不会捎上仅限 Node 的回调服务器（ai/auth/oauth/load.ts）。

<table><tr><td>供应商</td><td>流程</td><td>细节</td></tr><tr><td>anthropic</td><td>PKCE 授权码</td><td>claude.ai/oauth/authorize；回调监听 53692 端口，或粘贴一个码</td></tr><tr><td>openai-codex</td><td>PKCE，或设备码</td><td>auth.openai.com；重定向到 localhost:1455/auth/callback；accountId 从 token 的 chatgpt_account_id claim 中读出</td></tr><tr><td>openai（&quot;Sign in with ChatGPT&quot;）</td><td>PKCE 配动态注册的客户端</td><td>回调在 127.0.0.1:1455</td></tr><tr><td>github-copilot</td><td>设备码，然后换 Copilot token</td><td>toAuth 从 token 的 proxy-ep 取 baseUrl；支持企业域名</td></tr><tr><td>openrouter</td><td>PKCE，然后交换密钥</td><td>存储的密钥永不过期（expires: Number.MAX_SAFE_INTEGER）</td></tr><tr><td>kimi-coding · xai</td><td>设备码</td><td>RFC 8628 设备授权</td></tr><tr><td>meta</td><td>设备码，然后铸造 API 密钥</td><td>铸造出的密钥「大约活一天」；刷新时重新铸造</td></tr><tr><td>radius</td><td>在 127.0.0.1:1456 上用 PKCE，或设备码</td><td>每个网关一个</td></tr></table>

Every OAuth flow ends in the same OAuthCredential, and toAuth turns it into an API key, headers or a base URL. From ai/auth/oauth/*.ts (anthropic :15–20, openai-codex :23–26, :313, openai-chatgpt :16–25, github-copilot :60–85, openrouter :109, meta :7–12, radius :18–19).

每个 OAuth 流程最终都产出同一个 OAuthCredential，而 toAuth 把它变成一把 API 密钥、一组 headers 或一个 base URL。出自 ai/auth/oauth/*.ts（anthropic :15–20、openai-codex :23–26、:313、openai-chatgpt :16–25、github-copilot :60–85、openrouter :109、meta :7–12、radius :18–19）。

## Retries, errors, overflow and abort

## 重试、错误、溢出与中止

Failures are handled in two layers, and pi-ai supplies both.

失败分两层处理，而 pi-ai 两层都提供了。

Provider-level retry is retryProviderRequest ai/utils/provider-retry.ts:105. It reproduces the retry policy of the OpenAI and Anthropic SDKs, but with a sleep that the abort signal interrupts; the SDKs’ own timers ignore it, so adapters call the SDKs with max Retries: 0 and wrap the request ai/api/anthropic-messages.ts:647. It retries when the response header x-shouldretry is true, when there is no status, or on 408, 409, 429 and any status of 500 or above. The delay comes from retryafter-ms, then retry-after (seconds or a date), else min(0.5 × 2^i, 8) seconds less up to 25% jitter. A server-requested delay above maxRetryDelayMs (default 60,000) fails at once with Server requested <n>s retry delay (max: <m>s). so that the outer layer can show it. The attempt count defaults to options.max Retries ?? 0 ai/utils/providerretry.ts:109. Eight adapter files use it; Bedrock, Codex, Mistral and pi-messages do not.

供应商级的重试是 retryProviderRequest（ai/utils/provider-retry.ts:105）。它复现了 OpenAI 和 Anthropic SDK 的重试策略，但睡眠可以被中止信号打断；SDK 自己的定时器不理它，所以适配器以 maxRetries: 0 调用 SDK 并把请求包起来（ai/api/anthropic-messages.ts:647）。当响应头 x-shouldretry 为 true、没有状态码，或者状态码是 408、409、429 以及任何 500 及以上时，它会重试。延迟先取 retryafter-ms，再取 retry-after（秒数或日期），否则取 min(0.5 × 2^i, 8) 秒再减去最多 25% 的抖动。服务器要求的延迟超过 maxRetryDelayMs（默认 60,000）时会立刻失败，并带上 Server requested <n>s retry delay (max: <m>s，消息以便外层能展示它。尝试次数默认是 options.maxRetries ?? 0（ai/utils/provider-retry.ts:109）。有八个适配器文件用到它；Bedrock、Codex、Mistral 和 pi-messages 不用。

Agent-level retry re-runs a whole assistant turn. isRetryableAssistantError looks only at stop Reason: "error" messages, rejects non-retryable patterns first, then accepts retryable ones ai/utils/retry.ts:250. The non-retryable list is quota and billing: insufficient_quota, quota exceeded, billing, OpenCode usage limits, ChatGPT subscription limits ai/utils/retry.ts:7. The retryable list covers overload, rate limits, 5xx codes, network and socket errors, WebSocket closes, premature stream ends such as “stream ended before message_stop”, and the retry-delay message above ai/utils/retry.ts:30. retryAssistantCall waits baseDelayMs × 2^(attempt−1), capped at 60 seconds by default, and never retries an abort ai/utils/retry.ts:126. The coding agent applies the classifier in AgentSession CA/src/core/agentsession.ts:52 and retryAssistantCall in compaction CA/src/core/compaction/compaction.ts:638; see AgentSession: wiring the runtime (p. 61).

智能体级的重试会重跑整个助手轮次。isRetryableAssistantError 只看 stopReason 为 "error" 的消息，先排除不可重试的模式，再接受可重试的模式（ai/utils/retry.ts:250）。不可重试的列表是配额与计费：insufficient_quota、quota exceeded、billing、OpenCode usage limits、ChatGPT subscription limits（ai/utils/retry.ts:7）。可重试的列表涵盖过载、限流、5xx 错误码、网络和套接字错误、WebSocket 关闭、流的过早结束（例如「stream ended before message_stop」），以及上面那条重试延迟消息（ai/utils/retry.ts:30）。retryAssistantCall 等待 baseDelayMs × 2^(attempt−1)，默认上限为 60 秒，并且绝不对中止做重试（ai/utils/retry.ts:126）。编码智能体在 AgentSession 里应用这个分类器（CA/src/core/agent-session.ts:52），在压缩里应用 retryAssistantCall（CA/src/core/compaction/compaction.ts:638）；参见「AgentSession：接好运行时」（第 61 页）。

Context overflow is a third verdict, checked before retry. isContextOverflow(message, context Window?) returns true in three cases ai/utils/overflow.ts:137:

上下文溢出是第三种判定，在重试之前检查。isContextOverflow(message, contextWindow?) 在三种情况下返回 true（ai/utils/overflow.ts:137）：

1. stop Reason: "error" and the message matches one of 25 vendor patterns, such as prompt is too long, exceeds the context window or maximum context length is \d+ tokens, unless it also matches a throttling or rate-limit pattern. Cerebras’ body-less 400/413 counts too.

1. stopReason 为 "error"，且消息匹配 25 种厂商模式之一，例如 prompt is too long、exceeds the context window 或 maximum context length is \d+ tokens——除非它同时匹配限流或速率限制的模式。Cerebras 那种没有响应体的 400/413 也算。

2. Silent overflow: stop Reason: "stop" with input + cache Read above the window, as z.ai does.

2. 静默溢出：stopReason 为 "stop"，且 input + cacheRead 高于窗口上限，z.ai 就是这样。

3. Length overflow: stop Reason: "length", zero output, and input + cache Read at 99% of the window or more, as Xiaomi MiMo does.

3. 长度溢出：stopReason 为 "length"、输出为零，且 input + cacheRead 达到窗口的 99% 或更高，Xiaomi MiMo 就是这样。

The capture kit ran both classifiers on sample messages, with a 200,000-token window:

采集工具套件在样例消息上运行了这两个分类器，窗口设为 200,000 token：

```txt anthropic overflow overflow=true retryable=false bedrock throttling overflow=false retryable=false raw ThrottlingException overflow=true retryable=false overloaded overflow=false retryable=true quota overflow=false retryable=false retry-delay cap overflow=false retryable=true cerebras bodyless overflow=true retryable=false silent overflow (stop) overflow=true retryable=false length, zero output, 99% overflow=true retryable=false
```

## F O O T G U N

## 脚注

A Bedrock throttling error is neither retried nor treated as overflow. The adapter formats it as Throttling error: Too many tokens, please wait… ai/api/bedrock-converse-stream.ts:375. The overflow check excludes that prefix, and no retryable pattern matches “throttling”, so the turn fails. If the exclusion ever sees the raw SDK text ThrottlingException: Too many tokens…, /too many tokens/i fires and the turn is reported as a full context. Both rows above are from research/out/auth-costretries-cost.txt.

Bedrock 的限流错误既不会被重试，也不会被当作溢出。适配器把它格式化成 Throttling error: Too many tokens, please wait…（ai/api/bedrock-converse-stream.ts:375）。溢出检查把这个前缀排除在外，而且没有可重试模式能匹配「throttling」，于是这个轮次失败。如果哪天排除逻辑看到的是 SDK 的原始文本 ThrottlingException: Too many tokens…，那么 /too many tokens/i 就会命中，这个轮次会被报成上下文已满。上面两行均出自 research/out/auth-cost-retries-cost.txt。

Overflow recovery needs a token count, and pi-ai estimates one without a tokenizer ai/utils/estimate.ts. It counts 4 characters per token and 4,800 characters per image. The context estimate is the usage of the last assistant message that succeeded and postdates every earlier message, plus an estimate of the messages after it ai/utils/estimate.ts:97. compaction and branch summaries (p. 92) keeps its own copy of the same method for agent messages

溢出恢复需要一个 token 数，而 pi-ai 不借助分词器也能估出来（ai/utils/estimate.ts）。它按每个 token 4 个字符、每张图片 4,800 个字符来计算。上下文预估值等于最后一条成功的助手消息（它的时间晚于此前所有消息）的 usage，加上对它之后那些消息的估算（ai/utils/estimate.ts:97）。「压缩与分支摘要」（第 92 页）为智能体消息保留了自己的一份同样方法

CA/src/core/compaction/compaction.ts:196；「流式事件协议」（第 30 页）展示了 buildBaseOptions 用它来夹住 maxTokens。

Abort passes the caller’s signal to the SDK or fetch. An aborted message keeps the content and usage streamed so far, as the abort run in the streaming event protocol (p. 30) shows. It is skipped by the context estimate and by transform Messages on replay (wire APIs and cross-provider hand-of (p. 36)).

中止会把调用方的信号传给 SDK 或 fetch。被中止的消息会保留到目前为止已流式输出的内容和 usage，就像「流式事件协议」（第 30 页）里的 abort 运行所展示的。它在上下文预估和回放时的 transformMessages 中都会被跳过（「通信API 与跨供应商转交」，第 36 页）。

## The model catalog

## 模型目录

The built-in catalog is generated, not written.

内置目录是生成的，不是手写的。

![](images/fe5edbe8d0cca833a94b79eb15292701a3aa17dcc7709a1bbd8f6f0552765199.jpg)
1,620 catalog entries: 1,537 chat, 60 image and 23 classifier models. npm run build runs generate-models before tsc; build:offline reuses the data. Counted from src/providers/data/.json at the pinned build; pipeline from packages/ai/package.json (scripts), scripts/generate-models.ts:1292–1771, src/providers/.models.ts and ai/providers/all.ts:136–191.

1,620 个目录条目：1,537 个对话模型、60 个图像模型和 23 个分类模型。npm run build 会在 tsc 之前运行 generate-models；build:offline 复用这份数据。条目数在固定构建下从 src/providers/data/*.json 数出；流水线出自 packages/ai/package.json（scripts）、scripts/generate-models.ts:1292–1771、src/providers/models.ts 和 ai/providers/all.ts:136–191。

Each data file is grouped by API, then keyed "<type>:<id>"; groq.json begins {"openai-completions":{"chat:lama-3.1-8b-instant":{…}}} packages/ai/src/providers/data/groq.json. The type-level ChatModelCatalog maps those keys to literal types ai/model-catalog.ts:30, so getBuiltinModel("anthropic", "<id>") is typed per model ai/providers/all.ts:62. The repository’s agent rules forbid hand edits: “Never modify

每个数据文件先按 API 分组，再以 "<type>:<id>" 为键；groq.json 以 {"openai-completions":{"chat:lama-3.1-8b-instant":{…}}} 开头（packages/ai/src/providers/data/groq.json）。类型层的 ChatModelCatalog 把这些键映射到字面量类型（ai/model-catalog.ts:30），因此 getBuiltinModel("anthropic", "<id>") 的类型是逐模型确定的（ai/providers/all.ts:62）。仓库的智能体规则禁止手工编辑：「绝不要直接修改

packages/ai/src/models.generated.ts，而要更新 packages/ai/scripts/generate-models.ts，然后重新生成」（AGENTS.md）。

Dynamic providers fetch their list at runtime. Radius implements refresh Models ai/providers/radius.ts:49;

动态供应商在运行时拉取自己的列表。Radius 实现了 refreshModels（ai/providers/radius.ts:49）；

create Provider ofers the same through fetch Models, publishing results through a generation check so that a superseded refresh cannot overwrite a newer one ai/models.ts:1091 ai/models.ts:503. Results persist through a ModelsStore ai/modelsstore.ts:22. The coding agent stores them in models-store.json in the agent directory, \~/.pi/agent by default CA/src/core/models-store.ts:52.

createProvider 通过 fetchModels 提供同样的能力，并通过一次代次检查来发布结果，使得被取代的刷新不会覆盖更新的那一次（ai/models.ts:1091、ai/models.ts:503）。结果通过 ModelsStore 持久化（ai/models-store.ts:22）。编码智能体把它们存在智能体目录下的 models-store.json 里，默认是 \~/.pi/agent（CA/src/core/models-store.ts:52）。

## The faux provider

## faux 供应商

faux Provider(options) is a real provider with scripted answers ai/providers/faux.ts:687. Every capture in this book uses it. It registers model faux-1 at http://localhost:0, zero prices, and an API-key auth that always resolves, so it needs no key ai/providers/faux.ts:24.

fauxProvider(options) 是一个带脚本化答案的真实供应商（ai/providers/faux.ts:687）。本书里的每一次采集都用它。它注册模型 faux-1，地址是 http://localhost:0，价格为零，并带一个永远能解析成功的 API 密钥鉴权，因此不需要任何密钥（ai/providers/faux.ts:24）。

Responses — a queue set with set Responses or append Responses. Each step is an AssistantMessage built with fauxAssistantMessage, faux Text, faux Thinking and fauxToolCall, or a factory that receives the context, options, call state and model. An empty queue ends the stream with No more faux responses queued.

Responses —— 一个队列，用 setResponses 或 appendResponses 设置。每一步都是一条用 fauxAssistantMessage、fauxText、fauxThinking 和 fauxToolCall 构造的 AssistantMessage，或者是一个接收 context、options、调用状态和 model 的工厂函数。队列为空时，流会以 No more faux responses queued 结束。

Streaming — each block is split into chunks of token Size tokens, 3–5 by default at 4 characters per token, and emitted as real deltas ai/providers/faux.ts:270. tokensPerSecond paces them; without it they are emitted as fast as the consumer reads.

流式 —— 每个块被切成 tokenSize 个 token 的小片，按每 token 4 个字符算默认是 3–5 个 token，并以真实的增量发出（ai/providers/faux.ts:270）。tokensPerSecond 控制它们的节奏；没有它时，块会以消费者读取的速度发出。

Prompt caching — with a sessionId and cache Retention other than none, usage counts the common prefix with the previous prompt of that session as cache Read and the rest as cache Write ai/providers/faux.ts:230. The one-turn capture shows it: the first call writes 1,468 tokens, the second reads those 1,468 and writes 24 research/out/one-turn.txt §sessionjsonl.

提示词缓存 —— 在有 sessionId 且 cacheRetention 不是 none 的情况下，usage 会把与该会话上一条提示词的公共前缀计为 cacheRead，其余计为 cacheWrite（ai/providers/faux.ts:230）。单轮捕获展示了这一点：第一次调用写入 1,468 个 token，第二次读取这 1,468 个并写入 24 个（research/out/one-turn.txt §session-jsonl）。

Deferred responses — with deferred in the options, the stream ends with stop Reason: "deferred" and a handle; fetch Deferred returns the scripted answer after pending Fetches polls. It is the only built-in provider that implements fetch Deferred and cancel Deferred.

延迟响应 —— 在选项里带 deferred 时，流会以 stopReason: "deferred" 和一个句柄结束；pendingFetches 轮询之后，fetchDeferred 返回脚本化的答案。它是唯一实现了 fetchDeferred 和 cancelDeferred 的内置供应商。

The coding agent’s test suite runs on it through the compat helper registerFauxProvider CA/test/suite/harness.ts:18, and the repository rules require it: “For packages/coding-agent/test/suite/, use test/suite/harness.ts + the faux provider. No real provider APIs, keys, or paid tokens” AGENTS.md.

编码智能体的测试套件通过 compat 辅助函数 registerFauxProvider 跑在它上面（CA/test/suite/harness.ts:18），仓库规则也要求这样做：「对于 packages/coding-agent/test/suite/，使用 test/suite/harness.ts 加上 faux 供应商。不要用真实供应商 API、密钥或付费 token」（AGENTS.md）。

W H A T T H I S M E A N S F O R Y O U

这对你意味着什么

Remove a stored credential before expecting an environment key to take efect.

在指望某个环境变量密钥生效之前，先把已存储的凭据删掉。

Set max Retries explicitly if you want provider-level retries outside the coding agent; pi-ai’s default is none.

如果你想在编码智能体之外做供应商级重试，就显式设置 maxRetries；pi-ai 默认是不重试。

Check isContextOverflow before isRetryableAssistantError: overflow wants compaction, not a retry.

先检查 isContextOverflow，再检查 isRetryableAssistantError：溢出需要的是压缩，不是重试。

Read usage.cost as an estimate from the catalog price, adjusted only for tiers, one-hour cache writes and OpenAI service tiers.

把 usage.cost 当作基于目录价格的估算值来读，它只会被档位、一小时缓存写入和 OpenAI 服务层级调整。

Test against faux Provider; it exercises the same event protocol as a vendor.

对着 fauxProvider 做测试；它走的是和真实厂商一样的事件协议。

Sources: ai/models.ts (calculate Cost :1198, get Auth :742, refresh :551, publishProviderModels :503, create Provider :1039). ai/types.ts:1058–1073. ai/api/openai-responses.ts:391–419; ai/api/openai-codex-responses.ts:602–630. ai/auth/types.ts; ai/auth/resolve.ts; ai/auth/helpers.ts (envApiKeyAuth); ai/auth/oauth/*.ts. ai/env-api-keys.ts; ai/providers/cloudflare-auth.ts. ai/utils/provider-retry.ts; ai/utils/retry.ts; ai/utils/overflow.ts; ai/utils/estimate.ts; ai/api/bedrock-converse-stream.ts:375–410. scripts/generate-models.ts; ai/model-catalog.ts; ai/models.generated.ts; ai/providers/all.ts; ai/models-store.ts; CA/src/core/models-store.ts. ai/providers/faux.ts; CA/test/suite/harness.ts; AGENTS.md. research/capture/auth-cost-retries-cost.mjs; research/out/auth-cost-retriescost.txt; research/out/one-turn.txt

来源：ai/models.ts（calculateCost :1198、getAuth :742、refresh :551、publishProviderModels :503、createProvider :1039）。ai/types.ts:1058–1073。ai/api/openai-responses.ts:391–419；ai/api/openai-codex-responses.ts:602–630。ai/auth/types.ts；ai/auth/resolve.ts；ai/auth/helpers.ts（envApiKeyAuth）；ai/auth/oauth/*.ts。ai/env-api-keys.ts；ai/providers/cloudflare-auth.ts。ai/utils/provider-retry.ts；ai/utils/retry.ts；ai/utils/overflow.ts；ai/utils/estimate.ts；ai/api/bedrock-converse-stream.ts:375–410。scripts/generate-models.ts；ai/model-catalog.ts；ai/models.generated.ts；ai/providers/all.ts；ai/models-store.ts；CA/src/core/models-store.ts。ai/providers/faux.ts；CA/test/suite/harness.ts；AGENTS.md。research/capture/auth-cost-retries-cost.mjs；research/out/auth-cost-retries-cost.txt；research/out/one-turn.txt

![](images/db1675e7b25e62706124c97222520d2e953aeffeac0035daf172db669fbe09ac.jpg)