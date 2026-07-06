<template>
  <div class="page-container">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">新建用户</el-button>
    </div>
    <div class="search-bar">
      <el-input v-model="search" placeholder="搜索邮箱或姓名..." style="width: 260px" clearable @clear="fetchUsers" @keyup.enter="fetchUsers" />
      <el-button type="primary" @click="fetchUsers">搜索</el-button>
    </div>
    <div class="table-card">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="display_name" label="姓名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="r in row.roles" :key="r.id" size="small" style="margin-right:4px">{{ r.name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '活跃' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openRoleDialog(row)">角色</el-button>
            <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDeactivate(row)" v-if="row.is_active">禁用</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="total, prev, pager, next" @current-change="fetchUsers" style="margin-top:16px;justify-content:flex-end" />
    </div>

    <el-dialog v-model="showCreateDialog" :title="editingUser ? '编辑用户' : '新建用户'" width="500px">
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="80px">
        <el-form-item label="姓名" prop="display_name"><el-input v-model="userForm.display_name" /></el-form-item>
        <el-form-item label="邮箱" prop="email"><el-input v-model="userForm.email" :disabled="!!editingUser" /></el-form-item>
        <el-form-item label="密码" prop="password" v-if="!editingUser"><el-input v-model="userForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="userForm.phone" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreateDialog=false">取消</el-button><el-button type="primary" @click="handleSaveUser" :loading="saving">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="showRoleDialog" title="分配角色" width="400px">
      <el-checkbox-group v-model="selectedRoleIds">
        <el-checkbox v-for="r in allRoles" :key="r.id" :label="r.id" style="display:block;margin-bottom:8px">{{ r.name }} <span style="color:#909399;font-size:12px">({{ r.code }})</span></el-checkbox>
      </el-checkbox-group>
      <template #footer><el-button @click="showRoleDialog=false">取消</el-button><el-button type="primary" @click="handleAssignRoles" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usersApi } from '@/api/users'
import { rolesApi } from '@/api/roles'
import type { FormInstance } from 'element-plus'

const loading = ref(false); const saving = ref(false)
const users = ref<any[]>([]); const allRoles = ref<any[]>([])
const page = ref(1); const total = ref(0); const search = ref('')
const showCreateDialog = ref(false); const showRoleDialog = ref(false)
const editingUser = ref<any>(null); const roleTargetUser = ref<any>(null)
const selectedRoleIds = ref<string[]>([])
const userFormRef = ref<FormInstance>()
const userForm = reactive({ display_name: '', email: '', password: '', phone: '' })
const userRules = {
  display_name: [{ required: true, message: '请输入姓名' }],
  email: [{ required: true, message: '请输入邮箱' }],
  password: [{ required: true, message: '请输入密码' }, { min: 6, message: '至少6位' }],
}

async function fetchUsers() {
  loading.value = true
  try { const r = await usersApi.list({ page: page.value, page_size: 20, search: search.value || undefined }); users.value = r.items; total.value = r.total } catch {}
  loading.value = false
}
async function fetchRoles() { try { allRoles.value = await rolesApi.list() } catch {} }
async function handleSaveUser() {
  if (!userFormRef.value) return
  if (!(await userFormRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    if (editingUser.value) await usersApi.update(editingUser.value.id, { display_name: userForm.display_name, phone: userForm.phone || undefined })
    else await usersApi.create({ ...userForm, role_ids: [] })
    ElMessage.success(editingUser.value ? '更新成功' : '创建成功')
    showCreateDialog.value = false; resetForm(); fetchUsers()
  } catch (e: any) { ElMessage.error(e.response?.data?.error || '操作失败') }
  saving.value = false
}
function openEditDialog(u: any) { editingUser.value = u; userForm.display_name = u.display_name; userForm.email = u.email; userForm.phone = u.phone || ''; userForm.password = ''; showCreateDialog.value = true }
function openRoleDialog(u: any) { roleTargetUser.value = u; selectedRoleIds.value = u.roles?.map((r: any) => r.id) || []; showRoleDialog.value = true }
async function handleAssignRoles() {
  if (!roleTargetUser.value) return; saving.value = true
  try { await usersApi.assignRoles(roleTargetUser.value.id, selectedRoleIds.value); ElMessage.success('角色已更新'); showRoleDialog.value = false; fetchUsers() }
  catch (e: any) { ElMessage.error(e.response?.data?.error || '操作失败') }
  saving.value = false
}
async function handleDeactivate(u: any) {
  try { await ElMessageBox.confirm(`禁用 "${u.display_name}"？`, '确认', { type: 'warning' }); await usersApi.deactivate(u.id); ElMessage.success('已禁用'); fetchUsers() } catch {}
}
function resetForm() { editingUser.value = null; userForm.display_name = ''; userForm.email = ''; userForm.password = ''; userForm.phone = '' }
onMounted(() => { fetchUsers(); fetchRoles() })
</script>
