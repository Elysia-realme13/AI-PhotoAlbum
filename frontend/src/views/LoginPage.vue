<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-dark-bg dark:to-dark-card">
    <div class="w-full max-w-md">
      <div class="bg-white dark:bg-dark-card rounded-2xl shadow-xl p-8">
        <!-- Logo -->
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-900/30 mb-4">
            <el-icon :size="32" color="#409EFF"><PictureFilled /></el-icon>
          </div>
          <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">AI 智能相册</h2>
          <p class="text-gray-500 dark:text-dark-text-secondary mt-1 text-sm">让每一张照片都值得珍藏</p>
        </div>

        <!-- 切换 Tab -->
        <div class="flex mb-6 bg-gray-100 dark:bg-dark-hover rounded-lg p-1">
          <button
            :class="['flex-1 py-2 text-sm rounded-md transition', isLogin ? 'bg-white dark:bg-dark-card shadow text-blue-600 font-medium' : 'text-gray-500 dark:text-dark-text-secondary']"
            @click="isLogin = true"
          >
            登录
          </button>
          <button
            :class="['flex-1 py-2 text-sm rounded-md transition', !isLogin ? 'bg-white dark:bg-dark-card shadow text-blue-600 font-medium' : 'text-gray-500 dark:text-dark-text-secondary']"
            @click="isLogin = false"
          >
            注册
          </button>
        </div>

        <!-- 登录表单 -->
        <el-form v-if="isLogin" :model="loginForm" :rules="loginRules" ref="loginFormRef" @submit.prevent="handleLogin">
          <el-form-item prop="username">
            <el-input id="login-username" v-model="loginForm.username" placeholder="用户名或邮箱" :prefix-icon="User" size="large" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input id="login-password" v-model="loginForm.password" type="password" placeholder="密码" :prefix-icon="Lock" show-password size="large" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="large" class="w-full" :loading="loading" native-type="submit" @click="handleLogin">
              登 录
            </el-button>
          </el-form-item>
        </el-form>

        <!-- 注册表单 -->
        <el-form v-else :model="registerForm" :rules="registerRules" ref="registerFormRef" @submit.prevent="handleRegister">
          <el-form-item prop="username">
            <el-input id="register-username" v-model="registerForm.username" placeholder="用户名" :prefix-icon="User" size="large" />
          </el-form-item>
          <el-form-item prop="email">
            <el-input id="register-email" v-model="registerForm.email" placeholder="邮箱" :prefix-icon="Message" size="large" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input id="register-password" v-model="registerForm.password" type="password" placeholder="密码（至少6位）" :prefix-icon="Lock" show-password size="large" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="large" class="w-full" :loading="loading" native-type="submit" @click="handleRegister">
              注 册
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { authApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const isLogin = ref(true)
const loading = ref(false)

// 登录表单
const loginForm = reactive({ username: '', password: '' })
const loginRules = {
  username: [{ required: true, message: '请输入用户名或邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// 注册表单
const registerForm = reactive({ username: '', email: '', password: '' })
const registerRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
}

async function handleLogin() {
  loading.value = true
  try {
    const res = await authApi.login(loginForm)
    userStore.setAuth(res.data.access_token, res.data.user)
    ElMessage.success('登录成功')
    router.push('/home')
  } catch {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  loading.value = true
  try {
    const res = await authApi.register(registerForm)
    userStore.setAuth(res.data.access_token, res.data.user)
    ElMessage.success('注册成功')
    router.push('/home')
  } catch {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}
</script>
