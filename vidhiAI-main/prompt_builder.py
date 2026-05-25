def build_analysis_prompt(contract_text: str, laws: str, contract_type: str) -> str:
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are VidhiAI, a strict legal compliance analysis engine. You only output valid JSON. You never explain yourself outside the JSON. You never add markdown, code blocks, or extra text. You output raw JSON only.
<|eot_id|><|start_header_id|>user<|end_header_id|>

CONTRACT TYPE: {contract_type.replace('_', ' ').title()}

APPLICABLE LAWS:
{laws[:3000]}

CONTRACT TEXT:
{contract_text[:4000]}

TASK:
Analyze the contract against the laws above. Return ONLY a JSON object with exactly these keys:

{{
  "compliance_score": 72,
  "risk_level": "Medium",
  "missing_clauses": [
    "Force majeure clause",
    "Dispute resolution clause"
  ],
  "detected_risks": [
    {{
      "risk": "No limitation of liability clause found",
      "severity": "High",
      "section": "Liability"
    }}
  ],
  "explanation": "Two to three paragraph plain English summary of findings.",
  "referenced_laws": [
    "Indian Contract Act, 1872",
    "Specific Relief Act, 1963"
  ],
  "recommendations": [
    "Add a force majeure clause",
    "Specify governing law and jurisdiction"
  ]
}}

SCORING RULES:
- compliance_score: integer 0-100
- risk_level: "High" if score below 50, "Medium" if 50-74, "Low" if 75 or above
- missing_clauses: list clauses required by law but absent
- detected_risks: list actual risks with severity High/Medium/Low and section name
- explanation: plain English 2-3 paragraphs
- referenced_laws: only laws relevant to this contract
- recommendations: concrete actionable steps

OUTPUT ONLY THE JSON OBJECT. NO OTHER TEXT.
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
    return prompt


def build_analysis_prompt_fallback(contract_text: str, laws: str, contract_type: str) -> str:
    """
    Simpler prompt format for models that do not support Llama3 chat template.
    Works with gpt-oss, llama2, mistral, phi3, etc.
    """
    prompt = f"""### SYSTEM
You are VidhiAI, a legal compliance analysis engine. Output ONLY valid JSON. No extra text. No markdown. No explanation outside JSON.

### CONTRACT TYPE
{contract_type.replace('_', ' ').title()}

### APPLICABLE LAWS
{laws[:2000]}

### CONTRACT TEXT
{contract_text[:3000]}

### INSTRUCTION
Analyze the contract above. Return ONLY this exact JSON structure with real values filled in:

{{
  "compliance_score": 75,
  "risk_level": "Low",
  "missing_clauses": ["example missing clause"],
  "detected_risks": [
    {{
      "risk": "example risk description",
      "severity": "Medium",
      "section": "General"
    }}
  ],
  "explanation": "Plain English summary of the contract analysis in 2-3 paragraphs.",
  "referenced_laws": ["Indian Contract Act, 1872"],
  "recommendations": ["example recommendation"]
}}

RULES:
- compliance_score must be a number between 0 and 100
- risk_level must be exactly "High", "Medium", or "Low"
- If score is below 50 use High, 50-74 use Medium, 75+ use Low
- List every clause required by law that is missing from the contract
- List every risk you find in the contract

### RESPONSE (JSON only, no other text):
"""
    return prompt


def build_summary_prompt(analysis_result: dict) -> str:
    return (
        f"Summarize this legal analysis in 2 sentences for a non-lawyer:\n"
        f"Compliance Score: {analysis_result.get('compliance_score')}%\n"
        f"Risk Level: {analysis_result.get('risk_level')}\n"
        f"Issues found: {len(analysis_result.get('detected_risks', []))}"
    )