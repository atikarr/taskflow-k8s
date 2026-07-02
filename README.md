# ☸ TaskFlow K8s

> Sistem manajemen tugas kuliah cloud-native — Flask + MySQL di atas Kubernetes dengan HPA autoscaling, di-deploy pada infrastruktur OpenStack (IaaS).

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-HPA-326CE5?logo=kubernetes&logoColor=white)

## ✨ Fitur

- **Kanban Board** — drag & drop tugas antar kolom (To Do / In Progress / Done)
- **Real-time sync** — perubahan anggota tim muncul otomatis (polling 10 detik)
- **Statistik & grafik** — breakdown status, prioritas, dan per mata kuliah (Chart.js)
- **Multi-user** — register/login, assign tugas ke anggota tim
- **Materi kuliah** — upload file (PDF/PPT/dll) atau simpan link, filter per matkul
- **Komentar** — diskusi di dalam tiap tugas
- **Notifikasi Telegram** — reminder otomatis H-1 deadline via Kubernetes CronJob
- **Dark/light mode** — toggle tema, tersimpan di browser
- **Pencarian & filter** — cari tugas/materi, filter per matkul & prioritas

## 🏗 Arsitektur

```
┌───────────────────────────────────────────────┐
│ SaaS   → TaskFlow (yang dipakai user)         │
├───────────────────────────────────────────────┤
│ PaaS   → Kubernetes (orchestration + HPA)     │
├───────────────────────────────────────────────┤
│ IaaS   → OpenStack DevStack (VM + network)    │
├───────────────────────────────────────────────┤
│ Fisik  → VirtualBox VM (Ubuntu 24.04)         │
└───────────────────────────────────────────────┘
```

```
[Browser] → [NodePort :30080] → [Flask Pods (HPA 1-5)] → [MySQL + PVC]
                                       ↑
                              [HPA: CPU baseline 50%]
[CronJob 08:00 WIB] → cek deadline H-1 → [Telegram Bot API]
```

## 🚀 Menjalankan Lokal (Docker Compose)

```bash
docker-compose up --build -d
# App        → http://localhost:5001
# phpMyAdmin → http://localhost:8081
```

## ☸ Deploy ke Kubernetes (Minikube)

```bash
# Build image di dalam Minikube
eval $(minikube docker-env)
docker build -t taskflow-k8s:latest .

# Deploy semua manifest
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml -f k8s/configmap.yaml
kubectl apply -f k8s/mysql-pvc.yaml -f k8s/uploads-pvc.yaml
kubectl apply -f k8s/mysql-deployment.yaml -f k8s/mysql-service.yaml
kubectl apply -f k8s/app-deployment.yaml -f k8s/app-service.yaml
kubectl apply -f k8s/hpa.yaml -f k8s/cronjob.yaml

# Enable metrics untuk HPA
minikube addons enable metrics-server

# Akses app
minikube service taskflow-app -n taskflow --url
```

## 📈 Demo Autoscaling (HPA)

```bash
# Pantau HPA
kubectl get hpa -n taskflow -w

# Generate beban CPU
kubectl run load -n taskflow --image=busybox --restart=Never -- \
  /bin/sh -c "while true; do wget -q -O- http://taskflow-app; done"

# Pod akan bertambah otomatis saat CPU > 50% (baseline)
```

## 🗂 Struktur Proyek

```
├── app/               # Flask application
│   ├── models.py      # User, Task, Material, Comment
│   ├── routes/        # auth, tasks (+ API), materials
│   ├── templates/     # Jinja2 (kanban, charts, dark mode)
│   └── static/        # CSS custom
├── k8s/               # Kubernetes manifests (11 file)
├── scripts/notify.py  # Telegram notifier (CronJob)
├── Dockerfile
├── docker-compose.yml # Dev lokal: app + MySQL + phpMyAdmin
└── PRD.md             # Product Requirements Document
```

## 🔒 Catatan Keamanan

Kredensial di `k8s/secret.yaml` dan `docker-compose.yml` adalah **placeholder development**. Untuk production: ganti semua password, isi token Telegram via secret management yang proper (Vault/Sealed Secrets), dan aktifkan TLS.

---

*Proyek mata kuliah Keamanan Komputasi Awan — PoltekSSN*
