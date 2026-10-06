<img src="/pi-lessons/_assets/pi-durable/10-practice/fig-10.1.png" alt="THE CODING AGENT ASSEMBLED STRUCTURE" loading="lazy">

*代码与策略存在于进程之中；会话只存储它的选择。Harness 每次需要时才把两者组合起来。由 ex 26–29 与 `src/harness/agent.ts` 拼装。*

<a id="sec-10-1"></a>

## 10.1 构建一个编码智能体

<p class="lede">一个编码智能体就是一张注册表、一个设置对象和一个环境函数；用户按会话做出的一切选择，都是 `pi.agent` 里的一个名字。</p>
想象一个编码助手。用户把它切换到只读的 plan 模式，让它指向另一个文件夹，然后合上笔记本。明天它必须原样回来。只有每个选择都放在正确的位置，这才成立。示例 26 到 31 展示了各自的位置。读完本节，你就能把任何产品特性归入代码、策略或存储的选择，并说出一处变更何时生效。

<aside class="note">代码与策略存在于进程之中；会话只存储它的选择。Harness 每次需要时才把两者组合起来。由 ex 26–29 与 `src/harness/agent.ts` 拼装。</aside>
### 三个宿主输入，一个被存储的文档

你的宿主程序除 storage 和 models 之外，还给 `Harness.open()` 三样东西。它们都不被存储，改动其中任何一个都不会产生一次提交——提交是一次原子保存，其中的一切要么一起被存储，要么都不存。注册表——代码：按名字安装的扩展。安装第二个同名扩展会替换第一个（扩展与注册表（p. 103））。设置——每个会话共享的运行策略，比如重试次数和并行工具。Harness 每次需要时才读取它们。环境函数——`env(target)` 为一个会话构建工具所看到的文件系统和 shell。用户为某个会话选定的内容存储在该会话的 `pi.agent` 文档中：模型、思考级别、扩展名与工具名、指令以及工作目录（cwd）。它只存名字，从不存代码（每个会话的 agent（p. 106））。每一步之前，Harness 都在注册表里查这些名字，取得真正的工具与提示词片段。实时设置与可移动的文件夹 示例 26 是基础 agent。它安装 CodingTools（read、write、edit 和 bash 工具）以及一个小的提示词扩展。`CodingTools` 不会由框架替你安装 `src/tools/index.ts`。这些设置是围绕一个由用户编辑的对象的 getter，环境则跟随会话的 cwd。

<aside class="note">跟随文件的设置，跟随 cwd 的 env `test/examples/26-coding-agent.ts` TS</aside>
```ts
const userSettings = { parallelTools: true, maxRetries: 3 };
const settings: HarnessSettings = {
get toolExecution() {
return userSettings.parallelTools ? "parallel" : "sequential";
}, get retry() {
return { maxRetries: userSettings.maxRetries };
}, };
const env = ({ cwd = workspace }: { readonly cwd?: string }) =>
new NodeExecutionEnv({ cwd }); …
await root.configure({ cwd: join(workspace, "app") }, context);
userSettings.parallelTools = false;
```

<aside class="note">`Harness.open()` 调用和第一轮对话已省略（…）。第一次 `pwd` 打印 workspace，第二次打印 workspace/app（run 26）。两处变更都没有重启任何东西。</aside>
两处变更都从下一次使用开始生效。设置在每次决策时重新读取；缺失的字段取默认值 `src/harness/agent.ts` `resolveSettings`。cwd 的变更是一次对 `pi.agent` 的提交，下一次工具调用的 `env()` 就能看到它。一个后果是：环境按调用构建，因此崩溃后重跑的工具会运行在当时会话所处的目录里，那个目录可能并不是它第一次尝试所用的 `src/harness/tool.ts:253`。plan 模式是对 agent 的改动 示例 27 在不碰注册表的前提下让一个会话变成只读。plan 扩展带来一个 `submit_plan` 工具和一个 `plan_mode` 提示词片段。它把计划保存在自己的文档 `app.plan` 中，该文档是可回溯的，因此分叉会保留分叉点时的计划（定义文档（p. 50））。进入和退出 plan 模式是两次 `configure()` 调用。

