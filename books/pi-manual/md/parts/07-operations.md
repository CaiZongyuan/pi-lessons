The packages behind PI_EXPERIMENTAL, the trust boundaries,

PI_EXPERIMENTAL 背后的那些包、信任边界，

and what Pi reports about itself.

以及 Pi 关于自身的自我报告。

## 7.1 The experimental stack

## 7.1 实验特性栈

Six packages at 1.0.4 sketch a Pi that survives crashes, runs tools on other machines and serves many clientsfrom one socket. The stable \`pi\` command uses none ofthem, and npm users cannot reach the code that wires them together.

1.0.4 版的六个包勾勒出一种 Pi：它能在崩溃后存活、能在其他机器上运行工具、并从一个套接字服务多个客户端。稳定的 \`pi\` 命令一个都不用，npm 用户也接触不到把它们连起来的那部分代码。

The packages are pi-durable, pi-env, chord, pi-protocol, pi-server and pi-client. Together they hold 32,038 nonblank source lines, more than a third of the size of the coding agent itself research/out/stats.txt §package-lines. This section shows how the pieces fit into one process topology, then takes each package in turn: what it stores, what it puts on the wire, and the limits it enforces. the monorepo in one page (p. 11) shows how the build keeps this code out of the npm package; this section starts where that one stops, at PI_EXPERIMENTAL=1 in a source checkout.

这些包是 pi-durable、pi-env、chord、pi-protocol、pi-server 和 pi-client。合计 32,038 行非空源码，超过编码智能体自身规模的三分之一 research/out/stats.txt §package-lines。本节先说明这些部件如何拼成一个进程拓扑，然后逐个介绍每个包：它存什么、它往线上放什么、它强制哪些限制。the monorepo in one page (p. 11) 讲了构建如何把这些代码挡在 npm 包之外；本节从那一本停下的地方接着讲——在源码检出里设置 PI_EXPERIMENTAL=1 之后的事情。

## How to reach it

## 如何进入

The experimental entry point is CA/src/experimental/cli.ts. It calls runExperimentalCommand(args) and falls through to the ordinary main() when that returns false CA/src/experimental/cli.ts:8. The function returns false unless PI_EXPERIMENTAL is exactly "1" and the first argument is server or client CA/src/experimental/commands.ts:86. Its doc comment states the boundary: “Development-only command dispatch. Published entrypoints must not import this module.”

实验特性的入口点是 CA/src/experimental/cli.ts。它调用 runExperimentalCommand(args)，当该函数返回 false 时穿透到普通的 main() CA/src/experimental/cli.ts:8。除非 PI_EXPERIMENTAL 恰好为 "1" 且第一个参数是 server 或 client，否则该函数返回 false CA/src/experimental/commands.ts:86。它的文档注释划出了边界：“Development-only command dispatch. Published entrypoints must not import this module.”

Three facts keep the code out of a normal install. tsconfig.build.json excludes src/client, src/experimental and src/cli/experimental from compilation CA/tsconfig.build.json:19. pi-client, pi-protocol and pi-server are only dev Dependencies of the coding agent CA/package.json:78. And the consumer smoke test fails a release if the published package contains dist/experimental or if any of those three packages resolves scripts/coding-agent-consumer.mjs:82. From a checkout, ./pi-test.sh runs the source entry point under a TypeScript resolver pi-test.sh:

有三件事让这些代码进不了普通安装。tsconfig.build.json 把 src/client、src/experimental 和 src/cli/experimental 排除在编译之外 CA/tsconfig.build.json:19。pi-client、pi-protocol 和 pi-server 只是编码智能体的 devDependencies CA/package.json:78。而消费者冒烟测试会在两种情况下让一次发布失败：发布的包里含有 dist/experimental，或者上述三个包中的任何一个仍能被解析到 scripts/coding-agent-consumer.mjs:82。在源码检出中，./pi-test.sh 在 TypeScript 解析器下运行源码入口点 pi-test.sh：

start a server and attach a client from source CA/src/experimental/services/README.md

从源码启动一个服务器并接入一个客户端 CA/src/experimental/services/README.md

B A S H

B A S H

PI_EXPERIMENTAL=1 ./pi-test.sh server PI_EXPERIMENTAL=1 ./pi-test.sh client

PI_EXPERIMENTAL=1 ./pi-test.sh server PI_EXPERIMENTAL=1 ./pi-test.sh client

Copied from the services README. pi server takes --server-id, --session-dir, --provider, --model, repeatable -e and --auth-token or --authtoken-file; pi client adds --connect, --session-id, -c/--continue and -r/--resume CA/src/cli/experimental/commands/server.ts CA/src/cli/experimental/commands/client.ts.

抄自 services 的 README。pi server 接受 --server-id、--session-dir、--provider、--model、可重复的 -e，以及 --auth-token 或 --authtoken-file；pi client 另有 --connect、--session-id、-c/--continue 和 -r/--resume CA/src/cli/experimental/commands/server.ts CA/src/cli/experimental/commands/client.ts。

Two smaller programs under CA/src/experimental/ use pi-durable without the server. durable/main.ts is a oneprocess durable coding agent with its own TUI, and vacation/main.ts is the same harness with a vacation-planner prompt in place of the coding tools CA/src/experimental/durable/README.md CA/src/experimental/vacation/README.md. Neither checks PI_EXPERIMENTAL.

CA/src/experimental/ 下还有两个小一点的程序，在没有服务器的情况下使用 pi-durable。durable/main.ts 是一个单进程的持久化编码智能体，自带 TUI；vacation/main.ts 是同一套骨架，只是把编码工具换成了度假规划提示词 CA/src/experimental/durable/README.md CA/src/experimental/vacation/README.md。两者都不检查 PI_EXPERIMENTAL。

## One process topology

## 单进程拓扑

![](images/ce6a526c84f25ac800d34f38b61688360349cc66257d68966f842b9f0c379c78.jpg)

The server routes; only the session worker runs the agent. One pi server process accepts clients on a private Unix socket and hands session calls to a worke process, which owns the durable Harness and its SQLite file. Hatched boxes are parts that are of or unused in a default run. Process roles from CA/src/experimental/process.ts:8; schematic.

服务器只负责路由；只有 session worker 才运行智能体。一个 pi server 进程在私有 Unix 套接字上接受客户端，把会话调用交给一个 worker 进程，由它拥有持久化的 Harness 及其 SQLite 文件。带剖面线的方框是默认运行中未启用或未使用的部分。进程角色来自 CA/src/experimental/process.ts:8；示意图。

The three roles are coordinator, server and session-worker CA/src/experimental/process.ts:8. The server keeps each session in its own directory: meta.json holds the id, creation time and working directory, and session.sqlite is the pidurable storage. “The Session worker locks the directory, opens the storage, and owns it until it retires”

三个角色分别是 coordinator、server 和 session-worker CA/src/experimental/process.ts:8。服务器让每个会话各自独占一个目录：meta.json 保存 id、创建时间和工作目录，session.sqlite 则是持久化存储。“Session worker 锁住这个目录、打开存储，并在自己退役之前一直拥有它”

CA/src/experimental/services/README.md. Session directories default to <agent dir>/experimental/sessions CA/src/experimental/server.ts:69. The socket directory defaults to PI_SERVER_DIR or \~/.pi/server CA/src/experimental/server.ts:55. The server creates it with mode 0700 and refuses a directory owned by another user CA/src/experimental/server.ts:58.

CA/src/experimental/services/README.md。会话目录默认为 <agent dir>/experimental/sessions CA/src/experimental/server.ts:69。套接字目录默认为 PI_SERVER_DIR 或 \~/.pi/server CA/src/experimental/server.ts:55。服务器以 0700 模式创建它，并拒绝使用属于其他用户的目录 CA/src/experimental/server.ts:58。

The server also starts a RadiusRelayHost after the coordinator connects CA/src/experimental/server.ts:609. It dials wss://…/v1/session-relays/<serverId>/connect on the Radius gateway CA/src/experimental/radius-relay.ts:619 when it finds a token from --auth-token, --auth-token-file or a stored /login radius credential, and it stays local when PI_OFFLINE is set or no token exists CA/src/experimental/radius-auth.ts:36. A client reaches such a server with -- connect radius://<serverId> CA/src/cli/experimental/command-options.ts:47.

协调器连上之后，服务器还会启动一个 RadiusRelayHost CA/src/experimental/server.ts:609。当它从 --auth-token、--auth-token-file 或已保存的 /login radius 凭据中找到 token 时，就拨向 Radius 网关的 wss://…/v1/session-relays/<serverId>/connect CA/src/experimental/radius-relay.ts:619；而当 PI_OFFLINE 被设置或不存在 token 时，它保持在本地 CA/src/experimental/radius-auth.ts:36。客户端用 -- connect radius://<serverId> 访问这类服务器 CA/src/cli/experimental/command-options.ts:47。

#### pi-durable: commit first, show second

#### pi-durable：先提交，后展示

The README opens with the contract: “Conversations, model turns, tool calls, and your own state are committed to storage before anything is shown. If the process dies mid-turn, reopening the storage picks the work up where it stopped” durable/README.md. The normative text is durable/docs/spec.md, 4,692 lines, titled “Pico5 specification”. It lists eight required invariants; the first three are “One Session commit is atomic across all record and document writes”, “A document update is published only after its storage commit succeeds” and “All visible progress is durable. There is no volatile publication path” durable/docs/spec.md §1.

README 开门见山给出契约：“会话、模型轮次、工具调用以及你自己的状态，在任何内容被展示之前就已提交到存储。如果进程在轮次中途死掉，重新打开存储会从它停下的地方接着干活” durable/README.md。规范正文是 durable/docs/spec.md，4,692 行，标题为“Pico5 specification”。它列出八条必需的不变式；前三条是“一个 Session 的提交在所有记录与文档写入之间是原子的”“一次文档更新只有在它的存储提交成功之后才被发布”“所有可见进度都是持久的。不存在易失的发布路径” durable/docs/spec.md §1。

A Session owns one mutation line. Storage.commit(writes, context) persists one batch atomically and resolves to a Seq durable/src/types.ts:997. Five record kinds sit on that line: conversations, immutable entries, tasks, submissions and documents. The built-in entry types are pi.user, pi.assistant, pi.tool-result, pi.system, pi.reset and

一个 Session 拥有一条变更线。Storage.commit(writes, context) 原子地持久化一个批次，并 resolve 为一个 Seq durable/src/types.ts:997。那条线上有五种记录类型：conversations、不可变 entries、tasks、submissions 和 documents。内置的 entry 类型是 pi.user、pi.assistant、pi.tool-result、pi.system、pi.reset 以及

pi.compactiondurable/src/entries.ts. The built-in documents are pi.agent, pi.provider, pi.live, pi.inbox and pi.usage.

pi.compaction durable/src/entries.ts。内置的 documents 是 pi.agent、pi.provider、pi.live、pi.inbox 和 pi.usage。

Recovery is not replay of an event log; a “Session-kernel semantic event journal” is a listed non-goal durable/docs/spec.md §13. Each task resumes from its last committed checkpoint:

恢复不是重放事件日志；“Session 内核的语义事件日志”被明确列为非目标 durable/docs/spec.md §13。每个任务都从它最后一次提交的检查点继续：

```typescript the five durable states of a task durable/src/types.ts TS

