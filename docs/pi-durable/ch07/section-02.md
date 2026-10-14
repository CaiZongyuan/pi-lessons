---
title: "每个对话的智能体"
---

<div class="section-kicker">PI DURABLE / 7.2 · P. 106</div>

# 每个对话的智能体

---

> 每个对话都把自己的选择存储为名称；Harness 每次需要它们时，再将这些名称转换为实际工具和提示词区段。
> 
> 

不同对话需要不同配置：主聊天得到全部工具，只读审查者得到两个工具，子智能体有自己的指令。对话的 agent 就是这套配置：模型、思考级别、扩展、工具、提示词区段、指令和工作目录。读完本节，你就能配置一个智能体，并准确预测模型会获得哪些工具。

## 存储的选择与解析后的智能体



智能体以两种形式存在。存储形式 `AgentState` 位于对话的 `pi.agent` 文档中，只保存名称。从未设置过的字段遵循宿主默认值。解析形式 `Agent` 则是 Harness 每次需要真实对象时，根据存储的名称、当前注册表和宿主设置构建的结果。存储的文档会随对话一起分叉和回退（内置文档，原书第60页）。



|<strong>字段</strong>|<strong>存储形式</strong>|<strong>未设置时</strong>|
|---|---|---|
|`model`|`{ provider, modelId }`|没有模型；请求以 `no_model` 失败|
|`thinkingLevel`|一个 pi\-ai 级别|`"off"`|
|`extensions`|名称列表，或 `{ add?, remove? }`|宿主默认值：全部已安装扩展|
|`tools`|名称列表，或 `{ remove }`|所选扩展的全部工具|
|`instructions`|字符串|无；设置后渲染为最后一个提示词区段|
|`cwd`|路径|无；传给宿主的环境工厂（9\.5，原书第155页）|

> `AgentState` 及其默认值，见 `src/harness/types.ts` 和 `src/harness/agent.ts` 中的 `resolveAgent()`。
> 
> 



`Conversation.configure(change, context)` 编辑存储的智能体。每个字段都遵循一条规则：“给定字段替换已存储值，null 清除它，undefined 不作更改”，见 `src/harness/agent.ts`。你可以传入扩展对象和工具对象；它们会以名称存储。独立函数 `configure(tx, id, change)` 在更大的提交中执行同样操作；提交是一次原子保存，其中的一切要么一起存储，要么完全不存储。示例 7 展示了每次调用会存储什么。



配置后再读回，来源：示例 07 · `research/runs/07-configuration.txt`

```ts
// 默认工具：['read', 'write', 'grep']

await root.configure({
    model: { provider: "anthropic", modelId: "claude-sonnet-4-5" },
    thinkingLevel: "high",
    tools: [write, read], // 传入对象，存储名称
}, context);
// 存储结果：{ model: {...}, thinkingLevel: 'high', tools: ['write', 'read'] }

await root.configure({ extensions: { remove: [Search] }, tools: null }, context);
// 去掉 search 后：['read', 'write']

await root.configure({ extensions: [Files, Search] }, context);
registry.uninstall(Files); // files 卸载后：['grep']
registry.install(Files); // files 重新安装后：['read', 'write', 'grep']
```



由于字段会整体替换，`{ remove }` 列表不会累加。先移除 edit，再移除 bash，最终只会移除 bash：“edit 会再次提供给模型”，见规范 §2\.2。界面的开关必须读取当前列表，再写入新列表。配置不会向对话记录追加任何内容；下一个模型请求会采用这项更改。

## 从名称到工具



解析将存储的名称转换为请求使用的工具和区段。每次都执行相同的四步，不写入任何内容：

1. 选择扩展。若存储的是列表，就严格按列表顺序选择其中的名称。否则，从宿主默认值开始（按安装顺序排列的所有已安装扩展），再应用 add 和 remove。未安装的名称会被跳过

2. 按扩展顺序收集工具。后面出现的同名工具会原位替换前面的工具

3. 将包装器应用于当前占用目标名称的工具或区段

