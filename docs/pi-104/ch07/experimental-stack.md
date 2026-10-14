---
title: "实验性技术栈"
originalPage: 166
---

<div class="section-kicker">7.1 / EXPERIMENTAL & OPERATIONS</div>

# 实验性技术栈

---

1\.0\.4 版中的六个软件包勾勒出这样一种 Pi：能够在崩溃后继续工作、在其他机器上运行工具，并通过一个套接字服务多个客户端。稳定版 `pi` 命令没有使用其中任何一个软件包，npm 用户也无法访问将它们连接起来的代码。



这些软件包分别是 `pi-durable`、`pi-env`、`chord`、`pi-protocol`、`pi-server` 和 `pi-client`。它们合计有 32,038 行非空源代码，超过编码智能体自身代码规模的三分之一，见 `research/out/stats.txt` 的“软件包行数”一节。本节先展示这些部分如何组成一个进程拓扑，再逐一介绍各软件包：它们存储什么、通过线路传输什么，以及施加哪些限制。“一页看懂 monorepo”（原书第11页）介绍了构建过程如何将这些代码排除在 npm 软件包之外；本节从那里接着讲起，也就是在源代码检出目录中设置 `PI_EXPERIMENTAL=1`。

## 如何使用



实验性入口点位于 `CA/src/experimental/cli.ts`。它调用 `runExperimentalCommand(args)`，如果返回 `false`，就继续执行常规的 `main()`，见 `CA/src/experimental/cli.ts:8`。除非 `PI_EXPERIMENTAL` 恰好为 `"1"`，且第一个参数是 `server` 或 `client`，否则该函数会返回 `false`，见 `CA/src/experimental/commands.ts:86`。其文档注释明确了边界：“仅供开发使用的命令分派。已发布的入口点不得导入此模块。”



三个事实使这些代码无法进入普通安装。`tsconfig.build.json` 将 `src/client`、`src/experimental` 和 `src/cli/experimental` 排除在编译之外，见 `CA/tsconfig.build.json:19`。`pi-client`、`pi-protocol` 和 `pi-server` 只是编码智能体的 `devDependencies`，见 `CA/package.json:78`。而且，如果发布的软件包中包含 `dist/experimental`，或者上述三个软件包中的任何一个能够被解析到，消费者冒烟测试就会判定该版本发布失败，见 `scripts/coding-agent-consumer.mjs:82`。在源代码检出目录中，`./pi-test.sh` 会通过 TypeScript 解析器运行源代码入口点，见 `pi-test.sh`：



<strong>从源码启动服务器并连接客户端</strong> · 来源：`CA/src/experimental/services/README.md`

```bash
PI_EXPERIMENTAL=1 ./pi-test.sh server
PI_EXPERIMENTAL=1 ./pi-test.sh client
```



上述命令复制自服务 README。`pi server` 接受 `--server-id`、`--session-dir`、`--provider`、`--model`、可重复使用的 `-e`，以及 `--auth-token` 或 `--auth-token-file`；`pi client` 还增加了 `--connect`、`--session-id`、`-c/--continue` 和 `-r/--resume`，见 `CA/src/cli/experimental/commands/server.ts`、`CA/src/cli/experimental/commands/client.ts`。



`CA/src/experimental/` 下另有两个较小的程序，不借助服务器就能使用 `pi-durable`。`durable/main.ts` 是带有自身 TUI 的单进程持久化编码智能体；`vacation/main.ts` 使用同一套运行框架，只是用度假规划提示替换了编码工具，见 `CA/src/experimental/durable/README.md`、`CA/src/experimental/vacation/README.md`。两者都不检查 `PI_EXPERIMENTAL`。

## 一个进程拓扑



<BookFigure id="7.1" />

> 服务器负责路由；只有会话工作进程运行智能体。一个 `pi server` 进程通过私有 Unix 套接字接受客户端连接，并将会话调用交给工作进程，后者拥有持久化 `Harness` 及其 SQLite 文件。斜线填充的方框表示默认运行时关闭或未使用的部分。进程角色来自 `CA/src/experimental/process.ts:8`；此图为示意图。
> 
> 



