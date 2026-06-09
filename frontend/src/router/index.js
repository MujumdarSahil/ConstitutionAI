import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { title: 'Dashboard — ConstitutionAI' }
    },
    {
      path: '/learn/:articleId',
      name: 'learn',
      component: () => import('../views/LearnView.vue'),
      meta: { title: 'Learn — ConstitutionAI' }
    },
    {
      path: '/test/:sessionId',
      name: 'test',
      component: () => import('../views/TestView.vue'),
      meta: { title: 'Quiz — ConstitutionAI' }
    },
    {
      path: '/progress',
      name: 'progress',
      component: () => import('../views/ProgressView.vue'),
      meta: { title: 'Progress — ConstitutionAI' }
    },
    {
      path: '/revision',
      name: 'revision',
      component: () => import('../views/RevisionView.vue'),
      meta: { title: 'Revision — ConstitutionAI' }
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  }
})

// Update document title on navigation
router.afterEach((to) => {
  document.title = to.meta.title || 'ConstitutionAI'
})

export default router
