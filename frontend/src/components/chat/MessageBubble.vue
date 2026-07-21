<script setup lang="ts">
import { Check, Copy, Paperclip, Pencil, RotateCcw, Save, X } from 'lucide-vue-next'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import css from 'highlight.js/lib/languages/css'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import python from 'highlight.js/lib/languages/python'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import MarkdownIt from 'markdown-it'
import { computed, ref } from 'vue'

import type { ChatMessage } from '@/types/api'

const props = defineProps<{ message: ChatMessage }>()
const emit = defineEmits<{
  retry: [message: ChatMessage]
  edit: [message: ChatMessage, content: string]
}>()
const copied = ref(false)
const editing = ref(false)
const draft = ref(props.message.content)
for (const [name, language] of Object.entries({
  bash,
  css,
  javascript,
  js: javascript,
  json,
  python,
  py: python,
  typescript,
  ts: typescript,
  html: xml,
  xml,
})) {
  hljs.registerLanguage(name, language)
}
const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight(source, language) {
    if (language && hljs.getLanguage(language)) {
      return `<pre class="hljs"><code>${hljs.highlight(source, { language }).value}</code></pre>`
    }
    return `<pre class="hljs"><code>${hljs.highlightAuto(source).value}</code></pre>`
  },
})
const rendered = computed(() => DOMPurify.sanitize(md.render(props.message.content)))

async function copy() {
  await navigator.clipboard.writeText(props.message.content)
  copied.value = true
  window.setTimeout(() => (copied.value = false), 1500)
}

function startEdit() {
  draft.value = props.message.content
  editing.value = true
}

function submitEdit() {
  const content = draft.value.trim()
  if (!content || content === props.message.content) {
    editing.value = false
    return
  }
  emit('edit', props.message, content)
  editing.value = false
}
</script>

<template>
  <article class="message" :class="`message--${message.role}`">
    <div class="message__avatar">{{ message.role === 'user' ? '我' : 'M' }}</div>
    <div class="message__body">
      <div class="message__name">{{ message.role === 'user' ? '你' : 'MLab AI' }}</div>
      <div v-if="message.role === 'assistant'" class="markdown" v-html="rendered" />
      <div v-else-if="editing" class="message__edit">
        <textarea v-model="draft" rows="4" maxlength="100000" @keydown.ctrl.enter="submitEdit" />
        <div class="message__edit-actions">
          <button class="icon-button icon-button--small" title="取消编辑" @click="editing = false"><X :size="15" /></button>
          <button class="icon-button icon-button--small" title="保存并重新生成" @click="submitEdit"><Save :size="15" /></button>
        </div>
      </div>
      <div v-else class="message__plain">{{ message.content }}</div>
      <div v-if="message.attachments?.length" class="message__attachments">
        <span v-for="attachment in message.attachments" :key="attachment.id">
          <Paperclip :size="13" />{{ String(attachment.attachment_metadata.name || '附件') }}
        </span>
      </div>
      <div v-if="message.tool_status" class="message__tool-status">
        <span class="typing"><i /><i /><i /></span>{{ message.tool_status }}
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
        <button
          v-if="message.role === 'user'"
          class="icon-button icon-button--small"
          title="编辑后重新生成"
          @click="startEdit"
        ><Pencil :size="15" /></button>
      </div>
    </div>
  </article>
</template>
