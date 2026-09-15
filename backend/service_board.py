import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from database import get_connection, init_db, seed_initial_data

class ServiceBoard:
    def __init__(self):
        # สร้างตารางและข้อมูลตัวอย่างหากยังไม่มี
        init_db()

    def _generate_equipment_id(self, cursor: sqlite3.Cursor) -> str:
        cursor.execute("SELECT id FROM equipments WHERE id LIKE 'EQ-%' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            try:
                num = int(row["id"].split("-")[1]) + 1
                return f"EQ-{num:03d}"
            except (IndexError, ValueError):
                pass
        cursor.execute("SELECT COUNT(*) as count FROM equipments")
        count = cursor.fetchone()["count"] + 1
        return f"EQ-{count:03d}"

    def _generate_ticket_id(self, cursor: sqlite3.Cursor) -> str:
        cursor.execute("SELECT id FROM tickets WHERE id LIKE 'TK-%' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            try:
                num = int(row["id"].split("-")[1]) + 1
                return f"TK-{num:03d}"
            except (IndexError, ValueError):
                pass
        cursor.execute("SELECT COUNT(*) as count FROM tickets")
        count = cursor.fetchone()["count"] + 1
        return f"TK-{count:03d}"

    # --- Equipment Operations ---

    def add_equipment(self, name: str, location: str, category: str) -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        eq_id = self._generate_equipment_id(cursor)

        cursor.execute("""
            INSERT INTO equipments (id, name, location, category, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'Operational', ?, ?)
        """, (eq_id, name, location, category, now_str, now_str))
        conn.commit()

        cursor.execute("SELECT * FROM equipments WHERE id = ?", (eq_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row)

    def get_all_equipments(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM equipments WHERE 1=1"
        params = []

        if search:
            query += " AND (name LIKE ? OR location LIKE ? OR id LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])

        if category and category != "All":
            query += " AND category = ?"
            params.append(category)

        if status and status != "All":
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY id ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_equipment_by_id(self, equipment_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM equipments WHERE id = ?", (equipment_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        eq_dict = dict(row)

        # ดึง tickets ที่เกี่ยวข้องกับอุปกรณ์นี้
        cursor.execute("SELECT * FROM tickets WHERE equipment_id = ? ORDER BY created_at DESC", (equipment_id,))
        tickets = [dict(t) for t in cursor.fetchall()]
        eq_dict["tickets"] = tickets

        conn.close()
        return eq_dict

    def update_equipment(self, equipment_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM equipments WHERE id = ?", (equipment_id,))
        if not cursor.fetchone():
            conn.close()
            return None

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updates = []
        params = []

        for field in ["name", "location", "category", "status"]:
            if field in data and data[field] is not None:
                updates.append(f"{field} = ?")
                params.append(data[field])

        if not updates:
            conn.close()
            return self.get_equipment_by_id(equipment_id)

        updates.append("updated_at = ?")
        params.append(now_str)
        params.append(equipment_id)

        cursor.execute(f"UPDATE equipments SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

        cursor.execute("SELECT * FROM equipments WHERE id = ?", (equipment_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row)

    def delete_equipment(self, equipment_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM equipments WHERE id = ?", (equipment_id,))
        if not cursor.fetchone():
            conn.close()
            return False

        cursor.execute("DELETE FROM equipments WHERE id = ?", (equipment_id,))
        conn.commit()
        conn.close()
        return True

    # --- Ticket Operations ---

    def create_ticket(
        self, equipment_id: str, title: str, description: str, priority: str = "Medium", created_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM equipments WHERE id = ?", (equipment_id,))
        eq = cursor.fetchone()
        if not eq:
            conn.close()
            return None

        tk_id = self._generate_ticket_id(cursor)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO tickets (id, equipment_id, title, description, priority, status, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?)
        """, (tk_id, equipment_id, title, description, priority, created_by, now_str))

        # อัปเดตสถานะอุปกรณ์เป็น Needs Maintenance หากไม่ได้อยู่ในสถานะ Under Repair
        if eq["status"] != "Under Repair":
            cursor.execute("UPDATE equipments SET status = 'Needs Maintenance', updated_at = ? WHERE id = ?", (now_str, equipment_id))

        conn.commit()


        cursor.execute("""
            SELECT t.*, e.name as equipment_name, e.location as equipment_location 
            FROM tickets t
            LEFT JOIN equipments e ON t.equipment_id = e.id
            WHERE t.id = ?
        """, (tk_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row)

    def get_all_tickets(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        equipment_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT t.*, e.name as equipment_name, e.location as equipment_location 
            FROM tickets t
            LEFT JOIN equipments e ON t.equipment_id = e.id
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (t.title LIKE ? OR t.description LIKE ? OR t.id LIKE ? OR t.assigned_to LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term, term])

        if status and status != "All":
            query += " AND t.status = ?"
            params.append(status)

        if priority and priority != "All":
            query += " AND t.priority = ?"
            params.append(priority)

        if equipment_id:
            query += " AND t.equipment_id = ?"
            params.append(equipment_id)

        query += " ORDER BY CASE t.priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, t.created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, e.name as equipment_name, e.location as equipment_location 
            FROM tickets t
            LEFT JOIN equipments e ON t.equipment_id = e.id
            WHERE t.id = ?
        """, (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_ticket_status(
        self, ticket_id: str, status: str, technician: Optional[str] = None, notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            conn.close()
            return None

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        resolved_at = now_str if status in ["Resolved", "Closed"] else (None if status in ["Open", "In Progress"] else ticket["resolved_at"])

        assigned_to = technician if technician is not None else ticket["assigned_to"]
        current_notes = notes if notes is not None else ticket["notes"]

        cursor.execute("""
            UPDATE tickets 
            SET status = ?, assigned_to = ?, notes = ?, resolved_at = ?
            WHERE id = ?
        """, (status, assigned_to, current_notes, resolved_at, ticket_id))

        # ปรับสถานะอุปกรณ์โดยอัตโนมัติตามสถานะของ Ticket
        eq_id = ticket["equipment_id"]
        self._recalculate_equipment_status(cursor, eq_id, now_str)

        conn.commit()

        cursor.execute("""
            SELECT t.*, e.name as equipment_name, e.location as equipment_location 
            FROM tickets t
            LEFT JOIN equipments e ON t.equipment_id = e.id
            WHERE t.id = ?
        """, (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row)

    def delete_ticket(self, ticket_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT equipment_id FROM tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        eq_id = row["equipment_id"]
        cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._recalculate_equipment_status(cursor, eq_id, now_str)

        conn.commit()
        conn.close()
        return True

    def _recalculate_equipment_status(self, cursor: sqlite3.Cursor, equipment_id: str, now_str: str):
        """คำนวณสถานะอุปกรณ์อัตโนมัติตาม Ticket ที่คงค้างอยู่"""
        cursor.execute("SELECT status FROM tickets WHERE equipment_id = ?", (equipment_id,))
        tickets = cursor.fetchall()

        has_in_progress = any(t["status"] == "In Progress" for t in tickets)
        has_open = any(t["status"] == "Open" for t in tickets)

        if has_in_progress:
            new_status = "Under Repair"
        elif has_open:
            new_status = "Needs Maintenance"
        else:
            new_status = "Operational"

        cursor.execute("UPDATE equipments SET status = ?, updated_at = ? WHERE id = ?", (new_status, now_str, equipment_id))

    # --- Dashboard Summary & Statistics ---

    def get_dashboard_stats(self) -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM equipments")
        total_equipments = cursor.fetchone()["count"]

        cursor.execute("SELECT status, COUNT(*) as count FROM equipments GROUP BY status")
        eq_status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

        operational_count = eq_status_counts.get("Operational", 0)
        needs_maintenance_count = eq_status_counts.get("Needs Maintenance", 0)
        under_repair_count = eq_status_counts.get("Under Repair", 0)

        uptime_percentage = round((operational_count / total_equipments * 100), 1) if total_equipments > 0 else 100.0

        cursor.execute("SELECT COUNT(*) as count FROM tickets")
        total_tickets = cursor.fetchone()["count"]

        cursor.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
        tk_status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

        open_tickets_count = tk_status_counts.get("Open", 0)
        in_progress_tickets_count = tk_status_counts.get("In Progress", 0)
        resolved_tickets_count = tk_status_counts.get("Resolved", 0) + tk_status_counts.get("Closed", 0)

        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE priority = 'Urgent' AND status IN ('Open', 'In Progress')")
        urgent_tickets_count = cursor.fetchone()["count"]

        conn.close()

        return {
            "total_equipments": total_equipments,
            "operational_count": operational_count,
            "needs_maintenance_count": needs_maintenance_count,
            "under_repair_count": under_repair_count,
            "uptime_percentage": uptime_percentage,
            "total_tickets": total_tickets,
            "open_tickets_count": open_tickets_count,
            "in_progress_tickets_count": in_progress_tickets_count,
            "resolved_tickets_count": resolved_tickets_count,
            "urgent_tickets_count": urgent_tickets_count
        }

    def get_board_summary(self) -> Dict[str, Any]:
        return {
            "stats": self.get_dashboard_stats(),
            "equipments": self.get_all_equipments(),
            "tickets": self.get_all_tickets()
        }

    def reset_demo_data(self) -> Dict[str, str]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tickets")
        cursor.execute("DELETE FROM equipments")
        conn.commit()
        seed_initial_data(conn)
        conn.close()
        return {"message": "รีเซ็ตข้อมูลตัวอย่างสำเร็จเรียบร้อย"}