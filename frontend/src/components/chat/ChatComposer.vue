<script setup lang="ts">
import { ArrowUp, FileText, LoaderCircle, Paperclip, Square, WandSparkles, X } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import { useToastStore } from '@/stores/toast'
import type { FileAsset, ModelConfig } from '@/types/api'

const props = withDefaults(
  defineProps<{ loading?: boolean; initialText?: string; autofocus?: boolean }>(),
  { loading: false, initialText: '', autofocus: false },
)
const emit = defineEmits<{
  send: [content: string, modelId?: string, attachmentIds?: string[]]
  stop: []
}>()
const text = ref(props.initialText)
const selectedModel = ref('')
const models = ref<ModelConfig[]>([])
const textarea = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const attachments = ref<FileAsset[]>([])
const uploading = ref(false)
const toast = useToastStore()
const canSend = computed(() => text.value.trim().length > 0 && !props.loading)

onMounted(async () => {
  models.value = await api<ModelConfig[]>('/model-configs').catch(() => [])
  selectedModel.value = models.value.find((item) => item.is_default)?.id || models.value[0]?.id || ''
  if (props.autofocus) await nextTick(() => textarea.value?.focus())
})

function submit() {
  if (!canSend.value) return
  const content = text.value.trim()
  text.value = ''
  emit(
    'send',
    content,
    selectedModel.value || undefined,
    attachments.value.map((item) => item.id),
  )
  attachments.value = []
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}

async function uploadFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const availableSlots = Math.max(0, 10 - attachments.value.length)
  const files = Array.from(input.files || []).slice(0, availableSlots)
  if (!files.length) return
  uploading.value = true
  try {
    for (const file of files) {
      const body = new FormData()
      body.append('upload', file)
      attachments.value.push(await api<FileAsset>('/files', { method: 'POST', body }))
    }
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '文件上传失败', 'error')
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function removeAttachment(id: string) {
  attachments.value = attachments.value.filter((item) => item.id !== id)
}
</script>

<template>
  <div class="composer">
    <div v-if="attachments.length" class="composer__attachments">
      <span v-for="item in attachments" :key="item.id">
        <FileText :size="14" />{{ item.original_name }}
        <button title="移除附件" @click="removeAttachment(item.id)"><X :size="13" /></button>
      </span>
    </div>
    <textarea
      ref="textarea"
      v-model="text"
      rows="3"
      maxlength="100000"
      placeholder="从任何想法开始… 按 Enter 发送，Shift Enter 换行"
      @keydown="onKeydown"
    />
    <div class="composer__toolbar">
      <div class="composer__actions">
        <button class="chip" title="选择能力"><WandSparkles :size="16" /> 智能</button>
        <input
          ref="fileInput"
          class="visually-hidden"
          type="file"
          multiple
          accept=".txt,.md,.json,.pdf,.png,.jpg,.jpeg,.webp"
          @change="uploadFiles"
        />
        <button class="icon-button" title="添加附件" :disabled="uploading" @click="fileInput?.click()">
          <LoaderCircle v-if="uploading" class="spin" :size="18" />
          <Paperclip v-else :size="18" />
        </button>
      </div>
      <div class="composer__submit">
        <select v-if="models.length" v-model="selectedModel" aria-label="选择模型">
          <option v-for="model in models" :key="model.id" :value="model.id">{{ model.alias }}</option>
        </select>
        <RouterLink v-else to="/settings/api-keys" class="composer__configure">配置模型</RouterLink>
        <button v-if="loading" class="send-button" title="停止生成" @click="emit('stop')"><Square :size="17" /></button>
        <button v-else class="send-button" title="发送消息" :disabled="!canSend" @click="submit"><ArrowUp :size="20" /></button>
      </div>
    </div>
  </div>
</template>
