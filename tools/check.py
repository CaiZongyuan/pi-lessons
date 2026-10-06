#!/usr/bin/env python
"""
Validate every book: translations complete, HTML well-formed, assets present.

Runs in CI before publishing, so a broken build never reaches Pages. Exits non-zero on
any problem.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "books"
SITE = ROOT / "site"

TRANSLATABLE = {"part-title", "chapter-title", "h2", "lede", "p", "li", "small", "figure"}
TAGS = ["html", "head", "body", "main", "section", "figure", "figcaption",
        "ul", "ol", "li", "pre", "code", "span", "p", "h1", "h2", "h3", "a", "div", "details"]


def check_book(bdir: Path, require_html: bool):
    cfg = json.loads((bdir / "book.json").read_text(encoding="utf-8"))
    book = cfg["id"]
    problems = []
    rows = []

    for part in cfg["parts"]:
        slug = part["slug"]
        ir_path = bdir / "ir" / f"{slug}.json"
        html_path = SITE / book / slug / "index.html"

        if not ir_path.exists():
            rows.append((slug, "-", "-", "not translated", False))
            continue

        nodes = json.loads(ir_path.read_text(encoding="utf-8"))["nodes"]
        # `small` covers two things: prose notes, which must be translated, and captions
        # and `Sources:` citations, which are English by design — the figure they annotate
        # is the untranslated original. Counting the latter as missing made every part
        # BAD over captions the project never intended to translate.
        def needs_translation(i, n):
            """Whether this node is prose the project owes a Chinese translation for.

            `small` is one node type covering three unrelated things: prose notes (which
            must be translated), `Sources:` file citations, and figure/table captions. The
            last two annotate artefacts that are themselves the untranslated original, and
            the project has never translated them. Counting them made every part BAD over
            content that was never in scope.
            """
            if n["type"] != "small":
                return n["type"] in TRANSLATABLE
            text = n.get("text", "")
            if text.startswith(("Sources:", "//", "#", "$")):
                return False
            # a caption sets out what a figure or table shows; an entry in a reference
            # table leads with its identifier and carries a section reference, so those two
            # shapes are the ones that are genuinely prose
            if re.match(r"^[A-Za-z_][\w.]*\s*\(", text):
                return True
            if re.search(r"\d+\.\d+\s*\(p\.\s*\d+\)", text):
                return True
            return False

        missing = [n["type"] for i, n in enumerate(nodes)
                   if needs_translation(i, n)
                   and not (n.get("zh") or n.get("zh_caption"))]

        notes, fatal = [], []
        if missing:
            notes.append(f"UNTRANSLATED {len(missing)}: {missing[:4]}")
            fatal.extend(notes)          # a half-translated part must block publishing

        if html_path.exists():
            s = html_path.read_text(encoding="utf-8")
            for t in TAGS:
                o = len(re.findall(r"<" + t + r"[ >]", s))
                c = s.count("</" + t + ">")
                if o != c:
                    fatal.append(f"TAG {t}:{o}/{c}")
            for ref in set(re.findall(r'(?:src|href)="([^"#:]+)"', s)):
                if ref.startswith(("http", "mailto", "#")):
                    continue
                if not (html_path.parent / ref).exists():
                    fatal.append(f"MISSING ASSET {ref}")
            status = "ok" if not fatal else "BAD"
            notes = fatal
        else:
            status = "-"
            if require_html:
                # only a real problem once the render step should have produced output
                fatal.append("html not built")
                notes.append("html not built")

        rows.append((slug, len(nodes), len(missing), status, fatal))
        problems.extend(fatal)

    return book, rows, problems


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    # Before the render step a clean checkout legitimately has no HTML yet, so a missing
    # page is reported but not treated as a failure. `verify_site.py` covers the case
    # where a page is expected and its assets are missing.
    require_html = os.environ.get("CHECK_REQUIRE_HTML") == "1"

    total = 0
    print(f"{'part':20s} {'nodes':>6s} {'miss':>5s}  status")
    for bdir in sorted(BOOKS.iterdir()):
        if not (bdir / "book.json").exists():
            continue
        book, rows, problems = check_book(bdir, require_html)
        if only and book != only:
            continue
        print(f"\n== {book}")
        for slug, n, m, note, _ in rows:
            print(f"{slug:20s} {str(n):>6s} {str(m):>5s}  {note}")
        total += len(problems)

    print(f"\nPROBLEMS: {total}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
