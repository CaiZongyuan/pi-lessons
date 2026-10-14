---
title: "MCP：从 mcp.json 到工具调用"
originalPage: 144
---

<div class="section-kicker">6.1 / INTEGRATION & INTERFACES</div>

# MCP：从 mcp\.json 到工具调用

---

<strong>Pi 1\.0 自带 MCP 客户端，并将每个服务器工具注册到常规工具流水线中。默认情况下，这些工具不会以声明的形式呈现给模型；模型通过 codemode 脚本访问它们。</strong>



Model Context Protocol（模型上下文协议）服务器是提供工具和资源的进程或 URL。Pi 不借助官方 SDK 便可连接服务器，将每个工具命名为 `mcp__<server>__<tool>`，并让每次调用走与 `read` 或 `bash` 相同的流水线，因此 `tool_call` 钩子和权限关卡照常生效。本节介绍实现这一机制的两层结构，以及客户端的连接和超时规则，随后说明配置文件及其信任规则、决定模型如何访问工具的四种暴露方式，以及服务器故障时哪些操作会重试。

## 两层结构



第一层是 `@earendil-works/pi-mcp` 1\.0\.4：“一个小型、独立的 Model Context Protocol 客户端，不依赖官方 MCP SDK 或其他 pi 包”（`mcp/README.md`）。它唯一的运行时依赖是 `cross-spawn` 7\.0\.6（`mcp/package.json`）。OAuth 代码“改编自采用 MIT 许可证的 Model Context Protocol TypeScript SDK v1\.29\.0”，其许可证随包附在 `LICENSES/` 下（`mcp/README.md` 的“OAuth”节）。



第二层是 `CA/src/extensions/mcp/` 中内置的 `mcp` 扩展。它注册为可替换的内置扩展：如果某个扩展注册了 `/mcp`，就会接替它，而不是与它并行运行（`CA/src/extensions/index.ts:9`）。与服务器通信的部分采用延迟加载，因此“未配置服务器的会话永远不必承担这部分开销”（`CA/src/extensions/mcp/index.ts:1021`）。



|<strong>文件</strong>|<strong>行数</strong>|<strong>负责内容</strong>|
|---|---|---|
|`index.ts`|1,225|生命周期、暴露方式、`mcp_servers` 提示词章节、`/mcp`|
|`cli.ts`|614|`pi mcp add` · `remove` · `list` · `login` · `logout`|
|`oauth.ts`|532|登录、`mcp-auth.json`、令牌刷新|
|`runtime.ts`|491|每台服务器一个连接、传输方式、重试|
|`resources.ts`|339|三个资源工具|
|`tools.ts`|335|工具名称、结果转换、20 KiB 截断|
|`ui.ts` · `config.ts` · `log.ts`|252 · 242 · 69|`/mcp` 管理器、`mcp.json`、`mcp.log`|



客户端是一个库；所有 Pi 专有逻辑都放在一个扩展中。行数来自提交 `28dcce2` 上的 `wc -l`；未计入两个各为 2 行的 `.lazy.ts` 加载器。

## 客户端



`McpClient` 使用协议版本 `2025-11-25`，也接受协商为 `2025-06-18`、`2025-03-26` 或 `2024-11-05` 的服务器（`mcp/src/protocol/types.ts:4`）。它有 `idle`、`connecting`、`connected` 和 `closed` 四种状态（`mcp/src/client.ts:41`）；除 `idle` 外，`connect()` 拒绝在任何其他状态下运行（`mcp/src/client.ts:202`）。



<BookFigure id="6.1" />

> 服务器只有通过版本检查并完成 `notifications/initialized` 后才可用。如果服务器选择了未列出的版本，就会报错“MCP 服务器选择了不受支持的协议版本……”并关闭客户端。步骤 1–3 为 `connect()`，步骤 4 为 `listAll`，步骤 5 为带进度通知的 `requestInternal`。来源：`mcp/src/client.ts`。
> 
> 



