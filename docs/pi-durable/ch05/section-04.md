---
title: "调度器"
---

<div class="section-kicker">PI DURABLE / 5.4 · P. 73</div>

# 调度器

---

> Harness 中有一个部分决定接下来运行哪个任务；它绝不会仅仅因为缺少代码就结束任务。
> 
> 

<strong>重启、升级和扩展缺失都会带来同一个问题：哪些任务现在可以运行，又该使用哪些代码？调度器负责回答。</strong>本节结束后，你就能说明重启后的进程如何处理每个未完成任务，为什么任务可能永远停留在 `pending`，以及在任务运行期间重新加载扩展会发生什么。

## 启动任务



<strong>调度器是 Harness 中负责启动任务的部分。每当发生变化，例如任务被提交、扩展被安装，或调用 `resume()`，它都会寻找可以启动的任务。</strong>当没有调用实例正在运行该任务、任务不处于 `completing`，并且没有等待某个存活任务时，它就可以启动。对于带中止标记的任务，“等待”指的是等待自己的子工作，因为清理从下往上进行（`src/harness/scheduler.ts`）。



<strong>启动任务称为 reservation。在一次提交中，调度器按 `kind` 查找每个可启动任务的代码，将任务设为 `running`，并创建其调用实例。等待中的任务直接进入 `running`。</strong>如果记录带有中止标记，调用实例会运行中止处理函数，而不是各个阶段（spec §5\.4）。



<BookFigure id="D.5.4" :show-caption="false" />

> 调度器按 `kind` 查找任务代码；没有代码能够接手的任务保持 `pending`，只有中止会让它以 `orphaned` 结束。这是 spec §5\.4 中的表，由 `src/harness/scheduler.ts` 实现。迁移后的记录会与 `running` 状态一并提交。
> 
> 

## 被阻塞的任务



当没有已注册代码适合某个任务时，该任务就被阻塞。阻塞的任务并未失败。其记录保持不变，在空闲等待中仍计作未完成工作，调度器会在注册表每次变化时重新尝试。阻塞是“推导出的运行时状态，而不是持久化的任务状态”（spec §5\.4）。



|<strong>原因</strong>|<strong>何时出现</strong>|<strong>如何解除阻塞</strong>|
|---|---|---|
|`missing_task`|没有注册该名称的代码|注册相应代码|
|`task_too_old`|存储版本比代码版本新|注册该版本或更新版本的代码|
|`migration_failed`|代码较新，但缺少 `migrate`，或迁移抛出异常|注册不同的定义|

> 来源：spec §5\.4 和 `src/harness/scheduler.ts`。
> 
> 



恢复测试中，缺少定义的任务会一直保持 `pending`，直到 `addTask()` 注册定义，随后才完成（`test/harness-tasks-recovery.test.ts`）。使用 `harness.inspect()` 查找被阻塞的任务。它会为每个此类任务报告 `{ kind: "blocked", reason }`（任务图与 `inspect()`，原书第137页）。



迁移在任务被reservation时运行。一个回调 `migrate(input, checkpoint, fromVersion)` 负责升级所有旧版本记录。如果它抛出异常，错误会通过 `onReport` 报告一次；只有该 `kind` 注册了不同定义之后，调度器才会再次尝试。较新定义若没有 `migrate`，会以 `Task test.versioned version 2 has no migration from 1` 阻塞（`test/harness-tasks-recovery.test.ts`）。



<aside class="manual-callout callout-rule durable-callout" role="note" data-source-page="74">

<strong>不会因代码缺失而结束</strong>

“Harness 绝不会仅因注册表代码缺失或不兼容就将任务终结，无论是在打开时还是之后”（spec §5\.4）。只有中止会让被阻塞的任务以 `orphaned` 结束（中止、故障与孤立，原书第80页）。

</aside>

## 崩溃之后：重新打开



