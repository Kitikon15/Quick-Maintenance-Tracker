from datetime import datetime
from typing import Dict, Any, Optional

class MaintenanceTicket:
    def __init__(self, ticket_id: str, equipment_id: str, title: str, description: str, priority: str = "Medium", created_by: Optional[str] = None):
        self.id = ticket_id
        self.equipment_id = equipment_id
        self.title = title
        self.description = description
        self.priority = priority  # Low, Medium, High, Urgent
        self.status = "Open"      # Open, In Progress, Resolved, Closed
        self.assigned_to: Optional[str] = None
        self.created_by: Optional[str] = created_by
        self.created_at = datetime.now()
        self.resolved_at: Optional[datetime] = None

    def assign_technician(self, technician_name: str):
        self.assigned_to = technician_name
        if self.status == "Open":
            self.status = "In Progress"

    def resolve(self):
        self.status = "Resolved"
        self.resolved_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "created_by": self.created_by,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": self.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if self.resolved_at else None
        }