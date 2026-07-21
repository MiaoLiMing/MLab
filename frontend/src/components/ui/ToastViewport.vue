<script setup lang="ts">
import { CircleCheck, CircleX, Info, X } from 'lucide-vue-next'

import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
</script>

<template>
  <div class="toast-viewport" aria-live="polite">
    <div v-for="item in toast.items" :key="item.id" class="toast" :class="`toast--${item.kind}`">
      <CircleCheck v-if="item.kind === 'success'" :size="18" />
      <CircleX v-else-if="item.kind === 'error'" :size="18" />
      <Info v-else :size="18" />
      <span>{{ item.message }}</span>
      <button class="icon-button icon-button--small" title="关闭" @click="toast.dismiss(item.id)">
        <X :size="15" />
      </button>
    </div>
  </div>
</template>

