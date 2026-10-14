---
title: "子智能体"
---

<div class="section-kicker">PI DURABLE / 7.7 · P. 121</div>

# 子智能体

---

> 子智能体是由创建它的工作所拥有的普通对话；所有权和请求 ID 让它可中止、能经受崩溃，无需专门的子智能体 API。
> 
> 

子智能体是第二个智能体，拥有自己的对话记录；你的智能体把工作交给它，例如“研究这个”或“审查那个 diff”。你用对话、所有权和一个工具来构建它。读完本节，你就能编写本包提供的两种模式，并预测中止、等待空闲和崩溃分别会对它们产生什么影响。

## 前台模式



<strong>前台子智能体存在于一次工具调用内部。工具创建一个由自身工具任务拥有的子对话，将工作发给它，等待回答，再返回回答。每个持久化操作都设有标识键，因此崩溃后重跑时能够找到第一次尝试创建的内容。</strong>



subagent 工具，来源：示例 22（节选）

```ts
defineTool({
    name: "subagent", replay: "safe",
    parameters: Type.Object({ task: Type.String() }),
    execute: async (args, api, ctx) => {
    const child = await api.commit(async (tx) => {
    const found = await tx.scanConversations({ ownerTaskId: api.taskId }, 1);
    const existing = found.items[0];
    if (existing !== undefined) return existing.id;
    const created = await tx.createConversation({
    ownership: { kind: "task", taskId: api.taskId },
    });
    await configure(tx, created.id, { extensions: { remove: [Subagent] } });
    return created.id;
    }, ctx);
    await api.details({ conversationId: child }, ctx);
    const handle = (await api.conversation(child, ctx))!;
    const request = { type: "input", content: args.task,
    requestId: `subagent:${api.taskId}` } as const;
    const settled = await (await handle.submit(request, ctx)).wait(ctx);
    // ... 除非 settled 是已回答的 input，否则抛出异常（此处省略）
    const text = await answerText(api, settled.answer, ctx);
    return { content: [{ type: "text", text }] };
    },
})
```

> 运行记录 22 打印出子对话的助手回答 `2, 3, and 5.`，以及父对话的回答 `The subagent says: 2, 3, and 5.`。
> 
> 



每个部分都回答了一个与崩溃有关的问题：

- 先查找，再创建：子对话由工具的任务拥有，因此重跑时使用 `scanConversations({ ownerTaskId })` 找到它，而不会创建第二个

- 在一次提交中创建并配置：子对话一开始得到父对话智能体的副本（创建时的副本，原书第106页）；同一次提交会移除 subagent 扩展，因此子对话不能自行启动子智能体

- 从任务派生请求 ID：重跑时，用相同 ID 调用 `submit()` 会返回第一次提交请求，而不会把工作发送两次。绝不要使用提供商的调用 ID：它“在一个 Session 内并不唯一”，见规范 §7\.3

- details 让界面指向子对话：界面在工具执行更新事件中看到 `{ conversationId }`，并订阅子对话的事件（智能体事件，原书第133页）



<BookFigure id="D.7.9" :show-caption="false" />

> 可安全重放的子智能体调用，按拥有者找到子对话，按请求 ID 找到提交请求。图中是示例 22 的工具和界面步骤。第 1 步是一次提交；第 4 步提交工作，第 5 步是子对话自己的运行，第 6 步是工具的 `wait()`。
> 
> 



`api.conversation()` 返回的句柄只在调用运行期间有效，而且只接受 input。绝不要在 `commit()` 回调中使用它：Session 操作不能嵌套（提交与变更串行队列，原书第29页）。

## 所有权决定中止和空闲



拥有子对话，就意味着它是本次调用工作的一部分。“中止调用会中止子对话”，调用失败也一样；“只有子对话空闲后，父对话才算空闲”，见 README §Abort and Subagents。拥有仍在运行的工作的工具任务，会在这些工作结束之前保持未关闭状态（所有权与结构化并发，原书第76页；中止、故障与孤儿任务，原书第80页）。



<BookFigure id="D.7.10" :show-caption="false" />

> 前台子对话属于调用；后台子对话挂在后台锚点下。箭头从拥有者指向被拥有者。左侧：示例 22。右侧：示例 23，其中锚点立即完成，由 reporter 任务将每条消息交给子对话，再把回答发回父对话。虚线是后台边界：父对话的 Esc 和空闲等待到此为止。
> 
> 

## 后台模式



后台子智能体的生命周期超过父对话的各个轮次：用户之后仍可以给它发消息、停止它或列出它。示例 23 用一个 subagent 工具封装这些操作，提供 spawn、send、stop 和 status 动作。一次 spawn 在同一次提交中记录三件事。锚点任务 `app.subagent-anchor` 是父对话的后台任务；它立即完成，但子对话工作期间会保持未关闭状态。子对话由锚点拥有，不含 subagent 扩展，并有自己的指令。父对话的 `app.subagents` 文档将子智能体名称映射到子对话；父对话分叉时，该文档从空内容开始。



每条消息都经过一个后台 reporter 任务 `app.subagent-reporter`。它向子对话提交消息，等待结果，再将回答作为 follow\-up input 发给父对话。两次提交都使用从 reporter ID 派生的请求 ID，“因此子对话只收到一次消息，父对话也只收到一次回答”，见规范 §7\.3。运行记录 23 在子智能体工作期间关闭 Harness；重启后，父对话仍能收到 `reader: Moby Dick.`。



background 标记是一道墙。父对话的 Esc 和空闲等待止于锚点，因此不会影响子智能体。`abort(context, { background: true })` 仍可以越过这道墙。stop 动作直接中止子对话：当前回答结束，排队消息被丢弃，而子智能体仍可使用，和任何已完成的子智能体一样，见规范 §5\.4。



> <strong>这对你意味着什么：</strong>
> 
> - 为每个持久化操作设置标识键：按拥有者查找子对话，从任务 ID 派生请求 ID
> 
> - 一次回答中的工作用前台模式；用户之后还要继续与之交流的智能体用后台模式
> 
> - 绝不要把子对话的费用报告为工具 usage；那会重复计入（用量与费用，原书第100页）
> 
>
