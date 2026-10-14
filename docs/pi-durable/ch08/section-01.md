---
title: "Chord 与文档状态"
---

<div class="section-kicker">PI DURABLE / 8.1 · P. 125</div>

# Chord 与文档状态

---

> 观察者看到的文档是一系列只读值，每个值都附带产生它的确切编辑操作；存储中没有的内容，观察者永远看不到。
> 
> 

<strong>显示文档的面板必须与文档保持同步。工具更新任务列表时，面板应随之变化。崩溃后，它应准确显示已提交的内容。提交是一次原子保存：其中的全部内容一起存入，或者全部不存。Pi Durable 只向观察者提供已提交的变更：每次变更都包含一个新的只读值，以及产生它的一小组编辑操作。</strong>读完本节，你就能把文档接到 UI 上，并说明在文档被退役、被迁移或进程终止时，UI 会显示什么。

## 观察者收到什么



文档构建在 Chord（@earendil\-works/chord）之上。<strong>Chord 是一个用于复制 JSON 状态的小型库。</strong>要观察文档，你需要理解其中两个概念（基值与增量，原书第56页）：

- <strong>修订版（Revision）——一个不可变的 JSON 值。每次改变文档的提交都会产生一个新的修订版。</strong>

- <strong>操作（Operations）——从一个修订版到下一个修订版的确切编辑，以小型元组表示。其他位置的副本应用这些操作，就能保持同步。</strong>

- 观察者只读。Pi Durable 是唯一的写入者，被观察的状态没有任何用于修改自身的方法，见 spec §9\.1。每个操作都是一个元组：先是单个字母的名称，再是由键和数组索引组成的路径，用来定位值中的位置。



|<strong>元组</strong>|<strong>含义</strong>|
|---|---|
|`["r", value]`|替换整个值|
|`["s", path, value]`|设置一个属性或数组元素|
|`["d", path]`|删除一个属性或数组元素|
|`["a", path, text]`|向字符串追加内容|
|`["t", path, count]`|从字符串开头移除 count 个 UTF\-16 码元|
|`["p", path, index, remove, items]`|对数组执行 splice 操作|
|`["m", path, permutation]`|对数组重新排序：`new[i] = old[permutation[i]]`|

> 来源：research/pi/packages/chord/src/delta/README\.md。同一个变更可以用不同的元组表示；较大的编辑可能以一个 s 或 r 操作到达。只有最终结果值受到保证。
> 
> 

## 观察同一文档的两种方式



- `DOCUMENTSTATE()` 你订阅的一个只读状态。它以当前值作为初始值，并在每次提交 \(commit\) 后调用你的监听器。使用它来驱动用户界面 \(UI\)。

- `WATCHDOC()` 由一系列数据帧 \(frames\) 组成的流，每次提交对应一帧：包含新值、其操作以及该次提交的 `Context`（上下文）。你的回调函数每次处理一帧。使用它来按顺序转发变更内容（参见 watch 契约 \(第 129 页\)）。



两者都接受与 snapshot\(\) 相同的参数，并遵守两条规则。观察不会创建文档：文档不存在时返回 undefined；只有 tx\.doc\(\) 会创建文档（访问与创建，原书第53页）。此外，观察者跟随的是一个具体的文档实例世代，即它附着的那份已存储副本。如果该文档被退役后再次创建，观察者不会转而跟随它。



<BookFigure id="D.8.1" :show-caption="false" />

> 文档状态只有在存储持有提交之后才能看到它；你的监听器在 commit\(\) 完成前的一个微任务中运行。步骤1在 Session 的变更串行队列上运行，因此首次取值与附着之间不可能插入任何提交；随后 subscribe\(\) 立即以 hydrate 0 交付该值。Board 文档就是 research/capture/extra\-p8/doc\-observation\.txt 中捕获的文档（见下图）。来源：src/session/session\.ts、src/session/observation\.ts、chord/src/services/state\.ts。
> 
> 



这是从读取一侧看到的本书核心规则。在存储持有提交之前，观察者不会收到任何东西。提交在变更串行队列上的工作结束后、commit\(\) 完成之前，监听器会在一个微任务中运行。只有监听器的异步部分在队列之外运行：缓慢的同步监听器确实会拖延下一次提交，因此应把耗时工作交给 promise，见 spec §1。附着操作排在先前提交之后等待，所以首次取到的值已经包含所有这些提交。对于你尚未见过的修订版，你永远不会收到它的操作，见 spec §9\.1。

