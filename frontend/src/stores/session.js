import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API = '/api'

export const useSessionStore = defineStore('session', () => {
  // State
  const currentSession = ref(null)
  const sessionPlan = ref(null)
  const currentArticleId = ref(null)
  const isLoading = ref(false)
  const error = ref(null)
  const activeProvider = ref('groq')

  // Getters
  const hasActiveSession = computed(() => !!currentSession.value)
  const nextArticle = computed(() => sessionPlan.value?.next_article || null)
  const isRevisionMode = computed(() => sessionPlan.value?.is_revision || false)

  // Actions

  async function loadPlan() {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await axios.get(`${API}/session/plan`)
      sessionPlan.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function startSession() {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await axios.post(`${API}/session/start`)
      currentSession.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function endSession(articlesCovered = [], durationMins = 0, summary = '') {
    if (!currentSession.value) return
    try {
      await axios.post(`${API}/session/end`, {
        session_id: currentSession.value._id,
        articles_covered: articlesCovered,
        duration_mins: durationMins,
        provider_used: activeProvider.value,
        session_summary: summary,
      })
      currentSession.value = null
      currentArticleId.value = null
      // Refresh plan
      await loadPlan()
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function markArticleTaught(articleId) {
    if (!currentSession.value) return
    try {
      await axios.post(`${API}/articles/mark-taught`, {
        article_id: articleId,
        session_id: currentSession.value._id,
      })
    } catch (err) {
      console.error('Failed to mark article as taught:', err)
    }
  }

  async function updateScore(articleId, score) {
    try {
      await axios.post(`${API}/articles/score`, {
        article_id: articleId,
        score: score,
      })
    } catch (err) {
      console.error('Failed to update score:', err)
    }
  }

  function setCurrentArticle(articleId) {
    currentArticleId.value = articleId
  }

  function setProvider(provider) {
    activeProvider.value = provider
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    currentSession,
    sessionPlan,
    currentArticleId,
    isLoading,
    error,
    activeProvider,
    // Getters
    hasActiveSession,
    nextArticle,
    isRevisionMode,
    // Actions
    loadPlan,
    startSession,
    endSession,
    markArticleTaught,
    updateScore,
    setCurrentArticle,
    setProvider,
    clearError,
  }
})
