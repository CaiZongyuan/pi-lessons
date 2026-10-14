---
title: 设置参考
---

<div class="section-kicker">R.4 / REFERENCE</div>

# R\.4 设置参考

---

`settings.json` 中每个键的默认值都定义在 getter 中，而不在文件里；该文件只保存你修改过的内容，项目级文件则几乎可以覆盖其中的所有设置。



`settings.json` 是无类型的 JSON，读取后被放入 `Settings` 接口，见 `CA/src/core/settings-manager.ts:133`。加载时不会自动填充默认值。每个 getter 都通过 `??` 应用自己的默认值，因此下表的默认值来自 getter；如果 getter 返回 `undefined`，则来自使用该值的代码。每一行都已与提交 `28dcce2` 的 `CA/src/core/settings-manager.ts` 核对；随附的 `CA/docs/settings.md` 与此处的所有默认值一致。类型采用 TypeScript 表示法，并用 `·` 分隔字符串字面量。



## 配置层级与合并



两个文件共同生成一个合并后的对象。全局文件是 `<agent dir>/settings.json`，项目文件是 `<cwd>/.pi/settings.json`，见 `CA/src/core/settings-manager.ts:300`。只有在项目受信任时，才会读取项目文件，见 `CA/src/core/settings-manager.ts:474`。setter 始终写入全局文件。



<BookFigure id="R.2" />

> 项目列表会替换全局列表；项目对象则会合并到全局对象中。`deepMergeObjects()` 只对普通对象递归，见 `CA/src/core/settings-manager.ts:195`，因此 `extensions` 或 `enabledModels` 等数组会被整体替换。`defaultTools` 是唯一具有自身合并规则的数组：如果列表中只包含 `+name`/`-name` 条目，就会追加到继承的列表后面，见 `CA/src/core/settings-manager.ts:225`。
> 
> 



无论项目文件如何设置，以下三个键都只从全局文件读取：`defaultProjectTrust`，见 `CA/src/core/settings-manager.ts:1101`；`cacheWarming`，见 `CA/src/core/settings-manager.ts:1024`；以及 `httpProxy`，见 `CA/src/main.ts:594`。`settings.json` 不接受注释：去除 BOM 后会通过 `JSON.parse()` 解析，见 `CA/src/core/settings-manager.ts:487`。



## 模型、思考与交互



|键|类型|默认值|作用|参见|
|---|---|---|---|---|
|`defaultProvider`、`defaultModel`|`string`|自动|启动模型；当模型变更被持久保存时，写入全局文件，见 `CA/src/core/agent-session.ts:2473`|配置、模型与身份验证（原书第99页）|
|`defaultThinkingLevel`|`ThinkingLevel`|`"medium"`|启动时的思考等级；默认值来自 `DEFAULT_THINKING_LEVEL`，见 `CA/src/core/default.ts:3`|配置、模型与身份验证（原书第99页）|
|`modelThinkingLevels`|`Record`|无|按精确的 `provider/modelId` 为各模型设置等级，见 `CA/src/core/settings-manager.ts:878`|配置、模型与身份验证（原书第99页）|
|`thinkingBudgets`|`{minimal, low, medium, high}`|内置预算|各思考等级的 token 预算|认证、成本、重试与目录（原书第41页）|
|`enabledModels`|`string[]`|所有模型|用于启动选择和循环切换的模型模式；`--models` 优先，见 `CA/src/main.ts:810`|配置、模型与身份验证（原书第99页）|
|`transport`|`"auto"` · `"sse"` · `"websocket"` · `"websocket-cached"`|`"auto"`|提供商提供多种传输方式时的首选方式，见 `CA/src/core/settings-manager.ts:905`|传输 API 与跨提供商交接（原书第36页）|
|`steeringMode`、`followUpMode`|`"one-at-a-time"` · `"all"`|`"one-at-a-time"`|一次投递多少条排队消息，见 `CA/src/core/settings-manager.ts:831`|智能体循环（原书第49页）|
|`doubleEscapeAction`|`"tree"` · `"fork"` · `"none"`|`"tree"`|编辑器为空时连按两次 Escape 的动作，见 `CA/src/core/settings-manager.ts:1447`|斜杠命令与快捷键（原书第197页）|
|`treeFilterMode`|`"default"` · `"no-tools"` · `"user-only"` · `"labeled-only"` · `"all"`|`"default"`|`/tree` 的初始筛选器；未知值回退到默认值，见 `CA/src/core/settings-manager.ts:1456`|斜杠命令与快捷键（原书第197页）|
|`externalEditor`|`string`|`$VISUAL`、`$EDITOR`，然后是 `nano` 或 `notepad`|Ctrl\+G 使用的命令，见 `CA/src/core/settings-manager.ts:1054`|斜杠命令与快捷键（原书第197页）|
|`defaultProjectTrust`|`"ask"` · `"always"` · `"never"`|`"ask"`|后备信任决定；仅全局生效|安全模型（原书第174页）|



