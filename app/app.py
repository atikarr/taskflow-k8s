import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from app.models import db, User
from app.config import Config
from app.routes.auth import auth_bp
from app.routes.tasks import tasks_bp
from app.routes.materials import materials_bp
from app.routes.archive import archive_bp

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # Folder upload materi — di K8s nanti di-mount sebagai PVC
    app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "/app/uploads")
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024   # maks 20MB per file
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Arsip semester (opsional) — folder host di-mount read-only via docker-compose
    app.config["ARCHIVE_ROOT"] = os.environ.get("ARCHIVE_ROOT", "")

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Silakan login terlebih dahulu."

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(archive_bp)

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
