from typing import Any, Dict, List, Optional
from bson import ObjectId
from mm.repositories.base import MongoRepository


class ScopeRepository(MongoRepository):
    def __init__(self):
        super().__init__("scopes")

    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get semua scope untuk user tertentu"""
        try:  
            result = self.find_many({"user_id": user_id}, limit=100)        
            for scope in result:
                print("  - Scope:", scope.get('name', 'No name'), "ID:", scope.get('_id', 'No ID'))
            return result
        except Exception as e:
            print("🔍 [SCOPE_REPO] Error fetching scopes:", e)
            return []

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find satu dokumen"""
        try:
            return super().find_one(query)
        except Exception as e:
            print(f"Error in scope find_one: {e}")
            return None

    def update_scope(self, scope_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update scope dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(scope_id)
            
            # Pastikan scope milik user yang bersangkutan
            existing_scope = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_scope:
                return False
            
            # Update dengan ObjectId
            result = self.collection.update_one({"_id": obj_id}, {"$set": updates})
            return result.modified_count > 0
        except Exception:
            return False
    
    def delete_scope(self, scope_id: str, user_id: str) -> bool:
        """Delete scope dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(scope_id)
            
            # Pastikan scope milik user yang bersangkutan
            existing_scope = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_scope:
                return False
            
            # Delete dengan ObjectId
            result = self.collection.delete_one({"_id": obj_id})
            return result.deleted_count > 0
        except Exception:
            return False


