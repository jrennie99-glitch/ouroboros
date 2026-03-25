"""Ouroboros — Legal tools suite."""

from __future__ import annotations

import json
import textwrap
from datetime import datetime
from typing import Any, Dict, List

from ouroboros.tools._adapter import adapt_tools

DISCLAIMER = (
    "\n\n---\n**DISCLAIMER**: This is AI-generated legal content for informational "
    "purposes only. It does NOT constitute legal advice. Consult a licensed attorney "
    "before using any generated document."
)


def _contract_generator(contract_type: str = "nda",
                        party_a: str = "", party_b: str = "",
                        terms: str = "", duration: str = "1 year",
                        governing_law: str = "State of Delaware",
                        additional_clauses: str = "") -> Dict[str, Any]:
    templates = {
        "nda": {
            "title": "NON-DISCLOSURE AGREEMENT",
            "sections": [
                ("Recitals", f"{party_a} ('Disclosing Party') and {party_b} ('Receiving Party') wish to explore a business relationship requiring exchange of confidential information."),
                ("Definition of Confidential Information", "All non-public business, technical, financial information disclosed in any form."),
                ("Obligations", "Receiving Party shall hold information in strict confidence, use only for the stated purpose, and not disclose to third parties without written consent."),
                ("Exclusions", "Information that is publicly available, independently developed, or rightfully received from third parties."),
                ("Term", f"This Agreement shall remain in effect for {duration} from the Effective Date."),
                ("Remedies", "Disclosing Party shall be entitled to equitable relief including injunction and specific performance."),
            ],
        },
        "service_agreement": {
            "title": "SERVICE AGREEMENT",
            "sections": [
                ("Scope of Services", terms or "Services to be defined in Exhibit A."),
                ("Compensation", "As agreed upon and outlined in Exhibit B."),
                ("Term and Termination", f"This Agreement is effective for {duration}. Either party may terminate with 30 days written notice."),
                ("Intellectual Property", "All work product created shall be owned by the Client upon full payment."),
                ("Limitation of Liability", "Neither party shall be liable for indirect, incidental, or consequential damages."),
                ("Indemnification", "Each party shall indemnify the other against claims arising from breach of this Agreement."),
            ],
        },
        "partnership": {
            "title": "PARTNERSHIP AGREEMENT",
            "sections": [
                ("Formation", f"{party_a} and {party_b} hereby form a general partnership."),
                ("Purpose", terms or "To engage in lawful business activities as mutually agreed."),
                ("Capital Contributions", "Each partner shall contribute capital as outlined in Schedule A."),
                ("Profit and Loss Sharing", "Profits and losses shall be shared equally unless otherwise agreed in writing."),
                ("Management", "All partners shall have equal rights in management and conduct of business."),
                ("Dissolution", "Partnership may be dissolved by unanimous written consent or by operation of law."),
            ],
        },
        "freelance": {
            "title": "FREELANCE / INDEPENDENT CONTRACTOR AGREEMENT",
            "sections": [
                ("Engagement", f"{party_a} ('Client') engages {party_b} ('Contractor') as an independent contractor."),
                ("Services", terms or "Services as described in the attached Statement of Work."),
                ("Compensation", "Contractor shall be compensated at the agreed rate upon delivery of milestones."),
                ("Independent Contractor Status", "Contractor is not an employee and is responsible for own taxes and insurance."),
                ("Work Product", "All deliverables shall be works made for hire, owned by Client."),
                ("Termination", f"Either party may terminate with 14 days written notice. Term: {duration}."),
            ],
        },
        "employment": {
            "title": "EMPLOYMENT AGREEMENT",
            "sections": [
                ("Position", f"{party_b} ('Employee') is hired by {party_a} ('Employer') for the role specified herein."),
                ("Duties", terms or "As assigned by Employer and consistent with the position."),
                ("Compensation and Benefits", "Salary, bonuses, and benefits as outlined in Schedule A."),
                ("At-Will Employment", "Employment is at-will unless otherwise specified by governing law."),
                ("Confidentiality", "Employee agrees to maintain confidentiality of proprietary information."),
                ("Non-Compete", f"Employee shall not compete within the industry for 12 months post-termination within {governing_law} jurisdiction."),
            ],
        },
    }
    t = templates.get(contract_type, templates["nda"])
    body = f"# {t['title']}\n\n**Date:** {datetime.now().strftime('%B %d, %Y')}\n"
    body += f"**Party A:** {party_a or '[PARTY A]'}\n**Party B:** {party_b or '[PARTY B]'}\n"
    body += f"**Governing Law:** {governing_law}\n\n"
    for heading, content in t["sections"]:
        body += f"## {heading}\n{content}\n\n"
    if additional_clauses:
        body += f"## Additional Clauses\n{additional_clauses}\n\n"
    body += "## Signatures\n\n___________________________\nParty A\n\n___________________________\nParty B\n"
    return {"contract": body + DISCLAIMER}


