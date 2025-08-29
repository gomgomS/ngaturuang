from typing import Any, Dict, List, Optional
from bson import ObjectId
from mm.repositories.base import MongoRepository
import time


class WalletRepository(MongoRepository):
    def __init__(self):
        super().__init__("wallets")

    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get semua saving space untuk user tertentu"""
        try:
            return self.find_many({"user_id": user_id}, limit=100)
        except Exception:
            return []

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find satu dokumen"""
        try:
            print(f"🔍 [WALLET] find_one called with query: {query}")
            result = super().find_one(query)
            print(f"🔍 [WALLET] find_one result: {result}")
            return result
        except Exception as e:
            print(f"❌ [WALLET] Error in wallet find_one: {e}")
            import traceback
            print(f"❌ [WALLET] Error traceback: {traceback.format_exc()}")
            return None

    def update_wallet(self, wallet_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update saving space dengan validasi user ownership"""
        try:
            print(f"🔍 [WALLET] update_wallet called with wallet_id: {wallet_id}, user_id: {user_id}, updates: {updates}")
            
            # Convert string ID ke ObjectId
            obj_id = ObjectId(wallet_id)
            print(f"🔍 [WALLET] Converted to ObjectId: {obj_id}")
            
            # Pastikan saving space milik user yang bersangkutan
            existing_wallet = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            print(f"🔍 [WALLET] Existing wallet check result: {existing_wallet is not None}")
            
            if not existing_wallet:
                print(f"❌ [WALLET] Wallet not found or not owned by user")
                return False
            
            # Update dengan ObjectId
            print(f"🔍 [WALLET] Performing update operation...")
            result = self.collection.update_one({"_id": obj_id}, {"$set": updates})
            print(f"🔍 [WALLET] Update result: {result.modified_count} documents modified")
            
            success = result.modified_count > 0
            print(f"🔍 [WALLET] Update success: {success}")
            return success
        except Exception as e:
            print(f"❌ [WALLET] Error in update_wallet: {e}")
            import traceback
            print(f"❌ [WALLET] Error traceback: {traceback.format_exc()}")
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

    def update_wallet_balance(self, wallet_id: str, user_id: str, actual_balance: float, expected_balance: float = None) -> bool:
        """Update wallet balance ketika manual balance dibuat"""
        try:
            print(f"💰 [WALLET] Updating wallet balance: {wallet_id}, actual: {actual_balance}, expected: {expected_balance}")
            
            # Convert string ID ke ObjectId
            obj_id = ObjectId(wallet_id)
            
            # Pastikan wallet milik user yang bersangkutan
            existing_wallet = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_wallet:
                print(f"❌ [WALLET] Wallet not found or not owned by user")
                return False
            
            # Prepare updates
            updates = {
                "actual_balance": actual_balance,
                "updated_at": int(time.time())
            }
            
            # Update expected_balance jika disediakan
            if expected_balance is not None:
                updates["expected_balance"] = expected_balance
            
            # Update wallet
            result = self.collection.update_one({"_id": obj_id}, {"$set": updates})
            
            if result.modified_count > 0:
                print(f"✅ [WALLET] Successfully updated wallet balance: {wallet_id}")
                return True
            else:
                print(f"⚠️ [WALLET] No changes made to wallet: {wallet_id}")
                return False
                
        except Exception as e:
            print(f"❌ [WALLET] Error updating wallet balance: {e}")
            import traceback
            print(f"❌ [WALLET] Error traceback: {traceback.format_exc()}")
            return False

    def get_wallet_by_id(self, wallet_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet berdasarkan ID dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(wallet_id)
            
            wallet = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if wallet:
                # Convert ObjectId ke string
                wallet["_id"] = str(wallet["_id"])
                
                # Set default values
                wallet.setdefault("actual_balance", 0.0)
                wallet.setdefault("expected_balance", 0.0)
                wallet.setdefault("currency", "IDR")
                wallet.setdefault("is_active", True)
            
            return wallet
        except Exception as e:
            print(f"❌ [WALLET] Error getting wallet by ID: {e}")
            return None


