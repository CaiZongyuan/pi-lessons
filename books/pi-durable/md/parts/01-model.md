<a id="sec-1-1"></a>

## 1.1 Pi Durable 要解决什么

<p class="lede">智能体进程可能在任意一条指令处死去；Pi Durable 让每一个可见步骤都成为一次存储的提交，因此轮次中途的死亡只是一次暂停，而不是丢失。</p>
你的智能体正执行到部署工具的一半时，笔记本合上了盖子。进程回来时，它究竟完成了什么？Pi Durable 记录下中断之前它已经知道的内容。这个工具的重放策略决定是重新运行它，还是报告它可能只执行了一部分。本节说明没有它会出什么问题、它做的三个动作，以及它刻意不做的事。

### 问题：一个轮次有四类状态

智能体进程死于平常的原因：一次部署把它们替换掉，内核因为内存把它们杀掉，笔记本进入睡眠。轮次中途的死亡，会让四类状态都停在半途：

- 记录（transcript），即到目前为止的消息；
- 模型调用，即流式输出到一半的响应；
- 工具调用，即做了一半的效果；
- 应用状态，例如工具正在更新的待办列表。
它们各自待在不同的地方。崩溃之后它们彼此不一致，而且没有任何东西记录各自推进到了哪里。Earendil 的公告给出了目标：能在崩溃、重新部署和故障中存活，并恢复被中断的工作而不是从头重来的智能体 `earendil.com/posts/pi-durable`。

### 原版 Pi 保留了什么

Pi 编码智能体已经会持久化它的各个 Session。一个 Session 是 `~/.pi/agent/sessions/` 下的一个 `JSONL` 文件。每一行是一个带 `type` 的 JSON 对象；第一行是 Session 头，其余是通过 `id` 和 `parentId` 组成一棵树的条目 `coding-agent docs/session-format.md`。这棵树给了 Pi 原地分支的能力：`/tree` 可以移动到更早的条目，而不抹掉你离开的那条分支 `coding-agent docs/sessions.md`。各行随着智能体循环产出而追加。一条用户消息、一条带工具调用的助手消息、以及一条工具结果，各自都是一行消息 `session-format.md §Entry Types`。循环在供应商流式输出完成之后记录响应，然后逐个运行工具调用并记录结果 `coding-agent docs/how-pi-works.md §Agent loop`。这个设计保住了会话，但保不住轮次。如果进程在工具运行期间死去，文件就停在调用它的那条助手消息上。没有任何一行说明工具开始了，或者它打印了什么。流式输出到一半的响应不在文件里，扩展只存在内存中的状态也没了。下一个进程能把会话读回来，但无法判断工具的效果是否已经发生。

<img src="/pi-lessons/_assets/pi-durable/01-model/fig-1.1.png" alt="A CRASH IN THE MIDDLE OF A TOOL CALL
C O M P A R I S O N" loading="lazy">

*工具执行中途崩溃，会让原版 Pi 留下一个停在调用处的文件；Pi Durable 则重新打开一个被中断的任务。虚线左侧是崩溃之前已写入的内容*

### Pi Durable 的答案

Pi Durable 是一个 Harness：一处打开的存储，加上在其上运行智能体的机制。它做了三个动作，每个都补上前面某个缺口。所有可见的东西都要提交——「会话、模型轮次、工具调用和你自己的状态，在任何东西被展示之前都已提交到存储」`README`。流式输出到一半的答案和工具运行中的输出同样要提交，进度提交的默认最小间隔是 100 ms。崩溃只会丢失上一次成功提交之后的进展；存储延迟和输出节奏可能把这个间隔拉得更长 `README §Watching a Conversation`。工作就是带检查点的任务——一次模型调用和一次工具调用各自作为一个任务运行，也就是一个在每一步提交检查点的持久状态机。工具任务在 `execute()` 运行之前提交它的意图、最终参数和一条重放策略 `src/harness/tool.ts`。重新打开时，Harness 确切知道哪些调用已经开始。应用状态是同一次提交里的文档——文档是存在记录（transcript）旁边的带类型的 JSON。它与条目在同一次原子提交中改变，因此待办列表永远不会跑到修改它的那条消息前面 `README §Your Own State`。那次崩溃运行展示了结果。第二个进程重新打开了 `SQLite` 文件。仅是打开就把运行中的工具任务变回了 `pending`。在 `resume()` 时，`deploy` 工具没有被声明为可安全重跑，于是得到了一条 `pi.tool-result` 条目，里面是它已提交的那六行和一条错误：

