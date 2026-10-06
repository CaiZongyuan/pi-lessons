<img src="/pi-lessons/_assets/pi-durable/10-practice/fig-10.1.png" alt="THE CODING AGENT ASSEMBLED
S T R U C T U R E" loading="lazy">

*代码与策略存在于进程之中；会话只存储它的选择。Harness 每次需要时才把两者组合起来。由 ex 26–29 与 `src/harness/agent.ts` 拼装。*

<a id="sec-10-1"></a>

## 10.1 构建一个编码智能体

> 一个编码智能体就是一张注册表、一个设置对象和一个环境函数；用户按会话做出的一切选择，都是 `pi.agent` 里的一个名字。

想象一个编码助手。用户把它切换到只读的 plan 模式，让它指向另一个文件夹，然后合上笔记本。明天它必须原样回来。只有每个选择都放在正确的位置，这才成立。示例 26 到 31 展示了各自的位置。读完本节，你就能把任何产品特性归入代码、策略或存储的选择，并说出一处变更何时生效。

:::note
代码与策略存在于进程之中；会话只存储它的选择。Harness 每次需要时才把两者组合起来。由 ex 26–29 与 `src/harness/agent.ts` 拼装。
:::

### 三个宿主输入，一个被存储的文档

你的宿主程序除 storage 和 models 之外，还给 `Harness.open()` 三样东西。它们都不被存储，改动其中任何一个都不会产生一次提交——提交是一次原子保存，其中的一切要么一起被存储，要么都不存。注册表——代码：按名字安装的扩展。安装第二个同名扩展会替换第一个（扩展与注册表（p. 103））。设置——每个会话共享的运行策略，比如重试次数和并行工具。Harness 每次需要时才读取它们。环境函数——`env(target)` 为一个会话构建工具所看到的文件系统和 shell。用户为某个会话选定的内容存储在该会话的 `pi.agent` 文档中：模型、思考级别、扩展名与工具名、指令以及工作目录（cwd）。它只存名字，从不存代码（每个会话的 agent（p. 106））。每一步之前，Harness 都在注册表里查这些名字，取得真正的工具与提示词片段。实时设置与可移动的文件夹 示例 26 是基础 agent。它安装 CodingTools（read、write、edit 和 bash 工具）以及一个小的提示词扩展。`CodingTools` 不会由框架替你安装 `src/tools/index.ts`。这些设置是围绕一个由用户编辑的对象的 getter，环境则跟随会话的 cwd。

:::note
跟随文件的设置，跟随 cwd 的 env `test/examples/26-coding-agent.ts` TS
:::

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

:::note
`Harness.open()` 调用和第一轮对话已省略（…）。第一次 `pwd` 打印 workspace，第二次打印 workspace/app（run 26）。两处变更都没有重启任何东西。
:::

两处变更都从下一次使用开始生效。设置在每次决策时重新读取；缺失的字段取默认值 `src/harness/agent.ts` `resolveSettings`。cwd 的变更是一次对 `pi.agent` 的提交，下一次工具调用的 `env()` 就能看到它。一个后果是：环境按调用构建，因此崩溃后重跑的工具会运行在当时会话所处的目录里，那个目录可能并不是它第一次尝试所用的 `src/harness/tool.ts:253`。plan 模式是对 agent 的改动 示例 27 在不碰注册表的前提下让一个会话变成只读。plan 扩展带来一个 `submit_plan` 工具和一个 `plan_mode` 提示词片段。它把计划保存在自己的文档 `app.plan` 中，该文档是可回溯的，因此分叉会保留分叉点时的计划（定义文档（p. 50））。进入和退出 plan 模式是两次 `configure()` 调用。

:::note
进入与退出 plan 模式 `test/examples/27-plan-mode.ts` TS
:::

```ts
const read = createReadTool();
const enterPlanMode = { extensions: { add: [Plan] }, tools: [read, submitPlan] };
const leavePlanMode = { extensions: null, tools: null };
await root.configure(enterPlanMode, context);
const input = { type: "input", content: "Make the port configurable." } as const;
await (await root.submit(input, context)).wait(context); await root.configure(leavePlanMode, context);
```

:::note
示例的第 60–62 行与第 93–98 行；为排进页面，提交项被提取到了 input 中。
:::

<img src="/pi-lessons/_assets/pi-durable/10-practice/fig-10.2.png" alt="SAME REGISTRY, TWO BASH TOOLS
F L O W" loading="lazy">

