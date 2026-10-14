---
title: 源文件索引
---

<div class="section-kicker">R.5 / REFERENCE</div>

# R\.5 源文件索引

---

以下 62 行列出了负责本书所述几乎全部行为的文件。每行给出该文件在 `28dcce2` 时的大小、值得打开查看的符号，以及解释这些符号的章节。



译注：原文称有 62 行，但所提供的源文件索引实际包含 61 条记录；下表已完整保留全部记录。



下列每个路径均已核实存在于提交 `28dcce2`，每个行号都指向所列声明。行数通过对文件运行 `wc -l` 得到，包含空行和注释；列出目录的行统计其中非测试 `.ts` 文件的行数。路径使用本书的前缀：`ai/` = `packages/ai/src/`，`agent/` = `packages/agent/src/`，`CA/` = `packages/coding-agent/`，`tui/` = `packages/tui/src/`；其他包的路径从 `packages/` 开始列出。



## pi\-ai



|文件|行数|负责内容|参见|
|---|---|---|---|
|`ai/types.ts`|1,172|`KnownApi:17` · 消息类型 `SystemMessage...Message:524-612` · `AssistantMessageEvent:769` · `ProviderRequestOptions:134`|流式事件协议（原书第30页）|
|`ai/models.ts`|1,261|`stream():876` · `createModels:990` · `createProvider:1039` · `calculateCost:1198` · `getSupportedThinkingLevels:1222` · `clampThinkingLevel:1233`|提供商与模型（原书第24页）|
|`ai/utils/transcript.ts`|237|对话记录规范化|流式事件协议（原书第30页）|
|`ai/api/transform-messages.ts`|235|`transformMessages:64`，跨提供商重放|传输 API 与跨提供商交接（原书第36页）|
|`ai/auth/resolve.ts`|217|`resolveProviderAuth:33` · `refreshStoredOAuthCredential:119`|身份验证、费用、重试与目录（原书第41页）|
|`ai/utils/overflow.ts` · `retry.ts` · `provider-retry.ts`|188 · 255 · 125|上下文溢出检测、重试策略|身份验证、费用、重试与目录（原书第41页）|
|`ai/env-api-keys.ts`|195|从环境中读取的 API 密钥|环境变量（原书第185页）|
|`ai/providers/faux.ts`|710|采集工具包使用的离线 faux 提供商|一次提示的生命周期（原书第15页）|
|`packages/ai/scripts/generate-models.ts`|3,726|`*.models.ts` 目录的生成器|提供商与模型（原书第24页）|



九行概览提供商层。`ai/api/` 包含十种传输 API；“传输 API 与跨提供商交接”（原书第36页）列出了它们。



## pi\-agent\-core



|文件|行数|负责内容|参见|
|---|---|---|---|
|`agent/agent-loop.ts`|940|`runLoop:163` · 引导消息轮询 `:176`、`:204`、`:295` · 后续消息 `:302` · `executeToolCallsParallel:586`|智能体循环（原书第49页）|
|`agent/agent.ts`|613|`PendingMessageQueue:143` · `processEvents:565`|智能体循环（原书第49页）|
|`agent/types.ts`|529|`AgentEvent`、`AgentMessage`、循环配置|智能体事件与 `Agent` 类（原书第57页）|



循环由三个文件构成。行数来自对 `28dcce2` 版本运行 `wc -l` 的结果。



## pi\-coding\-agent：核心



