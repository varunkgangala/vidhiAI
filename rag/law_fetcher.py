import os
import json
import hashlib

LAW_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "law_cache")

# Curated legal knowledge base for contract compliance
LAW_DATABASE = {
    "general_contract": """
GENERAL CONTRACT LAW PRINCIPLES (Indian Contract Act, 1872 & International Standards):
1. Offer and Acceptance: A valid contract requires a clear offer and unambiguous acceptance.
2. Consideration: Every contract must have lawful consideration from both parties.
3. Free Consent: Consent must be free from coercion, undue influence, fraud, or misrepresentation.
4. Capacity to Contract: Parties must be of legal age and sound mind.
5. Lawful Object: The contract purpose must not be illegal, immoral, or against public policy.
6. Certainty: Terms must be clear, definite, and not vague.
7. Possibility of Performance: The contract must be capable of being performed.
8. Termination Clauses: Must specify valid grounds and notice period.
9. Dispute Resolution: Should include arbitration or litigation jurisdiction.
10. Force Majeure: Should address unforeseeable circumstances.
""",
    "employment": """
EMPLOYMENT LAW REGULATIONS (Indian Labour Laws & International Labour Organization Standards):
1. Minimum Wages Act, 1948: Compensation must meet or exceed statutory minimum wages.
2. Payment of Wages Act, 1936: Timely salary payment obligations.
3. Contract Labour (R&A) Act, 1970: Regulations for contract workers.
4. Equal Remuneration Act, 1976: No gender-based wage discrimination.
5. Maternity Benefit Act, 1961: Mandatory maternity leave provisions.
6. Gratuity Act, 1972: Gratuity entitlement after 5 years of service.
7. Provident Fund & ESI: Mandatory social security contributions.
8. Sexual Harassment of Women at Workplace Act, 2013: POSH compliance required.
9. Industrial Disputes Act, 1947: Termination procedures and notice periods.
10. Non-compete and NDA clauses must be reasonable in scope and duration.
""",
    "nda": """
NON-DISCLOSURE AGREEMENT REGULATIONS:
1. Definition of Confidential Information must be clearly defined and not overly broad.
2. Duration: Must specify a reasonable confidentiality period (typically 2–5 years).
3. Exclusions: Must list information not covered (public domain, independently developed).
4. Obligations of Receiving Party must be clearly stated.
5. Permitted Disclosures: Legal disclosures (court orders) must be addressed.
6. Return/Destruction: Protocol for confidential material upon termination.
7. Remedies: Injunctive relief and damages clauses must be proportionate.
8. Jurisdiction: Governing law must be specified.
9. Trade Secrets Protection Act compliance.
10. No overly broad restrictions that would prevent normal business activities.
""",
    "service_agreement": """
SERVICE AGREEMENT REGULATIONS (Indian IT Act, Consumer Protection Act):
1. Scope of Services must be clearly and specifically defined.
2. Deliverables and timelines must be explicit.
3. Payment Terms: Milestones, invoicing, and late payment penalties must comply with law.
4. Intellectual Property: Ownership of work product must be explicitly assigned.
5. Warranties and Representations must be truthful and not misleading.
6. Limitation of Liability: Cannot exclude liability for gross negligence or fraud.
7. Indemnification clauses must be mutual and reasonable.
8. Data Protection: Compliance with IT Act 2000 and PDPB 2023 requirements.
9. SLA: Service level agreements must be measurable and enforceable.
10. Termination: Convenience termination notice period must be reasonable (30–90 days).
""",
    "lease": """
LEASE/RENTAL AGREEMENT REGULATIONS (Transfer of Property Act, 1882; Rent Control Acts):
1. Description of Property must be precise and unambiguous.
2. Rent Amount and due dates must be clearly stated.
3. Security Deposit: Amount and refund conditions must comply with local Rent Control Acts.
4. Duration: Fixed-term or periodic tenancy must be clearly defined.
5. Maintenance Responsibilities must be allocated between landlord and tenant.
6. Permitted Use must be specified; changes require consent.
7. Sub-letting: Prohibition or permission must be explicit.
8. Eviction: Grounds and notice period must comply with local Rent Control Act.
9. Stamp Duty: Lease must be properly stamped per Indian Stamp Act.
10. Registration: Leases exceeding 11 months must be registered per Registration Act.
""",
}


def _cache_path(key: str) -> str:
    os.makedirs(LAW_CACHE_DIR, exist_ok=True)
    safe = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(LAW_CACHE_DIR, f"{safe}.json")


def _load_cache(key: str):
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f).get("content")
    return None


def _save_cache(key: str, content: str):
    path = _cache_path(key)
    with open(path, "w") as f:
        json.dump({"key": key, "content": content}, f)


def detect_contract_type(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["employee", "employer", "salary", "designation", "probation"]):
        return "employment"
    if any(w in text_lower for w in ["non-disclosure", "confidential", "nda", "proprietary"]):
        return "nda"
    if any(w in text_lower for w in ["service provider", "client", "deliverable", "sla", "scope of work"]):
        return "service_agreement"
    if any(w in text_lower for w in ["tenant", "landlord", "rent", "lease", "premises", "lessee"]):
        return "lease"
    return "general_contract"


def fetch_relevant_laws(contract_text: str) -> dict:
    contract_type = detect_contract_type(contract_text)
    cache_key = f"laws_{contract_type}"
    cached = _load_cache(cache_key)
    if cached:
        return {"contract_type": contract_type, "laws": cached, "source": "cache"}

    laws = LAW_DATABASE.get(contract_type, LAW_DATABASE["general_contract"])
    # Always also include general contract principles
    if contract_type != "general_contract":
        laws = LAW_DATABASE["general_contract"] + "\n\n" + laws

    _save_cache(cache_key, laws)
    return {"contract_type": contract_type, "laws": laws, "source": "database"}
