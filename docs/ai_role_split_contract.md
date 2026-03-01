# AI 职责划分接口 JSON 契约（仅定义，不实现 LLM）

## 接口
- `POST /api/ai/role-split`
- `Content-Type: application/json`

## 请求 JSON 契约
```json
{
  "project_name": "string, required, 1~100",
  "description": "string, required, 20~5000",
  "deadline": "string, optional, ISO8601 datetime/date",
  "work_mode": "string, optional, 远程协作/线下协作/混合协作",
  "expected_market": "string, optional, 1~200",
  "participant_count": "string, optional, e.g. 3-5人",
  "language": "string, optional, default zh-CN",
  "max_roles": "integer, optional, default 3, range 1~5"
}
```

## 响应 JSON 契约
```json
{
  "success": true,
  "code": 200,
  "message": "ok",
  "data": {
    "roles": [
      {
        "role_name": "string, required, unique in roles[]",
        "task_desc": "string, required, 10~500",
        "skill_require": "string, required, 2~300",
        "limit_num": "integer, required, 1~3",
        "task_deadline": "string, optional, ISO8601 datetime/date, <= project deadline if provided"
      }
    ],
    "assumptions": [
      "string"
    ],
    "questions_to_confirm": [
      "string"
    ]
  }
}
```

## 字段约束
1. `project_name` 必填，去首尾空格后不能为空。
2. `description` 必填，建议最少 20 字。
3. `roles` 至少 1 项，最多 `max_roles` 项。
4. `role_name` 在同一次响应内必须唯一（大小写不敏感去重）。
5. `limit_num` 必须为整数，范围 `1~3`。
6. `task_deadline` 若提供，不能晚于项目 `deadline`（若请求中有）。
7. `assumptions`、`questions_to_confirm` 可为空数组，但字段应始终返回。
8. 输入信息不足时，应通过 `questions_to_confirm` 给出澄清问题。

## 示例请求 JSON
```json
{
  "project_name": "校园二手交易平台",
  "description": "开发一个面向高校学生的二手交易平台，支持发布闲置、搜索、私信沟通、订单状态跟踪，并提供基础风控与举报功能。",
  "deadline": "2026-06-30",
  "work_mode": "混合协作",
  "expected_market": "高校校园市场",
  "participant_count": "4-6人",
  "language": "zh-CN",
  "max_roles": 3
}
```

## 示例响应 JSON
```json
{
  "success": true,
  "code": 200,
  "message": "ok",
  "data": {
    "roles": [
      {
        "role_name": "后端开发",
        "task_desc": "负责用户、商品、订单、私信与举报模块的 API 设计与实现，完成权限校验与日志记录。",
        "skill_require": "Python, Flask, SQLite/MySQL, RESTful API, 鉴权",
        "limit_num": 1,
        "task_deadline": "2026-06-10"
      },
      {
        "role_name": "前端开发",
        "task_desc": "负责项目核心页面开发（列表、详情、发布、个人中心），完成接口联调与基础交互体验优化。",
        "skill_require": "HTML, CSS, JavaScript, Fetch API, 前端调试",
        "limit_num": 2,
        "task_deadline": "2026-06-20"
      },
      {
        "role_name": "测试与运营支持",
        "task_desc": "负责测试用例设计、功能回归、异常场景验证，并协助整理上线文档与用户反馈。",
        "skill_require": "功能测试, 缺陷跟踪, 文档整理, 沟通协作",
        "limit_num": 1,
        "task_deadline": "2026-06-25"
      }
    ],
    "assumptions": [
      "默认项目采用 Web 形态交付，不包含原生 App 开发。",
      "默认团队已有基础 UI 设计稿或可接受简化视觉方案。"
    ],
    "questions_to_confirm": [
      "是否需要接入第三方支付？",
      "是否需要实名认证或校园身份校验？"
    ]
  }
}
```
