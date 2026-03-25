"""
Ouroboros — Tax & Bookkeeping tools.

Full-featured bookkeeping, tax estimation, P&L, invoicing, and deduction tracking.
All data persisted to JSON ledger files on disk.
"""

from __future__ import annotations
import logging

from ouroboros.tools._adapter import adapt_tools
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_tax")
LEDGER_PATH = os.path.join(WORKSPACE, "tax_ledger.json")

# ── IRS categories & tax constants ────────────────────────────────────────

IRS_EXPENSE_CATEGORIES = {
    "advertising": "Advertising",
    "car_vehicle": "Car and truck expenses",
    "commissions": "Commissions and fees",
    "contract_labor": "Contract labor",
    "depletion": "Depletion",
    "depreciation": "Depreciation",
    "employee_benefits": "Employee benefit programs",
    "insurance": "Insurance (other than health)",
    "interest_mortgage": "Interest (mortgage)",
    "interest_other": "Interest (other)",
    "legal_professional": "Legal and professional services",
    "office_expense": "Office expense",
    "pension_profit_sharing": "Pension and profit-sharing plans",
    "rent_lease_vehicles": "Rent or lease (vehicles, machinery, equipment)",
    "rent_lease_property": "Rent or lease (other business property)",
    "repairs_maintenance": "Repairs and maintenance",
    "supplies": "Supplies",
    "taxes_licenses": "Taxes and licenses",
    "travel": "Travel",
    "meals": "Meals (50% deductible)",
    "utilities": "Utilities",
    "wages": "Wages",
    "other": "Other expenses",
    "home_office": "Home office deduction",
    "phone_internet": "Phone and internet",
    "education_training": "Education and training",
    "software_subscriptions": "Software and subscriptions",
    "equipment": "Equipment purchases",
    "shipping": "Shipping and postage",
    "bank_fees": "Bank fees",
    "dues_memberships": "Dues and memberships",
}

INCOME_CATEGORIES = {
    "freelance": "Freelance / Contract Work",
    "product_sales": "Product Sales",
    "service": "Service Revenue",
    "rental": "Rental Income",
    "interest": "Interest Income",
    "dividend": "Dividend Income",
    "royalty": "Royalties",
    "affiliate": "Affiliate / Commission",
    "consulting": "Consulting",
    "1099_nec": "1099-NEC Income",
    "1099_misc": "1099-MISC Income",
    "1099_k": "1099-K Income",
    "other": "Other Income",
}

# 2024/2025 IRS rates (update annually)
FEDERAL_TAX_BRACKETS_SINGLE = [
    (11600, 0.10),
    (47150, 0.12),
    (100525, 0.22),
    (191950, 0.24),
    (243725, 0.32),
    (609350, 0.35),
    (float("inf"), 0.37),
]

SELF_EMPLOYMENT_TAX_RATE = 0.153  # 15.3% (12.4% SS + 2.9% Medicare)
SE_TAX_SS_WAGE_BASE = 168600  # 2024 Social Security wage base
STANDARD_DEDUCTION_SINGLE = 14600
STANDARD_DEDUCTION_MARRIED = 29200
QUALIFIED_BUSINESS_INCOME_DEDUCTION = 0.20  # QBI 20% deduction
IRS_MILEAGE_RATE = 0.67  # 2024 standard mileage rate per mile

# State sales tax rates (approximate - major states)
STATE_SALES_TAX = {
    "AL": 0.04, "AK": 0.0, "AZ": 0.056, "AR": 0.065, "CA": 0.0725,
    "CO": 0.029, "CT": 0.0635, "DE": 0.0, "FL": 0.06, "GA": 0.04,
    "HI": 0.04, "ID": 0.06, "IL": 0.0625, "IN": 0.07, "IA": 0.06,
    "KS": 0.065, "KY": 0.06, "LA": 0.0445, "ME": 0.055, "MD": 0.06,
    "MA": 0.0625, "MI": 0.06, "MN": 0.06875, "MS": 0.07, "MO": 0.04225,
    "MT": 0.0, "NE": 0.055, "NV": 0.0685, "NH": 0.0, "NJ": 0.06625,
    "NM": 0.05125, "NY": 0.04, "NC": 0.0475, "ND": 0.05, "OH": 0.0575,
    "OK": 0.045, "OR": 0.0, "PA": 0.06, "RI": 0.07, "SC": 0.06,
    "SD": 0.042, "TN": 0.07, "TX": 0.0625, "UT": 0.061, "VT": 0.06,
    "VA": 0.053, "WA": 0.065, "WV": 0.06, "WI": 0.05, "WY": 0.04,
    "DC": 0.06,
}


# ── Ledger persistence ───────────────────────────────────────────────────

def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


def _load_ledger() -> Dict[str, Any]:
    _ensure_workspace()
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH) as f:
            return json.load(f)
    return {
        "income": [],
        "expenses": [],
        "mileage": [],
        "invoices": [],
        "1099s": [],
        "assets": [],
        "liabilities": [],
        "created": datetime.now().isoformat(),
    }


def _save_ledger(ledger: Dict[str, Any]):
    _ensure_workspace()
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, indent=2)


# ── Tool implementations ─────────────────────────────────────────────────

