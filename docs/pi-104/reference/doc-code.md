---
title: 文档与代码的差异
---

<div class="section-kicker">R.6 / REFERENCE</div>

# R\.6 文档与代码的差异

---

Pi 随附的文档与代码很接近，但并不完全一致；在此提交中仍有十六处差异，而每一处实际运行的都是代码所定义的行为。



凡代码与随附文档不一致，本书均以代码为准，并用 `DOC ≠ CODE` 提示框标记。本节将所有此类差异汇总到一张表中。每一行都已对照 `28dcce2` 的检出版本重新核实：在所引文件与行号处找到文档原文，并从代码中读取对应行为。如果文档描述了代码没有执行的行为，或未提及会让信赖文档的读者感到意外的行为，就将其计为一处差异。



## 差异列表



|\#|文档所述（文件）|代码行为（文件:行号）|参见|
|---|---|---|---|
|1|来自不同提供商的思考内容会“转换为带标签的文本”。`packages/ai/README.md:1525`|使用不带标签的纯文本块保存思考内容；经过隐去处理的思考内容会被丢弃。`ai/api/transform-messages.ts:113`|传输 API 与跨提供商交接（原书第36页）|
|2|“默认情况下，［原文此处缺少主语］是 UUID。”`CA/docs/session-format.md:14`|由 `uuidv7()` 生成按时间排序的第 7 版 UUID。`CA/src/core/session-manager.ts:265`|会话：JSONL 树（原书第86页）|
|3|“‘叶节点’是树中的当前位置”，但没有说明重新打开时的规则。`CA/docs/session-format.md:215`|叶节点不会被保存；加载时，叶节点是按文件顺序排列的最后一条条目，无论它位于哪个分支。`CA/src/core/session-manager.ts:1111`|会话：JSONL 树（原书第86页）|
|4|会话名称由 `/name`、`--name` 或 `pi.setSessionName()` 设置。`CA/docs/session-format.md:201`|`getSessionName()` 返回文件顺序中的最后一条 `session_info`，与当前分支无关；空名称会清除名称。`CA/src/core/session-manager.ts:1322`|会话：JSONL 树（原书第86页）|
|5|`--append-system-prompt`“将文本或现有文件追加到系统提示”。`CA/docs/cli.md:232`|任何 `--append-system-prompt` 都会替换发现的 `APPEND_SYSTEM.md`；只有未提供该标志时才会使用该文件。`CA/src/core/resource-loader.ts:659`|系统提示词构建（原书第75页）|
|6|“项目设置覆盖智能体目录设置”，且“资源列表会合并”。`CA/docs/settings.md:3`|只有包管理器会分别读取两个文件并合并列表，见 `CA/src/core/package-manager.ts:922`；通用合并会替换数组，见 `CA/src/core/settings-manager.ts:195`，因此 `getSkillPaths()` 仅返回项目列表|配置、模型与身份验证（原书第99页）|
|7|未提及文件语法|`models.json` 可以包含注释，注释由 `stripJsonComments()` 去除，见 `CA/src/core/model-config.ts:310`；`settings.json` 直接使用 `JSON.parse()`，会拒绝注释，见 `CA/src/core/settings-manager.ts:487`|配置、模型与身份验证（原书第99页）|
|8|`@earendil-works/pi-agent-core`“拥有并导出”`AGENT_TELEMETRY_SCHEMAS`、`startAiSpan`、`startHarnessSpan`，以及 AI 和运行框架的模式定义。`packages/telemetry/README.md:371`|这些符号在 `packages/agent`、`packages/ai` 或 `packages/coding-agent` 中均不存在|遥测与评估（原书第179页）|
|9|`CustomAgentMessages` 的文档注释通过 `declare module "@mariozechner/agent"` 对其进行扩展。`agent/types.ts:357`|模块名是 `@earendil-works/pi-agent-core`；即使旧别名也是 `@mariozechner/pi-agent-core`，见 `CA/src/core/extensions/virtual-modules.ts:31`；对文档中的名称进行模块扩充，对这两个模块都不起作用|智能体事件与 `Agent` 类（原书第57页）|
|10|`PI_OFFLINE`“设为 1/true/yes 时”禁用网络操作。`CA/src/cli/args.ts:455`|大多数调用点只检查该变量是否存在，因此 `PI_OFFLINE=0` 仍会禁用版本检查、目录刷新、包更新检查和安装 ping。`CA/src/utils/version-check.ts:55`；`CA/src/core/model-runtime.ts:239`|环境变量（原书第185页）|
|11|`requiresThinkingAsText` 表示“转换为带分隔符的文本块”。`ai/types.ts:808`|适配器将思考内容输出为不带分隔符的纯文本块。`ai/api/openai-completions.ts:1324`|传输 API 与跨提供商交接（原书第36页）|
|12|当“扩展通过 `pi.appendEntry()` 追加自定义会话条目”时，会触发 `entry_appended`。`CA/docs/json.md:122`|`AgentSession` 中有五处会发出此事件，但消息条目从不发出；单轮次采集追加了五条消息，却一次也未发出此事件|`AgentSession`：组装运行时（原书第61页）|
|13|具有“暂时性状态码（408、429 和 5xx）的 HTTP 错误会重试两次”。`CA/docs/mcp.md:100`|5xx 中排除 501。`CA/src/extensions/mcp/runtime.ts:72`|MCP（原书第144页）|
|14|“当具有 codemode 暴露方式的服务器连接时，Pi 会激活 codemode。”`CA/docs/mcp.md:204`，另见 `CA/src/extensions/mcp/config.ts:29`|codemode 在会话启动时依据配置启用，此时尚无任何服务器连接|codemode（原书第151页）|
|15|某行宽于 `width` 时会“使 TUI……报错”。`tui/README.md:260`；`tui/README.md:798`|在默认的全屏模式下，该行会被静默裁切至规定宽度；回滚缓冲区渲染器仅在差分帧中抛出异常|pi\-tui（原书第158页）|
|16|project\-trust 示例要求在“包含 `.pi`、`AGENTS.md`/`CLAUDE.md` 或 `.agents/skills` 的项目中”试用。`CA/examples/extensions/project-trust.ts:13`|仅有一个 `.pi` 目录或一个上下文文件，不会触发信任决策。`CA/src/core/trust-manager.ts:186`|安全模型（原书第174页）|



