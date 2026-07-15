# Pull Request: 相册管理功能 + UI动画优化

## 变更概述

本次PR包含两个主要功能：

### 1. 相册管理功能
- **后端API**：实现完整的相册CRUD API
  - 创建相册 (`POST /api/albums`)
  - 获取相册列表 (`GET /api/albums`)
  - 获取相册详情 (`GET /api/albums/{id}`)
  - 更新相册 (`PUT /api/albums/{id}`)
  - 删除相册 (`DELETE /api/albums/{id}`)
  - 相册照片管理（添加/移除照片，分页查询）

- **前端实现**：
  - 新增相册API封装 (`frontend/src/api/album.ts`)
  - 优化相册页面，添加删除功能
  - 添加创建相册按钮
  - 删除确认对话框

### 2. UI动画优化
- **导航栏重新设计**：
  - 深色渐变背景（from-slate-900 to-slate-800）
  - 添加应用Logo和标题
  - 悬停动画效果（向右移动4px）
  - 活跃状态指示器（蓝色渐变背景 + 左侧白色竖条）

- **页面动画**：
  - 页面过渡动画（page-fade）
  - 照片卡片悬停效果（上浮+阴影增强）
  - 照片网格进入动画（交错淡入）

- **配置修复**：
  - 修复vite代理端口配置（8001→8000）
  - 添加照片位置API端点

## 技术实现

### 后端
- **CRUD模块**：`backend/app/crud/album.py` - 相册数据库操作
- **API路由**：`backend/app/api/album.py` - RESTful API端点
- **数据模型**：使用现有的Album和AlbumPhoto模型
- **认证**：所有API都需要JWT Token认证
- **权限控制**：用户只能操作自己的相册

### 前端
- **API封装**：`frontend/src/api/album.ts` - 相册API调用
- **页面组件**：`frontend/src/views/AlbumPage.vue` - 相册管理页面
- **UI动画**：`frontend/src/main.css` - CSS动画样式
- **组件优化**：`AppSidebar.vue`, `PhotoCard.vue`, `PhotoGrid.vue`

## 文件变更

### 新增文件
- `backend/app/crud/album.py` - 相册CRUD操作

### 修改文件
- `backend/app/api/album.py` - 相册API路由
- `frontend/src/api/album.ts` - 相册API封装
- `frontend/src/views/AlbumPage.vue` - 相册页面
- `frontend/src/main.css` - 动画样式
- `frontend/src/components/layout/AppSidebar.vue` - 导航栏
- `frontend/src/components/photo/PhotoCard.vue` - 照片卡片
- `frontend/src/components/photo/PhotoGrid.vue` - 照片网格
- `frontend/src/App.vue` - 页面过渡
- `frontend/vite.config.ts` - 代理配置
- `backend/app/api/photo.py` - 照片位置API
- `README.md` - 项目文档

## 测试验证

### 后端API测试
```bash
# 创建相册
curl -X POST http://localhost:8000/api/albums \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试相册","description":"测试描述"}'

# 获取相册列表
curl http://localhost:8000/api/albums \
  -H "Authorization: Bearer <token>"

# 删除相册
curl -X DELETE http://localhost:8000/api/albums/<album_id> \
  -H "Authorization: Bearer <token>"
```

### 前端测试
1. 访问 `http://localhost:5173`
2. 登录后进入相册页面
3. 测试创建相册功能
4. 测试删除相册功能（悬停显示删除按钮）
5. 验证UI动画效果

## 端口变更说明

本次更新将后端开发端口从8001统一为8000：
- 原配置：开发模式用8001，Docker用8000
- 新配置：开发模式和Docker统一使用8000
- 原因：简化配置，避免端口混淆

## 部署注意事项

1. **数据库**：无需迁移，使用现有表结构
2. **环境变量**：无需新增配置
3. **依赖**：无新增依赖
4. **端口**：后端统一使用8000端口

## 相关Issue

- 实现Phase 4相册管理功能
- 优化前端用户体验
- 统一后端端口配置

## 截图/演示

### 相册页面
- 相册列表展示
- 删除确认对话框
- 创建相册按钮

### UI动画
- 导航栏悬停效果
- 页面过渡动画
- 照片卡片悬停效果

---

**分支名称**：`feature/album-management`  
**目标分支**：`master`  
**变更类型**：功能增强 + UI优化