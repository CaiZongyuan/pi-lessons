---
title: 系统提示词构建
---

<div class="section-kicker">4.1 / THE CODING AGENT</div>

# 系统提示词构建

---

Pi 的提示词是一个由具名分节组成的有序映射，而不是一个字符串。因此，会话进行中的变化可以作为一个小补丁追加到对话记录中，之前的每条消息则逐字节保持发送时的原样。



<strong>Pi 发送的每个请求都以系统提示词开头，而编码智能体的提示词会在会话期间发生变化：安装了技能、关闭了工具，或者扩展添加了指令。本节介绍九类分节及其顺序，以及各项输入的读取来源。</strong>随后会展示变化如何在对话记录中成为 `SystemMessage` 补丁，而不是重写提示词。Pi 自身的默认提示词很短：一句开场说明、工具列表、少量规则，以及指向其文档的路径。见 `CA/src/core/system-prompt.ts:128`。

## 分节及其顺序



`buildSystemPromptSections()` 返回一个 `Record<string, string>`，其键的顺序就是提示词的顺序。见 `CA/src/core/system-prompt.ts:128`。`preamble` 是不带标签的文本。其余每节都包裹为 `<name>\n…\n</name>`，见 `CA/src/core/system-prompt.ts:190`，这样后续更新便能按名称指定要替换的分节。



<ManualFigure id="4.1" />

> <strong>自定义提示词替换的是四节，而不是一节。</strong>当 `SYSTEM.md` 或 `--system-prompt` 提供 `preamble` 时，根本不会构建 `tools`、`rules` 和 `docs`，见 `CA/src/core/system-prompt.ts:152`。带斜线底纹的框表示自定义提示词会移除的分节；空分节会被省略。本图为示意图，依据 `buildSystemPromptSections()` 绘制。
> 
> 



- `preamble`：<strong>默认文本是一句说明：“你是一名专业编码助手，运行在编码智能体运行框架 pi 中。你通过读取文件、执行命令、编辑代码和编写新文件来帮助用户。”</strong>见 `CA/src/core/system-prompt.ts:156`。<strong>自定义提示词会原样替换它。</strong>

- <strong>`tools`：对于每个声明了且具有 `promptSnippet` 的工具，生成一行 `- ${name}: ${snippet}`，然后加上“除上述工具外，根据项目情况，你可能还可以使用其他自定义工具。”没有片段的工具不会列入；如果一个也没有，列表显示 `(none)`</strong>。见 `CA/src/core/system-prompt.ts:157`。被 `prepareLoadout` 钩子隐藏的工具会被排除，因为请求没有声明这些工具，见 `CA/src/core/system-prompt.ts:150`。

- <strong>`rules`：来自 `buildRules()` 的去重项目列表</strong>，见 `CA/src/core/system-prompt.ts:88`。<strong>先是“使用 bash 进行 ls、rg、find 等文件操作”，再是额外的 `promptGuidelines`，最后始终附上“回答要简洁”和“处理文件时清楚地显示文件路径”。</strong>

- <strong>`docs`：指向 Pi 的 `README`、`docs/` 和 `examples/` 的绝对路径，并指示仅“在用户询问 pi 本身时”阅读这些文档</strong>，见 `CA/src/core/system-prompt.ts:162`。

- <strong>`addendum`：追加提示词文本；有多个时用空行连接</strong>，见 `CA/src/core/agent-session.ts:1697`。

- <strong>`project_context`：“项目特定的指令和准则：”，后面为每个上下文文件附上一个 `<project_instructions path="…">…</project_instructions>` 块</strong>，见 `CA/src/core/system-prompt.ts:79`。加载哪些文件，详见“上下文文件、技能、模板、主题与包”（原书第106页）。

- `skills`：`<available_skills>` 索引；每个允许模型调用的技能都有一个 `<skill>`，包含 `name`、`description` 和 `location`，见 `CA/src/core/skills.ts:358`。只有选用了 `read` 或 `bash` 时才会添加；如果两者都隐藏，提示便不会指定任何工具，见 `CA/src/core/system-prompt.ts:175`。

- `cwd`：工作目录，其中反斜杠会转为 `/`，见 `CA/src/core/system-prompt.ts:183`。

- <strong>自定义分节：来自 `systemPromptOptions.sections` 的扩展分节。</strong>名称必须匹配 `^[a-z][a-z0-9_-]*$`，且不能是 `preamble`，否则构建会抛出 `Invalid system prompt section name`（系统提示词分节名称无效），见 `CA/src/core/system-prompt.ts:58`。



<ManualFigure id="prompt-cards" />



