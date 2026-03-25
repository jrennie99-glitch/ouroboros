"""Ouroboros — Real Estate Investment tools."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List
from ouroboros.tools._adapter import adapt_tools


def _property_analyzer(purchase_price: float, monthly_rent: float, monthly_expenses: float,
                        down_payment_pct: float = 20.0, loan_rate: float = 7.0,
                        loan_term_years: int = 30, closing_costs: float = 0.0, **kw) -> Dict:
    down = purchase_price * down_payment_pct / 100
    loan = purchase_price - down
    r = loan_rate / 100 / 12
    n = loan_term_years * 12
    pmt = loan * (r * (1 + r) ** n) / ((1 + r) ** n - 1) if r > 0 else loan / n
    annual_rent = monthly_rent * 12
    annual_expenses = monthly_expenses * 12
    noi = annual_rent - annual_expenses
    cash_flow_monthly = monthly_rent - monthly_expenses - pmt
    total_invested = down + closing_costs
    cap_rate = (noi / purchase_price) * 100 if purchase_price else 0
    coc = (cash_flow_monthly * 12 / total_invested) * 100 if total_invested else 0
    roi = (noi / total_invested) * 100 if total_invested else 0
    grm = purchase_price / annual_rent if annual_rent else 0
    return {
        "purchase_price": purchase_price, "down_payment": down, "loan_amount": loan,
        "monthly_mortgage": round(pmt, 2), "monthly_cash_flow": round(cash_flow_monthly, 2),
        "annual_noi": round(noi, 2), "cap_rate": round(cap_rate, 2),
        "cash_on_cash_return": round(coc, 2), "roi": round(roi, 2),
        "gross_rent_multiplier": round(grm, 2), "total_invested": round(total_invested, 2),
        "verdict": "Good deal" if coc > 8 else "Marginal" if coc > 4 else "Poor deal"
    }


def _mortgage_calculator(principal: float, annual_rate: float = 7.0,
                          term_years: int = 30, show_schedule: bool = False, **kw) -> Dict:
    r = annual_rate / 100 / 12
    n = term_years * 12
    pmt = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1) if r > 0 else principal / n
    total_paid = pmt * n
    total_interest = total_paid - principal
    result: Dict[str, Any] = {
        "principal": principal, "rate": annual_rate, "term_years": term_years,
        "monthly_payment": round(pmt, 2), "total_paid": round(total_paid, 2),
        "total_interest": round(total_interest, 2),
    }
    if show_schedule:
        schedule = []
        balance = principal
        for yr in range(1, term_years + 1):
            yr_interest = 0
            yr_principal = 0
            for _ in range(12):
                mi = balance * r
                mp = pmt - mi
                yr_interest += mi
                yr_principal += mp
                balance -= mp
            schedule.append({"year": yr, "principal_paid": round(yr_principal, 2),
                             "interest_paid": round(yr_interest, 2), "balance": round(max(balance, 0), 2)})
        result["amortization"] = schedule
    return result


def _rental_income(area: str = "US Average", bedrooms: int = 3,
                    property_type: str = "single_family", **kw) -> Dict:
    base_rents = {
        "US Average": 1800, "New York": 3500, "San Francisco": 3800, "Los Angeles": 2900,
        "Chicago": 1700, "Houston": 1500, "Phoenix": 1600, "Dallas": 1700,
        "Atlanta": 1600, "Miami": 2400, "Denver": 2100, "Seattle": 2600,
        "Austin": 2000, "Nashville": 1900, "Charlotte": 1500, "Tampa": 1800,
    }
    base = base_rents.get(area, 1800)
    br_mult = {1: 0.6, 2: 0.85, 3: 1.0, 4: 1.25, 5: 1.45}
    type_mult = {"single_family": 1.0, "condo": 0.9, "townhouse": 0.95, "duplex": 1.1, "apartment": 0.85}
    rent = base * br_mult.get(bedrooms, 1.0) * type_mult.get(property_type, 1.0)
    vacancy = 0.08
    effective = rent * (1 - vacancy)
    return {
        "area": area, "bedrooms": bedrooms, "property_type": property_type,
        "estimated_monthly_rent": round(rent, 2), "vacancy_rate": f"{vacancy*100}%",
        "effective_monthly_income": round(effective, 2),
        "annual_gross": round(rent * 12, 2), "annual_effective": round(effective * 12, 2),
        "note": "Estimates based on market averages. Verify with local comps."
    }


def _property_comparison(properties: list, **kw) -> Dict:
    results = []
    for p in properties:
        analysis = _property_analyzer(
            purchase_price=p.get("purchase_price", 0), monthly_rent=p.get("monthly_rent", 0),
            monthly_expenses=p.get("monthly_expenses", 0),
            down_payment_pct=p.get("down_payment_pct", 20), loan_rate=p.get("loan_rate", 7.0),
        )
        analysis["address"] = p.get("address", "Unknown")
        results.append(analysis)
    ranked = sorted(results, key=lambda x: x["cash_on_cash_return"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    return {"comparison": ranked, "best_deal": ranked[0]["address"] if ranked else "N/A"}


def _rehab_estimator(rooms: list, scope: str = "moderate", sqft: int = 0, **kw) -> Dict:
    costs = {
        "kitchen": {"cosmetic": 8000, "moderate": 25000, "full_gut": 55000},
        "bathroom": {"cosmetic": 3000, "moderate": 12000, "full_gut": 28000},
        "bedroom": {"cosmetic": 1500, "moderate": 4000, "full_gut": 10000},
        "living_room": {"cosmetic": 2000, "moderate": 5000, "full_gut": 12000},
        "basement": {"cosmetic": 3000, "moderate": 15000, "full_gut": 40000},
        "roof": {"cosmetic": 2000, "moderate": 8000, "full_gut": 15000},
        "exterior": {"cosmetic": 3000, "moderate": 10000, "full_gut": 25000},
        "hvac": {"cosmetic": 500, "moderate": 5000, "full_gut": 12000},
        "plumbing": {"cosmetic": 1000, "moderate": 5000, "full_gut": 15000},
        "electrical": {"cosmetic": 800, "moderate": 4000, "full_gut": 12000},
        "flooring": {"cosmetic": 2000, "moderate": 6000, "full_gut": 14000},
    }
    breakdown = []
    total = 0
    for room in rooms:
        name = room if isinstance(room, str) else room.get("name", "unknown")
        s = room.get("scope", scope) if isinstance(room, dict) else scope
        cost = costs.get(name, {}).get(s, 5000)
        breakdown.append({"room": name, "scope": s, "estimated_cost": cost})
        total += cost
    contingency = round(total * 0.15, 2)
    return {
        "breakdown": breakdown, "subtotal": total,
        "contingency_15pct": contingency, "total_estimate": total + contingency,
        "scope": scope, "note": "Add 15-25% contingency for unknowns."
    }


def _market_analysis(market: str = "US National", property_type: str = "single_family", **kw) -> Dict:
    markets = {
        "US National": {"median": 420000, "yoy": 4.2, "dom": 35, "inv": 3.2},
        "New York": {"median": 750000, "yoy": 2.8, "dom": 55, "inv": 5.1},
        "San Francisco": {"median": 1200000, "yoy": 1.5, "dom": 28, "inv": 2.8},
        "Austin": {"median": 450000, "yoy": -1.2, "dom": 45, "inv": 4.5},
        "Miami": {"median": 550000, "yoy": 6.5, "dom": 30, "inv": 2.5},
        "Phoenix": {"median": 410000, "yoy": 3.8, "dom": 32, "inv": 3.0},
        "Dallas": {"median": 380000, "yoy": 2.1, "dom": 38, "inv": 3.8},
        "Atlanta": {"median": 370000, "yoy": 3.5, "dom": 30, "inv": 2.9},
        "Denver": {"median": 580000, "yoy": 1.8, "dom": 25, "inv": 2.2},
        "Nashville": {"median": 430000, "yoy": 4.0, "dom": 28, "inv": 2.7},
    }
    data = markets.get(market, {"median": 400000, "yoy": 3.0, "dom": 35, "inv": 3.5})
    if data["inv"] < 3:
        condition = "Seller's market"
    elif data["inv"] < 5:
        condition = "Balanced market"
    else:
        condition = "Buyer's market"
    return {
        "market": market, "property_type": property_type,
        "median_price": data["median"], "yoy_change_pct": data["yoy"],
        "avg_days_on_market": data["dom"], "months_inventory": data["inv"],
        "market_condition": condition,
        "price_to_rent_ratio": round(data["median"] / (1800 * 12), 1),
        "timestamp": datetime.now().isoformat(),
        "note": "Based on market averages. Use local MLS for precise data."
    }


def _offer_generator(property_address: str, offer_price: float, buyer_name: str,
                      earnest_money: float = 5000, closing_days: int = 30,
                      contingencies: list = None, seller_name: str = "Seller", **kw) -> Dict:
    if contingencies is None:
        contingencies = ["inspection", "financing", "appraisal"]
    cont_text = "\n".join(f"  - {c.replace('_', ' ').title()} contingency" for c in contingencies)
    letter = f"""REAL ESTATE PURCHASE OFFER