def _legal_letter(letter_type: str = "cease_and_desist",
                  sender: str = "", recipient: str = "",
                  subject: str = "", details: str = "",
                  deadline: str = "14 days",
                  governing_law: str = "State of Delaware") -> Dict[str, Any]:
    date = datetime.now().strftime("%B %d, %Y")
    headers = {
        "cease_and_desist": ("CEASE AND DESIST", f"You are hereby notified to immediately cease and desist from {subject or 'the described conduct'}. {details} Failure to comply within {deadline} may result in legal action under the laws of {governing_law}."),
        "demand_letter": ("DEMAND LETTER", f"This letter constitutes a formal demand regarding {subject}. {details} Payment/resolution is demanded within {deadline}. Failure to respond will result in pursuit of all available legal remedies."),
        "notice_of_termination": ("NOTICE OF TERMINATION", f"This letter serves as formal notice of termination of {subject}. {details} Effective {deadline} from the date of this letter. All obligations shall survive as specified in the original agreement."),
        "intent_to_sue": ("NOTICE OF INTENT TO SUE", f"This letter serves as formal notice of intent to commence legal proceedings regarding {subject}. {details} You have {deadline} to resolve this matter before litigation is filed under {governing_law} jurisdiction."),
    }
    title, body_text = headers.get(letter_type, headers["cease_and_desist"])
    letter = f"# {title}\n\n**Date:** {date}\n**From:** {sender or '[SENDER]'}\n**To:** {recipient or '[RECIPIENT]'}\n\n"
    letter += f"Dear {recipient or 'Sir/Madam'},\n\n{body_text}\n\n"
    letter += "Please govern yourself accordingly.\n\nSincerely,\n\n___________________________\n"
    letter += f"{sender or '[SENDER]'}\n"
    return {"letter": letter + DISCLAIMER}


def _terms_of_service(company_name: str = "", website_url: str = "",
                      services_description: str = "",
                      governing_law: str = "State of Delaware",
                      contact_email: str = "") -> Dict[str, Any]:
    sections = [
        ("Acceptance of Terms", f"By accessing {website_url or 'this website'}, you agree to be bound by these Terms of Service operated by {company_name or '[COMPANY]'}."),
        ("Description of Service", services_description or "We provide the services described on our website."),
        ("User Accounts", "You are responsible for maintaining the confidentiality of your account credentials and for all activities under your account."),
        ("Prohibited Conduct", "You agree not to: (a) violate any laws; (b) infringe intellectual property rights; (c) transmit malicious code; (d) interfere with service operation."),
        ("Intellectual Property", f"All content and materials on {website_url or 'this website'} are owned by {company_name or '[COMPANY]'} and protected by applicable IP laws."),
        ("Limitation of Liability", f"{company_name or '[COMPANY]'} shall not be liable for indirect, incidental, special, or consequential damages."),
        ("Indemnification", f"You agree to indemnify {company_name or '[COMPANY]'} against any claims arising from your use of the service."),
        ("Termination", "We may terminate or suspend your access at our sole discretion without prior notice."),
        ("Governing Law", f"These Terms shall be governed by the laws of {governing_law}."),
        ("Contact", f"Questions about these Terms should be directed to {contact_email or '[EMAIL]'}."),
    ]
    doc = f"# Terms of Service — {company_name or '[COMPANY]'}\n\n**Effective Date:** {datetime.now().strftime('%B %d, %Y')}\n\n"
    for heading, content in sections:
        doc += f"## {heading}\n{content}\n\n"
    return {"terms_of_service": doc + DISCLAIMER}


