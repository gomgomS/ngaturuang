from typing import Any, Dict, List
from bson import ObjectId
from mm.repositories.base import MongoRepository


class CategoryRepository(MongoRepository):
    def __init__(self):
        super().__init__("categories")

    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get semua kategori untuk user tertentu"""
        try:
            return self.find_many({"user_id": user_id}, limit=100)
        except Exception:
            return []

    def update_category(self, category_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update category dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(category_id)
            
            # Pastikan category milik user yang bersangkutan
            existing_category = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_category:
                return False
            
            # Update dengan ObjectId
            result = self.collection.update_one({"_id": obj_id}, {"$set": updates})
            return result.modified_count > 0
        except Exception:
            return False
    
    def delete_category(self, category_id: str, user_id: str) -> bool:
        """Delete category dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(category_id)
            
            # Pastikan category milik user yang bersangkutan
            existing_category = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_category:
                return False
            
            # Delete dengan ObjectId
            result = self.collection.delete_one({"_id": obj_id})
            return result.deleted_count > 0
        except Exception:
            return False


