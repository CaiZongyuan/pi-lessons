Outside tools arrive through MCP and codemode; everything the user sees is drawn by one diferential renderer.

# 6.1 MCP, from mcp.json to tool call

Pi 1.0 ships its own MCP client and registers every server tool in the ordinary tool pipeline. By default the model never sees those tools declared; it reaches them from a codemode script.

A Model Context Protocol server is a process or URL that ofers tools and resources. Pi connects to it without the oficial SDK, names each tool mcp__<server>__<tool>, and runs every call through the same pipeline as read or bash, so tool_call hooks and permission gates apply unchanged. This section shows the two layers that do this and the client’s connect and timeout rules. It then covers the configuration file and its trust rules, the four exposures that decide how the model reaches a tool, and what is retried when a server fails.

## Two layers

The first layer is @earendil-works/pi-mcp 1.0.4, “a small, standalone Model Context Protocol client. It does not depend on the oficial MCP SDK or other pi packages” mcp/README.md. Its one runtime dependency is cross-spawn 7.0.6 mcp/package.json. The OAuth code “is adapted from the MIT-licensed Model Context Protocol TypeScript SDK v1.29.0”, whose licence ships under LICENSES/ mcp/README.md §OAuth.

The second layer is the built-in mcp extension in CA/src/extensions/mcp/. It is registered as a replaceable built-in: an extension that registers /mcp takes over instead of running alongside it CA/src/extensions/index.ts:9. The part that talks to servers loads lazily, so “sessions without servers never pay for it” CA/src/extensions/mcp/index.ts:1021.

<table><tr><td>FILE</td><td>LINES</td><td>OWNS</td></tr><tr><td>index.ts</td><td>1,225</td><td>lifecycle, exposures, the mcp_servers prompt section, /mcp</td></tr><tr><td>cli.ts</td><td>614</td><td>pi mcp add · remove · list · login · logout</td></tr><tr><td>oauth.ts</td><td>532</td><td>sign-in, mcp-auth.json, token refresh</td></tr><tr><td>runtime.ts</td><td>491</td><td>one connection per server, transports, retries</td></tr><tr><td>resources.ts</td><td>339</td><td>the three resource tools</td></tr><tr><td>tools.ts</td><td>335</td><td>tool names, result conversion, the 20 KiB cut</td></tr><tr><td>ui.ts·config.ts·log.ts</td><td>252·242·69</td><td>the /mcp manager, mcp.json, mcp.log</td></tr></table>

The client is a library; everything Pi-specific lives in one extension. Line counts from wc -l at 28dcce2; the two 2-line .lazy.ts loaders are omitted.

## The client

McpClient speaks protocol 2025-11-25 and accepts a server that negotiates 2025-06-18, 2025-03-26 or 2024-11-05 mcp/src/protocol/types.ts:4. It has four states, idle, connecting, connected and closed mcp/src/client.ts:41, and connect() refuses to run in any state but idle mcp/src/client.ts:202.

![](images/7039cba5fca19115d298ab360232334633a70ea889f551d2377a4cf14dfc78f3.jpg)

A server is usable only after the version check and notifications/initialized. A server that picks an unlisted version fails with “MCP server selected unsupported protocol version …” and the client closes. Steps 1–3 are connect(), 4 is list All, 5 is request Internal with progress. From mcp/src/client.ts.

Timeouts. A request times out after 30 s in the library mcp/src/client.ts:38 and after 60 s in Pi, where the per-server timeout key is in seconds CA/src/extensions/mcp/runtime.ts:48. Every progress notification for the request re-arms the timer mcp/src/client.ts:531. On expiry, or when the caller’s signal aborts, the client rejects the request and sends notifications/cancelled; it never cancels initialize, which the spec forbids mcp/src/client.ts:556.

Supported: ping, paginated tools/list, tools/call with structured content, resources and templates, server ping and roots/list requests, logging and list-changed notifications, progress, cancellation and OAuth. “Batch JSON-RPC messages, legacy HTTP+SSE, servers, sampling, and tasks are outside the initial core” mcp/README.md §Supported protocol surface.

<table><tr><td>TRANSPORT</td><td>WHAT IT DOES</td></tr><tr><td>stdio transports/stdio.ts</td><td>cross-spawn with no shell, detached into its own process group on every platform but Windows mcp/src/transports/stdio.ts:101. Close: end stdin; after 500 ms SIGTERM the group; 2 s later SIGKILL. On Windows, taskkill /T /F. An exit hook sends SIGTERM to groups still alive when Pi exits. Keeps the last 64 KiB of stderr.</td></tr><tr><td>Streamable HTTP transports/streamable-http.ts</td><td>POST with accept: application/json, text/event-stream. Captures Mcp-Session-Id and sends it back; DELETE on close. Opens a GET SSE stream after init (405 means none) and reconnects dropped streams with backoff from 1 s to 30 s, 5 tries, resuming with Last-Event-ID. A 401, or a 403 whose challenge says insufficient_scope, goes to the auth provider.</td></tr><tr><td>SSE (legacy)</td><td>Rejected by validation: “legacy SSE transport is not supported; use the streamable HTTP URL” CA/src/core/mcp-servers.ts:270.</td></tr></table>

Two transports, one message cap. Both reject a single message over 16 MiB mcp/src/transports/transport.ts:3. From mcp/src/transports/.

## Configuration

Pi reads mcp.json from the agent directory, \~/.pi/agent/mcp.json, and then .pi/mcp.json in the project, but the project file only when the project is trusted CA/src/extensions/mcp/config.ts:145. Both use the mcp Servers shape other MCP clients use:

