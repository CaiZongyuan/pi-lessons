A small core that turns one prompt into model calls, tool runs and JSONL lines, with almost everything else left to extensions.

一个小内核，把一句提示词变成模型调用、工具运行和 JSONL 行，除此之外几乎全部留给扩展。

![](images/e6f26104eb453e2b55b900f324b44da14eec4d64a5a680ad5eb71ad4614af91a.jpg)

## 1.1 What Pi is for

## 1.1 Pi 要解决什么

Pi is a small core that turns a prompt into model calls, tool runs and JSONL lines. Everything a product would bake in on top of that — sub-agents, plan mode, permission popups — is left to extensions on purpose.

Pi 是一个小内核，把一句提示词变成模型调用、工具运行和 JSONL 行。产品通常会在这个内核之上做进去的一切——子智能体、计划模式、权限弹窗——都是有意留给扩展的。

Pi is a terminal coding agent whose authors describe it as “a minimal, extensible agent harness that you can make your own” CA/README.md. That sentence is a design constraint, not a slogan: the core decides how a prompt reaches a model, how tools run and how the conversation is stored, and it hands nearly every other decision to code you load. This section lists what ships at commit 28dcce2, counts each surface from the source, and names the features the core leaves out.

Pi 是一个终端编码智能体，作者这样描述它：“一个极简、可扩展、你可以改造成自己模样的智能体框架” CA/README.md。这句话是一条设计约束，不是口号：内核决定提示词如何抵达模型、工具如何运行、会话如何存储，而几乎所有其他决定都交给你加载的代码。本节列出 commit 28dcce2 时发布的内容，逐项从源码中统计，并点名内核刻意不做的功能。

## What the core ships

## 内核发布什么

The published package @earendil-works/pi-coding-agent 1.0.4 installs one binary, pi CA/package.json:9. Behind it sit seven things, each owned by one part of this book.

发布的包 @earendil-works/pi-coding-agent 1.0.4 只安装一个二进制文件，pi CA/package.json:9。它背后有七样东西，每一样都由本书的一个部分负责。

<table><tr><td>功能面</td><td>28dce2 时</td><td>位置</td><td>参见</td></tr><tr><td>LLM 抽象</td><td>10 个对话通信API、42 个已知供应商、1 个图像 API、3 个分类 API</td><td>ai/types.ts:17, ai/compat.ts:180</td><td>供应商与模型（p. 24）、通信API 与跨供应商转交（p. 36）</td></tr><tr><td>智能体循环</td><td>无状态 runLoop，带转向队列和后续队列；有状态 Agent 包装器</td><td>agent/agent-loop.ts:163, agent/agent.ts:188</td><td>智能体循环（p. 49）</td></tr><tr><td>Session 运行时</td><td>AgentSession：提示词流水线、重试、压缩、持久化</td><td>CA/src/core/agent-session.ts:1954</td><td>AgentSession：接好运行时（p. 61）</td></tr><tr><td>工具</td><td>默认启用 4 个（read、bash、edit、write）；内置 8 个</td><td>CA/src/core/settings-manager.ts:215, CA/src/core/tools/index.ts:95</td><td>内置工具（p. 81）</td></tr><tr><td>Session</td><td>树形结构、仅追加 JSONL；自动压缩，默认开启</td><td>CA/src/core/session-manager.ts:1172, CA/src/core/compaction/compaction.ts:127</td><td>Session、JSONL 树（p. 86）、压缩与分支摘要（p. 92）</td></tr><tr><td>扩展 API</td><td>41 个可订阅事件、31 个方法、一个共享事件总线</td><td>CA/src/core/extensions/types.ts:1553</td><td>扩展、加载与 API（p. 113）、扩展事件与上下文（p. 120）</td></tr><tr><td>运行模式</td><td>交互式 TUI、打印（-p）、JSON、RPC，以及进程内 SDK</td><td>CA/src/main.ts:112</td><td>运行模式（p. 127）、RPC 模式与 SDK（p. 133）</td></tr></table>

Seven surfaces, each counted from the source. The counting rules are in the next subsection.

七个功能面，每个数字都从源码里数出来。统计规则见下一小节。

Four more capabilities arrive as built-in extensions rather than core code. The CLI registers lama.cpp, codemode, toolsearch and mcp as inline extensions, and the last three are marked replaceable: “an extension that registers codemode, tool_search, or /mcp … takes over instead of running alongside the built-in one” CA/src/extensions/index.ts:7. Codemode runs model-written JavaScript in QuickJS compiled to WebAssembly, where “the only capability is calling injected tools” codemode/package.json; codemode (p. 151) covers it, and MCP (p. 144) covers the MCP client.

另外四项能力以内置扩展的形式提供，而不是写在内核代码里。CLI 把 llama.cpp、codemode、toolsearch 和 mcp 注册为内联扩展，后三者标记为可替换：“注册 codemode、tool_search 或 /mcp 的扩展……会取而代之，而不是与内置的那个并行运行” CA/src/extensions/index.ts:7。Codemode 在编译为 WebAssembly 的 QuickJS 中运行模型写的 JavaScript，那里“唯一的能力是调用注入进来的工具” codemode/package.json；codemode（p. 151）讲这一块，MCP（p. 144）讲 MCP 客户端。

## How the counts were made

## 这些数字是怎么来的

Every number in the table above was read from the checkout, and each one depends on a counting rule. Change the rule and the number changes, so the rules are stated here.

上表中的每个数字都是从这份检出里读出来的，而每个数字都取决于一条统计规则。规则一改，数字就变，所以规则写在这里。

Wire APIs: 10. The members of the KnownApi union ai/types.ts:17, which match the ten entries of BUILTIN_APIS registered at load ai/compat.ts:180. KnownImageApi adds openrouter-images and KnownClassifierApi adds three classifier APIs ai/types.ts:31; neither is a chat API. The 40 files in ai/api/ are not the count: 15 of them are .lazy.ts loaders and others are shared helpers research/out/stats.txt §api-files.

通信API：10 个。即 KnownApi 联合类型的成员 ai/types.ts:17，与加载时注册的 BUILTIN_APIS 十个条目一致 ai/compat.ts:180。KnownImageApi 增加 openrouter-images，KnownClassifierApi 增加三个分类 API ai/types.ts:31；两者都不是对话 API。ai/api/ 下的 40 个文件不是这个数：其中 15 个是 .lazy.ts 加载器，其余是共享辅助文件 research/out/stats.txt §api-files。

