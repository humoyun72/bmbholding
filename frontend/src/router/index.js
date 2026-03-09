import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const ErrorPage = () => import('@/pages/ErrorPage.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/Login.vue'),
    meta: { public: true }
  },
  // ── Error pages ──────────────────────────────────────────
  {
    path: '/403',
    name: 'Forbidden',
    component: ErrorPage,
    props: { code: 403 },
    meta: { public: true },
  },
  {
    path: '/500',
    name: 'ServerError',
    component: ErrorPage,
    props: { code: 500 },
    meta: { public: true },
  },
  {
    path: '/502',
    name: 'BadGateway',
    component: ErrorPage,
    props: { code: 502 },
    meta: { public: true },
  },
  {
    path: '/503',
    name: 'ServiceUnavailable',
    component: ErrorPage,
    props: { code: 503 },
    meta: { public: true },
  },
  {
    path: '/429',
    name: 'TooManyRequests',
    component: ErrorPage,
    props: { code: 429 },
    meta: { public: true },
  },
  // ── Main layout ──────────────────────────────────────────
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
      { path: 'audit', name: 'Audit', component: () => import('@/pages/Audit.vue'), meta: { adminOnly: true } },
      { path: 'users', name: 'Users', component: () => import('@/pages/Users.vue'), meta: { adminOnly: true } },
      { path: 'settings', name: 'Settings', component: () => import('@/pages/Settings.vue') },
    ]
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/pages/ForgotPassword.vue'),
    meta: { public: true },
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('@/pages/ResetPassword.vue'),
    meta: { public: true },
  },
  // ── 404 catch-all — eng oxirida bo'lishi kerak ──────────
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: ErrorPage,
    props: { code: 404 },
    meta: { public: true },
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
    next('/403')
  } else {
    next()
  }
})

export default router
