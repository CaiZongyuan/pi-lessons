---
title: "pi-tui：终端 UI 框架"
originalPage: 158
---

<div class="section-kicker">6.3 / INTEGRATION & INTERFACES</div>

# pi\-tui：终端 UI 框架

---

每个组件将给定宽度转换为一组行，渲染器在一个同步输出块中只写出发生变化的行。Pi 默认使用备用屏幕渲染器，它从不会因行过宽而报错；保留终端回滚历史的渲染器则会。



人们在交互式 Pi 中看到的一切，包括编辑器、流式对话记录、工具输出、`/mcp` 和每个扩展对话框，都由 `@earendil-works/pi-tui` 绘制。其 README 称它是“一个采用差分渲染与同步输出的极简终端 UI 框架，用于构建无闪烁的交互式 CLI 应用”（`tui/README.md`）。本节介绍组件契约、两种渲染器及其写出的字节、键盘输入如何协商和路由、浮层、终端能力与原生附加模块，以及内置组件。该包有两个运行时依赖：`get-east-asian-width` 1\.6\.0 和 `marked` 18\.0\.11；测试使用 `node:test` 运行，其中多项针对 `@xterm/headless` 5\.5\.0（`tui/package.json`）。

## 组件是宽度的函数



完整的组件契约。来源：`tui/tui.ts`。

```ts
export interface Component {
  /**
   * 按给定视口宽度将组件渲染为多行
   * @param width - 当前视口宽度
   * @returns 字符串数组，每个字符串表示一行
   */
  render(width: number): string[];
  /** 组件获得焦点时可选的键盘输入处理器。 */
  handleInput?(data: string): void;

  /** 可选的标准化鼠标处理器。 */
  handleMouse?(event: TuiMouseEvent): TuiMouseEventResult | undefined;

  /**
   * 若为 true，组件会接收按键释放事件（Kitty 协议）。
   * 默认为 false，即过滤掉释放事件。
   */
  wantsKeyRelease?: boolean;

  /**
   * 使所有缓存的渲染状态失效。
   * 在主题变化或组件需要从头重新渲染时调用。
   */
  invalidate(): void;
}
```

> 完整内容，第 117–142 行。
> 
> 



组件返回带有 ANSI 样式的行；当组件获得焦点时，`handleInput` 接收原始字节，包括转义序列。`Focusable` 组件多一个字段 `focused`；当该值为 `true` 时，它会在光标应在的位置输出 `CURSOR_MARKER`，即 `"\x1b_pi:c\x07"`，这是一个零宽 APC 序列。渲染器找到该标记，将其移除，并把硬件光标移到相应位置；输入法就在这里绘制候选窗口（`tui/tui.ts:180`；`tui/tui.ts:196`）。`Container` 将子组件纵向堆叠，并根据鼠标事件的 `y`，将事件路由给其所在行对应的子组件（`tui/tui.ts:347`）。



合成后，渲染器在每个非图像行末尾追加 `SEGMENT_RESET`，即 `"\x1b[0m\x1b]8;;\x07"`（SGR 重置加上 OSC 8 关闭），以免样式或超链接泄漏到下一行（`tui/tui.ts:412`；`tui/tui.ts:1413`）。



<strong>宽度规则。</strong> README 的要求很严格：“每行都不能超过 width，否则 TUI 会报错”（`tui/README.md`）。代码中，一个渲染器执行得更严格，另一个则更宽松，详见下方“文档 ≠ 代码”提示。

## 两种渲染器



<BookFigure id="6.5" />

> Pi picks the alternate\-screen renderer unless tuiMode is "regular"\. Both share TuiBase; only doRender\(\) differs\. Schematic, from tui/tui\.ts \(Component, Container, TUI, TuiBase\), tui\-main\-screen\.ts, tui\-alt\-screen\.ts, and CA/src/modes/interactive/tui\-renderer\.ts \(createInteractiveTui\)\.
> 
> 



<strong>结构：</strong>

- `Container`：`children: Component[]` · 纵向堆叠 · 按行分发鼠标事件

- «接口» `TUI`：`mode` · `setFocus` · `showOverlay` · `requestRender` · `start` · `stop`

- ↓ 继承 `Container`，实现 `TUI`