def track_income(amount: float, category: str = "freelance",
                 description: str = "", client: str = "",
                 date: str = "", is_1099: bool = False) -> Dict[str, Any]:
    """Track an income entry with categorization."""
    ledger = _load_ledger()
    entry_date = date or datetime.now().strftime("%Y-%m-%d")
    entry = {
        "id": str(uuid.uuid4())[:8],
        "amount": round(amount, 2),
        "category": category,
        "category_label": INCOME_CATEGORIES.get(category, category),
        "description": description,
        "client": client,
        "date": entry_date,
        "is_1099": is_1099,
        "timestamp": datetime.now().isoformat(),
    }
    ledger["income"].append(entry)
    if is_1099:
        ledger["1099s"].append({
            "income_id": entry["id"],
            "amount": entry["amount"],
            "client": client,
            "category": category,
            "date": entry_date,
        })
    _save_ledger(ledger)

    # Compute running totals
    now = datetime.now()
    month_income = sum(
        e["amount"] for e in ledger["income"]
        if e["date"].startswith(now.strftime("%Y-%m"))
    )
    quarter = (now.month - 1) // 3 + 1
    q_start = f"{now.year}-{(quarter - 1) * 3 + 1:02d}"
    year_income = sum(
        e["amount"] for e in ledger["income"]
        if e["date"].startswith(str(now.year))
    )
    return {
        "status": "recorded",
        "entry": entry,
        "running_totals": {
            "month": round(month_income, 2),
            "year": round(year_income, 2),
        },
    }


def categorize_expense(amount: float, category: str = "other",
                       description: str = "", vendor: str = "",
                       date: str = "", receipt: str = "",
                       is_deductible: bool = True) -> Dict[str, Any]:
    """Record and categorize an expense by IRS categories."""
    ledger = _load_ledger()
    entry_date = date or datetime.now().strftime("%Y-%m-%d")

    # Auto-categorize from description keywords if category is "other"
    if category == "other" and description:
        desc_lower = description.lower()
        auto_map = {
            "office": "office_expense", "supplies": "supplies",
            "software": "software_subscriptions", "subscription": "software_subscriptions",
            "uber": "travel", "lyft": "travel", "flight": "travel", "hotel": "travel",
            "airbnb": "travel", "airline": "travel",
            "lunch": "meals", "dinner": "meals", "restaurant": "meals",
            "coffee": "meals", "food": "meals",
            "gas": "car_vehicle", "parking": "car_vehicle", "car": "car_vehicle",
            "insurance": "insurance", "lawyer": "legal_professional",
            "attorney": "legal_professional", "accountant": "legal_professional",
            "phone": "phone_internet", "internet": "phone_internet",
            "wifi": "phone_internet", "cell": "phone_internet",
            "rent": "rent_lease_property", "lease": "rent_lease_property",
            "electric": "utilities", "water": "utilities", "power": "utilities",
            "repair": "repairs_maintenance", "maintenance": "repairs_maintenance",
            "shipping": "shipping", "postage": "shipping", "fedex": "shipping",
            "ups": "shipping", "usps": "shipping",
            "bank fee": "bank_fees", "wire fee": "bank_fees",
            "course": "education_training", "training": "education_training",
            "conference": "education_training", "book": "education_training",
            "ads": "advertising", "facebook ad": "advertising", "google ad": "advertising",
            "computer": "equipment", "laptop": "equipment", "monitor": "equipment",
        }
        for keyword, cat in auto_map.items():
            if keyword in desc_lower:
                category = cat
                break

    deduction_pct = 1.0
    if category == "meals":
        deduction_pct = 0.5  # Meals are 50% deductible

    entry = {
        "id": str(uuid.uuid4())[:8],
        "amount": round(amount, 2),
        "category": category,
        "category_label": IRS_EXPENSE_CATEGORIES.get(category, category),
        "description": description,
        "vendor": vendor,
        "date": entry_date,
        "receipt": receipt,
        "is_deductible": is_deductible,
        "deduction_pct": deduction_pct,
        "deductible_amount": round(amount * deduction_pct, 2) if is_deductible else 0,
        "timestamp": datetime.now().isoformat(),
    }
    ledger["expenses"].append(entry)
    _save_ledger(ledger)

    year_expenses_by_cat = {}
    for e in ledger["expenses"]:
        if e["date"].startswith(str(datetime.now().year)):
            cat = e.get("category_label", e["category"])
            year_expenses_by_cat[cat] = round(
                year_expenses_by_cat.get(cat, 0) + e["amount"], 2
            )

    return {
        "status": "recorded",
        "entry": entry,
        "year_expenses_by_category": year_expenses_by_cat,
    }


