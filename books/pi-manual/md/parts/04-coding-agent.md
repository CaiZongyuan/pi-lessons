What the model is told, what it can touch, and how every step

lands in an append-only tree.

![](images/bbf486c236ec0537168863c78b7e033c341b532b078310505132d1059129f121.jpg)

## 4.1 System prompt construction

Pi's prompt is an ordered map ofnamed sections, not a string. That lets a mid-session change travel as a small patch appended to the transcript, while every earlier message stays byte for byte as it was sent.

Every request Pi sends starts with a system prompt, and a coding agent’s prompt changes during a session: a skill is installed, a tool is switched of, an extension adds instructions. This section shows the nine kinds of section and their order, and where each input is read from. Then it shows how a change becomes a SystemMessage patch in the transcript instead of a rewrite of the prompt. Pi’s own default is short: one sentence of preamble, the tool list, a handful of rules and pointers to its docs CA/src/core/system-prompt.ts:128.

## Sections, in order

buildSystemPromptSections() returns a Record<string, string> whose key order is the prompt’s order CA/src/core/system-prompt.ts:128. The preamble is untagged text. Every other section is wrapped as <name>\n…\n</name> CA/src/core/system-prompt.ts:190, so that a later update can name the section it replaces.

![](images/992da82f888f281ce563109e502519ec336bedc20396c4a2003bee88c5590b34.jpg)

A custom prompt replaces four sections, not one. When SYSTEM.md or --system-prompt supplies the preamble, tools, rules and docs are not built at all CA/src/core/system-prompt.ts:152. Hatched boxes are the ones a custom prompt drops; empty sections are omitted. Schematic; from buildSystemPromptSections().

preamble: the default text is one sentence: “You are an expert coding assistant operating inside pi, a coding agent harness. You help users by reading files, executing commands, editing code, and writing new files.” CA/src/core/system-prompt.ts:156. A custom prompt replaces it verbatim.

tools: one line - \${name}: \${snippet} per declared tool that has a prompt Snippet, then “In addition to the tools above, you may have access to other custom tools depending on the project.” Tools without a snippet are not listed, and with none left the list reads (none) CA/src/core/system-prompt.ts:157. Tools hidden by a prepare Loadout hook are left out, because the request does not declare them CA/src/core/system-prompt.ts:150.

rules: de-duplicated bullets from build Rules() CA/src/core/system-prompt.ts:88. First “Use bash for file operations like ls, rg, then extra prompt Guidelines, then always “Be concise in your responses” and “Show file paths clearly when working with files”.

docs: absolute paths to Pi’s README, docs/ and examples/, with the instruction to read them only “when the user asks about pi itself” CA/src/core/system-prompt.ts:162.

addendum: the append-prompt text, joined with blank lines when there are several CA/src/core/agent-session.ts:1697.

project_context: “Project-specific instructions and guidelines:” followed by one <project_instructions path="…">… </project_instructions> block per context file CA/src/core/system-prompt.ts:79. Which files load is covered in context files, skills, templates, themes and packages (p. 106).

skills: the <available_skills> index, one <skill> with name, description and location per skill that allows model invocation CA/src/core/skills.ts:358. Added only if read or bash is selected; if both are hidden the hint names no tool CA/src/core/system-prompt.ts:175.

cwd: the working directory, with backslashes turned into / CA/src/core/system-prompt.ts:183.

custom sections: extension sections from systemPromptOptions.sections. A name must match ^[a-z][a-z0-9_-]*\$ and must not be preamble, or the build throws “Invalid system prompt section name” CA/src/core/system-prompt.ts:58.

The working directory is the only fact about the environment in the prompt. No date, time, operating system or shell is injected anywhere in system-prompt.ts. An extension that wants them adds a section in before_agent_start (extension events and contexts (p. 120)).

## A stored prompt, from the capture kit

The prompt is not kept as text. It is stored as the sections of a system message, the fourth line of the one-turn session file (the life of one prompt (p. 15)). The capture ran with the four default tools, no context files, no skills and no append prompt, so it has five sections:

```json
{
    "type": "message",
    "id": "ff9b46f6",
    "parentId": "f99fc4be",
    "timestamp": "2026-10-05T23:16:41.751Z",
    "message": {
    "role": "system",
    "content": "",
    "sections": {
    "preamble": "You are an expert coding assistant operating inside pi, a coding agent harness. You help users by reading files, executing commands, editing code, and writing new files.",
    "tools": "<tools>\n- read: Read file contents\n- bash: Execute bash commands (ls, grep, find, etc.)\n-edit: Make precise file edits with exact text replacement, including multiple disjoint edits in one call\n-write: Create or overwrite files\n\nIn addition to the tools above, you may have access to other custom tools depending on the project.\n</tools>",
    "rules": "<rules>\n- Use bash for file operations like ls, rg, find\n- Use read to examine files instead of cat or sed.\n- You can inspect PI_* environment variables for current model and session details.\n- Use edit for precise changes (edits[].old Text must match exactly)\n...\n- Be concise in your responses\n- Show file paths clearly when working with files\n</rules>",
    "docs": "<docs>\nPi documentation (read only when the user asks about pi itself, its SDK, extensions, themes, skills, or TUI):\n...\n</docs>",
    "cwd": "<cwd>\n<tmp>/project\n</cwd>"
    },
    "timestamp": 1791242201750,
    "tools Added": [
    { "name": "read", "description": "Read the contents of a file. ...", "parameters": { ... }, "constrained Sampling": { "type": "json_schema", "strict": "prefer" } },
    ...
    ]
    }
}
```

Cut: four of the ten rules, the body of docs, and three of the four tools Added declarations (bash, edit, write). content is empty because the structured sections carry the prompt CA/src/core/system-prompt.ts:199. Paths are redacted by the capture script.

Three things in the record matter later. content is "". The tool declarations travel in the same message as tools Added, so prompt and tool set are replayed together. And the record is an ordinary message entry in the session tree; there is no separate “prompt state” entry type (sessions, the JSONL tree (p. 86)).

## Where the inputs come from

AgentSession._rebuildSystemPrompt() collects the base options from the resource loader and the tool registry CA/src/core/agent-session.ts:1686.

