<a id="sec-5-1"></a>

## 5.1 任务即状态机

<p class="lede">任务是被切成若干阶段的工作，而关于它的全部信息中，唯一能在崩溃后存续下来的，是它的存储记录。</p>
假设你的智能体正在给一张卡扣款，中途笔记本合上了。进程恢复后，必须有某个东西说明它进行到了哪一步。在 Pi Durable 中，这个东西就是任务。读完本节，你可以编写一个任务、说出它的五种状态，并从存储中读取一条任务记录。

### 任务就是一份阶段列表

任务是 Harness 在推进过程中逐步提交的一份工作单元。你把它拆成若干阶段——诸如 `prepare` 和 `charge` 这样的具名步骤。当一个阶段做完它的那部分，就提交一个检查点：一个小的 JSON 值，指明下一个阶段，并携带该阶段需要的一切。提交是一次原子保存：其中的内容要么一起存下，要么都不存。如果进程死了，下一个进程就读取最后一个检查点，重新运行那个阶段。别的什么都不保留。变量和闭包都没了，只剩下存储的记录。Pi Durable 里所有工作都是这样运行的，包括 Harness 自己的模型调用、工具调用和压缩。你用 `defineTask()` 编写一个任务，并在某个扩展的 `tasks` 列表中注册它。Harness 每次启动该任务时都按任务名找到这段代码（扩展与注册表（p. 103））。

<aside class="note">一个两阶段支付任务 test/examples/12-tasks.ts TS</aside>
```ts
type PaymentState = { phase: "prepare" } | { phase: "charge"; key: string };
const Payment = defineTask<{ amount: number }, PaymentState, { receipt: number }>({
name: "example.payment",
version: 1,
initial: () => ({ phase: "prepare" }),
phases: {
prepare: async (task, runtime, taskContext) => {
const checkpoint = { phase: "charge", key: `payment-${task.id}` } as const;
await runtime.commit(() => ({ status: "running", checkpoint }), taskContext); },
charge: async (task, runtime, taskContext) => {
const key = task.state.checkpoint.key; if (!payments.has(key)) payments.set(key, task.input.amount * 100);
const receipt = payments.get(key)!;
const outcome = { status: "completed", result: { receipt } } as const; await runtime.commit(() => ({ status: "terminal", outcome }), taskContext);
},
```

```ts
}, abort: async (_task, runtime, taskContext) => {
const outcome = { status: "aborted" } as const;
await runtime.commit(() => ({ status: "terminal", outcome }), taskContext);
}, });
registry.install(defineExtension({ name: "payments", tasks: [Payment] }));
Two inline state literals are hoisted into checkpoint and outcome constants to fit the page. Run 12 prints { status: 'completed', result: { receipt:
500 } }.
```

自上而下读一遍。`initial` 给出第一个检查点。`prepare` 挑一个幂等键，并把它提交在检查点 `{ phase: "charge", key }` 里。`charge` 从 `task.state.checkpoint` 把键读回来，而不是从一个变量读，因为重启后那个变量就没了。然后它提交最终 outcome。只有有人中止这个任务时，`abort` 才会运行。

<img src="/pi-lessons/_assets/pi-durable/05-tasks/fig-5.1.png" alt="THE TASK STATE MACHINE
S T A T E" loading="lazy">

*一个任务有五种状态；你的代码提交检查点、等待和 outcome，剩下的由 Harness 完成。边取自 `src/harness/scheduler.ts`。一个带中止标记的 waiting 任务也会提前离开 waiting 去运行它的中止处理器；一个带中止标记、又没有任何代码能接手的 pending 或 waiting 任务则最终落到 orphaned。*

<aside class="note">`name` 任务的种类，存进每一条记录。改名会让已存的旧名任务搁浅。`version` 与每条记录一起存储，更新的定义必须迁移旧记录（调度器（p. 73））。`initial(input)` 第一个检查点，在任务创建时提交。`phases` 每个阶段名一个处理器。每个处理器看到的任务都已收窄到它自己的阶段。`abort` 在中止之后运行，必须提交一个最终 outcome（中止、故障与孤儿（p. 80））。`migrate?` 升级旧版本存储的输入和检查点。`hooks?` 其他扩展可以挂到这个任务上的钩子（钩子（p. 109））。</aside>
```
```

<aside class="note">`src/types.ts` 中的 `TaskDefinition`。它的类型参数分别是输入 I、检查点 S、结果 R 和钩子 H。</aside>
### 五种状态

任务永远处于五种状态之一（`src/types.ts`）。其中三种是活的。`pending` 表示它在排队等待运行。`running` 表示此刻有代码在执行它。`waiting` 表示它已暂停，直到其他任务完成。另外两种持有结果。`completing` 表示结果已定，但它启动的工作还在运行。`terminal` 表示它已彻底结束，此时记录就是一张回执。

<aside class="note">一个任务有五种状态；你的代码提交检查点、等待和 outcome，剩下的由 Harness 完成。边取自 `src/harness/scheduler.ts`。一个带中止标记的 waiting 任务也会提前离开 waiting 去运行它的中止处理器；一个带中止标记、又没有任何代码能接手的 pending 或 waiting 任务则最终落到 orphaned。</aside>
你的代码只能通过 `runtime.commit()` 移动任务。一个阶段可以提交新的检查点并保持 running，可以开始一次等待，也可以以 terminal 结束。它永远不能设置 pending。只有 Harness 会这么做——在崩溃后重开，或把任务交给新加载的代码时。Harness 还负责写入故障、孤儿和中止标记：「调度器拥有预留、对账、交接、故障和孤儿化；`abortTask()` 拥有中止标记」（spec §5.1）。如果一个阶段结束时它启动的任务还在运行，Harness 会把它存成 completing（所有权（p. 76））。

### 记录

任务的全部状态都放在一条 JSON 记录里，每次提交都整条替换记录。下面是一条来自抓取的商店运行的记录。它已经扣过款，发起了三个打包任务，正在等它们。