*选择顺序决定同名工具中谁胜出，包装器再装饰胜出的那个。两个会话共享同一张注册表。数值取自 ex 30 与 run 30；项目路径缩写为 `<project>`。*

:::note
$ node --conditions=source --experimental-strip-types test/examples/27-plan-mode.ts
:::

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

:::note
run 27，第一行 system 输出已缩短。模型把每次切换都看作一处小的 system 提示词变更，而不是一份新提示词（system 提示词（p. 115））。
:::

三个细节让它跑通。`{ add: [Plan] }` 在宿主默认扩展之上追加，而 tools 数组恰好按那个顺序提供这些工具。把两者都设为 null 会丢弃覆盖，于是会话重新跟随宿主默认值。而 `submit_plan` 会交回控制权：`{ terminate: true }`——当一轮里每个工具结果都提出这个要求时，运行就结束，不再发起新的模型请求 README §Tools。评审者与沙箱：会话才是单位 示例 28 把一个评审者作为第二个会话加入，它有自己的 agent：更便宜的模型、只有 read 工具，以及以自己的 checkout 作为 cwd。它的评审者扩展有一个 `onYield` 钩子。只要某个回答里没有「No further findings.」，钩子就返回 `{ continue: … }`，这会追加一条 user 消息并让运行继续（钩子（p. 109））。这一切都存储在 `pi.agent` 中，因此重启之后评审者仍然是评审者。示例 29 给每个用户的会话一个自己的沙箱目录。一个 `app.sandbox` 文档保存该路径，在会话创建时写入。env 函数读取它并据此构建环境。该文档的 fork 策略是 `initial`，因此分叉开始时没有路径；env 随后返回 undefined，内置工具随即以「No execution environment is configured」失败 `src/tools/env.ts`。子智能体同样不继承这个文档：如果子任务应当共享沙箱规格，创建者必须自己写一个 spec §2.2。替换与装饰工具

:::note
选择顺序决定同名工具中谁胜出，包装器再装饰胜出的那个。两个会话共享同一张注册表。数值取自 ex 30 与 run 30；项目路径缩写为 `<project>`。
:::

示例 30 需要一个能激活 Python virtualenv 的 `bash`，但只在部分会话里需要。venv 扩展自带一个名为 `bash` 的工具。工具按选择顺序以名字收集，因此靠后扩展的 `bash` 会替换靠前的那个。包装器在那之后才应用 `src/harness/agent.ts` `resolveAgent`，所以计时包装器计时的正是胜出的那个 `bash`。包装器按名字引用工具，因此重新加载任一 `bash` 都会让它保持被包装。

### 变更何时生效

每种输入都有自己的时机。表格回答产品团队问的第一个问题：如果我现在改这个，谁会看到它？

:::note
设置 getter｜每次使用｜下一次决策时生效；不写入任何东西。`configure()` 的 model、tools、sections｜每次模型请求之前｜下一次请求时生效；当前的请求保留自己的提示词。`configure({ cwd })`｜`env()` 每次使用｜下一次工具调用时生效，哪怕是模型已经发出的那一个。安装或替换扩展｜每个阶段的开始、每次请求和每次调用｜下一阶段生效；正在运行的调用会用旧代码完成。进程重启｜在你重新安装之后｜存储的名字绑定到新安装的代码。
:::

```
```

:::note
出自 spec §2.2、README §Per-Conversation Agent 与 §Reload，以及 run 31：重载期间运行的一次调用打印 v1，下一次打印 v2，而重启后的进程
:::

:::note
在装上该扩展之前不提供任何工具（运行中重载（p. 118））。
:::

:::note
代码放注册表，共享策略放设置，按会话的选择放 `pi.agent`。会话需要跨重启记住的其他任何东西，都放进你自己的文档。重新打开之前先安装每个扩展；脱离代码的存储名字毫无用处。
:::

```
Sources: ex 26–31; run 26–31; src/harness/agent.ts (resolveSettings, resolveAgent, selectExtensions); src/harness/registry.ts;
src/harness/tool.ts:253; src/tools/index.ts; src/tools/bash.ts; src/tools/env.ts; spec §2.2, §7.1; README §Tools, §Per-Conversation Agent, §Settings, §Environment, §Reload
```

<a id="sec-10-2"></a>

