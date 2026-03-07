import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    from .admin import admin_bp
    from .applications import applications_bp
    from .auth import auth_bp
    from .db import ensure_admin_user, init_database, seed_demo_data_if_empty
    from .projects import projects_bp
except ImportError:
    # Fallback for environments that execute files directly instead of package mode.
    from admin import admin_bp
    from applications import applications_bp
    from auth import auth_bp
    from db import ensure_admin_user, init_database, seed_demo_data_if_empty
    from projects import projects_bp


def load_local_env() -> None:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_paths = [
        os.path.join(base_dir, ".env.local"),
        os.path.join(base_dir, ".env"),
    ]

    for env_path in env_paths:
        if not os.path.exists(env_path):
            continue

        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value


def create_app() -> Flask:
    load_local_env()
    app = Flask(__name__)
    app.json.ensure_ascii = False
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

    # CORS（保持你原来的行为：允许任意来源）
    CORS(app)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    # 处理 OPTIONS 预检（不覆盖普通 GET 路由，避免根路径出现 405）
    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            return "", 200
        return None

    @app.get("/")
    def index_page():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/health")
    def health_check():
        return jsonify({"success": True, "message": "backend is running"})

    @app.get("/favicon.ico")
    def favicon():
        return "", 204

    @app.get("/enterprisecenter")
    def enterprise_center_page():
        return send_from_directory(frontend_dir, "enterprise_center.html")

    @app.get("/enterprisecenter/publish")
    def enterprise_publish_page():
        return send_from_directory(frontend_dir, "enterprise_publish.html")

    @app.get("/enterprisecenter/roles")
    def enterprise_roles_page():
        return send_from_directory(frontend_dir, "enterprise_roles.html")

    @app.get("/enterprisecenter/review")
    def enterprise_review_page():
        return send_from_directory(frontend_dir, "enterprise_review.html")

    @app.get("/enterprisecenter/projects/<int:project_id>")
    def enterprise_project_detail_page(project_id: int):  # noqa: ARG001
        return send_from_directory(frontend_dir, "enterprise_project_detail.html")

    @app.get("/admin")
    def admin_dashboard_page():
        return send_from_directory(frontend_dir, "admin_dashboard.html")

    @app.get("/<path:filename>")
    def frontend_file(filename: str):
        return send_from_directory(frontend_dir, filename)

    # DB init/migrate + demo data
    init_database()
    seed_demo_data_if_empty()
    ensure_admin_user()

    # 路由注册
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(admin_bp)
    # legacy/team 接口不注册（按新方案重写）

    return app