这是在 `28dcce2` 时随附文档与代码之间的十六处差异。第 1–9 行已在草稿版中列出，并经过重新验证；第 10–16 行是在编写本版时发现的，各自位于“参见”栏所列章节。文档路径除带有前缀的情况外，均相对于仓库根目录。



## 每处差异的代价



1 · 思考标签：模型收到另一提供商的历史记录时，会将推理内容视为普通助手文本。查找 `<thinking>` 的提示逻辑将一无所获。



2 · 会话 ID：ID 按创建时间排序。将 ID 解析为随机 v4 UUID，或假定其没有顺序的代码，会在另一个方向上出错。调用方提供的 `--session-id` 甚至可以完全不是 UUID，见 `CA/src/core/session-manager.ts:268`。



3 · 叶节点：用 `/tree` 导航到较早的分支，在追加任何内容前退出，然后重新打开：会话会在包含最后写入条目的分支恢复，而不是在你离开的地方恢复。



4 · 会话名称：在一个分支上为会话命名，会在所有分支上重命名该会话；页脚每帧都调用 `getSessionName()`，因此切换分支后仍保留最新名称。



5 · 追加提示：CLI 标志会静默丢弃用户或项目的 `APPEND_SYSTEM.md`。如果两者都需要，请通过第二个标志再次传入该文件的内容。



6 · 资源列表：通过 `PackageManager` 加载包、扩展、技能、提示和主题时，可以看到两个列表。任何读取合并后的 `Settings` 对象的代码，例如实验性的 durable 运行框架 `CA/src/experimental/durable/prompt.ts:34`，只要项目设置了列表，就只能看到项目列表。



7 · 注释：从 `models.json` 复制一条注释到 `settings.json`，就会使整个文件无法读取。加载错误会被记录，而该设置层会被视为空，见 `CA/src/core/settings-manager.ts:499`。



8 · 遥测模式定义：README 的导入示例列出了 1\.0\.4 中并不存在的导出。



9 · 模块名：示例扩充了一个不存在的模块，因此 `pi-agent-core` 中的 `CustomAgentMessages` 不会获得任何扩展。应改为扩充 `@earendil-works/pi-agent-core`。



10 · `PI_OFFLINE=0`：将变量设为一个看起来表示假的值，并不等于取消设置该变量。



11 · 分隔符：与差异 1 的影响相同，只是发生在 OpenAI 兼容路径上。



12 · `entry_appended`：每条消息后都等待此事件的客户端，永远也等不到。



13 · 501：返回 `501 Not Implemented` 的服务器会立即失败，而不是重试两次之后才失败。



14 · Codemode 启动：在任何 MCP 服务器可达之前，`codemode` 工具就已存在；脚本会等待其指定的服务器。



15 · 超宽行：在默认模式下，溢出的组件会被裁切而不会报错，因此只有在回滚缓冲区模式下才能暴露这个问题。



16 · 信任触发条件：打开仅含 `AGENTS.md` 的项目不会询问任何问题，示例中的测试说明也无法复现该提示。



><strong>DOC ≠ CODE</strong>
>
> 差异 10 还有另一面。`main()` 严格解析该标志，见 `CA/src/main.ts:576`，因此 `PI_OFFLINE=0` 不会设置 `PI_SKIP_VERSION_CHECK`，也不会阻止包自动安装，见 `CA/src/core/package-manager.ts:55`。但同一进程随后会因为该变量存在而跳过目录刷新和版本请求。若要联网，请取消设置该变量。



## 自草稿版以来已解决的差异



草稿版还列出过一处差异：发现项目的 `.agents/skills` 目录需要获得项目信任，见 `CA/src/core/package-manager.ts:2460`，但文档未作说明。在 `28dcce2`，文档已将其列入受项目信任保护的资源，见 `CA/docs/security.md:43`，因此它不再属于差异，也未列入表中。



来源：`packages/ai/README.md` 的跨提供商交接一节；`ai/api/transform-messages.ts`（`transformMessages`）；`CA/docs/session-format.md`；`CA/src/core/session-manager.ts`（`createSessionId`、`_buildIndex`、`getSessionName`）；`CA/docs/cli.md`；`CA/src/cli/args.ts`（帮助文本）；`CA/src/core/resource-loader.ts`（`reload`、追加来源）；`CA/docs/settings.md`；`CA/src/core/settings-manager.ts`（`deepMergeObjects`、`loadFromStorage`）；`CA/src/core/package-manager.ts`（`resolve`、`isOfflineModeEnabled`、技能发现）；`CA/src/core/model-config.ts`；`packages/telemetry/README.md`；`agent/types.ts`（`CustomAgentMessages`）；`CA/src/core/extensions/virtual-modules.ts`；`CA/src/utils/version-check.ts`；`CA/src/core/model-runtime.ts`；`CA/src/main.ts`；`CA/docs/security.md`；`CA/docs/json.md`；`CA/docs/mcp.md`；`CA/src/extensions/mcp/runtime.ts`、`config.ts`；`tui/README.md`；`CA/examples/extensions/project-trust.ts`；`CA/src/core/trust-manager.ts`。
