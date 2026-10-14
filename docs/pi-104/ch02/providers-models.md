---
title: "提供商与模型"
description: "Pi 1.0.4 · 2.1 · 原书第 24–29 页"
---

<div class="section-kicker">2.1 / THE PROVIDER LAYER</div>

# 提供商与模型

---

提供商负责一家厂商的模型、身份验证和传输格式；Models 集合只负责路由。pi-ai 之上的所有部分都与这个集合交互，永远不必知道究竟是 42 个提供商中的哪一个作出了响应。



无论背后是哪家厂商，@earendil-works/pi-ai 都会把“一个模型加一段对话”转换成一条事件流。本节介绍它的两个层次、软件包入口，以及后面各部分都会复用的核心类型：消息、内容块、工具、模型和思考级别。最后介绍一个影响 Pi 其余部分的设计选择：系统提示词和工具列表位于对话记录之内，而不是与它并列存放。

## 两个层次：Provider 与 Models



这个软件包有 151 个源文件、23,581 行非空代码，不包括生成的目录包装器中的 420 行（research/out/stats.txt §package-lines）。它的运行时模型有两个层次，都在同一个文件 ai/models.ts 中声明。



<BookFigure id="2.1" />

> 图 2.1：一页看懂 pi-ai。一个集合、多个提供商，每种 API 对应一个传输实现文件。集合解析身份验证并执行路由；提供商负责自己的目录和身份验证；API 模块使用一种厂商协议，并且仅在首次使用时导入。示意图，依据 ai/models.ts（createModels、createProvider）、ai/api/lazy.ts 和 ai/api/\*.lazy.ts。
> 
> 



<strong>Provider 是一个运行时单元</strong>（ai/models.ts:149）。<strong>它包含 id、name、可选的 baseUrl 和 headers、必需的 auth: ProviderAuth、同步的 getModels()，以及两个聊天操作 stream 和 streamSimple。</strong>可选成员包括 getAllModels、refreshModels、filterModels、filterAllModels、fetchDeferred、cancelDeferred、generateImages 和 classify。getModels()“不得抛出异常”；集合会把抛出异常的提供商视为没有模型的提供商（ai/models.ts:429）。



<strong>Models 集合由 `createModels({ credentials?, modelsStore?, authContext? })` 构建</strong>（ai/models.ts:990）。不传参数时，它使用内存凭据存储、内存模型存储和默认身份验证上下文（ai/models.ts:398）。集合在以 id 为键的映射中保存提供商，解析身份验证，规范化上下文，并把每个请求委派给该模型所属的提供商。它的方法分为五类（ai/models.ts:249）：



|<strong>类别</strong>|<strong>方法</strong>|<strong>说明</strong>|
|---|---|---|
|提供商<br>|getProviders、provider<br>|MutableModels 增加 setProvider（按 id 插入或更新）、deleteProvider、clearProviders|
|目录读取|Models、getModel、modelsOfType、modelOfType、getAllModels、refresh|同步读取最后已知的列表；refresh 更新动态提供商<br>|
|可用性与身份验证|checkAuth、getAvailable、getAvailableOfType、getAllAvailable、getAuth、login、logout|参见“身份验证、费用、重试与模型目录”（原书第41页）|
|聊天|stream、complete、streamSimple、completeSimple、streamDeferred、fetchDeferred、cancelDeferred|complete\* 会等待 stream\*().result()|
|一次性操作|generateImages、classify|永不拒绝 Promise；失败时返回错误结果|



24 个方法，只有一条路由规则：模型的 provider 字段决定使用哪个提供商。依据 ai/models.ts:249–365（Models、MutableModels 接口）。



每种 API 的实现都位于 `ai/api/<api-id>.ts`，并导出 stream 和 streamSimple（ai/types.ts:288）。同目录中的 `<api-id>.lazy.ts` 用 `lazyApi(() => import(...))` 包装它，所以厂商 SDK 只会在首次发出请求时加载（ai/api/lazy.ts）。Bedrock 更进一步，通过变量形式的模块说明符导入，防止打包器沿依赖追踪到仅限 Node 的 AWS SDK（ai/api/bedrock-converse-stream.lazy.ts）。



提供商工厂很薄。下面是一份完整示例：



完整的提供商工厂 · `packages/ai/src/providers/groq.ts`

