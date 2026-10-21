export interface MenuNode {
  path: string
  title: string
  perm?: string | null
  icon?: string
  children?: MenuNode[]
}

/** 菜单树：perm 对齐后端权限码；null 表示登录即可 */
export const MENU_TREE: MenuNode[] = [
  { path: '/workbench', title: '工作台', perm: 'workbench', icon: 'Home' },
  {
    path: '/service',
    title: '客服工作台',
    perm: 'service',
    icon: 'Headset',
    children: [
      { path: 'aftersale', title: '售后登记', perm: 'service.list' },
      { path: 'invoices', title: '发票管理', perm: 'service.list' },
      { path: 'suppliers', title: '供应商对接', perm: 'master.supplier.list' },
    ],
  },
  {
    path: '/master',
    title: '成本报价',
    perm: 'master',
    icon: 'Goods',
    children: [
      { path: 'suppliers', title: '供应商管理', perm: 'master.supplier.list' },
      { path: 'specs', title: '规格成本表', perm: 'master.spec.list' },
      { path: 'shop-products', title: '店铺产品登记', perm: 'master.shop_product.list' },
      { path: 'roi', title: 'ROI 计算', perm: 'roi.list' },
    ],
  },
  {
    path: '/calc',
    title: '财务核算',
    perm: 'calc',
    icon: 'Calculator',
    children: [
      { path: 'upload', title: '订单上传与计算', perm: 'calc.list' },
      { path: 'batches', title: '计算批次', perm: 'calc.list' },
    ],
  },
  {
    path: '/report',
    title: '经营驾驶舱',
    perm: 'report',
    icon: 'TrendCharts',
    children: [
      { path: 'cockpit', title: '利润总览', perm: 'report.list' },
      { path: 'daily', title: '经营日报', perm: 'report.list' },
    ],
  },
  {
    path: '/admin',
    title: '系统管理',
    perm: 'admin',
    icon: 'Setting',
    children: [
      { path: 'accounts', title: '账号管理', perm: 'admin.list' },
      { path: 'roles', title: '角色权限', perm: 'admin.list' },
      { path: 'region-rules', title: '附加成本规则', perm: 'admin.list' },
      { path: 'logs', title: '操作日志', perm: 'admin.list' },
    ],
  },
]

export function filterMenu(nodes: MenuNode[], has: (code?: string | null) => boolean): MenuNode[] {
  const out: MenuNode[] = []
  for (const n of nodes) {
    if (n.children) {
      const children = filterMenu(n.children, has)
      // 父节点：自身 perm 通过，或任一子节点可见
      if (has(n.perm) || children.length > 0) {
        out.push({ ...n, children: children.length ? children : n.children })
      }
    } else if (has(n.perm)) {
      out.push(n)
    }
  }
  // 若父 perm 不通过但有可见子节点，只保留子节点可见的父
  return out.map((n) => {
    if (n.children) {
      return { ...n, children: filterMenu(n.children, has) }
    }
    return n
  }).filter((n) => !n.children || n.children.length > 0 || has(n.perm))
}
