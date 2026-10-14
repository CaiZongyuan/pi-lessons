from pathlib import Path
import re,json,shutil,hashlib
from collections import Counter
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
FRONT=ROOT/'sources/full/Pi 技术手册/Pi 技术手册.md'
REF=ROOT/'sources/full/8.参考资料/8.参考资料.md'
REFS=[('environment','环境变量',185),('cli','CLI 参考',191),('commands','斜杠命令与快捷键',197),('settings','设置参考',202),('source-index','源文件索引',208),('doc-code','文档与代码的差异',213),('glossary','术语表',216),('sources','来源与版本',218),('figures','插图索引',220)]
MAP={'image.png':'R.1','image 1.png':'R.2'}
REPAIRS=[]
def sections(s):
 out=[];buf=[];fence=''
 for line in s.splitlines():
  m=re.match(r'^(`{3,}|~{3,})',line)
  if m:
   if not fence:fence=m[1]
   elif m[1][0]==fence[0] and len(m[1])>=len(fence):fence=''
  if not fence and line.startswith('# '):
   if buf:out.append('\n'.join(buf))
   buf=[line]
  elif buf:buf.append(line)
 if buf:out.append('\n'.join(buf))
 return out

def fmt(s,reference=False):
 out=[];fence=''
 for line in s.splitlines():
  m=re.match(r'^(`{3,}|~{3,})(.*)$',line)
  if m:
   if not fence:
    fence=m[1];lang=m[2].strip();line=fence+{'JSON':'json','TypeScript':'ts','Plain Text':'text','Markdown':'markdown','Bash':'bash'}.get(lang,lang.lower())
   elif m[1][0]==fence[0] and len(m[1])>=len(fence):fence=''
   out.append(line);continue
  if fence:out.append(line);continue
  line=line.replace('****','')
  chunks=re.split(r'(`[^`]*`)',line);opened=False
  for i,chunk in enumerate(chunks):
   if i%2:
    if line.lstrip().startswith('|'):chunks[i]=re.sub(r'(?<!\\)\|',r'\\|',chunk)
   else:
    bits=chunk.split('**');text=bits[0]
    for b in bits[1:]:text+=('</strong>' if opened else '<strong>')+b;opened=not opened
    chunks[i]=text
  assert not opened,line
  line=''.join(chunks)
  if reference and line.startswith('### '):line=line[1:]
  out.append(line)
 return '\n'.join(out)

def callout(s,prefix,label):
 pattern=re.compile(r'(?m)^'+re.escape(prefix)+r'.*$')
 m=pattern.search(s);assert m,prefix
 REPAIRS.append('Restore '+label+' callout: '+prefix)
 prior=s[:m.start()];old=re.search(r'(?m)^\*\*(易踩的坑|DOC ≠ CODE|文档 ≠ 代码)\*\*\s*$',prior)
 if old:return s[:old.start()]+'>'+old[0].rstrip()+'\n>\n> '+m[0]+s[m.end():]
 return s[:m.start()]+'> '+label+'\n>\n> '+m[0]+s[m.end():]

def norm(s):
 s=re.sub(r'^---\n.*?\n---\n','',s,flags=re.S)
 s=re.sub(r'<div class="section-kicker">.*?</div>','',s)
 s=re.sub(r'!\[[^\]]*\]\([^)]+\)|<BookFigure [^>]+/>','FIGURE',s)
 s=re.sub(r'<strong>|</strong>','',s)
 s=re.sub(r'^```[^\n]*','```',s,flags=re.M)
 s=re.sub(r'^#{1,6}\s*','',s,flags=re.M)
 s=re.sub(r'^>\s*','',s,flags=re.M)
 s=s.replace('**','').replace('\\|','|')
 s=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',s)
 return re.sub(r'\s+','',s)

def make_node(i,x,y,w,h,label,detail='',tone='green',**kw):return dict(id=i,x=x,y=y,w=w,h=h,label=label,detail=detail or label.replace('\n',' · '),tone=tone,**kw)
def flow(id,title,page,image,labels,details,source,caption):
 w=310;gap=34;width=len(labels)*(w+gap)+6
 ns=[make_node('n'+str(i),20+i*(w+gap),25,w,135,l,details[i],'indigo' if 'CLI override' in l else 'config') for i,l in enumerate(labels)]
 return dict(id=id,title=title,label='FIG. '+id,page=page,image=image,source=source,caption=caption,kind='diagram',width=width,height=195,nodes=ns,edges=[dict(**{'from':ns[i]['id'],'to':ns[i+1]['id']}) for i in range(len(ns)-1)])