|文件|行数|负责内容|参见|
|---|---|---|---|
|`CA/src/core/agent-session.ts`|4,383|`constructor:474` · `_handlePostAgentRun:1839` · `prompt:1954` · `_checkCompaction:2933` · `reload:3646`|`AgentSession`：组装运行时（原书第61页）|
|`CA/src/core/sdk.ts`|468|`createAgentSession:181` · 提供商请求头合并 `:337`|RPC 模式与 SDK（原书第133页）|
|`CA/src/core/system-prompt.ts`|229|`buildSystemPromptSections:128`|系统提示词构建（原书第75页）|
|`CA/src/core/tools/index` · `truncate` · `edit` · `edit-diff` · `bash` · `read`|224 · 314 · 220 · 556 · 442 · 224|内置工具、输出截断、编辑匹配|内置工具（原书第81页）|
|`CA/src/core/session-manager.ts`|2,013|JSONL 会话文件、条目树|会话：JSONL 树（原书第86页）|
|`CA/src/core/compaction/compaction.ts`|1,119|`DEFAULT_COMPACTION_SETTINGS:126` · `shouldCompact:267` · `findProjectedCutPoint:802` · `prepareCompaction:872` · `compact:965`|压缩与分支摘要（原书第92页）|
|`CA/src/core/model-runtime.ts`|1,032|编码智能体的 `ModelRuntime`|提供商与模型（原书第24页）|
|`CA/src/core/settings-manager.ts`|1,533|设置层、`defaultProjectTrust`、`enableInstallTelemetry:1142`|配置、模型与身份验证（原书第99页）|
|`CA/src/config.ts`|656|智能体目录、配置路径|配置、模型与身份验证（原书第99页）|
|`CA/src/core/model-config.ts` · `provider-composer.ts`|346 · 732|`models.json`、自定义提供商|配置、模型与身份验证（原书第99页）|
|`CA/src/core/resource-loader.ts`|1,283|资源发现、`loadProjectTrustExtensions:501`、上下文文件 `:642`|上下文文件、技能、模板、主题与包（原书第106页）|
|`CA/src/core/package-manager.ts` · `skills.ts` · `prompt-templates.ts`|2,760 · 514 · 320|包、技能、提示模板|上下文文件、技能、模板、主题与包（原书第106页）|



`pi` 命令的大部分行为都位于 `CA/src/core/` 下。仅 `agent-session.ts` 就有 4,383 行。



## pi\-coding\-agent：CLI 与模式



|文件|行数|负责内容|参见|
|---|---|---|---|
|`CA/src/main.ts`|999|`main:573` · 离线模式 `:576` · 信任判断前的会话目录 `:688`|一次提示的生命周期（原书第15页）|
|`CA/src/cli/args.ts`|469|标志解析、`--help` 文本|CLI 参考（原书第191页）|
|`CA/src/core/slash-commands.ts`|44|内置斜杠命令列表|斜杠命令与快捷键（原书第197页）|
|`CA/src/modes/print-mode.ts` · `json-event.ts`|169 · 61|print 与 JSON 模式|运行模式（原书第127页）|
|`CA/src/modes/rpc/`|4 个文件，共 1,797 行|RPC 模式、JSONL 帧封装、客户端、类型|RPC 模式与 SDK（原书第133页）|
|`CA/src/modes/interactive/`|60 个文件，共 21,662 行|TUI 应用；`interactive-mode.ts` 有 7,072 行|运行模式（原书第127页）|



四种运行模式，一个入口点。目录大小统计非测试 `.ts` 文件。



## 安全、遥测与评估



|文件|行数|负责内容|参见|
|---|---|---|---|
|`CA/src/core/project-trust.ts`|96|`resolveProjectTrusted:46`|安全模型（原书第174页）|
|`CA/src/core/trust-manager.ts`|246|需要信任的条目 `:30` · `getProjectTrustOptions:67` · `hasTrustRequiringProjectResources:186` · `trust.json:214`|安全模型（原书第174页）|
|`CA/src/core/auth-storage.ts`|506|`auth.json` 的文件权限模式与锁 `:25`|安全模型（原书第174页）|
|`CA/src/core/mcp-servers.ts`|346|MCP 配置校验、OAuth URL 规则 `:167`|MCP（原书第144页）|
|`CA/src/core/resolve-config-value.ts`|287|`$VAR` 与 `!command` 值 `:140`|配置、模型与身份验证（原书第99页）|
|`CA/src/core/telemetry.ts` · `provider-attribution.ts`|13 · 97|`PI_TELEMETRY` 开关 · 归属请求头|遥测与评估（原书第179页）|
|`CA/src/core/experimental.ts`|3|`areExperimentalFeaturesEnabled`|一页看懂单体仓库（原书第11页）|
|`packages/telemetry/src/index.ts` · `memory.ts`|357 · 219|`TelemetryContext`、模式定义 · `InMemoryTelemetryContext`|遥测与评估（原书第179页）|
|`packages/evals/src/harness.ts` · `cli.ts` · `report.ts`|537 · 192 · 483|隔离的评估会话 · 比较运行器 · 提升幅度报告|遥测与评估（原书第179页）|
|`CA/docs/security.md` · `containerization.md`|99 · 183|随附文档中的安全立场与隔离方案|安全模型（原书第174页）|



信任与遥测相关文件虽小，影响却很大。遥测开关只有 13 行；信任决策只有 96 行。



## MCP、codemode 与 TUI



