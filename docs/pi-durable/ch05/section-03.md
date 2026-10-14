---
title: "副作用三明治"
---

<div class="section-kicker">PI DURABLE / 5.3 · P. 70</div>

# 副作用三明治

---

> 先提交你准备做什么，执行它，再提交发生了什么；中途崩溃留下的是一个明确的问题，而不是无声的空白。
> 
> 

Harness 可以原子提交自己的记录，但无法让银行卡扣款、部署或电子邮件与这些记录一起原子完成。如果进程恰好在扣款后死亡，客户到底付过钱没有？本节结束后，你就能把任意外部动作拆分成若干阶段，让每个崩溃点都有明确定义且安全的恢复方式。

## 为什么副作用需要自己的阶段



副作用是任何改变存储之外世界的动作：一次支付、一次 API 调用、另一台机器上的一个文件。副作用不得在提交内部执行（spec §1，不变量 4）。一次提交会占用 Session 的写入队列，因此在其中等待网络会阻塞所有其他写入方（提交，原书第29页）。所以，副作用总是发生在两次提交之间，而进程也可能在两者之间死亡。规范给出的答案是一种固定结构：

```text
提交意图阶段
执行外部副作用
提交结果或下一阶段
```

> 对应 spec §5\.2 的原文。
> 
> 



<BookFigure id="D.5.3" :show-caption="false" />

> 提交意图、执行副作用、提交结果；中途崩溃后，会重新运行副作用阶段。阶段来自 spec §5\.1 的支付示例。步骤 4 的条目和最终状态在同一次提交中落地。
> 
> 



规范自身的示例分为三部分。<strong>`prepare` 创建一个幂等键，并将其作为下一个检查点提交。`charge` 使用该键执行副作用，然后在同一次提交中追加回执条目并完成任务。中止处理函数撤销扣款，并提交 `aborted`。</strong>



意图、副作用、结果；来源：`docs/spec.md` §5\.1

```js
// 意图、副作用、结果。
prepare: async (task, runtime, context) => {
    await runtime.commit(() => ({ status: "running",
        checkpoint: { phase: "charge", key: newKey() } }), context);
},
charge: async (task, runtime, context) => {
    const receipt = await payments.charge(task.state.checkpoint.key); // 按键保证幂等
    await runtime.commit(async (tx, current) => {
        const entry = await tx.appendEntry(current.conversationId, receiptEntry(receipt));
        return { status: "terminal",
            outcome: { status: "completed", result: { entryId: entry.id } } };
    }, context);
},
// 中止处理函数决定结果；未提交结果就返回会使任务出现故障。
abort: async (task, runtime, context) => {
    await payments.cancel(task.state.checkpoint);
    await runtime.commit(() => ({ status: "terminal",
        outcome: { status: "aborted", reason: "user" } }), context);
},
```

> Two long lines are wrapped; nothing else is changed\.
> 
> 

## 每个崩溃点，以及重新打开后会发现什么



新进程打开存储时，之前处于 `running` 的每个任务都会带着检查点回到 `pending`（调度器，原书第73页）。说明任务做到哪里的，是检查点，而不是进程：

|<strong>崩溃时机</strong>|<strong>重新打开后发现</strong>|<strong>会运行什么</strong>|
|---|---|---|
|意图提交之前|检查点为 `prepare`|再次执行 `prepare`；尚未发出扣款|
|意图之后、扣款之前|检查点为 `charge`|首次执行扣款|
|扣款之后、结果之前|检查点为 `charge`|使用相同的键，再次执行扣款|
|结果提交之后|`terminal`|不执行任何内容|

> 对新进程来说，中间两行看起来完全相同。用规范的话说：“在意图阶段重新打开，意味着副作用可能已经发生。”
> 
> 



Harness 无法知道进程死亡之前，请求是否已经到达支付服务，因此无论是哪种情况，你的阶段都必须正确。规范指出了三种方式：“阶段处理函数安全地重试、轮询外部句柄，或记录中断”（spec §5\.2）:

- 安全重试：发送一个在意图阶段创建并存入检查点的幂等键。在恢复测试中，转账服务在关闭和重新打开前后被调用两次，但只执行一次转账，因为两次调用都携带 `transfer-N`（`test/harness-tasks-recovery.test.ts`）

- 轮询句柄：远程系统返回操作 ID 后，先提交该 ID，再等待，然后向远程系统查询结果。生成任务对延迟模型调用采用这种方式（生成，原书第91页）

- 记录中断：前两种方式都不可用时，提交一个结果，说明副作用可能已经发生，也可能尚未发生。未标记 `replay: "safe"` 的工具调用采用这种方式（工具调用与重放，原书第94页）

## 内置任务采用同样的结构



Harness 自身的任务也遵循副作用三明治结构，所以它们的恢复行为可以预测。`pi.tool` 任务在运行工具前一刻提交意图 `{ phase: "execute", arguments, replay }`。`replay` 来自工具，默认为 `"unsafe"`（`src/harness/tool.ts`）。在正常运行中，同一个阶段会继续执行工具并提交结果，因此 `execute` 阶段“只会在恢复时到达”。在该阶段，只有已存储策略和当前策略都声明安全时，它才会重新执行工具。否则，它会将调用提交为失败，错误为 `Tool NAME was interrupted and may have partially run`。



`pi.generation` 任务采用轮询。当提供商返回延迟句柄时，任务会提交一个 `poll` 检查点，包含该句柄和 `pollAt` 时间。循环中任何位置发生崩溃，重新打开时的检查点仍然指向该远程操作，中止处理函数也能用已存储的句柄取消它（`src/harness/generation.ts`）。



<aside class="manual-callout callout-warning durable-callout" role="note" data-source-page="72">

<strong>不回滚</strong>

Pi Durable 绝不撤销外部副作用。提交失败只会回滚 Harness 自己的记录（提交失败时，原书第33页）。撤销扣款取决于远程系统：它的幂等键、取消端点和操作句柄（限制与非目标，原书第168页）。

</aside>




> <strong>这对你意味着什么：</strong>
> 
> - 在意图阶段创建键。在副作用阶段内部创建的键会在每次重跑时改变，从而破坏去重。示例 12 从任务 ID 派生该键；商店采集记录在任何扣款发生之前，于 seq 4 提交 `"key": "charge-a"`
> 
> - 将结果与其后续变更一起提交。终态提交会原子地写入结果、追加结果条目、退役任务文档，并结算它所回答的提交请求（spec §5\.3）。分成两次提交会留下一个窗口：回执已经存在，但任务仍然存活
> 
> - 用memos保护同一阶段内的第二个副作用。商店订单的 `charge` 阶段只在memos `chargeId` 为空时调用服务（先 seq 5，再 seq 6）。调用与memos之间若发生崩溃，仍会重复调用，所以调用本身必须能够容忍重复
> 
>
