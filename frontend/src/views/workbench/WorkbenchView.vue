<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">工作台</div>
    </div>

    <div class="stat-cards">
      <div v-for="card in todoCards" :key="card.label" class="stat-card" @click="card.to && $router.push(card.to)">
        <div class="label">{{ card.label }}</div>
        <div class="value" :class="{ accent: card.accent }">{{ card.value }}</div>
        <div class="link">{{ card.hint }} →</div>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>快捷入口</template>
          <div class="quick-links">
            <el-button v-for="q in quickLinks" :key="q.to" :type="q.type" size="large" @click="$router.push(q.to)">
              {{ q.label }}
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>最近计算批次</template>
          <el-table :data="recentBatches" size="small" v-loading="loadingBatches">
            <el-table-column prop="id" label="#" width="60" />
            <el-table-column prop="shop_name" label="店铺" width="70" />
            <el-table-column prop="period" label="期间" width="90" />
            <el-table-column label="利润" align="right">
              <template #default="{ row }">{{ fmtMoney((row.stats as any)?.profit) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'success' ? 'success' : 'info'">
                  {{ row.status === 'success' ? '成功' : row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { calcApi } from '@/api/calc'
import { serviceApi } from '@/api/service'
import { reportApi } from '@/api/service'
import { useAuthStore } from '@/stores/auth'
import { fmtMoney } from '@/utils/format'

const auth = useAuthStore()
const loadingBatches = ref(false)
const recentBatches = ref<any[]>([])
const invoiceCount = ref(0)
const unmatchedTotal = ref(0)
const cockpit = ref<Record<string, any> | null>(null)

const todoCards = computed(() => {
  const cards: Array<{ label: string; value: string; hint: string; to?: string; accent?: boolean }> = []
  if (auth.has('service.list')) {
    cards.push({ label: '发票提醒', value: String(invoiceCount.value), hint: '待回传发票', to: '/service/invoices' })
  }
  if (auth.has('calc.list')) {
    cards.push({ label: '未匹配订单', value: String(unmatchedTotal.value), hint: '待处理', to: '/calc/batches', accent: unmatchedTotal.value > 0 })
  }
  if (auth.has('report.list')) {
    cards.push({
      label: '当前利润',
      value: fmtMoney(cockpit.value?.profit_total || '0'),
      hint: '查看驾驶舱',
      to: '/report/cockpit',
      accent: true,
    })
  }
  if (auth.has('master.spec.list')) {
    cards.push({ label: '成本表', value: '查看', hint: '规格主数据', to: '/master/specs' })
  }
  if (cards.length === 0) {
    cards.push({ label: '欢迎', value: 'BLACK ERP', hint: '暂无待办' })
  }
  return cards.slice(0, 4)
})

const quickLinks = computed(() => {
  const links: Array<{ label: string; to: string; type: 'primary' | 'default' | 'success' }> = []
  if (auth.has('calc.upload')) links.push({ label: '上传订单计算', to: '/calc/upload', type: 'primary' })
  if (auth.has('service.create')) links.push({ label: '登记售后', to: '/service/aftersale', type: 'success' })
  if (auth.has('master.shop_product.create')) links.push({ label: '产品登记', to: '/master/shop-products', type: 'default' })
  if (auth.has('master.spec.create')) links.push({ label: '新增规格', to: '/master/specs', type: 'default' })
  if (!links.length) links.push({ label: '经营驾驶舱', to: '/report/cockpit', type: 'primary' })
  return links
})

onMounted(async () => {
  loadingBatches.value = true
  try {
    const [b, ic, ut] = await Promise.allSettled([
      calcApi.listBatches({ limit: 5 }),
      serviceApi.reminderCount(),
      calcApi.unmatchedTotal(),
    ])
    if (b.status === 'fulfilled') recentBatches.value = b.value
    if (ic.status === 'fulfilled') invoiceCount.value = ic.value.total
    if (ut.status === 'fulfilled') unmatchedTotal.value = ut.value.total
    if (auth.has('report.list')) {
      try {
        cockpit.value = await reportApi.cockpit()
      } catch {
        /* ignore */
      }
    }
  } finally {
    loadingBatches.value = false
  }
})
</script>

<style scoped>
.stat-card {
  cursor: pointer;
  transition: box-shadow 0.15s;
}

.stat-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.link {
  margin-top: 6px;
  font-size: 12px;
  color: var(--erp-text-sub);
}

.quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
