<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-dark-bg dark:to-dark-card">
    <div class="max-w-3xl mx-auto px-6 py-12">
      <!-- 标题 -->
      <div class="text-center mb-10">
        <router-link to="/login" class="inline-flex items-center gap-1 text-sm text-gray-400 dark:text-dark-text-secondary hover:text-blue-500 transition-colors mb-6">
          <el-icon><ArrowLeft /></el-icon>
          返回登录
        </router-link>
        <h1 class="text-3xl font-bold text-gray-800 dark:text-dark-text">服务协议与隐私声明</h1>
        <p class="text-gray-400 dark:text-dark-text-secondary mt-2 text-sm">最后更新日期：2026 年 7 月 20 日</p>
      </div>

      <!-- 内容 -->
      <div class="bg-white dark:bg-dark-card rounded-2xl shadow-lg p-8 md:p-10 space-y-10 text-sm text-gray-600 dark:text-dark-text-secondary leading-relaxed">

        <!-- ============ 第一部分：服务协议 ============ -->
        <section>
          <h2 class="text-xl font-bold text-gray-800 dark:text-dark-text mb-4 pb-2 border-b border-gray-100 dark:border-dark-border">一、服务协议</h2>

          <div class="space-y-4">
            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">1. 服务说明</h3>
              <p>AI 智能相册（以下简称"本服务"）是一款基于人工智能技术的照片管理与分析工具，提供照片存储、智能分类、人脸识别、以文搜图、对象检测等功能。</p>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">2. 账号管理</h3>
              <p>用户注册时需提供真实、准确的个人信息。用户应对其账号下的所有操作负责，不得将账号转让、出借或共享给他人使用。如发现账号异常，应立即通知我们。</p>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">3. 使用规范</h3>
              <p>用户不得利用本服务上传、存储或传播任何违反法律法规的内容，包括但不限于：侵犯他人隐私、知识产权的内容；含有病毒、恶意代码的文件；任何形式的违法或不当内容。我们保留对违规账户采取限制措施的权利。</p>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">4. AI 功能说明</h3>
              <p>本服务的 AI 功能（人脸识别、对象检测、图像描述等）均在用户本地或用户指定的服务器上运行。AI 分析结果仅供辅助参考，不构成任何形式的保证。用户应自行判断分析结果的准确性和适用性。</p>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">5. 免责条款</h3>
              <p>本服务按"现状"提供，不提供任何明示或暗示的担保。我们不对因使用本服务而产生的数据丢失、服务中断等问题承担赔偿责任。用户应自行备份重要数据。</p>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">6. 服务变更与终止</h3>
              <p>我们有权根据业务发展需要，随时调整、暂停或终止本服务的全部或部分功能，恕不另行通知。用户可随时停止使用本服务并删除账户。</p>
            </div>
          </div>
        </section>

        <!-- ============ 第二部分：隐私声明 ============ -->
        <section>
          <h2 class="text-xl font-bold text-gray-800 dark:text-dark-text mb-4 pb-2 border-b border-gray-100 dark:border-dark-border">二、隐私声明</h2>

          <div class="space-y-4">
            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">1. 信息收集</h3>
              <p>我们在您使用本服务时可能收集以下信息：</p>
              <ul class="list-disc pl-5 space-y-1 mt-1">
                <li><strong>账号信息：</strong>用户名、邮箱、昵称、头像等注册信息。</li>
                <li><strong>照片数据：</strong>您上传的照片文件及其 EXIF 元数据（拍摄时间、GPS 位置、设备信息等）。</li>
                <li><strong>AI 分析结果：</strong>人脸特征向量、对象标签、图像描述等由 AI 模型生成的元数据。</li>
                <li><strong>使用日志：</strong>访问时间、操作记录等技术日志。</li>
              </ul>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">2. 信息使用</h3>
              <p>我们收集的信息仅用于以下目的：</p>
              <ul class="list-disc pl-5 space-y-1 mt-1">
                <li>提供和维护照片管理、AI 分析等核心功能；</li>
                <li>改善和优化服务质量与用户体验；</li>
                <li>保障账户安全和防范欺诈行为；</li>
                <li>遵守适用法律法规的要求。</li>
              </ul>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">3. 数据存储与安全</h3>
              <p>您的所有数据（照片、元数据、AI 分析结果）均存储在您自己部署的服务器或本地环境中。我们采用行业标准的安全措施保护您的数据，但无法保证绝对的安全。建议您定期备份重要数据。</p>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">4. 数据共享</h3>
              <p>除非满足以下任一条件，我们不会向第三方共享您的个人信息：</p>
              <ul class="list-disc pl-5 space-y-1 mt-1">
                <li>获得您的明确同意；</li>
                <li>法律法规要求或政府机关依法请求；</li>
                <li>为保护我们的合法权益所必需。</li>
              </ul>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">5. AI 数据处理</h3>
              <p>本服务使用本地部署的 AI 模型进行图像分析。人脸特征向量、图像嵌入向量等数据仅存储在您的本地数据库中，不会上传至任何第三方服务器。AI 模型推理过程均在本地完成。</p>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">6. 用户权利</h3>
              <p>您有权随时：查看、更正您的个人信息；导出您的照片和数据；删除您的账户及所有关联数据。账户删除后，所有相关数据将被永久清除且不可恢复。</p>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">7. Cookie 与本地存储</h3>
              <p>本服务使用浏览器本地存储（LocalStorage）保存登录状态和用户偏好设置，不包含第三方追踪 Cookie。</p>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">8. 政策更新</h3>
              <p>我们可能会不时更新本协议与隐私声明。更新后的版本将在本页面发布，继续使用本服务即表示您同意更新后的条款。</p>
            </div>

            <div>
              <h3 class="font-semibold text-gray-700 dark:text-gray-300 mb-2">9. 联系方式</h3>
              <p>如对本协议或隐私声明有任何疑问，请通过项目 GitHub 仓库提交 Issue 或联系项目维护者。</p>
            </div>
          </div>
        </section>

        <!-- 返回 -->
        <div class="text-center pt-4">
          <router-link to="/login" class="text-blue-500 hover:text-blue-600 text-sm">← 返回登录页面</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
</script>
