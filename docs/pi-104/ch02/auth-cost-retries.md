---
title: "身份验证、费用、重试与模型目录"
description: "Pi 1.0.4 · 2.4 · 原书第 41–47 页"
---

<div class="section-kicker">2.4 / THE PROVIDER LAYER</div>

# 身份验证、费用、重试与模型目录

---

每个请求都需要凭据、价格表和失败处理策略。pi-ai 让已存储的凭据主导其提供商的身份验证，根据一个含 1,620 个模型的生成目录为 token 定价，并且只重试分类器判定为暂时性的问题。



前三节追踪的是成功的请求。本节介绍围绕请求发生的事情：usage 内容块如何换算成美元、凭据来自哪里以及何时刷新、哪些失败会被重试。最后介绍模型目录的来源，以及让这一切能够离线运行的 faux 提供商。

## 成本



calculateCost(model, usage) 把 token 计数转换成美元，写入 usage.cost，并返回该对象（ai/models.ts:1198）。适配器在每次 usage 更新后调用它，因此流中的 partial 带有持续累计的成本。



token 换算为美元 · packages/ai/src/models.ts

```ts
export function calculateCost(model: AnyModel, usage: Usage): Usage["cost"] {
    const inputTokens = usage.input + usage.cacheRead + usage.cacheWrite;
    let rates: ModelCostRates = model.cost;
    let matchedThreshold = -1;
    for (const tier of model.cost.tiers ?? []) {
        if (inputTokens > tier.inputTokensAbove && tier.inputTokensAbove > matchedThreshold) {
            rates = tier;
            matchedThreshold = tier.inputTokensAbove;
        }
    }

    // Anthropic 对 1 小时缓存写入收取基础输入价格的 2 倍。
    const longWrite = usage.cacheWrite1h ?? 0;
    const shortWrite = usage.cacheWrite - longWrite;
    usage.cost.input = (rates.input / 1000000) * usage.input;
    usage.cost.output = (rates.output / 1000000) * usage.output;
    usage.cost.cacheRead = (rates.cacheRead / 1000000) * usage.cacheRead;
    usage.cost.cacheWrite = (rates.cacheWrite * shortWrite + rates.input * 2 * longWrite) / 1000000;
    usage.cost.total = usage.cost.input + usage.cost.output + usage.cost.cacheRead + usage.cost.cacheWrite;
    return usage.cost;
}
```

> 完整函数，第1198–1218行。
> 
> 



费率以每百万 token 的美元金额表示（ai/types.ts:1058）。当请求的全部输入，也就是新输入、缓存读取和缓存写入 token 的总和，超过某个阈值时，就适用相应阶梯；随后，这个阶梯会为请求中的每个部分定价，包括输出（ai/types.ts:1071）。采集工具使用固定版本目录，为四个 usage 内容块计算了价格（research/capture/auth-cost-retries-cost.mjs）：

```sh
anthropic/claudе-opus-5-5 rates={"input":4,"output":20,"cacheRead":0.2,"cacheWrite":5}
usage input=2000 output=1000 cacheRead=100000 cacheWrite=20000
cost input=$0.008000 output=$0.020000 cacheRead=$0.020000 cacheWrite=$0.100000 total=$0.148000
usage ... cacheWrite=20000 cacheWrite1h=20000
cost input=$0.008000 output=$0.020000 cacheRead=$0.020000 cacheWrite=$0.160000 total=$0.208000
openai/gpt-5.5 rates={"input":5,"output":30,"cacheRead":0.5,"cacheWrite":0,"tiers":[{"inputTokensAbove":272000,"input":10,"output":45,"cacheRead":1,"cacheWrite":0}]}
usage input=72000 output=1000 cacheRead=200000 cacheWrite=0
cost input=$0.360000 output=$0.030000 cacheRead=$0.100000 cacheWrite=$0.000000 total=$0.490000
usage input=72001 output=1000 cacheRead=200000 cacheWrite=0
cost input=$0.720010 output=$0.045000 cacheRead=$0.200000 cacheWrite=$0.000000 total=$0.96501
```



这些数字说明了两点。向 Anthropic 的一小时缓存写入 20,000 token，成本是 $0.16，而不是 $0.10，因为它按输入费率的两倍收费，而不是按缓存写入费率收费。另外，gpt-5.5 只多一个输入 token，就会让 272,001 token 跨过阈值，使账单几乎翻倍，从 $0.49 增至 $0.97：更高的阶梯会为整个请求重新定价。



