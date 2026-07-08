<template>
  <div class="page-container">
    <div class="page-header">
      <h2>企业信息库</h2>
      <el-button type="primary" @click="handleSaveAll" :loading="saving">保存全部</el-button>
    </div>
    <div class="form-tip-main">客户提供的所有资料在这里一次性录入。有就填，没有就跳过。Agent1-Agent5 自动读取。</div>

    <!-- ═══════ 1. 基础信息 ═══════ -->
    <div class="profile-section">
      <div class="section-header"> 企业基础信息</div>
      <el-row :gutter="16">
        <el-col :span="6"><label>公司地址</label><el-input v-model="f.address" placeholder="详细地址" /></el-col>
        <el-col :span="6"><label>联系电话</label><el-input v-model="f.phone" placeholder="座机或手机" /></el-col>
        <el-col :span="6"><label>官方网站</label><el-input v-model="f.website" placeholder="www.example.com" /></el-col>
        <el-col :span="6"><label>成立年份</label><el-input v-model="f.established" placeholder="如：2008年" /></el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:10px">
        <el-col :span="12"><label>商务邮箱</label><el-input v-model="f.email" placeholder="客户咨询邮箱" /></el-col>
        <el-col :span="12"><label>客服微信</label><el-input v-model="f.service_contact" placeholder="微信号或400热线" /></el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:16px">
        <el-col :span="24"><label>公司简介</label><el-input v-model="f.intro" type="textarea" :rows="3" placeholder="公司成立时间、地点、规模、主营业务简介" /></el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:10px">
        <el-col :span="24"><label>主营产品</label><el-input v-model="f.products" type="textarea" :rows="3" placeholder="主要产品名称、型号、规格、产能。每行一个产品" /></el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:10px">
        <el-col :span="24"><label>资质认证</label><el-input v-model="f.certifications" type="textarea" :rows="2" placeholder="ISO9001、高新技术企业、专利号等。一行一个" /></el-col>
      </el-row>
      <div style="margin-top:14px">
        <label>核心关键词</label>
        <el-input v-model="tagInput" placeholder="输入关键词回车添加，Agent1自动用这些词搜索" @keyup.enter="addTag">
          <template #append><el-button @click="addTag">添加</el-button></template>
        </el-input>
        <div style="margin-top:4px"><el-tag v-for="(t,i) in f.tags" :key="i" closable @close="f.tags.splice(i,1)" size="small" style="margin:2px">{{ t }}</el-tag></div>
      </div>
    </div>

    <!-- ═══════ 2. 营销资料 ═══════ -->
    <div class="profile-section">
      <div class="section-header"> 营销资料</div>
      <el-row :gutter="16" style="margin-top:10px">
        <el-col :span="24"><label>客户案例</label><el-input v-model="m.cases" type="textarea" :rows="4" placeholder="描述2-3个代表客户的合作案例，Agent3创作时自动引用" /></el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:10px">
        <el-col :span="12"><label>核心优势</label><el-input v-model="m.advantage" type="textarea" :rows="2" placeholder="和竞品比好在哪" /></el-col>
        <el-col :span="12"><label>竞品名称</label><el-input v-model="m.competitors" type="textarea" :rows="2" placeholder="3-5家主要竞品，逗号分隔" /></el-col>
      </el-row>
    </div>

    <!-- ═══════ 3. 素材资料 ═══════ -->
    <div class="profile-section">
      <div class="section-header"> 素材资料（选填，有就描述没有跳过）</div>
      <el-row :gutter="16">
        <el-col :span="12"><label>实拍图片</label><el-input v-model="mm.photos" type="textarea" :rows="2" placeholder="描述已有的实拍图：工厂/车间/产品/团队" /></el-col>
        <el-col :span="12"><label>视频素材</label><el-input v-model="mm.videos" type="textarea" :rows="2" placeholder="描述已有的视频：工厂参观/产品演示" /></el-col>
      </el-row>
    </div>

    <div style="text-align:center;padding:20px">
      <el-button type="primary" size="large" @click="handleSaveAll" :loading="saving">保存全部档案</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { kbApi } from '@/api/knowledgeBase'

const saving = ref(false); const tagInput = ref('')

