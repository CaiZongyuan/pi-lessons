---
title: "定义文档"
---

<div class="section-kicker">PI DURABLE / 4.1 · P. 50</div>

# 定义文档

---

> 定义是一个带类型的 token，用于确定文档的种类、版本、所有者和分叉行为；存储记录会记住所有这些选择。
> 
> 

<strong>智能体需要聊天之外的状态：待办清单、计划、用户设置。如果这些状态与对话记录分开存储，崩溃就可能让两者不同步。文档就是这样的状态，与条目在同一次提交中存储。提交是原子保存：其中所有内容要么一并存储，要么全部不存储。</strong>本节结束后，你就能定义一个文档，并选择对话分叉时它如何变化。



<strong>文档是一个随每次提交而变化的 JSON 对象。存储将每次变更保存为一小组编辑，或保存为整个值（基值与增量，原书第56页）。Harness 将自身状态放在五个内置文档中</strong>（内置文档，原书第60页），<strong>而你用同一个函数 `defineDoc()` 定义自己的文档。</strong>



每个对话各自拥有的待办清单；来源：README §Your Own State

```ts
const Todos = defineDoc<{ items: string[] }>({
    kind: "app.todos",
    version: 1,
    scope: "conversation",
    history: "latest", // 也可用 "rewindable"，通过 snapshotAsOf() 读取旧值
    fork: "initial", // 分叉的初始状态："initial"、"current" 或 "asOf"
    initial: () => ({ items: [] }),
});

await root.commit(async (tx) => {
    (await tx.doc(Todos, root.id)).items.push("write docs");
}, context);
```

> 省略了导入行。`"asOf"` 只允许与 `history: "rewindable"` 一起使用；编译器会强制检查。
> 
> 

## 定义就是 token



`defineDoc()` 返回一个 token：携带定义和值类型的普通对象。它只检查 `version` 是否为正整数（`src/documents.ts`）。没有任何注册过程。每次读写都传入token，例如 `tx.doc(Todos, root.id)`；token为这一次调用提供类型、初始值和迁移逻辑（spec §3\.3）。每个token只在一个模块中定义一次，其他地方统一导入。不支持对同一个 `kind` 使用两个不同定义，也没有机制检测这种情况（spec §12）。



|<strong>字段</strong>|<strong>类型</strong>|<strong>决定什么</strong>|
|---|---|---|
|`kind`|`string`|存储名称。它是公共协议的一部分，不能重命名|
|`version`|正整数|值结构的版本；每次变更都会存储它|
|`scope`|`"session"` · `"conversation"` · `"task"`|谁拥有它，以及它存活多久|
|`history`|`"latest"` · `"rewindable"`|仅用于对话文档。旧值是否仍可读取|
|`fork`|`"current"` · `"initial"` · `"asOf"`|仅用于对话文档。分叉副本从什么值开始|
|`initial()`|`() => T`|新文档的值；必须是 JSON 对象|
|`migrate?`|`(value, fromVersion) => T`|读取较旧的已存储值时将其升级（4\.3，原书第56页）|
|`checkpointWhen?`|`(value, ops, info) => boolean`|何时存储整个值，而不是存储编辑（4\.3，原书第56页）|

> 定义字段，来源：`src/types.ts`（`CommonDocDefinition`、`DocumentSemantics`）。
> 
> 

## 作用域、历史与分叉



<strong>作用域决定所有者和生命周期。会话文档由所有对话共享，一直存活到你将其退役。对话文档属于一个对话。任务文档属于一个任务，并在任务结束时自动退役</strong>（spec §3\.1）。<strong>只有对话文档需要选择历史策略和分叉策略，由此形成七种合法组合。</strong>



<BookFigure id="D.4.1" :show-caption="false" />

> 作用域确定所有者和生命周期；只有对话文档需要选择历史策略和分叉策略。来源为 `src/types.ts` 的联合类型 `DocumentSemantics`；分叉结果来自 spec §3\.7。右列列出采用相应组合的内置文档。
> 
> 



<strong>`history: "latest"` 只保留当前值。`"rewindable"` 保留每一次已存储的变更，因此 `snapshotAsOf(token, conversationId, entryId)` 可以返回写入任意条目时的值。代价是存储空间：旧变更永远不会删除</strong>（4\.3，原书第56页）。



<strong>`fork` 决定分叉对话的初始状态</strong>（分叉，原书第43页）。<strong>`"current"` 复制父对话现在的值。`"asOf"` 复制分叉条目时的值，只有可回溯文档还保有该值。`"initial"` 不复制任何内容；分叉第一次调用 `tx.doc()` 时会创建一个全新的文档。</strong>在运行 02 中，父对话的备注文档内容是 `after goodbye`，而在更早条目处创建的分叉以 `after hello` 开始。

## 文档族



文档族是同一个所有者下多个文档共用的定义，通过字符串键彼此区分。可以把它理解为“每个文件一个审阅文档”。`defineDocFamily()` 接受同样的字段，另外加上 `family: true`，其初始化函数接收一个种子：



每个文件一个审阅文档；来源：`docs/pico-v5-chord-usage.md` §2

```js
const ReviewDoc = defineDocFamily<ReviewState, ReviewInput>({
    kind: "app.diff-review", version: 1, family: true, scope: "conversation",
    history: "latest", fork: "current",
    initial: seed => ({ path: seed.path, patch: seed.patch, comments: [] }),
});

await tx.doc(ReviewDoc, conversationId, review.key, review.seed);
```

> 键是地址的一部分，种子不是。种子只在首次创建成员时使用一次，之后便被忽略（spec §12）。采集记录中，针对键 `src/a.ts` 的第二次 `tx.doc()` 调用传入种子 `{"path":"IGNORED"}`，但该成员仍保持 `"path":"src/a.ts"`。要改变成员，就直接编辑它。
> 
> 

## 选择会被存储



<strong>每个已存储的文档都会记录其 `kind`、`scope`、`history` 和 `fork` 策略，因此即使定义它的代码已经缺失，现有数据仍然有明确含义（spec §3\.2）</strong>。每次访问都会将token与该记录核对。如果在代码中把 `fork` 从 `"initial"` 改成 `"current"`，现有文档不会改变，而是无法通过新token读取，并抛出 `Document 4 (app.todos) does not match the supplied definition semantics`（`src/documents.ts`）。



> <strong>这对你意味着什么：</strong>
> 
> - 对描述对话记录的状态，例如计划，使用 `rewindable` \+ `asOf`，这样从旧条目分叉时就能看到对应的计划。示例 27 的 `app.plan` 和内置 `pi.agent` 都采用这种组合
> 
> - 对属于用户的状态，例如草稿，使用 `current`，使分叉取得其当前状态（`docs/pico-v5-chord-usage.md` §2）
> 
> - 对属于单一分支的状态，例如沙箱或花费，使用 `initial`。复制花费计数器会造成重复计算，因此“分叉从零开始”（spec §8\.6）
> 
> - 将 `kind`、`scope`、`history` 和 `fork` 视为永久不变的选择。只有值的结构可以通过 `version` 和 `migrate()` 演进
> 
>
