import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/Login.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/pages/Dashboard.vue') },
      { path: 'cases', name: 'Cases', component: () => import('@/pages/Cases.vue') },
      { path: 'cases/:id', name: 'CaseDetail', component: () => import('@/pages/CaseDetail.vue') },
      { path: 'polls', name: 'Polls', component: () => import('@/pages/Polls.vue') },
      { path: 'polls/:id', name: 'PollDetail', component: () => import('@/pages/PollDetail.vue') },
      { path: 'audit', name: 'Audit', component: () => import('@/pages/Audit.vue') },
      { path: 'users', name: 'Users', component: () => import('@/pages/Users.vue'), meta: { adminOnly: true } },
      { path: 'settings', name: 'Settings', component: () => import('@/pages/Settings.vue') },
    ]
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    next('/login')
  } else if (to.meta.adminOnly && !auth.isAdmin) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
