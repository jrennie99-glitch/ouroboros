"""Ouroboros — Sales & advertising tools."""

from __future__ import annotations
import json, os, logging
from datetime import datetime
from typing import Any, Dict, List
from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)
WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_sales")
PIPELINE_PATH = os.path.join(WORKSPACE, "pipeline.json")
STAGES = ["prospect", "qualified", "proposal", "negotiation", "closed"]


def _ensure():
    os.makedirs(WORKSPACE, exist_ok=True)


def _load_pipeline() -> Dict[str, Any]:
    _ensure()
    if os.path.exists(PIPELINE_PATH):
        with open(PIPELINE_PATH) as f:
            return json.load(f)
    return {s: [] for s in STAGES}


def _save_pipeline(p: Dict[str, Any]):
    _ensure()
    with open(PIPELINE_PATH, "w") as f:
        json.dump(p, f, indent=2)


# 1 — sales_pipeline
def sales_pipeline(action: str = "view", deal_name: str = "",
                   stage: str = "prospect", value: float = 0,
                   contact: str = "", move_to: str = "") -> Dict[str, Any]:
    p = _load_pipeline()
    if action == "view":
        summary = {s: len(p.get(s, [])) for s in STAGES}
        return {"pipeline": p, "summary": summary}
    if action == "add":
        deal = {"name": deal_name, "value": value, "contact": contact,
                "stage": stage, "created": datetime.now().isoformat()}
        p.setdefault(stage, []).append(deal)
        _save_pipeline(p)
        return {"added": deal}
    if action == "move":
        if move_to not in STAGES:
            return {"error": f"Invalid stage. Choose from: {STAGES}"}
        for s in STAGES:
            for i, d in enumerate(p.get(s, [])):
                if d["name"] == deal_name:
                    p[s].pop(i)
                    d["stage"] = move_to
                    d["moved"] = datetime.now().isoformat()
                    p.setdefault(move_to, []).append(d)
                    _save_pipeline(p)
                    return {"moved": d, "from": s, "to": move_to}
        return {"error": f"Deal '{deal_name}' not found"}
    if action == "remove":
        for s in STAGES:
            for i, d in enumerate(p.get(s, [])):
                if d["name"] == deal_name:
                    p[s].pop(i)
                    _save_pipeline(p)
                    return {"removed": d}
        return {"error": f"Deal '{deal_name}' not found"}
    return {"error": "action must be view|add|move|remove"}


# 2 — sales_script
def sales_script(script_type: str = "cold_call", product: str = "",
                 target_role: str = "", objections: str = "") -> Dict[str, Any]:
    templates = {
        "cold_call": [
            f"Hi {{name}}, this is {{rep}} from {{company}}.",
            f"I noticed your team is dealing with [pain point]. We help {target_role}s solve this with {product}.",
            "Would you have 15 minutes this week to see how we've helped similar companies?",
            "OBJECTION HANDLES:", f"  'Not interested' → 'I understand. Can I ask what solution you're currently using?'",
            f"  'No budget' → 'Many clients felt the same before seeing the ROI. Can I share a quick case study?'",
            f"  'Send info' → 'Happy to. What specific challenge should I focus on?'",
        ],
        "follow_up": [
            f"Hi {{name}}, following up on our conversation about {product}.",
            "I wanted to share [relevant case study / data point].",
            "Would [day] or [day] work better for a quick demo?",
        ],
        "objection_handling": [
            f"PRODUCT: {product} | ROLE: {target_role}",
            f"Objections to handle: {objections or 'price, timing, competition, authority'}",
            "PRICE: Reframe as investment, show ROI calculation, offer payment plans.",
            "TIMING: Create urgency with limited offer, show cost of delay.",
            "COMPETITION: Highlight unique differentiators, offer head-to-head comparison.",
            "AUTHORITY: Ask to include decision-maker, provide exec summary.",
        ],
        "closing": [
            "ASSUMPTIVE: 'Shall I set up your account for the annual plan?'",
            "ALTERNATIVE: 'Would you prefer the standard or premium package?'",
            "URGENCY: 'This pricing is available through end of month.'",
            "SUMMARY: Recap all benefits, then ask for the order.",
        ],
    }
    lines = templates.get(script_type, templates["cold_call"])
    return {"script_type": script_type, "product": product, "target_role": target_role, "script": lines}


