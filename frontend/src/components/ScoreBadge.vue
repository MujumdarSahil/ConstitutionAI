<template>
  <div class="score-badge" :class="badgeClass" :title="`Score: ${score}/100`">
    <span class="score-value">{{ score }}</span>
    <span class="score-label">{{ label }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: {
    type: Number,
    default: 0,
  },
  showLabel: {
    type: Boolean,
    default: true,
  },
  size: {
    type: String,
    default: 'md', // 'sm' | 'md' | 'lg'
  },
})

const badgeClass = computed(() => ({
  'badge-high':   props.score >= 80,
  'badge-medium': props.score >= 60 && props.score < 80,
  'badge-low':    props.score < 60,
  [`size-${props.size}`]: true,
}))

const label = computed(() => {
  if (!props.showLabel) return ''
  if (props.score >= 80) return 'Excellent'
  if (props.score >= 60) return 'Good'
  if (props.score > 0)   return 'Needs Review'
  return 'Not Tested'
})
</script>

<style scoped>
.score-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3em;
  border-radius: var(--radius-full);
  font-weight: 700;
  line-height: 1;
}

.score-value {
  font-size: 1em;
}

.score-label {
  font-size: 0.7em;
  opacity: 0.85;
  font-weight: 600;
}

/* Sizes */
.size-sm {
  font-size: 0.75rem;
  padding: 0.25em 0.6em;
}
.size-md {
  font-size: 0.875rem;
  padding: 0.35em 0.75em;
}
.size-lg {
  font-size: 1rem;
  padding: 0.5em 1em;
}

/* Colors */
.badge-high {
  background: var(--color-success-dim);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}
.badge-medium {
  background: var(--color-warning-dim);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}
.badge-low {
  background: var(--color-danger-dim);
  color: var(--color-danger);
  border: 1px solid var(--color-danger);
}
</style>
