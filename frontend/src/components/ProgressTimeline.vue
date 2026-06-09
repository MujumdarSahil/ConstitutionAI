<template>
  <div class="progress-timeline">
    <div class="timeline-header">
      <h3>Study History</h3>
      <span class="text-muted text-sm">{{ sessions.length }} sessions</span>
    </div>

    <div v-if="!sessions.length" class="empty-state">
      <div class="empty-icon">📅</div>
      <p>No sessions yet. Start your first lesson!</p>
    </div>

    <div v-else class="timeline">
      <div
        v-for="(session, i) in sessions"
        :key="session._id"
        class="timeline-item"
        :class="{ 'is-latest': i === 0 }"
      >
        <!-- Connector line -->
        <div class="timeline-connector">
          <div class="timeline-dot" :class="getDotClass(session)"></div>
          <div v-if="i < sessions.length - 1" class="timeline-line"></div>
        </div>

        <!-- Content -->
        <div class="timeline-content card">
          <div class="session-header">
            <span class="session-date">{{ formatDate(session.date) }}</span>
            <div class="session-badges">
              <span class="badge" :class="session.completed ? 'badge-green' : 'badge-yellow'">
                {{ session.completed ? 'Completed' : 'Incomplete' }}
              </span>
              <span class="badge badge-blue">{{ session.provider_used || 'groq' }}</span>
            </div>
          </div>

          <div v-if="session.articles_covered?.length" class="articles-covered">
            <span
              v-for="artId in session.articles_covered"
              :key="artId"
              class="article-chip"
            >
              {{ formatArticleId(artId) }}
            </span>
          </div>

          <div v-if="session.session_summary" class="session-summary">
            {{ session.session_summary }}
          </div>

          <div class="session-meta">
            <span v-if="session.duration_mins" class="text-muted text-xs">
              ⏱ {{ Math.round(session.duration_mins) }} min
            </span>
            <span class="text-muted text-xs">
              📚 {{ session.articles_covered?.length || 0 }} articles
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  sessions: {
    type: Array,
    default: () => [],
  },
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-IN', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatArticleId(id) {
  return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).replace('Article ', 'Art.')
}

function getDotClass(session) {
  if (session.completed) return 'dot-success'
  return 'dot-warning'
}
</script>

<style scoped>
.progress-timeline {
  width: 100%;
}

.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-6);
}

.timeline-header h3 {
  font-size: 1.1rem;
  color: var(--color-text-primary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-12) var(--space-6);
  color: var(--color-text-muted);
  text-align: center;
}

.empty-icon { font-size: 2.5rem; margin-bottom: var(--space-4); }

.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-item {
  display: flex;
  gap: var(--space-4);
}

.timeline-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.timeline-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid;
  flex-shrink: 0;
  margin-top: var(--space-4);
  position: relative;
  z-index: 1;
}

.dot-success {
  background: var(--color-success);
  border-color: var(--color-success);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
}
.dot-warning {
  background: var(--color-warning);
  border-color: var(--color-warning);
}

.is-latest .timeline-dot {
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 8px rgba(16, 185, 129, 0.4); }
  50% { box-shadow: 0 0 16px rgba(16, 185, 129, 0.8); }
}

.timeline-line {
  width: 2px;
  flex: 1;
  background: var(--color-border);
  margin: var(--space-2) 0;
}

.timeline-content {
  flex: 1;
  margin-bottom: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.session-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.session-date {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.session-badges {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.articles-covered {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.article-chip {
  font-size: 0.72rem;
  font-family: var(--font-mono);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  color: var(--color-accent);
  padding: 0.2em 0.6em;
  border-radius: var(--radius-full);
  font-weight: 600;
}

.session-summary {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
  font-style: italic;
}

.session-meta {
  display: flex;
  gap: var(--space-4);
}
</style>