def generate_pnl(period: str = "year", year: int = 0,
                  month: int = 0, quarter: int = 0) -> Dict[str, Any]:
    """Generate a Profit & Loss statement for a given period."""
    ledger = _load_ledger()
    now = datetime.now()
    target_year = year or now.year

    def date_in_period(d: str) -> bool:
        if period == "year":
            return d.startswith(str(target_year))
        elif period == "month":
            m = month or now.month
            return d.startswith(f"{target_year}-{m:02d}")
        elif period == "quarter":
            q = quarter or ((now.month - 1) // 3 + 1)
            q_months = list(range((q - 1) * 3 + 1, q * 3 + 1))
            try:
                entry_month = int(d.split("-")[1])
                return d.startswith(str(target_year)) and entry_month in q_months
            except (IndexError, ValueError):
                return False
        return True

    income_items = [e for e in ledger["income"] if date_in_period(e["date"])]
    expense_items = [e for e in ledger["expenses"] if date_in_period(e["date"])]

    # Income by category
    income_by_cat = {}
    for e in income_items:
        cat = e.get("category_label", e["category"])
        income_by_cat[cat] = round(income_by_cat.get(cat, 0) + e["amount"], 2)
    total_income = round(sum(e["amount"] for e in income_items), 2)

    # Expenses by category
    expense_by_cat = {}
    for e in expense_items:
        cat = e.get("category_label", e["category"])
        expense_by_cat[cat] = round(expense_by_cat.get(cat, 0) + e["amount"], 2)
    total_expenses = round(sum(e["amount"] for e in expense_items), 2)

    gross_profit = round(total_income - total_expenses, 2)
    margin = round((gross_profit / total_income * 100), 2) if total_income > 0 else 0

    return {
        "title": f"Profit & Loss Statement — {period.title()} {target_year}",
        "period": period,
        "revenue": {
            "items": income_by_cat,
            "total": total_income,
        },
        "expenses": {
            "items": expense_by_cat,
            "total": total_expenses,
        },
        "gross_profit": gross_profit,
        "profit_margin_pct": margin,
        "net_income": gross_profit,
        "income_count": len(income_items),
        "expense_count": len(expense_items),
    }


def estimate_quarterly_tax(annual_income: float = 0, annual_expenses: float = 0,
                           filing_status: str = "single",
                           state: str = "", other_income: float = 0,
                           estimated_payments_made: float = 0) -> Dict[str, Any]:
    """Estimate quarterly taxes: federal income tax + self-employment tax."""
    ledger = _load_ledger()
    now = datetime.now()

    # Use ledger data if no overrides
    if annual_income == 0:
        annual_income = sum(
            e["amount"] for e in ledger["income"]
            if e["date"].startswith(str(now.year))
        )
    if annual_expenses == 0:
        annual_expenses = sum(
            e.get("deductible_amount", e["amount"])
            for e in ledger["expenses"]
            if e["date"].startswith(str(now.year)) and e.get("is_deductible", True)
        )

    net_self_employment = max(0, annual_income - annual_expenses)

    # Self-employment tax
    se_taxable = net_self_employment * 0.9235  # 92.35% is subject to SE tax
    if se_taxable > SE_TAX_SS_WAGE_BASE:
        ss_tax = SE_TAX_SS_WAGE_BASE * 0.124
        medicare_tax = se_taxable * 0.029
        # Additional Medicare tax on high earners
        if se_taxable > 200000:
            medicare_tax += (se_taxable - 200000) * 0.009
    else:
        ss_tax = se_taxable * 0.124
        medicare_tax = se_taxable * 0.029
    se_tax = round(ss_tax + medicare_tax, 2)

    # Deduction for 50% of SE tax
    se_deduction = round(se_tax / 2, 2)

    # Adjusted gross income
    agi = net_self_employment + other_income - se_deduction

    # Standard deduction
    std_deduction = (STANDARD_DEDUCTION_MARRIED if filing_status == "married"
                     else STANDARD_DEDUCTION_SINGLE)

    # QBI deduction (20% of qualified business income, simplified)
    qbi_deduction = round(net_self_employment * QUALIFIED_BUSINESS_INCOME_DEDUCTION, 2)
    qbi_deduction = min(qbi_deduction, round(agi * 0.20, 2))

    taxable_income = max(0, agi - std_deduction - qbi_deduction)

    # Federal income tax calculation
    brackets = FEDERAL_TAX_BRACKETS_SINGLE
    federal_tax = 0.0
    prev_limit = 0
    for limit, rate in brackets:
        if taxable_income <= 0:
            break
        bracket_income = min(taxable_income, limit) - prev_limit
        if bracket_income > 0:
            federal_tax += bracket_income * rate
        prev_limit = limit
        if taxable_income <= limit:
            break

    federal_tax = round(federal_tax, 2)
    total_annual_tax = round(federal_tax + se_tax, 2)
    quarterly_payment = round(total_annual_tax / 4, 2)
    remaining = round(max(0, total_annual_tax - estimated_payments_made), 2)

    effective_rate = round(
        (total_annual_tax / net_self_employment * 100) if net_self_employment > 0 else 0, 2
    )

    # Quarterly due dates
    due_dates = ["April 15", "June 15", "September 15", "January 15 (next year)"]
    current_quarter = (now.month - 1) // 3 + 1

    return {
        "summary": {
            "gross_income": round(annual_income, 2),
            "deductible_expenses": round(annual_expenses, 2),
            "net_self_employment_income": round(net_self_employment, 2),
            "other_income": round(other_income, 2),
            "adjusted_gross_income": round(agi, 2),
        },
        "deductions": {
            "standard_deduction": std_deduction,
            "se_tax_deduction": se_deduction,
            "qbi_deduction": qbi_deduction,
            "taxable_income": round(taxable_income, 2),
        },
        "taxes": {
            "federal_income_tax": federal_tax,
            "self_employment_tax": se_tax,
            "social_security": round(ss_tax, 2),
            "medicare": round(medicare_tax, 2),
            "total_annual_tax": total_annual_tax,
            "effective_tax_rate_pct": effective_rate,
        },
        "quarterly_estimate": {
            "quarterly_payment": quarterly_payment,
            "estimated_payments_made": estimated_payments_made,
            "remaining_liability": remaining,
            "current_quarter": current_quarter,
            "next_due": due_dates[min(current_quarter, 3)],
        },
        "filing_status": filing_status,
    }


def find_deductions(year: int = 0) -> Dict[str, Any]:
    """Scan expenses for potential tax deductions and optimization opportunities."""
    ledger = _load_ledger()
    target_year = year or datetime.now().year

    expenses = [
        e for e in ledger["expenses"]
        if e["date"].startswith(str(target_year))
    ]

    # Categorize deductions
    claimed = []
    unclaimed = []
    potential_missed = []

    for e in expenses:
        if e.get("is_deductible", True):
            claimed.append({
                "description": e["description"],
                "amount": e["amount"],
                "category": e.get("category_label", e["category"]),
                "deductible_amount": e.get("deductible_amount", e["amount"]),
            })
        else:
            unclaimed.append({
                "description": e["description"],
                "amount": e["amount"],
                "category": e.get("category_label", e["category"]),
            })

    total_claimed = round(sum(d["deductible_amount"] for d in claimed), 2)

    # Suggest commonly missed deductions
    claimed_cats = {e["category"] for e in expenses}
    common_missed = []
    missed_map = {
        "home_office": "Home Office Deduction — If you work from home, deduct a portion of rent/mortgage, utilities, and internet.",
        "phone_internet": "Phone & Internet — Business portion of your phone and internet bills.",
        "education_training": "Education — Courses, books, conferences related to your business.",
        "car_vehicle": "Vehicle Expenses — Business mileage at $0.67/mile (2024) or actual expenses.",
        "insurance": "Business Insurance — Liability, E&O, or professional insurance premiums.",
        "software_subscriptions": "Software & Subscriptions — SaaS tools, cloud hosting, design tools.",
        "bank_fees": "Bank & Payment Fees — Business account fees, payment processing fees.",
        "dues_memberships": "Professional Dues — Industry associations, professional memberships.",
        "depreciation": "Depreciation — Section 179 deduction for equipment over $2,500.",
        "advertising": "Marketing & Advertising — Website costs, ads, business cards.",
    }
    for cat, advice in missed_map.items():
        if cat not in claimed_cats:
            common_missed.append(advice)

    # Check for home office eligibility
    has_home_office = "home_office" in claimed_cats
    # Retirement suggestions
    income_items = [
        e for e in ledger["income"]
        if e["date"].startswith(str(target_year))
    ]
    total_income = sum(e["amount"] for e in income_items)
    retirement_suggestions = []
    if total_income > 0:
        solo_401k_limit = min(69000, total_income)
        sep_ira_limit = min(69000, round(total_income * 0.25, 2))
        retirement_suggestions = [
            f"Solo 401(k): Contribute up to ${solo_401k_limit:,.2f} (employee + employer)",
            f"SEP IRA: Contribute up to ${sep_ira_limit:,.2f} (25% of net self-employment)",
            "Traditional IRA: Up to $7,000 ($8,000 if age 50+)",
            "HSA: Up to $4,150 single / $8,300 family (if eligible)",
        ]

    return {
        "year": target_year,
        "claimed_deductions": {
            "count": len(claimed),
            "total": total_claimed,
            "by_category": _group_sum(claimed, "category"),
        },
        "unclaimed_expenses": {
            "count": len(unclaimed),
            "total": round(sum(u["amount"] for u in unclaimed), 2),
            "items": unclaimed[:20],
        },
        "commonly_missed_deductions": common_missed,
        "retirement_contribution_opportunities": retirement_suggestions,
        "tips": [
            "Keep all receipts for expenses over $75",
            "Document business purpose for all meal and travel expenses",
            "Track mileage with a log (date, destination, business purpose, miles)",
            "Consider estimated tax payments to avoid underpayment penalty",
            "If married, compare filing jointly vs separately",
        ],
    }


def _group_sum(items: list, key: str) -> Dict[str, float]:
    result = {}
    for item in items:
        k = item.get(key, "other")
        result[k] = round(result.get(k, 0) + item.get("deductible_amount", item.get("amount", 0)), 2)
    return result


def track_mileage(miles: float, date: str = "", purpose: str = "",
                  destination: str = "", round_trip: bool = False) -> Dict[str, Any]:
    """Track business mileage using the IRS standard rate."""
    ledger = _load_ledger()
    entry_date = date or datetime.now().strftime("%Y-%m-%d")
    actual_miles = miles * 2 if round_trip else miles
    deduction = round(actual_miles * IRS_MILEAGE_RATE, 2)

    entry = {
        "id": str(uuid.uuid4())[:8],
        "miles": round(actual_miles, 1),
        "date": entry_date,
        "purpose": purpose,
        "destination": destination,
        "round_trip": round_trip,
        "rate": IRS_MILEAGE_RATE,
        "deduction": deduction,
        "timestamp": datetime.now().isoformat(),
    }
    ledger["mileage"].append(entry)
    _save_ledger(ledger)

    year_miles = sum(
        m["miles"] for m in ledger["mileage"]
        if m["date"].startswith(str(datetime.now().year))
    )
    year_deduction = round(year_miles * IRS_MILEAGE_RATE, 2)

    return {
        "status": "recorded",
        "entry": entry,
        "year_totals": {
            "total_miles": round(year_miles, 1),
            "total_deduction": year_deduction,
            "irs_rate": IRS_MILEAGE_RATE,
            "trip_count": len([
                m for m in ledger["mileage"]
                if m["date"].startswith(str(datetime.now().year))
            ]),
        },
    }


def track_1099(payer: str, amount: float, form_type: str = "1099-NEC",
               ein: str = "", date_received: str = "",
               tax_withheld: float = 0) -> Dict[str, Any]:
    """Track 1099 income forms received."""
    ledger = _load_ledger()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "payer": payer,
        "amount": round(amount, 2),
        "form_type": form_type,
        "ein": ein,
        "date_received": date_received or datetime.now().strftime("%Y-%m-%d"),
        "tax_withheld": round(tax_withheld, 2),
        "year": datetime.now().year,
        "timestamp": datetime.now().isoformat(),
    }
    ledger["1099s"].append(entry)
    _save_ledger(ledger)

    year_1099s = [e for e in ledger["1099s"] if e.get("year") == datetime.now().year]
    total_1099 = round(sum(e["amount"] for e in year_1099s), 2)
    total_withheld = round(sum(e.get("tax_withheld", 0) for e in year_1099s), 2)

    return {
        "status": "recorded",
        "entry": entry,
        "year_summary": {
            "total_1099_income": total_1099,
            "total_tax_withheld": total_withheld,
            "form_count": len(year_1099s),
            "payers": list({e["payer"] for e in year_1099s}),
        },
    }


