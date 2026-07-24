<script setup lang="ts">
import { Archive, Check, ChevronLeft, MoreHorizontal, Pencil, Trash2, X } from 'lucide-vue-next'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import MessageBubble from '@/components/chat/MessageBubble.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import { useChatStore } from '@/stores/chat'
import { useToastStore } from '@/stores/toast'
import type { Assistant, ChatMessage } from '@/types/api'

const route = useRoute()
const router = useRouter()
const chat = useChatStore()
const toast = useToastStore()
const scrollArea = ref<HTMLElement | null>(null)
const openingMessage = ref('')
const moreOpen = ref(false)
const renaming = ref(false)
const titleDraft = ref('')
const deleteOpen = ref(false)
const busy = ref(false)

async function load(id: string) {
  await chat.loadConversation(id)
  openingMessage.value = ''
  if (chat.current?.assistant_id) {
    openingMessage.value = (
      await api<Assistant>(`/assistants/${chat.current.assistant_id}`).catch(() => null)
    )?.opening_message || ''
  }
  const prompt = typeof route.query.prompt === 'string' ? route.query.prompt : ''
  const attachmentIds =
    typeof route.query.attachments === 'string'
      ? route.query.attachments.split(',').filter(Boolean)
      : []
  if (prompt && chat.current?.messages.length === 0) await send(prompt, undefined, attachmentIds)
}

onMounted(() => {
  load(String(route.params.id)).catch(handleError)
  document.addEventListener('pointerdown', closeMoreOnOutside)
})
onBeforeUnmount(() => document.removeEventListener('pointerdown', closeMoreOnOutside))
watch(() => route.params.id, (id) => load(String(id)).catch(handleError))
watch(() => chat.current?.messages.map((item) => item.content.length), scrollToBottom, { deep: true })

async function send(
  content: string,
  modelId?: string,
  attachmentIds: string[] = [],
  sourceMessageId?: string,
) {
  try {
    await chat.send(content, modelId, attachmentIds, sourceMessageId)
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
  if (userMessage) await send(userMessage.content, undefined, [], userMessage.id)
}

async function edit(message: ChatMessage, content: string) {
  await send(content, undefined, [], message.id)
}

async function scrollToBottom() {
  await nextTick()
  scrollArea.value?.scrollTo({ top: scrollArea.value.scrollHeight, behavior: 'smooth' })
}

function closeMoreOnOutside(event: PointerEvent) {
  const target = event.target
  if (!(target instanceof Element) || !target.closest('.chat-more-host')) moreOpen.value = false
}

function beginRename() {
  titleDraft.value = chat.current?.title || ''
  renaming.value = true
}

async function renameConversation() {
  if (!chat.current) return
  const title = titleDraft.value.trim()
  if (!title) return
  busy.value = true
  try {
    await chat.updateConversation(chat.current.id, { title })
    renaming.value = false
    moreOpen.value = false
    toast.show('对话名称已更新', 'success')
  } catch (error) {
    handleError(error)
  } finally {
    busy.value = false
  }
}

async function archiveConversation() {
  if (!chat.current) return
  busy.value = true
  try {
    await chat.updateConversation(chat.current.id, { archived: true })
    toast.show('对话已归档', 'success')
    await router.push('/')
  } catch (error) {
    handleError(error)
  } finally {
    busy.value = false
  }
}

async function deleteConversation() {
  if (!chat.current) return
  busy.value = true
  try {
    await chat.deleteConversation(chat.current.id)
    deleteOpen.value = false
    toast.show('对话已删除', 'success')
    await router.push('/')
  } catch (error) {
    handleError(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="chat-page">
    <header class="chat-header">
      <RouterLink to="/" class="icon-button" title="返回首页"><ChevronLeft :size="20" /></RouterLink>
      <div><strong>{{ chat.current?.title || '对话' }}</strong><span>{{ chat.streaming ? '正在生成…' : 'MLab AI' }}</span></div>
      <div class="chat-more-host">
        <button
          class="icon-button"
          title="更多操作"
          :aria-expanded="moreOpen"
          aria-haspopup="menu"
          @click="moreOpen = !moreOpen"
        >
          <MoreHorizontal :size="20" />
        </button>
        <div v-if="moreOpen" class="chat-more-menu" role="menu">
          <form v-if="renaming" class="chat-rename" @submit.prevent="renameConversation">
            <input v-model="titleDraft" maxlength="200" aria-label="对话名称" autofocus />
            <button class="icon-button icon-button--small" title="保存" :disabled="busy"><Check :size="15" /></button>
            <button class="icon-button icon-button--small" type="button" title="取消" @click="renaming = false"><X :size="15" /></button>
          </form>
          <template v-else>
            <button role="menuitem" @click="beginRename"><Pencil :size="16" />重命名</button>
            <button role="menuitem" @click="archiveConversation"><Archive :size="16" />归档对话</button>
            <button class="danger" role="menuitem" @click="moreOpen = false; deleteOpen = true">
              <Trash2 :size="16" />删除对话
            </button>
          </template>
        </div>
      </div>
    </header>
    <div ref="scrollArea" class="chat-scroll">
      <div v-if="!chat.current?.messages.length" class="empty-state"><span>AI</span><h2>开始这段对话</h2><p>{{ openingMessage || '说出你的目标，我会和你一起梳理并完成它。' }}</p></div>
      <div class="message-list">
        <MessageBubble v-for="message in chat.current?.messages" :key="message.id" :message="message" @retry="retry" @edit="edit" />
      </div>
    </div>
    <div class="chat-composer-wrap"><ChatComposer :loading="chat.streaming" @send="send" @stop="chat.stop" /><small>AI 可能会犯错，请核查重要信息。</small></div>
  </div>
  <ConfirmDialog
    :open="deleteOpen"
    title="删除这段对话？"
    :description="`“${chat.current?.title || '当前对话'}”及其中的全部消息将永久删除，无法恢复。`"
    confirm-label="确认删除"
    :busy="busy"
    @cancel="deleteOpen = false"
    @confirm="deleteConversation"
  />
</template>
