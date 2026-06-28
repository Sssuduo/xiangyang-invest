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
    path: '/national',
    name: 'NationalAgriZone',
    component: () => import('@/views/NationalAgriZone.vue')
  },
  {
    path: '/promo-video',
    name: 'PromoVideo',
    component: () => import('@/views/PromoVideoView.vue')
  },
  {
    path: '/contact',
    name: 'Contact',
    component: () => import('@/views/ContactView.vue')
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
    path: '/admin/carousel',
    name: 'AdminCarousel',
    component: () => import('@/views/admin/CarouselConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/contact',
    name: 'AdminContact',
    component: () => import('@/views/admin/ContactConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/investment-dashboard',
    name: 'InvestmentDashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresBusinessAuth: true }
  },
  {
    path: '/investment',
    name: 'Investment',
    component: () => import('@/views/InvestmentView.vue'),
    meta: { requiresBusinessAuth: true }
  },
  {
    path: '/investment-activity',
    name: 'InvestmentActivity',
    component: () => import('@/views/ActivityView.vue'),
    meta: { requiresBusinessAuth: true }
  },
  {
    path: '/investment-demand',
    name: 'InvestmentDemand',
    component: () => import('@/views/DemandView.vue'),
    meta: { requiresBusinessAuth: true }
  },
  {
    path: '/investment-activity-ledger',
    name: 'InvestmentActivityLedger',
    component: () => import('@/views/ActivityLedgerView.vue'),
    meta: { requiresBusinessAuth: true }
  },
  // ---- 在建项目库 ----
  {
    path: '/construction-dashboard',
    name: 'ConstructionDashboard',
    component: () => import('@/views/ConstructionDashboardView.vue'),
    meta: { requiresBusinessAuth: true }
  },
  {
    path: '/construction',
    name: 'Construction',
    component: () => import('@/views/ConstructionView.vue'),
    meta: { requiresBusinessAuth: true }
  },
  {
    path: '/construction-progress',
    name: 'ConstructionProgress',
    component: () => import('@/views/ConstructionProgressView.vue'),
    meta: { requiresBusinessAuth: true }
  },
  {
    path: '/construction-issues',
    name: 'ConstructionIssues',
    component: () => import('@/views/ConstructionIssuesView.vue'),
    meta: { requiresBusinessAuth: true }
  },
  // ---- 管理后台 ----
  {
    path: '/admin/investment',
    name: 'AdminInvestment',
    component: () => import('@/views/admin/InvestmentList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/activity',
    name: 'AdminActivity',
    component: () => import('@/views/admin/ActivityList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/demand',
    name: 'AdminDemand',
    component: () => import('@/views/admin/DemandList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/import-config',
    name: 'AdminImportConfig',
    component: () => import('@/views/admin/ImportConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/export-config',
    name: 'AdminExportConfig',
    component: () => import('@/views/admin/ExportConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/activity-import-config',
    name: 'AdminActivityImportConfig',
    component: () => import('@/views/admin/ActivityImportConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/demand-import-config',
    name: 'AdminDemandImportConfig',
    component: () => import('@/views/admin/DemandImportConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/dict',
    name: 'AdminDict',
    component: () => import('@/views/admin/DictConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/activity-export-config',
    name: 'AdminActivityExportConfig',
    component: () => import('@/views/admin/ActivityExportConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/construction-export-config',
    name: 'AdminConstructionExportConfig',
    component: () => import('@/views/admin/ConstructionExportConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/print-templates',
    name: 'AdminPrintTemplates',
    component: () => import('@/views/admin/PrintTemplateManage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/promo-video',
    name: 'AdminPromoVideo',
    component: () => import('@/views/admin/PromoVideoManage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/business-users',
    name: 'AdminBusinessUsers',
    component: () => import('@/views/admin/BusinessUserList.vue'),
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

// 路由守卫 - 后台页面需要登录（AdminUser）
// 业务页面需要登录（BusinessUser）
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
    return
  }

  if (to.meta.requiresBusinessAuth) {
    try {
      const res = await fetch('/api/auth/check')
      const data = await res.json()
      if (data.code === 0) {
        next()
      } else {
        // 未登录业务用户 → 回到首页，可通过导航栏登录
        next('/')
      }
    } catch {
      next('/')
    }
    return
  }

  next()
})

// 设置浏览器标题
router.afterEach((to) => {
  if (to.path.startsWith('/admin')) {
    document.title = '招商平台后台管理'
  } else {
    document.title = '襄阳国家农高区招商平台'
  }
})

export default router
