#!/usr/bin/env python
"""
Clean MinerU output.

MinerU reads the page geometry faithfully, which is exactly the problem here: both manuals
are set with letter-spaced Type3 fonts, so the parser sees "sma<sup>ll</sup> core
t<sup>h</sup>at" instead of "small core that". Every glyph becomes its own superscript run.
Tables and images come through well, so the fix is surgical — unwrap the fragments and
re-join the letters — rather than a general-purpose Markdown tidy-up.

Two passes:
  1. collapse the sup/sub fragments back into plain text
  2. repair the damage that leaves behind: doubled first letters ("tthe"), stray
     underscores from escaped Markdown, and words split across an inline image

Usage:
    python tools/mdclean.py books/pi-manual/md/6-10.md            # in place
    python tools/mdclean.py books/pi-manual/md/*.md --to-md/     # batch
"""

import argparse
import re
from pathlib import Path

# a single letter or short run wrapped in <sup>…</sup> / <sub>…</sub>
FRAG = re.compile(r"</?(?:sup|sub)>", re.I)
# <sup>ll</sup> core t<h>at  ->  the tail of a word is in sup, the head is not
SUP_ONLY = re.compile(r"<sup>([^<>]{1,4})</sup>", re.I)


def strip_fragments(text: str) -> str:
    """Remove every sup/sub tag, keeping the text they wrap."""
    return FRAG.sub("", text)


def fix_doubled_letters(text: str) -> str:
    """Unwrapping sup tags can leave the previous letter duplicated.

    "t<sup>h</sup>at" -> "that" is fine, but a head letter that was itself split gives
    "tthe". Only collapse a doubled consonant at a word boundary, where the doubling is
    certainly an artefact.
    """
    text = re.sub(r"\b([bcdfghjklmnpqrstvwxz])\1(?=[a-z]{2,})", r"\1", text)
    return text


def fix_escaped(text: str) -> str:
    """MinerU escapes underscores inside identifiers; in prose they read as noise."""
    text = re.sub(r"\\([_*])", r"\1", text)
    # …that ships at commit 28dcce2, counts each surface from the source, and names…
    return text


def fix_split_words(text: str) -> str:
    """Rejoin words the parser fused or broke.

    Two artefacts recur: a line break inside a word ("of\nnamed" -> "of named"), and a
    dropped space where a run was recombined ("swapped of" for "swapped off" is content,
    but "ofnamed" is a join artefact). Only the fused form is repaired here — inserting a
    space needs the dictionary, not a regex.
    """
    text = re.sub(r"([a-z])\n([a-z]{2,})", r"\1 \2", text)
    # a lowercase run immediately followed by a capitalized one lost its space
    text = re.sub(r"\b([a-z]{3,})([A-Z][a-z]{2,})\b", r"\1 \2", text)
    return text


CODE_HINT = re.compile(r"[$§]|\b(?:const|let|await|async|function|return|export|import)\b"
                       r"|=>|^\s*[<\[(]|\b\w+\s*:\s*\w")


def demote_pseudo_headings(text: str) -> str:
    """Turn code comments back into comments.

    MinerU sometimes reads a leading `# …` line inside a fenced code block as a Markdown
    heading, so a code block gets chopped up and its comments surface as document headings.
    The giveaway is that these lines look like code: they mention `$`/`§` markers, a
    keyword, an arrow, or a type annotation.
    """
    out = []
    for line in text.split("\n"):
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m and CODE_HINT.search(m.group(2)):
            line = "#" + line          # one more hash => code comment inside a fence
        out.append(line)
    return "\n".join(out)


def fix_heading_spacing(text: str) -> str:
    """`## TheModel` -> `## The Model`; tracked caps leave words glued together.

    Acronyms must survive intact: splitting on the case boundary alone turns "WireAPIs"
    into "Wire AP Is" and "APIs" into "AP Is". So a boundary only counts as a word break
    when the following capital is followed by a *lowercase* letter (the "APIs" in
    "WireAPIs" → "Wire APIs"), or when the pair sits either side of a digit run.
    """
    def sp(m):
        title = m.group(2)
        # split "APIs" style boundaries only: capital + (Cap)(lower)
        t = re.sub(r"(?<=[a-z0-9])(?=[A-Z][a-z])", " ", title)
        # split "TheModel" style boundaries: lower/digit + Capital + Capitals
        t = re.sub(r"(?<=[a-z0-9])(?=[A-Z](?=[A-Z]))", " ", t)
        return f"{m.group(1)} {t.strip()}"
    return re.sub(r"^(#{1,6})\s+(.+)$", sp, text, flags=re.M)


def tidy(text: str) -> str:
    text = strip_fragments(text)
    text = fix_escaped(text)
    text = fix_doubled_letters(text)
    text = fix_split_words(text)
    text = demote_pseudo_headings(text)
    text = fix_heading_spacing(text)
    # a heading that is one tracked-caps run: "W H Y I T M A T T E R S"
    text = re.sub(r"^(#{1,6})\s*((?:[A-Z]\s+){3,}[A-Z])\s*$",
                  lambda m: f"{m.group(1)} {re.sub(r'\\s+', ' ', m.group(2)).title()}",
                  text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip() + "\n"


def clean_file(src: Path, dest: Path | None = None) -> tuple[int, int]:
    raw = src.read_text(encoding="utf-8")
    out = tidy(raw)
    (dest or src).write_text(out, encoding="utf-8")
    return len(raw), len(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--to-md", help="write cleaned copies into this directory")
    a = ap.parse_args()

    for p in a.paths:
        if not p.is_file():
            print(f"skip {p} (not a file)")
            continue
        if a.to_md:
            dest = Path(a.to_md) / p.name
            dest.parent.mkdir(parents=True, exist_ok=True)
        else:
            dest = None
        before, after = clean_file(p, dest)
        shown = dest or p
        print(f"{shown}: {before//1024} KB -> {after//1024} KB")


if __name__ == "__main__":
    main()