三种角色是 `coordinator`、`server` 和 `session-worker`，见 `CA/src/experimental/process.ts:8`。服务器将每个会话放在各自独立的目录中：`meta.json` 保存 id、创建时间和工作目录，`session.sqlite` 是 `pi-durable` 的存储。“会话工作进程锁定目录、打开存储，并一直拥有它，直到该进程退出服务”，见 `CA/src/experimental/services/README.md`。会话目录默认为 `<agent dir>/experimental/sessions`，见 `CA/src/experimental/server.ts:69`。套接字目录默认为 `PI_SERVER_DIR` 或 `~/.pi/server`，见 `CA/src/experimental/server.ts:55`。服务器以 `0700` 模式创建它，并拒绝使用属于其他用户的目录，见 `CA/src/experimental/server.ts:58`。



协调器连接后，服务器还会启动一个 `RadiusRelayHost`，见 `CA/src/experimental/server.ts:609`。当它从 `--auth-token`、`--auth-token-file` 或已保存的 `/login radius` 凭据中找到令牌时，会连接 Radius 网关上的 `wss://…/v1/session-relays/<serverId>/connect`，见 `CA/src/experimental/radius-relay.ts:619`；如果设置了 `PI_OFFLINE`，或不存在令牌，则只在本地运行，见 `CA/src/experimental/radius-auth.ts:36`。客户端通过 `--connect radius://<serverId>` 连接这样的服务器，见 `CA/src/cli/experimental/command-options.ts:47`。

## pi\-durable：先提交，再展示



README 开篇就给出了约定：“对话、模型轮次、工具调用以及你自己的状态，都会在任何内容展示之前提交到存储。如果进程在轮次中途终止，重新打开存储就能从停止之处继续工作”，见 `durable/README.md`。规范性文档是 `durable/docs/spec.md`，共 4,692 行，标题为“Pico5 规范”。它列出了八条必须满足的不变量；前三条是：“一次 Session 提交对所有记录和文档写入具有原子性”“文档更新只会在存储提交成功之后发布”，以及“所有可见进展都是持久化的，不存在易失性发布路径”，见 `durable/docs/spec.md` 第1节。



一个 `Session` 拥有一条变更序列。`Storage.commit(writes, context)` 原子性地持久化一批写入，并返回解析为 `Seq` 的结果，见 `durable/src/types.ts:997`。这条序列包含五种记录：对话、不可变条目、任务、提交项和文档。内置条目类型是 `pi.user`、`pi.assistant`、`pi.tool-result`、`pi.system`、`pi.reset` 和 `pi.compaction`，见 `durable/src/entries.ts`。内置文档是 `pi.agent`、`pi.provider`、`pi.live`、`pi.inbox` 和 `pi.usage`。



恢复并不是重放事件日志；“Session 内核语义事件日志”被明确列为非目标，见 `durable/docs/spec.md` 第13节。每个任务从其最后一次已提交的检查点恢复：



<strong>任务的五种持久化状态</strong> · 来源：`durable/src/types.ts`

```ts
export type TaskState<S, R> =
    | {
        /** 可以被调度。 */
        readonly status: "pending";
        /** 执行恢复时所依据的完整持久化状态。 */
        readonly checkpoint: S;
        readonly outcome?: never;
    }
    | {
        /** 由一次内存中的任务调用预留。 */
        readonly status: "running";
        ...
    }
    | {
        /** 暂停且不保留调用，直到 'on' 中每个任务都进入终态；随后从 'checkpoint' 恢复。 */
        readonly status: "waiting";
        readonly checkpoint: S;
        readonly on: readonly TaskId[];
        readonly policy: JoinPolicy;
        readonly outcome?: never;
    }
    | {
        /** 结果已确定；下属普通归属工作全部不再活动后进入终态。不再运行代码。 */
        readonly status: "completing";
        ...
    }
    | {
        /** 永久确定的持久化结果回执。 */
        readonly status: "terminal";
        ...
    };
```

> 以上摘自第486行。`running` 的主体重复了 `pending` 的字段；`completing` 和 `terminal` 携带 `outcome: TaskOutcome<R>`，不带 `checkpoint`。省略处以 `…` 标记。`JoinPolicy` 是 `"failFast" | "allSettled"`，见 `durable/src/types.ts:267`。
> 
> 