<aside class="note">恢复时写入的工具结果，节选自 `research/capture/crash-after.txt` `JSON`</aside>
```json
{
"role": "toolResult",
"toolCallId": "deploy-1",
"toolName": "deploy", "content": [
{ "type": "text", "text": "deploy site: step 1/10 (pid 98319)\n…step 6/10 (pid 98319)\n" },
{ "type": "text",
"text": "<harness>\n[error] Tool deploy was interrupted and may have partially run\n</harness>" } ],
"isError": true,
"timestamp": 1791211977057 }
```

<aside class="note">条目 25 的模型消息。第一个文本块（此处截断）包含被杀死进程的全部六行输出。该条目的 `data.diagnostics` 带有同样的错误，`code` 为 `"interrupted"`。</aside>
随后模型读了这条结果并给出答案，输入结算为 `done`。在同一次崩溃中，声明了 `replay: "safe"` 的 `fetch_report` 工具在新进程里直接从第 1 步重新跑了一遍 `research/capture/crash-README.md`。下一个进程并没有猜。它读到的是一个写着「这个效果可能已经发生」的检查点，然后套用事先选定的策略。效果三明治（p. 70）与工具调用和重放（p. 94）会把它拆开讲。

### 它不是什么

作用域是刻意收窄的。有三条限制从一开始就很重要。每个存储只有一个进程——「一个存储在同一时刻只归一个进程所有；不存在跨进程锁」`README §Storage`。Harness 不是集群调度器。监督和重启进程是宿主的事。没有多写入方合并——规范把「`CRDT`／离线多写入方合并」列为非目标 `spec §13`。许多客户端可以观察并引导一个会话，但每一次写入都经过同一个 Harness。

不提供对世界的回滚——提交只在存储范围内是原子的。外部效果「不在 `Session` 的变更事务内运行」`spec §1`，不变式 4。当 Harness 无法知道一笔支付是否已经发生时，它会如实说明，并把答案交给幂等键或远端记录（边界与非目标（p. 168））。

<aside class="note">重新打开同一个存储，恢复未完成的工作。安全的工具可以再次运行；不安全的工具报告一个被中断的结果。逐个工具决定运行两次是否安全。这一个选择就决定了被截断的调用会怎样。把应用状态放在文档里，而不是内存里，这样它永远不会与记录（transcript）不一致。每个存储保持一个进程，让你的监督者去重启它。</aside>
```
Sources: README.md (intro, §Concepts, §Watching a Conversation, §Your Own State, §Storage); docs/spec.md §1, §13; src/harness/tool.ts
(ToolTask phases call, execute); research/capture/crash-README.md, crash-before.txt, crash-reopen-tasks.txt, crash-after.txt; research/pi/packages/coding-agent/docs/session-format.md, sessions.md, how-pi-works.md; earendil.com/posts/pi-durable (Earendil, October 2026)
```

<img src="/pi-lessons/_assets/pi-durable/01-model/fig-1.2.png" alt="THE LAYERS OF A HARNESS
L A Y E R S" loading="lazy">

*宿主驱动一个 Harness，Harness 通过一个 `Session` 提交，`Session` 写入一处存储。右列是 `HarnessOptions`；`Chord` 是一个包依赖，不是选项。依据 `src/harness/harness.ts` 与 `src/session/session.ts`。*

<a id="sec-1-2"></a>

## 1.2 一页讲完架构

<p class="lede">Harness 就是一个 `Session` 内核，上面加上面话、提交项和任务调度器，下面垫着一处存储，其余一切由</p>
<p class="lede">宿主插入。</p>
把这个包想象成一个栈。你的程序让 Harness 做事；Harness 把每个请求变成一次提交；一处存储保管这些提交。本节为每一层命名，说明每一层各自拥有哪些状态，并展示哪些东西只存在于内存中、在进程重启时被重建。

### 四层

这个包叠了四层。你的进程，也就是宿主，位于顶层并调用 Harness。Harness 把这些调用变成某个 `Session` 上的提交。`Session` 把每次提交写入一处存储。Harness 运行但不拥有的代码——例如扩展、模型和执行环境——由宿主在打开 Harness 时传入。

