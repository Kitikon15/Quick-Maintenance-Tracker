"""
Quick Maintenance Tracker - Server Launcher
รันเซิร์ฟเวอร์ด้วยคำสั่ง: python main.py
"""
import sys
import os
import uvicorn

# เพิ่มโฟลเดอร์ backend เข้า sys.path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    print("=" * 60)
    print(" 🛠️  Quick Maintenance Tracker is starting...")
    print(" 🌐  Frontend & System: http://127.0.0.1:8000")
    print(" 📚  API Swagger Docs:  http://127.0.0.1:8000/docs")
    print("=" * 60)
    
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, app_dir=backend_dir)
