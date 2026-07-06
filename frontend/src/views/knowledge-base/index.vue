<template>
  <div class="page-container">
    <div class="page-header">
      <h2>知识库管理</h2>
      <el-button type="primary" @click="$router.push('/knowledge-base/new')">新建资产</el-button>
    </div>
    <div class="search-bar">
      <el-select v-model="filterType" placeholder="资产类型" clearable @change="fetchAssets" style="width:160px">
        <el-option label="基础资产" value="basic" /><el-option label="营销资产" value="marketing" /><el-option label="多模态资产" value="multimodal" />
      </el-select>
      <el-input v-model="search" placeholder="搜索资产..." style="width:240px" clearable @clear="fetchAssets" @keyup.enter="fetchAssets" />
      <el-button type="primary" @click="fetchAssets">搜索</el-button>
    </div>
    <div class="table-card">
      <el-table :data="assets" v-loading="loading" stripe>
        <el-table-column prop="title" label="名称" min-width="180" />
        <el-table-column label="类型" width="100">
          <template #default="{row}"><el-tag size="small">{{ typeLabel(row.asset_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="70" />
        <el-table-column label="状态" width="90">
          <template #default="{row}"><el-tag :type="row.status==='published'?'success':'info'" size="small">{{ row.status==='published'?'已发布':'草稿' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="标签" min-width="140">
          <template #default="{row}"><el-tag v-for="t in (row.tags||[]).slice(0,3)" :key="t" size="small" style="margin:2px">{{ t }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170">
          <template #default="{row}">{{ row.updated_at?.slice(0,16) || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{row}">
            <el-button size="small" @click="$router.push('/knowledge-base/'+row.id+'/edit')">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">归档</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="total, prev, pager, next" @current-change="fetchAssets" style="margin-top:16px;justify-content:flex-end" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { kbApi } from '@/api/knowledgeBase'

const loading = ref(false); const assets = ref<any[]>([])
const page = ref(1); const pageSize = ref(20); const total = ref(0)
const filterType = ref(''); const search = ref('')

function typeLabel(t: string) { return { basic:'基础资产', marketing:'营销资产', multimodal:'多模态资产' }[t] || t }

async function fetchAssets() {
  loading.value = true
  try {
    const r = await kbApi.listAssets({ page: page.value, page_size: pageSize.value, asset_type: filterType.value || undefined, search: search.value || undefined })
    assets.value = r.items || []; total.value = r.total || 0
  } catch {}
  loading.value = false
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm('归档此资产？', '确认', { type: 'warning' })
    await kbApi.archiveAsset(row.id)
    ElMessage.success('已归档'); fetchAssets()
  } catch {}
}

onMounted(() => fetchAssets())
</script>
