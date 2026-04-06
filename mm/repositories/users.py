from typing import Any, Dict, Optional

from bson import ObjectId
from mm.repositories.base import MongoRepository


class UserRepository(MongoRepository):
    def __init__(self):
        super().__init__("users")

    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        docs = self.find_many({"username": username}, limit=1)
        return docs[0] if docs else None

    def update_tour_status(self, user_id: str, completed: bool) -> bool:
        """Update tour_completed field. Tries ObjectId first, falls back to string _id."""
        update = {"$set": {"tour_completed": completed}}
        try:
            obj_id = ObjectId(user_id)
            result = self.collection.update_one({"_id": obj_id}, update)
            if result.matched_count > 0:
                return True
        except Exception:
            pass
        # Fallback: _id stored as plain string
        result = self.collection.update_one({"_id": user_id}, update)
        return result.matched_count > 0


