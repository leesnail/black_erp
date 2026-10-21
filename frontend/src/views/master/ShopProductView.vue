<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">店铺产品登记</div>
      <el-button v-if="canWrite" type="primary" @click="openCreate">新增登记</el-button>
    </div>

    <div class="filter-bar">
      <el-input v-model="query.q" placeholder="标题关键字" style="width: 220px" clearable @keyup.enter="search" />
      <el-select v-model="query.shop_id" placeholder="店铺" clearable style="width: 140px" @change="search">
        <el-option v-for="s in shops" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
      <el-button type="primary" plain @click="search">搜索</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="shop_name" label="店铺" width="80" />
      <el-table-column prop="title_keyword" label="标题关键字" min-width="200" show-overflow-tooltip />
      <el-table-column prop="link_id" label="链接ID" width="140" show-overflow-tooltip />
      <el-table-column prop="spec_code" label="规格编码" width="110" />
      <el-table-column prop="spec_name" label="规格" width="120" />
      <el-table-column label="售价" width="100" align="right">
        <template #default="{ row }">{{ fmtMoney(row.sale_price) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canWrite" link :type="row.status === 'active' ? 'danger' : 'success'" @click="toggle(row)">
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
    />

    <!-- 多步新增 -->
    <el-dialog v-model="visible" title="新增店铺产品登记" width="640px" :close-on-click-modal="false">
      <el-steps :active="step" finish-status="success" simple style="margin-bottom: 16px">
        <el-step title="基本信息" />
        <el-step title="选择规格" />
        <el-step title="售价确认" />
      </el-steps>

      <el-form v-show="step === 0" :model="form" label-width="90px">
        <el-form-item label="店铺" required>
          <el-select v-model="form.shop_id" style="width: 100%">
            <el-option v-for="s in shops" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题关键字" required>
          <el-input v-model="form.title_keyword" placeholder="用于订单反查，尽量唯一" />
        </el-form-item>
        <el-form-item label="链接ID">
          <el-input v-model="form.link_id" />
        </el-form-item>
      </el-form>

      <div v-show="step === 1">
        <el-input v-model="pickerQ" placeholder="搜索编码 / 产品名 / 规格" clearable @input="loadPicker" />
        <el-table
          :data="pickerRows"
          size="small"
          highlight-current-row
          style="margin-top: 8px; max-height: 280px; overflow: auto"
          @current-change="(r: any) => (selected = r)"
        >
          <el-table-column prop="spec_code" label="编码" width="110" />
          <el-table-column prop="product_name" label="产品" min-width="160" show-overflow-tooltip />
          <el-table-column prop="spec_name" label="规格" width="120" />
          <el-table-column label="拿货价" width="100">
            <template #default="{ row }">{{ fmtMoney(row.price) }}</template>
          </el-table-column>
        </el-table>
      </div>

      <el-form v-show="step === 2" :model="form" label-width="90px">
        <el-alert type="info" :closable="false" style="margin-bottom: 12px" :title="`已选规格：${selected?.spec_code || ''} ${selected?.spec_name || ''}`" />
        <el-form-item label="规格售价" required>
          <el-input-number v-model="form.sale_price" :min="0" :precision="2" :step="0.01" style="width: 200px" />
        </el-form-item>
        <el-alert type="warning" :closable="false" show-icon title="同规格多售价将并存，靠订单金额区分" />
      </el-form>

      <template #footer>
        <el-button v-if="step > 0" @click="step--">上一步</el-button>
        <el-button v-if="step < 2" type="primary" :disabled="step === 0 ? !form.shop_id || !form.title_keyword : !selected" @click="step++">
          下一步
        </el-button>
        <el-button v-if="step === 2" type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { masterApi, type ShopProduct, type SpecPickerItem } from '@/api/master'
import { usePageTable } from '@/composables/usePageTable'
import { useAuthStore } from '@/stores/auth'
import { fmtMoney } from '@/utils/format'

const auth = useAuthStore()
const canWrite = computed(() => auth.has('master.shop_product.create'))

const { query, rows, total, loading, search } = usePageTable<ShopProduct>((p) =>
  masterApi.listShopProducts(p),
)

const shops = ref<Array<{ id: number; name: string }>>([])

async function toggle(row: ShopProduct) {
  await masterApi.toggleShopProduct(row.id, row.status === 'active' ? 'disabled' : 'active')
  ElMessage.success('已更新')
  search()
}

// ---- dialog ----
const visible = ref(false)
const step = ref(0)
const saving = ref(false)
const form = reactive({
  shop_id: undefined as number | undefined,
  title_keyword: '',
  link_id: '',
  sale_price: 0,
})
const pickerQ = ref('')
const pickerRows = ref<SpecPickerItem[]>([])
const selected = ref<SpecPickerItem | null>(null)

async function loadPicker() {
  pickerRows.value = await masterApi.specPicker(pickerQ.value || undefined)
}

function openCreate() {
  step.value = 0
  form.shop_id = shops.value[0]?.id
  form.title_keyword = ''
  form.link_id = ''
  form.sale_price = 0
  selected.value = null
  pickerQ.value = ''
  visible.value = true
  loadPicker()
}

async function onSave() {
  if (!selected.value) return
  saving.value = true
  try {
    await masterApi.createShopProduct({
      shop_id: form.shop_id,
      title_keyword: form.title_keyword,
      link_id: form.link_id || null,
      spec_id: selected.value.spec_id,
      sale_price: form.sale_price,
    })
    ElMessage.success('登记成功')
    visible.value = false
    search()
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  shops.value = await masterApi.listShops()
  search()
})
</script>

<style scoped>
.pager {
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
