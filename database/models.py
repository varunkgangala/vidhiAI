import os
import json
from datetime import datetime

# ── Supabase connection ──────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


def get_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "Supabase credentials missing.\n"
            "Please set SUPABASE_URL and SUPABASE_KEY in your .env file."
        )

    from supabase import create_client

    return create_client(SUPABASE_URL, SUPABASE_KEY)
    # if not SUPABASE_URL or not SUPABASE_KEY:
    #     raise RuntimeError(
    #         "Supabase credentials missing.\n"
    #         "Please set SUPABASE_URL and SUPABASE_KEY in your .env file."
    #     )
    # from supabase import create_client, ClientOptions
    # options = ClientOptions(
    #     postgrest_client_timeout=30,
    #     storage_client_timeout=30,
    # )
    # from supabase import create_client
    # return create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db():
    try:
        client = get_client()
        client.table("users").select("user_id").limit(1).execute()
        print("[VidhiAI] Supabase connection successful.")
    except RuntimeError as e:
        print(f"[VidhiAI] WARNING: {e}")
    except Exception as e:
        print(f"[VidhiAI] WARNING: Could not connect to Supabase: {e}")


# ── User helpers ─────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> dict | None:
    try:
        client = get_client()
        res = client.table("users").select("*").eq("email", email).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[VidhiAI DB] Error getting user: {e}")
        raise RuntimeError(f"Database connection failed: {e}")


def get_user_by_id(user_id: int) -> dict | None:
    client = get_client()
    res = client.table("users").select("*").eq("user_id", user_id).limit(1).execute()
    return res.data[0] if res.data else None


def get_user_by_email_or_username(email: str, username: str) -> dict | None:
    client = get_client()
    # Check email first
    res_email = client.table("users").select("user_id").eq("email", email).limit(1).execute()
    if res_email.data:
        return res_email.data[0]
    # Check username second
    res_user = client.table("users").select("user_id").eq("username", username).limit(1).execute()
    if res_user.data:
        return res_user.data[0]
    return None


def create_user(username: str, email: str, hashed_password: str) -> dict:
    client = get_client()
    res = client.table("users").insert({
        "username": username,
        "email": email,
        "password": hashed_password,
    }).execute()
    return res.data[0]


# ── Analysis history helpers ─────────────────────────────────────────────────

def save_analysis(user_id: int, document_name: str, compliance_score: float,
                  risk_level: str, analysis_text: str) -> dict:
    client = get_client()
    res = client.table("analysis_history").insert({
        "user_id": user_id,
        "document_name": document_name,
        "compliance_score": compliance_score,
        "risk_level": risk_level,
        "analysis_text": analysis_text,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }).execute()
    return res.data[0]


def get_recent_analyses(user_id: int, limit: int = 5) -> list:
    client = get_client()
    res = (
        client.table("analysis_history")
        .select("*")
        .eq("user_id", user_id)
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def get_all_analyses(user_id: int) -> list:
    client = get_client()
    res = (
        client.table("analysis_history")
        .select("*")
        .eq("user_id", user_id)
        .order("timestamp", desc=True)
        .execute()
    )
    return res.data or []


def get_analysis_by_id(analysis_id: int, user_id: int) -> dict | None:
    client = get_client()
    res = (
        client.table("analysis_history")
        .select("*")
        .eq("analysis_id", analysis_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def delete_analysis(analysis_id: int, user_id: int) -> None:
    client = get_client()
    client.table("analysis_history").delete()\
        .eq("analysis_id", analysis_id)\
        .eq("user_id", user_id)\
        .execute()


def get_user_stats(user_id: int) -> dict:
    records = get_all_analyses(user_id)
    if not records:
        return {"total": 0, "avg_score": None, "high_risk": 0}
    total     = len(records)
    avg_score = sum(r["compliance_score"] for r in records) / total
    high_risk = sum(1 for r in records if r["risk_level"] == "High")
    return {"total": total, "avg_score": avg_score, "high_risk": high_risk}