<script setup lang="ts">
import { BookOpen, Copy, Plus, Search, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useToastStore } from '@/stores/toast'
import type { ResourceItem } from '@/types/api'

const resources = ref<ResourceItem[]>([])
const search = ref('')
const showForm = ref(false)
const form = reactive({ resource_type: 'prompt', title: '', description: '', content: '', tags: [] as string[] })
const toast = useToastStore()
const filtered = computed(() => resources.value.filter((item) => `${item.title}${item.description}${item.tags.join('')}`.toLowerCase().includes(search.value.toLowerCase())))
onMounted(async () => (resources.value = await api<ResourceItem[]>('/resources')))
async function create() {
  const item = await api<ResourceItem>('/resources', { method: 'POST', body: JSON.stringify(form) })
  resources.value.unshift(item); showForm.value = false; Object.assign(form, { title: '', description: '', content: '' }); toast.show('资源已保存', 'success')
}
async function copy(item: ResourceItem) { await navigator.clipboard.writeText(item.content); toast.show('内容已复制', 'success') }
async function remove(item: ResourceItem) {
  await api(`/resources/${item.id}`, { method: 'DELETE' })
  resources.value = resources.value.filter((resource) => resource.id !== item.id)
  toast.show('资源已删除', 'success')
}
</script>

<template>
  <div class="page-container">
    <PageHeader title="资源" subtitle="沉淀可复用的提示词、模板和知识资料"><div class="header-actions"><label class="search-field"><Search :size="17" /><input v-model="search" placeholder="搜索资源…" /></label><button class="button button--primary" @click="showForm = !showForm"><Plus :size="17" />新建</button></div></PageHeader>
    <form v-if="showForm" class="inline-create form-panel" @submit.prevent="create"><div class="form-grid"><label>类型<select v-model="form.resource_type"><option value="prompt">提示词</option><option value="template">模板</option><option value="knowledge">知识</option></select></label><label>标题<input v-model="form.title" required /></label></div><label>简介<input v-model="form.description" /></label><label>内容<textarea v-model="form.content" rows="5" /></label><div class="form-actions"><button type="button" class="button button--soft" @click="showForm = false">取消</button><button class="button button--primary">保存</button></div></form>
    <div v-if="!filtered.length" class="empty-state"><BookOpen :size="28" /><h2>还没有资源</h2><p>保存常用提示词，下次直接复用。</p></div>
    <div class="card-grid card-grid--3"><article v-for="item in filtered" :key="item.id" class="resource-card"><div><span class="tag">{{ item.resource_type }}</span><span v-if="item.visibility === 'system'" class="resource-system">MLab 精选</span></div><h3>{{ item.title }}</h3><p>{{ item.description }}</p><div class="resource-preview">{{ item.content }}</div><div class="card-footer"><div><span v-for="tag in item.tags" :key="tag" class="tag">{{ tag }}</span></div><div class="resource-actions"><button class="icon-button" title="复制内容" @click="copy(item)"><Copy :size="17" /></button><button v-if="item.owner_id" class="icon-button" title="删除资源" @click="remove(item)"><Trash2 :size="16" /></button></div></div></article></div>
  </div>
</template>