```json one stdio server and one HTTP server CA/docs/mcp.md JSON
{
    "mcp Servers": {
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

The entry types live in core, not in the extension, because extensions can also register servers with pi.registerMcpServer() CA/src/core/mcp-servers.ts:1.

Every server — exposure? (default "codemode"), description?, tool Exposure?: Record<string, McpExposure>, enabled? (default true), timeout? in seconds (default 60) CA/src/core/mcp-servers.ts:59.

Stdio — type?: "stdio", command, args?, env?, cwd?. env values can be \${NAME} or !command; a relative cwd resolves against the session directory CA/src/core/mcp-servers.ts:80.

HTTP — type?: "http" ("streamable-http" is also accepted), url, headers?, oauth?: McpOAuthConfig, and auth?: { provider }, which sends the token of a /login provider and requires https except on loopback hosts CA/src/core/mcp-

servers.ts:137.

Server names — must match ^[A-Za-z0-9_-]+\$ CA/src/core/mcp-servers.ts:152. Two names that difer only in - and _ share a namespace, so the second is rejected as conflicting CA/src/extensions/mcp/config.ts:128.

Tool names — mcp__<server>__<tool> with every character outside [A-Za-z0-9_] replaced by _. A name over 64 characters, or one already taken by another MCP tool, is cut and sufixed with _ and 8 hex characters of a SHA-256 of server and tool CA/src/extensions/mcp/tools.ts:84.

The capture kit ran createMcpToolName against the build. dev-radius / list.items becomes mcp__dev_radius__list_items; a 60-character tool on github becomes a 64-character name ending _5204ba68; and a-b on a server where mcp__srv__a_b is taken becomes mcp__srv__a_b_5c15ffbd research/out/mcp-naming.txt.

Merge rules. A project entry with the same name replaces the user entry. A project entry with no command, url or type is an override instead, and it may set only enabled, exposure and tool Exposure of the user entry; anything else is reported as an error CA/src/extensions/mcp/config.ts:108. A project file may not set auth: “Project files cannot use it, so a repository cannot pick where the credential goes” CA/src/extensions/mcp/config.ts:25. The top-level autoEnableCodemode (default true) can sit in either file, and the project value wins CA/src/extensions/mcp/config.ts:28.

## How the model reaches MCP tools

Each tool has one of four exposures: its tool Exposure entry, else the server’s exposure, else codemode. An exact tool name wins over patterns, and among patterns the first match in the object wins CA/src/core/mcp-servers.ts:234. codemodedeferred is accepted as an old alias for codemode CA/src/core/mcp-servers.ts:57.

<table><tr><td>EXPOSURE</td><td>DECLARED TO THE MODEL</td><td>CALLABLE FROM CODEMODE</td><td>TOOL PI ACTIVATES</td></tr><tr><td>codemode (default)</td><td>no</td><td>yes</td><td>codemode, unless autoEnableCodemode is false</td></tr><tr><td>deferred</td><td>after tool_search loads it</td><td>yes</td><td>tool_search</td></tr><tr><td>direct</td><td>yes</td><td>yes</td><td>—</td></tr><tr><td>hidden</td><td>no</td><td>no</td><td>—</td></tr></table>

Three of the four exposures keep the tool out of the request. From the McpExposure doc comment CA/src/core/mcp-servers.ts:43 and ensureDiscoveryActive CA/src/extensions/mcp/index.ts:466. Inside Pi both codemode and deferred map to tool exposure deferred; they difer only in which helper tool is activated CA/src/extensions/mcp/tools.ts:44.

![](images/25b61b2187e661452a7be621bd68873fadf709df090b8c5be78f2b8585461f86.jpg)

Every route ends in the same pipeline and the same connection. Only the first hop difers: a script call, a loaded declaration, or a declared tool. Schematic, from CA/src/extensions/mcp/index.ts (module comment, ensureDiscoveryActive, tool_call handler) and tools.ts (createMcpToolDefinition).

The mcp_servers section. The model learns that a codemode or deferred server exists from a system-prompt section, because neither codemode nor tool_search lists such servers CA/src/extensions/mcp/index.ts:186. Each enabled server gets one line: its namespace, the route, and the first line of its description or, once connected, of its server instructions, up to 250 characters per server and 4,096 for the whole section CA/src/extensions/mcp/index.ts:154. For the docs server above plus the GitHub example from the shipped docs, the build produces:

```txt
MCP servers whose tools are not declared to you. Call the tools of `codemode` servers from codemode scripts.
- mcp_docs (codemode): Search and read the product documentation
- mcp_github (codemode)
```

A third server with only direct tools was passed in and left out, as designed research/out/mcp-naming.txt. The section is set in before_agent_start CA/src/extensions/mcp/index.ts:1062. When it difers from what the transcript already holds, the session appends a system message carrying only the changed sections, so earlier messages are not rewritten CA/src/core/agent-session.ts:1714; from prompt() to agent_settled (p. 67) covers that dif.

Who waits for whom. Servers connect in the background. The first prompt waits up to 10 s, and only for servers with direct tools, since those must be declared in its request CA/src/extensions/mcp/index.ts:93. A codemode script waits for a pending server only if scriptNeedsServer says so: the code contains the server’s namespace, or any of search Tools, describe Namespace, describe Tool or ALL_TOOLS CA/src/extensions/mcp/index.ts:223. tool_search and the resource tools wait for every server CA/src/extensions/mcp/index.ts:1073.

Results. Model-facing text over 20 KiB keeps its start and end around a …N chars truncated… marker, and the full text goes to a temp file named in the result CA/src/extensions/mcp/tools.ts:51. Scripts receive the whole CallToolResult without _meta, never truncated, and a result with isError resolves in a script but is an error result for a direct call

Resources reach the model through list_mcp_resources, list_mcp_resource_templates and read_mcp_resource, “the tools Codex and opencode use” CA/src/extensions/mcp/resources.ts:2. MCP App resources, ui:// URIs or profile=mcpapp HTML, are left out CA/src/extensions/mcp/resources.ts:47.

## Failure, retries and sign-in

<table><tr><td>WHAT FAILED</td><td>WHAT PI DOES</td><td>WHERE</td></tr><tr><td>connect to an HTTP server, transient error</td><td>retries after 250 ms, then after 1,000 ms</td><td>CA/src/extensions/mcp/runtime.ts:362</td></tr><tr><td>connect to a stdio server</td><td>no retry</td><td>same</td></tr><tr><td>tools/call, any HTTP error</td><td>no retry: “they may have run”</td><td>CA/src/extensions/mcp/runtime.ts:297</td></tr><tr><td>any request, session expired (404)</td><td>one retry on a new session</td><td>same</td></tr><tr><td>list or read resources, transient error</td><td>one retry after 250 ms</td><td>same</td></tr><tr><td>connection dropped</td><td>state disconnected; the next call reconnects</td><td>CA/src/extensions/mcp/runtime.ts:53</td></tr></table>

Only requests that cannot have run are retried. “Transient” is HTTP 408, 429, or 500 and above except 501, plus a TypeError from fetch CA/src/extensions/mcp/runtime.ts:70.

OAuth. An HTTP server with no auth and no Authorization header signs in with OAuth CA/src/extensions/mcp/runtime.ts:83. The flow uses PKCE and a loopback callback. Pi identifies itself by dynamic client registration with client_name pi (or oauth.client Name), or by a Client ID Metadata Document on https://pi.dev/oauth, and it signs in again for step-up when a 403 asks for more scope mcp/README.md §Supported protocol surface CA/src/extensions/mcp/oauth.ts:272. The CIMD client id is https://pi.dev/oauth/client.json when the authorization server sends the RFC 9207 iss parameter, and https://pi.dev/oauth/<id>/client.json, with a matching callback path, when it does not CA/src/extensions/mcp/oauth.ts:253. Credentials go to mcp-auth.json in the agent directory CA/src/extensions/mcp/oauth.ts:144, created with mode 0600 CA/src/core/auth-storage.ts:25.

Commands. pi mcp add | remove | list | login | logout work without a session; add and remove take -l/--local for the project file, and list takes --json CA/src/extensions/mcp/cli.ts:33. Inside a session, /mcp opens the manager CA/src/extensions/mcp/index.ts:1141. --no-mcp disables the built-in support for one run CA/src/cli/args.ts:185.

D O C ≠ C O D E

CA/docs/mcp.md says “HTTP network errors and transient statuses (408, 429, and 5xx) are retried twice”. isTransientError excludes 501 CA/src/extensions/mcp/runtime.ts:72. The same page, and the comment in config.ts, say Pi activates codemode “when a server with codemode exposure connects”. ensureDiscoveryActive activates it from the configuration at session start, before any server connects, so a server that never connects still turns codemode on CA/src/extensions/mcp/index.ts:466.

W H A T T H I S M E A N S F O R Y O U

Expect MCP tools to be invisible in the request by default; look for them in the mcp_servers section and in codemode scripts.

Give each server a one-sentence description; it is the only line the model reads before connecting.

Use direct for a few hot tools, and accept that the first prompt waits up to 10 s for their server.

Keep credentials and auth in the user-level mcp.json; a project file can only toggle and re-expose.

Treat a failed tool call as possibly executed; Pi does not retry it, and neither should you.

Sources: mcp/README.md (§Supported protocol surface, §OAuth); mcp/package.json. mcp/src/protocol/types.ts (LATEST_PROTOCOL_VERSION, SUPPORTED_PROTOCOL_VERSIONS); mcp/src/client.ts (ClientState, connect, request Internal, handle Progress, cancel Pending, list All); mcp/src/transports/stdio.ts (close, killProcessTree, installExitHook); mcp/src/transports/streamable-http.ts (needs Authorization, reconnect defaults, openGetStream); mcp/src/transports/transport.ts (DEFAULT_MAX_MESSAGE_BYTES). CA/src/core/mcp-servers.ts (McpExposure, McpServerConfigBase, getMcpToolExposure, validateMcpServerConfig); CA/src/extensions/index.ts (builtInExtensions); CA/src/extensions/mcp/config.ts (readConfigFile, loadMcpConfig); CA/src/extensions/mcp/index.ts (renderServersSection, scriptNeedsServer, ensureDiscoveryActive, before_agent_start, tool_call); CA/src/extensions/mcp/tools.ts (createMcpToolName, limitMcpContent, convertMcpResult); CA/src/extensions/mcp/resources.ts. CA/src/extensions/mcp/runtime.ts (isTransientError, with Client, open); CA/src/extensions/mcp/oauth.ts; CA/src/extensions/mcp/cli.ts (HELP); CA/src/core/agent-session.ts (_preparePromptAndToolLoadout); CA/src/core/authstorage.ts; CA/src/cli/args.ts; CA/docs/mcp.md; research/capture/mcp-naming.mjs; research/out/mcp-naming.txt

# 6.2 Codemode, scripts that call tools

Codemode runs model-written JavaScript in a fresh QuickJS VM whose only

capability is calling tools. Every nested call goes through thefull tool

pipeline, but only the script's output reaches the context.

A model that needs fifty issues filtered down to three can make fifty tool calls, or write one script. Codemode is the second option. The model sends JavaScript; Pi runs it in a WebAssembly sandbox where tools.<name>(args) is the only door out; and the nested results stay in the script unless it prints them. This section shows the sandbox and why it is built from a worker, a wasm instance and a shared flag. It then covers the codemode tool: its schema and grammar, the description the model reads, how nested calls run, and what comes back.

## Two packages

@earendil-works/pi-codemode 1.0.4 “runs model-written JavaScript in a QuickJS VM (compiled to WebAssembly) where the only capability is calling injected tools. Nested tool calls never enter the LLM context; only the script’s output and return value do” codemode/README.md. It has no Pi dependencies and one runtime dependency, quickjs-wasi 3.6.2 codemode/package.json.

The codemode tool itself is a built-in, replaceable extension in CA/src/extensions/codemode/: tool.ts (419 lines) builds the definition and description, execute.ts (675) runs a script, renderer.ts (150) draws it in the TUI. It is registered with default Active: false CA/src/extensions/codemode/index.ts:43. --tools, the default Tools setting or setActiveTools() turn it on, and so does the MCP extension when a configured server has codemode tools (MCP (p. 144)).

## The sandbox

Each execute() creates a new worker_threads Worker, and the worker instantiates a new QuickJS VM from the compiled wasm module. “A fresh worker per run keeps termination simple: a runaway script, including one that only spins the microtask queue, is killed with terminate() and cannot poison a later run” codemode/src/runtime/host.ts:120.

![](images/72b7bdeb15daabfc5bd50ce3cb43ffe93c47d1aa908e6afb74ef6a45314b6c1f.jpg)
The VM reaches the host only through one bridge function, and the host can stop it two ways. Messages cross as JSON strings; the worker never builds structured values itself. Schematic, from codemode/src/runtime/protocol.ts (WorkerData, WorkerToHostMessage, HostToWorkerMessage), worker.ts and host.ts.

Isolation. The VM is a separate wasm instance with its own linear memory. Its only imports are a WASI shim, whose stdout and stderr writes the worker discards, and one host-call entry point codemode/src/runtime/worker.ts:32. There are no timers, fetch, process, require, modules or WebAssembly; “eval and Function work but only produce more code inside the same VM” codemode/README.md. Before the script runs, the prelude freezes the built-ins, so a script that patches

Array.prototype.toJSON cannot corrupt what the prelude reports to the host codemode/src/runtime/prelude-source.ts:28.

Why a worker. QuickJS runs synchronously; a spinning script on the host thread would block Pi’s event loop. Why the flag. On Bun, terminate() “cannot stop a thread that is spinning in wasm” codemode/src/runtime/protocol.ts:21, so the host first sets the shared Int32 and the VM’s interrupt Handler polls it codemode/src/runtime/worker.ts:60. Why maxStackSize. Without it, “deep recursion overflows the wasm stack and traps instead of throwing a catchable RangeError” codemode/src/runtime/worker.ts:57

The capture kit ran five scripts against the pinned build with a one-second deadline:

<table><tr><td>SCRIPT</td><td>RESULT</td></tr><tr><td>two tools.read calls in Promise.all, store, return</td><td>ok, both calls ok, store Writes.set = { seen: 2 }</td></tr><tr><td>typeof fetch, set Timeout, process, require, WebAssembly; eval(&quot;1 + 1&quot;); Object.isFrozen(Array.prototype)</td><td>five × &quot;undefined&quot;, 2, true</td></tr><tr><td>await new Promise( () =&gt; {} )</td><td>script: “The script is waiting on a promise that can never settle: no tool call is pending, and timers do not exist here.”</td></tr><tr><td>while (true) {}</td><td>timeout: “Execution timed out after 1000 ms”</td></tr><tr><td>unbounded recursion inside try</td><td>ok, value “RangeError: Maximum call stack size exceeded”</td></tr></table>

A stalled script fails at once; a spinning one waits for the deadline. From research/out/codemode-sandbox.txt, produced by research/capture/codemodesandbox.mjs.

execute() never rejects for a script failure. result.error.kind is script, timeout, aborted or sandbox (a wasm trap or a missing worker file) codemode/README.md §Results. The README puts the start-up cost at “about 20 ms including VM creation” per execution; the capture kit did not time it.

<table><tr><td>LIMIT</td><td>VALUE</td><td>WHERE SET</td></tr><tr><td>MAX_OUTPUT_CHARS</td><td>16 Mi characters of text and base64 image data</td><td>codemode/src/runtime/prelude-source.ts:40</td></tr><tr><td>MAX_OUTPUT_ITEMS</td><td>100,000 items</td><td>codemode/src/runtime/prelude-source.ts:41</td></tr><tr><td>MAX_STORE_VALUE_CHARS</td><td>256 Ki characters of JSON per value</td><td>codemode/src/runtime/prelude-source.ts:32</td></tr><tr><td>MAX_STORE_TOTAL_CHARS</td><td>1 Mi characters for all values</td><td>codemode/src/runtime/prelude-source.ts:33</td></tr><tr><td>deadline, library</td><td>300,000 ms</td><td>codemode/src/runtime/host.ts:22</td></tr><tr><td>deadline, Pi</td><td>none unless timeout_ms is set</td><td>CA/src/extensions/codemode/execute.ts:427</td></tr><tr><td>VM heap, Pi</td><td>256 MiB</td><td>CA/src/extensions/codemode/execute.ts:55</td></tr><tr><td>concurrent models.* calls, Pi</td><td>4</td><td>CA/src/extensions/codemode/execute.ts:49</td></tr></table>

Pi removes the library’s five-minute deadline and adds a heap cap. Past either output limit the script fails with a RangeError, “even if it catches the error” codemode/README.md §Results.

## The codemode tool

The schema has one field. Three more properties of the definition matter as much:

```typescript the input schema and the parts of the definition that shape it CA/src/extensions/codemode/tool.ts TS

