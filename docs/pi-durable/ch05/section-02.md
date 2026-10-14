---
title: "阶段、步骤与进展"
---

<div class="section-kicker">PI DURABLE / 5.2 · P. 67</div>

# 阶段、步骤与进展

---

> 如果一个阶段没有提交任何新进展，它就会永远重复运行，因此 Harness 会改为以故障停止该任务。
> 
> 

<strong>任务一个阶段接着一个阶段运行。在阶段之间，Harness 会快速检查：任务是否已经结束、被中止或正在关闭，以及上一个阶段是否提交了进展。</strong>本节结束后，你就能预测这一检查对任意阶段会作出何种判断，设计始终能够取得进展的阶段，并安全地使用memos和休眠。

## 一次运行，多个阶段



Harness 启动任务时，会创建一次调用实例：任务在内存中的一次运行，拥有自己的中止信号。一个调用实例会连续执行各阶段，直到任务完成、开始等待或被停止。提交检查点不会结束调用实例。下一个阶段会立即在同一进程中开始。



每个阶段之前，Harness 都会执行一次步骤检查：读取已提交记录，并判断是否继续。这一步本身也是 Session 唯一写入队列上的一次提交（提交，原书第29页），因此它能看到阶段返回之前完成的每次提交。在这一步之后才进入队列的提交会被拒绝，错误为 `invocation has ended`（`test/harness-tasks.test.ts`）。



<BookFigure id="D.5.2" :show-caption="false" />

> 每个阶段之前，步骤检查应用第一条匹配的规则；没有进展就属于故障。规则来自 spec §5\.1，由 `src/harness/scheduler.ts` 实现。
> 
> 

## 六条规则



第一个阶段之前只应用规则 1–3，因为还没有任何阶段返回。阶段返回后，以第一条匹配的规则为准：

1. <strong>已结束、`completing` 或 `waiting`：停止。</strong>该阶段已提交结果或等待状态，没有更多内容可运行

2. <strong>Harness 正在关闭：停止。</strong>检查点及任何中止标记保留给下一个进程。关闭绝不写入结果

3. <strong>有中止标记：停止本次运行。</strong>等任务自己的子工作完成后，再启动单独的中止运行（中止，原书第80页）

4. <strong>阶段抛出异常：写入 `faulted`，并附上错误消息。</strong>与所有结果一样，只要任务的子工作仍然存活，它就暂存为 `completing`（所有权，原书第76页）

5. <strong>检查点改变：继续下一个阶段，或将任务交给新加载的代码</strong>（调度器，原书第73页）

6. <strong>检查点未变：写入 `faulted`，“因为没有取得持久化进展”；</strong>同样，只要子工作仍然存活，就暂存为 `completing`



在两种情况下，顺序尤其重要。一个阶段先提交新检查点再抛出异常，仍会变成故障，因为规则 4 在规则 5 之前。一个阶段先提交最终结果再抛出异常，则会保留结果，因为规则 1 最先应用。此后它尝试的任何提交都会被拒绝，错误为 `Task N is terminal`（`test/harness-tasks.test.ts`）。

## 为什么没有进展就是故障



如果阶段结束时，检查点与开始时一样，它就会用同样的输入一遍遍运行，永无止境。因此，步骤检查会将两个检查点作为 JSON 比较，忽略键的顺序。如果二者相等，就将任务标为故障，错误为 `Task test.idle phase run returned without durable progress`（`test/harness-tasks.test.ts`）。三种模式会触发这条规则：

- 阶段没有提交任何内容就返回

- 阶段提交了条目或文档，但没有从 `runtime.commit()` 返回新状态。只有检查点才算进展

- 阶段提交了一个与旧检查点相等的副本



只要检查点发生改变，一个阶段可以再次运行自身。示例 13 的计数器只有一个阶段 `tick`，每次都提交 `{ phase: "tick", n: n + 1 }`。阶段名称没有变，但检查点变了，因此规则 5 允许继续。

## Memos：记住一个小决定



<strong>Memos是存储在任务记录上的一个小型命名值。首次写入者胜出。</strong>`runtime.memo(name, candidate)` 只在该名称尚无值时提交候选值，无论是否写入，都会返回已存储的胜出值。`runtime.memo(name)` 只读取（spec §5\.2）。同时写入 `"a"` 和 `"b"` 时，两次调用都会得到 `"a"`（`test/harness-tasks.test.ts`）。<strong>Memos可以跨重启保留，并在任务结束时被丢弃。提交memos不算进展。</strong>



<strong>用memos避免一个阶段内的某个副作用重复执行。</strong>示例 13 即便同一阶段运行两次，也只打印每个 tick 一次：



Memos保护同一阶段内的副作用；来源：`test/examples/13-recovery.ts`

```js
tick: async (task, runtime, taskContext) => {
    const n = task.state.checkpoint.n;
    if ((await runtime.memo(`printed-${n}`, taskContext)) === undefined) {
        await runtime.memo(`printed-${n}`, true, taskContext);
        console.log(`tick ${n}`);
    }
    // ...提交 { phase: "tick", n: n + 1 }，或在 n 达到 task.input.to 后提交 terminal
    await runtime.sleep(Date.now() + 50, taskContext);
},
```

> 省略了检查点提交和一个仅用于测试的钩子。
> 
> 



```bash
$ node --conditions=source --experimental-strip-types test/examples/13-recovery.ts
tick 1
tick 2
closed; saved checkpoint: { status: 'pending', checkpoint: { phase: 'tick', n: 2 } }
memos: { 'printed-1': true, 'printed-2': true }
tick 3
tick 4
tick 5
after reopen: { status: 'completed', result: 'counted to 5' }
```

> 运行 13；`memos` 为了排版被换到了第二行。第一个进程打印 `tick 2` 后、提交 `n: 3` 前关闭。第二个进程重新运行 tick 2，找到memos `printed-2`，因此跳过打印。
> 
> 

## 休眠



`runtime.sleep(until)` 等待 Harness 时钟到达 `until`。休眠不是持久化的。关闭 Harness 会取消休眠，下一个进程会从检查点重新启动该阶段。如果截止时间必须跨重启保留，就将其放入检查点，正如示例 24 的支付任务使用 `at` 字段所做的那样。

### 细节



时钟由 Harness 的 `now` 选项提供，默认为 `Date.now`。较长的休眠会被拆分为每段最多 2,147,483,647 毫秒的定时器，每段结束后重新检查时钟。运行被停止或调用方的上下文被取消时，休眠会拒绝（`src/harness/scheduler.ts`）。



钩子与任务共享memos名称，因此要为自己的memos加上前缀。`toString` 这样的名称绝不会解析到继承属性（spec §5\.2；`test/harness-tasks.test.ts`）。



> <strong>这对你意味着什么：</strong>
> 
> - 每个阶段结束时，都要改变检查点、开始等待，或完成任务
> 
> - 条目和文档不算进展。请从 `runtime.commit()` 返回新状态
> 
> - 用memos记录小型决定，例如一个 ID 或选定的分支。大量进度信息应放入文档（spec §12）
> 
> - 将截止时间保存在检查点中，不要仅保存在休眠里
> 
> 



> 来源：spec §5\.1、§5\.2、§12；`src/harness/scheduler.ts`；`test/harness-tasks.test.ts`（任务阶段、任务运行时）；示例 13、运行 13；示例 24。
> 
>
