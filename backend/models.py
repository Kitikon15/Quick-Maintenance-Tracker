from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum

class EquipmentStatus(str, Enum):
    OPERATIONAL = "Operational"
    NEEDS_MAINTENANCE = "Needs Maintenance"
    UNDER_REPAIR = "Under Repair"

class TicketPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"

class TicketStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"

class EquipmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="ชื่ออุปกรณ์")
    location: str = Field(..., min_length=1, max_length=100, description="สถานที่ติดตั้ง")
    category: str = Field(..., min_length=1, max_length=50, description="หมวดหมู่อุปกรณ์")

    @field_validator("name", "location", "category")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("ค่าต้องไม่เป็นช่องว่าง")
        return v

class EquipmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    status: Optional[EquipmentStatus] = None

class TicketCreate(BaseModel):
    equipment_id: str = Field(..., description="รหัสอุปกรณ์ เช่น EQ-001")
    title: str = Field(..., min_length=2, max_length=150, description="หัวข้อปัญหา")
    description: str = Field(..., min_length=1, max_length=1000, description="รายละเอียดอาการเสีย")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM, description="ระดับความสำคัญ")

    @field_validator("equipment_id", "title", "description")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("ค่าต้องไม่เป็นช่องว่าง")
        return v

class TicketUpdate(BaseModel):
    status: TicketStatus = Field(..., description="สถานะใหม่ของใบแจ้งซ่อม")
    technician: Optional[str] = Field(None, max_length=100, description="ชื่อช่างผู้รับผิดชอบ")
    notes: Optional[str] = Field(None, max_length=500, description="บันทึกเพิ่มเติมหรือวิธีแก้ไข")

class EquipmentResponse(BaseModel):
    id: str
    name: str
    location: str
    category: str
    status: str
    created_at: str
    updated_at: str

class TicketResponse(BaseModel):
    id: str
    equipment_id: str
    equipment_name: Optional[str] = None
    equipment_location: Optional[str] = None
    title: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None


class DashboardStats(BaseModel):
    total_equipments: int
    operational_count: int
    needs_maintenance_count: int
    under_repair_count: int
    uptime_percentage: float
    total_tickets: int
    open_tickets_count: int
    in_progress_tickets_count: int
    resolved_tickets_count: int
    urgent_tickets_count: int

# ==========================================
# User & Authentication Models
# ==========================================

class UserRole(str, Enum):
    ADMIN = "admin"
    TECHNICIAN = "technician"
    USER = "user"

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="ชื่อบัญชีผู้ใช้")
    password: str = Field(..., min_length=4, max_length=100, description="รหัสผ่าน (ขั้นต่ำ 4 ตัวอักษร)")
    full_name: str = Field(..., min_length=2, max_length=100, description="ชื่อ-นามสกุลจริง")
    role: Optional[UserRole] = Field(default=UserRole.USER, description="บทบาทผู้ใช้งาน")

    @field_validator("username", "full_name")
    @classmethod
    def strip_str(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("ค่าต้องไม่เป็นช่องว่าง")
        return v

class UserLogin(BaseModel):
    username: str = Field(..., min_length=1, description="ชื่อบัญชีผู้ใช้")
    password: str = Field(..., min_length=1, description="รหัสผ่าน")

class UserResponse(BaseModel):
    id: str
    username: str
    full_name: str
    role: str
    created_at: str

class UserRoleUpdate(BaseModel):
    role: UserRole = Field(..., description="สิทธิ์ใหม่ของผู้ใช้")

class TokenResponse(BaseModel):
    token: str
    user: UserResponse

