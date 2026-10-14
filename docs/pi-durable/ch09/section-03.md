---
title: "JSONL"
---

<div class="section-kicker">PI DURABLE / 9.3 · P. 148</div>

# JSONL

---

> 先写旁文件记录，再在 main\.jsonl 中写一个标记：提交恰好在其标记存在时成立。
> 
> 

JSONL 存储是一个纯文本文件目录，可以直接用 cat 阅读。它适合开发和调试，此时看清每条记录比速度更重要。读完本节，你就能阅读这些文件、说明崩溃可能丢失什么，并决定是否启用 fsync。

## 目录



来自 /storage/jsonl/node 的 openNodeJsonlStorage\(directory, context, options\) 会打开或创建目录。在其他运行时上，来自 /storage/jsonl 的 JsonlStorage\.open\(directory, fs, context, options\) 通过任意 FileSystem 完成同样的工作（执行环境，原书第155页）。每一行都是一个 JSON 对象，位于三类文件中的一种，见 spec §11\.3：



main\.jsonl——每次提交一行标记。它只会增长。



`doc-<id>.jsonl`——一个文档的内容：它的基值和增量。



`task-<id>.jsonl`——一个存活任务的历次记录。任务完成后会删除这个文件。



文档文件和任务文件是旁文件（sidecar）：它们保存体积较大且不断变化的数据。标记会完整携带较小的记录，例如条目和任务的最终记录。对于其余内容，标记携带一个指针：文件名，加上一个从0开始为本次提交的旁文件行编号的 ordinal，见 src/storage/jsonl/storage\.ts。



<BookFigure id="D.9.4" :show-caption="false" />

> 一次 JSONL 提交就是 main\.jsonl 中的一个标记，它通过序列号和 ordinal 指明相应的旁文件记录。这里是一次轮次运行中的提交6，在 count 工具运行期间复制而来：research/capture/jsonl\-dir\-midrun/。助手条目放在标记内部；两个任务和两个文档则放在旁文件中。
> 
> 



提交6的标记，来源：research/capture/jsonl\-dir\-midrun/main\.jsonl，第6行：

```json
{
    "format": 1, "type": "commit", "seq": 6,
    "writes": [
        { "type": "entry", "value": { "model": [ ... ], "kind": "pi.assistant", "id": 11, "conversationId": 1, "byTaskId": 9 } },
        { "type": "task.sidecar", "id": 9, "ordinal": 0 },
        { "type": "task.sidecar", "id": 12, "ordinal": 1 },
        { "type": "document.change", "id": 2, "ordinal": 2 },
        { "type": "document.change", "id": 4, "ordinal": 3 }
    ]
}
```

> 此处经过美化排版；磁盘上只有一行。条目的模型消息已省略。
> 
> 



轮次结束后，两个任务文件都不见了，doc\-2\.jsonl 只剩一个基值，见 research/capture/jsonl\-files\.txt。这两件事都是下文的回收过程完成的。

## 发布



每次提交都遵循同样的三个步骤，见 spec §11\.3：

1. 把本次提交的记录追加到每个受影响的旁文件。

2. 向 main\.jsonl 追加一个完整标记，列出这些记录。

3. 只有这时，才让读取能够看到本次提交。

    

<BookFigure id="D.9.5" :show-caption="false" />

> 旁文件记录先落定，标记使它们成为一次提交，回收则只在发布后运行。图中是为仅保留当前状态的文档写入新基值的一次提交，文件操作顺序由 test/jsonl\-storage\.test\.ts 断言；步骤2、5和7只在 fsync: true 时发生。
> 
> 



未通过验证的批次不会接触任何文件。一旦开始写入，任何追加或刷盘失败都会使后端中毒：直到重新打开之前，每次调用都会以 JsonlStoragePoisonedError 拒绝，Session 也会中毒（2\.3节，原书第33页）。



fsync 选项决定故障后保留什么，默认值为 false。没有它，JSONL 能经受进程崩溃，却不能保证经受断电、内核或磁盘故障。设置 fsync: true 后，每个旁文件都会先刷入磁盘，然后才写入其标记。最新的提交在断电时仍可能消失，“但保留下来的标记不应先于它的旁文件数据落盘”，见 spec §11\.3。

|<strong>提交</strong>|<strong>fsync: false</strong>|<strong>fsync: true</strong>|
|---|---|---|
|两个新文档|append ×2，append main|append ×2，flush ×2，append main|
|任务完成|append main，remove sidecar|append main，flush main，remove sidecar|

> 每次提交的文件操作，来源：test/jsonl\-storage\.test\.ts。
> 
> 

## 恢复



打开目录就是执行一遍恢复，规则很简短，见 spec §11\.3；src/storage/jsonl/storage\.ts：

- 残缺行——如果文件不是以换行符结尾，就把它截断到最后一个换行符。

- 未确认记录——旁文件中的一行只有被某个标记指明时才算数。末尾未确认的行会被截去。

- 损坏——已确认的行如果缺失、乱序，或位于未确认行之后，打开操作就会以 JsonlCorruptionError 失败（除非后来出现的基值已使它不再必要）。没有任何机制会修复它，见 spec §13。

- 残留内容——删除因回收中断而残留的文件，并完成所有尚未执行的回收。



<BookFigure id="D.9.6" :show-caption="false" />

> 打开 JSONL 目录时，会截去残缺的标记，以及每条没有标记确认的旁文件记录。来源：research/capture/extra\-p9/jsonl\-crash\.txt。
> 
> 



在捕获中，提交4本来要把计数器设为2，并将一个任务移入 effect 阶段。它的旁文件行已写入，但标记是残缺的。重新打开时，这三行都被截去：计数器读作 \{"n":1\}，任务在 intent 阶段处于 running 状态，而下一次提交再次获得 seq 4，见 research/capture/extra\-p9/jsonl\-crash\.txt。提交4从未发生，因此重新打开的 Harness 会再次运行 intent 阶段（5\.3节，原书第70页）。

## 回收



回收会删除因较新的基值、退役或任务完成而不再必要的旁文件行，而且只会在相应提交之后进行，见 spec §11\.3。可回溯文档绝不回收。如果回收失败，提交仍然保持已发布状态，下一次打开会完成这项工作，见 src/storage/jsonl/storage\.ts。



<strong>这对你意味着什么</strong>

- 进程崩溃绝不会留下半次提交。提交恰好在其标记行完整时存在。

- 如果文件必须在断电后仍保持一致状态，请启用 fsync: true。大型存储的打开速度会较慢，请做好准备（9\.4节，原书第152页）。
