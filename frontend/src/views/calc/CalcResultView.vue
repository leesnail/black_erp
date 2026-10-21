<template>
  <div class="page">
    <div class="page-header">
      <div>
        <div class="page-title">计算结果 · 批次 #{{ batchId }}</div>
        <div class="sub" v-if="summary">
          {{ summary.shop_name }} · {{ summary.period }} · v{{ summary.version }} ·
          <el-tag size="small" :type="statusType">{{ statusLabel }}</el-tag>
        </div>
      </div>
      <div>
        <el-button @click="$router.push('/calc/batches')">返回批次</el-button>
        <el-button v-if="hasRecalc" type="warning" plain @click="onRecalc">重算</el-button>
      </div>
    </div>

    <div v-if="summary" class="stat-cards">
      <div class="stat-card">
        <div class="label">商家实收</div>
        <div class="value money">{{ fmtMoney(summary.income_total) }}</div>
      </div>
      <div class="stat-card">
        <div class="label">发货单数</div>
        <div class="value">{{ fmtNum(summary.ship_count) }}</div>
      </div>
      <div class="stat-card">
        <div class="label">售后单数</div>
        <div class="value">{{ fmtNum(summary.aftersale) }}</div>
      </div>
      <div class="stat-card">
        <div class="label">采购成本</div>
        <div class="value money">{{ fmtMoney(summary.cost_total) }}</div>
      </div>
      <div class="stat-card accent">
        <div class="label">利润</div>
        <div class="value money">{{ fmtMoney(summary.profit) }}</div>
      </div>
    </div>

    <el-tabs v-model="tab" class="result-tabs">
      <el-tab-pane label="成本明细" name="lines">
        <div class="filter-bar">
          <el-select v-model="lineQuery.matched" placeholder="匹配方式" clearable style="width: 140px" @change="loadLines">
            <el-option label="自动" value="auto" />
            <el-option label="人工" value="manual" />
            <el-option label="未匹配" value="none" />
          </el-select>
        </div>
        <el-table v-loading="lineLoading" :data="lines" size="small" border height="520">
          <el-table-column prop="order_no" label="订单号" width="150" show-overflow-tooltip />
          <el-table-column prop="raw_product" label="选购商品" min-width="200" show-overflow-tooltip />
          <el-table-column prop="spec_code" label="命中编码" width="110">
            <template #default="{ row }">
              <span v-if="row.spec_code">{{ row.spec_code }}</span>
              <el-tag v-else type="danger" size="small">未匹配</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="拿货价" width="90" align="right">
            <template #default="{ row }">{{ fmtMoney(row.price_snapshot) }}</template>
          </el-table-column>
          <el-table-column label="附加" width="80" align="right">
            <template #default="{ row }">{{ fmtMoney(row.surcharge) }}</template>
          </el-table-column>
          <el-table-column prop="qty" label="数量" width="60" align="center" />
          <el-table-column label="行成本" width="100" align="right">
            <template #default="{ row }">{{ fmtMoney(row.line_cost) }}</template>
          </el-table-column>
          <el-table-column label="收入" width="100" align="right">
            <template #default="{ row }">{{ fmtMoney(row.income) }}</template>
          </el-table-column>
          <el-table-column label="匹配" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="matchType(row.matched)">{{ matchLabel(row.matched) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="aftersale_status" label="售后" width="80" />
        </el-table>
        <el-pagination
          class="pager"
          background
          layout="total, prev, pager, next"
          v-model:current-page="lineQuery.page"
          v-model:page-size="lineQuery.page_size"
          :total="lineTotal"
          @current-change="loadLines"
        />
      </el-tab-pane>

      <el-tab-pane :label="`未匹配 ${unmatched.length}`" name="unmatched">
        <el-alert
          v-if="unmatched.length"
          type="warning"
          :closable="false"
          show-icon
          title="未匹配清零后方可视为完成；指定编码将沉淀为匹配规则"
          style="margin-bottom: 12px"
        />
        <el-table v-loading="unmatchedLoading" :data="unmatched" size="small" border height="480">
          <el-table-column type="selection" width="40" />
          <el-table-column prop="order_no" label="订单号" width="140" show-overflow-tooltip />
          <el-table-column prop="raw_product" label="选购商品" min-width="200" show-overflow-tooltip />
          <el-table-column prop="qty" label="数量" width="60" align="center" />
          <el-table-column prop="province" label="省" width="80" />
          <el-table-column label="推荐候选" min-width="200">
            <template #default="{ row }">
              <template v-if="row.recommend?.length">
                <el-tag
                  v-for="r in row.recommend"
                  :key="r.spec_id"
                  size="small"
                  class="rec-tag"
                  @click="quickPick(row, r)"
                >
                  {{ r.spec_code }} (P{{ r.prio }})
                </el-tag>
              </template>
              <span v-else style="color: #909399">无</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openManual([row])">指定</el-button>
              <el-button link type="danger" @click="onIgnore(row)">忽略</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="batch-bar">
          <el-button type="primary" :disabled="!selectedIds.length" @click="openManualByIds()">
            批量指定编码（已选 {{ selectedIds.length }}）
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 指定编码对话框 -->
    <el-dialog v-model="manualVisible" title="指定规格编码" width="720px">
      <el-input v-model="pickerQ" placeholder="搜索编码 / 产品名" clearable @input="loadPicker" />
      <el-table
        :data="pickerRows"
        size="small"
        highlight-current-row
        style="margin-top: 8px; max-height: 320px; overflow: auto"
        @current-change="(r: any) => (pickedSpec = r)"
      >
        <el-table-column prop="spec_code" label="编码" width="110" />
        <el-table-column prop="product_name" label="产品" min-width="160" show-overflow-tooltip />
        <el-table-column prop="spec_name" label="规格" width="120" />
        <el-table-column label="拿货价" width="100">
          <template #default="{ row }">{{ fmtMoney(row.price) }}</template>
        </el-table-column>
      </el-table>
      <el-alert type="warning" :closable="false" style="margin-top: 10px" title="确认后将回填同文本行并沉淀匹配规则，后续自动命中" />
      <template #footer>
        <el-button @click="manualVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!pickedSpec" :loading="manualSaving" @click="confirmManual">
          确认指定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { calcApi, type OrderLine } from '@/api/calc'
import { masterApi, type SpecPickerItem } from '@/api/master'
import { useAuthStore } from '@/stores/auth'
import { fmtMoney, fmtNum } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const batchId = computed(() => Number(route.params.id))

const summary = ref<Record<string, any> | null>(null)
const tab = ref('lines')
const hasRecalc = computed(() => auth.has('calc.recalc'))

function matchType(m: string): 'success' | 'warning' | 'danger' {
  if (m === 'auto') return 'success'
  if (m === 'manual') return 'warning'
  return 'danger'
}

function matchLabel(m: string): string {
  const map: Record<string, string> = { auto: '自动', manual: '人工', none: '未匹配' }
  return map[m] || m
}

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '排队中',
    running: '计算中',
    success: '成功',
    failed: '失败',
    settled: '已结算',
  }
  return map[summary.value?.status] || summary.value?.status || '-'
})
const statusType = computed(() => {
  const s = summary.value?.status
  if (s === 'success') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'running' || s === 'pending') return 'warning'
  return 'info'
})

