import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    { path: '/register', component: () => import('@/views/RegisterView.vue'), meta: { public: true } },
    { path: '/', component: () => import('@/views/HomeView.vue') },
    { path: '/chat/:id', component: () => import('@/views/ChatView.vue') },
    { path: '/tasks', component: () => import('@/views/TasksView.vue') },
    { path: '/documents', component: () => import('@/views/DocumentsView.vue') },
    { path: '/assistants', component: () => import('@/views/AssistantsView.vue') },
    { path: '/assistants/new', component: () => import('@/views/AssistantEditorView.vue') },
    { path: '/tools', component: () => import('@/views/ToolsView.vue') },
    { path: '/resources', component: () => import('@/views/ResourcesView.vue') },
    { path: '/search', component: () => import('@/views/SearchView.vue') },
    { path: '/memories', component: () => import('@/views/MemoriesView.vue') },
    { path: '/settings/:section?', component: () => import('@/views/SettingsView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const hasToken = Boolean(localStorage.getItem('mlab_access_token'))
  if (!to.meta.public && !hasToken) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.meta.public && hasToken) return '/'
  return true
})

export default router
