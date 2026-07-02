# Product Requirements Document (PRD)
## TaskFlow K8s — Sistem Manajemen Tugas Berbasis Cloud

**Versi:** 1.0  
**Mata Kuliah:** Keamanan Komputasi Awan  
**Dibuat:** 2026-07-02

---

## 1. Ringkasan Eksekutif

TaskFlow K8s adalah aplikasi manajemen tugas untuk mahasiswa dan tim kuliah yang di-deploy menggunakan arsitektur cloud native. Proyek ini mendemonstrasikan implementasi nyata dari konsep IaaS (OpenStack), container orchestration (Kubernetes), dan autoscaling (HPA) dalam satu sistem yang berguna.

---

## 2. Latar Belakang & Tujuan

### Masalah
- Mahasiswa kesulitan melacak tugas kuliah yang tersebar di berbagai channel
- Tidak ada sistem terpusat untuk assign tugas ke anggota tim
- Tidak ada pengingat otomatis saat deadline hampir tiba

### Solusi
Aplikasi web manajemen tugas dengan notifikasi Telegram otomatis, di-deploy di atas infrastruktur cloud (OpenStack + Kubernetes).

### Tujuan Akademis
Membuktikan pemahaman terhadap:
- Containerization (Docker)
- Container Orchestration (Kubernetes)
- Horizontal Pod Autoscaling (HPA)
- IaaS layer (OpenStack sebagai platform)
- Arsitektur microservice sederhana

---

## 3. Pengguna Target

| Persona | Deskripsi |
|---|---|
| Mahasiswa | Mengelola tugas kuliah pribadi, melihat deadline |
| Ketua Kelompok | Assign tugas ke anggota, pantau progress tim |
| Anggota Tim | Lihat tugas yang di-assign, update status |

---

## 4. Fitur & Spesifikasi

### 4.1 Autentikasi (Auth)
| ID | Fitur | Prioritas |
|---|---|---|
| AUTH-1 | Register akun baru (username, email, password) | Wajib |
| AUTH-2 | Login dengan username + password | Wajib |
| AUTH-3 | Logout | Wajib |
| AUTH-4 | Simpan Telegram Chat ID di profil | Wajib |

### 4.2 Manajemen Tugas (CRUD)
| ID | Fitur | Prioritas |
|---|---|---|
| TASK-1 | Buat tugas baru (judul, deskripsi, prioritas, deadline) | Wajib |
| TASK-2 | Lihat daftar tugas (milik sendiri + yang di-assign) | Wajib |
| TASK-3 | Edit tugas yang dibuat sendiri | Wajib |
| TASK-4 | Hapus tugas yang dibuat sendiri | Wajib |
| TASK-5 | Update status tugas (Todo → In Progress → Done) | Wajib |
| TASK-6 | Assign tugas ke user lain | Wajib |
| TASK-7 | Filter tugas berdasarkan status dan prioritas | Wajib |

### 4.3 Status & Prioritas
| Status | Keterangan |
|---|---|
| `todo` | Belum dikerjakan |
| `in_progress` | Sedang dikerjakan |
| `done` | Selesai |

| Prioritas | Keterangan |
|---|---|
| `high` 🔴 | Harus segera diselesaikan |
| `medium` 🟡 | Prioritas normal |
| `low` ⚪ | Bisa dikerjakan belakangan |

### 4.4 Notifikasi Telegram
| ID | Fitur | Prioritas |
|---|---|---|
| NOTIF-1 | Kirim notifikasi H-1 deadline via Telegram Bot | Wajib |
| NOTIF-2 | Dijalankan otomatis oleh Kubernetes CronJob (01:00 UTC / 08:00 WIB) | Wajib |
| NOTIF-3 | User simpan Chat ID Telegram di halaman profil | Wajib |

---

## 5. Arsitektur Teknis

### 5.1 Stack Teknologi
| Layer | Teknologi | Alasan |
|---|---|---|
| Backend | Python Flask | Ringan, cocok untuk demo K8s |
| Database | MySQL 8.0 | Relasional, familiar |
| ORM | Flask-SQLAlchemy | Simpel, integrasi baik dengan Flask |
| Auth | Flask-Login + Werkzeug | Session-based, aman |
| Frontend | HTML + CSS + Jinja2 | Tanpa framework besar, ringan |
| Container | Docker | Standar industri |
| Orchestration | Kubernetes (Minikube) | Demo autoscaling |
| Notifikasi | Telegram Bot API | Mudah diintegrasikan |

### 5.2 Arsitektur Deployment

