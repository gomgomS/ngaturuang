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
    
    return jsonify({"message": "Transaction updated successfully"})

@bp.delete("/<transaction_id>")
def delete_transaction(transaction_id):
    user_id = session.get("user_id", "demo_user")
    repo = TransactionRepository()
    
    success = repo.delete_transaction(transaction_id, user_id)
    
    if not success:
        return jsonify({"error": "Transaction not found or delete failed"}), 404
    
    return jsonify({"message": "Transaction deleted successfully"})


