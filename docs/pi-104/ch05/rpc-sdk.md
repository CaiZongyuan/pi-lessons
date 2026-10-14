---
title: RPC 模式与 SDK
---

<div class="section-kicker">5.6 / CONFIGURATION & EXTENSIONS</div>

# RPC 模式与 SDK

---

RPC 模式就是在 SDK 的 `AgentSession` 两端接上 JSONL：输入 33 种命令，输出事件与响应。它真正新增的只有一个小型协议，让扩展能够向客户端提问。



想使用 Pi 的 IDE、Python 服务或 Web 后端有两个入口。它可以启动 `pi --mode rpc`，通过管道用 JSONL 通信；也可以导入 `@earendil-works/pi-coding-agent`，在自己的进程中持有一个 `AgentSession`。本节记录一次真实的 RPC 对话，列出每个命令及其响应数据，介绍扩展 UI 子协议和 TypeScript `RpcClient`，然后展示 CLI 本身赖以构建的 SDK 调用。CLI 如何执行到 `runRpcMode`，见“运行模式”（原书第127页）；事件本身见“智能体事件与 Agent 类”（原书第57页）。

## 分帧：严格的 JSONL



每条记录都是一个 JSON 对象，后面跟一个 LF。`serializeJsonLine` 就是 `JSON.stringify(value) + "\n"`，见 `CA/src/modes/rpc/jsonl.ts:10`。读取器仅按 `\n` 分割，并去掉末尾的一个 `\r`，因此也支持 CRLF 输入，见 `CA/src/modes/rpc/jsonl.ts:26`。



Pi 为什么不使用 readline。来源：`CA/src/modes/rpc/jsonL.ts:14`。

```ts
/**
 * 为流附加一个仅按 LF 分隔的 JSONL 读取器。
 *
 * 这里刻意不使用 Node readline。Readline 还会按其他 Unicode
 * 分隔符进行分割，而这些字符可以合法地出现在 JSON 字符串中，
 * 因此它无法实现严格的 JSONL 分帧。
 */
export function attachJsonLLineReader(stream: Readable, online: (line: string) => void): () => void {
    const decoder = new StringDecoder("utf8");
    let buffer = "";
    ...
}
```

> 在前两条语句之后截断；余下代码会缓冲数据块，并发出每个以 LF 结尾的行。
> 
> 



这里所说的分隔符是 U\+2028 和 U\+2029。两者都可以合法地出现在 JSON 字符串中，模型也可能生成其中任意一个。使用 Node readline 读取的客户端会把这样的记录拆成两段，且两段都无法解析，见 `CA/docs/rpc.md` 的 §Framing。`runRpcMode` 在做任何其他事情之前先调用 `takeOverStdout()`，见 `CA/src/modes/rpc/rpc-mode.ts:55`，因此扩展调用 `console.log` 时会写入 stderr，不会破坏事件流。

## 一次实录的交互



捕获工具包启动真实的 `runRpcMode`，配合 faux 提供商和一个内联扩展；该扩展在每次工具调用前都会调用 `ctx.ui.confirm()`。随后工具包扮演客户端，见 `research/capture/rpc-and-sdk-exchange.mjs`。模型按脚本先调用一次 `read`，然后回答。



<BookFigure id="5.12" />

> `prompt` 响应先于运行到达；`agent_settled` 标记运行结束。共 43 条记录：客户端发出 6 条，Pi 发出 36 条，再加上退出记录。步骤 2–3 是扩展 UI 子协议。来源：`research/out/rpc-exchange.txt`；事件数量会随着流式文本增量的数量变化。
> 
> 



以下是最先捕获到的三条原始记录：



```text
> {"id":"1","type":"prompt","message":"What does hello.txt say?"}
< {"id":"1","type":"response","command":"prompt","success":true,"data":{"disposition":"started"}}
< {"type":"agent_start"}
```



以下则是 `agent_settled` 之后，对话结束时的记录：



```text
{"id":"2","type":"get_last_assistant_text"}
{"id":"2","type":"response","command":"get_last_assistant_text","success":true,"data":{"text":"It says: Hello from the capture kit."}}
{ not json
{"type":"response","command":"parse","success":false,"error":"Failed to parse command: Expected property name or '}' in JSON at position 1 (line 1 column 2)"}
{"id":"4","type":"make_coffee"}
{"id":"4","type":"response","command":"make_coffee","success":false,"error":"Unknown command: make_coffee"}
> (stdin closed)
(exit code=0 signal=null)
```



