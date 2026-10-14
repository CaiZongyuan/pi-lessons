<script setup lang="ts">
import {computed,ref,useId} from 'vue'
import {withBase} from 'vitepress'
import durableGlyphs from '../durable-glyphs.json'
const props=defineProps<{id:string,showCaption?:boolean,captionId?:string}>()
const catalogs=import.meta.glob(['../figures/book-*.json','../figures/durable-*.json'],{eager:true,import:'default'})
const catalog=Object.values(catalogs).flatMap((v:any)=>Array.isArray(v)?v:(v.figures||[]))
const fig=computed<any>(()=>catalog.find((f:any)=>f.id===props.id))
const uid=useId().replace(/[^a-zA-Z0-9_-]/g,'')
const active=ref<string|null>(null)
const originalZoom=ref(false)
const picked=computed(()=>fig.value?.nodes?.find((n:any)=>n.id===active.value))
const nodes=computed<any[]>(()=>fig.value?.nodes||[])
const image=computed(()=>withBase(fig.value?.image||''))
const titleId=`book-figure-${uid}`
const split=(s:any)=>String(s||'').split('\n')
function points(e:any){
 if(e.points?.length)return e.points
 const a=nodes.value.find(n=>n.id===e.from),b=nodes.value.find(n=>n.id===e.to)
 if(!a||!b)return []
 const ax=a.x+a.w/2,ay=a.y+a.h/2,bx=b.x+b.w/2,by=b.y+b.h/2
 if(Math.abs(bx-ax)>Math.abs(by-ay))return [[ax+(bx>ax?a.w/2:-a.w/2),ay],[bx+(bx>ax?-b.w/2:b.w/2),by]]
 return [[ax,ay+(by>ay?a.h/2:-a.h/2)],[bx,by+(by>ay?-b.h/2:b.h/2)]]
}
function edgePath(e:any){return points(e).map((p:any,i:number)=>`${i?'L':'M'}${p[0]},${p[1]}`).join(' ')}
function midpoint(e:any){if(e.labelX!==undefined)return [e.labelX,e.labelY];const p=points(e);if(!p.length)return [0,0];const a=p[Math.floor((p.length-1)/2)],b=p[Math.ceil((p.length-1)/2)];return [(a[0]+b[0])/2,(a[1]+b[1])/2-9]}
function choose(n:any){active.value=n.id}
function key(e:KeyboardEvent,n:any){const i=nodes.value.indexOf(n);let j=i;if(e.key==='ArrowRight'||e.key==='ArrowDown')j=Math.min(i+1,nodes.value.length-1);else if(e.key==='ArrowLeft'||e.key==='ArrowUp')j=Math.max(i-1,0);else if(e.key==='Home')j=0;else if(e.key==='End')j=nodes.value.length-1;else if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(n);return}else return;e.preventDefault();active.value=nodes.value[j].id;(e.currentTarget as HTMLElement).closest('svg')?.querySelector<SVGElement>(`[data-node-index="${j}"]`)?.focus()}
</script>
<template>
<figure v-if="fig" class="book-figure" :aria-labelledby="titleId" :aria-describedby="captionId" :data-figure-id="id">
 <header><span class="book-figure-label">{{fig.label||`FIG. ${id}`}}</span><strong :id="titleId">{{fig.title}}</strong><span v-if="fig.page" class="book-figure-page">P. {{fig.page}}</span></header>
 <template v-if="fig.kind!=='original' && nodes.length">
  <p class="figure-help">选择图中节点查看说明 · 方向键切换</p>
  <div class="native-diagram-scroll" tabindex="0" :aria-label="`${fig.title}，可横向滚动`">
   <svg class="native-diagram" :class="{'dark-canvas':fig.theme==='dark'}" :style="{minWidth:`${fig.width||960}px`}" :viewBox="`0 0 ${fig.width||960} ${fig.height||400}`" :aria-label="fig.title" role="group">
    <defs><path v-for="(d,i) in fig.vectorDefs||[]" :key="`def${i}`" :id="`${uid}-vector-def-${i}`" :d="d.d||(durableGlyphs as Record<string,string>)[d.key]" /><clipPath v-for="(c,i) in fig.vectorClips||[]" :key="`clip${i}`" :id="`${uid}-vector-clip-${i}`" clipPathUnits="userSpaceOnUse"><path :d="c.d" :fill-rule="c.fillRule" :clip-path="c.parent===undefined?undefined:`url(#${uid}-vector-clip-${c.parent})`" /></clipPath><pattern :id="`${uid}-hatch`" width="7" height="7" patternUnits="userSpaceOnUse"><path d="M-2 2L2 -2M0 7L7 0M5 9L9 5" stroke="#89959b" stroke-width=".6" opacity=".5"/></pattern><marker :id="`${uid}-arrow`" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 1L9 5L0 9" fill="none" stroke="context-stroke" stroke-width="1.4"/></marker></defs>
    <g v-if="fig.vectorPaths" aria-hidden="true" class="source-vector-art">
     <g v-for="(p,i) in fig.vectorPaths" :key="`v${i}`" :clip-path="p.clip===undefined?undefined:`url(#${uid}-vector-clip-${p.clip})`"><component :is="p.ref===undefined?'path':'use'" :href="p.ref===undefined?undefined:`#${uid}-vector-def-${p.ref}`" :transform="p.transform" :d="p.d" :fill="p.fill||'none'" :stroke="p.stroke||'none'" :stroke-width="p.width" :fill-opacity="p.fillOpacity" :stroke-opacity="p.strokeOpacity" :stroke-linecap="p.lineCap" :stroke-linejoin="p.lineJoin" :fill-rule="p.fillRule" :stroke-dasharray="p.dashArray" :stroke-dashoffset="p.dashOffset" /></g>
    </g>
    <g v-for="(edge,i) in fig.edges||[]" :key="`e${i}`" class="diagram-edge" :class="{'is-related':active && (edge.from===active||edge.to===active)}">
     <path :d="edgePath(edge)" fill="none" :stroke="edge.color||'#89939a'" :stroke-width="edge.width||(edge.emphasis?2.8:1.5)" :stroke-dasharray="edge.dash==='dotted'?'2 4':edge.dashed?'6 5':undefined" :marker-end="edge.arrow===false?undefined:`url(#${uid}-arrow)`"/>
     <text v-if="edge.label" :x="midpoint(edge)[0]" :y="midpoint(edge)[1]" text-anchor="middle" class="edge-label"><tspan v-for="(line,j) in split(edge.label)" :key="j" :x="midpoint(edge)[0]" :dy="j?17:0">{{line}}</tspan></text>
    </g>
    <g v-for="(node,i) in nodes" :key="node.id" :data-node-index="i" class="diagram-node" :class="[`tone-${node.tone||'gray'}`,{'is-selected':active===node.id,'label-only':node.shape==='label','circle-node':node.shape==='circle','vector-hotspot':!!fig.vectorPaths}]" role="button" tabindex="0" :aria-pressed="active===node.id" :style="{'--fill':node.fill,'--stroke':node.stroke,'--text':node.text}" :aria-label="(node.ariaLabel||node.detail||String(node.label)).replaceAll('\n',' ')" @click="choose(node)" @keydown="key($event,node)">
     <ellipse v-if="node.shape==='circle' && !fig.vectorPaths" :cx="node.x+node.w/2" :cy="node.y+node.h/2" :rx="node.w/2-1" :ry="node.h/2-1"/>
     <rect v-else :x="node.x" :y="node.y" :width="node.w" :height="node.h" :rx="node.rx||0"/>
     <rect v-if="node.hatch && !fig.vectorPaths" :x="node.x" :y="node.y" :width="node.w" :height="node.h" :style="{fill:`url(#${uid}-hatch)`}" style="pointer-events:none"/>
     <foreignObject v-if="!fig.vectorPaths" :x="node.x" :y="node.y" :width="node.w" :height="node.h"><div xmlns="http://www.w3.org/1999/xhtml" class="node-copy" :class="{'centered':node.align==='center','right-aligned':node.align==='right'}"><span v-for="(line,j) in split(node.label)" :key="j">{{line}}</span></div></foreignObject>
     <title>{{node.detail||node.label}}</title>
    </g>
   </svg>
  </div>
  <div class="node-explanation" aria-live="polite"><template v-if="picked"><strong>{{String(picked.label).split('\n')[0]||picked.ariaLabel||picked.id}}</strong><p>{{picked.detail||String(picked.label).replaceAll('\n',' · ')}}</p></template><p v-else>图中结构与原书对应。选择节点可逐项阅读，原始图片保留在下方。</p></div>
 </template>
 <div v-else class="original-diagram" :class="{'zoom-original':originalZoom}"><button type="button" class="original-zoom" :aria-pressed="originalZoom" @click="originalZoom=!originalZoom">{{originalZoom?'适应宽度':'按原始尺寸查看'}}</button><img :src="image" :alt="fig.title" loading="lazy"><p v-if="fig.reason" class="figure-help">{{fig.reason}}</p></div>
 <figcaption v-if="fig.caption && showCaption!==false">{{fig.caption}}</figcaption>
 <ul v-if="fig.notes?.length" class="figure-notes"><li v-for="(note,i) in fig.notes" :key="i">{{note}}</li></ul>
 <details v-if="fig.sourceText" class="figure-text"><summary>读取图中文字</summary><pre>{{fig.sourceText}}</pre></details>
 <a v-if="fig.kind==='original'" :href="image" target="_blank" rel="noopener" class="full-image-link">在新标签页查看全尺寸原图 ↗</a>
 <p class="book-figure-source">{{fig.source}}<template v-if="fig.page"> · 原书第 {{fig.page}} 页</template></p>
 <details v-if="fig.kind!=='original'" class="source-comparison"><summary>对照原始图片</summary><a :href="image" target="_blank" rel="noopener" class="full-image-link">在新标签页查看全尺寸原图 ↗</a><img :src="image" :alt="`${fig.title}，原始图片`" loading="lazy"></details>
