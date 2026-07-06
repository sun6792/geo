<template>
  <div class="page-container">
    <div class="page-header">
      <h2>短板诊断分析 (智能体 2)</h2>
      <el-button type="primary" @click="generateReport" :loading="generating">生成新诊断报告</el-button>
    </div>

    <!-- Latest Report Summary -->
    <div class="detail-section" v-if="latestReport">
      <div class="section-title">{{ latestReport.title }}</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="诊断周期">{{ latestReport.diagnosis_period_start }} ~ {{ latestReport.diagnosis_period_end }}</el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="latestReport.status==='published'?'success':'info'">{{ latestReport.status }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="生成时间">{{ formatDate(latestReport.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top:16px;white-space:pre-wrap">{{ latestReport.summary }}</div>
    </div>

    <!-- Five-Dim Radar Chart -->
    <div class="detail-section" v-if="scores.length > 0">
      <div class="section-title">五维权重评分</div>
      <el-table :data="scores" stripe>
        <el-table-column prop="model_name" label="模型/总体" width="120">
          <template #default="{row}">{{ row.model_name || '总体评分' }}</template>
        </el-table-column>
        <el-table-column label="身份权重" width="100"><template #default="{row}">
          <el-progress :percentage="row.identity_score" :color="scoreColor(row.identity_score)" /></template></el-table-column>
        <el-table-column label="信源权重" width="100"><template #default="{row}">
          <el-progress :percentage="row.source_score" :color="scoreColor(row.source_score)" /></template></el-table-column>
        <el-table-column label="内容深度" width="100"><template #default="{row}">
          <el-progress :percentage="row.content_depth_score" :color="scoreColor(row.content_depth_score)" /></template></el-table-column>
        <el-table-column label="新鲜度" width="100"><template #default="{row}">
          <el-progress :percentage="row.content_freshness_score" :color="scoreColor(row.content_freshness_score)" /></template></el-table-column>
        <el-table-column label="交叉校验" width="100"><template #default="{row}">
          <el-progress :percentage="row.cross_validation_score" :color="scoreColor(row.cross_validation_score)" /></template></el-table-column>
        <el-table-column label="总分" width="80">
          <template #default="{row}"><b :style="{color:scoreColor(row.total_score)}">{{ row.total_score }}</b></template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Optimization Items -->
    <div class="detail-section">
      <div class="section-title">优化任务清单</div>
      <el-table :data="optimizationItems" stripe>
        <el-table-column label="优先级" width="80">
          <template #default="{row}"><el-tag :type="priorityType(row.priority)" size="small">{{ priorityLabel(row.priority) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="title" label="任务" min-width="200" />
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{row}">{{ categoryLabel(row.category) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{row}"><el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="目标模型" width="100"><template #default="{row}">{{ row.target_model || '--' }}</template></el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{row}">
            <el-button size="small" v-if="row.status==='pending'" @click="updateStatus(row,'in_progress')">开始</el-button>
            <el-button size="small" type="success" v-if="row.status==='in_progress'" @click="updateStatus(row,'completed')">完成</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- History Reports -->
    <div class="detail-section">
      <div class="section-title">历史诊断报告</div>
      <el-table :data="reports" v-loading="loading" stripe @row-click="viewReport">
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="report_type" label="类型" width="100" />
        <el-table-column prop="diagnosis_period_start" label="开始日期" width="120" />
        <el-table-column prop="diagnosis_period_end" label="结束日期" width="120" />
        <el-table-column prop="status" label="状态" width="80" />
        <el-table-column prop="created_at" label="生成时间" width="160"><template #default="{row}">{{ formatDate(row.created_at) }}</template></el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { diagnosisApi } from '@/api/detection'
import { formatDate } from '@/utils/format'

const loading = ref(false); const generating = ref(false)
const reports = ref<any[]>([]); const latestReport = ref<any>(null)
const scores = ref<any[]>([]); const optimizationItems = ref<any[]>([])

function scoreColor(s: number) { return s >= 70 ? '#67c23a' : s >= 40 ? '#e6a23c' : '#f56c6c' }
function priorityType(p: string) { return { urgent: 'danger', important: 'warning', long_term: 'info' }[p] || 'info' }
function priorityLabel(p: string) { return { urgent: '紧急', important: '重要', long_term: '长期' }[p] || p }
function categoryLabel(c: string) { return { kb_gap: '知识库缺口', content_creation: '内容创作', channel_expansion: '渠道扩展', rule_update: '规则更新' }[c] || c }
function statusType(s: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  return { pending: 'info', in_progress: 'warning', completed: 'success', skipped: '' }[s] as any || 'info'
}

async function fetchReports() {
  loading.value = true
  try { const r = await diagnosisApi.listReports({ page: 1, page_size: 20 }); reports.value = r.items; latestReport.value = r.items[0] || null } catch {}
  loading.value = false
}
async function fetchItems() { try { optimizationItems.value = await diagnosisApi.listOptimizationItems() } catch {} }
async function generateReport() {
  generating.value = true
  try {
    const result = await diagnosisApi.generateReport()
    ElMessage.success('诊断报告已生成')
    await fetchReports()   // Must await before fetchScores depends on latestReport
    await fetchItems()
    if (result?.id) { scores.value = await diagnosisApi.getScores(result.id) }
  } catch (e: any) { ElMessage.error(e.response?.data?.error || '生成失败') }
  generating.value = false
}
async function fetchScores() {
  if (!latestReport.value) return
  try { scores.value = await diagnosisApi.getScores(latestReport.value.id) } catch {}
}
async function updateStatus(item: any, status: string) {
  try { await diagnosisApi.updateOptimizationItem(item.id, { status }); fetchItems() } catch (e: any) { ElMessage.error(e.response?.data?.error || '更新失败') }
}
function viewReport(r: any) { latestReport.value = r; fetchScoresForReport(r.id) }
async function fetchScoresForReport(id: string) { try { scores.value = await diagnosisApi.getScores(id) } catch {} }

onMounted(async () => { await fetchReports(); fetchItems(); if (latestReport.value) fetchScores() })
</script>
