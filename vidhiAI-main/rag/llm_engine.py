import json
import re
import os
import random

from dotenv import load_dotenv
load_dotenv(override=True)

OLLAMA_URL   = os.environ.get("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:latest")

print(f"[VidhiAI] LLM Engine ready | Model: {OLLAMA_MODEL} | URL: {OLLAMA_URL}")


# ── Ollama connectivity ───────────────────────────────────────────────────────

def _check_ollama_running() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5)
        return True
    except Exception as e:
        print(f"[VidhiAI] Ollama ping failed: {e}")
        return False


def _get_available_models() -> list:
    try:
        import urllib.request
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def _call_llama(prompt: str, timeout: int = 300) -> str | None:
    try:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model":  OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p":       0.9,
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

        print(f"[VidhiAI] Sending NLP-enriched prompt to {OLLAMA_MODEL}...")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data          = json.loads(resp.read())
            response_text = data.get("response", "").strip()
            print(f"[VidhiAI] LLM responded with {len(response_text)} characters")
            return response_text

    except Exception as e:
        print(f"[VidhiAI] LLM call failed: {e}")
        return None


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict | None:
    if not raw:
        return None
    # Strategy 1: Direct parse
    try:
        return json.loads(raw.strip())
    except Exception:
        pass
    # Strategy 2: Strip markdown
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # Strategy 3: Find { } block
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
        fixed  = re.sub(r',\s*([}\]])', r'\1', cleaned)
        match2 = re.search(r'\{[\s\S]*\}', fixed)
        if match2:
            return json.loads(match2.group())
    except Exception:
        pass
    print("[VidhiAI] Could not extract JSON from LLM response")
    return None


def _validate_result(result: dict) -> bool:
    required = {"compliance_score": (int, float), "risk_level": str, "explanation": str}
    for key, types in required.items():
        if key not in result or not isinstance(result[key], types):
            return False
    rl = str(result["risk_level"]).strip().capitalize()
    result["risk_level"]      = rl if rl in ("High","Medium","Low") else \
        ("High" if int(result.get("compliance_score",50))<50 else
         "Medium" if int(result.get("compliance_score",50))<75 else "Low")
    result["compliance_score"] = max(0, min(100, int(result["compliance_score"])))
    for field in ["missing_clauses","detected_risks","referenced_laws","recommendations"]:
        if field not in result or not isinstance(result[field], list):
            result[field] = []
    return True


# ── NLP-only result builder ───────────────────────────────────────────────────