<aside class="note">order 任务 7，waiting（提交序号 7）research/capture/task-transitions.txt JSON</aside>
```json
{
"id": 7,
"kind": "shop.order",
"abortRequested": false,
"state": {
"status": "waiting",
"checkpoint": { "phase": "decide", "chargeId": "ch_a_1", "packs": [8, 9, 10], … },
"on": [8, 9, 10], "policy": "failFast"
},
```

```
"memos": { "chargeId": "ch_a_1" } }
```

<aside class="note">已省略：`conversationId`、`version`、`input`、`background` 以及检查点的 `key`。任务 7 没有 owner 字段，因为它由自己的会话拥有。</aside>
state —— 状态；在任务存活期间是检查点，有结果后则是 outcome。`on`、`policy` —— 它等待的任务，以及其中一个失败时会怎样（所有权（p. 76））。`memos` —— 一些小的存储值，先写入者胜（阶段与进度（p. 67））。`abortRequested` —— 持久化的中止标志。`owner` —— 只在子任务上设置。`conversationId` 和 `owner` 永不改变。试图把任务移到另一个会话的提交会被拒绝，报 `Task N cannot change conversations`（`src/session/transaction.ts`）。订单完成后，它的记录会收缩成一张回执：检查点和 memos 被丢弃，state 只保留 outcome：`{"status": "terminal", "outcome": {"status": "completed", "result": {"chargeId": "ch_a_1", "boxes": [...]}}}`（`capture/task-transitions.txt`）。terminal 记录永久保留，所以结果要保持精简。把大数据放进条目或文档，只返回它的 ID（spec §12）。

<aside class="note">`completed` `result` 任务成功，即带类型的 R。`failed` `error`、`result?` 任务出现了预期内的失败，比如被拒的卡。`aborted` `reason?`、`result?` 它的中止处理器已中止，任务也清理完毕。`orphaned` `reason` 没有代码能接手该任务，Harness 因而中止了它。</aside>
```
faulted error the Harness a bug: a throw, or a phase that made no progress
```

<aside class="note">`src/types.ts` 中的 `TaskOutcome<R>`。每个 error 都是纯 JSON，形如 `{ message, detail? }`，绝不是运行时的 `Error`。</aside>
### 阶段能调用什么

每个阶段处理器收到 `(task, runtime, context)`。`task` 是存储的记录。`runtime` 是这次任务运行的工具箱，这次运行结束就失效（`src/types.ts`）。

<aside class="note">提交 `commit(change, context)`、`memo(name, candidate, context)` 读取已提交状态 `memo(name)`、`getTask`、`outcomes`、`entry`、`context`、`snapshot`、`snapshotAsOf`、`watchDoc` 等待 `waitForTask`、`sleep(until)` 环境 `agent()`、`hooks`、`registry`、`settings`、`models`、`env()`、`conversation()` 身份与时钟 `taskId`、`conversationId`、`signal`、`now()`、`report()`。`src/types.ts` 中的 `TaskRuntime`。</aside>
`runtime.commit()` 是唯一的提交方式。你的回调会收到一个事务和当前记录。它可以追加条目、写入文档、创建子任务，也可以返回任务的下一种状态。所有这些都落在同一次原子提交里，所以检查点永远不会和它所描述的数据不一致。以这种方式提交的条目会把该任务记为它们的作者（`byTaskId`）（spec §5.1）。如果这次运行已经结束、Harness 正在关闭、任务已不在 running，或任务带有中止标记，提交都会被拒绝。

<aside class="note">把下一个阶段需要的一切都放进检查点。变量不会在重启后存活。把 `name` 当作永久的。当检查点的形状变化时，提高 `version` 并加上 `migrate`。在同一次 `runtime.commit()` 里提交检查点和它所描述的数据。outcome 要保持精简；批量数据放进文档或条目。</aside>
```
Sources: spec §1, §5.1, §5.3, §12; src/tasks.ts; src/types.ts (TaskDefinition, TaskState, TaskRecord, TaskOutcome, TaskRuntime); src/harness/scheduler.ts; src/session/transaction.ts; ex 12, run 12; research/capture/task-transitions.txt.
```

<img src="/pi-lessons/_assets/pi-durable/05-tasks/fig-5.2.png" alt="THE STEP BEFORE EVERY PHASE
D E C I S I O N" loading="lazy">

*每个阶段之前，step 会套用第一条匹配的规则；没有进展就是故障。规则来自 spec §5.1，实现在 `src/harness/scheduler.ts`。*

<a id="sec-5-2"></a>

## 5.2 阶段、步骤与进度

<p class="lede">一个什么新东西都不提交的阶段会永远运行，所以 Harness 改为用故障停掉这个任务。</p>
任务一个阶段接一个阶段地运行。阶段之间 Harness 做一个快速检查：任务是否已完成、中止或正在关闭，以及上一个阶段是否提交了进展。读完本节，你就能对任何阶段预测这次检查，设计始终有进展的阶段，并安全地使用 memos 和 sleep。

### 一次运行，多个阶段

Harness 启动一个任务时，会创建一个 invocation：任务在内存中的一次运行，带着自己的中止信号。一个 invocation 会一个阶段接一个阶段地运行，直到任务完成、等待或被停止。提交检查点并不会结束它。下一个阶段立刻在同一个进程里开始。每个阶段之前，Harness 会运行一个 step——一段读取已提交记录、决定是否继续的简短检查。step 本身就是 Session 单一写入队列上的一次提交（提交（p. 29）），所以它在返回前能看到该阶段做过的每一次提交。在 step 之后才进入队列的提交会被拒绝，报 `invocation has ended`（`test/harness-tasks.test.ts`）。

<aside class="note">每个阶段之前，step 会套用第一条匹配的规则；没有进展就是故障。规则来自 spec §5.1，实现在 `src/harness/scheduler.ts`。</aside>
### 六条规则

