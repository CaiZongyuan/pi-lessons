"""
Extract structured content + figure crops from a technical-manual PDF.

Design notes
------------
Both manuals in this repo were produced by the same "TechManual engine" (Paged.js +
Chrome), which shapes everything we can rely on:

* Every font is a Type3 subset, so font *names* are useless but text extracts cleanly.
* Bookmark page numbers are unreliable; structure is recovered from *geometry* —
  font size, colour and position.
* There is not a single raster image: all figures are vector art, so we crop the figure
  region at high DPI instead of extracting an embedded image.
* Running heads, folios and the table of contents are dropped.

The one genuinely fragile part is figure captions. They are set in letter-spaced caps,
so PyMuPDF returns them with *real spaces between every glyph*:

    "F I G . 1 . 4F R O M E N T E R T O T H E F I R S T..."

A naive `FIG\\.\\s*(\\d+\\.\\d+)` never matches that. `decap()` undoes the tracking before
matching, which is what makes the two books' different figure styles both work.

Usage:
    python extract.py --pdf <path> --config <book.json> --part <slug> --out <dir>
"""

import argparse
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

# ---------------------------------------------------------------- palette
INK = 0x161D27
MUTED = 0x5F6772
FAINT = 0x878E97
RULE = 0xDDE4EE

BODY_X = 57.6

DROP_EXACT = {"Pi Durable", "Pi", "PI DURABLE / TECHNICAL MANUAL",
              "PI / TECHNICAL MANUAL"}


def untrack_chars(chars) -> str:
    """Rebuild a tracked-caps run from character boxes.

    PyMuPDF reports tracked caps as 'F I G . 1 . 4', but the geometry says which spaces
    are real. Each space character carries its own advance width, and the two kinds are
    wildly different: a *tracking* space is a hairline (~1.3pt) while a genuine word space
    is a full glyph advance (~3.8pt, the same width as the letters around it). That is the
    only reliable discriminator — token length cannot tell a tracked 'FROM' from a real
    'MEASURED', and inter-glyph gaps are identical in both.
    """
    if not chars:
        return ""
    widths = [c["bbox"][2] - c["bbox"][0] for c in chars]
    glyph_adv = max((w for w in widths if w > 0), default=1.0)
    space_is_word = glyph_adv * 0.6      # a word space is most of a glyph advance

    out: list[str] = []
    for ch, w in zip(chars, widths):
        if ch["c"] == " " and w < space_is_word:
            continue                      # tracking artefact, not a word boundary
        out.append(ch["c"])
    s = "".join(out)
    s = re.sub(r"\s+([.,;:!?])", r"\1", s)      # '1 . 4' -> '1.4', 'FIG . 1' -> 'FIG. 1'
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def span_line_text(line) -> str:
    """Line text with tracking removed; falls back to raw text without char boxes."""
    parts = []
    for s in line["spans"]:
        if "chars" in s:
            parts.append(untrack_chars(s["chars"]))
        else:
            parts.append(s.get("text", ""))
    return " ".join(p for p in parts if p).strip()


def block_decap(block) -> str:
    parts = [t for t in (span_line_text(l) for l in block["lines"]) if t]
    return " ".join(parts).strip()


# ---------------------------------------------------------------- text helpers
def is_furniture(text: str) -> bool:
    t = text.strip()
    if t in DROP_EXACT:
        return True
    if re.fullmatch(r"\d{1,3}", t):          # bare folio
        return True
    return False


def block_text(block) -> str:
    # Lines must be joined with a separator: "...every visible" + "step a stored"
    # would otherwise fuse into "visiblestep". Spans *within* a line are concatenated
    # directly, because that is how one word splits across font runs.
    return "\n".join(line_text(l) for l in block["lines"])


def span_text(span) -> str:
    """Span text for either dict (has .text) or rawdict (only .chars)."""
    if "text" in span:
        return span["text"]
    return "".join(c["c"] for c in span.get("chars", []))


def line_text(line) -> str:
    return "".join(span_text(s) for s in line["spans"])


def max_size(block) -> float:
    return max((round(s["size"], 1) for l in block["lines"] for s in l["spans"]), default=0.0)


def dominant_color(block):
    counts = {}
    for l in block["lines"]:
        for s in l["spans"]:
            t = span_text(s)
            if t.strip():
                counts[s["color"]] = counts.get(s["color"], 0) + len(t)
    return max(counts.items(), key=lambda kv: kv[1])[0] if counts else INK


# ---------------------------------------------------------------- roles
CODE_SIZES_MAX = 8.0


def is_codeish(block) -> bool:
    """Code lives in tinted panels: small type and code punctuation density."""
    if max_size(block) > CODE_SIZES_MAX:
        return False
    txt = block_text(block)
    if not txt.strip():
        return False
    signals = 0
    if re.search(r"[;{}]\s*$", txt.strip()):
        signals += 1
    if re.search(r"[=:]\s", txt):
        signals += 1
    if re.search(r"\b(const|await|async|function|return|import|export|type|interface|new)\b", txt):
        signals += 1
    if re.search(r'[",;{}()\[\]]', txt):
        signals += 1
    return signals >= 2


def classify(size: float, color: int) -> str:
    if size >= 30:
        return "part-title"
    if size >= 19:
        return "chapter-title"
    if 10.2 <= size <= 10.6:
        return "h3"        # standfirst / lede
    if 11.0 <= size <= 13.0:
        return "h2"
    if size <= 8.7:
        return "small"
    if color in (MUTED, FAINT):
        return "muted"
    return "p"


