---
title: "内存、一致性与可移植性"
---

<div class="section-kicker">PI DURABLE / 9.4 · P. 152</div>

# 内存、一致性与可移植性

---

> MemoryStorage 定义每个后端应具备的语义，共享的测试套件负责检查；只要适配器能运行，存储核心就能运行。
> 
> 

三种后端可以互换，是因为它们遵循同一个参考实现，并接受同一套测试。读完本节，你就能根据实测成本选择后端，用共享套件测试自己的后端，并让存储在 Node 之外的运行时上运行。

## MemoryStorage 是参考实现



内存存储定义了其他后端必须做到什么。它会复制自己保留的每条记录，也会复制自己返回的每条记录：“这是有意模拟 SQLite 编码／解码和 JSONL 序列化自然形成的所有权边界”，见 spec §11\.1。因此，调用方修改读取到的记录，无法改变存储中的内容，无论后端在内存还是磁盘上。内存存储也严格按持久化后端的方式保留或丢弃文档历史。测试若读取仅保留当前状态的文档的旧时点，在内存后端上也会像在 SQLite 上一样失败。



内存存储不持久化任何内容。将它用于测试、示例和短生命周期的会话。test/examples 中的大多数示例都基于它运行；恢复和重启示例（示例13、23、24、31）使用 SQLite，示例17使用 JSONL。JSONL 内部也使用内存存储来响应每次读取，见 src/storage/jsonl/storage\.ts。

## 一致性测试套件



自定义后端需要通过内置后端也必须通过的同一套测试，以此证明自身符合要求。该套件从 @earendil\-works/pi\-durable/testing 导出，能在任何兼容 Vitest 或 Jest 的测试运行器下运行：



运行存储测试套件，来源：README §Storage：

```ts
import { registerStorageConformance } from "@earendil-works/pi-durable/testing";
import { describe, expect, it } from "vitest";

registerStorageConformance({ describe, expect, it }, "My Storage", async (use) => {
    const storage = await openMyStorage();
    try {
        await use(storage);
    } finally {
        await closeMyStorage(storage);
    }
});
```

> 每个测试用例恰好调用一次 use，并传入一个全新、空白的存储。
> 
> 



该套件有23个用例，覆盖 ID 空间、原子批次和与内部数据脱离的值、条目与分叉、对话和任务扫描、提交请求、文档历史与地址，以及无损字符串键，见 src/testing/storage\-conformance\.ts。包内会运行它五次：分别针对内存、SQLite 和 JSONL，以及每次提交后都关闭再重新打开的 SQLite 和 JSONL。套件固定的是语义，不是实现机制。崩溃恢复、刷盘顺序和查询计划按后端分别测试；自定义后端也需要自行测试这些内容。

## 可移植核心，Node 适配器



<BookFigure id="D.9.7" :show-caption="false" />

> SQLite 和 JSONL 的核心都可移植；只有它们的 Node 适配器接触 Node API。图中展示 package\.json 的子路径导出；任一核心也都接受你自行编写的适配器。test/storage\-runtime\-boundary\.test\.ts 会遍历每个入口的导入，以强制检查这个边界。
> 
> 



这种拆分由测试强制保证。/storage/sqlite、/storage/jsonl 和 /env 不得导入任何 node: 模块，即使间接导入也不行。只有 /storage/sqlite/node 和 /storage/jsonl/node 是 Node 专用的。要在其他运行时上运行，为 SqliteStorage\.open\(\) 提供一个 SqliteDatabase（SQLite，原书第144页），或者为 JsonlStorage\.open\(\) 提供一个 FileSystem（执行环境，原书第155页）。

## 实测成本



包内提供一个基准测试，在三个后端上执行相同的读写：npm run bench:storage。其数据集包含1,000个条目、300个任务和300个文档。下图展示了在 Apple M3 Max、Node 24\.13\.0 上某次运行结果中的三行。



<BookFigure id="D.9.8" :show-caption="false" />

> JSONL 的读取与内存一样快，因为它本来就是从内存读取；代价体现在每次提交和打开时。均值来自 research/capture/extra\-p9/bench\-storage\.txt（Apple M3 Max，macOS 26\.2，Node 24\.13\.0，2026\-10\-05）。提交和重新打开两行各有20个样本，误差幅度为 ±8–66%。每个面板使用独立刻度。
> 
> 



这些数字是设计的自然结果。JSONL 从内存响应读取，因此精确条目查找的成本与内存相同：0\.44 µs，而 SQLite 是2\.85 µs。JSONL 提交会向多个文件追加内容，耗时792 µs，而 SQLite 为120 µs。打开 JSONL 目录会重放每个标记，对于这个数据集耗时249 ms；SQLite 打开并完成首次读取只需1\.33 ms。在十倍规模下，SQLite 占用0\.22 MiB 堆内存；JSONL 和内存后端则各占用超过7 MiB，见 research/capture/extra\-p9/benchstorage\-memory\.txt。



|<strong>后端</strong>|<strong>能经受的故障</strong>|<strong>成本</strong>|<strong>适用场景</strong>|
|---|---|---|---|
|memory|无|堆内存随存储增长|测试、示例、短会话|
|SQLite|进程崩溃|读取较慢；堆内存小；打开快|任何长期存在的内容|
|JSONL|进程崩溃；启用 fsync 后，断电也能保持一致|提交慢；整个存储驻留内存；打开时重放|调试、可读文件|



本节与前两节的总结。



不同机器上的耗时不可比较。要比较自己的后端，请使用 /testing 导出的场景（seedStorageBenchmark\(\)，以及读写基准测试列表），并像包内的 test/storage\.bench\.ts 一样，在同一个进程中运行所有候选后端。



<strong>这对你意味着什么：</strong>

- 默认选择 SQLite；测试中使用内存；希望直接阅读文件时使用 JSONL。

- 无论选择哪个后端，每个存储都只运行一个进程。没有任何后端会通过锁来阻止第二个进程。

- 自定义后端必须通过23个用例的套件，以及自己的崩溃测试。



> 来源：spec §11\.1；README §Storage、§Examples；src/storage/memory\.ts；src/storage/jsonl/storage\.ts；src/testing/\{storage\-conformance,runner,storage\-benchmark\}\.ts；test/storage\.bench\.ts；test/memory\-storage\.test\.ts；test/sqlite\-storage\.test\.ts；test/jsonl\-storage\.test\.ts；test/storage\-runtime\-boundary\.test\.ts；package\.json；research/capture/extra\-p9/bench\-storage\.txt、benchstorage\-memory\.txt。
> 
>
