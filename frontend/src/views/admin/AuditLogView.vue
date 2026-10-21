<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">操作日志</div>
    </div>

    <div class="filter-bar">
      <el-select v-model="query.module" placeholder="模块" clearable style="width: 140px" @change="search">
        <el-option v-for="m in modules" :key="m" :label="m" :value="m" />
      </el-select>
      <el-input v-model="query.action" placeholder="动作 如 create/price" style="width: 160px" clearable @keyup.enter="search" />
      <el-button type="primary" plain @click="search">搜索</el-button>
      <el-button @click="reset">重置</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="id" label="#" width="70" />
      <el-table-column label="时间" width="160">
        <template #default="{ row }">{{ (row.created_at || '').replace('T', ' ').slice(0, 19) }}</template>
      </el-table-column>
      <el-table-column label="用户" width="120">
        <template #default="{ row }">{{ row.display_name || row.account || `#${row.user_id}` }}</template>
      </el-table-column>
      <el-table-column prop="module" label="模块" width="110" />
      <el-table-column prop="action" label="动作" width="130" show-overflow-tooltip />
      <el-table-column prop="target" label="对象" min-width="140" show-overflow-tooltip />
      <el-table-column label="变更" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.before || row.after" class="diff">
            <span v-if="row.before" class="before">{{ fmtJson(row.before) }}</span>
            <span v-if="row.before && row.after"> → </span>
            <span v-if="row.after" class="after">{{ fmtJson(row.after) }}</span>
          </span>
          <span v-else style="color: #c0c4cc">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="ip" label="IP" width="130" />
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
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { adminApi, type AuditItem } from '@/api/admin'
import { usePageTable } from '@/composables/usePageTable'

const modules = ['auth', 'admin', 'master', 'calc', 'service', 'report']

const { query, rows, total, loading, search, reset } = usePageTable<AuditItem>((p) => adminApi.auditLogs(p))

function fmtJson(v: unknown): string {
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 80 ? s.slice(0, 80) + '…' : s
}

onMounted(search)
</script>

<style scoped>
.pager {
  margin-top: 12px;
  justify-content: flex-end;
}

.diff {
  font-size: 12px;
}

.before {
  color: var(--erp-danger);
}

.after {
  color: var(--erp-primary);
}
</style>
