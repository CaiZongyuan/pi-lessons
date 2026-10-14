---
title: Pi 的用途
---

<div class="section-kicker">1.1 / MODEL</div>

# Pi 的用途

---

Pi 是一个小巧的核心，将提示变成模型调用、工具执行和 JSONL 中的各行。产品通常会在此基础上内置的其他功能，例如子智能体、规划模式和权限弹窗，都被有意留给扩展实现。



Pi 是一个终端编码智能体。作者将其描述为“一个极简、可扩展的智能体运行框架，你可以将它打造成自己的工具”（`CA/README.md`）。这句话是一项设计约束，而非口号：核心决定提示如何送达模型、工具如何运行，以及对话如何存储；几乎所有其他决策，都交由你加载的代码处理。本节列出提交 `28dcce2` 中随包提供的内容，从源代码统计各个功能面的规模，并说明核心有意不提供哪些功能。

## 核心提供什么



已发布的包 `@earendil-works/pi-coding-agent` 1\.0\.4 安装一个可执行程序 `pi`（`CA/package.json:9`）。它背后有七个功能面，本书分别用不同部分介绍。



|<strong>功能面</strong>|<strong>提交 `28dcce2` 中的内容</strong>|<strong>位置</strong>|<strong>参见</strong>|
|---|---|---|---|
|LLM 抽象层<br>|10 种聊天传输 API、42 个已知提供商、1 种图像 API、3 种分类器 API|`ai/types.ts:17`、`ai/compat.ts:180`|提供商与模型（原书第 24 页）、传输 API 与跨提供商交接（原书第 36 页）|
|智能体循环<br>|无状态的 `runLoop`，带引导消息和后续消息队列；有状态的 `Agent` 封装|`agent/agent-loop.ts:163`、`agent/agent.ts:188`|智能体循环（原书第 49 页）|
|会话运行时|`AgentSession`：提示处理流水线、重试、压缩、持久化|`CA/src/core/agent-session.ts:1954`|`AgentSession`：组装运行时（原书第 61 页）|
|工具|默认启用 4 个（`read`、`bash`、`edit`、`write`）；共 8 个内置工具<br>|`CA/src/core/settings-manager.ts:215`、`CA/src/core/tools/index.ts:95`|内置工具（原书第 81 页）|
|会话|树形结构、仅追加的 JSONL；自动压缩，默认开启|`CA/src/core/session-manager.ts:1172`、`CA/src/core/compaction/compaction.ts:127`|会话：JSONL 树（原书第 86 页）、压缩与分支摘要（原书第 92 页）|
|扩展 API|41 个可订阅事件、31 个方法、一个共享事件总线|`CA/src/core/extensions/types.ts:1553`|扩展：加载与 API（原书第 113 页）、扩展事件与上下文（原书第 120 页）|
|运行模式|交互式 TUI、print（`-p`）、JSON、RPC，以及进程内 SDK|`CA/src/main.ts:112`|运行模式（原书第 127 页）、RPC 模式与 SDK（原书第 133 页）|



七个功能面的数量都依据源代码统计。下一小节说明统计规则。



另有四项能力通过内置扩展提供，而非核心代码。CLI 将 `lama.cpp`、`codemode`、`toolsearch` 和 `mcp` 注册为内联扩展，后三个标为可替换：“注册 `codemode`、`tool_search` 或 `/mcp` 的扩展……会接管功能，而不是与内置扩展并行运行”（`CA/src/extensions/index.ts:7`）。codemode 在编译为 WebAssembly 的 QuickJS 中运行模型编写的 JavaScript，其中“唯一的能力是调用注入的工具”（`codemode/package.json`）。codemode（原书第 151 页）介绍这一机制，MCP（原书第 144 页）介绍 MCP 客户端。

## 这些数量如何统计



上表中的每个数字都来自检出版本，并且都依赖某项统计规则。规则改变，数字也会改变，因此这里明确列出规则：

- <strong>传输 API：10 种。</strong> 统计 `KnownApi` 联合类型中的成员（`ai/types.ts:17`），它们对应加载时注册到 `BUILTIN_APIS` 的十个条目（`ai/compat.ts:180`）。`KnownImageApi` 另加 `openrouter-images`，`KnownClassifierApi` 另加三种分类器 API（`ai/types.ts:31`）；两者都不是聊天 API。不能用 `ai/api/` 中的 40 个文件来计数：其中 15 个是 `.lazy.ts` 加载器，另一些是共享辅助模块（`research/out/stats.txt` 的 `§api-files`）。

- <strong>提供商：42 个。</strong> 统计 `KnownProvider` 联合类型中的成员（`ai/types.ts:39`）。其集合与 42 个 `ai/providers/*.models.ts` 目录文件完全一致（`research/out/stats.txt` 的 `§provider-files`）。仅用于测试的 `faux` 提供商不在这两者之中。

- <strong>工具：4 \+ 4 个。</strong> `DEFAULT_TOOL_NAMES` 为 `["read", "bash", "edit", "write"]`（`CA/src/core/settings-manager.ts:215`）。`ToolName` 联合类型再加上 `powershell`、`grep`、`find` 和 `ls`，共八个内置工具（`CA/src/core/tools/index.ts:95`）。内置扩展提供的 `tool_search` 工具注册时未激活，因此不计入。

