"""
llm_engine.py — Gemini API integration for VidhiAI

Pipeline:
  1. Run NLP analysis (already done, passed in)
  2. Call Gemini API for explanation generation
  3. Merge Gemini output with NLP results
  4. Fall back to NLP-only result if Gemini fails
"""

import json
import re
import os
import random
import urllib.request
import urllib.error

from dotenv import load_dotenv
load_dotenv(override=True)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

print(f"[VidhiAI] LLM Engine ready | Provider: Gemini | Model: {GEMINI_MODEL}")


# ── Gemini API call ───────────────────────────────────────────────────────────

def _call_gemini(prompt: str, timeout: int = 60) -> str | None:
    """
    Call Google Gemini API.
    Returns raw text response or None on failure.
    """
    if not GEMINI_API_KEY:
        print("[VidhiAI] GEMINI_API_KEY not set in .env")
        return None

    try:
        url     = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
        payload = json.dumps({
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature":     0.1,
                "maxOutputTokens": 2048,
                "topP":            0.9,
            }
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        print(f"[VidhiAI] Calling Gemini ({GEMINI_MODEL})...")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())

            # Extract text from Gemini response
            candidates = data.get("candidates", [])
            if not candidates:
                print("[VidhiAI] Gemini returned no candidates")
                return None

            content = candidates[0].get("content", {})
            parts   = content.get("parts", [])
            if not parts:
                print("[VidhiAI] Gemini returned empty parts")
                return None

            text = parts[0].get("text", "").strip()
            print(f"[VidhiAI] Gemini responded with {len(text)} characters")
            return text

    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code == 400:
            print(f"[VidhiAI] Gemini bad request: {body[:200]}")
        elif e.code == 403:
            print("[VidhiAI] Gemini API key invalid or quota exceeded")
        elif e.code == 429:
            print("[VidhiAI] Gemini rate limit hit — try again in a moment")
        else:
            print(f"[VidhiAI] Gemini HTTP {e.code}: {body[:200]}")
        return None

    except urllib.error.URLError as e:
        print(f"[VidhiAI] Gemini connection error: {e.reason}")
        return None

    except Exception as e:
        print(f"[VidhiAI] Gemini call failed: {e}")
        return None


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict | None:
    """Extract JSON from Gemini response — handles markdown wrapping."""
    if not raw:
        return None
    # Strategy 1: Direct parse
    try:
        return json.loads(raw.strip())
    except Exception:
        pass
    # Strategy 2: Strip markdown fences
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
        fixed  = re.sub(r',\s*([}\]])', r'\1', cleaned)
        match2 = re.search(r'\{[\s\S]*\}', fixed)
        if match2:
            return json.loads(match2.group())
    except Exception:
        pass
    print("[VidhiAI] Could not extract JSON from Gemini response")
    print(f"[VidhiAI] Response preview: {raw[:300]}")
    return None


def _validate_result(result: dict) -> bool:
    """Validate and normalise the result dict."""
    required = {"compliance_score": (int, float), "risk_level": str, "explanation": str}
    for key, types in required.items():
        if key not in result or not isinstance(result[key], types):
            print(f"[VidhiAI] Missing or invalid key: {key}")
            return False
    rl = str(result["risk_level"]).strip().capitalize()
    result["risk_level"]       = rl if rl in ("High", "Medium", "Low") else \
        ("High" if int(result.get("compliance_score", 50)) < 50 else
         "Medium" if int(result.get("compliance_score", 50)) < 75 else "Low")
    result["compliance_score"] = max(0, min(100, int(result["compliance_score"])))
    for field in ["missing_clauses", "detected_risks", "referenced_laws", "recommendations"]:
        if field not in result or not isinstance(result[field], list):
            result[field] = []
    return True


# ── NLP-only fallback ─────────────────────────────────────────────────────────

