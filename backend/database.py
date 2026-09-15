import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "maintenance.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ตารางอุปกรณ์ (Equipments)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Operational',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # ตารางใบแจ้งซ่อม (Tickets)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            equipment_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Open',
            assigned_to TEXT,
            created_by TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (equipment_id) REFERENCES equipments(id) ON DELETE CASCADE
        )
    """)

    # ตรวจสอบและ Migration เพิ่มคอลัมน์ created_by ในกรณีตารางเดิมมีอยู่แล้ว
    cursor.execute("PRAGMA table_info(tickets)")
    ticket_columns = [col["name"] for col in cursor.fetchall()]
    if "created_by" not in ticket_columns:
        cursor.execute("ALTER TABLE tickets ADD COLUMN created_by TEXT")


    # ตารางผู้ใช้งานและสิทธิ์ (Users & RBAC)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    # ตรวจสอบและ Seed ข้อมูลตัวอย่างหากยังไม่มีข้อมูล
    cursor.execute("SELECT COUNT(*) as count FROM equipments")
    eq_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()["count"]

    if eq_count == 0 or user_count == 0:
        seed_initial_data(conn)

    conn.close()

def _hash_seed_password(password: str) -> str:
    import hashlib, secrets
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"{salt}${pwd_hash}"

def seed_initial_data(conn: sqlite3.Connection):
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Seed Default Users
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] == 0:
        sample_users = [
            ("USR-001", "admin", _hash_seed_password("admin123"), "ผู้ดูแลระบบ (System Admin)", "admin", now_str),
            ("USR-002", "technician", _hash_seed_password("tech123"), "วิศวกร ธนากร (ช่างเทคนิค)", "technician", now_str),
            ("USR-003", "user", _hash_seed_password("user123"), "สมชาย ใจดี (พนักงานทั่วไป)", "user", now_str),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO users (id, username, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_users)

    # Seed Default Equipments
    cursor.execute("SELECT COUNT(*) as count FROM equipments")
    if cursor.fetchone()["count"] == 0:
        sample_equipments = [
            ("EQ-001", "Main Server Rack Alpha", "Server Room B1", "IT & Infrastructure", "Operational", now_str, now_str),
            ("EQ-002", "Central HVAC Chiller Unit", "Rooftop Plant Room", "HVAC / Facilities", "Needs Maintenance", now_str, now_str),
            ("EQ-003", "Precision CNC Milling Machine", "Production Bay 2", "Machinery", "Under Repair", now_str, now_str),
            ("EQ-004", "Backup Diesel Generator 500kVA", "Power House A", "Electrical", "Operational", now_str, now_str),
            ("EQ-005", "Automated Packaging Conveyor", "Logistics Hall 3", "Production", "Operational", now_str, now_str),
            ("EQ-006", "Enterprise Fiber Optic Core Switch", "Network Operations Center", "IT & Infrastructure", "Needs Maintenance", now_str, now_str),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO equipments (id, name, location, category, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sample_equipments)

    # Seed Default Tickets
    cursor.execute("SELECT COUNT(*) as count FROM tickets")
    if cursor.fetchone()["count"] == 0:
        sample_tickets = [
            ("TK-001", "EQ-002", "อุณหภูมิน้ำหล่อเย็นสูงเกินค่ามาตรฐาน", "ระบบแจ้งเตือนว่า Chiller 2 มีแรงดันน้ำยาหล่อเย็นตกและอุณหภูมิห้องเซิร์ฟเวอร์เริ่มขยับขึ้น", "High", "Open", None, None, now_str, None),
            ("TK-002", "EQ-003", "หัวสปินเดิลมีเสียงผิดปกติและสั่นสะเทือน", "ตรวจพบการสั่นสะเทือนเกิน 4.5 mm/s ที่รอบ 12,000 RPM ช่างกำลังถอดเปลี่ยนตลับลูกปืนแบริ่ง", "Urgent", "In Progress", "วิศวกร ธนากร (ช่างเครื่องกล)", "อะไหล่ตลับลูกปืน SKF มาถึงแล้ว กำลังติดตั้ง", now_str, None),
            ("TK-003", "EQ-006", "พอร์ต SFP+ Uplink 10G หลุดเป็นระยะ", "เกิด Packet Drop ประมาณ 3% ในช่วงเวลา Peak load ต้องทำการตรวจสอบสาย Fiber และทำความสะอาดหัวคอนเน็กเตอร์", "Medium", "Open", None, None, now_str, None),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO tickets (id, equipment_id, title, description, priority, status, assigned_to, notes, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_tickets)

    conn.commit()