- <strong>扩展事件：41 个。</strong> 统计 `ExtensionAPI` 的 `on()` 重载接受的不同事件名（`CA/src/core/extensions/types.ts:1558`）。`ExtensionEvent` 联合类型只有 32 个成员（`CA/src/core/extensions/types.ts:1366`），因为所有会话事件被合并到一个 `SessionEvent` 成员中。

- <strong>扩展方法：31 个。</strong> 统计 `ExtensionAPI` 除 `on` 之外的不同方法名，从 `registerTool` 到 `unregisterVirtualModel`（`CA/src/core/extensions/types.ts:1632`）。重载只算一次。`events` 属性是一个共享 `EventBus`，不是方法（`CA/src/core/extensions/types.ts:1878`）。

- <strong>运行模式：4 种。</strong> `resolveAppMode` 从四种应用模式中选择一种：`--mode` 指定的 `rpc` 和 `json`；使用 `-p`，或 stdin 或 stdout 不是终端时选用的 `print`；其他情况为 `interactive`（`CA/src/main.ts:112`）。因此，单独使用 `--mode text` 并不会选择 print：在终端中它仍会打开 TUI。Print 与 JSON 共用一个运行器 `runPrintMode`，其输出模式为 `"text" | "json"`（`CA/src/modes/print-mode.ts:20`）。SDK 是另一种入口：在自己的进程中调用 `createAgentSession()`（`CA/src/core/sdk.ts`）。因此，项目首页会写成“四种模式：交互式、print/JSON、RPC 和 SDK”。

## 有意不提供什么



`pi.dev` 首页有一节名为“我们没有构建的功能”。它列出五项功能，其中四项在仓库中有参考扩展。



五项未内置功能中的四项有仓库内的参考扩展；后台 bash 没有。左侧：提交 `28dcce2` 的核心代码。中间：`builtInExtensions`（`CA/src/extensions/index.ts:7`）。右侧：将 `pi.dev` 中“我们没有构建的功能”列表与 `CA/examples/extensions/` 对照。示意图。



<BookFigure id="1.1" />

> Pi 核心、内置扩展和有意留给扩展实现的功能
> 
> 



首页针对每项未提供的功能，都给出了具体建议：

- 对于子智能体：“通过 tmux 启动 Pi 实例，或使用扩展构建自己的实现”。

- 对于权限弹窗：“在容器中运行，或构建自己的确认流程”。

- 对于规划模式：“将计划写入文件”。

- 对于待办事项，建议在项目中放一个 Markdown 文件。

- 对于后台 bash，它只说：“使用 tmux。完全可观察，可直接交互。”同一页面还将 MCP 列为曾经未提供的功能，划去旧内容并替换成“现在支持 MCP\+Codemode”。



> `CA/examples/extensions/` 包含 80 个条目：70 个单文件 `.ts` 扩展、9 个目录，以及一个 `README.md`（`research/out/stats.txt` 的 `§example-extensions`）。也就是 79 个示例；首页写的是“50\+”。
> 
> 



> <strong>为什么这很重要</strong>
> 
> 每一项省略都留下了一个扩展接入点。权限关卡就是一个返回 `{ block: true }` 的 `tool_call` 处理器；规划模式就是一个 `before_agent_start` 处理器加上一条命令。在要求将某项功能加入核心之前，请先在“扩展事件与上下文”（原书第 120 页）中寻找能承载它的事件，并到 `CA/examples/extensions/` 中寻找参考实现。
> 
> 



> <strong>这对你意味着什么：</strong>
> 
> - 在加载扩展之前，只应期待 Pi 调用模型、运行工具和写入 JSONL
> 
> - 按 `KnownProvider` 统计提供商，按 `KnownApi` 统计传输 API；以 `ai/` 中的文件数量统计，两者都会偏高
> 
> - 实现缺失功能时，从 `CA/examples/extensions/` 中最接近需求的文件入手
> 
> - 将 `mcp`、`codemode` 和 `tool-search` 视为可替换的默认实现，而非核心
> 
> 



> 来源：`CA/README.md`；`CA/package.json`（`name`、`version`、`bin`）。`ai/types.ts`（`KnownApi`、`KnownImageApi`、`KnownClassifierApi`、`KnownProvider`）；`ai/compat.ts`（`BUILTIN_APIS`）；`agent/agent-loop.ts`（`runLoop`）；`agent/agent.ts`（`Agent`）。`CA/src/main.ts`（`resolveAppMode`）；`CA/src/modes/print-mode.ts`；`CA/src/core/settings-manager.ts`（`DEFAULT_TOOL_NAMES`）；`CA/src/core/tools/index.ts`（`ToolName`）；`CA/src/core/compaction/compaction.ts`（`DEFAULT_COMPACTION_SETTINGS`）；`CA/src/core/extensions/types.ts`（`ExtensionEvent`、`ExtensionAPI`）；`CA/src/cli/args.ts`（`Mode`）；`CA/src/modes/index.ts`。`CA/src/extensions/index.ts`（`builtInExtensions`）；`codemode/package.json`（`description`、`quickjs-wasi`）；`CA/examples/extensions/`。`pi.dev` 首页，抓取于 2026 年 10 月 5 日（“Four modes”“What we didn’t build”）；`research/out/stats.txt`（`§provider-files`、`§api-files`、`§example-extensions`）。
> 
>
