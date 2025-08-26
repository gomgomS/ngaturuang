from typing import Any, Dict, List
import time
from bson import ObjectId
from mm.repositories.base import MongoRepository


class TransactionRepository(MongoRepository):
    def __init__(self):
        super().__init__("transactions")

    def list_by_user(self, user_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Query sederhana untuk mendapatkan transaksi user"""
        try:
            transactions = self.find_many({"user_id": user_id}, limit=limit, sort=[("timestamp", -1)])
            # Ensure we always return a list, never None
            if transactions is None:
                transactions = []
            return transactions
        except Exception as e:
            print(f"Error in list_by_user: {e}")
            return []

    def get_user_transactions_simple(self, user_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Method sederhana untuk mendapatkan transaksi user"""
        try:
            query = {"user_id": user_id}
            transactions = self.find_many(query, limit=limit, sort=[("timestamp", -1)])
            
            # Ensure we always return a list, never None
            if transactions is None:
                transactions = []
            
            # Format data agar mudah digunakan di template
            for tx in transactions:
                # Pastikan field yang diperlukan ada
                tx.setdefault("amount", 0)
                tx.setdefault("type", "expense")
                tx.setdefault("note", "")
                tx.setdefault("scope_id", "")
                tx.setdefault("wallet_id", "")
                tx.setdefault("category_id", "")
                tx.setdefault("tags", [])
                
                # Format timestamp
                if "timestamp" in tx:
                    from datetime import datetime
                    try:
                        tx["formatted_time"] = datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        tx["formatted_time"] = "Invalid Time"
            
            return transactions
        except Exception as e:
            print(f"Error in get_user_transactions_simple: {e}")
            return []
    
    def get_transactions_by_scope(self, user_id: str, scope_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Method untuk mendapatkan transaksi berdasarkan scope tertentu"""
        try:
            query = {"user_id": user_id, "scope_id": scope_id}
            transactions = self.find_many(query, limit=limit, sort=[("timestamp", -1)])
            
            # Ensure we always return a list, never None
            if transactions is None:
                transactions = []
            
            # Format data agar mudah digunakan di template
            for tx in transactions:
                # Pastikan field yang diperlukan ada
                tx.setdefault("amount", 0)
                tx.setdefault("type", "expense")
                tx.setdefault("note", "")
                tx.setdefault("scope_id", "")
                tx.setdefault("wallet_id", "")
                tx.setdefault("category_id", "")
                tx.setdefault("tags", [])
                
                # Format timestamp
                if "timestamp" in tx:
                    from datetime import datetime
                    try:
                        tx["formatted_time"] = datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        tx["formatted_time"] = "Invalid Time"
            
            return transactions
        except Exception as e:
            print(f"Error in get_transactions_by_scope: {e}")
            return []

    def get_transactions_with_filters(self, user_id: str, filters: Dict[str, Any] = None, limit: int = 200) -> List[Dict[str, Any]]:
        """Method untuk mendapatkan transaksi dengan multiple filters"""
        try:
            print(f"🔍 [REPO] get_transactions_with_filters called with user_id: {user_id}, filters: {filters}")
            
            # Base query selalu include user_id
            query = {"user_id": user_id}
            
            # Apply filters
            if filters:
                if filters.get("scope_id"):
                    query["scope_id"] = filters["scope_id"]
                
                if filters.get("category_id"):
                    query["category_id"] = filters["category_id"]
                
                if filters.get("wallet_id"):
                    query["wallet_id"] = filters["wallet_id"]
                
                if filters.get("type"):
                    query["type"] = filters["type"]
                
                if filters.get("tags") and isinstance(filters["tags"], list):
                    # Filter berdasarkan tags (OR condition)
                    query["tags"] = {"$in": filters["tags"]}
                
                if filters.get("date_from") or filters.get("date_to"):
                    date_query = {}
                    if filters.get("date_from"):
                        date_query["$gte"] = int(filters["date_from"])
                    if filters.get("date_to"):
                        date_query["$lte"] = int(filters["date_to"])
                    if date_query:
                        query["timestamp"] = date_query
                
                if filters.get("amount_min") or filters.get("amount_max"):
                    amount_query = {}
                    if filters.get("amount_min"):
                        amount_query["$gte"] = float(filters["amount_min"])
                    if filters.get("amount_max"):
                        amount_query["$lte"] = float(filters["amount_max"])
                    if amount_query:
                        query["amount"] = amount_query
            
            print(f"🔍 [REPO] Final query: {query}")
            
            transactions = self.find_many(query, limit=limit, sort=[("timestamp", -1)])
            
            print(f"🔍 [REPO] find_many result type: {type(transactions)}")
            print(f"🔍 [REPO] find_many result: {transactions}")
            
            # Ensure we always return a list, never None
            if transactions is None:
                print(f"⚠️ [REPO] Transactions is None, returning empty list")
                transactions = []
            elif not isinstance(transactions, list):
                print(f"⚠️ [REPO] Transactions is not a list, converting to list")
                transactions = list(transactions) if transactions else []
            
            print(f"🔍 [REPO] After validation - transactions type: {type(transactions)}")
            print(f"🔍 [REPO] After validation - transactions length: {len(transactions) if transactions else 0}")
            
            # Format data agar mudah digunakan di template
            for tx in transactions:
                # Pastikan field yang diperlukan ada
                tx.setdefault("amount", 0)
                tx.setdefault("type", "expense")
                tx.setdefault("note", "")
                tx.setdefault("scope_id", "")
                tx.setdefault("wallet_id", "")
                tx.setdefault("category_id", "")
                tx.setdefault("tags", [])
                
                # Format timestamp
                if "timestamp" in tx:
                    from datetime import datetime
                    try:
                        tx["formatted_time"] = datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        tx["formatted_time"] = "Invalid Time"
            
            print(f"🔍 [REPO] Returning {len(transactions)} formatted transactions")
            return transactions
        except Exception as e:
            print(f"❌ [REPO] Error in get_transactions_with_filters: {e}")
            print(f"❌ [REPO] Error type: {type(e)}")
            import traceback
            print(f"❌ [REPO] Error traceback: {traceback.format_exc()}")
            return []
    
    def update_transaction(self, transaction_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update transaksi dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(transaction_id)
            
            # Pastikan transaksi milik user yang bersangkutan
            existing_tx = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_tx:
                return False
            
            # Tambah timestamp update
            updates["updated_at"] = int(time.time())
            
            # Update dengan ObjectId
            result = self.collection.update_one({"_id": obj_id}, {"$set": updates})
            return result.modified_count > 0
        except Exception:
            return False
    
    def delete_transaction(self, transaction_id: str, user_id: str) -> bool:
        """Delete transaksi dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(transaction_id)
            
            # Pastikan transaksi milik user yang bersangkutan
            existing_tx = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_tx:
                return False
            
            # Delete dengan ObjectId
            result = self.collection.delete_one({"_id": obj_id})
            return result.deleted_count > 0
        except Exception:
            return False
    
    def get_transaction_by_id(self, transaction_id: str, user_id: str) -> Dict[str, Any]:
        """Get transaksi berdasarkan ID dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(transaction_id)
            
            transaction = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if transaction:
                # Convert ObjectId ke string
                transaction["_id"] = str(transaction["_id"])
                
                # Format data
                transaction.setdefault("amount", 0)
                transaction.setdefault("type", "expense")
                transaction.setdefault("note", "")
                transaction.setdefault("scope_id", "")
                transaction.setdefault("wallet_id", "")
                transaction.setdefault("category_id", "")
                transaction.setdefault("tags", [])
                
                # Format timestamp
                if "timestamp" in transaction:
                    from datetime import datetime
                    try:
                        transaction["formatted_time"] = datetime.fromtimestamp(transaction["timestamp"]).strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        transaction["formatted_time"] = "Invalid Time"
            
            return transaction or {}
        except Exception:
            return {}


