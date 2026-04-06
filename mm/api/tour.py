from flask import Blueprint, jsonify, request, session
from mm.repositories.users import UserRepository

bp = Blueprint("tour", __name__)


@bp.get("/tour/status")
def get_tour_status():
    """Get the current tour completion status for the logged-in user"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    users = UserRepository()
    user = users.find_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "tour_completed": user.get("tour_completed", False),
        "user_id": user_id
    })


@bp.post("/tour/complete")
def complete_tour():
    """Mark the tour as completed for the logged-in user"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    users = UserRepository()
    result = users.update_one(
        {"_id": user_id},
        {"$set": {"tour_completed": True}}
    )
    
    if result.modified_count > 0:
        return jsonify({"message": "Tour marked as completed", "tour_completed": True})
    else:
        return jsonify({"error": "Failed to update tour status"}), 500


@bp.post("/tour/reset")
def reset_tour():
    """Reset the tour status for the logged-in user (for testing purposes)"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    users = UserRepository()
    result = users.update_one(
        {"_id": user_id},
        {"$set": {"tour_completed": False}}
    )
    
    if result.modified_count > 0:
        return jsonify({"message": "Tour status reset", "tour_completed": False})
    else:
        return jsonify({"error": "Failed to reset tour status"}), 500
