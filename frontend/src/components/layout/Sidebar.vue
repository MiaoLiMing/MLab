<script setup lang="ts">
import {
  Archive,
  Bot,
  ChevronDown,
  CreditCard,
  FileText,
  Grid3X3,
  Home,
  ListTodo,
  LogOut,
  MessageSquarePlus,
  MoreHorizontal,
  Pencil,
  Plus,
  Search,
  Settings,
  Sparkles,
  Trash2,
  UserRound,
  Wrench,
  X,
} from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useToastStore } from '@/stores/toast'
import type { Assistant, Conversation, UsageSummary } from '@/types/api'

type RemovalTarget =
  | { kind: 'conversation'; id: string; name: string }
  | { kind: 'assistant'; item: Assistant }
  | null

const props = defineProps<{ mobileOpen: boolean }>()
const emit = defineEmits<{ close: [] }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()
const toast = useToastStore()
const installedAssistants = ref<Assistant[]>([])
const usage = ref<UsageSummary | null>(null)
const profileOpen = ref(false)
const conversationMenuId = ref<string | null>(null)
const assistantMenuId = ref<string | null>(null)
const renamingId = ref<string | null>(null)
const renameDraft = ref('')
const removalTarget = ref<RemovalTarget>(null)
const busy = ref(false)

const initials = computed(() => auth.user?.display_name?.slice(0, 1).toUpperCase() || 'M')
const tokenUsage = computed(() => (usage.value?.input_tokens || 0) + (usage.value?.output_tokens || 0))
const removalTitle = computed(() =>
  removalTarget.value?.kind === 'conversation' ? '删除这段对话？' : '移除这个助手？',
)
const removalDescription = computed(() => {
  const target = removalTarget.value
  if (!target) return ''
  if (target.kind === 'conversation') {
    return `“${target.name}”及其中的全部消息将永久删除，无法恢复。`
  }
  return target.item.owner_id === auth.user?.id
    ? `“${target.item.name}”将被永久删除。`
    : `“${target.item.name}”会从你的工作台移除，之后仍可从助手市场重新安装。`
})
const removalLabel = computed(() => {
  const target = removalTarget.value
  return target?.kind === 'assistant' && target.item.owner_id !== auth.user?.id
    ? '确认移除'
    : '确认删除'
})

onMounted(async () => {
  await loadSidebar()
  document.addEventListener('pointerdown', handleOutsideClick)
  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('mlab:assistants-changed', loadAssistants)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleOutsideClick)
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('mlab:assistants-changed', loadAssistants)
})

watch(
  () => route.fullPath,
  () => closeMenus(),
)

async function loadSidebar() {
  await Promise.all([
    chat.loadConversations().catch(() => undefined),
    loadAssistants(),
    api<UsageSummary>('/users/me/usage')
      .then((item) => (usage.value = item))
      .catch(() => undefined),
  ])
}

async function loadAssistants() {
  installedAssistants.value = await api<Assistant[]>('/assistants/installed').catch(() => [])
}

function active(path: string) {
  return path === '/' ? route.path === '/' || route.path.startsWith('/chat') : route.path.startsWith(path)
}

function closeMenus() {
  profileOpen.value = false
  conversationMenuId.value = null
  assistantMenuId.value = null
}

function handleOutsideClick(event: PointerEvent) {
  const target = event.target
  if (!(target instanceof Element) || !target.closest('.sidebar-popover-host')) closeMenus()
}

function handleKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    goTo('/search')
    return
  }
  if (event.key === 'Escape') {
    closeMenus()
    renamingId.value = null
    removalTarget.value = null
  }
}

async function goTo(path: string) {
  closeMenus()
  emit('close')
  await router.push(path)
}

async function toggleProfile() {
  profileOpen.value = !profileOpen.value
  conversationMenuId.value = null
  assistantMenuId.value = null
  if (profileOpen.value) {
    usage.value = await api<UsageSummary>('/users/me/usage').catch(() => usage.value)
  }
}

async function signOut() {
  busy.value = true
  try {
    await auth.logout()
    await router.push('/login')
  } finally {
    busy.value = false
  }
}

async function createConversation() {
  busy.value = true
  try {
    const conversation = await chat.createConversation()
    emit('close')
    await router.push(`/chat/${conversation.id}`)
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '创建对话失败', 'error')
  } finally {
    busy.value = false
  }
}

async function startAssistant(assistantId: string) {
  busy.value = true
  try {
    const conversation = await chat.createConversation(assistantId)
    emit('close')
    await router.push(`/chat/${conversation.id}`)
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '创建对话失败', 'error')
  } finally {
    busy.value = false
  }
}

function toggleConversationMenu(id: string) {
  profileOpen.value = false
  assistantMenuId.value = null
  conversationMenuId.value = conversationMenuId.value === id ? null : id
}

