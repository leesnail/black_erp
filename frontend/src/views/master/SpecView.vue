<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">规格成本表</div>
      <div>
        <el-button v-if="canWrite" type="primary" @click="openCreate">新增规格</el-button>
        <el-button v-if="canWrite" @click="importVisible = true">导入 XLSX</el-button>
        <el-button @click="onExport">导出</el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input
        v-model="query.q"
        placeholder="编码 / 产品名 / 规格"
        style="width: 220px"
        clearable
        @keyup.enter="search"
        @clear="search"
      />
      <el-button type="primary" plain @click="search">搜索</el-button>
      <el-button @click="reset">重置</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="spec_code" label="编码" width="120" />
      <el-table-column prop="product_name" label="产品名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="spec_name" label="规格" width="140" show-overflow-tooltip />
      <el-table-column label="拿货价" width="110" align="right">
        <template #default="{ row }">
          <span class="money">{{ fmtMoney(row.price) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="supplier_id" label="供应商" width="100">
        <template #default="{ row }">{{ supplierName(row.supplier_id) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="160">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button v-if="canWrite" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link @click="showHistory(row)">历史</el-button>
            <el-button v-if="canWrite && row.status === 'active'" link type="danger" @click="onDisable(row)">
              停用
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pager"
      background
      layout="total, prev, pager, next, sizes"
      v-model:current-page="query.page"
      v-model:page-size="query.page_size"
      :total="total"
      :page-sizes="[20, 50, 100]"
    />

    <!-- 新增/编辑抽屉 -->
    <el-drawer v-model="drawerVisible" :title="editing ? '编辑规格' : '新增规格'" size="440px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="90px">
        <el-form-item label="产品名称" prop="product_name">
          <el-input v-model="form.product_name" placeholder="如：香葱椒盐月饼" />
        </el-form-item>
        <el-form-item label="规格名" prop="spec_name">
          <el-input v-model="form.spec_name" placeholder="如：60g×10枚" />
        </el-form-item>
        <el-form-item label="默认供应商" prop="supplier_id">
          <el-select v-model="form.supplier_id" placeholder="选择供应商" style="width: 100%">
            <el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="拿货价" prop="price">
          <el-input-number v-model="form.price" :min="0" :precision="2" :step="0.01" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-alert v-if="editing" type="info" :closable="false" show-icon title="保存将追加一条价格历史，不覆盖旧值" />
      </el-form>
      <template #footer>
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">
          {{ editing ? '保存' : '保存并生成编码' }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 历史 -->
    <el-dialog v-model="historyVisible" :title="`价格历史 · ${historySpec?.spec_code || ''}`" width="520px">
      <el-table :data="historyRows" size="small">
        <el-table-column prop="price" label="价格" width="120">
          <template #default="{ row }">{{ fmtMoney(row.price) }}</template>
        </el-table-column>
        <el-table-column prop="effective_at" label="生效时间" />
      </el-table>
    </el-dialog>

    <!-- XLSX 导入 -->
    <XlsxImportDialog v-model="importVisible" @done="refresh" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { masterApi, type Spec, type Supplier } from '@/api/master'
import { usePageTable } from '@/composables/usePageTable'
import { useAuthStore } from '@/stores/auth'
import { fmtMoney } from '@/utils/format'
import XlsxImportDialog from './XlsxImportDialog.vue'

const auth = useAuthStore()
const canWrite = computed(() => auth.has('master.spec.create') || auth.has('master.spec.update'))

const { query, rows, total, loading, search, reset, refresh } = usePageTable<Spec>((p) =>
  masterApi.listSpecs(p),
)

const suppliers = ref<Supplier[]>([])

function supplierName(id: number) {
  return suppliers.value.find((s) => s.id === id)?.name || String(id)
}

function formatTime(iso?: string) {
  if (!iso) return '-'
  return iso.replace('T', ' ').slice(0, 16)
}

// ---- form ----
const drawerVisible = ref(false)
const editing = ref<Spec | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({
  product_name: '',
  spec_name: '',
  supplier_id: undefined as number | undefined,
  price: 0,
  remark: '',
})
const formRules = {
  product_name: [{ required: true, message: '请输入产品名称', trigger: 'blur' }],
  spec_name: [{ required: true, message: '请输入规格名', trigger: 'blur' }],
  supplier_id: [{ required: true, message: '请选择供应商', trigger: 'change' }],
  price: [{ required: true, message: '请输入拿货价', trigger: 'blur' }],
}

function openCreate() {
  editing.value = null
  form.product_name = ''
  form.spec_name = ''
  form.supplier_id = undefined
  form.price = 0
  form.remark = ''
  drawerVisible.value = true
}

function openEdit(row: Spec) {
  editing.value = row
  form.product_name = row.product_name
  form.spec_name = row.spec_name
  form.supplier_id = row.supplier_id
  form.price = Number(row.price || 0)
  form.remark = ''
  drawerVisible.value = true
}

async function onSave() {
  await formRef.value?.validate().catch(() => Promise.reject())
  saving.value = true
  try {
    if (editing.value) {
      await masterApi.updateSpec(editing.value.id, { ...form })
      ElMessage.success('已保存（含价格历史）')
    } else {
      const created = await masterApi.createSpec({ ...form })
      ElMessage.success(`编码 ${created.spec_code} 已生成`)
    }
    drawerVisible.value = false
    refresh()
  } finally {
    saving.value = false
  }
}

async function onDisable(row: Spec) {
  await ElMessageBox.confirm(`确定停用 ${row.spec_code}？停用后新登记不可选。`, '停用确认', { type: 'warning' })
  await masterApi.disableSpec(row.id)
  ElMessage.success('已停用')
  refresh()
}

// ---- history ----
const historyVisible = ref(false)
const historySpec = ref<Spec | null>(null)
const historyRows = ref<Array<{ price: string; effective_at: string }>>([])

async function showHistory(row: Spec) {
  historySpec.value = row
  historyRows.value = (await masterApi.priceHistory(row.id)).map((r) => ({
    price: r.price,
    effective_at: r.effective_at.replace('T', ' ').slice(0, 19),
  }))
  historyVisible.value = true
}

function onExport() {
  ElMessage.info('导出将在 S5 完善')
}

const importVisible = ref(false)

onMounted(async () => {
  suppliers.value = await masterApi.listSuppliers()
  refresh()
})
</script>

<style scoped>
.pager {
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
