<script setup lang="ts">
import { Search, Users } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useToastStore } from '@/stores/toast'
import type { Assistant } from '@/types/api'

const assistants = ref<Assistant[]>([])
const search = ref('')
const toast = useToastStore()
const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  return term ? assistants.value.filter((item) => `${item.name}${item.description}`.toLowerCase().includes(term)) : assistants.value
})

onMounted(load)
async function load() {
  assistants.value = await api<Assistant[]>('/assistants')
}
async function toggleInstall(item: Assistant) {
  try {
    await api(`/assistants/${item.id}/install`, { method: item.installed ? 'DELETE' : 'POST' })
    item.installed = !item.installed
    toast.show(item.installed ? '助手已安装' : '助手已移除', 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '操作失败', 'error')
  }
}
</script>

<template>
  <div class="page-container">
    <PageHeader title="助手市场" subtitle="发现精选 AI 助手，一键安装到你的工作台">
      <label class="search-field"><Search :size="17" /><input v-model="search" placeholder="搜索助手…" /></label>
    </PageHeader>
    <div v-if="!filtered.length" class="empty-state"><Users :size="28" /><h2>没有找到助手</h2><p>换一个关键词试试。</p></div>
    <div class="card-grid card-grid--3">
      <article v-for="item in filtered" :key="item.id" class="assistant-card">
        <div class="assistant-card__head"><span class="assistant-avatar">{{ item.avatar }}</span><div><h3>{{ item.name }}</h3><p>@{{ item.slug }} · {{ (item.usage_count / 1000).toFixed(1) }}k 使用</p></div></div>
        <p class="assistant-card__description">{{ item.description }}</p>
        <div class="card-footer"><span class="tag">{{ item.category }}</span><button class="button" :class="item.installed ? 'button--soft' : 'button--primary'" @click="toggleInstall(item)">{{ item.installed ? '已安装' : '安装' }}</button></div>
      </article>
    </div>
  </div>
</template>

