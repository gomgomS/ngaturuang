"""Background worker for wallet balance updates.

Transactions are saved immediately; wallet saldo and balance_before/after
fields are updated asynchronously via a single FIFO queue so the API
response is not blocked by read-modify-write balance logic.
"""
from __future__ import annotations

import queue
import threading
import time
import traceback
from typing import Any, Dict, List, Optional

from bson import ObjectId


_job_queue: queue.Queue = queue.Queue()
_worker_thread: Optional[threading.Thread] = None
_worker_lock = threading.Lock()


def _tx_delta(transaction_type: str, amount: float) -> float:
    if transaction_type == "income":
        return amount
    if transaction_type == "expense":
        return -amount
    return 0.0


def _ensure_worker() -> None:
    global _worker_thread
    with _worker_lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(
                target=_worker_loop,
                name="wallet-balance-worker",
                daemon=True,
            )
            _worker_thread.start()


def start_wallet_balance_worker() -> None:
    """Start the background worker thread (idempotent)."""
    _ensure_worker()


def enqueue_wallet_balance_job(job: Dict[str, Any]) -> None:
    _ensure_worker()
    _job_queue.put(job)


def enqueue_apply_transaction(
    transaction_id: str,
    wallet_id: str,
    user_id: str,
    transaction_type: str,
    amount: float,
) -> None:
    enqueue_wallet_balance_job({
        "type": "apply",
        "transaction_id": transaction_id,
        "wallet_id": wallet_id,
        "user_id": user_id,
        "transaction_type": transaction_type,
        "amount": float(amount),
    })


def enqueue_revert_transaction(
    wallet_id: str,
    user_id: str,
    transaction_type: str,
    amount: float,
) -> None:
    enqueue_wallet_balance_job({
        "type": "revert",
        "wallet_id": wallet_id,
        "user_id": user_id,
        "transaction_type": transaction_type,
        "amount": float(amount),
    })


def enqueue_update_transaction_balances(
    transaction_id: str,
    user_id: str,
    old_wallet_id: str,
    old_type: str,
    old_amount: float,
    new_wallet_id: str,
    new_type: str,
    new_amount: float,
) -> None:
    enqueue_wallet_balance_job({
        "type": "update",
        "transaction_id": transaction_id,
        "user_id": user_id,
        "old_wallet_id": old_wallet_id,
        "old_type": old_type,
        "old_amount": float(old_amount),
        "new_wallet_id": new_wallet_id,
        "new_type": new_type,
        "new_amount": float(new_amount),
    })


def enqueue_set_wallet_balance(
    wallet_id: str,
    user_id: str,
    new_balance: float,
    transaction_id: Optional[str] = None,
) -> None:
    enqueue_wallet_balance_job({
        "type": "set",
        "wallet_id": wallet_id,
        "user_id": user_id,
        "new_balance": float(new_balance),
        "transaction_id": transaction_id,
    })


def enqueue_multi_adjust(steps: List[Dict[str, Any]]) -> None:
    """Apply multiple wallet deltas in order (e.g. transfers)."""
    enqueue_wallet_balance_job({
        "type": "multi_adjust",
        "steps": steps,
    })


def enqueue_recalculate_wallet(user_id: str, wallet_id: str) -> None:
    enqueue_wallet_balance_job({
        "type": "recalculate",
        "user_id": user_id,
        "wallet_id": wallet_id,
    })


def _worker_loop() -> None:
    while True:
        job = _job_queue.get()
        try:
            _process_job(job)
        except Exception as exc:
            print(f"❌ [WALLET_WORKER] Job failed ({job.get('type')}): {exc}")
            traceback.print_exc()
        finally:
            _job_queue.task_done()


def _process_job(job: Dict[str, Any]) -> None:
    job_type = job.get("type")
    if job_type == "apply":
        _apply_transaction(job)
    elif job_type == "revert":
        _revert_transaction(job)
    elif job_type == "update":
        _update_transaction_balances(job)
    elif job_type == "set":
        _set_wallet_balance(job)
    elif job_type == "multi_adjust":
        _multi_adjust(job)
    elif job_type == "recalculate":
        _recalculate_wallet(job)
    else:
        print(f"⚠️ [WALLET_WORKER] Unknown job type: {job_type}")


