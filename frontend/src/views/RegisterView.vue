<script setup lang="ts">
import { ArrowRight, Bot } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const displayName = ref('')
const email = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.register(email.value, password.value, displayName.value)
    await router.push('/')
  } catch (cause) {
    error.value = cause instanceof ApiError ? cause.message : '注册失败，请稍后重试'
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-intro">
      <div class="auth-brand"><Bot :size="26" /> MLab</div>
      <div><span class="eyebrow">从这里开始</span><h1>建立你的 AI 工作台。</h1><p>一个账户管理全部对话、助手、任务、文稿与长期记忆。</p></div>
      <small>你的 API Key 仅加密保存在服务端。</small>
    </section>
    <section class="auth-panel">
      <form class="auth-form" @submit.prevent="submit">
        <div><span class="eyebrow">创建账户</span><h2>加入 MLab</h2></div>
        <label>显示名称<input v-model="displayName" required maxlength="80" placeholder="你的名字" /></label>
        <label>邮箱<input v-model="email" type="email" autocomplete="email" required placeholder="you@example.com" /></label>
        <label>密码<input v-model="password" type="password" autocomplete="new-password" required minlength="8" placeholder="至少 8 位" /></label>
        <p v-if="error" class="form-error">{{ error }}</p>
        <button class="button button--primary button--wide" :disabled="auth.loading">{{ auth.loading ? '创建中…' : '创建账户' }}<ArrowRight :size="17" /></button>
        <p class="auth-switch">已有账户？<RouterLink to="/login">直接登录</RouterLink></p>
      </form>
    </section>
  </main>
</template>

