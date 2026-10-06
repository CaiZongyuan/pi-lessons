Outside tools arrive through MCP and codemode; everything the user sees is drawn by one diferential renderer.

外部工具通过 MCP 和 codemode 进入；用户看到的一切由同一个差分渲染器绘制。

# 6.1 MCP, from mcp.json to tool call

# 6.1 MCP：从 mcp.json 到工具调用

Pi 1.0 ships its own MCP client and registers every server tool in the ordinary tool pipeline. By default the model never sees those tools declared; it reaches them from a codemode script.

Pi 1.0 自带 MCP 客户端，并把每个服务器工具注册进普通工具流水线。默认情况下模型看不到这些工具的声明，而是从 codemode 脚本里触达它们。

A Model Context Protocol server is a process or URL that ofers tools and resources. Pi connects to it without the oficial SDK, names each tool mcp__<server>__<tool>, and runs every call through the same pipeline as read or bash, so tool_call hooks and permission gates apply unchanged. This section shows the two layers that do this and the client’s connect and timeout rules. It then covers the configuration file and its trust rules, the four exposures that decide how the model reaches a tool, and what is retried when a server fails.

一个 Model Context Protocol 服务器就是一个提供工具和资源的进程或 URL。Pi 不依赖官方 SDK 就连上它，把每个工具命名为 mcp__<server>__<tool>，并让每次调用都走与 read 或 bash 相同的流水线，因此 tool_call 钩子和权限闸门原样生效。本节展示实现这件事的两层结构，以及客户端的连接与超时规则；随后说明配置文件及其信任规则、决定模型如何触达工具的四种 exposure，以及服务器失败时哪些操作会重试。

## Two layers

## 两层结构

The first layer is @earendil-works/pi-mcp 1.0.4, “a small, standalone Model Context Protocol client. It does not depend on the oficial MCP SDK or other pi packages” mcp/README.md. Its one runtime dependency is cross-spawn 7.0.6 mcp/package.json. The OAuth code “is adapted from the MIT-licensed Model Context Protocol TypeScript SDK v1.29.0”, whose licence ships under LICENSES/ mcp/README.md §OAuth.

第一层是 @earendil-works/pi-mcp 1.0.4，「一个小巧、独立的 Model Context Protocol 客户端。它不依赖官方 MCP SDK 或其他 pi 包」mcp/README.md。它唯一的运行时依赖是 cross-spawn 7.0.6 mcp/package.json。OAuth 代码「改编自 MIT 许可的 Model Context Protocol TypeScript SDK v1.29.0」，其许可证随 LICENSES/ 一并分发 mcp/README.md §OAuth。

The second layer is the built-in mcp extension in CA/src/extensions/mcp/. It is registered as a replaceable built-in: an extension that registers /mcp takes over instead of running alongside it CA/src/extensions/index.ts:9. The part that talks to servers loads lazily, so “sessions without servers never pay for it” CA/src/extensions/mcp/index.ts:1021.

第二层是 CA/src/extensions/mcp/ 里的内置 mcp 扩展。它以可替换的内置扩展注册：某个扩展若注册了 /mcp，就接管它而不是与它并行运行 CA/src/extensions/index.ts:9。与服务器对话的那部分是懒加载的，因此「没有服务器的会话永远不必为此付费」CA/src/extensions/mcp/index.ts:1021。

<table><tr><td>文件</td><td>行数</td><td>职责</td></tr><tr><td>index.ts</td><td>1,225</td><td>生命周期、exposure、mcp_servers 提示词章节、/mcp</td></tr><tr><td>cli.ts</td><td>614</td><td>pi mcp add · remove · list · login · logout</td></tr><tr><td>oauth.ts</td><td>532</td><td>登录、mcp-auth.json、令牌刷新</td></tr><tr><td>runtime.ts</td><td>491</td><td>每服务器一个连接、传输方式、重试</td></tr><tr><td>resources.ts</td><td>339</td><td>三个资源工具</td></tr><tr><td>tools.ts</td><td>335</td><td>工具命名、结果转换、20 KiB 截断</td></tr><tr><td>ui.ts·config.ts·log.ts</td><td>252·242·69</td><td>/mcp 管理器、mcp.json、mcp.log</td></tr></table>

The client is a library; everything Pi-specific lives in one extension. Line counts from wc -l at 28dcce2; the two 2-line .lazy.ts loaders are omitted.

客户端是一个库；所有 Pi 特有的东西都住在一个扩展里。行数来自 28dcce2 的 wc -l；两个 2 行的 .lazy.ts 加载器已略去。

## The client

## 客户端

McpClient speaks protocol 2025-11-25 and accepts a server that negotiates 2025-06-18, 2025-03-26 or 2024-11-05 mcp/src/protocol/types.ts:4. It has four states, idle, connecting, connected and closed mcp/src/client.ts:41, and connect() refuses to run in any state but idle mcp/src/client.ts:202.

McpClient 使用协议 2025-11-25，并接受协商出 2025-06-18、2025-03-26 或 2024-11-05 的服务器 mcp/src/protocol/types.ts:4。它有四种状态：idle、connecting、connected 和 closed mcp/src/client.ts:41，而 connect() 在 idle 以外的任何状态都拒绝运行 mcp/src/client.ts:202。

![](images/7039cba5fca19115d298ab360232334633a70ea889f551d2377a4cf14dfc78f3.jpg)

A server is usable only after the version check and notifications/initialized. A server that picks an unlisted version fails with “MCP server selected unsupported protocol version …” and the client closes. Steps 1–3 are connect(), 4 is list All, 5 is request Internal with progress. From mcp/src/client.ts.

只有通过版本检查并完成 notifications/initialized 之后，服务器才可用。选了未列出版本的服务器会失败并报「MCP server selected unsupported protocol version …」，客户端随即关闭。步骤 1–3 是 connect()，4 是 list All，5 是带进度的 request Internal。取自 mcp/src/client.ts。

Timeouts. A request times out after 30 s in the library mcp/src/client.ts:38 and after 60 s in Pi, where the per-server timeout key is in seconds CA/src/extensions/mcp/runtime.ts:48. Every progress notification for the request re-arms the timer mcp/src/client.ts:531. On expiry, or when the caller’s signal aborts, the client rejects the request and sends notifications/cancelled; it never cancels initialize, which the spec forbids mcp/src/client.ts:556.

超时。库中一个请求在 30 秒后超时 mcp/src/client.ts:38，在 Pi 中则在 60 秒后超时，其中每服务器的超时键以秒为单位 CA/src/extensions/mcp/runtime.ts:48。该请求的每一条进度通知都会重新装填计时器 mcp/src/client.ts:531。一旦到期，或调用方的 signal 中止，客户端就 reject 这个请求并发送 notifications/cancelled；它绝不取消 initialize，规范明令禁止 mcp/src/client.ts:556。

Supported: ping, paginated tools/list, tools/call with structured content, resources and templates, server ping and roots/list requests, logging and list-changed notifications, progress, cancellation and OAuth. “Batch JSON-RPC messages, legacy HTTP+SSE, servers, sampling, and tasks are outside the initial core” mcp/README.md §Supported protocol surface.

支持：ping、分页的 tools/list、带结构化内容的 tools/call、资源与模板、服务器 ping 与 roots/list 请求、日志和 list-changed 通知、进度、取消和 OAuth。「批量 JSON-RPC 消息、旧式 HTTP+SSE、服务器、采样和任务不在初版核心范围内」mcp/README.md §Supported protocol surface。

<table><tr><td>传输方式</td><td>行为</td></tr><tr><td>stdio transports/stdio.ts</td><td>cross-spawn 且不经 shell，除 Windows 外在每个平台上都以 detached 方式进入自己的进程组 mcp/src/transports/stdio.ts:101。关闭流程：结束 stdin；500 ms 后对整个进程组发 SIGTERM；再过 2 s 发 SIGKILL。在 Windows 上用 taskkill /T /F。退出钩子在 Pi 退出时向仍存活的进程组发 SIGTERM。保留 stderr 最后 64 KiB。</td></tr><tr><td>Streamable HTTP transports/streamable-http.ts</td><td>POST 带上 accept: application/json, text/event-stream。捕获 Mcp-Session-Id 并回传；关闭时发 DELETE。初始化后打开一条 GET SSE 流（返回 405 表示没有），并以 1 秒到 30 秒的退避重连断掉的流，最多 5 次，用 Last-Event-ID 续传。401，或 challenge 里写着 insufficient_scope 的 403，都会转到认证提供者。</td></tr><tr><td>SSE（旧式）</td><td>校验直接拒绝：「legacy SSE transport is not supported; use the streamable HTTP URL」CA/src/core/mcp-servers.ts:270。</td></tr></table>

Two transports, one message cap. Both reject a single message over 16 MiB mcp/src/transports/transport.ts:3. From mcp/src/transports/.

两种传输方式，一个消息上限。两者都拒绝超过 16 MiB 的单条消息 mcp/src/transports/transport.ts:3。取自 mcp/src/transports/。

## Configuration

## 配置

Pi reads mcp.json from the agent directory, \~/.pi/agent/mcp.json, and then .pi/mcp.json in the project, but the project file only when the project is trusted CA/src/extensions/mcp/config.ts:145. Both use the mcp Servers shape other MCP clients use:

Pi 先从 agent 目录 \~/.pi/agent/mcp.json 读 mcp.json，再读项目里的 .pi/mcp.json，但项目文件只在项目受信任时才生效 CA/src/extensions/mcp/config.ts:145。两者都用的是其他 MCP 客户端通用的 mcp Servers 结构：

