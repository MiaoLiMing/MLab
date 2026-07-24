<script setup lang="ts">
import { Check, KeyRound, Plus, Save, Trash2, X } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { Assistant, Credential, ModelConfig, ProviderInfo, UsageSummary } from '@/types/api'

type DeleteTarget =
  | { kind: 'credential'; item: Credential }
  | { kind: 'model'; item: ModelConfig }
  | null

interface CredentialTestResult {
  ok: boolean
  latency_ms: number
  models: string[]
  message: string
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()
const section = computed(() => String(route.params.section || 'profile'))
const credentials = ref<Credential[]>([])
const models = ref<ModelConfig[]>([])
const usage = ref<UsageSummary | null>(null)
const providers = ref<ProviderInfo[]>([])
const installedAssistants = ref<Assistant[]>([])
const testing = ref(false)
const loading = ref(false)
const showModelForm = ref(false)
const discoveredModels = ref<string[]>([])
const savingModelId = ref<string | null>(null)
const deleteTarget = ref<DeleteTarget>(null)
const deleting = ref(false)

const profile = reactive({
  display_name: '',
  avatar_url: '',
  default_assistant_id: null as string | null,
})
const credentialForm = reactive({
  provider: 'deepseek',
  display_name: 'DeepSeek',
  base_url: 'https://api.deepseek.com/v1',
  api_key: '',
  model: 'deepseek-chat',
})
const modelForm = reactive({
  credential_id: '',
  provider: '',
  model_id: '',
  alias: '',
  temperature: 0.7,
  max_tokens: 2048,
  is_default: false,
})

const menu = [
  ['profile', '个人资料'],
  ['models', '模型配置'],
  ['api-keys', 'API 密钥'],
  ['appearance', '外观主题'],
  ['subscription', '订阅与用量'],
] as const
const themes: { value: 'light' | 'dark' | 'system'; label: string }[] = [
  { value: 'light', label: '浅色' },
  { value: 'dark', label: '深色' },
  { value: 'system', label: '跟随系统' },
]
const modelSuggestions = computed(() => {
  const provider = providers.value.find((item) => item.id === modelForm.provider)
  return [...new Set([...(provider?.example_models || []), ...discoveredModels.value])]
})
const deleteTitle = computed(() =>
  deleteTarget.value?.kind === 'credential' ? '删除这份 API 密钥？' : '删除这个模型？',
)
const deleteDescription = computed(() => {
  const target = deleteTarget.value
  if (!target) return ''
  if (target.kind === 'credential') {
    const count = models.value.filter((item) => item.credential_id === target.item.id).length
    return count
      ? `“${target.item.display_name}”及其关联的 ${count} 个模型配置将一并删除。`
      : `“${target.item.display_name}”将被删除，保存后的密钥原文无法找回。`
  }
  return `“${target.item.alias}”将从所有模型选择器中移除。`
})

onMounted(load)
watch(() => auth.user, syncProfile, { immediate: true })
watch(
  () => modelForm.model_id,
  (value, previous) => {
    if (!modelForm.alias || modelForm.alias === previous) modelForm.alias = value
  },
)

function syncProfile() {
  profile.display_name = auth.user?.display_name || ''
  profile.avatar_url = auth.user?.avatar_url || ''
  profile.default_assistant_id = auth.user?.default_assistant_id || null
}

async function load() {
  loading.value = true
  try {
    const results = await Promise.allSettled([
      api<Credential[]>('/provider-credentials'),
      api<ModelConfig[]>('/model-configs'),
      api<UsageSummary>('/users/me/usage'),
      api<Assistant[]>('/assistants/installed'),
      api<ProviderInfo[]>('/providers'),
    ])
    const [credentialResult, modelResult, usageResult, assistantResult, providerResult] = results
    if (credentialResult.status === 'fulfilled') credentials.value = credentialResult.value
    if (modelResult.status === 'fulfilled') models.value = modelResult.value
    if (usageResult.status === 'fulfilled') usage.value = usageResult.value
    if (assistantResult.status === 'fulfilled') installedAssistants.value = assistantResult.value
    if (providerResult.status === 'fulfilled') providers.value = providerResult.value

    const failure = results.find((result) => result.status === 'rejected')
    if (failure?.status === 'rejected') {
      const message =
        failure.reason instanceof Error ? failure.reason.message : '部分设置加载失败'
      toast.show(`${message}，其余配置已正常显示`, 'error')
    }
  } finally {
    loading.value = false
  }
}

function applyProvider() {
  const provider = providers.value.find((item) => item.id === credentialForm.provider)
  if (!provider) return
  credentialForm.display_name = provider.name
  credentialForm.base_url = provider.base_url
  credentialForm.model = provider.example_models[0] || ''
}

async function saveProfile() {
  await auth.updateProfile(profile)
  toast.show('资料已保存', 'success')
}

async function setTheme(theme: 'light' | 'dark' | 'system') {
  await auth.updateProfile({ theme })
  toast.show('主题已更新', 'success')
}

async function saveCredential() {
  testing.value = true
  try {
    const testResult = await api<CredentialTestResult>('/provider-credentials/test', {
      method: 'POST',
      body: JSON.stringify(credentialForm),
    })
    discoveredModels.value = testResult.models
    const credential = await api<Credential>('/provider-credentials', {
      method: 'POST',
      body: JSON.stringify(credentialForm),
    })
    const existingModel = models.value.find(
      (item) =>
        item.provider === credentialForm.provider && item.model_id === credentialForm.model,
    )
    if (credentialForm.model && !existingModel) {
      await api('/model-configs', {
        method: 'POST',
        body: JSON.stringify({
          credential_id: credential.id,
          provider: credentialForm.provider,
          model_id: credentialForm.model,
          alias: credentialForm.model,
          parameters: { temperature: 0.7, max_tokens: 2048 },
          is_default: models.value.length === 0,
        }),
      })
    }
    credentialForm.api_key = ''
    await load()
    toast.show(`连接成功，延迟 ${testResult.latency_ms}ms`, 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '验证失败', 'error')
  } finally {
    testing.value = false
  }
}

function openAddModel() {
  if (!credentials.value.length) {
    toast.show('请先添加一份 API 密钥', 'error')
    router.push('/settings/api-keys')
    return
  }
  const credential = credentials.value[0]
  Object.assign(modelForm, {
    credential_id: credential.id,
    provider: credential.provider,
    model_id: '',
    alias: '',
    temperature: 0.7,
    max_tokens: 2048,
    is_default: models.value.length === 0,
  })
  showModelForm.value = true
}

function applyModelCredential() {
  const credential = credentials.value.find((item) => item.id === modelForm.credential_id)
  if (!credential) return
  modelForm.provider = credential.provider
  const suggestion = providers.value.find((item) => item.id === credential.provider)?.example_models[0]
  if (!modelForm.model_id && suggestion) {
    modelForm.model_id = suggestion
    modelForm.alias = suggestion
  }
}

async function createModel() {
  const credential = credentials.value.find((item) => item.id === modelForm.credential_id)
  if (!credential || !modelForm.model_id.trim() || !modelForm.alias.trim()) return
  if (
    models.value.some(
      (item) =>
        item.provider === credential.provider && item.model_id === modelForm.model_id.trim(),
    )
  ) {
    toast.show('这个模型已经配置过了', 'error')
    return
  }
  savingModelId.value = 'new'
  try {
    await api('/model-configs', {
      method: 'POST',
      body: JSON.stringify({
        credential_id: credential.id,
        provider: credential.provider,
        model_id: modelForm.model_id.trim(),
        alias: modelForm.alias.trim(),
        parameters: {
          temperature: modelForm.temperature,
          max_tokens: modelForm.max_tokens,
        },
        is_default: modelForm.is_default,
      }),
    })
    showModelForm.value = false
    await load()
    toast.show('模型已添加', 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '模型添加失败', 'error')
  } finally {
    savingModelId.value = null
  }
}

async function setDefault(item: ModelConfig) {
  if (item.is_default) return
  savingModelId.value = item.id
  try {
    await api(`/model-configs/${item.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_default: true }),
    })
    await load()
    toast.show(`${item.alias} 已设为默认模型`, 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '默认模型更新失败', 'error')
  } finally {
    savingModelId.value = null
  }
}

function setModelParameter(item: ModelConfig, key: 'temperature' | 'max_tokens', event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  item.parameters = { ...item.parameters, [key]: value }
}

async function saveModel(item: ModelConfig) {
  savingModelId.value = item.id
  try {
    await api(`/model-configs/${item.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ alias: item.alias.trim(), parameters: item.parameters }),
    })
    toast.show('模型配置已保存', 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '模型保存失败', 'error')
  } finally {
    savingModelId.value = null
  }
}