# 3 — proposal_generator
def proposal_generator(client: str = "", project: str = "", scope: str = "",
                       price: float = 0, timeline_weeks: int = 4,
                       terms: str = "Net 30") -> Dict[str, Any]:
    proposal = {
        "title": f"Proposal: {project}",
        "client": client,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "sections": {
            "executive_summary": f"We propose to deliver {project} for {client}, addressing key business needs with a proven approach.",
            "scope": scope or "To be defined in discovery phase.",
            "deliverables": [f"{project} — Phase 1: Discovery", f"{project} — Phase 2: Implementation",
                             f"{project} — Phase 3: Testing & Launch"],
            "timeline": f"{timeline_weeks} weeks from signed agreement.",
            "pricing": {"total": price, "currency": "USD",
                        "breakdown": [{"phase": "Discovery", "pct": 20, "amount": price * 0.2},
                                      {"phase": "Implementation", "pct": 50, "amount": price * 0.5},
                                      {"phase": "Testing & Launch", "pct": 30, "amount": price * 0.3}]},
            "terms": terms,
            "validity": "This proposal is valid for 30 days.",
        },
    }
    return proposal


# 4 — pitch_deck_outline
def pitch_deck_outline(company: str = "", problem: str = "", solution: str = "",
                       market_size: str = "", traction: str = "",
                       team: str = "", ask: str = "") -> Dict[str, Any]:
    slides = [
        {"slide": 1, "title": "Title", "content": f"{company} — Investor Pitch"},
        {"slide": 2, "title": "Problem", "content": problem or "Define the pain point."},
        {"slide": 3, "title": "Solution", "content": solution or "Your unique approach."},
        {"slide": 4, "title": "Market Opportunity", "content": market_size or "TAM / SAM / SOM analysis."},
        {"slide": 5, "title": "Business Model", "content": "Revenue streams and pricing strategy."},
        {"slide": 6, "title": "Traction", "content": traction or "Key metrics and milestones."},
        {"slide": 7, "title": "Competitive Landscape", "content": "Positioning vs alternatives."},
        {"slide": 8, "title": "Go-to-Market", "content": "Customer acquisition strategy."},
        {"slide": 9, "title": "Team", "content": team or "Founders and key hires."},
        {"slide": 10, "title": "Financials", "content": "Projections and unit economics."},
        {"slide": 11, "title": "The Ask", "content": ask or "Funding amount, use of funds, timeline."},
    ]
    return {"company": company, "slides": slides, "total_slides": len(slides)}


# 5 — competitor_battle_card
def competitor_battle_card(our_product: str = "", competitor: str = "",
                           our_strengths: str = "", their_strengths: str = "",
                           their_weaknesses: str = "") -> Dict[str, Any]:
    card = {
        "title": f"{our_product} vs {competitor}",
        "our_product": our_product, "competitor": competitor,
        "comparison": {
            "our_strengths": [s.strip() for s in our_strengths.split(",") if s.strip()] or ["To be defined"],
            "their_strengths": [s.strip() for s in their_strengths.split(",") if s.strip()] or ["To be defined"],
            "their_weaknesses": [s.strip() for s in their_weaknesses.split(",") if s.strip()] or ["To be defined"],
        },
        "objection_handling": {
            f"'Why not {competitor}?'": f"While {competitor} offers [their strength], {our_product} differentiates with [our strength].",
            "'They are cheaper'": "Our total cost of ownership is lower when you factor in [hidden costs, support, scalability].",
            "'They have more features'": "We focus on the features that matter most: [key differentiators]. Less bloat, faster results.",
            "'We already use them'": f"Many of our best customers switched from {competitor}. Migration takes [timeframe] and we handle it.",
        },
        "trap_questions": [
            f"Ask prospect: 'How long does {competitor} take to [common pain point]?'",
            f"Ask prospect: 'What's your experience with {competitor}'s support response time?'",
        ],
    }
    return card


