---
title: 运行模式：交互式、print 与 JSON
---

<div class="section-kicker">5.5 / CONFIGURATION & EXTENSIONS</div>

# 运行模式：交互式、print 与 JSON

---

无论以哪种方式启动 Pi，都会运行同一个 `main()`，并构建同一个 `AgentSessionRuntime`；模式选择发生在较晚阶段，由两个标志和两次 TTY 检查决定，而且它只决定由谁读取事件。



在终端中运行 `pi` 会打开全屏编辑器。`pi -p "…"` 打印一个答案后退出。`pi --mode json` 将每个事件以一行 JSON 的形式流式输出，而 `pi --mode rpc` 则在 stdin 和 stdout 上保持一个开放的 JSONL 对话。本节跟随 `main()`，从 argv 一直追踪到它将运行时交给某个模式的那一刻，随后介绍人或 shell 脚本可以直接驱动的三种模式：交互、print 和 JSON。RPC 与进程内 SDK 见“RPC 模式与 SDK”（原书第133页）。这里提到的每个标志都列在“CLI 参考”（原书第191页）中。

## 一个入口点



`pi` 的可执行文件是 `dist/bundle/cli.js`，见 `CA/package.json:10`，它由仅六行的 `src/cli.ts` 构建而来。它调用 `setupCli()`，设置 `process.title`，导出 `PI_CODING_AGENT=true` 和 `AI_AGENT=pi`，禁用 `process.emitWarning` 的输出，并配置 HTTP 分发器，见 `CA/src/cli/setup.ts:4`。然后调用 `main(process.argv.slice(2))`，见 `CA/src/cli.ts:6`。该包还导出 `./rpc-entry`，见 `CA/package.json:19`；它执行相同的设置，但将 `process.title` 设为 `pi-rpc`，并调用 `main(["--mode", "rpc", ...argv])`，见 `CA/src/rpc-entry.ts:13`。这是一个模块入口点，而非第二个 bin。



随后，`main()` 按固定顺序执行，见 `CA/src/main.ts:573`。子命令会在任何标志解析之前分发，因此 `pi auth`、`pi install` 或 `pi mcp` 永远不会构建会话。



<BookFigure id="5.10" />

> 模式在第 3 步确定，但直到第 8 步才被使用。其间所有工作，包括迁移、会话选择、项目信任、扩展加载和模型解析，对四种模式都完全相同。行号均指向 `CA/src/main.ts`。此图为示意图。
> 
> 



图 5\.10（原书第127页）的第 1–8 步与源码的对应关系如下：

1. 子命令：`runAuthCommand` 最先运行，早于清理或设置，见 `CA/src/main.ts:582`。之后是 `handlePackageCommand`（`install`、`remove`、`uninstall`、`update`、`list`），它总是以 `process.exit` 结束，见 `CA/src/main.ts:597`；再之后是 `handleConfigCommand`，见 `CA/src/main.ts:610`；最后是 `mcp`，见 `CA/src/main.ts:614`。

2. 标志：`parseArgs` 将错误收集为诊断信息；出现任何错误都会打印并以退出码 1 退出，见 `CA/src/main.ts:626`。`--version` 打印后退出；`--export` 写入 HTML 后退出，不构建运行时，见 `CA/src/main.ts:637`。

3. 模式：参见下方的判定阶梯。除交互模式外，每种模式都会在这里调用 `takeOverStdout()`，将意外的 `process.stdout.write` 调用重定向到 stderr，见 `CA/src/core/output-guard.ts:45`。RPC 模式在此处拒绝 `@file` 参数，见 `CA/src/main.ts:657`。

4. 会话：`createSessionManager` 选择一个分支，采用第一个匹配项：`--no-session`（或 `--help`、`--list-models`）→ 内存中；`--fork`；`--session`；`--resume`；`--continue`；`--session-id`；否则创建新文件，见 `CA/src/main.ts:358`。“会话：JSONL 树”（原书第86页）介绍了这些文件。

5. 运行时：`createAgentSessionRuntime(createRuntime, …)` 在 `CA/src/main.ts:730` 运行工厂函数：`createAgentSessionServices` → `DefaultResourceLoader.reload()`（在信任确认前的扩展加载与完整扩展加载之间显示项目信任提示）→ `createAgentSessionFromServices`。这个工厂函数会被保留，因此 `/new`、`/resume` 和 `/fork` 都会通过它重新构建。

6. 元数据：只有运行时已经存在，才会响应 `--help`，因为帮助文本会列出已加载扩展注册的标志，见 `CA/src/main.ts:877`。

7. 输入：除 RPC 外，每种模式都会读取管道传入的 stdin；只要存在这类输入，交互模式就会降为 print 模式，见 `CA/src/main.ts:895`。随后打印运行时诊断信息；出现任何错误都以退出码 1 退出，见 `CA/src/main.ts:919`。非交互模式若没有模型，则以退出码 1 退出，见 `CA/src/main.ts:927`。

