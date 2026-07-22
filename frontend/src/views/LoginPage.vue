<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-dark-bg dark:to-dark-card">
    <div class="w-full max-w-md">
      <div class="bg-white dark:bg-dark-card rounded-2xl shadow-xl p-8">
        <!-- 返回首页 -->
        <router-link to="/" class="inline-flex items-center gap-1 text-sm text-gray-400 dark:text-dark-text-secondary hover:text-blue-500 dark:hover:text-blue-400 transition-colors mb-6">
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </router-link>

        <!-- Logo / 上次登录用户头像 -->
        <div class="text-center mb-8">
          <template v-if="isLogin && displayUser">
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-500 text-white text-2xl font-bold overflow-hidden mb-4">
              <img v-if="displayUser.avatar_url && !avatarLoadError" :src="displayUser.avatar_url" class="w-full h-full object-cover" alt="头像" @error="avatarLoadError = true" />
              <span v-else>{{ displayInitial }}</span>
            </div>
            <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">欢迎回来，{{ displayUser.nickname || displayUser.username }}</h2>
            <p class="text-gray-500 dark:text-dark-text-secondary mt-1 text-sm">登录以继续你的智能相册</p>
          </template>
          <template v-else>
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-900/30 mb-4">
              <el-icon :size="32" color="#409EFF"><PictureFilled /></el-icon>
            </div>
            <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">AI 智能相册</h2>
            <p class="text-gray-500 dark:text-dark-text-secondary mt-1 text-sm">让每一张照片都值得珍藏</p>
          </template>
        </div>

        <!-- 切换 Tab -->
        <div class="flex mb-6 bg-gray-100 dark:bg-dark-hover rounded-lg p-1">
          <button
            :class="['flex-1 py-2 text-sm rounded-md transition', isLogin ? 'bg-white dark:bg-dark-card shadow text-blue-600 font-medium' : 'text-gray-500 dark:text-dark-text-secondary']"
            @click="switchToLogin"
          >
            登录
          </button>
          <button
            :class="['flex-1 py-2 text-sm rounded-md transition', !isLogin ? 'bg-white dark:bg-dark-card shadow text-blue-600 font-medium' : 'text-gray-500 dark:text-dark-text-secondary']"
            @click="switchToRegister"
          >
            注册
          </button>
        </div>

        <!-- 登录表单 -->
        <el-form v-if="isLogin" :model="loginForm" :rules="loginRules" ref="loginFormRef" @submit.prevent="handleLogin">
          <el-form-item prop="username">
            <el-input v-model="loginForm.username" placeholder="用户名或邮箱" :prefix-icon="User" size="large" @input="onUsernameInput">
              <template #suffix>
                <el-dropdown v-if="knownUsers.length > 0" trigger="click" @command="selectKnownUser">
                  <el-icon class="cursor-pointer text-gray-400 hover:text-blue-500 transition-colors">
                    <ArrowDown />
                  </el-icon>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item v-for="user in knownUsers" :key="user.username" :command="user">
                        <div class="flex items-center gap-2">
                          <span class="font-medium">{{ user.nickname || user.username }}</span>
                          <span class="text-xs text-gray-400">@{{ user.username }}</span>
                        </div>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="loginForm.password" type="password" placeholder="密码" :prefix-icon="Lock" :show-password="!passwordAutoFilled" size="large" @keyup.enter="handleLogin" @input="passwordAutoFilled = false" />
          </el-form-item>

          <!-- 验证码 -->
          <el-form-item prop="captcha_code">
            <div class="flex gap-3">
              <el-input
                v-model="loginForm.captcha_code"
                placeholder="验证码"
                :prefix-icon="Key"
                size="large"
                class="flex-1"
                maxlength="4"
                @keyup.enter="handleLogin"
              />
              <img
                :src="captchaImage"
                alt="验证码"
                class="h-[50px] w-[140px] rounded-lg border border-gray-200 dark:border-dark-border cursor-pointer select-none flex-shrink-0 bg-white"
                title="点击刷新验证码"
                @click="refreshCaptcha"
              />
            </div>
          </el-form-item>

          <!-- 记住密码 + 同意协议 -->
          <el-form-item>
            <div class="flex items-center justify-between w-full gap-4">
              <el-checkbox v-model="rememberPassword" size="small" @keyup.enter="handleLogin">记住密码</el-checkbox>
              <el-checkbox v-model="agreedToTerms" size="small" @keyup.enter="handleLogin">
                <span class="text-xs text-gray-400 dark:text-dark-text-secondary">
                  已阅读并同意
                  <router-link to="/terms" target="_blank" class="text-blue-500 hover:text-blue-600">《服务协议》</router-link>
                  <router-link to="/terms" target="_blank" class="text-blue-500 hover:text-blue-600">《隐私声明》</router-link>
                </span>
              </el-checkbox>
            </div>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" size="large" class="w-full" :loading="loading" :disabled="!agreedToTerms" @click="handleLogin">
              登 录
            </el-button>
          </el-form-item>
        </el-form>

        <!-- 注册表单 -->
        <el-form v-else :model="registerForm" :rules="registerRules" ref="registerFormRef" @submit.prevent="handleRegister">
          <el-form-item prop="username">
            <el-input v-model="registerForm.username" placeholder="用户名" :prefix-icon="User" size="large" />
          </el-form-item>
          <el-form-item prop="email">
            <el-input v-model="registerForm.email" placeholder="邮箱" :prefix-icon="Message" size="large" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="registerForm.password" type="password" placeholder="密码（至少6位）" :prefix-icon="Lock" show-password size="large" />
          </el-form-item>

          <!-- 验证码 -->
          <el-form-item prop="captcha_code">
            <div class="flex gap-3">
              <el-input
                v-model="registerForm.captcha_code"
                placeholder="验证码"
                :prefix-icon="Key"
                size="large"
                class="flex-1"
                maxlength="4"
              />
              <img
                :src="captchaImage"
                alt="验证码"
                class="h-[50px] w-[140px] rounded-lg border border-gray-200 dark:border-dark-border cursor-pointer select-none flex-shrink-0 bg-white"
                title="点击刷新验证码"
                @click="refreshCaptcha"
              />
            </div>
          </el-form-item>

          <!-- 同意协议 -->
          <el-form-item>
            <el-checkbox v-model="agreedToTerms" size="small">
              <span class="text-xs text-gray-400 dark:text-dark-text-secondary">
                我已阅读并同意
                <router-link to="/terms" target="_blank" class="text-blue-500 hover:text-blue-600">《服务协议》</router-link>
                和
                <router-link to="/terms" target="_blank" class="text-blue-500 hover:text-blue-600">《隐私声明》</router-link>
              </span>
            </el-checkbox>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" size="large" class="w-full" :loading="loading" :disabled="!agreedToTerms" @click="handleRegister">
              注册并登录
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, User, Lock, Message, Key, ArrowDown } from '@element-plus/icons-vue'
import { authApi } from '@/api/auth'
import { useUserStore, getKnownUsers } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const isLogin = ref(true)
const loading = ref(false)

