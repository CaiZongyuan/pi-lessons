# Chapter 1 import evidence

## Result and scope
- Three complete reading pages; five native interactive figures; five immutable source PNGs copied verbatim for comparison. FIG.1.2 transcribes original drawn bar lengths without inventing a common numeric scale.
- Restored the missing FIG. 1.6 caption on the existing event table. This is a table in PDF p20, not a sixth missing image.
- Sources: `sources/full/1.模型/1.模型.md` and its five PNG attachments. PDF authority: Pi Technical Manual, printed/PDF pages 7–22. No claims based on executing the book's commands or fetching repository code.
- Import/validation: `python scripts/import_01.py` and `python scripts/import_01.py --check`.

| Reading page | Original first page | Route |
| --- | --- | --- |
| 1.1 Pi 的用途 | 7 | /pi-104/ch01/what-pi-is-for |
| 1.2 一页看懂 monorepo | 11 | /pi-104/ch01/monorepo |
| 1.3 一个提示的生命周期 | 15 | /pi-104/ch01/prompt-lifecycle |

## Coverage checks (passed)
- Normalized full text: 18,921 non-whitespace characters, exactly equal in source order after removing only documented formatting wrappers and the newly restored figure-table caption.
- Fenced code: 2 blocks / 23 body lines; every code body compared byte-for-byte (line endings excluded). A regression test injects an H1-looking line inside a code fence and verifies that the section splitter still returns exactly three pages.
- Markdown tables: 4, preserving 7 data rows × 4 columns, 15 data rows × 5 columns, 18 data rows × 6 columns, 8 data rows × 4 columns; all rows and columns unchanged.
- Every source image appears exactly once and maps to its verified original figure ID.
- Source SHA-256: `a7d65aa52c6c5fa35de610f42b6315b03e5810eeab5dd99d4d9a5b90450622e5`.
- Native FIG.1.2 chart checks: exactly 14 bars, each original drawn width and each stated numeric value locked independently; shared baseline x=366, 28px bar height, and meaningful bar accessible names. No formula maps values to widths.
- Native graph checks: unique node IDs; every edge resolves; nodes and explicit edge points stay within the viewBox; FIG.1.4 has 7 lifelines + 12 numbered steps; FIG.1.5 has 6 lifelines + 10 numbered steps including 2 self-loops.
- Reproducibility: --check compares every generated Markdown page, navigation JSON, figure catalog, report, and copied PNG against the in-memory regeneration without writing.

## Visual reference audit
All sixteen PDF pages 7–22 were rendered and visually inspected, including all source lists, callouts, code panels, figure/table captions, and all five supplied images at native size.

| Figure | PDF page | Supplied image | Fidelity decision |
| --- | --- | --- | --- |
| 1.1 | 9 | image.png | Native three-column classification, 14 boxes; original membership, ordering and detail retained. No invented arrows. |
| 1.2 | 12 | image 1.png | Native chart faithfully transcribes 14 original drawn bars, package/value labels, color classes and annotations. Explicit caveat: visual transcription, not recalculated quantitative scale. Original comparison retained. |
| 1.3 | 13 | image 3.png | Native five-layer dependency layout plus aside. In-box → lists preserve the original dependency encoding and dev-only/undeclared-import exceptions. |
| 1.4 | 16 | image 2.png | Native seven-lane sequence, exact 12-step arrow directions, dotted events versus dashed provider stream, and first write before model call. |
| 1.5 | 18 | image 4.png | Native six-lane sequence, exact ten steps, LOOP→EXT hooks, two self-loops, and agent_settled after agent_end. |
| 1.6 | 20 | Markdown event table | Native table; caption restored from “ONE ANSWERED PROMPT, EVENT BY EVENT”. All event groups 1–29 retained. |

### Other table/caption verification
- p7 core-surfaces table: seven data rows; its seven-surfaces caption remains verbatim in supplied Chinese.
- p11 package table: fourteen packages plus total row; all file/line counts retained, including 670 and 159,148. Exclusions and 48.6% / 1.4% caption remain.
- p20 event table: eighteen grouped rows represent all 29 events; the two turns / four writes / 5 ms caveat remains.
- p21 JSONL table: eight data rows; parent IDs, write events and caption remain.
- Existing explanatory captions, source lists and blockquotes remain in the Markdown. No callout content was rewritten.

## Precise mechanical repairs
- Removed 97 `****` export-artifact boundaries outside fenced code; converted 90 balanced bold spans to explicit strong tags to avoid CommonMark CJK punctuation ambiguities. No text removed.
- Canonicalized only the two fence-language labels: TypeScript→ts and JSON→json. Body text remains exact.
- Figure image references replaced by BookFigure IDs in the same positions; source filename URLs percent-decoded for lookup, copies use hyphens for spaces.
- Source chapter-title wrapper replaced by section kickers and frontmatter; all three actual reading headings and lower headings retained. Heading splitting is fence-aware.
- A safeguard escapes bare pipes only inside inline code in Markdown table cells; this chapter requires no such pipe repair.
- Added the verified p20 caption `FIG. 1.6 · 一个回答完成的提示，逐事件查看 · 原书第 20 页` immediately before its table.

## Explicit unresolved/source discrepancies
1. The supplied prose says `lama.cpp`; PDF p7 and FIG.1.1 say `llama.cpp`. The prose is preserved as supplied, and the native figure preserves the original spelling. A visible note in FIG.1.1 discloses the discrepancy. No speculative code correction.
2. FIG.1.2: 77,340 vs 23,581 do not have proportional displayed bar lengths, and the original does not disclose a transformation. Exact numeric labels/table are authoritative; native positions and lengths transcribe the original visual with an explicit caveat, without computing a replacement scale. The original is retained for comparison.
3. The JSON example intentionally contains `"usage": { ... }` and is an abbreviated excerpt, not executable JSON. Its existing explanation remains; no fabricated usage values are introduced.
4. This chapter's normalized text does not re-verify the book's source-code claims against an external repository; it faithfully preserves the supplied snapshot at commit 28dcce2.

## Immutable attachment hashes
| Source file | SHA-256 |
| --- | --- |
| image.png | dff0597db1dc27ac61f186037c5c817a949777840e230915a7d6c1b5d785f3a4 |
| image 1.png | 37cb35f250d06e10186b75442a078c4a6ee2888a2103d4eed919b42f7ed6c2e4 |
| image 3.png | 73180a99abf5ef86803f758a6045df6c7f6bf8cf674d84192f069982faad572f |
| image 2.png | 2c688f67174e6593e3beefae5ed64f6ccab575aae25f92abd9a038830bb1d72e |
| image 4.png | ef9dd352ee91c57d6d578e63a6ac03162eca25a4ef79f229bbbf03f9ab9c3065 |

## Static compiler check
All three generated pages were rendered through VitePress createMarkdownRenderer and compiled with @vue/compiler-sfc compileTemplate without errors. This is an isolated template check, not a global site build or browser inspection.

## Integration boundary
No shared theme/config/style changes, browser work, global build, commit, remote push or publishing were performed by this chapter importer. Parent integration owns final production rendering and accessibility checks. The native sequence renderer must honor explicit points, shape:label, arrow:false, dashed, dash:dotted, and multiline labels.