OpenAI Responses 和 Codex 适配器随后根据响应报告的服务层级，对这四个部分同时乘以系数：flex × 0.5，priority × 2，而 gpt-5.5 则为 × 2.5（ai/api/openai-responses.ts:391、ai/api/openai-codex-responses.ts:602）。Responses 适配器把 fast 按 priority 处理。

## 凭据及其解析



身份验证分成两半：存储什么，以及每个提供商知道如何解析什么（ai/auth/types.ts）：

- Credential：“每个提供商有一个带类型标签的凭据，即当前 auth.json 的结构”（ai/auth/types.ts:36）。它可以是 ApiKeyCredential { type: "api_key", key?, env? }，也可以是 OAuthCredential { type: "oauth", refresh, access, expires, … }。

- CredentialStore：由应用拥有、以提供商 id 为键的存储，提供 read、list、modify 和 delete（ai/auth/types.ts:65）。modify(providerId, fn)“是唯一写入路径”，按提供商串行执行；当底层存储支持锁时，也在进程之间串行执行。编码智能体的 auth.json 就是其中一种实现；参见“配置、模型与身份验证”（原书第99页）。

- ProviderAuth：{ apiKey?: ApiKeyAuth, oauth?: OAuthAuth }，至少存在一项（ai/auth/types.ts:247）。ApiKeyAuth.resolve() 将已存储的密钥与环境来源合并；如果提供商未配置，则返回 undefined。OAuthAuth 将 refresh（一次网络调用）与 toAuth（根据有效凭据纯粹推导请求身份验证）分离。

- ModelAuth：解析的结果，包含 apiKey?、headers?、baseUrl?（ai/auth/types.ts:7）。“如果一个值无法表示为 apiKey、headers 或 baseUrl，那么它属于提供商配置，而不是身份验证。”

- resolveProviderAuth 决定哪个来源优先（ai/auth/resolve.ts:33）。它的文件头注释陈述了这一策略：“已存储的凭据主导该提供商：只有在未存储任何凭据时才查询环境来源或环境变量。刷新失败，或凭据类型没有匹配处理程序时，不会悄悄回退到环境变量。”



<BookFigure id="2.6" />

> 没有已存储凭据，是通向环境变量的唯一路径。已存储凭据的类型不正确时，结果是“未配置”，而不是改用环境变量中的密钥。从上到下，第一个匹配项生效。依据 ai/auth/resolve.ts:46–93。
> 
> 



OAuth 令牌将在五分钟内过期，或进入调用方要求的更长刷新窗口时，会被刷新（ai/auth/resolve.ts:169）。刷新在 credentials.modify() 内运行，在锁内重新检查过期时间，使并发请求和进程只刷新一次，并受 15 秒超时限制（ai/auth/resolve.ts:119）。调用方的中止信号只取消等待锁的过程：一旦刷新已经开始，“提供商可能已经轮换了刷新令牌”，此时取消“可能丢弃唯一有效的刷新令牌”（ai/auth/resolve.ts:110）。刷新失败会以代码为 oauth 的 ModelsError 向外呈现，已存储凭据则保留下来供重试（ai/models.ts:301）。



环境密钥来自每个提供商对应的一个变量（ai/env-api-keys.ts:73）：

|<strong>提供商</strong>|<strong>变量</strong>|
|---|---|
|anthropic<br>|ANTHROPIC_OAUTH_TOKEN、ANTHROPIC_API_KEY；也会发现 ANTHROPIC_AUTH_TOKEN，但它必须作为 Authorization: Bearer 发送|
|openai · azure · google · google-vertex|OPENAI_API_KEY · AZURE_OPENAI_API_KEY · GEMINI_API_KEY · GOOGLE_CLOUD_API_KEY|
|github-copilot · xai · groq · cerebras · mistral|COPILOT_GITHUB_TOKEN · XAI_API_KEY · GROQ_API_KEY · CEREBRAS_API_KEY · MISTRAL_API_KEY|
|openrouter · vercel-ai-gateway · deepseek · nvidia|OPENROUTER_API_KEY · AI_GATEWAY_API_KEY · DEEPSEEK_API_KEY · NVIDIA_API_KEY|
|together · baseten · huggingface · fireworks|TOGETHER_API_KEY · BASETEN_API_KEY · HF_TOKEN · FIREWORKS_API_KEY|
|moonshotai、moonshotai-cn · zai · zai-coding-cn|MOONSHOT_API_KEY · ZAI_API_KEY · ZAI_CODING_CN_API_KEY|
|minimax · minimax-cn · kimi-coding · meta|MINIMAX_API_KEY · MINIMAX_CN_API_KEY · KIMI_API_KEY · META_API_KEY|
|opencode、opencode-go · radius · typesafe · ant-ling|OPENCODE_API_KEY · RADIUS_API_KEY · TYPESAFE_API_KEY · ANT_LING_API_KEY|
|cloudflare-workers-ai、cloudflare-ai-gateway|CLOUDFLARE_API_KEY，加上 CLOUDFLARE_ACCOUNT_ID；网关还需要 CLOUDFLARE_GATEWAY_ID|
|qwen-token-plan（以及 -individual）· qwen-token-plan-cn|QWEN_TOKEN_PLAN_API_KEY · QWEN_TOKEN_PLAN_CN_API_KEY|
|xiaomi · xiaomi-token-plan-cn/-ams/-sgp|XIAOMI_API_KEY · XIAOMI_TOKEN_PLAN_CN_API_KEY、_AMS_、*SGP*|



