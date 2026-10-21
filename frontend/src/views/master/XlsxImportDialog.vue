<template>
  <el-dialog v-model="visible" title="导入成本表（固定模板）" width="560px" :close-on-click-modal="false">
    <el-upload
      drag
      :auto-upload="false"
      :limit="1"
      accept=".xlsx"
      :on-change="onFileChange"
      :on-remove="() => (file = null)"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">拖入 <em>.xlsx</em> 文件，或点击选择</div>
      <template #tip>
        <div class="el-upload__tip">
          固定模板列：店铺名称、产品标题名、规格售价、拿货价（可选规格编码列）
        </div>
      </template>
    </el-upload>

    <div v-if="result" class="result-box">
      <el-descriptions :column="2" size="small" border>
        <el-descriptions-item label="总行数">{{ result.total_rows }}</el-descriptions-item>
        <el-descriptions-item label="有效行">{{ result.ok_rows }}</el-descriptions-item>
        <el-descriptions-item label="新建规格">{{ result.created }}</el-descriptions-item>
        <el-descriptions-item label="价格更新">{{ result.price_updated }}</el-descriptions-item>
      </el-descriptions>
      <el-alert
        v-if="result.errors?.length"
        type="warning"
        :closable="false"
        style="margin-top: 8px"
        :title="`异常 ${result.errors.length} 行（前 3 条）：`"
        :description="result.errors.slice(0, 3).map((e: any) => `第${e.row}行: ${e.reason}`).join('；')"
      />
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button :loading="loading" :disabled="!file" @click="onSubmit">
        {{ result ? '确认导入' : '预检' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import request from '@/api/request'

const visible = defineModel<boolean>({ default: false })
const emit = defineEmits<{ done: [] }>()

const file = ref<File | null>(null)
const loading = ref(false)
const result = ref<Record<string, any> | null>(null)
const dryRun = ref(true)

function onFileChange(f: UploadFile) {
  file.value = (f.raw as File) || null
  result.value = null
  dryRun.value = true
}

async function onSubmit() {
  if (!file.value) return
  loading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('dry_run', String(dryRun.value && !result.value))
    const res = await request.post('/master/specs/import-xlsx', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (!result.value) {
      result.value = res as any
      dryRun.value = false
      ElMessage.success('预检完成，确认后导入')
    } else {
      ElMessage.success('导入完成')
      visible.value = false
      result.value = null
      file.value = null
      emit('done')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.result-box {
  margin-top: 12px;
}
</style>