export const codemode Schema = Type.Object({
    code: Type.String({
    description: "Raw JavaScript source.",
    }),
});
...
parameters: codemode Schema,
// Scripts must not start other scripts.
exposure: "model-only",
prepare Loadout: (loadout) => prepareCodemodeLoadout(loadout, options),
// Capable models write the script as raw text instead of a JSON-escaped string.
constrained Sampling: { type: "grammar", variants: { openai_lark: CODEMODE_SOURCE_GRAMMAR } },
```
Lines 89–93 and 390–395; the rest of createCodemodeToolDefinition is cut.

The grammar lets a model that supports grammar-constrained tool input emit raw JavaScript rather than a JSON-escaped string. It fixes only the shape of an optional options line; the JSON and the code are checked by parseCodemodeSource codemode/src/source.ts:18.

```txt
CODEMODE_SOURCE_GRAMMAR codemode/src/source.ts start: options_source | plain_source options_source: OPTIONS_LINE NEWLINE SOURCE
plain_source: SOURCE
OPTIONS_LINE: /[\t]*\// @options:[^\r\n]*/
NEWLINE: /\r?\n/
SOURCE: /[\s\S]+/
```

```txt
Complete, lines 23–29.
```

The options line is // @options: {"max_output_tokens": N, "timeout_ms": N}. Any other field, invalid JSON, or an options line with no code after it throws CodemodeSourceError; timeout_ms must be a positive integer up to 2,147,483,647, the largest set Timeout delay codemode/src/source.ts:16. The line is replaced by an empty line, so line numbers in stack traces still match codemode/src/source.ts:40.

The description. createCodemodeDescription builds what the model reads: an intro, a list of globals, shared MCP types when a listed tool needs them, and one section per listed tool, grouped by namespace CA/src/extensions/codemode/tool.ts:248. With read as the only listed tool, the build produces:

```markdown
Run JavaScript that calls other tools. The input is raw JavaScript (not JSON, no code fence), run as an async function body in a QuickJS sandbox: top-level `await` and `return` work. No Node, file system, network, or timers.
- `await tools.<name>({ ...args })` resolves to a string, or an object if the tool's declaration says so, and rejects with an Error on failure. Calls still running when the script ends are cancelled.
- Optional first line: // @options: {"max_output_tokens": 10000, "timeout_ms": 60000}
Globals:
- `text(value)`, `image(dataUrlOrImageBlock)`, `console.log(...)`, and top-level `return` add output;
`exit()` ends the script. `image()` also saves the image to a temp file and the result names its path.
- `store(key, value)` and `load(key)` keep JSON values across codemode calls.
- `ALL_TOOLS`, `search Tools(query, { limit?, namespace? })`, `describe Tool(name)`, `describe Namespace(name)`: find unlisted tools, such as MCP tools.