4. 过滤工具。若存储的是列表，就严格按列表顺序只保留这些名称；`{ remove }` 则删除指定名称。区段以同样的方式收集，instructions 放在最后



<BookFigure id="D.7.3" :show-caption="false" />

> 解析先按扩展顺序收集工具，原位替换同名项，包装胜出的工具，最后过滤。扩展、描述和过滤器来自 `test/harness-registry.test.ts`。最后一行展示存储的过滤器从上一行保留了哪些内容。
> 
> 



两种失败会被刻意安静处理。若包装器抛出异常或重命名目标，本次解析就移除该工具，并向 `HarnessOptions.onReport` 报告；调用它时会得到 `tool_unavailable` 结果。如果包装器的目标没有被选中，它就什么也不做，因此没有 bash 时也可以安全使用计时包装器，见规范 §7\.1。

## 更改何时生效



Harness 在每次决策时重新解析智能体，而不是每次运行只解析一次：“每个读取方在每次决策时解析一次”，见规范 §7\.1。宿主设置也一样。`HarnessOptions.settings` 保存 Harness 级别的策略，包括默认选择、重试、压缩、工具执行模式和队列模式。它从不被复制或存储，因此一个带 getter 的 settings 对象“无需向 Session 写入，就能跟随用户偏好”，见规范 §2\.2。默认值参见“设置与默认值”（原书第180页）。



|<strong>谁读取</strong>|<strong>读取什么</strong>|<strong>何时读取</strong>|
|---|---|---|
|模型请求|模型、工具、提示词、流式选项|准备该请求时读取一次|
|工具调用|被调用工具的代码|调用开始时，以及恢复时再次读取|
|任意任务阶段|钩子|每个阶段一次，从该阶段的注册表快照读取|
|工具轮次|并行或顺序执行|每轮一次|
|输入边界|引导与后续消息的队列模式|每个边界|
|工具与提示词区段|当前 cwd 的环境|每次使用时|

> 精简自规范 §7\.1 的“谁解析什么，以及何时解析”。
> 
> 



因此，在一个轮次中途作出的更改，会在下一个模型请求中生效。模型已经发起的调用，会在实际执行时解析其工具。如果期间移除了该工具，调用会得到 `tool_unavailable`；如果修改了 cwd，调用会看到新目录，见 README §Per\-Conversation Agent。

## 创建时的副本



新对话一开始，要么拥有某个智能体的副本，要么什么都没有，见 `src/harness/agent.ts` 中的 `createAgent()`：

- 分叉：父对话在分叉点时的智能体（分叉，原书第43页）

- 任务拥有的对话：复制拥有它的任务所属对话的每个已存储字段，包括 instructions。之后拥有者的更改不会传递给它

- 无拥有者的对话：空对象 `{}`；每个字段都遵循宿主设置

    

随后，`root()`、`createConversation()` 和 `fork()` 的 agent 选项会在同一次提交中应用其更改。



<aside class="manual-callout callout-warning durable-callout" role="note" data-source-page="108">

<strong>复制的列表</strong>

`{ add, remove }`“始终编辑宿主的默认选择”，绝不编辑复制的列表。某个子对话复制了列表 `["a", "b"]`，随后接收到 `{ remove: [b] }`，最终得到的是宿主默认值去掉 b，而不是 `["a"]`。要编辑复制的列表，应读取解析后智能体的 extensions，再写入新列表，见规范 §2\.2、§12。

</aside>




> <strong>这对你意味着什么：</strong>
> 
> - 对话应遵循宿主设置时，就让字段保持未设置；只有需要不同配置时才设置
> 
> - 对话需要精确、稳定的工具集时，例如审查者，应使用存储的列表
> 
> - 配置更改会在下一个模型请求生效，不会在请求中途生效
> 
> 



> 来源：`src/harness/agent.ts`；`src/harness/types.ts`（`AgentState`、`AgentChange`、`Agent`、`HarnessSettings`、`Settings`）；`src/harness/scheduler.ts`；规范 §2\.2、§7\.1、§12；README §Per\-Conversation Agent、§Settings；示例 07 和运行记录 07；`test/harness-registry.test.ts`
> 
>