Providers: 42. The members of the KnownProvider union ai/types.ts:39. The set is identical to the 42 ai/providers/*.models.ts catalogue files research/out/stats.txt §provider-files. The test-only faux provider is in neither.

供应商：42 个。即 KnownProvider 联合类型的成员 ai/types.ts:39。这个集合与 ai/providers/*.models.ts 目录文件的 42 个完全一致 research/out/stats.txt §provider-files。仅供测试的 faux 供应商两处都不算。

Tools: 4 + 4. DEFAULT_TOOL_NAMES is ["read", "bash", "edit", "write"] CA/src/core/settings-manager.ts:215. The ToolName union adds powershell, grep, find and ls for eight built-in tools CA/src/core/tools/index.ts:95. The tool_search tool from the built-in extension is registered inactive and is not counted.

工具：4 + 4。DEFAULT_TOOL_NAMES 是 ["read", "bash", "edit", "write"] CA/src/core/settings-manager.ts:215。ToolName 联合类型再加上 powershell、grep、find 和 ls，共八个内置工具 CA/src/core/tools/index.ts:95。内置扩展带来的 tool_search 工具注册为未激活，不计入。

Extension events: 41. The distinct event names accepted by the on() overloads of ExtensionAPI CA/src/core/extensions/types.ts:1558. The ExtensionEvent union has 32 members CA/src/core/extensions/types.ts:1366 because it folds all session events into one SessionEvent member.

扩展事件：41 个。即 ExtensionAPI 的 on() 各重载所接受的不同事件名 CA/src/core/extensions/types.ts:1558。ExtensionEvent 联合类型有 32 个成员 CA/src/core/extensions/types.ts:1366，因为它把所有会话事件折叠进一个 SessionEvent 成员。

Extension methods: 31. The distinct method names of ExtensionAPI other than on, from register Tool to unregisterVirtualModel CA/src/core/extensions/types.ts:1632. Overloads count once. The events property, a shared EventBus, is not a method CA/src/core/extensions/types.ts:1878.

扩展方法：31 个。即 ExtensionAPI 除 on 之外的不同方法名，从 registerTool 到 unregisterVirtualModel CA/src/core/extensions/types.ts:1632。重载只算一次。events 属性是一个共享的 EventBus，不算方法 CA/src/core/extensions/types.ts:1878。

Run modes: 4. resolveAppMode picks one of four app modes: rpc and json from --mode, print from -p or when stdin or stdout is not a terminal, and interactive otherwise CA/src/main.ts:112. --mode text alone therefore does not select print: at a terminal it still opens the TUI. Print and JSON share one runner, runPrintMode, whose output mode is "text" | "json" CA/src/modes/print-mode.ts:20. The SDK is the other way in: createAgentSession() in your own process CA/src/core/sdk.ts. Hence the landing page’s “Four modes: interactive, print/JSON, RPC, and SDK”.

运行模式：4 种。resolveAppMode 从四种应用模式中选一种：rpc 和 json 来自 --mode，print 来自 -p 或 stdin/stdout 不是终端，其他情况是 interactive CA/src/main.ts:112。所以单写 --mode text 并不会选中 print：在终端下它仍然打开 TUI。print 和 JSON 共用一个运行器 runPrintMode，其输出模式是 "text" | "json" CA/src/modes/print-mode.ts:20。SDK 是另一个入口：在你自己的进程里调 createAgentSession() CA/src/core/sdk.ts。于是落地页上写的是“四种模式：交互式、print/JSON、RPC 和 SDK”。

## What is left out on purpose

## 刻意不做的部分

The pi.dev landing page has a section titled “What we didn’t build”. It names five features, and the repository ships a reference extension for four of them.

pi.dev 落地页有一节叫“我们没做什么”。它点名五项功能，仓库为其中四项提供了参考扩展。

Four of the five omitted features have a reference extension in the repository; background bash has none. Left: core code at 28dcce2. Centre: builtInExtensions CA/src/extensions/index.ts:7. Right: the list under “What we didn’t build” on pi.dev, matched against CA/examples/extensions/. Schematic.

五项被略去的功能中有四项在仓库里配有参考扩展；后台 bash 没有。左侧：28dcce2 时的内核代码。中间：builtInExtensions CA/src/extensions/index.ts:7。右侧：pi.dev 上“我们没做什么”下面的清单，与 CA/examples/extensions/ 对照。示意图。

![](images/a72a03c74a5d5658a8ff43e8294a8e4326ea5df66048b77b3682547cb5d35a6e.jpg)

The page’s advice for each omission is concrete. For sub-agents: “Spawn Pi instances via tmux, or build your own with extensions”. For permission popups: “Run in a container, or build your own confirmation flow”. For plan mode: “Write plans to files”. For to-dos, it suggests a Markdown file in the project. For background bash it gives only “Use tmux. Full observability, direct interaction.” The same page lists MCP as a former omission, struck through and replaced by “Now with MCP+Codemode”.

这一页对每项省略给出的建议都很具体。对子智能体：“用 tmux 起 Pi 实例，或者用扩展自己造一个”。对权限弹窗：“跑在容器里，或者自己写一套确认流程”。对计划模式：“把计划写到文件里”。对待办清单，它建议在项目里放一个 Markdown 文件。对后台 bash，它只给了“用 tmux。可观测性完整，直接交互。”同一页还把 MCP 列为曾经的省略项，划掉后换成“现已支持 MCP+Codemode”。

CA/examples/extensions/ holds 80 entries: 70 single-file .ts extensions, 9 directories and a README.md research/out/stats.txt §example-extensions. That is 79 examples; the landing page says “50+”.

CA/examples/extensions/ 下有 80 个条目：70 个单文件 .ts 扩展、9 个目录和一份 README.md research/out/stats.txt §example-extensions。这是 79 个示例；落地页上写的是“50+”。

## W H Y I T M A T T E R S

## 为什么重要

Every omission is a seam. A permission gate is a tool_call handler that returns { block: true }; a plan mode is a before_agent_start handler plus a command. Before you ask for a feature in core, look for the event that would carry it in extension events and contexts (p. 120) and for a reference implementation in CA/examples/extensions/.

每一处省略都是一道接缝。一个权限门就是一个返回 { block: true } 的 tool_call 处理器；一个计划模式就是一个 before_agent_start 处理器加一条命令。在你要求把某个功能做进内核之前，先到扩展事件与上下文（p. 120）里找能承载它的事件，再到 CA/examples/extensions/ 里找参考实现。

## W H A T T H I S M E A N S F O R Y O U

## 这对你意味着什么

Expect Pi to call a model, run tools and write JSONL, and nothing more, until you load extensions.

在加载扩展之前，只管期待 Pi 调用模型、运行工具、写 JSONL，仅此而已。

Count providers by KnownProvider and wire APIs by KnownApi; file counts in ai/ overstate both.

供应商按 KnownProvider 数，通信API 按 KnownApi 数；ai/ 下的文件数会把两者都算大。

Start a missing feature from the nearest file in CA/examples/extensions/.

缺某个功能时，从 CA/examples/extensions/ 里最接近的那个文件开始。

Treat mcp, codemode and tool-search as defaults you can replace, not as core.

把 mcp、codemode 和 tool-search 当作可以替换的默认值，而不是内核。

Sources: CA/README.md; CA/package.json (name, version, bin). ai/types.ts (KnownApi, KnownImageApi, KnownClassifierApi, KnownProvider); ai/compat.ts (BUILTIN_APIS); agent/agent-loop.ts (run Loop); agent/agent.ts (Agent). CA/src/main.ts (resolveAppMode); CA/src/modes/print-mode.ts; CA/src/core/settings-manager.ts (DEFAULT_TOOL_NAMES); CA/src/core/tools/index.ts (ToolName); CA/src/core/compaction/compaction.ts (DEFAULT_COMPACTION_SETTINGS); CA/src/core/extensions/types.ts (ExtensionEvent, ExtensionAPI); CA/src/cli/args.ts (Mode); CA/src/modes/index.ts. CA/src/extensions/index.ts (builtInExtensions); codemode/package.json (description, quickjs-wasi); CA/examples/extensions/. pi.dev landing page, fetched 5 October 2026 (“Four modes”, “What we didn’t build”); research/out/stats.txt (§provider-files, §api-files, §example-extensions)

来源：CA/README.md；CA/package.json（name、version、bin）。ai/types.ts（KnownApi、KnownImageApi、KnownClassifierApi、KnownProvider）；ai/compat.ts（BUILTIN_APIS）；agent/agent-loop.ts（runLoop）；agent/agent.ts（Agent）。CA/src/main.ts（resolveAppMode）；CA/src/modes/print-mode.ts；CA/src/core/settings-manager.ts（DEFAULT_TOOL_NAMES）；CA/src/core/tools/index.ts（ToolName）；CA/src/core/compaction/compaction.ts（DEFAULT_COMPACTION_SETTINGS）；CA/src/core/extensions/types.ts（ExtensionEvent、ExtensionAPI）；CA/src/cli/args.ts（Mode）；CA/src/modes/index.ts。CA/src/extensions/index.ts（builtInExtensions）；codemode/package.json（description、quickjs-wasi）；CA/examples/extensions/。pi.dev 落地页，2026 年 10 月 5 日获取（“Four modes”、“What we didn’t build”）；research/out/stats.txt（§provider-files、§api-files、§example-extensions）

## 1.2 The monorepo in one page

## 1.2 单页看懂这个 monorepo

The repository holdsfourteen packages, but the pi command runs on a chain of three — pi-coding-agent, pi-agent-core, pi-ai. Five of the others serve an experimental stack that installing the CLI from npm never pulls in.

仓库里有十四个包，但 pi 命令跑在一条三个包的链上——pi-coding-agent、pi-agent-core、pi-ai。其余包中有五个服务于一整套实验栈，从 npm 安装 CLI 时永远不会拉下来。

A reader opening packages/ meets fourteen directories and no map. Half of them are not on the path of a prompt in the stable CLI. This section lists every package with its size and role, draws the dependency graph from each package.json as layers, and shows exactly how the experimental packages are kept out of what npm and the standalone binary ship.

打开 packages/ 的读者会看到十四个目录，却没有任何地图。其中一半不在稳定 CLI 的提示词路径上。本节列出每个包的规模与职责，把每个 package.json 画成分层依赖图，并准确说明实验包是怎么被挡在 npm 包和独立二进制之外的。

## Fourteen packages

## 十四个包

Every package is at version 1.0.4 and all but one are public research/out/stats.txt §package-lines.

每个包都是 1.0.4 版，除一个之外都是公开的 research/out/stats.txt §package-lines。

<table><tr><td>目录</td><td>npm 包</td><td>文件数</td><td>行数</td><td>职责</td></tr><tr><td>packages/coding-agent</td><td>@earendil-works/pi-coding-agent</td><td>297</td><td>77,340</td><td>pi CLI：Session、工具、扩展、运行模式、TUI 应用</td></tr><tr><td>packages/ai</td><td>@earendil-works/pi-ai</td><td>151</td><td>23,581</td><td>供应商与模型、流式事件协议、认证、OAuth</td></tr><tr><td>packages/durable</td><td>@earendil-works/pi-durable</td><td>65</td><td>18,338</td><td>实验性的持久化会话、任务与文档运行时</td></tr><tr><td>packages/tui</td><td>@earendil-works/pi-tui</td><td>45</td><td>17,134</td><td>差分渲染终端 UI 库</td></tr><tr><td>packages/chord</td><td>@earendil-works/chord</td><td>29</td><td>8,136</td><td>组合运行时：facet、service、复制状态、RPC</td></tr><tr><td>packages/mcp</td><td>@earendil-works/pi-mcp</td><td>18</td><td>2,907</td><td>独立 MCP 客户端：stdio 与 Streamable HTTP、OAuth</td></tr><tr><td>packages/agent</td><td>@earendil-works/pi-agent-core</td><td>6</td><td>2,281</td><td>无状态智能体循环与有状态 Agent 包装器</td></tr><tr><td>packages/env</td><td>@earendil-works/pi-env</td><td>6</td><td>1,928</td><td>通过 SSH 为 Pi Durable 提供的远程 ExecutionEnv</td></tr><tr><td>packages/server</td><td>@earendil-works/pi-server</td><td>16</td><td>1,800</td><td>实验性的 Unix 套接字 Session 路由</td></tr><tr><td>packages/codemode</td><td>@earendil-works/pi-codemode</td><td>10</td><td>1,696</td><td>QuickJS-in-WebAssembly 脚本沙箱</td></tr><tr><td>packages/evals</td><td>@earendil-works/pi-evals（private）</td><td>5</td><td>1,345</td><td>vitest-evals 测试框架</td></tr><tr><td>packages/client</td><td>@earendil-works/pi-client</td><td>8</td><td>1,046</td><td>面向远程 Pi Session 的实验性客户端</td></tr><tr><td>packages/telemetry</td><td>@earendil-works/pi-telemetry</td><td>6</td><td>826</td><td>厂商中立的 span 契约，不含 exporter</td></tr><tr><td>packages/protocol</td><td>@earendil-works/pi-protocol</td><td>8</td><td>790</td><td>实验性的 CBOR 分帧协议，第 8 版</td></tr><tr><td>合计</td><td></td><td>670</td><td>159,148</td><td></td></tr></table>

pi-coding-agent is 48.6 percent of the code; the loop it runs on is 1.4 percent. LINES counts non-blank lines of *.ts, *.tsx and *.rs files under each package’s src/, excluding *.test.*, *.d.ts and the generated *.models.ts catalogues. From research/capture/stats.py at 28dcce2.

pi-coding-agent 占代码的 48.6%；它跑的那个循环占 1.4%。LINES 统计每个包 src/ 下 *.ts、*.tsx 和 *.rs 文件的非空行，排除 *.test.*、*.d.ts 以及生成的 *.models.ts 目录文件。来自 28dcce2 时的 research/capture/stats.py。

The counting rule leaves three things out, and each is large. The model catalogue lives in 42 JSON files under ai/src/providers/data/ and in 420 lines of generated *.models.ts. pi-tui ships prebuilt native addons for six platform targets under tui/native/, outside src/. The pi-env daemon is a Rust crate under env/daemon/, also outside src/. Roles in the table come from each package’s description field, its README, and one file checked per claim: PROTOCOL_VERSION = 8protocol/src/protocol.ts:5, the Unix-socket listener server/src/transports/unix/listener.ts:57, the two MCP transports mcp/src/transports/stdio.ts, and “no exporter” in the telemetry README telemetry/README.md:11.

这条统计规则把三样东西排除在外，而且每一项都很大。模型目录在 ai/src/providers/data/ 下的 42 个 JSON 文件里，以及生成的 420 行 *.models.ts 里。pi-tui 在 src/ 之外的 tui/native/ 下为六个平台目标提供预编译原生插件。pi-env 守护进程是 env/daemon/ 下的一个 Rust crate，同样在 src/ 之外。表中的职责来自各包的 description 字段、它的 README，以及每条说法核对过的一个文件：PROTOCOL_VERSION = 8 protocol/src/protocol.ts:5、Unix 套接字监听器 server/src/transports/unix/listener.ts:57、两个 MCP 传输实现 mcp/src/transports/stdio.ts，以及 telemetry README 中的 “no exporter” telemetry/README.md:11。

![](images/d2382d1d217d2cbf1d4c3f310c1331cbb735c1a5c51cd9511fc47934442d3234.jpg)

The CLI is bigger than everything it depends on combined. Blue: packages the stable pi command imports. Grey: packages that only the experimental stack or the eval harness uses. From research/out/stats.txt (§package-lines).

CLI 比它依赖的所有东西加起来还大。蓝色：稳定 pi 命令导入的包。灰色：只有实验栈或评测框架使用的包。来自 research/out/stats.txt（§package-lines）。

## The dependency graph, as layers

## 依赖图的分层

The graph below uses only dependencies entries that name another @earendil-works/* package. No package declares a peer or optional dependency on another. Sorting packages by the longest chain beneath them gives five layers.

下图只使用指向另一个 @earendil-works/* 包的 dependencies 条目。没有任何包声明对另一个包的 peer 或 optional 依赖。按各包之下的最长链条排序，得到五层。

![](images/fe868b83e343a6937f960f96b41fc7814447bc6720d99f8792b43fe2317a091c.jpg)

The stable CLI runs on a chain of three packages. Solid: pi-coding-agent → pi-agent-core → pi-ai. Blue: everything else the stable CLI imports. Hatched grey: packages reached only by experimental code, dev dependencies or the private eval harness. Read from the dependencies and dev Dependencies of all fourteen package.json files at 28dcce2.

稳定 CLI 跑在一条三个包的链上。实线：pi-coding-agent → pi-agent-core → pi-ai。蓝色：稳定 CLI 导入的其他一切。灰色斜线填充：只有实验代码、开发依赖或私有评测框架才会到达的包。读自 28dcce2 时十四个 package.json 文件的 dependencies 与 devDependencies。

Three edges in the figure are not ordinary runtime dependencies. pi-coding-agent lists pi-client, pi-protocol and piserver under dev Dependencies only. Twenty files under CA/src/experimental/ import @earendil-works/pi-durable, which the package does not declare at all; the import resolves because the root package.json makes every directory under packages/ an npm workspace. And chord, although a declared runtime dependency of the CLI, is imported only by files under CA/src/experimental/: a grep of CA/src/ for the package name finds 26 files, all in that directory. pi-env has no importer anywhere in the repository outside its own tests.

图中有三条边不是普通的运行时依赖。pi-coding-agent 只在 devDependencies 里列了 pi-client、pi-protocol 和 pi-server。CA/src/experimental/ 下的二十个文件 import 了 @earendil-works/pi-durable，而这个包根本没声明它；import 能解析成功，是因为根 package.json 把 packages/ 下的每个目录都做成了 npm workspace。而 chord 虽然是 CLI 声明过的运行时依赖，却只被 CA/src/experimental/ 下的文件 import：在 CA/src/ 里 grep 这个包名会找到 26 个文件，全在该目录中。pi-env 在整个仓库里除了自己的测试之外没有任何地方 import 它。

## Runtime and binary

## 运行时与二进制

Thirteen packages require Node >=22.19.0 in engines ai/package.json:99; the private pi-evals declares none. The npm package installs pi as dist/bundle/cli.js CA/package.json:10. The build:binary script compiles a standalone executable with Bun: bun build --compile … --outfile dist/pi CA/package.json:43. The native terminal addons of pi-tui are described in pi-tui (p. 158).

十三个包在 engines 里要求 Node >=22.19.0 ai/package.json:99；私有的 pi-evals 没声明任何要求。npm 包把 pi 安装为 dist/bundle/cli.js CA/package.json:10。build:binary 脚本用 Bun 编译出一个独立可执行文件：bun build --compile … --outfile dist/pi CA/package.json:43。pi-tui 的原生终端插件在 pi-tui（p. 158）里介绍。

## What PI_EXPERIMENTAL gates

## PI_EXPERIMENTAL 控制什么

One function holds the switch:

开关握在一个函数手里：

```typescript the experimental switch CA/src/core/experimental.ts TS export function areExperimentalFeaturesEnabled(): boolean {
    return process.env.PI_EXPERIMENTAL === "1";
}
```

The whole file, three lines.

整个文件就三行。

The value must be exactly "1"; true or yes leave it of. Three things read the switch. runExperimentalCommand returns false unless it is on and the first argument is server or client CA/src/experimental/commands.ts:86. The interactive footer CA/src/modes/interactive/components/footer.ts:213 and first-time setup CA/src/cli/startup-ui.ts:141 check it. The switch alone does not reach the experimental code from an npm install, because the files list of the package excludes !dist/client, !dist/experimental and !dist/cli/experimental CA/package.json:31. The services README states the intent: “The server, client, and experimental package subpaths are excluded from npm packages and standalone binaries” CA/src/experimental/services/README.md. The experimental entry point is CA/src/experimental/cli.ts, which ./pitest.sh runs from a source checkout pi-test.sh; the path from there is the subject of the experimental stack (p. 166).

取值必须严格是 "1"；true 或 yes 都不生效。有三处读这个开关。runExperimentalCommand 除非开关打开且第一个参数是 server 或 client，否则返回 false CA/src/experimental/commands.ts:86。交互式页脚 CA/src/modes/interactive/components/footer.ts:213 和首次启动向导 CA/src/cli/startup-ui.ts:141 都会检查它。仅靠这个开关并不能从 npm 安装中触达实验代码，因为包的 files 列表排除了 !dist/client、!dist/experimental 和 !dist/cli/experimental CA/package.json:31。services 的 README 说明了意图：“server、client 和 experimental 这些包子路径不包含在 npm 包和独立二进制里” CA/src/experimental/services/README.md。实验入口点是 CA/src/experimental/cli.ts，./pitest.sh 在源码检出中运行它 pi-test.sh；从那里开始的路径属于实验栈那一节（p. 166）。

## R U L E O F T H U M B

## 经验法则

If a file you are reading imports pi-durable, pi-server, pi-client, pi-protocol or chord, it is not on the path of the stable pi command. For the stable CLI, read pi-coding-agent, pi-agent-core and pi-ai first; then pi-tui, pi-mcp and pi-codemode when the question is about the screen, MCP or codemode.

如果你正在读的文件 import 了 pi-durable、pi-server、pi-client、pi-protocol 或 chord，它就不在稳定 pi 命令的路径上。要读稳定 CLI，先读 pi-coding-agent、pi-agent-core 和 pi-ai；当问题涉及屏幕、MCP 或 codemode 时，再读 pi-tui、pi-mcp 和 pi-codemode。

Sources: packages/*/package.json (name, version, private, dependencies, dev Dependencies, engines, description); CA/package.json (bin, files, build:binary); package.json (workspaces); CA/src/core/experimental.ts; CA/src/experimental/commands.ts (runExperimentalCommand); CA/src/experimental/cli.ts; CA/src/cli/startup-ui.ts (shouldRunFirstTimeSetup); CA/src/experimental/services/README.md; pi-test.sh; protocol/src/protocol.ts (PROTOCOL_VERSION); server/src/transports/unix/listener.ts; mcp/src/transports/; telemetry/README.md; research/capture/stats.py; research/out/stats.txt (§package-lines)

