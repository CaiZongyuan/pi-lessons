---
title: "钩子"
---

<div class="section-kicker">PI DURABLE / 7.3 · P. 109</div>

# 钩子

---

> 钩子是内置任务在提交某项决定之前，向你的扩展提出的问题；你的回答会影响最终写入的内容。
> 
> 

你常常希望不重写智能体就能引导它：阻止危险的 shell 命令，在发出请求之前裁减旧消息，或者在模型回答不够好时要求它继续。钩子就是为此而设。读完本节，你就能编写每一种钩子，预测多个扩展的回答如何组合，并让人工批准在崩溃前后保持稳定。

## 会询问谁



扩展通过 `hook(task, handlers)` 注册处理函数，例如 `hook(ToolTask, { beforeTool })`。任务对象提供类型检查；系统只保留它的名称，因此“钩子能够跨越其任务的重新加载而保留”，见规范 §7\.2。



任务只询问其所属对话选中的扩展中的钩子。这就是全部作用域规则：“要将钩子限制到部分对话，只在这些对话中选择它所属的扩展”，见 README §Hooks。没有全局钩子。反过来，这对安全性很重要：如果对话的扩展列表没有包含你的权限扩展，它就会在没有该防护的情况下运行，见规范 §12。

## 七种钩子



generation 任务询问四种钩子，tool 任务询问两种，compaction 任务询问一种。多个扩展回答时，每种钩子按自己的方式组合回答。



|<strong>钩子</strong>|<strong>由谁询问</strong>|<strong>可以做什么</strong>|<strong>抛出异常时</strong>|
|---|---|---|---|
|`beforeRequest`|generation|替换这一次请求的消息；每个处理函数接收上一个处理函数的结果|报告并忽略|
|`afterResponse`|generation|观察每次模型响应|报告并忽略|
|`onYield`|generation|对最终回答返回 `{ continue }`；第一个胜出|报告并忽略|
|`afterTools`|generation|观察一轮已完成的工具结果|报告并忽略|
|`beforeTool`|tool|改写参数，或阻止调用；第一个阻止决定胜出|阻止调用|
|`afterTool`|tool|逐个处理函数替换结果|报告并忽略|
|`beforeCompact`|compaction|拒绝压缩，或提供摘要；第一个决定胜出|报告并忽略|



`GenerationHooks`、`ToolHooks` 和 `CompactionHooks`，见 `src/harness/types.ts`；规范 §7\.2；`src/harness/tool.ts`。“报告”指传给 `HarnessOptions.onReport`。处理函数按扩展顺序运行。防护钩子抛出异常时会阻止调用，也就是在失败时保持关闭。



<BookFigure id="D.7.4" :show-caption="false" />

> 每个钩子都是内置任务在它所影响的那次提交之前提出的问题。图中是一个使用工具的轮次及其最终回答，来自 `src/harness/generation.ts` 和 `tool.ts`；作为防护的 beforeTool 用粗体标出。beforeCompact 在压缩选定范围之后、生成摘要之前询问（压缩，原书第97页）。
> 
> 

## 用 memo 让决定经得住崩溃



钩子可能运行两次：“如果在使用钩子结果的提交之前崩溃，可能会再次运行它们”，见规范 §7\.2。对于纯粹的检查，这无伤大雅，但人工批准不应该再次询问或发生改变。用 `api.memo(name, …)` 保存决定；它保留第一个写入的值：重跑时尝试记录 `"denied"`，仍会得到 `"approved"`，见 `test/harness-tools.test.ts`。钩子共享发问任务的 memo 名称空间，因此应给自己的名称加上前缀（阶段、步骤与进度，原书第67页）。要在界面中显示状态，就将它提交到文档中（对话视图，原书第129页）。

## 将状态保存在文档中



选择扩展，决定对话是否拥有某种行为。文档则保存这种行为的状态。规范 §7\.2 中的计划模式就是这一模式：扩展在所有地方都被选中，它的 beforeTool 读取当前对话自己的 plan\-mode 文档。



由扩展文档驱动的钩子，来源：规范 §7\.2

```ts
const PlanModeDoc = defineDoc<{ enabled: boolean }>({
    kind: "app.plan-mode", version: 1, scope: "conversation",
    history: "latest", fork: "current", initial: () => ({ enabled: false }),
});

export const PlanMode = defineExtension({
    name: "plan-mode",
    hooks: [hook(ToolTask, {
    // 文档不存在，表示计划模式关闭。
    beforeTool: async (call, api, context) =>
    (await api.snapshot(PlanModeDoc, api.conversationId, context))?.enabled
    && writes(call)
    ? { block: "Plan mode: read-only" }
    : undefined,
    })],
});

// plan 切换这个对话的状态；不改变扩展选择。

await root.commit(async (tx) => {
    (await tx.doc(PlanModeDoc, root.id)).enabled = true;
}, context);
```

> 创建对话时，扩展没有初始化步骤，因此钩子会将缺失的文档视为“关闭”。示例 27 构建了另一种变体：通过改变选择配置来切换模式（构建编码智能体，原书第159页）。
> 
> 



> 细节：
> 
> - 参数检查两次：在 beforeTool 之前和之后，都根据工具的 schema 检查。改写后不符合 schema，会产生 `invalid_arguments`；阻止调用则产生 `blocked`
> 
> - 提交意图之后，不再重新执行 beforeTool：一旦调用意图已提交，恢复就会复用存储的参数（工具调用与重放，原书第94页）
> 
> - 钩子中的工作会让任务保持未关闭：钩子创建的任务由发问任务拥有，直到它结束之前，发问任务都会保持未关闭，见规范 §12
> 
> 



> <strong>这对你意味着什么：</strong>
> 
> - 把防护放在 beforeTool 中；抛出异常会阻止调用，这是安全的默认行为
> 
> - 在每个需要防护的对话中选择防护扩展，包括使用存储扩展列表的子智能体
> 
> - 将人工决定存入 memo，将模式状态存入文档
> 
> 



> 来源：`src/harness/define.ts` 的 `hook()`；`src/harness/types.ts`（`HookApi`、`GenerationHooks`、`ToolHooks`、`CompactionHooks`）；`src/harness/scheduler.ts`；`src/harness/agent.ts`；`src/harness/tool.ts`；`src/harness/generation.ts`；规范 §7\.2、§7\.3、§12；README §Hooks；`test/harness-tools.test.ts`
> 
>
