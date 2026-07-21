<script setup lang="ts">
import { Bot, RefreshCw } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useToastStore } from '@/stores/toast'
import type { TaskTemplate } from '@/types/api'

const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()
const toast = useToastStore()
const templates = ref<TaskTemplate[]>([])
const offset = ref(0)
const visibleTemplates = computed(() => {
  if (templates.value.length <= 3) return templates.value
  return [...templates.value, ...templates.value].slice(offset.value, offset.value + 3)
})

onMounted(async () => {
  templates.value = await api<TaskTemplate[]>('/task-templates').catch(() => [])
})

async function start(content: string, modelId?: string, attachmentIds: string[] = []) {
  try {
    const conversation = await chat.createConversation(undefined, modelId)
    await router.push({
      path: `/chat/${conversation.id}`,
      query: {
        prompt: content,
        attachments: attachmentIds.length ? attachmentIds.join(',') : undefined,
      },
    })
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '创建对话失败', 'error')
  }
}

async function useTemplate(template: TaskTemplate) {
  await start(template.prompt_template)
}
</script>

<template>
  <div class="home-page">
    <section class="home-hero">
      <div class="home-brand"><span><Bot :size="22" /></span> MLab AI</div>
      <h1>只等你的召唤</h1>
      <p>{{ auth.user?.display_name || '你好' }}，我在这里。需要时随时叫我。</p>
      <ChatComposer autofocus @send="start" />
    </section>
    <section class="recommendations">
      <div class="section-label"><span>为你推荐的一些功能</span><button @click="offset = (offset + 1) % Math.max(templates.length, 1)"><RefreshCw :size="15" />换一批</button></div>
      <button v-for="template in visibleTemplates" :key="template.id" class="recommendation-card" @click="useTemplate(template)">
        <div class="recommendation-card__content"><span class="recommendation-icon">{{ template.title.slice(0, 1) }}</span><div><h3>{{ template.title }}</h3><p>{{ template.description }}</p></div></div>
        <span class="tag">{{ template.category }}</span><span class="button button--soft">开始使用</span>
      </button>
    </section>
  </div>
</template>