## 响应与错误



每个命令至多生成一条响应记录。事件不携带命令 ID，只有一个例外：`bash_execution_update` 会重复带上启动它的 `bash` 命令的 ID，见 `CA/src/core/agent-session.ts:3847`。



成功：`{ id?, type: "response", command, success: true, data? }`。命令不返回内容时，会省略 `data`，见 `CA/src/modes/rpc/rpc-mode.ts:64`。



失败：`{ id?, type: "response", command, success: false, error }`，见 `CA/src/modes/rpc/rpc-types.ts:245`。处理器抛出的错误会变成一个失败响应，使用该命令自己的 ID 和类型，见 `CA/src/modes/rpc/rpc-mode.ts:790`。



解析错误：不是 JSON 的行会得到 `command: "parse"`，且没有 ID，见 `CA/src/modes/rpc/rpc-mode.ts:755`。



未知命令：`command` 是那个未知的类型，`error` 是 `Unknown command: <type>`（未知命令：`<type>`），见 `CA/src/modes/rpc/rpc-mode.ts:715`。



`prompt`：在预检接受提示词时，通过 `preflightResult` 回调作答，而非等到运行结束，见 `CA/src/modes/rpc/rpc-mode.ts:403`。`disposition` 为 `started`、`queued` 或 `handled`，见 `CA/src/core/agent-session.ts:301`。`handled` 表示某个扩展已消费输入，不会开始运行，因此后面也不会出现 `agent_settled`。预检之前就被拒绝的提示词会改为收到失败响应。



`agent_end` 并不代表结束。重试、溢出恢复、压缩和排队的后续消息，都可能在它之后启动另一次底层运行。应等待 `agent_settled`，见 `CA/docs/rpc.md` 的 §Run lifecycle。



## 33 个命令



`RpcCommand` 是 33 种结构组成的联合类型，见 `CA/src/modes/rpc/rpc-types.ts:20`。每种命令都接受一个可选的字符串 `id`。



|<strong>领域</strong>|<strong>命令</strong>|<strong>参数</strong>|<strong>响应中的 `data`</strong>|
|---|---|---|---|
|提示词|`prompt`|`message, images?, streamingBehavior?: "steer" \| "followUp"`|`{ disposition }`|
||`steer`、`follow_up`|`message, images?`|`{ disposition: "queued" \| "handled" }`|
||`abort`|—|—|
||`clear_queue`|—|`{ steering: string[], followUp: string[] }`|
||`new_session`|`parentSession?`|`{ cancelled }`|
|状态|`get_state`|—|`RpcSessionState`|
||`get_messages`|—|`{ messages }`|
|模型|`set_model`|`provider, modelId`|`Model` 对象|
||`cycle_model`|—|`{ model, thinkingLevel, isScoped }` 或 `null`|
||`get_available_models`|—|`{ models }`|
|思考|`set_thinking_level`|`level`|—|
||`cycle_thinking_level`|—|`{ level }` 或 `null`|
||`get_available_thinking_levels`|—|`{ levels }`|
|队列|`set_steering_mode`、`set_follow_up_mode`|`mode: "all" \| "one-at-a-time"`|—|
|压缩|`compact`|`customInstructions?`|`CompactionResult`|
||`set_auto_compaction`|`enabled`|—|
|重试|`set_auto_retry`|`enabled`|—|
||`abort_retry`|—|—|
|Bash|`bash`|`command, excludeFromContext?`|`BashResult`；流式发出 `bash_execution_update`|
||`abort_bash`|—|—|
|会话|`get_session_stats`|—|`SessionStats`（计数、token 数、费用）|
||`export_html`|`outputPath?`|`{ path }`|
||`switch_session`|`sessionPath`|`{ cancelled }`|
||`fork`|`entryId`|`{ text, cancelled }`|
||`clone`|—|`{ cancelled }`|
||`get_entries`|`since?`（条目 ID）|`{ entries, leafId }`|
||`get_tree`|—|`{ tree, leafId }`|
||`get_last_assistant_text`|—|`{ text }`（或 `null`）|
||`set_session_name`|`name`|—|
|发现|`get_commands`|—|`{ commands }`：扩展命令、提示词模板、技能|

