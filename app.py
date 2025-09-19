import os
import json
from datetime import datetime
from flask import Flask, render_template, session, request, jsonify, redirect, url_for
from mm.repositories.transactions import TransactionRepository
from mm.repositories.scopes import ScopeRepository
from mm.repositories.wallets import WalletRepository
from mm.repositories.categories import CategoryRepository
from mm.repositories.ai_chats import AiChatRepository
from mm.repositories.users import UserRepository
from bson import ObjectId
from config import ensure_indexes
# from model import index_specs
from config import get_gemini_api_key
from mm.repositories.manual_balance import ManualBalanceRepository

app = Flask(__name__)
app.secret_key = "your-secret-key-here"

# Ensure database indexes (with error handling)
# try:
#     ensure_indexes(index_specs)
#     print("✅ Database indexes created successfully")
# except Exception as e:
#     print(f"⚠️ Warning: Could not create database indexes: {e}")
#     print("Application will continue without indexes...")

# Context processor to add total balance and username to all templates
@app.context_processor
def inject_global_data():
    """Inject total balance and username from session into all templates"""
    try:
        user_id = session.get("user_id")
        username = session.get("username")
           
        if user_id:
            # Calculate total balance using the same logic as dashboard
            # Get latest balance_after from all wallets up to current time
            current_timestamp = int(datetime.now().timestamp())
            total_balance = calculate_balance_from_transactions(user_id, current_timestamp)
            
            # If no transactions found, fallback to wallet actual_balance
            if total_balance == "-":
                wallet_repo = WalletRepository()
                wallets = wallet_repo.list_by_user(user_id)
                total_balance = sum(float(wallet.get("actual_balance", 0)) for wallet in wallets)

            return {
                "total_balance": total_balance,
                "username": username or "User"
            }
        else:

            return {
                "total_balance": 0,
                "username": "User"
            }
    except Exception as e:
        print(f"❌ [CONTEXT] Error calculating global data: {e}")
        import traceback
        print(f"❌ [CONTEXT] Error traceback: {traceback.format_exc()}")
        return {
            "total_balance": 0,
            "username": "User"
        }

# Helper function to check authentication
def require_login():
    """Check if user is logged in, redirect to login if not"""
    if not session.get("user_id"):
        return redirect("/login")
    return None

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

@app.template_filter('timestamp_to_date')
def timestamp_to_date_filter(timestamp):
    """Convert timestamp to readable date"""
    try:
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%d %b %Y')
    except (ValueError, TypeError):
        return "N/A"

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
        
        # Get current month data by default
        current_date = datetime.now()
        year = current_date.year
        month = current_date.month
        
        # Create start and end of current month timestamps
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        # Get data for current month only
        transactions = tx_repo.get_user_transactions_by_date_range(user_id, start_timestamp, end_timestamp, limit=10)
        
        # If no transactions in current month, get recent transactions from all time
        if not transactions:
            transactions = tx_repo.get_user_transactions_simple(user_id, limit=10)
        
        # Filter out system categories (Transfer and Balance Adjustment)
        system_categories = ["transfer", "balance_adjustment"]
        transactions = [tx for tx in transactions if tx.get("category_id") not in system_categories]
        
        scopes = scope_repo.list_by_user(user_id)
        wallets = wallet_repo.list_by_user(user_id)
        
        # Calculate totals for current month only
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
        
        # Get current month name for display
        current_month_name = current_date.strftime('%B %Y')
        
        # Process tags data - get all user transactions to count tags (excluding system categories)
        all_transactions = tx_repo.get_user_transactions_simple(user_id, limit=1000)  # Get more transactions for better tag analysis
        all_transactions = [tx for tx in all_transactions if tx.get("category_id") not in system_categories]
        tag_counts = {}
        
        for tx in all_transactions:
            tags = tx.get("tags", [])
            if isinstance(tags, list) and tags:
                for tag in tags:
                    if tag and tag.strip():  # Skip empty tags
                        tag = tag.strip().lower()
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
            elif isinstance(tags, str) and tags.strip():
                tag = tags.strip().lower()
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Get top 5 most used tags
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
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
                             current_month_name=current_month_name,
                             top_tags=top_tags)
    except Exception as e:
        print(f"Error in dashboard: {e}")
        # Get current month name for display even in error case
        current_month_name = datetime.now().strftime('%B %Y')
        
        return render_template("dashboard.html", 
                             transactions=[],
                             scopes=[],
                             wallets=[],
                             total_income=0,
                             total_expense=0,
                             total_transfer=0,
                             total_admin_fees=0,
                             balance=0,
                             total_transactions=0,
                             current_month_name=current_month_name,
                             top_tags=[])