`TaskOutcome` 可以是 `completed`、`failed`、`aborted`、`orphaned` 或 `faulted`，见 `durable/src/types.ts:449`。每个阶段处理器“必须通过 `runtime.commit()` 提交变更后的检查点或终态结果；若返回时没有产生持久化进展，就会使任务进入故障状态”，见 `durable/src/types.ts:148`。中止从下往上执行：“只有当一个任务所拥有的普通工作不再活动时，才会开始该任务的中止调用”，见 `durable/docs/spec.md` 第5节。



|<strong>任务</strong>|<strong>阶段</strong>|<strong>提交内容</strong>|
|---|---|---|
|`pi.generation`，`durable/src/harness/generation.ts:115`|`prepare → request → retry · poll · tools`，另加 `abort`|只有当计划使用的提示或工具不同于对话记录重放出的内容时，才提交 `pi.system` 条目，见 `durable/src/harness/prompt.ts:66`；部分输出；`pi.assistant` 条目|
|`pi.tool`，`durable/src/harness/tool.ts:50`|`call`、`execute`（仅用于恢复），另加 `abort`|运行前提交意图 `{ phase: "execute", arguments, replay }`，然后提交 `pi.tool-result`|
|`pi.compaction`，`durable/src/harness/compaction.ts:103`|`select → summarize → retry`，另加 `abort`|带有摘要的 `pi.compaction` 条目|



三个内置任务驱动一个轮次。默认值为：压缩的 `reserveTokens` 为 16,384，`keepRecentTokens` 为 20,000，`backgroundTokens` 为 32,768；重试 3 次，基础延迟为 2,000 ms；部分文本和工具输出最多每 100 ms 提交一次，见 `durable/src/harness/agent.ts:19`。



工具任务是持久性与副作用交汇的地方。`call` 在一个处理器中完成以下步骤：解析工具、验证、运行 `beforeTool`、提交意图、执行、运行 `afterTool`，并追加结果。只有恢复过程会进入 `execute`：



<BookFigure id="7.2" />

> 只有两份记录都认定重复执行安全时，工具才会运行两次。崩溃前存储的意图和崩溃后注册的工具都必须声明 `replay: "safe"`；`replay` 默认为 `"unsafe"`，见 `durable/src/harness/types.ts:215`。第4行记录的是失败结果，因此该调用拥有的对话会被中止。来源：`ToolTask.execute`，`durable/src/harness/tool.ts:94`。
> 
> 



内置 `CodingTools`（`read`、`write`、`edit`、`bash` 以及 `durable/src/tools/` 下的其他工具）没有设置 `replay`，因此调用中途发生崩溃时，它们一律会被中断。钩子也按相同方式处理：它们“脱离变更序列，按扩展顺序运行；如果在使用其结果的提交完成之前发生崩溃，钩子可能会重新运行”，见 `durable/docs/spec.md` 第7\.2节。必须只作出一次决定的钩子，可以通过 `memo(name, candidate)` 记录决定；它“是一次受控提交”，见 `durable/docs/spec.md` 第5节。钩子和发起询问的任务共享同一组备忘记录，见 `durable/src/harness/types.ts:604`。生成任务的钩子包括 `beforeRequest`、`afterResponse`、`onYield` 和 `afterTools`；工具任务的钩子包括 `beforeTool` 和 `afterTool`；压缩任务的钩子是 `beforeCompact`。



提交项通过请求 id 实现幂等：使用相同 `requestId` 再次调用 `submit()` 时，会返回已有提交项，见 `durable/src/harness/submissions.ts:155`。



|<strong>后端</strong>|<strong>打开方式</strong>|<strong>持久性</strong>|
|---|---|---|
|内存|`new MemoryStorage()`|不持久化任何内容|
|SQLite|`openNodeSqliteStorage(file)`|`PRAGMA journal_mode = WAL`、`synchronous = NORMAL`，见 `durable/src/storage/sqlite/node.ts:190`：“提交可以经受进程崩溃；断电或宿主机故障时，最新的提交可能丢失”|
|JSONL|`openNodeJsonlStorage(directory, context)`|仅追加文件；`{ fsync: true }` 会在每个提交标记之前刷盘，默认关闭，见 `durable/src/storage/jsonl/storage.ts:256`|



三种后端，每个都只有一个所有者。“同一时刻只有一个进程拥有一份存储；不存在跨进程锁”，见 `durable/README.md` 的“存储”一节。实验性服务器在每个会话工作进程中使用 `proper-lockfile` 提供这把锁。



