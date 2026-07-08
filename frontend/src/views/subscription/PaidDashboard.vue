<template>
  <div class="page-container">
    <div class="page-header"><h2>客户数据看板</h2></div>

    <div class="detail-section">
      <div class="section-title">发布数据</div>
      <el-row :gutter="16">
        <el-col :span="6"><div class="stat-card"><div class="stat-label">今日发布</div><div class="stat-value">{{ daily?.published_today || 0 }}</div></div></el-col>
        <el-col :span="6"><div class="stat-label">各模型提及</div>
          <div v-for="m in daily?.model_rankings || []" :key="m.model" style="margin:4px 0">{{ m.model }}: {{ m.mentions }}次</div>
        </el-col>
      </el-row>
    </div>

    <div class="detail-section">
      <div class="section-title">周度复盘报告</div>
      <el-table :data="weekly?.reviews || []" stripe>
        <el-table-column prop="week_start" label="周起始" width="120" />
        <el-table-column prop="week_end" label="周结束" width="120" />
        <el-table-column label="亮点" min-width="250">
          <template #default="{row}">{{ row.highlights?.summary || '暂无' }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!(weekly?.reviews?.length)" description="暂无复盘报告" />
    </div>

    <!-- Summary stats -->
    <div class="detail-section">
      <div class="section-title">本周汇总</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="本周发布">{{ weekly?.summary?.total_published || 0 }} 篇</el-descriptions-item>
        <el-descriptions-item label="新增资产">{{ weekly?.summary?.new_assets || 0 }} 条</el-descriptions-item>
        <el-descriptions-item label="曝光增长">{{ weekly?.summary?.exposure_growth || '--' }}</el-descriptions-item>
        <el-descriptions-item label="排名提升">{{ weekly?.summary?.avg_rank_improvement || '--' }}</el-descriptions-item>
        <el-descriptions-item label="权重变化">{{ weekly?.summary?.weight_score_change || '--' }}</el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import http from '@/api/index'

const daily = ref<any>(null)
const weekly = ref<any>({ reviews: [], summary: {} })

onMounted(async () => {
  try { daily.value = (await http.get('/p5/portal/daily-progress')).data } catch {}
  try { weekly.value = (await http.get('/p5/portal/weekly-summary')).data || {}; weekly.value.reviews = (await http.get('/p5/portal/weekly-reviews')).data || [] } catch {}
})
</script>