<strong>超时。</strong> 库中的请求会在 30 s 后超时（`mcp/src/client.ts:38`），而 Pi 中为 60 s；Pi 的每服务器配置项 `timeout` 以秒为单位（`CA/src/extensions/mcp/runtime.ts:48`）。请求的每条进度通知都会重新启动计时器（`mcp/src/client.ts:531`）。计时器到期或调用方的 signal 中止时，客户端会拒绝该请求并发送 `notifications/cancelled`；它绝不会取消 `initialize`，因为规范禁止这样做（`mcp/src/client.ts:556`）。



支持的功能包括：`ping`、分页的 `tools/list`、带结构化内容的 `tools/call`、资源和模板、服务器发起的 `ping` 和 `roots/list` 请求、日志和列表变更通知、进度、取消以及 OAuth。“批量 JSON\-RPC 消息、旧式 HTTP\+SSE、服务器、采样和任务不在初始核心范围内”（`mcp/README.md` 的“支持的协议范围”节）。



|<strong>传输方式</strong>|<strong>行为</strong>|
|---|---|
|stdio，`transports/stdio.ts`|使用 `cross-spawn`，不经过 shell；除 Windows 外，在所有平台上都分离到自身的进程组中（`mcp/src/transports/stdio.ts:101`）。关闭时先结束 stdin，500 ms 后向进程组发送 `SIGTERM`，再过 2 s 发送 `SIGKILL`。Windows 上使用 `taskkill /T /F`。退出钩子在 Pi 退出时向仍存活的进程组发送 `SIGTERM`。保留 stderr 的最后 64 KiB|
|Streamable HTTP，`transports/streamable-http.ts`|发送带有 `accept: application/json, text/event-stream` 的 POST。捕获 `Mcp-Session-Id` 并在后续请求中带回；关闭时发送 DELETE。初始化后打开 GET SSE 流（405 表示不提供该流），对断开的流进行 5 次重连，退避从 1 s 增长至 30 s，并通过 `Last-Event-ID` 恢复。401，或质询信息为 `insufficient_scope` 的 403，会交给认证提供商处理|
|SSE（旧式）|校验时拒绝：“不支持旧式 SSE 传输；请使用 streamable HTTP URL”（`CA/src/core/mcp-servers.ts:270`）|



两种传输方式，共用同一个消息大小上限。两者都会拒绝超过 16 MiB 的单条消息（`mcp/src/transports/transport.ts:3`）。来源：`mcp/src/transports/`。

## 配置



Pi 先读取智能体目录中的 `mcp.json`，即 `~/.pi/agent/mcp.json`，再读取项目中的 `.pi/mcp.json`；只有项目受信任时才会读取项目文件（`CA/src/extensions/mcp/config.ts:145`）。两者都使用其他 MCP 客户端采用的 `mcpServers` 结构：



