import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from werkzeug.security import generate_password_hash


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "multi_role_platform.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            user_type TEXT NOT NULL,
            real_name TEXT NOT NULL,
            school_company TEXT,
            skill_tags TEXT,
            contact TEXT,
            status INTEGER NOT NULL DEFAULT 1,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS project (
            project_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            description TEXT DEFAULT '无详细描述',
            publisher_id INTEGER NOT NULL,
            project_status TEXT NOT NULL DEFAULT '招募中',
            publish_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline TIMESTAMP,
            result_url TEXT,
            company TEXT NOT NULL,
            FOREIGN KEY (publisher_id) REFERENCES user(user_id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS role (
            role_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            role_name TEXT NOT NULL,
            task_desc TEXT NOT NULL,
            skill_require TEXT,
            limit_num INTEGER NOT NULL DEFAULT 1,
            join_num INTEGER NOT NULL DEFAULT 0,
            role_status TEXT NOT NULL DEFAULT '招募中',
            task_deadline TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES project(project_id) ON DELETE CASCADE,
            UNIQUE (project_id, role_name)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS role_application (
            application_id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            motivation TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            apply_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            update_time TIMESTAMP,
            UNIQUE (role_id, student_id),
            FOREIGN KEY (role_id) REFERENCES role(role_id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES project(project_id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES user(user_id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()


def seed_demo_data_if_empty() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS count FROM user")
    user_count = cursor.fetchone()["count"]

    if user_count > 0:
        conn.close()
        return

    users = [
        ("student1", generate_password_hash("123456"), "学生", "张三", "XX大学计算机学院", "Python,Flask", "13800000001"),
        ("student2", generate_password_hash("123456"), "学生", "李四", "XX大学软件学院", "Vue,前端", "13900000002"),
        ("company1", generate_password_hash("123456"), "企业", "阿里科技", "阿里科技有限公司", "", "ali@test.com"),
        ("company2", generate_password_hash("123456"), "企业", "腾讯云", "腾讯云计算有限公司", "", "tencent@test.com"),
    ]
    cursor.executemany(
        """
        INSERT INTO user (username, password_hash, user_type, real_name, school_company, skill_tags, contact, status, create_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        [(u[0], u[1], u[2], u[3], u[4], u[5], u[6], datetime.now().strftime("%Y-%m-%d %H:%M:%S")) for u in users],
    )

    cursor.execute("SELECT user_id FROM user WHERE user_type = '企业' ORDER BY user_id LIMIT 2")
    companies = cursor.fetchall()
    if len(companies) >= 2:
        company1_id = companies[0]["user_id"]
        company2_id = companies[1]["user_id"]

        cursor.execute(
            """
            INSERT INTO project
            (project_name, description, publisher_id, project_status, publish_time, deadline, result_url, company)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "电商平台V2.0",
                "轻量化电商平台开发",
                company1_id,
                "招募中",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "2026-06-30 23:59:59",
                "",
                "阿里科技有限公司",
            ),
        )
        project1_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO project
            (project_name, description, publisher_id, project_status, publish_time, deadline, result_url, company)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "大数据可视化",
                "用户行为数据分析",
                company2_id,
                "进行中",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "2026-05-15 23:59:59",
                "",
                "腾讯云计算有限公司",
            ),
        )
        project2_id = cursor.lastrowid

        roles = [
            (project1_id, "后端开发", "接口开发", "Python,Flask,SQLite", 3, 1, "招募中", "2026-04-30"),
            (project1_id, "前端开发", "页面开发", "Vue,HTML/CSS", 2, 0, "招募中", "2026-05-10"),
            (project2_id, "数据分析师", "数据清洗", "Python,Pandas", 2, 1, "进行中", "2026-04-20"),
        ]
        cursor.executemany(
            """
            INSERT INTO role
            (project_id, role_name, task_desc, skill_require, limit_num, join_num, role_status, task_deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            roles,
        )

    conn.commit()
    conn.close()


# ===== CRUD Functions (team contribution integration) =====

USER_TYPES = {"学生", "企业"}
PROJECT_STATUS = {"草稿", "招募中", "进行中", "已完成", "已终止"}
ROLE_STATUS = {"招募中", "进行中", "已完成"}


def user_add(
    username: str,
    password_hash: str,
    user_type: str,
    real_name: str,
    school_company: str,
    skill_tags: str = "",
    contact: str = "",
    status: int = 1,
    create_time: Optional[str] = None,
) -> Dict:
    if user_type not in USER_TYPES:
        return {"code": 400, "msg": "用户类型仅支持：学生/企业", "data": None}
    create_time = create_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO user (username, password_hash, user_type, real_name, school_company,
                              skill_tags, contact, status, create_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (username, password_hash, user_type, real_name, school_company, skill_tags, contact, status, create_time),
        )
        conn.commit()
        return {"code": 200, "msg": "用户新增成功", "data": {"user_id": cur.lastrowid, "username": username}}
    except sqlite3.IntegrityError:
        conn.rollback()
        return {"code": 409, "msg": "用户名已存在", "data": None}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"用户新增失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def user_del(user_id: int) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id FROM user WHERE user_id = ?", (user_id,))
        if not cur.fetchone():
            return {"code": 404, "msg": "用户ID不存在", "data": None}
        cur.execute("DELETE FROM user WHERE user_id = ?", (user_id,))
        conn.commit()
        return {"code": 200, "msg": "用户删除成功", "data": {"user_id": user_id}}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"用户删除失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def user_update(user_id: int, **kwargs) -> Dict:
    allow_fields = [
        "username",
        "password_hash",
        "user_type",
        "real_name",
        "school_company",
        "skill_tags",
        "contact",
        "status",
        "last_login",
    ]
    for k in kwargs:
        if k not in allow_fields:
            return {"code": 400, "msg": f"不支持修改字段：{k}", "data": None}
    if "user_type" in kwargs and kwargs["user_type"] not in USER_TYPES:
        return {"code": 400, "msg": "用户类型仅支持：学生/企业", "data": None}
    if not kwargs:
        return {"code": 400, "msg": "无修改字段传入", "data": None}

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id FROM user WHERE user_id = ?", (user_id,))
        if not cur.fetchone():
            return {"code": 404, "msg": "用户ID不存在", "data": None}
        update_sql = f"UPDATE user SET {', '.join([f'{k}=?' for k in kwargs])} WHERE user_id=?"
        cur.execute(update_sql, list(kwargs.values()) + [user_id])
        conn.commit()
        return {"code": 200, "msg": "用户修改成功", "data": {"user_id": user_id, "update_fields": list(kwargs.keys())}}
    except sqlite3.IntegrityError:
        conn.rollback()
        return {"code": 409, "msg": "用户名已存在（修改用户名冲突）", "data": None}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"用户修改失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def get_user(user_id: int) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM user WHERE user_id = ?", (user_id,))
        user_data = cur.fetchone()
        if not user_data:
            return {"code": 404, "msg": "用户ID不存在", "data": None}
        return {"code": 200, "msg": "用户详情查询成功", "data": dict(user_data)}
    except Exception as e:
        return {"code": 500, "msg": f"用户查询失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def get_user_by_username(username: str) -> Optional[dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM user WHERE username = ?", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def project_add(
    project_name: str,
    publisher_id: int,
    company: str,
    description: str = "无详细描述",
    project_status: str = "招募中",
    deadline: Optional[str] = None,
    result_url: str = "",
) -> Dict:
    if project_status not in PROJECT_STATUS:
        return {"code": 400, "msg": "项目状态不合法", "data": None}
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_type FROM user WHERE user_id = ?", (publisher_id,))
        pub = cur.fetchone()
        if not pub:
            return {"code": 404, "msg": "发布者ID不存在", "data": None}
        if pub["user_type"] != "企业":
            return {"code": 403, "msg": "仅企业可发布项目", "data": None}
        cur.execute(
            """
            INSERT INTO project (project_name, description, publisher_id, project_status,
                                 publish_time, deadline, result_url, company)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_name,
                description,
                publisher_id,
                project_status,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                deadline,
                result_url,
                company,
            ),
        )
        conn.commit()
        return {"code": 200, "msg": "项目新增成功", "data": {"project_id": cur.lastrowid, "project_name": project_name}}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"项目新增失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def project_update(project_id: int, **kwargs) -> Dict:
    allow_fields = [
        "project_name",
        "description",
        "publisher_id",
        "project_status",
        "deadline",
        "result_url",
        "company",
    ]
    for k in kwargs:
        if k not in allow_fields:
            return {"code": 400, "msg": f"不支持修改字段：{k}", "data": None}
    if "project_status" in kwargs and kwargs["project_status"] not in PROJECT_STATUS:
        return {"code": 400, "msg": "项目状态不合法", "data": None}
    if "publisher_id" in kwargs:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_type FROM user WHERE user_id = ?", (kwargs["publisher_id"],))
        pub = cur.fetchone()
        cur.close()
        conn.close()
        if not pub or pub["user_type"] != "企业":
            return {"code": 403, "msg": "新的发布者必须是企业且存在", "data": None}
    if not kwargs:
        return {"code": 400, "msg": "无修改字段传入", "data": None}

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT project_id FROM project WHERE project_id = ?", (project_id,))
        if not cur.fetchone():
            return {"code": 404, "msg": "项目ID不存在", "data": None}
        update_sql = f"UPDATE project SET {', '.join([f'{k}=?' for k in kwargs])} WHERE project_id=?"
        cur.execute(update_sql, list(kwargs.values()) + [project_id])
        conn.commit()
        return {"code": 200, "msg": "项目修改成功", "data": {"project_id": project_id, "update_fields": list(kwargs.keys())}}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"项目修改失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def project_del(project_id: int) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT project_id FROM project WHERE project_id = ?", (project_id,))
        if not cur.fetchone():
            return {"code": 404, "msg": "项目ID不存在", "data": None}
        cur.execute("DELETE FROM project WHERE project_id = ?", (project_id,))
        conn.commit()
        return {"code": 200, "msg": "项目删除成功", "data": {"project_id": project_id}}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"项目删除失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def get_project(project_id: int) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM project WHERE project_id = ?", (project_id,))
        project_data = cur.fetchone()
        if not project_data:
            return {"code": 404, "msg": "项目ID不存在", "data": None}
        return {"code": 200, "msg": "项目详情查询成功", "data": dict(project_data)}
    except Exception as e:
        return {"code": 500, "msg": f"项目查询失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def list_projects_by_publisher(publisher_id: int, status: Optional[str] = None) -> List[dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    if status:
        cur.execute(
            "SELECT * FROM project WHERE publisher_id = ? AND project_status = ? ORDER BY publish_time DESC",
            (publisher_id, status),
        )
    else:
        cur.execute("SELECT * FROM project WHERE publisher_id = ? ORDER BY publish_time DESC", (publisher_id,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def list_public_projects(q: str = "") -> List[dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    if q:
        cur.execute(
            """
            SELECT project_id, project_name, description, project_status, publish_time, deadline, company
            FROM project
            WHERE project_status != '草稿'
              AND (project_name LIKE ? OR description LIKE ? OR company LIKE ?)
            ORDER BY publish_time DESC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        )
    else:
        cur.execute(
            """
            SELECT project_id, project_name, description, project_status, publish_time, deadline, company
            FROM project
            WHERE project_status != '草稿'
            ORDER BY publish_time DESC
            """
        )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def role_add(
    project_id: int,
    role_name: str,
    task_desc: str,
    skill_require: str = "",
    limit_num: int = 1,
    join_num: int = 0,
    role_status: str = "招募中",
    task_deadline: Optional[str] = None,
) -> Dict:
    if role_status not in ROLE_STATUS:
        return {"code": 400, "msg": "角色状态不合法", "data": None}
    if join_num > limit_num:
        return {"code": 400, "msg": "已有人数不能超过人数限制", "data": None}
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT project_id FROM project WHERE project_id = ?", (project_id,))
        if not cur.fetchone():
            return {"code": 404, "msg": "项目ID不存在", "data": None}
        cur.execute(
            """
            INSERT INTO role (project_id, role_name, task_desc, skill_require,
                              limit_num, join_num, role_status, task_deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, role_name, task_desc, skill_require, limit_num, join_num, role_status, task_deadline),
        )
        conn.commit()
        return {"code": 200, "msg": "角色新增成功", "data": {"role_id": cur.lastrowid, "role_name": role_name}}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"角色新增失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def role_update(role_id: int, **kwargs) -> Dict:
    allow_fields = [
        "project_id",
        "role_name",
        "task_desc",
        "skill_require",
        "limit_num",
        "join_num",
        "role_status",
        "task_deadline",
    ]
    for k in kwargs:
        if k not in allow_fields:
            return {"code": 400, "msg": f"不支持修改字段：{k}", "data": None}
    if "role_status" in kwargs and kwargs["role_status"] not in ROLE_STATUS:
        return {"code": 400, "msg": "角色状态不合法", "data": None}
    if "join_num" in kwargs and "limit_num" in kwargs:
        if kwargs["join_num"] > kwargs["limit_num"]:
            return {"code": 400, "msg": "已有人数不能超过人数限制", "data": None}
    if "project_id" in kwargs:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT project_id FROM project WHERE project_id = ?", (kwargs["project_id"],))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return {"code": 404, "msg": "新项目ID不存在", "data": None}
        cur.close()
        conn.close()
    if not kwargs:
        return {"code": 400, "msg": "无修改字段传入", "data": None}

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT role_id FROM role WHERE role_id = ?", (role_id,))
        if not cur.fetchone():
            return {"code": 404, "msg": "角色ID不存在", "data": None}
        update_sql = f"UPDATE role SET {', '.join([f'{k}=?' for k in kwargs])} WHERE role_id=?"
        cur.execute(update_sql, list(kwargs.values()) + [role_id])
        conn.commit()
        return {"code": 200, "msg": "角色修改成功", "data": {"role_id": role_id, "update_fields": list(kwargs.keys())}}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"角色修改失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def role_del(role_id: int) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT role_id FROM role WHERE role_id = ?", (role_id,))
        if not cur.fetchone():
            return {"code": 404, "msg": "角色ID不存在", "data": None}
        cur.execute("DELETE FROM role WHERE role_id = ?", (role_id,))
        conn.commit()
        return {"code": 200, "msg": "角色删除成功", "data": {"role_id": role_id}}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"角色删除失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def get_role(role_id: int) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM role WHERE role_id = ?", (role_id,))
        role_data = cur.fetchone()
        if not role_data:
            return {"code": 404, "msg": "角色ID不存在", "data": None}
        return {"code": 200, "msg": "角色详情查询成功", "data": dict(role_data)}
    except Exception as e:
        return {"code": 500, "msg": f"角色查询失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def list_roles_by_project(project_id: int) -> List[dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM role WHERE project_id = ? ORDER BY role_id", (project_id,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def save_token(token: str, user_id: int) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO auth_tokens (token, user_id) VALUES (?, ?)", (token, user_id))
    conn.commit()
    cur.close()
    conn.close()


def delete_token(token: str) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
    conn.commit()
    cur.close()
    conn.close()


def get_user_by_token(token: str) -> Optional[dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.user_id, u.username, u.user_type, u.real_name, u.school_company
        FROM auth_tokens t
        JOIN user u ON t.user_id = u.user_id
        WHERE t.token = ?
        """,
        (token,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def apply_for_role(role_id: int, student_id: int, motivation: str) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT r.role_id, r.project_id, r.role_status, r.limit_num, r.join_num,
                   p.project_status
            FROM role r
            JOIN project p ON r.project_id = p.project_id
            WHERE r.role_id = ?
            """,
            (role_id,),
        )
        role = cur.fetchone()
        if not role:
            return {"code": 404, "msg": "角色不存在", "data": None}
        if role["project_status"] in ("草稿", "已终止"):
            return {"code": 400, "msg": "项目未发布或已终止，无法申请", "data": None}
        if role["role_status"] != "招募中":
            return {"code": 400, "msg": "角色不可申请", "data": None}
        if role["join_num"] >= role["limit_num"]:
            return {"code": 400, "msg": "角色名额已满", "data": None}

        cur.execute(
            "SELECT application_id, status FROM role_application WHERE role_id = ? AND student_id = ?",
            (role_id, student_id),
        )
        existing = cur.fetchone()
        if existing and existing["status"] in ("pending", "accepted"):
            return {"code": 400, "msg": "你已提交过该角色申请", "data": None}

        cur.execute(
            """
            SELECT application_id
            FROM role_application
            WHERE project_id = ? AND student_id = ? AND status = 'accepted'
            """,
            (role["project_id"], student_id),
        )
        if cur.fetchone():
            return {"code": 400, "msg": "你已加入该项目，无法再次申请", "data": None}

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if existing:
            cur.execute(
                """
                UPDATE role_application
                SET motivation = ?, status = 'pending', update_time = ?
                WHERE application_id = ?
                """,
                (motivation, now, existing["application_id"]),
            )
            application_id = existing["application_id"]
        else:
            cur.execute(
                """
                INSERT INTO role_application (role_id, project_id, student_id, motivation, status, apply_time, update_time)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (role_id, role["project_id"], student_id, motivation, now, now),
            )
            application_id = cur.lastrowid
        conn.commit()
        return {"code": 200, "msg": "申请成功", "data": {"application_id": application_id}}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"申请失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()


def list_student_applications(student_id: int) -> List[dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ra.application_id, ra.status, ra.motivation, ra.apply_time, ra.update_time,
               r.role_id, r.role_name,
               p.project_id, p.project_name, p.company
        FROM role_application ra
        JOIN role r ON ra.role_id = r.role_id
        JOIN project p ON ra.project_id = p.project_id
        WHERE ra.student_id = ?
        ORDER BY ra.apply_time DESC
        """,
        (student_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def cancel_application(application_id: int, student_id: int) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE role_application
        SET status = 'cancelled', update_time = ?
        WHERE application_id = ? AND student_id = ? AND status = 'pending'
        """,
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), application_id, student_id),
    )
    if cur.rowcount == 0:
        cur.close()
        conn.close()
        return {"code": 400, "msg": "撤回失败：记录不存在或状态不可撤回", "data": None}
    conn.commit()
    cur.close()
    conn.close()
    return {"code": 200, "msg": "已撤回", "data": {"application_id": application_id}}


def list_role_applications(role_id: int, enterprise_id: int) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.role_id
        FROM role r
        JOIN project p ON r.project_id = p.project_id
        WHERE r.role_id = ? AND p.publisher_id = ?
        """,
        (role_id, enterprise_id),
    )
    if not cur.fetchone():
        cur.close()
        conn.close()
        return {"code": 404, "msg": "角色不存在或无权限", "data": None}

    cur.execute(
        """
        SELECT ra.application_id, ra.status, ra.motivation, ra.apply_time, ra.update_time,
               u.user_id AS student_id, u.username AS student_name, u.real_name
        FROM role_application ra
        JOIN user u ON ra.student_id = u.user_id
        WHERE ra.role_id = ?
        ORDER BY ra.apply_time DESC
        """,
        (role_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return {"code": 200, "msg": "查询成功", "data": rows}


def review_application(application_id: int, enterprise_id: int, decision: str) -> Dict:
    if decision not in ("accepted", "rejected"):
        return {"code": 400, "msg": "decision 只能是 accepted 或 rejected", "data": None}
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT ra.application_id, ra.status, ra.student_id, ra.role_id, ra.project_id,
                   r.limit_num, r.join_num, r.role_status,
                   p.project_status
            FROM role_application ra
            JOIN role r ON ra.role_id = r.role_id
            JOIN project p ON ra.project_id = p.project_id
            WHERE ra.application_id = ? AND p.publisher_id = ?
            """,
            (application_id, enterprise_id),
        )
        app_row = cur.fetchone()
        if not app_row:
            return {"code": 404, "msg": "申请不存在或无权限", "data": None}
        if app_row["status"] != "pending":
            return {"code": 400, "msg": "只能审核 pending 申请", "data": None}

        if decision == "rejected":
            cur.execute(
                "UPDATE role_application SET status = 'rejected', update_time = ? WHERE application_id = ?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), application_id),
            )
            conn.commit()
            return {"code": 200, "msg": "已拒绝", "data": {"application_id": application_id}}

        if app_row["project_status"] in ("草稿", "已终止"):
            return {"code": 400, "msg": "项目未发布或已终止，无法录取", "data": None}
        if app_row["role_status"] != "招募中":
            return {"code": 400, "msg": "角色不可录取", "data": None}
        if app_row["join_num"] >= app_row["limit_num"]:
            return {"code": 400, "msg": "角色已满，无法录取", "data": None}

        cur.execute(
            """
            SELECT application_id
            FROM role_application
            WHERE project_id = ? AND student_id = ? AND status = 'accepted'
            """,
            (app_row["project_id"], app_row["student_id"]),
        )
        if cur.fetchone():
            return {"code": 400, "msg": "该学生已加入该项目", "data": None}

        cur.execute(
            "UPDATE role_application SET status = 'accepted', update_time = ? WHERE application_id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), application_id),
        )
        cur.execute("UPDATE role SET join_num = join_num + 1 WHERE role_id = ?", (app_row["role_id"],))
        cur.execute("SELECT join_num, limit_num FROM role WHERE role_id = ?", (app_row["role_id"],))
        role_counts = cur.fetchone()
        if role_counts and role_counts["join_num"] >= role_counts["limit_num"]:
            cur.execute("UPDATE role SET role_status = '已完成' WHERE role_id = ?", (app_row["role_id"],))
        conn.commit()
        return {"code": 200, "msg": "已录取", "data": {"application_id": application_id}}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "msg": f"录取失败：{str(e)}", "data": None}
    finally:
        cur.close()
        conn.close()
