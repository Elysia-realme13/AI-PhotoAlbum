<template>
  <div class="max-w-3xl">
    <h2 class="text-2xl font-bold text-gray-800 mb-6">设置</h2>

    <!-- 账户信息 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-4">
      <h3 class="text-lg font-semibold text-gray-800 mb-4">账户信息</h3>
      <div class="flex items-center gap-4">
        <div
          class="w-16 h-16 rounded-full bg-blue-500 text-white flex items-center justify-center text-2xl font-bold overflow-hidden shrink-0"
        >
          <img v-if="user?.avatar_url" :src="user.avatar_url" class="w-full h-full object-cover" />
          <span v-else>{{ avatarText }}</span>
        </div>
        <div class="space-y-1">
          <p class="text-lg font-medium text-gray-800">{{ user?.nickname || user?.username || '未登录' }}</p>
          <p class="text-sm text-gray-500">用户名：{{ user?.username || '-' }}</p>
          <p class="text-sm text-gray-500">邮箱：{{ user?.email || '-' }}</p>
        </div>
      </div>
    </div>

    <!-- 相册统计 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-4">
      <h3 class="text-lg font-semibold text-gray-800 mb-4">相册统计</h3>
      <div v-if="statsLoading" class="grid grid-cols-2 gap-4">
        <div v-for="i in 4" :key="i" class="h-14 bg-gray-100 rounded-lg animate-pulse" />
      </div>
      <div v-else class="grid grid-cols-2 gap-4">
        <div class="p-3 rounded-lg bg-gray-50">
          <p class="text-sm text-gray-500">照片总数</p>
          <p class="text-xl font-bold text-gray-800 mt-1">{{ stats.total }}</p>
        </div>
        <div class="p-3 rounded-lg bg-gray-50">
          <p class="text-sm text-gray-500">存储占用</p>
          <p class="text-xl font-bold text-gray-800 mt-1">{{ stats.size }}</p>
        </div>
        <div class="p-3 rounded-lg bg-gray-50">
          <p class="text-sm text-gray-500">格式分布</p>
          <p class="text-sm font-medium text-gray-700 mt-1">{{ stats.formats || '-' }}</p>
        </div>
        <div class="p-3 rounded-lg bg-gray-50">
          <p class="text-sm text-gray-500">时间跨度</p>
          <p class="text-sm font-medium text-gray-700 mt-1">{{ stats.span || '-' }}</p>
        </div>
      </div>
    </div>

    <!-- 偏好设置 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-4">
      <h3 class="text-lg font-semibold text-gray-800 mb-4">偏好设置</h3>
      <el-form label-width="120px" label-position="left">
        <el-form-item label="每页显示数量">
          <el-select v-model="prefs.pageSize" style="width: 160px" @change="savePrefs">
            <el-option :value="20" label="20 张 / 页" />
            <el-option :value="40" label="40 张 / 页" />
            <el-option :value="80" label="80 张 / 页" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认排序">
          <el-select v-model="prefs.sortOrder" style="width: 160px" @change="savePrefs">
            <el-option value="desc" label="最新优先" />
            <el-option value="asc" label="最早优先" />
          </el-select>
        </el-form-item>
      </el-form>
      <p class="text-xs text-gray-400">偏好保存在本地浏览器，实时生效。</p>
    </div>

    <!-- 个人资料修改 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-4">
      <h3 class="text-lg font-semibold text-gray-800 mb-3">个人资料</h3>
      <el-alert type="info" :closable="false" show-icon class="mb-4" title="该功能需后端接口支持，后端就绪后即可生效" />
      <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="120px" label-position="left">
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="profileForm.nickname" placeholder="请输入昵称" style="max-width: 320px" />
        </el-form-item>
        <el-form-item label="头像链接" prop="avatar_url">
          <el-input v-model="profileForm.avatar_url" placeholder="请输入头像图片 URL" style="max-width: 320px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="profileSaving" @click="saveProfile">保存资料</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 修改密码 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h3 class="text-lg font-semibold text-gray-800 mb-3">修改密码</h3>
      <el-alert type="info" :closable="false" show-icon class="mb-4" title="该功能需后端接口支持，后端就绪后即可生效" />
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="120px" label-position="left">
        <el-form-item label="当前密码" prop="old_password">
          <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入当前密码" style="max-width: 320px" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="请输入新密码" style="max-width: 320px" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="pwdForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" style="max-width: 320px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="pwdSaving" @click="savePassword">修改密码</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api/auth'
