---
title: "生成"
---

<div class="section-kicker">PI DURABLE / 6.3 · P. 91</div>

# 生成

---

> 每次模型调用都会在发送之前保存模型、选项和对话记录截止点。恢复时重建该上下文，并再次执行请求钩子。
> 
> 

调用模型是智能体中耗时、昂贵而且容易失败的一步。提供商可能返回 503，上下文可能过长，进程也可能在流式输出中途崩溃。Pi Durable 将每次模型调用作为一种名为 generation 的持久化任务运行。它会提交模型、选项和对话记录截止点。崩溃后，它根据这些记录重建请求，再次执行请求钩子。读完本节，你就能跟踪模型调用经历的各个阶段，读取其重试状态，并说明在每个阶段崩溃的代价。

## 一次生成，一个轮次



一次 generation 是一个 `pi.generation` 任务（阶段与步骤，原书第67页）。它执行一次模型调用，决定接下来做什么，并拥有本轮次的工具调用。一次运行是一串 generation，它们依次交接运行控制权（运行控制，原书第88页）。



<BookFigure id="D.6.4" :show-caption="false" />

> 一次 generation 先准备，再调用模型，对响应分类，然后结束或循环。来源：`src/harness/generation.ts`。琥珀色方框是任务的阶段；request 和 poll 会调用提供商。白色方框表示任务如何结束。虚线方框表示任务正在等待它所拥有的压缩任务，之后以同一个 attempt 再次准备。工具轮次结束后，该任务完成，并由新的 generation 接管运行。图中未画出：可在任意阶段结束任务的中止，以及模型缺失的情形；后者会在 prepare、request 或 poll 中以 `no_model` 使任务失败。
> 
> 



|<strong>阶段</strong>|<strong>做什么</strong>|<strong>检查点保存什么</strong>|
|---|---|---|
|`prepare`|构建系统提示词与工具列表；检查压缩预算|尝试次数|
|`request`|调用模型并流式传输回答|模型、思考级别、流式选项和 cutoff|
|`retry`|等待退避时间结束|唤醒时间 `until`|
|`poll`|等待稍后回答的提供商|提供商的句柄和 `pollAt`|
|`tools`|等待本轮工具调用|助手条目和工具任务 ID|



对应 `src/harness/generation.ts` 中的 `GenerationCheckpoint` 联合类型。每个任务都从 `{ phase: "prepare", attempt: 1 }` 开始。

## 先准备，再发送



prepare 读取对话的智能体和设置（每个对话的智能体，原书第106页）。如果没有可用模型，运行以原因 `no_model` 失败。它渲染系统提示词（系统提示词，原书第115页），并检查是否需要先压缩上下文（压缩，原书第97页）。随后，一次提交将阶段转为 request，并固定模型、选项和对话记录截止点。cutoff 是请求中包含的最新对话记录条目。



恢复流程使用已保存的模型和选项，重建直到 cutoff 为止的已提交上下文。随后再次执行 `beforeRequest` 钩子：钩子对消息的替换不会被保存，重放时可能变化。智能体变更后的模型和选项会从下一次 prepare 开始生效，而每次重试都会经过 prepare。



request 构建消息，让 `beforeRequest` 钩子调整它们（钩子，原书第109页），然后流式接收响应。部分回答按照实时文档的节流规则提交（原书第88页）。每个请求都携带 sessionId：每个对话一个 ID，保存在内置的 `pi.provider` 文档中。提供商用它做提示词缓存。它会跨越重启、重试、重置和模型变更而保留；分叉则会获得一个新 ID。

## 响应决定什么



每个响应都会作为 `pi.assistant` 条目追加，并记录其费用（用量，原书第100页），失败响应也不例外。之后的请求会排除失败和中止的消息（从对话记录到上下文，原书第40页）。停止原因决定下一步。



