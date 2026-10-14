# Chapter 5 import and source review

## Authority and inspection

- Text authority: `sources/full/5 配置与扩展/5 配置与扩展.md` (unchanged).
- Figure/caption/layout authority: original Pi Technical Manual, physical PDF pages 99–142 (printed pages agree).
- All 44 PDF pages visually inspected in page contact sheets; figure-bearing pages and their extracted text checked in detail. All twelve supplied images inspected individually at readable resolution.
- Rebuild: `python3 scripts/import_05.py`. This script writes only the six chapter pages, twelve copied chapter images, chapter figure JSON, chapter navigation manifest, and this report.
- Source SHA-256: `8faa64203c31a308c675121338fb352ca4b37bb6a792b2ad6981e8a3058dffec`

## Coverage

Six top-level sections preserved in order. The initial `# 5 配置与扩展` becomes the chapter navigation label; no prose is omitted. All source headings inside fenced code remain code. Markdown emphasis is rendered with strong tags to avoid CJK punctuation ambiguity; this changes markup only.

| Page | Normalized nonempty lines | Exact code blocks | Raw table rows | Original figures |
|---|---:|---:|---:|---:|
| 配置、模型与身份验证 | 146 | 3 | 14 | 4 |
| 上下文文件、技能、模板、主题与包 | 159 | 4 | 21 | 2 |
| 扩展：加载与 API | 151 | 4 | 27 | 2 |
| 扩展事件与上下文 | 143 | 2 | 54 | 1 |
| 运行模式：交互式、print 与 JSON | 142 | 3 | 22 | 2 |
| RPC 模式与 SDK | 217 | 4 | 83 | 1 |

- Normalized nonempty source-line multiset coverage: **100%** (958 lines). The normalization removes presentation-only strong markers, normalizes fenced-language labels, maps original image references to their BookFigure IDs, and unescapes table-only inline-code pipes, and ignores blockquote presentation markers.
- Fenced code: **20/20 blocks byte-identical internally**, in original order; SHA-256 over concatenated code interiors: `884c5a1a7e7448a10732ca72e10b392080b1d3917ecd5d47a0565cb6342d74de`.
- Table rows: **221/221** preserved; raw tables retained for central styling.
- Figures: **12/12** original references and **12/12** original PNGs retained; 12 faithful native coordinate-based diagrams, including the full directory tree.
- Inline-code pipe repairs: 19 affected inline-code spans; pipe characters remain visible content rather than creating accidental table cells.
- Malformed adjacent strong delimiters: 2 lines repaired without text edits.
- All assertions run on every rebuild. Source bytes were rehashed after output and remained unchanged.

## Figure inventory

| Figure | PDF page | Supplied image | Representation |
|---|---:|---|---|
| 5.1 | 100 | image 5.png | Native directory tree + complete source transcription |
| 5.2 | 101 | image 2.png | Coordinate-based diagram |
| 5.3 | 104 | image 8.png | Coordinate-based diagram |
| 5.4 | 105 | image 10.png | Coordinate-based diagram |
| 5.5 | 107 | image 1.png | Coordinate-based diagram |
| 5.6 | 107 | image 6.png | Coordinate-based diagram |
| 5.7 | 114 | image 7.png | Coordinate-based diagram |
| 5.8 | 116 | image 9.png | Coordinate-based diagram |
| 5.9 | 123 | image.png | Coordinate-based diagram |
| 5.10 | 127 | image 4.png | Coordinate-based diagram |
| 5.11 | 129 | image 11.png | Coordinate-based diagram |
| 5.12 | 134 | image 3.png | Coordinate-based diagram |

### Geometry and semantic fidelity

