A small core that turns one prompt into model calls, tool runs and JSONL lines, with almost everything else left to extensions.

![](images/e6f26104eb453e2b55b900f324b44da14eec4d64a5a680ad5eb71ad4614af91a.jpg)

## 1.1 What Pi is for

Pi is a small core that turns a prompt into model calls, tool runs and JSONL lines. Everything a product would bake in on top of that — sub-agents, plan mode, permission popups — is left to extensions on purpose.

Pi is a terminal coding agent whose authors describe it as “a minimal, extensible agent harness that you can make your own” CA/README.md. That sentence is a design constraint, not a slogan: the core decides how a prompt reaches a model, how tools run and how the conversation is stored, and it hands nearly every other decision to code you load. This section lists what ships at commit 28dcce2, counts each surface from the source, and names the features the core leaves out.

## What the core ships

The published package @earendil-works/pi-coding-agent 1.0.4 installs one binary, pi CA/package.json:9. Behind it sit seven things, each owned by one part of this book.

<table><tr><td>SURFACE</td><td>AT 28dce2</td><td>WHERE</td><td>SEE</td></tr><tr><td>LLM abstraction</td><td>10 chat wire APIs, 42 known providers, 1 image API, 3 classifier APIs</td><td>ai/types.ts:17, ai/compat.ts:180</td><td>providers and models (p. 24), wire APIs and cross-provider hand-off (p. 36)</td></tr><tr><td>Agent loop</td><td>stateless run Loop with steering and follow-up queues; stateful Agent wrapper</td><td>agent/agent-loop.ts:163, agent/agent.ts:188</td><td>the agent loop (p. 49)</td></tr><tr><td>Session runtime</td><td>AgentSession: prompt pipeline, retries, compaction, persistence</td><td>CA/src/core/agent-session.ts:1954</td><td>AgentSession: wiring the runtime (p. 61)</td></tr><tr><td>Tools</td><td>4 active by default (read, bash, edit, write); 8 built in</td><td>CA/src/core/settings-manager.ts:215, CA/src/core/tools/index.ts:95</td><td>built-in tools (p. 81)</td></tr><tr><td>Sessions</td><td>tree-structured, append-only JSONL; automatic compaction, on by default</td><td>CA/src/core/session-manager.ts:1172, CA/src/core/compaction/compaction.ts:127</td><td>sessions, the JSONL tree (p. 86), compaction and branch summaries (p. 92)</td></tr><tr><td>Extension API</td><td>41 subscribable events, 31 methods, one shared event bus</td><td>CA/src/core/extensions/types.ts:1553</td><td>extensions, loading and the API (p. 113), extension events and contexts (p. 120)</td></tr><tr><td>Run modes</td><td>interactive TUI, print (-p), JSON, RPC, plus the in-process SDK</td><td>CA/src/main.ts:112</td><td>run modes (p. 127), RPC mode and the SDK (p. 133)</td></tr></table>

Seven surfaces, each counted from the source. The counting rules are in the next subsection.

Four more capabilities arrive as built-in extensions rather than core code. The CLI registers lama.cpp, codemode, toolsearch and mcp as inline extensions, and the last three are marked replaceable: “an extension that registers codemode, tool_search, or /mcp … takes over instead of running alongside the built-in one” CA/src/extensions/index.ts:7. Codemode runs model-written JavaScript in QuickJS compiled to WebAssembly, where “the only capability is calling injected tools” codemode/package.json; codemode (p. 151) covers it, and MCP (p. 144) covers the MCP client.

## How the counts were made

Every number in the table above was read from the checkout, and each one depends on a counting rule. Change the rule and the number changes, so the rules are stated here.

Wire APIs: 10. The members of the KnownApi union ai/types.ts:17, which match the ten entries of BUILTIN_APIS registered at load ai/compat.ts:180. KnownImageApi adds openrouter-images and KnownClassifierApi adds three classifier APIs ai/types.ts:31; neither is a chat API. The 40 files in ai/api/ are not the count: 15 of them are .lazy.ts loaders and others are shared helpers research/out/stats.txt §api-files.

