<template>
  <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar">
    <div class="logo">
      <img src="@/assets/images/logo.svg" alt="" class="logo-img" v-if="!isCollapsed" />
      <span v-if="!isCollapsed" class="logo-text">GEO AI 运营系统</span>
      <span v-else class="logo-text-mini">GEO</span>
    </div>
    <el-menu
      :default-active="activeMenu"
      :collapse="isCollapsed"
      :collapse-transition="false"
      router
      background-color="#001529"
      text-color="#ffffffb3"
      active-text-color="#fff"
    >
      <el-menu-item index="/dashboard">
        <el-icon><Monitor /></el-icon>
        <span>工作台</span>
      </el-menu-item>
      <el-menu-item index="/knowledge-base">
        <el-icon><Document /></el-icon>
        <span>知识库管理</span>
      </el-menu-item>
      <el-menu-item index="/templates">
        <el-icon><Collection /></el-icon>
        <span>行业模板</span>
      </el-menu-item>
      <el-menu-item index="/content">
        <el-icon><Edit /></el-icon>
        <span>内容创作</span>
      </el-menu-item>
      <el-menu-item index="/review">
        <el-icon><Checked /></el-icon>
        <span>内容审核</span>
      </el-menu-item>
      <el-menu-item index="/publish">
        <el-icon><Promotion /></el-icon>
        <span>发布管理</span>
      </el-menu-item>
      <el-menu-item index="/detection">
        <el-icon><Search /></el-icon>
        <span>全域探测</span>
      </el-menu-item>
      <el-menu-item index="/diagnosis">
        <el-icon><DataAnalysis /></el-icon>
        <span>短板诊断</span>
      </el-menu-item>
      <el-menu-item index="/weekly-review">
        <el-icon><TrendCharts /></el-icon>
        <span>周度复盘</span>
      </el-menu-item>
      <el-menu-item index="/customer">
        <el-icon><OfficeBuilding /></el-icon>
        <span>客户管理</span>
      </el-menu-item>
      <el-menu-item index="/monitor">
        <el-icon><Monitor /></el-icon>
        <span>系统监控</span>
      </el-menu-item>
      <el-sub-menu index="account">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>系统管理</span>
        </template>
        <el-menu-item index="/account/users">用户管理</el-menu-item>
        <el-menu-item index="/account/roles">角色管理</el-menu-item>
        <el-menu-item index="/account/plans">服务档位</el-menu-item>
      </el-sub-menu>
    </el-menu>
  </el-aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/store/app'
import { Monitor, Document, Edit, Checked, Promotion, Search, DataAnalysis, TrendCharts, OfficeBuilding, Collection, Setting } from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()

const isCollapsed = computed(() => appStore.sidebarCollapsed)
const activeMenu = computed(() => route.path)
</script>

<style lang="scss" scoped>
.sidebar {
  background: #001529;
  transition: width 0.3s;
  overflow: hidden;

  .logo {
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 16px;
    gap: 8px;

    .logo-img {
      width: 32px;
      height: 32px;
    }

    .logo-text {
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      white-space: nowrap;
    }

    .logo-text-mini {
      font-size: 18px;
      font-weight: 700;
      color: #fff;
    }
  }

  .el-menu {
    border-right: none;
  }
}
</style>
