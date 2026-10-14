---
title: "内置文档"
---

<div class="section-kicker">PI DURABLE / 4.4 · P. 60</div>

# 内置文档

---

> 五个对话文档保存 Harness 在提交之间需要的信息：智能体是什么、提供商识别到的是谁、什么正在运行、什么正在等待，以及花了多少。
> 
> 

Harness 与你一样，以文档存储自身状态。UI 读取这些文档来显示加载指示、队列或账单。本节结束后，你就能读懂任何对话视图的 `docs` 块，并说明各部分由什么写入。



这五个文档使用与你相同的 `defineDoc()` 定义，并导出各自token：`AgentDoc`、`ProviderDoc`、`LiveDoc`、`InboxDoc` 和 `UsageDoc`（`src/index.ts`）。五者都属于一个对话，随对话创建，并以 `docs[kind]` 的形式出现在其视图中（对话视图，原书第129页）。你自己的文档不会挂载到那里；请用 `watchDoc()` 观察它们。



|<strong>种类</strong>|<strong>保存的内容</strong>|<strong>历史 · 分叉</strong>|<strong>何时写入基值</strong>|<strong>参见</strong>|
|---|---|---|---|---|
|`pi.agent`|模型、工具、指令|`rewindable` · `asOf`|每次变更|7\.2（原书第106页）|
|`pi.provider`|提供商会话 ID|`latest` · `initial`|每次变更|6\.3（原书第91页）|
|`pi.live`|当前正在运行的内容|`latest` · `initial`|没有任何内容正在运行|6\.2（原书第88页）|
|`pi.inbox`|排队中的输入|`latest` · `initial`|收件箱为空|6\.1（原书第84页）|
|`pi.usage`|token 与费用|`latest` · `initial`|每次变更|6\.6（原书第100页）|

> 来源：`src/harness/agent.ts`、`provider.ts`、`live.ts`、`inbox.ts` 和 `usage.ts` 中的定义。五者都是版本 1。
> 
> 



经过一个使用工具的轮次后，根对话的视图包含以下值：



一个轮次之后的 `docs` 块；来源：`research/capture/view-final.json`

```json
"docs": {
    "pi.agent": { "model": { "provider": "faux", "modelId": "faux-1" } },
    "pi.live": {},
    "pi.inbox": { "items": [] },
    "pi.provider": { "sessionId": "01a10c8d-c25d-72c3-83b8-8dc6cf418d86" },
    "pi.usage": { "models": { "faux/faux-1": { "input": 83, "output": 31, ... } }, "tools": {} }
}
```

> 用量条目在两个计数器之后截断。空闲对话的 `pi.live` 为空，收件箱也为空。
> 
> 

## 创建时与分叉时



每个新对话都在创建提交中获得这五个文档。其中四个总是以相同方式开始。只有 `pi.agent` 取决于对话的创建方式（spec §2\.2；`src/harness/agent.ts`，`createAgent`）：

|<strong>文档</strong>|<strong>新建，无所有者</strong>|<strong>新建，由任务拥有</strong>|<strong>在条目 E 处分叉</strong>|
|---|---|---|---|
|`pi.agent`|`{}`|所有者对话的智能体副本|父对话在 E 时的智能体|
|`pi.provider`|新的 UUIDv7，绝不复制|||
|`pi.live`|`{}`：没有运行中的内容|||
|`pi.inbox`|`{ items: [] }`：没有排队中的内容|||
|`pi.usage`|`{ models: {}, tools: {} }`：花费为零|||

> 复制只进行一次：“之后所有者的变更不会传递过来”（spec §12）。
> 
> 

## 各个文档



- `pi.agent`：为此对话选定的内容：模型、思考级别、扩展、工具、指令和工作目录。它只存名称，从不存代码（`src/harness/types.ts`，`AgentState`）。`configure()` 会更改它，工具结果也可以添加或移除工具。名称如何变成运行中的智能体，见每个对话的智能体（原书第106页）。

- `pi.provider`：`{ sessionId }`，即提供商看到的 ID，用于保持提示词缓存亲和性。重置、压缩、模型变更和重新打开都会保留它（spec §2\.2）。在 1\.0\.2 之前存储的对话，会在首次请求时获得一个 ID（`src/harness/provider.ts`；`CHANGELOG.md`）。

- `pi.live`：运行控制与进度。对话忙碌时 `run` 恰好存在；`generation`、`tools` 和 `compactions` 展示正在进行的工作（`src/harness/live.ts`）。

- `pi.inbox`：`{ items }`，按顺序保存等待下一个边界的输入和写入（`src/harness/inbox.ts`）。

- `pi.usage`：本对话的花费，以 `provider/modelId` 和工具名称为键。失败和中止的尝试也计入其中（spec §8\.6）。`Harness.usage()` 汇总所有对话的用量。

- `pi.live` 展示了一条好的检查点规则如何控制存储规模。每当没有内容正在运行时，它都会写入基值，因此编辑最多只累积一个工具轮次：工具运行时的 `pi.live` 记录；





来源：`research/capture/jsonl-dir-midrun/doc-2.jsonl`

```text
seq 6 base {"run":{"taskId":9,"inputs":[8], "tools":[{"callId":"call-1", "name":"count","taskId":12,"status":"pending"}]}}
seq 8 delta ["s","tools",0,"status","running"]
seq 9 delta ["s","tools",0,"output","1\n"]
seq 10 delta ["a","tools",0,"output","2\n3\n"]
```

> 每行的其他字段已省略。Seq 6 时，工具仍处于 `pending`，因此没有任何内容正在运行，规则选择了基值。运行结束后，文件只剩一行：seq 17 的基值 `{}`（`research/capture/jsonl-dir/doc-2.jsonl`）。
> 
> 



> <strong>这对你意味着什么</strong>
> 
> - 根据视图的 `docs` 块构建 UI 状态：`pi.live` 用于加载指示，`pi.inbox` 用于队列，`pi.usage` 用于费用
> 
> - 只通过 `configure()` 更改 `pi.agent`。不要写入另外四个文档；它们由 Harness 管理
> 
> 



> 来源：`src/harness/agent.ts`；`src/harness/provider.ts`；`src/harness/live.ts`；`src/harness/inbox.ts`；`src/harness/usage.ts`；`src/harness/harness.ts`；`src/harness/types.ts`（`AgentState`）；`src/index.ts`；spec §2\.2、§6、§8\.2、§8\.6、§12；`CHANGELOG.md` 1\.0\.2；`research/capture/view-final.json`、`jsonl-dir-midrun/doc-2.jsonl`、`jsonl-dir/doc-2.jsonl`。
> 
>
