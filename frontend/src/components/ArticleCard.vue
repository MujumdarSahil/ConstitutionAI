<template>
  <div class="article-card" :class="cardClass" @click="$emit('click', article)">
    <div class="card-top">
      <div class="article-meta">
        <span class="article-part">{{ article.part || 'Constitution' }}</span>
        <ScoreBadge v-if="article.first_taught_date" :score="article.last_score || 0" size="sm" />
        <span v-else class="badge badge-blue">New</span>
      </div>
      <span v-if="article.needs_review" class="review-indicator" title="Due for review">
        🔄
      </span>
    </div>

    <div class="article-id">{{ formatId(article.article_id) }}</div>
    <div class="article-title">{{ article.title || formatId(article.article_id) }}</div>

    <div class="card-bottom">
      <span v-if="article.first_taught_date" class="taught-date">
        Studied {{ formatDate(article.first_taught_date) }}
      </span>
      <span v-else class="not-studied">Not studied yet</span>

      <div class="card-action" v-if="showAction">
        <span v-if="article.needs_review" class="text-warning text-xs">Review Due</span>
        <span v-else-if="!article.first_taught_date" class="text-accent text-xs">Start →</span>
        <span v-else class="text-muted text-xs">Revisit →</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import ScoreBadge from './ScoreBadge.vue'

defineEmits(['click'])

const props = defineProps({
  article: {
    type: Object,
    required: true,
  },
  showAction: {
    type: Boolean,
    default: true,
  },
  compact: {
    type: Boolean,
    default: false,
  },
})

const cardClass = {
  'card': true,
  'article-card-taught': props.article.first_taught_date,
  'article-card-review': props.article.needs_review,
  'compact': props.compact,
}

function formatId(id) {
  if (!id) return ''
  return id
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace('Article ', 'Art. ')
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.article-card {
  cursor: pointer;
  transition: all var(--transition-normal);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.article-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-glow);
  transform: translateY(-2px);
}

.article-card-review {
  border-color: var(--color-warning) !important;
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.article-part {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.review-indicator {
  font-size: 0.9rem;
  animation: spin 3s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.article-id {
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--color-accent);
  font-weight: 600;
}

.article-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.3;
  flex: 1;
}

.card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border-subtle);
}

.taught-date, .not-studied {
  font-size: 0.72rem;
  color: var(--color-text-muted);
}

.compact {
  padding: var(--space-3) var(--space-4);
}

.compact .article-title {
  font-size: 0.85rem;
}
</style>
