<template>
  <div class="login-wrapper">
    <div class="login-card">
      <h1 class="login-title">GEO AI 智能体运营系统</h1>
      <p class="login-subtitle">企业级 GEO 全域智能体平台</p>
      <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="handleLogin">
        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" prefix-icon="Message" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" class="login-btn">
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ email: '', password: '' })
const rules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }],
}

async function handleLogin() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const profile = await authStore.login(form.email, form.password)
    ElMessage.success('登录成功')
    // Redirect by role
    const role = profile?.role_type || 'admin'
    let target = (route.query.redirect as string) || '/dashboard'
    if (role === 'customer_sub') target = '/paid-dashboard'
    else if (role === 'business_operator') target = '/demo-search'
    router.push(target)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '登录失败，请检查邮箱和密码')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.login-card {
  width: 400px;
  padding: 48px 40px 32px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  text-align: center;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.login-subtitle {
  font-size: 14px;
  text-align: center;
  color: #909399;
  margin-bottom: 32px;
}

.login-btn {
  width: 100%;
}

.login-hint {
  text-align: center;
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 16px;
}
</style>
