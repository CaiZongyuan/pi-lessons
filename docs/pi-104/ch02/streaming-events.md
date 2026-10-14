---
title: "流式事件协议"
description: "Pi 1.0.4 · 2.2 · 原书第 30–35 页"
---

<div class="section-kicker">2.2 / THE PROVIDER LAYER</div>

# 流式事件协议

---

无论使用哪家厂商，Pi 中每个请求都返回相同的流，包含十二种事件类型。失败不会抛出异常，而是作为最后一个事件到达；甚至在身份验证尚未解析时，流就已经返回了。



智能体循环、TUI、RPC 客户端和扩展读取的都是同一套协议：AssistantMessageEvent。本节列出其中的事件，陈述并图示其顺序约定，并展示从 faux 提供商采集的一条真实事件流。随后追踪一次 models.stream() 调用如何从调用方抵达适配器：惰性初始化、身份验证、请求头合并，以及 streamSimple 添加的选项。

## 十二种事件



每次聊天调用都返回一个 `AssistantMessageEventStream`（ai/utils/event-stream.ts）。它是一个事件异步可迭代对象，还提供 `result(): Promise<AssistantMessage>`，最终解析为终止事件 done 或 error 携带的消息。在终止事件之后推入的事件都会被丢弃。



|<strong>事件</strong>|<strong>partial 之外的载荷</strong>|<strong>含义</strong>|
|---|---|---|
|start|—|厂商已接受请求；partial 是空消息，stopReason: "pending"|
|text_start|contentIndex|在该索引处追加了一个空文本块|
|text_delta|contentIndex、delta|向内容块追加文本|
|text_end|contentIndex、content|该内容块的最终文本|
|thinking_start · _delta · _end|与文本相同|思考块也采用相同的三个步骤|
|toolcall_start|contentIndex|追加了一个工具调用块|
|toolcall_delta|contentIndex、delta|参数 JSON 的原始片段|
|toolcall_end|contentIndex、toolCall|已解析的最终 ToolCall|
|done|reason、message（无 partial）|reason 为 stop、length、toolUse 或 deferred|
|error|reason、error（无 partial）|reason 为 aborted 或 error；error 是最终消息|



三种内容块 × start、delta、end，再加上一个起始事件和两个结束事件。依据 ai/types.ts:769–785。

## 核心规则



“成功的流在任何局部更新之前发出 start，并以 done 终止。如果在开始生成之前，请求初始化就失败，流可以直接以 error 终止；在 start 之后，失败也会以［原文缺失事件名］终止。当请求缺少身份验证时，直接调用会同步抛出异常。更新和［原文缺失事件名］绝不能出现在 start 之前。”（ai/types.ts:753）



<BookFigure id="2.3" />

> <strong>一个起始事件、任意数量的内容块、恰好一个终止事件。</strong>第二行是“核心规则”允许的路径：没有 start，直接发出 error。示意图，依据 ai/types.ts:753–785；每一种转换都在 research/out/streaming-protocol-events.txt 中观察到。
> 
> 



这一语法附带四条规则（ai/types.ts:762）：

- <strong>partial 是实时对象，不是快照。</strong>它是“共享的、表示迄今响应内容的实时辅助对象，而不是事件发生时的快照”。Anthropic 适配器会在每个事件中推入同一个 output 对象（ai/api/anthropic-messages.ts:658）。如果需要保存某个事件发生时的状态，请复制它。

- <strong>文本和思考只能通过增量增长。</strong>它们的内容块“在发出 `*_start` 事件时为空，之后仅通过对应的 `*_delta` 事件增长，直到作为权威结果的 `*_end`”。被隐藏的思考是例外：它“可能在 start 时已经完整，且不发出任何 delta”。

- <strong>工具调用参数始终是对象。</strong>toolcall_delta.delta 是原始 JSON 片段。适配器保存拼接后的字符串，并在每个 delta 到来时用 parseStreamingJson 重新解析：它先尝试带修复的 JSON.parse，再尝试 partial-json，然后对修复后的字符串使用 partial-json，失败时返回 {} 而不是抛出异常（ai/utils/json-parse.ts:104）。

- <strong>返回之后的错误是事件，而不是异常。</strong>“错误终止必须生成一条带有 stopReason ‘error’ 或 ‘aborted’ 以及 errorMessage 的 AssistantMessage，并通过流协议发出”（ai/types.ts:371）。

## 一条真实的流



采集工具为 faux 提供商（参见“身份验证、费用、重试与模型目录”，原书第41页）编排了一个思考块、一个文本块和一个工具调用，并打印通过 models.stream() 收到的每个事件。token 大小固定为 4 token，因此每个 delta 携带 16 个字符，运行结果是确定的（research/capture/streaming-protocol-events.mjs）。



