<template>
  <div class="page-container">
    <div class="page-header">
      <h2>内容创作</h2>
      <div>
        <el-button type="success" @click="$router.push('/diagnosis')" icon="el-icon-link"> 从诊断缺口一键同步</el-button>
        <el-button type="primary" @click="$router.push('/content/create')">新建创作任务</el-button>
      </div>
    </div>
    <el-empty v-if="!loading && briefs.length === 0" description="暂无创作任务。请先到「短板诊断」页面生成报告，然后勾选缺口一键同步过来。" />
    <div class="table-card" v-else>
      <el-table :data="briefs" v-loading="loading" stripe>
        <el-table-column prop="title" label="标题" min-width="250" show-overflow-tooltip />
        <el-table-column prop="content_type" label="类型" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{row}"><el-tag :type="row.status==='draft'?'info':row.status==='ai_generated'?'success':'warning'" size="small">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{row}">{{ row.created_at?.slice(0,16) || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{row}">
            <el-button size="small" type="success" @click="generateBrief(row)" :loading="row._generating">
              {{ row._generating ? '生成中...' : '一键生成内容' }}
            </el-button>
            <el-button size="small" v-if="row._draftId" type="primary" @click="$router.push('/content/'+row._draftId)">查看稿件</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { contentApi } from '@/api/content'
import http from '@/api/index'

const loading = ref(false)
const briefs = ref<any[]>([])

async function generateBrief(row: any) {
  row._generating = true
  try {
    const r = await http.post(`/content/briefs/${row.id}/generate`)
    const draft = r.data
    row._draftId = draft.draft_id
    row.status = 'ai_generated'
    ElMessage.success(`内容生成成功！标题：${draft.title}`)
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '生成失败，请确认知识库有足够素材') }
  row._generating = false
}

onMounted(async () => {
  loading.value = true
  try { const r = await contentApi.listBriefs({ page: 1, page_size: 20 }); briefs.value = (r.items || []).map((b: any) => ({...b, _generating: false, _draftId: null})) } catch {}
  loading.value = false
})
</script>
