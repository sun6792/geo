<template>
  <div class="page-container">
    <div class="page-header">
      <h2>全域探测采集 (智能体 1)</h2>
      <div>
        <el-button @click="showTaskDialog = true" type="primary">新建探测任务</el-button>
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
          <template #default="{ row }"><el-tag :type="row.is_active?'success':'info'" size="small">{{ row.is_active ? '运行中' : '已停用' }}</el-tag></template>
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
      <div class="section-title">探测结果概览（按模型汇总）</div>
      <el-table :data="summaryList" stripe>
        <el-table-column prop="model" label="大模型" width="120"><template #default="{row}">{{ modelLabel(row.model) }}</template></el-table-column>
        <el-table-column prop="mention_rate" label="品牌提及率(%)" width="140" />
        <el-table-column prop="avg_rank" label="平均排名" width="100" />
        <el-table-column prop="total_exposure" label="总曝光量" width="100" />
        <el-table-column prop="mentioned" label="提及次数" width="100" />
        <el-table-column prop="total" label="总探测次数" width="120" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { detectionApi } from '@/api/detection'
import { formatDate } from '@/utils/format'

const MODEL_OPTIONS = [
  { label: '豆包', value: 'doubao' }, { label: '文心一言', value: 'wenxin' }, { label: '通义千问', value: 'qianwen' },
  { label: '腾讯元宝', value: 'yuanbao' }, { label: '讯飞星火', value: 'xinghuo' }, { label: 'DeepSeek', value: 'deepseek' }, { label: 'Kimi', value: 'kimi' },
]
const MODEL_LABELS: Record<string, string> = Object.fromEntries(MODEL_OPTIONS.map(m => [m.value, m.label]))
function modelLabel(m: string) { return MODEL_LABELS[m] || m }
function scheduleLabel(s: string) { return { manual: '手动', daily: '每日', weekly: '每周' }[s] || s }

const loading = ref(false); const saving = ref(false)
const tasks = ref<any[]>([]); const competitors = ref<any[]>([])
const summaryData = ref<any>(null)
const showTaskDialog = ref(false); const showCompetitorDialog = ref(false)
const editingTask = ref<any>(null)

const stats = ref([
  { label: '探测任务', value: 0 }, { label: '探测结果', value: 0 }, { label: '竞品数量', value: 0 }, { label: '品牌提及率', value: '--' },
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
async function fetchSummary() {
  try {
    summaryData.value = await detectionApi.getSummary()
    let total = 0; let mentioned = 0
    for (const d of Object.values<any>(summaryData.value)) { total += d.total; mentioned += d.mentioned }
    stats.value[3].value = total > 0 ? Math.round(mentioned / total * 100) + '%' : '--'
  } catch {}
}
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
async function runTask(t: any) { try { await detectionApi.runTask(t.id); ElMessage.success('探测已启动'); fetchTasks(); fetchSummary() } catch (e: any) { ElMessage.error(e.response?.data?.error || '执行失败') } }
async function deleteTask(t: any) { try { await ElMessageBox.confirm('删除此任务？'); await detectionApi.deleteTask(t.id); ElMessage.success('已删除'); fetchTasks() } catch {} }
async function saveCompetitor() { saving.value = true; try { await detectionApi.createCompetitor(compForm); ElMessage.success('竞品已添加'); showCompetitorDialog.value = false; compForm.name = ''; compForm.website = ''; compForm.industry = ''; fetchCompetitors() } catch (e: any) { ElMessage.error(e.response?.data?.error || '保存失败') } saving.value = false }
function resetTaskForm() { editingTask.value = null; taskForm.name = ''; taskForm.description = ''; taskForm.target_models = []; taskForm.keywords = []; taskForm.schedule_type = 'manual' }

onMounted(() => { fetchTasks(); fetchSummary(); fetchCompetitors() })
</script>
