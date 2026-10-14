---
title: 扩展：加载与 API
---

<div class="section-kicker">5.3 / CONFIGURATION & EXTENSIONS</div>

# 扩展：加载与 API

---

完整的扩展示例，`CA/docs/extensions.md`（TypeScript）



```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
    pi.registerCommand("hello", {
    description: "Show a greeting",
    handler: async (name, ctx) => {
    ctx.ui.notify(`Hello, ${name || "world"}!`, "info");
    },
    });
}
```



扩展就是一个函数，它接收含有 32 个方法和一个事件总线的 `ExtensionAPI`。在这次调用期间注册的内容会一直暂存，直到调用返回，因此抛出异常的工厂函数不会留下任何内容。



扩展是 Pi 添加功能的主要方式。内置 MCP 客户端、codemode 和工具搜索本身就是扩展。本节展示 Pi 如何查找并导入扩展文件、采用什么顺序、两个扩展声明同一名称时会发生什么，以及 `/reload` 如何替换它们。随后列出每个 `ExtensionAPI` 方法，以及扩展传给 `registerTool()` 的 `ToolDefinition`。扩展可以订阅的事件见“扩展事件与上下文”（原书第120页）。

## 只有一个工厂函数



扩展是一个 TypeScript 或 JavaScript 模块，其默认导出具有以下类型，见 `CA/src/core/extensions/types.ts:2006`：



扩展约定，`CA/src/core/extensions/types.ts`

```ts
export type ExtensionFactory = (pi: ExtensionAPI) => void | Promise<void>;
```

> 第 2006 行，未删节。Pi 会等待异步工厂函数完成，然后才继续启动。
> 
> 



上面的完整扩展示例摘自 `CA/docs/extensions.md` 的快速入门。将它保存为 `~/.pi/agent/extensions/hello.ts`，或使用 `pi -e ./hello.ts` 只加载一次，然后输入 `/hello`。



随附文档规定了生命周期规则：“不要在工厂函数中启动进程、套接字、监视器或定时器，因为某些调用会加载扩展，但不会启动会话。”见 `CA/docs/extensions.md`。应在 `session_start` 处理器中启动长期运行的资源，并在幂等的 `session_shutdown` 处理器中关闭它们。

## 查找与导入



扩展路径来自“上下文文件、技能、模板、主题与包”（原书第106页）介绍的资源流水线。在这条流水线中，扩展有自己的顺序：首先是命令行 `-e` 路径，然后是按优先级排序的列表，最后是内联工厂函数，见 `CA/src/core/resource-loader.ts:573`。



<BookFigure id="5.7" />

流程：

1. `-e <source>`：CLI，临时作用域，也支持 `builtin:`

2. 项目设置：`.pi/settings.json` 中的 `extensions` 条目，排名 0

3. `.pi/extensions/`：仅限受信任项目

4. 用户设置：`~/.pi/agent/settings.json` 中的 `extensions` 条目，排名 2

5. `~/.pi/agent/extensions/`：始终加载，排名 3

6. 包：先项目包，后用户包，排名 4

7. 内置扩展：`builtin:lama.cpp`、`codemode`、`tool-search`、`mcp`，排名 5

8. 内联工厂函数：SDK 的 `extensionFactories`，最后加载

    

命令行指定的扩展最先加载。事件处理器、工具渲染器以及首次注册查找都遵循这个顺序。`research/out/resources-precedence.txt`（§extensions）验证了这一点，其中通过 `-e` 指定的扩展先于两个自动发现的扩展加载。



|<strong>方面</strong>|<strong>行为</strong>|<strong>来源</strong>|
|---|---|---|
|目录扫描|在 `extensions/` 目录中：直接位于其中的 `*.ts` 和 `*.js` 文件，以及每个子目录的 `package.json` 中的 `pi.extensions` 条目；否则加载其 `index.ts`，再否则加载其 `index.js`。只向下一层。如果某个目录自身具有清单或 index 文件，则只加载该项|`package-manager.ts:563`|
|导入|使用 `jiti`，设置 `moduleCache: false`，因此每次加载都会重新求值模块。导入的工厂函数按工作目录和缓存代次进行缓存；`/reload` 会递增代次|`loader.ts:576`、`loader.ts:138`|
|宿主导入|编译后的二进制文件、打包的 Node 构建以及 TypeScript 源码使用虚拟模块；未打包的 Node 构建使用路径别名。两者映射相同的 20 个模块说明符|`loader.ts:571`、`virtual-modules.ts:14`|
|内置扩展|包括 `builtin:lama.cpp`，以及可替换的 `builtin:codemode`、`builtin:tool-search` 和 `builtin:mcp`。在 `extensions` 设置中使用 `"-builtin:"` 禁用一个扩展；`--no-extensions` 移除全部内置扩展，`--no-mcp` 只移除 MCP|`CA/src/extensions/index.ts:7`|
|SDK|只有 CLI 会添加内置扩展。使用 `createAgentSession()` 创建的会话不会加载任何内置扩展，除非调用方传入它们|`CA/src/main.ts:575`|
|错误|导入错误和工厂函数错误会被收集为 `Failed to load extension: ...`，不会阻止其余扩展加载。在 CLI 中，任何此类错误都会以退出码 1 结束启动|`loader.ts:655`、`main.ts:919`|



