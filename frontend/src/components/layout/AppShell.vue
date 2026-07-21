<script setup lang="ts">
import { ref } from 'vue'
import { Menu } from 'lucide-vue-next'

import Sidebar from './Sidebar.vue'

const mobileOpen = ref(false)
</script>

<template>
  <div class="app-shell">
    <Sidebar :mobile-open="mobileOpen" @close="mobileOpen = false" />
    <button class="mobile-menu-button" aria-label="打开导航" @click="mobileOpen = true"><Menu :size="20" /></button>
    <main class="app-main">
      <slot />
    </main>
  </div>
</template>