Nested tools:

### `read`
Read a file

codemode tool declaration:
```ts declare const tools: { read(args: { path: string; }) : Promise<string>; };
```

That is the complete output of createCodemodeDescription([read], {}) research/out/codemode-sandbox.txt. The models line is absent because the models option was not set.

Three rules decide which tools get a section.

Budget — listed sections share codemode.inline Budget, default 3,000 estimated tokens at 4 characters per token CA/src/extensions/codemode/tool.ts:156. Selection is round-robin: in each round every namespace group places its cheapest remaining tool, and a group whose next tool does not fit drops out, so every namespace appears before any is complete CA/src/extensions/codemode/tool.ts:222.

Deferred tools are never listed — that includes MCP tools with the default codemode exposure. They “do not afect the description at all, so it stays the same while MCP servers connect” CA/src/extensions/codemode/tool.ts:244. Scripts find them with search Tools(query), a BM25 ranking with a default limit of 8, describe Tool(name) and describe Namespace(name) CA/src/extensions/codemode/execute.ts:496.

codemode.mode — on (default) lists only callable tools without direct exposure and adds a “Codemode: tools.<id>(args) resolves to …” line to each declared tool’s own description. only lists every callable tool and drops the declarations of active direct tools from the request CA/src/extensions/codemode/tool.ts:342.

