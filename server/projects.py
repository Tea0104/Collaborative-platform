import logging
import re
from datetime import datetime

from flask import Blueprint, jsonify, request

try:
    from .auth import login_required, role_required
    from .db import (
        add_role_feedback,
        get_project,
        get_role,
        get_user,
        list_feedbacks_by_project,
        list_projects_by_publisher,
        list_public_projects,
        list_roles_by_project,
        project_add,
        project_update,
        role_add,
        role_update,
        update_feedback_status,
    )
except ImportError:
    from auth import login_required, role_required
    from db import (
        add_role_feedback,
        get_project,
        get_role,
        get_user,
        list_feedbacks_by_project,
        list_projects_by_publisher,
        list_public_projects,
        list_roles_by_project,
        project_add,
        project_update,
        role_add,
        role_update,
        update_feedback_status,
    )


projects_bp = Blueprint("projects", __name__)

PROJECT_STATUS = {"草稿", "招募中", "进行中", "已完成", "已终止"}
ROLE_STATUS = {"招募中", "进行中", "已完成"}


# ===== 企业侧 =====


@projects_bp.route("/api/enterprise/projects", methods=["GET"])
@login_required
@role_required("企业")
def enterprise_list_projects():
    user_id = request.current_user["user_id"]
    status = (request.args.get("status") or "").strip()
    projects = list_projects_by_publisher(user_id, status or None)
    return jsonify({"success": True, "projects": projects})


@projects_bp.route("/api/enterprise/projects", methods=["POST"])
@login_required
@role_required("企业")
def enterprise_create_project():
    user = request.current_user
    data = request.json or {}
    project_name = (data.get("project_name") or data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    company = (data.get("company") or user.get("school_company") or "").strip()
    project_status = (data.get("project_status") or "招募中").strip()
    deadline = data.get("deadline")
    result_url = (data.get("result_url") or "").strip()
    expected_market = (data.get("expected_market") or "").strip()
    work_mode = (data.get("work_mode") or "").strip()
    participant_count = (data.get("participant_count") or "").strip()

    if not project_name:
        return jsonify({"success": False, "message": "project_name 不能为空"}), 400
    if not company:
        return jsonify({"success": False, "message": "company 不能为空"}), 400
    if project_status not in PROJECT_STATUS:
        return jsonify({"success": False, "message": "project_status 不合法"}), 400

    res = project_add(
        project_name=project_name,
        publisher_id=user["user_id"],
        company=company,
        description=description,
        project_status=project_status,
        deadline=deadline,
        result_url=result_url,
        expected_market=expected_market,
        work_mode=work_mode,
        participant_count=participant_count,
    )
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), 400
    return jsonify({"success": True, "project_id": res["data"]["project_id"]}), 201


@projects_bp.route("/api/enterprise/projects/<int:project_id>", methods=["PUT"])
@login_required
@role_required("企业")
def enterprise_update_project(project_id: int):
    user_id = request.current_user["user_id"]
    data = request.json or {}

    allow_fields = {
        "project_name",
        "description",
        "project_status",
        "deadline",
        "result_url",
        "expected_market",
        "work_mode",
        "participant_count",
        "company",
    }
    update_fields = {k: v for k, v in data.items() if k in allow_fields}
    if not update_fields:
        return jsonify({"success": True, "message": "无可更新字段"})
    if "project_status" in update_fields and update_fields["project_status"] not in PROJECT_STATUS:
        return jsonify({"success": False, "message": "project_status 不合法"}), 400

    proj = get_project(project_id)
    if proj["code"] != 200:
        return jsonify({"success": False, "message": proj["msg"]}), 404
    if proj["data"]["publisher_id"] != user_id:
        return jsonify({"success": False, "message": "项目不存在或无权限"}), 403

    res = project_update(project_id, **update_fields)
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), 400
    return jsonify({"success": True, "message": "更新成功"})


@projects_bp.route("/api/enterprise/projects/<int:project_id>/roles", methods=["GET"])
@login_required
@role_required("企业")
def enterprise_list_roles(project_id: int):
    user_id = request.current_user["user_id"]
    proj = get_project(project_id)
    if proj["code"] != 200:
        return jsonify({"success": False, "message": proj["msg"]}), 404
    if proj["data"]["publisher_id"] != user_id:
        return jsonify({"success": False, "message": "项目不存在或无权限"}), 403

    roles = list_roles_by_project(project_id)
    return jsonify({"success": True, "roles": roles})


