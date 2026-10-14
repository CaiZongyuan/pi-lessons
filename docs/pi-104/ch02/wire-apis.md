---
title: "传输 API 与跨提供商交接"
description: "Pi 1.0.4 · 2.3 · 原书第 36–40 页"
---

<div class="section-kicker">2.3 / THE PROVIDER LAYER</div>

# 传输 API 与跨提供商交接

---

十个适配器文件将同一份对话记录翻译成十种厂商协议。在其中任何一个发送一个字节之前，一个共享函数会先重写历史，使始于一个模型的对话能够在另一个模型上继续。



一个会话可以从 Claude 开始，中途切换到 GPT，最后在 Gemini 上结束。只有每个适配器都能接受其他适配器写出的历史记录，这才可能实现。本节列出十种聊天传输 API 及其各自独有的行为、每种 API 在签名中保留的重放数据，以及 Anthropic 的 OAuth 模式。最后介绍让切换变得安全的函数 transformMessages，并在一段真实历史记录上运行它。

## 十种聊天 API



KnownApi 列出了十种聊天协议（ai/types.ts:17）。每种协议在 ai/api/ 下都有一个实现文件和一个 .lazy.ts 包装器；ai/providers/ 下的工厂文件导入各自需要的包装器（research/out/stats.txt §api-files）。

|<strong>API</strong>|<strong>文件 · 行数</strong>|<strong>导入它的提供商</strong>|<strong>特有行为</strong>|
|---|---|---|---|
|anthropic-messages<br>|anthropic-messages.ts · 1,639|anthropic、kimi-coding、minimax、minimax-cn；以及 cloudflare-ai-gateway、fireworks、github-copilot、opencode、opencode-go、openrouter、vercel-ai-gateway|自有 SSE 解析器。在系统内容块、最后一个工具，以及最后一条用户或系统消息上设置 cache_control。自适应或预算式思考。工具 id 重写为 [a-zA-Z0-9_-]，最多 64 个字符。连续的工具结果作为一条用户消息发送。服务端备用模型。|
|openai-completions|openai-completions.ts · 1,734|27 个工厂，包括 groq、deepseek、cerebras、together、zai、xiaomi、qwen|detectCompat() 根据提供商 id 和 baseUrl 检测，model.compat 可逐字段覆盖。十一种 thinkingFormats。从 reasoning_content、reasoning 或 reasoning_text 读取推理内容。工具 id 最多 40 个字符。|
|openai-responses|openai-responses.ts · 419，共享部分 · 809|openai、xai、meta；以及 cloudflare-ai-gateway、github-copilot、opencode、opencode-go|store: false。prompt_cache_key 来自 sessionId。请求 reasoning.encrypted_content。工具 id 为 call_id\|item_id。推理模型使用 developer 角色。按服务层级计价。|
|azure-openai-responses|azure-openai-responses.ts · 249，配置部分 · 107|azure|AZURE_OPENAI_BASE_URL 或 AZURE_OPENAI_RESOURCE_NAME；AZURE_OPENAI_API_VERSION，默认 v1；AZURE_OPENAI_DEPLOYMENT_NAME_MAP 使用 model=deployment 键值对。|
|openai-codex-responses|openai-codex-responses.ts · 1,697|openai-codex|ChatGPT 订阅后端位于 chatgpt.com/backend-api/codex/responses。每个会话一条 WebSocket：空闲 5 分钟，最长存续 55 分钟，通过 previous_response_id 续接。以 SSE 为后备；运行时支持 zstdCompressSync 时，使用 zstd 压缩请求体。|
|google-generative-ai|google-generative-ai.ts · 471，共享部分 · 515|google；以及 opencode|不支持对话中途的系统消息：始终折叠。按模型使用 thinkingLevel 或 thinkingBudget。思考签名只对相同提供商、相同模型重放，且必须是有效 base64。缺失的工具 id 会自动生成。|
|google-vertex|google-vertex.ts · 554，共享部分 · 515|google-vertex|同上，但使用 Vertex 身份验证。|
|bedrock-converse-stream|bedrock-converse-stream.ts · 1,373|amazon-bedrock|仅限 Node，通过变量形式的模块说明符加载。自定义请求头由 Smithy build 中间件添加，使 SigV4 覆盖这些请求头；跳过 x-amz-\*-、authorization 和 host。仅对支持缓存的 Claude 模型，或在 AWS_BEDROCK_FORCE_CACHE=1 时使用 cachePoint。被隐藏的推理以 base64 存储。|
|mistral-conversations|mistral-conversations.ts · 937|mistral|工具调用 id 必须恰好为 9 个字母或数字。|
|pi-messages|pi-messages.ts · 444|radius；任何自定义后端|Pi 自身的协议：向 /messages 发出一次包含 { model, context, options } 的 POST，以 SSE PiMessagesEvents 返回响应。|