def _apply_transaction(job: Dict[str, Any]) -> None:
    from mm.repositories.transactions import TransactionRepository
    from mm.repositories.wallets import WalletRepository

    tx_id = job["transaction_id"]
    wallet_id = job["wallet_id"]
    user_id = job["user_id"]
    tx_type = job["transaction_type"]
    amount = job["amount"]

    wallet_repo = WalletRepository()
    balance_before = wallet_repo.get_wallet_balance(wallet_id, user_id)
    if balance_before is None:
        return

    delta = _tx_delta(tx_type, amount)
    balance_after = wallet_repo.adjust_wallet_balance(wallet_id, user_id, delta)
    if balance_after is None:
        return

    TransactionRepository().collection.update_one(
        {"_id": ObjectId(tx_id), "user_id": user_id},
        {"$set": {
            "balance_before": balance_before,
            "balance_after": balance_after,
            "balance_sync": "synced",
            "updated_at": int(time.time()),
        }},
    )


def _revert_transaction(job: Dict[str, Any]) -> None:
    from mm.repositories.wallets import WalletRepository

    wallet_repo = WalletRepository()
    delta = -_tx_delta(job["transaction_type"], job["amount"])
    wallet_repo.adjust_wallet_balance(job["wallet_id"], job["user_id"], delta)


def _update_transaction_balances(job: Dict[str, Any]) -> None:
    from mm.repositories.transactions import TransactionRepository
    from mm.repositories.wallets import WalletRepository

    wallet_repo = WalletRepository()
    tx_repo = TransactionRepository()
    user_id = job["user_id"]

    old_wallet = job.get("old_wallet_id")
    old_type = job.get("old_type")
    old_amount = job.get("old_amount", 0)
    new_wallet = job.get("new_wallet_id")
    new_type = job.get("new_type")
    new_amount = job.get("new_amount", 0)

    if old_wallet and old_type and old_amount > 0:
        wallet_repo.adjust_wallet_balance(
            old_wallet, user_id, -_tx_delta(old_type, old_amount)
        )

    balance_before = wallet_repo.get_wallet_balance(new_wallet, user_id)
    if balance_before is None:
        return

    balance_after = wallet_repo.adjust_wallet_balance(
        new_wallet, user_id, _tx_delta(new_type, new_amount)
    )
    if balance_after is None:
        return

    tx_repo.collection.update_one(
        {"_id": ObjectId(job["transaction_id"]), "user_id": user_id},
        {"$set": {
            "balance_before": balance_before,
            "balance_after": balance_after,
            "balance_sync": "synced",
            "updated_at": int(time.time()),
        }},
    )


def _set_wallet_balance(job: Dict[str, Any]) -> None:
    from mm.repositories.transactions import TransactionRepository
    from mm.repositories.wallets import WalletRepository

    wallet_repo = WalletRepository()
    success = wallet_repo.set_wallet_balance(
        job["wallet_id"], job["user_id"], job["new_balance"]
    )
    if not success:
        return

    tx_id = job.get("transaction_id")
    if tx_id:
        TransactionRepository().collection.update_one(
            {"_id": ObjectId(tx_id), "user_id": job["user_id"]},
            {"$set": {
                "balance_sync": "synced",
                "updated_at": int(time.time()),
            }},
        )


def _multi_adjust(job: Dict[str, Any]) -> None:
    from mm.repositories.transactions import TransactionRepository
    from mm.repositories.wallets import WalletRepository

    wallet_repo = WalletRepository()
    tx_repo = TransactionRepository()

    for step in job.get("steps", []):
        wallet_id = step["wallet_id"]
        user_id = step["user_id"]
        delta = float(step["delta"])
        tx_id = step.get("transaction_id")

        balance_before = wallet_repo.get_wallet_balance(wallet_id, user_id)
        balance_after = wallet_repo.adjust_wallet_balance(wallet_id, user_id, delta)

        if tx_id and balance_before is not None and balance_after is not None:
            tx_repo.collection.update_one(
                {"_id": ObjectId(tx_id), "user_id": user_id},
                {"$set": {
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                    "balance_sync": "synced",
                    "updated_at": int(time.time()),
                }},
            )


def _recalculate_wallet(job: Dict[str, Any]) -> None:
    from mm.repositories.transactions import TransactionRepository

    TransactionRepository().recalculate_wallet_balances(
        job["user_id"], job["wallet_id"]
    )
