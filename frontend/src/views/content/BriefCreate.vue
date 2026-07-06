<template>
  <div class="page-container">
    <div class="page-header"><h2>新建创作任务</h2></div>
    <div class="table-card" style="max-width:800px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="创作标题" prop="title"><el-input v-model="form.title" placeholder="如：XX品牌GEO深度主稿" maxlength="200" /></el-form-item>
        <el-form-item label="内容类型" prop="content_type">
          <el-select v-model="form.content_type" style="width:100%">
            <el-option label="深度主稿" value="blog_post" /><el-option label="社交短文" value="social_media" />
            <el-option label="新闻稿" value="press_release" /><el-option label="产品页" value="product_page" />
          </el-select>
        </el-form-item>
        <el-form-item label="语气风格"><el-select v-model="form.tone_style" style="width:100%">
          <el-option label="专业严谨" value="professional" /><el-option label="生动活泼" value="casual" /><el-option label="技术深度" value="technical" /></el-select>
        </el-form-item>
        <el-form-item label="目标字数"><el-input-number v-model="form.word_count_target" :min="200" :max="5000" :step="200" /></el-form-item>
        <el-form-item label="目标受众"><el-input v-model="form.target_audience" placeholder="如：制造业采购经理、技术决策者" /></el-form-item>
        <el-form-item label="知识库来源" prop="source_kb_asset_ids">
          <div style="margin-bottom:8px;color:#e6a23c;font-size:13px">⚠️ 必须选择知识库资产作为信息来源，否则无法创作</div>
          <el-select v-model="form.source_kb_asset_ids" multiple filterable placeholder="搜索并选择知识库资产" style="width:100%" :loading="kbLoading" @focus="fetchKbAssets">
            <el-option v-for="a in kbAssets" :key="a.id" :label="a.title" :value="a.id">
              <span>{{ a.title }}</span><el-tag size="small" style="margin-left:8px">{{ a.asset_type }}</el-tag>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="关键词"><el-input v-model="keywordInput" placeholder="输入关键词后回车添加" @keyup.enter="addKeyword"><template #append><el-button @click="addKeyword">添加</el-button></template></el-input>
          <el-tag v-for="(k,i) in form.target_keywords" :key="i" closable @close="form.target_keywords.splice(i,1)" style="margin:2px">{{ k }}</el-tag>
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" placeholder="补充创作要求..." /></el-form-item>
        <el-form-item><el-button @click="$router.back()">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">创建并生成</el-button></el-form-item>
      </el-form>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contentApi } from '@/api/content'
import { kbApi } from '@/api/knowledgeBase'
import type { FormInstance } from 'element-plus'
const router = useRouter(); const formRef = ref<FormInstance>()
const loading = ref(false); const saving = ref(false); const kbLoading = ref(false); const kbAssets = ref<any[]>([]); const keywordInput = ref('')
const form = reactive({ title: '', content_type: 'blog_post', tone_style: 'professional', word_count_target: 800, target_audience: '', source_kb_asset_ids: [] as string[], target_keywords: [] as string[], description: '' })
const rules = { title: [{ required: true, message: '请输入标题' }], content_type: [{ required: true }], source_kb_asset_ids: [{ required: true, type: 'array', min: 1, message: '必须选择知识库资产' }] }
async function fetchKbAssets() { if (kbAssets.value.length) return; kbLoading.value = true; try { const r = await kbApi.listAssets({ page: 1, page_size: 100 }); kbAssets.value = r.items || [] } catch {}; kbLoading.value = false }
function addKeyword() { const k = keywordInput.value.trim(); if (k && !form.target_keywords.includes(k)) form.target_keywords.push(k); keywordInput.value = '' }
async function handleSave() {
  if (!formRef.value) return; if (!(await formRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    const brief = await contentApi.createBrief({ ...form, source_kb_asset_ids: form.source_kb_asset_ids })
    ElMessage.success('创作任务已创建')
    try { await contentApi.generate(brief.id); ElMessage.success('AI 内容生成已触发') } catch {}
    router.push('/content')
  } catch (e: any) { ElMessage.error(e.response?.data?.error || '创建失败') }
  saving.value = false
}
</script>
