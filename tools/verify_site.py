#!/usr/bin/env python
"""
Verify a built documentation site before publishing.

Takes the output directory as an argument so it works for both the Astro build (`docs/dist`)
and the legacy Python renderer (`site/`) — the checks are the same because the failure
modes are the same: a page that renders but whose images 404, an internal link to a page
that was never generated, an asset path that ignores the deploy base.

    python tools/verify_site.py docs/dist
    python tools/verify_site.py docs/dist --base /pi-lessons --expect pi-manual/01-model/index.html
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {".git", "__pycache__", ".workbuddy", "work", "node_modules", "src"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=str(ROOT / "docs" / "dist"),
                    help="build output directory (default: docs/dist)")
    ap.add_argument("--base", default="/pi-lessons",
                    help="deploy base path the site is served under")
    ap.add_argument("--expect", action="append", default=[],
                    help="path that must exist, e.g. pi-manual/01-model/index.html")
    a = ap.parse_args()

    out = Path(a.out).resolve()
    if not out.exists():
        print(f"output directory does not exist: {out}")
        return 1

    pages = [p for p in out.rglob("*.html") if not any(s in p.parts for s in SKIP_DIRS)]
    if not pages:
        print("no HTML pages found — was the build run?")
        return 1

    problems = []
    checked = 0
    kinds = {"css": 0, "js": 0, "img": 0, "other": 0}

    for page in pages:
        text = page.read_text(encoding="utf-8")

        for ref in set(re.findall(r'(?:src|href)="([^"]+)"', text)):
            if ref.startswith(("http://", "https://", "mailto:", "data:", "#")):
                continue
            target = ref.split("#")[0].split("?")[0]
            if not target:
                continue

            # A base-prefixed absolute path resolves from the deploy root, not from the
            # page's own directory; anything else that starts with "/" would escape the
            # site root and 404 once deployed under a sub-path.
            if target.startswith("/"):
                if not target.startswith(a.base):
                    problems.append(
                        f"{page.relative_to(out)}: {ref} escapes the base {a.base}")
                    continue
                candidate = out / target[len(a.base):].lstrip("/")
            else:
                candidate = page.parent / target
            checked += 1

            ext = candidate.suffix.lower()
            if ext == ".css":
                kinds["css"] += 1
            elif ext == ".js":
                kinds["js"] += 1
            elif ext in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".avif"):
                kinds["img"] += 1
            else:
                kinds["other"] += 1

            if not candidate.exists():
                problems.append(f"{page.relative_to(out)} -> {ref}")

    for want in a.expect:
        p = out / want
        if not (p.exists() or (p / "index.html").exists()):
            problems.append(f"expected page missing: {want}")

    # A published site that still points at the source PDF, or at a developer machine,
    # leaks both the licence position and the build environment.
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for pat, label in ((r"file:///[A-Za-z]", "absolute local path"),
                           (r"[A-Za-z]:\\\\", "windows local path"),
                           (r'href="[^"]*\.pdf"', "link to a source PDF")):
            m = re.search(pat, text)
            if m:
                problems.append(f"{page.relative_to(out)}: {label} ({m.group(0)!r})")

    print(f"pages: {len(pages)}   references checked: {checked}")
    print(f"  css {kinds['css']}  js {kinds['js']}  images {kinds['img']}  other {kinds['other']}")
    print(f"  base: {a.base}")

    if problems:
        print(f"\nPROBLEMS ({len(problems)}):")
        for p in problems[:40]:
            print("  ", p)
        if len(problems) > 40:
            print(f"   ... and {len(problems) - 40} more")
        return 1

    print("\nall pages self-contained; no reference escapes the base")
    return 0


if __name__ == "__main__":
    sys.exit(main())