模型设置块。getter 来自 `CA/src/core/settings-manager.ts`；思考等级默认值来自 `CA/src/core/defaults.ts`。



译注：源文将 `defaultThinkingLevel` 与 `modelThinkingLevels` 两行连成了一行，已按各列对应关系拆开。源文表格引用 `CA/src/core/default.ts:3`，表下注释则引用 `CA/src/core/defaults.ts`；两处拼写不一致，均按原文保留，未猜测哪个路径正确。



## 工具、codemode 与会话



|键|类型|默认值|作用|参见|
|---|---|---|---|---|
|`defaultTools`|`string[]`|`["read", "bash", "edit", "write"]`|启动工具；普通名称替换默认值；`+name` 添加、`-name` 移除，按顺序处理，见 `CA/src/core/settings-manager.ts:215`|内置工具（原书第81页）|
|`codemode.mode`|`"on"` · `"only"`|`"on"`|`only` 会对模型隐藏活动的直接工具，使模型通过 codemode 使用它们，见 `CA/src/extensions/codemode/index.ts:23`|codemode（原书第151页）|
|`codemode.inlineBudget`|`number`|`3000`|codemode 描述可用于声明的估算 token 数（字符数 ÷ 4），见 `CA/src/extensions/codemode/tool.ts:156`|codemode（原书第151页）|
|`shellPath`|`string`|平台 shell|bash 所用的 shell；会展开开头的 `~`，见 `CA/src/core/settings-manager.ts:1078`|内置工具（原书第81页）|
|`shellCommandPrefix`|`string`|无|加在每条 bash 命令之前|内置工具（原书第81页）|
|`npmCommand`|`string[]`|`npm`|npm 查询和安装所用的 argv；自更新仅读取全局值，见 `CA/src/package-manager-cli.ts:946`|上下文文件、技能、模板、主题与软件包（原书第106页）|
|`images.autoResize`|`boolean`|`true`|发送前将图像缩放至最大 2000 × 2000，见 `CA/src/core/settings-manager.ts:1404`|内置工具（原书第81页）|
|`images.blockImages`|`boolean`|`false`|不向任何提供商发送图像，见 `CA/src/core/settings-manager.ts:1417`|内置工具（原书第81页）|
|`sessionDir`|`string`|`/sessions/--`（源文如此，疑似残缺）|会话目录；在决定项目信任之前读取，见 `CA/src/main.ts:669`|会话：JSONL 树（原书第86页）|
|`compaction.enabled`|`boolean`|`true`|自动压缩，见 `CA/src/core/settings-manager.ts:915`|压缩与分支摘要（原书第92页）|
|`compaction.reserveTokens`|`number`|`16384`|为响应预留的 token 数，见 `CA/src/core/settings-manager.ts:23`|压缩与分支摘要（原书第92页）|
|`compaction.keepRecentTokens`|`number`|`20000`|保持原文、不做摘要的近期 token 数，见 `CA/src/core/settings-manager.ts:23`|压缩与分支摘要（原书第92页）|
|`compaction.modelOverrides`|`Record`|无|以 `provider/modelId` 为键的各模型设置值；每个字段按“覆盖值 → 普通值 → 默认值”的顺序解析，见 `CA/src/core/settings-manager.ts:952`|压缩与分支摘要（原书第92页）|
|`branchSummary.reserveTokens`|`number`|`16384`|为已放弃的分支生成摘要时预留的 token 数，见 `CA/src/core/settings-manager.ts:978`|压缩与分支摘要（原书第92页）|
|`branchSummary.skipPrompt`|`boolean`|`false`|跳过“是否为分支生成摘要？”提示，并默认不生成摘要|压缩与分支摘要（原书第92页）|



压缩参数必须是非负安全整数；任何其他值都会在 getter 执行时抛出错误。验证逻辑位于压缩 token getter 中，见 `CA/src/core/settings-manager.ts:935`。



## 网络、重试与成本



