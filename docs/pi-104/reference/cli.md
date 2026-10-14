---
title: CLI 参考
---

<div class="section-kicker">R.2 / REFERENCE</div>

# R\.2 CLI 参考

---

四十一个标志与八个子命令，均由一个手写解析器读取；无法识别的长标志不会立即报错，而是先让扩展有机会认领。



下列每个标志均已对照 `parseArgs`（`CA/src/cli/args.ts:72`）及 `main()` 随后执行的检查（`CA/src/main.ts:573`）核实。`pi --help` 会打印同一份列表，并加上已加载扩展注册的所有标志。



```text
pi [options] [--] [@files ...] [messages ...]
pi install|remove|uninstall|update|list|config|auth|mcp …
```



〔排版修复：源文将两行用法粘连，并将第一行的分隔符与省略号抽取成 `[ -] [@files .] [messages .]`；此处依据下文的解析规则恢复。〕



## 解析规则



|参数|含义|参见|
|---|---|---|
|`--`|结束选项解析；后续单词视为消息，若以 `@` 开头则视为文件|运行模式（原书第127页）|
|`@path`|附加到第一条提示词的文件；RPC 模式下不允许使用|运行模式（原书第127页）|
|裸单词|一条消息；第一条与管道输入的 stdin 和 `@file` 文本合并，其余分别作为独立提示词发送|运行模式（原书第127页）|
|`--name=value`|带值的未知长标志，交给扩展处理|扩展、加载与 API（原书第113页）|
|`--name value`|未知长标志；将下一个单词作为其值，除非该单词以 `-` 或 `@` 开头|扩展、加载与 API（原书第113页）|
|`--name`|值为 `true` 的未知长标志|扩展、加载与 API（原书第113页）|
|`-x`|未知短标志：报 `Unknown option: -x`，以退出码 `1` 退出|—|



未知长标志可以通过解析阶段；未知短标志则不行。若没有已加载扩展注册某个长标志，后续会以 `Unknown option: --name` 报错（`CA/src/core/agent-session-services.ts:120`）。来源：`CA/src/cli/args.ts:241–261`。



需要取值的标志若出现在命令行的最末尾，就没有可读取的值。它会落入未知标志分支，因此 `pi --model` 最终得到的是 `Unknown option: --model`，而不是缺少值的提示（`CA/src/cli/args.ts:117`）。



## 模式与输出



|标志|短形式|参数|作用|参见|
|---|---|---|---|---|
|`--print`|`-p`|`[message]`|单次运行；将下一个单词作为消息，除非以 `@` 或 `-` 开头（允许 `---`）|运行模式（原书第127页）|
|`--mode`||`text \| json \| rpc`|输出协议；仅设置 `text` 不会退出 TUI|运行模式（原书第127页）|
|`--tui-mode`||`fullscreen \| regular`|本次运行的交互布局|pi\-tui（原书第158页）|
|`--verbose`|||详细启动输出，覆盖 `quietStartup`|设置参考（原书第202页）|
|`--offline`|||设置 `PI_OFFLINE=1` 和 `PI_SKIP_VERSION_CHECK=1`|环境变量（原书第185页）|
|`--export`||`[out.html]`|写入 HTML 后退出；第一条消息作为输出路径|会话与 JSONL 树（原书第86页）|
|`--list-models`||`[search]`|列出模型后退出；将下一个单词作为模糊过滤条件，除非以 `-` 或 `@` 开头|提供商与模型（原书第24页）|
|`--help`|`-h`||显示帮助（包括扩展标志），然后退出|扩展、加载与 API（原书第113页）|
|`--version`|`-v`||打印版本并退出|—|



当流被重定向时，无须任何标志即可进入打印模式。stdin 或 stdout 只要有一个不是 TTY，就会选择打印模式（`CA/src/main.ts:119`）。`--offline` 在解析前通过 `args.includes` 检测（`CA/src/main.ts:576`），因此即使出现在 `--` 之后也会生效。



## 会话



