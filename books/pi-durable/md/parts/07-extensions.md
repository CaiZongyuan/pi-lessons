<a id="sec-7-1"></a>

## 7.1 扩展与注册表

<p class="lede">你的代码存放在进程内的注册表里；存储层只记录一个会话想要哪些扩展的名字。</p>
智能体需要工具、系统提示词和几道护栏。你还想在不停止智能体的情况下给其中之一发布修复，并在崩溃后重启而不丢失任何东西。Pi Durable 两样都做到了：所有代码留在内存里，只存名字。读完本节，你就能把代码打包成一个扩展、安装它、替换它，并说明重启需要什么。

### 这个包

扩展是你代码的一个具名包。它是一个普通对象，带一个名字和至多五个列表。`defineExtension()` 只是给这个对象标上类型；它不检查任何东西 `src/harness/define.ts`。每个列表都通过字符串名字与系统其余部分对应，绝不通过对象身份。注册表是扩展与 `Harness` 相遇的地方。`createRegistry()` 返回一个由你的应用拥有的对象。它已经持有三个内置任务定义 `pi.generation`、`pi.tool` 和 `pi.compaction`，它们不能被移除或替换。`Harness.open()` 会拒绝缺少它们的注册表，所以永远从 `createRegistry()` 开始 `src/harness/registry.ts`；`src/harness/harness.ts`。

<aside class="note">三个扩展，一个注册表 `README` §Extensions · spec §7.1 `TS`</aside>
```ts
import { createRegistry, defineExtension, hook, section, ToolTask }
from "@earendil-works/pi-durable"; import { CodingTools } from "@earendil-works/pi-durable/tools"; const Coding = defineExtension({
```

```
name: "coding", sections: [
section("preamble", () => "You are a concise coding assistant.", { tag: false }),
section("cwd", (input) => input.env?.cwd), ],
```

```ts
});
const Permissions = defineExtension({
```

```ts
name: "permissions", hooks: [hook(ToolTask, {
beforeTool: (call) => (isDangerous(call) ? { block: "Needs approval" } : undefined),
})], });
const registry = createRegistry(); registry.install(CodingTools); // "coding-tools": read, write, edit, bash
registry.install(Coding);
registry.install(Permissions);
```

<aside class="note">安装顺序有影响。默认情况下每个会话都按安装顺序使用全部已安装的扩展，因此 `coding-tools` 的工具排在 `coding` 添加的任何东西之前。</aside>
<img src="/pi-lessons/_assets/pi-durable/07-extensions/fig-7.1.png" alt="NAMES IN STORAGE , CODE IN MEMORY STRUCTURE" loading="lazy">

*代码存放在进程注册表里；会话只存名字。会话 1 没有存任何选择，使用宿主默认值。会话 7 指定了三个扩展；`skills` 在这个进程里没有安装，于是被跳过，存下的列表原样保留。前三个扩展来自这份列表；`reviewer` 和 `skills` 扩展取自 spec §7.1。*

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>tools tools the model can call tool name 7.4 (p. 112)</td><td>模型可以调用的工具 工具名 7.4（p. 112）</td><td></td></tr>
<tr><td>sections pieces of the system prompt section key 7.5 (p. 115)</td><td>系统提示词的组成部分 小节键 7.5（p. 115）</td><td></td></tr>
<tr><td>hooks handlers the built-in tasks call task name 7.3 (p. 109)</td><td>内置任务调用的处理器 任务名 7.3（p. 109）</td><td></td></tr>
<tr><td>wraps decorators for another extension’s tool or section tool name or section key 7.2 (p. 106)</td><td>另一个扩展的工具或小节的装饰器 工具名或小节键 7.2（p. 106）</td><td></td></tr>
<tr><td>tasks your own durable task definitions task name 5.4 (p. 73)</td><td>你自己的持久任务定义 任务名 5.4（p. 73）</td><td></td></tr>
<tr><td>The Extension interface, src/harness/types.ts.</td><td></td><td></td></tr>
</table>

### 存储里是名字，内存里是代码

注册表里的东西没有任何一样写到磁盘上。用 spec 自己的话，注册表「是进程本地的，可以比 `Harness` 活得更久，并且不被持久化」spec §7.1。会话把想要哪些扩展记成 `pi.agent` 文档里的一份名字列表（按会话的智能体（p. 106））。`Harness` 每次需要代码时，就在注册表里查这些名字。

<aside class="note">代码存放在进程注册表里；会话只存名字。会话 1 没有存任何选择，使用宿主默认值。会话 7 指定了三个扩展；`skills` 在这个进程里没有安装，于是被跳过，存下的列表原样保留。前三个扩展来自这份列表；`reviewer` 和 `skills` 扩展取自 spec §7.1。</aside>
这种划分正是让重启变得廉价的原因。抓取到的数据库中，一个已回答轮次把根的智能体存成 `{"model": {"provider": "faux", "modelId": "faux-1"}}`，别的什么都没有：没有工具代码，也没有提示词代码 `research/capture/sqlite-rows.txt`，文档 6。一个新进程安装自己的扩展，打开同一份存储，每个存下的名字就绑定到此刻承载它的代码上。没有已安装扩展的名字会被跳过，不是错误，并且它「在被再次安装时重新生效」spec §2.2。任务定义的机制完全一样。存下的任务把它的 kind 记成一个名字。如果没有任何已安装的扩展定义了这个名字，任务就被阻塞：它在等待，不是失败。之后安装这个扩展会解除阻塞（调度器（p. 73））。不管怎样，都在 `open()` 之前把一切装好，这样恢复的工作能立刻继续。

<img src="/pi-lessons/_assets/pi-durable/07-extensions/fig-7.2.png" alt="INSTALL ORDER TIMELINE" loading="lazy">