## 10.2 会咬人的契约

> Pi Durable 不会为自己的规则派出警察；违反其中一条不会有任何异常，直到负载、并发或崩溃让失败显形。

假设某个扩展在一次提交里 await 一次网络调用。什么都不会抛。进程里其他每一次写入，包括 Harness 自己的写入，都安静地排在它后面。规范把 38 条这样的规则列为「API footguns」，并写道：「这些是契约，不是邀请你加入防御性机制」。本节按它们在哪里咬人分组，并给出症状与修法。把它当作扩展代码与宿主代码的评审清单。多数规则都源自两个事实。其一，一个进程里的所有写入都走同一条队列——变更线——一次一个提交。其二，其他代码只能看到已提交的状态（核心规则（p. 16））。占着队列太久、绕过 Harness 写入，或去改一个本该只读的值的代码，都会破坏其中一条。

### 事务与存储

把提交回调当作一次快速编辑。它可以是异步的，但其中每一个 await 都让队列保持阻塞，其他每一次提交都要等。

:::note
保持提交简短（2.2（p. 29））｜在回调里 await 模型、工具、进程、网络调用、人，或另一次提交，会让每一次写入停滞或死锁｜只使用交给你的那个 `Tx`；把慢活放在提交之间做。回调返回后不留运行中的工作（2.2（p. 29））｜回调一返回，它的草稿和 `Tx` 就会 reject；在此之前未 await 的工作不受支持｜await 回调启动的每一样东西。先读后写（2.2（p. 29））｜第一次写表之后再读该表会抛出 `ReadAfterWrite`｜先把每一行读完；文档草稿仍然可用。显式创建文档（4.2（p. 53））｜读取一个从未创建过的文档会返回 undefined｜用 `tx.doc()` 创建它。族种子只生效一次（4.2（p. 53））｜为已存在的族成员传入种子会被忽略｜改用草稿修改该成员。存储失败是致命的（2.3（p. 33））｜在写入可能已落地也可能没落地的失败之后，每一次后续提交都会抛错｜不要 catch 之后继续；重新打开。JSONL 需要 fsync 才能在断电后幸存（9.3（p. 148））｜机器宕机时一次已确认的提交可能丢失｜在关键处传入 `{ fsync: true }`。
:::

```
a confirmed commit may be lost if the machine goes down pass { fsync: true } where that matters
```

:::note
JSONL 需要 fsync 才能在断电后幸存（9.3（p. 148））
:::

致命情形值得单独说一句。如果存储以某种方式失败，让人无法知道写入是否已落地，内存中的状态就可能与重新打开时读到的内容发生偏离。于是 Session 停止：它拒绝之后的每一次提交，必须重新打开，而重新打开读到的是存储实际持有的内容（提交失败时（p. 33））。`StorageRejected` 错误属于无害情形：存储在动手之前就拒绝了写入，提交回滚，Session 继续运行。

### 运行、收件箱与进度

运行活跃期间，只有 Harness 可以向会话添加条目。图 10.3 说明了原因。每次模型请求之前，Harness 读记录（transcript）的末尾，判断模型需要哪些 system 提示词变更，然后把它们提交 `src/harness/generation.ts` `prepare`。你在其间添加的条目不属于那个计划，但那些变更会在它之后落地。write 提交项避开了这一点：它会等到一个边界——一轮工具调用之后的暂停点，或最终答案处。

<img src="/pi-lessons/_assets/pi-durable/10-practice/fig-10.3.png" alt="A RAW WRITE INTO A BUSY CONVERSATION
S E Q U E N C E" loading="lazy">

*一个原始条目可能落在请求准备的读取与提交之间；write 提交项则改为等待一个边界。步骤 1–3 遵循*

:::note
同一条 note，原始形式与作为提交项的形式 README §Busy Conversations TS // 当运行可能处于活跃状态时这样做不安全：条目会落在队列放它的位置。
:::

```ts
await root.commit((tx) =>
tx.appendEntry(root.id, { kind: "app.note", data: "user opened a file" }), context);
// Safe: added at once when idle, otherwise at the next boundary. await root.submit(
{ type: "write", entry: { kind: "app.note", data: "user opened a file" } }, context);
```

:::note
第二种形式就是 README 自己的示例。write 提交项绝不会启动一个模型轮次。
:::

