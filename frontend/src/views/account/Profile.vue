<template>
  <div class="page-container">
    <div class="page-header"><h2>个人设置</h2></div>
    <div class="table-card" style="max-width:600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="姓名"><el-input v-model="form.display_name" disabled /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" disabled /></el-form-item>
        <el-form-item label="角色">
          <el-tag v-for="r in authStore.user?.roles || []" :key="r.id" size="small" style="margin-right:4px">{{ r.name }}</el-tag>
        </el-form-item>
        <el-form-item label="最后登录"><span>{{ authStore.user?.last_login_at || '-' }}</span></el-form-item>
      </el-form>
      <el-divider />
      <h4 style="margin-bottom:16px">修改密码</h4>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="100px">
        <el-form-item label="旧密码" prop="old_password"><el-input v-model="pwdForm.old_password" type="password" show-password /></el-form-item>
        <el-form-item label="新密码" prop="new_password"><el-input v-model="pwdForm.new_password" type="password" show-password /></el-form-item>
        <el-form-item label="确认密码" prop="confirm"><el-input v-model="pwdForm.confirm" type="password" show-password /></el-form-item>
        <el-form-item><el-button type="primary" @click="handleChangePwd" :loading="saving">修改密码</el-button></el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/api/auth'
import type { FormInstance } from 'element-plus'

const authStore = useAuthStore()
const saving = ref(false)
const pwdFormRef = ref<FormInstance>()

const form = reactive({
  display_name: authStore.user?.display_name || '',
  email: authStore.user?.email || '',
})

const pwdForm = reactive({ old_password: '', new_password: '', confirm: '' })
const validateConfirm = (_rule: any, value: string, cb: any) => {
  if (value !== pwdForm.new_password) cb(new Error('两次输入的密码不一致'))
  else cb()
}
const pwdRules = {
  old_password: [{ required: true, message: '请输入旧密码' }],
  new_password: [{ required: true, message: '请输入新密码' }, { min: 6, message: '至少6位' }],
  confirm: [{ required: true, message: '请确认密码' }, { validator: validateConfirm }],
}

async function handleChangePwd() {
  if (!pwdFormRef.value) return
  if (!(await pwdFormRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    await authApi.changePassword(pwdForm.old_password, pwdForm.new_password)
    ElMessage.success('密码修改成功，请重新登录')
    pwdForm.old_password = ''; pwdForm.new_password = ''; pwdForm.confirm = ''
  } catch (e: any) { ElMessage.error(e.response?.data?.error || '密码修改失败') }
  saving.value = false
}
</script>