工具通过 `ExecutionEnv` 访问机器，它由 `FileSystem` 加 `Shell` 组成，见 `durable/src/env/index.ts:324`。其操作返回 `Result<T, E>`，即 `{ ok: true, value } | { ok: false, error }`，而不是抛出异常，见 `durable/src/env/index.ts:4`。本地实现是 `NodeExecutionEnv`，其 id 为 `"node:local"`，见 `durable/src/env/node.ts:605`。

## pi\-env：在另一台机器上运行工具



<strong>`pi-env` 是第二种 `ExecutionEnv`：“智能体的工具在另一台机器上运行，通常通过 SSH 连接，而 Durable 工作进程、存储和凭据留在本地”</strong>，见 `env/README.md`。除它自己的测试外，仓库内没有任何地方导入它。远程部分是 `env/daemon/` 中的 Rust 守护进程，13 个 `.rs` 文件共 4,027 行。README 说，该软件包在 `bin/` 中附带了适用于 x86\-64 和 arm64 的 Linux、macOS、Android（Termux）及 Windows 预构建版本；`bin/` 是构建产物，不包含在源代码检出目录中。



客户端使用 `serve --token <hex>` 启动守护进程，见 `env/src/connection.ts:268`，并丢弃 stdout 中 `PI-ENV <token>` 这一行之前的所有内容，从而避免 shell 启动时的杂音破坏数据流，见 `env/src/connection.ts:329`。此后，stdout 只承载帧：



<BookFigure id="7.3" />

> JSON 说明要做什么；原始字节承载文件内容和输出。如果帧短于 9 字节或长于 16 MiB，连接会以“Corrupt frame from pi\-env”（来自 pi\-env 的损坏帧）错误结束，见 `env/src/connection.ts:345`。布局来自 `env/docs/protocol.md` 的“帧”一节；此图为示意图，不按比例绘制。
> 
> 



双方每 5 s 发送一次 `ping`。“如果 30 秒内没有收到任何字节，或 stdin 结束，守护进程就会终止它启动的每个进程组并退出”，见 `env/docs/protocol.md` 的“存活性”一节。客户端在同样的 30 s 静默后放弃连接，见 `env/src/connection.ts:15`。



`sshArguments()` 构建 ssh 命令行，见 `env/src/ssh.ts:77`。它传入 `-T -a -x`，并设置 `BatchMode=yes`、`ClearAllForwardings=yes`、`ForwardAgent=no`、`ForwardX11=no`、`ControlMaster=no`、`ControlPath=none`、`RemoteCommand=none`、`PermitLocalCommand=no`、`SendEnv=-*`、`StrictHostKeyChecking=yes`、调用方提供的 `UserKnownHostsFile`、`GlobalKnownHostsFile=none`，以及固定的 `HostKeyAlias`。主机密钥通过 `scanHostKey()` 和 `acceptHostKey()` 在带外接受一次。



远程守护进程文件的名称为 `pi-env-<first 32 hex digits of its SHA-256>`，即以其 SHA\-256 的前 32 个十六进制数字作为后缀，见 `env/src/ssh.ts:371`。`deployDaemon()` 在每次启动前计算远程文件的哈希，只有文件缺失或不同时才上传；如果上传文件的哈希不匹配，会删除该文件并报出“pi\-env upload is corrupt”（pi\-env 上传内容已损坏），见 `env/src/ssh.ts:396`。

## chord：组合运行时



尽管名为 chord，它与组合键并无关系。“Chord 是面向由插件／扩展组装而成的系统的应用组合运行时”，并且“它不是 Pi 软件包：它不依赖其他任何 Pi 工作区软件包”，见 `chord/README.md`。其组成部分包括：

- Facet：同步设置单元。一个 facet 会调用 `env.use()`、`env.observe()`、`env.provide()` 和 `env.provideMany()`，见 `chord/src/types.ts:281`；宿主根据这些调用构建依赖图，先激活提供方再激活使用方，并按相反顺序释放它们。

- 服务：模式为 `"singleton"` 或 `"keyed"` 的带类型令牌，见 `chord/src/types.ts:123`；可以仅供进程本地使用，也可以发布给远程使用方。参数、结果、快照和更新都必须是严格 JSON。

- 复制状态：`change(context, draft => …)` 发布一个修订版本，见 `chord/src/services/state.ts:202`。副本接收增量操作。

