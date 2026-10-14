# Pi 技术文库

中文启动说明：[README.zh-CN.md](README.zh-CN.md)

Local-first VitePress reading editions of Pi 1.0.4 and Pi Durable 1.0.3. Both books are complete in this combined project.

## Run on Windows, macOS or Linux

Install a supported Node.js LTS release (Node 20.19+; Node 22/24 recommended). Open a terminal in the extracted folder containing `package.json`:

```sh
npm ci --ignore-scripts
npm run build
npm run preview
```

Open http://localhost:4173 on the same computer. For development:

```sh
npm run dev
```

Use the local address printed by VitePress (normally http://localhost:5173). The ordinary install, build, development and preview commands use Node.js only. Python, Pillow, the original PDF and the optional original-image packs are not needed to run either book. No global Vite installation is required.

## Included content

- Pi 1.04: 36 reading/reference sections plus opening matter; 62 interactive diagrams; 101 adjustable tables; 60 code blocks
- Pi Durable: 53 reading/reference sections plus full opening matter; 67 source figures; 94 adjustable text tables; 64 code blocks
- Two-book landing page, collapsible chapter groups, previous/next links, narrow-screen menu
- Adjustable table widths with keyboard resizing, reset and long-table expansion; settings stay in the local browser
- Semantic warning, takeaway, rule, source and explanatory callouts
- 129 lossless original WebPs, with source comparison for native figures
- Locally bundled Latin fonts, with system Chinese-font fallbacks

Dense figures scroll within their own pane rather than shrink labels below readable size. Native Pi Durable SVG geometry/text is source-derived; semantic hotspots expose descriptions through click and keyboard interaction. Where source hatch textures require reconstruction, the figure report records that limitation. These diagrams explain the book; they do not execute code or display live system state.

## Source fidelity and version boundaries

The supplied Markdown is authoritative for the Chinese prose and code; the PDFs verify figure geometry, captions and callout styles. All original input files remain unchanged. Pi Durable corresponds to 1.0.3 at commit `5b6c792` (2026-10-05); its APIs are experimental. No examples have been silently modernized.

Formatting corrections and PDF-backed recovered callout labels are recorded in `sources/reports/durable-import.json` and `durable-callouts.json`. Source audits compare complete normalized prose, every fenced-code payload, table cells and original image pixels. An original caption or technical ambiguity is preserved rather than guessed.

## Authoring and optional source audits

The main project includes every generated page, runtime WebP, figure catalog, source Markdown, audit report, script and locked dependency definition. Optional original-source archives restore source PNGs for full authoring audits. Merge their `sources/` folders into this project root; do not create a nested project folder.

Node-only runtime asset audit: `npm run check:assets`.

Optional full source checks (Python 3): `npm run check:book` and `npm run check:durable`. These require the matching original-image packs. Re-importing pages: `npm run import:book` or `npm run import:durable`; Pillow is needed for image encoding. Pi Durable vector regeneration additionally requires the original PDF and PyMuPDF, fontTools, NumPy and Pillow (plus Inkscape for optional visual QA). Set `PI_DURABLE_PDF` to the source PDF path, regenerate the two figure catalogs, then run `node scripts/compact_durable_glyphs.mjs` to pool identical outlines. Ordinary readers do not need these authoring tools.

The original uploaded PDFs and ZIPs are excluded from the runnable archive. Native-vector extraction and optional-source delivery are documented in the figure reports. A small Python server remains solely for internal cloud-browser QA; it is not part of the normal startup workflow.

## Original manual sources

Both manuals were publicly released as PDFs by their authors; this repository hosts the Chinese reading editions only:

- **Pi Technical Manual** — <https://x.com/calebfahlgren/status/2107199330926899652>
- **Pi Durable Technical Manual** — <https://x.com/lucataco/status/2107230736403013653>

The original PDFs are not distributed with this repository. All rights to the original manuals remain with their authors; these editions are provided for study purposes.

## Boundaries

The site deploys to GitHub Pages at https://caizongyuan.github.io/pi-lessons/ via GitHub Actions. Book content and source commands are displayed, never executed. See `PROJECT.md` for scope and `QA.md` for verification evidence and limitations.

## License

The build scripts, site code and reading-edition layout in this repository are released under the [MIT License](LICENSE). The original manuals remain the property of their authors.
