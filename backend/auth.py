import sqlite3
import hashlib
import hmac
import secrets
import json
import base64
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from database import get_connection
from user import User

SECRET_KEY = "quick-maintenance-tracker-secret-key-enterprise-2026"
TOKEN_EXPIRATION_SECONDS = 86400 * 7  # 7 days

class AuthManager:
    """
    AuthManager Class
    จัดการระบบความปลอดภัย: การแฮชรหัสผ่าน, การออกและตรวจสอบ Token, การจัดการบัญชีผู้ใช้งาน
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """แฮชรหัสผ่านด้วย PBKDF2 HMAC SHA-256 พร้อม Salt สุ่ม 16 bytes"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        ).hex()
        return f"{salt}${pwd_hash}"

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """ตรวจสอบความถูกต้องของรหัสผ่านเทียบกับแฮชที่บันทึกไว้"""
        try:
            salt, orig_hash = stored_hash.split("$")
            new_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                100000
            ).hex()
            return hmac.compare_digest(orig_hash, new_hash)
        except Exception:
            return False

    @staticmethod
    def generate_token(user_id: str, username: str, role: str) -> str:
        """สร้าง HMAC-SHA256 Signed Token ที่ปลอดภัยและไม่ต้องพึ่งพาไลบรารีภายนอก"""
        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": int(time.time()) + TOKEN_EXPIRATION_SECONDS
        }
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode('utf-8').rstrip('=')

        signature = hmac.new(
            SECRET_KEY.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return f"{payload_b64}.{signature}"

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """ตรวจสอบความถูกต้องและวันหมดอายุของ Token"""
        try:
            parts = token.strip().split(".")
            if len(parts) != 2:
                return None

            payload_b64, signature = parts

            # ตรวจสอบลายเซ็น HMAC
            expected_sig = hmac.new(
                SECRET_KEY.encode('utf-8'),
                payload_b64.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_sig):
                return None

            # ถอดรหัส JSON Payload
            padded_b64 = payload_b64 + '=' * (-len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(padded_b64)
            payload = json.loads(payload_bytes.decode('utf-8'))

            # ตรวจสอบเวลาหมดอายุ
            if payload.get("exp", 0) < int(time.time()):
                return None

            return payload
        except Exception:
            return None

    def _generate_user_id(self, cursor: sqlite3.Cursor) -> str:
        cursor.execute("SELECT id FROM users WHERE id LIKE 'USR-%' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            try:
                num = int(row["id"].split("-")[1]) + 1
                return f"USR-{num:03d}"
            except (IndexError, ValueError):
                pass
        cursor.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()["count"] + 1
        return f"USR-{count:03d}"

    def register(self, username: str, password: str, full_name: str, role: str = "user") -> Dict[str, Any]:
        username = username.strip().lower()
        full_name = full_name.strip()
        role = role.strip().lower()

        if role not in ["admin", "technician", "user"]:
            role = "user"

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            raise ValueError(f"ชื่อผู้ใช้งาน '{username}' มีอยู่ในระบบแล้ว กรุณาใช้ชื่ออื่น")

        user_id = self._generate_user_id(cursor)
        password_hash = self.hash_password(password)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO users (id, username, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username, password_hash, full_name, role, now_str))
        conn.commit()
        conn.close()

        token = self.generate_token(user_id, username, role)
        user_obj = User(user_id, username, full_name, role, now_str)

        return {
            "token": token,
            "user": user_obj.to_dict()
        }

    def login(self, username: str, password: str) -> Dict[str, Any]:
        username = username.strip().lower()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError("ไม่พบบัญชีผู้ใช้งานนี้ในระบบ")

        if not self.verify_password(password, row["password_hash"]):
            raise ValueError("รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")

        user_obj = User(row["id"], row["username"], row["full_name"], row["role"], row["created_at"])
        token = self.generate_token(row["id"], row["username"], row["role"])

        return {
            "token": token,
            "user": user_obj.to_dict()
        }

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name, role, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        user_obj = User(row["id"], row["username"], row["full_name"], row["role"], row["created_at"])
        return user_obj.to_dict()

    def get_all_users(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name, role, created_at FROM users ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()

        return [
            User(r["id"], r["username"], r["full_name"], r["role"], r["created_at"]).to_dict()
            for r in rows
        ]

    def update_user_role(self, user_id: str, new_role: str) -> Optional[Dict[str, Any]]:
        new_role = new_role.lower()
        if new_role not in ["admin", "technician", "user"]:
            raise ValueError(f"บทบาท '{new_role}' ไม่ถูกต้อง (ต้องเป็น admin, technician หรือ user)")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        # ป้องกันการเปลี่ยน role ของ admin คนสุดท้าย
        if row["role"] == "admin" and new_role != "admin":
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
            admin_count = cursor.fetchone()["count"]
            if admin_count <= 1:
                conn.close()
                raise ValueError("ไม่สามารถลดสิทธิ์ผู้ดูแลระบบคนสุดท้ายได้")

        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()

        cursor.execute("SELECT id, username, full_name, role, created_at FROM users WHERE id = ?", (user_id,))
        updated_row = cursor.fetchone()
        conn.close()

        return User(
            updated_row["id"],
            updated_row["username"],
            updated_row["full_name"],
            updated_row["role"],
            updated_row["created_at"]
        ).to_dict()

    def delete_user(self, user_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        if row["role"] == "admin":
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
            admin_count = cursor.fetchone()["count"]
            if admin_count <= 1:
                conn.close()
                raise ValueError("ไม่สามารถลบบัญชีผู้ดูแลระบบคนสุดท้ายได้")

        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