Running a script
![](images/922188e19cb804d9b56381e04c80e21a8e4e52abd5614f27d79df57a87b88c2b.jpg)
The nested result stops at the VM; only step 5 reaches the model. Step 3 is the arrow the figure is about: the nested call is a full tool call with its own id and hooks. Schematic, from CA/src/extensions/codemode/execute.ts (execute Codemode, toScriptValue) and CA/src/core/nested-tool-calls.ts (NestedToolCallRunner).

Nested calls. A script can call the active direct tools and every codemode or deferred tool, but not codemode itself, whose exposure is model-only CA/src/extensions/codemode/tool.ts:392. Each call goes through ctx.execute Tool(name, args, { signal }), so validation, tool_call and tool_result hooks and permission gates apply as for a direct call CA/src/extensions/codemode/execute.ts:405. The nested call gets the id <codemode call id>/<n>, with n counting from 1, and its execution events carry parentToolCallIdCA/src/core/nested-tool-calls.ts:188.

What a call resolves to CA/src/extensions/codemode/execute.ts:347:

a tool that declares output Schema resolves to its structured Content, also for an error result that carries one. Every MCP tool declares one. An MCP call therefore resolves to the whole CallToolResult, isError included (MCP (p. 144));

any other tool resolves to its text content as one string;

a failed, blocked or invalid call rejects with an Error carrying the tool’s error text.

The store. store(key, value) and load(key) keep JSON values across calls. A successful script that wrote anything appends one codemode-store custom entry { set, delete } CA/src/extensions/codemode/execute.ts:451. load() replays those entries along the current branch from the root CA/src/extensions/codemode/execute.ts:217, so the store follows /tree, resume and fork (sessions, the JSONL tree (p. 86)). A failed script reports no writes. Its nested calls have already run, and nothing undoes them.

The result. The content starts with Script completed or Script failed, then Wall time N seconds, then Output: CA/src/extensions/codemode/execute.ts:470. A returned value is appended like text(); a failure appends Script error: and the error after the partial output. Text over max_output_tokens, default 10,000 CA/src/extensions/codemode/execute.ts:231, keeps its head and tail around a …N tokens truncated… marker, and the full text goes to a temp file. Images are saved to temp files and the result names each path.

## R U L E O F T H U M B
If the model needs every byte of a result, let it call the tool directly. If it needs a count, a filter or a join across several calls, give it codemode: the nested results stay in the VM and the context pays only for what the script prints. Set timeout_ms in the options line when a script calls a slow server; Pi sets no deadline of its own.

