<template>
  <div class="page-container">
    <div class="page-header"><h2>行业模板</h2></div>
    <div class="search-bar">
      <el-select v-model="filterIndustry" placeholder="筛选行业" clearable @change="fetchTemplates" style="width:200px">
        <el-option v-for="ind in industries" :key="ind" :label="industryLabel(ind)" :value="ind" />
      </el-select>
    </div>
    <div class="stat-cards">
      <div class="stat-card" v-for="t in templates" :key="t.id" style="cursor:pointer" @click="viewTemplate(t)">
        <div class="stat-label">{{ industryLabel(t.industry) }} · {{ t.name }}</div>
        <div class="stat-value" style="font-size:14px;line-height:1.6">{{ t.description || t.use_case || '暂无描述' }}</div>
        <div style="margin-top:8px">
          <el-tag size="small" type="success" v-if="t.is_system">系统预置</el-tag>
          <el-tag size="small" v-else>自定义</el-tag>
          <span style="color:#909399;font-size:12px;margin-left:8px">{{ t.preset_keywords?.length || 0 }}个关键词 | {{ t.asset_structure?.length || 0 }}项资产</span>
        </div>
      </div>
    </div>
    <!-- Template Detail & Initialize Dialog -->
    <el-dialog v-model="showDetail" :title="selected?.name" width="700px">
      <div v-if="selected">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="行业">{{ industryLabel(selected.industry) }}</el-descriptions-item>
          <el-descriptions-item label="适用场景">{{ selected.use_case || '--' }}</el-descriptions-item>
          <el-descriptions-item label="关键词数">{{ selected.preset_keywords?.length || 0 }}</el-descriptions-item>
          <el-descriptions-item label="资产模板">{{ selected.asset_structure?.length || 0 }}项</el-descriptions-item>
          <el-descriptions-item label="推荐渠道">{{ selected.recommended_channels?.length || 0 }}个</el-descriptions-item>
          <el-descriptions-item label="内容风格">{{ selected.content_strategy?.tone_style || '--' }}</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top:12px;padding:12px;background:#f0f9eb;border-radius:8px;text-align:center">
          <p style="color:#67c23a;margin-bottom:8px">一键初始化将自动创建：知识库结构 + 探测关键词 + 竞品配置 + 推荐渠道</p>
          <el-button type="success" size="large" @click="handleInit" :loading="initializing" :disabled="!customerId">执行一键初始化</el-button>
          <div v-if="!customerId" style="color:#f56c6c;font-size:12px;margin-top:4px">请先从客户管理选择当前客户</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api/index'
import { useAuthStore } from '@/store/auth'
const authStore = useAuthStore()
const customerId = ref(authStore.user?.customer_id || '')
const templates = ref<any[]>([]); const industries = ref<string[]>([]); const filterIndustry = ref('')
const showDetail = ref(false); const selected = ref<any>(null); const initializing = ref(false)
function industryLabel(i: string) {
  return { manufacturing:'制造业', local_service:'本地服务', ecommerce:'电商', education:'教育', healthcare:'医疗健康', technology:'科技' }[i] || i
}
async function fetchTemplates() {
  try {
    const r = await http.get('/templates/templates', { params: { industry: filterIndustry.value || undefined } })
    templates.value = r.data || []
  } catch {}
}
async function fetchIndustries() {
  try { industries.value = (await http.get('/templates/templates/industries')).data || [] } catch {}
}
function viewTemplate(t: any) { selected.value = t; showDetail.value = true }
async function handleInit() {
  if (!selected.value) return
  initializing.value = true
  try {
    const r = await http.post('/templates/templates/' + selected.value.id + '/initialize')
    ElMessage.success(`初始化完成：创建了${r.data.stats?.assets||0}个资产、${r.data.stats?.keywords||0}个关键词、${r.data.stats?.competitors||0}个竞品`)
    showDetail.value = false
  } catch (e: any) { ElMessage.error(e.response?.data?.error || '初始化失败') }
  initializing.value = false
}
onMounted(() => { fetchTemplates(); fetchIndustries() })
</script>
