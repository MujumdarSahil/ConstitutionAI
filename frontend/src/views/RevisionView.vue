<template>
  <div class="revision-view page-container">
    <!-- Header -->
    <div class="page-header fade-in">
      <h1>Article Browser</h1>
      <p class="text-muted">All 400+ articles, preamble, and schedules. Click any to jump directly to it.</p>
    </div>

    <!-- Search and filter bar -->
    <div class="filter-bar card fade-in">
      <div class="search-wrapper">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by article number, title, or topic..."
          class="search-input"
          id="article-search"
        />
        <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">✕</button>
      </div>

      <div class="filters">
        <select v-model="partFilter" class="filter-select" id="part-filter">
          <option value="">All Parts</option>
          <option v-for="part in availableParts" :key="part" :value="part">{{ part }}</option>
        </select>
        <select v-model="statusFilter" class="filter-select" id="status-filter">
          <option value="">All Status</option>
          <option value="taught">Studied</option>
          <option value="untaught">Not Studied</option>
          <option value="review">Needs Review</option>
          <option value="weak">Score &lt; 60</option>
        </select>
        <button class="btn btn-ghost btn-sm" @click="clearFilters">Clear Filters</button>
      </div>
    </div>

    <!-- Results count -->
    <div class="results-meta fade-in">
      <span class="text-muted text-sm">
        Showing <strong>{{ filteredArticles.length }}</strong> of {{ articles.length }} articles
      </span>
      <div class="sort-options">
        <button
          v-for="opt in sortOptions"
          :key="opt.value"
          class="sort-btn"
          :class="{ active: sortBy === opt.value }"
          @click="sortBy = opt.value"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="loading-grid stagger">
      <div v-for="i in 9" :key="i" class="skeleton" style="height: 120px; border-radius: 12px;"></div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!filteredArticles.length" class="empty-state fade-in">
      <div class="empty-icon">🔎</div>
      <h3>No articles found</h3>
      <p class="text-muted">Try different search terms or clear the filters.</p>
      <button class="btn btn-secondary mt-4" @click="clearFilters">Clear Filters</button>
    </div>

    <!-- Article grid -->
    <div v-else class="articles-grid stagger">
      <ArticleCard
        v-for="article in paginatedArticles"
        :key="article.article_id"
        :article="article"
        @click="jumpTo(article.article_id)"
      />
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="pagination fade-in">
      <button
        class="btn btn-ghost btn-sm"
        :disabled="currentPage === 1"
        @click="currentPage--"
      >
        ← Prev
      </button>
      <div class="page-numbers">
        <button
          v-for="page in visiblePages"
          :key="page"
          class="page-btn"
          :class="{ active: page === currentPage, ellipsis: page === '...' }"
          :disabled="page === '...'"
          @click="page !== '...' && (currentPage = page)"
        >
          {{ page }}
        </button>
      </div>
      <button
        class="btn btn-ghost btn-sm"
        :disabled="currentPage === totalPages"
        @click="currentPage++"
      >
        Next →
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useProgressStore } from '@/stores/progress.js'
import ArticleCard from '@/components/ArticleCard.vue'

const router = useRouter()
const progressStore = useProgressStore()

const searchQuery = ref('')
const partFilter = ref('')
const statusFilter = ref('')
const sortBy = ref('number')
const currentPage = ref(1)
const PAGE_SIZE = 24

const articles = computed(() => progressStore.articles)
const isLoading = computed(() => progressStore.isLoading)

const sortOptions = [
  { value: 'number', label: 'Article #' },
  { value: 'score', label: 'Score' },
  { value: 'date', label: 'Recently Studied' },
]

const availableParts = computed(() => {
  const parts = [...new Set(articles.value.map(a => a.part).filter(Boolean))]
  return parts.sort()
})

