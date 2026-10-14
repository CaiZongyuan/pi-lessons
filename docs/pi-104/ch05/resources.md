---
title: 上下文文件、技能、模板、主题与包
---

<div class="section-kicker">5.2 / CONFIGURATION & EXTENSIONS</div>

# 上下文文件、技能、模板、主题与包

---

Pi 加载的每一种资源都经过同一个函数：`DefaultResourceLoader.reload()`。它确定信任状态，从五类来源收集路径，并让同名资源的第一个副本胜出，因此收集顺序决定了一切。



项目可以提供自己的技能、提示词模板、主题和扩展，用户、包和命令行也一样。如果两个资源使用相同的名称，其中一个就会被静默丢弃。本节沿着 `reload()`，从信任决定一直讲到最后一个主题，给出解决冲突的优先级排名，并用一次采集实验将同名技能放到七个位置进行验证。随后介绍每类资源，以及分发这些资源的包管理器。

## 上下文文件



上下文文件是指 `AGENTS.md` 和 `CLAUDE.md`，其中的文本作为项目上下文进入系统提示词，见“系统提示词的构建”（原书第75页）。在每个目录中，Pi 从 `AGENTS.override.md`、`AGENTS.md`、`AGENTS.MD`、`CLAUDE.md` 和 `CLAUDE.MD` 中选取第一个存在的文件，见 `CA/src/core/resource-loader.ts:185`。每个目录只读取一个文件。



`loadProjectContextFiles()` 首先读取智能体目录，然后从工作目录向上遍历到文件系统根目录，并按根目录优先的顺序输出祖先目录，跳过已见过的路径，见 `CA/src/core/resource-loader.ts:232`。如果 git 链接工作树嵌套在主仓库内部，就会跳过主仓库中同一文件的副本，因为两者覆盖的是同一个逻辑仓库，见 `CA/src/core/resource-loader.ts:214`。`--no-context-files`（`-nc`）会关闭加载。



> <strong>易踩的坑</strong>
> 
> 上下文文件不要求信任。`loadProjectContextFiles()` 的遍历过程没有信任检查，因此刚克隆、不受信任的仓库及其每一级上层目录中的 `AGENTS.md` 都会传递给模型。信任控制的是 `.pi/` 和 `.agents/skills`，不是上下文文件。如果不希望检出目录中的文本传递给模型，请使用 `-nc`。
> 
> 

## 加载流水线



`reload()` 会在启动时以及执行 `/reload` 时运行，见 `CA/src/core/resource-loader.ts:509`。首先确定信任状态，因为它决定配置中的项目部分是否存在。







<BookFigure id="5.5" />

> 在读取任何项目本地内容之前，先决定信任状态。步骤按源码顺序排列，见 `resource-loader.ts:509–674`。在信任前加载阶段载入的扩展会在步骤 5 中复用，不会导入两次，见 `CA/src/core/resource-loader.ts:747`。
> 
> 

### 信任决定



信任前加载阶段强制将项目设为不受信任，只加载用户作用域和命令行扩展；内置扩展要等到最后一个阶段才加载，因为已加载的扩展无法卸载，见 `CA/src/core/resource-loader.ts:501`。这些扩展可以响应 `project_trust` 事件。然后，`resolveProjectTrusted()` 沿着第一个匹配项胜出的优先级链进行判断，见 `CA/src/core/project-trust.ts:46`：



<BookFigure id="5.6" />

返回“未决定”的处理器会把问题传给优先级链的下一环。第一个匹配项胜出。处理器顺序就是扩展加载顺序，见 `CA/src/core/extensions/runner.ts:295`。步骤 4 使用 `findNearestTrustEntry()`，因此信任一个父文件夹就会覆盖它下面的所有文件夹，见 `CA/src/core/trust-manager.ts:45`。

> 提示内容为：“信任项目文件夹？……这将允许 pi 加载 `.pi` 设置和资源、安装缺失的项目包，以及执行项目扩展。”见 `CA/src/core/project-trust.ts:24`。选择“仅此会话”选项不会向 `trust.json` 写入任何内容。
> 
> 