def _privacy_policy(company_name: str = "", website_url: str = "",
                    data_collected: str = "name, email, usage data",
                    third_party_sharing: bool = False,
                    cookie_usage: bool = True,
                    contact_email: str = "",
                    gdpr: bool = True, ccpa: bool = True) -> Dict[str, Any]:
    sections = [
        ("Information We Collect", f"We collect the following information: {data_collected}."),
        ("How We Use Your Information", "We use collected information to provide, maintain, and improve our services, communicate with you, and comply with legal obligations."),
        ("Data Sharing", "We share your information with third-party service providers as necessary." if third_party_sharing else "We do not sell or share your personal information with third parties except as required by law."),
        ("Cookies", "We use cookies and similar tracking technologies to enhance your experience." if cookie_usage else "We do not use cookies or tracking technologies."),
        ("Data Security", "We implement appropriate technical and organizational measures to protect your personal information."),
        ("Data Retention", "We retain personal data only as long as necessary for the purposes outlined in this policy."),
    ]
    if gdpr:
        sections.append(("GDPR Rights (EU Users)", "Under the GDPR, you have the right to: access, rectify, erase, restrict processing, data portability, and object to processing of your personal data. Contact us to exercise these rights."))
    if ccpa:
        sections.append(("CCPA Rights (California Residents)", "Under the CCPA, you have the right to: know what data is collected, delete your data, opt out of data sales, and non-discrimination. Contact us to exercise these rights."))
    sections.append(("Contact", f"For privacy inquiries, contact {contact_email or '[EMAIL]'}."))

    doc = f"# Privacy Policy — {company_name or '[COMPANY]'}\n\n**Effective Date:** {datetime.now().strftime('%B %d, %Y')}\n**Website:** {website_url or '[URL]'}\n\n"
    for heading, content in sections:
        doc += f"## {heading}\n{content}\n\n"
    return {"privacy_policy": doc + DISCLAIMER}


def _trademark_search(mark: str = "", industry: str = "",
                      classes: str = "") -> Dict[str, Any]:
    risk_factors = []
    suggestions = []
    common_prefixes = ["e-", "i", "my", "go", "smart", "pro", "net", "web", "cloud", "ai"]
    common_suffixes = ["ly", "ify", "io", "hub", "lab", "labs", "tech", "ware", "works", "nest"]
    mark_lower = mark.lower().strip()
    for p in common_prefixes:
        if mark_lower.startswith(p):
            risk_factors.append(f"Begins with common prefix '{p}' — higher chance of conflict.")
    for s in common_suffixes:
        if mark_lower.endswith(s):
            risk_factors.append(f"Ends with common suffix '{s}' — may be considered descriptive.")
    if len(mark_lower) < 4:
        risk_factors.append("Very short marks are harder to register and defend.")
    if mark_lower.lower() == industry.lower():
        risk_factors.append("Mark is identical to the industry name — likely descriptive and unregistrable.")
    generic_terms = ["app", "solutions", "services", "global", "digital", "online", "group"]
    for g in generic_terms:
        if g in mark_lower:
            risk_factors.append(f"Contains generic term '{g}' — may weaken distinctiveness.")
    suggestions.append("Conduct a comprehensive search on USPTO TESS database (tmsearch.uspto.gov).")
    suggestions.append("Search state trademark databases for the states you operate in.")
    suggestions.append("Check domain name availability for the mark.")
    suggestions.append("Search social media platforms for conflicting usage.")
    if classes:
        suggestions.append(f"Focus search on Nice Classification classes: {classes}.")
    risk = "HIGH" if len(risk_factors) > 2 else "MEDIUM" if risk_factors else "LOW"
    return {"mark": mark, "industry": industry, "risk_level": risk,
            "risk_factors": risk_factors or ["No obvious pattern-based risks detected."],
            "recommendations": suggestions, "note": "This is pattern-based analysis only. A professional trademark search is strongly recommended." + DISCLAIMER}


