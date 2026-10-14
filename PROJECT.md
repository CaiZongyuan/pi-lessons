# Pi documentation prototype

## Contract
Convert only the supplied Chinese chapter 4 into a local VitePress documentation library. The supplied Markdown is the content authority; Pi-Technical-Manual.pdf is the visual and figure-accuracy reference. Preserve every paragraph, code sample and source citation. Home offers Pi 1.04 and Pi Durable, with an extensible book registry. Pi Durable has no invented chapter content. Sidebar groups collapse; navigation works on mobile.

## Boundaries
New Git repository only. No remote, publishing, user computer access or external data sharing. The source ZIP is retained unchanged as extracted files. The original PDF is 221 pages; chapter 4 is printed pages 74–97. Reference https://github.com/ythx-101/live-panel-skill is read-only inspiration, never executed. Fixed, inspectable diagram layouts and illustrative-only interaction, no fabricated live measurements.

## Design evidence
Original PDF: ivory paper, navy ink, hairline warm-gray dividers, blue diagram blocks, gold/green highlights, uppercase monospaced figure labels. Fonts embedded in PDF include Manrope, Source Sans 3, Source Serif 4 and JetBrains Mono. Use matching locally bundled Latin families with available CJK fallbacks.

## Deliverables and proof
1. Complete chapter split into four faithful reading pages: content comparison and unchanged fenced code.
2. Native accessible figures with original source figures available for comparison; diagram mapping records all 12.
3. Landing library, book index, collapsible chapter navigation and mobile menu: browser checks.
4. Reproducible VitePress build and local preview; no public URL implied.

## Recovery and gates
Sources remain unchanged; generated pages can be rebuilt by scripts/import_chapter.py. Replan if diagram semantics cannot be resolved; preserve original figure rather than inventing. No publish or remote push without new user request. Validation evidence is recorded in QA.md at completion.

## Status
Complete. Source/code coverage, production build, independent semantic review, desktop navigation/interactions and phone-width browser QA passed. See QA.md. Local preview is open in the dot cloud browser. Await user trial feedback; no further chapter import or publishing is authorized.

## Accepted conversion decisions
- Four chapter reading pages preserve the source hierarchy; original printed page references are retained, without inventing links to unavailable chapters.
- Nine numbered original figures and three unnumbered user explanations remain distinct; all have source-image comparison.
- The six JSON key `**` markers are export artifacts (original p 77 corroborates); remove them. Two unescaped table pipes are escaped for correct cell boundaries. No technical values are changed.
- Some source snippets are intentionally abbreviated or quote-damaged, and retain the source's disclaimers rather than being passed off as executable examples.
- The original PDF uses Latin fonts; locally bundle those families and use CJK system fallbacks rather than claim a nonexistent Chinese font match.

# Full-book extension · 2026-10-08

## Updated user contract
The approved prototype now expands in this same local repository to the remaining supplied Pi 1.04 book material. Preserve PDF-derived UI and chapter 4 content. Import supplied chapters 1–3 and 5–7, opening matter and reference. Review each figure/table caption against the original PDF, preserve exact source semantics and explicitly flag unresolved gaps. Differentiate original callout styles (especially practical takeaways, sources and warnings). Add reversible, keyboard-operable adjustable table widths and expansion for long tables.

## Invariants and boundaries
Immutable source ZIP extracts under sources/full; original chapter 4 source remains sources/chapter. No invented Pi Durable material. No public deployment, remote configuration or push. Parent handles separate GitHub login/inspection only. Local commits are allowed. Preview must stay usable; retain previous production output until a successful build. Unclear captions are marked, not invented.

## Milestones and ownership
1. Source inventory and PDF page mapping: central + disjoint chapter workers. Evidence: exact filenames, counts, immutable hashes and page ranges.
2. Faithful reading pages and native diagrams: workers own ch 02/ch 03, ch 05, ch 06/ch 07; central owns opening/reference/shared components; ch 01 assigned as capacity permits. Evidence: normalized full-text/code coverage and figure graph checks.
3. Shared reading controls: central owns figure renderer, semantic callouts, adjustable/expandable tables, navigation. Evidence: accessible labels, keyboard resizing/reset, contained overflow and visible captions.
4. Integration gate: production build, source coverage, independent audit and actual desktop/phone-width browser checks. Fix semantic/interaction failures before local commit and updated source archive delivery.

## Replan / stop conditions
Escalate any source ambiguity that affects technical meaning. Preserve original figure as a comparison fallback if native redraw cannot be faithful. Do not claim missing content filled or GitHub publishing complete. New security/login requirements stay with parent. Reopen source/coverage gate after any late attachment or correction.

## Current status
All seven initial extension ZIPs are readable and extracted. Chapter 1 arrived separately and is being incorporated. Previous trial remains running at http://localhost:4173/. Work is parallel and not yet ready for final delivery.

## Completion update · 2026-10-08
Full requested book import is complete:36 sections plus opening matter,101 tables,60 code blocks,62 native figures. All supplied sources are unchanged. Caption/callout corrections and source ambiguities are recorded with PDF evidence. Actual desktop/phone-width QA and independent source/asset/accessibility audits passed. Latest requested public bitmap conversion is complete:62 lossless WebPs with exact decoded-pixel equivalence and 55.98% size reduction. Preview remains local and running. Await user review; no GitHub publication or additional content is authorized.

# Pi Durable continuation · 2026-10-13

## Contract and boundaries
Add the supplied Pi Durable 1.0.3 manuscript and PDF using the established reading design. Preserve all original prose, code, source references and diagrams. Correct obvious formatting/export errors with a reversible log. Existing Pi 1.04 reading pages and assets must stay byte-identical. Local authoring/commits/package only: no login, remote, push, publication or deployment.

## Deliverables and evidence
- 53 Pi Durable reading/reference sections plus complete front matter; immutable input hashes, normalized full-text comparison and exact fenced-code payload comparison.
- All 67 source figures with native interactive representations where faithful, plus exact-pixel lossless original WebP comparison; all 94 text tables remain adjustable.
- Two-book navigation and locally bundled reading design; no mandatory Python in npm install/build/dev/preview.
- Fresh build, independent content/semantic audit, desktop and mobile browser verification, and clean archive extraction/install/build/dev/preview.

## Recovery and status
Original upload ZIP/PDF remain outside runnable package. Immutable extracted source content is retained; original PNGs and nested ZIPs can be delivered separately. Replan if a figure cannot be reproduced faithfully: retain clearly labeled original rather than inventing technical meaning. Prior delivered ZIP was outside this turn's Library scope, so local c0582fe is the verified baseline; Node-only build fix is restored explicitly. Integration in progress.

## Completion · 2026-10-13
The Pi Durable continuation is complete:53 reading/reference sections plus opening matter,64 exact code blocks,94 adjustable text tables,66 native interactive figures plus one preserved cover,67 lossless originals and source-backed callout/caption treatment. Both books build with Node only. Final112-route desktop/narrow browser checks and clean-extraction startup tests pass. Pi1.04 content/assets remain unchanged. QA previews are stopped. No remote, push, login or publication occurred.