:::note
不要向忙碌的会话写入（6.1（p. 84））｜原始条目可能落在运行的 system 提示词条目之间｜改用 write 提交项。不要手工把头指针移回过去（3.4（p. 46））｜模型的上下文变了，但已打开的视图会继续显示旧条目，直到被重建｜改用 write 提交项，它会以过期为由拒绝。失败的运行会留下它的队列（6.1（p. 84））｜排队的后续项留在 `pi.inbox` 里，它们的 `wait()` 永远不落定｜重新提交，或者撤回它们。进度按步提交（6.2（p. 88））｜崩溃会丢失上一次成功进度提交以来流式输出的文本；100 ms 是默认的最小间隔，不是最大丢失窗口｜调整 `settings.progress`；绝不显示未提交的文本。
:::

```ts
finished task records stay in storage, so big results stay too store the data in entries or documents; return their IDs
```

:::note
保持任务结果小（5.1（p. 63））｜已结束的任务记录留在存储里，大结果也一样｜把数据放进条目或文档；返回它们的 ID。记录不是模型的上下文（3.2（p. 40））｜原始条目会漏掉编辑、仅用于展示的条目和过滤｜用 `context()` 获取模型看到的内容
:::

### 压缩

压缩用一段摘要替换旧轮次（压缩（p. 97））。摘要是在选定它那段条目范围之后过一段时间才写入的。这中间任何改变该范围的东西都有风险。

:::note
压缩要花一次模型调用｜每一次尝试都要付一次摘要请求的代价，即使摘要来得太晚用不上｜为它做预算；它会显示在 `pi.usage` 里。压缩期间的编辑｜在写入摘要期间放入的编辑，若摘要覆盖了它的目标就会丢失；同时放入的头指针会被这次切断撤销｜在压缩之前做这类写入。摘要时间戳｜排队的摘要携带的是它那次压缩完成的时间，而不是它被放入的时间｜像 Harness 那样按条目顺序判断新鲜度
:::

### 所有权、钩子与关闭

被拥有的工作构成一棵树。一个任务在它拥有的工作仍在运行时不能结束，而中止会在任何处理器运行之前先抵达子任务（所有权与结构化并发（p. 76））。有一条所有权规则很容易被违反，因为失败的提交看起来很合理：在结束自己的同一次提交里创建子任务的那个任务会故障。在 capture 中，一个订单任务扣款、打包，然后在结束的同时创建了一个 receipt 任务。

:::note
在结束提交中创建的子任务 `research/capture/task-transitions.txt` TEXT
:::

```
seq= 25 task 13 shop.pack owner=12 terminal outcome={"status":"completed",…}
seq= 26 task 12 shop.order owner=conv running checkpoint={"phase":"decide",…} seq= 27 task 12 shop.order owner=conv terminal outcome={"status":"faulted",
"error":{"message":"Task owner 12 is completing"}}
effects in order: ["charged charge-d"]
```

:::note
场景 D，时间戳与 memo 已省略（…）。receipt 任务从未被存储，扣款也从未退回，因为故障不会运行任何中止处理器。在更早的一次提交里创建子任务；这样结束中的任务就以 completing 状态等待（spec §5.5）。
:::

:::note
被拥有的工作会拖住它的拥有者（5.5（p. 76））｜拥有者停留在 completing；子智能体的工作会拖住工具调用与运行｜把不该拖住任何东西的工作创建为 background。钩子启动的工作（7.3（p. 109））｜它会拖住运行该钩子的任务；在结果出来后才响应的代码无法延长它｜在任务记录结果之前创建它。中止处理器不得创建子任务（5.6（p. 80））｜一个正在中止的任务无法创建被拥有的子任务｜在效果发生的地方撤销，或用 background 任务撤销。钩子共用 memo 名字（7.3（p. 109））｜钩子与它的任务使用同一个 memo 命名空间，因此名字冲突｜给 memo 名字加前缀。子智能体开销只计一次（6.6（p. 100））｜一个上报子任务用量的工具会在总计中被计两次｜让子任务的 `pi.usage` 去计。响应中止信号（2.3（p. 33））｜忽略自己信号的代码会让 `close()` 一直等待、让存储一直打开｜把 `context.abortSignal` 传给每一个 await。
:::

### 文档与观察者

文档 kind 与 fork 策略是一种存储格式：它们的寿命比定义它们的代码更长。你读到的值是共享的，不能修改；而观察者只能缓冲有限数量的更新（会话视图（p. 129））。

