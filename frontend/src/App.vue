<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import ToastViewport from '@/components/ui/ToastViewport.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

onMounted(() => auth.restore())
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <component :is="Component" v-if="route.meta.public" />
    <AppShell v-else>
      <component :is="Component" />
    </AppShell>
  </RouterView>
  <ToastViewport />
</template>

