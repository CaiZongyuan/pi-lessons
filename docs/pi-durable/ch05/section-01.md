---
title: "作为状态机的任务"
---

<div class="section-kicker">PI DURABLE / 5.1 · P. 63</div>

# 作为状态机的任务

---

> 任务是被拆分成若干阶段的工作；崩溃之后，唯一能保留下来的任务信息就是它的存储记录。
> 
> 

假设你的智能体正在执行银行卡扣款，做到一半，笔记本上盖突然合上了。进程再次启动时，总得有某样东西说明上次做到了哪里。在 Pi Durable 中，这样东西就是任务。本节结束后，你就能编写任务，说出它的五种状态，并读懂存储中的任务记录。

## 任务是一系列阶段



<strong>任务是 Harness 随执行推进而不断提交的工作单元。你将任务分为若干阶段，也就是 `prepare`、`charge` 这样的命名步骤。一个阶段完成自己那部分工作后，会提交一个检查点：一个小型 JSON 值，标明下一个阶段，并保存该阶段需要的全部内容。提交是原子保存：其中所有内容要么一并存储，要么全部不存储。如果进程死亡，下一个进程会读取最后一个检查点，再次运行相应阶段。除此之外，没有任何内容会延续下来。变量和闭包都已消失，只剩存储记录。</strong>



Pi Durable 中的所有工作都这样运行，包括 Harness 自身的模型调用、工具调用和压缩。你用 `defineTask()` 编写任务，并将其注册到扩展的 `tasks` 列表中。Harness 每次启动任务时，都会根据任务名称找到对应代码（扩展与注册表，原书第103页）。



一个两阶段支付任务；来源：`test/examples/12-tasks.ts`

```ts
type PaymentState = { phase: "prepare" } | { phase: "charge"; key: string };
const Payment = defineTask<{ amount: number }, PaymentState, { receipt: number }>({
    name: "example.payment",
    version: 1,
    initial: () => ({ phase: "prepare" }),
    phases: {
        prepare: async (task, runtime, taskContext) => {
            const checkpoint = { phase: "charge", key: `payment-${task.id}` } as const;
            await runtime.commit(() => ({ status: "running", checkpoint }), taskContext);
        },
        charge: async (task, runtime, taskContext) => {
            const key = task.state.checkpoint.key;
            if (!payments.has(key)) payments.set(key, task.input.amount * 100);
            const receipt = payments.get(key)!;
            const outcome = { status: "completed", result: { receipt } } as const;
            await runtime.commit(() => ({ status: "terminal", outcome }), taskContext);
        },
    },
    abort: async (_task, runtime, taskContext) => {
        const outcome = { status: "aborted" } as const;
        await runtime.commit(() => ({ status: "terminal", outcome }), taskContext);
    },
});
registry.install(defineExtension({ name: "payments", tasks: [Payment] }));
```

> 为适应页面宽度，两个内联状态字面量被提取为 `checkpoint` 和 `outcome` 常量。运行 12 打印 `{ status: 'completed', result: { receipt: 500 } }`。
> 
> 



从上到下阅读。`initial` 给出第一个检查点。`prepare` 选择一个幂等键，并将它提交到检查点 `{ phase: "charge", key }` 中。`charge` 从 `task.state.checkpoint` 读回该键，而不是从变量读取，因为重启后变量已经消失。随后，它提交最终结果。只有当某人中止任务时，`abort` 才会运行。



|<strong>字段</strong>|<strong>含义</strong>|
|---|---|
|`name`|任务的种类，存入每一条记录。重命名会让旧名称下已存储的任务失去对应代码|
|`version`|存入每一条记录。较新的定义必须迁移较旧的记录（调度器，原书第73页）|
|`initial(input)`|第一个检查点，在创建任务时提交|
|`phases`|每个阶段名称对应一个处理函数。每个处理函数看到的任务类型都已收窄到它自己的阶段|
|`abort`|中止后运行，必须提交最终结果（中止、故障与孤立，原书第80页）|
|`migrate?`|升级旧版本存储的输入和检查点|
|`hooks?`|其他扩展可以附加到此任务上的钩子（钩子，原书第109页）|

> 来源为 `src/types.ts` 中的 `TaskDefinition`。它的类型参数分别为输入 `I`、检查点 `S`、结果 `R` 和钩子 `H`。
> 
> 

## 五种状态



任务始终处于五种状态之一（`src/types.ts`）。其中三种是存活状态。<strong>`pending` 表示它正在排队等待运行。`running` 表示代码此刻正在执行它。`waiting` 表示它暂停下来，等待其他任务结束。另外两种状态已经持有结果。`completing` 表示结果已经确定，但任务启动的工作仍在运行。`terminal` 表示它已经彻底完成，此时记录就成了一份回执。</strong>



<BookFigure id="D.5.1" :show-caption="false" />

> 故障或孤立结果在子工作仍存活时，也会暂存为 `completing`。
> 
> 



`abortRequested` 是存活记录上的标志，不是一种状态：下一次启动将运行中止处理函数。



