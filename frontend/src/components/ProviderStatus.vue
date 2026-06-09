<template>
  <div class="provider-status" :class="statusClass" :title="tooltip">
    <span class="provider-dot"></span>
    <span class="provider-label">{{ labelText }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  provider: {
    type: String,
    default: 'groq', // 'groq' | 'gemini' | 'cache' | 'none'
  },
  streaming: {
    type: Boolean,
    default: false,
  },
})

const statusClass = computed(() => ({
  'provider-groq':   props.provider === 'groq',
  'provider-gemini': props.provider === 'gemini',
  'provider-cache':  props.provider === 'cache',
  'provider-none':   props.provider === 'none',
  'is-streaming':    props.streaming,
}))

const labelText = computed(() => {
  const labels = {
    groq:   '⚡ Groq',
    gemini: '✦ Gemini',
    cache:  '💾 Cached',
    none:   '○ Offline',
  }
  return labels[props.provider] || props.provider
})

const tooltip = computed(() => {
  const tooltips = {
    groq:   'Powered by Groq (llama-3.3-70b-versatile)',
    gemini: 'Powered by Google Gemini (gemini-1.5-flash) — fallback mode',
    cache:  'Lesson loaded from cache — no API call needed',
    none:   'AI provider unavailable',
  }
  return tooltips[props.provider] || ''
})
</script>

<style scoped>
.provider-status {
  display: inline-flex;
  align-items: center;
  gap: 0.4em;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.3em 0.8em;
  border-radius: var(--radius-full);
  letter-spacing: 0.02em;
  transition: all var(--transition-normal);
  cursor: default;
}

.provider-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* Groq — blue */
.provider-groq {
  background: var(--color-accent-dim);
  color: var(--color-accent);
  border: 1px solid var(--color-accent);
}
.provider-groq .provider-dot {
  background: var(--color-accent);
}

/* Gemini — purple */
.provider-gemini {
  background: var(--color-purple-dim);
  color: var(--color-purple);
  border: 1px solid var(--color-purple);
}
.provider-gemini .provider-dot {
  background: var(--color-purple);
}

/* Cache — green */
.provider-cache {
  background: var(--color-success-dim);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}
.provider-cache .provider-dot {
  background: var(--color-success);
}

/* None — gray */
.provider-none {
  background: transparent;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}
.provider-none .provider-dot {
  background: var(--color-text-muted);
}

/* Streaming pulse animation */
.is-streaming .provider-dot {
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.3); }
}
</style>
