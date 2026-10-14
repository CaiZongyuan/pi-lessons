---
title: "对话视图与 watch()"
---

<div class="section-kicker">PI DURABLE / 8.2 · P. 129</div>

# 对话视图与 watch()

---

一个值同时包含对话的对话记录和当前正在运行的内容；它只在提交落定时变化，你可以把它作为状态读取，也可以把它作为帧流读取。



聊天 UI 需要两样东西：对话记录，以及当下正在发生的事情，例如模型正在流式输出文本，或工具正在打印输出。对话视图把这两者放进同一个只读值中，这个值只在提交落定时改变。读完本节，你就能渲染它、让远程副本保持同步，并预测缓慢客户端或晚加入的客户端会看到什么。

## 视图包含什么



视图只是一组存储数据：没有任何计算或过滤。下面是捕获中那段对话在运行开始前的视图。



附着时的 watch\.value，来源：research/capture/watch\-ops\.txt：

```json
{
    "conversation": { "id": 1 },
    "entries": [],
    "docs": {
        "pi.agent": { "model": { "provider": "faux", "modelId": "faux-1" } },
        "pi.live": {},
        "pi.inbox": { "items": [] },
        "pi.provider": { "sessionId": "01a10c8d-c25d-72c3-83b8-8dc6cf418d86" },
        "pi.usage": { "models": {}, "tools": {} }
    }
}
```

> 每个文档都折叠成了一行。pi\.live 为 \{\}，因为还没有任何工作在运行。
> 
> 



- `conversation`——对话记录；如果有父级和所有者，也会包含它们（记录与 ID，原书第25页）。

- `entries`——按存储形态呈现的活动对话记录：最新的头指针标记，随后是从该标记的头指针目标到当前尾部之间的非头指针条目。这些是记录，不是模型上下文（从对话记录到模型上下文，原书第40页）。

- `docs`——五个内置文档，以 kind 为键（内置文档，原书第60页）。文档不存在，对应的键也就不存在。



这些 kind 及其字段都是公开协议。你自定义的文档 kind 不包含在视图中；请用 documentState\(\) 观察它们，见 spec §9\.3。

## 视图如何变化



Harness 为每段对话保留一个共享视图。它在首次使用时从存储中构建，并在最后一个观察者离开时丢弃，见 src/harness/view\.ts。每次涉及该对话的提交都会产生一帧：一批把旧视图转变为新视图的操作。



<BookFigure id="D.8.3" :show-caption="false" />

> 一个视图帧先包含提交的文档变更，再包含新条目，所有操作都改写成指向同一个值的路径。来源：src/harness/view\.ts 中的 advance\(\)。第一行来自 research/capture/watch\-ops\.txt 的第3帧；第1帧展示了操作顺序：先设置 pi\.live，再拼接插入条目7。
> 
> 



下面这一帧完成一个工具。五个操作一同落定：槽位的状态和条目、删除其进度的两个操作，以及拼接插入结果条目的操作。



第14帧：一次提交完成一个工具，来源：research/capture/watch\-ops\.txt：

```json
[
    ["s", ["docs", "pi.live", "tools", 0, "status"], "done"],
    ["s", ["docs", "pi.live", "tools", 0, "entry"], 13],
    ["d", ["docs", "pi.live", "tools", 0, "output"]],
    ["d", ["docs", "pi.live", "tools", 0, "details"]],
    ["p", ["entries"], 3, 0, [{ "kind": "pi.tool-result", "id": 13, ... }]]
]
```

> 条目内容已省略。槽位在插入条目13的同一帧中指向它，因此渲染器永远不会看到悬空引用。
> 
> 



按顺序应用一帧的操作；这些操作并不保证是最简集合。一帧没有触及的视图部分仍是同一批对象。只追加条目的帧会保留同一个 docs 对象，因此渲染器可以通过比较引用来跳过工作，见 test/harnessview\.test\.ts。

## 使用视图的两种方式



- <strong>viewState\(\) </strong>一个 Chord 状态，与 documentState\(\) 类似。如果在同一进程中只需要最新值，就使用它，例如每次更新时重新渲染的终端 UI。