import { loadAllPhotos } from '@/api/search'
import type { PhotoItem } from '@/types/photo'

const userStore = useUserStore()
const { user } = storeToRefs(userStore)

const avatarText = computed(() => {
  const name = user.value?.nickname || user.value?.username || '?'
  return name.charAt(0).toUpperCase()
})

// ── 相册统计 ─────────────────────────
const statsLoading = ref(true)
const stats = reactive({
  total: 0,
  size: '0 B',
  formats: '',
  span: '',
})

function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const value = bytes / Math.pow(1024, i)
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function ymd(ts?: string): string {
  if (!ts) return ''
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function computeStats(photos: PhotoItem[]) {
  stats.total = photos.length

  const totalBytes = photos.reduce((sum, p) => sum + (p.file_size || 0), 0)
  stats.size = formatBytes(totalBytes)

  // 格式分布
  const fmtCounter: Record<string, number> = {}
  for (const p of photos) {
    const fmt = (p.file_type || 'unknown').toUpperCase()
    fmtCounter[fmt] = (fmtCounter[fmt] || 0) + 1
  }
  stats.formats = Object.entries(fmtCounter)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([fmt, n]) => `${fmt} ${n}`)
    .join('、')

  // 时间跨度
  const times = photos
    .map((p) => p.photo_time || p.upload_time)
    .filter((t): t is string => !!t)
    .sort()
  if (times.length > 0) {
    const first = ymd(times[0])
    const last = ymd(times[times.length - 1])
    stats.span = first === last ? first : `${first} ~ ${last}`
  }
}

// ── 偏好设置（localStorage 持久化） ─────────────────
const PREF_KEY = 'settings.preferences'
const prefs = reactive({
  pageSize: 40,
  sortOrder: 'desc' as 'desc' | 'asc',
})

function loadPrefs() {
  const raw = localStorage.getItem(PREF_KEY)
  if (raw) {
    try {
      const saved = JSON.parse(raw)
      if (saved.pageSize) prefs.pageSize = saved.pageSize
      if (saved.sortOrder) prefs.sortOrder = saved.sortOrder
    } catch {
      // ignore
    }
  }
}

function savePrefs() {
  localStorage.setItem(PREF_KEY, JSON.stringify({ ...prefs }))
  ElMessage.success('偏好已保存')
}

// ── 个人资料修改（预留接口） ─────────────────
const profileFormRef = ref<FormInstance>()
const profileSaving = ref(false)
const profileForm = reactive({
  nickname: '',
  avatar_url: '',
})
const profileRules: FormRules = {
  nickname: [{ max: 30, message: '昵称不超过 30 个字符', trigger: 'blur' }],
}

async function saveProfile() {
  if (!profileFormRef.value) return
  const valid = await profileFormRef.value.validate().catch(() => false)
  if (!valid) return
  profileSaving.value = true
  try {
    await authApi.updateProfile({
      nickname: profileForm.nickname || undefined,
      avatar_url: profileForm.avatar_url || undefined,
    })
    ElMessage.success('资料已更新')
    await userStore.fetchUser()
  } catch {
    ElMessage.warning('资料修改功能待后端接口支持')
  } finally {
    profileSaving.value = false
  }
}

// ── 修改密码（预留接口） ─────────────────
const pwdFormRef = ref<FormInstance>()
const pwdSaving = ref(false)
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})
const pwdRules: FormRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== pwdForm.new_password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function savePassword() {
  if (!pwdFormRef.value) return
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return
  pwdSaving.value = true
  try {
    await authApi.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    ElMessage.success('密码已修改')
    pwdFormRef.value.resetFields()
  } catch {
    ElMessage.warning('修改密码功能待后端接口支持')
  } finally {
    pwdSaving.value = false
  }
}

// ── 初始化 ─────────────────────────
onMounted(async () => {
  loadPrefs()
  profileForm.nickname = user.value?.nickname || ''
  profileForm.avatar_url = user.value?.avatar_url || ''
  try {
    const photos = await loadAllPhotos()
    computeStats(photos)
  } finally {
    statsLoading.value = false
  }
})
</script>