```
```

:::note
有时存完整副本（4.3（p. 56））｜如果 `checkpointWhen()` 从不返回 true，存储就会无界增长｜时不时返回一次 true
:::

:::note
`current`、`initial` 和 `asOf` 决定分叉看到什么｜按产品语义来选。有意识地选择 fork 策略（4.1（p. 50））。kind 是永久的（4.3（p. 56））｜迁移无法给一个 kind 改名；两个定义都声称拥有同一个 kind 也不会被发现。
:::

```
to rename, copy to a new kind and retire the old
pi. names are reserved (3.1 (p. 37)) nothing enforces it; reusing one collides with the Harness use your own prefix, such as app. Read values are immutable (8.1 (p. 125)) changing a snapshot or watch value corrupts shared state copy before changing Start watches after reading (8.2 (p. 129)) before start(), watch.value is the value at the time you acquired it initialize from it, then start Watches can skip updates (8.2 (p. 129)) past 100 waiting updates, one full value replaces them; steps in between are lost count events from entries or a log stop() does not wait (8.2 (p. 129)) it neither aborts nor waits for a callback in progress coordinate with your callback yourself Close clients before the Harness (8.1 (p. 125)) a state ended by close keeps its last value forever detach clients and services first
```

观察者规则对远程客户端尤其重要。一个镜像最新值的客户端，在更新被合并时仍然正确，因为替代值带着完整的最新内容。一个统计状态转移的客户端——比如「每次工具开始时通知」——则不然：负载之下它只看到终态，看不到中间的步骤。任何必须被计数的东西，都应该放进消费者会读取的条目或日志。

### 扩展与 agent

一个扩展要么整体被选中，要么完全不被选中，因此守卫只在选中它的会话里运行。子会话在创建时复制一次它的选择（每个会话的 agent（p. 106））。

:::note
每一份列表都要包含守卫｜一份显式的扩展列表若漏掉某个权限扩展，运行时就少了它｜每一份列表都要包含守卫。改动会替换复制来的列表｜对复制过列表的子任务做 `{ add, remove }`，会从宿主默认值开始，而不是从复制品开始｜从解析后的 agent 构建完整列表。复制只发生一次｜之后对父级的改动永远到不了任务持有的子任务｜直接配置子任务。重跑使用当天的目录（9.5（p. 155））｜崩溃后的重跑会从当前 cwd 构建环境｜不要想当然地认为还是第一次尝试那个目录。默认值的改动要付出缓存代价（7.5（p. 115））｜改动设置或安装会新增 `pi.system` 条目并让提示词缓存失效｜预期每次改动带来一处 system 变更和一次缓存未命中。保持提示词文本稳定（7.5（p. 115））｜一个嵌入了时间的片段每次请求都会变化，从而破坏缓存｜只渲染真实的变化。延后 dispose（7.6（p. 118））｜在卸载时释放资源会打断仍在运行的调用｜在运行的调用结束之后再 dispose。表格各行在每组内部按 spec §12 的顺序转述；spec 给出修法时，「改用」一列就是它自己的修法。
:::

:::note
这其中几乎没有任何一项在运行时被检查。注册表只检查片段键，以及工具名在同一个扩展内是否唯一 `src/harness/registry.ts`。保留名、kind 冲突和不可变性都靠你的测试与评审。
:::

:::note
代码评审时，三个问题能抓到其中大多数。任何一个答「是」都是 bug——即使所有测试都通过，因为它只在负载、并发或崩溃下才显现。
:::

:::note
提交回调里有没有哪个 await 会离开进程？有没有哪段代码在写入一个它并不拥有其运行的会话？有没有哪个消费者改动了它读到的值，或依赖看到每一次更新？
:::

```
Sources: spec §12, §6, §4; src/harness/generation.ts (prepare); src/harness/registry.ts (validateExtension); src/session/observation.ts (MAX_PENDING_WATCH_FRAMES); README §Busy Conversations; test/harness-inbox.test.ts; test/harness-view.test.ts; research/capture/task-transitions.txt and NOTES.md §6
```

<img src="/pi-lessons/_assets/pi-durable/10-practice/fig-10.4.png" alt="INSIDE AND OUTSIDE THE GUARANTEE
C O M P A R I S O N" loading="lazy">

