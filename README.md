# Pi Lessons

把英文技术手册翻译成可在线阅读的简体中文版，保留原版排版、矢量图表与代码格式。

在线阅读：<https://caizongyuan.github.io/pi-lessons/>

## 仓库结构

```
books/
  pi-durable/           Pi Durable 技术手册（190 页，已完成）
    book.json             页码范围、章节中文名
    GLOSSARY.md           术语表 —— 翻译时必须遵守
    ir/
      01-model.json       译文（唯一需要手工维护的内容）
      01-model.meta.json  部分元数据
      01-model/figures/   图表裁切（PNG）
      ...
  pi-manual/           Pi 技术手册（221 页，待翻译）
tools/
  book.py                 统一入口：list / extract / render / build / check / index
  check.py                校验译文完整性与 HTML 结构
  verify_site.py          发布前检查站内链接与资源
  pdf2html/
    extract.py            PDF → 文本块 + 图表裁切
    normalize.py          文本块 → 语义 IR
    render.py             IR → HTML
    rebuild.py            改抽取规则后重跑并保住译文
    bookindex.py          生成 site/index.html
    style.css             唯一样式来源
site/                     构建产物（不入库，由 CI 生成并发布）
```

## 常用命令

```bash
python tools/book.py list                    # 查看各书与各部分的翻译/构建状态
python tools/book.py render pi-durable       # IR → HTML（不需要 PDF）
python tools/book.py extract pi-manual       # PDF → IR + 图表裁切（需要 PDF）
python tools/book.py check                   # 校验
```

## 关于源 PDF

**源 PDF 不入库**（版权原因）。需要重跑抽取时，把 PDF 放到本地任一目录，然后：

```bash
# Windows
set PI_PDF=C:\path\to\pdfs
python tools/book.py extract pi-durable

# macOS / Linux
export PI_PDF=/path/to/pdfs
python tools/book.py extract pi-durable
```

也可以直接指定：`--pdf /path/to/Pi-Technical-Manual.pdf`

| 书 | 文件名 | 页数 |
|---|---|---|
| Pi Durable 技术手册 | `Pi-Durable-Technical-Manual.pdf` | 190 |
| Pi 技术手册 | `Pi-Technical-Manual.pdf` | 221 |

## 流水线为什么这样切分

```
PDF ──extract──> content.json ──normalize──> ir.json ──翻译──> ir.json+zh
                                                              │
                                                        render │
                                                              ▼
                                                          HTML ──> site/
```

关键点：**`render` 阶段完全不需要 PDF**。它只读译文 IR、图表裁切和样式表。
这带来两个好处：

1. CI 跑得快（不用重跑 190 页抽取）
2. 译文与源 PDF 解耦 —— PDF 更新时只需本地重跑抽取、提交新的 IR，CI 自动重新发布

## 翻译流程

1. `book.py extract <book>` 产出 IR
2. 起 subagent 并行翻译各部分，遵守 `books/<id>/GLOSSARY.md`
3. 译文写回 IR 的 `zh` 字段（`figure` 节点写 `zh_caption`，`code` 节点不动）
4. `book.py check <book>` 确认 `missing: 0`
5. `book.py render <book>` + `book.py index`

详见 skill：`~/.workbuddy/skills/pdf-to-zh-html/SKILL.md`

## 新增一本书

```bash
mkdir -p books/<id>/ir
cp books/pi-durable/GLOSSARY.md books/<id>/GLOSSARY.md
$EDITOR books/<id>/book.json      # 填页码范围与章节名
python tools/book.py extract <id> # 需要先设好 PI_PDF
```

`book.json` 里 `parts` 的页码范围可以用这段脚本从 PDF 反查（大字号标题即章节起点）：

```bash
python - <<'PY'
import fitz
d = fitz.open("<your.pdf>")
for p in range(len(d)):
    for b in d[p].get_text("dict")["blocks"]:
        if b["type"]: continue
        mx = max((s["size"] for l in b["lines"] for s in l["spans"]), default=0)
        if mx >= 19:
            t = "".join(s["text"] for l in b["lines"] for s in l["spans"]).strip()
            if t: print(p + 1, round(mx, 1), t[:60])
PY
```

## 技术说明

两本手册都由同一个 "TechManual engine"（Paged.js + Chrome）生成，这决定了流水线必须这样写：

- **没有一张位图**，所有图表都是矢量 → 按坐标裁切为 200 DPI PNG
- **字体全是 Type3 子集** → 文本能提取，但字体名在系统上不存在
- **图注是字距展开的全大写**，PyMuPDF 返回 `F I G . 1 . 4` → 靠**空格字符自身的宽度**区分字距（1.3pt）与真实词间空格（3.8pt）
- **每个文本块只有一行** → 按垂直间距重组为段落；正文左边距 57.6、列表项 71.6，据此区分段落与列表
- **图注会重复出现**（截断版作为 `figure.caption`，完整版作为紧随的 `small`）→ 用最长公共子串覆盖率去重

`svgfig.py` 曾尝试导出带文字的 SVG 以便翻译图内标签，但 Type3 字体缺失导致回退字体重排、跨列文字重叠，已放弃。图表文字的翻译由下方中文图注承载。
