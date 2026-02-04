# 接口说明文档（前端联调版）
 
> Base URL：`http://127.0.0.1:5000`

## 通用规则
- 需要登录的接口：在 Header 中携带  
  `Authorization: Bearer <token>`
- 所有请求/响应均为 JSON
- 常见状态码  
  `200` 成功  
  `201` 创建成功  
  `400` 参数错误  
  `401` 未登录  
  `403` 权限不足  
  `404` 资源不存在

---

## 1. 认证模块

### 注册
`POST /api/auth/register`

请求体：
```json
{
  "username": "student1",
  "password": "123456",
  "user_type": "学生",
  "real_name": "张三",
  "school_company": "XX大学计算机学院",
  "skill_tags": "Python,Flask",
  "contact": "13800000001"
}
```

响应：
```json
{ "success": true, "message": "注册成功", "user_id": 1, "user_type": "学生" }
```

### 登录
`POST /api/auth/login`

请求体：
```json
{ "username": "student1", "password": "123456" }
```

响应：
```json
{ "success": true, "message": "登录成功", "user_id": 1, "user_type": "学生", "token": "..." }
```

### 当前用户
`GET /api/auth/profile`

---

## 2. 公共接口（无需登录）

### 项目列表
`GET /api/projects`

可选参数：
`q` 关键词（项目名/描述/公司）

响应字段（列表项）：
`project_id` `project_name` `description` `project_status` `publish_time` `deadline` `company`

### 项目详情（含角色）
`GET /api/projects/{project_id}`

响应字段：
`project` + `roles`

---

## 3. 企业端接口

### 企业项目列表
`GET /api/enterprise/projects`

可选参数：
`status`（草稿/招募中/进行中/已完成/已终止）

### 创建项目
`POST /api/enterprise/projects`

请求体：
```json
{
  "project_name": "调试项目A",
  "description": "用于接口联调",
  "company": "某科技有限公司",
  "project_status": "招募中",
  "deadline": "2026-06-30 23:59:59"
}
```

### 更新项目
`PUT /api/enterprise/projects/{project_id}`

可更新字段：
`project_name` `description` `project_status` `deadline` `result_url` `company`

### 项目角色列表
`GET /api/enterprise/projects/{project_id}/roles`

### 创建角色
`POST /api/enterprise/projects/{project_id}/roles`

请求体：
```json
{
  "role_name": "后端开发",
  "task_desc": "接口开发",
  "skill_require": "Python,Flask,SQLite",
  "limit_num": 2,
  "role_status": "招募中",
  "task_deadline": "2026-04-30"
}
```

### 更新角色
`PUT /api/enterprise/roles/{role_id}`

可更新字段：
`role_name` `task_desc` `skill_require` `limit_num` `join_num` `role_status` `task_deadline`

---

## 4. 学生端接口

### 申请角色
`POST /api/roles/{role_id}/apply`

请求体：
```json
{ "motivation": "我对该项目很感兴趣..." }
```

### 我的申请列表
`GET /api/student/applications`

### 撤回申请
`POST /api/student/applications/{application_id}/cancel`

---

## 5. 企业审核接口

### 角色申请列表
`GET /api/enterprise/roles/{role_id}/applications`

### 审核申请
`POST /api/enterprise/applications/{application_id}/review`

请求体：
```json
{ "decision": "accepted" }
```
`decision` 只能是 `accepted` 或 `rejected`
