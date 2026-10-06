#!/usr/bin/env python
"""
Sync `books/` into the Starlight content collection.

This is the architectural seam the refactor is built around:

    books/<id>/book.json      metadata, part order, slugs, page ranges
    books/<id>/md/parts/*.md  translation (Markdown books)
    books/<id>/ir/*.json      translation (IR books)
                │
                │  docs.py sync
                ▼
    docs/src/content/docs/parts/<id>/<part>.md   frontmatter injected
    docs/public/_assets/<id>/<part>/              images

`parts/` and `_assets/` are build artifacts: gitignored, never hand-edited, rebuilt
from a clean checkout. That is what keeps `books/` the only source of truth — there is no
second copy of the prose to drift.

Metadata is derived from `book.json` here rather than hardcoded in astro.config.mjs;
`docs.py sidebar` prints the config fragment so the two cannot diverge unnoticed.

Usage:
    python tools/docs.py sync              # regenerate content + copy images
    python tools/docs.py check             # verify _generated is in sync with books/
    python tools/docs.py sidebar           # print the Starlight sidebar config
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "books"
DOCS = ROOT / "docs"
DOCS_ROOT = DOCS / "src" / "content" / "docs"
# Generated pages live directly under the content root, not in a subdirectory: Starlight's
# docs loader derives each entry's slug from its path relative to that root, so a
# `parts/` wrapper would turn every slug into `parts/<book>/<part>` and break the
# `/pi-manual/01-model/` URLs. They stay gitignored as generated files.
GENERATED = DOCS_ROOT
BOOK_CONTENT = {p.name for p in BOOKS.iterdir()} if BOOKS.exists() else set()
PUBLIC = DOCS / "public"
ASSETS = PUBLIC / "_assets"

# Durable (IR) needs this script to produce Markdown first; Pi manual already has it.
sys.path.insert(0, str(ROOT / "tools"))


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


# Assets live under the deploy root too, so the prefix is part of the URL.
ASSETS_ROOT = "/_assets"

# Fence languages Shiki does not bundle. Expressive Code warns on every build and
# downgrades them itself, so remap at the source to keep the build log readable.
LANG_FIX = {"textproto": "protobuf", "prototext": "protobuf", "plaintext": "txt"}


# Letter-spaced headings in the sources, and how they actually read.
#
# The parser returns one space for both the letter tracking and the word gaps, so
# `W H Y  I T  M A T T E R S` and `W H A T  T H I S  M E A N S  F O R  Y O U` are the same
# shape and no spacing heuristic can tell them apart. There are eight of them across both
# books, so the real words are listed rather than guessed.
TRACKED_HEADINGS = {
    "C O R E R U L E": "Core rule",
    "F O O T G U N": "Footgun",
    "R U L E O F T H U M B": "Rule of thumb",
    "V E R I F Y": "Verify",
    "W H A T T H I S M E A N S F O R Y O U": "What this means for you",
    "W H Y I T M A T T E R S": "Why it matters",
}
TRACKED_HEAD = re.compile(
    r"(?P<pre>^(?:#{1,6}\s+)|(?<=sec-alt\">))"
    r"(?P<spaced>(?:[A-Z0-9]\s+){3,}[A-Z0-9])"
    r"(?P<post>(?=</p>)|$|<)", re.M)


def untrack_headings(body: str) -> str:
    """Rewrite letter-spaced capitals in a heading using `TRACKED_HEADINGS`."""
    def fix(m):
        pre, spaced, post = m.groups()
        return pre + TRACKED_HEADINGS.get(spaced, spaced) + post
    return TRACKED_HEAD.sub(fix, body)


def rewrite_langs(body: str) -> str:
    """Remap unbundled fence languages at the opening fence only.

    A fence info string can carry a title after the language (` ```textproto file: "…"`),
    so only the first token is inspected and rewritten.
    """
    def fix(m):
        info, rest = m.group(1), m.group(2)
        parts = info.split(None, 1)
        if parts:
            parts[0] = LANG_FIX.get(parts[0].lower(), parts[0])
        return "```" + " ".join(parts) + rest
    return re.sub(r"```([^\n`]*)(.*)$", fix, body, flags=re.M)


def books() -> list:
    return sorted((b for b in BOOKS.iterdir() if (b / "book.json").exists()),
                  key=lambda p: 0 if p.name == "pi-manual" else 1)


def book_order(bdir: Path) -> str:
    return "pi-manual" if bdir.name == "pi-manual" else "pi-durable"


# ---------------------------------------------------------------- frontmatter
def fm(pairs: dict) -> str:
    lines = ["---"]
    for k, v in pairs.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for kk, vv in v.items():
                lines.append(f"  {kk}: {json.dumps(vv, ensure_ascii=False)}")
        else:
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def part_meta(cfg: dict, part: dict) -> dict:
    src = cfg["source"]
    return {
        "title": part["title_zh"],
        "description": f"{cfg['title_zh']} 第 {part['num_zh']} 部分：{part['label_zh']}"
                       f"（{src.get('pages', '?')} 页原书）",
        "sidebar": {"order": part["first_page"]},
    }


# ---------------------------------------------------------------- image handling
def copy_images(bdir: Path, slug: str) -> int:
    """Publish a part's images to public/_assets/<book>/<part>/.

    Two layouts exist. Pi manual keeps one flat `md/images/` directory for the whole book
    (MinerU names files by hash, so no two parts collide) — copying it per part would
    duplicate ~177 files 8 times. Pi Durable keeps per-part crops in `ir/<part>/figures/`.

    So the flat directory is published once under `_assets/<book>/` and referenced from
    every part, while per-part crops go under `_assets/<book>/<part>/`. `resolve_asset()`
    in sync_one() picks the right form per book.
    """
    n = 0
    flat = bdir / "md" / "images"
    if flat.is_dir():
        dest = ASSETS / bdir.name
        dest.mkdir(parents=True, exist_ok=True)
        for f in flat.iterdir():
            if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            target = dest / f.name
            if not target.exists() or target.stat().st_size != f.stat().st_size:
                shutil.copy(f, target)
            n += 1

    per_part = bdir / "ir" / slug / "figures"
    if per_part.is_dir():
        dest = ASSETS / bdir.name / slug
        dest.mkdir(parents=True, exist_ok=True)
        for f in per_part.iterdir():
            if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            target = dest / f.name
            if not target.exists() or target.stat().st_size != f.stat().st_size:
                shutil.copy(f, target)
            n += 1
    return n


def asset_prefix(bdir: Path, slug: str) -> str:
    """Where this book's images end up, so the Markdown can be rewritten to match.

    A flat per-book image directory and per-part crops need different URLs; deciding it
    once here keeps sync_one() free of layout knowledge.

    The path is root-absolute so it survives pages nested two levels deep
    (`/pi-manual/01-model/`) and a future custom domain — Astro prepends `base` at build
    time.
    """
    if (bdir / "md" / "images").is_dir():
        return f"{base_prefix()}{ASSETS_ROOT}/{bdir.name}/"
    return f"{base_prefix()}{ASSETS_ROOT}/{bdir.name}/{slug}/"


CJK = re.compile(r"[一-鿿]")


def is_page_furniture(name: str) -> bool:
    """True for images that are page furniture rather than content.

    Pi Technical Manual has no bitmaps atall — every figure is vector — so when the
    parser renders the page it also rasterises the decorative parts. The big tinted
    chapter numeral in the header is one of those, and shipping it puts a 380x290 dark
    square in the middle of chapter 1. The originals are small and near-solid, which is
    what distinguishes them from a diagram.

    Kept as an explicit list rather than a size threshold: seven files qualify, and a
    threshold would also drop a genuinely small diagram the day one appears.
    """
    return name in PAGE_FURNITURE


# Rasterised header/footer decoration from Pi Technical Manual, not figures.
PAGE_FURNITURE = {
    "e6f26104eb453e2b55b900f324b44da14eec4d64a5a680ad5eb71ad4614af91a.jpg",  # "01"
}


def _is_bilingual(text: str) -> bool:
    """True when the translation interleaves English and Chinese paragraph by paragraph.

    Pi Manual does; Pi Durable's IR is Chinese-only. The ratio is a rough test and only
    has to be decisive, not exact.
    """
    paras = [p for p in text.split("\n\n") if p.strip() and not p.startswith(("#", "<", "!", "|", "```"))]
    if len(paras) < 8:
        return False
    cjk = sum(1 for p in paras if _has_cjk(p))
    return 0.2 < cjk / len(paras) < 0.8


def mark_translations(body: str) -> str:
    """Tag the Chinese half of a bilingual pair so the stylesheet can set it apart."""
    out = []
    for block in body.split("\n\n"):
        s = block.strip()
        # leave code, tables, images and generated markup alone
        if (s.startswith(("```", "<", "!", "|", "#"))
                or not _has_cjk(s)
                or s.startswith("p.lede")):
            out.append(block)
            continue
        out.append(f'<p class="zh">{s}</p>')
    return "\n\n".join(out)


def _has_cjk(text: str) -> bool:
    return bool(CJK.search(text))


def base_prefix() -> str:
    """Read the deploy base out of astro.config.mjs.

    Markdown links need the prefix written into them — Astro does not rewrite bare absolute
    paths in content — so it must come from the file that configures the build rather than
    being repeated here. Both forms are accepted: `base: '/pi-lessons'` and
    `const BASE = '/pi-lessons'; base: BASE`.
    """
    cfg = DOCS / "astro.config.mjs"
    if not cfg.exists():
        return ""
    text = cfg.read_text(encoding="utf-8")

    const = re.search(r"""const\s+BASE\s*=\s*['"]([^'"]+)['"]""", text)
    if const:
        return const.group(1).rstrip("/")

    m = re.search(r"""base:\s*['"]([^'"]+)['"]""", text)
    return m.group(1).rstrip("/") if m else ""


def sync_one(bdir: Path, verbose=True) -> list:
    cfg = load(bdir / "book.json")
    bid = cfg["id"]
    out_dir = GENERATED / bid
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    written = []
    for idx, part in enumerate(cfg["parts"], 1):
        slug = part["slug"]
        md = bdir / "md" / "parts" / f"{slug}.md"
        if not md.exists():
            if verbose:
                print(f"  skip {bid}/{slug} (no markdown)")
            continue

        source = md.read_text(encoding="utf-8")
        body = source
        # Split the bilingual title pair into a number line and a title line.
        #
        # The source opens a chapter with a small letter-spaced number, then a large
        # title beneath it. The two books arrive differently — Pi Manual has
        # `## 1.1 English` / `## 1.1 中文` as siblings, Pi Durable has
        # `## 1.1 中文` only — so both are normalised to
        # `<p class="sec-num">1.1</p>` + `## 中文`, and the English title is kept as a
        # subtitle so the original wording is still one click away in the source.
        body = re.sub(
            r"^##\s+(\d+(?:\.\d+)*)\s+([^\n]+?)\s*\n+\s*##\s+\1\s+([^\n]+?)\s*$",
            lambda m: f'<p class="sec-num">{m.group(1)}</p>\n\n'
                      f'## {m.group(3)}\n\n<p class="sec-alt">{m.group(2)}</p>',
            body, flags=re.M)
        body = re.sub(
            r"^##\s+(\d+(?:\.\d+)*)\s+([^\n]+?)\s*$",
            lambda m: f'<p class="sec-num">{m.group(1)}</p>\n\n## {m.group(2)}',
            body, flags=re.M)

        # Unnumbered headings: Pi Manual pairs `## English` with `## 中文`. Keep the
        # Chinese as the heading and demote the English to a quiet subtitle, the same
        # treatment the numbered pair gets. Done by position, since the two lines are
        # otherwise indistinguishable.
        lines = body.split("\n")
        for i in range(len(lines) - 2):
            en, blank, zh = lines[i], lines[i + 1], lines[i + 2]
            if (blank.strip() == ""
                    and re.match(r"^##\s+\S", en)
                    and re.match(r"^##\s+\S", zh)
                    and not re.match(r"^##\s+[\d.]", en)
                    and _has_cjk(zh) and not _has_cjk(en)):
                lines[i] = f'<p class="sec-alt">{en[3:].strip()}</p>'
                lines[i + 1] = ""
                lines[i + 2] = f"## {zh[3:].strip()}"
        body = "\n".join(lines)
        # Normalise images to an explicit <img> tag.
        #
        # Markdown image syntax does not survive this pipeline: with an empty alt text
        # (`![](…)`) Starlight's MDX renderer escapes the whole thing to literal text,
        # so the page shows the raw path instead of the figure. Durable already used an
        # <img> tag and rendered fine, so both books are converted to the same form —
        # which also gives a stable place to hang the caption styling.
        prefix = asset_prefix(bdir, slug)

        def to_img(m):
            alt, name = m.group(1), m.group(2)
            if is_page_furniture(name):
                return ""            # drop it, and the blank line with it
            return f'<img src="{prefix}{name}" alt="{alt}" loading="lazy">'

        body = re.sub(r"!\[([^\]]*)\]\((?:\.\./_assets/|images/)?([^)\s]+)\)", to_img, body)
        body = re.sub(r'<img src="\.\./_assets/([^"]+)"',
                      lambda m: "" if is_page_furniture(m.group(1))
                      else f'<img src="{prefix}{m.group(1)}"', body)
        body = re.sub(r"\n{3,}", "\n\n", body)
        # Mark the translation in a bilingual pair.
        #
        # Pi Manual's translation is interleaved — English paragraph, then Chinese, then
        # the next English one. Without a marker the reader cannot tell which is which,
        # because both are set in the same face. Pi Durable's IR carries Chinese only, so
        # nothing there is marked and its pages read as ordinary prose.
        if _is_bilingual(source):
            body = mark_translations(body)
        body = rewrite_langs(body)
        body = untrack_headings(body)

        meta = part_meta(cfg, part)
        meta["sidebar"]["label"] = f"{part['num_zh']} {part['label_zh']}"
        meta["sidebar"]["order"] = idx
        (out_dir / f"{slug}.md").write_text(fm(meta) + body, encoding="utf-8")
        copy_images(bdir, slug)
        written.append(slug)

    # a per-book index so the sidebar group has a landing target
    index_meta = {
        "title": cfg["title_zh"],
        "description": cfg.get("subtitle_zh", cfg["title_zh"]),
        "sidebar": {"order": 0, "label": cfg["title_zh"]},
    }
    # Links must carry the deploy base: Starlight does not rewrite bare absolute paths in
    # Markdown, and a link to `/pi-manual/…` 404s once the site is served from a
    # sub-directory. The base is read from astro.config.mjs so there is one source.
    links = "\n".join(
        f"- [{p['num_zh']} {p['label_zh']}]({base_prefix()}/{bid}/{p['slug']}/)"
        for p in cfg["parts"] if p["slug"] in written)
    source_row = (f"原文：[x.com/{cfg['source']['author']}]"
                  f"({cfg['source']['post_url']})") if cfg.get("source", {}).get("post_url") else ""
    body = [f"# {cfg['title_zh']}", ""]
    if cfg.get("subtitle_zh"):
        body += [cfg["subtitle_zh"], ""]
    body += [links, ""]
    if source_row:
        body += [f"## 原文", "", source_row, ""]
    (out_dir / "index.md").write_text(fm(index_meta) + "\n".join(body), encoding="utf-8")

    if verbose:
        print(f"{bid:14s} {len(written)} part(s) -> {out_dir.relative_to(ROOT)}")
    return written


def rebuild_durable_markdown(verbose=True):
    """IR books have no Markdown yet; produce it before the sync.

    Figure paths are written directly into the final public form so the sync step has
    nothing to rewrite for these books.
    """
    import ir2md
    for bdir in books():
        ir_dir = bdir / "ir"
        if not ir_dir.is_dir():
            continue
        out = bdir / "md" / "parts"
        out.mkdir(parents=True, exist_ok=True)
        bid = bdir.name
        for ir in sorted(ir_dir.glob("*.json")):
            if ir.name.endswith(".meta.json"):
                continue
            slug = ir.stem
            prefix = f"{base_prefix()}{ASSETS_ROOT}/{bid}/{slug}/"
            text, _ = ir2md.convert(ir, bilingual_mode=False, asset_prefix=prefix)
            (out / f"{slug}.md").write_text(text, encoding="utf-8")
            if verbose:
                print(f"  ir2md {slug:18s} {len(text)//1024:4d} KB")


def write_sitemap(out_dir: Path) -> None:
    """Emit sitemap-index.xml plus a child sitemap for the generated pages.

    Hand-written rather than pulled from a plugin: the page set is exactly the generated
    parts plus the home page, and a plugin would add a dependency whose install fails in
    this repo (a stale pnpm tree in node_modules confuses npm's resolver).
    """
    site = "https://caizongyuan.github.io"
    base = base_prefix()
    urls = [f"{base}/"]

    for book_dir in sorted(p for p in GENERATED.iterdir() if p.is_dir()):
        if book_dir.name not in BOOK_CONTENT:
            continue
        for part in sorted(book_dir.glob("*.md")):
            if part.stem == "index":
                urls.append(f"{base}/{book_dir.name}/")
            else:
                urls.append(f"{base}/{book_dir.name}/{part.stem}/")

    # split into chunks of 40, the sitemap protocol's practical limit
    chunks = [urls[i:i + 40] for i in range(0, len(urls), 40)] or [[]]
    (out_dir / "sitemap").mkdir(parents=True, exist_ok=True)
    for i, chunk in enumerate(chunks, 1):
        body = "".join(
            f"  <url><loc>{site}{u}</loc></url>\n" for u in chunk)
        (out_dir / "sitemap" / f"page-{i}.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{body}</urlset>\n", encoding="utf-8")
    (out_dir / "sitemap-index.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <sitemap><loc>{site}{base}/sitemap/page-{i}.xml</loc></sitemap>\n"
                  for i in range(1, len(chunks) + 1))
        + "</sitemapindex>\n", encoding="utf-8")
    print(f"sitemap: {len(urls)} url(s) in {len(chunks)} file(s)")


