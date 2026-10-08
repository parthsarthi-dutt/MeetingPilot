"""
OSINT MCP Server — Utility functions.

Shared helpers for person key computation and credit checks,
used by both tools and resources.
"""

from __future__ import annotations

import hashlib
from typing import Optional


def compute_person_key(email: Optional[str], name: str, company: str) -> str:
    """
    Compute a stable, unique person_key for OSINT caching.

    Primary: email address (lowercased) if available.
    Fallback: SHA-256 hash of normalized 'name|company' string.
    """
    if email and "@" in email:
        return email.lower().strip()
    raw = f"{name.strip().lower()}|{company.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
