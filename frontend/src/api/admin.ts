import { get, post, patch } from './request'
import type { Page } from './master'

export interface AccountItem {
  id: number
  account: string
  display_name: string
  role: string
  role_display: string
  status: string
  module_overrides: Record<string, unknown>
}

export interface AuditItem {
  id: number
  user_id: number | null
  account: string | null
  display_name: string | null
  module: string
  action: string
  target: string | null
  before: unknown
  after: unknown
  ip: string | null
  created_at: string | null
}

export interface RegionRuleItem {
  id: number
  name: string
  provinces: string[]
  amount: string
  unit: string
  status: string
}

export interface RolePerm {
  name: string
  display_name: string
  default_perms: string[]
}

export const adminApi = {
  // 账号
  accounts(params: Record<string, unknown>) {
    return get<Page<AccountItem>>('/admin/accounts', { params })
  },
  createAccount(data: Record<string, unknown>) {
    return post<{ id: number; account: string }>('/admin/accounts', data)
  },
  toggleAccount(id: number, status: string) {
    return patch(`/admin/accounts/${id}/status`, null, { params: { status } })
  },
  assignPerms(id: number, moduleOverrides: Record<string, unknown>) {
    return patch(`/admin/accounts/${id}/perm`, { module_overrides: moduleOverrides })
  },
  resetPassword(id: number, password: string) {
    return patch(`/admin/accounts/${id}/reset-password`, { password })
  },
  // 角色权限（只读种子矩阵）
  permMatrix() {
    return get<RolePerm[]>('/admin/perm-matrix')
  },
  // 审计
  auditLogs(params: Record<string, unknown>) {
    return get<Page<AuditItem>>('/admin/audit-logs', { params })
  },
  // 地区附加规则
  regionRules() {
    return get<RegionRuleItem[]>('/admin/region-rules')
  },
  updateRegionRule(id: number, data: Partial<RegionRuleItem>) {
    return patch(`/admin/region-rules/${id}`, data)
  },
}
