import re
import os
import math
from collections import defaultdict
from typing import Optional

# ── spaCy loader ─────────────────────────────────────────────────────────────

_nlp = None

def _load_spacy():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_sm")
            print("[VidhiAI NLP] spaCy en_core_web_sm loaded")
        except OSError:
            print("[VidhiAI NLP] Downloading spaCy model...")
            from spacy.cli import download
            download("en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
        return _nlp
    except ImportError:
        print("[VidhiAI NLP] spaCy not installed")
        return None


CLAUSE_SEEDS = {
    "termination": [
        "terminate agreement notice period end contract",
        "either party may terminate written notice days",
        "termination shall take effect upon expiry",
        "agreement terminated immediately for cause misconduct",
    ],
    "payment": [
        "salary compensation remuneration payable monthly",
        "payment terms invoice due date amount",
        "fees payable within days of receipt invoice",
        "gross monthly salary INR rupees compensation",
    ],
    "confidentiality": [
        "confidential information shall not disclose",
        "proprietary information trade secret non disclosure",
        "keep confidential business data client lists",
        "confidentiality obligation survive termination years",
    ],
    "intellectual_property": [
        "intellectual property rights ownership work product",
        "copyright patent trademark ownership employer",
        "all inventions creations assigned belong to",
        "work product created during employment belongs",
    ],
    "dispute_resolution": [
        "disputes resolved arbitration conciliation act",
        "arbitration proceedings seat jurisdiction",
        "dispute difference claim arising agreement",
        "mediation arbitration before litigation court",
    ],
    "governing_law": [
        "governed construed accordance laws India",
        "governing law applicable jurisdiction courts",
        "laws of India shall apply govern agreement",
        "exclusive jurisdiction courts of city state",
    ],
    "force_majeure": [
        "force majeure act of god unforeseen circumstances",
        "beyond reasonable control natural disaster pandemic",
        "neither party liable failure performance circumstances",
        "government orders war pandemic natural disaster",
    ],
    "liability": [
        "limitation of liability maximum aggregate damages",
        "total liability shall not exceed fees paid",
        "indemnify hold harmless against claims losses",
        "limitation damages indirect consequential losses",
    ],
    "non_compete": [
        "not engage competitor similar business period",
        "non compete restriction months years post termination",
        "shall not join direct competitor industry",
        "restraint trade non solicitation employees clients",
    ],
    "amendment": [
        "amendment modification agreement writing signed",
        "no modification valid unless written agreed",
        "changes agreement require written consent both",
        "amendment must be in writing signed parties",
    ],
    "severability": [
        "if any provision invalid unenforceable remaining",
        "severability invalid provision shall not affect",
        "provisions continue full force effect severed",
        "court holds provision invalid rest remains",
    ],
    "entire_agreement": [
        "entire agreement supersedes prior negotiations",
        "whole agreement between parties subject matter",
        "supersedes all prior representations understandings",
        "constitutes entire understanding between parties",
    ],
}

# Required clauses with weights
REQUIRED_CLAUSES = {
    "termination":           {"weight": 15, "label": "Termination Clause"},
    "payment":               {"weight": 15, "label": "Payment Terms"},
    "dispute_resolution":    {"weight": 12, "label": "Dispute Resolution"},
    "governing_law":         {"weight": 10, "label": "Governing Law"},
    "liability":             {"weight": 10, "label": "Limitation of Liability"},
    "confidentiality":       {"weight": 8,  "label": "Confidentiality Clause"},
    "force_majeure":         {"weight": 8,  "label": "Force Majeure Clause"},
    "intellectual_property": {"weight": 8,  "label": "Intellectual Property"},
    "amendment":             {"weight": 7,  "label": "Amendment Clause"},
    "severability":          {"weight": 4,  "label": "Severability Clause"},
    "entire_agreement":      {"weight": 3,  "label": "Entire Agreement Clause"},
}

# Risk phrases (rule-based — honest labeling)
RISK_PHRASES = {
    "High": [
        r'\bunlimited\s+liabilit\w+\b',
        r'\birrevocable\b',
        r'\bperpetual\b',
        r'\bwaive\s+all\s+rights\b',
        r'\bno\s+termination\b',
        r'\bwithout\s+notice\b',
        r'\bsole\s+discretion\b',
        r'\bnon.negotiable\b',
        r'\bforfeiture\b',
        r'\babsolute\s+obligation\b',
    ],
    "Medium": [
        r'\bat\s+will\b',
        r'\bbest\s+efforts\b',
        r'\bsubject\s+to\s+change\b',
        r'\bmaterial\s+breach\b',
        r'\bliquidated\s+damages\b',
        r'\bimmediately\s+terminat\w+\b',
    ],
    "Low": [
        r'\bmutual\s+agreement\b',
        r'\bwritten\s+notice\b',
        r'\bthirty\s+days\b',
        r'\bsixty\s+days\b',
        r'\bseverabilit\w+\b',
    ],
}

OBLIGATION_KEYWORDS = [
    "shall", "must", "will", "agrees to", "is required to",
    "is obligated to", "undertakes to", "covenants to",
    "is responsible for",
]


# ── TF-IDF implementation (pure Python, no sklearn needed) ───────────────────

def _tokenize(text: str) -> list:
    """Simple tokenizer — lowercase, remove punctuation."""
    text = text.lower()
    text = re.sub(r'[^a-z\s]', ' ', text)
    return [w for w in text.split() if len(w) > 2]


def _compute_tfidf(documents: list) -> list:
    """
    Compute TF-IDF vectors for a list of documents.
    Returns list of dicts {term: tfidf_score}.
    """
    N = len(documents)
    tokenized = [_tokenize(doc) for doc in documents]

    # Document frequency
    df = defaultdict(int)
    for tokens in tokenized:
        for term in set(tokens):
            df[term] += 1

    # IDF
    idf = {term: math.log(N / (1 + freq)) for term, freq in df.items()}

    # TF-IDF per document
    vectors = []
    for tokens in tokenized:
        tf = defaultdict(float)
        for term in tokens:
            tf[term] += 1
        # Normalize TF
        total = len(tokens) if tokens else 1
        tfidf = {term: (count / total) * idf.get(term, 0)
                 for term, count in tf.items()}
        vectors.append(tfidf)

    return vectors


def _cosine_similarity(vec1: dict, vec2: dict) -> float:
    """Compute cosine similarity between two TF-IDF vectors."""
    common = set(vec1.keys()) & set(vec2.keys())
    if not common:
        return 0.0

    dot_product = sum(vec1[t] * vec2[t] for t in common)
    mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


def classify_clauses_nlp(sentences: list) -> dict:
    """
    REAL NLP clause classification using TF-IDF + cosine similarity.

    For each sentence in the contract:
    - Compute its TF-IDF vector
    - Compare against seed phrases for each clause type
    - Assign to clause type with highest similarity score

    This is semantic matching — finds clauses even when
    worded differently from the seed phrases.
    """
    results = {}

    for clause_name, seeds in CLAUSE_SEEDS.items():
        # Compute TF-IDF for seeds + all sentences combined
        all_docs    = seeds + sentences
        all_vectors = _compute_tfidf(all_docs)

        seed_vectors     = all_vectors[:len(seeds)]
        sentence_vectors = all_vectors[len(seeds):]

        # Find best matching sentence for this clause
        best_score    = 0.0
        best_sentence = ""

        for i, sent_vec in enumerate(sentence_vectors):
            # Compare against all seeds, take max similarity
            max_sim = max(
                _cosine_similarity(sent_vec, seed_vec)
                for seed_vec in seed_vectors
            )
            if max_sim > best_score:
                best_score    = max_sim
                best_sentence = sentences[i]

        # Threshold: 0.08 for presence (tuned for legal text)
        present    = best_score >= 0.08
        confidence = min(1.0, best_score / 0.2)

        results[clause_name] = {
            "present":    present,
            "score":      round(best_score, 4),
            "confidence": round(confidence, 2),
            "sentences":  [best_sentence[:200]] if present and best_sentence else [],
            "method":     "tfidf_cosine",
        }

    return results


# ── spaCy NLP functions ───────────────────────────────────────────────────────

def extract_entities_spacy(doc) -> dict:
    """
    Real NLP: spaCy Named Entity Recognition.
    Identifies persons, organizations, dates, money amounts.
    """
    entities = {
        "parties":   [],
        "dates":     [],
        "amounts":   [],
        "locations": [],
        "orgs":      [],
    }
    seen = set()

    for ent in doc.ents:
        text = ent.text.strip()
        if text in seen or len(text) < 2:
            continue
        seen.add(text)

        if ent.label_ == "PERSON":
            entities["parties"].append(text)
        elif ent.label_ == "ORG":
            entities["orgs"].append(text)
            entities["parties"].append(text)
        elif ent.label_ == "DATE":
            entities["dates"].append(text)
        elif ent.label_ in ("MONEY", "CARDINAL") and any(c.isdigit() for c in text):
            entities["amounts"].append(text)
        elif ent.label_ in ("GPE", "LOC"):
            entities["locations"].append(text)

    for key in entities:
        entities[key] = list(dict.fromkeys(entities[key]))[:8]

    return entities


def extract_obligations_spacy(doc) -> list:
    """
    Real NLP: spaCy dependency parsing.
    Finds sentences with legal obligations (SHALL/MUST + action).
    """
    obligations = []
    seen        = set()

    for sent in doc.sents:
        sent_text  = sent.text.strip()
        sent_lower = sent_text.lower()

        for keyword in OBLIGATION_KEYWORDS:
            if keyword in sent_lower and sent_text not in seen:
                seen.add(sent_text)

                # Extract subject via dependency parse
                subject = "Party"
                for token in sent:
                    if token.dep_ in ("nsubj", "nsubjpass"):
                        subject = token.text
                        break

                # Extract main verb
                verb = ""
                for token in sent:
                    if token.dep_ == "ROOT" and token.pos_ == "VERB":
                        verb = token.lemma_
                        break

                obligations.append({
                    "text":    sent_text[:250],
                    "keyword": keyword,
                    "subject": subject,
                    "verb":    verb,
                })
                break

    return obligations[:15]


def detect_risk_phrases(text: str) -> list:
    """
    Rule-based risk phrase detection (labeled honestly as rule-based).
    Scans for known dangerous legal phrases using regex.
    """
    risks      = []
    text_lower = text.lower()
    seen       = set()

    for severity, patterns in RISK_PHRASES.items():
        for pattern in patterns:
            matches = list(re.finditer(pattern, text_lower))
            for match in matches:
                phrase = match.group().strip()
                if phrase in seen:
                    continue
                seen.add(phrase)

                start   = max(0, match.start() - 80)
                end     = min(len(text), match.end() + 80)
                context = re.sub(r'\s+', ' ', text[start:end]).strip()

                section = _find_section(text, match.start())

                risks.append({
                    "risk":     f"Risky language detected: '{phrase}'",
                    "severity": severity,
                    "section":  section,
                    "context":  context[:200],
                    "phrase":   phrase,
                    "method":   "rule_based",
                })

    order = {"High": 0, "Medium": 1, "Low": 2}
    risks.sort(key=lambda x: order.get(x["severity"], 3))
    return risks[:10]


def _find_section(text: str, position: int) -> str:
    """Find nearest section heading before a given position."""
    before   = text[:position]
    headings = re.findall(
        r'(?:^|\n)\s*(\d+[\.\)]\s+[A-Z][A-Z\s]+|[A-Z][A-Z\s]{3,})\s*\n',
        before
    )
    return headings[-1].strip()[:50] if headings else "General"


def compute_nlp_score(clause_results: dict, entities: dict, text: str) -> dict:
    """
    Compute compliance score from NLP results.

    Breakdown:
      Clause completeness : 70% (TF-IDF clause detection)
      Entity completeness : 15% (spaCy NER)
      Document structure  : 15% (length, formatting)
    """
    total_weight  = sum(c["weight"] for c in REQUIRED_CLAUSES.values())
    earned_weight = 0

    for clause_name, info in REQUIRED_CLAUSES.items():
        result = clause_results.get(clause_name, {})
        if result.get("present", False):
            confidence    = result.get("confidence", 0.5)
            earned_weight += info["weight"] * min(1.0, 0.5 + confidence)

    clause_score = (earned_weight / total_weight) * 70

    # Entity score
    entity_score = 0
    if entities.get("parties"):  entity_score += 7
    if entities.get("dates"):    entity_score += 4
    if entities.get("amounts"):  entity_score += 4

    # Structure score
    word_count      = len(text.split())
    structure_score = min(15, (word_count // 200) * 3)

    total = round(min(100, clause_score + entity_score + structure_score))

    return {
        "score":           total,
        "grade":           "A" if total >= 85 else "B" if total >= 70 else "C" if total >= 55 else "D" if total >= 40 else "F",
        "risk_level":      "Low" if total >= 75 else "Medium" if total >= 50 else "High",
        "clause_score":    round(clause_score, 1),
        "entity_score":    round(entity_score, 1),
        "structure_score": round(structure_score, 1),
        "word_count":      word_count,
    }


def find_missing_clauses(clause_results: dict) -> list:
    return [
        info["label"]
        for clause_name, info in REQUIRED_CLAUSES.items()
        if not clause_results.get(clause_name, {}).get("present", False)
    ]


def get_nlp_summary(entities: dict, clause_results: dict,
                    obligations: list, contract_type: str,
                    score_data: dict) -> str:
    parties  = entities.get("parties", [])
    dates    = entities.get("dates",   [])
    amounts  = entities.get("amounts", [])
    present  = [k for k, v in clause_results.items() if v.get("present")]
    absent   = find_missing_clauses(clause_results)

    return (
        f"NLP analysis identified this as a {contract_type.replace('_',' ')} contract "
        f"between {', '.join(parties[:2]) if parties else 'unidentified parties'}, "
        f"dated {dates[0] if dates else 'no date found'}. "
        f"Primary consideration: {amounts[0] if amounts else 'not specified'}.\n\n"
        f"TF-IDF semantic analysis detected {len(present)} of "
        f"{len(REQUIRED_CLAUSES)} required clauses. "
        f"{'All essential clauses present.' if not absent else 'Missing: ' + ', '.join(absent[:3]) + '.'} "
        f"spaCy dependency parsing extracted {len(obligations)} binding obligations.\n\n"
        f"Compliance score: {score_data.get('score',0)}/100 "
        f"(Grade {score_data.get('grade','?')} — {score_data.get('risk_level','?')} Risk). "
        f"Score breakdown: Clause={score_data.get('clause_score',0)}, "
        f"Entity={score_data.get('entity_score',0)}, "
        f"Structure={score_data.get('structure_score',0)}."
    )


# ── Main NLP pipeline ─────────────────────────────────────────────────────────

def run_nlp_analysis(contract_text: str, contract_type: str) -> dict:
    """
    Full NLP pipeline:

    Step 1: Sentence segmentation
    Step 2: TF-IDF + cosine similarity clause classification (NLP)
    Step 3: spaCy NER — extract parties, dates, amounts (NLP)
    Step 4: spaCy dependency parsing — extract obligations (NLP)
    Step 5: Rule-based risk phrase detection (rule-based)
    Step 6: Compliance scoring (weighted calculation)
    """
    print("[VidhiAI NLP] Starting NLP pipeline...")

    # Step 1: Sentence segmentation
    sentences = [
        s.strip() for s in re.split(r'(?<=[.!?])\s+', contract_text)
        if len(s.strip()) > 20
    ]
    print(f"[VidhiAI NLP] Step 1: Segmented {len(sentences)} sentences")

    # Step 2: TF-IDF clause classification (real NLP)
    print("[VidhiAI NLP] Step 2: TF-IDF semantic clause classification...")
    clause_results = classify_clauses_nlp(sentences)
    present = [k for k, v in clause_results.items() if v["present"]]
    print(f"[VidhiAI NLP]   Method: TF-IDF + cosine similarity")
    print(f"[VidhiAI NLP]   Clauses found: {present}")

    # Step 3 & 4: spaCy NER + dependency parsing
    nlp = _load_spacy()

    if nlp:
        print("[VidhiAI NLP] Step 3: spaCy NER (Named Entity Recognition)...")
        doc      = nlp(contract_text[:100000])
        entities = extract_entities_spacy(doc)
        print(f"[VidhiAI NLP]   Parties : {entities['parties'][:3]}")
        print(f"[VidhiAI NLP]   Dates   : {entities['dates'][:3]}")
        print(f"[VidhiAI NLP]   Amounts : {entities['amounts'][:3]}")

        print("[VidhiAI NLP] Step 4: Dependency parsing for obligations...")
        obligations = extract_obligations_spacy(doc)
        print(f"[VidhiAI NLP]   Obligations extracted: {len(obligations)}")
        nlp_available = True
    else:
        print("[VidhiAI NLP] Steps 3-4: spaCy unavailable — skipping NER and parsing")
        entities      = {"parties": [], "dates": [], "amounts": [], "orgs": [], "locations": []}
        obligations   = []
        nlp_available = False

    # Step 5: Rule-based risk detection
    print("[VidhiAI NLP] Step 5: Rule-based risk phrase detection...")
    risk_phrases = detect_risk_phrases(contract_text)
    print(f"[VidhiAI NLP]   Risk phrases found: {len(risk_phrases)}")

    # Step 6: Scoring
    print("[VidhiAI NLP] Step 6: Computing compliance score...")
    score_data      = compute_nlp_score(clause_results, entities, contract_text)
    missing_clauses = find_missing_clauses(clause_results)
    print(f"[VidhiAI NLP]   Score     : {score_data['score']}/100")
    print(f"[VidhiAI NLP]   Grade     : {score_data['grade']}")
    print(f"[VidhiAI NLP]   Risk Level: {score_data['risk_level']}")
    print(f"[VidhiAI NLP]   Missing   : {missing_clauses}")

    nlp_summary = get_nlp_summary(
        entities, clause_results, obligations, contract_type, score_data
    )

    print("[VidhiAI NLP] Pipeline complete.")

    return {
        "entities":        entities,
        "clauses":         clause_results,
        "obligations":     obligations,
        "risk_phrases":    risk_phrases,
        "missing_clauses": missing_clauses,
        "score_data":      score_data,
        "nlp_summary":     nlp_summary,
        "nlp_available":   nlp_available,
    }
