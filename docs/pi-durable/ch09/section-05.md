---
title: "执行环境"
---

<div class="section-kicker">PI DURABLE / 9.5 · P. 155</div>

# 执行环境

---

> 工具只能通过宿主为每次使用构建的 ExecutionEnv 接触文件和进程，因此对话在哪里运行，由宿主决定，而不是由工具决定。
> 
> 

你的智能体工具会读取文件和运行命令。执行环境决定在哪里做这些事：你自己的磁盘、每个用户独立的沙盒目录，或远程容器。工具从不直接接触机器；它们通过 ExecutionEnv 操作，宿主在每次需要时构建这个环境。读完本节，你就能为每段对话提供独立沙盒，为远程宿主实现这个接口，并了解内置工具的要求。

## 每次使用时构建



宿主提供一个函数 HarnessOptions\.env。只要工作需要环境，Harness 就会调用它；调用绝不发生在 Session 的变更串行队列上，而且它可以是异步的，见 src/harness/types\.ts。它接收 conversationId、对话的工作目录 cwd（如果在 pi\.agent 文档中设置了该值，见“每段对话的智能体”，原书第106页），以及用于读取已提交文档的 read。



<BookFigure id="D.9.9" :show-caption="false" />

> 工具、提示词区段和任务阶段只能通过宿主在每次使用时根据已提交状态构建的环境访问文件和进程。调用方来自 README §Environment 和 src/harness/\{tool,generation,scheduler\}\.ts；目标接口来自 src/harness/types\.ts。
> 
> 



三类工作会请求环境。工具调用通过 api\.env 收到它（定义工具，原书第112页）。系统提示词区段通过 input\.env 收到它（系统提示词，原书第115页）。任意任务阶段都可以通过 runtime\.env\(\) 请求环境。允许返回 undefined：此时内置工具会以错误结果失败，错误为“No execution environment is configured”。env 抛出的异常也会变成工具调用的错误结果，见 README §Environment；src/tools/env\.ts。



由于环境按每次使用构建，崩溃后重跑的工具调用会得到一个全新环境，“使用对话当前的 cwd，它可能与第一次尝试时不同”，见 spec §12。只根据已提交状态来构建它；示例29就是这样为每段对话提供独立沙盒的：

```ts
const harness = await Harness.open(
    new MemoryStorage(),
    {
        models,
        registry,
        // 只读取已提交内容；没有沙盒的对话不会获得环境，
        // 因此它的工具会以明确的错误失败。
        env: async ({ conversationId, read }, envContext) => {
            const sandbox = await read.snapshot(Sandbox, conversationId, envContext);
            return sandbox?.path === undefined
                ? undefined
                : new NodeExecutionEnv({ cwd: sandbox.path });
        },
    },
    context,
);
```



```PowerShell
$ node --conditions=source --experimental-strip-types test/examples/29-sandbox-per-conversation.ts
alice's sandbox: from alice
bob's sandbox: from bob
```



Sandbox 是创建每段对话时设置的应用文档。两段对话都运行了同一个 write 工具，每份便笺都落在自己的目录中（运行29）。三元表达式为了适应页面宽度重新换行。

## 接口



ExecutionEnv 由 FileSystem 加 Shell 组成，来自 @earendil\-works/pi\-durable/env。每个操作都返回结果，而不抛异常：\{ ok: true, value \} 或 \{ ok: false, error \}，其中 error 携带诸如 not found 或 timeout 这样的代码，见 src/env/index\.ts。



|<strong>分组</strong>|<strong>FileSystem 成员</strong>|
|---|---|
|标识|id, cwd|
|路径|absolutePath, joinPath, canonicalPath, exists|
|读取|readTextFile, readTextLines, openTextLineReader, readBinaryFile, openBinaryReader|
|写入|writeFile, appendFile, truncateFile, flushFile, renameFile|
|目录|Alternatives〔原文此处混入该词，疑为提取错误，含义待核〕；fileInfo, listDir, openDirReader, createDir, remove|
|临时内容|createTempDir, createTempFile, cleanup|
|变更|watch|

> 来源：src/env/index\.ts。truncateFile 和 flushFile 是为 JSONL 存储提供的。
> 
> 



id 为文件命名空间命名：“相同的 id 会在相同的路径看到相同的文件，无论 cwd 是什么”，见 src/env/index\.ts。每个本地 NodeExecutionEnv 都使用 "node:local"；每个容器或远程宿主都需要自己的 id。有了 id，宿主就能为每次调用构建一个新的环境对象。内置 edit 和 write 工具仍会轮流操作同一文件，因为它们按 id 加路径排队。这个队列属于单个进程，“不是针对 bash 或其他进程的锁”，见 src/tools/file\-mutation\-queue\.ts。

## 运行命令



exec\(command, options, context\) 接受字符串或数组。字符串通过 shell 运行；NodeExecutionEnv 使用 bash，无法使用时回退到 sh \-c。数组形式会直接运行 command\[0\]，其余元素作为参数，因此参数会完全按给定形式到达程序，见 src/env/index\.ts；src/env/node\.ts。当参数来自模型或用户时，优先使用数组形式。



在 NodeExecutionEnv 中，timeout 的单位是秒；非零退出码仍是一个成功结果，并带有对应的 exitCode。onOutput 接收每个输出块，并标记它来自 stdout 还是 stderr。中止 context 会终止该命令；关闭时，cleanup\(\) 会终止所有剩余命令。

## 输出窗口



如果工具只保留命令输出的尾部，可以明确声明这一点；远程环境于是可以不发送其他内容。调用方传入一个 window（包含 maxBytes、maxLines 和节奏限制）。环境可以丢弃该尾部窗口之外的输出，并在下一个输出块中通过 info\.skipped 报告丢弃了什么，见 src/env/index\.ts；CHANGELOG 1\.0\.3。



<BookFigure id="D.9.10" :show-caption="false" />

> 带窗口的 exec 可以丢弃调用方本来也会丢弃的输出，并精确统计丢弃量。图中展示 info\.skipped 的规则（src/env/index\.ts），以及一个通过200字节、5行窗口打印2,000行的一致性测试用例。
> 
> 



跳过输出之所以安全，是因为一条规则：跳过之后的那个输出块始终大于窗口，因此被丢弃的文本不可能属于要保留的尾部。内置 bash 工具使用窗口，见 src/harness/tool\.ts；src/tools/bash\.ts。NodeExecutionEnv 忽略 window，并交付全部内容；当输出需要跨网络传输时，窗口才有收益。会转换输出的工具包装器必须关闭窗口，否则被跳过的文本会绕过它的转换（定义工具，原书第112页）。



<strong>这对你意味着什么：</strong>

- 要隔离对话，就从 HarnessOptions\.env 为每段对话返回不同的环境。返回 undefined 可以关闭文件工具和 shell 工具。

- 只根据已提交状态构建环境：崩溃后重跑时，会重新构建它。



对于自定义环境，实现 FileSystem 和 Shell，把失败作为结果返回，为每个文件命名空间提供自己的 id，并运行 /testing 中有21个用例的 registerEnvConformance。

## 细节：1\.0\.3 新增的能力



1\.0\.3 版本将四项能力设为必需，因此自定义环境必须补上它们，见 CHANGELOG 1\.0\.3。



openBinaryReader\(path, \{ noFollow? \}\) 按位置读取一个已打开的文件，其 scanLines\(\) 通过一次扫描找到一段行范围；read 工具同时使用这两项能力。openDirReader\(path\) 分页遍历目录。watch\(targets, onChange\) 报告变化的路径、溢出（重新扫描全部内容）或错误。此外，exec 接受数组形式。