@app.route("/api/dashboard-data")
def api_dashboard_data():
    """API endpoint to get dashboard data for a specific month"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Get year parameter (format: YYYY)
        year = request.args.get('year')
        if not year or year == 'undefined':
            return jsonify({"error": "Year parameter required"}), 400
        
        # Get month parameter (optional, format: YYYY-MM)
        month = request.args.get('month')
        
        # Get day parameter (optional, format: DD)
        day = request.args.get('day')
        
        # Parse parameters to get start and end timestamps
        try:
            year = int(year)
            
            if day and month:
                # Filter by specific day
                month_parts = month.split('-')
                month_num = int(month_parts[1])
                day_num = int(day)
                start_date = datetime(year, month_num, day_num)
                end_date = datetime(year, month_num, day_num + 1)
            elif month:
                # Filter by entire month
                month_parts = month.split('-')
                month_num = int(month_parts[1])
                start_date = datetime(year, month_num, 1)
                if month_num == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month_num + 1, 1)
            else:
                # Filter by entire year
                start_date = datetime(year, 1, 1)
                end_date = datetime(year + 1, 1, 1)
            
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
        except ValueError:
            return jsonify({"error": "Invalid month format"}), 400
        
        # Get repositories
        tx_repo = TransactionRepository()
        wallet_repo = WalletRepository()
        
        # Get transactions for the specified month
        transactions = tx_repo.get_user_transactions_by_date_range(user_id, start_timestamp, end_timestamp)
        
        # Filter out system categories (Transfer and Balance Adjustment)
        system_categories = ["transfer", "balance_adjustment"]
        filtered_transactions = [tx for tx in transactions if tx.get("category_id") not in system_categories]
        
        # Calculate totals for the month (excluding system categories)
        total_income = sum(float(tx.get("amount", 0)) for tx in filtered_transactions if tx.get("type") == "income")
        total_expenses = sum(float(tx.get("amount", 0)) for tx in filtered_transactions if tx.get("type") == "expense")
        total_transfer = sum(float(tx.get("amount", 0)) for tx in filtered_transactions if tx.get("type") == "transfer")
        transaction_count = len(filtered_transactions)
        
        # Calculate total balance based on latest transaction balance_after for each wallet up to selected date
        # For month-only or year-only selection, pass start_timestamp to limit the search to that period
        total_balance = calculate_balance_from_transactions(user_id, end_timestamp, start_timestamp)
        
        # Calculate comparison data (yesterday for specific day, previous month for specific month)
        yesterday_balance = None
        balance_improvement = None
        yesterday_income = None
        income_improvement = None
        yesterday_expenses = None
        expenses_improvement = None
        
        previous_month_balance = None
        previous_month_income = None
        previous_month_expenses = None
        previous_month_balance_improvement = None
        previous_month_income_improvement = None
        previous_month_expenses_improvement = None
        
        if day and month:
            # Calculate yesterday's data for specific day
            yesterday_date = datetime(year, month_num, day_num - 1)
            yesterday_timestamp = int(yesterday_date.timestamp())
            yesterday_balance = calculate_balance_from_transactions(user_id, yesterday_timestamp)
            
            # Calculate yesterday's income and expenses (excluding system categories)
            yesterday_transactions = tx_repo.get_user_transactions_by_date_range(user_id, yesterday_timestamp, yesterday_timestamp + 86400)  # 24 hours
            yesterday_filtered = [tx for tx in yesterday_transactions if tx.get("category_id") not in system_categories]
            yesterday_income = sum(float(tx.get("amount", 0)) for tx in yesterday_filtered if tx.get("type") == "income")
            yesterday_expenses = sum(float(tx.get("amount", 0)) for tx in yesterday_filtered if tx.get("type") == "expense")
            
            # Calculate improvements if data is available
            if yesterday_balance != "-" and total_balance != "-":
                try:
                    yesterday_balance_float = float(yesterday_balance)
                    total_balance_float = float(total_balance)
                    balance_improvement = total_balance_float - yesterday_balance_float
                except (ValueError, TypeError):
                    balance_improvement = None
            
            # Calculate income improvement
            try:
                income_improvement = total_income - yesterday_income
            except (ValueError, TypeError):
                income_improvement = None
                
            # Calculate expenses improvement (negative means less spending, positive means more spending)
            try:
                expenses_improvement = total_expenses - yesterday_expenses
            except (ValueError, TypeError):
                expenses_improvement = None
                
        elif month and not day:
            # Calculate previous month's data for specific month
            if month_num == 1:
                # Previous month is December of previous year
                prev_month_date = datetime(year - 1, 12, 1)
                prev_month_end = datetime(year, 1, 1)
            else:
                # Previous month is in the same year
                prev_month_date = datetime(year, month_num - 1, 1)
                prev_month_end = datetime(year, month_num, 1)
            
            prev_month_timestamp = int(prev_month_date.timestamp())
            prev_month_end_timestamp = int(prev_month_end.timestamp())
            
            # Calculate previous month's balance
            previous_month_balance = calculate_balance_from_transactions(user_id, prev_month_end_timestamp)
            
            # Calculate previous month's income and expenses (excluding system categories)
            prev_month_transactions = tx_repo.get_user_transactions_by_date_range(user_id, prev_month_timestamp, prev_month_end_timestamp)
            prev_month_filtered = [tx for tx in prev_month_transactions if tx.get("category_id") not in system_categories]
            previous_month_income = sum(float(tx.get("amount", 0)) for tx in prev_month_filtered if tx.get("type") == "income")
            previous_month_expenses = sum(float(tx.get("amount", 0)) for tx in prev_month_filtered if tx.get("type") == "expense")
            
            # Calculate improvements if data is available
            if previous_month_balance != "-" and total_balance != "-":
                try:
                    prev_balance_float = float(previous_month_balance)
                    total_balance_float = float(total_balance)
                    previous_month_balance_improvement = total_balance_float - prev_balance_float
                except (ValueError, TypeError):
                    previous_month_balance_improvement = None
            
            # Calculate income improvement
            try:
                previous_month_income_improvement = total_income - previous_month_income
            except (ValueError, TypeError):
                previous_month_income_improvement = None
                
            # Calculate expenses improvement
            try:
                previous_month_expenses_improvement = total_expenses - previous_month_expenses
            except (ValueError, TypeError):
                previous_month_expenses_improvement = None
        
        # Get recent transactions (limit to 5, excluding system categories)
        recent_transactions = filtered_transactions[:5]
        
        # Generate chart data based on filter type (using filtered transactions)
        if day and month:
            # For day view, show hourly breakdown
            month_parts = month.split('-')
            month_num = int(month_parts[1])
            day_num = int(day)
            chart_data = generate_daily_chart_data(filtered_transactions, year, month_num, day_num)
        elif month:
            # For month view, show daily breakdown
            month_parts = month.split('-')
            month_num = int(month_parts[1])
            chart_data = generate_monthly_chart_data(filtered_transactions, year, month_num)
        else:
            # For year view, show monthly breakdown
            chart_data = generate_yearly_chart_data(filtered_transactions, year)
        
        return jsonify({
            "total_balance": total_balance,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "total_transfer": total_transfer,
            "transaction_count": transaction_count,
            "recent_transactions": recent_transactions,
            "chartData": chart_data,
            "yesterday_balance": yesterday_balance,
            "balance_improvement": balance_improvement,
            "yesterday_income": yesterday_income,
            "income_improvement": income_improvement,
            "yesterday_expenses": yesterday_expenses,
            "expenses_improvement": expenses_improvement,
            "previous_month_balance": previous_month_balance,
            "previous_month_balance_improvement": previous_month_balance_improvement,
            "previous_month_income": previous_month_income,
            "previous_month_income_improvement": previous_month_income_improvement,
            "previous_month_expenses": previous_month_expenses,
            "previous_month_expenses_improvement": previous_month_expenses_improvement
        })
        
    except Exception as e:
        print(f"Error in api_dashboard_data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/balance-analysis")
def api_balance_analysis():
    """API endpoint to analyze balance discrepancies between wallets and transactions"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Get repositories
        wallet_repo = WalletRepository()
        
        # Get all wallets for the user
        wallets = wallet_repo.list_by_user(user_id)
        
        # Analyze each wallet
        discrepancies = []
        total_discrepancy_amount = 0
        
        for wallet in wallets:
            wallet_id = wallet.get("_id")
            wallet_name = wallet.get("name", "Unknown Wallet")
            actual_balance = float(wallet.get("actual_balance", 0))
            
            # Calculate balance from transactions for this wallet
            calculated_balance = calculate_wallet_balance_from_transactions(user_id, wallet_id)
            
            # Calculate discrepancy
            discrepancy_amount = actual_balance - calculated_balance
            
            # Only include if there's a significant discrepancy (more than 1 Rupiah)
            if abs(discrepancy_amount) > 1:
                discrepancies.append({
                    "wallet_id": str(wallet_id),
                    "wallet_name": wallet_name,
                    "actual_balance": actual_balance,
                    "calculated_balance": calculated_balance,
                    "discrepancy_amount": discrepancy_amount
                })
                total_discrepancy_amount += discrepancy_amount
        
        # Prepare summary
        summary = {
            "total_wallets": len(wallets),
            "discrepancies_found": len(discrepancies),
            "total_discrepancy_amount": total_discrepancy_amount
        }
        
        return jsonify({
            "summary": summary,
            "discrepancies": discrepancies
        })
        
    except Exception as e:
        print(f"Error in api_balance_analysis: {e}")
        return jsonify({"error": "Internal server error"}), 500

