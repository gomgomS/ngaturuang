from flask import render_template, session, request
from mm.repositories.transactions import TransactionRepository
from mm.repositories.scopes import ScopeRepository
from mm.repositories.wallets import WalletRepository
from mm.repositories.categories import CategoryRepository

from . import bp


def _require_login_redirect():
    if not session.get("user_id"):
        return redirect(url_for("web.auth"))
    return None


def init_web_routes(app):
    @app.route("/dashboard")
    def dashboard():
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
            
        balance = total_income - total_expense
        
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
                             balance=balance)

    @app.route("/transactions")
    def transactions():
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

    @app.route("/transactions-type")
    def transactions_type():
        user_id = session.get("user_id", "demo_user")

        # Get repositories
        scope_repo = ScopeRepository()
        wallet_repo = WalletRepository()
        category_repo = CategoryRepository()

        # Get data
        scopes = scope_repo.list_by_user(user_id) or []
        wallets = wallet_repo.list_by_user(user_id) or []
        categories = category_repo.list_by_user(user_id) or []

        return render_template(
            "transaction_type.html",
            scopes=scopes,
            wallets=wallets,
            categories=categories,
        )

    @app.route("/goals")
    def goals():
        return render_template("goals.html")

    @app.route("/settings")
    def settings():
        user_id = session.get("user_id", "demo_user")
        
        # Get repositories
        scope_repo = ScopeRepository()
        wallet_repo = WalletRepository()
        category_repo = CategoryRepository()
        
        # Get data
        scopes = scope_repo.list_by_user(user_id)
        wallets = wallet_repo.list_by_user(user_id)
        categories = category_repo.list_by_user_with_defaults(user_id)
        
        # Ensure lists are passed
        scopes = scopes or []
        wallets = wallets or []
        categories = categories or []
        
        return render_template("settings.html",
                             scopes=scopes,
                             wallets=wallets,
                             categories=categories)