```text
# $success（thinking + text + toolCall → done）
    1 start    · stopReason=pending
    2 thinking_start [0] · stopReason=pending
    3 thinking_delta [0] delta="The user wants t" · stopReason=pending
    4 thinking_delta [0] delta="he file." · stopReason=pending
    5 thinking_end [0] content="The user wants the file." · stopReason=pending
    6 text_start [1] · stopReason=pending
    7 text_delta [1] delta="Reading hello.tx" · stopReason=pending
    8 text_delta [1] delta="t." · stopReason=pending
    9 text_end [1] content="Reading hello.txt." · stopReason=pending
    10 toolcall_start [2] · stopReason=pending
    11 toolcall_delta [2] delta="{{\"path\":\"hello.t" · stopReason=pending
    12 toolcall_delta [2] delta="xt\"}" · stopReason=pending
    13 toolcall_end [2] toolCall={"id":"call_1","name":"read","arguments":{"path":"hello.txt"}} · stopReason=pending
    14 done    reason=toolUse · stopReason=toolUse
    result(): stopReason=toolUse blocks=["thinking","text","toolCall"]

# $no-response（faux 队列为空 → error，没有 start）
    1 error    reason=error · stopReason=error errorMessage="No more faux responses queued"
# $unconfigured（Provider 未配置 → error，没有 start）
    1 error    reason=error · stopReason=error errorMessage="Provider is not configured: nokey"
# $abort（在第一个 text_delta 之后中止 signal）
    1 start    · stopReason=pending
    2 text_start [0] · stopReason=pending
    3 text_delta [0] delta="This answer is l" · stopReason=pending
    4 text_delta [0] delta="ong enough to be" · stopReason=pending
    5 text_delta [0] delta=" cut off in the " · stopReason=pending
    6 text_delta [0] delta="middle of stream" · stopReason=pending
    7 error    reason=aborted · stopReason=aborted errorMessage="Request was aborted"
    result(): stopReason=aborted text="This answer is long enough to be cut off in the middle of stream"
```



可以把成功的那次运行理解为沿图 2.3（原书第31页）的语法走了一遍：一个 start，索引分别为 0、1、2 的三个内容块，一个 done。工具调用的 20 字符参数分两段到达，只有 toolcall_end 携带解析后的对象。同样的结构会包装在 message_update 事件中送达智能体循环；单轮采集从智能体一侧展示了这一过程（research/out/one-turn.txt §events）。



接下来的两次运行都在 start 之前结束。空响应队列和未配置的提供商都只产生一个 error。中止运行说明了两件事。signal 触发时已经排队的 delta 仍会送达：消费方在事件 3，也就是第一个 delta 时执行中止，之后又收到三个 delta。最终消息保留了迄今流式传输的文本，stopReason 为 aborted，而不是 error。



> <strong>易踩的坑</strong>
> 
> “核心规则”中的同步抛出只适用于直接调用适配器的 streamSimple() 时；Anthropic 适配器在创建流之前调用 assertRequestAuth（ai/api/anthropic-messages.ts:933）。通过 Models 调用时，同样的缺失密钥会成为 error 事件，正如未配置提供商的那次运行所示，因为 Models 先构建流，再在后台解析身份验证。需要处理这两种路径的代码，既要在调用外围加 try，也要在循环中设置 error 分支。
> 
> 

## 适配器如何构建消息



适配器遵循同一个六步模式，Anthropic 适配器完整展示了这一过程（ai/api/anthropic-messages.ts:571）：

1. 创建 output，content 为空、usage 为零、stopReason: "pending"（ai/api/anthropic-messages.ts:582）。

2. 通过 retryProviderRequest 发送请求，以状态和响应头调用 onResponse，然后推入 start（ai/api/anthropic-messages.ts:649）。

3. 对于每个厂商内容块，推入一个带有临时字段（index、partialJson）的块，并发出 `*_start`。修改它，再发出 `*_delta`。在厂商的块停止事件到达时，删除临时字段，并发出 `*_end`。

4. 每当厂商报告 usage 时更新它，并在每次更新之后调用 calculateCost（ai/api/anthropic-messages.ts:688）。

5. 结束时，如果 signal 已中止、stopReason 仍为 pending（“Anthropic stream ended without a stop reason”），或者厂商将停止映射为 error 或 aborted，则抛出异常。否则推入 done（ai/api/anthropic-messages.ts:861）。

6. 在 catch 中剥离临时字段；signal 已触发时将 stopReason 设为 aborted，否则设为 error；设置 errorMessage，并推入 error（ai/api/anthropic-messages.ts:887）。

    

由于第 6 步发生在任何局部输出之后，出错或中止的消息会保留其已有内容和 usage。“传输 API 与跨提供商交接”（原书第36页）会说明为什么这样的消息永远不会再次送入模型。



为了支持存储和重放，assistant-message-frame.ts 定义了 AssistantMessageFrame：它沿用相同的事件，但没有 partial，start 携带克隆后的消息，并额外提供一个帧 toolcall_checkpoint { json }。有些适配器会把初始参数放在 toolcall_start 中，随后又从空字符串开始流式传输 JSON；编码器会暂缓发送这些 delta，等它们赶上快照时，再发出一个 checkpoint（ai/utils/assistant-message-frame.ts:236）。



