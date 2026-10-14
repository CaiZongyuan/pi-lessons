import { readdirSync,readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import captionPrefixes from './caption-prefixes.json'
import durableCaptions from './durable-table-captions.json'
/** Semantic presentation only: source text is never rewritten by this plugin. */
export function manualMarkdown(md:any){
 const catalogDir=fileURLToPath(new URL('./theme/figures/',import.meta.url))
 const figures=readdirSync(catalogDir).filter(f=>/^(?:book-|durable-).*\.json$/.test(f)).flatMap(f=>JSON.parse(readFileSync(catalogDir+f,'utf8')))
 const captionNorm=(s:string)=>s.replace(/<[^>]+>/g,'').replace(/[*`\\]/g,'').replace(/\s+/g,'').trim()
 const isTableCaption=(text:string)=>captionPrefixes.some(prefix=>text.replace(/\s/g,'').startsWith(prefix.replace(/\s/g,'')))||durableCaptions.some(c=>captionNorm(text)===captionNorm(c))
 md.core.ruler.push('pi-manual-semantics',(state:any)=>{
  const ts=state.tokens;let heading='数据表',table=0
  // Recover plain exported callouts while keeping their text and list tokens intact.
  for(let i=ts.length-3;i>=0;i--){
   if(ts[i].type!=='paragraph_open'||ts[i].level!==0||ts[i+1]?.type!=='inline')continue
   const text=ts[i+1].content.replace(/<[^>]+>/g,'').replace(/[*`\\]/g,'').trim()
   if(!/^(这对你意味着什么|对你的意义|易踩的坑|经验法则|RULE OF THUMB|DOC ≠ CODE|文档 ≠ 代码)/i.test(text))continue
   let end=i+2
   if(/^(这对你意味着什么|对你的意义)/.test(text)&&ts[end+1]?.type==='bullet_list_open'){
    let depth=0;for(let j=end+1;j<ts.length;j++){if(ts[j].type==='bullet_list_open')depth++;if(ts[j].type==='bullet_list_close'&&--depth===0){end=j;break}}
   } else if(text.length<40&&ts[end+1]?.type==='paragraph_open')end+=3
   const open=new state.Token('blockquote_open','blockquote',1),close=new state.Token('blockquote_close','blockquote',-1)
   ts.splice(end+1,0,close);ts.splice(i,0,open)
  }
  // Keep a single visible copy of a source caption, while retaining metadata.
  for(let i=0;i<ts.length;i++){
   const m=/<BookFigure\s+id="([^"]+)"/.exec(ts[i].content||'');if(!m)continue
   const f=figures.find((x:any)=>x.id===m[1]);if(!f?.caption)continue
   const wanted=captionNorm(f.caption);let match=-1
   for(let j=0;j<ts.length;j++){
    if(ts[j].type==='paragraph_open'&&ts[j+1]?.type==='inline'&&captionNorm(ts[j+1].content)===wanted){match=j;break}
    if(ts[j].type==='blockquote_open'){
     let end=j+1,depth=1;for(;end<ts.length;end++){if(ts[end].type==='blockquote_open')depth++;if(ts[end].type==='blockquote_close'&&--depth===0)break}
     const body=ts.slice(j+1,end).filter((x:any)=>x.type==='inline').map((x:any)=>x.content).join(' ')
     if(captionNorm(body)===wanted){match=j;break}
    }
   }
   if(match>=0){const id='caption-'+m[1].replace(/[^a-zA-Z0-9_-]/g,'-');ts[match].attrSet('id',id);ts[match].attrJoin('class','figure-caption');ts[i].content=ts[i].content.replace(/\s+:show-caption="false"/g,'').replace(/\s*\/>/,` :show-caption="false" caption-id="${id}" />`)}
  }
  const clean=(s:string)=>s.replace(/<[^>]+>/g,'').replace(/[*`\\]/g,'').trim()
  for(let i=0;i<ts.length;i++){
   const t=ts[i]
   if(t.type==='heading_open'&&ts[i+1]?.type==='inline')heading=clean(ts[i+1].content)
   if(t.type==='table_open'){t.meta={...(t.meta||{}),manualTitle:heading,manualId:`t${++table}`}}
   if(t.type==='blockquote_open'){
    let end=i+1,depth=1;for(;end<ts.length;end++){if(ts[end].type==='blockquote_open')depth++;if(ts[end].type==='blockquote_close'){depth--;if(depth===0)break} }
    const inline=ts.slice(i+1,end).filter((x:any)=>x.type==='inline');const first=clean(inline[0]?.content||'');let kind='note'
    if(/^(这对你意味着什么|对你的意义|这意味着什么|WHAT THIS MEANS FOR YOU)/i.test(first))kind='takeaway'
    else if(/^(来源|Sources?)\s*[:：]/i.test(first))kind='sources'
    else if(/^(易踩的坑|陷阱|注意事项|FOOTGUN|WARNING|警告)/i.test(first))kind='warning'
    else if(/^(经验法则|RULE OF THUMB)/i.test(first))kind='rule'
    else if(/^(文档\s*[≠≠]|DOC\s*≠\s*CODE|文档与代码)/i.test(first))kind='doc-gap'
    else if(/^(PDF核对注|PDF 核对注|源文说明|〔源文)/i.test(first))kind='editorial'
    t.attrJoin('class',`manual-callout callout-${kind}`)
    if(isTableCaption(first))t.attrJoin('class','table-caption-container')
    if(kind!=='note'){t.attrSet('role','note');t.tag='aside';if(ts[end])ts[end].tag='aside'}
    if(kind!=='sources'&&kind!=='note'&&inline[0]&&first.length<45){
     const firstP=ts.slice(i+1,end).find((x:any)=>x.type==='paragraph_open');if(firstP)firstP.attrJoin('class','callout-label')
    }
    // A quoted paragraph immediately following a supplied figure is its caption.
    let prev=i-1;while(prev>=0&&ts[prev].type==='paragraph_close')prev--
    if(kind==='note'&&(/<(ManualFigure|BookFigure)\b/.test(ts[prev]?.content||'')||/<(ManualFigure|BookFigure)\b/.test(ts[prev-1]?.content||'')))t.attrJoin('class','figure-caption')
   }
   if(t.type==='paragraph_open'&&ts[i+1]?.type==='inline'){
    const s=clean(ts[i+1].content)
    if(isTableCaption(s))t.attrJoin('class','table-caption')
    if(s.startsWith('docs/cli.md 说')&&s.includes('--append-system-prompt')){t.attrJoin('class','manual-callout callout-doc-gap');t.attrSet('data-callout-title','文档 ≠ 代码')}
    if(s.startsWith('如果客户端需要知道“模型已完成回答”')){t.attrJoin('class','manual-callout callout-rule');t.attrSet('data-callout-title','经验法则')}
    if(s.startsWith('导入 @earendil-works/pi-ai 的扩展并不会得到根入口')){t.attrJoin('class','manual-callout callout-why');t.attrSet('data-callout-title','为什么重要')}
    if(/^(来源|Sources?)\s*[:：]/i.test(s))t.attrJoin('class','source-line')
    if(/^(图\s*(?:[1-7R]\.\d+|\d+)\s*[:： ]|FIG\.)/i.test(s))t.attrJoin('class','standalone-figure-caption')
   }
  }
  for(let i=0;i<ts.length;i++)if(ts[i].type==='table_open'){
   let end=i+1;while(end<ts.length&&ts[end].type!=='table_close')end++
   let caption=-1
   for(let j=end+1;j<Math.min(ts.length,end+16);j++){if(ts[j].type==='heading_open'||ts[j].type==='table_open')break;if((ts[j].attrGet('class')||'').split(' ').includes('table-caption')){caption=j;break}}
   if(caption>=0){const id=ts[caption].attrGet('id')||`table-caption-${ts[i].meta.manualId}`;ts[caption].attrSet('id',id);ts[i].attrSet('aria-describedby',id)}
  }
 })
 const open=md.renderer.rules.table_open||((tokens:any,idx:number,opts:any,env:any,self:any)=>self.renderToken(tokens,idx,opts))
 const close=md.renderer.rules.table_close||((tokens:any,idx:number,opts:any,env:any,self:any)=>self.renderToken(tokens,idx,opts))
 md.renderer.rules.table_open=(tokens:any,idx:number,opts:any,env:any,self:any)=>{
  let html=open(tokens,idx,opts,env,self);const described=tokens[idx].attrGet('aria-describedby')
  if(described)html=html.replace(/<table\b/,`<table aria-describedby="${md.utils.escapeHtml(described)}"`)
  return `<AdjustableTable id="${tokens[idx].meta.manualId}" title="${md.utils.escapeHtml(tokens[idx].meta.manualTitle)}">`+html
 }
 md.renderer.rules.table_close=(tokens:any,idx:number,opts:any,env:any,self:any)=>close(tokens,idx,opts,env,self)+'</AdjustableTable>\n'
}
