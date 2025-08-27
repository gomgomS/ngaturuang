import os
from flask import Flask, render_template, session, request, jsonify
from mm.repositories.transactions import TransactionRepository
from mm.repositories.scopes import ScopeRepository
from mm.repositories.wallets import WalletRepository
from mm.repositories.categories import CategoryRepository
from mm.repositories.users import UserRepository
from bson import ObjectId
from config import ensure_indexes
from model import index_specs

app = Flask(__name__)
app.secret_key = "your-secret-key-here"

# Ensure database indexes (with error handling)
try:
    ensure_indexes(index_specs)
    print("✅ Database indexes created successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not create database indexes: {e}")
    print("Application will continue without indexes...")

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
def auth():
    return render_template("auth.html")

@app.route("/dashboard")
def dashboard():
    try:
        user_id = session.get("user_id", "demo_user")
        
        # Get repositories
        tx_repo = TransactionRepository()
        scope_repo = ScopeRepository()
        wallet_repo = WalletRepository()
        
        # Get data
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
                             total_transactions=total_transactions)
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
        categories = category_repo.list_by_user(user_id)
        
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
        
        # Get all saving spaces (same as settings)
        wallets = wallet_repo.list_by_user(user_id)
        
        # Get balance data with transactions for each saving space
        balance_data = []
        for wallet in wallets:
            wallet_id = wallet.get("_id")
            
            # Get transactions for this wallet ONLY
            wallet_id_str = str(wallet_id)
            
            print(f"🔍 Processing wallet: {wallet.get('name')} (ID: {wallet_id_str})")
            
            # Get transactions that belong to this specific wallet
            try:
                print(f"🔍 Querying transactions for wallet {wallet_id_str}")
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
            
            # Get manual balance from latest manual_balance transaction
            manual_balance = 0  # Initialize variable outside try-catch
            manual_balance_txs = []  # Initialize variable outside try-catch
            try:
                if transactions and isinstance(transactions, list):
                    manual_balance_txs = [tx for tx in transactions if tx.get("type") == "manual_balance"]
                    if manual_balance_txs:
                        # Sort by timestamp and get the latest
                        latest_manual_balance = max(manual_balance_txs, key=lambda x: x.get("timestamp", 0))
                        manual_balance = float(latest_manual_balance.get("amount", 0))
            except Exception as e:
                print(f"Error processing manual balance for {wallet.get('name')}: {e}")
                manual_balance_txs = []
                manual_balance = 0
            
            # Calculate expected balance based on transactions (excluding manual_balance)
            # This is what the balance should be based on recorded transactions
            expected_balance_from_transactions = 0
            
            try:
                if transactions and isinstance(transactions, list):
                    # Get the earliest manual balance as starting point
                    if manual_balance_txs:
                        earliest_manual_balance = min(manual_balance_txs, key=lambda x: x.get("timestamp", 0))
                        starting_balance = float(earliest_manual_balance.get("amount", 0))
                        starting_timestamp = earliest_manual_balance.get("timestamp", 0)
                        
                        # Calculate balance changes from transactions after the starting manual balance
                        # INCLUDE all transactions to calculate expected balance correctly
                        balance_changes = 0
                        for tx in transactions:
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
            except Exception as e:
                print(f"Error calculating expected balance from transactions for {wallet.get('name')}: {e}")
                expected_balance_from_transactions = 0
            
            # Calculate current balance: manual balance yang bertambah/berkurang sesuai transaksi
            # Balance = Latest manual balance (user input) + perubahan dari transaksi setelah manual balance terakhir
            # Jika belum ada manual balance, hitung dari semua transaksi
            current_balance = manual_balance
            
            try:
                if transactions:
                    if manual_balance_txs:
                        # Ada manual balance: hitung perubahan setelah manual balance terakhir
                        latest_manual_timestamp = max(manual_balance_txs, key=lambda x: x.get("timestamp", 0)).get("timestamp", 0)
                        
                        # Calculate balance changes from transactions after the latest manual balance
                        # INCLUDE all transactions to calculate current balance correctly
                        balance_changes_after_manual = 0
                        for tx in transactions:
                            if (tx.get("timestamp", 0) > latest_manual_timestamp and 
                                tx.get("type") != "manual_balance"):
                                
                                if tx.get("type") == "income":
                                    balance_changes_after_manual += float(tx.get("amount", 0))
                                elif tx.get("type") == "expense":
                                    balance_changes_after_manual -= float(tx.get("amount", 0))
                                elif tx.get("is_transfer"):
                                    if tx.get("type") == "expense" and tx.get("transfer_metadata", {}).get("transfer_type") == "outgoing":
                                        balance_changes_after_manual -= float(tx.get("amount", 0))
                                    elif tx.get("type") == "income" and tx.get("transfer_metadata", {}).get("transfer_type") == "incoming":
                                        balance_changes_after_manual += float(tx.get("amount", 0))
                        
                        # Current balance = manual balance + perubahan setelah manual balance
                        current_balance = manual_balance + balance_changes_after_manual
                    else:
                        # Belum ada manual balance: hitung dari semua transaksi (baseline = 0)
                        # INCLUDE all transactions to calculate current balance correctly
                        print(f"⚠️  No manual balance found for {wallet.get('name')}, calculating from all transactions")
                        balance_changes_from_all = 0
                        for tx in transactions:
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
            except Exception as e:
                print(f"Error calculating current balance for {wallet.get('name')}: {e}")
                current_balance = manual_balance
            
            # Calculate ghost transactions: difference between manual balance and expected balance
            ghost_transactions = []
            total_ghost_positive = 0
            total_ghost_negative = 0
            
            try:
                if manual_balance_txs and len(manual_balance_txs) > 1:
                    # NEW: Sort by transaction_order if available, otherwise by timestamp
                    if any(tx.get("transaction_order") is not None for tx in manual_balance_txs):
                        # Use transaction_order for precise ordering
                        sorted_manual_balances = sorted(manual_balance_txs, key=lambda x: x.get("transaction_order", 0))
                    else:
                        # Fallback to timestamp sorting
                        sorted_manual_balances = sorted(manual_balance_txs, key=lambda x: x.get("timestamp", 0))
                    
                    for i in range(1, len(sorted_manual_balances)):
                        prev_manual_balance = float(sorted_manual_balances[i-1].get("amount", 0))
                        curr_manual_balance = float(sorted_manual_balances[i].get("amount", 0))
                        prev_timestamp = sorted_manual_balances[i-1].get("timestamp", 0)
                        curr_timestamp = sorted_manual_balances[i].get("timestamp", 0)
                        
                        # Calculate what the balance should be at this point based on transactions
                        # between prev_timestamp and curr_timestamp (inclusive for same timestamp)
                        # INCLUDE all transactions to calculate expected balance
                        # NEW: Use transaction_order field if available, otherwise fallback to timestamp
                        balance_changes_between = 0
                        
                        # NEW: Track unique transactions to avoid duplicates
                        seen_transactions = set()
                        
                        for tx in transactions:
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
                            # Use transaction_order if available, otherwise fallback to timestamp
                            confirmed_for_this_ghost = 0
                            for tx in transactions:
                                # NEW LOGIC: Check if transaction is after current manual balance
                                should_include = False
                                
                                if tx.get("transaction_order") is not None:
                                    # Use transaction_order for precise ordering
                                    curr_order = sorted_manual_balances[i].get("transaction_order", 0)
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
                    income_txs = [tx for tx in transactions if tx.get("type") == "income" and tx.get("timestamp")]
                    if income_txs:
                        last_income = max(int(tx.get("timestamp", 0)) for tx in income_txs)
                    else:
                        last_income = 0
                else:
                    last_income = 0
            except (ValueError, TypeError) as e:
                print(f"Error calculating last_income for {wallet.get('name')}: {e}")
                last_income = 0
                
            try:
                if transactions and isinstance(transactions, list):
                    expense_txs = [tx for tx in transactions if tx.get("type") == "expense" and tx.get("timestamp")]
                    if expense_txs:
                        last_expense = max(int(tx.get("timestamp", 0)) for tx in expense_txs)
                    else:
                        last_expense = 0
                else:
                    last_expense = 0
            except (ValueError, TypeError) as e:
                print(f"Error calculating last_expense for {wallet.get('name')}: {e}")
                last_expense = 0
                
            try:
                if transactions and isinstance(transactions, list):
                    transfer_txs = [tx for tx in transactions if tx.get("type") == "transfer" and tx.get("timestamp")]
                    if transfer_txs:
                        last_transfer = max(int(tx.get("timestamp", 0)) for tx in transfer_txs)
                    else:
                        last_transfer = 0
                else:
                    last_transfer = 0
            except (ValueError, TypeError) as e:
                print(f"Error calculating last_transfer for {wallet.get('name')}: {e}")
                last_transfer = 0
                
            try:
                if transactions and isinstance(transactions, list):
                    valid_txs = [tx for tx in transactions if tx.get("timestamp")]
                    if valid_txs:
                        last_transaction = max(int(tx.get("timestamp", 0)) for tx in valid_txs)
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
                    transfer_count = len([tx for tx in transactions if tx.get("type") == "transfer"])
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
                        # Get category name if available
                        category_name = None
                        if tx.get("category_id"):
                            try:
                                category = category_repo.find_one({"_id": ObjectId(tx["category_id"])})
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
                if individual_transactions:
                    # Check if any transaction has transaction_order field
                    if any(tx.get("transaction_order") is not None for tx in individual_transactions):
                        # Sort by transaction_order (ascending - oldest first)
                        individual_transactions.sort(key=lambda x: x.get("transaction_order", 0))
                    else:
                        # Fallback to timestamp sorting (newest first)
                        individual_transactions.sort(key=lambda x: x["timestamp"], reverse=True)
            except Exception as e:
                print(f"Error sorting individual transactions for {wallet.get('name')}: {e}")
            
            # Combine regular transactions with ghost transactions
            try:
                all_transactions = individual_transactions + ghost_transactions
                
                # NEW: Sort all transactions by transaction_order if available, otherwise by timestamp
                # This will show transactions in the correct order when scrolling
                if all_transactions:
                    # Check if any transaction has transaction_order field
                    if any(tx.get("transaction_order") is not None for tx in all_transactions):
                        # Sort by transaction_order (ascending - oldest first)
                        all_transactions.sort(key=lambda x: x.get("transaction_order", 0))
                    else:
                        # Fallback to timestamp sorting (oldest first), with manual balance transactions prioritized by base_time
                        all_transactions.sort(key=lambda x: (x.get("base_time", x.get("timestamp", 0)), x.get("is_manual_balance", False)), reverse=False)
            except Exception as e:
                print(f"Error combining and sorting all transactions for {wallet.get('name')}: {e}")
                all_transactions = individual_transactions
            
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
                "manual_balance_transactions": manual_balance_txs
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
        categories = category_repo.list_by_user(user_id)
        
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