export type TaskState<S, R> =
    | {
    /** Eligible for scheduling. */
    readonly status: "pending";
    /** Complete durable state from which execution resumes. */
    readonly checkpoint: S;
    readonly outcome?: never;
    }
    | {
    /** Reserved by one in-memory task invocation. */
    readonly status: "running";
    ...
    }
    | {
    /** Parked without an invocation until every task in 'on' is terminal; then resumes at 'checkpoint'. */
    readonly status: "waiting";
    readonly checkpoint: S;
    readonly on: readonly TaskId[];
    readonly policy: JoinPolicy;
    readonly outcome?: never;
    }
    | {
    /** Outcome decided; becomes terminal once no ordinary owned work below is live. Runs no more code. */
    readonly status: "completing";
    ...
    }
    | {
    /** Permanently settled durable result receipt. */
    readonly status: "terminal";
    ...
    };
```

From line 486. The body of running repeats pending’s fields; completing and terminal carry outcome: TaskOutcome<R> and no checkpoint. Cuts marked with …. JoinPolicy is "fail Fast" | "all Settled" durable/src/types.ts:267.

从第 486 行开始。running 的分支重复 pending 的字段；completing 和 terminal 携带 outcome: TaskOutcome<R> 且没有 checkpoint。省略处以 … 标出。JoinPolicy 是 "fail Fast" | "all Settled" durable/src/types.ts:267。

A TaskOutcome is completed, failed, aborted, orphaned or faulted durable/src/types.ts:449. Every phase handler “must commit a changed checkpoint or a terminal outcome through runtime.commit(); returning without durable progress faults the task” durable/src/types.ts:148. Abort runs bottom-up: “An abort invocation of a task starts only once its ordinary owned work is no longer live” durable/docs/spec.md §5.

一个 TaskOutcome 是 completed、failed、aborted、orphaned 或 faulted durable/src/types.ts:449。每个阶段处理器“必须通过 runtime.commit() 提交一个变化的检查点或一个终态 outcome；没有持久进展就返回会让任务进入 faulted” durable/src/types.ts:148。abort 自底向上运行：“一个任务的 abort 调用，只有在它所拥有的常规工作都不再存活之后才会启动” durable/docs/spec.md §5。

<table><tr><td>TASK</td><td>PHASES</td><td>提交什么</td></tr><tr><td>pi.generation durable/src/harness/generation.ts:115</td><td>prepare → request → retry · poll · tools，外加 abort</td><td>仅当计划中的提示词或工具与记录重放出来的内容不同时才提交 pi.system 条目 durable/src/harness/prompt.ts:66；部分输出；pi.assistant 条目</td></tr><tr><td>pi.tool durable/src/harness/tool.ts:50</td><td>call、execute（仅恢复时），外加 abort</td><td>运行前提交 intent { phase: &quot;execute&quot;, arguments, replay }，随后是 pi.tool-result</td></tr><tr><td>pi.compaction durable/src/harness/compaction.ts:103</td><td>select → summarize → retry，外加 abort</td><td>一条带摘要的 pi.compaction 条目</td></tr></table>

Three built-in tasks drive a turn. Defaults: compaction reserve Tokens 16,384, keepRecentTokens 20,000, background Tokens 32,768; retries 3 with a 2,000 ms base delay; partial text and tool output committed at most every 100 ms durable/src/harness/agent.ts:19.

三个内置任务驱动一个轮次。默认值：compaction 的 reserveTokens 为 16,384，keepRecentTokens 为 20,000，backgroundTokens 为 32,768；重试 3 次，基础延迟 2,000 ms；部分文本与工具输出最多每 100 ms 提交一次 durable/src/harness/agent.ts:19。

The tool task is where durability meets side efects. call resolves the tool, validates, runs before Tool, commits the intent, executes, runs after Tool and appends the result in one handler. Only recovery reaches execute:

工具任务正是持久性与副作用相遇的地方。call 在一个处理器里依次完成：解析工具、校验、运行 beforeTool、提交 intent、执行、运行 afterTool 并追加结果。只有恢复流程会走到 execute：

![](images/7839da717d9e666fe087061ee79214bfd8bf5e92949b9d3b2628732a5ed56db8.jpg)

A tool runs twice only if two records agree it is safe to. Both the intent stored before the crash and the tool registered after it must say replay: "safe"; replay defaults to "unsafe" durable/src/harness/types.ts:215. Row 4 records a failed outcome, so conversations the call owned are aborted. From ToolTask.execute durable/src/harness/tool.ts:94.

只有两条记录都同意安全时，一个工具才会跑第二次。崩溃前存下的 intent 和之后注册的工具都必须声明 replay: "safe"；replay 默认是 "unsafe" durable/src/harness/types.ts:215。第 4 行记录了一个失败的 outcome，因此这次调用所拥有的会话会被 abort。摘自 ToolTask.execute durable/src/harness/tool.ts:94。

The built-in CodingTools (read, write, edit, bash and the rest under durable/src/tools/) set no replay, so a crash midcall always interrupts them. Hooks get the same treatment: they “run in extension order of the line; a crash before the consuming commit may rerun them” durable/docs/spec.md §7.2. A hook that must decide once can record its decision with memo(name, candidate), which “is one gated commit” durable/docs/spec.md §5; hooks and the asking task share the same memos durable/src/harness/types.ts:604. The hooks are before Request, after Response, onYield and after Tools on generation, before Tool and after Tool on tools, and before Compact on compaction.

内置的 CodingTools（read、write、edit、bash 以及 durable/src/tools/ 下的其余工具）都不设置 replay，所以中途崩溃总会打断它们。钩子受到的待遇相同：它们“按扩展顺序在变更线上运行；在消费它的提交之前发生崩溃可能导致它们重跑” durable/docs/spec.md §7.2。必须只决定一次的钩子可以用 memo(name, candidate) 记录它的决定，这“是一次带闸门的提交” durable/docs/spec.md §5；钩子与提问的任务共享同一批 memo durable/src/harness/types.ts:604。这些钩子是：generation 上的 beforeRequest、afterResponse、onYield 和 afterTools，tools 上的 beforeTool 和 afterTool，以及 compaction 上的 beforeCompact。

Submissions are idempotent by request id: a second submit() with the same requestId returns the existing submission durable/src/harness/submissions.ts:155.

Submissions 按 request id 幂等：带着相同 requestId 的第二次 submit() 返回已有的 submission durable/src/harness/submissions.ts:155。

<table><tr><td>BACKEND</td><td>OPENED WITH</td><td>持久性</td></tr><tr><td>Memory</td><td>new MemoryStorage()</td><td>不持久化任何东西</td></tr><tr><td>SQLite</td><td>openNodeSqliteStorage(file)</td><td>PRAGMA journal_mode = WAL, synchronous = NORMAL durable/src/storage/sqlite/node.ts:190：“提交能在进程崩溃后存活；最新的一次可能在断电或宿主机故障时丢失”</td></tr><tr><td>JSONL</td><td>openNodeJsonlStorage(directory, context)</td><td>仅追加文件；{ fsync: true } 会在每个提交标记前做刷盘，默认关闭 durable/src/storage/jsonl/storage.ts:256</td></tr></table>

Three backends, one owner each. “One process owns a storage at a time; there is no cross-process locking” durable/README.md §Storage. The experimental server supplies that lock with proper-lockfile in each session worker.

三种后端，各有唯一的持有者。“一个存储在同一时刻只由一个进程拥有；不存在跨进程加锁” durable/README.md §Storage。实验特性的服务器在每个 session worker 里用 proper-lockfile 提供了这把锁。

Tools reach the machine through an ExecutionEnv, which is FileSystem plus Shell durable/src/env/index.ts:324. Its operations return Result<T, E>, { ok: true, value } | { ok: false, error }, instead of throwing durable/src/env/index.ts:4. The local implementation is NodeExecutionEnv, whose id is "node:local" durable/src/env/node.ts:605.

工具通过 ExecutionEnv 触达机器，它是 FileSystem 加 Shell durable/src/env/index.ts:324。它的操作返回 Result<T, E>，即 { ok: true, value } | { ok: false, error }，而不是抛异常 durable/src/env/index.ts:4。本地实现是 NodeExecutionEnv，其 id 为 "node:local" durable/src/env/node.ts:605。

#### pi-env: tools on another machine

#### pi-env：把工具放到另一台机器上

pi-env is a second ExecutionEnv: “an agent’s tools run on another machine, usually over SSH, while the Durable worker, its storage and credentials stay local” env/README.md. Nothing in the repository imports it outside its own tests. The remote half is a Rust daemon in env/daemon/, 4,027 lines in 13 .rs files. The README says the package ships it prebuilt in bin/ for Linux, macOS, Android (Termux) and Windows on x86-64 and arm64; bin/ is a build output and is absent from the checkout.

pi-env 是第二个 ExecutionEnv：“一个智能体的工具在另一台机器上运行，通常通过 SSH，而 Durable 的 worker、它的存储和凭据仍留在本地” env/README.md。仓库里除了它自己的测试之外没有任何地方导入它。远端那一半是 env/daemon/ 里的一个 Rust 守护进程，13 个 .rs 文件共 4,027 行。README 说该包为 Linux、macOS、Android（Termux）以及 x86-64 和 arm64 上的 Windows 预构建好它，放在 bin/ 里；bin/ 是构建产物，在源码检出中并不存在。

The client spawns the daemon with serve --token <hex> env/src/connection.ts:268 and discards everything on stdout before the line PI-ENV <token>, so shell start-up noise cannot corrupt the stream env/src/connection.ts:329. After that, stdout carries only frames:

客户端用 serve --token <hex> 启动守护进程 env/src/connection.ts:268，并丢弃 PI-ENV <token> 这一行之前 stdout 上的所有内容，这样 shell 启动噪声就不会污染数据流 env/src/connection.ts:329。在这之后，stdout 只承载帧：

![](images/b9d93515b8f4348142636b5982bdeb23e236465fb3bf98a0d4b967d462dba0ac.jpg)

JSON says what to do; raw bytes carry file contents and output. A frame shorter than 9 bytes or longer than 16 MiB ends the connection as “Corrupt frame from pi-env” env/src/connection.ts:345. Layout from env/docs/protocol.md §Frames; schematic, not to scale.

JSON 说明要做什么；原始字节承载文件内容和输出。短于 9 字节或长于 16 MiB 的帧会以“Corrupt frame from pi-env”结束连接 env/src/connection.ts:345。布局来自 env/docs/protocol.md §Frames；示意图，非按比例。

Each side sends ping every 5 s. “The daemon kills every process group it started and exits after 30 seconds without receiving any bytes, or when stdin ends” env/docs/protocol.md §Liveness. The client gives up on a connection after the same 30 s of silence env/src/connection.ts:15.

每一侧每 5 秒发一次 ping。“守护进程会杀掉它启动的每个进程组，并且在 30 秒内没有收到任何字节、或 stdin 结束时退出” env/docs/protocol.md §Liveness。客户端在同样 30 秒的静默之后放弃连接 env/src/connection.ts:15。

ssh Arguments() builds the ssh command line env/src/ssh.ts:77. It passes -T -a -x and sets BatchMode=yes, ClearAllForwardings=yes, ForwardAgent=no, ForwardX11=no, ControlMaster=no, ControlPath=none, RemoteCommand=none, PermitLocalCommand=no, SendEnv=-*, StrictHostKeyChecking=yes, a caller-supplied

ssh Arguments() 构造 ssh 命令行 env/src/ssh.ts:77。它传入 -T -a -x，并设置 BatchMode=yes、ClearAllForwardings=yes、ForwardAgent=no、ForwardX11=no、ControlMaster=no、ControlPath=none、RemoteCommand=none、PermitLocalCommand=no、SendEnv=-*、StrictHostKeyChecking=yes，以及调用方提供的

UserKnownHostsFile, GlobalKnownHostsFile=none and a fixed HostKeyAlias. Host keys are accepted once, out of band, through scanHostKey() and acceptHostKey().

UserKnownHostsFile、GlobalKnownHostsFile=none 和一个固定的 HostKeyAlias。主机密钥只通过 scanHostKey() 和 acceptHostKey() 一次性、带外接受。

The daemon file on the remote is named pi-env-<first 32 hex digits of its SHA-256> env/src/ssh.ts:371. deploy Daemon() hashes the remote file before each start and uploads only when it is missing or diferent; an upload whose hash does not match is deleted with “pi-env upload is corrupt” env/src/ssh.ts:396.

远端的守护进程文件名为 pi-env-<其 SHA-256 的前 32 位十六进制> env/src/ssh.ts:371。deployDaemon() 在每次启动前对远端文件做哈希，只有文件缺失或不同时才上传；哈希不匹配的上传会被删除并报“pi-env upload is corrupt” env/src/ssh.ts:396。

#### chord: the composition runtime

#### chord：组合运行时

Despite its name, chord has nothing to do with key chords. “Chord is an application-composition runtime for systems assembled from plugins/extensions”, and “it is not a Pi package: it does not depend on any other Pi workspace package” chord/README.md. Its parts:

尽管名字如此，chord 与和弦没有任何关系。“Chord 是一个面向由插件/扩展组装起来的系统的应用组合运行时”，而且“它不是一个 Pi 包：它不依赖任何其他 Pi 工作区包” chord/README.md。它的组成部分有：

Facets: synchronous setup units. A facet calls env.use(), env.observe(), env.provide() and env.provide Many() chord/src/types.ts:281; the host builds the dependency graph from those calls, activates providers before consumers and disposes in reverse order.

Facets：同步的 setup 单元。一个 facet 调用 env.use()、env.observe()、env.provide() 和 env.provideMany() chord/src/types.ts:281；宿主从这些调用构建依赖图，先激活 provider 再激活 consumer，并按相反顺序释放。

Services: typed tokens in mode "singleton" or "keyed" chord/src/types.ts:123, process-local or published to remote consumers. Arguments, results, snapshots and updates must be strict JSON.

Services：模式为 "singleton" 或 "keyed" 的类型化 token chord/src/types.ts:123，可以是进程本地的，也可以发布给远端 consumer。参数、结果、快照和更新都必须是严格 JSON。

Replicated state: change(context, draft => …) publishes one revision chord/src/services/state.ts:202. Replicas receive delta operations.

复制状态：change(context, draft => …) 发布一个修订版本 chord/src/services/state.ts:202。副本接收 delta 操作。

Control service: \$chord.service with members catalogue, subscribe and unsubscribe chord/src/services/wire.ts:40. A subscriber holds at most 100 bufered updates; the 101st replaces the bufer with one reset snapshot chord/src/services/provider.ts:453.

控制服务：\$chord.service，成员为 catalogue、subscribe 和 unsubscribe chord/src/services/wire.ts:40。订阅者最多持有 100 个缓冲更新；第 101 个会用一份重置快照替换整个缓冲 chord/src/services/provider.ts:453。

Context: “a Go-like context system for cancellation and invocation-scoped application values” chord/README.md, with BACKGROUND_CONTEXT, TODO_CONTEXT, withAbortSignal, with Cancel and withContextValue

Context：“一套类 Go 的上下文系统，用于取消和调用作用域内的应用值” chord/README.md，配有 BACKGROUND_CONTEXT、TODO_CONTEXT、withAbortSignal、withCancel 和 withContextValue

chord/src/context/index.ts:55.

chord/src/context/index.ts:55。

```typescript the seven delta operations chord/src/delta/index.ts TS
export type 0p =
    | readonly ["r", JsonValue]
    | readonly ["s", NonEmptyPath, JsonValue]
    | readonly ["d", NonEmptyPath]
    | readonly ["a", NonEmptyPath, string]
    | readonly ["t", NonEmptyPath, number]
    | readonly ["p", Path, number, number, JsonValue[]]
    /** Reorder an array in place: `new[i] = old[permutation[i]]\'. */
    | readonly ["m", Path, number[]];
