# Pi Durable 技术手册 — 统一术语表

> 所有 subagent 必须遵守。翻译时把代码标识符、API 名、路径用反引号包裹。

## 保留英文（不译）

这些是代码中的类名 / 模块名 / 格式名，译了会与源码脱节：

`Session`、`Harness`、`Chord`、`SQLite`、`JSONL`、`Storage`（作类名时）、
`Tx`、`JSON`、`TypeScript`、`Node.js`

## 核心术语

| 英文 | 中文 | 备注 |
|---|---|---|
| commit | 提交 | 名词「一次提交」，动词「提交」 |
| Session | Session | 内核类名 |
| Conversation | 会话 | |
| Entry | 条目 | |
| Submission | 提交项 | 与 commit 区分：这是「对象」 |
| Task | 任务 | |
| Run | 运行 | |
| Generation | 生成 | |
| turn | 轮次 | 一次用户输入到回复 |
| tool call | 工具调用 | |
| transcript | 记录（transcript） | 首次出现中英对照，之后用「记录」 |
| document | 文档 | |
| invariant | 不变式 | |
| mutation line | 变更线 | |
| checkpoint | 检查点 | |
| replay | 重放 | |
| crash | 崩溃 | |
| compaction | 压缩 | |
| watcher | 观察者 | |
| scope | 作用域 | |
| base / delta | 基线 / 增量 | |
| idempotency key | 幂等键 | |
| built-in task | 内置任务 | |
| state machine | 状态机 | |
| structured concurrency | 结构化并发 | |
| adoption | 接管 | |
| abort | 中止 | |
| fault | 故障 | |
| orphan | 孤儿 | |
| scheduler | 调度器 | |
| registry | 注册表 | |
| hook | 钩子 | |
| extension | 扩展 | |
| subagent | 子智能体 | |
| prompt | 提示词 | |
| token | token | 不译 |
| budget | 预算 | |
| ledger | 账本 | |
| inbox | 收件箱 | |
| incarnation | 化身 | 文档的一次存续期 |
| lifetime | 存续期 | |
| migration | 迁移 | |
| rewindable | 可回溯的 | |
| handoff | 交接 | |
| head | 头指针 | |
| fork | 分叉 | |
| drain | 排空 | |
| sweep | 清扫 | |
| envelope | 信封 | |
| receipt | 回执 | |
| capability | 能力 | |
| provider | 供应商 | |
| wrapper | 包装器 | |
| conformance | 一致性 | |
| portability | 可移植性 | |
| tier | 层 | |
| agent loop | 智能体循环 | |
| outbox / inbox pattern | 发件箱 / 收件箱模式 | |

## 状态字面值（绝不翻译）

`pending`、`running`、`waiting`、`placed`、`done`、`terminal`、`stopped`、
`aborted`、`orphaned`、`prepare`、`request`、`tools`、`call`、`execute`、
`allSettled`、`toolUse`、`true`、`false`、`null`

这些是代码里真实的存储值，译了会与实际数据不一致。

## 代码标识符（反引号包裹，保持原样）

`submit()`、`commit()`、`fork()`、`abort()`、`createSession()`、`Harness.open()`、
`Harness.root()`、`wait()`、`close()`、`watch()`、`inspect()`、
`pi.user`、`pi.system`、`pi.assistant`、`pi.tool-result`、`pi.live`、
`pi.generation`、`pi.tool`、`pi.compaction`、
`src/session/session.ts`、`src/harness/tool.ts`、
`~/.pi/agent/sessions/`、`research/capture/*.txt`

## 写作风格

1. 简洁、克制、精确 —— 原文是英文技术写作，中文同样不要注水。
2. 不添加原文没有的解释，不删减原文的信息。
3. 简体中文全角标点（，。：；），代码内容与英文术语之间用半角空格。
4. 自然流畅，不要逐词直译。
