"""
Ouroboros — Invoice & financial management tools.

Invoice generator, payment tracker, expense categorizer,
profit/loss calculator, tax estimator.
"""

from __future__ import annotations

import json
import logging
import os
import textwrap
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_invoice")
INVOICES_PATH = os.path.join(WORKSPACE, "invoices.json")
PAYMENTS_PATH = os.path.join(WORKSPACE, "payments.json")
EXPENSES_PATH = os.path.join(WORKSPACE, "expenses.json")


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


def _load_json(path: str) -> Any:
    _ensure_workspace()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _save_json(path: str, data: Any):
    _ensure_workspace()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Invoice Generator ────────────────────────────────────────────────────

def invoice_generator(action: str = "create",
                      client_name: str = "",
                      client_email: str = "",
                      items: List[Dict[str, Any]] = None,
                      currency: str = "USD",
                      tax_rate: float = 0.0,
                      due_days: int = 30,
                      notes: str = "",
                      invoice_id: int = 0,
                      from_name: str = "",
                      from_email: str = "",
                      from_address: str = "") -> Dict[str, Any]:
    """Generate, list, or view invoices."""
    invoices = _load_json(INVOICES_PATH) or {"invoices": [], "next_id": 1001}

    if action == "create":
        if not client_name or not items:
            return {"error": "client_name and items are required"}

        # Calculate totals
        line_items = []
        subtotal = 0
        for item in items:
            qty = item.get("quantity", 1)
            rate = item.get("rate", 0)
            amount = qty * rate
            subtotal += amount
            line_items.append({
                "description": item.get("description", "Service"),
                "quantity": qty,
                "rate": rate,
                "amount": round(amount, 2),
            })

        tax_amount = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax_amount, 2)

        inv_id = invoices["next_id"]
        invoices["next_id"] += 1

        invoice = {
            "id": inv_id,
            "invoice_number": f"INV-{inv_id}",
            "status": "draft",
            "created": datetime.now().isoformat(),
            "due_date": (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d"),
            "from": {
                "name": from_name or "[Your Name/Company]",
                "email": from_email or "[your@email.com]",
                "address": from_address or "[Your Address]",
            },
            "to": {
                "name": client_name,
                "email": client_email,
            },
            "items": line_items,
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "total": total,
            "currency": currency,
            "notes": notes,
            "paid_amount": 0,
        }

        invoices["invoices"].append(invoice)
        _save_json(INVOICES_PATH, invoices)

        # Generate text representation
        text = _render_invoice_text(invoice)

        # Save text file
        text_path = os.path.join(WORKSPACE, f"INV-{inv_id}.txt")
        with open(text_path, "w") as f:
            f.write(text)

        return {
            "action": "created",
            "invoice": invoice,
            "text_file": text_path,
            "text_preview": text,
        }

    elif action == "list":
        summary = []
        for inv in invoices["invoices"]:
            summary.append({
                "id": inv["id"],
                "number": inv["invoice_number"],
                "client": inv["to"]["name"],
                "total": inv["total"],
                "currency": inv["currency"],
                "status": inv["status"],
                "due_date": inv["due_date"],
                "paid": inv.get("paid_amount", 0),
            })
        return {"invoices": summary, "count": len(summary)}

    elif action == "view":
        inv = next((i for i in invoices["invoices"] if i["id"] == invoice_id), None)
        if not inv:
            return {"error": f"Invoice not found: {invoice_id}"}
        return {"invoice": inv, "text": _render_invoice_text(inv)}

    elif action == "mark_paid":
        inv = next((i for i in invoices["invoices"] if i["id"] == invoice_id), None)
        if not inv:
            return {"error": f"Invoice not found: {invoice_id}"}
        inv["status"] = "paid"
        inv["paid_amount"] = inv["total"]
        inv["paid_date"] = datetime.now().isoformat()
        _save_json(INVOICES_PATH, invoices)
        return {"action": "marked_paid", "invoice_number": inv["invoice_number"], "total": inv["total"]}

    elif action == "mark_sent":
        inv = next((i for i in invoices["invoices"] if i["id"] == invoice_id), None)
        if not inv:
            return {"error": f"Invoice not found: {invoice_id}"}
        inv["status"] = "sent"
        inv["sent_date"] = datetime.now().isoformat()
        _save_json(INVOICES_PATH, invoices)
        return {"action": "marked_sent", "invoice_number": inv["invoice_number"]}

    elif action == "overdue":
        today = datetime.now().strftime("%Y-%m-%d")
        overdue = [
            {
                "number": inv["invoice_number"],
                "client": inv["to"]["name"],
                "total": inv["total"],
                "due_date": inv["due_date"],
                "days_overdue": (datetime.now() - datetime.strptime(inv["due_date"], "%Y-%m-%d")).days,
            }
            for inv in invoices["invoices"]
            if inv["status"] not in ("paid", "cancelled") and inv["due_date"] < today
        ]
        return {"overdue_invoices": overdue, "count": len(overdue)}

    return {"error": f"Unknown action: {action}"}


def _render_invoice_text(invoice: Dict[str, Any]) -> str:
    """Render invoice as formatted text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  INVOICE {invoice['invoice_number']}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  From: {invoice['from']['name']}")
    lines.append(f"        {invoice['from']['email']}")
    if invoice['from'].get('address'):
        lines.append(f"        {invoice['from']['address']}")
    lines.append("")
    lines.append(f"  To:   {invoice['to']['name']}")
    if invoice['to'].get('email'):
        lines.append(f"        {invoice['to']['email']}")
    lines.append("")
    lines.append(f"  Date:    {invoice['created'][:10]}")
    lines.append(f"  Due:     {invoice['due_date']}")
    lines.append(f"  Status:  {invoice['status'].upper()}")
    lines.append("")
    lines.append("-" * 60)
    lines.append(f"  {'Description':<30} {'Qty':>5} {'Rate':>10} {'Amount':>10}")
    lines.append("-" * 60)

    for item in invoice["items"]:
        lines.append(f"  {item['description']:<30} {item['quantity']:>5} {item['rate']:>10.2f} {item['amount']:>10.2f}")

    lines.append("-" * 60)
    lines.append(f"  {'Subtotal':>47} {invoice['subtotal']:>10.2f}")

    if invoice["tax_rate"] > 0:
        lines.append(f"  {'Tax (' + str(round(invoice['tax_rate'] * 100, 1)) + '%)':>47} {invoice['tax_amount']:>10.2f}")

    lines.append(f"  {'TOTAL (' + invoice['currency'] + ')':>47} {invoice['total']:>10.2f}")
    lines.append("=" * 60)

    if invoice.get("notes"):
        lines.append("")
        lines.append(f"  Notes: {invoice['notes']}")

    lines.append("")
    return "\n".join(lines)


# ── Payment Tracker ──────────────────────────────────────────────────────

def payment_tracker(action: str, amount: float = 0,
                    source: str = "", description: str = "",
                    payment_type: str = "income",
                    category: str = "general",
                    payment_id: int = 0) -> Dict[str, Any]:
    """Track payments: record income/expenses, view history, get summary."""
    payments = _load_json(PAYMENTS_PATH) or {"payments": [], "next_id": 1}

    if action == "record":
        if amount <= 0:
            return {"error": "amount must be positive"}
        payment = {
            "id": payments["next_id"],
            "amount": amount,
            "type": payment_type,
            "source": source,
            "description": description,
            "category": category,
            "date": datetime.now().isoformat(),
        }
        payments["next_id"] += 1
        payments["payments"].append(payment)
        _save_json(PAYMENTS_PATH, payments)
        return {"action": "recorded", "payment": payment}

    elif action == "list":
        recent = payments["payments"][-50:]  # Last 50
        if category != "general":
            recent = [p for p in recent if p.get("category") == category]
        return {"payments": recent, "count": len(recent)}

    elif action == "summary":
        total_income = sum(p["amount"] for p in payments["payments"] if p["type"] == "income")
        total_expenses = sum(p["amount"] for p in payments["payments"] if p["type"] == "expense")

        # By category
        by_category = {}
        for p in payments["payments"]:
            cat = p.get("category", "general")
            if cat not in by_category:
                by_category[cat] = {"income": 0, "expense": 0, "count": 0}
            by_category[cat][p["type"]] = by_category[cat].get(p["type"], 0) + p["amount"]
            by_category[cat]["count"] += 1

        # Monthly breakdown
        by_month = {}
        for p in payments["payments"]:
            month = p["date"][:7]  # YYYY-MM
            if month not in by_month:
                by_month[month] = {"income": 0, "expense": 0}
            by_month[month][p["type"]] = by_month[month].get(p["type"], 0) + p["amount"]

        return {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net": round(total_income - total_expenses, 2),
            "transaction_count": len(payments["payments"]),
            "by_category": by_category,
            "by_month": dict(sorted(by_month.items())),
        }

    elif action == "delete":
        payments["payments"] = [p for p in payments["payments"] if p["id"] != payment_id]
        _save_json(PAYMENTS_PATH, payments)
        return {"action": "deleted", "payment_id": payment_id}

    return {"error": f"Unknown action: {action}"}


# ── Expense Categorizer ─────────────────────────────────────────────────

EXPENSE_CATEGORIES = {
    "software": ["saas", "subscription", "software", "tool", "app", "cloud", "hosting", "domain", "api"],
    "marketing": ["ads", "advertising", "marketing", "seo", "social", "campaign", "google ads", "facebook"],
    "office": ["rent", "office", "supplies", "furniture", "equipment", "internet", "phone"],
    "travel": ["flight", "hotel", "airbnb", "uber", "lyft", "taxi", "gas", "parking", "travel"],
    "food": ["restaurant", "coffee", "lunch", "dinner", "meal", "food", "catering"],
    "payroll": ["salary", "wage", "contractor", "freelancer", "payroll", "bonus", "commission"],
    "legal": ["legal", "lawyer", "attorney", "accounting", "accountant", "cpa", "compliance"],
    "insurance": ["insurance", "health", "liability", "coverage", "premium"],
    "taxes": ["tax", "irs", "state tax", "sales tax", "vat"],
    "education": ["course", "training", "book", "conference", "workshop", "seminar"],
    "utilities": ["electric", "water", "gas", "internet", "phone", "utility"],
}


def expense_categorizer(description: str, amount: float = 0,
                        suggest_only: bool = False) -> Dict[str, Any]:
    """Auto-categorize expenses based on description."""
    desc_lower = description.lower()
    scores = {}

    for category, keywords in EXPENSE_CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in desc_lower)
        if score > 0:
            scores[category] = score

    if scores:
        best_category = max(scores, key=scores.get)
        confidence = min(scores[best_category] / 3, 1.0)
    else:
        best_category = "general"
        confidence = 0.0

    result = {
        "description": description,
        "suggested_category": best_category,
        "confidence": round(confidence, 2),
        "all_scores": scores,
        "is_tax_deductible": best_category in ("software", "marketing", "office", "travel", "education", "legal", "insurance"),
    }

    if not suggest_only and amount > 0:
        # Auto-record the expense
        record = payment_tracker(
            "record", amount=amount, description=description,
            payment_type="expense", category=best_category,
        )
        result["recorded"] = record

    return result


# ── Profit/Loss Calculator ──────────────────────────────────────────────

def profit_loss(period: str = "all",
                start_date: str = "",
                end_date: str = "") -> Dict[str, Any]:
    """Calculate profit and loss statement."""
    payments = _load_json(PAYMENTS_PATH) or {"payments": []}
    all_payments = payments["payments"]

    # Filter by period
    if start_date:
        all_payments = [p for p in all_payments if p["date"][:10] >= start_date]
    if end_date:
        all_payments = [p for p in all_payments if p["date"][:10] <= end_date]

    if period == "month":
        current_month = datetime.now().strftime("%Y-%m")
        all_payments = [p for p in all_payments if p["date"][:7] == current_month]
    elif period == "quarter":
        now = datetime.now()
        q_start_month = ((now.month - 1) // 3) * 3 + 1
        q_start = now.replace(month=q_start_month, day=1).strftime("%Y-%m-%d")
        all_payments = [p for p in all_payments if p["date"][:10] >= q_start]
    elif period == "year":
        current_year = datetime.now().strftime("%Y")
        all_payments = [p for p in all_payments if p["date"][:4] == current_year]

    # Revenue breakdown
    revenue_by_source = {}
    total_revenue = 0
    for p in all_payments:
        if p["type"] == "income":
            total_revenue += p["amount"]
            source = p.get("source") or p.get("category", "general")
            revenue_by_source[source] = revenue_by_source.get(source, 0) + p["amount"]

    # Expense breakdown
    expense_by_category = {}
    total_expenses = 0
    for p in all_payments:
        if p["type"] == "expense":
            total_expenses += p["amount"]
            cat = p.get("category", "general")
            expense_by_category[cat] = expense_by_category.get(cat, 0) + p["amount"]

    net_profit = total_revenue - total_expenses
    margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

    return {
        "period": period,
        "start_date": start_date or "all time",
        "end_date": end_date or "current",
        "revenue": {
            "total": round(total_revenue, 2),
            "by_source": {k: round(v, 2) for k, v in sorted(revenue_by_source.items(), key=lambda x: -x[1])},
        },
        "expenses": {
            "total": round(total_expenses, 2),
            "by_category": {k: round(v, 2) for k, v in sorted(expense_by_category.items(), key=lambda x: -x[1])},
        },
        "net_profit": round(net_profit, 2),
        "profit_margin_pct": round(margin, 1),
        "transaction_count": len(all_payments),
        "status": "profitable" if net_profit > 0 else ("break_even" if net_profit == 0 else "loss"),
    }


# ── Tax Estimator ────────────────────────────────────────────────────────

def tax_estimator(annual_income: float, filing_status: str = "single",
                  deductions: float = 0, state: str = "",
                  self_employed: bool = True) -> Dict[str, Any]:
    """Estimate US federal tax liability (simplified)."""
    # 2024 Federal tax brackets (simplified)
    brackets = {
        "single": [
            (11600, 0.10),
            (47150, 0.12),
            (100525, 0.22),
            (191950, 0.24),
            (243725, 0.32),
            (609350, 0.35),
            (float('inf'), 0.37),
        ],
        "married": [
            (23200, 0.10),
            (94300, 0.12),
            (201050, 0.22),
            (383900, 0.24),
            (487450, 0.32),
            (731200, 0.35),
            (float('inf'), 0.37),
        ],
    }

    # Standard deduction
    standard_deduction = {"single": 14600, "married": 29200, "head_of_household": 21900}
    std_ded = standard_deduction.get(filing_status, 14600)
    actual_deduction = max(deductions, std_ded)

    taxable_income = max(0, annual_income - actual_deduction)

    # Calculate federal tax
    tax_brackets = brackets.get(filing_status, brackets["single"])
    federal_tax = 0
    remaining = taxable_income
    prev_limit = 0
    bracket_breakdown = []

    for limit, rate in tax_brackets:
        bracket_income = min(remaining, limit - prev_limit)
        if bracket_income <= 0:
            break
        bracket_tax = bracket_income * rate
        federal_tax += bracket_tax
        bracket_breakdown.append({
            "bracket": f"{rate*100:.0f}%",
            "income_in_bracket": round(bracket_income, 2),
            "tax": round(bracket_tax, 2),
        })
        remaining -= bracket_income
        prev_limit = limit

    # Self-employment tax (Social Security + Medicare)
    se_tax = 0
    if self_employed:
        se_income = annual_income * 0.9235  # 92.35% of net SE income
        ss_tax = min(se_income, 168600) * 0.124  # Social Security (6.2% x2)
        medicare_tax = se_income * 0.029  # Medicare (1.45% x2)
        additional_medicare = max(0, se_income - 200000) * 0.009  # Additional Medicare
        se_tax = ss_tax + medicare_tax + additional_medicare

    # State tax estimate (simplified flat rates)
    state_rates = {
        "CA": 0.093, "NY": 0.0685, "TX": 0, "FL": 0, "WA": 0,
        "IL": 0.0495, "PA": 0.0307, "OH": 0.04, "GA": 0.055,
        "NC": 0.0525, "NJ": 0.0637, "VA": 0.0575, "MA": 0.05,
        "CO": 0.044, "OR": 0.099, "NV": 0, "TN": 0, "WY": 0,
    }
    state_rate = state_rates.get(state.upper(), 0.05) if state else 0
    state_tax = taxable_income * state_rate if state else 0

    total_tax = federal_tax + se_tax + state_tax
    effective_rate = (total_tax / annual_income * 100) if annual_income > 0 else 0
    quarterly_estimate = total_tax / 4

    return {
        "annual_income": annual_income,
        "filing_status": filing_status,
        "deduction_used": round(actual_deduction, 2),
        "deduction_type": "itemized" if deductions > std_ded else "standard",
        "taxable_income": round(taxable_income, 2),
        "federal_tax": round(federal_tax, 2),
        "bracket_breakdown": bracket_breakdown,
        "self_employment_tax": round(se_tax, 2) if self_employed else 0,
        "state_tax": round(state_tax, 2) if state else None,
        "state": state.upper() if state else "not specified",
        "total_estimated_tax": round(total_tax, 2),
        "effective_tax_rate": f"{effective_rate:.1f}%",
        "quarterly_payment": round(quarterly_estimate, 2),
        "take_home_estimate": round(annual_income - total_tax, 2),
        "disclaimer": "This is a simplified estimate. Consult a tax professional for accurate calculations.",
    }


# ── Raw tools ──────────────────────────────────────────────────────────────

def _raw_tools() -> list:
    return [
        {
            "name": "invoice_generator",
            "description": "Generate, list, view, and manage invoices. Creates formatted text invoices ready for PDF conversion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "list", "view", "mark_paid", "mark_sent", "overdue"], "default": "create"},
                    "client_name": {"type": "string", "default": ""},
                    "client_email": {"type": "string", "default": ""},
                    "items": {"type": "array", "items": {"type": "object"},
                              "description": "List of {description, quantity, rate}"},
                    "currency": {"type": "string", "default": "USD"},
                    "tax_rate": {"type": "number", "default": 0, "description": "Tax rate as decimal (0.1 = 10%)"},
                    "due_days": {"type": "integer", "default": 30},
                    "notes": {"type": "string", "default": ""},
                    "invoice_id": {"type": "integer", "default": 0, "description": "For view/mark_paid/mark_sent"},
                    "from_name": {"type": "string", "default": ""},
                    "from_email": {"type": "string", "default": ""},
                    "from_address": {"type": "string", "default": ""},
                },
            },
            "function": invoice_generator,
        },
        {
            "name": "payment_tracker",
            "description": "Track income and expenses with categories, view history, and get summaries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["record", "list", "summary", "delete"]},
                    "amount": {"type": "number", "default": 0},
                    "source": {"type": "string", "default": ""},
                    "description": {"type": "string", "default": ""},
                    "payment_type": {"type": "string", "enum": ["income", "expense"], "default": "income"},
                    "category": {"type": "string", "default": "general"},
                    "payment_id": {"type": "integer", "default": 0},
                },
                "required": ["action"],
            },
            "function": payment_tracker,
        },
        {
            "name": "expense_categorizer",
            "description": "Auto-categorize expenses and identify tax-deductible items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "Expense description to categorize"},
                    "amount": {"type": "number", "default": 0, "description": "If provided, auto-records the expense"},
                    "suggest_only": {"type": "boolean", "default": False},
                },
                "required": ["description"],
            },
            "function": expense_categorizer,
        },
        {
            "name": "profit_loss",
            "description": "Calculate profit & loss statement with revenue/expense breakdowns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["all", "month", "quarter", "year"], "default": "all"},
                    "start_date": {"type": "string", "default": "", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "default": "", "description": "YYYY-MM-DD"},
                },
            },
            "function": profit_loss,
        },
        {
            "name": "tax_estimator",
            "description": "Estimate US federal + state tax liability with bracket breakdown and quarterly payments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "annual_income": {"type": "number"},
                    "filing_status": {"type": "string", "enum": ["single", "married", "head_of_household"], "default": "single"},
                    "deductions": {"type": "number", "default": 0, "description": "Itemized deductions (0 = use standard)"},
                    "state": {"type": "string", "default": "", "description": "Two-letter state code (CA, NY, TX, etc)"},
                    "self_employed": {"type": "boolean", "default": True},
                },
                "required": ["annual_income"],
            },
            "function": tax_estimator,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())
