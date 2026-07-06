<template>
  <div class="page-container">
    <div class="page-header"><h2>系统监控</h2></div>

    <!-- Health Cards -->
    <div class="stat-cards">
      <div class="stat-card" v-for="c in healthComponents" :key="c.name">
        <div class="stat-label">{{ c.name }}</div>
        <div class="stat-value" :style="{color: c.status==='healthy'?'#67c23a':'#f56c6c'}">{{ c.status === 'healthy' ? '正常' : '异常' }}</div>
      </div>
    </div>

    <!-- Task Stats -->
    <div class="detail-section" v-if="taskStats">
      <div class="section-title">任务统计</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="失败发布"><el-tag type="danger">{{ taskStats.failed_publishes }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="活跃探测任务">{{ taskStats.active_detection_tasks }}</el-descriptions-item>
        <el-descriptions-item label="告警数"><el-tag :type="taskStats.alerts>0?'danger':'success'">{{ taskStats.alerts }}</el-tag></el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- Usage Stats -->
    <div class="detail-section" v-if="usageStats">
      <div class="section-title">资源用量</div>
      <el-row :gutter="16">
        <el-col :span="6" v-for="u in usageList" :key="u.label">
          <div class="stat-card"><div class="stat-label">{{ u.label }}</div><div class="stat-value">{{ u.value }}</div></div>
        </el-col>
      </el-row>
    </div>

    <!-- Operation Logs -->
    <div class="detail-section">
      <div class="section-title">操作日志</div>
      <div class="search-bar">
        <el-select v-model="filterResource" placeholder="模块筛选" clearable @change="fetchLogs" style="width:160px">
          <el-option label="知识库" value="kb" /><el-option label="内容" value="content" />
          <el-option label="审核" value="review" /><el-option label="发布" value="publish" />
        </el-select>
      </div>
      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="action" label="操作" min-width="200" />
        <el-table-column prop="resource_type" label="模块" width="100" />
        <el-table-column prop="created_at" label="时间" width="180"><template #default="{row}">{{ formatDate(row.created_at) }}</template></el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import http from '@/api/index'
import { formatDate } from '@/utils/format'

const loading = ref(false)
const healthComponents = ref<any[]>([])
const taskStats = ref<any>(null)
const usageStats = ref<any>(null)
const logs = ref<any[]>([])
const filterResource = ref('')

const usageList = computed(() => {
  if (!usageStats.value) return []
  return [
    { label: '知识库资产', value: usageStats.value.kb_assets },
    { label: '内容稿件', value: usageStats.value.content_drafts },
    { label: '探测结果', value: usageStats.value.detection_results },
    { label: '总操作数', value: usageStats.value.total_operations },
  ]
})

async function fetchHealth() {
  try { const r = await http.get('/p2/monitor/health'); healthComponents.value = Object.entries(r.data.components).map(([k,v]) => ({name:k,status:v})) } catch {}
}
async function fetchTaskStats() { try { taskStats.value = (await http.get('/p2/monitor/tasks')).data } catch {} }
async function fetchUsage() { try { usageStats.value = (await http.get('/p2/monitor/usage')).data } catch {} }
async function fetchLogs() {
  loading.value = true
  try { const r = await http.get('/p2/operation-logs', { params: { page: 1, page_size: 20, resource_type: filterResource.value || undefined } }); logs.value = r.data.items } catch {}
  loading.value = false
}

onMounted(() => { fetchHealth(); fetchTaskStats(); fetchUsage(); fetchLogs() })
</script>