async function confirmDelete() {
  const target = deleteTarget.value
  if (!target) return
  deleting.value = true
  try {
    if (target.kind === 'credential') {
      const linkedModels = models.value.filter((item) => item.credential_id === target.item.id)
      for (const item of linkedModels) {
        await api(`/model-configs/${item.id}`, { method: 'DELETE' })
      }
      await api(`/provider-credentials/${target.item.id}`, { method: 'DELETE' })
      toast.show('API 密钥及关联模型已删除', 'success')
    } else {
      const wasDefault = target.item.is_default
      await api(`/model-configs/${target.item.id}`, { method: 'DELETE' })
      const nextDefault = models.value.find((item) => item.id !== target.item.id)
      if (wasDefault && nextDefault) {
        await api(`/model-configs/${nextDefault.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ is_default: true }),
        })
      }
      toast.show('模型已删除', 'success')
    }
    deleteTarget.value = null
    await load()
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '删除失败', 'error')
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <PageHeader title="设置" subtitle="管理账户、模型与工作方式" />
    <div class="settings-layout">
      <nav class="settings-nav" aria-label="设置分类">
        <button
          v-for="item in menu"
          :key="item[0]"
          :class="{ active: section === item[0] }"
          @click="router.push(`/settings/${item[0]}`)"
        >
          {{ item[1] }}
        </button>
      </nav>

      <section class="settings-content" :aria-busy="loading">
        <template v-if="section === 'profile'">
          <div class="profile-summary">
            <div class="avatar avatar--large">
              <img v-if="auth.user?.avatar_url" :src="auth.user.avatar_url" alt="" />
              <template v-else>{{ auth.user?.display_name.slice(0, 1) }}</template>
            </div>
            <div><h2>{{ auth.user?.display_name }}</h2><p>{{ auth.user?.email }}</p></div>
          </div>
          <form class="settings-form" @submit.prevent="saveProfile">
            <label>显示名称<input v-model="profile.display_name" required /></label>
            <label>头像 URL<input v-model="profile.avatar_url" type="url" placeholder="https://…" /></label>
            <label>
              默认助手
              <select v-model="profile.default_assistant_id">
                <option :value="null">不使用默认助手</option>
                <option v-for="item in installedAssistants" :key="item.id" :value="item.id">{{ item.name }}</option>
              </select>
            </label>
            <div class="form-actions"><button class="button button--primary">保存资料</button></div>
          </form>
        </template>

        <template v-else-if="section === 'api-keys'">
          <div class="settings-section-head">
            <div><h2>API 密钥</h2><p>密钥会加密保存，保存后不再显示原文。</p></div>
            <KeyRound :size="24" />
          </div>
          <form class="settings-form settings-form--boxed" @submit.prevent="saveCredential">
            <div class="form-grid">
              <label>
                供应商
                <select v-model="credentialForm.provider" required @change="applyProvider">
                  <option v-for="item in providers" :key="item.id" :value="item.id">{{ item.name }}</option>
                </select>
              </label>
              <label>显示名称<input v-model="credentialForm.display_name" required /></label>
            </div>
            <label>API Base URL<input v-model="credentialForm.base_url" type="url" required /></label>
            <label>API Key<input v-model="credentialForm.api_key" type="password" required autocomplete="off" placeholder="sk-…" /></label>
            <label>
              初始模型
              <input v-model="credentialForm.model" list="credential-model-options" required placeholder="例如 deepseek-chat" />
              <small>保存后可在“模型配置”中继续添加同一供应商的其他模型。</small>
            </label>
            <datalist id="credential-model-options">
              <option v-for="item in discoveredModels" :key="item" :value="item" />
            </datalist>
            <button class="button button--primary" :disabled="testing">
              <Plus :size="17" />{{ testing ? '验证中…' : '验证并保存' }}
            </button>
          </form>
          <div class="credential-list">
            <article v-for="item in credentials" :key="item.id">
              <div><strong>{{ item.display_name }}</strong><span>{{ item.base_url }} · {{ item.key_hint }}</span></div>
              <button class="icon-button danger-text" title="删除密钥" @click="deleteTarget = { kind: 'credential', item }">
                <Trash2 :size="16" />
              </button>
            </article>
            <div v-if="!credentials.length" class="mini-empty">还没有保存 API 密钥。</div>
          </div>
        </template>

        <template v-else-if="section === 'models'">
          <div class="settings-section-head">
            <div><h2>模型配置</h2><p>一份供应商凭据可以配置多个模型，并在对话中随时切换。</p></div>
            <button class="button button--primary" @click="openAddModel"><Plus :size="17" />添加模型</button>
          </div>

          <form v-if="showModelForm" class="model-create settings-form" @submit.prevent="createModel">
            <header><div><strong>添加模型</strong><span>模型 ID 必须与供应商控制台保持一致。</span></div><button class="icon-button" type="button" title="关闭" @click="showModelForm = false"><X :size="18" /></button></header>
            <div class="form-grid">
              <label>
                使用凭据
                <select v-model="modelForm.credential_id" required @change="applyModelCredential">
                  <option v-for="item in credentials" :key="item.id" :value="item.id">{{ item.display_name }} · {{ item.provider }}</option>
                </select>
              </label>
              <label>
                模型 ID
                <input v-model="modelForm.model_id" list="model-suggestions" required placeholder="例如 deepseek-reasoner" />
                <datalist id="model-suggestions"><option v-for="item in modelSuggestions" :key="item" :value="item" /></datalist>
              </label>
            </div>
            <label>显示名称<input v-model="modelForm.alias" required placeholder="例如 DeepSeek 推理模型" /></label>
            <div class="form-grid">
              <label>温度<input v-model.number="modelForm.temperature" type="number" min="0" max="2" step="0.1" /></label>
              <label>最大 Token<input v-model.number="modelForm.max_tokens" type="number" min="1" max="100000" /></label>
            </div>
            <label class="checkbox-row"><input v-model="modelForm.is_default" type="checkbox" />设为默认模型</label>
            <div class="form-actions">
              <button type="button" class="button button--soft" @click="showModelForm = false">取消</button>
              <button class="button button--primary" :disabled="savingModelId === 'new'"><Save :size="16" />{{ savingModelId === 'new' ? '保存中…' : '保存模型' }}</button>
            </div>
          </form>

          <div class="model-list">
            <article v-for="item in models" :key="item.id" class="model-card" :class="{ active: item.is_default }">
              <header class="model-card__head">
                <button class="model-default" :disabled="savingModelId === item.id" @click="setDefault(item)">
                  <span class="model-status"><Check v-if="item.is_default" :size="15" /></span>
                  <div><strong>{{ item.is_default ? '默认模型' : '设为默认' }}</strong><span>{{ item.provider }} / {{ item.model_id }}</span></div>
                </button>
                <button class="icon-button danger-text" title="删除模型" @click="deleteTarget = { kind: 'model', item }"><Trash2 :size="16" /></button>
              </header>
              <div class="model-parameters">
                <label>显示名称<input v-model="item.alias" maxlength="120" /></label>
                <label>温度<input type="number" min="0" max="2" step="0.1" :value="Number(item.parameters.temperature ?? 0.7)" @change="setModelParameter(item, 'temperature', $event)" /></label>
                <label>最大 Token<input type="number" min="1" max="100000" :value="Number(item.parameters.max_tokens ?? 2048)" @change="setModelParameter(item, 'max_tokens', $event)" /></label>
                <button class="button button--soft" :disabled="savingModelId === item.id" @click="saveModel(item)">
                  {{ savingModelId === item.id ? '保存中…' : '保存' }}
                </button>
              </div>
            </article>
            <div v-if="!models.length" class="empty-state empty-state--compact">
              <KeyRound :size="26" /><h2>还没有模型</h2><p>添加 API 密钥后，可为同一供应商配置多个模型。</p>
            </div>
          </div>
        </template>

        <template v-else-if="section === 'appearance'">
          <div class="settings-section-head"><div><h2>外观主题</h2><p>选择更适合当前环境的显示方式。</p></div></div>
          <div class="theme-options">
            <button v-for="item in themes" :key="item.value" :class="{ active: auth.user?.theme === item.value }" @click="setTheme(item.value)">
              <span :class="`theme-preview theme-preview--${item.value}`" />{{ item.label }}
              <Check v-if="auth.user?.theme === item.value" :size="17" />
            </button>
          </div>
        </template>

        <template v-else>
          <div class="settings-section-head"><div><h2>订阅与用量</h2><p>查看当前计划和本账户的累计使用情况。</p></div></div>
          <div class="plan-card">
            <div class="plan-card__head"><div><span class="plan-badge">当前计划</span><h2>个人版</h2></div><span>使用自己的模型凭据</span></div>
            <div class="usage-grid">
              <div><strong>{{ usage?.conversations || 0 }}</strong><span>对话</span></div>
              <div><strong>{{ usage?.tasks || 0 }}</strong><span>任务</span></div>
              <div><strong>{{ usage?.documents || 0 }}</strong><span>文稿</span></div>
              <div><strong>{{ ((usage?.input_tokens || 0) + (usage?.output_tokens || 0)).toLocaleString() }}</strong><span>Token</span></div>
            </div>
            <button class="button button--soft" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新用量' }}</button>
          </div>
        </template>
      </section>
    </div>
  </div>

  <ConfirmDialog
    :open="Boolean(deleteTarget)"
    :title="deleteTitle"
    :description="deleteDescription"
    confirm-label="确认删除"
    :busy="deleting"
    @cancel="deleteTarget = null"
    @confirm="confirmDelete"
  />
</template>