def _build_result_from_nlp(nlp_result: dict, contract_type: str) -> dict:
    """Build complete result from NLP alone — used when Gemini is unavailable."""
    score_data   = nlp_result.get("score_data", {})
    risk_phrases = nlp_result.get("risk_phrases", [])
    missing      = nlp_result.get("missing_clauses", [])
    nlp_summary  = nlp_result.get("nlp_summary", "")
    score        = score_data.get("score", 50)
    risk_level   = score_data.get("risk_level", "Medium")

    detected_risks = [
        {"risk": r["risk"], "severity": r["severity"], "section": r["section"]}
        for r in risk_phrases[:6]
    ]
    if not detected_risks:
        detected_risks.append({
            "risk":     "No high-risk phrases detected",
            "severity": "Low",
            "section":  "General",
        })

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

    recommendations = []
    if missing:
        recommendations.append(f"Add a {missing[0].lower()} to meet legal requirements")
    recommendations += [
        "Ensure all monetary amounts comply with statutory minimums",
        "Have the contract reviewed by a qualified legal professional",
        "Ensure proper stamping and registration as required by law",
        "Include a severability clause to protect contract validity",
    ]

    return {
        "compliance_score": score,
        "risk_level":       risk_level,
        "missing_clauses":  missing,
        "detected_risks":   detected_risks,
        "explanation":      nlp_summary,
        "referenced_laws":  referenced_laws,
        "recommendations":  recommendations[:5],
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def run_llm_analysis(prompt: str, nlp_result: dict = None,
                     contract_type: str = "general_contract") -> dict:
    """
    Main analysis pipeline:
      1. NLP analysis already done (passed in as nlp_result)
      2. Call Gemini API for rich explanation generation
      3. Override Gemini score with NLP score (more accurate)
      4. Fall back to NLP-only result if Gemini unavailable
    """
    print(f"\n{'='*60}")
    print(f"[VidhiAI] Starting Gemini LLM analysis")
    print(f"[VidhiAI] API Key set: {bool(GEMINI_API_KEY)}")
    print(f"{'='*60}")

    if nlp_result:
        sd = nlp_result.get("score_data", {})
        print(f"[VidhiAI] NLP Score: {sd.get('score')} | Risk: {sd.get('risk_level')}")
        print(f"[VidhiAI] Missing  : {nlp_result.get('missing_clauses', [])}")

    # No API key — use NLP result directly
    if not GEMINI_API_KEY:
        print("[VidhiAI] No Gemini API key — using NLP-only result")
        if nlp_result:
            return _build_result_from_nlp(nlp_result, contract_type)
        return _build_simple_fallback(prompt)

    # Call Gemini
    raw = _call_gemini(prompt, timeout=60)

    if raw:
        result = _extract_json(raw)
        if result and _validate_result(result):
            # Override LLM score with more accurate NLP score
            if nlp_result:
                sd = nlp_result.get("score_data", {})
                result["compliance_score"] = sd.get("score", result["compliance_score"])
                result["risk_level"]       = sd.get("risk_level", result["risk_level"])
                # Use NLP missing clauses if LLM missed them
                if not result.get("missing_clauses") and nlp_result.get("missing_clauses"):
                    result["missing_clauses"] = nlp_result["missing_clauses"]
                # Add NLP risks if LLM found none
                if not result.get("detected_risks") and nlp_result.get("risk_phrases"):
                    result["detected_risks"] = [
                        {"risk": r["risk"], "severity": r["severity"], "section": r["section"]}
                        for r in nlp_result["risk_phrases"][:5]
                    ]
            print(f"[VidhiAI] Gemini SUCCESS | Score: {result['compliance_score']} | Risk: {result['risk_level']}")
            return result
        else:
            print("[VidhiAI] Gemini JSON parsing failed — using NLP fallback")
    else:
        print("[VidhiAI] Gemini returned no response — using NLP fallback")

    # Fallback to NLP-only
    if nlp_result:
        return _build_result_from_nlp(nlp_result, contract_type)
    return _build_simple_fallback(prompt)


def _build_simple_fallback(prompt: str) -> dict:
    """Keyword-based fallback when both Gemini and NLP are unavailable."""
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
        "missing_clauses":  [],
        "detected_risks":   [{"risk": "Basic analysis only", "severity": "Low", "section": "General"}],
        "explanation":      f"Contract scored {score}/100 ({risk_level} risk). Add GEMINI_API_KEY to .env for full AI analysis.",
        "referenced_laws":  ["Indian Contract Act, 1872"],
        "recommendations":  ["Add GEMINI_API_KEY to .env for full AI-powered analysis"],
    }
