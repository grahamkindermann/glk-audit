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

        # Build per-dimension score snapshot for historical tracking
        dim_scores = {}
        for dim_id, dim in result.get("dimensions", {}).items():
            dim_scores[dim_id] = {
                "name": dim.get("name", dim_id),
                "score": dim.get("score"),
                "band_label": dim.get("band_label", ""),
            }

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
            "dimension_scores": dim_scores,
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
            .select("id, mode, overall_score, overall_band, dimension_scores, ai_recommendations, created_at")
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
            .select("id, company_id, mode, overall_score, overall_band, created_at, firmographics, dimension_scores")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Get user audits error: {e}")
        return []


# ---------------------------------------------------------------------------
# Historical queries (Phase 5)
# ---------------------------------------------------------------------------

def get_audit_history(client, company_id, limit=20):
    """Return audit history for a company (for trend charts).

    Returns list of dicts with: id, overall_score, overall_band,
    dimension_scores, created_at — ordered oldest first for charting.
    """
    if client is None:
        return []
    try:
        result = (
            client.table("audits")
            .select("id, overall_score, overall_band, dimension_scores, created_at")
            .eq("company_id", company_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Get audit history error: {e}")
        return []


def get_previous_audit(client, company_id, before_id):
    """Return the most recent audit for a company that is NOT the given audit.

    Used for 'vs. last audit' comparison on the results page.
    Returns a single audit dict or None.
    """
    if client is None:
        return None
    try:
        result = (
            client.table("audits")
            .select("id, overall_score, overall_band, dimension_scores, ai_recommendations, created_at")
            .eq("company_id", company_id)
            .neq("id", before_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Get previous audit error: {e}")
        return None


# ---------------------------------------------------------------------------
# Recommendation tracker (Phase 5)
# ---------------------------------------------------------------------------

def save_recommendations(client, user_id, company_id, audit_id, recommendations):
    """Save a batch of recommendations from an audit.

    recommendations: list of {"dimension": str, "recommendation": str}
    Returns list of saved records or empty list.
    """
    if client is None:
        return []
    if not recommendations:
        return []

    try:
        rows = [
            {
                "user_id": user_id,
                "company_id": company_id,
                "audit_id": audit_id,
                "dimension": r["dimension"],
                "recommendation": r["recommendation"],
                "status": "not_started",
            }
            for r in recommendations
        ]
        result = (
            client.table("recommendation_tracker")
            .insert(rows)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Save recommendations error: {e}")
        return []


def get_recommendations_for_company(client, company_id):
    """Return all tracked recommendations for a company, newest first."""
    if client is None:
        return []
    try:
        result = (
            client.table("recommendation_tracker")
            .select("*")
            .eq("company_id", company_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Get recommendations error: {e}")
        return []


def update_recommendation_status(client, rec_id, new_status):
    """Update the status of a single recommendation.

    new_status: 'not_started' | 'in_progress' | 'done'
    Returns the updated record or None.
    """
    if client is None:
        return None
    try:
        result = (
            client.table("recommendation_tracker")
            .update({"status": new_status, "updated_at": datetime.utcnow().isoformat()})
            .eq("id", rec_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Update recommendation status error: {e}")
        return None
