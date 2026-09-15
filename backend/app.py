import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, status, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional, List

from models import (
    EquipmentCreate, EquipmentUpdate, EquipmentResponse,
    TicketCreate, TicketUpdate, TicketResponse,
    DashboardStats, EquipmentStatus, TicketPriority, TicketStatus,
    UserRole, UserRegister, UserLogin, UserResponse, UserRoleUpdate, TokenResponse
)
from service_board import ServiceBoard
from auth import AuthManager

app = FastAPI(
    title="Quick Maintenance Tracker API",
    description="Enterprise-grade RESTful API สำหรับระบบบริหารจัดการงานบำรุงรักษาและแจ้งซ่อมอุปกรณ์ (Quick Maintenance Tracker)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ตั้งค่า CORS Middleware เพื่อให้ Frontend สามารถเรียกใช้งานได้จากทุก Origin/Port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

board = ServiceBoard()
auth_manager = AuthManager()
security = HTTPBearer(auto_error=False)

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Optional[dict]:
    """ตรวจสอบความถูกต้องของ Bearer Token เพื่อดึงข้อมูลผู้ใช้ปัจจุบัน"""
    if not credentials:
        return None
    payload = auth_manager.verify_token(credentials.credentials)
    if not payload:
        return None
    return auth_manager.get_user_by_id(payload.get("user_id"))

def require_auth(current_user: Optional[dict] = Depends(get_current_user)) -> dict:
    """บังคับให้ผู้ใช้ต้องเข้าสู่ระบบก่อน"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="กรุณาเข้าสู่ระบบก่อนดำเนินการ"
        )
    return current_user

def require_admin(current_user: dict = Depends(require_auth)) -> dict:
    """บังคับสิทธิ์เฉพาะผู้ดูแลระบบ (Admin) เท่านั้น"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่มีสิทธิ์เข้าถึงฟังก์ชันนี้"
        )
    return current_user

# ==========================================
# Health Check & System Endpoints
# ==========================================

