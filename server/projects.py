import json
import logging
import os
import re
import uuid
from datetime import datetime
from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

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

DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions").strip()
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
DEEPSEEK_TIMEOUT = float(os.environ.get("DEEPSEEK_TIMEOUT", "15").strip() or "15")
FEEDBACK_UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "uploads", "feedbacks"))
MAX_FEEDBACK_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_FEEDBACK_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".zip",
    ".rar",
    ".7z",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".txt",
    ".md",
}


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
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        data = request.form or {}
        upload_file = request.files.get("evidence_file")
    else:
        data = request.json or {}
        upload_file = None

    content = (data.get("content") or "").strip()
    evidence_url = (data.get("evidence_url") or "").strip()
    user_id = request.current_user["user_id"]

    if not content:
        return jsonify({"code": 400, "msg": "content is required"}), 400

    if upload_file and upload_file.filename:
        try:
            evidence_url = _save_feedback_file(upload_file)
        except ValueError as exc:
            return jsonify({"code": 400, "msg": str(exc)}), 400

    res = add_role_feedback(role_id=role_id, user_id=user_id, content=content, evidence_url=evidence_url)
    if res["code"] != 200:
        return jsonify({"code": res["code"], "msg": res["msg"]}), res["code"]
    return jsonify({"code": 200, "msg": "successfully submitted", "evidence_url": evidence_url})


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


def _normalize_role_name(name: str) -> str:
    return re.sub(r"\s+", "", str(name or "")).strip()


def _allowed_feedback_file(filename: str) -> bool:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext in ALLOWED_FEEDBACK_EXTENSIONS


def _save_feedback_file(file_storage) -> str:
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("uploaded file is empty")
    if not _allowed_feedback_file(filename):
        raise ValueError("unsupported file type")

    os.makedirs(FEEDBACK_UPLOAD_DIR, exist_ok=True)
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > MAX_FEEDBACK_FILE_SIZE:
        raise ValueError("file is too large, max 20MB")

    ext = os.path.splitext(filename)[1].lower()
    saved_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:10]}{ext}"
    save_path = os.path.join(FEEDBACK_UPLOAD_DIR, saved_name)
    file_storage.save(save_path)
    return f"/uploads/feedbacks/{saved_name}"


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
        return f"负责{role_name}相关模块的实现、联调与测试，保证功能按时交付。"
    return text


def _sanitize_task_deadline(task_deadline: str, project_deadline: str) -> str:
    project_dt = _parse_datetime(project_deadline)
    role_dt = _parse_datetime(task_deadline)
    if project_dt is None:
        return str(task_deadline or "").strip()
    if role_dt is None or role_dt > project_dt:
        return str(project_deadline or "").strip()
    return str(task_deadline or "").strip()


def _sanitize_text_field(value, fallback: str = "", max_len: int = 500) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    if len(text) > max_len:
        return text[:max_len].strip()
    return text


def _extract_json_object(text: str) -> dict:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("empty model content")

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.S)
    if fenced_match:
        raw = fenced_match.group(1).strip()
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]

    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("model output is not a JSON object")
    return parsed


def _build_ai_contract_payload(project: dict, payload: dict) -> dict:
    project_name = (payload.get("project_name") or project.get("project_name") or "").strip()
    description = (payload.get("description") or project.get("description") or "").strip()
    deadline = (payload.get("deadline") or project.get("deadline") or "").strip()
    work_mode = (payload.get("work_mode") or project.get("work_mode") or "").strip()
    expected_market = (payload.get("expected_market") or project.get("expected_market") or "").strip()
    participant_count = (payload.get("participant_count") or project.get("participant_count") or "").strip()
    max_roles = payload.get("max_roles", 4)

    try:
        max_roles = int(max_roles)
    except Exception:
        max_roles = 4

    return {
        "project_name": project_name,
        "description": description,
        "deadline": deadline,
        "work_mode": work_mode,
        "expected_market": expected_market,
        "participant_count": participant_count,
        "language": "zh-CN",
        "max_roles": max(1, min(5, max_roles)),
    }


