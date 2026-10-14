---
title: "Codemode：调用工具的脚本"
originalPage: 151
---

<div class="section-kicker">6.2 / INTEGRATION & INTERFACES</div>

# Codemode：调用工具的脚本

---

<strong>Codemode 在全新的 QuickJS VM 中运行模型编写的 JavaScript；这个 VM 唯一的能力就是调用工具。每个嵌套调用都会经过完整的工具流水线，但只有脚本输出进入上下文。</strong>



<strong>如果模型需要从五十个 issue 中筛出三个，可以发起五十次工具调用，也可以编写一个脚本。Codemode 就是第二种选择。</strong>模型发送 JavaScript；Pi 在 WebAssembly 沙箱中运行它，`tools.<name>(args)` 是沙箱唯一的出口；嵌套调用的结果会留在脚本中，除非脚本将其打印出来。本节介绍沙箱，以及为什么它由一个 worker、一个 wasm 实例和一个共享标志构成，随后介绍 codemode 工具：它的 schema 和语法、模型读取的描述、嵌套调用如何执行，以及最终返回的内容。

## 两个包



`@earendil-works/pi-codemode` 1\.0\.4“在 QuickJS VM（编译为 WebAssembly）中运行模型编写的 JavaScript，其唯一能力是调用注入的工具。嵌套工具调用永远不会进入 LLM 上下文；只有脚本的输出和返回值会进入”（`codemode/README.md`）。它不依赖 Pi，唯一的运行时依赖是 `quickjs-wasi` 3\.6\.2（`codemode/package.json`）。



codemode 工具本身是位于 `CA/src/extensions/codemode/` 的内置可替换扩展：`tool.ts`（419 行）构建定义和描述，`execute.ts`（675 行）运行脚本，`renderer.ts`（150 行）在 TUI 中绘制它。注册时设置了 `defaultActive: false`（`CA/src/extensions/codemode/index.ts:43`）。`--tools`、`defaultTools` 设置或 `setActiveTools()` 都能启用它；当已配置的服务器包含 codemode 工具时，MCP 扩展也会启用它（“MCP”，原书第144页）。

## 沙箱



<strong>每次 `execute()` 都创建一个新的 `worker_threads` Worker，而 worker 从编译好的 wasm 模块实例化一个新的 QuickJS VM。</strong>“每次运行使用一个全新 worker，可以让终止操作保持简单：失控的脚本，包括只会让微任务队列空转的脚本，都会被 `terminate()` 杀死，无法污染后续运行”（`codemode/src/runtime/host.ts:120`）。



<BookFigure id="6.3" />

> VM 只能通过一个桥接函数访问主机，而主机有两种方式可以停止 VM。消息以 JSON 字符串形式传递；worker 自身从不构建结构化值。示意图来源：`codemode/src/runtime/protocol.ts`（`WorkerData`、`WorkerToHostMessage`、`HostToWorkerMessage`）、`worker.ts` 和 `host.ts`。
> 
> 



<strong>隔离。</strong> VM 是独立的 wasm 实例，拥有自己的线性内存。它唯一的导入是一个 WASI 适配层和一个主机调用入口；worker 会丢弃该适配层写入 stdout 和 stderr 的内容（`codemode/src/runtime/worker.ts:32`）。其中没有计时器、`fetch`、`process`、`require`、模块或 `WebAssembly`；“`eval` 和 `Function` 可以工作，但只能在同一个 VM 内生成更多代码”（`codemode/README.md`）。脚本运行前，前置代码会冻结内置对象，因此即使脚本修改 `Array.prototype.toJSON`，也无法破坏前置代码向主机报告的内容（`codemode/src/runtime/prelude-source.ts:28`）。



<strong>为什么使用 worker。</strong> QuickJS 同步运行；若脚本在主机线程上空转，就会阻塞 Pi 的事件循环。<strong>为什么使用标志。</strong> 在 Bun 上，`terminate()`“无法停止一个正在 wasm 内空转的线程”（`codemode/src/runtime/protocol.ts:21`），所以主机先设置共享的 `Int32`，VM 的 `interruptHandler` 再轮询它（`codemode/src/runtime/worker.ts:60`）。<strong>为什么设置 `maxStackSize`。</strong> 没有它，“深度递归会使 wasm 栈溢出并触发陷阱，而不是抛出可捕获的 `RangeError`”（`codemode/src/runtime/worker.ts:57`）。



