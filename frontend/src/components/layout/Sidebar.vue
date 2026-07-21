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
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'

const props = defineProps<{ mobileOpen: boolean }>()
const emit = defineEmits<{ close: [] }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()

const initials = computed(() => auth.user?.display_name?.slice(0, 1).toUpperCase() || 'M')

onMounted(() => chat.loadConversations().catch(() => undefined))

function active(path: string) {
  return path === '/' ? route.path === '/' || route.path.startsWith('/chat') : route.path.startsWith(path)
}

async function signOut() {
  await auth.logout()
  await router.push('/login')
}
</script>

<template>
  <div v-if="props.mobileOpen" class="sidebar-backdrop" @click="emit('close')" />
  <aside class="sidebar" :class="{ 'sidebar--open': props.mobileOpen }">
    <div class="sidebar-profile">
      <div class="avatar">{{ initials }}</div>
      <div class="sidebar-profile__text">
        <strong>{{ auth.user?.display_name || 'MLab 用户' }}</strong>
        <span>{{ auth.user?.email }}</span>
      </div>
      <ChevronDown :size="16" />
      <button class="icon-button sidebar-close" title="关闭导航" @click="emit('close')"><X :size="18" /></button>
    </div>

    <button class="sidebar-search" @click="router.push('/search')">
      <Search :size="16" /><span>搜索</span><kbd>⌘ K</kbd>
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
      <RouterLink to="/assistants" class="sidebar-item sidebar-assistant"><Bot :size="18" />助手市场</RouterLink>
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