def generate_balance_sheet(as_of_date: str = "") -> Dict[str, Any]:
    """Generate a simple balance sheet from ledger data."""
    ledger = _load_ledger()
    target = as_of_date or datetime.now().strftime("%Y-%m-%d")
    year = target[:4]

    income = [e for e in ledger["income"] if e["date"] <= target]
    expenses = [e for e in ledger["expenses"] if e["date"] <= target]

    total_income = round(sum(e["amount"] for e in income), 2)
    total_expenses = round(sum(e["amount"] for e in expenses), 2)
    retained_earnings = round(total_income - total_expenses, 2)

    # Assets = Cash (simplified as retained earnings) + equipment (from asset entries)
    assets_list = [a for a in ledger.get("assets", []) if a.get("date", "") <= target]
    total_assets_recorded = round(sum(a.get("value", 0) for a in assets_list), 2)

    # Accounts receivable from unpaid invoices
    ar = 0
    for inv in ledger.get("invoices", []):
        if inv.get("status") != "paid" and inv.get("date", "") <= target:
            ar += inv.get("total", 0)
    ar = round(ar, 2)

    liabilities_list = [l for l in ledger.get("liabilities", []) if l.get("date", "") <= target]
    total_liabilities = round(sum(l.get("amount", 0) for l in liabilities_list), 2)

    cash = round(retained_earnings, 2)
    total_assets = round(cash + ar + total_assets_recorded, 2)
    equity = round(total_assets - total_liabilities, 2)

    return {
        "title": f"Balance Sheet as of {target}",
        "assets": {
            "current_assets": {
                "cash_and_equivalents": cash,
                "accounts_receivable": ar,
                "total_current": round(cash + ar, 2),
            },
            "fixed_assets": {
                "equipment_and_property": total_assets_recorded,
                "items": assets_list[:10],
            },
            "total_assets": total_assets,
        },
        "liabilities": {
            "items": liabilities_list[:10],
            "total_liabilities": total_liabilities,
        },
        "equity": {
            "retained_earnings": retained_earnings,
            "total_equity": equity,
        },
        "balanced": abs(total_assets - (total_liabilities + equity)) < 0.01,
    }


