<script setup lang="ts">
import { Brain, Pencil, Plus, Save, Trash2, X } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { MemoryItem } from '@/types/api'

const memories = ref<MemoryItem[]>([])
const newMemory = ref('')
const editingId = ref<string | null>(null)
const draft = ref('')
const auth = useAuthStore()
const toast = useToastStore()
onMounted(async () => (memories.value = await api<MemoryItem[]>('/memories')))
async function create() { if (!newMemory.value.trim()) return; const item = await api<MemoryItem>('/memories', { method: 'POST', body: JSON.stringify({ content: newMemory.value, category: 'preference' }) }); memories.value.unshift(item); newMemory.value = '' }
async function toggle(item: MemoryItem) { item.enabled = !item.enabled; Object.assign(item, await api<MemoryItem>(`/memories/${item.id}`, { method: 'PATCH', body: JSON.stringify({ enabled: item.enabled }) })) }
async function remove(item: MemoryItem) { await api(`/memories/${item.id}`, { method: 'DELETE' }); memories.value = memories.value.filter((memory) => memory.id !== item.id); toast.show('记忆已删除', 'success') }
async function toggleGlobal() { await auth.updateProfile({ memory_enabled: !auth.user?.memory_enabled }); toast.show(auth.user?.memory_enabled ? '记忆已开启' : '记忆已关闭', 'success') }
function startEdit(item: MemoryItem) { editingId.value = item.id; draft.value = item.content }
async function saveEdit(item: MemoryItem) {
  if (!draft.value.trim()) return
  Object.assign(item, await api<MemoryItem>(`/memories/${item.id}`, { method: 'PATCH', body: JSON.stringify({ content: draft.value.trim() }) }))
  editingId.value = null
  toast.show('记忆已更新', 'success')
}
</script>

<template>
  <div class="page-container page-container--narrow">
    <PageHeader title="记忆" subtitle="管理 AI 可以在后续对话中使用的信息"><label class="switch-row"><span>启用记忆</span><button class="switch" :class="{ active: auth.user?.memory_enabled }" role="switch" :aria-checked="auth.user?.memory_enabled" @click="toggleGlobal"><i /></button></label></PageHeader>
    <section class="memory-create"><Brain :size="22" /><textarea v-model="newMemory" rows="2" placeholder="例如：我偏好简洁、直接的回答风格" /><button class="button button--primary" @click="create"><Plus :size="17" />添加</button></section>
    <div class="memory-list"><article v-for="item in memories" :key="item.id" class="memory-row" :class="{ disabled: !item.enabled }"><span class="memory-dot" /><div><textarea v-if="editingId === item.id" v-model="draft" rows="3" maxlength="5000" /><template v-else><p>{{ item.content }}</p><span>{{ item.category }} · {{ new Date(item.updated_at).toLocaleDateString() }}</span></template></div><button class="switch" :class="{ active: item.enabled }" title="启用或停用" @click="toggle(item)"><i /></button><div class="memory-actions"><template v-if="editingId === item.id"><button class="icon-button" title="保存" @click="saveEdit(item)"><Save :size="16" /></button><button class="icon-button" title="取消" @click="editingId = null"><X :size="16" /></button></template><template v-else><button class="icon-button" title="编辑" @click="startEdit(item)"><Pencil :size="16" /></button><button class="icon-button" title="删除" @click="remove(item)"><Trash2 :size="16" /></button></template></div></article><div v-if="!memories.length" class="empty-state"><Brain :size="30" /><h2>还没有记忆</h2><p>你可以主动添加，自动提取将在后台任务启用后出现。</p></div></div>
  </div>
</template>
