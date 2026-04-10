"""
stripe_gate.py — Stripe integration for paid tiers.

Pure function interface:
    is_configured() -> bool
    create_checkout_session(user_id, user_email, price_id, success_url, cancel_url) -> str (URL) or None
    create_portal_session(stripe_customer_id, return_url) -> str (URL) or None
    get_subscription_tier(client, user_id) -> str ("free" | "pro" | "team")
    handle_webhook_event(payload, sig_header) -> dict or None

If STRIPE_SECRET_KEY is not set, all tier checks return "free" and
all features defined in TIERS["free"] are available (graceful degradation
for local dev and the free lead-magnet instance).
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# ---------------------------------------------------------------------------
# Lazy Stripe import (only when key is configured)
# ---------------------------------------------------------------------------

_stripe = None


def _get_stripe():
    global _stripe
    if _stripe is not None:
        return _stripe
    if not STRIPE_SECRET_KEY:
        return None
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        _stripe = stripe
        return stripe
    except ImportError:
        logger.warning("stripe package not installed — payment features disabled.")
        return None


def is_configured():
    """Return True if Stripe is configured and importable."""
    return _get_stripe() is not None


# ---------------------------------------------------------------------------
# Checkout + portal
# ---------------------------------------------------------------------------

def create_checkout_session(user_id, user_email, price_id, success_url, cancel_url, mode="payment"):
    """Create a Stripe Checkout session. Returns the checkout URL or None.

    `mode` can be:
        "payment"       — one-time purchase (default, used by the $149 Full Report)
        "subscription"  — recurring subscription (legacy Pro / Team tiers)
    """
    stripe = _get_stripe()
    if stripe is None:
        return None

    try:
        kwargs = dict(
            mode=mode,
            payment_method_types=["card"],
            customer_email=user_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": user_id},
        )
        if mode == "subscription":
            kwargs["subscription_data"] = {"metadata": {"user_id": user_id}}
        else:
            # For one-time payments, attach user_id to the payment intent too
            # so the webhook can reconcile even if session metadata is lost.
            kwargs["payment_intent_data"] = {"metadata": {"user_id": user_id}}

        session = stripe.checkout.Session.create(**kwargs)
        return session.url
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        return None


def create_portal_session(stripe_customer_id, return_url):
    """Create a Stripe Customer Portal session. Returns the URL or None."""
    stripe = _get_stripe()
    if stripe is None:
        return None

    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return session.url
    except Exception as e:
        logger.error(f"Stripe portal error: {e}")
        return None


# ---------------------------------------------------------------------------
# Webhook handling
# ---------------------------------------------------------------------------

def handle_webhook_event(payload, sig_header):
    """Verify and parse a Stripe webhook event.

    Returns a dict with: event_type, user_id, stripe_customer_id,
    stripe_subscription_id, price_id, status — or None on failure.
    """
    stripe = _get_stripe()
    if stripe is None:
        return None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET,
        )
    except Exception as e:
        logger.error(f"Stripe webhook verification failed: {e}")
        return None

    event_type = event["type"]
    data = event["data"]["object"]

    # We care about subscription lifecycle events
    relevant_events = {
        "checkout.session.completed",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }
    if event_type not in relevant_events:
        return {"event_type": event_type, "handled": False}

    if event_type == "checkout.session.completed":
        return {
            "event_type": event_type,
            "handled": True,
            "user_id": data.get("metadata", {}).get("user_id"),
            "stripe_customer_id": data.get("customer"),
            "stripe_subscription_id": data.get("subscription"),
        }

    # subscription.updated or .deleted
    metadata = data.get("metadata", {})
    items = data.get("items", {}).get("data", [])
    price_id = items[0]["price"]["id"] if items else None

    return {
        "event_type": event_type,
        "handled": True,
        "user_id": metadata.get("user_id"),
        "stripe_customer_id": data.get("customer"),
        "stripe_subscription_id": data.get("id"),
        "price_id": price_id,
        "status": data.get("status"),
    }


# ---------------------------------------------------------------------------
# Tier resolution
# ---------------------------------------------------------------------------

def get_subscription_tier(client, user_id):
    """Return the user's current feature tier from Supabase.

    Resolution order:
      1. If Stripe is not configured, return "report" (graceful degradation —
         all paid features unlocked for dev/demo instances).
      2. If the user has any completed row in the `purchases` table
         (full_report or equivalent), return "report". Lifetime unlock.
      3. If the user has an active row in the `subscriptions` table, return
         that row's tier (legacy path for any grandfathered subscribers).
      4. Otherwise return "free".
    """
    if not STRIPE_SECRET_KEY:
        # Graceful degradation: no Stripe = all paid features unlocked
        return "report"

    if client is None or not user_id:
        return "free"

    # 1. Check for a lifetime one-time purchase first
    try:
        purchase_result = (
            client.table("purchases")
            .select("product_type, status")
            .eq("user_id", user_id)
            .eq("status", "completed")
            .limit(1)
            .execute()
        )
        if purchase_result.data:
            product_type = purchase_result.data[0].get("product_type", "full_report")
            if product_type == "full_report":
                return "report"
    except Exception as e:
        # Table may not exist yet if migration hasn't run — fall through to subscriptions
        logger.debug(f"Purchases lookup skipped: {e}")

    # 2. Fall back to legacy subscription tier
    try:
        result = (
            client.table("subscriptions")
            .select("tier, status")
            .eq("user_id", user_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0].get("tier", "free")
        return "free"
    except Exception as e:
        logger.error(f"Subscription lookup error: {e}")
        return "free"
