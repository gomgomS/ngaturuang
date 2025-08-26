from flask import Blueprint, jsonify, request, session
from mm.repositories.scopes import ScopeRepository

bp = Blueprint("scopes", __name__)

@bp.get("/")
def list_scopes():
    """Get semua scope untuk user"""
    user_id = session.get("user_id", "demo_user")
    repo = ScopeRepository()
    data = repo.list_by_user(user_id)
    return jsonify(data)

@bp.post("/")
def create_scope():
    """Create scope baru"""
    user_id = session.get("user_id", "demo_user")
    body = request.get_json(force=True) or {}
    
    # Tambah user_id ke data
    body["user_id"] = user_id
    
    repo = ScopeRepository()
    _id = repo.insert_one(body)
    return jsonify({"_id": _id}), 201

@bp.get("/<scope_id>")
def get_scope(scope_id):
    """Get single scope"""
    user_id = session.get("user_id", "demo_user")
    repo = ScopeRepository()
    
    scope = repo.find_one({"_id": scope_id, "user_id": user_id})
    if not scope:
        return jsonify({"error": "Scope not found"}), 404
    
    return jsonify(scope)

@bp.put("/<scope_id>")
def update_scope(scope_id):
    """Update scope"""
    user_id = session.get("user_id", "demo_user")
    body = request.get_json(force=True) or {}
    
    repo = ScopeRepository()
    success = repo.update_scope(scope_id, user_id, body)
    
    if not success:
        return jsonify({"error": "Scope not found or update failed"}), 404
    
    return jsonify({"message": "Scope updated successfully"})

@bp.delete("/<scope_id>")
def delete_scope(scope_id):
    """Delete scope"""
    user_id = session.get("user_id", "demo_user")
    repo = ScopeRepository()
    
    success = repo.delete_scope(scope_id, user_id)
    
    if not success:
        return jsonify({"error": "Scope not found or delete failed"}), 404
    
    return jsonify({"message": "Scope deleted successfully"})