第一个阶段之前只有规则 1–3 适用，因为还没有任何东西返回。一个阶段返回后，第一条匹配的规则获胜：1. 已完成、completing 或 waiting：停。该阶段提交了 outcome 或一次等待。没有更多东西要运行。2. Harness 正在关闭：停。检查点和任何中止标记都留给下一个进程。关闭从不写 outcome。3. 有中止标记：结束本次运行。之后会单独启动一次中止运行，等该任务自己的子工作完成后进行（中止（p. 80））。4. 阶段抛出：写入 faulted 和该错误的消息。和每个 outcome 一样，在该任务的

- 子工作仍存活期间，它会以 completing 持有（所有权（p. 76））。
5. 检查点变了：继续进入下一个阶段，或把任务交给新加载的代码（调度器（p. 73））。6. 检查点没变：写入 faulted，原因是「没有取得持久进展」，同样以 completing 持有，

- 只要子工作还存活。
顺序在两种情况下至关重要。一个提交了新检查点随后抛出的阶段仍然是 faulted，因为规则 4 在规则 5 之前。一个提交了最终 outcome 随后抛出的阶段会保留它的 outcome，因为规则 1 在最前。此后它尝试的任何提交都会被拒绝，报 `Task N is terminal`（`test/harness-tasks.test.ts`）。

### 为什么没有进展算故障

一个结束时检查点还和开始时一样的阶段，会带着同样的输入永远重复运行。所以 step 把两个检查点当作 JSON 比较，忽略键序。如果相等，它就用 `Task test.idle phase run returned without durable progress` 让任务进入故障（`test/harness-tasks.test.ts`）。三种写法会踩到这条规则：

- 阶段返回时没有提交任何东西。
- 阶段提交了条目或文档，但没有从 `runtime.commit()` 返回新状态。只有检查点才算
- 进展。
- 阶段提交了一份与旧检查点相同的副本。
一个阶段可以再次运行自己，只要检查点发生变化。示例 13 的 ticker 只有一个阶段 `tick`，每轮提交 `{ phase: "tick", n: n + 1 }`。阶段名不变，检查点变了，所以规则 5 让它继续。

### memos：记住一个小决定

memo 是存在任务记录上的一个小的具名值。先写入者胜。`runtime.memo(name, candidate)` 只在该名字仍为空时提交候选值，无论如何都返回已存的胜出者。`runtime.memo(name)` 只读（spec §5.2）。同时写入 `"a"` 和 `"b"` 时，两者都拿回 `"a"`（`test/harness-tasks.test.ts`）。memos 能跨重启存活，任务完成时被丢弃。提交 memo 不算进展。用 memo 防止一个阶段内部的某个效果重复发生。示例 13 每次 tick 只打印一次，即使它的阶段运行了两次：

<aside class="note">一个 memo 在一个阶段内部守住一个效果 test/examples/13-recovery.ts TS</aside>
```ts
tick: async (task, runtime, taskContext) => {
const n = task.state.checkpoint.n;
if ((await runtime.memo(`printed-${n}`, taskContext)) === undefined) {
await runtime.memo(`printed-${n}`, true, taskContext);
console.log(`tick ${n}`); }
// …commit { phase: "tick", n: n + 1 }, or terminal once n reaches task.input.to
await runtime.sleep(Date.now() + 50, taskContext); },
```

<aside class="note">已省略检查点提交和一个仅供测试的钩子。</aside>
<aside class="note">$ node --conditions=source --experimental-strip-types test/examples/13-recovery.ts tick 1 tick 2</aside>
```
closed; saved checkpoint: { status: 'pending', checkpoint: { phase: 'tick', n: 2 } }
memos: { 'printed-1': true, 'printed-2': true }
```

<aside class="note">tick 3 tick 4 tick 5</aside>
```
after reopen: { status: 'completed', result: 'counted to 5' }
```

<aside class="note">运行 13，memos 被换行到第二行。第一个进程在打印 tick 2 之后、提交 `n: 3` 之前关闭了。第二个进程重跑 tick 2，发现 memo `printed-2`，于是跳过打印。</aside>
### 休眠

`runtime.sleep(until)` 一直等到 Harness 时钟到达 `until`。休眠不是持久的。关闭 Harness 会取消它，下一个进程从检查点重新开始该阶段。如果某个截止时间必须跨重启存活，就把它放进检查点，比如示例 24 的支付对它 `at` 字段的做法。详情

- 时钟就是 Harness 的 `now` 选项，默认 `Date.now`。长时间的休眠会被切成最多 2,147,483,647 ms 的计时器，
- 每个计时器结束后再次检查时钟。当运行被停止或调用方的 context 被取消时，休眠会 reject
- `src/harness/scheduler.ts`。
- 钩子与任务共用 memo 名字，所以要给自己的加前缀。像 `toString` 这样的名字永远不会解析到继承属性（spec
- §5.2；`test/harness-tasks.test.ts`）。
<aside class="note">每个阶段都要以改变检查点、开始一次等待或结束收尾。条目和文档不算进展。从 `runtime.commit()` 返回一个新状态。小决定用 memos，比如一个 ID 或选中的分支。批量进展放进文档（spec §12）。截止时间放进检查点，不要放进 sleep。</aside>
```
Sources: spec §5.1, §5.2, §12; src/harness/scheduler.ts; test/harness-tasks.test.ts (task phases, task runtime); ex 13, run 13; ex 24.
```

<img src="/pi-lessons/_assets/pi-durable/05-tasks/fig-5.3.png" alt="INTENT, EFFECT, OUTCOME
S E Q U E N C E" loading="lazy">

*先提交意图，再执行效果，最后提交结果；中途崩溃会重跑效果阶段。spec §5.1 的支付示例的各个阶段。第 4 步的条目和最终状态落在同一次提交里。*

<a id="sec-5-3"></a>

## 5.3 效果三明治

