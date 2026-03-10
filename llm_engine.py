import json
import re
import os
import random

# ── Load .env FIRST ───────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(override=True)

# ── Ollama / Model settings ───────────────────────────────────────────────────
OLLAMA_URL   = os.environ.get("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:latest")

# Print on startup so you can confirm settings are loaded
print(f"[VidhiAI] LLM Engine ready.")
print(f"[VidhiAI] Ollama URL   : {OLLAMA_URL}")
print(f"[VidhiAI] Ollama Model : {OLLAMA_MODEL}")


# ── Ollama connectivity ───────────────────────────────────────────────────────

def _check_ollama_running() -> bool:
    """Ping Ollama to check if running."""
    try:
        import urllib.request
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5)
        return True
    except Exception as e:
        print(f"[VidhiAI] Ollama ping failed: {e}")
        return False


def _get_available_models() -> list:
    """Return list of models pulled in Ollama."""
    try:
        import urllib.request
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


# ── Model API call ────────────────────────────────────────────────────────────

def _call_llama(prompt: str, timeout: int = 300) -> str | None:
    """
    Send prompt to Ollama.
    Timeout is 300s (5 min) by default — needed for large 13GB models.
    """
    try:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 2048,
                "stop": ["<|eot_id|>", "### HUMAN", "### USER", "</s>"]
            }
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        print(f"[VidhiAI] Sending to {OLLAMA_MODEL} - please wait (may take 1-3 min for 13GB model)...")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            response_text = data.get("response", "").strip()
            print(f"[VidhiAI] Model responded with {len(response_text)} characters")
            return response_text

    except urllib.error.URLError as e:
        print(f"[VidhiAI] Connection error: {e}")
        return None
    except Exception as e:
        print(f"[VidhiAI] Model call error: {e}")
        return None


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict | None:
    """Extract JSON from model response — handles markdown, extra text, trailing commas."""
    if not raw:
        return None

    # Strategy 1: Direct parse
    try:
        return json.loads(raw.strip())
    except Exception:
        pass

    # Strategy 2: Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Strategy 3: Find largest { } block
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, dict):
                return result
        except Exception:
            pass

    # Strategy 4: Fix trailing commas
    try:
        fixed = re.sub(r',\s*([}\]])', r'\1', cleaned)
        match2 = re.search(r'\{[\s\S]*\}', fixed)
        if match2:
            return json.loads(match2.group())
    except Exception:
        pass

    print("[VidhiAI] Could not extract JSON from response.")
    print(f"[VidhiAI] Response preview: {raw[:400]}")
    return None


def _validate_result(result: dict) -> bool:
    """Validate and normalise the result dict."""
    required = {
        "compliance_score": (int, float),
        "risk_level": str,
        "explanation": str,
    }
    for key, types in required.items():
        if key not in result:
            print(f"[VidhiAI] Missing key: {key}")
            return False
        if not isinstance(result[key], types):
            print(f"[VidhiAI] Wrong type for {key}: {type(result[key])}")
            return False

    # Normalise risk level
    rl = str(result["risk_level"]).strip().capitalize()
    if rl not in ("High", "Medium", "Low"):
        score = int(result.get("compliance_score", 50))
        result["risk_level"] = "High" if score < 50 else ("Medium" if score < 75 else "Low")
    else:
        result["risk_level"] = rl

    # Clamp score
    result["compliance_score"] = max(0, min(100, int(result["compliance_score"])))

    # Ensure list fields
    for field in ["missing_clauses", "detected_risks", "referenced_laws", "recommendations"]:
        if field not in result or not isinstance(result[field], list):
            result[field] = []

    return True


# ── Simulation fallback ───────────────────────────────────────────────────────

