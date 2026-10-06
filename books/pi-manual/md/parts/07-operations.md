The packages behind PI_EXPERIMENTAL, the trust boundaries,

and what Pi reports about itself.

## 7.1 The experimental stack

Six packages at 1.0.4 sketch a Pi that survives crashes, runs tools on other machines and serves many clientsfrom one socket. The stable \`pi\` command uses none ofthem, and npm users cannot reach the code that wires them together.

The packages are pi-durable, pi-env, chord, pi-protocol, pi-server and pi-client. Together they hold 32,038 nonblank source lines, more than a third of the size of the coding agent itself research/out/stats.txt §package-lines. This section shows how the pieces fit into one process topology, then takes each package in turn: what it stores, what it puts on the wire, and the limits it enforces. the monorepo in one page (p. 11) shows how the build keeps this code out of the npm package; this section starts where that one stops, at PI_EXPERIMENTAL=1 in a source checkout.

## How to reach it

The experimental entry point is CA/src/experimental/cli.ts. It calls runExperimentalCommand(args) and falls through to the ordinary main() when that returns false CA/src/experimental/cli.ts:8. The function returns false unless PI_EXPERIMENTAL is exactly "1" and the first argument is server or client CA/src/experimental/commands.ts:86. Its doc comment states the boundary: “Development-only command dispatch. Published entrypoints must not import this module.”

Three facts keep the code out of a normal install. tsconfig.build.json excludes src/client, src/experimental and src/cli/experimental from compilation CA/tsconfig.build.json:19. pi-client, pi-protocol and pi-server are only dev Dependencies of the coding agent CA/package.json:78. And the consumer smoke test fails a release if the published package contains dist/experimental or if any of those three packages resolves scripts/coding-agent-consumer.mjs:82. From a checkout, ./pi-test.sh runs the source entry point under a TypeScript resolver pi-test.sh:

start a server and attach a client from source CA/src/experimental/services/README.md

B A S H

PI_EXPERIMENTAL=1 ./pi-test.sh server PI_EXPERIMENTAL=1 ./pi-test.sh client

Copied from the services README. pi server takes --server-id, --session-dir, --provider, --model, repeatable -e and --auth-token or --authtoken-file; pi client adds --connect, --session-id, -c/--continue and -r/--resume CA/src/cli/experimental/commands/server.ts CA/src/cli/experimental/commands/client.ts.

Two smaller programs under CA/src/experimental/ use pi-durable without the server. durable/main.ts is a oneprocess durable coding agent with its own TUI, and vacation/main.ts is the same harness with a vacation-planner prompt in place of the coding tools CA/src/experimental/durable/README.md CA/src/experimental/vacation/README.md. Neither checks PI_EXPERIMENTAL.

## One process topology

![](images/ce6a526c84f25ac800d34f38b61688360349cc66257d68966f842b9f0c379c78.jpg)
The server routes; only the session worker runs the agent. One pi server process accepts clients on a private Unix socket and hands session calls to a worke process, which owns the durable Harness and its SQLite file. Hatched boxes are parts that are of or unused in a default run. Process roles from CA/src/experimental/process.ts:8; schematic.

The three roles are coordinator, server and session-worker CA/src/experimental/process.ts:8. The server keeps each session in its own directory: meta.json holds the id, creation time and working directory, and session.sqlite is the pidurable storage. “The Session worker locks the directory, opens the storage, and owns it until it retires”

CA/src/experimental/services/README.md. Session directories default to <agent dir>/experimental/sessions CA/src/experimental/server.ts:69. The socket directory defaults to PI_SERVER_DIR or \~/.pi/server CA/src/experimental/server.ts:55. The server creates it with mode 0700 and refuses a directory owned by another user CA/src/experimental/server.ts:58.

The server also starts a RadiusRelayHost after the coordinator connects CA/src/experimental/server.ts:609. It dials wss://…/v1/session-relays/<serverId>/connect on the Radius gateway CA/src/experimental/radius-relay.ts:619 when it finds a token from --auth-token, --auth-token-file or a stored /login radius credential, and it stays local when PI_OFFLINE is set or no token exists CA/src/experimental/radius-auth.ts:36. A client reaches such a server with -- connect radius://<serverId> CA/src/cli/experimental/command-options.ts:47.

#### pi-durable: commit first, show second

The README opens with the contract: “Conversations, model turns, tool calls, and your own state are committed to storage before anything is shown. If the process dies mid-turn, reopening the storage picks the work up where it stopped” durable/README.md. The normative text is durable/docs/spec.md, 4,692 lines, titled “Pico5 specification”. It lists eight required invariants; the first three are “One Session commit is atomic across all record and document writes”, “A document update is published only after its storage commit succeeds” and “All visible progress is durable. There is no volatile publication path” durable/docs/spec.md §1.

A Session owns one mutation line. Storage.commit(writes, context) persists one batch atomically and resolves to a Seq durable/src/types.ts:997. Five record kinds sit on that line: conversations, immutable entries, tasks, submissions and documents. The built-in entry types are pi.user, pi.assistant, pi.tool-result, pi.system, pi.reset and

pi.compactiondurable/src/entries.ts. The built-in documents are pi.agent, pi.provider, pi.live, pi.inbox and pi.usage.

Recovery is not replay of an event log; a “Session-kernel semantic event journal” is a listed non-goal durable/docs/spec.md §13. Each task resumes from its last committed checkpoint:

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

A TaskOutcome is completed, failed, aborted, orphaned or faulted durable/src/types.ts:449. Every phase handler “must commit a changed checkpoint or a terminal outcome through runtime.commit(); returning without durable progress faults the task” durable/src/types.ts:148. Abort runs bottom-up: “An abort invocation of a task starts only once its ordinary owned work is no longer live” durable/docs/spec.md §5.

<table><tr><td>TASK</td><td>PHASES</td><td>WHAT IT COMMITS</td></tr><tr><td>pi.generation durable/src/harness/generation.ts:115</td><td>prepare → request → retry · poll · tools, plus abort</td><td>pi.system entries only when the planned prompt or tools differ from what the transcript replays durable/src/harness/prompt.ts:66; partial output; the pi.assistant entry</td></tr><tr><td>pi.tool durable/src/harness/tool.ts:50</td><td>call, execute (recovery only), plus abort</td><td>intent { phase: &quot;execute&quot;, arguments, replay } before running, then pi.tool-result</td></tr><tr><td>pi.compaction durable/src/harness/compaction.ts:103</td><td>select → summarize → retry, plus abort</td><td>a pi.compaction entry with the summary</td></tr></table>

Three built-in tasks drive a turn. Defaults: compaction reserve Tokens 16,384, keepRecentTokens 20,000, background Tokens 32,768; retries 3 with a 2,000 ms base delay; partial text and tool output committed at most every 100 ms durable/src/harness/agent.ts:19.

The tool task is where durability meets side efects. call resolves the tool, validates, runs before Tool, commits the intent, executes, runs after Tool and appends the result in one handler. Only recovery reaches execute:

![](images/7839da717d9e666fe087061ee79214bfd8bf5e92949b9d3b2628732a5ed56db8.jpg)
A tool runs twice only if two records agree it is safe to. Both the intent stored before the crash and the tool registered after it must say replay: "safe"; replay defaults to "unsafe" durable/src/harness/types.ts:215. Row 4 records a failed outcome, so conversations the call owned are aborted. From ToolTask.execute durable/src/harness/tool.ts:94.

The built-in CodingTools (read, write, edit, bash and the rest under durable/src/tools/) set no replay, so a crash midcall always interrupts them. Hooks get the same treatment: they “run in extension order of the line; a crash before the consuming commit may rerun them” durable/docs/spec.md §7.2. A hook that must decide once can record its decision with memo(name, candidate), which “is one gated commit” durable/docs/spec.md §5; hooks and the asking task share the same memos durable/src/harness/types.ts:604. The hooks are before Request, after Response, onYield and after Tools on generation, before Tool and after Tool on tools, and before Compact on compaction.

Submissions are idempotent by request id: a second submit() with the same requestId returns the existing submission durable/src/harness/submissions.ts:155.

<table><tr><td>BACKEND</td><td>OPENED WITH</td><td>DURABILITY</td></tr><tr><td>Memory</td><td>new MemoryStorage()</td><td>nothing persisted</td></tr><tr><td>SQLite</td><td>openNodeSqliteStorage(file)</td><td>PRAGMA journal_mode = WAL, synchronous = NORMAL durable/src/storage/sqlite/node.ts:190: “commits survive process crashes; the newest may be lost on power or host failure”</td></tr><tr><td>JSONL</td><td>openNodeJsonlStorage(directory, context)</td><td>append-only files; { fsync: true } flushes before each commit marker, default off durable/src/storage/jsonl/storage.ts:256</td></tr></table>

Three backends, one owner each. “One process owns a storage at a time; there is no cross-process locking” durable/README.md §Storage. The experimental server supplies that lock with proper-lockfile in each session worker.

Tools reach the machine through an ExecutionEnv, which is FileSystem plus Shell durable/src/env/index.ts:324. Its operations return Result<T, E>, { ok: true, value } | { ok: false, error }, instead of throwing durable/src/env/index.ts:4. The local implementation is NodeExecutionEnv, whose id is "node:local" durable/src/env/node.ts:605.

#### pi-env: tools on another machine

pi-env is a second ExecutionEnv: “an agent’s tools run on another machine, usually over SSH, while the Durable worker, its storage and credentials stay local” env/README.md. Nothing in the repository imports it outside its own tests. The remote half is a Rust daemon in env/daemon/, 4,027 lines in 13 .rs files. The README says the package ships it prebuilt in bin/ for Linux, macOS, Android (Termux) and Windows on x86-64 and arm64; bin/ is a build output and is absent from the checkout.

The client spawns the daemon with serve --token <hex> env/src/connection.ts:268 and discards everything on stdout before the line PI-ENV <token>, so shell start-up noise cannot corrupt the stream env/src/connection.ts:329. After that, stdout carries only frames:

![](images/b9d93515b8f4348142636b5982bdeb23e236465fb3bf98a0d4b967d462dba0ac.jpg)

JSON says what to do; raw bytes carry file contents and output. A frame shorter than 9 bytes or longer than 16 MiB ends the connection as “Corrupt frame from pi-env” env/src/connection.ts:345. Layout from env/docs/protocol.md §Frames; schematic, not to scale.

Each side sends ping every 5 s. “The daemon kills every process group it started and exits after 30 seconds without receiving any bytes, or when stdin ends” env/docs/protocol.md §Liveness. The client gives up on a connection after the same 30 s of silence env/src/connection.ts:15.

ssh Arguments() builds the ssh command line env/src/ssh.ts:77. It passes -T -a -x and sets BatchMode=yes, ClearAllForwardings=yes, ForwardAgent=no, ForwardX11=no, ControlMaster=no, ControlPath=none, RemoteCommand=none, PermitLocalCommand=no, SendEnv=-*, StrictHostKeyChecking=yes, a caller-supplied

UserKnownHostsFile, GlobalKnownHostsFile=none and a fixed HostKeyAlias. Host keys are accepted once, out of band, through scanHostKey() and acceptHostKey().

The daemon file on the remote is named pi-env-<first 32 hex digits of its SHA-256> env/src/ssh.ts:371. deploy Daemon() hashes the remote file before each start and uploads only when it is missing or diferent; an upload whose hash does not match is deleted with “pi-env upload is corrupt” env/src/ssh.ts:396.

#### chord: the composition runtime

Despite its name, chord has nothing to do with key chords. “Chord is an application-composition runtime for systems assembled from plugins/extensions”, and “it is not a Pi package: it does not depend on any other Pi workspace package” chord/README.md. Its parts:

Facets: synchronous setup units. A facet calls env.use(), env.observe(), env.provide() and env.provide Many() chord/src/types.ts:281; the host builds the dependency graph from those calls, activates providers before consumers and disposes in reverse order.

Services: typed tokens in mode "singleton" or "keyed" chord/src/types.ts:123, process-local or published to remote consumers. Arguments, results, snapshots and updates must be strict JSON.

Replicated state: change(context, draft => …) publishes one revision chord/src/services/state.ts:202. Replicas receive delta operations.

Control service: \$chord.service with members catalogue, subscribe and unsubscribe chord/src/services/wire.ts:40. A subscriber holds at most 100 bufered updates; the 101st replaces the bufer with one reset snapshot chord/src/services/provider.ts:453.

Context: “a Go-like context system for cancellation and invocation-scoped application values” chord/README.md, with BACKGROUND_CONTEXT, TODO_CONTEXT, withAbortSignal, with Cancel and withContextValue

chord/src/context/index.ts:55.

```typescript the seven delta operations chord/src/delta/index.ts TS
export type 0p =
    | readonly ["r", JsonValue]
    | readonly ["s", NonEmptyPath, JsonValue]
    | readonly ["d", NonEmptyPath]
    | readonly ["a", NonEmptyPath, string]
    | readonly ["t", NonEmptyPath, number]
    | readonly ["p", Path, number, number, JsonValue[])
    /** Reorder an array in place: `new[i] = old[permutation[i]]\'. */
    | readonly ["m", Path, number[]];
