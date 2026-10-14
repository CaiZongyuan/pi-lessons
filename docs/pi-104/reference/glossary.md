---
title: 术语表
---

<div class="section-kicker">R.7 / REFERENCE</div>

# R\.7 术语表

---

本书使用的 Pi 术语，每个术语单独一条，全文均严格采用这里给出的含义。



智能体目录（Agent directory）：`~/.pi/agent`，或 `PI_CODING_AGENT_DIR` 指定的目录；保存全局设置、身份验证信息、模型、会话和主题。参见“配置、模型与身份验证”（原书第99页）。



`AgentSession`：编码智能体的运行时对象；包装 `Agent`，将每一步持久化到会话文件，并发出 `agent_settled`。参见“`AgentSession`：组装运行时”（原书第61页）。



分支摘要（Branch summary）：一种 `branch_summary` 条目，用于浓缩在树中导航时你离开的路径。参见“压缩与分支摘要”（原书第92页）。



Codemode：`codemode` 工具；模型编写在 QuickJS 中运行的 JavaScript，并通过 `tools.*` 调用其他工具。参见“codemode”（原书第151页）。



压缩（Compaction）：用 `compaction` 条目中的摘要替换较早的上下文，使投影能够放入上下文窗口。参见“压缩与分支摘要”（原书第92页）。



上下文编辑（Context edit）：一种 `context_edit` 条目，无需重写文件，就能改变某条较早条目对模型上下文的贡献。参见“会话：JSONL 树”（原书第86页）。



上下文文件（Context file）：`AGENTS.override.md`、`AGENTS.md` 或 `CLAUDE.md`；无论项目是否受信任，都会加载到系统提示中。参见“上下文文件、技能、模板、主题与包”（原书第106页）。



`DOC ≠ CODE`：本书用于标记随附文档与代码不一致之处的符号；以代码为准。参见“文档与代码的差异”（原书第213页）。



条目（Entry）：会话文件中的一行 JSON，包含 `id`、`parentId`，以及 `message` 或 `model_change` 等类型。参见“会话：JSONL 树”（原书第86页）。



暴露方式（Exposure）：工具可被访问的方式：`direct`、`model-only`、`codemode`、`deferred` 或 `hidden`。参见“扩展、加载与 API”（原书第113页）。



扩展（Extension）：启动时加载的 TypeScript 模块，通过 `ExtensionAPI` 注册工具、命令、提供商和事件处理器。参见“扩展、加载与 API”（原书第113页）。



Faux 提供商（Faux provider）：测试及本书采集工具包使用的脚本化 pi\-ai 提供商（`faux/faux-1`）。参见“一次提示的生命周期”（原书第15页）。



后续消息（Follow\-up）：一种排队的消息，只在智能体原本将要停止时投递。参见“智能体循环”（原书第49页）。



叶节点（Leaf）：会话树中的当前位置，也是下一条条目的父节点。不会存储在文件中。参见“会话：JSONL 树”（原书第86页）。



项目信任（Project trust）：针对每个项目作出的决策，用于控制 `.pi/*` 设置和资源的加载；它不是安全边界。参见“安全模型”（原书第174页）。



投影（Projection）：经过压缩和上下文编辑后，根据通往叶节点的路径计算出的模型可见消息。参见“会话：JSONL 树”（原书第86页）。



可安全重放（Replay\-safe）：以 `replay: "safe"` 注册的 durable 工具，崩溃后可以再次运行；默认是不安全的。参见“实验性技术栈”（原书第166页）。



运行（Run）：智能体的一次 `prompt()` 或 `continue()` 调用，从 `agent_start` 到 `agent_end`。参见“智能体事件与 `Agent` 类”（原书第57页）。



运行模式（Run mode）：驱动 Pi 的方式：interactive、print、JSON 或 RPC。参见“运行模式”（原书第127页）。



会话文件（Session file）：仅追加的 JSONL 文件，保存一个会话的条目树。参见“会话：JSONL 树”（原书第86页）。



稳定结束（Settled）：运行结束后 Pi 不会自行继续的状态：重试、压缩和排队工作均已完成；由 `agent_settled` 标示。参见“从 `prompt()` 到 `agent_settled`”（原书第67页）。



技能（Skill）：包含 `SKILL.md` 的目录，在系统提示中列出，由模型按需加载。参见“上下文文件、技能、模板、主题与包”（原书第106页）。



引导消息（Steering）：一种排队的消息，在当前轮次的工具调用完成后、下一次模型调用之前投递。参见“智能体循环”（原书第49页）。



思考级别（Thinking level）：`off`、`minimal`、`low`、`medium`、`high`、`xhigh`、`max` 之一；默认为 `medium`。参见“配置、模型与身份验证”（原书第99页）。



对话记录系统消息（Transcript system message）：一种系统消息，其 `sections`、`toolsAdded` 和 `toolsRemoved` 会对提示与工具集作增量修改。参见“系统提示词构建”（原书第75页）。



轮次（Turn）：一次助手响应，加上其发出的工具调用及其结果，从 `turn_start` 到 `turn_end`。参见“智能体循环”（原书第49页）。



虚拟模型（Virtual model）：由扩展注册的目录条目，将每个请求路由到一个物理模型。参见“配置、模型与身份验证”（原书第99页）。



传输 API（Wire API）：pi\-ai 支持的十种请求格式之一，例如 `anthropic-messages` 或 `openai-responses`。参见“传输 API 与跨提供商交接”（原书第36页）。
