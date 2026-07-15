# 推送到自己的仓库

## 当前状态

您当前的远程仓库配置：
```
origin	git@github.com:boneluo/AI-PhotoAlbum.git (fetch)
origin	git@github.com:boneluo/AI-PhotoAlbum.git (push)
```

## 步骤一：Fork 仓库

1. 访问 https://github.com/boneluo/AI-PhotoAlbum
2. 点击右上角的 **Fork** 按钮
3. 选择您的 GitHub 账号
4. 等待 Fork 完成

完成后，您将拥有：`https://github.com/您的用户名/AI-PhotoAlbum`

## 步骤二：添加您的 Fork 作为远程仓库

```bash
# 添加您的 fork 作为新的远程仓库（命名为 myfork）
git remote add myfork git@github.com:您的用户名/AI-PhotoAlbum.git

# 验证远程仓库配置
git remote -v
```

预期输出：
```
myfork	git@github.com:您的用户名/AI-PhotoAlbum.git (fetch)
myfork	git@github.com:您的用户名/AI-PhotoAlbum.git (push)
origin	git@github.com:boneluo/AI-PhotoAlbum.git (fetch)
origin	git@github.com:boneluo/AI-PhotoAlbum.git (push)
```

## 步骤三：推送到您的 Fork

```bash
# 推送 feature/album-management 分支到您的 fork
git push -u myfork feature/album-management
```

## 步骤四：创建 Pull Request

1. 访问您的 Fork 页面：`https://github.com/您的用户名/AI-PhotoAlbum`
2. 点击 **Compare & pull request** 按钮
3. 填写 PR 信息：
   - **标题**：`feat(album): 新增相册CRUD功能和UI动画优化`
   - **描述**：复制 `PR_DESCRIPTION.md` 的内容
4. 点击 **Create pull request** 按钮

## 替代方案：使用 HTTPS

如果 SSH 方式有问题，可以使用 HTTPS：

```bash
# 删除旧的 myfork（如果有）
git remote remove myfork

# 添加 HTTPS 方式
git remote add myfork https://github.com/您的用户名/AI-PhotoAlbum.git

# 推送时需要输入用户名和密码（或 Personal Access Token）
git push -u myfork feature/album-management
```

## 常见问题

### 1. 推送失败：Permission denied

**原因**：没有配置 SSH 密钥

**解决方案**：
```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "z2644276566@163.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 将公钥添加到 GitHub：
# Settings -> SSH and GPG keys -> New SSH key
```

### 2. 推送失败：Repository not found

**原因**：用户名拼写错误或仓库不存在

**解决方案**：
- 确认您已经 Fork 了仓库
- 检查用户名是否正确

### 3. 使用 HTTPS 推送时需要 Token

**原因**：GitHub 不再支持密码认证

**解决方案**：
1. 访问 GitHub Settings -> Developer settings -> Personal access tokens
2. 生成新的 Token（勾选 `repo` 权限）
3. 推送时使用 Token 作为密码

## 快速命令汇总

```bash
# 1. Fork 仓库后，添加远程仓库
git remote add myfork git@github.com:您的用户名/AI-PhotoAlbum.git

# 2. 推送分支
git push -u myfork feature/album-management

# 3. 验证推送成功
git branch -r
```

## 验证推送成功

推送成功后，您可以：

1. 访问 `https://github.com/您的用户名/AI-PhotoAlbum/tree/feature/album-management`
2. 确认代码已经推送
3. 创建 Pull Request

---

**分支名称**：`feature/album-management`  
**目标仓库**：`https://github.com/您的用户名/AI-PhotoAlbum`  
**PR 目标**：`boneluo/AI-PhotoAlbum` 的 `master` 分支