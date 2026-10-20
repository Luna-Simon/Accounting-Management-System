"""
Depreciation calculation utilities.
Straight-line depreciation: (Cost - Salvage Value) / Useful Life
Salvage Value = Cost * Salvage Percentage
"""

from decimal import Decimal, ROUND_HALF_UP
from logic import clean_float, scale_money


def calculate_depreciation(cost, salvage_percent, useful_life_years):
    """
    Calculate annual and monthly depreciation using straight-line method.
    
    Args:
        cost: Asset cost (float)
        salvage_percent: Salvage value as percentage of cost (e.g., 5 for 5%)
        useful_life_years: Useful life in years (int)
    
    Returns:
        dict with 'annual', 'monthly', 'salvage_value', 'depreciable_base'
    """
    cost = clean_float(cost)
    salvage_percent = clean_float(salvage_percent)
    useful_life_years = int(clean_float(useful_life_years))
    
    if cost <= 0 or useful_life_years <= 0:
        return {"annual": 0.0, "monthly": 0.0, "salvage_value": 0.0, "depreciable_base": 0.0}
    
    salvage_value = cost * (salvage_percent / 100.0)
    depreciable_base = cost - salvage_value
    annual = depreciable_base / useful_life_years
    monthly = annual / 12.0
    
    return {
        "annual": round(annual, 2),
        "monthly": round(monthly, 2),
        "salvage_value": round(salvage_value, 2),
        "depreciable_base": round(depreciable_base, 2)
    }


def calculate_depreciation_schedule(cost, salvage_percent, useful_life_years, months=12):
    """
    Generate a monthly depreciation schedule.
    
    Returns list of dicts with month, accumulated, book_value
    """
    result = calculate_depreciation(cost, salvage_percent, useful_life_years)
    annual = result["annual"]
    monthly = result["monthly"]
    salvage = result["salvage_value"]
    
    schedule = []
    accumulated = 0.0
    book_value = cost
    
    total_months = useful_life_years * 12
    for month in range(1, min(months, total_months) + 1):
        accumulated += monthly
        book_value = cost - accumulated
        if book_value < salvage:
            book_value = salvage
        schedule.append({
            "month": month,
            "depreciation": round(monthly, 2),
            "accumulated": round(accumulated, 2),
            "book_value": round(book_value, 2)
        })
    
    return schedule


def create_depreciation_entry(asset_account, accum_depr_account, depr_expense_account, monthly_amount, date, description):
    """
    Create a depreciation adjusting entry.
    
    Returns entry dict ready for save_entry
    """
    monthly_cents = scale_money(monthly_amount)
    return {
        "id": None,
        "date": date,
        "description": description,
        "lines": [
            {"account": depr_expense_account, "debit": monthly_cents, "credit": 0},
            {"account": accum_depr_account, "debit": 0, "credit": monthly_cents},
        ]
    }