Providers: 42. The members of the KnownProvider union ai/types.ts:39. The set is identical to the 42 ai/providers/*.models.ts catalogue files research/out/stats.txt §provider-files. The test-only faux provider is in neither.

Tools: 4 + 4. DEFAULT_TOOL_NAMES is ["read", "bash", "edit", "write"] CA/src/core/settings-manager.ts:215. The ToolName union adds powershell, grep, find and ls for eight built-in tools CA/src/core/tools/index.ts:95. The tool_search tool from the built-in extension is registered inactive and is not counted.

Extension events: 41. The distinct event names accepted by the on() overloads of ExtensionAPI CA/src/core/extensions/types.ts:1558. The ExtensionEvent union has 32 members CA/src/core/extensions/types.ts:1366 because it folds all session events into one SessionEvent member.

Extension methods: 31. The distinct method names of ExtensionAPI other than on, from register Tool to unregisterVirtualModel CA/src/core/extensions/types.ts:1632. Overloads count once. The events property, a shared EventBus, is not a method CA/src/core/extensions/types.ts:1878.

Run modes: 4. resolveAppMode picks one of four app modes: rpc and json from --mode, print from -p or when stdin or stdout is not a terminal, and interactive otherwise CA/src/main.ts:112. --mode text alone therefore does not select print: at a terminal it still opens the TUI. Print and JSON share one runner, runPrintMode, whose output mode is "text" | "json" CA/src/modes/print-mode.ts:20. The SDK is the other way in: createAgentSession() in your own process CA/src/core/sdk.ts. Hence the landing page’s “Four modes: interactive, print/JSON, RPC, and SDK”.

## What is left out on purpose

The pi.dev landing page has a section titled “What we didn’t build”. It names five features, and the repository ships a reference extension for four of them.

Four of the five omitted features have a reference extension in the repository; background bash has none. Left: core code at 28dcce2. Centre: builtInExtensions CA/src/extensions/index.ts:7. Right: the list under “What we didn’t build” on pi.dev, matched against CA/examples/extensions/. Schematic.

![](images/a72a03c74a5d5658a8ff43e8294a8e4326ea5df66048b77b3682547cb5d35a6e.jpg)

The page’s advice for each omission is concrete. For sub-agents: “Spawn Pi instances via tmux, or build your own with extensions”. For permission popups: “Run in a container, or build your own confirmation flow”. For plan mode: “Write plans to files”. For to-dos, it suggests a Markdown file in the project. For background bash it gives only “Use tmux. Full observability, direct interaction.” The same page lists MCP as a former omission, struck through and replaced by “Now with MCP+Codemode”.

CA/examples/extensions/ holds 80 entries: 70 single-file .ts extensions, 9 directories and a README.md research/out/stats.txt §example-extensions. That is 79 examples; the landing page says “50+”.

## W H Y I T M A T T E R S
Every omission is a seam. A permission gate is a tool_call handler that returns { block: true }; a plan mode is a before_agent_start handler plus a command. Before you ask for a feature in core, look for the event that would carry it in extension events and contexts (p. 120) and for a reference implementation in CA/examples/extensions/.

## W H A T T H I S M E A N S F O R Y O U
Expect Pi to call a model, run tools and write JSONL, and nothing more, until you load extensions.

Count providers by KnownProvider and wire APIs by KnownApi; file counts in ai/ overstate both.

Start a missing feature from the nearest file in CA/examples/extensions/.

Treat mcp, codemode and tool-search as defaults you can replace, not as core.

Sources: CA/README.md; CA/package.json (name, version, bin). ai/types.ts (KnownApi, KnownImageApi, KnownClassifierApi, KnownProvider); ai/compat.ts (BUILTIN_APIS); agent/agent-loop.ts (run Loop); agent/agent.ts (Agent). CA/src/main.ts (resolveAppMode); CA/src/modes/print-mode.ts; CA/src/core/settings-manager.ts (DEFAULT_TOOL_NAMES); CA/src/core/tools/index.ts (ToolName); CA/src/core/compaction/compaction.ts (DEFAULT_COMPACTION_SETTINGS); CA/src/core/extensions/types.ts (ExtensionEvent, ExtensionAPI); CA/src/cli/args.ts (Mode); CA/src/modes/index.ts. CA/src/extensions/index.ts (builtInExtensions); codemode/package.json (description, quickjs-wasi); CA/examples/extensions/. pi.dev landing page, fetched 5 October 2026 (“Four modes”, “What we didn’t build”); research/out/stats.txt (§provider-files, §api-files, §example-extensions)

## 1.2 The monorepo in one page

The repository holdsfourteen packages, but the pi command runs on a chain of three — pi-coding-agent, pi-agent-core, pi-ai. Five of the others serve an experimental stack that installing the CLI from npm never pulls in.

A reader opening packages/ meets fourteen directories and no map. Half of them are not on the path of a prompt in the stable CLI. This section lists every package with its size and role, draws the dependency graph from each package.json as layers, and shows exactly how the experimental packages are kept out of what npm and the standalone binary ship.

## Fourteen packages

Every package is at version 1.0.4 and all but one are public research/out/stats.txt §package-lines.

<table><tr><td>DIRECTORY</td><td>NPM PACKAGE</td><td>FILES</td><td>LINES</td><td>ROLE</td></tr><tr><td>packages/coding-agent</td><td>@earendil-works/pi-coding-agent</td><td>297</td><td>77,340</td><td>the pi CLI: sessions, tools, extensions, run modes, TUI app</td></tr><tr><td>packages/ai</td><td>@earendil-works/pi-ai</td><td>151</td><td>23,581</td><td>providers and models, streaming protocol, auth, OAuth</td></tr><tr><td>packages/durable</td><td>@earendil-works/pi-durable</td><td>65</td><td>18,338</td><td>experimental durable conversation, task and document runtime</td></tr><tr><td>packages/tui</td><td>@earendil-works/pi-tui</td><td>45</td><td>17,134</td><td>differential-rendering terminal UI library</td></tr><tr><td>packages/chord</td><td>@earendil-works/chord</td><td>29</td><td>8,136</td><td>composition runtime: facets, services, replicated state, RPC</td></tr><tr><td>packages/mcp</td><td>@earendil-works/pi-mcp</td><td>18</td><td>2,907</td><td>standalone MCP client: stdio and Streamable HTTP, OAuth</td></tr><tr><td>packages/agent</td><td>@earendil-works/pi-agent-core</td><td>6</td><td>2,281</td><td>stateless agent loop and the stateful Agent wrapper</td></tr><tr><td>packages/env</td><td>@earendil-works/pi-env</td><td>6</td><td>1,928</td><td>remote ExecutionEnv for Pi Durable over SSH</td></tr><tr><td>packages/server</td><td>@earendil-works/pi-server</td><td>16</td><td>1,800</td><td>experimental Unix-socket session router</td></tr><tr><td>packages/codemode</td><td>@earendil-works/pi-codemode</td><td>10</td><td>1,696</td><td>QuickJS-in-WebAssembly script sandbox</td></tr><tr><td>packages/evals</td><td>@earendil-works/pi-evals (private)</td><td>5</td><td>1,345</td><td>vitest-evals harness</td></tr><tr><td>packages/client</td><td>@earendil-works/pi-client</td><td>8</td><td>1,046</td><td>experimental client for remote Pi sessions</td></tr><tr><td>packages/telemetry</td><td>@earendil-works/pi-telemetry</td><td>6</td><td>826</td><td>vendor-neutral span contracts, no exporter</td></tr><tr><td>packages/protocol</td><td>@earendil-works/pi-protocol</td><td>8</td><td>790</td><td>experimental CBOR-framed protocol, version 8</td></tr><tr><td>total</td><td></td><td>670</td><td>159,148</td><td></td></tr></table>

pi-coding-agent is 48.6 percent of the code; the loop it runs on is 1.4 percent. LINES counts non-blank lines of *.ts, *.tsx and *.rs files under each package’s src/, excluding *.test.*, *.d.ts and the generated *.models.ts catalogues. From research/capture/stats.py at 28dcce2.

The counting rule leaves three things out, and each is large. The model catalogue lives in 42 JSON files under ai/src/providers/data/ and in 420 lines of generated *.models.ts. pi-tui ships prebuilt native addons for six platform targets under tui/native/, outside src/. The pi-env daemon is a Rust crate under env/daemon/, also outside src/. Roles in the table come from each package’s description field, its README, and one file checked per claim: PROTOCOL_VERSION = 8protocol/src/protocol.ts:5, the Unix-socket listener server/src/transports/unix/listener.ts:57, the two MCP transports mcp/src/transports/stdio.ts, and “no exporter” in the telemetry README telemetry/README.md:11.

![](images/d2382d1d217d2cbf1d4c3f310c1331cbb735c1a5c51cd9511fc47934442d3234.jpg)
The CLI is bigger than everything it depends on combined. Blue: packages the stable pi command imports. Grey: packages that only the experimental stack or the eval harness uses. From research/out/stats.txt (§package-lines).

## The dependency graph, as layers

The graph below uses only dependencies entries that name another @earendil-works/* package. No package declares a peer or optional dependency on another. Sorting packages by the longest chain beneath them gives five layers.

![](images/fe868b83e343a6937f960f96b41fc7814447bc6720d99f8792b43fe2317a091c.jpg)
The stable CLI runs on a chain of three packages. Solid: pi-coding-agent → pi-agent-core → pi-ai. Blue: everything else the stable CLI imports. Hatched grey: packages reached only by experimental code, dev dependencies or the private eval harness. Read from the dependencies and dev Dependencies of all fourteen package.json files at 28dcce2.

Three edges in the figure are not ordinary runtime dependencies. pi-coding-agent lists pi-client, pi-protocol and piserver under dev Dependencies only. Twenty files under CA/src/experimental/ import @earendil-works/pi-durable, which the package does not declare at all; the import resolves because the root package.json makes every directory under packages/ an npm workspace. And chord, although a declared runtime dependency of the CLI, is imported only by files under CA/src/experimental/: a grep of CA/src/ for the package name finds 26 files, all in that directory. pi-env has no importer anywhere in the repository outside its own tests.

## Runtime and binary

Thirteen packages require Node >=22.19.0 in engines ai/package.json:99; the private pi-evals declares none. The npm package installs pi as dist/bundle/cli.js CA/package.json:10. The build:binary script compiles a standalone executable with Bun: bun build --compile … --outfile dist/pi CA/package.json:43. The native terminal addons of pi-tui are described in pi-tui (p. 158).

## What PI_EXPERIMENTAL gates

One function holds the switch:

```typescript the experimental switch CA/src/core/experimental.ts TS export function areExperimentalFeaturesEnabled(): boolean {
    return process.env.PI_EXPERIMENTAL === "1";
}
```

The whole file, three lines.

The value must be exactly "1"; true or yes leave it of. Three things read the switch. runExperimentalCommand returns false unless it is on and the first argument is server or client CA/src/experimental/commands.ts:86. The interactive footer CA/src/modes/interactive/components/footer.ts:213 and first-time setup CA/src/cli/startup-ui.ts:141 check it. The switch alone does not reach the experimental code from an npm install, because the files list of the package excludes !dist/client, !dist/experimental and !dist/cli/experimental CA/package.json:31. The services README states the intent: “The server, client, and experimental package subpaths are excluded from npm packages and standalone binaries” CA/src/experimental/services/README.md. The experimental entry point is CA/src/experimental/cli.ts, which ./pitest.sh runs from a source checkout pi-test.sh; the path from there is the subject of the experimental stack (p. 166).

## R U L E O F T H U M B
If a file you are reading imports pi-durable, pi-server, pi-client, pi-protocol or chord, it is not on the path of the stable pi command. For the stable CLI, read pi-coding-agent, pi-agent-core and pi-ai first; then pi-tui, pi-mcp and pi-codemode when the question is about the screen, MCP or codemode.

Sources: packages/*/package.json (name, version, private, dependencies, dev Dependencies, engines, description); CA/package.json (bin, files, build:binary); package.json (workspaces); CA/src/core/experimental.ts; CA/src/experimental/commands.ts (runExperimentalCommand); CA/src/experimental/cli.ts; CA/src/cli/startup-ui.ts (shouldRunFirstTimeSetup); CA/src/experimental/services/README.md; pi-test.sh; protocol/src/protocol.ts (PROTOCOL_VERSION); server/src/transports/unix/listener.ts; mcp/src/transports/; telemetry/README.md; research/capture/stats.py; research/out/stats.txt (§package-lines)

