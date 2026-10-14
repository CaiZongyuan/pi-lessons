---
title: 压缩与分支摘要
---

<div class="section-kicker">4.4 / THE CODING AGENT</div>

# 压缩与分支摘要

---

<strong>当上下文窗口填满时，Pi 会让模型为旧消息编写结构化检查点，并将它作为一个条目追加。文件保留每一行原始内容；只有模型看到的投影会变短。</strong>



<strong>长时间的编码会话终究会超出任何上下文窗口。Pi 的办法是压缩：总结当前路径中最旧的部分，逐字保留最新部分，并将结果记录为会话树中的 `compaction` 条目</strong>，详见“会话：JSONL 树”（原书第86页）。本节介绍压缩何时触发、如何从溢出中恢复、切分点如何选取，以及摘要如何生成、使用什么提示词。最后介绍模型之后看到的内容，以及用户离开分支时 `/tree` 写入的分支摘要。

## 何时触发



默认值和阈值检查。来源：`CA/src/core/compaction/compaction.ts`。

```text
export const DEFAULT_COMPACTION_SETTINGS: CompactionSettings = {
    enabled: true,
    reserveTokens: 16384,
    keepRecentTokens: 20000,
};
...
export function shouldCompact(contextTokens: number, contextWindow: number, settings: CompactionSettings):
boolean {
    if (!settings.enabled) return false;
    return contextTokens > contextWindow - settings.reserveTokens;
}
```

> 第126–130行及267–270行；删节部分省去了中间的 token 估算函数。
> 
> 



采用默认值时，200,000 token 的窗口会在超过183,616 token 时压缩。`reserveTokens` 和 `keepRecentTokens` 可以在 `compaction.modelOverrides["provider/modelId"]` 下按模型覆盖，键必须精确匹配且区分大小写；`enabled` 仍然是全局设置，见 `CA/src/core/settings-manager.ts:940`。这三个键都列在“设置参考”（原书第202页）中。



上下文大小先测量，再估算。基础值取最后一条有效助手消息的 `usage.totalTokens`，或者其各部分之和；中止、出错以及用量全为零的响应不计入，见 `CA/src/core/compaction/compaction.ts:148`。之后的消息按字符数 ÷ 4 估算，每张图片按4,800个字符计，见 `CA/src/core/compaction/compaction.ts:276`。如果用量是在分支上最新的 `context_edit` 或压缩之前采集的，则不予采信，改为估算整个投影，见 `CA/src/core/compaction/compaction.ts:227`。



|<strong>触发点</strong>|<strong>位置</strong>|<strong>原因</strong>|
|---|---|---|
|每个后续轮次之前<br>|`prepareNextTurnWithContext → _compactBeforeNextAssistantResponse`，见 `CA/src/core/agent-session.ts:764`|阈值|
|虚拟模型的每次请求|`prepareRequest`，对照路由后模型的窗口检查，见 `CA/src/core/agent-session.ts:826`|阈值|
|一次运行之后|`_handlePostAgentRun → _checkCompaction`，见 `CA/src/core/agent-session.ts:1870`|阈值或溢出|
|一次提示之前|`prompt() → _checkCompaction`，也包括中止的响应，见 `CA/src/core/agent-session.ts:2042`|阈值|
|手动|`/compact [instructions] → compact()`；先中止当前运行，且绝不重试该运行，见 `CA/src/core/agent-session.ts:2750`|手动|



五个入口，一个生成器。手动和自动压缩最终都会进入 `_runDefaultCompaction()` 及 `compaction/` 中的 `compact()` 函数，除非 `session_before_compact` 处理器取消操作或提供了结果。依据 `agent-session.ts`。



