<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">经营日报</div>
      <div class="filter-bar" style="margin: 0">
        <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始" end-placeholder="结束" @change="load" />
        <el-button @click="load">查询</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="report_date" label="日期" width="110" />
      <el-table-column prop="shop_name" label="店铺" width="100" />
      <el-table-column prop="order_count" label="订单量" width="100" align="right" />
      <el-table-column label="实收" align="right">
        <template #default="{ row }">{{ fmtMoney(row.income_total) }}</template>
      </el-table-column>
      <el-table-column label="成本" align="right">
        <template #default="{ row }">{{ fmtMoney(row.cost_total) }}</template>
      </el-table-column>
      <el-table-column label="利润" align="right">
        <template #default="{ row }">
          <strong>{{ fmtMoney(row.profit) }}</strong>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { reportApi } from '@/api/service'
import { fmtMoney } from '@/utils/format'

const rows = ref<any[]>([])
const loading = ref(false)
const range = ref<[string, string] | null>(null)

async function load() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (range.value) {
      params.start = range.value[0]
      params.end = range.value[1]
    }
    rows.value = (await reportApi.dailyReports(params)) as any[]
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