# 1.3 The life of one prompt

One answered question that needs one file read is two model calls, 29 session events and 8 JSONL lines. The prompt reaches the disk before it reaches the model, and the run is over at agent_settled, not at agent_end.

You type “What does hello.txt say?” and press Enter. Before the answer appears, Pi has run extension hooks, written a session file, called the model twice, read a file and appended three more lines. This section follows that one input through the stable CLI in 22 steps, verified against the source. It then shows the real event stream and session file the capture kit recorded for the same exchange. Every step names the section that explains it in full; read this one first and use it as the map.

## The specimen

The capture kit drives a real AgentSession with the faux provider from pi-ai, so no network or API key is involved research/capture/one-turn.mjs. The faux model is scripted with two replies. The first is the text “Reading it.” plus a read call for hello.txt with stop reason tool Use. The second is “It says: Hello from the capture kit.” The script subscribes to the session, calls session.prompt(), and dumps every event and every line of the session file to research/out/one-turn.txt. It runs under Node 26.10.0 against pi-coding-agent 1.0.4 built from 28dcce2. In the interactive CLI the same session.prompt() call comes from the editor; the steps below start there.

Into the loop: steps 1–12
![](images/1ca4bc5e4989f4c34753af31470bca5e290289263944e1a078bfe6efd9e47774.jpg)
The prompt is on disk before the model sees it. Steps 1–12 of one prompt in the stable CLI. Solid arrows are calls, the dashed arrow is the provider stream, dotted arrows are agent events delivered to AgentSession. Verified against CA/src/core/agent-session.ts, agent/agent-loop.ts and CA/src/core/model-runtime.ts at 28dcce2. Schematic.

