from datetime import datetime
from typing import Dict, Any, Optional

class User:
    """
    User Class (Object-Oriented Programming)
    รับผิดชอบ: ข้อมูลผู้ใช้งานในระบบ, การตรวจสอบบทบาทและสิทธิ์ (Role-Based Access)
    """
    def __init__(self, user_id: str, username: str, full_name: str, role: str = "user", created_at: Optional[str] = None):
        self.__id = user_id
        self.__username = username
        self.__full_name = full_name
        self.__role = role.lower()  # 'admin', 'technician', 'user'
        self.__created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Getters (Encapsulation)
    def get_id(self) -> str:
        return self.__id

    def get_username(self) -> str:
        return self.__username

    def get_full_name(self) -> str:
        return self.__full_name

    def get_role(self) -> str:
        return self.__role

    def get_created_at(self) -> str:
        return self.__created_at

    # Role Checks
    def is_admin(self) -> bool:
        return self.__role == "admin"

    def is_technician(self) -> bool:
        return self.__role in ["technician", "admin"]

    def set_role(self, new_role: str) -> bool:
        valid_roles = ["admin", "technician", "user"]
        if new_role.lower() in valid_roles:
            self.__role = new_role.lower()
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.__id,
            "username": self.__username,
            "full_name": self.__full_name,
            "role": self.__role,
            "created_at": self.__created_at
        }