一个 stdio 服务器和一个 HTTP 服务器。来源：`CA/docs/mcp.md`。

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    },
    "docs": {
      "url": "https://example.com/mcp",
      "headers": { "Authorization": "Bearer ${DOCS_TOKEN}" },
      "description": "Search and read the product documentation"
    }
  }
}
```

> 完整示例，出自“配置服务器”节。`command` 选择 stdio，`url` 选择 streamable HTTP；`type` 可省略。
> 
> 



这些条目的类型定义位于 core 而非扩展中，因为扩展也能通过 `pi.registerMcpServer()` 注册服务器（`CA/src/core/mcp-servers.ts:1`）：

- <strong>所有服务器：</strong> `exposure?`（默认 `"codemode"`）、`description?`、`toolExposure?: Record<string, McpExposure>`、`enabled?`（默认 `true`）、以秒为单位的 `timeout?`（默认 60）（`CA/src/core/mcp-servers.ts:59`）

- <strong>Stdio：</strong> `type?: "stdio"`、`command`、`args?`、`env?`、`cwd?`。`env` 的值可以是 `${NAME}` 或 `!command`；相对的 `cwd` 会以会话目录为基准解析（`CA/src/core/mcp-servers.ts:80`）

- <strong>HTTP：</strong> `type?: "http"`（也接受 `"streamable-http"`）、`url`、`headers?`、`oauth?: McpOAuthConfig` 以及 `auth?: { provider }`。`auth` 会发送 `/login` 提供商的令牌，除回环主机外都要求使用 https（`CA/src/core/mcp-servers.ts:137`）

- <strong>服务器名称：</strong> 必须匹配 `^[A-Za-z0-9_-]+$`（`CA/src/core/mcp-servers.ts:152`）。仅在 `-` 和 `_` 上不同的两个名称共享同一命名空间，因此第二个会因冲突而被拒绝（`CA/src/extensions/mcp/config.ts:128`）

- <strong>工具名称：</strong> 采用 `mcp__<server>__<tool>`，其中不属于 `[A-Za-z0-9_]` 的字符都替换为 `_`。若名称超过 64 个字符，或已被其他 MCP 工具占用，则会截短，并追加 `_` 和服务器与工具的 SHA\-256 的 8 个十六进制字符（`CA/src/extensions/mcp/tools.ts:84`）



采集工具集对该构建运行了 `createMcpToolName`。`dev-radius / list.items` 变为 `mcp__dev_radius__list_items`；`github` 上一个 60 字符的工具名变为以 `_5204ba68` 结尾的 64 字符名称；如果某台服务器上的 `mcp__srv__a_b` 已被占用，则 `a-b` 会变为 `mcp__srv__a_b_5c15ffbd`（`research/out/mcp-naming.txt`）。



<strong>合并规则。</strong> 同名项目条目会替换用户条目。但不含 `command`、`url` 或 `type` 的项目条目属于覆盖项，只能设置用户条目的 `enabled`、`exposure` 和 `toolExposure`；其他内容都会报错（`CA/src/extensions/mcp/config.ts:108`）。项目文件不能设置 `auth`：“项目文件不能使用它，这样仓库就无法决定凭据发往何处”（`CA/src/extensions/mcp/config.ts:25`）。顶层的 `autoEnableCodemode`（默认 `true`）可以出现在任一文件中，项目值优先（`CA/src/extensions/mcp/config.ts:28`）。

## 模型如何访问 MCP 工具



每个工具都有四种暴露方式之一：优先使用其 `toolExposure` 条目，其次使用服务器的 `exposure`，最后默认为 `codemode`。精确工具名优先于模式匹配；多个模式中，对象中最先匹配的那个生效（`CA/src/core/mcp-servers.ts:234`）。`codemode-deferred` 可作为 `codemode` 的旧别名（`CA/src/core/mcp-servers.ts:57`）。

|<strong>暴露方式</strong>|<strong>是否向模型声明</strong>|<strong>能否从 codemode 调用</strong>|<strong>Pi 激活的工具</strong>|
|---|---|---|---|
|`codemode`（默认）|否|是|`codemode`，除非 `autoEnableCodemode` 为 `false`|
|`deferred`|由 `tool_search` 加载后声明|是|`tool_search`|
|`direct`|是|是|—|
|`hidden`|否|否|—|



四种暴露方式中，有三种不会将工具加入请求。来源：`McpExposure` 的文档注释（`CA/src/core/mcp-servers.ts:43`）和 `ensureDiscoveryActive`（`CA/src/extensions/mcp/index.ts:466`）。在 Pi 内部，`codemode` 和 `deferred` 都映射为工具暴露方式 `deferred`；两者仅在所激活的辅助工具上不同（`CA/src/extensions/mcp/tools.ts:44`）。



<BookFigure id="6.2" />

> 每条路径最终都进入同一流水线并使用同一连接。不同的仅是第一跳：脚本调用、已加载的声明或已声明的工具。示意图来源：`CA/src/extensions/mcp/index.ts`（模块注释、`ensureDiscoveryActive`、`tool_call` 处理器）和 `tools.ts`（`createMcpToolDefinition`）。
> 
> 



<strong>`mcp_servers` 章节。</strong> 模型通过系统提示词中的一个章节得知 `codemode` 或 `deferred` 服务器的存在，因为 `codemode` 和 `tool_search` 都不会列出这类服务器（`CA/src/extensions/mcp/index.ts:186`）。每台已启用的服务器占一行，包含其命名空间、访问路径，以及描述的第一行；连接后则使用服务器指令的第一行。每台服务器最多 250 个字符，整个章节最多 4,096 个字符（`CA/src/extensions/mcp/index.ts:154`）。对上面的 `docs` 服务器加上随附文档中的 GitHub 示例，该构建生成如下内容：



```text
工具尚未向你声明的 MCP 服务器。请通过 codemode 脚本调用 `codemode` 服务器的工具。
- mcp_docs (codemode): 搜索和阅读产品文档
- mcp_github (codemode)
```



还传入了第三台只有 `direct` 工具的服务器；它按设计被排除在外（`research/out/mcp-naming.txt`）。该章节在 `before_agent_start` 中设置（`CA/src/extensions/mcp/index.ts:1062`）。当它与对话记录中已有的内容不同时，会话会追加一条仅包含已变化章节的系统消息，而不会改写之前的消息（`CA/src/core/agent-session.ts:1714`）；“从 `prompt()` 到 `agent_settled`”（原书第67页）介绍了这项差异。



<strong>谁等待谁。</strong> 服务器在后台连接。第一个提示词最多等待 10 s，而且只等待包含 `direct` 工具的服务器，因为必须在请求中声明这些工具（`CA/src/extensions/mcp/index.ts:93`）。只有在 `scriptNeedsServer` 判定需要时，codemode 脚本才等待尚未连接完成的服务器：代码中包含服务器的命名空间，或包含 `searchTools`、`describeNamespace`、`describeTool`、`ALL_TOOLS` 中任意一项（`CA/src/extensions/mcp/index.ts:223`）。`tool_search` 和资源工具会等待所有服务器（`CA/src/extensions/mcp/index.ts:1073`）。



<strong>结果。</strong> 面向模型的文本超过 20 KiB 时，会保留开头和结尾，中间插入 `…N chars truncated…` 标记；完整文本写入结果中指定的临时文件（`CA/src/extensions/mcp/tools.ts:51`）。脚本接收移除 `_meta` 后的完整 `CallToolResult`，绝不截断；带有 `isError` 的结果在脚本中正常 resolve，但对直接调用而言属于错误结果。



资源通过 `list_mcp_resources`、`list_mcp_resource_templates` 和 `read_mcp_resource` 呈现给模型，这些是“Codex 和 opencode 使用的工具”（`CA/src/extensions/mcp/resources.ts:2`）。MCP App 资源，即 `ui://` URI 或 `profile=mcpapp` HTML，会被排除（`CA/src/extensions/mcp/resources.ts:47`）。