1 · Submit. The editor’s onSubmit handles built-in slash commands and ! bash lines itself. Anything else goes to the main loop of InteractiveMode, which awaits session.prompt(user Input) CA/src/modes/interactive/interactive-mode.ts:1247. Print, JSON and RPC modes call the same method run modes (p. 127).

2 · Prompt pipeline. AgentSession.prompt() runs a fixed sequence CA/src/core/agent-session.ts:1954. An extension command such as /foo runs and returns. Then input handlers may rewrite or consume the text. Skill commands and prompt templates expand. If a run is already streaming, the text is queued as a steer or follow-up and prompt() returns. Otherwise the model and its auth are checked, the previous answer is checked for compaction, and before_agent_start handlers run; they may add messages or replace the system prompt CA/src/core/agent-session.ts:2048. Each stage is in from prompt() to agent_settled (p. 67), each hook in extension events and contexts (p. 120).

3 · Hand-of. prompt() builds the user message, then prepends a system message when the system prompt sections difer from the transcript’s CA/src/core/agent-session.ts:2091. It calls agent.prompt(messages) inside _runAgentPrompt CA/src/core/agent-session.ts:1818. The system prompt is a message in the transcript, not a request field system prompt construction (p. 75).

4 · Loop start. runAgentLoop declares any tool changes on that system message as tools Added, then emits agent_start, turn_start and a message_start/message_end pair for each new message agent/agent-loop.ts:117. The loop is in the agent loop (p. 49), its events in agent events and the Agent class (p. 57).

