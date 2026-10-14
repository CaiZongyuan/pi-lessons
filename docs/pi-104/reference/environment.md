---
title: 环境变量
---

<div class="section-kicker">R.1 / REFERENCE</div>

# R\.1 环境变量

---

Pi 的大多数环境变量会覆盖某项设置或检测到的终端能力；少数变量决定 Pi 可以在网络上做什么，还有七项由 Pi 写入，用于它启动的进程。



下列每个变量，都是在提交 `28dcce2` 的 `packages/*/src` 中搜索 `process.env`、`getProviderEnvValue()` 和 `ENV_*` 名称常量，再阅读使用这些变量的代码后找到的。各表列出了启用相应行为的取值、未设置变量时的默认值，以及解释其机制的章节。Pi 自行设置的变量列在最后。Pi 自己的文档页 `CA/docs/environment-variables.md` 只列出了其中一部分；文档与代码不一致时，此处以代码为准。

## 进程与存储



|<strong>变量</strong>|<strong>作用</strong>|<strong>默认值</strong>|<strong>参见</strong>|
|---|---|---|---|
|`PI_CODING_AGENT_DIR`|智能体目录：设置、身份验证、模型、会话、主题；开头的 `~` 会被展开。`CA/src/config.ts:606`|`~/.pi/agent`|配置、模型与身份验证（原书第99页）|
|`PI_CODING_AGENT_SESSION_DIR`|会话目录；优先级低于 `--session-dir`，高于 `sessionDir` 设置。`CA/src/main.ts:688`|`/sessions/--`〔源文此处的路径疑有缺失，保留原样〕|会话与 JSON 树（原书第86页）|
|`PI_PACKAGE_DIR`|Pi 查找自身包资源的位置；用于 Nix 和 Guix 存储路径。`CA/src/config.ts:395`|已安装的包|配置、模型与身份验证（原书第99页）|
|`PI_OFFLINE`|`1`、`true` 或 `yes`（或 `--offline`）：禁止自动安装包、版本检查、目录刷新、安装 ping、包更新检查、错误报告上传或 Radius 中继。`CA/src/main.ts:576`|未设置|配置、模型与身份验证（原书第99页）|
|`PI_SKIP_VERSION_CHECK`|任何非空值都会跳过向 `pi.dev` 发出的最新版本请求。`CA/src/utils/version-check.ts:98`|未设置|遥测与评测（原书第179页）|
|`PI_TELEMETRY`|`1`、`true` 或 `yes` 会强制启用安装遥测与提供商归因请求头；其他任何值都会强制关闭它们。`CA/src/core/telemetry.ts:12`|`enableInstallTelemetry` 设置|遥测与评测（原书第179页）|
|`PI_SHARE_VIEWER_URL`|`/share` 添加在 gist id 前面的基础 URL。`CA/src/config.ts:596`|`https://pi.dev/session/`|斜杠命令与快捷键（原书第197页）|
|`PI_RADIUS_GATEWAY`|内置 Radius 提供商、`/bug` 上传与中继连接使用的 Radius 网关源地址。`CA/src/core/radius.ts:10`|`https://radius.pi.dev`|提供商与模型（原书第24页）|
|`PI_CLEAR_ON_SHRINK`|当 `terminal.clearOnShrink` 未设置时，`1` 会在渲染内容缩小时清除空行。`CA/src/core/settings-manager.ts:1323`|关闭|pi\-tui（原书第158页）|
|`PI_TIMING`|`1` 会记录启动耗时并打印到 stderr。`CA/src/core/timings.ts:6`|关闭|一条提示词的完整历程（原书第15页）|
|`PI_STARTUP_BENCHMARK`|`1`、`true` 或 `yes`：初始化交互模式，停止它，打印耗时，然后退出；在其他模式下会失败。`CA/src/main.ts:932`|关闭|运行模式（原书第127页）|
|`VISUAL`、`EDITOR`|当 `externalEditor` 未设置时，指定 `Ctrl+G` 使用的外部编辑器；`VISUAL` 优先。`CA/src/core/settings-manager.ts:1059`|`nano`，Windows 上为 `notepad`|斜杠命令与快捷键（原书第197页）|
|`HTTP_PROXY`、`HTTPS_PROXY`|Pi 管理的 HTTP 客户端使用的代理；`httpProxy` 设置仅在它们未设置时填入值。`CA/src/core/http-dispatcher.ts:48`|未设置|配置、模型与身份验证（原书第99页）|