- 控制服务：`$chord.service`，成员包括 `catalogue`、`subscribe` 和 `unsubscribe`，见 `chord/src/services/wire.ts:40`。订阅方最多缓存 100 次更新；第101次更新会用一个重置快照替换缓冲区，见 `chord/src/services/provider.ts:453`。

- 上下文：“类似 Go 的上下文系统，用于取消和调用作用域内的应用值”，见 `chord/README.md`；包括 `BACKGROUND_CONTEXT`、`TODO_CONTEXT`、`withAbortSignal`、`withCancel` 和 `withContextValue`，见 `chord/src/context/index.ts:55`。

    

<strong>七种增量操作</strong> · 来源：`chord/src/delta/index.ts`

```ts
export type Op =
    | readonly ["r", JsonValue]
    | readonly ["s", NonEmptyPath, JsonValue]
    | readonly ["d", NonEmptyPath]
    | readonly ["a", NonEmptyPath, string]
    | readonly ["t", NonEmptyPath, number]
    | readonly ["p", Path, number, number, JsonValue[]]
    /** 原地重排数组：`new[i] = old[permutation[i]]`。 */
    | readonly ["m", Path, number[]];
```

> 以上是第32行起的完整内容。依次表示：替换根、设置、删除、追加字符串、截去字符串前端、数组 splice、置换。字符串追加使流式回答能够以很低的成本复制。
> 
> 



Node 打包器使用 esbuild 将每个 facet 入口构建为一个名为 `facet-<12 hex>-[hash].cjs` 的 CommonJS 文件，并记录一个 `sha256-…` 完整性值，见 `chord/src/node/bundle.ts:88`。加载器使用 `node:vm` 编译源码前会重新计算哈希；如果不匹配，就以“Facet bundle integrity check failed”（Facet 包完整性检查失败）报错，见 `chord/src/node/bundle-loader.ts:231`。`FacetHost.reload()` 在运行时替换 facet，见 `chord/src/facets/host.ts:423`；服务器的 `/reload` 就使用它。

## pi\-protocol、pi\-server、pi\-client



`PROTOCOL_VERSION` 为 `8`，见 `protocol/src/protocol.ts:5`；README 说得很直接：“该协议是实验性的，不保证兼容性”，见 `protocol/README.md:41`。一帧包含一个 4 字节无符号大端长度，以及一个由该软件包自身编解码器处理的确定长度 CBOR 项。默认限制为：每帧 16 MiB，见 `protocol/src/framing.ts:6`；数组元素或映射条目 1,000,000 个；嵌套层级 64 层，见 `protocol/README.md:41`、`protocol/src/cbor/options.ts:8`。



<BookFigure id="7.4" />

> 每条连接的第一帧都是 25 字节。它是一个包含两个文本键的 CBOR 映射，协议版本用一个单字节整数表示。服务器用相同的映射加上 `serverId` 回应；当 `serverId` 为 UUID 时，响应为 72 字节。字节数据来自固定版本的真实构建，由 `research/capture/experimental-stack-frames.mjs` 编码到 `research/out/experimental-stack-frames.txt`；原图按比例绘制。
> 
> 



封装消息是设置了 `additionalProperties: false` 的 TypeBox 对象，因此额外字段会导致验证失败；采集记录显示，带有一个额外键的 `hello` 会触发“Invalid client protocol message”（无效的客户端协议消息），见 `research/out/experimental-stack-frames.txt`。



|<strong>方向</strong>|<strong>类型</strong>|<strong>字段</strong>|
|---|---|---|
|客户端 → 服务器|`hello`|`version`；必须是第一帧|
|客户端 → 服务器|`request`|`id`、`target`、`call`|
|客户端 → 服务器|`cancel`|`id`、`target`|
|服务器 → 客户端|`hello`|`version`（字面量 `8`）、`serverId`|
|服务器 → 客户端|`hello_error`|`error {code, message}`|
|服务器 → 客户端|`response`|`id, ok: true, result?` 或 `ok: false, error`|
|服务器 → 客户端|`service_update`|`subscriptionId`、`update`|
|服务器 → 客户端|`attachment`|一个会话目标，或 `null`|

> 共有八种封装消息类型，其载荷是不透明的。`target` 是 `{serverId}` 或 `{serverId, sessionId, attachmentId}`，且 `serverId` 必须是小写 UUIDv4。`call` 和 `result` 是 Chord 值，`pi-protocol` 只检查它们是否为严格 JSON。来源：`protocol/src/protocol.ts`。
> 
> 