在已有存储上打开 Harness 时，调度器会执行一次清理提交。所有遗留在 `running` 状态的任务，都会带着相同的检查点和memos回到 `pending`。此时还没有任何代码运行：打开过程“不会调度任何处理函数”（`src/harness/scheduler.ts`）。处理函数会在 `resume()` 之后启动，或在 `waitForTask()`、`submit()` 这类需要推进工作的调用之后启动（spec §2\.2）。打开过程还会安排第二次提交，应用崩溃留下的尚未处理完的中止标记和最终结果。



|<strong>崩溃时状态</strong>|<strong>打开时写入什么</strong>|<strong>随后如何处理</strong>|
|---|---|---|
|`pending`|无|在恢复后启动|
|`running`|`pending`；保留检查点、memos和标记|从检查点重新运行|
|`waiting`|无|`on` 中的任务结束后恢复|
|`completing`|无|下属工作结束后完成|
|`terminal`|无|永不再次运行|

> 来源：`src/harness/scheduler.ts` 和 spec §5\.1、§5\.5。
> 
> 



`SIGKILL` 之后以及打开之后的一个 `pi.tool` 任务；来源：`research/capture/crash-reopen-tasks.txt`

```json
// 被杀死进程留下的 SQLite 行
{ "id": 24, "kind": "pi.tool", "owner": 18, ...
    "state": { "status": "running",
        "checkpoint": { "phase": "execute", "arguments": { "target": "weekly" },
            "replay": "safe" } } }

// Harness.open() 之后、resume() 之前：只有状态发生了变化
    "state": { "status": "pending", "checkpoint": { ... unchanged ... } }

// 它的所有者，也就是生成任务 18，仍保持 "waiting"，且 "on": [24]
```

> 进程在工具执行中途被杀死。省略号（`…`）代表 `conversationId`、`version`、`input`、`background` 和 `abortRequested`，这些字段在打开时均不改变。
> 
> 

## 在任务运行期间重新加载代码



正在运行的调用实例会保留启动时使用的代码。在每个阶段边界，步骤检查会重新查看注册表。如果该 `kind` 现在注册了不同定义，并且新定义能够接手任务（相同版本，或带有 `migrate` 的更新版本），任务就会交接。步骤检查会将它设回 `pending`，保留检查点、memos和中止标记，下一次reservation便会使用新代码运行它（spec §5\.4）。交接测试记录了 `old:a start`、`old:a end`、`new:b start`，因此新旧代码绝不重叠执行（`test/harness-tasks-recovery.test.ts`）。如果新代码无法接手，旧代码会继续运行，并报告一次问题。“始终不结束的处理函数永远不会交接。”运行时重新加载（原书第118页）展示了这一机制的实际使用。

### 关闭



`close()` 会停止新工作，以 `closed` 错误拒绝尚未完成的 `waitForTask()` 和空闲等待，向每个调用实例发送信号，并等待它们返回。它不写入结果，也不设置标记，因此重新打开后所有工作都会恢复（spec §5\.1）。忽略信号的处理函数会让 `close()` 一直等待（spec §12）。

### 细节



调度器在内存中保留每条存活记录的副本，每次提交落地时都会更新。每轮检查都会在一次提交中reservation所有可启动任务。



如果存储拒绝reservation提交，内存中的reservation会被撤销，错误送往 `onReport`，下一轮再试。测试任务仍然恰好运行一次（`test/harness-tasks.test.ts`）。如果进程在该提交期间死亡，重新打开后的任务仍然是 `pending`，并且没有任何代码运行过（`test/harness-tasks-recovery.test.ts`）。



> <strong>这对你意味着什么：</strong>
> 
> - 崩溃之后，每个 `running` 任务都会从最后的检查点重启。编写每个阶段时，都要让它能够重复运行
> 
> - 永久停在 `pending` 的任务通常是被阻塞了。检查 `harness.inspect()`
> 
> - 检查点结构变化时，提高 `version`，并提供能接受所有旧版本的 `migrate`
> 
> - 让处理函数响应自己的 `signal`，使 `close()` 和交接能够快速完成
> 
>
