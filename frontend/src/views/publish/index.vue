<template>
  <div class="page-container">
    <div class="page-header">
      <h2>发布管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="openCreateDialog">新建发布排期</el-button>
        <el-button @click="$router.push('/publish/channels')">渠道管理</el-button>
      </div>
    </div>
    <el-tabs v-model="activeTab" @tab-change="fetchData">
      <el-tab-pane label="待发布" name="scheduled" />
      <el-tab-pane label="已发布" name="published" />
      <el-tab-pane label="发布失败" name="failed" />
    </el-tabs>
    <div class="table-card">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column label="稿件标题" min-width="180">
          <template #default="{row}">{{ row.draft_title || row.draft_id }}</template>
        </el-table-column>
        <el-table-column label="渠道" width="140">
          <template #default="{row}">{{ row.channel_name || row.channel_id }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{row}"><el-tag :type="row.status==='published'?'success':row.status==='failed'?'danger':'warning'" size="small">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="scheduled_at" label="计划时间" width="160">
          <template #default="{row}">{{ row.scheduled_at?.slice(0,16) || '即时' }}</template>
        </el-table-column>
        <el-table-column prop="published_url" label="发布链接" min-width="200">
          <template #default="{row}">
            <a v-if="row.published_url" :href="row.published_url" target="_blank" style="color:#409eff">{{ row.published_url }}</a>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{row}">
            <el-button size="small" type="success" v-if="row.status==='scheduled'" @click="handlePublish(row)">立即发布</el-button>
            <el-button size="small" v-if="row.status==='failed'" @click="handleRetry(row)">重试</el-button>
            <el-button size="small" type="danger" @click="handleCancel(row)" v-if="row.status==='scheduled'">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建发布排期弹窗 -->
    <el-dialog v-model="showCreate" title="新建发布排期" width="500px">
      <el-form :model="publishForm" label-width="80px">
        <el-form-item label="选择稿件">
          <el-select v-model="publishForm.draft_id" filterable placeholder="搜索已审核通过的稿件" style="width:100%">
            <el-option v-for="d in approvedDrafts" :key="d.id" :label="d.title" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="发布渠道">
          <el-select v-model="publishForm.channel_id" placeholder="选择渠道" style="width:100%">
            <el-option v-for="c in channelList" :key="c.id" :label="c.name + ' (T' + c.tier + ')'" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="发布链接">
          <el-input v-model="publishForm.published_url" placeholder="手动填写落地页URL（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate=false">取消</el-button>
        <el-button type="primary" @click="handleCreateSchedule" :loading="publishing">提交排期</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { publishApi } from '@/api/review'
import { reviewApi } from '@/api/review'
import http from '@/api/index'

const loading = ref(false); const publishing = ref(false)
const items = ref<any[]>([]); const activeTab = ref('scheduled')
const showCreate = ref(false)
const approvedDrafts = ref<any[]>([])
const channelList = ref<any[]>([])
const publishForm = reactive({ draft_id: '', channel_id: '', published_url: '' })

async function fetchData() {
  loading.value = true
  try { const r = await publishApi.listSchedules({ status: activeTab.value }); items.value = Array.isArray(r) ? r : (r.items || []) } catch {}
  loading.value = false
}

async function openCreateDialog() {
  showCreate.value = true
  // Load approved drafts (those past client review)
  try {
    const reviews = await reviewApi.list({ status: 'approved' })
    const draftIds = [...new Set((Array.isArray(reviews) ? reviews : []).map((r:any) => r.draft_id))]
    approvedDrafts.value = draftIds.map((id: string) => ({ id, title: `稿件 ${id.slice(0,8)}...` }))
  } catch { approvedDrafts.value = [] }
  // Load channels
  try { channelList.value = await publishApi.listChannels() } catch { channelList.value = [] }
}

async function handleCreateSchedule() {
  if (!publishForm.draft_id || !publishForm.channel_id) {
    ElMessage.warning('请选择稿件和渠道'); return
  }
  publishing.value = true
  try {
    const schedule = await publishApi.createSchedule({
      draft_id: publishForm.draft_id,
      channel_id: publishForm.channel_id,
      scheduled_at: new Date().toISOString(),
      created_by: '',
    })
    // Immediately mark as published with the manual URL
    await publishApi.publishNow(schedule.id, { published_url: publishForm.published_url || undefined })
    ElMessage.success('发布成功！')
    showCreate.value = false
    publishForm.draft_id = ''; publishForm.channel_id = ''; publishForm.published_url = ''
    fetchData()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || e.response?.data?.error || '发布失败') }
  publishing.value = false
}

async function handlePublish(row: any) {
  try {
    await publishApi.publishNow(row.id)
    ElMessage.success('已发布')
    fetchData()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '发布失败') }
}
async function handleRetry(row: any) { try { await publishApi.publishNow(row.id); ElMessage.success('重试成功'); fetchData() } catch (e: any) { ElMessage.error(e.response?.data?.error || '重试失败') } }
async function handleCancel(row: any) { try { await publishApi.cancelSchedule(row.id); ElMessage.success('已取消'); fetchData() } catch {} }
onMounted(fetchData)
</script>
<style scoped>
.header-actions { display: flex; gap: 10px; }
</style>
