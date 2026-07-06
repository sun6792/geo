<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ draft?.title || '稿件详情' }}</h2>
      <div>
        <el-button @click="handleSubmit" type="primary" v-if="draft?.status==='draft'" :loading="submitting">提交审核</el-button>
        <el-button @click="$router.back()">返回</el-button>
      </div>
    </div>
    <div class="detail-section" v-if="draft" v-loading="loading">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="版本">{{ draft.version }}</el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag size="small">{{ draft.status }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="字数">{{ draft.word_count || 0 }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ draft.created_at?.slice(0,16) }}</el-descriptions-item>
        <el-descriptions-item label="知识库来源" :span="2">{{ (draft.kb_sources||[]).map((s:any)=>s.title).join(', ') || '无' }}</el-descriptions-item>
      </el-descriptions>
      <h4 style="margin:16px 0 8px">稿件内容</h4>
      <div style="padding:16px;background:#f9fafb;border-radius:8px;white-space:pre-wrap;font-family:monospace;font-size:14px;line-height:1.8;max-height:600px;overflow-y:auto" v-text="draft.body_markdown || '（无内容）'" />
    </div>
    <div v-else class="table-card"><el-empty description="稿件未找到" /></div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contentApi } from '@/api/content'
import { reviewApi } from '@/api/review'
const route = useRoute(); const router = useRouter()
const loading = ref(false); const submitting = ref(false); const draft = ref<any>(null)
const draftId = route.params.id as string
async function fetchDraft() { loading.value = true; try { draft.value = await contentApi.getDraft(draftId) } catch {}; loading.value = false }
async function handleSubmit() { submitting.value = true; try { await reviewApi.submitForReview(draftId); ElMessage.success('已提交审核'); draft.value.status = 'in_review' } catch (e: any) { ElMessage.error(e.response?.data?.error || '提交失败') }; submitting.value = false }
onMounted(fetchDraft)
</script>
