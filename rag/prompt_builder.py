def build_analysis_prompt(contract_text: str, laws: str, contract_type: str) -> str:
    prompt = f"""You are VidhiAI, an expert legal compliance assistant specializing in Indian and international contract law.

CONTRACT TYPE DETECTED: {contract_type.replace('_', ' ').title()}

=== APPLICABLE LAWS AND REGULATIONS ===
{laws}

=== CONTRACT TEXT FOR ANALYSIS ===
{contract_text[:6000]}

=== ANALYSIS TASK ===
Analyze the above contract against the applicable laws. Provide a thorough legal compliance assessment.

Respond ONLY in the following JSON format (no extra text):
{{
  "compliance_score": <integer 0-100>,
  "risk_level": "<Low|Medium|High>",
  "missing_clauses": [
    "<clause 1>",
    "<clause 2>"
  ],
  "detected_risks": [
    {{
      "risk": "<risk description>",
      "severity": "<Low|Medium|High>",
      "section": "<relevant section or 'General'>"
    }}
  ],
  "explanation": "<2-3 paragraph plain-English summary of findings>",
  "referenced_laws": [
    "<law 1>",
    "<law 2>"
  ],
  "recommendations": [
    "<recommendation 1>",
    "<recommendation 2>"
  ]
}}

Base the compliance_score on: completeness of essential clauses (40%), absence of illegal provisions (30%), clarity of terms (20%), and proper legal formalities (10%).
Risk level: High = score < 50, Medium = 50-74, Low = 75+.
"""
    return prompt


def build_summary_prompt(analysis_result: dict) -> str:
    return f"""Summarize this legal analysis in 2 sentences for a non-lawyer:
Compliance Score: {analysis_result.get('compliance_score')}%
Risk Level: {analysis_result.get('risk_level')}
Issues: {len(analysis_result.get('detected_risks', []))} risks found."""