> 每个命令都映射到一个 `AgentSession` 或 `AgentSessionRuntime` 调用。依据 `RpcCommand` 和 `RpcResponse` 联合类型，见 `CA/src/modes/rpc/rpc-types.ts:20`、`CA/src/modes/rpc/rpc-types.ts:116`，以及 `CA/src/modes/rpc/rpc-mode.ts:386` 中的 `handleCommand`。破折号表示成功响应没有 `data`。
> 
> 



三个命令会用各自的消息报告失败：`set_model` 使用 `Model not found: <provider>/<id>`（找不到模型），见 `CA/src/modes/rpc/rpc-mode.ts:474`；`get_entries` 使用 `Entry not found: <since>`（找不到条目），见 `CA/src/modes/rpc/rpc-mode.ts:642`；`set_session_name` 使用 `Session name cannot be empty`（会话名称不能为空），见 `CA/src/modes/rpc/rpc-mode.ts:662`。`clone` 相当于在当前叶节点以 `position: "at"` 执行 `fork`，见 `CA/src/modes/rpc/rpc-mode.ts:624`。`new_session`、`switch_session`、`fork` 和 `clone` 会替换活动会话，并将扩展及事件订阅重新绑定到新会话，见 `CA/src/modes/rpc/rpc-mode.ts:438`。斜杠命令不是 RPC 命令：将 `/name` 作为 `prompt` 的消息发送，`get_commands` 会列出可用的命令。“斜杠命令与快捷键”（原书第197页）中的 24 个内置交互命令不在其中。



`get_state` 返回 `RpcSessionState`，见 `CA/src/modes/rpc/rpc-types.ts:96`。其中没有会话头；与 JSON 模式不同，RPC 模式从不写出会话头。

|<strong>字段</strong>|<strong>类型</strong>|<strong>字段</strong>|<strong>类型</strong>|
|---|---|---|---|
|`model?`|`Model`|`sessionFile?`|`string`|
|`thinkingLevel`|`ThinkingLevel`|`sessionId`|`string`|
|`isStreaming`|`boolean`|`sessionName?`|`string`|
|`isCompacting`|`boolean`|`autoCompactionEnabled`|`boolean`|
|`steeringMode`|`"all" \| "one-at-a-time"`|`messageCount`|`number`|
|`followUpMode`|`"all" \| "one-at-a-time"`|`pendingMessageCount`|`number`|



共十二个字段，每次调用都会实时从会话中读取。见 `CA/src/modes/rpc/rpc-mode.ts:448`。



除了采用 JSON 模式形式的每个 `AgentSessionEvent`（“运行模式”，原书第127页），当扩展处理器抛出异常时，stdout 还会承载 `extension_error` 记录：`{ type, extensionPath, event, error }`，见 `CA/src/modes/rpc/rpc-mode.ts:349`。

## 扩展 UI 子协议



RPC 模式使用真正的 `uiContext` 绑定扩展，见 `CA/src/modes/rpc/rpc-mode.ts:320`，因此 `ctx.hasUI` 为 `true`，`ctx.mode` 为 `"rpc"`。每个受支持的调用都会变成一个 `extension_ui_request`，带有通过 `crypto.randomUUID()` 新生成的 ID，见 `CA/src/modes/rpc/rpc-mode.ts:99`。对话框会等待带有该 ID 的 `extension_ui_response`；其他方法不需要回复。



|<strong>方法</strong>|<strong>请求字段</strong>|<strong>客户端回复</strong>|<strong>超时或中止时的默认值</strong>|
|---|---|---|---|
|`select`|`title, options[], timeout?`|`{ value }` 或 `{ cancelled: true }`|`undefined`|
|`confirm`|`title, message, timeout?`|`{ confirmed }` 或 `{ cancelled: true }`|`false`|
|`input`|`title, placeholder?, timeout?`|`{ value }` 或 `{ cancelled: true }`|`undefined`|
|`editor`|`title, prefill?`|`{ value }` 或 `{ cancelled: true }`|无：等待客户端|
|`notify`|`message, notifyType?`|无需回复|—|
|`setState`|`statusKey, statusText`|无需回复|—|
|`setWidget`|`widgetKey, widgetLines, widgetPlacement?`|无需回复|—|
|`setTitle`|`title`|无需回复|—|
|`set_editor_text`|`text`|无需回复|—|



