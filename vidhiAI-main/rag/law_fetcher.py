import os
import json
import re
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import time

from dotenv import load_dotenv
load_dotenv(override=True)

LAW_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "law_cache")

# Cache expiry — 24 hours
CACHE_EXPIRY = 86400

# ── CourtListener API ─────────────────────────────────────────────────────────
# Get your token from: https://www.courtlistener.com/sign-in/
# Add to .env: COURTLISTENER_TOKEN=your_token_here
COURTLISTENER_TOKEN = os.environ.get("COURTLISTENER_TOKEN", "")
COURTLISTENER_BASE  = "https://www.courtlistener.com/api/rest/v4"

# ── Search terms per contract type ────────────────────────────────────────────

CONTRACT_SEARCH_TERMS = {
    "employment": [
        "employment contract termination notice period",
        "wrongful termination employment agreement",
        "non compete clause employment enforceability",
        "salary wages payment employment law",
    ],
    "nda": [
        "non disclosure agreement confidentiality breach",
        "trade secret misappropriation confidential information",
        "NDA enforceability restraint of trade",
        "confidential information definition scope",
    ],
    "service_agreement": [
        "service agreement breach of contract scope of work",
        "independent contractor service obligations deliverables",
        "limitation of liability service contract",
        "intellectual property ownership service agreement",
    ],
    "lease": [
        "lease agreement landlord tenant eviction",
        "security deposit refund rental agreement",
        "commercial lease termination breach",
        "subletting assignment lease agreement",
    ],
    "general_contract": [
        "breach of contract damages remedies",
        "contract formation offer acceptance consideration",
        "force majeure clause enforceability",
        "dispute resolution arbitration clause contract",
    ],
}

# ── Fallback law database ─────────────────────────────────────────────────────

