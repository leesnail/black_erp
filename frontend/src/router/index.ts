import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      { path: '', redirect: '/workbench' },
      {
        path: 'workbench',
        name: 'workbench',
        component: () => import('@/views/workbench/WorkbenchView.vue'),
        meta: { perm: 'workbench', title: '工作台' },
      },
      // 客服
      {
        path: 'service/aftersale',
        name: 'aftersale',
        component: () => import('@/views/service/AftersaleView.vue'),
        meta: { perm: 'service.list', title: '售后登记' },
      },
      {
        path: 'service/invoices',
        name: 'invoices',
        component: () => import('@/views/service/InvoiceView.vue'),
        meta: { perm: 'service.list', title: '发票管理' },
      },
      {
        path: 'service/suppliers',
        name: 'cs-suppliers',
        component: () => import('@/views/master/SupplierView.vue'),
        meta: { perm: 'master.supplier.list', title: '供应商对接' },
      },
      // 主数据
      {
        path: 'master/suppliers',
        name: 'suppliers',
        component: () => import('@/views/master/SupplierView.vue'),
        meta: { perm: 'master.supplier.list', title: '供应商管理' },
      },
      {
        path: 'master/specs',
        name: 'specs',
        component: () => import('@/views/master/SpecView.vue'),
        meta: { perm: 'master.spec.list', title: '规格成本表' },
      },
      {
        path: 'master/shop-products',
        name: 'shop-products',
        component: () => import('@/views/master/ShopProductView.vue'),
        meta: { perm: 'master.shop_product.list', title: '店铺产品登记' },
      },
      {
        path: 'master/roi',
        name: 'roi',
        component: () => import('@/views/master/RoiView.vue'),
        meta: { perm: 'roi.list', title: 'ROI 计算' },
      },
      // 财务
      {
        path: 'calc/upload',
        name: 'calc-upload',
        component: () => import('@/views/calc/CalcUploadView.vue'),
        meta: { perm: 'calc.list', title: '订单上传与计算' },
      },
      {
        path: 'calc/result/:id',
        name: 'calc-result',
        component: () => import('@/views/calc/CalcResultView.vue'),
        meta: { perm: 'calc.list', title: '计算结果' },
      },
      {
        path: 'calc/batches',
        name: 'calc-batches',
        component: () => import('@/views/calc/BatchListView.vue'),
        meta: { perm: 'calc.list', title: '计算批次' },
      },
      // 报表
      {
        path: 'report/cockpit',
        name: 'cockpit',
        component: () => import('@/views/report/CockpitView.vue'),
        meta: { perm: 'report.list', title: '经营驾驶舱' },
      },
      {
        path: 'report/daily',
        name: 'daily',
        component: () => import('@/views/report/DailyReportView.vue'),
        meta: { perm: 'report.list', title: '经营日报' },
      },
      // 系统管理
      {
        path: 'admin/accounts',
        name: 'admin-accounts',
        component: () => import('@/views/admin/AccountView.vue'),
        meta: { perm: 'admin.list', title: '账号管理' },
      },
      {
        path: 'admin/region-rules',
        name: 'admin-rules',
        component: () => import('@/views/admin/RegionRuleView.vue'),
        meta: { perm: 'admin.list', title: '附加成本规则' },
      },
      {
        path: 'admin/roles',
        name: 'admin-roles',
        component: () => import('@/views/admin/PermRoleView.vue'),
        meta: { perm: 'admin.list', title: '角色权限' },
      },
      {
        path: 'admin/logs',
        name: 'admin-logs',
        component: () => import('@/views/admin/AuditLogView.vue'),
        meta: { perm: 'admin.list', title: '操作日志' },
      },
      // 403
      {
        path: '403',
        name: 'forbidden',
        component: () => import('@/views/ForbiddenView.vue'),
        meta: { public: true },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.public) return true

  // 未登录 → 拉 me（Cookie 由浏览器带）
  if (!auth.loaded) {
    try {
      await auth.fetchMe()
    } catch {
      auth.clear()
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }
  if (!auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  const required = to.meta.perm as string | undefined
  if (required && !auth.has(required)) {
    return { path: '/403' }
  }
  return true
})

export default router