对话框超时由 Pi 执行，而不是由客户端执行。超时触发或扩展的信号中止时，`createDialogPromise` 会解析为默认值，见 `CA/src/modes/rpc/rpc-mode.ts:91`。只有字符串数组形式的 `setWidget` 会被发送；组件工厂会被丢弃，见 `CA/src/modes/rpc/rpc-mode.ts:197`。`pasteToEditor` 会变成 `set_editor_text`。



`ExtensionUIContext` 的其余功能会直接降级，不发送消息。`custom()` 返回 `undefined`，`getEditorText()` 返回 `""`，`setTheme()` 返回 `{ success: false, … }`，而页脚、页眉、工作指示器和编辑器组件的设置方法不执行任何操作，见 `CA/src/modes/rpc/rpc-mode.ts:179`。如果响应的 ID 与任何待处理请求都不匹配，就会被静默丢弃，见 `CA/src/modes/rpc/rpc-mode.ts:774`。



> <strong>易踩的坑</strong>
> 
> `editor` 是唯一不经过 `createDialogPromise` 的对话框。它不接受超时，并且忽略中止信号，见 `CA/src/modes/rpc/rpc-mode.ts:254`。客户端如果一直不回答 `editor` 请求，就会让扩展在进程剩余的整个生命周期中一直等待。`CA/docs/rpc-extension-ui.md` 说智能体端会在超时时自动结束对话框，但这只对另外三种对话框成立。始终回答 `editor`，哪怕只回复 `{ cancelled: true }`。
> 
> 

## 关闭与 RpcClient



关闭 stdin 是有序的关闭方式：Pi 会释放运行时，由此发出 `session_shutdown`，然后以退出码 0 退出，见 `CA/src/modes/rpc/rpc-mode.ts:802`。扩展调用 `ctx.shutdown()` 会设置一个标志；Pi 会在当前命令之后，或在下一个 `agent_settled` 之后退出，见 `CA/src/modes/rpc/rpc-mode.ts:745`。信号处理见“运行模式”（原书第127页）。



对于仍希望使用子进程的 TypeScript 调用方，该包导出了 `RpcClient`，见 `CA/src/modes/rpc/rpc-client.ts`。每个命令都有一个带类型的方法（`prompt`、`getState`、`fork`、`getCommands` 等），此外还有三个基于 `agent_settled` 的辅助方法：



|<strong>成员</strong>|<strong>作用</strong>|
|---|---|
|`new RpcClient({ cliPath?, cwd?, env?, provider?, model?, args? })`|仅设置选项；不会运行任何内容|
|`start()`|启动 `node --mode rpc ...`，`cliPath` 默认为 `dist/cli.js`；等待 100 ms，如果子进程已经退出则抛出异常|
|`stop()`|发送 `SIGTERM`，然后在 1,000 ms 后发送 `SIGKILL`|
|`onEvent(listener)`|接收所有不是待处理请求之响应的记录|
|`waitForIdle(timeout = 60000)`|在下一个 `agent_settled` 时解析|
|`collectEvents(timeout = 60000)`|收集到下一个 `agent_settled` 为止的每个事件|
|`promptAndWait(message, images?, timeout = 60000)`|先订阅，再发送提示词，然后收集|



每个辅助方法默认都在 60 秒后超时。长时间运行需要显式指定超时。来源：`CA/src/modes/rpc/rpc-client.ts`（`RpcClientOptions`、`start`、`stop`、`onEvent`、`waitForIdle`、`collectEvents`、`promptAndWait`）。

## RpcClient 无法回答对话框



`RpcClient` 将 `extension_ui_request` 记录当作事件交给 `onEvent` 监听器，见 `CA/src/modes/rpc/rpc-client.ts:523`。它没有可以写入 `extension_ui_response` 的公开方法；`send` 是私有方法，见 `CA/src/modes/rpc/rpc-client.ts:556`。扩展如果调用 `ctx.ui.editor()`，或调用不带超时的 `confirm`，就会阻塞运行，直到客户端被停止。使用 `RpcClient` 时，只加载为对话框设置了超时的扩展，或者改用 SDK。此外，`cliPath` 相对于子进程的 `cwd` 解析，并由 `node` 启动，因此默认值只有在已经构建好的该包检出目录内才有效。

