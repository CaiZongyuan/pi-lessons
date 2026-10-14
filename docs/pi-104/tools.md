---
title: 内置工具
---

<div class="section-kicker">4.2 / THE CODING AGENT</div>

# 内置工具

---

<strong>Pi 自带八个工具，默认启用四个。它们都遵循同一个输出约定：2,000 行或 50 KB，因此单个工具结果绝不会填满上下文窗口；`edit` 工具则会拒绝任何无法唯一定位的修改。</strong>



<strong>内置工具是默认智能体接触机器的唯一途径。</strong>本节列出这八个工具及其选择方式，然后说明它们共同遵循的截断约定，以及各工具的参数和行为。接着结合采集工具包中的真实错误消息，讲解 `edit` 算法。最后介绍包裹每次调用的钩子流水线，其中也包括一个工具代表另一个工具发起的调用。

## 八个工具，默认启用四个



`ToolName` 为 `"read" | "bash" | "powershell" | "edit" | "write" | "grep" | "find" | "ls"`，见 `CA/src/core/tools/index.ts:95`。`DEFAULT_TOOL_NAMES` 为 `["read", "bash", "edit", "write"]`，见 `CA/src/core/settings-manager.ts:215`。`createReadOnlyTools()` 返回 `read`、`grep`、`find` 和 `ls`，见 `CA/src/core/tools/index.ts:204`。



工具选择分三层进行。`defaultTools` 设置可以用普通名称替换默认列表，也可以按列表顺序应用 `+name` 和 `-name` 修饰符来修改它，见 `CA/src/core/settings-manager.ts:236`。在命令行中，`--tools` 是允许列表，`--exclude-tools` 是拒绝列表；两者都接受 `*` 模式，`--no-tools` 和 `--no-builtin-tools` 则会关闭整组工具，见 `CA/src/cli/args.ts:151`。完整标志列表详见“CLI 参考”（原书第191页）。



每个工具都是一个 `ToolDefinition`，由 `wrapToolDefinition()` 转成 `AgentTool`；该函数复制名称、模式、`prepareArguments` 和 `constrainedSampling`，并向 `execute` 传入每次调用专属的上下文，见 `CA/src/core/tools/tool-definition-wrapper.ts:8`。路径相对于会话的 `cwd` 解析，展开 `~` 并移除开头的 `@`，见 `CA/src/core/tools/path-utils.ts:48`。

## 截断约定



每个返回文件或进程输出的工具，都会将输出交给 `truncate.ts` 处理。存在两个限制，先触及哪个就按哪个截断：



所有内置工具共用的三个限制。来源：`CA/src/core/tools/truncate.ts`。

```ts
export const DEFAULT_MAX_LINES = 2000;
export const DEFAULT_MAX_BYTES = 50 * 1024; // 50KB
export const GREP_MAX_LINE_LENGTH = 500; // Max chars per grep match line
```

> 第11–13行，原样引用。
> 
> 



|<strong>函数</strong>|<strong>保留内容</strong>|<strong>使用方</strong>|
|---|---|---|
|`truncateHead`|开头；绝不拆分一行；如果仅第1行就超过字节限制，不返回任何内容，并设置 `firstLineExceedsLimit`|`read`、`grep`、`find`、`ls`|
|`truncateTail`|末尾；如果仅最后一行就超过字节限制，保留其末尾，并设置 `lastLinePartial`|`bash`、`powershell`（通过 `OutputAccumulator`）、用户的 `!` 命令|
|`truncateLine(line, 500)`|前500个字符，然后附上 `... [truncated]`|`grep` 的匹配行|
|`truncateMiddle(text, maxBytes)`|两端各占一半预算，中间放置 `...N chars truncated...`|MCP 工具结果，限制为 20 KiB，见 `CA/src/extensions/mcp/tools.ts:51`|



文件保留头部，进程保留尾部。读取文件从顶部开始；失败命令最后才输出错误。依据 `truncate.ts` 及 `CA/src` 中各函数的调用位置。



截断从来不会悄无声息。每个工具都会追加一条提示，告诉模型如何获取剩余内容。采集工具包用真实的 `read` 工具读取了一个2,500行的文件：

```text
read long.txt (2,500 lines) → ...line 1999\nline 2000\n\n[Showing lines 1-2000 of 2500. Use offset=2001 to continue.]
read offset=10 limit=3 → line 10\nline 11\nline 12\n\n[2488 more lines in file. Use offset=13 to continue.]
read offset=9999 × Offset 9999 is beyond end of file (2500 lines total)
```

## 工具参考



