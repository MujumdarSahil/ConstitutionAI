<template>
  <div class="progress-view page-container">
    <div class="page-header fade-in">
      <h1>Your Progress</h1>
      <p class="text-muted">Track your constitutional law mastery journey</p>
    </div>

    <!-- Stats grid -->
    <div class="stats-grid fade-in" v-if="summary">
      <div class="stat-block card">
        <div class="stat-icon">📚</div>
        <div class="stat-value">{{ summary.total_articles_taught }}</div>
        <div class="stat-label">Articles Studied</div>
        <div class="stat-sub text-muted text-xs">of {{ summary.total_articles_available }} total</div>
      </div>
      <div class="stat-block card">
        <div class="stat-icon">🎯</div>
        <div class="stat-value">{{ summary.average_score }}%</div>
        <div class="stat-label">Average Score</div>
        <div class="stat-sub" :class="getScoreClass(summary.average_score)">
          {{ getScoreLabel(summary.average_score) }}
        </div>
      </div>
      <div class="stat-block card">
        <div class="stat-icon">🔥</div>
        <div class="stat-value">{{ summary.current_streak_days }}</div>
        <div class="stat-label">Day Streak</div>
        <div class="stat-sub text-muted text-xs">consecutive days studied</div>
      </div>
      <div class="stat-block card">
        <div class="stat-icon">⚡</div>
        <div class="stat-value">{{ summary.needs_review?.length || 0 }}</div>
        <div class="stat-label">Needs Review</div>
        <div class="stat-sub text-muted text-xs">articles below 60%</div>
      </div>
    </div>

    <!-- Overall progress bar -->
    <div class="overall-progress card fade-in" v-if="summary">
      <div class="flex justify-between mb-4">
        <div>
          <div class="font-semibold">Overall Completion</div>
          <div class="text-muted text-sm">{{ summary.percent_complete }}% of the Constitution covered</div>
        </div>
        <div class="progress-fraction">
          {{ summary.total_articles_taught }}/{{ summary.total_articles_available }}
        </div>
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar-fill" :style="{ width: summary.percent_complete + '%' }"></div>
      </div>
    </div>

    <!-- Study activity heatmap -->
    <div class="heatmap-section card fade-in">
      <h3>Study Activity — Last 12 Weeks</h3>
      <div class="heatmap-grid">
        <div
          v-for="day in heatmapDays"
          :key="day.date"
          class="heatmap-cell"
          :class="day.intensity"
          :title="`${day.dateLabel}: ${day.count} session${day.count !== 1 ? 's' : ''}`"
        ></div>
      </div>
      <div class="heatmap-legend">
        <span class="text-muted text-xs">Less</span>
        <div class="legend-cell level-0"></div>
        <div class="legend-cell level-1"></div>
        <div class="legend-cell level-2"></div>
        <div class="legend-cell level-3"></div>
        <div class="legend-cell level-4"></div>
        <span class="text-muted text-xs">More</span>
      </div>
    </div>

    <!-- Weak topics -->
    <div v-if="weakTopics.length" class="section fade-in">
      <div class="section-header">
        <h2>⚡ Weak Topics</h2>
        <span class="badge badge-red">Score below 60%</span>
      </div>
      <div class="grid grid-3 stagger">
        <ArticleCard
          v-for="article in weakTopics"
          :key="article.article_id"
          :article="article"
          @click="revise(article.article_id)"
        />
      </div>
    </div>

    <!-- Articles needing review -->
    <div v-if="needsReview.length" class="section fade-in">
      <div class="section-header">
        <h2>🔄 Due for Review</h2>
        <span class="badge badge-yellow">{{ needsReview.length }} articles</span>
      </div>
      <div class="review-list">
        <div
          v-for="article in needsReview"
          :key="article.article_id"
          class="review-row card"
          @click="revise(article.article_id)"
        >
          <div class="review-info">
            <span class="article-chip">{{ formatId(article.article_id) }}</span>
            <span class="text-secondary text-sm">{{ article.title }}</span>
          </div>
          <div class="review-actions">
            <ScoreBadge :score="article.last_score" size="sm" />
            <span class="review-due text-xs text-warning">
              Due {{ formatDate(article.review_due_date) }}
            </span>
            <button class="btn btn-secondary btn-sm">Revise →</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Session history -->
    <div class="section fade-in">
      <div class="section-header">
        <h2>📅 Session History</h2>
      </div>
      <div v-if="isLoading" class="text-muted text-center p-6">Loading...</div>
      <ProgressTimeline v-else :sessions="recentSessions" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProgressStore } from '@/stores/progress.js'