Date: {datetime.now().strftime('%B %d, %Y')}
Property: {property_address}

Dear {seller_name},

I, {buyer_name}, hereby submit this offer to purchase the property at {property_address}.

TERMS:
  Offer Price: ${offer_price:,.2f}
  Earnest Money Deposit: ${earnest_money:,.2f}
  Closing Date: {closing_days} days from acceptance
  Financing: Conventional mortgage

CONTINGENCIES:
{cont_text}

This offer is valid for 72 hours from the date above.

Sincerely,
{buyer_name}"""
    return {"offer_letter": letter, "offer_price": offer_price, "property": property_address}


def _lease_generator(landlord_name: str, tenant_name: str, property_address: str,
                      monthly_rent: float, lease_start: str = "", lease_months: int = 12,
                      security_deposit: float = 0, **kw) -> Dict:
    start = lease_start or datetime.now().strftime("%Y-%m-%d")
    dep = security_deposit or monthly_rent
    lease = f"""RESIDENTIAL LEASE AGREEMENT

Date: {datetime.now().strftime('%B %d, %Y')}
Landlord: {landlord_name}
Tenant: {tenant_name}
Property: {property_address}

1. TERM: {lease_months} months beginning {start}.
2. RENT: ${monthly_rent:,.2f}/month, due on the 1st. Late fee of 5% after the 5th.
3. SECURITY DEPOSIT: ${dep:,.2f}, refundable per state law.
4. UTILITIES: Tenant responsible unless otherwise agreed.
5. MAINTENANCE: Tenant maintains premises; Landlord handles structural repairs.
6. PETS: Not permitted without written addendum.
7. SUBLETTING: Not permitted without Landlord's written consent.
8. ENTRY: Landlord may enter with 24-hour notice for repairs/inspections.
9. TERMINATION: 30-day written notice required for non-renewal.
10. GOVERNING LAW: State law where property is located.

