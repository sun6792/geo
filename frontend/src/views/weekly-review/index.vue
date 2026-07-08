<template>
  <div class="page-container">
    <div class="page-header">
      <h2>周度复盘报告</h2>
      <div>
        <el-button type="primary" @click="generateReview" :loading="generating">生成本周复盘</el-button>
        <el-button @click="$router.push('/weekly-review/rules')">AI引流规则库</el-button>
      </div>
    </div>

    <!-- Latest Review -->
    <div class="detail-section" v-if="latestReview">
      <div class="section-title">{{ latestReview.week_start }} ~ {{ latestReview.week_end }} 周度复盘</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="状态"><el-tag :type="latestReview.status==='completed'?'success':'info'">{{ latestReview.status }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(latestReview.created_at) }}</el-descriptions-item>
      </el-descriptions>

      <!-- Highlights -->
      <h4 style="margin-top:16px">核心亮点</h4>
      <div v-if="latestReview.highlights" style="margin-bottom:16px">
        <div style="margin-bottom:8px"><b>本周提升:</b></div>
        <el-tag v-for="w in latestReview.highlights?.wins" :key="w.metric" type="success" style="margin-right:8px;margin-bottom:4px">{{ w.metric }}: {{ w.change }}</el-tag>
        <div v-if="!latestReview.highlights?.wins?.length" style="color:#909399">暂无</div>
        <div style="margin-top:12px;margin-bottom:8px"><b>需关注:</b></div>
        <el-tag v-for="i in latestReview.highlights?.issues" :key="i.metric" type="danger" style="margin-right:8px;margin-bottom:4px">{{ i.metric }}: {{ i.change }}</el-tag>
        <div v-if="!latestReview.highlights?.issues?.length" style="color:#909399">暂无</div>
      </div>

      <!-- Recommendations -->
      <h4 style="margin-top:16px">下轮策略</h4>
      <div v-if="latestReview.recommendations">
        <p style="margin-bottom:8px">{{ latestReview.recommendations?.strategy }}</p>
        <div v-for="r in latestReview.recommendations?.next_steps" :key="r.action" style="margin-bottom:4px">
          <el-tag :type="r.priority==='urgent'?'danger':'warning'" size="small">{{ r.priority }}</el-tag>
          {{ r.action }}
          <span v-if="r.target" style="color:#909399">(目标: {{ r.target }})</span>
        </div>
      </div>

      <!-- Report Markdown -->
      <div v-if="latestReview.report_markdown" v-html="latestReview.report_markdown" style="margin-top:16px;padding:16px;background:#f9fafb;border-radius:8px;white-space:pre-wrap;font-family:monospace;font-size:13px"></div>
    </div>
    <div v-else class="table-card">
      <el-empty description="暂无复盘报告，点击'生成本周复盘'开始" />
    </div>

    <!-- KB Gap Analysis -->
    <div class="detail-section" v-if="latestReview?.kb_gap_analysis">
      <div class="section-title">知识库资产增厚</div>
      <el-row :gutter="16">
        <el-col :span="8" v-for="(v,k) in latestReview.kb_gap_analysis" :key="k">
          <div class="stat-card"><div class="stat-label">{{ k }}</div><div class="stat-value">{{ v }}</div></div>
        </el-col>
      </el-row>
    </div>

    <!-- Content Performance -->
    <div class="detail-section" v-if="latestReview?.content_performance_summary">
      <div class="section-title">本周内容表现</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="发布数量">{{ latestReview.content_performance_summary?.published_count || 0 }}</el-descriptions-item>
        <el-descriptions-item label="总曝光">{{ latestReview.content_performance_summary?.total_impressions || 0 }}</el-descriptions-item>
        <el-descriptions-item label="总点击">{{ latestReview.content_performance_summary?.total_clicks || 0 }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- History -->
    <div class="detail-section">
      <div class="section-title">历史复盘报告</div>
      <el-table :data="reviews" v-loading="loading" stripe>
        <el-table-column prop="week_start" label="周起始" width="120" />
        <el-table-column prop="week_end" label="周结束" width="120" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="created_at" label="生成时间" width="160"><template #default="{row}">{{ formatDate(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{row}"><el-button size="small" @click="viewReview(row)">查看详情</el-button></template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { weeklyReviewApi } from '@/api/detection'
import { formatDate } from '@/utils/format'

const loading = ref(false); const generating = ref(false)
const reviews = ref<any[]>([]); const latestReview = ref<any>(null)

async function fetchReviews() {
  loading.value = true
  try { const r = await weeklyReviewApi.listReviews({ page: 1, page_size: 10 }); reviews.value = r.items } catch {}
  loading.value = false
}
async function fetchLatest() {
  try { latestReview.value = await weeklyReviewApi.getLatest() } catch {}
}
async function generateReview() {
  generating.value = true
  try { await weeklyReviewApi.generateReview(); ElMessage.success('周度复盘已生成'); fetchReviews(); fetchLatest() } catch (e: any) { ElMessage.error(e.response?.data?.error || '生成失败') }
  generating.value = false
}
function viewReview(r: any) { latestReview.value = r }

onMounted(() => { fetchReviews(); fetchLatest() })
</script>
