import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API = '/api'

export const useProgressStore = defineStore('progress', () => {
  // State
  const summary = ref(null)
  const articles = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const totalTaught = computed(() => summary.value?.total_articles_taught || 0)
  const totalAvailable = computed(() => summary.value?.total_articles_available || 0)
  const percentComplete = computed(() => summary.value?.percent_complete || 0)
  const averageScore = computed(() => summary.value?.average_score || 0)
  const streak = computed(() => summary.value?.current_streak_days || 0)
  const weakTopics = computed(() => summary.value?.weak_topics || [])
  const needsReview = computed(() => summary.value?.needs_review || [])
  const recentSessions = computed(() => summary.value?.recent_sessions || [])

  // Filters for articles list
  const taughtArticles = computed(() =>
    articles.value.filter(a => a.first_taught_date)
  )
  const untaughtArticles = computed(() =>
    articles.value.filter(a => !a.first_taught_date)
  )
  const articlesNeedingReview = computed(() =>
    articles.value.filter(a => a.needs_review)
  )

  // Actions

  async function fetchProgress() {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await axios.get(`${API}/progress`)
      summary.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchArticles() {
    try {
      const { data } = await axios.get(`${API}/articles`)
      articles.value = data.articles || []
      return articles.value
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function fetchAll() {
    await Promise.all([fetchProgress(), fetchArticles()])
  }

  function getArticleById(articleId) {
    return articles.value.find(a => a.article_id === articleId) || null
  }

  function getScoreClass(score) {
    if (score >= 80) return 'score-high'
    if (score >= 60) return 'score-medium'
    return 'score-low'
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    summary,
    articles,
    isLoading,
    error,
    // Getters
    totalTaught,
    totalAvailable,
    percentComplete,
    averageScore,
    streak,
    weakTopics,
    needsReview,
    recentSessions,
    taughtArticles,
    untaughtArticles,
    articlesNeedingReview,
    // Actions
    fetchProgress,
    fetchArticles,
    fetchAll,
    getArticleById,
    getScoreClass,
    clearError,
  }
})