采集工具集对固定版本的构建运行了五个脚本，执行期限为一秒：

|<strong>脚本</strong>|<strong>结果</strong>|
|---|---|
|在 `Promise.all` 中进行两次 `tools.read` 调用，然后 `store`、`return`|成功，两次调用均成功，`storeWrites.set = { seen: 2 }`|
|`typeof fetch, setTimeout, process, require, WebAssembly; eval("1 + 1"); Object.isFrozen(Array.prototype)`|五个 `"undefined"`、`2`、`true`|
|`await new Promise(() => {} )`|`script`：“脚本正在等待一个永远无法完成的 promise：没有待完成的工具调用，而且这里没有计时器。”|
|`while (true) {}`|`timeout`：“执行在 1000 ms 后超时”|
|在 `try` 内无限递归|成功，值为“RangeError：超出最大调用栈大小”|



停滞的脚本会立即失败；空转的脚本则要等到期限到达。来源：`research/out/codemode-sandbox.txt`，由 `research/capture/codemodesandbox.mjs` 生成。



`execute()` 从不因脚本失败而 reject。`result.error.kind` 为 `script`、`timeout`、`aborted` 或 `sandbox`（wasm 陷阱或缺失 worker 文件）（`codemode/README.md` 的“结果”节）。README 称，每次执行的启动开销“包括 VM 创建在内约为 20 ms”；采集工具集没有测量这一时间。



|<strong>限制</strong>|<strong>数值</strong>|<strong>设置位置</strong>|
|---|---|---|
|`MAX_OUTPUT_CHARS`|文本和 base64 图像数据共 16 Mi 个字符|`codemode/src/runtime/prelude-source.ts:40`|
|`MAX_OUTPUT_ITEMS`|100,000 项|`codemode/src/runtime/prelude-source.ts:41`|
|`MAX_STORE_VALUE_CHARS`|每个值的 JSON 为 256 Ki 个字符|`codemode/src/runtime/prelude-source.ts:32`|
|`MAX_STORE_TOTAL_CHARS`|所有值共 1 Mi 个字符|`codemode/src/runtime/prelude-source.ts:33`|
|执行期限，库|300,000 ms|`codemode/src/runtime/host.ts:22`|
|执行期限，Pi|无，除非设置 `timeout_ms`|`CA/src/extensions/codemode/execute.ts:427`|
|VM 堆，Pi|256 MiB|`CA/src/extensions/codemode/execute.ts:55`|
|并发 `models.*` 调用，Pi|4|`CA/src/extensions/codemode/execute.ts:49`|



Pi 移除了库的五分钟期限，并增加堆大小上限。超过任一输出限制，脚本都会因 `RangeError` 而失败，“即使它捕获了这个错误”（`codemode/README.md` 的“结果”节）。

## codemode 工具



schema 只有一个字段。工具定义中另有三个同样重要的属性：



输入 schema 及塑造其行为的定义片段。来源：`CA/src/extensions/codemode/tool.ts`。

```ts
export const codemodeSchema = Type.Object({
  code: Type.String({
    description: "Raw JavaScript source.",
  }),
});
...
parameters: codemodeSchema,
// 脚本不得启动其他脚本。
exposure: "model-only",
prepareLoadout: (loadout) => prepareCodemodeLoadout(loadout, options),
// 具备相应能力的模型将脚本写为原始文本，而非 JSON 转义字符串。
constrainedSampling: { type: "grammar", variants: { openai_lark: CODEMODE_SOURCE_GRAMMAR } },
```

> 第 89–93 行和 390–395 行；`createCodemodeToolDefinition` 的其他部分已省略。
> 
> 



该语法允许支持语法约束工具输入的模型直接生成原始 JavaScript，而非 JSON 转义字符串。它只约束可选选项行的形式；JSON 和代码由 `parseCodemodeSource` 检查（`codemode/src/source.ts:18`）。



`CODEMODE_SOURCE_GRAMMAR`，来源：`codemode/src/source.ts`。

```text
start: options_source | plain_source
options_source: OPTIONS_LINE NEWLINE SOURCE
plain_source: SOURCE

OPTIONS_LINE: /[\t]*\/\/ @options:[^\r\n]*/
NEWLINE: /\r?\n/
SOURCE: /[\s\S]+/
```

> 完整内容，第 23–29 行。

