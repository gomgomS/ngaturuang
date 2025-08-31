import os
from flask import Flask, render_template, session, request, jsonify, redirect
from mm.repositories.transactions import TransactionRepository
from mm.repositories.scopes import ScopeRepository
from mm.repositories.wallets import WalletRepository
from mm.repositories.categories import CategoryRepository
from mm.repositories.users import UserRepository
from bson import ObjectId
from config import ensure_indexes
from model import index_specs
from mm.repositories.manual_balance import ManualBalanceRepository
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your-secret-key-here"

# Ensure database indexes (with error handling)
try:
    ensure_indexes(index_specs)
    print("✅ Database indexes created successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not create database indexes: {e}")
    print("Application will continue without indexes...")

# Context processor to add total balance to all templates
@app.context_processor
def inject_total_balance():
    """Inject total balance from all user wallets into all templates"""
    try:
        user_id = session.get("user_id")
        if user_id:
            wallet_repo = WalletRepository()
            wallets = wallet_repo.list_by_user(user_id)
            
            # Calculate total balance from all wallets
            total_balance = 0
            for wallet in wallets:
                actual_balance = wallet.get("actual_balance", 0)
                if actual_balance:
                    total_balance += float(actual_balance)
            
            return {"total_balance": total_balance}
        else:
            return {"total_balance": 0}
    except Exception as e:
        print(f"Error calculating total balance: {e}")
        return {"total_balance": 0}

# Custom Jinja filters
@app.template_filter('currency')
def currency_filter(value):
    """Format currency without decimal places"""
    try:
        return "{:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return "0"

@app.template_filter('currency_decimal')
def currency_decimal_filter(value):
    """Format currency with 2 decimal places"""
    try:
        return "{:,.2f}".format(float(value))
    except (ValueError, TypeError):
        return "0.00"

@app.template_filter('datetime')
def datetime_filter(timestamp):
    """Format timestamp to readable datetime"""
    try:
        if not timestamp:
            return "Never"
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%d %b %Y %H:%M")
    except (ValueError, TypeError):
        return "Invalid date"

# Web Routes
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    try:
        user_id = session.get("user_id")
        username = session.get("username")
        
        # Redirect to login if not authenticated
        if not user_id or not username:
            return redirect("/login")
        
        # Get repositories
        tx_repo = TransactionRepository()
        scope_repo = ScopeRepository()
        wallet_repo = WalletRepository()
        
        # Get data based on user_id from database
        transactions = tx_repo.get_user_transactions_simple(user_id, limit=10)
        scopes = scope_repo.list_by_user(user_id)
        wallets = wallet_repo.list_by_user(user_id)
        
        # Calculate totals (including all transactions for accurate display)
        try:
            total_income = sum(float(tx.get("amount", 0)) for tx in transactions if tx.get("type") == "income")
        except (ValueError, TypeError):
            total_income = 0
            
        try:
            total_expense = sum(float(tx.get("amount", 0)) for tx in transactions if tx.get("type") == "expense")
        except (ValueError, TypeError):
            total_expense = 0
        
        try:
            total_transfer = sum(float(tx.get("amount", 0)) for tx in transactions if tx.get("type") == "transfer")
        except (ValueError, TypeError):
            total_transfer = 0
        
        try:
            total_admin_fees = sum(float(tx.get("admin_fee", 0)) for tx in transactions if tx.get("type") == "transfer")
        except (ValueError, TypeError):
            total_admin_fees = 0
            
        balance = total_income - total_expense
        total_transactions = len(transactions)
        
        # Ensure lists are passed
        transactions = transactions or []
        scopes = scopes or []
        wallets = wallets or []
        
        return render_template("dashboard.html", 
                             transactions=transactions,
                             scopes=scopes,
                             wallets=wallets,
                             total_income=total_income,
                             total_expense=total_expense,
                             total_transfer=total_transfer,
                             total_admin_fees=total_admin_fees,
                             balance=balance,
                             total_transactions=total_transactions,
                             username=username)
    except Exception as e:
        print(f"Error in dashboard: {e}")
        return render_template("dashboard.html", 
                             transactions=[],
                             scopes=[],
                             wallets=[],
                             total_income=0,
                             total_expense=0,
                             total_transfer=0,
                             total_admin_fees=0,
                             balance=0,
                             total_transactions=0)

@app.route("/transactions")
def transactions():
    try:
        user_id = session.get("user_id", "demo_user")
        
        # Get repositories
        tx_repo = TransactionRepository()
        scope_repo = ScopeRepository()
        wallet_repo = WalletRepository()
        category_repo = CategoryRepository()
        
        # Get filter parameters
        scope_id = request.args.get("scope_id")
        category_id = request.args.get("category_id")
        wallet_id = request.args.get("wallet_id")
        transaction_type = request.args.get("type")
        tags = request.args.getlist("tags")  # Multiple tags
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        amount_min = request.args.get("amount_min")
        amount_max = request.args.get("amount_max")
        
        # Build filters
        filters = {}
        if scope_id:
            filters["scope_id"] = scope_id
        if category_id:
            filters["category_id"] = category_id
        if wallet_id:
            filters["wallet_id"] = wallet_id
        if transaction_type:
            filters["type"] = transaction_type
        if tags:
            filters["tags"] = tags
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        if amount_min:
            filters["amount_min"] = amount_min
        if amount_max:
            filters["amount_max"] = amount_max
        
        # Get transactions with filters
        if filters:
            transactions = tx_repo.get_transactions_with_filters(user_id, filters, limit=200)
        elif scope_id:
            transactions = tx_repo.get_transactions_by_scope(user_id, scope_id, limit=200)
        else:
            transactions = tx_repo.get_user_transactions_simple(user_id, limit=200)
        
        # Get master data for filters
        scopes = scope_repo.list_by_user(user_id)
        wallets = wallet_repo.list_by_user(user_id)
        categories = category_repo.list_by_user_with_defaults(user_id)  # Include default categories
        
        # Get selected items for display
        selected_scope = None
        selected_category = None
        selected_wallet = None
        
        if scope_id:
            selected_scope = next((s for s in scopes if s.get("_id") == scope_id), None)
        if category_id:
            selected_category = next((c for c in categories if c.get("_id") == category_id), None)
        if wallet_id:
            selected_wallet = next((w for w in wallets if w.get("_id") == wallet_id), None)
        
        # Calculate totals (including all transactions for accurate display)
        try:
            total_income = sum(float(tx.get("amount", 0)) for tx in transactions if tx.get("type") == "income")
        except (ValueError, TypeError):
            total_income = 0
            
        try:
            total_expense = sum(float(tx.get("amount", 0)) for tx in transactions if tx.get("type") == "expense")
        except (ValueError, TypeError):
            total_expense = 0
            
        total_transactions = len(transactions)
        
        # Ensure lists are passed
        transactions = transactions or []
        scopes = scopes or []
        wallets = wallets or []
        categories = categories or []
        
        return render_template("transactions.html",
                             transactions=transactions,
                             scopes=scopes,
                             wallets=wallets,
                             categories=categories,
                             selected_scope=selected_scope,
                             selected_category=selected_category,
                             selected_wallet=selected_wallet,
                             current_scope_id=scope_id,
                             current_category_id=category_id,
                             current_wallet_id=wallet_id,
                             current_type=transaction_type,
                             current_tags=tags,
                             current_date_from=date_from,
                             current_date_to=date_to,
                             current_amount_min=amount_min,
                             current_amount_max=amount_max,
                             total_income=total_income,
                             total_expense=total_expense,
                             total_transactions=total_transactions)
    except Exception as e:
        print(f"Error in transactions: {e}")
        return render_template("transactions.html",
                             transactions=[],
                             scopes=[],
                             wallets=[],
                             categories=[],
                             selected_scope=None,
                             selected_category=None,
                             selected_wallet=None,
                             current_scope_id=None,
                             current_category_id=None,
                             current_wallet_id=None,
                             current_type=None,
                             current_tags=[],
                             current_date_from=None,
                             current_date_to=None,
                             current_amount_min=None,
                             current_amount_max=None,
                             total_income=0,
                             total_expense=0,
                             total_transactions=0)

@app.route("/goals")
def goals():
    return render_template("goals.html")