*同名安装会就地替换；卸载后再安装会把扩展移到末尾。这些操作以及订阅者的日志 `["a",*

### 安装、替换、卸载

注册表有两个操作。`install(extension)` 在末尾添加一个新名字，或者在同一个位置上替换已经占用该名字的扩展。`uninstall(extension)` 移除持有该名字的任何东西。每次改动立刻生效，并且「一个扩展就是重载的单位」spec §7.1。

<aside class="note">同名安装会就地替换；卸载后再安装会把扩展移到末尾。这些操作以及订阅者的日志 `["a",</aside>
位置就是优先级。两个扩展定义同名工具时，后面的那个胜出，后面的钩子也更晚运行（钩子（p. 109））。因为替换保留了位置，重载一个扩展永远不会改变谁胜出。一个会让注册表变得无效的安装会抛错，什么都不改变。一个扩展内部，工具名和小节键必须唯一；跨扩展时，重复的工具名正是一个扩展覆盖另一个的方式。小节键是小写的（`^[a-z][a-z0-9_-]*$`），而且绝不是 `instructions`，后者是保留的。任务名必须在整个注册表内唯一。已经在运行的工作绝不会看到脚下的注册表变化（边运行边重载（p. 118））。

<aside class="note">在 `Harness.open()` 之前按你想要的优先级顺序安装每个扩展。绝不要重命名会话已经在用的扩展、工具或任务：存下的名字会失配。要发布修复，就用同一个名字安装新的对象。安装和卸载不调用任何清理代码，所以共享资源要你自己释放，而且要等旧调用结束后只释放一次 spec §12。</aside>
<aside class="note">Sources: src/harness/registry.ts; src/harness/define.ts; src/harness/types.ts (Extension, Registry, RegistrySnapshot); src/harness/harness.ts:410–435; spec §7.1, §2.2, §12; README §Extensions; test/harness-registry.test.ts; research/capture/sqlite-rows.txt</aside>
<a id="sec-7-2"></a>

## 7.2 按会话的智能体

<p class="lede">每个会话把自己的选择存成名字；`Harness` 每次需要时把它们变成真正的工具和提示词小节。</p>
不同会话需要不同配置：主聊天拿到全部工具，一个只读的评审者拿到两个，子智能体拿到它自己的指令。会话的智能体就是这套配置：它的模型、思考级别、扩展、工具、提示词小节、指令和工作目录。读完本节，你就能配置一套智能体，并准确预测模型会被提供哪些工具。

### 存下的选择，解析出的智能体

智能体有两种形态。存下的形态 `AgentState` 活在会话的 `pi.agent` 文档里，只持有名字。你从不设置的字段跟随宿主的默认值。解析出的形态 `Agent` 是 `Harness` 在需要真实对象时，用存下的名字、当前的注册表和宿主设置构建出来的东西。存下的文档随它的会话一起分叉和回溯（内置文档（p. 60））。

`Conversation.configure(change, context)` 编辑存下的智能体。每个字段遵循一条规则：「给出的字段替换存下的字段，`null` 清空它，`undefined` 不做改变」`src/harness/agent.ts`。你可以传扩展对象和工具对象；它们按名字存下。独立的 `configure(tx, id, change)` 在更大的一次提交里做同样的事，也就是一次原子保存：其中的一切要么一起存下，要么都不存。示例 7 展示了每次调用存下什么。

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>model { provider, modelId } no model; a request fails with no_model</td><td><code>{ provider, modelId }</code>：无模型；没有模型时一次请求以</td><td></td></tr>
<tr><td>thinkingLevel a pi-ai level "off"</td><td>：一个</td><td></td></tr>
<tr><td>extensions a list of names, or { add?, remove? } the host default: every installed extension</td><td></td><td></td></tr>
<tr><td>tools a list of names, or { remove } every tool of the selected extensions</td><td></td><td></td></tr>
<tr><td>instructions a string none; when set, rendered as the last prompt section</td><td></td><td></td></tr>
<tr><td>cwd a path none; passed to the host’s environment factory (9.5 (p. 155))</td><td></td><td></td></tr>
<tr><td>AgentState and its defaults, src/harness/types.ts and src/harness/agent.ts resolveAgent().</td><td></td><td></td></tr>
</table>

<aside class="note">先 configure，再读回来 ex 07 · `research/runs/07-configuration.txt` `TS`</aside>
```ts
// default tools: [ 'read', 'write', 'grep' ]
await root.configure({
```

```ts
model: { provider: "anthropic", modelId: "claude-sonnet-4-5" }, thinkingLevel: "high",
tools: [write, read], // objects in, names stored
}, context); // stored: { model: {…}, thinkingLevel: 'high', tools: [ 'write', 'read' ] }
await root.configure({ extensions: { remove: [Search] }, tools: null }, context);
// without search: [ 'read', 'write' ]
await root.configure({ extensions: [Files, Search] }, context);
registry.uninstall(Files); // files uninstalled: [ 'grep' ] registry.install(Files); // files reinstalled: [ 'read', 'write', 'grep' ]
```

<aside class="note">注释就是示例打印出的输出。`null` 清空工具过滤器，于是所选的每个工具又都会被提供。</aside>
因为一个字段是被整体替换的，`{ remove }` 列表不会累加。先移除 `edit` 再移除 `bash`，最后只有 `bash` 被移除：「`edit` 又会被提供」spec §2.2。一个界面开关必须先读当前列表，再写回新列表。配置不会往记录里追加任何东西；下一次模型请求会带上这个改动。

<img src="/pi-lessons/_assets/pi-durable/07-extensions/fig-7.3.png" alt="RESOLVING TOOLS FLOW" loading="lazy">

*解析按扩展顺序收集工具，就地替换同名者，包装胜出的那个，然后过滤。扩展、描述和过滤器取自 `test/harness-registry.test.ts`。最后一行显示存下的过滤器从上一行保留了哪些。*

### 从名字到工具

解析把存下的名字变成一次请求所用的工具和小节。它每次都跑同样的四个步骤，并且什么都不写：1. 挑选扩展。存下的列表精确地选中那些名字，按它的顺序。否则从宿主默认值（每个已安装的

- 扩展，按安装顺序）开始，然后应用 `add` 和 `remove`。未安装的名字被跳过。
2. 按扩展顺序收集工具。同名的后一个工具就地替换前一个。3. 把包装器应用到持有目标名字的那个工具或小节上。4. 过滤工具。存下的列表精确保留那些名字，按它的顺序；`{ remove }` 丢弃名字。小节以同样的

- 方式收集，`instructions` 在最后。
<aside class="note">解析按扩展顺序收集工具，就地替换同名者，包装胜出的那个，然后过滤。扩展、描述和过滤器取自 `test/harness-registry.test.ts`。最后一行显示存下的过滤器从上一行保留了哪些。</aside>
两种失败是刻意静默的。一个抛出异常的包装器，或者一个改掉了目标名字的包装器，会在本次解析中移除该工具，并上报到 `HarnessOptions.onReport`；对它的调用会得到一个 `tool_unavailable` 结果。目标未被选中的包装器什么也不做，所以一个计时包装器在没有 `bash` 的地方也是安全的 spec §7.1。

### 一个改动何时生效

`Harness` 在每个决策点重新解析智能体，绝不是每次运行只解析一次：「每个读取者在每个决策点解析一次」spec §7.1。宿主设置同理。`HarnessOptions.settings` 保存 `Harness` 全局的策略（默认选择、重试、压缩、工具执行模式、队列模式）。它从不被复制或存储，所以一个带 getter 的设置对象会「跟随用户偏好而无需一次 `Session` 写入」spec §2.2。默认值见「设置与默认值」（p. 180）。

所以一轮次期间做出的改动会到达下一次模型请求。模型已经发出的调用在它运行时解析自己的工具。如果你在中间移除了那个工具，这个调用会得到 `tool_unavailable`；如果你改了 `cwd`，这个调用会看到新目录 `README` §Per-Conversation Agent。

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>a model request model, tools, prompt, stream options once, while preparing that request</td><td></td><td></td></tr>
<tr><td>a tool call the called tool’s code when the call starts, and again on recovery</td><td></td><td></td></tr>
<tr><td>any task phase hooks once per phase, from that phase’s registry snapshot</td><td></td><td></td></tr>
<tr><td>a tool round parallel or sequential execution once per round</td><td></td><td></td></tr>
<tr><td>an input boundary steering and follow-up queue modes at each boundary</td><td></td><td></td></tr>
<tr><td>tools and prompt sections the environment for the current cwd at each use</td><td></td><td></td></tr>
<tr><td>Condensed from spec §7.1, “Who resolves what, and when”.</td><td></td><td></td></tr>
</table>

### 创建时的副本

一个新会话要么从某人的智能体副本开始，要么从空白开始 `src/harness/agent.ts` `createAgent()`：Fork——父方在分叉那一刻的智能体（分叉（p. 43））。Task-owned——所属任务的会话每一个存下字段的副本，包括 `instructions`。之后对拥有者的改动不会传给它。Ownerless——空白，即 `{}`：每个字段都跟随宿主。`root()`、`createConversation()` 和 `fork()` 的 `agent` 选项随后在同一次提交里应用它的改动。

<aside class="note">`{ add, remove }`「总是编辑宿主默认选择」，而不是一份复制来的列表。一个复制了列表 `["a", "b"]` 的子会话随后收到 `{ remove: [b] }`，最后得到的是宿主默认值减去 `b`，而不是 `["a"]`。要编辑一份复制来的列表，读出解析后智能体的 `extensions`，再写回新列表 spec §2.2、§12。</aside>
<aside class="note">会话应当跟随宿主时，就把字段留空；只在需要不同的时候才设置。会话需要一个精确、稳定的工具集（比如一个评审者）时，用存下的列表。预期配置改动在下一次模型请求时生效，而不是请求中途。</aside>
```
Sources: src/harness/agent.ts; src/harness/types.ts (AgentState, AgentChange, Agent, HarnessSettings, Settings); src/harness/scheduler.ts; spec §2.2, §7.1, §12; README §Per-Conversation Agent, §Settings; ex 07 and run 07; test/harness-
```

<aside class="note">`registry.test.ts`</aside>
<a id="sec-7-3"></a>

## 7.3 钩子

<p class="lede">钩子是内置任务在提交某个决策之前向你的扩展提出的一个问题；你的回答决定写入什么。</p>
你常常想引导智能体而不重写它：拦住一条危险的 shell 命令，在一次请求前裁掉旧消息，或者在答案薄弱时请模型继续。钩子做这些事。读完本节，你就能写出每一种钩子，预测多个扩展的回答如何合并，并让一次人工审批在崩溃中保持稳定。

### 谁会被问到

扩展用 `hook(task, handlers)` 注册处理器，例如 `hook(ToolTask, { beforeTool })`。任务对象提供类型检查；只有它的名字被保留，所以「钩子在其任务被重载后依然存在」spec §7.2。一个任务只问它的会话所选中的那些扩展的钩子。这就是全部的作用域模型：「要把一个钩子限制到某些会话，就只在那些会话里选中它的扩展」`README` §Hooks。没有全局钩子。这一面对安全性很重要：一个扩展列表里没有你的权限扩展的会话，会在没有它那道守卫的情况下运行 spec §12。

### 七种钩子

生成任务问四种钩子，工具任务问两种，压缩任务问一种。多个扩展都回答时，每种钩子用自己的方式合并这些回答。

<img src="/pi-lessons/_assets/pi-durable/07-extensions/fig-7.4.png" alt="WHERE HOOKS ARE ASKED SEQUENCE" loading="lazy">

*每个钩子都是内置任务在它所影响的提交之前提出的一个问题。一个使用工具的轮次及其最终答案，取自 `src/harness/generation.ts` 和 `tool.ts`；守卫 `beforeTool` 用粗体标出。`beforeCompact` 在压缩选定范围之后、做摘要之前被问到（压缩（p. 97））。*

### 用 memo 让决策崩溃安全

一个钩子可能运行两次：「消费它的那次提交之前的崩溃可能让它们重跑」spec §7.2。对纯检查来说这无害，但一次人工审批不能被再问一遍，也不能改变。用 `api.memo(name, …)` 存下它，它保留第一次写入的值：一次试图记下 `"denied"` 的重跑拿回的是 `"approved"` `test/harness-tools.test.ts`。钩子与提问的任务共用 memo 名字，所以要给自己的加前缀（阶段、步骤与进展（p. 67））。要在界面里显示状态，就把它提交到一个文档（会话视图（p. 129））。

### 把状态放在文档里

选中一个扩展决定了一个会话是否拥有某种行为。文档持有这个行为的状态。spec §7.2 里的计划模式就是这个模式：扩展在各处都被选中，而它的 `beforeTool` 读取会话自己的计划模式文档。

<aside class="note">一个由扩展文档驱动的钩子 spec §7.2 `TS`</aside>
```ts
const PlanModeDoc = defineDoc<{ enabled: boolean }>({
kind: "app.plan-mode", version: 1, scope: "conversation",
history: "latest", fork: "current", initial: () => ({ enabled: false }), });
export const PlanMode = defineExtension({
```

```
name: "plan-mode",
hooks: [hook(ToolTask, {
```

<aside class="note">// 文档不存在就意味着计划模式是关的。</aside>
```ts
beforeTool: async (call, api, context) =>
(await api.snapshot(PlanModeDoc, api.conversationId, context))?.enabled
&& writes(call)
```

```ts
? { block: "Plan mode: read-only" }
: undefined, })],
});
// /plan toggles this conversation's state; no selection change. await root.commit(async (tx) => {
(await tx.doc(PlanModeDoc, root.id)).enabled = true;
}, context);
```

<aside class="note">会话创建时扩展不会得到任何安装步骤，所以一个钩子把缺失的文档当作「关」。示例 27 构建了另一个变体：一种通过改变选择来切换的模式（构建一个编码智能体（p. 159））。</aside>
详解 参数被检查两次——在 `beforeTool` 之前按工具的 schema 检查一次，之后再检查一次。破坏 schema 的改写给出 `invalid_arguments`；一次拦截给出 `blocked`。意图之后不会重跑 `beforeTool`——一旦这次调用的意图被提交，恢复会复用存下的参数（工具调用与重放（p. 94））。钩子工作会占住这个任务——钩子创建的任务归提问的任务所有，并让它保持开启直到结束 spec §12。

<aside class="note">把守卫放在 `beforeTool` 里；抛出异常就拦截，这是安全的默认值。在每个需要它的会话里都选中守卫所在的扩展，包括使用存下扩展列表的子智能体。凡是人做出的决定都存进 memo，任何模式都存进文档。</aside>
<aside class="note">Sources: src/harness/define.ts hook(); src/harness/types.ts (HookApi, GenerationHooks, ToolHooks, CompactionHooks); src/harness/scheduler.ts; src/harness/agent.ts; src/harness/tool.ts; src/harness/generation.ts; spec §7.2, §7.3, §12; README §Hooks; test/harness-tools.test.ts</aside>
<a id="sec-7-4"></a>

## 7.4 定义工具

<p class="lede">工具是一个 schema、一条重放策略和一个 `execute()` 函数；`Harness` 把它报告的内容变成恰好一个结果条目。</p>
工具是模型作用于世界的方式：读一个文件、跑一条命令、调一个 API。难的是执行到一半崩溃。读完本节，你就能定义一个带类型的工具，把它的输出流给界面，选择它的重放策略，并读出它留下的结果条目。

### 十一行写一个工具

`defineTool()` 从它的 TypeBox 参数 schema 得到一个工具的类型。`Harness` 在 `execute()` 运行之前把模型的参数对照那个 schema 检查过，所以下面的 `args.n` 确实是一个数字。

<aside class="note">`count` 工具 `README` §Tools · `research/capture/scripts/one-turn.ts` `TS`</aside>
```ts
name: "count",
description: "Count from 1 to n",
parameters: Type.Object({ n: Type.Number() }),
execute: async (args, api) => {
for (let i = 1; i <= args.n; i++) api.output(`${i}\n`);
return {};
```

```
}, });
registry.install(defineExtension({ name: "count", tools: [count] }));
```

<aside class="note">`execute()` 不返回内容，所以它用 `api.output()` 写下的文本就成了结果。</aside>
只有标准的 `pi-ai` 工具字段（`name`、`description`、`parameters`）会发给模型。你自己的字段，比如一段提示词文本，留在你的代码里（系统提示词（p. 115））。四个可选字段用来设定策略：

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>replay "unsafe" may a call cut short by a crash run again on restart?</td><td>：<code>"unsafe"</code>——一次被崩溃打断的调用，重启后可以再跑吗？</td><td></td></tr>
<tr><td>executionMode "parallel" "sequential" makes the whole round of calls run one at a time</td><td>：<code>"parallel"</code>、<code>"sequential"</code>——让整轮调用一个一个地跑。</td><td></td></tr>
<tr><td>prepareArguments none repairs arguments before they are checked, such as a JSON string where an array belongs</td><td>：无——在检查之前修补参数，比如该放数组的地方给了一个 JSON 字符串。</td><td></td></tr>
<tr><td>outputLimits 50 KiB, 2,000 lines, keep the head bounds the output kept for the result</td><td>：50 KiB、2,000 行、保留头部——为结果保留的输出上限。</td><td></td></tr>
<tr><td>ToolRegistration, src/harness/types.ts; limits from src/truncate.ts. The execution mode default comes from settings’ toolExecution.</td><td></td><td></td></tr>
</table>

### 选择一条重放策略

每个工具作者都必须回答一个问题：如果进程在我的工具运行时死了，它可以再跑一次吗？在运行一次调用之前，工具任务把最终参数和策略写到磁盘上。重启时，只有存下的工具和当前的工具都说是 `"safe"`，它才重跑这次调用。否则它写下一个 `interrupted` 错误结果，带着当时保存下来的输出。只有以同样的参数跑两次无害时才声明 `safe`。完整的故事，连同一次抓取到的崩溃，见「工具调用与重放」（p. 94）。

<img src="/pi-lessons/_assets/pi-durable/07-extensions/fig-7.5.png" alt="ANATOMY OF A RESULT ENTRY ANATOMY" loading="lazy">

*一个 `tool-result` 条目存的正是模型看到的东西，外加结构化诊断。`research/capture/sqlite-rows.txt` 的第 13 条，`count` 工具对 `count {"n": 3}` 的回答，键按抓取顺序排列。*

### 从结果到条目

返回结果的每个字段都是可选的：`content`、`isError`、`details`、`diagnostics`、`usage` 和 `control`。工具任务补齐空缺，运行 `afterTool` 钩子，给长文本设上限（加上一条被截断的警告），然后写一个条目。存在诊断时，模型看到的文本以一个 `<harness>` 块结尾，每条诊断一行，而条目的 `data` 把它们保留为一个列表。

```
A tool-result entry stores exactly what the model saw, plus the structured diagnostics. Entry 13 of research/capture/sqlite-rows.txt, the count tool’s answer to count {"n": 3}, keys in captured order.
```

错误有两种，区别很重要。带 `isError: true` 的结果是一个普通回答：任务完成。从 `execute()` 抛出的异常也会变成一个错误结果，`code` 为 `tool_error`，部分输出被保留，但它会让工具任务以失败结束，这会中止这次调用启动的任何东西 `src/harness/tool.ts`。`Harness` 自己写下的错误带一个说明原因的 `code`：`tool_unavailable`、`invalid_arguments`、`blocked`、`interrupted` 或 `aborted`。两个结果字段作用于整个轮次。`usage` 记录工具自己的开销（用量与成本（p. 100））。`control` 可以提供更多工具（`addTools`）、在这一轮每个结果都要求时结束运行（`terminate`），或交给一个全新的上下文（交接、重置、交接与头指针（p. 46））。

### `execute()` 收到什么

`execute(args, api, context)` 拿到一个为这一次调用准备的 `api` 对象。它上面的每个操作在调用结束后都会失败。你最常用的部分：`env`——会话当前 `cwd` 的文件与进程，宿主没有配置时为 `undefined`（执行环境（p. 155））。`output(chunk)`——追加运行中的文本，比如 stdout。如果结果没有 `content`，保留下来的文本就成为 `content`。`details(value, context)`——为界面发布结构化进展；如果结果没有 `details`，最后一个值成为结果的 `details`。`diagnostic(d)`——给模型附上一条说明，比如一条警告，与工具的数据分开。`commit`、`memo`、`createTask`——提交、memo 和子任务，与任何任务里一样。`conversation(id)`——指向这次调用创建的某个会话的句柄（子智能体（p. 121））。`output`、`details` 和诊断在工具运行时就到达界面，大约每 100 ms 一次，通过实时文档。模型在结果条目被写出之前看不到其中任何东西（运行控制与实时文档（p. 88））。

### 内置工具与包装器

`@earendil-works/pi-durable/tools` 提供了 `read`、`write`、`edit` 和 `bash`，合起来就是 `CodingTools` 扩展（`coding-tools`）。没有东西会替你安装它们。它们只能通过 `api.env` 工作，而且这四个都是重载不安全的。`bash` 保留长输出的尾部，指向一个包含完整输出的文件，并在非零退出或超时时失败 `src/tools/`。要为某些会话改变一个工具，就覆盖或包装它，而不是复制它。同名的后一个扩展的工具会替换前一个，而 `wrapTool(tool, wrapper)` 装饰那个胜出的工具。包装器「从不捕获一个 base，所以重载 base 会保留它的包装器」spec §7.3。示例 30 让一个会话拥有一个会激活 virtualenv 并为每次 `bash` 调用计时的 `bash`，见运行 30。

<aside class="note">除非重跑无害，否则保持重载不安全；任何随机的值先用 memo 记下。预期内的失败返回 `isError: true`；只有当这次调用自身的工作应该被中止时才抛异常。给模型的说明用 `diagnostic()`，不要用工具的输出。</aside>
```
Sources: src/harness/define.ts; src/harness/types.ts (ToolRegistration, ToolExecutionApi, ToolExecutionResult); src/harness/tool.ts; src/truncate.ts; src/tools/index.ts, bash.ts, env.ts; spec §7.3, §8.5; README §Tools; ex 30, run 30; research/capture/sqlite-rows.txt
```

<img src="/pi-lessons/_assets/pi-durable/07-extensions/fig-7.6.png" alt="SECTIONS PER CONVERSATION COMPARISON" loading="lazy">

*小节按扩展顺序渲染，包装器生效，未选中的扩展退出，`instructions` 在最后。渲染出的值取自 `research/runs/15-system-prompt.txt`；每个标签内部的换行显示为空格。*

<a id="sec-7-5"></a>

## 7.5 系统提示词

<p class="lede">没有什么存下提示词；每次请求都从小节渲染它，而只有变化的部分被加进记录。</p>
供应商会缓存提示词的开头，所以每个轮次都重写系统提示词就是浪费钱和时间。Pi Durable 用小的具名片段构建提示词，某个片段变化时只发送那个片段。读完本节，你就能编写提示词小节，并让一个会话的提示词缓存保持温热。

### 小节

一个小节是系统提示词的一个具名片段。`section(key, render)` 构建一个。`render` 返回一个字符串，或返回 `undefined` 表示略过这个小节。默认情况下文本被包在标签里，即 `<key>…</key>`；`{ tag: false }` 则原样发送。所选扩展的小节和智能体的 `instructions` 是提示词文本唯一的来源 spec §7.4。一个 `render` 函数会拿到解析后的智能体（包括这次请求提供的工具）、这次请求的 `env`（一个 `cwd` 小节渲染 `input.env?.cwd`），以及用于读取已提交文档的 `read`。小节按扩展顺序排列，后出现的同键小节就地替换先出现的，`wrapSection()` 装饰器生效，`instructions` 在最后。示例 15 在两个会话上展示了这一切。

<aside class="note">小节按扩展顺序渲染，包装器生效，未选中的扩展退出，`instructions` 在最后。渲染出的值取自 `research/runs/15-system-prompt.txt`；每个标签内部的换行显示为空格。</aside>
抛出异常的小节不会让这次请求失败。它保留自己上次展示的文本（如果有），错误被上报。小节不该关心自己在哪里运行：「没有小节会检查自己是否跑在子智能体里」。一个会话的提示词只通过它的选择、它的 `instructions`、它的环境和它的文档而不同 spec §7.4。

<img src="/pi-lessons/_assets/pi-durable/07-extensions/fig-7.7.png" alt="THE DELTA STRUCTURE" loading="lazy">

*后一次请求只追加变化的那一个小节，放在它在记录中的位置。ex 15 的根会话；第二条 `pi.system` 条目是 {*

### 只发送差异

记录是模型看到过什么的记录，所以提示词也住在那里。每次请求之前，生成任务重放早先的系统条目，弄清模型已经有些什么。它渲染现在想要的小节，如果它们不同，就追加一条只带改动的 `pi.system` 条目。那条目持有一个 `sections` 补丁，外加 `toolsAdded` 和 `toolsRemoved`（条目与内置种类（p. 37））。

<aside class="note">第一次请求的基线 `research/capture/sqlite-rows.txt`，第 10 条 `JSON`</aside>
```json
{
"model": [ {
"role": "system", "content": "",
"sections": { "preamble": "You are a terse assistant." },
"toolsAdded": [
{ "name": "count", "description": "Count from 1 to n, …", "parameters": {…} } ],
"timestamp": 1791211974788
} ], "kind": "pi.system",
"id": 10,
"conversationId": 1, "byTaskId": 9
}
```

<aside class="note">一个会话的第一次请求写出完整的基线：一段不带标签的 `preamble` 和 `count` 工具（声明省略）。它跟在用户条目 7 之后，也就是它所回答的那条消息。这次抓取的 `preamble` 与示例 15 的不同，本节的两幅图用的是后者。</aside>
重放按记录顺序应用系统条目。一个字符串就地添加或替换一个小节，`null` 移除它。所以 `cwd` 改动之后，下一次请求追加一个只有单个键的补丁，提示词的其余部分保住它的位置和缓存。

<aside class="note">A later request appends only the section that changed, at its place in the transcript. The root conversation of ex 15; the second pi.system entry is {</aside>
```
sections: { cwd: '<cwd>\n/repo/packages\n</cwd>' } } in research/runs/15-system-prompt.txt.
```

示例 27 展示了工具以同样的方式变化。离开计划模式会追加 `sections: { plan_mode: null }`，加上 `write`、`edit` 和 `bash`，并移除 `submit_plan`，而 `read` 保住它的位置 运行 27。详解 一次压缩或重置之后——旧的基线可能落在活跃上下文之外，于是下一次请求会写一份全新的完整基线，即使什么都没变。抓取工具包见过一个没有小节的会话这样写出 `sections: {}` `research/capture/NOTES.md`，注 18。重排——补丁无法移动一个小节。当想要的顺序不同时，`Harness` 写两条条目：一条移除所有小节，一条按顺序把它们全部加回来 `src/harness/prompt.ts`。

缺失的工具——一次请求只提供能解析出来的工具。扩展已经消失的工具会列在 `toolsRemoved` 里，并在它再次解析出来时被加回来 spec §2.2。

历史是权威的——存进旧条目的渲染文本就保持原样，即使渲染器变了。

<aside class="note">让渲染器保持确定性：一个嵌进去的时间戳会改变文本、追加一个增量并破坏供应商的缓存 spec §7.4。给长寿命的会话一份稳定的扩展列表；宿主默认值会在你安装任何东西时移动 spec §12。以后通过过滤器或 `control.addTools` 添加工具：那只会追加一个小的增量，并保持先前的前缀完整。</aside>
<aside class="note">Sources: src/harness/prompt.ts; src/harness/define.ts section(), wrapSection(); src/harness/generation.ts; src/harness/types.ts (PromptInput, PromptSection); spec §7.4, §2.2, §12; README §System Prompt; ex 15, 27 and runs 15, 27; research/capture/sqlite-rows.txt; research/capture/NOTES.md</aside>
<a id="sec-7-6"></a>

## 7.6 边运行边重载

<p class="lede">用同一个名字安装一个新版本，会一次性把所有未来工作的代码换掉；已经在运行的工作用它启动时的代码跑完。</p>
你在一个智能体处于轮次中间时修工具里的一个 bug。你想让修复立刻生效，不干掉这个轮次，也不出现一次半旧半新的工具调用。读完本节，你就能在运行中的 `Harness` 里重载一个扩展，说清哪些工作看到旧代码、哪些看到新代码，并避开注册表抓不到的两个重载 bug。

### 重载就是一次安装

没有重载 API。你用同一个名字安装新的扩展对象。它就地替换旧的，而且「`Harness` 继续运行；不需要关闭或重新打开」spec §7.5。因为位置被保留，这个扩展的工具、钩子和小节保住它们的优先级。示例 31 在一次对它的调用正在运行时重载一个工具，然后重启进程。

<aside class="note">调用中途重载，然后重启 ex 31（节选）`TS`</aside>
```ts
const submission = await root.submit({ type: "input", content: "Which version?" }, context);
await running; // execute() of v1 has started
registry.install(loadVersioned("v2")); // same name "versioned" release();
await submission.wait(context); // call running during the reload: v1
await (await root.submit({ type: "input", content: "And now?" }, context)).wait(context);
// next call: v2 await harness.close(context); registry = createRegistry(); // second process: nothing installed harness = await open(registry);
```

```ts
root = await harness.root(context); // after restart, before install: []
registry.install(loadVersioned("v3"));
// after install: [ 'version' ]
```

<aside class="note">注释来自 `research/runs/31-reload-and-restart.txt`。两个进程用同一个 `SQLite` 文件；会话按名字选中了那个扩展。</aside>
<img src="/pi-lessons/_assets/pi-durable/07-extensions/fig-7.8.png" alt="A RELOAD MID - CALL TIMELINE" loading="lazy">

*运行中的工作保住它拿到的那份代码；下一次请求或调用使用替换后的那份。示例 31：这次调用在 v1 下开始，返回「v1」；下一次请求在 v2 下准备，它的调用返回「v2」。重启之后存下的选择没有变，并绑定到 v3。虚线标出各次安装。*

<aside class="note">Running work keeps the code it took; the next request or call uses the replacement. Example 31: the call started under v1 and returns “v1”; the next request is prepared under v2 and its call returns “v2”. After the restart the stored selection is unchanged and binds to v3. Dashed lines mark the installs.</aside>
### 谁看到哪份代码

三条规则决定它：一个阶段保住自己的代码——任务的每个阶段（两个检查点之间的一次处理器运行）都从它开始时取的注册表快照出发。它的钩子和智能体固定不变直到结束 `src/harness/scheduler.ts`。下一个阶段看到新代码——每个新阶段取一份新快照。同一次运行的不同阶段可能用不同版本：「没有什么要求一次运行只能看到一个注册表状态」spec §7.1。一次工具调用被钉住直到完成——这次调用在同一个阶段里找到它的工具、运行它的钩子、执行并写出结果，「所以不会有什么把解析和落定分开」`src/harness/tool.ts`。

两个方向都有测试钉住。调用中途被替换的工具仍然返回「v1」。一个 `section` 和一个 `beforeRequest` 钩子在工具运行期间被重载，第一次请求显示 `mode: v1`，第二次显示 `mode: v2` `test/harness-tools.test.ts`。替换代码「从不发出信号或中断」运行中的工作 spec §7.5。

### 任务定义会交接

你自己的任务定义同样按名字重载。当一个运行中的任务结束一个阶段，而它的 kind 此刻装上了一个不同的定义时，只要新代码能接手，任务就交给它：同一个版本，或者一个带 `migrate` 函数的更新版本。否则旧代码继续运行它，并上报这个不匹配。版本与迁移见「调度器」（p. 73）。安装还会解除阻塞。一个因为扩展在 `open` 时缺失、或因为存下的版本太新而阻塞的任务，一旦装上一个合适的定义就跑起来。`harness.inspect()` 显示哪些任务被阻塞（任务图与 `inspect()`（p. 137））。

### 重载不触及的东西

磁盘上什么都没有变化。重载不提交任何东西，不发出任何事件，也不重写任何记录。一个使用该扩展的会话在下一次请求时会收到一个系统增量，但仅限于渲染出的小节或工具声明确实不同（系统提示词（p. 115））。重启就是从空注册表开始的一次重载。第二个进程打开文件之后，根的智能体没有任何工具，直到扩展被再次装上，然后它有了新代码的那个版本工具 运行 31。来自这个扩展的待处理任务在装上之后恢复。绝不要在旧的 `close()` 兑现之前打开新的 `Harness`：两个实例不能同时拥有一个 `Session`。

<aside class="note">过早清理：替换一个扩展「只会停止新的使用」。紧跟在 `install()` 之后关闭数据库连接池或子进程，会破坏仍在旧对象上运行的调用。移动任务：把一个任务定义从一个扩展移到另一个扩展，「会在两次安装之间留下一段空档，其待处理任务被阻塞」spec §7.5、§12。</aside>
<aside class="note">用同一个名字安装来重载；没有别的可调。当一个任务存下的输入或检查点的含义变化时，提升它的版本。如果旧代码忽略取消且永远不结束，`close()` 仍然会等它。只有把扩展跑在一个独立的 worker 或进程里，你才能杀掉它们 spec §7.5、§13。</aside>
```
Sources: src/harness/registry.ts; src/harness/scheduler.ts; src/harness/tool.ts; spec §7.1, §7.5, §12, §13; README §Reload; ex 10, 31 and runs 10, 31; test/harness-tools.test.ts
```

<a id="sec-7-7"></a>

## 7.7 子智能体

<p class="lede">子智能体是一个普通会话，由创建它的工作所拥有；所有权和请求 ID 让它可中止、崩溃安全，而不需要一套</p>
<p class="lede">子智能体 API。</p>
子智能体是第二个智能体，有自己的记录，你把一件活交给它：「研究这个」「评审那个 diff」。你用会话、所有权和一个工具来构建它。读完本节，你就能写出这个包提供的两种模式，并预测中止、空闲等待和崩溃各自会对它们做什么。

### 前台模式

一个前台子智能体活在一次工具调用内部。这个工具创建一个由它自己的工具任务拥有的子会话，把活交给它，等待答案并返回。每个持久动作都有键，所以崩溃后的重跑能找到第一次尝试做出来的东西。

<aside class="note">`subagent` 工具 ex 22（节选）`TS`</aside>
```ts
defineTool({
name: "subagent", replay: "safe",
parameters: Type.Object({ task: Type.String() }),
execute: async (args, api, ctx) => {
const child = await api.commit(async (tx) => {
const found = await tx.scanConversations({ ownerTaskId: api.taskId }, 1);
const existing = found.items[0];
```

```ts
if (existing !== undefined) return existing.id; const created = await tx.createConversation({
ownership: { kind: "task", taskId: api.taskId },
}); await configure(tx, created.id, { extensions: { remove: [Subagent] } });
return created.id;
```

```ts
}, ctx); await api.details({ conversationId: child }, ctx);
const handle = (await api.conversation(child, ctx))!;
const request = { type: "input", content: args.task,
requestId: `subagent:${api.taskId}` } as const;
const settled = await (await handle.submit(request, ctx)).wait(ctx);
// … throw unless settled is an answered input (elided) const text = await answerText(api, settled.answer, ctx);
```

```ts
return { content: [{ type: "text", text }] };
}, }) Run 22 prints the child’s assistant: 2, 3, and 5. and the parent’s The subagent says: 2, 3, and 5.
```

每一部分都在回答一个崩溃问题：先找后建——子会话由这个工具的任务拥有，所以重跑会用 `scanConversations({ ownerTaskId })` 找到它，而不是造出第二个。一次提交完成创建与配置——子会话从父方智能体的副本开始（创建时的副本（p. 106））；同一次提交移除 `subagent` 扩展，让子会话自己不能启动子智能体。来自这个任务的请求 ID——重跑时，带同一个 ID 的 `submit()` 返回第一次的提交项，而不是把活发两遍。绝不要用供应商的调用 ID：它「在一个 `Session` 内不唯一」spec §7.3。`details` 把界面指向子会话——界面在 `tool_execution_update` 事件里看到 `{ conversationId }`，并接到子会话的事件上（智能体事件（p. 133））。

<img src="/pi-lessons/_assets/pi-durable/07-extensions/fig-7.9.png" alt="ONE SUBAGENT CALL SEQUENCE" loading="lazy">

*一次可重放安全的子智能体调用按所有者找到它的子会话，按请求 ID 找到它的提交项。ex 22 中工具与界面的各个步骤。第 1 步是一次提交；第 4 步提交这个活，第 5 步是子会话自己的运行，第 6 步是工具的 `wait()`。*

`api.conversation()` 返回的句柄只在这次调用运行期间有效，而且只接受 `input`。绝不要在 `commit()` 回调里用它：`Session` 操作不能嵌套（提交与变更线（p. 29））。

### 所有权决定中止与空闲

拥有子会话让它成为这次调用工作的一部分。「中止这次调用就会中止子会话」，这次调用失败也一样；「父方只有在子会话之后才空闲」`README` §Abort and Subagents。一个拥有运行中工作的工具任务会保持开启直到那份工作结束（所有权与结构化并发（p. 76），中止、故障与孤儿（p. 80））。

<img src="/pi-lessons/_assets/pi-durable/07-extensions/fig-7.10.png" alt="TWO OWNERSHIP SHAPES TREE" loading="lazy">

*前台子会话属于这次调用；后台子会话挂在一个后台锚点上。箭头从所有者指向被拥有者。左：ex 22。右：ex 23，锚点立刻完成，一个 reporter 任务把每条消息送给子会话，再把答案发回给父方。虚线是后台的边界：父方的 Esc 和空闲等待止步于此。*

<aside class="note">A foreground child belongs to the call; a background child hangs off a background anchor. Arrows point from owner to owned. Left: ex 22. Right: ex 23, where the anchor completes at once and a reporter task delivers each message to the child and posts the answer back to the parent. The dashed line is the background boundary: the parent’s Esc and idle waits stop there.</aside>
### 后台模式

一个后台子智能体活得比父方的轮次更久：用户可以给它发消息、停掉它，以后再列出它。示例 23 把这放在一个带 `spawn`、`send`、`stop` 和 `status` 四个动作的 `subagent` 工具后面。一次 `spawn` 一次提交三样东西。一个锚点任务 `app.subagent-anchor` 是父会话的后台任务；它立刻完成，并在子会话工作期间保持开启。子会话由这个锚点拥有，不带 `subagent` 扩展，并有自己的 `instructions`。父方的 `app.subagents` 文档把子智能体的名字映射到子会话；父方的一个分叉开始时它是空的。

每条消息都经过一个后台 reporter 任务 `app.subagent-reporter`。它把消息提交给子会话，等待，再把答案作为一条后续输入发给父方。两次提交都用从 reporter 的 ID 派生出的请求 ID，「所以子会话只收到一次消息，父方只收到一次答案」spec §7.3。运行 23 在子智能体工作期间关闭 `Harness`；重启之后父方仍然收到 `reader: Moby Dick`。

background 标志是一堵墙。父方的 Esc 和空闲等待止步于锚点，所以它们不会去动子智能体。`abort(context, { background: true })` 仍然能穿透过去。`stop` 动作直接中止子会话：它当前的答案结束，排队的消息被丢弃，而子智能体保持可用，就像任何已完成的子智能体一样 spec §5.4。

<aside class="note">为每个持久动作加上键：按所有者找子会话，并从任务 ID 派生请求 ID。一个答案内部的活选前台，用户之后还会对话的智能体选后台。绝不要把子会话的开销报成工具的 `usage`；那会被计两次（用量与成本（p. 100））。</aside>
```
Sources: spec §7.3, §5.4, §12; README §Abort and Subagents; ex 22, 23 and runs 22, 23; src/harness/harness.ts; src/harness/agent.ts; src/harness/tool.ts
```

<table>
<tr><th>导出</th><th>译文</th><th>参见</th></tr>
<tr><td>beforeRequest generation replace the messages of this one request; each handler gets the previous one’s result reported, ignored</td><td>generation：替换这一次请求的消息；每个处理器拿到前一个的结果。已上报，被忽略。</td><td></td></tr>
<tr><td>afterResponse generation observe every model response reported, ignored</td><td>generation：观察每一个模型响应。已上报，被忽略。</td><td></td></tr>
<tr><td>onYield generation answer a final answer with { continue }; the first wins reported, ignored</td><td>generation：用 <code>{ continue }</code> 回答一个最终答案；第一个胜出。已上报，被忽略。</td><td></td></tr>
<tr><td>afterTools generation observe a finished round of tool results reported, ignored</td><td>generation：观察一轮结束的工具结果。已上报，被忽略。</td><td></td></tr>
<tr><td>beforeTool tool rewrite the arguments, or block the call; the first block wins the call is blocked</td><td>tool：改写参数，或拦下这次调用；第一个拦截胜出。这次调用被拦下。</td><td></td></tr>
<tr><td>afterTool tool replace the result, handler by handler reported, ignored</td><td>tool：替换结果，逐个处理器进行。已上报，被忽略。</td><td></td></tr>
<tr><td>beforeCompact compaction decline, or supply a summary; the first decision wins reported, ignored</td><td>compaction：拒绝，或提供一份摘要；第一个决定胜出。已上报，被忽略。</td><td></td></tr>
<tr><td>GenerationHooks, ToolHooks and CompactionHooks, src/harness/types.ts; spec §7.2; src/harness/tool.ts. “Reported” means passed to</td><td></td><td></td></tr>
<tr><td>HarnessOptions.onReport. Handlers run in extension order. A throwing guard blocks: it fails closed.</td><td>。处理器按扩展顺序运行。一个抛出异常的守卫会拦截：它失败时封闭。</td><td></td></tr>
</table>
