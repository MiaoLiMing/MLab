<script setup lang="ts">
import { Check, KeyRound, Plus, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { Assistant, Credential, ModelConfig, ProviderInfo, UsageSummary } from '@/types/api'

const route = useRoute(); const router = useRouter(); const auth = useAuthStore(); const toast = useToastStore()
const section = computed(() => String(route.params.section || 'profile'))
const credentials = ref<Credential[]>([]); const models = ref<ModelConfig[]>([]); const testing = ref(false)
const usage = ref<UsageSummary | null>(null)
const providers = ref<ProviderInfo[]>([])
const installedAssistants = ref<Assistant[]>([])
const profile = reactive({ display_name: '', avatar_url: '', default_assistant_id: null as string | null })
const credentialForm = reactive({ provider: 'deepseek', display_name: 'DeepSeek', base_url: 'https://api.deepseek.com/v1', api_key: '', model: 'deepseek-chat' })
const menu = [['profile','个人资料'],['models','模型偏好'],['appearance','外观主题'],['api-keys','API 密钥'],['subscription','订阅计划']]
const themes: { value: 'light' | 'dark' | 'system'; label: string }[] = [
  { value: 'light', label: '浅色' },
  { value: 'dark', label: '深色' },
  { value: 'system', label: '跟随系统' },
]

onMounted(load); watch(() => auth.user, syncProfile, { immediate: true })
function syncProfile() { profile.display_name = auth.user?.display_name || ''; profile.avatar_url = auth.user?.avatar_url || ''; profile.default_assistant_id = auth.user?.default_assistant_id || null }
async function load() {
  ;[credentials.value, models.value, usage.value, installedAssistants.value, providers.value] = await Promise.all([
    api<Credential[]>('/provider-credentials'),
    api<ModelConfig[]>('/model-configs'),
    api<UsageSummary>('/users/me/usage'),
    api<Assistant[]>('/assistants/installed'),
    api<ProviderInfo[]>('/providers'),
  ])
}
function applyProvider() {
  const provider = providers.value.find((item) => item.id === credentialForm.provider)
  if (!provider) return
  credentialForm.display_name = provider.name
  credentialForm.base_url = provider.base_url
  credentialForm.model = provider.example_models[0] || ''
}
async function saveProfile() { await auth.updateProfile(profile); toast.show('资料已保存', 'success') }
async function setTheme(theme: 'light'|'dark'|'system') { await auth.updateProfile({ theme }); toast.show('主题已更新', 'success') }
async function saveCredential() {
  testing.value = true
  try {
    await api('/provider-credentials/test', { method: 'POST', body: JSON.stringify(credentialForm) })
    const credential = await api<Credential>('/provider-credentials', { method: 'POST', body: JSON.stringify(credentialForm) })
    const existingModel = models.value.find((item) => item.provider === credentialForm.provider && item.model_id === credentialForm.model)
    if (!existingModel) await api('/model-configs', { method: 'POST', body: JSON.stringify({ credential_id: credential.id, provider: credentialForm.provider, model_id: credentialForm.model, alias: credentialForm.model, parameters: { temperature: 0.7 }, is_default: models.value.length === 0 }) })
    credentialForm.api_key = ''; await load(); toast.show('API Key 已验证并保存', 'success')
  } catch (error) { toast.show(error instanceof Error ? error.message : '验证失败', 'error') } finally { testing.value = false }
}
async function removeCredential(item: Credential) { await api(`/provider-credentials/${item.id}`, { method: 'DELETE' }); await load(); toast.show('凭据已删除', 'success') }
async function setDefault(item: ModelConfig) { await api(`/model-configs/${item.id}`, { method: 'PATCH', body: JSON.stringify({ is_default: true }) }); await load() }
function setModelParameter(item: ModelConfig, key: 'temperature' | 'max_tokens', event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  item.parameters = { ...item.parameters, [key]: value }
}
async function saveModelParameters(item: ModelConfig) {
  await api(`/model-configs/${item.id}`, {
    method: 'PATCH',
    body: JSON.stringify({ parameters: item.parameters }),
  })
  toast.show('模型参数已保存', 'success')
}
</script>

<template>
  <div class="page-container">
    <PageHeader title="设置" subtitle="管理你的账户、模型与偏好" />
    <div class="settings-layout">
      <nav class="settings-nav"><button v-for="item in menu" :key="item[0]" :class="{ active: section === item[0] }" @click="router.push(`/settings/${item[0]}`)">{{ item[1] }}</button></nav>
      <section class="settings-content">
        <template v-if="section === 'profile'"><div class="profile-summary"><div class="avatar avatar--large">{{ auth.user?.display_name.slice(0,1) }}</div><div><h2>{{ auth.user?.display_name }}</h2><p>{{ auth.user?.email }}</p></div></div><form class="settings-form" @submit.prevent="saveProfile"><label>显示名称<input v-model="profile.display_name" required /></label><label>头像 URL<input v-model="profile.avatar_url" type="url" placeholder="https://…" /></label><label>默认助手<select v-model="profile.default_assistant_id"><option :value="null">不使用默认助手</option><option v-for="item in installedAssistants" :key="item.id" :value="item.id">{{ item.name }}</option></select></label><div class="form-actions"><button class="button button--primary">保存资料</button></div></form></template>
        <template v-else-if="section === 'api-keys'"><div class="settings-section-head"><div><h2>API 密钥</h2><p>密钥会加密保存，保存后不再显示原文。</p></div><KeyRound :size="24" /></div><form class="settings-form" @submit.prevent="saveCredential"><div class="form-grid"><label>供应商<input v-model="credentialForm.provider" list="provider-options" required @change="applyProvider" /><datalist id="provider-options"><option v-for="item in providers" :key="item.id" :value="item.id">{{ item.name }}</option></datalist></label><label>显示名称<input v-model="credentialForm.display_name" required /></label></div><label>API Base URL<input v-model="credentialForm.base_url" type="url" required /></label><label>API Key<input v-model="credentialForm.api_key" type="password" required autocomplete="off" placeholder="sk-…" /></label><label>默认模型<input v-model="credentialForm.model" required placeholder="deepseek-chat" /></label><button class="button button--primary" :disabled="testing"><Plus :size="17" />{{ testing ? '验证中…' : '验证并保存' }}</button></form><div class="credential-list"><article v-for="item in credentials" :key="item.id"><div><strong>{{ item.display_name }}</strong><span>{{ item.base_url }} · {{ item.key_hint }}</span></div><button class="icon-button" title="删除密钥" @click="removeCredential(item)"><Trash2 :size="16" /></button></article></div></template>
        <template v-else-if="section === 'models'"><div class="settings-section-head"><div><h2>模型偏好</h2><p>选择默认模型并调整生成参数。</p></div></div><div class="model-list"><article v-for="item in models" :key="item.id" class="model-card" :class="{ active: item.is_default }"><button class="model-default" @click="setDefault(item)"><div><strong>{{ item.alias }}</strong><span>{{ item.provider }} / {{ item.model_id }}</span></div><Check v-if="item.is_default" :size="18" /></button><div class="model-parameters"><label>温度<input type="number" min="0" max="2" step="0.1" :value="Number(item.parameters.temperature ?? 0.7)" @change="setModelParameter(item, 'temperature', $event)" /></label><label>最大 Token<input type="number" min="1" max="100000" :value="Number(item.parameters.max_tokens ?? 2048)" @change="setModelParameter(item, 'max_tokens', $event)" /></label><button class="button button--soft" @click="saveModelParameters(item)">保存参数</button></div></article><div v-if="!models.length" class="mini-empty">请先在 API 密钥中添加模型。</div></div></template>
        <template v-else-if="section === 'appearance'"><div class="settings-section-head"><div><h2>外观主题</h2><p>选择更适合当前环境的显示方式。</p></div></div><div class="theme-options"><button v-for="item in themes" :key="item.value" :class="{ active: auth.user?.theme === item.value }" @click="setTheme(item.value)"><span :class="`theme-preview theme-preview--${item.value}`" />{{ item.label }}<Check v-if="auth.user?.theme === item.value" :size="17" /></button></div></template>
        <template v-else><div class="plan-card"><span class="tag tag--inverse">当前计划</span><h2>个人版</h2><p>使用自己的模型凭据，不限制平台侧对话次数。</p><div class="usage-grid"><div><strong>{{ usage?.conversations || 0 }}</strong><span>对话</span></div><div><strong>{{ usage?.tasks || 0 }}</strong><span>任务</span></div><div><strong>{{ usage?.documents || 0 }}</strong><span>文稿</span></div><div><strong>{{ ((usage?.input_tokens || 0) + (usage?.output_tokens || 0)).toLocaleString() }}</strong><span>Token</span></div></div><button class="button button--inverse" @click="load">刷新用量</button></div></template>
      </section>
    </div>
  </div>
</template>