@app.route("/test-data")
def test_data():
    """Test route to check data structure"""
    try:
        user_id = session.get("user_id", "demo_user")
        
        # Get repositories
        wallet_repo = WalletRepository()
        tx_repo = TransactionRepository()
        
        # Get sample data
        wallets = wallet_repo.list_by_user(user_id)
        transactions = tx_repo.list_by_user(user_id, limit=10)
        
        # Check transactions for each wallet
        wallet_details = []
        for wallet in wallets:
            wallet_id = str(wallet.get("_id"))
            wallet_transactions = tx_repo.get_transactions_with_filters(
                user_id, 
                {"wallet_id": wallet_id}, 
                limit=10
            )
            
            wallet_details.append({
                "wallet_name": wallet.get("name"),
                "wallet_id": wallet_id,
                "transactions_count": len(wallet_transactions) if wallet_transactions else 0,
                "sample_transactions": wallet_transactions[:3] if wallet_transactions else []
            })
        
        test_data = {
            "user_id": user_id,
            "wallets_count": len(wallets) if wallets else 0,
            "transactions_count": len(transactions) if transactions else 0,
            "all_transactions": transactions[:5] if transactions else [],
            "wallet_details": wallet_details
        }
        
        return jsonify(test_data)
    except Exception as e:
        return jsonify({"error": str(e)})