来源：packages/*/package.json（name、version、private、dependencies、devDependencies、engines、description）；CA/package.json（bin、files、build:binary）；package.json（workspaces）；CA/src/core/experimental.ts；CA/src/experimental/commands.ts（runExperimentalCommand）；CA/src/experimental/cli.ts；CA/src/cli/startup-ui.ts（shouldRunFirstTimeSetup）；CA/src/experimental/services/README.md；pi-test.sh；protocol/src/protocol.ts（PROTOCOL_VERSION）；server/src/transports/unix/listener.ts；mcp/src/transports/；telemetry/README.md；research/capture/stats.py；research/out/stats.txt（§package-lines）

# 1.3 The life of one prompt

# 1.3 一句提示词的一生

One answered question that needs one file read is two model calls, 29 session events and 8 JSONL lines. The prompt reaches the disk before it reaches the model, and the run is over at agent_settled, not at agent_end.

一个只需要读一次文件就能回答的问题，是两次模型调用、29 个会话事件和 8 行 JSONL。提示词先落盘，然后才到达模型；一次运行结束于 agent_settled，而不是 agent_end。

You type “What does hello.txt say?” and press Enter. Before the answer appears, Pi has run extension hooks, written a session file, called the model twice, read a file and appended three more lines. This section follows that one input through the stable CLI in 22 steps, verified against the source. It then shows the real event stream and session file the capture kit recorded for the same exchange. Every step names the section that explains it in full; read this one first and use it as the map.

你输入“hello.txt 里写了什么？”并按下回车。在答案出现之前，Pi 已经跑过扩展钩子、写下一个 Session 文件、调用了两次模型、读了一个文件、并又追加了三行。本节用 22 步把这一次输入在稳定 CLI 中的走法跟到底，每一步都对着源码核过。随后它展示采集工具为同一次交互记录下来的真实事件流和 Session 文件。每一步都标出完整解释它的那一节；先读这一节，把它当地图用。

## The specimen

## 样本

The capture kit drives a real AgentSession with the faux provider from pi-ai, so no network or API key is involved research/capture/one-turn.mjs. The faux model is scripted with two replies. The first is the text “Reading it.” plus a read call for hello.txt with stop reason tool Use. The second is “It says: Hello from the capture kit.” The script subscribes to the session, calls session.prompt(), and dumps every event and every line of the session file to research/out/one-turn.txt. It runs under Node 26.10.0 against pi-coding-agent 1.0.4 built from 28dcce2. In the interactive CLI the same session.prompt() call comes from the editor; the steps below start there.

采集工具用 pi-ai 里的 faux 供应商驱动一个真实的 AgentSession，因此不涉及网络和 API key research/capture/one-turn.mjs。这个 faux 模型的剧本里有两段回复。第一段是文本 “Reading it.”，加上一次针对 hello.txt 的 read 调用，停止原因是 toolUse。第二段是 “It says: Hello from the capture kit.”。脚本订阅这个 Session、调用 session.prompt()，并把每一个事件和 Session 文件的每一行都 dump 到 research/out/one-turn.txt。它在 Node 26.10.0 下运行，对象是从 28dcce2 构建的 pi-coding-agent 1.0.4。在交互式 CLI 里，同一个 session.prompt() 调用来自编辑器；下面的步骤就从那里开始。

Into the loop: steps 1–12

进入循环：第 1–12 步

![](images/1ca4bc5e4989f4c34753af31470bca5e290289263944e1a078bfe6efd9e47774.jpg)

The prompt is on disk before the model sees it. Steps 1–12 of one prompt in the stable CLI. Solid arrows are calls, the dashed arrow is the provider stream, dotted arrows are agent events delivered to AgentSession. Verified against CA/src/core/agent-session.ts, agent/agent-loop.ts and CA/src/core/model-runtime.ts at 28dcce2. Schematic.

模型看到提示词之前，它已经在磁盘上了。稳定 CLI 中一句提示词的第 1–12 步。实线箭头是调用，虚线箭头是供应商流，点线箭头是投递给 AgentSession 的智能体事件。在 28dcce2 时对照 CA/src/core/agent-session.ts、agent/agent-loop.ts 和 CA/src/core/model-runtime.ts 核过。示意图。

1 · Submit. The editor’s onSubmit handles built-in slash commands and ! bash lines itself. Anything else goes to the main loop of InteractiveMode, which awaits session.prompt(user Input) CA/src/modes/interactive/interactive-mode.ts:1247. Print, JSON and RPC modes call the same method run modes (p. 127).

1 · 提交。编辑器的 onSubmit 自己处理内置斜杠命令和以 ! 开头的 bash 行。其余输入都进入 InteractiveMode 的主循环，由它 await session.prompt(userInput) CA/src/modes/interactive/interactive-mode.ts:1247。打印、JSON 和 RPC 模式调用同一个方法 运行模式（p. 127）。

2 · Prompt pipeline. AgentSession.prompt() runs a fixed sequence CA/src/core/agent-session.ts:1954. An extension command such as /foo runs and returns. Then input handlers may rewrite or consume the text. Skill commands and prompt templates expand. If a run is already streaming, the text is queued as a steer or follow-up and prompt() returns. Otherwise the model and its auth are checked, the previous answer is checked for compaction, and before_agent_start handlers run; they may add messages or replace the system prompt CA/src/core/agent-session.ts:2048. Each stage is in from prompt() to agent_settled (p. 67), each hook in extension events and contexts (p. 120).

2 · 提示词流水线。AgentSession.prompt() 跑一段固定序列 CA/src/core/agent-session.ts:1954。像 /foo 这样的扩展命令会被执行并返回。然后输入处理器可能改写或消费这段文本。技能命令和提示词模板会展开。如果已有一次运行正在流式输出，这段文本会作为转向项或后续项入队，prompt() 直接返回。否则依次检查模型及其认证，检查上一条回答是否需要压缩，然后运行 before_agent_start 处理器；它们可以追加消息或替换系统提示词 CA/src/core/agent-session.ts:2048。每个阶段见从 prompt() 到 agent_settled（p. 67），每个钩子见扩展事件与上下文（p. 120）。

3 · Hand-of. prompt() builds the user message, then prepends a system message when the system prompt sections difer from the transcript’s CA/src/core/agent-session.ts:2091. It calls agent.prompt(messages) inside _runAgentPrompt CA/src/core/agent-session.ts:1818. The system prompt is a message in the transcript, not a request field system prompt construction (p. 75).

3 · 转交。prompt() 先构造用户消息，当系统提示词的分节与记录中的不一致时，再 prepend 一条系统消息 CA/src/core/agent-session.ts:2091。它在 _runAgentPrompt 内部调用 agent.prompt(messages) CA/src/core/agent-session.ts:1818。系统提示词是记录里的一条消息，不是请求字段 系统提示词的构造（p. 75）。

4 · Loop start. runAgentLoop declares any tool changes on that system message as tools Added, then emits agent_start, turn_start and a message_start/message_end pair for each new message agent/agent-loop.ts:117. The loop is in the agent loop (p. 49), its events in agent events and the Agent class (p. 57).

4 · 循环开始。runAgentLoop 把那条系统消息上的任何工具变更声明为 toolsAdded，然后发出 agent_start、turn_start，以及每条新消息各一对 message_start/message_end agent/agent-loop.ts:117。循环本身见智能体循环（p. 49），它的事件见智能体事件与 Agent 类（p. 57）。

5 · First write. AgentSession hears every agent event, passes it to extensions first and to subscribers second, and on message_end appends the message to the session CA/src/core/agent-session.ts:1127. The session file does not exist until a user or assistant message does CA/src/core/session-manager.ts:1166. At the user message’s message_end, SessionManager creates the file and writes all five entries it was holding in memory at once sessions, the JSONL tree (p. 86).

5 · 第一次写入。AgentSession 听到每个智能体事件，先传给扩展，再传给订阅者，并在 message_end 时把消息追加到 Session CA/src/core/agent-session.ts:1127。在出现用户或助手消息之前，Session 文件并不存在 CA/src/core/session-manager.ts:1166。在用户消息的 message_end 处，SessionManager 创建该文件，并把它一直在内存里攒着的五条记录一次写入 Session、JSONL 树（p. 86）。

6 · Request projection. Before each model call the loop calls prepare Request agent/agent-loop.ts:219. AgentSession installs it to replace the context with a projection of the session tree CA/src/core/agent-session.ts:781. That projection is where compaction summaries and context edits take efect compaction and branch summaries (p. 92).

6 · 请求投影。每次模型调用前，循环调用 prepareRequest agent/agent-loop.ts:219。AgentSession 装上它，用 Session 树的一个投影替换上下文 CA/src/core/agent-session.ts:781。压缩摘要和上下文编辑正是在这个投影上生效 压缩与分支摘要（p. 92）。

7 · Context hook. streamAssistantResponse passes the messages through transform Context and then convertToLlm agent/agent-loop.ts:390. In the CLI, transform Context emits the context extension event CA/src/core/sdk.ts:418.

7 · 上下文钩子。streamAssistantResponse 先把消息过一遍 transformContext，再过 convertToLlm agent/agent-loop.ts:390。在 CLI 里，transformContext 会发出 context 扩展事件 CA/src/core/sdk.ts:418。

8–9 · Model call. The loop calls the stream function agent/agent-loop.ts:403, which the SDK wires to model Runtime.stream Simple CA/src/core/sdk.ts:412. ModelRuntime resolves the provider and its credentials, then hands the request to the provider’s stream Simple CA/src/core/model-runtime.ts:739. The provider speaks one of the ten wire APIs over HTTP providers and models (p. 24), wire APIs and cross-provider hand-of (p. 36), auth, cost, retries and the catalog (p. 41).

8–9 · 模型调用。循环调用流式函数 agent/agent-loop.ts:403，SDK 把它接到 ModelRuntime.streamSimple 上 CA/src/core/sdk.ts:412。ModelRuntime 解析出供应商及其凭证，再把请求交给供应商的 streamSimple CA/src/core/model-runtime.ts:739。供应商通过 HTTP 讲十种通信API 中的一种 供应商与模型（p. 24）、通信API 与跨供应商转交（p. 36）、认证、成本、重试与目录（p. 41）。

10–11 · Stream. The provider returns AssistantMessageEvents: start, then text_*, thinking_* and toolcall_* deltas, then done or error the streaming event protocol (p. 30). The loop turns start into message_start, each delta into message_update, and done into message_end agent/agent-loop.ts:414.

10–11 · 流。供应商返回一串 AssistantMessageEvent：先是 start，然后是 text_*、thinking_* 和 toolcall_* 增量，最后是 done 或 error 流式事件协议（p. 30）。循环把 start 变成 message_start，每个增量变成 message_update，done 变成 message_end agent/agent-loop.ts:414。

12 · Second write. On the assistant’s message_end, AgentSession appends it as line 6 CA/src/core/agent-session.ts:1149.

12 · 第二次写入。在助手消息的 message_end 处，AgentSession 把它作为第 6 行追加 CA/src/core/agent-session.ts:1149。

Out through the tools: steps 13–22

经工具而出：第 13–22 步

![](images/20077880fa64b69d0ff774d7cf37f69683f79bada6424bc0f77a45b6603e9382.jpg)

A run ends at agent_settled, not at agent_end. Steps 13–22. tool_call and tool_result reach extensions through the beforeToolCall and afterToolCall hooks that AgentSession installs on the agent CA/src/core/agent-session.ts:640; the figure draws them from the loop, which calls the hooks. Verified against agent/agent-loop.ts and CA/src/core/agent-session.ts at 28dcce2. Schematic.

一次运行结束于 agent_settled，而不是 agent_end。第 13–22 步。tool_call 和 tool_result 通过 AgentSession 装在智能体上的 beforeToolCall 与 afterToolCall 钩子抵达扩展 CA/src/core/agent-session.ts:640；图中把它们画在循环上，因为调用这些钩子的是循环。在 28dcce2 时对照 agent/agent-loop.ts 和 CA/src/core/agent-session.ts 核过。示意图。

13–17 · One tool batch. The loop collects the tool Call blocks of the answer. It runs them in parallel unless the agent is set to sequential or a called tool declares execution Mode: "sequential" agent/agent-loop.ts:519; the default is "parallel" agent/agent.ts:253. For each call it emits tool_execution_start, validates the arguments and runs beforeToolCall, which raises the tool_call extension event; a { block: true } result turns into an error result without running the tool agent/agent-loop.ts:727. After execute(), afterToolCall raises tool_result, whose handlers may replace content, details or isError agent/agent-loop.ts:864. Then come tool_execution_end and the result message’s message_start/message_end. The read tool and the other seven are in built-in tools (p. 81).

13–17 · 一批工具调用。循环收集回答里的 toolCall 块。除非智能体被设为顺序执行，或被调用的工具声明了 executionMode: "sequential" agent/agent-loop.ts:519，否则它们并行运行；默认是 "parallel" agent/agent.ts:253。对每个调用，它发出 tool_execution_start、校验参数并运行 beforeToolCall，后者抛出 tool_call 扩展事件；一个 { block: true } 的结果会在不执行工具的情况下变成错误结果 agent/agent-loop.ts:727。execute() 之后，afterToolCall 抛出 tool_result，它的处理器可以替换 content、details 或 isError agent/agent-loop.ts:864。接着是 tool_execution_end，以及结果消息的 message_start/message_end。read 工具和另外七个见内置工具（p. 81）。

## 18 · Third write. The tool result is line 7.

## 18 · 第三次写入。工具结果是第 7 行。

19 · Next turn. turn_end closes the turn agent/agent-loop.ts:287. Because the answer contained a tool call, the inner loop runs again. prepareNextTurn gives AgentSession a chance to compact and refresh the system prompt before steps 6–12 repeat CA/src/core/agent-session.ts:892. The second answer has no tool call, so it is the last; it becomes line 8.

19 · 下一轮。turn_end 结束这一轮 agent/agent-loop.ts:287。由于回答里含有一个工具调用，内层循环再跑一次。在第 6–12 步重复之前，prepareNextTurn 给 AgentSession 一个压缩并刷新系统提示词的机会 CA/src/core/agent-session.ts:892。第二条回答没有工具调用，所以它是最后一条；它成为第 8 行。

20 · Loop end. With no tool calls, no steering and no follow-up messages left, the loop emits agent_end agent/agentloop.ts:320. AgentSession adds will Retry to it for subscribers CA/src/core/agent-session.ts:1128.

20 · 循环结束。没有工具调用、没有转向、也没有遗留的后续消息时，循环发出 agent_end agent/agentloop.ts:320。AgentSession 为订阅者补上 willRetry CA/src/core/agent-session.ts:1128。

21 · After the loop. _runAgentPrompt does not return yet. It checks the last answer for a retryable error, then for compaction, then for queued messages, and calls agent.continue() if any of them needs another run CA/src/core/agent-session.ts:1839. Last, agent_before_settle handlers may ask to continue CA/src/core/agent-session.ts:1879. These branches are in AgentSession: wiring the runtime (p. 61) and compaction and branch summaries (p. 92).

21 · 循环之后。_runAgentPrompt 还没返回。它先检查最后一条回答有没有可重试的错误，再检查是否需要压缩，再检查有没有排队消息，任何一项需要再跑一次就调用 agent.continue() CA/src/core/agent-session.ts:1839。最后，agent_before_settle 处理器可以要求继续 CA/src/core/agent-session.ts:1879。这些分支见 AgentSession：接好运行时（p. 61）和压缩与分支摘要（p. 92）。

22 · Settle. In a finally block, _emitAgentSettled emits agent_settled to extensions and then to subscribers CA/src/core/agent-session.ts:1066, and session.prompt() resolves.

22 · 落定。在一个 finally 块里，_emitAgentSettled 先向扩展、再向订阅者发出 agent_settled CA/src/core/agent-session.ts:1066，随后 session.prompt() 完成。

## The captured event stream

## 抓到的事件流

The capture recorded 29 events from one session.prompt() call. Every one is an AgentSessionEvent delivered to session.subscribe().

这次采集从一次 session.prompt() 调用记录到 29 个事件。每个都是一个投递给 session.subscribe() 的 AgentSessionEvent。

<table><tr><td colspan="5">图 1.6 一个被回答的提示词，逐事件</td><td>时间线</td></tr><tr><td>#</td><td>毫秒</td><td>事件</td><td>细节</td><td>磁盘上</td><td>步骤</td></tr><tr><td>1</td><td>1</td><td>agent_start</td><td></td><td></td><td>4</td></tr><tr><td>2</td><td>1</td><td>turn_start</td><td>第 1 轮</td><td></td><td>4</td></tr><tr><td>3-4</td><td>1</td><td>message_start·message_end</td><td>system</td><td>留在内存里</td><td>4-5</td></tr><tr><td>5-6</td><td>1</td><td>message_start·message_end</td><td>user</td><td>文件已创建：第 1-5 行</td><td>4-5</td></tr><tr><td>7</td><td>2</td><td>message_start</td><td>assistant</td><td></td><td>11</td></tr><tr><td>8-13</td><td>2</td><td>message_update×6</td><td>text_start·text_delta·text_end·toolcall_start·toolcall_delta·toolcall_end</td><td></td><td>11</td></tr><tr><td>14</td><td>2</td><td>message_end</td><td>assistant，toolUse</td><td>第 6 行</td><td>12</td></tr><tr><td>15</td><td>2</td><td>tool_execution_start</td><td>read</td><td></td><td>13</td></tr><tr><td>16</td><td>4</td><td>tool_execution_end</td><td>read</td><td></td><td>17</td></tr><tr><td>17-18</td><td>4</td><td>message_start·message_end</td><td>toolResult</td><td>第 7 行</td><td>17-18</td></tr><tr><td>19</td><td>4</td><td>turn_end</td><td>第 1 轮</td><td></td><td>19</td></tr><tr><td>20</td><td>4</td><td>turn_start</td><td>第 2 轮</td><td></td><td>19</td></tr><tr><td>21</td><td>4</td><td>message_start</td><td>assistant</td><td></td><td>11</td></tr><tr><td>22-25</td><td>4</td><td>message_update×4</td><td>text_start·text_delta×2·text_end</td><td></td><td>11</td></tr><tr><td>26</td><td>4</td><td>message_end</td><td>assistant，stop</td><td>第 8 行</td><td>12</td></tr><tr><td>27</td><td>4</td><td>turn_end</td><td>第 2 轮</td><td></td><td>19</td></tr><tr><td>28</td><td>4</td><td>agent_end</td><td></td><td></td><td>20</td></tr><tr><td>29</td><td>5</td><td>agent_settled</td><td></td><td></td><td>22</td></tr></table>

Two turns, 29 events, four writes. MS is milliseconds since the subscription, and the whole run takes 5 ms because the faux model answers from a script; with a real provider, events 7–14 and 21–26 wait on the network. STEP points into Fig. 1.4 (p. 16) and Fig. 1.5 (p. 18). From research/out/one-turn.txt (§events). The number of text_delta events changes from run to run; the order of events does not.

两轮、29 个事件、四次写入。MS 是订阅之后的毫秒数；整次运行只用 5 ms，因为 faux 模型是从剧本里回答的；换成真实供应商，事件 7–14 和 21–26 就得等网络。STEP 指向图 1.4（p. 16）和图 1.5（p. 18）。来自 research/out/one-turn.txt（§events）。text_delta 事件的数量每次运行都会变；事件的顺序不会变。

Turns are the unit of the loop: each one is a single model response plus the tools it called. Turn 1 spans events 2–19 and turn 2 spans events 20–27. Ten of the 29 events are message_update, the stream of deltas the TUI redraws from. The hooks of steps 2, 7, 14, 16 and 21 appear nowhere in this list. input, before_agent_start, context, tool_call, tool_result and agent_before_settle are dispatched to the ExtensionRunner only, and several are skipped when no handler is registered CA/src/core/agent-session.ts:651. A session.subscribe() listener never sees them extension events and contexts (p. 120).

轮次是循环的单位：每一轮是一次模型响应加上它调用的那些工具。第 1 轮跨事件 2–19，第 2 轮跨事件 20–27。29 个事件里有十个是 message_update，也就是 TUI 据以重绘的那串增量。第 2、7、14、16、21 步的钩子在这个列表里完全不出现。input、before_agent_start、context、tool_call、tool_result 和 agent_before_settle 只投递给 ExtensionRunner，其中几个在没有注册处理器时会被跳过 CA/src/core/agent-session.ts:651。session.subscribe() 的监听者永远看不到它们 扩展事件与上下文（p. 120）。

## Eight lines on disk

## 磁盘上的八行

The session file holds eight lines, one JSON object each research/out/one-turn.txt §session-jsonl. The first three describe the session; the last five are the conversation.

Session 文件有八行，每行一个 JSON 对象 research/out/one-turn.txt §session-jsonl。前三行描述这个 Session，后五行是会话内容。

<table><tr><td>行</td><td>类型</td><td>ID ← 父 ID</td><td>写入时机</td></tr><tr><td>1</td><td>session，version 3</td><td>01a10e5a-...（session id）</td><td>事件 6</td></tr><tr><td>2</td><td>model_change faux/faux-1</td><td>2cd13c47 ← null</td><td>事件 6</td></tr><tr><td>3</td><td>thinking_level_change off</td><td>f99fc4be ← 2cd13c47</td><td>事件 6</td></tr><tr><td>4</td><td>message system：5 个分节，4 个 toolsAdded</td><td>ff9b46f6 ← f99fc4be</td><td>事件 6</td></tr><tr><td>5</td><td>message user</td><td>dd741bf1 ← ff9b46f6</td><td>事件 6</td></tr><tr><td>6</td><td>message assistant，stopReason: &quot;toolUse&quot;</td><td>0f939fd7 ← dd741bf1</td><td>事件 14</td></tr><tr><td>7</td><td>message toolResult，toolCallId: &quot;call_1&quot;</td><td>81cb0f01 ← 0f939fd7</td><td>事件 18</td></tr><tr><td>8</td><td>message assistant，stopReason: &quot;stop&quot;</td><td>01f5647e ← 81cb0f01</td><td>事件 26</td></tr></table>

Every entry names its parent, so eight lines form one branch of a tree. Lines 2 and 3 are appended in memory by createAgentSession when the session is new CA/src/core/sdk.ts:436; they reach the file with line 5. version is CURRENT_SESSION_VERSION CA/src/core/session-manager.ts:41. From research/out/one-turn.txt (§session-jsonl).

每条记录都指明自己的父节点，所以这八行构成树上的一条分支。第 2、3 行在 Session 新建时由 createAgentSession 在内存中追加 CA/src/core/sdk.ts:436；它们随第 5 行一起进入文件。version 是 CURRENT_SESSION_VERSION CA/src/core/session-manager.ts:41。来自 research/out/one-turn.txt（§session-jsonl）。

Line 6 carries the whole first answer: the text, the tool call, the model that produced it, its usage and why it stopped.

第 6 行承载了第一条回答的全部内容：文本、工具调用、产出它的模型、用量，以及它为什么停下。

```json line 6: the first answer, with its tool call research/out/one-turn.txt JSONL
{
    "type": "message",
    "id": "0f939fd7",
    "parentId": "dd741bf1",
    "timestamp": "2026-10-05T23:16:41.752Z",
    "message": {
    "role": "assistant",
    "content": [
    { "type": "text", "text": "Reading it." },
    { "type": "tool Call", "id": "call_1", "name": "read", "arguments": { "path": "hello.txt" } }
    ],
    "api": "faux",
    "provider": "faux",
    "model": "faux-1",
    "usage": { ... },
    "stop Reason": "tool Use",
    "timestamp": 1791242201744,
    "thinking Level": "off"
    }
}
```

Cut from §session-jsonl, line 6. The usage object (token counts and a zero cost from the faux provider) is cut, and the two content blocks are set on one line each; keys are in stored order.

摘自 §session-jsonl 的第 6 行。usage 对象（token 计数和来自 faux 供应商的零成本）被截掉了，两个内容块各占一行；键按存储顺序排列。

The entry has two timestamps. The outer timestamp is an ISO string written by SessionManager when it appends the entry. The inner message.timestamp is milliseconds since the epoch, set by whoever built the message — here the faux provider. Every entry type is read field by field in sessions, the JSONL tree (p. 86).

这条记录有两个时间戳。外层 timestamp 是 SessionManager 追加记录时写入的 ISO 字符串。内层 message.timestamp 是自 epoch 起的毫秒数，由构造这条消息的人设置——这里就是 faux 供应商。每种记录类型都在 Session、JSONL 树（p. 86）里逐字段讲解。

## F O O T G U N

## 脚注

agent_end is not the end of a run. After it, AgentSession can retry a failed response, compact and continue, or start a new run for queued messages, all inside the same prompt() call. Code that waits for idle must wait for agent_settled or for session.prompt() to resolve. Check will Retry on agent_end before treating it as final.

agent_end 不是一次运行的结束。在它之后，AgentSession 还可以重试失败的响应、压缩后继续，或为排队消息开始一次新运行，这些全都发生在同一个 prompt() 调用内部。等待空闲的代码必须等 agent_settled，或者等 session.prompt() 完成。在把 agent_end 当作最终结果之前，先检查它的 willRetry。

## V E R I F Y

## 验证

From books/pi, run HOME=\$(mktemp -d) node research/capture/one-turn.mjs against the built checkout. It prints the event list and rewrites research/out/one-turn.txt. The empty HOME keeps your own settings and skills out of the run.

在 books/pi 下，对已构建的检出运行 HOME=$(mktemp -d) node research/capture/one-turn.mjs。它会打印事件列表并重写 research/out/one-turn.txt。空的 HOME 把你自己的设置和技能挡在这次运行之外。

Sources: CA/src/modes/interactive/interactive-mode.ts (onSubmit, run loop); CA/src/modes/print-mode.ts; CA/src/modes/rpc/rpc-mode.ts (prompt command). CA/src/core/agent-session.ts (prompt, _runAgentPrompt, _handleAgentEvent, _emitExtensionEvent, _installAgentRequestProjection, _installAgentToolHooks). CA/src/core/agent-session.ts (_beforeToolCall, _afterToolCall, _installAgentNextTurnRefresh, _handlePostAgentRun, _runBeforeSettleBoundary, _emitAgentSettled, AgentSessionEvent). CA/src/core/sdk.ts (createAgentSession: new Agent, streamFn, transform Context, initial entries); CA/src/core/model-runtime.ts (stream Simple, prepare Request). CA/src/core/session-manager.ts (_hasConversation, _persist, append Message, CURRENT_SESSION_VERSION). agent/agent.ts (prompt, tool Execution, process Events); agent/agent-loop.ts (runAgentLoop, run Loop, streamAssistantResponse, executeToolCalls, prepareToolCall, finalizeExecutedToolCall). agent/types.ts (AgentEvent); research/capture/one-turn.mjs; research/out/one-turn.txt (§versions, §events, §session-jsonl)

来源：CA/src/modes/interactive/interactive-mode.ts（onSubmit、主循环）；CA/src/modes/print-mode.ts；CA/src/modes/rpc/rpc-mode.ts（prompt 命令）。CA/src/core/agent-session.ts（prompt、_runAgentPrompt、_handleAgentEvent、_emitExtensionEvent、_installAgentRequestProjection、_installAgentToolHooks）。CA/src/core/agent-session.ts（_beforeToolCall、_afterToolCall、_installAgentNextTurnRefresh、_handlePostAgentRun、_runBeforeSettleBoundary、_emitAgentSettled、AgentSessionEvent）。CA/src/core/sdk.ts（createAgentSession：新建 Agent、streamFn、transformContext、初始记录）；CA/src/core/model-runtime.ts（streamSimple、prepareRequest）。CA/src/core/session-manager.ts（_hasConversation、_persist、appendMessage、CURRENT_SESSION_VERSION）。agent/agent.ts（prompt、toolExecution、processEvents）；agent/agent-loop.ts（runAgentLoop、runLoop、streamAssistantResponse、executeToolCalls、prepareToolCall、finalizeExecutedToolCall）。agent/types.ts（AgentEvent）；research/capture/one-turn.mjs；research/out/one-turn.txt（§versions、§events、§session-jsonl）