```
[User Browser]
      │ HTTP
      ▼
[K8s NodePort Service :30080]
      │
      ▼
[Flask App Deployment]    ←── HPA (scale 1-5 pod, CPU baseline 50%)
[Pod 1] [Pod 2] ... [Pod N]
      │ SQL
      ▼
[MySQL Deployment + PVC]
      │
[K8s CronJob]  ──→  [Telegram Bot API]  ──→  [User Telegram]
(tiap hari 08:00 WIB)

Platform: OpenStack (IaaS) / Ubuntu VM
```

### 5.3 Database Schema

```sql
-- Tabel users
CREATE TABLE users (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    username        VARCHAR(80) UNIQUE NOT NULL,
    email           VARCHAR(120) UNIQUE NOT NULL,
    password_hash   VARCHAR(256) NOT NULL,
    telegram_chat_id VARCHAR(50),
    created_at      DATETIME DEFAULT NOW()
);

-- Tabel tasks
CREATE TABLE tasks (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    status      ENUM('todo','in_progress','done') DEFAULT 'todo',
    priority    ENUM('low','medium','high') DEFAULT 'medium',
    deadline    DATE,
    created_at  DATETIME DEFAULT NOW(),
    updated_at  DATETIME DEFAULT NOW() ON UPDATE NOW(),
    user_id     INT NOT NULL REFERENCES users(id),
    assigned_to INT REFERENCES users(id)
);
```

---

## 6. Struktur File

```
taskflow-k8s/
├── PRD.md                      ← dokumen ini
├── Dockerfile                  ← build image Flask app
├── docker-compose.yml          ← local development
├── requirements.txt            ← Python dependencies
├── app/
│   ├── app.py                  ← entry point Flask
│   ├── config.py               ← konfigurasi (env vars)
│   ├── models.py               ← SQLAlchemy models (User, Task)
│   ├── routes/
│   │   ├── auth.py             ← register, login, logout, profil
│   │   └── tasks.py            ← CRUD tugas + health endpoint
│   ├── templates/
│   │   ├── base.html           ← layout utama + navbar
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html      ← daftar tugas + filter + stats
│   │   ├── task_form.html      ← form buat/edit tugas
│   │   └── profile.html        ← simpan Telegram Chat ID
│   └── static/
│       └── style.css           ← dark theme custom CSS
├── scripts/
│   └── notify.py               ← Telegram notifier (untuk CronJob)
└── k8s/
    ├── namespace.yaml
    ├── secret.yaml             ← password + token (tidak di-commit)
    ├── configmap.yaml          ← env vars non-sensitif
    ├── mysql-pvc.yaml          ← PersistentVolumeClaim 2GB
    ├── mysql-deployment.yaml
    ├── mysql-service.yaml      ← ClusterIP (internal only)
    ├── app-deployment.yaml
    ├── app-service.yaml        ← NodePort :30080
    ├── hpa.yaml                ← HPA cpu=50% min=1 max=5
    └── cronjob.yaml            ← notif Telegram tiap 08:00 WIB
```

---

## 7. API Endpoints

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| GET | `/` | ✓ | Redirect ke dashboard |
| GET | `/dashboard` | ✓ | Daftar tugas + filter + stats |
| GET/POST | `/tasks/new` | ✓ | Form buat tugas baru |
| GET/POST | `/tasks/<id>/edit` | ✓ | Form edit tugas |
| POST | `/tasks/<id>/delete` | ✓ | Hapus tugas |
| POST | `/tasks/<id>/status` | ✓ | Update status tugas |
| GET/POST | `/register` | ✗ | Registrasi user baru |
| GET/POST | `/login` | ✗ | Login |
| GET | `/logout` | ✓ | Logout |
| GET/POST | `/profile` | ✓ | Lihat & simpan Telegram Chat ID |
| GET | `/health` | ✗ | Health check (untuk K8s probe) |

---

## 8. Rencana Deployment

### Phase 1 — Local (Windows)
- Docker Compose: Flask + MySQL
- Test semua fitur
- URL: `http://localhost:5000`

### Phase 2 — Kubernetes (Ubuntu VM)
- Build image di Minikube
- Deploy semua manifest K8s
- Enable HPA + metrics-server
- Demo autoscaling
- URL: `http://<minikube-ip>:30080`

### Phase 3 — OpenStack Integration (Portfolio)
- Screenshot OpenStack dashboard sebagai IaaS layer
- Tunjukkan Neutron network, Nova instance, Cinder volume
- Dokumentasikan sebagai arsitektur IaaS → K8s → App

---

## 9. Kriteria Keberhasilan

| Kriteria | Target |
|---|---|
| App dapat diakses via browser | ✓ |
| CRUD tugas berfungsi | ✓ |
| Login/register berfungsi | ✓ |
| HPA scale out saat CPU > 50% | ✓ |
| CronJob berjalan terjadwal | ✓ |
| Telegram notif terkirim | ✓ (setelah setup bot) |
| Screenshot portfolio lengkap | ✓ |
