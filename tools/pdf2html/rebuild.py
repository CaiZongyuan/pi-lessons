#!/usr/bin/env python
"""
Re-run extraction + normalisation for a book while *preserving* translations.

Normalisation rules improve as we learn more about the source (caption/code separation,
line merging, list detection). Re-running would wipe every translated `zh` field, so
translations are matched back onto the rebuilt nodes by progressively looser keys.

    python tools/pdf2html/rebuild.py pi-durable
    python tools/pdf2html/rebuild.py pi-manual --part 01-model
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BOOKS = ROOT / "books"
PIPELINE = Path(__file__).resolve().parent
PY = sys.executable

sys.path.insert(0, str(ROOT / "tools"))


def snapshot(path: Path):
    """Translation payloads keyed by progressively looser identity.

    A rule change can alter a node's *type* as well as its boundaries — a caption used to
    be classed as `code` and is now `small` — so the type is deliberately excluded from
    the loosest keys. Without that, a genuine reclassification silently orphans the
    translation.
    """
    if not path.exists():
        return {}
    d = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for n in d["nodes"]:
        payload = {}
        if n.get("zh"):
            payload["zh"] = n["zh"]
        if n.get("zh_caption"):
            payload["zh_caption"] = n["zh_caption"]
        if not payload:
            continue
        text = n.get("text", "")
        norm = " ".join(text.split())
        out[("full", n["type"], n.get("page"), text)] = payload
        out[("norm", n["type"], n.get("page"), norm)] = payload
        # type-free keys: survive a node being reclassified
        if len(norm) >= 24:
            out[("anytype", norm)] = payload
            out[("anystem", norm[:40])] = payload
        # strongest key: same page and same position is the same node, whatever it was
        # called before. Column-table detection rebuilds rows from scratch, so this is the
        # only thing that can put their translations back.
        if n.get("page") is not None and n.get("_y") is not None:
            out[("pos", n["page"], round(n["_y"]))] = payload
    return out


def _lookup(snap, n):
    text = n.get("text", "")
    norm = " ".join(text.split())
    # position first for a table row: it is rebuilt from the blocks at that place, so its
    # own text is new and no text key can match
    if n["type"] == "table-row" or n.get("_y") is not None:
        key = ("pos", n.get("page"), round(n["_y"])) if n.get("_y") is not None else None
        if key and key in snap:
            return snap[key]
    for key in (
        ("full", n["type"], n.get("page"), text),
        ("norm", n["type"], n.get("page"), norm),
        ("anytype", norm),
        ("anystem", norm[:40]),
    ):
        if key in snap:
            return snap[key]
    return None


def restore(path: Path, snap) -> int:
    if not snap:
        return 0
    d = json.loads(path.read_text(encoding="utf-8"))
    hits = 0
    for n in d["nodes"]:
        if n["type"] == "code":
            continue
        if n.get("zh") or n.get("zh_caption"):
            hits += 1
            continue
        payload = _lookup(snap, n)
        if payload:
            n.update(payload)
            hits += 1
    path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("--part")
    ap.add_argument("--pdf", help="source PDF (or set PI_PDF)")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    bdir = BOOKS / args.book
    cfg = json.loads((bdir / "book.json").read_text(encoding="utf-8"))

    from book import locate_pdf          # same PDF resolution rules as book.py
    pdf = locate_pdf(cfg, args.pdf)

    for part in cfg["parts"]:
        slug = part["slug"]
        if args.part and slug != args.part:
            continue
        out = bdir / "ir" / slug
        ir = out / "ir.json"
        if not ir.exists():
            print(f"skip {slug} (never extracted)")
            continue

        snap = snapshot(ir)
        (out / "ir.prev.json").write_text(ir.read_text(encoding="utf-8"), encoding="utf-8")

        subprocess.run([PY, str(PIPELINE / "extract.py"),
                        "--pdf", str(pdf), "--config", str(bdir / "book.json"),
                        "--part", slug, "--out", str(out), "--dpi", str(args.dpi)],
                       check=True, capture_output=True)
        subprocess.run([PY, str(PIPELINE / "normalize.py"), str(out)],
                       check=True, capture_output=True)

        kept = restore(ir, snap)
        total = len(json.loads(ir.read_text(encoding="utf-8"))["nodes"])
        print(f"{slug:18s} nodes={total:4d}  translated={kept:4d}")


if __name__ == "__main__":
    main()