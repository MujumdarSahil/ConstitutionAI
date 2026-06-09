<template>
  <div class="test-view page-container">
    <!-- Loading state -->
    <div v-if="isLoading" class="loading-state fade-in">
      <div class="loading-icon">📝</div>
      <h2>Generating your quiz...</h2>
      <p class="text-muted">Crafting questions about {{ formatIds(articleIds) }}</p>
      <div class="loading-bar">
        <div class="loading-bar-fill"></div>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state fade-in">
      <div class="error-icon">⚠️</div>
      <h2>Quiz Generation Failed</h2>
      <p class="text-muted">{{ error }}</p>
      <div class="flex gap-3 mt-6">
        <button class="btn btn-secondary" @click="$router.back()">Go Back</button>
        <button class="btn btn-primary" @click="loadQuiz">Retry</button>
      </div>
    </div>

    <!-- Quiz active -->
    <template v-else-if="questions.length && !showFinalScore">
      <!-- Header -->
      <div class="quiz-header fade-in">
        <router-link to="/" class="btn btn-ghost btn-sm">← Exit Quiz</router-link>
        <div class="quiz-progress-bar">
          <div
            class="quiz-progress-fill"
            :style="{ width: `${(answeredCount / questions.length) * 100}%` }"
          ></div>
        </div>
        <span class="quiz-counter">{{ answeredCount }}/{{ questions.length }}</span>
      </div>

      <div class="quiz-title fade-in">
        <h1>Constitution Quiz</h1>
        <p class="text-muted">{{ formatIds(articleIds) }}</p>
      </div>

      <!-- Questions -->
      <div class="questions-list stagger">
        <QuizQuestion
          v-for="(q, i) in questions"
          :key="q._id"
          :question="q"
          :index="i"
          :show-result="!!results[q._id]"
          :result="results[q._id]"
          @submit="handleSubmit"
        />
      </div>

      <!-- Submit all / Finish -->
      <div class="quiz-footer card fade-in" v-if="answeredCount > 0">
        <div class="footer-score">
          <span class="text-muted text-sm">Current score:</span>
          <span class="current-score">{{ currentScore }}%</span>
        </div>
        <button
          v-if="answeredCount === questions.length"
          class="btn btn-primary btn-lg"
          @click="finishQuiz"
          id="finish-quiz-btn"
        >
          See Final Results →
        </button>
        <span v-else class="text-muted text-sm">
          {{ questions.length - answeredCount }} questions remaining
        </span>
      </div>
    </template>

    <!-- Final score screen -->
    <div v-else-if="showFinalScore" class="final-score-screen fade-in">
      <!-- Score card -->
      <div class="score-card card">
        <div class="score-emoji">{{ scoreSummary.emoji }}</div>
        <div class="final-score-value">{{ finalScore }}%</div>
        <div class="final-score-label">{{ scoreSummary.label }}</div>
        <div
          class="pass-fail-badge"
          :class="finalScore >= 60 ? 'badge-green' : 'badge-red'"
        >
          {{ finalScore >= 60 ? '✅ PASS — Good Understanding' : '❌ NEEDS MORE STUDY' }}
        </div>
      </div>

      <!-- Question breakdown -->
      <div class="score-breakdown card">
        <h3>Question Breakdown</h3>
        <div class="breakdown-list">
          <div
            v-for="q in questions"
            :key="q._id"
            class="breakdown-item"
          >
            <span class="result-icon">
              {{ results[q._id]?.is_correct ? '✓' : '✗' }}
            </span>
            <span class="breakdown-q">{{ q.question.slice(0, 80) }}...</span>
            <ScoreBadge :score="results[q._id]?.score || 0" size="sm" :show-label="false" />
          </div>
        </div>
      </div>

      <!-- Weak areas -->
      <div v-if="weakAreas.length" class="weak-areas card">
        <h3>⚡ Areas to Review</h3>
        <ul>
          <li v-for="(item, i) in weakAreas" :key="i" class="weak-item">
            {{ item }}
          </li>
        </ul>
      </div>

      <!-- Actions -->
      <div class="final-actions">
        <router-link to="/" class="btn btn-secondary btn-lg">Back to Dashboard</router-link>
        <router-link :to="`/learn/${articleIds[0]}`" class="btn btn-ghost btn-lg">
          Review Lesson Again
        </router-link>
        <router-link to="/revision" class="btn btn-primary btn-lg">
          Continue Studying →
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session.js'
import QuizQuestion from '@/components/QuizQuestion.vue'
import ScoreBadge from '@/components/ScoreBadge.vue'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()

const sessionId = computed(() => route.params.sessionId)
const articleIds = computed(() => {
  const ids = route.query.article_ids
  return ids ? ids.split(',').filter(Boolean) : []
})

const questions = ref([])
const results = ref({})
const isLoading = ref(true)
const error = ref('')
const showFinalScore = ref(false)

const answeredCount = computed(() => Object.keys(results.value).length)