Sources: codemode/README.md (§Results, §How it works, §Store); codemode/package.json. codemode/src/runtime/protocol.ts (WorkerData, WorkerToHostMessage, HostToWorkerMessage); codemode/src/runtime/worker.ts (main, discard Output, bridge); codemode/src/runtime/host.ts (Execution, DEFAULT_TIMEOUT_MS); codemode/src/runtime/prelude-source.ts (limits, freezing); codemode/src/source.ts (CODEMODE_SOURCE_GRAMMAR, parseCodemodeSource). CA/src/extensions/codemode/index.ts; CA/src/extensions/codemode/tool.ts (codemode Schema, DESCRIPTION_INTRO, select Catalog, createCodemodeDescription, prepareCodemodeLoadout, createCodemodeToolDefinition); CA/src/extensions/codemode/execute.ts (execute Codemode, toScriptValue, readCodemodeStore, createDiscoveryGlobals, truncate Output). CA/src/core/nested-tool-calls.ts (NestedToolCallRunner.execute); CA/src/core/settings-manager.ts (CodemodeSettings); research/capture/codemodesandbox.mjs; research/out/codemode-sandbox.txt

## 6.3 pi-tui, the terminal UI framework

Every component turns a width into a list oflines, and the renderer writes only the lines that changed, inside one synchronized-output block. Pi's default renderer is the alternate-screen one, which never errors on an overwide line; the scrollback one does.

Everything a person sees in interactive Pi — the editor, the streaming transcript, tool output, /mcp and every extension dialog — is drawn by @earendil-works/pi-tui. Its README calls it a “minimal terminal UI framework with diferential rendering and synchronized output for flicker-free interactive CLI applications” tui/README.md. This section shows the component contract, the two renderers and the bytes they write, how keyboard input is negotiated and routed, overlays, terminal capabilities and native addons, and the built-in components. The package has two runtime dependencies, get-east-asian-width 1.6.0 and marked 18.0.11; its tests run on node:test, several of them against @xterm/headless 5.5.0 tui/package.json.

#### A component is a function of width

