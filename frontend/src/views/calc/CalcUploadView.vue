<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">订单上传与计算</div>
    </div>

    <el-card shadow="never" class="upload-card">
      <div class="meta-row">
        <el-select v-model="shopId" placeholder="店铺（可选，按文件名识别）" clearable style="width: 200px">
          <el-option v-for="s in shops" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-input v-model="period" placeholder="期间 如 2026-08" style="width: 160px" />
      </div>

      <el-upload
        drag
        :auto-upload="false"
        :limit="1"
        accept=".csv"
        :on-change="onFile"
        :on-remove="() => (file = null)"
        class="dropzone"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖入订单 CSV（文件名建议含店铺名，如 誉恒8月份.csv）</div>
      </el-upload>

      <div class="actions">
        <el-button type="primary" size="large" :disabled="!file" :loading="uploading" @click="onUpload">
          上传并预检
        </el-button>
      </div>
    </el-card>

    <!-- 预检报告 -->
    <el-card v-if="calc.preview && calc.phase === 'preview'" shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>预检报告 · {{ calc.preview.shop_name }}</span>
          <el-button type="primary" size="large" @click="onConfirm">确认计算</el-button>
        </div>
      </template>
      <div class="stat-cards">
        <div class="stat-card">
          <div class="label">总行数</div>
          <div class="value">{{ calc.preview.total }}</div>
        </div>
        <div class="stat-card">
          <div class="label">无物流跳过</div>
          <div class="value">{{ calc.preview.no_ship_skip }}</div>
        </div>
        <div class="stat-card">
          <div class="label">售后单（计成本）</div>
          <div class="value">{{ calc.preview.aftersale }}</div>
        </div>
        <div class="stat-card">
          <div class="label">数量异常</div>
          <div class="value">{{ calc.preview.qty_invalid }}</div>
        </div>
      </div>
      <el-alert type="info" :closable="false" show-icon title="口径：有物流才计成本 · 售后仍计采购成本 · 地区附加按件" />
    </el-card>

    <!-- 计算中 -->
    <el-card v-if="calc.phase === 'running'" shadow="never" style="margin-top: 16px">
      <div class="running-box">
        <el-progress :percentage="88" :indeterminate="true" :duration="2" :show-text="false" style="width: 320px" />
        <div class="running-text">计算中… 批次 #{{ calc.batchId }}，完成后自动跳转结果页</div>
      </div>
    </el-card>

    <el-card v-if="calc.phase === 'failed'" shadow="never" style="margin-top: 16px">
      <el-result icon="error" title="计算失败" :sub-title="calc.batch?.err_msg || '请重试'">
        <template #extra>
          <el-button type="primary" @click="calc.reset()">重新上传</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type UploadFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { masterApi } from '@/api/master'
import { useCalcStore } from '@/stores/calc'
import { todayPeriod } from '@/utils/format'

const router = useRouter()
const calc = useCalcStore()

const shops = ref<Array<{ id: number; name: string }>>([])
const shopId = ref<number | undefined>()
const period = ref(todayPeriod())
const file = ref<File | null>(null)
const uploading = ref(false)

function onFile(f: UploadFile) {
  file.value = (f.raw as File) || null
}

async function onUpload() {
  if (!file.value) return
  uploading.value = true
  try {
    await calc.upload(file.value, shopId.value, period.value || undefined)
    ElMessage.success('预检完成')
  } finally {
    uploading.value = false
  }
}

function onConfirm() {
  calc.startPoll()
}

onMounted(async () => {
  shops.value = await masterApi.listShops()
  // 若上一次还在 running，恢复轮询
  if (calc.phase === 'running' && calc.batchId) {
    calc.startPoll()
  }
})

// 计算完成后跳转结果页
watch(
  () => calc.phase,
  (p) => {
    if (p === 'success' && calc.batchId) {
      router.push(`/calc/result/${calc.batchId}`)
    }
  },
)

onUnmounted(() => calc.stopPoll())
</script>

<style scoped>
.upload-card :deep(.el-upload-dragger) {
  padding: 40px 20px;
}

.meta-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.actions {
  margin-top: 16px;
  text-align: center;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.running-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px 0;
}

.running-text {
  color: var(--erp-text-sub);
}
</style>