def generate_monthly_chart_data(transactions, year, month_num):
    """Generate chart data for a specific month"""
    try:
        # Get number of days in the month
        if month_num == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month_num + 1, 1)
        
        days_in_month = (next_month - datetime(year, month_num, 1)).days
        
        # Initialize daily data
        daily_income = [0] * days_in_month
        daily_expenses = [0] * days_in_month
        labels = []
        
        # Generate labels for each day
        for day in range(1, days_in_month + 1):
            labels.append(f"{day}")
        
        # Process transactions
        for tx in transactions:
            try:
                # Convert timestamp to date
                tx_date = datetime.fromtimestamp(tx.get("timestamp", 0))
                day_index = tx_date.day - 1  # 0-based index
                
                if 0 <= day_index < days_in_month:
                    amount = float(tx.get("amount", 0))
                    tx_type = tx.get("type", "")
                    
                    if tx_type == "income":
                        daily_income[day_index] += amount
                    elif tx_type == "expense":
                        daily_expenses[day_index] += amount
                        
            except (ValueError, TypeError) as e:
                print(f"Error processing transaction for chart: {e}")
                continue
        
        return {
            "labels": labels,
            "income": daily_income,
            "expenses": daily_expenses
        }
        
    except Exception as e:
        print(f"Error generating chart data: {e}")
        # Return empty data structure
        return {
            "labels": [],
            "income": [],
            "expenses": []
        }

def generate_daily_chart_data(transactions, year, month_num, day_num):
    """Generate chart data for a specific day (hourly breakdown)"""
    try:
        # Initialize hourly data (24 hours)
        hourly_income = [0] * 24
        hourly_expenses = [0] * 24
        labels = []
        
        # Generate labels for each hour
        for hour in range(24):
            labels.append(f"{hour:02d}:00")
        
        # Process transactions
        for tx in transactions:
            try:
                # Convert timestamp to datetime
                tx_date = datetime.fromtimestamp(tx.get("timestamp", 0))
                hour_index = tx_date.hour
                
                if 0 <= hour_index < 24:
                    amount = float(tx.get("amount", 0))
                    tx_type = tx.get("type", "")
                    
                    if tx_type == "income":
                        hourly_income[hour_index] += amount
                    elif tx_type == "expense":
                        hourly_expenses[hour_index] += amount
                        
            except (ValueError, TypeError) as e:
                print(f"Error processing transaction for daily chart: {e}")
                continue
        
        return {
            "labels": labels,
            "income": hourly_income,
            "expenses": hourly_expenses
        }
        
    except Exception as e:
        print(f"Error generating daily chart data: {e}")
        # Return empty data structure
        return {
            "labels": [],
            "income": [],
            "expenses": []
        }

def generate_yearly_chart_data(transactions, year):
    """Generate chart data for a specific year (monthly breakdown)"""
    try:
        # Initialize monthly data (12 months)
        monthly_income = [0] * 12
        monthly_expenses = [0] * 12
        labels = []
        
        # Generate labels for each month
        for month in range(1, 13):
            date = datetime(year, month, 1)
            month_name = date.strftime('%b')  # Short month name
            labels.append(month_name)
        
        # Process transactions
        for tx in transactions:
            try:
                # Convert timestamp to datetime
                tx_date = datetime.fromtimestamp(tx.get("timestamp", 0))
                month_index = tx_date.month - 1  # 0-based index
                
                if 0 <= month_index < 12:
                    amount = float(tx.get("amount", 0))
                    tx_type = tx.get("type", "")
                    
                    if tx_type == "income":
                        monthly_income[month_index] += amount
                    elif tx_type == "expense":
                        monthly_expenses[month_index] += amount
                        
            except (ValueError, TypeError) as e:
                print(f"Error processing transaction for yearly chart: {e}")
                continue
        
        return {
            "labels": labels,
            "income": monthly_income,
            "expenses": monthly_expenses
        }
        
    except Exception as e:
        print(f"Error generating yearly chart data: {e}")
        # Return empty data structure
        return {
            "labels": [],
            "income": [],
            "expenses": []
        }

def calculate_balance_from_transactions(user_id, end_timestamp, start_timestamp=None):
    """Calculate total balance based on latest transaction balance_after for each wallet up to selected date"""
    try:
        from config import get_collection
        
        # Get all transactions for the user up to the end timestamp
        coll = get_collection("transactions")
        
        # For balance calculation, we always want the latest transaction up to the end_timestamp
        # regardless of start_timestamp (which is used for income/expense filtering)
        balance_match_query = {
            "user_id": user_id,
            "timestamp": {"$lte": end_timestamp}
        }
        
        # Find the latest transaction for each wallet up to the end timestamp
        pipeline = [
            {
                "$match": balance_match_query
            },
            {
                "$sort": {"wallet_id": 1, "timestamp": -1, "sequence_number": -1}
            },
            {
                "$group": {
                    "_id": "$wallet_id",
                    "latest_transaction": {"$first": "$$ROOT"}
                }
            }
        ]
        
        latest_transactions = list(coll.aggregate(pipeline))
        
        # If no transactions found for the period, return "-"
        if not latest_transactions:
            return "-"
        
        # Sum up the balance_after from the latest transaction of each wallet
        total_balance = 0
        for wallet_data in latest_transactions:
            latest_tx = wallet_data.get("latest_transaction", {})
            balance_after = latest_tx.get("balance_after", 0)
            if balance_after is not None:
                total_balance += float(balance_after)
        
        return total_balance
        
    except Exception as e:
        print(f"Error calculating balance from transactions: {e}")
        # Fallback to current wallet balance if there's an error
        try:
            wallet_repo = WalletRepository()
            wallets = wallet_repo.list_by_user(user_id)
            return sum(float(wallet.get("actual_balance", 0)) for wallet in wallets)
        except:
            return "-"

def get_latest_wallet_balance(user_id, wallet_id, end_timestamp):
    """Get the latest balance_after for a specific wallet up to the given timestamp"""
    try:
        from config import get_collection
        
        coll = get_collection("transactions")
        
        # Find the latest transaction for this specific wallet up to the end timestamp
        latest_tx = coll.find_one(
            {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "timestamp": {"$lte": end_timestamp}
            },
            sort=[("timestamp", -1), ("sequence_number", -1)]
        )
        
        if latest_tx and latest_tx.get("balance_after") is not None:
            return float(latest_tx.get("balance_after", 0))
        else:
            # If no transactions found, return 0
            return 0.0
            
    except Exception as e:
        print(f"Error getting latest wallet balance: {e}")
        return 0.0

