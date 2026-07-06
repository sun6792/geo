<template>
  <div class="demo-wrapper">
    <div class="demo-container">
      <div class="demo-header"><h1>GEO 智能优化系统</h1><p>输入企业信息，一键查询主流大模型真实曝光与竞品差距</p></div>

      <div class="demo-form">
        <el-input v-model="companyName" size="large" placeholder="企业全称（必填）" :disabled="loading" style="margin-bottom:12px" />
        <div style="display:flex;gap:12px;margin-bottom:12px">
          <el-input v-model="industry" size="large" placeholder="所属行业（必填，如：运动面料制造）" :disabled="loading" style="flex:1" />
          <el-input v-model="mainBusiness" size="large" placeholder="核心主营业务（必填，如：研发骑行速干面料）" :disabled="loading" style="flex:1" />
        </div>
        <el-button type="primary" size="large" @click="startScan" :loading="loading" :disabled="!canSubmit" style="width:100%">
          {{ loading ? '正在多模型一问一答探测...' : '一键分析' }}
        </el-button>
      </div>

      <div v-if="loading" class="demo-loading">
        <el-steps :active="loadStep" align-center finish-status="success">
          <el-step title="豆包" description="3轮问答交互" /><el-step title="文心一言" description="3轮问答交互" />
          <el-step title="通义千问" description="3轮问答交互" /><el-step title="腾讯元宝" description="3轮问答交互" />
          <el-step title="DeepSeek" description="综合交叉分析" />
        </el-steps>
        <el-progress :percentage="progress" :stroke-width="6" color="#409eff" style="margin-top:16px" />
        <p class="load-text">{{ loadText }}</p>
      </div>
      <div v-if="errorMsg" class="demo-error">{{ errorMsg }}</div>

      <div v-if="result && !loading" class="demo-results">
        <!-- 1. Base info -->
        <div class="result-card"><h3>企业概况</h3>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="企业全称">{{ result.base_info?.company_name }}</el-descriptions-item>
            <el-descriptions-item label="所属行业">{{ result.base_info?.industry }}</el-descriptions-item>
            <el-descriptions-item label="主营业务">{{ result.base_info?.main_business }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 2. Model table -->
        <div class="result-card"><h3>主流大模型一问一答探测结果 · 综合 {{ result.total_score }} 分</h3>
          <el-table :data="result.model_table_data" stripe>
            <el-table-column prop="platform" label="平台" width="90" />
            <el-table-column prop="mention_month" label="月度提及" width="85" align="center">
              <template #default="{row}"><b :style="{color:row.mention_month>30?'#67c23a':row.mention_month>5?'#e6a23c':'#f56c6c'}">{{ row.mention_month }}</b></template>
            </el-table-column>
            <el-table-column label="排名" width="75" align="center">
              <template #default="{row}"><b :style="{color:row.avg_rank<=10?'#67c23a':row.avg_rank<=30?'#e6a23c':'#f56c6c'}">{{ row.avg_rank ? 'No.'+row.avg_rank : '-' }}</b></template>
            </el-table-column>
            <el-table-column prop="collect_count" label="收录" width="65" align="center" />
            <el-table-column label="等级" width="85">
              <template #default="{row}"><el-tag :type="row.expose_level==='高频置顶'?'success':row.expose_level==='稳定曝光'?'warning':'danger'" size="small" effect="dark">{{ row.expose_level }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="platform_short" label="平台短板" min-width="190" show-overflow-tooltip />
            <el-table-column label="溯源" width="80" align="center">
              <template #default="{row}"><el-button size="small" link type="primary" @click="openTrace(row.platform)">查看原始问答</el-button></template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 3. Rival -->
        <div class="result-card" style="border-left:4px solid #f56c6c"><h3>竞品横向对比</h3>
          <p style="color:#f56c6c;font-weight:700;font-size:16px;margin:8px 0">{{ result.rival_info?.name }}</p>
          <el-row :gutter="16" style="margin-bottom:12px">
            <el-col :span="8"><div class="stat-card"><div class="stat-label">我方月度总曝光</div><div class="stat-value" style="color:#f56c6c">{{ result.rival_info?.self_total }}</div></div></el-col>
            <el-col :span="8"><div class="stat-card"><div class="stat-label">竞品月度总曝光</div><div class="stat-value" style="color:#67c23a">{{ result.rival_info?.rival_total_mention }}</div></div></el-col>
            <el-col :span="8"><div class="stat-card"><div class="stat-label">曝光倍数</div><div class="stat-value" style="color:#f56c6c;font-size:32px">{{ result.rival_info?.gap_text?.match(/(\d+\.?\d*)倍/)?.[0] || '--' }}</div></div></el-col>
          </el-row>
          <div style="background:rgba(245,108,108,0.1);border-radius:8px;padding:16px"><p style="color:#f56c6c;font-weight:600;font-size:15px;line-height:1.8;margin:0"> 风险警示：{{ result.rival_info?.gap_text }}</p></div>
          <el-button type="warning" size="small" style="margin-top:12px" @click="openRivalTrace()">查看竞品原始探测对话</el-button>
        </div>

        <!-- 4. Shortcomings -->
        <div class="result-card pain-card"><h3>分层短板诊断</h3>
          <h4 style="color:#f56c6c;margin:12px 0 8px">全平台通用短板</h4>
          <div v-for="(p,i) in result.diagnose_shortcoming?.global_short" :key="'g'+i" class="pain-item"><span class="pain-num">{{ i+1 }}</span><span>{{ p }}</span></div>
          <h4 style="color:#e6a23c;margin:16px 0 8px">各平台专属短板</h4>
          <div v-for="(p,i) in result.diagnose_shortcoming?.platform_short" :key="'s'+i" class="pain-item"><span class="pain-num s">{{ i+1 }}</span><span>{{ p }}</span></div>
        </div>

        <!-- 5. Solution -->
        <div class="result-card solution-card"><h3>GEO 系统落地解决方案</h3>
          <el-timeline>
            <el-timeline-item timestamp="短期 · 第1周期 (1-2周)" color="#409eff" size="large"><p>{{ result.geo_solution?.phase1 }}</p></el-timeline-item>
            <el-timeline-item timestamp="中期 · 第2周期 (3-4周)" color="#67c23a" size="large"><p>{{ result.geo_solution?.phase2 }}</p></el-timeline-item>
            <el-timeline-item timestamp="长期 · 常态化运营" color="#e6a23c" size="large"><p>{{ result.geo_solution?.phase3 }}</p></el-timeline-item>
          </el-timeline>
        </div>

        <!-- 6. CTA -->
        <div class="result-card cta-card"><p style="font-size:16px;font-weight:700;margin-bottom:12px">付费开通后每日实时追踪优化进度</p>
          <p style="color:#a0aec0;font-size:14px;line-height:1.8">{{ result.pay_tip_text }}</p></div>
      </div>

      <!-- Trace dialog (reads from in-memory cache, no API call) -->
      <el-dialog v-model="traceVisible" :title="'一问一答原始探测记录 — ' + traceModel" width="780px" top="3vh">
        <div v-if="traceRounds.length">
          <div v-for="(t,i) in traceRounds" :key="i" style="margin-bottom:20px;border:1px solid #ebeef5;border-radius:8px;overflow:hidden">
            <div style="background:#f5f7fa;padding:8px 12px;font-size:12px;color:#909399">第{{ i+1 }}轮 {{ traceIsRival ? '· 竞品探测' : '' }}</div>
            <div style="padding:12px"><p style="color:#409eff;font-weight:600;margin:0 0 8px"> 我方提问：</p><pre style="background:#ecf5ff;padding:12px;border-radius:4px;white-space:pre-wrap;font-size:13px;line-height:1.6;margin:0;color:#303133">{{ t.ask }}</pre></div>
            <div style="padding:0 12px 12px"><p style="color:#67c23a;font-weight:600;margin:0 0 8px"> 模型回答：</p><pre style="background:#f0f9eb;padding:12px;border-radius:4px;white-space:pre-wrap;font-size:13px;line-height:1.6;margin:0;max-height:300px;overflow-y:auto;color:#303133">{{ t.reply || '（模型返回为空）' }}</pre></div>
          </div>
        </div>
        <el-empty v-else description="本次探测未抓取到该平台相关对话记录，请确认已完成一键分析" />
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api/index'

const companyName = ref(''); const industry = ref(''); const mainBusiness = ref('')
const loading = ref(false); const progress = ref(0); const loadStep = ref(0); const loadText = ref('')
const result = ref<any>(null); const errorMsg = ref('')
const canSubmit = computed(() => companyName.value.trim() && industry.value.trim() && mainBusiness.value.trim())

// Trace dialog state — reads from in-memory cache, NO second API call
const traceVisible = ref(false); const traceModel = ref(''); const traceIsRival = ref(false)
const traceRounds = ref<any[]>([])

function openTrace(platform: string) {
  if (!result.value) return
  const cache = result.value.task_temp_cache || {}
  const data = cache[platform]
  traceModel.value = platform; traceIsRival.value = false
  traceRounds.value = data?.chat_rounds || []
  traceVisible.value = true
}

function openRivalTrace() {
  if (!result.value) return
  const cache = result.value.rival_temp_cache || {}
  const first = Object.values(cache)[0] as any
  traceModel.value = '竞品'; traceIsRival.value = true
  traceRounds.value = first?.chat_rounds || []
  traceVisible.value = true
}

const steps = ['正在对豆包执行3轮一问一答...','正在对文心一言执行3轮一问一答...','正在对通义千问执行3轮一问一答...','正在对腾讯元宝执行3轮一问一答...','DeepSeek综合交叉分析中...']
let timer: any = null

async function startScan() {
  if (!canSubmit.value) { ElMessage.warning('请完整填写企业全称、所属行业、主营业务三项信息'); return }
  errorMsg.value = ''; result.value = null; loading.value = true; progress.value = 0; loadStep.value = 0; loadText.value = steps[0]
  timer = setInterval(() => { if (progress.value < 90) { progress.value += Math.random() * 10 + 5; loadStep.value = Math.min(4, Math.floor(progress.value / 20)); loadText.value = steps[loadStep.value] } }, 600)
  try {
    const r = await http.get('/demo/scan_enterprise', { params: { company_name: companyName.value.trim(), industry: industry.value.trim(), main_business: mainBusiness.value.trim() } })
    result.value = r.data
  } catch (e: any) {
    if (e.code === 'ECONNABORTED') errorMsg.value = '多模型并行探测耗时较长（约30-60秒），请稍后重试'
    else if (e.response?.status === 404) errorMsg.value = '演示接口未部署，请检查后端服务是否启动'
    else if (e.response?.status === 500) errorMsg.value = '探测服务执行出错：' + (e.response?.data?.detail || '查看后端日志')
    else if (e.response?.status === 429) errorMsg.value = '请求过于频繁，请60秒后再试'
    else if (!e.response) errorMsg.value = '无法连接后端服务，请确认已启动：uvicorn app.main:app --port 8000'
    else errorMsg.value = e.response?.data?.detail || '探测失败，请检查企业信息后重试'
    console.error('Demo scan error:', e)
  }
  clearInterval(timer); progress.value = 100; loadStep.value = 5
  setTimeout(() => { loading.value = false }, 400)
}
</script>

<style scoped>
.demo-wrapper { min-height:100vh; background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%); }
.demo-container { max-width:880px; margin:0 auto; padding:40px 20px 60px; color:#fff; }
.demo-header { text-align:center; margin-bottom:28px; } .demo-header h1 { font-size:36px; font-weight:700; margin:0; } .demo-header p { font-size:16px; color:#a0aec0; margin-top:8px; }
.demo-form { margin-bottom:24px; }
.demo-loading { text-align:center; padding:32px 0; } .demo-loading :deep(.el-step__title){font-size:13px;color:#a0aec0} .demo-loading :deep(.el-step__description){font-size:11px;color:#6b7280}
.load-text { color:#a0aec0; margin-top:12px; } .demo-error { text-align:center; padding:40px; color:#f56c6c; font-size:16px; }
.demo-results { margin-top:24px; }
.result-card { background:rgba(255,255,255,0.06); border-radius:12px; padding:24px; margin-bottom:20px; border:1px solid rgba(255,255,255,0.08); } .result-card h3 { margin:0 0 4px; font-size:18px; }
.stat-card { background:rgba(255,255,255,0.04); border-radius:8px; padding:16px; text-align:center } .stat-label { font-size:13px; color:#a0aec0; margin-bottom:8px } .stat-value { font-size:26px; font-weight:700 }
.pain-card { border-left:3px solid #f56c6c; } .pain-item { display:flex; align-items:flex-start; gap:12px; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.06); font-size:14px; line-height:1.7; } .pain-num { background:#f56c6c; color:#fff; width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; flex-shrink:0; } .pain-num.s { background:#e6a23c; }
.solution-card :deep(.el-timeline-item__content){color:#c0c4cc} .solution-card p { margin:0; line-height:1.8; color:#a0aec0; font-size:13px; }
.cta-card { background:rgba(64,158,255,0.12); border:1px solid rgba(64,158,255,0.3); text-align:center; }
:deep(.el-table){--el-table-bg-color:transparent;--el-table-tr-bg-color:transparent;--el-table-text-color:#c0c4cc}:deep(.el-table th){background:rgba(255,255,255,0.06);color:#a0aec0}:deep(.el-descriptions__label){color:#a0aec0}:deep(.el-descriptions__content){color:#c0c4cc}
</style>