@app.route("/balance")
def balance():
    try:
        user_id = session.get("user_id", "demo_user")
        
        # Get repositories
        wallet_repo = WalletRepository()
        tx_repo = TransactionRepository()
        category_repo = CategoryRepository()
        
        # Get all wallets for the user
        all_wallets = wallet_repo.list_by_user(user_id)
        if all_wallets:
            wallets = all_wallets  # Take all wallets
            print(f"💰 [BALANCE] Found {len(wallets)} wallets for user")
        else:
            wallets = []
            print(f"⚠️ [BALANCE] No wallets found for user")
        
        # Ensure the single wallet has actual_balance field initialized
        for wallet in wallets:
            if "actual_balance" not in wallet or wallet["actual_balance"] is None:
                wallet_id_str = str(wallet.get("_id"))
                print(f"💰 [BALANCE] Initializing actual_balance for wallet: {wallet.get('name')}")
                
                # Set default actual_balance to 0 if not exists
                wallet["actual_balance"] = 0.0
                
                # Update in database
                try:
                    wallet_repo.update_wallet_balance(wallet_id_str, user_id, 0.0)
                    print(f"✅ [BALANCE] Initialized actual_balance for {wallet.get('name')}")
                except Exception as e:
                    print(f"❌ [BALANCE] Failed to initialize actual_balance for {wallet.get('name')}: {e}")
        
        # Get balance data with transactions for the single wallet
        balance_data = []
        for wallet in wallets:
            wallet_id = wallet.get("_id")
            
            # Get transactions for this wallet ONLY
            wallet_id_str = str(wallet_id)
            
            print(f"🔍 Processing wallet: {wallet.get('name')} (ID: {wallet_id_str})")
            
            # Get latest manual balance for this wallet
            latest_manual_balance = None
            try:
                from mm.repositories.manual_balance import ManualBalanceRepository
                manual_balance_repo = ManualBalanceRepository()
                latest_manual_balance = manual_balance_repo.get_latest_balance(user_id, wallet_id_str)
                
                if latest_manual_balance:
                    print(f"🔍 [BALANCE] Found latest manual balance: {latest_manual_balance['_id']} (seq: {latest_manual_balance.get('sequence_number', 0)})")
                else:
                    print(f"⚠️ [BALANCE] No manual balance found for {wallet.get('name')}")
            except Exception as e:
                print(f"❌ [BALANCE] Error getting latest manual balance: {e}")
            
            # Get transactions that belong to this specific wallet AND manual balance sequence
            try:
                print(f"🔍 Querying transactions for wallet {wallet_id_str}")
                
                if latest_manual_balance:
                    # Get transactions from the latest manual balance sequence
                    manual_balance_id = str(latest_manual_balance['_id'])
                    print(f"🔍 [BALANCE] Filtering transactions by manual balance ID: {manual_balance_id}")
                    
                    transactions = tx_repo.get_transactions_by_manual_balance(
                        user_id, 
                        manual_balance_id, 
                        limit=1000
                    )
                else:
                    # Fallback: get all transactions for this wallet
                    print(f"🔍 [BALANCE] No manual balance found, getting all transactions for wallet")
                    transactions = tx_repo.get_transactions_with_filters(
                        user_id, 
                        {"wallet_id": wallet_id_str}, 
                        limit=1000
                    )
                
                print(f"🔍 Raw transactions result type: {type(transactions)}")
                print(f"🔍 Raw transactions result: {transactions}")
                
                # Ensure we always have a list, never None
                if transactions is None:
                    print(f"⚠️ Transactions is None for {wallet.get('name')}, setting to empty list")
                    transactions = []
                elif not isinstance(transactions, list):
                    print(f"⚠️ Transactions is not a list for {wallet.get('name')}, converting to list")
                    transactions = list(transactions) if transactions else []
                
                print(f"🔍 After validation - transactions type: {type(transactions)}")
                print(f"🔍 After validation - transactions length: {len(transactions) if transactions else 0}")
                
                # Ensure we only get transactions for this wallet
                if transactions:
                    # Double-check: filter by wallet_id to be absolutely sure
                    original_count = len(transactions)
                    transactions = [tx for tx in transactions if str(tx.get("wallet_id", "")) == wallet_id_str]
                    filtered_count = len(transactions)
                    
                    if original_count != filtered_count:
                        print(f"⚠️ Filtered transactions for {wallet.get('name')}: {original_count} -> {filtered_count}")
            except Exception as e:
                print(f"❌ Error getting transactions for wallet {wallet.get('name')}: {e}")
                print(f"❌ Error type: {type(e)}")
                import traceback
                print(f"❌ Error traceback: {traceback.format_exc()}")
                transactions = []
            
            print(f"📊 {wallet.get('name')}: Found {len(transactions)} transactions")
            
            # Debug: Print first few transactions
            if transactions and len(transactions) > 0:
                print(f"🔍 Sample transactions for {wallet.get('name')}:")
                for i, tx in enumerate(transactions[:3]):
                    print(f"   {i+1}. Type: {tx.get('type')}, Amount: {tx.get('amount')}, Wallet: {tx.get('wallet_id')}")
            else:
                print(f"🔍 No transactions found for {wallet.get('name')}")
            
            # Calculate totals
            total_income = 0  # Initialize variable outside try-catch
            total_expense = 0  # Initialize variable outside try-catch
            total_transfer = 0  # Initialize variable outside try-catch
            
            try:
                if transactions and isinstance(transactions, list):
                    total_income = sum(float(tx.get("amount", 0)) for tx in transactions if tx.get("type") == "income")
            except (ValueError, TypeError) as e:
                print(f"Error calculating total_income for {wallet.get('name')}: {e}")
                total_income = 0
                
            try:
                if transactions and isinstance(transactions, list):
                    total_expense = sum(float(tx.get("amount", 0)) for tx in transactions if tx.get("type") == "expense")
            except (ValueError, TypeError) as e:
                print(f"Error calculating total_expense for {wallet.get('name')}: {e}")
                total_expense = 0
                
            try:
                if transactions and isinstance(transactions, list):
                    # Calculate transfer impact for this wallet (including all transfers)
                    total_transfer = 0
                    for tx in transactions:
                        if tx.get("is_transfer"):
                            if tx.get("type") == "expense" and tx.get("transfer_metadata", {}).get("transfer_type") == "outgoing":
                                # This is an outgoing transfer (expense)
                                if str(tx.get("wallet_id")) == wallet_id_str:
                                    total_transfer -= float(tx.get("amount", 0))
                            elif tx.get("type") == "income" and tx.get("transfer_metadata", {}).get("transfer_type") == "incoming":
                                # This is an incoming transfer (income)
                                if str(tx.get("wallet_id")) == wallet_id_str:
                                    total_transfer += float(tx.get("amount", 0))
            except (ValueError, TypeError) as e:
                print(f"Error calculating total_transfer for {wallet.get('name')}: {e}")
                total_transfer = 0
            
            # Get manual balance from manual balance table (tidak lagi dari transaksi)
            manual_balance = 0  # Initialize variable outside try-catch
            try:
                from mm.repositories.manual_balance import ManualBalanceRepository
                manual_balance_repo = ManualBalanceRepository()
                latest_manual_balance = manual_balance_repo.get_latest_balance(user_id, wallet_id_str)
                
                if latest_manual_balance:
                    manual_balance = float(latest_manual_balance.get("balance_amount", 0))
                    print(f"✅ [MANUAL_BALANCE] Found manual balance for {wallet.get('name')}: {manual_balance}")
                else:
                    print(f"⚠️ [MANUAL_BALANCE] No manual balance found for {wallet.get('name')}, using 0")
                    manual_balance = 0
            except Exception as e:
                print(f"❌ [MANUAL_BALANCE] Error getting manual balance for {wallet.get('name')}: {e}")
                manual_balance = 0
            
            # Calculate expected balance based on transactions
            # This is what the balance should be based on recorded transactions
            expected_balance_from_transactions = 0
            
            try:
                if transactions and isinstance(transactions, list):
                    # Get manual balance history untuk starting point
                    from mm.repositories.manual_balance import ManualBalanceRepository
                    manual_balance_repo = ManualBalanceRepository()
                    balance_history = manual_balance_repo.get_balance_history(user_id, wallet_id_str, limit=100)
                    
                    if balance_history and len(balance_history) > 0:
                        # Sort by balance_date dan ambil yang earliest
                        sorted_history = sorted(balance_history, key=lambda x: x.get("balance_date", 0))
                        earliest_balance = sorted_history[0]
                        starting_balance = float(earliest_balance.get("balance_amount", 0))
                        starting_timestamp = earliest_balance.get("balance_date", 0)
                        
                        print(f"🔍 [MANUAL_BALANCE] Starting balance for {wallet.get('name')}: {starting_balance} at {starting_timestamp}")
                        
                        # Calculate balance changes from transactions after the starting manual balance
                        balance_changes = 0
                        
                        for tx in transactions:
                            if not tx or not isinstance(tx, dict):
                                continue
                                
                            # Hanya hitung transaksi setelah manual balance pertama (bukan manual_balance transaction)
                            if tx.get("timestamp", 0) > starting_timestamp and tx.get("type") != "manual_balance":
                                if tx.get("type") == "income":
                                    balance_changes += float(tx.get("amount", 0))
                                elif tx.get("type") == "expense":
                                    balance_changes -= float(tx.get("amount", 0))
                                elif tx.get("is_transfer"):
                                    if tx.get("type") == "expense" and tx.get("transfer_metadata", {}).get("transfer_type") == "outgoing":
                                        balance_changes -= float(tx.get("amount", 0))
                                    elif tx.get("type") == "income" and tx.get("transfer_metadata", {}).get("transfer_type") == "incoming":
                                        balance_changes += float(tx.get("amount", 0))
                        
                        expected_balance_from_transactions = starting_balance + balance_changes
                        print(f"🔍 [MANUAL_BALANCE] Expected balance for {wallet.get('name')}: {expected_balance_from_transactions}")
                    else:
                        # Tidak ada manual balance history, hitung dari semua transaksi
                        print(f"⚠️ [MANUAL_BALANCE] No manual balance history for {wallet.get('name')}, calculating from all transactions")
                        balance_changes = 0
                        
                        for tx in transactions:
                            if not tx or not isinstance(tx, dict):
                                continue
                                
                            if tx.get("type") != "manual_balance":
                                if tx.get("type") == "income":
                                    balance_changes += float(tx.get("amount", 0))
                                elif tx.get("type") == "expense":
                                    balance_changes -= float(tx.get("amount", 0))
                                elif tx.get("type") == "transfer":
                                    if tx.get("type") == "expense" and tx.get("transfer_metadata", {}).get("transfer_type") == "outgoing":
                                        balance_changes -= float(tx.get("amount", 0))
                                    elif tx.get("type") == "income" and tx.get("transfer_metadata", {}).get("transfer_type") == "incoming":
                                        balance_changes += float(tx.get("amount", 0))
                        
                        expected_balance_from_transactions = balance_changes
                        print(f"🔍 [MANUAL_BALANCE] Expected balance from all transactions for {wallet.get('name')}: {expected_balance_from_transactions}")
            except Exception as e:
                print(f"❌ [MANUAL_BALANCE] Error calculating expected balance for {wallet.get('name')}: {e}")
                expected_balance_from_transactions = 0
            
            # Calculate current balance: manual balance yang bertambah/berkurang sesuai transaksi
            # Balance = Latest manual balance (user input) + perubahan dari transaksi setelah manual balance terakhir
            # Jika belum ada manual balance, hitung dari semua transaksi
            current_balance = manual_balance
            
            try:
                if transactions:
                    # Get manual balance history untuk menentukan starting point
                    from mm.repositories.manual_balance import ManualBalanceRepository
                    manual_balance_repo = ManualBalanceRepository()
                    balance_history = manual_balance_repo.get_balance_history(user_id, wallet_id_str, limit=100)
                    
                    if balance_history and len(balance_history) > 0:
                        # Sort by balance_date dan ambil yang latest
                        sorted_history = sorted(balance_history, key=lambda x: x.get("balance_date", 0))
                        latest_real_balance = sorted_history[-1]  # Yang terbaru
                        latest_balance_timestamp = latest_real_balance.get("balance_date", 0)
                        
                        print(f"🔍 [REAL_BALANCE] Latest real balance for {wallet.get('name')}: {latest_real_balance.get('balance_amount', 0)} at {latest_balance_timestamp}")
                        
                        # Calculate balance changes from transactions after the latest real balance
                        balance_changes_after_manual = 0
                        
                        if transactions and isinstance(transactions, list):
                            for tx in transactions:
                                if not tx or not isinstance(tx, dict):
                                    continue
                                    
                                # Hanya hitung transaksi setelah real balance terakhir (bukan manual_balance transaction)
                                if tx.get("timestamp", 0) > latest_balance_timestamp and tx.get("type") != "manual_balance":
                                    if tx.get("type") == "income":
                                        balance_changes_after_manual += float(tx.get("amount", 0))
                                    elif tx.get("type") == "expense":
                                        balance_changes_after_manual -= float(tx.get("amount", 0))
                                    elif tx.get("is_transfer"):
                                        if tx.get("type") == "expense" and tx.get("transfer_metadata", {}).get("transfer_type") == "outgoing":
                                            balance_changes_after_manual -= float(tx.get("amount", 0))
                                        elif tx.get("type") == "income" and tx.get("transfer_metadata", {}).get("transfer_type") == "incoming":
                                            balance_changes_after_manual += float(tx.get("amount", 0))
                        
                        # Current balance = manual balance + perubahan setelah real balance terakhir
                        current_balance = manual_balance + balance_changes_after_manual
                        print(f"🔍 [REAL_BALANCE] Current balance for {wallet.get('name')}: {current_balance}")
                    else:
                        # Tidak ada real balance history, hitung dari semua transaksi
                        print(f"⚠️ [REAL_BALANCE] No real balance history for {wallet.get('name')}, calculating from all transactions")
                        balance_changes_from_all = 0
                        
                        if transactions and isinstance(transactions, list):
                            for tx in transactions:
                                if not tx or not isinstance(tx, dict):
                                    continue
                                    
                                if tx.get("type") != "manual_balance":
                                    if tx.get("type") == "income":
                                        balance_changes_from_all += float(tx.get("amount", 0))
                                    elif tx.get("type") == "expense":
                                        balance_changes_from_all -= float(tx.get("amount", 0))
                                    elif tx.get("is_transfer"):
                                        if tx.get("type") == "expense" and tx.get("transfer_metadata", {}).get("transfer_type") == "outgoing":
                                            balance_changes_from_all -= float(tx.get("amount", 0))
                                        elif tx.get("type") == "income" and tx.get("transfer_metadata", {}).get("transfer_type") == "incoming":
                                            balance_changes_from_all += float(tx.get("amount", 0))
                        
                        # Current balance = 0 + perubahan dari semua transaksi
                        current_balance = 0 + balance_changes_from_all
                        print(f"🔍 [REAL_BALANCE] Current balance from all transactions for {wallet.get('name')}: {current_balance}")
            except Exception as e:
                print(f"❌ [REAL_BALANCE] Error calculating current balance for {wallet.get('name')}: {e}")
                current_balance = manual_balance
            
            # Calculate ghost transactions: difference between manual balance and expected balance
            ghost_transactions = []
            total_ghost_positive = 0
            total_ghost_negative = 0
            
            try:
                if manual_balance_txs and isinstance(manual_balance_txs, list) and len(manual_balance_txs) > 1:
                    # Ensure all items in manual_balance_txs are valid
                    valid_manual_balances = [tx for tx in manual_balance_txs if tx and isinstance(tx, dict)]
                    if valid_manual_balances and len(valid_manual_balances) > 1:
                        # NEW: Sort by transaction_order if available, otherwise by timestamp
                        if any(tx.get("transaction_order") is not None for tx in valid_manual_balances):
                            # Use transaction_order for precise ordering
                            sorted_manual_balances = sorted(valid_manual_balances, key=lambda x: x.get("transaction_order", 0) if x and isinstance(x, dict) else 0)
                        else:
                            # Fallback to timestamp sorting
                            sorted_manual_balances = sorted(valid_manual_balances, key=lambda x: x.get("timestamp", 0) if x and isinstance(x, dict) else 0)
                        
                        for i in range(1, len(sorted_manual_balances)):
                            prev_manual_balance = float(sorted_manual_balances[i-1].get("amount", 0)) if sorted_manual_balances[i-1] and isinstance(sorted_manual_balances[i-1], dict) else 0
                            curr_manual_balance = float(sorted_manual_balances[i].get("amount", 0)) if sorted_manual_balances[i] and isinstance(sorted_manual_balances[i], dict) else 0
                            prev_timestamp = sorted_manual_balances[i-1].get("timestamp", 0) if sorted_manual_balances[i-1] and isinstance(sorted_manual_balances[i-1], dict) else 0
                            curr_timestamp = sorted_manual_balances[i].get("timestamp", 0) if sorted_manual_balances[i] and isinstance(sorted_manual_balances[i], dict) else 0
                        
                        # Calculate what the balance should be at this point based on transactions
                        # between prev_timestamp and curr_timestamp (inclusive for same timestamp)
                        # INCLUDE all transactions to calculate expected balance
                        # NEW: Use transaction_order field if available, otherwise fallback to timestamp
                        balance_changes_between = 0
                        
                        # NEW: Track unique transactions to avoid duplicates
                        seen_transactions = set()
                        
                        # Ensure transactions is a valid list before iterating
                        if transactions and isinstance(transactions, list):
                            for tx in transactions:
                                # Ensure tx is a valid transaction object
                                if not tx or not isinstance(tx, dict):
                                    continue
                                    
                                # NEW LOGIC: Check if transaction should be between manual balances
                                # Option 1: Use transaction_order field if available
                                # Option 2: Fallback to timestamp logic
                                should_include = False
                                
                                if tx.get("transaction_order") is not None:
                                    # Use transaction_order field for precise ordering
                                    prev_order = sorted_manual_balances[i-1].get("transaction_order", 0)
                                    curr_order = sorted_manual_balances[i].get("transaction_order", 0)
                                    tx_order = tx.get("transaction_order", 0)
                                    
                                    # Include if transaction_order is between manual balance orders
                                    if (tx_order > prev_order and 
                                        tx_order < curr_order and 
                                        tx.get("type") != "manual_balance"):
                                        should_include = True
                                else:
                                    # Fallback to timestamp logic
                                    if (tx.get("timestamp", 0) >= prev_timestamp and 
                                        tx.get("timestamp", 0) <= curr_timestamp and 
                                        tx.get("type") != "manual_balance"):
                                        should_include = True
                                
                                if should_include:
                                    # NEW: Create unique identifier to avoid duplicates
                                    tx_key = f"{tx.get('type')}_{tx.get('amount')}_{tx.get('timestamp')}_{tx.get('description', '')}"
                                    
                                    # Only process if we haven't seen this transaction before
                                    if tx_key not in seen_transactions:
                                        seen_transactions.add(tx_key)
                                        
                                        if tx.get("type") == "income":
                                            balance_changes_between += float(tx.get("amount", 0))
                                        elif tx.get("type") == "expense":
                                            balance_changes_between -= float(tx.get("amount", 0))
                                        elif tx.get("is_transfer"):
                                            if tx.get("type") == "expense" and tx.get("transfer_metadata", {}).get("transfer_type") == "outgoing":
                                                balance_changes_between -= float(tx.get("amount", 0))
                                            elif tx.get("type") == "income" and tx.get("transfer_metadata", {}).get("transfer_type") == "incoming":
                                                balance_changes_between += float(tx.get("amount", 0))
                        
                        # Expected balance should be: prev_manual_balance + balance_changes_between
                        expected_balance_at_curr = prev_manual_balance + balance_changes_between
                        
                        # Ghost transaction = difference between actual manual balance and expected
                        ghost_amount = curr_manual_balance - expected_balance_at_curr
                        
                        # DEBUG: Print calculation details
                        print(f"🔍 Ghost Calculation for {wallet.get('name')}:")
                        print(f"   Manual Balance {i-1}: {prev_manual_balance:,.0f}")
                        print(f"   Manual Balance {i}: {curr_manual_balance:,.0f}")
                        print(f"   Balance Changes Between: {balance_changes_between:,.0f}")
                        print(f"   Expected Balance: {expected_balance_at_curr:,.0f}")
                        print(f"   Ghost Amount: {ghost_amount:,.0f}")
                        
                        if abs(ghost_amount) > 0.01:  # Significant difference
                            ghost_type = "positive" if ghost_amount > 0 else "negative"
                            ghost_amount_abs = abs(ghost_amount)
                            
                            # Calculate remaining ghost amount by looking at transactions AFTER this ghost was detected
                            # that are marked as confirmed ghost transactions
                            remaining_ghost_amount = ghost_amount_abs
                            
                            # NEW: Look for confirmed ghost transactions AFTER this point
                            # Use transaction_order if avaable, otherwise fallback to timestamp
                            confirmed_for_this_ghost = 0
                            
                            # Ensure transactions is a valid list before iterating
                            if transactions and isinstance(transactions, list):
                                for tx in transactions:
                                    # Ensure tx is a valid transaction object
                                    if not tx or not isinstance(tx, dict):
                                        continue
                                        
                                    # NEW LOGIC: Check if transaction is after current manual balance
                                    should_include = False
                                    
                                    if tx.get("transaction_order") is not None:
                                        # Use transaction_order for precise ordering
                                        curr_order = sorted_manual_balances[i].get("transaction_order", 0) if sorted_manual_balances[i] and isinstance(sorted_manual_balances[i], dict) else 0
                                        tx_order = tx.get("transaction_order", 0)
                                        
                                        # Include if transaction_order is after current manual balance order
                                        if (tx_order > curr_order and 
                                            tx.get("type") != "manual_balance" and
                                            tx.get("is_from_ghost_transaction")):
                                            should_include = True
                                    else:
                                        # Fallback to timestamp logic
                                        if (tx.get("timestamp", 0) > curr_timestamp and 
                                            tx.get("type") != "manual_balance" and
                                            tx.get("is_from_ghost_transaction")):
                                            should_include = True
                                    
                                    if should_include:
                                        
                                        if ghost_type == "positive":
                                            # For positive ghost (unexplained income), reduce by confirmed income
                                            if tx.get("type") == "income":
                                                confirmed_for_this_ghost += float(tx.get("amount", 0))
                                            elif tx.get("type") == "expense":
                                                confirmed_for_this_ghost -= float(tx.get("amount", 0))
                                        else:
                                            # For negative ghost (unexplained expense), reduce by confirmed expense
                                            if tx.get("type") == "income":
                                                confirmed_for_this_ghost += float(tx.get("amount", 0))
                                            elif tx.get("type") == "expense":
                                                confirmed_for_this_ghost -= float(tx.get("amount", 0))
                            
                            # Calculate remaining ghost amount
                            if ghost_type == "positive":
                                # For positive ghost, reduce by net confirmed income
                                remaining_ghost_amount = max(0, ghost_amount_abs - confirmed_for_this_ghost)
                            else:
                                # For negative ghost, reduce by net confirmed expense
                                remaining_ghost_amount = max(0, ghost_amount_abs + confirmed_for_this_ghost)
                            
                            # Only show ghost transaction if there's still unexplained amount
                            if remaining_ghost_amount > 0.01:
                                ghost_transactions.append({
                                    "type": ghost_type,
                                    "amount": remaining_ghost_amount,
                                    "description": f"Ghost transaction ({ghost_type}) - Remaining unexplained",
                                    "timestamp": curr_timestamp,
                                    "note": f"Original ghost: {ghost_amount_abs:.2f}, Confirmed after: {confirmed_for_this_ghost:.2f}, Remaining: {remaining_ghost_amount:.2f}",
                                    "category_name": "Ghost Transaction"
                                })
                                
                                if ghost_type == "positive":
                                    total_ghost_positive += remaining_ghost_amount
                                else:
                                    total_ghost_negative += remaining_ghost_amount
            except Exception as e:
                print(f"Error calculating ghost transactions for {wallet.get('name')}: {e}")
                ghost_transactions = []
                total_ghost_positive = 0
                total_ghost_negative = 0
            
            # Get last transaction timestamps for each type - ensure all are integers
            last_income = 0  # Initialize variable outside try-catch
            last_expense = 0  # Initialize variable outside try-catch
            last_transfer = 0  # Initialize variable outside try-catch
            last_transaction = 0  # Initialize variable outside try-catch
            
            try:
                if transactions and isinstance(transactions, list):
                    income_txs = [tx for tx in transactions if tx and isinstance(tx, dict) and tx.get("type") == "income" and tx.get("timestamp")]
                    if income_txs:
                        last_income = max(int(tx.get("timestamp", 0)) for tx in income_txs if tx and isinstance(tx, dict))
                    else:
                        last_income = 0
                else:
                    last_income = 0
            except (ValueError, TypeError) as e:
                print(f"Error calculating last_income for {wallet.get('name')}: {e}")
                last_income = 0
                
            try:
                if transactions and isinstance(transactions, list):
                    expense_txs = [tx for tx in transactions if tx and isinstance(tx, dict) and tx.get("type") == "expense" and tx.get("timestamp")]
                    if expense_txs:
                        last_expense = max(int(tx.get("timestamp", 0)) for tx in expense_txs if tx and isinstance(tx, dict))
                    else:
                        last_expense = 0
                else:
                    last_expense = 0
            except (ValueError, TypeError) as e:
                print(f"Error calculating last_expense for {wallet.get('name')}: {e}")
                last_expense = 0
                
            try:
                if transactions and isinstance(transactions, list):
                    transfer_txs = [tx for tx in transactions if tx and isinstance(tx, dict) and tx.get("type") == "transfer" and tx.get("timestamp")]
                    if transfer_txs:
                        last_transfer = max(int(tx.get("timestamp", 0)) for tx in transfer_txs if tx and isinstance(tx, dict))
                    else:
                        last_transfer = 0
                else:
                    last_transfer = 0
            except (ValueError, TypeError) as e:
                print(f"Error calculating last_transfer for {wallet.get('name')}: {e}")
                last_transfer = 0
                
            try:
                if transactions and isinstance(transactions, list):
                    valid_txs = [tx for tx in transactions if tx and isinstance(tx, dict) and tx.get("timestamp")]
                    if valid_txs:
                        last_transaction = max(int(tx.get("timestamp", 0)) for tx in valid_txs if tx and isinstance(tx, dict))
                    else:
                        last_transaction = 0
                else:
                    last_transaction = 0
            except (ValueError, TypeError) as e:
                print(f"Error calculating last_transaction for {wallet.get('name')}: {e}")
                last_transaction = 0
            
            # Count transactions by type (including all transactions)
            transfer_count = 0  # Initialize variable outside try-catch
            try:
                if transactions and isinstance(transactions, list):
                    transfer_count = len([tx for tx in transactions if tx and isinstance(tx, dict) and tx.get("type") == "transfer"])
            except Exception as e:
                print(f"Error counting transfer transactions for {wallet.get('name')}: {e}")
                transfer_count = 0
            
            # Prepare individual transactions with category names and sort by timestamp (newest first)
            individual_transactions = []  # Initialize variable outside try-catch
            all_transactions = []  # Initialize variable outside try-catch
            try:
                if transactions and isinstance(transactions, list):
                    # NEW: Track unique transactions to avoid duplicates in display
                    seen_tx_keys = set()
                    
                    for tx in transactions:
                            # Ensure tx is a valid transaction object
                            if not tx or not isinstance(tx, dict):
                                continue
                                
                            # Get category name if available
                            category_name = None
                            if tx.get("category_id"):
                                try:
                                    # Try to get category using new method that includes defaults
                                    category = category_repo.get_category_by_id(tx["category_id"], user_id)
                                    category_name = category["name"] if category else None
                                except Exception:
                                    category_name = None
                            
                            # Special handling for manual balance transactions
                            if tx.get("type") == "manual_balance":
                                category_name = "Manual Balance Update"
                                # Add base_time for sorting multiple balance updates
                                if tx.get("base_time"):
                                    tx["timestamp"] = tx["base_time"]
                            
                            # Special handling for transfer transactions
                            if tx.get("is_transfer"):
                                if tx.get("type") == "expense" and tx.get("transfer_metadata", {}).get("transfer_type") == "outgoing":
                                    # This is an outgoing transfer (expense)
                                    to_wallet_name = tx.get("transfer_metadata", {}).get("to_wallet_name", "Unknown")
                                    net_amount = tx.get("transfer_metadata", {}).get("net_amount", 0)
                                    admin_fee = tx.get("transfer_metadata", {}).get("admin_fee", 0)
                                    category_name = f"Transfer to {to_wallet_name}"
                                    display_amount = -float(tx.get("amount", 0))  # Negative for expense
                                    description = f"Transfer to {to_wallet_name} (Net: {net_amount}, Fee: {admin_fee})"
                                elif tx.get("type") == "income" and tx.get("transfer_metadata", {}).get("transfer_type") == "incoming":
                                    # This is an incoming transfer (income)
                                    from_wallet_name = tx.get("transfer_metadata", {}).get("from_wallet_name", "Unknown")
                                    category_name = f"Transfer from {from_wallet_name}"
                                    display_amount = float(tx.get("amount", 0))  # Positive for income
                                    description = f"Transfer from {from_wallet_name}"
                                else:
                                    display_amount = tx.get("amount", 0)
                                    description = tx.get("description", "")
                            else:
                                display_amount = tx.get("amount", 0)
                                description = tx.get("description", "")
                            
                            # NEW: Create unique identifier to avoid duplicates
                            tx_key = f"{tx.get('type')}_{tx.get('amount')}_{tx.get('timestamp')}_{tx.get('description', '')}"
                            
                            # Only add if we haven't seen this transaction before
                            if tx_key not in seen_tx_keys:
                                seen_tx_keys.add(tx_key)
                                
                                individual_transactions.append({
                                "type": tx.get("type"),
                                "amount": display_amount,
                                "description": description,
                                "timestamp": tx.get("timestamp", 0),
                                "note": tx.get("note", ""),
                                "category_name": category_name,
                                "is_manual_balance": tx.get("is_manual_balance", False),
                                "base_time": tx.get("base_time", tx.get("timestamp", 0)),
                                "is_transfer": tx.get("is_transfer", False),
                                "transfer_metadata": tx.get("transfer_metadata", {}),
                                "transaction_order": tx.get("transaction_order", None)  # NEW: Add transaction_order field
                                })
                            # End of if not duplicate
            except Exception as e:
                print(f"Error processing individual transactions for {wallet.get('name')}: {e}")
                individual_transactions = []
            
            # NEW: Sort transactions by transaction_order if available, otherwise by timestamp
            try:
                if individual_transactions and isinstance(individual_transactions, list):
                    # Check if any transaction has transaction_order field
                    if any(tx and isinstance(tx, dict) and tx.get("transaction_order") is not None for tx in individual_transactions):
                        # Sort by transaction_order (ascending - oldest first)
                        individual_transactions.sort(key=lambda x: x.get("transaction_order", 0) if x and isinstance(x, dict) else 0)
                    else:
                        # Fallback to timestamp sorting (newest first)
                        individual_transactions.sort(key=lambda x: x.get("timestamp", 0) if x and isinstance(x, dict) else 0, reverse=True)
            except Exception as e:
                print(f"Error sorting individual transactions for {wallet.get('name')}: {e}")
            
            # Combine regular transactions with ghost transactions
            try:
                all_transactions = individual_transactions + ghost_transactions
                
                # NEW: Sort all transactions by transaction_order if available, otherwise by timestamp
                # This will show transactions in the correct order when scrolling
                if all_transactions and isinstance(all_transactions, list):
                    # Check if any transaction has transaction_order field
                    if any(tx and isinstance(tx, dict) and tx.get("transaction_order") is not None for tx in all_transactions):
                        # Sort by transaction_order (ascending - oldest first)
                        all_transactions.sort(key=lambda x: x.get("transaction_order", 0) if x and isinstance(x, dict) else 0)
                    else:
                        # Fallback to timestamp sorting (oldest first), with manual balance transactions prioritized by base_time
                        all_transactions.sort(key=lambda x: (x.get("base_time", x.get("timestamp", 0)) if x and isinstance(x, dict) else 0, x.get("is_manual_balance", False) if x and isinstance(x, dict) else False), reverse=False)
            except Exception as e:
                print(f"Error combining and sorting all transactions for {wallet.get('name')}: {e}")
                all_transactions = individual_transactions
            
            # Get manual balance history untuk display (sorted by timestamp descending)
            from mm.repositories.manual_balance import ManualBalanceRepository
            manual_balance_repo = ManualBalanceRepository()
            manual_balance_history = manual_balance_repo.get_balance_history(user_id, wallet_id_str, limit=100)
            
            # Sort by timestamp descending (newest first) untuk dropdown
            if manual_balance_history:
                manual_balance_history.sort(key=lambda x: x.get("balance_date", 0), reverse=True)
            
            balance_data.append({
                "wallet": wallet,
                "total_income": total_income,
                "total_expense": total_expense,
                "total_transfer": total_transfer,
                "manual_balance": manual_balance,
                "current_balance": current_balance,
                "expected_balance_from_transactions": expected_balance_from_transactions,
                "transaction_count": len(transactions),
                "transfer_count": transfer_count,
                "last_transaction": last_transaction,
                "last_income": last_income,
                "last_expense": last_expense,
                "last_transfer": last_transfer,
                "transactions": all_transactions,
                "ghost_transactions": ghost_transactions,
                "total_ghost_positive": total_ghost_positive,
                "total_ghost_negative": total_ghost_negative,
                "manual_balance_transactions": manual_balance_history,  # Sekarang menggunakan manual balance history
                "manual_balance_history": manual_balance_history  # Tambahan field untuk manual balance
            })
        
        # Ensure lists are passed
        wallets = wallets or []
        balance_data = balance_data or []
        
        return render_template("balance.html",
                             wallets=wallets,
                             balance_data=balance_data)
    except Exception as e:
        print(f"Error in balance: {e}")
        return render_template("balance.html",
                             wallets=[],
                             balance_data=[])