|键|类型|默认值|作用|参见|
|---|---|---|---|---|
|`retry.enabled`|`boolean`|`true`|对暂时性错误进行智能体级重试，见 `CA/src/core/settings-manager.ts:988`|认证、成本、重试与目录（原书第41页）|
|`retry.maxRetries`|`number`|`3`|智能体级尝试次数|认证、成本、重试与目录（原书第41页）|
|`retry.baseDelayMs`|`number`|`2000`|首次退避延迟；每次尝试后翻倍，见 `CA/src/core/settings-manager.ts:1004`|认证、成本、重试与目录（原书第41页）|
|`retry.maxAgentDelayMs`|`number`|`60000`|智能体级最长延迟；`DEFAULT_MAX_AGENT_RETRY_DELAY_MS`，见 `ai/utils/retry.ts:124`|认证、成本、重试与目录（原书第41页）|
|`retry.provider.timeoutMs`|`number`|`httpIdleTimeoutMs`|提供商请求超时，见 `CA/src/core/sdk.ts:332`|认证、成本、重试与目录（原书第41页）|
|`retry.provider.maxRetries`|`number`|`0`|pi\-ai 内部重试；默认值来自 `retryProviderRequest()`，见 `ai/utils/provider-retry.ts:109`|认证、成本、重试与目录（原书第41页）|
|`retry.provider.maxRetryDelayMs`|`number`|`60000`|可接受的服务器要求的最长延迟，见 `CA/src/core/settings-manager.ts:1038`|认证、成本、重试与目录（原书第41页）|
|`httpIdleTimeoutMs`|`number`|`300000`|响应头和响应体的空闲超时；`0` 表示禁用，见 `CA/src/core/http-dispatcher.ts:4`|认证、成本、重试与目录（原书第41页）|
|`websocketConnectTimeoutMs`|`number`|`15000`|OpenAI Codex 的 WebSocket 连接超时；`0` 表示禁用，见 `ai/api/openai-codex-responses.ts:57`|传输 API 与跨提供商交接（原书第36页）|
|`httpProxy`|`string`|无|在 `HTTP_PROXY` 和 `HTTPS_PROXY` 未设置时，将此值复制到两者；仅全局生效，见 `CA/src/core/http-dispatcher.ts:45`|环境变量（原书第185页）|
|`cacheWarming`|`"off"` · `"streaming"` · `"idle"`|`"streaming"`|在运行期间，或也在运行间隙，保持提示词缓存处于热状态；仅全局生效，因为每次刷新都会产生费用|认证、成本、重试与目录（原书第41页）|



两层重试的默认值不同。智能体重试默认开启，提供商重试默认关闭。`getHttpIdleTimeoutMs()` 返回 `300000`，而值 `0` 在请求选项中会变成 `2147483647` ms，见 `CA/src/core/sdk.ts:328`。



## 资源、终端与显示



