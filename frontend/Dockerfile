# 前端 Dockerfile — 多阶段构建
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json ./

# 使用 npm 安装依赖
RUN npm install

COPY . .
RUN npm run build

# 生产阶段 — Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