FALLBACK_LAW_DATABASE = {
    "general_contract": """
GENERAL CONTRACT LAW - Indian Contract Act, 1872:
1. Offer and Acceptance (Sections 2-9): Valid contract requires clear offer and unambiguous acceptance.
2. Consideration (Section 2(d), 25): Every contract must have lawful consideration from both parties.
3. Free Consent (Sections 13-22): Consent must be free from coercion, undue influence, fraud, misrepresentation.
4. Capacity to Contract (Sections 11-12): Parties must be of legal age (18+) and sound mind.
5. Lawful Object (Section 23): Contract purpose must not be illegal, immoral, or against public policy.
6. Certainty (Section 29): Terms must be clear, definite, and not vague.
7. Possibility of Performance (Section 56): Contract must be capable of being performed.
8. Termination: Must specify valid grounds and notice period.
9. Dispute Resolution: Should include arbitration (Arbitration & Conciliation Act, 1996) or jurisdiction.
10. Force Majeure: Should address unforeseeable circumstances beyond parties control.
11. Specific Relief Act, 1963: Governs enforcement and remedies for breach of contract.
12. Indian Stamp Act, 1899: Contracts must be properly stamped to be admissible as evidence.
13. Registration Act, 1908: Certain contracts require compulsory registration.
14. Limitation Act, 1963: Suits for breach of contract must be filed within 3 years.
""",
    "employment": """
EMPLOYMENT LAW - India 2024:
1. Industrial Disputes Act, 1947: Termination requires valid reason and notice. Retrenchment needs compensation.
2. Minimum Wages Act, 1948: Compensation must meet or exceed state-specific statutory minimum wages.
3. Payment of Wages Act, 1936: Salary must be paid by 7th/10th of following month. No unauthorized deductions.
4. Contract Labour (R&A) Act, 1970: Regulations for contract and gig workers.
5. Equal Remuneration Act, 1976: No gender-based wage discrimination for same work.
6. Maternity Benefit Act, 1961 (Amended 2017): 26 weeks paid maternity leave mandatory.
7. Payment of Gratuity Act, 1972: Gratuity mandatory after 5 years continuous service.
8. Employees Provident Funds Act, 1952: 12% employer + 12% employee PF contribution mandatory.
9. ESI Act, 1948: ESI contributions mandatory for employees earning under Rs.21,000/month.
10. POSH Act, 2013: Internal Complaints Committee mandatory. Zero tolerance for sexual harassment.
11. Non-compete clauses post-employment are generally unenforceable under Section 27 of Indian Contract Act.
12. Notice period: Typically 30-90 days. Garden leave provisions should be specified.
""",
    "nda": """
NON-DISCLOSURE AGREEMENT LAW - India 2024:
1. Indian Contract Act, 1872 (Section 27): Restraint of trade clauses must be reasonable in scope and duration.
2. Definition of Confidential Information must be clearly and specifically defined.
3. Duration: Must specify reasonable confidentiality period (typically 2-5 years post-termination).
4. Exclusions: Must list excluded information - public domain, independently developed, third party.
5. Obligations: Receiving party obligations must be clearly stated.
6. Permitted Disclosures: Legal disclosures (court orders) must be addressed.
7. Return/Destruction: Protocol for confidential material upon termination must be specified.
8. Remedies: Injunctive relief and liquidated damages must be proportionate.
9. Information Technology Act, 2000: Data protection for electronic confidential information.
10. Digital Personal Data Protection Act, 2023: Consent and purpose limitation required.
""",
    "service_agreement": """
SERVICE AGREEMENT LAW - India 2024:
1. Indian Contract Act, 1872: Service obligations must be specific and measurable.
2. Scope of Services must be clearly defined to avoid disputes.
3. Information Technology Act, 2000: Governs IT/software agreements. Electronic signatures valid.
4. Consumer Protection Act, 2019: Unfair trade practices prohibited.
5. Indian Copyright Act, 1957: IP ownership of deliverables must be explicitly assigned in writing.
6. MSME Development Act, 2006: Payments to MSMEs within 45 days. Delayed payment attracts interest.
7. Limitation of Liability: Cannot exclude liability for gross negligence or fraud.
8. Digital Personal Data Protection Act, 2023: Compliance mandatory for personal data processing.
9. SLA: Service levels must be measurable with clear remedies for breach.
10. Termination: Convenience termination 30-90 days notice recommended.
11. GST: All invoicing must be GST compliant with proper HSN/SAC codes.
""",
    "lease": """
LEASE/RENTAL AGREEMENT LAW - India 2024:
1. Transfer of Property Act, 1882 (Sections 105-117): Governs all lease agreements in India.
2. Model Tenancy Act, 2021: Caps security deposit at 2 months rent for residential properties.
3. Registration Act, 1908: Leases exceeding 11 months MUST be registered.
4. Indian Stamp Act, 1899: Lease must be stamped at prescribed rates.
5. Rent Control Acts: State-specific legislation protects tenants from arbitrary eviction.
6. Security Deposit: Amount and refund timeline must be specified.
7. Rent Escalation: Annual increase percentage must be pre-agreed (typically 5-10%).
8. Maintenance responsibilities must be clearly allocated.
9. Permitted Use: Commercial/residential use must be specified.
10. Sub-letting: Prohibition or permission must be explicit.
11. Eviction: Grounds must comply with state Rent Control Act.
12. GST: Commercial property lease above threshold attracts 18% GST.
""",
}


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_path(key: str) -> str:
    os.makedirs(LAW_CACHE_DIR, exist_ok=True)
    safe = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(LAW_CACHE_DIR, f"{safe}.json")


def _load_cache(key: str) -> str | None:
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        if time.time() - data.get("timestamp", 0) > CACHE_EXPIRY:
            print(f"[VidhiAI] Law cache expired - fetching fresh data")
            return None
        print(f"[VidhiAI] Laws loaded from cache (cached at {data.get('cached_at')})")
        return data.get("content")
    except Exception:
        return None


