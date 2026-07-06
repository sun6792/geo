<template>
  <div class="page-container">
    <div class="page-header">
      <h2>内容创作</h2>
      <el-button type="primary" @click="$router.push('/content/create')">新建创作任务</el-button>
    </div>
    <div class="table-card">
      <el-table :data="briefs" v-loading="loading" stripe>
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="content_type" label="类型" width="120" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{row}">
            <el-button size="small" @click="$router.push('/content/'+row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { contentApi } from '@/api/content'

const loading = ref(false)
const briefs = ref<any[]>([])

onMounted(async () => {
  loading.value = true
  try { const r = await contentApi.listBriefs({ page: 1, page_size: 20 }); briefs.value = r.items || [] } catch {}
  loading.value = false
})
</script>
