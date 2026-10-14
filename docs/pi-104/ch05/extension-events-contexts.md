---
title: 扩展事件与上下文
---

<div class="section-kicker">5.4 / CONFIGURATION & EXTENSIONS</div>

# 扩展事件与上下文

---

扩展通过 41 个事件了解 Pi，其中大约一半允许它改变接下来发生的事情。处理器若抛出异常，系统会报告错误并跳过它；但 `tool_call` 和 `user_bash` 是例外，在这两个事件中抛出异常会阻止操作。



Pi 提供的并非单一拦截点。它为一次运行的每个步骤都提供了带类型的事件：启动、会话变更、输入、系统提示词、消息列表、提供商请求、每条消息和每次工具调用，以及轮次之间的边界。本节介绍所有事件共用的分发规则，并给出完整的事件表，列明各处理器可以返回的内容；还会从头到尾展示一次被阻止的调用，列出处理器接收的上下文对象，并梳理 `CA/examples/extensions/` 中的 80 个条目。

## 分发规则



所有分发都经过 `ExtensionRunner`，见 `CA/src/core/extensions/runner.ts`。每个事件都遵循四条规则：



顺序：处理器先按扩展加载顺序执行，再按同一扩展内部的注册顺序执行（“扩展、加载与 API”，原书第113页，给出了加载顺序）。`pi.on()` 返回一个函数，用于移除这一次注册；已经开始的分发仍保留其快照。



等待：必须等待每个处理器完成，才会运行下一个处理器。缓慢的 `provider_stream_event` 处理器会延迟流的消费。



错误：抛出的异常通过错误监听器以 `{ extensionPath, event, error, stack }` 的形式报告，随后继续分发给下一个处理器，见 `CA/src/core/extensions/runner.ts:1104`。



错误规则的例外：在 `tool_call` 中，运行器没有 `try`，因此抛出的异常会传出运行器并阻止调用，见 `CA/src/core/extensions/runner.ts:1242`。在 `user_bash` 中，异常会先被报告，然后再次抛出，见 `CA/src/core/extensions/runner.ts:1285`。两者都采取出错即拒绝的方式。



多个处理器的结果如何合并，取决于事件。`input` 串联转换，并在遇到第一个 `handled` 时停止，见 `CA/src/core/extensions/runner.ts:1519`。`tool_call` 在遇到第一个 `block: true` 时停止。`session_before_*` 事件在遇到第一个 `cancel: true` 时停止；否则，采用最后一个非空结果，见 `CA/src/core/extensions/runner.ts:1098`。`message_end` 串联替换；如果替换改变了角色，就拒绝它，并报告 `message_end handlers must return a message with the same role`（`message_end` 处理器必须返回角色相同的消息）。`cache_warming_decision` 采用最后返回的 `action`。`project_trust` 采用第一个 `yes` 或 `no`。

## 事件



图例：N 表示仅通知，M 表示可以修改，B 表示可以阻止或取消。表格按会话中的顺序排列。