<strong>工作目录是提示词中唯一的环境信息。`system-prompt.ts` 中没有任何地方会注入日期、时间、操作系统或 shell。需要这些信息的扩展可以在 `before_agent_start` 中添加一个分节</strong>，详见“扩展事件与上下文”（原书第120页）。

## 来自采集工具包的已存储提示词



<strong>提示词并不是以纯文本保存的。它存储为一条系统消息的分节，位于单轮会话文件的第四行</strong>，详见“一个提示的生命周期”（原书第15页）。<strong>此次采集使用了四个默认工具，没有上下文文件、技能或追加提示词</strong>，所以包含<strong>五节</strong>：



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
      "rules": "<rules>\n- Use bash for file operations like ls, rg, find\n- Use read to examine files instead of cat or sed.\n- You can inspect PI_* environment variables for current model and session details.\n- Use edit for precise changes (edits[].oldText must match exactly)\n...\n- Be concise in your responses\n- Show file paths clearly when working with files\n</rules>",
      "docs": "<docs>\nPi documentation (read only when the user asks about pi itself, its SDK, extensions, themes, skills, or TUI):\n...\n</docs>",
      "cwd": "<cwd>\n<tmp>/project\n</cwd>"
    },
    "timestamp": 1791242201750,
    "toolsAdded": [
      {
        "name": "read",
        "description": "Read the contents of a file. ...",
        "parameters": { ... },
        "constrainedSampling": {
          "type": "json_schema",
          "strict": "prefer"
        }
      },
      ...
    ]
  }
}
```



删节说明：省去了十条规则中的四条、`docs` 的正文，以及四个 `toolsAdded` 声明中的三个（`bash`、`edit`、`write`）。`content` 为空，因为提示词由结构化分节承载，见 `CA/src/core/system-prompt.ts:199`。路径已由采集脚本脱敏。



这条记录中有三点会在后面发挥作用。`content` 为 `""`。工具声明以 `toolsAdded` 的形式与提示词放在同一条消息中，因此提示词和工具集会一起重放。而且，这条记录是会话树中的普通 `message` 条目；并不存在单独的“提示词状态”条目类型，详见“会话：JSONL 树”（原书第86页）。

## 输入从哪里来



`AgentSession._rebuildSystemPrompt()` 从资源加载器和工具注册表收集基础选项，见 `CA/src/core/agent-session.ts:1686`。



|<strong>输入</strong>|<strong>来源</strong>|<strong>参见</strong>|
|---|---|---|
|`customPrompt`<br>|`--system-prompt`；否则，项目受信任时使用 `<cwd>/.pi/SYSTEM.md`；再否则使用 `~/.pi/agent/SYSTEM.md`。见 `CA/src/core/resource-loader.ts:1209`|配置、模型与身份验证（原书第99页）|
|`appendSystemPrompt`|每个 `--append-system-prompt`（可重复）；否则，项目受信任时使用 `.pi/APPEND_SYSTEM.md`；再否则使用 `~/.pi/agent/APPEND_SYSTEM.md`。见 `CA/src/core/resource-loader.ts:1223`|CLI 参考（原书第191页）|
|`contextFiles`|`loadProjectContextFiles()`：智能体目录，然后是从文件系统根目录到 `cwd` 的每一级祖先目录。见 `CA/src/core/resource-loader.ts:232`|上下文文件、技能、模板、主题与包（原书第106页）|
|`skills`|资源加载器的技能|上下文文件、技能、模板、主题与包（原书第106页）|
|`toolSnippets`、`toolGuidelines`|每个已注册工具定义的 `promptSnippet` 和 `promptGuidelines`|内置工具（原书第81页）|
|`forceSystemPrompt`|返回 `systemPrompt` 的 `before_agent_start` 处理器|扩展事件与上下文（原书第120页）|



两个同名文件绝不会合并。对于 `SYSTEM.md` 和 `APPEND_SYSTEM.md`，受信任的项目文件都优先于智能体目录中的文件。依据 `resource-loader.ts`（`discoverSystemPromptFile`、`discoverAppendSystemPromptFile`）。



如果 CLI 参数值指向一个现有文件，就读取该文件的内容，并去掉 BOM；其他任何值都作为字面文本使用，见 `CA/src/core/resource-loader.ts:167`。



`docs/cli.md` 说 `--append-system-prompt` 会“将文本或现有文件追加到系统提示词”，`docs/configuration.md` 说 `APPEND_SYSTEM.md` 会“添加指令”。合起来读，似乎两者都会生效。实际并非如此：只要提供了任何 `--append-system-prompt`，就会跳过 `APPEND_SYSTEM.md` 的发现过程，见 `CA/src/core/resource-loader.ts:659`。如果希望两者都生效，请把该文件也作为其中一个标志的参数传入。

## 提示词变化是对话记录补丁



`_preparePromptAndToolLoadout()` 会在每次 `prompt()` 开始时，以及之后每个轮次之前，通过 `prepareNextTurnWithContext` 运行，见 `CA/src/core/agent-session.ts:1724`、`CA/src/core/agent-session.ts:892`。<strong>它从不重新发送整个提示词，而是重放对话记录中的系统消息，得到模型当前持有的分节，再将它们与新构建的分节比较，并追加差异。</strong>



<ManualFigure id="4.2" />

> <strong>之前的消息绝不会被重写。发生变化的分节作为文本发送，被移除的分节作为 `null` 发送；工具变化放在同一条系统消息中。只有模型接受对话中途的系统消息时，提供商才会在原位置发送后续系统消息，并以 `Updated system prompt section "name"`（已更新系统提示词分节“name”）标示。</strong>依据 `agent-session.ts`（`_preparePromptAndToolLoadout`）、`system-prompt.ts:217`、`agent-loop.ts:333`、`ai/utils/transcript.ts:115`。
> 
> 



补丁：变化的分节为文本，移除的分节为 `null`。来源：`CA/src/core/system-prompt.ts`。

```ts
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

