import { defineStore } from 'pinia'
import { ref } from 'vue'
import { calcApi, type Batch, type Preview } from '@/api/calc'

export type CalcPhase = 'idle' | 'preview' | 'running' | 'success' | 'failed'

export const useCalcStore = defineStore('calc', () => {
  const phase = ref<CalcPhase>('idle')
  const batchId = ref<number | null>(null)
  const preview = ref<Preview | null>(null)
  const batch = ref<Batch | null>(null)

  let timer: number | null = null
  let slowCount = 0

  function reset() {
    stopPoll()
    phase.value = 'idle'
    batchId.value = null
    preview.value = null
    batch.value = null
  }

  async function upload(file: File, shopId?: number, period?: string) {
    const res = await calcApi.upload(file, shopId, period)
    batchId.value = res.batch_id
    preview.value = res.preview
    phase.value = 'preview'
    return res
  }

  function startPoll() {
    if (timer) return
    phase.value = 'running'
    slowCount = 0
    const tick = async () => {
      if (!batchId.value) return
      try {
        const b = await calcApi.getBatch(batchId.value)
        batch.value = b
        if (b.status === 'success') {
          phase.value = 'success'
          stopPoll()
          return
        }
        if (b.status === 'failed') {
          phase.value = 'failed'
          stopPoll()
          return
        }
      } catch {
        /* 网络抖动继续轮询 */
      }
      slowCount++
      const ms = slowCount > 3 ? 5000 : 2000
      timer = window.setTimeout(tick, ms)
    }
    timer = window.setTimeout(tick, 800)
  }

  function stopPoll() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  return { phase, batchId, preview, batch, reset, upload, startPoll, stopPoll }
})