def calculate_wallet_balance_from_transactions(user_id, wallet_id):
    """Calculate balance for a specific wallet based on its latest transaction"""
    try:
        from config import get_collection
        
        # Get all transactions for the specific wallet
        coll = get_collection("transactions")
        
        # Find the latest transaction for this wallet
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "wallet_id": wallet_id
                }
            },
            {
                "$sort": {"timestamp": -1, "sequence_number": -1}
            },
            {
                "$limit": 1
            }
        ]
        
        latest_transaction = list(coll.aggregate(pipeline))
        
        if latest_transaction:
            balance_after = latest_transaction[0].get("balance_after", 0)
            return float(balance_after) if balance_after is not None else 0
        else:
            # No transactions found for this wallet, return 0
            return 0
        
    except Exception as e:
        print(f"Error calculating wallet balance from transactions: {e}")
        return 0

@app.route("/transactions")
def transactions():
    # Check authentication
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    try:
        user_id = session.get("user_id")
        
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
        
        # Get pagination parameters
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))  # Default 10 transactions per page
        
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
        
        # Get transactions with filters and pagination
        try:
            if filters:
                transactions, total_count = tx_repo.get_transactions_with_filters_paginated(user_id, filters, page, per_page)
            elif scope_id:
                transactions, total_count = tx_repo.get_transactions_by_scope_paginated(user_id, scope_id, page, per_page)
            else:
                transactions, total_count = tx_repo.get_user_transactions_paginated(user_id, page, per_page)
        except Exception as e:
            print(f"Error getting paginated transactions: {e}")
            # Fallback to non-paginated method
            if filters:
                transactions = tx_repo.get_transactions_with_filters(user_id, filters, limit=200)
            elif scope_id:
                transactions = tx_repo.get_transactions_by_scope(user_id, scope_id, limit=200)
            else:
                transactions = tx_repo.get_user_transactions_simple(user_id, limit=200)
            total_count = len(transactions)
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        has_prev = page > 1
        has_next = page < total_pages
        
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
                             # Pagination data
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages,
                             total_count=total_count,
                             has_prev=has_prev,
                             has_next=has_next,
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

@app.route("/transactions-type")
def transactions_type():
    # Check authentication
    auth_check = require_login()
    if auth_check:
        return auth_check
    try:
        user_id = session.get("user_id")

        # Get repositories
        scope_repo = ScopeRepository()
        wallet_repo = WalletRepository()
        category_repo = CategoryRepository()

        # Get data
        scopes = scope_repo.list_by_user(user_id) or []
        wallets = wallet_repo.list_by_user(user_id) or []
        categories = category_repo.list_by_user_with_defaults(user_id) or []

        return render_template(
            "transaction_type.html",
            scopes=scopes,
            wallets=wallets,
            categories=categories,
        )
    except Exception as e:
        print(f"Error in transactions_type: {e}")
        return render_template(
            "transaction_type.html",
            scopes=[],
            wallets=[],
            categories=[],
        )

@app.route("/goals")
def goals():
    # Check authentication
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    return render_template("goals.html")

@app.route("/accounts")
def accounts():
    # Check authentication
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    user_id = session.get("user_id", "demo_user")
    
    # Get repositories
    wallet_repo = WalletRepository()
    scope_repo = ScopeRepository()
    category_repo = CategoryRepository()
    
    # Get all wallets for the user
    wallets = wallet_repo.list_by_user(user_id)
    
    # Get all scopes for the user
    scopes = scope_repo.list_by_user(user_id)
    
    # Get all categories for the user (including defaults)
    categories = category_repo.list_by_user_with_defaults(user_id)
    
    # Get transaction repository for scope filtering
    tx_repo = TransactionRepository()
    
    # Calculate balance from latest transaction for each wallet and check scope usage
    if wallets:
        current_timestamp = int(datetime.now().timestamp())
        
        for wallet in wallets:
            wallet_id = wallet.get("_id")
            if wallet_id:
                # Get latest transaction for this wallet
                latest_balance = get_latest_wallet_balance(user_id, wallet_id, current_timestamp)
                # Update the wallet with the latest balance
                wallet["latest_balance"] = latest_balance
                
                # Check which scopes this wallet has transactions in
                wallet_scopes = set()
                try:
                    # Get all transactions for this wallet using filters
                    wallet_filters = {"wallet_id": wallet_id}
                    wallet_transactions = tx_repo.get_transactions_with_filters(user_id, wallet_filters, limit=1000)
                    for tx in wallet_transactions:
                        if tx.get('scope_id'):
                            wallet_scopes.add(tx['scope_id'])
                except Exception as e:
                    print(f"Error getting wallet transactions: {e}")
                
                wallet["scopes_with_transactions"] = list(wallet_scopes)
            else:
                wallet["latest_balance"] = 0
                wallet["scopes_with_transactions"] = []
    
    # Ensure lists are passed
    wallets = wallets or []
    scopes = scopes or []
    categories = categories or []
    
    return render_template("accounts.html", wallets=wallets, scopes=scopes, categories=categories)

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
    # Check authentication
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    try:
        user_id = session.get("user_id")
        
        # Get repositories
        wallet_repo = WalletRepository()
        tx_repo = TransactionRepository()
        category_repo = CategoryRepository()
        
        # Get all wallets for the user
        all_wallets = wallet_repo.list_by_user(user_id)
        if all_wallets:
            wallets = all_wallets  # Take all wallets
        else:
            wallets = []
        
        # Ensure the single wallet has actual_balance field initialized
        for wallet in wallets:
            if "actual_balance" not in wallet or wallet["actual_balance"] is None:
                wallet_id_str = str(wallet.get("_id"))

                # Set default actual_balance to 0 if not exists
                wallet["actual_balance"] = 0.0
                
                # Update in database
                try:
                    wallet_repo.update_wallet_balance(wallet_id_str, user_id, 0.0)
                except Exception as e:
                    print(f"❌ [BALANCE] Failed to initialize actual_balance for {wallet.get('name')}: {e}")
        
        # Get balance data with transactions for the single wallet
        balance_data = []
        for wallet in wallets:
            wallet_id = wallet.get("_id")
            
            # Get transactions for this wallet ONLY
            wallet_id_str = str(wallet_id)

            # Get latest manual balance for this wallet
            latest_manual_balance = None
            try:
                from mm.repositories.manual_balance import ManualBalanceRepository
                manual_balance_repo = ManualBalanceRepository()
                latest_manual_balance = manual_balance_repo.get_latest_balance(user_id, wallet_id_str)
                
            except Exception as e:
                print(f"❌ [BALANCE] Error getting latest manual balance: {e}")
            
            # Get transactions that belong to this specific wallet AND manual balance sequence
            try:
                if latest_manual_balance:
                    # Get transactions from the latest manual balance sequence
                    manual_balance_id = str(latest_manual_balance['_id'])
    
                    transactions = tx_repo.get_transactions_by_manual_balance(
                        user_id, 
                        manual_balance_id, 
                        limit=1000
                    )
                else:
                    # Fallback: get all transactions for this wallet
                    transactions = tx_repo.get_transactions_with_filters(
                        user_id, 
                        {"wallet_id": wallet_id_str}, 
                        limit=1000
                    )
            
                # Ensure we always have a list, never None
                if transactions is None:
                    print(f"⚠️ Transactions is None for {wallet.get('name')}, setting to empty list")
                    transactions = []
                elif not isinstance(transactions, list):
                    print(f"⚠️ Transactions is not a list for {wallet.get('name')}, converting to list")
                    transactions = list(transactions) if transactions else []
                
 
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
                for i, tx in enumerate(transactions[:3]):
                    print(f"   {i+1}. Type: {tx.get('type')}, Amount: {tx.get('amount')}, Wallet: {tx.get('wallet_id')}")

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

                    else:
                        # Tidak ada manual balance history, hitung dari semua transaksi

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

                    else:
                        # Tidak ada real balance history, hitung dari semua transaksi
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

