<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">售后登记</div>
      <el-button v-if="auth.has('service.create')" type="primary" @click="openCreate">登记售后</el-button>
    </div>

    <div class="filter-bar">
      <el-input v-model="query.q" placeholder="订单号 / 客户" style="width: 200px" clearable @keyup.enter="search" />
      <el-select v-model="query.status" placeholder="状态" clearable style="width: 130px" @change="search">
        <el-option label="待处理" value="pending" />
        <el-option label="已解决" value="resolved" />
        <el-option label="已关闭" value="closed" />
      </el-select>
      <el-button type="primary" plain @click="search">搜索</el-button>
      <el-button @click="reset">重置</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="order_no" label="订单号" width="150" show-overflow-tooltip />
      <el-table-column prop="customer_name" label="客户" width="100" />
      <el-table-column prop="problem_type" label="类型" width="90" />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="statusType(row.status)">{{ statusMap[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="150">
        <template #default="{ row }">{{ (row.created_at || '').replace('T', ' ').slice(0, 16) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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
      @current-change="load"
    />

    <el-drawer v-model="visible" :title="editing ? '编辑售后' : '登记售后'" size="440px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="订单号">
          <el-input v-model="form.order_no" placeholder="可选" />
        </el-form-item>
        <el-form-item label="客户">
          <el-input v-model="form.customer_name" />
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="form.customer_contact" />
        </el-form-item>
        <el-form-item label="问题类型">
          <el-select v-model="form.problem_type" style="width: 100%">
            <el-option label="退货" value="退货" />
            <el-option label="质量问题" value="质量问题" />
            <el-option label="物流问题" value="物流问题" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="问题描述" required>
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="处理结果">
          <el-input v-model="form.result" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="处理状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="待处理" value="pending" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { serviceApi } from '@/api/service'
import { usePageTable } from '@/composables/usePageTable'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const { query, rows, total, loading, search, reset } = usePageTable<Record<string, any>>((p) =>
  serviceApi.listAftersales(p),
)

const statusMap: Record<string, string> = { pending: '待处理', resolved: '已解决', closed: '已关闭' }
function statusType(s: string) {
  return s === 'resolved' ? 'success' : s === 'closed' ? 'info' : 'warning'
}

const visible = ref(false)
const saving = ref(false)
const editing = ref<Record<string, any> | null>(null)
const form = reactive({
  order_no: '',
  customer_name: '',
  customer_contact: '',
  problem_type: '其他',
  description: '',
  result: '',
  status: 'pending',
})

function load() {
  search()
}

function openCreate() {
  editing.value = null
  Object.assign(form, {
    order_no: '',
    customer_name: '',
    customer_contact: '',
    problem_type: '其他',
    description: '',
    result: '',
    status: 'pending',
  })
  visible.value = true
}

function openEdit(row: Record<string, any>) {
  editing.value = row
  Object.assign(form, {
    order_no: row.order_no || '',
    customer_name: row.customer_name || '',
    customer_contact: row.customer_contact || '',
    problem_type: row.problem_type,
    description: row.description || '',
    result: row.result || '',
    status: row.status,
  })
  visible.value = true
}

async function onSave() {
  if (!form.description.trim()) {
    ElMessage.warning('请输入问题描述')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await serviceApi.updateAftersale(editing.value.id as number, { ...form })
    } else {
      await serviceApi.createAftersale({ ...form })
    }
    ElMessage.success('已保存')
    visible.value = false
    search()
  } finally {
    saving.value = false
  }
}

onMounted(search)
</script>

<style scoped>
.pager {
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
