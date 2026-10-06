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
        missing = [n["type"] for n in nodes
                   if n["type"] in TRANSLATABLE
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
