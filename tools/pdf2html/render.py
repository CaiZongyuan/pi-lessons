"""
Render an IR file into a standalone HTML part.

The renderer is deliberately translation-aware: subagents fill in `zh` fields on the IR
nodes (headings, paragraphs, list items, captions, callouts). Anything without a `zh`
falls back to the English source, so a partially translated part still renders correctly.

Usage: python render.py <ir_dir> <out_html> [--title "..."]
"""

import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def linkify(text: str) -> str:
    """Escape, then re-apply the inline markup recorded in the IR."""
    out = esc(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"§\s?([\w.§]+)", r'<a class="spec" href="#ref">§\1</a>', out)
    # bare source paths and API names that were not back-ticked in the source
    out = re.sub(
        r"(?<![\w/])((?:src|test|research|docs)/[\w./-]+)",
        r"<code>\1</code>", out,
    )
    out = re.sub(r"(?<![\w.])(\bpi\.[a-z][\w.]*)", r"<code>\1</code>", out)
    return out


def highlight(code: str, lang: str = "") -> str:
    """Minimal, dependency-free syntax highlighting.

    Implemented as a single left-to-right token scan rather than successive regex
    passes: nesting replacements would wrap already-emitted spans (producing
    `<span class="k"><span class="k">`), whereas one pass keeps every tag balanced.
    """
    if not code:
        return ""

    TOKEN = re.compile(
        r"(?P<comment>//[^\n]*)"
        r"|(?P<string>\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)"
        r"|(?P<number>\b\d+(?:\.\d+)?\b)"
        r"|(?P<key>\"(?:[^\"\\\n]|\\.)*\"(?=\s*:))"
        r"|(?P<word>[A-Za-z_$][\w$]*)"
    )
    KEYWORDS = {
        "const", "let", "var", "await", "async", "function", "return", "export",
        "import", "from", "type", "interface", "new", "if", "else", "for", "of",
        "in", "class", "extends", "throw", "try", "catch", "true", "false",
        "null", "undefined",
    }
    LITERALS = {"true", "false", "null", "undefined"}

    out = []
    pos = 0
    for m in TOKEN.finditer(code):
        out.append(esc(code[pos:m.start()]))
        pos = m.end()
        kind = m.lastgroup
        text = m.group(0)
        if kind == "comment":
            out.append(f'<span class="c">{esc(text)}</span>')
        elif kind == "key":
            out.append(f'<span class="k">{esc(text)}</span>')
        elif kind == "string":
            out.append(f'<span class="s">{esc(text)}</span>')
        elif kind == "number":
            out.append(f'<span class="n">{esc(text)}</span>')
        elif kind == "word":
            if text in KEYWORDS:
                cls = "b" if text in LITERALS else "k"
                out.append(f'<span class="{cls}">{esc(text)}</span>')
            else:
                out.append(esc(text))
        else:
            out.append(esc(text))
    out.append(esc(code[pos:]))
    return "".join(out)


def guess_lang(lines) -> str:
    blob = "\n".join(lines)
    if re.search(r'^\s*"[\w]+"\s*:', blob, re.M) or blob.strip().startswith("{"):
        return "json"
    if re.search(r"\b(const|await|function|=>)\b", blob):
        return "ts"
    return ""


def pick(node, field="text"):
    """Prefer the Chinese translation, fall back to English."""
    zh = node.get("zh")
    if isinstance(zh, dict):
        return zh.get(field) or zh.get("text") or node.get(field, "")
    return zh or node.get(field, "")


# ---------------------------------------------------------------- node renderers
def similar(a: str, b: str) -> float:
    """How much of the shorter string the longer one already contains (0.0 - 1.0).

    The same caption reaches us twice: once truncated (the figure's own caption block)
    and once complete (the following small-print paragraph). Neither is a plain prefix
    of the other, because truncation happens mid-sentence and the two translations may
    word a boundary differently, so we look for the shorter string anywhere inside the
    longer one.
    """
    def norm(s):
        return re.sub(r"[^\w一-鿿]+", "", s.lower())
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    short, long = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(short) < 10:
        return 0.0
    if short in long:
        return 1.0
    # longest common substring, as a share of the shorter string
    lo, hi, best = 0, len(short), 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if any(short[i:i + mid] in long for i in range(len(short) - mid + 1)):
            best, lo = mid, mid
        else:
            hi = mid - 1
    return best / len(short)


def _last_figure_index(body):
    for i in range(len(body) - 1, -1, -1):
        if body[i].lstrip().startswith("<figure>"):
            return i
    return None


def _figure_with_caption(block: str, caption: str) -> str:
    cap = f"\n  <figcaption>{linkify(caption)}</figcaption>"
    if "<figcaption>" in block:
        return re.sub(r"\n\s*<figcaption>.*?</figcaption>", cap, block, flags=re.S)
    return block.replace("\n</figure>", cap + "\n</figure>")