进程变量覆盖路径、网络策略和少数设置。它们的读取位置见各行引用的文件。会话目录的默认值来自 `getDefaultSessionDirPath()`，见 `CA/src/core/session-manager.ts:589`。



<strong>图 R\.1 会话写入的位置</strong>



<BookFigure id="R.1" />

> 第一个已设置的来源生效，并且设置层会在决定是否信任项目之前读取。顺序来自 `main()`（`CA/src/main.ts:688`）；默认路径来自 `CA/src/core/session-manager.ts:589`。因此，即使后来拒绝信任该项目，项目的 `.pi/settings.json` 仍然可以改变会话文件的存储位置；`CA/docs/security.md` 也作了同样说明。
> 
> 



> 文档 ≠ 代码
>
> `--help` 说，`PI_OFFLINE` 在“设为 `1/true/yes` 时”生效（`CA/src/cli/args.ts:455`）。只有 `main()`、包管理器和工具管理器按这种方式解析它。版本检查、目录刷新、包更新检查、安装 ping、错误报告上传和 Radius 中继只检查该变量是否存在（`CA/src/utils/version-check.ts:55`、`CA/src/core/model-runtime.ts:239`）。因此，`PI_OFFLINE=0` 仍会禁用大多数网络活动。若要关闭这一行为，应取消设置该变量。

## 提供商与网络



|变量|作用|默认值|参见|
|---|---|---|---|
|`PI_CACHE_RETENTION`|`long` 会在模型支持时请求较长的提示词缓存保留期：Anthropic 为 `ttl: "1h"`，OpenAI Responses 为 `prompt_cache_retention: "24h"`；也适用于 Bedrock 和 OpenAI Completions。`ai/api/anthropic-messages.ts:73`、`ai/api/openai-responses.ts:100`|`short`|身份验证、费用、重试与目录（原书第41页）|
|`PI_OAUTH_CALLBACK_HOST`|Anthropic、OpenAI Codex、ChatGPT 和 OpenRouter 的 OAuth 回调使用的回环主机。`ai/auth/oauth/anthropic.ts:17`|`127.0.0.1`|身份验证、费用、重试与目录（原书第41页）|
|`KIMI_CODE_OAUTH_HOST`、`KIMI_OAUTH_HOST`|`kimi-coding` 的 OAuth 主机；前者优先。`ai/auth/oauth/kimi-coding.ts:37`|内置主机|身份验证、费用、重试与目录（原书第41页）|
|`AWS_REGION`、`AWS_DEFAULT_REGION`|Bedrock 区域，优先级低于推理配置文件 ARN 中的区域和显式选项。`ai/api/bedrock-converse-stream.ts:1197`|SDK 链；否则为 `us-east-1`|传输 API 与跨提供商交接（原书第36页）|
|`AWS_PROFILE`|Bedrock 的命名配置文件；也算作已配置的凭证。`ai/env-api-keys.ts:183`|未设置|传输 API 与跨提供商交接（原书第36页）|
|`AWS_ACCESS_KEY_ID` \+ `AWS_SECRET_ACCESS_KEY`、`AWS_SESSION_TOKEN`|Bedrock 静态 IAM 凭证。`ai/api/bedrock-converse-stream.ts:1203`|未设置|传输 API 与跨提供商交接（原书第36页）|
|`AWS_BEARER_TOKEN_BEDROCK`|Bedrock API 密钥（bearer）身份验证。`ai/api/bedrock-converse-stream.ts:187`|未设置|传输 API 与跨提供商交接（原书第36页）|
|`AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`、`..._FULL_URI`、`AWS_WEB_IDENTITY_TOKEN_FILE`|视作 Bedrock 凭证（ECS 任务角色、IRSA）。`ai/env-api-keys.ts:186`|未设置|传输 API 与跨提供商交接（原书第36页）|
|`AWS_BEDROCK_SKIP_AUTH`|`1` 会发送占位凭证，供不需要凭证的代理使用。`ai/api/bedrock-converse-stream.ts:183`|关闭|传输 API 与跨提供商交接（原书第36页）|
|`AWS_BEDROCK_FORCE_HTTP1`|未设置代理时，`1` 会使用 HTTP/1\.1 处理器。`ai/api/bedrock-converse-stream.ts:229`|HTTP/2|传输 API 与跨提供商交接（原书第36页）|
|`AWS_BEDROCK_FORCE_CACHE`|`1` 会为 id 中不含 Claude 的模型添加缓存点，例如应用程序推理配置文件。`ai/api/bedrock-converse-stream.ts:880`|关闭|传输 API 与跨提供商交接（原书第36页）|
|`AZURE_OPENAI_BASE_URL`、`AZURE_OPENAI_RESOURCE_NAME`|通过 URL 或资源名称指定 Azure 端点。`ai/api/azure-openai-config.ts:74`|模型的 `baseUrl`|传输 API 与跨提供商交接（原书第36页）|
|`AZURE_OPENAI_API_VERSION`|Azure API 版本。`ai/api/azure-openai-config.ts:104`|`v1`|传输 API 与跨提供商交接（原书第36页）|
|`AZURE_OPENAI_DEPLOYMENT_NAME_MAP`|模型 id → 部署名称映射。`ai/api/azure-openai-config.ts:32`|部署名称 = 模型 id|传输 API 与跨提供商交接（原书第36页）|
|`GOOGLE_CLOUD_PROJECT`（或 `GLOUD_PROJECT`）、`GOOGLE_CLOUD_LOCATION`|Vertex 项目和位置；结合 ADC 凭证，可在无密钥的情况下验证 `google-vertex`。`ai/env-api-keys.ts:163`|未设置|传输 API 与跨提供商交接（原书第36页）|
|`GOOGLE_APPLICATION_CREDENTIALS`|Vertex 的 ADC 文件。`ai/env-api-keys.ts:60`|`~/.config/gcloud/` 下的 `application_default_credentials.json`|传输 API 与跨提供商交接（原书第36页）|
|`LLAMA_BASE_URL`|内置 `lama.cpp` 扩展使用的 `lama.cpp` 服务器。`CA/src/extensions/lama/provider.ts:33`|`http://127.0.0.1:8080`|提供商与模型（原书第24页）|

