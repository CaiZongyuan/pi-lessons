What the model is told, what it can touch, and how every step

lands in an append-only tree.

模型被告知了什么、它能触碰到什么，以及每一步如何落进一棵仅追加树。

![](images/bbf486c236ec0537168863c78b7e033c341b532b078310505132d1059129f121.jpg)

## 4.1 System prompt construction

## 4.1 系统提示词构建

Pi's prompt is an ordered map ofnamed sections, not a string. That lets a mid-session change travel as a small patch appended to the transcript, while every earlier message stays byte for byte as it was sent.

Pi 的提示词是一张有序的具名小节映射，而不是一整条字符串。这使得会话中途的改动可以作为一小片补丁追加到记录里，而更早的每一条消息都逐字节保持发送时的样子。

Every request Pi sends starts with a system prompt, and a coding agent's prompt changes during a session: a skill is installed, a tool is switched of, an extension adds instructions. This section shows the nine kinds of section and their order, and where each input is read from. Then it shows how a change becomes a SystemMessage patch in the transcript instead of a rewrite of the prompt. Pi's own default is short: one sentence of preamble, the tool list, a handful of rules and pointers to its docs CA/src/core/system-prompt.ts:128.

Pi 发出的每个请求都以系统提示词开头，而编码智能体的提示词在会话期间会变化：装上一个技能、关掉一个工具、扩展追加指令。本节展示九种小节的类型及其顺序，以及每项输入从哪里读入；随后展示一次改动如何变成记录里的一片 SystemMessage 补丁，而不是重写整条提示词。Pi 自己的默认提示词很短：一句前言、工具列表、若干条规则，以及指向它自己文档的指针 CA/src/core/system-prompt.ts:128。

## Sections, in order

## 小节及其顺序

buildSystemPromptSections() returns a Record<string, string> whose key order is the prompt's order CA/src/core/system-prompt.ts:128. The preamble is untagged text. Every other section is wrapped as <name>\n…\n</name> CA/src/core/system-prompt.ts:190, so that a later update can name the section it replaces.

buildSystemPromptSections() 返回一个 Record<string, string>，其键顺序就是提示词的顺序 CA/src/core/system-prompt.ts:128。preamble 是不带标签的纯文本。其他每个小节都包成 <name>\n…\n</name> CA/src/core/system-prompt.ts:190，这样后续更新就能指明自己要替换的是哪个小节。

![](images/992da82f888f281ce563109e502519ec336bedc20396c4a2003bee88c5590b34.jpg)

A custom prompt replaces four sections, not one. When SYSTEM.md or --system-prompt supplies the preamble, tools, rules and docs are not built at all CA/src/core/system-prompt.ts:152. Hatched boxes are the ones a custom prompt drops; empty sections are omitted. Schematic; from buildSystemPromptSections().

自定义提示词替换的是四个小节，而不是一个。当 SYSTEM.md 或 --system-prompt 提供时，preamble、tools、rules 和 docs 根本不会被构造 CA/src/core/system-prompt.ts:152。画斜线的方框是自定义提示词会丢掉的那些；空的小节会被省略。示意图；取自 buildSystemPromptSections()。

preamble: the default text is one sentence: "You are an expert coding assistant operating inside pi, a coding agent harness. You help users by reading files, executing commands, editing code, and writing new files." CA/src/core/system-prompt.ts:156. A custom prompt replaces it verbatim.

preamble：默认文本是一句话："You are an expert coding assistant operating inside pi, a coding agent harness. You help users by reading files, executing commands, editing code, and writing new files." CA/src/core/system-prompt.ts:156。自定义提示词会逐字替换它。

tools: one line - \${name}: \${snippet} per declared tool that has a prompt Snippet, then "In addition to the tools above, you may have access to other custom tools depending on the project." Tools without a snippet are not listed, and with none left the list reads (none) CA/src/core/system-prompt.ts:157. Tools hidden by a prepare Loadout hook are left out, because the request does not declare them CA/src/core/system-prompt.ts:150.

tools：每个带 promptSnippet 的已声明工具一行 —— \${name}: \${snippet}，然后接 "In addition to the tools above, you may have access to other custom tools depending on the project."。没有 snippet 的工具不会被列出；如果一个都没有，列表就显示为 (none) CA/src/core/system-prompt.ts:157。被 prepareLoadout 钩子隐藏的工具会被略去，因为请求里并未声明它们 CA/src/core/system-prompt.ts:150。

rules: de-duplicated bullets from build Rules() CA/src/core/system-prompt.ts:88. First "Use bash for file operations like ls, rg, then extra prompt Guidelines, then always "Be concise in your responses" and "Show file paths clearly when working with files".

rules：来自 buildRules() 的去重要点列表 CA/src/core/system-prompt.ts:88。先是 "Use bash for file operations like ls, rg"，然后是额外的 promptGuidelines，再然后固定有 "Be concise in your responses" 和 "Show file paths clearly when working with files"。

docs: absolute paths to Pi's README, docs/ and examples/, with the instruction to read them only "when the user asks about pi itself" CA/src/core/system-prompt.ts:162.

docs：Pi 的 README、docs/ 和 examples/ 的绝对路径，并附带只在 "when the user asks about pi itself" 时才读它们的指令 CA/src/core/system-prompt.ts:162。

addendum: the append-prompt text, joined with blank lines when there are several CA/src/core/agent-session.ts:1697.

addendum：追加提示词的文本，有多段时用空行连接 CA/src/core/agent-session.ts:1697。

project_context: "Project-specific instructions and guidelines:" followed by one <project_instructions path="…">… </project_instructions> block per context file CA/src/core/system-prompt.ts:79. Which files load is covered in context files, skills, templates, themes and packages (p. 106).

project_context："Project-specific instructions and guidelines:"，随后每个上下文文件一个 <project_instructions path="…">… </project_instructions> 块 CA/src/core/system-prompt.ts:79。哪些文件会被加载见 context files, skills, templates, themes and packages (p. 106)。

skills: the <available_skills> index, one <skill> with name, description and location per skill that allows model invocation CA/src/core/skills.ts:358. Added only if read or bash is selected; if both are hidden the hint names no tool CA/src/core/system-prompt.ts:175.

skills：`<available_skills>` 索引，每个允许模型调用的技能一个 `<skill>`，含 name、description 和 location CA/src/core/skills.ts:358。只有在 read 或 bash 之一被选中时才加入；若两者都被隐藏，这条提示不含任何工具名 CA/src/core/system-prompt.ts:175。

cwd: the working directory, with backslashes turned into / CA/src/core/system-prompt.ts:183.

cwd：工作目录，其中反斜杠被换成 / CA/src/core/system-prompt.ts:183。

custom sections: extension sections from systemPromptOptions.sections. A name must match ^[a-z][a-z0-9_-]*\$ and must not be preamble, or the build throws "Invalid system prompt section name" CA/src/core/system-prompt.ts:58.

custom sections：来自 systemPromptOptions.sections 的扩展小节。名字必须匹配 ^[a-z][a-z0-9_-]*\$ 且不能是 preamble，否则构造过程会抛出 "Invalid system prompt section name" CA/src/core/system-prompt.ts:58。

The working directory is the only fact about the environment in the prompt. No date, time, operating system or shell is injected anywhere in system-prompt.ts. An extension that wants them adds a section in before_agent_start (extension events and contexts (p. 120)).

工作目录是提示词里唯一涉及环境的fact。system-prompt.ts 里任何地方都没有注入日期、时间、操作系统或 shell。想要这些的扩展可以在 before_agent_start 中加一个小节（extension events and contexts (p. 120)）。

## A stored prompt, from the capture kit

## 捕获工具包抓到的已存储提示词

The prompt is not kept as text. It is stored as the sections of a system message, the fourth line of the one-turn session file (the life of one prompt (p. 15)). The capture ran with the four default tools, no context files, no skills and no append prompt, so it has five sections:

提示词不是以文本形式保存的。它被存为一条系统消息的小节，也就是单轮会话文件的第四行（the life of one prompt (p. 15)）。这次捕获以四个默认工具、无上下文文件、无技能、无追加提示词运行，因此它有五个小节：

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

已裁剪：十条规则中的四条、docs 的正文，以及四条 toolsAdded 声明中的三条（bash、edit、write）。content 为空是因为结构化小节承载了提示词 CA/src/core/system-prompt.ts:199。路径被捕获脚本抹去。

Three things in the record matter later. content is "". The tool declarations travel in the same message as tools Added, so prompt and tool set are replayed together. And the record is an ordinary message entry in the session tree; there is no separate "prompt state" entry type (sessions, the JSONL tree (p. 86)).

这条记录里有三件事对后文很重要。content 是 ""。工具声明与 toolsAdded 同处一条消息，因此提示词和工具集是一起重放的。而且这条记录就是会话树里一条普通的 message 条目；并不存在单独的 "prompt state" 条目类型（sessions, the JSONL tree (p. 86)）。

## Where the inputs come from

## 输入来自哪里

AgentSession._rebuildSystemPrompt() collects the base options from the resource loader and the tool registry CA/src/core/agent-session.ts:1686.

AgentSession._rebuildSystemPrompt() 从资源加载器和工具注册表收集基础选项 CA/src/core/agent-session.ts:1686。

<table><tr><td>输入</td><td>来源</td><td>参见</td></tr><tr><td>custom Prompt</td><td>--system-prompt；否则若项目受信任则用 /.pi/SYSTEM.md；否则 ~/.pi/agent/SYSTEM.md CA/src/core/resource-loader.ts:1209</td><td>configuration, models and auth (p. 99)</td></tr><tr><td>appendSystemPrompt</td><td>每一个 --append-system-prompt（可重复）；否则若受信任则用 .pi/APPEND_SYSTEM.md；否则 ~/.pi/agent/APPEND_SYSTEM.md CA/src/core/resource-loader.ts:1223</td><td>CLI reference (p. 191)</td></tr><tr><td>context 文件</td><td>loadProjectContextFiles()：先 agent 目录，再从文件系统根到 cwd 之间的每一级祖先目录 CA/src/core/resource-loader.ts:232</td><td>context files, skills, templates, themes and packages (p. 106)</td></tr><tr><td>skills</td><td>资源加载器的 skills</td><td>context files, skills, templates, themes and packages (p. 106)</td></tr><tr><td>tool Snippets、tool Guidelines</td><td>每个已注册工具定义的 promptSnippet 与 promptGuidelines</td><td>built-in tools (p. 81)</td></tr><tr><td>forceSystemPrompt</td><td>一个返回 systemPrompt 的 before_agent_start 处理器</td><td>extension events and contexts (p. 120)</td></tr></table>

