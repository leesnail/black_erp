<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">供应商管理</div>
      <el-button v-if="canWrite" type="primary" @click="openCreate">新增供应商</el-button>
    </div>

    <div class="filter-bar">
      <el-input v-model="q" placeholder="名称 / 联系人" style="width: 220px" clearable @keyup.enter="load" />
      <el-button type="primary" plain @click="load">搜索</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="wechat_group" label="对接微信群" min-width="140" />
      <el-table-column prop="contact_name" label="对接人" width="100" />
      <el-table-column prop="contact_phone" label="联系方式" width="130" />
      <el-table-column prop="products" label="供应产品" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canWrite" link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="visible" :title="editing ? '编辑供应商' : '新增供应商'" size="420px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="对接群">
          <el-input v-model="form.wechat_group" />
        </el-form-item>
        <el-form-item label="对接人">
          <el-input v-model="form.contact_name" />
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="form.contact_phone" />
        </el-form-item>
        <el-form-item label="供应产品">
          <el-input v-model="form.products" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { masterApi, type Supplier } from '@/api/master'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.has('master.supplier.create'))

const rows = ref<Supplier[]>([])
const loading = ref(false)
const q = ref('')

async function load() {
  loading.value = true
  try {
    rows.value = await masterApi.listSuppliers(q.value || undefined)
  } finally {
    loading.value = false
  }
}

const visible = ref(false)
const editing = ref<Supplier | null>(null)
const saving = ref(false)
const form = reactive({
  name: '',
  wechat_group: '',
  contact_name: '',
  contact_phone: '',
  products: '',
  remark: '',
})

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', wechat_group: '', contact_name: '', contact_phone: '', products: '', remark: '' })
  visible.value = true
}

function openEdit(row: Supplier) {
  editing.value = row
  Object.assign(form, {
    name: row.name,
    wechat_group: row.wechat_group || '',
    contact_name: row.contact_name || '',
    contact_phone: row.contact_phone || '',
    products: row.products || '',
    remark: row.remark || '',
  })
  visible.value = true
}

async function onSave() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await masterApi.updateSupplier(editing.value.id, { ...form })
    } else {
      await masterApi.createSupplier({ ...form })
    }
    ElMessage.success('已保存')
    visible.value = false
    load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
