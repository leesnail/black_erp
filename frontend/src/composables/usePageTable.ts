import { ref, reactive, watch } from 'vue'

export interface PageQuery {
  page: number
  page_size: number
  [key: string]: unknown
}

export function usePageTable<T>(
  fetcher: (params: PageQuery) => Promise<{ items: T[]; total: number }>,
  defaults: Record<string, unknown> = {},
) {
  const query = reactive<PageQuery>({ page: 1, page_size: 20, ...defaults })
  const rows = ref<T[]>([]) as { value: T[] }
  const total = ref(0)
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const res = await fetcher(query)
      rows.value = res.items
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  function search() {
    query.page = 1
    return load()
  }

  function reset() {
    Object.keys(query).forEach((k) => {
      if (k !== 'page' && k !== 'page_size') delete query[k]
    })
    Object.assign(query, defaults, { page: 1 })
    return load()
  }

  watch(
    () => [query.page, query.page_size],
    () => load(),
  )

  return { query, rows, total, loading, search, reset, refresh: load }
}
