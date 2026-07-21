<script setup lang="ts">
import {
  Bot,
  ChevronDown,
  FileText,
  Grid3X3,
  Home,
  ListTodo,
  LogOut,
  Menu,
  MessageSquarePlus,
  Search,
  Settings,
  Sparkles,
  Wrench,
  X,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import type { Assistant } from '@/types/api'

const props = defineProps<{ mobileOpen: boolean }>()
const emit = defineEmits<{ close: [] }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()
const installedAssistants = ref<Assistant[]>([])

const initials = computed(() => auth.user?.display_name?.slice(0, 1).toUpperCase() || 'M')

onMounted(async () => {
  await Promise.all([
    chat.loadConversations().catch(() => undefined),
    api<Assistant[]>('/assistants/installed')
      .then((items) => (installedAssistants.value = items))
      .catch(() => undefined),
  ])
})

function active(path: string) {
  return path === '/' ? route.path === '/' || route.path.startsWith('/chat') : route.path.startsWith(path)
}

async function signOut() {
  await auth.logout()
  await router.push('/login')
}

async function startAssistant(assistantId: string) {
  const conversation = await chat.createConversation(assistantId)
  emit('close')
  await router.push(`/chat/${conversation.id}`)
}
</script>

<template>
  <div v-if="props.mobileOpen" class="sidebar-backdrop" @click="emit('close')" />
  <aside class="sidebar" :class="{ 'sidebar--open': props.mobileOpen }">
    <div class="sidebar-profile">
      <div class="avatar"><img v-if="auth.user?.avatar_url" :src="auth.user.avatar_url" alt="" /> <template v-else>{{ initials }}</template></div>
      <div class="sidebar-profile__text">
        <strong>{{ auth.user?.display_name || 'MLab 用户' }}</strong>
        <span>{{ auth.user?.email }}</span>
      </div>
      <ChevronDown :size="16" />
      <button class="icon-button sidebar-close" title="关闭导航" @click="emit('close')"><X :size="18" /></button>
    </div>

    <button class="sidebar-search" @click="router.push('/search')">
      <Search :size="16" /><span>搜索</span>
    </button>

    <nav class="sidebar-nav" aria-label="主导航">
      <RouterLink to="/" :class="{ active: active('/') }"><Home :size="18" />首页</RouterLink>
      <RouterLink to="/tasks" :class="{ active: active('/tasks') }"><ListTodo :size="18" />任务</RouterLink>
      <RouterLink to="/documents" :class="{ active: active('/documents') }"><FileText :size="18" />文稿</RouterLink>
    </nav>

    <div class="sidebar-section">
      <div class="sidebar-section__title"><span>最近</span><ChevronDown :size="14" /></div>
      <RouterLink
        v-for="item in chat.conversations.slice(0, 4)"
        :key="item.id"
        :to="`/chat/${item.id}`"
        class="sidebar-item"
      >
        <span>#</span><span class="truncate">{{ item.title }}</span>
      </RouterLink>
      <span v-if="!chat.conversations.length" class="sidebar-empty">暂无对话</span>
    </div>

    <div class="sidebar-section">
      <div class="sidebar-section__title"><span>助手</span><Menu :size="14" /></div>
      <button v-for="item in installedAssistants.slice(0, 4)" :key="item.id" class="sidebar-item sidebar-assistant" @click="startAssistant(item.id)"><span class="sidebar-assistant__avatar">{{ item.avatar }}</span><span class="truncate">{{ item.name }}</span></button>
      <RouterLink to="/assistants" class="sidebar-item"><Bot :size="18" />助手市场</RouterLink>
      <RouterLink to="/assistants/new" class="sidebar-item"><MessageSquarePlus :size="17" />创建助手</RouterLink>
    </div>

    <nav class="sidebar-nav sidebar-nav--bottom" aria-label="工具导航">
      <RouterLink to="/assistants" :class="{ active: active('/assistants') }"><Sparkles :size="18" />生成</RouterLink>
      <RouterLink to="/tools" :class="{ active: active('/tools') }"><Wrench :size="18" />工具</RouterLink>
      <RouterLink to="/resources" :class="{ active: active('/resources') }"><Grid3X3 :size="18" />资源</RouterLink>
      <RouterLink to="/memories" :class="{ active: active('/memories') }"><Bot :size="18" />记忆</RouterLink>
      <RouterLink to="/settings/profile" :class="{ active: active('/settings') }"><Settings :size="18" />设置</RouterLink>
      <button class="sidebar-logout" @click="signOut"><LogOut :size="18" />退出登录</button>
    </nav>
  </aside>
</template>
