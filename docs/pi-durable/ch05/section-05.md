---
title: "所有权与结构化并发"
---

<div class="section-kicker">PI DURABLE / 5.5 · P. 76</div>

# 所有权与结构化并发

---

> 任务启动的工作归它所有：这些工作没有结束之前，任务就不能结束；中止任务也会中止这些工作。
> 
> 

一次结账会启动四笔银行卡支付。仍有支付在进行时，它不应该报告完成；如果客户取消，支付也应该被中止。所有权同时提供这两种保证。本节结束后，你就能创建子任务，用合适的策略等待它们，并预测任务何时会暂留在 `completing`。

## 一棵所有权树



<strong>每个任务都有所有者，在创建时设置，此后永不改变。</strong>通过 `tx.createTask(task, input, { ownership })` 的 `ownership` 传入它（spec §5\.5）：

- <strong>`{ kind: "conversation" }`：顶层任务，由所属对话拥有</strong>

- <strong>`{ kind: "task", taskId }`：子任务，由另一个任务拥有，且始终位于该任务所在的对话中</strong>



对话也可以有所有者。子智能体的对话由创建它的工具任务拥有（有所有者的对话，原书第43页）。任务和对话一起组成一棵树。分叉不参与这棵树。



<BookFigure id="D.5.5" :show-caption="false" />

> 任务和对话组成一棵所有权树，后台任务会截断其下方的子树。图中并列展示了 README §Abort and Subagents 及示例 22 的前台子智能体，以及示例 23 的后台锚点。生成任务拥有自己的工具任务（README §Concepts）。
> 
> 



<strong>创建子任务时，所有者必须仍然存活：不处于 `completing`，不处于 `terminal`，也没有中止标记。</strong>检查使用的是提交结束后将留下的状态（`src/session/transaction.ts`）。因此，任务不能在使自己完成的同一次提交中创建子任务。商店采集记录的场景 D 正是这样尝试的。提交被拒绝，错误为 `Task owner 12 is completing`，阶段抛出异常，任务在 seq 27 发生故障。请在一次提交中创建子任务，再在之后的提交中完成自己。

## 前台与后台工作



任务拥有的工作，是树中它下方的所有内容：它的子任务、它所拥有对话中的任务，以及再往下的所有内容。规范将其称为普通的所属工作，遍历会在后台任务处停止。后台任务是以 `background: true` 创建、由对话拥有的任务。普通等待和中止会跳过它“以及它完整的所属子树”（spec §5\.4）。空闲等待采用相同规则：`Conversation.waitForIdle()` 会在该对话下方不再有存活的前台任务时返回。

## 等待任务



阶段通过返回 `{ status: "waiting", checkpoint, on, policy }` 来等待。此时任务没有调用实例。`on` 中的所有任务结束后，它从 `checkpoint` 恢复，并通过 `runtime.outcomes(ids)` 按顺序读取它们的结果。示例 24 的结账任务在同一次提交中创建四个支付任务并等待它们：



在一次提交中创建子任务并等待；来源：`test/examples/24-child-tasks.ts`

```ts
pay: async (task, runtime, taskContext) => {
    await runtime.commit(async (tx) => {
        const payments: TaskId<PaymentResult>[] = [];
        for (const card of task.input.cards) {
            const ownership = { kind: "task", taskId: task.id } as const;
            payments.push(await tx.createTask(Payment, { card }, { ownership }));
        }
        return { status: "waiting", checkpoint: { phase: "decide", payments },
            on: payments, policy: "failFast" };
    }, taskContext);
},
```

> 为适应页面宽度，所有权字面量已被提取。`decide` 阶段读取 `runtime.outcomes(payments)`，只有每笔支付都 `completed` 时，才提交 `completed`。
> 
> 



提交等待时会检查 `on` 的规则，违反任意一条都会让任务出现故障（`src/harness/scheduler.ts`）：

- `on` 不能列出不存在的任务、任务自身，或其任意所有者，“因为它们不可能先于该任务结束”

- `failFast` 只能列出等待方拥有的任务。`allSettled` 可以列出任何任务，甚至已经结束的任务

- 空的 `on` 会在下一轮调度时恢复

- 中止处理函数完全不能进入等待状态

## `allSettled` 还是 `failFast`