<aside class="note">进入与退出 plan 模式 `test/examples/27-plan-mode.ts` TS</aside>
```ts
const enterPlanMode = { extensions: { add: [Plan] }, tools: [read, submitPlan] };
const leavePlanMode = { extensions: null, tools: null };
await root.configure(enterPlanMode, context);
const input = { type: "input", content: "Make the port configurable." } as const;
await (await root.submit(input, context)).wait(context); await root.configure(leavePlanMode, context);
```

<aside class="note">示例的第 60–62 行与第 93–98 行；为排进页面，提交项被提取到了 input 中。</aside>
<img src="/pi-lessons/_assets/pi-durable/10-practice/fig-10.2.png" alt="SAME REGISTRY , TWO BASH TOOLS FLOW" loading="lazy">

*选择顺序决定同名工具中谁胜出，包装器再装饰胜出的那个。两个会话共享同一张注册表。数值取自 ex 30 与 run 30；项目路径缩写为 `<project>`。*

<aside class="note">$ node --conditions=source --experimental-strip-types test/examples/27-plan-mode.ts</aside>
```
tools: [ 'read', 'write', 'edit', 'bash' ]
plan mode tools: [ 'read', 'submit_plan' ]
plan: [ 'Read PORT from the environment', 'Default to 3000' ]
tools again: [ 'read', 'write', 'edit', 'bash' ]
system: { sections: { plan_mode: '<plan_mode>\n…' },
added: [ 'read', 'submit_plan' ], … }
system: { sections: { plan_mode: null },
added: [ 'write', 'edit', 'bash' ], removed: [ 'submit_plan' ] }
```

<aside class="note">run 27，第一行 system 输出已缩短。模型把每次切换都看作一处小的 system 提示词变更，而不是一份新提示词（system 提示词（p. 115））。</aside>
三个细节让它跑通。`{ add: [Plan] }` 在宿主默认扩展之上追加，而 tools 数组恰好按那个顺序提供这些工具。把两者都设为 null 会丢弃覆盖，于是会话重新跟随宿主默认值。而 `submit_plan` 会交回控制权：`{ terminate: true }`——当一轮里每个工具结果都提出这个要求时，运行就结束，不再发起新的模型请求 README §Tools。评审者与沙箱：会话才是单位 示例 28 把一个评审者作为第二个会话加入，它有自己的 agent：更便宜的模型、只有 read 工具，以及以自己的 checkout 作为 cwd。它的评审者扩展有一个 `onYield` 钩子。只要某个回答里没有「No further findings.」，钩子就返回 `{ continue: … }`，这会追加一条 user 消息并让运行继续（钩子（p. 109））。这一切都存储在 `pi.agent` 中，因此重启之后评审者仍然是评审者。示例 29 给每个用户的会话一个自己的沙箱目录。一个 `app.sandbox` 文档保存该路径，在会话创建时写入。env 函数读取它并据此构建环境。该文档的 fork 策略是 `initial`，因此分叉开始时没有路径；env 随后返回 undefined，内置工具随即以「No execution environment is configured」失败 `src/tools/env.ts`。子智能体同样不继承这个文档：如果子任务应当共享沙箱规格，创建者必须自己写一个 spec §2.2。替换与装饰工具

<aside class="note">选择顺序决定同名工具中谁胜出，包装器再装饰胜出的那个。两个会话共享同一张注册表。数值取自 ex 30 与 run 30；项目路径缩写为 `<project>`。</aside>
示例 30 需要一个能激活 Python virtualenv 的 `bash`，但只在部分会话里需要。venv 扩展自带一个名为 `bash` 的工具。工具按选择顺序以名字收集，因此靠后扩展的 `bash` 会替换靠前的那个。包装器在那之后才应用 `src/harness/agent.ts` `resolveAgent`，所以计时包装器计时的正是胜出的那个 `bash`。包装器按名字引用工具，因此重新加载任一 `bash` 都会让它保持被包装。

### 变更何时生效

