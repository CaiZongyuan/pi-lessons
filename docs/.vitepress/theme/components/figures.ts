/** Faithful, local teaching models of the chapter's nine original figures and three supplied supplements. */
export type Tone = 'teal' | 'blue' | 'green' | 'purple' | 'rose' | 'amber' | 'gray'
export interface Step { label: string; title: string; summary: string; detail: string; tone: Tone; outcome?: string }
export interface TreeEntry { id: string; label: string; note: string; parent: string | null; depth: number; tone: Tone; prefix: string }
export interface ManualFigureData { id: string; title: string; english: string; kind: string; category: string; image: string; page?: number; caption: string; source: string; steps?: Step[]; tree?: TreeEntry[] }
const step = (label: string, title: string, summary: string, detail: string, tone: Tone = 'teal', outcome?: string): Step => ({ label, title, summary, detail, tone, outcome })
export const promptSections = [
  step('preamble', '开场说明', '无标签 · 默认文本或 SYSTEM.md', '默认开场句说明 Pi 的编码助手角色。SYSTEM.md 或 --system-prompt 会原样替换这一节，并让 tools、rules、docs 三节不再构建。', 'blue'),
  step('tools', '工具清单', '仅默认提示词', '每个已声明且有 promptSnippet 的工具占一行：name: snippet。没有任何带 promptSnippet 的声明工具时显示 (none)；prepareLoadout 隐藏的工具不会列出。', 'green'),
  step('rules', '规则', '仅默认提示词', 'buildRules() 生成去重后的规则列表，包括使用 bash 进行 ls、rg、find 等文件操作、回答简洁以及清晰展示文件路径。', 'green'),
  step('docs', '文档', '仅默认提示词', '指向 README、docs/、examples/；只在用户问及 Pi 本身时阅读。', 'green'),
  step('addendum', '附加说明', 'APPEND_SYSTEM.md', '追加提示词文本；多个来源之间用空行连接。空分节省略。', 'green'),
  step('project_context', '项目上下文', 'AGENTS.md、CLAUDE.md', '每个上下文文件放入一个带 path 属性的 project_instructions 块。空分节省略。', 'green'),
  step('skills', '技能', '仅当 read 或 bash 可用', 'available_skills 索引列出各技能的 name、description、location；需存在 read 或 bash 工具。', 'green'),
  step('cwd', '工作目录', '始终考虑', '工作目录是默认提示词中唯一的运行环境信息；反斜杠转为 /。这里不会注入日期、时间、操作系统或 shell。', 'gray'),
  step('custom…', '自定义分节', '扩展', '通过 systemPromptOptions.sections 添加；名称必须匹配 ^[a-z][a-z0-9_-]*$，且不能为 preamble。', 'purple')
]
export const figures: Record<string, ManualFigureData> = {
  '4.1': { id: '4.1', title: '系统提示词分节与顺序', english: 'System prompt sections, in order', kind: 'prompt', category: 'STRUCTURE', image: 'image 9.webp', page: 75,
    caption: '自定义提示词替换四节的默认构建方式：preamble 被替换，tools、rules、docs 不再构建。其余分节保持原有顺序，空分节省略。', source: 'system-prompt.ts · buildSystemPromptSections()', steps: promptSections },
  '4.2': { id: '4.2', title: '提示词变化如何成为补丁', english: 'A prompt change becomes a patch', kind: 'sequence', category: 'SEQUENCE', image: 'image 1.webp', page: 79,
    caption: '之前的消息不被改写。变化分节发送完整新文本，被移除分节发送 null；工具变化与分节补丁放在同一条系统消息里。', source: 'agent-session.ts · system-prompt.ts:217 · agent-loop.ts:333 · ai/utils/transcript.ts:115',
    steps: [
      step('build', 'buildSystemPromptSections(options)', '当前工具、技能、上下文文件', 'AgentSession 按当前配置重新构建有序分节。', 'amber'),
      step('replay', 'getCurrentSystemMessage(messages)', '重放已有系统消息', '依次重放 transcript；后出现的同名分节覆盖更早分节。工具变化在每条消息内先应用 toolsRemoved，再应用 toolsAdded。', 'teal'),
      step('diff', 'diffSystemPromptSections(prev, cur)', '没有变化时返回 undefined', '逐节比较完整文本。修改发送完整新文本；删除发送 null。这不是字符级差异。', 'amber'),
      step('append', 'append SystemMessage', '{ content: "", sections: patch }', '追加一条新的系统消息；原有 transcript 中每条消息保持不变。', 'teal'),
      step('tools', 'toolsAdded / toolsRemoved', 'declareToolChanges · 同一条消息', '工具声明变化随同一条系统消息发送；重放时先移除，再添加。', 'teal'),
      step('resolve', 'resolveTranscript(…)', '原位发送，或合并到开头', '仅当 supportsMidConvoSystemMessages 为 true，补丁系统消息才保留在原位；默认 false 会将系统消息合并到开头，改变缓存前缀。', 'purple')
    ] },
  '4.3': { id: '4.3', title: 'edit 的六步检查', english: 'The edit algorithm', kind: 'decision', category: 'DECISION', image: 'image 8.webp', page: 83,
    caption: '五种拒绝路径，一种写入路径。首个失败的检查决定结果；失败时不写文件。所有替换始终相对于本次调用的原始文件。', source: 'edit.ts · edit-diff.ts · file-mutation-queue.ts',
    steps: [
      step('read', '读取、移除 BOM、识别换行', '把文件及 oldText/newText 规范为 LF', '首个 CRLF 早于首个 LF 时视为 CRLF。oldText 不能为空。', 'green', 'oldText empty · “oldText must not be empty in path.”'),
      step('match', '先精确匹配每个 edit', '任一 edit 需要时，所有 edit 转入模糊匹配', '模糊规范化使用 NFKC、移除行尾空白、智能引号转 ASCII、Unicode 横线转 -、特殊空格转普通空格。', 'green', 'no match · “Could not find the exact text in path…”'),
      step('count', '检查匹配次数', '每个 edit 都在模糊空间中计数', '即使精确匹配成功，唯一性仍在模糊空间中检查。仅引号样式或行尾空白不同的两行也可能计为两次。', 'green', 'more than one · “Found N occurrences of the text in path…”'),
      step('overlap', '按偏移排序，检查重叠', '所有范围基于原始文件', '排序后检查替换范围是否重叠；错误信息中的 edits[i] / edits[j] 使用排序后的位置。', 'green', 'overlap · “edits[i] and edits[j] overlap in path…”'),
      step('apply', '逆偏移顺序应用替换', '模糊路径只重写触及的行', '其他行保留原始字节。结果与原文件相同则拒绝。', 'green', 'content unchanged · “No changes made to path…”'),
      step('write', '恢复 BOM 与换行，再写入', '返回 diff、统一补丁与 firstChangedLine', '只有所有检查通过才写入。统一补丁保留四行上下文；同一真实文件路径的修改由队列串行执行。', 'green', 'write · “Successfully replaced N block(s) in path.”')
    ] },
  '4.4': { id: '4.4', title: '一次工具调用，六个阶段', english: 'One tool call, six stages', kind: 'flow', category: 'FLOW', image: 'image 3.webp', page: 84,
    caption: '扩展可以修改已经验证的参数，或阻止调用。tool_result 处理器完成后，才会调整图片大小。', source: 'agent-loop.ts · prepareToolCall / finalizeExecutedToolCall · agent-session.ts · _beforeToolCall / _afterToolCall',
    steps: [
      step('prepare', '准备参数', 'prepareArguments · 每工具修复', '工具特有的 prepareArguments 首先修复或准备参数。', 'green'),
      step('validate', '验证参数', 'TypeBox schema · 错误 → isError', 'TypeBox 验证在扩展的 tool_call 事件之前运行。验证失败会成为错误工具结果。', 'green'),
      step('before', '调用前钩子', 'beforeToolCall → tool_call', '扩展接收 execute 将接收的同一参数对象；修改 event.input 会改变调用，block 则产生带原因的错误结果。', 'purple'),
      step('execute', '执行工具', 'execute(id, params, signal, onUpdate, ctx)', '通过验证且未被阻止后执行工具；执行错误也会转为 isError: true 的工具结果。', 'green'),
      step('after', '调用后钩子', 'afterToolCall → tool_result → 图片缩放', '扩展可以替换 content、details、isError。图片大小在此钩子之后调整。', 'purple'),
      step('result', '持久化结果', 'toolResult message', '最终工具结果消息被保存到 transcript。', 'blue')
    ] },
  '4.5': { id: '4.5', title: '单轮会话也是一棵树', english: 'The one-turn session as a tree', kind: 'tree', category: 'TREE', image: 'image 11.webp', page: 88,
    caption: '文件头不是树条目。首个 model_change 才是根；系统消息与其他消息一样位于树中。每条 parentId 指向前一条。', source: 'research/out/one-turn.txt · §session-jsonl',
    tree: [
      { id: 'header', label: 'header · session 01a10e5a… · version 3', note: '第 1 行 · 文件头，不是树条目', parent: null, depth: 0, tone: 'teal', prefix: '' },
      { id: '2cd13c47', label: '2cd13c47 · model_change · faux/faux-1', note: '第 2 行 · parentId: null · 根', parent: null, depth: 0, tone: 'teal', prefix: '' },
      { id: 'f99fc4be', label: 'f99fc4be · thinking_level_change · off', note: '第 3 行', parent: '2cd13c47', depth: 1, tone: 'teal', prefix: '└─' },
      { id: 'ff9b46f6', label: 'ff9b46f6 · message · system', note: '第 4 行 · 五个分节、四个工具', parent: 'f99fc4be', depth: 2, tone: 'blue', prefix: '└─' },
      { id: 'dd741bf1', label: 'dd741bf1 · message · user', note: '第 5 行 · What does hello.txt say?', parent: 'ff9b46f6', depth: 3, tone: 'blue', prefix: '└─' },
      { id: '0f939fd7', label: '0f939fd7 · message · assistant', note: '第 6 行 · toolCall read, call_1', parent: 'dd741bf1', depth: 4, tone: 'blue', prefix: '└─' },
      { id: '81cb0f01', label: '81cb0f01 · message · toolResult', note: '第 7 行 · Hello from the capture kit.', parent: '0f939fd7', depth: 5, tone: 'green', prefix: '└─' },
      { id: '01f5647e', label: '01f5647e · message · assistant', note: '第 8 行 · 重新打开时的叶节点', parent: '81cb0f01', depth: 6, tone: 'rose', prefix: '└─' }
    ] },
  '4.6': { id: '4.6', title: '重新打开一个分支会话', english: 'A branched session, reopened', kind: 'tree', category: 'TREE', image: 'image 5.webp', page: 88,
    caption: '标签也是条目，追加标签会移动叶指针。lb 是 a3 的子节点，却指向 a1；bs 是 a2 的子节点，fromId 则记录离开的 lb。', source: 'research/out/sessions-tree.txt · session-manager.ts · branch() / _buildIndex()',
    tree: [
      { id: 'mc', label: 'mc · model_change', note: '第 2 行 · 根', parent: null, depth: 0, tone: 'teal', prefix: '' },
      { id: 'u1', label: 'u1 · user', note: '第 3 行', parent: 'mc', depth: 1, tone: 'blue', prefix: '└─' },
      { id: 'a1', label: 'a1 · assistant', note: '第 4 行 · 标签 “plan” 指向这里', parent: 'u1', depth: 2, tone: 'blue', prefix: '└─' },
      { id: 'u2', label: 'u2 · user', note: '第 5 行 · 分支 A', parent: 'a1', depth: 3, tone: 'blue', prefix: '├─' },
      { id: 'a2', label: 'a2 · assistant', note: '第 6 行', parent: 'u2', depth: 4, tone: 'blue', prefix: '└─' },
      { id: 'bs', label: 'bs · branch_summary · fromId=lb', note: '第 10 行 · 重新打开后的叶节点', parent: 'a2', depth: 5, tone: 'rose', prefix: '└─' },
      { id: 'u3', label: 'u3 · user', note: '第 7 行 · branch(a1) 后的分支 B', parent: 'a1', depth: 3, tone: 'blue', prefix: '└─' },
      { id: 'a3', label: 'a3 · assistant', note: '第 8 行', parent: 'u3', depth: 4, tone: 'blue', prefix: '└─' },
      { id: 'lb', label: 'lb · label · targetId=a1', note: '第 9 行 · 父节点是 a3，而非 a1', parent: 'a3', depth: 5, tone: 'gray', prefix: '└─' }
    ] },
  '4.7': { id: '4.7', title: '从树条目到模型上下文', english: 'From entries to model context', kind: 'flow', category: 'FLOW', image: 'image 4.webp', page: 90,
    caption: '只有当前路径上最新一次压缩贡献摘要。被保留范围内更早的压缩不产生消息；压缩快照替代切分前的原始系统消息。', source: 'session-manager.ts · buildSessionPath / buildContextEntries / buildSessionProjection',
    steps: [
      step('path', '选择路径', 'leaf → root · parentId · 反转', '沿 parentId 从叶节点回溯到根，再反转。其他分支的兄弟节点不属于这条路径。'),
      step('settings', '重建设置', '最新 thinking_level_change 与 model', 'thinkingLevel 取路径上最新变化，默认 off；model 取最新 model_change 或 assistant 消息。'),
      step('compaction', '应用压缩', '[C] + kept + after C', '最新压缩 C 在前，其后是 firstKeptEntryId 到 C 之前的保留条目（去掉原始系统消息），再加 C 之后的条目。'),
      step('edits', '应用上下文编辑', '每个 target 最新的 context_edit', 'null 省略目标；非 null 仅替换内容。只应用当前路径中的编辑，因此是分支局部的。', 'rose'),
      step('messages', '转换为消息', 'sessionEntryToContextMessages', 'message、custom_message、branch_summary 产生对应消息；compaction 产生 systemMessage 快照和 compactionSummary。其他类型不产生消息。', 'blue'),
      step('context', '形成上下文', 'messages · thinkingLevel · model', 'buildSessionProjection 返回 SessionContext。模型接收路径的投影，从不直接读取 JSONL 文件本身。', 'blue')
    ] },
  '4.8': { id: '4.8', title: '压缩切分点落在哪里', english: 'Where the cut lands', kind: 'cut', category: 'STRUCTURE', image: 'image.webp', page: 93,
    caption: '切分点绝不落在 toolResult 上。示例在轮次中途的一条 assistant 消息前切分，所以轮次开头会成为单独的 turnPrefixMessages。', source: 'compaction.ts · isCutPointMessage / isTurnStartMessage / findProjectedCutPoint / prepareCompaction' },
  '4.9': { id: '4.9', title: '一次压缩的完整流程', english: 'One compaction', kind: 'flow', category: 'FLOW', image: 'image 7.webp', page: 94,
    caption: '最多调用模型两次，每次都是单次请求。默认 reserve 为 16,384 时，历史摘要上限 13,107，轮次前缀摘要上限 8,192；各自还受模型 maxTokens 限制。', source: 'compaction.ts · compact / generateSummaryWithUsage / generateTurnPrefixSummary',
    steps: [
      step('prepare', '准备压缩', 'prepareCompaction · cut / messages / fileOps', '在投影路径上选择切分点，准备需要总结的消息、上一份摘要与文件操作记录。'),
      step('hook', '压缩前钩子', 'session_before_compact', '处理器可以取消压缩，或提供自己的结果（fromHook）。', 'purple'),
      step('history', '历史摘要', '≤ 0.8 × reserve · 默认 13,107', '生成或更新历史摘要；这是一次独立、单次的模型请求。输出上限还受模型 maxTokens 约束。', 'rose'),
      step('prefix', '轮次前缀摘要', '仅拆分轮次 · ≤ 0.5 × reserve · 默认 8,192', '只有拆分轮次才额外生成前缀摘要；输出上限同样受 maxTokens 约束。', 'rose'),
      step('append', '追加压缩条目', '文件清单 + appendCompaction + 快照', '追加摘要、firstKeptEntryId 与完整 systemMessage 快照；原始 JSONL 文件的旧行不被改写。'),
      step('notify', '通知完成', 'session_compact · compaction_end', '压缩结束后发出通知事件。', 'purple')
    ] },
  'prompt-cards': { id: 'prompt-cards', title: '九种提示词分节速览', english: 'Named sections, ordered map', kind: 'cards', category: 'EXPLAINER', image: 'image 6.webp',
    caption: '系统提示词是具名分节的有序映射，而非一段字符串。preamble 无标签，其余分节包裹为 <name>…</name>；空分节省略。', source: '用户提供的中文补充图 · 对应 buildSystemPromptSections()', steps: promptSections },
  'patch-example': { id: 'patch-example', title: '123456 → 1234567：补丁里究竟是什么', english: 'A complete section, not a character diff', kind: 'patch', category: 'EXPLAINER', image: 'image 10.webp',
    caption: '补丁携带分节的完整新文本 “1234567”，并非新增字符 “7”。之前的消息逐字节保持不变。', source: '用户提供的中文补充图 · diffSystemPromptSections() / getCurrentSystemMessage() / collapseSystemMessages()' },
  'compaction-explainer': { id: 'compaction-explainer', title: '压缩前、切分、压缩后', english: 'A conversation through compaction', kind: 'explainer', category: 'EXPLAINER', image: 'image 2.webp',
    caption: '用“实现排序函数 → 加测试 → 部署”的示例观察投影变化。消息内容为教学示例，不是实时会话。', source: '用户提供的中文补充图 · compaction.ts / session-manager.ts',
    steps: [
      step('before', '压缩前', 'buildSessionProjection', '模型上下文包含上一份摘要，以及最近尚未总结的对话。'),
      step('cut', '选择切分点', 'findProjectedCutPoint', '从最新条目倒数估算 token，再对齐最近有效切分点。本例切在 assistant “测试通过了”，拆分了“再加个测试吧”这一轮。', 'amber'),
      step('compact', '生成摘要', 'compact', '更新历史摘要，并单独总结被拆轮次的前缀。写入压缩条目与当时的完整提示词快照；原始 JSONL 旧行不改。', 'rose'),
      step('after', '压缩后的投影', 'buildSessionProjection', '新上下文依次包含压缩条目的系统快照、新摘要，以及从 firstKeptEntryId 起逐字保留的最新消息。', 'green')
    ] }
}
export const cutEntries = [
  { role: 'C', label: 'previous summary', tone: 'gray' },
  { role: 'u', label: 'user', tone: 'blue' }, { role: 'a', label: 'assistant', tone: 'blue' }, { role: 't', label: 'toolResult', tone: 'green' },
  { role: 'a', label: 'assistant', tone: 'blue' }, { role: 't', label: 'toolResult', tone: 'green' },
  { role: 'u', label: 'user', tone: 'blue' }, { role: 'a', label: 'assistant', tone: 'blue' }, { role: 't', label: 'toolResult', tone: 'green' },
  { role: 'a', label: 'assistant', tone: 'blue' }, { role: 't', label: 'toolResult', tone: 'green' },
  { role: 'u', label: 'user', tone: 'blue' }, { role: 'a', label: 'assistant', tone: 'blue' }, { role: 't', label: 'toolResult', tone: 'green' },
  { role: 'a', label: 'assistant', tone: 'blue' }
]