def _legal_research(topic: str = "", jurisdiction: str = "Federal",
                    area_of_law: str = "") -> Dict[str, Any]:
    areas = {
        "contract": {"statutes": ["UCC Article 2", "Restatement (Second) of Contracts"], "concepts": ["Offer and acceptance", "Consideration", "Breach and remedies", "Statute of frauds"]},
        "employment": {"statutes": ["Fair Labor Standards Act (FLSA)", "Title VII of the Civil Rights Act", "Americans with Disabilities Act (ADA)", "Family and Medical Leave Act (FMLA)"], "concepts": ["At-will employment", "Wrongful termination", "Workplace discrimination", "Wage and hour compliance"]},
        "intellectual property": {"statutes": ["Patent Act (35 U.S.C.)", "Copyright Act (17 U.S.C.)", "Lanham Act (15 U.S.C.)", "Defend Trade Secrets Act"], "concepts": ["Patentability", "Fair use", "Trademark infringement", "Trade secret misappropriation"]},
        "business": {"statutes": ["Delaware General Corporation Law", "Revised Uniform LLC Act", "Securities Act of 1933", "Sherman Antitrust Act"], "concepts": ["Fiduciary duties", "Piercing the corporate veil", "Mergers and acquisitions", "Securities compliance"]},
        "privacy": {"statutes": ["GDPR (EU)", "CCPA (California)", "HIPAA", "COPPA", "FERPA"], "concepts": ["Data minimization", "Consent requirements", "Breach notification", "Data subject rights"]},
        "tort": {"statutes": ["Restatement (Third) of Torts", "State tort reform statutes"], "concepts": ["Negligence", "Strict liability", "Intentional torts", "Damages and remedies"]},
    }
    matched = areas.get(area_of_law.lower(), None)
    if not matched:
        for key in areas:
            if key in topic.lower() or key in area_of_law.lower():
                matched = areas[key]
                break
    if not matched:
        matched = {"statutes": ["Research specific statutes for this area"], "concepts": ["Consult a legal database (Westlaw, LexisNexis) for comprehensive research"]}
    return {"topic": topic, "jurisdiction": jurisdiction, "area_of_law": area_of_law,
            "relevant_statutes": matched["statutes"], "key_concepts": matched["concepts"],
            "research_resources": ["Westlaw", "LexisNexis", "Google Scholar (case law)", "Congress.gov (federal statutes)", "State legislature websites"],
            "note": "This provides a starting framework. Comprehensive legal research requires access to legal databases." + DISCLAIMER}


def _corporate_formation(entity_type: str = "llc", company_name: str = "",
                         state: str = "Delaware", members: str = "",
                         purpose: str = "any lawful business") -> Dict[str, Any]:
    templates = {
        "llc": ("ARTICLES OF ORGANIZATION", [
            ("Name", f"The name of the limited liability company is {company_name or '[COMPANY NAME]'}, LLC."),
            ("Registered Agent", f"The registered agent in {state} shall be designated upon filing."),
            ("Purpose", f"The company is organized for the purpose of {purpose}."),
            ("Members", members or "Member names and ownership percentages to be specified in the Operating Agreement."),
            ("Management", "The LLC shall be member-managed unless otherwise specified in the Operating Agreement."),
            ("Duration", "The LLC shall have perpetual duration."),
            ("Operating Agreement", "The members shall adopt an Operating Agreement governing the internal affairs of the company."),
        ]),
        "corp": ("ARTICLES OF INCORPORATION", [
            ("Name", f"The name of the corporation is {company_name or '[COMPANY NAME]'}, Inc."),
            ("Registered Agent", f"The registered agent in {state} shall be designated upon filing."),
            ("Purpose", f"The corporation is organized for {purpose}."),
            ("Authorized Shares", "The corporation is authorized to issue 10,000,000 shares of common stock, par value $0.001 per share."),
            ("Directors", members or "Initial directors to be named in the bylaws."),
            ("Incorporator", "The incorporator's name and address shall be provided upon filing."),
            ("Bylaws", "The Board of Directors shall adopt bylaws for the governance of the corporation."),
        ]),
        "s-corp": ("ARTICLES OF INCORPORATION (S-Corporation Election)", [
            ("Name", f"The name of the corporation is {company_name or '[COMPANY NAME]'}, Inc."),
            ("S-Corp Election", "The corporation intends to elect S-Corporation status by filing IRS Form 2553 within 75 days of incorporation."),
            ("Shareholders", members or "Shareholders to be named. Note: S-Corps are limited to 100 shareholders, all must be U.S. citizens/residents."),
            ("Stock", "The corporation shall issue only one class of stock as required for S-Corp status."),
            ("Fiscal Year", "The corporation shall adopt a calendar year fiscal year."),
            ("Purpose", f"The corporation is organized for {purpose}."),
        ]),
    }
    title, sections = templates.get(entity_type.lower(), templates["llc"])
    doc = f"# {title}\n\n**State of Formation:** {state}\n**Date:** {datetime.now().strftime('%B %d, %Y')}\n\n"
    for heading, content in sections:
        doc += f"## {heading}\n{content}\n\n"
    return {"document": doc + DISCLAIMER, "entity_type": entity_type, "next_steps": [
        f"File with {state} Secretary of State", "Obtain EIN from IRS",
        "Open business bank account", "Draft operating agreement/bylaws",
        "Obtain necessary licenses and permits"]}


