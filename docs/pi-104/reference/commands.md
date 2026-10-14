---
title: 斜杠命令与快捷键
---

<div class="section-kicker">R.3 / REFERENCE</div>

# R\.3 斜杠命令与快捷键

---

交互式编辑器内置了 24 个斜杠命令，这些命令仅在该编辑器中可用；快捷键对应 90 个具名操作，其默认绑定会因 Windows 和 WSL 而异。所有操作都可以在同一个 JSON 文件中重新绑定或禁用。



本节内容仅适用于交互模式，参见“运行模式”（原书第127页）。RPC 客户端将斜杠命令作为提示词文本发送，而在 RPC 中，只有来自扩展、提示词模板或技能的命令才有效，参见“RPC 模式与 SDK”（原书第133页）。



## 内置斜杠命令



|命令|参数|作用|参见|
|---|---|---|---|
|`/settings`||设置菜单|设置参考（原书第202页）|
|`/model`|`[provider/model]`|打开模型选择器，或直接选择模型|提供商与模型（原书第24页）|
|`/tree`||浏览会话树并切换分支|会话：JSONL 树（原书第86页）|
|`/thinking`|`[level]`|设置思考等级|认证、成本、重试与目录（原书第41页）|
|`/scoped-models`||选择按 Ctrl\+P 循环切换的模型|配置、模型与身份验证（原书第99页）|
|`/export`|`[path]`|默认导出 HTML；根据扩展名导出 `.html` 或 `.jsonl`|会话：JSONL 树（原书第86页）|
|`/import`||导入 JSONL 会话并恢复该会话|会话：JSONL 树（原书第86页）|
|`/share`||上传为私密 GitHub gist；链接为 `https://pi.dev/session/#`|环境变量（原书第185页）|
|`/bug`|`[description]`|为 Pi 开发者准备错误报告|—|
|`/copy`||复制智能体的最后一条消息|—|
|`/name`|`[name]`|设置会话的显示名称|会话：JSONL 树（原书第86页）|
|`/session`||会话信息与统计数据|会话：JSONL 树（原书第86页）|
|`/changelog`||更新日志条目|—|
|`/hotkeys`||所有当前生效的快捷键|本节|
|`/fork`||从较早的一条用户消息创建新会话|会话：JSONL 树（原书第86页）|
|`/clone`||在当前位置复制会话|会话：JSONL 树（原书第86页）|
|`/trust`||保存项目信任决定|安全模型（原书第174页）|
|`/login`|`[provider]`|配置提供商认证|认证、成本、重试与目录（原书第41页）|
|`/logout`||移除提供商认证|认证、成本、重试与目录（原书第41页）|
|`/compact`|`[instructions]`|立即压缩，可选用自定义指令|压缩与分支摘要（原书第92页）|
|`/resume`||选择另一个会话|会话：JSONL 树（原书第86页）|
|`/reload`||重新加载快捷键、扩展、技能、提示词、主题和上下文文件|上下文文件、技能、模板、主题与软件包（原书第106页）|
|`/quit`||退出 Pi|—|



此列表是按源码顺序列出的 `BUILTIN_SLASH_COMMANDS`。共 24 项，见 `CA/src/core/slash-commands.ts:19`；编辑器的提交处理函数通过精确文本，或文本后跟一个空格的方式匹配每个命令，见 `CA/src/modes/interactive/interactive-mode.ts:3185`。`PI_SHARE_VIEWER_URL` 可替换分享链接的基础 URL，见 `CA/src/config.ts:596`。



译注：源文正文称有 24 项，但所提供的表格仅含 23 个命令；此处保留全部现有行，不补写缺失项。`/share` 的链接在源文中止于 `#`，此处按原样保留。