> <strong>易踩的坑</strong>
> 
> `.agents/skills` 处理流程的两个部分，对于向上查找多远存在分歧。`hasTrustRequiringProjectResources()` 会检查一直到文件系统根目录的所有祖先目录，见 `CA/src/core/trust-manager.ts:196`。技能发现则止于 git 根目录，见 `CA/src/core/package-manager.ts:468`。仓库根目录上方的 `.agents/skills` 目录会让 Pi 请求信任，但你授予信任之后，其中的技能一个也不会加载。
> 
> 

### 冲突：优先级排名



`packageManager.resolve()` 将资源收集到每类资源各自的映射中，然后按 `resourcePrecedenceRank()` 排序，见 `CA/src/core/package-manager.ts:192`。排名数字越小越靠前，同名资源的第一个副本胜出。



|<strong>排名</strong>|<strong>来源</strong>|<strong>示例</strong>|
|---|---|---|
|0|项目设置条目|`.pi/settings.json` 中的 `skills: ["/tools/skills"]`|
|1|项目中自动发现的资源|`.pi/skills/`，然后是从 cwd 向上直到 git 根目录的 `.agents/skills/`|
|2|用户设置条目|`~/.pi/agent/settings.json` 中的 `skills`|
|3|用户范围内自动发现的资源|`~/.pi/agent/skills/`，然后是 `~/.agents/skills/`|
|4|包资源|包提供的任何资源，项目包先于用户包|
|5|内置资源|`builtin:mcp`、`builtin:codemode`、……（仅扩展）|



设置条目的优先级高于同一作用域中的约定目录。来源：`resourcePrecedenceRank()` 以及 `addAutoDiscoveredResources()` 的插入顺序，见 `CA/src/core/package-manager.ts:2413`。JavaScript 的排序是稳定排序，因此排名相同时保留插入顺序。



排名并不是完整的顺序。`reload()` 会将命令行路径放在排序列表的前面或后面，而且不同种类资源的位置不同，见 `CA/src/core/resource-loader.ts:573`。通过 `-e` 指定的扩展最先加载。通过 `-e` 指定的包所包含的技能、提示词和主题也最先加载，但单独指定的 `--skill`、`--prompt-template` 和 `--theme` 路径会追加到最后。采集工具包在每个作用域中都放置了一个名为 `dup` 的技能、一个 `/dup` 模板和一个 `dup_tool` 工具，再询问加载器哪个胜出：



在每个作用域中使用同一名称，`research/capture/resources-precedence.mjs`

```ts
const loader = new DefaultResourceLoader({
    cwd, agentDir, settingsManager,
    additionalSkillPaths: [path.join(root, "cli-skill")],
    additionalPromptTemplatePaths: [path.join(root, "cli-prompt")],
    additionalExtensionPaths: [path.join(root, "cli-ext.js")],
});
await loader.reload();
```



这里只保留调用部分；脚本首先在临时 `HOME` 下写入七个 `dup` 技能、三个 `/dup` 模板，以及三个分别注册 `dup_tool` 的扩展。针对固定版本的 `dist/` 构建离线运行。

```bash
### §skills（名为 "dup" 的技能出现在七个位置；加载顺序中的第一个胜出）
胜出：项目 settings.skills
落选：项目 .pi/skills（自动发现）
落选：项目 .agents/skills（自动发现）
落选：用户 settings.skills
落选：用户 ~/.pi/agent/skills（自动发现）
落选：用户 ~/.agents/skills（自动发现）
落选：CLI --skill

### $prompts（/dup 出现在三个位置）
胜出：项目 .pi/prompts（自动发现）
落选：用户 ~/.pi/agent/prompts（自动发现）
落选：CLI --prompt-template

### $extensions（加载顺序；每个扩展都注册工具 "dup_tool"）
已加载：CLI -e
已加载：项目 .pi/extensions（自动发现）
已加载：用户 ~/.pi/agent/extensions（自动发现）
错误：项目 .pi/extensions（自动发现）：工具 "dup_tool" 与 CLI -e 冲突
错误：用户 ~/.pi/agent/extensions（自动发现）：工具 "dup_tool" 与 CLI -e 冲突
```



