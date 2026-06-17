import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomePage.vue')
  },
  {
    path: '/intro',
    name: 'Carousel',
    component: () => import('@/views/CarouselView.vue')
  },
  {
    path: '/toolbox',
    name: 'Toolbox',
    component: () => import('@/views/ToolboxView.vue')
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: () => import('@/views/admin/LoginView.vue')
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('@/views/admin/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/pages',
    name: 'AdminPages',
    component: () => import('@/views/admin/PagesList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/pages/new',
    name: 'AdminPageCreate',
    component: () => import('@/views/admin/PageEdit.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/pages/:id/edit',
    name: 'AdminPageEdit',
    component: () => import('@/views/admin/PageEdit.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/provinces',
    name: 'AdminProvinces',
    component: () => import('@/views/admin/ProvincesList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/provinces/:id/edit',
    name: 'AdminProvinceEdit',
    component: () => import('@/views/admin/ProvinceEdit.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/models',
    name: 'AdminModels',
    component: () => import('@/views/admin/ModelsList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/models/new',
    name: 'AdminModelCreate',
    component: () => import('@/views/admin/ModelEdit.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/models/:id/edit',
    name: 'AdminModelEdit',
    component: () => import('@/views/admin/ModelEdit.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/prompts',
    name: 'AdminPrompts',
    component: () => import('@/views/admin/PromptsList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/prompts/new',
    name: 'AdminPromptCreate',
    component: () => import('@/views/admin/PromptEdit.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/prompts/:id/edit',
    name: 'AdminPromptEdit',
    component: () => import('@/views/admin/PromptEdit.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/homepage',
    name: 'AdminHomepage',
    component: () => import('@/views/admin/HomepageConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/debug',
    name: 'Debug',
    component: () => import('@/views/DebugView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 - 后台页面需要登录
router.beforeEach(async (to, from, next) => {
  if (to.meta.requiresAuth) {
    try {
      const res = await fetch('/api/admin/check')
      const data = await res.json()
      if (data.code === 0) {
        next()
      } else {
        next('/admin/login')
      }
    } catch {
      next('/admin/login')
    }
  } else {
    next()
  }
})

export default router