每种输入都有自己的时机。表格回答产品团队问的第一个问题：如果我现在改这个，谁会看到它？

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>a settings getter every use at the next decision; nothing is written</td><td></td><td></td></tr>
<tr><td>configure() model, tools, sections before each model request at the next request; the current one keeps its prompt</td><td></td><td></td></tr>
<tr><td>configure({ cwd }) env() at each use at the next tool call, even one the model already made</td><td>的 model、tools、sections｜每次模型请求之前｜下一次请求时生效；当前的请求保留自己的提示词。<code>configure({ cwd })</code>｜</td><td></td></tr>
<tr><td>installing or replacing an extension each phase start, request and call at the next phase; a running call finishes on the old code</td><td></td><td></td></tr>
<tr><td>a process restart after you reinstall stored names bind to the newly installed code</td><td></td><td></td></tr>
<tr><td>From spec §2.2, README §Per-Conversation Agent and §Reload, and run 31: a call running during a reload prints v1, the next prints v2, and a restarted process</td><td></td><td></td></tr>
</table>

<aside class="note">代码放注册表，共享策略放设置，按会话的选择放 `pi.agent`。会话需要跨重启记住的其他任何东西，都放进你自己的文档。重新打开之前先安装每个扩展；脱离代码的存储名字毫无用处。</aside>
<aside class="note">Sources: ex 26–31; run 26–31; src/harness/agent.ts (resolveSettings, resolveAgent, selectExtensions); src/harness/registry.ts; src/harness/tool.ts:253; src/tools/index.ts; src/tools/bash.ts; src/tools/env.ts; spec §2.2, §7.1; README §Tools, §Per-Conversation Agent, §Settings, §Environment, §Reload</aside>
<a id="sec-10-2"></a>

## 10.2 会咬人的契约

<p class="lede">Pi Durable 不会为自己的规则派出警察；违反其中一条不会有任何异常，直到负载、并发或崩溃让失败显形。</p>
假设某个扩展在一次提交里 await 一次网络调用。什么都不会抛。进程里其他每一次写入，包括 Harness 自己的写入，都安静地排在它后面。规范把 38 条这样的规则列为「API footguns」，并写道：「这些是契约，不是邀请你加入防御性机制」。本节按它们在哪里咬人分组，并给出症状与修法。把它当作扩展代码与宿主代码的评审清单。多数规则都源自两个事实。其一，一个进程里的所有写入都走同一条队列——变更线——一次一个提交。其二，其他代码只能看到已提交的状态（核心规则（p. 16））。占着队列太久、绕过 Harness 写入，或去改一个本该只读的值的代码，都会破坏其中一条。

### 事务与存储

把提交回调当作一次快速编辑。它可以是异步的，但其中每一个 await 都让队列保持阻塞，其他每一次提交都要等。

致命情形值得单独说一句。如果存储以某种方式失败，让人无法知道写入是否已落地，内存中的状态就可能与重新打开时读到的内容发生偏离。于是 Session 停止：它拒绝之后的每一次提交，必须重新打开，而重新打开读到的是存储实际持有的内容（提交失败时（p. 33））。`StorageRejected` 错误属于无害情形：存储在动手之前就拒绝了写入，提交回滚，Session 继续运行。

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>Keep commits short (2.2 (p. 29)) awaiting a model, tool, process, network call, person or another commit inside the callback stalls or deadlocks every write</td><td></td><td></td></tr>
<tr><td>No work left running after the callback (2.2 (p. 29))</td><td></td><td></td></tr>
<tr><td>await everything the callback starts</td><td></td><td></td></tr>
<tr><td>Read before you write (2.2 (p. 29)) reading a table after the first table write throws ReadAfterWrite read every row first; document drafts stay usable</td><td></td><td></td></tr>
<tr><td>Create documents explicitly (4.2 (p. 53))</td><td></td><td></td></tr>
<tr><td>Family seeds apply once (4.2 (p. 53))</td><td></td><td></td></tr>
<tr><td>Storage failures are fatal (2.3 (p. 33))</td><td></td><td></td></tr>
<tr><td>JSONL needs fsync to survive power loss (9.3 (p. 148))</td><td></td><td></td></tr>
</table>

### 运行、收件箱与进度

运行活跃期间，只有 Harness 可以向会话添加条目。图 10.3 说明了原因。每次模型请求之前，Harness 读记录（transcript）的末尾，判断模型需要哪些 system 提示词变更，然后把它们提交 `src/harness/generation.ts` `prepare`。你在其间添加的条目不属于那个计划，但那些变更会在它之后落地。write 提交项避开了这一点：它会等到一个边界——一轮工具调用之后的暂停点，或最终答案处。

