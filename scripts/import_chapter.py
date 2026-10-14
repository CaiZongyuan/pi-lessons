from pathlib import Path
import re,json
root=Path(__file__).resolve().parents[1]
s=(root/'sources/chapter/4.编码智能体.md').read_text()
slugs=['system-prompt','tools','sessions','compaction']
parts=[]; lines=[]; fenced=False
for line in s.splitlines():
 if line.startswith('```'):fenced=not fenced
 if not fenced and line.startswith('# ') and not line.startswith('# 4'):
  if lines:parts.append('\n'.join(lines));lines=[]
  lines=[line]
 elif lines:lines.append(line)
if lines:parts.append('\n'.join(lines))
assert len(parts)==4
mapping={'image 9.png':'4.1','image 6.png':'prompt-cards','image 1.png':'4.2','image 10.png':'patch-example','image 8.png':'4.3','image 3.png':'4.4','image 11.png':'4.5','image 5.png':'4.6','image 4.png':'4.7','image.png':'4.8','image 2.png':'compaction-explainer','image 7.png':'4.9'}
from urllib.parse import unquote
for n,(slug,part) in enumerate(zip(slugs,parts),1):
 part=part.replace('****','')
 for key in ['sections','preamble','tools','rules','docs','cwd']:
  part=part.replace('"**'+key+'**":', '"'+key+'":')
 part=part.replace("... | head -c 51200", "... \\| head -c 51200").replace("{content} | null", "{content} \\| null")
 part=part.replace('```Plain Text','```text')
 if slug=='compaction':part=part.replace('```TypeScript','```text')
 def fig(m):
  name=unquote(m[1]).split('/')[-1];return f'<ManualFigure id="{mapping[name]}" />'
 part=re.sub(r'!\[[^\]]*\]\(([^)]+)\)',fig,part)
 part=part.replace('```JSON','```json').replace('```TypeScript','```ts')
 # Explicit strong tags avoid CommonMark CJK punctuation-edge ambiguity.
 fixed=[];in_fence=False
 for line in part.splitlines():
  if line.startswith('```'):in_fence=not in_fence
  if not in_fence and not line.startswith('```'):
   chunks=re.split(r'(`[^`]*`)',line);opened=False
   for ci in range(0,len(chunks),2):
    bits=chunks[ci].split('**');joined=bits[0]
    for bit in bits[1:]:
     joined+=('</strong>' if opened else '<strong>')+bit;opened=not opened
    chunks[ci]=joined
   assert not opened, 'Unbalanced bold formatting'
   line=''.join(chunks)
  fixed.append(line)
 part='\n'.join(fixed)
 title=part.splitlines()[0][2:]
 part=part.replace('# '+title,f'<div class="section-kicker">4.{n} / THE CODING AGENT</div>\n\n# {title}',1)
 (root/f'docs/pi-104/{slug}.md').write_text('---\ntitle: '+title+'\n---\n\n'+part.strip()+'\n')
print('Imported all four sections; 12 figure references; source Markdown unchanged.')
