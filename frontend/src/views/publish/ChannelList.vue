<template>
  <div class="page-container">
    <div class="page-header">
      <h2>渠道管理</h2>
      <div class="header-actions">
        <el-button type="success" @click="seedMatrix" :loading="seeding">
          <el-icon><MagicStick /></el-icon> 一键初始化渠道矩阵
        </el-button>
        <el-button type="primary" @click="openCreate">添加渠道</el-button>
      </div>
    </div>
    <div class="table-card">
      <el-table :data="channels" v-loading="loading" stripe>
        <el-table-column prop="name" label="渠道名称" min-width="150" />
        <el-table-column prop="channel_type" label="类型" width="120" />
        <el-table-column label="级别" width="80"><template #default="{row}"><el-tag size="small">T{{ row.tier }}</el-tag></template></el-table-column>
        <el-table-column label="API" width="70"><template #default="{row}"><el-tag :type="row.config_json?.api ? 'success' : 'info'" size="small">{{ row.config_json?.api ? '已配' : '手动' }}</el-tag></template></el-table-column>
        <el-table-column label="状态" width="70"><template #default="{row}"><el-tag :type="row.is_active?'success':'info'" size="small">{{ row.is_active?'启用':'停用' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{row}">
            <el-button size="small" @click="editChannel(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加/编辑渠道弹窗 -->
    <el-dialog v-model="showDialog" :title="editing?'编辑渠道':'添加渠道'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="渠道名称"><el-input v-model="form.name" placeholder="如：小红书、B站" /></el-form-item>
        <el-form-item label="渠道类型"><el-input v-model="form.channel_type" placeholder="英文标识，如 xiaohongshu" /></el-form-item>
        <el-form-item label="渠道级别">
          <el-radio-group v-model="form.tier">
            <el-radio :value="1">一级 · 全模型加分</el-radio>
            <el-radio :value="2">二级 · 分模型专属</el-radio>
            <el-radio :value="3">三级 · 垂直行业</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="所属平台"><el-input v-model="form.platform" placeholder="如：小红书、抖音" /></el-form-item>

        <el-divider />
        <el-form-item label="API自动发布">
          <el-switch v-model="apiEnabled" active-text="启用" inactive-text="手动发布（不需填下方API）" />
        </el-form-item>

        <template v-if="apiEnabled">
          <el-form-item label="API地址"><el-input v-model="apiForm.url" placeholder="https://open-api.xxx.com/v1/articles" /></el-form-item>
          <el-form-item label="请求方式">
            <el-select v-model="apiForm.method"><el-option label="POST" value="POST" /><el-option label="PUT" value="PUT" /><el-option label="PATCH" value="PATCH" /></el-select>
          </el-form-item>
          <el-form-item label="认证方式">
            <el-select v-model="apiForm.auth_type">
              <el-option label="Bearer Token" value="bearer" />
              <el-option label="API Key" value="api_key" />
              <el-option label="Basic Auth" value="basic" />
            </el-select>
          </el-form-item>
          <el-form-item label="API密钥"><el-input v-model="authForm.api_key" placeholder="填写该平台的API Key或Access Token" show-password /></el-form-item>
          <el-form-item label="Secret" v-if="apiForm.auth_type==='basic'"><el-input v-model="authForm.api_secret" placeholder="Basic Auth 的 Secret" show-password /></el-form-item>
          <el-form-item label="请求体模板">
            <el-input v-model="apiForm.body_template" type="textarea" :rows="4"
              :placeholder="bodyPlaceholder" />
            <span class="form-tip">&#123;&#123;title&#125;&#125; &#123;&#123;body&#125;&#125; &#123;&#123;summary&#125;&#125; &#123;&#123;tags&#125;&#125; 会被自动替换为实际内容</span>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showDialog=false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import { publishApi } from '@/api/review'
import http from '@/api/index'

const bodyPlaceholder = '{"title":"{{title}}","content":"{{body}}","tags":"{{tags}}"}'
const loading = ref(false); const saving = ref(false); const seeding = ref(false)
const channels = ref<any[]>([])
const showDialog = ref(false); const editing = ref(false); const editId = ref('')
const apiEnabled = ref(false)

const form = reactive({ name: '', channel_type: '', tier: 1, platform: '' })
const apiForm = reactive({ url: '', method: 'POST', auth_type: 'bearer', body_template: '{"title":"{{title}}","content":"{{body}}"}' })
const authForm = reactive({ api_key: '', api_secret: '' })

async function fetchChannels() { loading.value = true; try { channels.value = await publishApi.listChannels() } catch {}; loading.value = false }

async function seedMatrix() {
  seeding.value = true
  try {
    const res = await http.post('/publish/smart/channels/seed-matrix')
    ElMessage.success(`渠道矩阵初始化完成：新建${res.data.created}个，更新${res.data.updated}个，共${res.data.total}个渠道`)
    fetchChannels()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '初始化失败') }
  seeding.value = false
}

function openCreate() {
  editing.value = false; editId.value = ''
  form.name = ''; form.channel_type = ''; form.tier = 1; form.platform = ''
  apiEnabled.value = false
  apiForm.url = ''; apiForm.method = 'POST'; apiForm.auth_type = 'bearer'; apiForm.body_template = '{"title":"{{title}}","content":"{{body}}"}'
  authForm.api_key = ''; authForm.api_secret = ''
  showDialog.value = true
}

function editChannel(row: any) {
  editing.value = true; editId.value = row.id
  form.name = row.name; form.channel_type = row.channel_type; form.tier = row.tier; form.platform = row.platform || ''
  const cfg = row.config_json || {}
  if (cfg.auth) {
    apiEnabled.value = true
    authForm.api_key = cfg.auth.api_key || ''
    authForm.api_secret = cfg.auth.api_secret || ''
  } else { apiEnabled.value = false; authForm.api_key = ''; authForm.api_secret = '' }
  if (cfg.api) {
    apiForm.url = cfg.api.url || ''
    apiForm.method = cfg.api.method || 'POST'
    apiForm.auth_type = cfg.api.auth_type || 'bearer'
    apiForm.body_template = typeof cfg.api.body_template === 'string' ? cfg.api.body_template : JSON.stringify(cfg.api.body_template || {})
  }
  showDialog.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const data: any = { name: form.name, channel_type: form.channel_type, tier: form.tier, platform: form.platform }
    if (apiEnabled.value && apiForm.url) {
      data.config_json = {
        api: {
          url: apiForm.url, method: apiForm.method, auth_type: apiForm.auth_type,
          body_template: (() => { try { return JSON.parse(apiForm.body_template) } catch { return {} } })(),
        },
        auth: { api_key: authForm.api_key, api_secret: authForm.api_secret },
      }
    }
    if (editing.value) { await publishApi.updateChannel(editId.value, data) }
    else { await publishApi.createChannel(data) }
    ElMessage.success('保存成功'); showDialog.value = false; fetchChannels()
  } catch (e: any) { ElMessage.error(e.response?.data?.error || '保存失败') }
  saving.value = false
}

async function handleDelete(row: any) {
  try { await ElMessageBox.confirm('删除此渠道？'); await publishApi.deleteChannel(row.id); ElMessage.success('已删除'); fetchChannels() } catch {}
}
onMounted(fetchChannels)
</script>
<style scoped>
.header-actions { display: flex; gap: 10px; }
.form-tip { font-size: 12px; color: #999; margin-top: 4px; display: block; }
</style>
