"""
db_client.py, Supabase client initialization.

Graceful degradation: if SUPABASE_URL or SUPABASE_KEY are not set,
get_client() returns None. All downstream code must check for None
before using the client. This lets the app work without a database
(free lead-magnet mode).
"""

import os
import logging

logger = logging.getLogger(__name__)

_client = None
_initialized = False

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


def get_client():
    """Return a Supabase client singleton, or None if not configured."""
    global _client, _initialized

    if _initialized:
        return _client

    _initialized = True

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.info("SUPABASE_URL or SUPABASE_KEY not set, database disabled.")
        return None

    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized.")
        return _client
    except ImportError:
        logger.warning("supabase package not installed, database disabled.")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def is_configured():
    """Check if Supabase is configured (without initializing)."""
    return bool(SUPABASE_URL and SUPABASE_KEY)