// lines
const lines = ref<OrderLine[]>([])
const lineTotal = ref(0)
const lineLoading = ref(false)
const lineQuery = reactive({ page: 1, page_size: 50, matched: '' as string })

async function loadLines() {
  lineLoading.value = true
  try {
    const res = await calcApi.lines(batchId.value, {
      page: lineQuery.page,
      page_size: lineQuery.page_size,
      matched: lineQuery.matched || undefined,
    })
    lines.value = res.items
    lineTotal.value = res.total
  } finally {
    lineLoading.value = false
  }
}

// unmatched
const unmatched = ref<OrderLine[]>([])
const unmatchedLoading = ref(false)
const selectedIds = ref<number[]>([])

async function loadUnmatched() {
  unmatchedLoading.value = true
  try {
    unmatched.value = await calcApi.unmatched(batchId.value)
  } finally {
    unmatchedLoading.value = false
  }
}

// manual match
const manualVisible = ref(false)
const manualSaving = ref(false)
const pickerQ = ref('')
const pickerRows = ref<SpecPickerItem[]>([])
const pickedSpec = ref<SpecPickerItem | null>(null)
let manualLineIds: number[] = []

async function loadPicker() {
  pickerRows.value = await masterApi.specPicker(pickerQ.value || undefined)
}

function openManual(rows: OrderLine[]) {
  manualLineIds = rows.map((r) => r.id)
  pickedSpec.value = null
  pickerQ.value = ''
  manualVisible.value = true
  loadPicker()
}

function openManualByIds() {
  openManual(unmatched.value.filter((u) => selectedIds.value.includes(u.id)))
}

async function quickPick(row: OrderLine, rec: any) {
  manualLineIds = [row.id]
  pickedSpec.value = {
    spec_id: rec.spec_id,
    spec_code: rec.spec_code,
    product_name: rec.product_name,
    spec_name: '',
    price: null,
  }
  await confirmManual()
}

async function confirmManual() {
  if (!pickedSpec.value) return
  manualSaving.value = true
  try {
    await calcApi.manualMatch(batchId.value, manualLineIds, pickedSpec.value.spec_id)
    ElMessage.success('已指定并沉淀规则')
    manualVisible.value = false
    selectedIds.value = []
    loadUnmatched()
    loadSummary()
  } finally {
    manualSaving.value = false
  }
}

async function onIgnore(row: OrderLine) {
  const { value } = await ElMessageBox.prompt('请输入忽略原因（审计留痕）', '忽略行', {
    inputPattern: /\S+/,
    inputErrorMessage: '原因不能为空',
  })
  await calcApi.ignore(batchId.value, [row.id], value)
  ElMessage.success('已忽略')
  loadUnmatched()
}

async function onRecalc() {
  await ElMessageBox.confirm('将以当前成本表与匹配规则重算，生成新版本批次。旧版本保留。', '重算确认', {
    type: 'warning',
  })
  const b = await calcApi.recalc(batchId.value)
  router.push(`/calc/result/${b.id}`)
}

async function loadSummary() {
  summary.value = await calcApi.summary(batchId.value)
}

onMounted(() => {
  loadSummary()
  loadLines()
  loadUnmatched()
})
</script>

<style scoped>
.sub {
  margin-top: 4px;
  font-size: 13px;
  color: var(--erp-text-sub);
}

.pager {
  margin-top: 10px;
  justify-content: flex-end;
}

.rec-tag {
  cursor: pointer;
  margin-right: 4px;
}

.batch-bar {
  margin-top: 12px;
}
</style>