<img src="/pi-lessons/_assets/pi-durable/10-practice/fig-10.3.png" alt="A RAW WRITE INTO A BUSY CONVERSATION SEQUENCE" loading="lazy">

*一个原始条目可能落在请求准备的读取与提交之间；write 提交项则改为等待一个边界。步骤 1–3 遵循*

<aside class="note">同一条 note，原始形式与作为提交项的形式 README §Busy Conversations TS // 当运行可能处于活跃状态时这样做不安全：条目会落在队列放它的位置。</aside>
```ts
await root.commit((tx) =>
tx.appendEntry(root.id, { kind: "app.note", data: "user opened a file" }), context);
// Safe: added at once when idle, otherwise at the next boundary. await root.submit(
{ type: "write", entry: { kind: "app.note", data: "user opened a file" } }, context);
```

<aside class="note">第二种形式就是 README 自己的示例。write 提交项绝不会启动一个模型轮次。</aside>
<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>Don’t write into a busy conversation (6.1 (p. 84))</td><td></td><td></td></tr>
<tr><td>Don’t move the head into the past by hand (3.4 (p. 46))</td><td></td><td></td></tr>
<tr><td>A failed run leaves its queue (6.1 (p. 84))</td><td></td><td></td></tr>
<tr><td>Progress is committed in steps (6.2 (p. 88))</td><td></td><td></td></tr>
<tr><td>Keep task results small (5.1 (p. 63))</td><td></td><td></td></tr>
<tr><td>The transcript is not the model’s context (3.2 (p. 40))</td><td></td><td></td></tr>
</table>

### 压缩

压缩用一段摘要替换旧轮次（压缩（p. 97））。摘要是在选定它那段条目范围之后过一段时间才写入的。这中间任何改变该范围的东西都有风险。

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>Compaction costs a model call</td><td></td><td></td></tr>
<tr><td>Edits during compaction</td><td></td><td></td></tr>
<tr><td>Summary timestamps a queued summary carries the time its compaction finished, not when it was placed judge freshness by entry order, as the Harness does</td><td></td><td></td></tr>
</table>

### 所有权、钩子与关闭

被拥有的工作构成一棵树。一个任务在它拥有的工作仍在运行时不能结束，而中止会在任何处理器运行之前先抵达子任务（所有权与结构化并发（p. 76））。有一条所有权规则很容易被违反，因为失败的提交看起来很合理：在结束自己的同一次提交里创建子任务的那个任务会故障。在 capture 中，一个订单任务扣款、打包，然后在结束的同时创建了一个 receipt 任务。

<aside class="note">在结束提交中创建的子任务 `research/capture/task-transitions.txt` TEXT</aside>
```
seq= 25 task 13 shop.pack owner=12 terminal outcome={"status":"completed",…}
seq= 26 task 12 shop.order owner=conv running checkpoint={"phase":"decide",…} seq= 27 task 12 shop.order owner=conv terminal outcome={"status":"faulted",
"error":{"message":"Task owner 12 is completing"}}
effects in order: ["charged charge-d"]
```

<aside class="note">场景 D，时间戳与 memo 已省略（…）。receipt 任务从未被存储，扣款也从未退回，因为故障不会运行任何中止处理器。在更早的一次提交里创建子任务；这样结束中的任务就以 completing 状态等待（spec §5.5）。</aside>
<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>Owned work holds its owner (5.5 (p. 76))</td><td></td><td></td></tr>
<tr><td>Work started by hooks (7.3 (p. 109)) it holds up the task that ran the hook; code reacting after the result cannot extend it</td><td></td><td></td></tr>
<tr><td>No children from abort handlers (5.6 (p. 80))</td><td></td><td></td></tr>
<tr><td>Hooks share memo names (7.3 (p. 109))</td><td></td><td></td></tr>
<tr><td>Count subagent spend once (6.6 (p. 100))</td><td></td><td></td></tr>
<tr><td>Honour abort signals (2.3 (p. 33)) code that ignores its signal keeps close() waiting and storage open</td><td></td><td></td></tr>
</table>

### 文档与观察者

文档 kind 与 fork 策略是一种存储格式：它们的寿命比定义它们的代码更长。你读到的值是共享的，不能修改；而观察者只能缓冲有限数量的更新（会话视图（p. 129））。

