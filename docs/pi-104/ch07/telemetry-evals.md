---
title: "遥测与评测"
originalPage: 179
---

<div class="section-kicker">7.3 / EXPERIMENTAL & OPERATIONS</div>

# 遥测与评测

---

Pi 提供了一套 span 约定，但仓库中没有任何代码向其发出 span；它还提供了默认开启的安装 ping。其评测衡量的是另一件事：自身文档在多大程度上帮助模型完成任务。



这里的遥测指三种不同的事，很容易混淆。`pi-telemetry` 是用于追踪的接口库。产品遥测是编码智能体发送给 `pi.dev` 和提供商的少量数据。评测是一个私有软件包，针对模型运行真实的智能体会话，并为结果评分。本节按这个顺序介绍，准确说明哪些信息会在什么时候离开机器，最后讲述评测运行如何被隔离，以及如何报告结果。

## pi\-telemetry：没有生产方的约定



该软件包自称提供“供应商中立的遥测约定和带类型的 schema 实用工具”，且“不包含导出器、全局当前 span 状态，也不依赖遥测后端”，见 `telemetry/README.md:11`。包括一致性测试套件在内，它共有 935 行，而且不读取任何环境变量：在 `telemetry/src` 中 grep `process.env` 没有任何结果。



<strong>完整的运行时约定</strong> · 来源：`telemetry/src/index.ts`

```ts
export interface TelemetryContext {
    startSpan<T>(options: SpanOptions, callback: (span: TelemetrySpan) => T | Promise<T>): Promise<T>;
}
export interface TelemetrySpan extends TelemetryContext {
    addEvent(name: string, attributes?: SpanAttributes): void;
    setAttributes(attributes: SpanAttributes): void;
    focal Status(status: SpanStatus): void;
}
```

> 译注：已修复可明确判断的 `start Span`、`add Event` 以及 `set Attributes.attributes:` 的空格或标点损坏。所提供文本中的 `focal Status` 无法唯一还原，因此原样保留；这一行不是合法的 TypeScript，不能把本代码块视为可直接编译的源码。

> <strong>PDF核对注（原书第179页）：</strong> 原始 PDF 的对应接口行为 `setStatus(status: SpanStatus): void;`。上方保留所提供译稿的 `focal Status` 及译注，便于核对；此处仅记录原书中的明确写法。
> 
> 



以上完整对应第14至22行。`SpanStatus` 为 `{ status: "ok" }` 或 `{ status: "error"; error?: { name, message } }`；属性值是标量或由同一种标量类型组成的数组，见 `telemetry/src/index.ts:1`。



Span 的作用域由回调限定：一个 span 只存在于 `startSpan` 回调内部，而 span 本身也是子 span 的上下文。围绕这一约定，该软件包导出了 `NOOP_TELEMETRY_CONTEXT`，见 `telemetry/src/noop.ts:20`；参考实现 `InMemoryTelemetryContext`，见 `telemetry/src/memory.ts:192`；schema 辅助函数 `defineTelemetrySchema` 和 `createTypedSpanStarter`，见 `telemetry/src/index.ts:72`；以及位于 `@earendil-works/pi-telemetry/testing` 的适配器一致性测试套件，见 `telemetry/src/testing/index.ts:1`。



`pi-ai` 在每个提供商请求上通过 `telemetryContext` 接受上下文，即“该逻辑请求生成遥测时所使用的显式父上下文”，见 `ai/src/types.ts:136`，并将它复制到 simple\-stream 选项中，见 `ai/src/api/simple-options.ts:48`。这就是全部集成内容。在 `telemetry/` 之外的全部十四个软件包中 grep `startSpan`，找不到任何调用，因此传给 `pi-ai` 的上下文不会收到 span。



<BookFigure id="7.7" />

> 约定是完整的；缺少的是生产方。实色表示实际存在的代码；玫瑰色斜线填充表示 `telemetry/README.md` 的“Pi 软件包集成”一节让读者预期存在、却找不到的内容。来源是在 `28dcce2` 上对 `packages/*/src` 的 grep；此图为示意图。
> 
> 



> <strong>文档 ≠ 代码</strong>
> 
> `telemetry/README.md` 说“`@earendil-works/pi-agent-core` 拥有并导出 Pi 的 AI 请求和运行框架 schema”，还展示了从中导入 `AGENT_TELEMETRY_SCHEMAS`、`AI_TELEMETRY_SCHEMA`、`HARNESS_TELEMETRY_SCHEMA`、`startAiSpan` 和 `startHarnessSpan`。除这份 README 外，这五个符号在仓库其他任何位置都不存在，而且 `pi-agent-core` 并不依赖 `pi-telemetry`。应把这个软件包当作可据以实现适配器的接口，而不是 Pi span 的来源。
> 
> 

## 编码智能体发送什么



产品遥测位于编码智能体中，而不在 `pi-telemetry` 中。一个开关控制它：



<strong>安装遥测开关</strong> · 来源：`CA/src/core/telemetry.ts`

