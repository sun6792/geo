<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ asset?.title || '资产详情' }}</h2>
      <div>
        <el-button type="primary" @click="$router.push('/knowledge-base/'+assetId+'/edit')" v-if="asset">编辑</el-button>
        <el-button @click="$router.push('/knowledge-base')">返回列表</el-button>
      </div>
    </div>
    <div v-if="asset" v-loading="loading" style="max-width:800px">
      <div class="detail-section">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="类型"><el-tag size="small">{{ typeLabel(asset.asset_type) }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="分类">{{ asset.content_type }}</el-descriptions-item>
          <el-descriptions-item label="版本">v{{ asset.version }}</el-descriptions-item>
          <el-descriptions-item label="状态"><el-tag :type="asset.status==='published'?'success':'info'" size="small">{{ asset.status }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ asset.created_at?.slice(0,16) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ asset.updated_at?.slice(0,16) }}</el-descriptions-item>
          <el-descriptions-item label="标签" :span="2">
            <el-tag v-for="t in (asset.tags||[])" :key="t" size="small" style="margin:2px">{{ t }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <div class="detail-section" v-if="asset.content_text">
        <div class="section-title">资产内容</div>
        <div style="padding:16px;background:#f9fafb;border-radius:8px;white-space:pre-wrap;line-height:1.8" v-text="asset.content_text" />
      </div>
    </div>
    <div v-else class="table-card"><el-empty description="资产未找到" /></div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { kbApi } from '@/api/knowledgeBase'
const route = useRoute(); const asset = ref<any>(null); const loading = ref(false)
const assetId = route.params.id as string
function typeLabel(t: string) { return { basic: '基础资产', marketing: '营销资产', multimodal: '多模态资产' }[t] || t }
onMounted(async () => { loading.value = true; try { asset.value = await kbApi.getAsset(assetId) } catch {}; loading.value = false })
</script>
