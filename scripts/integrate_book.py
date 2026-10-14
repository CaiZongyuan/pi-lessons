from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
nav=[]
for p in sorted((ROOT/'sources/reports').glob('navigation-*.json')):nav+=json.loads(p.read_text())
nav += [dict(title=t,link='/pi-104/'+s,page=p,chapter='4',chapterTitle='编码智能体') for s,t,p in [('system-prompt','系统提示词构建',75),('tools','内置工具',81),('sessions','会话：JSONL 树',86),('compaction','压缩与分支摘要',92)]]
for r in nav:
 r['chapter']=str(r['chapter']);r['page']=r.get('page',(r.get('pageRange') or [0])[0]);r['link']=r.get('link',r.get('route'));r['chapterTitle']=r.get('chapterTitle',{'2':'提供商层','3':'智能体循环'}.get(r['chapter'],''))
nav.sort(key=lambda r:r['page'])
assert len(nav)==36,len(nav)
(ROOT/'docs/.vitepress/navigation.json').write_text(json.dumps(nav,ensure_ascii=False,indent=2)+'\n')
parts=['---\ntitle: Pi 1.04\noutline: false\n---\n','<div class="section-kicker">PI / TECHNICAL MANUAL · 1.0.4</div>\n','# Pi 1.04\n','<div class="book-lede">从一个提示一直追踪到 JSONL 中的一行，理解这个极简智能体运行框架。</div>\n','[如何阅读本书 · 来源、约定与插图颜色 →](./preface)\n']
for c in list('1234567R'):
 rows=[r for r in nav if r['chapter']==c]
 parts.append(f'\n<div class="chapter-title"><span>{c.zfill(2) if c!="R" else "R"}</span><h2>{rows[0]["chapterTitle"]}</h2></div>\n\n<div class="chapter-contents">')
 for i,r in enumerate(rows,1):parts.append(f'<a href="{r["link"]}"><span>{c}.{i}</span><strong>{r["title"]}</strong><small>P. {r["page"]}</small><b>→</b></a>')
 parts.append('</div>\n')
parts.append('<p class="edition-note">依据所提供的中文书稿与原版 PDF 整理。页码对应原书；图示保留原图对照，核对中发现的源文差异会明确标注。</p>\n')
(ROOT/'docs/pi-104/index.md').write_text('\n'.join(parts))
files=list((ROOT/'sources/full').rglob('*'))+list((ROOT/'sources/chapter').rglob('*'))
manifest={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files if p.is_file()}
(ROOT/'sources/full-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Integrated 36 reading sections, opening matter, eight sidebar groups; immutable manifest saved.')
