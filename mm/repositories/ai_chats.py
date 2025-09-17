from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING

from .base import MongoRepository


class AiChatRepository(MongoRepository):
    def __init__(self):
        super().__init__("ai_conversations")
        # Ensure index on user_id for quick lookups and uniqueness (one doc per user)
        try:
            self.collection.create_index([("user_id", ASCENDING)], name="idx_ai_user", unique=True)
            self.collection.create_index([("updated_at", ASCENDING)], name="idx_ai_updated")
        except Exception:
            # Index creation failures should not hard-crash app in runtime
            pass

    def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        doc = self.collection.find_one({"user_id": user_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def append_message(
        self,
        user_id: str,
        message: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()

        # Upsert conversation document with one doc per user
        self.collection.update_one(
            {"user_id": user_id},
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "created_at": now,
                    "version": 1,
                },
                "$push": {"messages": {"data": message, "created_at": now}},
                "$set": {"updated_at": now, "last_message_at": now},
            },
            upsert=True,
        )

        # Return the updated conversation
        updated = self.get_by_user_id(user_id) or {"user_id": user_id, "messages": []}
        return updated