## documentState\(\) 的用法



示例4创建了一个文本为 "first" 的对话文档，附着一个状态，然后提交一次变更。

```js
const notesState = await session.documentState(Notes, chat.id, context);
const stopNotes = notesState.subscribe((value, _deliveryContext, delivery) => {
    console.log("Chord notes:", delivery.kind, delivery.sequence, value);
});
await session.commit(async(tx) => {
    (await tx.doc(Notes, chat.id)).text = "published through Chord";
}, context);
```



```bash
$ node --conditions=source --experimental-strip-types test/examples/04-chord-state.ts
Chord notes: hydrate 0 { text: 'first' }
Chord notes: update 1 { text: 'published through Chord' }
```

> 这里省略了 Notes 定义、用于创建文档的提交、undefined 检查，以及末尾的 stopNotes\(\) 和 dispose\(\)。subscribe 立即以 hydrate 交付当前值，之后每次提交交付一次 update。输出来自运行04。
> 
> 



delivery\.sequence 从0开始计数，只统计这个状态自身的交付次数。它不是提交编号，也不会被存储，见 spec §9\.1。同一文档上的两个状态彼此独立。释放其中一个只会停止那个观察者，不会停止文档。

## 修订版不可变且共享结构



你收到的每个值都是一个 Session 永远不会再改变的修订版。提交未触及的部分与上一个修订版共享，而不会被复制。在下图所依据的捕获中，修改标题生成了一个新的根对象，但 V2\.cards 与 V1\.cards 是同一个数组对象。



<BookFigure id="D.8.2" :show-caption="false" />

> 每次提交都会产生一个新的不可变修订版，以及产生它的确切操作。这里同时通过 documentState\(\) 和 watchDoc\(\) 观察一个会话作用域的 app\.board；退役之前又发生了101次提交。值、操作、序号和共享检查均来自 research/capture/extra\-p8/doc\-observation\.txt。
> 
> 



共享使发布的成本很低，但没有任何对象被冻结。如果你的代码修改了收到的值，就会悄无声息地破坏 Session 的副本以及其他所有观察者的副本。需要编辑时，先复制，见 spec §12。



要在另一个进程中维护副本，应从首次取得的值开始，使用 Chord 的 applyImmutable\(value, ops\) 按顺序应用每一批操作。测试套件会检查这样能否重建每一个交付值，见 test/session\-watches\.test\.ts。

## 退役、版本、关闭与崩溃



- 退役——最后一帧是 `[["r", null]]`。之后状态读出的就是 null，绝不会是过时数据。监听交付该帧后，以 retired 原因结束。若要看到重新创建的文档，需要重新附着。

- 新版本——当某次提交以不同的定义版本存储文档时，观察者收到的是以 `["r", value]` 表示的完整新值，而不是针对它并不拥有的数据结构的操作，见 src/session/session\.ts。

- Session 关闭——每个状态和监听都会结束。状态保留最后一个值，见 spec §2\.2。

- 崩溃——状态和监听都存在于内存中，随进程一起消失。重新打开后，再次附着；新状态从已提交的内容开始，见 spec §9\.1。



UI 不会因崩溃而丢失任何已经显示过的内容，因为它显示的始终只有已提交数据。自上次成功提交以来的进度可能消失。默认的100 ms最小间隔并不限定这种损失的上限（实时文档，原书第88页）。



> <strong>这对你意味着什么：</strong>
> 
> - 用 documentState\(\) 驱动 UI。它只显示已提交的数据，因此崩溃后无需额外处理就能保持正确。
> 
> - 绝不要修改收到的值。先复制它。
> 
> - 将 `["r", …]` 视为“替换所有内容”。文档退役、版本变化和缓冲区溢出时都会出现它。
> 
> - 文档退役或重新打开后，重新附着；观察者绝不会移到新的实例世代上。若要通过 Chord 服务为远程客户端提供数据，请遵循 docs/pico\-v5\-chord\-usage\.md。
> 
>
