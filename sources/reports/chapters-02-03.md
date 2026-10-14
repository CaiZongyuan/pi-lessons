# Chapters 02–03 import and verification

## Scope and authority

- Text authority: supplied Chinese Markdown, unchanged. Original PDF pp.24–73 and all 15 supplied PNGs visually inspected before authoring.
- Eight reading pages, four per chapter. Navigation: `navigation-02-03.json`.
- All 15 source figures reconstructed with native nodes/edges and exact original figure IDs/titles; source PNGs copied without recompression for expandable inspection.
- All original caption text retained in the body pending the shared central callout pass. Figure JSON captions reproduce supplied authoritative wording. Fig.2.5 uses its PDF-verified caption paragraph, relocated intact from its erroneous export position; the capture introduction remains separate prose.
- No shared theme/config/CSS changes and no publication, push, or global build.

## Reproducible validation

Run `python3 scripts/import_02_03.py`. The importer asserts all code bodies match byte-for-byte, independently compares normalized prose/code, preserves table and image counts, verifies image hashes, and validates figure geometry and edge targets.

Independent verification: all eight pages parsed through VitePress createMarkdownRenderer and Vue compileTemplate successfully; every rendered table row has the same cell count as its header. All node labels fit their boxes under the shared 13px monospace layout estimate, and positioned edge labels remain within their viewboxes. No global build or browser run by this worker.

```json
[
  {
    "chapter": 2,
    "sections": 4,
    "figures": 7,
    "tables": 8,
    "table_rows": 77,
    "code_blocks": 9,
    "code_lines": 122,
    "prose_code_coverage": "PASS"
  },
  {
    "chapter": 3,
    "sections": 4,
    "figures": 8,
    "tables": 9,
    "table_rows": 85,
    "code_blocks": 5,
    "code_lines": 97,
    "prose_code_coverage": "PASS"
  }
]
```

## Export repairs (presentation only)

- Parse sections using a fence-aware line scanner. A `#` inside a captured code example cannot create a reading page.
- Collapse exporter-only `****` seams and convert paired `**` emphasis into explicit strong tags so punctuation-adjacent CJK emphasis renders consistently. No code body is changed.
- Normalize escaped ordinary punctuation outside code spans: dots, hyphens, parentheses, brackets, braces, exclamation/plus signs and underscores; collapse multiply escaped prose pipes to one Markdown escape.
- Escape pipes inside inline-code spans only when inside a table row, preventing TypeScript unions such as `Partial<Record<level, string | null>>` from creating phantom columns.
- Normalize fence labels: TypeScript→ts, JavaScript→js, JSON→json, Plain Text→text, Shell→sh. Preserve fenced body whitespace and content.
- Replace source image tags with BookFigure references; preserve caption wording. One PDF-verified Fig.2.5 paragraph relocation restores the original figure association (documented below).
- Wrap the literal faux endpoint `http://localhost:0` in inline code, preserving visible text while preventing VitePress from interpreting an ephemeral test endpoint as a navigable/dead local link.
- Leave pre-existing ellipses, missing-data annotations, suspicious sample values, mixed English/Chinese caption text, source citations, and code indentation exactly as supplied.

## Source issues retained (not silently repaired)

- §2.2 core rule contains two `［原文缺失事件名］` placeholders. Original PDF p.31 reads `error` for the first, `done` for the second, and explicitly says direct `streamSimple()` calls. These PDF-confirmed readings are recorded here, but authoritative Chinese prose remains unchanged.
- §3.1 states its source citation was truncated as `agent/agent-`. The reference continues on original PDF p.51 as `loop.ts:163`. The supplied note remains unchanged.
- Figure 2.5 caption relocation (PDF p.38 verified): move the exact source paragraph beginning `历史记录始终为目标模型重写，而不是为源模型重写。` from before Anthropic OAuth to immediately below BookFigure 2.5. It is now the catalog caption and body caption. The supplied `图 2.5：transformMessages 如何处理历史记录。采集工具…` paragraph retains its exact wording but is restored to ordinary capture-introduction prose. Coverage asserts the moved paragraph occurs exactly once on each side, then compares all remaining text in its original order. No source words or code changed.
- The supplied chapter2 groq JSON prose example spells `lama-3.1-8b-instant`; PDF p.46 spells `llama-3.1-8b-instant`. Source spelling is retained.
- §2.4 captured cost examples and §3.3/3.4 excerpts remain source snapshots; no current-library claims or external corrections were introduced.

