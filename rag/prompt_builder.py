
def build_analysis_prompt(contract_text: str, laws: str,
                           contract_type: str, nlp_result: dict = None) -> str:

    # Build NLP context section if available
    nlp_context = ""
    if nlp_result:
        score_data      = nlp_result.get("score_data", {})
        entities        = nlp_result.get("entities", {})
        missing_clauses = nlp_result.get("missing_clauses", [])
        risk_phrases    = nlp_result.get("risk_phrases", [])
        obligations     = nlp_result.get("obligations", [])
        nlp_summary     = nlp_result.get("nlp_summary", "")

        # Format detected risks
        risks_text = "\n".join([
            f"- [{r['severity']}] {r['risk']} (Section: {r['section']})"
            for r in risk_phrases[:6]
        ])

        # Format obligations
        oblig_text = "\n".join([
            f"- {o['subject']}: {o['text'][:120]}"
            for o in obligations[:5]
        ])

        nlp_context = f"""
=== PRE-COMPUTED NLP ANALYSIS RESULTS ===

CONTRACT TYPE     : {contract_type.replace('_', ' ').title()}
NLP COMPLIANCE SCORE: {score_data.get('score', 0)} / 100
RISK LEVEL        : {score_data.get('risk_level', 'Unknown')}
GRADE             : {score_data.get('grade', 'N/A')}

PARTIES IDENTIFIED (NER):
{', '.join(entities.get('parties', ['Not identified'])[:5])}

DATES FOUND (NER):
{', '.join(entities.get('dates', ['Not found'])[:4])}

AMOUNTS FOUND (NER):
{', '.join(entities.get('amounts', ['Not found'])[:4])}

MISSING CLAUSES (NLP Detection):
{chr(10).join('- ' + c for c in missing_clauses) if missing_clauses else '- None detected'}

RISK PHRASES DETECTED (NLP):
{risks_text if risks_text else '- No high-risk phrases found'}

KEY OBLIGATIONS EXTRACTED (Dependency Parsing):
{oblig_text if oblig_text else '- No obligations extracted'}

NLP SUMMARY:
{nlp_summary}
"""

    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are VidhiAI, a legal compliance assistant. NLP analysis has already been performed on the contract. Your job is to use the NLP results and applicable laws to generate a detailed compliance report in JSON format only. No extra text outside JSON.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{nlp_context}

=== APPLICABLE LAWS ===
{laws[:2000]}

=== CONTRACT TEXT (first 3000 chars) ===
{contract_text[:3000]}

=== YOUR TASK ===
Using the NLP analysis results and applicable laws above, generate a compliance report.
The compliance_score and risk_level have already been computed by NLP — use them directly.
Focus on generating a detailed explanation, referenced laws, and actionable recommendations.

Return ONLY this JSON:

{{
  "compliance_score": {nlp_result.get('score_data', {}).get('score', 60) if nlp_result else 60},
  "risk_level": "{nlp_result.get('score_data', {}).get('risk_level', 'Medium') if nlp_result else 'Medium'}",
  "missing_clauses": {str(missing_clauses if nlp_result else []).replace("'", '"')},
  "detected_risks": [
    {{
      "risk": "<description of risk>",
      "severity": "<High|Medium|Low>",
      "section": "<section name>"
    }}
  ],
  "explanation": "<3 paragraph detailed explanation using NLP findings and laws>",
  "referenced_laws": ["<law 1>", "<law 2>"],
  "recommendations": ["<recommendation 1>", "<recommendation 2>"]
}}

OUTPUT ONLY THE JSON. NO OTHER TEXT.
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
    return prompt


def build_analysis_prompt_fallback(contract_text: str, laws: str,
                                    contract_type: str,
                                    nlp_result: dict = None) -> str:
    """
    Simpler prompt format for models that don't support Llama3 chat template.
    Works with gpt-oss, llama2, mistral, phi3 etc.
    """
    score      = nlp_result.get("score_data", {}).get("score", 60)      if nlp_result else 60
    risk       = nlp_result.get("score_data", {}).get("risk_level", "Medium") if nlp_result else "Medium"
    missing    = nlp_result.get("missing_clauses", [])                   if nlp_result else []
    risk_phrases = nlp_result.get("risk_phrases", [])                    if nlp_result else []

    risks_text = "\n".join([
        f"- [{r['severity']}] {r['risk']}"
        for r in risk_phrases[:5]
    ]) if risk_phrases else "None detected"

    prompt = f"""### SYSTEM
You are VidhiAI legal compliance assistant. Output ONLY valid JSON. No markdown. No extra text.

### NLP PRE-ANALYSIS
Contract Type  : {contract_type.replace('_', ' ').title()}
Compliance Score: {score}/100
Risk Level     : {risk}
Missing Clauses: {', '.join(missing) if missing else 'None'}
Risk Phrases   : {risks_text}

### APPLICABLE LAWS
{laws[:1500]}

### CONTRACT TEXT
{contract_text[:2500]}

### INSTRUCTION
Generate a compliance report JSON using the NLP analysis above.
Use the pre-computed score ({score}) and risk level ({risk}) directly.

{{
  "compliance_score": {score},
  "risk_level": "{risk}",
  "missing_clauses": {str(missing).replace("'", '"')},
  "detected_risks": [
    {{"risk": "description", "severity": "High|Medium|Low", "section": "section name"}}
  ],
  "explanation": "detailed 3 paragraph explanation",
  "referenced_laws": ["law name"],
  "recommendations": ["recommendation"]
}}

### RESPONSE (JSON only):
"""
    return prompt


def build_summary_prompt(analysis_result: dict) -> str:
    return (
        f"Summarize this legal analysis in 2 sentences for a non-lawyer:\n"
        f"Compliance Score : {analysis_result.get('compliance_score')}%\n"
        f"Risk Level       : {analysis_result.get('risk_level')}\n"
        f"Issues found     : {len(analysis_result.get('detected_risks', []))}"
    )
