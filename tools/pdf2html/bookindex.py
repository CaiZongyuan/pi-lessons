"""Build site/index.html — the landing page listing every book and its chapters.

Reads books/*/book.json plus each part's translated IR, so chapter titles come from the
translations rather than being hardcoded.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BOOKS = ROOT / "books"
SITE = ROOT / "site"
PIPELINE = Path(__file__).resolve().parent


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def part_summary(ir_path: Path, meta: dict) -> str:
    """The part standfirst: meta if a translator filled it, else the h2 after the title."""
    if meta.get("part_sub_zh"):
        return meta["part_sub_zh"]
    if not ir_path.exists():
        return ""
    d = load(ir_path)
    for n in d["nodes"][1:3]:
        if n["type"] == "h2":
            return n.get("zh") or n.get("text", "")
    return ""


def chapters_of(ir_path: Path):
    if not ir_path.exists():
        return []
    out = []
    for n in load(ir_path)["nodes"]:
        if n["type"] == "chapter-title":
            zh = n.get("zh") or n.get("text", "")
            m = re.match(r"([\d.R]+)\s+(.*)", zh)
            out.append((m.group(1), m.group(2)) if m else ("", zh))
    return out


def main():
    SITE.mkdir(exist_ok=True)
    sections, total_parts, total_ch = [], 0, 0

    # Pi before Durable: it is the primary tutorial, Durable is the follow-up deep dive
    order = {"pi-manual": 0, "pi-durable": 1}
    book_dirs = sorted(BOOKS.iterdir(),
                       key=lambda p: order.get(
                           json.loads((p / "book.json").read_text(encoding="utf-8"))["id"]
                           if (p / "book.json").exists() else "", 99))

    for b in book_dirs:
        cfg_path = b / "book.json"
        if not cfg_path.exists():
            continue
        cfg = load(cfg_path)
        book_blocks, ch_total = [], 0

        for p in cfg["parts"]:
            total_parts += 1
            ir = b / "ir" / f"{p['slug']}.json"
            meta_p = b / "ir" / f"{p['slug']}.meta.json"
            meta = load(meta_p) if meta_p.exists() else {}
            chs = chapters_of(ir)
            ch_total += len(chs)
            total_ch += len(chs)

            if chs:
                items = "\n".join(
                    f'      <li><a href="{cfg["id"]}/{p["slug"]}/index.html">'
                    f'<span class="num">{cnum}</span>{esc(ctitle)}</a></li>'
                    for cnum, ctitle in chs
                )
                lis = f'\n    <ol class="ch-list">\n{items}\n    </ol>\n'
            else:
                lis = ('\n    <p class="todo">待翻译 · '
                       f'{p["first_page"]}–{p["last_page"]} 页</p>\n')

            book_blocks.append(f"""  <details class="toc-part">
    <summary>
      <span class="part-badge">第 {p['num_zh']} 部分</span>
      <span class="part-name">{esc(p['title_zh'])}</span>
      <span class="part-count">{len(chs)} 章</span>
    </summary>
    <p class="part-note">{esc(part_summary(ir, meta))}</p>{lis}  </details>""")

        subtitle = cfg.get("subtitle_zh", "")
        sections.append(f"""<section class="book" id="{cfg['id']}">
  <header class="book-head">
    <h2>{esc(cfg['title_zh'])}</h2>
    <p class="sub">{esc(subtitle)}</p>
    <p class="meta">{esc(cfg['title_en'])} · {len(cfg['parts'])} 部分 · {ch_total} 章</p>
  </header>
{chr(10).join(book_blocks)}
</section>""")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pi Lessons · 技术手册</title>
<link rel="stylesheet" href="style.css">
<style>
.page {{ max-width: 900px; }}
.masthead {{
  margin: 0 0 54px; padding: 84px 0 34px;
  border-top: 3px solid var(--ink);
}}
.masthead .kicker {{
  font-family: var(--sans); font-size: 12.5px; font-weight: 700;
  letter-spacing: .3em; text-transform: uppercase; color: var(--accent);
  display: block; margin-bottom: 16px;
}}
.masthead h1 {{ font-size: 56px; line-height: 1.05; margin: 0 0 18px; font-weight: 700; letter-spacing: -.02em; }}
.masthead .sub {{
  font-size: 19px; line-height: 1.65; color: var(--muted);
  font-style: italic; margin: 0 0 18px; max-width: 34em;
}}
.masthead .meta {{
  font-family: var(--sans); font-size: 12.5px; color: var(--faint); letter-spacing: .08em;
}}
.book {{ margin: 0 0 52px; scroll-margin-top: 24px; }}
.book-head {{ margin: 0 0 22px; }}
.book-head h2 {{ font-size: 30px; margin: 0 0 8px; font-weight: 700; }}
.book-head .sub {{ margin: 0 0 8px; font-size: 15.5px; color: var(--muted); font-style: italic; }}
.book-head .meta {{ margin: 0; font-family: var(--sans); font-size: 12px; color: var(--faint); letter-spacing: .06em; }}
.toc-part {{
  margin: 0 0 10px; padding: 0 26px;
  background: var(--panel); border: 1px solid var(--rule); border-radius: 2px;
}}
.toc-part summary {{
  cursor: pointer; padding: 15px 0; list-style: none;
  display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap;
}}
.toc-part summary::-webkit-details-marker {{ display: none; }}
.toc-part summary::after {{
  content: "▸"; margin-left: auto; color: var(--faint); font-size: 12px;
}}
.toc-part[open] summary::after {{ content: "▾"; }}
.part-badge {{
  font-family: var(--sans); font-size: 10.5px; font-weight: 700;
  letter-spacing: .18em; text-transform: uppercase; color: var(--accent);
}}
.part-name {{ font-family: var(--sans); font-size: 16px; font-weight: 500; }}
.part-count {{ font-family: var(--mono); font-size: 11.5px; color: var(--faint); margin-left: auto; }}
.part-note {{
  margin: 0 0 14px; font-size: 14.5px; line-height: 1.6; color: var(--muted); max-width: 48em;
}}
.ch-list {{ margin: 0 0 18px; padding: 14px 0 0; list-style: none; border-top: 1px solid var(--rule); }}
.ch-list li {{ margin: 0; padding: 0; }}
.ch-list li::before {{ display: none; }}
.ch-list a {{
  display: flex; gap: 12px; align-items: baseline; padding: 5px 0;
  font-family: var(--sans); font-size: 14px; color: var(--ink); text-decoration: none;
}}
.ch-list a:hover {{ color: var(--accent); }}
.ch-list .num {{
  font-family: var(--mono); font-size: 12px; color: var(--accent);
  flex: 0 0 2.8em; text-align: right;
}}
.todo {{ margin: 0 0 16px; font-family: var(--mono); font-size: 12.5px; color: var(--faint); }}
</style>
</head>
<body>
<main class="page">
  <header class="masthead">
    <span class="kicker">Pi Lessons</span>
    <h1>Pi 技术手册</h1>
    <p class="sub">把英文技术手册翻译成可在线阅读的中文版，保留原版排版、图表与代码格式。</p>
    <p class="meta">{len(sections)} 本手册 · {total_parts} 个部分 · {total_ch} 章 · 简体中文版</p>
  </header>
{chr(10).join(sections)}
</main>
</body>
</html>
"""
    (SITE / "index.html").write_text(html, encoding="utf-8")
    (SITE / "style.css").write_text(
        (PIPELINE / "style.css").read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote site/index.html — {len(sections)} books, {total_parts} parts, {total_ch} chapters")


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


if __name__ == "__main__":
    main()
