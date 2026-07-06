<template>
  <div class="page-container">
    <div class="page-header"><h2>子账号管理</h2><el-button type="primary" @click="showCreate=true">新建子账号</el-button></div>
    <div class="table-card">
      <el-table :data="accounts" v-loading="loading" stripe>
        <el-table-column prop="email" label="登录邮箱" min-width="180" />
        <el-table-column prop="company_name" label="企业名称" min-width="150" />
        <el-table-column prop="service_start" label="服务起始" width="120" />
        <el-table-column prop="service_end" label="到期日" width="120" />
        <el-table-column label="状态" width="80">
          <template #default="{row}"><el-tag :type="row.is_active?'success':'danger'" size="small">{{ row.is_active?'正常':'停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{row}">
            <el-button size="small" @click="handleReset(row)">重置密码</el-button>
            <el-button size="small" :type="row.is_active?'danger':'success'" @click="handleToggle(row)">{{ row.is_active?'停用':'启用' }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="showCreate" title="新建子账号" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="客户ID"><el-input v-model="form.customer_id" placeholder="关联客户UUID" /></el-form-item>
        <el-form-item label="登录邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="显示名称"><el-input v-model="form.display_name" /></el-form-item>
        <el-form-item label="企业名称"><el-input v-model="form.company_name" /></el-form-item>
        <el-form-item label="服务起始"><el-date-picker v-model="form.service_start" type="date" style="width:100%" /></el-form-item>
        <el-form-item label="到期日"><el-date-picker v-model="form.service_end" type="date" style="width:100%" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="handleCreate" :loading="saving">创建</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api/index'
const loading = ref(false); const saving = ref(false); const accounts = ref<any[]>([]); const showCreate = ref(false)
const today = new Date().toISOString().slice(0,10)
const form = reactive({ customer_id: '', email: '', display_name: '', company_name: '', service_start: today, service_end: '' })
async function fetchAccounts() { loading.value = true; try { const r = await http.get('/p5/sub-accounts', { params: { page: 1, page_size: 50 } }); accounts.value = r.data.items || [] } catch {}; loading.value = false }
async function handleCreate() { saving.value = true; try { const r = await http.post('/p5/sub-accounts', form); ElMessage.success('创建成功！密码: ' + r.data.password); showCreate.value = false; fetchAccounts() } catch (e: any) { ElMessage.error(e.response?.data?.error || '创建失败') }; saving.value = false }
async function handleReset(row: any) { try { const r = await http.post('/p5/sub-accounts/' + row.id + '/reset-password'); ElMessage.success('新密码: ' + r.data.new_password) } catch {} }
async function handleToggle(row: any) { try { await http.patch('/p5/sub-accounts/' + row.id, { is_active: !row.is_active }); ElMessage.success('已' + (row.is_active ? '停用' : '启用')); fetchAccounts() } catch {} }
onMounted(fetchAccounts)
</script>
