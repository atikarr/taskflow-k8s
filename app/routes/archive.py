import os
from flask import Blueprint, render_template, jsonify, request, send_from_directory, current_app, abort
from flask_login import login_required

archive_bp = Blueprint("archive", __name__)

# Folder yang dilewati saat scan
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".claude", ".venv", "venv", ".idea", ".vscode"}
MAX_RESULTS = 800

ICONS = {
    ".pdf": "📕", ".doc": "📘", ".docx": "📘", ".ppt": "📙", ".pptx": "📙",
    ".xls": "📗", ".xlsx": "📗", ".csv": "📗", ".md": "📝", ".txt": "📄",
    ".png": "🖼", ".jpg": "🖼", ".jpeg": "🖼", ".gif": "🖼",
    ".zip": "🗜", ".rar": "🗜", ".7z": "🗜", ".ova": "💿", ".iso": "💿",
    ".py": "🐍", ".html": "🌐", ".js": "📜", ".yaml": "⚙", ".yml": "⚙",
    ".mp4": "🎬", ".mkv": "🎬",
}


def _root():
    root = current_app.config.get("ARCHIVE_ROOT")
    if not root or not os.path.isdir(root):
        return None
    return root


def categorize(rel_parts, filename):
    """Tebak kategori file dari nama folder dan nama file."""
    joined = " ".join(rel_parts).lower()
    name = filename.lower()

    if "referensi" in joined or "senior" in joined:
        return "referensi"
    if "tugas" in joined or "uts" in joined or "uas" in joined or "kuis" in joined:
        return "tugas"
    if "materi" in joined or "kuliah" in joined:
        return "materi"
    if "laporan" in name or "tugas" in name or "presentasi" in name or "naskah" in name:
        return "tugas"
    if name.endswith((".pptx", ".ppt")):
        return "materi"
    return "lainnya"


def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


@archive_bp.route("/archive")
@login_required
def index():
    root = _root()
    courses = []
    if root:
        courses = sorted(
            d for d in os.listdir(root)
            if os.path.isdir(os.path.join(root, d)) and d not in SKIP_DIRS and not d.startswith(".")
        )
    return render_template("archive.html", courses=courses, available=root is not None)


@archive_bp.route("/api/archive")
@login_required
def api_archive():
    root = _root()
    if not root:
        return jsonify(error="Arsip tidak dikonfigurasi"), 404

    course = request.args.get("course", "").strip()
    category = request.args.get("category", "").strip()
    q = request.args.get("q", "").strip().lower()

    if not course:
        return jsonify(files=[], counts={}, truncated=False)

    base = os.path.join(root, course)
    if not os.path.isdir(base) or ".." in course:
        return jsonify(error="Folder tidak ditemukan"), 404

    files = []
    counts = {"materi": 0, "tugas": 0, "referensi": 0, "lainnya": 0}
    truncated = False

    for dirpath, dirnames, filenames in os.walk(base):
        # skip folder junk & hasil ekstrak "..._files"
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith("_files")]

        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            rel_under_course = os.path.relpath(dirpath, base).replace("\\", "/")
            parts = [] if rel_under_course == "." else rel_under_course.split("/")

            cat = categorize(parts, fn)
            counts[cat] += 1

            if category and cat != category:
                continue
            if q and q not in fn.lower() and q not in rel_under_course.lower():
                continue

            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0
            ext = os.path.splitext(fn)[1].lower()

            files.append({
                "name": fn,
                "path": rel,
                "folder": rel_under_course if parts else "(root)",
                "category": cat,
                "size": human_size(size),
                "icon": ICONS.get(ext, "📄"),
            })

            if len(files) >= MAX_RESULTS:
                truncated = True
                break
        if truncated:
            break

    # Urutkan per folder lalu nama
    files.sort(key=lambda f: (f["folder"], f["name"].lower()))
    return jsonify(files=files, counts=counts, truncated=truncated)


@archive_bp.route("/archive/files/<path:relpath>")
@login_required
def serve_file(relpath):
    root = _root()
    if not root:
        abort(404)
    return send_from_directory(root, relpath, as_attachment=False)