const filteredArticles = computed(() => {
  let list = [...articles.value]

  // Search
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(a =>
      a.article_id?.toLowerCase().includes(q) ||
      a.title?.toLowerCase().includes(q) ||
      a.part?.toLowerCase().includes(q)
    )
  }

  // Part filter
  if (partFilter.value) {
    list = list.filter(a => a.part === partFilter.value)
  }

  // Status filter
  if (statusFilter.value === 'taught') {
    list = list.filter(a => a.first_taught_date)
  } else if (statusFilter.value === 'untaught') {
    list = list.filter(a => !a.first_taught_date)
  } else if (statusFilter.value === 'review') {
    list = list.filter(a => a.needs_review)
  } else if (statusFilter.value === 'weak') {
    list = list.filter(a => a.last_score > 0 && a.last_score < 60)
  }

  // Sort
  if (sortBy.value === 'number') {
    list.sort((a, b) => a.article_number - b.article_number)
  } else if (sortBy.value === 'score') {
    list.sort((a, b) => (b.last_score || 0) - (a.last_score || 0))
  } else if (sortBy.value === 'date') {
    list.sort((a, b) => {
      const da = a.first_taught_date ? new Date(a.first_taught_date) : new Date(0)
      const db = b.first_taught_date ? new Date(b.first_taught_date) : new Date(0)
      return db - da
    })
  }

  return list
})

const totalPages = computed(() => Math.ceil(filteredArticles.value.length / PAGE_SIZE))

const paginatedArticles = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredArticles.value.slice(start, start + PAGE_SIZE)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)

  const pages = []
  if (current <= 4) {
    pages.push(1, 2, 3, 4, 5, '...', total)
  } else if (current >= total - 3) {
    pages.push(1, '...', total - 4, total - 3, total - 2, total - 1, total)
  } else {
    pages.push(1, '...', current - 1, current, current + 1, '...', total)
  }
  return pages
})

// Reset page when filters change
watch([searchQuery, partFilter, statusFilter, sortBy], () => {
  currentPage.value = 1
})

function clearFilters() {
  searchQuery.value = ''
  partFilter.value = ''
  statusFilter.value = ''
  sortBy.value = 'number'
  currentPage.value = 1
}

function jumpTo(articleId) {
  router.push({
    name: 'learn',
    params: { articleId },
    query: { revision: 'true' },
  })
}

onMounted(async () => {
  if (!articles.value.length) {
    await progressStore.fetchArticles()
  }
})
</script>

<style scoped>
.revision-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.page-header h1 {
  font-size: 2rem;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Filter bar */
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: var(--space-3);
  font-size: 1rem;
  pointer-events: none;
  z-index: 1;
}

.search-input {
  padding-left: 2.5rem;
  padding-right: 2.5rem;
  font-size: 0.95rem;
  height: 44px;
}

.clear-btn {
  position: absolute;
  right: var(--space-3);
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0;
  line-height: 1;
  transition: color var(--transition-fast);
}
.clear-btn:hover { color: var(--color-text-primary); }

.filters {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  align-items: center;
}

.filter-select {
  width: auto;
  min-width: 140px;
  height: 36px;
  padding: 0 var(--space-3);
  font-size: 0.85rem;
}

/* Results meta */
.results-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.sort-options {
  display: flex;
  gap: var(--space-2);
}

.sort-btn {
  padding: 0.3em 0.8em;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.sort-btn:hover, .sort-btn.active {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-dim);
}

/* Loading grid */
.loading-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-16) var(--space-8);
  text-align: center;
  color: var(--color-text-muted);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: var(--space-4);
}

/* Articles grid */
.articles-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

@media (max-width: 900px) {
  .articles-grid { grid-template-columns: repeat(2, 1fr); }
  .loading-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .articles-grid { grid-template-columns: 1fr; }
  .loading-grid { grid-template-columns: 1fr; }
}

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.page-numbers {
  display: flex;
  gap: var(--space-1);
}

.page-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.page-btn.active {
  background: var(--gradient-accent);
  border-color: transparent;
  color: white;
}

.page-btn.ellipsis {
  cursor: default;
  border: none;
  color: var(--color-text-muted);
}
</style>
