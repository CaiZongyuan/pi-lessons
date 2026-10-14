<script setup lang="ts">
import {computed,onBeforeUnmount,onMounted,ref,useId} from 'vue'
import {useRoute} from 'vitepress'
const props=defineProps<{id?:string,title?:string}>()
const root=ref<HTMLElement>();const rowCount=ref(0);const expanded=ref(false);const wide=ref(false);const announcement=ref('')
const uid=useId();const route=useRoute();const tableId=`table-${uid.replace(/[^\w-]/g,'')}`
const label=ref(props.title||'数据表');let table:HTMLTableElement|null=null;let widths:number[]=[];let defaults:number[]=[];let cols:HTMLTableColElement[]=[];let handles:HTMLElement[]=[];let cleanup:(()=>void)|undefined;let activeStop:(()=>void)|undefined
const key=computed(()=>`pi-docs:table-widths:${route.path}:${props.id||tableId}`)
function save(){try{localStorage.setItem(key.value,JSON.stringify(widths))}catch{}}
function apply(){if(!table)return;table.style.tableLayout='fixed';table.style.width=widths.reduce((a,b)=>a+b,0)+'px';cols.forEach((c,i)=>c.style.width=widths[i]+'px');handles.forEach((h,i)=>h.setAttribute('aria-valuenow',String(Math.round(widths[i]))))}
function setWidth(i:number,value:number,persist=true){widths[i]=Math.max(120,Math.min(1200,Math.round(value)));apply();announcement.value=`第 ${i+1} 列宽度 ${widths[i]} 像素`;if(persist)save()}
function reset(){widths=[...defaults];apply();try{localStorage.removeItem(key.value)}catch{};announcement.value='已重置为默认列宽'}
function toggleWide(){wide.value=!wide.value;announcement.value=wide.value?'表格已在当前阅读区域内展开':'表格已恢复常规视图'}
onMounted(()=>{
 table=root.value?.querySelector('table')||null;if(!table)return
 const head=table.tHead?.rows[0]||table.rows[0];if(!head)return
 rowCount.value=table.tBodies[0]?.rows.length||0
 table.setAttribute('aria-label',label.value);table.id=tableId
 const count=head.cells.length;const available=root.value?.clientWidth||720;const total=Math.max(available,count*175)
 const weights=Array.from(head.cells).map((c,i)=>{const samples=Array.from(table!.tBodies[0]?.rows||[]).slice(0,16).map(r=>r.cells[i]?.textContent?.length||0);return Math.max(1,Math.min(3,Math.sqrt(Math.max(c.textContent?.length||1,...samples))/4))})
 const sum=weights.reduce((a,b)=>a+b,0);defaults=weights.map(w=>Math.max(120,Math.round(total*w/sum)));widths=[...defaults]
 try{const saved=JSON.parse(localStorage.getItem(key.value)||'null');if(Array.isArray(saved)&&saved.length===count&&saved.every(v=>typeof v==='number'&&v>=120&&v<=1200))widths=saved}catch{}
 const group=document.createElement('colgroup');cols=widths.map(()=>document.createElement('col'));group.append(...cols);table.prepend(group)
 const controller=new AbortController();cleanup=()=>controller.abort()
 Array.from(head.cells).forEach((cell,i)=>{
  cell.setAttribute('scope','col');cell.classList.add('resizable-heading')
  const name=(cell.textContent||`第${i+1}列`).trim();const handle=document.createElement('button');handle.type='button';handle.className='column-resizer';handle.setAttribute('role','separator');handle.setAttribute('aria-orientation','vertical');handle.setAttribute('aria-label',`调整“${name}”列宽`);handle.setAttribute('aria-valuemin','120');handle.setAttribute('aria-valuemax','1200');handle.setAttribute('aria-controls',tableId);handle.title='拖动调整列宽；方向键微调；Home/End 最窄/最宽';cell.append(handle);handles.push(handle)
  handle.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();setWidth(i,e.key==='Home'?120:e.key==='End'?1200:widths[i]+(e.key==='ArrowRight'?1:-1)*(e.shiftKey?5:20))},{signal:controller.signal})
  handle.addEventListener('pointerdown',e=>{e.preventDefault();activeStop?.();const start=e.clientX,initial=widths[i];handle.focus();handle.setPointerCapture(e.pointerId);const move=(event:PointerEvent)=>setWidth(i,initial+event.clientX-start,false);const stop=()=>{handle.removeEventListener('pointermove',move);handle.removeEventListener('pointerup',stop);handle.removeEventListener('pointercancel',stop);save();activeStop=undefined};activeStop=stop;handle.addEventListener('pointermove',move);handle.addEventListener('pointerup',stop);handle.addEventListener('pointercancel',stop)},{signal:controller.signal})
 });apply()
})
onBeforeUnmount(()=>{activeStop?.();cleanup?.()})
</script>
<template><section ref="root" class="adjustable-table" :class="{'is-collapsed':rowCount>12&&!expanded,'is-expanded':wide}" :aria-label="label">
 <div class="table-toolbar"><span>{{label}}<small v-if="rowCount"> · {{rowCount}} 行</small></span><div class="table-actions"><button type="button" @click="reset">重置列宽</button><button type="button" :aria-pressed="wide" @click="toggleWide">{{wide?'恢复视图':'展开表格'}}</button></div></div>
 <p class="table-instruction">拖动表头右侧边线调整列宽；聚焦边线后可用 ← / →。宽表可横向滚动。</p>
 <div class="table-scroll" tabindex="0" :aria-label="`${label}，横向滚动区域`"><slot/></div>
 <button v-if="rowCount>12" type="button" class="show-rows" :aria-expanded="expanded" :aria-controls="tableId" @click="expanded=!expanded">{{expanded?'收起长表':`显示全部 ${rowCount} 行`}}</button>
 <span class="sr-only" role="status" aria-live="polite">{{announcement}}</span>
