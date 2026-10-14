<script setup lang="ts">
import { computed, ref, watch, useId } from 'vue'
import { withBase } from 'vitepress'
import { figures, promptSections, cutEntries } from './figures'

const props = defineProps<{ id: string }>()
const uid = `manual-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
const figure = computed(() => figures[props.id])
const selected = ref(0)
const customPrompt = ref(false)
const skillTools = ref(true)
const leaf = ref('bs')
const selectedEntry = ref('bs')
const branchMode = ref('reopen')
const requestedCut = ref(9)
const patchAction = ref('replace')
const supportsMidConvo = ref(false)
const currentStep = computed(() => figure.value?.steps?.[selected.value])
const imageUrl = computed(() => withBase(`/figures/${encodeURIComponent(figure.value?.image || '')}`))
const nodes = computed(() => figure.value?.tree || [])
const treeEntry = computed(() => nodes.value.find(n => n.id === selectedEntry.value))
const activePath = computed(() => {
  const path = new Set<string>()
  let id: string | null = props.id === '4.5' ? '01f5647e' : leaf.value
  while (id) { path.add(id); id = nodes.value.find(n => n.id === id)?.parent || null }
  return path
})
const effectiveCut = computed(() => {
  let i = Number(requestedCut.value)
  while (i < cutEntries.length - 1 && cutEntries[i].role === 't') i++
  return i
})
const turnStart = computed(() => {
  let i = effectiveCut.value
  while (i > 0 && cutEntries[i].role !== 'u') i--
  return i
})
const splitTurn = computed(() => cutEntries[effectiveCut.value].role !== 'u')
const visibleSections = computed(() => promptSections.filter((_, i) => !(customPrompt.value && i > 0 && i < 4) && !(i === 6 && !skillTools.value)))
const routes = [{ start: 1, span: 1 }, { start: 1, span: 3 }, { start: 1, span: 1 }, { start: 1, span: 3 }, { start: 2, span: 2 }, { start: 3, span: 2 }]
const conversation = [
  ['用户', '实现一个排序函数'], ['助手', '好的 + 调用编辑工具'], ['工具结果', '编辑执行成功'], ['助手', '排序函数写好了'],
  ['用户', '再加个测试吧'], ['助手', '好的 + 调用 bash'], ['工具结果', 'bash 测试输出'], ['助手', '测试通过了'],
  ['用户', '部署一下'], ['助手', '好的 + 调用 bash'], ['工具结果', 'bash 部署输出'], ['助手', '部署完成']
]
watch(() => props.id, () => {
  selected.value = 0; customPrompt.value = false; skillTools.value = true; leaf.value = 'bs'; selectedEntry.value = props.id === '4.5' ? '2cd13c47' : 'bs'; branchMode.value = 'reopen'; requestedCut.value = 9; patchAction.value = 'replace'; supportsMidConvo.value = false
}, { immediate: true })
function stepKey(event: KeyboardEvent, index: number) {
  const count = figure.value.steps?.length || 0
  let next = index
  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = Math.min(count - 1, index + 1)
  else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = Math.max(0, index - 1)
  else if (event.key === 'Home') next = 0
  else if (event.key === 'End') next = count - 1
  else return
  event.preventDefault(); selected.value = next
  const group = (event.currentTarget as HTMLElement).closest('[data-step-group]')
  ;(group?.querySelector(`[data-step="${next}"]`) as HTMLElement | null)?.focus()
}
function setBranch(mode: string) {
  branchMode.value = mode
  leaf.value = mode === 'branch' ? 'u1' : 'bs'
  selectedEntry.value = leaf.value
}
function cutClass(index: number) {
  if (index >= effectiveCut.value) return 'kept'
  if (splitTurn.value && index >= turnStart.value) return 'turn-prefix'
  return 'summarized'
}
</script>

<template>
  <figure v-if="figure" class="manual-figure" :class="`kind-${figure.kind}`" :aria-labelledby="`${uid}-title`">
    <header class="figure-head">
      <div><span class="figure-index">{{ figure.page ? `FIG. ${figure.id}` : '补充图解' }}</span><span :id="`${uid}-title`" class="figure-title">{{ figure.title }}</span></div>
      <span class="figure-category">{{ figure.category }}</span>
    </header>
    <div class="english-title">{{ figure.english }}</div>

    <template v-if="figure.kind === 'prompt'">
      <div class="figure-controls">
        <label><input v-model="customPrompt" type="checkbox"> 使用自定义 preamble</label>
        <label><input v-model="skillTools" type="checkbox"> read 或 bash 可用</label>
      </div>
      <div class="diagram-scroll" tabindex="0" aria-label="系统提示词顺序图，可横向滚动">
        <div class="prompt-order" data-step-group>
          <div class="row-label">1–4 · 默认提示词，或仅一个自定义 preamble</div>
          <div class="prompt-row first-row">
            <button v-for="(s, i) in promptSections.slice(0, 4)" :key="s.label" type="button" :data-step="i" class="node prompt-node" :class="[`tone-${s.tone}`, { active: selected === i, omitted: customPrompt && i > 0, hatch: !customPrompt && i > 0 }]" :aria-pressed="selected === i" @click="selected = i" @keydown="stepKey($event, i)">
              <code>{{ i === 0 ? s.label : `<${s.label}>` }}</code><span>{{ customPrompt && i > 0 ? '不构建' : (customPrompt && i === 0 ? 'SYSTEM.md / --system-prompt' : s.summary) }}</span>
            </button>
          </div>
          <div class="row-label">5–9 · 始终考虑；为空时省略</div>
          <div class="prompt-row second-row">
            <button v-for="(s, j) in promptSections.slice(4)" :key="s.label" type="button" :data-step="j + 4" class="node prompt-node" :class="[`tone-${s.tone}`, { active: selected === j + 4, omitted: j === 2 && !skillTools }]" :aria-pressed="selected === j + 4" @click="selected = j + 4" @keydown="stepKey($event, j + 4)">
              <code>&lt;{{ s.label }}&gt;</code><span>{{ j === 2 && !skillTools ? '无 read / bash，不加入' : s.summary }}</span>
            </button>
          </div>
        </div>
      </div>
      <p class="output-line" aria-live="polite"><span class="small-label">本例构建顺序</span><code>{{ visibleSections.map(s => s.label).join(' → ') }}</code></p>
    </template>

    <template v-else-if="figure.kind === 'sequence'">
      <div class="diagram-scroll" tabindex="0" aria-label="六步时序图，可横向滚动">
        <div class="sequence-chart" data-step-group>
          <div class="sequence-head">
            <div class="tone-amber"><strong>SESSION</strong><span>AgentSession</span></div><div class="tone-amber"><strong>LOOP</strong><span>agent-loop</span></div><div class="tone-teal"><strong>TRANSCRIPT</strong><span>messages · JSONL</span></div><div class="tone-purple"><strong>PROVIDER</strong><span>pi-ai api</span></div>
          </div>
          <div v-for="(s, i) in figure.steps" :key="s.label" class="sequence-row" :class="{ active: selected === i }">
            <span class="sequence-number">{{ i + 1 }}</span>
            <div class="sequence-route" :class="{ self: routes[i].span === 1 }" :style="{ gridColumn: `${routes[i].start} / span ${routes[i].span}` }">
              <button type="button" :data-step="i" :aria-pressed="selected === i" @click="selected = i" @keydown="stepKey($event, i)"><code>{{ s.title }}</code><span>{{ s.summary }}</span></button>
              <span class="sequence-arrow" aria-hidden="true"></span>
              <span v-if="i === 1" class="sequence-return">← replayed sections · 后续同名分节覆盖之前的值</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template v-else-if="figure.kind === 'decision'">
      <div class="decision-list" data-step-group>
        <div v-for="(s, i) in figure.steps" :key="s.label" class="decision-row">
          <button type="button" class="node tone-green" :class="{ active: selected === i }" :data-step="i" :aria-pressed="selected === i" @click="selected = i" @keydown="stepKey($event, i)"><strong>{{ i + 1 }} · {{ s.title }}</strong><span>{{ s.summary }}</span></button>
          <span class="decision-arrow" aria-hidden="true">→</span>
          <div class="decision-outcome" :class="i === 5 ? 'tone-gray' : 'tone-rose'"><span class="outcome-tag">{{ i === 5 ? '唯一写入路径' : '失败则返回' }}</span><code>{{ s.outcome }}</code></div>
        </div>
      </div>
    </template>

    <template v-else-if="figure.kind === 'flow'">
      <div class="diagram-scroll" tabindex="0" aria-label="流程图，可横向滚动">
        <div class="flow-track" data-step-group>
          <button v-for="(s, i) in figure.steps" :key="s.label" type="button" class="node flow-node" :class="[`tone-${s.tone}`, { active: selected === i }]" :data-step="i" :aria-pressed="selected === i" @click="selected = i" @keydown="stepKey($event, i)">
            <span class="step-number">{{ i + 1 }}</span><code>{{ s.label }}</code><strong>{{ s.title }}</strong><span>{{ s.summary }}</span>
          </button>
        </div>
      </div>
    </template>

    <template v-else-if="figure.kind === 'tree'">
      <div v-if="figure.id === '4.6'" class="figure-controls tree-controls" aria-label="树的叶指针状态">
        <button type="button" :aria-pressed="branchMode === 'branch'" @click="setBranch('branch')">执行 branch(u1)</button>
        <button type="button" :aria-pressed="branchMode === 'reopen'" @click="setBranch('reopen')">重新打开会话</button>
        <span>当前叶节点：<code>{{ leaf }}</code></span>
      </div>
      <div class="diagram-scroll" tabindex="0" aria-label="会话树，可横向滚动">
        <div class="session-tree">
          <div v-for="n in nodes" :key="n.id" class="tree-line" :class="[{ 'on-path': activePath.has(n.id), 'tree-header': n.id === 'header' }, `tone-text-${n.tone}`]" :style="{ '--depth': n.depth }">
            <span class="tree-connector" aria-hidden="true">{{ n.prefix }}</span>
            <button type="button" :aria-label="`${n.label}；${n.id === 'header' ? '文件头，不属于树' : `parentId: ${n.parent ?? 'null'}`}；${n.note}`" :aria-pressed="selectedEntry === n.id" :class="{ 'selected-entry': selectedEntry === n.id }" @click="selectedEntry = n.id"><code>{{ n.label }}</code></button>
            <span v-if="n.id === (figure.id === '4.5' ? '01f5647e' : leaf)" class="leaf-marker">leaf</span><span class="tree-note">{{ n.note }}</span>
          </div>
        </div>
      </div>
      <div class="inspection-panel" aria-live="polite">
        <template v-if="treeEntry"><strong>{{ treeEntry.id === 'header' ? '文件头 ≠ 树根' : `所选条目：${treeEntry.id}` }}</strong><p>{{ treeEntry.id === 'header' ? '文件头不参与 parentId 链；首个 model_change 条目才是根。' : `parentId = ${treeEntry.parent === null ? 'null（根节点）' : treeEntry.parent}` }}<span v-if="treeEntry.id === 'lb'">；targetId = a1。目标引用与父子关系是两回事。</span><span v-if="treeEntry.id === 'bs'">；fromId = lb。它从标签 lb 所在的分支离开，追加在 a2 之后。</span></p></template>
        <p v-if="figure.id === '4.6'" class="branch-note">{{ branchMode === 'branch' ? 'branch(u1) 只移动内存中的叶指针，没有追加文件条目。此时退出，再打开仍会回到文件最后追加的 bs。' : '重开时按文件顺序取最后一个条目作为叶节点，因此是第 10 行 bs。高亮显示 mc → u1 → a1 → u2 → a2 → bs。' }}</p>
      </div>
    </template>

    <template v-else-if="figure.kind === 'cut'">
      <div class="cut-controls">
        <label :for="`${uid}-cut`">选择候选切分条目 <span>教学示意，不按实际 token 计量</span></label>
        <input :id="`${uid}-cut`" v-model.number="requestedCut" type="range" min="6" max="14" step="1" :aria-valuetext="`候选第 ${requestedCut + 1} 项 ${cutEntries[requestedCut].label}；有效切分点第 ${effectiveCut + 1} 项 ${cutEntries[effectiveCut].label}`">
      </div>
      <div class="diagram-scroll" tabindex="0" aria-label="由旧到新的投影条目与压缩分区，可横向滚动">
        <div class="cut-chart"><div class="row-label">OLDEST → NEWEST · U 用户 · A 助手 · T 工具结果</div>
          <div class="cut-track">
            <div v-for="(entry, i) in cutEntries" :key="i" class="cut-entry" :class="[`tone-${entry.tone}`, cutClass(i), { boundary: i === effectiveCut, candidate: i === requestedCut }]" :aria-label="`第 ${i + 1} 项 ${entry.label}：${i >= effectiveCut ? '逐字保留' : (splitTurn && i >= turnStart ? '轮次前缀摘要' : '合并历史摘要')}`"><span>{{ entry.role }}</span><small v-if="i === 0">prev</small><span v-if="i === effectiveCut" class="cut-scissors" aria-hidden="true">✂</span></div>
          </div>
          <div class="cut-groups"><div :style="{ flex: splitTurn ? turnStart : effectiveCut }" class="summary-group">messagesToSummarize<br><span>合并入历史摘要</span></div><div v-if="splitTurn" :style="{ flex: effectiveCut - turnStart }" class="prefix-group">turnPrefixMessages<br><span>单独总结轮次开头</span></div><div :style="{ flex: cutEntries.length - effectiveCut }" class="kept-group">kept verbatim<br><span>从 firstKeptEntryId 起逐字保留</span></div></div>
        </div>
      </div>
      <div class="inspection-panel" aria-live="polite"><strong>{{ requestedCut !== effectiveCut ? '候选是 toolResult，向后对齐到下一个有效条目。' : `有效切分点：第 ${effectiveCut + 1} 项 ${cutEntries[effectiveCut].label}` }}</strong><p>{{ splitTurn ? '切在轮次中途：从最近 user 到切分点之前的消息单独成为 turnPrefixMessages。调用和对应结果留在同一侧。' : '切在 user 开始处：没有拆分轮次，turnPrefixMessages 为空。' }} 实际算法先倒数估算 keepRecentTokens，再寻找有效切分点。</p></div>
    </template>

    <template v-else-if="figure.kind === 'cards'">
      <div class="section-cards" data-step-group>
        <button v-for="(s, i) in figure.steps" :key="s.label" type="button" class="section-card" :class="{ active: selected === i }" :data-step="i" :aria-pressed="selected === i" @click="selected = i" @keydown="stepKey($event, i)"><span class="step-number">{{ i + 1 }}</span><code>{{ s.label === 'custom…' ? '自定义分节' : s.label }}</code><span class="tag">{{ i === 0 ? '无标签' : i === 8 ? '可选' : '带标签' }}</span><p>{{ s.summary }}</p></button>
      </div>
    </template>

    <template v-else-if="figure.kind === 'patch'">
      <div class="figure-controls"><button type="button" :aria-pressed="patchAction === 'replace'" @click="patchAction = 'replace'">修改分节</button><button type="button" :aria-pressed="patchAction === 'remove'" @click="patchAction = 'remove'">移除分节</button><label><input v-model="supportsMidConvo" type="checkbox"> 模型支持中途系统消息</label></div>
      <div class="patch-stack">
        <section><h4>① N 轮 · 原始消息保持不变</h4><div class="message-chips"><code class="tone-blue">system: 123456</code><code class="tone-gray">other: 789</code></div></section>
        <div class="down-arrow" aria-hidden="true">↓</div>
        <section><h4>② N+1 轮 · 在末尾追加补丁系统消息</h4><div class="message-chips"><code class="tone-blue">system: 123456<span>原样，未重写</span></code><code class="tone-gray">other: 789<span>原样，未重写</span></code><code class="tone-green">sections: { system: {{ patchAction === 'replace' ? '"1234567"' : 'null' }} }<span>{{ patchAction === 'replace' ? '完整新文本，不是新增字符 “7”' : 'null 表示移除整个具名分节' }}</span></code></div></section>
        <section><h4>③ 重放后 · 同名分节后出现的覆盖先出现的</h4><div class="message-chips" aria-live="polite"><code :class="patchAction === 'replace' ? 'tone-blue' : 'tone-rose'">{{ patchAction === 'replace' ? 'system = 1234567' : 'system 分节已移除' }}</code><code class="tone-gray">other = 789</code></div></section>
        <section class="provider-result" :class="supportsMidConvo ? 'tone-green' : 'tone-amber'" aria-live="polite"><h4>④ {{ supportsMidConvo ? '支持中途系统消息：保留原位补丁' : '默认 false：合并系统消息到开头' }}</h4><p>{{ supportsMidConvo ? '原消息前缀逐字节不变，提供商已缓存的前缀仍然有效；末尾新增系统补丁。' : 'collapseSystemMessages 把系统消息合并为开头一条。前缀发生变化，从本次请求起失去先前缓存前缀。' }}</p><code>supportsMidConvoSystemMessages = {{ supportsMidConvo }}</code></section>
      </div>
    </template>

    <template v-else-if="figure.kind === 'explainer'">
      <div class="explainer-stages" data-step-group><button v-for="(s, i) in figure.steps" :key="s.label" type="button" :data-step="i" :class="[`tone-${s.tone}`, { active: selected === i }]" :aria-pressed="selected === i" @click="selected = i" @keydown="stepKey($event, i)"><span class="step-number">{{ i + 1 }}</span><strong>{{ s.title }}</strong><code>{{ s.label }}</code></button></div>
      <div class="conversation-stage" aria-live="polite">
        <template v-if="selected === 0"><div class="conversation-box tone-gray"><strong>之前压缩的摘要 · C prev</strong><p>更早的历史已总结成摘要；模型看到的是摘要，而非原始消息。</p></div><div class="conversation-box"><strong>中间的历史消息</strong><div v-for="(line, i) in conversation" :key="i" class="conversation-line"><b>{{ line[0] }}</b><span>{{ line[1] }}</span></div></div></template>
        <template v-else-if="selected === 1"><div class="conversation-box tone-gray"><strong>messagesToSummarize · 合并入历史摘要</strong><p>实现排序函数 → 编辑工具 → 排序函数写好了</p></div><div class="conversation-box tone-amber"><strong>turnPrefixMessages · 被拆轮次的开头</strong><p>再加个测试吧 → 助手调用 bash → 测试输出</p></div><div class="cut-rule">切分点：assistant “测试通过了”</div><div class="conversation-box tone-green"><strong>kept verbatim · 逐字保留</strong><p>测试通过了 → 部署一下 → bash 部署 → 部署完成</p></div></template>
        <template v-else-if="selected === 2"><div class="summary-pair"><div class="conversation-box tone-rose"><strong>生成历史摘要</strong><p>把灰色部分并入上一份摘要，previousSummary 被替换。</p></div><div class="conversation-box tone-amber"><strong>生成轮次前缀摘要</strong><p>把琥珀色部分按原始请求、目前进展、继续工作所需上下文单独总结。</p></div></div><div class="conversation-box tone-teal"><strong>追加新的压缩条目</strong><p>摘要 + firstKeptEntryId + systemMessage 完整快照。原始 JSONL 一行都不改。</p></div></template>
        <template v-else><div class="conversation-box tone-teal"><strong>系统消息：完整提示词快照</strong><p>所有分节、所有工具。由压缩条目携带快照，替代此前的原始系统消息。</p></div><div class="conversation-box tone-gray"><strong>用户消息：新的 compactionSummary</strong><p>更新后的历史摘要 + 轮次前缀摘要。</p></div><div class="conversation-box tone-green"><strong>最新消息：逐字保留</strong><div v-for="(line, i) in conversation.slice(7)" :key="i" class="conversation-line"><b>{{ line[0] }}</b><span>{{ line[1] }}</span></div></div></template>
      </div>
    </template>

    <div v-if="currentStep" class="step-inspector">
      <div class="step-detail" aria-live="polite"><span class="small-label">{{ figure.kind === 'cards' || figure.kind === 'prompt' ? '分节' : '步骤' }} {{ selected + 1 }} / {{ figure.steps?.length }}</span><strong>{{ currentStep.title }}</strong><p>{{ currentStep.detail }}</p></div>
      <div class="step-navigation" aria-label="逐步查看"><button type="button" :disabled="selected === 0" aria-label="上一步" @click="selected--">←</button><button type="button" :disabled="selected === (figure.steps?.length || 1) - 1" aria-label="下一步" @click="selected++">→</button></div>
    </div>
    <figcaption>{{ figure.caption }}<span class="figure-source">{{ figure.source }}<template v-if="figure.page"> · 原书第 {{ figure.page }} 页</template></span></figcaption>
    <details class="source-comparison"><summary>对照原始图片<span>{{ figure.page ? `原书图 ${figure.id}` : '中文补充图' }}</span></summary><a :href="imageUrl" target="_blank" rel="noopener" :aria-label="`在新标签页查看${figure.title}原始图片`"><img :src="imageUrl" :alt="`${figure.title}，用户提供的原始图片`" loading="lazy"></a><p>点击图片可在新标签页查看原尺寸。</p></details>
  </figure>
  <p v-else class="figure-missing">图解 {{ id }} 暂无对应数据。</p>
</template>

<style scoped>
.manual-figure { --ink: #232a34; --muted: #5f6772; --line: #d6d0c5; --paper: #f4f1ea; --accent: #0f5a61; margin: 30px 0; padding: 20px 20px 0; border: 1px solid #e1dcd1; border-left: 2px solid #4f9ea4; background: var(--paper); color: var(--ink); font-family: 'Source Sans 3', 'Noto Sans SC', sans-serif; font-size: 14px; line-height: 1.55; overflow: hidden; }
.manual-figure * { box-sizing: border-box; }
.manual-figure button, .manual-figure input { font: inherit; }
.manual-figure button { cursor: pointer; color: inherit; }
.manual-figure button:disabled { cursor: default; opacity: .35; }
.manual-figure button:focus-visible, .manual-figure input:focus-visible, .manual-figure summary:focus-visible, .diagram-scroll:focus-visible, .manual-figure a:focus-visible { outline: 3px solid #0f5a61; outline-offset: 3px; }
.manual-figure code { padding: 0; border-radius: 0; background: transparent; color: inherit; font-family: 'JetBrains Mono', monospace; font-size: 13px; overflow-wrap: anywhere; }
.manual-figure p { margin: 7px 0; line-height: 1.6; }
.figure-head { display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; }
.figure-head > div { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
.figure-index, .figure-category, .english-title, .row-label, .small-label { font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .14em; }
.figure-index { color: #161d27; font-weight: 600; white-space: nowrap; }
.figure-title { color: #0f5a61; font-weight: 600; letter-spacing: .045em; font-size: 16px; }
.figure-category { color: #737b85; margin-top: 2px; }
.english-title { color: #6c7480; font-size: 12px; margin-top: 5px; text-transform: uppercase; }
.figure-controls { min-height: 44px; display: flex; gap: 10px 18px; align-items: center; flex-wrap: wrap; padding: 13px 0 6px; font-size: 13px; }
.figure-controls label { min-height: 32px; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
.figure-controls input, .cut-controls input { accent-color: #0f5a61; }
.figure-controls button { min-height: 36px; padding: 6px 9px; border: 1px solid #a9b4b8; background: transparent; font-size: 13px; }
.figure-controls button[aria-pressed='true'] { background: #0f5a61; border-color: #0f5a61; color: #fff; }
.diagram-scroll { overflow-x: auto; padding: 7px 3px 12px; margin: 10px -3px 0; scrollbar-width: thin; overscroll-behavior-x: contain; }
.node { position: relative; text-align: left; border: 1px solid var(--tone-border); background: var(--tone-bg); color: var(--tone-ink) !important; padding: 11px 10px; border-radius: 0; min-width: 0; transition: border-color 160ms ease, box-shadow 160ms ease; }
.node:hover, .section-card:hover { box-shadow: 0 0 0 1px var(--tone-ink, #0f5a61); }
.node.active, .section-card.active, .explainer-stages .active { outline: 2px solid var(--tone-ink, #0f5a61); outline-offset: 2px; }
.node > code, .node > strong, .node > span { display: block; }
.node > code { font-size: 14px; font-weight: 600; }
.node > strong { font-size: 14px; font-weight: 600; }
.node > span:not(.step-number) { font-size: 13px; line-height: 1.5; margin-top: 5px; }
.tone-teal { --tone-bg: #dfeeef; --tone-border: #4f9ea4; --tone-ink: #0f5a61; }
.tone-blue { --tone-bg: #e3ecf4; --tone-border: #6f9cc4; --tone-ink: #24527a; }
.tone-green { --tone-bg: #e5eddd; --tone-border: #8aa66f; --tone-ink: #3f5e2a; }
.tone-purple { --tone-bg: #ebe7f4; --tone-border: #9a8cc6; --tone-ink: #5b4a8b; }
.tone-rose { --tone-bg: #f6e6ea; --tone-border: #cf7f93; --tone-ink: #9b3550; }
.tone-amber { --tone-bg: #f5ead4; --tone-border: #cda359; --tone-ink: #8a5513; }
.tone-gray { --tone-bg: #ebe9e4; --tone-border: #aaa69c; --tone-ink: #5f6772; }
.prompt-order { min-width: 960px; }
.prompt-row { display: grid; gap: 26px; }
.first-row { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.second-row { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.prompt-node { min-height: 76px; }
.prompt-node:not(:last-child)::after { content: '→'; position: absolute; right: -20px; top: 30%; color: #878e97; }
.row-label { color: #5f6772; font-size: 12px; margin: 0 0 8px; line-height: 1.6; }
.prompt-row + .row-label { margin-top: 14px; }
.hatch { background: repeating-linear-gradient(135deg, #e5eddd80 0, #e5eddd80 2px, transparent 2px, transparent 6px); }
.omitted { color: #69716b !important; border-style: dashed; background: repeating-linear-gradient(135deg, transparent 0, transparent 4px, #d6d0c577 4px, #d6d0c577 5px); }
.omitted code { text-decoration: line-through; }
.output-line { border-top: 1px solid var(--line); padding-top: 10px; font-size: 12px; }
.output-line code { display: block; margin-top: 5px; color: #24405e; }
.flow-track { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 23px; min-width: 1000px; padding: 4px; }
.flow-node { min-height: 158px; }
.flow-node:not(:last-child)::after { content: '→'; position: absolute; right: -19px; top: 45%; color: #878e97; font-size: 17px; }
.step-number { display: inline-flex !important; justify-content: center; align-items: center; width: 21px; height: 21px; margin-bottom: 8px; border: 1px solid currentColor; border-radius: 50%; font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.flow-node > strong { margin-top: 4px; }
.step-inspector { display: flex; gap: 18px; align-items: center; margin: 15px 0; padding: 13px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.step-detail { flex: 1; min-width: 0; }
.small-label { display: block; color: #5f6772; font-size: 12px; margin-bottom: 4px; }
.step-detail > strong { font-size: 14px; }
.step-detail p { margin-bottom: 0; font-size: 14px; color: #4c5662; }
.step-navigation { display: flex; gap: 5px; }
.step-navigation button { height: 36px; width: 36px; background: transparent; border: 1px solid #aaa69c; font-size: 16px; }
.decision-list { padding: 18px 3px 4px; }
.decision-row { display: grid; grid-template-columns: minmax(0, 1.25fr) 25px minmax(0, 1fr); align-items: stretch; margin-bottom: 12px; }
.decision-arrow { align-self: center; justify-self: center; color: #878e97; }
.decision-outcome { padding: 9px 10px; border: 1px solid var(--tone-border); background: var(--tone-bg); color: var(--tone-ink); }
.decision-outcome code { display: block; font-size: 13px; }
.outcome-tag { display: block; margin-bottom: 4px; font-size: 12px; letter-spacing: .04em; }
.sequence-chart { min-width: 1000px; padding: 5px 8px 10px 30px; }
.sequence-head { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; }
.sequence-head > div { margin: 0 15px; background: var(--tone-bg); border: 1px solid var(--tone-border); color: var(--tone-ink); text-align: center; padding: 9px; }
.sequence-head strong { display: block; font: 600 13px 'JetBrains Mono', monospace; letter-spacing: .13em; }
.sequence-head span { font-size: 12px; color: #5f6772; }
.sequence-row { position: relative; display: grid; grid-template-columns: repeat(4, 1fr); min-height: 74px; padding-top: 14px; background-image: repeating-linear-gradient(to right, transparent 0, transparent calc(12.5% - 1px), #a9b4c280 calc(12.5% - 1px), #a9b4c280 12.5%, transparent 12.5%, transparent 25%); }
.sequence-row:nth-child(3) { min-height: 108px; }
.sequence-number { position: absolute; left: -29px; top: 29px; display: flex; width: 18px; height: 18px; align-items: center; justify-content: center; border: 1px solid #878e97; border-radius: 50%; color: #5f6772; font: 12px 'JetBrains Mono', monospace; }
.sequence-route { position: relative; margin-left: calc(50% / 3); margin-right: calc(50% / 3); }
.sequence-route[style*='span 2'] { margin-left: 25%; margin-right: 25%; }
.sequence-route.self { margin-left: 50%; margin-right: 0; min-width: 360px; }
.sequence-route button { display: block; width: 100%; background: transparent; border: none; text-align: center; padding: 4px 2px; }
.sequence-route.self button { text-align: left; padding-left: 30px; }
.sequence-route button code { font-size: 13px; }
.sequence-route button span { display: block; color: #5f6772; font-size: 12px; margin-top: 2px; }
.sequence-arrow { display: block; height: 1px; background: #232a34; position: relative; }
.sequence-arrow::after { content: ''; position: absolute; right: 0; top: -3px; width: 0; height: 0; border-top: 3px solid transparent; border-bottom: 3px solid transparent; border-left: 6px solid currentColor; }
.self .sequence-arrow { position: absolute; top: 16px; left: 0; height: 12px; width: 20px; border: 1px solid; border-left: 0; background: transparent; }
.self .sequence-arrow::after { right: auto; left: 0; top: 8px; transform: rotate(180deg); }
.sequence-return { display: block; font-size: 12px; color: #5f6772; border-bottom: 1px dashed #878e97; padding-top: 7px; text-align: center; }
.sequence-row.active button code { color: #0f5a61; font-weight: 700; }
.sequence-row.active .sequence-arrow { background: #0f5a61; color: #0f5a61; height: 2px; }
.sequence-row.active .self .sequence-arrow { background: transparent; height: 12px; }
.session-tree { min-width: 1000px; padding-bottom: 4px; }
.tree-line { padding-left: calc(var(--depth) * 22px); min-height: 32px; display: flex; align-items: baseline; gap: 7px; white-space: nowrap; }
.tree-connector { font-family: monospace; color: #878e97; }
.tree-line button { min-height: 32px; border: 1px solid transparent; background: transparent; padding: 2px 3px; text-align: left; color: inherit; }
.tree-line button code { font-size: 13px; }
.tree-line.on-path button { background: #dfeeef88; }
.tree-line button.selected-entry { border-color: currentColor; }
.tree-note { font-family: 'Source Serif 4', serif; font-size: 12px; font-style: italic; color: #717b86; }
.tone-text-teal { color: #0f5a61; }.tone-text-blue { color: #24527a; }.tone-text-green { color: #3f5e2a; }.tone-text-rose { color: #9b3550; }.tone-text-gray { color: #5f6772; }
.leaf-marker { padding: 1px 5px; border: 1px solid #cf7f93; color: #9b3550; font: 12px 'JetBrains Mono', monospace; }
.inspection-panel { border-top: 1px solid var(--line); padding: 12px 0 3px; margin-top: 8px; font-size: 14px; }
.inspection-panel p { color: #4c5662; }
.branch-note { border-left: 2px solid #cda359; padding-left: 10px; }
.cut-controls { padding-top: 16px; }
.cut-controls label { display: block; font-size: 14px; }
.cut-controls label span { color: #5f6772; margin-left: 10px; font-size: 12px; }
.cut-controls input { min-height: 32px; width: min(100%, 440px); margin: 10px 0; }
.cut-chart { min-width: 1000px; }
.cut-track { display: flex; gap: 12px; padding: 10px 0 5px; }
.cut-entry { position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; width: 43px; height: 45px; flex: 1; border: 1px solid var(--tone-border); background: var(--tone-bg); color: var(--tone-ink); font: 13px 'JetBrains Mono', monospace; }
.cut-entry small { font: italic 12px 'Source Serif 4', serif; }
.cut-entry.summarized { background: repeating-linear-gradient(135deg, transparent 0, transparent 4px, #aaa69c44 4px, #aaa69c44 5px); }
.cut-entry.turn-prefix { background: #f5ead4; border-color: #cda359; color: #8a5513; }
.cut-entry.boundary { background: #9b3550; border-color: #9b3550; color: #fff; }
.cut-entry.candidate::after { content: ''; position: absolute; top: -9px; width: 5px; height: 5px; border-radius: 50%; background: #0f5a61; }
.cut-scissors { position: absolute; left: -13px; bottom: -16px; color: #9b3550; font-size: 15px; }
.cut-groups { display: flex; gap: 12px; margin-top: 15px; font: italic 12px 'Source Serif 4', serif; }
.cut-groups > div { border-top: 1px solid #aaa69c; padding-top: 7px; min-width: 0; overflow-wrap: anywhere; }
.cut-groups span { font: 12px 'Source Sans 3', sans-serif; color: #5f6772; }
.cut-groups .prefix-group { border-color: #cda359; color: #8a5513; }.cut-groups .kept-group { border-color: #4f9ea4; color: #0f5a61; }
.section-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 18px 3px 5px; }
.section-card { border: 1px solid #d6d0c5; background: #faf7f2; text-align: left; padding: 12px; min-width: 0; }
.section-card .step-number { background: #dfeeef; color: #0f5a61; border: none; margin: 0 5px 7px 0; }
.section-card code { color: #24405e; font-size: 13px; font-weight: 600; }.section-card p { margin-bottom: 0; color: #5f6772; font-size: 12px; }
.tag { float: right; font-size: 12px; background: #dfeeef; color: #0f5a61; padding: 1px 4px; }
.patch-stack { margin-top: 12px; }.patch-stack section { background: #faf7f2; padding: 14px; margin-bottom: 12px; border: 1px solid #e1dcd1; }
.manual-figure h4 { margin: 0 0 9px; padding: 0; font: 600 14px 'Source Sans 3', sans-serif; letter-spacing: 0; border: 0; }
.message-chips { display: flex; flex-wrap: wrap; gap: 8px; }.message-chips code { padding: 9px 11px; background: var(--tone-bg); color: var(--tone-ink); border: 1px solid var(--tone-border); font-size: 13px; }.message-chips code span { display: block; margin-top: 4px; font: 12px 'Source Sans 3', sans-serif; color: #5f6772; }
.down-arrow { text-align: center; margin: -7px 0 6px; color: #878e97; }.patch-stack .provider-result { background: var(--tone-bg); border-color: var(--tone-border); color: var(--tone-ink); }.provider-result p, .provider-result code { font-size: 13px; }
.explainer-stages { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 18px 3px; }.explainer-stages button { text-align: left; background: var(--tone-bg); color: var(--tone-ink); border: 1px solid var(--tone-border); padding: 11px; }.explainer-stages strong, .explainer-stages code { display: block; font-size: 14px; }.explainer-stages code { font-size: 12px; margin-top: 4px; }
.conversation-stage { min-height: 200px; }.conversation-box { background: var(--tone-bg, #faf7f2); border: 1px solid var(--tone-border, #d6d0c5); color: var(--tone-ink, #232a34); padding: 12px; margin-bottom: 10px; font-size: 12px; }.conversation-box > strong { font-size: 14px; }.conversation-box p { color: #5f6772; font-size: 13px; }.conversation-line { display: grid; grid-template-columns: 60px 1fr; gap: 10px; line-height: 1.8; font-size: 13px; }.conversation-line b { font-weight: 600; }.conversation-line:first-of-type { margin-top: 8px; }.summary-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }.cut-rule { color: #9b3550; text-align: center; border-top: 1px dashed #cf7f93; padding-top: 6px; margin: 15px 0 10px; font-size: 12px; }
.manual-figure figcaption { font-size: 13px; color: #4c5662; line-height: 1.7; margin: 15px 0; }.figure-source { display: block; margin-top: 4px; font-size: 12px; color: #717b86; font-family: 'JetBrains Mono', monospace; overflow-wrap: anywhere; }
.source-comparison { margin: 0 -20px; border-top: 1px solid var(--line); padding: 0 20px; background: #faf7f255; }.source-comparison summary { cursor: pointer; padding: 11px 0; color: #5f6772; font-size: 12px; }.source-comparison summary span { float: right; color: #717b86; font-size: 12px; }.source-comparison img { width: 100%; max-height: none; display: block; margin: 10px auto; object-fit: contain; }.source-comparison > p { font-size: 12px; color: #717b86; margin: 9px 0 14px; }
@media (max-width: 680px) { .manual-figure { padding: 15px 13px 0; margin: 24px 0; }.figure-title { font-size: 14px; }.figure-head > div { gap: 6px 10px; }.figure-category { display: none; }.figure-controls { gap: 9px; }.section-cards { grid-template-columns: repeat(2, 1fr); }.section-card { padding: 10px; }.section-card code { font-size: 13px; }.decision-row { grid-template-columns: 1fr 19px 1fr; }.decision-row .node { padding: 8px; }.decision-row .node > strong { font-size: 14px; }.decision-row .node > span { font-size: 13px; }.decision-outcome { padding: 8px; }.decision-outcome code { font-size: 13px; }.step-inspector { align-items: flex-start; gap: 10px; }.step-navigation { flex-direction: column; }.source-comparison { margin: 0 -13px; padding: 0 13px; }.explainer-stages { grid-template-columns: repeat(2, 1fr); }.summary-pair { grid-template-columns: 1fr; gap: 0; }.cut-controls label span { display: block; margin: 4px 0 0; } }
@media (prefers-reduced-motion: reduce) { .manual-figure *, .manual-figure *::before, .manual-figure *::after { transition: none !important; animation: none !important; scroll-behavior: auto !important; } }
</style>