42 个提供商中，有 40 个具有 API 密钥变量；amazon-bedrock 和 openai-codex 没有。Google Vertex 还接受搭配 GOOGLE_CLOUD_PROJECT 和 GOOGLE_CLOUD_LOCATION 的 Application Default Credentials；Bedrock 接受 AWS_PROFILE、访问密钥对、AWS_BEARER_TOKEN_BEDROCK、ECS 容器凭据或 AWS_WEB_IDENTITY_TOKEN_FILE。依据 ai/env-api-keys.ts:73–127、:160–190，以及 ai/providers/cloudflare-auth.ts。包含编码智能体自身变量的完整列表见“环境变量”（原书第185页）。



九个提供商还提供 OAuth 登录。流程通过变量形式的导入说明符惰性加载，因此打包产物不会带入仅限 Node 的回调服务器（ai/auth/oauth/load.ts）。



|<strong>提供商</strong>|<strong>流程</strong>|<strong>细节</strong>|
|---|---|---|
|anthropic|PKCE 授权码|claude.ai/oauth/authorize；在端口 53692 接收回调，或粘贴授权码|
|openai-codex|PKCE，或设备码|auth.openai.com；重定向到 localhost:1455/auth/callback；accountId 从令牌的 chatgpt_account_id 声明读取|
|openai（“使用 ChatGPT 登录”）|使用动态注册客户端的 PKCE|在 127.0.0.1:1455 接收回调|
|github-copilot|设备码，然后获取 Copilot 令牌|toAuth 从令牌的 proxy-ep 获取 baseUrl；支持企业域名|
|openrouter|PKCE，然后交换密钥|已存储的密钥永不过期（expires: Number.MAX_SAFE_INTEGER）|
|kimi-coding · xai|设备码|RFC 8628 设备授权|
|meta|设备码，然后签发 API 密钥|签发的密钥“存续约一天”；刷新时重新签发|
|radius|127.0.0.1:1456 上的 PKCE，或设备码|按网关分别处理|



每个 OAuth 流程最终都得到同一种 OAuthCredential，toAuth 将其转换成 API 密钥、请求头或基础 URL。依据 ai/auth/oauth/\*.ts（anthropic :15–20、openai-codex :23–26、:313、openai-chatgpt :16–25、github-copilot :60–85、openrouter :109、meta :7–12、radius :18–19）。

## 重试、错误、溢出与中止



失败分两层处理，pi-ai 提供这两层机制。



提供商级重试由 retryProviderRequest 实现（ai/utils/provider-retry.ts:105）。它复现了 OpenAI 和 Anthropic SDK 的重试策略，但其休眠可被中止信号打断；SDK 自身的计时器会忽略中止信号，因此适配器以 maxRetries: 0 调用 SDK，再包装请求（ai/api/anthropic-messages.ts:647）。当响应头 x-shouldretry 为 true、没有状态码，或者状态码为 408、409、429、任何 500 及以上值时，它会重试。延迟先取自 retryafter-ms，再取自 retry-after（秒数或日期），否则采用 min(0.5 × 2^i, 8) 秒，再减去最多 25% 的随机抖动。服务器要求的延迟如果超过 maxRetryDelayMs（默认 60,000），会立即失败并显示 `Server requested <n>s retry delay (max: <m>s).`，以便外层展示它。尝试次数默认为 options.maxRetries ?? 0（ai/utils/provider-retry.ts:109）。八个适配器文件使用它；Bedrock、Codex、Mistral 和 pi-messages 不使用。