const currentScore = computed(() => {
  const scores = Object.values(results.value).map(r => r.score || 0)
  if (!scores.length) return 0
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
})

const finalScore = computed(() => currentScore.value)

const scoreSummary = computed(() => {
  const s = finalScore.value
  if (s >= 90) return { emoji: '🏆', label: 'Outstanding! You\'ve mastered this article.' }
  if (s >= 80) return { emoji: '⭐', label: 'Excellent work! Strong understanding.' }
  if (s >= 60) return { emoji: '👍', label: 'Good job! A few areas to polish.' }
  if (s >= 40) return { emoji: '📚', label: 'Needs more study. Review the lesson again.' }
  return { emoji: '💪', label: 'Keep going! The Constitution takes time to master.' }
})

const weakAreas = computed(() => {
  return questions.value
    .filter(q => results.value[q._id] && !results.value[q._id].is_correct)
    .map(q => q.question.slice(0, 100) + '...')
    .slice(0, 3)
})

function formatIds(ids) {
  return ids.map(id => id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())).join(', ')
}

async function loadQuiz() {
  isLoading.value = true
  error.value = ''
  results.value = {}
  showFinalScore.value = false

  try {
    const ids = articleIds.value.join(',')
    const { data } = await axios.get(`/api/test/${sessionId.value}?article_ids=${ids}`)
    questions.value = data.questions || []
    if (!questions.value.length) {
      error.value = 'No questions were generated. Please try again.'
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to generate quiz.'
  } finally {
    isLoading.value = false
  }
}

async function handleSubmit({ questionId, answer }) {
  if (results.value[questionId]) return // already answered

  try {
    const { data } = await axios.post('/api/test/submit', {
      test_result_id: questionId,
      user_answer: answer,
    })
    results.value = { ...results.value, [questionId]: data }

    // Update article score
    const q = questions.value.find(q => q._id === questionId)
    if (q && sessionStore) {
      await sessionStore.updateScore(q.article_id, data.score)
    }
  } catch (err) {
    console.error('Submit error:', err)
  }
}

async function finishQuiz() {
  showFinalScore.value = true

  // End session with this article
  if (sessionStore.currentSession) {
    await sessionStore.endSession(
      articleIds.value,
      0,
      `Quiz score: ${finalScore.value}%`
    )
  }

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(loadQuiz)
</script>

<style scoped>
.test-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 760px;
}

/* Loading */
.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-16) var(--space-8);
  text-align: center;
}

.loading-icon, .error-icon {
  font-size: 3rem;
  margin-bottom: var(--space-4);
}

.loading-bar {
  width: 240px;
  height: 4px;
  background: var(--color-bg-elevated);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-top: var(--space-8);
}

.loading-bar-fill {
  height: 100%;
  background: var(--gradient-accent);
  border-radius: var(--radius-full);
  animation: loading-pulse 1.5s ease-in-out infinite;
}

@keyframes loading-pulse {
  0% { width: 0%; }
  50% { width: 80%; }
  100% { width: 100%; }
}

/* Quiz header */
.quiz-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--color-bg-primary);
  padding: var(--space-3) 0;
}

.quiz-progress-bar {
  flex: 1;
  height: 6px;
  background: var(--color-bg-elevated);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.quiz-progress-fill {
  height: 100%;
  background: var(--gradient-accent);
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

.quiz-counter {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.quiz-title h1 {
  font-size: 1.6rem;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Questions */
.questions-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

/* Footer */
.quiz-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  bottom: var(--space-4);
  background: var(--color-bg-card);
}

.footer-score {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.current-score {
  font-size: 1.5rem;
  font-weight: 800;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Final score */
.final-score-screen {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.score-card {
  text-align: center;
  padding: var(--space-10);
  background: linear-gradient(145deg, #0d1528, #162035);
  border-color: var(--color-accent-dim);
}

.score-emoji {
  font-size: 4rem;
  margin-bottom: var(--space-4);
}

.final-score-value {
  font-size: 4rem;
  font-weight: 900;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
  margin-bottom: var(--space-2);
}

.final-score-label {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-4);
}

.pass-fail-badge {
  display: inline-flex;
  padding: 0.5em 1.5em;
  border-radius: var(--radius-full);
  font-weight: 700;
  font-size: 0.85rem;
}

/* Breakdown */
.score-breakdown h3, .weak-areas h3 {
  font-size: 1.1rem;
  margin-bottom: var(--space-4);
}

.breakdown-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.breakdown-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-elevated);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
}

.result-icon {
  font-weight: 700;
  font-size: 1rem;
  width: 20px;
  flex-shrink: 0;
}

.breakdown-q {
  flex: 1;
  color: var(--color-text-secondary);
  font-size: 0.82rem;
}

/* Weak areas */
.weak-areas ul {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.weak-item {
  padding: var(--space-2) var(--space-3);
  background: var(--color-danger-dim);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.final-actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  justify-content: center;
}
</style>