def _ip_protection(ip_type: str = "overview", asset_name: str = "",
                   description: str = "", industry: str = "") -> Dict[str, Any]:
    strategies = {
        "patent": {"protection": "Utility or design patent via USPTO", "duration": "20 years (utility) / 15 years (design)", "steps": ["Conduct prior art search", "File provisional patent application ($320 small entity)", "File non-provisional within 12 months", "Respond to office actions", "Maintain with periodic fees"], "cost_range": "$5,000 - $15,000+"},
        "trademark": {"protection": "Federal trademark registration via USPTO", "duration": "Indefinite with renewals every 10 years", "steps": ["Search USPTO TESS database", "File application (TEAS Plus $250/class)", "Respond to office actions", "Publish for opposition", "Register and maintain"], "cost_range": "$1,000 - $5,000"},
        "copyright": {"protection": "Copyright registration via US Copyright Office", "duration": "Life of author + 70 years", "steps": ["Document creation date", "Register with US Copyright Office ($65 online)", "Include copyright notice on works", "Consider Creative Commons licensing if sharing"], "cost_range": "$65 - $500"},
        "trade_secret": {"protection": "Internal policies and NDAs under DTSA/state law", "duration": "Indefinite while secret is maintained", "steps": ["Identify and classify trade secrets", "Implement access controls", "Require NDAs for employees/contractors", "Mark documents as confidential", "Conduct regular audits"], "cost_range": "$500 - $5,000 (NDA/policy drafting)"},
    }
    if ip_type == "overview":
        return {"asset": asset_name, "strategies": strategies, "recommendation": "Evaluate which IP protections apply to your specific assets. Most businesses benefit from a combination of protections." + DISCLAIMER}
    s = strategies.get(ip_type, strategies["trademark"])
    return {"asset": asset_name, "ip_type": ip_type, "description": description, **s, "note": DISCLAIMER}