@projects_bp.route("/api/enterprise/projects/<int:project_id>/roles", methods=["POST"])
@login_required
@role_required("企业")
def enterprise_create_role(project_id: int):
    user_id = request.current_user["user_id"]
    data = request.json or {}
    role_name = (data.get("role_name") or data.get("name") or "").strip()
    task_desc = (data.get("task_desc") or data.get("description") or "").strip()
    skill_require = (data.get("skill_require") or data.get("required_skills") or "").strip()
    limit_num = data.get("limit_num", data.get("capacity", 1))
    role_status = (data.get("role_status") or "招募中").strip()
    task_deadline = data.get("task_deadline")

    if not role_name:
        return jsonify({"success": False, "message": "role_name 不能为空"}), 400
    if not task_desc:
        return jsonify({"success": False, "message": "task_desc 不能为空"}), 400
    try:
        limit_num = int(limit_num)
    except Exception:
        return jsonify({"success": False, "message": "limit_num 必须是整数"}), 400
    if limit_num <= 0:
        return jsonify({"success": False, "message": "limit_num 必须大于 0"}), 400
    if role_status not in ROLE_STATUS:
        return jsonify({"success": False, "message": "role_status 不合法"}), 400

    proj = get_project(project_id)
    if proj["code"] != 200:
        return jsonify({"success": False, "message": proj["msg"]}), 404
    if proj["data"]["publisher_id"] != user_id:
        return jsonify({"success": False, "message": "项目不存在或无权限"}), 403

    res = role_add(
        project_id=project_id,
        role_name=role_name,
        task_desc=task_desc,
        skill_require=skill_require,
        limit_num=limit_num,
        join_num=0,
        role_status=role_status,
        task_deadline=task_deadline,
    )
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), 400
    return jsonify({"success": True, "role_id": res["data"]["role_id"]}), 201


@projects_bp.route("/api/enterprise/roles/<int:role_id>", methods=["PUT"])
@login_required
@role_required("企业")
def enterprise_update_role(role_id: int):
    user_id = request.current_user["user_id"]
    data = request.json or {}

    allow_fields = {"role_name", "task_desc", "skill_require", "limit_num", "join_num", "role_status", "task_deadline"}
    update_fields = {k: v for k, v in data.items() if k in allow_fields}
    if not update_fields:
        return jsonify({"success": True, "message": "无可更新字段"})

    if "role_status" in update_fields and update_fields["role_status"] not in ROLE_STATUS:
        return jsonify({"success": False, "message": "role_status 不合法"}), 400
    if "limit_num" in update_fields:
        try:
            update_fields["limit_num"] = int(update_fields["limit_num"])
        except Exception:
            return jsonify({"success": False, "message": "limit_num 必须是整数"}), 400
        if update_fields["limit_num"] <= 0:
            return jsonify({"success": False, "message": "limit_num 必须大于 0"}), 400
    if "join_num" in update_fields and "limit_num" in update_fields:
        if int(update_fields["join_num"]) > int(update_fields["limit_num"]):
            return jsonify({"success": False, "message": "join_num 不能超过 limit_num"}), 400

    sets = []
    params = []
    for k, v in update_fields.items():
        sets.append(f"{k} = ?")
        params.append(v)
    params.append(role_id)

    role_res = get_role(role_id)
    if role_res["code"] != 200:
        return jsonify({"success": False, "message": role_res["msg"]}), 404
    proj = get_project(role_res["data"]["project_id"])
    if proj["code"] != 200 or proj["data"]["publisher_id"] != user_id:
        return jsonify({"success": False, "message": "角色不存在或无权限"}), 403

    res = role_update(role_id, **update_fields)
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), 400
    return jsonify({"success": True, "message": "更新成功"})


# ===== 公共侧 =====


@projects_bp.route("/api/projects", methods=["GET"])
def public_list_projects():
    q = (request.args.get("q") or "").strip()
    projects = list_public_projects(q)
    return jsonify({"success": True, "projects": projects})


