"""
保留你现有的“非 /api/”接口，避免前端已有页面/同学调试脚本失效。
同时，这些接口的实现复用现有数据库表，不强制前端立刻迁移到 /api/。
"""

from flask import Blueprint, jsonify, request

from .db import get_db_connection


legacy_bp = Blueprint("legacy", __name__)


@legacy_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.json or {}
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        if not username or not password:
            return jsonify({"success": False, "message": "用户名和密码不能为空"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, role FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        user = cursor.fetchone()
        conn.close()
        if not user:
            return jsonify({"success": False, "message": "用户名或密码错误"}), 401

        return jsonify(
            {
                "success": True,
                "message": "登录成功",
                "user": {"id": user["id"], "username": user["username"], "role": user["role"]},
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"登录失败: {str(e)}"}), 500


@legacy_bp.route("/", methods=["GET"])
def home():
    return jsonify(
        {
            "message": "项目组队系统",
            "endpoints": {
                "legacy": [
                    {"method": "POST", "path": "/login", "description": "旧版登录"},
                    {"method": "POST", "path": "/apply", "description": "旧版：直接加入角色（无审核）"},
                    {"method": "POST", "path": "/application/check", "description": "旧版：申请可行性检查"},
                    {"method": "GET", "path": "/project/<id>", "description": "旧版：项目详情"},
                    {"method": "GET", "path": "/project/<id>/members", "description": "旧版：项目成员"},
                    {"method": "GET", "path": "/project/<id>/available_roles", "description": "旧版：可申请角色"},
                    {"method": "GET", "path": "/student/<id>/projects", "description": "旧版：学生参与项目"},
                ],
                "api": [
                    {"method": "POST", "path": "/api/auth/register", "description": "注册"},
                    {"method": "POST", "path": "/api/auth/login", "description": "登录并返回 token"},
                    {"method": "GET", "path": "/api/auth/profile", "description": "当前用户信息"},
                    {"method": "GET", "path": "/api/projects", "description": "公开项目列表"},
                    {"method": "GET", "path": "/api/projects/<id>", "description": "公开项目详情(含角色)"},
                ],
            },
        }
    )


@legacy_bp.route("/apply", methods=["POST"])
def apply_for_role_direct_join():
    """
    旧版逻辑：学生申请后直接成为成员（不走审核）。
    新版推荐：用 /api/roles/{role_id}/apply + 企业 review。
    """
    try:
        data = request.json or {}
        student_id = data.get("student_id")
        project_id = data.get("project_id")
        role_id = data.get("role_id")
        if student_id is None or project_id is None or role_id is None:
            return jsonify({"success": False, "message": "student_id/project_id/role_id 不能为空"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'student'", (student_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "学生不存在或不是学生角色"}), 404

        cursor.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            conn.close()
            return jsonify({"success": False, "message": "项目不存在"}), 404

        cursor.execute(
            "SELECT id, max_member, current_member FROM project_roles WHERE id = ? AND project_id = ?",
            (role_id, project_id),
        )
        role = cursor.fetchone()
        if not role:
            conn.close()
            return jsonify({"success": False, "message": "角色不存在或不属于该项目"}), 404
        if role["current_member"] >= role["max_member"]:
            conn.close()
            return jsonify({"success": False, "message": "该角色已满员"}), 400

        cursor.execute("SELECT id FROM project_members WHERE student_id = ? AND project_id = ?", (student_id, project_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "您已经加入该项目"}), 400

        cursor.execute("INSERT INTO project_members (project_id, role_id, student_id) VALUES (?, ?, ?)", (project_id, role_id, student_id))
        cursor.execute("UPDATE project_roles SET current_member = current_member + 1 WHERE id = ?", (role_id,))
        conn.commit()

        member_id = cursor.lastrowid
        cursor.execute(
            """
            SELECT pm.id as member_id, pm.project_id, p.name as project_name,
                   pm.role_id, pr.role_name, pm.student_id, u.username as student_name,
                   pm.join_date, pm.status
            FROM project_members pm
            JOIN projects p ON pm.project_id = p.id
            JOIN project_roles pr ON pm.role_id = pr.id
            JOIN users u ON pm.student_id = u.id
            WHERE pm.id = ?
            """,
            (member_id,),
        )
        application = cursor.fetchone()
        conn.close()
        return jsonify({"success": True, "message": "申请成功！已加入项目", "application": dict(application)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"申请失败: {str(e)}"}), 500


@legacy_bp.route("/project/<int:project_id>/members", methods=["GET"])
def get_project_members(project_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            conn.close()
            return jsonify({"success": False, "message": "项目不存在"}), 404

        cursor.execute(
            """
            SELECT pm.id as member_id, pm.role_id, pr.role_name, pr.task_description,
                   pm.student_id, u.username as student_name,
                   datetime(pm.join_date, 'localtime') as join_date, pm.status
            FROM project_members pm
            JOIN project_roles pr ON pm.role_id = pr.id
            JOIN users u ON pm.student_id = u.id
            WHERE pm.project_id = ?
            ORDER BY pr.role_name, pm.join_date
            """,
            (project_id,),
        )
        members = cursor.fetchall()

        members_by_role = {}
        for member in members:
            role_name = member["role_name"]
            members_by_role.setdefault(role_name, []).append(
                {
                    "member_id": member["member_id"],
                    "student_id": member["student_id"],
                    "student_name": member["student_name"],
                    "join_date": member["join_date"],
                    "status": member["status"],
                }
            )

        cursor.execute(
            """
            SELECT id, role_name, task_description, max_member, current_member,
                   (max_member - current_member) as available_slots
            FROM project_roles
            WHERE project_id = ?
            ORDER BY role_name
            """,
            (project_id,),
        )
        roles = cursor.fetchall()
        conn.close()

        total_roles = len(roles)
        total_positions = sum(role["max_member"] for role in roles)
        filled_positions = sum(role["current_member"] for role in roles)
        available_positions = total_positions - filled_positions

        return jsonify(
            {
                "success": True,
                "message": "获取项目成员成功",
                "project": {
                    "id": project["id"],
                    "name": project["name"],
                    "stats": {
                        "total_roles": total_roles,
                        "total_positions": total_positions,
                        "filled_positions": filled_positions,
                        "available_positions": available_positions,
                    },
                },
                "roles": [dict(role) for role in roles],
                "members_by_role": members_by_role,
                "total_members": len(members),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"获取项目成员失败: {str(e)}"}), 500


@legacy_bp.route("/project/<int:project_id>/available_roles", methods=["GET"])
def get_available_roles(project_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            conn.close()
            return jsonify({"success": False, "message": "项目不存在"}), 404

        cursor.execute(
            """
            SELECT id, role_name, task_description, max_member, current_member,
                   (max_member - current_member) as available_slots
            FROM project_roles
            WHERE project_id = ? AND current_member < max_member
            ORDER BY available_slots DESC, role_name
            """,
            (project_id,),
        )
        available_roles = cursor.fetchall()
        conn.close()
        return jsonify(
            {
                "success": True,
                "message": "获取可申请角色成功",
                "project": {"id": project["id"], "name": project["name"]},
                "available_roles": [dict(role) for role in available_roles],
                "count": len(available_roles),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"获取可申请角色失败: {str(e)}"}), 500


@legacy_bp.route("/student/<int:student_id>/projects", methods=["GET"])
def get_student_projects(student_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE id = ? AND role = 'student'", (student_id,))
        student = cursor.fetchone()
        if not student:
            conn.close()
            return jsonify({"success": False, "message": "学生不存在或不是学生角色"}), 404

        cursor.execute(
            """
            SELECT pm.project_id, p.name as project_name, p.description,
                   pm.role_id, pr.role_name, u.username as company_name,
                   datetime(pm.join_date, 'localtime') as join_date, pm.status
            FROM project_members pm
            JOIN projects p ON pm.project_id = p.id
            JOIN project_roles pr ON pm.role_id = pr.id
            JOIN users u ON p.company_id = u.id
            WHERE pm.student_id = ?
            ORDER BY pm.join_date DESC
            """,
            (student_id,),
        )
        projects = cursor.fetchall()
        conn.close()
        return jsonify(
            {
                "success": True,
                "message": "获取学生项目成功",
                "student": {"id": student["id"], "username": student["username"]},
                "projects": [dict(project) for project in projects],
                "count": len(projects),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"获取学生项目失败: {str(e)}"}), 500


@legacy_bp.route("/application/check", methods=["POST"])
def check_application():
    try:
        data = request.json or {}
        student_id = data.get("student_id")
        project_id = data.get("project_id")
        role_id = data.get("role_id")
        if student_id is None or project_id is None or role_id is None:
            return jsonify({"success": False, "message": "学生ID、项目ID和角色ID都不能为空"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'student'", (student_id,))
        student = cursor.fetchone()
        cursor.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        cursor.execute(
            "SELECT id, role_name, max_member, current_member FROM project_roles WHERE id = ? AND project_id = ?",
            (role_id, project_id),
        )
        role = cursor.fetchone()
        cursor.execute("SELECT id FROM project_members WHERE student_id = ? AND project_id = ?", (student_id, project_id))
        already_in_project = cursor.fetchone()
        cursor.execute("SELECT id FROM project_members WHERE student_id = ? AND role_id = ?", (student_id, role_id))
        already_applied_role = cursor.fetchone()
        conn.close()

        checks = {
            "student_exists": bool(student),
            "project_exists": bool(project),
            "role_exists": bool(role),
            "role_belongs_to_project": role is not None,
            "role_has_capacity": bool(role) and role["current_member"] < role["max_member"],
            "student_not_in_project": not bool(already_in_project),
            "student_not_applied_role": not bool(already_applied_role),
        }
        all_passed = all(checks.values())
        if all_passed:
            return jsonify({"success": True, "message": "可以申请该角色", "checks": checks, "role_info": dict(role)})
        return jsonify({"success": False, "message": "不能申请该角色", "checks": checks, "role_info": dict(role) if role else None}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"检查申请失败: {str(e)}"}), 500


@legacy_bp.route("/project/create", methods=["POST"])
def create_project_legacy():
    try:
        data = request.json or {}
        name = (data.get("name") or "").strip()
        description = (data.get("description") or "").strip()
        company_id = data.get("company_id")
        if not name or company_id is None:
            return jsonify({"success": False, "message": "项目名称和公司ID不能为空"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'company'", (company_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "公司用户不存在"}), 404

        cursor.execute("INSERT INTO projects (name, description, company_id) VALUES (?, ?, ?)", (name, description, company_id))
        project_id = cursor.lastrowid

        roles = data.get("roles", []) or []
        inserted_roles = []
        for role in roles:
            role_name = (role.get("role_name") or "").strip()
            if not role_name:
                continue
            cursor.execute(
                "INSERT INTO project_roles (project_id, role_name, task_description, max_member) VALUES (?, ?, ?, ?)",
                (project_id, role_name, role.get("task_description", ""), role.get("max_member", 1)),
            )
            inserted_roles.append({"id": cursor.lastrowid, "role_name": role_name})

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "项目创建成功", "project_id": project_id, "roles": inserted_roles}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"创建项目失败: {str(e)}"}), 500


@legacy_bp.route("/project/<int:project_id>", methods=["GET"])
def get_project_detail_legacy(project_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.id, p.name, p.description, p.company_id, u.username as company_name, p.created_at
            FROM projects p
            JOIN users u ON p.company_id = u.id
            WHERE p.id = ?
            """,
            (project_id,),
        )
        project = cursor.fetchone()
        if not project:
            conn.close()
            return jsonify({"success": False, "message": "项目不存在"}), 404

        cursor.execute(
            "SELECT id, role_name, task_description, max_member, current_member FROM project_roles WHERE project_id = ?",
            (project_id,),
        )
        roles = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) as member_count FROM project_members WHERE project_id = ?", (project_id,))
        member_count = cursor.fetchone()["member_count"]
        conn.close()

        return jsonify({"success": True, "project": dict(project), "roles": [dict(role) for role in roles], "member_count": member_count})
    except Exception as e:
        return jsonify({"success": False, "message": f"获取项目详情失败: {str(e)}"}), 500

