---
title: "一页看懂架构"
---

<div class="section-kicker">PI DURABLE / 1.2 · P. 13</div>

# 一页看懂架构

---

<strong>Harness 以 Session 为内核，上层提供对话、commit请求和任务调度器，下层连接一个存储，其余一切都由宿主接入。</strong>



可以把这个软件包看作一个<strong>分层栈</strong>。<strong>你的程序请求 Harness 执行工作，Harness 将每个请求转化为commit，一个存储负责保存这些commit。</strong>本节介绍每一层的名称、各自拥有的状态，以及哪些内容仅存在于内存中、会在进程重启时重新构建。

## 四个层次



软件包由<strong>四层叠成</strong>。你的进程，也就是宿主，位于顶层并调用 Harness。Harness 将这些调用转化为一个 Session 上的commit。Session 将每次commit写入一个存储。扩展、模型和执行环境等代码虽然由harness运行，却不归它所有；宿主会在打开 Harness 时将这些代码传入。



<BookFigure id="D.1.2" :show-caption="false" />

> 宿主驱动 Harness，Harness 通过一个 Session commit，Session 写入一个存储。右栏是 `HarnessOptions`；Chord 是软件包依赖，不是选项。依据 `src/harness/harness.ts` 和 `src/session/session.ts` 绘制。
> 
> 



- <strong>Storage</strong>：<strong>存储记录和文档、并以原子方式commit一批写入的后端。</strong>软件包自带三种。见 `README §Storage`；第9部分介绍存储契约（原书第141页）。

- <strong>Session</strong>：内核。它“<strong>拥有一条变更串行队列、对话、条目、任务、commit请求和文档”</strong>。见 `spec §1`。变更串行队列一次执行一个commit。Session 还为每个已加载文档保留一个跟踪器，并向观察者发布每次commit。见 `src/session/session.ts`。你可以通过 `createSession()` 单独使用它；示例 00 至 05 就是这样做的。

- <strong>Harness</strong>：在 Session 内核上“扩展了对话句柄和注册表”。见 `src/harness/harness.ts`。它增加了你所调用的句柄、commit请求处理机制、任务调度器和视图。

## Harness 内部



四个组件承担 Harness 的工作，各自位于 `src/harness/` 下独立的文件中。

|<strong>组件</strong>|<strong>文件</strong>|<strong>拥有的内容</strong>|
|---|---|---|
|对话句柄|`harness.ts`|无：句柄只是一个 ID 加一组方法；“通过 ID 比较句柄”，见 `README §Concepts`|
|commit请求|`submissions.ts`、`inbox.ts`|输入与写入的接纳、每个对话的收件箱，以及 `wait()` 背后的等待者|
|任务调度器|`scheduler.ts`|每个活动任务的内存镜像；对任务进行预留、运行和中止|
|视图|`view.ts`、`task-graph.ts`、`events.ts`|`viewState()`、`watch()`、任务图和智能体事件|



harness通过三个内置任务回答输入。`pi.generation` 准备提示词并调用模型。`pi.tool` 执行一次工具调用。`pi.compaction` 总结较早的上下文。见 `spec §8`。它们“不是扩展，不能被移除或替换”。见 `src/harness/registry.ts`。因此，始终使用 `createRegistry()` 构建注册表；`Harness.open()` 会拒绝缺少它们的注册表。

## 宿主接入哪些内容



`Harness.open(storage, options, context)` 通过 `HarnessOptions` 接收其他所有内容。见 `spec §2.2`。

|<strong>选项</strong>|<strong>含义</strong>|<strong>详见</strong>|
|---|---|---|
|`models`|pi\-ai 的 `Models` 接口；生成过程调用 `models.streamSimple()`|生成（原书第91页）|
|`registry`|已安装的扩展：工具、提示词区段、钩子、包装器和任务|注册表（原书第103页）|
|`settings`|每次使用时读取、从不存储的运行策略|设置与默认值（原书第180页）|
|`env`|为每次工具调用和提示词渲染构建 `ExecutionEnv`|环境（原书第155页）|
|`conversationCreated`|在每次创建或分叉对话的commit中运行|访问与创建（原书第53页）|
|`now`、`onReport`|时钟，以及接收harness所报告的非致命错误的接口|—|



