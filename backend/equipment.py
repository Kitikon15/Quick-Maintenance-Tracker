from datetime import datetime
from typing import Dict, Any, Optional

class Equipment:
    def __init__(self, equipment_id: str, name: str, location: str, category: str):
        self.id = equipment_id
        self.name = name
        self.location = location
        self.category = category
        self.status = "Operational"  # Operational, Needs Maintenance, Under Repair
        self.created_at = datetime.now()

    def update_status(self, new_status: str):
        valid_statuses = ["Operational", "Needs Maintenance", "Under Repair"]
        if new_status in valid_statuses:
            self.status = new_status
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "category": self.category,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }