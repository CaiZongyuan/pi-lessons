"""
Re-run extraction + normalisation for every part while *preserving* existing
translations, then re-render.

Normalisation rules change as we learn more about the source (caption/code
separation, line merging, list detection). Without this, a rule fix would wipe the
translated `zh` fields. Translations are matched to nodes by (type, page, english
text) so they survive the rebuild.

Usage:  python rebuild.py            # all parts
        python rebuild.py 05tasks    # just one
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
PY = sys.executable
sys.path.insert(0, str(HERE))
from parts import PARTS, part_dir  # noqa: E402


def snapshot(path: Path):
    """Map several keys -> translation payload, for progressively looser matching."""
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
        out[("full", n["type"], n.get("page"), text)] = payload
        # looser keys let a translation survive a rule change that re-merged or
        # re-split neighbouring lines
        norm = " ".join(text.split())
        out[("norm", n["type"], n.get("page"), norm)] = payload
        if len(norm) > 24:
            out[("stem", n["type"], n.get("page"), norm[:24])] = payload
    return out


def _lookup(snap, n):
    text = n.get("text", "")
    norm = " ".join(text.split())
    for key in (
        ("full", n["type"], n.get("page"), text),
        ("norm", n["type"], n.get("page"), norm),
        ("stem", n["type"], n.get("page"), norm[:24]),
    ):
        if key in snap:
            return snap[key]
    return None


def restore(path: Path, snap):
    if not snap:
        return 0, 0
    d = json.loads(path.read_text(encoding="utf-8"))
    hits = exact = 0
    for n in d["nodes"]:
        if n["type"] == "code":
            continue
        if n.get("zh") or n.get("zh_caption"):
            exact += 1
            continue
        payload = _lookup(snap, n)
        if payload:
            n.update(payload)
            hits += 1
    path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return exact + hits, hits


def main():
    targets = sys.argv[1:] or [p[0] for p in PARTS]
    for slug in targets:
        d = part_dir(slug)
        ir = d / "ir.json"
        # stash the previous IR so a failed run never loses the translations
        bak = d / "ir.prev.json"
        snap = snapshot(ir)
        before = len({k for k in snap})
        if ir.exists():
            bak.write_text(ir.read_text(encoding="utf-8"), encoding="utf-8")

        subprocess.run([PY, str(HERE / "extract.py"), *_pages(slug), str(d)],
                       check=True, capture_output=True)
        subprocess.run([PY, str(HERE / "normalize.py"), str(d)],
                       check=True, capture_output=True)

        total_nodes, kept = restore(ir, snap)
        total = len(json.loads(ir.read_text(encoding="utf-8"))["nodes"])
        d = part_dir(slug)
        (d / "style.css").write_text((HERE / "style.css").read_text(encoding="utf-8"),
                                     encoding="utf-8")
        subprocess.run([PY, str(HERE / "render.py"), str(d), str(d / "index.html")],
                       check=True, capture_output=True)
        print(f"{slug:18s} nodes={total:4d}  translated={kept:4d}  (backup: ir.prev.json)")


def _pages(slug):
    _, a, b, *_ = next(p for p in PARTS if p[0] == slug)
    return str(a), str(b)


if __name__ == "__main__":
    main()