> <strong>PDF核对注（原书第154页）：</strong> 原始 PDF 的 `OPTIONS_LINE` 字符类为 `[ \t]`，包含一个普通空格与 `\t`。上方所提供代码为 `[\t]`，保留原样以便核对。
> 
> 



选项行为 `// @options: {"max_output_tokens": N, "timeout_ms": N}`。任何其他字段、无效 JSON，或选项行后没有代码，都会抛出 `CodemodeSourceError`；`timeout_ms` 必须是正整数，最大为 2,147,483,647，即 `setTimeout` 支持的最大延迟（`codemode/src/source.ts:16`）。该行会被替换为空行，因此堆栈跟踪中的行号仍然对应原代码（`codemode/src/source.ts:40`）。



<strong>描述。</strong> `createCodemodeDescription` 构建模型读取的内容：简介、全局对象列表、在所列工具需要时加入的共享 MCP 类型，以及按命名空间分组的每工具一个章节（`CA/src/extensions/codemode/tool.ts:248`）。仅列出 `read` 工具时，该构建生成如下内容：



````markdown
运行调用其他工具的 JavaScript。输入是原始 JavaScript（不是 JSON，不带代码围栏），在 QuickJS 沙箱中作为异步函数体执行：支持顶层 `await` 和 `return`。没有 Node、文件系统、网络或计时器。
- `await tools.<name>({ ...args })` 会 resolve 为字符串；若工具声明如此规定，则为对象；失败时以 Error reject。脚本结束时仍在运行的调用会被取消。
- 可选的第一行：// @options: {"max_output_tokens": 10000, "timeout_ms": 60000}
全局对象：
- `text(value)`、`image(dataUrlOrImageBlock)`、`console.log(...)` 和顶层 `return` 会添加输出；`exit()` 结束脚本。`image()` 还会将图像保存到临时文件，结果中会给出其路径。
- `store(key, value)` 和 `load(key)` 在多次 codemode 调用之间保留 JSON 值。
- `ALL_TOOLS`、`searchTools(query, { limit?, namespace? })`、`describeTool(name)`、`describeNamespace(name)`：查找未列出的工具，例如 MCP 工具。

嵌套工具：

### `read`
读取文件

codemode 工具声明：
```ts
declare const tools: { read(args: { path: string; }) : Promise<string>; };
```
````



这就是 `createCodemodeDescription([read], {})` 的完整输出（`research/out/codemode-sandbox.txt`）。由于未设置 `models` 选项，因此不包含 `models` 那一行。



三条规则决定哪些工具会拥有一个章节。



<strong>预算。</strong> 所列章节共用 `codemode.inlineBudget`，默认 3,000 个估算 token，按每 token 4 个字符计算（`CA/src/extensions/codemode/tool.ts:156`）。选择采用轮询方式：每轮中，每个命名空间组放入其剩余工具中代价最小的一个；如果某组的下一个工具无法放入剩余预算，该组就退出，因此在任何一个命名空间被完整列出之前，每个命名空间都会先出现（`CA/src/extensions/codemode/tool.ts:222`）。



<strong>延迟工具从不列出。</strong> 其中包括采用默认 `codemode` 暴露方式的 MCP 工具。它们“完全不影响描述，因此 MCP 服务器连接时，描述保持不变”（`CA/src/extensions/codemode/tool.ts:244`）。脚本通过 `searchTools(query)`（使用 BM25 排名，默认上限为 8）、`describeTool(name)` 和 `describeNamespace(name)` 查找它们（`CA/src/extensions/codemode/execute.ts:496`）。



<strong>`codemode.mode`。</strong> `on`（默认）只列出不采用 `direct` 暴露方式的可调用工具，并在每个已声明工具自身的描述中加上一行“Codemode：`tools.<id>(args)` resolve 为……”；`only` 则列出所有可调用工具，并从请求中移除已激活 `direct` 工具的声明（`CA/src/extensions/codemode/tool.ts:342`）。

## 运行脚本



<BookFigure id="6.4" />

> 嵌套调用的结果止于 VM；只有步骤 5 到达模型。步骤 3 是此图要强调的箭头：嵌套调用是拥有自身 ID 和钩子的完整工具调用。示意图来源：`CA/src/extensions/codemode/execute.ts`（`executeCodemode`、`toScriptValue`）和 `CA/src/core/nested-tool-calls.ts`（`NestedToolCallRunner`）。
> 
> 