<aside class="note">宿主驱动一个 Harness，Harness 通过一个 `Session` 提交，`Session` 写入一处存储。右列是 `HarnessOptions`；`Chord` 是一个包依赖，不是选项。依据 `src/harness/harness.ts` 与 `src/session/session.ts`。</aside>
`Storage`——一个存储记录与文档、并把一批写入原子提交的后端。随包附带三种 `README §Storage`；第 9 部分讲存储契约（p. 141）。`Session`——内核。它「拥有一条变更线、会话、条目、任务、提交项和文档」`spec §1`。变更线是一个一次只跑一次提交的队列。`Session` 还为每个已加载文档维护一个追踪器，并把每次提交发布给它的观察者 `src/session/session.ts`。你可以通过 `createSession()` 单独使用它；示例 00 到 05 就是这么做的。`Harness`——被「扩展了会话句柄和注册表」的 `Session` 内核 `src/harness/harness.ts`。它加上你要调用的句柄、提交项机制、任务调度器和各种视图。

### Harness 内部

四个组件承担 Harness 的工作，每个都在 `src/harness/` 下的一个文件里。

```
harness.ts nothing: a handle is an id plus methods; “compare handles by id” README §Concepts
```

<aside class="note">会话句柄｜提交项 `submissions.ts`、`inbox.ts`：输入与写入的受理、每个会话各自的收件箱，以及 `wait()` 背后的等待者｜任务调度器 `scheduler.ts`：每个存活任务的内存镜像；预留、运行和中止它们｜视图 `view.ts`、`task-graph.ts`、`events.ts`：`viewState()`、`watch()`、任务图和智能体事件</aside>
Harness 用三个内置任务来回应输入。`pi.generation` 准备提示词并调用模型。`pi.tool` 运行一次工具调用。`pi.compaction` 概括旧上下文 `spec §8`。它们「不是扩展，不能被移除或替换」`src/harness/registry.ts`，所以永远用 `createRegistry()` 构建注册表；`Harness.open()` 会拒绝缺少它们的注册表。

### 宿主插入的东西

`Harness.open(storage, options, context)` 把其余一切都作为 `HarnessOptions` 接收 `spec §2.2`。

```
models the pi-ai Models interface; generation calls models.streamSimple() generation (p. 91)
registry the installed extensions: tools, prompt sections, hooks, wraps and tasks the registry (p. 103)
```

<aside class="note">`settings`：每次使用时读取、从不存储的运行策略｜设置与默认值（p. 180）｜`env`：为每次工具调用和提示词渲染构建 `ExecutionEnv`｜渲染环境（p. 155）｜`conversationCreated`：在每次创建或分叉会话的提交中运行｜访问与创建（p. 53）｜`now`、`onReport`：时钟，以及 Harness 报告但能挺过去的错误的去处——</aside>
有两个依赖不是选项：`@earendil-works/pi-ai` 提供消息类型和 faux 供应商，`@earendil-works/chord` 提供文档状态 `package.json`。每个异步调用都接受一个 `Chord Context`；取消它取消的是等待，而不是工作 `README §Quick Start`。

### 一次调用穿过各层

沿着 `root.submit(input, context)` 往下走，看各层如何分工。1. 会话句柄把输入交给提交项组件 `src/harness/submissions.ts`。2. 提交项组件发起一次提交。它追加用户条目、记录提交项、创建第一个生成任务，并在会话的 `pi.live` 文档中把它标记为忙碌。

3. `Session` 把那次提交写入存储，然后才通知它的监听者 `src/session/session.ts`。4. 调度器就是这些监听者之一。它看到新任务并认领它去运行。认领本身又是一次提交

- `src/harness/scheduler.ts`。
5. 任务在任何提交之外运行。它通过 `models` 调用模型，它想保留的每个结果都作为一次新的

- 提交写回去。
没有哪一层绕过另一层，调度器只从已发布的提交中得知新工作。一个被回应的输入的一生（p. 19）用真实记录走完这条链。

### 内存与存储