智能体级重试会重新运行整个助手轮次。isRetryableAssistantError 只检查 stopReason: "error" 的消息，先排除不可重试的模式，再接受可重试的模式（ai/utils/retry.ts:250）。不可重试列表涉及配额和计费：insufficient_quota、quota exceeded、billing、OpenCode 用量限制、ChatGPT 订阅限制（ai/utils/retry.ts:7）。可重试列表涵盖过载、速率限制、5xx 状态码、网络和套接字错误、WebSocket 关闭、过早结束的流，例如“stream ended before message_stop”，以及上述重试延迟消息（ai/utils/retry.ts:30）。retryAssistantCall 等待 baseDelayMs × 2^(attempt−1)，默认上限为 60 秒，并且绝不重试中止操作（ai/utils/retry.ts:126）。编码智能体在 AgentSession 中应用该分类器（CA/src/core/agent-session.ts:52），并在压缩中使用 retryAssistantCall（CA/src/core/compaction/compaction.ts:638）；参见“AgentSession：组装运行时”（原书第61页）。



上下文溢出是第三种判定，在重试之前检查。isContextOverflow(message, contextWindow?) 在三种情况下返回 true（ai/utils/overflow.ts:137）：

1. stopReason: "error"，且消息匹配 25 种厂商模式中的一种，例如 prompt is too long、exceeds the context window 或 maximum context length is \\d+ tokens，除非它同时匹配节流或速率限制模式。Cerebras 没有响应体的 400/413 也计算在内。

2. 静默溢出：stopReason: "stop"，且 input + cacheRead 超过窗口，如 z.ai 的行为。

3. 长度溢出：stopReason: "length"、输出为零，且 input + cacheRead 达到窗口的 99% 或更高，如 Xiaomi MiMo 的行为。



采集工具针对示例消息运行了这两个分类器，使用 200,000 token 的窗口：

```text
Anthropic 溢出                  overflow=true  retryable=false
Bedrock 节流                    overflow=false retryable=false
原始 ThrottlingException        overflow=true  retryable=false
过载                            overflow=false retryable=true
配额                            overflow=false retryable=false
重试延迟上限                    overflow=false retryable=true
Cerebras 无响应体                overflow=true  retryable=false
静默溢出（stop）                overflow=true  retryable=false
length、零输出、99%             overflow=true  retryable=false
```



> <strong>易踩的坑</strong>
> 
> Bedrock 节流错误既不会被重试，也不会被视为溢出。适配器将其格式化为 Throttling error: Too many tokens, please wait…（ai/api/bedrock-converse-stream.ts:375）。溢出检查排除了这一前缀，而可重试模式中没有任何一项匹配“throttling”，因此该轮次失败。如果排除检查碰到原始 SDK 文本 ThrottlingException: Too many tokens…，/too many tokens/i 就会匹配，随后这个轮次会被报告为上下文已满。上面两行都来自 research/out/auth-cost-retries-cost.txt。
> 
> 



从溢出中恢复需要 token 计数，而 pi-ai 不用 tokenizer 就能作出估算（ai/utils/estimate.ts）。它按每 token 4 个字符、每张图像 4,800 个字符计数。上下文估算值取自最后一条成功且时间晚于所有更早消息的助手消息的 usage，再加上其后消息的估算量（ai/utils/estimate.ts:97）。“压缩与分支摘要”（原书第92页）为智能体消息保留了同一方法的一个独立副本（CA/src/core/compaction/compaction.ts:196）；“流式事件协议”（原书第30页）展示了 buildBaseOptions 如何用它限制 maxTokens。



中止会把调用方的 signal 传给 SDK 或 fetch。已中止的消息会保留迄今流式传输的内容和 usage，正如“流式事件协议”（原书第30页）中的中止运行所示。上下文估算会跳过它，重放时 transformMessages 也会跳过它（“传输 API 与跨提供商交接”，原书第36页）。

## 模型目录



内置目录通过生成得到，而不是手写。



<BookFigure id="2.7" />

> 1,620 个目录条目：1,537 个聊天模型、60 个图像模型、23 个分类器模型。npm run build 会在 tsc 之前运行 generate-models；build:offline 复用已有数据。数量来自固定构建版本中 src/providers/data/.json 的统计；流水线依据 packages/ai/package.json（scripts）、scripts/generate-models.ts:1292–1771、src/providers/.models.ts 和 ai/providers/all.ts:136–191。
> 
> 



每个数据文件先按 API 分组，再以 `"<type>:<id>"` 为键；groq.json 以 {"openai-completions":{"chat:lama-3.1-8b-instant":{…}}} 开头（packages/ai/src/providers/data/groq.json）。类型层面的 ChatModelCatalog 将这些键映射到字面量类型（ai/model-catalog.ts:30），所以 `getBuiltinModel("anthropic", "<id>")` 能按具体模型获得类型（ai/providers/all.ts:62）。仓库的智能体规则禁止手工修改：“绝不要直接修改 packages/ai/src/models.generated.ts；应更新 packages/ai/scripts/generate-models.ts，然后重新生成”（AGENTS.md）。