```

Complete, from line 32. Replace root, set, delete, string append, string front-truncate, array splice, permutation. String append is what makes a streamed answer cheap to replicate.

完整，从第 32 行开始。分别是替换根、set、delete、字符串追加、字符串前端截断、数组 splice、permutation。正是字符串追加让流式回答的复制变得廉价。

The Node bundler builds each facet entry with esbuild into one CommonJS file named facet-<12 hex>-[hash].cjs and records a sha256-… integrity value chord/src/node/bundle.ts:88. The loader recomputes the hash before compiling the source with node:vm and fails with “Facet bundle integrity check failed” on mismatch chord/src/node/bundle-loader.ts:231. FacetHost.reload() swaps facets at run time chord/src/facets/host.ts:423; the server’s /reload uses it.

Node 打包器用 esbuild 把每个 facet 入口构建成一个名为 facet-<12 位十六进制>-[hash].cjs 的 CommonJS 文件，并记录一个 sha256-… 完整性值 chord/src/node/bundle.ts:88。加载器在用 node:vm 编译源码之前重新计算该哈希，不匹配就以“Facet bundle integrity check failed”失败 chord/src/node/bundle-loader.ts:231。FacetHost.reload() 在运行时替换 facets chord/src/facets/host.ts:423；服务器的 /reload 用的就是它。

## pi-protocol, pi-server, pi-client

## pi-protocol、pi-server、pi-client

PROTOCOL_VERSION is 8 protocol/src/protocol.ts:5, and the README is blunt: “The protocol is experimental and has no compatibility guarantees” protocol/README.md:41. A frame is a 4-byte unsigned big-endian length and one definite-length CBOR item from the package’s own codec. Default limits are 16 MiB per frame protocol/src/framing.ts:6, 1,000,000 array elements or map entries, and 64 nesting levels protocol/README.md:41 protocol/src/cbor/options.ts:8.

PROTOCOL_VERSION 是 8 protocol/src/protocol.ts:5，README 说话很直接：“这个协议是实验性的，不提供任何兼容性保证” protocol/README.md:41。一帧由一个 4 字节无符号大端长度和该包自带 codec 编码的一个定长 CBOR 项组成。默认限制是每帧 16 MiB protocol/src/framing.ts:6、1,000,000 个数组元素或 map 条目，以及 64 层嵌套 protocol/README.md:41 protocol/src/cbor/options.ts:8。

```javascript
FIG. 7.4 CLIENT HELLO, BYTE BY BYTE
25 BYTES ENCODED BY ENCODECLIENTMESSAGE({ TYPE: "HELLO", VERSION: 8 })
```

<table><tr><td>length00 00 00 15 = 21</td><td>a2map</td><td>&quot;type&quot;64 74 79 70 65</td><td>&quot;hello&quot;65 68 65 6c 6c 6f</td><td>&quot;version&quot;67 ... 6e</td><td>088</td></tr><tr><td>0</td><td>4</td><td>5</td><td>10</td><td>16</td><td>2425</td></tr></table>

The first frame of every connection is 25 bytes. A CBOR map of two text keys and the protocol version as a one-byte integer. The server answers with the same map plus serverId, 72 bytes for a UUID. Real bytes from the pinned build, encoded by research/capture/experimental-stack-frames.mjs into research/out/experimental-stack-frames.txt; drawn to scale.

每个连接的第一帧都是 25 字节：一个含两个文本键的 CBOR map，协议版本为单字节整数。服务器用同样的 map 加上 serverId 回应，UUID 占 72 字节。真实字节取自固定版本构建，由 research/capture/experimental-stack-frames.mjs 编码进 research/out/experimental-stack-frames.txt；按比例绘制。

Envelopes are TypeBox objects with additional Properties: false, so an extra field fails validation; the capture shows “Invalid client protocol message” for a hello with one extra key research/out/experimental-stack-frames.txt.

信封是 additionalProperties: false 的 TypeBox 对象，所以多出一个字段就会校验失败；那次抓取显示，多带一个键的 hello 会得到“Invalid client protocol message” research/out/experimental-stack-frames.txt。

<table><tr><td>DIRECTION</td><td>TYPE</td><td>FIELDS</td></tr><tr><td>client → server</td><td>hello</td><td>version —— 必须是第一帧</td></tr><tr><td>client → server</td><td>request</td><td>id, target, call</td></tr><tr><td>client → server</td><td>cancel</td><td>id, target</td></tr><tr><td>server → client</td><td>hello</td><td>version（字面量 8）, serverId</td></tr><tr><td>server → client</td><td>hello_error</td><td>error {code, message}</td></tr><tr><td>server → client</td><td>response</td><td>id, ok: true, result? 或 ok: false, error</td></tr><tr><td>server → client</td><td>service_update</td><td>subscriptionId, update</td></tr><tr><td>server → client</td><td>attachment</td><td>一个会话 target，或 null</td></tr></table>

Eight envelope types, and the payloads are opaque. target is {serverId} or {serverId, sessionId, attachmentId}, and serverId must be a lowercase UUIDv4. call and result are Chord values that pi-protocol only checks for strict JSON. From protocol/src/protocol.ts.

八种信封类型，载荷都是不透明的。target 是 {serverId} 或 {serverId, sessionId, attachmentId}，serverId 必须是小写 UUIDv4。call 和 result 是 Chord 值，pi-protocol 只检查它们是否为严格 JSON。摘自 protocol/src/protocol.ts。

pi-server listens on a Unix domain socket only; there is no HTTP or WebSocket listener in the package. The socket path is <dir>/<serverId>.sock server/src/transports/unix/address.ts:8 with mode 0600 server/src/transports/unix/listener.ts:11. A client that does not finish the handshake within 5 s is dropped with “Handshake timeout” server/src/server.ts:42. The error codes are wrong_server, session_not_found, session_ambiguous, session_not_attached and server_draining server/src/errors.ts:5. The server does not wrap AgentSession: the session worker imports Harness from pi-durable and opens openNodeSqliteStorage CA/src/experimental/session-worker.ts:15.

pi-server 只监听 Unix 域套接字；包里没有 HTTP 或 WebSocket 监听器。套接字路径是 <dir>/<serverId>.sock server/src/transports/unix/address.ts:8，模式为 0600 server/src/transports/unix/listener.ts:11。未能在 5 秒内完成握手的客户端会被丢弃，报“Handshake timeout” server/src/server.ts:42。错误码是 wrong_server、session_not_found、session_ambiguous、session_not_attached 和 server_draining server/src/errors.ts:5。服务器不包装 AgentSession：session worker 从 pi-durable 导入 Harness 并打开 openNodeSqliteStorage CA/src/experimental/session-worker.ts:15。

pi-client exports Client, createClientServiceTransport (the Chord adapter) and three error classes client/src/index.ts; discoverUnixServers() scans a server directory client/src/unix.ts:37. It “never reconnects or replays requests automatically”; the application calls reconnect(), attaches again and repeats only what it knows is safe client/README.md:34.

pi-client 导出 Client、createClientServiceTransport（Chord 适配器）和三个错误类 client/src/index.ts；discoverUnixServers() 扫描一个服务器目录 client/src/unix.ts:37。它“从不自动重连或重放请求”；应用要自己调用 reconnect()、重新 attach，并且只重复它知道安全的部分 client/README.md:34。

W H A T T H I S M E A N S F O R Y O U

这 对 你 意 味 着 什 么

Do not plan an integration on pi server: it is absent from npm and the binary, and protocol 8 promises no compatibility.

不要把集成方案押在 pi server 上：它不在 npm 和二进制里，而协议 8 不承诺任何兼容性。

Embed pi-durable directly if you need crash-safe turns today; declare replay: "safe" only on tools you can run twice.

如果今天就需要崩溃安全的轮次，就直接嵌入 pi-durable；只对你能跑两次的工具声明 replay: "safe"。

Give every durable storage exactly one owning process; the package will not stop a second one.

给每个持久化存储恰好一个所属进程；这个包不会阻止第二个进程。

For pi-env, accept the host key out of band once, then let the content-addressed daemon redeploy itself.

对于 pi-env，先一次性带外接受主机密钥，然后让这个内容寻址的守护进程自己重新部署。

The Pi Durable Technical Manual, a separate book in this series written against pi@5b6c792 and npm 1.0.3, covers pi-durable at length: commits, tasks, documents, observation and recovery. This section stays at the depth the coding agent needs.

《Pi Durable 技术手册》是本系列中的另一本书，针对 pi@5b6c792 和 npm 1.0.3 撰写，详细覆盖了 pi-durable：提交、任务、文档、观测与恢复。本节只讲到编码智能体所需的深度。

Sources: CA/src/experimental/cli.ts; CA/src/experimental/commands.ts (runExperimentalCommand); CA/src/cli/experimental/commands/server.ts, client.ts, command-options.ts (parseTransportAddress); CA/src/experimental/server.ts (resolveServerDirectory, ensurePrivateServerDirectory, resolveSessionDirectory, startForegroundServer); CA/src/experimental/process.ts; CA/src/experimental/radius-auth.ts, radius-relay.ts; CA/src/experimental/session-worker.ts; CA/src/experimental/services/README.md, durable/README.md, vacation/README.md; CA/tsconfig.build.json; CA/package.json; scripts/coding-agent-consumer.mjs; pi-test.sh; durable/README.md; durable/docs/spec.md §1, §5, §7.2, §13; durable/src/types.ts (TaskState, TaskOutcome, PhaseHandler, Storage); durable/src/entries.ts; durable/src/harness/{generation,tool,compaction,agent,prompt,submissions,types}.ts; durable/src/storage/sqlite/node.ts, jsonl/storage.ts; durable/src/env/index.ts, node.ts; env/README.md; env/docs/protocol.md; env/src/connection.ts, ssh.ts (ssh Arguments, deploy Daemon); chord/README.md; chord/src/types.ts; chord/src/delta/index.ts; chord/src/services/{wire,provider,state}.ts; chord/src/node/bundle.ts, bundle-loader.ts; chord/src/facets/host.ts; chord/src/context/index.ts; protocol/README.md; protocol/src/{protocol,framing}.ts, cbor/options.ts; server/src/{server,errors}.ts, transports/unix/{address,listener}.ts; client/README.md; client/src/index.ts, unix.ts; research/capture/experimental-stack-frames.mjs; research/out/experimental-stack-frames.txt; research/out/stats.txt

来源：CA/src/experimental/cli.ts；CA/src/experimental/commands.ts（runExperimentalCommand）；CA/src/cli/experimental/commands/server.ts、client.ts、command-options.ts（parseTransportAddress）；CA/src/experimental/server.ts（resolveServerDirectory、ensurePrivateServerDirectory、resolveSessionDirectory、startForegroundServer）；CA/src/experimental/process.ts；CA/src/experimental/radius-auth.ts、radius-relay.ts；CA/src/experimental/session-worker.ts；CA/src/experimental/services/README.md、durable/README.md、vacation/README.md；CA/tsconfig.build.json；CA/package.json；scripts/coding-agent-consumer.mjs；pi-test.sh；durable/README.md；durable/docs/spec.md §1、§5、§7.2、§13；durable/src/types.ts（TaskState、TaskOutcome、PhaseHandler、Storage）；durable/src/entries.ts；durable/src/harness/{generation,tool,compaction,agent,prompt,submissions,types}.ts；durable/src/storage/sqlite/node.ts、jsonl/storage.ts；durable/src/env/index.ts、node.ts；env/README.md；env/docs/protocol.md；env/src/connection.ts、ssh.ts（ssh Arguments、deploy Daemon）；chord/README.md；chord/src/types.ts；chord/src/delta/index.ts；chord/src/services/{wire,provider,state}.ts；chord/src/node/bundle.ts、bundle-loader.ts；chord/src/facets/host.ts；chord/src/context/index.ts；protocol/README.md；protocol/src/{protocol,framing}.ts、cbor/options.ts；server/src/{server,errors}.ts、transports/unix/{address,listener}.ts；client/README.md；client/src/index.ts、unix.ts；research/capture/experimental-stack-frames.mjs；research/out/experimental-stack-frames.txt；research/out/stats.txt

## 7.2 Security model

## 7.2 安全模型

Pi runs every tool call with your account's permissions and asks for no approval. Project trust decides which files in a folder may configure Pi; it does not decide what the model may do once Pi is running.

Pi 以你账户的权限运行每一次工具调用，不请求任何审批。项目信任决定一个文件夹里哪些文件可以配置 Pi；它并不决定 Pi 跑起来之后模型能做什么。

A repository you cloned this morning contains .pi/extensions/, an AGENTS.md and a test script. Starting Pi in it can run three kinds of code: the extension, whatever the model decides to run after reading AGENTS.md, and the script the model calls. This section shows which of the three Pi gates and how. It quotes Pi’s own security stance, follows the project-trust decision through the code, compares the isolation options the docs ofer, and lists the controls inside individual components.

你今早克隆的一个仓库里有 .pi/extensions/、一个 AGENTS.md 和一个测试脚本。在里面启动 Pi 可能运行三类代码：扩展本身、模型读完 AGENTS.md 后决定运行的东西，以及模型调用的那个脚本。本节说明 Pi 给这三类代码分别上了哪些闸门、怎么上的。它引用 Pi 自己的安全立场，沿着代码追踪项目信任的判定，比较文档提供的隔离选项，并列出各个组件内部的控制措施。

## The stance

## 立场

The shipped guide begins with one rule: “Treat model-generated commands and code as untrusted. Pi can read, change, and execute files with the permissions of the account that started it, and it does not ask for approval before every tool call” CA/docs/security.md. Extensions, package installers, language servers and other child processes “run with those same permissions unless an operating-system or virtualization boundary restricts them”. The guide names what is not a boundary: “Watching the transcript, using project trust, and reviewing changes do not create a security boundary.”

随包发布的指南以一条规则开场：“把模型生成的命令和代码视为不可信。Pi 能以启动它的那个账户的权限读取、修改和执行文件，而且它不会在每次工具调用前请求审批” CA/docs/security.md。扩展、包管理器、语言服务器和其他子进程“同样以那些权限运行，除非有操作系统或虚拟化边界限制它们”。指南还点名了什么不算边界：“盯着记录、用项目信任、审查改动，这些都不构成安全边界。”

The repository’s SECURITY.md draws the reporting line in the same place: “Pi treats the local user account and files writable by that account as inside the same trust boundary as the Pi process itself” SECURITY.md. In the guide’s words, prompt injection, the lack of a built-in sandbox and behaviour of user-installed extensions are “generally outside the security boundary unless the report demonstrates a privilege-boundary bypass or access that the local user did not already have” CA/docs/security.md §Report a security issue. Reports go to security@earendil.com or a private GitHub advisory SECURITY.md.

仓库的 SECURITY.md 把上报界线划在同一处：“Pi 把本地用户账户以及该账户可写的文件，视在与 Pi 进程本身同一个信任边界之内” SECURITY.md。用指南的话说，提示词注入、缺少内置沙箱、以及用户安装的扩展的行为，通常“在安全边界之外，除非报告能演示一次权限边界绕过，或一种本地用户本来就不具备的访问” CA/docs/security.md §Report a security issue。报告请发到 security@earendil.com，或走私有 GitHub 安全通告 SECURITY.md。

The working folder does not confine anything either: it “controls resource discovery and the default location for tools, but it does not prevent commands from accessing other paths available to the Pi process” CA/docs/security.md.

工作目录同样不构成约束：它“控制资源发现和工具的默认位置，但并不阻止命令访问 Pi 进程可用的其他路径” CA/docs/security.md。

## Project trust

## 项目信任

Project trust is a startup gate on configuration. A folder needs a decision when it has any of eight entries under .pi/ — settings.json, mcp.json, extensions, skills, prompts, themes, SYSTEM.md, APPEND_SYSTEM.md CA/src/core/trustmanager.ts:30 — or a .agents/skills directory in the folder or any ancestor. \~/.agents/skills itself is a user resource and never triggers it CA/src/core/trust-manager.ts:186. A bare .pi directory needs no decision.

项目信任是启动时对配置的一道闸门。当一个文件夹的 .pi/ 下有八个条目中的任何一个——settings.json、mcp.json、extensions、skills、prompts、themes、SYSTEM.md、APPEND_SYSTEM.md CA/src/core/trustmanager.ts:30——或者该文件夹或其任一祖先目录下有 .agents/skills 目录时，就需要一次判定。\~/.agents/skills 本身是用户资源，永远不会触发它 CA/src/core/trust-manager.ts:186。只有一个空的 .pi 目录则不需要判定。

![](images/f7498fd8abdc748fe05b41b07c06d5704ce755243e46be4d7584681056404770.jpg)

The first row that answers decides, and every path without an answer ends untrusted. Order from resolveProjectTrusted() CA/src/core/projecttrust.ts:46. The command-line override is checked before the resource scan, so --no-approve applies even in a folder with nothing to protect. Rows 3–6 run only when protected resources exist.

第一个给出答案的行决定结果，任何没有得出答案的路径都以不受信任告终。顺序来自 resolveProjectTrusted() CA/src/core/projecttrust.ts:46。命令行覆盖在资源扫描之前检查，所以即使文件夹里没有任何需要保护的东西，--no-approve 依然生效。第 3–6 行只在存在受保护资源时才运行。

Row 3 runs before any project code loads. loadProjectTrustExtensions() forces the project untrusted and loads the user, global and command-line extensions plus SDK factories, so project-local extensions cannot vote on their own trust CA/src/core/resource-loader.ts:501. Built-in extensions wait for the final pass, because “project settings can disable them, and a loaded extension cannot be unloaded” CA/src/core/resource-loader.ts:683. The handler loop returns the first "yes" or "no"; a handler that throws is reported and skipped CA/src/core/extensions/runner.ts:295.

第 3 行在任何项目代码加载之前运行。loadProjectTrustExtensions() 强制把项目判为不受信任，并加载用户级、全局和命令行扩展以及 SDK 工厂，这样项目本地的扩展就无法为自己的信任投票 CA/src/core/resource-loader.ts:501。内置扩展要等最后一轮，因为“项目设置可以禁用它们，而已加载的扩展无法卸载” CA/src/core/resource-loader.ts:683。处理器循环遇到第一个 "yes" 或 "no" 就返回；抛异常的处理器会被报告并跳过 CA/src/core/extensions/runner.ts:295。

The trust store is trust.json in the agent directory CA/src/core/trust-manager.ts:214, a JSON object from canonical directory paths to true or false. Lookup walks from the folder up to the root and takes the first explicit value CA/src/core/trustmanager.ts:45. Reads and writes hold a proper-lockfile lock on trust.json.lock. The interactive prompt reads “Trust project folder?” and ofers five choices:

信任存储是智能体目录下的 trust.json CA/src/core/trust-manager.ts:214，一个从规范化目录路径到 true 或 false 的 JSON 对象。查找从该文件夹一路向上走到根，取第一个显式值 CA/src/core/trustmanager.ts:45。读和写都持有 trust.json.lock 上的 proper-lockfile 锁。交互式提示读作“Trust project folder?”，并给出五个选项：

<table><tr><td>CHOICE</td><td>DECISION</td><td>WRITTEN TO trust.json</td></tr><tr><td>Trust</td><td>trusted</td><td>当前文件夹 → true</td></tr><tr><td>Trust parent folder (...)</td><td>trusted</td><td>父目录 → true；删掉当前文件夹自己的条目</td></tr><tr><td>Trust (this session only)</td><td>trusted</td><td>什么都不写</td></tr><tr><td>Do not trust</td><td>untrusted</td><td>当前文件夹 → false</td></tr><tr><td>Do not trust (this session only)</td><td>untrusted</td><td>什么都不写</td></tr></table>

Two of the five choices leave no record. From getProjectTrustOptions() CA/src/core/trust-manager.ts:67. /trust saves a decision later from inside a session CA/src/core/slash-commands.ts:36.

五个选项中有两个不留记录。摘自 getProjectTrustOptions() CA/src/core/trust-manager.ts:67。/trust 可以在会话内部稍后保存判定 CA/src/core/slash-commands.ts:36。

Print, JSON and RPC modes have no trust prompt. Without an override, an extension answer or a saved decision, they load protected resources only under defaultProjectTrust: "always" CA/src/core/project-trust.ts:86. Use --approve or -- no-approve in automation.

打印、JSON 和 RPC 模式没有信任提示。在没有覆盖、没有扩展给出的答案、也没有已保存判定的情况下，它们只在 defaultProjectTrust: "always" 之下加载受保护资源 CA/src/core/project-trust.ts:86。在自动化里请使用 --approve 或 --no-approve。

Granting trust loads project settings, project MCP servers, the extensions, skills, prompt templates, themes and system-prompt files under .pi, and project packages. Declining it also blocks the package manager from project package storage: “Project is not trusted; refusing to access project package storage” CA/src/core/package-manager.ts:1777. The npm and git directories under .pi are covered by that check, but their presence alone does not trigger a decision.

授予信任会加载项目设置、项目 MCP 服务器、.pi 下的扩展、技能、提示词模板、主题和系统提示词文件，以及项目包。拒绝信任同样会挡住包管理器访问项目包存储：“Project is not trusted; refusing to access project package storage” CA/src/core/package-manager.ts:1777。.pi 下的 npm 和 git 目录也在这项检查覆盖范围内，但它们的存在本身不会触发判定。

Two things escape the gate. Context files — AGENTS.override.md, AGENTS.md, CLAUDE.md and their upper-case variants — load with no trust check; only --no-context-files stops them CA/src/core/resource-loader.ts:642. And the session directory is chosen before trust is resolved, from --session-dir, then PI_CODING_AGENT_SESSION_DIR, then the session Dir setting read by a startup settings manager CA/src/main.ts:688. A project’s .pi/settings.json can therefore move where session files are written even when the project is declined; CA/docs/security.md documents the gap.

有两样东西逃出了这道闸门。上下文文件——AGENTS.override.md、AGENTS.md、CLAUDE.md 及其大写变体——加载时不做信任检查；只有 --no-context-files 能挡住它们 CA/src/core/resource-loader.ts:642。另外，会话目录在信任判定之前就已选定，依次取自 --session-dir、PI_CODING_AGENT_SESSION_DIR，最后是由启动时设置管理器读取的 sessionDir 设置 CA/src/main.ts:688。因此，即使项目被拒绝信任，项目的 .pi/settings.json 仍能改变会话文件的写入位置；CA/docs/security.md 记录了这个缺口。

Declining trust does not stop a folder from steering the model. AGENTS.md and CLAUDE.md still enter the system prompt, and the model still runs tools with your permissions. Read instructions in an untrusted repository as input, start Pi with -nc if you have not read them, and isolate the process if you have to run the model there.

拒绝信任并不能阻止一个文件夹左右模型。AGENTS.md 和 CLAUDE.md 依然会进入系统提示词，模型依然以你的权限运行工具。请把不受信任仓库里的指令当作输入来读；如果你没读过它们就用 -nc 启动 Pi；如果非要在那里运行模型，就把进程隔离起来。

The example extension CA/examples/extensions/project-trust.ts says “Try it in a project containing .pi, AGENTS.md/CLAUDE.md, or .agents/skills”. A bare .pi, AGENTS.md and CLAUDE.md do not fire project_trust: the event runs only when one of the eight .pi entries or a project .agents/skills exists CA/src/core/trust-manager.ts:186.

示例扩展 CA/examples/extensions/project-trust.ts 写着“Try it in a project containing .pi, AGENTS.md/CLAUDE.md, or .agents/skills”。只有一个空的 .pi，加上 AGENTS.md 和 CLAUDE.md，并不会触发 project_trust：该事件只在八个 .pi 条目之一存在、或项目级 .agents/skills 存在时才运行 CA/src/core/trust-manager.ts:186。

## Isolation options

## 隔离选项

Because Pi has no sandbox of its own, isolation means running it, or some of its tools, somewhere else. CA/docs/containerization.md compares four methods, and the example extensions add two more.

因为 Pi 自己没有沙箱，隔离意味着把它、或它的一部分工具放到别处运行。CA/docs/containerization.md 比较了四种方法，示例扩展又补了两种。

![](images/3f0dd0c72559e01f7ff3da3f9062d1d48cb9e333e7bd3d009ef7cc084e1c17c4.jpg)

Only whole-process isolation contains extensions. Tool-level methods move selected tools out of the host process and leave Pi, its other tools and its environment variables behind. Rows from CA/docs/containerization.md and CA/examples/extensions/{gondolin,sandbox,permissiongate.ts,protected-paths.ts}; schematic.

只有整进程隔离才能困住扩展。工具级方法把选定的工具移出宿主进程，却把 Pi、它的其他工具和它的环境变量留在原地。各行来自 CA/docs/containerization.md 和 CA/examples/extensions/{gondolin,sandbox,permissiongate.ts,protected-paths.ts}；示意图。

<table><tr><td>METHOD</td><td>HOW</td><td>WHAT TO WATCH</td></tr><tr><td>Plain Docker</td><td>FROM node:24-bookworm-slim, npm install -g --ignore- scripts @earendil-works/pi-coding-agent; 用 -v &quot;$PWD:/workspace&quot; 运行，并给 /root/.pi/agent 配一个具名卷</td><td>用 -e 传入的环境变量在容器内可见；挂载宿主机的 ~/.pi/agent 会暴露其中的凭据</td></tr><tr><td>Docker Sandboxes</td><td>sbx run --kit &quot;docker.io/sbx/pi-kit:latest&quot; pi</td><td>代理会把占位符替换成真实的供应商密钥；在里面运行 /login 会把真实凭据写进沙箱</td></tr><tr><td>NVIDIA OpenShell</td><td>openshell sandbox create --name pi-sandbox --from pi -- pi</td><td>提供文件系统、进程、网络、凭据和推理策略；远端网关不会挂载你的文件夹</td></tr><tr><td>gondolin (example)</td><td>pi -e ~/.pi/agent/extensions/gondolin；QEMU 微虚拟机，Node ≥ 23.6</td><td>&quot;VM 内的命令会继承宿主进程的环境&quot;，所以它不是凭据边界</td></tr><tr><td>sandbox (example)</td><td>@anthropic-ai/sandbox-runtime 0.0.26 替换 bash；macOS 上用 sandbox- exec，Linux 上用 bubblewrap</td><td>配置在 ~/.pi/agent/extensions/sandbox.json 和 .pi/sandbox.json；其他工具不受沙箱保护</td></tr><tr><td>tool_call gate (example)</td><td>permission-gate.ts 在 rm -rf、sudo 和 chmod/chown 777 之前询问，并在没有 UI 时直接拦下；protected-paths.ts 拦截对含 .env、.git/ 或 node_modules/ 的路径的 write 和 edit</td><td>依赖正则和子串规则；写入 .env 的 bash 命令，或模式漏掉的危险命令，都会放行</td></tr></table>

Six ways to narrow what a wrong action reaches. Commands copied from CA/docs/containerization.md and the example extensions at 28dcce2. The guide calls whole-process isolation “usually the strongest practical option” CA/docs/security.md.

六种收窄错误动作影响范围的办法。命令抄自 28dcce2 时的 CA/docs/containerization.md 和示例扩展。指南称整进程隔离“通常是最强的可行选项” CA/docs/security.md。

## Controls inside components

## 组件内部的控制

The components below each enforce a narrow rule. None of them turns Pi into a sandbox, but each closes a specific hole.

下面这些组件各自强制一条很窄的规则。它们都不能把 Pi 变成沙箱，但每一个都能堵上一个具体的漏洞。

Credentials: auth.json is written with mode 0600 and its directory created with 0700; “the mode applies only on creation so administrator-managed modes and ACLs remain intact” CA/src/core/auth-storage.ts:24. Every read-modify-write holds a proper-lockfile lock. mcp-auth.json uses the same backend CA/src/extensions/mcp/oauth.ts:144. An OAuth refresh that has started ignores cancellation: “the provider may already have rotated the refresh token, so the refresh and its persistence ignore signal and are bounded only by a timeout” ai/src/auth/resolve.ts:105.

凭据：auth.json 以 0600 模式写入，其目录以 0700 创建；“该模式只在创建时生效，这样由管理员管理的模式和 ACL 才得以保留” CA/src/core/auth-storage.ts:24。每一次读-改-写都持有 proper-lockfile 锁。mcp-auth.json 使用同一套后端 CA/src/extensions/mcp/oauth.ts:144。已经开始的 OAuth 刷新会忽略取消信号：“供应商可能已经轮换了刷新令牌，所以刷新及其持久化都忽略信号，只受超时约束” ai/src/auth/resolve.ts:105。

MCP configuration: a project .pi/mcp.json loads only when the project is trusted, and it may not set auth: “auth is only allowed in the global mcp.json”, so “a repository cannot pick where the credential goes” CA/src/extensions/mcp/config.ts:133. A server with auth.provider must use https, or http on localhost, 127.0.0.1 or [::1] CA/src/core/mcp-servers.ts:285. oauth.callback Url must be an http loopback URI CA/src/core/mcp-servers.ts:178; oauth.authServerMetadataUrl must be https or loopback http CA/src/core/mcp-servers.ts:201.

MCP 配置：项目的 .pi/mcp.json 只在项目受信任时才加载，而且不得设置 auth：“auth is only allowed in the global mcp.json”，因此“a repository cannot pick where the credential goes” CA/src/extensions/mcp/config.ts:133。带 auth.provider 的服务器必须使用 https，或者在 localhost、127.0.0.1 或 [::1] 上使用 http CA/src/core/mcp-servers.ts:285。oauth.callbackUrl 必须是一个 http 回环 URI CA/src/core/mcp-servers.ts:178；oauth.authServerMetadataUrl 必须是 https 或回环 http CA/src/core/mcp-servers.ts:201。

MCP OAuth: the flow throws OAuthInsecureEndpointError for a non-loopback endpoint that is not https mcp/src/oauth/flow.ts:121 and OAuthIssuerMismatchError when the returned iss difers from the metadata issuer mcp/src/oauth/flow.ts:373.

MCP OAuth：对于不是 https 的非回环端点，该流程抛出 OAuthInsecureEndpointError mcp/src/oauth/flow.ts:121；当返回的 iss 与元数据中的 issuer 不一致时，抛出 OAuthIssuerMismatchError mcp/src/oauth/flow.ts:373。

MCP processes: stdio servers start through cross-spawn with no shell, detached into their own process group on every platform but Windows, so closing kills the group mcp/src/transports/stdio.ts:101. Values in env and headers pass through resolveConfigValue, where a leading ! runs the rest as a shell command CA/src/core/resolve-config-value.ts:140. A trusted config can therefore execute code when a server connects.

MCP 进程：stdio 服务器通过 cross-spawn 启动，不经过 shell；除 Windows 之外的所有平台上都以 detached 方式放入自己的进程组，因此关掉就会杀掉整个进程组 mcp/src/transports/stdio.ts:101。env 和 headers 中的值都经过 resolveConfigValue，其中开头的 `!` 会把剩下的部分当作 shell 命令执行 CA/src/core/resolve-config-value.ts:140。所以一份受信任的配置在服务器连接时就能执行代码。

Codemode: scripts run in QuickJS compiled to WebAssembly, “where the only capability is calling injected tools” codemode/README.md. The prelude freezes the built-ins first codemode/src/runtime/prelude-source.ts:28; the coding agent caps VM memory at 256 MiB CA/src/extensions/codemode/execute.ts:55, the worker sets QuickJS’s maximum stack size codemode/src/runtime/worker.ts:59, and the host sets an interrupt flag before terminate() codemode/src/runtime/host.ts:323. Nested calls are real calls through ctx.execute Tool, so tool_call hooks and permission checks apply CA/src/extensions/codemode/tool.ts:7, and “calls made before a failure are not undone” CA/docs/codemode.md.

Codemode：脚本运行在编译为 WebAssembly 的 QuickJS 中，“在那里唯一的能力就是调用注入的工具” codemode/README.md。prelude 先冻结内置对象 codemode/src/runtime/prelude-source.ts:28；编码智能体把 VM 内存上限设为 256 MiB CA/src/extensions/codemode/execute.ts:55，worker 设置 QuickJS 的最大栈大小 codemode/src/runtime/worker.ts:59，宿主在 terminate() 之前设置中断标志 codemode/src/runtime/host.ts:323。嵌套调用是经由 ctx.executeTool 的真实调用，所以 tool_call 钩子和权限检查照样生效 CA/src/extensions/codemode/tool.ts:7，而且“失败之前发出的调用不会撤销” CA/docs/codemode.md。

Experimental stack: durable tools without replay: "safe" never rerun after a crash. pi-env pins host keys under a fixed alias, turns of every forwarding, re-verifies the daemon’s SHA-256 before each start and kills remote process groups after 30 s of silence. pi server binds a 0600 socket in a 0700 directory it owns, and dials a Radius relay only with credentials (the experimental stack (p. 166)).

实验特性栈：没有 replay: "safe" 的持久化工具在崩溃后绝不重跑。pi-env 用固定别名锁定主机密钥，关闭所有转发，每次启动前重新校验守护进程的 SHA-256，并在 30 秒静默后杀掉远端进程组。pi server 在自己拥有的 0700 目录里绑定一个 0600 套接字，并且只在有凭据时才拨 Radius 中继（见 experimental stack (p. 166)）。

## Supply chain

## 供应链

The repository’s AGENTS.md sets the rules for contributors and agents: “Treat npm dep and lockfile changes as reviewed code. Direct external deps stay pinned to exact versions.” Installs run with --ignore-scripts, and “New deps with lifecycle scripts require review and an explicit allowlist entry” in scripts/generate-coding-agent-install-lock.mjs AGENTS.md §Dependency and Install Security. At 28dcce2 that allowlist has three entries: @google/genai@2.21.0, esbuild@0.28.2 and protobufjs@7.6.6, each with a one-line justification scripts/generate-coding-agent-install-lock.mjs:17. scripts/check-pinned-deps.mjs enforces exact versions, and a pre-commit check blocks lockfile commits unless PI_ALLOW_LOCKFILE_CHANGE is set scripts/check-lockfile-commit.mjs:5. The Docker recipe above installs Pi with --ignorescripts too.

仓库的 AGENTS.md 为贡献者和智能体定下规则：“把 npm 依赖和 lockfile 的改动当作经过评审的代码看待。直接外部依赖必须锁定到精确版本。”安装时带 --ignore-scripts 运行，并且“带生命周期脚本的新依赖需要评审，并显式加入白名单” scripts/generate-coding-agent-install-lock.mjs AGENTS.md §Dependency and Install Security。在 28dcce2 时该白名单有三条：@google/genai@2.21.0、esbuild@0.28.2 和 protobufjs@7.6.6，每条都有一行理由说明 scripts/generate-coding-agent-install-lock.mjs:17。scripts/check-pinned-deps.mjs 强制精确版本，而一项 pre-commit 检查会拦截 lockfile 提交，除非设置了 PI_ALLOW_LOCKFILE_CHANGE scripts/check-lockfile-commit.mjs:5。上面的 Docker 配方安装 Pi 时也带了 --ignore-scripts。

W H A T T H I S M E A N S F O R Y O U

这 对 你 意 味 着 什 么

Decide trust per repository, and remember that a declined project still supplies AGENTS.md.

按仓库逐个决定信任，并且记住：被拒绝信任的项目照样会提供 AGENTS.md。

Pass --approve or --no-approve in CI; non-interactive modes never prompt.

在 CI 里传 --approve 或 --no-approve；非交互模式永远不提示。

Run Pi in a container or VM when the repository or the task is not yours; tool-level isolation leaves extensions on the host.

当仓库或任务不属于你时，把 Pi 跑在容器或 VM 里；工具级隔离会把扩展留在宿主机上。

Keep provider credentials out of the environment of anything you isolate, or use the Docker Sandboxes proxy.

别让供应商凭据进入你隔离的任何东西的环境里，或者使用 Docker Sandboxes 代理。

Review an extension before loading it: it runs inside the Pi process with your permissions.

加载一个扩展之前先审查它：它在 Pi 进程内部以你的权限运行。

Sources: CA/docs/security.md; CA/docs/containerization.md; SECURITY.md; AGENTS.md §Dependency and Install Security; CA/src/core/project-trust.ts (resolveProjectTrusted); CA/src/core/trust-manager.ts (TRUST_REQUIRING_PROJECT_CONFIG_RESOURCES, hasTrustRequiringProjectResources, getProjectTrustOptions, ProjectTrustStore); CA/src/core/resource-loader.ts (loadProjectTrustExtensions, loadCurrentExtensionSet, loadProjectContextFiles); CA/src/core/extensions/runner.ts (emitProjectTrustEvent); CA/src/main.ts (session Dir); CA/src/core/package-manager.ts (assertProjectTrustedForScope); CA/examples/extensions/{project-trust.ts, permission-gate.ts, protected-paths.ts, gondolin/, sandbox/}; CA/src/core/auth-storage.ts; ai/src/auth/resolve.ts (refreshStoredOAuthCredential); CA/src/extensions/mcp/config.ts, oauth.ts; CA/src/core/mcp-servers.ts (validateOAuth, auth check); mcp/src/oauth/flow.ts; mcp/src/transports/stdio.ts; CA/src/core/resolve-config-value.ts; codemode/README.md; codemode/src/runtime/{preludesource,worker,host}.ts; CA/src/extensions/codemode/execute.ts, tool.ts; CA/docs/codemode.md; scripts/generate-codingagent-install-lock.mjs; scripts/check-pinned-deps.mjs; scripts/check-lockfile-commit.mjs

来源：CA/docs/security.md；CA/docs/containerization.md；SECURITY.md；AGENTS.md §Dependency and Install Security；CA/src/core/project-trust.ts（resolveProjectTrusted）；CA/src/core/trust-manager.ts（TRUST_REQUIRING_PROJECT_CONFIG_RESOURCES、hasTrustRequiringProjectResources、getProjectTrustOptions、ProjectTrustStore）；CA/src/core/resource-loader.ts（loadProjectTrustExtensions、loadCurrentExtensionSet、loadProjectContextFiles）；CA/src/core/extensions/runner.ts（emitProjectTrustEvent）；CA/src/main.ts（sessionDir）；CA/src/core/package-manager.ts（assertProjectTrustedForScope）；CA/examples/extensions/{project-trust.ts、permission-gate.ts、protected-paths.ts、gondolin/、sandbox/}；CA/src/core/auth-storage.ts；ai/src/auth/resolve.ts（refreshStoredOAuthCredential）；CA/src/extensions/mcp/config.ts、oauth.ts；CA/src/core/mcp-servers.ts（validateOAuth、auth check）；mcp/src/oauth/flow.ts；mcp/src/transports/stdio.ts；CA/src/core/resolve-config-value.ts；codemode/README.md；codemode/src/runtime/{preludesource,worker,host}.ts；CA/src/extensions/codemode/execute.ts、tool.ts；CA/docs/codemode.md；scripts/generate-codingagent-install-lock.mjs；scripts/check-pinned-deps.mjs；scripts/check-lockfile-commit.mjs

## 7.3 Telemetry and evals

## 7.3 遥测与评测

Pi ships a span contract that nothing in the repository emits into, and an install ping that is on by default. Its evals measure something else, how much its own documentation helps a modelfinish a task.

Pi 发布的 span 契约在仓库里没有任何生产者会往里写入；它还带一个默认开启的安装 ping。它的评测测的是另一件事——它自己的文档对模型完成任务有多大帮助。

Telemetry here means three separate things, and they are easy to confuse. pi-telemetry is a library of interfaces for tracing. Product telemetry is the small amount of data the coding agent sends to pi.dev and to providers. Evals are a private package that runs real agent sessions against a model and scores the result. This section takes them in that order, says exactly what leaves the machine and when, and ends with how an eval run is isolated and reported.

这里的“遥测”指三件互不相同的事，而且很容易混淆。pi-telemetry 是一个用于追踪的接口库。产品遥测是编码智能体发往 pi.dev 和各供应商的那少量数据。评测是一个私有包，它针对模型运行真实的智能体会话并给结果打分。本节按这个顺序展开，准确说明哪些数据会离开机器、在什么时机离开，最后讲一次评测运行如何被隔离和报告。

#### pi-telemetry: a contract with no producer

#### pi-telemetry：一个没有生产者的契约

The package describes itself as “vendor-neutral telemetry contracts and typed schema utilities”, with “no exporter, global current-span state, or dependency on a telemetry backend” telemetry/README.md:11. It is 935 lines including the conformance suite, and it reads no environment variables: a grep of telemetry/src for process.env finds nothing.

这个包把自己描述为“与厂商无关的遥测契约和类型化 schema 工具”，并且“没有导出器、没有全局的当前 span 状态、也不依赖任何遥测后端” telemetry/README.md:11。它连同一致性测试套件一共 935 行，不读任何环境变量：在 telemetry/src 里 grep process.env 一无所获。

```typescript the whole runtime contract telemetry/src/index.ts TS
export interface TelemetryContext {
    start Span<T>(options: SpanOptions, callback: (span: TelemetrySpan) => T | Promise<T>): Promise<T>;
}
export interface TelemetrySpan extends TelemetryContext {
    add Event(name: string, attributes?: SpanAttributes): void;
    set Attributes.attributes: SpanAttributes): void;
    focal Status(status: SpanStatus): void;
}
```

Lines 14–22, complete. SpanStatus is { status: "ok" } or { status: "error"; error?: { name, message } }; attribute values are scalars or arrays of one scalar type telemetry/src/index.ts:1.

第 14–22 行，完整。SpanStatus 是 { status: "ok" } 或 { status: "error"; error?: { name, message } }；属性值是标量，或某一标量类型的数组 telemetry/src/index.ts:1。

Spans are callback-scoped: a span exists only inside the start Span callback, and a span is itself a context for child spans. Around that contract the package exports NOOP_TELEMETRY_CONTEXT telemetry/src/noop.ts:20, the reference InMemoryTelemetryContext telemetry/src/memory.ts:192, schema helpers defineTelemetrySchema and createTypedSpanStarter telemetry/src/index.ts:72, and an adapter conformance suite at @earendil-works/pitelemetry/testing telemetry/src/testing/index.ts:1.

Span 是回调作用域的：它只存在于 startSpan 回调内部，而一个 span 本身就是子 span 的上下文。围绕这个契约，该包导出 NOOP_TELEMETRY_CONTEXT telemetry/src/noop.ts:20、参考实现 InMemoryTelemetryContext telemetry/src/memory.ts:192、schema 辅助函数 defineTelemetrySchema 和 createTypedSpanStarter telemetry/src/index.ts:72，以及一个位于 @earendil-works/pi-telemetry/testing 的适配器一致性测试套件 telemetry/src/testing/index.ts:1。

pi-ai accepts a context as telemetry Context on every provider request, “explicit parent context for telemetry produced by this logical request” ai/src/types.ts:136, and copies it into simple-stream options ai/src/api/simple-options.ts:48. That is the whole integration. A grep of all fourteen packages outside telemetry/ for start Span finds no call, so a context passed to piai receives no spans.

pi-ai 在每次供应商请求上都接受一个上下文作为 telemetryContext，也就是“为这个逻辑请求产生的遥测提供显式的父上下文” ai/src/types.ts:136，并把它复制到 simple-stream 的选项里 ai/src/api/simple-options.ts:48。集成就这么多。对 telemetry/ 之外的全部十四个包 grep startSpan，找不到任何调用，所以传给 pi-ai 的上下文不会收到任何 span。

```txt
FIG. 7.7 WHAT THE TELEMETRY README DESCRIBES, AND WHAT EXISTS COMPARISON
PI-TELEMETRY TelemetryContext · TelemetrySpan NOOP · InMemory · schemas · conformance exporter none, by design
PI-AI telemetry Context?: TelemetryContext accepted on requests and passed along start Span calls none in the repository
PI-AGENT-CORE AGENT_TELEMETRY_SCHEMA · AI_TELEMETRY_SCHEMA · HARNESS_TELEMETRY_SCHEMA · startAiSpan · startHarnessSpan named in the README; not defined anywhere at 28dcce2
```

The contract is complete; the producers are missing. Solid: code that exists. Hatched rose: what a reader of telemetry/README.md §Pi Package Integration expects and will not find. From greps of packages/*/src at 28dcce2; schematic.

契约是完整的；生产者缺失。实线：确实存在的代码。玫红剖面线：读 telemetry/README.md §Pi Package Integration 的人所期待、却找不到的东西。来自 28dcce2 时对 packages/*/src 的 grep；示意图。

D O C ≠ C O D E telemetry/README.md says “@earendil-works/pi-agent-core owns and exports the pi AI-request and harness schemas” and shows an import of AGENT_TELEMETRY_SCHEMAS, AI_TELEMETRY_SCHEMA, HARNESS_TELEMETRY_SCHEMA, startAiSpan and startHarnessSpan from it. None of the five symbols exists anywhere in the repository outside that README, and pi-agent-core does not depend on pi-telemetry. Treat the package as an interface to implement against, not a source of Pi spans.

文 档 ≠ 代 码 telemetry/README.md 声称“@earendil-works/pi-agent-core owns and exports the pi AI-request and harness schemas”，并展示了一段从它导入 AGENT_TELEMETRY_SCHEMAS、AI_TELEMETRY_SCHEMA、HARNESS_TELEMETRY_SCHEMA、startAiSpan 和 startHarnessSpan 的 import。这五个符号在那份 README 之外，仓库里任何地方都不存在，而且 pi-agent-core 并不依赖 pi-telemetry。请把这个包当成一个需要你去实现的接口，而不是 Pi span 的来源。

## What the coding agent sends

## 编码智能体会发送什么

Product telemetry lives in the coding agent, not in pi-telemetry. One switch controls it:

产品遥测在编码智能体里，而不在 pi-telemetry 里。它由一个开关控制：

```typescript the install-telemetry switch CA/src/core/telemetry.ts