|<strong>阶段</strong>|<strong>事件与载荷</strong>|<strong>处理器返回值</strong>|<strong>类型</strong>|
|---|---|---|---|
|启动|`project_trust { cwd }`，仅限信任确认前加载的扩展|`{ trusted: "yes" \| "no" \| "undecided", remember? }`|B|
||`resources_discover { cwd, reason: startup \| reload }`|`{ skillPaths?, promptPaths?, themePaths? }`|M|
||`mcp_servers_change { servers }`|—|N|
|会话|`session_start { reason: startup \| reload \| new \| resume \| fork, previousSessionFile? }`|—|N|
||`session_before_switch { reason: new \| resume, targetSessionFile? }`|`{ cancel? }`|B|
||`session_before_fork { entryId, position: before \| at }`|`{ cancel?, skipConversationRestore? }`|B|
||`session_before_compact { preparation, branchEntries, customInstructions?, reason, willRetry, signal }`|`{ cancel?, compaction? }`|B/M|
||`session_compact`、`session_compact_failed`|—|N|
||`session_before_tree { preparation, signal }`|`{ cancel?, summary?, customInstructions?, replaceInstructions?, label? }`|B/M|
||`session_tree`、`session_info_changed { name }`|—|N|
||`session_shutdown { reason: quit \| reload \| new \| resume \| fork, targetSessionFile? }`|—|N|
|输入|`input { text, images?, source, streamingBehavior? }`|`continue \| transform { text, images? } \| handled`|M/B|
||`before_agent_start { prompt, images?, systemPrompt, systemPromptOptions }`|`{ message?, systemPrompt? }`，或修改 `systemPromptOptions`|M|
|循环|`agent_start`、`turn_start { turnIndex, timestamp }`|—|N|
||`context { messages }`，隐藏系统消息|`{ messages? }`，或原地编辑|M|
||`context_with_system { messages }`，完整对话记录|`{ messages? }`|M|
|提供商|`before_provider_request { payload }`|替换后的载荷|M|
||`before_provider_headers { headers }`|原地修改；`null` 会删除一个请求头|M|
||`after_provider_response { status, headers }`、`provider_stream_event { provider, api, model, data }`|—|N|
||`cache_warming_decision { warmCost, missCost, continuationProbability, action }`|`{ action?: "warm" \| "stop" }`|M|
|消息|`message_start`、`message_update { message, assistantMessageEvent }`|—|N|
||`message_end { message }`|`{ message? }`，角色相同|M|
|工具|`tool_call { toolCallId, toolName, input, parentToolCallId? }`|`{ block?, reason?, terminate? }`；原地修改 `input`|B/M|
||`tool_execution_start`、`tool_execution_update`、`tool_execution_end`|—|N|
||`tool_result { ..., input, content, details, structuredContent?, isError, usage? }`|`{ content?, details?, structuredContent?, isError?, usage? }`|M|
|边界|`turn_end`、`agent_before_settle: { entries, continue, context, outcome }`|`{ entries?, continue? }`|M|
|UI|`agent_end { messages }`、`agent_settled`|—|N|
||`ui_prompt_start`、`ui_prompt_end { kind, title? }`|—|N|
|模型|`model_select { model, previousModel, source: set \| cycle \| restore }`、`thinking_level_select { level, previousLevel }`|—|N|
|Bash|`user_bash { command, excludeFromContext, cwd }`|`{ operations } \| { result }`|M/B|



41 个事件中有 19 个可以改变接下来发生的事情，其余 22 个只能观察。载荷和结果来自 `types.ts:679–1490` 与 `cache-warmer.ts:112`；`turn_end` 还携带 `turnIndex`、`message`、`toolResults` 及其条目 ID。“智能体事件与 Agent 类”（原书第57页）给出了循环发出其中各事件的顺序；“一个提示词的生命周期”（原书第15页）中的捕获记录展示了真实的事件流。



有几行内容需要进一步说明：

- `context` 与 `context_with_system`：`context` 处理器看到的是不含系统消息的对话，Pi 会在每个处理器执行后放回提示词和工具状态。之后，`context_with_system` 处理器看到完整对话记录，其输出会按返回的内容发送。如果移除了开头的系统消息，系统会报告“Handler removed the leading system message; the request has no prompt or initial tool declarations\.”（处理器移除了开头的系统消息；请求不含提示词或初始工具声明），但仍会照此执行，见 `CA/src/core/extensions/runner.ts:1342`。

- `before_agent_start`：后续处理器能看到前面处理器对 `systemPromptOptions` 的修改。返回 `systemPrompt` 会设置 `forceSystemPrompt`，并替换此次运行的整个提示词，见 `CA/src/core/extensions/runner.ts:1454`。每条返回的消息都会被收集。

- `tool_call`：在模式验证之后运行；处理器修改 `input` 后，不会再次验证，见 `CA/src/core/extensions/types.ts:1211`。只有当前批次中的每个最终结果都设置了 `terminate: true`，才会在该批次结束后终止运行。