- «抽象类» `TuiBase`：焦点 · 浮层栈 · 输入路由 · 16 ms 渲染节流 · 抽象 `doRender()`

- `TuiMainScreen` · 模式 `"regular"`：与上一帧逐行比较差异 · 输出保留在终端回滚历史中 · 行过宽时抛出异常

- `TuiAltScreen` · 模式 `"fullscreen"`：备用屏幕 · 按行比较差异 · 鼠标、选择、搜索、滚动条 · 过宽行被裁切 · Pi 的默认选择

    

除非 `tuiMode` 为 `"regular"`，否则 Pi 选择备用屏幕渲染器。两者共享 `TuiBase`；只有 `doRender()` 不同。示意结构来源：`tui/tui.ts`（`Component`、`Container`、`TUI`、`TuiBase`）、`tui-main-screen.ts`、`tui-alt-screen.ts`，以及 `CA/src/modes/interactive/tui-renderer.ts`（`createInteractiveTui`）。



编码智能体的 `tuiMode` 设置默认为 `"fullscreen"`（`CA/src/core/settings-manager.ts:184`），`createInteractiveTui` 会为其构建 `TuiAltScreen`，只有设置为 `"regular"` 才构建 `TuiMainScreen`（`CA/src/modes/interactive/tui-renderer.ts:22`）。



<strong>调度。</strong> `MIN_RENDER_INTERVAL_MS` 为 16，约每秒 60 帧（`tui/tui.ts:507`）。`requestRender()` 设置标志并延后到 `process.nextTick`；后者安排一个 `setTimeout`，等待这 16 ms 中剩余的时间；期间的后续请求会合并到这一帧中（`tui/tui.ts:990`）。键盘输入跳过节流，因为“即使是 `setTimeout(0)`，在 Windows 上也可能花费完整的一个 16 ms 时钟周期”（`tui/tui.ts:1117`）。



<strong>主屏幕帧。</strong> `TuiMainScreen.doRender()` 渲染组件树、合成浮层、提取光标标记、应用逐行重置，然后决定采用全量写入还是差分写入（`tui/tui-main-screen.ts:247`）。



<BookFigure id="6.6" />

> 首个匹配项生效；每个玫瑰色行都会清除回滚历史。每次写入都包裹在同步输出序列（`CSI ? 2026 h/l`）内，因此终端显示的是完整帧。写入经过 `BoundedTerminalWriter`，它以 1 MiB 块流式输出，因此全量渲染也不会构造出超过 V8 限制的字符串。来源：`tui/tui-main-screen.ts:247–567`。
> 
> 



采集工具集使用一个 20 × 10 的桩终端和三行 `Text` 驱动 `TuiMainScreen`，然后修改中间那一行。转义字节表示为 `\u001b`：

```text
<# frame 1: first render
"\u001b[?2026halpha               \u001b[0m\u001b]8<;\u0007\r\nbeta
\u001b[0m\u001b]8<;\u0007\r\ngamma               \u001b[0m\u001b]8<;\u0007\u001b[?2026l"
<# frame 2: line 1 changed
"\u001b[?2026h\u001b[1A\r\u001b[2KBETA                \u001b[0m\u001b]8<;\u0007\u001b[?2026l"
<# frame 3: nothing changed
fullRedraws: 1
```

> 第 2 帧正是这种设计的意义所在：一次光标上移、一次清行、20 列内容以及一次重置；单词变更只需 55 字节。第 3 帧不写入任何内容。`Text` 会把每行填充到给定宽度，因此重置落在第 20 列之后（`research/out/tui-frames.txt`）。
> 
> 



<strong>备用屏幕帧。</strong> `TuiAltScreen` 以 `\x1b[?1049h` 进入备用屏幕，关闭自动换行；启用鼠标时，还会开启模式 1000、1002、1004（焦点报告）和 1006（SGR 鼠标）（`tui/tui-alt-screen.ts:63`）。它与前一屏逐行比较差异，并用绝对位置 `CSI <row>;1H` 加上 `CSI 2K` 重写发生变化的行（`tui/tui-alt-screen.ts:1745`），同样包裹在 `CSI ? 2026 h/l` 内。在此之上，它还增加了 `VStack`、`HStack` 和 `ScrollView` 布局、跟随末尾的对话记录、OSC 133 提示符跳转、滚动条、支持 OSC 52 复制的拖动选择、可点击的 OSC 8 链接，以及对话记录搜索（`tui/tui-alt-screen.ts:202`）。退出时，Pi 恢复主屏幕并打印对话记录；如果 `fullscreenExitOutput` 为 `"resume-hint"`，则只打印恢复提示（`CA/src/core/settings-manager.ts:185`）。