def analyze_cash_flow(period: str = "month", year: int = 0,
                      month: int = 0) -> Dict[str, Any]:
    """Analyze cash flow — inflows vs outflows over time."""
    ledger = _load_ledger()
    now = datetime.now()
    target_year = year or now.year
    target_month = month or now.month

    if period == "year":
        months = range(1, 13)
    elif period == "quarter":
        q = (target_month - 1) // 3 + 1
        months = range((q - 1) * 3 + 1, q * 3 + 1)
    else:
        months = [target_month]

    monthly_flow = []
    running_balance = 0

    for m in months:
        prefix = f"{target_year}-{m:02d}"
        m_income = round(sum(
            e["amount"] for e in ledger["income"] if e["date"].startswith(prefix)
        ), 2)
        m_expenses = round(sum(
            e["amount"] for e in ledger["expenses"] if e["date"].startswith(prefix)
        ), 2)
        net = round(m_income - m_expenses, 2)
        running_balance = round(running_balance + net, 2)

        monthly_flow.append({
            "month": prefix,
            "inflows": m_income,
            "outflows": m_expenses,
            "net_cash_flow": net,
            "running_balance": running_balance,
        })

    total_in = round(sum(m["inflows"] for m in monthly_flow), 2)
    total_out = round(sum(m["outflows"] for m in monthly_flow), 2)
    avg_monthly_net = round(
        (total_in - total_out) / len(monthly_flow), 2
    ) if monthly_flow else 0

    # Burn rate (if expenses exceed income)
    burn_rate = round(total_out / len(monthly_flow), 2) if monthly_flow else 0
    avg_income = round(total_in / len(monthly_flow), 2) if monthly_flow else 0

    return {
        "period": period,
        "year": target_year,
        "monthly_breakdown": monthly_flow,
        "summary": {
            "total_inflows": total_in,
            "total_outflows": total_out,
            "net_cash_flow": round(total_in - total_out, 2),
            "avg_monthly_net": avg_monthly_net,
            "avg_monthly_income": avg_income,
            "avg_monthly_expenses": burn_rate,
        },
        "health": {
            "positive_months": sum(1 for m in monthly_flow if m["net_cash_flow"] > 0),
            "negative_months": sum(1 for m in monthly_flow if m["net_cash_flow"] < 0),
            "trend": "positive" if avg_monthly_net > 0 else "negative",
            "months_of_runway": (
                round(running_balance / burn_rate, 1) if burn_rate > 0 and running_balance > 0
                else float("inf")
            ),
        },
    }


