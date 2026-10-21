<template>
  <div class="forbidden">
    <el-result icon="warning" title="403 无访问权限" sub-title="当前账号没有该模块的访问权限，请联系管理员">
      <template #extra>
        <el-button type="primary" @click="$router.push('/')">返回工作台</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
.forbidden {
  padding: 80px 0;
}
</style>
