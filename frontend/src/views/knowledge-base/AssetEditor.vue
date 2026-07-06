<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ isEdit ? '编辑资产' : '新建资产' }}</h2>
    </div>

    <div class="table-card" style="max-width:800px" v-loading="loading">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 资产名称 -->
        <el-form-item label="资产名称" prop="title">
          <el-input v-model="form.title" placeholder="请输入资产标题/名称" maxlength="200" show-word-limit />
        </el-form-item>

        <!-- 资产类型 -->
        <el-form-item label="资产类型" prop="asset_type">
          <el-select v-model="form.asset_type" placeholder="选择资产类型" @change="onTypeChange" style="width:100%">
            <el-option label="基础资产 (企业简介/产品参数/资质等)" value="basic" />
            <el-option label="营销资产 (案例/关键词/话术等)" value="marketing" />
            <el-option label="多模态资产 (图片/视频/白皮书等)" value="multimodal" />
          </el-select>
        </el-form-item>

        <!-- 内容分类 -->
        <el-form-item label="内容分类" prop="content_type">
          <el-select v-model="form.content_type" placeholder="选择内容分类" style="width:100%">
            <el-option v-for="c in contentTypeOptions" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>

        <!-- 基础/营销资产: 文本内容 -->
        <el-form-item v-if="form.asset_type !== 'multimodal'" label="资产内容" prop="content_text">
          <el-input v-model="form.content_text" type="textarea" :rows="10" placeholder="请输入资产详细内容（支持 Markdown 格式）" />
        </el-form-item>

        <!-- 多模态资产: 文件上传 -->
        <el-form-item v-if="form.asset_type === 'multimodal'" label="上传文件" prop="file">
          <el-upload ref="uploadRef" :auto-upload="false" :limit="3" drag
            :on-change="onFileChange" :on-remove="onFileRemove"
            accept=".jpg,.jpeg,.png,.gif,.webp,.pdf,.doc,.docx,.mp4,.mov,.avi">
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处或 <em>点击上传</em></div>
            <template #tip><div class="el-upload__tip">支持图片/PDF/文档/视频，单个不超过 50MB</div></template>
          </el-upload>
        </el-form-item>

        <!-- 标签 -->
        <el-form-item label="标签">
          <el-input v-model="tagInput" placeholder="输入标签后按回车添加" @keyup.enter="addTag">
            <template #append><el-button @click="addTag">添加</el-button></template>
          </el-input>
          <div style="margin-top:8px">
            <el-tag v-for="(t,i) in form.tags" :key="i" closable @close="form.tags.splice(i,1)" style="margin:2px">{{ t }}</el-tag>
          </div>
        </el-form-item>

        <!-- 排序号 -->
        <el-form-item label="排序号">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
        </el-form-item>

        <!-- 状态 -->
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="draft">草稿</el-radio>
            <el-radio value="published">发布</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 操作按钮 -->
        <el-form-item>
          <el-button @click="$router.back()">取消</el-button>
          <el-button type="primary" @click="handleSave" :loading="saving">
            {{ isEdit ? '保存修改' : '创建资产' }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { kbApi } from '@/api/knowledgeBase'
import type { FormInstance, UploadFile } from 'element-plus'

const route = useRoute(); const router = useRouter()
const formRef = ref<FormInstance>(); const uploadRef = ref()
const loading = ref(false); const saving = ref(false); const tagInput = ref('')

const assetId = computed(() => route.params.id as string)
const isEdit = computed(() => !!assetId.value)

const form = reactive<Record<string, any>>({
  title: '', asset_type: '', content_type: 'text',
  content_text: '', tags: [] as string[], status: 'draft', sort_order: 0,
})
const rules = {
  title: [{ required: true, message: '请输入资产名称', trigger: 'blur' }],
  asset_type: [{ required: true, message: '请选择资产类型', trigger: 'change' }],
  content_type: [{ required: true, message: '请选择内容分类', trigger: 'change' }],
}

const contentTypeOptions = computed(() => {
  const map: Record<string, {label:string,value:string}[]> = {
    basic: [
      { label:'企业简介', value:'company_intro' }, { label:'产品参数', value:'product_spec' },
      { label:'资质证书', value:'certification' }, { label:'联系方式', value:'contact' },
      { label:'其他文本', value:'text' },
    ],
    marketing: [
      { label:'行业关键词', value:'keywords' }, { label:'客户案例', value:'case_study' },
      { label:'差异化优势', value:'competitive_advantage' }, { label:'竞品分析', value:'competitor_analysis' },
      { label:'话术模板', value:'script' },
    ],
    multimodal: [
      { label:'产品图片', value:'image' }, { label:'技术白皮书', value:'whitepaper' },
      { label:'案例视频', value:'video' }, { label:'宣传物料', value:'brochure' },
    ],
  }
  return map[form.asset_type] || []
})

function onTypeChange() {
  form.content_type = contentTypeOptions.value[0]?.value || 'text'
  form.content_text = ''
}

function addTag() {
  const t = tagInput.value.trim()
  if (t && !form.tags.includes(t)) { form.tags.push(t) }
  tagInput.value = ''
}

function onFileChange(file: UploadFile) {
  form._file = file.raw
}

function onFileRemove() { form._file = null }

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload: any = {
      title: form.title,
      asset_type: form.asset_type,
      content_type: form.content_type,
      content_text: form.content_text || '',
      tags: form.tags,
      status: form.status,
    }

    if (isEdit.value) {
      await kbApi.updateAsset(assetId.value, payload)
      ElMessage.success('资产已更新')
    } else {
      // Generate a slug from title
      payload.slug = form.title.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9一-龥-]/g, '').slice(0, 200) || 'asset-' + Date.now()
      await kbApi.createAsset(payload)
      ElMessage.success('资产已创建')
    }
    router.push('/knowledge-base')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '保存失败')
  }
  saving.value = false
}

onMounted(async () => {
  if (!isEdit.value) return
  loading.value = true
  try {
    const asset = await kbApi.getAsset(assetId.value)
    Object.assign(form, {
      title: asset.title || '',
      asset_type: asset.asset_type || '',
      content_type: asset.content_type || 'text',
      content_text: asset.content_text || '',
      tags: Array.isArray(asset.tags) ? [...asset.tags] : [],
      status: asset.status || 'draft',
      sort_order: 0,
    })
  } catch (e: any) {
    ElMessage.error('加载资产失败')
    router.push('/knowledge-base')
  }
  loading.value = false
})
</script>

<style scoped>
.el-upload__tip { margin-top: 4px; font-size: 12px; color: #909399; }
</style>