def year_end_tax_summary(year: int = 0,
                         filing_status: str = "single") -> Dict[str, Any]:
    """Comprehensive year-end tax summary combining all data."""
    target_year = year or datetime.now().year
    ledger = _load_ledger()

    income = [e for e in ledger["income"] if e["date"].startswith(str(target_year))]
    expenses = [e for e in ledger["expenses"] if e["date"].startswith(str(target_year))]
    mileage = [m for m in ledger["mileage"] if m["date"].startswith(str(target_year))]
    forms_1099 = [f for f in ledger["1099s"] if f.get("year") == target_year or
                  f.get("date_received", "").startswith(str(target_year))]

    total_income = round(sum(e["amount"] for e in income), 2)
    total_expenses = round(sum(e["amount"] for e in expenses), 2)
    total_deductible = round(sum(
        e.get("deductible_amount", e["amount"])
        for e in expenses if e.get("is_deductible", True)
    ), 2)

    # Mileage deduction
    total_miles = sum(m["miles"] for m in mileage)
    mileage_deduction = round(total_miles * IRS_MILEAGE_RATE, 2)

    # Income by category
    income_by_cat = {}
    for e in income:
        cat = e.get("category_label", e["category"])
        income_by_cat[cat] = round(income_by_cat.get(cat, 0) + e["amount"], 2)

    # Expenses by category
    expense_by_cat = {}
    for e in expenses:
        cat = e.get("category_label", e["category"])
        expense_by_cat[cat] = round(expense_by_cat.get(cat, 0) + e["amount"], 2)

    # 1099 summary
    total_1099 = round(sum(f["amount"] for f in forms_1099), 2)
    total_withheld = round(sum(f.get("tax_withheld", 0) for f in forms_1099), 2)

    # Tax estimate
    tax_est = estimate_quarterly_tax(
        annual_income=total_income,
        annual_expenses=total_deductible + mileage_deduction,
        filing_status=filing_status,
        estimated_payments_made=total_withheld,
    )

    # Quarterly breakdown
    quarterly = []
    for q in range(1, 5):
        q_months = list(range((q - 1) * 3 + 1, q * 3 + 1))
        q_income = round(sum(
            e["amount"] for e in income
            if int(e["date"].split("-")[1]) in q_months
        ), 2)
        q_expenses = round(sum(
            e["amount"] for e in expenses
            if int(e["date"].split("-")[1]) in q_months
        ), 2)
        quarterly.append({
            "quarter": f"Q{q}",
            "income": q_income,
            "expenses": q_expenses,
            "net": round(q_income - q_expenses, 2),
        })

    return {
        "title": f"Year-End Tax Summary — {target_year}",
        "year": target_year,
        "filing_status": filing_status,
        "income_summary": {
            "total": total_income,
            "by_category": income_by_cat,
            "1099_income": total_1099,
            "tax_withheld": total_withheld,
        },
        "expense_summary": {
            "total": total_expenses,
            "total_deductible": total_deductible,
            "by_category": expense_by_cat,
        },
        "mileage_summary": {
            "total_miles": round(total_miles, 1),
            "deduction": mileage_deduction,
            "trip_count": len(mileage),
        },
        "net_profit": round(total_income - total_expenses, 2),
        "quarterly_breakdown": quarterly,
        "tax_estimate": tax_est["taxes"],
        "quarterly_payment": tax_est["quarterly_estimate"],
        "deductions_used": tax_est["deductions"],
        "forms_needed": [
            "Schedule C (Form 1040) — Profit or Loss from Business",
            "Schedule SE — Self-Employment Tax",
            "Form 1040-ES — Estimated Tax" if total_income > 1000 else None,
            "Schedule 1 — Additional Income and Adjustments",
        ],
    }


