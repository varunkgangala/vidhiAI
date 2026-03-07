from analysis.risk_analyzer import MISSING_CLAUSE_PATTERNS


ESSENTIAL_CLAUSES = [
    "Termination Clause",
    "Dispute Resolution",
    "Governing Law",
    "Payment Terms",
]

IMPORTANT_CLAUSES = [
    "Force Majeure",
    "Limitation of Liability",
    "Intellectual Property",
    "Confidentiality",
]

NICE_TO_HAVE_CLAUSES = [
    "Amendment Clause",
    "Severability",
]


def compute_compliance_score(contract_text: str, llm_score: int = None) -> dict:
    """Compute a compliance score and breakdown."""
    if llm_score is not None:
        return {"score": llm_score, "grade": _score_to_grade(llm_score)}

    text_lower = contract_text.lower()
    total = 0
    max_score = 0

    # Essential clauses (40% weight)
    essential_present = 0
    for clause in ESSENTIAL_CLAUSES:
        patterns = MISSING_CLAUSE_PATTERNS.get(clause, [])
        if any(p in text_lower for p in patterns):
            essential_present += 1
    essential_score = (essential_present / len(ESSENTIAL_CLAUSES)) * 40
    total += essential_score
    max_score += 40

    # Important clauses (35% weight)
    important_present = 0
    for clause in IMPORTANT_CLAUSES:
        patterns = MISSING_CLAUSE_PATTERNS.get(clause, [])
        if any(p in text_lower for p in patterns):
            important_present += 1
    important_score = (important_present / len(IMPORTANT_CLAUSES)) * 35
    total += important_score
    max_score += 35

    # Nice to have (15% weight)
    nice_present = 0
    for clause in NICE_TO_HAVE_CLAUSES:
        patterns = MISSING_CLAUSE_PATTERNS.get(clause, [])
        if any(p in text_lower for p in patterns):
            nice_present += 1
    nice_score = (nice_present / len(NICE_TO_HAVE_CLAUSES)) * 15
    total += nice_score
    max_score += 15

    # Clarity bonus (10% weight)
    word_count = len(contract_text.split())
    clarity = 10 if word_count > 300 else (5 if word_count > 100 else 2)
    total += clarity

    final = round(min(100, total))
    return {"score": final, "grade": _score_to_grade(final)}


def _score_to_grade(score: int) -> str:
    if score >= 85:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 55:
        return "C"
    elif score >= 40:
        return "D"
    return "F"