|<strong>工具</strong>|<strong>参数</strong>|<strong>行为</strong>|
|---|---|---|
|`read`|`path`、`offset?`（从1开始）、`limit?`|先应用 `limit`，再应用 `truncateHead`。第一行超过 50 KB 时，不返回文本，而是给出 `sed -n '...p' ... \| head -c 51200` 提示。图片（jpg、png、gif、webp、bmp，根据文件内容检测）以图片块返回，并根据模型的输入限制缩放；如果模型不接受图片输入，则添加说明。会尝试 macOS 文件名变体：AM/PM 之前的窄不换行空格、NFD、弯撇号。见 `CA/src/core/tools/path-utils.ts:86`。|
|`bash`|`command`、`timeout?`（秒；无默认值；最多2,147,483\.647）|启动配置的 shell，分离到独立进程组，并合并 stdout 和 stderr。中止或超时会终止进程树。保留输出末尾；完整输出写入提示中指定的临时文件 `pi-bash-*.log`。更新节流为每100 ms最多一次。非零退出会返回 `isError`，并附上 `Command exited with code N`（命令以代码 N 退出）。|
|`powershell`|与 `bash` 相同|使用相同定义，但采用 PowerShell 配置、UTF\-8 控制台前缀和临时文件前缀 `pi-powershell`，见 `CA/src/core/tools/powershell.ts:16`。|
|`edit`|`path`、`edits: [{oldText,newText}]`|一次调用中执行多处互不重叠的替换（算法见下文）。`prepareArguments` 也接受 JSON 字符串或单个对象形式的 `edits`，以及旧式顶层 `oldText`/`newText`，见 `CA/src/core/tools/edit.ts:103`。|
|`write`|`path`、`content`|在按文件划分的修改队列内创建父目录，以 UTF\-8 写入。返回 `Successfully wrote to path`（已成功写入 path）。|
|`grep`|`pattern`、`path?`、`glob?`、`ignoreCase?`、`literal?`、`context?`、`limit? = 100`|运行 `rg --json --line-number --color=never --hidden`；如果缺少 ripgrep，会进行下载。遵循 `.gitignore`。每行截断至500个字符；输出上限为 50 KB。|
|`find`|`pattern`（glob）、`path?`、`limit? = 1000`|运行 `fd --glob --color=never --hidden --max-results N`；返回相对于搜索目录的路径，以 `/` 作为分隔符。|
|`ls`|`path?`、`limit? = 500`|读取目录，按不区分大小写的顺序排序，为目录追加 `/`，包括点文件。|



只有四种工具请求严格的模式解码。`read`、`bash`（因而也包括 `powershell`）、`edit` 和 `write` 设置 `constrainedSampling: {type: "json_schema", strict: "prefer"}`；`grep`、`find` 和 `ls` 不设置。依据 `CA/src/core/tools/*.ts`。



`bash` 有两种输出。模型看到的是经过截断的尾部。以程序方式调用它的调用方，例如 codemode 脚本（“codemode”，原书第151页），得到的是 `structuredContent`，即 `{output, truncated, full_output_path?, exit_code, wall_time_seconds}`，其中 `output` 的上限改为 1 MiB，见 `CA/src/core/tools/bash.ts:24`。除非 `exposeSessionEnvironment` 为 `false`，否则子进程的环境会包含 `PI_SESSION_ID`、`PI_SESSION_FILE`、`PI_PROVIDER`、`PI_MODEL` 和 `PI_REASONING_LEVEL`，而这五个变量继承而来的值会先被移除，见 `CA/src/core/tools/bash.ts:186`。

## edit 算法



`edit` 的所有替换都针对原始文件，绝不针对同一次调用中先前替换的结果。它在 `withFileMutationQueue()` 内运行，以文件的真实路径为键：对同一文件的两次编辑依次执行，对不同文件的编辑则并行执行，见 `CA/src/core/tools/file-mutation-queue.ts:32`。



<ManualFigure id="4.3" />

> 五种拒绝路径，一种写入路径。第一个失败的检查会决定结果，文件不会被触碰。依据 `edit.ts`（`execute`）和 `edit-dif.ts`（`applyEditsToNormalizedContent`、`normalizeForFuzzyMatch`、`applyReplacementsPreservingUnchangedLines`）。本图为示意图。
> 
> 



采集工具包先对一个带有 BOM、CRLF 行尾和重复行的文件运行真实工具，随后又对一个包含弯引号和行尾空格的文件运行：

```text
file: "\uFEFFconst a = 1;\r\nconst b = 2;\r\nconst b = 2;\r\n"
edit oldText absent    x Could not find the exact text in src.ts. The old text must match exactly including all whitespace and newlines.
edit oldText twice    x Found 2 occurrences of the text in src.ts. The text must be unique. Please provide more context to make it unique.
edit two overlapping edits    x edits[1] and edits[0] overlap in src.ts. Merge them into one edit or target disjoint regions.
edit identical replacement    x No changes made to src.ts. The replacement produced identical content. This might indicate an issue with special characters or the text not existing as expected.
edit LF oldText on CRLF file → Successfully replaced 1 block(s) in src.ts.
file after: "\uFEFFconst a = 10;\r\nconst b = 2;\r\nconst b = 2;\r\n"

file: "say("hello"); \nkeep('this');\n"
edit with ASCII quotes (fuzzy) → Successfully replaced 1 block(s) in src.ts.
file after: "say(\"bye");\nkeep('this');\n"
```

