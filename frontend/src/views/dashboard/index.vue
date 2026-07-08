<template>
  <div class="page-container">
    <div class="page-header"><h2>运营工作台</h2></div>

    <!-- Pipeline Status Bar -->
    <div class="pipeline-bar" v-if="pipeline">
      <div class="pipeline-item" v-for="a in agents" :key="a.key" :class="'status-'+a.status">
        <div class="p-agent-name">{{ a.label }}</div>
        <div class="p-agent-stat" v-if="a.detail">{{ a.detail }}</div>
        <el-tag :type="a.status==='completed'?'success':a.status==='in_progress'?'warning':'info'" size="small" effect="dark">
          {{ a.status === 'completed' ? '已完成' : a.status === 'in_progress' ? '进行中' : '待启动' }}
        </el-tag>
        <el-button size="small" @click="$router.push(a.path)" style="margin-top:6px">进入</el-button>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="stat-cards">
      <div class="stat-card" v-for="s in stats" :key="s.label">
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-value">{{ s.value }}</div>
      </div>
    </div>

    <!-- Agent Cards -->
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="8" v-for="card in agentCards" :key="card.key">
        <div class="agent-card" @click="$router.push(card.path)">
          <div class="card-header">
            <span class="card-title">{{ card.icon }} {{ card.title }}</span>
            <el-tag :type="card.status==='active'?'success':'info'" size="small">{{ card.statusText }}</el-tag>
          </div>
          <div class="card-desc">{{ card.desc }}</div>
          <div class="card-action">{{ card.action }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- Recent Activity -->
    <div class="detail-section" style="margin-top:20px">
      <div class="section-title">最近操作记录</div>
      <el-table :data="activity" stripe size="small">
        <el-table-column prop="action" label="操作" min-width="200" />
        <el-table-column prop="resource_type" label="模块" width="120" />
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{row}">{{ row.created_at?.slice(0,16) || '-' }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!activity.length" description="暂无操作记录" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import http from '@/api/index'

const pipeline = ref<any>(null)
const stats = ref([
  { label: '探测任务', value: 0 }, { label: '诊断报告', value: 0 },
  { label: '内容稿件', value: 0 }, { label: '本周发布', value: 0 },
])

const agents = computed(() => {
  if (!pipeline.value) return []
  const a = pipeline.value.agents || {}
  return [
    { key: 'agent1', label: '1.模型探测', path: '/detection',
      status: a.agent1_detection?.status || 'not_started',
      detail: a.agent1_detection?.results_this_week ? `${a.agent1_detection.results_this_week}条本周` : '' },
    { key: 'agent2', label: '2.短板诊断', path: '/diagnosis',
      status: a.agent2_diagnosis?.status || 'not_started',
      detail: a.agent2_diagnosis?.open_gaps ? `${a.agent2_diagnosis.open_gaps}个缺口` : '' },
    { key: 'agent3', label: '3.内容创作', path: '/content',
      status: a.agent3_content?.status || 'not_started',
      detail: a.agent3_content?.drafts_this_week ? `${a.agent3_content.drafts_this_week}篇本周` : '' },
    { key: 'agent4', label: '4.审核发布', path: '/review',
      status: a.agent4_review_publish?.status || 'not_started',
      detail: a.agent4_review_publish?.pending_reviews ? `${a.agent4_review_publish.pending_reviews}条待审` : '' },
    { key: 'agent5', label: '5.周度复盘', path: '/weekly-review',
      status: a.agent5_weekly_review?.status || 'not_started',
      detail: a.agent5_weekly_review?.backflows_applied ? `${a.agent5_weekly_review.backflows_applied}条回流` : '' },
  ]
})

const agentCards = computed(() => {
  const getStatus = (key: string) => {
    if (!pipeline.value) return { status: 'idle', statusText: '待启动' }
    const a = pipeline.value.agents || {}
    const map: Record<string,string> = { agent1: 'agent1_detection', agent2: 'agent2_diagnosis', agent3: 'agent3_content', agent4: 'agent4_review_publish', agent5: 'agent5_weekly_review' }
    const s = a[map[key]]?.status || 'not_started'
    return { status: s === 'completed' ? 'active' : 'idle', statusText: s === 'completed' ? '已完成' : s === 'in_progress' ? '进行中' : '待启动' }
  }
  const s1 = getStatus('agent1'); const s2 = getStatus('agent2'); const s3 = getStatus('agent3')
  const s4 = getStatus('agent4'); const s5 = getStatus('agent5')
  return [
    { key:'agent1', icon:'[探测器]', title:'全域模型探测', path:'/detection', status:s1.status, statusText:s1.statusText, desc:'5大模型真实一问一答，检测品牌曝光', action:'新建探测任务 →' },
    { key:'agent2', icon:'[诊断器]', title:'短板诊断分析', path:'/diagnosis', status:s2.status, statusText:s2.statusText, desc:'三层资产诊断+五维评分+缺口清单', action:s2.status==='active'?'查看缺口→':'生成诊断报告 →' },
    { key:'agent3', icon:'[创作器]', title:'智能内容创作', path:'/content', status:s3.status, statusText:s3.statusText, desc:'缺口→Brief→主稿+5模型差异化改写', action:s3.status==='active'?'查看稿件→':'一键生成内容 →' },
    { key:'agent4', icon:'[审核器]', title:'内容审核发布', path:'/review', status:s4.status, statusText:s4.statusText, desc:'双重审核+18渠道三级矩阵分发', action:s4.status==='active'?'处理待审→':'查看队列 →' },
    { key:'agent5', icon:'[复盘器]', title:'周度效果复盘', path:'/weekly-review', status:s5.status, statusText:s5.statusText, desc:'竞品对标+资产增厚+数据回流', action:s5.status==='active'?'查看报告→':'生成周报 →' },
    { key:'kb', icon:'[知识库]', title:'客户知识库', path:'/knowledge-base', status:'active', statusText:'随时可用', desc:'录入企业资料、产品、案例、素材', action:'管理资产 →' },
  ]
})

const activity = ref<any[]>([])

onMounted(async () => {
  // Load all data in parallel for speed
  const [pRes, rRes, lRes] = await Promise.allSettled([
    http.get('/pipeline/status'),
    http.get('/reviews/', { params: { status: 'pending' } }),
    http.get('/p2/operation-logs', { params: { page:1, page_size:10 } }),
  ])
  if (pRes.status === 'fulfilled') {
    pipeline.value = pRes.value.data
    const a = pRes.value.data?.agents || {}
    stats.value[0].value = a.agent1_detection?.tasks_total || 0
    stats.value[1].value = a.agent2_diagnosis?.reports_total || 0
    stats.value[2].value = a.agent3_content?.drafts_total || 0
  }
  if (rRes.status === 'fulfilled') {
    const r = rRes.value.data
    stats.value[3].value = Array.isArray(r) ? r.length : 0
  }
  if (lRes.status === 'fulfilled') {
    activity.value = lRes.value.data?.items || []
  }
})
</script>

<style scoped>
.pipeline-bar { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.pipeline-item { flex: 1; min-width: 140px; background: #fff; border-radius: 10px; padding: 14px; text-align: center; border: 2px solid #e4e7ed; transition: all .2s; }
.pipeline-item.status-completed { border-color: #67c23a; background: #f0f9eb; }
.pipeline-item.status-in_progress { border-color: #409eff; background: #ecf5ff; }
.pipeline-item:hover { box-shadow: 0 2px 12px rgba(0,0,0,.08); }
.p-agent-name { font-weight: 700; font-size: 14px; margin-bottom: 4px; }
.p-agent-stat { font-size: 12px; color: #909399; margin-bottom: 4px; }

.agent-card { background: #fff; border-radius: 10px; padding: 18px; cursor: pointer; border: 1px solid #ebeef5; transition: all .2s; margin-bottom: 14px; }
.agent-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.1); transform: translateY(-2px); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.card-title { font-weight: 700; font-size: 15px; }
.card-desc { color: #606266; font-size: 13px; margin-bottom: 8px; }
.card-action { color: #409eff; font-size: 13px; font-weight: 600; }
</style>