内存与存储的划分是整个包的关键。存储持有真相。内存持有的是一份始终从真相重建的工作集：存活的任务——调度器「镜像每个已提交的非终态任务记录」`src/harness/scheduler.ts`，打开时它把它们全部载入，并在一次提交中把任何被死掉进程留下的运行中任务变回 `pending`。已加载的文档——已读文档的一份缓存 `src/session/session.ts`。等待者与观察——`wait()` 背后的 promise 和视图背后的订阅；下一个进程会重新创建它们。如果进程死去，这份清单里的东西都无关紧要：打开会把它们全都读回来。「重新打开存储会从停下的地方接着做」`README`。

### 入口点

这个包暴露十条导入路径。依赖 Node 的代码位于以 `/node` 结尾的路径之后；可移植的 `SQLite` 与 `JSONL` 核心也能在 Bun 或 Cloudflare Durable Objects 上运行 `README §Storage`。

<aside class="note">`@earendil-works/pi-durable`：`Harness`、`createRegistry`、`defineExtension`、`defineTool`、`defineTask`、`defineDoc`、条目词元、内置文档与内置任务、`MemoryStorage`、`createSession`｜`…/storage/sqlite/node`、`…/storage/sqlite`</aside>
```ts
openNodeSqliteStorage(file); the portable core over an async database facade
…/storage/jsonl/node, …/storage/jsonl openNodeJsonlStorage(directory, context); the portable core over a FileSystem …/storage/memory MemoryStorage on its own …/env, …/env/node the ExecutionEnv interfaces; NodeExecutionEnv …/tools createReadTool(), createWriteTool(), createEditTool(), createBashTool(), and the CodingTools extension of all four …/testing registerStorageConformance(), registerEnvConformance(), storage benchmarks From the exports map of package.json. The package requires Node 22.19.0 or later.
```

<aside class="note">你的代码只与 Harness 及其会话句柄对话，从不直接接触存储。任何重启后还需要的东西，都必须存在于某次提交中；内存只是缓存。句柄不持有状态。重启之后，用 `harness.conversation(id, context)` 重新取一个。</aside>
```
Sources: package.json (exports, dependencies, engines); README.md (§Quick Start, §Concepts, §Storage); docs/spec.md §1, §2.2, §8; src/index.ts; src/harness/harness.ts (Harness.open, conversationCreated); src/harness/registry.ts (BUILTIN_TASKS); src/harness/scheduler.ts (TaskScheduler, open); src/session/session.ts (SessionImpl); test/examples/00-conversation.ts
```

<img src="/pi-lessons/_assets/pi-durable/01-model/fig-1.3.png" alt="THE COMMIT AS THE ONLY DOOR
F L O W" loading="lazy">

*每一个可见的改变，都要经过变更线上的同一次提交；效果只以提交的形式抵达观察者。阶段名称遵循 `spec §4`：变更线从回调一直持有到发布。*

<a id="sec-1-3"></a>

## 1.3 核心规则及其不变式

<p class="lede">一句话定义了这个系统：所有东西一起提交，不展示任何未提交的东西。八条不变式让这句话成立。</p>
整个设计只容纳一个想法：没有提交的东西就不算数。提交是一次原子保存：其中的一切要么一起存下，要么都不存。如果你的屏幕显示了出来，崩溃就收不回它。本节陈述这条规则，定义全书其余部分使用的术语，并解释让这条规则成立的八项保证。

### 规则

规范在给出任何类型之前，用两句话陈述了整个设计：

<aside class="note">「`Session` 原子地提交不可变条目、完整任务记录和由 `Chord` 跟踪的文档。只有已提交的状态是可观测的。」</aside>
第一句说明一次提交包含什么：记录、任务记录和文档变更，作为一个整体写入。第二句说明别的什么都看不见。屏幕、等待者、观察以及调度器本身，读的都是已提交的状态，而且不存在旁路 `spec`，前言。把它读成一扇门：每个改变都从提交通过，每个观察者都坐在门的另一侧。

```
Every visible change passes through one commit on the mutation line; effects reach observers only as commits. Stage names follow spec §4: the line is held from the callback through publication.
```

### 术语