- <strong>watch\(\) </strong>一个帧流。要跨进程边界维护副本，就使用它：先发送一次 watch\.value，再按顺序发送每一帧的操作。另一侧通过 applyImmutable\(\) 应用它们。



重新连接时，启动一个新的监听并再次发送其值。示例19加上 \-\-ops 会准确打印这个流：先是视图，随后每次提交输出一行操作。

## 监听契约



watch\(\)、watchDoc\(\) 和 watchTaskGraph\(\) 都返回 WatchHandle，并遵守相同的五条规则：

1. 先读取 watch\.value。它保存起始值。start\(\) 之前提交的帧会在缓冲区中等待。

2. 只调用一次 start\(listener\)。它绝不会同步调用监听器。第二次调用 start\(\)，或在监听结束后调用，都会抛出异常。

3. 每次只运行一个回调。每个回调都收到 \(value, ops, context\)。你的 promise 落定后，下一个回调才会开始。提交绝不会等待你。

4. context 来自该提交，但不带其 abort 信号。监听器启动的工作由你负责中止。

5. 可以安全地重复调用 stop\(\)。它会丢弃待处理的帧，并返回监听结束的方式。已经运行的回调不会被中止。

    

|<strong>WatchEnd\.reason</strong>|<strong>原因</strong>|
|---|---|
|stopped|调用了 stop\(\)|
|cancelled|附着时传入的 Context 被中止|
|session\_closed|Session 开始关闭|
|retired|已交付被退役文档的 null 帧|
|listener\_error|你的监听器抛出了异常；携带 error，且只有这个监听结束|

> 来源：src/types\.ts（WatchEnd）。先出现的原因生效。在任务或工具内部打开的监听也会在那次调用结束时停止（src/harness/scheduler\.ts）。
> 
> 

## 缓慢的使用方与晚加入的使用方



监听绝不会让提交等待。如果你的监听器落后超过100帧，等待中的帧就会被丢弃，并由一帧持有最新值的帧替换。



<BookFigure id="D.8.4" :show-caption="false" />

> 一个监听会保留100个尚未交付的帧；下一次提交会用最新值替换它们全部。正在交付的帧绝不会被替换。规则来源：spec §9\.2 和 src/session/observation\.ts。一个测试在 start\(\) 之前提交了101个条目，最终收到一帧 `[["r", view]]`，其中包含所有101个条目。
> 
> 



替换帧是 `[["r", newest]]`，因此应用操作的代码不需要特殊处理。代价是某些中间状态永远不会被交付。监听显示的是最终到了哪里，而不是每一个步骤。如果你需要每次状态转换，就把每次转换记录为条目，或记录在文档中。要获取单个输入的结果，请使用 Submission\.wait\(\)（提交请求与收件箱，原书第84页）。



晚加入或重新连接的客户端从当前视图开始，不会重放任何内容。示例21在一个每100 ms打印一行的工具运行到一半时附着：

```bash
$ node --conditions=source --experimental-strip-types test/examples/21-late-join.ts
view entries: [ 'pi.user', 'pi.system', 'pi.assistant' ]
view tool slot: running "1\n2\n3\n4\n5\n"
view output now: "1\n2\n3\n4\n5\n"
snapshot tools: [ 'count running' ]
view output now: "1\n2\n3\n4\n5\n6\n"
event output now: "1\n2\n3\n4\n5\n6\n"
```

> 这是 research/runs/21\-late\-join\.txt 的开头几行。视图已经包含已提交的输出；8\.3节（原书第133页）的事件流也从同一状态开始。
> 
> 



晚加入的客户端看到五行，是因为每一行都已提交。工具进度的默认最小提交间隔为100 ms（settings\.progress）。崩溃会丢失自上次成功提交以来的进度；实际间隔可能更长（运行控制与实时文档，原书第88页）。



> <strong>这对你意味着什么：</strong>
> 
> - 同一进程中，只需要最新值：viewState\(\)。远程副本：watch\(\) 配合 applyImmutable\(\)。
> 
> - 在流中的任何位置都要把 `["r", value]` 当作完整替换来处理。
> 
> - 不要把监听当成审计日志。请使用条目、文档或 Submission\.wait\(\)。
> 
> - 重新连接时，再次附着并重新发送 watch\.value。
> 
>
