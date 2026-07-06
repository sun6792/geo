<template>
  <div class="page-container">
    <div class="page-header">
      <h2>客户管理</h2>
      <el-button type="primary" @click="showCreate=true">新建客户</el-button>
    </div>
    <div class="search-bar">
      <el-input v-model="search" placeholder="搜索客户名称..." style="width:260px" clearable @clear="fetchCustomers" @keyup.enter="fetchCustomers" />
      <el-button type="primary" @click="fetchCustomers">搜索</el-button>
    </div>
    <div class="table-card">
      <el-table :data="customers" v-loading="loading" stripe>
        <el-table-column prop="name" label="客户名称" min-width="150" />
        <el-table-column prop="company_name" label="公司名" min-width="150" />
        <el-table-column prop="industry" label="行业" width="100" />
        <el-table-column label="套餐" width="100">
          <template #default="{row}"><el-tag size="small">{{ row.subscription_tier }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{row}"><el-tag :type="row.status==='active'?'success':row.status==='suspended'?'danger':'info'" size="small">{{ row.status==='active'?'正常':row.status==='suspended'?'停用':'--' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{row}">{{ row.created_at?.slice(0,10) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{row}">
            <el-button size="small" @click="editCustomer(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleSuspend(row)" v-if="row.status==='active'">停用</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="total, prev, pager, next" @current-change="fetchCustomers" style="margin-top:16px;justify-content:flex-end" />
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showCreate" :title="editing?'编辑客户':'新建客户'" width="550px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="客户名称" prop="name"><el-input v-model="form.name" placeholder="如：XX科技有限公司" /></el-form-item>
        <el-form-item label="URL标识" prop="slug"><el-input v-model="form.slug" placeholder="如：xx-tech" :disabled="editing" /></el-form-item>
        <el-form-item label="公司全称"><el-input v-model="form.company_name" placeholder="营业执照上的公司全称" /></el-form-item>
        <el-form-item label="行业" prop="industry">
          <el-select v-model="form.industry" style="width:100%">
            <el-option label="制造业" value="manufacturing" /><el-option label="本地服务" value="local_service" />
            <el-option label="电商" value="ecommerce" /><el-option label="教育" value="education" />
            <el-option label="医疗健康" value="healthcare" /><el-option label="科技" value="technology" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人邮箱" prop="owner_email"><el-input v-model="form.owner_email" /></el-form-item>
        <el-form-item label="套餐档位">
          <el-select v-model="form.subscription_tier" style="width:100%">
            <el-option label="基础版 ¥999/月" value="basic" />
            <el-option label="专业版 ¥2,999/月" value="professional" />
            <el-option label="企业版 ¥8,999/月" value="enterprise" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户上限"><el-input-number v-model="form.max_users" :min="1" :max="9999" /></el-form-item>
        <el-form-item label="资产上限"><el-input-number v-model="form.max_kb_assets" :min="100" :max="99999" /></el-form-item>
        <el-form-item label="月内容量"><el-input-number v-model="form.max_content_per_month" :min="10" :max="9999" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api/index'
import type { FormInstance } from 'element-plus'

const loading = ref(false); const saving = ref(false)
const customers = ref<any[]>([]); const page = ref(1); const total = ref(0); const search = ref('')
const showCreate = ref(false); const editing = ref(false); const editId = ref('')
const formRef = ref<FormInstance>()

const form = reactive({
  name: '', slug: '', company_name: '', industry: '', owner_email: '',
  subscription_tier: 'professional', max_users: 10, max_kb_assets: 2000, max_content_per_month: 200
})
const rules = {
  name: [{ required: true, message: '请输入客户名称' }],
  slug: [{ required: true, message: '请输入URL标识' }, { pattern: /^[a-z0-9-]+$/, message: '仅小写字母数字和连字符' }],
  owner_email: [{ required: true, message: '请输入负责人邮箱' }],
  industry: [{ required: true, message: '请选择行业' }],
}

async function fetchCustomers() {
  loading.value = true
  try {
    const r = await http.get('/customers/', { params: { page: page.value, page_size: 20, search: search.value || undefined } })
    customers.value = r.data.items || []; total.value = r.data.total || 0
  } catch {}
  loading.value = false
}

function editCustomer(row: any) {
  editing.value = true; editId.value = row.id
  Object.assign(form, {
    name: row.name, slug: row.slug, company_name: row.company_name || '', industry: row.industry || '',
    owner_email: row.owner_email, subscription_tier: row.subscription_tier || 'professional',
    max_users: row.max_users || 10, max_kb_assets: row.max_kb_assets || 2000, max_content_per_month: row.max_content_per_month || 200
  })
  showCreate.value = true
}

async function handleSave() {
  if (!formRef.value) return
  if (!(await formRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    if (editing.value) {
      await http.patch('/customers/' + editId.value, form)
    } else {
      await http.post('/customers/', form)
    }
    ElMessage.success(editing.value ? '已更新' : '客户已创建'); showCreate.value = false
    editing.value = false; editId.value = ''
    Object.assign(form, { name: '', slug: '', company_name: '', industry: '', owner_email: '', subscription_tier: 'professional', max_users: 10, max_kb_assets: 2000, max_content_per_month: 200 })
    fetchCustomers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '保存失败')
  }
  saving.value = false
}

async function handleSuspend(row: any) {
  try {
    await ElMessageBox.confirm('确定停用该客户？', '确认', { type: 'warning' })
    await http.patch('/customers/' + row.id, { status: 'suspended' })
    ElMessage.success('已停用'); fetchCustomers()
  } catch {}
}

onMounted(fetchCustomers)
</script>
