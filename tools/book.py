#!/usr/bin/env python
"""
Unified entry point for every book in this repo.

    python tools/book.py list                      # show books and their parts
    python tools/book.py extract <book> [--part S]  # PDF  -> IR (+ figure crops)
    python tools/book.py render <book> [--part S]   # IR   -> HTML
    python tools/book.py build   <book> [--part S]  # extract + render
    python tools/book.py check  [<book>]            # validate output
    python tools/book.py index                      # regenerate the landing page

Design constraints that shape this file:

* **The render stage never needs the PDF.** IR + meta + figure crops are enough, which
  is what lets CI publish without shipping the source PDF in the repo.
* **Part metadata lives in books/<id>/book.json**, not in Python, so adding a book or
  adjusting page ranges never requires a code change.
* **The source PDF is located via --pdf, the PI_PDF environment variable, or a local
  cache dir**, because the PDFs are deliberately not committed.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
PIPELINE = TOOLS / "pdf2html"
BOOKS = ROOT / "books"
SITE = ROOT / "site"
PY = sys.executable


# ---------------------------------------------------------------- discovery
# Pi before Durable: it is the primary tutorial, Durable is the follow-up deep dive.
BOOK_ORDER = {"pi-manual": 0, "pi-durable": 1}


def find_books():
    """All book directories, primary tutorial first."""
    def key(p):
        try:
            bid = json.loads((p / "book.json").read_text(encoding="utf-8"))["id"]
        except Exception:
            return 99
        return (BOOK_ORDER.get(bid, 50), bid)
    return sorted((p for p in BOOKS.iterdir() if (p / "book.json").exists()), key=key)


def load_config(book_id: str) -> dict:
    for b in find_books():
        cfg = json.loads((b / "book.json").read_text(encoding="utf-8"))
        if cfg["id"] == book_id or b.name == book_id:
            return cfg
    raise SystemExit(f"unknown book: {book_id}\navailable: "
                     + ", ".join(load_all_ids()))


def load_all_ids():
    out = []
    for b in find_books():
        out.append(json.loads((b / "book.json").read_text(encoding="utf-8"))["id"])
    return out


def locate_pdf(cfg: dict, explicit: str | None) -> Path:
    """Find the source PDF: explicit flag, then $PI_PDF, then a local cache."""
    name = cfg["source"]["filename"]
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("PI_PDF"):
        candidates.append(Path(os.environ["PI_PDF"]) / name)
        candidates.append(Path(os.environ["PI_PDF"]))
    candidates.append(BOOKS / cfg["id"] / "source" / name)
    candidates.append(ROOT / "source" / name)

    for c in candidates:
        if c.is_file():
            return c
    raise SystemExit(
        f"PDF not found for '{cfg['id']}'.\n"
        f"  looked for: {name}\n"
        f"  Fix: pass --pdf <path>, or set PI_PDF=<dir containing the pdf>.\n"
        f"  (source PDFs are intentionally not committed to this repo)"
    )


# ---------------------------------------------------------------- layout
def ir_dir(book: str, part: str | None):
    b = BOOKS / book
    return b / "ir" if part is None else b / "ir" / part


def out_dir(book: str, part: str):
    return SITE / book / part


# ---------------------------------------------------------------- commands
def cmd_list(args):
    if getattr(args, "ids", False):
        for b in find_books():
            print(json.loads((b / "book.json").read_text(encoding="utf-8"))["id"])
        return
    for b in find_books():
        cfg = json.loads((b / "book.json").read_text(encoding="utf-8"))
        pages = cfg["source"].get("pages", "?")
        print(f"\n{cfg['id']}  —  {cfg['title_zh']}   ({pages} pages)")
        if cfg.get("status"):
            print(f"  status: {cfg['status']}")
        for p in cfg["parts"]:
            done = "x" if (b / "ir" / f"{p['slug']}.json").exists() else " "
            built = "x" if (SITE / cfg["id"] / p["slug"] / "index.html").exists() else " "
            print(f"    [{done}{built}] {p['slug']:16s} p{p['first_page']:>3}-{p['last_page']:<3} {p['title_zh']}")
    print("\nlegend: [x ] = IR translated   [ x] = HTML built")


def cmd_extract(args):
    cfg = load_config(args.book)
    pdf = locate_pdf(cfg, args.pdf)
    parts = [p for p in cfg["parts"]
             if args.part in (None, p["slug"])]
    for p in parts:
        out = ir_dir(args.book, p["slug"])
        print(f"--- extract {cfg['id']}/{p['slug']}")
        subprocess.run(
            [PY, str(PIPELINE / "extract.py"),
             "--pdf", str(pdf), "--config", str(BOOKS / args.book / "book.json"),
             "--part", p["slug"], "--out", str(out), "--dpi", str(args.dpi)],
            check=True)
        subprocess.run([PY, str(PIPELINE / "normalize.py"), str(out)], check=True)
        # meta.json lives beside the IR so render needs nothing else
        meta = {"css": "style.css", "part_label": p["label_zh"],
                "part_title_zh": p["title_zh"], "part_num_zh": p["num_zh"],
                "part_sub_zh": "", "toc": True}
        (out / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_render(args):
    cfg = load_config(args.book)
    parts = [p for p in cfg["parts"] if args.part in (None, p["slug"])]
    for p in parts:
        src = ir_dir(args.book, p["slug"])
        ir = src / "ir.json"
        if not ir.exists():
            # migrated layout: <slug>.json beside the figures dir
            ir = src.with_suffix(".json")
            src = ir.parent
        if not ir.exists():
            print(f"skip {p['slug']} (no IR yet — run extract)")
            continue
        # normalise naming so render always sees ir.json + meta.json + figures/
        work = src
        if ir.name != "ir.json":
            work = src / p["slug"]
            work.mkdir(exist_ok=True)
            shutil.copy(ir, work / "ir.json")
            meta_src = src.with_suffix(".meta.json")
            if meta_src.exists():
                shutil.copy(meta_src, work / "meta.json")
            elif (src / "meta.json").exists():
                shutil.copy(src / "meta.json", work / "meta.json")
            if (src / "figures").is_dir() and not (work / "figures").is_dir():
                shutil.copytree(src / "figures", work / "figures")

        out = out_dir(args.book, p["slug"])
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy(PIPELINE / "style.css", work / "style.css")
        # the page links "style.css" relatively, so the sheet must sit beside it
        shutil.copy(PIPELINE / "style.css", out / "style.css")
        subprocess.run([PY, str(PIPELINE / "render.py"), str(work), str(out / "index.html")],
                       check=True)
        # figures must sit next to the html for relative src to resolve
        if (work / "figures").is_dir() and not (out / "figures").is_dir():
            shutil.copytree(work / "figures", out / "figures")
        print(f"--- rendered {cfg['id']}/{p['slug']} -> {out}")


def cmd_build(args):
    cmd_extract(args)
    cmd_render(args)
    cmd_index(args)


def cmd_index(_args):
    subprocess.run([PY, str(PIPELINE / "bookindex.py")], check=True)


def cmd_check(args):
    subprocess.run([PY, str(TOOLS / "check.py")] + ([args.book] if args.book else []),
                   check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="show books and their parts")
    p.add_argument("--ids", action="store_true", help="print book ids only (for scripts)")
    p.set_defaults(fn=cmd_list)

    for name, fn in (("extract", cmd_extract), ("render", cmd_render), ("build", cmd_build)):
        p = sub.add_parser(name, help=f"{name} a book")
        p.add_argument("book")
        p.add_argument("--part", help="limit to one part slug")
        p.add_argument("--pdf", help="path to the source PDF")
        p.add_argument("--dpi", type=int, default=200)
        p.set_defaults(fn=fn)

    p = sub.add_parser("index", help="regenerate site/index.html")
    p.set_defaults(fn=cmd_index)

    p = sub.add_parser("check", help="validate IR and HTML")
    p.add_argument("book", nargs="?")
    p.set_defaults(fn=cmd_check)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