- `tool_result`：替换 `content` 而不返回 `structuredContent` 时，结构化内容会被丢弃，因为它可能已不再匹配，见 `CA/src/core/extensions/runner.ts:1194`。

- `turn_end`、`agent_before_settle`：这两个边界允许采取行动。处理器串联拟议的条目，也就是 `custom`、`custom_message`、`context_edit` 或 `compaction` 类型的草稿，见 `CA/src/core/extensions/types.ts:966`；还可以设置 `continue: true`，以再发起一次模型请求。如果最终草稿未通过验证，就会全部丢弃，且 `continue` 变为 `false`，见 `CA/src/core/extensions/runner.ts:1075`。

- `user_bash`：用户输入 `!` 和 `!!` 命令时触发。由第一个返回结果的处理器决定后续行为：`{ operations }` 替换执行后端，`{ result }` 则完全替代执行过程。处理器抛出异常时，不会回退到本地执行：TUI 会报告错误，且不执行任何内容，见 `CA/src/modes/interactive/interactive-mode.ts:6962`。

## 一次调用，两个处理器



原手册中的时序图在固定提交版本上依然成立。`AgentSession` 在智能体上安装 `beforeToolCall`，并将其转发给 `emitToolCall()`，见 `CA/src/core/agent-session.ts:646`。智能体循环把结果转换为错误工具结果，见 `agent/agent-loop.ts:744`。



<BookFigure id="5.9" />

> 阻止操作会成为一个普通的失败工具结果；模型会读到其中的原因。如果没有提供原因，文本就是 `Tool execution was blocked`（工具执行被阻止）。如果 B 改为抛出异常，错误就会未经报告而传出运行器，`_beforeToolCall` 会再次抛出它，循环中的 `catch` 则会生成一个携带该异常消息的错误结果，见 `agent/agent-loop.ts:769`。此图为示意图；依据 `runner.ts:1242`、`agent-session.ts:646–669` 和 `agent-loop.ts:724–775`。
> 
> 



随附文档给出了一个基于工具注解的权限检查：



在调用任何非只读工具前询问。来源：`CA/docs/extensions.md`。

```js
pi.on("tool_call", async (event, ctx) => {
    const hints = pi.getAllTools().find((tool) => tool.name === event.toolName)?.annotations;
    const needsApproval =
        hints?.destructiveHint === true ||
        (!hints?.readOnlyHint && ((hints?.destructiveHint ?? true) || (hints?.openWorldHint ?? true)));
    if (needsApproval && !(await ctx.ui.confirm("Allow tool call?", event.toolName))) {
        return { block: true, reason: `${event.toolName} was not approved` };
    }
});
```

> 复制自 `CA/docs/extensions.md` 第169–177行。在 print 和 JSON 模式中，`ctx.ui.confirm()` 会立即解析为 `false`，因此这项检查会阻止其中所有没有注解的工具；`examples/extensions/permission-gate.ts` 会先检查 `ctx.hasUI`。
> 
> 

## 上下文



每个处理器的第二个参数都是 `ExtensionContext`，见 `CA/src/core/extensions/types.ts:325`。工具和命令接收其扩展版本。



三种上下文类型，仅列出成员。来源：`CA/src/core/extensions/types.ts`。

```ts
interface ExtensionContext {
    ui: ExtensionUIContext; mode: "tui" | "rpc" | "json" | "print"; hasUI: boolean;
    cwd; sessionManager: ReadOnlySessionManager; modelRegistry; model; scopedModels; thinkingLevel?;
    isIdle(); isProjectTrusted(); signal; abort(); hasPendingMessages(); shutdown();
    getContextUsage(); compact(options?); getSystemPrompt();
}

interface ExtensionToolContext extends ExtensionContext {
    readonly tools: readonly AgentTool[];
    executeTool(name, args, options?): Promise<AgentToolCallOutcome>;
}

interface ExtensionCommandContext extends ExtensionContext {
    getSystemServiceOptions(); waitForIdle(); newSession(options?); fork(entryId, options?);
    navigateTree(targetId, options?); switchSession(sessionPath, options?); reload();
}
```

