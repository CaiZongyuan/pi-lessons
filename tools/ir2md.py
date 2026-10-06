#!/usr/bin/env python
"""
Convert a translated IR part into Markdown.

Pi Durable's translation source of truth is the IR JSON that `extract.py` +
`normalize.py` produce, not Markdown. Rather than hand-convert it (which would create a
second copy to keep in sync), this adapter projects the IR into Markdown so that both
books reach Starlight through one shape.

Conversion rules, mirroring the existing translation-aware HTML renderer:

* prefer the Chinese (`zh` / `zh_caption`), fall back to the English source
* code blocks are copied verbatim, never translated
* a figure caption that arrives twice — truncated as `figure.caption`, complete as the
  following `small` node — is emitted once
* the translation sits under the English so a reader can compare, and so a partial
  translation still renders

Output shape per node type:

    part-title     -> frontmatter `part` + nothing in the body
    chapter-title  -> `## <number> <title>`  (number kept, Chinese preferred)
    lede           -> italic standfirst
    h2             -> `### <title>`
    p              -> paragraph, English then Chinese
    li             -> bullet item
    code           -> fenced block, language guessed
    figure         -> image + caption
    small          -> `:::note` blockquote, unless it is a duplicate caption

Usage:
    python tools/ir2md.py books/pi-durable/ir --out books/pi-durable/md/parts
    python tools/ir2md.py books/pi-durable/ir --out ... --part 01-model
    python tools/ir2md.py books/pi-durable/ir --out ... --bilingual
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LANG_HINTS = [
    (re.compile(r"^\s*[{[]"), "json"),
    (re.compile(r"\b(const|await|async|function|return|export|import)\b"), "ts"),
    (re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE)\b", re.I), "sql"),
]


def guess_lang(lines) -> str:
    blob = "\n".join(lines)
    for rx, lang in LANG_HINTS:
        if rx.search(blob):
            return lang
    return ""


def zh_of(node):
    """Prefer the translation; fall back to the English source."""
    return node.get("zh") or node.get("text", "")


def norm(s: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", s.lower())


def caption_covered(caption: str, note: str) -> bool:
    """True when `note` already contains the figure caption.

    The extractor emits the same caption twice: truncated as the figure's own caption,
    then complete as the following small-print node. Neither is a prefix of the other
    (truncation is mid-sentence and the two translations may word the boundary
    differently), so the shorter string is looked for anywhere inside the longer one.
    """
    a, b = norm(caption), norm(note)
    if len(a) < 10 or len(b) < 10:
        return False
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    if short in long:
        return True
    lo, hi, best = 0, len(short), 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if any(short[i:i + mid] in long for i in range(len(short) - mid + 1)):
            best, lo = mid, mid
        else:
            hi = mid - 1
    return best / len(short) >= 0.6


def bilingual(en: str, zh: str, out: list[str]):
    """Emit the English source then the translation, when they differ."""
    en = (en or "").strip()
    zh = (zh or "").strip()
    if not zh:
        if en:
            out.append(en)
            out.append("")
        return
    if not en or norm(en) == norm(zh):
        out.append(f"**{zh}**" if zh else "")
        out.append("")
        return
    out.append(en)
    out.append("")
    out.append(zh)
    out.append("")


def convert(ir_path: Path, bilingual_mode: bool, asset_prefix: str = "") -> tuple[str, dict]:
    """Return (markdown, stats) for one IR file."""
    data = json.loads(ir_path.read_text(encoding="utf-8"))
    nodes = data["nodes"]
    out: list[str] = []
    stats = {}

    def bump(key):
        stats[key] = stats.get(key, 0) + 1

    # drop the part-level lede/h2 that repeats the part subtitle (renderer skips it)
    start = 0
    if nodes and nodes[0]["type"] == "part-title":
        start = 1
        if len(nodes) > 1 and nodes[1]["type"] == "h2":
            start = 2

    chapter_no = 0
    skip_caption_until = -1
    last_was_figure = False
    prev_caption = ""

    for n in nodes[start:]:
        t = n["type"]

        if t == "part-title":
            bump("part-title")
            continue

        if t == "chapter-title":
            chapter_no += 1
            raw = n.get("zh") or n.get("text", "")
            m = re.match(r"([\d.R]+)\s+(.*)", raw)
            num, title = (m.group(1), m.group(2)) if m else ("", raw)
            anchor = num or str(chapter_no)
            out.append(f'<a id="sec-{anchor.replace(".", "-")}"></a>')
            out.append("")
            out.append(f"## {num} {title}".rstrip())
            out.append("")
            bump("chapter-title")
            last_was_figure = False
            continue

        if t == "lede":
            text = zh_of(n)
            if text:
                # A class, not a blockquote: the source sets the standfirst as italic
                # prose with no rule down the side, and a `>` renders as a quote with one.
                out.append(f'<p class="lede">{text}</p>')
            bump("lede")
            continue

        if t == "h2":
            out.append(f"### {zh_of(n)}")
            out.append("")
            bump("h2")
            last_was_figure = False
            continue

        if t == "p":
            en, zh = n.get("text", ""), n.get("zh", "")
            bilingual(en, zh, out) if bilingual_mode else (
                out.extend([zh or en, ""]))
            bump("p")
            last_was_figure = False
            continue

        if t == "li":
            out.append(f"- {zh_of(n)}")
            bump("li")
            last_was_figure = False
            continue

        if t == "code":
            lines = n.get("lines", [])
            lang = guess_lang(lines)
            out.append(f"```{lang}")
            out.extend(lines)
            out.append("```")
            out.append("")
            bump("code")
            last_was_figure = False
            continue

        if t == "figure":
            cap = n.get("zh_caption") or n.get("caption", "")
            out.append(f'<img src="{asset_prefix}{n["file"].split("/")[-1]}" '
                       f'alt="{n.get("title", "")}" loading="lazy">')
            out.append("")
            if cap:
                out.append(f"*{cap}*")
                out.append("")
            prev_caption = cap
            bump("figure")
            last_was_figure = True
            continue

        if t == "small":
            note = zh_of(n)
            if last_was_figure and prev_caption and caption_covered(prev_caption, note):
                bump("caption-deduped")
                last_was_figure = False
                continue
            if note:
                # Aside: a tinted panel in the source, not a quotation.
                out.append(f'<aside class="note">{note}</aside>')
            bump("small")
            last_was_figure = False
            continue

        bump("unknown:" + t)

    # collapse runs of blank lines
    md = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"
    return md, stats


def deploy_base() -> str:
    """Read the deploy base from docs/astro.config.mjs.

    Figure paths must carry the base: the site is served from a sub-path, and Astro does
    not rewrite absolute URLs inside Markdown. Reading it here rather than taking it from
    the caller means `ir2md.py` produces correct output whether it is run by hand, by
    `docs.py sync --ir-to-md`, or by CI — an earlier version relied on the caller passing
    `--asset-prefix` and silently emitted base-less paths whenever nobody did.
    """
    cfg = ROOT / "docs" / "astro.config.mjs"
    if not cfg.exists():
        return ""
    text = cfg.read_text(encoding="utf-8")
    const = re.search(r"""const\s+BASE\s*=\s*['"]([^'"]+)['"]""", text)
    if const:
        return const.group(1).rstrip("/")
    m = re.search(r"""base:\s*['"]([^'"]+)['"]""", text)
    return m.group(1).rstrip("/") if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ir_dir", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--part", help="only convert this slug")
    ap.add_argument("--bilingual", action="store_true",
                    help="keep the English source above the translation")
    ap.add_argument("--asset-prefix", default=None,
                    help="override the figure src prefix; default derives it from the "
                         "deploy base in docs/astro.config.mjs")
    a = ap.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    total = 0
    for ir in sorted(a.ir_dir.glob("*.json")):
        if ir.name.endswith(".meta.json"):
            continue
        slug = ir.stem
        if a.part and slug != a.part:
            continue
        prefix = a.asset_prefix
        if prefix is None:
            prefix = f"{deploy_base()}/_assets/{a.ir_dir.parent.name}/{slug}/"
        md, stats = convert(ir, a.bilingual, prefix)
        (a.out / f"{slug}.md").write_text(md, encoding="utf-8")
        total += 1
        print(f"{slug:18s} {len(md)//1024:4d} KB  "
              + " ".join(f"{k}={v}" for k, v in sorted(stats.items())))
    print(f"\nconverted {total} part(s) -> {a.out}")


if __name__ == "__main__":
    main()