def _simulate_analysis(prompt: str) -> dict:
    """Rule-based fallback engine — used when Ollama is unavailable."""
    print("[VidhiAI] Running simulation engine (Ollama not used)...")
    prompt_lower = prompt.lower()

    has_termination   = any(w in prompt_lower for w in ["terminat", "notice period", "30 days", "60 days"])
    has_dispute       = any(w in prompt_lower for w in ["arbitration", "dispute", "jurisdiction", "court"])
    has_confidential  = any(w in prompt_lower for w in ["confidential", "non-disclosure", "proprietary"])
    has_payment       = any(w in prompt_lower for w in ["payment", "salary", "compensation", "remuneration"])
    has_ip            = any(w in prompt_lower for w in ["intellectual property", "copyright", "patent", "ownership"])
    has_liability     = any(w in prompt_lower for w in ["liability", "indemnif", "limitation"])
    has_force_majeure = any(w in prompt_lower for w in ["force majeure", "act of god", "unforeseen"])
    has_governing_law = any(w in prompt_lower for w in ["governing law", "governed by", "applicable law"])

    signals = sum([has_termination, has_dispute, has_confidential, has_payment,
                   has_ip, has_liability, has_force_majeure, has_governing_law])

    compliance_score = max(20, min(95, 35 + (signals * 8) + random.randint(-5, 5)))
    risk_level = "Low" if compliance_score >= 75 else ("Medium" if compliance_score >= 50 else "High")

    missing_clauses = []
    if not has_termination:   missing_clauses.append("Termination clause with adequate notice period")
    if not has_dispute:       missing_clauses.append("Dispute resolution / arbitration clause")
    if not has_force_majeure: missing_clauses.append("Force majeure / act of God clause")
    if not has_governing_law: missing_clauses.append("Governing law and jurisdiction clause")
    if not has_liability:     missing_clauses.append("Limitation of liability clause")
    if not has_ip:            missing_clauses.append("Intellectual property ownership clause")
    if not missing_clauses:   missing_clauses.append("Severability clause")

    detected_risks = []
    if not has_payment:
        detected_risks.append({"risk": "Payment terms are ambiguous or missing", "severity": "High", "section": "Payment Terms"})
    if not has_termination:
        detected_risks.append({"risk": "No clear termination procedure defined", "severity": "High", "section": "Termination"})
    if not has_dispute:
        detected_risks.append({"risk": "No dispute resolution mechanism included", "severity": "Medium", "section": "Dispute Resolution"})
    if not has_governing_law:
        detected_risks.append({"risk": "Governing law not specified", "severity": "Medium", "section": "General"})
    if not has_liability:
        detected_risks.append({"risk": "Unlimited liability - no cap on damages", "severity": "High" if compliance_score < 55 else "Medium", "section": "Liability"})
    if not detected_risks:
        detected_risks.append({"risk": "Contract appears comprehensive; minor gaps noted", "severity": "Low", "section": "General"})

    if "employment" in prompt_lower or "employee" in prompt_lower:
        contract_type = "Employment"
        referenced_laws = ["Indian Contract Act, 1872", "Industrial Disputes Act, 1947",
                           "Minimum Wages Act, 1948", "Payment of Wages Act, 1936",
                           "POSH Act, 2013", "Employees Provident Funds Act, 1952"]
    elif "nda" in prompt_lower or "non-disclosure" in prompt_lower:
        contract_type = "NDA"
        referenced_laws = ["Indian Contract Act, 1872 (Sections 27, 73-74)",
                           "Information Technology Act, 2000", "Personal Data Protection Bill, 2023"]
    elif "service" in prompt_lower:
        contract_type = "Service Agreement"
        referenced_laws = ["Indian Contract Act, 1872", "Information Technology Act, 2000",
                           "Consumer Protection Act, 2019", "Indian Copyright Act, 1957"]
    else:
        contract_type = "General"
        referenced_laws = ["Indian Contract Act, 1872", "Specific Relief Act, 1963",
                           "Indian Stamp Act, 1899", "Registration Act, 1908"]

    score_desc = "strong" if compliance_score >= 75 else ("moderate" if compliance_score >= 50 else "weak")
    explanation = (
        f"This {contract_type} contract demonstrates {score_desc} legal compliance "
        f"with a score of {compliance_score}%. "
        f"{'The contract covers most essential elements required under applicable Indian law.' if compliance_score >= 75 else 'Several critical provisions are missing or inadequately addressed.'} "
        f"A total of {len(detected_risks)} risk(s) were identified.\n\n"
        f"{'Key gaps: ' + ', '.join(missing_clauses[:3]) + '.' if missing_clauses else 'Contract structure is sound.'} "
        f"Compliance with {referenced_laws[0]} should be verified.\n\n"
        f"A qualified legal professional should review this contract before execution."
    )

    return {
        "compliance_score": compliance_score,
        "risk_level": risk_level,
        "missing_clauses": missing_clauses[:6],
        "detected_risks": detected_risks[:6],
        "explanation": explanation,
        "referenced_laws": referenced_laws,
        "recommendations": [
            f"Add a comprehensive {missing_clauses[0].lower()}" if missing_clauses else "Review all clauses",
            "Ensure compensation complies with statutory minimums",
            "Include a severability clause",
            "Specify clear timelines for all obligations",
            "Have the contract reviewed by a legal professional",
        ]
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def run_llm_analysis(prompt: str) -> dict:
    """
    Main analysis pipeline:
      1. Check Ollama is running
      2. Check model is available
      3. Attempt 1 - primary Llama3 chat prompt
      4. Attempt 2 - simpler fallback prompt
      5. Simulation fallback
    """
    from rag.prompt_builder import build_analysis_prompt_fallback

    print(f"\n{'='*60}")
    print(f"[VidhiAI] Starting contract analysis")
    print(f"[VidhiAI] Model : {OLLAMA_MODEL}")
    print(f"[VidhiAI] URL   : {OLLAMA_URL}")
    print(f"{'='*60}")

    # Step 1: Check Ollama is reachable
    if not _check_ollama_running():
        print("[VidhiAI] STATUS : Ollama NOT running at", OLLAMA_URL)
        print("[VidhiAI] ACTION : Open browser and check http://localhost:11434")
        print("[VidhiAI]          If blank - run 'ollama serve' in a new terminal")
        print("[VidhiAI] FALLBACK: Using simulation engine")
        return _simulate_analysis(prompt)

    # Step 2: Check model is pulled
    models = _get_available_models()
    print(f"[VidhiAI] STATUS : Ollama is running")
    print(f"[VidhiAI] Models : {models if models else 'None found'}")

    if models and OLLAMA_MODEL not in models:
        print(f"[VidhiAI] WARNING: '{OLLAMA_MODEL}' not found in Ollama")
        print(f"[VidhiAI] ACTION : Run this command -> ollama pull {OLLAMA_MODEL}")
        print(f"[VidhiAI] FALLBACK: Using simulation engine")
        return _simulate_analysis(prompt)

    # Step 3: Attempt 1 with primary prompt
    print(f"[VidhiAI] Attempt 1: Using primary prompt format...")
    raw1 = _call_llama(prompt, timeout=300)
    if raw1:
        result1 = _extract_json(raw1)
        if result1 and _validate_result(result1):
            print(f"[VidhiAI] SUCCESS via Ollama (attempt 1)")
            print(f"[VidhiAI] Score: {result1['compliance_score']} | Risk: {result1['risk_level']}")
            return result1
        print("[VidhiAI] Attempt 1: JSON parsing failed, trying attempt 2...")

    # Step 4: Attempt 2 with simpler prompt
    print(f"[VidhiAI] Attempt 2: Using simpler prompt format...")
    contract_match = re.search(r'CONTRACT TEXT:\n([\s\S]*?)(?=TASK:|SCORING|$)', prompt)
    laws_match     = re.search(r'APPLICABLE LAWS:\n([\s\S]*?)(?=CONTRACT TEXT:|$)', prompt)
    type_match     = re.search(r'CONTRACT TYPE[:\s]+(.+)', prompt)

    contract_text = contract_match.group(1).strip() if contract_match else prompt[:2000]
    laws_text     = laws_match.group(1).strip()     if laws_match     else ""
    contract_type = type_match.group(1).strip()     if type_match     else "General"

    fallback_prompt = build_analysis_prompt_fallback(contract_text, laws_text, contract_type)
    raw2 = _call_llama(fallback_prompt, timeout=300)
    if raw2:
        result2 = _extract_json(raw2)
        if result2 and _validate_result(result2):
            print(f"[VidhiAI] SUCCESS via Ollama (attempt 2)")
            print(f"[VidhiAI] Score: {result2['compliance_score']} | Risk: {result2['risk_level']}")
            return result2
        print("[VidhiAI] Attempt 2: JSON parsing also failed")

    # Step 5: Simulation fallback
    print("[VidhiAI] Both Ollama attempts failed - switching to simulation engine")
    return _simulate_analysis(prompt)