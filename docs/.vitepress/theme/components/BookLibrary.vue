<script setup>
import { withBase } from 'vitepress'
const books=[
 {id:'01',title:'Pi 1.04',subtitle:'TECHNICAL MANUAL',description:'编码智能体的系统提示词、工具、会话与压缩。',path:'/pi-104/',ready:true,status:'已收录 · 7 个章节与参考资料'},
 {id:'02',title:'Pi Durable',subtitle:'TECHNICAL SERIES',description:'原子提交、崩溃恢复、任务与实时观察。',path:'/pi-durable/',ready:true,status:'已收录 · 10 个章节与参考资料'}
]
</script>
<template><main class="library-page">
<header class="library-intro"><p class="eyebrow">PI / TECHNICAL LIBRARY</p><h1>技术文库<span>从系统结构，读懂智能体。</span></h1><p class="library-caption">选择一本书，开始阅读。</p></header>
<div class="book-shelf"><a v-for="book in books" :key="book.id" :href="withBase(book.path)" class="book-entry">
<div class="book-cover" :class="{'durable-cover':book.id==='02'}"><span class="cover-top">PI TECHNICAL SERIES <span>{{book.id}}</span></span><div class="cover-title">{{book.title}}<small>{{book.subtitle}}</small></div><svg viewBox="0 0 400 110" aria-hidden="true"><path d="M20 55H120M165 55H265M310 55H380"/><rect x="120" y="33" width="45" height="45"/><rect x="265" y="33" width="45" height="45"/><circle cx="20" cy="55" r="6"/><circle cx="380" cy="55" r="6"/><path d="M142 33V10H288V33M142 78V100H288V78" class="secondary-wire"/></svg><span class="cover-bottom">系统 · 接口 · 实践<span>中文阅读版</span></span></div>
<div class="book-info"><div><h2>{{book.title}}</h2><p>{{book.description}}</p></div><span class="book-link">{{book.ready?'进入阅读':'查看目录'}} ↗</span></div><span class="book-status">{{book.status}}</span>
</a></div><footer class="library-end"><span>02 本书籍</span><span>更多书籍，将在这里继续。</span></footer>
</main></template>
