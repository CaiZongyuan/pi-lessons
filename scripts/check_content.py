from pathlib import Path
import re
r=Path(__file__).resolve().parents[1]
s=(r/'sources/chapter/4.编码智能体.md').read_text()
pages=[(r/f'docs/pi-104/{x}.md').read_text() for x in ['system-prompt','tools','sessions','compaction']]
out='\n'.join(pages)
assert len(re.findall(r'<ManualFigure ',out))==12
fences=lambda t: re.findall(r'```[^\n]*\n(.*?)\n```',t,re.S)
a,b=fences(s),fences(out)
assert len(a)==len(b)==9
for i,(x,y) in enumerate(zip(a,b)):
 for key in ['sections','preamble','tools','rules','docs','cwd']:
  x=x.replace('"**'+key+'**":','"'+key+'":')
 assert x==y, f'Code block {i+1} drifted'
def norm(t):
 t=re.sub(r'^---\n.*?\n---\n','',t,flags=re.S)
 t=re.sub(r'<div class="section-kicker">.*?</div>','',t)
 t=re.sub(r'!\[[^\]]*\]\([^)]+\)|<ManualFigure [^>]+/>','FIGURE',t)
 t=re.sub(r'```[^\n]*','```',t)
 t=t.replace('<strong>','').replace('</strong>','').replace('**','').replace('\\|','|')
 return re.sub(r'\s+','',t)
s=re.sub(r'^# 4[^\n]*\n','',s)
assert norm(s)==''.join(norm(p) for p in pages),'Body text drifted'
print('PASS: complete chapter text; all 4 sections; 12 figures; 9 code blocks unchanged except six verified export-artifact key fixes.')
