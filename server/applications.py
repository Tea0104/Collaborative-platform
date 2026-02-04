from flask import Blueprint, jsonify, request

from .auth import login_required, role_required
from .db import (
    apply_for_role,
    cancel_application,
    list_role_applications,
    list_student_applications,
    review_application,
)


applications_bp = Blueprint("applications", __name__)


@applications_bp.route("/api/roles/<int:role_id>/apply", methods=["POST"])
@login_required
@role_required("学生")
def student_apply(role_id: int):
    data = request.json or {}
    motivation = (data.get("motivation") or "").strip()
    student_id = request.current_user["user_id"]
    res = apply_for_role(role_id=role_id, student_id=student_id, motivation=motivation)
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), res["code"]
    return jsonify({"success": True, "message": res["msg"], "application_id": res["data"]["application_id"]}), 201


@applications_bp.route("/api/student/applications", methods=["GET"])
@login_required
@role_required("学生")
def student_list_applications():
    student_id = request.current_user["user_id"]
    rows = list_student_applications(student_id)
    return jsonify({"success": True, "applications": rows})


@applications_bp.route("/api/student/applications/<int:application_id>/cancel", methods=["POST"])
@login_required
@role_required("学生")
def student_cancel_application(application_id: int):
    student_id = request.current_user["user_id"]
    res = cancel_application(application_id, student_id)
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), res["code"]
    return jsonify({"success": True, "message": res["msg"]})


@applications_bp.route("/api/enterprise/roles/<int:role_id>/applications", methods=["GET"])
@login_required
@role_required("企业")
def enterprise_list_role_applications(role_id: int):
    enterprise_id = request.current_user["user_id"]
    res = list_role_applications(role_id, enterprise_id)
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), res["code"]
    return jsonify({"success": True, "applications": res["data"]})


@applications_bp.route("/api/enterprise/applications/<int:application_id>/review", methods=["POST"])
@login_required
@role_required("企业")
def enterprise_review_application(application_id: int):
    enterprise_id = request.current_user["user_id"]
    data = request.json or {}
    decision = (data.get("decision") or "").strip()
    res = review_application(application_id, enterprise_id, decision)
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), res["code"]
    return jsonify({"success": True, "message": res["msg"]})