function toggleAssistantMenu(id: string) {
  profileOpen.value = false
  conversationMenuId.value = null
  assistantMenuId.value = assistantMenuId.value === id ? null : id
}

function beginRename(item: Conversation) {
  renamingId.value = item.id
  renameDraft.value = item.title
  conversationMenuId.value = null
}

async function submitRename(item: Conversation) {
  const title = renameDraft.value.trim()
  if (!title || title === item.title) {
    renamingId.value = null
    return
  }
  busy.value = true
  try {
    await chat.updateConversation(item.id, { title })
    toast.show('对话名称已更新', 'success')
    renamingId.value = null
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '重命名失败', 'error')
  } finally {
    busy.value = false
  }
}

async function archiveConversation(item: Conversation) {
  conversationMenuId.value = null
  busy.value = true
  try {
    await chat.updateConversation(item.id, { archived: true })
    if (route.params.id === item.id) await router.push('/')
    toast.show('对话已归档', 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '归档失败', 'error')
  } finally {
    busy.value = false
  }
}

function requestConversationDelete(item: Conversation) {
  conversationMenuId.value = null
  removalTarget.value = { kind: 'conversation', id: item.id, name: item.title }
}

function requestAssistantRemoval(item: Assistant) {
  assistantMenuId.value = null
  removalTarget.value = { kind: 'assistant', item }
}