def _save_cache(key: str, content: str):
    path = _cache_path(key)
    with open(path, "w") as f:
        json.dump({
            "key": key,
            "content": content,
            "timestamp": time.time(),
            "cached_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=2)
    print(f"[VidhiAI] Laws cached at {time.strftime('%Y-%m-%d %H:%M:%S')} (valid 24h)")


# ── CourtListener API fetchers ────────────────────────────────────────────────

def _cl_headers() -> dict:
    """Return headers with Authorization token."""
    return {
        "Authorization": f"Token {COURTLISTENER_TOKEN}",
        "Content-Type":  "application/json",
        "User-Agent":    "VidhiAI Legal Research/1.0",
    }


def _fetch_opinions(query: str) -> str | None:
    """
    Search CourtListener opinions (court judgements).
    Returns formatted text of top results.
    """
    try:
        params = urllib.parse.urlencode({
            "q":        query,
            "type":     "o",          # opinions
            "order_by": "score desc",
            "stat_Precedential": "on",
        })
        url = f"{COURTLISTENER_BASE}/search/?{params}"
        req = urllib.request.Request(url, headers=_cl_headers())

        with urllib.request.urlopen(req, timeout=12) as resp:
            data    = json.loads(resp.read())
            results = data.get("results", [])

            if not results:
                return None

            texts = []
            for item in results[:3]:
                case_name  = item.get("caseName",    "Unknown Case")
                court      = item.get("court",       "")
                date       = item.get("dateFiled",   "")
                snippet    = item.get("snippet",     "")
                # Clean HTML
                snippet    = re.sub(r'<[^>]+>', ' ', snippet)
                snippet    = re.sub(r'\s+', ' ', snippet).strip()
                if snippet and len(snippet) > 50:
                    texts.append(
                        f"Case: {case_name} | Court: {court} | Date: {date}\n"
                        f"Excerpt: {snippet[:500]}"
                    )

            return "\n\n".join(texts) if texts else None

    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"[VidhiAI] CourtListener: Invalid token - check COURTLISTENER_TOKEN in .env")
        else:
            print(f"[VidhiAI] CourtListener opinions HTTP error: {e.code}")
        return None
    except Exception as e:
        print(f"[VidhiAI] CourtListener opinions error: {e}")
        return None


def _fetch_statutes(query: str) -> str | None:
    """
    Search CourtListener RECAP documents (legal filings and statutes).
    """
    try:
        params = urllib.parse.urlencode({
            "q":        query,
            "type":     "r",          # RECAP documents
            "order_by": "score desc",
        })
        url = f"{COURTLISTENER_BASE}/search/?{params}"
        req = urllib.request.Request(url, headers=_cl_headers())

        with urllib.request.urlopen(req, timeout=12) as resp:
            data    = json.loads(resp.read())
            results = data.get("results", [])

            if not results:
                return None

            texts = []
            for item in results[:3]:
                case_name = item.get("caseName",  "Unknown")
                court     = item.get("court",     "")
                snippet   = item.get("snippet",   "")
                snippet   = re.sub(r'<[^>]+>', ' ', snippet)
                snippet   = re.sub(r'\s+', ' ', snippet).strip()
                if snippet and len(snippet) > 50:
                    texts.append(
                        f"Document: {case_name} | Court: {court}\n"
                        f"Excerpt: {snippet[:500]}"
                    )

            return "\n\n".join(texts) if texts else None

    except Exception as e:
        print(f"[VidhiAI] CourtListener statutes error: {e}")
        return None


def _fetch_courtlistener_laws(contract_type: str) -> str | None:
    """
    Fetch real legal data from CourtListener for the contract type.
    Runs multiple queries and combines results.
    """
    if not COURTLISTENER_TOKEN:
        print("[VidhiAI] CourtListener token not set in .env - skipping real-time fetch")
        print("[VidhiAI] Add COURTLISTENER_TOKEN=your_token to .env file")
        return None

    search_terms = CONTRACT_SEARCH_TERMS.get(
        contract_type,
        CONTRACT_SEARCH_TERMS["general_contract"]
    )
    collected = []

    print(f"[VidhiAI] Fetching from CourtListener for: {contract_type}")

    # Fetch opinions (court judgements)
    for i, term in enumerate(search_terms[:3]):
        print(f"[VidhiAI] CourtListener opinions query {i+1}: '{term}'")
        result = _fetch_opinions(term)
        if result:
            collected.append(f"--- Court Opinions: {term} ---\n{result}")
            print(f"[VidhiAI] Got opinion results for: '{term}'")
        else:
            print(f"[VidhiAI] No opinion results for: '{term}'")
        time.sleep(0.3)  # small delay to respect rate limits

    # Fetch statutes/documents
    for i, term in enumerate(search_terms[:2]):
        print(f"[VidhiAI] CourtListener documents query {i+1}: '{term}'")
        result = _fetch_statutes(term)
        if result:
            collected.append(f"--- Legal Documents: {term} ---\n{result}")
            print(f"[VidhiAI] Got document results for: '{term}'")
        time.sleep(0.3)

    if collected:
        print(f"[VidhiAI] CourtListener: {len(collected)} sets of results fetched")
        return "\n\n".join(collected)

    print("[VidhiAI] CourtListener returned no results - using fallback database")
    return None


# ── Contract type detection ───────────────────────────────────────────────────

def detect_contract_type(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["employee", "employer", "salary", "designation", "probation", "employment"]):
        return "employment"
    if any(w in text_lower for w in ["non-disclosure", "confidential", "nda", "proprietary", "trade secret"]):
        return "nda"
    if any(w in text_lower for w in ["service provider", "client", "deliverable", "sla", "scope of work", "milestone"]):
        return "service_agreement"
    if any(w in text_lower for w in ["tenant", "landlord", "rent", "lease", "premises", "lessee", "lessor"]):
        return "lease"
    return "general_contract"


# ── Main fetch function ───────────────────────────────────────────────────────

def fetch_relevant_laws(contract_text: str) -> dict:
    """
    Fetch laws pipeline:
      1. Check cache (valid 24 hours)
      2. Fetch real-time from CourtListener API
      3. Combine with fallback Indian law database
      4. Cache and return
    """
    contract_type = detect_contract_type(contract_text)
    print(f"[VidhiAI] Contract type: {contract_type}")

    # Step 1: Check cache
    cache_key = f"cl_laws_{contract_type}"
    cached = _load_cache(cache_key)
    if cached:
        return {
            "contract_type": contract_type,
            "laws": cached,
            "source": "cache"
        }

    # Step 2: Fetch from CourtListener
    realtime_laws = _fetch_courtlistener_laws(contract_type)

    # Step 3: Combine with fallback
    fallback_laws = FALLBACK_LAW_DATABASE.get(
        contract_type,
        FALLBACK_LAW_DATABASE["general_contract"]
    )
    general_laws = (
        FALLBACK_LAW_DATABASE["general_contract"]
        if contract_type != "general_contract" else ""
    )

    if realtime_laws:
        print(f"[VidhiAI] Using CourtListener real-time data + Indian statutory framework")
        combined = (
            f"=== REAL-TIME COURT DATA (CourtListener) ===\n"
            f"{realtime_laws}\n\n"
            f"=== INDIAN STATUTORY FRAMEWORK ===\n"
            f"{fallback_laws}\n\n"
            f"{('=== GENERAL CONTRACT PRINCIPLES ===' + chr(10) + general_laws) if general_laws else ''}"
        )
        source = "courtlistener+database"
    else:
        print(f"[VidhiAI] Using Indian statutory framework only")
        combined = (
            f"=== INDIAN STATUTORY FRAMEWORK ===\n"
            f"{fallback_laws}\n\n"
            f"{('=== GENERAL CONTRACT PRINCIPLES ===' + chr(10) + general_laws) if general_laws else ''}"
        )
        source = "database"

    # Step 4: Cache result
    _save_cache(cache_key, combined)

    return {
        "contract_type": contract_type,
        "laws": combined,
        "source": source
    }


def clear_law_cache():
    """Clear all cached laws to force fresh CourtListener fetch."""
    cleared = 0
    errors  = 0
    if os.path.exists(LAW_CACHE_DIR):
        for filename in os.listdir(LAW_CACHE_DIR):
            filepath = os.path.join(LAW_CACHE_DIR, filename)
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    cleared += 1
            except Exception as e:
                print(f"[VidhiAI] Could not delete {filename}: {e}")
                errors += 1
    os.makedirs(LAW_CACHE_DIR, exist_ok=True)
    print(f"[VidhiAI] Law cache cleared: {cleared} file(s) removed, {errors} error(s)")