二十个导入说明符会解析到宿主自己的副本。其中六个属于 TypeBox：`typebox`、`typebox/compile`、`typebox/value`，以及 `@sinclair/typebox` 下对应的三个。七个是 `@earendil-works/` 下的 Pi 包：`pi-agent-core`、`pi-tui`、`pi-ai`、`pi-ai/compat`、`pi-ai/oauth`、`pi-ai/providers/all` 和 `pi-coding-agent`。另外七个是旧版 `@mariozechner/` 作用域下相同的 Pi 包。裸的 `pi-ai` 说明符映射到 compat 入口点。

### 事务式注册



扩展收到的 API 对象有三个状态：`loading`、`active` 和 `failed`，见 `CA/src/core/extensions/loader.ts:253`。会改变共享运行时状态的注册操作，即 `registerProvider`、`unregisterProvider`、`registerMcpServer`、`unregisterMcpServer`、`registerVirtualModel`、`unregisterVirtualModel` 以及标志默认值，在工厂函数运行时会进入队列。只有工厂函数返回后，`commit()` 才会应用它们。如果工厂函数抛出异常，`discard()` 会丢弃队列、取消加载期间添加的事件总线监听器，并把 API 标记为失败，此后调用将抛出 `Extension "<path>" failed to load and its API is no longer active.`，见 `CA/src/core/extensions/loader.ts:532`。加载完成后，同样的调用会立即生效，因此命令处理器可以直接注册提供商，无须 `/reload`。



工具、命令、快捷键、标志、渲染器和处理器会直接写入扩展对象。只有扩展进入已加载列表后，它们才会变得可见；抛出异常的工厂函数不会进入该列表。

### 两个扩展，同一个名称



资源加载器不会拒绝重复项。如果两个扩展注册了相同的工具或标志，两者都会保持加载状态，加载器会把 `Tool "x" conflicts with <path>` 加入扩展错误列表，见 `CA/src/core/resource-loader.ts:1246`；工具查找会采用加载顺序中的第一个注册项，见 `CA/src/core/extensions/runner.ts:631`。CLI 会将该列表的每个条目转换为错误诊断，见 `CA/src/main.ts:800`，而错误诊断会终止启动：



```shell
$ pi -ne -e <tmp>/a.js -e <tmp>/b.js -p hi
Error: Failed to load extension "<tmp>/b.js": Tool "dup_tool" conflicts with <tmp>/a.js
Hint: Start without extensions using "pi -ne".
exit code: 1
```



这是 `research/out/extensions-conflict.txt` 的内容，来自两个各自只有一行、都注册 `dup_tool` 的扩展，针对固定构建离线运行。自行构建 `DefaultResourceLoader` 的 SDK 调用方会在 `getExtensions().errors` 中收到相同条目，并自行决定如何处理。



内置扩展是例外。如果可替换的内置扩展与其他任意扩展共享工具、命令或标志名称，它会在冲突检查之前被移除，见 `CA/src/core/resource-loader.ts:120`。因此，注册 `/mcp` 的第三方扩展会替换内置 MCP 客户端，并产生一条同时列出二者名称的警告。



易踩的坑：两个已安装扩展如果注册同名工具，会阻止 `pi` 命令启动，而 `CA/docs/extensions.md` 完全没有提到这一点。建议使用的 `pi -ne` 在任一扩展来自 `-e` 时都无济于事，因为即使指定 `--no-extensions`，`-e` 路径仍会加载。移除或禁用这两个扩展中的一个；注册通用名称之前，先用 `pi.getAllTools()` 检查名称。

### 热重载



`/reload` 调用 `AgentSession.reload()`，后者会替换整个扩展运行时，见 `CA/src/core/agent-session.ts:3646`：



<BookFigure id="5.8" />

> 重新加载后，除了会话转交的内容外，其他内容都不会保留。活动工具名称和标志值会传入新运行时；扩展闭包中保存的一切都会丢失。来源：`agent-session.ts:3646–3684`。最后两个事件只有在绑定了 UI 或命令上下文时才会触发。
> 
> 