async function confirmRemoval() {
  const target = removalTarget.value
  if (!target) return
  busy.value = true
  try {
    if (target.kind === 'conversation') {
      await chat.deleteConversation(target.id)
      if (route.params.id === target.id) await router.push('/')
      toast.show('对话已删除', 'success')
    } else {
      const item = target.item
      await api(
        item.owner_id === auth.user?.id ? `/assistants/${item.id}` : `/assistants/${item.id}/install`,
        { method: 'DELETE' },
      )
      installedAssistants.value = installedAssistants.value.filter((assistant) => assistant.id !== item.id)
      toast.show(item.owner_id === auth.user?.id ? '助手已删除' : '助手已从工作台移除', 'success')
    }
    removalTarget.value = null
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '操作失败', 'error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div v-if="props.mobileOpen" class="sidebar-backdrop" @click="emit('close')" />
  <aside class="sidebar" :class="{ 'sidebar--open': props.mobileOpen }">
    <div class="sidebar-profile-wrap sidebar-popover-host">
      <button
        class="sidebar-profile"
        :aria-expanded="profileOpen"
        aria-haspopup="menu"
        @click="toggleProfile"
      >
        <div class="avatar">
          <img v-if="auth.user?.avatar_url" :src="auth.user.avatar_url" alt="" />
          <template v-else>{{ initials }}</template>
        </div>
        <div class="sidebar-profile__text">
          <strong>{{ auth.user?.display_name || 'MLab 用户' }}</strong>
          <span>{{ auth.user?.email }}</span>
        </div>
        <ChevronDown :size="15" :class="{ rotated: profileOpen }" />
      </button>
      <button class="icon-button sidebar-close" title="关闭导航" @click="emit('close')"><X :size="18" /></button>

      <section v-if="profileOpen" class="account-menu" role="menu">
        <header>
          <div class="avatar account-menu__avatar">
            <img v-if="auth.user?.avatar_url" :src="auth.user.avatar_url" alt="" />
            <template v-else>{{ initials }}</template>
          </div>
          <div>
            <strong>{{ auth.user?.display_name || 'MLab 用户' }}</strong>
            <span>{{ auth.user?.email }}</span>
          </div>
          <span class="plan-badge">个人版</span>
        </header>
        <div class="account-menu__usage">
          <div><strong>{{ usage?.conversations || 0 }}</strong><span>对话</span></div>
          <div><strong>{{ usage?.tasks || 0 }}</strong><span>任务</span></div>
          <div><strong>{{ tokenUsage.toLocaleString() }}</strong><span>Token</span></div>
        </div>
        <nav>
          <button role="menuitem" @click="goTo('/settings/profile')"><UserRound :size="17" />基本信息</button>
          <button role="menuitem" @click="goTo('/settings/models')"><Settings :size="17" />应用设置</button>
          <button role="menuitem" @click="goTo('/settings/subscription')"><CreditCard :size="17" />订阅与用量</button>
          <button class="account-menu__logout" role="menuitem" :disabled="busy" @click="signOut">
            <LogOut :size="17" />退出登录
          </button>
        </nav>
      </section>
    </div>

    <button class="sidebar-search" @click="goTo('/search')">
      <Search :size="17" /><span>搜索</span><kbd>⌘ K</kbd>
    </button>

    <nav class="sidebar-nav" aria-label="主导航">
      <RouterLink to="/" :class="{ active: active('/') }" @click="emit('close')"><Home :size="18" />首页</RouterLink>
      <RouterLink to="/tasks" :class="{ active: active('/tasks') }" @click="emit('close')"><ListTodo :size="18" />任务</RouterLink>
      <RouterLink to="/documents" :class="{ active: active('/documents') }" @click="emit('close')"><FileText :size="18" />文稿</RouterLink>
    </nav>

    <div class="sidebar-scroll">
      <section class="sidebar-section">
        <div class="sidebar-section__title">
          <span>最近对话</span>
          <button class="icon-button icon-button--tiny" title="新建对话" :disabled="busy" @click="createConversation">
            <Plus :size="15" />
          </button>
        </div>
        <div
          v-for="item in chat.conversations"
          :key="item.id"
          class="sidebar-row sidebar-popover-host"
          :class="{ active: route.params.id === item.id }"
        >
          <form v-if="renamingId === item.id" class="sidebar-rename" @submit.prevent="submitRename(item)">
            <input v-model="renameDraft" maxlength="200" aria-label="对话名称" autofocus />
            <button class="icon-button icon-button--tiny" title="保存" :disabled="busy"><Pencil :size="13" /></button>
            <button class="icon-button icon-button--tiny" type="button" title="取消" @click="renamingId = null"><X :size="14" /></button>
          </form>
          <template v-else>
            <RouterLink :to="`/chat/${item.id}`" class="sidebar-row__link" @click="emit('close')">
              <span class="conversation-mark">#</span><span class="truncate">{{ item.title }}</span>
            </RouterLink>
            <button class="icon-button icon-button--tiny sidebar-row__more" title="管理对话" @click.stop="toggleConversationMenu(item.id)">
              <MoreHorizontal :size="15" />
            </button>
            <div v-if="conversationMenuId === item.id" class="sidebar-context-menu" role="menu">
              <button role="menuitem" @click="beginRename(item)"><Pencil :size="15" />重命名</button>
              <button role="menuitem" @click="archiveConversation(item)"><Archive :size="15" />归档</button>
              <button class="danger" role="menuitem" @click="requestConversationDelete(item)"><Trash2 :size="15" />删除</button>
            </div>
          </template>
        </div>
        <span v-if="!chat.conversations.length" class="sidebar-empty">还没有对话，点击右侧“+”开始</span>
      </section>

      <section class="sidebar-section">
        <div class="sidebar-section__title">
          <span>助手</span>
          <button class="icon-button icon-button--tiny" title="创建助手" @click="goTo('/assistants/new')"><Plus :size="15" /></button>
        </div>
        <div v-for="item in installedAssistants" :key="item.id" class="sidebar-row sidebar-popover-host">
          <button class="sidebar-row__link sidebar-assistant" :disabled="busy" @click="startAssistant(item.id)">
            <span class="sidebar-assistant__avatar">{{ item.avatar }}</span><span class="truncate">{{ item.name }}</span>
          </button>
          <button class="icon-button icon-button--tiny sidebar-row__more" title="管理助手" @click.stop="toggleAssistantMenu(item.id)">
            <MoreHorizontal :size="15" />
          </button>
          <div v-if="assistantMenuId === item.id" class="sidebar-context-menu" role="menu">
            <button role="menuitem" @click="startAssistant(item.id)"><MessageSquarePlus :size="15" />新建对话</button>
            <button v-if="item.owner_id === auth.user?.id" role="menuitem" @click="goTo(`/assistants/${item.id}/edit`)">
              <Pencil :size="15" />编辑助手
            </button>
            <button class="danger" role="menuitem" @click="requestAssistantRemoval(item)">
              <Trash2 :size="15" />{{ item.owner_id === auth.user?.id ? '删除助手' : '从工作台移除' }}
            </button>
          </div>
        </div>
        <RouterLink to="/assistants" class="sidebar-item" @click="emit('close')"><Bot :size="17" />管理与发现助手</RouterLink>
      </section>
    </div>

    <nav class="sidebar-nav sidebar-nav--bottom" aria-label="工具导航">
      <RouterLink to="/assistants" :class="{ active: active('/assistants') }" @click="emit('close')"><Sparkles :size="18" />生成</RouterLink>
      <RouterLink to="/tools" :class="{ active: active('/tools') }" @click="emit('close')"><Wrench :size="18" />工具</RouterLink>
      <RouterLink to="/resources" :class="{ active: active('/resources') }" @click="emit('close')"><Grid3X3 :size="18" />资源</RouterLink>
      <RouterLink to="/memories" :class="{ active: active('/memories') }" @click="emit('close')"><Bot :size="18" />记忆</RouterLink>
    </nav>
  </aside>

  <ConfirmDialog
    :open="Boolean(removalTarget)"
    :title="removalTitle"
    :description="removalDescription"
    :confirm-label="removalLabel"
    :busy="busy"
    @cancel="removalTarget = null"
    @confirm="confirmRemoval"
  />
</template>