8. 交接：调用 `runRpcMode(runtime)`，见 `CA/src/main.ts:950`；或 `new InteractiveMode(runtime, …).run()`，见 `CA/src/main.ts:952`；或 `runPrintMode(runtime, { mode })`，见 `CA/src/main.ts:986`。随后每种模式都会调用 `session.bindExtensions(…)`，发出 `session_start` 和 `resources_discover`，见“扩展事件与上下文”（原书第120页）。

### 判定阶梯



完整的模式判定逻辑。来源：`CA/src/main.ts:112`。

```ts
function resolveAppMode(parsed: Args, stdinIsTTY: boolean, stdoutIsTTY: boolean): AppMode {
    if (parsed.mode === "rpc") {
        return "rpc";
    }
    if (parsed.mode === "json") {
        return "json";
    }
    if (parsed.print || !stdinIsTTY || !stdoutIsTTY) {
        return "print";
    }
    return "interactive";
}
```

> 这是完整函数，复制自固定提交版本的检出代码。
> 
> 



这个判定阶梯有一个出人意料的结果：`--mode text` 不会选中任何模式。`parseArgs` 接受它，见 `CA/src/cli/args.ts:103`，但 `resolveAppMode` 从不检查它，所以在终端中运行 `pi --mode text` 仍会打开 TUI。一次性文本输出应使用 `-p`。只要重定向 stdout 或 stdin 中的任意一个，就足以进入 print 模式；即便两次检查均通过，之后读到管道 stdin 仍会强制采用 print，见 `CA/src/main.ts:895`。



|<strong>调用</strong>|<strong>模式</strong>|<strong>原因</strong>|
|---|---|---|
|`pi`|`interactive`|两个流都是 TTY|
|`pi --mode text`|`interactive`|没有检查 `text`|
|`pi -p "..."`|`print`|`--print`|
|`pi "..." > out.txt`|`print`|stdout 不是 TTY|
|`echo "..." \| pi`|`print`|stdin 不是 TTY|
|`pi --mode json "..."`|`json`|在 `--print` 之前检查|
|`pi --mode rpc`|`rpc`|最先检查|



`--mode` 的优先级高于 `--print`；在两者都未指定时，重定向会决定模式。来源：`CA/src/main.ts:112` 中的 `resolveAppMode`，以及 `CA/src/main.ts:895` 中根据 stdin 进行的降级。



四种模式的区别，仅在于如何处理三个标准流，以及如何处理扩展对话框：

<BookFigure id="5.11" />

> 只有交互模式和 RPC 模式能够提问。print 和 JSON 模式不绑定 UI 上下文，因此每个扩展对话框都会解析为其默认值。三个非交互模式会将意外的 `process.stdout.write` 调用重定向到 stderr，使 stdout 只承载它们自己的输出。此图为示意图，依据 `CA/src/main.ts:651–655`、`CA/src/core/output-guard.ts`、`CA/src/modes/print-mode.ts` 和 `CA/src/modes/rpc/rpc-mode.ts`。
> 
> 

## 交互模式



`InteractiveMode` 有 7,072 行，位于 `CA/src/modes/interactive/interactive-mode.ts`，通过 `pi-tui` 绘制所有内容，见“pi\-tui”（原书第158页）。它有两种布局，由 `tuiMode` 设置或 `--tui-mode` 选择：默认的 `fullscreen`，见 `CA/src/core/settings-manager.ts:1349`，会固定编辑器和状态区域，让对话记录在窗口内部滚动；`regular` 则写入终端自身的回滚缓冲区，见 `CA/docs/usage.md`。



编辑器的提交处理器按以下顺序判断一行输入的含义，见 `CA/src/modes/interactive/interactive-mode.ts:3179`：

|<strong>输入</strong>|<strong>效果</strong>|
|---|---|
|内置 `/command`|由模式自身处理；24 个命令列在“斜杠命令与快捷键”（原书第197页）中|
|`! cmd`|用 bash 运行 `cmd`，并将输出加入上下文|
|`!! cmd`|运行 `cmd`，但不将其加入上下文|
|压缩期间输入的任何文本|排队，直到压缩结束；扩展命令仍会立即运行|
|流式输出期间输入的任何文本|`session.prompt(text, { streamingBehavior: "steer" })`|
|空闲时输入的任何文本|一个新提示词|



Enter 会向正在运行的智能体发送引导消息，而不会等待。Alt\+Enter 则将后续消息排入队列，Alt\+Up 会将排队文本取回编辑器。提交处理器见 `CA/src/modes/interactive/interactive-mode.ts:3179`；按键定义来自 `CA/src/core/keybindings.ts:135`。