5 · First write. AgentSession hears every agent event, passes it to extensions first and to subscribers second, and on message_end appends the message to the session CA/src/core/agent-session.ts:1127. The session file does not exist until a user or assistant message does CA/src/core/session-manager.ts:1166. At the user message’s message_end, SessionManager creates the file and writes all five entries it was holding in memory at once sessions, the JSONL tree (p. 86).

6 · Request projection. Before each model call the loop calls prepare Request agent/agent-loop.ts:219. AgentSession installs it to replace the context with a projection of the session tree CA/src/core/agent-session.ts:781. That projection is where compaction summaries and context edits take efect compaction and branch summaries (p. 92).

7 · Context hook. streamAssistantResponse passes the messages through transform Context and then convertToLlm agent/agent-loop.ts:390. In the CLI, transform Context emits the context extension event CA/src/core/sdk.ts:418.

8–9 · Model call. The loop calls the stream function agent/agent-loop.ts:403, which the SDK wires to model Runtime.stream Simple CA/src/core/sdk.ts:412. ModelRuntime resolves the provider and its credentials, then hands the request to the provider’s stream Simple CA/src/core/model-runtime.ts:739. The provider speaks one of the ten wire APIs over HTTP providers and models (p. 24), wire APIs and cross-provider hand-of (p. 36), auth, cost, retries and the catalog (p. 41).