Two files of the same name are never combined. The trusted project file wins over the agent-directory file, for both SYSTEM.md and APPEND_SYSTEM.md. From resource-loader.ts (discoverSystemPromptFile, discoverAppendSystemPromptFile).

同名的两个文件永远不会被合并。对 SYSTEM.md 和 APPEND_SYSTEM.md 而言，受信任的项目文件都优先于 agent 目录下的文件。取自 resource-loader.ts（discoverSystemPromptFile、discoverAppendSystemPromptFile）。

A CLI value that names an existing file is read as that file's content, with any BOM stripped; anything else is used as literal text CA/src/core/resource-loader.ts:167.

命令行值若指向一个已存在的文件，就被读作该文件的内容并剥掉 BOM；其他任何值都当作字面文本使用 CA/src/core/resource-loader.ts:167。

docs/cli.md says --append-system-prompt "Appends text or an existing file to the system prompt", and docs/configuration.md says APPEND_SYSTEM.md "Adds instructions". Read together they suggest both apply. They do not: when any --append-systemprompt is given, discovery of APPEND_SYSTEM.md is skipped CA/src/core/resource-loader.ts:659. Pass the file as one of the flags if you want both.

docs/cli.md 说 --append-system-prompt "Appends text or an existing file to the system prompt"，而 docs/configuration.md 说 APPEND_SYSTEM.md "Adds instructions"。合起来读会以为两者都生效。并非如此：只要给了任意一个 --append-systemprompt，就会跳过对 APPEND_SYSTEM.md 的发现 CA/src/core/resource-loader.ts:659。若想两者都用，就把该文件作为其中一个标志传入。

## Prompt changes are transcript patches

## 提示词变更就是记录补丁

_preparePromptAndToolLoadout() runs at the start of every prompt() and before every later turn, through prepareNextTurnWithContext CA/src/core/agent-session.ts:1724 CA/src/core/agent-session.ts:892. It never re-sends the whole prompt. It replays the transcript's system messages into the sections the model has now, difs them against freshly built sections, and appends the diference.

_preparePromptAndToolLoadout() 在每次 prompt() 开头、以及之后每个轮次之前通过 prepareNextTurnWithContext 运行 CA/src/core/agent-session.ts:1724 CA/src/core/agent-session.ts:892。它从不重发整条提示词。它把记录里的系统消息重放成模型当前拥有的小节，与新构造出的小节做 diff，再把差异追加上去。

![](images/504cda31a9751c67d650dd7ffd41cc4364a4700dfd9816d3971479011f9472c5.jpg)

Earlier messages are never rewritten. A changed section is sent as text, a removed one as null; tool changes ride on the same system message. The provider sends a later system message in place, framed as Updated system prompt section "name", only if the model accepts mid-conversation system messages. From agent-session.ts (_preparePromptAndToolLoadout), system-prompt.ts:217, agent-loop.ts:333, ai/utils/transcript.ts:115.

更早的消息从不被改写。变更的小节以文本发送，被移除的小节以 null 发送；工具变更搭同一条系统消息。只有当模型接受会话中途的系统消息时，供应商才会就地发送后面那条系统消息，并把它表述为 Updated system prompt section "name"。取自 agent-session.ts（_preparePromptAndToolLoadout）、system-prompt.ts:217、agent-loop.ts:333、ai/utils/transcript.ts:115。

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

完整函数，第 217–229 行。

Replay is defined once, in getCurrentSystemMessage(): walk every system message in order, concatenate non-empty content, set or delete sections by name, and resolve tools by applying each tools Removed then tools Added ai/utils/transcript.ts:73. Providers receive the patched transcript. renderSystemMessageUpdate() frames each patched section as Updated system prompt section "name": or Removed system prompt section "name".ai/utils/text.ts:28. When the model's compat flag supportsMidConvoSystemMessages is false, which is the default, collapseSystemMessages() folds every system message into one leading message instead

重放只定义一次，在 getCurrentSystemMessage() 里：按顺序遍历每条系统消息，拼接非空 content，按名字设置或删除小节，并依次应用每个 toolsRemoved 再应用 toolsAdded 来解析工具 ai/utils/transcript.ts:73。供应商收到的是打过补丁的记录。renderSystemMessageUpdate() 把每个被补的小节表述为 Updated system prompt section "name": 或 Removed system prompt section "name". ai/utils/text.ts:28。当模型的兼容标志 supportsMidConvoSystemMessages 为 false 时（这是默认情形），collapseSystemMessages() 改为把所有系统消息折叠成开头的一条消息。

ai/utils/transcript.ts:108.

That last case decides what the design buys. On a model that accepts mid-conversation system messages, installing a skill or connecting an MCP server appends a patch, and the provider's cached prefix stays valid. On a model that does not, the collapsed head changes and the cached prefix is lost from that request on. Which models carry the flag is in wire APIs and cross provider hand-of (p. 36).

最后这一种情形决定了这个设计能换来什么。在接受会话中途系统消息的模型上，装一个技能或连一个 MCP 服务器只是追加一片补丁，供应商的缓存前缀仍然有效。在不接受这种消息的模型上，折叠后的开头变了，从那次请求起缓存前缀就作废了。哪些模型带这个标志见 wire APIs and cross-provider hand-off (p. 36)。

## F O O T G U N

## 危险做法

A before_agent_start handler that returns system Prompt (or sets forceSystemPrompt) does not change the transcript. The structured sections are still difed and stored; the forced text is projected onto the request only, as one head message with the current tools CA/src/core/agent-session.ts:1773. The projection lasts for that run. A later run, and anything that reads the session file, sees the structured prompt. Prefer editing sections, tools or guidelines in systemPromptOptions, which docs/extensions.md also recommends.

返回 systemPrompt（或设置 forceSystemPrompt）的 before_agent_start 处理器并不会改变记录。结构化小节照样被 diff 并存储；被强制的文本只投影到请求上，作为一条带头部的消息，配上当前工具集 CA/src/core/agent-session.ts:1773。这个投影只持续那一次运行。之后的运行，以及任何读取会话文件的东西，看到的都是结构化提示词。更推荐在 systemPromptOptions 里修改小节、工具或指南，docs/extensions.md 也这么建议。

W H A T T H I S M E A N S F O R Y O U

## 这对你意味着什么

Read a session's prompt by replaying its system messages, not by reading the first one.

要读某个会话的提示词，请重放它的系统消息，而不是去读第一条。

Add instructions from an extension as a named section; a rename shows up as a removal plus an addition.

从扩展添加指令时用一个具名小节；改名会表现为一次移除加一次新增。

Put dates or environment facts in a section of their own; the default prompt carries only cwd.

把日期或环境信息放进各自独立的小节；默认提示词只带 cwd。

Check supportsMidConvoSystemMessages before counting on cache hits after a prompt change.

在指望提示词变更后仍能命中缓存之前，先检查 supportsMidConvoSystemMessages。

Sources: CA/src/core/system-prompt.ts (normalizeBuildSystemPromptOptions, build Rules, buildSystemPromptSections, buildSystemPromptState, diffSystemPromptSections); CA/src/core/skills.ts (formatSkillsForPrompt); CA/src/core/agentsession.ts (_rebuildSystemPrompt, _preparePromptAndToolLoadout, _installAgentForcedPromptProjection, _installAgentNextTurnRefresh); CA/src/core/resource-loader.ts (resolvePromptInput, loadProjectContextFiles, discoverSystemPromptFile, discoverAppendSystemPromptFile); agent/agent-loop.ts (declareToolChanges); ai/types.ts (SystemMessage); ai/utils/transcript.ts (getCurrentSystemMessage, collapseSystemMessages, resolve Transcript); ai/utils/text.ts (renderSystemMessageUpdate); CA/docs/cli.md; CA/docs/configuration.md; CA/docs/extensions.md; research/out/one-turn.txt (§session-jsonl)

来源：CA/src/core/system-prompt.ts（normalizeBuildSystemPromptOptions、buildRules、buildSystemPromptSections、buildSystemPromptState、diffSystemPromptSections）；CA/src/core/skills.ts（formatSkillsForPrompt）；CA/src/core/agentsession.ts（_rebuildSystemPrompt、_preparePromptAndToolLoadout、_installAgentForcedPromptProjection、_installAgentNextTurnRefresh）；CA/src/core/resource-loader.ts（resolvePromptInput、loadProjectContextFiles、discoverSystemPromptFile、discoverAppendSystemPromptFile）；agent/agent-loop.ts（declareToolChanges）；ai/types.ts（SystemMessage）；ai/utils/transcript.ts（getCurrentSystemMessage、collapseSystemMessages、resolveTranscript）；ai/utils/text.ts（renderSystemMessageUpdate）；CA/docs/cli.md；CA/docs/configuration.md；CA/docs/extensions.md；research/out/one-turn.txt（§session-jsonl）

## 4.2 Built-in tools

## 4.2 内置工具

Pi ships eight tools and enables four. All of them obey one output contract,

Pi 内置八个工具，默认启用四个。它们全都遵守同一个输出契约：

2,000 lines or 50 KB, so a single tool result can never fill the context window,

2,000 行或 50 KB，因此单个工具结果永远填不满上下文窗口，

and the edit tool refuses any change it cannot place exactly once.

而 edit 工具会拒绝任何它无法精确定位一次的改动。

The built-in tools are the only way the default agent touches the machine. This section lists the eight tools and how they are selected, then states the truncation contract they share and each tool's parameters and behaviour. It walks the edit algorithm with real error messages from the capture kit. It ends with the hook pipeline that wraps every call, including calls one tool makes on behalf of another.

内置工具是默认智能体触碰这台机器的唯一途径。本节先列出这八个工具及其选择方式，再说明它们共用的截断契约，以及每个工具的参数与行为；然后用捕获工具包里的真实错误消息走一遍 edit 算法；最后给出包裹每一次调用的钩子流水线，包括一个工具代另一个工具发起的调用。

