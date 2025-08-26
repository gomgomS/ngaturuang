from flask import Blueprint, jsonify, request, session

from mm.repositories.goals import GoalRepository


bp = Blueprint("goals", __name__)


@bp.get("/")
def list_goals():
    user_id = session.get("user_id", "demo_user")
    repo = GoalRepository()
    data = repo.list_by_user(user_id)
    return jsonify(data)


@bp.post("/")
def create_goal():
    body = request.get_json(force=True) or {}
    body["user_id"] = session.get("user_id", "demo_user")
    repo = GoalRepository()
    _id = repo.insert_one(body)
    return jsonify({"_id": _id}), 201


@bp.delete("/<goal_id>")
def delete_goal(goal_id: str):
    repo = GoalRepository()
    ok = repo.delete_by_id(goal_id)
    return ("", 204) if ok else ("", 404)


