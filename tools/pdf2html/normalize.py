"""
Turn raw block dumps into a clean document IR: paragraphs, lists, code, figures.

The PDF gives us one text block per *line* (Paged.js emits each line separately), so the
main job here is re-joining lines into paragraphs and telling body copy from list items.
Geometry does the work: body text starts at x=57.6, list items are indented to x=71.6.

Output IR node types: part, chapter, h2, h3, lede, p, ul, code, figure, callout, small.
"""

import json
import re
import sys
from pathlib import Path

BODY_X = 57.6
LIST_X = 71.6
LINE_H = 14.3          # body leading, used as the "same paragraph" test
COL_GAP = 16.0         # vertical gap that starts a new block


def load(path):
    return json.load(open(path, encoding="utf-8"))


# ---------------------------------------------------------------- inline markup
CODE_RE = re.compile(
    r"(`[^`]+`"
    r"|\b(?:src|test|research|docs)/[\w./-]+"
    r"|\b[\w.-]+\.(?:ts|tsx|js|json|txt|md|sqlite|jsonl|bt)\b"
    r"|\bpi\.[a-z][\w.]*"
    r"|\b[A-Z][A-Za-z]*(?:Storage|Session|Conversation|Registry|Task|Run|Document|Entry|Commit|Options|Env)\b"
    r"|\u00a7\s?[\w.\u00a7]+"
    r"|\bcreateSession\b|\bHarness\b|\bChord\b|\bSQLite\b)"
)


def inline(text: str) -> str:
    """Mark up code-ish runs so the HTML can style them without touching the wording."""
    if not text:
        return ""
    parts = []
    last = 0
    for m in CODE_RE.finditer(text):
        if m.start() < last:
            continue
        parts.append(text[last:m.start()])
        tok = m.group(0)
        if tok.startswith("`"):
            parts.append(f"<code>{tok[1:-1]}</code>")
        elif tok.startswith("§"):
            parts.append(f'<a class="spec" href="#ref">{tok}</a>')
        else:
            parts.append(f"<code>{tok}</code>")
        last = m.end()
    parts.append(text[last:])
    return "".join(parts).strip()


def clean(text: str) -> str:
    """Repair the spacing artefacts that justified multi-span lines leave behind.

    Text is handed to us one line per block, so the only things to fix are:
    double spaces, hyphens broken across line ends, and the occasional space that
    vanished where two spans abut mid-word.
    """
    t = text.replace("\n", " ")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(\w)- (\w)", r"\1-\2", t)          # "deploy- ing" -> "deploy-ing"
    t = re.sub(r"([~`]) (\.)", r"\1\2", t)                    # "~ /." -> "~/."
    t = re.sub(r"(\w) \.(ts|tsx|js|json|md|txt|py)\b", r"\1.\2", t)
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    return t.strip()


# TOC lines on a part-opening page look like "1.1  What Pi Durable is for  10"
TOC_RE = re.compile(r"^\d+\.\d+\s*\S.*\s\d{1,3}$")
FURNITURE_RE = re.compile(r"^[A-Z](?:\s+[A-Z])+\s+[A-Z]$")  # letter-spaced footer


# ---------------------------------------------------------------- block grouping
def merge_blocks(pages):
    """Re-join per-line blocks into semantic nodes."""
    nodes = []
    pending = None       # accumulating paragraph lines
    pending_kind = None

    def flush():
        nonlocal pending, pending_kind
        if pending:
            nodes.append({"type": pending_kind, "text": " ".join(pending)})
        pending, pending_kind = None, None

    for page in pages:
        pno = page["page"]
        blocks = sorted(page["blocks"], key=lambda b: (b["bbox"][1], b["bbox"][0]))
        for b in blocks:
            role, x, y, txt = b["role"], b["bbox"][0], b["bbox"][1], b["text"]

            # running heads / folios
            if role == "small" and (y < 55 or y > 735):
                continue
            if role == "small" and re.fullmatch(r"[\d\s]+", txt):
                continue

            txt = clean(txt)

            if role == "small" and (TOC_RE.match(txt) or FURNITURE_RE.match(txt)):
                continue
            if role == "small" and txt.isupper() and len(txt) > 12:
                continue

            # A heading / lede / caption can wrap across lines. Only start a new node
            # when the role changes or the vertical gap says a new block began.
            if role in ("part-title", "chapter-title", "h2", "h3", "small"):
                kind = "lede" if role == "h3" else role
                if (
                    nodes
                    and nodes[-1]["type"] == kind
                    and nodes[-1].get("page") == pno
                    and y - nodes[-1]["_last_y"] < COL_GAP * 1.9
                    and kind not in ("part-title", "chapter-title")
                ):
                    nodes[-1]["text"] += " " + txt
                    nodes[-1]["_last_y"] = y
                    continue
                flush()
                nodes.append({"type": kind, "text": txt, "page": pno, "_last_y": y})
                continue
            if role == "code":
                flush()
                nodes.append({"type": "code", "lines": [txt], "page": pno})
                continue

            # body-ish: list item if indented
            kind = "li" if x > (BODY_X + 6) else "p"

            # A list item is exactly one line in this book, so never merge two of them.
            if pending is not None and pending_kind == "li":
                flush()
            elif pending is not None and pending_kind == kind:
                gap = y - pending_y
                if gap < COL_GAP * 1.9:
                    pending.append(txt)
                    pending_y = y
                    continue
            flush()
            pending, pending_kind, pending_y = [txt], kind, y

        # figures are anchored by page; insert them in reading order
    flush()
    return nodes