> <strong>易踩的坑</strong>
> 
> `--skill` 和 `--prompt-template` 无法覆盖任何资源。它们被追加在所有发现路径和配置路径之后，见 `CA/src/core/resource-loader.ts:597`，所以通过命令行传入的技能会输给磁盘上任何同名技能，唯一的提示只有冲突诊断。`-e` 则相反：它指定的内容最先加载，包括包中的技能和模板。要测试一个替代技能，可以重命名它，或者把一个包含 `skills/` 文件夹的目录作为本地包传给 `-e`。最后一个代码块中的重复工具是另一回事：在 CLI 中，它会阻止启动，见“扩展：加载与 API”（原书第113页）。
> 
> 

## 技能



技能是一个包含 Agent Skills 格式 `SKILL.md` 的目录，或一个带有 frontmatter 的独立 Markdown 文件。“系统提示词的构建”（原书第75页）展示了技能在提示词中的位置。加载器读取三个 frontmatter 字段，见 `CA/src/core/skills.ts:67`：

- `name`：可选；默认为父目录名称。按规范进行检查：最多 64 个字符，符合 `^[a-z0-9-]+$`，不能以连字符开头或结尾，也不能出现连续两个连字符，见 `CA/src/core/skills.ts:92`。违反规则只会产生警告，技能仍会加载。

- `description`：必需。缺少此字段的 `SKILL.md` 会被报告并跳过；缺少此字段的独立 `.md` 文件会被静默跳过，见 `CA/src/core/skills.ts:304`。超过 1,024 个字符会产生警告。

- `disable-model-invocation: true`：在系统提示词中隐藏该技能；只能通过 `/skill:name` 访问它。



规范中的其他字段，如 `license`、`compatibility` 和 `allowed-tools`，会被解析，但随后被忽略。发现过程将包含 `SKILL.md` 的目录视为技能根目录，不会继续向下遍历。其他位置则会递归遍历，跳过点开头的条目和 `node_modules`，并遵守 `.gitignore`、`.ignore` 和 `.fdignore`，见 `CA/src/core/package-manager.ts:371`。对于独立的 `.md` 文件，在 `~/.pi/agent/skills` 和 `.pi/skills` 中只认可顶层文件，而在 `.agents/skills` 目录中只认可顶层以下的文件，见 `CA/src/core/package-manager.ts:428`。



系统提示词只列出每个技能的名称、描述和绝对路径，从不包含正文。模型在任务匹配时读取文件，因此添加一个技能只会在提示词中增加一个条目，而不是增加它的全部指令：



系统提示词中的技能块，`CA/src/core/skills.ts`

```ts
const lines = [
    "\n\nThe following skills provide specialized instructions for specific tasks.",
    fileReadTool === "read"
    ? "Use the read tool to load a skill's file when the task matches its description."
    : fileReadTool === "bash"
    ? "Use bash to load a skill's file when the task matches its description."
    : "Load a skill's file when the task matches its description.",
    "When a skill file references a relative path, resolve it against the skill directory (parent of SKILL.md / dirname of the path) and use that absolute path in tool commands.",
    "",
    "<available_skills>",
];
```



这是 `formatSkillsForPrompt()` 的第 365–375 行。随后，每个可见技能都会添加一个包含 `<name>`、`<description>` 和 `<location>` 的 `<skill>`，并进行 XML 转义。段落构建器会将结果包裹在 `<skills>` 中，见 `CA/src/core/system-prompt.ts:179`。如果所选工具中既没有 `read` 也没有 `bash`，则省略此块。



输入 `/skill:name args` 后，输入文本会被替换为 `<skill name="N" location="P">`、一行 `References are relative to DIR.`、不含 frontmatter 的正文，以及 `</skill>`，之后是一个空行和参数，见 `CA/src/core/agent-session.ts:2146`。未知名称会保持原样传递。

## 提示词模板



提示词模板是一个 Markdown 文件，通过 `/name args` 展开到提示词中。名称就是去掉 `.md` 后的文件名。描述使用 frontmatter 中的 `description`；如果没有，则使用第一个非空行，截取到 60 个字符，超出时追加 `...`；`argument-hint` 为可选字段，见 `CA/src/core/prompt-templates.ts:129`。