溢出在一次运行之后处理，见 `CA/src/core/agent-session.ts:2933`。上下文溢出错误，或者在未达到模型自身输出限制时发生的 `length` 停止，都会启动恢复。Pi 通过 `replacement` 为 `null` 的 `context_edit` 条目隐藏失败的响应及其工具结果，见 `CA/src/core/agent-session.ts:1224`，然后压缩，并重试该轮次一次。第二次失败会以如下消息结束：`Context overflow recovery failed after one compact-and-retry attempt. Try reducing context or switching to a larger-context model.`（经过一次压缩并重试后，上下文溢出恢复失败。请尝试减少上下文，或切换到上下文窗口更大的模型。）如果是 `length` 停止，则消息为 `Truncated response recovery failed after one compact-and-retry attempt.`（经过一次压缩并重试后，截断响应恢复失败。）由不同于当前模型的模型报告的溢出会被忽略，早于最新压缩的任何助手消息也会被忽略。如果响应以 `stop` 完成，但仍然超过窗口，Pi 会执行压缩而不重试。

## 选择切分点



<strong>`prepareCompaction()` 处理的是投影路径，而不是原始行</strong>，见 `CA/src/core/compaction/compaction.ts:872`。<strong>它从最新一次提供摘要的压缩之后开始，因此该次压缩所保留的条目，会与它的摘要一起再次被总结。随后，`findProjectedCutPoint()` 从最新条目开始向后遍历，累加估算 token，直到总量达到 `keepRecentTokens`，然后对齐到该条目或其后最近的有效切分点</strong>，见 `CA/src/core/compaction/compaction.ts:802`。



<ManualFigure id="4.8" />

> 切分点绝不会落在工具结果上。<strong>有效切分点是会产生 `user`、`assistant`、`bashExecution`、`custom`、`branchSummary` 或 `compactionSummary` 消息的条目</strong>，因此调用及其结果会留在同一侧。此处切分点落在轮次中途的一条助手消息上，所以该轮次的开头会单独总结。本图为示意图，依据 `compaction.ts`（`isCutPointMessage`、`isTurnStartMessage`、`findProjectedCutPoint`、`prepareCompaction`）绘制。
> 
> 



对齐后，切分点会继续向前回退，越过相邻且不产生消息的条目，例如 `model_change`，让它们留在保留部分。如果切分条目不是轮次的起点，这次切分就是拆分轮次：<strong>从轮次起点到切分点之前的消息会成为 `turnPrefixMessages`</strong>，见 `CA/src/core/compaction/compaction.ts:903`。<strong>轮次从 `user`、`bashExecution`、`custom`、`branchSummary` 或 `compactionSummary` 消息开始。</strong>



<ManualFigure id="compaction-explainer" />



如果路径本来就以压缩条目结束，或者没有任何内容需要总结，`prepareCompaction()` 返回 `undefined`；手动压缩会分别报告 `Already compacted`（已压缩）和 `Nothing to compact (session too small)`（没有可压缩的内容，会话太小），见 `CA/src/core/agent-session.ts:2771`。否则，它返回一个 `CompactionPreparation`，供 `session_before_compact` 处理器接收：

- `firstKeptEntryId`：第一条逐字保留的条目的 ID。

- `messagesToSummarize`：从前一次边界到切分点的消息；若为拆分轮次，则到轮次起点为止；系统消息已移除。

- `turnPrefixMessages`：被拆分轮次中切分点之前的消息；其他情况下为空。

- `previousSummary`：即将被替换的压缩摘要，用于选择更新提示词。

- `fileOps`：读取、写入和编辑过的文件，取自 `read`、`write`、`edit` 工具调用、工具结果中记录的嵌套调用，以及前一次压缩的 `details`（如果该压缩由 Pi 生成），见 `CA/src/core/compaction/compaction.ts:60`。

- `tokensBefore`：压缩前对投影上下文的估算值。

## 生成摘要



<ManualFigure id="4.9" />

> <strong>最多调用模型两次，每次都是单次请求。默认预留16,384 token 时，历史摘要最多可使用13,107个输出 token，轮次前缀摘要最多可使用8,192个输出 token，并且两者各自都受模型的 `maxTokens` 上限约束。</strong>依据 `compaction.ts`（`compact`、`generateSummaryWithUsage`、`generateTurnPrefixSummary`）和 `agentsession.ts`（`compact`、`_runAutoCompaction`）。
> 
> 



<strong>摘要请求有自己的系统提示词 `SUMMARIZATION_SYSTEM_PROMPT`：“你是一个上下文总结助手。……不要继续对话。不要回答对话中的任何问题。只输出结构化摘要。</strong>”见 `CA/src/core/compaction/utils.ts:161`。对话会被序列化为文本，因此模型是在阅读它，而不是继续它，见 `CA/src/core/compaction/utils.ts:114`：