> 〔源文说明：上表的 `GLOUD_PROJECT`、`lama.cpp` 及路径中的 `lama` 疑有字符缺失；现有材料不足以确认原始拼写，因此保留原样。〕
> 
> 每个提供商变量都通过 `getProviderEnvValue()` 读取。它先检查单次请求的 `env` 选项，然后检查 `process.env`，最后检查 Bun 沙箱环境（`ai/utils/provider-env.ts:45`）。因此，SDK 调用方可以将凭证的作用域限定为一次请求。
> 
> 



## 提供商 API 密钥



`getApiKeyEnvVars()` 将每个内置提供商映射到一个变量（`ai/env-api-keys.ts:73`）。环境凭证（AWS 配置文件、IAM、Google ADC）不在此映射中；它们由上表所列的机制处理。



|<strong>提供商</strong>|<strong>变量</strong>|<strong>提供商</strong>|<strong>变量</strong>|
|---|---|---|---|
|`anthropic`|先 `ANTHROPIC_OAUTH_TOKEN`，再 `ANTHROPIC_API_KEY`|`openai`|`OPENAI_API_KEY`|
|`azure`|`AZURE_OPENAI_API_KEY`|`google`|`GEMINI_API_KEY`|
|`google-vertex`|`GOOGLE_CLOUD_API_KEY`|`github-copilot`|`COPILOT_GITHUB_TOKEN`|
|`openrouter`|`OPENROUTER_API_KEY`|`vercel-ai-gateway`|`AI_GATEWAY_API_KEY`|
|`groq`|`GROQ_API_KEY`|`cerebras`|`CEREBRAS_API_KEY`|
|`xai`|`XAI_API_KEY`|`mistral`|`MISTRAL_API_KEY`|
|`deepseek`|`DEEPSEEK_API_KEY`|`nvidia`|`NVIDIA_API_KEY`|
|`huggingface`|`HF_TOKEN`|`fireworks`|`FIREWORKS_API_KEY`|
|`together`|`TOGETHER_API_KEY`|`baseten`|`BASETEN_API_KEY`|
|`zai`|`ZAI_API_KEY`|`zai-coding-cn`|`ZAI_CODING_CN_API_KEY`|
|`minimax`|`MINIMAX_API_KEY`|`minimax-cn`|`MINIMAX_CN_API_KEY`|
|`moonshotai`、`moonshotai-cn`|`MOONSHOT_API_KEY`|`kimi-coding`|`KIMI_API_KEY`|
|`opencode`、`opencode-go`|`OPENCODE_API_KEY`|`meta`|`META_API_KEY`|
|`cloudflare-workers-ai`、`cloudflare-ai-gateway`|`CLOUDFLARE_API_KEY`|`radius`|`RADIUS_API_KEY`|
|`typesafe`|`TYPESAFE_API_KEY`|`ant-ling`|`ANT_LING_API_KEY`|
|`qwen-token-plan`、`qwen-token-plan-individual`|`QWEN_TOKEN_PLAN_API_KEY`|`qwen-token-plan-cn`|`QWEN_TOKEN_PLAN_CN_API_KEY`|
|`xiaomi`|`XIAOMI_API_KEY`|`xiaomi-token-plan-cn`|`XIAOMI_TOKEN_PLAN_CN_API_KEY`|
|`xiaomi-token-plan-ams`|`XIAOMI_TOKEN_PLAN_AMS_API_KEY`|`xiaomi-token-plan-sgp`|`XIAOMI_TOKEN_PLAN_SGP_API_KEY`|