10–11 · Stream. The provider returns AssistantMessageEvents: start, then text_*, thinking_* and toolcall_* deltas, then done or error the streaming event protocol (p. 30). The loop turns start into message_start, each delta into message_update, and done into message_end agent/agent-loop.ts:414.

12 · Second write. On the assistant’s message_end, AgentSession appends it as line 6 CA/src/core/agent-session.ts:1149.

Out through the tools: steps 13–22
![](images/20077880fa64b69d0ff774d7cf37f69683f79bada6424bc0f77a45b6603e9382.jpg)

A run ends at agent_settled, not at agent_end. Steps 13–22. tool_call and tool_result reach extensions through the beforeToolCall and afterToolCall hooks that AgentSession installs on the agent CA/src/core/agent-session.ts:640; the figure draws them from the loop, which calls the hooks. Verified against agent/agent-loop.ts and CA/src/core/agent-session.ts at 28dcce2. Schematic.

13–17 · One tool batch. The loop collects the tool Call blocks of the answer. It runs them in parallel unless the agent is set to sequential or a called tool declares execution Mode: "sequential" agent/agent-loop.ts:519; the default is "parallel" agent/agent.ts:253. For each call it emits tool_execution_start, validates the arguments and runs beforeToolCall, which raises the tool_call extension event; a { block: true } result turns into an error result without running the tool agent/agent-loop.ts:727. After execute(), afterToolCall raises tool_result, whose handlers may replace content, details or isError agent/agent-loop.ts:864. Then come tool_execution_end and the result message’s message_start/message_end. The read tool and the other seven are in built-in tools (p. 81).

## 18 · Third write. The tool result is line 7.

19 · Next turn. turn_end closes the turn agent/agent-loop.ts:287. Because the answer contained a tool call, the inner loop runs again. prepareNextTurn gives AgentSession a chance to compact and refresh the system prompt before steps 6–12 repeat CA/src/core/agent-session.ts:892. The second answer has no tool call, so it is the last; it becomes line 8.

20 · Loop end. With no tool calls, no steering and no follow-up messages left, the loop emits agent_end agent/agentloop.ts:320. AgentSession adds will Retry to it for subscribers CA/src/core/agent-session.ts:1128.

21 · After the loop. _runAgentPrompt does not return yet. It checks the last answer for a retryable error, then for compaction, then for queued messages, and calls agent.continue() if any of them needs another run CA/src/core/agent-session.ts:1839. Last, agent_before_settle handlers may ask to continue CA/src/core/agent-session.ts:1879. These branches are in AgentSession: wiring the runtime (p. 61) and compaction and branch summaries (p. 92).

22 · Settle. In a finally block, _emitAgentSettled emits agent_settled to extensions and then to subscribers CA/src/core/agent-session.ts:1066, and session.prompt() resolves.

## The captured event stream

The capture recorded 29 events from one session.prompt() call. Every one is an AgentSessionEvent delivered to session.subscribe().

