<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">附加成本规则</div>
      <span class="hint">按件计价 · 仅影响之后的计算</span>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="name" label="规则" width="160" />
      <el-table-column label="省份" min-width="260">
        <template #default="{ row }">
          <el-tag v-for="p in row.provinces" :key="p" size="small" class="prov-tag">{{ p }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="附加/件" width="120" align="right">
        <template #default="{ row }">{{ fmtMoney(row.amount) }}</template>
      </el-table-column>
      <el-table-column prop="unit" label="计价单位" width="90" align="center" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link :type="row.status === 'active' ? 'danger' : 'success'" @click="toggleStatus(row)">
            {{ row.status === 'active' ? '停用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="`编辑 · ${editing?.name || ''}`" width="560px">
      <el-form label-width="90px">
        <el-form-item label="附加/件" required>
          <el-input-number v-model="amount" :min="0" :precision="2" :step="1" style="width: 180px" />
        </el-form-item>
        <el-form-item label="省份">
          <el-input v-model="provincesText" type="textarea" :rows="5" placeholder="每行一个省份，如：海南" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi, type RegionRuleItem } from '@/api/admin'
import { fmtMoney } from '@/utils/format'

const rows = ref<RegionRuleItem[]>([])
const loading = ref(false)
const visible = ref(false)
const saving = ref(false)
const editing = ref<RegionRuleItem | null>(null)
const amount = ref(0)
const provincesText = ref('')

async function load() {
  loading.value = true
  try {
    rows.value = await adminApi.regionRules()
  } finally {
    loading.value = false
  }
}

function openEdit(row: RegionRuleItem) {
  editing.value = row
  amount.value = Number(row.amount)
  provincesText.value = (row.provinces || []).join('\n')
  visible.value = true
}

async function onSave() {
  if (!editing.value) return
  saving.value = true
  try {
    const provinces = provincesText.value
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
    await adminApi.updateRegionRule(editing.value.id, { amount: String(amount.value), provinces })
    ElMessage.success('已保存（仅影响之后的计算）')
    visible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function toggleStatus(row: RegionRuleItem) {
  const next = row.status === 'active' ? 'disabled' : 'active'
  const label = next === 'active' ? '停用' : '启用'
  await ElMessageBox.confirm(`确认${label}「${row.name}」规则？`, '提示', { type: 'warning' })
  await adminApi.updateRegionRule(row.id, { status: next })
  load()
}

onMounted(load)
</script>

<style scoped>
.hint {
  font-size: 13px;
  color: var(--erp-text-sub);
}

.prov-tag {
  margin: 0 4px 4px 0;
}
</style>
