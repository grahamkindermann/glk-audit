"""
db_queries.py — CRUD operations for the Structural Advantage audit platform.

All functions take a Supabase client as the first argument. If the client
is None, they return sensible defaults (empty lists, None) so the app
works without a database.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def sign_up(client, email, password):
    """Sign up a new user. Returns (user, error_message)."""
    if client is None:
        return None, "Database not configured"
    try:
        res = client.auth.sign_up({"email": email, "password": password})
        if res.user:
            return res.user, None
        return None, "Sign-up failed. Check your email for confirmation."
    except Exception as e:
        logger.error(f"Sign-up error: {e}")
        return None, str(e)


def sign_in(client, email, password):
    """Sign in an existing user. Returns (session, error_message)."""
    if client is None:
        return None, "Database not configured"
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.session:
            return res.session, None
        return None, "Invalid email or password."
    except Exception as e:
        logger.error(f"Sign-in error: {e}")
        return None, str(e)


def sign_out(client):
    """Sign out the current user."""
    if client is None:
        return
    try:
        client.auth.sign_out()
    except Exception as e:
        logger.error(f"Sign-out error: {e}")


def get_current_user(client):
    """Return the current authenticated user or None."""
    if client is None:
        return None
    try:
        return client.auth.get_user()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

def upsert_company(client, user_id, firmographics):
    """Create or update a company for the given user.

    Uses company name as the natural key for upsert logic.
    Returns the company record (dict) or None.
    """
    if client is None:
        return None

    name = (firmographics.get("company_name") or "").strip()
    if not name:
        return None

    try:
        # Check if company already exists for this user
        existing = (
            client.table("companies")
            .select("*")
            .eq("user_id", user_id)
            .eq("name", name)
            .limit(1)
            .execute()
        )

        company_data = {
            "user_id": user_id,
            "name": name,
            "industry": firmographics.get("industry"),
            "revenue_band": firmographics.get("revenue_band"),
            "ebitda_margin": firmographics.get("ebitda_margin"),
            "headcount": firmographics.get("employees"),
            "years": firmographics.get("years"),
            "owner_hours": firmographics.get("owner_hours"),
        }

        if existing.data:
            # Update existing
            company_id = existing.data[0]["id"]
            company_data["updated_at"] = datetime.utcnow().isoformat()
            result = (
                client.table("companies")
                .update(company_data)
                .eq("id", company_id)
                .execute()
            )
            return result.data[0] if result.data else existing.data[0]
        else:
            # Insert new
            result = (
                client.table("companies")
                .insert(company_data)
                .execute()
            )
            return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Company upsert error: {e}")
        return None


def get_companies(client, user_id):
    """Return all companies for a user, ordered by most recent."""
    if client is None:
        return []
    try:
        result = (
            client.table("companies")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Get companies error: {e}")
        return []


# ---------------------------------------------------------------------------
# Audits
# ---------------------------------------------------------------------------

def save_audit(client, user_id, company_id, mode, answers, firmographics,
               result, ai_recommendations=None):
    """Save a completed audit. Returns the audit record or None."""
    if client is None:
        return None

    try:
        overall = result.get("overall", {})
        audit_data = {
            "user_id": user_id,
            "company_id": company_id,
            "mode": mode,
            "answers": answers,
            "firmographics": firmographics,
            "result": result,
            "ai_recommendations": ai_recommendations,
            "overall_score": overall.get("score"),
            "overall_band": overall.get("band_label"),
        }
        res = (
            client.table("audits")
            .insert(audit_data)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Save audit error: {e}")
        return None


def get_audits_for_company(client, company_id, limit=20):
    """Return audits for a company, newest first."""
    if client is None:
        return []
    try:
        result = (
            client.table("audits")
            .select("id, mode, overall_score, overall_band, created_at")
            .eq("company_id", company_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Get audits error: {e}")
        return []


def get_audit(client, audit_id):
    """Return a single audit with all data."""
    if client is None:
        return None
    try:
        result = (
            client.table("audits")
            .select("*")
            .eq("id", audit_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Get audit error: {e}")
        return None


def get_audits_for_user(client, user_id, limit=50):
    """Return all audits for a user, newest first."""
    if client is None:
        return []
    try:
        result = (
            client.table("audits")
            .select("id, company_id, mode, overall_score, overall_band, created_at, firmographics")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Get user audits error: {e}")
        return []
