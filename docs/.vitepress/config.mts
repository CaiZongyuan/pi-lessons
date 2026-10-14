import { defineConfig } from 'vitepress'
import { manualMarkdown } from './manual-markdown'
import navigation from './navigation.json'
import durableNavigation from './durable-navigation.json'
const durableGroups=[...new Set(durableNavigation.map(r=>r.chapter))].map(chapter=>{const rows=durableNavigation.filter(r=>r.chapter===chapter);return {text:`${chapter==='R'?'R':chapter.padStart(2,'0')} · ${rows[0].chapterTitle}`,collapsed:chapter!=='1',items:rows.map(r=>({text:`${r.number} ${r.title}`,link:r.link}))}})
const groups = ['1','2','3','4','5','6','7','R'].map(chapter => {
 const rows=navigation.filter(r=>r.chapter===chapter)
 return {text:`${chapter==='R'?'R':chapter.padStart(2,'0')} · ${rows[0].chapterTitle}`,collapsed:chapter!=='1',items:rows.map((r,i)=>({text:`${chapter}.${i+1} ${r.title}`,link:r.link}))}
})
// PI_PAGES_BASE lets GitHub Pages host the site under /pi-lessons/ while local
// dev keeps the root base. Raw HTML anchors in the supplied Markdown carry
// site-absolute hrefs, so a core rule prefixes them with the same base.
const base = process.env.PI_PAGES_BASE || '/'
const joinBase = (p: string) => (base.endsWith('/') ? base : base + '/') + p.replace(/^\//, '')
export default defineConfig({
 outDir: process.env.PI_BUILD_DIR || undefined,
 base,
 lang: 'zh-CN', title: 'Pi · 技术文库', description: 'Pi 技术手册中文阅读版',
 appearance: false, cleanUrls: true,
 head: [['link', { rel:'icon', type:'image/svg+xml', href: joinBase('favicon.svg') }]],
 markdown: { theme: 'github-light', config(md) { md.set({ breaks: false });
  md.core.ruler.push('pi_site_base', state => {
   const prefix = base.endsWith('/') ? base : base + '/'
   const fix = (tokens: any[]) => { for (const t of tokens) {
    if ((t.type==='html_block' || t.type==='html_inline') && /="\/(?!\/)/.test(t.content))
     t.content = t.content.replace(/(href|src)="\/(?!\/)/g, `$1="${prefix}`)
    if (t.children) fix(t.children)
   } }
   fix(state.tokens)
  })
  ;manualMarkdown(md) } },
 themeConfig: {
  logo: joinBase('favicon.svg'), siteTitle: 'Pi / 技术文库',
  nav: [{text:'全部书籍',link:'/'},{text:'Pi 1.04',link:'/pi-104/'},{text:'Pi Durable',link:'/pi-durable/'}],
  sidebar: {'/pi-104/': [{text:'PI 1.04',items:[{text:'本书目录',link:'/pi-104/'},{text:'如何阅读本书',link:'/pi-104/preface'}]},...groups], '/pi-durable/':[{text:'PI DURABLE',items:[{text:'本书目录',link:'/pi-durable/'},{text:'如何阅读本书',link:'/pi-durable/preface'}]},...durableGroups]},
  outline: { level:2, label:'本页目录' }, docFooter:{prev:'上一节',next:'下一节'},
  sidebarMenuLabel:'书籍目录', returnToTopLabel:'返回顶部', darkModeSwitchLabel:'配色',
  footer: { message:'PI / TECHNICAL LIBRARY',copyright:'中文阅读版 · Pi 1.0.4 / Pi Durable 1.0.3' }
 }
})