## 故障、重试与登录



|<strong>失败情况</strong>|<strong>Pi 的处理</strong>|<strong>位置</strong>|
|---|---|---|
|连接 HTTP 服务器，发生暂时性错误|250 ms 后重试，然后 1,000 ms 后再次重试|`CA/src/extensions/mcp/runtime.ts:362`|
|连接 stdio 服务器|不重试|同上|
|`tools/call`，任何 HTTP 错误|不重试：“它们可能已经运行过”|`CA/src/extensions/mcp/runtime.ts:297`|
|任何请求，会话过期（404）|在新会话中重试一次|同上|
|列出或读取资源，发生暂时性错误|250 ms 后重试一次|同上|
|连接断开|状态设为 `disconnected`；下次调用时重新连接|`CA/src/extensions/mcp/runtime.ts:53`|



只会重试不可能已经执行过的请求。“暂时性”错误指 HTTP 408、429，以及除 501 外的 500 及以上状态码，再加上 `fetch` 抛出的 `TypeError`（`CA/src/extensions/mcp/runtime.ts:70`）。



<strong>OAuth。</strong> 未设置 `auth` 且没有 `Authorization` 标头的 HTTP 服务器通过 OAuth 登录（`CA/src/extensions/mcp/runtime.ts:83`）。流程使用 PKCE 和回环回调。Pi 通过动态客户端注册，以 `client_name` 为 `pi`（或 `oauth.clientName`）标识自身，也可以通过 https://pi\.dev/oauth 上的 Client ID Metadata Document 标识自身；如果 403 要求更大的权限范围，则会再次登录以提升授权（`mcp/README.md` 的“支持的协议范围”节；`CA/src/extensions/mcp/oauth.ts:272`）。授权服务器发送 RFC 9207 的 `iss` 参数时，CIMD 客户端 ID 为 https://pi\.dev/oauth/client\.json；未发送时则为 `https://pi.dev/oauth/<id>/client.json`，并使用匹配的回调路径（`CA/src/extensions/mcp/oauth.ts:253`）。凭据保存在智能体目录的 `mcp-auth.json` 中（`CA/src/extensions/mcp/oauth.ts:144`），文件以 `0600` 模式创建（`CA/src/core/auth-storage.ts:25`）。