def _call_deepseek_role_suggest(contract_payload: dict) -> dict:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    system_prompt = (
        "You are a project staffing assistant. "
        "Return only valid JSON. "
        "Generate practical roles for an enterprise-student collaboration project."
    )
    user_prompt = (
        "Return a JSON object with keys roles, assumptions, questions_to_confirm.\n"
        "roles must be a non-empty array.\n"
        "Each role must contain role_name, task_desc, skill_require, limit_num, task_deadline.\n"
        "role_name must be unique.\n"
        "limit_num must be an integer between 1 and 3.\n"
        "task_deadline must not be later than the project deadline when a deadline exists.\n"
        "Keep the content concise and practical.\n"
        f"Input JSON:\n{json.dumps(contract_payload, ensure_ascii=False)}"
    )
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.5,
        "stream": False,
    }

    req = urllib_request.Request(
        DEEPSEEK_API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=DEEPSEEK_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek HTTP {exc.code}: {detail[:300]}") from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(f"DeepSeek request failed: {exc.reason}") from exc

    parsed = json.loads(raw)
    choices = parsed.get("choices") or []
    message = choices[0].get("message") if choices else {}
    result = _extract_json_object((message or {}).get("content") or "")
    if not isinstance(result.get("roles"), list) or not result.get("roles"):
        raise ValueError("DeepSeek returned empty roles")
    return result


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
        add_role("前端开发", "负责页面实现、接口联调和基础交互优化。", "HTML/CSS/JavaScript, API联调", 2)
    if any(k in desc for k in ("接口", "数据库", "后端", "backend", "api", "db")):
        add_role("后端开发", "负责接口实现、数据库设计及联调测试。", "Python/Flask, SQL, RESTful API", 1)
    if any(k in desc for k in ("推广", "运营", "用户", "增长", "operation", "community")):
        add_role("运营支持", "负责用户触达、反馈收集和基础运营执行。", "运营策划, 用户沟通, 数据分析", 1)

    add_role("产品经理", "负责需求梳理、方案设计和项目推进。", "需求分析, 原型设计, 项目协作", 1)
    add_role("前端开发", "负责页面实现、接口联调和基础交互优化。", "HTML/CSS/JavaScript, API联调", 2)
    add_role("后端开发", "负责接口实现、数据库设计及联调测试。", "Python/Flask, SQL, RESTful API", 1)
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
                "skill_require": _sanitize_text_field(item.get("skill_require"), "通用协作与岗位基础技能", 300),
                "limit_num": _coerce_limit_num(item.get("limit_num", 1)),
                "task_deadline": _sanitize_task_deadline(item.get("task_deadline", ""), project_deadline),
            }
        )
    return cleaned


def _normalize_questions(items) -> list[str]:
    values: list[str] = []
    for item in items or []:
        text = _sanitize_text_field(item, "", 120)
        if text:
            values.append(text)
    return values[:5]


def _generate_role_suggestions(project: dict, payload: dict, existing_names: set[str]) -> dict:
    contract_payload = _build_ai_contract_payload(project, payload)
    deadline = contract_payload["deadline"]
    project_name = contract_payload["project_name"]
    description = contract_payload["description"]
    fallback_roles = _clean_roles_for_persist(
        _generate_stub_roles(description=description, project_deadline=deadline),
        deadline,
        existing_names,
    )

    try:
        llm_result = _call_deepseek_role_suggest(contract_payload)
        roles = _clean_roles_for_persist(llm_result.get("roles") or [], deadline, existing_names)
        if not roles:
            raise ValueError("cleaned roles are empty")
        return {
            "roles": roles,
            "assumptions": _normalize_questions(llm_result.get("assumptions"))
            or [f"建议基于项目“{project_name or '未命名项目'}”生成。"],
            "questions_to_confirm": _normalize_questions(llm_result.get("questions_to_confirm")),
            "provider": "deepseek",
            "fallback_used": False,
            "message": "success",
        }
    except Exception as exc:
        logging.warning("ai-suggest fallback: %s", exc)
        return {
            "roles": fallback_roles,
            "assumptions": [
                f"建议基于项目“{project_name or '未命名项目'}”生成。",
                "DeepSeek 调用失败，已回退为本地 stub 建议。",
            ],
            "questions_to_confirm": ["请在保存前检查岗位名称、职责、技能与人数是否合理。"],
            "provider": "stub",
            "fallback_used": True,
            "message": str(exc),
        }


@projects_bp.route("/api/projects/<int:project_id>/roles/ai-suggest", methods=["POST"])
@login_required
@role_required("企业")
def ai_suggest_project_roles(project_id: int):
    proj = get_project(project_id)
    if proj["code"] != 200:
        return jsonify({"code": 404, "msg": "project not found", "data": None}), 404

    project = proj["data"] or {}
    if project.get("publisher_id") != request.current_user["user_id"]:
        return jsonify({"code": 403, "msg": "forbidden", "data": None}), 403

    payload = request.get_json(silent=True) or {}
    existing_names = {_normalize_role_name(row.get("role_name", "")) for row in list_roles_by_project(project_id)}
    result = _generate_role_suggestions(project, payload, existing_names)

    logging.info(
        "ai-suggest project_id=%s provider=%s fallback=%s role_count=%s",
        project_id,
        result["provider"],
        result["fallback_used"],
        len(result["roles"]),
    )
    return jsonify({"code": 200, "msg": result["message"], "data": result})
