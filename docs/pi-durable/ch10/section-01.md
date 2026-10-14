---
title: "构建编码智能体"
---

<div class="section-kicker">PI DURABLE / 10.1 · P. 159</div>

# 构建编码智能体

---

> 编码智能体由一个注册表、一个设置对象和一个环境函数组成；用户为每段对话所做的选择，都以名称的形式保存在 `pi.agent` 中。
> 
> 

想象一个编码助手。用户将它切换到只读的计划模式，让它指向另一个文件夹，然后合上笔记本电脑。明天，它必须完全恢复到用户离开时的样子。只有把每项选择放在正确的位置，才能做到这一点。示例 26 至 31 展示了这些位置。读完本节，你就能把任何产品功能归到代码、策略或已存储的选择中，并说明一项变更何时生效。



<BookFigure id="D.10.1" :show-caption="false" />

> 代码和策略留在进程中；对话只存储自己的选择。Harness 每次需要它们时，都会将两者结合起来。本图根据示例 26–29 和 `src/harness/agent.ts` 整理。
> 
> 

## 三项宿主输入，一个已存储的文档



除了存储和模型，宿主程序还会向 `Harness.open()` 提供三样东西。它们都不会被存储，改变其中任何一个也都不会产生提交。提交是一次原子保存，其中的所有内容要么一起存入，要么完全不存：

- <strong>注册表</strong>：代码，也就是按名称安装的扩展。安装第二个同名扩展会替换第一个，参见“扩展与注册表”（原书第103页）。

- <strong>设置</strong>：所有对话共享的运行策略，例如重试和并行工具。Harness 每次需要时都会读取它们。

- <strong>环境函数</strong>：`env(target)` 构造某一段对话中的工具所能看到的文件系统和 shell。



用户为某段对话所做的选择，会存入该对话的 `pi.agent` 文档：模型、思考级别、扩展和工具名称、指令，以及工作目录（`cwd`）。它存储的是名称，绝不是代码，参见“每段对话的智能体”（原书第106页）。每一步开始前，Harness 都会在注册表中查找这些名称，取得真正的工具和提示词区段。

## 动态设置与会变化的文件夹



示例 26 是基础智能体。它安装了 `CodingTools`（`read`、`write`、`edit` 和 `bash` 工具），以及一个小型提示词扩展。不会有任何东西替你安装 `CodingTools`，见 `src/tools/index.ts`。设置通过 getter 读取用户会编辑的对象，环境则跟随对话的 `cwd`。



随文件变化的设置，以及跟随 `cwd` 的 `env`：`test/examples/26-coding-agent.ts`

```ts
const userSettings = { parallelTools: true, maxRetries: 3 };
const settings: HarnessSettings = {
    get toolExecution() {
    return userSettings.parallelTools ? "parallel" : "sequential";
    },
    get retry() {
    return { maxRetries: userSettings.maxRetries };
    },
};
const env = ({ cwd = workspace }: { readonly cwd?: string }) =>
    new NodeExecutionEnv({ cwd });
...
await root.configure({ cwd: join(workspace, "app") }, context);
userSettings.parallelTools = false;
```

> 此处省略了 Harness 的 `open()` 调用和第一个轮次（…）。第一次 `pwd` 打印工作区路径，第二次打印 `workspace/app`（运行 26）。这两项变更都没有重启任何东西。
> 
> 



两项变更都从下一次使用起生效。每次决策都会重新读取设置；缺失字段使用默认值，见 `src/harness/agent.ts` 的 `resolveSettings`。`cwd` 的变更会提交到 `pi.agent`，下一次工具调用的 `env()` 就能看到它。由此带来一个后果：环境是按调用构造的，因此工具在崩溃后重新运行时，使用的是对话届时的目录，可能与首次尝试时使用的目录不同，见 `src/harness/tool.ts:253`。

## 计划模式是一项智能体变更



示例 27 不改动注册表，就能让一段对话变为只读。计划扩展带来了 `submit_plan` 工具和 `plan_mode` 提示词区段。它将计划保存在自己的文档 `app.plan` 中。这个文档是可回溯的，因此分叉会保留分叉点当时的计划，参见“定义文档”（原书第50页）。进入和退出计划模式，就是两次 `configure()` 调用。



进入和退出计划模式：`test/examples/27-plan-mode.ts`

```js
const read = createReadTool();
const enterPlanMode = { extensions: { add: [Plan] }, tools: [read, submitPlan] };
const leavePlanMode = { extensions: null, tools: null };

await root.configure(enterPlanMode, context);
const input = { type: "input", content: "Make the port configurable." } as const;
await (await root.submit(input, context)).wait(context);
await root.configure(leavePlanMode, context);
```