```json one stdio server and one HTTP server CA/docs/mcp.md JSON
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

Complete, from §Configure servers. A command selects stdio and a url selects streamable HTTP; type is optional.

完整内容，取自 §Configure servers。写 command 即选 stdio，写 url 即选 streamable HTTP；type 是可选的。

The entry types live in core, not in the extension, because extensions can also register servers with pi.registerMcpServer() CA/src/core/mcp-servers.ts:1.

条目类型定义在 core 里，而不是扩展里，因为扩展也可以用 pi.registerMcpServer() 注册服务器 CA/src/core/mcp-servers.ts:1。

Every server — exposure? (default "codemode"), description?, tool Exposure?: Record<string, McpExposure>, enabled? (default true), timeout? in seconds (default 60) CA/src/core/mcp-servers.ts:59.

每个服务器 —— exposure?（默认 "codemode"）、description?、toolExposure?: Record<string, McpExposure>、enabled?（默认 true）、timeout?，单位为秒（默认 60）CA/src/core/mcp-servers.ts:59。

Stdio — type?: "stdio", command, args?, env?, cwd?. env values can be \${NAME} or !command; a relative cwd resolves against the session directory CA/src/core/mcp-servers.ts:80.

Stdio —— type?: "stdio"、command、args?、env?、cwd?。env 的值可以是 \${NAME} 或 !command；相对的 cwd 会相对会话目录解析 CA/src/core/mcp-servers.ts:80。

HTTP — type?: "http" ("streamable-http" is also accepted), url, headers?, oauth?: McpOAuthConfig, and auth?: { provider }, which sends the token of a /login provider and requires https except on loopback hosts CA/src/core/mcp-

HTTP —— type?: "http"（也接受 "streamable-http"）、url、headers?、oauth?: McpOAuthConfig，以及 auth?: { provider }，后者会发送 /login 提供者的令牌，并要求 https，环回主机除外 CA/src/core/mcp-

servers.ts:137.

servers.ts:137。

Server names — must match ^[A-Za-z0-9_-]+\$ CA/src/core/mcp-servers.ts:152. Two names that difer only in - and _ share a namespace, so the second is rejected as conflicting CA/src/extensions/mcp/config.ts:128.

服务器名称 —— 必须匹配 ^[A-Za-z0-9_-]+\$ CA/src/core/mcp-servers.ts:152。两个只在 - 和 _ 上不同的名字会共享同一个命名空间，因此第二个会被当作冲突而拒绝 CA/src/extensions/mcp/config.ts:128。

Tool names — mcp__<server>__<tool> with every character outside [A-Za-z0-9_] replaced by _. A name over 64 characters, or one already taken by another MCP tool, is cut and sufixed with _ and 8 hex characters of a SHA-256 of server and tool CA/src/extensions/mcp/tools.ts:84.

工具名称 —— 形如 mcp__<server>__<tool>，其中 [A-Za-z0-9_] 之外的每个字符都替换为 _。超过 64 个字符的名称，或已被别的 MCP 工具占用的名称，会被截断，并追加 _ 加服务器与工具的 SHA-256 的 8 位十六进制字符 CA/src/extensions/mcp/tools.ts:84。

The capture kit ran createMcpToolName against the build. dev-radius / list.items becomes mcp__dev_radius__list_items; a 60-character tool on github becomes a 64-character name ending _5204ba68; and a-b on a server where mcp__srv__a_b is taken becomes mcp__srv__a_b_5c15ffbd research/out/mcp-naming.txt.

采集套件对构建产物运行了 createMcpToolName。dev-radius / list.items 变成 mcp__dev_radius__list_items；github 上一个 60 字符的工具变成一个以 _5204ba68 结尾的 64 字符名称；而在 mcp__srv__a_b 已被占用的服务器上，a-b 变成 mcp__srv__a_b_5c15ffbd research/out/mcp-naming.txt。

Merge rules. A project entry with the same name replaces the user entry. A project entry with no command, url or type is an override instead, and it may set only enabled, exposure and tool Exposure of the user entry; anything else is reported as an error CA/src/extensions/mcp/config.ts:108. A project file may not set auth: “Project files cannot use it, so a repository cannot pick where the credential goes” CA/src/extensions/mcp/config.ts:25. The top-level autoEnableCodemode (default true) can sit in either file, and the project value wins CA/src/extensions/mcp/config.ts:28.

合并规则。同名的项目条目替换用户条目。不带 command、url 或 type 的项目条目则是覆盖项，它只能设置用户条目的 enabled、exposure 和 toolExposure；其余任何设置都报错 CA/src/extensions/mcp/config.ts:108。项目文件不得设置 auth：「项目文件不能用它，这样仓库就无法决定凭证放在哪里」CA/src/extensions/mcp/config.ts:25。顶层的 autoEnableCodemode（默认 true）可以放在任一文件里，项目侧的值优先 CA/src/extensions/mcp/config.ts:28。

## How the model reaches MCP tools

## 模型如何触达 MCP 工具

Each tool has one of four exposures: its tool Exposure entry, else the server’s exposure, else codemode. An exact tool name wins over patterns, and among patterns the first match in the object wins CA/src/core/mcp-servers.ts:234. codemodedeferred is accepted as an old alias for codemode CA/src/core/mcp-servers.ts:57.

每个工具有四种 exposure 之一：它的 toolExposure 条目，否则是服务器的 exposure，再否则是 codemode。精确的工具名优先于模式；模式之间则以对象中第一个匹配项为准 CA/src/core/mcp-servers.ts:234。codemodedeferred 作为 codemode 的旧别名仍然被接受 CA/src/core/mcp-servers.ts:57。

<table><tr><td>EXPOSURE</td><td>是否声明给模型</td><td>能否从 CODEMODE 调用</td><td>PI 激活的工具</td></tr><tr><td>codemode（默认）</td><td>否</td><td>能</td><td>codemode，除非 autoEnableCodemode 为 false</td></tr><tr><td>deferred</td><td>等 tool_search 加载后</td><td>能</td><td>tool_search</td></tr><tr><td>direct</td><td>是</td><td>能</td><td>—</td></tr><tr><td>hidden</td><td>否</td><td>否</td><td>—</td></tr></table>

Three of the four exposures keep the tool out of the request. From the McpExposure doc comment CA/src/core/mcp-servers.ts:43 and ensureDiscoveryActive CA/src/extensions/mcp/index.ts:466. Inside Pi both codemode and deferred map to tool exposure deferred; they difer only in which helper tool is activated CA/src/extensions/mcp/tools.ts:44.

四种 exposure 里有三种会把工具挡在请求之外。依据 McpExposure 的文档注释 CA/src/core/mcp-servers.ts:43 和 ensureDiscoveryActive CA/src/extensions/mcp/index.ts:466。在 Pi 内部，codemode 和 deferred 都映射到工具 exposure 的 deferred；两者只是激活的辅助工具不同 CA/src/extensions/mcp/tools.ts:44。

![](images/25b61b2187e661452a7be621bd68873fadf709df090b8c5be78f2b8585461f86.jpg)

Every route ends in the same pipeline and the same connection. Only the first hop difers: a script call, a loaded declaration, or a declared tool. Schematic, from CA/src/extensions/mcp/index.ts (module comment, ensureDiscoveryActive, tool_call handler) and tools.ts (createMcpToolDefinition).

每条路径最终都汇入同一条流水线和同一个连接。只有第一跳不同：脚本调用、加载得到的声明，或已声明的工具。示意图取自 CA/src/extensions/mcp/index.ts（模块注释、ensureDiscoveryActive、tool_call 处理器）和 tools.ts（createMcpToolDefinition）。

The mcp_servers section. The model learns that a codemode or deferred server exists from a system-prompt section, because neither codemode nor tool_search lists such servers CA/src/extensions/mcp/index.ts:186. Each enabled server gets one line: its namespace, the route, and the first line of its description or, once connected, of its server instructions, up to 250 characters per server and 4,096 for the whole section CA/src/extensions/mcp/index.ts:154. For the docs server above plus the GitHub example from the shipped docs, the build produces:

mcp_servers 章节。模型是从系统提示词的一个章节得知存在 codemode 或 deferred 服务器的，因为 codemode 和 tool_search 都不会列出这类服务器 CA/src/extensions/mcp/index.ts:186。每个启用的服务器占一行：它的命名空间、路径，以及它的 description 的第一行，或者连接后其服务器 instructions 的第一行，每个服务器上限 250 字符，整个章节上限 4,096 字符 CA/src/extensions/mcp/index.ts:154。对上面的 docs 服务器加上随包文档里的 GitHub 示例，构建产物如下：

```txt
MCP servers whose tools are not declared to you. Call the tools of `codemode` servers from codemode scripts.
- mcp_docs (codemode): Search and read the product documentation
- mcp_github (codemode)
```

A third server with only direct tools was passed in and left out, as designed research/out/mcp-naming.txt. The section is set in before_agent_start CA/src/extensions/mcp/index.ts:1062. When it diferes from what the transcript already holds, the session appends a system message carrying only the changed sections, so earlier messages are not rewritten CA/src/core/agent-session.ts:1714; from prompt() to agent_settled (p. 67) covers that dif.

第三个只有 direct 工具的服务器被传进来后按设计被排除在外 research/out/mcp-naming.txt。该章节在 before_agent_start 中写入 CA/src/extensions/mcp/index.ts:1062。当它与记录中已有的内容不同时，会话会追加一条只带变化章节的系统消息，因此早先的消息不会被重写 CA/src/core/agent-session.ts:1714；从 prompt() 到 agent_settled（p. 67）那一节讲的就是这个差异。

Who waits for whom. Servers connect in the background. The first prompt waits up to 10 s, and only for servers with direct tools, since those must be declared in its request CA/src/extensions/mcp/index.ts:93. A codemode script waits for a pending server only if scriptNeedsServer says so: the code contains the server’s namespace, or any of search Tools, describe Namespace, describe Tool or ALL_TOOLS CA/src/extensions/mcp/index.ts:223. tool_search and the resource tools wait for every server CA/src/extensions/mcp/index.ts:1073.

谁等谁。服务器在后台连接。第一条提示词最多等 10 秒，而且只等带 direct 工具的服务器，因为那些工具必须在它的请求里被声明 CA/src/extensions/mcp/index.ts:93。只有 scriptNeedsServer 这么说时，codemode 脚本才会等待尚未就绪的服务器：代码里包含该服务器的命名空间，或者包含 searchTools、describeNamespace、describeTool、ALL_TOOLS 中的任何一个 CA/src/extensions/mcp/index.ts:223。tool_search 和资源工具则等待每一个服务器 CA/src/extensions/mcp/index.ts:1073。

Results. Model-facing text over 20 KiB keeps its start and end around a …N chars truncated… marker, and the full text goes to a temp file named in the result CA/src/extensions/mcp/tools.ts:51. Scripts receive the whole CallToolResult without _meta, never truncated, and a result with isError resolves in a script but is an error result for a direct call

结果。面向模型的文本超过 20 KiB 时，会在 …N chars truncated… 标记两侧保留开头和结尾，全文写入结果中指名的临时文件 CA/src/extensions/mcp/tools.ts:51。脚本拿到的是完整的 CallToolResult，不含 _meta，且从不截断；带 isError 的结果在脚本里是 resolve，但在 direct 调用里算错误结果

Resources reach the model through list_mcp_resources, list_mcp_resource_templates and read_mcp_resource, “the tools Codex and opencode use” CA/src/extensions/mcp/resources.ts:2. MCP App resources, ui:// URIs or profile=mcpapp HTML, are left out CA/src/extensions/mcp/resources.ts:47.

资源通过 list_mcp_resources、list_mcp_resource_templates 和 read_mcp_resource 抵达模型，「也就是 Codex 和 opencode 用的那几个工具」CA/src/extensions/mcp/resources.ts:2。MCP App 资源、ui:// URI 或 profile=mcpapp 的 HTML 都被排除 CA/src/extensions/mcp/resources.ts:47。

## Failure, retries and sign-in

## 失败、重试与登录

<table><tr><td>失败的环节</td><td>PI 的处理</td><td>位置</td></tr><tr><td>连接 HTTP 服务器，瞬时错误</td><td>250 ms 后重试一次，再在 1,000 ms 后重试一次</td><td>CA/src/extensions/mcp/runtime.ts:362</td></tr><tr><td>连接 stdio 服务器</td><td>不重试</td><td>同上</td></tr><tr><td>tools/call，任意 HTTP 错误</td><td>不重试：「它们可能已经执行过了」</td><td>CA/src/extensions/mcp/runtime.ts:297</td></tr><tr><td>任意请求，会话过期（404）</td><td>在新会话上重试一次</td><td>同上</td></tr><tr><td>列出或读取资源，瞬时错误</td><td>250 ms 后重试一次</td><td>同上</td></tr><tr><td>连接掉线</td><td>状态转为 disconnected；下一次调用会重连</td><td>CA/src/extensions/mcp/runtime.ts:53</td></tr></table>

Only requests that cannot have run are retried. “Transient” is HTTP 408, 429, or 500 and above except 501, plus a TypeError from fetch CA/src/extensions/mcp/runtime.ts:70.

只有不可能已经执行过的请求才会重试。「瞬时」指 HTTP 408、429，以及 500 及以上但不含 501，外加 fetch 抛出的 TypeError CA/src/extensions/mcp/runtime.ts:70。

OAuth. An HTTP server with no auth and no Authorization header signs in with OAuth CA/src/extensions/mcp/runtime.ts:83. The flow uses PKCE and a loopback callback. Pi identifies itself by dynamic client registration with client_name pi (or oauth.client Name), or by a Client ID Metadata Document on https://pi.dev/oauth, and it signs in again for step-up when a 403 asks for more scope mcp/README.md §Supported protocol surface CA/src/extensions/mcp/oauth.ts:272. The CIMD client id is https://pi.dev/oauth/client.json when the authorization server sends the RFC 9207 iss parameter, and https://pi.dev/oauth/<id>/client.json, with a matching callback path, when it does not CA/src/extensions/mcp/oauth.ts:253. Credentials go to mcp-auth.json in the agent directory CA/src/extensions/mcp/oauth.ts:144, created with mode 0600 CA/src/core/auth-storage.ts:25.

OAuth。没有 auth 也没有 Authorization 头的 HTTP 服务器会用 OAuth 登录 CA/src/extensions/mcp/runtime.ts:83。该流程使用 PKCE 和环回回调。Pi 通过动态客户端注册（client_name 为 pi，或 oauth.clientName）来自证身份，或者通过 https://pi.dev/oauth 上的 Client ID Metadata Document；当 403 要求更多 scope 时会再次登录以提升权限 mcp/README.md §Supported protocol surface CA/src/extensions/mcp/oauth.ts:272。当授权服务器发送 RFC 9207 的 iss 参数时，CIMD client id 是 https://pi.dev/oauth/client.json；不发送时则是 https://pi.dev/oauth/<id>/client.json，并配上对应的回调路径 CA/src/extensions/mcp/oauth.ts:253。凭证写入 agent 目录下的 mcp-auth.json CA/src/extensions/mcp/oauth.ts:144，以 0600 模式创建 CA/src/core/auth-storage.ts:25。

Commands. pi mcp add | remove | list | login | logout work without a session; add and remove take -l/--local for the project file, and list takes --json CA/src/extensions/mcp/cli.ts:33. Inside a session, /mcp opens the manager CA/src/extensions/mcp/index.ts:1141. --no-mcp disables the built-in support for one run CA/src/cli/args.ts:185.

命令。pi mcp add | remove | list | login | logout 无需会话即可使用；add 和 remove 接受 -l/--local 以作用于项目文件，list 接受 --json CA/src/extensions/mcp/cli.ts:33。在会话内，/mcp 打开管理器 CA/src/extensions/mcp/index.ts:1141。--no-mcp 为单次运行禁用内置支持 CA/src/cli/args.ts:185。

D O C ≠ C O D E

文档 ≠ 代码

CA/docs/mcp.md says “HTTP network errors and transient statuses (408, 429, and 5xx) are retried twice”. isTransientError excludes 501 CA/src/extensions/mcp/runtime.ts:72. The same page, and the comment in config.ts, say Pi activates codemode “when a server with codemode exposure connects”. ensureDiscoveryActive activates it from the configuration at session start, before any server connects, so a server that never connects still turns codemode on CA/src/extensions/mcp/index.ts:466.

CA/docs/mcp.md 说「HTTP 网络错误和瞬时状态码（408、429 和 5xx）会重试两次」。而 isTransientError 把 501 排除在外 CA/src/extensions/mcp/runtime.ts:72。同一页以及 config.ts 里的注释都说，Pi 在「某个 codemode exposure 的服务器连上时」激活 codemode。而 ensureDiscoveryActive 是在会话开始时从配置里激活它，早于任何服务器连接，因此一个始终连不上的服务器仍会打开 codemode CA/src/extensions/mcp/index.ts:466。

W H A T T H I S M E A N S F O R Y O U

这 对 你 意 味 着 什 么

Expect MCP tools to be invisible in the request by default; look for them in the mcp_servers section and in codemode scripts.

预期 MCP 工具默认在请求里不可见；要到 mcp_servers 章节和 codemode 脚本里去找它们。

Give each server a one-sentence description; it is the only line the model reads before connecting.

给每个服务器写一句话的 description；这是模型在连接前读到的唯一一行。

Use direct for a few hot tools, and accept that the first prompt waits up to 10 s for their server.

给少数几个高频工具用 direct，并接受第一条提示词为它们的服务器最多等 10 秒。

Keep credentials and auth in the user-level mcp.json; a project file can only toggle and re-expose.

凭证和 auth 放在用户级 mcp.json 里；项目文件只能开关和改 exposure。

Treat a failed tool call as possibly executed; Pi does not retry it, and neither should you.

把失败的工具调用当作「可能已经执行」；Pi 不重试，你也不该重试。

Sources: mcp/README.md (§Supported protocol surface, §OAuth); mcp/package.json. mcp/src/protocol/types.ts (LATEST_PROTOCOL_VERSION, SUPPORTED_PROTOCOL_VERSIONS); mcp/src/client.ts (ClientState, connect, request Internal, handle Progress, cancel Pending, list All); mcp/src/transports/stdio.ts (close, killProcessTree, installExitHook); mcp/src/transports/streamable-http.ts (needs Authorization, reconnect defaults, openGetStream); mcp/src/transports/transport.ts (DEFAULT_MAX_MESSAGE_BYTES). CA/src/core/mcp-servers.ts (McpExposure, McpServerConfigBase, getMcpToolExposure, validateMcpServerConfig); CA/src/extensions/index.ts (builtInExtensions); CA/src/extensions/mcp/config.ts (readConfigFile, loadMcpConfig); CA/src/extensions/mcp/index.ts (renderServersSection, scriptNeedsServer, ensureDiscoveryActive, before_agent_start, tool_call); CA/src/extensions/mcp/tools.ts (createMcpToolName, limitMcpContent, convertMcpResult); CA/src/extensions/mcp/resources.ts. CA/src/extensions/mcp/runtime.ts (isTransientError, with Client, open); CA/src/extensions/mcp/oauth.ts; CA/src/extensions/mcp/cli.ts (HELP); CA/src/core/agent-session.ts (_preparePromptAndToolLoadout); CA/src/core/authstorage.ts; CA/src/cli/args.ts; CA/docs/mcp.md; research/capture/mcp-naming.mjs; research/out/mcp-naming.txt

来源：mcp/README.md（§Supported protocol surface、§OAuth）；mcp/package.json。mcp/src/protocol/types.ts（LATEST_PROTOCOL_VERSION、SUPPORTED_PROTOCOL_VERSIONS）；mcp/src/client.ts（ClientState、connect、requestInternal、handleProgress、cancelPending、listAll）；mcp/src/transports/stdio.ts（close、killProcessTree、installExitHook）；mcp/src/transports/streamable-http.ts（needsAuthorization、reconnect 默认值、openGetStream）；mcp/src/transports/transport.ts（DEFAULT_MAX_MESSAGE_BYTES）。CA/src/core/mcp-servers.ts（McpExposure、McpServerConfigBase、getMcpToolExposure、validateMcpServerConfig）；CA/src/extensions/index.ts（builtInExtensions）；CA/src/extensions/mcp/config.ts（readConfigFile、loadMcpConfig）；CA/src/extensions/mcp/index.ts（renderServersSection、scriptNeedsServer、ensureDiscoveryActive、before_agent_start、tool_call）；CA/src/extensions/mcp/tools.ts（createMcpToolName、limitMcpContent、convertMcpResult）；CA/src/extensions/mcp/resources.ts。CA/src/extensions/mcp/runtime.ts（isTransientError、withClient、open）；CA/src/extensions/mcp/oauth.ts；CA/src/extensions/mcp/cli.ts（HELP）；CA/src/core/agent-session.ts（_preparePromptAndToolLoadout）；CA/src/core/authstorage.ts；CA/src/cli/args.ts；CA/docs/mcp.md；research/capture/mcp-naming.mjs；research/out/mcp-naming.txt

# 6.2 Codemode, scripts that call tools

# 6.2 Codemode：调用工具的脚本

Codemode runs model-written JavaScript in a fresh QuickJS VM whose only

capability is calling tools. Every nested call goes through thefull tool

pipeline, but only the script's output reaches the context.

Codemode 在一个全新的 QuickJS VM 里运行模型写的 JavaScript，它唯一的

能力就是调用工具。每次嵌套调用都走完整的工具

流水线，但只有脚本的输出会进入上下文。

A model that needs fifty issues filtered down to three can make fifty tool calls, or write one script. Codemode is the second option. The model sends JavaScript; Pi runs it in a WebAssembly sandbox where tools.<name>(args) is the only door out; and the nested results stay in the script unless it prints them. This section shows the sandbox and why it is built from a worker, a wasm instance and a shared flag. It then covers the codemode tool: its schema and grammar, the description the model reads, how nested calls run, and what comes back.

一个需要把五十个 issue 过滤成三个的模型，可以发起五十次工具调用，也可以写一个脚本。Codemode 是第二种选择。模型发送 JavaScript；Pi 在一个 WebAssembly 沙箱里运行它，那里 tools.<name>(args) 是唯一的出口；嵌套结果留在脚本里，除非脚本把它们打印出来。本节展示这个沙箱，以及它为什么由一个 worker、一个 wasm 实例和一个共享标志构成；随后说明 codemode 工具：它的 schema 与语法、模型读到的描述、嵌套调用如何执行，以及返回什么。

## Two packages

## 两个包

@earendil-works/pi-codemode 1.0.4 “runs model-written JavaScript in a QuickJS VM (compiled to WebAssembly) where the only capability is calling injected tools. Nested tool calls never enter the LLM context; only the script’s output and return value do” codemode/README.md. It has no Pi dependencies and one runtime dependency, quickjs-wasi 3.6.2 codemode/package.json.

@earendil-works/pi-codemode 1.0.4「在一个 QuickJS VM（编译为 WebAssembly）里运行模型写的 JavaScript，那里唯一的能力是调用注入的工具。嵌套的工具调用绝不进入 LLM 上下文；进入的只有脚本的输出和返回值」codemode/README.md。它没有任何 Pi 依赖，只有一个运行时依赖 quickjs-wasi 3.6.2 codemode/package.json。

The codemode tool itself is a built-in, replaceable extension in CA/src/extensions/codemode/: tool.ts (419 lines) builds the definition and description, execute.ts (675) runs a script, renderer.ts (150) draws it in the TUI. It is registered with default Active: false CA/src/extensions/codemode/index.ts:43. --tools, the default Tools setting or setActiveTools() turn it on, and so does the MCP extension when a configured server has codemode tools (MCP (p. 144)).

codemode 工具本身是 CA/src/extensions/codemode/ 里一个可替换的内置扩展：tool.ts（419 行）构建定义和描述，execute.ts（675）运行脚本，renderer.ts（150）在 TUI 里绘制它。它注册时的默认值是 Active: false CA/src/extensions/codemode/index.ts:43。--tools、默认的 Tools 设置或 setActiveTools() 都能打开它；当某个已配置的服务器带有 codemode 工具时，MCP 扩展也会打开它（MCP（p. 144））。

## The sandbox

## 沙箱

Each execute() creates a new worker_threads Worker, and the worker instantiates a new QuickJS VM from the compiled wasm module. “A fresh worker per run keeps termination simple: a runaway script, including one that only spins the microtask queue, is killed with terminate() and cannot poison a later run” codemode/src/runtime/host.ts:120.

每次 execute() 都创建一个新的 worker_threads Worker，由该 worker 从编译好的 wasm 模块实例化出一个新的 QuickJS VM。「每次运行都用全新的 worker，让终止变得简单：失控的脚本，包括那些只是空转微任务队列的脚本，都会被 terminate() 杀掉，也无法污染之后的运行」codemode/src/runtime/host.ts:120。

![](images/72b7bdeb15daabfc5bd50ce3cb43ffe93c47d1aa908e6afb74ef6a45314b6c1f.jpg)
The VM reaches the host only through one bridge function, and the host can stop it two ways. Messages cross as JSON strings; the worker never builds structured values itself. Schematic, from codemode/src/runtime/protocol.ts (WorkerData, WorkerToHostMessage, HostToWorkerMessage), worker.ts and host.ts.

VM 只能通过一个桥函数触达宿主，而宿主有两种方式让它停下。消息以 JSON 字符串往返；worker 自己从不构造结构化值。示意图取自 codemode/src/runtime/protocol.ts（WorkerData、WorkerToHostMessage、HostToWorkerMessage）、worker.ts 和 host.ts。

Isolation. The VM is a separate wasm instance with its own linear memory. Its only imports are a WASI shim, whose stdout and stderr writes the worker discards, and one host-call entry point codemode/src/runtime/worker.ts:32. There are no timers, fetch, process, require, modules or WebAssembly; “eval and Function work but only produce more code inside the same VM” codemode/README.md. Before the script runs, the prelude freezes the built-ins, so a script that patches

Array.prototype.toJSON cannot corrupt what the prelude reports to the host codemode/src/runtime/prelude-source.ts:28.

隔离。VM 是一个独立的 wasm 实例，有自己的线性内存。它唯一的导入是一个 WASI shim（其 stdout 和 stderr 写入被 worker 丢弃）和一个宿主调用入口 codemode/src/runtime/worker.ts:32。这里没有计时器、fetch、process、require、模块或 WebAssembly；「eval 和 Function 能用，但只是在同一个 VM 里产出更多代码」codemode/README.md。脚本运行之前，prelude 会冻结内建对象，因此一个篡改

Array.prototype.toJSON 的脚本无法破坏 prelude 向宿主报告的内容 codemode/src/runtime/prelude-source.ts:28。

Why a worker. QuickJS runs synchronously; a spinning script on the host thread would block Pi’s event loop. Why the flag. On Bun, terminate() “cannot stop a thread that is spinning in wasm” codemode/src/runtime/protocol.ts:21, so the host first sets the shared Int32 and the VM’s interrupt Handler polls it codemode/src/runtime/worker.ts:60. Why maxStackSize. Without it, “deep recursion overflows the wasm stack and traps instead of throwing a catchable RangeError” codemode/src/runtime/worker.ts:57

为什么用 worker。QuickJS 是同步运行的；在宿主线程上空转的脚本会阻塞 Pi 的事件循环。为什么用标志。在 Bun 上，terminate()「无法停止一个在 wasm 里空转的线程」codemode/src/runtime/protocol.ts:21，所以宿主先设置共享的 Int32，VM 的 interruptHandler 再轮询它 codemode/src/runtime/worker.ts:60。为什么用 maxStackSize。没有它，「深递归会溢出 wasm 栈并触发 trap，而不是抛出可捕获的 RangeError」codemode/src/runtime/worker.ts:57

The capture kit ran five scripts against the pinned build with a one-second deadline:

采集套件以一秒为截止时间，对固定版本构建运行了五个脚本：

<table><tr><td>脚本</td><td>结果</td></tr><tr><td>在 Promise.all 里做两次 tools.read 调用，store，return</td><td>ok，两次调用都 ok，storeWrites.set = { seen: 2 }</td></tr><tr><td>typeof fetch、setTimeout、process、require、WebAssembly；eval(&quot;1 + 1&quot;)；Object.isFrozen(Array.prototype)</td><td>五个 &quot;undefined&quot;、2、true</td></tr><tr><td>await new Promise( () =&gt; {} )</td><td>script：「脚本正在等待一个永远不会落定的 promise：没有待处理的工具调用，而且这里不存在计时器。」</td></tr><tr><td>while (true) {}</td><td>timeout：「Execution timed out after 1000 ms」</td></tr><tr><td>try 里的无限递归</td><td>ok，值 &quot;RangeError: Maximum call stack size exceeded&quot;</td></tr></table>

A stalled script fails at once; a spinning one waits for the deadline. From research/out/codemode-sandbox.txt, produced by research/capture/codemodesandbox.mjs.

卡住的脚本立刻失败；空转的脚本则一直等到截止时间。取自 research/out/codemode-sandbox.txt，由 research/capture/codemodesandbox.mjs 生成。

execute() never rejects for a script failure. result.error.kind is script, timeout, aborted or sandbox (a wasm trap or a missing worker file) codemode/README.md §Results. The README puts the start-up cost at “about 20 ms including VM creation” per execution; the capture kit did not time it.

脚本失败时 execute() 绝不 reject。result.error.kind 为 script、timeout、aborted 或 sandbox（wasm trap 或 worker 文件缺失）codemode/README.md §Results。README 把启动成本记为每次执行「约 20 ms，含 VM 创建」；采集套件没有计时。

<table><tr><td>限制</td><td>值</td><td>设置位置</td></tr><tr><td>MAX_OUTPUT_CHARS</td><td>16 Mi 字符的文本和 base64 图像数据</td><td>codemode/src/runtime/prelude-source.ts:40</td></tr><tr><td>MAX_OUTPUT_ITEMS</td><td>100,000 个条目</td><td>codemode/src/runtime/prelude-source.ts:41</td></tr><tr><td>MAX_STORE_VALUE_CHARS</td><td>每个值 256 Ki 字符的 JSON</td><td>codemode/src/runtime/prelude-source.ts:32</td></tr><tr><td>MAX_STORE_TOTAL_CHARS</td><td>所有值合计 1 Mi 字符</td><td>codemode/src/runtime/prelude-source.ts:33</td></tr><tr><td>截止时间，库</td><td>300,000 ms</td><td>codemode/src/runtime/host.ts:22</td></tr><tr><td>截止时间，Pi</td><td>除非设置 timeout_ms，否则没有</td><td>CA/src/extensions/codemode/execute.ts:427</td></tr><tr><td>VM 堆，Pi</td><td>256 MiB</td><td>CA/src/extensions/codemode/execute.ts:55</td></tr><tr><td>并发 models.* 调用，Pi</td><td>4</td><td>CA/src/extensions/codemode/execute.ts:49</td></tr></table>

Pi removes the library’s five-minute deadline and adds a heap cap. Past either output limit the script fails with a RangeError, “even if it catches the error” codemode/README.md §Results.

Pi 去掉了库里的五分钟截止时间，并加上堆上限。超过任一输出上限，脚本都会以 RangeError 失败，「即使它捕获了这个错误」codemode/README.md §Results。

## The codemode tool

## codemode 工具

The schema has one field. Three more properties of the definition matter as much:

schema 只有一个字段。定义里另外三个属性同样重要：

```typescript the input schema and the parts of the definition that shape it CA/src/extensions/codemode/tool.ts TS