<p class="lede">提交你打算做的事，执行它，再提交实际发生的事；中途崩溃留下的是一个明确的问题，而不是一段无声的空白。</p>
Harness 能原子地提交自己的记录，但无法让一次扣卡、一次部署或一封邮件与它们原子。进程若恰好在扣款之后死掉，客户到底付了钱没有？读完本节，你就能把任何外部动作拆成若干阶段，使每个崩溃点都有明确而安全的恢复路径。

### 为什么效果需要自己的阶段

效果就是任何改变存储之外世界的东西：一笔支付、一次 API 调用、另一台机器上的一个文件。效果不得在提交内部运行（spec §1，不变式 4）。一次提交会占住 Session 的写入队列，在那里等待网络会拖住所有其他写者（提交（p. 29））。因此效果总是发生在两次提交之间，而进程可能死在它们中间。规范给出的答案是固定形状：

<aside class="note">提交意图 阶段 执行外部效果 提交结果或下一阶段 spec §5.2，原文。</aside>
<aside class="note">先提交意图，再执行效果，最后提交结果；中途崩溃会重跑效果阶段。spec §5.1 的支付示例的各个阶段。第 4 步的条目和最终状态落在同一次提交里。</aside>
规范自己的示例分三部分。`prepare` 创建一个幂等键，并把它作为下一个检查点提交。`charge` 用那个键执行效果，然后在同一次提交里追加一条回执条目并结束任务。中止处理器撤销这次扣款并提交 aborted。

<aside class="note">意图、效果、结果 docs/spec.md §5.1 TS // 意图、效果、结果。</aside>
```ts
prepare: async (task, runtime, context) => {
await runtime.commit(() => ({ status: "running",
checkpoint: { phase: "charge", key: newKey() } }), context);
},
```

```ts
charge: async (task, runtime, context) => {
const receipt = await payments.charge(task.state.checkpoint.key); // idempotent by key
await runtime.commit(async (tx, current) => {
const entry = await tx.appendEntry(current.conversationId, receiptEntry(receipt)); return { status: "terminal",
outcome: { status: "completed", result: { entryId: entry.id } } };
}, context);
}, // The abort handler decides the outcome; returning without one faults the task.
```

```ts
abort: async (task, runtime, context) => {
await payments.cancel(task.state.checkpoint); await runtime.commit(() => ({ status: "terminal",
outcome: { status: "aborted", reason: "user" } }), context);
}, Two long lines are wrapped; nothing else is changed.
```

### 每一个崩溃点，以及重开时会发现什么

新进程打开存储时，每一个当时在 running 的任务都会带着它的检查点退回 pending（调度器（p. 73））。是检查点而非进程说明任务当时处在什么位置：

<aside class="note">意图提交之前 检查点 prepare 再次 prepare；没有发出扣款 意图之后、扣款之前 检查点 charge 首次扣款 扣款之后、结果之前 检查点 charge 用同一个键再次扣款 结果提交之后 terminal 无</aside>
```
```

<aside class="note">中间两行对新进程来说没有区别。用规范的话说：「在意图阶段重开，意味着效果可能已经发生。」</aside>
Harness 无法知道在进程死掉之前请求有没有到达支付服务，所以你的阶段无论如何都必须正确。规范给出三种方式：「阶段处理器安全地重试、轮询一个外部句柄，或记录中断」（spec §5.2）。

安全地重试 —— 发送一个在意图阶段创建、并存在检查点里的幂等键。在恢复测试中，转账服务跨了一次关闭与重开被调用了两次，却只应用了一次转账，因为两次调用都带着 `transfer-N`（`test/harness-tasks-recovery.test.ts`）。轮询句柄 —— 当远端系统返回一个操作 ID 时，先把它提交下来再去等待，然后向远端系统询问结果。generation 任务对延迟的模型调用就是这么做的（generation（p. 91））。记录中断 —— 两者都做不到时，提交一个说明效果可能发生也可能没发生的 outcome。未被标记为可重放的工具调用，也就是 `"safe"` 的，就采用这个做法（工具调用与重放（p. 94））。

### 内置任务用的是同一个形状

Harness 自己的任务也遵循这个三明治，所以它们的恢复是可预测的。`pi.tool` 任务在运行工具之前刚好提交意图 `{ phase: "execute", arguments, replay }`。`replay` 来自该工具，默认是 `"unsafe"`（`src/harness/tool.ts`）。在正常运行中，同一个阶段接着运行工具并提交结果，所以 execute 阶段「只会在恢复时被到达」。在那里，只有当存储的策略和当前策略都说是 safe 时，它才重跑工具。否则它把这次调用提交为失败，并带上 `Tool NAME was interrupted and may have partially run`。`pi.generation` 任务则轮询。当供应商返回一个延迟句柄时，任务提交一个带该句柄和 `pollAt` 时间的轮询检查点。这个循环中任何地方崩溃，重开都会落在一个仍然指名远端操作的检查点上，而中止处理器可以用存下来的句柄取消它（`src/harness/generation.ts`）。

<aside class="note">Pi Durable 从不撤销外部效果。提交失败只回滚 Harness 自己的记录（提交失败时（p. 33））。撤销一次扣款是远端系统的事：它的幂等键、它的取消端点、它的操作句柄（限制与非目标（p. 168））。</aside>
<aside class="note">在意图阶段创建键。在效果阶段内部创建的键每次重跑都会变，去重就失效了。示例 12 从任务 ID 推导出它；商店抓取在序号 4 处、在任何扣款之前提交了 `"key": "charge-a"`。把结果和它的后果一起提交。一次 terminal 提交会原子地写入 outcome、追加 result 条目、退休该任务的文档，并结清它所回复的提交项（spec §5.3）。分两次提交会留下一个窗口：回执已经存在，任务却还活着。</aside>
<aside class="note">用一个 memo 守住同一阶段里的第二个效果。商店订单的 charge 阶段只在 memo `chargeId` 为空时才调用服务（序号 5，然后序号 6）。调用与 memo 之间崩溃仍会重复这次调用，所以调用本身必须容忍这一点。</aside>
```
Sources: spec §1 (invariant 4), §5.1 (payment example), §5.2, §5.3, §12; test/harness-tasks-recovery.test.ts (resumes an
intent/effect/outcome task interrupted after its intent); ex 12; research/capture/task-transitions.txt (scenario A, seq 4–6); src/harness/tool.ts; src/harness/generation.ts.
```