@app.route("/api/wallets/<wallet_id>/balance", methods=["PUT"])
def update_wallet_balance(wallet_id):
    """Update manual balance for saving space"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        # Validate balance input
        if "manual_balance" not in body:
            return jsonify({"error": "manual_balance is required"}), 400
        
        try:
            manual_balance = float(body["manual_balance"])
        except (ValueError, TypeError):
            return jsonify({"error": "manual_balance must be a valid number"}), 400
        
        # Get current wallet to check if we need to add to history
        repo = WalletRepository()
        current_wallet = repo.find_one({"_id": ObjectId(wallet_id), "user_id": user_id})
        
        if not current_wallet:
            return jsonify({"error": "Saving space not found"}), 404
        
        # Prepare updates
        updates = {"manual_balance": manual_balance}
        
        # Create manual balance transaction for history tracking
        current_balance = current_wallet.get("manual_balance", 0)
        if abs(manual_balance - current_balance) > 0.01:  # Allow small floating point differences
            import time
            current_timestamp = int(time.time())
            
            # Create manual balance transaction for history tracking
            tx_repo = TransactionRepository()
            manual_balance_tx = {
                "user_id": user_id,
                "type": "manual_balance",  # Special type for manual balance updates
                "amount": manual_balance,
                "wallet_id": wallet_id,
                "description": f"Manual balance update: {current_balance} → {manual_balance}",
                "note": body.get("note", "Balance update"),
                "timestamp": current_timestamp,
                "currency": "IDR",
                "category_id": None,
                "scope_id": None,
                "base_time": current_timestamp,  # For sorting multiple balance updates
                "is_manual_balance": True  # Flag to identify manual balance transactions
            }
            
            # Insert the transaction
            tx_repo.insert_one(manual_balance_tx)
        
        # Update wallet with new balance (no history needed)
        success = repo.update_wallet(wallet_id, user_id, updates)
        
        if not success:
            return jsonify({"error": "Update failed"}), 500
        
        return jsonify({
            "message": "Manual balance updated successfully",
            "manual_balance": manual_balance,
            "added_to_history": True
        })
    except Exception as e:
        print(f"Error in update_wallet_balance: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/wallets/<wallet_id>/balance-history", methods=["GET"])
def get_wallet_balance_history(wallet_id):
    """Get manual balance history for saving space from transactions"""
    try:
        user_id = session.get("user_id", "demo_user")
        
        # Get repositories
        wallet_repo = WalletRepository()
        tx_repo = TransactionRepository()
        
        # Validate wallet exists and belongs to user
        wallet = wallet_repo.find_one({"_id": ObjectId(wallet_id), "user_id": user_id})
        if not wallet:
            return jsonify({"error": "Saving space not found"}), 404
        
        # Get manual balance transactions
        manual_balance_txs = tx_repo.get_transactions_with_filters(
            user_id, 
            {"wallet_id": wallet_id, "type": "manual_balance"}, 
            limit=100
        )
        
        # Convert to history format
        history = []
        for tx in manual_balance_txs:
            history.append({
                "balance": float(tx.get("amount", 0)),
                "timestamp": tx.get("timestamp", 0),
                "note": tx.get("note", "Balance update"),
                "description": tx.get("description", "")
            })
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return jsonify({
            "wallet_id": str(wallet["_id"]),
            "wallet_name": wallet["name"],
            "current_manual_balance": wallet.get("manual_balance", 0),
            "balance_history": history
        })
    except Exception as e:
        print(f"Error in get_wallet_balance_history: {e}")
        return jsonify({"error": str(e)}), 500

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
        
        # Check if source wallet has sufficient balance (use actual balance including transactions)
        manual_balance = from_wallet.get("manual_balance", 0)
        
        # Get actual balance by calculating from transactions
        try:
            from_wallet_transactions = tx_repo.get_transactions_with_filters(
                user_id, 
                {"wallet_id": str(from_wallet["_id"])}, 
                limit=1000
            )
            
            # Ensure we always have a list
            if from_wallet_transactions is None:
                from_wallet_transactions = []
            
            # Calculate actual balance
            total_income = 0
            total_expense = 0
            try:
                if from_wallet_transactions and isinstance(from_wallet_transactions, list):
                    total_income = sum(float(tx.get("amount", 0)) for tx in from_wallet_transactions if tx.get("type") == "income")
            except (ValueError, TypeError) as e:
                print(f"Error calculating total_income for transfer: {e}")
                total_income = 0
                
            try:
                if from_wallet_transactions and isinstance(from_wallet_transactions, list):
                    total_expense = sum(float(tx.get("amount", 0)) for tx in from_wallet_transactions if tx.get("type") == "expense")
            except (ValueError, TypeError) as e:
                print(f"Error calculating total_expense for transfer: {e}")
                total_expense = 0
            
            current_balance = manual_balance + total_income - total_expense
        except Exception as e:
            print(f"Error getting wallet transactions for transfer: {e}")
            # Fallback to manual balance only
            current_balance = manual_balance
            total_income = 0
            total_expense = 0
        
        total_debit = amount + admin_fee
        
        # Debug logging - after all variables are defined
        print(f"Transfer Debug - User ID: {user_id}")
        print(f"From Wallet ID: {from_wallet_id}, Found: {from_wallet is not None}")
        print(f"To Wallet ID: {to_wallet_id}, Found: {to_wallet is not None}")
        print(f"Manual Balance: {manual_balance}")
        print(f"Total Income: {total_income}")
        print(f"Total Expense: {total_expense}")
        print(f"Current Balance: {current_balance}")
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
            "category_id": None,
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
            "category_id": None,
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
        new_to_balance = to_wallet.get("manual_balance", 0) + amount
        
        # Update source wallet balance
        try:
            success_from = wallet_repo.update_wallet(str(from_wallet_id), user_id, {"manual_balance": new_from_balance})
            if not success_from:
                print(f"Warning: Failed to update source wallet balance for {from_wallet['name']}")
        except Exception as e:
            print(f"Error updating source wallet balance: {e}")
        
        # Update destination wallet balance
        try:
            success_to = wallet_repo.update_wallet(str(to_wallet_id), user_id, {"manual_balance": new_to_balance})
            if not success_to:
                print(f"Warning: Failed to update destination wallet balance for {to_wallet['name']}")
        except Exception as e:
            print(f"Error updating destination wallet balance: {e}")
        
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

