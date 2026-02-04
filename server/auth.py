import secrets
from datetime import datetime
from functools import wraps
from typing import Callable, Optional

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from .db import (
    get_user_by_token,
    get_user_by_username,
    save_token,
    delete_token,
    user_add,
    user_update,
)


auth_bp = Blueprint("auth", __name__)

USER_TYPES = {"学生", "企业"}


def _get_bearer_token() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts[0].strip(), parts[1].strip()
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def login_required(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _get_bearer_token()
        if not token:
            return jsonify({"success": False, "message": "未登录：缺少 Authorization Bearer token"}), 401

        user = get_user_by_token(token)
        if not user:
            return jsonify({"success": False, "message": "未登录：token 无效或已过期"}), 401
        request.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def role_required(required_user_type: str):
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = getattr(request, "current_user", None)
            if not user:
                return jsonify({"success": False, "message": "未登录"}), 401
            if user.get("user_type") != required_user_type:
                return jsonify({"success": False, "message": f"无权限：需要{required_user_type}身份"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


@auth_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.json or {}
    username = (data.get("username") or data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    user_type = (data.get("user_type") or "").strip()
    real_name = (data.get("real_name") or "").strip()
    school_company = (data.get("school_company") or "").strip()
    skill_tags = (data.get("skill_tags") or "").strip()
    contact = (data.get("contact") or "").strip()

    if not username:
        return jsonify({"success": False, "message": "username 不能为空"}), 400
    if len(username) < 3:
        return jsonify({"success": False, "message": "username 长度至少 3 位"}), 400
    if not password or len(password) < 6:
        return jsonify({"success": False, "message": "password 长度至少 6 位"}), 400
    if user_type not in USER_TYPES:
        return jsonify({"success": False, "message": "user_type 仅支持：学生/企业"}), 400
    if not real_name:
        return jsonify({"success": False, "message": "real_name 不能为空"}), 400
    if not school_company:
        return jsonify({"success": False, "message": "school_company 不能为空"}), 400

    password_hash = generate_password_hash(password)

    res = user_add(
        username=username,
        password_hash=password_hash,
        user_type=user_type,
        real_name=real_name,
        school_company=school_company,
        skill_tags=skill_tags,
        contact=contact,
        status=1,
    )
    if res["code"] != 200:
        return jsonify({"success": False, "message": res["msg"]}), 400
    user_id = res["data"]["user_id"]

    return jsonify(
        {
            "success": True,
            "message": "注册成功",
            "user_id": user_id,
            "user_type": user_type,
        }
    ), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json or {}
    username = (data.get("username") or data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "username 和 password 不能为空"}), 400

    user = get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "账号或密码错误"}), 401
    if user["status"] != 1:
        return jsonify({"success": False, "message": "账号已被禁用"}), 403

    token = secrets.token_urlsafe(32)
    save_token(token, user["user_id"])
    user_update(user["user_id"], last_login=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return jsonify(
        {
            "success": True,
            "message": "登录成功",
            "user_id": user["user_id"],
            "user_type": user["user_type"],
            "token": token,
        }
    )


@auth_bp.route("/api/auth/logout", methods=["POST"])
def api_logout():
    token = _get_bearer_token()
    if not token:
        return jsonify({"success": True, "message": "已退出（无 token）"})

    delete_token(token)
    return jsonify({"success": True, "message": "退出成功"})


@auth_bp.route("/api/auth/profile", methods=["GET"])
@login_required
def api_profile():
    user = request.current_user
    return jsonify(
        {
            "success": True,
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "user_type": user["user_type"],
                "real_name": user.get("real_name"),
                "school_company": user.get("school_company"),
            },
        }
    )
