<template>
  <div class="page-container">
    <div class="page-header"><h2>工作台</h2></div>
    <div class="stat-cards">
      <div class="stat-card" v-for="s in stats" :key="s.label">
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-value">{{ s.value }}</div>
      </div>
    </div>
    <div class="detail-section">
      <div class="section-title">快捷操作</div>
      <el-row :gutter="12">
        <el-col :span="6"><el-button style="width:100%" @click="$router.push('/knowledge-base')">知识库管理</el-button></el-col>
        <el-col :span="6"><el-button style="width:100%" @click="$router.push('/content/create')">新建创作</el-button></el-col>
        <el-col :span="6"><el-button style="width:100%" @click="$router.push('/review')">内容审核</el-button></el-col>
        <el-col :span="6"><el-button style="width:100%" @click="$router.push('/detection')">全域探测</el-button></el-col>
      </el-row>
    </div>
    <div class="detail-section">
      <div class="section-title">最近活动</div>
      <el-table :data="activity" stripe>
        <el-table-column prop="action" label="操作" min-width="200" />
        <el-table-column prop="created_at" label="时间" width="180"><template #default="{row}">{{ row.created_at?.slice(0,16) }}</template></el-table-column>
      </el-table>
      <el-empty v-if="!activity.length" description="暂无活动数据" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import http from '@/api/index'
const stats = ref([{ label: '知识库资产', value: 0 },{ label: '待审核稿件', value: 0 },{ label: '本周发布', value: 0 },{ label: '累计内容', value: 0 }])
const activity = ref<any[]>([])
onMounted(async () => {
  try { const u = (await http.get('/p2/monitor/usage')).data; stats.value[0].value = u.kb_assets || 0; stats.value[3].value = u.content_drafts || 0 } catch {}
  try { const r = (await http.get('/reviews/', { params: { status: 'pending' } })).data; stats.value[1].value = (Array.isArray(r) ? r : []).length } catch {}
  try { const l = (await http.get('/p2/operation-logs', { params: { page: 1, page_size: 5 } })).data; activity.value = l.items || [] } catch {}
})
</script>
