---
title: "提交请求与收件箱"
---

<div class="section-kicker">PI DURABLE / 6.1 · P. 84</div>

# 提交请求与收件箱

---

> 每条消息都会在发送的一刻提交；忙碌的对话会将其排队，而边界决定它何时进入对话记录。
> 
> 

用户在智能体仍在回答第一个问题时，又输入了第二条消息。它应该打断当前回答、等待，还是被拒绝？如果进程一秒钟后就崩溃了，这条消息会丢失吗？Pi Durable 用一条规则回答这些问题：<strong>在对消息做任何其他处理之前，先提交它。提交是一次原子保存：其中的一切要么一起存储，要么完全不存储。</strong>读完本节，你就能预测任意时刻发送的消息会发生什么，并选择忙碌的对话应该如何处理它。

## 两种提交请求



提交请求是你交给某个对话的内容的持久化记录，共有两种。input 是用户消息；它可能启动一次运行，也就是用于回答该消息的模型调用和工具调用。write 向对话记录添加一个条目，但不向模型提问，例如应用添加的一条备注。



`Conversation.submit()` 在一次提交中写入记录，并返回一个 `Submission` 句柄。这个句柄提供 `status()`、`wait()` 和 `abort()`。



`SubmissionDraft`，来源：`src/harness/types.ts`

```ts
type SubmissionDraft = {requestId?: string} & (
    | { type: "input"; content: UserInput;
    whenBusy?: "steer" | "followUp" | "reject" }
    | { type: "write"; entry: EntryDraft }
);
```

> 此处为简化版本：源码将每个字段都标记为 `readonly`，还添加了 `never` 字段，确保两个分支彼此区分。
> 
> 

## 提交请求的去向



提交请求处于四种状态之一。等待时为 `queued`。input 的消息进入对话记录，并有运行正在回答它时，就变为 `placed`。当它有了对应条目，而且对于 input 来说还有了回答时，就变为 `done`。如果结束时仍没有回答，则为 `unanswered`，并由一个原因说明为什么。`wait()` 仅在 `done` 或 `unanswered` 时完成。



<BookFigure id="D.6.1" :show-caption="false" />

> 提交请求处于排队、放入或最终结算状态；只有 input 才会处于 `placed` 状态。来源：`src/harness/submissions.ts`、`inbox.ts` 和 `live.ts`；原因取自规范 §6 和 §8\.3。玫红色箭头表示结束时没有回答。
> 
> 



它走哪条路径，取决于一个问题：对话忙碌吗？只要有一次运行正在进行，对话就是忙碌的（运行控制，原书第88页）。

|<strong>提交时机</strong>|<strong>会发生什么</strong>|
|---|---|
|空闲，且没有排队内容|input 被放入并启动一次运行；write 被追加并变为 `done`|
|忙碌，或已有其他条目排队|提交请求进入收件箱排队|
|忙碌，且指定 `whenBusy: "reject"`|不写入任何内容；`submit()` 抛出 `ConversationBusy`|
|`requestId` 已被使用|不写入任何内容；返回已有的提交请求|

> 来源：`src/harness/submissions.ts` 和规范 §6 的接纳规则表。唯一的例外是会撤销重置效果的 write；参见下文“细节”。
> 
> 



`requestId` 检查让重试变得安全。如果一次提交超时，或者进程重启，使用同一个 ID 再发送一次，就会得到同一个提交请求，而不是第二份副本。这个 ID 的作用域限于一个对话。

## 收件箱



排队的提交请求在 `pi.inbox` 中等待。这是一个小型内置文档，每个对话各有一个（内置文档，原书第60页）；分叉时会得到一个空收件箱。每个条目都有一个 mode，说明它可以在何时进入对话记录：

- `steer`：“当前工具调用一完成，就告诉智能体。”消息加入正在进行的运行

- `followUp`：“当前回答结束后再处理。”消息启动下一次运行。这是 `whenBusy` 的默认值

- `write`：排队的写入。它会在下一次机会进入对话记录，先于任何用户消息

## 边界：排队条目何时进入对话记录



