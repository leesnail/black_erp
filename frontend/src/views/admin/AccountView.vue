<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">账号管理</div>
      <div class="filter-bar" style="margin: 0">
        <el-input v-model="query.q" placeholder="账号 / 姓名" style="width: 180px" clearable @keyup.enter="search" />
        <el-button type="primary" plain @click="search">搜索</el-button>
        <el-button type="primary" @click="openCreate">新建账号</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="id" label="#" width="60" />
      <el-table-column prop="account" label="账号" width="120" />
      <el-table-column prop="display_name" label="姓名" width="110" />
      <el-table-column label="角色" width="110">
        <template #default="{ row }">
          <el-tag size="small">{{ row.role_display }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="模块覆盖" min-width="160">
        <template #default="{ row }">
          <template v-if="Object.keys(row.module_overrides || {}).length">
            <el-tag v-for="(v, k) in row.module_overrides" :key="k" size="small" style="margin-right: 4px">
              {{ k }}: {{ v }}
            </el-tag>
          </template>
          <span v-else style="color: #c0c4cc">按角色默认</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openPerms(row)">权限</el-button>
          <el-button link type="warning" @click="openReset(row)">重置密码</el-button>
          <el-button link :type="row.status === 'active' ? 'danger' : 'success'" @click="toggleStatus(row)">
            {{ row.status === 'active' ? '停用' : '启用' }}
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

    <!-- 新建 -->
    <el-dialog v-model="visible" title="新建账号" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="账号" required>
          <el-input v-model="form.account" placeholder="登录账号" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.display_name" />
        </el-form-item>
        <el-form-item label="初始密码" required>
          <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="form.role" style="width: 100%">
            <el-option v-for="r in roleOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 模块覆盖 -->
    <el-dialog v-model="permVisible" :title="`模块权限 · ${current?.account || ''}`" width="520px">
      <el-alert type="info" :closable="false" show-icon style="margin-bottom: 10px" title="留空 = 按角色默认权限；设置后覆盖角色" />
      <div v-for="m in modules" :key="m.code" class="module-row">
        <span class="module-name">{{ m.label }} <span class="code">{{ m.code }}</span></span>
        <el-radio-group v-model="overrides[m.code]" size="small">
          <el-radio-button value="">默认</el-radio-button>
          <el-radio-button value="read">只读</el-radio-button>
          <el-radio-button value="write">可写</el-radio-button>
          <el-radio-button :value="false">禁止</el-radio-button>
        </el-radio-group>
      </div>
      <template #footer>
        <el-button @click="permVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePerms">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="resetVisible" :title="`重置密码 · ${current?.account || ''}`" width="400px">
      <el-input v-model="newPassword" type="password" show-password placeholder="至少 8 位" />
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePassword">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi, type AccountItem } from '@/api/admin'
import { usePageTable } from '@/composables/usePageTable'

const { query, rows, total, loading, search } = usePageTable<AccountItem>((p) => adminApi.accounts(p))

const roleOptions = [
  { value: 'admin', label: '管理员' },
  { value: 'boss', label: '老板' },
  { value: 'cs', label: '客服' },
  { value: 'po', label: '采购' },
  { value: 'op', label: '运营' },
  { value: 'fin', label: '财务' },
]

const modules = [
  { code: 'master', label: '成本报价' },
  { code: 'calc', label: '财务核算' },
  { code: 'service', label: '客服工作台' },
  { code: 'report', label: '经营报表' },
  { code: 'roi', label: 'ROI' },
  { code: 'admin', label: '系统管理' },
]

const visible = ref(false)
const permVisible = ref(false)
const resetVisible = ref(false)
const saving = ref(false)
const current = ref<AccountItem | null>(null)
const form = reactive({ account: '', display_name: '', password: '', role: 'cs' })
const overrides = reactive<Record<string, unknown>>({})
const newPassword = ref('')

function openCreate() {
  Object.assign(form, { account: '', display_name: '', password: '', role: 'cs' })
  visible.value = true
}

async function onCreate() {
  if (!form.account.trim() || form.password.length < 8) {
    ElMessage.warning('账号不能为空，密码至少 8 位')
    return
  }
  saving.value = true
  try {
    await adminApi.createAccount({ ...form })
    ElMessage.success('已创建')
    visible.value = false
    search()
  } finally {
    saving.value = false
  }
}

async function toggleStatus(row: AccountItem) {
  const next = row.status === 'active' ? 'disabled' : 'active'
  const label = next === 'active' ? '启用' : '停用'
  await ElMessageBox.confirm(`确认${label}账号 ${row.account}？`, '提示', { type: 'warning' })
  await adminApi.toggleAccount(row.id, next)
  ElMessage.success(`已${label}`)
  search()
}

function openPerms(row: AccountItem) {
  current.value = row
  Object.keys(overrides).forEach((k) => delete overrides[k])
  Object.entries(row.module_overrides || {}).forEach(([k, v]) => {
    overrides[k] = (v === false || v === 'read' || v === 'write') ? v : ''
  })
  permVisible.value = true
}

async function savePerms() {
  if (!current.value) return
  saving.value = true
  try {
    const data: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(overrides)) {
      if (v !== '') data[k] = v
    }
    await adminApi.assignPerms(current.value.id, data)
    ElMessage.success('权限已保存')
    permVisible.value = false
    search()
  } finally {
    saving.value = false
  }
}

function openReset(row: AccountItem) {
  current.value = row
  newPassword.value = ''
  resetVisible.value = true
}

async function savePassword() {
  if (!current.value || newPassword.value.length < 8) {
    ElMessage.warning('密码至少 8 位')
    return
  }
  saving.value = true
  try {
    await adminApi.resetPassword(current.value.id, newPassword.value)
    ElMessage.success('密码已重置')
    resetVisible.value = false
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

.module-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed var(--erp-border);
}

.module-name {
  font-size: 13px;
}

.code {
  font-size: 12px;
  color: var(--erp-text-sub);
}
</style>
