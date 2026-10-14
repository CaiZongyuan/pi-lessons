---
title: "用量与费用"
---

<div class="section-kicker">PI DURABLE / 6.6 · P. 100</div>

# 用量与费用

---

> 费用与产生它的响应在同一次提交中记录，因此账本与对话记录绝不会不一致。
> 
> 

这段对话到目前为止花了多少钱？`pi.usage` 会给出答案。账本与每次模型响应在同一次提交中更新，因此即使崩溃后，它也与对话记录完全吻合。读完本节，你就能读取账本，说明它统计了哪些尝试，并在不重复计费的情况下汇总多个对话的费用。

## 账本



`pi.usage` 是内置文档，每个对话一个，包含两个映射。models 以 `"provider/model"` 为键。tools 以工具名为键，用于那些自行支付模型调用费用的工具。每个值都是一条 pi\-ai 的 `Usage` 记录，与每条助手消息携带的结构相同。分叉从零开始计数。



一次工具调用和一次回答之后的 `pi.usage`，来源：`research/capture/extra-p6/live-run.txt`

```json
{
    "models": {
    "faux/faux-1": {
    "input": 74, "output": 15, "cacheRead": 54, "cacheWrite": 75, "totalTokens": 218,
    "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0 }
    }
    },
    "tools": {}
}
```



这是两次响应的总和：发起工具调用的响应（118 token）和最终回答。测试提供商报告的费用为零：

- token 计数：input、output、cacheRead、cacheWrite 和 totalTokens，始终存在

- 可选计数：提供商报告时，会有 cacheWrite1h（保留一小时的缓存写入）和 reasoning（用于思考的输出）

- cost：相同的分类，再加 total，由 pi\-ai 按模型定价

    

账本是持续累加的总和。每轮次费用仍保留在对话记录中：每个助手条目都携带自己的 usage。

## 哪些内容会计入



用量在追加响应的那次提交中记录，绝不延后。



|<strong>费用来源</strong>|<strong>记入</strong>|
|---|---|
|每次模型响应：回答、工具调用、失败尝试|`models`|
|崩溃或中止之前已提交的部分回答|`models`|
|每次摘要尝试，即使失败或最终过时|`models`|
|报告 usage 的工具结果|`tools[name]`|

> 规范 §8\.6；`src/harness/usage.ts`，由 `generation.ts`、`tool.ts` 和 `compaction.ts` 调用。
> 
> 



失败和中止的尝试也会计入，因为提供商已为它们收费。如果某次尝试在任何内容提交之前就被打断，它没有响应，因此不会计入任何费用；重发请求会在得到回答时计入。

## 跨对话汇总



每个对话只统计自己的费用。`harness.usage()` 将每个对话的账本累加成一个总额；这个总额不会存储在任何地方。对于其他汇总方式，例如一棵子智能体树，需要你自行遍历 `scanConversations()`，对账本求和。



<BookFigure id="D.6.8" :show-caption="false" />

> 费用只记录一次，记录在产生它的对话中，并位于记录响应的那次提交里。写入方来自规范 §8\.6；models 总额来自 `research/capture/extra-p6/live-run.txt`。虚线路径表示规范 §12 中的重复计入。
> 
> 



<aside class="manual-callout callout-warning durable-callout" role="note" data-source-page="101">

<strong>重复计入</strong>

如果某个工具让子智能体在独立对话中运行，就绝不能在结果的 usage 中报告该对话的费用。子对话的 `pi.usage` 已经计入了这笔费用，因此 `harness.usage()` 会重复计算（子智能体，原书第121页）。

</aside>




界面像读取其他文档一样读取账本，通过对话视图的 `docs["pi.usage"]` 访问（对话视图，原书第129页）。



> <strong>这对你意味着什么：</strong>
> 
> - 从 `pi.usage` 读取单个对话的费用，从 `harness.usage()` 读取总费用
> 
> - 仅为工具直接承担的费用报告工具 usage
> 
> - 工具名是数据：使用 `Object.entries()` 读取这些映射，不要用属性访问，以防某个工具名叫 `__proto__`
> 
> 



> 来源：规范 §8\.6、§12；`src/harness/usage.ts`；`src/harness/generation.ts`；`src/harness/tool.ts`；`src/harness/compaction.ts`；`src/harness/harness.ts`（usage）；README §Usage and Cost；`test/harness-inbox.test.ts`（describe “usage”）；`test/harness-compaction.test.ts`；`research/capture/extra-p6/live-run.txt`
> 
>