const f = reactive({ address:'', phone:'', website:'', email:'', service_contact:'', established:'', intro:'', products:'', certifications:'', tags:[] as string[] })
const m = reactive({ cases:'', advantage:'', competitors:'', pitfalls:'' })
const mm = reactive({ photos:'', videos:'', whitepapers:'' })

function addTag() { const t = tagInput.value.trim(); if (t && !f.tags.includes(t)) f.tags.push(t); tagInput.value = '' }

async function saveAsset(type: string, title: string, contentText: string, contentJson: any, tags: string[] = []) {
  const slug = title.replace(/\s+/g,'-').replace(/[^a-z0-9一-鿿-]/g,'').slice(0,200) || 'asset-'+Date.now()
  const existing = await kbApi.listAssets({ page:1, page_size:100, asset_type:type, search: title.slice(0,10) }).catch(() => ({ items:[] }))
  const matched = (existing as any).items?.find((a:any) => a.title === title)
  if (matched) {
    await kbApi.updateAsset(matched.id, { content_text: contentText, content_json: contentJson, tags, status: 'published' })
  } else {
    await kbApi.createAsset({ title, slug, asset_type: type, content_type: 'text', content_text: contentText, content_json: contentJson, tags, status: 'published' })
  }
}

async function handleSaveAll() {
  saving.value = true
  try {
    // Build structured content for each section
    const basicText = [
      '## 联系方式', ...[f.address&&'地址：'+f.address, f.phone&&'电话：'+f.phone, f.website&&'官网：'+f.website, f.email&&'邮箱：'+f.email, f.service_contact&&'客服：'+f.service_contact].filter(Boolean),
      '## 公司信息', f.intro, '## 产品', f.products, '## 资质', f.certifications,
    ].filter(Boolean).join('\n\n')
    const basicJson = { address:f.address, phone:f.phone, website:f.website, email:f.email, service_contact:f.service_contact, established:f.established, intro:f.intro, products:f.products, certifications:f.certifications }

    const mktText = ['## 客户案例', m.cases, '## 核心优势', m.advantage, '## 竞品分析', m.competitors, '## 避坑指南', m.pitfalls].filter(Boolean).join('\n\n')
    const mktJson = { cases:m.cases, advantage:m.advantage, competitors:m.competitors, pitfalls:m.pitfalls }

    const mmText = ['## 图片素材', mm.photos, '## 视频素材', mm.videos, '## 白皮书', mm.whitepapers].filter(Boolean).join('\n\n')
    const mmJson = { photos:mm.photos, videos:mm.videos, whitepapers:mm.whitepapers }

    const allTags = [...f.tags]

    await saveAsset('basic', '企业基础档案', basicText, basicJson, allTags)
    await saveAsset('marketing', '营销内容档案', mktText, mktJson, allTags)
    await saveAsset('multimodal', '多模态素材档案', mmText, mmJson, allTags)

    ElMessage.success('企业档案已全部保存！Agent1-Agent5现在可以读取到完整客户资料。')
  } catch (e: any) { ElMessage.error('保存失败：' + (e.response?.data?.error || e.message)) }
  saving.value = false
}

onMounted(async () => {
  // Load existing profile data
  try {
    const assets = await kbApi.listAssets({ page:1, page_size:50, status:'published' })
    for (const a of (assets as any)?.items || []) {
      const j = a.content_json || {}
      if (a.title.includes('基础档案')) { Object.assign(f, j); f.tags = a.tags || [] }
      if (a.title.includes('营销')) { Object.assign(m, j) }
      if (a.title.includes('多模态') || a.title.includes('素材')) { Object.assign(mm, j) }
    }
  } catch {}
})
</script>

<style scoped>
.profile-section { background:#fff; border-radius:12px; padding:20px 24px; margin-bottom:16px; border:1px solid #ebeef5; }
.section-header { font-size:17px; font-weight:700; color:#303133; margin-bottom:8px; padding-bottom:8px; border-bottom:2px solid #409eff; }
label { display:block; font-size:13px; color:#606266; font-weight:600; margin-bottom:4px; }
.form-tip-main { background:#ecf5ff; padding:10px 16px; border-radius:8px; color:#409eff; font-size:13px; margin-bottom:16px; }
</style>