def cmd_sync(args):
    if args.ir_to_md:
        rebuild_durable_markdown()
    GENERATED.mkdir(parents=True, exist_ok=True)
    # remove pages from a previous run whose book or part no longer exists
    for stale_dir in GENERATED.iterdir():
        if stale_dir.is_dir() and stale_dir.name not in BOOK_CONTENT:
            shutil.rmtree(stale_dir)
            print(f"  removed stale {stale_dir.name}/")

    total = 0
    for bdir in books():
        total += len(sync_one(bdir))
    (GENERATED / "404.md").write_text(
        fm({"title": "页面未找到", "template": "splash", "sidebar": {"order": 999}})
        + "# 页面未找到\n\n这个页面不存在，或者已经被移动。\n\n"
          f"可以从左侧目录回到 [首页]({base_prefix()}/)。\n",
        encoding="utf-8")
    write_sitemap(DOCS / 'public')
    print(f"synced {total} part(s) -> {GENERATED.relative_to(ROOT)}")


def cmd_check(_args):
    """Fail when _generated is stale, so CI never publishes a half-synced site."""
    if not GENERATED.exists():
        sys.exit("sync has never run: `pnpm sync`")
    stale = []
    for bdir in books():
        cfg = load(bdir / "book.json")
        for part in cfg["parts"]:
            src = bdir / "md" / "parts" / f"{part['slug']}.md"
            gen = GENERATED / cfg["id"] / f"{part['slug']}.md"
            if not src.exists():
                continue
            if not gen.exists():
                stale.append(f"missing {gen.relative_to(ROOT)}")
                continue
            if gen.stat().st_mtime < src.stat().st_mtime:
                stale.append(f"stale  {gen.relative_to(ROOT)}")
    if stale:
        print("run `pnpm sync` — these pages are out of date:")
        for s in stale[:20]:
            print("  ", s)
        sys.exit(1)
    print(f"_generated is in sync with books/")


def cmd_sidebar(_args):
    """Print the Starlight sidebar fragment derived from book.json."""
    print("[")
    print("  { label: '首页', slug: '' },")
    for i, bdir in enumerate(books()):
        cfg = load(bdir / "book.json")
        print(f"  {{")
        print(f"    label: {json.dumps(cfg['title_zh'], ensure_ascii=False)},")
        print("    collapsed: false,")
        print("    items: [")
        for part in cfg["parts"]:
            if not (bdir / "md" / "parts" / f"{part['slug']}.md").exists():
                continue
            label = f"{part['num_zh']} {part['label_zh']}"
            print(f"      {{ label: {json.dumps(label, ensure_ascii=False)}, "
                  f"slug: '{cfg['id']}/{part['slug']}' }},")
        print("    ],")
        print("  },")
    print("]")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync", help="generate parts/ from books/")
    s.add_argument("--ir-to-md", action="store_true",
                   help="also convert IR books to Markdown first")
    s.set_defaults(fn=cmd_sync)
    sub.add_parser("check", help="fail if _generated is stale").set_defaults(fn=cmd_check)
    sub.add_parser("sidebar", help="print the sidebar config").set_defaults(fn=cmd_sidebar)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()