import os
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, status, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any

from models import (
    EquipmentCreate, EquipmentUpdate, EquipmentResponse,
    TicketCreate, TicketUpdate, TicketResponse, TicketReviewCreate,
    DashboardStats, EquipmentStatus, TicketPriority, TicketStatus, DeviceCategory,
    UserRole, UserRegister, UserLogin, UserResponse, UserRoleUpdate, TokenResponse,
    AdminPasscodeVerify, AIConsultRequest, AIConsultResponse
)
from service_board import ServiceBoard
from auth import AuthManager

app = FastAPI(
    title="Quick Maintenance Tracker API - Tech Repair Edition",
    description="Enterprise RESTful API สำหรับระบบบริการและบริหารจัดการงานซ่อม Notebook, Computer, Mobile, iPhone, iPad",
    version="2.5.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ตั้งค่า CORS Middleware
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
    """บังคับให้ผู้ใช้ต้องเข้าสู่ระบบก่อนดำเนินการ"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="กรุณาสมัครสมาชิกหรือเข้าสู่ระบบก่อนดำเนินการแก้ไขหรือจัดการข้อมูล"
        )
    return current_user

def require_admin(current_user: dict = Depends(require_auth)) -> dict:
    """บังคับสิทธิ์เฉพาะผู้ดูแลระบบ (Admin) เท่านั้น"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่มีสิทธิ์เข้าถึงส่วนนี้"
        )
    return current_user

def require_tech_or_admin(current_user: dict = Depends(require_auth)) -> dict:
    """บังคับสิทธิ์ช่างเทคนิค (Technician) หรือ Admin เท่านั้นในการแก้ไขงานซ่อม"""
    if current_user.get("role") not in ["admin", "technician"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="เฉพาะช่างเทคนิคหรือผู้ดูแลระบบเท่านั้นที่สามารถอัปเดตสถานะงานซ่อมได้"
        )
    return current_user

# ==========================================
# Health Check & System Endpoints
# ==========================================

@app.get("/api/health", tags=["System"], summary="ตรวจสอบสถานะการทำงานของระบบ")
def health_check():
    return {
        "status": "healthy",
        "service": "Quick Maintenance Tracker (Tech Repair Portal)",
        "version": "2.5.0",
        "accepted_devices": ["Notebook", "Computer", "Mobile", "iPhone", "iPad"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ==========================================
# Authentication & User Endpoints
# ==========================================

@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["Auth"], summary="สมัครสมาชิกใหม่")
def register(data: UserRegister):
    """ลงทะเบียนผู้ใช้งานใหม่เข้าระบบ (หากต้องการสิทธิ์ admin/technician ต้องมี admin_code)"""
    try:
        result = auth_manager.register(
            username=data.username,
            password=data.password,
            full_name=data.full_name,
            role=data.role.value if data.role else "user",
            admin_code=data.admin_code
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
    return user

@app.post("/api/admin/verify-passcode", tags=["Admin"], summary="ยืนยันรหัสความปลอดภัยสำหรับเข้าส่วน Admin")
def verify_admin_passcode(data: AdminPasscodeVerify):
    is_valid = auth_manager.verify_admin_passcode(data.passcode)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="รหัสความปลอดภัย Admin ไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"
        )
    return {"status": "success", "message": "ยืนยันรหัส Admin ถูกต้อง อนุญาตให้เข้าถึง"}

# ==========================================
# Admin Management Endpoints
# ==========================================

@app.get("/api/admin/users", response_model=List[UserResponse], tags=["Admin"], summary="ดูรายชื่อผู้ใช้งานทั้งหมด (Admin Only)")
def list_users(admin: dict = Depends(require_admin)):
    return auth_manager.get_all_users()

@app.patch("/api/admin/users/{user_id}/role", response_model=UserResponse, tags=["Admin"], summary="เปลี่ยนบทบาทผู้ใช้ (Admin Only)")
def update_user_role(user_id: str, data: UserRoleUpdate, admin: dict = Depends(require_admin)):
    try:
        updated = auth_manager.update_user_role(user_id=user_id, new_role=data.role.value)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบผู้ใช้รหัส '{user_id}'")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/api/admin/users/{user_id}", tags=["Admin"], summary="ลบผู้ใช้งาน (Admin Only)")
