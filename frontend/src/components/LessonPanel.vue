<template>
  <div class="lesson-panel">
    <!-- Header bar -->
    <div class="lesson-header">
      <div class="lesson-meta">
        <span class="lesson-article-id">{{ formatId(articleId) }}</span>
        <ProviderStatus :provider="provider" :streaming="isStreaming" />
      </div>
      <div v-if="isStreaming" class="streaming-indicator">
        <span class="dot-1">.</span><span class="dot-2">.</span><span class="dot-3">.</span>
        <span class="ml-1 text-xs text-muted">Generating lesson</span>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="isLoading && !displayText" class="skeleton-lesson">
      <div class="skeleton skeleton-text wide" style="height: 2rem; width: 60%"></div>
      <div class="skeleton skeleton-text wide" style="margin-top: 1.5rem"></div>
      <div class="skeleton skeleton-text medium"></div>
      <div class="skeleton skeleton-text wide"></div>
      <div class="skeleton skeleton-text short"></div>
      <div class="skeleton skeleton-text wide" style="margin-top: 1.5rem"></div>
      <div class="skeleton skeleton-text medium"></div>
      <div class="skeleton skeleton-text wide"></div>
    </div>

    <!-- Lesson content -->
    <div v-if="displayText" class="lesson-content" v-html="renderedHtml"></div>

    <!-- Error state -->
    <div v-if="errorMessage" class="lesson-error">
      <div class="error-icon">⚠️</div>
      <div class="error-text">{{ errorMessage }}</div>
      <button class="btn btn-secondary btn-sm mt-4" @click="$emit('retry')">
        Retry
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ProviderStatus from './ProviderStatus.vue'

const props = defineProps({
  articleId: String,
  displayText: String,
  provider: { type: String, default: 'groq' },
  isStreaming: { type: Boolean, default: false },
  isLoading: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
})

defineEmits(['retry'])

function formatId(id) {
  if (!id) return ''
  return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// Simple markdown-to-HTML renderer (no external dependency needed)
const renderedHtml = computed(() => {
  if (!props.displayText) return ''
  let text = props.displayText

  // Headers
  text = text.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  text = text.replace(/^# (.+)$/gm, '<h2>$1</h2>')

  // Bold and italic
  text = text.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/\*(.+?)\*/g, '<em>$1</em>')

  // Blockquote
  text = text.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')

  // Unordered lists
  text = text.replace(/(^[\*\-] .+$(\n[\*\-] .+$)*)/gm, (match) => {
    const items = match.split('\n')
      .filter(l => l.trim())
      .map(l => `<li>${l.replace(/^[\*\-] /, '')}</li>`)
      .join('')
    return `<ul>${items}</ul>`
  })

  // Ordered lists
  text = text.replace(/(^\d+\. .+$(\n\d+\. .+$)*)/gm, (match) => {
    const items = match.split('\n')
      .filter(l => l.trim())
      .map(l => `<li>${l.replace(/^\d+\. /, '')}</li>`)
      .join('')
    return `<ol>${items}</ol>`
  })

  // Paragraphs (wrap non-tagged lines)
  text = text.split('\n\n').map(block => {
    block = block.trim()
    if (!block) return ''
    if (block.startsWith('<h') || block.startsWith('<ul') ||
        block.startsWith('<ol') || block.startsWith('<blockquote')) {
      return block
    }
    return `<p>${block.replace(/\n/g, '<br>')}</p>`
  }).join('\n')

  // Inline code
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>')

  return text
})
</script>

<style scoped>
.lesson-panel {
  width: 100%;
}

.lesson-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
  gap: var(--space-3);
}

.lesson-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.lesson-article-id {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  color: var(--color-accent);
  font-weight: 600;
  background: var(--color-accent-dim);
  padding: 0.25em 0.75em;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-accent);
}

.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 0;
  color: var(--color-accent);
  font-size: 1.2rem;
  font-weight: 700;
}

.streaming-indicator span {
  animation: bounce 1.2s infinite;
}
.dot-1 { animation-delay: 0s; }
.dot-2 { animation-delay: 0.2s; }
.dot-3 { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-4px); }
}

.skeleton-lesson {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4) 0;
}

.lesson-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-12) var(--space-6);
  text-align: center;
  color: var(--color-danger);
}

.error-icon {
  font-size: 2.5rem;
  margin-bottom: var(--space-4);
}

.error-text {
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  max-width: 400px;
}

.ml-1 { margin-left: 0.25rem; }
</style>