Escape 具有多种用途，采用第一个匹配的状态，见 `CA/src/modes/interactive/interactive-mode.ts:3050`。智能体进行流式输出时，Escape 会中止运行，并将所有排队的引导消息和后续消息移回编辑器，用空行连接，见 `CA/src/modes/interactive/interactive-mode.ts:4702`。`!` 命令运行期间，它会中止该命令。在 bash 模式中，它会清空当前行。编辑器为空时，在 500 ms 内按两次 Escape，会根据 `doubleEscapeAction` 打开 `/tree`、`/fork` 或不执行任何操作，见 `CA/src/modes/interactive/interactive-mode.ts:3064`。Ctrl\+C 会清空编辑器，500 ms 内再次按下则退出，见 `CA/src/modes/interactive/interactive-mode.ts:4231`。

## print 模式



print 模式按顺序发送提示词，然后退出。第一个提示词由三部分组装而成：管道 stdin、`@file` 文本，以及第一个位置参数消息；其余消息随后作为独立提示词发送，见 `CA/src/cli/initial-message.ts:20`、`CA/src/modes/print-mode.ts:131`。



print 模式写出的文本。来源：`CA/src/modes/print-mode.ts:139`。



```ts
if (mode === "text") {
    const state = session.state;
    const lastMessage = state.messages[state.messages.length - 1];

    if (lastMessage?.role === "assistant") {
        const assistantMsg = lastMessage as AssistantMessage;
        if (assistantMsg.stopReason === "error" || assistantMsg.stopReason === "aborted") {
            console.error(assistantMsg.errorMessage || `Request ${assistantMsg.stopReason}`);
            exitCode = 1;
        } else {
            for (const content of assistantMsg.content) {
                if (content.type === "text") {
                    writeRawStdout(`${content.text}\n`);
                }
            }
        }
    }
}
```

> 这是完整代码块。最后一条消息中的思考块和工具调用块不会打印；更早的消息则完全不会打印。
> 
> 



只有最后一条助手消息会进入 stdout。如果运行以错误或中止结束，错误会写入 stderr，退出码为 1。抛出的异常也会导致以退出码 1 退出，见 `CA/src/modes/print-mode.ts:159`。



管道 stdin 与提示词之间没有分隔符。`readPipedStdin` 会去掉输入首尾的空白，见 `CA/src/main.ts:93`，而 `buildInitialMessage` 用 `""` 连接 stdin、文件文本和第一条消息，见 `CA/src/cli/initial-message.ts:40`。因此，`cat notes.txt | pi -p "Summarise this"` 会把文件的最后一行与“Summarise this”粘在一起发送。单元测试传入的 stdin 带有末尾换行符，而 CLI 永远不会传入这样的内容，见 `CA/test/initial-message.test.ts`。可以在提示词开头添加换行符或空格，也可以把指令放进管道传入的文本中。

## JSON 模式



JSON 模式就是换了订阅者的 print 模式。第 1 行是会话头，在绑定扩展之前写入，见 `CA/src/modes/print-mode.ts:122`。之后每个 `AgentSessionEvent` 都经过 `toJsonEvent`，各占一行 JSON，见 `CA/src/modes/print-mode.ts:110`。stdout 不会写入其他内容，退出码遵循与文本模式相同的规则。



`toJsonEvent` 会改变一种事件类型。`message_update` 会移除累积的 `message` 和其 `assistantMessageEvent` 内部的 `partial` 快照，并增加一个顶层 `usage`，见 `CA/src/modes/json-event.ts:48`。`toolcall_start` 会保留工具调用的 `id` 和 `toolName`，否则它们会随着 `partial` 一同丢失，见 `CA/src/modes/json-event.ts:23`。其他所有事件都原样通过。RPC 模式使用同一个函数，因此下面的结构也就是 RPC 事件的结构。



捕获工具包使用 faux 提供商和一个内联扩展，在 JSON 模式下通过真实运行时执行了一次提示词；该扩展会在每次工具调用之前调用 `ctx.ui.confirm()`，见 `research/capture/rpc-and-sdk-child.mjs`：

```js
{"type":"session","version":3,"id":"<uuid>","timestamp":"2026-10-05T23:26:18.959Z","cwd":"<tmp>/project"}
{"type":"agent_start"}
{"type":"turn_start"}
{"type":"message_start","message":{"role":"system","content":"","sections":...}}
{"type":"message_end","message":{"role":"system",...}}
{"type":"message_start","message":{"role":"user","content":[{"type":"text","text":"What does hello.txt say?"}],"timestamp":<ts>}}
{"type":"message_end",...}
{"type":"message_start","message":{"role":"assistant","content":[],...}}
{"type":"message_update","usage":{"input":1468,"output":10,...},"assistantMessageEvent":{"type":"toolcall_start","contentIndex":1,"id":"call_1","toolName":"read"}}
{"type":"tool_execution_start","toolCallId":"call_1","toolName":"read","args":{"path":"hello.txt"}}
{"type":"tool_execution_end","toolCallId":"call_1","toolName":"read","result":{"content":[{"type":"text","text":"not confirmed"}],"details":{}},"isError":true}
{"type":"agent_end","messages":[...],"willRetry":false}
{"type":"agent_settled"}
```