规范在 §1 里一次性定义了它的名词。全书其余部分都严格按这个方式使用它们。`Session`——拥有一条变更线、会话、条目、任务、提交项和文档。`Conversation`（会话）——一个记录（transcript）作用域。它可以分叉出另一个会话。`Entry`（条目）——一条不可变的记录。`Task`（任务）——挂在某个会话上的持久状态机。`Document`（文档）——你的应用的 JSON 状态，随会话或任务一起保存。`Definition`——为文档命名并设定其初始值与存储规则的 TypeScript 声明。`Source`——文档更新保存后形成的只读流。`Turn`（轮次）——一次助手响应及其发起的工具调用。`Run`（运行）——从一个被受理的输入到最终答案之间的轮次序列。运行进行期间，会话就是忙碌的。

### 八条不变式

接着规范 §1 列出八条「必需的不变式」。每一条都堵住一种具体的失效。表格以短形式引用它们；下面的段落说明每一条换来了什么。

<aside class="note">1 一次提交在所有记录和文档写入上是原子的。｜被存下却没有任务的工具调用
2 文档更新只有在其存储提交成功后才发布。｜屏幕显示的状态被崩溃抹掉
3 所有可见进展都是持久的；不存在易失的发布路径。｜重开之后从未存在过的流式文本
4 外部效果不在变更事务内运行。｜一个慢调用拖住每一个会话
5 条目与 ID 不可变且永不复用。｜引用指向错误的记录
6 草稿在回调结算时被撤销；值是复制的严格 JSON。｜绕过提交的写入
7 变更线在结算与采纳期间保持持有；用户回调稍后在线外运行。｜建立在未采纳状态上的提交
8 不确定的存储失败对已打开的 `Session` 是致命的。｜内存与磁盘悄悄分叉</aside>
1 · 跨记录与文档的原子性 一次提交就是对 `Storage.commit(writes)` 的一次调用，它要么存下全部写入，要么一个都不存 `src/session/session.ts`。在单轮次的抓取中，提交 6 写入带工具调用的助手条目、把生成任务 9 移到 `waiting`、创建工具任务 12，并更新两个文档。若拆成两次写入，其间的崩溃会留下一个永远不会有任务来运行的工具调用。

2 与 3 · 先落存储，再发布，而且只有如此 `Session` 只有在 `Storage.commit()` 返回、并且新修订被采纳之后，才发布一次提交。不变式 3 排除了另一种可能：没有办法展示某个东西而不先提交它。因此部分答案和工具输出同样要提交，由 `settings.progress` 节流。这些提交每一次都是一次存储写入；这就是「屏幕绝不显示任何崩溃能收走的东西」的代价 `src/harness/generation.ts`（`streamResponse`）。
4 · 效果留在变更线之外「外部的模型、进程、工具、网络和人工效果都在它之外运行」`spec §4`。一个 Harness 的每个会话共享同一条变更线，所以在提交内等待一次模型调用，会阻塞其他所有提交直到它返回。更糟的是，这次提交的内容会依赖一个它无法撤销的效果。工具任务展示了这个模式：提交意图，在变更线之外运行 `execute()`，再提交结果（效果三明治（p. 70））。
5 · 条目不可变，id 永不复用 所有记录类型共享同一个 id 空间。在 `SQLite` 抓取中，会话 1、文档 2 到 6、条目 7、提交项 8 和任务 9 都来自同一个计数器 `research/capture/sqlite-rows.txt`（`record_ids`）。记录之间通过 id 相互指向：工具任务 12 的输入是 `{"assistant": 11, "callId": "call-1"}`，提交项 8 的答案是条目 15。如果 id 可以被复用、或者条目可以被改写，这些指针就会悄悄改变含义。即使一个 id 已被一次故障的提交占用，它也保持被占用 `research/capture/NOTES.md §6`。
6 · 草稿随回调一同消亡 在提交内部，`tx.doc()` 返回一个可变草稿。当回调结算时，`Session`「同步地准备或中止每一个打开的更改」，草稿随之被撤销。一个测试把草稿保留过它的提交，并检查此后读取或写入它会抛错 `test/session-documents.test.ts`，「revokes escaped drafts」。没有这条，一个游离的引用就可能在任何提交之外改动文档，从而破坏规则。
7 · 变更线覆盖存储与采纳 变更线一直保持持有，直到存储结算、并且新修订被采纳。因此下一次提交总是从上一次提交存下的状态开始。提交观察者在线上运行，但只是为了捕获不可变的值。你的 watch 和文档状态回调稍后在线外运行，因此一个缓慢的 UI 拖不住 Harness（提交与变更线（p. 29））。
8 · 不确定的失败会毒化 `Session` 一个可能已经写入了什么的存储错误，会让内存无法知道磁盘上是什么。此后 `Session` 会用「`Session` 已被存储接纳之后的一次失败提交毒化；请重新打开它」拒绝之后的每一次调用 `src/session/session.ts`。只有 `StorageRejected` 承诺没有写入任何东西，也只有它能让 `Session` 继续。准备阶段的失败，例如草稿里出现了非 JSON 值，发生在存储看到这批写入之前，会正常回滚（当提交失败时（p. 33））。