// ── 记住密码 ─────────────────────────
const REMEMBER_KEY = 'remembered_credentials'
const rememberPassword = ref(false)
// 密码是否由"记住密码"自动填入（不可查看）
const passwordAutoFilled = ref(false)

// 存储格式: { "username": "password", ... }
function loadCredentialMap(): Record<string, string> {
  try {
    const raw = localStorage.getItem(REMEMBER_KEY)
    if (!raw) return {}
    const map = JSON.parse(raw)
    return typeof map === 'object' && !Array.isArray(map) ? map : {}
  } catch { return {} }
}

function saveCredentials(username: string, password: string) {
  const map = loadCredentialMap()
  map[username] = password
  localStorage.setItem(REMEMBER_KEY, JSON.stringify(map))
}

function removeCredential(username: string) {
  const map = loadCredentialMap()
  delete map[username]
  if (Object.keys(map).length === 0) {
    localStorage.removeItem(REMEMBER_KEY)
  } else {
    localStorage.setItem(REMEMBER_KEY, JSON.stringify(map))
  }
}

const credentialMap = loadCredentialMap()
// ── 验证码 ───────────────────────────
const captchaId = ref('')
const captchaImage = ref('')
const captchaLoading = ref(false)
const avatarLoadError = ref(false)

async function refreshCaptcha() {
  captchaLoading.value = true
  try {
    const res = await authApi.getCaptcha()
    captchaId.value = res.data.captcha_id
    captchaImage.value = res.data.captcha_image
  } catch {
    // 忽略
  } finally {
    captchaLoading.value = false
  }
}

// ── 登录表单 ─────────────────────────
const loginForm = reactive({
  username: '',
  password: '',
  captcha_code: '',
})

// ── 切换账号刷新验证码 ───────────────
// 记录上次尝试登录的用户名，用于检测账号切换
const lastLoginAttemptUsername = ref('')

// ── 同意协议 ─────────────────────────
const TERMS_KEY = 'term_agreements'

function loadTermAgreementMap(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(TERMS_KEY)
    if (!raw) return {}
    const map = JSON.parse(raw)
    return typeof map === 'object' && !Array.isArray(map) ? map : {}
  } catch { return {} }
}

function saveTermAgreement(username: string) {
  const map = loadTermAgreementMap()
  map[username] = true
  localStorage.setItem(TERMS_KEY, JSON.stringify(map))
}

const termAgreementMap = loadTermAgreementMap()
const agreedToTerms = ref(false)