重新加载或替换会话后，捕获的旧运行时 `pi` 或 `ctx` 会抛出异常：“会话替换或重新加载后，此扩展 ctx 已过期。不要在 `ctx.newSession()`、`ctx.fork()`、`ctx.switchSession()` 或 `ctx.reload()` 之后使用捕获的 pi 或命令 ctx。……”见 `CA/src/core/extensions/runner.ts:723`。必须在新会话中运行的工作应放在 `newSession()`、`fork()` 或 `switchSession()` 的 `withSession` 回调中，该回调会收到新的上下文，见“扩展事件与上下文”（原书第120页）。

## 扩展 API



`ExtensionAPI` 定义在 `types.ts:1553–1879`。它包含一个有 41 个类型化重载的 `on()` 方法、另外 31 个方法，以及 `events` 总线。

|<strong>分组</strong>|<strong>方法</strong>|
|---|---|
|事件|`on(event, handler)` → 取消订阅函数。共 41 个事件名；见“扩展事件与上下文”（原书第120页）|
|工具|`registerTool(def)` · `getActiveTools()` · `getAllTools()` · `setActiveTools(names)`|
|命令与输入|`registerCommand(name, { description?, getArgumentCompletions?, handler(args, ctx) })` · `registerShortcut(key, { description?, handler(ctx) })` · `registerFlag(name, { description?, type: "boolean" \| "string", default? })` · `getFlag(name)` · `getCommands()`|
|渲染|`registerMessageRenderer(customType, r)` · `registerEntryRenderer(customType, r)` · `registerToolRenderer(resolver)` · `registerMarkdownTransformer(t)`|
|对话|`sendMessage({ customType, content, display, details }, { triggerTurn?, deliverAs?: "steer" \| "followUp" \| "nextTurn" })` · `sendUserMessage(content, { deliverAs?, expandPromptTemplates? })`|
|会话数据|`appendEntry(customType, data?)` · `setSessionName(name)` · `getSessionName()` · `setLabel(entryId, label)`|
|模型|`setModel(model)` → `Promise` · `getThinkingLevel()` · `setThinkingLevel(level)`|
|提供商|`registerProvider(provider)` 或 `registerProvider(name, config)` · `unregisterProvider(name)` · `registerVirtualModel(m)` · `unregisterVirtualModel(provider, id)`|
|MCP|`registerMcpServer(name, config)` · `unregisterMcpServer(name)` · `getMcpServers()`|
|其他|`exec(command, args, options?)` · `getSettings()` · `events`（共享 `EventBus`）|



注册方法写入扩展；动作方法转交给共享运行时。来源：`ExtensionAPI` 接口和 `createExtensionAPI()`，见 `CA/src/core/extensions/loader.ts:244`。



有些行为无法从签名看出：

- `sendUserMessage`：始终触发一个轮次。只有设置 `expandPromptTemplates: true` 时才展开提示词模板和技能命令；默认值为 `false`，见 `CA/src/core/agent-session.ts:2376`。

- `appendEntry`：向会话文件写入一个自定义条目。它绝不会发送给模型；“会话：JSONL 树”（原书第86页）展示了它的结构。

- `setModel`：更改会话模型，但不更改已保存的默认模型；如果提供商没有配置身份验证，则返回 `false`。

- `registerProvider(name, config)`：带有 `models` 时，替换该提供商的所有模型；只有 `baseUrl` 时，重定向现有模型。`unregisterProvider` 会恢复它覆盖的内置模型。`config.apiKey` 的优先级高于 `models.json`，见“配置、模型与身份验证”（原书第99页）。

- `registerMcpServer`：不会持久化；每次加载都要重新注册。`mcp.json` 中的同名服务器优先；如果名称已由另一个扩展注册，则抛出异常，见“MCP”（原书第144页）。

- `getFlag`：如果某个标志不是调用此方法的扩展自己注册的，就返回 `undefined`。

## ToolDefinition



`registerTool()` 接受一个 `ToolDefinition`，见 `CA/src/core/extensions/types.ts:567`。如果定义中的 `parameters` 不是对象模式，`registerTool()` 会拒绝它，见 `CA/src/core/extensions/loader.ts:291`。“内置工具”（原书第81页）展示了使用同一类型构建的内置工具。



`ToolDefinition`，节选，`CA/src/core/extensions/types.ts`

