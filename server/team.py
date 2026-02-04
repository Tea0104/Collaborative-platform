from flask import Blueprint, jsonify, request

from .auth import login_required
from .db import get_db_connection


team_bp = Blueprint("team", __name__)


@team_bp.route("/api/projects/<int:project_id>/team", methods=["GET"])
@login_required
def get_project_team(project_id: int):
    """
    计划接口：GET /api/projects/{project_id}/team
    可见性：项目所属企业、或项目团队内学生
    """
    user = request.current_user
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, company_id, name, status FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    if not project:
        conn.close()
        return jsonify({"success": False, "message": "项目不存在"}), 404

    allowed = False
    if user["role"] == "company" and project["company_id"] == user["id"]:
        allowed = True
    if user["role"] == "student":
        cursor.execute(
            """
            SELECT 1
            FROM team_members tm
            JOIN teams t ON tm.team_id = t.id
            WHERE t.project_id = ? AND tm.user_id = ?
            """,
            (project_id, user["id"]),
        )
        allowed = bool(cursor.fetchone())

    if not allowed:
        conn.close()
        return jsonify({"success": False, "message": "无权限查看团队信息"}), 403

    cursor.execute("SELECT id, name, status, created_at FROM teams WHERE project_id = ?", (project_id,))
    team = cursor.fetchone()
    if not team:
        # 尚未形成团队（无人被录取）
        conn.close()
        return jsonify(
            {
                "success": True,
                "project": {"id": project["id"], "title": project["name"]},
                "team": None,
                "members": [],
            }
        )

    cursor.execute(
        """
        SELECT tm.id, tm.user_id, u.username AS user_name,
               tm.project_role_id, pr.role_name AS role_name,
               tm.joined_at
        FROM team_members tm
        JOIN users u ON tm.user_id = u.id
        JOIN project_roles pr ON tm.project_role_id = pr.id
        WHERE tm.team_id = ?
        ORDER BY pr.role_name, tm.joined_at
        """,
        (team["id"],),
    )
    members = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify(
        {
            "success": True,
            "project": {"id": project["id"], "title": project["name"]},
            "team": dict(team),
            "members": members,
        }
    )