三个环境变量有助于调试：`PI_TUI_DEBUG_REDRAW=1` 将主屏幕每次全量重绘的原因记录到 `pi-tui-debug.log`（`tui/tui-main-screen.ts:321`）；`PI_TUI_DEBUG=1` 在 `/tmp/tui` 下为每个差分帧写一个日志文件（`tui/tui-main-screen.ts:569`）；`PI_TUI_WRITE_LOG=<file>` 捕获原始输出流（`tui/terminal.ts:152`）。



> <strong>文档 ≠ 代码</strong>
> 
> README 说，过宽的行会导致“TUI……报错”。在 `TuiMainScreen` 中，检查只位于差分路径上：某行比终端更宽时，会写入 `pi-tui-crash.log`、停止 TUI，并抛出“渲染行 N 超过终端宽度”（`tui/tui-main-screen.ts:517`）；首次帧或全量重绘则不检查，直接写出。Pi 默认的 `TuiAltScreen` 从不抛出这一异常，而是通过 `sliceByColumn` 将行裁切至给定宽度（`tui/tui-alt-screen.ts:1692`）。采集工具集确认了该异常：一个原始组件在 20 列终端中返回 25 列内容，导致第 5 帧停止，并报错“渲染行 3 超过终端宽度（25 \> 20）。”（`research/out/tui-frames.txt`）
> 
> 

## 输入与键盘协议



`ProcessTerminal.start` 将 stdin 设为原始模式，并通过 `\x1b[?2004h` 启用括号粘贴（`tui/terminal.ts:174`）。随后，它在一次写入中协商 Kitty 键盘协议：



请求标志 7，查询标志，并发送 DA1 作为哨兵。来源：`tui/terminal.ts`。

