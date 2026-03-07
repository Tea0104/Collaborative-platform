import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "multi_role_platform.db"
ADMIN_USERNAME = "Tea0104"
ADMIN_PASSWORD_HASH = "scrypt:32768:8:1$MmySDxLHDJKmhnna$3513e700d6d1733841012378f2fb7738d4f567b1658a74dd0650e8e597aef53480a9f17f88e4349d93140c3918f618032062de432e91dc7279285fad6294e001"
DEMO_USERS = [
    ("student1", "scrypt:32768:8:1$EXPWjD0oSAvSKmka$964ec76e0e6659d6cae5e9271978bbc6b58dad83f3b0a2b807b508fb336d1588865b2b54e09dc6b75c8f26cb63445326cc39a2eed2f5b7b59fedaba8052826ab", "学生", "张三", "XX大学计算机学院", "Python,Flask", "13800000001"),
    ("student2", "scrypt:32768:8:1$bYC3Iu5b7LkJdMDy$017a6e90cde07580a2c9a6071a180f9df7bc1faa523574fbbc3ba1ba3fa49229b79ebdff9d2f2e122f9b66bafa5f10d335e694fe40a22e5bb00435a7e936f43e", "学生", "李四", "XX大学软件学院", "Vue,前端", "13900000002"),
    ("company1", "scrypt:32768:8:1$sdN2Y5y58Vf9GlPy$b542bae9aead6de5db9dec5942a35f859691f269d6e47d488045e3441a7a581e0a375f2480579f501b10ad64d4f9f9dda1540ff719d1a21c75ae8debe278ad5d", "企业", "阿里科技", "阿里科技有限公司", "", "ali@test.com"),
    ("company2", "scrypt:32768:8:1$9or0y3WjrR981cJS$8e970fc00bf82bb87edbaac944c9b165d8608f66eb4c1709492a3c5e045eba5d1762198542974e0fed17243a05dbead58af6d4a0f937e2c91ada3959a6ed8046", "企业", "腾讯云", "腾讯云计算有限公司", "", "tencent@test.com"),
]


def backup_database() -> Path:
    backup_dir = PROJECT_ROOT / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"multi_role_platform_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def main() -> int:
    if not DB_PATH.exists():
        print(f"数据库不存在：{DB_PATH}")
        return 1

    backup_path = backup_database()
    print(f"已备份数据库到：{backup_path}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cur.execute("SELECT user_id FROM user WHERE username = ?", (ADMIN_USERNAME,))
        row = cur.fetchone()
        if row:
            admin_user_id = row["user_id"]
            cur.execute(
                """
                UPDATE user
                SET password_hash = ?, user_type = '管理员', real_name = ?, school_company = ?, status = 1
                WHERE user_id = ?
                """,
                (ADMIN_PASSWORD_HASH, ADMIN_USERNAME, "系统管理", admin_user_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO user (username, password_hash, user_type, real_name, school_company, skill_tags, contact, status, create_time)
                VALUES (?, ?, '管理员', ?, ?, '', '', 1, ?)
                """,
                (ADMIN_USERNAME, ADMIN_PASSWORD_HASH, ADMIN_USERNAME, "系统管理", now),
            )
            admin_user_id = cur.lastrowid

        cur.execute("DELETE FROM auth_tokens WHERE user_id != ?", (admin_user_id,))
        cur.execute("DELETE FROM role_feedback")
        cur.execute("DELETE FROM role_application")
        cur.execute("DELETE FROM role")
        cur.execute("DELETE FROM project")
        cur.execute("DELETE FROM user WHERE user_id != ?", (admin_user_id,))

        cur.executemany(
            """
            INSERT INTO user (username, password_hash, user_type, real_name, school_company, skill_tags, contact, status, create_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            [(u[0], u[1], u[2], u[3], u[4], u[5], u[6], now) for u in DEMO_USERS],
        )

        cur.execute("SELECT user_id FROM user WHERE username = 'company1'")
        company1_id = cur.fetchone()["user_id"]
        cur.execute("SELECT user_id FROM user WHERE username = 'company2'")
        company2_id = cur.fetchone()["user_id"]

        cur.execute(
            """
            INSERT INTO project
            (project_name, description, publisher_id, project_status, publish_time, deadline, result_url, expected_market, work_mode, participant_count, company)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "电商平台V2.0",
                "轻量化电商平台开发",
                company1_id,
                "招募中",
                now,
                "2026-06-30 23:59:59",
                "",
                "校园市场",
                "远程协作",
                "5-8人",
                "阿里科技有限公司",
            ),
        )
        project1_id = cur.lastrowid

        cur.execute(
            """
            INSERT INTO project
            (project_name, description, publisher_id, project_status, publish_time, deadline, result_url, expected_market, work_mode, participant_count, company)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "大数据可视化",
                "用户行为数据分析",
                company2_id,
                "进行中",
                now,
                "2026-05-15 23:59:59",
                "",
                "企业市场",
                "混合协作",
                "3-5人",
                "腾讯云计算有限公司",
            ),
        )
        project2_id = cur.lastrowid

        cur.executemany(
            """
            INSERT INTO role
            (project_id, role_name, task_desc, skill_require, limit_num, join_num, role_status, task_deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (project1_id, "后端开发", "接口开发", "Python,Flask,SQLite", 3, 1, "招募中", "2026-04-30"),
                (project1_id, "前端开发", "页面开发", "Vue,HTML/CSS", 2, 0, "招募中", "2026-05-10"),
                (project2_id, "数据分析师", "数据清洗", "Python,Pandas", 2, 1, "进行中", "2026-04-20"),
            ],
        )

        conn.commit()
        print("已清洗历史数据，仅保留管理员账号，并重新写入测试账号和测试项目。")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"重置失败：{exc}")
        return 1
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
