from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from .applications import applications_bp
    from .auth import auth_bp
    from .db import init_database, seed_demo_data_if_empty
    from .projects import projects_bp
except ImportError:
    # Fallback for environments that execute files directly instead of package mode.
    from applications import applications_bp
    from auth import auth_bp
    from db import init_database, seed_demo_data_if_empty
    from projects import projects_bp



def create_app() -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False

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
    def health_check():
        return jsonify({"success": True, "message": "backend is running"})

    @app.get("/favicon.ico")
    def favicon():
        return "", 204

    # DB init/migrate + demo data
    init_database()
    seed_demo_data_if_empty()

    # 路由注册
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(applications_bp)
    # legacy/team 接口不注册（按新方案重写）

    return app