对约定目录 `~/.pi/agent/prompts/` 和 `.pi/prompts/`（受信任时）的扫描不递归，传给 `--prompt-template` 的目录也一样，见 `CA/src/core/prompt-templates.ts:159`。在 `prompts` 设置或包中指定的目录则与其他资源目录一样，会递归收集，见 `CA/src/core/package-manager.ts:651`。



参数按空白分割，可以用 `'` 和 `"` 分组，不支持转义字符，见 `CA/src/core/prompt-templates.ts:25`。替换只对模板执行一遍；如果参数值本身包含 `$1`，不会再次展开，见 `CA/src/core/prompt-templates.ts:71`。



|<strong>语法</strong>|<strong>值</strong>|
|---|---|
|`$1`、`$2`、……|位置参数；缺失时 → `""`|
|`$@`、`$ARGUMENTS`|所有参数以空格连接|
|`${N:-default}`|第 N 个参数；缺失或为空时使用默认值|
|`${@:-default}`、`${ARGUMENTS:-default}`|所有参数；没有参数时使用默认值|
|`${@:N}`|从第 N 个开始的所有参数|
|`${@:N:L}`|从第 N 个开始的 L 个参数|



Bash 风格，只执行一遍。来源：`substituteArgs()`。



`AgentSession.prompt()` 对以 `/` 开头的文本应用四个阶段：先运行已注册的扩展命令并消耗该输入；否则，输入处理器会看到原始文本；接着展开 `/skill:`；最后展开模板，见 `CA/src/core/agent-session.ts:1963`。“从 `prompt()` 到 `agent_settled`”（原书第67页）继续追踪之后的文本流向。

## 主题



内置三个主题：默认主题 `system`，根据终端调色板生成，见 `CA/src/modes/interactive/theme/themecontroller.ts:175`；以及 `dark` 和 `light`。自定义主题是 JSON 文件，来自 `~/.pi/agent/themes/`、`.pi/themes/`（受信任时）、`themes` 设置、包或 `--theme`。只有位于 `~/.pi/agent/themes/` 中的当前自定义主题会被监视并热重载，见 `CA/src/modes/interactive/theme/theme.ts:808`。



主题文件包含 `name`、可选的 `appearance`（`"dark"` 或 `"light"`；省略时根据颜色检测）、可选的 `vars`、`colors`，以及可选的 `export` 块，后者使用 `pageBg`、`cardBg` 和 `infoBg` 控制 HTML 导出。`colors` 有 51 个必需键和 5 个可选键。颜色值可以是十六进制字符串、`oklch()`、`okhsl()`、某个 `vars` 条目的名称、表示终端默认值的 `""`，或表示调色板索引的 0–255 整数，见 `CA/src/modes/interactive/theme/theme-json.ts:13`。设置 `theme: "light-name/darkname"` 会跟随终端的明暗外观，浅色主题在前，见 `CA/src/modes/interactive/theme/theme.ts:652`；包含 `/` 的主题名称会被拒绝，见 `CA/src/modes/interactive/theme/theme.ts:528`。

## Pi 包



包把扩展、技能、提示词和主题捆绑在一起，可从 npm、git 或本地路径安装。它的清单是 `package.json` 中的 `pi` 键，包含四个可选的字符串数组，数组条目可以是 glob，见 `CA/src/core/pi-manifest.ts:4`：



包清单，`package.json`

```json
{
    "name": "@me/pi-tools",
    "keywords": ["pi-package"],
    "pi": {
    "extensions": ["/ext/*.ts"],
    "skills": ["/skills"],
    "prompts": ["/prompts"],
    "themes": ["/themes/*.json"]
    },
    "peerDependencies": { "@earendil-works/pi-coding-agent": "*", "typebox": "*" }
}
```



此为示例。加载器只读取 `pi` 键。如果没有该键，Pi 会回退到包根目录下的约定目录 `extensions/`、`skills/`、`prompts/` 和 `themes/`，见 `CA/src/core/package-manager.ts:2250`。



