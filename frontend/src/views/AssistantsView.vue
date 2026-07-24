<script setup lang="ts">
import { Pencil, Plus, Search, Trash2, Users } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { Assistant } from '@/types/api'

const assistants = ref<Assistant[]>([])
const search = ref('')
const category = ref('全部')
const toast = useToastStore()
const auth = useAuthStore()
const pendingRemoval = ref<Assistant | null>(null)
const removing = ref(false)
const categories = computed(() => ['全部', ...new Set(assistants.value.map((item) => item.category))])
const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  return assistants.value.filter(
    (item) =>
      (category.value === '全部' || item.category === category.value) &&
      (!term || `${item.name}${item.description}`.toLowerCase().includes(term)),
  )
})

onMounted(load)
async function load() {
  assistants.value = await api<Assistant[]>('/assistants')
}
async function toggleInstall(item: Assistant) {
  try {
    await api(`/assistants/${item.id}/install`, { method: item.installed ? 'DELETE' : 'POST' })
    item.installed = !item.installed
    window.dispatchEvent(new CustomEvent('mlab:assistants-changed'))
    toast.show(item.installed ? '助手已安装' : '助手已移除', 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '操作失败', 'error')
  }
}
async function remove(item: Assistant) {
  pendingRemoval.value = item
}
async function confirmRemove() {
  const item = pendingRemoval.value
  if (!item) return
  removing.value = true
  try {
    await api(`/assistants/${item.id}`, { method: 'DELETE' })
    await load()
    window.dispatchEvent(new CustomEvent('mlab:assistants-changed'))
    pendingRemoval.value = null
    toast.show('助手已删除', 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '删除失败', 'error')
  } finally {
    removing.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <PageHeader title="助手市场" subtitle="发现精选 AI 助手，一键安装到你的工作台">
      <div class="header-actions">
        <label class="search-field"><Search :size="17" /><input v-model="search" placeholder="搜索助手…" /></label>
        <RouterLink to="/assistants/new" class="button button--primary"><Plus :size="17" />创建助手</RouterLink>
      </div>
    </PageHeader>
    <div class="segmented-control"><button v-for="item in categories" :key="item" :class="{ active: category === item }" @click="category = item">{{ item }}</button></div>
    <div v-if="!filtered.length" class="empty-state"><Users :size="28" /><h2>没有找到助手</h2><p>换一个关键词试试。</p></div>
    <div class="card-grid card-grid--3">
      <article v-for="item in filtered" :key="item.id" class="assistant-card">
        <div class="assistant-card__head"><span class="assistant-avatar">{{ item.avatar }}</span><div><h3>{{ item.name }}</h3><p>@{{ item.slug }} · {{ (item.usage_count / 1000).toFixed(1) }}k 使用</p></div></div>
        <p class="assistant-card__description">{{ item.description }}</p>
        <div class="card-footer"><span class="tag">{{ item.category }}</span><div v-if="item.owner_id === auth.user?.id" class="card-actions"><RouterLink :to="`/assistants/${item.id}/edit`" class="icon-button" title="编辑助手"><Pencil :size="16" /></RouterLink><button class="icon-button danger-text" title="删除助手" @click="remove(item)"><Trash2 :size="16" /></button></div><button v-else class="button" :class="item.installed ? 'button--soft' : 'button--primary'" @click="toggleInstall(item)">{{ item.installed ? '移除' : '安装' }}</button></div>
      </article>
    </div>
  </div>
  <ConfirmDialog
    :open="Boolean(pendingRemoval)"
    title="删除这个助手？"
    :description="`“${pendingRemoval?.name || '当前助手'}”将被永久删除，无法恢复。`"
    confirm-label="确认删除"
    :busy="removing"
    @cancel="pendingRemoval = null"
    @confirm="confirmRemove"
  />
</template>