export const codemodeSchema = Type.Object({
    code: Type.String({
    description: "Raw JavaScript source.",
    }),
});
...
parameters: codemodeSchema,
// Scripts must not start other scripts.
exposure: "model-only",
prepareLoadout: (loadout) => prepareCodemodeLoadout(loadout, options),
// Capable models write the script as raw text instead of a JSON-escaped string.
constrainedSampling: { type: "grammar", variants: { openai_lark: CODEMODE_SOURCE_GRAMMAR } },
```

Lines 89–93 and 390–395; the rest of createCodemodeToolDefinition is cut.

第 89–93 行和 390–395 行；createCodemodeToolDefinition 的其余部分已略去。

The grammar lets a model that supports grammar-constrained tool input emit raw JavaScript rather than a JSON-escaped string. It fixes only the shape of an optional options line; the JSON and the code are checked by parseCodemodeSource codemode/src/source.ts:18.

这套语法让支持语法约束工具输入的模型可以直接输出原始 JavaScript，而不是 JSON 转义字符串。它只固定一行可选 options 行的形状；JSON 和代码本身由 parseCodemodeSource 校验 codemode/src/source.ts:18。

```txt
CODEMODE_SOURCE_GRAMMAR codemode/src/source.ts start: options_source | plain_source options_source: OPTIONS_LINE NEWLINE SOURCE
plain_source: SOURCE
OPTIONS_LINE: /[\t]*\// @options:[^\r\n]*/
NEWLINE: /\r?\n/
SOURCE: /[\s\S]+/
```

```txt
完整内容，第 23–29 行。
```

The options line is // @options: {"max_output_tokens": N, "timeout_ms": N}. Any other field, invalid JSON, or an options line with no code after it throws CodemodeSourceError; timeout_ms must be a positive integer up to 2,147,483,647, the largest set Timeout delay codemode/src/source.ts:16. The line is replaced by an empty line, so line numbers in stack traces still match codemode/src/source.ts:40.

options 行形如 // @options: {"max_output_tokens": N, "timeout_ms": N}。出现其他字段、JSON 无效，或者 options 行之后没有代码，都会抛出 CodemodeSourceError；timeout_ms 必须是正整数，最大 2,147,483,647，也就是 setTimeout 能设置的最大延迟 codemode/src/source.ts:16。该行会被替换成一个空行，因此栈追踪里的行号仍然对得上 codemode/src/source.ts:40。

The description. createCodemodeDescription builds what the model reads: an intro, a list of globals, shared MCP types when a listed tool needs them, and one section per listed tool, grouped by namespace CA/src/extensions/codemode/tool.ts:248. With read as the only listed tool, the build produces:

描述。createCodemodeDescription 构建模型读到的内容：一段引言、一份全局对象清单、当被列出的工具需要时补上共享的 MCP 类型，以及每个被列出工具各一节、按命名空间分组 CA/src/extensions/codemode/tool.ts:248。以 read 作为唯一被列出的工具时，构建产物如下：

```markdown
Run JavaScript that calls other tools. The input is raw JavaScript (not JSON, no code fence), run as an async function body in a QuickJS sandbox: top-level `await` and `return` work. No Node, file system, network, or timers.
- `await tools.<name>({ ...args })` resolves to a string, or an object if the tool's declaration says so, and rejects with an Error on failure. Calls still running when the script ends are cancelled.
- Optional first line: // @options: {"max_output_tokens": 10000, "timeout_ms": 60000}
Globals:
- `text(value)`, `image(dataUrlOrImageBlock)`, `console.log(...)`, and top-level `return` add output;
`exit()` ends the script. `image()` also saves the image to a temp file and the result names its path.
- `store(key, value)` and `load(key)` keep JSON values across codemode calls.
- `ALL_TOOLS`, `searchTools(query, { limit?, namespace? })`, `describeTool(name)`, `describeNamespace(name)`: find unlisted tools, such as MCP tools.

