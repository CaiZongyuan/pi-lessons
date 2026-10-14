---
title: "来源"
---

<div class="section-kicker">PI DURABLE / R.6 · P. 187</div>

# 来源



本书引用的全部内容，以及阅读时对应的提交。



仓库为 `github.com/earendil-works/pi`，包位于 `packages/durable`，版本为 `@earendil-works/pi-durable 1.0.3`，提交为 `5b6c792b424e73edefbfa558b901bcd64788dad2`（2026\-10\-05）。除以 `research/` 开头的路径外，其余路径均相对于 `packages/durable/`。



## 文档与源码



|路径|引用形式|内容|
|---|---|---|
|`docs/spec.md`|spec §N|规范性说明（内部名称为 Pico5）|
|`README.md`|README §X|包使用指南|
|`CHANGELOG.md`|CHANGELOG 1\.0\.N|1\.0\.0 至 1\.0\.3 各版本|
|`docs/pico-v5-handoff.md`|handoff|实现计划|
|`docs/pico-v5-chord-usage.md`|chord usage|该包如何使用 Chord|
|`docs/chord-delta-findings.md`|delta findings|Chord 增量笔记|
|`src/index.ts, src/types.ts, src/errors.ts`|`src/...`|公开接口、记录和存储类型、错误|
|`src/session/`|`src/session/...`|Session、事务、分叉、观察|
|`src/harness/`|`src/harness/...`|Harness、调度器、内置任务和文档、视图、事件|
|`src/storage/`|`src/storage/...`|Memory、SQLite 和 JSONL 后端|
|`src/env/, src/tools/`|`src/env/..., src/tools/...`|执行环境；内置工具|
|`src/testing/`|`src/testing/...`|存储与环境一致性测试套件|
|`test/*.test.ts`|`test/...`|行为测试|
|`research/pi/packages/coding-agent/docs/`|`session-format.md, sessions.md, how-pi-works.md`|原版 Pi 会话格式|



## 示例与运行结果



|示例|展示内容|
|---|---|
|ex 00–05|Session 层：对话、文档、分叉、有所有者的对话、Chord 状态、监听|
|ex 06–11|Harness、配置、对话、上下文、注册表重新加载、扩展状态|
|ex 12–13|一个持久化任务；关闭、重新打开并继续|
|ex 14–19|聊天、系统提示词、真实模型、编码工具、打印模式、JSON 模式|
|ex 20–21|繁忙期间的收件箱；晚加入|
|ex 22–24|前台与后台子智能体；子任务|
|ex 25|压缩：后台、手动、溢出|
|ex 26–31|编码智能体、计划模式、审查者、每段对话的沙箱、工具覆盖、重新加载和重启|



示例位于 `test/examples/NN-*.ts`；采集到的输出位于 `research/runs/NN-*.txt`（引用为 run NN）。示例 16 需要真实模型，没有对应的运行文件。其余示例全部使用 pi\-ai 的 `faux` 提供商。



## 采集工具



|文件|内容|
|---|---|
|`README.md, NOTES.md`|每个产物如何生成；观察到的行为与文档的差异|
|`sqlite-schema.sql, sqlite-rows*.txt, sqlite-commits.txt`|SQLite 模式与一个轮次结束后的每一行、运行中的行、提交日志|
|`jsonl-dir/, jsonl-dir-midrun/, jsonl-*.txt`|一个轮次结束后及运行期间的 JSONL 目录、清单、提交日志|
|`crash-README.md, crash-*.txt`|在两次工具调用期间发送 `SIGKILL`，然后重新打开并恢复|
|`task-transitions.txt, task-graph.txt`|每次任务记录状态转变；任务图帧|
|`watch-ops.txt, agent-events.txt, view-final.json`|视图监听帧、智能体事件批次、最终视图|
|`inbox-steps.txt, context.txt`|繁忙期间的收件箱和提交请求；原始条目与模型上下文的对照|
|`scripts/`|采集脚本，即 `test/capture/*.ts` 的副本|



全部位于 `research/capture/`，使用 Node v24\.13\.0，在同一个提交上生成。`extra-p*/` 目录保存为各个部分额外进行的采集。



## 网络来源



|来源|用途|
|---|---|
|Earendil Engineering，“Pi Durable”，2026 年 10 月 1 日，https://earendil\.com/posts/pi\-durable/|只用于说明动机；绝不用作 API 事实依据|



来源：`package.json`；README §Examples、§Design Documents；`research/capture/README.md`；`research/runs/`。
