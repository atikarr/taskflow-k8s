from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    telegram_chat_id = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_tasks = db.relationship("Task", foreign_keys="Task.user_id", backref="creator", lazy=True)
    assigned_tasks = db.relationship("Task", foreign_keys="Task.assigned_to", backref="assignee", lazy=True)
    comments = db.relationship("Comment", backref="author", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Task(db.Model):
    __tablename__ = "tasks"

    STATUS_TODO = "todo"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"

    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    course = db.Column(db.String(100), nullable=True)      # mata kuliah / kategori
    status = db.Column(db.String(20), default=STATUS_TODO, nullable=False)
    priority = db.Column(db.String(10), default=PRIORITY_MEDIUM, nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    comments = db.relationship("Comment", backref="task", lazy=True, cascade="all, delete-orphan")

    @property
    def status_label(self):
        return {"todo": "To Do", "in_progress": "In Progress", "done": "Done"}.get(self.status, self.status)

    @property
    def priority_label(self):
        return {"low": "Rendah", "medium": "Sedang", "high": "Tinggi"}.get(self.priority, self.priority)

    @property
    def is_overdue(self):
        if self.deadline and self.status != self.STATUS_DONE:
            return self.deadline < datetime.utcnow().date()
        return False

    def to_dict(self, current_user_id=None):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "course": self.course or "",
            "status": self.status,
            "priority": self.priority,
            "priority_label": self.priority_label,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "is_overdue": self.is_overdue,
            "creator": self.creator.username if self.creator else None,
            "assignee": self.assignee.username if self.assignee else None,
            "is_mine": self.user_id == current_user_id,
            "comment_count": len(self.comments),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Task {self.title}>"


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    course = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(500), nullable=True)         # link eksternal (GDrive, YouTube, dll)
    filename = db.Column(db.String(300), nullable=True)     # file yang diupload
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploader = db.relationship("User", backref="materials", lazy=True)

    def to_dict(self, current_user_id=None):
        return {
            "id": self.id,
            "title": self.title,
            "course": self.course or "",
            "description": self.description or "",
            "link": self.link or "",
            "filename": self.filename or "",
            "uploader": self.uploader.username if self.uploader else "?",
            "is_mine": self.user_id == current_user_id,
            "created_at": self.created_at.strftime("%d %b %Y"),
        }

    def __repr__(self):
        return f"<Material {self.title}>"


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "author": self.author.username if self.author else "?",
            "created_at": self.created_at.strftime("%d %b %Y %H:%M"),
        }

    def __repr__(self):
        return f"<Comment {self.id}>"