@app.route("/settings")
def settings():
    try:
        user_id = session.get("user_id", "demo_user")
        
        # Get repositories
        scope_repo = ScopeRepository()
        wallet_repo = WalletRepository()
        category_repo = CategoryRepository()
        
        # Get data
        scopes = scope_repo.list_by_user(user_id)
        wallets = wallet_repo.list_by_user(user_id)
        categories = category_repo.list_by_user_with_defaults(user_id)  # Include default categories
        
        # Ensure lists are passed
        scopes = scopes or []
        wallets = wallets or []
        categories = categories or []
        
        return render_template("settings.html",
                             scopes=scopes,
                             wallets=wallets,
                             categories=categories)
    except Exception as e:
        print(f"Error in settings: {e}")
        return render_template("settings.html",
                             scopes=[],
                             wallets=[],
                             categories=[])

# API Routes
@app.route("/api/transactions/", methods=["GET"])
def list_transactions():
    """Get semua transaksi untuk user"""
    try:
        user_id = session.get("user_id", "demo_user")
        repo = TransactionRepository()
        data = repo.get_user_transactions_simple(user_id, limit=200)
        return jsonify(data)
    except Exception as e:
        print(f"Error in list_transactions: {e}")
        return jsonify([])

@app.route("/api/transactions/", methods=["POST"])
def create_transaction():
    """Create transaksi baru"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        # Tambah user_id ke data
        body["user_id"] = user_id
        
        # Set default values
        if "timestamp" not in body:
            import time
            body["timestamp"] = int(time.time())
        
        repo = TransactionRepository()
        _id = repo.insert_one(body)
        return jsonify({"_id": _id}), 201
    except Exception as e:
        print(f"Error in create_transaction: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/transactions/<transaction_id>", methods=["GET"])
def get_transaction(transaction_id):
    """Get single transaksi"""
    try:
        user_id = session.get("user_id", "demo_user")
        repo = TransactionRepository()
        
        transaction = repo.get_transaction_by_id(transaction_id, user_id)
        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404
        
        return jsonify(transaction)
    except Exception as e:
        print(f"Error in get_transaction: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/transactions/<transaction_id>", methods=["PUT"])
def update_transaction(transaction_id):
    """Update transaksi"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        repo = TransactionRepository()
        success = repo.update_transaction(transaction_id, user_id, body)
        
        if not success:
            return jsonify({"error": "Transaction not found or update failed"}), 404
        
        return jsonify({"message": "Transaction updated successfully"})
    except Exception as e:
        print(f"Error in update_transaction: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/transactions/<transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    """Delete transaksi"""
    try:
        user_id = session.get("user_id", "demo_user")
        repo = TransactionRepository()
        
        success = repo.delete_transaction(transaction_id, user_id)
        
        if not success:
            return jsonify({"error": "Transaction not found or delete failed"}), 404
        
        return jsonify({"message": "Transaction deleted successfully"})
    except Exception as e:
        print(f"Error in delete_transaction: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/scopes/", methods=["GET"])
def list_scopes():
    """Get semua scope untuk user"""
    try:
        user_id = session.get("user_id", "demo_user")
        repo = ScopeRepository()
        data = repo.list_by_user(user_id)
        return jsonify(data)
    except Exception as e:
        print(f"Error in list_scopes: {e}")
        return jsonify([])

@app.route("/api/scopes/", methods=["POST"])
def create_scope():
    """Create scope baru"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        # Tambah user_id ke data
        body["user_id"] = user_id
        
        repo = ScopeRepository()
        _id = repo.insert_one(body)
        return jsonify({"_id": _id}), 201
    except Exception as e:
        print(f"Error in create_scope: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/scopes/<scope_id>", methods=["PUT"])
def update_scope(scope_id):
    """Update scope"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        repo = ScopeRepository()
        success = repo.update_scope(scope_id, user_id, body)
        
        if not success:
            return jsonify({"error": "Scope not found or update failed"}), 404
        
        return jsonify({"message": "Scope updated successfully"})
    except Exception as e:
        print(f"Error in update_scope: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/scopes/<scope_id>", methods=["DELETE"])
def delete_scope(scope_id):
    """Delete scope"""
    try:
        user_id = session.get("user_id", "demo_user")
        repo = ScopeRepository()
        
        success = repo.delete_scope(scope_id, user_id)
        
        if not success:
            return jsonify({"error": "Scope not found or delete failed"}), 404
        
        return jsonify({"message": "Scope deleted successfully"})
    except Exception as e:
        print(f"Error in delete_scope: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/wallets/", methods=["GET"])
def list_wallets():
    """Get semua saving space untuk user"""
    try:
        user_id = session.get("user_id", "demo_user")
        repo = WalletRepository()
        data = repo.list_by_user(user_id)
        return jsonify(data)
    except Exception as e:
        print(f"Error in list_wallets: {e}")
        return jsonify([])

@app.route("/api/wallets/", methods=["POST"])
def create_wallet():
    """Create saving space baru"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        # Tambah user_id ke data
        body["user_id"] = user_id
        body["manual_balance"] = 0
        
        # Set default type jika tidak ada
        if "type" not in body:
            body["type"] = "bank"
        
        repo = WalletRepository()
        _id = repo.insert_one(body)
        return jsonify({"_id": _id}), 201
    except Exception as e:
        print(f"Error in create_wallet: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/wallets/<wallet_id>", methods=["PUT"])
def update_wallet(wallet_id):
    """Update saving space"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        repo = WalletRepository()
        success = repo.update_wallet(wallet_id, user_id, body)
        
        if not success:
            return jsonify({"error": "Saving space not found or update failed"}), 404
        
        return jsonify({"message": "Saving space updated successfully"})
    except Exception as e:
        print(f"Error in update_wallet: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/wallets/<wallet_id>/balance', methods=['PUT'])
def update_wallet_balance(wallet_id):
    try:
        data = request.get_json()
        amount = data.get('amount', 0)
        note = data.get('note', '')
        
        if not amount or amount < 0:
            return jsonify({'error': 'Invalid amount'}), 400
        
        # Get wallet info
        wallet_repo = WalletRepository()
        wallet = wallet_repo.find_one({"_id": ObjectId(wallet_id), "user_id": session.get("user_id", "demo_user")})
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404
        
        # Create new manual balance
        balance_repo = ManualBalanceRepository()
        balance_data = {
            'balance_amount': amount,
            'note': note,
            'currency': 'IDR'
        }
        
        balance_id = balance_repo.create_balance(
            session.get("user_id", "demo_user"), 
            wallet_id, 
            balance_data
        )
        
        if balance_id:
            return jsonify({
                'success': True,
                'balance_id': balance_id,
                'message': 'Balance updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update balance'}), 500
            
    except Exception as e:
        print(f"❌ [API] Error updating wallet balance: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/manual-balance/<wallet_id>/history')
def get_manual_balance_history(wallet_id):
    try:
        balance_repo = ManualBalanceRepository()
        history = balance_repo.get_balance_history(session.get("user_id", "demo_user"), wallet_id, limit=100)
        
        # Format dates for frontend
        for balance in history:
            if 'balance_date' in balance:
                balance['formatted_date'] = datetime.fromtimestamp(balance['balance_date']).strftime('%d %b %Y')
        
        return jsonify(history)
        
    except Exception as e:
        print(f"❌ [API] Error getting manual balance history: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/manual-balance/<balance_id>/transactions')
def get_transactions_by_manual_balance(balance_id):
    try:
        tx_repo = TransactionRepository()
        transactions = tx_repo.get_transactions_by_manual_balance(
            session.get("user_id", "demo_user"), 
            balance_id, 
            limit=1000
        )
        
        return jsonify(transactions)
        
    except Exception as e:
        print(f"❌ [API] Error getting transactions by manual balance: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/manual-balance/<wallet_id>/sequence-summary')
def get_manual_balance_sequence_summary(wallet_id):
    try:
        balance_repo = ManualBalanceRepository()
        summary = balance_repo.get_balance_sequence_summary(session.get("user_id", "demo_user"), wallet_id)
        return jsonify(summary)
        
    except Exception as e:
        print(f"❌ [API] Error getting manual balance sequence summary: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/manual-balance/<wallet_id>/sequence/<int:sequence_number>')
def get_manual_balance_by_sequence(wallet_id, sequence_number):
    try:
        balance_repo = ManualBalanceRepository()
        balance = balance_repo.get_balance_by_sequence(session.get("user_id", "demo_user"), wallet_id, sequence_number)
        
        if balance:
            return jsonify(balance)
        else:
            return jsonify({'error': 'Balance not found'}), 404
            
    except Exception as e:
        print(f"❌ [API] Error getting manual balance by sequence: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route("/api/transfer", methods=["POST"])
def transfer_funds():
    """Transfer funds between saving spaces"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        # Validate required fields
        required_fields = ["from_wallet_id", "to_wallet_id", "amount", "admin_fee"]
        for field in required_fields:
            if field not in body:
                return jsonify({"error": f"{field} is required"}), 400
        
        try:
            amount = float(body["amount"])
            admin_fee = float(body["admin_fee"])
        except (ValueError, TypeError):
            return jsonify({"error": "amount and admin_fee must be valid numbers"}), 400
        
        if amount <= 0:
            return jsonify({"error": "amount must be greater than 0"}), 400
        
        if admin_fee < 0:
            return jsonify({"error": "admin_fee cannot be negative"}), 400
        
        # Get repositories
        wallet_repo = WalletRepository()
        tx_repo = TransactionRepository()
        
        # Convert string IDs to ObjectId for MongoDB query
        from bson import ObjectId
        try:
            from_wallet_id = ObjectId(body["from_wallet_id"])
            to_wallet_id = ObjectId(body["to_wallet_id"])
        except Exception as e:
            return jsonify({"error": "Invalid wallet ID format"}), 400
        
        # Validate wallets exist and belong to user
        from_wallet = wallet_repo.find_one({"_id": from_wallet_id, "user_id": user_id})
        to_wallet = wallet_repo.find_one({"_id": to_wallet_id, "user_id": user_id})
        
        if not from_wallet:
            return jsonify({"error": "Source saving space not found"}), 404
        
        if not to_wallet:
            return jsonify({"error": "Destination saving space not found"}), 404
        
        if from_wallet["_id"] == to_wallet["_id"]:
            return jsonify({"error": "Cannot transfer to the same saving space"}), 400
        
        # Check if source wallet has sufficient balance (use actual_balance from wallet)
        current_balance = from_wallet.get("actual_balance", 0)
        
        total_debit = amount + admin_fee
        
        # Debug logging - after all variables are defined
        print(f"Transfer Debug - User ID: {user_id}")
        print(f"From Wallet ID: {from_wallet_id}, Found: {from_wallet is not None}")
        print(f"To Wallet ID: {to_wallet_id}, Found: {to_wallet is not None}")
        print(f"Actual Balance: {current_balance}")
        print(f"Transfer Amount: {amount}")
        print(f"Admin Fee: {admin_fee}")
        print(f"Total Debit: {total_debit}")
        
        if current_balance < total_debit:
            return jsonify({"error": f"Insufficient balance. Available: {current_balance}, Required: {total_debit}"}), 400
        
        # Create three separate transactions for clarity
        import time
        current_timestamp = int(time.time())
        
        # 1. Expense transaction for sender (transfer amount + admin fee)
        sender_expense_data = {
            "user_id": user_id,
            "type": "expense",
            "amount": total_debit,  # amount + admin_fee
            "wallet_id": str(from_wallet["_id"]),
            "description": f"Transfer to {to_wallet['name']}",
            "timestamp": current_timestamp,
            "currency": "IDR",
            "category_id": "transfer",  # Use default transfer category
            "scope_id": None,
            "note": f"Transfer amount: {amount}, Admin fee: {admin_fee}",
            "is_transfer": True,
            "transfer_metadata": {
                "transfer_type": "outgoing",
                "to_wallet_id": str(to_wallet["_id"]),
                "to_wallet_name": to_wallet["name"],
                "net_amount": amount,
                "admin_fee": admin_fee
            }
        }
        
        # 2. Income transaction for receiver
        receiver_income_data = {
            "user_id": user_id,
            "type": "income",
            "amount": amount,
            "wallet_id": str(to_wallet["_id"]),
            "description": f"Transfer from {from_wallet['name']}",
            "timestamp": current_timestamp,
            "currency": "IDR",
            "category_id": "transfer",  # Use default transfer category
            "scope_id": None,
            "note": f"Incoming transfer from {from_wallet['name']}",
            "is_transfer": True,
            "transfer_metadata": {
                "transfer_type": "incoming",
                "from_wallet_id": str(from_wallet["_id"]),
                "from_wallet_name": from_wallet["name"]
            }
        }
        
        # Insert both transactions
        sender_expense_id = tx_repo.insert_one(sender_expense_data)
        receiver_income_id = tx_repo.insert_one(receiver_income_data)
        
        # Update balances
        new_from_balance = current_balance - total_debit
        new_to_balance = to_wallet.get("actual_balance", 0) + amount
        
        # Update source wallet actual_balance
        try:
            success_from = wallet_repo.update_wallet(str(from_wallet_id), user_id, {"actual_balance": new_from_balance})
            if not success_from:
                print(f"Warning: Failed to update source wallet actual_balance for {from_wallet['name']}")
        except Exception as e:
            print(f"Error updating source wallet actual_balance: {e}")
        
        # Update destination wallet actual_balance
        try:
            success_to = wallet_repo.update_wallet(str(to_wallet_id), user_id, {"actual_balance": new_to_balance})
            if not success_to:
                print(f"Warning: Failed to update destination wallet actual_balance for {to_wallet['name']}")
        except Exception as e:
            print(f"Error updating destination wallet actual_balance: {e}")
        
        return jsonify({
            "message": "Transfer completed successfully",
            "sender_expense_id": str(sender_expense_id),
            "receiver_income_id": str(receiver_income_id),
            "amount": amount,
            "admin_fee": admin_fee,
            "total_debit": total_debit,
            "from_balance": new_from_balance,
            "to_balance": new_to_balance,
            "from_wallet": from_wallet["name"],
            "to_wallet": to_wallet["name"]
        })
        
    except Exception as e:
        print(f"Error in transfer_funds: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/wallets/<wallet_id>", methods=["DELETE"])
def delete_wallet(wallet_id):
    """Delete saving space"""
    try:
        user_id = session.get("user_id", "demo_user")
        repo = WalletRepository()
        
        success = repo.delete_wallet(wallet_id, user_id)
        
        if not success:
            return jsonify({"error": "Saving space not found or delete failed"}), 404
        
        return jsonify({"message": "Saving space deleted successfully"})
    except Exception as e:
        print(f"Error in delete_wallet: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/categories/", methods=["GET"])
def list_categories():
    """Get semua kategori untuk user"""
    try:
        user_id = session.get("user_id", "demo_user")
        repo = CategoryRepository()
        data = repo.list_by_user(user_id)
        return jsonify(data)
    except Exception as e:
        print(f"Error in list_categories: {e}")
        return jsonify([])

@app.route("/api/categories/", methods=["POST"])
def create_category():
    """Create kategori baru"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        # Tambah user_id ke data
        body["user_id"] = user_id
        
        repo = CategoryRepository()
        _id = repo.insert_one(body)
        return jsonify({"_id": _id}), 201
    except Exception as e:
        print(f"Error in create_category: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/categories/<category_id>", methods=["PUT"])
def update_category(category_id):
    """Update kategori"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        repo = CategoryRepository()
        success = repo.update_category(category_id, user_id, body)
        
        if not success:
            return jsonify({"error": "Category not found or update failed"}), 404
        
        return jsonify({"message": "Category updated successfully"})
    except Exception as e:
        print(f"Error in update_category: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/categories/<category_id>", methods=["DELETE"])
def delete_category(category_id):
    """Delete kategori"""
    try:
        user_id = session.get("user_id", "demo_user")
        repo = CategoryRepository()
        
        success = repo.delete_category(category_id, user_id)
        
        if not success:
            return jsonify({"error": "Category not found or delete failed"}), 404
        
        return jsonify({"message": "Category deleted successfully"})
    except Exception as e:
        print(f"Error in delete_category: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/auth/me", methods=["GET"])
def get_current_user():
    """Get current user info"""
    user_id = session.get("user_id", "demo_user")
    return jsonify({"user_id": user_id, "username": "demo_user"})

@app.route("/api/auth/check-username", methods=["POST"])
def api_check_username():
    """Check username availability endpoint"""
    try:
        data = request.get_json()
        username = data.get("username")
        
        if not username:
            return jsonify({"available": False, "message": "Username is required"}), 400
        
        # Check if username already exists
        user_repo = UserRepository()
        existing_user = user_repo.find_by_username(username)
        available = existing_user is None
        
        return jsonify({"available": available, "message": "Username is available" if available else "Username is already taken"})
        
    except Exception as e:
        print(f"Error in api_check_username: {e}")
        return jsonify({"available": False, "message": "Error checking username"}), 500

@app.route("/api/auth/register", methods=["POST"])
def api_register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        # Basic validation
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters long"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long"}), 400
        
        # Check if username already exists
        user_repo = UserRepository()
        existing_user = user_repo.find_by_username(username)
        if existing_user:
            return jsonify({"error": "Username already exists"}), 400
        
        # Create new user
        new_user = {
            "username": username,
            "password": password,  # In production, hash the password
            "created_at": datetime.now().timestamp(),
            "updated_at": datetime.now().timestamp()
        }
        
        # Save user to database
        user_id = user_repo.insert_one(new_user)
        
        if not user_id:
            return jsonify({"error": "Failed to create user"}), 500
        
        # Set user session
        session["user_id"] = str(user_id)
        session["username"] = username
        
        return jsonify({"success": True, "message": "Registration successful", "user_id": str(user_id)}), 200
        
    except Exception as e:
        print(f"Error in api_register: {e}")
        return jsonify({"error": "Registration failed"}), 500

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        # Basic validation
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        # Verify user credentials from database
        user_repo = UserRepository()
        user = user_repo.find_by_username(username)
        
        if not user:
            return jsonify({"error": "Invalid username or password"}), 401
        
        # Check password (in production, verify hashed password)
        if user.get("password") != password:
            return jsonify({"error": "Invalid username or password"}), 401
        
        # Set user session
        session["user_id"] = str(user["_id"])
        session["username"] = username
        
        return jsonify({"success": True, "message": "Login successful", "user_id": str(user["_id"])}), 200
        
    except Exception as e:
        print(f"Error in api_login: {e}")
        return jsonify({"error": "Login failed"}), 500

