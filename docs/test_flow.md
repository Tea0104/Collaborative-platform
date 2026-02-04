# 测试流程（Postman）

> 目标：覆盖注册/登录、企业发布项目、角色拆分、项目查询、角色申请与审核。

## 0. 启动服务
```
python -m server
```
默认地址：`http://127.0.0.1:5000`

---

## 1. 登录（企业）
**接口**：`POST /api/auth/login`  
**Body (JSON)**：
```json
{ "username": "company1", "password": "123456" }
```
**记录**：返回的 `token`，后续企业请求头带：
```
Authorization: Bearer <enterprise_token>
```

---

## 2. 登录（学生）
**接口**：`POST /api/auth/login`  
**Body (JSON)**：
```json
{ "username": "student1", "password": "123456" }
```
**记录**：返回的 `token`，后续学生请求头带：
```
Authorization: Bearer <student_token>
```

---

## 3. 企业创建项目
**接口**：`POST /api/enterprise/projects`  
**Headers**：`Authorization: Bearer <enterprise_token>`  
**Body (JSON)**：
```json
{
  "project_name": "调试项目A",
  "description": "用于接口联调",
  "company": "某科技有限公司",
  "project_status": "招募中",
  "deadline": "2026-06-30 23:59:59"
}
```
**记录**：返回的 `project_id`

---

## 4. 企业为项目创建角色
**接口**：`POST /api/enterprise/projects/{project_id}/roles`  
**Headers**：`Authorization: Bearer <enterprise_token>`  
**Body (JSON)**：
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
**记录**：返回的 `role_id`

---

## 5. 公共项目列表（学生查看）
**接口**：`GET /api/projects`  
可选 `q` 参数模糊搜索

---

## 6. 学生申请角色
**接口**：`POST /api/roles/{role_id}/apply`  
**Headers**：`Authorization: Bearer <student_token>`  
**Body (JSON)**：
```json
{ "motivation": "我对该项目很感兴趣，且具备相关技能。" }
```
**记录**：返回的 `application_id`

---

## 7. 企业查看该角色申请
**接口**：`GET /api/enterprise/roles/{role_id}/applications`  
**Headers**：`Authorization: Bearer <enterprise_token>`

---

## 8. 企业审核申请（录取/拒绝）
**接口**：`POST /api/enterprise/applications/{application_id}/review`  
**Headers**：`Authorization: Bearer <enterprise_token>`  
**Body (JSON)**：
```json
{ "decision": "accepted" }
```
或
```json
{ "decision": "rejected" }
```

---

## 9. 学生查看自己的申请
**接口**：`GET /api/student/applications`  
**Headers**：`Authorization: Bearer <student_token>`

---

## 10. 学生撤回申请（仅 pending 可撤回）
**接口**：`POST /api/student/applications/{application_id}/cancel`  
**Headers**：`Authorization: Bearer <student_token>`

---

## 常见问题排查
- `401`：token 缺失或无效  
- `403`：身份不匹配  
- `400`：字段缺失/状态不合法/名额已满  
- `404`：资源不存在或无权限