@app.get("/api/health", tags=["System"], summary="ตรวจสอบสถานะการทำงานของระบบ")
def health_check():
    """Endpoint สำหรับ Frontend หรือ Monitoring ใช้ตรวจสอบสถานะ API"""
    return {
        "status": "healthy",
        "service": "Quick Maintenance Tracker API",
        "version": "2.0.0",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ==========================================
# Authentication & User Endpoints
# ==========================================

@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["Auth"], summary="สมัครสมาชิกใหม่")
def register(data: UserRegister):
    """ลงทะเบียนผู้ใช้งานใหม่เข้าระบบ (กำหนดบทบาทเริ่มต้นได้)"""
    try:
        result = auth_manager.register(
            username=data.username,
            password=data.password,
            full_name=data.full_name,
            role=data.role.value if data.role else "user"
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/api/auth/login", response_model=TokenResponse, tags=["Auth"], summary="เข้าสู่ระบบ")
def login(data: UserLogin):
    """เข้าสู่ระบบด้วย Username และ Password เพื่อรับ Bearer Token"""
    try:
        result = auth_manager.login(username=data.username, password=data.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@app.get("/api/auth/me", response_model=UserResponse, tags=["Auth"], summary="ดูข้อมูลผู้ใช้ปัจจุบัน")
def get_me(user: dict = Depends(require_auth)):
    """ดึงข้อมูลส่วนตัวของผู้ใช้งานที่กำลังล็อกอินอยู่ผ่าน Bearer Token"""
    return user

# ==========================================
# Admin Management Endpoints
# ==========================================

@app.get("/api/admin/users", response_model=List[UserResponse], tags=["Admin"], summary="ดูรายชื่อผู้ใช้งานทั้งหมด (Admin Only)")
def list_users(admin: dict = Depends(require_admin)):
    """ดึงรายชื่อผู้ใช้ทั้งหมดในระบบพร้อมสิทธิ์การใช้งาน (เฉพาะ Admin)"""
    return auth_manager.get_all_users()

@app.patch("/api/admin/users/{user_id}/role", response_model=UserResponse, tags=["Admin"], summary="เปลี่ยนบทบาทผู้ใช้ (Admin Only)")
def update_user_role(user_id: str, data: UserRoleUpdate, admin: dict = Depends(require_admin)):
    """ปรับเปลี่ยนสิทธิ์ผู้ใช้เป็น admin, technician หรือ user (เฉพาะ Admin)"""
    try:
        updated = auth_manager.update_user_role(user_id=user_id, new_role=data.role.value)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบผู้ใช้รหัส '{user_id}'")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/api/admin/users/{user_id}", tags=["Admin"], summary="ลบผู้ใช้งาน (Admin Only)")
def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """ลบบัญชีผู้ใช้งานออกจากระบบ (เฉพาะ Admin)"""
    try:
        success = auth_manager.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบผู้ใช้รหัส '{user_id}'")
        return {"message": f"ลบบัญชีผู้ใช้งานรหัส '{user_id}' เรียบร้อยแล้ว"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==========================================
# Dashboard & Overview Endpoints
# ==========================================

@app.get("/api/stats", response_model=DashboardStats, tags=["Dashboard"], summary="ดึงสถิติภาพรวมระดับผู้บริหาร")
def get_stats():
    """ดึงข้อมูล KPI สรุปสถานะอุปกรณ์และงานแจ้งซ่อมทั้งหมด"""
    return board.get_dashboard_stats()

@app.get("/api/board", tags=["Dashboard"], summary="ดึงข้อมูลกระดานสรุปทั้งหมด")
def get_board():
    """ดึงข้อมูลสรุปทั้งอุปกรณ์ ใบแจ้งซ่อม และสถิติภาพรวม"""
    return board.get_board_summary()

@app.post("/api/reset-demo", tags=["System"], summary="รีเซ็ตข้อมูลตัวอย่างสำหรับ Demo")
def reset_demo():
    """รีเซ็ตฐานข้อมูลและสร้างข้อมูลตัวอย่างใหม่อีกครั้ง"""
    return board.reset_demo_data()

# ==========================================
# Equipment Endpoints
# ==========================================

@app.get("/api/equipments", tags=["Equipments"], summary="ดึงรายการอุปกรณ์ทั้งหมด")
def list_equipments(
    search: Optional[str] = Query(None, description="ค้นหาชื่อ, รหัส หรือสถานที่"),
    category: Optional[str] = Query(None, description="กรองตามหมวดหมู่"),
    status: Optional[str] = Query(None, description="กรองตามสถานะ")
):
    """ค้นหาและดึงรายการอุปกรณ์ตามเงื่อนไข"""
    return board.get_all_equipments(search=search, category=category, status=status)

@app.get("/api/equipments/{equipment_id}", tags=["Equipments"], summary="ดูรายละเอียดอุปกรณ์เดี่ยวและประวัติซ่อม")
def get_equipment(equipment_id: str):
    """ดูรายละเอียดอุปกรณ์พร้อมประวัติใบแจ้งซ่อมที่เกี่ยวข้องทั้งหมด"""
    eq = board.get_equipment_by_id(equipment_id)
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบอุปกรณ์รหัส '{equipment_id}' ในระบบ"
        )
    return eq

@app.post("/api/equipments", status_code=status.HTTP_201_CREATED, tags=["Equipments"], summary="เพิ่มอุปกรณ์ใหม่")
def create_equipment(data: EquipmentCreate, current_user: Optional[dict] = Depends(get_current_user)):
    """ลงทะเบียนอุปกรณ์ใหม่เข้าระบบ (สถานะเริ่มต้นจะเป็น Operational)"""
    eq = board.add_equipment(name=data.name, location=data.location, category=data.category)
    return eq

@app.put("/api/equipments/{equipment_id}", tags=["Equipments"], summary="แก้ไขข้อมูลอุปกรณ์")
def update_equipment(equipment_id: str, data: EquipmentUpdate, current_user: Optional[dict] = Depends(get_current_user)):
    """แก้ไขข้อมูลรายละเอียดอุปกรณ์หรือสถานะ"""
    if current_user and current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="เฉพาะ Admin เท่านั้นที่สามารถแก้ไขข้อมูลอุปกรณ์ได้")
    update_data = data.model_dump(exclude_unset=True)
    eq = board.update_equipment(equipment_id, update_data)
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบอุปกรณ์รหัส '{equipment_id}' ในระบบ"
        )
    return eq

@app.delete("/api/equipments/{equipment_id}", tags=["Equipments"], summary="ลบอุปกรณ์")
def delete_equipment(equipment_id: str, current_user: Optional[dict] = Depends(get_current_user)):
    """ลบอุปกรณ์และประวัติการแจ้งซ่อมที่เกี่ยวข้อง (เฉพาะ Admin)"""
    if current_user and current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="เฉพาะ Admin เท่านั้นที่สามารถลบอุปกรณ์ได้")
    success = board.delete_equipment(equipment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบอุปกรณ์รหัส '{equipment_id}' หรือถูกลบไปแล้ว"
        )
    return {"message": f"ลบอุปกรณ์รหัส '{equipment_id}' เรียบร้อยแล้ว"}

