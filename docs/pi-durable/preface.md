---
title: 如何阅读本书
---

<div class="section-kicker">PI DURABLE / ENGINEERING EDITION · 1.0.3</div>

# Pi Durable 技术手册

<BookFigure id="D.front.1" :show-caption="false" />

> 从最初的设计理念一直深入到存储的行记录，全面讲解持久化智能体运行框架：原子提交、在每个阶段设置检查点的任务、崩溃后的工具重放、分叉、子智能体、压缩、实时观察器，以及底层的 SQLite 和 JSONL 存储。
> 
> 



## 目录



1 模型  

[1\.1 Pi Durable 的用途（原书第10页）](/pi-durable/ch01/section-01)  

[1\.2 一页看懂架构（原书第13页）](/pi-durable/ch01/section-02)  

[1\.3 核心规则及其不变量（原书第16页）](/pi-durable/ch01/section-03)  

[1\.4 一次输入得到回答的全过程（原书第19页）](/pi-durable/ch01/section-04)



2 会话与提交  

[2\.1 记录与 ID（原书第25页）](/pi-durable/ch02/section-01)  

[2\.2 提交与变更串行队列（原书第29页）](/pi-durable/ch02/section-02)  

[2\.3 提交失败时会怎样（原书第33页）](/pi-durable/ch02/section-03)



3 对话与上下文  

[3\.1 条目与内置类型（原书第37页）](/pi-durable/ch03/section-01)  

[3\.2 从对话记录到模型上下文（原书第40页）](/pi-durable/ch03/section-02)  

[3\.3 分叉与有归属的对话（原书第43页）](/pi-durable/ch03/section-03)  

[3\.4 重置、交接与头指针（原书第46页）](/pi-durable/ch03/section-04)



4 文档  

[4\.1 定义文档（原书第50页）](/pi-durable/ch04/section-01)  

[4\.2 访问、创建与生命周期（原书第53页）](/pi-durable/ch04/section-02)  

[4\.3 基值、增量与迁移（原书第56页）](/pi-durable/ch04/section-03)  

[4\.4 内置文档（原书第60页）](/pi-durable/ch04/section-04)



5 任务  

[5\.1 作为状态机的任务（原书第63页）](/pi-durable/ch05/section-01)  

[5\.2 阶段、步骤与进度（原书第67页）](/pi-durable/ch05/section-02)  

[5\.3 副作用三明治（原书第70页）](/pi-durable/ch05/section-03)  

[5\.4 调度器（原书第73页）](/pi-durable/ch05/section-04)  

[5\.5 所有权与结构化并发（原书第76页）](/pi-durable/ch05/section-05)  

[5\.6 中止、故障与孤儿任务（原书第80页）](/pi-durable/ch05/section-06)



6 运行  

[6\.1 提交请求与收件箱（原书第84页）](/pi-durable/ch06/section-01)  

[6\.2 运行控制与实时文档（原书第88页）](/pi-durable/ch06/section-02)  

[6\.3 生成（原书第91页）](/pi-durable/ch06/section-03)  

[6\.4 工具调用与重放（原书第94页）](/pi-durable/ch06/section-04)  

[6\.5 压缩（原书第97页）](/pi-durable/ch06/section-05)  

[6\.6 用量与成本（原书第100页）](/pi-durable/ch06/section-06)



7 扩展与智能体  

[7\.1 扩展与注册表（原书第103页）](/pi-durable/ch07/section-01)  

[7\.2 每个对话的智能体（原书第106页）](/pi-durable/ch07/section-02)  

[7\.3 钩子（原书第109页）](/pi-durable/ch07/section-03)  

[7\.4 定义工具（原书第112页）](/pi-durable/ch07/section-04)  

[7\.5 系统提示词（原书第115页）](/pi-durable/ch07/section-05)  

[7\.6 运行时重新加载（原书第118页）](/pi-durable/ch07/section-06)  

[7\.7 子智能体（原书第121页）](/pi-durable/ch07/section-07)



8 观察  

[8\.1 Chord 与文档状态（原书第125页）](/pi-durable/ch08/section-01)  

[8\.2 对话视图与 `watch()`（原书第129页）](/pi-durable/ch08/section-02)  

[8\.3 智能体事件（原书第133页）](/pi-durable/ch08/section-03)  