*Harness 保证的是它存储中已提交的东西；它周边的一切都归宿主所有。每一行都把一项保证与它留下的工作配在一起。出自 spec §2.2、§5.2、§11.3、§13、README §Storage 与 `src/harness/types.ts`。*

<a id="sec-10-3"></a>

## 10.3 边界与非目标

> Pi Durable 保证的是发生在一个进程、一个存储之内的事情；监管、身份、备份和远端恰好一次，都由宿主自己去建。

Pi Durable 让已提交的内部状态在进程崩溃后依然存在。外部效果仍可能执行两次；这由工具重放策略和远端系统的保障措施决定。它不会重启你崩溃的进程，不会阻止两个进程打开同一个文件，也不知道你的用户是谁。本节划出这条界线。读完本节，你就能列出一个生产部署必须在 Harness 之外补上什么，并向一个 Pi 编码智能体用户解释会话迁到 Pi Durable 后有什么变化。

:::note
Harness 保证的是它存储中已提交的东西；它周边的一切都归宿主所有。每一行都把一项保证与它留下的工作配在一起。出自 spec §2.2、§5.2、§11.3、§13、README §Storage 与 `src/harness/types.ts`。
:::

### 规范排除在外的东西

规范以系统「最初没有」的十一件事收尾：这些是范围上的决定，不是需要绕开的缺口。表格把它们全部列出。其中两条塑造了日常代码：

- 没有「可见但未持久」的发布。UI 绝不显示存储并未持有的文本，所以流式输出只能和
- 进度提交一样平滑，默认间隔 100 ms（6.2（p. 88））。
- 没有强制终止。一个忽略自己中止信号的工具无法在进程内被停下；`close()` 会等它。把该次调用的 context 传给每一个 await。
:::note
整个 Session 的 DOM｜没有一棵包含全部内容的可观察树；去观察会话视图、文档或任务图（8.2（p. 129））。可见但未持久的发布｜未提交进度没有快速通道；片段按提交节奏出现（6.2（p. 88））。Session 内核的语义事件日志｜agent 事件由提交推导而来，不被存储（8.3（p. 133））。会话作用域的可回溯文档｜可回溯只对 conversation 作用域存在（4.1（p. 50））。自动检查点启发式｜文档只在 `checkpointWhen()` 这么说时才存基线（4.3（p. 56））。自动挂载第三方视图｜视图只挂载内置文档；你自己的要用 `snapshot()`、`documentState()` 或 `watchDoc()` 读。CRDT／离线多写者合并｜每个存储一个写者；不合并并发的历史。把 Chord 操作翻译成 SQL｜SQLite 把操作存为记录，而不是 SQL 更新（9.2（p. 144））。JSONL 的全局压缩或修复｜main.jsonl 只会增长；一旦损坏，打开就会失败（9.3（p. 148））。与已移除的 Pico 原型的兼容性｜没有从更早的内部原型迁移的路径。强制终止扩展代码｜一个忽略自己信号的处理器无法在进程内被杀掉；close 会等它。
:::

### 一个存储，一个所有者

同一时刻只有一个进程可以使用一个存储。「一个存储在同一时刻属于一个进程；不存在跨进程锁」README §Storage。没有什么能阻止第二个进程打开同一个文件，于是每个进程都会以为自己才是唯一的写者。SQLite 选项 `busyTimeoutMs`（默认 5,000 ms）只是让 SQLite 等待文件锁 `src/storage/sqlite/node.ts`；它并不能让两个 Harness 在同一个文件上变得安全。所以崩溃恢复是你监管者的职责。必须有东西发现进程死了，启动一个新的，并重新打开存储。重新打开会做完剩下的事：正在运行的任务回到 `pending`，下一次 `resume()`、提交项或 `wait()` 会再次启动它们（调度器（p. 73））。同一次重新打开也处理计划中的交接：一旦 `close()` 兑现，「新的 Harness 可以打开同一个 Storage」spec §2.2。打开本身就是一次写入。`Harness.open()` 会提交对运行中任务的重置，即便之后没有任何东西恢复 `research/capture/crash-reopen-tasks.txt`，所以一个仪表盘绝不能「只是打开」另一个进程拥有的存储。对 SQLite 而言，一个独立的只读连接可以安全地读取运行中的数据库；capture kit 就是这样读取它运行中的行的 `research/capture/sqlite-rows-midrun.txt`。重新打开之前先安装每个扩展。代码缺失的任务不算失败；它会一直阻塞等待，直到注册表能运行它（5.4（p. 73））。