<img src="/pi-lessons/_assets/pi-durable/05-tasks/fig-5.4.png" alt="LOOKING UP A TASK’S CODE
D E C I S I O N" loading="lazy">

*调度器按 kind 查找任务的代码；没有代码能接手的任务会一直停在 pending，只有中止才会让它以 orphaned 结束。spec §5.4 的表格，实现在 `src/harness/scheduler.ts`。迁移过的记录与 running 一起提交。*

<a id="sec-5-4"></a>

## 5.4 调度器

<p class="lede">Harness 中有一部分决定下一个跑哪个任务，而且它绝不会仅仅因为代码缺失就结束一个任务。</p>
重启、升级和缺失的扩展都提出同一个问题：哪些任务现在可以运行，用哪份代码？调度器给出答案。读完本节，你就能说出重启的进程会怎么处理每个未完成的任务、为什么一个任务可以永远停在 pending，以及在任务运行时重新加载扩展会发生什么。

### 启动任务

调度器是 Harness 中负责启动任务的部分。每当有什么发生变化——某个任务被提交、某个扩展被安装、一次 `resume()` 调用——它就去找可以启动的任务。当没有东西在运行它、它不是 completing、它也没有在等待一个存活的任务时，任务就可以启动。对带中止标记的任务，「等待」指的是在等它自己的子工作，因为清理是自底向上运行的（`src/harness/scheduler.ts`）。

启动一个任务称为预留。在一次提交里，调度器按 kind 查找每个可启动任务的代码，把任务置为 running，并创建它的 invocation。等待中的任务直接进入 running。如果记录带有中止标记，invocation 就运行中止处理器而不是各个阶段（spec §5.4）。

<aside class="note">调度器按 kind 查找任务的代码；没有代码能接手的任务会一直停在 pending，只有中止才会让它以 orphaned 结束。spec §5.4 的表格，实现在 `src/harness/scheduler.ts`。迁移过的记录与 running 一起提交。</aside>
### 被阻塞的任务

当没有已注册的代码适配它时，任务就被阻塞。被阻塞的任务并没有失败。它的记录保持不变，它对空闲等待来说仍算未完成的工作，而注册表每次变化时调度器都会重试。阻塞是「推导出的运行时状态，不是被持久化的任务状态」（spec §5.4）。

<aside class="note">`missing_task` 没有注册任何同名代码 → 注册它。`task_too_old` 存储的版本比代码新 → 注册该版本或更新的代码。`migration_failed` 代码更新，但 migrate 缺失或抛出 → 注册一个不同的定义。出自 spec §5.4 与 `src/harness/scheduler.ts`。</aside>
在恢复测试中，一个缺失定义的任务会一直停在 pending，直到 `addTask()` 注册它，然后才完成（`test/harness-tasks-recovery.test.ts`）。用 `harness.inspect()` 找出被阻塞的任务。它为每个任务报告 `{ kind: "blocked", reason }`（任务图与 `inspect()`（p. 137））。迁移在任务被预留时运行。一个回调 `migrate(input, checkpoint, fromVersion)` 把记录从每个更旧的版本升级上来。如果它抛出，错误通过 `onReport` 报告一次，调度器要等到为该 kind 注册了一个不同的定义才会再试。一个没有 migrate 的更新定义会阻塞并报 `Task test.versioned version 2 has no migration from 1`（`test/harness-tasks-recovery.test.ts`）。

<aside class="note">「Harness 绝不会仅仅因为注册表代码缺失或不兼容就把一个任务置为 terminal，无论是在打开时还是之后」（spec §5.4）。只有中止才会结束一个被阻塞的任务，让它成为 orphaned（中止、故障与孤儿（p. 80））。</aside>
### 崩溃之后：重开

当你在已有存储上打开一个 Harness 时，调度器会做一次清理提交。每个留在 running 的任务都带着同样的检查点和 memos 退回 pending。此时还不会有什么运行：打开阶段「不分发任何东西」（`src/harness/scheduler.ts`）。处理器在 `resume()` 之后启动，或者在需要进展的调用之后启动，比如 `waitForTask()` 或 `submit()`（spec §2.2）。打开时还会安排第二次提交，应用崩溃留下的任何中止标记和最终结果。

<aside class="note">pending 打开后在 resume 之前什么也不启动；running → pending，保留检查点、memos 和标记，从检查点重跑；waiting 在它的 on 完成后恢复；completing 在它下方的工作完成后结束；terminal 永不再运行。出自 `src/harness/scheduler.ts` 与 spec §5.1、§5.5。`SIGKILL` 之后、打开之后的一个 `pi.tool` 任务 research/capture/crash-reopen-tasks.txt JSON // 被杀掉进程留下的 SQLite 行</aside>
```json
{ "id": 24, "kind": "pi.tool", "owner": 18, …
"state": { "status": "running",
"checkpoint": { "phase": "execute", "arguments": { "target": "weekly" },
"replay": "safe" } } }
// after Harness.open(), before resume(): only the status changed
"state": { "status": "pending", "checkpoint": { … unchanged … } }
// its owner, generation 18, stays "waiting" with "on": [24]
```

<aside class="note">进程在工具执行中途被杀掉。已省略（……）：`conversationId`、`version`、`input`、`background` 和 `abortRequested`，它们都没有被打开改变。</aside>
### 在运行中的任务下重新加载代码

