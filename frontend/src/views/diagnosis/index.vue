<template>
  <div class="page-container">
    <div class="page-header">
      <h2>短板诊断分析</h2>
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
      <div class="section-title">
        优化任务清单
        <el-button type="success" size="small" @click="convertToContent" :loading="converting" :disabled="selectedGaps.length===0" style="margin-left:16px">
          一键生成内容 (已选{{ selectedGaps.length }})
        </el-button>
      </div>
      <el-table :data="optimizationItems" stripe @selection-change="onSelectGaps" ref="gapTable">
        <el-table-column type="selection" width="45" />
        <el-table-column label="优先级" width="80">
          <template #default="{row}"><el-tag :type="priorityType(row.priority)" size="small">{{ priorityLabel(row.priority) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="name" label="缺口名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="layer" label="层级" width="90">
          <template #default="{row}">{{ layerLabel(row.layer) }}</template>
        </el-table-column>
        <el-table-column label="影响" width="70">
          <template #default="{row}"><el-progress :percentage="row.impact_weight||0" :stroke-width="6" :color="row.impact_weight>60?'#f56c6c':'#e6a23c'" /></template>
        </el-table-column>
        <el-table-column label="影响模型" width="140">
          <template #default="{row}">{{ (row.affected_models||[]).join(', ') || '全部' }}</template>
        </el-table-column>
        <el-table-column label="预估提升" width="90">
          <template #default="{row}"><el-tag size="small">{{ row.estimated_impact || '--' }}</el-tag></template>
        </el-table-column>
      </el-table>
    </div>

    <!-- History Reports -->
    <div class="detail-section">
      <div class="section-title">历史诊断报告</div>
      <el-table :data="reports" v-loading="loading" stripe @row-click="viewReport" style="cursor:pointer">
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="report_type" label="类型" width="100" />
        <el-table-column prop="diagnosis_period_start" label="开始日期" width="120" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{row}"><el-tag :type="row.status==='published'?'success':'info'" size="small">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="160"><template #default="{row}">{{ formatDate(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{row}">
            <el-button size="small" type="primary" @click.stop="viewReport(row)">查看</el-button>
            <el-button size="small" type="danger" @click.stop="deleteReport(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { diagnosisApi } from '@/api/detection'
import { formatDate } from '@/utils/format'
import http from '@/api/index'

const loading = ref(false); const generating = ref(false); const converting = ref(false)
const reports = ref<any[]>([]); const latestReport = ref<any>(null)
const scores = ref<any[]>([]); const optimizationItems = ref<any[]>([])
const selectedGaps = ref<any[]>([])
const currentReportId = ref('')

function onSelectGaps(selection: any[]) { selectedGaps.value = selection }

async function convertToContent() {
  if (selectedGaps.value.length === 0) { ElMessage.warning('请先勾选要生成内容的缺口'); return }
  if (!currentReportId.value) { ElMessage.warning('请先生成诊断报告'); return }
  converting.value = true
  try {
    const ids = selectedGaps.value.map((g: any) => g.id)
    const r = await http.post('/diagnosis/layered/gaps/convert-to-briefs', ids)
    ElMessage.success(r.data?.message || `成功创建 ${r.data?.converted || 0} 个内容Brief！`)
    selectedGaps.value = []
    await fetchItems()
    // 引导去内容页
    setTimeout(() => { ElMessage({ message: '点击左侧菜单「内容创作」查看生成的Brief', type: 'success', duration: 5000 }) }, 500)
  } catch (e: any) {
    const msg = e.response?.data?.detail || e.message || '转换失败，请确认已生成诊断报告且勾选了缺口'
    ElMessage.error(msg)
    console.error('Convert error:', e.response?.data || e)
  }
  converting.value = false
}

function scoreColor(s: number) { return s >= 70 ? '#67c23a' : s >= 40 ? '#e6a23c' : '#f56c6c' }
function priorityType(p: string) { return { urgent: 'danger', important: 'warning', long_term: 'info' }[p] || 'info' }
function priorityLabel(p: string) { return { urgent: '紧急', important: '重要', long_term: '长期' }[p] || p }
function categoryLabel(c: string) { return { kb_gap: '知识库缺口', content_creation: '内容创作', channel_expansion: '渠道扩展', rule_update: '规则更新' }[c] || c }
function layerLabel(l: string) { return { basic: '基础资产', marketing: '营销资产', multimodal: '多模态资产' }[l] || l }
function statusType(s: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  return { pending: 'info', in_progress: 'warning', completed: 'success', skipped: '' }[s] as any || 'info'
}

async function fetchReports() {
  loading.value = true
  try { const r = await diagnosisApi.listReports({ page: 1, page_size: 20 }); reports.value = r.items; latestReport.value = r.items[0] || null } catch {}
  loading.value = false
}
async function fetchItems() {
  if (currentReportId.value) {
    try { const r = await http.get(`/diagnosis/layered/reports/${currentReportId.value}/gaps`); optimizationItems.value = r.data.gaps || [] } catch { optimizationItems.value = [] }
  }
}
async function generateReport() {
  generating.value = true
  try {
    const result = await http.post('/diagnosis/layered/run')
    const d = result.data
    if (d.report_id) currentReportId.value = d.report_id
    ElMessage.success(`诊断完成！总分${d.total_score}分，发现${d.gaps_count}个缺口（紧急${d.urgent_gaps}个）`)
    await fetchReports()
    await fetchItems()
    scores.value = [
      { model_name: '身份可信度', identity_score: d.identity_score||0, total_score: d.identity_score||0 },
      { model_name: '基础资产', identity_score: d.basic_asset_score||0, total_score: d.basic_asset_score||0 },
      { model_name: '营销资产', identity_score: d.marketing_asset_score||0, total_score: d.marketing_asset_score||0 },
      { model_name: '多模态资产', identity_score: d.multimodal_asset_score||0, total_score: d.multimodal_asset_score||0 },
      { model_name: '口碑健康度', identity_score: d.sentiment_score||0, total_score: d.sentiment_score||0 },
    ]
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '生成失败') }
  generating.value = false
}
async function fetchScores() {
  if (!latestReport.value) return
  try { scores.value = await diagnosisApi.getScores(latestReport.value.id) } catch {}
}
async function updateStatus(item: any, status: string) {
  try { await diagnosisApi.updateOptimizationItem(item.id, { status }); fetchItems() } catch (e: any) { ElMessage.error(e.response?.data?.error || '更新失败') }
}
function viewReport(r: any) { latestReport.value = r; currentReportId.value = r.id; fetchScoresForReport(r.id); fetchItems() }
async function fetchScoresForReport(id: string) { try { scores.value = await diagnosisApi.getScores(id) } catch {} }
async function deleteReport(r: any) {
  try {
    await ElMessageBox.confirm(`删除报告「${r.title}」？相关缺口数据也将被删除。`, '确认删除', { type: 'warning' })
    await http.delete(`/diagnosis/layered/reports/${r.id}`)
    ElMessage.success('已删除')
    await fetchReports()
    if (currentReportId.value === r.id) { currentReportId.value = ''; optimizationItems.value = []; scores.value = [] }
  } catch (e: any) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

onMounted(async () => {
  await fetchReports()
  if (latestReport.value) {
    currentReportId.value = latestReport.value.id
    await fetchItems()
    await fetchScores()
  }
})
</script>