> 译注：原文说明称此例含有弯引号，但提取出的示例文字显示为直引号，且字符串的引号转义不一致。上例保留所提供的采集文字，未补造实际字符；因此请结合本段说明理解模糊匹配行为。
> 
> 



最后一组示例显示了模糊匹配路径的限制。模型写入 ASCII 引号，因此匹配回退到了规范化文本。被修改的那一行以规范化形式返回：行尾空格消失了。未触碰的行保留了弯引号。在一次多处编辑调用中，只要一处编辑使用模糊匹配，所有编辑都会切换到规范化匹配；任何编辑触及的每一行都会以规范化形式写入。



重叠错误消息按排序后的位置命名编辑，因此 `edits[1]` 和 `edits[0]` 并非笔误。更重要的是，即使精确匹配成功，也会在模糊匹配空间中统计唯一性，见 `CA/src/core/tools/edit-diff.ts:328`。两行如果仅引号样式或行尾空白不同，仍会被算作两次出现，因此编辑会被拒绝。请在 `oldText` 中加入相邻的一行。

## 每次调用外的钩子层



每个工具调用，无论是否为内置工具，都会经过 `agent-loop.ts` 中的同一条流水线，见 `agent/agent-loop.ts:707`。`AgentSession` 安装了两个将其连接到扩展的钩子，见 `CA/src/core/agent-session.ts:640`。



<ManualFigure id="4.4" />

> 扩展看到的是已验证的参数，而且可以更改它们。`tool_call` 处理器接收到的对象与 `execute` 接收的是同一个对象，所以修改 `event.input` 就会改变调用；阻止调用的结果会转换为错误结果，并附上处理器提供的原因。`tool_result` 处理器可以替换 `content`、`details` 和 `isError`；之后才会调整图片大小。依据 `agent-loop.ts`（`prepareToolCall`、`finalizeExecutedToolCall`）和 `agent-session.ts`（`_beforeToolCall`、`_afterToolCall`）。
> 
> 



未知工具名、验证失败、阻止调用以及抛出的错误，都会作为带有 `isError: true` 的工具结果返回；它们都不会把异常抛到循环之外，见 `agent/agent-loop.ts:807`。事件名称和结果结构详见“扩展事件与上下文”（原书第120页）。



同一条流水线也用于嵌套调用，即工具调用 `ctx.executeTool()` 的情况，codemode 脚本就是这样做的。嵌套调用的 ID 为 `<parent id>/<n>`，从1开始计数；其 `tool_execution_*` 事件和钩子事件都携带 `parentToolCallId`，见 `CA/src/core/nested-tool-calls.ts:188`。父调用的工具结果会在 `NESTED_CALL_LIMITS` 限制内记录嵌套调用：最多256次调用，每次调用的参数最多 8 KiB，参数总量最多 32 KiB，每条错误最多500个字符。超出限制的参数会被省略，第256次之后的调用会被丢弃，记录会标为不完整，见 `CA/src/core/nested-tool-calls.ts:26`。



> 这对你意味着什么：
> 
> - 告诉模型用 `offset` 分页；提示本来就会这样建议，因此不要为了避免分页而提高限制。
> 
> - 脚本需要读取命令最后2,000行之外的内容时，读取 `structuredContent.output`。
> 
> - 要预料到 `edit` 会拒绝有歧义的文本；扩大 `oldText` 的范围，而不是原样重试同一个调用。
> 
> - 将权限检查放在 `tool_call` 中：这样它们也会适用于嵌套调用。
> 
> 



> 来源：`CA/src/core/tools/index.ts`（`ToolName`、`createReadOnlyTools`）；`CA/src/core/settings-manager.ts`（`DEFAULT_TOOL_NAMES`、`resolveDefaultTools`）；`CA/src/cli/args.ts`（`-tools`、`-exclude-tools`）；`CA/src/core/tools/tool-definition-wrapper.ts`；`CA/src/core/tools/path-utils.ts`；`CA/src/core/tools/truncate.ts`；`CA/src/core/tools/{read,bash,powershell,edit,editdiff,write,grep,find,ls,file-mutation-queue}.ts`；`CA/src/core/tools/renderers/bash.ts`（`BASH_UPDATE_THROTTLE_MS`）；`CA/src/extensions/mcp/tools.ts`（`MCP_OUTPUT_MAX_BYTES`）；`agent/agent-loop.ts`（`prepareToolCall`、`runToolCall`、`finalizeExecutedToolCall`）；`CA/src/core/agent-session.ts`（`_beforeToolCall`、`_afterToolCall`、`_executeNestedToolCall`）；`CA/src/core/nested-tool-calls.ts`（`NESTED_CALL_LIMITS`）；`research/capture/built-in-tools-edit.mjs`；`research/out/built-intools-edit.txt`。
> 
>
