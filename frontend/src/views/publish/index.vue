<template>
  <div class="page-container">
    <div class="page-header">
      <h2>发布管理</h2>
      <el-button type="primary" @click="$router.push('/publish/channels')">渠道管理</el-button>
    </div>
    <el-tabs v-model="activeTab" @tab-change="fetchData">
      <el-tab-pane label="待发布" name="scheduled" />
      <el-tab-pane label="已发布" name="published" />
      <el-tab-pane label="发布失败" name="failed" />
    </el-tabs>
    <div class="table-card">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="draft_id" label="稿件ID" width="120" show-overflow-tooltip />
        <el-table-column prop="channel_id" label="渠道" width="120" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{row}"><el-tag :type="row.status==='published'?'success':row.status==='failed'?'danger':'warning'" size="small">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="scheduled_at" label="计划时间" width="170">
          <template #default="{row}">{{ row.scheduled_at?.slice(0,16) || '-' }}</template>
        </el-table-column>
        <el-table-column prop="published_url" label="发布链接" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="160">
          <template #default="{row}">
            <el-button size="small" type="success" v-if="row.status==='scheduled'" @click="handlePublish(row)">立即发布</el-button>
            <el-button size="small" v-if="row.status==='failed'" @click="handleRetry(row)">重试</el-button>
            <el-button size="small" type="danger" @click="handleCancel(row)" v-if="row.status==='scheduled'">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { publishApi } from '@/api/review'
const loading = ref(false); const items = ref<any[]>([]); const activeTab = ref('scheduled')
async function fetchData() {
  loading.value = true
  try { const r = await publishApi.listSchedules({ status: activeTab.value === 'published' ? 'published' : activeTab.value === 'failed' ? 'failed' : 'scheduled' }); items.value = Array.isArray(r) ? r : (r.items || []) } catch {}
  loading.value = false
}
async function handlePublish(row: any) { try { await publishApi.publishNow(row.id); ElMessage.success('已发布'); fetchData() } catch (e: any) { ElMessage.error(e.response?.data?.error || '发布失败') } }
async function handleRetry(row: any) { try { await publishApi.publishNow(row.id); ElMessage.success('重试成功'); fetchData() } catch (e: any) { ElMessage.error(e.response?.data?.error || '重试失败') } }
async function handleCancel(row: any) { try { await publishApi.cancelSchedule(row.id); ElMessage.success('已取消'); fetchData() } catch {} }
onMounted(fetchData)
</script>