## Eight tools, four on by default

## 八个工具，默认开四个

ToolName is "read" | "bash" | "powershell" | "edit" | "write" | "grep" | "find" | "ls" CA/src/core/tools/index.ts:95. DEFAULT_TOOL_NAMES is ["read", "bash", "edit", "write"] CA/src/core/settingsmanager.ts:215. createReadOnlyTools() returns read, grep, find and ls CA/src/core/tools/index.ts:204.

ToolName 是 "read" | "bash" | "powershell" | "edit" | "write" | "grep" | "find" | "ls" CA/src/core/tools/index.ts:95。DEFAULT_TOOL_NAMES 是 ["read", "bash", "edit", "write"] CA/src/core/settingsmanager.ts:215。createReadOnlyTools() 返回 read、grep、find 和 ls CA/src/core/tools/index.ts:204。

Selection happens in three layers. The default Tools setting either replaces the default list with plain names or edits it with +name and -name modifiers, applied in list order CA/src/core/settings-manager.ts:236. On the command line, --tools is an allowlist and --exclude-tools a denylist; both accept * patterns, and --no-tools and --no-builtin-tools switch whole groups of CA/src/cli/args.ts:151. The full flag list is in CLI reference (p. 191).

选择分三层发生。默认的 tools 设置要么用纯名字替换默认列表，要么用 +name 和 -name 修饰符编辑它，按列表顺序生效 CA/src/core/settings-manager.ts:236。在命令行上，--tools 是允许列表，--exclude-tools 是拒绝列表；两者都接受 * 通配模式，而 --no-tools 和 --no-builtin-tools 关闭整组工具 CA/src/cli/args.ts:151。完整标志列表见 CLI reference (p. 191)。

Each tool is a ToolDefinition turned into an AgentTool by wrapToolDefinition(), which copies name, schema, prepare Arguments and constrained Sampling and passes a per-call context to execute CA/src/core/tools/tooldefinition-wrapper.ts:8. Paths resolve against the session's cwd, with \~ expanded and a leading @ stripped CA/src/core/tools/path-utils.ts:48.

每个工具都是 ToolDefinition，由 wrapToolDefinition() 变成 AgentTool：它复制 name、schema、prepareArguments 和 constrainedSampling，并把每次调用的 context 传给 execute CA/src/core/tools/tooldefinition-wrapper.ts:8。路径按会话的 cwd 解析，其中 \~ 会被展开，开头的 @ 会被剥掉 CA/src/core/tools/path-utils.ts:48。

## The truncation contract

## 截断契约

Every tool that returns file or process output passes it through truncate.ts. Two limits apply, and whichever is hit first wins:

每个返回文件或进程输出的工具都让它经过 truncate.ts。这里有两条限制，先碰到哪条算哪条：

```typescript the three limits every built-in tool shares CA/src/core/tools/truncate.ts export const DEFAULT_MAX_LINES = 2000;
export const DEFAULT_MAX_BYTES = 50 * 1024; // 50KB
export const GREP_MAX_LINE_LENGTH = 500; // Max chars per grep match line
```

T S

## TS

Lines 11–13, verbatim.

第 11–13 行，逐字原文。

<table><tr><td>函数</td><td>保留</td><td>使用者</td></tr><tr><td>truncateHead</td><td>开头部分；从不切分某一行；若仅第 1 行就超出字节限制，则什么都不返回并置 firstLineExceedsLimit</td><td>read、grep、find、ls</td></tr><tr><td>truncateTail</td><td>结尾部分；若仅最后一行超出字节限制，则保留它的尾部并置 lastLinePartial</td><td>bash、powershell（通过 OutputAccumulator）、用户 ! 命令</td></tr><tr><td>truncateLine(line, 500)</td><td>前 500 个字符，然后是 ... [truncated]</td><td>grep 匹配行</td></tr><tr><td>truncateMiddle(text, maxBytes)</td><td>从两端各取一半预算，中间以 ...N chars truncated... 相连</td><td>MCP 工具结果，上限 20 KiBCA/src/extensions/mcp/tools.ts:51</td></tr></table>

Head for files, tail for processes. A file is read from the top; a failing command prints its error last. From truncate.ts and the call sites of each function in CA/src.

文件取头部，进程取尾部。文件从开头读起；失败的命令把错误打在最后。取自 truncate.ts 以及 CA/src 中各函数的调用点。

Truncation is never silent. Each tool appends a notice that tells the model how to get the rest. The capture kit read a 2,500-line file with the real read tool:

截断从不是静默的。每个工具都会附上一条提示，告诉模型怎么拿到剩余部分。捕获工具包用真实的 read 工具读了一个 2,500 行的文件：

```txt read long.txt (2,500 lines) → ...line 1999\nline 2000\n\n[Showing lines 1-2000 of 2500. Use offset=2001 to continue.]
read offset=10 limit=3 → line 10\nline 11\nline 12\n\n[2488 more lines in file. Use offset=13 to continue.]
read offset=9999 × Offset 9999 is beyond end of file (2500 lines total)
```

## Tool reference

## 工具参考

<table><tr><td>工具</td><td>参数</td><td>行为</td></tr><tr><td>read</td><td>path, offset?（从 1 开始）, limit?</td><td>先应用 limit，再 truncateHead。若首行超过 50 KB，则不返回文本，而给出一条 sed -n &#x27;...p&#x27; ... | head -c 51200 的提示。图片（jpg、png、gif、webp、bmp，按文件内容识别）以图像块返回，并缩放到模型的输入上限；若模型不支持图像输入，会附一条说明。还会尝试 macOS 的文件名变体：AM/PM 前的窄不换行空格、NFD、弯引号 CA/src/core/tools/path-utils.ts:86。</td></tr><tr><td>bash</td><td>command, timeout?（秒，无默认值，最多 2,147,483.647）</td><td>以分离的独立进程组启动配置好的 shell，stdout 与 stderr 合并。中止或超时会杀掉整个进程树。保留尾部；完整输出写入临时文件 pi-bash-*.log，文件名写在提示里。更新节流为每 100 ms 一次。非零退出返回 isError，并带上 "Command exited with code N"。</td></tr><tr><td>powershell</td><td>同 bash</td><td>同一份定义，改用 PowerShell 的配置、UTF-8 控制台前缀和临时前缀 pi-powershell CA/src/core/tools/powershell.ts:16。</td></tr><tr><td>edit</td><td>path, edits: [{oldText,newText}]</td><td>一次调用做多处互不相交的替换（算法见下文）。prepareArguments 还接受以 JSON 字符串或单个对象传入的 edits，以及旧式的顶层 oldText/newText CA/src/core/tools/edit.ts:103。</td></tr><tr><td>write</td><td>path, content</td><td>创建父目录，以 UTF-8 写入，在按文件的变更队列内执行。返回 "Successfully wrote to path"。</td></tr><tr><td>grep</td><td>pattern, path?, glob?, ignoreCase?, literal?, context?, limit? = 100</td><td>运行 rg --json --line-number --color=never --hidden，若本机没有 ripgrep 则先下载。遵循 .gitignore。行内容在 500 个字符处截断；输出上限 50 KB。</td></tr><tr><td>find</td><td>pattern(glob), path?, limit? = 1000</td><td>运行 fd --glob --color=never --hidden --max-results N；返回相对于搜索目录的路径，使用 / 作分隔符。</td></tr><tr><td>ls</td><td>path?, limit? = 500</td><td>读取目录，按不区分大小写排序，目录后追加 /，包含点文件。</td></tr></table>

