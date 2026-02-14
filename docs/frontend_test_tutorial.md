# 前端联调测试教程

## 1. 测试目标
- 首页统一使用 `index.html`（业务首页）。
- 使用 `index.html/login.html/register.html/project_list.html/project_detail.html` 作为业务页面进行联调。
- 登录态与退出逻辑统一：`auth_token`、`token`、`username`、`user_type`、`user`。

## 2. 启动后端
1. 进入项目根目录：`c:\Users\Tea\Desktop\my-backend`
2. 启动服务（按你的项目方式）：
   - 常见方式：`python -m server`
3. 确认接口可访问：`http://127.0.0.1:5000/api/projects`

## 3. 页面入口说明
- 业务首页：`frontend/index.html`
- 注册页：`frontend/register.html`
- 登录页：`frontend/login.html`
- 项目列表页：`frontend/project_list.html`
- 项目详情页：`frontend/project_detail.html?id=<项目ID>`

## 4. 业务链路测试
### 4.1 注册
1. 打开 `register.html`
2. 填写：用户名、密码、用户类型、真实姓名、学校/单位
3. 点击注册
4. 预期：提示注册成功，并跳转 `login.html`

### 4.2 登录
1. 打开 `login.html`
2. 输入账号密码登录
3. 预期：
   - 提示登录成功
   - 跳转 `index.html`
   - `localStorage` 中出现：
     - `auth_token`
     - `token`
     - `username`
     - `user_type`
     - `user`

### 4.3 首页登录态
1. 打开 `index.html`
2. 预期：右上角显示用户信息和“退出”按钮
3. 点击退出
4. 预期：
   - 调用 `/api/auth/logout`
   - 清空上述登录键
   - 留在/跳回 `index.html`

### 4.4 项目列表
1. 打开 `project_list.html`
2. 预期：
   - 可加载项目列表（`GET /api/projects`）
   - 关键词筛选生效
3. 点击任一“查看详情”
4. 预期：跳转 `project_detail.html?id=...`

### 4.5 项目详情与申请（学生账号）
1. 打开 `project_detail.html?id=<有效ID>`
2. 预期：
   - 加载项目详情（`GET /api/projects/{id}`）
   - 加载我的申请（`GET /api/student/applications`，学生且已登录时）
3. 点击“申请加入”
4. 预期：调用 `POST /api/roles/{role_id}/apply` 成功后刷新状态
5. 点击“取消申请”
6. 预期：调用 `POST /api/student/applications/{application_id}/cancel` 成功

### 4.6 详情页退出
1. 在 `project_detail.html` 顶部点击“退出”
2. 预期：
   - 调用 `/api/auth/logout`
   - 清空统一登录键
   - 跳转 `login.html`

## 5. 常见问题排查
- 问题：页面提示网络错误
  - 检查后端是否启动、`api_base` 是否是 `http://127.0.0.1:5000`
- 问题：已登录但页面显示未登录
  - 检查 `localStorage` 是否有 `auth_token` 或 `token`
  - 用浏览器 Network 看 `/api/auth/profile` 是否 401
- 问题：申请按钮灰掉
  - 可能不是学生账号
  - 角色已满员或非招募状态
  - 已提交过申请

## 6. 建议回归清单
- 注册成功后登录
- 退出后重新登录
- 列表页跳详情页
- 详情页申请与撤销
- 详情页退出