def _compliance_audit(business_type: str = "", industry: str = "",
                      employee_count: int = 0, state: str = "",
                      areas: str = "all") -> Dict[str, Any]:
    checks = {}
    checks["labor_law"] = {
        "items": ["Wage and hour compliance (FLSA)", "Employee classification (W-2 vs 1099)", "Anti-discrimination policies (Title VII, ADA)", "Workplace safety (OSHA)", "Workers' compensation insurance"],
        "applicable": employee_count > 0,
        "threshold_notes": []
    }
    if employee_count >= 15:
        checks["labor_law"]["threshold_notes"].append("15+ employees: Title VII, ADA apply")
    if employee_count >= 50:
        checks["labor_law"]["threshold_notes"].append("50+ employees: FMLA, ACA employer mandate apply")
    checks["data_privacy"] = {
        "items": ["Privacy policy published and current", "Data breach notification procedures", "Cookie consent mechanisms", "Data processing agreements with vendors", "Employee data handling policies"],
        "frameworks": ["GDPR (if EU customers)", "CCPA (if CA customers)", "HIPAA (if health data)", "PCI DSS (if payment data)"]
    }
    checks["ada_accessibility"] = {
        "items": ["Website WCAG 2.1 compliance", "Physical premises accessibility", "Reasonable accommodation policies", "Service animal policies"]
    }
    checks["corporate_governance"] = {
        "items": ["Annual report filings current", "Business licenses valid", "Registered agent designated", "Meeting minutes maintained", "Operating agreement/bylaws up to date"]
    }
    industry_checks = {
        "healthcare": ["HIPAA compliance", "Medical licensing", "Clinical trial regulations", "FDA approvals"],
        "finance": ["SEC registration", "Anti-money laundering (AML)", "Know Your Customer (KYC)", "SOX compliance"],
        "food": ["FDA food safety", "Health department permits", "Allergen labeling", "HACCP plan"],
        "technology": ["SOC 2 compliance", "Data encryption standards", "Incident response plan", "Software licensing"],
        "retail": ["Consumer protection laws", "Product liability insurance", "Return/refund policies", "Sales tax compliance"],
    }
    ind = industry.lower()
    for key, items in industry_checks.items():
        if key in ind:
            checks["industry_specific"] = {"industry": key, "items": items}
    return {"business_type": business_type, "state": state, "employee_count": employee_count,
            "compliance_checklist": checks, "recommendation": "Address high-priority items first. Consider engaging a compliance consultant for a thorough audit." + DISCLAIMER}


def _dispute_resolution(dispute_type: str = "mediation",
                        parties: str = "", dispute_description: str = "",
                        preferred_location: str = "",
                        governing_law: str = "State of Delaware") -> Dict[str, Any]:
    clauses = {
        "mediation": f"## Mediation Clause\n\nAny dispute arising out of or relating to this agreement shall first be submitted to mediation administered by a mutually agreed mediator in {preferred_location or governing_law}. The parties shall share mediation costs equally. If mediation fails to resolve the dispute within 60 days, either party may pursue binding arbitration or litigation.",
        "arbitration": f"## Binding Arbitration Clause\n\nAny dispute arising out of or relating to this agreement shall be resolved by binding arbitration in {preferred_location or governing_law}, administered by the American Arbitration Association (AAA) under its Commercial Arbitration Rules. The arbitrator's decision shall be final and enforceable in any court of competent jurisdiction. Each party shall bear its own costs unless the arbitrator rules otherwise.",
        "mediation_then_arbitration": f"## Mediation-Arbitration Clause\n\nAny dispute shall first be submitted to mediation in {preferred_location or governing_law}. If unresolved within 30 days, the dispute shall proceed to binding arbitration under AAA rules. The arbitrator's award shall be final and binding.",
        "litigation": f"## Jurisdiction and Venue Clause\n\nAny legal action arising from this agreement shall be brought exclusively in the courts of {governing_law}. The parties consent to personal jurisdiction and venue in said courts. The prevailing party shall be entitled to reasonable attorney's fees.",
    }
    clause = clauses.get(dispute_type, clauses["mediation"])
    result = f"# DISPUTE RESOLUTION — {dispute_type.upper().replace('_', ' ')}\n\n"
    result += f"**Parties:** {parties or '[PARTIES]'}\n"
    result += f"**Re:** {dispute_description or '[DISPUTE DESCRIPTION]'}\n"
    result += f"**Governing Law:** {governing_law}\n\n"
    result += clause + "\n"
    return {"clause": result + DISCLAIMER, "dispute_type": dispute_type,
            "recommended_steps": ["Document all communications", "Preserve relevant evidence",
                                  "Review existing contractual obligations", "Consider settlement before escalation",
                                  "Engage qualified legal counsel"]}


