from flask import Blueprint, jsonify, request, session
from mm.repositories.wallets import WalletRepository

bp = Blueprint("wallets", __name__)

@bp.get("/")
def list_wallets():
    """Get semua saving space untuk user"""
    user_id = session.get("user_id", "demo_user")
    repo = WalletRepository()
    data = repo.list_by_user(user_id)
    return jsonify(data)

@bp.post("/")
def create_wallet():
    """Create saving space baru"""
    user_id = session.get("user_id", "demo_user")
    body = request.get_json(force=True) or {}
    
    # Tambah user_id ke data
    body["user_id"] = user_id
    
    # Set default type jika tidak ada
    if "type" not in body:
        body["type"] = "bank"
    
    repo = WalletRepository()
    _id = repo.insert_one(body)
    return jsonify({"_id": _id}), 201

@bp.get("/<wallet_id>")
def get_wallet(wallet_id):
    """Get single saving space"""
    user_id = session.get("user_id", "demo_user")
    repo = WalletRepository()
    
    wallet = repo.find_one({"_id": wallet_id, "user_id": user_id})
    if not wallet:
        return jsonify({"error": "Saving space not found"}), 404
    
    return jsonify(wallet)

@bp.put("/<wallet_id>")
def update_wallet(wallet_id):
    """Update saving space"""
    user_id = session.get("user_id", "demo_user")
    body = request.get_json(force=True) or {}
    
    repo = WalletRepository()
    success = repo.update_wallet(wallet_id, user_id, body)
    
    if not success:
        return jsonify({"error": "Saving space not found or update failed"}), 404
    
    return jsonify({"message": "Saving space updated successfully"})

@bp.delete("/<wallet_id>")
def delete_wallet(wallet_id):
    """Delete saving space"""
    user_id = session.get("user_id", "demo_user")
    repo = WalletRepository()
    
    success = repo.delete_wallet(wallet_id, user_id)
    
    if not success:
        return jsonify({"error": "Saving space not found or delete failed"}), 404
    
    return jsonify({"message": "Saving space deleted successfully"})


