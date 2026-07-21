<script setup lang="ts">
import { Check, KeyRound, Plus, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { Credential, ModelConfig } from '@/types/api'

const route = useRoute(); const router = useRouter(); const auth = useAuthStore(); const toast = useToastStore()
const section = computed(() => String(route.params.section || 'profile'))
const credentials = ref<Credential[]>([]); const models = ref<ModelConfig[]>([]); const testing = ref(false)
const profile = reactive({ display_name: '', avatar_url: '' })
const credentialForm = reactive({ provider: 'deepseek', display_name: 'DeepSeek', base_url: 'https://api.deepseek.com/v1', api_key: '', model: 'deepseek-chat' })
const menu = [['profile','个人资料'],['models','模型偏好'],['appearance','外观主题'],['api-keys','API 密钥'],['subscription','订阅计划']]

onMounted(load); watch(() => auth.user, syncProfile, { immediate: true })
function syncProfile() { profile.display_name = auth.user?.display_name || ''; profile.avatar_url = auth.user?.avatar_url || '' }
async function load() { ;[credentials.value, models.value] = await Promise.all([api<Credential[]>('/provider-credentials'), api<ModelConfig[]>('/model-configs')]) }
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
</script>

<template>
  <div class="page-container">
    <PageHeader title="设置" subtitle="管理你的账户、模型与偏好" />
    <div class="settings-layout">
      <nav class="settings-nav"><button v-for="item in menu" :key="item[0]" :class="{ active: section === item[0] }" @click="router.push(`/settings/${item[0]}`)">{{ item[1] }}</button></nav>
      <section class="settings-content">
        <template v-if="section === 'profile'"><div class="profile-summary"><div class="avatar avatar--large">{{ auth.user?.display_name.slice(0,1) }}</div><div><h2>{{ auth.user?.display_name }}</h2><p>{{ auth.user?.email }}</p></div></div><form class="settings-form" @submit.prevent="saveProfile"><label>显示名称<input v-model="profile.display_name" required /></label><label>头像 URL<input v-model="profile.avatar_url" type="url" placeholder="https://…" /></label><div class="form-actions"><button class="button button--primary">保存资料</button></div></form></template>
        <template v-else-if="section === 'api-keys'"><div class="settings-section-head"><div><h2>API 密钥</h2><p>密钥会加密保存，保存后不再显示原文。</p></div><KeyRound :size="24" /></div><form class="settings-form" @submit.prevent="saveCredential"><div class="form-grid"><label>供应商<input v-model="credentialForm.provider" required /></label><label>显示名称<input v-model="credentialForm.display_name" required /></label></div><label>API Base URL<input v-model="credentialForm.base_url" type="url" required /></label><label>API Key<input v-model="credentialForm.api_key" type="password" required autocomplete="off" placeholder="sk-…" /></label><label>默认模型<input v-model="credentialForm.model" required placeholder="deepseek-chat" /></label><button class="button button--primary" :disabled="testing"><Plus :size="17" />{{ testing ? '验证中…' : '验证并保存' }}</button></form><div class="credential-list"><article v-for="item in credentials" :key="item.id"><div><strong>{{ item.display_name }}</strong><span>{{ item.base_url }} · {{ item.key_hint }}</span></div><button class="icon-button" title="删除密钥" @click="removeCredential(item)"><Trash2 :size="16" /></button></article></div></template>
        <template v-else-if="section === 'models'"><div class="settings-section-head"><div><h2>模型偏好</h2><p>选择新对话默认使用的模型。</p></div></div><div class="model-list"><button v-for="item in models" :key="item.id" :class="{ active: item.is_default }" @click="setDefault(item)"><div><strong>{{ item.alias }}</strong><span>{{ item.provider }} / {{ item.model_id }}</span></div><Check v-if="item.is_default" :size="18" /></button><div v-if="!models.length" class="mini-empty">请先在 API 密钥中添加模型。</div></div></template>
        <template v-else-if="section === 'appearance'"><div class="settings-section-head"><div><h2>外观主题</h2><p>选择更适合当前环境的显示方式。</p></div></div><div class="theme-options"><button v-for="item in [['light','浅色'],['dark','深色'],['system','跟随系统']]" :key="item[0]" :class="{ active: auth.user?.theme === item[0] }" @click="setTheme(item[0] as 'light'|'dark'|'system')"><span :class="`theme-preview theme-preview--${item[0]}`" />{{ item[1] }}<Check v-if="auth.user?.theme === item[0]" :size="17" /></button></div></template>
        <template v-else><div class="plan-card"><span class="tag tag--inverse">当前计划</span><h2>个人版</h2><p>使用自己的模型凭据，不限制平台侧对话次数。</p><button class="button button--inverse">管理订阅</button></div></template>
      </section>
    </div>
  </div>
</template>