<table><tr><td>INPUT</td><td>SOURCE</td><td>SEE</td></tr><tr><td>custom Prompt</td><td>--system-prompt; else/.pi/SYSTEM.md if the project is trusted; else ~/.pi/agent/SYSTEM.md CA/src/core/resource-loader.ts:1209</td><td>configuration, models and auth (p. 99)</td></tr><tr><td>appendSystemPrompt</td><td>every --append-system-prompt (repeatable); else .pi/APPEND_SYSTEM.md if trusted; else ~/.pi/agent/APPEND_SYSTEM.md CA/src/core/resource-loader.ts:1223</td><td>CLI reference (p. 191)</td></tr><tr><td>context Files</td><td>loadProjectContextFiles(): the agent directory, then every ancestor from the filesystem root down to cwd CA/src/core/resource-loader.ts:232</td><td>context files, skills, templates, themes and packages (p. 106)</td></tr><tr><td>skills</td><td>the resource loader&#x27;s skills</td><td>context files, skills, templates, themes and packages (p. 106)</td></tr><tr><td>tool Snippets, tool Guidelines</td><td>prompt Snippet and prompt Guidelines of each registered tool definition</td><td>built-in tools (p. 81)</td></tr><tr><td>forceSystemPrompt</td><td>a before_agent_start handler that returns system Prompt</td><td>extension events and contexts (p. 120)</td></tr></table>

Two files of the same name are never combined. The trusted project file wins over the agent-directory file, for both SYSTEM.md and APPEND_SYSTEM.md. From resource-loader.ts (discoverSystemPromptFile, discoverAppendSystemPromptFile).

A CLI value that names an existing file is read as that file’s content, with any BOM stripped; anything else is used as literal text CA/src/core/resource-loader.ts:167.

docs/cli.md says --append-system-prompt “Appends text or an existing file to the system prompt”, and docs/configuration.md says APPEND_SYSTEM.md “Adds instructions”. Read together they suggest both apply. They do not: when any --append-systemprompt is given, discovery of APPEND_SYSTEM.md is skipped CA/src/core/resource-loader.ts:659. Pass the file as one of the flags if you want both.

## Prompt changes are transcript patches

_preparePromptAndToolLoadout() runs at the start of every prompt() and before every later turn, through prepareNextTurnWithContext CA/src/core/agent-session.ts:1724 CA/src/core/agent-session.ts:892. It never re-sends the whole prompt. It replays the transcript’s system messages into the sections the model has now, difs them against freshly built sections, and appends the diference.

![](images/504cda31a9751c67d650dd7ffd41cc4364a4700dfd9816d3971479011f9472c5.jpg)

Earlier messages are never rewritten. A changed section is sent as text, a removed one as null; tool changes ride on the same system message. The provider sends a later system message in place, framed as Updated system prompt section "name", only if the model accepts mid-conversation system messages. From agent-session.ts (_preparePromptAndToolLoadout), system-prompt.ts:217, agent-loop.ts:333, ai/utils/transcript.ts:115.

```typescript the patch: changed sections as text, removed sections as null CA/src/core/system-prompt.ts TS
export function diffSystemPromptSections(
    previous: Record<string, string | null>,
    current: SystemPromptSections,
): Record<string, string | null> | undefined {
    const patch: Record<string, string | null> = {};
    for (const [name, text] of Object.entries(current)) {
    if (previous[name] !== text) patch[name] = text;
    }
    for (const name of Object.keys(previous)) {
    if (current[name] === undefined) patch[name] = null;
    }
    return Object.keys(patch).length > 0 ? patch : undefined;
}
```
Complete function, lines 217–229.

Replay is defined once, in getCurrentSystemMessage(): walk every system message in order, concatenate non-empty content, set or delete sections by name, and resolve tools by applying each tools Removed then tools Added ai/utils/transcript.ts:73. Providers receive the patched transcript. renderSystemMessageUpdate() frames each patched section as Updated system prompt section "name": or Removed system prompt section "name".ai/utils/text.ts:28. When the model’s compat flag supportsMidConvoSystemMessages is false, which is the default, collapseSystemMessages() folds every system message into one leading message instead

ai/utils/transcript.ts:108.

That last case decides what the design buys. On a model that accepts mid-conversation system messages, installing a skill or connecting an MCP server appends a patch, and the provider’s cached prefix stays valid. On a model that does not, the collapsed head changes and the cached prefix is lost from that request on. Which models carry the flag is in wire APIs and cross provider hand-of (p. 36).

## F O O T G U N
A before_agent_start handler that returns system Prompt (or sets forceSystemPrompt) does not change the transcript. The structured sections are still difed and stored; the forced text is projected onto the request only, as one head message with the current tools CA/src/core/agent-session.ts:1773. The projection lasts for that run. A later run, and anything that reads the session file, sees the structured prompt. Prefer editing sections, tools or guidelines in systemPromptOptions, which docs/extensions.md also recommends.

W H A T T H I S M E A N S F O R Y O U

Read a session’s prompt by replaying its system messages, not by reading the first one.

Add instructions from an extension as a named section; a rename shows up as a removal plus an addition.

Put dates or environment facts in a section of their own; the default prompt carries only cwd.

Check supportsMidConvoSystemMessages before counting on cache hits after a prompt change.

Sources: CA/src/core/system-prompt.ts (normalizeBuildSystemPromptOptions, build Rules, buildSystemPromptSections, buildSystemPromptState, diffSystemPromptSections); CA/src/core/skills.ts (formatSkillsForPrompt); CA/src/core/agentsession.ts (_rebuildSystemPrompt, _preparePromptAndToolLoadout, _installAgentForcedPromptProjection, _installAgentNextTurnRefresh); CA/src/core/resource-loader.ts (resolvePromptInput, loadProjectContextFiles, discoverSystemPromptFile, discoverAppendSystemPromptFile); agent/agent-loop.ts (declareToolChanges); ai/types.ts (SystemMessage); ai/utils/transcript.ts (getCurrentSystemMessage, collapseSystemMessages, resolve Transcript); ai/utils/text.ts (renderSystemMessageUpdate); CA/docs/cli.md; CA/docs/configuration.md; CA/docs/extensions.md; research/out/one-turn.txt (§session-jsonl)

## 4.2 Built-in tools

Pi ships eight tools and enables four. All of them obey one output contract,

2,000 lines or 50 KB, so a single tool result can never fill the context window,

and the edit tool refuses any change it cannot place exactly once.

