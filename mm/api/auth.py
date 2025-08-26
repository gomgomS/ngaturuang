from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash

from mm.repositories.users import UserRepository


bp = Blueprint("auth", __name__)


@bp.post("/register")
def register():
    body = request.get_json(force=True) or {}
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    users = UserRepository()
    exists = users.find_by_username(username)
    if exists:
        return jsonify({"error": "username taken"}), 400

    user_id = users.insert_one({
        "username": username,
        "password": generate_password_hash(password),
        "name": username,
        "type": "both",
    })
    session["user_id"] = user_id
    return jsonify({"_id": user_id, "username": username})


@bp.post("/login")
def login():
    body = request.get_json(force=True) or {}
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    users = UserRepository()
    user = users.find_by_username(username)
    if not user or not check_password_hash(user.get("password", ""), password):
        return jsonify({"error": "invalid credentials"}), 401
    session["user_id"] = user["_id"]
    return jsonify({"_id": user["_id"], "username": username})


@bp.post("/logout")
def logout():
    session.pop("user_id", None)
    return ("", 204)


@bp.get("/me")
def me():
    user_id = session.get("user_id")
    return jsonify({"user_id": user_id})