# ==========================================
# Ticket Endpoints
# ==========================================

@app.get("/api/tickets", tags=["Tickets"], summary="ดึงรายการใบแจ้งซ่อมทั้งหมด")
def list_tickets(
    search: Optional[str] = Query(None, description="ค้นหาหัวข้อ รายละเอียด หรือรหัส"),
    status: Optional[str] = Query(None, description="กรองตามสถานะ Open, In Progress, Resolved, Closed"),
    priority: Optional[str] = Query(None, description="กรองตามระดับความเร่งด่วน Low, Medium, High, Urgent"),
    equipment_id: Optional[str] = Query(None, description="กรองตามรหัสอุปกรณ์")
):
    """ค้นหาและดึงรายการใบแจ้งซ่อมตามเงื่อนไข"""
    return board.get_all_tickets(search=search, status=status, priority=priority, equipment_id=equipment_id)

@app.get("/api/tickets/{ticket_id}", tags=["Tickets"], summary="ดูรายละเอียดใบแจ้งซ่อมเดี่ยว")
def get_ticket(ticket_id: str):
    """ดึงข้อมูลใบแจ้งซ่อมตามรหัสที่ระบุ"""
    ticket = board.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบใบแจ้งซ่อมรหัส '{ticket_id}'"
        )
    return ticket

@app.post("/api/tickets", status_code=status.HTTP_201_CREATED, tags=["Tickets"], summary="สร้างใบแจ้งซ่อมใหม่")
def create_ticket(data: TicketCreate, current_user: Optional[dict] = Depends(get_current_user)):
    """สร้างใบแจ้งซ่อมใหม่ และปรับสถานะอุปกรณ์ให้อัตโนมัติ (บันทึกผู้แจ้งซ่อมจากเซสชัน)"""
    creator_name = current_user.get("full_name") if current_user else "ผู้ใช้งานทั่วไป (Kiosk)"
    ticket = board.create_ticket(
        equipment_id=data.equipment_id,
        title=data.title,
        description=data.description,
        priority=data.priority.value,
        created_by=creator_name
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบอุปกรณ์รหัส '{data.equipment_id}' กรุณาตรวจสอบรหัสอุปกรณ์อีกครั้ง"
        )
    return ticket

@app.patch("/api/tickets/{ticket_id}", tags=["Tickets"], summary="อัปเดตสถานะหรือมอบหมายช่าง")
def update_ticket(ticket_id: str, data: TicketUpdate, current_user: Optional[dict] = Depends(get_current_user)):
    """อัปเดตสถานะใบแจ้งซ่อม มอบหมายช่าง หรือบันทึกโน้ตการซ่อม"""
    technician_name = data.technician
    if not technician_name and current_user and current_user.get("role") in ["technician", "admin"]:
        technician_name = current_user.get("full_name")

    ticket = board.update_ticket_status(
        ticket_id=ticket_id,
        status=data.status.value,
        technician=technician_name,
        notes=data.notes
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบใบแจ้งซ่อมรหัส '{ticket_id}'"
        )
    return ticket

@app.delete("/api/tickets/{ticket_id}", tags=["Tickets"], summary="ลบ/ยกเลิกใบแจ้งซ่อม")
def delete_ticket(ticket_id: str, current_user: Optional[dict] = Depends(get_current_user)):
    """ลบใบแจ้งซ่อม และคำนวณสถานะอุปกรณ์ใหม่โดยอัตโนมัติ (เฉพาะ Admin / Technician)"""
    if current_user and current_user.get("role") not in ["admin", "technician"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="เฉพาะ Admin หรือ Technician เท่านั้นที่สามารถลบใบแจ้งซ่อมได้")
    success = board.delete_ticket(ticket_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบใบแจ้งซ่อมรหัส '{ticket_id}'"
        )
    return {"message": f"ลบใบแจ้งซ่อมรหัส '{ticket_id}' เรียบร้อยแล้ว"}


# ==========================================
# Frontend Static Files Mounting
# ==========================================
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

if os.path.isdir(frontend_dir):
    # Mount /frontend สำหรับรองรับกรณีเปิดผ่าน path /frontend
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend_dir")
    # Mount root / สำหรับให้เปิด http://localhost:8000 แล้วเข้าถึง index.html และไฟล์ static ได้ทันที
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend_root")
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {"message": "Quick Maintenance Tracker API v2.0 is running. Visit /docs for API documentation."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)