Landlord Signature: ___________________  Date: _________
Tenant Signature:  ___________________  Date: _________"""
    return {"lease_agreement": lease, "monthly_rent": monthly_rent, "term_months": lease_months}


def _property_tax_estimator(property_value: float, state: str = "TX",
                             county: str = "", homestead: bool = False, **kw) -> Dict:
    rates = {
        "TX": 1.80, "NJ": 2.49, "IL": 2.27, "NH": 2.18, "CT": 2.14,
        "WI": 1.85, "NE": 1.73, "OH": 1.56, "NY": 1.72, "PA": 1.58,
        "CA": 0.76, "FL": 0.89, "CO": 0.51, "HI": 0.28, "AL": 0.41,
        "AZ": 0.66, "GA": 0.92, "NC": 0.84, "WA": 0.98, "OR": 0.97,
        "TN": 0.71, "NV": 0.60, "MI": 1.54, "VA": 0.82, "MA": 1.23,
    }
    rate = rates.get(state.upper(), 1.10)
    assessed = property_value * 0.85
    if homestead:
        assessed = max(assessed - 25000, 0)
    annual_tax = assessed * rate / 100
    monthly_tax = annual_tax / 12
    return {
        "property_value": property_value, "state": state, "county": county or "Average",
        "effective_rate_pct": rate, "assessed_value": round(assessed, 2),
        "homestead_exemption": homestead, "annual_tax": round(annual_tax, 2),
        "monthly_tax": round(monthly_tax, 2),
        "note": "Rates are state averages. County rates may vary significantly."
    }


def _investment_strategy(strategy: str, purchase_price: float, arv: float = 0,
                          rehab_cost: float = 0, monthly_rent: float = 0,
                          hold_months: int = 12, **kw) -> Dict:
    strategies = {
        "brrrr": lambda: _brrrr(purchase_price, arv, rehab_cost, monthly_rent),
        "fix_and_flip": lambda: _flip(purchase_price, arv, rehab_cost, hold_months),
        "buy_and_hold": lambda: _hold(purchase_price, monthly_rent, hold_months),
        "wholesale": lambda: _wholesale(purchase_price, arv),
    }
    fn = strategies.get(strategy.lower().replace("-", "_").replace(" ", "_"))
    if not fn:
        return {"error": f"Unknown strategy. Use: {list(strategies.keys())}"}
    return fn()


def _brrrr(price, arv, rehab, rent):
    total_in = price + rehab
    refi_amount = arv * 0.75
    cash_left = max(total_in - refi_amount, 0)
    r = 0.07 / 12
    n = 360
    refi_pmt = refi_amount * (r * (1+r)**n) / ((1+r)**n - 1) if refi_amount > 0 else 0
    cash_flow = rent - refi_pmt - (rent * 0.40)
    coc = (cash_flow * 12 / cash_left * 100) if cash_left > 0 else float('inf')
    return {
        "strategy": "BRRRR", "total_investment": total_in, "arv": arv,
        "refinance_amount": round(refi_amount, 2), "cash_left_in_deal": round(cash_left, 2),
        "refi_payment": round(refi_pmt, 2), "monthly_cash_flow": round(cash_flow, 2),
        "cash_on_cash": round(coc, 2),
        "verdict": "Excellent" if cash_left < total_in * 0.1 else "Good" if cash_left < total_in * 0.3 else "Review numbers"
    }


def _flip(price, arv, rehab, months):
    total_cost = price + rehab + (price * 0.03 * months / 12)
    sale_costs = arv * 0.08
    profit = arv - total_cost - sale_costs
    roi = (profit / (price + rehab)) * 100 if (price + rehab) else 0
    return {
        "strategy": "Fix & Flip", "purchase": price, "rehab": rehab, "arv": arv,
        "holding_costs": round(price * 0.03 * months / 12, 2),
        "sale_costs": round(sale_costs, 2), "profit": round(profit, 2),
        "roi": round(roi, 2), "hold_months": months,
        "verdict": "Good flip" if roi > 20 else "Marginal" if roi > 10 else "Too thin"
    }


def _hold(price, rent, months):
    dp = price * 0.20
    loan = price - dp
    r = 0.07 / 12
    n = 360
    pmt = loan * (r * (1+r)**n) / ((1+r)**n - 1) if loan > 0 else 0
    expenses = rent * 0.40
    cash_flow = rent - pmt - expenses
    appreciation = price * (1.04 ** (months / 12)) - price
    total_return = (cash_flow * months) + appreciation
    return {
        "strategy": "Buy & Hold", "purchase": price, "down_payment": dp,
        "monthly_mortgage": round(pmt, 2), "monthly_expenses": round(expenses, 2),
        "monthly_cash_flow": round(cash_flow, 2), "annual_cash_flow": round(cash_flow * 12, 2),
        "projected_appreciation": round(appreciation, 2),
        "total_return": round(total_return, 2), "hold_months": months,
    }


def _wholesale(price, arv):
    max_offer = arv * 0.70 - price * 0.1
    assignment_fee = max_offer - price if max_offer > price else 0
    return {
        "strategy": "Wholesale", "purchase_contract": price, "arv": arv,
        "max_offer_70pct_rule": round(max_offer, 2),
        "estimated_assignment_fee": round(assignment_fee, 2),
        "verdict": "Viable" if assignment_fee > 5000 else "Spread too thin"
    }


def _raw_tools():
    return [
        {"name": "property_analyzer", "description": "Analyze a property deal — cash flow, cap rate, ROI, cash-on-cash return",
         "parameters": {"type": "object", "properties": {
             "purchase_price": {"type": "number"}, "monthly_rent": {"type": "number"},
             "monthly_expenses": {"type": "number"}, "down_payment_pct": {"type": "number", "default": 20},
             "loan_rate": {"type": "number", "default": 7.0}, "loan_term_years": {"type": "integer", "default": 30},
             "closing_costs": {"type": "number", "default": 0}},
          "required": ["purchase_price", "monthly_rent", "monthly_expenses"]},
         "function": _property_analyzer},
        {"name": "mortgage_calculator", "description": "Calculate monthly payment, total interest, and optional amortization schedule",
         "parameters": {"type": "object", "properties": {
             "principal": {"type": "number"}, "annual_rate": {"type": "number", "default": 7.0},
             "term_years": {"type": "integer", "default": 30}, "show_schedule": {"type": "boolean", "default": False}},
          "required": ["principal"]},
         "function": _mortgage_calculator},
        {"name": "rental_income", "description": "Estimate rental income by area, bedrooms, and property type",
         "parameters": {"type": "object", "properties": {
             "area": {"type": "string", "default": "US Average"}, "bedrooms": {"type": "integer", "default": 3},
             "property_type": {"type": "string", "enum": ["single_family", "condo", "townhouse", "duplex", "apartment"]}},
          "required": []},
         "function": _rental_income},
        {"name": "property_comparison", "description": "Compare multiple properties side by side on key metrics",
         "parameters": {"type": "object", "properties": {
             "properties": {"type": "array", "items": {"type": "object"}}},
          "required": ["properties"]},
         "function": _property_comparison},
        {"name": "rehab_estimator", "description": "Estimate renovation costs by room and scope (cosmetic/moderate/full_gut)",
         "parameters": {"type": "object", "properties": {
             "rooms": {"type": "array", "items": {"type": "string"}},
             "scope": {"type": "string", "enum": ["cosmetic", "moderate", "full_gut"], "default": "moderate"},
             "sqft": {"type": "integer", "default": 0}},
          "required": ["rooms"]},
         "function": _rehab_estimator},
        {"name": "market_analysis", "description": "Analyze a real estate market — median prices, trends, days on market, inventory",
         "parameters": {"type": "object", "properties": {
             "market": {"type": "string", "default": "US National"},
             "property_type": {"type": "string", "default": "single_family"}},
          "required": []},
         "function": _market_analysis},
        {"name": "offer_generator", "description": "Generate a real estate purchase offer letter",
         "parameters": {"type": "object", "properties": {
             "property_address": {"type": "string"}, "offer_price": {"type": "number"},
             "buyer_name": {"type": "string"}, "earnest_money": {"type": "number", "default": 5000},
             "closing_days": {"type": "integer", "default": 30},
             "contingencies": {"type": "array", "items": {"type": "string"}},
             "seller_name": {"type": "string", "default": "Seller"}},
          "required": ["property_address", "offer_price", "buyer_name"]},
         "function": _offer_generator},
        {"name": "lease_generator", "description": "Generate a residential lease agreement",
         "parameters": {"type": "object", "properties": {
             "landlord_name": {"type": "string"}, "tenant_name": {"type": "string"},
             "property_address": {"type": "string"}, "monthly_rent": {"type": "number"},
             "lease_start": {"type": "string"}, "lease_months": {"type": "integer", "default": 12},
             "security_deposit": {"type": "number", "default": 0}},
          "required": ["landlord_name", "tenant_name", "property_address", "monthly_rent"]},
         "function": _lease_generator},
        {"name": "property_tax_estimator", "description": "Estimate property taxes by state with homestead exemption support",
         "parameters": {"type": "object", "properties": {
             "property_value": {"type": "number"}, "state": {"type": "string", "default": "TX"},
             "county": {"type": "string"}, "homestead": {"type": "boolean", "default": False}},
          "required": ["property_value"]},
         "function": _property_tax_estimator},
        {"name": "investment_strategy", "description": "Analyze BRRRR, fix-and-flip, buy-and-hold, or wholesale strategies",
         "parameters": {"type": "object", "properties": {
             "strategy": {"type": "string", "enum": ["brrrr", "fix_and_flip", "buy_and_hold", "wholesale"]},
             "purchase_price": {"type": "number"}, "arv": {"type": "number", "default": 0},
             "rehab_cost": {"type": "number", "default": 0}, "monthly_rent": {"type": "number", "default": 0},
             "hold_months": {"type": "integer", "default": 12}},
          "required": ["strategy", "purchase_price"]},
         "function": _investment_strategy},
    ]


def get_tools():
    return adapt_tools(_raw_tools())
