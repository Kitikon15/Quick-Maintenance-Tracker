import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "maintenance.db")

ALLOWED_CATEGORIES = ["Notebook", "Computer", "Mobile", "iPhone", "iPad"]

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ตารางอุปกรณ์ (Equipments) - เฉพาะ Notebook, Computer, Mobile, iPhone, iPad
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Operational',
            image_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # ตรวจสอบและ Migration เพิ่ม image_url ใน equipments
    cursor.execute("PRAGMA table_info(equipments)")
    eq_cols = [col["name"] for col in cursor.fetchall()]
    if "image_url" not in eq_cols:
        cursor.execute("ALTER TABLE equipments ADD COLUMN image_url TEXT")

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
            image_before TEXT,
            image_after TEXT,
            device_category TEXT,
            device_model TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            estimated_cost REAL DEFAULT 0,
            estimated_days INTEGER DEFAULT 1,
            rating INTEGER,
            review_comment TEXT,
            FOREIGN KEY (equipment_id) REFERENCES equipments(id) ON DELETE CASCADE
        )
    """)

    # ตรวจสอบและ Migration สำหรับคอลัมน์ใหม่ใน tickets
    cursor.execute("PRAGMA table_info(tickets)")
    ticket_columns = [col["name"] for col in cursor.fetchall()]
    
    new_cols = [
        ("created_by", "TEXT"),
        ("image_before", "TEXT"),
        ("image_after", "TEXT"),
        ("device_category", "TEXT"),
        ("device_model", "TEXT"),
        ("customer_name", "TEXT"),
        ("customer_phone", "TEXT"),
        ("estimated_cost", "REAL DEFAULT 0"),
        ("estimated_days", "INTEGER DEFAULT 1"),
        ("rating", "INTEGER"),
        ("review_comment", "TEXT")
    ]
    for col_name, col_type in new_cols:
        if col_name not in ticket_columns:
            cursor.execute(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type}")

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

    # ตรวจสอบว่ามีข้อมูลตัวอย่างเดิมที่ไม่ใช่อุปกรณ์ 5 ชนิดหรือไม่
    cursor.execute("SELECT COUNT(*) as count FROM equipments WHERE category NOT IN ('Notebook', 'Computer', 'Mobile', 'iPhone', 'iPad')")
    invalid_category_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM equipments")
    eq_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()["count"]

    if eq_count == 0 or user_count == 0 or invalid_category_count > 0:
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

    # ล้างข้อมูลเดิมที่อาจไม่สอดคล้องกับ 5 หมวดหมู่ใหม่
    cursor.execute("DELETE FROM tickets")
    cursor.execute("DELETE FROM equipments")

    # Seed Default Users
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] == 0:
        sample_users = [
            ("USR-001", "admin", _hash_seed_password("admin123"), "ผู้ดูแลระบบ (System Admin)", "admin", now_str),
            ("USR-002", "technician", _hash_seed_password("tech123"), "วิศวกร ธนากร (ช่างเทคนิคอาวุโส)", "technician", now_str),
            ("USR-003", "user", _hash_seed_password("user123"), "สมชาย ใจดี (ลูกค้าสมาชิก)", "user", now_str),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO users (id, username, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_users)

    # Seed Equipments (เฉพาะ 5 ชนิด: Notebook, Computer, Mobile, iPhone, iPad)
    sample_equipments = [
        ("EQ-001", "Asus ROG Strix G15 (Gaming Notebook)", "เคาน์เตอร์ซ่อมด่วน 1", "Notebook", "Needs Maintenance", "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop&q=80", now_str, now_str),
        ("EQ-002", "MacBook Pro 14 M2 Pro (Space Gray)", "โต๊ะตรวจเช็ค Apple Lab", "Notebook", "Under Repair", "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80", now_str, now_str),
        ("EQ-003", "Gaming PC Intel i7-13700KF RTX 4070", "โซนทดสอบ Benchmark PC", "Computer", "Operational", "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=600&auto=format&fit=crop&q=80", now_str, now_str),
        ("EQ-004", "iPhone 14 Pro Max 256GB Deep Purple", "ตู้จัดเก็บมือถือลูกค้า B2", "iPhone", "Needs Maintenance", "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=600&auto=format&fit=crop&q=80", now_str, now_str),
        ("EQ-005", "iPad Air 5 (M1) Wi-Fi 64GB Blue", "โต๊ะตรวจซ่อมแท็บเล็ต C1", "iPad", "Under Repair", "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=80", now_str, now_str),
        ("EQ-006", "Samsung Galaxy S23 Ultra Phantom Black", "เคาน์เตอร์ตรวจเช็ค Mobile 2", "Mobile", "Operational", "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=600&auto=format&fit=crop&q=80", now_str, now_str),
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO equipments (id, name, location, category, status, image_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, sample_equipments)

    # Seed Tickets พร้อมภาพ Before/After และตัวอย่าง Review
    sample_tickets = [
        (
            "TK-001", "EQ-001", "พัดลมระบายความร้อนเสียงดังและเครื่องร้อนจัดตัดดับ",
            "พัดลมฝั่ง GPU มีเสียงแกว่งเสียดสีอย่างหนัก อุณหภูมิพุ่งแตะ 96°C เครื่องตัดดับขณะเล่นเกมหรือเรนเดอร์งาน",
            "High", "In Progress", "วิศวกร ธนากร (ช่างเทคนิคอาวุโส)", "สมชาย ใจดี",
            "สั่งอะไหล่พัดลมแท้ Asus ROG แล้ว กำลังทำความสะอาดฮีทไปป์และเปลี่ยนซิลิโคน Honeywell PTM7950",
            now_str, None,
            "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=600&auto=format&fit=crop&q=80",
            None,
            "Notebook", "Asus ROG Strix G15", "คุณธนพล", "081-234-5678", 1600.0, 2, None, None
        ),
        (
            "TK-002", "EQ-004", "หน้าจอแตกร้าว ทัชสกรีนรวน และแบตเตอรี่เสื่อมสภาพ",
            "เครื่องตกกระแทกพื้นมุมขวาบน จอแตกร้าวเป็นเส้น ทัชสกรีนบางจุดไม่ตอบสนอง สุขภาพแบตเตอรี่เหลือ 72% ลูกค้าต้องการเปลี่ยนจอแท้และแบตเตอรี่ใหม่",
            "Urgent", "Open", None, "คุณปิยะพร",
            "ประเมินราคาเรียบร้อย ลูกค้าอนุมัติซ่อม รอช่างจัดเตรียมหน้าจอ OLED แท้และกาวกันน้ำ",
            now_str, None,
            "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=600&auto=format&fit=crop&q=80",
            None,
            "iPhone", "iPhone 14 Pro Max", "คุณปิยะพร", "089-987-6543", 6500.0, 1, None, None
        ),
        (
            "TK-003", "EQ-005", "พอร์ต USB-C ชาร์จไฟไม่เข้า และหน้าจอสัมผัสกระตุก",
            "พอร์ตชาร์จหลวมมาก เสียบสายชาร์จแล้วติดๆ ดับๆ ตรวจสอบพบขั้วพินภายในหักงอ",
            "Medium", "In Progress", "วิศวกร ธนากร (ช่างเทคนิคอาวุโส)", "คุณวรวิทย์",
            "กำลังถอดบอร์ดเพื่อเชื่อมเปลี่ยนพอร์ต Type-C ใหม่ พร้อมทดสอบกระแสไฟชาร์จแบบ Power Delivery",
            now_str, None,
            "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=80",
            None,
            "iPad", "iPad Air 5", "คุณวรวิทย์", "086-555-1234", 1900.0, 2, None, None
        ),
        (
            "TK-004", "EQ-003", "คอมเปิดติดแต่ไม่มีภาพขึ้นจอ (No Display) ตรวจพบการ์ดจอมีฝุ่นหนาและพัดลมติดขัด",
            "ไฟ Debug LED บนเมนบอร์ดค้างที่ VGA ไม่มีสัญญาณภาพออก HDMI/DisplayPort",
            "High", "Resolved", "วิศวกร ธนากร (ช่างเทคนิคอาวุโส)", "คุณกิตติศักดิ์",
            "ทำความสะอาดพอร์ต PCIe เปลี่ยน thermal pad การ์ดจอ RTX 4070 และอัปเดต BIOS เมนบอร์ด ทดสอบผ่าน Furmark 2 ชม. ไม่พบปัญหา",
            now_str, now_str,
            "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=600&auto=format&fit=crop&q=80",
            "Computer", "Gaming PC Core i7 RTX 4070", "คุณกิตติศักดิ์", "082-111-9988", 1200.0, 1,
            5, "ช่างตรวจเช็คเร็วและละเอียดมากครับ มีภาพเปรียบเทียบก่อนซ่อมและหลังซ่อมให้ดูชัดเจน คอมกลับมาเล่นเกมได้ลื่นเหมือนใหม่ ประทับใจมาก!"
        )
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO tickets (
            id, equipment_id, title, description, priority, status, assigned_to, created_by, notes,
            created_at, resolved_at, image_before, image_after, device_category, device_model,
            customer_name, customer_phone, estimated_cost, estimated_days, rating, review_comment
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sample_tickets)

    conn.commit()
