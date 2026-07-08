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

        <!-- 内容分区：所有字段平铺展示，每项独立填写，留空则跳过 -->
        <template v-if="form.asset_type">
          <el-divider content-position="left">
            {{ form.asset_type==='basic' ? '基础资产详情（每个字段选填，有就写没有就跳过）' : form.asset_type==='marketing' ? '营销资产详情（每个字段选填，有就写没有就跳过）' : '多模态资产详情（上传图片视频等素材文件）' }}
          </el-divider>

          <template v-if="form.asset_type === 'basic'">
            <!-- 联系方式：最优先，全部智能体都依赖 -->
            <el-divider content-position="left"><el-tag type="danger" size="small">最重要</el-tag> 联系方式 — Agent3写文章自动带上，Agent1核验身份一致性</el-divider>
            <el-row :gutter="12">
              <el-col :span="8">
                <el-form-item label="公司地址">
                  <el-input v-model="basicFields.address" placeholder="详细地址，如：广东省东莞市XX镇XX路88号" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="联系电话">
                  <el-input v-model="basicFields.phone" placeholder="如：0769-88886666 / 138xxxx" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="官方网站">
                  <el-input v-model="basicFields.website" placeholder="如：www.example.com" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="商务邮箱">
                  <el-input v-model="basicFields.email" placeholder="客户咨询/商务合作邮箱" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="客服微信/热线">
                  <el-input v-model="basicFields.service_contact" placeholder="如：微信ID 或 400电话" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">公司基础信息</el-divider>
            <el-form-item label="公司简介">
              <div class="form-tip">Agent1用此核验身份，Agent2计算基础资产分</div>
              <el-input v-model="basicFields.intro" type="textarea" :rows="4" placeholder="公司成立时间、地点、规模、主营业务简介" />
            </el-form-item>
            <el-form-item label="产品参数">
              <div class="form-tip">Agent2判断产品信息是否完整，Agent3创作时引用</div>
              <el-input v-model="basicFields.product_spec" type="textarea" :rows="4" placeholder="主要产品名称、型号、规格、材质、产能等参数" />
            </el-form-item>
            <el-form-item label="资质证书">
              <div class="form-tip">Agent1核验身份可信度，Agent3创作时增强权威性</div>
              <el-input v-model="basicFields.certifications" type="textarea" :rows="4" placeholder="如：ISO9001质量管理体系认证、高新技术企业、专利号等" />
            </el-form-item>
          </template>

          <template v-if="form.asset_type === 'marketing'">
            <el-form-item label="客户案例">
              <div class="form-tip">Agent2判断案例丰富度，Agent3创作时自动融入文章</div>
              <el-input v-model="mktFields.case_study" type="textarea" :rows="6" placeholder="描述2-3个代表客户案例：客户是谁、遇到什么问题、怎么解决的、效果怎么样。可匿名化处理" />
            </el-form-item>
            <el-form-item label="竞争优势">
              <div class="form-tip">Agent3创作时突出差异化卖点</div>
              <el-input v-model="mktFields.advantage" type="textarea" :rows="3" placeholder="和竞品相比，你们的差异化优势是什么？价格、品质、交期、服务、技术？" />
            </el-form-item>
            <el-form-item label="竞品分析">
              <div class="form-tip">Agent1探测时参考，Agent5周报复盘时对比</div>
              <el-input v-model="mktFields.competitor_analysis" type="textarea" :rows="3" placeholder="主要竞品有哪些？他们做得怎么样？你们在哪些方面比他们强？" />
            </el-form-item>
            <el-form-item label="行业避坑指南">
              <div class="form-tip">Agent3创作"避坑类"文章时引用，吸引精准流量</div>
              <el-input v-model="mktFields.pitfall_guide" type="textarea" :rows="3" placeholder="客户在采购这类产品时容易踩什么坑？怎么避免？" />
            </el-form-item>
          </template>

          <template v-if="form.asset_type === 'multimodal'">
            <el-form-item label="上传文件">
              <div class="form-tip">Agent2诊断时检查多模态素材覆盖度，Agent4发布时挂载</div>
              <el-upload ref="uploadRef" :auto-upload="false" :limit="5" drag
                :on-change="onFileChange" :on-remove="onFileRemove"
                accept=".jpg,.jpeg,.png,.gif,.webp,.pdf,.doc,.docx,.mp4,.mov,.avi">
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖拽文件到此处或 <em>点击上传</em></div>
                <template #tip><div class="el-upload__tip">支持图片/PDF/文档/视频，单个不超过 50MB。建议上传：工厂实拍/产品图/检测报告/宣传视频</div></template>
              </el-upload>
            </el-form-item>
            <el-form-item label="文件描述">
              <el-input v-model="multimodalFields.description" type="textarea" :rows="2" placeholder="描述上传的文件内容，用于Agent3生成图文搭配内容" />
            </el-form-item>
          </template>
        </template>

        <!-- 关键词标签：智能体1探测时自动匹配，智能体3创作时自动融入 -->
        <el-form-item label="关键词标签">
          <div class="form-tip">Agent1自动用这些词去大模型搜索，Agent3创作时自动融入文章</div>
          <el-input v-model="tagInput" placeholder="如：运动面料、骑行装备、源头工厂" @keyup.enter="addTag">
            <template #append><el-button @click="addTag">添加</el-button></template>
          </el-input>
          <div style="margin-top:8px">
            <el-tag v-for="(t,i) in form.tags" :key="i" closable @close="form.tags.splice(i,1)" style="margin:2px">{{ t }}</el-tag>
          </div>
        </el-form-item>

        <!-- 排序号：数字越大越靠前，Agent2诊断时优先检视排序靠前的资产 -->
        <el-form-item label="权重排序">
          <div class="form-tip">数字越大越优先，Agent2诊断时会先检查排序靠前的资产缺口</div>
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
  title: '', asset_type: '', tags: [] as string[], status: 'draft', sort_order: 0,
})
const basicFields = reactive({
  address: '', phone: '', website: '', email: '', service_contact: '',
  intro: '', product_spec: '', certifications: '',
})
const mktFields = reactive({ case_study: '', advantage: '', competitor_analysis: '', pitfall_guide: '' })
const multimodalFields = reactive({ description: '' })

