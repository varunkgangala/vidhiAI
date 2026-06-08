import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import json
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from database.models import (
    init_db, save_analysis, get_recent_analyses,
    get_all_analyses, get_analysis_by_id,
    delete_analysis, get_user_stats,
)
from auth.auth_routes import auth_bp
from analysis.contract_parser import parse_contract, is_allowed_file
from analysis.nlp_engine import run_nlp_analysis
from rag.law_fetcher import fetch_relevant_laws
from rag.prompt_builder import build_analysis_prompt
from rag.llm_engine import run_llm_analysis

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vidhiai-secret-key-change-in-prod-2024")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["UPLOAD_FOLDER"]      = os.path.join("data", "uploads")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(os.path.join("data", "law_cache"), exist_ok=True)

app.register_blueprint(auth_bp)
init_db()


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def index():
    return render_template("home.html")


@app.route("/dashboard")
@login_required
def dashboard():
    recent = get_recent_analyses(session["user_id"], limit=5)
    stats  = get_user_stats(session["user_id"])
    return render_template("dashboard.html", recent=recent, stats=stats)


@app.route("/analyze", methods=["GET", "POST"])
@login_required
def analyze():
    if request.method == "GET":
        return render_template("analyze.html")

    contract_text = ""
    document_name = "Pasted Text"

    uploaded_file = request.files.get("contract_file")
    pasted_text   = request.form.get("contract_text", "").strip()

    if uploaded_file and uploaded_file.filename:
        filename = uploaded_file.filename
        if not is_allowed_file(filename):
            flash("Unsupported file type. Please upload PDF, DOCX, or TXT.", "error")
            return render_template("analyze.html")
        try:
            contract_text = parse_contract(uploaded_file.stream, filename)
            document_name = filename
        except Exception as e:
            flash(str(e), "error")
            return render_template("analyze.html")
    elif pasted_text:
        contract_text = pasted_text
        document_name = "Pasted Contract - " + datetime.now().strftime("%Y-%m-%d %H:%M")
    else:
        flash("Please upload a file or paste contract text.", "warning")
        return render_template("analyze.html")

    if len(contract_text.strip()) < 50:
        flash("Contract text is too short to analyze (minimum 50 characters).", "warning")
        return render_template("analyze.html")

    #STEP 1: NLP Analysis 
    print("\n[VidhiAI] === STEP 1: NLP ANALYSIS ===")
    law_data   = fetch_relevant_laws(contract_text)
    nlp_result = run_nlp_analysis(contract_text, law_data["contract_type"])

    #  STEP 2: Build Prompt with NLP results 
    print("\n[VidhiAI] === STEP 2: BUILD PROMPT ===")
    prompt = build_analysis_prompt(
        contract_text,
        law_data["laws"],
        law_data["contract_type"],
        nlp_result
    )

    #STEP 3: LLM Analysis (explanation generation) 
    print("\n[VidhiAI] === STEP 3: LLM EXPLANATION ===")
    result = run_llm_analysis(
        prompt,
        nlp_result      = nlp_result,
        contract_type   = law_data["contract_type"]
    )

    # STEP 4: Enrich result with NLP data 
    result["nlp_data"] = {
        "entities":      nlp_result.get("entities", {}),
        "clauses":       {k: v["present"] for k, v in nlp_result.get("clauses", {}).items()},
        "obligations":   nlp_result.get("obligations", []),
        "score_breakdown": nlp_result.get("score_data", {}),
        "nlp_available": nlp_result.get("nlp_available", False),
        "word_count":    nlp_result.get("score_data", {}).get("word_count", 0),
        "law_source":    law_data.get("source", "database"),
    }

    #STEP 5: Save to Supabase
    print("\n[VidhiAI] === STEP 4: SAVE TO SUPABASE ===")
    analysis_json = json.dumps(result)
    record = save_analysis(
        user_id          = session["user_id"],
        document_name    = document_name,
        compliance_score = result.get("compliance_score", 0),
        risk_level       = result.get("risk_level", "Unknown"),
        analysis_text    = analysis_json,
    )
    print(f"[VidhiAI] Saved report ID: {record['analysis_id']}")
    return redirect(url_for("report_view", analysis_id=record["analysis_id"]))


@app.route("/history")
@login_required
def history():
    records = get_all_analyses(session["user_id"])
    return render_template("history.html", records=records)


@app.route("/report/<int:analysis_id>")
@login_required
def report_view(analysis_id):
    record = get_analysis_by_id(analysis_id, session["user_id"])
    if not record:
        flash("Report not found.", "error")
        return redirect(url_for("history"))
    try:
        analysis = json.loads(record["analysis_text"])
    except Exception:
        analysis = {}
    return render_template("report_view.html", record=record, analysis=analysis)


@app.route("/delete_report/<int:analysis_id>", methods=["POST"])
@login_required
def delete_report(analysis_id):
    delete_analysis(analysis_id, session["user_id"])
    flash("Report deleted.", "info")
    return redirect(url_for("history"))


@app.route("/clear_law_cache", methods=["POST"])
@login_required
def clear_law_cache():
    from rag.law_fetcher import clear_law_cache as _clear
    _clear()
    flash("Law cache cleared. Next analysis will fetch fresh laws.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
