"""Verify translated Markdown against the pre-translation baseline in git.

Every structural count must be unchanged: a lost code fence or table means the
translation dropped content, which is the failure mode worth catching before publishing.
"""
import re
import subprocess
import sys
from pathlib import Path

PARTS = sorted(Path("books/pi-manual/md/parts").glob("*.md"))


def stats(text: str):
    return {
        "blocks": text.count("```") // 2,
        "tables": text.count("<table>"),
        "images": len(re.findall(r"!\[\]", text)),
        "rows": text.count("<tr>"),
        "cells": text.count("<td>"),
    }


def html_defects(text: str):
    """Structural HTML faults a translation can introduce.

    An unclosed backtick in one cell swallows the next `<td>`, so the row silently gains
    a column and the table renders wrong. Counting cells against the git baseline catches
    it, but naming the exact offset makes it fixable.
    """
    out = []
    if text.count("<table>") != text.count("</table>"):
        out.append(f"table tags unbalanced: {text.count('<table>')}/"
                   f"{text.count('</table>')}")
    if text.count("<tr>") != text.count("</tr>"):
        out.append(f"tr tags unbalanced: {text.count('<tr>')}/{text.count('</tr>')}")
    nested = list(re.finditer(r"<td>[^<]*<td>", text))
    if nested:
        out.append(f"{len(nested)} cell(s) with a stray <td>: "
                   + "; ".join(repr(text[max(0, m.start() - 30):m.start() + 30])
                               for m in nested[:3]))
    return out


def zh_lines(text: str) -> int:
    return len([l for l in text.split("\n") if re.search(r"[\u4e00-\u9fff]", l)])


print(f"{'part':22s} {'中文字符':>8s} {'blocks':>14s} {'tables':>13s} "
      f"{'images':>13s} {'rows':>13s} {'cells':>13s}")
bad = 0
for p in PARTS:
    cur = p.read_text(encoding="utf-8")
    try:
        base = subprocess.run(["git", "show", f"HEAD:{p.as_posix()}"],
                              capture_output=True, text=True, encoding="utf-8",
                              check=True).stdout
    except subprocess.CalledProcessError:
        print(f"{p.name:22s} (no baseline)")
        continue

    b, c = stats(base), stats(cur)
    drift = [k for k in b if b[k] != c[k]]
    defects = html_defects(cur)
    mark = "OK" if not drift and not defects else "DRIFT"
    if drift or defects:
        bad += 1
    zh = len(re.findall(r"[\u4e00-\u9fff]", cur))
    print(f"{p.name:22s} {zh:8d} "
          f"{b['blocks']:>6d}->{c['blocks']:<6d} "
          f"{b['tables']:>5d}->{c['tables']:<5d} "
          f"{b['images']:>6d}->{c['images']:<6d} "
          f"{b['rows']:>6d}->{c['rows']:<6d} "
          f"{b['cells']:>6d}->{c['cells']:<6d} {mark}")
    for d in defects:
        print(f"{'':22s}   ! {d}")

print()
print("parts with problems:", bad)
sys.exit(1 if bad else 0)