<script setup lang="ts">
import { ExternalLink, Heart, Search, Wrench } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useToastStore } from '@/stores/toast'
import type { ToolItem } from '@/types/api'

const tools = ref<ToolItem[]>([])
const search = ref('')
const category = ref('全部')
const toast = useToastStore()
const categories = computed(() => ['全部', ...new Set(tools.value.map((item) => item.category))])
const filtered = computed(() => tools.value.filter((item) => (category.value === '全部' || item.category === category.value) && `${item.name}${item.description}`.toLowerCase().includes(search.value.toLowerCase())))
onMounted(async () => (tools.value = await api<ToolItem[]>('/tools')))

async function favorite(item: ToolItem) {
  await api(`/tools/${item.id}/favorite`, { method: 'POST' })
  item.is_favorite = !item.is_favorite
  toast.show(item.is_favorite ? '已收藏' : '已取消收藏', 'success')
}

function open(item: ToolItem) {
  if (item.external_url) window.open(item.external_url, '_blank', 'noopener,noreferrer')
}

async function useTool(item: ToolItem) {
  if (item.access_type === 'external_link') return open(item)
  try {
    const input =
      item.slug === 'calculator'
        ? { expression: window.prompt('输入要计算的算式', '(12 + 8) * 3') || '' }
        : { timezone: window.prompt('输入 IANA 时区', 'Asia/Shanghai') || 'Asia/Shanghai' }
    const result = await api<{ output: Record<string, unknown> }>(`/tools/${item.id}/execute`, {
      method: 'POST',
      body: JSON.stringify({ input }),
    })
    toast.show(
      item.slug === 'calculator'
        ? `计算结果：${String(result.output.result)}`
        : `${String(result.output.timezone)}：${String(result.output.display)}`,
      'success',
    )
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '工具执行失败', 'error')
  }
}
</script>

<template>
  <div class="page-container">
    <PageHeader title="工具库" subtitle="精选 AI 工具，连接你的完整工作流">
      <label class="search-field"><Search :size="17" /><input v-model="search" placeholder="搜索工具…" /></label>
    </PageHeader>
    <div class="segmented-control"><button v-for="item in categories" :key="item" :class="{ active: category === item }" @click="category = item">{{ item }}</button></div>
    <div v-if="!filtered.length" class="empty-state"><Wrench :size="28" /><h2>没有匹配的工具</h2></div>
    <div class="card-grid card-grid--3">
      <article v-for="item in filtered" :key="item.id" class="tool-card">
        <div class="tool-card__top"><span class="tool-icon">{{ item.name.slice(0, 1) }}</span><span class="tag">{{ item.category }}</span></div>
        <h3>{{ item.name }}</h3><p>{{ item.description }}</p>
        <div class="card-footer"><span class="rating">★ {{ item.rating.toFixed(1) }}</span><div><button class="icon-button" :class="{ active: item.is_favorite }" title="收藏" @click="favorite(item)"><Heart :size="17" /></button><button class="button button--primary" @click="useTool(item)">{{ item.access_type === 'external_link' ? '访问' : '使用' }}<ExternalLink v-if="item.access_type === 'external_link'" :size="15" /></button></div></div>
      </article>
    </div>
  </div>
</template>
