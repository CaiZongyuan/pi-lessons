---
title: "分叉与有所有者的对话"
---

<div class="section-kicker">PI DURABLE / 3.3 · P. 43</div>

# 分叉与有所有者的对话

---

> 分叉在某个条目处分出一条对话支路，并共享此前的历史；有所有者的对话属于某个任务，因此中止该任务也会影响到它。
> 
> 

<strong>用户希望回到早先的消息，尝试另一种做法，同时保留原有对话。智能体希望为子智能体开启旁支对话。这两种情况都会产生新对话。</strong>本节结束后，你就能创建这两种对话，并预测它们能看到什么。

## 获得对话的四种方式



|<strong>调用</strong>|<strong>得到的结果</strong>|
|---|---|
|`harness.root(context, options)`|对话 1，首次调用时创建；后续调用不写入任何内容|
|`harness.createConversation(options, context)`|一个全新的空对话；必须指定所有权|
|`conversation.fork(at, options, context)`|一条共享截至条目 `at` 的历史的分支|
|`tx.createConversation()`、`tx.forkConversation()`|同样的操作，但位于任意提交内，例如工具的提交|

> 来源：spec §2\.2 和 `src/harness/harness.ts`。选项为 `ownership`、`agent` 和 `init`。
> 
> 



<strong>创建过程只需一次提交。它会写入对话、五个内置文档（内置文档，原书第60页）、任何智能体设置，以及你的 `init(tx, id)` 写入的全部内容。</strong>不会出现创建一半的状态（spec §2\.2）。



<strong>创建对话和发送第一条消息是两个独立调用。</strong>如果进程可能在两者之间崩溃，就在 `init` 中写入一个键，以便再次找到该对话，然后携带请求 ID 提交消息，避免重试时重复发送（spec §2\.2）。

## 分叉



分叉是一个新对话，从父对话的某个条目 E 开始。它的记录存有 `parent: { conversationId, at }`。没有任何内容被复制。分叉能看到自己的条目，然后看到父对话截至 E 的条目，再看到祖父对话截至其相应上限的条目，依此类推（spec §2\.1、§3\.7）。每个祖先对话的条目都按沿途最小的上限截断。



```bash
$ node --conditions=source --experimental-strip-types test/capture-p23-context.ts
root 1: #9:"three" #8:"two" #7:"one"
fork 10: #16:"fork-only" #8:"two" #7:"one"
grand 17: #23:"grandchild-only" #7:"one"
fork2 24: #16:"fork-only" #8:"two" #7:"one"
grand.fork(#9) -> Entry 9 is not visible from conversation 17
```

> 来源：`research/capture/extra-p23/forks.txt`；条目按从新到旧排列。对话 17 看不到 \#9，因此不能在那里分叉。
> 
> 



头指针也会跨越分叉。压缩之后创建的分叉，其上下文会从父对话的摘要开始（`research/capture/context.txt`，阶段 6）。在工具调用与结果之间创建的分叉，其上下文会得到一条错误结果（上下文推导，原书第40页）。



<BookFigure id="D.3.3" :show-caption="false" />

> 分叉能看到自己的条目，以及每个祖先截至 `parent.at` 上限的条目。对话 32 没有父对话；它由位于对话 1 中的任务 31 拥有。对话、条目与可见范围来自 `research/capture/extra-p23/forks.txt`。
> 
> 

## 分叉继承什么



|<strong>状态</strong>|<strong>分叉中的情况</strong>|
|---|---|
|条目|共享截至 E 的条目，绝不复制|
|`fork: "asOf"` 的文档|父对话在 E 时的值的副本|
|`fork: "current"` 的文档|父对话当前值的副本|
|`fork: "initial"` 的文档|不继承；首次使用时全新创建|
|`pi.agent`|父对话在 E 时的智能体设置|
|`pi.provider`|一个新的提供商会话 ID，绝不使用父对话的 ID|
|实时状态、收件箱、用量|为空|
|任务和任务文档|绝不复制|
|Session 文档|共享，不复制|



来源：spec §2\.2、§3\.7。文档的分叉策略见定义文档（原书第50页）。



采集记录展示了 `asOf` 规则。写入 \#8 时，根对话的智能体指令为 `"v1: be brief"`，后来变成了 `"v2: be thorough"`。在 \#8 处创建的分叉从 v1 开始，并拥有自己的提供商会话 ID（`research/capture/extra-p23/forks.txt`）。

## 有所有者的对话



有所有者的对话属于某个任务。创建时使用 `{ kind: "task", taskId }` 所有权；记录随后保存 `owner: { conversationId, taskId }`。任务也可以在同一次提交中创建：



在一次提交中创建任务及其拥有的对话；来源：`test/capture-p23-context.ts`

```js
const owned = await harness.commit(async (tx) => {
    const taskId = await tx.createTask(Supervisor, null, {
        ownership: { kind: "conversation" }, conversationId: root.id, background: true,
    });
    const child = await tx.createConversation({ ownership: { kind: "task", taskId } });
    return { taskId, child };
}, context);
// child: {"id":32,"owner":{"conversationId":1,"taskId":31}}
```

> 注释是 `research/capture/extra-p23/forks.txt` 中采集到的输出。
> 
> 



所有权描述的是工作关系，而不是历史关系。有所有者的对话最初为空。它会一次性复制所有者所在对话的智能体设置；之后所有者对话中的变更不会传递过来（spec §2\.2）。所有权边会将两者关联起来，以支持中止和空闲等待。中止任务会触及该对话中的非后台工作，而等待任务空闲也会涵盖这些工作（所有权与结构化并发，原书第76页）。子智能体正是建立在这一机制之上的（子智能体，原书第121页）。



所有者必须仍处于存活状态。正在完成、已经完成或正在被中止的任务不能再获得新对话，即使是在同一次提交中也不行（spec §3\.3）。



> <strong>这对你意味着什么：</strong>
> 
> - 要“从这里重新尝试”，就使用分叉。原对话不受影响
> 
> - 对于任务停止时也应该停止的工作，例如子智能体，使用有所有者的对话
> 
> - 有意识地选择每个文档的分叉策略；它决定分支的初始状态
> 
> 



> 来源：spec §2、§2\.1、§2\.2、§3\.3、§3\.7；`src/harness/harness.ts`（`root`、`createConversation`、`fork`）；`src/harness/agent.ts`（`createAgent`）；`src/session/transaction.ts`；`src/session/forks.ts`；示例 03；运行 09；`research/capture/extra-p23/forks.txt`；`research/capture/context.txt`。
> 
>