@app.route("/analysis")
def analysis():
    # Check authentication
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    try:
        user_id = session.get("user_id")
        
        # Get repositories
        wallet_repo = WalletRepository()
        
        # Get user data
        wallets = wallet_repo.list_by_user(user_id)
        
        # Calculate total balance
        total_balance = sum(float(wallet.get("actual_balance", 0)) for wallet in wallets)
        
        return render_template("analysis.html", 
                             username=session.get("username"),
                             wallets=wallets,
                             total_balance=total_balance)
    
    except Exception as e:
        print(f"Error in analysis: {e}")
        return render_template("analysis.html", 
                             username=session.get("username"),
                             wallets=[],
                             total_balance=0)

@app.route("/settings")
def settings():
    # Check authentication
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    try:
        user_id = session.get("user_id")
        
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

@app.route("/ai-advisor")
def ai_advisor():
    # Check authentication
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    try:
        user_id = session.get("user_id")
        
        # Get repositories
        scope_repo = ScopeRepository()
        wallet_repo = WalletRepository()
        category_repo = CategoryRepository()
        
        # Get data for filters
        scopes = scope_repo.list_by_user(user_id)
        wallets = wallet_repo.list_by_user(user_id)
        categories = category_repo.list_by_user_with_defaults(user_id)
        
        # Ensure lists are passed
        scopes = scopes or []
        wallets = wallets or []
        categories = categories or []
        
        return render_template("ai_advisor.html",
                             scopes=scopes,
                             wallets=wallets,
                             categories=categories)
    except Exception as e:
        print(f"Error in ai_advisor: {e}")
        return render_template("ai_advisor.html",
                             scopes=[],
                             wallets=[],
                             categories=[])

