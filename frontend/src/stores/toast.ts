import { defineStore } from 'pinia'
import { ref } from 'vue'

interface Toast {
  id: number
  message: string
  kind: 'success' | 'error' | 'info'
}

export const useToastStore = defineStore('toast', () => {
  const items = ref<Toast[]>([])
  let nextId = 1

  function show(message: string, kind: Toast['kind'] = 'info') {
    const id = nextId++
    items.value.push({ id, message, kind })
    window.setTimeout(() => dismiss(id), 3600)
  }

  function dismiss(id: number) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  return { items, show, dismiss }
})

