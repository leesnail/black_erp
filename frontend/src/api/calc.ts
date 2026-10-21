import { get, post } from './request'
import type { Page } from './master'

export interface Preview {
  total: number
  no_ship_skip: number
  aftersale: number
  qty_invalid: number
  est_unmatched: number
  shop_name: string
  errors: Array<{ row: number; reason: string }>
}

export interface Batch {
  id: number
  shop_id: number
  shop_name: string
  period: string
  source_filename: string
  status: string
  version: number
  stats: Record<string, unknown>
  err_msg?: string
  created_at: string
}

export interface OrderLine {
  id: number
  order_no: string
  raw_product: string
  title?: string
  spec_text?: string
  qty: number
  province?: string
  spec_id?: number
  spec_code?: string
  price_snapshot?: string | null
  surcharge: string
  unit_cost?: string | null
  line_cost?: string | null
  income: string
  matched: string
  aftersale_status?: string
  ignored: boolean
  recommend?: Array<Record<string, unknown>>
}

export const calcApi = {
  upload(file: File, shopId?: number, period?: string) {
    const fd = new FormData()
    fd.append('file', file)
    if (shopId) fd.append('shop_id', String(shopId))
    if (period) fd.append('period', period)
    return post<{ batch_id: number; preview: Preview; status: string }>('/calc/batches', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  listBatches(params?: Record<string, unknown>) {
    return get<Batch[]>('/calc/batches', { params })
  },
  getBatch(id: number) {
    return get<Batch>(`/calc/batches/${id}`)
  },
  summary(id: number) {
    return get<Record<string, unknown>>(`/calc/batches/${id}/summary`)
  },
  lines(id: number, params: Record<string, unknown>) {
    return get<Page<OrderLine>>(`/calc/batches/${id}/lines`, { params })
  },
  unmatched(id: number) {
    return get<OrderLine[]>(`/calc/batches/${id}/unmatched`)
  },
  manualMatch(id: number, lineIds: number[], specId: number) {
    return post(`/calc/batches/${id}/manual-match`, { line_ids: lineIds, spec_id: specId })
  },
  ignore(id: number, lineIds: number[], reason: string) {
    return post(`/calc/batches/${id}/ignore`, { line_ids: lineIds, reason })
  },
  recalc(id: number) {
    return post<Batch>(`/calc/batches/${id}/recalc`)
  },
  unmatchedTotal() {
    return get<{ total: number }>('/calc/unmatched-total')
  },
}