<table><tr><td colspan="5">FIG. 1.6 ONE ANSWERED PROMPT, EVENT BY EVENT</td><td>TIMELINE</td></tr><tr><td>#</td><td>MS</td><td>EVENT</td><td>DETAIL</td><td>ON DISK</td><td>STEP</td></tr><tr><td>1</td><td>1</td><td>agent_start</td><td></td><td></td><td>4</td></tr><tr><td>2</td><td>1</td><td>turn_start</td><td>turn 1</td><td></td><td>4</td></tr><tr><td>3-4</td><td>1</td><td>message_start·message_end</td><td>system</td><td>held in memory</td><td>4-5</td></tr><tr><td>5-6</td><td>1</td><td>message_start·message_end</td><td>user</td><td>file created: lines 1-5</td><td>4-5</td></tr><tr><td>7</td><td>2</td><td>message_start</td><td>assistant</td><td></td><td>11</td></tr><tr><td>8-13</td><td>2</td><td>message_update×6</td><td>text_start·text_delta·text_end·toolcall_start·toolcall_delta·toolcall_end</td><td></td><td>11</td></tr><tr><td>14</td><td>2</td><td>message_end</td><td>assistant, tool Use</td><td>line 6</td><td>12</td></tr><tr><td>15</td><td>2</td><td>tool_execution_start</td><td>read</td><td></td><td>13</td></tr><tr><td>16</td><td>4</td><td>tool_execution_end</td><td>read</td><td></td><td>17</td></tr><tr><td>17-18</td><td>4</td><td>message_start·message_end</td><td>tool Result</td><td>line 7</td><td>17-18</td></tr><tr><td>19</td><td>4</td><td>turn_end</td><td>turn 1</td><td></td><td>19</td></tr><tr><td>20</td><td>4</td><td>turn_start</td><td>turn 2</td><td></td><td>19</td></tr><tr><td>21</td><td>4</td><td>message_start</td><td>assistant</td><td></td><td>11</td></tr><tr><td>22-25</td><td>4</td><td>message_update×4</td><td>text_start·text_delta×2·text_end</td><td></td><td>11</td></tr><tr><td>26</td><td>4</td><td>message_end</td><td>assistant, stop</td><td>line 8</td><td>12</td></tr><tr><td>27</td><td>4</td><td>turn_end</td><td>turn 2</td><td></td><td>19</td></tr><tr><td>28</td><td>4</td><td>agent_end</td><td></td><td></td><td>20</td></tr><tr><td>29</td><td>5</td><td>agent_settled</td><td></td><td></td><td>22</td></tr></table>

Two turns, 29 events, four writes. MS is milliseconds since the subscription, and the whole run takes 5 ms because the faux model answers from a script; with a real provider, events 7–14 and 21–26 wait on the network. STEP points into Fig. 1.4 (p. 16) and Fig. 1.5 (p. 18). From research/out/one-turn.txt (§events). The number of text_delta events changes from run to run; the order of events does not.

Turns are the unit of the loop: each one is a single model response plus the tools it called. Turn 1 spans events 2–19 and turn 2 spans events 20–27. Ten of the 29 events are message_update, the stream of deltas the TUI redraws from. The hooks of steps 2, 7, 14, 16 and 21 appear nowhere in this list. input, before_agent_start, context, tool_call, tool_result and agent_before_settle are dispatched to the ExtensionRunner only, and several are skipped when no handler is registered CA/src/core/agent-session.ts:651. A session.subscribe() listener never sees them extension events and contexts (p. 120).

## Eight lines on disk

The session file holds eight lines, one JSON object each research/out/one-turn.txt §session-jsonl. The first three describe the session; the last five are the conversation.

