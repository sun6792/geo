<template>
  <div class="page-container">
    <div class="page-header">
      <h2>企业信息库</h2>
      <el-button type="primary" @click="save" :loading="saving">保存全部</el-button>
    </div>
    <div class="form-tip-main">{{ cid ? '正在为「'+cname+'」填写资料' : '请从客户管理页面点击「知识库」进入' }}</div>

    <!-- ═══════ 1. 基础信息 ═══════ -->
    <div class="profile-section">
      <div class="section-header">企业基础信息</div>
      <el-row :gutter="16">
        <el-col :span="6"><label>公司地址</label><el-input v-model="d.address" placeholder="详细地址" /></el-col>
        <el-col :span="6"><label>联系电话</label><el-input v-model="d.phone" placeholder="座机或手机" /></el-col>
        <el-col :span="6"><label>官方网站</label><el-input v-model="d.website" placeholder="www.example.com" /></el-col>
        <el-col :span="6"><label>成立年份</label><el-input v-model="d.established" placeholder="如：2008年" /></el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:10px">
        <el-col :span="12"><label>商务邮箱</label><el-input v-model="d.email" placeholder="客户咨询邮箱" /></el-col>
        <el-col :span="12"><label>客服微信</label><el-input v-model="d.service_contact" placeholder="微信号或400热线" /></el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:14px">
        <el-col :span="24"><label>公司简介</label><el-input v-model="d.intro" type="textarea" :rows="3" placeholder="公司成立时间、地点、规模、主营业务简介" /></el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:10px">
        <el-col :span="24"><label>主营产品</label><el-input v-model="d.products" type="textarea" :rows="3" placeholder="主要产品名称、型号、规格、产能。每行一个产品" /></el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:10px">
        <el-col :span="24"><label>资质认证</label><el-input v-model="d.certs" type="textarea" :rows="2" placeholder="ISO9001、高新技术企业、专利号等。一行一个" /></el-col>
      </el-row>
      <div style="margin-top:14px">
        <label>核心关键词</label>
        <el-input v-model="tagInput" placeholder="输入关键词回车添加，Agent1自动用这些词搜索" @keyup.enter="addTag">
          <template #append><el-button @click="addTag">添加</el-button></template>
        </el-input>
        <div style="margin-top:4px"><el-tag v-for="(t,i) in d.keywords" :key="i" closable @close="d.keywords.splice(i,1)" size="small" style="margin:2px">{{ t }}</el-tag></div>
      </div>
    </div>

    <!-- ═══════ 2. 营销信息 ═══════ -->
    <div class="profile-section">
      <div class="section-header">营销资料</div>
      <el-row :gutter="16" style="margin-top:10px">
        <el-col :span="24"><label>客户案例</label><el-input v-model="d.cases" type="textarea" :rows="4" placeholder="描述2-3个代表客户的合作案例，Agent3创作时自动引用" /></el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:10px">
        <el-col :span="12"><label>核心优势</label><el-input v-model="d.advantage" type="textarea" :rows="2" placeholder="和竞品比好在哪" /></el-col>
        <el-col :span="12"><label>竞品名称</label><el-input v-model="d.competitors" type="textarea" :rows="2" placeholder="3-5家主要竞品，逗号分隔" /></el-col>
      </el-row>
    </div>

    <!-- ═══════ 3. 素材信息 ═══════ -->
    <div class="profile-section">
      <div class="section-header">素材资料（选填）</div>
      <el-row :gutter="16">
        <el-col :span="8"><label>实拍图片</label><el-upload :action="uploadUrl" :headers="uploadHeaders" :on-success="onUpload('photos')" :file-list="photoList" list-type="picture" multiple><el-button size="small" type="primary">上传</el-button></el-upload><el-input v-model="d.photos" type="textarea" :rows="2" placeholder="或手动描述" style="margin-top:6px" /></el-col>
        <el-col :span="8"><label>视频素材</label><el-upload :action="uploadUrl" :headers="uploadHeaders" :on-success="onUpload('videos')" :file-list="videoList" multiple><el-button size="small" type="success">上传</el-button></el-upload><el-input v-model="d.videos" type="textarea" :rows="2" placeholder="或手动描述" style="margin-top:6px" /></el-col>
        <el-col :span="8"><label>资质文件</label><el-upload :action="uploadUrl" :headers="uploadHeaders" :on-success="onUpload('docs')" :file-list="docList" multiple><el-button size="small" type="warning">上传</el-button></el-upload><el-input v-model="d.docs" type="textarea" :rows="2" placeholder="或手动描述" style="margin-top:6px" /></el-col>
      </el-row>
    </div>

    <div style="text-align:center;padding:20px">
      <el-button type="primary" size="large" @click="save" :loading="saving">保存全部信息</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import http from '@/api/index'

const route = useRoute()
const saving = ref(false); const tagInput = ref('')
const cid = ref((route.query.cid as string) || '')
const cname = ref('')
const photoList = ref<any[]>([]); const videoList = ref<any[]>([]); const docList = ref<any[]>([])
const token = localStorage.getItem('geoai_access_token') || ''
const uploadHeaders = { Authorization: `Bearer ${token}` }
const uploadUrl = computed(() => `/api/v1/enterprise-profile/upload?customer_id=${cid.value}`)

const d = reactive<any>({ address:'', phone:'', website:'', email:'', service_contact:'', established:'', intro:'', products:'', certs:'', keywords:[], cases:'', advantage:'', competitors:'', pitfalls:'', photos:'', videos:'', docs:'' })

function onUpload(field: string) { return (res: any) => { d[field] = (d[field] ? d[field] + '\n' : '') + (res.paths||[]).join('\n') } }
function addTag() { const t = tagInput.value.trim(); if (t && !d.keywords.includes(t)) d.keywords.push(t); tagInput.value = '' }

async function load() {
  if (!cid.value) return
  try { const r = await http.get('/customers/' + cid.value); cname.value = r.data?.name || '' } catch {}
  try { const r = await http.get('/enterprise-profile', { params: { customer_id: cid.value } }); const saved = r.data?.data; if (saved && Object.keys(saved).length>0) Object.assign(d, saved) } catch {}
}

async function save() {
  if (!cid.value) { ElMessage.warning('请从客户管理页面进入'); return }
  saving.value = true
  try { await http.put('/enterprise-profile', { customer_id: cid.value, data: { ...d } }); ElMessage.success('已保存') } catch { ElMessage.error('保存失败') }
  saving.value = false
}

onMounted(() => { if (cid.value) load() })
</script>

<style scoped>
.profile-section { background:#fff; border-radius:12px; padding:20px 24px; margin-bottom:16px; border:1px solid #ebeef5; }
.section-header { font-size:16px; font-weight:700; color:#303133; margin-bottom:8px; padding-bottom:8px; border-bottom:2px solid #409eff; }
label { display:block; font-size:13px; color:#606266; font-weight:600; margin-bottom:2px; }
.form-tip-main { background:#ecf5ff; padding:10px 16px; border-radius:8px; color:#409eff; font-size:13px; margin-bottom:16px; }
</style>
