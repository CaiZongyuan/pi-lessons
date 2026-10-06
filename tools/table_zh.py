"""Reattach the reference tables' Chinese, split back onto the individual rows.

Appendix R's tables arrive from the extractor as: one block holding several rows' English
stacked at the same x, and a node whose `zh` is the Chinese for that same run. Rendering
that literally wraps prose in a code fence, which is what this appendix used to look like.
`normalize.py` fixes the English by grouping blocks into `table-row` nodes; the Chinese is
the harder half.

The Chinese cannot be re-paired by page (one page holds several blobs), nor by text
similarity (a blob that covers six rows reads like every one of them). What it does have
is structure: **each row's translation opens with that row's signature in backticks**, in
source order. So the blob's own signature list *is* the row list — the rows it describes
are found by looking those signatures up among the detected rows, rather than by assuming
the blob lines up with a fixed span of them.

A signature the blob names but no row has means the two have drifted apart; the blob is
then left unattached rather than guessed at.
"""

import json
import re
import sys
from pathlib import Path

SIGNATURE = re.compile(r"`([^`]+)`")
POINTER_ONLY = re.compile(r"^[\d.]+\s*(\(p\.\s*\d+\))?$")


def signature_of(text: str) -> str:
    """The identifier that opens a row: `createSession (storage) a bare …` → createSession."""
    m = re.match(r"\s*([A-Za-z_][\w]*)", text)
    return m.group(1) if m else ""


def row_signature(row: dict) -> str:
    for cell in row.get("cells", []):
        c = cell.strip()
        if not c or POINTER_ONLY.match(c):
            continue
        sig = signature_of(c)
        if sig:
            return sig
    return ""


def blob_cuts(blob: str) -> list[tuple[int, str]]:
    """Where each row's translation starts, as (offset, signature) in source order.

    Only the *first* mention of each signature counts: a row's prose goes on to refer to
    its own return type and section pointer, and cutting there would split the row.
    """
    cuts: list[tuple[int, str]] = []
    seen: set[str] = set()
    for m in SIGNATURE.finditer(blob):
        sig = signature_of(m.group(1))
        if sig and sig not in seen:
            seen.add(sig)
            cuts.append((m.start(), sig))
    return cuts


def main() -> int:
    slug, part = sys.argv[1], sys.argv[2]
    prev_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    target = Path("books") / slug / "ir" / f"{part}.json"
    ir = json.loads(target.read_text(encoding="utf-8"))
    rows = [n for n in ir["nodes"] if n["type"] == "table-row"]
    for r in rows:
        r["_sig"] = row_signature(r)
        r["zh"] = None

    if not prev_path or not prev_path.exists():
        print(f"{len(rows)} rows, no previous IR to take translations from")
        return 0

    prev = json.loads(prev_path.read_text(encoding="utf-8"))
    blobs = [(n.get("page"), (n.get("zh") or "").strip()) for n in prev["nodes"]
             if (n.get("zh") or "").strip()]

    hit = 0
    orphaned = 0
    for page, blob in blobs:
        # Restrict the lookup to this blob's own page. Without that, a signature such as
        # `Harness` — which heads the glossary and is quoted in a dozen rows' prose — pulls
        # a translation out of an unrelated table and hands it to the wrong row.
        local = {r["_sig"]: r for r in rows if r.get("page") == page and r["_sig"]}
        cuts = blob_cuts(blob)
        if not cuts:
            continue
        if len(cuts) == 1:
            sig = cuts[0][1]
            row = local.get(sig)
            if row and not row.get("zh") and len(blob) > 12:
                row["zh"] = blob
                hit += 1
            continue

        for i, (pos, sig) in enumerate(cuts):
            end = cuts[i + 1][0] if i + 1 < len(cuts) else len(blob)
            piece = blob[pos:end].strip()
            row = local.get(sig)
            if row is None:
                orphaned += 1
                continue
            # a row already translated by an earlier blob keeps the shorter, more specific
            # piece: two blobs can both cover a row, and the one naming fewer siblings is
            # the one that was written for it
            if row.get("zh") and len(row["zh"]) <= len(piece):
                continue
            row["zh"] = piece
            hit += 1

    target.write_text(json.dumps(ir, ensure_ascii=False, indent=1), encoding="utf-8")
    done = sum(1 for r in rows if r.get("zh"))
    print(f"{len(rows)} rows, {done} translated ({hit} pieces, {orphaned} unmatched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())