import ArticleCard from '@/components/ArticleCard.vue'
import ScoreBadge from '@/components/ScoreBadge.vue'
import ProgressTimeline from '@/components/ProgressTimeline.vue'

const router = useRouter()
const progressStore = useProgressStore()

const summary = computed(() => progressStore.summary)
const weakTopics = computed(() => progressStore.weakTopics)
const needsReview = computed(() => progressStore.needsReview)
const recentSessions = computed(() => progressStore.recentSessions)
const isLoading = computed(() => progressStore.isLoading)

function formatId(id) {
  if (!id) return ''
  return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

function getScoreClass(score) {
  if (score >= 80) return 'text-success'
  if (score >= 60) return 'text-warning'
  return 'text-danger'
}

function getScoreLabel(score) {
  if (score >= 80) return 'Excellent'
  if (score >= 60) return 'Good'
  return 'Needs work'
}

function revise(articleId) {
  router.push({ name: 'learn', params: { articleId }, query: { revision: 'true' } })
}

// Build 84-day heatmap (12 weeks)
const heatmapDays = computed(() => {
  const sessions = recentSessions.value || []
  const sessionDateCounts = {}
  sessions.forEach(s => {
    const d = new Date(s.date)
    const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
    sessionDateCounts[key] = (sessionDateCounts[key] || 0) + 1
  })

  const days = []
  const today = new Date()
  for (let i = 83; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(today.getDate() - i)
    const key = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
    const count = sessionDateCounts[key] || 0
    let intensity = 'level-0'
    if (count >= 4) intensity = 'level-4'
    else if (count === 3) intensity = 'level-3'
    else if (count === 2) intensity = 'level-2'
    else if (count === 1) intensity = 'level-1'
    days.push({
      date: key,
      dateLabel: date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
      count,
      intensity,
    })
  }
  return days
})

onMounted(async () => {
  await progressStore.fetchAll()
})
</script>

<style scoped>
.progress-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}

.page-header h1 {
  font-size: 2rem;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

@media (max-width: 900px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

.stat-block {
  text-align: center;
  padding: var(--space-5) var(--space-4);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.stat-icon { font-size: 1.8rem; }

.stat-value {
  font-size: 2.2rem;
  font-weight: 900;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}

.stat-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.stat-sub { font-size: 0.72rem; }

/* Overall progress */
.progress-fraction {
  font-size: 1.5rem;
  font-weight: 800;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Heatmap */
.heatmap-section h3 {
  font-size: 1rem;
  margin-bottom: var(--space-4);
}

.heatmap-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 3px;
}

@media (max-width: 600px) {
  .heatmap-grid { grid-template-columns: repeat(7, 1fr); }
}

.heatmap-cell {
  aspect-ratio: 1;
  border-radius: 2px;
  transition: transform 0.1s ease;
  cursor: default;
}

.heatmap-cell:hover { transform: scale(1.3); }

.level-0 { background: var(--color-bg-elevated); }
.level-1 { background: rgba(59, 130, 246, 0.25); }
.level-2 { background: rgba(59, 130, 246, 0.5); }
.level-3 { background: rgba(59, 130, 246, 0.75); }
.level-4 { background: var(--color-accent); }

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--space-3);
  justify-content: flex-end;
}

.legend-cell {
  width: 14px;
  height: 14px;
  border-radius: 2px;
}

/* Sections */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.section-header h2 { font-size: 1.25rem; }

/* Review list */
.review-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.review-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.review-row:hover {
  border-color: var(--color-warning);
}

.review-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.article-chip {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-accent);
  background: var(--color-accent-dim);
  padding: 0.2em 0.6em;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.review-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.review-due {
  white-space: nowrap;
}
</style>
