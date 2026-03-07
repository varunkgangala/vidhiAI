from typing import List, Dict


RISK_KEYWORDS = {
    "High": [
        "unlimited liability", "irrevocable", "perpetual", "waive all rights",
        "no termination", "penalty", "forfeit", "void", "null and void",
        "unilateral", "sole discretion", "without notice", "immediate termination",
        "non-negotiable", "absolute obligation"
    ],
    "Medium": [
        "may terminate", "reasonable notice", "discretion", "subject to change",
        "best efforts", "commercially reasonable", "material breach",
        "liquidated damages", "indemnify", "hold harmless", "at will"
    ],
    "Low": [
        "mutual agreement", "written notice", "thirty days", "sixty days",
        "arbitration", "mediation", "governing law", "severability",
        "entire agreement", "amendment in writing", "counterparts"
    ]
}

MISSING_CLAUSE_PATTERNS = {
    "Termination Clause": ["terminat", "end of agreement", "expiry", "notice period"],
    "Dispute Resolution": ["arbitration", "mediation", "dispute", "jurisdiction"],
    "Force Majeure": ["force majeure", "act of god", "unforeseen", "circumstances beyond"],
    "Governing Law": ["governing law", "governed by", "applicable law", "laws of"],
    "Limitation of Liability": ["limitation of liability", "liability cap", "maximum liability"],
    "Intellectual Property": ["intellectual property", "copyright", "patent", "ownership of work"],
    "Confidentiality": ["confidential", "non-disclosure", "proprietary", "trade secret"],
    "Payment Terms": ["payment", "invoice", "due date", "compensation", "remuneration"],
    "Amendment Clause": ["amendment", "modification", "changes to this agreement"],
    "Severability": ["severability", "severable", "invalid provision"],
}


def classify_risk(detected_risks: List[Dict]) -> str:
    """Classify overall risk based on detected risks list."""
    if not detected_risks:
        return "Low"
    severities = [r.get("severity", "Low") for r in detected_risks]
    if severities.count("High") >= 2:
        return "High"
    if "High" in severities or severities.count("Medium") >= 3:
        return "Medium"
    return "Low"


def scan_text_for_risks(text: str) -> List[Dict]:
    """Scan contract text for risky language patterns."""
    text_lower = text.lower()
    risks = []
    seen = set()
    for severity, keywords in RISK_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower and kw not in seen:
                seen.add(kw)
                risks.append({
                    "risk": f"Potentially problematic language detected: '{kw}'",
                    "severity": severity,
                    "section": "General"
                })
    return risks[:8]


def find_missing_clauses(text: str) -> List[str]:
    """Detect commonly required clauses that are absent."""
    text_lower = text.lower()
    missing = []
    for clause_name, patterns in MISSING_CLAUSE_PATTERNS.items():
        if not any(p in text_lower for p in patterns):
            missing.append(clause_name)
    return missing
