<template>
  <div class="flex items-center justify-center h-screen bg-gray-50 dark:bg-dark-bg">
    <div class="text-center">
      <h1 class="text-6xl font-bold text-gray-300 dark:text-dark-border mb-4">404</h1>
      <p class="text-gray-500 dark:text-dark-text-secondary mb-6">页面不存在</p>
      <el-button type="primary" @click="$router.push('/home')">返回首页</el-button>
    </div>
  </div>
</template>
