import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Material

materials_bp = Blueprint("materials", __name__)

ALLOWED_EXTENSIONS = {"pdf", "ppt", "pptx", "doc", "docx", "xls", "xlsx", "zip", "png", "jpg", "jpeg", "txt", "md"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@materials_bp.route("/materials")
@login_required
def index():
    courses = [
        row[0] for row in
        Material.query.with_entities(Material.course)
        .filter(Material.course.isnot(None), Material.course != "")
        .distinct().all()
    ]
    return render_template("materials.html", courses=courses)


@materials_bp.route("/api/materials")
@login_required
def api_materials():
    query = Material.query
    course = request.args.get("course", "").strip()
    q = request.args.get("q", "").strip()

    if course:
        query = query.filter(Material.course == course)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Material.title.like(like) | Material.description.like(like)
        )

    materials = query.order_by(Material.created_at.desc()).all()
    return jsonify(materials=[m.to_dict(current_user.id) for m in materials])


@materials_bp.route("/materials/new", methods=["POST"])
@login_required
def create():
    title = request.form.get("title", "").strip()
    if not title:
        flash("Judul materi wajib diisi.", "error")
        return redirect(url_for("materials.index"))

    filename = None
    file = request.files.get("file")
    if file and file.filename:
        if not allowed_file(file.filename):
            flash("Tipe file tidak diizinkan.", "error")
            return redirect(url_for("materials.index"))
        # Prefix uuid supaya nama file tidak bentrok
        safe = secure_filename(file.filename)
        filename = f"{uuid.uuid4().hex[:8]}_{safe}"
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))

    material = Material(
        title=title,
        course=request.form.get("course", "").strip() or None,
        description=request.form.get("description", "").strip() or None,
        link=request.form.get("link", "").strip() or None,
        filename=filename,
        user_id=current_user.id,
    )
    db.session.add(material)
    db.session.commit()
    flash("Materi berhasil ditambahkan!", "success")
    return redirect(url_for("materials.index"))


@materials_bp.route("/materials/files/<path:filename>")
@login_required
def download(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename, as_attachment=False)


@materials_bp.route("/api/materials/<int:material_id>", methods=["DELETE"])
@login_required
def api_delete(material_id):
    material = Material.query.get_or_404(material_id)
    if material.user_id != current_user.id:
        return jsonify(error="Bukan materi milikmu"), 403

    if material.filename:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], material.filename)
        if os.path.exists(path):
            os.remove(path)

    db.session.delete(material)
    db.session.commit()
    return jsonify(ok=True)