|文件|行数|负责内容|参见|
|---|---|---|---|
|`CA/src/extensions/mcp/`|11 个文件，共 4,103 行|内置 MCP 扩展：配置、OAuth、运行时、工具、`/mcp`|MCP（原书第144页）|
|`packages/mcp/src/client.ts`|615|`McpClient`|MCP（原书第144页）|
|`packages/mcp/src/transports/` · `oauth/`|4 个文件，共 822 行 · 7 个文件，共 1,304 行|stdio 与可流式传输的 HTTP · OAuth 流程|MCP（原书第144页）|
|`CA/src/extensions/codemode/`|6 个文件，共 1,300 行|`codemode` 工具，`execute.ts:55` 中的 256 MiB 上限|codemode（原书第151页）|
|`packages/codemode/src/runtime/`|4 个文件，共 1,138 行|QuickJS 工作线程、宿主、前置代码|codemode（原书第151页）|
|`packages/codemode/src/declarations.ts` · `source.ts`|355 · 115|面向脚本的工具声明、脚本源代码处理|codemode（原书第151页）|
|`tui/tui.ts` · `tui-main-screen.ts` · `tui-alt-screen.ts`|1,493 · 655 · 1,778|差分渲染器、主屏幕与备用屏幕|pi\-tui（原书第158页）|
|`tui/terminal.ts` · `keys.ts`|554 · 1,401|终端 I/O、按键解析|pi\-tui（原书第158页）|
|`tui/components/editor.ts`|2,472|`Editor:296`，提示编辑器|pi\-tui（原书第158页）|



集成分布在两个地方：一个独立库，以及将其接入系统的内置扩展。目录大小统计非测试 `.ts` 文件。



## 实验性技术栈



|文件|行数|负责内容|参见|
|---|---|---|---|
|`CA/src/experimental/`|46 个文件，共 9,950 行|`pi server`、`pi client`、会话工作进程、协调器、Radius 中继、durable 与 vacation 演示|实验性技术栈（原书第166页）|
|`CA/src/experimental/commands.ts` · `server.ts` · `session-worker.ts`|98 · 770 · 840|`runExperimentalCommand:86` · 服务器目录 `:54` · `Harness` 导入 `:15`|实验性技术栈（原书第166页）|
|`packages/durable/src/types.ts`|1,085|`TaskOutcome:449` · `TaskState:486` · `Storage.commit:997`|实验性技术栈（原书第166页）|
|`packages/durable/src/harness/`|22 个文件，共 6,756 行|`GenerationTask`、`ToolTask`（`tool.ts` 中的 `:50`）、`CompactionTask`、`agent.ts` 中的默认值|实验性技术栈（原书第166页）|
|`packages/durable/src/storage/` · `env/`|9 个文件，共 2,926 行 · 5 个文件，共 2,250 行|内存、SQLite、JSONL 后端 · `ExecutionEnv`、`NodeExecutionEnv`|实验性技术栈（原书第166页）|
|`packages/durable/docs/spec.md`|4,692|规范性的“Pico5 规范”|实验性技术栈（原书第166页）|
|`packages/env/src/connection.ts` · `ssh.ts`|384 · 530|帧编解码器、存活性检测 · `sshArguments:77`、`deployDaemon:396`|实验性技术栈（原书第166页）|
|`packages/env/docs/protocol.md`|114|守护进程的线上协议|实验性技术栈（原书第166页）|
|`packages/chord/src/delta/index.ts` · `facets/host.ts` · `services/provider.ts`|694 · 906 · 633|`Op:32` · `FacetHost.reload:423` · 订阅者缓冲区 `:453`|实验性技术栈（原书第166页）|
|`packages/protocol/src/protocol.ts` · `framing.ts`|110 · 151|`PROTOCOL_VERSION:5`、消息封套 · 16 MiB 帧 `:6`|实验性技术栈（原书第166页）|
|`packages/server/src/server.ts` · `transports/unix/listener.ts`|576 · 421|握手超时 `:42` · 套接字权限模式 `:11`|实验性技术栈（原书第166页）|
|`packages/client/src/client.ts` · `unix.ts`|479 · 299|`Client`、重连 `:134` · `discoverUnixServers:37`|实验性技术栈（原书第166页）|



仅编码智能体中的实验性连接代码就有 9,950 行。这些代码既不包含在 npm 包中，也不包含在二进制文件中；“一页看懂单体仓库”（原书第11页）说明了它们是如何被排除的。



来源：在 `28dcce2` 对每个列出的路径运行 `wc -l` 与 `ls`；行号从各文件读取；目录行统计由 `find` 找到的非测试 `.ts` 文件。