## SDK



SDK 是 CLI 的基础。不带参数调用 `createAgentSession()`，会从工作目录和 `~/.pi/agent` 发现资源，选择设置中的默认模型或第一个可用模型，并将会话存储到 JSONL 文件中，见 `CA/src/core/sdk.ts:181`。



最小 SDK 程序。来源：`CA/examples/sdk/01-minimal.ts`。

```ts
import { createAgentSession } from "@earendil-works/pi-coding-agent";

const { session } = await createAgentSession();

try {
    session.subscribe((event) => {
        if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
            process.stdout.write(event.assistantMessageEvent.delta);
        }
    });

    await session.prompt("What files are in the current directory?");
    session.state.messages.forEach((msg) => {
        console.log(msg);
    });
    console.log();
} finally {
    session.dispose();
}
```

> 这是去掉头部注释后的完整文件。进程内事件是完整的 `AgentSessionEvent`：`message_update` 仍携带累积的 `message`，而 JSON 和 RPC 模式会将它移除。
> 
> 



`session.prompt()` 在已接受的运行完成后解析，其中包括重试，见 `CA/docs/sdk.md` 的 §Prompting。`CreateAgentSessionOptions` 有 14 个字段，全部可选，见 `CA/src/core/sdk.ts:42`：



|<strong>选项</strong>|<strong>省略时的默认值</strong>|
|---|---|
|`cwd`|会话管理器的 `cwd`，否则为 `process.cwd()`|
|`agentDir`|`getAgentDir()`：`~/.pi/agent` 或 `PI_CODING_AGENT_DIR`|
|`modelRuntime`|基于 `auth.json` 和 `models.json` 的 `ModelRuntime.create()`|
|`model`|从会话恢复；否则采用设置中的默认值；再否则采用第一个可用模型|
|`thinkingLevel`|从会话恢复；否则采用模型专属设置；再否则采用设置中的默认值；最后为 `"medium"`|
|`scopedModels`|无；即 Ctrl\+P 循环切换的列表|
|`noTools`|未设置；可为 `"all"` 或 `"builtin"`|
|`tools`|`defaultTools` 设置，否则为 `read`、`bash`、`edit`、`write`|
|`excludeTools`|无；在 `tools` 之后应用，包含 MCP 工具|
|`customTools`|无|
|`resourceLoader`|一个新的 `DefaultResourceLoader`，并执行重新加载|
|`sessionManager`|`SessionManager.create(cwd, ...)`：持久化文件|
|`settingsManager`|`SettingsManager.create(cwd, agentDir)`|
|`sessionStartEvent`|启动时的 `session_start` 载荷|



> 如果没有传入 `sessionManager`，SDK 就会写入会话文件；要避免写入，传入 `SessionManager.inMemory()`。结果为 `{ session, extensionsResult, modelFallbackMessage? }`，见 `CA/src/core/sdk.ts:99`。默认值来自 `CA/src/core/sdk.ts:181` 和 `CA/src/core/defaults.ts`。
> 
> 



CLI 不直接调用 `createAgentSession`。它使用三个更底层的调用，这三个调用都已导出：



`createAgentSessionServices(opts)`：构建绑定到 cwd 的服务 `{ cwd, agentDir, modelRuntime, settingsManager, resourceLoader, diagnostics }`，重新加载资源加载器，并注册扩展先前排入队列的提供商，见 `CA/src/core/agent-session-services.ts:135`。



`createAgentSessionFromServices({ services, sessionManager, … })`：使用这些服务调用 `createAgentSession`，见 `CA/src/core/agent-session-services.ts:214`。



`createAgentSessionRuntime(factory, { cwd, agentDir, sessionManager })`：运行一次工厂函数并保留它。返回的 `AgentSessionRuntime` 提供 `newSession`、`switchSession`、`fork`、`importFromJsonl`、`setRebindSession` 和 `dispose`；每次替换都会通过 `session_shutdown` 拆除旧会话，再通过同一工厂函数构建新会话，见 `CA/src/core/agent-session-runtime.ts:420`。



