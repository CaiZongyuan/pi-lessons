<script setup>
import {ref,watch,onMounted} from 'vue'
import {useData} from 'vitepress'
const hidden=ref(false);const {page}=useData()
function apply(){document.documentElement.classList.toggle('sidebar-hidden',hidden.value)}
watch(hidden,apply);watch(page,()=>{hidden.value=false})
onMounted(apply)
</script>
<template><button v-if="page.relativePath.startsWith('pi-')" class="desktop-sidebar-toggle" :aria-pressed="!hidden" @click="hidden=!hidden">{{hidden ? '显示目录' : '收起目录'}}</button></template>