|标志|短形式|参数|作用|参见|
|---|---|---|---|---|
|`--continue`|`-c`||当前工作目录最近的会话|会话与 JSONL 树（原书第86页）|
|`--resume`|`-r`||交互式会话选择器|会话与 JSONL 树（原书第86页）|
|`--session`|||打开文件，或打开 id 以该参数开头的第一个会话|会话与 JSONL 树（原书第86页）|
|`--session-id`|||打开项目中 id 与之完全一致的会话，或用该 id 创建会话|会话与 JSONL 树（原书第86页）|
|`--fork`|||将某个会话复制为当前工作目录中的新会话|会话与 JSONL 树（原书第86页）|
|`--session-dir`|||会话存储位置；优先于 `PI_CODING_AGENT_SESSION_DIR` 与 `sessionDir` 设置|环境变量（原书第185页）|
|`--no-session`|||内存会话，不写入任何内容|会话与 JSONL 树（原书第86页）|
|`--name`|`-n`||会话显示名称；空值会报错|会话与 JSONL 树（原书第86页）|



只有一个分支会生效，优先顺序为：`--no-session`、`--fork`、`--session`、`--resume`、`--continue`、`--session-id`，最后是新建会话（`CA/src/main.ts:358`）。参数若含 `/` 或 `\`，或者以 `.jsonl` 结尾，就被视为路径；其他参数先作为 id 在当前项目中匹配，再在所有项目中匹配（`CA/src/main.ts:252`）。若 `--session` 匹配到其他项目中的会话，会询问 `Fork this session into current directory? [y/N]`（是否将此会话分叉到当前目录？）。



## 模型



|标志|短形式|参数|作用|参见|
|---|---|---|---|---|
|`--model`|||模型 id 或模式；接受 `provider/id` 和 `:suffix`|提供商与模型（原书第24页）|
|`--provider`|||缩小 `--model` 的范围；单独使用会报错|提供商与模型（原书第24页）|
|`--models`|||用于 `Ctrl+P` 循环切换的模式；允许 glob 和 `:`|配置、模型与身份验证（原书第99页）|
|`--thinking`||`off\|minimal\|low\|medium\|high\|xhigh\|max`|思考级别；优先于 `:` 后缀；无效值会触发警告|身份验证、费用、重试与目录（原书第41页）|
|`--api-key`|||所选模型提供商的仅运行时密钥；绝不存储|身份验证、费用、重试与目录（原书第41页）|



`--api-key` 需要指定模型，但使用 `--models` 即可满足这一要求。错误文本为 `--api-key requires a model to be specified via --model, --provider/--model, or --models`（`CA/src/main.ts:832`）；密钥通过 `setRuntimeApiKey` 设置（`CA/src/main.ts:835`）。



## 提示词与工具



|标志|短形式|参数|作用|参见|
|---|---|---|---|---|
|`--system-prompt`|||替换基础系统提示词；若是存在的路径，则按文件读取|系统提示词的构造（原书第75页）|
|`--append-system-prompt`|||追加在基础提示词后；可重复使用|系统提示词的构造（原书第75页）|
|`--tools`|`-t`||名称或 `*` 模式的允许列表；MCP 工具仍保留，除非某个条目以 `mcp__` 开头|内置工具（原书第81页）|
|`--exclude-tools`|`-xt`||拒绝列表，在 `--tools` 之后应用，也包含 MCP 工具|内置工具（原书第81页）|
|`--no-tools`|`-nt`||默认不启用任何工具，无论内置工具还是扩展工具|内置工具（原书第81页）|
|`--no-builtin-tools`|`-nbt`||默认不启用内置工具；扩展工具保留|内置工具（原书第81页）|



两个提示词标志都接受文件路径。若 `existsSync` 为真，`resolvePromptInput` 会将参数作为文件读取，否则作为文本使用（`CA/src/core/resource-loader.ts:167`）。`pi --help` 对 `--system-prompt` 只写了 `<text>`。



## 资源与信任



|标志|短形式|参数|作用|参见|
|---|---|---|---|---|
|`--extension`|`-e`||文件、目录、`builtin:` 或包来源（`npm:`、`git:`）；可重复使用|扩展、加载与 API（原书第113页）|
|`--no-extensions`|`-ne`||不加载发现的、已配置的或内置的扩展；显式指定的 `-e` 仍会加载|扩展、加载与 API（原书第113页）|
|`--no-mcp`|||仅禁用内置 MCP 扩展|MCP（原书第144页）|
|`--skill`|||额外的技能文件或目录；可重复使用|上下文文件、技能、模板、主题与包（原书第106页）|
|`--no-skills`|`-ns`||不发现技能；显式指定的 `--skill` 仍会加载|上下文文件、技能、模板、主题与包（原书第106页）|
|`--prompt-template`||`<path>`|额外的提示词模板；可重复使用|上下文文件、技能、模板、主题与包（原书第106页）|
|`--no-prompt-templates`|`-np`||不发现提示词模板|上下文文件、技能、模板、主题与包（原书第106页）|
|`--theme`||`<path>`|额外的主题文件或目录；可重复使用|pi\-tui（原书第158页）|
|`--no-themes`|||不发现主题|pi\-tui（原书第158页）|
|`--use-theme`||`<name [/name]>`|本次交互运行的初始主题|pi\-tui（原书第158页）|
|`--no-context-files`|`-nc`||不加载 `AGENTS.md` / `CLAUDE.md`|系统提示词的构造（原书第75页）|
|`--approve`|`-a`||本次运行信任项目本地文件|安全模型（原书第174页）|
|`--no-approve`|`-na`||本次运行忽略项目本地文件|安全模型（原书第174页）|



〔排版说明：源文的 `--skill` 与 `--no-skills` 两行粘连，此处已拆分。以上多个表格的“参数”单元格在源文中为空，即使作用说明明确需要参数也未补写；`<name [/name]>` 的原始格式亦保留。〕



`--no-mcp` 对应 `disabledBuiltinExtensions: ["mcp"]`。它仍会加载 `codemode`、`tool-search` 和 `lama.cpp`（`CA/src/main.ts:785`）。传给 `-e`、`--skill`、`--prompt-template` 和 `--theme` 的路径，会在任何会话切换之前，相对于启动时的当前工作目录解析（`CA/src/main.ts:726`）。



## 启动错误



|条件|消息（stderr）|退出码|
|---|---|---|
|`--fork` 与 `--session`、`-c`、`-r` 或 `--no-session` 同时使用|`Error: --fork cannot be combined with ...`|`1`|
|`--session-id` 与 `--session`、`-c` 或 `-r` 同时使用|`Error: --session-id cannot be combined with ...`|`1`|
|`--fork` 搭配一个已存在的 `--session-id`|`Session already exists with id ''`|`1`|
|没有会话匹配 `--session` 或 `--fork`|`No session found matching ''`|`1`|
|`--mode` 缺少值或值无效|`--mode requires text, json, or rpc` / `Invalid mode "..."`|`1`|
|使用 `--provider` 但未使用 `--model`|`--provider requires --model (for example: ...)`|`1`|
|`@file` 与 `--mode rpc` 同时使用|`Error: @file arguments are not supported in RPC mode`|`1`|
|任意扩展加载失败|`Failed to load extension "..."`，并提示 `pi -ne`|`1`|
|非交互模式，未指定模型|无可用模型时的指引|`1`|



〔源文说明：上表两条消息中的空引号 `''` 疑为参数占位内容在抽取时丢失；此处保留原样。错误消息保留程序输出的英文，以便准确检索和对照。〕



所有启动错误均以退出码 `1` 退出；拒绝分叉提示则以 `0` 退出。来源：`CA/src/main.ts`（`validateForkFlags`、`validateSessionIdFlags`、`createSessionManager`、`buildSessionOptions`、`main`）和 `CA/src/cli/args.ts`。



><strong>易踩的坑</strong>
>
> 布尔型扩展标志会吞掉下一个单词。解析器不知道哪些未知标志是布尔型，因此 `pi --plan "refactor auth"` 会把 `"refactor auth"` 存为 `--plan` 的值（`CA/src/cli/args.ts:250`）。如果扩展将 `--plan` 注册为布尔型，该值会被丢弃，消息也就消失了（`CA/src/core/agent-session-services.ts:106`）。请将布尔型扩展标志放在消息之后，或写成 `--plan=true`。



## 子命令



子命令在标志解析之前，根据第一个单词匹配，顺序是 `auth`、包命令、`config`、`mcp`（`CA/src/main.ts:582`）。



|命令|选项|作用|参见|
|---|---|---|---|
|`pi install`|`-l`、`-a`、`-na`|安装包并将其加入设置；`-l` 写入项目设置|上下文文件、技能、模板、主题与包（原书第106页）|
|`pi remove`|`-l`、`-a`、`-na`|移除包；`uninstall` 是别名|上下文文件、技能、模板、主题与包（原书第106页）|
|`pi update [source\|self\|pi]`|`--self`、`--extensions`、`--models`、`--all`、`--extension`、`--force`、`-a`、`-na`|无目标时：只更新 Pi；`--all`：更新 Pi 与包；`--models`：刷新目录|上下文文件、技能、模板、主题与包（原书第106页）|
|`pi list`|`-a`、`-na`|列出用户设置与项目设置中的已安装包|上下文文件、技能、模板、主题与包（原书第106页）|
|`pi config`|`-l`、`-a`、`-na`|用于启用或禁用包资源的 TUI；`Tab` 切换作用域|配置、模型与身份验证（原书第99页）|
|`pi auth print-api-key`|`--provider`、`--model`|打印密钥|身份验证、费用、重试与目录（原书第41页）|
|`pi auth print-bearer-token`|`--provider`、`--model`、`--min-expiry (ms\|s\|m\|h)`|打印 OAuth 令牌，必要时刷新|身份验证、费用、重试与目录（原书第41页）|
|`pi auth check`|`--provider`、`--model`、`--json`、`--credentials`、`--no-refresh`|就绪状态：退出码 `0` 表示就绪，`1` 表示未就绪，`2` 表示无效|身份验证、费用、重试与目录（原书第41页）|
|`pi mcp add`|`-l`、`--url`、`--env`、`--cwd`、`--header`、`--bearer-token-env-var`、`--oauth-*`、`--exposure`、`--description`、`--`|在 `mcp.json` 中添加或替换服务器|MCP（原书第144页）|
|`pi mcp remove`|`-l`|移除服务器|MCP（原书第144页）|
|`pi mcp list`|`--json`|状态、工具与错误；失败时以退出码 `1` 退出|MCP（原书第144页）|
|`pi mcp login`|`--timeout`（默认 `300`）|浏览器 OAuth 登录|MCP（原书第144页）|
|`pi mcp logout`||删除已存储的 OAuth 凭证|MCP（原书第144页）|



身份验证命令需要 `--provider` 或 `--model`。消息、`@files`、`--api-key` 和未知标志都会被拒绝（`CA/src/cli/auth-command.ts:98`）。`--json`、`--credentials` 和 `--no-refresh` 仅用于 `check`；`--min-expiry` 仅用于 `print-bearer-token`（`CA/src/cli/auth-command.ts:72`）。用法字符串来自 `CA/src/package-manager-cli.ts:265`、`CA/src/cli/auth-command.ts:18` 和 `CA/src/extensions/mcp/cli.ts:33`。



来源：`CA/src/cli/args.ts`（`parseArgs`、`printHelp`）。`CA/src/main.ts`（`main`、`runAuthCommand`、`resolveSessionPath`、`validateForkFlags`、`validateSessionIdFlags`、`createSessionManager`、`buildSessionOptions`、`createRuntime`）。`CA/src/core/agent-session-services.ts`（`applyExtensionFlagValues`）；`CA/src/core/resource-loader.ts`（`resolvePromptInput`）。`CA/src/package-manager-cli.ts`（`getPackageCommandUsage`、`parsePackageCommand`、`handleConfigCommand`）；`CA/src/cli/auth-command.ts`；`CA/src/extensions/mcp/cli.ts`（`HELP`、`runMcpCommand`）。`CA/docs/cli.md`。