```ts
export interface ToolDefinition<TParams extends TSchema = TSchema, TDetails = unknown, TState = any> {
    name: string;
    label: string;
    description: string;
    promptSnippet?: string;
    promptGuidelines?: string[];
    parameters: TParams;
    constrainedSampling?: false | ConstrainedSamplingConfig;
    renderShell?: "default" | "self";
    prepareArguments?: (args: unknown) => Static<TParams>;
    outputSchema?: TSchema;
    exposure?: ToolExposure;
    namespace?: ToolNamespace;
    annotations?: ToolAnnotations;
    defaultActive?: boolean;
    prepareLoadout?: (loadout: ToolLoadout) => ToolLoadoutChanges | undefined;
    executionMode?: ToolExecutionMode;
    execute(
    toolCallId: string,
    params: Static<TParams>,
    signal: AbortSignal | undefined,
    onUpdate: AgentToolUpdateCallback<TDetails> | undefined,
    ctx: ExtensionToolContext,
    ): Promise<AgentToolResult<TDetails>>;
    renderCall?: (args: Static<TParams>, theme: Theme, context: ToolRenderContext<TState, Static<TParams>>) => Component;
    renderResult?: (...) => Component;
}
```

> 第 567–647 行，移除了所有文档注释，并将 `renderResult` 的参数缩略为 `…`；这些参数分别是 `result`、`options`、`theme` 和 `context`。
> 
> 



- `promptSnippet`：默认系统提示词 `<tools>` 部分中的单行条目。没有此字段的自定义工具不会出现在该部分。

- `promptGuidelines`：工具处于活动状态时，添加到 `<rules>` 部分的项目符号条目。

- `prepareArguments`：在模式验证之前重写原始参数，以兼容旧参数结构。

- `outputSchema`：结果中 `structuredContent` 的模式。codemode 脚本接收的是结构化值，而不是文本。

- `annotations`：`readOnlyHint`、`destructiveHint`、`idempotentHint`、`openWorldHint`，含义与 MCP 中相同。它们来自工具作者，没有任何机制验证它们。

- `defaultActive`：对于 `direct` 和 `model-only` 工具，默认为 `true`；其他暴露方式的工具在注册时绝不会激活。

- `executionMode`：`"sequential"` 或 `"parallel"`；覆盖该工具的默认值，见“智能体循环”（原书第49页）。

- `exposure` 决定模型如何访问工具。“可调用”指的是像 codemode 工具那样，通过 `ctx.executeTool()` 从另一个工具调用，见 `CA/src/core/extensions/types.ts:494`：



|<strong>暴露方式</strong>|<strong>向模型声明</strong>|<strong>可从工具调用</strong>|<strong>说明</strong>|
|---|---|---|---|
|`direct`（默认）|处于活动状态时|处于活动状态时|注册时激活|
|`model-only`|处于活动状态时|从不|用于编排型或交互式工具；注册时激活|
|`codemode`|仅在显式激活时|只要已注册即可|列在 codemode 工具的描述中|
|`deferred`|仅在显式激活时|只要已注册即可|codemode 不列出；工具搜索可以找到它|
|`hidden`|从不|从不|已注册但无法访问；激活它也没有效果|



活动集合恰好就是向模型声明的集合。`setActiveTools()` 会忽略未知名称和隐藏工具名称，见 `CA/src/core/extensions/types.ts:1736`。不存在 `unregisterTool()`。“codemode”（原书第151页）介绍了 `codemode` 和 `deferred` 暴露方式的实际用法。



这对你意味着什么：

- 在工厂函数中注册；在 `session_start` 中启动进程和定时器。

- 为工具和标志起有辨识度的名称；两个扩展之间的重复名称会阻止 CLI 启动。

- 绝不要跨越 `/reload`、`newSession()`、`fork()` 或 `switchSession()` 保留 `pi` 或 `ctx`。

- 使用 `-e ./ext.ts` 测试扩展；它会先于所有已安装扩展加载。



> 来源：`CA/src/core/extensions/types.ts`（`ExtensionFactory`、`ExtensionAPI`、`ToolDefinition`、`ToolExposure`、`ToolAnnotations`）；`CA/src/core/extensions/loader.ts`（`getAliases`、`createExtensionAPI`、`loadExtensionModule`、`initializeExtension`、`clearExtensionCache`）；`CA/src/core/extensions/virtual-modules.ts`；`CA/src/core/extensions/runner.ts`（过期提示消息、`getAllRegisteredTools`）；`CA/src/core/resource-loader.ts`（`reload`、`omitReplacedExtensions`、`detectExtensionConflicts`）；`CA/src/core/package-manager.ts`（`resolveExtensionEntries`、`collectAutoExtensionEntries`）；`CA/src/extensions/index.ts`；`CA/src/main.ts`；`CA/src/core/agent-session.ts`（`reload`、`sendUserMessage`）；`CA/docs/extensions.md`；`research/capture/extensions-conflict.mjs`；`research/out/extensions-conflict.txt`；`research/out/resources-precedence.txt`。
> 
>
