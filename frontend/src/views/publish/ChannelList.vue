<template>
  <div class="page-container">
    <div class="page-header"><h2>渠道管理</h2><el-button type="primary" @click="showDialog=true">添加渠道</el-button></div>
    <div class="table-card">
      <el-table :data="channels" v-loading="loading" stripe>
        <el-table-column prop="name" label="渠道名称" min-width="150" />
        <el-table-column prop="channel_type" label="类型" width="120" />
        <el-table-column label="级别" width="80"><template #default="{row}"><el-tag size="small">T{{ row.tier }}</el-tag></template></el-table-column>
        <el-table-column label="状态" width="80"><template #default="{row}"><el-tag :type="row.is_active?'success':'info'" size="small">{{ row.is_active?'启用':'停用' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{row}">
            <el-button size="small" @click="editChannel(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="showDialog" :title="editing?'编辑渠道':'添加渠道'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型"><el-input v-model="form.channel_type" /></el-form-item>
        <el-form-item label="级别"><el-input-number v-model="form.tier" :min="1" :max="3" /></el-form-item>
        <el-form-item label="平台"><el-input v-model="form.platform" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { publishApi } from '@/api/review'
const loading = ref(false); const saving = ref(false); const channels = ref<any[]>([])
const showDialog = ref(false); const editing = ref(false); const editId = ref('')
const form = reactive({ name: '', channel_type: '', tier: 1, platform: '' })
async function fetchChannels() { loading.value = true; try { channels.value = await publishApi.listChannels() } catch {}; loading.value = false }
function editChannel(row: any) { editing.value = true; editId.value = row.id; form.name = row.name; form.channel_type = row.channel_type; form.tier = row.tier; form.platform = row.platform || ''; showDialog.value = true }
async function handleSave() {
  saving.value = true
  try {
    if (editing.value) { await publishApi.updateChannel(editId.value, form) } else { await publishApi.createChannel(form) }
    ElMessage.success('保存成功'); showDialog.value = false; fetchChannels()
  } catch (e: any) { ElMessage.error(e.response?.data?.error || '保存失败') }
  saving.value = false
}
async function handleDelete(row: any) { try { await ElMessageBox.confirm('删除此渠道？'); await publishApi.deleteChannel(row.id); ElMessage.success('已删除'); fetchChannels() } catch {} }
onMounted(fetchChannels)
</script>