除了 Anthropic 之外，每个提供商对应一个变量。来源是 `getApiKeyEnvVars()`（`ai/env-api-keys.ts:73`）。`ANTHROPIC_AUTH_TOKEN` 也会被发现，但 `getEnvApiKey()` 会跳过它，因为它必须通过 `Authorization: Bearer` 发送（`ai/env-api-keys.ts:156`）。存储的凭证及其各自的 `env` 对象见“身份验证、费用、重试与目录”（原书第41页）。



## 终端 UI



|变量|作用|默认值|参见|
|---|---|---|---|
|`PI_HARDWARE_CURSOR`|当 `showHardwareCursor` 未设置时，`1` 会显示硬件光标。`CA/src/core/settings-manager.ts:1469`|隐藏|pi\-tui（原书第158页）|
|`PI_IMAGE_PROTOCOL`|`kitty` 或 `iterm2` 强制使用指定协议；`none` 或 `0` 禁用图像；其他任何值都会触发检测。`tui/terminal-image.ts:145`|自动检测|pi\-tui（原书第158页）|
|`PI_TRUE_COLOR`|`1` 开启，`0` 关闭，其他任何值都会触发检测。`tui/terminal-image.ts:152`|自动检测|pi\-tui（原书第158页）|
|`PI_HYPERLINKS`|`1` 开启，`0` 关闭，其他任何值都会触发检测（OSC 8）。`tui/terminal-image.ts:141`|自动检测|pi\-tui（原书第158页）|
|`PI_TUI_ESC_TIMEOUT`|收到单独的 ESC 后，等待多少毫秒才将其视为 Escape；可设为任何正数。`tui/terminal.ts:123`|`10`；若设置了 `SSH_CONNECTION` 或 `SSH_TTY`，则为 `100`|pi\-tui（原书第158页）|
|`PI_TUI_WRITE_LOG`|将每次终端写入记录到此文件；若指定的是目录，则写入 `tui-<timestamp>-.log`。`tui/terminal.ts:152`|关闭|pi\-tui（原书第158页）|
|`PI_TUI_DEBUG`|`1` 会将每次渲染的诊断信息写入 `/tmp/tui/render-*.log`。`tui/tui-main-screen.ts:569`|关闭|pi\-tui（原书第158页）|
|`PI_TUI_DEBUG_REDRAW`|`1` 会将每次全量重绘及其原因记录到 TUI 日志目录下的 `pi-tui-debug.log`。`tui/tui-main-screen.ts:321`|关闭|pi\-tui（原书第158页）|



〔源文说明：协议值 `item2` 已依据第 6\.3 节同一变量的明确取值修复为 `iterm2`；日志文件名 `tui-<timestamp>-.log` 仍有无法确认的字符缺失，因此保留原样。〕



对于光标与内容缩小时清屏的行为，设置优先于变量；`terminal` 设置也优先于终端能力变量。`main()` 将终端设置传给 `setCapabilityOverrides()`（`CA/src/main.ts:871`），而 `getCapabilities()` 在检测后展开这些设置（`tui/terminal-image.ts:161`）。终端标识变量（`TERM`、`TERM_PROGRAM`、`TMUX`、`KITTY_WINDOW_ID` 等）用于检测，此处不一一列出。



## 实验性服务器与评测



|变量|作用|默认值|参见|
|---|---|---|---|
|`PI_EXPERIMENTAL`|只有值恰好为 `1` 时才启用实验性技术栈：`pi server`、`pi client`、首次运行设置。`CA/src/core/experimental.ts:2`|关闭|实验性技术栈（原书第166页）|
|`PI_SERVER_DIR`|服务器配置文件与套接字目录。`CA/src/experimental/server.ts:55`|`~/.pi/server`|实验性技术栈（原书第166页）|
|`PI_SERVER_ID`|逻辑服务器 id。`CA/src/experimental/server.ts:502`|该目录的默认服务器 id|实验性技术栈（原书第166页）|
|`PI_PROVIDER`、`PI_MODEL`|评测运行框架使用的模型；必须同时设置，或都不设置。`evals/cli.ts:76`|除非通过标志传入，否则必填|遥测与评测（原书第179页）|
|`PI_EVAL_RUNS_PER_VARIANT`|每个 `without_docs` / `with_docs` 变体的运行次数；正整数。`evals/cli.ts:79`|`1`|遥测与评测（原书第179页）|