[8\.4 任务图与 `inspect()`（原书第137页）](/pi-durable/ch08/section-04)



9 存储与环境  

[9\.1 存储契约（原书第141页）](/pi-durable/ch09/section-01)  

[9\.2 SQLite（原书第144页）](/pi-durable/ch09/section-02)  

[9\.3 JSONL（原书第148页）](/pi-durable/ch09/section-03)  

[9\.4 内存、符合性与可移植性（原书第152页）](/pi-durable/ch09/section-04)  

[9\.5 执行环境（原书第155页）](/pi-durable/ch09/section-05)



10 实践  

[10\.1 构建编码智能体（原书第159页）](/pi-durable/ch10/section-01)  

[10\.2 容易踩坑的契约（原书第163页）](/pi-durable/ch10/section-02)  

[10\.3 限制与非目标（原书第168页）](/pi-durable/ch10/section-03)



R 参考  

[R\.1 Harness 与 Conversation API（原书第172页）](/pi-durable/reference/section-01)  

[R\.2 内置类型（原书第179页）](/pi-durable/reference/section-02)  

[R\.3 设置与默认值（原书第180页）](/pi-durable/reference/section-03)  

[R\.4 错误与原因（原书第183页）](/pi-durable/reference/section-04)  

[R\.5 术语表（原书第185页）](/pi-durable/reference/section-05)  

[R\.6 来源（原书第187页）](/pi-durable/reference/section-06)  

[R\.7 插图索引（原书第189页）](/pi-durable/reference/section-07)



## 如何阅读本书



这是一个软件包在某次提交时的全貌图；书中的每条记录、每个文件和每个事件，都来自实际运行该软件包。



本书介绍 Pi Durable，即 npm 软件包 `@earendil-works/pi-durable` 的 1\.0\.3 版本，对应仓库 `earendil-works/pi` 的提交 `5b6c792`（2026年10月5日）。本书从运行框架的一条核心规则讲起，一直深入到 SQLite 文件中的行记录；展示的每条记录都从真实运行中捕获而来。



## 本书面向谁



你是一位 TypeScript 工程师，曾经构建或使用过 LLM 智能体：这种循环把对话记录发给模型，执行模型返回的工具调用，再把结果发回去。你可能用过 Pi 编码智能体，但还没有读过 Pi Durable 的源代码或规范。读完本书后，你将能够为任务设计合适的阶段，并预判运行过程中任何时刻发生崩溃时，哪些内容能保留下来。你还可以逐行阅读存储转储，编写可安全重新运行的工具，以及找出运行卡住的原因。



<aside class="manual-callout callout-warning durable-callout" role="note" data-source-page="4">

<strong>实验性</strong>

README 开篇用一句话说明项目状态：“API 在各版本之间可能不经通知而发生变化。”本书的所有内容均适用于 1\.0\.3。若要在后续版本中依赖某项细节，请先查看 CHANGELOG。

</aside>



## 本书如何编写



本书没有任何内容是凭记忆写成的。每节末尾都有“来源”一行，列出写作所依据的文件。除非路径以 `research/` 开头，否则均相对于 `research/pi/packages/durable/`。各类来源的权威性按以下顺序排列：



|<strong>来源</strong>|<strong>路径</strong>|<strong>用途</strong>|
|---|---|---|
|源代码|`src/**`|每个类型、默认值、字段名及行为；引用形式为 `src/harness/tool.ts`|
|规范|`docs/spec.md`|每条规则，均按原文引用；引用形式为 `spec §5.2`|
|README、变更日志|`README.md`、`CHANGELOG.md`|作者对外呈现的公共接口|
|设计笔记|`docs/pico-v5-handoff.md`、`docs/pico-v5-chord-usage.md`|规则存在的原因|
|测试|`test/*.test.ts`|边界情况的确切行为|
|示例|`test/examples/NN-*.ts`、`research/runs/`|可运行的代码及其输出；引用形式为 `ex 24`、`run 24`|
|捕获工具集|`research/capture/`|书中展示的每条记录、每个文件、每个事件及每份对话记录|



源代码优先于规范。两者不一致时，正文会明确指出。规范使用系统的内部名称 Pico5，而且早于代码：§2\.2 仍写着“Pico5 尚未实现”。本书在其他地方统一使用软件包名 Pi Durable。无法追溯到上述任何文件的说法，都已删除。



