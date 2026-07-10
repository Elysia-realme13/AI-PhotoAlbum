<template>
  <div>
    <h2 class="text-2xl font-bold text-gray-800 mb-6">首页</h2>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-500 text-sm">总照片数</p>
            <p class="text-3xl font-bold text-gray-800 mt-1">{{ stats.photos }}</p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center">
            <el-icon :size="24" color="#409EFF"><PictureFilled /></el-icon>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-500 text-sm">相册数</p>
            <p class="text-3xl font-bold text-gray-800 mt-1">{{ stats.albums }}</p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-green-50 flex items-center justify-center">
            <el-icon :size="24" color="#67C23A"><Folder /></el-icon>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-500 text-sm">识别人物</p>
            <p class="text-3xl font-bold text-gray-800 mt-1">{{ stats.faces }}</p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-purple-50 flex items-center justify-center">
            <el-icon :size="24" color="#9C27B0"><UserFilled /></el-icon>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-500 text-sm">足迹城市</p>
            <p class="text-3xl font-bold text-gray-800 mt-1">{{ stats.cities }}</p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-orange-50 flex items-center justify-center">
            <el-icon :size="24" color="#E6A23C"><Location /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近上传 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h3 class="text-lg font-semibold text-gray-800 mb-4">最近上传</h3>
      <el-empty v-if="recentPhotos.length === 0" description="还没有照片，快去上传吧！" />
      <div v-else class="grid grid-cols-6 gap-3">
        <div v-for="photo in recentPhotos" :key="photo.id"
          class="aspect-square bg-gray-100 rounded-lg overflow-hidden">
          <img :src="`/api/medias/${photo.id}/thumbnail`" class="w-full h-full object-cover" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

const stats = reactive({
  photos: 0,
  albums: 0,
  faces: 0,
  cities: 0,
})

const recentPhotos: any[] = []
</script>