const rules = {
  title: [{ required: true, message: '请输入资产名称', trigger: 'blur' }],
  asset_type: [{ required: true, message: '请选择资产类型', trigger: 'change' }],
}

function onTypeChange() { /* fields reset on type change via template v-if */ }

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
    // Build structured content from all fields
    let contentJson: any = {}
    let contentText = ''
    if (form.asset_type === 'basic') {
      contentJson = { ...basicFields }
      // 联系方式排最前面，Agent3创作时优先提取
      const contactBlock = [
        basicFields.address && `公司地址：${basicFields.address}`,
        basicFields.phone && `联系电话：${basicFields.phone}`,
        basicFields.website && `官方网站：${basicFields.website}`,
        basicFields.email && `商务邮箱：${basicFields.email}`,
        basicFields.service_contact && `客服联系：${basicFields.service_contact}`,
      ].filter(Boolean).join('\n')
      const infoBlock = [basicFields.intro, basicFields.product_spec, basicFields.certifications].filter(Boolean).join('\n\n---\n\n')
      contentText = (contactBlock ? '## 联系方式\n' + contactBlock + '\n\n---\n\n' : '') + infoBlock
    } else if (form.asset_type === 'marketing') {
      contentJson = { ...mktFields }
      contentText = [mktFields.case_study, mktFields.advantage, mktFields.competitor_analysis, mktFields.pitfall_guide]
        .filter(Boolean).join('\n\n---\n\n')
    } else if (form.asset_type === 'multimodal') {
      contentJson = { ...multimodalFields }
      contentText = multimodalFields.description || ''
    }

    const payload: any = {
      title: form.title,
      asset_type: form.asset_type,
      content_type: 'text',
      content_text: contentText || form.title,
      content_json: contentJson,
      tags: form.tags,
      status: form.status,
      sort_order: form.sort_order,
    }

    if (isEdit.value) {
      await kbApi.updateAsset(assetId.value, payload)
      ElMessage.success('资产已更新')
    } else {
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
.form-tip { font-size: 12px; color: #67c23a; margin-bottom: 4px; line-height: 1.4; }
</style>
