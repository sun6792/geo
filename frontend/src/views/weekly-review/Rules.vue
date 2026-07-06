<template>
  <div class="page-container">
    <div class="page-header">
      <h2>GEO 规则库管理</h2>
      <span style="color:#909399;font-size:13px">基于探测数据反推的各模型权重规则</span>
    </div>
    <div class="search-bar">
      <el-select v-model="filterModel" placeholder="筛选模型" clearable @change="fetchRules" style="width:200px">
        <el-option v-for="m in MODEL_OPTIONS" :key="m.value" :label="m.label" :value="m.value" />
      </el-select>
    </div>
    <div class="table-card">
      <el-table :data="rules" v-loading="loading" stripe>
        <el-table-column label="模型" width="120">
          <template #default="{row}"><el-tag>{{ modelLabel(row.model_name) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="rule_name" label="规则名称" min-width="200" />
        <el-table-column label="分类" width="120">
          <template #default="{row}">{{ categoryLabel(row.rule_category) }}</template>
        </el-table-column>
        <el-table-column prop="rule_content" label="规则内容" min-width="300" show-overflow-tooltip />
        <el-table-column label="置信度" width="120">
          <template #default="{row}">
            <el-progress :percentage="Math.round(row.confidence*100)" :color="row.confidence>0.8?'#67c23a':row.confidence>0.6?'#e6a23c':'#f56c6c'" />
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="60" />
        <el-table-column label="操作" width="160">
          <template #default="{row}">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" @click="viewVersions(row)">历史</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Edit Rule Dialog -->
    <el-dialog v-model="showEdit" title="编辑规则" width="500px">
      <el-form label-width="80px">
        <el-form-item label="规则内容"><el-input v-model="editForm.rule_content" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="置信度"><el-slider v-model="editForm.confidence" :min="0" :max="1" :step="0.05" show-input /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="editForm.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showEdit=false">取消</el-button><el-button type="primary" @click="saveRule" :loading="saving">保存</el-button></template>
    </el-dialog>

    <!-- Version History Dialog -->
    <el-dialog v-model="showVersions" title="版本历史" width="700px">
      <el-timeline>
        <el-timeline-item v-for="v in versions" :key="v.id" :timestamp="formatDate(v.created_at)" placement="top">
          <el-card>
            <p><b>v{{ v.version }}</b> (置信度: {{ Math.round(v.confidence*100) }}%)</p>
            <p>{{ v.rule_content }}</p>
            <el-tag size="small" :type="v.is_latest?'success':'info'">{{ v.is_latest ? '当前版本' : '历史版本' }}</el-tag>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { weeklyReviewApi } from '@/api/detection'
import { formatDate } from '@/utils/format'

const MODEL_OPTIONS = [
  { label: '豆包', value: 'doubao' }, { label: '文心一言', value: 'wenxin' }, { label: '通义千问', value: 'qianwen' },
  { label: '腾讯元宝', value: 'yuanbao' }, { label: '讯飞星火', value: 'xinghuo' }, { label: 'DeepSeek', value: 'deepseek' }, { label: 'Kimi', value: 'kimi' },
]
const MODEL_LABELS: Record<string, string> = Object.fromEntries(MODEL_OPTIONS.map(m => [m.value, m.label]))
function modelLabel(m: string) { return MODEL_LABELS[m] || m }
function categoryLabel(c: string) { return { ranking: '排名规则', recommendation: '推荐规则', source_weight: '信源权重', content_quality: '内容质量', freshness: '新鲜度' }[c] || c }

const loading = ref(false); const saving = ref(false)
const rules = ref<any[]>([]); const filterModel = ref('')
const showEdit = ref(false); const showVersions = ref(false)
const editingRule = ref<any>(null); const versions = ref<any[]>([])
const editForm = reactive({ rule_content: '', confidence: 0.7, is_active: true })

async function fetchRules() {
  loading.value = true
  try { rules.value = await weeklyReviewApi.listRules(filterModel.value ? { model_name: filterModel.value } : undefined) } catch {}
  loading.value = false
}
function openEdit(r: any) { editingRule.value = r; editForm.rule_content = r.rule_content; editForm.confidence = r.confidence; editForm.is_active = r.is_active; showEdit.value = true }
async function saveRule() {
  if (!editingRule.value) return; saving.value = true
  try { await weeklyReviewApi.updateRule(editingRule.value.id, editForm); ElMessage.success('规则已更新(新版本)'); showEdit.value = false; fetchRules() } catch (e: any) { ElMessage.error(e.response?.data?.error || '更新失败') }
  saving.value = false
}
async function viewVersions(r: any) { try { versions.value = await weeklyReviewApi.getRuleVersions(r.id); showVersions.value = true } catch {} }

onMounted(() => fetchRules())
</script>