动态提供商在运行时获取列表。Radius 实现了 refreshModels（ai/providers/radius.ts:49）；createProvider 通过 fetchModels 提供相同功能，并通过代次检查发布结果，避免已被取代的刷新覆盖更新的结果（ai/models.ts:1091、ai/models.ts:503）。结果通过 ModelsStore 持久化（ai/models-store.ts:22）。编码智能体将其存储在智能体目录中的 models-store.json 内，默认目录为 \~/.pi/agent（CA/src/core/models-store.ts:52）。

## faux 提供商



fauxProvider(options) 是一个响应经过编排的真实提供商（ai/providers/faux.ts:687）。本书中的每一次采集都使用它。它在 `http://localhost:0` 注册模型 faux-1，价格为零，并使用始终能够解析成功的 API 密钥身份验证，因此不需要密钥（ai/providers/faux.ts:24）。



响应：通过 setResponses 或 appendResponses 设置的队列。每一步可以是使用 fauxAssistantMessage、fauxText、fauxThinking 和 fauxToolCall 构建的 AssistantMessage，也可以是一个接收 context、options、调用状态和 model 的工厂。队列为空时，流以 No more faux responses queued 结束。



流式输出：每个内容块按 tokenSize token 拆成小块；默认每块 3–5 token，每个 token 按 4 个字符计算，并以真实 delta 事件发出（ai/providers/faux.ts:270）。tokensPerSecond 控制发送节奏；未设置时，会以消费方读取的速度尽快发出。



提示词缓存：存在 sessionId，且 cacheRetention 不为 none 时，usage 将当前提示词与该会话前一次提示词的公共前缀计为 cacheRead，其余计为 cacheWrite（ai/providers/faux.ts:230）。单轮采集展示了这一点：第一次调用写入 1,468 token，第二次读取这 1,468 token，并写入 24 token（research/out/one-turn.txt §session-jsonl）。



延迟响应：选项中带有 deferred 时，流以 stopReason: "deferred" 和一个句柄结束；轮询 pendingFetches 次后，fetchDeferred 返回编排好的响应。它是唯一实现了 fetchDeferred 和 cancelDeferred 的内置提供商。



编码智能体的测试套件通过兼容辅助函数 registerFauxProvider 在它之上运行（CA/test/suite/harness.ts:18），仓库规则也要求这样做：“对于 packages/coding-agent/test/suite/，请使用 test/suite/harness.ts 加 faux 提供商。不得使用真实提供商 API、密钥或付费 token”（AGENTS.md）。



> <strong>这对你意味着什么：</strong>
> 
> - 想让环境变量中的密钥生效，先移除已存储的凭据。
> 
> - 如果希望在编码智能体之外启用提供商级重试，请显式设置 maxRetries；pi-ai 默认不重试。
> 
> - 先检查 isContextOverflow，再检查 isRetryableAssistantError：溢出需要压缩，而不是重试。
> 
> - 将 usage.cost 视为基于目录价格的估算值；它只针对阶梯价格、一小时缓存写入和 OpenAI 服务层级作了调整。
> 
> - 使用 fauxProvider 进行测试；它执行的事件协议与厂商完全相同。
> 
> 



> 来源：ai/models.ts（calculateCost :1198、getAuth :742、refresh :551、publishProviderModels :503、createProvider :1039）。ai/types.ts:1058–1073。ai/api/openai-responses.ts:391–419；ai/api/openai-codex-responses.ts:602–630。ai/auth/types.ts；ai/auth/resolve.ts；ai/auth/helpers.ts（envApiKeyAuth）；ai/auth/oauth/\*.ts。ai/env-api-keys.ts；ai/providers/cloudflare-auth.ts。ai/utils/provider-retry.ts；ai/utils/retry.ts；ai/utils/overflow.ts；ai/utils/estimate.ts；ai/api/bedrock-converse-stream.ts:375–410。scripts/generate-models.ts；ai/model-catalog.ts；ai/models.generated.ts；ai/providers/all.ts；ai/models-store.ts；CA/src/core/models-store.ts。ai/providers/faux.ts；CA/test/suite/harness.ts；AGENTS.md。research/capture/auth-cost-retries-cost.mjs；research/out/auth-cost-retries-cost.txt；research/out/one-turn.txt。
> 
>