> 完整函数，第217–229行。
> 
> 



重放逻辑只在 `getCurrentSystemMessage()` 中定义一次：依次遍历每条系统消息，拼接非空的 `content`，按名称设置或删除分节，并对每条消息先应用 `toolsRemoved`、再应用 `toolsAdded`，从而解析工具。见 `ai/utils/transcript.ts:73`。提供商接收打过补丁的对话记录。`renderSystemMessageUpdate()` 将每个补丁分节标示为 `Updated system prompt section "name":`（已更新系统提示词分节“name”：）或 `Removed system prompt section "name"`（已移除系统提示词分节“name”）。见 `ai/utils/text.ts:28`。当模型的兼容性标志 `supportsMidConvoSystemMessages` 为 `false`（默认值）时，`collapseSystemMessages()` 会改为把所有系统消息合并成一条置于开头的消息，见 `ai/utils/transcript.ts:108`。



<ManualFigure id="patch-example" />



最后这种情况决定了这项设计能带来什么收益。对于接受对话中途系统消息的模型，安装技能或连接 MCP 服务器会追加一个补丁，提供商已缓存的前缀仍然有效。对于不接受的模型，合并后的头部会改变，从该次请求开始就会丢失缓存前缀。哪些模型带有这个标志，详见“传输 API 与跨提供商交接”（原书第36页）。



> <strong>易踩的坑</strong>
> 
> 返回 `systemPrompt`（或设置 `forceSystemPrompt`）的 `before_agent_start` 处理器不会改变对话记录。结构化分节仍然会进行差异比较并存储；强制文本只投影到请求中，成为一条携带当前工具的头部消息，见 `CA/src/core/agent-session.ts:1773`。这种投影只持续本次运行。之后的运行以及任何读取会话文件的程序，看到的都是结构化提示词。最好修改 `systemPromptOptions` 中的分节、工具或准则，`docs/extensions.md` 也给出了同样的建议。
> 
> 



> 这对你意味着什么
> 
> - 通过重放会话的系统消息来读取提示词，而不是只读第一条。
> 
> - 让扩展以具名分节的形式添加指令；重命名会表现为一次移除加一次新增。
> 
> - 将日期或环境信息放在独立分节中；默认提示词只包含 `cwd`。
> 
> - 在期望提示词变化后仍能命中缓存之前，先检查 `supportsMidConvoSystemMessages`。
> 
> 



> 来源：`CA/src/core/system-prompt.ts`（`normalizeBuildSystemPromptOptions`、`buildRules`、`buildSystemPromptSections`、`buildSystemPromptState`、`diffSystemPromptSections`）；`CA/src/core/skills.ts`（`formatSkillsForPrompt`）；`CA/src/core/agent-session.ts`（`_rebuildSystemPrompt`、`_preparePromptAndToolLoadout`、`_installAgentForcedPromptProjection`、`_installAgentNextTurnRefresh`）；`CA/src/core/resource-loader.ts`（`resolvePromptInput`、`loadProjectContextFiles`、`discoverSystemPromptFile`、`discoverAppendSystemPromptFile`）；`agent/agent-loop.ts`（`declareToolChanges`）；`ai/types.ts`（`SystemMessage`）；`ai/utils/transcript.ts`（`getCurrentSystemMessage`、`collapseSystemMessages`、`resolveTranscript`）；`ai/utils/text.ts`（`renderSystemMessageUpdate`）；`CA/docs/cli.md`；`CA/docs/configuration.md`；`CA/docs/extensions.md`；`research/out/one-turn.txt`（§session\-jsonl）。
> 
>