一个运行中的 invocation 会一直用它启动时的代码。在每个阶段边界，step 都会重新检查注册表。如果现在为该 kind 注册了另一个定义并且它能接手这个任务（同一版本，或带 migrate 的更新版本），任务就交接。step 把它带着检查点、memos 和中止标记置回 pending，下一次预留就在新代码下运行它（spec §5.4）。交接测试会记录 `old:a start`、`old:a end`、`new:b start`，新旧代码从不重叠（`test/harness-tasks-recovery.test.ts`）。如果新代码接不了手，旧代码继续运行，问题被报告一次。「一个永不settle 的处理器永不交接。」「在运行时重新加载」（p. 118）在实践中展示了这一点。

### 关闭

`close()` 停止新工作，把待决的 `waitForTask()` 和空闲等待以 closed 错误拒绝，向每个 invocation 发信号，并等待它们返回。它不写 outcome，也不设标记，所以所有工作会在重开后恢复（spec §5.1）。忽略信号的处理器会让 `close()` 一直等着（spec §12）。详情

- 调度器在内存中保留每一条存活记录的副本，随每次提交落地而更新。每一轮都在一次提交里预留每个
- 可启动的任务。
- 如果存储拒绝这次预留提交，这些预留会在内存中撤销，错误交给 `onReport`，下一轮
- 再试。测试任务仍然恰好运行一次（`test/harness-tasks.test.ts`）。如果进程在那次提交期间死掉，
- 重开的任务仍停在 pending，什么也没运行（`test/harness-tasks-recovery.test.ts`）。
<aside class="note">崩溃之后，每个 running 的任务都从最后一个检查点重新开始。把每个阶段都写成可以再次运行的。永远停在 pending 的任务通常是被阻塞了。检查 `harness.inspect()`。当检查点的形状变化时，提高 `version`，并提供一个接受每个更旧版本的 `migrate`。让处理器尊重它们的 signal，这样 `close()` 和交接都很快。</aside>
```
Sources: spec §2.2, §5.1, §5.4, §12; src/harness/scheduler.ts; test/harness-tasks.test.ts (task scheduling); test/harness-tasks-recovery.test.ts (blocked tasks, definition handover, task crash recovery); research/capture/crash-reopen-tasks.txt.
```

<img src="/pi-lessons/_assets/pi-durable/05-tasks/fig-5.5.png" alt="THE OWNERSHIP TREE
T R E E" loading="lazy">

*任务与会话构成一棵所有权树，而后台任务会把它下方的子树切掉。README §Abort and Subagents 与示例 22 的前台子智能体，旁边是示例 23 的后台锚点。一个 generation 拥有它的工具任务（README §Concepts）。*

<a id="sec-5-5"></a>

## 5.5 所有权与结构化并发

<p class="lede">任务启动的工作归属于它：任务不会早于那些工作结束，而中止任务也会中止那些工作。</p>
一次结账发起了四笔卡支付。它不该在还有支付在途时报告 done；如果顾客取消，这些支付也应该被中止。所有权给了你两者。读完本节，你就能创建子任务、用正确的策略等待它们，并预测一个任务何时会一直挂在 completing。

### 一棵所有权树

每个任务都有一个 owner，在创建时设定，永不改变。你通过 `tx.createTask(task, input, { ownership })` 传入它（spec §5.5）：`{ kind: "conversation" }` —— 顶层任务，由它的会话拥有。`{ kind: "task", taskId }` —— 子任务，由另一个任务拥有，并且始终在那个任务的会话中。会话也可以有 owner。子智能体的会话由创建它的那个工具任务拥有（被拥有的会话（p. 43））。合起来，任务与会话构成一棵树。分叉在其中不起作用。

<aside class="note">任务与会话构成一棵所有权树，而后台任务会把它下方的子树切掉。README §Abort and Subagents 与示例 22 的前台子智能体，旁边是示例 23 的后台锚点。一个 generation 拥有它的工具任务（README §Concepts）。</aside>
创建子任务时 owner 必须存活：不是 completing、不是 terminal、没有中止标记。这个检查用的是提交完成后会留下的状态（`src/session/transaction.ts`）。所以任务不能在结束自己的那次提交里创建子任务。商店抓取的场景 D 正是这么试的。提交被拒绝，报 `Task owner 12 is completing`，该阶段抛出，任务在序号 27 处进入故障。在一次提交里创建子任务，在之后的一次提交里结束。

### 前台与后台工作

一个任务拥有的工作就是树中它下方的所有东西：它的子任务、它拥有的会话里的任务，如此往下。规范称之为普通的被拥有工作，它在后台任务处停下。后台任务是用 `background: true` 创建的、由会话拥有的任务。普通的等待和中止会跳过它「及其完整的被拥有子树」（spec §5.4）。空闲等待用同样的规则：`Conversation.waitForIdle()` 在会话下方不再有存活的前台任务时返回。

### 等待任务

一个阶段通过返回 `{ status: "waiting", checkpoint, on, policy }` 来等待。此时任务没有 invocation。当 `on` 中的每个任务都完成时，它从 `checkpoint` 恢复，并用 `runtime.outcomes(ids)` 按顺序读取它们的结果。示例 24 的结账在同一次提交里创建四笔支付并等待它们：

<aside class="note">在一次提交里创建子任务并等待 test/examples/24-child-tasks.ts TS</aside>
```ts
pay: async (task, runtime, taskContext) => {
await runtime.commit(async (tx) => {
const payments: TaskId<PaymentResult>[] = []; for (const card of task.input.cards) {
const ownership = { kind: "task", taskId: task.id } as const;
payments.push(await tx.createTask(Payment, { card }, { ownership })); }
return { status: "waiting", checkpoint: { phase: "decide", payments },
on: payments, policy: "failFast" }; }, taskContext);
}, The ownership literal is hoisted to fit the page. The decide phase reads runtime.outcomes(payments) and commits completed only if every payment completed.
```

`on` 的规则在等待被提交时检查，违反其中一条就会让任务进入故障（`src/harness/scheduler.ts`）：

