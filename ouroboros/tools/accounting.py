"""Ouroboros — Accounting tools. Double-entry bookkeeping, financial statements, AR/AP, depreciation."""
from __future__ import annotations
import json, os
from datetime import datetime, timedelta
from typing import Any, Dict
from ouroboros.tools._adapter import adapt_tools

WORKSPACE = "/tmp/ouroboros_accounting"
LEDGER_PATH = os.path.join(WORKSPACE, "ledger.json")

def _ensure(): os.makedirs(WORKSPACE, exist_ok=True)

def _load() -> Dict[str, Any]:
    _ensure()
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH) as f: return json.load(f)
    return {"accounts": {}, "journal": [], "invoices": [], "bills": [],
            "bank_statements": [], "created": datetime.now().isoformat()}

def _save(d: Dict[str, Any]):
    _ensure()
    with open(LEDGER_PATH, "w") as f: json.dump(d, f, indent=2, default=str)

DEFAULT_COA = {
    "1000": {"name": "Cash", "type": "asset", "balance": 0},
    "1100": {"name": "Accounts Receivable", "type": "asset", "balance": 0},
    "1200": {"name": "Inventory", "type": "asset", "balance": 0},
    "1500": {"name": "Fixed Assets", "type": "asset", "balance": 0},
    "1510": {"name": "Accum. Depreciation", "type": "asset", "balance": 0},
    "2000": {"name": "Accounts Payable", "type": "liability", "balance": 0},
    "2100": {"name": "Notes Payable", "type": "liability", "balance": 0},
    "3000": {"name": "Owner's Equity", "type": "equity", "balance": 0},
    "3100": {"name": "Retained Earnings", "type": "equity", "balance": 0},
    "4000": {"name": "Revenue", "type": "revenue", "balance": 0},
    "4100": {"name": "Service Revenue", "type": "revenue", "balance": 0},
    "5000": {"name": "COGS", "type": "expense", "balance": 0},
    "6000": {"name": "Operating Expenses", "type": "expense", "balance": 0},
    "6100": {"name": "Rent Expense", "type": "expense", "balance": 0},
    "6200": {"name": "Utilities Expense", "type": "expense", "balance": 0},
    "6300": {"name": "Depreciation Expense", "type": "expense", "balance": 0},
}

def _init_coa(data):
    if not data["accounts"]:
        data["accounts"] = {k: dict(v) for k, v in DEFAULT_COA.items()}
        _save(data)

def chart_of_accounts(action="list", code="", name="", account_type="asset"):
    data = _load()
    _init_coa(data)
    if action == "init":
        data["accounts"] = {k: dict(v) for k, v in DEFAULT_COA.items()}
        _save(data)
        return {"status": "initialized", "count": len(data["accounts"])}
    if action == "add" and code:
        data["accounts"][code] = {"name": name, "type": account_type, "balance": 0}
        _save(data)
        return {"status": "added", "code": code}
    if action == "delete" and code:
        data["accounts"].pop(code, None); _save(data)
        return {"status": "deleted", "code": code}
    grouped = {}
    for c, a in data["accounts"].items():
        grouped.setdefault(a["type"], []).append({"code": c, **a})
    return {"accounts": grouped}

def journal_entry(date="", description="", debits="[]", credits="[]"):
    data = _load(); _init_coa(data)
    d_list = json.loads(debits) if isinstance(debits, str) else debits
    c_list = json.loads(credits) if isinstance(credits, str) else credits
    total_d = sum(e["amount"] for e in d_list)
    total_c = sum(e["amount"] for e in c_list)
    if abs(total_d - total_c) > 0.005:
        return {"error": f"Debits ({total_d}) != Credits ({total_c})"}
    entry = {"id": len(data["journal"]) + 1, "date": date or datetime.now().strftime("%Y-%m-%d"),
             "description": description, "debits": d_list, "credits": c_list}
    for e in d_list:
        acct = data["accounts"].get(e["account"])
        if acct:
            acct["balance"] += e["amount"] if acct["type"] in ("asset", "expense") else -e["amount"]
    for e in c_list:
        acct = data["accounts"].get(e["account"])
        if acct:
            acct["balance"] += -e["amount"] if acct["type"] in ("asset", "expense") else e["amount"]
    data["journal"].append(entry); _save(data)
    return {"status": "recorded", "entry": entry}