def _raw_tools():
    return [
        {"name": "contract_generator", "description": "Generate contracts (NDA, service agreement, partnership, freelance, employment)",
         "parameters": {"type": "object", "properties": {
             "contract_type": {"type": "string", "enum": ["nda", "service_agreement", "partnership", "freelance", "employment"]},
             "party_a": {"type": "string"}, "party_b": {"type": "string"},
             "terms": {"type": "string"}, "duration": {"type": "string"},
             "governing_law": {"type": "string"}, "additional_clauses": {"type": "string"},
         }, "required": ["contract_type"]}, "function": _contract_generator},
        {"name": "legal_letter", "description": "Generate legal letters (cease and desist, demand, termination notice, intent to sue)",
         "parameters": {"type": "object", "properties": {
             "letter_type": {"type": "string", "enum": ["cease_and_desist", "demand_letter", "notice_of_termination", "intent_to_sue"]},
             "sender": {"type": "string"}, "recipient": {"type": "string"},
             "subject": {"type": "string"}, "details": {"type": "string"},
             "deadline": {"type": "string"}, "governing_law": {"type": "string"},
         }, "required": ["letter_type"]}, "function": _legal_letter},
        {"name": "terms_of_service", "description": "Generate website terms of service",
         "parameters": {"type": "object", "properties": {
             "company_name": {"type": "string"}, "website_url": {"type": "string"},
             "services_description": {"type": "string"}, "governing_law": {"type": "string"},
             "contact_email": {"type": "string"},
         }}, "function": _terms_of_service},
        {"name": "privacy_policy", "description": "Generate GDPR/CCPA compliant privacy policy",
         "parameters": {"type": "object", "properties": {
             "company_name": {"type": "string"}, "website_url": {"type": "string"},
             "data_collected": {"type": "string"}, "third_party_sharing": {"type": "boolean"},
             "cookie_usage": {"type": "boolean"}, "contact_email": {"type": "string"},
             "gdpr": {"type": "boolean"}, "ccpa": {"type": "boolean"},
         }}, "function": _privacy_policy},
        {"name": "trademark_search", "description": "Analyze a trademark for potential conflicts using pattern analysis",
         "parameters": {"type": "object", "properties": {
             "mark": {"type": "string"}, "industry": {"type": "string"}, "classes": {"type": "string"},
         }, "required": ["mark"]}, "function": _trademark_search},
        {"name": "legal_research", "description": "Research legal topics with statute citations and key concepts",
         "parameters": {"type": "object", "properties": {
             "topic": {"type": "string"}, "jurisdiction": {"type": "string"}, "area_of_law": {"type": "string"},
         }, "required": ["topic"]}, "function": _legal_research},
        {"name": "corporate_formation", "description": "Generate articles of incorporation, bylaws, operating agreements",
         "parameters": {"type": "object", "properties": {
             "entity_type": {"type": "string", "enum": ["llc", "corp", "s-corp"]},
             "company_name": {"type": "string"}, "state": {"type": "string"},
             "members": {"type": "string"}, "purpose": {"type": "string"},
         }, "required": ["entity_type"]}, "function": _corporate_formation},
        {"name": "ip_protection", "description": "Intellectual property protection strategy (patents, trademarks, copyrights, trade secrets)",
         "parameters": {"type": "object", "properties": {
             "ip_type": {"type": "string", "enum": ["overview", "patent", "trademark", "copyright", "trade_secret"]},
             "asset_name": {"type": "string"}, "description": {"type": "string"}, "industry": {"type": "string"},
         }}, "function": _ip_protection},
        {"name": "compliance_audit", "description": "Audit a business for legal compliance (labor, ADA, privacy, industry-specific)",
         "parameters": {"type": "object", "properties": {
             "business_type": {"type": "string"}, "industry": {"type": "string"},
             "employee_count": {"type": "integer"}, "state": {"type": "string"},
             "areas": {"type": "string"},
         }}, "function": _compliance_audit},
        {"name": "dispute_resolution", "description": "Generate mediation/arbitration clauses and dispute resolution frameworks",
         "parameters": {"type": "object", "properties": {
             "dispute_type": {"type": "string", "enum": ["mediation", "arbitration", "mediation_then_arbitration", "litigation"]},
             "parties": {"type": "string"}, "dispute_description": {"type": "string"},
             "preferred_location": {"type": "string"}, "governing_law": {"type": "string"},
         }}, "function": _dispute_resolution},
    ]


def get_tools():
    return adapt_tools(_raw_tools())
