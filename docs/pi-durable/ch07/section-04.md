---
title: "定义工具"
---

<div class="section-kicker">PI DURABLE / 7.4 · P. 112</div>

# 定义工具

---

工具由 schema、重放策略和 `execute()` 函数组成；Harness 将它报告的内容转化为恰好一个结果条目。



工具是模型作用于世界的方式：读取文件、执行命令、调用 API。困难在于执行中途崩溃。读完本节，你就能定义带类型的工具，将输出流式传给界面，选择重放策略，并读懂它留下的结果条目。

## 十一行定义一个工具



`defineTool()` 根据工具的 TypeBox 参数 schema 确定类型。Harness 在 `execute()` 运行之前，根据该 schema 检查模型参数，因此下面的 `args.n` 确实是一个数字。



count 工具，来源：README §Tools · `research/capture/scripts/one-turn.ts`

```ts
import { Type } from "@earendil-works/pi-ai";

const count = defineTool({
    name: "count",
    description: "Count from 1 to n",
    parameters: Type.Object({ n: Type.Number() }),
    execute: async (args, api) => {
    for (let i = 1; i <= args.n; i++) api.output(`${i}\n`);
    return {};
    },
});

registry.install(defineExtension({ name: "count", tools: [count] }));
```

> `execute()` 没有返回 content，因此它用 `api.output()` 写出的文本会成为结果。
> 
> 



只有标准的 pi\-ai 工具字段（name、description、parameters）会发送给模型。你自己的字段，例如提示词区段，仍留在代码中（系统提示词，原书第115页）。四个可选字段设置策略：

|<strong>字段</strong>|<strong>默认值</strong>|<strong>含义</strong>|
|---|---|---|
|`replay`|`"unsafe"`|调用因崩溃而中断后，是否可以在重启时再次运行？|
|`executionMode`|`"parallel"`|`"sequential"` 让整轮调用逐个执行|
|`prepareArguments`|无|在检查之前修复参数，例如应该是数组的地方却收到 JSON 字符串|
|`outputLimits`|50 KiB、2,000 行、保留开头|限制为结果保留的输出|

> `ToolRegistration`，见 `src/harness/types.ts`；限制值来自 `src/truncate.ts`。执行模式的默认值来自 settings 的 toolExecution。
> 
> 

## 选择重放策略



每位工具作者都必须回答一个问题：如果进程在我的工具执行时崩溃，它可以再次运行吗？调用执行之前，工具任务将最终参数和策略写入磁盘。重启后，只有存储的策略和当前工具都声明 `"safe"`，才会重跑调用。否则，它会用已保存的输出写入一个 interrupted 错误结果。只有使用相同参数运行两次也无害时，才声明 safe。完整说明及实际崩溃采集记录，参见“工具调用与重放”（原书第94页）。

## 从结果到条目



返回结果的每个字段都是可选的：content、isError、details、diagnostics、usage 和 control。工具任务会补齐缺项，运行 afterTool 钩子，限制长文本（添加 truncated 警告），然后写入一个条目。存在诊断信息时，模型看到的文本末尾会附加一个 `<harness>` 块，每条诊断占一行；条目的 data 以列表保存这些诊断。



<BookFigure id="D.7.5" :show-caption="false" />

> 工具结果条目准确保存模型看到的内容，并附上结构化诊断。这里是 `research/capture/sqlite-rows.txt` 中的条目 13，即 count 工具对 `count {"n": 3}` 的回答，键按采集记录中的顺序排列。
> 
> 



错误有两种，区别很重要。带有 `isError: true` 的结果是普通回答：任务会完成。`execute()` 抛出的异常也会转化为错误结果，代码为 `tool_error`，并保留部分输出，但它会让工具任务以 failed 结束，进而中止该调用启动的所有内容，见 `src/harness/tool.ts`。Harness 自行写入的错误携带说明原因的代码：`tool_unavailable`、`invalid_arguments`、`blocked`、`interrupted` 或 `aborted`。



两个结果字段会影响轮次。usage 记录工具自己的费用（用量与费用，原书第100页）。control 可以提供更多工具（addTools），在本轮每个结果都提出要求时结束运行（terminate），或者交接到全新的上下文（handoff，参见重置、交接与头指针，原书第46页）。

## execute\(\) 接收什么



`execute(args, api, context)` 接收一个专为本次调用创建的 api 对象。调用一旦结束，对这个对象的每项操作都会失败。你最常使用的部分有：

- `env`：对话当前 cwd 的文件和进程；如果宿主没有配置环境，则为 undefined（执行环境，原书第155页）

- `output(chunk)`：像 stdout 一样追加执行中的文本。如果结果没有 content，保留的文本就成为 content

- `details(value, context)`：向界面发布结构化进度；如果结果没有 details，最后一个值就成为结果的 details

- `diagnostic(d)`：附加给模型的说明，例如警告，与工具数据分开

- `commit`、`memo`、`createTask`：提交、备忘和子任务，与任何任务中一样

- `conversation(id)`：指向本次调用创建的对话的句柄（子智能体，原书第121页）

    

工具运行期间，output、details 和 diagnostics 会通过实时文档大约每 100 ms 传到界面。结果条目写入之前，模型看不到其中任何内容（运行控制与实时文档，原书第88页）。

## 内置工具与包装器



`@earendil-works/pi-durable/tools` 提供 read、write、edit 和 bash，将它们打包为 `CodingTools` 扩展（coding\-tools）。没有任何东西会自动帮你安装它们。它们只通过 `api.env` 工作，而且四个工具的重放策略都是 unsafe。bash 保留长输出的尾部，提供指向完整输出文件的路径，并在退出码非零或超时时失败，见 `src/tools/`。



要为部分对话改变工具，应覆盖或包装它，而不是复制。较后扩展中的同名工具会替换较早工具，而 `wrapTool(tool, wrapper)` 会装饰最终胜出的工具。包装器“从不捕获基础工具，因此重新加载基础工具仍会保留它的包装器”，见规范 §7\.3。示例 30 为一个对话提供会激活 virtualenv 的 bash，并对两个对话的每次 bash 调用计时，见运行记录 30。



> <strong>这对你意味着什么：</strong>
> 
> - 除非重跑无害，否则让 replay 保持 unsafe；先把任何随机值记录到 memo 中
> 
> - 对预期内的失败，返回 `isError: true`；只有在调用自身的工作应该被中止时才抛出异常
> 
> - 给模型的说明使用 `diagnostic()`，不要混入工具输出
> 
>