Nested tools:

### `read`
Read a file

codemode tool declaration:
```ts declare const tools: { read(args: { path: string; }) : Promise<string>; };
```

That is the complete output of createCodemodeDescription([read], {}) research/out/codemode-sandbox.txt. The models line is absent because the models option was not set.

这就是 createCodemodeDescription([read], {}) 的完整输出 research/out/codemode-sandbox.txt。没有 models 这一行，是因为 models 选项未被设置。

Three rules decide which tools get a section.

三条规则决定哪些工具能拿到一节。

Budget — listed sections share codemode.inlineBudget, default 3,000 estimated tokens at 4 characters per token CA/src/extensions/codemode/tool.ts:156. Selection is round-robin: in each round every namespace group places its cheapest remaining tool, and a group whose next tool does not fit drops out, so every namespace appears before any is complete CA/src/extensions/codemode/tool.ts:222.

预算 —— 被列出的各节共享 codemode.inlineBudget，默认按每 token 4 字符估算为 3,000 token CA/src/extensions/codemode/tool.ts:156。挑选是轮转式的：每一轮里，每个命名空间组都放上它剩余最便宜的那个工具，而下一个工具放不下的组就退出，因此每个命名空间都会在任何一组完成之前出现 CA/src/extensions/codemode/tool.ts:222。