|<strong>来源格式</strong>|<strong>类型</strong>|<strong>安装位置</strong>|
|---|---|---|
|`npm:@scope/name[@version]`|npm；指定确切版本时会固定版本|`~/.pi/agent/npm/node_modules/`，使用 `-l` 时为 `.pi/npm/...`|
|`git:github.com/user/repo[@ref]`、`https://...`、`ssh://...`|git|`~/.pi/agent/git/<host>/<path>`：执行 `git clone`、`git checkout`，如果存在 `package.json`，再执行 `npm install`|
|`./path`、`/abs`、`~/...`|本地|原地使用|



项目包安装在 `.pi/` 下，且仅针对受信任项目。来源：`parseSource()`、`getManagedNpmInstallPath()`、`getGitInstallRoot()` 和 `installGit()`，见 `CA/src/core/package-manager.ts:2126`。



命令包括 `pi install <source> [-l]`、`pi remove <source> [-l]`（别名为 `uninstall`）、`pi update [--self|--extensions|--models|--all]` 和 `pi list`，见 `CA/src/package-manager-cli.ts:265`。不指定目标的 `pi update` 会更新 Pi 自身。



见 `CA/src/core/package-manager.ts:1721`。如果同一个标识同时在两个作用域中配置，项目条目胜出。已配置但尚未安装的包会在 `reload()` 期间安装，除非 `PI_OFFLINE` 为 `1`、`true` 或 `yes`，见 `CA/src/core/package-manager.ts:54`。



宿主向每个扩展提供 `pi-ai`、`pi-agent-core`、`pi-coding-agent`、`pi-tui` 和 `typebox`。如果包把它们中的任何一个列入 `dependencies`，就会收到警告：“宿主提供的扩展包必须在 `peerDependencies` 中以 `"*"` 版本范围声明，而不是放在 `dependencies` 中。”见 `CA/src/core/resource-loader.ts:93`。“扩展：加载与 API”（原书第113页）展示了加载器如何映射这些导入。



设置条目可以是对象，而不是字符串：`{ source, autoload?, extensions?, skills?, prompts?, themes? }`。每个数组都用于筛选包所提供的内容。普通条目和 glob 表示包含，`!glob` 表示排除，`+path` 强制包含一个确切路径，`-path` 强制排除一个确切路径，按这个顺序应用，见 `CA/src/core/package-manager.ts:745`。



> <strong>这对你意味着什么：</strong>
> 
> - 为不同作用域中的技能和模板使用唯一名称；发生冲突时，其中一个副本会被丢弃，只留下诊断信息。
> 
> - 要在单次运行中覆盖资源，请通过 `-e` 加载，而不是 `--skill`。
> 
> - 如果不希望不受信任检出目录中的 `AGENTS.md` 传递给模型，运行时使用 `-nc`。
> 
> - 在你发布的任何包中，都把宿主包声明为版本范围为 `"*"` 的 peer 依赖。
> 
> 



> 来源：`CA/src/core/resource-loader.ts`（`loadContextFileFromDir`、`findShadowedContextFile`、`loadProjectContextFiles`、`reload`、`loadFinalExtensionSet`、`dedupePrompts`、`collectExtensionPackageWarnings`）；`CA/src/core/project-trust.ts`（`resolveProjectTrusted`）；`CA/src/core/trust-manager.ts`；`CA/src/core/extensions/runner.ts`（`emitProjectTrustEvent`）；`CA/src/core/package-manager.ts`（`resourcePrecedenceRank`、`collectSkillEntries`、`collectAncestorAgentsSkillDirs`、`applyPatterns`、`resolve`、`addAutoDiscoveredResources`、`collectPackageResources`、`parseSource`、`getPackageIdentity`）；`CA/src/core/skills.ts`；`CA/src/core/system-prompt.ts`；`CA/src/core/agent-session.ts`（`prompt`、`_expandSkillCommand`）；`CA/src/core/prompt-templates.ts`；`CA/src/modes/interactive/theme/{theme.ts, theme-json.ts, theme-controller.ts}`；`CA/src/core/pi-manifest.ts`；`CA/src/package-manager-cli.ts`；`CA/docs/skills.md`；`research/capture/resources-precedence.mjs`；`research/out/resources-precedence.txt`。
> 
>