```typescript the whole component contract tui/tui.ts TS

export interface Component {
    /**
    * Render the component to lines for the given viewport width
    * @param width - Current viewport width
    * @returns Array of strings, each representing a line
    */
    render(width: number): string[];
    /** Optional handler for keyboard input when component has focus. */
    handle Input?(data: string): void;

    /** Optional normalized mouse handler. */
    handle Mouse?(event: TuiMouseEvent): TuiMouseEventResult | undefined;

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

A component returns ANSI-styled lines; handle Input receives raw bytes, escape sequences included, while the component has focus. A Focusable component has one more field, focused, and while it is true it emits CURSOR_MARKER,

"\x1b_pi:c\x07", a zero-width APC sequence, where the cursor belongs. The renderer finds the marker, strips it and puts the hardware cursor there, which is where an IME draws its candidate window tui/tui.ts:180 tui/tui.ts:196. Container stacks its children vertically and routes a mouse event to the child whose rows contain its y tui/tui.ts:347.

After compositing, the renderer appends SEGMENT_RESET, "\x1b[0m\x1b]8;;\x07" (SGR reset plus an OSC 8 close), to every line that is not an image, so neither a style nor a hyperlink leaks into the next line tui/tui.ts:412 tui/tui.ts:1413.

The width rule. The README is strict: “Each line must not exceed width or the TUI will error” tui/README.md. The code is stricter in one renderer and looser in the other, as the DOC ≠ CODE callout below shows.

## Two renderers

S T R U C T U R E

Container children: Component[] · vertical stack · mouse by row

«interface» TUI mode · set Focus · show Overlay · request Render · start · stop

↓ extends Container, implements TUI

«abstract» TuiBase focus · overlay stack · input routing · 16 ms render throttle · abstract doRender()

TuiMainScreen · mode “regular” line dif against the previous frame · output stays in terminal scrollback · overwide line throws

TuiAltScreen · mode “fullscreen” alternate screen · row dif · mouse, selection, search, scrollbar · over-wide line sliced · Pi’s default

Pi picks the alternate-screen renderer unless tui Mode is "regular". Both share TuiBase; only doRender() difers. Schematic, from tui/tui.ts (Component, Container, TUI, TuiBase), tui-main-screen.ts, tui-alt-screen.ts, and CA/src/modes/interactive/tui-renderer.ts (createInteractiveTui).

The coding agent’s tui Mode setting defaults to "fullscreen" CA/src/core/settings-manager.ts:184, and createInteractiveTui builds a TuiAltScreen for it and a TuiMainScreen only for "regular"

CA/src/modes/interactive/tui-renderer.ts:22.

Scheduling. MIN_RENDER_INTERVAL_MS is 16, about 60 frames a second tui/tui.ts:507. request Render() sets a flag and defers to process.next Tick, which schedules a set Timeout for the rest of the 16 ms; further requests in the meantime coalesce into that one frame tui/tui.ts:990. Keyboard input skips the throttle, because “even set Timeout(0) can take a full 16 ms tick on Windows” tui/tui.ts:1117.

The main-screen frame. TuiMainScreen.doRender() renders the tree, composites overlays, extracts the cursor marker, applies the per-line resets, then decides between a full and a diferential write tui/tui-main-screen.ts:247.

![](images/cd54ea92ecfb4a73e0b2ed172435f0f0e00bb60e680d51607398acf5f2c3be44.jpg)
First match wins; every rose row clears the scrollback. Every write is wrapped in synchronized output (CSI ? 2026 h/l), so the terminal shows whole frames. Writes go through BoundedTerminalWriter, which streams in 1 MiB chunks so a full render never builds a string past V8’s limit. From tui/tui-main-screen.ts:247– 567.

The capture kit drove TuiMainScreen with a stub 20 × 10 terminal and three Text lines, then changed the middle one. Escape bytes are shown as \u001b:

```txt
#### frame 1: first render
"\u001b[?2026halpha \u001b[0m\u001b]8;;\u0007\r\nbeta
\u001b[0m\u001b]8;;\u0007\r\ngamma \u001b[0m\u001b]8;;\u0007\u001b[?2026l"
#### frame 2: line 1 changed
"\u001b[?2026h\u001b[1A\r\u001b[2KBETA \u001b[0m\u001b]8;;\u0007\u001b[?2026l"
#### frame 3: nothing changed full Redraws: 1
```

Frame 2 is the whole point of the design: one cursor-up, one line clear, 20 columns and a reset: 55 bytes for a one-word change. Frame 3 writes nothing. Text pads every line to the width, so the reset lands after column 20 research/out/tui-frames.txt.

The alternate-screen frame. TuiAltScreen enters with \x1b[?1049h, turns of autowrap and, when the mouse is enabled, turns on modes 1000, 1002, 1004 (focus reporting) and 1006 (SGR mouse) tui/tui-alt-screen.ts:63. It difs row by row against the previous screen and rewrites a changed row with an absolute CSI <row>;1H plus CSI 2K tui/tui-alt-screen.ts:1745, again inside CSI ? 2026 h/l. On top of that it adds VStack, HStack and ScrollView layout, a follow-end transcript, OSC 133 prompt jumps, a scrollbar, drag-select with OSC 52 copy, clickable OSC 8 links, and transcript search tui/tui-altscreen.ts:202. On exit Pi restores the main screen and prints the transcript, or only a resume hint when fullscreenExitOutput is "resume-hint"CA/src/core/settings-manager.ts:185.

```javascript request flags 7, query them, and send DA1 as a sentinel tui/terminal.ts const DESIRED_KITTY_KEYBOARD_PROTOCOL_FLAGS = 7;
const KEYBOARD_PROTOCOL_RESPONSE_FRAGMENT_TIMEOUT_MS = 150;
const KITTY_KEYBOARD_PROTOCOL_QUERY = '\x1b[>${DESIRED_KITTY_KEYBOARD_PROTOCOL_FLAGS}u\x1b[?u\x1b[c`;
```

Three environment variables help debugging: PI_TUI_DEBUG_REDRAW=1 logs the reason for each main-screen full redraw to pi-tui-debug.log tui/tui-main-screen.ts:321, PI_TUI_DEBUG=1 writes one log file per diferential frame under /tmp/tui tui/tui-main-screen.ts:569, and PI_TUI_WRITE_LOG=<file> captures the raw output stream tui/terminal.ts:152.

D O C ≠ C O D E The README says an over-wide line makes “the TUI … error”. In TuiMainScreen the check sits only on the diferential path: a line wider than the terminal writes pi-tui-crash.log, stops the TUI and throws “Rendered line N exceeds terminal width” tui/tuimain-screen.ts:517; a first frame or full redraw writes it unchecked. TuiAltScreen, Pi’s default, never throws and slices the line to the width with sliceByColumn tui/tui-alt-screen.ts:1692. The capture kit confirmed the throw: a raw component returning 25 columns in a 20-column terminal stopped frame 5 with “Rendered line 3 exceeds terminal width (25 > 20).” research/out/tuiframes.txt

## Input and the keyboard protocol

ProcessTerminal.start puts stdin in raw mode and enables bracketed paste with \x1b[?2004h tui/terminal.ts:174. It then negotiates the Kitty keyboard protocol in one write:

Lines 12–14. Flags 7 = 1 (disambiguate escape codes) + 2 (report press, repeat and release) + 4 (report alternate keys).

A reply CSI ? <flags> u with non-zero flags turns Kitty mode on. Flags of zero, or a DA1 reply with no Kitty reply before it, turns on xterm modifyOtherKeys instead with \x1b[>4;2m tui/terminal.ts:267. Every terminal answers DA1, so the fallback needs no start-up timeout.

StdinBuffer reassembles escape sequences split across reads. A lone ESC counts as the Escape key after 10 ms, or 100 ms when SSH_CONNECTION or SSH_TTY is set, because legacy Alt+key arrives as ESC plus a byte; PI_TUI_ESC_TIMEOUT overrides both tui/terminal.ts:115.

Routing. TuiBase.handleTerminalInput passes each input through a fixed ladder; the first step that consumes it ends the walk tui/tui.ts:1044:

1. terminal colour replies (OSC 10, 11, 4) and colour-scheme reports;

2. input listeners, in order, each able to consume the input or rewrite it;

3. the terminal’s cell-size reply;

4. Shift+Ctrl+D, the debug key, when a debug handler is set;

5. overlay focus repair: a focused overlay that is no longer visible hands focus to the topmost visible one;

6. Kitty key-release events, dropped unless the focused component sets wantsKeyRelease;

7. the focused component’s handle Input, followed by an immediate render.

Keybindings. interface Keybindings is a registry that other packages extend by declaration merging; pi-tui declares the tui.* actions tui/keybindings.ts:3. The coding agent merges in its app.* actions CA/src/core/keybindings.ts:69 and reads overrides from keybindings.json in the agent directory CA/src/core/keybindings.ts:380; slash commands and keybindings (p. 197) lists them.

## Overlays

show Overlay(component, options) pushes a component onto an overlay stack and returns a handle. Overlays are composited into the base lines before the dif, with ANSI-aware column slicing (compositeTuiLine), so an overlay costs only the rows it covers tui/tui.ts:415.

<table><tr><td>OverlayOptions FIELD</td><td>MEANING</td></tr><tr><td>width,max Height</td><td>columns or rows, or a percentage string such as &quot;50%&quot;</td></tr><tr><td>min Width</td><td>minimum columns</td></tr><tr><td>anchor</td><td>center (default), top-left, top-right, bottom-left, bottom-right, top-center, bottom-center, left-center, right-center</td></tr><tr><td>offsetX,offsetY</td><td>shift from the anchor</td></tr><tr><td>row,col</td><td>absolute or percentage position instead of an anchor</td></tr><tr><td>margin</td><td>distance from the terminal edges, one number or per side</td></tr><tr><td>visible(term Width, term Height)</td><td>rendered only while it returns true</td></tr><tr><td>non Capturing</td><td>shown without taking keyboard focus</td></tr></table>

Nine anchors, and a percentage for every size. From OverlayOptions tui/tui.ts:243. The OverlayHandle returned has hide, set Hidden, isHidden, focus, unfocus, isFocused and get Bounds tui/tui.ts:298.

Extensions reach overlays through ctx.ui.custom(factory, { overlay: true, overlay Options, onHandle }), which resolves with the value the component passes to done CA/src/core/extensions/types.ts:214; extensions, loading and the API (p. 113) covers the UI context.

## Images, colours and native addons

pi-tui draws images with the Kitty graphics protocol (a=T,f=100,q=2, base64 in 4,096-character chunks, a random image id in 1–0xffff) or iTerm2’s OSC 1337 tui/terminal-image.ts:217 tui/terminal-image.ts:230. Which one, if any, comes from the environment:

![](images/a7e801b4f24a1c682b7c86211529097c3b073ff6c75151d5802dfc10e8bf40de.jpg)
First match wins, and an unknown terminal gets no images and no hyperlinks. PI_IMAGE_PROTOCOL (kitty or iterm2), PI_TRUE_COLOR and PI_HYPERLINKS (1 or 0) override the result. From tui/terminal-image.ts (detectCapabilitiesFromEnvironment, detect Capabilities).

Colours come as indexed, sRGB, OKLCH or OKHSL values; parse Color reads oklch(…) and okhsl(…) strings and mix Colors mixes in OKLCH by default tui/colors.ts:121 tui/colors.ts:241. A query for OSC 10, OSC 11 and the 16 palette entries, closed by a DA1 request, reads the terminal’s own colours for the system theme tui/tui.ts:168.

Native addons are prebuilt N-API binaries committed under tui/native/<platform>/prebuilds/, so installing Pi never runs node-gyp:

<table><tr><td>PLATFORM</td><td>BINARY</td><td>PROVIDES</td></tr><tr><td>darwin arm64, x64</td><td>darwin-platform.node (AppKit)</td><td>clipboard text, images and file paths; modifier state, which turns Shift+Enter in Apple Terminal into \x1b[13;2u</td></tr><tr><td>linux x64, arm64</td><td>linux-platform-x11.node (libxcb)</td><td>X11 clipboard reads; loaded only when DISPLAY is set; Wayland falls back to wl-paste</td></tr><tr><td>win32 x64, arm64</td><td>win32-platform.node</td><td>console input setup, modifier state, clipboard</td></tr></table>

Six prebuilt binaries, one per platform and architecture. A missing or failing addon degrades to undefined and the caller falls back tui/nativeplatform.ts:28. Rebuild with npm run build:native:<platform> tui/package.json. From tui/native/*/README.md and tui/terminal.ts:11.

Built-in components

<table><tr><td>COMPONENT</td><td>WHAT IT IS</td></tr><tr><td>Text, TruncatedText, Box, Spacer</td><td>wrapped text, one truncated line, a padded box, empty rows</td></tr><tr><td>Input</td><td>a single-line field</td></tr><tr><td>Editor</td><td>2,472 lines: multiline editing, a 100-entry prompt history, a kill ring, undo, autocomplete on @ and # and on / at the start of a message; a paste over 10 lines or 1,000 characters collapses to [paste #N +L lines] or [paste #N C chars]</td></tr><tr><td>Markdown</td><td>marked tokens, output cached per text and width, inline and block LaTeX rendered to Unicode, a pluggable highlight Code</td></tr><tr><td>Loader, CancellationLoader</td><td>spinners, the second abortable</td></tr><tr><td>SelectList, SettingsList</td><td>a keyboard-driven list; a settings list with fuzzy search</td></tr><tr><td>Image</td><td>an image line in the detected protocol</td></tr><tr><td>VStack, HStack, ScrollView, MouseRegion</td><td>layout and mouse targets for the alternate screen</td></tr></table>

Utilities do the column arithmetic. visible Width, truncateToWidth, sliceByColumn, wrapTextWithAnsi and fuzzy Filter measure terminal columns, not string length tui/index.ts:184. From tui/index.ts and tui/components/editor.ts (history limit, paste markers, autocomplete triggers).

W H A T T H I S M E A N S F O R Y O U

Measure every line you return with visible Width() and cut it with truncateToWidth(); Pi’s fullscreen mode hides the mistake and regular mode crashes on it.

Reapply styles on every line; the renderer resets SGR and OSC 8 at each line end.

Cache rendered lines by width and clear the cache in invalidate(); render() runs on every frame.

Test in both tui Mode values, and set PI_TUI_DEBUG_REDRAW=1 when regular mode keeps redrawing everything.

Sources: tui/README.md; tui/package.json (dependencies, test, build:native:*). tui/tui.ts (Component, Focusable, CURSOR_MARKER, OverlayOptions, OverlayHandle, Container, SEGMENT_RESET, compositeTuiLine, TUI, TuiBase: MIN_RENDER_INTERVAL_MS, request Render, schedule Render, handleTerminalInput, applyLineResets, TERMINAL_COLOR_QUERY); tui/tui-main-screen.ts (BoundedTerminalWriter, doRender); tui/tui-alt-screen.ts (ENTER_ALT_SCREEN, mouse modes, doRender, scrollToPrompt, OSC 52 copy). tui/terminal.ts (Kitty negotiation, modifyOtherKeys, resolveEscapeTimeoutMs); tui/keybindings.ts; tui/terminal-image.ts (detectCapabilitiesFromEnvironment, Kitty and iTerm2 encoders); tui/colors.ts; tui/native-platform.ts; tui/native/*/README.md; tui/components/editor.ts; tui/components/markdown.ts. CA/src/core/settings-manager.ts (tui Mode, fullscreenExitOutput); CA/src/modes/interactive/tui-renderer.ts; CA/src/core/keybindings.ts; CA/src/core/extensions/types.ts (ExtensionUIContext.custom); research/capture/tui-frames.mjs; research/out/tui-frames.txt
