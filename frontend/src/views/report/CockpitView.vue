<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">经营驾驶舱</div>
      <el-select v-model="period" placeholder="期间" clearable style="width: 140px" @change="load">
        <el-option v-for="p in periods" :key="p" :label="p" :value="p" />
      </el-select>
    </div>

    <el-alert
      v-if="BacklogAlert"
      type="warning"
      :closable="false"
      show-icon
      title="存在未匹配订单，利润可能不完整"
      style="margin-bottom: 12px"
    />

    <div class="stat-cards">
      <div class="stat-card">
        <div class="label">商家实收</div>
        <div class="value money">{{ fmtMoney(data?.income_total) }}</div>
      </div>
      <div class="stat-card">
        <div class="label">发货单数</div>
        <div class="value">{{ fmtNum(data?.ship_count) }}</div>
      </div>
      <div class="stat-card">
        <div class="label">采购成本</div>
        <div class="value money">{{ fmtMoney(data?.cost_total) }}</div>
      </div>
      <div class="stat-card accent">
        <div class="label">利润</div>
        <div class="value money">{{ fmtMoney(data?.profit_total) }}</div>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>店铺利润对比</template>
          <div ref="barRef" style="height: 300px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>近 6 期利润趋势</template>
          <div ref="lineRef" style="height: 300px" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>店铺汇总</template>
      <el-table :data="data?.shops || []" size="small">
        <el-table-column prop="shop_name" label="店铺" width="100" />
        <el-table-column label="实收" align="right">
          <template #default="{ row }">{{ fmtMoney(row.income) }}</template>
        </el-table-column>
        <el-table-column label="成本" align="right">
          <template #default="{ row }">{{ fmtMoney(row.cost) }}</template>
        </el-table-column>
        <el-table-column label="利润" align="right">
          <template #default="{ row }">
            <strong>{{ fmtMoney(row.profit) }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="ship_count" label="发货单" width="90" align="center" />
        <el-table-column prop="aftersale" label="售后单" width="90" align="center" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { reportApi } from '@/api/service'
import { fmtMoney, fmtNum, todayPeriod } from '@/utils/format'

const data = ref<Record<string, any> | null>(null)
const period = ref(todayPeriod())
const periods = ref<string[]>([])

const BacklogAlert = computed(() => Number(data.value?.unmatched_backlog || 0) > 0)

const barRef = ref<HTMLDivElement>()
const lineRef = ref<HTMLDivElement>()
let barChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

function renderCharts() {
  if (!data.value) return
  if (barRef.value) {
    if (!barChart) barChart = echarts.init(barRef.value)
    const shops = data.value.shops || []
    barChart.setOption({
      grid: { left: 60, right: 20, top: 20, bottom: 40 },
      xAxis: { type: 'category', data: shops.map((s: any) => s.shop_name) },
      yAxis: { type: 'value' },
      tooltip: { trigger: 'axis' },
      series: [
        {
          type: 'bar',
          data: shops.map((s: any) => Number(s.profit)),
          itemStyle: { color: '#1B5E38', borderRadius: [4, 4, 0, 0] },
        },
      ],
    })
  }
  if (lineRef.value) {
    if (!lineChart) lineChart = echarts.init(lineRef.value)
    const trend = data.value.trend || []
    lineChart.setOption({
      grid: { left: 60, right: 20, top: 20, bottom: 40 },
      xAxis: { type: 'category', data: trend.map((t: any) => t.period) },
      yAxis: { type: 'value' },
      tooltip: { trigger: 'axis' },
      series: [
        {
          type: 'line',
          smooth: true,
          data: trend.map((t: any) => Number(t.profit)),
          itemStyle: { color: '#1B5E38' },
          areaStyle: { color: 'rgba(27,94,56,0.12)' },
        },
      ],
    })
  }
}

async function load() {
  data.value = await reportApi.cockpit(period.value ? { period: period.value } : undefined)
  const ps = (data.value?.trend || []).map((t: any) => t.period).filter(Boolean)
  if (ps.length) periods.value = ps
  renderCharts()
}

function onResize() {
  barChart?.resize()
  lineChart?.resize()
}

watch(period, load)

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  barChart?.dispose()
  lineChart?.dispose()
})
</script>