观察者规则对远程客户端尤其重要。一个镜像最新值的客户端，在更新被合并时仍然正确，因为替代值带着完整的最新内容。一个统计状态转移的客户端——比如「每次工具开始时通知」——则不然：负载之下它只看到终态，看不到中间的步骤。任何必须被计数的东西，都应该放进消费者会读取的条目或日志。

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>Store full copies sometimes (4.3 (p. 56)) if checkpointWhen() never returns true, storage grows without bound return true now and then</td><td></td><td></td></tr>
<tr><td>current, initial and asOf change what a fork sees choose by what the product means</td><td></td><td></td></tr>
<tr><td>Pick fork policies on purpose (4.1 (p. 50))</td><td></td><td></td></tr>
<tr><td>Kinds are permanent (4.3 (p. 56)) a migration cannot rename a kind; two definitions claiming one kind go unnoticed</td><td></td><td></td></tr>
<tr><td>pi. names are reserved (3.1 (p. 37)) nothing enforces it; reusing one collides with the Harness use your own prefix, such as app.</td><td>去计。响应中止信号（2.3（p. 33））｜忽略自己信号的代码会让</td><td></td></tr>
<tr><td>Read values are immutable (8.1 (p. 125)) changing a snapshot or watch value corrupts shared state copy before changing</td><td></td><td></td></tr>
<tr><td>Start watches after reading (8.2 (p. 129)) before start(), watch.value is the value at the time you acquired it initialize from it, then start</td><td></td><td></td></tr>
<tr><td>Watches can skip updates (8.2 (p. 129)) past 100 waiting updates, one full value replaces them; steps in between are lost</td><td></td><td></td></tr>
<tr><td>stop() does not wait (8.2 (p. 129)) it neither aborts nor waits for a callback in progress coordinate with your callback yourself</td><td></td><td></td></tr>
<tr><td>Close clients before the Harness (8.1 (p. 125))</td><td></td><td></td></tr>
</table>

### 扩展与 agent

一个扩展要么整体被选中，要么完全不被选中，因此守卫只在选中它的会话里运行。子会话在创建时复制一次它的选择（每个会话的 agent（p. 106））。

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>Include guards in every list an explicit extension list that leaves out a permissions extension runs without it</td><td></td><td></td></tr>
<tr><td>Edits replace copied lists { add, remove } on a child that copied a list starts from the host default instead</td><td></td><td></td></tr>
<tr><td>Copies happen once later changes to the parent never reach a task-owned child configure the child directly</td><td></td><td></td></tr>
<tr><td>a rerun after a crash builds its environment from the current cwd do not assume the first attempt’s directory</td><td></td><td></td></tr>
<tr><td>Reruns use today’s directory (9.5 (p. 155))</td><td></td><td></td></tr>
<tr><td>Default changes cost cache (7.5 (p. 115))</td><td></td><td></td></tr>
<tr><td>Keep prompt text stable (7.5 (p. 115))</td><td></td><td></td></tr>
<tr><td>Dispose late (7.6 (p. 118)) freeing resources at uninstall breaks calls still running dispose after running calls end</td><td></td><td></td></tr>
<tr><td>Almost none of this is checked at runtime. The registry only checks section keys and that tool names are unique within one extension</td><td></td><td></td></tr>
<tr><td>Does any await inside a commit callback leave the process?</td><td></td><td></td></tr>
<tr><td>Does any code write to a conversation whose run it does not own?</td><td></td><td></td></tr>
<tr><td>Does any consumer change a value it read, or depend on seeing every update?</td><td></td><td></td></tr>
</table>

```
Sources: spec §12, §6, §4; src/harness/generation.ts (prepare); src/harness/registry.ts (validateExtension); src/session/observation.ts (MAX_PENDING_WATCH_FRAMES); README §Busy Conversations; test/harness-inbox.test.ts; test/harness-view.test.ts; research/capture/task-transitions.txt and NOTES.md §6
```

<img src="/pi-lessons/_assets/pi-durable/10-practice/fig-10.4.png" alt="INSIDE AND OUTSIDE THE GUARANTEE COMPARISON" loading="lazy">