任务有五种状态；你的代码提交检查点、等待和结果，其余事情由 Harness 处理。状态边来自 `src/harness/scheduler.ts`。带有中止标记的 `waiting` 任务也会提前离开等待状态，运行中止处理函数；带有中止标记的 `pending` 或 `waiting` 任务，如果没有代码能够接手，则以 `orphaned` 结束。



你的代码只能通过 `runtime.commit()` 推动任务。一个阶段可以提交新检查点并保持 `running`，开始等待，或以 `terminal` 结束。它绝不能设置 `pending`。只有 Harness 会在崩溃后重新打开，或将任务交给新加载的代码时设置该状态。Harness 还会写入故障、孤立结果和中止标记：“调度器负责启动reservation、协调、交接、故障与孤立处理；`abortTask()` 负责中止标记”（spec §5\.1）。如果一个阶段结束时，它启动的任务仍在运行，Harness 会改为将它存成 `completing`（所有权，原书第76页）。

## 记录



任务的完整状态位于一条 JSON 记录中，每次提交都会整体替换该记录。<strong>下面是商店运行采集中的一个订单任务。它已完成银行卡扣款，启动了三个打包任务，目前正在等待它们。</strong>



订单任务 7，正在等待（提交 seq 7）；来源：`research/capture/task-transitions.txt`

```json
{
    "id": 7,
    "kind": "shop.order",
    "abortRequested": false,
    "state": {
        "status": "waiting",
        "checkpoint": { "phase": "decide", "chargeId": "ch_a_1", "packs": [8, 9, 10], ... },
        "on": [8, 9, 10],
        "policy": "failFast"
    },
    "memos": { "chargeId": "ch_a_1" }
}
```

> 省略了 `conversationId`、`version`、`input`、`background` 和检查点的 `key`。任务 7 没有 `owner` 字段，因为它的所有者是所属对话。
> 
> 



- `state`：状态，以及任务存活时的检查点，或结果确定后的结果

- `on`、`policy`：它等待的任务，以及其中一个失败时会发生什么（所有权，原书第76页）

- `memos`：小型存储值，首次写入者胜出（阶段与进展，原书第67页）

- `abortRequested`：持久化的中止标志

- `owner`：仅在子任务上设置



`conversationId` 和 `owner` 永远不会改变。尝试将任务移到另一个对话的提交，会被拒绝并报错 `Task N cannot change conversations`（`src/session/transaction.ts`）。



订单完成后，其记录会缩减成一份回执。检查点和memos被丢弃，状态中只保留结果：`{"status": "terminal", "outcome": {"status": "completed", "result": {"chargeId": "ch_a_1", "boxes": [...]}}}`（`capture/task-transitions.txt`）。终态记录会永久保留，因此要让结果尽量小。将大块数据放到条目或文档里，只返回其 ID（spec §12）。

## 结果



|<strong>状态</strong>|<strong>字段</strong>|<strong>写入方</strong>|<strong>含义</strong>|
|---|---|---|---|
|`completed`|`result`|任务|成功；带类型的 `R`|
|`failed`|`error`、`result?`|任务|预期内的失败，例如银行卡被拒|
|`aborted`|`reason?`、`result?`|其中止处理函数|已中止，任务完成了清理|
|`orphaned`|`reason`|Harness|中止时没有代码能够接手|
|`faulted`|`error`|Harness|缺陷：抛出异常，或阶段没有取得进展|

> 来源为 `src/types.ts` 中的 `TaskOutcome<R>`。每个错误都是普通 JSON：`{ message, detail? }`，绝不是运行时 `Error`。
> 
> 

## 阶段可以调用什么



每个阶段处理函数接收 `(task, runtime, context)`。`task` 是存储记录。`runtime` 是本次任务运行的工具箱，运行结束后它就会失效（`src/types.ts`）。

|<strong>用途</strong>|<strong>成员</strong>|
|---|---|
|提交|`commit(change, context)`、`memo(name, candidate, context)`|
|读取已提交状态|`memo(name)`、`getTask`、`outcomes`、`entry`、`context`、`snapshot`、`snapshotAsOf`、`watchDoc`|
|等待|`waitForTask`、`sleep(until)`|
|环境|`agent()`、`hooks`、`registry`、`settings`、`models`、`env()`、`conversation()`|
|身份与时钟|`taskId`、`conversationId`、`signal`、`now()`、`report()`|

> 来源为 `src/types.ts` 中的 `TaskRuntime`。
> 
> 



`runtime.commit()` 是唯一的提交途径。回调接收一个事务和当前记录。它可以追加条目、写入文档、创建子任务，也可以返回任务的下一个状态。所有内容都在一次原子提交中落地，因此检查点绝不会与它描述的数据不一致。以这种方式提交的条目会将任务记为其作者（`byTaskId`）（spec §5\.1）。如果运行已经结束、Harness 正在关闭、任务不再处于 `running`，或任务带有中止标记，提交会被拒绝。



> <strong>这对你意味着什么：</strong>
> 
> - 将下一个阶段需要的所有内容放入检查点。变量无法跨重启保留
> 
> - 将 `name` 视为永久不变。检查点结构变化时，提高 `version` 并添加 `migrate`
> 
> - 在同一次 `runtime.commit()` 中提交检查点及其描述的数据
> 
> - 保持结果小巧；将大块数据存入文档或条目
> 
>