边界是排队条目进入对话记录的那次提交。有两种边界。如果运行还要继续，一轮工具调用之后会执行 `postTools` 边界。运行成功结束时会执行 `final` 边界。

|<strong>边界</strong>|<strong>WRITE</strong>|<strong>STEER</strong>|<strong>FOLLOW\-UP</strong>|<strong>它接收的用户消息</strong>|
|---|---|---|---|---|
|`postTools`|全部|第一条|不接收|加入当前运行|
|`final`|全部|第一条|第一条|启动同一次新运行|

> 规范 §6；`src/harness/inbox.ts`。将 `steeringMode` 或 `followUpMode` 设为 `"all"`，便会接收该模式下的所有条目，而不仅是第一条（两者均默认为 `"one-at-a-time"`）。排队的重置会将 `postTools` 边界变为 `final` 边界（参见下文“细节”）。向仍有条目等待的空闲对话提交内容时，新提交会排在它们后面，并立即执行一次 `final` 边界（`src/harness/submissions.ts`）。
> 
> 



边界先放入 write，再放入用户消息；每类内部均按提交顺序处理。因此，在重置或压缩摘要之前排队的消息，会在它们之后进入对话记录，模型在新的上下文中读取它。



<BookFigure id="D.6.2" :show-caption="false" />

> `postTools` 边界接收 write 和 steer；只有 `final` 边界接收 follow\-up。一个工具调用使第一次运行保持未完成状态，与此同时，后续消息、引导消息和一条备注进入队列；每条连线都将排队条目与它最终形成的条目连接起来。回答 21 与 `final` 边界在同一次提交中追加，并不是从收件箱取出的。ID、序列号和 `pi.live.run` 的值来自 `research/capture/inbox-steps.txt`。
> 
> 

## 撤回、失败与崩溃



`Submission.abort()` 会撤回仍在排队的提交请求。它以原因 `aborted` 结算为 `unanswered`，调用返回 `"aborted"`。一旦进入 `placed`，就来不及撤回了：调用返回 `"already_placed"`；如果已经结束，则返回 `"settled"`。`Conversation.abort()` 会撤回所有排队的 input，但保留排队的 write。



只有成功的运行才会执行 `final` 边界。失败或被中止的运行会将自己的 input 结算为 `unanswered`，并保持收件箱不变。



<aside class="manual-callout callout-warning durable-callout" role="note" data-source-page="87">

<strong>运行失败之后</strong>

排队的 follow\-up 会留在收件箱里，其 `wait()` 不会完成，直到另有内容被提交，或者你撤回它们。下一次提交会排在它们后面，因此较早的 follow\-up 先运行（`test/harness-inbox.test.ts`）。

</aside>




崩溃不会改变这些规则：每条记录和每个收件箱条目都已提交。重新打开后，排队的 follow\-up 仍会在被打断的运行结束之后运行。丢失的只是内存中的等待者。使用 `harness.submission(id)` 获取一个新句柄，再等待它即可。

## 细节：移动头指针的写入



write 可以设置 head，从而移动模型上下文的起点（重置、交接与头指针，原书第46页）。如果 head 指向当前起点之前，就会重新引入被重置或摘要截去的历史。这种 write 已过时：无论它是在空闲时提交，还是到达了边界，都会以原因 `stale` 结算为 `unanswered`。重置（`head: "self"`）永远不会过时。如果 `postTools` 边界接收到重置，就会按 `final` 边界处理；当前运行的 input 以原因 `reset` 结算，因为它们在得到回答之前上下文就被截断了。压缩依赖的也是同一条规则（压缩，原书第97页）。



> <strong>这对你意味着什么：</strong>
> 
> - 凡是可能重试的提交，都传入 `requestId`
> 
> - 按消息选择 `whenBusy`：运行中希望智能体看到的纠正用 `steer`，下一个问题用 `followUp`，界面应该拒绝时用 `reject`
> 
> - 运行失败后，重新提交或撤回排队的 follow\-up；不要永远等下去
> 
> - 重启后，使用 `harness.submission(id)` 重新获取句柄
> 
>