每种协议一个文件，每个文件可服务多个提供商。仅 openai-completions 就被 42 个工厂中的 27 个导入。“导入它的提供商”指的是导入该 API 惰性包装器的工厂文件；导入多个包装器的工厂会通过 model.api 为每个模型选择一个。行数来自固定提交版本上的 wc -l。行为依据 ai/api/anthropic-messages.ts:1291、:1463；openai-completions.ts:273、:1211、:1593；openai-responses.ts:334–379。另见 openai-responses-shared.ts:167、:215；azure-openai-config.ts；openai-codex-responses.ts:52、:218、:866–867。另见 google-shared.ts:146–159；google-generative-ai.ts:196–200；bedrock-converse-stream.ts:462–493、:870–880；mistral-conversations.ts:28。



聊天路径之外还有另外三类 API。openrouter-images 用于生成图像。typesafe-system-one、cloudflare-workers-ai-system-one 和 lama-cpp-classify 是分类器 API（ai/types.ts:31、ai/types.ts:35）。它们通过 generateImages 和 classify 调用，从不经过 stream。



<strong>OpenAI Completions 适配器被最多的提供商共用，因此带有最多的开关。</strong>detectCompat 根据提供商 id 或 URL 片段识别 z.ai、Together、Moonshot、OpenRouter、Cloudflare、NVIDIA、Ant Ling、Cerebras、DeepSeek 等（ai/api/openai-completions.ts:1593）。每个检测出的值都是默认值，model.compat 中的对应字段可以替换它（ai/api/openai-completions.ts:1710）。十一种思考格式为 openai、openrouter、deepseek、together、baseten、zai、qwen、chat-template、qwen-chat-template、string-thinking 和 ant-ling（ai/types.ts:813）。自定义端点在 models.json 中配置相同字段；参见“配置、模型与身份验证”（原书第99页）。

## 签名中的重放数据



推理模型希望在下一轮次取回自己的推理内容，这些内容往往是加密的。Pi 将其保存在内容块的签名字段中，格式由写入它的 API 决定。



|<strong>API</strong>|<strong>thinkingSignature 保存的内容</strong>|<strong>其他签名</strong>|
|---|---|---|
|anthropic-messages|Anthropic 的签名字符串，或 redacted_thinking 内容块中的不透明数据|—|
|openai-responses 及其相关 API|序列化为 JSON 的推理条目，包括 encrypted_content|textSignature：消息 id 或 TextSignatureV1 JSON|
|openai-completions|推理内容所来自的字段名（reasoning_content 等），或序列化的 reasoning_details|—|
|bedrock-converse-stream|签名，或被隐藏字节的 base64 编码|—|
|google-\*|base64 思考签名|文本部分上的 textSignature，工具调用上的 thoughtSignature|



签名只对写入它的 API 有意义。因此，图 2.5（原书第38页）对相同模型保留签名，对其他模型则丢弃签名。依据 ai/api/anthropic-messages.ts:704–722、openai-responses-shared.ts:265、:692、openai-completions.ts:336、:1339–1347、bedrock-converse-stream.ts:655–691、google-shared.ts:231–266、ai/types.ts:391–427。




## Anthropic OAuth 模式



Claude Pro 或 Max 登录会存储一个 OAuth 令牌，适配器通过子串 sk-ant-oat 识别它（ai/api/anthropic-messages.ts:978）。使用这种密钥时，适配器会改变五件事。



它将令牌作为 Bearer authToken 发送，同时设置 user-agent: claude-cli/2.1.280 和 x-app: cli（ai/api/anthropic-messages.ts:1014）。



它添加 beta 标志 claude-code-20250219 和 oauth-2025-04-20，除非调用方显式设置了 anthropic-beta（ai/api/anthropic-messages.ts:1106）。



它将 You are Claude Code, Anthropic's official CLI for Claude. 作为第一个系统内容块发送，放在 Pi 自己的提示词之前（ai/api/anthropic-messages.ts:1167）。



发送时，它把工具名改成 Claude Code 的大小写形式：Read、Write、Edit、Bash、Grep、Glob，以及另外十一个名字（ai/api/anthropic-messages.ts:101）。



接收时，它通过与当前工具列表进行不区分大小写的匹配，把名称映射回来（ai/api/anthropic-messages.ts:127）。



源码把这一块标为“隐身模式：完全模仿 Claude Code 的工具命名”（ai/api/anthropic-messages.ts:95）。

## 跨提供商交接：transformMessages



十个聊天适配器中，有九个在转换历史记录之前，先将其传入 transformMessages(messages, model, normalizeToolCallId?)（ai/api/transform-messages.ts:64）。六个调用点覆盖 Anthropic、Bedrock、通过 google-shared.ts 接入的两种 Google API、Mistral、OpenAI Completions，以及通过 openai-responses-shared.ts 接入的三种 Responses API（ai/api/openai-responses-shared.ts:179）。pi-messages 不调用它：它原样 POST 对话记录，转换由后端负责（ai/api/pi-messages.ts:5）。



<BookFigure id="2.5" />

> 历史记录始终为目标模型重写，而不是为源模型重写。“相同模型”意味着 provider、api、model 这三个字段都与目标一致。步骤 0–3 在第一遍处理中逐条消息运行；步骤 4–5 在第二遍处理中运行。如果第二遍发现在调用与其结果之间夹着一条系统消息，还会暂时保留它，直到输出结果之后再放出。依据 ai/api/transform-messages.ts:35–235。