# 6 — commission_calculator
def commission_calculator(deal_value: float = 0, model: str = "flat",
                          rate: float = 10, tiers: str = "",
                          accelerator_threshold: float = 0,
                          accelerator_rate: float = 0,
                          split_pcts: str = "") -> Dict[str, Any]:
    if model == "flat":
        commission = deal_value * (rate / 100)
        return {"model": "flat", "deal_value": deal_value, "rate": rate, "commission": round(commission, 2)}
    if model == "tiered":
        tier_list = []
        for t in (tiers or "0-50000:5,50000-100000:8,100000+:12").split(","):
            rng, pct = t.strip().split(":")
            tier_list.append((rng.strip(), float(pct)))
        total = 0.0
        remaining = deal_value
        breakdown = []
        for rng, pct in tier_list:
            if "+" in rng:
                low = float(rng.replace("+", ""))
                amt = max(0, remaining)
            else:
                parts = rng.split("-")
                low, high = float(parts[0]), float(parts[1])
                amt = min(max(0, remaining), high - low)
            c = amt * (pct / 100)
            total += c
            breakdown.append({"range": rng, "rate": pct, "amount": round(amt, 2), "commission": round(c, 2)})
            remaining -= amt
            if remaining <= 0:
                break
        return {"model": "tiered", "deal_value": deal_value, "breakdown": breakdown, "total_commission": round(total, 2)}
    if model == "accelerator":
        if deal_value <= accelerator_threshold:
            commission = deal_value * (rate / 100)
        else:
            base = accelerator_threshold * (rate / 100)
            accel = (deal_value - accelerator_threshold) * ((accelerator_rate or rate * 1.5) / 100)
            commission = base + accel
        return {"model": "accelerator", "deal_value": deal_value, "base_rate": rate,
                "accel_rate": accelerator_rate or rate * 1.5,
                "threshold": accelerator_threshold, "commission": round(commission, 2)}
    if model == "split":
        pcts = [float(x.strip()) for x in (split_pcts or "60,40").split(",")]
        base_commission = deal_value * (rate / 100)
        splits = [{"rep": i + 1, "pct": p, "amount": round(base_commission * p / 100, 2)} for i, p in enumerate(pcts)]
        return {"model": "split", "deal_value": deal_value, "total_commission": round(base_commission, 2), "splits": splits}
    return {"error": "model must be flat|tiered|accelerator|split"}


# 7 — sales_forecast
def sales_forecast(method: str = "weighted_pipeline", deals: str = "",
                   historical_revenue: str = "", growth_rate: float = 10,
                   periods: int = 4) -> Dict[str, Any]:
    if method == "weighted_pipeline":
        stage_weights = {"prospect": 0.1, "qualified": 0.25, "proposal": 0.5, "negotiation": 0.75, "closed": 1.0}
        p = _load_pipeline()
        total_weighted = 0.0
        detail = []
        for stage, w in stage_weights.items():
            for d in p.get(stage, []):
                val = d.get("value", 0) * w
                total_weighted += val
                detail.append({"deal": d["name"], "stage": stage, "value": d.get("value", 0),
                                "weight": w, "weighted": round(val, 2)})
        return {"method": "weighted_pipeline", "forecast": round(total_weighted, 2), "deals": detail}
    if method == "historical":
        revs = [float(x.strip()) for x in (historical_revenue or "100000,110000,120000,130000").split(",")]
        if len(revs) < 2:
            return {"error": "Need at least 2 historical data points"}
        avg_growth = sum((revs[i] - revs[i - 1]) / revs[i - 1] * 100 for i in range(1, len(revs))) / (len(revs) - 1)
        forecast = []
        last = revs[-1]
        for i in range(1, periods + 1):
            projected = last * (1 + avg_growth / 100)
            forecast.append({"period": i, "projected": round(projected, 2)})
            last = projected
        return {"method": "historical", "avg_growth_pct": round(avg_growth, 2), "forecast": forecast}
    if method == "growth_rate":
        base = float((historical_revenue or "100000").split(",")[-1].strip())
        forecast = []
        for i in range(1, periods + 1):
            projected = base * (1 + growth_rate / 100) ** i
            forecast.append({"period": i, "projected": round(projected, 2)})
        return {"method": "growth_rate", "base": base, "rate": growth_rate, "forecast": forecast}
    return {"error": "method must be weighted_pipeline|historical|growth_rate"}