<strong>命令。</strong> `pi mcp add | remove | list | login | logout` 无需会话即可运行；`add` 和 `remove` 接受 `-l/--local` 来操作项目文件，`list` 接受 `--json`（`CA/src/extensions/mcp/cli.ts:33`）。在会话中，`/mcp` 打开管理器（`CA/src/extensions/mcp/index.ts:1141`）。`--no-mcp` 在本次运行中禁用内置支持（`CA/src/cli/args.ts:185`）。



> <strong>文档 ≠ 代码</strong>
> 
> `CA/docs/mcp.md` 写道：“HTTP 网络错误和暂时性状态码（408、429 和 5xx）会重试两次。”但 `isTransientError` 排除了 501（`CA/src/extensions/mcp/runtime.ts:72`）。同一页面及 `config.ts` 中的注释还说，Pi 会“在采用 codemode 暴露方式的服务器连接后”激活 codemode。实际上，`ensureDiscoveryActive` 会在会话开始时依据配置激活它，此时还没有任何服务器连接，因此即使某台服务器永远连不上，也仍会启用 codemode（`CA/src/extensions/mcp/index.ts:466`）。
> 
> 



> <strong>对你的意义：</strong>
> 
> - 默认情况下，MCP 工具不会出现在请求中；请在 `mcp_servers` 章节和 codemode 脚本中寻找它们
> 
> - 为每台服务器写一句话的描述；这是模型在连接前唯一会读到的内容
> 
> - 对少数常用工具使用 `direct`，并接受第一个提示词最多等待其服务器 10 s
> 
> - 将凭据和 `auth` 放在用户级 `mcp.json` 中；项目文件只能切换启用状态和调整暴露方式
> 
> - 将失败的工具调用视为可能已经执行过；Pi 不会重试，你也不应重试
> 
> 



> 来源：`mcp/README.md`（“支持的协议范围”“OAuth”节）；`mcp/package.json`。`mcp/src/protocol/types.ts`（`LATEST_PROTOCOL_VERSION`、`SUPPORTED_PROTOCOL_VERSIONS`）；`mcp/src/client.ts`（`ClientState`、`connect`、`requestInternal`、`handleProgress`、`cancelPending`、`listAll`）；`mcp/src/transports/stdio.ts`（`close`、`killProcessTree`、`installExitHook`）；`mcp/src/transports/streamable-http.ts`（`needsAuthorization`、重连默认值、`openGetStream`）；`mcp/src/transports/transport.ts`（`DEFAULT_MAX_MESSAGE_BYTES`）。`CA/src/core/mcp-servers.ts`（`McpExposure`、`McpServerConfigBase`、`getMcpToolExposure`、`validateMcpServerConfig`）；`CA/src/extensions/index.ts`（`builtInExtensions`）；`CA/src/extensions/mcp/config.ts`（`readConfigFile`、`loadMcpConfig`）；`CA/src/extensions/mcp/index.ts`（`renderServersSection`、`scriptNeedsServer`、`ensureDiscoveryActive`、`before_agent_start`、`tool_call`）；`CA/src/extensions/mcp/tools.ts`（`createMcpToolName`、`limitMcpContent`、`convertMcpResult`）；`CA/src/extensions/mcp/resources.ts`。`CA/src/extensions/mcp/runtime.ts`（`isTransientError`、`withClient`、`open`）；`CA/src/extensions/mcp/oauth.ts`；`CA/src/extensions/mcp/cli.ts`（`HELP`）；`CA/src/core/agent-session.ts`（`_preparePromptAndToolLoadout`）；`CA/src/core/auth-storage.ts`；`CA/src/cli/args.ts`；`CA/docs/mcp.md`；`research/capture/mcp-naming.mjs`；`research/out/mcp-naming.txt`。
> 
>
