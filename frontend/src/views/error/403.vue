<template>
  <div style="text-align:center;padding:80px 20px">
    <h1 style="font-size:72px;color:#e6a23c;margin:0">403</h1>
    <p style="font-size:20px;color:#606266;margin:16px 0">无权限访问</p>
    <p style="color:#909399;margin-bottom:32px">您没有权限访问此页面，请联系管理员</p>
    <el-button type="primary" @click="$router.push('/dashboard')">返回工作台</el-button>
  </div>
</template>
