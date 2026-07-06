<template>
  <div class="page-container">
    <div class="page-header"><h2>内部审核</h2></div>
    <div v-if="review" v-loading="loading" style="max-width:900px">
      <div class="detail-section">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="审核阶段">内部初审</el-descriptions-item>
          <el-descriptions-item label="状态"><el-tag :type="review.status==='approved'?'success':review.status==='rejected'?'danger':'warning'">{{ review.status }}</el-tag></el-descriptions-item>
        </el-descriptions>
      </div>
      <div class="detail-section" v-if="review.comments?.length">
        <div class="section-title">审核意见</div>
        <div v-for="c in review.comments" :key="c.id" style="padding:8px 0;border-bottom:1px solid #ebeef5">
          <div style="color:#909399;font-size:12px;margin-bottom:4px">{{ c.created_at?.slice(0,16) }}</div>
          <div>{{ c.comment_text }}</div>
        </div>
      </div>
      <div class="detail-section">
        <div class="section-title">审核操作</div>
        <el-input v-model="comment" type="textarea" :rows="3" placeholder="审核意见（选填）" style="margin-bottom:12px" />
        <el-button type="success" @click="handleAction('approve')" :loading="acting">通过</el-button>
        <el-button type="danger" @click="handleAction('reject')" :loading="acting">驳回</el-button>
        <el-button @click="handleAction('request_changes')" :loading="acting">需修改</el-button>
      </div>
      <div class="detail-section" v-if="review.status==='approved'">
        <div class="section-title">推送客户审核</div>
        <el-form :inline="true"><el-form-item label="客户邮箱"><el-input v-model="clientEmail" /></el-form-item><el-form-item label="客户姓名"><el-input v-model="clientName" /></el-form-item>
          <el-form-item><el-button type="primary" @click="advanceToClient" :loading="advancing">推送</el-button></el-form-item></el-form>
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
const loading = ref(false); const acting = ref(false); const advancing = ref(false)
const comment = ref(''); const clientEmail = ref(''); const clientName = ref('')
const reviewId = route.params.id as string
async function fetchReview() { loading.value = true; try { review.value = await reviewApi.get(reviewId) } catch {}; loading.value = false }
async function handleAction(action: string) { acting.value = true; try { action === 'approve' ? await reviewApi.approve(reviewId, comment.value) : action === 'reject' ? await reviewApi.reject(reviewId, comment.value) : await reviewApi.requestChanges(reviewId, comment.value); ElMessage.success('操作成功'); fetchReview() } catch (e: any) { ElMessage.error(e.response?.data?.error || '操作失败') }; acting.value = false }
async function advanceToClient() { if (!clientEmail.value) return ElMessage.warning('请输入客户邮箱'); advancing.value = true; try { await reviewApi.advanceToClient(review.value.draft_id, { client_email: clientEmail.value, client_name: clientName.value }); ElMessage.success('已推送客户审核') } catch (e: any) { ElMessage.error(e.response?.data?.error || '推送失败') }; advancing.value = false }
onMounted(fetchReview)
</script>