> 取自示例第 60–62 行和第 93–98 行；为适应页面宽度，提交请求被提取到 `input` 中。
> 
> 



```YAML
$ node --conditions=source --experimental-strip-types test/examples/27-plan-mode.ts
tools: [ 'read', 'write', 'edit', 'bash' ]
plan mode tools: [ 'read', 'submit_plan' ]
plan: [ 'Read PORT from the environment', 'Default to 3000' ]
tools again: [ 'read', 'write', 'edit', 'bash' ]
system: { sections: { plan_mode: '<plan_mode>\n...' },
    added: [ 'read', 'submit_plan' ], ... }
system: { sections: { plan_mode: null },
    added: [ 'write', 'edit', 'bash' ], removed: [ 'submit_plan' ] }
```

> 运行 27，第一行 `system` 已缩短。模型看到的每次切换都是一小段系统提示词变更，而不是一个全新的提示词，参见“系统提示词”（原书第115页）。
> 
> 



有三个细节让它得以运作。`{ add: [Plan] }` 在宿主默认扩展的基础上添加扩展，而 `tools` 数组则严格按给定顺序提供其中的工具。将两者都设为 `null` 会去掉覆盖设置，让对话重新跟随宿主默认值。此外，`submit_plan` 会交还控制权：`{ terminate: true }`。当一轮中的每个工具结果都提出这个要求时，运行便会结束，不再向模型发出请求，见 README §Tools。

## 审查者与沙箱：以对话为单位



示例 28 添加了一位审查者：它是第二段对话，拥有自己的智能体，使用更便宜的模型，只提供 `read` 工具，并以自己的检出目录作为 `cwd`。它的 `reviewer` 扩展带有 `onYield` 钩子。只要回答中还没有出现 “No further findings\.”，钩子就会返回 `{ continue: … }`，添加一条用户消息，让运行继续，参见“钩子”（原书第109页）。这些内容全部存储在 `pi.agent` 中，因此重启之后，审查者仍然是审查者。



示例 29 为每位用户的对话分配一个独立的沙箱文件夹。`app.sandbox` 文档保存路径，并在创建对话时写入。`env` 函数读取它，据此构造环境。该文档的分叉策略是 `initial`，因此分叉最初没有路径；此时 `env` 返回 `undefined`，内置工具会报错 “No execution environment is configured”，见 `src/tools/env.ts`。子智能体也不会继承这个文档：如果子对话需要共享沙箱，创建者就必须为它写入一个文档，见 spec §2\.2。

## 替换和装饰工具



<BookFigure id="D.10.2" :show-caption="false" />

> 选择顺序决定哪个同名工具胜出，包装器则装饰胜出的工具。两段对话共享一个注册表。数值来自示例 30 和运行 30；项目路径缩写为 `<project>`。
> 
> 



示例 30 需要一个会激活 Python virtualenv 的 `bash`，但只在部分对话中需要。`venv` 扩展自带名为 `bash` 的工具。工具按选择顺序、依名称收集，因此后面的扩展所提供的 `bash` 会替换前面的同名工具。包装器在这之后应用，见 `src/harness/agent.ts` 的 `resolveAgent`，所以计时包装器会为胜出的那个 `bash` 计时。包装器按名称引用工具，因此不论重新加载哪个 `bash`，它都会继续受到包装。

## 变更何时到达



每一种输入都有自己的生效时机。下表回答产品团队首先会问的问题：如果我现在改了它，谁会看到？

|<strong>变更</strong>|<strong>何时读取</strong>|<strong>何时生效</strong>|
|---|---|---|
|设置的 getter|每次使用时|下一次决策时；不写入任何内容|
|`configure()` 的模型、工具、提示词区段|每次模型请求前|下一次请求时；当前请求保留原有提示词|
|`configure({ cwd })`|每次使用时由 `env()` 读取|下一次工具调用时，即使该调用已经由模型发出|
|安装或替换扩展|每个阶段开始时，以及每次请求和调用时|下一阶段；正在执行的调用仍使用旧代码直到结束|
|进程重启|重新安装之后|已存储的名称绑定到新安装的代码|



依据 spec §2\.2、README §Per\-Conversation Agent 和 §Reload，以及运行 31：重新加载期间正在执行的调用打印 `v1`，下一个调用打印 `v2`；重启后的进程在安装扩展之前不会提供任何工具，参见“运行时重新加载”（原书第118页）。



<strong>这对你意味着什么：</strong>

- 把代码放进注册表，把共享策略放进设置，把每段对话的选择放进 `pi.agent`。

- 对话还有什么内容需要跨重启记住，就把它放进你自己的文档。

- 重新打开之前，先安装所有扩展；没有相应的代码，存储的名称毫无用处。
