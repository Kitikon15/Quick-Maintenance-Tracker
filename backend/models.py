from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum

class DeviceCategory(str, Enum):
    NOTEBOOK = "Notebook"
    COMPUTER = "Computer"
    MOBILE = "Mobile"
    IPHONE = "iPhone"
    IPAD = "iPad"

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
    name: str = Field(..., min_length=1, max_length=100, description="ชื่ออุปกรณ์ / รุ่น")
    location: str = Field(..., min_length=1, max_length=100, description="สถานที่จัดเก็บ / เคาน์เตอร์")
    category: DeviceCategory = Field(..., description="ประเภทอุปกรณ์ (จำกัดเฉพาะ Notebook, Computer, Mobile, iPhone, iPad)")
    image_url: Optional[str] = Field(None, description="URL รูปภาพอุปกรณ์")

    @field_validator("name", "location")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("ค่าต้องไม่เป็นช่องว่าง")
        return v

class EquipmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[DeviceCategory] = None
    status: Optional[EquipmentStatus] = None
    image_url: Optional[str] = None

class TicketCreate(BaseModel):
    equipment_id: Optional[str] = Field(None, description="รหัสอุปกรณ์ เช่น EQ-001 (หากไม่ระบุ ระบบจะค้นหาหรือสร้างให้อัตโนมัติ)")
    device_category: DeviceCategory = Field(..., description="ประเภทอุปกรณ์ที่รับซ่อม (เฉพาะ Notebook, Computer, Mobile, iPhone, iPad)")
    device_model: Optional[str] = Field(None, max_length=150, description="ชื่อรุ่นอุปกรณ์ เช่น MacBook Pro M2, iPhone 14 Pro")
    title: str = Field(..., min_length=2, max_length=150, description="หัวข้อปัญหา / อาการเสียโดยย่อ")
    description: str = Field(..., min_length=1, max_length=1000, description="รายละเอียดอาการเสีย")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM, description="ระดับความสำคัญ")
    image_before: Optional[str] = Field(None, description="URL รูปภาพอุปกรณ์ตอนนำมาส่งซ่อม (Before)")
    customer_name: Optional[str] = Field(None, max_length=100, description="ชื่อลูกค้า / ผู้ส่งซ่อม")
    customer_phone: Optional[str] = Field(None, max_length=50, description="เบอร์โทรศัพท์ติดต่อ")
    estimated_cost: Optional[float] = Field(default=0.0, description="ราคาประเมินเบื้องต้น (บาท)")
    estimated_days: Optional[int] = Field(default=1, description="ระยะเวลาซ่อมประเมิน (วัน)")

    @field_validator("title", "description")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("ค่าต้องไม่เป็นช่องว่าง")
        return v

class TicketUpdate(BaseModel):
    status: TicketStatus = Field(..., description="สถานะใหม่ของใบแจ้งซ่อม")
    technician: Optional[str] = Field(None, max_length=100, description="ชื่อช่างผู้รับผิดชอบ")
    notes: Optional[str] = Field(None, max_length=1000, description="บันทึกผลการซ่อม อะไหล่ที่เปลี่ยน หรือวิธีแก้ไข")
    image_after: Optional[str] = Field(None, description="URL รูปภาพหลังซ่อมเสร็จสิ้น (After)")
    estimated_cost: Optional[float] = Field(None, description="ราคาซ่อมจริงหรือปรับปรุง")
    estimated_days: Optional[int] = Field(None, description="ระยะเวลาซ่อมจริง")

class TicketReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="คะแนนความพึงพอใจ 1 ถึง 5 ดาว")
    review_comment: str = Field(..., min_length=2, max_length=1000, description="ข้อความรีวิวความประทับใจ")

class EquipmentResponse(BaseModel):
    id: str
    name: str
    location: str
    category: str
    status: str
    image_url: Optional[str] = None
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
    image_before: Optional[str] = None
    image_after: Optional[str] = None
    device_category: Optional[str] = None
    device_model: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    estimated_cost: Optional[float] = 0.0
    estimated_days: Optional[int] = 1
    rating: Optional[int] = None
    review_comment: Optional[str] = None

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
    role: Optional[UserRole] = Field(default=UserRole.USER, description="บทบาทผู้ใช้งาน (ค่าเริ่มต้นคือ user)")
    admin_code: Optional[str] = Field(None, description="รหัสยืนยันสำหรับขอสิทธิ์ Admin หรือ Technician (ADMIN@2026)")

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

class AdminPasscodeVerify(BaseModel):
    passcode: str = Field(..., min_length=1, description="รหัสความปลอดภัยสำหรับเข้าส่วน Admin")

# ==========================================
# AI Consultant Models
# ==========================================

class AIConsultRequest(BaseModel):
    device_category: Optional[str] = Field(None, description="ประเภทอุปกรณ์ Notebook, Computer, Mobile, iPhone, iPad")
    device_model: Optional[str] = Field(None, description="รุ่นของอุปกรณ์")
    issue_description: str = Field(..., min_length=2, max_length=1000, description="อาการเสียหรือคำถามที่ต้องการปรึกษา")

class AIConsultResponse(BaseModel):
    device_category: str
    symptom: str
    diagnosis: str
    estimated_cost_range: str
    estimated_days_range: str
    solutions: List[str]
    recommendations: str
    store_info: str
