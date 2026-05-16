import os

from flask import Flask

from .models import db


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///genealogy_demo.db",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["APP_MODE"] = os.getenv("APP_MODE", "demo")
    app.config["APP_MODE_LABEL"] = {
        "demo": "演示模式",
        "full": "大数据模式",
    }.get(app.config["APP_MODE"], app.config["APP_MODE"])

    db.init_app(app)

    from .routes import bp

    app.register_blueprint(bp)

    @app.context_processor
    def inject_app_meta():
        return {
            "app_mode": app.config["APP_MODE"],
            "app_mode_label": app.config["APP_MODE_LABEL"],
        }

    with app.app_context():
        db.create_all()

    return app