> 由第325–435行压缩而来：移除了类型和文档注释，并将多个成员合并到同一行。成员名称及其顺序不变。
> 
> 



- `ExtensionToolContext.executeTool()`：运行另一个工具，经过与模型发起的调用相同的准备、验证、`tool_call` 和 `tool_result` 钩子。嵌套调用获得形如 `<calling id>/<n>` 的 ID，且不会出现在对话记录中。工具失败不会使它拒绝；失败会以 `isError: true` 返回，见 `CA/src/core/extensions/types.ts:383`。

- `ExtensionCommandContext`：只有命令处理器可以进行会话控制；接口注释称其为“仅在用户发起的命令中才可安全使用的会话控制方法”，见 `CA/src/core/extensions/types.ts:399`。`newSession()`、`fork()` 和 `switchSession()` 接受一个 `withSession(ctx)` 回调，它接收绑定到新会话的全新 `ReplacedSessionContext`。切换之后的任何操作都应使用它；旧的 `ctx` 已经过时（“扩展、加载与 API”，原书第113页）。

- `compact()`：启动压缩后直接返回，不等待完成；传入 `onComplete` 和 `onError` 可以观察结果（“压缩与分支摘要”，原书第92页）。

- `ctx.ui` 是 `ExtensionUIContext`，见 `CA/src/core/extensions/types.ts:149`：



|<strong>分组</strong>|<strong>成员</strong>|
|---|---|
|对话框|`select`、`confirm`、`input`（每个都接受 `{ signal?, timeout? }`）；`editor(title, prefill?)` 不接受选项|
|状态|`notify`、`setStatus`、`setWorkingMessage`、`setWorkingVisible`、`setWorkingIndicator`、`setHiddenThinkingLabel`、`setTitle`|
|布局|`setWidget(key, lines \| factory, { placement: "aboveEditor" \| "belowEditor" })`、`setHeader`、`setFooter`|
|组件|`custom(factory, { overlay?, overlayOptions?, onHandle? })`|
|编辑器|`setEditorText`、`getEditorText`、`pasteToEditor`、`setEditorComponent`、`getEditorComponent`、`addAutocompleteProvider`、`onTerminalInput`|
|外观|`theme`、`getAllThemes`、`getTheme`、`setTheme`、`getToolsExpanded`、`setToolsExpanded`|



`editor()` 是唯一不能超时的对话框。它的签名只接受标题和预填内容。



这些调用的行为取决于运行模式（“运行模式”，原书第127页）。绑定了真正的 UI 上下文时，`hasUI` 为 `true`；TUI 和 RPC 模式都是如此，见 `CA/src/core/extensions/runner.ts:621`：

|<strong>模式</strong>|<strong>`ctx.mode`</strong>|<strong>`hasUI`</strong>|<strong>对话框</strong>|<strong>组件与布局</strong>|
|---|---|---|---|---|
|交互模式|`tui`|`true`|完整支持|完整支持|
|RPC|`rpc`|`true`|以 `extension_ui_request` 发送给客户端，并等待回复|`custom()` → `undefined`；页眉、页脚、编辑器组件、工作指示器：空操作；`setWidget` 仅支持字符串行；`getEditorText()` → `""`|
|print、JSON|`print`、`json`|`false`|立即解析为 `undefined`，或在 `confirm` 中解析为 `false`|空操作|



需要答案的扩展必须检查 `hasUI`，否则就应当预期收到默认值。来源：`rpc-mode.ts` 中的 `createExtensionUIContext`，以及 `runner.ts` 中的 `noOpUIContext`。“RPC 模式与 SDK”（原书第133页）规定了 RPC UI 子协议。

## 扩展示例



在固定提交版本中，`CA/examples/extensions/` 包含 80 个条目：70 个单文件 `.ts` 扩展、9 个目录和一个 `README.md`，见 `research/out/stats.txt` 的 §example\-extensions。下列示例各自展示一种技巧；所有名称都已与目录列表核对。



