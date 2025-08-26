from flask import Blueprint, jsonify


bp = Blueprint("ai", __name__)


@bp.get("/placeholder")
def placeholder():
    # Static placeholder; integrate LLM later
    return jsonify({
        "summary_text": "Pengeluaran kamu bulan ini naik 12% terutama di 'Ngopi' dan 'Hiburan'.",
        "kpis": {
            "this_month_income": 10000000,
            "this_month_expense": 7200000,
            "net_cashflow": 2800000,
            "top_categories_expense": [
                {"category_id": "cat_ngopi", "name": "Ngopi", "amount": 1200000},
                {"category_id": "cat_hiburan", "name": "Hiburan", "amount": 900000}
            ],
            "top_scopes_expense": [
                {"scope_id": "scope_personal", "name": "Personal", "amount": 4800000}
            ]
        },
        "insights": [
            "Ngopi melebihi rata-rata 3 bulan terakhir (+30%)."
        ],
        "recommendations": [
            {"action": "Set budget ngopi Rp800k/bulan", "estimated_impact": 400000, "timeframe": "next_month"},
            {"action": "Auto-transfer 10% income ke goal 1 tahun", "estimated_impact": 1000000, "timeframe": "monthly_auto"}
        ],
        "goals_progress": [
            {"goal_id": "g1", "title": "Tabungan 1 tahun 50jt", "progress_pct": 42, "on_track": False, "eta_months": 15}
        ]
    })


