<script setup lang="ts">
import { Check, Circle, Pencil, Plus, Save, Sparkles, Trash2, X } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useToastStore } from '@/stores/toast'
import type { TaskItem, TaskTemplate } from '@/types/api'

const tasks = ref<TaskItem[]>([])
const templates = ref<TaskTemplate[]>([])
type TaskFilter = 'all' | TaskItem['status']
const filter = ref<TaskFilter>('all')
const filters: { value: TaskFilter; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'todo', label: '待办' },
  { value: 'doing', label: '进行中' },
  { value: 'done', label: '已完成' },
]
const newTitle = ref('')
const editingId = ref<string | null>(null)
const draft = reactive({ title: '', content: '' })
const toast = useToastStore()
const filtered = computed(() => filter.value === 'all' ? tasks.value : tasks.value.filter((item) => item.status === filter.value))

onMounted(load)
async function load() {
  ;[tasks.value, templates.value] = await Promise.all([api<TaskItem[]>('/tasks'), api<TaskTemplate[]>('/task-templates')])
}
async function create(title = newTitle.value, templateId?: string) {
  if (!title.trim()) return
  const item = await api<TaskItem>('/tasks', { method: 'POST', body: JSON.stringify({ title, content: '', template_id: templateId || null, priority: 'normal' }) })
  tasks.value.unshift(item); newTitle.value = ''; toast.show('任务已创建', 'success')
}
async function toggle(item: TaskItem) {
  item.status = item.status === 'done' ? 'todo' : 'done'
  Object.assign(item, await api<TaskItem>(`/tasks/${item.id}`, { method: 'PATCH', body: JSON.stringify({ status: item.status }) }))
}
async function remove(item: TaskItem) {
  await api(`/tasks/${item.id}`, { method: 'DELETE' }); tasks.value = tasks.value.filter((task) => task.id !== item.id)
}
async function breakDown(item: TaskItem) {
  try {
    const result = await api<{ content: string }>(`/tasks/${item.id}/ai-breakdown`, {
      method: 'POST',
      body: JSON.stringify({}),
    })
    item.content = result.content
    toast.show('已生成执行步骤', 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : 'AI 拆解失败', 'error')
  }
}
function startEdit(item: TaskItem) {
  editingId.value = item.id
  draft.title = item.title
  draft.content = item.content
}
async function saveEdit(item: TaskItem) {
  if (!draft.title.trim()) return
  Object.assign(
    item,
    await api<TaskItem>(`/tasks/${item.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title: draft.title.trim(), content: draft.content }),
    }),
  )
  editingId.value = null
  toast.show('任务已更新', 'success')
}
</script>

<template>
  <div class="page-container">
    <PageHeader title="任务" subtitle="把想法变成下一步行动" />
    <section class="task-create"><input v-model="newTitle" placeholder="添加一个任务…" @keyup.enter="create()" /><button class="button button--primary" @click="create()"><Plus :size="17" />添加</button></section>
    <section v-if="templates.length" class="template-strip"><button v-for="item in templates" :key="item.id" @click="create(item.title, item.id)"><strong>{{ item.title }}</strong><span>{{ item.description }}</span></button></section>
    <div class="segmented-control"><button v-for="item in filters" :key="item.value" :class="{ active: filter === item.value }" @click="filter = item.value">{{ item.label }}</button></div>
    <section class="task-list">
      <article v-for="item in filtered" :key="item.id" class="task-row" :class="{ done: item.status === 'done', editing: editingId === item.id }"><button class="task-check" :title="item.status === 'done' ? '标记待办' : '标记完成'" @click="toggle(item)"><Check v-if="item.status === 'done'" :size="16" /><Circle v-else :size="18" /></button><div v-if="editingId === item.id" class="task-edit"><input v-model="draft.title" maxlength="200" /><textarea v-model="draft.content" rows="4" maxlength="20000" /></div><div v-else><h3>{{ item.title }}</h3><p>{{ item.content || '尚未添加说明' }}</p></div><span class="tag">{{ item.priority === 'high' ? '高优先级' : '普通' }}</span><div class="task-row__actions"><template v-if="editingId === item.id"><button class="icon-button" title="保存" @click="saveEdit(item)"><Save :size="16" /></button><button class="icon-button" title="取消" @click="editingId = null"><X :size="16" /></button></template><template v-else><button class="icon-button" title="编辑" @click="startEdit(item)"><Pencil :size="16" /></button><button class="icon-button" title="AI 拆解" @click="breakDown(item)"><Sparkles :size="16" /></button><button class="icon-button" title="删除" @click="remove(item)"><Trash2 :size="16" /></button></template></div></article>
      <div v-if="!filtered.length" class="empty-state"><Check :size="28" /><h2>这里很清爽</h2><p>添加任务或从上方模板开始。</p></div>
    </section>
  </div>
</template>