def trial_balance():
    data = _load()
    rows, total_d, total_c = [], 0.0, 0.0
    for code, acct in sorted(data.get("accounts", {}).items()):
        b = acct["balance"]
        if acct["type"] in ("liability", "equity", "revenue"):
            dr, cr = (abs(b), 0) if b < 0 else (0, b)
        else:
            dr, cr = (b, 0) if b >= 0 else (0, abs(b))
        rows.append({"code": code, "name": acct["name"], "debit": dr, "credit": cr})
        total_d += dr; total_c += cr
    return {"rows": rows, "total_debit": round(total_d, 2),
            "total_credit": round(total_c, 2), "balanced": abs(total_d - total_c) < 0.01}

def income_statement(period_start="", period_end=""):
    data = _load()
    accts = data.get("accounts", {})
    revenue = sum(a["balance"] for a in accts.values() if a["type"] == "revenue")
    cogs = sum(a["balance"] for a in accts.values() if a["name"] == "COGS")
    expenses = sum(a["balance"] for a in accts.values() if a["type"] == "expense" and a["name"] != "COGS")
    gross = revenue - cogs; net = gross - expenses
    return {"period": {"start": period_start, "end": period_end}, "revenue": round(revenue, 2),
            "cogs": round(cogs, 2), "gross_profit": round(gross, 2),
            "operating_expenses": round(expenses, 2), "net_income": round(net, 2)}

def balance_sheet_report():
    data = _load()
    accts = data.get("accounts", {})
    assets = {c: a for c, a in accts.items() if a["type"] == "asset"}
    liabilities = {c: a for c, a in accts.items() if a["type"] == "liability"}
    equity = {c: a for c, a in accts.items() if a["type"] == "equity"}
    ta = sum(a["balance"] for a in assets.values())
    tl = sum(a["balance"] for a in liabilities.values())
    te = sum(a["balance"] for a in equity.values())
    rev = sum(a["balance"] for a in accts.values() if a["type"] == "revenue")
    exp = sum(a["balance"] for a in accts.values() if a["type"] == "expense")
    ni = rev - exp
    return {"assets": {c: {"name": a["name"], "balance": a["balance"]} for c, a in assets.items()},
            "total_assets": round(ta, 2),
            "liabilities": {c: {"name": a["name"], "balance": a["balance"]} for c, a in liabilities.items()},
            "total_liabilities": round(tl, 2),
            "equity": {c: {"name": a["name"], "balance": a["balance"]} for c, a in equity.items()},
            "net_income": round(ni, 2), "total_equity": round(te + ni, 2),
            "total_liabilities_equity": round(tl + te + ni, 2),
            "balanced": abs(ta - (tl + te + ni)) < 0.01}

