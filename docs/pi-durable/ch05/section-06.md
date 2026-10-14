---
title: "中止、故障与孤立"
---

<div class="section-kicker">PI DURABLE / 5.6 · P. 80</div>

# 中止、故障与孤立

---

> 中止是一个已提交的标记，会沿树向下传播；待下方所有工作都完成后，每个任务自己的处理函数再决定如何清理。
> 
> 

中止已经触及外部世界的工作，不只是让它停下来：已经扣款的银行卡需要退款。Pi Durable 让每个任务自己决定如何清理，并按安全顺序运行这些清理。本节结束后，你就能编写正确执行补偿的中止处理函数，读懂存储中的中止记录，并根据记录判断是否运行过任何清理。

## 中止如何工作



<strong>使用 `harness.abortTask(id)` 中止任务。它不会当场停止任务，而是在记录上提交一个名为 `abortRequested` 的标志，称为中止标记。随后发生五个步骤</strong>（spec §5\.4）：

1. 在任务上提交 `abortRequested`

2. 如果存在正在运行的调用实例，就向它发送信号，并等待它返回

3. 等待任务拥有的工作结束

4. 启动新的调用实例，运行中止处理函数

5. 中止处理函数提交最终结果



`abortTask()` 执行步骤 1 和 2，并返回 `"marked"`。对于已经结束的任务，它返回 `"terminal"`；对于未知 ID，则拒绝。它不会等待清理；请使用 `waitForTask()` 查看最终结果（spec §2\.2）。如果你取消自己的上下文，从而停止等待，标记已经提交，中止仍会继续（`test/harness-tasks.test.ts`）。



标记一经提交，正在运行的阶段就再也无法提交任何内容。所有 `runtime.commit()` 和memos写入都会以 `Task N has a durable abort mark` 拒绝，下一次步骤检查会结束本次运行（步骤规则 3，原书第67页）。中止处理函数稍后会在新调用实例中运行。它仍然能看到记录中的memos，并运行一次（`test/harness-tasks.test.ts`）。



中止处理函数必须决定结果，通常是 `aborted`。未提交结果就返回，会使任务以 `Abort handler of task N returned without a terminal outcome` 故障结束；抛出异常则会以异常消息故障结束。处理函数不能进入等待状态，也不能创建子任务，因为自己的任务已被标记（`src/harness/scheduler.ts`；spec §5\.5）。要执行补偿，可直接在处理函数内完成，或创建由对话拥有的后台任务，再用 `runtime.waitForTask()` 等待它们（spec §12）。

## 中止向下传播，清理向上执行



中止会传播给下方的工作。存活任务带有中止标记，或暂存一个非 `completed` 的 `completing` 结果时，都会向下传递。规范将这两种情况都称为取消意图，并说明它会“幂等地级联到所属的前台工作”（spec §5\.4）。调度器在另一次提交中写入子任务的标记，“并在打开时再次执行，因此即使中途崩溃，也不会丢失任何内容”。示例 24 中被中止的结账任务，通过八次提交执行完整协议，即 seq 17 到 24，如下图所示。



这一顺序有保证。只要所属工作仍存活，被标记任务的中止处理函数就不能启动，因此“中止处理函数看到的下方结果均为最终结果”。等待期间，`inspect()` 会将结账任务显示为 `{ kind: "waiting", on: [child] }`。三层测试中，每个处理函数都会记录：下一层已经是终态（`test/harness-structured.test.ts`）。



级联有以下限制（spec §5\.4）：

- 它会在本身没有取消意图的后台任务处停止

- 已完成的所有者绝不会继续传递中止。已完成子智能体的对话中新出现的工作，例如用户追加提问，“会正常运行”

- 等待方列在 `on` 中、但并不拥有的任务，既不会被标记，也不会被等待

    

级联触及的每个对话，都会按 `Conversation.abort()` 的方式处理：排队的输入变成未回答，原因为 `aborted`，排队的写入则保留（提交请求与收件箱，原书第84页）。被中止任务自己所在的对话会保留其队列。



<BookFigure id="D.5.7" :show-caption="false" />

> 中止标记在单独的提交中向下传播，中止处理函数从叶节点向上运行。来源为 `research/capture/extra-p5/checkout-transitions.txt` 的场景 2；seq 编号就是采集到的提交顺序。运行 24 先打印四次退款，再打印 `checkout aborted`。
> 
> 