- `on` 不能指一个缺失的任务、任务自身，或它自己的某个 owner，「因为那些永远不可能先完成」。
- `failFast` 只能指等待者拥有的任务。`allSettled` 可以指任何任务，甚至已经完成的。
- 空的 `on` 会在下一轮调度时恢复。
- 中止处理器完全不能等待。
allSettled 还是 failFast —— 策略决定一个任务失败时其他任务会怎样。用 `allSettled` 时什么也不会发生：最后一个任务结束时等待者就恢复，不管结果如何。用 `failFast` 时，「`on` 中第一个挂起或以非 completed 结果结束的任务，会在下一次对账提交中给 `on` 里其他每个存活任务打上中止标记」（spec §5.5）。等待者自身不会被中止。它恢复后自己决定结果。

<img src="/pi-lessons/_assets/pi-durable/05-tasks/fig-5.6.png" alt="FAILFAST ON A DECLINED CARD
T I M E L I N E" loading="lazy">

*一次失败的支付会在下一次提交中中止它还存活的兄弟任务；结账本身永远不会被标上中止标记。示例 24 的第一个场景，按提交记录在 research/capture/extra-p5/checkout-transitions.txt。每根条带是一个已提交的状态，一直持续到下一次提交改写它；terminal 记录永不被改写（斜线填充）。marked 表示带着中止标记的 running。*

从左往右读这张图。在序号 6，支付 9（`expired-2`）失败。在序号 7，一次提交给支付 8、10 和 11 打上中止标记，它们的中止处理器给这些卡退款。到序号 10，三者都已 aborted。在序号 11，结账在 `decide` 恢复，读到 `aborted`、`failed`、`aborted`、`aborted`，并在序号 12 提交 failed。

### completing：owner 等待它的工作

如果一个任务结束时它拥有的工作还在运行，它会被提交为 `{ status: "completing", outcome }`。结果已定，但任务还没完成。一旦它下方不再有存活的东西，调度器就提交最终的 terminal 记录（spec §5.5）。商店订单完整展示了这一点：

<aside class="note">13 7 order running 提交检查点 finish；在同一次提交里创建回执子任务 11；14 11 send-receipt running 已启动；15 7 order completing finish 提交 completed；子任务 11 仍存活；16 11 send-receipt terminal completed，"sent"；17 7 order terminal 调度器的最终提交；waitForTask(7) 兑现。场景 A，research/capture/task-transitions.txt。</aside>
被挂起的结果遵循五条规则（spec §5.5）：

- 它是最终的。不会再有阶段或中止处理器运行，任务也不会被重启或迁移。
- 中止一个 completing 的任务只会给它打标记，从而中止它下方的工作。最终记录保留被挂起的结果。
- completed 以外的挂起结果意味着取消意图，所以它下方的工作会先被中止。这样一个挂起的失败
- 还会在自己的工作排空之前触发 failFast（`test/harness-structured.test.ts`）。
- 写入在挂起处被分开。来自结束提交中的条目和文档会立即落地。terminal 状态、该任务文档的
- 退休，以及它的等待者，都要等到最终提交。
- 等待者、空闲等待和 `inspect()` 都把 completing 的任务视为存活。
<aside class="note">扩展在一个子智能体会话里启动的前台工作会挂住调用它的工具，进而挂住整个运行。在某个工具还在 completing 时再问子智能体更多问题，会延长这个挂起。应该不挂住自己 owner 的工作，就创建成会话拥有的后台任务（spec §12）。</aside>
<aside class="note">让一个任务成为其结果所依赖的任何工作的 owner。对全有或全无的子任务用 failFast，对你想要每个结果的情形用 allSettled。在一次提交里创建子任务，在之后的一次提交里结束。对不该挂住调用者的工作，用会话拥有的后台任务。</aside>
```
Sources: spec §5.4, §5.5, §12; README §Concepts, §Abort and Subagents, §Child Tasks; src/types.ts (TaskOwnership, TaskOptions,
```

<aside class="note">JoinPolicy）；src/session/transaction.ts；src/harness/scheduler.ts；test/harness-structured.test.ts；示例 22、23、24；运行 24；research/capture/task-transitions.txt；research/capture/extra-p5/checkout-transitions.txt。</aside>
<a id="sec-5-6"></a>

## 5.6 中止、故障与孤儿

<p class="lede">中止是一个会向下流遍整棵树的已提交标记；每个任务自己的处理器决定怎么清理，时机在它下方的一切都结束之后。</p>
中止已经触及外部世界的工作，需要的不只是停下来：一张已经扣过款的卡需要退款。Pi Durable 让每个任务自己决定如何清理，并按安全的顺序执行这些清理。读完本节，你就能写出正确补偿的中止处理器、从存储中读出一次中止，并从记录中看出是否有过任何清理。

### 中止如何工作

用 `harness.abortTask(id)` 中止一个任务。它不会当场停掉任务。它在记录上提交一个标志 `abortRequested`，称为中止标记。随后是五个步骤（spec §5.4）：1. 在任务上提交 `abortRequested`。2. 向运行中的 invocation（如果存在）发信号，并等待它返回。3. 一直等到该任务拥有的工作完成。4. 启动一个新的 invocation 运行中止处理器。5. 中止处理器提交一个最终 outcome。`abortTask()` 只做第 1、2 步并返回 `"marked"`。对一个已经完成的任务，它返回 `"terminal"`；对未知 ID 则 reject。它不等待清理；要看到最终结果请用 `waitForTask()`（spec §2.2）。如果你通过取消自己的 context 停止等待，标记已经提交，中止照常进行（`test/harness-tasks.test.ts`）。标记一旦提交，正在运行的阶段就不能再提交任何东西。每次 `runtime.commit()` 和 memo 写入都会 reject，报 `Task N has a durable abort mark`，而下一次 step 会结束这次运行（step 的规则 3（p. 67））。中止处理器稍后在一个新的 invocation 中运行。它仍然能看到记录里的 memos，并且只运行一次（`test/harness-tasks.test.ts`）。