```ts
function isTruthyEnvFlag(value: string | undefined): boolean {
    if (!value) return false;
    return value === "1" || value.toLowerCase() === "true" || value.toLowerCase() === "yes";
}

export function isInstallTelemetryEnabled(
    settingsManager: SettingsManager,
    telemetryEnv: string | undefined = process.env.PI_TELEMETRY,
): boolean {
    return telemetryEnv !== undefined ? isTruthyEnvFlag(telemetryEnv) :
    settingsManager.getEnableInstallTelemetry();
}
```



以上是该文件除导入语句外的全部内容。只要设置了 `PI_TELEMETRY`，它就具有优先权：`1`、`true` 或 `yes` 开启遥测，其他任何值，包括空字符串，都会关闭遥测。若未设置，则由 `enableInstallTelemetry` 设置决定；其默认值为 `true`，见 `CA/src/core/settings-manager.ts:1142`。

|<strong>发送内容</strong>|<strong>发送时机</strong>|<strong>控制条件</strong>|
|---|---|---|
|GET https://pi\.dev/api/report\-install?version=\<v\> with User\-Agent: pi/\<v\> \(\<platform\>;\<runtime\>; \<arch\>\), 5 s 超时，忽略响应。|交互模式中的新会话；没有记录变更日志版本时（全新安装），或变更日志包含比已记录版本更新的条目时，见 `CA/src/modes/interactive/interactive-mode.ts:1324`|先检查是否设置了任意值的 `PI_OFFLINE`，再检查 `isInstallTelemetryEnabled`，见 `CA/src/modes/interactive/interactive-mode.ts:1351`|
|OpenRouter 请求头：`HTTP-Referer: https://pi.dev`、`X-OpenRouter-Title: pi`、`X-OpenRouter-Categories: cli-agent`|向 OpenRouter 模型发出的每次请求|`isInstallTelemetryEnabled`，见 `CA/src/core/provider-attribution.ts:40`|
|NVIDIA NIM：`X-BILLING-INFOKE-ORIGIN: Pi`；Cloudflare：`User-Agent: pi-coding-agent`|向这些主机发出的每次请求|`isInstallTelemetryEnabled`|
|OpenCode：`x-opencode-session:`、`x-opencode-client: pi`|向 `opencode`、`opencode-go` 或 `opencode.ai` 发出的每次请求|不受开关控制，见 `CA/src/core/provider-attribution.ts:67`|
|`GET https://pi.dev/api/latest-version`，10 s 超时|交互模式启动时的版本检查|`PI_OFFLINE` 或 `PI_SKIP_VERSION_CHECK`，见 `CA/src/utils/version-check.ts:5`|

> <strong>PDF核对注（原书第181页）：</strong> NVIDIA NIM 请求头在原始 PDF 中为 `X-BILLING-INVOKE-ORIGIN: Pi`；上表保留所提供译稿中的 `X-BILLING-INFOKE-ORIGIN: Pi`。

> 一次 ping、三个归属标识请求头、一个会话请求头，以及一次版本检查。这些请求头来自 `mergeProviderAttributionHeaders()`；该函数最后合并请求自身的头部，因此请求自身的头部会覆盖这些值；随后 `before_provider_headers` 扩展处理器会看到合并结果，见 `CA/src/core/sdk.ts:337`。模型目录刷新是另一个独立请求，见“提供商与模型”（原书第24页）。
> 
> 



`PI_OFFLINE` 有两种检查方式。`main()` 将 `1`、`true`、`yes` 或 `--offline` 视为离线，然后设置 `PI_OFFLINE=1`，见 `CA/src/main.ts:576`。安装 ping 和版本检查只判断变量是否为非空，因此 `PI_OFFLINE=0` 也会抑制它们。



`enableAnalytics` 默认为 `false`，见 `CA/src/core/settings-manager.ts:1152`。只有首次设置界面会写入它，见 `CA/src/cli/startup-ui.ts:193`；而该界面只在以下条件同时成立时运行：`PI_EXPERIMENTAL=1`、使用官方发行版、采用默认智能体目录，并且尚无 `settings.json`，见 `CA/src/cli/startup-ui.ts:131`。选择加入时还会保存一个随机 `trackingId`，见 `CA/src/core/settings-manager.ts:1160`。在 `28dcce2` 中，没有任何代码读取这两个值：`getEnableAnalytics()` 和 `getTrackingId()` 没有调用方，而错误报告包会从所附设置中删除 `trackingId` 和 `deviceId`，见 `CA/src/core/bug-report.ts:62`。





> <strong>经验法则：</strong>对于不允许向外回传自身信息的机器，应设置 `PI_OFFLINE=1` 和 `PI_TELEMETRY=0`。前者会停止 ping、版本检查、目录刷新和软件包自动安装；后者会移除归属标识请求头。两者都不会移除 OpenCode 会话请求头，该头部只会发送给 OpenCode。
> 
> 

## 评测



