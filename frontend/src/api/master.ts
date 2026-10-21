import { get, post, patch } from './request'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Spec {
  id: number
  spec_code: string
  product_name: string
  spec_name: string
  supplier_id: number
  status: string
  price: string | null
  updated_at?: string
}

export interface SpecPickerItem {
  spec_id: number
  spec_code: string
  product_name: string
  spec_name: string
  price: string | null
}

export interface Supplier {
  id: number
  name: string
  wechat_group?: string
  contact_name?: string
  contact_phone?: string
  products?: string
  remark?: string
  status: string
}

export interface ShopProduct {
  id: number
  shop_id: number
  shop_name: string
  title_keyword: string
  link_id?: string
  spec_id: number
  spec_code: string
  spec_name: string
  sale_price: string
  status: string
}

export const masterApi = {
  // suppliers
  listSuppliers(q?: string) {
    return get<Supplier[]>('/master/suppliers', { params: { q } })
  },
  createSupplier(data: Partial<Supplier>) {
    return post<Supplier>('/master/suppliers', data)
  },
  updateSupplier(id: number, data: Partial<Supplier>) {
    return patch<Supplier>(`/master/suppliers/${id}`, data)
  },
  // specs
  listSpecs(params: Record<string, unknown>) {
    return get<Page<Spec>>('/master/specs', { params })
  },
  createSpec(data: Record<string, unknown>) {
    return post<Spec>('/master/specs', data)
  },
  updateSpec(id: number, data: Record<string, unknown>) {
    return patch<Spec>(`/master/specs/${id}`, data)
  },
  updatePrice(id: number, price: string) {
    return post(`/master/specs/${id}/price`, null, { params: { price } })
  },
  priceHistory(id: number) {
    return get<Array<{ id: number; price: string; effective_at: string }>>(`/master/specs/${id}/price-history`)
  },
  disableSpec(id: number) {
    return post(`/master/specs/${id}/disable`)
  },
  specPicker(q?: string) {
    return get<SpecPickerItem[]>('/master/spec-picker', { params: { q, limit: 50 } })
  },
  // shop products
  listShopProducts(params: Record<string, unknown>) {
    return get<Page<ShopProduct>>('/master/shop-products', { params })
  },
  createShopProduct(data: Record<string, unknown>) {
    return post<ShopProduct>('/master/shop-products', data)
  },
  toggleShopProduct(id: number, status: string) {
    return patch(`/master/shop-products/${id}/status`, null, { params: { status } })
  },
  // shops / roi / region
  listShops() {
    return get<Array<{ id: number; name: string }>>('/master/shops')
  },
  listRoi(shopId?: number) {
    return get('/master/roi-records', { params: { shop_id: shopId } })
  },
  createRoi(data: Record<string, unknown>) {
    return post('/master/roi-records', data)
  },
  listRegionRules() {
    return get('/master/region-rules')
  },
}