*Harness 保证的是它存储中已提交的东西；它周边的一切都归宿主所有。每一行都把一项保证与它留下的工作配在一起。出自 spec §2.2、§5.2、§11.3、§13、README §Storage 与 `src/harness/types.ts`。*

<a id="sec-10-3"></a>

## 10.3 边界与非目标

<p class="lede">Pi Durable 保证的是发生在一个进程、一个存储之内的事情；监管、身份、备份和远端恰好一次，都由宿主自己去建。</p>
Pi Durable 让已提交的内部状态在进程崩溃后依然存在。外部效果仍可能执行两次；这由工具重放策略和远端系统的保障措施决定。它不会重启你崩溃的进程，不会阻止两个进程打开同一个文件，也不知道你的用户是谁。本节划出这条界线。读完本节，你就能列出一个生产部署必须在 Harness 之外补上什么，并向一个 Pi 编码智能体用户解释会话迁到 Pi Durable 后有什么变化。

<aside class="note">Harness 保证的是它存储中已提交的东西；它周边的一切都归宿主所有。每一行都把一项保证与它留下的工作配在一起。出自 spec §2.2、§5.2、§11.3、§13、README §Storage 与 `src/harness/types.ts`。</aside>
### 规范排除在外的东西

规范以系统「最初没有」的十一件事收尾：这些是范围上的决定，不是需要绕开的缺口。表格把它们全部列出。其中两条塑造了日常代码：

- 没有「可见但未持久」的发布。UI 绝不显示存储并未持有的文本，所以流式输出只能和
- 进度提交一样平滑，默认间隔 100 ms（6.2（p. 88））。
- 没有强制终止。一个忽略自己中止信号的工具无法在进程内被停下；`close()` 会等它。把该次调用的 context 传给每一个 await。
<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>whole-Session DOM no single observable tree of everything; observe a conversation view, a document or the task graph (8.2 (p. 129))</td><td></td><td></td></tr>
<tr><td>visible-undurable publication no fast path for uncommitted progress; partials appear at commit cadence (6.2 (p. 88))</td><td></td><td></td></tr>
<tr><td>Session-kernel semantic event journal agent events are derived from commits, not stored (8.3 (p. 133))</td><td></td><td></td></tr>
<tr><td>session-scoped rewindable documents rewindable exists only for conversation scope (4.1 (p. 50))</td><td></td><td></td></tr>
<tr><td>automatic checkpoint heuristic a document stores a base only when checkpointWhen() says so (4.3 (p. 56))</td><td></td><td></td></tr>
<tr><td>CRDT/offline multi-writer merge one writer per storage; no merge of concurrent histories</td><td></td><td></td></tr>
<tr><td>SQL translation of Chord operations SQLite stores operations as records, not as SQL updates (9.2 (p. 144))</td><td></td><td></td></tr>
<tr><td>JSONL global compaction or repair main.jsonl only grows; corruption fails the open (9.3 (p. 148))</td><td></td><td></td></tr>
<tr><td>compatibility with removed Pico prototypes</td><td></td><td></td></tr>
<tr><td>forced termination of extension code a handler that ignores its signal cannot be killed in-process; close waits for it</td><td></td><td></td></tr>
</table>

### 一个存储，一个所有者

同一时刻只有一个进程可以使用一个存储。「一个存储在同一时刻属于一个进程；不存在跨进程锁」README §Storage。没有什么能阻止第二个进程打开同一个文件，于是每个进程都会以为自己才是唯一的写者。SQLite 选项 `busyTimeoutMs`（默认 5,000 ms）只是让 SQLite 等待文件锁 `src/storage/sqlite/node.ts`；它并不能让两个 Harness 在同一个文件上变得安全。所以崩溃恢复是你监管者的职责。必须有东西发现进程死了，启动一个新的，并重新打开存储。重新打开会做完剩下的事：正在运行的任务回到 `pending`，下一次 `resume()`、提交项或 `wait()` 会再次启动它们（调度器（p. 73））。同一次重新打开也处理计划中的交接：一旦 `close()` 兑现，「新的 Harness 可以打开同一个 Storage」spec §2.2。打开本身就是一次写入。`Harness.open()` 会提交对运行中任务的重置，即便之后没有任何东西恢复 `research/capture/crash-reopen-tasks.txt`，所以一个仪表盘绝不能「只是打开」另一个进程拥有的存储。对 SQLite 而言，一个独立的只读连接可以安全地读取运行中的数据库；capture kit 就是这样读取它运行中的行的 `research/capture/sqlite-rows-midrun.txt`。重新打开之前先安装每个扩展。代码缺失的任务不算失败；它会一直阻塞等待，直到注册表能运行它（5.4（p. 73））。

