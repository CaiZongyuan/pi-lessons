# Pi 技术手册 — 术语表

> 翻译前必读。本表继承 `pi-durable/GLOSSARY.md` 的核心约定，补充 Pi 手册特有条目。
> **目标：两本书术语一致。** 同一个英文词在两本书里必须译成同一个中文。

## 继承自 Pi Durable（保持一致，不要另起译名）

| 英文 | 中文 |
|---|---|
| commit | 提交 |
| Session | Session（保留英文，代码类名） |
| Conversation | 会话 |
| Entry | 条目 |
| Submission | 提交项 |
| Task | 任务 |
| turn | 轮次 |
| transcript | 记录（transcript），首次出现中英对照，之后用「记录」 |
| document | 文档 |
| invariant | 不变式 |
| generation | 生成 |
| replay | 重放 |
| checkpoint | 检查点 |
| compaction | 压缩 |
| crash | 崩溃 |
| scope | 作用域 |
| state | 状态 |
| Extension | 扩展 |
| extension event | 扩展事件 |
| subagent | 子智能体 |
| agent loop | 智能体循环 |
| token | token（不译） |
| prompt | 提示词 |

## Pi 手册特有：保留英文

这些是 Pi 仓库的包名、类名、函数名。它们在原书正文里**常以裸文本出现（无反引号）**，
翻译时保持原样，**不要加书名号或译名**。

**包名**

| 英文 | 说明 |
|---|---|
| `pi-ai` | 模型接入层 |
| `pi-agent-core` | 智能体内核（无状态循环 + Agent 类） |
| `pi-coding-agent` | 编码智能体（产品本体） |
| `pi-tui` | 终端 UI 框架 |
| `pi-mcp` / `pi-codemode` / `pi-env` / `pi-telemetry` / `pi-evals` | 其余内置包 |
| `pi-durable` | 会话与提交内核（即本仓库另一本手册的主题） |
| `pi-test` / `pi-protocol` / `pi-messages` / `pi-client` / `pi-server` / `pi-manifest` | 辅助包 |

**类与接口**

| 英文 | 中文 |
|---|---|
| `AgentSession` | 保留英文（有状态会话封装） |
| `ExtensionContext` / `ExtensionAPI` | 保留英文（`this` 在扩展里的类型） |
| `StreamFn` | 保留英文（流式调用函数类型） |
| `AssistantMessageEvent` | 保留英文（流式事件协议） |
| `AgentEvent` / `SessionEvent` | 保留英文 |
| `EventBus` | 事件总线 |
| `Provider` | 供应商 |
| `ModelRuntime` | 保留英文 |
| `ToolDefinition` / `AgentTool` | 保留英文 |
| `EventStream` | 保留英文 |
| `MemoryStorage` / `JsonlStorage` | 保留英文 |

**函数**

`runLoop`、`runAgentLoop`、`agentLoopContinue`、`streamSimple`、`streamAssistantResponse`、
`prepareRequest`、`executeToolCalls`、`runToolCall`、`convertToLlm`、`transformContext`、
`setDefaultStreamFn`、`getDefaultStreamFn`、`createAgentSession`、`declareToolChanges`、
`runPrintMode`、`runRpcMode`、`resolveAppMode` —— 全部保留英文。

## Pi 手册特有：需要翻译

| 英文 | 中文 | 备注 |
|---|---|---|
| wire API | 通信API | 供应商的具体协议实现 |
| cross-provider hand-off | 跨供应商转交 | |
| chat / vision / classifier API | 对话 / 图像 / 分类 API | |
| streaming event protocol | 流式事件协议 | |
| system prompt | 系统提示词 | |
| tool declaration | 工具声明 | |
| tool call | 工具调用 | |
| compaction | 压缩 | 会话历史压缩 |
| branch summary | 分支摘要 | |
| append-only tree | 仅追加树 | JSONL 会话结构 |
| steer / steering queue | 转向 / 转向队列 | 运行中插话 |
| follow-up queue | 后续队列 | |
| built-in tool | 内置工具 | |
| context file | 上下文文件 | |
| resource | 资源 | skills / prompts / themes / packages 统称 |
| skill | 技能 | |
| theme | 主题 | |
| package | 包 | |
| run mode | 运行模式 | interactive / print / JSON / RPC |
| print mode | 打印模式 | |
| TUI | 保留英文 | |
| RPC | 保留英文 | |
| SDK | 保留英文 | |
| hook | 钩子 | |
| codemode | 保留英文 | |
| QuickJS / WebAssembly | 保留英文 | |
| faux provider | faux 供应商 | 测试用假供应商，faux 不译 |
| security model | 安全模型 | |
| telemetry | 遥测 | |
| eval | 评测 | |
| environment variable | 环境变量 | |
| slash command | 斜杠命令 | |
| keybinding | 键位绑定 | |
| source index | 源码索引 | |
| glossary | 术语表 | |

## 状态字面值（绝不翻译）

`pending`、`running`、`waiting`、`done`、`error`、`aborted`、`terminal`、`stopped`、
`cancelled`、`interrupted`、`ready`、`blocked`、`steer`、`final`、`postTools`、
`terminate`、`addTools`、`recording` —— 都是代码里的真实存储值。

同理，**字段名不译**：`model`、`messages`、`tools`、`context`、`temperature`、
`maxTokens`、`thinking`、`api`、`provider`、`apiKey`、`stopReason`、`usage`、
`toolCallId`、`toolName`、`arguments`、`content`。

## 路径与错误消息

- 路径保留原样：`agent/agent-loop.ts:163`、`ai/types.ts:17`、`src/core/sdk.ts`
- **错误消息字符串保留英文原样**：`Session is closed`、`Unknown record kind`。
  它们是运行时抛出的字面量，译了会与真实报错对不上。
- 版本号、commit hash、URL 不译。

## 源引用格式

原书用「说明 + 路径 + 行号」标注来源，例如：

```
streamSimple in ai/providers/anthropic.ts:180
README §extension-api (p. 113)
```

译文保留路径与行号，说明文字译出，格式用中文括号或保持原样均可。

## 写作风格

1. 简洁、克制、精确 —— 原文是英文技术写作，中文不要注水。
2. 不添加原文没有的解释，不删减原文的信息。
3. 简体中文全角标点（，。：；），代码内容和英文术语之间用半角空格。
4. 自然流畅，不要逐词直译。
5. **表格用 `<table>` 标签**：MinerU 已输出 HTML 表格，翻译时只替换单元格内的文字，保留标签结构。

## 翻译产物格式

每个部分一个文件，译文写在原文下方或替换原文，保持结构对应。推荐做法：

```markdown
## 3.1 智能体循环

<英文原文段落>

<中文译文段落>
```

或者直接就地替换（段落级一一对应）。**不要合并或删减段落**，保持行号可追溯。