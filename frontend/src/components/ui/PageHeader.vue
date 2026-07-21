<script setup lang="ts">
defineProps<{ title: string; subtitle: string }>()
</script>

<template>
  <header class="page-header">
    <div>
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
    </div>
    <slot />
  </header>
</template>

