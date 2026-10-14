---
title: 会话：JSONL 树
---

<div class="section-kicker">4.3 / THE CODING AGENT</div>

# 会话：JSONL 树

---

<strong>会话文件是仅追加的，每个条目都指明其父节点，因此一个文件就能容纳整棵对话树。当前位于哪个分支只保存在内存中，重启后会选择最后写入的那一行。</strong>



<strong>智能体在会话中做过的一切，都可以从一个 JSONL 文件中恢复</strong>：它收到的提示词、模型的每次响应、每个工具结果，以及用户尝试过的每条分支。本节介绍文件的存放位置与命名方式，随后介绍文件头和十一种条目类型。接着沿着 `parentId` 构建的树，以及在树上移动的叶指针展开说明。最后讨论加载与迁移，以及一条路径上的条目如何变成发送给模型的消息。相关代码是 `SessionManager`，共2,013行，位于单个文件中，见 `CA/src/core/session-manager.ts:987`。

## 位置、命名与标识



目录：`~/.pi/agent/sessions/--<cwd>--/`。`cwd` 会移除开头的 `/` 或 `\`，并将每个 `/`、`\` 和 `:` 替换为 `-`，见 `CA/src/core/session-manager.ts:592`。`/Users/me/proj` 会变为 `--Users-me-proj--`。



目录优先顺序：`--session-dir`，然后是 `$PI_CODING_AGENT_SESSION_DIR`，再是 `sessionDir` 设置，最后是按 `cwd` 划分的默认目录，见 `CA/src/main.ts:688`。



文件名：`<将 : 和 . 替换为 - 的 ISO 时间戳>_<session id>.jsonl`，见 `CA/src/core/session-manager.ts:1079`。采集工具包中的文件为 `2026-10-05T23-16-41-747Z_01a10e5a-ea92-7225-8c3a-c148ed81dc38.jsonl`。



会话 ID：UUIDv7，见 `CA/src/core/session-manager.ts:264`，所以 ID 按创建时间排序。通过 `--session-id` 或 SDK 提供的自定义 ID 必须匹配 `^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$`，见 `CA/src/core/session-manager.ts:268`。



条目 ID：`randomUUID()` 的前8个十六进制字符，最多与现有 ID 检查100次，之后改用完整 UUID，见 `CA/src/core/session-manager.ts:277`。



<strong>文件采用延迟创建。在会话包含用户或助手消息之前，条目都留在内存中；只打开再关闭 Pi、不输入内容，不会留下文件</strong>，见 `CA/src/core/session-manager.ts:1166`。第一次刷新以 `"wx"` 标志打开文件（文件已存在就会失败），并写入所有缓冲的条目。之后，每个条目都通过一次 `appendFileSync` 追加一行，见 `CA/src/core/session-manager.ts:1172`。`sessions-tree` 采集展示了这个转变：在 `model_change` 之后，磁盘上的文件有0行；在第一条用户消息之后，有3行。

## 文件格式



第1行是文件头。之后每行都是一个条目，包含 `type`、`id`、`parentId` 和 ISO 时间戳。`CURRENT_SESSION_VERSION` 为3，见 `CA/src/core/session-manager.ts:41`。下面是单轮采集的前三行，与 Pi 写入的内容一致：



文件头，随后是真实会话的前两个条目。来源：`research/out/one-turn.txt`（§session\-jsonl，第1–3行）。

```json
{"type":"session","version":3,"id":"01a10e5a-ea92-7225-8c3a-c148ed81dc38","timestamp":"2026-10-05T23:16:41.747Z","cwd":"<tmp>/project"}
{"type":"model_change","id":"2cd13c47","parentId":null,"timestamp":"2026-10-05T23:16:41.749Z","provider":"faux","modelId":"faux-1"}
{"type":"thinking_level_change","id":"f99fc4be","parentId":"2cd13c47","timestamp":"2026-10-05T23:16:41.749Z","thinkingLevel":"off"}
```



以上为完整行，重新序列化为每条一行。文件头没有 `parentId`，也不是条目。`parentSession` 未出现，因为新会话中它是 `undefined`，而 `JSON.stringify` 会将其丢弃。

|<strong>类型</strong>|<strong>附加字段</strong>|<strong>是否进入模型上下文</strong>|
|---|---|---|
|`message`|`message`：一个 `AgentMessage`（`user`、`assistant`、`toolResult`、`system`、`bashExecution`、`custom`）|是|
|`thinking_level_change`|`thinkingLevel`|否；设置状态|
|`model_change`|`provider`、`modelId`|否；设置状态|
|`usage`|`kind`（例如 `cache_warm`）、`provider`、`model`、`usage`、`note?`|否|
|`compaction`|`summary`、`firstKeptEntryId`、`tokensBefore`、`details?`、`usage?`、`fromHook?`、`systemMessage?`|是，作为检查点加摘要|
|`branch_summary`|`fromId`、`summary`、`details?`、`usage?`、`fromHook?`|是，作为摘要|
|`custom`|`customType`、`data?`|否；扩展状态|
|`custom_message`|`customType`、`content`、`details?`、`display`|是，作为自定义消息|
|`context_edit`|`targetId`、`replacement: {content} \| null`|更改另一个条目|
|`label`|`targetId`、`label`（`undefined` 会清除它）|否；书签|
|`session_info`|`name?`|否；显示名称|



共有十一种条目类型，没有独立的提示词状态。提示词和工具集是 `message` 条目中的系统消息，详见“系统提示词构建”（原书第75页）；依次重放它们即可得到当前状态。依据 `session-manager.ts`（`SessionEntry` 联合类型，第183–194行）。

## 树与叶指针



<strong>每次追加都会将 `parentId` 设为当前叶节点，然后将叶指针移到新条目</strong>，见 `CA/src/core/session-manager.ts:1191`。<strong>没有分支的会话中，树就是一条链。单轮采集就是这样一条链，共八行：</strong>



<ManualFigure id="4.5" />

> <strong>树形图。Each line’s parentId is the line before it 每一行的 `parentId` 都指向前一行。</strong>根节点是第一个条目，而不是文件头；系统消息像其他消息一样位于树中。依据 `research/out/one-turn.txt`（§session\-jsonl）绘制；ID 来自该次运行。
> 
> 



<strong>分支操作不会复制或删除任何东西。`branch(id)` 将叶指针移到更早的条目，下一次追加便会成为原本紧随该条目之后的节点的兄弟节点</strong>，见 `CA/src/core/session-manager.ts:1579`。<strong>`sessions-tree` 采集用 `SessionManager` 构建了一个真实的分支文件，然后重新打开它：</strong>



<ManualFigure id="4.6" />

> 树形图。<strong>Labels are tree entries, and they move the leaf\. 标签是树中的条目，也会移动叶指针。</strong>`appendLabelChange(a1)` 将标签挂在当时的叶节点 `a3` 下，因此后来的 `branch_summary` 会把 `fromId=lb`（一个标签）记录为它离开的分支。最后一次没有后续追加的 `branch(u1)` 丢失了：重新打开会话后的叶节点是 `bs`。来源：`research/out/sessions-tree.txt`；这里用名称代替8位十六进制 ID。
> 
> 



<strong>叶指针从不会被写入文件。加载时，`_buildIndex()` 将它设为文件顺序中的最后一个条目</strong>，见 `CA/src/core/session-manager.ts:1103`。因此，只有在某个分支下追加了内容，这个分支位置才能在重启后保留。标签也按相同方式解析：按文件顺序，某个目标最后出现的标签条目生效；标签值为 `undefined` 时则清除它。

|<strong>操作</strong>|<strong>效果</strong>|
|---|---|
|`branch(id)`，见 `CA/src/core/session-manager.ts:1579`|移动叶指针；下次追加会创建一个兄弟节点|
|`resetLeaf()`，见 `CA/src/core/session-manager.ts:1591`|`leaf = null`；下次追加成为新的根节点（用于重新编辑第一条消息）|
|`branchWithSummary(fromId, summary)`，见 `CA/src/core/session-manager.ts:1600`|移动叶指针，并在其下追加 `branch_summary`；`fromId` 为旧叶节点或 `"root"`|
|`createBranchedSession(leafId)`，见 `CA/src/core/session-manager.ts:1632`|创建只包含根到叶路径的新文件；移除标签条目，重新连接路径，再将标签追加到末尾；`parentSession` 等于旧文件|
|`forkFrom(src, targetCwd)`，见 `CA/src/core/session-manager.ts:1815`|将另一文件的所有条目复制到另一个 `cwd` 的新文件中（`--fork`、跨项目的 `--session`）|



什么都不会被删除。每个操作要么移动内存中的叶指针，要么写入新文件。依据 `session-manager.ts`（分支操作部分）。



`getTree()` 会将父节点缺失的条目设为根节点，并按时间戳排列每个节点的子节点，见 `CA/src/core/session-manager.ts:1529`。从这种条目回溯路径时，会在缺口处停止。

## 加载与迁移



`loadEntriesFromFile()` 以 1 MiB 为单位读取，按 `\n` 拆分，并跳过空行和格式错误的行，不发出警告，见 `CA/src/core/session-manager.ts:627`。如果第一个解析出的条目不是带有字符串 `id` 的文件头，就返回 `[]`。最后一行即使没有末尾换行符也会保留，并向文件追加换行符。



空文件会用一个新文件头初始化。非空文件如果无法得到任何条目，则抛出 `Session file is not a valid pi session: path`（会话文件不是有效的 pi 会话：path），且不会被修改，见 `CA/src/core/session-manager.ts:1039`。



文件头版本低于3时会运行迁移（缺失时按1处理），之后重写整个文件，见 `CA/src/core/session-manager.ts:337`：

- v1 → v2：为每个条目分配 ID，按文件顺序线性连接 `parentId`，并将压缩条目的 `firstKeptEntryIndex` 转换为 `firstKeptEntryId`，见 `CA/src/core/session-manager.ts:287`。

- v2 → v3：消息角色 `hookMessage` 改为 `custom`，见 `CA/src/core/session-manager.ts:316`。

## 上下文重建



模型从不会看到文件本身。它看到的是文件中某条路径的投影，由 `buildSessionProjection()` 重建，见 `CA/src/core/session-manager.ts:543`。



<ManualFigure id="4.7" />

> 只有路径上最新的一次压缩会提供摘要。保留范围内更早的压缩在投影中不产生任何内容；切分点之前的原始系统消息会被丢弃，因为压缩本身携带自己的快照。依据 `session-manager.ts`（`buildSessionPath`、`getSessionContextSettings`、`buildContextEntries`、`buildSessionProjection`、`sessionEntryToContextMessages`）。
> 
> 



- 路径：从叶节点回溯到根节点，再反转，见 `CA/src/core/session-manager.ts:390`。其他分支上的兄弟节点不在这条路径上。

- 设置：`thinkingLevel` 是路径上最后一个 `thinking_level_change` 的值，默认为 `"off"`。`model` 来自最后一个 `model_change` 或助手消息，以较晚者为准，见 `CA/src/core/session-manager.ts:418`。

- 压缩：当路径上存在压缩条目 `C` 时，条目顺序为 `C`，然后是从 `C.firstKeptEntryId` 到 `C` 之间去掉原始系统消息后的条目，最后是 `C` 之后的所有内容，见 `CA/src/core/session-manager.ts:476`。“压缩与分支摘要”（原书第92页）介绍了 `C` 的生成方式。

- 上下文编辑：每个目标以最新的 `context_edit` 为准；`null` 会省略目标，有值时只替换其 `content`，见 `CA/src/core/session-manager.ts:519`。只考虑当前路径上的编辑，因此编辑仅在所在分支内生效。

- 消息：`message` 产生其 `message`；`custom_message` 产生自定义消息；`branch_summary` 产生 `branchSummary` 消息；`compaction` 先产生其 `systemMessage` 快照，再产生一条 `compactionSummary` 消息；其他类型都不产生内容，见 `CA/src/core/session-manager.ts:439`。



应用于分支采集时，重新打开的会话路径为 `mc → u1 → a1 → u2 → a2 → bs`，上下文包含五条消息：`user`、`assistant`、`user`、`assistant`、`branchSummary`。`model_change` 设置状态，不产生消息；分支 B 及其标签不在路径上。



易踩的坑：移动叶指针不会被保存。不带摘要或标签的 `/tree` 导航、SDK 中的 `branch()`，以及重新定位叶指针的扩展，在下一次追加之前都不会改变文件，见 `CA/src/core/agent-session.ts:4113`。如果 Pi 在那之前退出，会话重新打开时会定位到文件最后一行，而那一行可能属于用户刚刚离开的分支。向目标追加标签是固定位置成本最低的方式。



这对你意味着什么：

- 通过构建 `parentId` 索引解析会话，而不是按行顺序读取。

- 只有文件处于静止状态时，才将最后一行视为叶节点；运行中的 Pi 可以把叶指针放在别处。

- 用 `custom` 条目保存扩展状态，用 `custom_message` 保存模型应当看到的文本。

- 用 `context_edit` 隐藏或重写更早的消息；原始行仍留在文件中。

    

> 来源：`CA/src/core/session-manager.ts`（`SessionHeader`、`SessionEntry` 类型、`createSessionId`、`assertValidSessionId`、`generateId`、`migrateV1ToV2`、`migrateV2ToV3`、`migrateToCurrentVersion`、`buildSessionPath`、`getSessionContextSettings`、`sessionEntryToContextMessages`、`buildContextEntries`、`projectContextEntry`、`buildSessionProjection`、`getDefaultSessionDirPath`、`loadEntriesFromFile`；`SessionManager`：`_setSessionFile`、`newSession`、`_buildIndex`、`_hasConversation`、`_persist`、`_appendEntry`、`appendLabelChange`、`getTree`、`branch`、`resetLeaf`、`branchWithSummary`、`createBranchedSession`、`forkFrom`）；`CA/src/main.ts`（会话目录）；`CA/docs/session-format.md`；`research/capture/sessions-tree.mjs`；`research/out/sessions-tree.txt`；`research/out/one-turn.txt`（§session\-files、§sessionjsonl）。
> 
>