def delete_user(user_id: str, admin: dict = Depends(require_admin)):
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

@app.get("/api/stats", response_model=DashboardStats, tags=["Dashboard"], summary="ดึงสถิติภาพรวม")
def get_stats():
    return board.get_dashboard_stats()

@app.get("/api/board", tags=["Dashboard"], summary="ดึงข้อมูลกระดานสรุปทั้งหมด")
def get_board():
    return board.get_board_summary()

@app.post("/api/reset-demo", tags=["System"], summary="รีเซ็ตข้อมูลตัวอย่างสำหรับ Demo (Admin Only)")
def reset_demo(admin: dict = Depends(require_admin)):
    return board.reset_demo_data()

# ==========================================
# Equipment Endpoints (เฉพาะ 5 ประเภทเท่านั้น)
# ==========================================

@app.get("/api/equipments", tags=["Equipments"], summary="ดึงรายการอุปกรณ์ทั้งหมด")
def list_equipments(
    search: Optional[str] = Query(None, description="ค้นหาชื่อ, รหัส หรือสถานที่"),
    category: Optional[str] = Query(None, description="กรองตามหมวดหมู่ (Notebook, Computer, Mobile, iPhone, iPad)"),
    status: Optional[str] = Query(None, description="กรองตามสถานะ")
):
    return board.get_all_equipments(search=search, category=category, status=status)

@app.get("/api/equipments/{equipment_id}", tags=["Equipments"], summary="ดูรายละเอียดอุปกรณ์เดี่ยว")
def get_equipment(equipment_id: str):
    eq = board.get_equipment_by_id(equipment_id)
    if not eq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบอุปกรณ์รหัส '{equipment_id}'")
    return eq

