import time
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request, session

from config import get_collection


bp = Blueprint("reports", __name__)


@bp.get("/summary")
def summary():
    user_id = session.get("user_id", "demo_user")
    period = request.args.get("period", "monthly")  # monthly | yearly

    coll = get_collection("transactions")

    now = int(time.time())
    if period == "yearly":
        start = int(datetime(datetime.utcfromtimestamp(now).year, 1, 1).timestamp())
    else:
        dt = datetime.utcfromtimestamp(now)
        start = int(datetime(dt.year, dt.month, 1).timestamp())

    pipeline = [
        {"$match": {"user_id": user_id, "timestamp": {"$gte": start}}},
        {"$group": {
            "_id": {
                "type": "$type"
            },
            "amount": {"$sum": "$amount"}
        }}
    ]
    grouped = list(coll.aggregate(pipeline))
    income = next((g["amount"] for g in grouped if g["_id"]["type"] == "income"), 0)
    expense = next((g["amount"] for g in grouped if g["_id"]["type"] == "expense"), 0)

    return jsonify({
        "period": period,
        "start": start,
        "kpis": {
            "income": income,
            "expense": expense,
            "net_cashflow": income - expense
        }
    })


@bp.get("/breakdown/category")
def breakdown_by_category():
    user_id = session.get("user_id", "demo_user")
    coll = get_collection("transactions")
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": {"category_id": "$category_id", "type": "$type"},
            "amount": {"$sum": "$amount"}
        }},
        {"$sort": {"amount": -1}}
    ]
    data = list(coll.aggregate(pipeline))
    return jsonify(data)


@bp.get("/breakdown/wallet")
def breakdown_by_wallet():
    user_id = session.get("user_id", "demo_user")
    coll = get_collection("transactions")
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": {"wallet_id": "$wallet_id", "type": "$type"},
            "amount": {"$sum": "$amount"}
        }},
        {"$sort": {"amount": -1}}
    ]
    data = list(coll.aggregate(pipeline))
    return jsonify(data)


@bp.get("/breakdown/scope")
def breakdown_by_scope():
    user_id = request.args.get("user_id", "demo_user")
    coll = get_collection("transactions")
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": {"scope_id": "$scope_id", "type": "$type"},
            "amount": {"$sum": "$amount"}
        }},
        {"$sort": {"amount": -1}}
    ]
    data = list(coll.aggregate(pipeline))
    return jsonify(data)


