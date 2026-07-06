import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/store/auth'

// Layout wrapper — loaded lazily
const Layout = () => import('@/layout/index.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', noAuth: true },
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '工作台', icon: 'Monitor' },
      },
      {
        path: 'knowledge-base',
        name: 'KnowledgeBase',
        component: () => import('@/views/knowledge-base/index.vue'),
        meta: { title: '知识库管理', icon: 'Document' },
      },
      {
        path: 'knowledge-base/:id',
        name: 'AssetDetail',
        component: () => import('@/views/knowledge-base/AssetDetail.vue'),
        meta: { title: '资产详情', hidden: true },
      },
      {
        path: 'knowledge-base/new',
        name: 'AssetCreate',
        component: () => import('@/views/knowledge-base/AssetEditor.vue'),
        meta: { title: '新建资产', hidden: true },
      },
      {
        path: 'knowledge-base/:id/edit',
        name: 'AssetEditor',
        component: () => import('@/views/knowledge-base/AssetEditor.vue'),
        meta: { title: '编辑资产', hidden: true },
      },
      {
        path: 'content',
        name: 'Content',
        component: () => import('@/views/content/index.vue'),
        meta: { title: '内容创作', icon: 'Edit' },
      },
      {
        path: 'content/create',
        name: 'BriefCreate',
        component: () => import('@/views/content/BriefCreate.vue'),
        meta: { title: '新建创作任务', hidden: true },
      },
      {
        path: 'content/:id',
        name: 'DraftView',
        component: () => import('@/views/content/DraftView.vue'),
        meta: { title: '稿件详情', hidden: true },
      },
      {
        path: 'review',
        name: 'Review',
        component: () => import('@/views/review/index.vue'),
        meta: { title: '内容审核', icon: 'Checked' },
      },
      {
        path: 'review/:id',
        name: 'InternalReview',
        component: () => import('@/views/review/InternalReview.vue'),
        meta: { title: '审核详情', hidden: true },
      },
      {
        path: 'publish',
        name: 'Publish',
        component: () => import('@/views/publish/index.vue'),
        meta: { title: '发布管理', icon: 'Promotion' },
      },
      {
        path: 'publish/channels',
        name: 'ChannelList',
        component: () => import('@/views/publish/ChannelList.vue'),
        meta: { title: '渠道配置', hidden: true },
      },
      {
        path: 'publish/performance',
        name: 'PerformanceRecord',
        component: () => import('@/views/publish/PerformanceRecord.vue'),
        meta: { title: '效果录入', hidden: true },
      },
      // ── P1: Detection, Diagnosis, Weekly Review ──────────
      {
        path: 'detection',
        name: 'Detection',
        component: () => import('@/views/detection/index.vue'),
        meta: { title: '全域探测', icon: 'Search', permission: 'detection:read' },
      },
      {
        path: 'diagnosis',
        name: 'Diagnosis',
        component: () => import('@/views/diagnosis/index.vue'),
        meta: { title: '短板诊断', icon: 'DataAnalysis', permission: 'diagnosis:read' },
      },
      {
        path: 'weekly-review',
        name: 'WeeklyReview',
        component: () => import('@/views/weekly-review/index.vue'),
        meta: { title: '周度复盘', icon: 'TrendCharts', permission: 'review:read' },
      },
      {
        path: 'weekly-review/rules',
        name: 'GeoRules',
        component: () => import('@/views/weekly-review/Rules.vue'),
        meta: { title: 'GEO规则库', hidden: true, permission: 'rule:read' },
      },
      // ── P2: Monitoring ─────────────────────────────────
      {
        path: 'monitor',
        name: 'Monitor',
        component: () => import('@/views/monitor/index.vue'),
        meta: { title: '系统监控', icon: 'Monitor', permission: 'monitor:read' },
      },
      {
        path: 'templates',
        name: 'Templates',
        component: () => import('@/views/template/index.vue'),
        meta: { title: '行业模板', icon: 'Collection', permission: 'template:read' },
      },
      {
        path: 'customer',
        name: 'CustomerList',
        component: () => import('@/views/customer/index.vue'),
        meta: { title: '客户管理', icon: 'OfficeBuilding', permission: 'customer:read' },
      },
      {
        path: 'account/users',
        name: 'UserList',
        component: () => import('@/views/account/UserList.vue'),
        meta: { title: '用户管理', icon: 'User', permission: 'account:read' },
      },
      {
        path: 'account/roles',
        name: 'RoleList',
        component: () => import('@/views/account/RoleList.vue'),
        meta: { title: '角色管理', icon: 'Avatar', permission: 'account:read' },
      },
      {
        path: 'account/plans',
        name: 'BillingPlans',
        component: () => import('@/views/billing/index.vue'),
        meta: { title: '服务档位', hidden: true, permission: 'billing:read' },
      },
      {
        path: 'account/sub-accounts',
        name: 'SubAccounts',
        component: () => import('@/views/subscription/SubAccounts.vue'),
        meta: { title: '子账号管理', hidden: true, permission: 'subaccount:read' },
      },
      {
        path: 'account/payments',
        name: 'Payments',
        component: () => import('@/views/subscription/Payments.vue'),
        meta: { title: '付费记录', hidden: true, permission: 'payment:read' },
      },
      {
        path: 'account/profile',
        name: 'Profile',
        component: () => import('@/views/account/Profile.vue'),
        meta: { title: '个人设置', hidden: true },
      },
    ],
  },
  {
    path: '/demo-search',
    name: 'DemoSearch',
    component: () => import('@/views/demo/DemoSearch.vue'),
    meta: { title: '商务演示', noAuth: false },
  },
  {
    path: '/customer-dashboard',
    name: 'CustomerPortal',
    component: () => import('@/views/subscription/CustomerPortal.vue'),
    meta: { title: '客户门户', noAuth: false },
  },
  {
    path: '/paid-dashboard',
    name: 'PaidDashboard',
    component: () => import('@/views/subscription/PaidDashboard.vue'),
    meta: { title: '数据看板(智能体4+5)', noAuth: false },
  },
  {
    path: '/review/client/:token',
    name: 'ClientReview',
    component: () => import('@/views/review/ClientReview.vue'),
    meta: { title: '客户审核', noAuth: true },
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/error/403.vue'),
    meta: { title: '无权限', noAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '页面不存在', noAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard — check auth
router.beforeEach((to, _from, next) => {
  // Set page title
  document.title = `${to.meta.title || 'GEO AI'} - GEO AI 智能体运营系统`

  // Allow no-auth pages
  if (to.meta.noAuth) {
    return next()
  }

  // Check login state
  const authStore = useAuthStore()
  if (!authStore.isLoggedIn) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  // Check permission if route requires it
  if (to.meta.permission && !authStore.hasPermission(to.meta.permission as string)) {
    return next({ name: 'Forbidden' })
  }

  // Role-based access + redirect
  const role = authStore.user?.role_type || 'guest'
  const path = to.path
  // guest (no role) → force login
  if (role === 'guest') {
    authStore.clearAuth()
    return next({ name: 'Login' })
  }
  // business_operator: only demo-search, paid-dashboard, customer-dashboard, profile
  if (role === 'business_operator') {
    const allowed = ['/demo-search', '/customer-dashboard', '/paid-dashboard', '/dashboard', '/account/profile']
    if (!allowed.some(a => path.startsWith(a))) {
      return next('/demo-search')
    }
  }
  // customer_sub: only paid-dashboard, customer-dashboard
  if (role === 'customer_sub') {
    const allowed = ['/customer-dashboard', '/paid-dashboard', '/dashboard', '/account/profile']
    if (!allowed.some(a => path.startsWith(a))) {
      return next('/paid-dashboard')
    }
  }

  next()
})

export default router
