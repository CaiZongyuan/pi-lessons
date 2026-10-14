> Current delivery: both books are complete. The earlier sections below are historical; see “Pi Durable continuation · 2026-10-13” for the latest verification.

# Full-book acceptance evidence

## Scope and source preservation
- 36 reading sections: all seven chapters plus nine reference sections; opening matter is also fully included.
- 101 tables, 60 fenced code blocks, 62 supplied figures.
- Source Markdown and PNGs are immutable; hashes in `sources/full-manifest.json`.
- Per-chapter importers verify normalized source text, code interiors, table rows and figure mappings. Detailed source discrepancies and permitted caption relocations are recorded under `sources/reports/`.
- Substantive source typos/omissions remain visible with explicit PDF-backed notes rather than silently changed examples.
- Original PDF is not distributed with the website or source archive.

## Figure and caption verification
- All 62 figures are native interactive HTML/Vue/SVG reconstructions; no image-only fallback remains.
- All originals remain available for comparison and full-size viewing.
- Opening timeline preserves the 29-event axis, original write positions, first 3 metadata records and agent_settled endpoint. No invented parentId edges.
- Fig 1.2 transcribes original drawn bar lengths and exact labels; an explicit caveat states that the original does not disclose a uniform proportional scale.
- Dense directory, MCP/Codemode sequence and byte-protocol figures preserve hierarchy, lifelines, return/progress distinctions and byte-proportional positions.
- PDF-verified misplaced Fig 2.5/5.6 captions and SDK callout association were corrected without losing wording.
- Exact repeated captions are displayed once;41 new figures link to their external source caption.
-63 tables have explicit aria-describedby associations to existing captions. No duplicate IDs, unresolved ARIA references, unnamed interactive nodes or missing figures were found.

## Tables and callouts
- All 101 tables have adjustable columns, keyboard controls and reset.
- Pointer drag verified 230→320 px; keyboard ArrowRight verified 210→230 px; Home minimum 120 px; reset 210 px.
- Width persistence verified after reload. Preferences stay in browser-local storage.
- Largest 59-row table initially shows 12 rows and expands to 59; desktop and phone-width checks passed.
- Warning, DOC≠CODE, takeaway, rule-of-thumb and quiet source-footer treatments are distinguished using PDF evidence.

## Build and actual browser QA
- Production VitePress build: PASS. `npm run check:book`: PASS.
- All 36 reading routes inspected in dot cloud browser at 1165 px: zero missing figures, no page-level overflow, no clipped node labels.
- All 40 routes (reading pages, opening matter, indexes and Pi Durable entry) checked in a 390×844 browser iframe: no page-level overflow. This is responsive-layout testing, not physical touch-device emulation.
- Sidebar/group collapse, phone menu, chapter navigation and book switching: PASS.
- Native figure keyboard selection and accessible names: PASS.
- Existing chapter 4 prompt/branch/cut/patch controls retained and tested.
- Application console errors: none observed; unrelated browser-extension metadata warnings were excluded.
- Build staging installs assets before HTML and preserves the running preview directory so failed builds do not replace the last working version.

## Lossless WebP
-62/62 public originals/comparison images converted to WebP; native diagrams remain HTML/SVG.
-20,626,921→9,080,278 bytes:55.98% smaller,11,546,643 bytes saved.
- Independent review confirmed exact dimensions and every decoded RGBA pixel against immutable source PNG.
-62 built image references resolve; no public or dist PNG remains. SourcePNG files are unchanged.
- `scripts/optimize_assets.py` is idempotent and needs no Pillow when no PNG conversion is pending.

## Delivery boundary
Preview: http://localhost:4173/ on dot cloud computer only. No public publication, remote configuration or push. Pi Durable remains an empty entry. Source ZIP excludes dependencies, original full PDF, authentication state and unrelated files. Latin font families match the PDF; CJK uses system fallbacks.

# Pi Durable continuation · 2026-10-13

## Source coverage and preservation

- 12 supplied Markdown files: complete opening matter, 46 chapter sections and 7 reference sections. No source files were rewritten.
- All 64 fenced-code payloads match the supplied manuscript byte-for-byte.
- All 94 Markdown tables and 700 data rows retain their exact cells;11 inline-code union-pipe rows were escaped for correct rendering.
- All 67 source images retain exact decoded RGBA pixels in lossless WebP.
- All 66 native figures retain PDF geometry/labels/scales and expose selectable source transcripts. The composite cover remains a zoomable original, explicitly explained.
- 405 exact pooled Type 3 glyph outlines serve 33,632 native glyph uses; no raster tracing or invented chart scales. Original diagonal hatch textures alone are reconstructed as SVG line fills.
- 1,764 named keyboard-operable figure hotspots;67 figure descriptions;45 exact adjacent source-caption/table associations.
- 41 takeaways, 12 warning callouts, 2 rule callouts and 37 source blocks retain source semantics. Four missing callout labels restored with PDF evidence.
- Formatting log covers 139 redundant bold-delimiter joins,387 strong spans normalized for Chinese punctuation boundaries,11 table pipes,4 recovered labels and removal of empty quote tails after restored callouts. No technical values or code modernized.
- The source benchmark disagreement in figure 9.8 remains explicit: graphic 0.45 μs, adjacent prose 0.44 μs.

## Regression and build

- Existing Pi 1.04 reading pages, public figures and original figure catalogs remain byte-unchanged versus baseline c0582fe; its full acceptance suite still passes (37 pages,62 figures,101 tables,60 code blocks).
- `npm run build`, `npm run check:book`, `npm run check:durable` and `npm run check:assets` pass in the complete authoring workspace.
- Build verifies all 129 public WebP hashes through Node.js. Python is no longer called by the normal build.
- Default dev/preview bind 127.0.0.1 for local-only use, avoiding wildcard-interface enumeration issues in restricted environments.
- Clean project ZIP extraction passes `npm ci --ignore-scripts`, build, preview HTTP 200 and dev HTTP 200 with PATH containing only Node, npm and the system shell, without Python. A writable temporary npm cache was used because this executor has no default home cache directory.
- Vite reports a nonfatal large-chunk advisory for the source-faithful native figure catalogs. Local runtime and all route tests pass.

## Actual browser evidence

- dot cloud Chromium, 56 routes × 2 widths = 112 final route checks after the last formatting corrections. Desktop content width 1165 CSS px; narrow test is a 390 px iframe with 375 px content width after scrollbar.
- No horizontal document overflow, missing figure placeholders or irregular table column counts at either width.
- Desktop sidebar toggle and phone-width chapter menu pass. Figure click, arrow keys and mobile-frame Enter selection pass. All source text is exposed in selectable details.
- Table arrow-key resize 158→178 px, persistence after reload, reset, long-table expand/collapse and wide-table expand/restore pass.
- No site console errors. Browser-extension metadata errors were separately identified and excluded.
- Temporary browser tabs and both preview servers were stopped/closed after QA. No persistent preview or public deployment remains.

## Limits and delivery

No physical phone or real Windows machine was used. Windows portability is supported by the Node-only cross-platform command path; responsive checks used a real Chromium document at narrow width, not mobile hardware. Book examples were displayed and compared, never executed. Original PDFs/nested ZIPs, dependencies, built output and `.git` are excluded from the runnable archive. Optional PNG packs are required only for full source-image authoring audits, never for normal install/build/dev/preview.
