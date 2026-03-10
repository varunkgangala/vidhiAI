import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env file automatically
from dotenv import load_dotenv
load_dotenv()

import json
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from database.models import (
    init_db,
    save_analysis,
    get_recent_analyses,
    get_all_analyses,
    get_analysis_by_id,
    delete_analysis,
    get_user_stats,
)
from auth.auth_routes import auth_bp
from analysis.contract_parser import parse_contract, is_allowed_file
from rag.law_fetcher import fetch_relevant_laws
from rag.prompt_builder import build_analysis_prompt
from rag.llm_engine import run_llm_analysis

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vidhiai-secret-key-change-in-prod-2024")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
app.config["UPLOAD_FOLDER"] = os.path.join("data", "uploads")

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
            flash(f"Could not read file: {e}", "error")
            return render_template("analyze.html")
    elif pasted_text:
        contract_text = pasted_text
        document_name = "Pasted Contract - " + datetime.now().strftime("%Y-%m-%d %H:%M")
    else:
        flash("Please upload a file or paste contract text.", "warning")
        return render_template("analyze.html")

    if len(contract_text.strip()) < 50:
        flash("Contract text is too short to analyze.", "warning")
        return render_template("analyze.html")

    # RAG Pipeline
    law_data = fetch_relevant_laws(contract_text)
    prompt   = build_analysis_prompt(contract_text, law_data["laws"], law_data["contract_type"])
    result   = run_llm_analysis(prompt)

    # Save to Supabase
    analysis_json = json.dumps(result)
    record = save_analysis(
        user_id          = session["user_id"],
        document_name    = document_name,
        compliance_score = result.get("compliance_score", 0),
        risk_level       = result.get("risk_level", "Unknown"),
        analysis_text    = analysis_json,
    )
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