```ts
export function groqProvider(): Provider<"openai-completions"> {
    return createProvider({
        id: "groq",
        name: "Groq",
        baseUrl: "https://api.groq.com/openai/v1",
        auth: { apiKey: envApiKeyAuth("Groq API key", ["GROQ_API_KEY"]) },
        models: Object.values(GROQ_MODELS),
        api: openAICompletionsApi(),
    });
}
```



函数上方的四行 import 已省略。



createProvider 既接受供所有聊天模型共用的单个 api，也接受按 model.api 为键的映射，供混合型提供商使用（ai/models.ts:1024）。GitHub Copilot、OpenCode 和 OpenRouter 使用映射形式：它们的目录混合了 Anthropic、OpenAI Completions 和 OpenAI Responses 模型（ai/providers/github-copilot.ts）。如果某个模型的 api 没有对应条目，不会抛出异常；它的流会以 `Provider <id> has no API implementation for "<api>"` 结束（ai/models.ts:1077）。如果一个提供商既没有 api，也没有 images 或 classifiers，则会在构建时被拒绝（ai/models.ts:1051）。

## 入口点



软件包导出九个子路径（packages/ai/package.json，exports）。只有 ./compat 和图像注册模块被声明为有副作用。



```text
子路径                 内容
.                      核心，无副作用：类型、createModels、createProvider、faux 提供商，以及对话记录、重试、溢出和验证工具
./models               仅模型运行时（ai/models.ts）
./providers/*          每个提供商一个工厂；./providers/all 另外提供 builtinProviders()、builtinModels() 和 getBuiltinModel()
./api/*                API 实现及其 *.lazy 包装器
./utils/*              各个工具模块
./compat               旧的全局 API：stream、complete、UrModel、registerApiProvider、registerFauxProvider……标注为临时接口
./oauth                供扩展使用的 OAuth 类型，仅含类型
./bun-oauth             为独立 Bun 二进制文件静态打包的 OAuth 流程
./bedrock-provider      以静态导入方式提供的 Bedrock 模块，供 Bun 二进制文件使用
```



根入口的导入最轻量。`.` 不加载任何目录或提供商；./providers/all 会加载全部 42 个。依据 packages/ai/package.json 和 ai/index.ts（文件头注释）。



README 的快速入门使用较重的路径：



所有提供商、一个模型、一条流 · packages/ai/README.md

```js
import { builtinModels } from '@earendil-works/pi-ai/providers/all';
// 一个注册了全部内置提供商的 Models 集合
const models = builtinModels();
// 在集合中同步查找
const model = models.getModel('openai', 'gpt-4o-mini')!;
...
const s = models.stream(model, context);
```



节选自 README §Quick Start：Type/Context/Tool 的导入，以及含有一个 get_time 工具的 context 构建过程，都替换成了 ……。gpt-4o-mini 是固定版本 OpenAI 目录中的 44 个条目之一。



导入 @earendil-works/pi-ai 的扩展并不会得到根入口。编码智能体的虚拟模块映射会将这一说明符及旧名称 @mariozechner/pi-ai 解析到 ./compat（CA/src/core/extensions/virtual-modules.ts:26）。为扩展编写的代码看到的是旧版全局 API；面向 npm 软件包编写的代码看到的是 createModels()。参见“扩展、加载与 API”（原书第113页）。

## 消息与内容块



四种内容块类型和四种消息角色承载所有对话（ai/types.ts:397）。

|<strong>内容块</strong>|<strong>字段</strong>|<strong>说明</strong>|
|---|---|---|
|TextContent|type: "text"、text、textSignature?|签名保存提供商消息元数据，例如 OpenAI Responses 的消息 id|
|ThinkingContent<br>|type: "thinking"、thinking、thinkingSignature?、redacted?|签名是不透明的重放数据；当 redacted 为真时，加密载荷位于签名中|
|ImageContent|type: "image"、data（base64）、mimeType|仅用于用户消息和工具结果的内容|
|ToolCall|type: "toolCall"、id、name、arguments: JsonObject、thoughtSignature?、namespace?|thoughtSignature 属于 Google；namespace 属于 OpenAI Responses|



助手内容由文本、思考和工具调用构成；用户内容由文本和图像构成。依据 ai/types.ts:397–427：

- <strong>SystemMessage</strong>（ai/types.ts:524）：role: "system"、content: string \| TextContent[]、sections?: `Record<string, string | null>`、toolsAdded?: Tool[]、toolsRemoved?: ToolReference[]、timestamp。开头的一条是系统提示词；后续的系统消息会修改它。

- <strong>UserMessage </strong>（ai/types.ts:542） // role: "user"，content: string \| (TextContent \| ImageContent)[]，timestamp。