def attach_figures(nodes, pages):
    """Re-insert figure nodes at their page position."""
    by_page = {}
    for page in pages:
        for f in page.get("figures", []):
            if f.get("caption"):
                by_page.setdefault(f["number"], f)
    manifest = json.load(open(Path(nodes[0]["_dir"]) / "figures.json", encoding="utf-8"))
    meta = {m["number"]: m for m in manifest}

    out = []
    for n in nodes:
        pno = n.get("page")
        for num, f in by_page.items():
            m = meta.get(num)
            if m and m["page"] == pno and not any(
                o.get("type") == "figure" and o.get("number") == num for o in out
            ):
                out.append({
                    "type": "figure",
                    "number": num,
                    "file": m["file"],
                    "title": m["title"],
                    "caption": f["caption"],
                    "page": pno,
                })
        out.append(n)
    return out


def split_caption_lines(nodes):
    """A code listing's trailing prose is a figure caption, not code.

    PyMuPDF cannot tell the two apart (both are small type), so a caption line often
    lands as the last line of the listing. Real code can also *continue* past what looks
    like prose, so we only strip a trailing run when it is unambiguously English: it
    must start with a capital letter, contain no code punctuation, and be long enough
    to be a sentence rather than a wrapped code line.
    """
    for i, n in enumerate(nodes):
        if n["type"] != "code" or not n.get("lines"):
            continue
        tail = []
        while n["lines"] and looks_like_prose(n["lines"][-1]):
            tail.insert(0, n["lines"].pop())
        if tail:
            nodes.insert(i + 1, {"type": "small", "text": " ".join(tail),
                                 "page": n.get("page")})


def looks_like_prose(line: str) -> bool:
    s = line.strip()
    # A code listing that wrapped across a page boundary resumes mid-statement, so its
    # continuation line has no leading capital and is full of code punctuation. Those
    # must never be mistaken for a caption.
    if not s or not s[0].isupper():
        return False
    if len(s) < 45:
        return False
    if s.count("{") != s.count("}") or s.count("[") != s.count("]"):
        return False
    if s.count('"') % 2 or s.count("(") != s.count(")"):
        return False
    if re.search(r"[<>=;|&${}]|=>|\bconst\b|\bfunction\b", s):
        return False
    words = s.split()
    if len(words) < 8:
        return False
    letters = sum(c.isalpha() or c == " " for c in s)
    return letters / len(s) > 0.85


def reattach_code_fragments(nodes):
    """Pull stray code lines back into the listing they belong to.

    A long listing that spans a page break is emitted as two separate code nodes with a
    prose-looking line wedged between them. Any `small` node that is really a wrapped
    continuation of code (no capitalised opening, unbalanced brackets, code punctuation)
    is moved back onto the end of the preceding code node.
    """
    out = []
    for n in nodes:
        if n["type"] == "small" and out and out[-1]["type"] == "code" \
                and is_code_fragment(n.get("text", "")):
            out[-1]["lines"].append(n["text"].strip())
            continue
        out.append(n)
    nodes[:] = out


def is_code_fragment(text: str) -> bool:
    s = text.strip()
    if not s or s[0].isupper():
        return False
    if re.search(r"[<>=;|&${}]|=>|\bconst\b|\bfunction\b|\bas\b", s):
        return True
    # unbalanced brackets: a listing cut mid-statement
    return s.count("{") != s.count("}") or s.count("(") != s.count(")")


def normalize(src_dir: Path):
    data = load(src_dir / "content.json")
    nodes = merge_blocks(data["pages"])
    for n in nodes:
        n["_dir"] = str(src_dir)
    nodes = attach_figures(nodes, data["pages"])
    for n in nodes:
        n.pop("_dir", None)

    # figures -> keep caption, drop the duplicated heading line
    for n in nodes:
        if n["type"] == "figure":
            n["caption"] = clean(n["caption"])

    # merge runs of consecutive code lines back into single listings
    merged = []
    for n in nodes:
        if n["type"] == "code" and merged and merged[-1]["type"] == "code" \
                and merged[-1]["page"] == n["page"] and \
                n["page"] - merged[-1]["_last_page"] <= 1:
            merged[-1]["lines"].extend(n["lines"])
            merged[-1]["_last_page"] = n["page"]
            continue
        n["_last_page"] = n.get("page")
        merged.append(n)

    split_caption_lines(merged)
    reattach_code_fragments(merged)

    merged = [{k: v for k, v in n.items() if not k.startswith("_")} for n in merged]
    out = src_dir / "ir.json"
    out.write_text(json.dumps({"nodes": merged}, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("nodes:", len(merged), Counter(n["type"] for n in merged))
    return merged


if __name__ == "__main__":
    normalize(Path(sys.argv[1]))