## `orphaned`、`faulted`、`aborted`



|<strong>结果</strong>|<strong>运行过哪些任务代码</strong>|<strong>它启动的副作用</strong>|
|---|---|---|
|`aborted`|任务自己的中止处理函数|在处理函数能力范围内已完成补偿|
|`orphaned`|无：没有代码能够接手任务|“可能仍未清理”|
|`faulted`|抛出异常或未取得进展的阶段，或没有提交结果的中止处理函数|未知；未进行补偿|

> 来源：spec §5\.4。这里没有列出 `failed`，因为它与 `completed` 一样，是任务自己选择的结果。
> 
> 



- <strong>`orphaned`。被阻塞的任务无法运行中止处理函数，因为该代码缺失，或无法接手该任务。</strong>因此，中止它会使其以 `orphaned` 结束，`reason` 为阻塞原因。恢复测试在 `resume()` 之前中止一个缺少定义的任务，读到 `{ status: "orphaned", reason: "missing_task" }`，此时任务的文档已经退役（`test/harness-tasks-recovery.test.ts`）。只有中止会让任务孤立。单纯缺少代码绝不会。

- <strong>`faulted`。故障来自任务缺陷、格式错误的提供商数据，或存储明确拒绝的提交（`StorageRejected`）。</strong>不确定的存储失败则会停止 Session，不写入结果（提交失败时，原书第33页）。如果存储连故障结果本身也拒绝，任务会保持 `running`，并在下一次reservation时再次运行（`test/harness-tasks.test.ts`）。

## 中止期间的崩溃



唯一关键的是已经提交的中止标记，因此每个崩溃点都能据此恢复（`test/harness-tasks-recovery.test.ts`）：

|<strong>崩溃时机</strong>|<strong>重新打开之后</strong>|
|---|---|
|正在提交标记时|没有标记；恢复运行|
|标记之后、运行返回之前|带着标记进入 `pending`；只运行中止处理函数|
|中止处理函数运行期间|新的中止调用实例再次运行它|
|正在提交它的结果时|再次运行中止处理函数|
|最终结果之后|不运行任何内容；`abortTask()` 返回 `"terminal"`|

> 来源为任务崩溃恢复测试套件。中止处理函数可能运行不止一次，因此与任何副作用阶段一样，它必须可以安全重复（副作用三明治，原书第70页）。
> 
> 

## 细节：内置任务的清理



对于 Harness 自己写入的两种结果 `faulted` 和 `orphaned`，它会在使结果最终确定的提交中运行一个清理钩子（`src/harness/live.ts`；spec §5\.4）。只有三种任务使用它：

- `pi.generation`：如果它是当前运行的任务，已提交的部分响应会成为停止原因为 `aborted` 的 `pi.assistant` 条目；该运行的输入变为未回答，原因为 `faulted` 或阻塞原因；随后运行结束（运行控制，原书第88页）

- `pi.tool`：将工具调用标记为完成，但不写入结果条目。运行继续，构建模型上下文时再补上缺失结果（上下文，原书第40页）

- `pi.compaction`：清除压缩状态（压缩，原书第97页）



> <strong>这对你意味着什么：</strong>
> 
> - 编写可以安全运行两次的中止处理函数。崩溃可能让它们再次运行
> 
> - 始终从中止处理函数提交最终结果；没有结果就返回会让任务出现故障
> 
> - 直接执行补偿，或通过后台任务执行。中止处理函数不能创建子任务，也不能进入等待它们的状态
> 
> 

- 将 `orphaned` 和 `faulted` 视为“没有清理任何东西”。请自行核实外部世界的状态

    

> 来源：spec §2\.2、§5\.3、§5\.4、§5\.5、§12；`src/harness/scheduler.ts`；`src/harness/live.ts`（`settleSchedulerOutcome`）；`test/harness-tasks.test.ts`（任务中止）；`test/harness-tasks-recovery.test.ts`；`test/harness-structured.test.ts`（中止顺序）；`test/harnessownership.test.ts`；示例 24、运行 24；`research/capture/extra-p5/checkout-transitions.txt`。
> 
>