有两个依赖不属于选项：`@earendil-works/pi-ai` 提供消息类型和 faux 提供商，`@earendil-works/chord` 提供文档状态。见 `package.json`。每个异步调用都接收一个 Chord `Context`；取消它会取消等待，绝不会取消工作。见 `README §Quick Start`。

## 一次调用如何穿过各层



沿着 `root.submit(input, context)` 向下走过整个分层栈，就能看到各层如何分工：

1. Conversation 句柄把输入交给 Submissions 组件。见 `src/harness/submissions.ts`

2. Submissions 进行一次commit。它追加用户条目、记录commit请求、创建第一个生成任务，并在该对话的 `pi.live` 文档中将其标记为忙碌

3. Session 把这次commit写入存储，之后才通知监听者。见 `src/session/session.ts`

4. 调度器是这些监听者之一。它看到新任务后，会领取任务以便运行。领取本身是另一次commit。见 `src/harness/scheduler.ts`

5. 任务在任何commit之外运行。它通过 `models` 调用模型，凡是想保留的结果，都会作为新的commit写回



没有哪一层会绕过另一层；调度器只从已发布的commit中获知新工作。一次输入得到回答的全过程（原书第19页）将用真实记录串起这条链路。

## 内存与存储



内存与存储的分工是理解整个软件包的关键。存储保存事实，内存保存一个始终可据此重建的工作集：

- <strong>活动任务</strong>：调度器“镜像每一条已commit的非终态任务记录”。见 `src/harness/scheduler.ts`。打开时，它加载所有这些任务，并在一次commit中，将已终止进程遗留的所有 `running` 任务改回 `pending`

- <strong>已加载文档</strong>：已读取文档的缓存。见 `src/session/session.ts`

- <strong>等待者与观察订阅</strong>：`wait()` 背后的 Promise，以及视图背后的订阅；下一个进程会重新创建它们



如果进程终止，上述列表中的任何内容都无关紧要：打开时会全部读回。“重新打开存储，即可从工作停止的地方继续。”见 `README`。

## 入口



软件包公开十个导入路径。Node 专用代码位于以 `/node` 结尾的路径后；可移植的 SQLite 和 JSONL 核心也能在 Bun 或 Cloudflare Durable Objects 上运行。见 `README §Storage`。



|<strong>导入路径</strong>|<strong>提供的内容</strong>|
|---|---|
|`@earendil-works/pi-durable`|`Harness`、`createRegistry`、`defineExtension`、`defineTool`、`defineTask`、`defineDoc`、条目令牌、内置文档和任务、`MemoryStorage`、`createSession`|
|`.../storage/sqlite/node`、`.../storage/sqlite`|`openNodeSqliteStorage(file)`；基于异步数据库门面的可移植核心|
|`.../storage/jsonl/node`、`.../storage/jsonl`|`openNodeJsonlStorage(directory, context)`；基于 `FileSystem` 的可移植核心|
|`.../storage/memory`|独立的 `MemoryStorage`|
|`.../env`、`.../env/node`|`ExecutionEnv` 接口；`NodeExecutionEnv`|
|`.../tools`|`createReadTool()`、`createWriteTool()`、`createEditTool()`、`createBashTool()`，以及包含全部四者的 `CodingTools` 扩展|
|`.../testing`|`registerStorageConformance()`、`registerEnvConformance()`、存储基准测试|

> 依据 `package.json` 的 exports 映射。软件包要求 Node 22\.19\.0 或更高版本。
> 
> 



> <strong>这对你意味着什么：</strong>
> 
> - 你的代码与 Harness 及其对话句柄交互，不直接与存储交互
> 
> - 重启后仍然需要的任何内容，都必须放在commit中；内存只是缓存
> 
> - 句柄不保存状态。重启之后，使用 `harness.conversation(id, context)` 获取新句柄
> 
> 



> 来源：`package.json`（exports、dependencies、engines）；`README.md`（§Quick Start、§Concepts、§Storage）；`docs/spec.md §1, §2.2, §8`；`src/index.ts`；`src/harness/harness.ts`（`Harness.open`、`conversationCreated`）；`src/harness/registry.ts`（`BUILTIN_TASKS`）；`src/harness/scheduler.ts`（`TaskScheduler`、`open`）；`src/session/session.ts`（`SessionImpl`）；`test/examples/00-conversation.ts`
> 
>
