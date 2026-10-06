The tables to keep open while running, configuring or extending Pi.

运行、配置或扩展 Pi 时需要一直摊在桌上的那些表。

![](images/017d1a8065040617db3bad0b866b1129e86fa379a109fade3f5933cde56e89f2.jpg)

R . 1

## Environment variables

## 环境变量

Most of Pi's environment variables override a setting or a detected terminal capability; a few decide what Pi may do on the network, and seven are written by Pi for the processes it starts.

Pi 的环境变量大多用来覆盖某个设置或某项探测到的终端能力；少数几个决定 Pi 在网络上可以做什么；还有七个是 Pi 为自己启动的进程写入的。

Every variable below was found by grepping process.env, getProviderEnvValue() and the ENV_* name constants in packages/*/src at 28dcce2, then reading the code that consumes it. The tables give the value that switches the behaviour on, the default when the variable is unset, and the section that explains the mechanism. Variables set by Pi come last. Pi’s own docs page, CA/docs/environment-variables.md, lists a subset of these; where it and the code difer, the code is shown.

下面每个变量都是在 28dcce2 处grep `process.env`、`getProviderEnvValue()` 以及 `packages/*/src` 里的 `ENV_*` 名称常量找到的，然后阅读消费它们的代码得出。表格给出的是打开该行为的取值、未设置时的默认值，以及解释其机制的章节。由 Pi 写入的变量排在最后。Pi 自带的文档页 `CA/docs/environment-variables.md` 只列了其中一部分；凡它与代码不一致之处，一律以代码为准。

## Process and storage

<table><tr><td>VARIABLE</td><td>EFFECT</td><td>DEFAULT</td><td>SEE</td></tr><tr><td>PI_CODING_AGENT_DIR</td><td>智能体目录：设置、认证、模型、Session、主题；开头的 ~ 会被展开 CA/src/config.ts:606</td><td>~/.pi/agent</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>PI_CODING_AGENT_SESSION_DIR</td><td>Session 目录；优先级低于 --session-dir，高于 sessionDir 设置 CA/src/main.ts:688</td><td>/sessions/--</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>PI_PACKAGE_DIR</td><td>Pi 查找自身包资源的位置；用于 Nix 与 Guix 的store 路径 CA/src/config.ts:395</td><td>已安装的包</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>PI_OFFLINE</td><td>1、true 或 yes（或 --offline）：不做包自动安装、版本检查、目录刷新、安装 ping、包更新检查、缺陷报告上传或 Radius 中继 CA/src/main.ts:576</td><td>未设置</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>PI_SKIP_VERSION_CHECK</td><td>任何非空值都会跳过对 pi.dev 最新版本的请求 CA/src/utils/version-check.ts:98</td><td>未设置</td><td>遥测与评测（第 179 页）</td></tr><tr><td>PI_TELEMETRY</td><td>1、true 或 yes 强制打开安装遥测与供应商归因头；其他任何值强制关闭 CA/src/core/telemetry.ts:12</td><td>enableInstallTelemetry 设置</td><td>遥测与评测（第 179 页）</td></tr><tr><td>PI_SHARE_VIEWER_URL</td><td>/share 给 gist id 加前缀的基础 URL CA/src/config.ts:596</td><td>https://pi.dev/session/</td><td>斜杠命令与键位绑定（第 197 页）</td></tr><tr><td>PI_RADIUS_GATEWAY</td><td>内置 Radius 供应商、/bug 上传与中继连接所用的 Radius 网关源 CA/src/core/radius.ts:10</td><td>https://radius.pi.dev</td><td>供应商与模型（第 24 页）</td></tr><tr><td>PI_CLEAR_ON_SHRINK</td><td>1 表示渲染内容收缩时清空空行，前提是 terminal.clearOnShrink 未设置 CA/src/core/settings-manager.ts:1323</td><td>关闭</td><td>pi-tui（第 158 页）</td></tr><tr><td>PI_TIMING</td><td>1 表示记录启动耗时并打印到 stderr CA/src/core/timings.ts:6</td><td>关闭</td><td>一条提示词的生命周期（第 15 页）</td></tr><tr><td>PI_STARTUP_BENCHMARK</td><td>1、true 或 yes：初始化交互模式、停止它、打印耗时、退出；在其他模式下失败 CA/src/main.ts:932</td><td>关闭</td><td>运行模式（第 127 页）</td></tr><tr><td>VISUAL, EDITOR</td><td>externalEditor 未设置时 Ctrl+G 使用的外部编辑器；VISUAL 优先 CA/src/core/settings-manager.ts:1059</td><td>nano，Windows 上为 notepad</td><td>斜杠命令与键位绑定（第 197 页）</td></tr><tr><td>HTTP_PROXY, HTTPS_PROXY</td><td>Pi 管理的 HTTP 客户端所用的代理；httpProxy 设置只在它们未设置时填入 CA/src/core/http-dispatcher.ts:48</td><td>未设置</td><td>配置、模型与认证（第 99 页）</td></tr></table>

Process variables override paths, network policy and a handful of settings. Read from the files cited in each row. The session-directory default is getDefaultSessionDirPath() CA/src/core/session-manager.ts:589.

进程类变量覆盖路径、网络策略以及少量设置。请在各行引用的文件里查阅。Session 目录的默认值来自 `getDefaultSessionDirPath()` CA/src/core/session-manager.ts:589。

F I G . R . 1 W H E R E S E S S I O N S A R E W R I T T E N

图 R.1 Session 写在哪里

![](images/63014736fee27db124151633bf1a53b5d05785265432f35eb9560d6a5e18cdee.jpg)

The first source that is set wins, and the settings layer is read before project trust is decided. Order from main() CA/src/main.ts:688; the default path from CA/src/core/session-manager.ts:589. A project .pi/settings.json can therefore move session files even when its project is later declined; CA/docs/security.md states the same.

最先设置的那个来源胜出，并且设置层在项目信任判定之前读取。顺序见 `main()` CA/src/main.ts:688；默认路径见 CA/src/core/session-manager.ts:589。因此，即使项目后来被拒绝，项目的 `.pi/settings.json` 仍然可以挪动 Session 文件；CA/docs/security.md 也是这么写的。

--help says PI_OFFLINE takes efect “when set to 1/true/yes” CA/src/cli/args.ts:455. Only main(), the package manager and the tools manager parse it that way. The version check, catalog refresh, package update check, install ping, bug-report upload and Radius relay test for presence CA/src/utils/version-check.ts:55 CA/src/core/model-runtime.ts:239. PI_OFFLINE=0 therefore still disables most network activity. Unset the variable instead.

`--help` 说 PI_OFFLINE “设为 1/true/yes 时” 生效 CA/src/cli/args.ts:455。只有 `main()`、包管理器和工具管理器按这种方式解析它。版本检查、目录刷新、包更新检查、安装 ping、缺陷报告上传和 Radius 中继判断的是该变量是否存在 CA/src/utils/version-check.ts:55 CA/src/core/model-runtime.ts:239。因此 `PI_OFFLINE=0` 仍然会禁用大部分网络活动。请改为不设置该变量。

## Providers and network

## 供应商与网络

<table><tr><td>VARIABLE</td><td>EFFECT</td><td>DEFAULT</td><td>SEE</td></tr><tr><td>PI_CACHE_RETENTION</td><td>long 表示在模型支持时请求较长的提示词缓存保留期：Anthropic 为 ttl: "1h"，OpenAI Responses 为 prompt_cache_retention: "24h"，Bedrock 与 OpenAI Completions 同理 ai/api/anthropic-messages.ts:73 ai/api/openai-responses.ts:100</td><td>short</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>PI_OAUTH_CALLBACK_HOST</td><td>Anthropic、OpenAI Codex、ChatGPT 与 OpenRouter 的 OAuth 回调所用的回环主机 ai/auth/oauth/anthropic.ts:17</td><td>127.0.0.1</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>KIMI_CODE_OAUTH_HOST,KIMI_OAUTH_HOST</td><td>kimi-coding 的 OAuth 主机；前者优先 ai/auth/oauth/kimi-coding.ts:37</td><td>内置主机</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>AWS_REGION,AWS_DEFAULT_REGION</td><td>Bedrock 区域；优先级在推理配置文件 ARN 中的区域之后、在显式选项之前 ai/api/bedrock-converse-stream.ts:1197</td><td>SDK 链，否则 us-east-1</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>AWS_PROFILE</td><td>Bedrock 具名配置；也算作已配置的凭据 ai/env-api-keys.ts:183</td><td>未设置</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN</td><td>Bedrock 静态 IAM 凭据 ai/api/bedrock-converse-stream.ts:1203</td><td>未设置</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>AWS_BEARER_TOKEN_BEDROCK</td><td>Bedrock API 密钥（bearer）认证 ai/api/bedrock-converse-stream.ts:187</td><td>未设置</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>AWS_CONTAINER_CREDENTIALS_RELATIVE_URI, ... _FULL_URI, AWS_WEB_IDENTITY_TOKEN_FILE</td><td>计为 Bedrock 凭据（ECS 任务角色、IRSA） ai/env-api-keys.ts:186</td><td>未设置</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>AWS_BEDROCK_SKIP_AUTH</td><td>1 表示发送哑凭据，用于不需要凭据的代理 ai/api/bedrock-converse-stream.ts:183</td><td>关闭</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>AWS_BEDROCK_FORCE_HTTP1</td><td>1 表示在未设置代理时使用 HTTP/1.1 处理器 ai/api/bedrock-converse-stream.ts:229</td><td>HTTP/2</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>AWS_BEDROCK_FORCE_CACHE</td><td>1 表示为 id 中不含 Claude 的模型添加缓存点，例如应用推理配置文件 ai/api/bedrock-converse-stream.ts:880</td><td>关闭</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>AZURE_OPENAI_BASE_URL, AZURE_OPENAI_RESOURCE_NAME</td><td>Azure 端点，按 URL 或资源名指定 ai/api/azure-openai-config.ts:74</td><td>模型的 baseUrl</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>AZURE_OPENAI_API_VERSION</td><td>Azure API 版本 ai/api/azure-openai-config.ts:104</td><td>v1</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>AZURE_OPENAI_DEPLOYMENT_NAME_MAP</td><td>模型 id → 部署名映射 ai/api/azure-openai-config.ts:32</td><td>部署名 = 模型 id</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>GOOGLE_CLOUD_PROJECT (or GLOUD_PROJECT), GOOGLE_CLOUD_LOCATION</td><td>Vertex 项目与区域；配合 ADC 凭据时无需密钥即可认证 google-vertex ai/env-api-keys.ts:163</td><td>未设置</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>GOOGLE_APPLICATION_CREDENTIALS</td><td>Vertex 的 ADC 文件 ai/env-api-keys.ts:60</td><td>~/.config/gcloud/ 下的 application_default_credentials.json</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>LLAMA_BASE_URL</td><td>内置 lama.cpp 扩展所用的 llama.cpp 服务器 CA/src/extensions/lama/provider.ts:33</td><td>http://127.0.0.1:8080</td><td>供应商与模型（第 24 页）</td></tr></table>

Every provider variable is read through getProviderEnvValue(). It checks the per-request env option first, then process.env, then the Bun sandbox environment ai/utils/provider-env.ts:45. An SDK caller can therefore scope a credential to one request.

每个供应商变量都通过 `getProviderEnvValue()` 读取。它先检查单次请求的 env 选项，然后是 `process.env`，最后是 Bun 沙箱环境 ai/utils/provider-env.ts:45。因此 SDK 调用方可以把一份凭据限定在单次请求内。

## Provider API keys

## 供应商 API 密钥

getApiKeyEnvVars() maps each built-in provider to one variable ai/env-api-keys.ts:73. Ambient credentials (AWS profiles, IAM, Google ADC) are not in the map; they are handled by the rows above.

`getApiKeyEnvVars()` 把每个内置供应商映射到一个变量 ai/env-api-keys.ts:73。环境凭据（AWS 配置、IAM、Google ADC）不在该映射里，由上表的各行处理。

<table><tr><td>供应商</td><td>变量</td><td>供应商</td><td>变量</td></tr><tr><td>anthropic</td><td>ANTHROPIC_OAUTH_TOKEN, then ANTHROPIC_API_KEY</td><td>openai</td><td>OPENAI_API_KEY</td></tr><tr><td>azure</td><td>AZURE_OPENAI_API_KEY</td><td>google</td><td>GEMINI_API_KEY</td></tr><tr><td>google-vertex</td><td>GOOGLE_CLOUD_API_KEY</td><td>github-copilot</td><td>COPILOT_GITHUB_TOKEN</td></tr><tr><td>openrouter</td><td>OPENROUTER_API_KEY</td><td>vercel-ai-gateway</td><td>AI_GATEWAY_API_KEY</td></tr><tr><td>groq</td><td>GROQ_API_KEY</td><td>cerebras</td><td>CEREBRAS_API_KEY</td></tr><tr><td>xai</td><td>XAI_API_KEY</td><td>mistral</td><td>MISTRAL_API_KEY</td></tr><tr><td>deepseek</td><td>DEEPSEEK_API_KEY</td><td>nvidia</td><td>NVIDIA_API_KEY</td></tr><tr><td>huggingface</td><td>HF_TOKEN</td><td>fireworks</td><td>FIREWORKS_API_KEY</td></tr><tr><td>together</td><td>TOGETHER_API_KEY</td><td>baseten</td><td>BASETEN_API_KEY</td></tr><tr><td>zai</td><td>ZAI_API_KEY</td><td>zai-coding-cn</td><td>ZAI_CODING_CN_API_KEY</td></tr><tr><td>minimax</td><td>MINIMAX_API_KEY</td><td>minimax-cn</td><td>MINIMAX_CN_API_KEY</td></tr><tr><td>moonshotai, moonshotai-cn</td><td>MOONSHOT_API_KEY</td><td>kimi-coding</td><td>KIMI_API_KEY</td></tr><tr><td>opencode, opencode-go</td><td>OPENCODE_API_KEY</td><td>meta</td><td>META_API_KEY</td></tr><tr><td>cloudflare-workers-ai, cloudflare-ai-gateway</td><td>CLOUDFLARE_API_KEY</td><td>radius</td><td>RADIUS_API_KEY</td></tr><tr><td>typesafe</td><td>TYPESAFE_API_KEY</td><td>ant-ling</td><td>ANT_LING_API_KEY</td></tr><tr><td>qwen-token-plan, qwen-token-plan-individual</td><td>QWEN_TOKEN_PLAN_API_KEY</td><td>qwen-token-plan-cn</td><td>QWEN_TOKEN_PLAN_CN_API_KEY</td></tr><tr><td>xiaomi</td><td>XIAOMI_API_KEY</td><td>xiaomi-token-plan-cn</td><td>XIAOMI_TOKEN_PLAN_CN_API_KEY</td></tr><tr><td>xiaomi-token-plan-ams</td><td>XIAOMI_TOKEN_PLAN_AMS_API_KEY</td><td>xiaomi-token-plan-sgp</td><td>XIAOMI_TOKEN_PLAN_SGP_API_KEY</td></tr></table>

One variable per provider, except Anthropic. From getApiKeyEnvVars() ai/env-api-keys.ts:73. ANTHROPIC_AUTH_TOKEN is also discovered, but getEnvApiKey() skips it because it must be sent as Authorization: Bearer ai/env-api-keys.ts:156. Stored credentials and their own env objects are covered in auth, cost, retries and the catalog (p. 41).

除 Anthropic 外，每个供应商对应一个变量。出自 `getApiKeyEnvVars()` ai/env-api-keys.ts:73。`ANTHROPIC_AUTH_TOKEN` 也会被发现，但 `getEnvApiKey()` 会跳过它，因为它必须以 `Authorization: Bearer` 发送 ai/env-api-keys.ts:156。已存储的凭据及其各自的 env 对象见「认证、成本、重试与目录」（第 41 页）。

## Terminal UI

## 终端 UI

<table><tr><td>VARIABLE</td><td>EFFECT</td><td>DEFAULT</td><td>SEE</td></tr><tr><td>PI_HARDWARE_CURSOR</td><td>1 表示显示硬件光标，前提是 showHardwareCursor 未设置 CA/src/core/settings-manager.ts:1469</td><td>隐藏</td><td>pi-tui（第 158 页）</td></tr><tr><td>PI_IMAGE_PROTOCOL</td><td>kitty 或 item2 强制指定协议；none 或 0 禁用图像；其他值则自动探测 tui/terminal-image.ts:145</td><td>自动探测</td><td>pi-tui（第 158 页）</td></tr><tr><td>PI_TRUE_COLOR</td><td>1 开启，0 关闭，其他值自动探测 tui/terminal-image.ts:152</td><td>自动探测</td><td>pi-tui（第 158 页）</td></tr><tr><td>PI_HYPERLINKS</td><td>1 开启，0 关闭，其他值自动探测（OSC 8） tui/terminal-image.ts:141</td><td>自动探测</td><td>pi-tui（第 158 页）</td></tr><tr><td>PI_TUI_ESC_TIMEOUT</td><td>孤立ESC 之后等待多少毫秒才算作 Escape；任意正整数均可 tui/terminal.ts:123</td><td>10；设置了 SSH_CONNECTION 或 SSH_TTY 时为 100</td><td>pi-tui（第 158 页）</td></tr><tr><td>PI_TUI_WRITE_LOG</td><td>把每次终端写入记录到此文件；若该值为目录名，则记录到 tui-&lt;timestamp&gt;-.log tui/terminal.ts:152</td><td>关闭</td><td>pi-tui（第 158 页）</td></tr><tr><td>PI_TUI_DEBUG</td><td>1 表示把每次渲染的诊断信息写入 /tmp/tui/render-*.log tui/tui-main-screen.ts:569</td><td>关闭</td><td>pi-tui（第 158 页）</td></tr><tr><td>PI_TUI_DEBUG_REDRAW</td><td>1 表示把每次整屏重绘及其原因记录到 TUI 日志目录下的 pi-tui-debug.log tui/tui-main-screen.ts:321</td><td>关闭</td><td>pi-tui（第 158 页）</td></tr></table>

A setting beats the variable for the cursor and clear-on-shrink; the terminal settings beat the capability variables. main() passes the terminal settings to setCapabilityOverrides() CA/src/main.ts:871, and getCapabilities() spreads them after detection tui/terminal-image.ts:161. Terminal identification variables (TERM, TERM_PROGRAM, TMUX, KITTY_WINDOW_ID and others) feed detection and are not listed.

在光标和收缩清空这两项上，设置优先于环境变量；终端相关设置又优先于那些能力变量。`main()` 把终端设置传给 `setCapabilityOverrides()` CA/src/main.ts:871，而 `getCapabilities()` 在探测之后把它们展开进去 tui/terminal-image.ts:161。终端标识类变量（TERM、TERM_PROGRAM、TMUX、KITTY_WINDOW_ID 等）参与探测，未在此列出。

## Experimental server and evals

## 实验性服务器与评测

<table><tr><td>VARIABLE</td><td>EFFECT</td><td>DEFAULT</td><td>SEE</td></tr><tr><td>PI_EXPERIMENTAL</td><td>恰好为 1 时启用实验特性栈：pi server、pi client、首次运行设置 CA/src/core/experimental.ts:2</td><td>关闭</td><td>实验特性栈（第 166 页）</td></tr><tr><td>PI_SERVER_DIR</td><td>服务器配置与socket 目录 CA/src/experimental/server.ts:55</td><td>~/.pi/server</td><td>实验特性栈（第 166 页）</td></tr><tr><td>PI_SERVER_ID</td><td>逻辑服务器 id CA/src/experimental/server.ts:502</td><td>该目录的默认 server id</td><td>实验特性栈（第 166 页）</td></tr><tr><td>PI_PROVIDER, PI_MODEL</td><td>评测harness 所用的模型；两个都设或都不设 evals/cli.ts:76</td><td>必填，除非以参数传入</td><td>遥测与评测（第 179 页）</td></tr><tr><td>PI_EVAL_RUNS_PER_VARIANT</td><td>每个 without_docs / with_docs 变体的运行次数；正整数 evals/cli.ts:79</td><td>1</td><td>遥测与评测（第 179 页）</td></tr></table>

PI_PROVIDER and PI_MODEL mean two things. The eval harness reads them as input; inside Pi, the bash tool writes them as output (next table). Eval paths are relative to packages/evals/src/.

PI_PROVIDER 和 PI_MODEL 有两重含义。评测 harness 把它们当作输入；在 Pi 内部，bash 工具把它们当作输出写入（见下表）。评测路径相对于 `packages/evals/src/`。

## Set by Pi

## 由 Pi 写入

<table><tr><td>VARIABLE</td><td>WHERE</td><td>VALUE</td><td>SEE</td></tr><tr><td>PI_CODING_AGENT</td><td>Pi 自身的进程（CLI 与 RPC 入口），子进程会继承</td><td>true CA/src/cli/setup.ts:6</td><td>运行模式（第 127 页）</td></tr><tr><td>AI_AGENT</td><td>Pi 自身的进程（CLI 与 RPC 入口），子进程会继承</td><td>pi CA/src/cli/setup.ts:7</td><td>运行模式（第 127 页）</td></tr><tr><td>PI_SESSION_ID</td><td>每条 bash / powershell 工具命令</td><td>Session id CA/src/core/tools/bash.ts:201</td><td>内置工具（第 81 页）</td></tr><tr><td>PI_SESSION_FILE</td><td>每条工具命令</td><td>JSONL 绝对路径；内存 Session 不设置 CA/src/core/tools/bash.ts:203</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>PI_PROVIDER, PI_MODEL</td><td>每条工具命令</td><td>所选模型的供应商与 id CA/src/core/tools/bash.ts:205</td><td>内置工具（第 81 页）</td></tr><tr><td>PI_REASONING_LEVEL</td><td>每条工具命令</td><td>当前思考级别 CA/src/core/tools/bash.ts:208</td><td>内置工具（第 81 页）</td></tr><tr><td>PI_OFFLINE, PI_SKIP_VERSION_CHECK</td><td>Pi 自身的进程，离线模式下</td><td>1 CA/src/main.ts:578</td><td>配置、模型与认证（第 99 页）</td></tr></table>

Session variables are resolved per command, and only for model-issued commands. resolveSpawnContext() first deletes inherited copies, then writes current values when exposeSessionEnvironment is true, the default CA/src/core/tools/bash.ts:193. User ! commands go through execute Bash() with plain local operations and receive none of them CA/src/core/agent-session.ts:3843. The SDK does not set the two process markers.

Session 类变量按命令逐条解析，而且只对模型发出的命令生效。`resolveSpawnContext()` 先删除继承来的副本，然后在 `exposeSessionEnvironment` 为 true（默认值）时写入当前值 CA/src/core/tools/bash.ts:193。用户用 `!` 触发的命令走 `execute Bash()`，执行的是纯本地操作，不会拿到其中任何一个变量 CA/src/core/agent-session.ts:3843。SDK 不设置那两个进程标记。

Internal variables used between Pi’s own processes are omitted: PI_SESSION_WORKER_* and PI_SESSION_SNAPSHOT_ARTIFACT (experimental session workers), PI_MANAGED_INSTALL_ROOT and PI_INSTALLER_API_BASE (the managed installer), and PI_EVAL_CONTAINER, PI_EVAL_VARIANT, PI_EVAL_SANDBOX_*, PI_EVAL_ARTIFACT_* (the eval container).

这里略去了 Pi 自身进程之间使用的内部变量：`PI_SESSION_WORKER_*` 与 `PI_SESSION_SNAPSHOT_ARTIFACT`（实验性 Session worker）、`PI_MANAGED_INSTALL_ROOT` 与 `PI_INSTALLER_API_BASE`（托管安装器），以及 `PI_EVAL_CONTAINER`、`PI_EVAL_VARIANT`、`PI_EVAL_SANDBOX_*`、`PI_EVAL_ARTIFACT_*`（评测容器）。

Sources: CA/src/config.ts (ENV_AGENT_DIR, ENV_SESSION_DIR, getAgentDir, getPackageDir, getShareViewerUrl). CA/src/main.ts (main: offline mode, session-dir order, PI_STARTUP_BENCHMARK); CA/src/core/telemetry.ts; CA/src/utils/version-check.ts; CA/src/core/model-runtime.ts; CA/src/core/package-manager.ts (isOfflineModeEnabled); CA/src/core/settings-manager.ts (getClearOnShrink, getShowHardwareCursor, getExternalEditorCommand); CA/src/core/http-dispatcher.ts (applyHttpProxySettings); CA/src/core/radius.ts; CA/src/core/tools/bash.ts (resolveSpawnContext); CA/src/cli/setup.ts; CA/src/cli/args.ts (help text); CA/src/experimental/server.ts; ai/utils/provider-env.ts; ai/env-api-keys.ts; ai/api/{anthropic-messages,openai-responses,bedrock-converse-stream,azure-openai-config}.ts; ai/auth/oauth/*.ts; tui/terminal.ts; tui/terminal-image.ts; tui/tui-main-screen.ts; packages/evals/src/cli.ts; CA/docs/environmentvariables.md

来源：`CA/src/config.ts`（`ENV_AGENT_DIR`、`ENV_SESSION_DIR`、`getAgentDir`、`getPackageDir`、`getShareViewerUrl`）；`CA/src/main.ts`（`main`：离线模式、session-dir 顺序、`PI_STARTUP_BENCHMARK`）；`CA/src/core/telemetry.ts`；`CA/src/utils/version-check.ts`；`CA/src/core/model-runtime.ts`；`CA/src/core/package-manager.ts`（`isOfflineModeEnabled`）；`CA/src/core/settings-manager.ts`（`getClearOnShrink`、`getShowHardwareCursor`、`getExternalEditorCommand`）；`CA/src/core/http-dispatcher.ts`（`applyHttpProxySettings`）；`CA/src/core/radius.ts`；`CA/src/core/tools/bash.ts`（`resolveSpawnContext`）；`CA/src/cli/setup.ts`；`CA/src/cli/args.ts`（帮助文本）；`CA/src/experimental/server.ts`；`ai/utils/provider-env.ts`；`ai/env-api-keys.ts`；`ai/api/{anthropic-messages,openai-responses,bedrock-converse-stream,azure-openai-config}.ts`；`ai/auth/oauth/*.ts`；`tui/terminal.ts`；`tui/terminal-image.ts`；`tui/tui-main-screen.ts`；`packages/evals/src/cli.ts`；CA/docs/environmentvariables.md
R . 2

## CLI reference

## CLI 参考

Forty-one flags and eight subcommands, read from one hand-written parser; an unrecognised longflag is not an error until the extensions have had a chance to claim it.

四十一个标志和八个子命令，全部读自同一个手写解析器；无法识别的长标志不会立刻报错，要等扩展有机会认领之后才算。

Every flag below was checked against parse Args CA/src/cli/args.ts:72 and the checks that main() runs after it CA/src/main.ts:573. pi --help prints the same list plus any flags registered by loaded extensions.

下面每个标志都对照 `parseArgs` CA/src/cli/args.ts:72 以及 `main()` 在它之后运行的各项检查核对过 CA/src/main.ts:573。`pi --help` 打印的也是这份清单，外加已加载扩展所注册的任何标志。

pi [options] [ -] [@files .] [messages .] pi install|remove|uninstall|update|list|config|auth|mcp …

## Parsing rules

## 解析规则

<table><tr><td>参数</td><td>含义</td><td>参见</td></tr><tr><td>--</td><td>结束选项解析；之后的词是消息，若以 @ 开头则是文件</td><td>运行模式（第 127 页）</td></tr><tr><td>@path</td><td>附加到第一条提示词的文件；在 RPC 模式下会被拒绝</td><td>运行模式（第 127 页）</td></tr><tr><td>bare word</td><td>一条消息；第一条会把管道传入的 stdin 与 @file 文本拼接起来，其余作为独立提示词发送</td><td>运行模式（第 127 页）</td></tr><tr><td>--name=value</td><td>带值的未知长标志，交给扩展认领</td><td>扩展、加载与 API（第 113 页）</td></tr><tr><td>--name value</td><td>未知长标志；除非下一个词以 - 或 @ 开头，否则把它当作值</td><td>扩展、加载与 API（第 113 页）</td></tr><tr><td>--name</td><td>未知长标志，值为 true</td><td>扩展、加载与 API（第 113 页）</td></tr><tr><td>-x</td><td>未知短标志：Unknown option: -x，退出码 1</td><td>—</td></tr></table>

Unknown long flags survive parsing; unknown short flags do not. A long flag that no loaded extension registered fails later with Unknown option: --name CA/src/core/agent-session-services.ts:120. From CA/src/cli/args.ts:241–261.

未知长标志能通过解析，未知短标志则不行。若某个长标志没有任何已加载扩展注册过，它会在稍后失败并报 `Unknown option: --name` CA/src/core/agent-session-services.ts:120。出自 CA/src/cli/args.ts:241–261。

A value-taking flag at the very end of the line has no value to take. It falls through to the unknown-flag branch, so pi --model ends in Unknown option: --model, not in a missing-value message CA/src/cli/args.ts:117.

位于命令行最末尾的带值标志无值可取。它会落到未知标志那一支，因此 `pi --model` 最终报的是 `Unknown option: --model`，而不是缺少取值的提示 CA/src/cli/args.ts:117。

## Mode and output

## 模式与输出

Print mode needs no flag when a stream is redirected. Either a non-TTY stdin or a non-TTY stdout selects print CA/src/main.ts:119. --offline is detected with args.includes before parsing CA/src/main.ts:576, so it also counts after --.

当某个流被重定向时，打印模式不需要标志。stdin 或 stdout 任意一个不是 TTY，就会选中打印模式 CA/src/main.ts:119。`--offline` 在解析之前用 `args.includes` 检测 CA/src/main.ts:576，因此写在 `--` 之后也算数。

<table><tr><td>标志</td><td>短形式</td><td>参数</td><td>效果</td><td>参见</td></tr><tr><td>--print</td><td>-p</td><td>[message]</td><td>一次性运行；除非下一个词以 @ 或 - 开头（允许 ---），否则把它当作消息</td><td>运行模式（第 127 页）</td></tr><tr><td>--mode</td><td></td><td>text | json | rpc</td><td>输出协议；单用 text 不会离开 TUI</td><td>运行模式（第 127 页）</td></tr><tr><td>--tui-mode</td><td></td><td>fullscreen | regular</td><td>本次运行的交互布局</td><td>pi-tui（第 158 页）</td></tr><tr><td>--verbose</td><td></td><td></td><td>详细启动信息，覆盖 quietStartup</td><td>设置参考（第 202 页）</td></tr><tr><td>--offline</td><td></td><td></td><td>设置 PI_OFFLINE=1 与 PI_SKIP_VERSION_CHECK=1</td><td>环境变量（第 185 页）</td></tr></table>

CLI reference

CLI 参考

CLI 参考

<table><tr><td>--export</td><td></td><td>[out.html]</td><td>写出 HTML 并退出；第一条消息是输出路径</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>--list-models</td><td></td><td>[search]</td><td>列出模型并退出；除非下一个词以 - 或 @ 开头，否则把它当作模糊过滤条件</td><td>供应商与模型（第 24 页）</td></tr><tr><td rowspan="2">--help</td><td>-</td><td></td><td rowspan="2">显示帮助（含扩展标志）后退出</td><td rowspan="2">扩展、加载与 API（第 113 页）</td></tr><tr><td>h</td><td></td></tr><tr><td rowspan="2">--version</td><td>-</td><td></td><td rowspan="2">打印版本号并退出</td><td rowspan="2">—</td></tr><tr><td>v</td><td></td></tr></table>

Print mode needs no flag when a stream is redirected. Either a non-TTY stdin or a non-TTY stdout selects print CA/src/main.ts:119. --offline is detected with args.includes before parsing CA/src/main.ts:576, so it also counts after --.

当某个流被重定向时，打印模式不需要标志。stdin 或 stdout 任意一个不是 TTY，就会选中打印模式 CA/src/main.ts:119。`--offline` 在解析之前用 `args.includes` 检测 CA/src/main.ts:576，因此写在 `--` 之后也算数。

## Sessions

## Session

<table><tr><td>标志</td><td>短形式</td><td>参数</td><td>效果</td><td>参见</td></tr><tr><td>--continue</td><td>-c</td><td></td><td>当前工作目录下最近的 Session</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>--resume</td><td>-r</td><td></td><td>交互式 Session 选择器</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>--session</td><td></td><td>&lt;path|id&gt;</td><td>打开某个文件，或 id 以该参数开头的第一个 Session</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>--session-id</td><td></td><td>&lt;id&gt;</td><td>打开 id 恰好为此的项目 Session，或用它新建一个</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>--fork</td><td></td><td>&lt;path|id&gt;</td><td>把某个 Session 复制到当前工作目录下的一个新 Session</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>--session-dir</td><td></td><td>&lt;dir&gt;</td><td>Session 存储位置；优先于 PI_CODING_AGENT_SESSION_DIR 与 sessionDir 设置</td><td>环境变量（第 185 页）</td></tr><tr><td>--no-session</td><td></td><td></td><td>内存 Session，不写任何文件</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>--name</td><td>-n</td><td></td><td>Session 显示名；为空则是错误</td><td>Session 与 JSONL 树（第 86 页）</td></tr></table>

One branch wins, in this order: --no-session, --fork, --session, --resume, --continue, --session-id, then a new session CA/src/main.ts:358. An argument containing / or \, or ending in .jsonl, is a path; anything else is matched as an id in this project and then in all projects CA/src/main.ts:252. A -- session match from another project asks Fork this session into current directory? [y/N].

其中只有一个分支胜出，顺序是：`--no-session`、`--fork`、`--session`、`--resume`、`--continue`、`--session-id`，最后是新建 Session CA/src/main.ts:358。含 `/` 或 `\`、或以 `.jsonl` 结尾的参数是路径；其他一律先按 id 在本项目内匹配，再在所有项目中匹配 CA/src/main.ts:252。若`--` 匹配到的是别的项目里的 Session，会询问 `Fork this session into current directory? [y/N]`。

## Model

## 模型

<table><tr><td>标志</td><td>短形式</td><td>参数</td><td>效果</td><td>参见</td></tr><tr><td>--model</td><td></td><td></td><td>模型 id 或模式；接受 provider/id 形式以及 :suffix 后缀</td><td>供应商与模型（第 24 页）</td></tr><tr><td>--provider</td><td></td><td></td><td>收窄 --model 的范围；单独使用是错误</td><td>供应商与模型（第 24 页）</td></tr><tr><td>--models</td><td></td><td></td><td>Ctrl+P 轮换所用的模式；支持 glob 与 :allowed</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>--thinking</td><td></td><td>off|minimal|low|medium|high|xhigh|max</td><td>思考级别；优先于 : 后缀；无效值只给出警告</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>--api-key</td><td></td><td></td><td>仅运行时使用的密钥，适用于所选模型的供应商；绝不存储</td><td>认证、成本、重试与目录（第 41 页）</td></tr></table>

--api-key needs a model, but --models is enough. The error reads --api-key requires a model to be specified via --model, --provider/-- model, or --models CA/src/main.ts:832; the key is set with setRuntimeApiKey CA/src/main.ts:835.

`--api-key` 需要一个模型，但有 `--models` 就够了。错误信息是 `--api-key requires a model to be specified via --model, --provider/--model, or --models` CA/src/main.ts:832；密钥通过 `setRuntimeApiKey` 设置 CA/src/main.ts:835。

## Prompt and tools

## 提示词与工具

<table><tr><td>标志</td><td>短形式</td><td>参数</td><td>效果</td><td>参见</td></tr><tr><td>--system-prompt</td><td></td><td></td><td>替换基础系统提示词；若路径存在则按文件读取</td><td>系统提示词构建（第 75 页）</td></tr><tr><td>--append-system-prompt</td><td></td><td></td><td>追加在基础提示词之后；可重复</td><td>系统提示词构建（第 75 页）</td></tr><tr><td>--tools</td><td>-t</td><td></td><td>名称或 * 模式的白名单；除非某项以 mcp__ 开头，否则 MCP 工具会保留</td><td>内置工具（第 81 页）</td></tr><tr><td>--exclude-tools</td><td>-xt</td><td></td><td>黑名单，在 --tools 之后应用，包含 MCP 工具</td><td>内置工具（第 81 页）</td></tr><tr><td>--no-tools</td><td>-nt</td><td></td><td>默认不给任何工具，内置和扩展都不给</td><td>内置工具（第 81 页）</td></tr><tr><td>--no-builtin-tools</td><td>-nbt</td><td></td><td>默认不给内置工具；扩展工具仍然保留</td><td>内置工具（第 81 页）</td></tr></table>

Both prompt flags accept a file path. resolvePromptInput reads the argument as a file when exists Sync is true and uses it as text otherwise CA/src/core/resource-loader.ts:167. pi --help says only <text> for --system-prompt.

两个提示词标志都接受文件路径。`resolvePromptInput` 在 `existsSync` 为 true 时把参数当作文件读取，否则当作文本使用 CA/src/core/resource-loader.ts:167。`pi --help` 对 `--system-prompt` 只写了 `<text>`。

## Resources and trust

## 资源与信任

<table><tr><td>标志</td><td>短形式</td><td>参数</td><td>效果</td><td>参见</td></tr><tr><td>--extension</td><td>-e</td><td></td><td>文件、目录、builtin: 或包源（npm:、git:）；可重复</td><td>扩展、加载与 API（第 113 页）</td></tr><tr><td>--no- extensions</td><td>-ne</td><td></td><td>不加载任何探测到的、已配置的或内置的扩展；显式给出的 -e 仍会加载</td><td>扩展、加载与 API（第 113 页）</td></tr><tr><td>--no-mcp</td><td></td><td></td><td>只禁用内置的 MCP 扩展</td><td>MCP（第 144 页）</td></tr><tr><td>--skill--no-skills</td><td>-ns</td><td></td><td>额外的技能文件或目录；可重复 不做技能探测；显式给出的 --skill 仍会加载</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>--prompt-template</td><td></td><td>&lt;path&gt;</td><td>额外的提示词模板；可重复</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>--no-prompt-templates</td><td>-np</td><td></td><td>不做提示词模板探测</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>--theme</td><td></td><td>&lt;path&gt;</td><td>额外的主题文件或目录；可重复</td><td>pi-tui（第 158 页）</td></tr><tr><td>--no-themes</td><td></td><td></td><td>不做主题探测</td><td>pi-tui（第 158 页）</td></tr><tr><td>--use-theme</td><td></td><td>&lt;name [/name]&gt;</td><td>本次交互运行的初始主题</td><td>pi-tui（第 158 页）</td></tr><tr><td>--no-context-files</td><td>-nc</td><td></td><td>不加载 AGENTS.md / CLAUDE.md</td><td>系统提示词构建（第 75 页）</td></tr><tr><td>--approve</td><td>-a</td><td></td><td>本次运行信任项目本地文件</td><td>安全模型（第 174 页）</td></tr><tr><td>--no-approve</td><td>-na</td><td></td><td>本次运行忽略项目本地文件</td><td>安全模型（第 174 页）</td></tr></table>

--no-mcp is disabledBuiltinExtensions: ["mcp"]. It leaves codemode, tool-search and lama.cpp loaded CA/src/main.ts:785. Paths given to -e, - -skill, --prompt-template and --theme are resolved against the startup cwd before any session switch CA/src/main.ts:726.

`--no-mcp` 的实现是 `disabledBuiltinExtensions: ["mcp"]`。它让 codemode、tool-search 与 llama.cpp 保持加载状态 CA/src/main.ts:785。传给 `-e`、`--skill`、`--prompt-template` 和 `--theme` 的路径，在任何 Session 切换之前都相对启动时的 cwd 解析 CA/src/main.ts:726。

## Startup errors

## 启动期错误

<table><tr><td>条件</td><td>消息（stderr）</td><td>退出码</td></tr><tr><td>--fork 与 --session、-c、-r 或 --no-session 同时使用</td><td>Error: --fork cannot be combined with ...</td><td>1</td></tr><tr><td>--session-id 与 --session、-c 或 -r 同时使用</td><td>Error: --session-id cannot be combined with ...</td><td>1</td></tr><tr><td>--fork 搭配一个已存在的 --session-id</td><td>Session already exists with id &#x27;&#x27;</td><td>1</td></tr><tr><td>没有 Session 匹配 --session 或 --fork</td><td>No session found matching &#x27;&#x27;</td><td>1</td></tr><tr><td>--mode 缺失或无效</td><td>--mode requires text, json, or rpc/Invalid mode &quot;...&quot;</td><td>1</td></tr><tr><td>--provider 没有搭配 --model</td><td>--provider requires --model (for example: ...)</td><td>1</td></tr><tr><td>在 --mode rpc 下使用 @file</td><td>Error: @file arguments are not supported in RPC mode</td><td>1</td></tr><tr><td>任一扩展加载失败</td><td>Failed to load extension &quot;...&quot; +hintpi -ne</td><td>1</td></tr><tr><td>非交互模式下没有模型</td><td>给出无模型的提示</td><td>1</td></tr></table>

Every startup error exits 1; a declined fork prompt exits 0. From CA/src/main.ts (validateForkFlags, validateSessionIdFlags, createSessionManager, buildSessionOptions, main) and CA/src/cli/args.ts.

每个启动期错误都以 1 退出；被拒绝的 fork 询问以 0 退出。出自 `CA/src/main.ts`（`validateForkFlags`、`validateSessionIdFlags`、`createSessionManager`、`buildSessionOptions`、`main`）与 `CA/src/cli/args.ts`。

F O O T G U N

脚注

A boolean extension flag swallows the next word. The parser does not know which unknown flags are boolean, so pi --plan "refactor auth" stores "refactor auth" as the value of --plan CA/src/cli/args.ts:250. If the extension registered --plan as boolean, the value is discarded and the message is gone CA/src/core/agent-session-services.ts:106. Put boolean extension flags after the messages, or write --plan=true.

布尔型扩展标志会把下一个词一并吞掉。解析器并不知道哪些未知标志是布尔的，因此 `pi --plan "refactor auth"` 会把 `"refactor auth"` 存成 `--plan` 的值 CA/src/cli/args.ts:250。如果该扩展把 `--plan` 注册为布尔型，这个值会被丢弃，消息也就没了 CA/src/core/agent-session-services.ts:106。请把布尔型扩展标志写在消息之后，或者写成 `--plan=true`。

## Subcommands

## 子命令

Subcommands are matched on the first word before flag parsing, in the order auth, package commands, config, mcp CA/src/main.ts:582.

子命令在解析标志之前按第一个词匹配，顺序是 auth、包相关命令、config、mcp CA/src/main.ts:582。

<table><tr><td>命令</td><td>选项</td><td>效果</td><td>参见</td></tr><tr><td>pi install</td><td>-l, -a, -na</td><td>安装一个包并写入设置；-l 写入项目设置</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>pi remove</td><td>-l, -a, -na</td><td>移除一个包；uninstall 是别名</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>pi update [source|self|pi]</td><td>--self, --extensions, --models, --all, --extension, --force, -a, -na</td><td>不带目标：只更新 Pi；--all：Pi 与包；--models：刷新目录</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>pi list</td><td>-a, -na</td><td>来自用户设置与项目设置的已安装包</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>pi config</td><td>-l, -a, -na</td><td>用 TUI 启用或禁用包资源；Tab 切换作用域</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>pi auth print-api-key</td><td>--provider, --model</td><td>打印密钥</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>pi auth print-bearer-token</td><td>--provider, --model, --min-expiry (ms|s|m|h)</td><td>打印 OAuth token，必要时先刷新</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>pi auth check</td><td>--provider, --model, --json, --credentials, -- no-refresh</td><td>就绪状态：退出码 0 表示就绪，1 表示未就绪，2 表示无效</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>pi mcp add</td><td>-l, --url, --env, --cwd, --header, --bearer-token-env-var, --oauth-*, --exposure, --description, --</td><td>在 mcp.json 中添加或替换一个服务器</td><td>MCP（第 144 页）</td></tr><tr><td>pi mcp remove</td><td>-l</td><td>移除一个服务器</td><td>MCP（第 144 页）</td></tr><tr><td>pi mcp list</td><td>--json</td><td>状态、工具与错误；失败时退出码为 1</td><td>MCP（第 144 页）</td></tr><tr><td>pi mcp login</td><td>--timeout (default 300)</td><td>浏览器 OAuth 登录</td><td>MCP（第 144 页）</td></tr><tr><td>pi mcp logout</td><td></td><td>删除已存储的 OAuth 凭据</td><td>MCP（第 144 页）</td></tr></table>

Auth commands need --provider or --model. Messages, @files, --api-key and unknown flags are rejected CA/src/cli/auth-command.ts:98. --json, --credentials and --no-refresh are for check only; --min-expiry is for print-bearer-token only CA/src/cli/auth-command.ts:72. Usage strings from CA/src/package-manager-cli.ts:265, CA/src/cli/auth-command.ts:18 and CA/src/extensions/mcp/cli.ts:33.

auth 命令需要 `--provider` 或 `--model`。消息、`@file`、`--api-key` 与未知标志都会被拒绝 CA/src/cli/auth-command.ts:98。`--json`、`--credentials` 和 `--no-refresh` 只用于 check；`--min-expiry` 只用于 print-bearer-token CA/src/cli/auth-command.ts:72。用法字符串出自 CA/src/package-manager-cli.ts:265、CA/src/cli/auth-command.ts:18 与 CA/src/extensions/mcp/cli.ts:33。

Sources: CA/src/cli/args.ts (parse Args, print Help). CA/src/main.ts (main, runAuthCommand, resolveSessionPath, validateForkFlags, validateSessionIdFlags, createSessionManager, buildSessionOptions, create Runtime). CA/src/core/agentsession-services.ts (applyExtensionFlagValues); CA/src/core/resource-loader.ts (resolvePromptInput). CA/src/packagemanager-cli.ts (getPackageCommandUsage, parsePackageCommand, handleConfigCommand); CA/src/cli/auth-command.ts; CA/src/extensions/mcp/cli.ts (HELP, runMcpCommand). CA/docs/cli.md

来源：`CA/src/cli/args.ts`（`parseArgs`、`printHelp`）；`CA/src/main.ts`（`main`、`runAuthCommand`、`resolveSessionPath`、`validateForkFlags`、`validateSessionIdFlags`、`createSessionManager`、`buildSessionOptions`、`createRuntime`）；`CA/src/core/agent-session-services.ts`（`applyExtensionFlagValues`）；`CA/src/core/resource-loader.ts`（`resolvePromptInput`）；`CA/src/package-manager-cli.ts`（`getPackageCommandUsage`、`parsePackageCommand`、`handleConfigCommand`）；`CA/src/cli/auth-command.ts`；`CA/src/extensions/mcp/cli.ts`（`HELP`、`runMcpCommand`）；CA/docs/cli.md

R . 3

## Slash commands and keybindings

## 斜杠命令与键位绑定

Twenty-four slash commands are built into the interactive editor and nowhere else; the keys are 90 named actions with defaults that change on Windows and WSL, and any ofthem can be rebound or switched ofin one JSON file.

二十四个斜杠命令内建于交互式编辑器，别处没有；按键则是 90 个具名动作，其默认值在 Windows 和 WSL 上不同，任意一个都可以在一个 JSON 文件里重新绑定或关闭。

Everything here applies to interactive mode only run modes (p. 127). RPC clients send slash commands as the text of a prompt, and only commands that come from extensions, prompt templates or skills work there RPC mode and the SDK (p. 133).

这里的一切只适用于交互模式（见「运行模式」第 127 页）。RPC 客户端把斜杠命令当作提示词文本发送，其中只有来自扩展、提示词模板或技能的命令能在那里生效（见「RPC 模式与 SDK」第 133 页）。

## Built-in slash commands

## 内置斜杠命令

<table><tr><td>命令</td><td>参数</td><td>效果</td><td>参见</td></tr><tr><td>/settings</td><td></td><td>设置菜单</td><td>设置参考（第 202 页）</td></tr><tr><td>/model</td><td>[provider/model]</td><td>模型选择器，或直接选定</td><td>供应商与模型（第 24 页）</td></tr><tr><td>/tree</td><td></td><td>在 Session 树中导航并切换分支</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>/thinking</td><td>[level]</td><td>设置思考级别</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>/scoped-models</td><td></td><td>选择 Ctrl+P 轮换经过的模型</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>/export</td><td>[path]</td><td>默认 HTML；按扩展名为 .html 或 .jsonl</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>/import</td><td></td><td>导入一个 JSONL Session 并恢复它</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>/share</td><td></td><td>以秘密 GitHub gist 上传；链接为 https://pi.dev/session/#</td><td>环境变量（第 185 页）</td></tr><tr><td>/bug</td><td>[description]</td><td>为 Pi 开发者准备一份缺陷报告</td><td>—</td></tr><tr><td>/copy</td><td></td><td>复制最后一条智能体消息</td><td>—</td></tr><tr><td>/name</td><td>[name]</td><td>设置 Session 显示名</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>/session</td><td></td><td>Session 信息与统计</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>/changelog</td><td></td><td>更新日志条目</td><td>—</td></tr><tr><td>/hotkeys</td><td></td><td>所有生效的快捷键</td><td>本节</td></tr><tr><td>/fork</td><td></td><td>从更早的某条用户消息出发新建 Session</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>/clone</td><td></td><td>在当前位置复制 Session</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>/trust</td><td></td><td>保存项目信任判定</td><td>安全模型（第 174 页）</td></tr><tr><td>/login</td><td>[provider]</td><td>配置供应商认证</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>/logout</td><td></td><td>移除供应商认证</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>/compact</td><td>[instructions]</td><td>立即压缩，可附带自定义指令</td><td>压缩与分支摘要（第 92 页）</td></tr><tr><td>/resume</td><td></td><td>另选一个 Session</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>/reload</td><td></td><td>重新加载键位绑定、扩展、技能、提示词、主题与上下文文件</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>/quit</td><td></td><td>退出 Pi</td><td>—</td></tr></table>

The list is BUILTIN_SLASH_COMMANDS, in source order. 24 entries CA/src/core/slash-commands.ts:19; each is matched by exact text or text plus a space in the editor’s submit handler CA/src/modes/interactive/interactive-mode.ts:3185. PI_SHARE_VIEWER_URL replaces the share base URL CA/src/config.ts:596.

这份清单就是 `BUILTIN_SLASH_COMMANDS`，按源码顺序排列。共 24 条 CA/src/core/slash-commands.ts:19；在编辑器的提交处理函数中，每条都按精确文本或文本加一个空格来匹配 CA/src/modes/interactive/interactive-mode.ts:3185。`PI_SHARE_VIEWER_URL` 会替换 share 的基础 URL CA/src/config.ts:596。

Three more commands are handled but are not in the list, so autocomplete never ofers them: /debug writes every rendered line with its visible width to the debug log CA/src/modes/interactive/interactive-mode.ts:6904, and /arminsayshi and /dementedelves are easter eggs CA/src/modes/interactive/interactive-mode.ts:3305. Shift+Ctrl+D triggers the same debug dump from anywhere; it is wired in pi-tui, not in the keybinding table, and cannot be rebound tui/tui.ts:1075.

还有三条命令会被处理但不在清单里，因此自动补全永远不会提供它们：`/debug` 把每一行渲染内容及其可见宽度写入调试日志 CA/src/modes/interactive/interactive-mode.ts:6904；`/arminsayshi` 与 `/dementedelves` 是彩蛋 CA/src/modes/interactive/interactive-mode.ts:3305。`Shift+Ctrl+D` 在任何位置都能触发同样的调试输出，它接在 pi-tui 里而不在键位绑定表中，且无法重新绑定 tui/tui.ts:1075。

## Commands from resources

## 来自资源的命令

<table><tr><td>来源</td><td>形式</td><td>说明</td><td>参见</td></tr><tr><td>内置 mcp 扩展</td><td>/mcp</td><td>登录、重连、启用或禁用服务器、修改 exposure</td><td>MCP（第 144 页）</td></tr><tr><td>内置 lama.cpp 扩展</td><td>/lama</td><td>管理 llama.cpp router 模型；仅限 TUI</td><td>供应商与模型（第 24 页）</td></tr><tr><td>任意扩展</td><td>/</td><td>pi.registerCommand(name, ...)</td><td>扩展、加载与 API（第 113 页）</td></tr><tr><td>提示词模板</td><td>/</td><td>把模板展开进提示词</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>技能</td><td>/skill:</td><td>仅在 enableSkillCommands 为 true（默认）时可用</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr></table>

Two extensions registering the same name both get a sufix. Each becomes name:1, name:2 in load order; a sufix already taken is skipped CA/src/core/extensions/runner.ts:825. An extension command that shares a built-in name is left out of autocomplete with a warning, and is reachable only under its sufixed name if it has one CA/src/modes/interactive/interactive-mode.ts:703. From CA/src/extensions/mcp/index.ts:1141, CA/src/extensions/lama/index.ts:183, CA/src/core/settings-manager.ts:164.

两个扩展注册同名命令时，双方都会得到后缀。按加载顺序分别变成 `name:1`、`name:2`；已被占用的后缀会被跳过 CA/src/core/extensions/runner.ts:825。与内置命令同名的扩展命令会带警告从自动补全中排除，只有在它确实有后缀时才通过带后缀的名字访问 CA/src/modes/interactive/interactive-mode.ts:703。出自 CA/src/extensions/mcp/index.ts:1141、CA/src/extensions/lama/index.ts:183、CA/src/core/settings-manager.ts:164。

## Editor prefixes

## 编辑器前缀

<table><tr><td>前缀</td><td>效果</td><td>参见</td></tr><tr><td>/</td><td>命令自动补全</td><td>上文</td></tr><tr><td>@</td><td>文件路径自动补全；该文件会被附加</td><td>pi-tui（第 158 页）</td></tr><tr><td>! cmd</td><td>用 bash 运行；输出进入上下文</td><td>内置工具（第 81 页）</td></tr><tr><td>! ! cmd</td><td>用 bash 运行；输出留在上下文之外</td><td>内置工具（第 81 页）</td></tr></table>

! switches the editor into bash mode as soon as it is typed. The border colour changes on the first ! CA/src/modes/interactive/interactivemode.ts:3105; the command runs on submit CA/src/modes/interactive/interactive-mode.ts:3327.

只要输入 `!`，编辑器就会切换到 bash 模式。边框颜色在第一个 `!` 处改变 CA/src/modes/interactive/interactive-mode.ts:3105；命令在提交时运行 CA/src/modes/interactive/interactive-mode.ts:3327。

## Application keys

## 应用级按键

Defaults from KEYBINDINGS CA/src/core/keybindings.ts:75. “Win” means native Windows; “WSL” means Linux with WSL_DISTRO_NAME or WSL_INTEROP set CA/src/core/keybindings.ts:62.

默认值来自 `KEYBINDINGS` CA/src/core/keybindings.ts:75。「Win」指原生 Windows；「WSL」指设置了 `WSL_DISTRO_NAME` 或 `WSL_INTEROP` 的 Linux CA/src/core/keybindings.ts:62。

<table><tr><td>动作</td><td>默认值</td><td>WIN / WSL</td><td>效果</td></tr><tr><td>app.interrupt</td><td>Esc</td><td></td><td>中止一次运行（排队的文本回到编辑器）、一条 bash 命令，或 bash 模式；在空编辑器上 500 毫秒内按两次则执行 doubleEscapeAction</td></tr><tr><td>app.clear</td><td>Ctrl+C</td><td></td><td>清空编辑器；500 毫秒内按两次则退出</td></tr><tr><td>app.exit</td><td>Ctrl+D</td><td></td><td>编辑器为空时退出</td></tr><tr><td>app.suspend</td><td>Ctrl+Z</td><td>Win：无</td><td>挂起到后台</td></tr><tr><td>tui.input.submit</td><td>Enter</td><td></td><td>发送；若智能体正在运行则作为转向发送</td></tr><tr><td>app.message.followUp</td><td>Alt+Enter</td><td>Ctrl+Q</td><td>排入一条后续消息</td></tr><tr><td>app.message.dequeue</td><td>Alt+Up</td><td>Alt+Q</td><td>把排队的消息退回编辑器</td></tr><tr><td>app.model.select</td><td>Ctrl+L</td><td></td><td>模型选择器</td></tr><tr><td>app.model.cycle Forward</td><td>Ctrl+P</td><td></td><td>下一个模型</td></tr><tr><td>app.model.cycle Backward</td><td>Shift+Ctrl+P</td><td>Alt+P</td><td>上一个模型</td></tr><tr><td>app.thinking.cycle</td><td>Shift+Tab</td><td></td><td>下一个思考级别</td></tr><tr><td>app.thinking.toggle</td><td>Ctrl+T</td><td></td><td>折叠或展开思考块</td></tr><tr><td>app.tools.expand</td><td>Ctrl+O</td><td></td><td>折叠或展开工具输出</td></tr><tr><td>app.editor.external</td><td>Ctrl+G</td><td></td><td>在外部编辑器中编辑提示词</td></tr><tr><td>app.clipboard.paste Image</td><td>Ctrl+V</td><td>Alt+V</td><td>粘贴文件（macOS）、图像或文本</td></tr><tr><td>app.message.copy</td><td>Ctrl+X</td><td></td><td>复制选区或最后一条助手消息</td></tr><tr><td>app.session.new .tree .fork .resume</td><td>none</td><td></td><td>/new、/tree、/fork、/resume 未绑定的快捷键</td></tr></table>

doubleEscapeAction is tree by default; fork and none are the alternatives. CA/src/core/settings-manager.ts:169. Escape order and timings from CA/src/modes/interactive/interactive-mode.ts:3050–3075 and :4229.

`doubleEscapeAction` 默认为 tree；另外两种可选值是 fork 和 none CA/src/core/settings-manager.ts:169。Escape 的顺序与时序取自 CA/src/modes/interactive/interactive-mode.ts:3050–3075 与 :4229。

## Context keys

## 上下文按键

These apply only inside one picker or view, so they reuse keys the editor also uses.

这些键只在某个选择器或视图内部生效，因此复用了编辑器也在用的按键。

<table><tr><td>视图</td><td>动作</td><td>默认值</td><td>效果</td></tr><tr><td>/tree</td><td>app.tree.foldOrUp / unfoldOrDown</td><td>Alt+← / Alt+→, Ctrl+← / Ctrl+→</td><td>折叠或展开一段分支</td></tr><tr><td></td><td>app.tree.edit Label</td><td>Shift+L</td><td>编辑节点的标签</td></tr><tr><td></td><td>app.tree.toggleLabelTimestamp</td><td>Shift+T</td><td>标签时间戳</td></tr></table>

Slash commands and keybindings

斜杠命令与键位绑定

<table><tr><td></td><td>app.tree.filter.default·noTools·user Only·labeled Only·all</td><td>Ctrl+D · Ctrl+T · Ctrl+U · Ctrl+L · Ctrl+A</td><td>树过滤器</td></tr><tr><td></td><td>app.tree.filter.cycle Forward/cycle Backward</td><td>Ctrl+O / Shift+Ctrl+O</td><td>轮换过滤器</td></tr><tr><td>session picker</td><td>app.session.toggle Path · toggle Sort · toggleNamedFilter</td><td>Ctrl+P · Ctrl+S · Ctrl+N</td><td>路径显示、排序、仅显示已命名</td></tr><tr><td></td><td>app.session.rename · delete · delete Noninvasive</td><td>Ctrl+R · Ctrl+D · Ctrl+Backspace</td><td>重命名、删除、查询为空时删除</td></tr><tr><td>model and thinking selectors</td><td>app.models.save · app.thinking.save</td><td>Ctrl+S</td><td>把所选内容存入设置</td></tr><tr><td>/scoped-models</td><td>app.models.enable All · clear All · toggle Provider</td><td>Ctrl+A · Ctrl+X · Ctrl+P</td><td>批量启用、清空、按供应商</td></tr><tr><td></td><td>app.models.reorderUp/reorder Down</td><td>Alt+↑ / Alt+↓</td><td>在轮换顺序中移动</td></tr><tr><td>fullscreen</td><td>tui.alt Screen.search</td><td>Ctrl+Shift+F (Win/WSL: Ctrl+F)</td><td>搜索记录（transcript）；Enter / Shift+Enter 跳到下一个 / 上一个</td></tr><tr><td></td><td>tui.alt Screen.previous Prompt/next Prompt</td><td>Ctrl+Shift+↑ / ↓ and Ctrl+↑ / ↓ (Win/WSL: Ctrl only)</td><td>在提示词之间跳转</td></tr><tr><td></td><td>tui.alt Screen.top/bottom</td><td>Ctrl+Home / Ctrl+End</td><td>顶部；底部并跟随</td></tr><tr><td></td><td>tui.alt Screen.pageUp/page Down</td><td>PageUp / PageDown</td><td>滚动一页</td></tr></table>

The /tree fold keys put Alt first on macOS and Ctrl first elsewhere; both are bound everywhere. CA/src/core/keybindings.ts:151. Fullscreen defaults from tui/keybindings.ts:160–209 with the overrides at CA/src/core/keybindings.ts:82–92.

`/tree` 的折叠键在 macOS 上以 Alt 优先，其他平台以 Ctrl 优先；两者在所有平台都已绑定 CA/src/core/keybindings.ts:151。全屏模式的默认值取自 tui/keybindings.ts:160–209，覆盖项见 CA/src/core/keybindings.ts:82–92。

## Editor keys

## 编辑器按键

<table><tr><td>动作</td><td>默认值</td><td>动作</td><td>默认值</td></tr><tr><td>tui.input.new Line</td><td>Shift+Enter, Ctrl+J</td><td>tui.editor.deleteWordBackward</td><td>Ctrl+W, Alt+Backspace</td></tr><tr><td>tui.input.tab</td><td>Tab（自动补全）</td><td>tui.editor.deleteWordForward</td><td>Alt+D, Alt+Delete</td></tr><tr><td>tui.editor.cursorLineStart</td><td>Home, Ctrl+A</td><td>tui.editor.deleteToLineStart</td><td>Ctrl+U</td></tr><tr><td>tui.editor.cursorLineEnd</td><td>End, Ctrl+E</td><td>tui.editor.deleteToLineEnd</td><td>Ctrl+K</td></tr><tr><td>tui.editor.cursorWordLeft</td><td>Alt+←, Ctrl+←, Alt+B</td><td>tui.editor.yank / yank Pop</td><td>Ctrl+Y / Alt+Y</td></tr><tr><td>tui.editor.cursorWordRight</td><td>Alt+→, Ctrl+→, Alt+F</td><td>tui.editor.undo</td><td>Ctrl+ - (Win: Ctrl+Z; WSL: Alt+Z)</td></tr><tr><td>tui.editor.jump Forward/jump Backward</td><td>Ctrl+] / Ctrl+Alt+]</td><td>tui.editor.history Previous / history Next</td><td>无</td></tr></table>

The editor follows Emacs conventions. Up and Down move the cursor and browse prompt history at the first or last line CA/docs/keybindings.md §Cursor movement. From tui/keybindings.ts:72–146 and the undo override at CA/src/core/keybindings.ts:77.

编辑器遵循 Emacs 惯例。Up 与 Down 移动光标，在首行或末行时浏览提示词历史 CA/docs/keybindings.md §Cursor movement。出自 tui/keybindings.ts:72–146 以及 CA/src/core/keybindings.ts:77 处的 undo 覆盖项。

## Rebinding

## 重新绑定

<agent Dir>/keybindings.json maps an action id to one key or an array of keys; a configured value replaces the default, and [] disables the action CA/src/core/keybindings.ts:379. Keys are written modifier+key with ctrl, shift, alt and super CA/docs/keybindings.md §Key syntax. Legacy names such as cycleModelForward are migrated to their app. or tui. ids on load CA/src/core/keybindings.ts:240. A file that is not valid JSON is ignored without a message, and every default applies CA/src/core/keybindings.ts:360. /reload re-reads the file.

`<agentDir>/keybindings.json` 把动作 id 映射到一个按键或一组按键；配置的值会替换默认值，`[]` 表示禁用该动作 CA/src/core/keybindings.ts:379。按键写成「修饰键+键」，修饰键有 ctrl、shift、alt 和 super CA/docs/keybindings.md §Key syntax。`cycleModelForward` 这类旧名字在加载时迁移到对应的 `app.` 或 `tui.` id CA/src/core/keybindings.ts:240。非法 JSON 的文件会被静默忽略，所有默认值照常生效 CA/src/core/keybindings.ts:360。`/reload` 会重新读取该文件。

```txt
a keybindings.json CA/docs/keybindings.md JSON
{
    "app.session.new": "ctrl+shift+n",
    "app.session.tree": ["ctrl+shift+t", "alt+shift+t"]
}
```
Copied from the shipped documentation (§Assign keybindings).

抄自随包文档（§Assign keybindings）。

An extension shortcut that collides with a built-in key either replaces it with a warning or is skipped, depending on the built-in’s restrict Override flag CA/src/core/extensions/runner.ts:690. Details are in extensions, loading and the API (p. 113).

与内置按键冲突的扩展快捷键，要么带警告替换该内置键，要么被跳过，取决于内置键的 restrictOverride 标志 CA/src/core/extensions/runner.ts:690。细节见「扩展、加载与 API」（第 113 页）。

Sources: CA/src/core/slash-commands.ts (BUILTIN_SLASH_COMMANDS). CA/src/modes/interactive/interactive-mode.ts (setupEditorSubmitHandler, setupKeyHandlers, getBuiltInCommandConflictDiagnostics, handleDebugCommand, handleCtrlC). CA/src/core/extensions/runner.ts (getRegisteredCommands, get Shortcuts). CA/src/core/keybindings.ts (KEYBINDINGS, useWindowsKeybindings, KEYBINDING_NAME_MIGRATIONS, KeybindingsManager); tui/keybindings.ts (TUI_KEYBINDINGS); tui/tui.ts (onDebug). CA/src/core/settings-manager.ts (doubleEscapeAction, enableSkillCommands); CA/src/config.ts (getShareViewerUrl). CA/src/extensions/mcp/index.ts, lama/index.ts. CA/docs/slash-commands.md, keybindings.md

来源：`CA/src/core/slash-commands.ts`（`BUILTIN_SLASH_COMMANDS`）；`CA/src/modes/interactive/interactive-mode.ts`（`setupEditorSubmitHandler`、`setupKeyHandlers`、`getBuiltInCommandConflictDiagnostics`、`handleDebugCommand`、`handleCtrlC`）；`CA/src/core/extensions/runner.ts`（`getRegisteredCommands`、`getShortcuts`）；`CA/src/core/keybindings.ts`（`KEYBINDINGS`、`useWindowsKeybindings`、`KEYBINDING_NAME_MIGRATIONS`、`KeybindingsManager`）；`tui/keybindings.ts`（`TUI_KEYBINDINGS`）；`tui/tui.ts`（`onDebug`）；`CA/src/core/settings-manager.ts`（`doubleEscapeAction`、`enableSkillCommands`）；`CA/src/config.ts`（`getShareViewerUrl`）；`CA/src/extensions/mcp/index.ts`、`lama/index.ts`；CA/docs/slash-commands.md、keybindings.md

R . 4

## Settings reference

## 设置参考

## 设置参考

Every key in settings.json has a default in a getter, not in the file; the file holds only what you changed, and a project file can override almost all of it.

`settings.json` 里的每个键都有一个 getter 作为默认值，而不是写在文件里；文件只保存你改动过的部分，并且项目文件几乎可以覆盖其中全部。

`settings.json` 里的每个键都有一个 getter 作为默认值，而不是写在文件里；文件只保存你改动过的部分，并且项目文件几乎可以覆盖其中全部。

settings.json is untyped JSON read into the Settings interface CA/src/core/settings-manager.ts:133. Nothing fills in defaults on load. Each getter applies its own default with ??, so the defaults below were read from the getters, and from the consuming code where a getter returns undefined. Every row was checked against CA/src/core/settings-manager.ts at 28dcce2; the shipped CA/docs/settings.md agrees with every default here. Types use TypeScript notation, with · separating string literals.

`settings.json` 是无类型 JSON，被读入 `Settings` 接口 CA/src/core/settings-manager.ts:133。加载时不会填充任何默认值。每个 getter 用 `??` 施加自己的默认值，因此下面的默认值都是从 getter 里读出来的；对于 getter 返回 undefined 的情况，则从消费它的代码中读出。每一行都在 28dcce2 处对照 `CA/src/core/settings-manager.ts` 核对过；随包的 CA/docs/settings.md 与这里的所有默认值一致。类型采用 TypeScript 记法，用 `·` 分隔字符串字面量。

`settings.json` 是无类型 JSON，被读入 `Settings` 接口 CA/src/core/settings-manager.ts:133。加载时不会填充任何默认值。每个 getter 用 `??` 施加自己的默认值，因此下面的默认值都是从 getter 里读出来的；对于 getter 返回 undefined 的情况，则从消费它的代码中读出。每一行都在 28dcce2 处对照 `CA/src/core/settings-manager.ts` 核对过；随包的 CA/docs/settings.md 与这里的所有默认值一致。类型采用 TypeScript 记法，用 `·` 分隔字符串字面量。

## Layers and merging

## 层次与合并

## 层次与合并

Two files feed one merged object. The global file is <agent dir>/settings.json and the project file is <cwd>/.pi/settings.json CA/src/core/settings-manager.ts:300. The project file is read only when the project is trusted CA/src/core/settings-manager.ts:474. Setters always write the global file.

两个文件汇成一个合并后的对象。全局文件是 `<agentDir>/settings.json`，项目文件是 `<cwd>/.pi/settings.json` CA/src/core/settings-manager.ts:300。项目文件只在项目被信任时才读取 CA/src/core/settings-manager.ts:474。setter 始终写入全局文件。

两个文件汇成一个合并后的对象。全局文件是 `<agentDir>/settings.json`，项目文件是 `<cwd>/.pi/settings.json` CA/src/core/settings-manager.ts:300。项目文件只在项目被信任时才读取 CA/src/core/settings-manager.ts:474。setter 始终写入全局文件。

![](images/a261c3f7e984a3697770eed63f2c83ad16cb9a285bd7f1f388efa818e60878dc.jpg)
A project list replaces a global list; a project object merges into a global object. deepMergeObjects() recurses only into plain objects CA/src/core/settings-manager.ts:195, so arrays such as extensions or enabled Models are replaced wholesale. default Tools is the one array with its own merge: a list of only +name/-name entries is appended to the inherited one CA/src/core/settings-manager.ts:225.

项目里的列表会替换全局列表；项目里的对象则合并进全局对象。`deepMergeObjects()` 只对普通对象递归 CA/src/core/settings-manager.ts:195，因此 `extensions`、`enabledModels` 这类数组是整体替换。`defaultTools` 是唯一自带合并规则的数组：如果一个列表只含 `+name`/`-name` 条目，它会被追加到继承来的列表上 CA/src/core/settings-manager.ts:225。

项目里的列表会替换全局列表；项目里的对象则合并进全局对象。`deepMergeObjects()` 只对普通对象递归 CA/src/core/settings-manager.ts:195，因此 `extensions`、`enabledModels` 这类数组是整体替换。`defaultTools` 是唯一自带合并规则的数组：如果一个列表只含 `+name`/`-name` 条目，它会被追加到继承来的列表上 CA/src/core/settings-manager.ts:225。

Three keys are read from the global file only, whatever the project says: defaultProjectTrust CA/src/core/settingsmanager.ts:1101, cache Warming CA/src/core/settings-manager.ts:1024 and http Proxy CA/src/main.ts:594. settings.json does not accept comments: it is parsed with JSON.parse() after stripping a BOM CA/src/core/settings-manager.ts:487.

有三个键无论项目怎么写都只从全局文件读取：`defaultProjectTrust` CA/src/core/settingsmanager.ts:1101、`cacheWarming` CA/src/core/settings-manager.ts:1024 和 `httpProxy` CA/src/main.ts:594。`settings.json` 不接受注释：它先去掉 BOM，再用 `JSON.parse()` 解析 CA/src/core/settings-manager.ts:487。

有三个键无论项目怎么写都只从全局文件读取：`defaultProjectTrust` CA/src/core/settingsmanager.ts:1101、`cacheWarming` CA/src/core/settings-manager.ts:1024 和 `httpProxy` CA/src/main.ts:594。`settings.json` 不接受注释：它先去掉 BOM，再用 `JSON.parse()` 解析 CA/src/core/settings-manager.ts:487。

## Model, thinking and interaction

## 模型、思考与交互

## 模型、思考与交互

<table><tr><td>键</td><td>类型</td><td>默认值</td><td>效果</td><td>参见</td></tr><tr><td>defaultProvider、defaultModel</td><td>string</td><td>自动</td><td>启动模型；模型变更持久化时写入全局文件 CA/src/core/agent-session.ts:2473</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>defaultThinkingLevel、modelThinkingLevels</td><td>ThinkingLevelRecord</td><td>"medium"、无</td><td>启动思考级别；默认取自 DEFAULT_THINKING_LEVEL CA/src/core/default.ts:3 按 provider/modelId 精确匹配的逐模型级别 CA/src/core/settings-manager.ts:878</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>thinkingBudgets</td><td>{minimal, low, medium, high}</td><td>内置预算</td><td>各思考级别的 token 预算</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>enabledModels</td><td>string[]</td><td>全部模型</td><td>启动选择与轮换所用的模型模式；--models 优先 CA/src/main.ts:810</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>transport</td><td>&quot;auto&quot; · &quot;sse&quot; · &quot;websocket&quot; · &quot;websocket-cached&quot;</td><td>&quot;auto&quot;</td><td>供应商提供多种传输方式时的首选 CA/src/core/settings-manager.ts:905</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>steeringMode、followUpMode</td><td>&quot;one-at-a-time&quot; · &quot;all&quot;</td><td>&quot;one-at-a-time&quot;</td><td>每次投递多少条排队消息 CA/src/core/settings-manager.ts:831</td><td>智能体循环（第 49 页）</td></tr><tr><td>doubleEscapeAction</td><td>&quot;tree&quot; · &quot;fork&quot; · &quot;none&quot;</td><td>&quot;tree&quot;</td><td>在空编辑器上双击 Escape 时的动作 CA/src/core/settings-manager.ts:1447</td><td>斜杠命令与键位绑定（第 197 页）</td></tr><tr><td>treeFilterMode</td><td>&quot;default&quot; · &quot;no-tools&quot; · &quot;user-only&quot; · &quot;labeled-only&quot; · &quot;all&quot;</td><td>&quot;default&quot;</td><td>`/tree` 的初始过滤器；未知值回退到默认 CA/src/core/settings-manager.ts:1456</td><td>斜杠命令与键位绑定（第 197 页）</td></tr><tr><td>externalEditor</td><td>string</td><td>$VISUAL、$EDITOR，其次是 nano 或 notepad</td><td>Ctrl+G 使用的命令 CA/src/core/settings-manager.ts:1054</td><td>斜杠命令与键位绑定（第 197 页）</td></tr><tr><td>defaultProjectTrust</td><td>&quot;ask&quot; · &quot;always&quot; · &quot;never&quot;</td><td>&quot;ask&quot;</td><td>兜底的信任判定；仅全局</td><td>安全模型（第 174 页）</td></tr></table>

The model block. Getters from CA/src/core/settings-manager.ts; the thinking default from CA/src/core/defaults.ts.

本表是模型这一块。getter 来自 `CA/src/core/settings-manager.ts`；思考级别的默认值来自 `CA/src/core/defaults.ts`。

本表是模型这一块。getter 来自 `CA/src/core/settings-manager.ts`；思考级别的默认值来自 `CA/src/core/defaults.ts`。

## Tools, codemode and sessions

## 工具、codemode 与 Session

## 工具、codemode 与 Session

<table><tr><td>键</td><td>类型</td><td>默认值</td><td>效果</td><td>参见</td></tr><tr><td>defaultTools</td><td>string[]</td><td>[&quot;read&quot;, &quot;bash&quot;, &quot;edit&quot;, &quot;write&quot;]</td><td>启动工具； plain 名称会替换默认值；`+name` 添加、`-name` 移除，按顺序生效 CA/src/core/settings-manager.ts:215</td><td>内置工具（第 81 页）</td></tr><tr><td>codemode.mode</td><td>&quot;on&quot; · &quot;only&quot;</td><td>&quot;on&quot;</td><td>only 会把当前启用的直接工具对模型隐藏起来，模型只能通过 codemode 触达它们 CA/src/extensions/codemode/index.ts:23</td><td>codemode（第 151 页）</td></tr><tr><td>codemode.inlineBudget</td><td>number</td><td>3000</td><td>codemode 描述在声明上可花费的估算 token 数（字符数 ÷ 4） CA/src/extensions/codemode/tool.ts:156</td><td>codemode（第 151 页）</td></tr><tr><td>shellPath</td><td>string</td><td>平台默认 shell</td><td>bash 使用的 shell；开头的 ~ 会被展开 CA/src/core/settings-manager.ts:1078</td><td>内置工具（第 81 页）</td></tr><tr><td>shellCommandPrefix</td><td>string</td><td>无</td><td>加在每条 bash 命令之前</td><td>内置工具（第 81 页）</td></tr></table>

Settings reference

设置参考

<table><tr><td>npmCommand</td><td>string[]</td><td>npm</td><td>npm 查询与安装所用的 argv；自我更新只读取全局值 CA/src/package-manager-cli.ts:946</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>images.autoResize</td><td>boolean</td><td>true</td><td>发送前把图像缩放到不超过 $2000 \times 2000$ CA/src/core/settings-manager.ts:1404</td><td>内置工具（第 81 页）</td></tr><tr><td>images.blockImages</td><td>boolean</td><td>false</td><td>不向任何供应商发送图像 CA/src/core/settings-manager.ts:1417</td><td>内置工具（第 81 页）</td></tr><tr><td>sessionDir</td><td>string</td><td>/sessions/--</td><td>Session 目录；在项目信任判定之前读取 CA/src/main.ts:669</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>compaction.enabled</td><td>boolean</td><td>true</td><td>自动压缩 CA/src/core/settings-manager.ts:915</td><td>压缩与分支摘要（第 92 页）</td></tr><tr><td>compaction.reserveTokens</td><td>number</td><td>16384</td><td>为回复保留的 token 数 CA/src/core/settings-manager.ts:23</td><td>压缩与分支摘要（第 92 页）</td></tr><tr><td>compaction.keepRecentTokens</td><td>number</td><td>20000</td><td>保持未摘要的近期 token 数 CA/src/core/settings-manager.ts:23</td><td>压缩与分支摘要（第 92 页）</td></tr><tr><td>compaction.modelOverrides</td><td>Record</td><td>无</td><td>以 provider/modelId 为键的逐模型取值；每个字段按 覆盖值 → 普通值 → 默认值 的顺序解析 CA/src/core/settings-manager.ts:952</td><td>压缩与分支摘要（第 92 页）</td></tr><tr><td>branchSummary.reserveTokens</td><td>number</td><td>16384</td><td>在总结一条被放弃的分支时保留的 token 数 CA/src/core/settings-manager.ts:978</td><td>压缩与分支摘要（第 92 页）</td></tr><tr><td>branchSummary.skipPrompt</td><td>boolean</td><td>false</td><td>跳过「Summarize branch?」，默认不做摘要</td><td>压缩与分支摘要（第 92 页）</td></tr></table>

Compaction values must be non-negative safe integers; anything else throws when the getter runs. Validation is in the compaction token getter CA/src/core/settings-manager.ts:935.

压缩相关的取值必须是非负安全整数；其他取值会在 getter 执行时抛错。校验位于压缩 token 的 getter 中 CA/src/core/settings-manager.ts:935。

压缩相关的取值必须是非负安全整数；其他取值会在 getter 执行时抛错。校验位于压缩 token 的 getter 中 CA/src/core/settings-manager.ts:935。

## Network, retries and cost

## 网络、重试与成本

## 网络、重试与成本

<table><tr><td>键</td><td>类型</td><td>默认值</td><td>效果</td><td>参见</td></tr><tr><td>retry.enabled</td><td>boolean</td><td>true</td><td>在智能体层面重试瞬时错误 CA/src/core/settings-manager.ts:988</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>retry.maxRetries</td><td>number</td><td>3</td><td>智能体层面的尝试次数</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>retry.baseDelayMs</td><td>number</td><td>2000</td><td>首次退避延时；每次尝试翻倍 CA/src/core/settings-manager.ts:1004</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>retry.maxAgentDelayMs</td><td>number</td><td>60000</td><td>智能体层面最长的延时；DEFAULT_MAX_AGENT_RETRY_DELAY_MS ai/utils/retry.ts:124</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>retry.provider.timeoutMs</td><td>number</td><td>httpIdleTimeoutMs</td><td>供应商请求超时 CA/src/core/sdk.ts:332</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>retry.provider.maxRetries</td><td>number</td><td>0</td><td>pi-ai 内部的重试次数；默认值来自 retryProviderRequest() ai/utils/provider-retry.ts:109</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>retry.provider.maxRetryDelayMs</td><td>number</td><td>60000</td><td>可接受的、服务器请求的最长延时 CA/src/core/settings-manager.ts:1038</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>httpIdleTimeoutMs</td><td>number</td><td>300000</td><td>响应头与响应体的空闲超时；0 表示禁用 CA/src/core/http-dispatcher.ts:4</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>websocketConnectTimeoutMs</td><td>number</td><td>15000</td><td>OpenAI Codex 的 WebSocket 连接超时；0 表示禁用 ai/api/openai-codex-responses.ts:57</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>httpProxy</td><td>string</td><td>无</td><td>在 HTTP_PROXY 与 HTTPS_PROXY 未设置时复制到它们；仅全局 CA/src/core/http-dispatcher.ts:45</td><td>环境变量（第 185 页）</td></tr><tr><td>cacheWarming</td><td>"off" · "streaming" · "idle"</td><td>"streaming"</td><td>在运行期间（也可在两次运行之间）保持提示词缓存温热；仅全局，因为每次刷新都要花钱</td><td>认证、成本、重试与目录（第 41 页）</td></tr></table>

Two retry layers with diferent defaults. Agent retries are on by default; provider retries are of. getHttpIdleTimeoutMs() returns 300000, and a value of 0 becomes 2147483647 ms in the request options CA/src/core/sdk.ts:328.

两层重试的默认值各不相同。智能体层重试默认开启；供应商层重试默认关闭。`getHttpIdleTimeoutMs()` 返回 300000，而取值 0 在请求选项里会变成 2147483647 毫秒 CA/src/core/sdk.ts:328。

两层重试的默认值各不相同。智能体层重试默认开启；供应商层重试默认关闭。`getHttpIdleTimeoutMs()` 返回 300000，而取值 0 在请求选项里会变成 2147483647 毫秒 CA/src/core/sdk.ts:328。

## Resources, terminal and display

## 资源、终端与显示

## 资源、终端与显示

<table><tr><td>键</td><td>类型</td><td>默认值</td><td>效果</td><td>参见</td></tr><tr><td>packages</td><td>(string · {source, autoload?, extensions?, skills?, prompts?, themes?}) []</td><td>[]</td><td>npm、git 或本地包源</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>extensions、skills、prompts、themes</td><td>string[]</td><td>[]</td><td>本地路径；`!pattern`、`+path`、`-path` 过滤</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>enableSkillCommands</td><td>boolean</td><td>true</td><td>把每个技能注册为 /skill:name CA/src/core/settings-manager.ts:1265</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr></table>

Settings reference

设置参考

<table><tr><td>theme</td><td>string</td><td>&quot;system&quot;</td><td>主题名；initTheme() 回退到 system CA/src/modes/interactive/theme/theme.ts:757</td><td>上下文文件、技能、模板、主题与包（第 106 页）</td></tr><tr><td>quietStartup</td><td>boolean · &quot;header&quot;</td><td>false</td><td>true 隐藏启动页眉和资源清单；&quot;header&quot; 保留页眉 CA/src/core/settings-manager.ts:1089</td><td>运行模式（第 127 页）</td></tr><tr><td>collapseChangelog</td><td>boolean</td><td>false</td><td>更新后以精简形式显示更新日志</td><td>遥测与评测（第 179 页）</td></tr><tr><td>tuiMode</td><td>&quot;fullscreen&quot; · &quot;regular&quot;</td><td>&quot;fullscreen&quot;</td><td>交互渲染器模式 CA/src/core/settings-manager.ts:1349</td><td>pi-tui（第 158 页）</td></tr><tr><td>fullscreenExitOutput</td><td>&quot;transcript&quot; · &quot;resume-hint&quot;</td><td>&quot;transcript&quot;</td><td>退出全屏时打印什么</td><td>pi-tui（第 158 页）</td></tr><tr><td>fullscreenScrollbar</td><td>&quot;auto&quot; · &quot;always&quot; · &quot;hidden&quot;</td><td>&quot;auto&quot;</td><td>记录（transcript）滚动条 CA/src/core/settings-manager.ts:1368</td><td>pi-tui（第 158 页）</td></tr><tr><td>fullscreenCopyOnSelect</td><td>boolean</td><td>true</td><td>自动复制选中的文本</td><td>pi-tui（第 158 页）</td></tr><tr><td>fullscreenWheelScrollLines</td><td>&quot;auto&quot; · number</td><td>&quot;auto&quot;</td><td>每次滚轮事件的行数，限制在 1-100 CA/src/core/settings-manager.ts:1389</td><td>pi-tui（第 158 页）</td></tr><tr><td>terminal.showImages</td><td>boolean</td><td>true</td><td>在支持的地方内联显示图像</td><td>pi-tui（第 158 页）</td></tr><tr><td>terminal.imageWidthCells</td><td>number</td><td>60</td><td>首选的内联图像宽度 CA/src/core/settings-manager.ts:1301</td><td>pi-tui（第 158 页）</td></tr><tr><td>terminal.images</td><td>&quot;kitty&quot; · &quot;iterm2&quot; · &quot;auto&quot; · false</td><td>&quot;auto&quot;</td><td>覆盖图像协议探测结果 CA/src/core/settings-manager.ts:1278</td><td>pi-tui（第 158 页）</td></tr><tr><td>terminal.hyperlinks、terminal.trueColor</td><td>boolean · &quot;auto&quot;</td><td>&quot;auto&quot;</td><td>覆盖 OSC 8 与真彩色探测结果</td><td>pi-tui（第 158 页）</td></tr><tr><td>terminal.clearOnShrink</td><td>boolean</td><td>false,or PI_CLEAR_ON_SHRINK=1</td><td>内容收缩时清空空行 CA/src/core/settings-manager.ts:1318</td><td>pi-tui（第 158 页）</td></tr><tr><td>terminal.showTerminalProgress</td><td>boolean</td><td>false</td><td>在终端标签页上显示 OSC 9;4 进度</td><td>pi-tui（第 158 页）</td></tr><tr><td>showHardwareCursor</td><td>boolean</td><td>false,or PI_HARDWARE_CURSOR=1</td><td>为 IME 定位光标时显示光标 CA/src/core/settings-manager.ts:1469</td><td>pi-tui（第 158 页）</td></tr><tr><td>markdown.mermaid</td><td>&quot;off&quot; · &quot;final&quot; · &quot;streaming&quot;</td><td>&quot;streaming&quot;</td><td>Mermaid 渲染 CA/src/core/settings-manager.ts:1512</td><td>pi-tui（第 158 页）</td></tr><tr><td>markdown.codeBlockIndent</td><td>string</td><td>two spaces</td><td>渲染出的代码块的前缀 CA/src/core/settings-manager.ts:1509</td><td>pi-tui（第 158 页）</td></tr><tr><td>hideThinkingBlock</td><td>boolean</td><td>false</td><td>在记录（transcript）中隐藏思考块</td><td>pi-tui（第 158 页）</td></tr></table>

Settings reference

设置参考

<table><tr><td>showCacheMissNotices</td><td>boolean</td><td>false</td><td>显示缓存未命中、预热、压缩用量与恢复提示</td><td>认证、成本、重试与目录（第 41 页）</td></tr><tr><td>editorPaddingX</td><td>number</td><td>0</td><td>编辑器内边距；setter 会限制到 0–3 CA/src/core/settings-manager.ts:1483</td><td>pi-tui（第 158 页）</td></tr><tr><td>outputPad</td><td>0 · 1</td><td>1</td><td>记录（transcript）内边距；任何非 0 值都按 1 处理 CA/src/core/settings-manager.ts:1489</td><td>pi-tui（第 158 页）</td></tr><tr><td>autocompleteMaxVisible</td><td>number</td><td>5</td><td>自动补全显示的行数；setter 会限制到 3–20 CA/src/core/settings-manager.ts:1503</td><td>pi-tui（第 158 页）</td></tr><tr><td>enableInstallTelemetry</td><td>boolean</td><td>true</td><td>安装 ping 与供应商归因头；PI_TELEMETRY 优先 CA/src/core/settings-manager.ts:1142</td><td>遥测与评测（第 179 页）</td></tr><tr><td>enableAnalytics</td><td>boolean</td><td>false</td><td>分析功能的选择加入；供实验性的首次运行设置使用</td><td>遥测与评测（第 179 页）</td></tr><tr><td>warnings.anthropicExtraUsage</td><td>boolean</td><td>true</td><td>当 Anthropic 订阅认证可能产生付费额外用量时发出警告；只有 false 才会关闭 CA/src/modes/interactive/interactive-mode.ts:5233</td><td>认证、成本、重试与目录（第 41 页）</td></tr></table>

The clamps live in the setters. editorPaddingX and autocompleteMaxVisible are clamped only when /settings writes them; a hand-edited value is returned as written.

这些上下界限制写在 setter 里。`editorPaddingX` 与 `autocompleteMaxVisible` 只在由 `/settings` 写入时才做限制；手工编辑过的值会按原样返回。

这些上下界限制写在 setter 里。`editorPaddingX` 与 `autocompleteMaxVisible` 只在由 `/settings` 写入时才做限制；手工编辑过的值会按原样返回。

Three keys are written by Pi and not meant to be edited: lastChangelogVersion, trackingId (created when analytics is enabled) and deviceId (a UUID created when a login first needs it, global only) CA/src/core/settings-manager.ts:157.

有三个键由 Pi 写入，不应手工修改：`lastChangelogVersion`、`trackingId`（启用分析功能时创建）和 `deviceId`（首次有登录需要时创建的 UUID，仅全局）CA/src/core/settings-manager.ts:157。

有三个键由 Pi 写入，不应手工修改：`lastChangelogVersion`、`trackingId`（启用分析功能时创建）和 `deviceId`（首次有登录需要时创建的 UUID，仅全局）CA/src/core/settings-manager.ts:157。

R . 5

## Source file index

## 源文件索引

## 源文件索引

Sixty-two rows name thefiles that own nearly every behaviour this book describes. Each gives the file's size at \`28dcce2\`, the symbols worth opening it for, and the section that explains them.

六十二行表格指出了本书所描述的几乎所有行为的归属文件。每一行给出该文件在 \`28dcce2\` 处的规模、值得为哪些符号打开它，以及解释它们的章节。

六十二行表格指出了本书所描述的几乎所有行为的归属文件。每一行给出该文件在 \`28dcce2\` 处的规模、值得为哪些符号打开它，以及解释它们的章节。

Every path below was checked to exist at commit 28dcce2, and every line number points at the named declaration. Line counts are wc -l of the file, blank lines and comments included; a row naming a directory counts its non-test .ts files. Paths use the book’s prefixes: ai/ = packages/ai/src/, agent/ = packages/agent/src/, CA/ = packages/coding-agent/, tui/ = packages/tui/src/; other packages are named from packages/.

下面每个路径都核对过在 28dcce2 处确实存在，每个行号都指向所说的声明。行数是对文件执行 `wc -l` 的结果，包含空行与注释；以目录为行的条目统计其中非测试的 `.ts` 文件。路径采用本书的前缀：`ai/` = `packages/ai/src/`，`agent/` = `packages/agent/src/`，`CA/` = `packages/coding-agent/`，`tui/` = `packages/tui/src/`；其他包从 `packages/` 起名。

下面每个路径都核对过在 28dcce2 处确实存在，每个行号都指向所说的声明。行数是对文件执行 `wc -l` 的结果，包含空行与注释；以目录为行的条目统计其中非测试的 `.ts` 文件。路径采用本书的前缀：`ai/` = `packages/ai/src/`，`agent/` = `packages/agent/src/`，`CA/` = `packages/coding-agent/`，`tui/` = `packages/tui/src/`；其他包从 `packages/` 起名。

pi-ai

pi-ai

<table><tr><td>FILE</td><td>LINES</td><td>OWNS</td><td>SEE</td></tr><tr><td>ai/types.ts</td><td>1,172</td><td>KnownApi:17·message types SystemMessage...Message:524-612·AssistantMessageEvent:769·ProviderRequestOptions:134</td><td>the streaming event protocol (p. 30)</td></tr><tr><td>ai/models.ts</td><td>1,261</td><td>stream():876·create Models:990·create Provider:1039·calculate Cost:1198·getSupportedThinkingLevels:1222·clampThinkingLevel:1233</td><td>providers and models (p. 24)</td></tr><tr><td>ai/utils/transcript.ts</td><td>237</td><td>transcript normalisation</td><td>the streaming event protocol (p. 30)</td></tr><tr><td>ai/api/transform-messages.ts</td><td>235</td><td>transform Messages:64,cross-provider replay</td><td>wire APIs and cross-provider hand-off (p. 36)</td></tr><tr><td>ai/auth/resolve.ts</td><td>217</td><td>resolveProviderAuth:33·refreshStoredOAuthCredential:119</td><td>auth, cost, retries and the catalog (p. 41)</td></tr><tr><td>ai/utils/overflow.ts·retry.ts·provider-retry.ts</td><td>188·255·125</td><td>context-overflow detection, retry policy</td><td>auth, cost, retries and the catalog (p. 41)</td></tr><tr><td>ai/env-api-keys.ts</td><td>195</td><td>API keys read from the environment</td><td>environment variables (p. 185)</td></tr><tr><td>ai/providers/faux.ts</td><td>710</td><td>the offline faux provider used by the capture kit</td><td>the life of one prompt (p. 15)</td></tr><tr><td>packages/ai/scripts/generate-models.ts</td><td>3,726</td><td>generator of the *.models.ts catalogs</td><td>providers and models (p. 24)</td></tr></table>

The provider layer in nine rows. ai/api/ holds the ten wire APIs; wire APIs and cross-provider hand-of (p. 36) lists them.

供应商层共九行。`ai/api/` 下是十种通信API；见「通信API与跨供应商转交」（第 36 页）的列举。

供应商层共九行。`ai/api/` 下是十种通信API；见「通信API与跨供应商转交」（第 36 页）的列举。

## pi-agent-core

## pi-agent-core

<table><tr><td>FILE</td><td>LINES</td><td>OWNS</td><td>SEE</td></tr><tr><td>agent/agent-loop.ts</td><td>940</td><td>run Loop :163 · steering polls :176, :204, :295 · follow-ups :302 · executeToolCallsParallel :586</td><td>the agent loop (p. 49)</td></tr><tr><td>agent/agent.ts</td><td>613</td><td>PendingMessageQueue :143 · process Events :565</td><td>the agent loop (p. 49)</td></tr><tr><td>agent/types.ts</td><td>529</td><td>AgentEvent, AgentMessage, loop configuration</td><td>agent events and the Agent class (p. 57)</td></tr></table>

The loop is three files. Line counts from wc -l at 28dcce2.

循环部分共三个文件。行数取自 28dcce2 处的 `wc -l`。

循环部分共三个文件。行数取自 28dcce2 处的 `wc -l`。

#### pi-coding-agent: core

#### pi-coding-agent：内核

#### pi-coding-agent：内核

<table><tr><td>FILE</td><td>LINES</td><td>OWNS</td><td>SEE</td></tr><tr><td>CA/src/core/agent-session.ts</td><td>4,383</td><td>constructor:474 · _handlePostAgentRun :1839 · prompt:1954 · _checkCompaction:2933 · reload :3646</td><td>AgentSession: wiring the runtime (p. 61)</td></tr><tr><td>CA/src/core/sdk.ts</td><td>468</td><td>createAgentSession :181 · provider header merge :337</td><td>RPC mode and the SDK (p. 133)</td></tr><tr><td>CA/src/core/system-prompt.ts</td><td>229</td><td>buildSystemPromptSections :128</td><td>system prompt construction (p. 75)</td></tr><tr><td>CA/src/core/tools/index · truncate · edit · edit-diff · bash · read</td><td>224 · 314 · 220 · 556 · 442 · 224</td><td>built-in tools, output truncation, edit matching</td><td>built-in tools (p. 81)</td></tr><tr><td>CA/src/core/session-manager.ts</td><td>2,013</td><td>JSONL session files, the entry tree</td><td>sessions, the JSONL tree (p. 86)</td></tr><tr><td>CA/src/core/compaction/compaction.ts</td><td>1,119</td><td>DEFAULT_COMPACTION_SETTINGS :126 · should Compact :267 · findProjectedCutPoint :802 · prepare Compaction :872 · compact :965</td><td>compaction and branch summaries (p. 92)</td></tr><tr><td>CA/src/core/model-runtime.ts</td><td>1,032</td><td>the coding agent&#x27;s ModelRuntime</td><td>providers and models (p. 24)</td></tr><tr><td>CA/src/core/settings-manager.ts</td><td>1,533</td><td>settings layers, defaultProjectTrust, enableInstallTelemetry :1142</td><td>configuration, models and auth (p. 99)</td></tr><tr><td>CA/src/config.ts</td><td>656</td><td>agent directory, config paths</td><td>configuration, models and auth (p. 99)</td></tr><tr><td>CA/src/core/model-config.ts · provider-composer.ts</td><td>346 · 732</td><td>models.json, custom providers</td><td>configuration, models and auth (p. 99)</td></tr><tr><td>CA/src/core/resource-loader.ts</td><td>1,283</td><td>resource discovery, loadProjectTrustExtensions :501, context files :642</td><td>context files, skills, templates, themes and packages (p. 106)</td></tr><tr><td>CA/src/core/package-manager.ts · skills.ts · prompt-templates.ts</td><td>2,760 · 514 · 320</td><td>packages, skills, prompt templates</td><td>context files, skills, templates, themes and packages (p. 106)</td></tr></table>

Most behaviour of the pi command lives under CA/src/core/. agent-session.ts alone is 4,383 lines.

pi 命令的大部分行为都在 `CA/src/core/` 之下。仅 `agent-session.ts` 就有 4,383 行。

pi 命令的大部分行为都在 `CA/src/core/` 之下。仅 `agent-session.ts` 就有 4,383 行。

#### pi-coding-agent: CLI and modes

#### pi-coding-agent：CLI 与各模式

#### pi-coding-agent：CLI 与各模式

<table><tr><td>FILE</td><td>LINES</td><td>OWNS</td><td>SEE</td></tr><tr><td>CA/src/main.ts</td><td>999</td><td>main :573 · offline mode :576 · session directory before trust :688</td><td>the life of one prompt (p. 15)</td></tr><tr><td>CA/src/cli/args.ts</td><td>469</td><td>flag parsing, --help text</td><td>CLI reference (p. 191)</td></tr><tr><td>CA/src/core/slash-commands.ts</td><td>44</td><td>built-in slash command list</td><td>slash commands and keybindings (p. 197)</td></tr><tr><td>CA/src/modes/print-mode.ts·json-event.ts</td><td>169 · 61</td><td>print and JSON modes</td><td>run modes (p. 127)</td></tr><tr><td>CA/src/modes/rpc/</td><td>1,797 in 4 files</td><td>RPC mode, JSONL framing, client, types</td><td>RPC mode and the SDK (p. 133)</td></tr><tr><td>CA/src/modes/interactive/</td><td>21,662 in 60 files</td><td>the TUI application; interactive-mode.ts is 7,072 lines</td><td>run modes (p. 127)</td></tr></table>

Four run modes, one entry point. Directory sizes count non-test .ts files.

四种运行模式，一个入口点。目录规模统计其中非测试的 `.ts` 文件。

四种运行模式，一个入口点。目录规模统计其中非测试的 `.ts` 文件。

## Security, telemetry and evals

## 安全、遥测与评测

## 安全、遥测与评测

<table><tr><td>FILE</td><td>LINES</td><td>OWNS</td><td>SEE</td></tr><tr><td>CA/src/core/project-trust.ts</td><td>96</td><td>resolveProjectTrusted:46</td><td>the security model (p. 174)</td></tr><tr><td>CA/src/core/trust-manager.ts</td><td>246</td><td>trust-requiring entries:30 · getProjectTrustOptions:67 · hasTrustRequiringProjectResources:186 · trust.json:214</td><td>the security model (p. 174)</td></tr><tr><td>CA/src/core/auth-storage.ts</td><td>506</td><td>auth.json mode and lock:25</td><td>the security model (p. 174)</td></tr><tr><td>CA/src/core/mcp-servers.ts</td><td>346</td><td>MCP config validation, OAuth URL rules:167</td><td>MCP (p. 144)</td></tr><tr><td>CA/src/core/resolve-config-value.ts</td><td>287</td><td>$VAR and !command values:140</td><td>configuration, models and auth (p. 99)</td></tr><tr><td>CA/src/core/telemetry.ts·provider-attribution.ts</td><td>13 · 97</td><td>PI_TELEMETRY switch · attribution headers</td><td>telemetry and evals (p. 179)</td></tr><tr><td>CA/src/core/experimental.ts</td><td>3</td><td>areExperimentalFeaturesEnabled</td><td>the monorepo in one page (p. 11)</td></tr><tr><td>packages/telemetry/src/index.ts·memory.ts</td><td>357 · 219</td><td>TelemetryContext, schemas · InMemoryTelemetryContext</td><td>telemetry and evals (p. 179)</td></tr><tr><td>packages/evals/src/harness.ts·cli.ts·report.ts</td><td>537 · 192 · 483</td><td>isolated eval sessions · comparison runner · lift report</td><td>telemetry and evals (p. 179)</td></tr><tr><td>CA/docs/security.md·containerization.md</td><td>99 · 183</td><td>the shipped security stance and isolation recipes</td><td>the security model (p. 174)</td></tr></table>

Trust and telemetry are small files with large consequences. The telemetry switch is 13 lines; the trust decision is 96.

信任与遥测都是小文件，却影响很大。遥测开关只有 13 行；信任判定有 96 行。

信任与遥测都是小文件，却影响很大。遥测开关只有 13 行；信任判定有 96 行。

## MCP, codemode and TUI

## MCP、codemode 与 TUI

## MCP、codemode 与 TUI

<table><tr><td>FILE</td><td>LINES</td><td>OWNS</td><td>SEE</td></tr><tr><td>CA/src/extensions/mcp/</td><td>4,103 in 11 files</td><td>the built-in MCP extension: config, OAuth, runtime, tools, /mcp</td><td>MCP (p. 144)</td></tr><tr><td>packages/mcp/src/client.ts</td><td>615</td><td>McpClient</td><td>MCP (p. 144)</td></tr><tr><td>packages/mcp/src/transports/·oauth/</td><td>822 in 4 · 1,304 in 7</td><td>stdio and streamable HTTP · the OAuth flow</td><td>MCP (p. 144)</td></tr><tr><td>CA/src/extensions/codemode/</td><td>1,300 in 6 files</td><td>the codemode tool, 256 MiB cap in execute .ts :55</td><td>codemode (p. 151)</td></tr><tr><td>packages/codemode/src/runtime/</td><td>1,138 in 4 files</td><td>QuickJS worker, host, prelude</td><td>codemode (p. 151)</td></tr><tr><td>packages/codemode/src/declarations.ts·source.ts</td><td>355 · 115</td><td>tool declarations for scripts, script source handling</td><td>codemode (p. 151)</td></tr><tr><td>tui/tui.ts·tui-main-screen.ts·tui-alt-screen.ts</td><td>1,493 · 655 · 1,778</td><td>differential renderer, main and alternate screens</td><td>pi-tui (p. 158)</td></tr><tr><td>tui/terminal.ts·keys.ts</td><td>554 · 1,401</td><td>terminal I/O, key parsing</td><td>pi-tui (p. 158)</td></tr><tr><td>tui/components/editor.ts</td><td>2,472</td><td>Editor :296, the prompt editor</td><td>pi-tui (p. 158)</td></tr></table>

Integrations sit in two places: a standalone library and a built-in extension that wires it in. Directory sizes count non-test .ts files.

集成代码分布在两处：一个独立库，以及把它接进来的内置扩展。目录规模统计其中非测试的 `.ts` 文件。

集成代码分布在两处：一个独立库，以及把它接进来的内置扩展。目录规模统计其中非测试的 `.ts` 文件。

## Experimental stack

## 实验特性栈

## 实验特性栈

<table><tr><td>FILE</td><td>LINES</td><td>OWNS</td><td>SEE</td></tr><tr><td>CA/src/experimental/</td><td>9,950 in 46 files</td><td>pi server, pi client, session worker, coordinator, Radius relay, durable and vacation demos</td><td>实验特性栈（第 166 页）</td></tr><tr><td>CA/src/experimental/commands.ts·server.ts·session-worker.ts</td><td>98 · 770 · 840</td><td>runExperimentalCommand :86 · server directories :54 · Harness import :15</td><td>实验特性栈（第 166 页）</td></tr><tr><td>packages/durable/src/types.ts</td><td>1,085</td><td>TaskOutcome :449 · TaskState :486 · Storage.commit :997</td><td>实验特性栈（第 166 页）</td></tr><tr><td>packages/durable/src/harness/</td><td>6,756 in 22 files</td><td>GenerationTask, ToolTask (:50 in tool.ts), CompactionTask, defaults in agent.ts</td><td>实验特性栈（第 166 页）</td></tr><tr><td>packages/durable/src/storage/·env/</td><td>2,926 in 9 · 2,250 in 5</td><td>memory, SQLite, JSONL backends · ExecutionEnv, NodeExecutionEnv</td><td>实验特性栈（第 166 页）</td></tr><tr><td>packages/durable/docs/spec.md</td><td>4,692</td><td>the normative “Pico5 specification”</td><td>实验特性栈（第 166 页）</td></tr><tr><td>packages/env/src/connection.ts·ssh.ts</td><td>384 · 530</td><td>frame codec, liveness · ssh Arguments :77, deploy Daemon :396</td><td>实验特性栈（第 166 页）</td></tr><tr><td>packages/env/docs/protocol.md</td><td>114</td><td>the daemon wire protocol</td><td>实验特性栈（第 166 页）</td></tr><tr><td>packages/chord/src/delta/index.ts·facets/host.ts·services/provider.ts</td><td>694 · 906 · 633</td><td>Op :32 · FacetHost.reload :423 · subscriber buffer :453</td><td>实验特性栈（第 166 页）</td></tr></table>

Source file index

源文件索引

<table><tr><td>packages/protocol/src/protocol.ts·framing.ts</td><td>110·151</td><td>PROTOCOL_VERSION:5、信封 · 16 MiB 帧:6</td><td>实验特性栈（第 166 页）</td></tr><tr><td>packages/server/src/server.ts·transports/unix/listener.ts</td><td>576·421</td><td>握手超时:42 · socket 模式:11</td><td>实验特性栈（第 166 页）</td></tr><tr><td>packages/client/src/client.ts·unix.ts</td><td>479·299</td><td>Client、reconnect:134、discoverUnixServers:37</td><td>实验特性栈（第 166 页）</td></tr></table>

The experimental wiring in the coding agent alone is 9,950 lines. None of it is in the npm package or the binary; the monorepo in one page (p. 11) shows how it is excluded.

仅编码智能体里的实验性接线就有 9,950 行。它们都不在 npm 包或二进制文件中；「一页看懂 monorepo」（第 11 页）说明了它们是如何被排除的。

仅编码智能体里的实验性接线就有 9,950 行。它们都不在 npm 包或二进制文件中；「一页看懂 monorepo」（第 11 页）说明了它们是如何被排除的。

Sources: wc -l and ls of every listed path at 28dcce2; line numbers read from each file; directory rows count the nontest .ts files found by find

来源：在 28dcce2 处对每个列出的路径执行 `wc -l` 与 `ls`；行数逐个文件读取；目录行统计 `find` 找到的非测试 `.ts` 文件。

来源：在 28dcce2 处对每个列出的路径执行 `wc -l` 与 `ls`；行数逐个文件读取；目录行统计 `find` 找到的非测试 `.ts` 文件。

R . 6

## Documentation versus code

## 文档与代码的差异

## 文档与代码的差异

Pi's shipped docs are close to the code but not identical; sixteen gaps survive at this commit, and in every one the code is what runs.

Pi 随包的文档与代码很接近，但并不完全一致；在当前这个提交上仍有十六处差异，而且每一处都是代码说了算。

Pi 随包的文档与代码很接近，但并不完全一致；在当前这个提交上仍有十六处差异，而且每一处都是代码说了算。

This book follows the code wherever it and the shipped documentation disagree, and marks each place with a DOC ≠ CODE callout. This section collects every such gap in one table. Each row was re-checked against the checkout at 28dcce2: the doc text was found at the cited file and line, and the behaviour was read in the code. A gap counts if the docs say something the code does not do, or stay silent about behaviour that surprises a reader who trusts them.

凡随包文档与代码不一致之处，本书一律以代码为准，并用 DOC ≠ CODE 标注。本节把这类差异汇成一张表。每一行都在 28dcce2 处对照检出重新核对：文档原文在所引的文件与行号处找到，行为则从代码中读出。如果文档说了代码并不做的事，或者对会让信任它的读者感到意外的行为只字不提，就算一处差异。

凡随包文档与代码不一致之处，本书一律以代码为准，并用 DOC ≠ CODE 标注。本节把这类差异汇成一张表。每一行都在 28dcce2 处对照检出重新核对：文档原文在所引的文件与行号处找到，行为则从代码中读出。如果文档说了代码并不做的事，或者对会让信任它的读者感到意外的行为只字不提，就算一处差异。

## The gaps

## 差异清单

## 差异清单

<table><tr><td>#</td><td>文档的说法（文件）</td><td>代码的行为（文件:行号）</td><td>参见</td></tr><tr><td>1</td><td>来自其他供应商的思考「被转换成带标签的文本」 packages/ai/README.md:1525</td><td>是一个不带任何标签、装着思考内容的纯文本块；被打码的思考会被丢弃 ai/api/transform-messages.ts:113</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>2</td><td>「默认情况下，是一个 UUID」 CA/docs/session-format.md:14</td><td>是一个按时间排序的 UUID 版本 7，来自 uuidv7() CA/src/core/session-manager.ts:265</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>3</td><td>「『叶子』是树中的当前位置」，没有说明重开时如何处理 CA/docs/session-format.md:215</td><td>叶子并不存储；加载时它是文件顺序中的最后一个条目，无论那属于哪个分支 CA/src/core/session-manager.ts:1111</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>4</td><td>Session 名由 /name、--name 或 pi.setSessionName() 设置 CA/docs/session-format.md:201</td><td>getSessionName() 返回文件顺序中最后一个 session_info，与当前分支无关；传入空名会清除它 CA/src/core/session-manager.ts:1322</td><td>Session 与 JSONL 树（第 86 页）</td></tr><tr><td>5</td><td>--append-system-prompt 「把文本或一个已有文件追加到系统提示词」 CA/docs/cli.md:232</td><td>任何 --append-system-prompt 都会替换探测到的 APPEND_SYSTEM.md；该文件只在没有给标志时才使用 CA/src/core/resource-loader.ts:659</td><td>系统提示词构建（第 75 页）</td></tr><tr><td>6</td><td>「项目设置覆盖智能体目录设置」，且「资源列表会被合并」 CA/docs/settings.md:3</td><td>只有包管理器会合并它们，且是分别读取两个文件 CA/src/core/package-manager.ts:922；通用合并会替换数组 CA/src/core/settings-manager.ts:195，因此 getSkillPaths() 只返回项目列表</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>7</td><td>对文件语法只字未提</td><td>models.json 可以包含注释，由 stripJsonComments() 剥离 CA/src/core/model-config.ts:310；settings.json 用的是普通 JSON.parse()，会拒绝注释 CA/src/core/settings-manager.ts:487</td><td>配置、模型与认证（第 99 页）</td></tr><tr><td>8</td><td>「拥有并导出」AGENT_TELEMETRY_SCHEMAS、startAiSpan、startHarnessSpan 以及 AI 与 harness schema packages/telemetry/README.md:371</td><td>这些符号在 packages/agent、packages/ai、packages/coding-agent 中任何一处都不存在</td><td>遥测与评测（第 179 页）</td></tr><tr><td>9</td><td>CustomAgentMessages 的文档注释用 declare module "@mariozechner/agent" 扩展它 agent/types.ts:357</td><td>该模块实际是 @earendil-works/pi-agent-core；连旧别名也是 @mariozechner/pi-agent-core CA/src/core/extensions/virtual-modules.ts:31；扩展文档里写的那个名字两者都碰不到</td><td>智能体事件与 Agent 类（第 57 页）</td></tr><tr><td>10</td><td>PI_OFFLINE「设为 1/true/yes 时」禁用网络操作 CA/src/cli/args.ts:455</td><td>大多数调用点判断的是该变量是否存在，因此 PI_OFFLINE=0 仍会禁用版本检查、目录刷新、包更新检查和安装 ping CA/src/utils/version-check.ts:55 CA/src/core/model-runtime.ts:239</td><td>环境变量（第 185 页）</td></tr><tr><td>11</td><td>requiresThinkingAsText 意味着「转换成带分隔符的文本块」 ai/types.ts:808</td><td>适配器把思考作为不带分隔符的纯文本块输出 ai/api/openai-completions.ts:1324</td><td>通信 API 与跨供应商转交（第 36 页）</td></tr><tr><td>12</td><td>entry_appended 在「某个扩展通过 pi.appendEntry() 追加了一条自定义 Session 条目」时触发 CA/docs/json.md:122</td><td>它从 AgentSession 的五处发出，对消息条目从不触发；单轮采集追加了五条消息却一次也没触发</td><td>AgentSession：接好运行时（第 61 页）</td></td></tr><tr><td>13</td><td>HTTP 错误中「瞬时状态码（408、429 和 5xx）会重试两次」 CA/docs/mcp.md:100</td><td>5xx 会重试，但 501 除外 CA/src/extensions/mcp/runtime.ts:72</td><td>MCP（第 144 页）</td></tr><tr><td>14</td><td>「当一个 exposure 为 codemode 的服务器连上时，Pi 会启用 codemode」 CA/docs/mcp.md:204，CA/src/extensions/mcp/config.ts:29 也是这么写的</td><td>codemode 在 Session 开始时就根据配置启用，早于任何服务器连上</td><td>codemode（第 151 页）</td></tr><tr><td>15</td><td>比 width 更宽的行会让「TUI ... 报错」 tui/README.md:260 tui/README.md:798</td><td>在默认的全屏模式下，该行被静默截断到 width；回滚渲染器只在差分帧上才抛错</td><td>pi-tui（第 158 页）</td></tr><tr><td>16</td><td>project-trust 示例建议在「一个包含 .pi、AGENTS.md/CLAUDE.md 或 .agents/skills 的项目里」 CA/examples/extensions/project-trust.ts:13</td><td>单独的 .pi 目录或上下文文件都不会触发信任判定 CA/src/core/trust-manager.ts:186</td><td>安全模型（第 174 页）</td></td></tr></table>

Sixteen gaps between the shipped docs and the code at 28dcce2. Rows 1–9 were listed in the draft edition and re-verified; rows 10–16 were found while writing this edition, each in the section named in SEE. Doc paths are relative to the repository root unless prefixed.

在 28dcce2 处，随包文档与代码之间共有十六处差异。第 1–9 行曾列在草稿版中并已重新验证；第 10–16 行是撰写本版时发现的，每一处都出现在「参见」所指的章节里。文档路径除带前缀者外，均相对于仓库根目录。

在 28dcce2 处，随包文档与代码之间共有十六处差异。第 1–9 行曾列在草稿版中并已重新验证；第 10–16 行是撰写本版时发现的，每一处都出现在「参见」所指的章节里。文档路径除带前缀者外，均相对于仓库根目录。

## What each gap costs

## 每处差异的代价

## 每处差异的代价

1 · Thinking tags: a model receiving another provider’s history sees reasoning as ordinary assistant text. Prompt logic that looks for <thinking> finds nothing.

1 · 思考标签：收到其他供应商历史记录的模型，会把推理内容当成普通的助手文本。查找 `<thinking>` 的提示词逻辑什么也找不到。

1 · 思考标签：收到其他供应商历史记录的模型，会把推理内容当成普通的助手文本。查找 `<thinking>` 的提示词逻辑什么也找不到。

2 · Session id: ids sort by creation time. Code that parses the id as a random v4 UUID, or assumes no ordering, is wrong in the other direction. A caller-supplied --session-id need not be a UUID at all CA/src/core/session-manager.ts:268.

2 · Session id：id 按创建时间排序。把该 id 当作随机 v4 UUID 解析的代码，或假设它没有顺序的代码，反过来就错了。调用方自行给出的 `--session-id` 根本不必是 UUID CA/src/core/session-manager.ts:268。

2 · Session id：id 按创建时间排序。把该 id 当作随机 v4 UUID 解析的代码，或假设它没有顺序的代码，反过来就错了。调用方自行给出的 `--session-id` 根本不必是 UUID CA/src/core/session-manager.ts:268。

3 · Leaf: navigate to an older branch with /tree, quit before anything is appended, and reopen: the session resumes on the branch that holds the last-written entry, not where you left it.

3 · 叶子：用 `/tree` 导航到一条较早的分支，在追加任何内容之前退出，然后重开：Session 恢复在持有最后写入条目的那条分支上，而不是你离开时所在的位置。

3 · 叶子：用 `/tree` 导航到一条较早的分支，在追加任何内容之前退出，然后重开：Session 恢复在持有最后写入条目的那条分支上，而不是你离开时所在的位置。

4 · Session name: naming a session on one branch renames it on every branch, and the footer, which calls getSessionName() on every frame, keeps the most recent name after you switch branch.

4 · Session 名：在一条分支上给 Session 命名，会把它在所有分支上都改名；而页脚每帧都会调用 `getSessionName()`，所以切换分支后它仍保留最近一次取到的名字。

4 · Session 名：在一条分支上给 Session 命名，会把它在所有分支上都改名；而页脚每帧都会调用 `getSessionName()`，所以切换分支后它仍保留最近一次取到的名字。

5 · Append prompt: a CLI flag silently drops the user’s or project’s APPEND_SYSTEM.md. Pass its content again with a second flag if you need both.

5 · 追加提示词：一个 CLI 标志会悄悄丢掉用户或项目的 APPEND_SYSTEM.md。如果两者都需要，就再用第二个标志把它的内容传一遍。

5 · 追加提示词：一个 CLI 标志会悄悄丢掉用户或项目的 APPEND_SYSTEM.md。如果两者都需要，就再用第二个标志把它的内容传一遍。

6 · Resource lists: package, extension, skill, prompt and theme loading through PackageManager sees both lists. Anything that reads the merged Settings object, such as the experimental durable harness CA/src/experimental/durable/prompt.ts:34, sees only the project list once the project sets one.

6 · 资源列表：通过 PackageManager 进行的包、扩展、技能、提示词和主题加载会看到两份清单。而任何读取合并后 Settings 对象的东西——例如实验性的 durable harness CA/src/experimental/durable/prompt.ts:34——一旦项目设置了清单，就只能看到项目那一份。

6 · 资源列表：通过 PackageManager 进行的包、扩展、技能、提示词和主题加载会看到两份清单。而任何读取合并后 Settings 对象的东西——例如实验性的 durable harness CA/src/experimental/durable/prompt.ts:34——一旦项目设置了清单，就只能看到项目那一份。

7 · Comments: a comment copied from models.json into settings.json makes that whole file unreadable. The load error is recorded and the layer is treated as empty CA/src/core/settings-manager.ts:499.

7 · 注释：把 models.json 里的注释复制进 settings.json，会让整个文件无法读取。加载错误会被记录下来，该层被视为空 CA/src/core/settings-manager.ts:499。

7 · 注释：把 models.json 里的注释复制进 settings.json，会让整个文件无法读取。加载错误会被记录下来，该层被视为空 CA/src/core/settings-manager.ts:499。

8 · Telemetry schemas: the README’s import example names exports that 1.0.4 does not have.

8 · 遥测 schema：README 的 import 示例里点名了 1.0.4 并不存在的导出。

8 · 遥测 schema：README 的 import 示例里点名了 1.0.4 并不存在的导出。

9 · Module name: the example augments a module that does not exist, so CustomAgentMessages in pi-agent-core gains nothing. Augment @earendil-works/pi-agent-core instead.

9 · 模块名：示例扩展的是一个并不存在的模块，因此 pi-agent-core 中的 CustomAgentMessages 什么也没得到。应当扩展 @earendil-works/pi-agent-core。

9 · 模块名：示例扩展的是一个并不存在的模块，因此 pi-agent-core 中的 CustomAgentMessages 什么也没得到。应当扩展 @earendil-works/pi-agent-core。

10 · PI_OFFLINE=0: setting the variable to a false-looking value is not the same as unsetting it.

10 · PI_OFFLINE=0：把变量设成一个看着像假的值，与不设置它并不是一回事。

10 · PI_OFFLINE=0：把变量设成一个看着像假的值，与不设置它并不是一回事。

11 · Delimiters: the same efect as gap 1, on the OpenAI-compatible path.

11 · 分隔符：在 OpenAI 兼容路径上，与差异 1 同样的效果。

11 · 分隔符：在 OpenAI 兼容路径上，与差异 1 同样的效果。

12 · entry_appended: a client that waits for it after every message never sees one.

12 · entry_appended：每条消息之后都等它的客户端，永远等不到。

12 · entry_appended：每条消息之后都等它的客户端，永远等不到。

13 · 501: a server that answers 501 Not Implemented fails at once instead of after two retries.

13 · 501：返回 501 Not Implemented 的服务器会立刻失败，而不是重试两次之后才失败。

13 · 501：返回 501 Not Implemented 的服务器会立刻失败，而不是重试两次之后才失败。

14 · Codemode start: the codemode tool exists before any MCP server is reachable; scripts wait for the servers they name.

14 · Codemode 启动：在任何 MCP 服务器可达之前，codemode 工具就已经存在；脚本要等它们所点名的服务器。

14 · Codemode 启动：在任何 MCP 服务器可达之前，codemode 工具就已经存在；脚本要等它们所点名的服务器。

15 · Over-wide lines: a component that overflows is clipped, not reported, in the default mode, so the bug shows only in scrollback mode.

15 · 过宽的行：在默认模式下，溢出的组件会被裁剪而不是被报告，因此这个 bug 只在回滚模式下才显现。

15 · 过宽的行：在默认模式下，溢出的组件会被裁剪而不是被报告，因此这个 bug 只在回滚模式下才显现。

16 · Trust trigger: opening a project with only AGENTS.md asks nothing, and the example’s test instructions do not reproduce the prompt.

16 · 信任触发条件：打开一个只有 AGENTS.md 的项目不会问任何问题，示例中的测试步骤也复现不出那个询问。

16 · 信任触发条件：打开一个只有 AGENTS.md 的项目不会问任何问题，示例中的测试步骤也复现不出那个询问。

D O C ≠ C O D E

文档 ≠ 代码

文档 ≠ 代码

Gap 10 has a second edge. main() parses the flag strictly CA/src/main.ts:576, so PI_OFFLINE=0 does not set PI_SKIP_VERSION_CHECK and does not stop package auto-install CA/src/core/package-manager.ts:55. The same process then skips catalog refresh and the version request because the variable is present. Unset it to go online.

差异 10 还有另一面。`main()` 严格解析该标志 CA/src/main.ts:576，因此 `PI_OFFLINE=0` 不会设置 `PI_SKIP_VERSION_CHECK`，也阻止不了包自动安装 CA/src/core/package-manager.ts:55。而同一个进程又会因为该变量存在而跳过目录刷新和版本请求。要联网就把它取消设置。

差异 10 还有另一面。`main()` 严格解析该标志 CA/src/main.ts:576，因此 `PI_OFFLINE=0` 不会设置 `PI_SKIP_VERSION_CHECK`，也阻止不了包自动安装 CA/src/core/package-manager.ts:55。而同一个进程又会因为该变量存在而跳过目录刷新和版本请求。要联网就把它取消设置。

## Closed since the draft

## 草稿版之后已修复

## 草稿版之后已修复

The draft edition listed one more gap: discovery of project .agents/skills directories was gated on project trust CA/src/core/package-manager.ts:2460 but undocumented. At 28dcce2 the docs list it among the resources protected by project trust CA/docs/security.md:43, so it is no longer a gap and is not in the table.

草稿版还列了另外一处差异：项目 `.agents/skills` 目录的发现受项目信任控制 CA/src/core/package-manager.ts:2460，却没有文档说明。在 28dcce2 处，文档已把它列为受项目信任保护的资源之一 CA/docs/security.md:43，因此它不再是差异，也不在表中。

草稿版还列了另外一处差异：项目 `.agents/skills` 目录的发现受项目信任控制 CA/src/core/package-manager.ts:2460，却没有文档说明。在 28dcce2 处，文档已把它列为受项目信任保护的资源之一 CA/docs/security.md:43，因此它不再是差异，也不在表中。

Sources: packages/ai/README.md §cross-provider hand-off; ai/api/transform-messages.ts (transform Messages); CA/docs/session-format.md; CA/src/core/session-manager.ts (createSessionId, _buildIndex, getSessionName); CA/docs/cli.md; CA/src/cli/args.ts (help); CA/src/core/resource-loader.ts (reload, append sources); CA/docs/settings.md; CA/src/core/settings-manager.ts (deepMergeObjects, loadFromStorage); CA/src/core/package-manager.ts (resolve, isOfflineModeEnabled, skill discovery); CA/src/core/model-config.ts; packages/telemetry/README.md; agent/types.ts (CustomAgentMessages); CA/src/core/extensions/virtual-modules.ts; CA/src/utils/version-check.ts; CA/src/core/modelruntime.ts; CA/src/main.ts; CA/docs/security.md; CA/docs/json.md; CA/docs/mcp.md; CA/src/extensions/mcp/runtime.ts, config.ts; tui/README.md; CA/examples/extensions/project-trust.ts; CA/src/core/trust-manager.ts

来源：`packages/ai/README.md` §cross-provider hand-off；`ai/api/transform-messages.ts`（`transformMessages`）；`CA/docs/session-format.md`；`CA/src/core/session-manager.ts`（`createSessionId`、`_buildIndex`、`getSessionName`）；`CA/docs/cli.md`；`CA/src/cli/args.ts`（帮助）；`CA/src/core/resource-loader.ts`（`reload`、追加来源）；`CA/docs/settings.md`；`CA/src/core/settings-manager.ts`（`deepMergeObjects`、`loadFromStorage`）；`CA/src/core/package-manager.ts`（`resolve`、`isOfflineModeEnabled`、技能发现）；`CA/src/core/model-config.ts`；`packages/telemetry/README.md`；`agent/types.ts`（`CustomAgentMessages`）；`CA/src/core/extensions/virtual-modules.ts`；`CA/src/utils/version-check.ts`；`CA/src/core/model-runtime.ts`；`CA/src/main.ts`；`CA/docs/security.md`；`CA/docs/json.md`；`CA/docs/mcp.md`；`CA/src/extensions/mcp/runtime.ts`、`config.ts`；`tui/README.md`；`CA/examples/extensions/project-trust.ts`；`CA/src/core/trust-manager.ts`

R . 7

## Glossary

## 术语表

## 术语表

The vocabulary ofPi as this book uses it, one line per term, each used in exactly this sense throughout.

本书使用的 Pi 词汇表，每个词条一行，全书都按这里的含义使用。

本书使用的 Pi 词汇表，每个词条一行，全书都按这里的含义使用。

Agent directory: \~/.pi/agent, or PI_CODING_AGENT_DIR; holds global settings, auth, models, sessions and themes. See configuration, models and auth (p. 99).

智能体目录（agent directory）：\~/.pi/agent，或由 PI_CODING_AGENT_DIR 指定；存放全局设置、认证、模型、Session 与主题。见「配置、模型与认证」（第 99 页）。

智能体目录（agent directory）：\~/.pi/agent，或由 PI_CODING_AGENT_DIR 指定；存放全局设置、认证、模型、Session 与主题。见「配置、模型与认证」（第 99 页）。

AgentSession: the coding agent’s runtime object; wraps the Agent, persists every step to the session file and emits agent_settled. See AgentSession: wiring the runtime (p. 61).

AgentSession：编码智能体的运行时对象；封装 Agent，把每一步持久化到 Session 文件，并发出 agent_settled。见「AgentSession：接好运行时」（第 61 页）。

AgentSession：编码智能体的运行时对象；封装 Agent，把每一步持久化到 Session 文件，并发出 agent_settled。见「AgentSession：接好运行时」（第 61 页）。

Branch summary: a branch_summary entry that condenses the path you leave when navigating the tree. See compaction and branch summaries (p. 92).

分支摘要（branch summary）：一条 branch_summary 条目，把你在树中导航时离开的那段路径浓缩起来。见「压缩与分支摘要」（第 92 页）。

分支摘要（branch summary）：一条 branch_summary 条目，把你在树中导航时离开的那段路径浓缩起来。见「压缩与分支摘要」（第 92 页）。

Codemode: the codemode tool; the model writes JavaScript that runs in QuickJS and calls other tools through tools.*. See codemode (p. 151).

Codemode：即 codemode 工具；模型编写在 QuickJS 中运行的 JavaScript，通过 `tools.*` 调用其他工具。见 codemode（第 151 页）。

Codemode：即 codemode 工具；模型编写在 QuickJS 中运行的 JavaScript，通过 `tools.*` 调用其他工具。见 codemode（第 151 页）。

Compaction: replacing older context with a summary in a compaction entry, so the projection fits the context window. See compaction and branch summaries (p. 92).

压缩（compaction）：用一条 compaction 条目中的摘要替换较旧的上下文，使投影能装进上下文窗口。见「压缩与分支摘要」（第 92 页）。

压缩（compaction）：用一条 compaction 条目中的摘要替换较旧的上下文，使投影能装进上下文窗口。见「压缩与分支摘要」（第 92 页）。

Context edit: a context_edit entry that changes one earlier entry’s contribution to model context without rewriting the file. See sessions, the JSONL tree (p. 86).

上下文编辑（context edit）：一条 context_edit 条目，在不重写文件的前提下改变某条更早条目对模型上下文的贡献。见「Session 与 JSONL 树」（第 86 页）。

上下文编辑（context edit）：一条 context_edit 条目，在不重写文件的前提下改变某条更早条目对模型上下文的贡献。见「Session 与 JSONL 树」（第 86 页）。

Context file: AGENTS.override.md, AGENTS.md or CLAUDE.md, loaded into the system prompt regardless of project trust. See context files, skills, templates, themes and packages (p. 106).

上下文文件（context file）：AGENTS.override.md、AGENTS.md 或 CLAUDE.md，无论项目是否受信都会加载进系统提示词。见「上下文文件、技能、模板、主题与包」（第 106 页）。

上下文文件（context file）：AGENTS.override.md、AGENTS.md 或 CLAUDE.md，无论项目是否受信都会加载进系统提示词。见「上下文文件、技能、模板、主题与包」（第 106 页）。

DOC ≠ CODE: this book’s mark for a place where shipped docs and code disagree; the code is followed. See documentation versus code (p. 213).

DOC ≠ CODE：本书用来标记随包文档与代码不一致之处的记号；一律以代码为准。见「文档与代码的差异」（第 213 页）。

DOC ≠ CODE：本书用来标记随包文档与代码不一致之处的记号；一律以代码为准。见「文档与代码的差异」（第 213 页）。

Entry: one JSON line of a session file, with id, parentId and a type such as message or model_change. See sessions, the JSONL tree (p. 86).

条目（entry）：Session 文件中的一行 JSON，带有 id、parentId 以及 message、model_change 之类的类型。见「Session 与 JSONL 树」（第 86 页）。

条目（entry）：Session 文件中的一行 JSON，带有 id、parentId 以及 message、model_change 之类的类型。见「Session 与 JSONL 树」（第 86 页）。

Exposure: how a tool is reachable: direct, model-only, codemode, deferred or hidden. See extensions, loading and the API (p. 113).

暴露方式（exposure）：一个工具如何被触达：direct、model-only、codemode、deferred 或 hidden。见「扩展、加载与 API」（第 113 页）。

暴露方式（exposure）：一个工具如何被触达：direct、model-only、codemode、deferred 或 hidden。见「扩展、加载与 API」（第 113 页）。

Extension: a TypeScript module loaded at startup that registers tools, commands, providers and event handlers through ExtensionAPI. See extensions, loading and the API (p. 113).

扩展（Extension）：启动时加载的 TypeScript 模块，通过 ExtensionAPI 注册工具、命令、供应商与事件处理器。见「扩展、加载与 API」（第 113 页）。

扩展（Extension）：启动时加载的 TypeScript 模块，通过 ExtensionAPI 注册工具、命令、供应商与事件处理器。见「扩展、加载与 API」（第 113 页）。

Faux provider: the scripted pi-ai provider (faux/faux-1) used by tests and by this book’s capture kit. See the life of one prompt (p. 15).

faux 供应商：脚本化的 pi-ai 供应商（faux/faux-1），供测试与本书的采集工具使用。见「一条提示词的生命周期」（第 15 页）。

faux 供应商：脚本化的 pi-ai 供应商（faux/faux-1），供测试与本书的采集工具使用。见「一条提示词的生命周期」（第 15 页）。

Follow-up: a queued message delivered only when the agent would otherwise stop. See the agent loop (p. 49).

后续消息（follow-up）：只有在智能体本来就要停下时才投递的排队消息。见「智能体循环」（第 49 页）。

后续消息（follow-up）：只有在智能体本来就要停下时才投递的排队消息。见「智能体循环」（第 49 页）。

Leaf: the current position in the session tree; the next entry’s parent. Not stored in the file. See sessions, the JSONL tree (p. 86).

叶子（leaf）：Session 树中的当前位置，即下一条条目的父节点。它不存储在文件里。见「Session 与 JSONL 树」（第 86 页）。

叶子（leaf）：Session 树中的当前位置，即下一条条目的父节点。它不存储在文件里。见「Session 与 JSONL 树」（第 86 页）。

Project trust: the per-project decision that gates .pi/* settings and resources; not a security boundary. See the security model (p. 174).

项目信任（project trust）：按项目作出的判定，用来控制 `.pi/*` 设置与资源；它不是安全边界。见「安全模型」（第 174 页）。

项目信任（project trust）：按项目作出的判定，用来控制 `.pi/*` 设置与资源；它不是安全边界。见「安全模型」（第 174 页）。

Projection: the model-visible messages computed from the path to the leaf, after compaction and context edits. See sessions, the JSONL tree (p. 86).

投影（projection）：在压缩与上下文编辑之后，根据通往叶子的路径算出的、模型可见的消息集合。见「Session 与 JSONL 树」（第 86 页）。

投影（projection）：在压缩与上下文编辑之后，根据通往叶子的路径算出的、模型可见的消息集合。见「Session 与 JSONL 树」（第 86 页）。

Replay-safe: a durable tool registered with replay: "safe", which may rerun after a crash; the default is unsafe. See the experimental stack (p. 166).

可重放安全（replay-safe）：注册时带有 `replay: "safe"` 的 durable 工具，崩溃后可能重跑；默认是不安全的。见「实验特性栈」（第 166 页）。

可重放安全（replay-safe）：注册时带有 `replay: "safe"` 的 durable 工具，崩溃后可能重跑；默认是不安全的。见「实验特性栈」（第 166 页）。

Run: one prompt() or continue() of the agent, from agent_start to agent_end. See agent events and the Agent class (p. 57).

运行（run）：智能体的一次 `prompt()` 或 `continue()`，从 agent_start 到 agent_end。见「智能体事件与 Agent 类」（第 57 页）。

运行（run）：智能体的一次 `prompt()` 或 `continue()`，从 agent_start 到 agent_end。见「智能体事件与 Agent 类」（第 57 页）。

Run mode: how Pi is driven: interactive, print, JSON or RPC. See run modes (p. 127).

运行模式（run mode）：Pi 被如何驱动：interactive、print、JSON 或 RPC。见「运行模式」（第 127 页）。

运行模式（run mode）：Pi 被如何驱动：interactive、print、JSON 或 RPC。见「运行模式」（第 127 页）。

Session file: the append-only JSONL file holding one session’s tree of entries. See sessions, the JSONL tree (p. 86).

Session 文件（session file）：保存一个 Session 条目树的仅追加 JSONL 文件。见「Session 与 JSONL 树」（第 86 页）。

Session 文件（session file）：保存一个 Session 条目树的仅追加 JSONL 文件。见「Session 与 JSONL 树」（第 86 页）。

Settled: the state after a run when Pi will not continue on its own: retries, compaction and queued work are done; signalled by agent_settled. See from prompt() to agent_settled (p. 67).

落定（settled）：一次运行之后 Pi 不会自行继续的状态：重试、压缩与排队工作都已完成；由 agent_settled 标示。见「从 prompt() 到 agent_settled」（第 67 页）。

落定（settled）：一次运行之后 Pi 不会自行继续的状态：重试、压缩与排队工作都已完成；由 agent_settled 标示。见「从 prompt() 到 agent_settled」（第 67 页）。

Skill: a directory with a SKILL.md, listed in the system prompt and loaded by the model on demand. See context files, skills, templates, themes and packages (p. 106).

技能（skill）：一个含 SKILL.md 的目录，列在系统提示词中，由模型按需加载。见「上下文文件、技能、模板、主题与包」（第 106 页）。

技能（skill）：一个含 SKILL.md 的目录，列在系统提示词中，由模型按需加载。见「上下文文件、技能、模板、主题与包」（第 106 页）。

Steering: a queued message delivered after the current turn’s tool calls finish, before the next model call. See the agent loop (p. 49).

转向（steering）：在当前轮的工具调用结束之后、下一次模型调用之前投递的排队消息。见「智能体循环」（第 49 页）。

转向（steering）：在当前轮的工具调用结束之后、下一次模型调用之前投递的排队消息。见「智能体循环」（第 49 页）。

Thinking level: one of off, minimal, low, medium, high, xhigh, max; medium by default. See configuration, models and auth (p. 99).

思考级别（thinking level）：off、minimal、low、medium、high、xhigh、max 之一；默认为 medium。见「配置、模型与认证」（第 99 页）。

思考级别（thinking level）：off、minimal、low、medium、high、xhigh、max 之一；默认为 medium。见「配置、模型与认证」（第 99 页）。

Transcript system message: a system message whose sections, tools Added and tools Removed patch the prompt and tool set. See system prompt construction (p. 75).

记录系统消息（transcript system message）：一种系统消息，其 sections、toolsAdded 与 toolsRemoved 会对提示词和工具集打补丁。见「系统提示词构建」（第 75 页）。

记录系统消息（transcript system message）：一种系统消息，其 sections、toolsAdded 与 toolsRemoved 会对提示词和工具集打补丁。见「系统提示词构建」（第 75 页）。

Turn: one assistant response plus the tool calls it made and their results, from turn_start to turn_end. See the agent loop (p. 49).

轮次（turn）：一次助手响应，加上它发起的工具调用及其结果，从 turn_start 到 turn_end。见「智能体循环」（第 49 页）。

轮次（turn）：一次助手响应，加上它发起的工具调用及其结果，从 turn_start 到 turn_end。见「智能体循环」（第 49 页）。

Virtual model: an extension-registered catalog entry that routes each request to a physical model. See configuration, models and auth (p. 99).

虚拟模型（virtual model）：由扩展注册的目录条目，把每个请求路由到一个物理模型。见「配置、模型与认证」（第 99 页）。

虚拟模型（virtual model）：由扩展注册的目录条目，把每个请求路由到一个物理模型。见「配置、模型与认证」（第 99 页）。

Wire API: one of the ten request formats pi-ai speaks, such as anthropic-messages or openai-responses. See wire APIs and cross-provider hand-of (p. 36).

通信API（wire API）：pi-ai 所说的十种请求格式之一，例如 anthropic-messages 或 openai-responses。见「通信API与跨供应商转交」（第 36 页）。

通信API（wire API）：pi-ai 所说的十种请求格式之一，例如 anthropic-messages 或 openai-responses。见「通信API与跨供应商转交」（第 36 页）。

R . 8

## Sources and versions

## 来源与版本

## 来源与版本

Everything this book was checked against, with the revision it was checked at; a later commit can change any line number, and some defaults.

本书据以核对的一切材料，以及核对时所依据的修订；换一个更晚的提交，任何行号、乃至某些默认值都可能改变。

本书据以核对的一切材料，以及核对时所依据的修订；换一个更晚的提交，任何行号、乃至某些默认值都可能改变。

Every claim in this book traces to one of the sources below. The table names the revision each was read at and what it was used for, in order of authority. The list after it names what this edition could not confirm and therefore does not claim.

本书的每一条论断都可追溯到下列来源之一。表格按权威顺序列出各来源读取时的修订及其用途。随后的清单列出本版无法确认、因而不作断言的内容。

本书的每一条论断都可追溯到下列来源之一。表格按权威顺序列出各来源读取时的修订及其用途。随后的清单列出本版无法确认、因而不作断言的内容。

<table><tr><td>来源</td><td>版本</td><td>用于</td></tr><tr><td>earendil-works/pi monorepo, packages/*/src/**</td><td>commit28dcce2ba45ce4a9efeb0f5b686f0be830fd89b9, 2026-10-05 21:23:02 +0200</td><td>每一个类型、默认值、字段名、事件、错误消息与行为；每一处 file:line 引用</td></tr><tr><td>npm packages@earendil-works/pi-*(14 workspace packages; pi-evals private)</td><td>1.0.4, from each package.json at that commit</td><td>包名与版本；封面上的版本行</td></tr><tr><td>Shipped docs: packages/coding-agent/docs/*.md, package READMEs</td><td>same commit</td><td>作者所呈现的公开界面；「文档与代码的差异」（第 213 页）中的每一处 DOC ≠ CODE 对比</td></tr><tr><td>Tests and examples: packages/*/test/**, packages/coding-agent/examples/**</td><td>same commit</td><td>各章节引用到的边界行为与可运行的扩展示例代码</td></tr><tr><td>Node.js</td><td>v26.10.0 for the capture runs; the root and pi-coding-agent package.json declare &quot;node&quot;: &quot;&gt;=22.19.0&quot;</td><td>针对构建产物 dist/ 运行采集工具</td></tr><tr><td>Capture kit: research/capture/one-turn.mjs → research/out/one-turn.txt</td><td>this book, run against the pinned build</td><td>AgentSession 事件流（29 个事件）以及一轮 faux 供应商运行的 Session JSONL</td></tr><tr><td>Capture kit: research/capture/stats.py → research/out/stats.txt</td><td>this book, at the pinned commit</td><td>包行数、供应商目录、API 文件、扩展示例</td></tr><tr><td>Capture kit: per-section scripts in research/capture/(agent-loop-queues, auth-cost-retries-cost, built-in-tools-edit, codemode-sandbox, rpc-and-sdk-*, sessions-tree, streaming-protocol-events, tui-frames, wire-apis-transform)</td><td>this book, offline and deterministic except ids and timestamps</td><td>research/out/ 中的各份输出，即以其命名的那些章节所展示的内容</td></tr><tr><td>Pi Technical Manual, source/user/Pi-Technical-Manual.pdf</td><td>draft edition, 100 pages, headed 28dcce2 · v1.0.4</td><td>本版据以改写的草稿：其结构与知识；每一条保留的论断都已对照检出重新验证</td></tr></table>

One commit, one version, one capture kit. The draft’s text and page images, extracted to research/original/, were used only to find what to verify.

一个提交、一个版本、一套采集工具。草稿的文字与页面图像解压到 `research/original/`，仅用于确定需要核实什么。

一个提交、一个版本、一套采集工具。草稿的文字与页面图像解压到 `research/original/`，仅用于确定需要核实什么。

## Not verified, and therefore not claimed

## 未经验证因而不作断言

## 未经验证因而不作断言

Built-in thinking budgets. thinking Budgets falls back to per-provider budgets that were not traced; settings reference (p. 202) gives no numbers.

内置思考预算。`thinkingBudgets` 会回退到一些未能追溯来源的逐供应商预算；「设置参考」（第 202 页）没有给出具体数字。

内置思考预算。`thinkingBudgets` 会回退到一些未能追溯来源的逐供应商预算；「设置参考」（第 202 页）没有给出具体数字。

The efect of some display settings. shellCommandPrefix, fullscreenExitOutput, collapse Changelog and the 2000 × 2000 limit of images.auto Resize are described from their declarations and docs, not from the code that consumes them.

部分显示设置的实际效果。`shellCommandPrefix`、`fullscreenExitOutput`、`collapseChangelog` 以及 `images.autoResize` 的 2000 × 2000 上限，都是依据它们的声明与文档描述的，而非依据消费它们的代码。

部分显示设置的实际效果。`shellCommandPrefix`、`fullscreenExitOutput`、`collapseChangelog` 以及 `images.autoResize` 的 2000 × 2000 上限，都是依据它们的声明与文档描述的，而非依据消费它们的代码。

Where PI_TUI_DEBUG_REDRAW writes. The log goes to the TUI’s log directory; how that directory is chosen was not traced.

`PI_TUI_DEBUG_REDRAW` 写到哪里。日志会进入 TUI 的日志目录；但这个目录如何选定，未能追溯。

`PI_TUI_DEBUG_REDRAW` 写到哪里。日志会进入 TUI 的日志目录；但这个目录如何选定，未能追溯。

What the TypeScript compiler reports for gap 9. documentation versus code (p. 213) says the documented module augmentation reaches no module; the exact compiler diagnostic was not captured.

差异 9 中 TypeScript 编译器会报什么。「文档与代码的差异」（第 213 页）指出文档里的模块扩展够不到任何模块；但具体的编译诊断没有采集到。

差异 9 中 TypeScript 编译器会报什么。「文档与代码的差异」（第 213 页）指出文档里的模块扩展够不到任何模块；但具体的编译诊断没有采集到。

Codemode start-up time. The “about 20 ms” sandbox start-up in codemode (p. 151) is quoted from the package README; this edition did not time it.

Codemode 的启动耗时。codemode（第 151 页）中「约 20 ms」的沙箱启动时间引自该包的 README；本版没有实测。

Codemode 的启动耗时。codemode（第 151 页）中「约 20 ms」的沙箱启动时间引自该包的 README；本版没有实测。

Timings of real providers. Every captured run uses the faux provider, which streams in milliseconds; no timing in this book describes a network model.

真实供应商的耗时。所有采集到的运行都使用 faux 供应商，它在毫秒级内流完；本书没有任何耗时数据描述的是网络模型。

真实供应商的耗时。所有采集到的运行都使用 faux 供应商，它在毫秒级内流完；本书没有任何耗时数据描述的是网络模型。

The draft’s line counts. The draft edition’s per-package line counts (for example 26.4k for pi-ai) used an unknown method; the monorepo in one page (p. 11) replaces them with counts from stats.py, and the old numbers are not reproduced.

草稿中的行数。草稿版给出的逐包行数（例如 pi-ai 的 26.4k）采用了未知的方法；「一页看懂 monorepo」（第 11 页）用来自 `stats.py` 的计数取代了它们，旧数字不再沿用。

草稿中的行数。草稿版给出的逐包行数（例如 pi-ai 的 26.4k）采用了未知的方法；「一页看懂 monorepo」（第 11 页）用来自 `stats.py` 的计数取代了它们，旧数字不再沿用。

Windows behaviour. Windows-specific paths (PowerShell, notepad, self-update quarantine) are read from code; no capture exercised them.

Windows 上的行为。与 Windows 相关的路径（PowerShell、notepad、自我更新的隔离处理）都是从代码读出的；没有任何采集覆盖过它们。

Windows 上的行为。与 Windows 相关的路径（PowerShell、notepad、自我更新的隔离处理）都是从代码读出的；没有任何采集覆盖过它们。

R . 9

## Index of figures

## 插图索引

## 插图索引

Every figure in the book, with the claim it makes.

全书所有插图，以及每幅图所支撑的论断。

<table><tr><td>图号</td><td>内容</td><td>页码</td></tr><tr><td>1.1</td><td>被略去的五个特性中有四个在仓库里带有参考扩展；后台 bash 没有</td><td>9</td></tr><tr><td>1.2</td><td>CLI 比它所依赖的一切加起来还大</td><td>12</td></tr><tr><td>1.3</td><td>稳定版 CLI 运行在三个包串成的链条上</td><td>13</td></tr><tr><td>1.4</td><td>在模型看到之前，提示词已经落盘</td><td>16</td></tr><tr><td>1.5</td><td>一次运行结束于 `agent_settled`，而不是 `agent_end`</td><td>18</td></tr><tr><td>1.6</td><td>两轮、29 个事件、四次写入</td><td>20</td></tr><tr><td>2.1</td><td>一个集合、多个供应商、每种 API 一个线路文件</td><td>24</td></tr><tr><td>2.2</td><td>追加会保留已缓存的前缀；折叠则会重写它</td><td>29</td></tr><tr><td>2.3</td><td>一次开场、任意多个块、恰好一个终止事件</td><td>31</td></tr><tr><td>2.4</td><td>在认证解析完成之前调用方就持有了流</td><td>34</td></tr><tr><td>2.5</td><td>历史是为目标模型重写的，绝不为源模型重写</td><td>38</td></tr><tr><td>2.6</td><td>不存储任何东西，是通往环境的唯一途径</td><td>43</td></tr><tr><td>2.7</td><td>1,620 条目录记录：1,537 个对话模型、60 个图像模型和 23 个分类模型</td><td>46</td></tr><tr><td>3.1</td><td>只要还有东西需要回应，循环就一直转，只在三处停下</td><td>51</td></tr><tr><td>3.2</td><td>预检是串行的，执行是并发的，结果按源顺序返回</td><td>55</td></tr><tr><td>3.3</td><td>一次运行由轮次组成，一轮由消息组成，工具夹在助手消息与它的结果之间</td><td>58</td></tr><tr><td>3.4</td><td>`isStreaming` 在最后一个监听器返回后才被清除，而不是在发出 `agent_end` 时</td></td><td>59</td></tr><tr><td>3.5</td><td>Session 拥有智能体的钩子；智能体除了循环之外什么都不拥有</td><td>64</td></tr><tr><td>3.6</td><td>监听器看到消息时，它还没落盘</td><td>65</td></tr><tr><td>3.7</td><td>即使智能体正在流式输出，扩展命令照样运行；其他一切都排队或等待</td><td>68</td></tr><tr><td>3.8</td><td>一条提示词、两次运行、两个 `agent_end`、一个 `agent_settled`</td><td>70</td></tr><tr><td>4.1</td><td>自定义提示词替换的是四个区块，不是一个</td><td>75</td></tr><tr><td>4.2</td><td>更早的消息从不被重写</td><td>79</td></tr><tr><td>4.3</td><td>五种拒绝的方式，一种写入的方式</td><td>83</td></tr><tr><td>4.4</td><td>扩展看到的是校验过的参数，并且可以改动它们</td><td>84</td></tr><tr><td>4.5</td><td>每一行的 parentId 就是它前面那一行</td><td>88</td></tr><tr><td>4.6</td><td>标签就是树中的条目，而且它们会移动叶子</td><td>88</td></tr><tr><td>4.7</td><td>只有路径上最新的那次压缩才贡献摘要</td><td>90</td></tr></table>
