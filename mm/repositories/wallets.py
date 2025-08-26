from typing import Any, Dict, List
from bson import ObjectId
from mm.repositories.base import MongoRepository


class WalletRepository(MongoRepository):
    def __init__(self):
        super().__init__("wallets")

    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get semua saving space untuk user tertentu"""
        try:
            return self.find_many({"user_id": user_id}, limit=100)
        except Exception:
            return []

    def update_wallet(self, wallet_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update saving space dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(wallet_id)
            
            # Pastikan saving space milik user yang bersangkutan
            existing_wallet = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_wallet:
                return False
            
            # Update dengan ObjectId
            result = self.collection.update_one({"_id": obj_id}, {"$set": updates})
            return result.modified_count > 0
        except Exception:
            return False
    
    def delete_wallet(self, wallet_id: str, user_id: str) -> bool:
        """Delete saving space dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(wallet_id)
            
            # Pastikan saving space milik user yang bersangkutan
            existing_wallet = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_wallet:
                return False
            
            # Delete dengan ObjectId
            result = self.collection.delete_one({"_id": obj_id})
            return result.deleted_count > 0
        except Exception:
            return False