def render(nodes, css_href, part_label, part_title_zh, part_sub_zh,
           toc=True, part_num_zh="", home_href="../../index.html"):
    body = []
    body_nodes = []
    chapter_no = 0
    chapters = []

    i = 0
    # ---- part opener
    if nodes and nodes[0]["type"] == "part-title":
        n = nodes[0]
        num = re.search(r"PART\s+(\S+)", n["text"])
        num_zh = part_num_zh or (num.group(1) if num else "")
        label = part_label
        if label.startswith("第") and "部分" in label:
            label = label.split("·")[-1].strip()
        body.append(f"""<header class="part-opener">
  <span class="part-no">第 {esc(num_zh)} 部分 · {esc(label)}</span>
  <h1>{esc(part_title_zh or n.get('zh') or n['text'])}</h1>
  <p class="part-sub">{esc(part_sub_zh)}</p>
</header>""")

    # The h2 directly after the part title is the part's standfirst. Skip it so it
    # does not also appear as a section heading further down the page.
    if len(nodes) > 1 and nodes[1]["type"] == "h2":
        nodes = nodes[:1] + nodes[2:]

    while i < len(nodes):
        n = nodes[i]
        t = n["type"]

        if t == "chapter-title":
            if chapter_no:
                body.append("</section>")   # close the previous chapter
            chapter_no += 1
            raw = n["text"]
            m = re.match(r"([\d.]+)\s+(.*)", raw)
            num, title = (m.group(1), m.group(2)) if m else ("", raw)
            # the Chinese title also carries the number ("1.1 xxx"); strip it here
            # because .chapter-num already shows it
            zh = pick(n)
            title = re.sub(r"^[\d.\s]+", "", zh).strip() or title
            chapters.append((num, title))
            sub = ""
            if i + 1 < len(nodes) and nodes[i + 1]["type"] == "lede":
                sub = f'\n  <p class="lede">{linkify(pick(nodes[i + 1]))}</p>'
                i += 1
            # the number is rendered in .chapter-num above the title, so drop the
            # leading "1.1" from the heading itself to avoid showing it twice
            body.append(f"""<section class="chapter" id="ch-{num.replace('.', '-')}">
  <div class="chapter-head">
    <span class="chapter-num">第 {esc(num)} 节</span>
    <h2>{esc(title)}</h2>{sub}
  </div>""")
            i += 1
            continue

        # a run of consecutive list items becomes one <ul>
        if t == "li":
            items = []
            while i < len(nodes) and nodes[i]["type"] == "li":
                items.append(f"    <li>{linkify(pick(nodes[i]))}</li>")
                i += 1
            body.append("  <ul>\n" + "\n".join(items) + "\n  </ul>")
            continue

        if t == "h2":
            body.append(f'  <h3>{linkify(pick(n))}</h3>')
        elif t == "lede":
            pass  # consumed by its chapter
        elif t == "p":
            body.append(f"  <p>{linkify(pick(n))}</p>")
        elif t == "code":
            lines = n.get("lines", [])
            body.append(
                '<pre><code class="lang-%s">%s</code></pre>'
                % (guess_lang(lines), highlight("\n".join(lines), guess_lang(lines)))
            )
        elif t == "figure":
            cap = n.get("zh_caption") or n.get("caption", "")
            cap_html = linkify(cap) if cap else ""
            # the extractor sometimes emits the caption twice (once as the figure's
            # own caption, once as a following small-print block); the renderer
            # suppresses the duplicate rather than showing the reader it twice
            n["_cap"] = cap
            body.append(f"""<figure>
  <img src="{n['file']}" alt="{esc(n.get('title', ''))}" loading="lazy">
  <figcaption>{cap_html}</figcaption>
</figure>""")
        elif t == "small":
            txt = pick(n)
            prev = body_nodes[-1] if body_nodes else None
            if txt and prev and prev.get("_cap") and similar(prev["_cap"], txt) >= 0.6:
                # The same caption arrives twice: truncated as the figure's own caption
                # block, then complete as small print. Replace the caption with the full
                # text instead of showing the reader the same words twice.
                fig_i = _last_figure_index(body)
                if fig_i is not None:
                    body[fig_i] = _figure_with_caption(body[fig_i], txt)
                prev["_cap"] = None
                body_nodes.append(n)
                i += 1
                continue
            if txt:
                body.append(f'  <div class="note"><p>{linkify(txt)}</p></div>')
        if t != "li":
            body_nodes.append(n)

        i += 1

    if chapter_no:
        body.append("</section>")

    toc_html = ""
    if toc and chapters:
        items = "\n".join(
            f'    <li><a href="#ch-{num.replace(".", "-")}">'
            f'<span class="num">{esc(num)}</span>{esc(t)}</a></li>'
            for num, t in chapters
        )
        toc_html = f'<nav class="toc"><h2>本章目录</h2>\n{items}\n</nav>'

    nav = f"""<div class="part-nav">
  <span>{esc(part_label)}</span>
  <span><a href="{home_href}">← 返回全书目录</a></span>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(part_title_zh)} · Pi Durable 技术手册</title>
<link rel="stylesheet" href="{css_href}">
</head>
<body>
<main class="page">
{nav}
{toc_html}
{chr(10).join(body)}
</main>
</body>
</html>
"""


def main():
    ir_dir = Path(sys.argv[1])
    out = Path(sys.argv[2])
    data = json.loads((ir_dir / "ir.json").read_text(encoding="utf-8"))
    meta_path = ir_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    html_out = render(
        data["nodes"],
        meta.get("css", "style.css"),
        meta.get("part_label", "PART"),
        meta.get("part_title_zh", ""),
        meta.get("part_sub_zh", ""),
        toc=meta.get("toc", True),
        part_num_zh=meta.get("part_num_zh", ""),
        home_href=meta.get("home_href", "../../index.html"),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_out, encoding="utf-8")
    print("wrote", out, len(html_out), "bytes")


if __name__ == "__main__":
    main()