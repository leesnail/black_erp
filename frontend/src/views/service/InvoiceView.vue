<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">发票管理</div>
      <el-button v-if="auth.has('service.create')" type="primary" @click="openCreate">登记发票</el-button>
    </div>

    <el-tabs v-model="tab">
      <el-tab-pane label="发票列表" name="list">
        <div class="filter-bar">
          <el-input v-model="query.q" placeholder="发票号" style="width: 180px" clearable @keyup.enter="search" />
          <el-select v-model="query.status" placeholder="回传状态" clearable style="width: 130px" @change="search">
            <el-option label="未回传" value="pending" />
            <el-option label="已回传" value="uploaded" />
          </el-select>
          <el-button type="primary" plain @click="search">搜索</el-button>
        </div>

        <el-table v-loading="loading" :data="rows" border stripe>
          <el-table-column prop="invoice_no" label="发票号" width="150" />
          <el-table-column prop="invoice_type" label="类型" width="70" />
          <el-table-column label="金额" width="110" align="right">
            <template #default="{ row }">{{ fmtMoney(row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="invoice_date" label="开票日期" width="110" />
          <el-table-column label="附件" width="90" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.status === 'uploaded'" type="success" size="small">已回传</el-tag>
              <el-tag v-else type="info" size="small">未回传</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button v-if="auth.has('service.invoice_upload') && row.status !== 'uploaded'" link type="primary" @click="openUpload(row)">
                回传
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          class="pager"
          background
          layout="total, prev, pager, next"
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          @current-change="search"
        />
      </el-tab-pane>

      <el-tab-pane label="提醒记录" name="reminders">
        <el-table :data="reminders" size="small" v-loading="remLoading">
          <el-table-column prop="title" label="提醒" min-width="220" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'read' ? 'info' : row.status === 'failed' ? 'danger' : 'warning'">
                {{ remStatusMap[row.status] || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="retry_count" label="重试" width="70" align="center" />
          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">{{ (row.created_at || '').replace('T', ' ').slice(0, 16) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 登记 -->
    <el-dialog v-model="visible" title="登记发票" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="发票号" required>
          <el-input v-model="form.invoice_no" />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.invoice_type">
            <el-radio value="专票">专票</el-radio>
            <el-radio value="普票">普票</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input-number v-model="form.amount" :min="0" :precision="2" style="width: 200px" />
        </el-form-item>
        <el-form-item label="开票日期">
          <el-date-picker v-model="form.invoice_date" value-format="YYYY-MM-DD" style="width: 200px" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 回传：简化为示例附件 key（S4 接通用上传） -->
    <el-dialog v-model="uploadVisible" title="发票回传" width="480px">
      <el-upload drag multiple accept=".jpg,.png,.pdf" :auto-upload="false" :on-change="(f: any) => uploadFiles.push(f.raw)">
        <div class="el-upload__text">拖入发票照片 / PDF（jpg png pdf）</div>
      </el-upload>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="confirmUpload">确认回传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { serviceApi } from '@/api/service'
import { usePageTable } from '@/composables/usePageTable'
import { useAuthStore } from '@/stores/auth'
import { fmtMoney } from '@/utils/format'

const auth = useAuthStore()
const tab = ref('list')

const { query, rows, total, loading, search } = usePageTable<Record<string, any>>((p) =>
  serviceApi.listInvoices(p),
)

const reminders = ref<any[]>([])
const remLoading = ref(false)
const remStatusMap: Record<string, string> = {
  pending: '待触发',
  delivered: '已推送',
  read: '已读',
  failed: '失败',
}

// create
const visible = ref(false)
const saving = ref(false)
const form = reactive({
  invoice_no: '',
  invoice_type: '普票',
  amount: 0,
  invoice_date: '',
  remark: '',
})

function openCreate() {
  Object.assign(form, { invoice_no: '', invoice_type: '普票', amount: 0, invoice_date: '', remark: '' })
  visible.value = true
}

async function onSave() {
  if (!form.invoice_no.trim()) {
    ElMessage.warning('请输入发票号')
    return
  }
  saving.value = true
  try {
    await serviceApi.createInvoice({ ...form })
    ElMessage.success('已登记')
    visible.value = false
    search()
  } finally {
    saving.value = false
  }
}

// upload
const uploadVisible = ref(false)
const uploading = ref(false)
const uploadFiles = ref<File[]>([])
const currentInvoice = ref<Record<string, any> | null>(null)

function openUpload(row: Record<string, any>) {
  currentInvoice.value = row
  uploadFiles.value = []
  uploadVisible.value = true
}

async function confirmUpload() {
  if (!currentInvoice.value) return
  uploading.value = true
  try {
    // 简化：以文件名作为 key 存储（真实实现走通用上传接口）
    const keys = uploadFiles.value.map((f) => f.name)
    if (!keys.length) {
      ElMessage.warning('请选择文件')
      return
    }
    await serviceApi.uploadInvoice(currentInvoice.value.id as number, keys)
    ElMessage.success('已回传，该发票提醒停止')
    uploadVisible.value = false
    search()
  } finally {
    uploading.value = false
  }
}

async function loadReminders() {
  remLoading.value = true
  try {
    reminders.value = (await serviceApi.reminders()) as any[]
  } finally {
    remLoading.value = false
  }
}

watch(tab, (t) => {
  if (t === 'reminders') loadReminders()
})

onMounted(search)
</script>

<style scoped>
.pager {
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