摘要请求中的用户消息。来源：`CA/src/core/compaction/compaction.ts`（`generateSummaryWithUsage`、`SUMMARIZATION_PROMPT`）。



```text
<conversation>
[User]: ...
[Assistant thinking]: ...
[Assistant]: ...
[Assistant tool calls]: read(path="src/args.ts"); edit(path=..., edits=[...])
[Tool result]: ...first 2,000 characters...

[... N more characters truncated]
</conversation>

<previous-summary>
...
</previous-summary>

The messages above are a conversation to summarize. Create a structured context checkpoint summary that another LLM will use to continue the work.

Use this EXACT format:
## Goal
## Constraints & Preferences
## Progress
### Done
### In Progress
### Blocked
## Key Decisions
## Next Steps
## Critical Context

Keep each section concise. Preserve exact file paths, function names, and error messages.

Additional focus: <custom instructions>
```



<strong>根据代码组装；工具调用参数为示例，各标题下方括号内的提示已省略。仅在存在先前摘要时才出现 `<previous-summary>`，此时 `UPDATE_SUMMARIZATION_PROMPT` 会将指令替换为保留条目、添加条目，以及将条目从 `In Progress`（进行中）移到 `Done`（已完成）的规则。只有 `/compact` 附带指令时才会出现 `Additional focus:`（额外关注点：）。</strong>



对于拆分轮次，会在 `Original Request`（原始请求）、`Progress So Far`（目前进展）和 `Context Needed to Continue`（继续工作所需的上下文）这几个标题下，单独总结轮次前缀。两段文本按 `history\n\n---\n\n**Turn Context (split turn):**\n\nprefix` 拼接；如果没有更早的历史，第一部分为 `No prior history.`（没有先前历史），见 `CA/src/core/compaction/compaction.ts:1032`。然后以 `<read-files>` 和 `<modified-files>` 块的形式追加排序后的文件列表；一个文件若既被读取又被修改，则只列为已修改，见 `CA/src/core/compaction/utils.ts:67`。



每个摘要请求都采用 `cacheRetention: "none"` 和新生成的 UUIDv7 `sessionId`，并经过会话的重试策略，见 `CA/src/core/compaction/compaction.ts:619`。只有模型支持推理，且为该请求解析出的思考级别不是 `off` 时，才会请求推理，见 `CA/src/core/compaction/compaction.ts:606`。响应如果以 `error` 或 `length` 停止，或包含工具调用，都会使压缩失败：`length` 停止意味着摘要不完整，绝不会存储，见 `CA/src/core/compaction/compaction.ts:585`。

## 之后模型会看到什么



`appendCompaction()` 存储 `summary`、`firstKeptEntryId`、`tokensBefore`、`details` 和 `usage`，以及 `systemMessage`：该时刻完整重放后的提示词和工具集，见 `CA/src/core/session-manager.ts:1261`。路径的下一次投影为：



```text
[ compaction.systemMessage ] ← 一条系统消息：所有分节、所有工具
[ user: "The conversation history before this point was compacted into the following summary:
<summary>
...
</summary>" ]
[ 从 firstKeptEntryId 到压缩条目之前的条目，移除原始系统消息 ]
[ 压缩之后追加的条目 ]
```



摘要以用户消息的形式送达提供商，由 `convertToLlm()` 根据 `COMPACTION_SUMMARY_PREFIX` 和 `COMPACTION_SUMMARY_SUFFIX` 构建，见 `CA/src/core/messages.ts:11`。原始条目仍留在 JSONL 文件中；压缩只改变 `buildSessionProjection()` 的返回内容。将叶指针移到不包含这次压缩的分支，就能恢复完整历史。



快照替换此前所有系统消息，因此摘要跟在一个完整的提示词之后，而不是一串补丁之后。这既重置了提示词历史，也重置了对话。也就是说，压缩后的第一次请求具有新的前缀，提供商缓存会从头开始。

## 分支摘要



