<template>
  <div class="home-view page-container">
    <!-- Welcome hero -->
    <div class="hero-section fade-in">
      <div class="hero-text">
        <div class="greeting">{{ greeting }}, Aspirant 🇮🇳</div>
        <h1>Master the Indian Constitution</h1>
        <p class="hero-subtitle">
          {{ sessionPlan?.message || 'Your AI-powered UPSC preparation begins here.' }}
        </p>
      </div>
      <div class="hero-stats">
        <div class="stat-card">
          <div class="stat-value">{{ streak }}</div>
          <div class="stat-label">Day Streak 🔥</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ totalTaught }}</div>
          <div class="stat-label">Articles Studied</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ averageScore }}%</div>
          <div class="stat-label">Avg. Score</div>
        </div>
      </div>
    </div>

    <!-- Progress bar -->
    <div class="progress-section card fade-in">
      <div class="flex justify-between items-center mb-4">
        <div>
          <div class="font-semibold text-lg">Overall Progress</div>
          <div class="text-muted text-sm">{{ totalTaught }} of {{ totalAvailable }} articles completed</div>
        </div>
        <div class="progress-percent">{{ percentComplete }}%</div>
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar-fill" :style="{ width: percentComplete + '%' }"></div>
      </div>
    </div>

    <!-- Today's session CTA -->
    <div class="session-cta card fade-in">
      <div class="cta-left">
        <div v-if="sessionPlan?.next_article" class="next-article-info">
          <div class="next-label">
            <span v-if="sessionPlan.is_revision" class="badge badge-yellow">🔄 Revision</span>
            <span v-else class="badge badge-blue">📖 New Article</span>
            <span class="text-muted text-sm">~{{ sessionPlan.estimated_duration_mins }} min</span>
          </div>
          <div class="next-article-title">
            {{ sessionPlan.next_article.title || formatId(sessionPlan.next_article.article_id) }}
          </div>
          <div class="next-article-meta">
            {{ sessionPlan.next_article.part }} ·
            {{ formatId(sessionPlan.next_article.article_id) }}
            <ScoreBadge
              v-if="sessionPlan.next_article.last_score"
              :score="sessionPlan.next_article.last_score"
              size="sm"
            />
          </div>
        </div>
        <div v-else class="all-done">
          <div class="all-done-icon">🎉</div>
          <div>
            <div class="font-semibold">All articles studied!</div>
            <div class="text-muted text-sm">Jump to revision or explore any article.</div>
          </div>
        </div>
      </div>

      <div class="cta-actions">
        <button
          v-if="sessionPlan?.next_article"
          class="btn btn-primary btn-lg"
          :disabled="isStarting"
          @click="startTodaySession"
          id="start-session-btn"
        >
          <span v-if="isStarting">Starting...</span>
          <span v-else>{{ sessionPlan.has_completed_today ? 'Continue Studying →' : 'Start Today\'s Session →' }}</span>
        </button>
        <router-link to="/revision" class="btn btn-secondary btn-lg">
          Browse Articles
        </router-link>
      </div>
    </div>

    <!-- Review due section -->
    <div v-if="needsReview.length" class="review-section">
      <div class="section-header">
        <h2>🔄 Due for Review</h2>
        <span class="badge badge-yellow">{{ needsReview.length }} articles</span>
      </div>
      <div class="grid grid-3 stagger">
        <ArticleCard
          v-for="article in needsReview.slice(0, 6)"
          :key="article.article_id"
          :article="article"
          @click="jumpToArticle(article.article_id)"
        />
      </div>
    </div>

    <!-- Weak topics section -->
    <div v-if="weakTopics.length" class="weak-section">
      <div class="section-header">
        <h2>⚡ Needs Attention</h2>
        <span class="badge badge-red">Score below 60%</span>
      </div>
      <div class="grid grid-3 stagger">
        <ArticleCard
          v-for="article in weakTopics.slice(0, 6)"
          :key="article.article_id"
          :article="article"
          @click="jumpToArticle(article.article_id)"
        />
      </div>
    </div>

    <!-- Recent sessions -->
    <div v-if="recentSessions.length" class="recent-section">
      <div class="section-header">
        <h2>📅 Recent Sessions</h2>
        <router-link to="/progress" class="btn btn-ghost btn-sm">View All →</router-link>
      </div>
      <ProgressTimeline :sessions="recentSessions.slice(0, 3)" />
    </div>

    <!-- Setup banner -->
    <div v-if="showSetupBanner" class="setup-banner card">
      <div class="setup-icon">🚀</div>
      <div class="setup-text">
        <div class="font-semibold">First-time setup required</div>
        <div class="text-muted text-sm">
          Place your constitution PDF at <code>backend/data/constitution.pdf</code> and run the setup.
        </div>
      </div>
      <button class="btn btn-primary" @click="runSetup" :disabled="isSettingUp">
        {{ isSettingUp ? 'Setting up...' : 'Run Setup' }}
      </button>
    </div>

    <!-- Setup progress -->
    <div v-if="setupMessages.length" class="setup-progress card">
      <div class="font-semibold mb-4">Setup Progress</div>
      <div class="setup-log">
        <div
          v-for="(msg, i) in setupMessages"
          :key="i"
          class="log-line"
          :class="{ 'log-error': msg.error, 'log-done': msg.done }"
        >
          <span class="log-step" v-if="msg.step">{{ msg.step }}/{{ msg.total }}</span>
          <span class="log-message">{{ msg.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session.js'
import { useProgressStore } from '@/stores/progress.js'
import ArticleCard from '@/components/ArticleCard.vue'
import ProgressTimeline from '@/components/ProgressTimeline.vue'
import ScoreBadge from '@/components/ScoreBadge.vue'
import axios from 'axios'

const router = useRouter()
const sessionStore = useSessionStore()
const progressStore = useProgressStore()

const isStarting = ref(false)
const isSettingUp = ref(false)
const setupMessages = ref([])
const showSetupBanner = ref(false)

// Computed from stores
const sessionPlan = computed(() => sessionStore.sessionPlan)
const totalTaught = computed(() => progressStore.totalTaught)
const totalAvailable = computed(() => progressStore.totalAvailable)
const percentComplete = computed(() => progressStore.percentComplete)
const averageScore = computed(() => progressStore.averageScore)
const streak = computed(() => progressStore.streak)
const weakTopics = computed(() => progressStore.weakTopics)
const needsReview = computed(() => progressStore.needsReview)
const recentSessions = computed(() => progressStore.recentSessions)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
})

