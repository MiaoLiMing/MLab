<script setup lang="ts">
import { FileText, ListTodo, MessageSquare, Search, Shapes } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import type { SearchResult } from '@/types/api'

const query = ref('')
const results = ref<SearchResult[]>([])
const loading = ref(false)
let timer: number | undefined
const typeLabels: Record<string, string> = {
  conversation: '对话',
  task: '任务',
  document: '文稿',
  resource: '资源',
}
const grouped = computed(() =>
  Object.entries(
    results.value.reduce<Record<string, SearchResult[]>>((groups, item) => {
      ;(groups[item.result_type] ||= []).push(item)
      return groups
    }, {}),
  ),
)

watch(query, (value) => {
  window.clearTimeout(timer)
  if (!value.trim()) {
    results.value = []
    return
  }
  timer = window.setTimeout(() => search(value), 250)
})

async function search(value: string) {
  loading.value = true
  try {
    results.value = await api<SearchResult[]>(`/search?q=${encodeURIComponent(value.trim())}`)
  } finally {
    loading.value = false
  }
}

function iconFor(type: SearchResult['result_type']) {
  return { conversation: MessageSquare, task: ListTodo, document: FileText, resource: Shapes }[type]
}
</script>

<template>
  <div class="page-container page-container--narrow search-page">
    <PageHeader title="搜索" subtitle="查找你的对话、任务、文稿和资源" />
    <label class="global-search"><Search :size="21" /><input v-model="query" autofocus placeholder="输入关键词…" /><span v-if="loading">搜索中…</span></label>
    <div v-if="grouped.length" class="search-results">
      <section v-for="group in grouped" :key="group[0]"><h2>{{ typeLabels[group[0]] }}</h2><RouterLink v-for="item in group[1]" :key="item.id" :to="item.path"><component :is="iconFor(item.result_type)" :size="18" /><div><strong>{{ item.title }}</strong><p>{{ item.snippet || typeLabels[item.result_type] }}</p></div></RouterLink></section>
    </div>
    <div v-else-if="query && !loading" class="empty-state"><Search :size="28" /><h2>没有找到相关内容</h2><p>尝试使用更短或不同的关键词。</p></div>
  </div>
</template>