当用户通过 `/tree` 跳转到另一个节点时（“斜杠命令与快捷键”，原书第197页），Pi 可以总结正在离开的分支。`navigateTree()` 分五步完成此事，见 `CA/src/core/agent-session.ts:3949`：

1. `collectEntriesForBranchSummary(oldLeaf, target)` 收集从旧叶节点回溯至它与目标最深共同祖先的条目，见 `CA/src/core/compaction/branch-summarization.ts:108`。

2. `session_before_tree` 处理器可以取消操作、提供摘要、替换或扩展指令，或者设置标签。

3. `generateBranchSummary()` 在 `contextWindow − branchSummary.reserveTokens` 的预算内，按从新到旧的顺序保留条目（默认预留16,384；窗口为0时按128,000计），跳过工具结果，并在预算使用量低于90%时尽量放入更早的一次压缩或分支摘要，见 `CA/src/core/compaction/branch-summarization.ts:195`。提示词采用压缩摘要的标题，但去掉 `Critical Context`（关键上下文）；`maxTokens` 为 `min(4096, model.maxTokens)`。

4. 结果前面加上 `The user explored a different conversation branch before returning here.\nSummary of that exploration:\n\n`（用户在回到这里之前探索了另一条对话分支。以下为该次探索的摘要：），后面加上文件列表，见 `CA/src/core/compaction/branch-summarization.ts:253`。

5. 如果目标是用户消息或自定义消息，新叶节点就是目标的父节点，目标文本会放回编辑器。否则，叶节点就是目标。随后 `branchWithSummary()` 将摘要追加为新叶节点的子节点，而不是旧分支的子节点。

    

在上下文中，该条目会变成一条用户消息，外面包裹 `The following is a summary of a branch that this conversation came back from:`（以下是本次对话返回前所在分支的摘要：）和 `<summary>` 标签，见 `CA/src/core/messages.ts:19`。设置 `branchSummary.skipPrompt` 会跳过交互提问，并默认不生成摘要。



> <strong>经验法则</strong>
> 
> 如果只是想让摘要聚焦某件事，向 `/compact` 传入指令即可。如果需要完全不同的摘要，就通过 `session_before_compact` 返回一个；它会以 `fromHook: true` 存储，其 `details` 不会作为文件列表读回。如果某个模型的窗口远大于其他模型，请为它设置一条 `modelOverrides`，而不是修改全局 `reserveTokens`。
> 
> 



> 来源：`CA/src/core/compaction/compaction.ts`（`DEFAULT_COMPACTION_SETTINGS`、`calculateContextTokens`、`getAssistantUsage`、`estimateContextTokens`、`estimateProjectedContextTokens`、`shouldCompact`、`estimateTokens`、`isCutPointMessage`、`isTurnStartMessage`、`findProjectedCutPoint`、`prepareCompaction`、`SUMMARIZATION_PROMPT`、`UPDATE_SUMMARIZATION_PROMPT`、`TURN_PREFIX_SUMMARIZATION_PROMPT`、`getSummarizationFailure`、`completeSummarization`、`generateSummaryWithUsage`、`compact`）；`CA/src/core/compaction/utils.ts`（`extractFileOpsFromMessage`、`computeFileLists`、`formatFileOperations`、`serializeConversation`、`SUMMARIZATION_SYSTEM_PROMPT`）；`CA/src/core/compaction/branch-summarization.ts`（`collectEntriesForBranchSummary`、`prepareBranchEntries`、`generateBranchSummary`）；`CA/src/core/agent-session.ts`（`_compactBeforeNextAssistantResponse`、`_installAgentRequestProjection`、`_handlePostAgentRun`、`prompt`、`compact`、`_checkCompaction`、`_runAutoCompaction`、`_omitRecoveryAttempt`、`navigateTree`）；`CA/src/core/session-manager.ts`（`appendCompaction`、`buildContextEntries`）；`CA/src/core/messages.ts`（`COMPACTION_SUMMARY_PREFIX`、`BRANCH_SUMMARY_PREFIX`、`convertToLlm`）；`CA/src/core/settings-manager.ts`（`getCompactionSettings`、`getBranchSummarySettings`）；`CA/docs/compaction.md`。
> 
>