## PDF-verified callout classifications for central pass

- p.26 WHY IT MATTERS: paragraph beginning `导入 @earendil-works/pi-ai 的扩展并不会得到根入口` is plain prose in the Markdown export.
- p.31 CORE RULE: quoted paragraph beginning `成功的流在任何局部更新之前发出 start` under `核心规则`.
- pp.32,45,52,60,64 FOOTGUN: source blockquotes titled `易踩的坑`.
- pp.39,65 DOC ≠ CODE: source blockquotes titled `文档 ≠ 代码` (including mixed typography if present).
- p.71 RULE OF THUMB: paragraph beginning `如果客户端需要知道“模型已完成回答”` is plain prose in the Markdown export.
- pp.29,35,39,47,56,60,65,73 WHAT THIS MEANS FOR YOU: source blockquotes beginning `这对你意味着什么`.
- Source/citation blocks remain raw `>` blocks, separate from figure captions and callouts.

## PDF-verified table-caption paragraph prefixes

These exact normalized source paragraph prefixes identify the complete paragraph to style, without inventing new text. Retain their inline formatting and source references.

- p.25 / ch02/providers-models: `24 个方法，只有一条路由规则`
- p.27 / ch02/providers-models: `助手内容由文本、思考和工具调用构成`
- p.28 / ch02/providers-models: `限制、价格和特殊行为都随模型一起传递`
- p.30 / ch02/streaming-events: `三种内容块 × start、delta、end`
- p.37 / ch02/wire-apis: `每种协议一个文件，每个文件可服务多个提供商`
- p.37 / ch02/wire-apis: `签名只对写入它的 API 有意义`
- p.43 / ch02/auth-cost-retries: `42 个提供商中，有 40 个具有 API 密钥变量`
- p.44 / ch02/auth-cost-retries: `每个 OAuth 流程最终都得到同一种 OAuthCredential`
- p.49 / ch03/agent-loop: `整个运行时集中在三个文件中`
- p.50 / ch03/agent-loop: `除 convertToLlm 外，每个钩子都是可选的`
- p.53 / ch03/agent-loop: `Steering等待当前轮次的工具完成`
- p.57 / ch03/agent-events: `只有助手消息以流式方式传递`
- p.59 / ch03/agent-events: `不带选项构建的 Agent 没有模型`
- p.60 / ch03/agent-events: `状态在监听器运行之前更新`
- p.63 / ch03/agent-session: `编码智能体的每种角色，要么以用户消息的形式传达给模型`
- p.73 / ch03/prompt-lifecycle: `十种智能体事件之上，还有十二种会话事件`
- p.71 retry-settings following paragraph is preserved as source prose; no caption wrapper inferred.

## Native diagram decisions

- Figures 2.4, 3.2 and 3.8 keep source participants, direction, chronology and solid/dashed event distinction. Dashed, non-arrow lifelines retain the participant lanes; numbered phase labels and explicit routes preserve the original messages.
- Figure 2.2 uses three unconnected comparison rows; it does not imply transitions between the scenarios.
- Figure 2.3 shows the three content-block grammars as peers and records zero-or-more semantics in notes, rather than implying an obligatory text/thinking/tool order.
- Figure 3.1 retains first-turn bypass, all three stops, and both loop-back paths. Notes preserve the special error-path finishTurn behavior.
- Figure 3.3 retains printed lifecycle indentation; node details contain the source annotations and full block-event sequences.
- Figures with compact cards move the original card explanatory text into the selectable node detail, preserving it verbatim or as a directly matched Chinese note. Original images are available alongside every native version.

## Source-palette reconciliation (tone-only)

