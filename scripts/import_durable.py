#!/usr/bin/env python3
"""Import immutable supplied Pi Durable Markdown without technical modernization.

Ordinary npm builds do not run this script. Pillow is only used during authoring.
"""
from pathlib import Path
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'sources/durable'; OUT=ROOT/'docs/pi-durable'
FRONT=SRC/'Pi Durable 技术手册/Pi Durable 技术手册.md'
REPORT=ROOT/'sources/reports/durable-import.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
clean=lambda s:re.sub(r'\\([\\`*_{}\[\]()#+.!<>|~-])',r'\1',s).strip()
image_rx=re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
front=FRONT.read_text()
page_map={f'{a}.{b}':int(n) for a,b,n in re.findall(r'([\dR]+)\\\.(\d+) [^\n]+?（原书第(\d+)页）',front)}
nav=[]; sections=[]; images=[]; corrections=[]

def convert(text,source,chapter):
    callouts=json.loads((ROOT/'sources/reports/durable-callouts.json').read_text())
    original_lines=text.splitlines()
    for c in callouts:
        if c['source']!=source.relative_to(SRC).as_posix():continue
        first=(c['label_line'] or c['body_start_line'])-1
        snippet='\n'.join(original_lines[first:c['body_end_line']])
        paragraph=re.sub(r'^> ?', '', c['body_exact'],flags=re.M)
        replacement=f'<aside class="manual-callout callout-{c["kind"]} durable-callout" role="note" data-source-page="{c["pdf_page"]}">\n\n**{c["label"]}**\n\n{paragraph}\n\n</aside>'
        assert snippet in text,(source,c['label'])
        text=text.replace(snippet,replacement,1)
        if not c['label_present_in_manuscript']:corrections.append({'source':source.relative_to(ROOT).as_posix(),'kind':'restore-pdf-callout-label','label':c['label'],'originalLabel':c['original_label'],'page':c['pdf_page']})
    # Exported empty quote tails must not become literal text after an HTML aside.
    text=re.sub(r'</aside>\n(?:>[ \t]*\n)+','</aside>\n\n',text)
    index=0
    folder='front' if chapter=='front' else ('reference' if chapter=='R' else f'ch{int(chapter):02}')
    def image(m):
        nonlocal index
        index+=1; original=source.parent/unquote(m[2]); assert original.is_file(),original
        name=original.stem.replace(' ','-')+'.webp'; path=f'/durable/{folder}/{name}'
        fid=f'D.{chapter}.{index}'
        images.append({'id':fid,'source':original.relative_to(ROOT).as_posix(),'image':path,'sha256':sha(original.read_bytes())})
        return f'<BookFigure id="{fid}" :show-caption="false" />'
    text=image_rx.sub(image,text)
    # Language identifiers are metadata; fenced payloads remain byte-exact.
    aliases={'TypeScript':'ts','Typescript':'ts','JavaScript':'js','Javascript':'js','JSON':'json','Bash':'bash','Shell':'sh','SQL':'sql','Plain Text':'text','Text':'text'}
    text=re.sub(r'^```([^\n]*)$',lambda m:'```'+aliases.get(m[1],m[1]),text,flags=re.M)
    # Escape literal union/pipe characters inside inline code in table cells.
    # Markdown tables split at pipes even within code; source content is retained.
    lines=[]; fenced=False
    for line in text.splitlines(keepends=True):
        if line.startswith('```'):fenced=not fenced
        if not fenced and '****' in line:
            count=line.count('****'); line=line.replace('****','')
            corrections.append({'source':source.relative_to(ROOT).as_posix(),'kind':'adjacent-bold-export-delimiter','count':count})
        if not fenced and '**' in line:
            held=[]
            def hold(m):
                held.append(m[0]);return f'INLINECODETOKEN{len(held)-1}END'
            protected=re.sub(r'`+[^`]*`+',hold,line)
            count=len(re.findall(r'\*\*(.+?)\*\*',protected))
            if count:
                protected=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',protected)
                for j,value in enumerate(held):protected=protected.replace(f'INLINECODETOKEN{j}END',value)
                line=protected
                corrections.append({'source':source.relative_to(ROOT).as_posix(),'kind':'unambiguous-prose-bold-markup','count':count})
        if not fenced and line.startswith('|'):
            before=line
            line=re.sub(r'`([^`]+)`',lambda m:'`'+re.sub(r'(?<!\\)\|',r'\\|',m[1])+'`',line)
            if before!=line:corrections.append({'source':source.relative_to(ROOT).as_posix(),'kind':'table-pipe-escape','before':before.strip(),'after':line.strip()})
        lines.append(line)
    return ''.join(lines)

