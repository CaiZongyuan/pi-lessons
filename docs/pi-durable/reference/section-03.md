---
title: "设置与默认值"
---

<div class="section-kicker">PI DURABLE / R.3 · P. 180</div>

# 设置与默认值



宿主传给 `Harness.open()` 的每个选项、每个设置键及其内置默认值，以及源码中写死的其他默认值。



设置每次需要时都会读取，从不存储。不提供某个字段，就会取得其默认值；对于 `retry` 这样的对象，每个缺失键都会分别取得自己的默认值。getter 可以让设置动态生效，参见“构建编码智能体”（原书第159页）。



## HarnessOptions



|字段|类型|默认值|参见|
|---|---|---|---|
|`models`|pi\-ai 的 `Models`|必填|6\.3（原书第91页）|
|`registry`|`RegistryReader`|必填；必须包含内置任务|7\.1（原书第103页）|
|`settings`|`HarnessSettings`|每个字段均取默认值|7\.2（原书第106页）|
|`env`|`(target, ctx) => ExecutionEnv \| undefined`|无：没有环境|9\.5（原书第155页）|
|`conversationCreated`|`(tx, record) => void`|无|4\.2（原书第53页）|
|`now`|`() => number`|`Date.now`|5\.2（原书第67页）|
|`onReport`|`(error) => void`|无；不得抛出异常|7\.3（原书第109页）|



## HarnessSettings



|键|默认值|作用|参见|
|---|---|---|---|
|`extensions`|所有已安装扩展，按安装顺序|对话未自行选择时使用的扩展|7\.2（原书第106页）|
|`stream`|`{}`|pi\-ai 请求选项，见下表|6\.3（原书第91页）|
|`retry.enabled`|`true`|重试失败的模型请求|6\.3（原书第91页）|
|`retry.maxRetries`|`3`|首次失败之后的重试次数|6\.3（原书第91页）|
|`retry.baseDelayMs`|`2000`|退避基数|6\.3（原书第91页）|
|`retry.maxAgentDelayMs`|`60000`|退避上限|6\.3（原书第91页）|
|`compaction.enabled`|`true`|上下文填满时自动压缩|6\.5（原书第97页）|
|`compaction.reserveTokens`|`16384`|上下文超过 `contextWindow - reserveTokens` 后，在请求前压缩|6\.5（原书第97页）|
|`compaction.keepRecentTokens`|`20000`|逐字保留的近期 token 数|6\.5（原书第97页）|
|`compaction.backgroundTokens`|`32768`|提前这么多个 token 开始后台压缩；`0` 表示禁用|6\.5（原书第97页）|
|`progress.partialIntervalMs`|`100`|两次流式文本提交之间的最小间隔|6\.2（原书第88页）|
|`progress.outputIntervalMs`|`100`|两次工具输出提交之间的最小间隔|6\.2（原书第88页）|
|`toolExecution`|`"parallel"`|或 `"sequential"`|6\.4（原书第94页）|
|`steeringMode`|`"one-at-a-time"`|或 `"all"`，按边界应用|6\.1（原书第84页）|
|`followUpMode`|`"one-at-a-time"`|或 `"all"`，按边界应用|6\.1（原书第84页）|



默认值来自 `src/harness/agent.ts` 中的 `DEFAULT_RETRY_POLICY`、`DEFAULT_COMPACTION_POLICY`、`DEFAULT_PROGRESS_POLICY` 和 `resolveSettings`。规范中的 `HarnessSettings` 列表遗漏了 `progress`；源码和 CHANGELOG 1\.0\.3 都包含它。



## stream 选项



|键|含义|
|---|---|
|`transport`|pi\-ai 传输方式|
|`timeoutMs`|请求超时|
|`maxRetries, maxRetryDelayMs`|单次尝试内部的提供商／SDK 重试，与 `retry` 不同|
|`headers, metadata`|转发的请求头和元数据|
|`cacheRetention`|pi\-ai 提示词缓存保留策略|
|`deferred`|布尔值，或 `{ window: "15m" \| "1h" \| "24h" }`|



缺失字段使用 pi\-ai 的默认值（`ConversationStreamOptions`，`src/harness/types.ts`）。



## 其他默认值



|位置|默认值|来源|参见|
|---|---|---|---|
|工具的 `replay`|`"unsafe"`|`src/harness/tool.ts`|6\.4（原书第94页）|
|工具的 `executionMode`|设置中的 `toolExecution`|`src/harness/types.ts`|6\.4（原书第94页）|
|工具的 `outputLimits`|50 KB，2000 行，`retain: "head"`|`src/harness/tool.ts, src/truncate.ts`|7\.4（原书第112页）|
|`bash` 输出|`retain: "tail"`|`src/tools/bash.ts`|7\.4（原书第112页）|
|提示词区段的 `tag`|`true`：`<key>...</key>`|`src/harness/types.ts`|7\.5（原书第115页）|
|智能体的 `thinkingLevel`|`"off"`|`src/harness/agent.ts`|7\.2（原书第106页）|
|输入的 `whenBusy`|`"followUp"`|spec §2\.2|6\.1（原书第84页）|
|监听的待处理帧|100 帧，之后由一个完整值帧替换|`src/session/observation.ts`|8\.2（原书第129页）|
|JSONL 的 `fsync`|`false`|`src/storage/jsonl/storage.ts`|9\.3（原书第148页）|
|SQLite 的 `walAutoCheckpointPages`|`1000`|`src/storage/sqlite/node.ts`|9\.2（原书第144页）|
|SQLite 的 `busyTimeoutMs`|`5000`|`src/storage/sqlite/node.ts`|9\.2（原书第144页）|



来源：`src/harness/types.ts`（`HarnessOptions, HarnessSettings, Settings, ConversationStreamOptions, ToolRegistration, PromptSection`）；`src/harness/agent.ts`；`src/harness/harness.ts:180`；`src/harness/tool.ts:88, :176`；`src/truncate.ts`；`src/tools/bash.ts`；`src/session/observation.ts:15`；`src/storage/jsonl/storage.ts`；`src/storage/sqlite/node.ts`；spec §2\.2；CHANGELOG 1\.0\.3。