- <strong>AssistantMessage</strong>（ai/types.ts:548）：content，生成这条消息的 api、provider 和 model，usage、stopReason、timestamp；可选字段为 responseModel（当厂商实际使用了不同模型时）、responseId、providerThinkingLevel、thinkingLevel、diagnostics、deferred、errorMessage、rawStopReason 和 endTurn。

- <strong>ToolResultMessage</strong>（ai/types.ts:596）：role: "toolResult"、toolCallId、toolName、content: (TextContent \| ImageContent)[]、isError、timestamp；可选字段为 details、usage 和 nestedCalls。nestedCalls 会保留在会话记录中，且“不会发送给模型”。

- <strong>Usage</strong>（ai/types.ts:429）：input、output、cacheRead、cacheWrite、可选的 cacheWrite1h（仅 Anthropic）和 reasoning（output 的子集）、totalTokens，以及包含相同四个部分外加 total 的 cost，单位为美元。

- <strong>StopReason</strong>（ai/types.ts:452）："pending" \| "stop" \| "length" \| "toolUse" \| "error" \| "aborted" \| "deferred"。pending 只在流尚未关闭时存在。

- <strong>Message </strong>是上述四种角色的联合类型（ai/types.ts:612）。单轮采集记录第 6 行中的真实助手消息包含全部必需字段，以及一个可选字段 thinkingLevel（research/out/one-turn.txt §session-jsonl）。

## 工具、模型与思考级别



Tool 包含 name、description、一个 TypeBox parameters 模式，以及可选的 constrainedSampling 设置（ai/types.ts:717）。该设置可以是 false、{ type: "json_schema", strict: "prefer" \| "require" }，或带有 openai_lark 和 openai_regex 编码的 { type: "grammar", variants }。单轮采集中的所有内置工具都声明为 json_schema，且 strict: "prefer"（research/out/one-turn.txt §session-jsonl，第4行）。



validateToolArguments(tool, toolCall) 会在调用执行前对其进行检查（ai/utils/validation.ts:317）。它复制参数，规范化可选的 null 值，运行 TypeBox Value.Convert 进行强制转换；当模式不是 TypeBox 对象时，应用 JSON-schema 强制转换，然后验证。失败时会抛出 `Validation failed for tool "<name>":`，后面为每个错误附上一行 - path: message，并以缩进 JSON 形式列出接收到的参数。



每个目录条目都共享 BaseModel：id、name、api、provider、baseUrl、input（"text"、"image"）、可选的 inputLimits、cost 和可选的 headers（ai/types.ts:1099）。聊天 Model 增加下列字段（ai/types.ts:1113）。ImageModel（type: "image"、output）和 ClassifierModel（type: "classifier"、contextWindow）也扩展同一个基类。



|<strong>字段</strong>|<strong>类型</strong>|<strong>含义</strong>|
|---|---|---|
|type|"chat"，可选|缺省表示聊天|
|reasoning|boolean|是否适用思考级别|
|thinkingLevelMap|`Partial<Record<level, string \| null>>`|每个 Pi 级别对应的提供商值；null = 不支持|
|promptCache|{ short?, long? }，单位为秒|缓存存续时间未知时不设置|
|contextWindow、maxTokens|number|输入窗口与输出上限|
|cost|{ input, output, cacheRead, cacheWrite, tiers? }|每百万 token 的美元价格；参见“身份验证、费用、重试与模型目录”（原书第41页）|
|samplingParams、samplingParamsByThinkingLevel|记录类型|合并到 OpenAI 兼容请求体中|
|compat|五种 compat 接口之一，由 api 决定|按模型覆盖自动检测结果|



限制、价格和特殊行为都随模型一起传递。适配器从传入的记录读取窗口、上限、成本和 compat 标志。依据 ai/types.ts:1098–1172。



<strong>Pi 有七个思考级别</strong>：先是 off，然后是 ThinkingLevel = minimal、low、medium、high、xhigh、max（ai/types.ts:85）。对于 reasoning: false 的模型，getSupportedThinkingLevels(model) 返回 ["off"]（ai/models.ts:1222）。否则，它返回从 off 到 high 中所有未被映射为 null 的级别；只有映射中明确列出时，才额外返回 xhigh 和 max。clampThinkingLevel 会保留受支持的级别，否则向上查找下一个受支持的级别，再不行则向下查找（ai/models.ts:1233）。如果请求的 xhigh 不受模型支持，而映射中列出了 max，则变成 max；否则变成 high。