另外还有三个命令也会被处理，但不在列表中，因此自动补全不会提供它们：`/debug` 会将每一条已渲染的行及其可见宽度写入调试日志，见 `CA/src/modes/interactive/interactive-mode.ts:6904`；`/arminsayshi` 和 `/dementedelves` 则是彩蛋，见 `CA/src/modes/interactive/interactive-mode.ts:3305`。在任何位置按 Shift\+Ctrl\+D 都会触发同样的调试转储；这一快捷键接在 pi\-tui 中，而非快捷键表中，因此不能重新绑定，见 `tui/tui.ts:1075`。



## 来自资源的命令



|来源|形式|说明|参见|
|---|---|---|---|
|内置 mcp 扩展|`/mcp`|登录、重新连接、启用或禁用服务器、更改暴露方式|MCP（原书第144页）|
|内置 lama\.cpp 扩展|`/lama`|管理 lama\.cpp 路由器模型；仅限 TUI|提供商与模型（原书第24页）|
|任意扩展|`/`|`pi.registerCommand(name, ...)`|扩展、加载与 API（原书第113页）|
|提示词模板|`/`|将模板展开为提示词|上下文文件、技能、模板、主题与软件包（原书第106页）|
|技能|`/skill:`|仅在 `enableSkillCommands` 为 `true` 时可用，默认即为 `true`|上下文文件、技能、模板、主题与软件包（原书第106页）|



译注：源文中任意扩展、提示词模板和技能的命令形式分别只显示为 `/`、`/` 和 `/skill:`，名称占位符疑似在转换时丢失，未擅自补写；`lama.cpp`、`/lama` 及相应源码路径均保留源文拼写。



如果两个扩展注册了同一个名称，它们都会加上后缀。按加载顺序分别变为 `name:1`、`name:2`；已被占用的后缀会被跳过，见 `CA/src/core/extensions/runner.ts:825`。如果扩展命令与内置命令同名，自动补全会排除该扩展命令并发出警告；只有当它带有后缀名称时，才能通过该名称调用，见 `CA/src/modes/interactive/interactive-mode.ts:703`。来源：`CA/src/extensions/mcp/index.ts:1141`、`CA/src/extensions/lama/index.ts:183`、`CA/src/core/settings-manager.ts:164`。



## 编辑器前缀



|前缀|作用|参见|
|---|---|---|
|`/`|命令自动补全|上文|
|`@`|文件路径自动补全；附加对应文件|pi\-tui（原书第158页）|
|`! cmd`|通过 bash 运行；输出进入上下文|内置工具（原书第81页）|
|`!! cmd`|通过 bash 运行；输出不进入上下文|内置工具（原书第81页）|



一输入 `!`，编辑器就切换到 bash 模式。输入第一个 `!` 时边框颜色便会改变，见 `CA/src/modes/interactive/interactive-mode.ts:3105`；提交后才运行命令，见 `CA/src/modes/interactive/interactive-mode.ts:3327`。



## 应用快捷键



默认值来自 `KEYBINDINGS`，见 `CA/src/core/keybindings.ts:75`。“Win”表示原生 Windows；“WSL”表示设置了 `WSL_DISTRO_NAME` 或 `WSL_INTEROP` 的 Linux，见 `CA/src/core/keybindings.ts:62`。



|操作|默认快捷键|Win / WSL|作用|
|---|---|---|---|
|`app.interrupt`|Esc||中止一次运行（排队文本会返回编辑器）、一条 bash 命令或 bash 模式；编辑器为空时，在 500 ms 内按两次会执行 `doubleEscapeAction`|
|`app.clear`|Ctrl\+C||清空编辑器；在 500 ms 内按两次会退出|
|`app.exit`|Ctrl\+D||编辑器为空时退出|
|`app.suspend`|Ctrl\+Z|Win：无|挂起到后台|
|`tui.input.submit`|Enter||发送；若智能体正在运行，则作为引导消息发送|
|`app.message.followUp`|Alt\+Enter|Ctrl\+Q|将一条后续消息加入队列|
|`app.message.dequeue`|Alt\+Up|Alt\+Q|将排队消息放回编辑器|
|`app.model.select`|Ctrl\+L||模型选择器|
|`app.model.cycleForward`|Ctrl\+P||下一个模型|
|`app.model.cycleBackward`|Shift\+Ctrl\+P|Alt\+P|上一个模型|
|`app.thinking.cycle`|Shift\+Tab||下一个思考等级|
|`app.thinking.toggle`|Ctrl\+T||折叠或展开思考块|
|`app.tools.expand`|Ctrl\+O||折叠或展开工具输出|
|`app.editor.external`|Ctrl\+G||在外部编辑器中编辑提示词|
|`app.clipboard.pasteImage`|Ctrl\+V|Alt\+V|粘贴文件（macOS）、图像或文本|
|`app.message.copy`|Ctrl\+X||复制选中内容或助手的最后一条消息|
|`app.session.new`、`.tree`、`.fork`、`.resume`|无||`/new`、`/tree`、`/fork`、`/resume` 的未绑定快捷键|