def cold_email_sequence(product: str = "", target_role: str = "",
                        value_prop: str = "", num_emails: int = 5,
                        company: str = "") -> Dict[str, Any]:
    vp = value_prop or "achieve better results"
    base = [
        {"day": 1, "subject": "Quick question about {company}'s [challenge]",
         "body": f"Hi {{name}}, I help {target_role}s {vp}. Worth a 10-min call?", "cta": "Reply with a time."},
        {"day": 3, "subject": "Re: Quick question",
         "body": f"{product} helped [similar co] achieve [result]. Thought it might resonate.", "cta": "Quick chat?"},
        {"day": 7, "subject": f"How [co] solved [problem] with {product}",
         "body": "Sharing a case study: [Company X] saw [metric] in [timeframe].", "cta": "Same for you?"},
        {"day": 14, "subject": "One more idea for {company}",
         "body": f"One more thought on how {product} could help with [challenge].", "cta": "Still a priority?"},
        {"day": 21, "subject": "Should I close your file?",
         "body": "Haven't heard back — should I check in later or connect with someone else?", "cta": "Reply 'later' or 'pass'."},
        {"day": 30, "subject": f"Last one — {product} update",
         "body": f"We just launched [feature] addressing [pain point for {target_role}s].", "cta": "Worth revisiting?"},
        {"day": 45, "subject": "Breakup email",
         "body": "Stopping outreach. If things change, my door is open.", "cta": "All the best."},
    ]
    return {"product": product, "target_role": target_role, "num_emails": min(num_emails, 7),
            "sequence": base[:min(num_emails, 7)]}


# 9 — ad_campaign_planner
def ad_campaign_planner(budget: float = 1000, objective: str = "leads",
                        channels: str = "", target_audience: str = "",
                        duration_days: int = 30) -> Dict[str, Any]:
    channel_list = [c.strip() for c in (channels or "google_ads,facebook,linkedin").split(",")]
    alloc = {}
    weights = {"google_ads": 40, "facebook": 25, "linkedin": 20, "twitter": 10, "tiktok": 15,
               "instagram": 20, "youtube": 25, "email": 10, "display": 10}
    total_w = sum(weights.get(c, 10) for c in channel_list)
    for c in channel_list:
        w = weights.get(c, 10)
        alloc[c] = {"budget": round(budget * w / total_w, 2), "pct": round(w / total_w * 100, 1)}
    cpc_est = {"google_ads": 2.5, "facebook": 1.2, "linkedin": 5.0, "twitter": 1.5,
               "tiktok": 0.8, "instagram": 1.0, "youtube": 3.0, "email": 0.5, "display": 0.8}
    kpis = {}
    for c in channel_list:
        cb = alloc[c]["budget"]
        cpc = cpc_est.get(c, 1.5)
        clicks = int(cb / cpc)
        conv_rate = 0.03 if objective == "leads" else 0.02
        kpis[c] = {"est_clicks": clicks, "est_cpc": cpc, "est_conversions": int(clicks * conv_rate),
                    "est_cpa": round(cb / max(1, int(clicks * conv_rate)), 2)}
    return {"budget": budget, "objective": objective, "duration_days": duration_days,
            "target_audience": target_audience, "allocation": alloc, "kpis": kpis}


# 10 — roi_calculator
def roi_calculator(spend: float = 0, impressions: int = 0, clicks: int = 0,
                   conversions: int = 0, revenue: float = 0,
                   cost_per_unit: float = 0) -> Dict[str, Any]:
    ctr = (clicks / impressions * 100) if impressions > 0 else 0
    conv_rate = (conversions / clicks * 100) if clicks > 0 else 0
    cpc = (spend / clicks) if clicks > 0 else 0
    cpa = (spend / conversions) if conversions > 0 else 0
    profit = revenue - spend - (conversions * cost_per_unit)
    roi = (profit / spend * 100) if spend > 0 else 0
    roas = (revenue / spend) if spend > 0 else 0
    return {
        "spend": spend, "impressions": impressions, "clicks": clicks,
        "conversions": conversions, "revenue": revenue,
        "metrics": {
            "ctr_pct": round(ctr, 2), "conversion_rate_pct": round(conv_rate, 2),
            "cpc": round(cpc, 2), "cpa": round(cpa, 2),
            "profit": round(profit, 2), "roi_pct": round(roi, 2), "roas": round(roas, 2),
        },
    }