### 效果属于执行它们的系统

Harness 能提交「打算扣这张卡」的意图。它无法让这次扣款恰好发生一次。工具调用先提交意图，再执行，然后提交结果。如果进程死在这中间，「效果可能已经发生」spec §5.2（效果三明治（p. 70））。只有远端系统能了结这件事：靠一个它认得的幂等键，或者一个你可以去问的句柄。对于没有重放的工具：`safe` 根本不会被重跑；模型只会收到一个被中断的错误结果（工具调用与重放（p. 94））。没有任何东西会自动回滚。撤销一个效果是你自己写的代码，写在执行它的那个任务的中止处理器里。

### 原始 Pi session 与 Pi Durable

Pi Durable「并不取代 Pi 编码智能体。它是一个用来构建任何智能体应用的框架，编码智能体也包含在内」earendil.com/posts/pi-durable。编码智能体保留自己的 session 文件。表格为已经了解前者的读者比较这两种记录模型（Pi Durable 的用途（p. 10））。

两种设计共享记录方面的想法：只追加的条目、位置化的 system 增量、保留原始条目的摘要。不同之处在于一次写入意味着什么。Pi session 的一行记录某件事发生了。Pi Durable 的一次提交记录被允许看到的状态，包括尚未完成的工作。

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>Storage one JSONL file per session under ~/.pi/agent/sessions/ Memory, one SQLite file, or a JSONL directory with sidecars</td><td></td><td></td></tr>
<tr><td>History shape a tree in one file; the leaf is the current position conversations; a fork is a new conversation capped at parent.at</td><td></td><td></td></tr>
<tr><td>Branching /tree in place; /fork, /clone write new files fork(entryId) in the same storage, with document fork policies</td><td></td><td></td></tr>
<tr><td>Write unit one appended line per entry, file first written once a user or assistant message exists</td><td></td><td></td></tr>
<tr><td>System prompt system messages patching sections, toolsAdded/toolsRemoved pi.system entries with the same positional contract</td><td></td><td></td></tr>
<tr><td>Compaction compaction entry: summary, firstKeptEntryId, system checkpoint pi.compaction entry whose head is the first kept entry</td><td></td><td></td></tr>
<tr><td>Context edits context_edit entry with targetId and replacement edits on an entry: omit or replace</td><td></td><td></td></tr>
<tr><td>Model and thinking</td><td></td><td></td></tr>
<tr><td>Extension state custom entries with customType and data typed documents with scope, history and fork policy</td><td></td><td></td></tr>
<tr><td>Queued messages</td><td></td><td></td></tr>
<tr><td>Work in flight no entry type records a running response or tool call pi.generation and pi.tool tasks with checkpoints</td><td></td><td></td></tr>
</table>

### 需要你自己动手的部分

监管——在崩溃、重新部署和 OOM 时重启；保证每个存储只有一个进程，例如每个进程槽位或每个租户一个存储。身份与权限——API 里没有用户、账户或凭据类型。守卫是带 `beforeTool` 钩子的扩展，只在会话选中它们的范围内生效（钩子（p. 109））。备份——重新打开的 JSONL 存储会丢弃末尾写了一半的行，但「缺少必需的已确认数据就是损坏，打开会失败」spec §11.3。SQLite 可能在断电或宿主机故障时丢掉最新一次提交 README §Storage。没有任何东西会修复损坏的存储。API 变动——这个包还是实验性的：「API 可能在两个版本之间毫无预告地改变」README。1.0.3 版本已经破坏了自定义的 FileSystem 和 Shell 实现 CHANGELOG 1.0.3。锁定版本，并在升级后运行一致性测试套件（9.4（p. 152））。

```
Sources: spec §2.2, §5.2, §11.3, §13; README §Storage; CHANGELOG 1.0.3; research/capture/crash-reopen-tasks.txt; coding-agent docs/session-format.md, src/core/session-manager.ts; earendil.com/posts/pi-durable
```
