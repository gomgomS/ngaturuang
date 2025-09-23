from flask import Blueprint, jsonify, request, session
from mm.repositories.categories import CategoryRepository

bp = Blueprint("categories", __name__)

@bp.get("/")
def list_categories():
    """Get semua kategori untuk user"""
    user_id = session.get("user_id", "demo_user")
    repo = CategoryRepository()
    data = repo.list_by_user_with_defaults(user_id)
    return jsonify(data)

@bp.post("/")
def create_category():
    """Create kategori baru"""
    user_id = session.get("user_id", "demo_user")
    body = request.get_json(force=True) or {}
    
    # Tambah user_id ke data
    body["user_id"] = user_id
    
    repo = CategoryRepository()
    _id = repo.insert_one(body)
    return jsonify({"_id": _id}), 201

@bp.get("/<category_id>")
def get_category(category_id):
    """Get single kategori"""
    user_id = session.get("user_id", "demo_user")
    repo = CategoryRepository()
    
    category = repo.find_one({"_id": category_id, "user_id": user_id})
    if not category:
        return jsonify({"error": "Category not found"}), 404
    
    return jsonify(category)

@bp.put("/<category_id>")
def update_category(category_id):
    """Update kategori"""
    user_id = session.get("user_id", "demo_user")
    body = request.get_json(force=True) or {}
    
    repo = CategoryRepository()
    success = repo.update_category(category_id, user_id, body)
    
    if not success:
        return jsonify({"error": "Category not found or update failed"}), 404
    
    return jsonify({"message": "Category updated successfully"})

@bp.delete("/<category_id>")
def delete_category(category_id):
    """Delete kategori"""
    user_id = session.get("user_id", "demo_user")
    repo = CategoryRepository()
    
    success = repo.delete_category(category_id, user_id)
    
    if not success:
        return jsonify({"error": "Category not found or delete failed"}), 404
    
    return jsonify({"message": "Category deleted successfully"})