def _build_result_from_nlp(nlp_result: dict, contract_type: str) -> dict:
    """
    Build a complete analysis result purely from NLP — no LLM needed.
    Used as fallback when Ollama is unavailable.
    """
    score_data   = nlp_result.get("score_data", {})
    entities     = nlp_result.get("entities", {})
    risk_phrases = nlp_result.get("risk_phrases", [])
    missing      = nlp_result.get("missing_clauses", [])
    nlp_summary  = nlp_result.get("nlp_summary", "")

    score      = score_data.get("score", 50)
    risk_level = score_data.get("risk_level", "Medium")

    # Build detected risks from NLP risk phrases
    detected_risks = [
        {
            "risk":     r["risk"],
            "severity": r["severity"],
            "section":  r["section"],
        }
        for r in risk_phrases[:6]
    ]
    if not detected_risks:
        detected_risks.append({
            "risk":     "No high-risk phrases detected by NLP analysis",
            "severity": "Low",
            "section":  "General",
        })

    # Referenced laws based on contract type
    laws_map = {
        "employment":        ["Indian Contract Act, 1872", "Industrial Disputes Act, 1947",
                              "Minimum Wages Act, 1948", "Payment of Wages Act, 1936",
                              "POSH Act, 2013", "Employees Provident Funds Act, 1952"],
        "nda":               ["Indian Contract Act, 1872 (Section 27)",
                              "Information Technology Act, 2000",
                              "Digital Personal Data Protection Act, 2023"],
        "service_agreement": ["Indian Contract Act, 1872", "Information Technology Act, 2000",
                              "Consumer Protection Act, 2019", "Indian Copyright Act, 1957"],
        "lease":             ["Transfer of Property Act, 1882", "Model Tenancy Act, 2021",
                              "Registration Act, 1908", "Indian Stamp Act, 1899"],
        "general_contract":  ["Indian Contract Act, 1872", "Specific Relief Act, 1963",
                              "Indian Stamp Act, 1899"],
    }
    referenced_laws = laws_map.get(contract_type, laws_map["general_contract"])

    # Recommendations
    recommendations = []
    if missing:
        recommendations.append(f"Add a {missing[0]} to meet legal requirements")
    recommendations += [
        "Ensure all monetary amounts comply with statutory minimums",
        "Have the contract reviewed by a qualified legal professional",
        "Ensure proper stamping and registration as required by law",
        "Include a severability clause to protect contract validity",
    ]

    # Build explanation from NLP summary
    explanation = (
        f"{nlp_summary}\n\n"
        f"Based on NLP analysis, the contract scored {score}/100 with a "
        f"{risk_level.lower()} risk classification. "
        f"{'All major clauses are present.' if not missing else f'Key missing clauses: {chr(44).join(missing[:3])}.'}\n\n"
        f"It is strongly recommended that a qualified legal professional review "
        f"this contract before execution."
    )

    return {
        "compliance_score": score,
        "risk_level":       risk_level,
        "missing_clauses":  missing,
        "detected_risks":   detected_risks,
        "explanation":      explanation,
        "referenced_laws":  referenced_laws,
        "recommendations":  recommendations[:5],
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def run_llm_analysis(prompt: str, nlp_result: dict = None,
                     contract_type: str = "general_contract") -> dict:
    """
    Main analysis pipeline:
      1. NLP analysis already done (passed in as nlp_result)
      2. Try Ollama LLM to generate detailed explanation
      3. Merge LLM output with NLP results
      4. Fall back to NLP-only result if LLM unavailable
    """
    from rag.prompt_builder import build_analysis_prompt_fallback

    print(f"\n{'='*60}")
    print(f"[VidhiAI] Starting LLM analysis")
    print(f"[VidhiAI] NLP available: {nlp_result is not None}")
    print(f"[VidhiAI] Model: {OLLAMA_MODEL}")
    print(f"{'='*60}")

    # If NLP ran, show its results
    if nlp_result:
        sd = nlp_result.get("score_data", {})
        print(f"[VidhiAI] NLP Score : {sd.get('score')} | Risk: {sd.get('risk_level')}")
        print(f"[VidhiAI] NLP Missing: {nlp_result.get('missing_clauses', [])}")

    # Step 1: Check Ollama
    if not _check_ollama_running():
        print("[VidhiAI] Ollama not running - using NLP-only result")
        if nlp_result:
            return _build_result_from_nlp(nlp_result, contract_type)
        return _build_fallback_simulation(prompt)

    models = _get_available_models()
    print(f"[VidhiAI] Ollama models: {models}")

    if models and OLLAMA_MODEL not in models:
        print(f"[VidhiAI] Model '{OLLAMA_MODEL}' not found - run: ollama pull {OLLAMA_MODEL}")
        if nlp_result:
            return _build_result_from_nlp(nlp_result, contract_type)
        return _build_fallback_simulation(prompt)

    # Step 2: Attempt 1 — primary prompt
    print("[VidhiAI] Attempt 1: primary prompt...")
    raw1 = _call_llama(prompt, timeout=600)
    if raw1:
        result1 = _extract_json(raw1)
        if result1 and _validate_result(result1):
            # Merge NLP score into LLM result (NLP score is more accurate)
            if nlp_result:
                sd = nlp_result.get("score_data", {})
                result1["compliance_score"] = sd.get("score", result1["compliance_score"])
                result1["risk_level"]       = sd.get("risk_level", result1["risk_level"])
                # Add NLP-detected risks if LLM missed them
                nlp_risks = nlp_result.get("risk_phrases", [])
                if nlp_risks and not result1.get("detected_risks"):
                    result1["detected_risks"] = [
                        {"risk": r["risk"], "severity": r["severity"], "section": r["section"]}
                        for r in nlp_risks[:5]
                    ]
            print(f"[VidhiAI] SUCCESS (attempt 1) | Score: {result1['compliance_score']} | Risk: {result1['risk_level']}")
            return result1

    # Step 3: Attempt 2 — fallback prompt
    print("[VidhiAI] Attempt 2: fallback prompt...")
    contract_match = re.search(r'CONTRACT TEXT.*?\n([\s\S]*?)(?=TASK:|SCORING|$)', prompt)
    laws_match     = re.search(r'APPLICABLE LAWS.*?\n([\s\S]*?)(?=CONTRACT TEXT|$)', prompt)
    contract_text  = contract_match.group(1).strip() if contract_match else prompt[:2000]
    laws_text      = laws_match.group(1).strip()     if laws_match     else ""

    fallback_prompt = build_analysis_prompt_fallback(
        contract_text, laws_text, contract_type, nlp_result
    )
    raw2 = _call_llama(fallback_prompt, timeout=600)
    if raw2:
        result2 = _extract_json(raw2)
        if result2 and _validate_result(result2):
            if nlp_result:
                sd = nlp_result.get("score_data", {})
                result2["compliance_score"] = sd.get("score", result2["compliance_score"])
                result2["risk_level"]       = sd.get("risk_level", result2["risk_level"])
            print(f"[VidhiAI] SUCCESS (attempt 2) | Score: {result2['compliance_score']} | Risk: {result2['risk_level']}")
            return result2

    # Step 4: NLP-only fallback
    print("[VidhiAI] LLM failed - using NLP-only result")
    if nlp_result:
        return _build_result_from_nlp(nlp_result, contract_type)
    return _build_fallback_simulation(prompt)


def _build_fallback_simulation(prompt: str) -> dict:
    """Last resort fallback using simple keyword detection."""
    prompt_lower = prompt.lower()
    signals = sum([
        any(w in prompt_lower for w in ["terminat", "notice period"]),
        any(w in prompt_lower for w in ["arbitration", "dispute"]),
        any(w in prompt_lower for w in ["confidential", "non-disclosure"]),
        any(w in prompt_lower for w in ["payment", "salary", "compensation"]),
        any(w in prompt_lower for w in ["intellectual property", "copyright"]),
        any(w in prompt_lower for w in ["liability", "indemnif"]),
        any(w in prompt_lower for w in ["force majeure", "act of god"]),
        any(w in prompt_lower for w in ["governing law", "governed by"]),
    ])
    score      = max(20, min(95, 35 + (signals * 8) + random.randint(-5, 5)))
    risk_level = "Low" if score >= 75 else ("Medium" if score >= 50 else "High")
    return {
        "compliance_score": score,
        "risk_level":       risk_level,
        "missing_clauses":  ["Termination clause", "Dispute resolution clause"],
        "detected_risks":   [{"risk": "Analysis ran in fallback mode", "severity": "Low", "section": "General"}],
        "explanation":      f"Contract scored {score}/100 ({risk_level} risk). Run full NLP analysis for detailed results.",
        "referenced_laws":  ["Indian Contract Act, 1872"],
        "recommendations":  ["Install spaCy for full NLP analysis: pip install spacy"],
    }
