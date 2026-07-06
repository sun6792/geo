<template>
  <div class="page-container">
    <div class="page-header"><h2>服务档位配置</h2><el-button type="primary" @click="showPlanDialog=true">新增套餐</el-button></div>
    <div class="stat-cards">
      <div class="stat-card" v-for="plan in plans" :key="plan.id">
        <div class="stat-label">【{{ tierLabel(plan.tier) }}】{{ plan.name }}</div>
        <div class="stat-value">¥{{ plan.monthly_price }}/月</div>
        <div style="font-size:12px;color:#909399;margin-top:4px">年付 ¥{{ plan.yearly_price }}/年</div>
        <div style="margin-top:8px">
          <el-tag v-for="(f,i) in (plan.features||[])" :key="i" size="small" style="margin:2px">{{ f }}</el-tag>
        </div>
        <div style="margin-top:8px">
          用户{{ plan.quotas?.max_users || '-' }} · 资产{{ plan.quotas?.max_kb_assets || '-' }} · 月内容{{ plan.quotas?.max_content_month || '-' }} · LLM调用{{ plan.quotas?.max_llm_calls_month || '-' }}
        </div>
        <div style="margin-top:8px">
          <el-button size="small" @click="editPlan(plan)">编辑</el-button>
          <el-tag :type="plan.is_active?'success':'info'" size="small">{{ plan.is_active?'启用':'停用' }}</el-tag>
        </div>
      </div>
    </div>
    <!-- Plan Edit Dialog -->
    <el-dialog v-model="showPlanDialog" title="套餐配置" width="550px">
      <el-form :model="planForm" label-width="100px">
        <el-form-item label="名称"><el-input v-model="planForm.name" /></el-form-item>
        <el-form-item label="编码"><el-input v-model="planForm.code" /></el-form-item>
        <el-form-item label="档位"><el-select v-model="planForm.tier" style="width:100%"><el-option :value="1" label="基础版" /><el-option :value="2" label="专业版" /><el-option :value="3" label="企业版" /></el-select></el-form-item>
        <el-form-item label="月价(元)"><el-input-number v-model="planForm.monthly_price" :min="0" :step="100" style="width:100%" /></el-form-item>
        <el-form-item label="年价(元)"><el-input-number v-model="planForm.yearly_price" :min="0" :step="1000" style="width:100%" /></el-form-item>
        <el-form-item label="用户上限"><el-input-number v-model="planForm.max_users" :min="1" :max="9999" /></el-form-item>
        <el-form-item label="资产上限"><el-input-number v-model="planForm.max_kb_assets" :min="100" :max="99999" /></el-form-item>
        <el-form-item label="月内容上限"><el-input-number v-model="planForm.max_content" :min="10" :max="9999" /></el-form-item>
        <el-form-item label="LLM调用上限"><el-input-number v-model="planForm.max_llm" :min="100" :max="999999" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="planForm.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showPlanDialog=false">取消</el-button><el-button type="primary" @click="handleSavePlan" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api/index'
const plans = ref<any[]>([]); const showPlanDialog = ref(false); const saving = ref(false); const editingId = ref('')
const planForm = reactive({ name:'', code:'', tier:1, monthly_price:999, yearly_price:9990, max_users:10, max_kb_assets:2000, max_content:200, max_llm:2000, is_active:true })
function tierLabel(t: number) { return {1:'基础版',2:'专业版',3:'企业版'}[t]||'--' }
async function fetchPlans() { try { plans.value = (await http.get('/billing/plans')).data || [] } catch {} }
function editPlan(p: any) { editingId.value = p.id; Object.assign(planForm, { name:p.name, code:p.code, tier:p.tier, monthly_price:p.monthly_price, yearly_price:p.yearly_price, max_users:p.quotas?.max_users||10, max_kb_assets:p.quotas?.max_kb_assets||2000, max_content:p.quotas?.max_content_month||200, max_llm:p.quotas?.max_llm_calls_month||2000, is_active:p.is_active }); showPlanDialog.value = true }
async function handleSavePlan() {
  saving.value = true
  try {
    const payload = { name: planForm.name, code: planForm.code, tier: planForm.tier, monthly_price: planForm.monthly_price, yearly_price: planForm.yearly_price, quotas: { max_users: planForm.max_users, max_kb_assets: planForm.max_kb_assets, max_content_month: planForm.max_content, max_llm_calls_month: planForm.max_llm, max_detection_tasks: 20, max_channels: 10 }, is_active: planForm.is_active }
    if (editingId.value) { await http.patch('/billing/plans/' + editingId.value, payload) } else { await http.post('/billing/plans', payload) }
    ElMessage.success('保存成功'); showPlanDialog.value = false; editingId.value = ''; fetchPlans()
  } catch (e: any) { ElMessage.error(e.response?.data?.error || '保存失败') }
  saving.value = false
}
onMounted(fetchPlans)
</script>
