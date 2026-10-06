#!/usr/bin/env python
"""
Split a MinerU-converted book into one Markdown file per part.

MinerU returns the whole book as a single stream, so the part structure has to be
recovered from the text. The reliable signal is the book's own part openers — the ones
that read like "PART 2 The Provider Layer" — which the parser emits inconsistently:

    "## The Provider Layer"                 a heading, number lost
    "2 The Provider Layer"                  a heading, number glued on
    "P A R T 2The Provider Layer"           tracked caps, number glued on
    "## 2 The Provider Layer"               already fine

`normalise_part_headings` rewrites all of these to "## Part N · Title" first, so
`split_parts` has one shape to look for. Chapter numbers ("1.1", "R.4") sit on their own
line before the title in the source, so those are rejoined too — otherwise the translation
loses the numbering it is supposed to preserve.

Usage:
    python tools/mdsplit.py books/pi-manual/md/1-190.md --out books/pi-manual/md/parts
    python tools/mdclean.py books/pi-manual/md/parts/*.md
"""

import argparse
import re
from pathlib import Path

# "P A R T 2The Provider Layer" / "PART 2The Provider Layer" / "PART 2 The Provider Layer"
PART_GLUED = re.compile(r"^#{0,6}\s*P\s?A\s?R\s?T\s+(\d+)\s*\.?\s*(.+?)\s*$", re.I)
# "## The Provider Layer" — no number yet
BARE_HEAD = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
# a lone "1.1" or "R.4" line sitting just above its title
LONE_NUM = re.compile(r"^(\d+\.\d+|R\.\d+)\s*$")
CHAP_TITLE = re.compile(r"^#{1,6}\s+(\d+\.\d+|R\.\d+)\s+(.+?)\s*$")

# how the parts are named, in book order
PART_TITLES = {
    1: "The Model", 2: "The Provider Layer", 3: "The Agent Loop",
    4: "The Coding Agent", 5: "Configuration and Extensibility",
    6: "Integrations and Interface", 7: "Experimental and Operations",
    8: "Reference",
}
PART_SLUGS = {
    1: "01-model", 2: "02-provider", 3: "03-agent-loop", 4: "04-coding-agent",
    5: "05-config", 6: "06-integrations", 7: "07-operations", 8: "08-reference",
}


def normalise_part_headings(text: str) -> str:
    """Rewrite each part opener to '## Part N · Title'.

    MinerU drops the part number from the big display heading — the page shows a large
    "02" as a separate graphic, and what survives in the text stream is just
    "## The Provider Layer". The table of contents keeps the number ("2 The Provider
    Layer"), so that is the authority: we title the openers from `PART_TITLES` in book
    order rather than trusting the OCR to have numbered them.
    """
    lines = text.split("\n")
    out = []
    seen = 0
    # the contents block sits at the top; everything before the first real part opener
    # is front matter and stays with whatever chunk it lands in
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.strip())
        if m:
            title = m.group(2).strip()
            for num, want in PART_TITLES.items():
                # match the opener by title, in book order, so a repeated word elsewhere
                # cannot steal the match; never accept a numbered chapter heading
                if title.lower() == want.lower() and num > seen:
                    out.append(f"## Part {num} · {want}")
                    seen = num
                    break
            else:
                out.append(line)
        else:
            out.append(line)
    return "\n".join(out)


def rejoin_chapter_numbers(text: str) -> str:
    """Fold a lone '1.1' line into the heading below it, and drop its TOC twin.

    Two artefacts come from the printed layout. The contents list puts the chapter
    number, title and page number on one line ("1.1 System prompt construction 75"), and
    the chapter itself starts with the number alone on a line and then the title as a
    heading ("4 . 1" then "## System prompt construction"). Keeping the TOC line would
    put a phantom chapter in the translation, so it is dropped once the real heading has
    been recognised.
    """
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        raw = lines[i].strip()

        # "4 . 1" on its own -> the number belongs to the next heading
        m = re.match(r"^(\d+)\s*\.\s*(\d+)$", raw)
        if m:
            num = f"{m.group(1)}.{m.group(2)}"
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                hm = BARE_HEAD.match(lines[j].strip())
                if hm:
                    out.append(f"{hm.group(1)} {num} {hm.group(2)}")
                    i = j + 1
                    continue

        # "1.1 System prompt construction 75" -> a contents entry, drop it
        toc = re.match(r"^(\d+\.\d+|R\.\d+)\s+(.+?)\s+\d{1,3}$", raw)
        if toc:
            i += 1
            continue

        out.append(lines[i])
        i += 1
    return "\n".join(out)


def drop_front_matter(lines: list[str]) -> list[str]:
    """Remove the printed table of contents and the 'how to read this book' preamble.

    Everything before the first part opener is front matter: a contents list with page
    numbers and a short reader's guide. It is navigation, not tutorial content, and would
    only be translated into dead weight.
    """
    start = next((i for i, l in enumerate(lines)
                  if re.match(r"^##\s+Part\s+\d+\s*·", l.strip())), 0)
    return lines[start:]


def split_parts(text: str):
    """Yield (part_number, body_lines). Front matter is dropped, not attached."""
    lines = drop_front_matter(text.split("\n"))
    chunks = {}
    current = None
    buf: list[str] = []
    for line in lines:
        m = re.match(r"^##\s+Part\s+(\d+)\s*·", line.strip())
        if m:
            if current is not None:
                chunks[current] = buf
            current = int(m.group(1))
            buf = []
            continue
        buf.append(line)
    if current is not None:
        chunks[current] = buf
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()

    raw = a.src.read_text(encoding="utf-8")
    text = normalise_part_headings(raw)
    text = rejoin_chapter_numbers(text)
    chunks = split_parts(text)

    a.out.mkdir(parents=True, exist_ok=True)
    for num, body in sorted(chunks.items()):
        slug = PART_SLUGS.get(num, f"part-{num:02d}")
        path = a.out / f"{slug}.md"
        path.write_text("\n".join(body).strip() + "\n", encoding="utf-8")
        heads = sum(1 for l in body if re.match(r"^#{1,6}\s", l))
        print(f"{path.name:20s} {len(body):6d} lines  {heads:3d} headings  "
              f"({len(chr(10).join(body))//1024} KB)")

    print(f"\nparts found: {sorted(chunks)}")


if __name__ == "__main__":
    main()