```

Complete, from line 32. Replace root, set, delete, string append, string front-truncate, array splice, permutation. String append is what makes a streamed answer cheap to replicate.

The Node bundler builds each facet entry with esbuild into one CommonJS file named facet-<12 hex>-[hash].cjs and records a sha256-… integrity value chord/src/node/bundle.ts:88. The loader recomputes the hash before compiling the source with node:vm and fails with “Facet bundle integrity check failed” on mismatch chord/src/node/bundle-loader.ts:231. FacetHost.reload() swaps facets at run time chord/src/facets/host.ts:423; the server’s /reload uses it.

## pi-protocol, pi-server, pi-client

PROTOCOL_VERSION is 8 protocol/src/protocol.ts:5, and the README is blunt: “The protocol is experimental and has no compatibility guarantees” protocol/README.md:41. A frame is a 4-byte unsigned big-endian length and one definite-length CBOR item from the package’s own codec. Default limits are 16 MiB per frame protocol/src/framing.ts:6, 1,000,000 array elements or map entries, and 64 nesting levels protocol/README.md:41 protocol/src/cbor/options.ts:8.

```javascript
FIG. 7.4 CLIENT HELLO, BYTE BY BYTE
25 BYTES ENCODED BY ENCODECLIENTMESSAGE({ TYPE: "HELLO", VERSION: 8 })
```

<table><tr><td>length00 00 00 15 = 21</td><td>a2map</td><td>&quot;type&quot;64 74 79 70 65</td><td>&quot;hello&quot;65 68 65 6c 6c 6f</td><td>&quot;version&quot;67 ... 6e</td><td>088</td></tr><tr><td>0</td><td>4</td><td>5</td><td>10</td><td>16</td><td>2425</td></tr></table>

The first frame of every connection is 25 bytes. A CBOR map of two text keys and the protocol version as a one-byte integer. The server answers with the same map plus serverId, 72 bytes for a UUID. Real bytes from the pinned build, encoded by research/capture/experimental-stack-frames.mjs into research/out/experimental-stack-frames.txt; drawn to scale.

Envelopes are TypeBox objects with additional Properties: false, so an extra field fails validation; the capture shows “Invalid client protocol message” for a hello with one extra key research/out/experimental-stack-frames.txt.

<table><tr><td>DIRECTION</td><td>TYPE</td><td>FIELDS</td></tr><tr><td>client → server</td><td>hello</td><td>version — must be the first frame</td></tr><tr><td>client → server</td><td>request</td><td>id, target, call</td></tr><tr><td>client → server</td><td>cancel</td><td>id, target</td></tr><tr><td>server → client</td><td>hello</td><td>version (literal 8), serverId</td></tr><tr><td>server → client</td><td>hello_error</td><td>error {code, message}</td></tr><tr><td>server → client</td><td>response</td><td>id, ok: true, result? or ok: false, error</td></tr><tr><td>server → client</td><td>service_update</td><td>subscriptionId, update</td></tr><tr><td>server → client</td><td>attachment</td><td>a session target, or null</td></tr></table>

Eight envelope types, and the payloads are opaque. target is {serverId} or {serverId, sessionId, attachmentId}, and serverId must be a lowercase UUIDv4. call and result are Chord values that pi-protocol checks only for strict JSON. From protocol/src/protocol.ts.

pi-server listens on a Unix domain socket only; there is no HTTP or WebSocket listener in the package. The socket path is <dir>/<serverId>.sock server/src/transports/unix/address.ts:8 with mode 0600 server/src/transports/unix/listener.ts:11. A client that does not finish the handshake within 5 s is dropped with “Handshake timeout” server/src/server.ts:42. The error codes are wrong_server, session_not_found, session_ambiguous, session_not_attached and server_draining server/src/errors.ts:5. The server does not wrap AgentSession: the session worker imports Harness from pi-durable and opens openNodeSqliteStorage CA/src/experimental/sessionworker.ts:15.

pi-client exports Client, createClientServiceTransport (the Chord adapter) and three error classes client/src/index.ts; discoverUnixServers() scans a server directory client/src/unix.ts:37. It “never reconnects or replays requests automatically”; the application calls reconnect(), attaches again and repeats only what it knows is safe client/README.md:34.

W H A T T H I S M E A N S F O R Y O U

Do not plan an integration on pi server: it is absent from npm and the binary, and protocol 8 promises no compatibility.

Embed pi-durable directly if you need crash-safe turns today; declare replay: "safe" only on tools you can run twice.

Give every durable storage exactly one owning process; the package will not stop a second one.

For pi-env, accept the host key out of band once, then let the content-addressed daemon redeploy itself.

The Pi Durable Technical Manual, a separate book in this series written against pi@5b6c792 and npm 1.0.3, covers pi-durable at length: commits, tasks, documents, observation and recovery. This section stays at the depth the coding agent needs.

Sources: CA/src/experimental/cli.ts; CA/src/experimental/commands.ts (runExperimentalCommand); CA/src/cli/experimental/commands/server.ts, client.ts, command-options.ts (parseTransportAddress); CA/src/experimental/server.ts (resolveServerDirectory, ensurePrivateServerDirectory, resolveSessionDirectory, startForegroundServer); CA/src/experimental/process.ts; CA/src/experimental/radius-auth.ts, radius-relay.ts; CA/src/experimental/session-worker.ts; CA/src/experimental/services/README.md, durable/README.md, vacation/README.md; CA/tsconfig.build.json; CA/package.json; scripts/coding-agent-consumer.mjs; pi-test.sh; durable/README.md; durable/docs/spec.md §1, §5, §7.2, §13; durable/src/types.ts (TaskState, TaskOutcome, PhaseHandler, Storage); durable/src/entries.ts; durable/src/harness/{generation,tool,compaction,agent,prompt,submissions,types}.ts; durable/src/storage/sqlite/node.ts, jsonl/storage.ts; durable/src/env/index.ts, node.ts; env/README.md; env/docs/protocol.md; env/src/connection.ts, ssh.ts (ssh Arguments, deploy Daemon); chord/README.md; chord/src/types.ts; chord/src/delta/index.ts; chord/src/services/{wire,provider,state}.ts; chord/src/node/bundle.ts, bundle-loader.ts; chord/src/facets/host.ts; chord/src/context/index.ts; protocol/README.md; protocol/src/{protocol,framing}.ts, cbor/options.ts; server/src/{server,errors}.ts, transports/unix/{address,listener}.ts; client/README.md; client/src/index.ts, unix.ts; research/capture/experimental-stack-frames.mjs; research/out/experimental-stack-frames.txt; research/out/stats.txt

## 7.2 Security model

Pi runs every tool call with your account's permissions and asks for no approval. Project trust decides which files in a folder may configure Pi; it does not decide what the model may do once Pi is running.

A repository you cloned this morning contains .pi/extensions/, an AGENTS.md and a test script. Starting Pi in it can run three kinds of code: the extension, whatever the model decides to run after reading AGENTS.md, and the script the model calls. This section shows which of the three Pi gates and how. It quotes Pi’s own security stance, follows the project-trust decision through the code, compares the isolation options the docs ofer, and lists the controls inside individual components.

## The stance

The shipped guide begins with one rule: “Treat model-generated commands and code as untrusted. Pi can read, change, and execute files with the permissions of the account that started it, and it does not ask for approval before every tool call” CA/docs/security.md. Extensions, package installers, language servers and other child processes “run with those same permissions unless an operating-system or virtualization boundary restricts them”. The guide names what is not a boundary: “Watching the transcript, using project trust, and reviewing changes do not create a security boundary.”

The repository’s SECURITY.md draws the reporting line in the same place: “Pi treats the local user account and files writable by that account as inside the same trust boundary as the Pi process itself” SECURITY.md. In the guide’s words, prompt injection, the lack of a built-in sandbox and behaviour of user-installed extensions are “generally outside the security boundary unless the report demonstrates a privilege-boundary bypass or access that the local user did not already have” CA/docs/security.md §Report a security issue. Reports go to security@earendil.com or a private GitHub advisory SECURITY.md.

The working folder does not confine anything either: it “controls resource discovery and the default location for tools, but it does not prevent commands from accessing other paths available to the Pi process” CA/docs/security.md.

## Project trust

Project trust is a startup gate on configuration. A folder needs a decision when it has any of eight entries under .pi/ — settings.json, mcp.json, extensions, skills, prompts, themes, SYSTEM.md, APPEND_SYSTEM.md CA/src/core/trustmanager.ts:30 — or a .agents/skills directory in the folder or any ancestor. \~/.agents/skills itself is a user resource and never triggers it CA/src/core/trust-manager.ts:186. A bare .pi directory needs no decision.

![](images/f7498fd8abdc748fe05b41b07c06d5704ce755243e46be4d7584681056404770.jpg)
The first row that answers decides, and every path without an answer ends untrusted. Order from resolveProjectTrusted() CA/src/core/projecttrust.ts:46. The command-line override is checked before the resource scan, so --no-approve applies even in a folder with nothing to protect. Rows 3–6 run only when protected resources exist.

Row 3 runs before any project code loads. loadProjectTrustExtensions() forces the project untrusted and loads the user, global and command-line extensions plus SDK factories, so project-local extensions cannot vote on their own trust CA/src/core/resource-loader.ts:501. Built-in extensions wait for the final pass, because “project settings can disable them, and a loaded extension cannot be unloaded” CA/src/core/resource-loader.ts:683. The handler loop returns the first "yes" or "no"; a handler that throws is reported and skipped CA/src/core/extensions/runner.ts:295.

The trust store is trust.json in the agent directory CA/src/core/trust-manager.ts:214, a JSON object from canonical directory paths to true or false. Lookup walks from the folder up to the root and takes the first explicit value CA/src/core/trustmanager.ts:45. Reads and writes hold a proper-lockfile lock on trust.json.lock. The interactive prompt reads “Trust project folder?” and ofers five choices:

<table><tr><td>CHOICE</td><td>DECISION</td><td>WRITTEN TO trust.json</td></tr><tr><td>Trust</td><td>trusted</td><td>this folder → true</td></tr><tr><td>Trust parent folder (...)</td><td>trusted</td><td>parent → true; this folder&#x27;s own entry removed</td></tr><tr><td>Trust (this session only)</td><td>trusted</td><td>nothing</td></tr><tr><td>Do not trust</td><td>untrusted</td><td>this folder → false</td></tr><tr><td>Do not trust (this session only)</td><td>untrusted</td><td>nothing</td></tr></table>

Two of the five choices leave no record. From getProjectTrustOptions() CA/src/core/trust-manager.ts:67. /trust saves a decision later from inside a session CA/src/core/slash-commands.ts:36.

Print, JSON and RPC modes have no trust prompt. Without an override, an extension answer or a saved decision, they load protected resources only under defaultProjectTrust: "always" CA/src/core/project-trust.ts:86. Use --approve or -- no-approve in automation.

Granting trust loads project settings, project MCP servers, the extensions, skills, prompt templates, themes and system-prompt files under .pi, and project packages. Declining it also blocks the package manager from project package storage: “Project is not trusted; refusing to access project package storage” CA/src/core/package-manager.ts:1777. The npm and git directories under .pi are covered by that check, but their presence alone does not trigger a decision.

Two things escape the gate. Context files — AGENTS.override.md, AGENTS.md, CLAUDE.md and their upper-case variants — load with no trust check; only --no-context-files stops them CA/src/core/resource-loader.ts:642. And the session directory is chosen before trust is resolved, from --session-dir, then PI_CODING_AGENT_SESSION_DIR, then the session Dir setting read by a startup settings manager CA/src/main.ts:688. A project’s .pi/settings.json can therefore move where session files are written even when the project is declined; CA/docs/security.md documents the gap.

Declining trust does not stop a folder from steering the model. AGENTS.md and CLAUDE.md still enter the system prompt, and the model still runs tools with your permissions. Read instructions in an untrusted repository as input, start Pi with -nc if you have not read them, and isolate the process if you have to run the model there.

The example extension CA/examples/extensions/project-trust.ts says “Try it in a project containing .pi, AGENTS.md/CLAUDE.md, or .agents/skills”. A bare .pi, AGENTS.md and CLAUDE.md do not fire project_trust: the event runs only when one of the eight .pi entries or a project .agents/skills exists CA/src/core/trust-manager.ts:186.

## Isolation options

Because Pi has no sandbox of its own, isolation means running it, or some of its tools, somewhere else. CA/docs/containerization.md compares four methods, and the example extensions add two more.

![](images/3f0dd0c72559e01f7ff3da3f9062d1d48cb9e333e7bd3d009ef7cc084e1c17c4.jpg)

Only whole-process isolation contains extensions. Tool-level methods move selected tools out of the host process and leave Pi, its other tools and its environment variables behind. Rows from CA/docs/containerization.md and CA/examples/extensions/{gondolin,sandbox,permissiongate.ts,protected-paths.ts}; schematic.

<table><tr><td>METHOD</td><td>HOW</td><td>WHAT TO WATCH</td></tr><tr><td>Plain Docker</td><td>FROM node:24-bookworm-slim, npm install -g --ignore- scripts @earendil-works/pi-coding-agent; run with -v &quot;$PWD:/workspace&quot; and a named volume for /root/.pi/agent</td><td>env vars passed with -e are visible inside; mounting the host&#x27;s ~/.pi/agent exposes its credentials</td></tr><tr><td>Docker Sandboxes</td><td>sbx run --kit &quot;docker.io/sbx/pi-kit:latest&quot; pi</td><td>the proxy substitutes the real provider key for a placeholder; running /login inside writes a real credential into the sandbox</td></tr><tr><td>NVIDIA OpenShell</td><td>openshell sandbox create --name pi-sandbox --from pi -- pi</td><td>filesystem, process, network, credential and inference policies; a remote gateway does not mount your folder</td></tr><tr><td>gondolin (example)</td><td>pi -e ~/.pi/agent/extensions/gondolin; QEMU micro-VM, Node ≥ 23.6</td><td>&quot;Commands inside the VM inherit the host process environment&quot;, so it is not a credential boundary</td></tr><tr><td>sandbox (example)</td><td>@anthropic-ai/sandbox-runtime 0.0.26 replaces bash; sandbox- exec on macOS, bubblewrap on Linux</td><td>config in ~/.pi/agent/extensions/sandbox.json and .pi/sandbox.json; other tools are unsandboxed</td></tr><tr><td>tool_call gate (example)</td><td>permission-gate.ts asks before rm -rf, sudo and chmod/chown 777, and blocks them without a UI; protected-paths.ts blocks write and edit on paths containing .env, .git/ or node_modules/</td><td>regex and substring rules; a bash command that writes .env, or a dangerous command the patterns miss, passes</td></tr></table>

Six ways to narrow what a wrong action reaches. Commands copied from CA/docs/containerization.md and the example extensions at 28dcce2. The guide calls whole-process isolation “usually the strongest practical option” CA/docs/security.md.

## Controls inside components

The components below each enforce a narrow rule. None of them turns Pi into a sandbox, but each closes a specific hole.

Credentials: auth.json is written with mode 0600 and its directory created with 0700; “the mode applies only on creation so administrator-managed modes and ACLs remain intact” CA/src/core/auth-storage.ts:24. Every read-modify-write holds a proper-lockfile lock. mcp-auth.json uses the same backend CA/src/extensions/mcp/oauth.ts:144. An OAuth refresh that has started ignores cancellation: “the provider may already have rotated the refresh token, so the refresh and its persistence ignore signal and are bounded only by a timeout” ai/src/auth/resolve.ts:105.

MCP configuration: a project .pi/mcp.json loads only when the project is trusted, and it may not set auth: “auth is only allowed in the global mcp.json”, so “a repository cannot pick where the credential goes” CA/src/extensions/mcp/config.ts:133. A server with auth.provider must use https, or http on localhost, 127.0.0.1 or [::1] CA/src/core/mcp-servers.ts:285. oauth.callback Url must be an http loopback URI CA/src/core/mcp-servers.ts:178; oauth.authServerMetadataUrl must be https or loopback http CA/src/core/mcp-servers.ts:201.

MCP OAuth: the flow throws OAuthInsecureEndpointError for a non-loopback endpoint that is not https mcp/src/oauth/flow.ts:121 and OAuthIssuerMismatchError when the returned iss difers from the metadata issuer mcp/src/oauth/flow.ts:373.

MCP processes: stdio servers start through cross-spawn with no shell, detached into their own process group on every platform but Windows, so closing kills the group mcp/src/transports/stdio.ts:101. Values in env and headers pass through resolveConfigValue, where a leading ! runs the rest as a shell command CA/src/core/resolve-config-value.ts:140. A trusted config can therefore execute code when a server connects.

Codemode: scripts run in QuickJS compiled to WebAssembly, “where the only capability is calling injected tools” codemode/README.md. The prelude freezes the built-ins first codemode/src/runtime/prelude-source.ts:28; the coding agent caps VM memory at 256 MiB CA/src/extensions/codemode/execute.ts:55, the worker sets QuickJS’s maximum stack size codemode/src/runtime/worker.ts:59, and the host sets an interrupt flag before terminate() codemode/src/runtime/host.ts:323. Nested calls are real calls through ctx.execute Tool, so tool_call hooks and permission checks apply CA/src/extensions/codemode/tool.ts:7, and “calls made before a failure are not undone” CA/docs/codemode.md.

Experimental stack: durable tools without replay: "safe" never rerun after a crash. pi-env pins host keys under a fixed alias, turns of every forwarding, re-verifies the daemon’s SHA-256 before each start and kills remote process groups after 30 s of silence. pi server binds a 0600 socket in a 0700 directory it owns, and dials a Radius relay only with credentials (the experimental stack (p. 166)).

## Supply chain

The repository’s AGENTS.md sets the rules for contributors and agents: “Treat npm dep and lockfile changes as reviewed code. Direct external deps stay pinned to exact versions.” Installs run with --ignore-scripts, and “New deps with lifecycle scripts require review and an explicit allowlist entry” in scripts/generate-coding-agent-install-lock.mjs AGENTS.md §Dependency and Install Security. At 28dcce2 that allowlist has three entries: @google/genai@2.21.0, esbuild@0.28.2 and protobufjs@7.6.6, each with a one-line justification scripts/generate-coding-agent-install-lock.mjs:17. scripts/check-pinned-deps.mjs enforces exact versions, and a pre-commit check blocks lockfile commits unless PI_ALLOW_LOCKFILE_CHANGE is set scripts/check-lockfile-commit.mjs:5. The Docker recipe above installs Pi with --ignorescripts too.

W H A T T H I S M E A N S F O R Y O U

Decide trust per repository, and remember that a declined project still supplies AGENTS.md.

Pass --approve or --no-approve in CI; non-interactive modes never prompt.

Run Pi in a container or VM when the repository or the task is not yours; tool-level isolation leaves extensions on the host.

Keep provider credentials out of the environment of anything you isolate, or use the Docker Sandboxes proxy.

Review an extension before loading it: it runs inside the Pi process with your permissions.

Sources: CA/docs/security.md; CA/docs/containerization.md; SECURITY.md; AGENTS.md §Dependency and Install Security; CA/src/core/project-trust.ts (resolveProjectTrusted); CA/src/core/trust-manager.ts (TRUST_REQUIRING_PROJECT_CONFIG_RESOURCES, hasTrustRequiringProjectResources, getProjectTrustOptions, ProjectTrustStore); CA/src/core/resource-loader.ts (loadProjectTrustExtensions, loadCurrentExtensionSet, loadProjectContextFiles); CA/src/core/extensions/runner.ts (emitProjectTrustEvent); CA/src/main.ts (session Dir); CA/src/core/package-manager.ts (assertProjectTrustedForScope); CA/examples/extensions/{project-trust.ts, permission-gate.ts, protected-paths.ts, gondolin/, sandbox/}; CA/src/core/auth-storage.ts; ai/src/auth/resolve.ts (refreshStoredOAuthCredential); CA/src/extensions/mcp/config.ts, oauth.ts; CA/src/core/mcp-servers.ts (validateOAuth, auth check); mcp/src/oauth/flow.ts; mcp/src/transports/stdio.ts; CA/src/core/resolve-config-value.ts; codemode/README.md; codemode/src/runtime/{preludesource,worker,host}.ts; CA/src/extensions/codemode/execute.ts, tool.ts; CA/docs/codemode.md; scripts/generate-codingagent-install-lock.mjs; scripts/check-pinned-deps.mjs; scripts/check-lockfile-commit.mjs

## 7.3 Telemetry and evals

Pi ships a span contract that nothing in the repository emits into, and an install ping that is on by default. Its evals measure something else, how much its own documentation helps a modelfinish a task.

Telemetry here means three separate things, and they are easy to confuse. pi-telemetry is a library of interfaces for tracing. Product telemetry is the small amount of data the coding agent sends to pi.dev and to providers. Evals are a private package that runs real agent sessions against a model and scores the result. This section takes them in that order, says exactly what leaves the machine and when, and ends with how an eval run is isolated and reported.

#### pi-telemetry: a contract with no producer

The package describes itself as “vendor-neutral telemetry contracts and typed schema utilities”, with “no exporter, global current-span state, or dependency on a telemetry backend” telemetry/README.md:11. It is 935 lines including the conformance suite, and it reads no environment variables: a grep of telemetry/src for process.env finds nothing.

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

Spans are callback-scoped: a span exists only inside the start Span callback, and a span is itself a context for child spans. Around that contract the package exports NOOP_TELEMETRY_CONTEXT telemetry/src/noop.ts:20, the reference InMemoryTelemetryContext telemetry/src/memory.ts:192, schema helpers defineTelemetrySchema and createTypedSpanStarter telemetry/src/index.ts:72, and an adapter conformance suite at @earendil-works/pitelemetry/testing telemetry/src/testing/index.ts:1.

pi-ai accepts a context as telemetry Context on every provider request, “explicit parent context for telemetry produced by this logical request” ai/src/types.ts:136, and copies it into simple-stream options ai/src/api/simple-options.ts:48. That is the whole integration. A grep of all fourteen packages outside telemetry/ for start Span finds no call, so a context passed to piai receives no spans.

```txt
FIG. 7.7 WHAT THE TELEMETRY README DESCRIBES, AND WHAT EXISTS COMPARISON
PI-TELEMETRY TelemetryContext · TelemetrySpan NOOP · InMemory · schemas · conformance exporter none, by design
PI-AI telemetry Context?: TelemetryContext accepted on requests and passed along start Span calls none in the repository
PI-AGENT-CORE AGENT_TELEMETRY_SCHEMA · AI_TELEMETRY_SCHEMA · HARNESS_TELEMETRY_SCHEMA · startAiSpan · startHarnessSpan named in the README; not defined anywhere at 28dcce2
```

The contract is complete; the producers are missing. Solid: code that exists. Hatched rose: what a reader of telemetry/README.md §Pi Package Integration expects and will not find. From greps of packages/*/src at 28dcce2; schematic.

D O C ≠ C O D E telemetry/README.md says “@earendil-works/pi-agent-core owns and exports the pi AI-request and harness schemas” and shows an import of AGENT_TELEMETRY_SCHEMAS, AI_TELEMETRY_SCHEMA, HARNESS_TELEMETRY_SCHEMA, startAiSpan and startHarnessSpan from it. None of the five symbols exists anywhere in the repository outside that README, and pi-agent-core does not depend on pi-telemetry. Treat the package as an interface to implement against, not a source of Pi spans.

## What the coding agent sends

Product telemetry lives in the coding agent, not in pi-telemetry. One switch controls it:

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

<table><tr><td>WHAT</td><td>WHEN</td><td>GATED BY</td></tr><tr><td>GET https://pi.dev/api/report-install version=with User-Agent: pi/((,5 s timeout, response ignored</td><td>interactive mode, on a new session, when no changelog version is recorded (fresh install) or the changelog has entries newer than the recorded oneCA/src/modes/interactive/interactive-mode.ts:1324</td><td>PI_OFFLINE set to any value, thenisInstallTelemetryEnabledCA/src/modes/interactive/interactive-mode.ts:1351</td></tr><tr><td>OpenRouter headers HTTP-Referer:https://pi.dev,X-OpenRouter-Title: pi,X-OpenRouter-Categories: cli-agent</td><td>every request to an OpenRouter model</td><td>isInstallTelemetryEnabledCA/src/core/provider-attribution.ts:40</td></tr><tr><td>NVIDIA NIM X-BILLING-INFOKE-ORIGIN: Pi; Cloudflare User-Agent: pi-coding-agent</td><td>every request to those hosts</td><td>isInstallTelemetryEnabled</td></tr><tr><td>OpenCode x-opencode-session:,x-opencode-client: pi</td><td>every request to opencode, opencode-go or opencode.ai</td><td>not gated CA/src/core/provider-attribution.ts:67</td></tr><tr><td>GET https://pi.dev/api/latest-version, 10 s timeout</td><td>interactive start-up version check</td><td>PI_OFFLINE or PI_SKIP_VERSION_CHECKCA/src/utils/version-check.ts:5</td></tr></table>

One ping, three attribution headers, one session header and a version check. Headers from mergeProviderAttributionHeaders(), which merges the request’s own headers last, so they override these; a before_provider_headers extension handler then sees the result CA/src/core/sdk.ts:337. The model-catalog refresh is a separate request covered in providers and models (p. 24).

PI_OFFLINE is tested two ways. main() treats 1, true, yes or --offline as ofline and then sets PI_OFFLINE=1 CA/src/main.ts:576. The install ping and the version check only ask whether the variable is non-empty, so PI_OFFLINE=0 also suppresses them.

enable Analytics defaults to false CA/src/core/settings-manager.ts:1152. Only the first-time setup screen writes it CA/src/cli/startup-ui.ts:193, and that screen runs only with PI_EXPERIMENTAL=1, in the oficial distribution, with the default agent directory and no settings.json yet CA/src/cli/startup-ui.ts:131. Opting in also stores a random trackingId CA/src/core/settings-manager.ts:1160. At 28dcce2 nothing reads either value back: getEnableAnalytics() and getTrackingId() have no caller, and the bug-report bundle strips trackingId and deviceId from the settings it attaches CA/src/core/bug-report.ts:62.

## R U L E O F T H U M B
For a machine that must not call home, set PI_OFFLINE=1 and PI_TELEMETRY=0. The first stops the ping, the version check, catalog refreshes and package auto-installs; the second removes the attribution headers. Neither removes the OpenCode session header, which goes only to OpenCode.

## Evals

packages/evals is @earendil-works/pi-evals, marked private and never published evals/package.json. It is built on vitest-evals 0.15.0 and runs real, in-process AgentSessions. The harness creates services with createAgentSessionServices and a session with createAgentSessionFromServices evals/src/harness.ts:337, after pointing HOME, USERPROFILE and PI_CODING_AGENT_DIR at a fresh temporary directory evals/src/harness.ts:82. Each run gets its own home, agent directory, workspace and session directory under one mkdtemp("pi-eval-") root evals/src/harness.ts:283. The provider credential is copied from the host’s auth.json into an in-memory store, and the run fails with “Isolated eval loaded unexpected extensions” if anything other than its own inline extensions loads evals/src/harness.ts:362.

<table><tr><td>KIND</td><td>FILES</td><td>RUNS</td><td>WHAT IT MEASURES</td></tr><tr><td>Host evals</td><td>evals/*.eval.ts: smoke, documentation-audit</td><td>npm run eval:host, Vitest on this machine</td><td>ordinary pass or fail; smoke asks for the capital of France with no tools and expects Paris evals/evals/smoke.eval.ts</td></tr><tr><td>Documentation-lift evals</td><td>evals/*.docs.eval.ts:custom-provider, extensions, models, openai-provider,tui</td><td>npm run eval:docs, one Docker container per arm</td><td>pass-rate difference between without_docs and with_docs</td></tr></table>

Two suites: one checks the agent works, the other checks the docs help. Both need PI_PROVIDER and PI_MODEL, set together or not at all evals/src/cli.ts:76. PI_EVAL_RUNS_PER_VARIANT or --runs-per-variant sets repetitions; the default is one evals/src/cli.ts:79.

The without_docs image omits the coding agent’s README.md, CHANGELOG.md, docs/ and examples/, and the harness cuts the “Pi documentation” section out of the default system prompt; it throws if the prompt has no such section evals/src/harness.ts:498. with_docs keeps both. Documentation evals allow only read, write, edit, grep, find and ls evals/src/harness.ts:485, so the model has no shell. Inside the container the harness drops to an unprivileged UID, after which eval definitions and graders are unreadable evals/README.md §Documentation variants.

F I G . 7 . 8 O N E D O C U M E N T A T I O N C O M P A R I S O N
![](images/7be34716cded2340d71d0b1627a3db0234a915a600412e9d956458aaa64ee32c.jpg)

A comparison either has every pair or reports no headline number. A pair counts only when both arms produce exactly one score; missing, duplicate, skipped or errored arms block it, and the process exits non-zero. Order alternates by run number to reduce order bias. From evals/README.md §Run documentation comparisons and §Results.

Results go to an ignored .eval/<timestamp>_<id>/ directory: protocol.json with model, image ids, cases and a protocol digest; expected-runs.json; observations.jsonl; per-arm tasks/*/vitest.json; native Pi sessions under <variant>/sessions/*/session.jsonl; and report.json plus report.txt evals/README.md §Results. “Artifacts may contain prompts, responses, generated code, and tool output.”

W H A T T H I S M E A N S F O R Y O U

Supply your own TelemetryContext adapter if you want traces; Pi will not emit spans into it at 1.0.4.

Set PI_TELEMETRY=0, or enableInstallTelemetry: false, to stop the install ping and attribution headers.

Copy the eval harness pattern — fresh home, agent directory and workspace per run, no unexpected extensions — when you test your own extensions against a real model.

Sources: telemetry/README.md (intro, §Pi Package Integration); telemetry/src/index.ts, noop.ts, memory.ts, testing/index.ts; ai/src/types.ts (ProviderRequestOptions.telemetry Context); ai/src/api/simple-options.ts; grep of packages/*/src for start Span and the five README symbols; CA/src/core/telemetry.ts; CA/src/core/provider-attribution.ts; CA/src/core/settings-manager.ts (enableInstallTelemetry, enable Analytics, trackingId); CA/src/modes/interactive/interactive-mode.ts (getChangelogForDisplay, reportInstallTelemetry); CA/src/utils/versioncheck.ts; CA/src/main.ts (offline mode); CA/src/cli/startup-ui.ts (shouldRunFirstTimeSetup); CA/src/core/bug-report.ts; evals/package.json; evals/README.md; evals/src/harness.ts, cli.ts, docker.ts; evals/evals/smoke.eval.ts, documentationaudit.eval.ts
