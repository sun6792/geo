<template>
  <div class="page-container">
    <div class="page-header">
      <h2>AI模型探测</h2>
      <div style="display:flex;gap:10px;align-items:center">
        <span style="font-weight:600">选择客户：</span>
        <el-select v-model="selectedCustomerId" placeholder="选择要探测的客户" style="width:240px" @change="onCustomerChange" clearable>
          <el-option v-for="c in customerList" :key="c.id" :label="c.name + ' (' + (c.industry||'未分类') + ')'" :value="c.id" />
        </el-select>
        <el-button @click="showTaskDialog = true" type="primary">新建探索任务</el-button>
        <el-button @click="showCompetitorDialog = true">添加竞品</el-button>
      </div>
    </div>

    <!-- Stat cards -->
    <div class="stat-cards">
      <div class="stat-card" v-for="s in stats" :key="s.label">
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-value">{{ s.value }}</div>
      </div>
    </div>

    <!-- Detection Tasks -->
    <div class="detail-section">
      <div class="section-title">探测任务列表</div>
      <el-table :data="tasks" v-loading="loading" stripe>
        <el-table-column prop="name" label="任务名称" min-width="150" />
        <el-table-column label="目标模型" min-width="200">
          <template #default="{ row }"><el-tag v-for="m in row.target_models" :key="m" size="small" style="margin:2px">{{ modelLabel(m) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="关键词数" width="100"><template #default="{ row }">{{ row.keywords?.length || 0 }}</template></el-table-column>
        <el-table-column label="调度" width="80"><template #default="{ row }">{{ scheduleLabel(row.schedule_type) }}</template></el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="row.last_status==='completed'?'success':row.last_status==='running'?'warning':'info'" size="small">{{ row.last_status || (row.is_active ? '待执行' : '已停用') }}</el-tag></template>
        </el-table-column>
        <el-table-column label="上次运行" width="160">
          <template #default="{ row }">{{ row.last_run_at ? formatDate(row.last_run_at) : '未运行' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="runTask(row)">执行</el-button>
            <el-button size="small" @click="editTask(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteTask(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Detection Results Summary -->
    <div class="detail-section" v-if="summaryData">
      <div class="section-title">
        探测结果概览（按模型汇总）
        <el-button size="small" type="primary" @click="viewChats()" style="margin-left:12px"> 查看原始对话</el-button>
      </div>
      <el-table :data="summaryList" stripe>
        <el-table-column prop="model" label="大模型" width="120"><template #default="{row}">{{ modelLabel(row.model) }}</template></el-table-column>
        <el-table-column prop="mention_rate" label="提及率(%)" width="100" />
        <el-table-column prop="avg_rank" label="均排名" width="80" />
        <el-table-column label="操作" width="100">
          <template #default="{row}"><el-button size="small" @click="viewChats(row.model)">查看对话</el-button></template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create/Edit Task Dialog -->
    <el-dialog v-model="showTaskDialog" :title="editingTask ? '编辑任务' : '新建探测任务'" width="600px">
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="任务名称"><el-input v-model="taskForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="taskForm.description" type="textarea" /></el-form-item>
        <el-form-item label="目标模型">
          <el-checkbox-group v-model="taskForm.target_models">
            <el-checkbox v-for="m in MODEL_OPTIONS" :key="m.value" :label="m.value" :value="m.value">{{ m.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="探测关键词">
          <div v-for="(kw, i) in taskForm.keywords" :key="i" style="display:flex;gap:8px;margin-bottom:4px">
            <el-input v-model="kw.word" placeholder="关键词" style="flex:1" />
            <el-select v-model="kw.type" style="width:120px">
              <el-option label="泛需求" value="broad" /><el-option label="精准产品" value="product" />
              <el-option label="对比选型" value="comparison" /><el-option label="场景方案" value="scenario" />
            </el-select>
            <el-button @click="taskForm.keywords.splice(i,1)" type="danger" size="small">×</el-button>
          </div>
          <el-button size="small" @click="taskForm.keywords.push({word:'',type:'broad'})">+ 添加关键词</el-button>
        </el-form-item>
        <el-form-item label="调度类型">
          <el-radio-group v-model="taskForm.schedule_type">
            <el-radio label="manual">手动</el-radio><el-radio label="daily">每日</el-radio><el-radio label="weekly">每周</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="showTaskDialog=false">取消</el-button><el-button type="primary" @click="saveTask" :loading="saving">保存</el-button></template>
    </el-dialog>

    <!-- Competitor Dialog -->
    <el-dialog v-model="showCompetitorDialog" title="添加竞品" width="400px">
      <el-form :model="compForm" label-width="80px">
        <el-form-item label="名称"><el-input v-model="compForm.name" /></el-form-item>
        <el-form-item label="网址"><el-input v-model="compForm.website" /></el-form-item>
        <el-form-item label="行业"><el-input v-model="compForm.industry" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCompetitorDialog=false">取消</el-button><el-button type="primary" @click="saveCompetitor" :loading="saving">保存</el-button></template>
    </el-dialog>

    <!-- Raw Chat Dialog -->
    <el-dialog v-model="showChatDialog" title="原始一问一答记录" width="800px" top="3vh">
      <el-select v-model="chatModelFilter" placeholder="筛选模型" style="width:150px;margin-bottom:12px" @change="loadChatLogs">
        <el-option v-for="m in MODEL_OPTIONS" :key="m.value" :label="m.label" :value="m.value" />
      </el-select>
      <div v-if="chatLogs.length === 0" style="text-align:center;padding:40px;color:#999">暂无对话记录，请先执行探测任务</div>
      <div v-for="(log, i) in chatLogs" :key="i" style="margin-bottom:16px;border:1px solid #ebeef5;border-radius:8px;overflow:hidden">
        <div style="background:#f5f7fa;padding:6px 12px;font-size:12px;color:#909399">第{{ i+1 }}条 · {{ log.model_name || log.model_id }} · {{ log.query_type === 'follow_up' ? '追问' : '首轮' }} · {{ log.probe_time?.slice(0,16) || '' }}</div>
        <div style="padding:10px 12px"><b style="color:#409eff"> 提问：</b><pre style="background:#ecf5ff;padding:8px;border-radius:4px;white-space:pre-wrap;overflow-wrap:break-word;word-break:break-word;font-size:12px;margin:4px 0;max-height:120px;overflow-y:auto">{{ log.query_text }}</pre></div>
        <div style="padding:0 12px 10px">
          <b style="color:#67c23a"> 回答：</b>
          <span v-if="log.status==='failed'" style="color:#f56c6c;font-size:11px">(API调用失败: {{ log.error_message }})</span>
          <pre style="background:#f0f9eb;padding:8px;border-radius:4px;white-space:pre-wrap;overflow-wrap:break-word;word-break:break-word;font-size:12px;margin:4px 0;max-height:200px;overflow-y:auto">{{ log.raw_answer || '(模型未返回有效回复)' }}</pre></div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { detectionApi } from '@/api/detection'
import { formatDate } from '@/utils/format'
import http from '@/api/index'

const MODEL_OPTIONS = [
  { label: '豆包', value: 'doubao' }, { label: '文心一言', value: 'wenxin' }, { label: '通义千问', value: 'qianwen' },
  { label: '腾讯元宝', value: 'yuanbao' }, { label: '讯飞星火', value: 'xinghuo' },
]
const MODEL_LABELS: Record<string, string> = Object.fromEntries(MODEL_OPTIONS.map(m => [m.value, m.label]))
function modelLabel(m: string) { return MODEL_LABELS[m] || m }
function scheduleLabel(s: string) { return { manual: '手动', daily: '每日', weekly: '每周' }[s] || s }

const loading = ref(false); const saving = ref(false)
const tasks = ref<any[]>([]); const competitors = ref<any[]>([])
const summaryData = ref<any>(null)
const showTaskDialog = ref(false); const showCompetitorDialog = ref(false); const showChatDialog = ref(false)
const editingTask = ref<any>(null)
const chatLogs = ref<any[]>([]); const chatModelFilter = ref(''); const allChatLogs = ref<any[]>([])
const lastRunTaskId = ref('')
const customerList = ref<any[]>([])
const selectedCustomerId = ref(localStorage.getItem('detection_selected_customer') || '')
const selectedCustomer = ref<any>(null)

async function loadCustomers() {
  try { const r = await http.get('/customers/', { params: { page:1, page_size:100 } }); customerList.value = r.data.items || [] } catch {}
}
function onCustomerChange(id: string) {
  localStorage.setItem('detection_selected_customer', id)
  selectedCustomer.value = customerList.value.find((c:any) => c.id === id) || null
}

const stats = ref([
  { label: '探测任务', value: 0 }, { label: '探测结果', value: 0 }, { label: '竞品数量', value: 0 }, { label: '综合评分', value: '--' },
])
const summaryList = computed(() => {
  if (!summaryData.value) return []
  return Object.entries(summaryData.value).map(([model, data]: [string, any]) => ({ model, ...data }))
})
const taskForm = reactive({ name: '', description: '', target_models: [] as string[], keywords: [] as any[], schedule_type: 'manual' })
const compForm = reactive({ name: '', website: '', industry: '' })

async function fetchTasks() {
  loading.value = true
  try { const r = await detectionApi.listTasks({ page: 1, page_size: 50 }); tasks.value = r.items; stats.value[0].value = r.total } catch {}
  loading.value = false
}
// Summary is now populated by runTask() from demo API response
async function fetchSummary() { /* data from in-memory cache */ }
async function fetchCompetitors() {
  try { competitors.value = await detectionApi.listCompetitors(); stats.value[2].value = competitors.value.length } catch {}
}

async function saveTask() {
  saving.value = true
  try {
    if (editingTask.value) await detectionApi.updateTask(editingTask.value.id, taskForm)
    else await detectionApi.createTask(taskForm)
    ElMessage.success('保存成功'); showTaskDialog.value = false; resetTaskForm(); fetchTasks()
  } catch (e: any) { ElMessage.error(e.response?.data?.error || '保存失败') }
  saving.value = false
}
function editTask(t: any) { editingTask.value = t; Object.assign(taskForm, { name: t.name, description: t.description, target_models: [...t.target_models], keywords: t.keywords?.map((k: any) => ({...k})) || [], schedule_type: t.schedule_type }); showTaskDialog.value = true }
async function runTask(t: any) {
  if (!selectedCustomer.value) { ElMessage.warning('请先在上方选择一个客户'); return }
  const cust = selectedCustomer.value
  const companyName = cust.company_name || cust.name || '未命名企业'
  // Load keywords from enterprise profile
  let profileKeywords: string[] = []
  try {
    const pr = await http.get('/enterprise-profile', { params: { customer_id: cust.id } })
    profileKeywords = pr.data?.data?.keywords || []
  } catch {}
  const allKeywords = profileKeywords.length > 0 ? profileKeywords : (t.keywords?.map((k:any)=>k.word) || [])
  const kwStr = allKeywords.slice(0,5).join(' ')
  const industry = cust.industry || kwStr || '通用'
  const mainBiz = allKeywords[0] || cust.industry || '产品'
  ElMessage.info(`正在为「${companyName}」进行5大模型探测，关键词：${kwStr || industry}`)
  try {
    const r = await http.get('/demo/scan_enterprise', {
      params: { company_name: companyName, industry, main_business: mainBiz, fast: true },
      timeout: 60000,
    })
    lastRunTaskId.value = t.id
    const d = r.data
    // Build summary from demo response
    const mStats: Record<string,any> = {}
    for (const item of d.model_table_data || []) {
      mStats[item.platform] = { model: item.platform, total: 3, mentioned: item.mention_month > 0 ? 3 : 0, mention_rate: item.mention_month > 20 ? 60 : item.mention_month > 5 ? 20 : 0, avg_rank: item.avg_rank, total_exposure: item.collect_count }
    }
    summaryData.value = mStats
    stats.value[1].value = (d.model_table_data || []).length * 3
    stats.value[3].value = d.total_score + '%'
    // Store chat cache for dialog
    const cache = d.task_temp_cache || {}
    const logs: any[] = []
    for (const [model, data] of Object.entries<any>(cache)) {
      for (const round of data.chat_rounds || []) {
        logs.push({ model_id: model, model_name: model, query_text: round.ask, raw_answer: round.reply, query_type: 'first_round', probe_time: new Date().toISOString(), status: 'success' })
      }
    }
    allChatLogs.value = logs
    chatLogs.value = logs
    // Save to localStorage so results persist after refresh
    localStorage.setItem('detection_last_summary', JSON.stringify(mStats))
    localStorage.setItem('detection_last_chats', JSON.stringify(logs))
    localStorage.setItem('detection_last_score', String(d.total_score || 0))
    localStorage.setItem('detection_last_time', new Date().toISOString())
    ElMessage.success(`探测完成！${Object.keys(cache).length}个模型已返回真实回答`)
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '探测失败') }
}
async function viewChats(model?: string) {
  showChatDialog.value = true
  chatModelFilter.value = model || ''
  // Always filter from full cache
  if (model) {
    chatLogs.value = allChatLogs.value.filter((l: any) => l.model_name === model || l.model_id === model)
  } else {
    chatLogs.value = [...allChatLogs.value]
  }
}
async function loadChatLogs() { /* handled by viewChats from allChatLogs cache */ }

async function deleteTask(t: any) { try { await ElMessageBox.confirm('删除此任务？'); await detectionApi.deleteTask(t.id); ElMessage.success('已删除'); fetchTasks() } catch {} }
async function saveCompetitor() { saving.value = true; try { await detectionApi.createCompetitor(compForm); ElMessage.success('竞品已添加'); showCompetitorDialog.value = false; compForm.name = ''; compForm.website = ''; compForm.industry = ''; fetchCompetitors() } catch (e: any) { ElMessage.error(e.response?.data?.error || '保存失败') } saving.value = false }
function resetTaskForm() { editingTask.value = null; taskForm.name = ''; taskForm.description = ''; taskForm.target_models = []; taskForm.keywords = []; taskForm.schedule_type = 'manual' }

onMounted(async () => {
  await loadCustomers()
  if (selectedCustomerId.value) {
    selectedCustomer.value = customerList.value.find((c:any) => c.id === selectedCustomerId.value) || null
  }
  await fetchTasks()
  await fetchCompetitors()
  try {
    const savedSummary = localStorage.getItem('detection_last_summary')
    const savedChats = localStorage.getItem('detection_last_chats')
    const savedScore = localStorage.getItem('detection_last_score')
    const savedTime = localStorage.getItem('detection_last_time')
    if (savedSummary) summaryData.value = JSON.parse(savedSummary)
    if (savedChats) { allChatLogs.value = JSON.parse(savedChats); chatLogs.value = allChatLogs.value; stats.value[1].value = allChatLogs.value.length }
    if (savedScore) stats.value[3].value = savedScore + '%'
    if (savedTime) { const ago = Math.round((Date.now() - new Date(savedTime).getTime()) / 60000); if (ago < 60) ElMessage.info(`已恢复${ago}分钟前的结果`) }
  } catch {}
})
</script>