Deferred tools are never listed — that includes MCP tools with the default codemode exposure. They “do not afect the description at all, so it stays the same while MCP servers connect” CA/src/extensions/codemode/tool.ts:244. Scripts find them with searchTools(query), a BM25 ranking with a default limit of 8, describeTool(name) and describeNamespace(name) CA/src/extensions/codemode/execute.ts:496.

deferred 工具永远不会被列出 —— 这包括默认 codemode exposure 的 MCP 工具。它们「完全不影响描述，所以在 MCP 服务器连接期间描述保持不变」CA/src/extensions/codemode/tool.ts:244。脚本用 searchTools(query)（BM25 排序，默认上限 8）、describeTool(name) 和 describeNamespace(name) 找到它们 CA/src/extensions/codemode/execute.ts:496。

codemode.mode — on (default) lists only callable tools without direct exposure and adds a “Codemode: tools.<id>(args) resolves to …” line to each declared tool’s own description. only lists every callable tool and drops the declarations of active direct tools from the request CA/src/extensions/codemode/tool.ts:342.

codemode.mode —— on（默认）只列出没有 direct exposure 的可调用工具，并在每个已声明工具自己的描述里加一行「Codemode: tools.<id>(args) resolves to …」。only 则列出所有可调用工具，并把启用中的 direct 工具的声明从请求里去掉 CA/src/extensions/codemode/tool.ts:342。

Running a script

运行脚本

![](images/922188e19cb804d9b56381e04c80e21a8e4e52abd5614f27d79df57a87b88c2b.jpg)
The nested result stops at the VM; only step 5 reaches the model. Step 3 is the arrow the figure is about: the nested call is a full tool call with its own id and hooks. Schematic, from CA/src/extensions/codemode/execute.ts (executeCodemode, toScriptValue) and CA/src/core/nested-tool-calls.ts (NestedToolCallRunner).

嵌套结果止步于 VM；只有第 5 步抵达模型。第 3 步正是图里画的那根箭头：嵌套调用是一次完整的工具调用，有自己的 id 和钩子。示意图取自 CA/src/extensions/codemode/execute.ts（executeCodemode、toScriptValue）和 CA/src/core/nested-tool-calls.ts（NestedToolCallRunner）。

Nested calls. A script can call the active direct tools and every codemode or deferred tool, but not codemode itself, whose exposure is model-only CA/src/extensions/codemode/tool.ts:392. Each call goes through ctx.executeTool(name, args, { signal }), so validation, tool_call and tool_result hooks and permission gates apply as for a direct call CA/src/extensions/codemode/execute.ts:405. The nested call gets the id <codemode call id>/<n>, with n counting from 1, and its execution events carry parentToolCallIdCA/src/core/nested-tool-calls.ts:188.

嵌套调用。脚本可以调用启用中的 direct 工具，以及每个 codemode 或 deferred 工具，但不能调用 codemode 本身，因为它的 exposure 是 model-only CA/src/extensions/codemode/tool.ts:392。每次调用都走 ctx.executeTool(name, args, { signal })，因此校验、tool_call 与 tool_result 钩子和权限闸门的适用方式与 direct 调用相同 CA/src/extensions/codemode/execute.ts:405。嵌套调用拿到的 id 是 <codemode call id>/<n>，n 从 1 开始计数，其执行事件携带 parentToolCallIdCA/src/core/nested-tool-calls.ts:188。

What a call resolves to CA/src/extensions/codemode/execute.ts:347:

一次调用 resolve 成什么 CA/src/extensions/codemode/execute.ts:347：

a tool that declares output Schema resolves to its structured Content, also for an error result that carries one. Every MCP tool declares one. An MCP call therefore resolves to the whole CallToolResult, isError included (MCP (p. 144));

声明了 outputSchema 的工具 resolve 成它的结构化 content，带结构化 content 的错误结果也一样。每个 MCP 工具都声明了。因此一次 MCP 调用 resolve 成整个 CallToolResult，包含 isError（MCP（p. 144））；

any other tool resolves to its text content as one string;

其他任何工具 resolve 成它的文本内容，合并为一个字符串；

a failed, blocked or invalid call rejects with an Error carrying the tool’s error text.

失败、被拦截或无效的调用会 reject 一个 Error，带着该工具的错误文本。

The store. store(key, value) and load(key) keep JSON values across calls. A successful script that wrote anything appends one codemode-store custom entry { set, delete } CA/src/extensions/codemode/execute.ts:451. load() replays those entries along the current branch from the root CA/src/extensions/codemode/execute.ts:217, so the store follows /tree, resume and fork (sessions, the JSONL tree (p. 86)). A failed script reports no writes. Its nested calls have already run, and nothing undoes them.

store。store(key, value) 和 load(key) 让 JSON 值跨调用保留。成功且写入过东西的脚本会追加一条 codemode-store 自定义条目 { set, delete } CA/src/extensions/codemode/execute.ts:451。load() 会从根开始沿当前分支重放这些条目 CA/src/extensions/codemode/execute.ts:217，因此 store 跟随 /tree、resume 和 fork（会话、JSONL 树（p. 86））。失败的脚本不报告任何写入。它的嵌套调用已经执行过了，也没有什么会撤销它们。

The result. The content starts with Script completed or Script failed, then Wall time N seconds, then Output: CA/src/extensions/codemode/execute.ts:470. A returned value is appended like text(); a failure appends Script error: and the error after the partial output. Text over max_output_tokens, default 10,000 CA/src/extensions/codemode/execute.ts:231, keeps its head and tail around a …N tokens truncated… marker, and the full text goes to a temp file. Images are saved to temp files and the result names each path.

结果。内容以 Script completed 或 Script failed 开头，然后是 Wall time N seconds，再是 Output: CA/src/extensions/codemode/execute.ts:470。返回的返回值像 text() 一样被追加；失败时追加 Script error:，并把错误放在部分输出之后。文本超过 max_output_tokens（默认 10,000 CA/src/extensions/codemode/execute.ts:231）时，会在 …N tokens truncated… 标记两侧保留头尾，全文写入临时文件。图像被保存到临时文件，结果中会给出每个路径。

## R U L E O F T H U M B

## 经 验 法 则

If the model needs every byte of a result, let it call the tool directly. If it needs a count, a filter or a join across several calls, give it codemode: the nested results stay in the VM and the context pays only for what the script prints. Set timeout_ms in the options line when a script calls a slow server; Pi sets no deadline of its own.

如果模型需要结果的每一个字节，就让它直接调用那个工具。如果它需要的是对多次调用的计数、筛选或合并，就给它 codemode：嵌套结果留在 VM 里，上下文只为脚本打印的内容付出代价。脚本调用慢服务器时，在 options 行里设置 timeout_ms；Pi 自己不设截止时间。

Sources: codemode/README.md (§Results, §How it works, §Store); codemode/package.json. codemode/src/runtime/protocol.ts (WorkerData, WorkerToHostMessage, HostToWorkerMessage); codemode/src/runtime/worker.ts (main, discardOutput, bridge); codemode/src/runtime/host.ts (Execution, DEFAULT_TIMEOUT_MS); codemode/src/runtime/prelude-source.ts (limits, freezing); codemode/src/source.ts (CODEMODE_SOURCE_GRAMMAR, parseCodemodeSource). CA/src/extensions/codemode/index.ts; CA/src/extensions/codemode/tool.ts (codemodeSchema, DESCRIPTION_INTRO, selectCatalog, createCodemodeDescription, prepareCodemodeLoadout, createCodemodeToolDefinition); CA/src/extensions/codemode/execute.ts (executeCodemode, toScriptValue, readCodemodeStore, createDiscoveryGlobals, truncateOutput). CA/src/core/nested-tool-calls.ts (NestedToolCallRunner.execute); CA/src/core/settings-manager.ts (CodemodeSettings); research/capture/codemodesandbox.mjs; research/out/codemode-sandbox.txt

