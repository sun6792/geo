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
        <el-table-column label="服务期限" width="170">
          <template #default="{row}">{{ row.service_start || '-' }} ~ {{ row.service_end || '-' }}</template>
        </el-table-column>
        <el-table-column label="套餐" width="100">
          <template #default="{row}"><el-tag size="small">{{ row.subscription_tier }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{row}"><el-tag :type="row.status==='active'?'success':row.status==='suspended'?'danger':'info'" size="small">{{ row.status==='active'?'正常':row.status==='suspended'?'停用':'--' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{row}">{{ row.created_at?.slice(0,10) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{row}">
            <el-button size="small" type="success" @click="$router.push('/knowledge-base?cid='+row.id)">知识库</el-button>
            <el-button size="small" @click="editCustomer(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleSuspend(row)" v-if="row.status==='active'">停用</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)" v-if="row.status!=='active'">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="total, prev, pager, next" @current-change="fetchCustomers" style="margin-top:16px;justify-content:flex-end" />
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showCreate" :title="editing?'编辑客户':'新建客户'" width="550px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="客户名称" prop="name"><el-input v-model="form.name" placeholder="如：XX科技有限公司" /></el-form-item>
        <el-form-item label="URL标识" prop="slug"><el-input v-model="form.slug" placeholder="英文标识，留空自动生成" :disabled="editing" /></el-form-item>
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
        <el-form-item label="服务档位" prop="plan_id">
          <el-select v-model="form.plan_id" style="width:100%" @change="onPlanChange" placeholder="选择服务档位">
            <el-option v-for="p in planList" :key="p.id" :label="p.name + ' ¥' + (p.monthly_price||0) + '/' + (p.code.includes('yearly')||p.code.includes('y')?'年':'月')" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务开始"><el-date-picker v-model="form.service_start" type="date" style="width:100%" placeholder="选择开始日期" /></el-form-item>
        <el-form-item label="服务到期"><el-date-picker v-model="form.service_end" type="date" style="width:100%" placeholder="选择到期日期" /></el-form-item>
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

const planList = ref<any[]>([])
const form = reactive({
  name: '', slug: '', company_name: '', industry: '', owner_email: '',
  subscription_tier: 'professional', plan_id: '' as string, service_start: '' as string, service_end: '' as string,
  max_users: 10, max_kb_assets: 2000, max_content_per_month: 200
})

function onPlanChange(planId: string) {
  const plan = planList.value.find((p:any) => p.id === planId)
  if (plan) {
    form.subscription_tier = plan.code
    form.max_kb_assets = plan.quotas?.kb_assets || 500
    form.max_content_per_month = plan.quotas?.content || 50
    form.max_users = Math.max(5, Math.floor((plan.quotas?.kb_assets || 500) / 100))
  }
}

async function loadPlans() {
  try { const r = await http.get('/billing/plans'); planList.value = (r.data || []).filter((p:any) => p.is_active) } catch {}
}
const rules = {
  name: [{ required: true, message: '请输入客户名称' }],
  slug: [{ pattern: /^[a-z0-9-]+$/, message: '仅小写字母数字和连字符，留空自动生成' }],
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
    plan_id: row.plan_id || '', service_start: row.service_start || '', service_end: row.service_end || '',
    max_users: row.max_users || 10, max_kb_assets: row.max_kb_assets || 2000, max_content_per_month: row.max_content_per_month || 200
  })
  showCreate.value = true
}

async function handleSave() {
  if (!formRef.value) return
  if (!(await formRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    // Clean: remove empty strings for optional fields
    const data: any = { ...form }
    if (!data.plan_id) data.plan_id = null
    if (!data.service_start) data.service_start = null
    if (!data.service_end) data.service_end = null
    if (!data.slug && data.name) {
      data.slug = data.name.replace(/[^\w]/g, '').toLowerCase().slice(0, 20) || 'client' + Date.now().toString(36)
    }
    // Convert Date objects to ISO date strings
    if (data.service_start instanceof Date) data.service_start = data.service_start.toISOString().slice(0,10)
    if (data.service_end instanceof Date) data.service_end = data.service_end.toISOString().slice(0,10)
    // Remove null values for optional fields
    if (!data.company_name) data.company_name = null
    if (!data.industry) data.industry = null
    if (editing.value) {
      await http.patch('/customers/' + editId.value, data)
    } else {
      await http.post('/customers/', data)
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
    if (row.status === 'active') {
      await ElMessageBox.confirm('停用后该客户账号将无法登录。确定？', '确认', { type: 'warning' })
      await http.patch('/customers/' + row.id, { status: 'suspended' })
      ElMessage.success('已停用')
    } else {
      await http.patch('/customers/' + row.id, { status: 'active' })
      ElMessage.success('已重新激活')
    }
    fetchCustomers()
  } catch {}
}
async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm('永久删除该客户及所有关联数据！不可恢复！', '危险操作', { type: 'error' })
    await http.delete('/customers/' + row.id)
    ElMessage.success('已删除'); fetchCustomers()
  } catch {}
}

onMounted(() => { fetchCustomers(); loadPlans() })
</script>