def save(chapter,i,title,body,source,start,end,route,level=1):
    title=clean(title)
    if chapter=='R':title=re.sub(r'^R\.\d+\s+','',title)
    key=f'{chapter}.{i}'; page=page_map.get(key)
    # Only section heading levels change for standalone reading pages.
    if level==2:
        body=re.sub(r'^(#{2,6}) ',lambda m:m[1][1:]+' ',body,flags=re.M)
    body=re.sub(r'^# [^\n]+', '# '+title,body,count=1)
    kicker=f'PI DURABLE / {key}'+(f' · P. {page}' if page else '')
    output='---\ntitle: '+json.dumps(title,ensure_ascii=False)+'\n---\n\n<div class="section-kicker">'+kicker+'</div>\n\n'+body.strip()+'\n'
    dest=ROOT/('docs'+route+'.md');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(output)
    nav.append({'chapter':chapter,'number':key,'title':title,'link':route,'page':page})
    sections.append({'chapter':chapter,'number':key,'source':source.relative_to(ROOT).as_posix(),'sourceStart':start,'sourceEnd':end,'output':dest.relative_to(ROOT).as_posix(),'title':title,'page':page})

for ch in range(1,11):
    source=next(p for p in SRC.rglob('*.md') if p.name.startswith(f'{ch}.'))
    raw=source.read_text(); text=convert(raw,source,str(ch)); starts=list(re.finditer(r'^# (.+)$',text,re.M))
    assert len(starts)>1
    for i,m in enumerate(starts[1:],1):
        end=starts[i+1].start() if i+1<len(starts) else len(text)
        save(str(ch),i,m[1],text[m.start():end],source,m.start(),end,f'/pi-durable/ch{ch:02}/section-{i:02}')
source=SRC/'参考.md';text=convert(source.read_text(),source,'R');starts=list(re.finditer(r'^## (R\\\.\d+ .+)$',text,re.M))
for i,m in enumerate(starts,1):
    end=starts[i].start() if i<len(starts) else len(text)
    save('R',i,m[1],text[m.start():end],source,m.start(),end,f'/pi-durable/reference/section-{i:02}',2)
# Full front matter, including its original supplied contents, is retained.
text=convert(front,FRONT,'front')
# Make the original TOC usable without changing its wording.
for row in nav:
    pat=re.escape(row['number'].replace('.',r'\.'))+r' [^\n]+?（原书第\d+页）'
    text=re.sub(pat,lambda m:'['+m[0]+']('+row['link']+')',text,count=1)
(OUT/'preface.md').write_text('---\ntitle: 如何阅读本书\n---\n\n<div class="section-kicker">PI DURABLE / ENGINEERING EDITION · 1.0.3</div>\n\n'+text)
chapters={str(ch):clean(next(p for p in SRC.rglob('*.md') if p.name.startswith(f'{ch}.')).read_text().splitlines()[0][2:]).split('.',1)[-1].strip() for ch in range(1,11)};chapters['R']='参考'
for row in nav:row['chapterTitle']=chapters[row['chapter']]
(ROOT/'docs/.vitepress/durable-navigation.json').write_text(json.dumps(nav,ensure_ascii=False,indent=2)+'\n')
index=['---','title: Pi Durable','outline: false','---','','<div class="section-kicker">PI / TECHNICAL SERIES · 02</div>','','# Pi Durable','','<div class="book-lede">从原子提交到崩溃恢复，读懂持久化智能体运行框架。</div>','','Pi Durable 1.0.3 · 工程版 · 2026.10。完整收录 10 章、7 节参考资料及开篇内容。','','[如何阅读本书与第一个可运行的对话 →](/pi-durable/preface)','','> **版本说明**','> 本书对应提交 `5b6c792`（2026 年 10 月 5 日）。Pi Durable 为实验性软件；本阅读版保留书中版本与技术语义，示例不会自动更新到后续版本。','']
for chapter,title in chapters.items():
    index+=['## '+('R' if chapter=='R' else chapter.zfill(2))+' · '+title,'']
    for row in nav:
        if row['chapter']==chapter:index+=['- ['+row['number']+' '+row['title']+']('+row['link']+')'+(f' · 原书第 {row["page"]} 页' if row['page'] else '')]
    index+=['']
index+=['---','','[返回技术文库 →](/)']
(OUT/'index.md').write_text('\n'.join(index)+'\n')
# Convert each original bitmap with exact decoded RGBA equivalence.
from PIL import Image
assets=[]
for row in images:
    p=ROOT/row['source'];out=ROOT/'docs/public'/row['image'].lstrip('/');out.parent.mkdir(parents=True,exist_ok=True)
    original=Image.open(p).convert('RGBA')
    if not out.exists():original.save(out,format='WEBP',lossless=True,quality=100,method=6,exact=True)
    actual=Image.open(out).convert('RGBA');assert actual.size==original.size and actual.tobytes()==original.tobytes()
    assets.append({**row,'output':'docs/public'+row['image'],'webp_sha256':sha(out.read_bytes()),'source_bytes':p.stat().st_size,'webp_bytes':out.stat().st_size,'width':original.width,'height':original.height,'rgba_equal':True})
source_files=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p.read_bytes())} for p in SRC.rglob('*.md')]
REPORT.write_text(json.dumps({'sections':sections,'front':'docs/pi-durable/preface.md','sourceFiles':source_files,'images':assets,'corrections':corrections},ensure_ascii=False,indent=2)+'\n')
print(f'Imported {len(nav)} sections + front; {len(images)} lossless WebPs; {len(corrections)} safe formatting corrections')