def accounts_receivable(action="list", invoice_id="", customer="",
                        amount=0.0, due_date="", payment_amount=0.0):
    data = _load()
    if action == "create":
        inv = {"id": invoice_id or f"INV-{len(data['invoices'])+1:04d}", "customer": customer,
               "amount": amount, "paid": 0, "status": "open", "created": datetime.now().isoformat(),
               "due_date": due_date or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")}
        data["invoices"].append(inv); _save(data)
        return {"status": "created", "invoice": inv}
    if action == "payment":
        for inv in data["invoices"]:
            if inv["id"] == invoice_id:
                inv["paid"] += payment_amount
                inv["status"] = "paid" if inv["paid"] >= inv["amount"] else "partial"
                _save(data); return {"status": "payment_recorded", "invoice": inv}
        return {"error": "Invoice not found"}
    if action == "aging":
        today = datetime.now()
        buckets = {"current": [], "30": [], "60": [], "90": [], "over_90": []}
        for inv in data["invoices"]:
            if inv["status"] == "paid": continue
            days = (today - datetime.strptime(inv["due_date"], "%Y-%m-%d")).days
            rem = inv["amount"] - inv["paid"]
            rec = {"id": inv["id"], "customer": inv["customer"], "remaining": rem, "days_overdue": max(days, 0)}
            key = "current" if days <= 0 else "30" if days <= 30 else "60" if days <= 60 else "90" if days <= 90 else "over_90"
            buckets[key].append(rec)
        return {"aging": buckets, "totals": {k: sum(r["remaining"] for r in v) for k, v in buckets.items()}}
    return {"invoices": data["invoices"]}

def accounts_payable(action="list", bill_id="", vendor="",
                     amount=0.0, due_date="", payment_amount=0.0):
    data = _load()
    if action == "create":
        bill = {"id": bill_id or f"BILL-{len(data['bills'])+1:04d}", "vendor": vendor,
                "amount": amount, "paid": 0, "status": "unpaid", "created": datetime.now().isoformat(),
                "due_date": due_date or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")}
        data["bills"].append(bill); _save(data)
        return {"status": "created", "bill": bill}
    if action == "payment":
        for bill in data["bills"]:
            if bill["id"] == bill_id:
                bill["paid"] += payment_amount
                bill["status"] = "paid" if bill["paid"] >= bill["amount"] else "partial"
                _save(data); return {"status": "payment_recorded", "bill": bill}
        return {"error": "Bill not found"}
    if action == "schedule":
        upcoming = []
        for bill in data["bills"]:
            if bill["status"] != "paid":
                days = (datetime.strptime(bill["due_date"], "%Y-%m-%d") - datetime.now()).days
                upcoming.append({"id": bill["id"], "vendor": bill["vendor"],
                                 "remaining": bill["amount"] - bill["paid"],
                                 "due_date": bill["due_date"], "days_until_due": days})
        return {"schedule": sorted(upcoming, key=lambda x: x["days_until_due"])}
    return {"bills": data["bills"]}

def bank_reconciliation(action="status", bank_balance=0.0, statement_items="[]"):
    data = _load()
    book_balance = data.get("accounts", {}).get("1000", {}).get("balance", 0)
    if action == "reconcile":
        items = json.loads(statement_items) if isinstance(statement_items, str) else statement_items
        matched, unmatched_bank = [], []
        journal_amts = {}
        for je in data.get("journal", []):
            for d in je.get("debits", []):
                if d["account"] == "1000":
                    journal_amts.setdefault(d["amount"], []).append({"type": "debit", "entry": je["id"]})
            for c in je.get("credits", []):
                if c["account"] == "1000":
                    journal_amts.setdefault(c["amount"], []).append({"type": "credit", "entry": je["id"]})
        for item in items:
            amt = abs(item.get("amount", 0))
            if amt in journal_amts and journal_amts[amt]:
                matched.append({**item, "matched_entry": journal_amts[amt].pop(0)})
            else:
                unmatched_bank.append(item)
        diff = bank_balance - book_balance
        return {"bank_balance": bank_balance, "book_balance": round(book_balance, 2),
                "difference": round(diff, 2), "matched": len(matched),
                "unmatched_bank": unmatched_bank, "reconciled": abs(diff) < 0.01}
    return {"book_balance": round(book_balance, 2), "journal_entries": len(data.get("journal", []))}

def depreciation_calculator(asset_cost=0.0, salvage_value=0.0, useful_life=5,
                            method="straight_line", year=1):
    schedule, accum = [], 0
    if method == "straight_line":
        annual = (asset_cost - salvage_value) / useful_life if useful_life else 0
        for y in range(1, useful_life + 1):
            accum += annual
            schedule.append({"year": y, "depreciation": round(annual, 2),
                             "accumulated": round(accum, 2), "book_value": round(asset_cost - accum, 2)})
    elif method == "declining_balance":
        rate, bv = (2.0 / useful_life if useful_life else 0), asset_cost
        for y in range(1, useful_life + 1):
            dep = min(bv * rate, bv - salvage_value)
            accum += dep; bv -= dep
            schedule.append({"year": y, "depreciation": round(dep, 2),
                             "accumulated": round(accum, 2), "book_value": round(bv, 2)})
    elif method == "macrs":
        rates = ([0.20, 0.32, 0.192, 0.1152, 0.1152, 0.0576] if useful_life <= 5
                 else [0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 0.0892, 0.0893, 0.0446])
        for y, r in enumerate(rates, 1):
            dep = asset_cost * r; accum += dep
            schedule.append({"year": y, "depreciation": round(dep, 2),
                             "accumulated": round(accum, 2), "book_value": round(asset_cost - accum, 2)})
    current = schedule[year - 1] if 0 < year <= len(schedule) else None
    return {"method": method, "asset_cost": asset_cost, "salvage_value": salvage_value,
            "useful_life": useful_life, "current_year": current, "schedule": schedule}

def financial_ratios():
    data = _load()
    accts = data.get("accounts", {})
    cash = accts.get("1000", {}).get("balance", 0)
    ar = accts.get("1100", {}).get("balance", 0)
    inv = accts.get("1200", {}).get("balance", 0)
    ta = sum(a["balance"] for a in accts.values() if a["type"] == "asset")
    tl = sum(a["balance"] for a in accts.values() if a["type"] == "liability")
    te = sum(a["balance"] for a in accts.values() if a["type"] == "equity")
    rev = sum(a["balance"] for a in accts.values() if a["type"] == "revenue")
    exp = sum(a["balance"] for a in accts.values() if a["type"] == "expense")
    ni, ca, cl = rev - exp, cash + ar + inv, accts.get("2000", {}).get("balance", 0)
    sd = lambda a, b: round(a / b, 4) if b else None
    return {"current_ratio": sd(ca, cl), "quick_ratio": sd(cash + ar, cl),
            "debt_to_equity": sd(tl, te) if te else None, "profit_margin": sd(ni, rev),
            "roe": sd(ni, te), "roa": sd(ni, ta),
            "components": {"current_assets": round(ca, 2), "current_liabilities": round(cl, 2),
                           "total_assets": round(ta, 2), "total_liabilities": round(tl, 2),
                           "total_equity": round(te, 2), "revenue": round(rev, 2), "net_income": round(ni, 2)}}

_P = lambda **kw: {"type": "object", "properties": kw}
_S, _N, _I = {"type": "string"}, {"type": "number"}, {"type": "integer"}

def _raw_tools():
    acct_types = ["asset", "liability", "equity", "revenue", "expense"]
    return [
        {"name": "chart_of_accounts", "description": "Manage chart of accounts. Actions: list, init, add, delete.",
         "parameters": _P(action={"type": "string", "enum": ["list", "init", "add", "delete"], "default": "list"},
                          code=_S, name=_S, account_type={"type": "string", "enum": acct_types}),
         "function": chart_of_accounts},
        {"name": "journal_entry", "description": "Record double-entry journal entry. Debits/credits as JSON arrays of {account, amount}.",
         "parameters": {**_P(date=_S, description=_S, debits=_S, credits=_S), "required": ["debits", "credits"]},
         "function": journal_entry},
        {"name": "trial_balance", "description": "Generate trial balance from all journal entries.",
         "parameters": _P(), "function": trial_balance},
        {"name": "income_statement", "description": "Generate income statement (revenue - COGS - expenses = net income).",
         "parameters": _P(period_start=_S, period_end=_S), "function": income_statement},
        {"name": "balance_sheet_report", "description": "Full balance sheet (assets = liabilities + equity).",
         "parameters": _P(), "function": balance_sheet_report},
        {"name": "accounts_receivable", "description": "Track invoices/payments with aging (30/60/90 days). Actions: list, create, payment, aging.",
         "parameters": _P(action={"type": "string", "enum": ["list", "create", "payment", "aging"], "default": "list"},
                          invoice_id=_S, customer=_S, amount=_N, due_date=_S, payment_amount=_N),
         "function": accounts_receivable},
        {"name": "accounts_payable", "description": "Track bills, due dates, payment scheduling. Actions: list, create, payment, schedule.",
         "parameters": _P(action={"type": "string", "enum": ["list", "create", "payment", "schedule"], "default": "list"},
                          bill_id=_S, vendor=_S, amount=_N, due_date=_S, payment_amount=_N),
         "function": accounts_payable},
        {"name": "bank_reconciliation", "description": "Reconcile bank statement against books. Actions: status, reconcile.",
         "parameters": _P(action={"type": "string", "enum": ["status", "reconcile"], "default": "status"},
                          bank_balance=_N, statement_items=_S),
         "function": bank_reconciliation},
        {"name": "depreciation_calculator", "description": "Calculate depreciation (straight_line, declining_balance, macrs).",
         "parameters": {**_P(asset_cost=_N, salvage_value=_N, useful_life={**_I, "default": 5},
                             method={"type": "string", "enum": ["straight_line", "declining_balance", "macrs"]},
                             year={**_I, "default": 1}), "required": ["asset_cost"]},
         "function": depreciation_calculator},
        {"name": "financial_ratios", "description": "Calculate key ratios: current, quick, debt-to-equity, profit margin, ROE, ROA.",
         "parameters": _P(), "function": financial_ratios},
    ]

def get_tools():
    return adapt_tools(_raw_tools())