</section></template>
<style scoped>
.adjustable-table{border-top:1px solid #d8d2c7;border-bottom:1px solid #d8d2c7;max-width:100%;min-width:0;margin:26px 0;background:#faf7f2}.table-toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;font-size:14px;color:#435366}.table-toolbar>span{font-weight:600}.table-toolbar small{font-size:12px;font-weight:400;color:#7e8590}.table-actions{display:flex;gap:6px;flex-shrink:0}.table-actions button,.show-rows{font:12px var(--vp-font-family-base);min-height:34px;padding:5px 10px;border:1px solid #d9d2c6;color:#526274;background:#f4f1ea;cursor:pointer}.table-actions button:hover,.show-rows:hover{background:#e6ebea}.table-actions button[aria-pressed=true]{border-color:#658b98;background:#e5eeef}.table-instruction{font-size:12px!important;color:#7f8791;margin:0 0 10px!important;line-height:1.6!important}.table-scroll{overflow:auto;max-width:100%;overscroll-behavior-x:contain;max-height:620px}.is-expanded .table-scroll{max-height:none}.is-expanded{position:relative;z-index:1;background:#faf7f2;padding:0 14px;margin-left:-14px;margin-right:-14px;max-width:calc(100% + 28px);box-shadow:0 0 0 1px #c2ccd1}.show-rows{display:block;margin:12px auto}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}.table-scroll:focus-visible,button:focus-visible{outline:2px solid #356b81;outline-offset:2px}.table-scroll :deep(table){display:table!important;border-collapse:collapse;margin:0!important;max-width:none!important;font-size:14px;line-height:1.8}.table-scroll :deep(th){position:sticky;top:0;z-index:2;background:#faf7f2;color:#52616e;font:12px/1.6 var(--vp-font-family-mono);letter-spacing:.07em;border-top:0!important;border-left:0!important;border-right:0!important;border-bottom:2px solid #232a34!important;padding:10px 22px 10px 10px!important;vertical-align:top}.table-scroll :deep(td){border-left:0!important;border-right:0!important;border-color:#ddd5c9!important;padding:12px 10px!important;vertical-align:top;overflow-wrap:anywhere;word-break:normal;min-width:0!important}.table-scroll :deep(tr){border:0!important;background:transparent!important}.table-scroll :deep(code){white-space:normal;overflow-wrap:anywhere}.table-scroll :deep(.resizable-heading){position:sticky}.table-scroll :deep(.column-resizer){position:absolute;top:0;right:-1px;width:18px;height:100%;min-height:36px;padding:0;background:transparent;border:0;cursor:col-resize;touch-action:none;z-index:3}.table-scroll :deep(.column-resizer::after){content:'';position:absolute;top:20%;bottom:20%;left:8px;border-left:2px solid #9bb0ba}.table-scroll :deep(.column-resizer:hover::after),.table-scroll :deep(.column-resizer:focus-visible::after){border-color:#245b75;border-left-width:3px}.table-scroll :deep(.column-resizer:focus-visible){outline:2px solid #356b81;outline-offset:-2px}.is-collapsed :deep(tbody tr:nth-child(n+13)){display:none}@media(max-width:640px){.table-toolbar{align-items:flex-start;flex-direction:column;gap:6px}.table-actions button{min-height:36px;font-size:12px}.is-expanded{padding:0 6px;margin-left:-6px;margin-right:-6px;max-width:calc(100% + 12px)}.table-scroll{max-height:540px}}
</style>