<aside class="note">对任何设计都问同一个问题：你展示或据以行动的状态是已提交的吗？如果不是，它就还不存在。在一次提交里改动相关的东西，这样崩溃永远无法把它们拆开。绝不在提交回调内部调用模型、工具或网络。如果存储以一种可能已经写入的方式失败，关闭并重新打开；不要重试。</aside>
```
Sources: docs/spec.md (preamble, §1, §4); src/session/session.ts (commit, poison check); src/errors.ts (StorageRejected); src/harness/generation.ts (streamResponse); src/harness/tool.ts (call phase); test/session-documents.test.ts (“revokes escaped
drafts”, “poisons the Session after an uncertain Storage failure”); research/capture/sqlite-rows.txt, sqlite-commits.txt, NOTES.md §6
```

<a id="sec-1-4"></a>

## 1.4 一个被回应的输入的一生

<p class="lede">一个问题、一次工具调用和一个答案要用掉十七次提交；按顺序读它们，就是在读整个 Harness。</p>
用户问「Count to 3.」，模型调用一个计数工具，然后给出答案。这次小小的往返用掉十七次提交。本节按顺序走过它们，于是你可以读任何提交日志，说出每一行是谁写的、为什么写，以及在那个位置崩溃会留下什么。

### 这次运行

`README` 的快速开始是最小的宿主。它在存储之上打开一个 Harness，取得根会话，提交一个输入，然后等待答案：

<aside class="note">快速开始，节选 `README.md §Quick Start` `TS`</aside>
```ts
const harness = await Harness.open(
new MemoryStorage(), { models, registry: createRegistry() }, context
); const root = await harness.root(context, {
agent: { model: { provider: "openai", modelId: "gpt-6-sol" } },
});
const submission = await root.submit(
{ type: "input", content: "What is the capital of France?" }, context);
const settled = await submission.wait(context);
// settled.answer is the id of the pi.assistant entry that answered await harness.close(context);
```

<aside class="note">导入语句、模型设置以及把答案读回来这几部分被略去。输入完成或没有得到回答之后，`wait()` 就会 resolve。</aside>
这次抓取在 `SQLite` 上跑同样的步骤，于是每次提交都可以作为行读回来 `research/capture/scripts/one-turn.ts`。faux 模型用 `{n: 3}` 调用计数工具，然后回答「I counted 1, 2, 3.」。工具用 `api.output()` 打印三行，并返回 `{}`。一个 `subscribeCommits()` 监听者记录每一次提交。两张图展示了这次运行。每个带编号的箭头就是一次提交，它的编号就是该提交在存储中的 `seq`。

### 提交 1–2：一个会话，然后一个输入

`root()` 在提交 1 中创建根会话。同一次提交还创建了它的五个内置文档，id 2 到 6：`pi.live`、`pi.inbox`、`pi.usage`、`pi.provider` 和 `pi.agent` `src/harness/harness.ts`（`conversationCreated`）。`agent` 文档存放模型选择，这里是 `faux`／`faux-1`。打开 Harness 时也运行了一次提交，用来对齐运行中的任务，但它没有写入任何东西。没有写入的提交会被丢弃，也不占用序列号 `src/session/session.ts`。`submit()` 是提交 2，它是让输入变得持久的那一次。此时会话空闲，于是受理在一次提交里做了三件事 `src/harness/submissions.ts`（`admitSubmission`）。它追加一条 `pi.user` 条目 7。它创建提交项 8，`status` 为 `placed`、`entry` 为 7。它启动一次运行：创建生成任务 9，并把 `pi.live.run` 设为 `{"taskId": 9, "inputs": [8]}`。从这一刻起会话就是忙碌的，因为「忙碌」的定义就是 `pi.live.run` 存在（运行控制（p. 88））。在这次提交之后崩溃，不会丢失用户输入的任何内容。用相同的 `requestId` 重新提交，会返回提交项 8，而不是新建一个。