def _raw_tools() -> List[Dict[str, Any]]:
    return [
        {"name": "sales_pipeline", "description": "Manage sales pipeline — add, move, view, remove deals through stages.",
         "parameters": {"type": "object", "properties": {
             "action": {"type": "string", "enum": ["view", "add", "move", "remove"]},
             "deal_name": {"type": "string"}, "stage": {"type": "string", "enum": STAGES},
             "value": {"type": "number"}, "contact": {"type": "string"}, "move_to": {"type": "string", "enum": STAGES},
         }}, "function": sales_pipeline},
        {"name": "sales_script", "description": "Generate sales scripts for cold call, follow-up, objection handling, closing.",
         "parameters": {"type": "object", "properties": {
             "script_type": {"type": "string", "enum": ["cold_call", "follow_up", "objection_handling", "closing"]},
             "product": {"type": "string"}, "target_role": {"type": "string"}, "objections": {"type": "string"},
         }}, "function": sales_script},
        {"name": "proposal_generator", "description": "Generate business proposals with summary, scope, pricing, timeline, terms.",
         "parameters": {"type": "object", "properties": {
             "client": {"type": "string"}, "project": {"type": "string"}, "scope": {"type": "string"},
             "price": {"type": "number"}, "timeline_weeks": {"type": "integer"}, "terms": {"type": "string"},
         }}, "function": proposal_generator},
        {"name": "pitch_deck_outline", "description": "Generate pitch deck structure: problem, solution, market, traction, team, ask.",
         "parameters": {"type": "object", "properties": {
             "company": {"type": "string"}, "problem": {"type": "string"}, "solution": {"type": "string"},
             "market_size": {"type": "string"}, "traction": {"type": "string"}, "team": {"type": "string"},
             "ask": {"type": "string"},
         }}, "function": pitch_deck_outline},
        {"name": "competitor_battle_card", "description": "Generate competitive battle cards: strengths, weaknesses, objection handling.",
         "parameters": {"type": "object", "properties": {
             "our_product": {"type": "string"}, "competitor": {"type": "string"},
             "our_strengths": {"type": "string"}, "their_strengths": {"type": "string"},
             "their_weaknesses": {"type": "string"},
         }}, "function": competitor_battle_card},
        {"name": "commission_calculator", "description": "Calculate sales commissions: flat, tiered, accelerator, split models.",
         "parameters": {"type": "object", "properties": {
             "deal_value": {"type": "number"}, "model": {"type": "string", "enum": ["flat", "tiered", "accelerator", "split"]},
             "rate": {"type": "number"}, "tiers": {"type": "string"},
             "accelerator_threshold": {"type": "number"}, "accelerator_rate": {"type": "number"},
             "split_pcts": {"type": "string"},
         }}, "function": commission_calculator},
        {"name": "sales_forecast", "description": "Forecast revenue: weighted pipeline, historical trend, or growth rate.",
         "parameters": {"type": "object", "properties": {
             "method": {"type": "string", "enum": ["weighted_pipeline", "historical", "growth_rate"]},
             "deals": {"type": "string"}, "historical_revenue": {"type": "string"},
             "growth_rate": {"type": "number"}, "periods": {"type": "integer"},
         }}, "function": sales_forecast},
        {"name": "cold_email_sequence", "description": "Generate multi-touch cold email sequences (5-7 emails with timing).",
         "parameters": {"type": "object", "properties": {
             "product": {"type": "string"}, "target_role": {"type": "string"},
             "value_prop": {"type": "string"}, "num_emails": {"type": "integer"}, "company": {"type": "string"},
         }}, "function": cold_email_sequence},
        {"name": "ad_campaign_planner", "description": "Plan ad campaigns: budget allocation, channel mix, targeting, KPIs.",
         "parameters": {"type": "object", "properties": {
             "budget": {"type": "number"}, "objective": {"type": "string", "enum": ["leads", "sales", "awareness", "traffic"]},
             "channels": {"type": "string"}, "target_audience": {"type": "string"},
             "duration_days": {"type": "integer"},
         }}, "function": ad_campaign_planner},
        {"name": "roi_calculator", "description": "Calculate marketing/ad ROI: spend, impressions, clicks, conversions, revenue, ROAS.",
         "parameters": {"type": "object", "properties": {
             "spend": {"type": "number"}, "impressions": {"type": "integer"}, "clicks": {"type": "integer"},
             "conversions": {"type": "integer"}, "revenue": {"type": "number"}, "cost_per_unit": {"type": "number"},
         }}, "function": roi_calculator},
    ]


def get_tools():
    return adapt_tools(_raw_tools())
