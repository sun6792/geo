<template>
  <div style="min-height:100vh;background:#f5f7fa">
    <!-- 极简顶部 -->
    <div style="background:#fff;padding:16px 32px;box-shadow:0 1px 4px rgba(0,0,0,0.06);display:flex;align-items:center;justify-content:space-between">
      <div style="display:flex;align-items:center;gap:12px">
        <h2 style="margin:0;font-size:20px;color:#1a1a2e">AI引流 效果看板</h2>
        <el-tag size="small" type="info">{{ authStore.user?.display_name || '客户' }}</el-tag>
      </div>
      <el-button @click="handleLogout" size="small">退出</el-button>
    </div>

    <div style="max-width:1100px;margin:0 auto;padding:24px 16px">
      <!-- 每日进度 -->
      <div class="detail-section">
        <div class="section-title"> 每日实时进度</div>
        <el-row :gutter="16">
          <el-col :span="6"><div class="stat-card"><div class="stat-label">今日发布量</div><div class="stat-value">{{ daily?.published_today || 0 }}</div></div></el-col>
          <el-col :span="6"><div class="stat-card"><div class="stat-label">今日提及量</div><div class="stat-value">{{ daily?.model_rankings?.reduce((s:any,r:any)=>s+r.mentions,0) || 0 }}</div></div></el-col>
          <el-col :span="6"><div class="stat-card"><div class="stat-label">新增信源</div><div class="stat-value">{{ daily?.new_sources || 0 }}</div></div></el-col>
          <el-col :span="6"><div class="stat-card"><div class="stat-label">日期</div><div class="stat-value" style="font-size:16px">{{ daily?.date || '--' }}</div></div></el-col>
        </el-row>
        <!-- 各模型排名 -->
        <el-table :data="daily?.model_rankings || []" style="margin-top:16px" stripe>
          <el-table-column prop="model" label="模型" width="120" />
          <el-table-column prop="mentions" label="提及次数" width="100" />
          <el-table-column label="平均排名" width="100">
            <template #default="{row}"><b :style="{color:row.avg_rank<=5?'#67c23a':'#e6a23c'}">{{ row.avg_rank || '>' }}</b></template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 周度汇总 -->
      <div class="detail-section">
        <div class="section-title"> 本周效果汇总</div>
        <el-descriptions :column="4" border>
          <el-descriptions-item label="本周发布">{{ weekly?.total_published || 0 }} 篇</el-descriptions-item>
          <el-descriptions-item label="新增资产">{{ weekly?.new_assets || 0 }} 条</el-descriptions-item>
          <el-descriptions-item label="曝光增长">{{ weekly?.exposure_growth || '--' }}</el-descriptions-item>
          <el-descriptions-item label="排名提升">{{ weekly?.avg_rank_improvement || '--' }}</el-descriptions-item>
          <el-descriptions-item label="权重复合变化" :span="4">{{ weekly?.weight_score_change || '--' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 历史周报 -->
      <div class="detail-section">
        <div class="section-title"> 历史周度复盘</div>
        <el-table :data="reviews" stripe>
          <el-table-column prop="week_start" label="周起始" width="120" />
          <el-table-column prop="week_end" label="周结束" width="120" />
          <el-table-column label="亮点" min-width="300">
            <template #default="{row}">{{ row.highlights?.summary || '暂无' }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!reviews.length" description="暂无复盘报告" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import http from '@/api/index'
const authStore = useAuthStore(); const router = useRouter()
const daily = ref<any>(null); const weekly = ref<any>(null); const reviews = ref<any[]>([])
function handleLogout() { authStore.clearAuth(); router.push('/login') }
onMounted(async () => {
  try { daily.value = (await http.get('/p5/portal/daily-progress')).data } catch {}
  try { weekly.value = (await http.get('/p5/portal/weekly-summary')).data } catch {}
  try { reviews.value = (await http.get('/p5/portal/weekly-reviews')).data || [] } catch {}
})
</script>