@app.post("/api/equipments", status_code=status.HTTP_201_CREATED, tags=["Equipments"], summary="เพิ่มอุปกรณ์ใหม่ (Admin Only)")
def create_equipment(data: EquipmentCreate, admin: dict = Depends(require_admin)):
    try:
        eq = board.add_equipment(
            name=data.name,
            location=data.location,
            category=data.category.value,
            image_url=data.image_url
        )
        return eq
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.put("/api/equipments/{equipment_id}", tags=["Equipments"], summary="แก้ไขข้อมูลอุปกรณ์ (Admin Only)")
def update_equipment(equipment_id: str, data: EquipmentUpdate, admin: dict = Depends(require_admin)):
    update_data = data.model_dump(exclude_unset=True)
    if "category" in update_data and update_data["category"] is not None:
        update_data["category"] = update_data["category"].value
    try:
        eq = board.update_equipment(equipment_id, update_data)
        if not eq:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบอุปกรณ์รหัส '{equipment_id}'")
        return eq
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/api/equipments/{equipment_id}", tags=["Equipments"], summary="ลบอุปกรณ์ (Admin Only)")
def delete_equipment(equipment_id: str, admin: dict = Depends(require_admin)):
    success = board.delete_equipment(equipment_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบอุปกรณ์รหัส '{equipment_id}'")
    return {"message": f"ลบอุปกรณ์รหัส '{equipment_id}' เรียบร้อยแล้ว"}

# ==========================================
# Ticket Endpoints (แจ้งซ่อม, จัดการ, รูป Before/After, รีวิว)
# ==========================================

@app.get("/api/tickets", tags=["Tickets"], summary="ดึงรายการใบแจ้งซ่อมทั้งหมด")
def list_tickets(
    search: Optional[str] = Query(None, description="ค้นหาหัวข้อ รายละเอียด รหัส หรือเบอร์โทร"),
    status: Optional[str] = Query(None, description="กรองตามสถานะ"),
    priority: Optional[str] = Query(None, description="กรองตามระดับความเร่งด่วน"),
    device_category: Optional[str] = Query(None, description="กรองตามประเภทอุปกรณ์ 5 ชนิด"),
    equipment_id: Optional[str] = Query(None, description="กรองตามรหัสอุปกรณ์")
):
    return board.get_all_tickets(
        search=search,
        status=status,
        priority=priority,
        device_category=device_category,
        equipment_id=equipment_id
    )

@app.get("/api/tickets/{ticket_id}", tags=["Tickets"], summary="ดูรายละเอียดใบแจ้งซ่อมเดี่ยว / ติดตามสถานะ")
def get_ticket(ticket_id: str):
    ticket = board.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบใบแจ้งซ่อมรหัส '{ticket_id}'")
    return ticket

@app.post("/api/tickets", status_code=status.HTTP_201_CREATED, tags=["Tickets"], summary="สร้างใบแจ้งซ่อมใหม่")
def create_ticket(data: TicketCreate, current_user: Optional[dict] = Depends(get_current_user)):
    """สร้างใบแจ้งซ่อมใหม่ (รองรับรูป Before และข้อมูลติดต่อ)"""
    creator_name = current_user.get("full_name") if current_user else (data.customer_name or "ลูกค้าผู้ใช้บริการ")
    try:
        ticket = board.create_ticket(
            title=data.title,
            description=data.description,
            device_category=data.device_category.value,
            equipment_id=data.equipment_id,
            device_model=data.device_model,
            priority=data.priority.value,
            image_before=data.image_before,
            customer_name=data.customer_name or creator_name,
            customer_phone=data.customer_phone,
            estimated_cost=data.estimated_cost or 0.0,
            estimated_days=data.estimated_days or 1,
            created_by=creator_name
        )
        return ticket
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.patch("/api/tickets/{ticket_id}", tags=["Tickets"], summary="อัปเดตสถานะงานซ่อม แนบภาพ After (ช่าง / Admin Only)")
def update_ticket(
    ticket_id: str,
    data: TicketUpdate,
    user: dict = Depends(require_tech_or_admin)
):
    """
    [ข้อ 3 & 4] อัปเดตสถานะงานซ่อม มอบหมายช่าง บันทึกผลการซ่อม และแนบรูปภาพหลังซ่อมเสร็จ
    ต้องล็อกอินด้วยสิทธิ์ช่าง (Technician) หรือแอดมิน (Admin) เท่านั้น
    """
    technician_name = data.technician or user.get("full_name")
    ticket = board.update_ticket_status(
        ticket_id=ticket_id,
        status=data.status.value,
        technician=technician_name,
        notes=data.notes,
        image_after=data.image_after,
        estimated_cost=data.estimated_cost,
        estimated_days=data.estimated_days
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบใบแจ้งซ่อมรหัส '{ticket_id}'")
    return ticket

@app.post("/api/tickets/{ticket_id}/review", tags=["Tickets"], summary="ลูกค้าให้คะแนนและรีวิวงานซ่อม")
def review_ticket(ticket_id: str, data: TicketReviewCreate):
    """[ข้อ 4] ลูกค้าให้คะแนนความพึงพอใจ (1-5 ดาว) และข้อความรีวิว"""
    ticket = board.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบใบแจ้งซ่อมรหัส '{ticket_id}'")
    
    updated = board.add_ticket_review(
        ticket_id=ticket_id,
        rating=data.rating,
        review_comment=data.review_comment
    )
    return {
        "status": "success",
        "message": "บันทึกรีวิวและความคิดเห็นของท่านเรียบร้อยแล้ว ขอบพระคุณที่ใช้บริการ",
        "ticket": updated
    }

@app.get("/api/reviews", tags=["Tickets"], summary="ดูรีวิวงานซ่อมทั้งหมดที่ลูกค้าให้ไว้")
def list_reviews():
    return board.get_all_reviews()

@app.delete("/api/tickets/{ticket_id}", tags=["Tickets"], summary="ลบใบแจ้งซ่อม (Admin Only)")
def delete_ticket(ticket_id: str, admin: dict = Depends(require_admin)):
    success = board.delete_ticket(ticket_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบใบแจ้งซ่อมรหัส '{ticket_id}'")
    return {"message": f"ลบใบแจ้งซ่อมรหัส '{ticket_id}' เรียบร้อยแล้ว"}

# ==========================================
# AI Repair Consultant Engine [ข้อ 5]
# ==========================================

AI_KNOWLEDGE_BASE = {
    "screen": {
        "keywords": ["จอแตก", "หน้าจอ", "จอดำ", "จอเป็นเส้น", "จอฟ้า", "ทัชไม่ได้", "สัมผัสไม่ได้", "กระตุก", "จอม่วง", "จอลาย", "screen"],
        "Notebook": {
            "diagnosis": "หน้าจอ LCD/OLED ได้รับแรงกระแทก, สายแพรจอ (eDP Cable) หลุดหลวมหรือขาดใน, หรือชิปแสดงผลบนเมนบอร์ดมีปัญหา",
            "cost": "2,200 - 4,800 บาท (ขึ้นอยู่กับขนาดหน้าจอและอัตรารีเฟรช 60Hz/144Hz/OLED)",
            "days": "1 - 2 วัน",
            "solutions": ["ตรวจเช็คสายแพรจอ", "เปลี่ยนชุดพาเนลหน้าจอเกรดแท้ตรงรุ่น", "ทดสอบสีและ Dead Pixel ก่อนส่งมอบ"],
            "tips": "อย่าพยายามกดบริเวณที่จอแตกร้าวเพื่อป้องกันผลึกเหลวไหลลาม"
        },
        "Computer": {
            "diagnosis": "การ์ดจอ (GPU) แสดงผลผิดปกติ, พอร์ต HDMI/DisplayPort ชำรุด, สายเคเบิลหลวม หรือมอนิเตอร์เสีย",
            "cost": "500 - 2,500 บาท (ค่าบริการตรวจเช็ค/ซ่อมบอร์ดการ์ดจอ ไม่รวมราคามอนิเตอร์ใหม่)",
            "days": "1 วัน",
            "solutions": ["ทำความสะอาดสล็อต PCIe และขั้วสัมผัสการ์ดจอ", "แฟลช VBIOS / อัปเดตไดรเวอร์ใหม่", "ทดสอบเปลี่ยนสายสัญญาณหรือสลับพอร์ต"],
            "tips": "ลองสลับสาย HDMI หรือต่อเข้าพอร์ตบนเมนบอร์ดเพื่อแยกว่าเป็นที่การ์ดจอหรือหน้าจอ"
        },
        "iPhone": {
            "diagnosis": "ชุดหน้าจอ OLED/Retina แตกกระจายจากแรงตกกระแทก, เลเยอร์ Digitizer เสียหายทำให้สัมผัสไม่ได้ หรือไอซีคุมจอ (Touch IC) บนบอร์ดหลุดร่อน",
            "cost": "1,900 - 6,900 บาท (รุ่น iPhone 11 ถึง 15 Pro Max มีทั้งจอแท้เทียบและจอแท้แกะเครื่อง)",
            "days": "1 - 2 ชั่วโมง (รอรับได้เลย)",
            "solutions": ["เปลี่ยนชุดหน้าจอเกรดแท้พร้อมย้ายชิป True Tone และเซนเซอร์ Face ID", "เปลี่ยนซีลยางกันน้ำและฝุ่นใหม่รอบตัวเครื่อง", "ทดสอบ 3D Touch และสีสันครบทุกมุม"],
            "tips": "หากจอแตกแต่ยังสัมผัสได้ ควรรีบสำรองข้อมูลลง iCloud หรือคอมพิวเตอร์ทันที"
        },
        "iPad": {
            "diagnosis": "กระจกทัชสกรีนด้านนอกแตกร้าว หรือจอใน LCD/Liquid Retina ด้านในหมอง/ช้ำ หรือสายแพรหลวม",
            "cost": "1,800 - 5,500 บาท (iPad Gen ธรรมดาสามารถเปลี่ยนเฉพาะกระจกนอกได้, iPad Air/Pro เป็นจอประกบแท้)",
            "days": "1 - 2 วัน",
            "solutions": ["ลอกกระจกเปลี่ยนใหม่ (สำหรับรุ่นกระจกแยก)", "เปลี่ยนชุดจอแท้แบบ Full Assembly", "ย้ายชุดเซนเซอร์กล้องหน้าและลำโพง"],
            "tips": "ระวังเศษกระจกแตกบาดมือและไม่ควรชาร์จไฟทิ้งไว้หากตัวเครื่องบิดงอ"
        },
        "Mobile": {
            "diagnosis": "หน้าจอ AMOLED/LCD แตกเป็นลายใยแมงมุม หรือจอเบิร์นสัมผัสไม่ไป",
            "cost": "1,200 - 4,200 บาท (Samsung, Oppo, Vivo, Xiaomi)",
            "days": "1 - 2 วัน",
            "solutions": ["เปลี่ยนชุดหน้าจอ AMOLED แท้", "ทำความสะอาดโครงบอดี้เพื่อป้องกันจอใหม่ดัน"],
            "tips": "หลีกเลี่ยงการเปิดเครื่องในที่ชื้นหากหน้าจอมีรอยแตกเปิดกว้าง"
        }
    },
    "battery": {
        "keywords": ["แบต", "แบตเตอรี่", "แบตบวม", "แบตหมดไว", "ชาร์จไม่เข้า", "ชาร์จช้า", "เครื่องร้อน", "battery", "ชาร์จ"],
        "Notebook": {
            "diagnosis": "เซลล์แบตเตอรี่ลิเธียมไอออนเสื่อมสภาพตามรอบ Cycle หรือแผงวงจร BMS ของแบตเตอรี่ตัดการทำงาน",
            "cost": "1,200 - 2,900 บาท (แบตเตอรี่แท้ OEM พร้อมการรับประกัน 6 เดือน)",
            "days": "1 - 2 วัน",
            "solutions": ["ตรวจเช็คค่าสุขภาพแบตเตอรี่และกระแสไฟชาร์จ", "เปลี่ยนก้อนแบตเตอรี่ใหม่ตรงรุ่น", "ทำความสะอาดช่องระบายความร้อน"],
            "tips": "หากพบว่าฝาเครื่องหรือทัชแพดเริ่มดันนูนขึ้นมา แสดงว่าแบตบวม ห้ามกดทับเด็ดขาดเพราะอาจเกิดไฟลุกไหม้ได้"
        },
        "Computer": {
            "diagnosis": "พาวเวอร์ซัพพลาย (Power Supply / PSU) เสื่อมสภาพ จ่ายกระแสไฟไม่นิ่ง หรือถ่านกระดุม BIOS (CR2032) หมด ทำให้นาฬิกาเครื่องรีเซ็ต",
            "cost": "150 - 2,200 บาท (เปลี่ยนถ่าน BIOS 150 บ. / เปลี่ยน PSU 80+ แท้ 1,500 - 2,500 บ.)",
            "days": "1 วัน",
            "solutions": ["ตรวจเช็คแรงดันไฟ 12V, 5V, 3.3V ด้วยเครื่องวัด PSU Tester", "เปลี่ยน PSU คุณภาพสูงมาตรฐาน 80 Plus", "จัดระเบียบสายไฟภายในเคส"],
            "tips": "หากคอมมีเสียงดีดยิกๆ หรือกลิ่นไหม้ ให้ดึงปลั๊กไฟออกทันที"
        },
        "iPhone": {
            "diagnosis": "สุขภาพแบตเตอรี่ต่ำกว่า 80% หรือแบตเตอรี่บวมดันฝาหลังและจอขึ้นมาอย่างเห็นได้ชัด",
            "cost": "990 - 2,200 บาท (แบตเตอรี่มาตรฐาน มอก. พร้อมเพิ่มความจุ และระบบโชว์สุขภาพแบต)",
            "days": "30 - 45 นาที (รอรับได้ทันที)",
            "solutions": ["เปลี่ยนก้อนแบตเตอรี่เกรดแท้คุณภาพสูง มอก.", "ย้ายแพรเดิมเพื่อคงระบบตรวจสอบสุขภาพแบตเตอรี่ (ในรุ่นใหม่)", "ติดกาวซีลกันน้ำมาตรฐานศูนย์"],
            "tips": "แบตเตอรี่ที่บวมมีความเสี่ยง ควรนำมาเปลี่ยนโดยเร็ว ไม่ควรเสียบชาร์จทิ้งไว้ข้ามคืน"
        },
        "iPad": {
            "diagnosis": "แบตเตอรี่กักเก็บประจุไม่ได้ ชาร์จขึ้นช้า หรือเปิดติดแล้วดับทันทีเมื่อถอดสายชาร์จ",
            "cost": "1,500 - 3,200 บาท",
            "days": "1 - 2 วัน",
            "solutions": ["เปิดหน้าจออย่างประณีตด้วยแท่นความร้อน", "เปลี่ยนแบตเตอรี่ iPad ความจุเต็มตรงรุ่น", "ตรวจสอบบอร์ดและวงจรชาร์จ Tristar/Hydra"],
            "tips": "ไม่ควรใช้งาน iPad หนักๆ เช่น เล่นเกม ระหว่างเสียบชาร์จ เพราะจะสะสมความร้อนสูง"
        },
        "Mobile": {
            "diagnosis": "แบตเตอรี่เสื่อม บวมดันฝาหลังอ้า หรือชาร์จไม่เข้าจากพอร์ต Type-C สกปรก",
            "cost": "800 - 1,800 บาท",
            "days": "1 วัน",
            "solutions": ["เปลี่ยนแบตเตอรี่ใหม่มาตรฐานความปลอดภัย", "ทำความสะอาดหรือเปลี่ยนขั้วชาร์จ USB-C"],
            "tips": "ตรวจสอบว่ามีเศษฝุ่นติดอยู่ในรูชาร์จหรือไม่ก่อนส่งซ่อม"
        }
    },
    "power": {
        "keywords": ["เปิดไม่ติด", "ไฟไม่เข้า", "ดับ", "ดับเอง", "ค้าง", "ช็อต", "น้ำเข้า", "โดนน้ำ", "power", "dead"],
        "Notebook": {
            "diagnosis": "เมนบอร์ดช็อตที่ลายไฟหลัก 19V/20V, วงจรชาร์จ IC Power ขัดข้อง, หรือโดนของเหลวหกใส่ทำให้เกิดคราบออกไซด์",
            "cost": "1,500 - 3,500 บาท (ซ่อมจุดช็อตบนเมนบอร์ด ไม่ต้องเปลี่ยนบอร์ดยกชุด ประหยัดกว่ามาก)",
            "days": "2 - 3 วัน",
            "solutions": ["ล้างคราบออกไซด์ด้วยน้ำยาเคมีเฉพาะทางและคลื่นอัลตราโซนิก", "ตรวจวัดลายไฟหาจุดช็อตด้วยกล้องจับความร้อน Thermal Camera", "เปลี่ยนตัวต้านทาน ตัวเก็บประจุ หรือ MOSFET ที่ชำรุด"],
            "tips": "หากโดนน้ำหกใส่ ให้ดึงสายชาร์จออกทันที และห้ามเปิดเครื่องเด็ดขาดจนกว่าจะได้รับการเป่าแห้งและล้างบอร์ด"
        },
        "Computer": {
            "diagnosis": "พาวเวอร์ซัพพลาย (PSU) เสีย, สวิตช์ปุ่ม Power หน้าเคสขาด, หรือเมนบอร์ดช็อตวงจร VRM ภาคจ่ายไฟ CPU",
            "cost": "400 - 2,500 บาท",
            "days": "1 - 2 วัน",
            "solutions": ["ทดสอบจั๊มไฟ PSU (Paperclip Test)", "เช็คไฟสแตนด์บายบนเมนบอร์ด", "เคลียร์ CMOS / ซ่อมภาคจ่ายไฟหรือเปลี่ยน PSU"],
            "tips": "ลองตรวจสอบรางปลั๊กไฟและสายไฟ AC หลังเคสคอมพิวเตอร์ก่อนส่งตรวจเช็ค"
        },
        "iPhone": {
            "diagnosis": "เครื่องตกน้ำ, เมนบอร์ดช็อตวงจร VDD_MAIN หรือไฟตกจากอแดปเตอร์ชาร์จไม่ได้มาตรฐาน",
            "cost": "1,500 - 4,500 บาท (ซ่อมบอร์ดสองชั้น ยกเมนบอร์ด)",
            "days": "1 - 3 วัน",
            "solutions": ["แยกเลเยอร์เมนบอร์ดสองชั้น (Interposer Reballing)", "เปลี่ยนชิปไอซีที่ช็อตและทำลายวงจรใหม่", "ดึงข้อมูลสำคัญคืนให้ลูกค้า"],
            "tips": "ห้ามนำเครื่องไปแช่ถังข้าวสาร เพราะฝุ่นแป้งจะเข้าไปอุดตันและทำให้ความชื้นกัดกร่อนวงจรเร็วขึ้น"
        },
        "iPad": {
            "diagnosis": "เมนบอร์ดช็อต, ไอซีคุมไฟ PMIC ชำรุด หรือชิป CPU Overheat",
            "cost": "1,800 - 4,200 บาท",
            "days": "2 - 3 วัน",
            "solutions": ["ตรวจเช็คกระแสไฟกินบอร์ดด้วย DC Power Supply", "ซ่อมลายไฟช็อตใต้แผ่นชิลด์กันสัญญาณ"],
            "tips": "สังเกตว่าตัวเครื่องมีความร้อนผิดปกติขึ้นมาเฉพาะจุดหรือไม่"
        },
        "Mobile": {
            "diagnosis": "เมนบอร์ดช็อต ลายไฟชาร์จขาด หรือพาวเวอร์ไอซีเสียหาย",
            "cost": "900 - 2,800 บาท",
            "days": "1 - 2 วัน",
            "solutions": ["ตรวจเช็คระบบไฟ", "เปลี่ยนชิป IC ชาร์จหรือ IC จ่ายไฟ"],
            "tips": "นำที่ชาร์จและสายเดิมมาให้ช่างตรวจสอบพร้อมกันเพื่อหาสาเหตุที่แท้จริง"
        }
    },
    "general": {
        "keywords": [],
        "Notebook": {
            "diagnosis": "อาการผิดปกติทั่วไป เช่น ฮาร์ดดิสก์/SSD เต็ม, เครื่องช้าผิดปกติ, ติดไวรัส หรือพัดลมมีฝุ่นเกาะหนาแน่น",
            "cost": "400 - 1,800 บาท (ล้างเครื่องลงโปรแกรม / เพิ่ม SSD / ทำความสะอาดทาซิลิโคนใหม่)",
            "days": "1 วัน",
            "solutions": ["ทำความสะอาดพัดลมและทาซิลิโคนนำความร้อนใหม่", "สแกนไวรัสและเคลียร์ไฟล์ขยะ", "อัปเกรดความจุด้วย SSD NVMe"],
            "tips": "ควรนำเครื่องมาทำความสะอาดและเปลี่ยนซิลิโคนอย่างน้อยปีละ 1 ครั้ง"
        },
        "Computer": {
            "diagnosis": "ระบบวินโดวส์ขัดข้อง, RAM หลวม, ไดรฟ์เก็บข้อมูลมี Bad Sector หรือต้องการอัปเกรดสเปกเพื่อความลื่นไหล",
            "cost": "400 - 1,500 บาท (ไม่รวมค่าฮาร์ดแวร์ชิ้นใหม่)",
            "days": "1 วัน",
            "solutions": ["ทดสอบสุขภาพฮาร์ดไดรฟ์และหน่วยความจำ RAM", "จัดสายไฟและเป่าฝุ่นทำความสะอาดชุดระบายความร้อน", "ติดตั้งระบบปฏิบัติการและไดรเวอร์แท้ล่าสุด"],
            "tips": "สามารถแจ้งงบประมาณและสเปกที่ต้องการเพื่อให้ทีมช่างช่วยแนะนำการอัปเกรดที่คุ้มค่าที่สุดได้"
        },
        "iPhone": {
            "diagnosis": "ความจุเต็มเครื่องค้างโลโก้ Apple, กล้องสั่น/มัว, ลำโพงสนทนาเสียงเบา หรือปุ่มกดกดยาก",
            "cost": "600 - 2,500 บาท",
            "days": "1 - 2 ชั่วโมง",
            "solutions": ["ทำความสะอาดตะแกรงลำโพงและไมโครโฟน", "เปลี่ยนโมดูลกล้องหรือชุดปุ่มสวิตช์", "กู้คืนระบบ iOS โดยรักษาข้อมูลเดิม"],
            "tips": "ควรเคลียร์พื้นที่ว่างในตัวเครื่องอย่างน้อย 5-10GB เพื่อป้องกันเครื่องวนลูปดับ"
        },
        "iPad": {
            "diagnosis": "ระบบปฏิบัติการค้าง, พอร์ตชาร์จหลวม, ลำโพงแตก หรือปุ่มเปิดปิดค้าง",
            "cost": "800 - 2,500 บาท",
            "days": "1 วัน",
            "solutions": ["เปลี่ยนพอร์ตชาร์จหรือปุ่มกดใหม่", "รีเฟรชระบบ iPadOS และตรวจเช็คการทำงานของ Apple Pencil"],
            "tips": "ตรวจเช็คว่าปลายหัวปากกา Apple Pencil สึกกร่อนหรือหน้าจอมีฟิล์มหนาเกินไปหรือไม่"
        },
        "Mobile": {
            "diagnosis": "ระบบทำงานช้า, หน่วยความจำเต็ม, หรือพอร์ตเชื่อมต่อสกปรก",
            "cost": "400 - 1,500 บาท",
            "days": "1 วัน",
            "solutions": ["ล้างระบบและอัปเดตเฟิร์มแวร์", "ทำความสะอาดจุดเชื่อมต่อ"],
            "tips": "สำรองรูปภาพและข้อมูลบัญชี Google/LINE ไว้ล่วงหน้า"
        }
    }
}

@app.post("/api/ai/consult", response_model=AIConsultResponse, tags=["AI Consultant"], summary="AI ปรึกษางานซ่อมคอมพิวเตอร์และมือถือ 24 ชม.")
def ai_consult(req: AIConsultRequest):
    """
    [ข้อ 5] AI ผู้เชี่ยวชาญให้คำปรึกษาเกี่ยวกับงานซ่อม Notebook, Computer, Mobile, iPhone, iPad
    - ประเมินราคาซ่อมเบื้องต้น
    - วิเคราะห์สาเหตุของปัญหา
    - ประเมินระยะเวลาซ่อม (วัน/ชม.)
    - ข้อแนะนำในการปฏิบัติตัวและข้อมูลระบบส่งซ่อม
    """
    desc = req.issue_description.lower().strip()
    
    # ตรวจสอบประเภทอุปกรณ์ (หากผู้ใช้ไม่ได้ระบุ ให้ตรวจจับจากคำในข้อความ หรือเลือก Notebook เป็นค่าเริ่มต้น)
    cat = req.device_category
    if not cat or cat not in ["Notebook", "Computer", "Mobile", "iPhone", "iPad"]:
        if "iphone" in desc or "ไอโฟน" in desc:
            cat = "iPhone"
        elif "ipad" in desc or "ไอแพด" in desc:
            cat = "iPad"
        elif "คอม" in desc or "pc" in desc or "เคส" in desc or "desktop" in desc:
            cat = "Computer"
        elif "โน้ตบุ๊ก" in desc or "โน๊ตบุ๊ค" in desc or "notebook" in desc or "laptop" in desc or "macbook" in desc:
            cat = "Notebook"
        elif "มือถือ" in desc or "samsung" in desc or "mobile" in desc or "android" in desc or "โทรศัพท์" in desc:
            cat = "Mobile"
        else:
            cat = "Notebook"

    # แมปประเภทอาการเสียกับคลังความรู้
    matched_category = "general"
    for issue_type, data in AI_KNOWLEDGE_BASE.items():
        if issue_type == "general":
            continue
        if any(kw in desc for kw in data["keywords"]):
            matched_category = issue_type
            break

    kb_item = AI_KNOWLEDGE_BASE[matched_category].get(cat, AI_KNOWLEDGE_BASE["general"][cat])

    device_name = f"{cat} {req.device_model}".strip() if req.device_model else cat

    return AIConsultResponse(
        device_category=cat,
        symptom=f"ปรึกษาอาการ: {req.issue_description} (สำหรับ {device_name})",
        diagnosis=kb_item["diagnosis"],
        estimated_cost_range=kb_item["cost"],
        estimated_days_range=kb_item["days"],
        solutions=kb_item["solutions"],
        recommendations=kb_item["tips"],
        store_info="ศูนย์บริการ QUICK TECH REPAIR รับประกันงานซ่อม 90 วันเต็ม ตรวจเช็คอาการเบื้องต้นฟรีไม่มีค่าใช้จ่าย สามารถนำเครื่องเข้ามาหน้าร้าน หรือเปิดใบแจ้งซ่อมออนไลน์เพื่อรับคิวพิเศษได้ทันที"
    )

# ==========================================
# Frontend Static Files Mounting
# ==========================================
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

if os.path.isdir(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend_dir")
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend_root")
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {"message": "Quick Maintenance Tracker API v2.5 is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)