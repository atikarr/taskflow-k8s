"""
Telegram Notification Script — dijalankan oleh Kubernetes CronJob
Cek tugas yang deadline-nya besok (H-1) dan kirim notifikasi ke Telegram.
"""
import os
import sys
import requests
from datetime import date, timedelta

MYSQL_HOST = os.environ.get("MYSQL_HOST", "taskflow-mysql")
MYSQL_USER = os.environ.get("MYSQL_USER", "taskflow")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "taskflow123")
MYSQL_DB = os.environ.get("MYSQL_DB", "taskflow")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

def get_db_connection():
    import pymysql
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor
    )

def send_telegram(chat_id, message):
    if not BOT_TOKEN:
        print(f"[SKIP] Bot token kosong, pesan tidak dikirim ke {chat_id}")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    return resp.status_code == 200

def main():
    tomorrow = date.today() + timedelta(days=1)
    print(f"[INFO] Cek tugas deadline H-1: {tomorrow}")

    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"[ERROR] Gagal koneksi database: {e}")
        sys.exit(1)

    with conn:
        with conn.cursor() as cursor:
            # Ambil tugas deadline besok yang belum selesai, beserta telegram_chat_id user
            cursor.execute("""
                SELECT t.title, t.priority, t.deadline,
                       u.username, u.telegram_chat_id
                FROM tasks t
                JOIN users u ON (t.assigned_to = u.id OR (t.assigned_to IS NULL AND t.user_id = u.id))
                WHERE t.deadline = %s
                  AND t.status != 'done'
                  AND u.telegram_chat_id IS NOT NULL
            """, (tomorrow,))
            tasks = cursor.fetchall()

    if not tasks:
        print("[INFO] Tidak ada tugas deadline besok.")
        return

    print(f"[INFO] Ditemukan {len(tasks)} tugas deadline besok.")
    for task in tasks:
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(task["priority"], "")
        message = (
            f"⏰ <b>Reminder Deadline H-1</b>\n\n"
            f"📋 <b>{task['title']}</b>\n"
            f"{priority_icon} Prioritas: {task['priority'].capitalize()}\n"
            f"📅 Deadline: <b>{task['deadline'].strftime('%d %B %Y')}</b>\n\n"
            f"Segera selesaikan tugasmu! — TaskFlow K8s"
        )
        success = send_telegram(task["telegram_chat_id"], message)
        status = "✅ Terkirim" if success else "❌ Gagal"
        print(f"[{status}] → {task['username']}: {task['title']}")

if __name__ == "__main__":
    main()