@app.route("/logout")
def logout():
    """User logout endpoint"""
    # Clear session
    session.clear()
    return redirect("/")

@app.route("/balance-history/<manual_balance_id>")
def balance_history(manual_balance_id):
    """Halaman balance history dengan pembukuan debit/kredit"""
    try:
        user_id = session.get("user_id", "demo_user")
        
        # Get repositories
        tx_repo = TransactionRepository()
        manual_balance_repo = ManualBalanceRepository()
        wallet_repo = WalletRepository()
        category_repo = CategoryRepository()
        
        # Get manual balance info
        manual_balance = manual_balance_repo.find_by_id(manual_balance_id)
        if not manual_balance:
            return "Manual balance not found", 404
        
        # Validate user ownership
        if manual_balance.get("user_id") != user_id:
            return "Access denied", 403
        
        # Get wallet info
        wallet = wallet_repo.get_wallet_by_id(manual_balance.get("wallet_id"), user_id)
        if not wallet:
            return "Wallet not found", 404
        
        # Ensure wallet _id is string
        if "_id" in wallet:
            wallet["_id"] = str(wallet["_id"])
        
        # Get transactions berdasarkan fk_manual_balance_id
        transactions = tx_repo.get_transactions_by_manual_balance(user_id, manual_balance_id, limit=1000)
        
        # Get categories untuk display (including defaults)
        categories = category_repo.list_by_user_with_defaults(user_id)
        category_map = {cat["_id"]: cat["name"] for cat in categories}
        
        # Calculate totals
        total_debit = 0
        total_kredit = 0
        
        for tx in transactions:
            try:
                if tx.get("type") == "expense":
                    total_debit += float(tx.get("amount", 0))
                elif tx.get("type") == "income":
                    total_kredit += float(tx.get("amount", 0))
            except (ValueError, TypeError):
                print(f"⚠️ [BALANCE_HISTORY] Invalid amount in transaction: {tx.get('_id')}")
                continue
        
        # Format transactions dengan category name dan balance info
        formatted_transactions = []
        for tx in transactions:
            # Handle both string IDs (default categories) and ObjectId (user categories)
            category_id = tx.get("category_id")
            if category_id:
                # Convert ObjectId to string if needed
                if hasattr(category_id, '__str__'):
                    category_id = str(category_id)
                tx["category_name"] = category_map.get(category_id, "Unknown")
            else:
                tx["category_name"] = "Unknown"
            # Safe timestamp formatting
            try:
                timestamp = tx.get("timestamp", 0)
                if timestamp:
                    tx["formatted_time"] = datetime.fromtimestamp(timestamp).strftime("%d %b %Y %H:%M")
                else:
                    tx["formatted_time"] = "No date"
            except (ValueError, TypeError):
                tx["formatted_time"] = "Invalid date"
            
            # Ensure _id is string
            if "_id" in tx:
                tx["_id"] = str(tx["_id"])
            formatted_transactions.append(tx)
        
        # Ensure manual_balance _id is string
        if "_id" in manual_balance:
            manual_balance["_id"] = str(manual_balance["_id"])
        
        return render_template("balance_history.html", 
                             manual_balance=manual_balance,
                             wallet=wallet,
                             transactions=formatted_transactions,
                             total_debit=total_debit,
                             total_kredit=total_kredit)
                             
    except Exception as e:
        print(f"Error in balance_history: {e}")
        return "Error loading balance history", 500

if __name__ == "__main__":
    print("🚀 Starting Money Management AI Application...")
    print("📍 Application will be available at: http://localhost:5002")
    print("💡 Press Ctrl+C to stop the application")
    try:
        app.run(debug=True, host="0.0.0.0", port=5002)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

