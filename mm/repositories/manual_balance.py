from typing import Any, Dict, List, Optional
from bson import ObjectId
from mm.repositories.base import MongoRepository
from datetime import datetime


class ManualBalanceRepository(MongoRepository):
    def __init__(self):
        super().__init__("manual_balances")

    def get_latest_balance(self, user_id: str, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get balance terbaru untuk wallet tertentu"""
        try:
            query = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "is_latest": True
            }
            return self.find_one(query)
        except Exception as e:
            print(f"❌ [MANUAL_BALANCE] Error getting latest balance: {e}")
            return None

    def get_balance_history(self, user_id: str, wallet_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get history balance untuk wallet tertentu (sorted by timestamp descending)"""
        try:
            query = {
                "user_id": user_id,
                "wallet_id": wallet_id
            }
            # Sort by balance_date descending (newest first) untuk dropdown
            return self.find_many(query, sort=[("balance_date", -1)], limit=limit)
        except Exception as e:
            print(f"❌ [MANUAL_BALANCE] Error getting balance history: {e}")
            return []

    def create_balance(self, user_id: str, wallet_id: str, balance_data: Dict[str, Any]) -> Optional[str]:
        """Create balance baru dan set balance lama menjadi tidak latest"""
        try:
            # Get sequence number untuk wallet ini
            last_balance = self.collection.find_one(
                {"user_id": user_id, "wallet_id": wallet_id},
                sort=[("sequence_number", -1)]
            )
            next_sequence = (last_balance.get("sequence_number", 0) + 1) if last_balance else 1
            
            # Close balance lama jika ada
            if last_balance and last_balance.get("is_latest", False):
                # Close balance = nominal terbaru dari manual balance yang diinput user
                # Bukan hasil kalkulasi dari transaksi
                close_balance = float(balance_data.get("balance_amount", 0))
                
                # Update balance lama menjadi closed
                self.collection.update_one(
                    {"_id": last_balance["_id"]},
                    {
                        "$set": {
                            "is_latest": False,
                            "is_closed": True,
                            "close_balance": close_balance,  # Menggunakan balance_amount dari input user
                            "close_date": int(datetime.now().timestamp()),
                            "updated_at": int(datetime.now().timestamp())
                        }
                    }
                )
                print(f"🔒 [MANUAL_BALANCE] Closed previous balance {last_balance['_id']} with close_balance: {close_balance}")
            
            # Set semua balance lama untuk wallet ini menjadi tidak latest
            self.collection.update_many(
                {
                    "user_id": user_id,
                    "wallet_id": wallet_id,
                    "is_latest": True
                },
                {"$set": {"is_latest": False}}
            )

            # Set timestamp dan created_at
            current_time = int(datetime.now().timestamp())
            balance_data.update({
                "user_id": user_id,
                "wallet_id": wallet_id,
                "balance_date": current_time,
                "created_at": current_time,
                "updated_at": current_time,
                "is_latest": True,
                "sequence_number": next_sequence,
                "is_closed": False,
                "close_balance": 0.0,
                "close_date": 0
            })

            # Insert balance baru
            _id = self.insert_one(balance_data)
            print(f"✅ [MANUAL_BALANCE] Created new balance: {_id} with sequence: {next_sequence}")
            
            # Update wallet actual_balance
            if _id:
                try:
                    from mm.repositories.wallets import WalletRepository
                    wallet_repo = WalletRepository()
                    
                    # Update actual_balance di wallet
                    balance_amount = float(balance_data.get("balance_amount", 0))
                    wallet_updated = wallet_repo.update_wallet_balance(
                        wallet_id=wallet_id,
                        user_id=user_id,
                        actual_balance=balance_amount
                    )
                    
                    if wallet_updated:
                        print(f"💰 [MANUAL_BALANCE] Successfully updated wallet actual_balance: {balance_amount}")
                    else:
                        print(f"⚠️ [MANUAL_BALANCE] Failed to update wallet actual_balance")
                        
                except Exception as e:
                    print(f"❌ [MANUAL_BALANCE] Error updating wallet balance: {e}")
            
            return _id

        except Exception as e:
            print(f"❌ [MANUAL_BALANCE] Error creating balance: {e}")
            import traceback
            print(f"❌ [MANUAL_BALANCE] Error traceback: {traceback.format_exc()}")
            return None

    def update_balance(self, balance_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update balance yang ada"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(balance_id)
            
            # Pastikan balance milik user yang bersangkutan
            existing_balance = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_balance:
                print(f"❌ [MANUAL_BALANCE] Balance not found or not owned by user")
                return False
            
            # Update dengan ObjectId
            updates["updated_at"] = int(datetime.now().timestamp())
            result = self.collection.update_one({"_id": obj_id}, {"$set": updates})
            
            success = result.modified_count > 0
            print(f"✅ [MANUAL_BALANCE] Update success: {success}")
            return success

        except Exception as e:
            print(f"❌ [MANUAL_BALANCE] Error updating balance: {e}")
            import traceback
            print(f"❌ [MANUAL_BALANCE] Error traceback: {traceback.format_exc()}")
            return False

    def delete_balance(self, balance_id: str, user_id: str) -> bool:
        """Delete balance dengan validasi user ownership"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(balance_id)
            
            # Pastikan balance milik user yang bersangkutan
            existing_balance = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_balance:
                return False
            
            # Delete dengan ObjectId
            result = self.collection.delete_one({"_id": obj_id})
            return result.deleted_count > 0

        except Exception:
            return False

    def get_user_balances(self, user_id: str) -> List[Dict[str, Any]]:
        """Get semua balance untuk user tertentu"""
        try:
            query = {"user_id": user_id, "is_latest": True}
            return self.find_many(query)
        except Exception as e:
            print(f"❌ [MANUAL_BALANCE] Error getting user balances: {e}")
            return []

    def get_balance_summary(self, user_id: str, wallet_id: str) -> Dict[str, Any]:
        """Get summary balance untuk wallet tertentu termasuk history dan transaksi"""
        try:
            from mm.repositories.transactions import TransactionRepository
            
            # Get latest balance
            latest_balance = self.get_latest_balance(user_id, wallet_id)
            
            # Get balance history
            balance_history = self.get_balance_history(user_id, wallet_id, limit=100)
            
            # Get transactions yang menggunakan manual balance ini
            tx_repo = TransactionRepository()
            transactions = []
            
            if latest_balance:
                manual_balance_id = str(latest_balance["_id"])
                transactions = tx_repo.get_transactions_by_manual_balance(user_id, manual_balance_id, limit=1000)
            
            return {
                "latest_balance": latest_balance,
                "balance_history": balance_history,
                "transactions_count": len(transactions),
                "transactions": transactions[:10]  # Limit untuk preview
            }
            
        except Exception as e:
            print(f"❌ [MANUAL_BALANCE] Error getting balance summary: {e}")
            return {
                "latest_balance": None,
                "balance_history": [],
                "transactions_count": 0,
                "transactions": []
            }
    
    def get_balance_by_sequence(self, user_id: str, wallet_id: str, sequence_number: int) -> Optional[Dict[str, Any]]:
        """Get balance berdasarkan sequence number"""
        try:
            query = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "sequence_number": sequence_number
            }
            return self.find_one(query)
        except Exception as e:
            print(f"❌ [MANUAL_BALANCE] Error getting balance by sequence: {e}")
            return None
    
    def get_balance_sequence_summary(self, user_id: str, wallet_id: str) -> Dict[str, Any]:
        """Get summary semua sequence balance untuk wallet tertentu"""
        try:
            query = {
                "user_id": user_id,
                "wallet_id": wallet_id
            }
            
            # Sort by sequence number
            balances = self.find_many(query, sort=[("sequence_number", 1)], limit=100)
            
            # Group by sequence dan hitung ghost transaction
            sequence_summary = []
            for balance in balances:
                if balance.get("is_closed", False):
                    # Hitung ghost transaction dari close_balance
                    from mm.repositories.transactions import TransactionRepository
                    tx_repo = TransactionRepository()
                    
                    # Get transaksi yang menggunakan manual balance ini
                    manual_balance_id = str(balance["_id"])
                    transactions = tx_repo.get_transactions_by_manual_balance(user_id, manual_balance_id, limit=1000)
                    
                    # Hitung expected balance dari transaksi
                    expected_balance = float(balance.get("balance_amount", 0))
                    for tx in transactions:
                        if tx.get("type") == "income":
                            expected_balance += float(tx.get("amount", 0))
                        elif tx.get("type") == "expense":
                            expected_balance -= float(tx.get("amount", 0))
                    
                    # Ghost amount = close_balance - expected_balance
                    # close_balance sekarang adalah nominal terbaru dari manual balance user
                    close_balance = float(balance.get("close_balance", 0))
                    ghost_amount = close_balance - expected_balance
                    
                    sequence_summary.append({
                        "sequence_number": balance.get("sequence_number", 0),
                        "balance_amount": balance.get("balance_amount", 0),
                        "balance_date": balance.get("balance_date", 0),
                        "close_balance": close_balance,  # Nominal terbaru dari manual balance user
                        "close_date": balance.get("close_date", 0),
                        "is_closed": True,
                        "ghost_amount": ghost_amount,  # Selisih antara close_balance dan expected_balance
                        "transactions_count": len(transactions)
                    })
                else:
                    # Balance yang masih aktif
                    sequence_summary.append({
                        "sequence_number": balance.get("sequence_number", 0),
                        "balance_amount": balance.get("balance_amount", 0),
                        "balance_date": balance.get("balance_date", 0),
                        "is_closed": False,
                        "ghost_amount": 0,
                        "transactions_count": 0
                    })
            
            return {
                "wallet_id": wallet_id,
                "total_sequences": len(sequence_summary),
                "sequences": sequence_summary
            }
            
        except Exception as e:
            print(f"❌ [MANUAL_BALANCE] Error getting balance sequence summary: {e}")
            return {
                "wallet_id": wallet_id,
                "total_sequences": 0,
                "sequences": []
            }
