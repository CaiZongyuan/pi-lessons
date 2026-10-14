---
title: "任务图与 inspect()"
---

<div class="section-kicker">PI DURABLE / 8.4 · P. 137</div>

# 任务图与 inspect()

---

> 任务图展示每个存活任务的已提交状态；inspect\(\) 还会补充：在你当前的注册表下，调度器会如何处理每个任务。
> 
> 

当一次运行看起来卡住时，原因通常是某个任务正在等待对话记录中看不见的东西。两个只读工具可以展示这些任务。taskGraph\(\) 是用于任务面板的实时值。inspect\(\) 是一次性诊断，也会说明某个任务为何无法运行。读完本节，你就能从“什么都没发生”追踪到相应任务及其原因。

## 一个节点



整个任务图是一个值 \{ tasks \}，以任务 ID 为键。每个节点都是存储中的任务记录去掉载荷后的版本：没有 input、检查点 data、结果 data 或 memo。



图中一个正在等待的任务，来源：research/capture/extra\-p8/inspect\-vs\-graph\.txt：

```json
"8": {
    "id": 8,
    "kind": "app.join",
    "conversationId": 1,
    "background": false,
    "abortRequested": false,
    "state": { "status": "waiting", "phase": "done", "on": [7], "policy": "allSettled" },
    "conversations": []
}
```

> 没有 owner 键：这个任务由一段对话拥有。由另一个任务拥有的节点会携带 `"owner": <TaskId>`。abortRequested 在中止该任务的提交中变为 true。
> 
> 



|<strong>state\.status</strong>|<strong>其他字段</strong>|<strong>含义</strong>|
|---|---|---|
|pending|phase|已提交但尚未被调度器取走；也包括进程终止时正在运行、且尚未再次运行的所有任务|
|running|phase|已被当前进程中的调度器取走|
|waiting|phase, on, policy|已存储的等待，完全按提交时的状态呈现|
|completing|outcome|自身已完成，正在保留结果，直到它拥有的工作结束|

> 来源：src/harness/task\-graph\.ts；spec §9\.5。各状态的定义见“任务即状态机”（原书第63页）。
> 
> 

## 任务图如何变化



节点在创建其任务的提交中出现，在完成其任务的提交中消失。不改变任何节点的提交，例如 memo 写入，不会产生帧。任务图显示已提交的事实，因此阅读时要牢记三条规则；后面的图通过一个真实帧展示第一条规则。



on 是已存储的值——它列出该等待曾指明的每个任务，包括已经完成的任务。inspect\(\) 会告诉你哪些仍然存活。



running 指当前进程——重新打开 Harness 会把幸存的 running 任务改回 pending（调度器，原书第73页）。在它们再次被取走之前，显示的都是 pending。



只包含存活任务——后台子智能体的任务一旦完成，就不会再有节点列出它的对话。要在那段对话中放置后续任务，应使用该对话的 owner；对话视图也携带这个字段（子智能体，原书第121页）。



<BookFigure id="D.8.6" :show-caption="false" />

> 任务图就是存活任务的所有权树；已完成任务在结束它的那次提交中离开任务图。这里展示 research/capture/task\-graph\.txt 中场景 A 的第6帧和第7帧：一个 order 以 failFast 策略等待三个 pack，第一个完成的 pack 被删除，但 order 中已存储的 on 仍然指向它。对话框根据 conversationId 绘制；任务图本身只保存任务节点。
> 
> 



taskGraph\(\) 返回一个 Chord 状态；watchTaskGraph\(\) 返回一个遵守8\.2节（原书第129页）规则的监听。两者都不会启动调度，因此查看器可以附着到暂停中的 Harness，而不启动任何工作，见 spec §9\.5。

## inspect\(\)：调度器会做什么



harness\.inspect\(context\) 不写入任何内容，也不运行任何任务代码。它返回 scheduling（首次 resume\(\) 之前为 paused，之后可能是 running 或 closing）、每个存活任务的完整记录和派生状态，以及 queued 和 placed 状态的提交请求。



|<strong>state\.kind</strong>|<strong>条件</strong>|
|---|---|
|running|其代码正在当前进程中运行|
|completing|其结果被保留，直到它拥有的工作结束|
|waiting, on|它仍在等待的存活任务|
|blocked, reason|没有已安装的定义可以运行它：missing\_task、task\_too\_old 或 migration\_failed（带 error）|
|ready, migrates|下一轮调度会取走它；如果较新的定义会先迁移它，则带有 migrates|

> 来源：src/harness/scheduler\.ts。migration\_failed 只在调度器尝试过迁移之后出现；检查本身绝不会执行迁移。
> 
> 



<BookFigure id="D.8.7" :show-caption="false" />

> 任务图显示已提交的内容；inspect\(\) 补充在这个注册表下调度器会做什么。四个任务在同一次提交中创建，读取发生在 gate 运行期间。app\.legacy 由版本2的定义存储，但只安装了版本1；app\.retired 则未安装。来源：research/capture/extra\-p8/inspect\-vs\-graph\.txt。
> 
> 



任务图无法显示“blocked”，因为没有任何地方存储这个状态。阻塞任务的记录是普通的 pending 或 waiting 记录，它永远不会自行完成。安装可以运行它的定义，或中止它：在捕获中，abortTask\(\) 让两个阻塞任务立即以 orphaned 完成，并把阻塞原因作为结果的 reason。

## 从“什么都没发生”找到原因



当一段对话一直忙碌，或 waitForTask\(\) 始终不完成时，调用 inspect\(\)，并按以下顺序检查:

1. scheduling 为 paused。没有任何东西调用过 resume\(\)，也没有调用会启动它的方法，例如 submit\(\) 或 waitForIdle\(\)。只读查看器绝不会启动它。

2. 某个任务为 blocked。注册表中缺少其 kind，或只有更旧的版本。修正安装，或中止任务，使其以 orphaned 完成（调度器，原书第73页）。

3. 某个任务为 waiting。沿着它的 on 找到存活任务，并重复检查。被中止的任务会先等待它拥有的工作（中止、故障与孤儿任务，原书第80页）。

4. 某个任务为 completing。它自身的工作已完成，但它拥有的工作尚未完成；在任务图中找出它拥有的节点（所有权与结构化并发，原书第76页）。

5. 某个任务为 running。其代码正在执行。对于生成和工具，对话视图中的 pi\.live 会显示尝试、重试等待或工具输出（实时文档，原书第88页）。

    

queued 状态的提交请求在等待排在它前面的运行；placed 状态的提交请求属于一个尚未回答的运行（6\.1节，原书第84页）。已完成的任务不在 inspect\(\) 中；请通过 getTask\(\) 读取它们。
