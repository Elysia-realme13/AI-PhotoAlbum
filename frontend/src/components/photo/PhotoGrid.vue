<template>
  <div>
    <!-- 加载骨架屏 -->
    <div v-if="loading" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
      <div v-for="i in 12" :key="i" class="aspect-square rounded-lg bg-gray-200 animate-pulse" />
    </div>

    <!-- 空状态 -->
    <el-empty v-else-if="photos.length === 0" description="还没有照片，快去上传吧！">
      <el-button type="primary" @click="$emit('upload')">上传照片</el-button>
    </el-empty>

    <!-- 照片网格 -->
    <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
      <PhotoCard
        v-for="photo in photos"
        :key="photo.id"
        :photo="photo"
        @click="$emit('preview', photo)"
        @delete="$emit('delete', photo)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import PhotoCard from './PhotoCard.vue'
import type { PhotoItem } from '@/types/photo'

defineProps<{
  photos: PhotoItem[]
  loading: boolean
}>()

defineEmits<{
  upload: []
  preview: [photo: PhotoItem]
  delete: [photo: PhotoItem]
}>()
</script>