`pi-server` 只监听 Unix 域套接字；该软件包没有 HTTP 或 WebSocket 监听器。套接字路径为 `<dir>/<serverId>.sock`，见 `server/src/transports/unix/address.ts:8`，权限模式为 `0600`，见 `server/src/transports/unix/listener.ts:11`。如果客户端未能在 5 s 内完成握手，连接就会以“Handshake timeout”（握手超时）断开，见 `server/src/server.ts:42`。错误码包括 `wrong_server`、`session_not_found`、`session_ambiguous`、`session_not_attached` 和 `server_draining`，见 `server/src/errors.ts:5`。服务器并未包装 `AgentSession`：会话工作进程从 `pi-durable` 导入 `Harness`，并打开 `openNodeSqliteStorage`，见 `CA/src/experimental/session-worker.ts:15`。



`pi-client` 导出 `Client`、`createClientServiceTransport`（Chord 适配器）和三个错误类，见 `client/src/index.ts`；`discoverUnixServers()` 扫描服务器目录，见 `client/src/unix.ts:37`。它“从不自动重连或重放请求”；应用需要调用 `reconnect()`、重新连接会话，并且只重复自己确定安全的操作，见 `client/README.md:34`。



> 这对你意味着什么：
> 
> - 不要围绕 `pi server` 规划集成：npm 和二进制发行版都不包含它，协议 8 也不承诺兼容性。
> 
> - 如果现在就需要能够经受崩溃的轮次，可以直接嵌入 `pi-durable`；只有能安全运行两次的工具，才应声明 `replay: "safe"`。
> 
> - 每份持久化存储必须恰好由一个进程拥有；这个软件包不会阻止第二个进程访问它。
> 
> - 对 `pi-env`，先在带外接受一次主机密钥，之后让采用内容寻址的守护进程自行重新部署。
> 
> 



本系列的另一本书《Pi Durable 技术手册》基于 `pi@5b6c792` 和 npm `1.0.3` 编写，详细介绍 `pi-durable`：提交、任务、文档、观测和恢复。本节只深入到理解编码智能体所需的程度。



> 来源：`CA/src/experimental/cli.ts`；`CA/src/experimental/commands.ts`（`runExperimentalCommand`）；`CA/src/cli/experimental/commands/server.ts`、`client.ts`、`command-options.ts`（`parseTransportAddress`）；`CA/src/experimental/server.ts`（`resolveServerDirectory`、`ensurePrivateServerDirectory`、`resolveSessionDirectory`、`startForegroundServer`）；`CA/src/experimental/process.ts`；`CA/src/experimental/radius-auth.ts`、`radius-relay.ts`；`CA/src/experimental/session-worker.ts`；`CA/src/experimental/services/README.md`、`durable/README.md`、`vacation/README.md`；`CA/tsconfig.build.json`；`CA/package.json`；`scripts/coding-agent-consumer.mjs`；`pi-test.sh`；`durable/README.md`；`durable/docs/spec.md` 第1、5、7\.2、13节；`durable/src/types.ts`（`TaskState`、`TaskOutcome`、`PhaseHandler`、`Storage`）；`durable/src/entries.ts`；`durable/src/harness/{generation,tool,compaction,agent,prompt,submissions,types}.ts`；`durable/src/storage/sqlite/node.ts`、`jsonl/storage.ts`；`durable/src/env/index.ts`、`node.ts`；`env/README.md`；`env/docs/protocol.md`；`env/src/connection.ts`、`ssh.ts`（`sshArguments`、`deployDaemon`）；`chord/README.md`；`chord/src/types.ts`；`chord/src/delta/index.ts`；`chord/src/services/{wire,provider,state}.ts`；`chord/src/node/bundle.ts`、`bundle-loader.ts`；`chord/src/facets/host.ts`；`chord/src/context/index.ts`；`protocol/README.md`；`protocol/src/{protocol,framing}.ts`、`cbor/options.ts`；`server/src/{server,errors}.ts`、`transports/unix/{address,listener}.ts`；`client/README.md`；`client/src/index.ts`、`unix.ts`；`research/capture/experimental-stack-frames.mjs`；`research/out/experimental-stack-frames.txt`；`research/out/stats.txt`。
> 
>