def main():
 (ROOT/'docs/pi-104/reference').mkdir(parents=True,exist_ok=True)
 for source,target in [(FRONT,'front'),(REF,'reference')]:
  dest=ROOT/'docs/public/figures'/target;dest.mkdir(parents=True,exist_ok=True)
  for p in (source.parent/'图片和附件').glob('*'):shutil.copy2(p,dest/p.name)
 ref=REF.read_text();parts=sections(ref)[1:];assert len(parts)==9
 nav=[];counts=[]
 for i,((slug,title,page),s) in enumerate(zip(REFS,parts),1):
  original=s
  if i==1:s=callout(s,'`--help` 说','文档 ≠ 代码')
  if i==2:s=callout(s,'布尔型扩展标志会吞掉下一个单词。','易踩的坑')
  if i==6:
   candidates=[l for l in s.splitlines() if l.startswith('差异 10 还有另一面。')]
   if candidates:s=callout(s,candidates[0][:24],'文档 ≠ 代码')
  s=fmt(s,True)
  s=re.sub(r'!\[[^\]]*\]\(([^)]+)\)',lambda m:f'<BookFigure id="{MAP[unquote(m[1]).split("/")[-1]]}" />',s)
  heading=s.splitlines()[0]
  s=s.replace(heading,f'<div class="section-kicker">R.{i} / REFERENCE</div>\n\n'+heading,1)
  out=f'---\ntitle: {title}\n---\n\n'+s.strip()+'\n';path=ROOT/f'docs/pi-104/reference/{slug}.md';path.write_text(out)
  check=out
  for label in ['文档 ≠ 代码','易踩的坑']:check=check.replace('> '+label+'\n>\n','')
  assert norm(original)==norm(check),(slug,'content drift')
  nav.append(dict(title=title,link=f'/pi-104/reference/{slug}',page=page,chapter='R',chapterTitle='参考资料'))
  counts.append(dict(slug=slug,characters=len(norm(original)),tables=len(re.findall(r'^\|\s*[-:]+',original,re.M)),codeBlocks=len(re.findall(r'^```',original,re.M))//2))
 front=FRONT.read_text();s=fmt(front)
 s=re.sub(r'!\[[^\]]*\]\(([^)]+)\)','<BookFigure id="front-run" />',s)
 # Front matter contains escaped Markdown links from a rich-text export.
 links={'1':'/pi-104/ch01/what-pi-is-for','2':'/pi-104/ch02/providers-models','3':'/pi-104/ch03/agent-loop','4':'/pi-104/system-prompt','5':'/pi-104/ch05/configuration-models-auth','6':'/pi-104/ch06/mcp','7':'/pi-104/ch07/experimental-stack','R':'/pi-104/reference/environment'}
 # Keep TOC labels verbatim, repair only the link syntax and destination.
 s=re.sub(r'\\\[([1-7R]) ([^\n]+?)\\\]\\\([^\n]+?\\\)',lambda m:f'[{m[1]} {m[2]}]({links[m[1]]})',s)
 s=s.replace(r'\[文档与代码的差异\]\(08\_参考资料\.md\)','[文档与代码的差异](/pi-104/reference/doc-code)')
 (ROOT/'docs/pi-104/preface.md').write_text('---\ntitle: 如何阅读本书\n---\n\n<div class="section-kicker">PI / TECHNICAL MANUAL · 1.0.4</div>\n\n'+s.strip()+'\n')
 cap1='第一个已设置的来源生效，并且设置层会在决定是否信任项目之前读取。顺序来自 main()（CA/src/main.ts:688）；默认路径来自 CA/src/core/session-manager.ts:589。即使后来拒绝项目，项目设置仍能改变会话文件位置。'
 cap2='项目列表替换全局列表，项目对象合并到全局对象。defaultTools 仅含 +name/-name 时追加到继承列表；其余数组整体替换。'
 figs=[flow('R.1','会话写入的位置',186,'/figures/reference/image.png',['① --session-dir\nCLI 标志\n最先匹配，立即生效','② PI_CODING_AGENT_SESSION_DIR\n环境变量\n展开 ~','③ sessionDir\n项目或全局 settings.json\n决定信任前读取','④ default\n<agent dir>/sessions/--<cwd>--'],['命令行 --session-dir 的优先级最高。','只有前一来源未设置时检查环境变量，路径中的 ~ 会展开。','sessionDir 来自项目或全局设置；读取发生在项目是否受信任的判断之前。','以上均未设置时，使用由工作目录编码而成的默认会话目录。'],'CA/src/main.ts:688 · CA/src/core/session-manager.ts:589',cap1),flow('R.2','设置值如何解析',202,'/figures/reference/image 1.png',['① global\n<agent dir>/settings.json\nsetter 写入此处','② project\n<cwd>/.pi/settings.json\n仅当项目受信任','③ merge\n对象合并 · 数组替换\ndefaultTools ± 追加','④ CLI override\napplyOverrides()\n启动时，仅 --theme','⑤ getter\nvalue ?? default'],['全局设置首先读取，setter 始终写入全局文件。','受信任的项目才加载项目设置。','对象递归合并，数组整体替换；defaultTools 的修饰符列表有自己的追加规则。','CLI 使用 applyOverrides()；图中的例外为启动时的 --theme。','getter 使用空值合并运算应用默认值；文件本身不填充默认值。'],'CA/src/core/settings-manager.ts:195,225,300,474',cap2)]
 from front_figure import front_figure
 figs.append(front_figure())
 (ROOT/'docs/.vitepress/theme/figures/book-reference.json').write_text(json.dumps(figs,ensure_ascii=False,indent=2)+'\n')
 (ROOT/'sources/reports/navigation-reference.json').write_text(json.dumps(nav,ensure_ascii=False,indent=2)+'\n')
 report={'source':str(REF.relative_to(ROOT)),'sourceSha256':hashlib.sha256(ref.encode()).hexdigest(),'sections':counts,'figures':3,'repairs':REPAIRS,'sourceDiscrepancies':['R.1 supplied default session path is incomplete; translator note retained, native figure uses complete path shown in original p186.','R.1 supplied GLOUD_PROJECT/lama.cpp spellings retain explicit translator warning; not silently corrected.'],'pdfEvidence':'Opening pp1–5; reference pp185–221; FigR.1 p186 and FigR.2 p202; DOC≠CODE p186/p215; FOOTGUN p194.'}
 (ROOT/'sources/reports/front-reference.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('PASS: all nine reference sections preserve normalized text; opening matter and three figures imported.')
if __name__=='__main__':main()
