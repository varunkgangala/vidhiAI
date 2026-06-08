import sys
import os
import json
from datetime import datetime

# Allow importing local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# Import database models
from database.models import (
    init_db, save_analysis, get_recent_analyses,
    get_all_analyses, get_analysis_by_id,
    delete_analysis, get_user_stats,
    get_user_by_email, create_user, get_user_by_email_or_username
)
from auth.auth_utils import hash_password, verify_password, validate_email, validate_password
from analysis.contract_parser import parse_contract, is_allowed_file
from analysis.nlp_engine import run_nlp_analysis
from rag.law_fetcher import fetch_relevant_laws
from rag.prompt_builder import build_analysis_prompt
from rag.llm_engine import run_llm_analysis

# Page Config
st.set_page_config(
    page_title="VidhiAI - Legal Compliance Assistant",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling injection
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Source+Sans+3:wght@300;400;500;600&display=swap');
    
    /* Global Background and Fonts */
    .stApp {
        background-color: #f5f0e8 !important;
        font-family: 'Source Sans 3', sans-serif !important;
        color: #1a1a2e !important;
    }
    
    /* Typography */
    h1, h2, h3, .playfair {
        font-family: 'Playfair Display', serif !important;
        color: #0d1b2a !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0d1b2a !important;
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] button {
        background-color: #c9a84c !important;
        color: #0d1b2a !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    /* Cards */
    .card {
        background: #ffffff;
        border-radius: 16px;
        box-shadow: 0 4px 24px rgba(13,27,42,0.12);
        border: 1px solid rgba(212,201,176,0.4);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    .card-header-custom {
        background: #0d1b2a;
        color: #ffffff;
        padding: 0.75rem 1.25rem;
        border-radius: 16px 16px 0 0;
        margin: -1.5rem -1.5rem 1.5rem -1.5rem;
        font-family: 'Playfair Display', serif;
        font-size: 1.15rem;
        font-weight: 600;
        border-bottom: 2px solid #c9a84c;
    }
    
    /* Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.3rem 0.75rem;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    .badge-high { background: #fde8e8; color: #c0392b; border: 1px solid #f5c6c6; }
    .badge-medium { background: #fef3d7; color: #d68910; border: 1px solid #fce8a0; }
    .badge-low { background: #d4f4e3; color: #1e8449; border: 1px solid #a8e6c5; }
    
    /* Statistics Cards */
    .stat-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 24px rgba(13,27,42,0.12);
        border: 1px solid rgba(212,201,176,0.4);
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .stat-label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #6b7280;
        margin-bottom: 0.25rem;
    }
    
    .stat-value {
        font-family: 'Playfair Display', serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #0d1b2a;
    }
    
    /* Explanation block */
    .explanation-box {
        background: linear-gradient(135deg, rgba(13,27,42,0.03), rgba(201,168,76,0.06));
        border: 1px solid #d4c9b0;
        border-left: 4px solid #c9a84c;
        border-radius: 0 8px 8px 0;
        padding: 1.25rem 1.5rem;
        font-size: 0.93rem;
        line-height: 1.75;
        color: #1a1a2e;
        white-space: pre-line;
    }
    
    /* Referenced Laws */
    .law-ref {
        background: rgba(13,27,42,0.07);
        border: 1px solid rgba(13,27,42,0.12);
        color: #0d1b2a;
        padding: 0.3rem 0.75rem;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 500;
        display: inline-block;
        margin: 0.25rem;
    }
    
    /* Hero section */
    .hero {
        background-color: #0d1b2a;
        padding: 4rem 2rem;
        text-align: center;
        border-radius: 16px;
        color: #ffffff;
        margin-bottom: 2rem;
        position: relative;
    }
    
    .hero h1 {
        color: #ffffff !important;
        font-size: 2.8rem !important;
        margin-bottom: 1rem !important;
    }
    
    .hero p {
        color: rgba(255,255,255,0.8) !important;
        font-size: 1.1rem !important;
        max-width: 700px;
        margin: 0 auto 1.5rem auto !important;
    }
    
    .hero-eyebrow {
        display: inline-block;
        background: rgba(201,168,76,0.15);
        border: 1px solid rgba(201,168,76,0.4);
        color: #c9a84c;
        padding: 0.35rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 1.5rem;
    }
    
    /* Buttons Override */
    div.stButton > button {
        background-color: #0d1b2a !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 600 !important;
        border: 1px solid transparent !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background-color: #243b55 !important;
        border-color: #c9a84c !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Helper to render circular score ring via SVG
def render_score_ring(score, risk_level):
    if risk_level == "Low" or score >= 75:
        color = "#1e8449"  # green
    elif risk_level == "Medium" or score >= 50:
        color = "#d68910"  # amber
    else:
        color = "#c0392b"  # red
        
    radius = 50
    circumference = 2 * 3.14159 * radius
    stroke_dashoffset = circumference - (score / 100) * circumference
    
    html = f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 10px;">
        <div style="position: relative; width: 120px; height: 120px;">
            <svg width="120" height="120" style="transform: rotate(-90deg);">
                <circle cx="60" cy="60" r="{radius}" fill="none" stroke="#e8e0d0" stroke-width="10" />
                <circle cx="60" cy="60" r="{radius}" fill="none" stroke="{color}" stroke-width="10" 
                        stroke-dasharray="{circumference}" stroke-dashoffset="{stroke_dashoffset}" 
                        stroke-linecap="round" style="transition: stroke-dashoffset 1s ease;" />
            </svg>
            <div style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                <span style="font-family: 'Playfair Display', serif; font-size: 1.8rem; font-weight: 700; color: #0d1b2a; line-height: 1;">{score}</span>
                <span style="font-size: 0.7rem; color: #6b7280; font-weight: 600;">SCORE</span>
            </div>
        </div>
    </div>
    """
    return html

# Initialize Session State Variables
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"
if "view_report_id" not in st.session_state:
    st.session_state["view_report_id"] = None

# Initialize Database Connection
try:
    init_db()
except Exception as e:
    st.error(f"[VidhiAI] Supabase Database Initialization Failed: {e}")

# Inject styles
inject_custom_css()

# Navigation Router logic helper
def navigate_to(page_name):
    st.session_state["current_page"] = page_name
    st.rerun()

# ── NAVIGATION SIDEBAR ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <div style="font-family: 'Playfair Display', serif; font-size: 1.8rem; font-weight: 700; color: #c9a84c;">🏛️ VidhiAI</div>
        <div style="font-size: 0.7rem; color: rgba(255,255,255,0.7); text-transform: uppercase; letter-spacing: 1.5px;">Legal Compliance Assistant</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state["user_id"] is not None:
        st.markdown(f"""
        <div style="background-color: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; margin-bottom: 1.5rem; text-align: center;">
            <div style="font-size: 0.8rem; color: #c9a84c;">Logged In As</div>
            <div style="font-weight: 600; color: #ffffff; font-size: 1rem;">{st.session_state['username']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # User Menu Options
        nav_selection = st.radio(
            "Go To",
            ["📊 Dashboard", "🔍 New Analysis", "📜 History"],
            index=["Dashboard", "New Analysis", "History"].index(
                st.session_state["current_page"].replace("📊 ", "").replace("🔍 ", "").replace("📜 ", "")
                if st.session_state["current_page"] in ["Dashboard", "New Analysis", "History"] else "Dashboard"
            )
        )
        
        # Sync page state
        clean_nav = nav_selection.split(" ", 1)[1]
        if st.session_state["current_page"] not in ["Report", clean_nav]:
            st.session_state["current_page"] = clean_nav
            st.rerun()
            
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["user_id"] = None
            st.session_state["username"] = None
            st.session_state["current_page"] = "Home"
            st.rerun()
            
    else:
        st.markdown("""
        <div style="background-color: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; margin-bottom: 1.5rem; text-align: center; font-size: 0.85rem;">
            Please log in or sign up to analyze agreements.
        </div>
        """, unsafe_allow_html=True)
        
        nav_selection = st.radio(
            "Menu",
            ["🏛️ Welcome", "🔑 Login", "📝 Sign Up"],
            index=["Home", "Login", "Signup"].index(
                st.session_state["current_page"] if st.session_state["current_page"] in ["Home", "Login", "Signup"] else "Home"
            )
        )
        
        clean_nav = "Home" if "Welcome" in nav_selection else "Login" if "Login" in nav_selection else "Signup"
        if st.session_state["current_page"] != clean_nav:
            st.session_state["current_page"] = clean_nav
            st.rerun()


# ── PAGE RENDERING ────────────────────────────────────────────────────────────

# 1. HOME / WELCOME PAGE
if st.session_state["current_page"] == "Home":
    st.markdown("""
    <div class="hero">
        <div class="hero-eyebrow">Artificial Intelligence & Legal Authority</div>
        <h1>Analyze Contracts with <span>Absolute Clarity</span></h1>
        <p>VidhiAI uses state-of-the-art hybrid NLP and Gemini intelligence to audit your legal documents, evaluate Indian law compliance, and point out potential liabilities.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="card">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚖️</div>
            <h3>Indian Statutory RAG</h3>
            <p>Cross-references agreements directly with the Indian Contract Act, Transfer of Property Act, Industrial Disputes Act, and other relevant codes.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="card">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔍</div>
            <h3>Hybrid NLP Scrutiny</h3>
            <p>Uses spaCy named-entity recognition and custom TF-IDF cosine similarity to spot missing standard legal clauses and find hidden obligations.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="card">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🛡️</div>
            <h3>Instant Risk Auditing</h3>
            <p>Generates professional-grade compliance summaries and highlights high-risk terms with actionable mitigation advice.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><h3 style='text-align: center;'>Get Started</h3>", unsafe_allow_html=True)
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🔑 Log In to Dashboard", use_container_width=True):
            navigate_to("Login")
    with c_btn2:
        if st.button("📝 Create a New Account", use_container_width=True):
            navigate_to("Signup")


# 2. LOGIN PAGE
elif st.session_state["current_page"] == "Login":
    st.markdown("## 🔑 Account Login")
    st.write("Enter your credentials to access your dashboard.")
    
    with st.form("login_form"):
        email = st.text_input("Email Address").strip().lower()
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if not email or not password:
                st.error("Please fill in all fields.")
            else:
                try:
                    user = get_user_by_email(email)
                    if user and verify_password(password, user["password"]):
                        st.session_state["user_id"] = user["user_id"]
                        st.session_state["username"] = user["username"]
                        st.toast(f"Welcome back, {user['username']}!")
                        navigate_to("Dashboard")
                    else:
                        st.error("Invalid email or password.")
                except Exception as e:
                    st.error("Database connection failed. Please ensure your Supabase configuration is valid.")
                    print(f"[VidhiAI] Login error: {e}")
                    
    st.markdown("Don't have an account? [Sign Up here](#) or select **Sign Up** in the sidebar.")


# 3. SIGNUP PAGE
elif st.session_state["current_page"] == "Signup":
    st.markdown("## 📝 Account Registration")
    st.write("Create a secure account to audit contracts.")
    
    with st.form("signup_form"):
        username = st.text_input("Username").strip()
        email = st.text_input("Email Address").strip().lower()
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Register")
        
        if submit:
            if not username or not email or not password or not confirm_password:
                st.error("Please fill in all fields.")
            elif len(username) < 3:
                st.error("Username must be at least 3 characters.")
            elif not validate_email(email):
                st.error("Invalid email address format.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                valid_pass, pass_msg = validate_password(password)
                if not valid_pass:
                    st.error(pass_msg)
                else:
                    try:
                        existing = get_user_by_email_or_username(email, username)
                        if existing:
                            st.error("Username or email already registered.")
                        else:
                            hashed = hash_password(password)
                            user = create_user(username, email, hashed)
                            st.session_state["user_id"] = user["user_id"]
                            st.session_state["username"] = user["username"]
                            st.success("Registration successful!")
                            navigate_to("Dashboard")
                    except Exception as e:
                        st.error(f"Registration failed: {e}")


# 4. DASHBOARD PAGE
elif st.session_state["current_page"] == "Dashboard":
    if st.session_state["user_id"] is None:
        st.warning("Please log in to access this page.")
        navigate_to("Login")
        
    st.markdown("## 📊 Dashboard")
    st.write(f"Welcome back, **{st.session_state['username']}**! Here is your legal analysis overview.")
    
    # Load Stats from DB
    stats = {"total": 0, "avg_score": None, "high_risk": 0}
    try:
        stats = get_user_stats(st.session_state["user_id"])
    except Exception as e:
        st.error(f"Error loading user stats: {e}")
        
    # Render Stats Row
    s_col1, s_col2, s_col3 = st.columns(3)
    with s_col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Total Audited Contracts</div>
            <div class="stat-value">{stats['total']}</div>
        </div>
        """, unsafe_allow_html=True)
    with s_col2:
        avg = f"{stats['avg_score']:.1f}%" if stats['avg_score'] is not None else "N/A"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Avg. Compliance Score</div>
            <div class="stat-value">{avg}</div>
        </div>
        """, unsafe_allow_html=True)
    with s_col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">High Risk Contracts</div>
            <div class="stat-value">{stats['high_risk']}</div>
        </div>
        """, unsafe_allow_html=True)
        
    # Actions
    st.markdown("### Quick Actions")
    act_col1, act_col2 = st.columns(2)
    with act_col1:
        if st.button("🔍 Run New Analysis", use_container_width=True):
            navigate_to("New Analysis")
    with act_col2:
        if st.button("🧹 Clear Law Cache", use_container_width=True):
            try:
                from rag.law_fetcher import clear_law_cache as _clear
                _clear()
                st.success("Law cache cleared! Next analysis will fetch fresh data.")
            except Exception as e:
                st.error(f"Error clearing cache: {e}")
                
    # Recent Reports
    st.markdown("### Recent Analysis Reports")
    recent_records = []
    try:
        recent_records = get_recent_analyses(st.session_state["user_id"], limit=5)
    except Exception as e:
        st.error(f"Error loading reports: {e}")
        
    if not recent_records:
        st.info("You haven't run any contract analyses yet. Click 'Run New Analysis' above to get started!")
    else:
        # Table Header
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([4, 1.5, 1.5, 2, 2])
        h_col1.markdown("**Document Name**")
        h_col2.markdown("**Score**")
        h_col3.markdown("**Risk Level**")
        h_col4.markdown("**Date/Time**")
        h_col5.markdown("**Actions**")
        st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
        
        # Render Rows
        for rec in recent_records:
            r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([4, 1.5, 1.5, 2, 2])
            r_col1.write(rec["document_name"])
            r_col2.write(f"**{rec['compliance_score']}%**")
            
            badge_class = "badge-high" if rec["risk_level"] == "High" else "badge-medium" if rec["risk_level"] == "Medium" else "badge-low"
            r_col3.markdown(f'<span class="badge {badge_class}">{rec["risk_level"]}</span>', unsafe_allow_html=True)
            r_col4.write(rec["timestamp"])
            
            with r_col5:
                act1, act2 = st.columns(2)
                if act1.button("👁️", key=f"view_dash_{rec['analysis_id']}", help="View Report"):
                    st.session_state["view_report_id"] = rec["analysis_id"]
                    navigate_to("Report")
                if act2.button("🗑️", key=f"del_dash_{rec['analysis_id']}", help="Delete Report"):
                    try:
                        delete_analysis(rec["analysis_id"], st.session_state["user_id"])
                        st.toast("Report deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {e}")


# 5. NEW ANALYSIS PAGE
elif st.session_state["current_page"] == "New Analysis":
    if st.session_state["user_id"] is None:
        st.warning("Please log in to access this page.")
        navigate_to("Login")
        
    st.markdown("## 🔍 New Legal Analysis")
    st.write("Upload a legal contract file or paste the plain text to audit it against statutory framework and best practices.")
    
    # Input selection
    input_method = st.radio("Select Input Method", ["Upload Document File", "Paste Plain Text"])
    
    contract_text = ""
    document_name = ""
    
    if input_method == "Upload Document File":
        uploaded_file = st.file_uploader("Upload contract file (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
        if uploaded_file:
            filename = uploaded_file.name
            if not is_allowed_file(filename):
                st.error("Unsupported file type. Please upload PDF, DOCX, or TXT.")
            else:
                try:
                    # parse contract using stream
                    contract_text = parse_contract(uploaded_file, filename)
                    document_name = filename
                    st.success(f"Successfully read {filename} ({len(contract_text)} characters)")
                except Exception as e:
                    st.error(f"Error parsing file: {e}")
                    
    else:
        pasted_text = st.text_area("Paste Contract Text Here", height=250)
        doc_title = st.text_input("Document Name / Reference Title (Optional)", placeholder="e.g. Employment Agreement - Tech Solutions")
        if pasted_text:
            contract_text = pasted_text.strip()
            document_name = doc_title.strip() if doc_title.strip() else f"Pasted Contract - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
    if st.button("🚀 Analyze Agreement", use_container_width=True):
        if not contract_text or len(contract_text) < 50:
            st.error("Contract text is too short to analyze (minimum 50 characters).")
        else:
            # Run Analysis
            with st.spinner("Initiating analysis pipeline..."):
                # STEP 1: Fetch Laws
                st.write("🔄 Step 1: Fetching relevant legal framework...")
                law_data = fetch_relevant_laws(contract_text)
                
                # STEP 2: NLP engine pre-analysis
                st.write("🔄 Step 2: Extracting entities and identifying clauses...")
                nlp_result = run_nlp_analysis(contract_text, law_data["contract_type"])
                
                # STEP 3: Prompt Construction
                st.write("🔄 Step 3: Structuring AI validation rules...")
                prompt = build_analysis_prompt(
                    contract_text,
                    law_data["laws"],
                    law_data["contract_type"],
                    nlp_result
                )
                
                # STEP 4: LLM analysis
                st.write("🔄 Step 4: Interrogating Gemini model for compliance explanation...")
                result = run_llm_analysis(
                    prompt,
                    nlp_result=nlp_result,
                    contract_type=law_data["contract_type"]
                )
                
                # Enrich results
                result["nlp_data"] = {
                    "entities": nlp_result.get("entities", {}),
                    "clauses": {k: v["present"] for k, v in nlp_result.get("clauses", {}).items()},
                    "obligations": nlp_result.get("obligations", []),
                    "score_breakdown": nlp_result.get("score_data", {}),
                    "nlp_available": nlp_result.get("nlp_available", False),
                    "word_count": nlp_result.get("score_data", {}).get("word_count", 0),
                    "law_source": law_data.get("source", "database"),
                }
                
                # Save to Supabase
                st.write("💾 Step 5: Archiving report on Supabase...")
                try:
                    analysis_json = json.dumps(result)
                    record = save_analysis(
                        user_id=st.session_state["user_id"],
                        document_name=document_name,
                        compliance_score=result.get("compliance_score", 0),
                        risk_level=result.get("risk_level", "Unknown"),
                        analysis_text=analysis_json
                    )
                    st.success("Analysis complete!")
                    st.session_state["view_report_id"] = record["analysis_id"]
                    navigate_to("Report")
                except Exception as e:
                    st.error(f"Error archiving report to Supabase: {e}")


# 6. HISTORY PAGE
elif st.session_state["current_page"] == "History":
    if st.session_state["user_id"] is None:
        st.warning("Please log in to access this page.")
        navigate_to("Login")
        
    st.markdown("## 📜 Analysis History")
    st.write("Access all past legal audits performed on your account.")
    
    records = []
    try:
        records = get_all_analyses(st.session_state["user_id"])
    except Exception as e:
        st.error(f"Error loading history: {e}")
        
    if not records:
        st.info("You don't have any saved analysis records. Go to 'New Analysis' to start.")
    else:
        # Table headers
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([4, 1.5, 1.5, 2, 2])
        h_col1.markdown("**Document Name**")
        h_col2.markdown("**Compliance Score**")
        h_col3.markdown("**Risk Level**")
        h_col4.markdown("**Date/Time**")
        h_col5.markdown("**Actions**")
        st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
        
        # Render rows
        for rec in records:
            r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([4, 1.5, 1.5, 2, 2])
            r_col1.write(rec["document_name"])
            r_col2.write(f"**{rec['compliance_score']}%**")
            
            badge_class = "badge-high" if rec["risk_level"] == "High" else "badge-medium" if rec["risk_level"] == "Medium" else "badge-low"
            r_col3.markdown(f'<span class="badge {badge_class}">{rec["risk_level"]}</span>', unsafe_allow_html=True)
            r_col4.write(rec["timestamp"])
            
            with r_col5:
                act1, act2 = st.columns(2)
                if act1.button("👁️", key=f"view_hist_{rec['analysis_id']}", help="View Report"):
                    st.session_state["view_report_id"] = rec["analysis_id"]
                    navigate_to("Report")
                if act2.button("🗑️", key=f"del_hist_{rec['analysis_id']}", help="Delete Report"):
                    try:
                        delete_analysis(rec["analysis_id"], st.session_state["user_id"])
                        st.toast("Report deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {e}")


# 7. REPORT VIEW
elif st.session_state["current_page"] == "Report":
    if st.session_state["user_id"] is None:
        st.warning("Please log in to access reports.")
        navigate_to("Login")
        
    if st.session_state["view_report_id"] is None:
        st.error("No report selected.")
        if st.button("Back to Dashboard"):
            navigate_to("Dashboard")
    else:
        # Load report
        record = None
        try:
            record = get_analysis_by_id(st.session_state["view_report_id"], st.session_state["user_id"])
        except Exception as e:
            st.error(f"Failed to fetch report from database: {e}")
            
        if not record:
            st.error("Report not found or permission denied.")
            if st.button("Back to Dashboard"):
                navigate_to("Dashboard")
        else:
            try:
                analysis = json.loads(record["analysis_text"])
            except Exception:
                analysis = {}
                
            # Back Nav
            if st.button("← Back to History"):
                navigate_to("History")
                
            # Header card
            st.markdown(f"""
            <div class="card">
                <div class="card-header-custom">Legal Compliance Report: {record['document_name']}</div>
                <div style="font-size: 0.9rem; color: #6b7280; margin-top: 0.5rem;">Analyzed on: {record['timestamp']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 2 Columns: Score and basic stats on left, Explanation on right
            c_left, c_right = st.columns([1, 2])
            
            with c_left:
                st.markdown("### Compliance Rating")
                score = record.get("compliance_score", 0)
                risk_level = record.get("risk_level", "Unknown")
                
                # Render SVG ring
                st.markdown(render_score_ring(score, risk_level), unsafe_allow_html=True)
                
                grade = analysis.get("grade", "N/A")
                badge_class = "badge-high" if risk_level == "High" else "badge-medium" if risk_level == "Medium" else "badge-low"
                
                st.markdown(f"""
                <div style="text-align: center; margin-top: 10px;">
                    <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 5px;">Risk Level: <span class="badge {badge_class}">{risk_level}</span></div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: #0d1b2a;">Letter Grade: {grade}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with c_right:
                st.markdown("### Professional Legal Assessment")
                explanation = analysis.get("explanation", "No assessment available.")
                st.markdown(f'<div class="explanation-box">{explanation}</div>', unsafe_allow_html=True)
                
            st.markdown("---")
            
            # Risks and Missing Clauses row
            col_risks, col_clauses = st.columns(2)
            
            with col_risks:
                st.markdown("### ⚠️ Detected Legal Risks")
                detected_risks = analysis.get("detected_risks", [])
                if not detected_risks:
                    st.success("No significant legal risks identified in the analyzed text.")
                else:
                    for r in detected_risks:
                        sev = r.get("severity", "Low").capitalize()
                        dot_color = "#c0392b" if sev == "High" else "#d68910" if sev == "Medium" else "#1e8449"
                        st.markdown(f"""
                        <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; border-bottom: 1px solid rgba(212,201,176,0.3); padding-bottom: 8px;">
                            <span style="color: {dot_color}; font-size: 1.2rem; line-height: 1;">●</span>
                            <div>
                                <strong>{r.get('risk')}</strong><br>
                                <span style="font-size: 0.8rem; color: #6b7280;">Severity: {sev} | Section: {r.get('section', 'General')}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
            with col_clauses:
                st.markdown("### 📑 Missing Essential Clauses")
                missing_clauses = analysis.get("missing_clauses", [])
                if not missing_clauses:
                    st.success("All primary standard clauses detected.")
                else:
                    for c in missing_clauses:
                        st.markdown(f"""
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; color: #d68910; font-weight: 500;">
                            <span>⚠️</span>
                            <span>{c}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
            st.markdown("---")
            
            # Referenced Laws and Recommendations
            col_laws, col_recs = st.columns(2)
            
            with col_laws:
                st.markdown("### 📜 Referenced Legal Framework")
                referenced_laws = analysis.get("referenced_laws", [])
                if not referenced_laws:
                    st.info("No specific law references parsed.")
                else:
                    for law in referenced_laws:
                        st.markdown(f'<span class="law-ref">{law}</span>', unsafe_allow_html=True)
                        
            with col_recs:
                st.markdown("### 💡 Recommended Actions")
                recommendations = analysis.get("recommendations", [])
                if not recommendations:
                    st.info("No specific recommendations provided.")
                else:
                    for rec in recommendations:
                        st.markdown(f"""
                        <div style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 8px;">
                            <span style="color: #1e8449; font-weight: bold;">✓</span>
                            <span>{rec}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
            st.markdown("---")
            
            # Collapsible spaCy NLP details
            with st.expander("🔬 View NLP Pre-Analysis & Named Entities (spaCy)"):
                nlp_data = analysis.get("nlp_data", {})
                if not nlp_data:
                    st.info("No NLP metadata saved for this analysis.")
                else:
                    st.write(f"**Word Count:** {nlp_data.get('word_count', 0)} words")
                    st.write(f"**Law Source:** {nlp_data.get('law_source', 'database')}")
                    
                    entities = nlp_data.get("entities", {})
                    col_e1, col_e2, col_e3 = st.columns(3)
                    
                    with col_e1:
                        st.markdown("**Parties Identified**")
                        parties = entities.get("parties", [])
                        if parties:
                            for p in parties: st.write(f"- {p}")
                        else: st.write("None identified")
                        
                    with col_e2:
                        st.markdown("**Dates Identified**")
                        dates = entities.get("dates", [])
                        if dates:
                            for d in dates: st.write(f"- {d}")
                        else: st.write("None identified")
                        
                    with col_e3:
                        st.markdown("**Amounts/Values**")
                        amounts = entities.get("amounts", [])
                        if amounts:
                            for a in amounts: st.write(f"- {a}")
                        else: st.write("None identified")
                        
                    st.markdown("**Extracted Obligations (Dependency Parse)**")
                    obligations = nlp_data.get("obligations", [])
                    if obligations:
                        for o in obligations:
                            st.markdown(f"- **{o.get('subject', 'Party')}** {o.get('keyword', 'shall')} *{o.get('verb', 'perform')}*: \"{o.get('text')}\"")
                    else:
                        st.write("No binding obligations parsed.")
