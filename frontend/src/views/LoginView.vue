<script setup lang="ts">
import { ArrowRight, Bot } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const email = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    await router.push(String(route.query.redirect || '/'))
  } catch (cause) {
    error.value = cause instanceof ApiError ? cause.message : '登录失败，请稍后重试'
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-intro">
      <div class="auth-brand"><Bot :size="26" /> MLab</div>
      <div>
        <span class="eyebrow">AI 工作空间</span>
        <h1>让想法持续生长。</h1>
        <p>对话、助手、任务和知识都在一个安静高效的工作台里。</p>
      </div>
      <small>模型凭据由你掌控，数据按账户严格隔离。</small>
    </section>
    <section class="auth-panel">
      <form class="auth-form" @submit.prevent="submit">
        <div><span class="eyebrow">欢迎回来</span><h2>登录 MLab</h2></div>
        <label>邮箱<input v-model="email" type="email" autocomplete="email" required placeholder="you@example.com" /></label>
        <label>密码<input v-model="password" type="password" autocomplete="current-password" required minlength="8" placeholder="至少 8 位" /></label>
        <p v-if="error" class="form-error">{{ error }}</p>
        <button class="button button--primary button--wide" :disabled="auth.loading">
          {{ auth.loading ? '登录中…' : '登录' }}<ArrowRight :size="17" />
        </button>
        <p class="auth-switch">还没有账户？<RouterLink to="/register">创建账户</RouterLink></p>
      </form>
    </section>
  </main>
</template>