@projects_bp.route("/api/projects/<int:project_id>", methods=["GET"])
def public_project_detail(project_id: int):
    proj = get_project(project_id)
    if proj["code"] != 200:
        return jsonify({"success": False, "message": proj["msg"]}), 404
    publisher = get_user(proj["data"]["publisher_id"])
    publisher_name = publisher["data"]["real_name"] if publisher["code"] == 200 else ""
    project = dict(proj["data"])
    project["publisher_name"] = publisher_name
    roles = list_roles_by_project(project_id)
    return jsonify({"success": True, "project": project, "roles": roles})


@projects_bp.route("/api/roles/<int:role_id>/feedbacks", methods=["POST"])
@login_required
def submit_role_feedback(role_id: int):
    data = request.json or {}
    content = (data.get("content") or "").strip()
    evidence_url = (data.get("evidence_url") or "").strip()
    user_id = request.current_user["user_id"]

    if not content:
        return jsonify({"code": 400, "msg": "content is required"}), 400

    res = add_role_feedback(role_id=role_id, user_id=user_id, content=content, evidence_url=evidence_url)
    if res["code"] != 200:
        return jsonify({"code": res["code"], "msg": res["msg"]}), res["code"]
    return jsonify({"code": 200, "msg": "successfully submitted"})


@projects_bp.route("/api/projects/<int:project_id>/feedbacks", methods=["GET"])
def list_project_feedbacks(project_id: int):
    status = (request.args.get("status") or "").strip()
    feedbacks = list_feedbacks_by_project(project_id, status or None)
    return jsonify({"success": True, "feedbacks": feedbacks})


@projects_bp.route("/api/feedbacks/<int:feedback_id>/status", methods=["PUT"])
@login_required
def set_feedback_status(feedback_id: int):
    data = request.json or {}
    status = (data.get("status") or "").strip()
    if not status:
        return jsonify({"code": 400, "msg": "status is required"}), 400

    user_id = request.current_user["user_id"]
    res = update_feedback_status(feedback_id=feedback_id, status=status, operator_user_id=user_id)
    if res["code"] != 200:
        return jsonify({"code": res["code"], "msg": res["msg"]}), res["code"]
    return jsonify({"code": 200, "msg": "updated"})


ACTION_VERBS = (
    "实现",
    "搭建",
    "联调",
    "测试",
    "上线",
    "优化",
    "设计",
    "开发",
    "部署",
    "implement",
    "build",
    "integrate",
    "test",
    "deploy",
)


def _normalize_role_name(name: str) -> str:
    return re.sub(r"\s+", "", str(name or "")).strip()


def _coerce_limit_num(value) -> int:
    try:
        n = int(value)
    except Exception:
        n = 1
    return max(1, min(3, n))


def _parse_datetime(value: str):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00").replace(" ", "T"))
    except Exception:
        return None


def _sanitize_task_desc(task_desc: str, role_name: str) -> str:
    text = str(task_desc or "").strip()
    hit_count = sum(1 for verb in ACTION_VERBS if verb.lower() in text.lower())
    if len(text) < 12 or hit_count < 2:
        return f"负责{role_name}相关模块的实现与联调，完成测试并支持上线交付。"
    return text


def _sanitize_task_deadline(task_deadline: str, project_deadline: str) -> str:
    project_dt = _parse_datetime(project_deadline)
    role_dt = _parse_datetime(task_deadline)
    if project_dt is None:
        return str(task_deadline or "").strip()
    if role_dt is None or role_dt > project_dt:
        return str(project_deadline or "").strip()
    return str(task_deadline or "").strip()