## 捕获工具集



本书的记录来自一组脚本：它们驱动软件包运行，并写出软件包所存储的内容。这些脚本位于 `research/capture/`，使用 `@earendil-works/pi-ai` 的 faux 提供商运行，因此不需要网络，也不需要 API 密钥。其中一个脚本通过一次工具调用回答一个输入，并转储每一条 SQLite 行记录和每一个 JSONL 文件。另一个脚本在两次工具调用执行期间终止进程，并记录第二个进程所发现的内容。其他脚本记录任务转换、观察操作、智能体事件、收件箱步骤和派生上下文。每个脚本都像示例一样从软件包目录运行；代码清单的标题会注明其摘录自哪个捕获文件。



捕获内容中的 ID 和提交编号在各次运行之间保持稳定，时间戳、进程 ID 和 UUID 则不稳定。有一点可能发生偏移：一个经过节流的进度提交可能提前或延后一个提交落盘，从而使后续序号整体偏移一位。见 `research/capture/README.md`。



## 约定



方法、选项、字段、类型、状态和原因均使用代码字体。句中引用来源时，使用 `spec §4` 或 `src/session/session.ts` 这样的形式。诸如“副作用三明治（原书第70页）”这样的交叉引用，所列页码均为印刷版页码。



记录按存储中的原貌展示：经过美化排版的 JSON，使用两个空格缩进，键按存储时的顺序排列。代码清单如有删节，会用 `…` 标记，并在下方说明中指出删去了什么。



规范用普通陈述句书写规则，不使用 RFC 2119 规定的大写关键词；其中小写的“must”（必须）仍然是一条规则。本书逐字引用这些规则。



## 第一个可运行的对话



这个小应用会提出一个问题，关闭 SQLite 存储，然后重新打开它并读取已保存的答案。一个模拟模型始终回复“Paris\.”，所以不需要 API 密钥。请使用 Node 24，将清单保存为 `first-conversation.mjs`，并在一个新建文件夹中运行。



```bash
$ npm init -y
$ npm install @earendil-works/pi-durable@1.0.3 \
    @earendil-works/pi-ai@1.0.3 @earendil-works/chord@1.0.3
$ node first-conversation.mjs
```



<strong>保存一个答案，然后重新打开</strong> · `manual/examples/first-conversation.mjs`



```js
import { BACKGROUND_CONTEXT } from '@earendil-works/chord/context';
import { createModels } from '@earendil-works/pi-ai/models';
import {
    fauxAssistantMessage, fauxProvider,
} from '@earendil-works/pi-ai/providers/faux';
import { createRegistry, Harness } from '@earendil-works/pi-durable';
import { openNodeSqliteStorage } from '@earendil-works/pi-durable/storage/sqlite/node';

const context = BACKGROUND_CONTEXT;
const faux = fauxProvider();
const models = createModels();
models.setProvider(faux.provider);
faux.setResponses([fauxAssistantMessage('Paris.')]);
const options = { models, registry: createRegistry() };
const path = process.env.DEMO_DB ?? './conversation.db';

let harness = await Harness.open(await openNodeSqliteStorage(path), options, context);
const root = await harness.root(context, {
    agent: { model: { provider: 'faux', modelId: 'faux-1' } },
});
const input = await root.submit({
    type: 'input', content: 'Capital of France?', requestId: 'capital-1',
}, context);
const result = await input.wait(context);
if (result.status !== 'done') throw new Error('The input was not answered');
await harness.close(context);

harness = await Harness.open(await openNodeSqliteStorage(path), options, context);
const reopened = await harness.root(context);
const page = await reopened.entries({}, 10, undefined, context);
const answer = page.items.find((entry) => entry.id === result.answer);
if (answer?.kind !== 'pi.assistant') throw new Error('Saved answer missing');
console.log('saved answer:', JSON.stringify(answer.model[0]?.content));
await harness.close(context);
```



这是完整示例，已针对固定版本的软件包构建进行测试。faux 提供商使用真实的运行框架和 SQLite 存储；它不会调用远程模型。



```ts
saved answer: [{"type":"text","text":"Paris."}]
```



该进程退出后，数据库仍保留对话。再次运行这个文件时，相同的 `requestId` 会返回已保存的提交请求，而不会重复提问。这验证了存储和重新打开的行为；它并不模拟工具副作用执行期间的崩溃。