// 本地登录过的用户
const knownUsers = getKnownUsers()

const loginRules = {
  username: [{ required: true, message: '请输入用户名或邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

// 顶部展示的用户
const displayUser = computed(() => {
  const input = loginForm.username.trim().toLowerCase()
  if (input) {
    return (
      knownUsers.find(
        (u) => u.username.toLowerCase() === input || u.email?.toLowerCase() === input,
      ) || null
    )
  }
  return null
})
const displayInitial = computed(() => {
  const name = displayUser.value?.nickname || displayUser.value?.username || '?'
  return name.charAt(0).toUpperCase()
})

function onUsernameInput() {
  avatarLoadError.value = false
  const input = loginForm.username.trim()

  // 匹配已保存的密码：自动填入且不可查看
  if (input && credentialMap[input]) {
    loginForm.password = credentialMap[input]
    passwordAutoFilled.value = true
  } else {
    if (passwordAutoFilled.value) {
      loginForm.password = ''
      passwordAutoFilled.value = false
    }
  }

  // 匹配已同意协议的用户：自动勾选
  agreedToTerms.value = input ? !!termAgreementMap[input] : false

  // 匹配已保存密码的账号：自动勾选记住密码
  rememberPassword.value = input ? !!credentialMap[input] : false

  // 用户切换到了另一账号（之前尝试过登录），刷新验证码
  if (lastLoginAttemptUsername.value && input && input !== lastLoginAttemptUsername.value) {
    loginForm.captcha_code = ''
    refreshCaptcha()
    lastLoginAttemptUsername.value = ''
  }
  // 用户名被清空时，清空验证码输入
  if (!input && lastLoginAttemptUsername.value) {
    loginForm.captcha_code = ''
  }
}

function selectKnownUser(user: { username: string }) {
  loginForm.username = user.username
  onUsernameInput()
  lastLoginAttemptUsername.value = ''
  // 切换账号时刷新验证码并清空已输入的验证码
  loginForm.captcha_code = ''
  refreshCaptcha()
}

function switchToLogin() {
  isLogin.value = true
  // 根据当前输入的用户名判断是否默认勾选协议
  const input = loginForm.username.trim()
  agreedToTerms.value = input ? !!termAgreementMap[input] : false
  refreshCaptcha()
}

// ── 注册表单 ─────────────────────────
const registerForm = reactive({ username: '', email: '', password: '', captcha_code: '' })
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
  captcha_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

function switchToRegister() {
  isLogin.value = false
  agreedToTerms.value = false
  refreshCaptcha()
}

// ── 登录 ─────────────────────────────
async function handleLogin() {
  if (!agreedToTerms.value) {
    ElMessage.warning('请先阅读并同意服务协议和隐私声明')
    return
  }
  // 记录本次登录尝试的用户名，用于切换账号时自动刷新验证码
  lastLoginAttemptUsername.value = loginForm.username.trim()
  loading.value = true
  try {
    const res = await authApi.login({
      username: loginForm.username,
      password: loginForm.password,
      captcha_id: captchaId.value,
      captcha_code: loginForm.captcha_code,
    })

    // 记住密码
    if (rememberPassword.value) {
      saveCredentials(loginForm.username, loginForm.password)
    } else {
      removeCredential(loginForm.username)
    }

    // 记住协议同意
    if (agreedToTerms.value) {
      saveTermAgreement(loginForm.username)
    }

    userStore.setAuth(res.data.access_token, res.data.user)
    ElMessage.success('登录成功')
    router.push('/home')
  } catch (err: any) {
    // 验证码错误时刷新（等待刷新完成，防止竞态）
    const msg = err?.response?.data?.detail || ''
    if (msg.includes('验证码')) {
      loginForm.captcha_code = ''
      await refreshCaptcha()
    }
  } finally {
    loading.value = false
  }
}

// ── 注册 ─────────────────────────────
async function handleRegister() {
  loading.value = true
  try {
    const res = await authApi.register({
      ...registerForm,
      captcha_id: captchaId.value,
      captcha_code: registerForm.captcha_code,
    })
    userStore.setAuth(res.data.access_token, res.data.user)
    ElMessage.success('注册成功')
    router.push('/home')
  } catch (err: any) {
    // 验证码错误时刷新
    const msg = err?.response?.data?.detail || ''
    if (msg.includes('验证码')) {
      registerForm.captcha_code = ''
      await refreshCaptcha()
    }
  } finally {
    loading.value = false
  }
}

// ── 初始化 ───────────────────────────
onMounted(() => {
  if (isLogin.value) {
    refreshCaptcha()
  }
  // 根据当前输入同步协议状态
  nextTick(() => {
    const input = loginForm.username.trim()
    agreedToTerms.value = input ? !!termAgreementMap[input] : false
  })
})
</script>
