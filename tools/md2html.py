#!/usr/bin/env python
"""
Render a translated Markdown part into a standalone HTML page.

Used for books whose translation unit is Markdown (Pi Technical Manual) rather than the
structured IR that the PDF extractor produces (Pi Durable). The page reuses the same
stylesheet as the IR pipeline, so both books look identical.

Markdown is rendered with the stdlib only — no third-party dependency. What it supports is
exactly what these files contain: ATX headings, fenced code, pipe-free HTML tables, images,
inline code, bold/italic, blockquotes, lists and rules. Table cells may already contain
inline markup, which is why they are emitted as raw HTML rather than escaped.

Usage:
    python tools/md2html.py books/pi-manual/md/parts --out site/pi-manual
"""

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "tools" / "pdf2html" / "style.css"

CODE_LANG = re.compile(r'^```(\w+)')
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
ULIST = re.compile(r"^[-*]\s+(.*)$")
OLIST = re.compile(r"^\d+[.、]\s+(.*)$")
INLINE_CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITALIC = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?!\*)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def inline(text: str) -> str:
    """Escape, then re-apply the inline markup. Code spans go first so their contents
    are never treated as emphasis."""
    placeholders = []

    def stash(m):
        placeholders.append(m.group(1))
        return f"\x00{len(placeholders) - 1}\x00"

    text = INLINE_CODE.sub(stash, text)
    out = html.escape(text, quote=False)
    out = BOLD.sub(r"<strong>\1</strong>", out)
    out = ITALIC.sub(r"<em>\1</em>", out)
    out = LINK.sub(r'<a href="\2">\1</a>', out)
    for i, code in enumerate(placeholders):
        out = out.replace(f"\x00{i}\x00", f"<code>{html.escape(code, quote=False)}</code>")
    return out


