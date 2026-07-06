<template>
  <div class="page-container">
    <div class="page-header"><h2>效果录入</h2><el-button type="primary" @click="showDialog=true">录入效果数据</el-button></div>
    <div class="table-card">
      <el-table :data="records" v-loading="loading" stripe>
        <el-table-column prop="recorded_at" label="日期" width="120" />
        <el-table-column prop="impressions" label="曝光量" width="100" />
        <el-table-column prop="clicks" label="点击量" width="100" />
        <el-table-column label="CTR" width="80"><template #default="{row}">{{ row.ctr ? (row.ctr*100).toFixed(2)+'%' : '-' }}</template></el-table-column>
        <el-table-column prop="shares" label="分享" width="80" />
        <el-table-column prop="notes" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="100"><template #default="{row}"><el-button size="small" @click="editRecord(row)">编辑</el-button></template></el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="showDialog" title="录入效果数据" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="稿件ID"><el-input v-model="form.draft_id" /></el-form-item>
        <el-form-item label="渠道ID"><el-input v-model="form.channel_id" /></el-form-item>
        <el-form-item label="日期"><el-date-picker v-model="form.recorded_at" type="date" /></el-form-item>
        <el-form-item label="曝光量"><el-input-number v-model="form.impressions" :min="0" /></el-form-item>
        <el-form-item label="点击量"><el-input-number v-model="form.clicks" :min="0" /></el-form-item>
        <el-form-item label="CTR"><el-input-number v-model="form.ctr" :min="0" :max="1" :step="0.001" /></el-form-item>
        <el-form-item label="分享数"><el-input-number v-model="form.shares" :min="0" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { publishApi } from '@/api/review'
const loading = ref(false); const saving = ref(false); const records = ref<any[]>([]); const showDialog = ref(false)
const today = new Date().toISOString().slice(0,10)
const form = reactive({ draft_id: '', channel_id: '', recorded_at: today, impressions: 0, clicks: 0, ctr: 0, shares: 0, notes: '' })
async function fetchRecords() { loading.value = true; try { const r = await publishApi.listPerformance({ page: 1, page_size: 30 }); records.value = r.items || [] } catch {}; loading.value = false }
function editRecord(row: any) { Object.assign(form, { draft_id: row.draft_id, channel_id: row.channel_id, recorded_at: row.recorded_at, impressions: row.impressions||0, clicks: row.clicks||0, ctr: row.ctr||0, shares: row.shares||0, notes: row.notes||'' }); showDialog.value = true }
async function handleSave() { saving.value = true; try { await publishApi.recordPerformance({ ...form }); ElMessage.success('已录入'); showDialog.value = false; fetchRecords(); Object.assign(form, { draft_id: '', channel_id: '', impressions: 0, clicks: 0, ctr: 0, shares: 0, notes: '' }) } catch (e: any) { ElMessage.error(e.response?.data?.error || '录入失败') }; saving.value = false }
onMounted(fetchRecords)
</script>