图 2.5：transformMessages 如何处理历史记录。采集工具对一份五消息历史记录运行 transformMessages。这份记录由 openai/gpt-5 通过 openai-responses 写出；一次以相同模型为目标，另一次以纯文本 Anthropic 模型为目标，并采用 Anthropic 的 id 规范化函数（research/capture/wire-apis-transform.mjs）。





```text
### $input（5 条消息，由 openai/gpt-5 写出）
1. user ["Look at this.", "<image>"]
2. assistant(toolUse) [{"thinking":"Need to read two files.", "sig":true,"redacted":false}, {"thinking":"[Reasoning redacted]", "sig":true,"redacted":true}, {"text":"Reading.", "sig":true}, {"toolCall":"call_abc|fc_0123456789"}, {"toolCall":"call_def|fc_9876543210"}]
3. toolResult call_abc|fc_0123456789 isError=false ["A"]
4. assistant(aborted) [{"text":"Half an ans","sig":false}]
5. user "Go on."

### $same-model（openai/gpt-5，支持图像）→ 5 条消息
1. user ["Look at this.", "<image>"]
2. assistant(toolUse) [{"thinking":"Need to read two files.", "sig":true,"redacted":false}, {"thinking":"[Reasoning redacted]", "sig":true,"redacted":true}, {"text":"Reading.", "sig":true}, {"toolCall":"call_abc|fc_0123456789"}, {"toolCall":"call_def|fc_987543210"}]
3. toolResult call_abc|fc_0123456789 isError=false ["A"]
4. toolResult call_def|fc_9876543210 isError=true ["No result provided"]
5. user "Go on."

### $cross-model（anthropic/claude-x，纯文本，使用 Anthropic id 规范化函数）→ 5 条消息
1. user ["Look at this.", "(image omitted: model does not support images)"]
2. assistant(toolUse) [{"text":"Need to read two files.", "sig":false}, {"text":"Reading.", "sig":false}, {"toolCall":"call_abc_fc_0123456789"}, {"toolCall":"call_def_fc_9876543210"}]
3. toolResult call_abc_fc_0123456789 isError=false ["A"]
4. toolResult call_def_fc_9876543210 isError=true ["No result provided"]
5. user "Go on."
```



两次运行都删除了已中止的第 4 条消息，并为从未得到结果的 call_def 插入一个失败结果；第二遍处理会对所有目标模型执行这一操作。只有跨模型的那次运行修改了内容。图像变成占位文本。可见的思考变成普通文本块，被隐藏的内容块消失，两种签名都被移除。每个 OpenAI Responses id 中的竖线都变成 _，保留下来的工具结果则被重新映射到新 id。



> <strong>文档 ≠ 代码：</strong>
> 
> README 说，来自其他提供商的助手消息“会将思考块转换为带有 `<thinking>` 标签的文本”（packages/ai/README.md:1525）。代码实际输出的是没有标签的普通文本块（ai/api/transform-messages.ts:113）。README 的同一小节还说，用户消息和工具结果消息“保持不变”，工具调用也“原样保留”；但上面的采集结果显示，图像会被替换，id 会被重写。requiresThinkingAsText compat 标志也存在同样的不一致：它的文档注释承诺使用“`<thinking>` 分隔符”（ai/types.ts:808），而适配器自己的注释写的是“纯文本（不加标签，以免模型模仿它们）”（ai/api/openai-completions.ts:1324）。
> 
> 



> <strong>这对你意味着什么：</strong>
> 
> - 可以在会话中途自由切换模型；历史记录会按每次请求重写，已存储的会话不会被修改。
> 
> - 新模型看到的早先推理会是普通助手文本，而被隐藏的推理则完全不可见。
> 
> - 不要依赖下一次请求能看到已中止或失败的轮次；这些轮次会被跳过。
> 
> - 为 pi-messages 编写自定义后端时，请自行完成交接所需的重写。
> 
> 



> 来源：ai/types.ts:17–37（KnownApi、图像和分类器 API）、:391–427、:808、:813。ai/api/transform-messages.ts（transformMessages、downgradeUnsupportedImages）。ai/api/anthropic-messages.ts（claudeCodeTools :95–131、createClient :982、getBetaFeatures :1080、buildParams :1160–1195、normalizeToolCallId :1290、convertMessages :1463、缓存控制 :1483）。ai/api/openai-completions.ts（detectCompat :1593、normalizeToolCallId :1205、requiresThinkingAsText :1323）。ai/api/openai-responses.ts；ai/api/openai-responses-shared.ts；ai/api/azure-openai-config.ts；ai/api/openai-codex-responses.ts。ai/api/google-shared.ts；ai/api/google-generative-ai.ts；ai/api/bedrock-converse-stream.ts；ai/api/mistral-conversations.ts；ai/api/pi-messages.ts。ai/providers/\*.ts（惰性 API 导入）；packages/ai/README.md:1520–1527；research/capture/wire-apis-transform.mjs；research/out/wire-apis-transform.txt；research/out/stats.txt §api-files。
> 
>
