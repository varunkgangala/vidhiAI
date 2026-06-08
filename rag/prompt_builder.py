"""
prompt_builder.py — Gemini-optimised prompts for VidhiAI

Gemini does not use Llama3 chat template tags.
Uses plain conversational prompt format which Gemini responds to best.
"""


def build_analysis_prompt(contract_text: str, laws: str,
                           contract_type: str, nlp_result: dict = None) -> str:
    """
    Build Gemini-optimised prompt with NLP results embedded.
    """
    nlp_context = ""
    if nlp_result:
        score_data      = nlp_result.get("score_data", {})
        entities        = nlp_result.get("entities", {})
        missing_clauses = nlp_result.get("missing_clauses", [])
        risk_phrases    = nlp_result.get("risk_phrases", [])
        obligations     = nlp_result.get("obligations", [])

        risks_text = "\n".join([
            f"- [{r['severity']}] {r['risk']} (Section: {r['section']})"
            for r in risk_phrases[:6]
        ]) or "- None detected"

        oblig_text = "\n".join([
            f"- {o['subject']}: {o['text'][:120]}"
            for o in obligations[:5]
        ]) or "- None extracted"

        parties_text = ", ".join(entities.get("parties", [])[:4]) or "Not identified"
        dates_text   = ", ".join(entities.get("dates",   [])[:3]) or "Not found"
        amounts_text = ", ".join(entities.get("amounts", [])[:3]) or "Not found"

        nlp_context = f"""
=== NLP PRE-ANALYSIS (already computed) ===
Contract Type    : {contract_type.replace('_', ' ').title()}
Compliance Score : {score_data.get('score', 0)} / 100
Risk Level       : {score_data.get('risk_level', 'Unknown')}
Grade            : {score_data.get('grade', 'N/A')}
Clauses Found    : {score_data.get('clauses_found', 0)} of {score_data.get('clauses_total', 11)}

Parties (NER)    : {parties_text}
Dates (NER)      : {dates_text}
Amounts (NER)    : {amounts_text}

Missing Clauses  :
{chr(10).join('- ' + c for c in missing_clauses) if missing_clauses else '- None'}

Risk Phrases     :
{risks_text}

Obligations      :
{oblig_text}
"""

    score   = nlp_result.get("score_data", {}).get("score", 60)   if nlp_result else 60
    risk    = nlp_result.get("score_data", {}).get("risk_level", "Medium") if nlp_result else "Medium"
    missing = nlp_result.get("missing_clauses", [])               if nlp_result else []

    prompt = f"""You are VidhiAI, an expert legal compliance assistant specializing in Indian contract law.

{nlp_context}

=== APPLICABLE LAWS ===
{laws[:2500]}

=== CONTRACT TEXT ===
{contract_text[:3000]}

=== TASK ===
Using the NLP analysis above and applicable laws, generate a detailed legal compliance report.

IMPORTANT RULES:
- Use compliance_score = {score} exactly (already computed by NLP)
- Use risk_level = "{risk}" exactly (already computed by NLP)  
- Write the explanation in professional legal language (3 paragraphs)
- Do NOT mention "NLP", "TF-IDF", "spaCy" or any technical terms in the explanation
- The explanation should read like a legal professional wrote it
- Reference specific Indian laws by name

Respond ONLY with this JSON (no extra text, no markdown):

{{
  "compliance_score": {score},
  "risk_level": "{risk}",
  "missing_clauses": {json_list(missing)},
  "detected_risks": [
    {{
      "risk": "specific risk description",
      "severity": "High or Medium or Low",
      "section": "clause/section name"
    }}
  ],
  "explanation": "Paragraph 1: Overall compliance assessment with score and risk level.\\n\\nParagraph 2: Key findings — missing clauses and their legal implications under Indian law.\\n\\nParagraph 3: Recommendations and next steps.",
  "referenced_laws": ["Law 1", "Law 2", "Law 3"],
  "recommendations": ["Specific recommendation 1", "Specific recommendation 2", "Specific recommendation 3"]
}}"""

    return prompt


def json_list(items: list) -> str:
    """Convert Python list to JSON array string."""
    import json
    return json.dumps(items)


def build_analysis_prompt_fallback(contract_text: str, laws: str,
                                    contract_type: str,
                                    nlp_result: dict = None) -> str:
    """Simpler prompt — same format, shorter context."""
    score   = nlp_result.get("score_data", {}).get("score", 60)        if nlp_result else 60
    risk    = nlp_result.get("score_data", {}).get("risk_level", "Medium") if nlp_result else "Medium"
    missing = nlp_result.get("missing_clauses", [])                     if nlp_result else []

    prompt = f"""You are a legal compliance expert. Analyze this contract and return JSON only.

Contract Type: {contract_type.replace('_', ' ').title()}
Pre-computed Score: {score}/100
Pre-computed Risk: {risk}
Missing Clauses: {', '.join(missing) if missing else 'None'}

Laws:
{laws[:1500]}

Contract:
{contract_text[:2500]}

Return this exact JSON structure:
{{
  "compliance_score": {score},
  "risk_level": "{risk}",
  "missing_clauses": {json_list(missing)},
  "detected_risks": [{{"risk": "description", "severity": "High/Medium/Low", "section": "section"}}],
  "explanation": "3 paragraph professional legal analysis",
  "referenced_laws": ["Indian Contract Act, 1872"],
  "recommendations": ["recommendation 1", "recommendation 2"]
}}

JSON only, no other text:"""
    return prompt


def build_summary_prompt(analysis_result: dict) -> str:
    return (
        f"Summarize this legal analysis in 2 sentences:\n"
        f"Score: {analysis_result.get('compliance_score')}%\n"
        f"Risk: {analysis_result.get('risk_level')}\n"
        f"Issues: {len(analysis_result.get('detected_risks', []))}"
    )
