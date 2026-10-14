#!/usr/bin/env python3
"""Read-only fidelity, artifact and accessibility audit for Pi Durable."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re
R=Path(__file__).resolve().parents[1]; report=json.loads((R/'sources/reports/durable-import.json').read_text()); nav=json.loads((R/'docs/.vitepress/durable-navigation.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert len(nav)==53
for f in report['sourceFiles']:assert sha(R/f['path'])==f['sha256'],f['path']

def body(t):
 t=re.sub(r'^---\n.*?\n---\n','',t,flags=re.S)
 t=re.sub(r'<div class="section-kicker">.*?</div>','',t)
 return t

def codes(t):return re.findall(r'^```[^\n]*\n(.*?)^```\s*$',t,re.M|re.S)
def norm(t):
 t=body(t).replace('<strong>','**').replace('</strong>','**')
 t=re.sub(r'</?aside[^>]*>', '', t)
 for c in json.loads((R/'sources/reports/durable-callouts.json').read_text()):
  if not c['label_present_in_manuscript']:t=t.replace('**'+c['label']+'**','')
 t=re.sub(r'^> ?', '', t,flags=re.M)
 t=re.sub(r'!\[[^\]]*\]\([^)]+\)|<BookFigure[^>]*?/>','',t)
 t=re.sub(r'\[([^\]]+)\]\(/pi-durable/[^)]+\)',r'\1',t)
 # Formatting-only transformations, never payload substitutions.
 t=t.replace('****','')
 t=re.sub(r'\\([\\`*_{}\[\]()#+.!<>|~-])',r'\1',t)
 t=re.sub(r'^#{1,6}\s+(?:R\.\d+\s+)?', '', t,flags=re.M)
 t=re.sub(r'^```[^\n]*','```',t,flags=re.M)
 return re.sub(r'\s+','',t)
counts={'codeblocks':0,'figures':0,'tables':0}
for f in report['sourceFiles']:
 source=R/f['path'];raw=source.read_text();rows=[s for s in report['sections'] if s['source']==f['path']]
 if rows:
  rendered='\n'.join(body((R/s['output']).read_text()) for s in rows)
  raw=re.sub(r'^# [^\n]+\n','',raw,count=1)
 else:rendered=body((R/report['front']).read_text())
 assert codes(raw)==codes(rendered),f'Code payload mismatch: {source}'
 assert norm(raw)==norm(rendered),f'Text mismatch: {source}'
 counts['codeblocks']+=len(codes(rendered))
figures=[f for p in (R/'docs/.vitepress/theme/figures').glob('durable-*.json') for f in json.loads(p.read_text())]
assert len(figures)==67 and len({f['id'] for f in figures})==67,len(figures)
byid={f['id']:f for f in figures}
for row in report['images']:
 assert sha(R/row['source'])==row['sha256']
 assert sha(R/row['output'])==row['webp_sha256']
 assert byid[row['id']]['image']==row['image']
 f=byid[row['id']];ids={n['id'] for n in f.get('nodes',[])}
 for e in f.get('edges',[]):assert e.get('from') in ids and e.get('to') in ids
 for p in f.get('vectorPaths',[]):
  if 'clip' in p:assert 0<=p['clip']<len(f['vectorClips'])
class HTMLCheck(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.refs=[];self.tables=0;self.figures=0;self.missing=0
 def handle_starttag(self,t,attrs):
  a=dict(attrs);c=a.get('class','').split()
  if 'id' in a:self.ids.append(a['id'])
  self.refs+=a.get('aria-describedby','').split()+a.get('aria-labelledby','').split()
  self.tables+=t=='table';self.figures+=t=='figure' and 'book-figure' in c;self.missing+='figure-missing' in c
for p in [R/s['output'] for s in report['sections']]+[R/report['front']]:
 html=R/'docs/.vitepress/dist'/p.relative_to(R/'docs').with_suffix('.html');assert html.exists(),html
 c=HTMLCheck();c.feed(html.read_text());assert len(c.ids)==len(set(c.ids)),html;assert set(c.refs)<=set(c.ids),(html,set(c.refs)-set(c.ids));assert not c.missing,html
 counts['figures']+=c.figures;counts['tables']+=c.tables
assert counts=={'codeblocks':64,'figures':67,'tables':94},counts
print('PASS Pi Durable: 53 sections + full front, exact normalized text and 64 fenced payloads; 67 figures/WebPs with source hashes; 94 adjustable tables; valid IDs and ARIA.')