<table><tr><td>LINE</td><td>TYPE</td><td>ID ← PARENT</td><td>WRITTEN AT</td></tr><tr><td>1</td><td>session, version 3</td><td>01a10e5a-... (session id)</td><td>event 6</td></tr><tr><td>2</td><td>model_change faux/faux-1</td><td>2cd13c47 ← null</td><td>event 6</td></tr><tr><td>3</td><td>thinking_level_change off</td><td>f99fc4be ← 2cd13c47</td><td>event 6</td></tr><tr><td>4</td><td>message system: 5 sections, 4 tools Added</td><td>ff9b46f6 ← f99fc4be</td><td>event 6</td></tr><tr><td>5</td><td>message user</td><td>dd741bf1 ← ff9b46f6</td><td>event 6</td></tr><tr><td>6</td><td>message assistant, stop Reason: &quot;tool Use&quot;</td><td>0f939fd7 ← dd741bf1</td><td>event 14</td></tr><tr><td>7</td><td>message tool Result, toolCallId: &quot;call_1&quot;</td><td>81cb0f01 ← 0f939fd7</td><td>event 18</td></tr><tr><td>8</td><td>message assistant, stop Reason: &quot;stop&quot;</td><td>01f5647e ← 81cb0f01</td><td>event 26</td></tr></table>

Every entry names its parent, so eight lines form one branch of a tree. Lines 2 and 3 are appended in memory by createAgentSession when the session is new CA/src/core/sdk.ts:436; they reach the file with line 5. version is CURRENT_SESSION_VERSION CA/src/core/session-manager.ts:41. From research/out/one-turn.txt (§session-jsonl).

Line 6 carries the whole first answer: the text, the tool call, the model that produced it, its usage and why it stopped.

```json line 6: the first answer, with its tool call research/out/one-turn.txt JSONL
{
    "type": "message",
    "id": "0f939fd7",
    "parentId": "dd741bf1",
    "timestamp": "2026-10-05T23:16:41.752Z",
    "message": {
    "role": "assistant",
    "content": [
    { "type": "text", "text": "Reading it." },
    { "type": "tool Call", "id": "call_1", "name": "read", "arguments": { "path": "hello.txt" } }
    ],
    "api": "faux",
    "provider": "faux",
    "model": "faux-1",
    "usage": { ... },
    "stop Reason": "tool Use",
    "timestamp": 1791242201744,
    "thinking Level": "off"
    }
}
```

Cut from §session-jsonl, line 6. The usage object (token counts and a zero cost from the faux provider) is cut, and the two content blocks are set on one line each; keys are in stored order.

The entry has two timestamps. The outer timestamp is an ISO string written by SessionManager when it appends the entry. The inner message.timestamp is milliseconds since the epoch, set by whoever built the message — here the faux provider. Every entry type is read field by field in sessions, the JSONL tree (p. 86).

## F O O T G U N
agent_end is not the end of a run. After it, AgentSession can retry a failed response, compact and continue, or start a new run for queued messages, all inside the same prompt() call. Code that waits for idle must wait for agent_settled or for session.prompt() to resolve. Check will Retry on agent_end before treating it as final.

## V E R I F Y
From books/pi, run HOME=\$(mktemp -d) node research/capture/one-turn.mjs against the built checkout. It prints the event list and rewrites research/out/one-turn.txt. The empty HOME keeps your own settings and skills out of the run.

Sources: CA/src/modes/interactive/interactive-mode.ts (onSubmit, run loop); CA/src/modes/print-mode.ts; CA/src/modes/rpc/rpc-mode.ts (prompt command). CA/src/core/agent-session.ts (prompt, _runAgentPrompt, _handleAgentEvent, _emitExtensionEvent, _installAgentRequestProjection, _installAgentToolHooks). CA/src/core/agent-session.ts (_beforeToolCall, _afterToolCall, _installAgentNextTurnRefresh, _handlePostAgentRun, _runBeforeSettleBoundary, _emitAgentSettled, AgentSessionEvent). CA/src/core/sdk.ts (createAgentSession: new Agent, streamFn, transform Context, initial entries); CA/src/core/model-runtime.ts (stream Simple, prepare Request). CA/src/core/session-manager.ts (_hasConversation, _persist, append Message, CURRENT_SESSION_VERSION). agent/agent.ts (prompt, tool Execution, process Events); agent/agent-loop.ts (runAgentLoop, run Loop, streamAssistantResponse, executeToolCalls, prepareToolCall, finalizeExecutedToolCall). agent/types.ts (AgentEvent); research/capture/one-turn.mjs; research/out/one-turn.txt (§versions, §events, §session-jsonl)