中止处理器必须决定结果，通常是 aborted。不返回结果会让任务进入故障，报 `Abort handler of task N returned without a terminal outcome`；抛出则以抛出的消息让它进入故障。该处理器不能等待，也不能创建子任务，因为它自己的任务已被标记（`src/harness/scheduler.ts`；spec §5.5）。要补偿就就地行动，或者创建会话拥有的后台任务并用 `runtime.waitForTask()` 等待它们（spec §12）。

### 中止向下流，清理向上跑

中止会扩散到下方的工作。一个存活的任务在自己带有中止标记时，或自己挂着一个非 completed 的 completing 结果时，会把它传下去。规范把两者都称为取消意图，它会「幂等地级联到前台拥有的工作」（spec §5.4）。调度器在单独一次提交里提交子任务的标记，「并在打开时再来一次，这样中间的崩溃不会丢失任何东西」。示例 24 中被中止的结账用八次提交（序号 17 到 24）跑完了整个协议，见下图。顺序是有保证的。一个被标记任务的中止处理器在它拥有的工作存活期间无法启动，所以「中止处理器会看到它下方的最终结果」。在等待期间，`inspect()` 把结账显示为 `{ kind: "waiting", on: [child] }`。在三层测试中，每个处理器都记录下方的层级已经是 terminal（`test/harness-structured.test.ts`）。级联有若干限制（spec §5.4）：

- 它会停在自身没有取消意图的后台任务处。
- 已完成的 owner 绝不会把中止传下去。在一个已完成的子智能体会话里发起的新工作，比如用户追问它一句，
- 「照常运行」。
- 等待者在 `on` 中提到但不拥有的任务，既不会被标记也不会被等待。
- 级联到达的每个会话都按 `Conversation.abort()` 对待：它排队的输入变成无人回复，
- 原因为 aborted，排队的写入保留（提交项与收件箱（p. 84））。被中止任务自己的会话保留其
- 队列。
<img src="/pi-lessons/_assets/pi-durable/05-tasks/fig-5.7.png" alt="ABORTTASK ON A WAITING CHECKOUT
S E Q U E N C E" loading="lazy">

*中止标记在单独一次提交里向下流，中止处理器自叶向上运行。research/capture/extra-p5/checkout-transitions.txt 的场景 2；序号是抓取到的提交顺序。运行 24 会在 checkout aborted 之前打印出四笔退款。*

### orphaned、faulted、aborted

<aside class="note">`aborted` 任务自己的中止处理器做了补偿，在它能做到的范围内。`orphaned` 没有代码能接手该任务，「可能未经清理」。`faulted` 某个阶段抛出或没有进展，或者中止处理器没有提交结果。`unknown` 什么都没补偿。</aside>
```
```

<aside class="note">出自 spec §5.4。failed 不在这里：它是任务自己选择的一种结果，和 completed 一样。</aside>
orphaned —— 被阻塞的任务无法运行它的中止处理器，因为那份代码缺失或接不了这个任务。所以中止它会让它以 orphaned 结束，reason 就是被阻塞的原因。恢复测试在 `resume()` 之前中止一个缺失定义的任务，读到 `{ status: "orphaned", reason: "missing_task" }`，该任务的文档已被退休（`test/harness-tasks-recovery.test.ts`）。只有中止会让一个任务成为孤儿。仅仅代码缺失永远不会。faulted —— 故障来自任务 bug、格式不合的供应商数据，或一次被存储干净地拒绝的提交（`StorageRejected`）。不确定的存储失败会改为停掉 Session 且不写 outcome（提交失败时（p. 33））。如果存储连这条故障也拒绝，任务会保持 running，并在下一次预留时再次运行（`test/harness-tasks.test.ts`）。

### 中止过程中的崩溃

已提交的中止标记就是全部关键，所以每个崩溃点都能从它恢复（`test/harness-tasks-recovery.test.ts`）：

<aside class="note">标记正在提交时 没有标记；这次运行在标记之后恢复；运行返回之前 pending，带标记；只有中止处理器运行时 只运行中止处理器；中止处理器运行一次新的中止 invocation 时 再运行它；结果正在提交时 中止处理器再次运行；最终结果之后 什么都不运行；`abortTask()` 返回 `"terminal"`。任务崩溃恢复测试套件。中止处理器可能运行不止一次，所以它必须可安全重复，就像任何效果阶段一样（效果三明治（p. 70））。</aside>
细节：内置任务的清理 —— 对于 Harness 自己写入的两种结果 faulted 和 orphaned，它会在让该结果定下的那次提交里运行一个清理钩子（`src/harness/live.ts`；spec §5.4）。只有三种任务会用它：`pi.generation` —— 当它是当前运行的任务时，一条已提交的半截回复变成一条 aborted 的 `pi.assistant` 条目，该运行的输入变成无人回复，原因为 faulted 或被阻塞的原因，运行结束（运行控制（p. 88））。`pi.tool` —— 把这次工具调用标记为 done，但没有结果条目。运行继续，缺失的结果会在构建模型上下文时补上（context（p. 40））。`pi.compaction` —— 清掉压缩状态（压缩（p. 97））。

<aside class="note">写出可以安全运行两次的中止处理器。崩溃可能让它们再次运行。始终从中止处理器提交一个最终结果；不返回结果会让任务进入故障。就地补偿，或通过后台任务补偿。中止处理器不能创建子任务，也不能等待它们。把 orphaned 和 faulted 当作「什么都没清理」。自己去检查外部世界。</aside>
```
Sources: spec §2.2, §5.3, §5.4, §5.5, §12; src/harness/scheduler.ts; src/harness/live.ts (settleSchedulerOutcome); test/harness-tasks.test.ts (task abort); test/harness-tasks-recovery.test.ts; test/harness-structured.test.ts (abort order); test/harness-
ownership.test.ts; ex 24, run 24; research/capture/extra-p5/checkout-transitions.txt.
```
