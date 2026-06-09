<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="app-sidebar" :class="{ open: sidebarOpen }">
      <!-- Logo -->
      <div class="sidebar-logo">
        <div class="logo-icon">⚖️</div>
        <div class="logo-text">
          <div class="logo-title">ConstitutionAI</div>
          <div class="logo-subtitle">UPSC Prep</div>
        </div>
      </div>

      <!-- Nav links -->
      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: $route.path === item.to || ($route.path !== '/' && item.to !== '/' && $route.path.startsWith(item.to)) }"
          @click="sidebarOpen = false"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
        </router-link>
      </nav>

      <!-- Sidebar footer: health status -->
      <div class="sidebar-footer">
        <div class="health-status" :class="healthClass">
          <span class="health-dot"></span>
          <span class="health-label">{{ healthLabel }}</span>
        </div>
        <div class="text-xs text-muted mt-1">
          {{ health?.chromadb_documents || 0 }} articles indexed
        </div>
      </div>
    </aside>

    <!-- Mobile overlay -->
    <div
      v-if="sidebarOpen"
      class="sidebar-overlay"
      @click="sidebarOpen = false"
    ></div>

    <!-- Main content -->
    <main class="app-main">
      <!-- Mobile top bar -->
      <div class="mobile-topbar">
        <button class="hamburger" @click="sidebarOpen = !sidebarOpen" id="menu-toggle">
          ☰
        </button>
        <span class="mobile-title">ConstitutionAI</span>
        <div></div>
      </div>

      <!-- Page transitions -->
      <router-view v-slot="{ Component, route }">
        <Transition name="page" mode="out-in">
          <component :is="Component" :key="route.path" />
        </Transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useProgressStore } from '@/stores/progress.js'
import axios from 'axios'

const progressStore = useProgressStore()
const sidebarOpen = ref(false)
const health = ref(null)

const needsReviewCount = computed(() => progressStore.needsReview.length)

const navItems = computed(() => [
  { to: '/', icon: '🏠', label: 'Dashboard' },
  { to: '/revision', icon: '📖', label: 'Browse Articles' },
  { to: '/progress', icon: '📊', label: 'My Progress' },
  ...(needsReviewCount.value > 0 ? [{
    to: '/revision?status=review',
    icon: '🔄',
    label: 'Due for Review',
    badge: needsReviewCount.value
  }] : []),
])

const healthClass = computed(() => {
  if (!health.value) return 'health-unknown'
  if (health.value.mongodb === 'connected' && health.value.chromadb_documents > 0) return 'health-good'
  if (health.value.mongodb === 'connected') return 'health-partial'
  return 'health-bad'
})

const healthLabel = computed(() => {
  if (!health.value) return 'Checking...'
  if (health.value.mongodb !== 'connected') return 'MongoDB offline'
  if (health.value.chromadb_documents === 0) return 'Setup needed'
  return 'All systems go'
})

async function checkHealth() {
  try {
    const { data } = await axios.get('/api/health')
    health.value = data
  } catch {
    health.value = { mongodb: 'disconnected', chromadb_documents: 0 }
  }
}

onMounted(async () => {
  await checkHealth()
  // Fetch progress for badge counts
  try {
    await progressStore.fetchProgress()
  } catch {}
})
</script>

<style scoped>
/* Sidebar */
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.logo-icon {
  font-size: 1.8rem;
  line-height: 1;
}

.logo-title {
  font-size: 1rem;
  font-weight: 800;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}

.logo-subtitle {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

/* Nav */
.sidebar-nav {
  padding: var(--space-4) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  border-radius: var(--radius-lg);
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  font-weight: 500;
  text-decoration: none;
  transition: all var(--transition-fast);
  position: relative;
}

.nav-item:hover {
  background: var(--color-bg-elevated);
  color: var(--color-text-primary);
}

.nav-item.active {
  background: var(--color-accent-dim);
  color: var(--color-accent);
  font-weight: 600;
  border: 1px solid var(--color-border);
}

.nav-item.active .nav-icon {
  filter: none;
}

.nav-icon {
  font-size: 1.1rem;
  width: 22px;
  flex-shrink: 0;
}

.nav-label { flex: 1; }

.nav-badge {
  background: var(--color-warning);
  color: #000;
  font-size: 0.65rem;
  font-weight: 800;
  padding: 0.15em 0.5em;
  border-radius: var(--radius-full);
  min-width: 18px;
  text-align: center;
}

/* Sidebar footer */
.sidebar-footer {
  margin-top: auto;
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--color-border);
}

.health-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.78rem;
  font-weight: 600;
}

.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.health-good .health-dot {
  background: var(--color-success);
  box-shadow: 0 0 6px var(--color-success);
  animation: pulse-health 2s infinite;
}
.health-good .health-label { color: var(--color-success); }

.health-partial .health-dot { background: var(--color-warning); }
.health-partial .health-label { color: var(--color-warning); }

.health-bad .health-dot { background: var(--color-danger); }
.health-bad .health-label { color: var(--color-danger); }

.health-unknown .health-dot { background: var(--color-text-muted); }
.health-unknown .health-label { color: var(--color-text-muted); }

@keyframes pulse-health {
  0%, 100% { box-shadow: 0 0 4px var(--color-success); }
  50% { box-shadow: 0 0 12px var(--color-success); }
}

/* Mobile overlay */
.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 99;
  backdrop-filter: blur(2px);
}

/* Mobile top bar */
.mobile-topbar {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 50;
}

.hamburger {
  background: none;
  border: none;
  color: var(--color-text-primary);
  font-size: 1.4rem;
  cursor: pointer;
  padding: var(--space-1);
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}

.hamburger:hover {
  background: var(--color-bg-elevated);
}

.mobile-title {
  font-weight: 800;
  font-size: 1rem;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

@media (max-width: 768px) {
  .mobile-topbar { display: flex; }
}
</style>