使用 token 预算的提供商通过 DEFAULT_THINKING_BUDGETS 转换级别：minimal 为 1,024、low 为 2,048、medium 为 8,192、high 为 16,384 token（ai/api/simple-options.ts:70）。xhigh 和 max 使用 high 的预算（ai/api/simple-options.ts:77）。当思考预算与回答共用输出上限时，至少为回答预留 MIN_ANSWER_TOKENS = 1,024 token（ai/api/simple-options.ts:68）。

## 系统提示词位于对话记录中



调用方传入 Context：systemPrompt?、messages、tools?（ai/types.ts:734）。提供商永远看不到它们。提供商接收的是带品牌标记的 TranscriptContext，只有 normalizeContext() 能生成它（ai/types.ts:748）。normalizeContext 把提示词和工具折叠到开头的一条 SystemMessage 中，其字段为 content: systemPrompt ?? ""、toolsAdded: tools 和 timestamp: 0（ai/utils/transcript.ts:30）。提示词和工具列表都为空时，它不添加任何内容，因此空的对话记录仍然为空（ai/utils/transcript.ts:10）。



后续系统消息以三种方式修改提示词。content 追加指令。sections 替换具名分节，而 null 删除某个分节。toolsAdded 和 toolsRemoved 修改工具集。getCurrentSystemMessage 和 getCurrentTools 逐条重放系统消息，得到当前状态（ai/utils/transcript.ts:58）。



<BookFigure id="2.2" />

> <strong>追加会保留缓存前缀；折叠则会重写它。</strong>只有模型的 compat 声明接受对话中途的系统消息时，resolveTranscript 才会把后续系统消息保留在原处；否则，重放得到的状态会放到最前面，并删除后续所有系统消息。示意图，依据 ai/utils/transcript.ts:108–120 和 ai/utils/text.ts（renderSystemMessageUpdate）。
> 
> 



<strong>对于接受对话中途系统消息的模型，后续系统消息会在其原有位置发送。分节变更会表示为 `Updated system prompt section "<name>":`，后接该值，或者 `Removed system prompt section "<name>"`</strong>（ai/utils/text.ts:28）。对于其他所有模型，collapseSystemMessages 会把重放状态折叠成开头的一条消息（ai/utils/transcript.ts:108）。Google 适配器始终执行折叠（ai/api/google-shared.ts:193）。compat 标志 supportsMidConvoSystemMessages 默认为 false，生成的目录只对“已验证模型”启用它（ai/types.ts:847）。



<strong>这个设计的原因是提示词缓存。修改工具或提示词分节时，会追加一条消息，而不是重写请求的开头，因此采用前缀缓存的提供商可以保留缓存。</strong>编码智能体也因此使用具名分节构建提示词；参见“系统提示词构建”（原书第75页）。



> <strong>这对你意味着什么：</strong>
> 
> - 从 @earendil-works/pi-ai 导入类型和 createModels；在意打包体积时，从 `./providers/<id>` 导入单个工厂。
> 
> - 把 AssistantMessage.provider、api 和 model 视为记录的一部分：“传输 API 与跨提供商交接”（原书第36页）中的重放规则依赖这三个字段。
> 
> - 通过追加系统消息修改提示词和工具，不要编辑第一条消息。
> 
> - 向用户显示思考级别前，先使用 clampThinkingLevel；模型支持的级别可能少于七个。
> 
> 



> 来源：ai/models.ts（Provider :149、Models :249、MutableModels :360、ModelsImpl、createModels :990、createProvider :1039、getSupportedThinkingLevels :1222、clampThinkingLevel :1233）。ai/types.ts（KnownApi :17、ThinkingLevel :85、内容块 :397–427、Usage :429、StopReason :452、消息 :524–612、Tool :717、Context :734、TranscriptContext :748、compat :847、BaseModel/Model :1099–1146）；ai/utils/transcript.ts（normalizeContext、getCurrentSystemMessage、collapseSystemMessages、resolveTranscript）。ai/utils/text.ts（renderSystemMessageUpdate）；ai/utils/validation.ts:317；ai/api/simple-options.ts；ai/api/lazy.ts；ai/api/bedrock-converse-stream.lazy.ts；ai/providers/groq.ts；ai/index.ts；packages/ai/package.json（exports、sideEffects）；packages/ai/README.md §Quick Start；CA/src/core/extensions/virtual-modules.ts；research/out/stats.txt；research/out/one-turn.txt。
> 
>