Only four tools ask for strict schema decoding. read, bash (and so powershell), edit and write set constrained Sampling: {type: "json_schema", strict: "prefer"}; grep, find and ls do not. From CA/src/core/tools/*.ts.

只有四个工具要求严格的 schema 解码。read、bash（因此还有 powershell）、edit 和 write 设置 constrainedSampling: {type: "json_schema", strict: "prefer"}；grep、find 和 ls 不设置。取自 CA/src/core/tools/*.ts。

bash has two outputs. The model sees the truncated tail. Programmatic callers such as codemode scripts (codemode (p. 151)) get structured Content — {output, truncated, full_output_path?, exit_code, wall_time_seconds} — whose output is capped at 1 MiB instead CA/src/core/tools/bash.ts:24. Unless exposeSessionEnvironment is false, the child process's environment carries PI_SESSION_ID, PI_SESSION_FILE, PI_PROVIDER, PI_MODEL and PI_REASONING_LEVEL, and the inherited values of those five are removed first CA/src/core/tools/bash.ts:186.

bash 有两种输出。模型看到的是截断后的尾部。程序化调用方（比如 codemode 脚本，codemode (p. 151)）拿到的是结构化的 content —— {output, truncated, full_output_path?, exit_code, wall_time_seconds} —— 其中的 output 上限是 1 MiB CA/src/core/tools/bash.ts:24。除非 exposeSessionEnvironment 为 false，子进程环境会带上 PI_SESSION_ID、PI_SESSION_FILE、PI_PROVIDER、PI_MODEL 和 PI_REASONING_LEVEL，并且会先移除这五个变量的继承值 CA/src/core/tools/bash.ts:186。

## The edit algorithm

## edit 算法

edit makes all its replacements against the original file, never against the result of an earlier replacement in the same call. It runs inside withFileMutationQueue(), keyed by the file's real path: two edits to one file run one after the other, edits to diferent files run in parallel CA/src/core/tools/file-mutation-queue.ts:32.

edit 的所有替换都针对原始文件进行，绝不针对同一次调用中较早替换的结果。它在 withFileMutationQueue() 内运行，以文件的真实路径为键：对同一个文件的两次编辑一前一后执行，对不同文件的编辑并行执行 CA/src/core/tools/file-mutation-queue.ts:32。

![](images/f54e0b62d263e24e02c1d2f7f92399a51c61426e6cbb7cea102352594e671def.jpg)

Five ways to refuse, one way to write. The first failing check wins and the file is not touched. From edit.ts (execute) and edit-dif.ts (applyEditsToNormalizedContent, normalizeForFuzzyMatch, applyReplacementsPreservingUnchangedLines). Schematic.

五种拒绝方式，一种写入方式。第一项失败的检查胜出，文件不会被碰到。取自 edit.ts（execute）和 edit-diff.ts（applyEditsToNormalizedContent、normalizeForFuzzyMatch、applyReplacementsPreservingUnchangedLines）。示意图。

The capture kit ran the real tool against a file with a BOM, CRLF line endings and a duplicated line, then against a file with curly quotes and trailing spaces:

捕获工具包用真实工具处理了一个带 BOM、CRLF 行尾且有一行重复的文件，然后又处理了一个带弯引号和行尾空格的文件：

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

The last pair shows the fuzzy path's limit. The model wrote ASCII quotes, so matching fell back to normalised text. The touched line came back normalised: its trailing spaces are gone. The untouched line kept its curly quotes. In a multi-edit call, one fuzzy edit switches every edit to normalised matching, and every line any edit touches is written in normalised form.

最后一对展示了模糊匹配路径的极限。模型写的是 ASCII 引号，因此匹配退回到归一化文本。被改动的行回来时是归一化的：它的行尾空格没了。没被改动的行保留了它的弯引号。在一次多编辑调用中，只要有一个编辑是模糊的，所有编辑就都切换到归一化匹配，并且任何编辑碰到的每一行都以归一化形式写入。

The overlap message names edits by sorted position, so edits[1] and edits[0] is not a typo. More important: uniqueness is counted in fuzzy space even when the exact match succeeded CA/src/core/tools/edit-diff.ts:328. Two lines that difer only in quote style or trailing whitespace count as two occurrences, and the edit is refused. Add a neighbouring line to old Text.

重叠提示按排序后的位置来称呼各编辑，所以 edits[1] and edits[0] 不是笔误。更重要的是：即便精确匹配已经成功，唯一性仍是在模糊空间里计数的 CA/src/core/tools/edit-diff.ts:328。仅在引号风格或行尾空白上有差异的两行会被算作两处出现，编辑因此被拒绝。给 oldText 加上相邻的一行。

## The hook layer around every call

## 包裹每次调用的钩子层

Every tool call, built-in or not, passes through the same pipeline in agent-loop.ts agent/agent-loop.ts:707. AgentSession installs the two hooks that connect it to extensions CA/src/core/agent-session.ts:640.

每一次工具调用，无论内置与否，都经过 agent-loop.ts 中同一条流水线 agent/agent-loop.ts:707。AgentSession 装上把它与扩展连接起来的两个钩子 CA/src/core/agent-session.ts:640。

![](images/f18254134a5a7f37a60b0e06b209332517f7c4a2662e0491af405599462e7081.jpg)

Extensions see validated arguments and can change them. tool_call handlers receive the same object that execute gets, so mutating event.input changes the call; a block result becomes an error result with the handler's reason. tool_result handlers can replace content, details and isError, and images are resized after them. From agent-loop.ts (prepareToolCall, finalizeExecutedToolCall) and agent-session.ts (_beforeToolCall, _afterToolCall).

扩展看到的是校验过的参数，并且可以改它们。tool_call 处理器拿到的对象和 execute 拿到的是同一个，因此修改 event.input 就会改变这次调用；block 结果会变成错误结果，并带上处理器给出的理由。tool_result 处理器可以替换 content、details 和 isError，图片则在其之后被缩放。取自 agent-loop.ts（prepareToolCall、finalizeExecutedToolCall）和 agent-session.ts（_beforeToolCall、_afterToolCall）。

An unknown tool name, a validation failure, a block and a thrown error all come back as a tool result with isError: true; none of them throws out of the loop agent/agent-loop.ts:807. The event names and result shapes are in extension events and contexts (p. 120).

未知的工具名、校验失败、block 以及抛出的错误，全都以 isError: true 的工具结果返回；它们都不会从循环里抛出去 agent/agent-loop.ts:807。事件名和结果结构见 extension events and contexts (p. 120)。

The same pipeline runs for nested calls: a tool that calls ctx.execute Tool(), as codemode scripts do. A nested call's id is <parent id>/<n>, counting from 1, and its tool_execution_* events and hook events carry parentToolCallId

同一条流水线也用于嵌套调用：工具调用 ctx.executeTool()，正如 codemode 脚本所做的那样。嵌套调用的 id 是 <parent id>/<n>，从 1 开始计数；它的 tool_execution_* 事件和钩子事件都带上 parentToolCallId。

CA/src/core/nested-tool-calls.ts:188. The parent's tool result records the nested calls within NESTED_CALL_LIMITS: at most 256 calls, 8 KiB of arguments per call, 32 KiB of arguments in total, and 500 characters per error. Arguments over a limit are omitted, calls beyond 256 are dropped, and the record is marked incomplete CA/src/core/nested-tool-calls.ts:26.

CA/src/core/nested-tool-calls.ts:188。父级工具结果在 NESTED_CALL_LIMITS 之内记录这些嵌套调用：最多 256 次调用，每次调用的参数 8 KiB，参数总计 32 KiB，每个错误 500 个字符。超限的参数会被略去，超过 256 次的调用会被丢弃，该记录被标记为不完整 CA/src/core/nested-tool-calls.ts:26。

W H A T T H I S M E A N S F O R Y O U

## 这对你意味着什么

Tell the model to page with offset; the notice already does, so do not raise the limits to avoid it.

告诉模型用 offset 翻页；提示里已经这么说了，所以不要为了躲开它而抬高限制。

Read structured Content.output from scripts that need more than the last 2,000 lines of a command.

需要命令最后 2,000 行以外的输出时，从脚本里读结构化的 content.output。

Expect edit to refuse ambiguous text; widen old Text rather than retrying the same call.

要预期 edit 会拒绝有歧义的文本；扩大 oldText，而不是用同样的调用重试。

Put permission checks in tool_call: they then apply to nested calls too.

把权限检查放在 tool_call 里：这样它们对嵌套调用同样生效。

Sources: CA/src/core/tools/index.ts (ToolName, createReadOnlyTools); CA/src/core/settings-manager.ts (DEFAULT_TOOL_NAMES, resolveDefaultTools); CA/src/cli/args.ts (-tools, -exclude-tools); CA/src/core/tools/tool-definition-wrapper.ts; CA/src/core/tools/path-utils.ts; CA/src/core/tools/truncate.ts; CA/src/core/tools/{read,bash,powershell,edit,editdiff,write,grep,find,ls,file-mutation-queue}.ts; CA/src/core/tools/renderers/bash.ts (BASH_UPDATE_THROTTLE_MS); CA/src/extensions/mcp/tools.ts (MCP_OUTPUT_MAX_BYTES); agent/agent-loop.ts (prepareToolCall, runToolCall, finalizeExecutedToolCall); CA/src/core/agent-session.ts (_beforeToolCall, _afterToolCall, _executeNestedToolCall); CA/src/core/nested-tool-calls.ts (NESTED_CALL_LIMITS); research/capture/built-in-tools-edit.mjs; research/out/built-intools-edit.txt

来源：CA/src/core/tools/index.ts（ToolName、createReadOnlyTools）；CA/src/core/settings-manager.ts（DEFAULT_TOOL_NAMES、resolveDefaultTools）；CA/src/cli/args.ts（-tools、-exclude-tools）；CA/src/core/tools/tool-definition-wrapper.ts；CA/src/core/tools/path-utils.ts；CA/src/core/tools/truncate.ts；CA/src/core/tools/{read,bash,powershell,edit,editdiff,write,grep,find,ls,file-mutation-queue}.ts；CA/src/core/tools/renderers/bash.ts（BASH_UPDATE_THROTTLE_MS）；CA/src/extensions/mcp/tools.ts（MCP_OUTPUT_MAX_BYTES）；agent/agent-loop.ts（prepareToolCall、runToolCall、finalizeExecutedToolCall）；CA/src/core/agent-session.ts（_beforeToolCall、_afterToolCall、_executeNestedToolCall）；CA/src/core/nested-tool-calls.ts（NESTED_CALL_LIMITS）；research/capture/built-in-tools-edit.mjs；research/out/built-intools-edit.txt

#### 4.3 Sessions: the JSONLtree

#### 4.3 会话：JSONL树

A session file is append-only and every entry names its parent, so one file holds a whole tree ofconversations. Which branch is current lives only in memory, and a restart picks the last line written.

会话文件是仅追加的，每条条目都指明自己的父条目，因此一个文件就装着一整棵会话树。当前处于哪个分支只存在于内存中，重启时则取最后写入的那一行。

Everything an agent did in a session is recoverable from one JSONL file: the prompt it was given, each model response, each tool result, and every branch the user tried. This section shows where the file lives and how it is named, then the header and the eleven entry types. It follows the tree that parentId builds and the leaf pointer that walks it. It ends with loading and migration, and with how the entries on one path become the messages sent to the model. The code is SessionManager, 2,013 lines in one file CA/src/core/session-manager.ts:987.

智能体在一个会话里做过的一切，都能从一个 JSONL 文件中恢复：它得到的提示词、每次模型响应、每个工具结果，以及用户尝试过的每个分支。本节先说明文件放在哪里、如何命名，然后介绍文件头和十一种条目类型；接着沿着 parentId 构建的树和遍历它的叶指针往下走；最后讲加载与迁移，以及一条路径上的条目如何变成发给模型的消息。相关代码是 SessionManager，单文件 2,013 行 CA/src/core/session-manager.ts:987。

## Location, naming, identity

## 位置、命名与标识

Directory: ~/.pi/agent/sessions/--<cwd>--/. The cwd has its leading / or \ removed and every /, \ and : replaced by - CA/src/core/session-manager.ts:592. /Users/me/proj becomes --Users-me-proj--.

目录：`~/.pi/agent/sessions/--<cwd>--/`。cwd 开头的 / 或 \ 被去掉，其中每个 /、\ 和 : 都换成 - CA/src/core/session-manager.ts:592。/Users/me/proj 变成 --Users-me-proj--。

Directory precedence: --session-dir, then \$PI_CODING_AGENT_SESSION_DIR, then the session Dir setting, then the percwd default CA/src/main.ts:688.

目录优先级：--session-dir，然后 \$PI_CODING_AGENT_SESSION_DIR，然后 sessionDir 设置，最后是按 cwd 的默认值 CA/src/main.ts:688。

File name: <ISO timestamp with : and . replaced by ->_<session id>.jsonl CA/src/core/sessionmanager.ts:1079. The capture kit's file is 2026-10-05T23-16-41-747Z_01a10e5a-ea92-7225-8c3a-c148ed81dc38.jsonl.

文件名：<把 : 和 . 换成 - 的 ISO 时间戳>_<会话 id>.jsonl CA/src/core/sessionmanager.ts:1079。捕获工具包的文件是 2026-10-05T23-16-41-747Z_01a10e5a-ea92-7225-8c3a-c148ed81dc38.jsonl。

Session id: a UUIDv7 CA/src/core/session-manager.ts:264, so ids sort by creation time. A custom id from --session-id or the SDK must match ^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\$ CA/src/core/session-manager.ts:268.

会话 id：一个 UUIDv7 CA/src/core/session-manager.ts:264，因此 id 按创建时间排序。来自 --session-id 或 SDK 的自定义 id 必须匹配 ^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\$ CA/src/core/session-manager.ts:268。

Entry id: the first 8 hex characters of randomUUID(), checked against existing ids up to 100 times, then a full UUID CA/src/core/session-manager.ts:277.

条目 id：randomUUID() 的前 8 个十六进制字符，最多对照已有 id 检查 100 次，然后才是完整 UUID CA/src/core/session-manager.ts:277。

Files are created lazily. Until the session holds a user or assistant message, entries stay in memory; opening and closing Pi without typing leaves no file CA/src/core/session-manager.ts:1166. The first flush opens the file with flag "wx", which fails if it exists, and writes every bufered entry. After that, each entry is one appendFileSync of one line CA/src/core/sessionmanager.ts:1172. The sessions-tree capture shows the switch: after a model_change the file has 0 lines on disk; after the first user message it has 3.

文件是惰性创建的。在会话持有用户或助手消息之前，条目都留在内存里；打开 Pi 再关闭、什么都不输入，不会留下文件 CA/src/core/session-manager.ts:1166。首次落盘用 "wx" 标志打开文件（若已存在则失败），并写入所有已缓冲的条目。之后每个条目就是一次 appendFileSync、写一行 CA/src/core/sessionmanager.ts:1172。sessions-tree 捕获展示了这次切换：一次 model_change 之后磁盘上的文件有 0 行；第一条用户消息之后有 3 行。

## The file format

## 文件格式

Line 1 is a header. Every later line is one entry with type, id, parentId and an ISO timestamp. CURRENT_SESSION_VERSION is 3 CA/src/core/session-manager.ts:41. These are the first three lines of the one-turn capture, as Pi wrote them:

第 1 行是文件头。之后每一行是一条条目，带 type、id、parentId 和一个 ISO 时间戳。CURRENT_SESSION_VERSION 为 3 CA/src/core/session-manager.ts:41。下面是单轮捕获的前三行，按 Pi 写下的原样：

```txt header, then the first two entries of a real session research/out/one-turn.txt (§session-jsonl, lines 1-3) JSON
{"type":"session","version":3,"id":"01a10e5a-ea92-7225-8c3a-c148ed81dc38","timestamp":"2026-10-05T23:16:41.747Z","cwd":"<tmp>/project"}
{"type":"model_change","id":"2cd13c47","parentId":null,"timestamp":"2026-10-05T23:16:41.749Z","provider":"faux","modelId":"faux-1"}
{"type":"thinking_level_change","id":"f99fc4be","parentId":"2cd13c47","timestamp":"2026-10-05T23:16:41.749Z","thinking Level":"off"}
```

Complete lines, re-serialised on one line each. The header has no parentId and is not an entry. parent Session is absent because it is undefined for a new session and JSON.stringify drops it.

完整行，每行各自重新序列化为单行。文件头没有 parentId，也不是条目。parentSession 之所以缺席，是因为它对新会话来说是 undefined，而 JSON.stringify 会把它丢掉。

<table><tr><td>类型</td><td>额外字段</td><td>是否进入模型上下文</td></tr><tr><td>message</td><td>message：一条 AgentMessage（user、assistant、toolResult、system、bashExecution、custom）</td><td>是</td></tr><tr><td>thinking_level_change</td><td>thinkingLevel</td><td>否；设置状态</td></tr><tr><td>model_change</td><td>provider、modelId</td><td>否；设置状态</td></tr><tr><td>usage</td><td>kind（如 cache_warm）、provider、model、usage、note?</td><td>否</td></tr><tr><td>compaction</td><td>summary、firstKeptEntryId、tokensBefore、details?、usage?、fromHook?、systemMessage?</td><td>是，作为检查点 + 摘要</td></tr><tr><td>branch_summary</td><td>fromId、summary、details?、usage?、fromHook?</td><td>是，作为一条摘要</td></tr><tr><td>custom</td><td>customType、data?</td><td>否；扩展状态</td></tr><tr><td>custom_message</td><td>customType、content、details?、display</td><td>是，作为一条自定义消息</td></tr><tr><td>context_edit</td><td>targetId、replacement: {content} | null</td><td>改变另一条条目</td></tr><tr><td>label</td><td>targetId、label（undefined 表示清除）</td><td>否；书签</td></tr><tr><td>session_info</td><td>name?</td><td>否；显示名称</td></tr></table>

Eleven entry types, and no separate prompt state. The prompt and tool set are system messages inside message entries (system prompt construction (p. 75)); replaying them in order gives the current state. From session-manager.ts (SessionEntry union, lines 183–194).

十一种条目类型，没有单独的提示词状态。提示词和工具集就是 message 条目内部的系统消息（system prompt construction (p. 75)）；按顺序重放它们就得到当前状态。取自 session-manager.ts（SessionEntry 联合类型，第 183–194 行）。

## The tree and the leaf pointer

## 树与叶指针

Every append sets parentId to the current leaf, then moves the leaf to the new entry CA/src/core/session-manager.ts:1191. In a session with no branching the tree is a chain. The one-turn capture is that chain, eight lines long:

每次追加都把 parentId 设为当前叶节点，然后把叶节点移到新条目 CA/src/core/session-manager.ts:1191。在没有分叉的会话里，树就是一条链。单轮捕获正是这样一条链，共八行：

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

## 树

Each line's parentId is the line before it. The root is the first entry, not the header, and the system message sits inside the tree like any other message. Drawn from research/out/one-turn.txt (§session-jsonl); ids are from that run

每一行的 parentId 就是它前面那一行。根是第一条条目，而不是文件头；系统消息和其他消息一样坐在树里。图取自 research/out/one-turn.txt（§session-jsonl）；id 来自那次运行。

Branching does not copy or delete anything. branch(id) moves the leaf to an earlier entry, and the next append becomes a sibling of whatever followed it CA/src/core/session-manager.ts:1579. The sessions-tree capture builds a real branched file with SessionManager and then reopens it:

分叉既不复制也不删除任何东西。branch(id) 把叶节点移到某个更早的条目上，下一次追加就成为它后继那些条目的兄弟 CA/src/core/session-manager.ts:1579。sessions-tree 捕获用 SessionManager 构造了一个真正带分叉的文件，然后重新打开它：

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

## 树

Labels are tree entries, and they move the leaf. appendLabelChange(a1) hung the label under a3, the leaf at the time, so the later branch_summary records fromId=lb, a label, as the branch it left. A final branch(u1) without an append was lost: the reopened session's leaf is bs. From research/out/sessions-tree.txt; names replace the 8-hex ids.

标签就是树里的条目，而且它们会移动叶节点。appendLabelChange(a1) 把标签挂在了当时的叶节点 a3 之下，因此后来那条 branch_summary 记录的 fromId=lb —— 一个标签 —— 正是它离开的那个分支。最后那次没有追加的 branch(u1) 丢了：重开会话后的叶节点是 bs。取自 research/out/sessions-tree.txt；名字替代了 8 位十六进制 id。

The leaf is never written down. On load, _buildIndex() sets it to the last entry in file order CA/src/core/sessionmanager.ts:1103. A branch therefore survives a restart only once something has been appended under it. Labels resolve the same way: the latest label entry for a target, in file order, wins, and a label of undefined clears it.

叶节点从不写进文件。加载时 _buildIndex() 把它设为文件顺序中的最后一条条目 CA/src/core/sessionmanager.ts:1103。因此一个分支只有在它下面被追加过东西之后，才能在重启后存活。标签的解析方式相同：按文件顺序，针对同一 target 的最新 label 条目胜出，而值为 undefined 的 label 会把它清除。

<table><tr><td>操作</td><td>效果</td></tr><tr><td>branch(id) CA/src/core/session-manager.ts:1579</td><td>移动叶节点；下一次追加会创建一个兄弟节点</td></tr><tr><td>resetLeaf() CA/src/core/session-manager.ts:1591</td><td>leaf = null；下一次追加会成为一个新根（用于重新编辑第一条消息）</td></tr><tr><td>branchWithSummary(fromId, summary) CA/src/core/session-manager.ts:1600</td><td>移动叶节点并在其下追加一条 branch_summary；fromId 是旧叶节点，或 &quot;root&quot;</td></tr><tr><td>createBranchedSession(leafId) CA/src/core/session-manager.ts:1632</td><td>新文件，只含从根到叶的路径；label 条目被丢弃，路径重新串成链，标签在末尾重新追加；parentSession = 旧文件</td></tr><tr><td>forkFrom(src, targetCwd) CA/src/core/session-manager.ts:1815</td><td>把另一个文件的每条条目复制到一个新文件，供另一个 cwd 使用（--fork、跨项目 --session）</td></tr></table>

Nothing is ever deleted. Each operation either moves the in-memory leaf or writes a new file. From session-manager.ts (Branching).

任何东西都不会被删除。每个操作要么移动内存中的叶节点，要么写出一个新文件。取自 session-manager.ts（Branching）。

get Tree() makes an entry whose parent is missing a root, and sorts each node's children by timestamp CA/src/core/sessionmanager.ts:1529. A path walk from such an entry stops at the gap.

getTree() 会把父条目缺失的条目当作根，并按时间戳排序每个节点的子节点 CA/src/core/sessionmanager.ts:1529。从这样一个条目出发的路径遍历，会在缺口处停下。

## Loading and migration

## 加载与迁移

loadEntriesFromFile() reads in 1 MiB chunks, splits on \n, and skips blank and malformed lines without a warning CA/src/core/session-manager.ts:627. If the first parsed entry is not a header with a string id, it returns []. A last line without a trailing newline is kept and the newline is appended to the file.

loadEntriesFromFile() 以 1 MiB 为块读取，按 \n 切分，并静默跳过空行和格式错误的行 CA/src/core/session-manager.ts:627。如果解析出的第一条不是带字符串 id 的文件头，它就返回 []。最后一行若没有结尾换行会被保留，同时给文件补上换行。

An empty file is initialised with a new header. A non-empty file that yields no entries throws "Session file is not a valid pi session: path" and is not modified CA/src/core/session-manager.ts:1039.

空文件会用一个新文件头初始化。非空文件若解析不出任何条目，则抛出 "Session file is not a valid pi session: path"，并且文件不会被修改 CA/src/core/session-manager.ts:1039。

Migrations run when the header's version is below 3 (absent counts as 1), and the whole file is then rewritten CA/src/core/session-manager.ts:337:

当文件头的版本低于 3（缺失算作 1）时，迁移会运行，随后整个文件被重写 CA/src/core/session-manager.ts:337：

v1 → v2: assign an id to every entry, chain parentId linearly in file order, and convert a compaction's firstKeptEntryIndex into firstKeptEntryId CA/src/core/session-manager.ts:287.

v1 → v2：给每条条目分配一个 id，按文件顺序把 parentId 串成链，并把 compaction 的 firstKeptEntryIndex 转成 firstKeptEntryId CA/src/core/session-manager.ts:287。

v2 → v3: the message role hook Message becomes custom CA/src/core/session-manager.ts:316.

v2 → v3：消息角色 hookMessage 变成 custom CA/src/core/session-manager.ts:316。

## Context reconstruction

## 上下文重建

The model never sees the file. It sees a projection of one path through it, rebuilt by buildSessionProjection() CA/src/core/session-manager.ts:543.

模型从来看不到这个文件。它看到的是穿过文件的一条路径的投影，由 buildSessionProjection() 重建 CA/src/core/session-manager.ts:543。

![](images/16403b5bdc983dc2b3b5ef16d8b00477ca2e8a12fc4bdb3d540901d54a17122c.jpg)

Only the newest compaction on the path contributes a summary. An older compaction that falls inside the kept range is projected as nothing, and raw system messages before the cut are dropped because the compaction carries its own snapshot. From session-manager.ts (buildSessionPath, getSessionContextSettings, buildContextEntries, buildSessionProjection, sessionEntryToContextMessages).

路径上只有最新的那次压缩会贡献摘要。落在保留范围内的更早压缩会被投影成空，而切口之前的原始系统消息会被丢弃，因为压缩自带一份快照。取自 session-manager.ts（buildSessionPath、getSessionContextSettings、buildContextEntries、buildSessionProjection、sessionEntryToContextMessages）。

Path: from the leaf back to the root, then reversed CA/src/core/session-manager.ts:390. Siblings on other branches are not on it.

路径：从叶节点回溯到根，然后反转 CA/src/core/session-manager.ts:390。其他分支上的兄弟节点不在其中。

Settings: thinking Level is the last thinking_level_change on the path, default "off". model is the last model_change or assistant message, whichever is later CA/src/core/session-manager.ts:418.

设置：thinkingLevel 取路径上最后一个 thinking_level_change，默认 "off"。model 取最后一个 model_change 或 assistant 消息，以较晚者为准 CA/src/core/session-manager.ts:418。

Compaction: with a compaction C on the path, the entries are C, then the entries from C.firstKeptEntryId up to C minus raw system messages, then everything after C CA/src/core/session-manager.ts:476. compaction and branch summaries (p. 92) covers how C is made.

压缩：若路径上有一次压缩 C，条目依次是 C，然后是从 C.firstKeptEntryId 到 C 之前的条目（去掉原始系统消息），再是 C 之后的所有条目 CA/src/core/session-manager.ts:476。compaction and branch summaries (p. 92) 介绍了 C 是怎么做出来的。

Context edits: the latest context_edit per target applies; null omits the target, a value replaces only its content CA/src/core/session-manager.ts:519. Only edits on the current path count, so an edit is branch-local.

上下文编辑：针对每个 target，最新的 context_edit 生效；null 表示省略该 target，有值则只替换它的内容 CA/src/core/session-manager.ts:519。只有当前路径上的编辑算数，因此编辑是分支局部的。

Messages: a message yields its message; custom_message a custom message; branch_summary a branch Summary message; compaction its system Message snapshot followed by a compaction Summary message; every other type yields nothing CA/src/core/session-manager.ts:439.

消息：message 产出其 message；custom_message 产出一条自定义消息；branch_summary 产出一条分支摘要消息；compaction 产出它的系统消息快照，随后是一条压缩摘要消息；其他任何类型都不产出内容 CA/src/core/session-manager.ts:439。

Run against the branched capture, the reopened session's path is mc → u1 → a1 → u2 → a2 → bs, and its context is five messages: user, assistant, user, assistant, branch Summary. The model_change sets state and contributes no message; branch B and its label are not on the path.

对带分叉的捕获运行，重开会话后的路径是 mc → u1 → a1 → u2 → a2 → bs，其上下文是五条消息：user、assistant、user、assistant、分支摘要。model_change 设置状态、不贡献消息；分支 B 及其标签不在这条路径上。

## F O O T G U N

## 危险做法

Moving the leaf is not saved. /tree navigation without a summary or label, branch() from the SDK, or an extension that repositions the leaf all leave the file unchanged until the next append CA/src/core/agent-session.ts:4113. If Pi exits first, the session reopens at the last line of the file, and that line can belong to the branch the user just left. Appending a label to the target is the cheapest way to pin a position.

移动叶节点不会被保存。没有摘要或标签的 /tree 导航、来自 SDK 的 branch()，以及重新定位叶节点的扩展，都会让文件在下一次追加之前保持不变 CA/src/core/agent-session.ts:4113。如果 Pi 先退出了，会话会在文件的最后一行重开，而那一行可能属于用户刚刚离开的那个分支。往目标上追加一条标签是钉住一个位置最便宜的办法。

W H A T T H I S M E A N S F O R Y O U

## 这对你意味着什么

Parse a session by building the parentId index, not by reading lines in order.

要解析一个会话，请构建 parentId 索引，而不是按顺序读行。

Treat the last line as the leaf only for a file at rest; a running Pi can hold its leaf elsewhere.

只有处于静止状态的文件才把最后一行当作叶节点；正在运行的 Pi 可能把叶节点放在别处。

Use custom entries for extension state and custom_message for text the model should see.

扩展状态用 custom 条目，模型应当看到的文本用 custom_message。

Hide or rewrite an earlier message with context_edit; the original line stays in the file.

用 context_edit 隐藏或改写更早的消息；原始那一行仍留在文件里。

Sources: CA/src/core/session-manager.ts (SessionHeader, SessionEntry types, createSessionId, assertValidSessionId, generateId, migrateV1ToV2, migrateV2ToV3, migrateToCurrentVersion, buildSessionPath, getSessionContextSettings, sessionEntryToContextMessages, buildContextEntries, projectContextEntry, buildSessionProjection, getDefaultSessionDirPath, loadEntriesFromFile, SessionManager: _setSessionFile, new Session, _buildIndex, _hasConversation, _persist, _appendEntry, appendLabelChange, get Tree, branch, reset Leaf, branchWithSummary, createBranchedSession, fork From); CA/src/main.ts (session directory); CA/docs/session-format.md; research/capture/sessions-tree.mjs; research/out/sessions-tree.txt; research/out/one-turn.txt (§session-files, §sessionjsonl)

来源：CA/src/core/session-manager.ts（SessionHeader、SessionEntry 类型、createSessionId、assertValidSessionId、generateId、migrateV1ToV2、migrateV2ToV3、migrateToCurrentVersion、buildSessionPath、getSessionContextSettings、sessionEntryToContextMessages、buildContextEntries、projectContextEntry、buildSessionProjection、getDefaultSessionDirPath、loadEntriesFromFile、SessionManager：_setSessionFile、new Session、_buildIndex、_hasConversation、_persist、_appendEntry、appendLabelChange、getTree、branch、resetLeaf、branchWithSummary、createBranchedSession、forkFrom）；CA/src/main.ts（会话目录）；CA/docs/session-format.md；research/capture/sessions-tree.mjs；research/out/sessions-tree.txt；research/out/one-turn.txt（§session-files、§session-jsonl）

## 4.4 Compaction and branch summaries

## 4.4 压缩与分支摘要

When the context windowfills, Pi asks the model to write a structured checkpoint of the old messages and appends it as one entry. The file keeps every raw line; only the projection the model sees gets shorter.

当上下文窗口快满时，Pi 让模型把旧消息写成一份结构化检查点，并作为一条条目追加进去。文件保留每一行原始内容；变短的只是模型看到的投影。

A long coding session outgrows any context window. Pi's answer is compaction: summarise the oldest part of the current path, keep the newest part verbatim, and record the result as a compaction entry in the session tree (sessions, the JSONL tree (p. 86)). This section shows when compaction triggers and how overflow is recovered, how the cut point is chosen, and how the summary is generated and with what prompt. It ends with what the model sees afterwards, and with the branch summary that /tree writes when the user leaves a branch.

再长的编码会话也会超出任何上下文窗口。Pi 的答案是压缩：把当前路径最老的那部分总结起来，最新的那部分逐字保留，再把结果作为一条压缩条目记进会话树（sessions, the JSONL tree (p. 86)）。本节说明压缩何时触发、溢出如何恢复，切口点如何选择，以及摘要如何生成、用什么提示词生成；最后讲模型之后看到什么，以及用户离开某个分支时 /tree 写入的分支摘要。

## When it triggers

## 何时触发

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

第 126–130 行与 267–270 行；为紧凑起见省略了它们之间的 token 估算函数。

With the defaults, a 200,000-token window compacts above 183,616 tokens. reserve Tokens and keepRecentTokens can be overridden per model under compaction.model Overrides["provider/modelId"], with exact, case-sensitive keys; enabled stays global CA/src/core/settings-manager.ts:940. All three keys are in settings reference (p. 202).

按默认值，一个 200,000 token 的窗口在超过 183,616 token 时触发压缩。reserveTokens 和 keepRecentTokens 可以在 compaction.modelOverrides["provider/modelId"] 下按模型覆盖，键必须精确且区分大小写；enabled 仍是全局的 CA/src/core/settings-manager.ts:940。三个键都在 settings reference (p. 202)。

Context size is measured, then estimated. The base is the last valid assistant message's usage.total Tokens, or the sum of its parts; aborted, errored and all-zero responses do not count CA/src/core/compaction/compaction.ts:148. Messages after it are estimated at characters ÷ 4, with an image counted as 4,800 characters CA/src/core/compaction/compaction.ts:276. Usage captured before the latest context_edit or compaction on the branch is not trusted, and the whole projection is estimated instead CA/src/core/compaction/compaction.ts:227.

上下文大小先测量，再估算。基准是最后一条有效 assistant 消息的 usage.totalTokens，或各部分之和；中止的、出错的和全零的响应都不计入 CA/src/core/compaction/compaction.ts:148。它之后的消息按字符数 ÷ 4 估算，一张图片按 4,800 个字符计 CA/src/core/compaction/compaction.ts:276。在该分支上最新的 context_edit 或压缩之前捕获到的 usage 不可信，此时改为估算整个投影 CA/src/core/compaction/compaction.ts:227。

<table><tr><td>触发点</td><td>位置</td><td>原因</td></tr><tr><td>之后每个轮次之前</td><td>prepareNextTurnWithContext → _compactBeforeNextAssistantResponse CA/src/core/agent-session.ts:764</td><td>阈值</td></tr><tr><td>每次请求，虚拟模型</td><td>prepareRequest，对照路由到的模型窗口 CA/src/core/agent-session.ts:826</td><td>阈值</td></tr><tr><td>一次运行之后</td><td>_handlePostAgentRun → _checkCompaction CA/src/core/agent-session.ts:1870</td><td>阈值或溢出</td></tr><tr><td>一次提示词之前</td><td>prompt() → _checkCompaction，包含被中止的响应 CA/src/core/agent-session.ts:2042</td><td>阈值</td></tr><tr><td>手动</td><td>/compact [instructions] → compact()；先中止当前运行，且绝不重试 CA/src/core/agent-session.ts:2750</td><td>手动</td></tr></table>

Five entry points, one generator. Manual and automatic compaction both end in _runDefaultCompaction() and the compact() function from compaction/, unless a session_before_compact handler cancels or supplies the result. From agent-session.ts.

五个入口，一个生成器。手动压缩和自动压缩最终都进入 _runDefaultCompaction() 以及来自 compaction/ 的 compact() 函数，除非有 session_before_compact 处理器取消或直接提供结果。取自 agent-session.ts。

Overflow is handled after a run CA/src/core/agent-session.ts:2933. A context-overflow error, or a length stop that ended below the model's own output limit, starts recovery. Pi hides the failed response and its tool results with context_edit entries whose replacement is null CA/src/core/agent-session.ts:1224, compacts, and retries the turn once. A second failure ends with "Context overflow recovery failed after one compact-and-retry attempt. Try reducing context or switching to a larger-context model." (or "Truncated response recovery failed after one compact-and-retry attempt." for a length stop). An overflow reported by a diferent model than the current one is ignored, and so is any assistant message older than the latest compaction. If the response completed with stop but still exceeded the window, Pi compacts without retrying.

溢出在一次运行之后处理 CA/src/core/agent-session.ts:2933。上下文溢出错误，或一个在低于模型自身输出上限处结束的 length 停止，都会启动恢复流程。Pi 用 replacement 为 null 的 context_edit 条目把失败的响应及其工具结果隐藏起来 CA/src/core/agent-session.ts:1224，做一次压缩，然后重试该轮次一次。第二次失败以 "Context overflow recovery failed after one compact-and-retry attempt. Try reducing context or switching to a larger-context model." 结束（length 停止则是 "Truncated response recovery failed after one compact-and-retry attempt."）。由当前模型之外的其他模型上报的溢出会被忽略，比最新压缩更早的 assistant 消息也会被忽略。如果响应以 stop 结束却仍超出窗口，Pi 会压缩而不重试。

## Choosing the cut point

## 选择切口点

prepare Compaction() works on the projected path, not on raw lines CA/src/core/compaction/compaction.ts:872. It starts after the newest compaction that contributes a summary, so the entries that compaction kept are summarised again, together with its summary. Then findProjectedCutPoint() walks backwards from the newest entry, summing estimated tokens until the total reaches keepRecentTokens, and snaps to the nearest valid cut point at or after that entry CA/src/core/compaction/compaction.ts:802

prepareCompaction() 处理的是投影后的路径，而不是原始行 CA/src/core/compaction/compaction.ts:872。它从最新那次贡献摘要的压缩之后开始，因此那次压缩保留的条目会连同它的摘要一起被再次总结。然后 findProjectedCutPoint() 从最新条目往回走，累加估算 token 直到总量达到 keepRecentTokens，并吸附到该条目或其之后的最近一个有效切口点 CA/src/core/compaction/compaction.ts:802

![](images/d508e5083584b34eb1687ac72838421cea0f5c8088b3a3fcce3aeebf1bac220c.jpg)

A cut never lands on a tool result. Valid cut points are entries that yield a user, assistant, bash Execution, custom, branch Summary or compaction Summary message, so a call and its result stay on the same side. Here the cut lands on an assistant, mid-turn, so the turn's start is summarised separately. Schematic; from compaction.ts (isCutPointMessage, isTurnStartMessage, findProjectedCutPoint, prepare Compaction).

切口绝不会落在工具结果上。有效切口点是那些能产出 user、assistant、bashExecution、custom、分支摘要或压缩摘要消息的条目，因此一次调用和它的结果留在同一侧。这里切口落在一个 assistant 消息上，处于轮次中间，因此该轮次的开头被单独总结。示意图；取自 compaction.ts（isCutPointMessage、isTurnStartMessage、findProjectedCutPoint、prepareCompaction）。

After snapping, the cut moves back over adjacent entries that contribute no message, such as a model_change, so they stay with the kept part. If the cut entry does not start a turn, the cut is a split turn: the messages from the turn's start up to the cut become turnPrefixMessagesCA/src/core/compaction/compaction.ts:903. A turn starts at a user, bash Execution, custom, branch Summary or compaction Summary message.

吸附之后，切口会越过相邻的、不贡献消息的条目（比如 model_change）往回退，使它们留在保留部分中。如果切口条目不是某个轮次的开头，这就是一次轮次切分：从该轮次开头到切口的这些消息成为 turnPrefixMessages CA/src/core/compaction/compaction.ts:903。一个轮次始于 user、bashExecution、custom、分支摘要或压缩摘要消息。

prepare Compaction() returns undefined when the path already ends in a compaction or there is nothing to summarise; manual compaction reports these as "Already compacted" and "Nothing to compact (session too small)" CA/src/core/agentsession.ts:2771. Otherwise it returns a CompactionPreparation, which session_before_compact handlers receive:

当路径已经以一次压缩结尾，或没有东西可总结时，prepareCompaction() 返回 undefined；手动压缩会把这些情况报告为 "Already compacted" 和 "Nothing to compact (session too small)" CA/src/core/agentsession.ts:2771。否则它返回一个 CompactionPreparation，session_before_compact 处理器会收到它：

firstKeptEntryId: the id of the first entry kept verbatim.

firstKeptEntryId：第一条逐字保留的条目的 id。

messagesToSummarize: messages from the previous boundary to the cut, or to the turn start for a split turn, with system messages removed.

messagesToSummarize：从上一个边界到切口的消息；对于轮次切分，则是到轮次开头为止；其中系统消息已被移除。

turnPrefixMessages: the split turn's messages before the cut; empty otherwise.

turnPrefixMessages：被切分轮次在切口之前的消息；其他情况为空。

previous Summary: the summary of the compaction being replaced, used to select the update prompt.

previousSummary：被替换掉的那次压缩的摘要，用于选择更新提示词。

file Ops: files read, written and edited, taken from read, write and edit tool calls, from nested calls recorded on tool results, and from the previous compaction's details if Pi generated it CA/src/core/compaction/compaction.ts:60.

fileOps：被读取、写入和编辑过的文件，来源是 read、write 和 edit 工具调用，记录在工具结果上的嵌套调用，以及（若那次压缩是 Pi 生成的）上一次压缩的 details CA/src/core/compaction/compaction.ts:60。

tokens Before: the projected context estimate before compaction.

tokensBefore：压缩前的投影上下文估算值。

## Generating the summary

## 生成摘要

![](images/c2cd8a508325eb76ab605778d3c79fc3878acb506715373942a0b711226e330c.jpg)

Two model calls at most, both one-shot. With the default 16,384-token reserve the history summary may use up to 13,107 output tokens and the turn-prefix summary 8,192, each capped by the model's max Tokens. From compaction.ts (compact, generateSummaryWithUsage, generateTurnPrefixSummary) and agentsession.ts (compact, _runAutoCompaction).

最多两次模型调用，都是一次性的。按默认 16,384 token 的预留，历史摘要最多可用 13,107 个输出 token，轮次前缀摘要可用 8,192 个，各自还受模型 maxTokens 限制。取自 compaction.ts（compact、generateSummaryWithUsage、generateTurnPrefixSummary）和 agentsession.ts（compact、_runAutoCompaction）。

The summary request has its own system prompt, SUMMARIZATION_SYSTEM_PROMPT: "You are a context summarization assistant. … Do NOT continue the conversation. Do NOT respond to any questions in the conversation. ONLY output the structured summary." CA/src/core/compaction/utils.ts:161. The conversation is serialised to text, so the model reads it instead of continuing it CA/src/core/compaction/utils.ts:114:

摘要请求有自己的系统提示词 SUMMARIZATION_SYSTEM_PROMPT："You are a context summarization assistant. … Do NOT continue the conversation. Do NOT respond to any questions in the conversation. ONLY output the structured summary." CA/src/core/compaction/utils.ts:161。会话被序列化成文本，因此模型是在读它而不是继续它 CA/src/core/compaction/utils.ts:114：

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

由代码拼装而成；工具调用参数是示意性的，各标题下的方括号提示已省略。<previous-summary> 只在已有先前摘要时出现，此时 UPDATE_SUMMARIZATION_PROMPT 会把指令换成用于保留、添加以及把条目从 In Progress 移到 Done 的规则。Additional focus: 只在带 /compact 指令时出现。

For a split turn, the turn prefix is summarised separately under the headings Original Request, Progress So Far and Context Needed to Continue. The two texts are joined as history\n\n---\n\n**Turn Context (split turn):**\n\nprefix, and with no older history the first part reads "No prior history." CA/src/core/compaction/compaction.ts:1032. Then the file lists are appended as <read-files> and <modified-files> blocks, sorted, with a file that was both read and modified listed only as modified CA/src/core/compaction/utils.ts:67.

对于被切分的轮次，轮次前缀会在 Original Request、Progress So Far 和 Context Needed to Continue 这几个标题下单独总结。两段文本按 history\n\n---\n\n**Turn Context (split turn):**\n\nprefix 连接；如果没有更早的历史，第一部分就是 "No prior history." CA/src/core/compaction/compaction.ts:1032。随后文件列表以 `<read-files>` 和 `<modified-files>` 块追加，已排序，其中既被读取又被修改的文件只列为已修改 CA/src/core/compaction/utils.ts:67。

Every summary request runs with cache Retention: "none" and a fresh UUIDv7 sessionId, through the session's retry policy CA/src/core/compaction/compaction.ts:619. Reasoning is requested only if the model supports it and the thinking level resolved for the request is not off CA/src/core/compaction/compaction.ts:606. A response that stops with error or length, or that contains a tool call, fails the compaction: a length stop is a partial summary and is never stored CA/src/core/compaction/compaction.ts:585.

每次摘要请求都以 cacheRetention: "none" 和一个全新的 UUIDv7 sessionId 运行，并遵循会话的重试策略 CA/src/core/compaction/compaction.ts:619。只有模型支持推理、且为该请求解析出的 thinking level 不为 off 时才会请求推理 CA/src/core/compaction/compaction.ts:606。以 error 或 length 停止的响应，或包含工具调用的响应，都算这次压缩失败：length 停止意味着只拿到了部分摘要，绝不会被存储 CA/src/core/compaction/compaction.ts:585。

## What the model sees afterwards

## 之后模型看到什么

append Compaction() stores the summary, firstKeptEntryId, tokens Before, details and usage, plus system Message: the complete replayed prompt and tool set at that moment CA/src/core/session-manager.ts:1261. The next projection of the path is:

appendCompaction() 存储 summary、firstKeptEntryId、tokensBefore、details 和 usage，外加 systemMessage：那一刻完整重放出来的提示词与工具集 CA/src/core/session-manager.ts:1261。该路径的下一次投影是：

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

摘要以一条用户消息的形式到达供应商，由 convertToLlm() 用 COMPACTION_SUMMARY_PREFIX 和 COMPACTION_SUMMARY_SUFFIX 构造 CA/src/core/messages.ts:11。原始条目仍留在 JSONL 文件里；压缩只改变 buildSessionProjection() 的返回值。把叶节点移到一条不含该压缩的分支上，完整历史就会回来。

The snapshot replaces every earlier system message, so the summary follows a single complete prompt rather than a chain of patches. That resets the prompt history as well as the conversation. It also means the first request after compaction has a new prefix, and the provider cache starts over.

这份快照取代了更早的每一条系统消息，因此摘要后面跟着的是一条完整的提示词，而不是一串补丁。这既重置了会话，也重置了提示词历史。它还意味着压缩之后的第一个请求有了新的前缀，供应商缓存要重新开始。

## Branch summaries

## 分支摘要

When the user jumps to another node with /tree (slash commands and keybindings (p. 197)), Pi can summarise the branch being left. navigate Tree() does it in five steps CA/src/core/agent-session.ts:3949:

当用户用 /tree 跳到另一个节点时（slash commands and keybindings (p. 197)），Pi 可以总结将要离开的那个分支。navigateTree() 分五步完成 CA/src/core/agent-session.ts:3949：

1. collectEntriesForBranchSummary(old Leaf, target) collects the entries from the old leaf back to the deepest ancestor shared with the target CA/src/core/compaction/branch-summarization.ts:108.

1. collectEntriesForBranchSummary(oldLeaf, target) 收集从旧叶节点回溯到与目标共享的最深祖先为止的那些条目 CA/src/core/compaction/branch-summarization.ts:108。

2. A session_before_tree handler can cancel, supply a summary, replace or extend the instructions, or set a label.

2. 一个 session_before_tree 处理器可以取消、提供摘要、替换或扩充指令，或者设置一个标签。

3. generateBranchSummary() keeps entries newest first within context Window − branch Summary.reserve Tokens (16,384 by default; a window of 0 counts as 128,000), skips tool results, and squeezes in an older compaction or branch summary while under 90 % of the budget CA/src/core/compaction/branch-summarization.ts:195. The prompt has the compaction headings minus Critical Context, and max Tokens is min(4096, model.max Tokens).

3. generateBranchSummary() 在 contextWindow − branchSummary.reserveTokens 的范围内按最新优先保留条目（默认 16,384；窗口为 0 时按 128,000 计），跳过工具结果，并在预算的 90 % 以内额外塞进一次更早的压缩或分支摘要 CA/src/core/compaction/branch-summarization.ts:195。提示词使用压缩的那些标题，但去掉 Critical Context；maxTokens 为 min(4096, model.maxTokens)。

4. The result is prefixed with "The user explored a diferent conversation branch before returning here.\nSummary of that exploration:\n\n" and followed by the file lists CA/src/core/compaction/branch-summarization.ts:253.

4. 结果前面加上 "The user explored a diferent conversation branch before returning here.\nSummary of that exploration:\n\n"，后面跟上文件列表 CA/src/core/compaction/branch-summarization.ts:253。

5. If the target is a user or custom message, the new leaf is the target's parent and its text goes back into the editor. Otherwise the leaf is the target. branchWithSummary() then appends the summary as a child of the new leaf, not of the old branch.

5. 如果目标是 user 或 custom 消息，新叶节点就是目标的父节点，而目标的文本会回到编辑器里。否则叶节点就是目标本身。随后 branchWithSummary() 把摘要追加为新叶节点的子节点，而不是旧分支的子节点。

In context the entry becomes a user message wrapped in "The following is a summary of a branch that this conversation came back from:" and <summary> tags CA/src/core/messages.ts:19. Setting branch Summary.skip Prompt skips the interactive question and defaults to no summary.

进入上下文时，这条条目变成一条用户消息，外面包着 "The following is a summary of a branch that this conversation came back from:" 以及 `<summary>` 标签 CA/src/core/messages.ts:19。设置 branchSummary.skipPrompt 会跳过那个交互式提问，并默认为不生成摘要。

## R U L E O F T H U M B

## 经验法则

If you only want the summary to focus on something, pass instructions to /compact. If you need a diferent summary altogether, return one from session_before_compact; it is stored with from Hook: true and its details are not read back as file lists. If one model has a far larger window than the others, set a model Overrides entry for it instead of changing the global reserve Tokens.

如果你只想让摘要聚焦某件事，把指令传给 /compact。如果你需要一份完全不同的摘要，就从 session_before_compact 返回一个；它会带着 fromHook: true 被存储，而且它的 details 不会被读回当作文件列表。如果某个模型的窗口比其他模型大得多，就为它设置一条 modelOverrides，而不是去改全局的 reserveTokens。

Sources: CA/src/core/compaction/compaction.ts (DEFAULT_COMPACTION_SETTINGS, calculateContextTokens, getAssistantUsage, estimateContextTokens, estimateProjectedContextTokens, should Compact, estimate Tokens, isCutPointMessage, isTurnStartMessage, findProjectedCutPoint, prepare Compaction, SUMMARIZATION_PROMPT, UPDATE_SUMMARIZATION_PROMPT, TURN_PREFIX_SUMMARIZATION_PROMPT, getSummarizationFailure, complete Summarization, generateSummaryWithUsage, compact); CA/src/core/compaction/utils.ts (extractFileOpsFromMessage, computeFileLists, formatFileOperations, serialize Conversation, SUMMARIZATION_SYSTEM_PROMPT); CA/src/core/compaction/branch-summarization.ts (collectEntriesForBranchSummary, prepareBranchEntries, generateBranchSummary); CA/src/core/agent-session.ts (_compactBeforeNextAssistantResponse, _installAgentRequestProjection, _handlePostAgentRun, prompt, compact, _checkCompaction, _runAutoCompaction, _omitRecoveryAttempt, navigate Tree); CA/src/core/session-manager.ts (append Compaction, buildContextEntries); CA/src/core/messages.ts (COMPACTION_SUMMARY_PREFIX, BRANCH_SUMMARY_PREFIX, convertToLlm); CA/src/core/settings-manager.ts (getCompactionSettings, getBranchSummarySettings); CA/docs/compaction.md

来源：CA/src/core/compaction/compaction.ts（DEFAULT_COMPACTION_SETTINGS、calculateContextTokens、getAssistantUsage、estimateContextTokens、estimateProjectedContextTokens、shouldCompact、estimateTokens、isCutPointMessage、isTurnStartMessage、findProjectedCutPoint、prepareCompaction、SUMMARIZATION_PROMPT、UPDATE_SUMMARIZATION_PROMPT、TURN_PREFIX_SUMMARIZATION_PROMPT、getSummarizationFailure、completeSummarization、generateSummaryWithUsage、compact）；CA/src/core/compaction/utils.ts（extractFileOpsFromMessage、computeFileLists、formatFileOperations、serializeConversation、SUMMARIZATION_SYSTEM_PROMPT）；CA/src/core/compaction/branch-summarization.ts（collectEntriesForBranchSummary、prepareBranchEntries、generateBranchSummary）；CA/src/core/agent-session.ts（_compactBeforeNextAssistantResponse、_installAgentRequestProjection、_handlePostAgentRun、prompt、compact、_checkCompaction、_runAutoCompaction、_omitRecoveryAttempt、navigateTree）；CA/src/core/session-manager.ts（appendCompaction、buildContextEntries）；CA/src/core/messages.ts（COMPACTION_SUMMARY_PREFIX、BRANCH_SUMMARY_PREFIX、convertToLlm）；CA/src/core/settings-manager.ts（getCompactionSettings、getBranchSummarySettings）；CA/docs/compaction.md