- Audited against all supplied images and PDF figure pages. Chapter 2 provider/model transport, transcript, auth and catalog nodes are plum; chapter 3 model/assistant nodes are plum. Extension hooks and event nodes retain purple.
- Listener/UI state nodes and handled/queued dispositions are indigo. The skill/template settings row in Fig.3.7 is config. The two neutral message_update rows in Fig.3.3 are gray, matching the original tree text.
- Exact per-node corrections below: 38 purple→plum, 8 blue→indigo, 1 green→config, and 2 purple→gray. No text, caption, geometry, edge or source-image change.
```json
{
  "plum": [
    "2.1-models",
    "2.1-provider",
    "2.1-api-0",
    "2.1-api-1",
    "2.1-api-2",
    "2.1-api-3",
    "2.1-api-4",
    "2.1-api-5",
    "2.2-r0-0",
    "2.2-r0-3",
    "2.2-r1-0",
    "2.2-r1-3",
    "2.3-start",
    "2.3-text",
    "2.3-thinking",
    "2.3-tool",
    "2.3-done",
    "2.4-lane-1",
    "2.4-lane-2",
    "2.4-lane-3",
    "2.4-lane-4",
    "2.5-step-1",
    "2.5-step-2",
    "2.5-step-3",
    "2.6-step-0",
    "2.6-step-1",
    "2.6-step-2",
    "2.7-step-1",
    "2.7-step-3",
    "2.7-step-4",
    "2.7-step-5",
    "3.1-step-5",
    "3.3-event-4",
    "3.3-event-6",
    "3.3-event-12",
    "3.3-event-14",
    "3.7-check-6",
    "3.8-lane-2"
  ],
  "indigo": [
    "3.2-lane-3",
    "3.3-event-17",
    "3.4-step-2",
    "3.6-step-3",
    "3.7-outcome-0",
    "3.7-outcome-2",
    "3.7-outcome-4",
    "3.8-lane-3"
  ],
  "config": [
    "3.7-check-3"
  ],
  "gray": [
    "3.3-event-5",
    "3.3-event-13"
  ]
}
```

## Immutable source SHA-256

```json
{
  "sources/full/2.提供商层/2.提供商层.md": "b2d7ff3e7f9e70210d6571b0586b6c6329758c8b27613d2c80e8d41b0ebfb29f",
  "sources/full/2.提供商层/图片和附件/image 2.png": "1cc180033b84574cfaf802bd092b3d20b7e5cf016cfde825bbc9a71823938c05",
  "sources/full/2.提供商层/图片和附件/image 6.png": "95567e6eed8afcf8b5fabecac131eaa2a6f2ff40fd4e13ab2f9f8c93fed17f53",
  "sources/full/2.提供商层/图片和附件/image 3.png": "91cdf6408e166048c97a5838372efe729b2d7053623aa27f18be99643feb645a",
  "sources/full/2.提供商层/图片和附件/image 5.png": "69b091af423416c14b939cde2ea940d35e500c5c71b7e2f5017bfd0904e79d63",
  "sources/full/2.提供商层/图片和附件/image.png": "c8ffb931cd3d5f789d97bbeda7938b663c9db9a046d79d6b07d27f2a7eeb8451",
  "sources/full/2.提供商层/图片和附件/image 4.png": "35b0bf43ef23b44aa8c7e52e0d4818f25d79bae795fd2a8e7fad5bef0274ce6a",
  "sources/full/2.提供商层/图片和附件/image 1.png": "5df13510d5956b97bd0b5238bccee1161559e69dd8dfd2822f3862e779ae853c",
  "sources/full/3.智能体循环/3.智能体循环.md": "390a172d5e9d4d1011951fab21691c348ae6286d542fb74942e473849aceec81",
  "sources/full/3.智能体循环/图片和附件/image 4.png": "5cdc9fe82006b06232991be327af921709cb649129342aabbd4d79fbfd39803a",
  "sources/full/3.智能体循环/图片和附件/image 2.png": "5c564d4c307affeef6db098eeebac71b98c411213525536279e6d47850eb3605",
  "sources/full/3.智能体循环/图片和附件/image 1.png": "b7876d456a519a79f12917d07f72bd3f0622f8c24b8b23c6207babfd3f553ebf",
  "sources/full/3.智能体循环/图片和附件/image 5.png": "1e5f9608a7a952c9377a45b283ba05c6558ab22fa3fa3b7eaeef90e8d93fdc63",
  "sources/full/3.智能体循环/图片和附件/image 7.png": "fd5d379685e68917774ffe282f4d75679b78002264fef124448957cfe79dd556",
  "sources/full/3.智能体循环/图片和附件/image.png": "eb5bc2d98de83cb028acb7bfd12ce4e1000070340c2148fd701a48b3a392f807",
  "sources/full/3.智能体循环/图片和附件/image 3.png": "9f128995fcf02350794b3a8f6d7831c1bd0ad008fa750ab416685b55a94a3cae",
  "sources/full/3.智能体循环/图片和附件/image 6.png": "be694231a795d34f2c2874b0cd3aa84e9d329b12dce1324265b52b014b7ba171"
}
```
