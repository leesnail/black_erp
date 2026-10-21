<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">计算批次</div>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="id" label="批次" width="80" />
      <el-table-column prop="shop_name" label="店铺" width="80" />
      <el-table-column prop="period" label="期间" width="100" />
      <el-table-column prop="source_filename" label="文件名" min-width="180" show-overflow-tooltip />
      <el-table-column label="行数" width="80" align="right">
        <template #default="{ row }">{{ fmtNum((row.stats as any)?.ship_count) }}</template>
      </el-table-column>
      <el-table-column label="成本" width="100" align="right">
        <template #default="{ row }">{{ fmtMoney((row.stats as any)?.cost_total) }}</template>
      </el-table-column>
      <el-table-column label="利润" width="100" align="right">
        <template #default="{ row }">{{ fmtMoney((row.stats as any)?.profit) }}</template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="60" align="center">
        <template #default="{ row }">v{{ row.version }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">
            {{ statusMap[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/calc/result/${row.id}`)">查看</el-button>
          <el-button v-if="row.status === 'success'" link type="warning" @click="onRecalc(row)">重算</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { calcApi, type Batch } from '@/api/calc'
import { fmtMoney, fmtNum } from '@/utils/format'

const router = useRouter()
const rows = ref<Batch[]>([])
const loading = ref(false)

const statusMap: Record<string, string> = {
  pending: '排队',
  running: '计算中',
  success: '成功',
  failed: '失败',
  settled: '已结算',
}

async function load() {
  loading.value = true
  try {
    rows.value = await calcApi.listBatches()
  } finally {
    loading.value = false
  }
}

async function onRecalc(row: Batch) {
  await ElMessageBox.confirm(`重算批次 #${row.id} 将生成新版本，旧版保留。`, '重算确认', { type: 'warning' })
  const b = await calcApi.recalc(row.id)
  ElMessage.success(`已创建 v${b.version} 批次 #${b.id}`)
  router.push(`/calc/result/${b.id}`)
}

onMounted(load)
</script>