# API Routes
@app.route("/api/ai/chat", methods=["POST"])
def api_ai_chat():
    """Append a chat message into per-user conversation document.

    Body JSON is stored as-is under messages[].data with minimal metadata.
    """
    try:
        user_id = session.get("user_id", "demo_user")
        data = request.get_json(force=True) or {}
        message_text = (data.get("message") or "").strip()
        if not message_text:
            return jsonify({"error": "message is required"}), 400

        # Map helpers to proper types/ids using user's data (categories, wallets, scopes)
        try:
            # Load master data
            cat_repo = CategoryRepository()
            wal_repo = WalletRepository()
            scp_repo = ScopeRepository()
            categories = cat_repo.list_by_user_with_defaults(user_id) or []
            wallets = wal_repo.list_by_user(user_id) or []
            scopes = scp_repo.list_by_user(user_id) or []

            # Build lookup maps by lowercase name
            cat_map = {str(c.get("name", "")).strip().lower(): {"type": "category", "id": str(c.get("_id")), "name": c.get("name")}
                       for c in categories if c.get("name")}
            wal_map = {str(w.get("name", "")).strip().lower(): {"type": "wallet", "id": str(w.get("_id")), "name": w.get("name")}
                       for w in wallets if w.get("name")}
            scp_map = {str(s.get("name", "")).strip().lower(): {"type": "scope", "id": str(s.get("_id")), "name": s.get("name")}
                       for s in scopes if s.get("name")}

            # Parse helpers from payload or message
            helpers_in = data.get("helpers") or []
            if not helpers_in:
                import re
                found = re.findall(r"\(@([^\)]+)\)", message_text)
                helpers_in = [{"name": n} for n in found]

            mapped_helpers = []
            for h in helpers_in:
                name = str(h.get("name", "")).strip()
                if not name:
                    continue
                key = name.lower()
                info = cat_map.get(key) or wal_map.get(key) or scp_map.get(key)
                if info:
                    mapped_helpers.append({"type": info["type"], "name": info["name"], "id": info["id"]})
                else:
                    mapped_helpers.append({"type": h.get("type") or "unknown", "name": name})
        except Exception:
            # Fallback: keep original helpers
            mapped_helpers = data.get("helpers") or []

        # Enrich payload minimally while storing full JSON under data
        payload = dict(data)
        payload.setdefault("text", message_text)
        # Store both user id and username in payload
        username = session.get("username")
        payload["user_id"] = user_id
        if username is not None:
            payload["user_name"] = username
        payload.setdefault("received_at", int(datetime.now().timestamp()))
        # Overwrite helpers with mapped helpers
        payload["helpers"] = mapped_helpers

        repo = AiChatRepository()
        conversation = repo.append_message(user_id, payload)
        # Generate helper-based transactions JSON file under data/json_banks.json (raw transactions with relations)
        try:
            tx_repo = TransactionRepository()
            base_dir = os.path.dirname(os.path.abspath(__file__))
            out_dir = os.path.join(base_dir, "data")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "json_banks.json")
            # Clear file first
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write("{}")
            except Exception as _e:
                print(f"Error clearing json_banks.json: {_e}")
            # Build lookup maps for names
            cat_name = {}
            wal_name = {}
            scp_name = {}
            try:
                for c in categories:
                    if c.get("_id") and c.get("name"):
                        cat_name[str(c["_id"])]= c.get("name")
            except Exception:
                pass
            try:
                for w in wallets:
                    if w.get("_id") and w.get("name"):
                        wal_name[str(w["_id"])]= w.get("name")
            except Exception:
                pass
            try:
                for s in scopes:
                    if s.get("_id") and s.get("name"):
                        scp_name[str(s["_id"])]= s.get("name")
            except Exception:
                pass

            # Collect transactions matching any helper
            union_map = {}
            cat_ids = [h.get("id") for h in mapped_helpers if h.get("type") == "category" and h.get("id")]
            wal_ids = [h.get("id") for h in mapped_helpers if h.get("type") == "wallet" and h.get("id")]
            scp_ids = [h.get("id") for h in mapped_helpers if h.get("type") == "scope" and h.get("id")]

            def add_txs(filters):
                txs = tx_repo.get_transactions_with_filters(user_id, filters, limit=2000)
                for t in txs:
                    tid = str(t.get("_id"))
                    union_map[tid] = t

            for c in cat_ids:
                add_txs({"category_id": c})
            for w in wal_ids:
                add_txs({"wallet_id": w})
            for s in scp_ids:
                add_txs({"scope_id": s})

            # Build raw list with relation info
            tx_items = []
            for t in union_map.values():
                cat_id = str(t.get("category_id") or "")
                wal_id = str(t.get("wallet_id") or "")
                scp_id = str(t.get("scope_id") or "")
                tx_items.append({
                    "_id": str(t.get("_id")),
                    "amount": float(t.get("amount", 0) or 0),
                    "type": t.get("type", ""),
                    "timestamp": t.get("timestamp"),
                    "tags": t.get("tags", []),
                    "note": t.get("note"),
                    "category": {"id": cat_id or None, "name": cat_name.get(cat_id) if cat_id else None, "selected": cat_id in cat_ids},
                    "wallet": {"id": wal_id or None, "name": wal_name.get(wal_id) if wal_id else None, "selected": wal_id in wal_ids},
                    "scope": {"id": scp_id or None, "name": scp_name.get(scp_id) if scp_id else None, "selected": scp_id in scp_ids}
                })

            output = {
                "meta": {
                    "user_id": user_id,
                    "user_name": username,
                    "message": message_text,
                    "generated_at": int(datetime.now().timestamp())
                },
                "helpers": mapped_helpers,
                "transactions": tx_items
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error generating json_banks.json: {e}")
        # Build AI-style analysis text based on prompt and json
        ai_text = None
        ai_provider = None
        ai_model = None
        try:
            # Read the freshly created JSON
            with open(out_path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
            helpers_list = dataset.get("helpers", [])
            txs = dataset.get("transactions", [])
            # Try Gemini first if API key available
            try:
                api_key = get_gemini_api_key()

                if api_key:
                    prompt_path = os.path.join(base_dir, "data", "prompt_advicer.ai")
                    prompt_text = ""
                    try:
                        with open(prompt_path, "r", encoding="utf-8") as pf:
                            prompt_text = pf.read()
                    except Exception:
                        prompt_text = "You are a financial advisor. Analyze the following JSON."
                    user_payload = (
                        prompt_text
                        + "\n\nFormat the response in clear Markdown with headings and bullet/numbered lists. Keep it concise.\n"
                        + "\nJSON dataset:\n"
                        + json.dumps(dataset, ensure_ascii=False)
                    )
                    # Call Gemini via REST with simple retries on transient errors
                    import urllib.request, urllib.error, time
                    request_body = json.dumps({
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": user_payload}]
                            }
                        ]
                    }).encode("utf-8")
                    model_id = "gemini-1.5-flash-latest"
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
                    headers = {"Content-Type": "application/json"}
                    for attempt in range(3):
                        try:
                            req = urllib.request.Request(url=url, method="POST", data=request_body, headers=headers)
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                resp_raw = resp.read().decode("utf-8")
                                resp_json = json.loads(resp_raw)
                                cand = (resp_json.get("candidates") or [{}])[0]
                                cont = cand.get("content") or {}
                                parts = cont.get("parts") or []
                                if parts and isinstance(parts, list) and parts[0].get("text"):
                                    ai_text = parts[0]["text"]
                                    ai_provider = "Gemini"
                                    ai_model = model_id
                                break
                        except urllib.error.HTTPError as he:
                            body = he.read().decode("utf-8", errors="ignore") if hasattr(he, 'read') else ''
                            print(f"Gemini HTTPError {he.code}: {body[:500]}")
                            if he.code in (429, 500, 502, 503, 504):
                                time.sleep(2 ** attempt)
                                continue
                            else:
                                raise
                        except Exception as e:
                            print(f"Gemini call exception: {e}")
                            time.sleep(2 ** attempt)
                            continue
            except Exception as ge:
                print(f"Gemini call failed: {ge}")
            # Fallback to OpenAI if available and Gemini didn't return
            if not ai_text:
                try:
                    from config import get_openai_api_key
                    oai_key = get_openai_api_key()
                    if oai_key:
                        prompt_path = os.path.join(base_dir, "data", "prompt_advicer.ai")
                        try:
                            with open(prompt_path, "r", encoding="utf-8") as pf:
                                prompt_text = pf.read()
                        except Exception:
                            prompt_text = "You are a financial advisor. Analyze the following JSON."
                        user_payload = (
                            prompt_text
                            + "\n\nFormat the response in clear Markdown with headings and bullet/numbered lists. Keep it concise.\n"
                            + "\nJSON dataset:\n"
                            + json.dumps(dataset, ensure_ascii=False)
                        )
                        import urllib.request, urllib.error
                        url = "https://api.openai.com/v1/responses"
                        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {oai_key}"}
                        openai_model = "gpt-4o-mini"
                        body = json.dumps({"model": openai_model, "input": user_payload, "temperature": 0.3}).encode("utf-8")
                        req = urllib.request.Request(url=url, method="POST", data=body, headers=headers)
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            resp_json = json.loads(resp.read().decode("utf-8"))
                            ai_text = resp_json.get("output_text") or (resp_json.get("choices") or [{}])[0].get("message", {}).get("content")
                            ai_provider = "OpenAI"
                            ai_model = openai_model
                except Exception as oe:
                    print(f"OpenAI fallback failed: {oe}")

            # Selected filters
            selected_categories = {t["category"]["id"]: t["category"]["name"] for t in txs if t.get("category", {}).get("selected")}
            selected_wallets = {t["wallet"]["id"]: t["wallet"]["name"] for t in txs if t.get("wallet", {}).get("selected")}

            # Totals
            def sum_amount(items):
                return sum(float(x.get("amount", 0) or 0) for x in items)

            # Total expense in selected category (sum across all selected categories)
            cat_expense_total = sum_amount([t for t in txs if t.get("type") == "expense" and t.get("category", {}).get("selected")])

            # Wallet totals
            wallet_income_total = sum_amount([t for t in txs if t.get("type") == "income" and t.get("wallet", {}).get("selected")])
            wallet_expense_total = sum_amount([t for t in txs if t.get("type") == "expense" and t.get("wallet", {}).get("selected")])
            wallet_net = wallet_income_total - wallet_expense_total

            # Overlap (selected in both category and wallet)
            overlap_txs = [t for t in txs if t.get("wallet", {}).get("selected") and t.get("category", {}).get("selected")]
            overlap_total = sum_amount(overlap_txs)

            # Compose text (following prompt tone)
            cat_names = ", ".join(filter(None, set(selected_categories.values()))) or "(tidak ada kategori terpilih)"
            wal_names = ", ".join(filter(None, set(selected_wallets.values()))) or "(tidak ada wallet terpilih)"

            insights = []
            if wallet_expense_total > wallet_income_total * 0.9 and wallet_expense_total > 0:
                insights.append("Pengeluaran dari wallet terpilih cukup tinggi dibanding pemasukan — pertimbangkan batas anggaran mingguan.")
            if cat_expense_total > 0 and wallet_expense_total > 0:
                share = (cat_expense_total / wallet_expense_total) * 100.0
                if share >= 30:
                    insights.append(f"Kategori terpilih menyumbang sekitar {share:.1f}% dari pengeluaran wallet — ini sinyal untuk dikendalikan.")
            if not insights:
                insights.append("Data terlihat sehat. Lanjutkan kebiasaan baik dan sisihkan sebagian pemasukan untuk tabungan.")

            advice = [
                "Tetapkan budget bulanan untuk kategori utama dan aktifkan pengingat.",
                "Alokasikan sebagian pemasukan otomatis ke tabungan/goal.",
                "Gunakan satu wallet untuk belanja harian agar pemantauan lebih mudah."
            ]

            if not ai_text:
                ai_text = (
                    "## Rangkuman Data Terpilih\n\n"
                    f"- **Kategori terpilih**: {cat_names}.\n"
                    f"- **Wallet terpilih**: {wal_names}.\n"
                    f"- **Total pengeluaran kategori terpilih**: Rp {cat_expense_total:,.0f}.\n"
                    f"- **Wallet (terpilih)** — pemasukan: Rp {wallet_income_total:,.0f}, pengeluaran: Rp {wallet_expense_total:,.0f}, neto: Rp {wallet_net:,.0f}.\n"
                    f"- **Transaksi overlap (kategori & wallet terpilih)**: Rp {overlap_total:,.0f}.\n\n"
                    "## Insight & Saran\n\n"
                    f"- Insight: {insights[0]}\n"
                    f"- Saran: {advice[0]}\n\n"
                    "_Tetap disiplin agar keuangan makin kuat!_"
                )
                ai_provider = ai_provider or "Local"
                ai_model = ai_model or "rule-based"

            # Append AI message to conversation
            try:
                repo.append_message(user_id, {"role": "ai", "text": ai_text, "source": "prompt_advicer", "created_at": int(datetime.now().timestamp())})
            except Exception:
                pass
            # Clear json_banks.json after processing
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write("{}")
            except Exception as _e:
                print(f"Error clearing json_banks.json after read: {_e}")
        except Exception as e:
            print(f"Error building AI analysis text: {e}")
            ai_text = None

        return jsonify({"ok": True, "conversation": conversation, "ai_text": ai_text, "ai_provider": ai_provider, "ai_model": ai_model})
    except Exception as e:
        print(f"Error in api_ai_chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/chat", methods=["GET"])
