#!/usr/bin/env python
"""
Validate every book: translations complete, HTML well-formed, assets present.

Runs in CI before publishing, so a broken build never reaches Pages. Exits non-zero on
any problem.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "books"
SITE = ROOT / "site"

TRANSLATABLE = {"part-title", "chapter-title", "h2", "lede", "p", "li", "small", "figure"}
TAGS = ["html", "head", "body", "main", "section", "figure", "figcaption",
        "ul", "ol", "li", "pre", "code", "span", "p", "h1", "h2", "h3", "a", "div", "details"]


def check_book(bdir: Path, only: str | None):
    cfg = json.loads((bdir / "book.json").read_text(encoding="utf-8"))
    book = cfg["id"]
    problems = []
    rows = []

    for part in cfg["parts"]:
        slug = part["slug"]
        ir_path = bdir / "ir" / f"{slug}.json"
        html_path = SITE / book / slug / "index.html"

        if not ir_path.exists():
            rows.append((slug, "-", "-", "not translated"))
            continue

        nodes = json.loads(ir_path.read_text(encoding="utf-8"))["nodes"]
        missing = [n["type"] for n in nodes
                   if n["type"] in TRANSLATABLE
                   and not (n.get("zh") or n.get("zh_caption"))]

        notes = []
        if missing:
            notes.append(f"UNTRANSLATED {len(missing)}: {missing[:4]}")

        if html_path.exists():
            s = html_path.read_text(encoding="utf-8")
            for t in TAGS:
                o = len(re.findall(r"<" + t + r"[ >]", s))
                c = s.count("</" + t + ">")
                if o != c:
                    notes.append(f"TAG {t}:{o}/{c}")
            # every referenced local asset must exist next to the page
            for ref in set(re.findall(r'(?:src|href)="([^"#:]+)"', s)):
                if ref.startswith(("http", "mailto", "#")):
                    continue
                if not (html_path.parent / ref).exists():
                    notes.append(f"MISSING ASSET {ref}")
            status = "ok" if not notes else "BAD"
        else:
            status = "-"
            notes.append("html not built")

        rows.append((slug, len(nodes), len(missing), status + ("; " + "; ".join(notes) if notes else "")))
        problems.extend(notes)

    return book, rows, problems


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    total = 0
    print(f"{'part':20s} {'nodes':>6s} {'miss':>5s}  status")
    for bdir in sorted(BOOKS.iterdir()):
        if not (bdir / "book.json").exists():
            continue
        book, rows, problems = check_book(bdir, only)
        if only and book != only:
            continue
        print(f"\n== {book}")
        for slug, n, m, note in rows:
            ns = n if isinstance(n, str) else str(n)
            ms = m if isinstance(m, str) else str(m)
            print(f"{slug:20s} {ns:>6s} {ms:>5s}  {note}")
        total += len(problems)

    print(f"\nPROBLEMS: {total}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
