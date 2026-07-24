<script setup lang="ts">
import { FileText, LoaderCircle, Paperclip, Save, X } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useToastStore } from '@/stores/toast'
import type { Assistant, FileAsset, ModelConfig } from '@/types/api'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const assistantId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''))
const editing = computed(() => Boolean(assistantId.value))
const form = reactive({
  name: '',
  description: '',
  avatar: 'AI',
  category: '通用',
  system_prompt: '',
  opening_message: '',
  model_config: {
    model_config_id: '',
    temperature: 0.7,
    max_tokens: 2048,
  },
  knowledge_file_ids: [] as string[],
})
const knowledgeFiles = ref<FileAsset[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const models = ref<ModelConfig[]>([])

onMounted(async () => {
  const [modelItems, files] = await Promise.all([
    api<ModelConfig[]>('/model-configs'),
    api<FileAsset[]>('/files'),
  ])
  models.value = modelItems
  if (!editing.value) {
    form.model_config.model_config_id = models.value.find((item) => item.is_default)?.id || ''
    return
  }
  const assistant = await api<Assistant>(`/assistants/${assistantId.value}`)
  form.name = assistant.name
  form.description = assistant.description
  form.avatar = assistant.avatar
  form.category = assistant.category
  form.system_prompt = assistant.system_prompt
  form.opening_message = assistant.opening_message
  form.model_config = {
    model_config_id: String(assistant.model_config.model_config_id || ''),
    temperature: Number(assistant.model_config.temperature ?? 0.7),
    max_tokens: Number(assistant.model_config.max_tokens ?? 2048),
  }
  form.knowledge_file_ids = [...assistant.knowledge_file_ids]
  knowledgeFiles.value = files.filter((item) => assistant.knowledge_file_ids.includes(item.id))
})

async function save() {
  try {
    const payload = {
      ...form,
      model_config: {
        ...form.model_config,
        model_config_id: form.model_config.model_config_id || null,
      },
    }
    await api<Assistant>(editing.value ? `/assistants/${assistantId.value}` : '/assistants', {
      method: editing.value ? 'PATCH' : 'POST',
      body: JSON.stringify(payload),
    })
    window.dispatchEvent(new CustomEvent('mlab:assistants-changed'))
    toast.show(editing.value ? '助手已更新' : '助手已创建', 'success')
    await router.push('/assistants')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '创建失败', 'error')
  }
}

async function uploadKnowledge(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || []).slice(0, 20 - knowledgeFiles.value.length)
  uploading.value = true
  try {
    for (const file of files) {
      const body = new FormData()
      body.append('upload', file)
      const asset = await api<FileAsset>('/files', { method: 'POST', body })
      knowledgeFiles.value.push(asset)
      form.knowledge_file_ids.push(asset.id)
    }
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '知识文件上传失败', 'error')
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function removeKnowledge(id: string) {
  knowledgeFiles.value = knowledgeFiles.value.filter((item) => item.id !== id)
  form.knowledge_file_ids = form.knowledge_file_ids.filter((fileId) => fileId !== id)
}
</script>

<template>
  <div class="page-container page-container--narrow">
    <PageHeader :title="editing ? '编辑助手' : '创建助手'" subtitle="用清晰的角色、目标和边界定义你的专属 AI" />
    <form class="form-panel" @submit.prevent="save">
      <div class="assistant-preview"><span class="assistant-avatar assistant-avatar--large">{{ form.avatar || 'AI' }}</span><div><strong>{{ form.name || '未命名助手' }}</strong><p>{{ form.description || '助手描述会显示在这里' }}</p></div></div>
      <div class="form-grid">
        <label>助手名称<input v-model="form.name" required maxlength="100" placeholder="例如：产品策略顾问" /></label>
        <label>头像文字<input v-model="form.avatar" maxlength="2" placeholder="AI" /></label>
      </div>
      <label>分类<select v-model="form.category"><option>通用</option><option>写作</option><option>编程</option><option>分析</option><option>学习</option></select></label>
      <label>简介<textarea v-model="form.description" rows="2" maxlength="500" placeholder="一句话说明助手擅长什么" /></label>
      <label>开场白<textarea v-model="form.opening_message" rows="3" maxlength="2000" placeholder="例如：今天想先解决什么问题？" /></label>
      <label>系统提示词<textarea v-model="form.system_prompt" rows="10" maxlength="20000" placeholder="你是……你的目标是……回答时需要……" /></label>
      <div class="form-grid">
        <label>默认模型<select v-model="form.model_config.model_config_id"><option value="">跟随账户默认模型</option><option v-for="model in models" :key="model.id" :value="model.id">{{ model.alias }}</option></select></label>
        <label>最大输出 Token<input v-model.number="form.model_config.max_tokens" type="number" min="1" max="100000" /></label>
      </div>
      <label>温度（{{ form.model_config.temperature.toFixed(1) }}）<input v-model.number="form.model_config.temperature" type="range" min="0" max="2" step="0.1" /></label>
      <div class="knowledge-field">
        <div><strong>知识文件</strong><span>支持 TXT、Markdown 和 JSON，单个文件不超过 20MB。</span></div>
        <input ref="fileInput" class="visually-hidden" type="file" multiple accept=".txt,.md,.markdown,.json" @change="uploadKnowledge" />
        <button type="button" class="button button--soft" :disabled="uploading" @click="fileInput?.click()"><LoaderCircle v-if="uploading" class="spin" :size="16" /><Paperclip v-else :size="16" />添加文件</button>
        <div v-if="knowledgeFiles.length" class="knowledge-files"><span v-for="item in knowledgeFiles" :key="item.id"><FileText :size="15" /><span>{{ item.original_name }}</span><button type="button" title="移除" @click="removeKnowledge(item.id)"><X :size="14" /></button></span></div>
      </div>
      <div class="form-actions"><RouterLink to="/assistants" class="button button--soft">取消</RouterLink><button class="button button--primary"><Save :size="17" />{{ editing ? '保存修改' : '保存助手' }}</button></div>
    </form>
  </div>
</template>
