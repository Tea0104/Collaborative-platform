from flask import Blueprint, jsonify, request

try:
    from .auth import login_required, role_required
    from .db import (
        admin_set_user_status,
        get_admin_dashboard_data,
        list_all_applications,
        list_all_feedbacks,
        list_all_projects,
        list_all_users,
        project_del,
    )
except ImportError:
    from auth import login_required, role_required
    from db import (
        admin_set_user_status,
        get_admin_dashboard_data,
        list_all_applications,
        list_all_feedbacks,
        list_all_projects,
        list_all_users,
        project_del,
    )


admin_bp = Blueprint("admin", __name__)


def _parse_limit(default: int = 8) -> int:
    limit_raw = (request.args.get("limit") or str(default)).strip()
    try:
        return int(limit_raw)
    except ValueError:
        return default


@admin_bp.route("/api/admin/dashboard", methods=["GET"])
@login_required
@role_required("管理员")
def admin_dashboard():
    res = get_admin_dashboard_data(limit=_parse_limit(8))
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), 500
    return jsonify({"success": True, **res["data"]})


@admin_bp.route("/api/admin/users", methods=["GET"])
@login_required
@role_required("管理员")
def admin_list_users():
    res = list_all_users(limit=_parse_limit(100))
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), 500
    return jsonify({"success": True, "users": res["data"]})


@admin_bp.route("/api/admin/users/<int:user_id>/status", methods=["PUT"])
@login_required
@role_required("管理员")
def admin_update_user_status(user_id: int):
    data = request.json or {}
    if "status" not in data:
        return jsonify({"success": False, "message": "status 不能为空"}), 400

    try:
        status = int(data.get("status"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "status 必须是数字 0 或 1"}), 400

    operator_user_id = request.current_user["user_id"]
    res = admin_set_user_status(user_id, status, operator_user_id)
    code = 200 if res["code"] == 200 else res["code"]
    return jsonify({"success": res["code"] == 200, "message": res["msg"], "data": res.get("data")}), code


@admin_bp.route("/api/admin/projects", methods=["GET"])
@login_required
@role_required("管理员")
def admin_list_projects():
    res = list_all_projects(limit=_parse_limit(100))
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), 500
    return jsonify({"success": True, "projects": res["data"]})


@admin_bp.route("/api/admin/projects/<int:project_id>", methods=["DELETE"])
@login_required
@role_required("管理员")
def admin_delete_project(project_id: int):
    res = project_del(project_id)
    code = 200 if res["code"] == 200 else res["code"]
    return jsonify({"success": res["code"] == 200, "message": res["msg"], "data": res.get("data")}), code


@admin_bp.route("/api/admin/applications", methods=["GET"])
@login_required
@role_required("管理员")
def admin_list_applications():
    res = list_all_applications(limit=_parse_limit(100))
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), 500
    return jsonify({"success": True, "applications": res["data"]})


@admin_bp.route("/api/admin/feedbacks", methods=["GET"])
@login_required
@role_required("管理员")
def admin_list_feedbacks():
    res = list_all_feedbacks(limit=_parse_limit(100))
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), 500
    return jsonify({"success": True, "feedbacks": res["data"]})
