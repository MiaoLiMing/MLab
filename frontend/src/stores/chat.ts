import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api, authenticatedFetch } from '@/api/client'
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

  async function send(
    content: string,
    modelConfigId?: string,
    attachmentIds: string[] = [],
    sourceMessageId?: string,
  ) {
    if (!current.value || streaming.value) return
    const conversationId = current.value.id
    const sourceIndex = sourceMessageId
      ? current.value.messages.findIndex(
          (message) => message.id === sourceMessageId && message.role === 'user',
        )
      : -1
    const existingSource = sourceIndex >= 0 ? current.value.messages[sourceIndex] : undefined
    const optimisticUser: ChatMessage = existingSource || {
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
      attachments: attachmentIds.map((fileId) => ({
        id: `pending-${fileId}`,
        file_id: fileId,
        attachment_type: 'file',
        attachment_metadata: {},
      })),
    }
    optimisticUser.content = content
    if (attachmentIds.length) {
      optimisticUser.attachments = attachmentIds.map((fileId) => ({
        id: `pending-${fileId}`,
        file_id: fileId,
        attachment_type: 'file',
        attachment_metadata: {},
      }))
    }
    if (existingSource) current.value.messages.splice(sourceIndex + 1)
    else current.value.messages.push(optimisticUser)
    const optimisticAssistant: ChatMessage = {
      ...optimisticUser,
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      status: 'streaming',
      attachments: [],
    }
    current.value.messages.push(optimisticAssistant)
    streaming.value = true
    abortController.value = new AbortController()
    try {
      const response = await authenticatedFetch(`/conversations/${conversationId}/messages`, {
        method: 'POST',
        body: JSON.stringify({
          content,
          model_config_id: modelConfigId || null,
          attachment_ids: attachmentIds,
          source_message_id: sourceMessageId || null,
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
          optimisticAssistant.tool_status = undefined
        } else if (event.event === 'tool.call') {
          optimisticAssistant.tool_status = `正在使用 ${String(event.data.name || '工具')}`
        } else if (event.event === 'tool.result') {
          optimisticAssistant.tool_status = '工具执行完成，正在整理结果'
        } else if (event.event === 'error') {
          optimisticAssistant.status = 'failed'
          optimisticAssistant.error_code = String(event.data.code || 'MODEL_ERROR')
          throw new Error(String(event.data.message || '模型生成失败'))
        }
      }
      await loadConversation(conversationId)
      await loadConversations()
    } catch (error) {
      if (abortController.value?.signal.aborted) {
        optimisticAssistant.status = 'stopped'
        return
      }
      optimisticAssistant.status = 'failed'
      optimisticAssistant.error_code =
        error instanceof Error && error.name ? error.name : 'REQUEST_FAILED'
      throw error
    } finally {
      streaming.value = false
      activeMessageId.value = null
      abortController.value = null
    }
  }

  async function stop() {
    abortController.value?.abort()
    if (activeMessageId.value) {
      await api(`/conversations/messages/${activeMessageId.value}/stop`, { method: 'POST' }).catch(
        () => undefined,
      )
    }
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
