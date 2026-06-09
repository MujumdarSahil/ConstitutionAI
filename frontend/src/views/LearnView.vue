<template>
  <div class="learn-view page-container">
    <!-- Top bar -->
    <div class="learn-topbar fade-in">
      <router-link to="/" class="btn btn-ghost btn-sm back-btn">
        ← Back
      </router-link>
      <div class="topbar-right">
        <ProviderStatus :provider="provider" :streaming="isStreaming" />
        <span v-if="revisionMode" class="badge badge-yellow">Revision Mode</span>
      </div>
    </div>

    <!-- Article header -->
    <div class="article-header fade-in" v-if="articleProgress">
      <div class="article-part">{{ articleProgress.part }}</div>
      <h1 class="article-title-main">
        {{ articleProgress.title || formatId(articleId) }}
      </h1>
      <div class="article-meta-row">
        <span class="article-id-chip">{{ formatId(articleId) }}</span>
        <ScoreBadge
          v-if="articleProgress.last_score"
          :score="articleProgress.last_score"
          size="md"
        />
        <span v-if="articleProgress.times_reviewed" class="text-muted text-sm">
          Reviewed {{ articleProgress.times_reviewed }}×
        </span>
      </div>
    </div>

    <!-- Lesson panel -->
    <div class="lesson-container">
      <LessonPanel
        :article-id="articleId"
        :display-text="lessonText"
        :provider="provider"
        :is-streaming="isStreaming"
        :is-loading="isLoading"
        :error-message="errorMessage"
        @retry="startLesson"
      />
    </div>

    <!-- Action bar — appears after lesson loads -->
    <Transition name="slide-up">
      <div v-if="lessonComplete && !revisionMode" class="action-bar card fade-in">
        <div class="action-bar-left">
          <div class="font-semibold">Lesson complete! 🎉</div>
          <div class="text-muted text-sm">Ready to test your understanding?</div>
        </div>
        <div class="action-bar-right">
          <button class="btn btn-ghost" @click="markAndContinue">
            Skip Test, Continue →
          </button>
          <button class="btn btn-primary btn-lg" @click="takeTest" id="take-test-btn">
            Take the Quiz →
          </button>
        </div>
      </div>
    </Transition>

    <!-- Revision mode action bar -->
    <Transition name="slide-up">
      <div v-if="lessonComplete && revisionMode" class="action-bar card fade-in">
        <div class="action-bar-left">
          <div class="font-semibold">Revision complete! 📚</div>
          <div class="text-muted text-sm">Test your refreshed knowledge.</div>
        </div>
        <div class="action-bar-right">
          <router-link to="/revision" class="btn btn-ghost">Browse More →</router-link>
          <button class="btn btn-primary" @click="takeTest" id="revision-test-btn">
            Quick Quiz →
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session.js'
import { useProgressStore } from '@/stores/progress.js'
import LessonPanel from '@/components/LessonPanel.vue'
import ProviderStatus from '@/components/ProviderStatus.vue'
import ScoreBadge from '@/components/ScoreBadge.vue'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()
const progressStore = useProgressStore()

const articleId = computed(() => route.params.articleId)
const revisionMode = computed(() => route.query.revision === 'true')

const lessonText = ref('')
const isLoading = ref(true)
const isStreaming = ref(false)
const lessonComplete = ref(false)
const errorMessage = ref('')
const provider = ref('groq')
const articleProgress = ref(null)
const sessionStartTime = ref(null)

let eventSource = null

function formatId(id) {
  if (!id) return ''
  return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

async function loadArticleProgress() {
  try {
    const { data } = await axios.get(`/api/articles/${articleId.value}`)
    articleProgress.value = data
  } catch {
    // Not critical
  }
}

function startLesson() {
  lessonText.value = ''
  isLoading.value = true
  isStreaming.value = false
  lessonComplete.value = false
  errorMessage.value = ''

  if (eventSource) {
    eventSource.close()
  }

  sessionStartTime.value = Date.now()

  eventSource = new EventSource(`/api/teach/${articleId.value}`)

  eventSource.addEventListener('meta', (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.provider) {
        provider.value = data.provider
        sessionStore.setProvider(data.provider)
      }
    } catch {}
    isLoading.value = false
    isStreaming.value = true
  })

  eventSource.addEventListener('token', (e) => {
    isLoading.value = false
    isStreaming.value = true
    lessonText.value += e.data
  })

  eventSource.addEventListener('done', async () => {
    isStreaming.value = false
    lessonComplete.value = true
    eventSource.close()

    // Mark article as taught
    if (sessionStore.currentSession) {
      await sessionStore.markArticleTaught(articleId.value)
    }
  })

  eventSource.addEventListener('error', (e) => {
    try {
      const data = JSON.parse(e.data)
      errorMessage.value = data.error || 'Failed to load lesson.'
    } catch {
      errorMessage.value = 'Connection error. Please try again.'
    }
    isLoading.value = false
    isStreaming.value = false
    eventSource.close()
  })

  eventSource.onerror = () => {
    if (!lessonComplete.value && !lessonText.value) {
      errorMessage.value = 'Connection lost. Please retry.'
      isLoading.value = false
      isStreaming.value = false
    }
  }
}

async function takeTest() {
  // Ensure we have a session
  if (!sessionStore.currentSession) {
    await sessionStore.startSession()
  }
  const sessionId = sessionStore.currentSession._id
  router.push({
    name: 'test',
    params: { sessionId },
    query: { article_ids: articleId.value },
  })
}

async function markAndContinue() {
  if (sessionStore.currentSession) {
    const durationMins = sessionStartTime.value
      ? (Date.now() - sessionStartTime.value) / 60000
      : 0
    await sessionStore.endSession([articleId.value], durationMins)
  }
  router.push({ name: 'home' })
}

onMounted(async () => {
  await loadArticleProgress()
  startLesson()

  // Ensure session is active
  if (!sessionStore.currentSession && !revisionMode.value) {
    await sessionStore.startSession()
  }
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
})
</script>

<style scoped>
.learn-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 860px;
}

/* Top bar */
.learn-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.back-btn {
  font-size: 0.85rem;
}

/* Article header */
.article-header {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-6);
}

.article-part {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-accent);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: var(--space-2);
}

.article-title-main {
  font-size: 1.8rem;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: var(--space-3);
}

.article-meta-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.article-id-chip {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 600;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  color: var(--color-accent);
  padding: 0.25em 0.75em;
  border-radius: var(--radius-full);
}

/* Lesson */
.lesson-container {
  min-height: 300px;
}

/* Action bar */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  background: linear-gradient(135deg, #0d1a35, #162035);
  border-color: var(--color-accent-dim);
  position: sticky;
  bottom: var(--space-4);
  flex-wrap: wrap;
}

.action-bar-right {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

/* Slide-up transition */
.slide-up-enter-active {
  animation: slideUp 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
}
</style>
