import { defineStore } from 'pinia'
import { ref } from 'vue'

import { API_BASE, api, authHeaders } from '@/api/client'
import { readSSE } from '@/api/sse'
import type { ChatMessage, Conversation, ConversationDetail } from '@/types/api'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const current = ref<ConversationDetail | null>(null)
  const streaming = ref(false)
  const activeMessageId = ref<string | null>(null)
  const abortController = ref<AbortController | null>(null)

  async function loadConversations() {
    conversations.value = await api<Conversation[]>('/conversations')
  }

  async function createConversation(assistantId?: string, modelConfigId?: string) {
    const conversation = await api<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify({
        title: '新对话',
        assistant_id: assistantId || null,
        model_config_id: modelConfigId || null,
      }),
    })
    conversations.value.unshift(conversation)
    return conversation
  }

  async function loadConversation(id: string) {
    current.value = await api<ConversationDetail>(`/conversations/${id}`)
  }

  async function send(content: string, modelConfigId?: string, attachmentIds: string[] = []) {
    if (!current.value || streaming.value) return
    const conversationId = current.value.id
    const optimisticUser: ChatMessage = {
      id: crypto.randomUUID(),
      conversation_id: conversationId,
      parent_id: null,
      role: 'user',
      content,
      status: 'completed',
      model: null,
      input_tokens: 0,
      output_tokens: 0,
      error_code: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      attachments: [],
    }
    current.value.messages.push(optimisticUser)
    const optimisticAssistant: ChatMessage = {
      ...optimisticUser,
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      status: 'streaming',
    }
    current.value.messages.push(optimisticAssistant)
    streaming.value = true
    abortController.value = new AbortController()
    try {
      const response = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          content,
          model_config_id: modelConfigId || null,
          attachment_ids: attachmentIds,
        }),
        signal: abortController.value.signal,
      })
      if (!response.ok) {
        const body = (await response.json()) as { error?: { message?: string } }
        throw new Error(body.error?.message || '发送失败')
      }
      for await (const event of readSSE(response)) {
        if (event.event === 'message.start') {
          activeMessageId.value = String(event.data.message_id)
          optimisticAssistant.id = activeMessageId.value
        } else if (event.event === 'message.delta') {
          optimisticAssistant.content += String(event.data.content || '')
        } else if (event.event === 'message.done') {
          optimisticAssistant.status = String(event.data.status) as ChatMessage['status']
        } else if (event.event === 'error') {
          optimisticAssistant.status = 'failed'
          optimisticAssistant.error_code = String(event.data.code || 'MODEL_ERROR')
          throw new Error(String(event.data.message || '模型生成失败'))
        }
      }
      await loadConversation(conversationId)
      await loadConversations()
    } finally {
      streaming.value = false
      activeMessageId.value = null
      abortController.value = null
    }
  }

  async function stop() {
    if (activeMessageId.value) {
      await api(`/conversations/messages/${activeMessageId.value}/stop`, { method: 'POST' })
    }
    abortController.value?.abort()
    streaming.value = false
  }

  return {
    conversations,
    current,
    streaming,
    activeMessageId,
    loadConversations,
    createConversation,
    loadConversation,
    send,
    stop,
  }
})