策略决定某个任务失败时，其他任务会发生什么。使用 `allSettled` 时，什么也不会发生：无论结果如何，等待方都会在最后一个任务结束后恢复。使用 `failFast` 时，“`on` 中第一个暂存或以非 `completed` 结果结束的任务，会在调度器下一次协调提交中，为 `on` 中其他所有存活任务加上中止标记”（spec §5\.5）。等待方自身不会被中止。它会恢复，并决定自己的结果。



<BookFigure id="D.5.6" :show-caption="false" />

> 一笔支付失败后，下次提交会中止其仍存活的兄弟任务；结账任务自身始终不会被标记为中止。这是示例 24 的第一个场景，逐提交记录在 `research/capture/extra-p5/checkout-transitions.txt` 中。每个条形代表一次提交后的状态，该状态持续到下一次提交改写它；终态记录永远不会重写（斜线填充）。`marked` 表示带有中止标记的 `running`。
> 
> 



从左向右阅读此图。在 seq 6，支付任务 9（`expired-2`）失败。在 seq 7，一次提交为支付任务 8、10、11 加上中止标记，其中止处理函数会退款。到 seq 10 时，三个任务都已 `aborted`。在 seq 11，结账任务从 `decide` 恢复，读到 `aborted`、`failed`、`aborted`、`aborted`，并在 seq 12 提交 `failed`。

## `completing`：所有者等待其工作



如果任务结束时，其拥有的工作仍在运行，它会被提交为 `{ status: "completing", outcome }`。结果已经固定，但任务尚未完成。一旦其下方不再有任何存活工作，调度器就会提交最终的 `terminal` 记录（spec §5\.5）。商店订单展示了完整过程：

|<strong>SEQ</strong>|<strong>任务</strong>|<strong>状态</strong>|<strong>发生了什么</strong>|
|---|---|---|---|
|13|7 order|running|检查点为 `finish`；在同一次提交中创建回执子任务 11|
|14|11 send\-receipt|running|已启动|
|15|7 order|completing|`finish` 提交 `completed`；子任务 11 仍存活|
|16|11 send\-receipt|terminal|`completed`，`"sent"`|
|17|7 order|terminal|调度器的最终提交；`waitForTask(7)` 完成|

> 场景 A，`research/capture/task-transitions.txt`。
> 
> 



暂存的结果遵循五条规则（spec §5\.5）：

1. 它是最终结果。阶段和中止处理函数都不会再运行，任务也绝不会重启或迁移

2. 中止一个 `completing` 任务，只会为它加上标记，从而中止下方工作。最终记录保留暂存结果

3. 非 `completed` 的暂存结果视为取消意图，因此先中止下方工作。这样的暂存失败，也会在自己的工作尚未全部结束时触发 `failFast`（`test/harness-structured.test.ts`）

4. 写入在暂存点处分开。结束提交中的条目和文档立即落地。终态、任务文档的退役，以及任务的等待方，都要等待最终提交

5. 等待方、空闲等待和 `inspect()` 都将 `completing` 任务视为仍然存活



<aside class="manual-callout callout-warning durable-callout" role="note" data-source-page="79">

<strong>容易出乎意料的暂留</strong>

扩展在子智能体对话中启动的前台工作，会让调用它的工具保持未完成，进而让整个运行保持未完成。在工具处于 `completing` 时继续向子智能体提问，会延长这一暂留。对于不应阻止所有者完成的工作，应将它创建为由对话拥有的后台工作（spec §12）。

</aside>




> <strong>这对你意味着什么：</strong>
> 
> - 如果任务的结果依赖某项工作，就让该任务成为这项工作的所有者
> 
> - 对要求全部成功的子任务使用 `failFast`；希望拿到每个结果时使用 `allSettled`
> 
> - 在一次提交中创建子任务，再在后续提交中结束父任务
> 
> - 对不得阻止调用方完成的工作，使用由对话拥有的后台任务
> 
> 



> 来源：spec §5\.4、§5\.5、§12；README §Concepts、§Abort and Subagents、§Child Tasks；`src/types.ts`（`TaskOwnership`、`TaskOptions`、`JoinPolicy`）；`src/session/transaction.ts`；`src/harness/scheduler.ts`；`test/harness-structured.test.ts`；示例 22、23、24；运行 24；`research/capture/task-transitions.txt`；`research/capture/extra-p5/checkout-transitions.txt`。
> 
>
