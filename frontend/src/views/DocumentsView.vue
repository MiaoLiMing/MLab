<script setup lang="ts">
import Placeholder from '@tiptap/extension-placeholder'
import StarterKit from '@tiptap/starter-kit'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import { Bold, FilePlus2, History, Italic, List, Save, Sparkles, Trash2, X } from 'lucide-vue-next'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useToastStore } from '@/stores/toast'
import type { DocumentItem, DocumentVersion } from '@/types/api'

const documents = ref<DocumentItem[]>([])
const selected = ref<DocumentItem | null>(null)
const saving = ref(false)
const aiWorking = ref(false)
const showVersions = ref(false)
const versions = ref<DocumentVersion[]>([])
const toast = useToastStore()
let saveTimer: number | undefined

const editor = useEditor({
  extensions: [StarterKit, Placeholder.configure({ placeholder: '开始写作，或使用 AI 帮你展开想法…' })],
  content: '',
  onUpdate: ({ editor: instance }) => scheduleSave(instance.getJSON(), instance.getText()),
})

onMounted(load)
onBeforeUnmount(() => window.clearTimeout(saveTimer))
watch(selected, (document) => editor.value?.commands.setContent(document?.content_json || ''))

async function load() {
  documents.value = await api<DocumentItem[]>('/documents')
  selected.value = documents.value[0] || null
}
async function create() {
  const document = await api<DocumentItem>('/documents', { method: 'POST', body: JSON.stringify({ title: '无标题文稿', content_json: {}, content_text: '' }) })
  documents.value.unshift(document); selected.value = document
}
function scheduleSave(contentJson: Record<string, unknown>, contentText: string) {
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => save(false, contentJson, contentText), 700)
}
async function save(
  createVersion = false,
  contentJson = editor.value?.getJSON() || {},
  contentText = editor.value?.getText() || '',
) {
  if (!selected.value) return
  saving.value = true
  try {
    const updated = await api<DocumentItem>(`/documents/${selected.value.id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        title: selected.value.title,
        content_json: contentJson,
        content_text: contentText,
        create_version: createVersion,
      }),
    })
    Object.assign(selected.value, updated)
  } finally { saving.value = false }
}
async function remove() {
  if (!selected.value) return
  await api(`/documents/${selected.value.id}`, { method: 'DELETE' })
  documents.value = documents.value.filter((item) => item.id !== selected.value?.id); selected.value = documents.value[0] || null
}
async function aiAction(action: 'rewrite' | 'continue' | 'summarize') {
  if (!selected.value?.content_text.trim()) return toast.show('先写一些内容再使用 AI', 'info')
  aiWorking.value = true
  try {
    const result = await api<{ content: string }>(`/documents/${selected.value.id}/ai-actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (action === 'continue') editor.value?.chain().focus().insertContent(`\n\n${result.content}`).run()
    else editor.value?.commands.setContent(result.content)
    toast.show('AI 处理完成', 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : 'AI 处理失败', 'error')
  } finally {
    aiWorking.value = false
  }
}
async function openVersions() {
  if (!selected.value) return
  versions.value = await api<DocumentVersion[]>(`/documents/${selected.value.id}/versions`)
  showVersions.value = true
}
async function restoreVersion(version: number) {
  if (!selected.value) return
  selected.value = await api<DocumentItem>(
    `/documents/${selected.value.id}/versions/${version}/restore`,
    { method: 'POST' },
  )
  editor.value?.commands.setContent(selected.value.content_json)
  showVersions.value = false
  toast.show(`已恢复版本 ${version}`, 'success')
}
</script>

<template>
  <div class="page-container documents-page">
    <PageHeader title="文稿" subtitle="专注写作，需要时让 AI 接手"><button class="button button--primary" @click="create"><FilePlus2 :size="17" />新建文稿</button></PageHeader>
    <div class="documents-layout">
      <aside class="document-list"><button v-for="item in documents" :key="item.id" :class="{ active: selected?.id === item.id }" @click="selected = item"><strong>{{ item.title }}</strong><span>版本 {{ item.current_version }}</span></button><div v-if="!documents.length" class="mini-empty">还没有文稿</div></aside>
      <section v-if="selected" class="editor-panel">
        <header class="editor-header"><input v-model="selected.title" maxlength="200" @change="save()" /><span>{{ saving ? '保存中…' : '已自动保存' }}</span><button class="icon-button" title="删除文稿" @click="remove"><Trash2 :size="17" /></button></header>
        <div class="editor-toolbar"><button title="粗体" :class="{ active: editor?.isActive('bold') }" @click="editor?.chain().focus().toggleBold().run()"><Bold :size="17" /></button><button title="斜体" :class="{ active: editor?.isActive('italic') }" @click="editor?.chain().focus().toggleItalic().run()"><Italic :size="17" /></button><button title="项目符号" :class="{ active: editor?.isActive('bulletList') }" @click="editor?.chain().focus().toggleBulletList().run()"><List :size="17" /></button><span /><button :disabled="aiWorking" @click="aiAction('rewrite')"><Sparkles :size="15" />改写</button><button :disabled="aiWorking" @click="aiAction('continue')">续写</button><button :disabled="aiWorking" @click="aiAction('summarize')">总结</button><button title="版本历史" @click="openVersions"><History :size="16" /></button><button title="创建版本并保存" @click="save(true)"><Save :size="16" /></button></div>
        <EditorContent :editor="editor" class="document-editor" />
      </section>
      <div v-else class="empty-state editor-empty"><FilePlus2 :size="30" /><h2>创建第一篇文稿</h2><p>内容会自动保存并保留版本。</p></div>
    </div>
    <div v-if="showVersions" class="modal-backdrop" @click.self="showVersions = false">
      <section class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="version-dialog-title"><header><div><h2 id="version-dialog-title">版本历史</h2><p>恢复操作会创建一个新版本，不会覆盖历史。</p></div><button class="icon-button" title="关闭" @click="showVersions = false"><X :size="18" /></button></header><div class="version-list"><button v-for="item in versions" :key="item.id" @click="restoreVersion(item.version)"><strong>版本 {{ item.version }}</strong><span>{{ new Date(item.created_at).toLocaleString() }}</span></button></div></section>
    </div>
  </div>
</template>