The built-in tools are the only way the default agent touches the machine. This section lists the eight tools and how they are selected, then states the truncation contract they share and each tool’s parameters and behaviour. It walks the edit algorithm with real error messages from the capture kit. It ends with the hook pipeline that wraps every call, including calls one tool makes on behalf of another.

## Eight tools, four on by default

ToolName is "read" | "bash" | "powershell" | "edit" | "write" | "grep" | "find" | "ls" CA/src/core/tools/index.ts:95. DEFAULT_TOOL_NAMES is ["read", "bash", "edit", "write"] CA/src/core/settingsmanager.ts:215. createReadOnlyTools() returns read, grep, find and ls CA/src/core/tools/index.ts:204.

Selection happens in three layers. The default Tools setting either replaces the default list with plain names or edits it with +name and -name modifiers, applied in list order CA/src/core/settings-manager.ts:236. On the command line, --tools is an allowlist and --exclude-tools a denylist; both accept * patterns, and --no-tools and --no-builtin-tools switch whole groups of CA/src/cli/args.ts:151. The full flag list is in CLI reference (p. 191).

Each tool is a ToolDefinition turned into an AgentTool by wrapToolDefinition(), which copies name, schema, prepare Arguments and constrained Sampling and passes a per-call context to execute CA/src/core/tools/tooldefinition-wrapper.ts:8. Paths resolve against the session’s cwd, with \~ expanded and a leading @ stripped CA/src/core/tools/path-utils.ts:48.

## The truncation contract

Every tool that returns file or process output passes it through truncate.ts. Two limits apply, and whichever is hit first wins:

```typescript the three limits every built-in tool shares CA/src/core/tools/truncate.ts export const DEFAULT_MAX_LINES = 2000;
export const DEFAULT_MAX_BYTES = 50 * 1024; // 50KB
export const GREP_MAX_LINE_LENGTH = 500; // Max chars per grep match line
```

T S

Lines 11–13, verbatim.

<table><tr><td>FUNCTION</td><td>KEEPS</td><td>USED BY</td></tr><tr><td>truncate Head</td><td>the start; never splits a line; if line 1 alone exceeds the byte limit, returns nothing and sets firstLineExceedsLimit</td><td>read, grep, find, ls</td></tr><tr><td>truncate Tail</td><td>the end; if the last line alone exceeds the byte limit, keeps its tail and sets lastLinePartial</td><td>bash, powershell (through OutputAccumulator), user ! commands</td></tr><tr><td>truncate Line(line, 500)</td><td>the first 500 characters, then ... [truncated]</td><td>grep match lines</td></tr><tr><td>truncate Middle(text, max Bytes)</td><td>half the budget from each end, with ...N chars truncated... between</td><td>MCP tool results, at 20 KiBCA/src/extensions/mcp/tools.ts:51</td></tr></table>

Head for files, tail for processes. A file is read from the top; a failing command prints its error last. From truncate.ts and the call sites of each function in CA/src.

Truncation is never silent. Each tool appends a notice that tells the model how to get the rest. The capture kit read a 2,500-line file with the real read tool:

```txt read long.txt (2,500 lines) → ...line 1999\nline 2000\n\n[Showing lines 1-2000 of 2500. Use offset=2001 to continue.]
read offset=10 limit=3 → line 10\nline 11\nline 12\n\n[2488 more lines in file. Use offset=13 to continue.]
read offset=9999 × Offset 9999 is beyond end of file (2500 lines total)
```

## Tool reference

<table><tr><td>TOOL</td><td>PARAMETERS</td><td>BEHAVIOUR</td></tr><tr><td>read</td><td>path, offset? (1-based), limit?</td><td>Applies Limit first, then truncate Head. A first line over 50 KB yields a sed -n &#x27;...p&#x27; ... | head -c 51200 hint instead of text. Images (jpg, png, gif, webp, bmp, detected from file content) come back as an image block, resized to the model&#x27;s input Limits; a note is added if the model has no image input. Tries macOS name variants: narrow no-break space before AM/PM, NFD, curly apostrophe CA/src/core/tools/path-utils.ts:86.</td></tr><tr><td>bash</td><td>command, timeout? (seconds, no default, at most 2,147,483.647)</td><td>Spawns the configured shell, detached in its own process group, stdout and stderr merged. Abort or timeout kills the process tree. Keeps the tail; the full output goes to a temp file pi-bash-*.log named in the notice. Updates are throttled to one per 100 ms. Non-zero exit returns isError with “Command exited with code N”.</td></tr><tr><td>powershell</td><td>as bash</td><td>The same definition with PowerShell&#x27;s config, a UTF-8 console prefix and temp prefix pi-powershell CA/src/core/tools/powershell.ts:16.</td></tr><tr><td>edit</td><td>path, edits: [{old Text,new Text}]</td><td>Several disjoint replacements in one call (algorithm below). prepare Arguments also accepts edits as a JSON string or a single object, and legacy top-level old Text/new Text CA/src/core/tools/edit.ts:103.</td></tr><tr><td>write</td><td>path, content</td><td>Creates parent directories, writes UTF-8, inside the per-file mutation queue. Returns “Successfully wrote to path”.</td></tr><tr><td>grep</td><td>pattern, path?, glob?, ignore Case?, literal?, context?, limit? = 100</td><td>Runs rg --json --line-number --color=never --hidden, downloading ripgrep if it is missing. Respects .gitignore. Lines cut at 500 characters; output capped at 50 KB.</td></tr><tr><td>find</td><td>pattern(glob), path?, limit? = 1000</td><td>Runs fd --glob --color=never --hidden --max-results N; returns paths relative to the search directory, with / separators.</td></tr><tr><td>ls</td><td>path?, limit? = 500</td><td>Reads the directory, sorts case-insensitively, appends / to directories, includes dotfiles.</td></tr></table>