捕获记录共有 31 行：会话头、1 个 `agent_start`、2 个轮次、5 对消息事件、11 行 `message_update`、一次工具执行、`agent_end` 和 `agent_settled`，见 `research/out/rpc-exchange.txt` 的 §json\-mode。`text_delta` 更新的数量会随每次运行变化，但顺序不变。这里用 `…` 省略了较长的值。



`tool_execution_end` 这一行显示了没有 UI 的代价。print 和 JSON 模式绑定扩展时不传入 `uiContext`，见 `CA/src/modes/print-mode.ts:76`，因此运行器保留其空操作上下文，`ctx.hasUI` 为 `false`，见 `CA/src/core/extensions/runner.ts:621`。在这个上下文中，`select` 和 `input` 解析为 `undefined`，`confirm` 解析为 `false`，见 `CA/src/core/extensions/runner.ts:324`。阻止工具的是扩展自己的检查逻辑。同一个扩展在 RPC 模式中则会询问客户端（图 5\.12，原书第134页）。



> <strong>文档 ≠ 代码</strong>
> 
> `CA/docs/json.md`（§Event sequence）中的基本运行示例以用户消息开始，并将其 `content` 显示为字符串。真实事件流会在用户消息之前发出一对 `role: "system"` 的 `message_start` / `message_end`，而用户消息的 `content` 是内容块数组，见 `research/out/rpc-exchange.txt` 的 §json\-mode。根据文档示例编写的严格解析器会在第 4 行失败。
> 
> 

### 信号



|<strong>信号</strong>|<strong>print / JSON</strong>|<strong>RPC</strong>|
|---|---|---|
|`SIGTERM`|释放运行时，以退出码 143 退出|释放运行时，以退出码 143 退出，不刷新 stdout|
|`SIGHUP`（非 Windows）|释放运行时，以退出码 129 退出|释放运行时，以退出码 129 退出|
|stdin EOF|—|释放运行时，以退出码 0 退出|



每次有序退出都会触发 `reason: "quit"` 的 `session_shutdown`。`AgentSessionRuntime.dispose()` 在释放会话之前发出该事件，见 `CA/src/core/agent-session-runtime.ts:404`。处理器位于 `CA/src/modes/print-mode.ts:50` 和 `CA/src/modes/rpc/rpc-mode.ts:366`；两者都会先终止所跟踪的脱离父进程的子进程。



> <strong>对你的启示：</strong>
> 
> - 一次性文本输出使用 `-p`；在终端中仅指定 `--mode text` 仍会打开 TUI。
> 
> - 解析 JSON 模式时，应依据 `message_start`、增量事件和 `message_end`；`message_update` 中没有累积快照。
> 
> - 为每个扩展对话框设置安全的默认值：在 print 和 JSON 模式中，`confirm` 的答案永远是 `false`。
> 
> - 检查退出码：1 表示最后一条助手消息以错误或中止结束。
> 
> 



> 来源：`CA/package.json`（`bin`、`exports`）；`CA/src/cli.ts`；`CA/src/cli/setup.ts`（`setupCli`）；`CA/src/rpc-entry.ts`；`CA/src/main.ts`（`main`、`resolveAppMode`、`createSessionManager`、`readPipedStdin`、`createRuntime`）。`CA/src/cli/args.ts`（`parseArgs`）；`CA/src/cli/initial-message.ts`（`buildInitialMessage`）；`CA/src/core/output-guard.ts`（`takeOverStdout`）。`CA/src/modes/print-mode.ts`（`runPrintMode`）；`CA/src/modes/json-event.ts`（`toJsonEvent`）；`CA/src/core/extensions/runner.ts`（`noOpUIContext`、`hasUI`）；`CA/src/core/agent-session-runtime.ts`（`dispose`）。`CA/src/modes/interactive/interactive-mode.ts`（`setupEditorSubmitHandler`、`setupKeyHandlers`、`restoreQueuedMessagesToEditor`、`handleCtrlC`）；`CA/src/core/keybindings.ts`；`CA/src/core/settings-manager.ts`（`getTuiMode`、`getDoubleEscapeAction`）。`CA/test/initial-message.test.ts`；`CA/docs/json.md`、`usage.md`；`research/capture/rpc-and-sdk-child.mjs`；`research/out/rpc-exchange.txt`（§json\-mode）。
> 
>