def render_table(block: str) -> str:
    """Emit an HTML table unchanged apart from inline formatting in each cell.

    The source tables come from MinerU already well-formed; re-building them from pipe
    syntax would only risk losing the cell contents.
    """
    rows = re.findall(r"<tr>(.*?)</tr>", block, re.S)
    if not rows:
        return block
    out = ["<table>"]
    for i, row in enumerate(rows):
        cells = re.findall(r"<td>(.*?)</td>", row, re.S)
        tag = "th" if i == 0 else "td"
        out.append("<tr>" + "".join(
            f"<{tag}>{inline(c.strip())}</{tag}>" for c in cells) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def render(md: str, title: str, part_label: str, part_num: str, home: str) -> str:
    body = []
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    headings: list[tuple[str, str]] = []
    para: list[str] = []

    def flush_para():
        if para:
            body.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            if in_code:
                cls = f' class="lang-{code_lang}"' if code_lang else ""
                body.append(f"<pre><code{cls}>"
                            + html.escape("\n".join(code_buf), quote=False)
                            + "</code></pre>")
                code_buf.clear()
                in_code = False
            else:
                flush_para()
                m = CODE_LANG.match(line)
                code_lang = (m.group(1) if m else "").lower()
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if line.strip().startswith("<table>"):
            flush_para()
            buf = []
            depth = 0
            while i < len(lines):
                buf.append(lines[i])
                depth += lines[i].count("<table>") - lines[i].count("</table>")
                i += 1
                if depth <= 0:
                    break
            body.append(render_table("\n".join(buf)))
            continue

        if not line.strip():
            flush_para()
            i += 1
            continue

        m = HEADING.match(line)
        if m:
            flush_para()
            level = len(m.group(1))
            text = m.group(2).strip()
            # "## 3.1 The agent loop" followed by "## 3.1 智能体循环" — the pair is one
            # chapter. Render the Chinese as the heading and keep the English beside it,
            # so the reader sees one title rather than two.
            num = re.match(r"^([\d]+(?:\.\d+)*)\s+(.*)$", text)
            if level == 2 and num:
                n, t = num.group(1), num.group(2)
                anchor = f"sec-{n.replace('.', '-')}"
                zh_t = None
                # peek past a blank line: the translated title sits below the English
                # one as its own heading of the same level
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    nm = HEADING.match(lines[j].strip())
                    if nm and len(nm.group(1)) == level:
                        zh_t = re.sub(r"^[\d.]+\s+", "", nm.group(2).strip())
                        i = j          # consume the blank lines and the translated title
                shown = zh_t or t
                body.append(f'<h2 id="{anchor}">'
                            f'<span class="secnum">{n}</span>{inline(shown)}</h2>')
                if zh_t:
                    body.append(f'<p class="en-title">{inline(t)}</p>')
                headings.append((n, shown))
                i += 1
                continue
            if level == 2:
                anchor = "sec-" + re.sub(r"[^\w\u4e00-\u9fff]+", "-", text)[:40].strip("-")
                if re.match(r"^[\d.]+\s", text):
                    pass                      # numbered chapter handled above
                body.append(f'<h3 id="{anchor}">{inline(text)}</h3>')
            elif level == 1:
                body.append(f"<h2>{inline(text)}</h2>")
            else:
                body.append(f"<h{level + 1}>{inline(text)}</h{level + 1}>")
            i += 1
            continue

        if ULIST.match(line) or OLIST.match(line):
            flush_para()
            ordered = bool(OLIST.match(line))
            items = []
            while i < len(lines) and (ULIST.match(lines[i]) or OLIST.match(lines[i])):
                mm = ULIST.match(lines[i]) or OLIST.match(lines[i])
                items.append(f"<li>{inline(mm.group(1))}</li>")
                i += 1
            tag = "ol" if ordered else "ul"
            body.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue

        if line.startswith(">"):
            flush_para()
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").rstrip())
                i += 1
            body.append('<div class="note"><p>'
                        + inline(" ".join(x for x in buf if x.strip()))
                        + "</p></div>")
            continue

        if re.fullmatch(r"-{3,}|\*{3,}", line.strip()):
            flush_para()
            body.append("<hr>")
            i += 1
            continue

        img = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", line.strip())
        if img:
            flush_para()
            body.append(f'<figure><img src="{img.group(2)}" alt="{img.group(1)}" '
                        f'loading="lazy"></figure>')
            i += 1
            continue

        para.append(line.strip())
        i += 1

    flush_para()
    if in_code and code_buf:
        body.append("<pre><code>" + html.escape("\n".join(code_buf), quote=False)
                     + "</code></pre>")

    toc = ""
    chapters = [(n, t) for n, t in headings if re.match(r"^\d+\.\d+$", n)]
    if chapters:
        items = "\n".join(
            f'<li><a href="#sec-{n.replace(".", "-")}">'
            f'<span class="num">{n}</span>{inline(t)}</a></li>'
            for n, t in chapters)
        toc = f'<nav class="toc"><h2>本章目录</h2>{items}</nav>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · Pi 技术手册</title>
<link rel="stylesheet" href="style.css">
<style>
h2 {{
  display: flex; align-items: baseline; gap: 12px;
}}
.secnum {{
  font-family: var(--mono); font-size: 13px; color: var(--accent);
  flex: 0 0 auto; letter-spacing: .02em;
}}
.en-title {{
  margin: -8px 0 24px; font-family: var(--sans); font-size: 15px;
  color: var(--faint); font-style: italic;
}}
td, th {{
  border: 1px solid var(--rule); padding: 8px 11px;
  font-size: 14px; line-height: 1.55; vertical-align: top; text-align: left;
}}
th {{ background: var(--tint); font-weight: 600; }}
table {{ border-collapse: collapse; width: 100%; margin: 26px 0; font-size: 14px; }}
hr {{ border: 0; border-top: 1px solid var(--rule); margin: 40px 0; }}
pre code {{ font-size: 13px; }}
</style>
</head>
<body>
<main class="page">
<div class="part-nav">
  <span>{html.escape(part_label)}</span>
  <span><a href="{home}">← 返回全书目录</a></span>
</div>
{toc}
{chr(10).join(body)}
</main>
</body>
</html>
"""


def main():
    src_dir = Path(sys.argv[1])
    out_root = Path(sys.argv[2])
    cfg = json.loads((ROOT / "books" / "pi-manual" / "book.json").read_text(encoding="utf-8"))
    meta = {p["slug"]: p for p in cfg["parts"]}

    written = 0
    for md in sorted(src_dir.glob("*.md")):
        part = meta.get(md.stem)
        if not part:
            print(f"skip {md.name} (not in book.json)")
            continue
        out = out_root / md.stem
        out.mkdir(parents=True, exist_ok=True)
        page = render(md.read_text(encoding="utf-8"),
                      part["title_zh"],
                      f"第 {part['num_zh']} 部分 · {part['label_zh']}",
                      part["num_zh"], "../../index.html")
        (out / "index.html").write_text(page, encoding="utf-8")
        shutil.copy(STYLE, out / "style.css")
        img_src = ROOT / "books" / "pi-manual" / "md" / "images"
        if img_src.is_dir() and not (out / "images").exists():
            shutil.copytree(img_src, out / "images")
        written += 1
        print(f"{md.stem:18s} -> {out}")

    print(f"wrote {written} part(s)")


if __name__ == "__main__":
    import json
    main()