def api_ai_chat_get():
    """Return current user's conversation document if exists."""
    try:
        user_id = session.get("user_id", "demo_user")
        repo = AiChatRepository()
        conv = repo.get_by_user_id(user_id)
        return jsonify({"ok": True, "conversation": conv})
    except Exception as e:
        print(f"Error in api_ai_chat_get: {e}")
        return jsonify({"error": str(e)}), 500
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
        
        # Get the wallet_id for balance recalculation
        wallet_id = body.get("wallet_id")
        if not wallet_id:
            # If wallet_id not in body, get it from the existing transaction
            existing_tx = repo.get_transaction_by_id(transaction_id, user_id)
            wallet_id = existing_tx.get("wallet_id")
        
        if wallet_id: 
            balance_result = repo.recalculate_wallet_balances(user_id, wallet_id)
              
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

@app.route("/api/transactions/recalculate-balances", methods=["POST"])
def recalculate_balances():
    """Recalculate balances for a specific wallet after transaction edit"""
    try:
        user_id = session.get("user_id", "demo_user")
        data = request.get_json(force=True) or {}
        wallet_id = data.get("wallet_id")
        
        if not wallet_id:
            return jsonify({"error": "wallet_id is required"}), 400
        
        repo = TransactionRepository()
        result = repo.recalculate_wallet_balances(user_id, wallet_id)
        
        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify({"error": result.get("error", "Balance recalculation failed")}), 500
    except Exception as e:
        print(f"Error in recalculate_balances: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/transactions/transfer", methods=["POST"])
