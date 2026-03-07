import json
import re
import os
import random

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def _call_claude_api(prompt: str) -> str | None:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import urllib.request
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"]
    except Exception:
        return None


def _simulate_analysis(prompt: str) -> dict:
    """Simulate a realistic LLM response based on prompt content."""
    prompt_lower = prompt.lower()

    # Detect contract quality signals from the text
    has_termination = any(w in prompt_lower for w in ["terminat", "notice period", "30 days", "60 days"])
    has_dispute = any(w in prompt_lower for w in ["arbitration", "dispute", "jurisdiction", "court"])
    has_confidential = any(w in prompt_lower for w in ["confidential", "non-disclosure", "proprietary"])
    has_payment = any(w in prompt_lower for w in ["payment", "salary", "compensation", "remuneration"])
    has_ip = any(w in prompt_lower for w in ["intellectual property", "copyright", "patent", "ownership"])
    has_liability = any(w in prompt_lower for w in ["liability", "indemnif", "limitation"])
    has_force_majeure = any(w in prompt_lower for w in ["force majeure", "act of god", "unforeseen"])
    has_governing_law = any(w in prompt_lower for w in ["governing law", "governed by", "applicable law"])

    signals = sum([has_termination, has_dispute, has_confidential, has_payment,
                   has_ip, has_liability, has_force_majeure, has_governing_law])

    base_score = 35 + (signals * 8) + random.randint(-5, 5)
    compliance_score = max(20, min(95, base_score))

    if compliance_score >= 75:
        risk_level = "Low"
    elif compliance_score >= 50:
        risk_level = "Medium"
    else:
        risk_level = "High"

    missing_clauses = []
    if not has_termination:
        missing_clauses.append("Termination clause with adequate notice period")
    if not has_dispute:
        missing_clauses.append("Dispute resolution / arbitration clause")
    if not has_force_majeure:
        missing_clauses.append("Force majeure / act of God clause")
    if not has_governing_law:
        missing_clauses.append("Governing law and jurisdiction clause")
    if not has_liability:
        missing_clauses.append("Limitation of liability clause")
    if not has_ip:
        missing_clauses.append("Intellectual property ownership clause")
    if not missing_clauses:
        missing_clauses.append("Severability clause")

    detected_risks = []
    if not has_payment:
        detected_risks.append({
            "risk": "Payment terms are ambiguous or missing — creates financial and enforcement risk",
            "severity": "High",
            "section": "Payment Terms"
        })
    if not has_termination:
        detected_risks.append({
            "risk": "No clear termination procedure — may lead to disputes on contract exit",
            "severity": "High",
            "section": "Termination"
        })
    if not has_dispute:
        detected_risks.append({
            "risk": "No dispute resolution mechanism — parties may face costly litigation",
            "severity": "Medium",
            "section": "Dispute Resolution"
        })
    if not has_governing_law:
        detected_risks.append({
            "risk": "Governing law not specified — unclear which jurisdiction's laws apply",
            "severity": "Medium",
            "section": "General"
        })
    if not has_liability:
        detected_risks.append({
            "risk": "Unlimited liability exposure — no cap on damages in case of breach",
            "severity": "High" if compliance_score < 55 else "Medium",
            "section": "Liability"
        })
    if not detected_risks:
        detected_risks.append({
            "risk": "Contract appears reasonably comprehensive; minor procedural gaps noted",
            "severity": "Low",
            "section": "General"
        })

    contract_type = "General"
    if "employment" in prompt_lower or "employee" in prompt_lower:
        contract_type = "Employment"
        referenced_laws = [
            "Indian Contract Act, 1872",
            "Industrial Disputes Act, 1947",
            "Minimum Wages Act, 1948",
            "Payment of Wages Act, 1936",
            "Sexual Harassment of Women at Workplace Act, 2013 (POSH)",
            "Employees' Provident Funds Act, 1952"
        ]
    elif "nda" in prompt_lower or "non-disclosure" in prompt_lower:
        contract_type = "NDA"
        referenced_laws = [
            "Indian Contract Act, 1872 (Sections 27, 73–74)",
            "Information Technology Act, 2000",
            "Trade Secrets Protection principles",
            "Personal Data Protection Bill, 2023"
        ]
    elif "service" in prompt_lower:
        contract_type = "Service Agreement"
        referenced_laws = [
            "Indian Contract Act, 1872",
            "Information Technology Act, 2000",
            "Consumer Protection Act, 2019",
            "Indian Copyright Act, 1957 (IP provisions)"
        ]
    else:
        referenced_laws = [
            "Indian Contract Act, 1872",
            "Specific Relief Act, 1963",
            "Indian Stamp Act, 1899",
            "Registration Act, 1908"
        ]

    score_desc = "strong" if compliance_score >= 75 else ("moderate" if compliance_score >= 50 else "weak")
    explanation = (
        f"This {contract_type} contract demonstrates {score_desc} legal compliance with a score of {compliance_score}%. "
        f"{'The contract covers most essential elements required under applicable Indian law, though some refinements are recommended.' if compliance_score >= 75 else 'Several critical provisions are either missing or inadequately addressed, creating significant legal exposure for both parties.'} "
        f"A total of {len(detected_risks)} risk(s) were identified across the document.\n\n"
        f"{'The contract would benefit from strengthening clauses related to: ' + ', '.join(missing_clauses[:3]) + '.' if missing_clauses else 'The contract structure is sound.'} "
        f"{'Particular attention should be paid to ensuring compliance with ' + referenced_laws[0] + ' requirements.' if referenced_laws else ''}\n\n"
        f"It is strongly recommended that a qualified legal professional review this contract before execution. "
        f"The identified gaps, if unaddressed, could result in disputes, financial penalties, or unenforceability of key provisions."
    )

    recommendations = [
        f"Add a comprehensive {missing_clauses[0].lower()}" if missing_clauses else "Review all clauses for clarity",
        "Ensure all monetary amounts comply with statutory minimums under applicable law",
        "Include a severability clause to preserve contract validity if one clause is struck down",
        "Specify clear timelines for all obligations and deliverables",
        "Have the contract reviewed and stamped by a notary or legal counsel",
    ]

    return {
        "compliance_score": compliance_score,
        "risk_level": risk_level,
        "missing_clauses": missing_clauses[:6],
        "detected_risks": detected_risks[:6],
        "explanation": explanation,
        "referenced_laws": referenced_laws,
        "recommendations": recommendations[:5]
    }


def run_llm_analysis(prompt: str) -> dict:
    """Try Claude API first, fall back to simulation."""
    raw = _call_claude_api(prompt)
    if raw:
        try:
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

    # Simulation fallback
    return _simulate_analysis(prompt)
