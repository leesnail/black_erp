import { get, post, patch } from './request'
import type { Page } from './master'

export const serviceApi = {
  listAftersales(params: Record<string, unknown>) {
    return get<Page<Record<string, unknown>>>('/service/aftersales', { params })
  },
  createAftersale(data: Record<string, unknown>) {
    return post('/service/aftersales', data)
  },
  updateAftersale(id: number, data: Record<string, unknown>) {
    return patch(`/service/aftersales/${id}`, data)
  },
  listInvoices(params: Record<string, unknown>) {
    return get<Page<Record<string, unknown>>>('/service/invoices', { params })
  },
  createInvoice(data: Record<string, unknown>) {
    return post('/service/invoices', data)
  },
  uploadInvoice(id: number, keys: string[]) {
    return post(`/service/invoices/${id}/upload`, { files: keys })
  },
  reminders(status?: string) {
    return get('/service/reminders', { params: { status } })
  },
  reminderCount() {
    return get<{ total: number }>('/service/reminder-count')
  },
}

export const reportApi = {
  cockpit(params?: Record<string, unknown>) {
    return get<Record<string, unknown>>('/report/cockpit/overview', { params })
  },
  dailyReports(params?: Record<string, unknown>) {
    return get('/report/daily-reports', { params })
  },
}
