from typing import Any, Dict, List, Optional
import time

from bson import ObjectId
from pymongo import ASCENDING

from mm.repositories.base import MongoRepository


class SharePublicRepository(MongoRepository):
    """Stores public share configurations for /myuangly/<username>/<slug>."""

    def __init__(self):
        super().__init__("share_public")
        # The public URL is /myuangly/<username>/<slug> — enforce uniqueness of that pair.
        # Inline create_index is the only live unique-index pattern in the codebase
        # (see mm/repositories/ai_chats.py); ensure_indexes() is commented out in app.py.
        try:
            self.collection.create_index(
                [("username", ASCENDING), ("slug", ASCENDING)],
                name="idx_share_username_slug",
                unique=True,
            )
        except Exception:
            pass

    # ---- reads ------------------------------------------------------------
    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            return self.find_many(
                {"user_id": user_id}, limit=200, sort=[("updated_at", -1)]
            )
        except Exception:
            return []

    def find_by_username_slug(
        self, username: str, slug: str
    ) -> Optional[Dict[str, Any]]:
        try:
            return self.find_one({"username": username, "slug": slug})
        except Exception:
            return None

    def find_owned(
        self, share_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Ownership-checked fetch (used by every mutation)."""
        try:
            obj_id = ObjectId(share_id)
        except Exception:
            return None
        doc = self.collection.find_one({"_id": obj_id, "user_id": user_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def slug_exists(
        self,
        username: str,
        slug: str,
        exclude_id: Optional[str] = None,
    ) -> bool:
        query: Dict[str, Any] = {"username": username, "slug": slug}
        if exclude_id:
            try:
                query["_id"] = {"$ne": ObjectId(exclude_id)}
            except Exception:
                pass
        try:
            return self.collection.count_documents(query) > 0
        except Exception:
            return False

    # ---- writes -----------------------------------------------------------
    def create(self, data: Dict[str, Any]) -> Optional[str]:
        now = int(time.time())
        data.setdefault("created_at", now)
        data["updated_at"] = now
        try:
            return self.insert_one(data)
        except Exception as e:
            # Duplicate key on (username, slug) surfaces here as a 11000 error
            print(f"❌ [SHARE_PUBLIC] create error: {e}")
            return None

    def update(
        self, share_id: str, user_id: str, updates: Dict[str, Any]
    ) -> bool:
        try:
            obj_id = ObjectId(share_id)
        except Exception:
            return False
        updates["updated_at"] = int(time.time())
        try:
            result = self.collection.update_one(
                {"_id": obj_id, "user_id": user_id}, {"$set": updates}
            )
            return result.matched_count > 0
        except Exception as e:
            print(f"❌ [SHARE_PUBLIC] update error: {e}")
            return False

    def set_published(
        self, share_id: str, user_id: str, is_published: bool
    ) -> bool:
        return self.update(share_id, user_id, {"is_published": bool(is_published)})

    def delete(self, share_id: str, user_id: str) -> bool:
        try:
            obj_id = ObjectId(share_id)
        except Exception:
            return False
        try:
            result = self.collection.delete_one({"_id": obj_id, "user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"❌ [SHARE_PUBLIC] delete error: {e}")
            return False
