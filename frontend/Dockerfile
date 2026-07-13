# 前端 Dockerfile — 多阶段构建
# 固定 node 和 nginx 小版本，避免基础镜像漂移
FROM node:20.18-alpine AS build

WORKDIR /app

# 先复制依赖文件（利用 Docker 缓存层）
COPY package.json package-lock.json ./

# npm ci 严格按 lock 文件安装，不重新解析版本
RUN npm ci

COPY . .
RUN npm run build

# 生产阶段 — Nginx
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
