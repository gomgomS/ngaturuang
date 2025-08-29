from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


# MongoDB logical model templates
# Embed when read-always-together and bounded; reference when reused across docs


db: Dict[str, Dict[str, Any]] = {
    "db_user": {
        "status": "",  # active | inactive | pending
        "type": "",  # personal | business | both
        "username": "",
        "name": "",
        "phone": "",
        "bank_phone_otp": "",
        "phone_otp": "",
        "phone_cc": "",
        "address": "",
        "pic": "",
        "role": "",  # owner | member | admin
        "email": "",
        "payment_method_duration": 10,
        "charge_fee_customer": True,
        "join_date": "",
        "default_bank": "",  # PAYPAL | BANK
        "paypal": "",
        "rec_timestamp": 0,
        "information": "",
        "info_color": "",
        "on_boarding_step": False,
        "activation_token": "",
        "is_email_active": False,
        "is_wms_registered": False,
        "is_kini_registered": False,
        "advance_setting": {
            "pixel_id": "",
            "pixel_access_token": "",
            "tracking_id": "",
            "container_id": "",
            "medium": "",
            "source": "",
            "title": "",
            "description": "",
            "show_logo": True,
            "show_shop_policy": False,
            "show_contact_info": False,
        },
        "site_settings": {
            "favicon": "",
            "favicon_filename": "",
            "html_title": "",
        },
        "deleted_at": None,
        "from_affiliate_registered": False,
        "gg_registered": False,
        "need_verification": True,
        "enable_chat": None,
        "chat_message": {
            "message": "",
            "phone": "",
            "country_code": "",
        },
        "kini_creds": {
            "created_at": 0,
            "expires_at": 0,
            "token": "",
        },
        "kyc_verified": False,
        "hold_status": False,
    },

    "db_user_questionaire_upload": {
        "fk_user_id": "",
        "send_email_warning": False,
        "limit_size": 20,
    },

    "db_user_auth": {
        "username": "",
        "password": "",
        "fk_user_id": "",
        "last_login": "",
        "str_last_login": "",
        "last_otp_code": "",
        "login_status": "",
        "inactive_status": False,
        "inactive_note": "",
        "lock_status": False,
        "lock_note": "",
        "lock_date": "",
        "fk_acm_id": "",
        "fk_owner_id": "",
        "deleted_at": None,
    },
}


# Domain-specific collections for money management

domain_models: Dict[str, Dict[str, Any]] = {
    # Wallets / money locations
    "wallets": {
        "user_id": "",  # reference to users._id
        "name": "",  # e.g., Bank BCA, OVO, Kas, Saham
        "type": "",  # bank | ewallet | cash | stock | mutual_fund | crypto | other
        "currency": "IDR",  # default currency
        "actual_balance": 0.0,  # actual balance dari manual balance terbaru
        "expected_balance": 0.0,  # expected balance dari kalkulasi transaksi
        "metadata": {},  # account numbers, broker code, etc
        "is_active": True,
        "created_at": 0,
        "updated_at": 0,
    },

    # Manual Balance Collection
    "manual_balances": {
        "collection": "manual_balances",
        "indexes": [
            [("user_id", 1)],
            [("wallet_id", 1)],
            [("user_id", 1), ("wallet_id", 1)],
            [("user_id", 1), ("wallet_id", 1), ("is_latest", 1)],
            [("user_id", 1), ("wallet_id", 1), ("balance_date", -1)],
            [("user_id", 1), ("wallet_id", 1), ("sequence_number", 1)],
            [("user_id", 1), ("wallet_id", 1), ("is_closed", 1)]
        ]
    },

    # High-level and granular categories
    "categories": {
        "user_id": "",
        "name": "",  # e.g., makanan, hiburan
        "type": "",  # income | expense | both
        "parent_id": None,  # for nested categories; None for root
        "is_system": False,  # system-provided vs user-defined
        "is_active": True,
        "created_at": 0,
        "updated_at": 0,
    },

    # Business scopes owned by user (Personal default + optional: bisnis A/B, startup)
    "scopes": {
        "user_id": "",
        "name": "",  # Personal | Bisnis A | Startup | Kopi Shop
        "description": "",
        "is_active": True,
        "created_at": 0,
        "updated_at": 0,
    },

    # Transactions (normalize; reference reusable entities)
    "transactions": {
        "user_id": "",
        "amount": 0.0,
        "currency": "IDR",
        "type": "",  # income | expense
        "scope_id": "",  # reference to scopes
        "wallet_id": "",  # reference to wallets
        "category_id": "",  # reference to categories (sub-category allowed)
        "fk_manual_balance_id": "",  # reference to manual_balances._id (base balance untuk transaksi ini)
        "sequence_number": 1,  # urutan transaksi berdasarkan real balance (1, 2, 3, dst)
        "tags": [],  # e.g., ["#harian", "#netflix", "#clientX"]
        "note": "",
        "timestamp": 0,  # unix seconds
        "created_at": 0,
        "updated_at": 0,
        # denormalized snapshot for fast reporting (optional but useful)
        "_snap": {
            "wallet_name": "",
            "wallet_type": "",
            "scope_name": "",
            "category_path": [],  # [parent, child]
        },
    },

    # Goals (1/5/10-year etc.)
    "goals": {
        "user_id": "",
        "title": "",
        "target_amount": 0.0,
        "currency": "IDR",
        "target_date": 0,  # unix seconds
        "scope_id": None,  # optional scope linking if business-specific
        "description": "",
        "is_active": True,
        "created_at": 0,
        "updated_at": 0,
    },

    # AI advisor placeholder results cache (to be computed later)
    "advisor_insights": {
        "user_id": "",
        "generated_at": 0,
        "timeframe": "monthly",  # monthly | quarterly | yearly
        "summary_text": "",
        "recommendations": [],  # list of strings
        "top_spend_categories": [],  # [{category_id, amount}]
        "savings_opportunities": [],  # [{hint, potential_amount}]
    },
}


# Suggested indexes (to be applied via config.ensure_indexes)
index_specs: Dict[str, List] = {
    "wallets": [(("user_id", 1), {"name": "idx_wallet_user"})],
    "manual_balances": [
        [("user_id", 1)],
        [("wallet_id", 1)],
        [("user_id", 1), ("wallet_id", 1)],
        [("user_id", 1), ("wallet_id", 1), ("is_latest", 1)],
        [("user_id", 1), ("wallet_id", 1), ("balance_date", -1)],
        [("user_id", 1), ("wallet_id", 1), ("sequence_number", 1)],
        [("user_id", 1), ("wallet_id", 1), ("is_closed", 1)]
    ],
    "categories": [
        (("user_id", 1), {"name": "idx_cat_user"}),
        (("parent_id", 1), {"name": "idx_cat_parent"}),
    ],
    "scopes": [(("user_id", 1), {"name": "idx_scope_user"})],
    "transactions": [
        (("user_id", 1), {"name": "idx_tx_user"}),
        (("timestamp", -1), {"name": "idx_tx_time"}),
        (("scope_id", 1), {"name": "idx_tx_scope"}),
        (("wallet_id", 1), {"name": "idx_tx_wallet"}),
        (("category_id", 1), {"name": "idx_tx_category"}),
        (("fk_manual_balance_id", 1), {"name": "idx_tx_manual_balance"}),
        (("sequence_number", 1), {"name": "idx_tx_sequence"}),
    ],
    "goals": [(("user_id", 1), {"name": "idx_goal_user"})],
    "advisor_insights": [(("user_id", 1), {"name": "idx_ai_user"})],
}


