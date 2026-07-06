<template>
  <div class="page-container">
    <div class="page-header"><h2>客户审核</h2></div>
    <div v-if="review" v-loading="loading" style="max-width:800px">
      <div class="detail-section">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="客户">{{ review.client_reviewer_name || review.client_reviewer_email }}</el-descriptions-item>
          <el-descriptions-item label="状态"><el-tag :type="review.status==='approved'?'success':'warning'">{{ review.status }}</el-tag></el-descriptions-item>
        </el-descriptions>
      </div>
      <div class="detail-section">
        <div class="section-title">审核操作</div>
        <el-input v-model="comment" type="textarea" :rows="3" placeholder="审核意见（选填）" style="margin-bottom:12px" />
        <el-button type="success" size="large" @click="handleAction('approve')" :loading="acting">确认通过</el-button>
        <el-button type="danger" size="large" @click="handleAction('reject')" :loading="acting">驳回</el-button>
      </div>
    </div>
    <div v-else class="table-card"><el-empty description="审核记录未找到" /></div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { reviewApi } from '@/api/review'
const route = useRoute(); const review = ref<any>(null)
const loading = ref(false); const acting = ref(false); const comment = ref('')
const token = route.params.token as string
async function fetchReview() {
  loading.value = true
  try { review.value = (await (await fetch('/api/public/review/' + token)).json()) } catch {}
  loading.value = false
}
async function handleAction(action: string) {
  acting.value = true
  const url = '/api/public/review/' + token + '/' + (action === 'approve' ? 'approve' : 'reject')
  try { await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ comment: comment.value }) }); ElMessage.success('操作成功'); review.value.status = action + 'd' } catch { ElMessage.error('操作失败') }
  acting.value = false
}
</script>
