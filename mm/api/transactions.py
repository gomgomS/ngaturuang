from flask import Blueprint, jsonify, request, session
from mm.repositories.transactions import TransactionRepository

bp = Blueprint("transactions", __name__)

@bp.get("/")
def list_transactions():
    user_id = session.get("user_id", "demo_user")
    limit = int(request.args.get("limit", "200"))
    scope_id = request.args.get("scope_id") or None
    
    repo = TransactionRepository()
    
    # Query sederhana langsung dari MongoDB
    query = {"user_id": user_id}
    if scope_id:
        query["scope_id"] = scope_id
    
    data = repo.find_many(query, limit=limit, sort=[("timestamp", -1)])
    return jsonify(data)

@bp.post("/")
def create_transaction():
    body = request.get_json(force=True) or {}
    body["user_id"] = session.get("user_id", "demo_user")
    
    # Tambah timestamp sederhana
    import time
    body["timestamp"] = int(time.time())
    body["created_at"] = body["timestamp"]
    
    repo = TransactionRepository()
    _id = repo.insert_one(body)
    return jsonify({"_id": _id}), 201

@bp.get("/<transaction_id>")
def get_transaction(transaction_id):
    user_id = session.get("user_id", "demo_user")
    repo = TransactionRepository()
    
    transaction = repo.get_transaction_by_id(transaction_id, user_id)
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404
    
    return jsonify(transaction)

@bp.put("/<transaction_id>")
def update_transaction(transaction_id):
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
        # Trigger balance recalculation for the wallet
        print(f"🔄 [API] Triggering balance recalculation for wallet: {wallet_id}")
        balance_result = repo.recalculate_wallet_balances(user_id, wallet_id)
        
        if balance_result.get("success"):
            print(f"✅ [API] Balance recalculation successful: {balance_result.get('message')}")
        else:
            print(f"❌ [API] Balance recalculation failed: {balance_result.get('error')}")
    
    return jsonify({"message": "Transaction updated successfully"})

@bp.delete("/<transaction_id>")
def delete_transaction(transaction_id):
    user_id = session.get("user_id", "demo_user")
    repo = TransactionRepository()
    
    success = repo.delete_transaction(transaction_id, user_id)
    
    if not success:
        return jsonify({"error": "Transaction not found or delete failed"}), 404
    
    return jsonify({"message": "Transaction deleted successfully"})

@bp.post("/recalculate-balances")
def recalculate_balances():
    """Recalculate balances for a specific wallet after transaction edit"""
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


