---
title: "错误与原因"
---

<div class="section-kicker">PI DURABLE / R.4 · P. 183</div>

# 错误与原因



抛出的错误，以及工作异常结束时 Harness 存储的字符串：提交请求原因、任务结局、阻塞原因、诊断和监听结束原因。



出问题时，你会通过两种方式之一看到它。错误类会被抛出，由你的代码捕获。原因则是存储在记录上的字符串，因此能够保留到重启之后，供你稍后查询。



## 错误类



|类|何时抛出|恢复方法|参见|
|---|---|---|---|
|`ReadAfterWrite`|`Tx` 在第一次写表后又读表|先读；修正代码|2\.2（原书第29页）|
|`StorageRejected`|存储在产生任何持久化副作用之前拒绝一个批次|提交回滚；Session 继续运行|2\.3（原书第33页）|
|`ConversationBusy`|对繁忙对话使用 `whenBusy: "reject"`；携带 `conversationId`|没有写入任何内容|6\.1（原书第84页）|
|`JsonlCorruptionError`|打开时发现已提交数据缺失或损坏|从备份恢复|9\.3（原书第148页）|
|`JsonlStoragePoisonedError`|写入失败，且是否落地不确定；“must be reopened”|重新打开|9\.3（原书第148页）|
|`FileError`|环境中的文件操作；带有 `not_found` 等代码|根据代码处理|9\.5（原书第155页）|
|`ExecutionError`|环境中的 `exec`；带有 `timeout`、`aborted` 等代码|根据代码处理|9\.5（原书第155页）|
|普通 `Error`|“Session is poisoned by a failed commit after storage admission; reopen it”|重新打开|2\.3（原书第33页）|
|普通 `Error`|“Session is closed”|使用新的 Harness|2\.3（原书第33页）|



前三种从包根路径导出，JSONL 错误从 `…/storage/jsonl` 导出，环境错误从 `…/env` 导出。



## 提交请求未获回答的原因



|原因|何时设置|参见|
|---|---|---|
|`aborted`|撤回排队条目，或运行所属的任务中止|6\.1（原书第84页）|
|`stale`|头指针写入所指向的条目早于活动范围|6\.1（原书第84页）|
|`reset`|在 `postTools` 放入的重置使运行在回答之前结束|3\.4（原书第46页）|
|`no_model`|智能体没有模型，或模型无法解析|6\.3（原书第91页）|
|`model_error`|提供商在重试后仍失败；`detail` 是它的错误文本|6\.3（原书第91页）|
|`faulted`|运行任务发生故障；`detail` 是错误消息|5\.6（原书第80页）|
|`missing_task, task_too_old, migration_failed`|阻塞的运行任务被中止，并成为孤儿任务|5\.4（原书第73页）|



## 任务结局与阻塞原因



|值|字段|含义|参见|
|---|---|---|---|
|`completed`|`outcome` 的 `status`|由任务连同结果一起提交|5\.1（原书第63页）|
|`failed`|`outcome` 的 `status`|由任务提交的预期失败，带有错误|5\.1（原书第63页）|
|`aborted`|`outcome` 的 `status`|任务的中止处理器运行，并选择了这一结局|5\.6（原书第80页）|
|`orphaned`|`outcome` 的 `status`|在没有代码可以运行该任务时中止；`reason` 说明原因|5\.6（原书第80页）|
|`faulted`|`outcome` 的 `status`|任务违反了规则：抛出异常、没有推进，或者其提交被拒绝|5\.2（原书第67页）|
|`missing_task`|检查结果的 `blocked.reason`|没有与任务种类对应的已注册定义|5\.4（原书第73页）|
|`task_too_old`|检查结果的 `blocked.reason`|已注册的版本比记录的版本旧|5\.4（原书第73页）|
|`migration_failed`|检查结果的 `blocked.reason`|`migrate` 抛出异常或不存在|5\.4（原书第73页）|
|`model_error, no_model`|`failed` 的 `error.detail.reason`|生成或压缩无法取得回答|6\.3（原书第91页）|



阻塞原因在检查时推导出来，从不存储，直到中止操作把它变成 `orphaned` 原因。



## 工具诊断与监听结束



|代码或原因|位置|含义|参见|
|---|---|---|---|
|`tool_unavailable`|诊断|工具未被提供，或已无法解析|6\.4（原书第94页）|
|`invalid_arguments`|诊断|参数未通过 TypeBox 验证|7\.4（原书第112页）|
|`blocked`|诊断|`beforeTool` 钩子阻止了调用|7\.3（原书第109页）|
|`interrupted`|诊断|不安全的工具被崩溃或关闭打断|6\.4（原书第94页）|
|`truncated, full_output`|诊断|输出被截断；完整输出溢出到文件|7\.4（原书第112页）|
|`stopped, cancelled`|`WatchEnd.reason`|调用了 `stop()`；所观察的取消信号已中止|8\.1（原书第125页）|
|`session_closed, retired`|`WatchEnd.reason`|Session 已关闭；文档已退役|8\.1（原书第125页）|
|`listener_error`|`WatchEnd.reason`|监听器抛出异常；携带 `error`|8\.1（原书第125页）|



来源：`src/errors.ts`；`src/storage/jsonl/storage.ts:81–94`；`src/env/index.ts:35–75`；`src/session/session.ts:539–546`；`src/session/observation.ts`；`src/harness/submissions.ts`；`src/harness/inbox.ts`；`src/harness/generation.ts`；`src/harness/live.ts:171`；`src/harness/scheduler.ts:769–813`；`src/harness/tool.ts`；`src/tools/read.ts`；`src/tools/bash.ts`；`src/types.ts`（`TaskOutcome, WatchEnd`）；spec §5\.4、§6、§8\.3；`research/capture/crash-after.txt`；`research/capture/inbox-steps.txt`。