<strong>嵌套调用。</strong> 脚本可以调用已激活的 `direct` 工具，以及所有 `codemode` 或 `deferred` 工具，但不能调用 codemode 本身，因为它的暴露方式是 `model-only`（`CA/src/extensions/codemode/tool.ts:392`）。每次调用都通过 `ctx.executeTool(name, args, { signal })`，因此校验、`tool_call` 和 `tool_result` 钩子，以及权限关卡，都与直接调用一样生效（`CA/src/extensions/codemode/execute.ts:405`）。嵌套调用的 ID 为 `<codemode call id>/<n>`，其中 `n` 从 1 开始计数；其执行事件携带 `parentToolCallId`（`CA/src/core/nested-tool-calls.ts:188`）。



调用会 resolve 为什么（`CA/src/extensions/codemode/execute.ts:347`）：

- 声明了 `outputSchema` 的工具会 resolve 为其 `structuredContent`；即使是错误结果，只要带有结构化内容，也同样如此。每个 MCP 工具都声明了该 schema。因此 MCP 调用会 resolve 为完整的 `CallToolResult`，包括 `isError`（“MCP”，原书第144页）

- 其他工具会 resolve 为其文本内容组成的一个字符串

- 失败、被阻止或无效的调用会以包含工具错误文本的 `Error` reject

    

<strong>存储。</strong> `store(key, value)` 和 `load(key)` 在不同调用之间保留 JSON 值。成功的脚本只要写入过任何内容，就会追加一个 `codemode-store` 自定义条目 `{ set, delete }`（`CA/src/extensions/codemode/execute.ts:451`）。`load()` 从根节点开始，沿当前分支重放这些条目（`CA/src/extensions/codemode/execute.ts:217`），因此存储会跟随 `/tree`、恢复和分叉操作（“会话：JSONL 树”，原书第86页）。失败的脚本不会报告任何写入。它的嵌套调用已经执行，而且不会有任何操作撤销它们。



<strong>结果。</strong> 内容首先是 `Script completed` 或 `Script failed`，然后是 `Wall time N seconds`，再接着是 `Output:`（`CA/src/extensions/codemode/execute.ts:470`）。返回值会像 `text()` 一样追加到输出中；失败时，会在部分输出后追加 `Script error:` 和错误信息。文本超过 `max_output_tokens` 时（默认 10,000；`CA/src/extensions/codemode/execute.ts:231`），会保留头尾，中间插入 `…N tokens truncated…` 标记，完整文本则写入临时文件。图像会保存为临时文件，结果中列出每个路径。



> <strong>经验法则</strong>
> 
> 如果模型需要结果的每一个字节，就让它直接调用工具。如果它需要计数、筛选，或合并多次调用的结果，就让它使用 codemode：嵌套结果留在 VM 中，上下文只需承担脚本打印内容的开销。脚本调用慢速服务器时，请在选项行设置 `timeout_ms`；Pi 自身不会设置执行期限。
> 
> 



> 来源：`codemode/README.md`（“结果”“工作原理”“存储”节）；`codemode/package.json`。`codemode/src/runtime/protocol.ts`（`WorkerData`、`WorkerToHostMessage`、`HostToWorkerMessage`）；`codemode/src/runtime/worker.ts`（`main`、`discardOutput`、`bridge`）；`codemode/src/runtime/host.ts`（`Execution`、`DEFAULT_TIMEOUT_MS`）；`codemode/src/runtime/prelude-source.ts`（限制、冻结）；`codemode/src/source.ts`（`CODEMODE_SOURCE_GRAMMAR`、`parseCodemodeSource`）。`CA/src/extensions/codemode/index.ts`；`CA/src/extensions/codemode/tool.ts`（`codemodeSchema`、`DESCRIPTION_INTRO`、`selectCatalog`、`createCodemodeDescription`、`prepareCodemodeLoadout`、`createCodemodeToolDefinition`）；`CA/src/extensions/codemode/execute.ts`（`executeCodemode`、`toScriptValue`、`readCodemodeStore`、`createDiscoveryGlobals`、`truncateOutput`）。`CA/src/core/nested-tool-calls.ts`（`NestedToolCallRunner.execute`）；`CA/src/core/settings-manager.ts`（`CodemodeSettings`）；`research/capture/codemodesandbox.mjs`；`research/out/codemode-sandbox.txt`。
> 
>