</figure>
<div v-else class="figure-missing" role="alert">图示 {{id}} 尚未加载。</div>
</template>
<style scoped>
.book-figure{--panel:#f4f1ea;--line:#e1dcd1;--ink:#232a34;border:1px solid var(--line);border-left:2px solid #72a29b;background:var(--panel);padding:18px 20px 0;margin:28px 0;min-width:0;max-width:100%;color:var(--ink)}
.book-figure header{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:12px;line-height:1.7}.book-figure-label,.book-figure-page{font:12px 'JetBrains Mono',monospace;letter-spacing:.13em}.book-figure header strong{font-size:16px;font-weight:600;color:#285e61}.book-figure-page{margin-left:auto;color:#737c87}.book-figure .figure-help{font-size:12px;line-height:1.6;color:#737c87;margin:7px 0 12px}.native-diagram-scroll{overflow:auto;max-width:100%;overscroll-behavior-x:contain;margin:10px 0}.native-diagram{display:block;width:100%;height:auto;overflow:visible}.diagram-node{cursor:pointer;outline:none;--fill:#e9e8e4;--stroke:#a8abad;--text:#46505b}.diagram-node rect,.diagram-node ellipse{fill:var(--fill);stroke:var(--stroke);stroke-width:1.5}.diagram-node.is-selected rect,.diagram-node:focus-visible rect,.diagram-node.is-selected ellipse,.diagram-node:focus-visible ellipse{stroke:var(--text);stroke-width:3}.label-only rect{fill:transparent;stroke:transparent}.label-only.is-selected rect,.label-only:focus-visible rect{stroke:var(--text);stroke-width:1;stroke-dasharray:4 3}.node-copy{box-sizing:border-box;padding:10px 11px;height:100%;font:13px/1.4 'JetBrains Mono','Noto Sans CJK SC',sans-serif;color:var(--text);display:flex;flex-direction:column;justify-content:center;overflow-wrap:anywhere;white-space:pre-wrap}.node-copy.centered{text-align:center}.node-copy.right-aligned{text-align:right}.node-copy span+span{margin-top:3px}.node-copy span:first-child{font-weight:600}.label-only .node-copy{padding:3px 4px}.edge-label{font:12px 'JetBrains Mono','Noto Sans CJK SC',sans-serif;fill:#5f6772;paint-order:stroke;stroke:#f4f1ea;stroke-width:4px;stroke-linejoin:round}.diagram-edge.is-related path{stroke:#346e76;stroke-width:2.5}.diagram-edge.is-related text{fill:#24405e}.tone-teal{--fill:#e0eeee;--stroke:#71a5a5;--text:#245f67}.tone-blue{--fill:#e1ebf3;--stroke:#89a9c3;--text:#315b7e}.tone-green{--fill:#e5eedb;--stroke:#9bb281;--text:#456932}.tone-config{--fill:#e0eee2;--stroke:#7fab89;--text:#387345}.tone-purple{--fill:#eee7f4;--stroke:#b19bc8;--text:#72548e}.tone-plum{--fill:#eee3ed;--stroke:#b994b6;--text:#835981}.tone-rose{--fill:#f4e4e9;--stroke:#cc8ca1;--text:#9b405c}.tone-amber{--fill:#f3e8cd;--stroke:#c4a058;--text:#8c6428}.tone-indigo{--fill:#e6e8f5;--stroke:#939ccd;--text:#485d96}.node-explanation{border-top:1px solid var(--line);padding:12px 0;min-height:65px}.node-explanation strong{font-size:14px;overflow-wrap:anywhere}.book-figure .node-explanation p{font-size:14px;line-height:1.8;margin:5px 0}.book-figure figcaption{font-family:'Source Serif 4','Noto Serif CJK SC',serif;font-size:14px;line-height:1.85;color:#56616d;margin:14px 0}.book-figure .book-figure-source{font:12px/1.8 'JetBrains Mono','Noto Sans CJK SC',sans-serif;color:#7b8490;overflow-wrap:anywhere;margin:12px 0}.book-figure .figure-notes{font-size:13px;line-height:1.8;padding-left:20px}.original-diagram{overflow:auto}.original-diagram img{display:block;max-width:100%;height:auto}.source-comparison{border-top:1px solid var(--line);margin:0 -20px;padding:0 20px}.source-comparison summary{cursor:pointer;min-height:42px;display:list-item;padding:10px 0;font-size:13px;color:#67717c}.source-comparison img{width:100%;height:auto;margin:8px 0 20px}.native-diagram-scroll:focus-visible,summary:focus-visible{outline:2px solid #346e76;outline-offset:3px}@media(max-width:680px){.book-figure{padding:14px 12px 0}.book-figure header strong{font-size:15px}.book-figure-page{margin-left:0}.source-comparison{margin:0 -12px;padding:0 12px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
.circle-node .node-copy{padding:0!important;text-align:center;font-size:14px}.dark-canvas{background:#0e1725}.dark-canvas .diagram-node{--fill:#152437;--stroke:#8293a6;--text:#b9c5d1}.dark-canvas .tone-teal{--fill:#0e1725;--stroke:#7cbfc1;--text:#82c4c7}.dark-canvas .tone-amber{--fill:#e2ad5e;--stroke:#e2ad5e;--text:#111c2a}.dark-canvas .tone-amber.label-only{--text:#dfb36d}.dark-canvas .tone-amber.circle-node{--fill:#0e1725;--text:#dfb36d}.dark-canvas .tone-plum{--fill:#372c40;--stroke:#b495bc;--text:#c0a1c7}.dark-canvas .tone-green{--fill:#a2c77e;--stroke:#a2c77e;--text:#a2c77e}.dark-canvas .label-only rect{fill:transparent;stroke:transparent}.dark-canvas .edge-label{stroke:#0e1725;fill:#abb9c8}.dark-canvas .node-copy{font-size:14px}.dark-canvas .diagram-edge.is-related path{stroke:#dce8f0}
.original-zoom{font-size:13px;min-height:36px;border:1px solid #b3bec5;padding:5px 12px;margin-bottom:12px}.zoom-original img{max-width:none!important;width:auto!important}.full-image-link{display:block;font-size:13px;line-height:1.8;margin:8px 0;color:#35667f}
.figure-text{border-top:1px solid var(--line);padding:10px 0;font-size:13px}.figure-text summary{cursor:pointer}.figure-text pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.8 'JetBrains Mono',sans-serif;max-height:360px;overflow:auto;padding:12px;background:#fff9;margin:8px 0}.vector-hotspot rect{fill:transparent!important;stroke:transparent!important}.vector-hotspot.is-selected rect,.vector-hotspot:focus-visible rect{fill:#5b8b9814!important;stroke:#35667f!important;stroke-width:2}.source-vector-art{pointer-events:none}
</style>