function formatId(id) {
  if (!id) return ''
  return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

async function startTodaySession() {
  isStarting.value = true
  try {
    const session = await sessionStore.startSession()
    const articleId = sessionPlan.value?.next_article?.article_id
    if (articleId) {
      sessionStore.setCurrentArticle(articleId)
      router.push({ name: 'learn', params: { articleId } })
    }
  } catch (err) {
    console.error('Failed to start session:', err)
  } finally {
    isStarting.value = false
  }
}

function jumpToArticle(articleId) {
  router.push({ name: 'learn', params: { articleId }, query: { revision: 'true' } })
}

async function runSetup() {
  isSettingUp.value = true
  setupMessages.value = []

  try {
    const response = await fetch('/api/setup', { method: 'POST' })
    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const lines = decoder.decode(value).split('\n').filter(l => l.trim())
      for (const line of lines) {
        try {
          const msg = JSON.parse(line)
          setupMessages.value.push(msg)
          if (msg.done && !msg.error) {
            showSetupBanner.value = false
            await loadAll()
          }
        } catch {}
      }
    }
  } catch (err) {
    setupMessages.value.push({ message: `Setup error: ${err.message}`, error: true })
  } finally {
    isSettingUp.value = false
  }
}

async function loadAll() {
  try {
    await Promise.all([
      sessionStore.loadPlan(),
      progressStore.fetchAll(),
    ])
    showSetupBanner.value = progressStore.totalAvailable === 0
  } catch (err) {
    showSetupBanner.value = true
  }
}

onMounted(loadAll)
</script>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}

/* Hero */
.hero-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-8);
  flex-wrap: wrap;
}

.greeting {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: var(--space-2);
}

.hero-text h1 {
  font-size: 2.2rem;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: var(--space-3);
}

.hero-subtitle {
  font-size: 1rem;
  color: var(--color-text-secondary);
  max-width: 500px;
  line-height: 1.6;
}

.hero-stats {
  display: flex;
  gap: var(--space-4);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.stat-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-4) var(--space-6);
  text-align: center;
  min-width: 90px;
  transition: all var(--transition-normal);
}

.stat-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-glow);
}

.stat-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text-primary);
  line-height: 1;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stat-label {
  font-size: 0.72rem;
  color: var(--color-text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: var(--space-1);
}

/* Progress */
.progress-percent {
  font-size: 1.5rem;
  font-weight: 800;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* CTA */
.session-cta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  background: linear-gradient(135deg, #0d1528, #162035);
  border-color: var(--color-accent-dim);
  flex-wrap: wrap;
}

.next-label {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.next-article-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: var(--space-1);
}

.next-article-meta {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.cta-actions {
  display: flex;
  gap: var(--space-3);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.all-done {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
.all-done-icon { font-size: 2.5rem; }

/* Sections */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.section-header h2 {
  font-size: 1.25rem;
}

/* Setup banner */
.setup-banner {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  background: linear-gradient(135deg, #1a0a00, #2d1500);
  border-color: var(--color-warning);
  flex-wrap: wrap;
}

.setup-icon { font-size: 2rem; }

.setup-text { flex: 1; }

/* Setup progress */
.setup-progress {
  background: var(--color-bg-card);
}

.setup-log {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  font-family: var(--font-mono);
  font-size: 0.82rem;
}

.log-line {
  display: flex;
  gap: var(--space-3);
  color: var(--color-text-secondary);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-elevated);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.log-step {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.log-error {
  color: var(--color-danger);
  border-color: var(--color-danger);
  background: var(--color-danger-dim);
}

.log-done {
  color: var(--color-success);
  border-color: var(--color-success);
  background: var(--color-success-dim);
}
</style>
