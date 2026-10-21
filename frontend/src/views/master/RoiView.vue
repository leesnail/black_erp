<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">ROI 计算</div>
    </div>

    <el-row :gutter="16">
      <el-col :span="10">
        <el-card shadow="never">
          <el-form label-width="80px">
            <el-form-item label="店铺">
              <el-select v-model="form.shop_id" style="width: 100%">
                <el-option v-for="s in shops" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="周期">
              <el-input v-model="form.period" placeholder="2026-08" style="width: 160px" />
            </el-form-item>
            <el-form-item label="投放花费">
              <el-input-number v-model="form.spend" :min="0" :precision="2" style="width: 200px" />
            </el-form-item>
            <el-form-item label="成交金额">
              <el-input-number v-model="form.deal" :min="0" :precision="2" style="width: 200px" />
            </el-form-item>
            <el-form-item label="ROI">
              <div class="roi-value">{{ roiText }}</div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" :disabled="!form.shop_id || !form.period" @click="onSave">
                保存记录
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>历史记录</template>
          <el-table :data="history" size="small" v-loading="loading">
            <el-table-column prop="period" label="周期" width="100" />
            <el-table-column label="花费" width="120" align="right">
              <template #default="{ row }">{{ fmtMoney(row.spend) }}</template>
            </el-table-column>
            <el-table-column label="成交" width="120" align="right">
              <template #default="{ row }">{{ fmtMoney(row.deal_amount) }}</template>
            </el-table-column>
            <el-table-column label="ROI" width="100" align="right">
              <template #default="{ row }">{{ row.roi ?? '-' }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { masterApi } from '@/api/master'
import { fmtMoney, todayPeriod } from '@/utils/format'

const shops = ref<Array<{ id: number; name: string }>>([])
const history = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)

const form = reactive({
  shop_id: undefined as number | undefined,
  period: todayPeriod(),
  spend: 0,
  deal: 0,
})

const roiText = computed(() => {
  if (!form.spend) return '-'
  return (form.deal / form.spend).toFixed(2)
})

async function loadHistory() {
  loading.value = true
  try {
    history.value = (await masterApi.listRoi(form.shop_id)) as any[]
  } finally {
    loading.value = false
  }
}

async function onSave() {
  saving.value = true
  try {
    await masterApi.createRoi({
      shop_id: form.shop_id,
      period: form.period,
      spend: form.spend,
      deal_amount: form.deal,
    })
    ElMessage.success('已保存')
    loadHistory()
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  shops.value = await masterApi.listShops()
  form.shop_id = shops.value[0]?.id
  loadHistory()
})
</script>

<style scoped>
.roi-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--erp-primary);
}
</style>