Only four tools ask for strict schema decoding. read, bash (and so powershell), edit and write set constrained Sampling: {type: "json_schema", strict: "prefer"}; grep, find and ls do not. From CA/src/core/tools/*.ts.

bash has two outputs. The model sees the truncated tail. Programmatic callers such as codemode scripts (codemode (p. 151)) get structured Content — {output, truncated, full_output_path?, exit_code, wall_time_seconds} — whose output is capped at 1 MiB instead CA/src/core/tools/bash.ts:24. Unless exposeSessionEnvironment is false, the child’s environment carries PI_SESSION_ID, PI_SESSION_FILE, PI_PROVIDER, PI_MODEL and PI_REASONING_LEVEL, and the inherited values of those five are removed first CA/src/core/tools/bash.ts:186.

## The edit algorithm

edit makes all its replacements against the original file, never against the result of an earlier replacement in the same call. It runs inside withFileMutationQueue(), keyed by the file’s real path: two edits to one file run one after the other, edits to diferent files run in parallel CA/src/core/tools/file-mutation-queue.ts:32.

![](images/f54e0b62d263e24e02c1d2f7f92399a51c61426e6cbb7cea102352594e671def.jpg)
Five ways to refuse, one way to write. The first failing check wins and the file is not touched. From edit.ts (execute) and edit-dif.ts (applyEditsToNormalizedContent, normalizeForFuzzyMatch, applyReplacementsPreservingUnchangedLines). Schematic.

The capture kit ran the real tool against a file with a BOM, CRLF line endings and a duplicated line, then against a file with curly quotes and trailing spaces:

```textproto file: "\uFEFFconst a = 1;\r\nconst b = 2;\r\nconst b = 2;\r\n"
edit old Text absent    x Could not find the exact text in src.ts. The old text must match exactly including all whitespace and newlines.
edit old Text twice    x Found 2 occurrences of the text in src.ts. The text must be unique. Please provide more context to make it unique.
edit two overlapping edits    x edits[1] and edits[0] overlap in src.ts. Merge them into one edit or target disjoint regions.
edit identical replacement    x No changes made to src.ts. The replacement produced identical content. This might indicate an issue with special characters or the text not existing as expected.
edit LF old Text on CRLF file → Successfully replaced 1 block(s) in src.ts.
file after: "\uFEFFconst a = 10;\r\nconst b = 2;\r\nconst b = 2;\r\n"

file: "say("hello"); \nkeep('this');\n"
edit with ASCII quotes (fuzzy) → Successfully replaced 1 block(s) in src.ts.
file after: "say(\"bye");\nkeep('this');\n"
```

The last pair shows the fuzzy path’s limit. The model wrote ASCII quotes, so matching fell back to normalised text. The touched line came back normalised: its trailing spaces are gone. The untouched line kept its curly quotes. In a multi-edit call, one fuzzy edit switches every edit to normalised matching, and every line any edit touches is written in normalised form.

The overlap message names edits by sorted position, so edits[1] and edits[0] is not a typo. More important: uniqueness is counted in fuzzy space even when the exact match succeeded CA/src/core/tools/edit-diff.ts:328. Two lines that difer only in quote style or trailing whitespace count as two occurrences, and the edit is refused. Add a neighbouring line to old Text.

## The hook layer around every call

Every tool call, built-in or not, passes through the same pipeline in agent-loop.ts agent/agent-loop.ts:707. AgentSession installs the two hooks that connect it to extensions CA/src/core/agent-session.ts:640.

![](images/f18254134a5a7f37a60b0e06b209332517f7c4a2662e0491af405599462e7081.jpg)

Extensions see validated arguments and can change them. tool_call handlers receive the same object that execute gets, so mutating event.input changes the call; a block result becomes an error result with the handler’s reason. tool_result handlers can replace content, details and isError, and images are resized after them. From agent-loop.ts (prepareToolCall, finalizeExecutedToolCall) and agent-session.ts (_beforeToolCall, _afterToolCall).

An unknown tool name, a validation failure, a block and a thrown error all come back as a tool result with isError: true; none of them throws out of the loop agent/agent-loop.ts:807. The event names and result shapes are in extension events and contexts (p. 120).

The same pipeline runs for nested calls: a tool that calls ctx.execute Tool(), as codemode scripts do. A nested call’s id is <parent id>/<n>, counting from 1, and its tool_execution_* events and hook events carry parentToolCallId

CA/src/core/nested-tool-calls.ts:188. The parent’s tool result records the nested calls within NESTED_CALL_LIMITS: at most 256 calls, 8 KiB of arguments per call, 32 KiB of arguments in total, and 500 characters per error. Arguments over a limit are omitted, calls beyond 256 are dropped, and the record is marked incomplete CA/src/core/nested-tool-calls.ts:26.

W H A T T H I S M E A N S F O R Y O U

Tell the model to page with offset; the notice already does, so do not raise the limits to avoid it.

Read structured Content.output from scripts that need more than the last 2,000 lines of a command.

Expect edit to refuse ambiguous text; widen old Text rather than retrying the same call.

Put permission checks in tool_call: they then apply to nested calls too.

Sources: CA/src/core/tools/index.ts (ToolName, createReadOnlyTools); CA/src/core/settings-manager.ts (DEFAULT_TOOL_NAMES, resolveDefaultTools); CA/src/cli/args.ts (-tools, -exclude-tools); CA/src/core/tools/tool-definition-wrapper.ts; CA/src/core/tools/path-utils.ts; CA/src/core/tools/truncate.ts; CA/src/core/tools/{read,bash,powershell,edit,editdiff,write,grep,find,ls,file-mutation-queue}.ts; CA/src/core/tools/renderers/bash.ts (BASH_UPDATE_THROTTLE_MS); CA/src/extensions/mcp/tools.ts (MCP_OUTPUT_MAX_BYTES); agent/agent-loop.ts (prepareToolCall, runToolCall, finalizeExecutedToolCall); CA/src/core/agent-session.ts (_beforeToolCall, _afterToolCall, _executeNestedToolCall); CA/src/core/nested-tool-calls.ts (NESTED_CALL_LIMITS); research/capture/built-in-tools-edit.mjs; research/out/built-intools-edit.txt

#### 4.3 Sessions: the JSONLtree

A session file is append-only and every entry names its parent, so one file holds a whole tree ofconversations. Which branch is current lives only in memory, and a restart picks the last line written.

Everything an agent did in a session is recoverable from one JSONL file: the prompt it was given, each model response, each tool result, and every branch the user tried. This section shows where the file lives and how it is named, then the header and the eleven entry types. It follows the tree that parentId builds and the leaf pointer that walks it. It ends with loading and migration, and with how the entries on one path become the messages sent to the model. The code is SessionManager, 2,013 lines in one file CA/src/core/session-manager.ts:987.

## Location, naming, identity

Directory: \~/.pi/agent/sessions/--<cwd>--/. The cwd has its leading / or \ removed and every /, \ and : replaced by - CA/src/core/session-manager.ts:592. /Users/me/proj becomes --Users-me-proj--.

Directory precedence: --session-dir, then \$PI_CODING_AGENT_SESSION_DIR, then the session Dir setting, then the percwd default CA/src/main.ts:688.

File name: <ISO timestamp with : and . replaced by ->_<session id>.jsonl CA/src/core/sessionmanager.ts:1079. The capture kit’s file is 2026-10-05T23-16-41-747Z_01a10e5a-ea92-7225-8c3a-c148ed81dc38.jsonl.

Session id: a UUIDv7 CA/src/core/session-manager.ts:264, so ids sort by creation time. A custom id from --session-id or the SDK must match ^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\$ CA/src/core/session-manager.ts:268.

Entry id: the first 8 hex characters of randomUUID(), checked against existing ids up to 100 times, then a full UUID CA/src/core/session-manager.ts:277.

Files are created lazily. Until the session holds a user or assistant message, entries stay in memory; opening and closing Pi without typing leaves no file CA/src/core/session-manager.ts:1166. The first flush opens the file with flag "wx", which fails if it exists, and writes every bufered entry. After that, each entry is one appendFileSync of one line CA/src/core/sessionmanager.ts:1172. The sessions-tree capture shows the switch: after a model_change the file has 0 lines on disk; after the first user message it has 3.

## The file format

Line 1 is a header. Every later line is one entry with type, id, parentId and an ISO timestamp. CURRENT_SESSION_VERSION is 3 CA/src/core/session-manager.ts:41. These are the first three lines of the one-turn capture, as Pi wrote them:

```txt header, then the first two entries of a real session research/out/one-turn.txt (§session-jsonl, lines 1-3) JSON
{"type":"session","version":3,"id":"01a10e5a-ea92-7225-8c3a-c148ed81dc38","timestamp":"2026-10-05T23:16:41.747Z","cwd":"<tmp>/project"}
{"type":"model_change","id":"2cd13c47","parentId":null,"timestamp":"2026-10-05T23:16:41.749Z","provider":"faux","modelId":"faux-1"}
{"type":"thinking_level_change","id":"f99fc4be","parentId":"2cd13c47","timestamp":"2026-10-05T23:16:41.749Z","thinking Level":"off"}
```

Complete lines, re-serialised on one line each. The header has no parentId and is not an entry. parent Session is absent because it is undefined for a new session and JSON.stringify drops it.

<table><tr><td>TYPE</td><td>EXTRA FIELDS</td><td>IN MODEL CONTEXT</td></tr><tr><td>message</td><td>message: an AgentMessage (user, assistant, tool Result, system, bash Execution, custom)</td><td>yes</td></tr><tr><td>thinking_level_change</td><td>thinking Level</td><td>no; sets state</td></tr><tr><td>model_change</td><td>provider, modelId</td><td>no; sets state</td></tr><tr><td>usage</td><td>kind (such as cache_warm), provider, model, usage, note?</td><td>no</td></tr><tr><td>compaction</td><td>summary, firstKeptEntryId, tokens Before, details?, usage?, from Hook?, system Message?</td><td>yes, as checkpoint + summary</td></tr><tr><td>branch_summary</td><td>fromId, summary, details?, usage?, from Hook?</td><td>yes, as a summary</td></tr><tr><td>custom</td><td>custom Type, data?</td><td>no; extension state</td></tr><tr><td>custom_message</td><td>custom Type, content, details?, display</td><td>yes, as a custom message</td></tr><tr><td>context_edit</td><td>targetId, replacement: {content} | null</td><td>changes another entry</td></tr><tr><td>label</td><td>targetId, label (undefined clears it)</td><td>no; bookmark</td></tr><tr><td>session_info</td><td>name?</td><td>no; display name</td></tr></table>

Eleven entry types, and no separate prompt state. The prompt and tool set are system messages inside message entries (system prompt construction (p. 75)); replaying them in order gives the current state. From session-manager.ts (SessionEntry union, lines 183–194).

## The tree and the leaf pointer

Every append sets parentId to the current leaf, then moves the leaf to the new entry CA/src/core/session-manager.ts:1191. In a session with no branching the tree is a chain. The one-turn capture is that chain, eight lines long:

```txt
FIG. 4.5 THE ONE-TURN SESSION AS A TREE
header · session 01a10e5a... · version 3 line 1 · not an entry
2cd13c47 · model_change · faux/faux-1 line 2 · parentId null: the root
f99fc4be · thinking_level_change · off line 3
ff9b46f6 · message · system line 4 · five sections, four tools dd741bf1 · message · user line 5 · What does hello.txt say?
0f939fd7 · message · assistant line 6 · tool Call read, call_1
81cb0f01 · message · tool Result line 7 · Hello from the capture kit.
01f5647e · message · assistant line 8 · leaf on load: the last line
```

T R E E

Each line’s parentId is the line before it. The root is the first entry, not the header, and the system message sits inside the tree like any other message. Drawn from research/out/one-turn.txt (§session-jsonl); ids are from that run

Branching does not copy or delete anything. branch(id) moves the leaf to an earlier entry, and the next append becomes a sibling of whatever followed it CA/src/core/session-manager.ts:1579. The sessions-tree capture builds a real branched file with SessionManager and then reopens it:

```txt
FIG. 4.6 A BRANCHED SESSION, REOPENED

mc · model_change line 2 · root
└ u1 · user line 3
    └ a1 · assistant line 4 · label "plan" points here
    └ u2 · user line 5 · branch A
    | └ a2 · assistant line 6
    | └ bs · branch_summary · fromId=lb line 10 · leaf after reopen
    └ u3 · user line 7 · branch B, after branch(a1)
    └ a3 · assistant line 8
    └ lb · label · targetId=a1 line 9 · a child of the leaf, not of a1
```

T R E E

Labels are tree entries, and they move the leaf. appendLabelChange(a1) hung the label under a3, the leaf at the time, so the later branch_summary records fromId=lb, a label, as the branch it left. A final branch(u1) without an append was lost: the reopened session’s leaf is bs. From research/out/sessions-tree.txt; names replace the 8-hex ids.

The leaf is never written down. On load, _buildIndex() sets it to the last entry in file order CA/src/core/sessionmanager.ts:1103. A branch therefore survives a restart only once something has been appended under it. Labels resolve the same way: the latest label entry for a target, in file order, wins, and a label of undefined clears it.

<table><tr><td>OPERATION</td><td>EFFECT</td></tr><tr><td>branch(id) CA/src/core/session-manager.ts:1579</td><td>moves the leaf; the next append creates a sibling</td></tr><tr><td>reset Leaf() CA/src/core/session-manager.ts:1591</td><td>leaf = null; the next append is a new root (used to re-edit the first message)</td></tr><tr><td>branchWithSummary(fromId, summary)CA/src/core/session-manager.ts:1600</td><td>moves the leaf and appends a branch_summary under it; fromId is the old leaf, or &quot;root&quot;</td></tr><tr><td>createBranchedSession(leafId) CA/src/core/session-manager.ts:1632</td><td>new file with only the root-to-leaf path; label entries dropped, the path re-chained, labels re-appended at the end; parent Session = old file</td></tr><tr><td>fork From(src, target Cwd) CA/src/core/session-manager.ts:1815</td><td>copies every entry of another file into a new file for another cwd (--fork, cross-project --session)</td></tr></table>

Nothing is ever deleted. Each operation either moves the in-memory leaf or writes a new file. From session-manager.ts (Branching).

get Tree() makes an entry whose parent is missing a root, and sorts each node’s children by timestamp CA/src/core/sessionmanager.ts:1529. A path walk from such an entry stops at the gap.

## Loading and migration

loadEntriesFromFile() reads in 1 MiB chunks, splits on \n, and skips blank and malformed lines without a warning CA/src/core/session-manager.ts:627. If the first parsed entry is not a header with a string id, it returns []. A last line without a trailing newline is kept and the newline is appended to the file.

An empty file is initialised with a new header. A non-empty file that yields no entries throws “Session file is not a valid pi session: path” and is not modified CA/src/core/session-manager.ts:1039.

Migrations run when the header’s version is below 3 (absent counts as 1), and the whole file is then rewritten CA/src/core/session-manager.ts:337:

v1 → v2: assign an id to every entry, chain parentId linearly in file order, and convert a compaction’s firstKeptEntryIndex into firstKeptEntryId CA/src/core/session-manager.ts:287.

v2 → v3: the message role hook Message becomes custom CA/src/core/session-manager.ts:316.

## Context reconstruction

The model never sees the file. It sees a projection of one path through it, rebuilt by buildSessionProjection() CA/src/core/session-manager.ts:543.

![](images/16403b5bdc983dc2b3b5ef16d8b00477ca2e8a12fc4bdb3d540901d54a17122c.jpg)

Only the newest compaction on the path contributes a summary. An older compaction that falls inside the kept range is projected as nothing, and raw system messages before the cut are dropped because the compaction carries its own snapshot. From session-manager.ts (buildSessionPath, getSessionContextSettings, buildContextEntries, buildSessionProjection, sessionEntryToContextMessages).

Path: from the leaf back to the root, then reversed CA/src/core/session-manager.ts:390. Siblings on other branches are not on it.

Settings: thinking Level is the last thinking_level_change on the path, default "off". model is the last model_change or assistant message, whichever is later CA/src/core/session-manager.ts:418.

Compaction: with a compaction C on the path, the entries are C, then the entries from C.firstKeptEntryId up to C minus raw system messages, then everything after C CA/src/core/session-manager.ts:476. compaction and branch summaries (p. 92) covers how C is made.

Context edits: the latest context_edit per target applies; null omits the target, a value replaces only its content CA/src/core/session-manager.ts:519. Only edits on the current path count, so an edit is branch-local.

Messages: a message yields its message; custom_message a custom message; branch_summary a branch Summary message; compaction its system Message snapshot followed by a compaction Summary message; every other type yields nothing CA/src/core/session-manager.ts:439.

Run against the branched capture, the reopened session’s path is mc → u1 → a1 → u2 → a2 → bs, and its context is five messages: user, assistant, user, assistant, branch Summary. The model_change sets state and contributes no message; branch B and its label are not on the path.

## F O O T G U N
Moving the leaf is not saved. /tree navigation without a summary or label, branch() from the SDK, or an extension that repositions the leaf all leave the file unchanged until the next append CA/src/core/agent-session.ts:4113. If Pi exits first, the session reopens at the last line of the file, and that line can belong to the branch the user just left. Appending a label to the target is the cheapest way to pin a position.

W H A T T H I S M E A N S F O R Y O U

Parse a session by building the parentId index, not by reading lines in order.

Treat the last line as the leaf only for a file at rest; a running Pi can hold its leaf elsewhere.

Use custom entries for extension state and custom_message for text the model should see.

Hide or rewrite an earlier message with context_edit; the original line stays in the file.

Sources: CA/src/core/session-manager.ts (SessionHeader, SessionEntry types, createSessionId, assertValidSessionId, generateId, migrateV1ToV2, migrateV2ToV3, migrateToCurrentVersion, buildSessionPath, getSessionContextSettings, sessionEntryToContextMessages, buildContextEntries, projectContextEntry, buildSessionProjection, getDefaultSessionDirPath, loadEntriesFromFile, SessionManager: _setSessionFile, new Session, _buildIndex, _hasConversation, _persist, _appendEntry, appendLabelChange, get Tree, branch, reset Leaf, branchWithSummary, createBranchedSession, fork From); CA/src/main.ts (session directory); CA/docs/session-format.md; research/capture/sessions-tree.mjs; research/out/sessions-tree.txt; research/out/one-turn.txt (§session-files, §sessionjsonl)

## 4.4 Compaction and branch summaries

When the context windowfills, Pi asks the model to write a structured checkpoint of the old messages and appends it as one entry. The file keeps every raw line; only the projection the model sees gets shorter.

A long coding session outgrows any context window. Pi’s answer is compaction: summarise the oldest part of the current path, keep the newest part verbatim, and record the result as a compaction entry in the session tree (sessions, the JSONL tree (p. 86)). This section shows when compaction triggers and how overflow is recovered, how the cut point is chosen, and how the summary is generated and with what prompt. It ends with what the model sees afterwards, and with the branch summary that /tree writes when the user leaves a branch.

## When it triggers

```typescript the defaults and the threshold test CA/src/core/compaction/compaction.ts TS
export const DEFAULT_COMPACTION_SETTINGS: CompactionSettings = {
    enabled: true,
    reserve Tokens: 16384,
    keepRecentTokens: 20000,
};
...
export function should Compact(context Tokens: number, context Window: number, settings: CompactionSettings):
boolean {
    if (!settings.enabled) return false;
    return context Tokens > context Window - settings.reserve Tokens;
}
```
Lines 126–130 and 267–270; the cut hides the token-estimation functions between them.

With the defaults, a 200,000-token window compacts above 183,616 tokens. reserve Tokens and keepRecentTokens can be overridden per model under compaction.model Overrides["provider/modelId"], with exact, case-sensitive keys; enabled stays global CA/src/core/settings-manager.ts:940. All three keys are in settings reference (p. 202).

Context size is measured, then estimated. The base is the last valid assistant message’s usage.total Tokens, or the sum of its parts; aborted, errored and all-zero responses do not count CA/src/core/compaction/compaction.ts:148. Messages after it are estimated at characters ÷ 4, with an image counted as 4,800 characters CA/src/core/compaction/compaction.ts:276. Usage captured before the latest context_edit or compaction on the branch is not trusted, and the whole projection is estimated instead CA/src/core/compaction/compaction.ts:227.

<table><tr><td>TRIGGER POINT</td><td>WHERE</td><td>REASON</td></tr><tr><td>Before each later turn</td><td>prepareNextTurnWithContext → _compactBeforeNextAssistantResponse CA/src/core/agent-session.ts:764</td><td>threshold</td></tr><tr><td>Per request, virtual model</td><td>prepare Request, against the routed model&#x27;s window CA/src/core/agent-session.ts:826</td><td>threshold</td></tr><tr><td>After a run</td><td>_handlePostAgentRun → _checkCompaction CA/src/core/agent-session.ts:1870</td><td>threshold or overflow</td></tr><tr><td>Before a prompt</td><td>prompt() → _checkCompaction, aborted responses included CA/src/core/agent-session.ts:2042</td><td>threshold</td></tr><tr><td>Manual</td><td>/compact [instructions] → compact(); aborts the current run first and never retries it CA/src/core/agent-session.ts:2750</td><td>manual</td></tr></table>

Five entry points, one generator. Manual and automatic compaction both end in _runDefaultCompaction() and the compact() function from compaction/, unless a session_before_compact handler cancels or supplies the result. From agent-session.ts.

Overflow is handled after a run CA/src/core/agent-session.ts:2933. A context-overflow error, or a length stop that ended below the model’s own output limit, starts recovery. Pi hides the failed response and its tool results with context_edit entries whose replacement is null CA/src/core/agent-session.ts:1224, compacts, and retries the turn once. A second failure ends with “Context overflow recovery failed after one compact-and-retry attempt. Try reducing context or switching to a larger-context model.” (or “Truncated response recovery failed after one compact-and-retry attempt.” for a length stop). An overflow reported by a diferent model than the current one is ignored, and so is any assistant message older than the latest compaction. If the response completed with stop but still exceeded the window, Pi compacts without retrying.

## Choosing the cut point

prepare Compaction() works on the projected path, not on raw lines CA/src/core/compaction/compaction.ts:872. It starts after the newest compaction that contributes a summary, so the entries that compaction kept are summarised again, together with its summary. Then findProjectedCutPoint() walks backwards from the newest entry, summing estimated tokens until the total reaches keepRecentTokens, and snaps to the nearest valid cut point at or after that entry CA/src/core/compaction/compaction.ts:802

![](images/d508e5083584b34eb1687ac72838421cea0f5c8088b3a3fcce3aeebf1bac220c.jpg)
A cut never lands on a tool result. Valid cut points are entries that yield a user, assistant, bash Execution, custom, branch Summary or compaction Summary message, so a call and its result stay on the same side. Here the cut lands on an assistant, mid-turn, so the turn’s start is summarised separately. Schematic; from compaction.ts (isCutPointMessage, isTurnStartMessage, findProjectedCutPoint, prepare Compaction).

After snapping, the cut moves back over adjacent entries that contribute no message, such as a model_change, so they stay with the kept part. If the cut entry does not start a turn, the cut is a split turn: the messages from the turn’s start up to the cut become turnPrefixMessagesCA/src/core/compaction/compaction.ts:903. A turn starts at a user, bash Execution, custom, branch Summary or compaction Summary message.

prepare Compaction() returns undefined when the path already ends in a compaction or there is nothing to summarise; manual compaction reports these as “Already compacted” and “Nothing to compact (session too small)” CA/src/core/agentsession.ts:2771. Otherwise it returns a CompactionPreparation, which session_before_compact handlers receive:

firstKeptEntryId: the id of the first entry kept verbatim.

messagesToSummarize: messages from the previous boundary to the cut, or to the turn start for a split turn, with system messages removed.

turnPrefixMessages: the split turn’s messages before the cut; empty otherwise.

previous Summary: the summary of the compaction being replaced, used to select the update prompt.

file Ops: files read, written and edited, taken from read, write and edit tool calls, from nested calls recorded on tool results, and from the previous compaction’s details if Pi generated it CA/src/core/compaction/compaction.ts:60.

tokens Before: the projected context estimate before compaction.

## Generating the summary

![](images/c2cd8a508325eb76ab605778d3c79fc3878acb506715373942a0b711226e330c.jpg)

Two model calls at most, both one-shot. With the default 16,384-token reserve the history summary may use up to 13,107 output tokens and the turn-prefix summary 8,192, each capped by the model’s max Tokens. From compaction.ts (compact, generateSummaryWithUsage, generateTurnPrefixSummary) and agentsession.ts (compact, _runAutoCompaction).

The summary request has its own system prompt, SUMMARIZATION_SYSTEM_PROMPT: “You are a context summarization assistant. … Do NOT continue the conversation. Do NOT respond to any questions in the conversation. ONLY output the structured summary.” CA/src/core/compaction/utils.ts:161. The conversation is serialised to text, so the model reads it instead of continuing it CA/src/core/compaction/utils.ts:114:

```txt the user message of a summary request CA/src/core/compaction/compaction.ts (generateSummaryWithUsage, SUMMARIZATION_PROMPT) PROMPT
<conversation>
[User]: ...
[Assistant thinking]: ...
[Assistant]: ...
[Assistant tool calls]: read(path="src/args.ts"); edit(path=..., edits=[...])
[Tool result]: ...first 2,000 characters...
[... N more characters truncated]
</conversation>
<previous-summary>
...
</previous-summary>
The messages above are a conversation to summarize. Create a structured context checkpoint summary that another LLM will use to continue the work.
Use this EXACT format:
## Goal
## Constraints & Preferences
## Progress
### Done
### In Progress
### Blocked
## Key Decisions
## Next Steps
## Critical Context
Keep each section concise. Preserve exact file paths, function names, and error messages.
Additional focus: <custom instructions>
```

Assembled from the code; the tool-call arguments are illustrative and the bracketed hints under each heading are cut. <previous-summary> appears only when a previous summary exists, and then UPDATE_SUMMARIZATION_PROMPT replaces the instructions with rules to preserve, add and move items from In Progress to Done. Additional focus: appears only with /compact instructions.

For a split turn, the turn prefix is summarised separately under the headings Original Request, Progress So Far and Context Needed to Continue. The two texts are joined as history\n\n---\n\n**Turn Context (split turn):**\n\nprefix, and with no older history the first part reads “No prior history.” CA/src/core/compaction/compaction.ts:1032. Then the file lists are appended as <read-files> and <modified-files> blocks, sorted, with a file that was both read and modified listed only as modified CA/src/core/compaction/utils.ts:67.

Every summary request runs with cache Retention: "none" and a fresh UUIDv7 sessionId, through the session’s retry policy CA/src/core/compaction/compaction.ts:619. Reasoning is requested only if the model supports it and the thinking level resolved for the request is not off CA/src/core/compaction/compaction.ts:606. A response that stops with error or length, or that contains a tool call, fails the compaction: a length stop is a partial summary and is never stored CA/src/core/compaction/compaction.ts:585.

## What the model sees afterwards

append Compaction() stores the summary, firstKeptEntryId, tokens Before, details and usage, plus system Message: the complete replayed prompt and tool set at that moment CA/src/core/session-manager.ts:1261. The next projection of the path is:

```txt
[ compaction.system Message ] ← one system message: every section, every tool
[ user: "The conversation history before this point was compacted into the following summary:
<summary>
...
</summary>" ]
[ entries from firstKeptEntryId up to the compaction, raw system messages removed ]
[ entries appended after the compaction ]
```

The summary reaches the provider as a user message, built by convertToLlm() from COMPACTION_SUMMARY_PREFIX and COMPACTION_SUMMARY_SUFFIX CA/src/core/messages.ts:11. The raw entries stay in the JSONL file; compaction changes only what buildSessionProjection() returns. Moving the leaf to a branch that does not contain the compaction brings the full history back.

The snapshot replaces every earlier system message, so the summary follows a single complete prompt rather than a chain of patches. That resets the prompt history as well as the conversation. It also means the first request after compaction has a new prefix, and the provider cache starts over.

## Branch summaries

When the user jumps to another node with /tree (slash commands and keybindings (p. 197)), Pi can summarise the branch being left. navigate Tree() does it in five steps CA/src/core/agent-session.ts:3949:

1. collectEntriesForBranchSummary(old Leaf, target) collects the entries from the old leaf back to the deepest ancestor shared with the target CA/src/core/compaction/branch-summarization.ts:108.

2. A session_before_tree handler can cancel, supply a summary, replace or extend the instructions, or set a label.

3. generateBranchSummary() keeps entries newest first within context Window − branch Summary.reserve Tokens (16,384 by default; a window of 0 counts as 128,000), skips tool results, and squeezes in an older compaction or branch summary while under 90 % of the budget CA/src/core/compaction/branch-summarization.ts:195. The prompt has the compaction headings minus Critical Context, and max Tokens is min(4096, model.max Tokens).

4. The result is prefixed with “The user explored a diferent conversation branch before returning here.\nSummary of that exploration:\n\n” and followed by the file lists CA/src/core/compaction/branch-summarization.ts:253.

5. If the target is a user or custom message, the new leaf is the target’s parent and its text goes back into the editor. Otherwise the leaf is the target. branchWithSummary() then appends the summary as a child of the new leaf, not of the old branch.

In context the entry becomes a user message wrapped in “The following is a summary of a branch that this conversation came back from:” and <summary> tags CA/src/core/messages.ts:19. Setting branch Summary.skip Prompt skips the interactive question and defaults to no summary.

## R U L E O F T H U M B
If you only want the summary to focus on something, pass instructions to /compact. If you need a diferent summary altogether, return one from session_before_compact; it is stored with from Hook: true and its details are not read back as file lists. If one model has a far larger window than the others, set a model Overrides entry for it instead of changing the global reserve Tokens.

Sources: CA/src/core/compaction/compaction.ts (DEFAULT_COMPACTION_SETTINGS, calculateContextTokens, getAssistantUsage, estimateContextTokens, estimateProjectedContextTokens, should Compact, estimate Tokens, isCutPointMessage, isTurnStartMessage, findProjectedCutPoint, prepare Compaction, SUMMARIZATION_PROMPT, UPDATE_SUMMARIZATION_PROMPT, TURN_PREFIX_SUMMARIZATION_PROMPT, getSummarizationFailure, complete Summarization, generateSummaryWithUsage, compact); CA/src/core/compaction/utils.ts (extractFileOpsFromMessage, computeFileLists, formatFileOperations, serialize Conversation, SUMMARIZATION_SYSTEM_PROMPT); CA/src/core/compaction/branch-summarization.ts (collectEntriesForBranchSummary, prepareBranchEntries, generateBranchSummary); CA/src/core/agent-session.ts (_compactBeforeNextAssistantResponse, _installAgentRequestProjection, _handlePostAgentRun, prompt, compact, _checkCompaction, _runAutoCompaction, _omitRecoveryAttempt, navigate Tree); CA/src/core/session-manager.ts (append Compaction, buildContextEntries); CA/src/core/messages.ts (COMPACTION_SUMMARY_PREFIX, BRANCH_SUMMARY_PREFIX, convertToLlm); CA/src/core/settings-manager.ts (getCompactionSettings, getBranchSummarySettings); CA/docs/compaction.md
