<script setup lang="ts">
import { Check, Copy, Paperclip, RotateCcw } from 'lucide-vue-next'
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { computed, ref } from 'vue'

import type { ChatMessage } from '@/types/api'

const props = defineProps<{ message: ChatMessage }>()
const emit = defineEmits<{ retry: [message: ChatMessage] }>()
const copied = ref(false)
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })
const rendered = computed(() => DOMPurify.sanitize(md.render(props.message.content)))

async function copy() {
  await navigator.clipboard.writeText(props.message.content)
  copied.value = true
  window.setTimeout(() => (copied.value = false), 1500)
}
</script>

<template>
  <article class="message" :class="`message--${message.role}`">
    <div class="message__avatar">{{ message.role === 'user' ? '我' : 'M' }}</div>
    <div class="message__body">
      <div class="message__name">{{ message.role === 'user' ? '你' : 'MLab AI' }}</div>
      <div v-if="message.role === 'assistant'" class="markdown" v-html="rendered" />
      <div v-else class="message__plain">{{ message.content }}</div>
      <div v-if="message.attachments?.length" class="message__attachments">
        <span v-for="attachment in message.attachments" :key="attachment.id">
          <Paperclip :size="13" />附件
        </span>
      </div>
      <span v-if="message.status === 'streaming' && !message.content" class="typing"><i /><i /><i /></span>
      <div v-if="message.status === 'failed'" class="message__error">生成失败，请检查模型配置后重试。</div>
      <div v-if="message.content" class="message__tools">
        <button class="icon-button icon-button--small" title="复制" @click="copy">
          <Check v-if="copied" :size="15" /><Copy v-else :size="15" />
        </button>
        <button
          v-if="message.role === 'assistant'"
          class="icon-button icon-button--small"
          title="重新生成"
          @click="emit('retry', message)"
        ><RotateCcw :size="15" /></button>
      </div>
    </div>
  </article>
</template>