`PI_PROVIDER` 与 `PI_MODEL` 有两种含义。评测运行框架将它们作为输入读取；在 Pi 内部，`bash` 工具将它们作为输出写入（见下表）。评测路径相对于 `packages/evals/src/`。



## 由 Pi 设置的变量



|变量|设置位置|值|参见|
|---|---|---|---|
|`PI_CODING_AGENT`|Pi 自身的进程（CLI 与 RPC 入口），由子进程继承|`true`。`CA/src/cli/setup.ts:6`|运行模式（原书第127页）|
|`AI_AGENT`|Pi 自身的进程（CLI 与 RPC 入口），由子进程继承|`pi`。`CA/src/cli/setup.ts:7`|运行模式（原书第127页）|
|`PI_SESSION_ID`|每条 `bash` / `powershell` 工具命令|会话 id。`CA/src/core/tools/bash.ts:201`|内置工具（原书第81页）|
|`PI_SESSION_FILE`|每条工具命令|JSONL 绝对路径；内存会话不设置此值。`CA/src/core/tools/bash.ts:203`|会话与 JSONL 树（原书第86页）|
|`PI_PROVIDER`、`PI_MODEL`|每条工具命令|所选模型的提供商与 id。`CA/src/core/tools/bash.ts:205`|内置工具（原书第81页）|
|`PI_REASONING_LEVEL`|每条工具命令|当前思考级别。`CA/src/core/tools/bash.ts:208`|内置工具（原书第81页）|
|`PI_OFFLINE`、`PI_SKIP_VERSION_CHECK`|离线模式下 Pi 自身的进程|`1`。`CA/src/main.ts:578`|配置、模型与身份验证（原书第99页）|



会话变量会针对每条命令解析，而且仅适用于模型发出的命令。`resolveSpawnContext()` 先删除继承的副本，再在 `exposeSessionEnvironment` 为默认值 `true` 时写入当前值（`CA/src/core/tools/bash.ts:193`）。用户的 `!` 命令通过 `executeBash()` 执行普通本地操作，不会收到这些变量（`CA/src/core/agent-session.ts:3843`）。SDK 不设置前述两个进程标记。



Pi 自身进程之间使用的内部变量未列出：`PI_SESSION_WORKER_*` 与 `PI_SESSION_SNAPSHOT_ARTIFACT`（实验性会话工作进程）、`PI_MANAGED_INSTALL_ROOT` 与 `PI_INSTALLER_API_BASE`（托管安装器），以及 `PI_EVAL_CONTAINER`、`PI_EVAL_VARIANT`、`PI_EVAL_SANDBOX_*`、`PI_EVAL_ARTIFACT_*`（评测容器）。



来源：`CA/src/config.ts`（`ENV_AGENT_DIR`、`ENV_SESSION_DIR`、`getAgentDir`、`getPackageDir`、`getShareViewerUrl`）。`CA/src/main.ts`（`main`：离线模式、`session-dir` 顺序、`PI_STARTUP_BENCHMARK`）；`CA/src/core/telemetry.ts`；`CA/src/utils/version-check.ts`；`CA/src/core/model-runtime.ts`；`CA/src/core/package-manager.ts`（`isOfflineModeEnabled`）；`CA/src/core/settings-manager.ts`（`getClearOnShrink`、`getShowHardwareCursor`、`getExternalEditorCommand`）；`CA/src/core/http-dispatcher.ts`（`applyHttpProxySettings`）；`CA/src/core/radius.ts`；`CA/src/core/tools/bash.ts`（`resolveSpawnContext`）；`CA/src/cli/setup.ts`；`CA/src/cli/args.ts`（帮助文本）；`CA/src/experimental/server.ts`；`ai/utils/provider-env.ts`；`ai/env-api-keys.ts`；`ai/api/{anthropic-messages,openai-responses,bedrock-converse-stream,azure-openai-config}.ts`；`ai/auth/oauth/*.ts`；`tui/terminal.ts`；`tui/terminal-image.ts`；`tui/tui-main-screen.ts`；`packages/evals/src/cli.ts`；`CA/docs/environment-variables.md`。