来源：codemode/README.md（§Results、§How it works、§Store）；codemode/package.json。codemode/src/runtime/protocol.ts（WorkerData、WorkerToHostMessage、HostToWorkerMessage）；codemode/src/runtime/worker.ts（main、discardOutput、bridge）；codemode/src/runtime/host.ts（Execution、DEFAULT_TIMEOUT_MS）；codemode/src/runtime/prelude-source.ts（limits、freezing）；codemode/src/source.ts（CODEMODE_SOURCE_GRAMMAR、parseCodemodeSource）。CA/src/extensions/codemode/index.ts；CA/src/extensions/codemode/tool.ts（codemodeSchema、DESCRIPTION_INTRO、selectCatalog、createCodemodeDescription、prepareCodemodeLoadout、createCodemodeToolDefinition）；CA/src/extensions/codemode/execute.ts（executeCodemode、toScriptValue、readCodemodeStore、createDiscoveryGlobals、truncateOutput）。CA/src/core/nested-tool-calls.ts（NestedToolCallRunner.execute）；CA/src/core/settings-manager.ts（CodemodeSettings）；research/capture/codemodesandbox.mjs；research/out/codemode-sandbox.txt

## 6.3 pi-tui, the terminal UI framework

## 6.3 pi-tui：终端 UI 框架

Every component turns a width into a list oflines, and the renderer writes only the lines that changed, inside one synchronized-output block. Pi's default renderer is the alternate-screen one, which never errors on an overwide line; the scrollback one does.

每个组件把一个宽度变成一组行，渲染器只写发生变化的行，并包在一个同步输出块里。Pi 的默认渲染器是备用屏幕那个，它在超宽行上从不报错；回滚缓冲那个会。

Everything a person sees in interactive Pi — the editor, the streaming transcript, tool output, /mcp and every extension dialog — is drawn by @earendil-works/pi-tui. Its README calls it a “minimal terminal UI framework with diferential rendering and synchronized output for flicker-free interactive CLI applications” tui/README.md. This section shows the component contract, the two renderers and the bytes they write, how keyboard input is negotiated and routed, overlays, terminal capabilities and native addons, and the built-in components. The package has two runtime dependencies, get-east-asian-width 1.6.0 and marked 18.0.11; its tests run on node:test, several of them against @xterm/headless 5.5.0 tui/package.json.

交互式 Pi 里人所看到的一切 —— 编辑器、流式记录、工具输出、/mcp 以及每个扩展对话框 —— 都由 @earendil-works/pi-tui 绘制。它的 README 自称是「一个极简的终端 UI 框架，带差分渲染和同步输出，用于无闪烁的交互式 CLI 应用」tui/README.md。本节展示组件契约、两个渲染器及它们写出的字节、键盘输入如何协商与路由、覆盖层、终端能力与原生插件，以及内置组件。这个包有两个运行时依赖，get-east-asian-width 1.6.0 和 marked 18.0.11；它的测试跑在 node:test 上，其中几个跑在 @xterm/headless 5.5.0 上 tui/package.json。

#### A component is a function of width

#### 组件是宽度的函数

```typescript the whole component contract tui/tui.ts TS

export interface Component {
    /**
    * Render the component to lines for the given viewport width
    * @param width - Current viewport width
    * @returns Array of strings, each representing a line
    */
    render(width: number): string[];
    /** Optional handler for keyboard input when component has focus. */
    handleInput?(data: string): void;

    /** Optional normalized mouse handler. */
    handleMouse?(event: TuiMouseEvent): TuiMouseEventResult | undefined;

    /**
    * If true, component receives key release events (Kitty protocol).
    * Default is false - release events are filtered out.
    */
    wantsKeyRelease?: boolean;

    /**
    * Invalidate any cached rendering state.
    * Called when theme changes or when component needs to re-render from scratch.
    */
    invalidate(): void;
}
```

Complete, lines 117–142.

完整内容，第 117–142 行。

A component returns ANSI-styled lines; handle Input receives raw bytes, escape sequences included, while the component has focus. A Focusable component has one more field, focused, and while it is true it emits CURSOR_MARKER,

"\x1b_pi:c\x07", a zero-width APC sequence, where the cursor belongs. The renderer finds the marker, strips it and puts the hardware cursor there, which is where an IME draws its candidate window tui/tui.ts:180 tui/tui.ts:196. Container stacks its children vertically and routes a mouse event to the child whose rows contain its y tui/tui.ts:347.

组件返回带 ANSI 样式的行；组件获得焦点期间，handleInput 接收原始字节，包括转义序列。Focusable 组件多一个字段 focused，只要它为真就会输出 CURSOR_MARKER，

即 "\x1b_pi:c\x07"，一个零宽的 APC 序列，标示光标应在的位置。渲染器找到这个标记、把它剥掉，再把硬件光标放到那里，输入法的候选窗就画在那里 tui/tui.ts:180 tui/tui.ts:196。Container 把子组件竖直堆叠，并把鼠标事件路由到行范围包含其 y 坐标的那个子组件 tui/tui.ts:347。

After compositing, the renderer appends SEGMENT_RESET, "\x1b[0m\x1b]8;;\x07" (SGR reset plus an OSC 8 close), to every line that is not an image, so neither a style nor a hyperlink leaks into the next line tui/tui.ts:412 tui/tui.ts:1413.

合成之后，渲染器会向每一行非图像的行追加 SEGMENT_RESET，即 "\x1b[0m\x1b]8;;\x07"（SGR 重置加 OSC 8 关闭），这样样式和超链接都不会渗到下一行 tui/tui.ts:412 tui/tui.ts:1413。

The width rule. The README is strict: “Each line must not exceed width or the TUI will error” tui/README.md. The code is stricter in one renderer and looser in the other, as the DOC ≠ CODE callout below shows.

宽度规则。README 说得很严格：「每一行都不得超过 width，否则 TUI 会报错」tui/README.md。而代码在一个渲染器上更严、另一个上更松，正如下面 DOC ≠ CODE 的提示框所示。

## Two renderers

## 两个渲染器

S T R U C T U R E

结 构

Container children: Component[] · vertical stack · mouse by row

Container 子组件：Component[] · 竖直堆叠 · 按行处理鼠标

«interface» TUI mode · setFocus · showOverlay · requestRender · start · stop

«interface» TUI mode · setFocus · showOverlay · requestRender · start · stop

↓ extends Container, implements TUI

↓ extends Container, implements TUI

«abstract» TuiBase focus · overlay stack · input routing · 16 ms render throttle · abstract doRender()

«abstract» TuiBase focus · 覆盖层栈 · 输入路由 · 16 ms 渲染节流 · 抽象的 doRender()

TuiMainScreen · mode “regular” line dif against the previous frame · output stays in terminal scrollback · overwide line throws

TuiMainScreen · mode “regular” 逐行与上一帧做差分 · 输出留在终端回滚缓冲 · 超宽行抛错

TuiAltScreen · mode “fullscreen” alternate screen · row dif · mouse, selection, search, scrollbar · over-wide line sliced · Pi’s default

TuiAltScreen · mode “fullscreen” 备用屏幕 · 按行差分 · 鼠标、选区、搜索、滚动条 · 超宽行被切片 · Pi 的默认

Pi picks the alternate-screen renderer unless tui Mode is "regular". Both share TuiBase; only doRender() difers. Schematic, from tui/tui.ts (Component, Container, TUI, TuiBase), tui-main-screen.ts, tui-alt-screen.ts, and CA/src/modes/interactive/tui-renderer.ts (createInteractiveTui).

除非 tuiMode 是 "regular"，Pi 会选备用屏幕渲染器。两者共用 TuiBase；只有 doRender() 不同。示意图取自 tui/tui.ts（Component、Container、TUI、TuiBase）、tui-main-screen.ts、tui-alt-screen.ts 和 CA/src/modes/interactive/tui-renderer.ts（createInteractiveTui）。

The coding agent’s tui Mode setting defaults to "fullscreen" CA/src/core/settings-manager.ts:184, and createInteractiveTui builds a TuiAltScreen for it and a TuiMainScreen only for "regular"

编码智能体的 tuiMode 设置默认是 "fullscreen" CA/src/core/settings-manager.ts:184，而 createInteractiveTui 为它构建 TuiAltScreen，只在 "regular" 时构建 TuiMainScreen

CA/src/modes/interactive/tui-renderer.ts:22.

CA/src/modes/interactive/tui-renderer.ts:22。

Scheduling. MIN_RENDER_INTERVAL_MS is 16, about 60 frames a second tui/tui.ts:507. request Render() sets a flag and defers to process.next Tick, which schedules a set Timeout for the rest of the 16 ms; further requests in the meantime coalesce into that one frame tui/tui.ts:990. Keyboard input skips the throttle, because “even set Timeout(0) can take a full 16 ms tick on Windows” tui/tui.ts:1117.

调度。MIN_RENDER_INTERVAL_MS 是 16，约合每秒 60 帧 tui/tui.ts:507。requestRender() 设置一个标志并把工作推迟给 process.nextTick，由它为剩下的 16 ms 安排一次 setTimeout；这期间再来的请求会合并进那一帧 tui/tui.ts:990。键盘输入不受节流限制，因为「即便 setTimeout(0)，在 Windows 上也可能耗掉完整的 16 ms 一个 tick」tui/tui.ts:1117。

The main-screen frame. TuiMainScreen.doRender() renders the tree, composites overlays, extracts the cursor marker, applies the per-line resets, then decides between a full and a diferential write tui/tui-main-screen.ts:247.

主屏幕帧。TuiMainScreen.doRender() 渲染树、合成覆盖层、取出光标标记、逐行应用重置，然后在全量写入和差分写入之间做选择 tui/tui-main-screen.ts:247。

![](images/cd54ea92ecfb4a73e0b2ed172435f0f0e00bb60e680d51607398acf5f2c3be44.jpg)

First match wins; every rose row clears the scrollback. Every write is wrapped in synchronized output (CSI ? 2026 h/l), so the terminal shows whole frames. Writes go through BoundedTerminalWriter, which streams in 1 MiB chunks so a full render never builds a string past V8’s limit. From tui/tui-main-screen.ts:247– 567.

第一个匹配项胜出；升起的每一行都会清空回滚缓冲。每次写入都包在同步输出（CSI ? 2026 h/l）里，因此终端显示的是完整帧。写入走 BoundedTerminalWriter，它按 1 MiB 的块流式输出，因此全量渲染不会拼出超过 V8 上限的字符串。取自 tui/tui-main-screen.ts:247– 567。

The capture kit drove TuiMainScreen with a stub 20 × 10 terminal and three Text lines, then changed the middle one. Escape bytes are shown as \u001b:

