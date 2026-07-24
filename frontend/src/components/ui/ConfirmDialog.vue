<script setup lang="ts">
import { AlertTriangle, X } from 'lucide-vue-next'
import { onBeforeUnmount, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    description: string
    confirmLabel?: string
    busy?: boolean
  }>(),
  {
    confirmLabel: '确认',
    busy: false,
  },
)

const emit = defineEmits<{
  cancel: []
  confirm: []
}>()

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.open && !props.busy) emit('cancel')
}

watch(
  () => props.open,
  (open) => {
    if (open) document.addEventListener('keydown', handleKeydown)
    else document.removeEventListener('keydown', handleKeydown)
  },
  { immediate: true },
)
onBeforeUnmount(() => document.removeEventListener('keydown', handleKeydown))
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="emit('cancel')" @keydown.esc="emit('cancel')">
      <section
        class="confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
      >
        <div class="confirm-dialog__icon"><AlertTriangle :size="20" /></div>
        <div class="confirm-dialog__content">
          <h2 id="confirm-dialog-title">{{ title }}</h2>
          <p id="confirm-dialog-description">{{ description }}</p>
        </div>
        <button class="icon-button confirm-dialog__close" title="关闭" :disabled="busy" @click="emit('cancel')">
          <X :size="18" />
        </button>
        <div class="confirm-dialog__actions">
          <button class="button button--soft" :disabled="busy" @click="emit('cancel')">取消</button>
          <button class="button button--danger" :disabled="busy" @click="emit('confirm')">
            {{ busy ? '处理中…' : confirmLabel }}
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>
