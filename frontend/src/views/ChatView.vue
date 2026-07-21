<script setup lang="ts">
import { ChevronLeft, MoreHorizontal } from 'lucide-vue-next'
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import ChatComposer from '@/components/chat/ChatComposer.vue'
import MessageBubble from '@/components/chat/MessageBubble.vue'
import { useChatStore } from '@/stores/chat'
import { useToastStore } from '@/stores/toast'
import type { ChatMessage } from '@/types/api'

const route = useRoute()
const chat = useChatStore()
const toast = useToastStore()
const scrollArea = ref<HTMLElement | null>(null)

async function load(id: string) {
  await chat.loadConversation(id)
  const prompt = typeof route.query.prompt === 'string' ? route.query.prompt : ''
  const attachmentIds =
    typeof route.query.attachments === 'string'
      ? route.query.attachments.split(',').filter(Boolean)
      : []
  if (prompt && chat.current?.messages.length === 0) await send(prompt, undefined, attachmentIds)
}

onMounted(() => load(String(route.params.id)).catch(handleError))
watch(() => route.params.id, (id) => load(String(id)).catch(handleError))
watch(() => chat.current?.messages.map((item) => item.content.length), scrollToBottom, { deep: true })

async function send(content: string, modelId?: string, attachmentIds: string[] = []) {
  try {
    await chat.send(content, modelId, attachmentIds)
  } catch (error) {
    handleError(error)
  }
}

function handleError(error: unknown) {
  toast.show(error instanceof Error ? error.message : '操作失败', 'error')
}

async function retry(message: ChatMessage) {
  const messages = chat.current?.messages || []
  const index = messages.findIndex((item) => item.id === message.id)
  const userMessage = [...messages.slice(0, index)].reverse().find((item) => item.role === 'user')
  if (userMessage) await send(userMessage.content)
}

async function scrollToBottom() {
  await nextTick()
  scrollArea.value?.scrollTo({ top: scrollArea.value.scrollHeight, behavior: 'smooth' })
}
</script>

<template>
  <div class="chat-page">
    <header class="chat-header">
      <RouterLink to="/" class="icon-button" title="返回首页"><ChevronLeft :size="20" /></RouterLink>
      <div><strong>{{ chat.current?.title || '对话' }}</strong><span>{{ chat.streaming ? '正在生成…' : 'MLab AI' }}</span></div>
      <button class="icon-button" title="更多操作"><MoreHorizontal :size="20" /></button>
    </header>
    <div ref="scrollArea" class="chat-scroll">
      <div v-if="!chat.current?.messages.length" class="empty-state"><span>AI</span><h2>开始这段对话</h2><p>说出你的目标，我会和你一起梳理并完成它。</p></div>
      <div class="message-list">
        <MessageBubble v-for="message in chat.current?.messages" :key="message.id" :message="message" @retry="retry" />
      </div>
    </div>
    <div class="chat-composer-wrap"><ChatComposer :loading="chat.streaming" @send="send" @stop="chat.stop" /><small>AI 可能会犯错，请核查重要信息。</small></div>
  </div>
</template>