采集套件用一个 20 × 10 的桩终端和三行 Text 驱动 TuiMainScreen，然后改动中间那一行。转义字节以 \u001b 呈现：

```txt
#### frame 1: first render
"\u001b[?2026halpha \u001b[0m\u001b]8;;\u0007\r\nbeta
\u001b[0m\u001b]8;;\u0007\r\ngamma \u001b[0m\u001b]8;;\u0007\u001b[?2026l"
#### frame 2: line 1 changed
"\u001b[?2026h\u001b[1A\r\u001b[2KBETA \u001b[0m\u001b]8;;\u0007\u001b[?2026l"
#### frame 3: nothing changed full Redraws: 1
```

Frame 2 is the whole point of the design: one cursor-up, one line clear, 20 columns and a reset: 55 bytes for a one-word change. Frame 3 writes nothing. Text pads every line to the width, so the reset lands after column 20 research/out/tui-frames.txt.

第 2 帧正是整个设计的意义所在：一次光标上移、一次清行、20 列加一次重置——一个词的改动只花 55 字节。第 3 帧什么都不写。Text 会把每行补齐到宽度，因此重置正好落在第 20 列之后 research/out/tui-frames.txt。

The alternate-screen frame. TuiAltScreen enters with \x1b[?1049h, turns of autowrap and, when the mouse is enabled, turns on modes 1000, 1002, 1004 (focus reporting) and 1006 (SGR mouse) tui/tui-alt-screen.ts:63. It difs row by row against the previous screen and rewrites a changed row with an absolute CSI <row>;1H plus CSI 2K tui/tui-alt-screen.ts:1745, again inside CSI ? 2026 h/l. On top of that it adds VStack, HStack and ScrollView layout, a follow-end transcript, OSC 133 prompt jumps, a scrollbar, drag-select with OSC 52 copy, clickable OSC 8 links, and transcript search tui/tui-altscreen.ts:202. On exit Pi restores the main screen and prints the transcript, or only a resume hint when fullscreenExitOutput is "resume-hint"CA/src/core/settings-manager.ts:185.

备用屏幕帧。TuiAltScreen 以 \x1b[?1049h 进入，关闭自动换行，并在启用鼠标时打开模式 1000、1002、1004（焦点报告）和 1006（SGR 鼠标）tui/tui-alt-screen.ts:63。它逐行与上一屏做差分，用绝对的 CSI <row>;1H 加 CSI 2K 重写变化的行 tui/tui-alt-screen.ts:1745，同样包在 CSI ? 2026 h/l 里。除此之外它还提供 VStack、HStack 和 ScrollView 布局、跟随末尾的记录、OSC 133 提示符跳转、滚动条、带 OSC 52 复制的拖拽选中、可点击的 OSC 8 链接，以及记录搜索 tui/tui-altscreen.ts:202。退出时 Pi 恢复主屏并打印记录；当 fullscreenExitOutput 为 "resume-hint" 时只打印一条恢复提示 CA/src/core/settings-manager.ts:185。

```javascript request flags 7, query them, and send DA1 as a sentinel tui/terminal.ts const DESIRED_KITTY_KEYBOARD_PROTOCOL_FLAGS = 7;
const KEYBOARD_PROTOCOL_RESPONSE_FRAGMENT_TIMEOUT_MS = 150;
const KITTY_KEYBOARD_PROTOCOL_QUERY = '\x1b[>${DESIRED_KITTY_KEYBOARD_PROTOCOL_FLAGS}u\x1b[?u\x1b[c';
```

Three environment variables help debugging: PI_TUI_DEBUG_REDRAW=1 logs the reason for each main-screen full redraw to pi-tui-debug.log tui/tui-main-screen.ts:321, PI_TUI_DEBUG=1 writes one log file per diferential frame under /tmp/tui tui/tui-main-screen.ts:569, and PI_TUI_WRITE_LOG=<file> captures the raw output stream tui/terminal.ts:152.

三个环境变量有助于调试：PI_TUI_DEBUG_REDRAW=1 把主屏每次全量重绘的原因记录到 pi-tui-debug.log tui/tui-main-screen.ts:321；PI_TUI_DEBUG=1 在 /tmp/tui 下为每个差分帧写一个日志文件 tui/tui-main-screen.ts:569；PI_TUI_WRITE_LOG=<file> 则捕获原始输出流 tui/terminal.ts:152。

D O C ≠ C O D E The README says an over-wide line makes “the TUI … error”. In TuiMainScreen the check sits only on the diferential path: a line wider than the terminal writes pi-tui-crash.log, stops the TUI and throws “Rendered line N exceeds terminal width” tui/tuimain-screen.ts:517; a first frame or full redraw writes it unchecked. TuiAltScreen, Pi’s default, never throws and slices the line to the width with sliceByColumn tui/tui-alt-screen.ts:1692. The capture kit confirmed the throw: a raw component returning 25 columns in a 20-column terminal stopped frame 5 with “Rendered line 3 exceeds terminal width (25 > 20).” research/out/tuiframes.txt

文档 ≠ 代码 README 说超宽的行会让「TUI …… 报错」。在 TuiMainScreen 里，这个检查只存在于差分路径上：比终端更宽的行会写入 pi-tui-crash.log、停掉 TUI，并抛出「Rendered line N exceeds terminal width」tui/tuimain-screen.ts:517；而首帧或全量重写时不会检查。Pi 默认的 TuiAltScreen 从不抛错，它用 sliceByColumn 把行切到宽度 tui/tui-alt-screen.ts:1692。采集套件证实了这个抛出：在 20 列终端里，一个返回 25 列的裸组件让第 5 帧停下并报「Rendered line 3 exceeds terminal width (25 > 20).」research/out/tuiframes.txt

## Input and the keyboard protocol

## 输入与键盘协议

ProcessTerminal.start puts stdin in raw mode and enables bracketed paste with \x1b[?2004h tui/terminal.ts:174. It then negotiates the Kitty keyboard protocol in one write:

ProcessTerminal.start 把 stdin 置为原始模式，并用 \x1b[?2004h 启用括号粘贴 tui/terminal.ts:174。然后它用一次写入协商 Kitty 键盘协议：

Lines 12–14. Flags 7 = 1 (disambiguate escape codes) + 2 (report press, repeat and release) + 4 (report alternate keys).

第 12–14 行。标志位 7 = 1（消歧转义码）+ 2（上报按下、重复和释放）+ 4（上报备用键）。

A reply CSI ? <flags> u with non-zero flags turns Kitty mode on. Flags of zero, or a DA1 reply with no Kitty reply before it, turns on xterm modifyOtherKeys instead with \x1b[>4;2m tui/terminal.ts:267. Every terminal answers DA1, so the fallback needs no start-up timeout.

带非零标志位的回复 CSI ? <flags> u 会打开 Kitty 模式。标志位为零，或 DA1 的回复之前没有 Kitty 回复，则改用 \x1b[>4;2m 打开 xterm 的 modifyOtherKeys tui/terminal.ts:267。每个终端都会回应 DA1，因此这条回退路径不需要启动超时。

StdinBuffer reassembles escape sequences split across reads. A lone ESC counts as the Escape key after 10 ms, or 100 ms when SSH_CONNECTION or SSH_TTY is set, because legacy Alt+key arrives as ESC plus a byte; PI_TUI_ESC_TIMEOUT overrides both tui/terminal.ts:115.

StdinBuffer 会把跨多次读取拆散的转义序列重新拼起来。孤立的 ESC 在 10 ms 后算作 Escape 键；设了 SSH_CONNECTION 或 SSH_TTY 时则是 100 ms，因为旧式的 Alt+键到达时是 ESC 加一个字节；PI_TUI_ESC_TIMEOUT 可以覆盖两者 tui/terminal.ts:115。

Routing. TuiBase.handleTerminalInput passes each input through a fixed ladder; the first step that consumes it ends the walk tui/tui.ts:1044:

路由。TuiBase.handleTerminalInput 让每次输入都走一遍固定的阶梯；第一个消费掉它的步骤就终止这次遍历 tui/tui.ts:1044：

1. terminal colour replies (OSC 10, 11, 4) and colour-scheme reports;

1. 终端颜色回复（OSC 10、11、4）和配色方案报告；

2. input listeners, in order, each able to consume the input or rewrite it;

2. 输入监听器，按顺序排列，每个都可以消费该输入或改写它；

3. the terminal’s cell-size reply;

3. 终端的单元格尺寸回复；

4. Shift+Ctrl+D, the debug key, when a debug handler is set;

4. Shift+Ctrl+D 这个调试键，在设置了调试处理器时；

5. overlay focus repair: a focused overlay that is no longer visible hands focus to the topmost visible one;

5. 覆盖层焦点修复：获得焦点但已不可见的覆盖层，会把焦点交给最顶层的可见覆盖层；

6. Kitty key-release events, dropped unless the focused component sets wantsKeyRelease;

6. Kitty 按键释放事件，除非获得焦点的组件设置了 wantsKeyRelease，否则被丢弃；

7. the focused component’s handle Input, followed by an immediate render.

7. 获得焦点的组件的 handleInput，随后立即渲染一次。

Keybindings. interface Keybindings is a registry that other packages extend by declaration merging; pi-tui declares the tui.* actions tui/keybindings.ts:3. The coding agent merges in its app.* actions CA/src/core/keybindings.ts:69 and reads overrides from keybindings.json in the agent directory CA/src/core/keybindings.ts:380; slash commands and keybindings (p. 197) lists them.

键位绑定。interface Keybindings 是一个注册表，其他包通过声明合并来扩展它；pi-tui 声明了 tui.* 动作 tui/keybindings.ts:3。编码智能体把自己的 app.* 动作合并进去 CA/src/core/keybindings.ts:69，并从 agent 目录下的 keybindings.json 读取覆盖项 CA/src/core/keybindings.ts:380；斜杠命令与键位绑定（p. 197）列出了它们。

## Overlays

## 覆盖层

show Overlay(component, options) pushes a component onto an overlay stack and returns a handle. Overlays are composited into the base lines before the dif, with ANSI-aware column slicing (compositeTuiLine), so an overlay costs only the rows it covers tui/tui.ts:415.

showOverlay(component, options) 把一个组件压入覆盖层栈并返回一个句柄。覆盖层在做差分之前被合成进基础行，列切片是 ANSI 感知的（compositeTuiLine），因此一个覆盖层只花费它覆盖的那几行 tui/tui.ts:415。

<table><tr><td>OverlayOptions 字段</td><td>含义</td></tr><tr><td>width、maxHeight</td><td>列数或行数，或像 &quot;50%&quot; 这样的百分比字符串</td></tr><tr><td>minWidth</td><td>最小列数</td></tr><tr><td>anchor</td><td>center（默认）、top-left、top-right、bottom-left、bottom-right、top-center、bottom-center、left-center、right-center</td></tr><tr><td>offsetX、offsetY</td><td>相对锚点的偏移</td></tr><tr><td>row、col</td><td>改用绝对位置或百分比位置，而不是锚点</td></tr><tr><td>margin</td><td>与终端边缘的距离，一个数字或逐边设置</td></tr><tr><td>visible(termWidth, termHeight)</td><td>只在它返回 true 期间才渲染</td></tr><tr><td>nonCapturing</td><td>显示时不夺取键盘焦点</td></tr></table>

Nine anchors, and a percentage for every size. From OverlayOptions tui/tui.ts:243. The OverlayHandle returned has hide, set Hidden, isHidden, focus, unfocus, isFocused and get Bounds tui/tui.ts:298.

九种锚点，每种尺寸都能用百分比。取自 OverlayOptions tui/tui.ts:243。返回的 OverlayHandle 带有 hide、setHidden、isHidden、focus、unfocus、isFocused 和 getBounds tui/tui.ts:298。

Extensions reach overlays through ctx.ui.custom(factory, { overlay: true, overlay Options, onHandle }), which resolves with the value the component passes to done CA/src/core/extensions/types.ts:214; extensions, loading and the API (p. 113) covers the UI context.

扩展通过 ctx.ui.custom(factory, { overlay: true, overlayOptions, onHandle }) 使用覆盖层，它会以组件传给 done 的值 resolve CA/src/core/extensions/types.ts:214；扩展、加载与 API（p. 113）介绍了这个 UI 上下文。

## Images, colours and native addons

## 图像、颜色与原生插件

pi-tui draws images with the Kitty graphics protocol (a=T,f=100,q=2, base64 in 4,096-character chunks, a random image id in 1–0xffff) or iTerm2’s OSC 1337 tui/terminal-image.ts:217 tui/terminal-image.ts:230. Which one, if any, comes from the environment:

pi-tui 用 Kitty 图形协议（a=T,f=100,q=2，base64 分成 4,096 字符的块，1–0xffff 之间的随机图像 id）或 iTerm2 的 OSC 1337 绘制图像 tui/terminal-image.ts:217 tui/terminal-image.ts:230。用哪一个（如果用的话）取决于环境：

![](images/a7e801b4f24a1c682b7c86211529097c3b073ff6c75151d5802dfc10e8bf40de.jpg)

First match wins, and an unknown terminal gets no images and no hyperlinks. PI_IMAGE_PROTOCOL (kitty or iterm2), PI_TRUE_COLOR and PI_HYPERLINKS (1 or 0) override the result. From tui/terminal-image.ts (detectCapabilitiesFromEnvironment, detectCapabilities).

第一个匹配项胜出，未知终端则既没有图像也没有超链接。PI_IMAGE_PROTOCOL（kitty 或 iterm2）、PI_TRUE_COLOR 和 PI_HYPERLINKS（1 或 0）会覆盖这个结果。取自 tui/terminal-image.ts（detectCapabilitiesFromEnvironment、detectCapabilities）。

Colours come as indexed, sRGB, OKLCH or OKHSL values; parse Color reads oklch(…) and okhsl(…) strings and mix Colors mixes in OKLCH by default tui/colors.ts:121 tui/colors.ts:241. A query for OSC 10, OSC 11 and the 16 palette entries, closed by a DA1 request, reads the terminal’s own colours for the system theme tui/tui.ts:168.

颜色有 indexed、sRGB、OKLCH 或 OKHSL 几种形式；parseColor 读取 oklch(…) 和 okhsl(…) 字符串，mixColors 默认在 OKLCH 里做混色 tui/colors.ts:121 tui/colors.ts:241。对 OSC 10、OSC 11 和 16 个调色板条目发一次查询、再用一次 DA1 请求收尾，就能读出终端自己的颜色，用于系统主题 tui/tui.ts:168。

Native addons are prebuilt N-API binaries committed under tui/native/<platform>/prebuilds/, so installing Pi never runs node-gyp:

原生插件是预先构建好的 N-API 二进制文件，提交在 tui/native/<platform>/prebuilds/ 下，因此安装 Pi 时永远不会跑 node-gyp：

<table><tr><td>平台</td><td>二进制文件</td><td>提供的能力</td></tr><tr><td>darwin arm64、x64</td><td>darwin-platform.node（AppKit）</td><td>剪贴板文本、图像和文件路径；修饰键状态，它让 Apple Terminal 里的 Shift+Enter 变成 \x1b[13;2u</td></tr><tr><td>linux x64、arm64</td><td>linux-platform-x11.node（libxcb）</td><td>X11 剪贴板读取；仅在设置了 DISPLAY 时加载；Wayland 下回退到 wl-paste</td></tr><tr><td>win32 x64、arm64</td><td>win32-platform.node</td><td>控制台输入设置、修饰键状态、剪贴板</td></tr></table>

Six prebuilt binaries, one per platform and architecture. A missing or failing addon degrades to undefined and the caller falls back tui/nativeplatform.ts:28. Rebuild with npm run build:native:<platform> tui/package.json. From tui/native/*/README.md and tui/terminal.ts:11.

六个预构建二进制文件，每个平台与架构一个。插件缺失或加载失败会退化为 undefined，由调用方回退 tui/nativeplatform.ts:28。用 npm run build:native:<platform> 重新构建 tui/package.json。取自 tui/native/*/README.md 和 tui/terminal.ts:11。

Built-in components

内置组件

<table><tr><td>组件</td><td>是什么</td></tr><tr><td>Text、TruncatedText、Box、Spacer</td><td>自动换行的文本、单行截断文本、带内边距的盒子、空行</td></tr><tr><td>Input</td><td>单行输入框</td></tr><tr><td>Editor</td><td>2,472 行：多行编辑、100 条的提示词历史、kill ring、撤销、对 @ 和 # 以及消息开头的 / 的自动补全；超过 10 行或 1,000 个字符的粘贴会折叠成 [paste #N +L lines] 或 [paste #N C chars]</td></tr><tr><td>Markdown</td><td>marked 的 token、按文本和宽度缓存的输出、行内和块级 LaTeX 渲染为 Unicode、可插拔的 highlightCode</td></tr><tr><td>Loader、CancellationLoader</td><td>加载动画，第二个可中止</td></tr><tr><td>SelectList、SettingsList</td><td>键盘驱动的列表；带模糊搜索的设置列表</td></tr><tr><td>Image</td><td>以检测到的协议呈现的一行图像</td></tr><tr><td>VStack、HStack、ScrollView、MouseRegion</td><td>备用屏幕用的布局和鼠标命中区域</td></tr></table>

Utilities do the column arithmetic. visible Width, truncateToWidth, sliceByColumn, wrapTextWithAnsi and fuzzy Filter measure terminal columns, not string length tui/index.ts:184. From tui/index.ts and tui/components/editor.ts (history limit, paste markers, autocomplete triggers).

工具函数负责列宽换算。visibleWidth、truncateToWidth、sliceByColumn、wrapTextWithAnsi 和 fuzzyFilter 测的是终端列数，不是字符串长度 tui/index.ts:184。取自 tui/index.ts 和 tui/components/editor.ts（history limit、paste markers、autocomplete triggers）。

W H A T T H I S M E A N S F O R Y O U

这 对 你 意 味 着 什 么

Measure every line you return with visible Width() and cut it with truncateToWidth(); Pi’s fullscreen mode hides the mistake and regular mode crashes on it.

用 visibleWidth() 度量你返回的每一行，并用 truncateToWidth() 把它截断；Pi 的 fullscreen 模式会掩盖这个错误，而 regular 模式会直接崩溃。

Reapply styles on every line; the renderer resets SGR and OSC 8 at each line end.

每一行都重新应用样式；渲染器会在每行末尾重置 SGR 和 OSC 8。

Cache rendered lines by width and clear the cache in invalidate(); render() runs on every frame.

按宽度缓存渲染好的行，并在 invalidate() 里清空缓存；render() 每一帧都会运行。

Test in both tui Mode values, and set PI_TUI_DEBUG_REDRAW=1 when regular mode keeps redrawing everything.

两种 tuiMode 值都要测；当 regular 模式总是重绘全部内容时，设上 PI_TUI_DEBUG_REDRAW=1。

Sources: tui/README.md; tui/package.json (dependencies, test, build:native:*). tui/tui.ts (Component, Focusable, CURSOR_MARKER, OverlayOptions, OverlayHandle, Container, SEGMENT_RESET, compositeTuiLine, TUI, TuiBase: MIN_RENDER_INTERVAL_MS, requestRender, scheduleRender, handleTerminalInput, applyLineResets, TERMINAL_COLOR_QUERY); tui/tui-main-screen.ts (BoundedTerminalWriter, doRender); tui/tui-alt-screen.ts (ENTER_ALT_SCREEN, mouse modes, doRender, scrollToPrompt, OSC 52 copy). tui/terminal.ts (Kitty negotiation, modifyOtherKeys, resolveEscapeTimeoutMs); tui/keybindings.ts; tui/terminal-image.ts (detectCapabilitiesFromEnvironment, Kitty and iTerm2 encoders); tui/colors.ts; tui/native-platform.ts; tui/native/*/README.md; tui/components/editor.ts; tui/components/markdown.ts. CA/src/core/settings-manager.ts (tuiMode, fullscreenExitOutput); CA/src/modes/interactive/tui-renderer.ts; CA/src/core/keybindings.ts; CA/src/core/extensions/types.ts (ExtensionUIContext.custom); research/capture/tui-frames.mjs; research/out/tui-frames.txt

来源：tui/README.md；tui/package.json（dependencies、test、build:native:*）。tui/tui.ts（Component、Focusable、CURSOR_MARKER、OverlayOptions、OverlayHandle、Container、SEGMENT_RESET、compositeTuiLine、TUI、TuiBase：MIN_RENDER_INTERVAL_MS、requestRender、scheduleRender、handleTerminalInput、applyLineResets、TERMINAL_COLOR_QUERY）；tui/tui-main-screen.ts（BoundedTerminalWriter、doRender）；tui/tui-alt-screen.ts（ENTER_ALT_SCREEN、mouse modes、doRender、scrollToPrompt、OSC 52 copy）。tui/terminal.ts（Kitty negotiation、modifyOtherKeys、resolveEscapeTimeoutMs）；tui/keybindings.ts；tui/terminal-image.ts（detectCapabilitiesFromEnvironment、Kitty 与 iTerm2 编码器）；tui/colors.ts；tui/native-platform.ts；tui/native/*/README.md；tui/components/editor.ts；tui/components/markdown.ts。CA/src/core/settings-manager.ts（tuiMode、fullscreenExitOutput）；CA/src/modes/interactive/tui-renderer.ts；CA/src/core/keybindings.ts；CA/src/core/extensions/types.ts（ExtensionUIContext.custom）；research/capture/tui-frames.mjs；research/out/tui-frames.txt