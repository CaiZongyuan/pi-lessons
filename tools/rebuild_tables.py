"""Re-extract every chapter, then rebuild the reference tables and their translations.

`normalize.py` recognises the reference tables' three-column layout and emits `table-row`
nodes; that has to run for the whole book before the translations can be reattached,
because a chapter's Chinese may cover rows the previous run never produced.

`table_zh.py` then splits the merged Chinese back onto the rows, anchored on the
signatures each blob names.
"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "tools/pdf2html")
import rebuild  # noqa: E402  — the snapshot/restore pair that carries translations over

PY = sys.executable


def main() -> int:
    # usage: rebuild_tables.py <slug> [<stash-dir>] [part ...]
    args = sys.argv[1:]
    slug = args.pop(0) if args else "pi-durable"
    stash = Path(args.pop(0)) if args and Path(args[0]).is_dir() else None
    parts = args
    ir_root = Path("books") / slug / "ir"

    if not parts:
        parts = [p.stem for p in sorted(ir_root.glob("*.json"))
                 if not p.name.endswith(".meta.json")]

    # The translations live in the pre-rebuild IR, matched to the *old* node boundaries;
    # normalize produces new boundaries, so that copy is what carries them over. Falling
    # back to the current IR keeps a first run working, before anything is rebuilt.
    stash = stash or Path(".scratch") / f"{slug}-ir-before-tables"
    stash.mkdir(parents=True, exist_ok=True)
    for part in parts:
        src = stash / f"{part}.json"
        if not src.exists() and (ir_root / f"{part}.json").exists():
            shutil.copy(ir_root / f"{part}.json", src)

    total_rows = 0
    for part in parts:
        work = ir_root / part
        if not work.is_dir():
            print(f"{part}: no content.json, skipped")
            continue
        r = subprocess.run([PY, "tools/pdf2html/normalize.py", str(work)],
                           capture_output=True, text=True)
        if r.returncode:
            print(f"{part}: normalize failed\n{r.stderr[-400:]}")
            continue
        # normalize rewrites the working copy; the committed IR is what the rest reads
        shutil.copy(work / "ir.json", ir_root / f"{part}.json")

        # Headings, ledes and paragraphs keep their translations through normalize's
        # text-based snapshot; only the table rows are new, and those are handled next.
        snap = rebuild.snapshot(stash / f"{part}.json")
        kept = rebuild.restore(ir_root / f"{part}.json", snap)

        r = subprocess.run([PY, "tools/table_zh.py", slug, part,
                            str(stash / f"{part}.json")],
                           capture_output=True, text=True)
        print(f"{part}: {r.stdout.strip() or r.stderr[-300:]} ({kept} other nodes)")

    print(f"stash: {stash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())