- 5.1 is a native label-only directory tree with all 15 user-directory child rows, all three project-directory child groups, both independent Agent Skills roots, and the independent ancestor-context row. User/project scope columns use parent–child tree branches without arrowheads; no flow is invented. Every original permission, trust condition and side note is retained. The supplied code transcription stays below, and the high-resolution original remains available for comparison.
- 5.2 retains two merging inputs plus the separate global-only bypass and all four global-only keys.
- 5.3/5.4/5.6 preserve the original first-match ladders, each original choice and its exception conditions. The notes distinguish precedence from mandatory sequential execution.
- 5.5/5.7/5.10 preserve original horizontal/vertical direction, all original steps, and their internal ordering.
- 5.8, 5.9 and 5.12 preserve participant columns, dashed lifelines, directed calls, dashed returns, self-calls and stage numbers. Explicit edge coordinates remain independent of node bounds.
- 5.11 retains all four modes × four stream/UI columns (16 comparison cells), including no-op/hasUI false and print exit behavior. It contains no invented flow arrows.
- Every original image remains available to the shared component for comparison.

## Verified repairs

1. **Trust caption moved, wording unchanged.** In supplied Markdown, the paragraph starting “返回‘未决定’的处理器…” occurs before Fig.5.5. PDF p.107 places the equivalent paragraph immediately below Fig.5.6, referring to the trust ladder. The importer moves the exact paragraph immediately below Fig.5.6. Apart from the independently verified callout-heading move below, all other source body order remains unchanged. The following prompt-text quotation stays in place.
2. **Figure 5.7 placeholder restored.** The supplied PNG/PDF visually drops the opening `<` in the first `-e <source>` item. The explicit numbered Chinese source list confirms the complete spelling. The redraw uses `-e <source>`.
3. **Figure headings/captions recovered as metadata.** Figure IDs/titles are embedded in the original images and absent from Markdown figure alt text. All 12 IDs and titles are mapped against PDF pages; Chinese captions remain in the body as requested and are additionally available to the shared figure component.
4. **Inline-code table pipes escaped.** For example, `echo "..." | pi` stays one table cell instead of splitting the invocation and mode columns. All similar cases are repaired mechanically without altering displayed text.
5. **SDK table-caption/callout association repaired.** PDF p.141 shows the paragraph beginning “如果没有传入 sessionManager” as the defaults-table caption, without a DOC ≠ CODE heading. The supplied heading is moved, unchanged, to the later paragraph beginning “createAgentSession 的 JSDoc”, which is the actual DOC ≠ CODE callout in the PDF. The table caption stays in place and remains verbatim.
6. **Adjacent strong markers normalized.** The directory trust-resource sentence and RPC table's data-column heading contain `****` artifacts. Their visible text is preserved.

## Ambiguities retained rather than silently rewritten

- **Fig.5.1 sessions extension:** original image and PDF p.100 show `sessions/--<cwd>--/*.jsonl`; supplied Chinese Bash directory block says `*.json`. Markdown is the code authority, so its exact code is retained. Original image remains correct to the PDF. This is a documented discrepancy, not a claim both spellings are equivalent.
- **Fig.5.7 builtin spelling:** original image/PDF p.114 use `builtin:llama.cpp`; supplied Markdown prose/table/list use `builtin:lama.cpp`. The redraw follows the original figure, while body and code preserve the supplied text. No source version was invented.
- **Fig.5.10 source-line annotations:** the graphic uses positions such as runtime `main.ts:863`, whereas the accompanying prose discusses factory execution at `main.ts:730`. Both are preserved in their respective authorities; a graphic location label is not silently replaced with a prose citation.
- The full extension example appears before its introductory prose in supplied Markdown, while PDF p.113 places it later. This is not a caption association error, so the Markdown's body order is retained.
- Source spelling/casing such as `jsonL.ts` / `attachJsonLLineReader` is not corrected inside supplied code or prose. This import is not a code-version reconciliation.

## Validation boundary

Local source import and structural assertions completed. VitePress Markdown parsing and Vue template compilation of all six pages reported zero errors. The 21 tables parse as 200 header/data rows plus 21 delimiter rows, with consistent column counts. All figure nodes and explicit edge points fit their canvases, and all edge endpoints resolve. Two consecutive importer runs produced identical page, figure-data and navigation hashes. Global site build, browser review, deployment, remote pushes, shared table/callout styling and shared component rendering belong to the parent task and were not run here.