function isTruthyEnvFlag(value: string | undefined): boolean {
    if (!value) return false;
    return value === "1" || value.toLowerCase() === "true" || value.toLowerCase() === "yes";
}

export function isInstallTelemetryEnabled(
    settings Manager: SettingsManager,
    telemetry Env: string | undefined = process.env.PI_TELEMETRY,
): boolean {
    return telemetry Env !== undefined ? isTruthyEnvFlag(telemetry Env) :
    settingsManager能使EnableInstallTelemetry();
}
```

The whole file except its import. When PI_TELEMETRY is set at all it wins: 1, true or yes turn telemetry on, any other value, including an empty string, turns it of. Unset, the enableInstallTelemetry setting decides; its default is true CA/src/core/settings-manager.ts:1142.

整个文件，除了它的 import。只要 PI_TELEMETRY 有被设置，它就优先：1、true 或 yes 打开遥测，任何其他值（包括空字符串）都会把它关掉。未设置时，由 enableInstallTelemetry 设置决定；默认是 true CA/src/core/settings-manager.ts:1142。

<table><tr><td>WHAT</td><td>WHEN</td><td>GATED BY</td></tr><tr><td>GET https://pi.dev/api/report-install version=with User-Agent: pi/((,5 s 超时，响应被忽略</td><td>交互模式下、新会话开始时，且没有记录过 changelog 版本（全新安装），或 changelog 中有比记录更新的条目 CA/src/modes/interactive/interactive-mode.ts:1324</td><td>PI_OFFLINE 被设为任意值，其次是 isInstallTelemetryEnabled CA/src/modes/interactive/interactive-mode.ts:1351</td></tr><tr><td>OpenRouter headers HTTP-Referer:https://pi.dev,X-OpenRouter-Title: pi,X-OpenRouter-Categories: cli-agent</td><td>每次对 OpenRouter 模型的请求</td><td>isInstallTelemetryEnabled CA/src/core/provider-attribution.ts:40</td></tr><tr><td>NVIDIA NIM X-BILLING-INFOKE-ORIGIN: Pi; Cloudflare User-Agent: pi-coding-agent</td><td>每次对这些主机的请求</td><td>isInstallTelemetryEnabled</td></tr><tr><td>OpenCode x-opencode-session:,x-opencode-client: pi</td><td>每次对 opencode、opencode-go 或 opencode.ai 的请求</td><td>不受开关控制 CA/src/core/provider-attribution.ts:67</td></tr><tr><td>GET https://pi.dev/api/latest-version, 10 s 超时</td><td>交互模式启动时的版本检查</td><td>PI_OFFLINE 或 PI_SKIP_VERSION_CHECK CA/src/utils/version-check.ts:5</td></tr></table>

One ping, three attribution headers, one session header and a version check. Headers from mergeProviderAttributionHeaders(), which merges the request’s own headers last, so they override these; a before_provider_headers extension handler then sees the result CA/src/core/sdk.ts:337. The model-catalog refresh is a separate request covered in providers and models (p. 24).

一次 ping、三个归因头、一个会话头和一次版本检查。这些头来自 mergeProviderAttributionHeaders()，它把请求自身的头放在最后合并，所以会覆盖前面这些；随后 before_provider_headers 扩展处理器看到的就是合并后的结果 CA/src/core/sdk.ts:337。模型目录刷新是另一个请求，见 providers and models (p. 24)。

PI_OFFLINE is tested two ways. main() treats 1, true, yes or --offline as ofline and then sets PI_OFFLINE=1 CA/src/main.ts:576. The install ping and the version check only ask whether the variable is non-empty, so PI_OFFLINE=0 also suppresses them.

PI_OFFLINE 有两种判定方式。main() 把 1、true、yes 或 --offline 视为离线，然后设置 PI_OFFLINE=1 CA/src/main.ts:576。安装 ping 和版本检查只问这个变量是否非空，所以 PI_OFFLINE=0 同样会抑制它们。

enable Analytics defaults to false CA/src/core/settings-manager.ts:1152. Only the first-time setup screen writes it CA/src/cli/startup-ui.ts:193, and that screen runs only with PI_EXPERIMENTAL=1, in the oficial distribution, with the default agent directory and no settings.json yet CA/src/cli/startup-ui.ts:131. Opting in also stores a random trackingId CA/src/core/settings-manager.ts:1160. At 28dcce2 nothing reads either value back: getEnableAnalytics() and getTrackingId() have no caller, and the bug-report bundle strips trackingId and deviceId from the settings it attaches CA/src/core/bug-report.ts:62.

enableAnalytics 默认是 false CA/src/core/settings-manager.ts:1152。只有首次设置界面会写它 CA/src/cli/startup-ui.ts:193，而该界面只在满足以下条件时运行：PI_EXPERIMENTAL=1、官方分发版、使用默认智能体目录、且还没有 settings.json CA/src/cli/startup-ui.ts:131。选择加入还会存下一个随机的 trackingId CA/src/core/settings-manager.ts:1160。在 28dcce2 时没有任何地方把这两个值读回来：getEnableAnalytics() 和 getTrackingId() 都没有调用方，而缺陷报告包会从它附带的设置里剥掉 trackingId 和 deviceId CA/src/core/bug-report.ts:62。

R U L E O F T H U M B
经 验 之 握
For a machine that must not call home, set PI_OFFLINE=1 and PI_TELEMETRY=0. The first stops the ping, the version check, catalog refreshes and package auto-installs; the second removes the attribution headers. Neither removes the OpenCode session header, which goes only to OpenCode.

对于一台不得回连的机器，请设置 PI_OFFLINE=1 和 PI_TELEMETRY=0。前者挡住 ping、版本检查、目录刷新和包自动安装；后者去掉归因头。两者都去不掉 OpenCode 会话头，它只发给 OpenCode。

## Evals

## 评测

packages/evals is @earendil-works/pi-evals, marked private and never published evals/package.json. It is built on vitest-evals 0.15.0 and runs real, in-process AgentSessions. The harness creates services with createAgentSessionServices and a session with createAgentSessionFromServices evals/src/harness.ts:337, after pointing HOME, USERPROFILE and PI_CODING_AGENT_DIR at a fresh temporary directory evals/src/harness.ts:82. Each run gets its own home, agent directory, workspace and session directory under one mkdtemp("pi-eval-") root evals/src/harness.ts:283. The provider credential is copied from the host’s auth.json into an in-memory store, and the run fails with “Isolated eval loaded unexpected extensions” if anything other than its own inline extensions loads evals/src/harness.ts:362.

packages/evals 就是 @earendil-works/pi-evals，标记为私有、从不发布 evals/package.json。它基于 vitest-evals 0.15.0 构建，并运行真实的、进程内的 AgentSession。评测骨架先用 createAgentSessionServices 创建服务、再用 createAgentSessionFromServices 创建会话 evals/src/harness.ts:337，此前它会把 HOME、USERPROFILE 和 PI_CODING_AGENT_DIR 指向一个全新的临时目录 evals/src/harness.ts:82。每次运行都在同一个 mkdtemp("pi-eval-") 根目录下获得自己的 home、智能体目录、工作区和会话目录 evals/src/harness.ts:283。供应商凭据从宿主机的 auth.json 复制进一个内存存储；如果加载了除它自己内联扩展之外的任何东西，这次运行就会以“Isolated eval loaded unexpected extensions”失败 evals/src/harness.ts:362。

<table><tr><td>KIND</td><td>FILES</td><td>RUNS</td><td>WHAT IT MEASURES</td></tr><tr><td>Host evals</td><td>evals/*.eval.ts: smoke, documentation-audit</td><td>npm run eval:host，在本机上用 Vitest 跑</td><td>普通的通过或失败；smoke 不给工具地问法国首都，期望答案是 Paris evals/evals/smoke.eval.ts</td></tr><tr><td>Documentation-lift evals</td><td>evals/*.docs.eval.ts:custom-provider, extensions, models, openai-provider,tui</td><td>npm run eval:docs，每条实验臂一个 Docker 容器</td><td>without_docs 与 with_docs 之间的通过率差异</td></tr></table>

Two suites: one checks the agent works, the other checks the docs help. Both need PI_PROVIDER and PI_MODEL, set together or not at all evals/src/cli.ts:76. PI_EVAL_RUNS_PER_VARIANT or --runs-per-variant sets repetitions; the default is one evals/src/cli.ts:79.

两个套件：一个检查智能体能不能干活，另一个检查文档有没有帮助。两者都需要 PI_PROVIDER 和 PI_MODEL，要么一起设置，要么都不设 evals/src/cli.ts:76。PI_EVAL_RUNS_PER_VARIANT 或 --runs-per-variant 设置重复次数；默认是 1 evals/src/cli.ts:79。

The without_docs image omits the coding agent’s README.md, CHANGELOG.md, docs/ and examples/, and the harness cuts the “Pi documentation” section out of the default system prompt; it throws if the prompt has no such section evals/src/harness.ts:498. with_docs keeps both. Documentation evals allow only read, write, edit, grep, find and ls evals/src/harness.ts:485, so the model has no shell. Inside the container the harness drops to an unprivileged UID, after which eval definitions and graders are unreadable evals/README.md §Documentation variants.

without_docs 镜像去掉了编码智能体的 README.md、CHANGELOG.md、docs/ 和 examples/，评测骨架还把默认系统提示词中的“Pi documentation”一节剪掉；如果提示词里没有这一节，它就抛异常 evals/src/harness.ts:498。with_docs 两者都保留。文档评测只允许 read、write、edit、grep、find 和 ls evals/src/harness.ts:485，所以模型没有 shell。在容器内部，评测骨架会降权到一个非特权 UID，此后评测定义和评分器都读不到 evals/README.md §Documentation variants。

F I G . 7 . 8 O N E D O C U M E N T A T I O N C O M P A R I S O N

图 7.8 一次文档对比

![](images/7be34716cded2340d71d0b1627a3db0234a915a600412e9d956458aaa64ee32c.jpg)

A comparison either has every pair or reports no headline number. A pair counts only when both arms produce exactly one score; missing, duplicate, skipped or errored arms block it, and the process exits non-zero. Order alternates by run number to reduce order bias. From evals/README.md §Run documentation comparisons and §Results.

一次对比要么拥有全部配对，要么不报告任何头条数字。只有当两条实验臂都恰好产出一个分数时，这一对才计入；缺失、重复、跳过或出错的实验臂都会挡住它，进程以非零码退出。顺序按运行编号交替，以减少顺序偏差。摘自 evals/README.md §Run documentation comparisons 和 §Results。

Results go to an ignored .eval/<timestamp>_<id>/ directory: protocol.json with model, image ids, cases and a protocol digest; expected-runs.json; observations.jsonl; per-arm tasks/*/vitest.json; native Pi sessions under <variant>/sessions/*/session.jsonl; and report.json plus report.txt evals/README.md §Results. “Artifacts may contain prompts, responses, generated code, and tool output.”

结果写入一个被忽略的 .eval/<timestamp>_<id>/ 目录：protocol.json，含 model、镜像 id、用例和一个协议摘要；expected-runs.json；observations.jsonl；每条实验臂的 tasks/*/vitest.json；位于 <variant>/sessions/*/session.jsonl 的原生 Pi 会话；还有 report.json 和 report.txt evals/README.md §Results。“Artifacts may contain prompts, responses, generated code, and tool output.”

W H A T T H I S M E A N S F O R Y O U

这 对 你 意 味 着 什 么

Supply your own TelemetryContext adapter if you want traces; Pi will not emit spans into it at 1.0.4.

如果你想要链路追踪，就自己提供 TelemetryContext 适配器；在 1.0.4 里 Pi 不会往它里面发 span。

Set PI_TELEMETRY=0, or enableInstallTelemetry: false, to stop the install ping and attribution headers.

设置 PI_TELEMETRY=0 或 enableInstallTelemetry: false，以停掉安装 ping 和归因头。

Copy the eval harness pattern — fresh home, agent directory and workspace per run, no unexpected extensions — when you test your own extensions against a real model.

当你用自己的扩展对着真实模型做测试时，照抄评测骨架那套做法——每次运行全新的 home、智能体目录和工作区，不允许出现意外的扩展。

Sources: telemetry/README.md (intro, §Pi Package Integration); telemetry/src/index.ts, noop.ts, memory.ts, testing/index.ts; ai/src/types.ts (ProviderRequestOptions.telemetry Context); ai/src/api/simple-options.ts; grep of packages/*/src for start Span and the five README symbols; CA/src/core/telemetry.ts; CA/src/core/provider-attribution.ts; CA/src/core/settings-manager.ts (enableInstallTelemetry, enable Analytics, trackingId); CA/src/modes/interactive/interactive-mode.ts (getChangelogForDisplay, reportInstallTelemetry); CA/src/utils/versioncheck.ts; CA/src/main.ts (offline mode); CA/src/cli/startup-ui.ts (shouldRunFirstTimeSetup); CA/src/core/bug-report.ts; evals/package.json; evals/README.md; evals/src/harness.ts, cli.ts, docker.ts; evals/evals/smoke.eval.ts, documentationaudit.eval.ts

来源：telemetry/README.md（前言、§Pi Package Integration）；telemetry/src/index.ts、noop.ts、memory.ts、testing/index.ts；ai/src/types.ts（ProviderRequestOptions.telemetryContext）；ai/src/api/simple-options.ts；对 packages/*/src 中 startSpan 和那五个 README 符号的 grep；CA/src/core/telemetry.ts；CA/src/core/provider-attribution.ts；CA/src/core/settings-manager.ts（enableInstallTelemetry、enableAnalytics、trackingId）；CA/src/modes/interactive/interactive-mode.ts（getChangelogForDisplay、reportInstallTelemetry）；CA/src/utils/version-check.ts；CA/src/main.ts（离线模式）；CA/src/cli/startup-ui.ts（shouldRunFirstTimeSetup）；CA/src/core/bug-report.ts；evals/package.json；evals/README.md；evals/src/harness.ts、cli.ts、docker.ts；evals/evals/smoke.eval.ts、documentation-audit.eval.ts