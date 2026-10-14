---
title: 一页看懂 monorepo
---

<div class="section-kicker">1.2 / MODEL</div>

# 一页看懂 monorepo

---

仓库有十四个包，<strong>但 `pi` 命令依赖的主链只有三个：`pi-coding-agent`、`pi-agent-core`、`pi-ai`</strong>。其他包中的五个服务于实验性技术栈，从 npm 安装 CLI 时绝不会将它们一起引入。



打开 `packages/` 的读者会面对十四个目录，却没有一张地图。其中一半不在稳定版 CLI 的提示处理路径上。本节列出每个包的规模和职责，根据各自的 `package.json` 将依赖图画成分层结构，并准确说明实验性包如何被排除在 npm 发布包和独立可执行程序之外。

## 十四个包



每个包的版本都是 1\.0\.4，除一个之外，其他均为公开包（`research/out/stats.txt` 的 `§package-lines`）。

|<strong>目录</strong>|<strong>npm 包</strong>|<strong>文件数</strong>|<strong>行数</strong>|<strong>职责</strong>|
|---|---|---|---|---|
|<strong>`packages/coding-agent`</strong><br>|`@earendil-works/pi-coding-agent`|<strong>297</strong>|<strong>77,340</strong><br>|<strong>`pi` CLI：会话、工具、扩展、运行模式、TUI 应用</strong>|
|<strong>`packages/ai`</strong>|<strong>`@earendil-works/pi-ai`</strong><br>|<strong>151</strong>|<strong>23,581</strong>|<strong>提供商与模型、流式协议、身份验证、OAuth</strong>|
|<strong>`packages/durable`</strong><br>|<strong>`@earendil-works/pi-durable`</strong>|<strong>65</strong>|<strong>18,338</strong>|<strong>实验性的持久对话、任务和文档运行时</strong>|
|`packages/tui`|`@earendil-works/pi-tui`|45|17,134|差分渲染的终端 UI 库|
|`packages/chord`<br>|`@earendil-works/chord`<br>|29|8,136|组合运行时：facet、服务、复制状态、RPC|
|`packages/mcp`|`@earendil-works/pi-mcp`|18|2,907|独立 MCP 客户端：stdio 与 Streamable HTTP、OAuth|
|<strong>`packages/agent`</strong><br>|<strong>`@earendil-works/pi-agent-core`</strong>|<strong>6</strong>|<strong>2,281</strong>|<strong>无状态的智能体循环，以及有状态的 `Agent` 封装</strong>|
|`packages/env`|`@earendil-works/pi-env`|6|1,928|通过 SSH 为 Pi Durable 提供远程 `ExecutionEnv`|
|`packages/server`|`@earendil-works/pi-server`|16|1,800|实验性的 Unix 套接字会话路由器|
|`packages/codemode`|`@earendil-works/pi-codemode`|10|1,696|WebAssembly 中的 QuickJS 脚本沙箱|
|`packages/evals`|`@earendil-works/pi-evals`（私有）|5|1,345|`vitest-evals` 运行框架|
|`packages/client`|`@earendil-works/pi-client`|8|1,046|远程 Pi 会话的实验性客户端|
|`packages/telemetry`|`@earendil-works/pi-telemetry`|6|826|厂商中立的 span 契约，不含导出器|
|`packages/protocol`|`@earendil-works/pi-protocol`|8|790|实验性的 CBOR 分帧协议，版本 8|
|合计||670|159,148||



`pi-coding-agent` 占代码量的 48\.6%；它所运行的循环只占 1\.4%。行数统计各包 `src/` 下 `*.ts`、`*.tsx` 和 `*.rs` 文件中的非空行，排除 `*.test.*`、`*.d.ts` 以及生成的 `*.models.ts` 模型目录文件。数据来自提交 `28dcce2` 的 `research/capture/stats.py`。



这套统计规则排除了三块内容，而它们的规模都不小。模型目录存放于 `ai/src/providers/data/` 下的 42 个 JSON 文件，以及生成的 `*.models.ts` 中的 420 行代码。`pi-tui` 在 `tui/native/` 下为六个平台目标提供预构建的原生插件，位于 `src/` 之外。`pi-env` 守护进程是 `env/daemon/` 下的一个 Rust crate，也不在 `src/` 内。表中的职责取自各包的 `description` 字段、README，以及为核实每项声明所检查的一个文件：`PROTOCOL_VERSION = 8`（`protocol/src/protocol.ts:5`）、Unix 套接字监听器（`server/src/transports/unix/listener.ts:57`）、两种 MCP 传输方式（`mcp/src/transports/stdio.ts`），以及 telemetry README 中的“不含导出器”（`telemetry/README.md:11`）。



<BookFigure id="1.2" />

> 各包代码量：CLI 大于其全部依赖包的总和
> 
> 



