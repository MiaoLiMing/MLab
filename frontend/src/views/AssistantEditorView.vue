<script setup lang="ts">
import { Bot, Save } from 'lucide-vue-next'
import { reactive } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useToastStore } from '@/stores/toast'
import type { Assistant } from '@/types/api'

const router = useRouter()
const toast = useToastStore()
const form = reactive({ name: '', description: '', avatar: 'AI', category: '通用', system_prompt: '', model_config: {} })

async function save() {
  try {
    await api<Assistant>('/assistants', { method: 'POST', body: JSON.stringify(form) })
    toast.show('助手已创建', 'success')
    await router.push('/assistants')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '创建失败', 'error')
  }
}
</script>

<template>
  <div class="page-container page-container--narrow">
    <PageHeader title="创建助手" subtitle="用清晰的角色、目标和边界定义你的专属 AI" />
    <form class="form-panel" @submit.prevent="save">
      <div class="assistant-preview"><span class="assistant-avatar assistant-avatar--large">{{ form.avatar || 'AI' }}</span><div><strong>{{ form.name || '未命名助手' }}</strong><p>{{ form.description || '助手描述会显示在这里' }}</p></div></div>
      <div class="form-grid">
        <label>助手名称<input v-model="form.name" required maxlength="100" placeholder="例如：产品策略顾问" /></label>
        <label>头像文字<input v-model="form.avatar" maxlength="2" placeholder="AI" /></label>
      </div>
      <label>分类<select v-model="form.category"><option>通用</option><option>写作</option><option>编程</option><option>分析</option><option>学习</option></select></label>
      <label>简介<textarea v-model="form.description" rows="2" maxlength="500" placeholder="一句话说明助手擅长什么" /></label>
      <label>系统提示词<textarea v-model="form.system_prompt" rows="10" maxlength="20000" placeholder="你是……你的目标是……回答时需要……" /></label>
      <div class="form-actions"><RouterLink to="/assistants" class="button button--soft">取消</RouterLink><button class="button button--primary"><Save :size="17" />保存助手</button></div>
    </form>
  </div>
</template>