`packages/evals` 对应 `@earendil-works/pi-evals`，标记为 `private`，从未发布，见 `evals/package.json`。它基于 `vitest-evals 0.15.0` 构建，运行真实的进程内 `AgentSession`。运行框架先将 `HOME`、`USERPROFILE` 和 `PI_CODING_AGENT_DIR` 指向一个全新的临时目录，见 `evals/src/harness.ts:82`，再使用 `createAgentSessionServices` 创建服务，并使用 `createAgentSessionFromServices` 创建会话，见 `evals/src/harness.ts:337`。每次运行都会在一个 `mkdtemp("pi-eval-")` 根目录下，获得独立的主目录、智能体目录、工作区和会话目录，见 `evals/src/harness.ts:283`。提供商凭据从宿主机的 `auth.json` 复制到内存存储中；如果加载了自身内联扩展之外的任何扩展，运行就会失败并报出“Isolated eval loaded unexpected extensions”（隔离评测加载了意外扩展），见 `evals/src/harness.ts:362`。



|<strong>类型</strong>|<strong>文件</strong>|<strong>运行方式</strong>|<strong>衡量内容</strong>|
|---|---|---|---|
|宿主机评测|`evals/*.eval.ts`：`smoke`、`documentation-audit`|`npm run eval:host`，在本机运行 Vitest|普通的通过或失败；`smoke` 在不提供工具的情况下询问法国首都，并期望回答 Paris，见 `evals/evals/smoke.eval.ts`|
|文档提升效果评测|`evals/*.docs.eval.ts`：`custom-provider`、`extensions`、`models`、`openai-provider`、`tui`|`npm run eval:docs`，每个实验组使用一个 Docker 容器|`without_docs` 和 `with_docs` 之间的通过率差异|



两个套件：一个检查智能体是否正常工作，另一个检查文档是否有帮助。两者都需要 `PI_PROVIDER` 和 `PI_MODEL`，它们必须同时设置或同时不设置，见 `evals/src/cli.ts:76`。`PI_EVAL_RUNS_PER_VARIANT` 或 `--runs-per-variant` 设置重复次数；默认是一次，见 `evals/src/cli.ts:79`。



`without_docs` 镜像不包含编码智能体的 `README.md`、`CHANGELOG.md`、`docs/` 和 `examples/`，运行框架还会从默认系统提示中删去“Pi documentation”（Pi 文档）一节；如果提示中没有这一节，就会抛出异常，见 `evals/src/harness.ts:498`。`with_docs` 则保留文档和提示中的这一节。文档评测只允许使用 `read`、`write`、`edit`、`grep`、`find` 和 `ls`，见 `evals/src/harness.ts:485`，因此模型没有 shell。容器内的运行框架会降权到一个非特权 UID，此后评测定义和评分器就不可读取，见 `evals/README.md` 的“文档变体”一节。



<BookFigure id="7.8" />

> 一次对照实验要么包含全部配对，要么不报告总体指标。只有两个实验组都恰好产生一个分数时，该配对才计入统计；实验组缺失、重复、跳过或出错都会阻止报告总体指标，而且进程会以非零状态退出。运行顺序按运行编号交替，以减少顺序偏差。来源：`evals/README.md` 的“运行文档对照实验”和“结果”两节。
> 
> 



结果写入被版本控制忽略的 `.eval/<timestamp>_<id>/` 目录：`protocol.json`，包含模型、镜像 id、案例和协议摘要；`expected-runs.json`；`observations.jsonl`；每个实验组的 `tasks/*/vitest.json`；`<variant>/sessions/*/session.jsonl` 下的原生 Pi 会话；以及 `report.json` 和 `report.txt`，见 `evals/README.md` 的“结果”一节。“产物可能包含提示、回答、生成的代码和工具输出。”



> 这对你意味着什么：
> 
> - 如果需要追踪，应提供自己的 `TelemetryContext` 适配器；在 1\.0\.4 中，Pi 不会向其中发出 span。
> 
> - 设置 `PI_TELEMETRY=0` 或 `enableInstallTelemetry: false`，以停止安装 ping 和归属标识请求头。
> 
> - 使用真实模型测试自己的扩展时，可以借鉴评测运行框架的模式：每次运行使用全新的主目录、智能体目录和工作区，并确保没有意外扩展。
> 
> 



> 来源：`telemetry/README.md`（简介、“Pi 软件包集成”一节）；`telemetry/src/index.ts`、`noop.ts`、`memory.ts`、`testing/index.ts`；`ai/src/types.ts`（`ProviderRequestOptions.telemetryContext`）；`ai/src/api/simple-options.ts`；在 `packages/*/src` 中 grep `startSpan` 和 README 中的五个符号；`CA/src/core/telemetry.ts`；`CA/src/core/provider-attribution.ts`；`CA/src/core/settings-manager.ts`（`enableInstallTelemetry`、`enableAnalytics`、`trackingId`）；`CA/src/modes/interactive/interactive-mode.ts`（`getChangelogForDisplay`、`reportInstallTelemetry`）；`CA/src/utils/version-check.ts`；`CA/src/main.ts`（离线模式）；`CA/src/cli/startup-ui.ts`（`shouldRunFirstTimeSetup`）；`CA/src/core/bug-report.ts`；`evals/package.json`；`evals/README.md`；`evals/src/harness.ts`、`cli.ts`、`docker.ts`；`evals/evals/smoke.eval.ts`、`documentation-audit.eval.ts`。
> 
>