CLI 的体量比它依赖的全部包加起来还大。蓝色：稳定版 `pi` 命令导入的包。灰色：仅供实验性技术栈或评测运行框架使用的包。数据来自 `research/out/stats.txt`（`§package-lines`）。

## 将依赖图画成分层结构



下图仅使用指向其他 `@earendil-works/*` 包的 `dependencies` 条目。没有包对另一个包声明 peer 或 optional 依赖。按每个包下方的最长依赖链排序，可得到五层。



<BookFigure id="1.3" />

> monorepo 的五层依赖图
> 
> 



<strong>稳定版 CLI 依赖一条由三个包组成的主链。实线：`pi-coding-agent → pi-agent-core → pi-ai`</strong>。蓝色：稳定版 CLI 导入的其他所有包。灰色斜线：只有实验性代码、开发依赖或私有评测运行框架才会触及的包。依据提交 `28dcce2` 中全部十四个 `package.json` 文件的 `dependencies` 与 `devDependencies` 绘制。



图中有三条边并非普通的运行时依赖。`pi-coding-agent` 只在 `devDependencies` 中列出 `pi-client`、`pi-protocol` 和 `pi-server`。`CA/src/experimental/` 下有二十个文件导入 `@earendil-works/pi-durable`，但该包根本没有声明这个依赖；之所以能解析导入，是因为根目录的 `package.json` 将 `packages/` 下每个目录都设为 npm workspace。`chord` 虽然被声明为 CLI 的运行时依赖，却只被 `CA/src/experimental/` 下的文件导入：在 `CA/src/` 中 grep 该包名会找到 26 个文件，全部位于这个目录。除了自身的测试，仓库中没有任何地方导入 `pi-env`。

## 运行时与可执行程序



十三个包在 `engines` 中要求 Node \>=22\.19\.0（`ai/package.json:99`）；私有的 `pi-evals` 没有声明要求。npm 包将 `pi` 安装为 `dist/bundle/cli.js`（`CA/package.json:10`）。`build:binary` 脚本使用 Bun 编译独立可执行程序：`bun build --compile … --outfile dist/pi`（`CA/package.json:43`）。`pi-tui` 的原生终端插件见 pi\-tui（原书第 158 页）。

## `PI_EXPERIMENTAL` 控制什么



一个函数掌握着开关：<strong>实验性功能开关 · `CA/src/core/experimental.ts` · TypeScript</strong>

```ts
export function areExperimentalFeaturesEnabled(): boolean {
  return process.env.PI_EXPERIMENTAL === "1";
}
```



这就是整个文件，共三行。



值必须恰好为 `"1"`；`true` 或 `yes` 都不会开启它。有三处读取这个开关。除非开关开启，并且第一个参数是 `server` 或 `client`，否则 `runExperimentalCommand` 返回 `false`（`CA/src/experimental/commands.ts:86`）。交互式界面的页脚（`CA/src/modes/interactive/components/footer.ts:213`）和首次设置（`CA/src/cli/startup-ui.ts:141`）也会检查它。仅打开这个开关，并不能让 npm 安装版本访问实验性代码，因为包的 `files` 列表排除了 `!dist/client`、`!dist/experimental` 和 `!dist/cli/experimental`（`CA/package.json:31`）。services README 明确说明了这一意图：“server、client 和 experimental 包子路径不会包含在 npm 包和独立可执行程序中”（`CA/src/experimental/services/README.md`）。实验性入口点是 `CA/src/experimental/cli.ts`，`./pi-test.sh` 会从源码检出版本中运行它（`pi-test.sh`）；从该入口开始的路径是“实验性技术栈”（原书第 166 页）的主题。



> <strong>经验法则</strong>
> 
> 如果正在阅读的文件导入了 `pi-durable`、`pi-server`、`pi-client`、`pi-protocol` 或 `chord`，它就不在稳定版 `pi` 命令的执行路径上。<strong>研究稳定版 CLI 时，先读 `pi-coding-agent`、`pi-agent-core` 和 `pi-ai`；</strong>问题涉及屏幕、MCP 或 codemode 时，再读 `pi-tui`、`pi-mcp` 和 `pi-codemode`。
> 
> 



> 来源：`packages/*/package.json`（`name`、`version`、`private`、`dependencies`、`devDependencies`、`engines`、`description`）；`CA/package.json`（`bin`、`files`、`build:binary`）；`package.json`（`workspaces`）；`CA/src/core/experimental.ts`；`CA/src/experimental/commands.ts`（`runExperimentalCommand`）；`CA/src/experimental/cli.ts`；`CA/src/cli/startup-ui.ts`（`shouldRunFirstTimeSetup`）；`CA/src/experimental/services/README.md`；`pi-test.sh`；`protocol/src/protocol.ts`（`PROTOCOL_VERSION`）；`server/src/transports/unix/listener.ts`；`mcp/src/transports/`；`telemetry/README.md`；`research/capture/stats.py`；`research/out/stats.txt`（`§package-lines`）。
> 
>