AssistantMessageFrameEncoder 会拒绝顺序错误的输入，例如“Assistant message done event appears before start”（ai/utils/assistant-message-frame.ts:153）。reduceAssistantMessageFrames 会重建消息（ai/utils/assistant-message-frame.ts:372）。终止状态的结算“被有意排除在外，必须单独持久化”。

## 请求分派



Models.stream() 同步返回流，并在后台完成其余工作（ai/models.ts:876）。



<BookFigure id="2.4" />

> <strong>调用方在身份验证解析前就已拿到流。</strong>步骤 1–2 在 Models 内部发生；步骤 2 中抛出的任何异常，例如“Provider is not configured”，都会成为单个 error 事件。依据 ai/models.ts:876–890（stream）、:842–874（applyAuth）和 ai/api/lazy.ts（lazyStream、forwardStream）。
> 
> 



- applyAuth 构建提供商请求（ai/models.ts:842）。它使用请求的 apiKey、env 和 signal 调用 getAuth(model)；如果没有解析到任何凭据，就抛出 `ModelsError("auth", "Provider is not configured: <id>")`；随后组装四项内容。

- apiKey：options.apiKey ?? auth.apiKey。每次请求显式提供的密钥优先。

- headers：按固定顺序进行不区分大小写的合并，后面的来源覆盖前面的来源：提供商身份验证请求头 → model.headers（在 getAuth 内）→ options.headers → options.transformHeaders()。最后一项是只有 Models 接受的钩子，会在分派之前移除（ai/models.ts:751、ai/models.ts:866）。

- env：已解析凭据中的提供商专属值，再叠加 options.env。

- baseUrl：若设置了 auth.baseUrl，它会在本次请求中替换 model.baseUrl。GitHub Copilot 的 OAuth toAuth 从 Copilot 令牌的 proxy-ep 字段推导出该值（ai/auth/oauth/github-copilot.ts:65）。



采集工具通过一个侦察提供商发送请求，以观察合并过程（research/capture/streaming-protocol-events.mjs）：



```js
auth.headers {"X-Auth":"auth","X-Model":"auth","X-Req":"auth","X-Drop":"auth"}
model.headers {"x-model":"model","X-Req":"model"}
options.headers {"x-req":"request","x-drop":null}
transformHeaders 收到 {"X-Auth":"auth","x-model":"model","x-req":"request","x-drop":null}
provider.stream headers={"X-Auth":"auth","x-model":"model","x-req":"request","x-drop":null,"X-Last":"transform"} apiKey="k-auth"
```



可以看到三个细节。后面的来源会替换前面的请求头，无论大小写如何，而且保留后者的拼写：X-Model 最终以 x-model 到达。null 值会在合并中保留下来；真正丢弃它的是适配器，因为“null 值会抑制提供商/API 中同名的默认请求头”（ai/types.ts:166）。Provider.headers 不参与此过程：Models 从不读取它（ai/models.ts:842）。



streamSimple 又增加了一层。适配器通过 buildBaseOptions，把不依赖提供商的选项转换成自身的选项（ai/api/simple-options.ts:36）。它将 maxTokens 限制在 contextWindow − 估计的上下文 token 数 − 4,096 以内，但永远不会低于 1（ai/api/simple-options.ts:18）。它按以下顺序合并采样参数：model.samplingParams，然后是经过限制的级别对应的 samplingParamsByThinkingLevel[level]，最后是请求自身的参数，每个键都覆盖前一个来源中的同名键（ai/api/simple-options.ts:24）。只有 OpenAI 兼容适配器会发送这些参数（ai/types.ts:202）。这里使用的估算方法见“身份验证、费用、重试与模型目录”（原书第41页）。



> <strong>这对你意味着什么：</strong>
> 
> - 将 error 当作普通终止事件处理；检查结果的 stopReason，不要依赖 try。
> 
> - 如果要保留 partial，就克隆它；下一个事件会修改它。
> 
> - 根据 partial.content[i].arguments 渲染工具调用进度，不要靠拼接 delta。
> 
> - 将每次请求的请求头放入 options.headers；用 null 移除默认值。
> 
> 



> 来源：ai/types.ts（StreamOptions :189、约定 :362–377、事件协议 :753–785）；ai/utils/event-stream.ts（EventStream、AssistantMessageEventStream）；ai/utils/json-parse.ts:104（parseStreamingJson）；ai/utils/assistant-message-frame.ts（AssistantMessageFrame、AssistantMessageFrameEncoder、reduceAssistantMessageFrames）；ai/api/anthropic-messages.ts（stream :571–901、streamSimple :928、createClient）；ai/api/lazy.ts（lazyStream、lazyApi）。ai/models.ts（mergeHeaders :373、getAuth :742、applyAuth :842、stream :876）；ai/api/simple-options.ts（clampMaxTokensToContext、resolveSamplingParams、buildBaseOptions）；ai/auth/oauth/github-copilot.ts；research/capture/streaming-protocol-events.mjs；research/out/streaming-protocol-events.txt；research/out/one-turn.txt §events。
> 
>