`doubleEscapeAction` 默认为 `tree`；另有 `fork` 和 `none` 可选。见 `CA/src/core/settings-manager.ts:169`。Escape 的处理顺序和时间间隔来自 `CA/src/modes/interactive/interactive-mode.ts:3050–3075` 和 `:4229`。



## 特定界面的快捷键



这些快捷键只在某个选择器或视图中生效，因此会复用编辑器也使用的按键。



|视图|操作|默认快捷键|作用|
|---|---|---|---|
|`/tree`|`app.tree.foldOrUp / unfoldOrDown`|Alt\+← / Alt\+→、Ctrl\+← / Ctrl\+→|折叠或展开一个分支片段|
||`app.tree.editLabel`|Shift\+L|编辑节点标签|
||`app.tree.toggleLabelTimestamp`|Shift\+T|标签时间戳|
||`app.tree.filter.default·noTools·userOnly·labeledOnly·all`|Ctrl\+D · Ctrl\+T · Ctrl\+U · Ctrl\+L · Ctrl\+A|树筛选器|
||`app.tree.filter.cycleForward/cycleBackward`|Ctrl\+O / Shift\+Ctrl\+O|循环切换筛选器|
|会话选择器|`app.session.togglePath · toggleSort · toggleNamedFilter`|Ctrl\+P · Ctrl\+S · Ctrl\+N|路径显示、排序、仅显示具名会话|
||`app.session.rename · delete · deleteNoninvasive`|Ctrl\+R · Ctrl\+D · Ctrl\+Backspace|重命名、删除、查询为空时删除|
|模型和思考等级选择器|`app.models.save · app.thinking.save`|Ctrl\+S|将选择保存到设置中|
|`/scoped-models`|`app.models.enableAll · clearAll · toggleProvider`|Ctrl\+A · Ctrl\+X · Ctrl\+P|批量启用、清空、按提供商切换|
||`app.models.reorderUp/reorderDown`|Alt\+↑ / Alt\+↓|调整循环切换顺序|
|全屏|`tui.altScreen.search`|Ctrl\+Shift\+F（Win/WSL：Ctrl\+F）|搜索对话记录；Enter / Shift\+Enter 跳到下一个 / 上一个结果|
||`tui.altScreen.previousPrompt/nextPrompt`|Ctrl\+Shift\+↑ / ↓ 和 Ctrl\+↑ / ↓（Win/WSL：仅 Ctrl）|在提示词之间跳转|
||`tui.altScreen.top/bottom`|Ctrl\+Home / Ctrl\+End|跳到顶部；跳到底部并跟随|
||`tui.altScreen.pageUp/pageDown`|PageUp / PageDown|滚动一页|



`/tree` 的折叠快捷键在 macOS 上优先列出 Alt，在其他系统上优先列出 Ctrl；两组按键在所有系统上均有绑定。见 `CA/src/core/keybindings.ts:151`。全屏模式的默认值来自 `tui/keybindings.ts:160–209`，覆盖设置位于 `CA/src/core/keybindings.ts:82–92`。



## 编辑器快捷键



