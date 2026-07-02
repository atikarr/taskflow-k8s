from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, Task, User, Comment
from datetime import date, datetime
from sqlalchemy import or_, func

tasks_bp = Blueprint("tasks", __name__)


def _my_tasks_query():
    """Query dasar: tugas milik user atau yang di-assign ke user."""
    return Task.query.filter(
        (Task.user_id == current_user.id) | (Task.assigned_to == current_user.id)
    )


def _apply_filters(query):
    """Terapkan filter dari query params: course, priority, q (search)."""
    course = request.args.get("course", "").strip()
    priority = request.args.get("priority", "").strip()
    q = request.args.get("q", "").strip()

    if course:
        query = query.filter(Task.course == course)
    if priority:
        query = query.filter(Task.priority == priority)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Task.title.like(like), Task.description.like(like)))
    return query


@tasks_bp.route("/")
@login_required
def dashboard():
    # Daftar mata kuliah unik untuk dropdown filter
    courses = [
        row[0] for row in
        _my_tasks_query().with_entities(Task.course).filter(Task.course.isnot(None), Task.course != "")
        .distinct().all()
    ]
    users = User.query.filter(User.id != current_user.id).all()
    return render_template("dashboard.html", courses=courses, users=users)


# ============ API ENDPOINTS (AJAX / polling) ============

@tasks_bp.route("/api/tasks")
@login_required
def api_tasks():
    """Semua tugas user dalam JSON — dipanggil polling tiap 10 detik."""
    query = _apply_filters(_my_tasks_query())
    tasks = query.order_by(
        Task.deadline.is_(None), Task.deadline.asc(), Task.created_at.desc()
    ).all()
    return jsonify(tasks=[t.to_dict(current_user.id) for t in tasks])


@tasks_bp.route("/api/tasks/<int:task_id>/status", methods=["POST"])
@login_required
def api_update_status(task_id):
    """Update status via drag & drop kanban."""
    task = Task.query.get_or_404(task_id)
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status not in [Task.STATUS_TODO, Task.STATUS_IN_PROGRESS, Task.STATUS_DONE]:
        return jsonify(error="Status tidak valid"), 400

    task.status = new_status
    task.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(ok=True, task=task.to_dict(current_user.id))


@tasks_bp.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def api_delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify(error="Bukan tugas milikmu"), 403
    db.session.delete(task)
    db.session.commit()
    return jsonify(ok=True)


@tasks_bp.route("/api/stats")
@login_required
def api_stats():
    """Statistik untuk chart — breakdown status, prioritas, dan per matkul."""
    base = _my_tasks_query()

    by_status = {s: base.filter(Task.status == s).count()
                 for s in ["todo", "in_progress", "done"]}
    by_priority = {p: base.filter(Task.priority == p).count()
                   for p in ["high", "medium", "low"]}

    course_rows = (
        base.with_entities(Task.course, func.count(Task.id))
        .filter(Task.course.isnot(None), Task.course != "")
        .group_by(Task.course).all()
    )
    by_course = {c: n for c, n in course_rows}

    total = base.count()
    done = by_status["done"]
    overdue = base.filter(
        Task.deadline < date.today(), Task.status != "done"
    ).count()

    return jsonify(
        total=total, done=done, overdue=overdue,
        completion=round(done / total * 100) if total else 0,
        by_status=by_status, by_priority=by_priority, by_course=by_course
    )


@tasks_bp.route("/api/tasks/<int:task_id>/comments", methods=["GET", "POST"])
@login_required
def api_comments(task_id):
    task = Task.query.get_or_404(task_id)

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        content = (data.get("content") or "").strip()
        if not content:
            return jsonify(error="Komentar kosong"), 400
        comment = Comment(content=content, task_id=task.id, user_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        return jsonify(ok=True, comment=comment.to_dict())

    comments = Comment.query.filter_by(task_id=task.id).order_by(Comment.created_at.asc()).all()
    return jsonify(comments=[c.to_dict() for c in comments])


# ============ FORM PAGES (buat & edit) ============

@tasks_bp.route("/tasks/new", methods=["GET", "POST"])
@login_required
def new_task():
    users = User.query.filter(User.id != current_user.id).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Judul tugas tidak boleh kosong.", "error")
            return render_template("task_form.html", users=users, action="new", task=None)

        deadline = None
        deadline_str = request.form.get("deadline", "")
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Format tanggal tidak valid.", "error")
                return render_template("task_form.html", users=users, action="new", task=None)

        assigned_to = request.form.get("assigned_to", "") or None
        task = Task(
            title=title,
            description=request.form.get("description", "").strip(),
            course=request.form.get("course", "").strip() or None,
            priority=request.form.get("priority", "medium"),
            deadline=deadline,
            user_id=current_user.id,
            assigned_to=int(assigned_to) if assigned_to else None
        )
        db.session.add(task)
        db.session.commit()
        flash("Tugas berhasil dibuat!", "success")
        return redirect(url_for("tasks.dashboard"))

    return render_template("task_form.html", users=users, action="new", task=None)


@tasks_bp.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)

    if task.user_id != current_user.id:
        flash("Kamu tidak punya akses untuk mengedit tugas ini.", "error")
        return redirect(url_for("tasks.dashboard"))

    users = User.query.filter(User.id != current_user.id).all()

    if request.method == "POST":
        task.title = request.form.get("title", "").strip() or task.title
        task.description = request.form.get("description", "").strip()
        task.course = request.form.get("course", "").strip() or None
        task.priority = request.form.get("priority", task.priority)
        task.status = request.form.get("status", task.status)
        assigned_to = request.form.get("assigned_to", "") or None
        task.assigned_to = int(assigned_to) if assigned_to else None

        deadline_str = request.form.get("deadline", "")
        if deadline_str:
            try:
                task.deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Format tanggal tidak valid.", "error")
        else:
            task.deadline = None

        task.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Tugas berhasil diperbarui!", "success")
        return redirect(url_for("tasks.dashboard"))

    return render_template("task_form.html", users=users, action="edit", task=task)


@tasks_bp.route("/health")
def health():
    import socket
    return jsonify(status="ok", hostname=socket.gethostname())
