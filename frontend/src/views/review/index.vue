<template>
  <div class="page-container">
    <div class="page-header"><h2>内容审核</h2></div>
    <div class="table-card">
      <el-table :data="reviews" v-loading="loading" stripe>
        <el-table-column prop="stage" label="审核阶段" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{row}"><el-tag :type="row.status==='approved'?'success':row.status==='rejected'?'danger':'warning'" size="small">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{row}"><el-button size="small" @click="$router.push('/review/'+row.id)">审核</el-button></template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { reviewApi } from '@/api/review'
const loading = ref(false); const reviews = ref<any[]>([])
onMounted(async () => { loading.value = true; try { reviews.value = await reviewApi.list() } catch {}; loading.value = false })
</script>