|<strong>模型返回什么</strong>|<strong>下一步</strong>|
|---|---|
|工具调用（`toolUse`）|执行工具轮次（工具调用，原书第94页）|
|回答（`stop` 或 `length`）|回答 input；执行 final 边界|
|错误：上下文过长|压缩一次，然后再次 prepare|
|提供商可能恢复的错误|等待，然后重试|
|其他任何错误，或 `aborted`|input 以 `model_error` 结算为 `unanswered`；运行失败|
|`deferred`：“稍后再来”|在 `pollAfterMs` 之后轮询，默认为 5000 ms|

> `src/harness/generation.ts`。没有任何调用的 `toolUse` 响应视为回答。上下文过长的补救需要启用压缩，而且存在可截断的位置；缺少任一条件，或第二次溢出时，运行都会以 `model_error` 失败。
> 
> 



回答还可以继续延长。在结算 input 之前，`onYield` 钩子可以返回 `{ continue }`，附带更多用户内容。运行随后带着这条消息继续，input 保持未结算状态。只有同一个边界没有排队的用户消息或重置进入时，这才适用。

## 重试与延迟回答



重试策略是 `settings.retry`。默认在第一次尝试之后允许重试 3 次，从 2000 ms 开始，每次翻倍，上限为 60 000 ms。pi\-ai 决定哪些错误可重试。上下文过长从不按这种方式重试；只有压缩才能让它容得下。



一次 503、50 ms 的退避，然后得到回答，来源：`research/capture/extra-p6/retry.txt`

```text
seq 4 task 9 {"phase": "request", "attempt": 1, "cutoff": 7, ...}
seq 6 entry 10 pi.assistant, stopReason "error"
task 9 {"phase": "retry", "attempt": 1, "until": 1791211854633}
pi.live generation.retry = {"at": ..., "error": "503 service unavailable"}
seq 7 task 9 {"phase": "prepare", "attempt": 2}
seq 8 task 9 {"phase": "request", "attempt": 2, "cutoff": 10, ...}
seq 9 entry 11 pi.assistant; submission 8 done; task 9 completed
```

> 使用 `settings.retry.baseDelayMs = 50` 运行；部分提交已省略。第二次请求的 cutoff 包含错误条目，但构建上下文时会将其排除。
> 
> 



这两种等待都能跨重启保留。retry 会休眠到已提交的 until 时间，因此重新打开的进程只需完成剩余退避，而不必从头开始。poll 服务于稍后回答的提供商：它休眠到 pollAt，再次询问，并像处理流式结果一样处理返回结果。在 poll 期间中止，还会要求提供商取消该请求。

## 各阶段崩溃的代价



|<strong>崩溃发生于</strong>|<strong>哪些工作会再次执行</strong>|
|---|---|
|`prepare`|基于同一份对话记录重新准备|
|`request`，尚未流式接收任何内容|使用已保存的上下文、模型和选项；请求钩子再次执行|
|`request`，部分回答已提交|部分回答成为 aborted 条目；重建已保存的上下文，并再次执行请求钩子|
|`retry` 或 `poll`|剩余的等待|
|`tools`|本轮的收尾（工具轮次，原书第94页）|

> `test/harness-generation-recovery.test.ts` 和 `test/harness-tools-recovery.test.ts`。如果重启后固定的模型已经不存在，运行以 `no_model` 失败。
> 
> 



被打断的请求可能需要付费两次：提供商可能在崩溃之前已经完成工作，而重发又让它做了一遍。已提交的部分回答携带自己的 usage，因此账本会计入崩溃之前已流式传输的内容。



> <strong>这对你意味着什么：</strong>
> 
> - 重发保留已保存的模型和选项，但会再次执行请求钩子。如果需要完全相同的消息，应让钩子输出保持稳定
> 
> - 调整 `settings.retry`；`maxRetries` 统计的是第一次尝试之后的重试次数
> 
> - 为请求中途崩溃时偶尔出现的重复收费预留预算
> 
>