<img src="/pi-lessons/_assets/pi-durable/01-model/fig-1.4.png" alt="ONE ANSWERED INPUT, COMMITS 1–8
S E Q U E N C E" loading="lazy">

*提交 1–8 把输入从 `submit()` 带到一次意图已经持久的工具调用。来自 `research/capture/sqlite-commits.txt`；文档操作来自 `research/capture/extra-p1/sqlite-commit-ops.txt`。*

### 提交 3–6：第一次生成

提交 3 是调度器在工作。它通过把任务 9 从 `pending` 改写为 `running` 来预留它，同时不改动它的检查点 `{phase: "prepare", attempt: 1}`（调度器（p. 73））。这次运行中的每个任务都以这样一次预留提交开始。`prepare` 阶段渲染系统提示词和工具列表，并把它们作为 `pi.system` 条目 10 提交，其中含前言小节和计数工具。同一次提交，也就是提交 4，把任务移到 `request` 阶段，带上模型、思考级别和条目 10 的截断点。`request` 阶段先提交 `pi.live.generation = {attempt: 1}`（提交 5），然后在变更线之外调用 `models.streamSimple()`。faux 流在 100 ms 的节流窗口内就结束了，因此没有提交任何部分。更慢的流会在此处加上经节流的部分提交（生成（p. 91））。响应以 `toolUse` 结束。提交 6 是这个轮次的转折点。它把响应写成 `pi.assistant` 条目 11，并把用量加进 `pi.usage`。它创建工具任务 12，归属于任务 9。它把这次调用列进 `pi.live.tools`。并把任务 9 移到在 `[12]` 上等待，策略为 `allSettled` `src/harness/generation.ts`（`startToolRound`）。在提交 6 之后崩溃，重开时会带着已记录的调用和处于 `pending` 的任务，于是工具会运行。在它之前崩溃，则重开时仍处于 `request` 阶段，模型调用干脆再做一次。

### 提交 7–8：先有意图，后有效果

提交 7 预留任务 12。它的 `call` 阶段接着从条目 11 读出这次调用，解析工具、校验参数，并运行所有 `beforeTool` 钩子。然后它提交自己的意图，也就是提交 8，之后才运行任何工具代码：

<aside class="note">提交 8 之后的工具任务 12 `research/capture/sqlite-rows-midrun.txt` `JSON`</aside>
```json
{
"id": 12,
"kind": "pi.tool", …
"input": { "assistant": 11, "callId": "call-1" },
"owner": 9,
… "state": {
"status": "running",
"checkpoint": {
"phase": "execute",
"arguments": { "n": 3 },
"replay": "unsafe" }
}
}
```

<aside class="note">这是 `tasks` 表的一行，在 `execute()` 运行期间从第二个连接读出；`conversationId`、`version` 和两个布尔标志被略去。`count` 没有声明重放，因此存下的策略是 `"unsafe"`。</aside>
这条记录正是工具执行中途的崩溃可以恢复的原因。`execute` 阶段只有通过恢复才会被独自走到。如果后来的进程发现某个任务处于这个阶段，工具可能已经运行过，而存下的重放策略决定是重新运行它，还是写入一条被中断的错误结果 `src/harness/tool.ts`。1.1 里的 `deploy` 发生的正是这件事（p. 10）。

### 提交 9–11：先是输出，然后是结果

工具的输出作为进展提交，默认最小间隔为 100 ms。提交 9 把 `pi.live.tools[0].output` 设为 `"1\n"`；提交 10 追加 `"2\n3\n"`。观察者看到输出在增长，而崩溃只会丢失上一次成功进展提交之后的输出。这个间隔没有固定的时间上限。当 `execute()` 返回时，提交 11 追加 `pi.tool-result` 条目 13，内容为 `"1\n2\n3\n"`，并把任务 12 变为终态，`outcome` 为 `{status: "completed", result: {entryId: 13}}`。