# ---------------------------------------------------------------- figures
# The two books set figure captions slightly differently: 'FIG. 1.4' vs 'FIG . 1.2'.
# Tolerate optional space before the dot, and a number that may be a bare integer.
FIG_RE = re.compile(r"^\s*FIG\s*\.\s*(\d+(?:\.\d+)?)\s*(.*)$", re.S)


def figure_blocks(page):
    out = []
    for b in page.get_text("rawdict")["blocks"]:
        if b["type"] != 0:
            continue
        m = FIG_RE.match(block_decap(b))
        if m:
            out.append((b, m.group(1), m.group(2)))
    return out


def art_extent(page, band_top):
    """Bounds of the figure's outer panel frame.

    Every figure sits inside a ruled panel whose top border sits a couple of points below
    the caption. That frame is by far the widest drawing anchored at the top of the band,
    so we pick it directly; footer rules and paragraph rules never compete.
    """
    best = None
    for d in page.get_drawings():
        r = d["rect"]
        if r.width < 80 or r.height < 30 or r.width > 560:
            continue
        if abs(r.y0 - band_top) > 8:
            continue
        area = r.width * r.height
        if best is None or area > best[0]:
            best = (area, r)
    return (best[1].x0, best[1].y1, best[1].x1) if best else (None, None, None)


def find_caption(raw, art_bottom):
    for b in sorted(raw["blocks"], key=lambda x: x["bbox"][1]):
        if b["type"] != 0 or b["bbox"][1] < art_bottom - 2:
            continue
        if block_text(b).strip():
            return b
    return None


def figure_box(page, band_top, band_bottom):
    x0, x1 = 1e9, -1e9
    for d in page.get_drawings():
        r = d["rect"]
        if r.height <= 0 and r.width <= 0:
            continue
        cy = (r.y0 + r.y1) / 2
        if band_top <= cy <= band_bottom and r.width < 600:
            x0, x1 = min(x0, r.x0), max(x1, r.x1)
    return (max(50.0, x0 - 3.0), min(566.0, x1 + 3.0)) if x0 < x1 else None


def crop_figure(page, cap_bbox, bottom_y, out_path: Path, dpi, box=None):
    pad_top, pad_bottom = 4.0, 2.0
    x0, x1 = box if box else (BODY_X, 549.6)
    y0 = cap_bbox[1] - pad_top
    y1 = bottom_y + pad_bottom
    if y1 - y0 < 30:
        y1 = min(page.rect.height - 45, y0 + 560)
    page.get_pixmap(dpi=dpi, clip=fitz.Rect(x0, y0, x1, y1)).save(str(out_path))
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


# ---------------------------------------------------------------- extraction
def extract(pdf: Path, first: int, last: int, out_dir: Path, dpi: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    figs_dir = out_dir / "figures"
    figs_dir.mkdir(exist_ok=True)

    doc = fitz.open(str(pdf))
    pages, manifest = [], []

    for pno in range(first - 1, last):
        page = doc[pno]
        raw = page.get_text("rawdict")

        figs = figure_blocks(page)
        bands = []
        for cap, num, title in figs:
            band_top = cap["bbox"][1] - 9
            fx0, fy1, fx1 = art_extent(page, band_top)
            if fy1 is None:
                fy1 = cap["bbox"][3] + 300
            cap_blk = find_caption(raw, fy1 + 2)
            cap_y = cap_blk["bbox"][1] if cap_blk is not None else fy1 + 26
            cap_txt = block_decap(cap_blk) if cap_blk is not None else ""

            box = None
            if fx0 is not None:
                box = (max(50.0, fx0 - 3.0), min(566.0, fx1 + 3.0))
            fname = f"fig-{num}.png"
            meta = crop_figure(page, cap["bbox"], fy1, figs_dir / fname, dpi, box=box)
            manifest.append({"number": num, "title": title, "page": pno + 1,
                             "file": f"figures/{fname}", **meta})
            bands.append((band_top, cap_y - 2, num, cap_txt))

        def in_figure(y):
            return any(a <= y <= b for a, b, _, _ in bands)

        blocks = []
        for b in raw["blocks"]:
            if b["type"] != 0:
                continue
            txt = block_text(b).strip()
            if not txt or is_furniture(txt) or in_figure(b["bbox"][1]):
                continue
            size = max_size(b)
            color = dominant_color(b)
            blocks.append({
                "role": "code" if is_codeish(b) else classify(size, color),
                "size": size, "color": f"#{color:06x}",
                "bbox": [round(v, 1) for v in b["bbox"]],
                "text": txt,
                "lines": [{"text": line_text(l),
                           "spans": [{"t": span_text(s), "c": f"#{s['color']:06x}"}
                                     for s in l["spans"] if span_text(s).strip()]}
                          for l in b["lines"] if line_text(l).strip()],
            })

        pages.append({"page": pno + 1, "blocks": blocks,
                      "figures": [{"number": n, "caption": c} for _, _, n, c in bands]})

    (out_dir / "content.json").write_text(
        json.dumps({"part": {"first_page": first, "last_page": last},
                    "pages": pages}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "figures.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"pages={len(pages)} blocks={sum(len(p['blocks']) for p in pages)} "
          f"figures={len(manifest)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--part", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--dpi", type=int, default=200)
    a = ap.parse_args()

    cfg = json.loads(a.config.read_text(encoding="utf-8"))
    part = next(p for p in cfg["parts"] if p["slug"] == a.part)
    extract(a.pdf, part["first_page"], part["last_page"], a.out, a.dpi)


if __name__ == "__main__":
    main()
