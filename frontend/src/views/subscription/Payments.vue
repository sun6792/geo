<template>
  <div class="page-container">
    <div class="page-header"><h2>付费记录</h2><el-button type="primary" @click="showDialog=true">新增付费记录</el-button></div>
    <div class="table-card">
      <el-table :data="records" v-loading="loading" stripe>
        <el-table-column prop="company_name" label="企业名称" min-width="150" />
        <el-table-column prop="plan_name" label="套餐" width="100" />
        <el-table-column label="金额" width="100"><template #default="{row}">¥{{ row.amount }}</template></el-table-column>
        <el-table-column prop="billing_cycle" label="周期" width="80" />
        <el-table-column prop="service_start" label="起止" width="180"><template #default="{row}">{{ row.service_start }} ~ {{ row.service_end }}</template></el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{row}">
            <el-button size="small" type="success" @click="handleGenerate(row)" v-if="!row.sub_account_id">生成子账号</el-button>
            <el-tag size="small" type="success" v-else>已生成</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="showDialog" title="新增付费记录" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="客户ID"><el-input v-model="form.customer_id" /></el-form-item>
        <el-form-item label="企业名称"><el-input v-model="form.company_name" /></el-form-item>
        <el-form-item label="套餐"><el-select v-model="form.plan_name" style="width:100%"><el-option value="basic" label="基础版" /><el-option value="professional" label="专业版" /><el-option value="enterprise" label="企业版" /></el-select></el-form-item>
        <el-form-item label="金额"><el-input-number v-model="form.amount" :min="0" :step="1000" style="width:100%" /></el-form-item>
        <el-form-item label="周期"><el-select v-model="form.billing_cycle" style="width:100%"><el-option value="yearly" label="按年" /><el-option value="monthly" label="按月" /></el-select></el-form-item>
        <el-form-item label="服务起始"><el-date-picker v-model="form.service_start" type="date" style="width:100%" /></el-form-item>
        <el-form-item label="到期日"><el-date-picker v-model="form.service_end" type="date" style="width:100%" /></el-form-item>
        <el-form-item label="支付方式"><el-input v-model="form.payment_method" placeholder="如：银行转账、微信" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api/index'
const loading = ref(false); const saving = ref(false); const records = ref<any[]>([]); const showDialog = ref(false)
const today = new Date().toISOString().slice(0,10); const nextYear = (new Date().getFullYear()+1)+today.slice(4)
const form = reactive({ customer_id: '', company_name: '', plan_name: 'professional', amount: 29990, billing_cycle: 'yearly', service_start: today, service_end: nextYear, payment_method: '', notes: '' })
async function fetchRecords() { loading.value = true; try { const r = await http.get('/p5/payment-records', { params: { page: 1, page_size: 50 } }); records.value = r.data.items || [] } catch {}; loading.value = false }
async function handleSave() { saving.value = true; try { await http.post('/p5/payment-records', form); ElMessage.success('已保存'); showDialog.value = false; fetchRecords() } catch (e: any) { ElMessage.error(e.response?.data?.error || '保存失败') }; saving.value = false }
async function handleGenerate(row: any) {
  try {
    const email = await ElMessageBox.prompt('请输入客户邮箱', '生成子账号', { confirmButtonText: '确定' })
    const r = await http.post('/p5/payment-records/' + row.id + '/create-sub', { email: email.value })
    ElMessage.success('子账号已创建！密码: ' + r.data.password); fetchRecords()
  } catch {}
}
onMounted(fetchRecords)
</script>
