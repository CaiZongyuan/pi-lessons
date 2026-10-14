"""Non-mutating full-book acceptance checks; importer-specific coverage is in reports."""
from pathlib import Path
import json,hashlib,re,subprocess,sys
from html.parser import HTMLParser
R=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(R/'scripts/check_content.py')],check=True)
manifest=json.loads((R/'sources/full-manifest.json').read_text())
for name,m in manifest.items():
 p=R/name;assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256'],name
nav=json.loads((R/'docs/.vitepress/navigation.json').read_text());assert len(nav)==36
pages=[R/('docs'+r['link']+'.md') for r in nav]+[R/'docs/pi-104/preface.md']
assert all(p.is_file() for p in pages)
figs=[f for p in (R/'docs/.vitepress/theme/figures').glob('book-*.json') for f in json.loads(p.read_text())]
assert len(figs)==50 and len({f['id'] for f in figs})==50
for f in figs:
 assert f['kind']=='diagram',f['id']
 assert (R/'docs/public'/f['image'].lstrip('/')).is_file(),f['image']
 ids={n['id'] for n in f['nodes']}
 for e in f['edges']:assert e.get('from') in ids and e.get('to') in ids,(f['id'],e)
text='\n'.join(p.read_text() for p in pages)
assert len(re.findall(r'<BookFigure\s',text))==50
assert len(re.findall(r'<ManualFigure\s',text))==12
class Check(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.refs=[];self.tables=0;self.figures=0;self.codeblocks=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);classes=a.get('class','').split()
  if 'id' in a:self.ids.append(a['id'])
  self.refs+=a.get('aria-describedby','').split()+a.get('aria-labelledby','').split()
  self.tables+=tag=='table';self.figures+=tag=='figure' and bool({'book-figure','manual-figure'}&set(classes))
  self.codeblocks+=tag=='div' and any(x.startswith('language-') for x in classes)
counts={'tables':0,'figures':0,'codeblocks':0}
for p in pages:
 html=R/'docs/.vitepress/dist'/p.relative_to(R/'docs').with_suffix('.html');assert html.is_file(),html
 c=Check();c.feed(html.read_text());assert len(c.ids)==len(set(c.ids)),html
 assert set(c.refs)<=set(c.ids),(html,set(c.refs)-set(c.ids))
 for k in counts:counts[k]+=getattr(c,k)
assert counts=={'tables':101,'figures':62,'codeblocks':60},counts
assert not list((R/'docs/public').rglob('*.png')),'Public PNG assets remain'
assert len(list((R/'docs/public/figures').rglob('*.webp')))==62
print('PASS:',len(pages),'reading/front-matter pages; 36 sections; 101 tables; 60 code blocks; 62 native figures; immutable source hashes; 62 WebP assets; valid IDs/ARIA.')
