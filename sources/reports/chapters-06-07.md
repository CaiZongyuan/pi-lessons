# Chapters 6–7 import verification

Scope: supplied Chinese Markdown and 15 PNGs only; original English PDF is the visual/caption verification source. All 41 PDF pages 144–184 were visually reviewed in contact sheets; all 15 PNGs were inspected at readable resolution. Chapter 7 begins on p166, after the p165 divider; p184 is the reference divider.

## Reproduction and coverage

Run `python scripts/import_06_07.py`. Inputs under `sources/full/` are never written. The importer asserts line-order normalized source coverage and exact code-body equality before writing the six pages.

| Chapter | Pages | Figures | Code blocks | Tables | Table lines | Headings | Normalized nonempty source lines |
|---|---:|---:|---:|---:|---:|---:|---:|
| 6 | 3 | 7 | 8 | 9 | 70 | 18 | 308 |
| 7 | 3 | 8 | 5 | 7 | 46 | 17 | 247 |

Normalization ignores whitespace, Markdown emphasis/escaping, quotation markers, fence language spelling and image/component syntax. Added PDF-verification notices and two recovered callout titles are excluded. All source prose, lists, tables, captions, citations and notes remain in original order. Code contents receive an independent byte-for-byte string comparison, including the nested Markdown sample.

An isolated VitePress Markdown-token check (without a global build) parsed 16 tables, 100 header/data rows, 13 outer code blocks and 15 BookFigure references. Every parsed table row matches its header column count. Diagram validation checks unique node ids, node bounds, edge endpoints and all original image paths.

## Evidenced presentation repairs

- PDF p154 contains a Markdown output sample with an inner TS fence. Its outer source fence is lengthened from three to four backticks; all interior text and the inner fence are preserved.
- The source labels the Lark grammar as TypeScript. PDF p154 labels it LARK. The output uses literal text highlighting; its code remains unchanged.
- Repeated `****` emphasis artifacts outside code are removed; other bold text becomes explicit `<strong>` for CJK punctuation compatibility. Inline-code pipe characters in Markdown table cells are escaped, preserving their visible values.
- PDF p164: the final `对你的意义：` paragraph and four bullets in the TUI section are restored as a practical-takeaway blockquote.
- PDF p176: the source paragraphs beginning `拒绝信任并不会阻止…` and `示例扩展…` regain their original FOOTGUN and DOC ≠ CODE callout roles. Paragraph contents are unchanged; verified headings are added.

## Source discrepancies retained and explicitly annotated

- PDF p179 visibly reads `setStatus(status: SpanStatus): void;`. The supplied code reads `focal Status(status: SpanStatus): void;` and its supplied translator note says the corruption could not be resolved. Both supplied items remain unchanged; a separately labeled `PDF核对注` records the original PDF line.
- PDF p154 shows a literal space in the `OPTIONS_LINE` character class, `[ \t]`; supplied code has `[\t]`. Supplied code is unchanged; a PDF-verification note states the difference.
- PDF p181 shows `X-BILLING-INVOKE-ORIGIN: Pi`; the supplied table has `X-BILLING-INFOKE-ORIGIN: Pi`. Supplied table text is retained and the discrepancy is stated separately.

## Figure mapping and native reconstruction

| Figure | PDF page | Supplied PNG | Treatment |
|---|---:|---|---|
| 6.1 | 145 | image 4.png | Native diagram, with original PNG comparison |
| 6.2 | 148 | image.png | Native diagram, with original PNG comparison |
| 6.3 | 152 | image 1.png | Native diagram, with original PNG comparison |
| 6.4 | 156 | image 3.png | Native diagram, with original PNG comparison |
| 6.5 | 159 | image 5.png | Native diagram, with original PNG comparison |
| 6.6 | 160 | image 2.png | Native diagram, with original PNG comparison |
| 6.7 | 163 | image 6.png | Native diagram, with original PNG comparison |
| 7.1 | 167 | image 6.png | Native diagram, with original PNG comparison |
| 7.2 | 169 | image 4.png | Native diagram, with original PNG comparison |
| 7.3 | 170 | image 5.png | Native diagram, with original PNG comparison |
| 7.4 | 172 | image 7.png | Native diagram, with original PNG comparison |
| 7.5 | 175 | image 3.png | Native diagram, with original PNG comparison |
| 7.6 | 176 | image.png | Native diagram, with original PNG comparison |
| 7.7 | 180 | image 2.png | Native diagram, with original PNG comparison |
| 7.8 | 182 | image 1.png | Native diagram, with original PNG comparison |

All 15 figures now use native interactive data, retaining their original PNG comparison. All original figure numbers and captions were checked. No supplemental figure ids are needed. Native diagrams preserve original grouping and arrows: row-wise decisions remain row-wise, comparisons and byte fields have no invented relationships, process topology preserves only the four arrows drawn in the source, and 7.2/7.5 explicitly distinguish decision-reading order from unconditional execution. Every native node carries inspectable source detail.