有三点值得注意：`models` 提供模型，`registry` 保存扩展代码，`context` 传递取消信号。`root` 是接收提交请求的对话。后续各章将解释这些调用会保存什么，以及如何恢复中断的工作。



后续简短代码片段中使用的 `MemoryStorage` 只把所有内容保存在 RAM 中。如果需要重新打开已保存的工作，请使用 SQLite 这样的持久化后端。恢复未完成的工作之前，请重新安装相同的扩展和任务代码。



来源：`ex 14`；`src/storage/sqlite/node.ts`；`src/harness/harness.ts`；`manual/examples/first-conversation.mjs`



## 运行示例



软件包在 `test/examples/` 中附带了可运行示例，编号为 00 到 31。较小编号的示例使用 Harness 下方的各层；从 14 开始，示例构建真正的智能体。从软件包目录运行任意一个示例即可；大多数使用 faux 提供商，不需要密钥。见 `README §Examples`：



```bash
$ node --conditions=source --experimental-strip-types test/examples/14-chat.ts
answer: [ { type: 'text', text: 'Paris.' } ]
transcript: [ 'pi.user', 'pi.system', 'pi.assistant' ]
```



每个示例的输出都保存在 `research/runs/` 中，书中以 `run 14` 这样的形式引用。某节展示的对话记录一定来自这些文件之一或一次捕获，绝不是重构出来的。



## 各部分的编排顺序



全书先从理念讲到字节，再延伸到实践。第1部分用通俗语言介绍完整模型，之后每个部分都会深入其中的一层。



|部分|涵盖内容|
|---|---|
|1 · 模型|运行框架的用途、各个层次、核心规则及其八个不变量，以及一个输入得到回答的端到端过程。请完整通读一次|
|2 · 会话与提交|记录与 ID、提交与变更串行队列，以及提交失败时发生的事情|
|3 · 对话与上下文|条目及其类型、如何从对话记录生成模型上下文、分叉、重置和头指针|
|4 · 文档|定义带类型的状态、作用域与生命周期、基值与增量，以及五种内置文档|
|5 · 任务|作为状态机的任务、步骤规则、副作用三明治、调度器、所有权与中止|
|6 · 运行|提交请求与收件箱、实时文档、生成、工具调用、压缩与用量|
|7 · 扩展与智能体|注册表、每个对话的智能体、钩子、工具、系统提示词、重新加载和子智能体|
|8 · 观察|Chord 状态、对话视图与 `watch()`、智能体事件和任务图|
|9 · 存储与环境|存储契约、SQLite、JSONL、符合性与执行环境|
|10 · 实践|构建编码智能体、容易踩坑的契约，以及限制与非目标|
|R · 参考|API、内置类型、设置与默认值、错误与原因、术语表、来源和插图索引|



## 插图中的颜色



所有插图都使用统一的颜色编码，每种颜色在全书中都具有相同含义。

|颜色|含义|颜色|含义|
|---|---|---|---|
|蓝色|对话、条目、对话记录|梅紫色|模型、生成、提供商|
|水蓝色|Session、提交、存储记录|深绿色|工具、环境、外部副作用|
|紫罗兰色|提交请求与收件箱|靛蓝色|视图、观察、事件、观察者|
|绿色|文档与 Chord 状态|玫瑰色|崩溃、中止、故障、错误、丢失的工作|
|琥珀色|任务、阶段、检查点|灰色|宿主应用；带斜线填充时，表示处于活动范围之外|



时序图为每个参与方画出一条垂直生命线，时间沿页面向下推进。箭头样式表示交互类型。图中重点讲解的箭头会画得更粗，并使用粗体标签。左侧页边的编号圆圈表示步骤编号；在展示捕获运行的图中，它们是存储中提交的序号。



<strong>图0\.1 如何阅读时序图</strong>



<strong>时序图</strong>



<BookFigure id="D.front.2" :show-caption="false" />

> 本书的每次交互都使用同一套八种箭头样式绘制。指向 Storage 的箭头表示提交；琥珀色箭头表示该提交唯一的写入是任务状态变化。如果 1\.4 节（原书第19页）所展示的单轮捕获中包含相应交互，标签就沿用那次捕获的标注。
> 
> 



