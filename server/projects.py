from flask import Blueprint, jsonify, request

from .auth import login_required, role_required
from .db import (
    get_project,
    get_role,
    get_user,
    list_projects_by_publisher,
    list_public_projects,
    list_roles_by_project,
    project_add,
    project_update,
    role_add,
    role_update,
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

    allow_fields = {"project_name", "description", "project_status", "deadline", "result_url", "company"}
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
