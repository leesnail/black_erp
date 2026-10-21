<template>
  <div class="layout">
    <header class="topbar">
      <div class="topbar-left">
        <span class="logo">BLACK ERP</span>
      </div>
      <div class="topbar-right">
        <el-badge :value="app.unreadCount" :hidden="!app.unreadCount" class="msg-badge">
          <el-icon :size="18" class="msg-icon"><Bell /></el-icon>
        </el-badge>
        <el-dropdown @command="onCommand">
          <span class="user-trigger">
            <el-avatar :size="28" class="avatar">{{ avatarText }}</el-avatar>
            <span class="user-name">{{ auth.user?.display_name }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>{{ auth.user?.account }} · {{ roleLabel }}</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="body">
      <aside class="sider" :class="{ collapsed: app.siderCollapsed }">
        <el-menu
          :default-active="$route.path"
          :collapse="app.siderCollapsed"
          router
          background-color="#1F2D3D"
          text-color="#C0C4CC"
          active-text-color="#FFFFFF"
        >
          <template v-for="item in visibleMenu" :key="item.path">
            <el-sub-menu v-if="item.children?.length" :index="item.path">
              <template #title>
                <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
                <span>{{ item.title }}</span>
              </template>
              <el-menu-item
                v-for="child in item.children"
                :key="child.path"
                :index="`${item.path}/${child.path}`"
              >
                {{ child.title }}
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="item.path">
              <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
              <template #title>{{ item.title }}</template>
            </el-menu-item>
          </template>
        </el-menu>
      </aside>

      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { MENU_TREE, filterMenu } from '@/router/menu'
import { serviceApi } from '@/api/service'

const auth = useAuthStore()
const app = useAppStore()
const router = useRouter()

const visibleMenu = computed(() => filterMenu(MENU_TREE, (c) => auth.has(c)))

const avatarText = computed(() => (auth.user?.display_name || '?').slice(0, 1))
const roleLabel = computed(() => {
  const map: Record<string, string> = {
    admin: '管理员',
    boss: '老板',
    cs: '客服',
    po: '采购',
    op: '运营',
    fin: '财务',
  }
  return map[auth.role] || auth.role
})

async function onCommand(cmd: string) {
  if (cmd === 'logout') {
    await auth.logout()
    router.replace('/login')
  }
}

onMounted(async () => {
  try {
    const res = await serviceApi.reminderCount()
    app.setUnread(res.total)
  } catch {
    /* 无权限时忽略 */
  }
})
</script>

<style scoped lang="scss">
.layout {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: 52px;
  background: #fff;
  border-bottom: 1px solid var(--erp-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: var(--erp-primary);
  letter-spacing: 0.5px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.msg-icon {
  cursor: pointer;
  color: #606266;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  outline: none;
  color: #606266;
}

.avatar {
  background: var(--erp-primary);
  color: #fff;
  font-size: 12px;
}

.body {
  flex: 1;
  display: flex;
  min-height: 0;
}

.sider {
  width: 200px;
  flex-shrink: 0;
  background: var(--erp-sider);
  overflow-y: auto;
  transition: width 0.2s;

  &.collapsed {
    width: 64px;
  }

  :deep(.el-menu) {
    border-right: none;
  }
}

.content {
  flex: 1;
  overflow: auto;
  background: var(--erp-bg);
  min-width: 0;
}
</style>