<img src="/pi-lessons/_assets/pi-durable/01-model/fig-1.5.png" alt="ONE ANSWERED INPUT, COMMITS 9–17
S E Q U E N C E" loading="lazy">

*提交 9–17 承载工具输出、结果、第二次生成以及答案。琥珀色的箭头是只涉及任务的提交：预留，以及在提示词没有变化时移到 `request`。*

```
```

<aside class="note">提交 9–17 承载工具输出、结果、第二次生成以及答案。琥珀色的箭头是只涉及任务的提交：预留，以及在提示词没有变化时移到 `request`。</aside>
### 提交 12–17：第二次生成与答案

任务 12 已是终态，所以任务 9 的等待结束。提交 12 在 `tools` 阶段预留它。这个阶段正是工具轮次期间排队的写入和引导消息会被安放的地方（收件箱（p. 84））。接着它把运行交接出去：提交 13 创建生成任务 14，把 `pi.live.run.taskId` 移到 14，清空工具轮次，并以 `result: {entryId: 11}` 让任务 9 以 `completed` 结束 `src/harness/generation.ts`（`finishToolRound`）。生成任务 14 重复第一次生成的各个阶段，只有一处不同。它的 `prepare` 阶段发现提示词和工具都没有变，因此不追加 `pi.system` 条目，提交 15 只把任务移到 `request`。系统条目是按位置发送的增量，只在有变化时才发（系统提示词（p. 115））。提交 16 在 `pi.live` 中标记这次尝试，模型以停止原因 `stop` 给出答案。提交 17 一次性结束所有事情。它把答案追加为 `pi.assistant` 条目 15，并把提交项 8 结算为 `done`、`answer` 为 15。它把任务 14 变为终态，删除 `pi.live.run` 和 `pi.live.generation`，于是会话重新空闲，并把第二个响应的 token 数加入 `pi.usage`。提交项组件在这次提交的发布中看到那条已结算的记录，于是 resolve 掉宿主的 `wait()`。

### 完整日志

<aside class="note">1 conversation 1 create　2–6　`root()`
2 entry 7 `pi.user`；submission 8 placed；task 9 pending　`pi.live`　`submit()`
3 task 9 running · prepare —— scheduler
4 entry 10 `pi.system`；task 9 · request —— generation 9
5 —— `pi.live`　generation 9
6 entry 11 `pi.assistant`；task 9 waiting；task 12 pending　`pi.live`、`pi.usage`　generation 9
7 task 12 running · call —— scheduler
8 task 12 · execute　`pi.live`　tool 12
9、10 —— `pi.live`　tool 12 progress
11 entry 13 `pi.tool-result`；task 12 terminal　`pi.live`　tool 12
12 task 9 running · tools —— scheduler
13 task 14 pending；task 9 terminal　`pi.live`　generation 9
14 task 14 running · prepare —— scheduler
15 task 14 · request —— generation 14
16 —— `pi.live`　generation 14
17 entry 15 `pi.assistant`；submission 8 done；task 14 terminal　`pi.live`、`pi.usage`　generation 14
以上每一行都出自 `research/capture/sqlite-commits.txt`；`JSONL` 那次运行是同样的十七条。</aside>
<aside class="note">从提交 2 起，用户的文本就是安全的；用相同的 `requestId` 重新提交，不会把它复制一份。工具的意图在任何工具代码运行之前就已被提交（提交 8），因此恢复时总能知道某次调用可能已经开始。没有哪次提交会让答案悬在提交项未结算的状态，也没有哪次提交会让工具调用没有任务。在任何一行之后杀掉进程，重开时它都知道下一步该做什么。</aside>
```
Sources: README.md (§Quick Start, §Concepts “One answered input”); research/capture/sqlite-commits.txt, sqlite-rows.txt, sqlite-rows-midrun.txt, jsonl-commits.txt, scripts/one-turn.ts, scripts/sqlite-one-turn.ts; research/capture/extra-p1/sqlite-commit-ops.txt (test/capture-p1-ops.ts); src/harness/harness.ts (root, conversationCreated); src/harness/submissions.ts (admitSubmission);
src/harness/generation.ts (prepare, request, startToolRound, finishToolRound, answer, startRun); src/harness/tool.ts (call, execute); src/harness/scheduler.ts (#reserve); src/session/session.ts (#runCommit)
```
