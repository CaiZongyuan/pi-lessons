---
title: 来源与版本
---

<div class="section-kicker">R.8 / REFERENCE</div>

# R\.8 来源与版本

---

本书核对过的所有资料，以及核对时采用的版本；后续提交可能改变任何行号，也可能改变某些默认值。



本书每一项陈述都可追溯到下列某个来源。表格按权威性顺序列出读取各来源时的版本及其用途。表后的列表列出了本版未能确认、因而不作断言的事项。



|来源|版本|用途|
|---|---|---|
|`earendil-works/pi` 单体仓库，`packages/*/src/**`|提交 `28dcce2ba45ce4a9efeb0f5b686f0be830fd89b9`，2026\-10\-05 21:23:02 \+0200|每个类型、默认值、字段名、事件、错误消息和行为；每个“文件:行号”引用|
|npm 包 `@earendil-works/pi-*`（14 个工作区包；`pi-evals` 为私有包）|1\.0\.4，来自该提交中各包的 `package.json`|包名与版本；封面上的版次信息|
|随附文档：`packages/coding-agent/docs/*.md`、各包的 README|同一提交|作者所呈现的公开接口；“文档与代码的差异”（原书第213页）中的每项 `DOC ≠ CODE` 对比|
|测试与示例：`packages/*/test/**`、`packages/coding-agent/examples/**`|同一提交|各节引用它们时涉及的边界行为及可运行扩展代码|
|Node\.js|采集运行使用 v26\.10\.0；根目录和 `pi-coding-agent` 的 `package.json` 声明为 `"node": ">=22.19.0"`|针对构建后的 `dist/` 运行采集工具包|
|采集工具包：`research/capture/one-turn.mjs` → `research/out/one-turn.txt`|本书自带，针对固定版本的构建运行|`AgentSession` 事件流（29 个事件），以及 faux 提供商单个轮次的会话 JSONL|
|采集工具包：`research/capture/stats.py` → `research/out/stats.txt`|本书自带，采用固定提交|包行数、提供商目录、API 文件、扩展示例|
|采集工具包：`research/capture/` 中按章节划分的脚本（`agent-loop-queues`、`auth-cost-retries-cost`、`built-in-tools-edit`、`codemode-sandbox`、`rpc-and-sdk-*`、`sessions-tree`、`streaming-protocol-events`、`tui-frames`、`wire-apis-transform`）|本书自带，离线运行，除 ID 与时间戳外均为确定性结果|`research/out/` 中的输出，由与脚本同名的章节展示|
|《Pi 技术手册》，`source/user/Pi-Technical-Manual.pdf`|草稿版，100 页，页首标注 `28dcce2 · v1.0.4`|本版重新设计样式所依据的草稿：其结构与知识；每项保留的陈述均已对照检出版本重新核实|



一个提交、一个版本、一套采集工具包。提取到 `research/original/` 的草稿文本与页面图像，仅用于确定需要验证的内容。



## 未验证，因此不作断言的事项



内置思考预算。`thinkingBudgets` 会回退到各提供商的预算，但未追踪这些预算；“设置参考”（原书第202页）没有给出数值。



某些显示设置的效果。对 `shellCommandPrefix`、`fullscreenExitOutput`、`collapseChangelog` 以及 `images.autoResize` 的 2000 × 2000 限制的描述，依据的是声明与文档，而非使用这些设置的代码。



`PI_TUI_DEBUG_REDRAW` 写入的位置。日志会写入 TUI 的日志目录；未追踪该目录是如何选定的。



TypeScript 编译器对差异 9 的报错。“文档与代码的差异”（原书第213页）说明，文档中的模块扩充对任何模块都不起作用；未采集准确的编译器诊断信息。



Codemode 启动时间。“codemode”（原书第151页）中沙箱启动“约 20 ms”的说法引自包的 README；本版未对其计时。



真实提供商的耗时。所有采集运行都使用 faux 提供商，它会在毫秒级时间内流式输出；本书没有任何耗时数据描述联网模型。



草稿版的行数。草稿版各包的行数（例如 pi\-ai 的 26\.4k）采用了未知的统计方法；“一页看懂单体仓库”（原书第11页）用 `stats.py` 的统计结果替换了这些数字，没有重新列出旧数据。



Windows 行为。Windows 专用路径（PowerShell、notepad、自更新隔离）是从代码中读取的；没有任何采集实际执行过这些路径。