### 效果属于执行它们的系统

Harness 能提交「打算扣这张卡」的意图。它无法让这次扣款恰好发生一次。工具调用先提交意图，再执行，然后提交结果。如果进程死在这中间，「效果可能已经发生」spec §5.2（效果三明治（p. 70））。只有远端系统能了结这件事：靠一个它认得的幂等键，或者一个你可以去问的句柄。对于没有重放的工具：`safe` 根本不会被重跑；模型只会收到一个被中断的错误结果（工具调用与重放（p. 94））。没有任何东西会自动回滚。撤销一个效果是你自己写的代码，写在执行它的那个任务的中止处理器里。

### 原始 Pi session 与 Pi Durable

Pi Durable「并不取代 Pi 编码智能体。它是一个用来构建任何智能体应用的框架，编码智能体也包含在内」earendil.com/posts/pi-durable。编码智能体保留自己的 session 文件。表格为已经了解前者的读者比较这两种记录模型（Pi Durable 的用途（p. 10））。

:::note
存储｜`~/.pi/agent/sessions/` 下每个 session 一个 JSONL 文件｜内存、一个 SQLite 文件，或一个带 sidecar 的 JSONL 目录。
:::

```
History shape a tree in one file; the leaf is the current position conversations; a fork is a new conversation capped at parent.at
Branching /tree in place; /fork, /clone write new files fork(entryId) in the same storage, with document fork policies
```

:::note
写入单位｜每个条目追加一行，文件在出现第一条 user 或 assistant 消息时才首次写入｜跨条目、任务、提交项和文档的一次原子提交。system 提示词｜用 system 消息给片段打补丁，`toolsAdded`／`toolsRemoved`｜具有相同位置契约的 `pi.system` 条目。
:::

```
```

:::note
压缩｜compaction 条目：`summary`、`firstKeptEntryId`、system 检查点｜`pi.compaction` 条目，其头指针是第一个保留的条目。
:::

:::note
上下文编辑｜带 `targetId` 和替换内容的 `context_edit` 条目｜对某个条目的编辑：省略或替换。模型与思考｜`model_change`、`thinking_level_change` 条目｜可回溯的 `pi.agent` 文档的字段。扩展状态｜带 `customType` 和 `data` 的自定义条目｜带 scope、history 和 fork 策略的类型化文档。排队的消息｜转向与后续项放在内存里；中止把它们退回编辑器｜`pi.inbox` 里持久的提交项，按 `requestId` 去重。进行中的工作｜没有任何条目类型记录运行中的响应或工具调用｜带检查点的 `pi.generation` 与 `pi.tool` 任务。
:::

```
Left: coding-agent docs and src/core/session-manager.ts. Right: src/types.ts, src/entries.ts and spec §2–§8.
```

两种设计共享记录方面的想法：只追加的条目、位置化的 system 增量、保留原始条目的摘要。不同之处在于一次写入意味着什么。Pi session 的一行记录某件事发生了。Pi Durable 的一次提交记录被允许看到的状态，包括尚未完成的工作。

### 需要你自己动手的部分

监管——在崩溃、重新部署和 OOM 时重启；保证每个存储只有一个进程，例如每个进程槽位或每个租户一个存储。身份与权限——API 里没有用户、账户或凭据类型。守卫是带 `beforeTool` 钩子的扩展，只在会话选中它们的范围内生效（钩子（p. 109））。备份——重新打开的 JSONL 存储会丢弃末尾写了一半的行，但「缺少必需的已确认数据就是损坏，打开会失败」spec §11.3。SQLite 可能在断电或宿主机故障时丢掉最新一次提交 README §Storage。没有任何东西会修复损坏的存储。API 变动——这个包还是实验性的：「API 可能在两个版本之间毫无预告地改变」README。1.0.3 版本已经破坏了自定义的 FileSystem 和 Shell 实现 CHANGELOG 1.0.3。锁定版本，并在升级后运行一致性测试套件（9.4（p. 152））。

```
Sources: spec §2.2, §5.2, §11.3, §13; README §Storage; CHANGELOG 1.0.3; research/capture/crash-reopen-tasks.txt; coding-agent docs/session-format.md, src/core/session-manager.ts; earendil.com/posts/pi-durable
```
