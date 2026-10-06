#!/usr/bin/env python
"""
Convert a source PDF to Markdown with the MinerU API (precision / v4 endpoint).

Why this exists: the hand-rolled PyMuPDF extractor in this repo recovers structure from
geometry, which works but is brittle for multi-column tables and reference sections.
MinerU is a purpose-built parser and gives us clean Markdown plus the table structure the
source actually has.

Workflow (MinerU is asynchronous throughout):
    1. POST /api/v4/file-urls/batch     -> signed upload URL(s)
    2. PUT  <file_url>                  -> upload the PDF (or a page slice of it)
    3. poll /api/v4/extract-results/batch/<batch_id>
    4. download full_zip_url, keep full.md

Page limit: the v4 endpoint caps a task at 200 pages, so longer PDFs are sliced with
PyMuPDF into <=200-page chunks and parsed separately.

Usage:
    python tools/pdf2md.py <book-id>                     # whole book
    python tools/pdf2md.py pi-manual --pages 1-30         # a slice, for a quick look
    python tools/pdf2md.py pi-durable --pdf <path>
"""

import argparse
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "books"
API = "https://mineru.net/api/v4"

POLL_SECONDS = 6
TIMEOUT_SECONDS = 60 * 40
CHUNK_PAGES = 190          # stay under the 200-page task cap


def load_key() -> str:
    key = os.environ.get("MINERU_KEY")
    if key:
        return key.strip()
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("MINERU_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("MINERU_KEY not found: set it in the environment or in .env")


def auth(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Accept": "*/*"}


def chunk_ranges(total: int, size: int = CHUNK_PAGES):
    for start in range(1, total + 1, size):
        yield start, min(total, start + size - 1)


def slice_pdf(src: Path, first: int, last: int, dest: Path) -> Path:
    """Write pages [first, last] (1-based, inclusive) of src into dest."""
    import fitz
    doc = fitz.open(str(src))
    out = fitz.open()
    out.insert_pdf(doc, from_page=first - 1, to_page=last - 1)
    out.save(str(dest))
    out.close()
    doc.close()
    return dest


def upload_and_parse(key: str, pdf: Path, name: str) -> str:
    """Upload one PDF and return the batch_id tracking it."""
    r = requests.post(
        f"{API}/file-urls/batch",
        headers={**auth(key), "Content-Type": "application/json"},
        data=json.dumps({"files": [{"name": name, "data_id": name}],
                         "model_version": "vlm", "language": "en"}),
        timeout=60,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("code") not in (0, None):
        sys.exit(f"apply for upload url failed: {body}")
    url = body["data"]["file_urls"][0]
    batch_id = body["data"]["batch_id"]

    with open(pdf, "rb") as fh:
        up = requests.put(url, data=fh, timeout=600)
    up.raise_for_status()
    return batch_id


def poll(key: str, batch_id: str) -> dict:
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        r = requests.get(f"{API}/extract-results/batch/{batch_id}",
                         headers=auth(key), timeout=60)
        r.raise_for_status()
        data = r.json()
        results = (data.get("data") or {}).get("extract_result") or []
        for item in results:
            state = item.get("state")
            if state == "done":
                return item
            if state == "failed":
                sys.exit(f"parse failed: {item.get('err_msg') or item}")
        done = sum(1 for i in results if i.get("state") in ("done", "failed"))
        print(f"    … {done}/{len(results)} chunks done", flush=True)
        time.sleep(POLL_SECONDS)
    sys.exit("timed out waiting for MinerU")


def fetch_markdown(item: dict, dest: Path) -> Path:
    zip_url = item.get("full_zip_url")
    if not zip_url:
        sys.exit(f"no zip url in result: {list(item)[:8]}")
    blob = requests.get(zip_url, timeout=600).content
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = z.namelist()
        md = next((n for n in names if n.endswith("full.md")), None) or \
             next((n for n in names if n.endswith(".md")), None)
        if md is None:
            sys.exit(f"no markdown in zip: {names[:10]}")
        dest.write_bytes(z.read(md))
        # images are referenced as relative paths by the markdown
        for n in names:
            if "/images/" in n or n.startswith("images/"):
                target = dest.parent / Path(n).name
                if not target.exists():
                    target.write_bytes(z.read(n))
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("--pdf", help="override the source PDF path")
    ap.add_argument("--pages", help="only parse this range, e.g. 1-30")
    ap.add_argument("--out", help="output directory (default books/<id>/md)")
    a = ap.parse_args()

    bdir = BOOKS / a.book
    cfg = json.loads((bdir / "book.json").read_text(encoding="utf-8"))

    src = Path(a.pdf) if a.pdf else Path(
        os.environ.get("PI_PDF", ROOT / "source")) / cfg["source"]["filename"]
    if not src.is_file():
        sys.exit(f"PDF not found: {src}\n  set PI_PDF or pass --pdf")

    out_dir = Path(a.out) if a.out else bdir / "md"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "_chunks"
    tmp.mkdir(exist_ok=True)

    if a.pages:
        first, _, last = a.pages.partition("-")
        ranges = [(int(first), int(last or first))]
    else:
        import fitz
        ranges = list(chunk_ranges(fitz.open(str(src)).page_count))

    key = load_key()
    print(f"{a.book}: {src.name} -> {len(ranges)} chunk(s)")

    for i, (lo, hi) in enumerate(ranges, 1):
        tag = f"{lo}-{hi}"
        md_path = out_dir / f"{tag}.md"
        if md_path.exists() and md_path.stat().st_size > 200:
            print(f"  [{i}/{len(ranges)}] p{tag} already done, skip")
            continue
        print(f"  [{i}/{len(ranges)}] p{tag} …", flush=True)

        pdf = src if len(ranges) == 1 and (lo, hi) == (1, 10**9) else \
            slice_pdf(src, lo, hi, tmp / f"{tag}.pdf")
        batch_id = upload_and_parse(key, pdf, f"{a.book}-{tag}.pdf")
        item = poll(key, batch_id)
        fetch_markdown(item, md_path)
        print(f"      -> {md_path.relative_to(ROOT)} "
              f"({md_path.stat().st_size // 1024} KB)")

    print("done")


if __name__ == "__main__":
    main()