```js
const DESIRED_KITTY_KEYBOARD_PROTOCOL_FLAGS = 7;
const KEYBOARD_PROTOCOL_RESPONSE_FRAGMENT_TIMEOUT_MS = 150;
const KITTY_KEYBOARD_PROTOCOL_QUERY = `\x1b[>${DESIRED_KITTY_KEYBOARD_PROTOCOL_FLAGS}u\x1b[?u\x1b[c`;
```

> 第 12–14 行。标志 7 = 1（消除转义码歧义）\+ 2（报告按下、重复和释放）\+ 4（报告替代按键）。
> 
> 



若回复为 `CSI ? <flags> u` 且标志非零，则开启 Kitty 模式。若标志为零，或先收到 DA1 回复而之前没有 Kitty 回复，则改用 `\x1b[>4;2m` 开启 xterm `modifyOtherKeys`（`tui/terminal.ts:267`）。每个终端都会回复 DA1，所以这一回退机制不需要启动超时。



`StdinBuffer` 会重新拼接被拆分到多次读取中的转义序列。单独的 ESC 会在 10 ms 后被视为 Escape 键；如果设置了 `SSH_CONNECTION` 或 `SSH_TTY`，则等待 100 ms，因为旧式 Alt\+按键以 ESC 加一个字节的方式到达。`PI_TUI_ESC_TIMEOUT` 可以覆盖这两个值（`tui/terminal.ts:115`）。



<strong>路由。</strong> `TuiBase.handleTerminalInput` 让每条输入经过一个固定的处理阶梯；最先消费它的步骤会结束后续处理（`tui/tui.ts:1044`）：

1. 终端颜色回复（OSC 10、11、4）和配色方案报告

2. 按顺序执行输入监听器；每个监听器都能消费或改写输入

3. 终端的单元格大小回复

4. 如果设置了调试处理器，则处理调试快捷键 Shift\+Ctrl\+D

5. 修复浮层焦点：已聚焦但不再可见的浮层，将焦点交给最顶层的可见浮层

6. Kitty 按键释放事件；除非获得焦点的组件设置了 `wantsKeyRelease`，否则丢弃

7. 获得焦点的组件的 `handleInput`，随后立即渲染

    

<strong>键绑定。</strong> `interface Keybindings` 是一个注册表，其他包通过声明合并来扩展它；pi\-tui 声明 `tui.*` 操作（`tui/keybindings.ts:3`）。编码智能体合并其 `app.*` 操作（`CA/src/core/keybindings.ts:69`），并从智能体目录中的 `keybindings.json` 读取覆盖项（`CA/src/core/keybindings.ts:380`）；“斜杠命令与键绑定”（原书第197页）列出了这些操作。

## 浮层



`showOverlay(component, options)` 将组件压入浮层栈，并返回一个句柄。浮层在差分比较之前合成进底层行，使用可识别 ANSI 的列切片（`compositeTuiLine`），因此浮层的开销只涉及其覆盖的那些行（`tui/tui.ts:415`）。

|<strong>`OverlayOptions` 字段</strong>|<strong>含义</strong>|
|---|---|
|`width`、`maxHeight`|列数或行数，或百分比字符串，例如 `"50%"`|
|`minWidth`|最小列数|
|`anchor`|`center`（默认）、`top-left`、`top-right`、`bottom-left`、`bottom-right`、`top-center`、`bottom-center`、`left-center`、`right-center`|
|`offsetX`、`offsetY`|相对锚点的偏移|
|`row`、`col`|用绝对位置或百分比位置代替锚点|
|`margin`|到终端边缘的距离，可用一个数值或分别指定各边|
|`visible(termWidth, termHeight)`|仅在其返回 `true` 时渲染|
|`nonCapturing`|显示但不获取键盘焦点|



九个锚点，每种尺寸都可使用百分比。来源：`OverlayOptions`，`tui/tui.ts:243`。返回的 `OverlayHandle` 包含 `hide`、`setHidden`、`isHidden`、`focus`、`unfocus`、`isFocused` 和 `getBounds`（`tui/tui.ts:298`）。



扩展通过 `ctx.ui.custom(factory, { overlay: true, overlayOptions, onHandle })` 使用浮层；它会 resolve 为组件传给 `done` 的值（`CA/src/core/extensions/types.ts:214`）。“扩展：加载与 API”（原书第113页）介绍了 UI 上下文。

## 图像、颜色与原生附加模块



pi\-tui 使用 Kitty 图形协议（`a=T,f=100,q=2`、以 4,096 字符块传送的 base64、范围为 `1–0xffff` 的随机图像 ID）或 iTerm2 的 OSC 1337 绘制图像（`tui/terminal-image.ts:217`；`tui/terminal-image.ts:230`）。是否使用，以及使用哪一种，由环境决定：



<BookFigure id="6.7" />

> 首个匹配项生效，未知终端不会获得图像或超链接支持。`PI_IMAGE_PROTOCOL`（`kitty` 或 `iterm2`）、`PI_TRUE_COLOR` 和 `PI_HYPERLINKS`（`1` 或 `0`）会覆盖检测结果。来源：`tui/terminal-image.ts`（`detectCapabilitiesFromEnvironment`、`detectCapabilities`）。
> 
> 



颜色可以是索引色、sRGB、OKLCH 或 OKHSL 值；`parseColor` 读取 `oklch(…)` 和 `okhsl(…)` 字符串，`mixColors` 默认在 OKLCH 中混色（`tui/colors.ts:121`；`tui/colors.ts:241`）。通过查询 OSC 10、OSC 11 和 16 个调色板条目，并以 DA1 请求收尾，可以读取终端自身的颜色，用于 system 主题（`tui/tui.ts:168`）。



原生附加模块是提交在 `tui/native/<platform>/prebuilds/` 下的预构建 N\-API 二进制文件，因此安装 Pi 时绝不会运行 `node-gyp`：

|<strong>平台</strong>|<strong>二进制文件</strong>|<strong>提供的能力</strong>|
|---|---|---|
|darwin arm64、x64|`darwin-platform.node`（AppKit）|剪贴板文本、图像和文件路径；修饰键状态，将 Apple Terminal 中的 Shift\+Enter 转换为 `\x1b[13;2u`|
|linux x64、arm64|`linux-platform-x11.node`（libxcb）|读取 X11 剪贴板；仅在设置了 `DISPLAY` 时加载；Wayland 回退为 `wl-paste`|
|win32 x64、arm64|`win32-platform.node`|控制台输入设置、修饰键状态、剪贴板|



六个预构建二进制文件，每个平台与架构组合各一个。缺失或失败的附加模块会降级为 `undefined`，调用方随后执行回退（`tui/native-platform.ts:28`）。使用 `npm run build:native:<platform>` 重新构建（`tui/package.json`）。来源：`tui/native/*/README.md` 和 `tui/terminal.ts:11`。

## 内置组件



|<strong>组件</strong>|<strong>说明</strong>|
|---|---|
|`Text`、`TruncatedText`、`Box`、`Spacer`|自动换行文本、单行截断文本、带内边距的框、空行|
|`Input`|单行输入字段|
|`Editor`|2,472 行：多行编辑、100 条提示词历史、剪切环、撤销，以及在 `@`、`#` 和消息开头的 `/` 处自动补全；超过 10 行或 1,000 个字符的粘贴内容会折叠为 `[paste #N +L lines]` 或 `[paste #N C chars]`|
|`Markdown`|使用 `marked` token，按文本和宽度缓存输出，将行内与块级 LaTeX 渲染为 Unicode，支持可插拔的 `highlightCode`|
|`Loader`、`CancellationLoader`|加载旋转指示器，后者可中止|
|`SelectList`、`SettingsList`|键盘驱动的列表；支持模糊搜索的设置列表|
|`Image`|以检测到的协议输出的一行图像|
|`VStack`、`HStack`、`ScrollView`、`MouseRegion`|备用屏幕的布局和鼠标目标区域|



工具函数负责列运算。`visibleWidth`、`truncateToWidth`、`sliceByColumn`、`wrapTextWithAnsi` 和 `fuzzyFilter` 衡量的是终端列数，而非字符串长度（`tui/index.ts:184`）。来源：`tui/index.ts` 和 `tui/components/editor.ts`（历史记录上限、粘贴标记、自动补全触发条件）。



> 对你的意义：
>
> - 用 `visibleWidth()` 测量返回的每一行，并用 `truncateToWidth()` 裁切；Pi 的全屏模式会掩盖这个错误，而 regular 模式会因此崩溃
>
> - 在每一行重新应用样式；渲染器在每行末尾重置 SGR 和 OSC 8
>
> - 按宽度缓存渲染行，并在 `invalidate()` 中清除缓存；`render()` 每帧都会运行
>
> - 对 `tuiMode` 的两种值都进行测试；如果 regular 模式持续全量重绘，设置 `PI_TUI_DEBUG_REDRAW=1`
>
>     

> 来源：`tui/README.md`；`tui/package.json`（依赖、测试、`build:native:*`）。`tui/tui.ts`（`Component`、`Focusable`、`CURSOR_MARKER`、`OverlayOptions`、`OverlayHandle`、`Container`、`SEGMENT_RESET`、`compositeTuiLine`、`TUI`、`TuiBase`：`MIN_RENDER_INTERVAL_MS`、`requestRender`、`scheduleRender`、`handleTerminalInput`、`applyLineResets`、`TERMINAL_COLOR_QUERY`）；`tui/tui-main-screen.ts`（`BoundedTerminalWriter`、`doRender`）；`tui/tui-alt-screen.ts`（`ENTER_ALT_SCREEN`、鼠标模式、`doRender`、`scrollToPrompt`、OSC 52 复制）。`tui/terminal.ts`（Kitty 协商、`modifyOtherKeys`、`resolveEscapeTimeoutMs`）；`tui/keybindings.ts`；`tui/terminal-image.ts`（`detectCapabilitiesFromEnvironment`、Kitty 和 iTerm2 编码器）；`tui/colors.ts`；`tui/native-platform.ts`；`tui/native/*/README.md`；`tui/components/editor.ts`；`tui/components/markdown.ts`。`CA/src/core/settings-manager.ts`（`tuiMode`、`fullscreenExitOutput`）；`CA/src/modes/interactive/tui-renderer.ts`；`CA/src/core/keybindings.ts`；`CA/src/core/extensions/types.ts`（`ExtensionUIContext.custom`）；`research/capture/tui-frames.mjs`；`research/out/tui-frames.txt`。
> 
>