|操作|默认快捷键|操作|默认快捷键|
|---|---|---|---|
|`tui.input.newLine`|Shift\+Enter、Ctrl\+J|`tui.editor.deleteWordBackward`|Ctrl\+W、Alt\+Backspace|
|`tui.input.tab`|Tab（自动补全）|`tui.editor.deleteWordForward`|Alt\+D、Alt\+Delete|
|`tui.editor.cursorLineStart`|Home、Ctrl\+A|`tui.editor.deleteToLineStart`|Ctrl\+U|
|`tui.editor.cursorLineEnd`|End、Ctrl\+E|`tui.editor.deleteToLineEnd`|Ctrl\+K|
|`tui.editor.cursorWordLeft`|Alt\+←、Ctrl\+←、Alt\+B|`tui.editor.yank / yankPop`|Ctrl\+Y / Alt\+Y|
|`tui.editor.cursorWordRight`|Alt\+→、Ctrl\+→、Alt\+F|`tui.editor.undo`|Ctrl\+\-（Win：Ctrl\+Z；WSL：Alt\+Z）|
|`tui.editor.jumpForward/jumpBackward`|Ctrl\+\] / Ctrl\+Alt\+\]|`tui.editor.historyPrevious / historyNext`|无|



编辑器遵循 Emacs 惯例。Up 和 Down 用于移动光标，在首行或末行时则用于浏览提示词历史，见 `CA/docs/keybindings.md` 的“光标移动”一节。来源：`tui/keybindings.ts:72–146`，以及 `CA/src/core/keybindings.ts:77` 中对撤销操作的覆盖设置。



## 重新绑定



`<agent Dir>/keybindings.json` 将操作 ID 映射到一个按键或一个按键数组；配置值会替换默认值，而 `[]` 会禁用该操作，见 `CA/src/core/keybindings.ts:379`。按键写作 `modifier+key`，修饰键包括 `ctrl`、`shift`、`alt` 和 `super`，见 `CA/docs/keybindings.md` 的“按键语法”一节。`cycleModelForward` 等旧名称会在加载时迁移为对应的 `app.` 或 `tui.` ID，见 `CA/src/core/keybindings.ts:240`。如果文件不是有效 JSON，则会被静默忽略，所有操作均使用默认值，见 `CA/src/core/keybindings.ts:360`。`/reload` 会重新读取该文件。



`keybindings.json` 示例。来源：`CA/docs/keybindings.md`。格式：JSON。



```json
{
    "app.session.new": "ctrl+shift+n",
    "app.session.tree": ["ctrl+shift+t", "alt+shift+t"]
}
```



复制自随附文档的“分配快捷键”一节。



如果扩展快捷键与内置快捷键冲突，则要么替换内置快捷键并发出警告，要么被跳过，具体取决于内置快捷键的 `restrictOverride` 标志，见 `CA/src/core/extensions/runner.ts:690`。详情参见“扩展、加载与 API”（原书第113页）。



来源：`CA/src/core/slash-commands.ts`（`BUILTIN_SLASH_COMMANDS`）。`CA/src/modes/interactive/interactive-mode.ts`（`setupEditorSubmitHandler`、`setupKeyHandlers`、`getBuiltInCommandConflictDiagnostics`、`handleDebugCommand`、`handleCtrlC`）。`CA/src/core/extensions/runner.ts`（`getRegisteredCommands`、`getShortcuts`）。`CA/src/core/keybindings.ts`（`KEYBINDINGS`、`useWindowsKeybindings`、`KEYBINDING_NAME_MIGRATIONS`、`KeybindingsManager`）；`tui/keybindings.ts`（`TUI_KEYBINDINGS`）；`tui/tui.ts`（`onDebug`）。`CA/src/core/settings-manager.ts`（`doubleEscapeAction`、`enableSkillCommands`）；`CA/src/config.ts`（`getShareViewerUrl`）。`CA/src/extensions/mcp/index.ts`、`lama/index.ts`。`CA/docs/slash-commands.md`、`keybindings.md`。
