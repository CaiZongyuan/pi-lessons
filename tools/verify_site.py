#!/usr/bin/env python
"""
Final gate before publishing: prove every page in site/ is self-contained and every
internal link resolves. Catches the failure mode where a part renders but its figures or
stylesheet never made it into the artifact — which would look fine locally and 404 on
Pages.
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

SKIP_DIRS = {".git", "__pycache__", ".workbuddy", "work"}


def main():
    if not SITE.exists():
        print("site/ does not exist — nothing to verify")
        return 0

    pages = [p for p in SITE.rglob("*.html")
             if not any(part in SKIP_DIRS for part in p.parts)]
    problems = []
    checked_links = 0

    for page in pages:
        text = page.read_text(encoding="utf-8")

        for ref in set(re.findall(r'(?:src|href)="([^"]+)"', text)):
            if ref.startswith(("http://", "https://", "mailto:", "data:", "#")):
                continue
            target = ref.split("#")[0].split("?")[0]
            if not target:
                continue
            checked_links += 1
            # Path.resolve() on Windows can mangle a relative path that walks up out of
            # the site root, so normalise against the page's own directory by hand.
            candidate = (page.parent / target)
            try:
                norm = Path(os.path.normpath(str(candidate)))
            except ValueError:
                norm = candidate
            if not norm.exists():
                problems.append(f"{page.relative_to(SITE)} -> {ref}")

    print(f"pages: {len(pages)}  internal links checked: {checked_links}")
    if problems:
        print(f"\nBROKEN ({len(problems)}):")
        for p in sorted(problems)[:40]:
            print("  ", p)
        return 1
    print("all internal links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