def create_transfer_transaction():
    """Create a transfer transaction between wallets"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        # Validate required fields
        required_fields = ['from_wallet_id', 'to_wallet_id', 'amount']
        for field in required_fields:
            if field not in body:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        from_wallet_id = body['from_wallet_id']
        to_wallet_id = body['to_wallet_id']
        amount = float(body['amount'])
        admin_fee = float(body.get('admin_fee', 0))
        note = body.get('note', '')
        
        # Validate wallets are different
        if from_wallet_id == to_wallet_id:
            return jsonify({"error": "Source and destination wallets cannot be the same"}), 400
        
        # Validate amount
        if amount <= 0:
            return jsonify({"error": "Transfer amount must be greater than 0"}), 400
        
        if admin_fee < 0:
            return jsonify({"error": "Admin fee cannot be negative"}), 400
        
        # Validate wallet ownership
        wallet_repo = WalletRepository()
        from_wallet = wallet_repo.get_wallet_by_id(from_wallet_id, user_id)
        to_wallet = wallet_repo.get_wallet_by_id(to_wallet_id, user_id)

        if not from_wallet:
            return jsonify({"error": "Source wallet not found or access denied"}), 404
        
        if not to_wallet:
            return jsonify({"error": "Destination wallet not found or access denied"}), 404
        
        # Check sufficient balance with detailed information
        current_balance = float(from_wallet.get("actual_balance", 0))
        total_deducted = amount + admin_fee
        
        if total_deducted > current_balance:
            error_details = {
                "error": "Insufficient balance for transfer",
                "details": {
                    "from_wallet": from_wallet.get("name", "Unknown"),
                    "to_wallet": to_wallet.get("name", "Unknown"),
                    "current_balance": current_balance,
                    "transfer_amount": amount,
                    "admin_fee": admin_fee,
                    "total_required": total_deducted,
                    "shortfall": total_deducted - current_balance
                },
                "message": f"Saldo tidak mencukupi untuk transfer. Saldo tersedia: Rp {current_balance:,.0f}, Total yang dibutuhkan: Rp {total_deducted:,.0f} (Transfer: Rp {amount:,.0f} + Admin Fee: Rp {admin_fee:,.0f})"
            }
            return jsonify(error_details), 400
        
        # Create transfer transaction data
        import time
        current_time = int(time.time())
        
        # Main transfer transaction (income to destination wallet)
        to_wallet_balance_before = float(to_wallet.get("actual_balance", 0))
        to_wallet_balance_after = to_wallet_balance_before + amount
        
        transfer_data = {
            "user_id": user_id,
            "wallet_id": to_wallet_id,
            "type": "income",
            "amount": amount,
            "note": note or f"Transfer from {from_wallet.get('name', 'Unknown')}",
            "timestamp": current_time,
            "created_at": current_time,
            "category_id": "transfer",  # You may want to add this category
            "scope_id": None,
            "tags": ["transfer"],
            "is_transfer": True,
            "from_wallet_id": from_wallet_id,
            "to_wallet_id": to_wallet_id,
            "transfer_amount": amount,
            "admin_fee": admin_fee,
            "balance_before": to_wallet_balance_before,
            "balance_after": to_wallet_balance_after
        }
        
        # Create expense transaction for source wallet (if amount > 0)
        from_wallet_balance_before = current_balance
        from_wallet_balance_after = current_balance - amount
        
        expense_data = {
            "user_id": user_id,
            "wallet_id": from_wallet_id,
            "type": "expense",
            "amount": amount,
            "note": note or f"Transfer to {to_wallet.get('name', 'Unknown')}",
            "timestamp": current_time,
            "created_at": current_time,
            "category_id": "transfer",
            "scope_id": None,
            "tags": ["transfer"],
            "is_transfer": True,
            "from_wallet_id": from_wallet_id,
            "to_wallet_id": to_wallet_id,
            "transfer_amount": amount,
            "admin_fee": admin_fee,
            "balance_before": from_wallet_balance_before,
            "balance_after": from_wallet_balance_after
        }
        
        # Create admin fee transaction (if fee > 0)
        fee_data = None
        if admin_fee > 0:
            
            # Fee balance should be calculated AFTER the main transfer amount is deducted
            # Main transfer deducts 'amount', so fee starts from that reduced balance
            fee_balance_before = from_wallet_balance_after  # Balance after main transfer
            fee_balance_after = fee_balance_before - admin_fee  # Balance after fee deduction
            fee_timestamp = current_time + 2
            
            fee_data = {
                "user_id": user_id,
                "wallet_id": from_wallet_id,
                "type": "expense",
                "amount": admin_fee,
                "note": f"Transfer fee for transfer to {to_wallet.get('name', 'Unknown')}",
                "timestamp": fee_timestamp,
                "created_at": fee_timestamp,
                "category_id": "transfer_fee",  # You may want to add this category
                "scope_id": None,
                "tags": ["transfer", "fee"],
                "is_transfer_fee": True,
                "from_wallet_id": from_wallet_id,
                "to_wallet_id": to_wallet_id,
                "transfer_amount": amount,
                "admin_fee": admin_fee,
                "balance_before": fee_balance_before,  # Balance after main transfer
                "balance_after": fee_balance_after     # Balance after fee deduction
            }
            
        # Create transactions
        transaction_repo = TransactionRepository()
        
        # For transfers, we need to handle balance updates manually to avoid double updates
        # First, disable automatic balance updates by setting a flag
        transfer_data["skip_balance_update"] = True
        expense_data["skip_balance_update"] = True
        if fee_data:
            fee_data["skip_balance_update"] = True
        
        # Insert main transfer transaction (income to destination)
        transfer_id = transaction_repo.insert_one(transfer_data)
        if not transfer_id:
            return jsonify({"error": "Failed to create transfer transaction"}), 500
        
        # Insert expense transaction (expense from source)
        expense_id = transaction_repo.insert_one(expense_data)
        if not expense_id:
            return jsonify({"error": "Failed to create expense transaction"}), 500
        
        # Insert fee transaction if applicable
        fee_id = None
        if fee_data:
            fee_id = transaction_repo.insert_one(fee_data)
            if not fee_id:
                return jsonify({"error": "Failed to create fee transaction"}), 500
        
        # Now manually update wallet balances for the complete transfer
        # Update destination wallet (add amount)
        new_to_balance = float(to_wallet.get("actual_balance", 0)) + amount
        success_to = wallet_repo.update_wallet_balance(to_wallet_id, user_id, new_to_balance)
        
        # Update source wallet (subtract amount + fee)
        new_from_balance = current_balance - total_deducted
        success_from = wallet_repo.update_wallet_balance(from_wallet_id, user_id, new_from_balance)
        
        if not success_to or not success_from:
            return jsonify({"error": "Transfer created but failed to update wallet balances"}), 500
        
        return jsonify({
            "message": "Transfer completed successfully",
            "transfer_id": transfer_id,
            "expense_id": expense_id,
            "fee_id": fee_id,
            "amount": amount,
            "admin_fee": admin_fee,
            "from_wallet": from_wallet.get("name"),
            "to_wallet": to_wallet.get("name")
        }), 201
        
    except Exception as e:
        print(f"Error in create_transfer_transaction: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/transactions/modified-balance", methods=["POST"])
def create_modified_balance_transaction():
    """Create a transaction for balance adjustment"""
    try:
        user_id = session.get("user_id", "demo_user")
        body = request.get_json(force=True) or {}
        
        # Validate required fields
        required_fields = ['wallet_id', 'new_balance', 'current_balance', 'difference']
        for field in required_fields:
            if field not in body:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        wallet_id = body['wallet_id']
        new_balance = float(body['new_balance'])
        current_balance = float(body['current_balance'])
        difference = float(body['difference'])
        
        # Determine transaction type based on difference
        if difference > 0:
            transaction_type = 'income'  # Balance increased
        else:
            transaction_type = 'expense'  # Balance decreased
        
        note = body.get('note', 'Balance adjustment')
        
        # Validate wallet ownership
        wallet_repo = WalletRepository()
        wallet = wallet_repo.get_wallet_by_id(wallet_id, user_id)
        if not wallet:
            return jsonify({"error": "Wallet not found or access denied"}), 404
        
        # Validate difference matches calculation
        expected_difference = new_balance - current_balance
        if abs(difference - expected_difference) > 0.01:  # Allow small floating point differences
            return jsonify({"error": "Difference calculation mismatch"}), 400
        
        # Create transaction data
        import time
        transaction_data = {
            "user_id": user_id,
            "wallet_id": wallet_id,
            "type": transaction_type,
            "amount": abs(difference),  # Always positive amount
            "note": note,
            "timestamp": int(time.time()),
            "created_at": int(time.time()),
            "category_id": "balance_adjustment",  # Use the default balance adjustment category
            "scope_id": None,  # No scope for balance adjustments
            "tags": [],  # Empty tags as requested
            "is_balance_adjustment": True,  # Flag to identify balance adjustment transactions
            "balance_before": current_balance,
            "balance_after": new_balance
        }
        
        # Create transaction
        transaction_repo = TransactionRepository()
        transaction_id = transaction_repo.insert_one(transaction_data)
        
        if not transaction_id:
            return jsonify({"error": "Failed to create transaction"}), 500
        
        # Update wallet balance
        success = wallet_repo.update_wallet_balance(wallet_id, user_id, new_balance)
        
        if not success:
            # If wallet update fails, we should ideally rollback the transaction
            # For now, just return an error
            return jsonify({"error": "Transaction created but failed to update wallet balance"}), 500
        
        return jsonify({
            "message": "Balance updated successfully",
            "transaction_id": transaction_id,
            "new_balance": new_balance,
            "difference": difference
        }), 201
        
    except Exception as e:
        print(f"Error in create_modified_balance_transaction: {e}")
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
    # Check authentication
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    try:
        user_id = session.get("user_id")
        
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
    print("📍 Application will be available at: http://localhost:5006")
    print("💡 Press Ctrl+C to stop the application")
    try:
        app.run(debug=True, host="0.0.0.0", port=5006)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

