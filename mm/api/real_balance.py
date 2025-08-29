from flask import Blueprint, jsonify, request, session
from mm.repositories.real_balance import RealBalanceRepository

bp = Blueprint("real_balance", __name__)

@bp.get("/")
def list_real_balances():
    """Get semua real balance untuk user"""
    user_id = session.get("user_id", "demo_user")
    repo = RealBalanceRepository()
    data = repo.get_user_balances(user_id)
    return jsonify(data)

@bp.get("/<wallet_id>")
def get_wallet_real_balance(wallet_id):
    """Get real balance untuk wallet tertentu"""
    user_id = session.get("user_id", "demo_user")
    repo = RealBalanceRepository()
    
    balance = repo.get_latest_balance(user_id, wallet_id)
    if not balance:
        return jsonify({"balance_amount": 0, "note": "", "balance_date": None}), 200
    
    return jsonify(balance)

@bp.post("/<wallet_id>")
def create_real_balance(wallet_id):
    """Create real balance baru untuk wallet"""
    user_id = session.get("user_id", "demo_user")
    body = request.get_json(force=True) or {}
    
    # Validasi input
    if "balance_amount" not in body:
        return jsonify({"error": "balance_amount is required"}), 400
    
    try:
        balance_amount = float(body["balance_amount"])
        if balance_amount < 0:
            return jsonify({"error": "balance_amount cannot be negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "balance_amount must be a valid number"}), 400
    
    # Prepare balance data
    balance_data = {
        "balance_amount": balance_amount,
        "currency": body.get("currency", "IDR"),
        "note": body.get("note", "")
    }
    
    repo = RealBalanceRepository()
    _id = repo.create_balance(user_id, wallet_id, balance_data)
    
    if not _id:
        return jsonify({"error": "Failed to create balance"}), 500
    
    return jsonify({
        "message": "Real balance created successfully",
        "balance_id": _id,
        "balance_amount": balance_amount
    }), 201

@bp.put("/<wallet_id>")
def update_real_balance(wallet_id):
    """Update real balance untuk wallet (create new one)"""
    user_id = session.get("user_id", "demo_user")
    body = request.get_json(force=True) or {}
    
    # Validasi input
    if "balance_amount" not in body:
        return jsonify({"error": "balance_amount is required"}), 400
    
    try:
        balance_amount = float(body["balance_amount"])
        if balance_amount < 0:
            return jsonify({"error": "balance_amount cannot be negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "balance_amount must be a valid number"}), 400
    
    # Prepare balance data
    balance_data = {
        "balance_amount": balance_amount,
        "currency": body.get("currency", "IDR"),
        "note": body.get("note", "")
    }
    
    repo = RealBalanceRepository()
    _id = repo.create_balance(user_id, wallet_id, balance_data)
    
    if not _id:
        return jsonify({"error": "Failed to update balance"}), 500
    
    return jsonify({
        "message": "Real balance updated successfully",
        "balance_id": _id,
        "balance_amount": balance_amount
    })

@bp.get("/<wallet_id>/history")
def get_wallet_balance_history(wallet_id):
    """Get history balance untuk wallet tertentu"""
    user_id = session.get("user_id", "demo_user")
    limit = request.args.get("limit", 10, type=int)
    
    repo = RealBalanceRepository()
    history = repo.get_balance_history(user_id, wallet_id, limit)
    
    return jsonify(history)