|键|类型|默认值|作用|参见|
|---|---|---|---|---|
|`packages`|`(string · {source, autoload?, extensions?, skills?, prompts?, themes?})[]`|`[]`|npm、git 或本地软件包来源|上下文文件、技能、模板、主题与软件包（原书第106页）|
|`extensions`、`skills`、`prompts`、`themes`|`string[]`|`[]`|本地路径；`!pattern`、`+path`、`-path` 筛选器|上下文文件、技能、模板、主题与软件包（原书第106页）|
|`enableSkillCommands`|`boolean`|`true`|将每个技能注册为 `/skill:name`，见 `CA/src/core/settings-manager.ts:1265`|上下文文件、技能、模板、主题与软件包（原书第106页）|
|`theme`|`string`|`"system"`|主题名称；`initTheme()` 会回退到 `system`，见 `CA/src/modes/interactive/theme/theme.ts:757`|上下文文件、技能、模板、主题与软件包（原书第106页）|
|`quietStartup`|`boolean` · `"header"`|`false`|`true` 隐藏启动标题和资源列表；`"header"` 保留标题，见 `CA/src/core/settings-manager.ts:1089`|运行模式（原书第127页）|
|`collapseChangelog`|`boolean`|`false`|更新后以精简形式显示更新日志|遥测与评测（原书第179页）|
|`tuiMode`|`"fullscreen"` · `"regular"`|`"fullscreen"`|交互式渲染器模式，见 `CA/src/core/settings-manager.ts:1349`|pi\-tui（原书第158页）|
|`fullscreenExitOutput`|`"transcript"` · `"resume-hint"`|`"transcript"`|退出全屏时打印的内容|pi\-tui（原书第158页）|
|`fullscreenScrollbar`|`"auto"` · `"always"` · `"hidden"`|`"auto"`|对话记录滚动条，见 `CA/src/core/settings-manager.ts:1368`|pi\-tui（原书第158页）|
|`fullscreenCopyOnSelect`|`boolean`|`true`|自动复制选中的文本|pi\-tui（原书第158页）|
|`fullscreenWheelScrollLines`|`"auto"` · `number`|`"auto"`|每次滚轮事件滚动的行数，限制在 1–100，见 `CA/src/core/settings-manager.ts:1389`|pi\-tui（原书第158页）|
|`terminal.showImages`|`boolean`|`true`|在支持的情况下显示内联图像|pi\-tui（原书第158页）|
|`terminal.imageWidthCells`|`number`|`60`|首选内联图像宽度，见 `CA/src/core/settings-manager.ts:1301`|pi\-tui（原书第158页）|
|`terminal.images`|`"kitty"` · `"iterm2"` · `"auto"` · `false`|`"auto"`|覆盖图像协议检测结果，见 `CA/src/core/settings-manager.ts:1278`|pi\-tui（原书第158页）|
|`terminal.hyperlinks`、`terminal.trueColor`|`boolean` · `"auto"`|`"auto"`|覆盖 OSC 8 和真彩色检测结果|pi\-tui（原书第158页）|
|`terminal.clearOnShrink`|`boolean`|`false`，或 `PI_CLEAR_ON_SHRINK=1`|内容缩短时清除空行，见 `CA/src/core/settings-manager.ts:1318`|pi\-tui（原书第158页）|
|`terminal.showTerminalProgress`|`boolean`|`false`|在终端标签页中显示 OSC 9;4 进度|pi\-tui（原书第158页）|
|`showHardwareCursor`|`boolean`|`false`，或 `PI_HARDWARE_CURSOR=1`|为输入法定位光标时显示光标，见 `CA/src/core/settings-manager.ts:1469`|pi\-tui（原书第158页）|
|`markdown.mermaid`|`"off"` · `"final"` · `"streaming"`|`"streaming"`|Mermaid 渲染，见 `CA/src/core/settings-manager.ts:1512`|pi\-tui（原书第158页）|
|`markdown.codeBlockIndent`|`string`|两个空格|渲染代码块时使用的前缀，见 `CA/src/core/settings-manager.ts:1509`|pi\-tui（原书第158页）|
|`hideThinkingBlock`|`boolean`|`false`|在对话记录中隐藏思考块|pi\-tui（原书第158页）|
|`showCacheMissNotices`|`boolean`|`false`|显示缓存未命中、缓存预热、压缩用量和恢复通知|认证、成本、重试与目录（原书第41页）|
|`editorPaddingX`|`number`|`0`|编辑器内边距；setter 将值限制在 0–3，见 `CA/src/core/settings-manager.ts:1483`|pi\-tui（原书第158页）|
|`outputPad`|`0` · `1`|`1`|对话记录内边距；除 `0` 外的任何值都读取为 `1`，见 `CA/src/core/settings-manager.ts:1489`|pi\-tui（原书第158页）|
|`autocompleteMaxVisible`|`number`|`5`|自动补全行数；setter 将值限制在 3–20，见 `CA/src/core/settings-manager.ts:1503`|pi\-tui（原书第158页）|
|`enableInstallTelemetry`|`boolean`|`true`|安装遥测 ping 和提供商归因请求头；`PI_TELEMETRY` 可覆盖此值，见 `CA/src/core/settings-manager.ts:1142`|遥测与评测（原书第179页）|
|`enableAnalytics`|`boolean`|`false`|选择加入分析；由实验性的首次运行设置使用|遥测与评测（原书第179页）|
|`warnings.anthropicExtraUsage`|`boolean`|`true`|当 Anthropic 订阅认证可能产生付费额外用量时发出警告；只有 `false` 才会禁用，见 `CA/src/modes/interactive/interactive-mode.ts:5233`|认证、成本、重试与目录（原书第41页）|



范围限制位于 setter 中。只有通过 `/settings` 写入 `editorPaddingX` 和 `autocompleteMaxVisible` 时，才会限制它们的取值；手工编辑的值会按原样返回。



以下三个键由 Pi 写入，不应手工编辑：`lastChangelogVersion`、`trackingId`（启用分析时创建）和 `deviceId`（首次登录需要时创建的 UUID，仅全局生效），见 `CA/src/core/settings-manager.ts:157`。