|<strong>类别</strong>|<strong>示例</strong>|<strong>展示内容</strong>|
|---|---|---|
|安全|`permission-gate.ts`、`protected-paths.ts`、`confirm-destructive.ts`、`dirty-repo-guard.ts`、`project-trust.ts`、`sandbox/`、`gondolin/`|通过 `tool_call` 阻止调用，通过 `session_before_*` 取消操作，以及 `project_trust`；`sandbox/` 用基于 `@anthropic-ai/sandbox-runtime` 的版本替换 bash；`gondolin/` 在 QEMU 微型虚拟机中运行内置工具|
|工作流|`subagent/`、`plan-mode/`、`todo.ts`、`handoff.ts`、`preset.ts`、`tools.ts`、`git-checkpoint.ts`、`auto-commit-on-exit.ts`|子级 pi 进程、每种模式各自的工具集、存储在自定义条目中的状态|
|工具|`hello.ts`、`dynamic-tools.ts`、`tool-override.ts`、`structured-output.ts`、`ssh.ts`、`truncated-tool.ts`、`question.ts`|`registerTool`、替换内置工具、`terminate: true`、远程执行|
|提示词与上下文|`custom-compaction.ts`、`trigger-compact.ts`、`claude-rules.ts`、`prompt-customizer.ts`、`pirate.ts`、`dynamic-resources/`|`session_before_compact`、`before_agent_start`、`resources_discover`|
|UI|`custom-footer.ts`、`custom-header.ts`、`modal-editor.ts`、`overlay-test.ts`、`doom-overlay/`、`snake.ts`、`status-line.ts`、`notify.ts`|`ctx.ui` 布局、叠加层、自定义编辑器|
|提供商|`custom-provider-anthropic/`、`custom-provider-gitlab-duo/`、`jev-router.ts`|`registerProvider`；`jev-router.ts` 注册一个虚拟模型|
|基础连接|`event-bus.ts`、`rpc-demo.ts`、`reload-runtime.ts`、`interactive-shell.ts`、`inline-bash.ts`、`with-deps/`|`pi.events`、RPC UI、`/reload`、`user_bash`、带有自身 `node_modules` 的扩展|



这里列出了 79 个示例中的 45 个，并按各自展示的内容分类。说明来自每个文件的头部注释。



> <strong>对你的启示：</strong>
> 
> - 只有确实想阻止调用时，才在 `tool_call` 处理器中抛出异常；在其他每个事件中，异常都会被记录并忽略。
> 
> - 每次阻止调用时都返回原因；这是模型唯一能了解到的信息。
> 
> - 打开对话框前检查 `ctx.hasUI`，或为 print 和 JSON 运行选择安全的默认值。
> 
> - 将 `newSession()`、`fork()` 或 `switchSession()` 之后的工作放进 `withSession` 中。
> 
> 



> 来源：`CA/src/core/extensions/types.ts`（`ExtensionUIContext`、`ExtensionContext`、`ExtensionToolContext`、`ExtensionCommandContext`、事件和结果接口、`SessionBoundaryDraft`）；`CA/src/core/extensions/runner.ts`（`emit`、`emitCacheWarmingDecision`、`emitMessageEnd`、`emitToolResult`、`emitToolCall`、`emitUserBash`、`emitContext`、`emitBeforeProviderHeaders`、`emitBeforeAgentStart`、`emitResourcesDiscover`、`emitInput`、`emitBoundary`、`emitProjectTrustEvent`、`noOpUIContext`、`hasUI`）；`CA/src/core/cache-warmer.ts`；`CA/src/core/agent-session.ts`（`_beforeToolCall`、`_afterToolCall`）；`agent/agent-loop.ts`（`prepareToolCall`）；`CA/src/modes/rpc/rpc-mode.ts`（`createExtensionUIContext`）；`CA/src/modes/print-mode.ts`；`CA/docs/extensions.md`；`CA/examples/extensions *`；`research/out/stats.txt`（§example\-extensions）。
> 
>
