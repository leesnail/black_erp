<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">角色权限（只读）</div>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 12px"
      title="角色权限为系统种子配置（权限码 = 模块[.子].动作），单个账号的差异在「账号管理 → 权限」中覆盖"
    />

    <el-table v-loading="loading" :data="roles" border>
      <el-table-column prop="display_name" label="角色" width="110">
        <template #default="{ row }">
          <el-tag>{{ row.display_name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="编码" width="90" />
      <el-table-column label="权限码" min-width="520">
        <template #default="{ row }">
          <el-tag
            v-for="p in row.default_perms"
            :key="p"
            size="small"
            :type="p === '*' ? 'danger' : 'default'"
            class="perm-tag"
          >
            {{ p === '*' ? '全部权限 (*)' : p }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { adminApi, type RolePerm } from '@/api/admin'

const roles = ref<RolePerm[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    roles.value = await adminApi.permMatrix()
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.perm-tag {
  margin: 0 4px 4px 0;
}
</style>