def _generate_stub_roles(description: str, project_deadline: str = "") -> list[dict]:
    desc = (description or "").strip().lower()
    roles: list[dict] = []

    def add_role(role_name: str, task_desc: str, skill_require: str, limit_num: int):
        roles.append(
            {
                "role_name": role_name,
                "task_desc": task_desc,
                "skill_require": skill_require,
                "limit_num": limit_num,
                "task_deadline": project_deadline or "",
            }
        )

    if any(k in desc for k in ("前端", "网页", "小程序", "frontend", "web")):
        add_role(
            "前端开发",
            "负责页面实现与接口联调，完成兼容性测试并推动上线。",
            "HTML/CSS/JavaScript, API联调",
            2,
        )
    if any(k in desc for k in ("接口", "数据库", "后端", "backend", "api", "db")):
        add_role(
            "后端开发",
            "负责接口实现与数据库搭建，联调测试后支持上线发布。",
            "Python/Flask, SQL, RESTful API",
            1,
        )
    if any(k in desc for k in ("推广", "运营", "用户", "增长", "operation", "community")):
        add_role(
            "运营支持",
            "负责用户触达与运营执行，跟踪数据并测试转化策略。",
            "运营策划, 用户沟通, 数据分析",
            1,
        )

    # Keep a minimum default role set for demonstration.
    add_role("产品经理", "负责需求梳理与方案设计，组织联调测试并推进上线。", "需求分析, 原型设计, 项目协作", 1)
    add_role("前端开发", "负责页面实现与接口联调，完成兼容性测试并推动上线。", "HTML/CSS/JavaScript, API联调", 2)
    add_role("后端开发", "负责接口实现与数据库搭建，联调测试后支持上线发布。", "Python/Flask, SQL, RESTful API", 1)
    return roles


def _clean_roles_for_persist(raw_roles: list[dict], project_deadline: str, existing_names: set[str]) -> list[dict]:
    taken = {_normalize_role_name(name).lower() for name in existing_names if name}
    cleaned: list[dict] = []

    for item in raw_roles or []:
        base_name = _normalize_role_name(item.get("role_name") or "角色")
        if not base_name:
            base_name = "角色"

        candidate = base_name
        seq = 2
        while _normalize_role_name(candidate).lower() in taken:
            candidate = f"{base_name}_{seq}"
            seq += 1
        taken.add(_normalize_role_name(candidate).lower())

        cleaned.append(
            {
                "role_name": candidate,
                "task_desc": _sanitize_task_desc(item.get("task_desc"), candidate),
                "skill_require": str(item.get("skill_require") or "通用协作与岗位基础技能").strip(),
                "limit_num": _coerce_limit_num(item.get("limit_num", 1)),
                "task_deadline": _sanitize_task_deadline(item.get("task_deadline", ""), project_deadline),
            }
        )
    return cleaned


def _self_check_ai_suggest_cleaning():
    """Unit-level self-check example: run manually in Flask shell."""
    sample = [
        {"role_name": " 前端 开发 ", "task_desc": "做页面", "limit_num": 9, "task_deadline": "2099-01-01"},
        {"role_name": "前端开发", "task_desc": "实现并测试接口页面", "limit_num": 0, "task_deadline": ""},
    ]
    cleaned = _clean_roles_for_persist(sample, "2026-12-31", {"产品经理"})
    logging.info("ai-suggest self-check input=%s", sample)
    logging.info("ai-suggest self-check output=%s", cleaned)
    return cleaned


@projects_bp.route("/api/projects/<int:project_id>/roles/ai-suggest", methods=["POST"])
def ai_suggest_project_roles(project_id: int):
    proj = get_project(project_id)
    if proj["code"] != 200:
        return jsonify({"code": 404, "msg": "project not found", "data": None}), 404

    project = proj["data"] or {}
    payload = request.get_json(silent=True) or {}

    project_name = (payload.get("project_name") or project.get("project_name") or "").strip()
    description = (payload.get("description") or project.get("description") or "").strip()
    deadline = (payload.get("deadline") or project.get("deadline") or "").strip()

    raw_roles = _generate_stub_roles(description=description, project_deadline=deadline)
    existing_names = {_normalize_role_name(row.get("role_name", "")) for row in list_roles_by_project(project_id)}
    roles = _clean_roles_for_persist(raw_roles, deadline, existing_names)

    logging.info(
        "ai-suggest project_id=%s project=%s raw_count=%s cleaned_count=%s",
        project_id,
        project_name or "",
        len(raw_roles),
        len(roles),
    )

    assumptions = [
        f"当前建议基于项目《{project_name or '未命名项目'}》描述自动生成。",
        "当前结果为规则 stub，建议人工确认后再保存为正式角色。",
    ]
    return jsonify({"code": 200, "msg": "success", "data": {"roles": roles, "assumptions": assumptions}})