有两个步骤很容易遗漏。第一，`createAgentSession` 从不发出 `session_start`；宿主必须调用 `session.bindExtensions({ … })`，正如每种模式所做的那样，见 `CA/src/core/agent-session.ts:3244`。MCP 扩展会在该处理器中连接其服务器，见“MCP”（原书第144页）。第二，内置的 `codemode`、`tool-search`、`mcp` 和 `lama.cpp` 扩展来自 CLI 的 `main()`，见 `CA/src/main.ts:575`，而不是来自 SDK。SDK 宿主通过 `DefaultResourceLoader` 的 `extensionFactories` 中的 `createCodemodeExtension()`、`createToolSearchExtension()` 和 `createMcpExtension()` 添加它们，见 `CA/examples/sdk/14-codemode-mcp.ts`。`CA/examples/sdk/` 中有十四个示例，从 `01-minimal.ts` 到 `14-codemodemcp.ts`，每个分别介绍一个功能。



> <strong>文档 ≠ 代码</strong>
> 
> `createAgentSession` 的 JSDoc 展示了 `createAgentSession({ continueSession: true })`，见 `CA/src/core/sdk.ts:163`。`CreateAgentSessionOptions` 没有 `continueSession` 字段，因此 TypeScript 会拒绝它。要继续最近的会话，应传入 `sessionManager: SessionManager.continueRecent(cwd)`；这正是 `pi -c` 的做法，见 `CA/src/main.ts:433`。

## 选择集成方式



|<strong>选择</strong>|<strong>适用场景</strong>|<strong>需要放弃的能力</strong>|
|---|---|---|
|SDK|同一进程中的 Node 或 Bun TypeScript|进程隔离|
|RPC|其他语言、IDE、沙箱化子进程|直接访问对象；24 个内置命令|
|`RpcClient`|希望将 Pi 作为子进程运行的 TypeScript|回答扩展对话框|
|JSON 模式|一次脚本化运行，并保留完整事件日志|启动之后的任何输入|
|print 模式|一次脚本化运行，只需要最终文本|事件、工具输出|



每一行运行的都是同一个 `AgentSession`。区别只有传输方式和 UI 上下文。来源：`CA/docs/rpc.md`（接口表）以及上文各节。



> <strong>对你的启示：</strong>
> 
> - 以字节方式读取 RPC stdout，仅按 LF 分割；绝不要使用 readline。
> 
> - 将 `prompt` 响应视为“已接受”，并等待 `agent_settled`，除非 `disposition` 为 `handled`。
> 
> - 按 ID 关联响应；命令处理是异步的。
> 
> - 回答每个 `editor` 请求；扩展会打开对话框时，避免使用 `RpcClient`。
> 
> - 在 SDK 中，一次性会话应传入 `SessionManager.inMemory()`，并在第一个提示词之前调用 `bindExtensions`。
> 
> 



> 来源：`CA/src/modes/rpc/jsonl.ts`（`serializeJsonLine`、`attachJsonlLineReader`）。`CA/src/modes/rpc/rpc-mode.ts`（`runRpcMode`、`createDialogPromise`、`createExtensionUIContext`、`handleCommand`、`handleInputLine`、`shutdown`）。`CA/src/modes/rpc/rpc-types.ts`（`RpcCommand`、`RpcResponse`、`RpcSessionState`、`RpcExtensionUIRequest`、`RpcExtensionUIResponse`）。`CA/src/modes/rpc/rpc-client.ts`（`RpcClient`）。`CA/src/core/agent-session.ts`（`PromptDisposition`、`bindExtensions`、`bash_execution_update`）。`CA/src/core/sdk.ts`（`CreateAgentSessionOptions`、`createAgentSession`）；`CA/src/core/agent-session-services.ts`；`CA/src/core/agent-session-runtime.ts`；`CA/src/core/defaults.ts`；`CA/src/extensions/index.ts`。`CA/examples/sdk/01-minimal.ts`、`14-codemode-mcp.ts`。`CA/docs/rpc.md`、`rpc-commands.md`、`rpc-extension-ui.md`、`sdk.md`。`research/capture/rpc-and-sdk-exchange.mjs`、`rpc-and-sdkchild.mjs`；`research/out/rpc-exchange.txt`。
> 
>