- FIG6.1: four dashed lifelines, ten message/self-call arrows, five step markers, version-check loop, progress dotted arrow, dashed returns, pagination limit and timeout-reset annotation. Explicit points preserve direction and timing independently of actor-box bounds.
- FIG6.4: five lifelines, thirteen message/self-call arrows, five step markers, call_7 and call_7/1 identifiers, parentToolCallId, both hook phases, intermediate result returning only to VM, and success-only codemode-store append. Dashed returns and final model output remain separate.
- FIG7.4: exact 25-byte scale at 64 drawing units per byte; touching fields span 4/1/5/6/8/1 bytes, with offset ticks at 0/4/5/10/16/24/25. All original hex strings, including the original version-field ellipsis, are preserved. The importer asserts byte widths, boundaries and total length.

Reference palette reconciliation uses an explicit node whitelist: model/AI-context plum in 6.2/6.4/7.7; the original indigo clients, UI/renderers, terminal capability outcomes, CBOR map/key fields and telemetry contract in 6.1/6.5/6.6/6.7/7.1/7.4/7.7; mint configuration decisions in 7.5. Existing purple extension/runtime nodes remain purple. Blue data nodes (including the hello value) are unchanged. Original hatching is restored on optional Radius/pi-env nodes (7.1), the non-boundary call gate (7.6), and absent exporter/producer/schema nodes (7.7). No role-only or global recoloring is applied.

## Table and callout verification

- Ch6 tables: MCP module files p144; transports p146; exposure modes p147; retries p149; sandbox probes p152; runtime limits p153; overlay fields p162; native binaries p163; built-in components p164.
- Ch7 tables: durable harness tasks p169; storage backends p170; protocol message types p172; five trust options p175; isolation methods p177; product telemetry p181; evaluation suites p182.
- Original table captions remain immediately before/after their tables. Original figure captions remain in the body and also populate the figure data for shared presentation.
- Verified original callouts: DOC ≠ CODE p149/p161/p176/p180; RULE OF THUMB p157/p181; practical takeaways p150/p164/p173/p178/p182; FOOTGUN p176; source blocks at each section end.

## Boundaries

No shared files, global build, browser preview, Git remote, publication or push were changed by this importer. Shared-component visual QA remains an integration task for the parent.

## Immutable input hashes

| Source | SHA-256 |
|---|---|
| sources/full/6.集成与界面/6.集成与界面.md | `d426e2dd1a8803b863235df823ae6d9d97746c901cfca8387edd9463a5442c44` |
| sources/full/6.集成与界面/图片和附件/image 1.png | `480daa3b120b0ca52844fe4d47b7b3bd729702073d7bad64e570c310c92235bd` |
| sources/full/6.集成与界面/图片和附件/image 2.png | `402ada1f028367c0900f5650ab35f6fcb95c8bc77346353c503441a21171ca63` |
| sources/full/6.集成与界面/图片和附件/image 3.png | `55f999c16cecbd358390643c4b271c0e939a36168058eca3879f93be839840c3` |
| sources/full/6.集成与界面/图片和附件/image 4.png | `6f0d5f3f99330fdbf9ac9b003f664f366ebf27767c392531646d4d985f11b0e6` |
| sources/full/6.集成与界面/图片和附件/image 5.png | `f53600fcd9b00acd5c75e19d0c657c4637f9ccf36bff60288f796c7396cd9b4d` |
| sources/full/6.集成与界面/图片和附件/image 6.png | `529229e3ce0afe18308606d690736bbab57390dfc1d3a3b54d1bee6d02e782ef` |
| sources/full/6.集成与界面/图片和附件/image.png | `79e157b790eb4268a256faa1858be31f5b43612b746c993c69b458655104724c` |
| sources/full/7.实验性功能与运维/7.实验性功能与运维.md | `505310500f55d01a9b2ffa1041084007966a1d8edb9d135ca4d40c8405c5e171` |
| sources/full/7.实验性功能与运维/图片和附件/image 1.png | `8f8bedbea3f72c46e4b64282bd8d835e92c7fa3d1123eb95bba4778af30f563c` |
| sources/full/7.实验性功能与运维/图片和附件/image 2.png | `e986d1fd2271fa51ccc00c708bdb55f9db18cc1cc6ae69bfbabbd644b832894c` |
| sources/full/7.实验性功能与运维/图片和附件/image 3.png | `510dbab8c339a7c501afa3b203a20bf0652c43b737941bda70499d543b60da09` |
| sources/full/7.实验性功能与运维/图片和附件/image 4.png | `5cfd6cf1b26d19d3f609caf15d1191417dee0a0d71d390bd5bf5239c6bbc4522` |
| sources/full/7.实验性功能与运维/图片和附件/image 5.png | `b8584fd6f9e69cf91ce218092934ff686be7465db4a06cbfce57926fa9c7a26e` |
| sources/full/7.实验性功能与运维/图片和附件/image 6.png | `8a4a1cd6f7bbb95f3d9e8993095b575c842e9c3eed7e8e88ba9b26f444b88913` |
| sources/full/7.实验性功能与运维/图片和附件/image 7.png | `ac62efba4a0ee9627d1807812074b96bb0904a1b58bedabda6ddb0c8cb363bd9` |
| sources/full/7.实验性功能与运维/图片和附件/image.png | `ecc8ca8e22e4eaa58d13d19d49b0fb02023420927875db53198dbdc473bc424a` |
