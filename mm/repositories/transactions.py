from typing import Any, Dict, List, Optional
import time
from bson import ObjectId
from mm.repositories.base import MongoRepository
from datetime import datetime


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
                tx.setdefault("fk_real_balance_id", "")
                tx.setdefault("tags", [])
                tx.setdefault("balance_before", 0)
                tx.setdefault("balance_after", 0)
                
                # Format timestamp
                if "timestamp" in tx:
                    try:
                        tx["formatted_time"] = datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        tx["formatted_time"] = "Invalid Time"
            
            return transactions
        except Exception as e:
            print(f"Error in get_user_transactions_simple: {e}")
            return []

    def get_user_transactions_by_date_range(self, user_id: str, start_timestamp: int, end_timestamp: int, limit: int = 200) -> List[Dict[str, Any]]:
        """Get user transactions within a specific date range"""
        try:
            query = {
                "user_id": user_id,
                "timestamp": {
                    "$gte": start_timestamp,
                    "$lt": end_timestamp
                }
            }
            transactions = self.find_many(query, limit=limit, sort=[("timestamp", -1)])
            
            # Ensure we always return a list, never None
            if transactions is None:
                transactions = []
            
            # Format data for easy use
            for tx in transactions:
                # Ensure required fields exist
                tx.setdefault("amount", 0)
                tx.setdefault("type", "expense")
                tx.setdefault("note", "")
                tx.setdefault("scope_id", "")
                tx.setdefault("wallet_id", "")
                tx.setdefault("category_id", "")
                tx.setdefault("fk_real_balance_id", "")
                tx.setdefault("tags", [])
                tx.setdefault("balance_before", 0)
                tx.setdefault("balance_after", 0)
                
                # Format timestamp
                if "timestamp" in tx:
                    try:
                        tx["formatted_time"] = datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                        tx["date"] = datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        tx["formatted_time"] = "Invalid Date"
                        tx["date"] = "Invalid Date"
                
                # Get category name if category_id exists
                if tx.get("category_id"):
                    try:
                        from mm.repositories.categories import CategoryRepository
                        category_repo = CategoryRepository()
                        category = category_repo.find_by_id(tx["category_id"])
                        if category:
                            tx["category_name"] = category.get("name", "Unknown")
                        else:
                            tx["category_name"] = "Unknown"
                    except Exception:
                        tx["category_name"] = "Unknown"
                else:
                    tx["category_name"] = "Uncategorized"
                
                # Get scope name if scope_id exists
                if tx.get("scope_id"):
                    try:
                        from mm.repositories.scopes import ScopeRepository
                        scope_repo = ScopeRepository()
                        scope = scope_repo.find_by_id(tx["scope_id"])
                        if scope:
                            tx["scope_name"] = scope.get("name", "Unknown")
                        else:
                            tx["scope_name"] = "Unknown"
                    except Exception:
                        tx["scope_name"] = "Unknown"
                else:
                    tx["scope_name"] = "No Scope"
                
                # Get wallet name if wallet_id exists
                if tx.get("wallet_id"):
                    try:
                        from mm.repositories.wallets import WalletRepository
                        wallet_repo = WalletRepository()
                        wallet = wallet_repo.find_by_id(tx["wallet_id"])
                        if wallet:
                            tx["wallet_name"] = wallet.get("name", "Unknown")
                            print(f"🔍 [TX] Found wallet: {tx['wallet_name']} for wallet_id: {tx['wallet_id']}")
                        else:
                            tx["wallet_name"] = "Unknown"
                            print(f"❌ [TX] Wallet not found for wallet_id: {tx['wallet_id']}")
                    except Exception as e:
                        tx["wallet_name"] = "Unknown"
                        print(f"❌ [TX] Error getting wallet for wallet_id {tx['wallet_id']}: {e}")
                else:
                    tx["wallet_name"] = "No Wallet"
                    print(f"⚠️ [TX] No wallet_id in transaction")
            
            return transactions
        except Exception as e:
            print(f"Error in get_user_transactions_by_date_range: {e}")
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
                tx.setdefault("fk_real_balance_id", "")
                tx.setdefault("tags", [])
                tx.setdefault("balance_before", 0)
                tx.setdefault("balance_after", 0)
                
                # Format timestamp
                if "timestamp" in tx:
                    try:
                        tx["formatted_time"] = datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        tx["formatted_time"] = "Invalid Time"
            
            return transactions
        except Exception as e:
            print(f"Error in get_transactions_by_scope: {e}")
            return []

    def get_active_manual_balance_id(self, user_id: str, wallet_id: str, timestamp: int) -> Optional[str]:
        """Get manual balance ID yang aktif saat transaksi dibuat berdasarkan timestamp"""
        try:
            from mm.repositories.manual_balance import ManualBalanceRepository
            balance_repo = ManualBalanceRepository()
            
            # Get manual balance yang balance_date <= timestamp transaksi
            # Dan yang memiliki sequence number terakhir (is_latest = True)
            query = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "balance_date": {"$lte": timestamp},
                "is_latest": True
            }
            
            # Sort by sequence_number descending untuk dapat yang terbaru
            balance = balance_repo.collection.find_one(
                query, 
                sort=[("sequence_number", -1)]
            )
            
            if balance:
                print(f"🔗 [TRANSACTIONS] Found active manual balance: {balance['_id']} (seq: {balance.get('sequence_number', 0)})")
                return str(balance["_id"])
            
            # Fallback: jika tidak ada yang is_latest, cari berdasarkan balance_date
            fallback_query = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "balance_date": {"$lte": timestamp}
            }
            
            fallback_balance = balance_repo.collection.find_one(
                fallback_query, 
                sort=[("balance_date", -1)]
            )
            
            if fallback_balance:
                print(f"⚠️ [TRANSACTIONS] Using fallback manual balance: {fallback_balance['_id']} (seq: {fallback_balance.get('sequence_number', 0)})")
                return str(fallback_balance["_id"])
            
            print(f"⚠️ [TRANSACTIONS] No manual balance found for user: {user_id}, wallet: {wallet_id}")
            return None
            
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error getting active manual balance ID: {e}")
            return None

    def migrate_existing_transactions(self, user_id: str = None):
        """Migrate transaksi yang sudah ada untuk menambahkan fk_manual_balance_id dan sequence_number"""
        try:
            print(f"🔄 [TRANSACTIONS] Starting migration for existing transactions...")
            
            # Query untuk transaksi yang belum ada fk_manual_balance_id
            query = {}
            if user_id:
                query["user_id"] = user_id
            
            # Cari transaksi yang belum ada fk_manual_balance_id
            transactions_to_migrate = self.collection.find({
                **query,
                "$or": [
                    {"fk_manual_balance_id": {"$exists": False}},
                    {"fk_manual_balance_id": ""},
                    {"fk_manual_balance_id": None}
                ]
            })
            
            migrated_count = 0
            for tx in transactions_to_migrate:
                try:
                    tx_user_id = tx.get("user_id")
                    tx_wallet_id = tx.get("wallet_id")
                    tx_timestamp = tx.get("timestamp", 0)
                    
                    if not tx_user_id or not tx_wallet_id:
                        print(f"⚠️ [TRANSACTIONS] Skipping transaction {tx['_id']}: missing user_id or wallet_id")
                        continue
                    
                    # Get active manual balance untuk timestamp transaksi
                    manual_balance_id = self.get_active_manual_balance_id(tx_user_id, tx_wallet_id, tx_timestamp)
                    
                    if manual_balance_id:
                        # Get next sequence number
                        next_sequence = self.get_next_sequence_number(tx_user_id, tx_wallet_id, manual_balance_id)
                        
                        # Update transaction
                        update_result = self.collection.update_one(
                            {"_id": tx["_id"]},
                            {
                                "$set": {
                                    "fk_manual_balance_id": manual_balance_id,
                                    "sequence_number": next_sequence,
                                    "updated_at": int(time.time())
                                }
                            }
                        )
                        
                        if update_result.modified_count > 0:
                            print(f"✅ [TRANSACTIONS] Migrated transaction {tx['_id']}: manual_balance_id={manual_balance_id}, sequence={next_sequence}")
                            migrated_count += 1
                        else:
                            print(f"⚠️ [TRANSACTIONS] No changes made to transaction {tx['_id']}")
                    else:
                        print(f"⚠️ [TRANSACTIONS] No manual balance found for transaction {tx['_id']}")
                        
                except Exception as e:
                    print(f"❌ [TRANSACTIONS] Error migrating transaction {tx.get('_id', 'unknown')}: {e}")
                    continue
            
            print(f"✅ [TRANSACTIONS] Migration completed. {migrated_count} transactions migrated.")
            return migrated_count
            
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error in migration: {e}")
            import traceback
            print(f"❌ [TRANSACTIONS] Error traceback: {traceback.format_exc()}")
            return 0

    def get_manual_balance_at_timestamp(self, user_id: str, wallet_id: str, timestamp: int) -> Optional[Dict[str, Any]]:
        """Get manual balance yang aktif pada timestamp tertentu"""
        try:
            from mm.repositories.manual_balance import ManualBalanceRepository
            balance_repo = ManualBalanceRepository()
            
            query = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "balance_date": {"$lte": timestamp}
            }
            
            return balance_repo.collection.find_one(query, sort=[("balance_date", -1)])
            
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error getting manual balance at timestamp: {e}")
            return None

    def get_transactions_by_manual_balance(self, user_id: str, manual_balance_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get transaksi berdasarkan manual balance ID"""
        try:
            query = {
                "user_id": user_id,
                "fk_manual_balance_id": manual_balance_id
            }
            
            transactions = self.find_many(query, sort=[("timestamp", -1)], limit=limit)
            
            # Set default values untuk backward compatibility
            for tx in transactions:
                tx.setdefault("fk_manual_balance_id", "")
            
            return transactions
            
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error getting transactions by manual balance: {e}")
            return []

    def get_transactions_after_manual_balance(self, user_id: str, wallet_id: str, balance_timestamp: int, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get transaksi yang dibuat setelah manual balance tertentu"""
        try:
            query = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "timestamp": {"$gt": balance_timestamp}
            }
            
            return self.find_many(query, sort=[("timestamp", 1)], limit=limit)
            
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error getting transactions after manual balance: {e}")
            return []

    def get_next_sequence_number(self, user_id: str, wallet_id: str, manual_balance_id: str) -> int:
        """Get sequence number berikutnya untuk transaksi dalam manual balance tertentu"""
        try:
            query = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "fk_manual_balance_id": manual_balance_id
            }
            
            last_tx = self.collection.find_one(query, sort=[("sequence_number", -1)])
            return (last_tx.get("sequence_number", 0) + 1) if last_tx else 1
            
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error getting next sequence number: {e}")
            return 1

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
                tx.setdefault("fk_real_balance_id", "")
                tx.setdefault("tags", [])
                tx.setdefault("balance_before", 0)
                tx.setdefault("balance_after", 0)
                
                # Format timestamp
                if "timestamp" in tx:
                    try:
                        tx["formatted_time"] = datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
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
    
    def insert_one(self, data: Dict[str, Any]) -> Optional[str]:
        """Insert transaksi baru dengan auto-populate manual balance ID"""
        try:
            # Auto-populate fk_manual_balance_id jika tidak ada
            if "fk_manual_balance_id" not in data or not data["fk_manual_balance_id"]:
                user_id = data.get("user_id")
                wallet_id = data.get("wallet_id")
                timestamp = data.get("timestamp", int(datetime.now().timestamp()))
                
                if user_id and wallet_id:
                    manual_balance_id = self.get_active_manual_balance_id(user_id, wallet_id, timestamp)
                    if manual_balance_id:
                        data["fk_manual_balance_id"] = manual_balance_id
                        print(f"🔗 [TRANSACTIONS] Auto-linked to manual balance: {manual_balance_id}")
            
            # Auto-populate sequence_number jika tidak ada
            if "sequence_number" not in data or not data["sequence_number"]:
                user_id = data.get("user_id")
                wallet_id = data.get("wallet_id")
                manual_balance_id = data.get("fk_manual_balance_id")
                
                if user_id and wallet_id and manual_balance_id:
                    next_sequence = self.get_next_sequence_number(user_id, wallet_id, manual_balance_id)
                    data["sequence_number"] = next_sequence
                    print(f"🔢 [TRANSACTIONS] Auto-assigned sequence: {next_sequence}")
            
            # Set timestamp jika tidak ada
            if "timestamp" not in data:
                data["timestamp"] = int(datetime.now().timestamp())
            
            # Validasi dan konversi amount field
            if "amount" in data:
                try:
                    # Handle berbagai tipe data amount
                    amount_value = data["amount"]
                    if isinstance(amount_value, str):
                        # Jika string kosong atau whitespace, set ke 0
                        if not amount_value.strip():
                            data["amount"] = 0.0
                            print(f"⚠️ [TRANSACTIONS] Empty amount string, setting to 0")
                        else:
                            # Coba konversi string ke float
                            data["amount"] = float(amount_value)
                            print(f"💰 [TRANSACTIONS] Converted amount string to float: {data['amount']}")
                    elif isinstance(amount_value, (int, float)):
                        # Jika sudah numeric, pastikan float
                        data["amount"] = float(amount_value)
                    else:
                        # Jika tipe data tidak valid, set ke 0
                        print(f"⚠️ [TRANSACTIONS] Invalid amount type: {type(amount_value)}, setting to 0")
                        data["amount"] = 0.0
                except (ValueError, TypeError) as e:
                    print(f"⚠️ [TRANSACTIONS] Error converting amount '{amount_value}': {e}, setting to 0")
                    data["amount"] = 0.0
            else:
                # Jika amount tidak ada, set default 0
                data["amount"] = 0.0
                print(f"⚠️ [TRANSACTIONS] Amount field missing, setting to 0")
            
            # Set created_at dan updated_at
            current_time = int(datetime.now().timestamp())
            data["created_at"] = current_time
            data["updated_at"] = current_time
            
            # Tambahkan field balance tracking sebelum transaksi
            # Skip balance tracking for transfer fee transactions as they already have correct values
            if data.get("wallet_id") and data.get("user_id") and not data.get("is_transfer_fee"):
                from mm.repositories.wallets import WalletRepository
                wallet_repo = WalletRepository()
                wallet = wallet_repo.get_wallet_by_id(data["wallet_id"], data["user_id"])
                if wallet:
                    # Balance sebelum transaksi
                    data["balance_before"] = float(wallet.get("actual_balance", 0))
                    print(f"💰 [TRANSACTIONS] Balance before transaction: {data['balance_before']}")
            elif data.get("is_transfer_fee"):
                print(f"💰 [TRANSACTIONS] Skipping balance_before overwrite for transfer fee transaction")
                print(f"💰 [TRANSACTIONS] Keeping calculated balance_before: {data.get('balance_before')}")
            
            # Insert ke database
            result = self.collection.insert_one(data)
            
            if result.inserted_id:
                print(f"✅ [TRANSACTIONS] Inserted transaction: {result.inserted_id}")
                
                # Auto-update wallet balance setelah transaksi berhasil dibuat
                # Skip balance update if flag is set (for transfers)
                if (data.get("wallet_id") and data.get("user_id") and 
                    not data.get("skip_balance_update", False)):
                    
                    success = self._update_wallet_balance_after_transaction(
                        data["wallet_id"], 
                        data["user_id"], 
                        data.get("type", "expense"), 
                        float(data.get("amount", 0))
                    )
                    
                    # Tambahkan field balance setelah transaksi jika update berhasil
                    if success:
                        from mm.repositories.wallets import WalletRepository
                        wallet_repo = WalletRepository()
                        updated_wallet = wallet_repo.get_wallet_by_id(data["wallet_id"], data["user_id"])
                        if updated_wallet:
                            balance_after = float(updated_wallet.get("actual_balance", 0))
                            # Update transaksi dengan balance setelah
                            self.collection.update_one(
                                {"_id": result.inserted_id},
                                {"$set": {"balance_after": balance_after}}
                            )
                            print(f"💰 [TRANSACTIONS] Balance after transaction: {balance_after}")
                else:
                    print(f"⏭️ [TRANSACTIONS] Skipping automatic balance update (skip_balance_update flag set)")
                
                return str(result.inserted_id)
            else:
                print("❌ [TRANSACTIONS] Failed to insert transaction")
                return None
                
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error inserting transaction: {e}")
            import traceback
            print(f"❌ [TRANSACTIONS] Error traceback: {traceback.format_exc()}")
            return None

    def _update_wallet_balance_after_transaction(self, wallet_id: str, user_id: str, transaction_type: str, amount: float) -> bool:
        """Update wallet balance secara otomatis setelah transaksi dibuat"""
        try:
            print(f"💰 [TRANSACTIONS] Auto-updating wallet balance for transaction: {wallet_id}, type: {transaction_type}, amount: {amount}")
            
            from mm.repositories.wallets import WalletRepository
            wallet_repo = WalletRepository()
            
            # Get current wallet using get_wallet_by_id method
            wallet = wallet_repo.get_wallet_by_id(wallet_id, user_id)
            if not wallet:
                print(f"❌ [TRANSACTIONS] Wallet not found: {wallet_id}")
                return False
            
            # Get current actual_balance
            current_balance = float(wallet.get("actual_balance", 0))
            
            # Calculate new balance based on transaction type
            new_balance = current_balance
            if transaction_type == "income":
                new_balance += amount
                print(f"💰 [TRANSACTIONS] Income: {current_balance} + {amount} = {new_balance}")
            elif transaction_type == "expense":
                new_balance -= amount
                print(f"💰 [TRANSACTIONS] Expense: {current_balance} - {amount} = {new_balance}")
            elif transaction_type == "transfer":
                # For transfers, we need to check if it's incoming or outgoing
                # This will be handled by the transfer logic
                print(f"💰 [TRANSACTIONS] Transfer transaction - balance update handled by transfer logic")
                return True
            else:
                print(f"💰 [TRANSACTIONS] Unknown transaction type: {transaction_type}, skipping balance update")
                return True
            
            # Update wallet balance
            success = wallet_repo.update_wallet_balance(wallet_id, user_id, new_balance)
            
            if success:
                print(f"✅ [TRANSACTIONS] Successfully updated wallet balance: {wallet_id} -> {new_balance}")
            else:
                print(f"❌ [TRANSACTIONS] Failed to update wallet balance: {wallet_id}")
            
            return success
            
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error updating wallet balance: {e}")
            import traceback
            print(f"❌ [TRANSACTIONS] Error traceback: {traceback.format_exc()}")
            return False

    def update_transaction(self, transaction_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update transaksi dengan validasi user ownership dan auto-update wallet balance"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(transaction_id)
            
            # Pastikan transaksi milik user yang bersangkutan
            existing_tx = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_tx:
                return False
            
            # Store old values for balance recalculation
            old_wallet_id = existing_tx.get("wallet_id")
            old_type = existing_tx.get("type")
            
            # Safe conversion untuk old_amount
            try:
                old_amount = float(existing_tx.get("amount", 0))
            except (ValueError, TypeError):
                old_amount = 0.0
                print(f"⚠️ [TRANSACTIONS] Invalid old_amount, setting to 0")
            
            # Tambah timestamp update
            updates["updated_at"] = int(time.time())
            
            # Update dengan ObjectId
            result = self.collection.update_one({"_id": obj_id}, {"$set": updates})
            
            if result.modified_count > 0:
                # Auto-update wallet balance jika ada perubahan yang mempengaruhi balance
                if (old_wallet_id and 
                    (updates.get("wallet_id") != old_wallet_id or 
                     updates.get("type") != old_type or 
                     updates.get("amount") != old_amount)):
                    
                    # Revert old transaction's effect on old wallet
                    if old_wallet_id and old_type and old_amount > 0:
                        self._revert_wallet_balance_change(old_wallet_id, user_id, old_type, old_amount)
                    
                    # Apply new transaction's effect on new wallet
                    new_wallet_id = updates.get("wallet_id", old_wallet_id)
                    new_type = updates.get("type", old_type)
                    
                    # Safe conversion untuk new_amount
                    try:
                        new_amount = float(updates.get("amount", old_amount))
                    except (ValueError, TypeError):
                        new_amount = 0.0
                        print(f"⚠️ [TRANSACTIONS] Invalid new_amount, setting to 0")
                    
                    if new_wallet_id and new_type and new_amount > 0:
                        # Update balance tracking fields
                        from mm.repositories.wallets import WalletRepository
                        wallet_repo = WalletRepository()
                        
                        # Get balance before new transaction
                        wallet = wallet_repo.get_wallet_by_id(new_wallet_id, user_id)
                        if wallet:
                            balance_before = float(wallet.get("actual_balance", 0))
                            updates["balance_before"] = balance_before
                            print(f"💰 [TRANSACTIONS] Updated balance_before: {balance_before}")
                        
                        # Apply new transaction effect
                        success = self._update_wallet_balance_after_transaction(new_wallet_id, user_id, new_type, new_amount)
                        
                        # Get balance after new transaction
                        if success:
                            updated_wallet = wallet_repo.get_wallet_by_id(new_wallet_id, user_id)
                            if updated_wallet:
                                balance_after = float(updated_wallet.get("actual_balance", 0))
                                updates["balance_after"] = balance_after
                                print(f"💰 [TRANSACTIONS] Updated balance_after: {balance_after}")
                                
                                # Update transaksi dengan field balance tracking
                                self.collection.update_one(
                                    {"_id": obj_id},
                                    {"$set": {"balance_before": balance_before, "balance_after": balance_after}}
                                )
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error updating transaction: {e}")
            return False

    def _revert_wallet_balance_change(self, wallet_id: str, user_id: str, transaction_type: str, amount: float) -> bool:
        """Revert wallet balance change when transaction is updated or deleted"""
        try:
            print(f"🔄 [TRANSACTIONS] Reverting wallet balance change: {wallet_id}, type: {transaction_type}, amount: {amount}")
            
            from mm.repositories.wallets import WalletRepository
            wallet_repo = WalletRepository()
            
            # Get current wallet using get_wallet_by_id method
            wallet = wallet_repo.get_wallet_by_id(wallet_id, user_id)
            if not wallet:
                print(f"❌ [TRANSACTIONS] Wallet not found for revert: {wallet_id}")
                return False
            
            # Get current actual_balance
            current_balance = float(wallet.get("actual_balance", 0))
            
            # Calculate reverted balance (opposite of original transaction)
            reverted_balance = current_balance
            if transaction_type == "income":
                reverted_balance -= amount  # Remove income
                print(f"🔄 [TRANSACTIONS] Reverting income: {current_balance} - {amount} = {reverted_balance}")
            elif transaction_type == "expense":
                reverted_balance += amount  # Add back expense
                print(f"🔄 [TRANSACTIONS] Reverting expense: {current_balance} + {amount} = {reverted_balance}")
            else:
                print(f"🔄 [TRANSACTIONS] Unknown transaction type for revert: {transaction_type}")
                return True
            
            # Update wallet balance
            success = wallet_repo.update_wallet_balance(wallet_id, user_id, reverted_balance)
            
            if success:
                print(f"✅ [TRANSACTIONS] Successfully reverted wallet balance: {wallet_id} -> {reverted_balance}")
            else:
                print(f"❌ [TRANSACTIONS] Failed to revert wallet balance: {wallet_id}")
            
            return success
            
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error reverting wallet balance: {e}")
            import traceback
            print(f"❌ [TRANSACTIONS] Error traceback: {traceback.format_exc()}")
            return False

    def delete_transaction(self, transaction_id: str, user_id: str) -> bool:
        """Delete transaksi dengan validasi user ownership dan auto-update wallet balance"""
        try:
            # Convert string ID ke ObjectId
            obj_id = ObjectId(transaction_id)
            
            # Pastikan transaksi milik user yang bersangkutan
            existing_tx = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_tx:
                return False
            
            # Store transaction details for balance reversion
            wallet_id = existing_tx.get("wallet_id")
            transaction_type = existing_tx.get("type")
            
            # Safe conversion untuk amount
            try:
                amount = float(existing_tx.get("amount", 0))
            except (ValueError, TypeError):
                amount = 0.0
                print(f"⚠️ [TRANSACTIONS] Invalid amount for deletion, setting to 0")
            
            # Delete dengan ObjectId
            result = self.collection.delete_one({"_id": obj_id})
            
            if result.deleted_count > 0:
                # Auto-update wallet balance setelah transaksi dihapus
                if wallet_id and transaction_type and amount > 0:
                    # Get balance before deletion for logging
                    from mm.repositories.wallets import WalletRepository
                    wallet_repo = WalletRepository()
                    wallet = wallet_repo.get_wallet_by_id(wallet_id, user_id)
                    if wallet:
                        balance_before = float(wallet.get("actual_balance", 0))
                        print(f"💰 [TRANSACTIONS] Balance before deletion: {balance_before}")
                    
                    # Revert balance change
                    success = self._revert_wallet_balance_change(wallet_id, user_id, transaction_type, amount)
                    
                    # Log balance after deletion
                    if success:
                        updated_wallet = wallet_repo.get_wallet_by_id(wallet_id, user_id)
                        if updated_wallet:
                            balance_after = float(updated_wallet.get("actual_balance", 0))
                            print(f"💰 [TRANSACTIONS] Balance after deletion: {balance_after}")
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ [TRANSACTIONS] Error deleting transaction: {e}")
            return False
    
    def recalculate_wallet_balances(self, user_id: str, wallet_id: str) -> Dict[str, Any]:
        """Recalculate all balance_before and balance_after for transactions in a specific wallet"""
        try:
            print(f"🔄 [BALANCE] Starting balance recalculation for wallet: {wallet_id}")
            
            # Get all transactions for this wallet, sorted by timestamp ascending
            query = {
                "user_id": user_id,
                "wallet_id": wallet_id
            }
            
            transactions = list(self.collection.find(query).sort("timestamp", 1))
            
            if not transactions:
                print(f"⚠️ [BALANCE] No transactions found for wallet: {wallet_id}")
                return {"success": True, "message": "No transactions to recalculate", "updated_count": 0}
            
            print(f"🔍 [BALANCE] Found {len(transactions)} transactions to recalculate")
            
            # Get the starting balance from the wallet
            from mm.repositories.wallets import WalletRepository
            wallet_repo = WalletRepository()
            wallet = wallet_repo.get_wallet_by_id(wallet_id, user_id)
            
            if not wallet:
                print(f"❌ [BALANCE] Wallet not found: {wallet_id}")
                return {"success": False, "error": "Wallet not found"}
            
            # Get the current actual balance
            current_balance = float(wallet.get("actual_balance", 0))
            print(f"💰 [BALANCE] Current wallet balance: {current_balance}")
            
            # Calculate what the balance should be by going through all transactions
            calculated_balance = 0.0
            for tx in transactions:
                tx_type = tx.get("type", "expense")
                tx_amount = float(tx.get("amount", 0))
                
                if tx_type == "income":
                    calculated_balance += tx_amount
                elif tx_type == "expense":
                    calculated_balance -= tx_amount
                # Skip transfer types as they're handled separately
                
                print(f"🔍 [BALANCE] Transaction {tx['_id']}: {tx_type} {tx_amount} -> balance: {calculated_balance}")
            
            print(f"💰 [BALANCE] Calculated final balance: {calculated_balance}")
            print(f"💰 [BALANCE] Actual wallet balance: {current_balance}")
            
            # If balances don't match, we need to find the starting balance
            if abs(calculated_balance - current_balance) > 0.01:  # Allow small floating point differences
                print(f"⚠️ [BALANCE] Balance mismatch detected. Need to find correct starting balance.")
                
                # Find the difference and adjust starting balance
                balance_difference = current_balance - calculated_balance
                starting_balance = balance_difference
                print(f"🔍 [BALANCE] Balance difference: {balance_difference}")
                print(f"🔍 [BALANCE] Starting balance should be: {starting_balance}")
            else:
                # Balances match, use 0 as starting balance
                starting_balance = 0.0
                print(f"✅ [BALANCE] Balances match, using starting balance: {starting_balance}")
            
            # Now recalculate all transactions with the correct starting balance
            running_balance = starting_balance
            updated_count = 0
            
            for tx in transactions:
                tx_id = tx["_id"]
                tx_type = tx.get("type", "expense")
                tx_amount = float(tx.get("amount", 0))
                
                # Set balance_before to current running balance
                balance_before = running_balance
                
                # Calculate balance_after based on transaction type
                if tx_type == "income":
                    balance_after = running_balance + tx_amount
                    running_balance = balance_after
                elif tx_type == "expense":
                    balance_after = running_balance - tx_amount
                    running_balance = balance_after
                else:
                    # For transfer types, keep the same balance
                    balance_after = running_balance
                
                # Update the transaction with new balance values
                update_result = self.collection.update_one(
                    {"_id": tx_id},
                    {
                        "$set": {
                            "balance_before": balance_before,
                            "balance_after": balance_after,
                            "updated_at": int(time.time())
                        }
                    }
                )
                
                if update_result.modified_count > 0:
                    updated_count += 1
                    print(f"✅ [BALANCE] Updated transaction {tx_id}: before={balance_before}, after={balance_after}")
                else:
                    print(f"⚠️ [BALANCE] No changes made to transaction {tx_id}")
            
            print(f"✅ [BALANCE] Recalculation completed. Updated {updated_count} transactions.")
            
            return {
                "success": True, 
                "message": f"Successfully recalculated {updated_count} transactions",
                "updated_count": updated_count,
                "starting_balance": starting_balance,
                "final_balance": running_balance
            }
            
        except Exception as e:
            print(f"❌ [BALANCE] Error recalculating balances: {e}")
            import traceback
            print(f"❌ [BALANCE] Error traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

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
                transaction.setdefault("fk_real_balance_id", "")
                transaction.setdefault("balance_before", 0)
                transaction.setdefault("balance_after", 0)
                
                # Format timestamp
                if "timestamp" in transaction:
                    try:
                        transaction["formatted_time"] = datetime.fromtimestamp(transaction["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        transaction["formatted_time"] = "Invalid Time"
            
            return transaction or {}
        except Exception:
            return {}


