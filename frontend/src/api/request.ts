import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

export interface ApiError {
  detail: string
  code?: number
}

const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 60_000,
})

request.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.csrfToken && !['get', 'head', 'options'].includes((config.method || 'get').toLowerCase())) {
    config.headers['X-CSRF-Token'] = auth.csrfToken
  }
  return config
})

let redirecting = false

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status: number | undefined = error.response?.status
    const detail: string = error.response?.data?.detail || '请求失败'

    if (status === 401 && !redirecting) {
      redirecting = true
      useAuthStore().clear()
      ElMessage.warning('登录已过期，请重新登录')
      const current = router.currentRoute.value.fullPath
      router
        .replace({ path: '/login', query: { redirect: current } })
        .finally(() => {
          redirecting = false
        })
    } else if (status !== 401) {
      ElMessage.error(detail)
    }
    return Promise.reject(new Error(detail))
  },
)

export function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return request.get(url, config) as unknown as Promise<T>
}

export function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request.post(url, data, config) as unknown as Promise<T>
}

export function patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request.patch(url, data, config) as unknown as Promise<T>
}

export default request
