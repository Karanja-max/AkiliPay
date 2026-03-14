"""
Business insights: PnL, most-sold items, and daily summaries for trends.
Uses Transaction (inflow/outflow), Sale, ManualExpense, and DailySummary.
Call from app routes within Flask app context.
"""
import json
import os
from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy import func

# #region agent log
_debug_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug-eec1d2.log")
def _dlog(msg, data, hypothesis_id, run_id="run1"):
    try:
        with open(_debug_log_path, "a", encoding="utf-8") as _f:
            _f.write(json.dumps({"sessionId": "eec1d2", "runId": run_id, "hypothesisId": hypothesis_id, "location": "business_insights.py", "message": msg, "data": data, "timestamp": __import__("time").time() * 1000}) + "\n")
    except Exception:
        pass
# #endregion

from models import (
    DailySummary,
    InventoryItem,
    ManualExpense,
    Sale,
    Transaction,
    db,
)


def generate_msme_insights(
    mpesa_transactions: List[dict],
    manual_expenses: List[dict],
    currency: str = "KES",
) -> dict:
    """
    Calculate revenue (inflows only), expenses, net profit, and an insight message.
    """
    # #region agent log
    _dlog("generate_msme_insights entry", {"len_mpesa": len(mpesa_transactions), "len_expenses": len(manual_expenses), "exp_keys": [list(e.keys()) for e in manual_expenses] if manual_expenses else []}, "H3")
    # #endregion
    total_revenue = sum(
        tx["amount"] for tx in mpesa_transactions if tx.get("type") == "inflow"
    )
    total_expenses = sum(exp["amount"] for exp in manual_expenses)
    net_profit = total_revenue - total_expenses

    if net_profit > 0:
        margin = (net_profit / total_revenue) * 100 if total_revenue > 0 else 0
        insight_message = (
            f"Good job! You made a profit of {currency} {net_profit:.2f}. "
            f"Your profit margin is {margin:.1f}%. Keep saving!"
        )
    elif net_profit < 0:
        insight_message = (
            f"Warning: You are operating at a loss of {currency} {abs(net_profit):.2f}. "
            "Review your stock expenses."
        )
    else:
        insight_message = "You broke even today. No profit, no loss."

    return {
        "revenue": total_revenue,
        "expenses": total_expenses,
        "profit": net_profit,
        "insight": insight_message,
        "currency": currency,
    }


def get_most_sold_items(
    business_id: int,
    from_date: date,
    to_date: date,
    limit: int = 10,
) -> List[dict]:
    """
    Returns items most sold for a business in a date range, ordered by quantity sold.
    """
    # #region agent log
    _dlog("get_most_sold_items entry", {"business_id": business_id, "from_date": str(from_date), "to_date": str(to_date)}, "H4")
    # #endregion
    rows = (
        db.session.query(
            Sale.inventory_item_id,
            InventoryItem.item_name,
            func.sum(Sale.quantity_sold).label("total_quantity"),
            func.sum(Sale.total_amount).label("total_amount"),
        )
        .join(InventoryItem, Sale.inventory_item_id == InventoryItem.id)
        .filter(
            Sale.business_id == business_id,
            func.date(Sale.sold_at) >= from_date,
            func.date(Sale.sold_at) <= to_date,
        )
        .group_by(Sale.inventory_item_id, InventoryItem.item_name)
        .order_by(func.sum(Sale.quantity_sold).desc())
        .limit(limit)
        .all()
    )
    # #region agent log
    _dlog("get_most_sold_items after query", {"row_count": len(rows), "first_total_quantity": getattr(rows[0], "total_quantity", None) if rows else None}, "H4")
    # #endregion
    return [
        {
            "inventory_item_id": r.inventory_item_id,
            "item_name": r.item_name,
            "quantity_sold": int(r.total_quantity),
            "total_amount": float(r.total_amount),
        }
        for r in rows
    ]


def get_most_sold_items_for_day(business_id: int, target_date: date, limit: int = 10) -> List[dict]:
    """Most sold items on a single day."""
    return get_most_sold_items(business_id, target_date, target_date, limit=limit)


def compute_daily_summary(business_id: int, target_date: date) -> dict:
    """
    Compute revenue (inflows), expenses (outflows + manual expenses), net profit,
    and top sold items for the given day.
    """
    date_start = datetime.combine(target_date, datetime.min.time())
    date_end = datetime.combine(target_date, datetime.max.time())

    inflows = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.business_id == business_id,
            Transaction.type == "inflow",
            Transaction.date_added >= date_start,
            Transaction.date_added <= date_end,
        )
        .scalar()
    )
    total_revenue = float(inflows or 0)

    outflows = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.business_id == business_id,
            Transaction.type == "outflow",
            Transaction.date_added >= date_start,
            Transaction.date_added <= date_end,
        )
        .scalar()
    )
    manual = (
        db.session.query(func.coalesce(func.sum(ManualExpense.amount), 0))
        .filter(
            ManualExpense.business_id == business_id,
            ManualExpense.expense_date == target_date,
        )
        .scalar()
    )
    total_expenses = float(outflows or 0) + float(manual or 0)
    net_profit = total_revenue - total_expenses

    top_sold = get_most_sold_items_for_day(business_id, target_date, limit=10)
    top_sold_json = json.dumps(
        [
            {"item_name": s["item_name"], "quantity_sold": s["quantity_sold"]}
            for s in top_sold
        ]
    )

    return {
        "summary_date": target_date.isoformat(),
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "top_sold_items": top_sold,
        "top_sold_items_json": top_sold_json,
    }


def store_daily_summary(business_id: int, target_date: date) -> DailySummary:
    """
    Compute and store (or update) daily summary for the given date.
    Returns the DailySummary model instance.
    """
    computed = compute_daily_summary(business_id, target_date)
    existing = DailySummary.query.filter_by(
        business_id=business_id,
        summary_date=target_date,
    ).first()
    if existing:
        existing.total_revenue = computed["total_revenue"]
        existing.total_expenses = computed["total_expenses"]
        existing.net_profit = computed["net_profit"]
        existing.top_sold_items = computed["top_sold_items_json"]
        db.session.commit()
        return existing
    new_summary = DailySummary(
        business_id=business_id,
        summary_date=target_date,
        total_revenue=computed["total_revenue"],
        total_expenses=computed["total_expenses"],
        net_profit=computed["net_profit"],
        top_sold_items=computed["top_sold_items_json"],
    )
    db.session.add(new_summary)
    db.session.commit()
    return new_summary


def get_daily_summaries(
    business_id: int,
    from_date: date,
    to_date: date,
) -> List[dict]:
    """
    Return stored daily summaries in range for trends (profit, loss, most sold per day).
    """
    rows = (
        DailySummary.query.filter(
            DailySummary.business_id == business_id,
            DailySummary.summary_date >= from_date,
            DailySummary.summary_date <= to_date,
        )
        .order_by(DailySummary.summary_date.asc())
        .all()
    )
    return [r.to_dict() for r in rows]