def create_invoice(client: str, items: list, invoice_number: str = "",
                   due_days: int = 30, notes: str = "",
                   tax_rate: float = 0, state: str = "") -> Dict[str, Any]:
    """Create an invoice with tax line items.

    items: list of dicts with 'description', 'quantity', 'unit_price'
    """
    ledger = _load_ledger()
    inv_num = invoice_number or f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
    issue_date = datetime.now().strftime("%Y-%m-%d")
    due_date = (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d")

    # Calculate line items
    line_items = []
    subtotal = 0
    for item in items:
        desc = item.get("description", "Service")
        qty = item.get("quantity", 1)
        price = item.get("unit_price", 0)
        line_total = round(qty * price, 2)
        subtotal += line_total
        line_items.append({
            "description": desc,
            "quantity": qty,
            "unit_price": round(price, 2),
            "total": line_total,
        })

    subtotal = round(subtotal, 2)

    # Tax calculation
    actual_tax_rate = tax_rate
    if actual_tax_rate == 0 and state:
        actual_tax_rate = STATE_SALES_TAX.get(state.upper(), 0)

    tax_amount = round(subtotal * actual_tax_rate, 2)
    total = round(subtotal + tax_amount, 2)

    invoice = {
        "id": str(uuid.uuid4())[:8],
        "invoice_number": inv_num,
        "client": client,
        "date": issue_date,
        "due_date": due_date,
        "line_items": line_items,
        "subtotal": subtotal,
        "tax_rate": actual_tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "notes": notes,
        "status": "unpaid",
        "state": state,
        "timestamp": datetime.now().isoformat(),
    }
    ledger["invoices"].append(invoice)
    _save_ledger(ledger)

    return {
        "status": "created",
        "invoice": invoice,
        "payment_due": due_date,
    }


def calculate_sales_tax(amount: float, state: str,
                        city_rate: float = 0, county_rate: float = 0,
                        exempt: bool = False) -> Dict[str, Any]:
    """Calculate sales tax for any US state, optionally including city/county rates."""
    if exempt:
        return {
            "amount": round(amount, 2),
            "state": state.upper(),
            "tax_exempt": True,
            "state_rate": 0,
            "total_rate": 0,
            "tax_amount": 0,
            "total": round(amount, 2),
        }

    state_code = state.upper()
    state_rate = STATE_SALES_TAX.get(state_code, 0)
    total_rate = state_rate + city_rate + county_rate
    tax = round(amount * total_rate, 2)

    return {
        "amount": round(amount, 2),
        "state": state_code,
        "state_rate": state_rate,
        "state_rate_pct": round(state_rate * 100, 3),
        "city_rate": city_rate,
        "county_rate": county_rate,
        "combined_rate": round(total_rate, 5),
        "combined_rate_pct": round(total_rate * 100, 3),
        "tax_amount": tax,
        "total_with_tax": round(amount + tax, 2),
        "no_sales_tax": state_code in ("OR", "MT", "NH", "DE", "AK"),
        "note": (
            f"Alaska has no state sales tax but localities may impose taxes"
            if state_code == "AK" else ""
        ),
    }


# ── Tool registration ────────────────────────────────────────────────────

def _raw_tools():
    return [
        {
            "name": "track_income",
            "description": "Track and categorize income entries (freelance, product sales, service revenue, etc). Computes running monthly/annual totals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Income amount in USD"},
                    "category": {"type": "string", "description": "Income category: freelance, product_sales, service, rental, interest, dividend, royalty, affiliate, consulting, 1099_nec, 1099_misc, 1099_k, other"},
                    "description": {"type": "string", "description": "Description of the income"},
                    "client": {"type": "string", "description": "Client or payer name"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD), defaults to today"},
                    "is_1099": {"type": "boolean", "description": "Whether this is 1099 income"},
                },
                "required": ["amount"],
            },
            "function": track_income,
        },
        {
            "name": "categorize_expense",
            "description": "Record and auto-categorize expenses by IRS Schedule C categories. Auto-detects category from description if not specified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Expense amount in USD"},
                    "category": {"type": "string", "description": "IRS category: advertising, car_vehicle, office_expense, travel, meals, utilities, software_subscriptions, etc. Leave as 'other' for auto-detection."},
                    "description": {"type": "string", "description": "Expense description (used for auto-categorization)"},
                    "vendor": {"type": "string", "description": "Vendor or payee name"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "receipt": {"type": "string", "description": "Receipt reference or file path"},
                    "is_deductible": {"type": "boolean", "description": "Whether expense is tax-deductible (default true)"},
                },
                "required": ["amount"],
            },
            "function": categorize_expense,
        },
        {
            "name": "generate_pnl",
            "description": "Generate a Profit & Loss statement for a given period (month, quarter, or year). Shows revenue and expenses by category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["month", "quarter", "year"], "description": "Time period"},
                    "year": {"type": "integer", "description": "Year (defaults to current)"},
                    "month": {"type": "integer", "description": "Month number (for monthly P&L)"},
                    "quarter": {"type": "integer", "description": "Quarter number 1-4 (for quarterly P&L)"},
                },
            },
            "function": generate_pnl,
        },
        {
            "name": "estimate_quarterly_tax",
            "description": "Estimate quarterly taxes for US self-employed/freelancers. Calculates federal income tax + self-employment tax (SS + Medicare), applies standard deduction and QBI deduction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "annual_income": {"type": "number", "description": "Total annual income (uses ledger data if 0)"},
                    "annual_expenses": {"type": "number", "description": "Total deductible expenses (uses ledger if 0)"},
                    "filing_status": {"type": "string", "enum": ["single", "married"], "description": "Filing status"},
                    "state": {"type": "string", "description": "State code for state tax estimate"},
                    "other_income": {"type": "number", "description": "W-2 or other non-SE income"},
                    "estimated_payments_made": {"type": "number", "description": "Estimated tax payments already made this year"},
                },
            },
            "function": estimate_quarterly_tax,
        },
        {
            "name": "find_deductions",
            "description": "Scan expenses for potential tax deductions, identify commonly missed deductions, and suggest retirement contribution strategies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Tax year to analyze (defaults to current)"},
                },
            },
            "function": find_deductions,
        },
        {
            "name": "track_mileage",
            "description": "Track business mileage and calculate deduction using the IRS standard mileage rate ($0.67/mile for 2024).",
            "parameters": {
                "type": "object",
                "properties": {
                    "miles": {"type": "number", "description": "Miles driven (one-way unless round_trip=true)"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "purpose": {"type": "string", "description": "Business purpose of the trip"},
                    "destination": {"type": "string", "description": "Destination"},
                    "round_trip": {"type": "boolean", "description": "If true, miles are doubled"},
                },
                "required": ["miles"],
            },
            "function": track_mileage,
        },
        {
            "name": "track_1099",
            "description": "Track 1099 forms received (1099-NEC, 1099-MISC, 1099-K). Maintains payer records and withholding totals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "payer": {"type": "string", "description": "Name of the payer/company"},
                    "amount": {"type": "number", "description": "Amount reported on the 1099"},
                    "form_type": {"type": "string", "enum": ["1099-NEC", "1099-MISC", "1099-K"], "description": "Type of 1099 form"},
                    "ein": {"type": "string", "description": "Payer's EIN (optional)"},
                    "date_received": {"type": "string", "description": "Date received (YYYY-MM-DD)"},
                    "tax_withheld": {"type": "number", "description": "Federal tax withheld"},
                },
                "required": ["payer", "amount"],
            },
            "function": track_1099,
        },
        {
            "name": "generate_balance_sheet",
            "description": "Generate a balance sheet showing assets, liabilities, and equity as of a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "as_of_date": {"type": "string", "description": "Date for the balance sheet (YYYY-MM-DD, defaults to today)"},
                },
            },
            "function": generate_balance_sheet,
        },
        {
            "name": "analyze_cash_flow",
            "description": "Analyze cash flow patterns — monthly inflows vs outflows, burn rate, runway, and trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["month", "quarter", "year"], "description": "Analysis period"},
                    "year": {"type": "integer", "description": "Year to analyze"},
                    "month": {"type": "integer", "description": "Month number (if period is month)"},
                },
            },
            "function": analyze_cash_flow,
        },
        {
            "name": "year_end_tax_summary",
            "description": "Comprehensive year-end tax summary: income, expenses, deductions, mileage, 1099s, quarterly breakdown, and estimated tax liability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Tax year (defaults to current)"},
                    "filing_status": {"type": "string", "enum": ["single", "married"], "description": "Filing status"},
                },
            },
            "function": year_end_tax_summary,
        },
        {
            "name": "create_invoice",
            "description": "Create a professional invoice with line items, tax calculation, and due date tracking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client": {"type": "string", "description": "Client name"},
                    "items": {
                        "type": "array",
                        "description": "Line items: [{description, quantity, unit_price}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit_price": {"type": "number"},
                            },
                        },
                    },
                    "invoice_number": {"type": "string", "description": "Custom invoice number (auto-generated if empty)"},
                    "due_days": {"type": "integer", "description": "Payment terms in days (default 30)"},
                    "notes": {"type": "string", "description": "Additional notes"},
                    "tax_rate": {"type": "number", "description": "Tax rate as decimal (e.g. 0.08 for 8%). Auto-looked up from state if 0."},
                    "state": {"type": "string", "description": "State code for auto sales tax lookup"},
                },
                "required": ["client", "items"],
            },
            "function": create_invoice,
        },
        {
            "name": "calculate_sales_tax",
            "description": "Calculate sales tax for any US state, with optional city and county rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Pre-tax amount"},
                    "state": {"type": "string", "description": "Two-letter state code (e.g. CA, TX, NY)"},
                    "city_rate": {"type": "number", "description": "Additional city tax rate as decimal"},
                    "county_rate": {"type": "number", "description": "Additional county tax rate as decimal"},
                    "exempt": {"type": "boolean", "description": "Whether the sale is tax-exempt"},
                },
                "required": ["amount", "state"],
            },
            "function": calculate_sales_tax,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())
