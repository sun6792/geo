<template>
  <div class="page-container">
    <div class="page-header">
      <h2>角色管理</h2>
      <el-button type="primary" @click="openCreateDialog">新建角色</el-button>
    </div>
    <div class="table-card">
      <el-table :data="roles" v-loading="loading" stripe>
        <el-table-column prop="name" label="角色名称" min-width="150" />
        <el-table-column prop="code" label="角色编码" width="150" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="系统角色" width="100">
          <template #default="{ row }"><el-tag :type="row.is_system ? 'info' : ''" size="small">{{ row.is_system ? '是' : '否' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="权限数" width="80">
          <template #default="{ row }">{{ row.permissions?.length || 0 }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openPermissionDialog(row)">权限</el-button>
            <el-button size="small" @click="openEditDialog(row)" :disabled="row.is_system">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)" :disabled="row.is_system">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create/Edit Role Dialog -->
    <el-dialog v-model="showDialog" :title="editingRole ? '编辑角色' : '新建角色'" width="500px">
      <el-form ref="roleFormRef" :model="roleForm" :rules="roleRules" label-width="80px">
        <el-form-item label="名称" prop="name"><el-input v-model="roleForm.name" /></el-form-item>
        <el-form-item label="编码" prop="code"><el-input v-model="roleForm.code" :disabled="!!editingRole" placeholder="如: custom_editor" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="roleForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSaveRole" :loading="saving">保存</el-button></template>
    </el-dialog>

    <!-- Permission Assignment Dialog -->
    <el-dialog v-model="showPermDialog" title="配置权限" width="600px">
      <el-checkbox-group v-model="selectedPermIds">
        <div v-for="group in permissionGroups" :key="group.resource" style="margin-bottom:16px">
          <h4 style="margin-bottom:8px;color:#303133">{{ group.label }}</h4>
          <el-checkbox v-for="p in group.permissions" :key="p.id" :label="p.id" style="margin-right:16px;margin-bottom:4px">
            {{ p.action }} <span style="color:#909399;font-size:12px">({{ p.code }})</span>
          </el-checkbox>
        </div>
      </el-checkbox-group>
      <template #footer><el-button @click="showPermDialog=false">取消</el-button><el-button type="primary" @click="handleSavePermissions" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { rolesApi, permissionsApi } from '@/api/roles'
import type { FormInstance } from 'element-plus'

const loading = ref(false); const saving = ref(false)
const roles = ref<any[]>([]); const allPermissions = ref<any[]>([])
const showDialog = ref(false); const showPermDialog = ref(false)
const editingRole = ref<any>(null); const permTargetRole = ref<any>(null)
const selectedPermIds = ref<string[]>([])
const roleFormRef = ref<FormInstance>()
const roleForm = reactive({ name: '', code: '', description: '' })
const roleRules = {
  name: [{ required: true, message: '请输入角色名称' }],
  code: [{ required: true, message: '请输入角色编码' }, { pattern: /^[a-z_]+$/, message: '仅支持小写字母和下划线' }],
}

const permissionGroups = computed(() => {
  const groups: Record<string, any> = {}
  for (const p of allPermissions.value) {
    if (!groups[p.resource]) groups[p.resource] = { resource: p.resource, label: resourceLabel(p.resource), permissions: [] }
    groups[p.resource].permissions.push(p)
  }
  return Object.values(groups)
})

function resourceLabel(r: string): string {
  const map: Record<string, string> = { customer: '客户管理', account: '账号管理', kb: '知识库', content: '内容创作', review: '内容审核', publish: '发布管理', system: '系统管理' }
  return map[r] || r
}

async function fetchRoles() { loading.value = true; try { roles.value = await rolesApi.list() } catch {} loading.value = false }
async function fetchPermissions() { try { allPermissions.value = await permissionsApi.list() } catch {} }

function openCreateDialog() { editingRole.value = null; roleForm.name = ''; roleForm.code = ''; roleForm.description = ''; showDialog.value = true }
function openEditDialog(r: any) { editingRole.value = r; roleForm.name = r.name; roleForm.code = r.code; roleForm.description = r.description || ''; showDialog.value = true }

async function handleSaveRole() {
  if (!roleFormRef.value || !(await roleFormRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    if (editingRole.value) await rolesApi.update(editingRole.value.id, { name: roleForm.name, description: roleForm.description || undefined })
    else await rolesApi.create({ name: roleForm.name, code: roleForm.code, description: roleForm.description || undefined })
    ElMessage.success('保存成功'); showDialog.value = false; fetchRoles()
  } catch (e: any) { ElMessage.error(e.response?.data?.error || '操作失败') }
  saving.value = false
}

function openPermissionDialog(r: any) { permTargetRole.value = r; selectedPermIds.value = r.permissions?.map((p: any) => p.id) || []; showPermDialog.value = true }
async function handleSavePermissions() {
  if (!permTargetRole.value) return; saving.value = true
  try { await rolesApi.setPermissions(permTargetRole.value.id, selectedPermIds.value); ElMessage.success('权限已更新'); showPermDialog.value = false; fetchRoles() }
  catch (e: any) { ElMessage.error(e.response?.data?.error || '操作失败') }
  saving.value = false
}

async function handleDelete(r: any) {
  try { await ElMessageBox.confirm(`删除角色 "${r.name}"？`, '确认', { type: 'warning' }); await rolesApi.delete(r.id); ElMessage.success('已删除'); fetchRoles() } catch {}
}

onMounted(() => { fetchRoles(); fetchPermissions() })
</script>
