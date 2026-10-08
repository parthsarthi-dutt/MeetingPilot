"""
OSINT MCP Server — FastMCP Server Definition.

This is the main server module that creates the FastMCP instance
and registers all tools, resources, and prompts.

Run standalone:  python -m app.mcp.osint_server
Or via FastMCP:  fastmcp run app/mcp/osint_server/server.py
"""

import json
import logging
import time
import uuid
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context

from app.mcp.osint_server.config import OSINTServerConfig
from app.mcp.osint_server.pipeline import PersonOSINTPipeline
from app.mcp.osint_server.utils import compute_person_key

logger = logging.getLogger(__name__)

# ─── Server Configuration ────────────────────────────────────
config = OSINTServerConfig.from_env()

# ─── Initialize FastMCP Server ────────────────────────────────
mcp = FastMCP(config.server_name)

# ─── Lazy DB initialization (only when needed) ───────────────
_db = None


def _get_db():
    global _db
    if _db is None:
        from app.mcp.osint_server.db import MCPDatabase
        _db = MCPDatabase(config.database_url)
    return _db


def _get_pipeline() -> PersonOSINTPipeline:
    """Create a new pipeline instance with current config."""
    return PersonOSINTPipeline(
        jina_api_key=config.jina_api_key,
        apify_token=config.apify_token,
        hunter_key=config.hunter_api_key,
        linkdapi_key=config.linkdapi_key,
    )


# =============================================================================
# TOOLS — Executable actions the LLM/agent can invoke
# =============================================================================


@mcp.tool()
async def research_person(
    name: str,
    company: str,
    email: Optional[str] = None,
    user_id: Optional[str] = None,
    force_rerun: bool = False,
    ctx: Context = None,
) -> str:
    """
    Research a person using multi-source OSINT intelligence.

    Performs LinkedIn profiling, web presence analysis, company research,
    email verification, and recent news gathering. Results are cached
    per person_key (email or name|company hash) and reused on subsequent calls.

    Args:
        name: Full name of the person to research.
        company: Company/organization the person is associated with.
        email: Email address (optional but improves accuracy).
        user_id: UUID of the requesting user (for credit tracking).
        force_rerun: If True, bypasses cache and re-runs the full pipeline.

    Returns:
        JSON string with the research results and metadata including:
        - status: "success", "cached", "skipped", "credit_exhausted", or "failed"
        - person_key: The unique identifier used for caching
        - osint_data: The full OSINT research output (if available)
        - credit_charged: Whether a credit was consumed
        - duration_ms: Time taken in milliseconds
    """
    t0 = time.time()
    person_key = compute_person_key(email, name, company)

    await ctx.info(f"Starting OSINT research for: {name} ({company})")

    db = _get_db()

    # ─── 1. Check do_not_research opt-out ─────────────────
    if user_id:
        uid = uuid.UUID(user_id)
        existing = await db.get_person_research(uid, person_key)

        if existing and existing.do_not_research:
            await ctx.info(f"Skipped: {name} has do_not_research=True")
            return json.dumps({
                "status": "skipped",
                "reason": "do_not_research",
                "person_key": person_key,
                "osint_data": None,
                "credit_charged": False,
                "duration_ms": int((time.time() - t0) * 1000),
            })

        # ─── 2. Check cache ──────────────────────────────
        if existing and existing.osint_data and not force_rerun:
            await ctx.info(f"Cache hit for {name} — reusing stored data")
            return json.dumps({
                "status": "cached",
                "person_key": person_key,
                "osint_data": existing.osint_data,
                "credit_charged": False,
                "duration_ms": int((time.time() - t0) * 1000),
            })

        # ─── 3. Check credit quota ───────────────────────
        used, total = await db.get_credits(uid)
        if used >= total:
            await ctx.warning(f"Credit limit reached for user {user_id}: {used}/{total}")
            return json.dumps({
                "status": "credit_exhausted",
                "reason": "osint_unavailable_credit_limit",
                "person_key": person_key,
                "osint_data": None,
                "credit_charged": False,
                "credits_used": used,
                "credits_total": total,
                "duration_ms": int((time.time() - t0) * 1000),
            })

    # ─── 4. Run the OSINT pipeline ────────────────────────
    await ctx.info(f"Running OSINT pipeline for {name}...")
    await ctx.report_progress(0.1, 1.0)

    pipeline = _get_pipeline()

    try:
        osint_data = pipeline.run(name, email or "", company)
    except Exception as e:
        await ctx.error(f"Pipeline failed for {name}: {e}")
        return json.dumps({
            "status": "failed",
            "reason": str(e),
            "person_key": person_key,
            "osint_data": None,
            "credit_charged": False,
            "duration_ms": int((time.time() - t0) * 1000),
        })

    await ctx.report_progress(0.9, 1.0)

    # ─── 5. Store result and increment credit ─────────────
    if user_id:
        uid = uuid.UUID(user_id)
        await db.save_person_research(uid, person_key, osint_data, credit_charged=True)
        await db.increment_credits(uid)
        await ctx.info(f"Stored result and charged 1 credit for {name}")

    duration_ms = int((time.time() - t0) * 1000)
    await ctx.report_progress(1.0, 1.0)
    await ctx.info(f"OSINT research complete for {name} in {duration_ms}ms")

    return json.dumps({
        "status": "success",
        "person_key": person_key,
        "osint_data": osint_data,
        "credit_charged": True,
        "duration_ms": duration_ms,
    })


@mcp.tool()
async def check_credits(
    user_id: str,
    ctx: Context = None,
) -> str:
    """
    Check the remaining OSINT credits for a user.

    Args:
        user_id: UUID of the user to check credits for.

    Returns:
        JSON string with used_count, total_allowed, and remaining.
    """
    db = _get_db()
    uid = uuid.UUID(user_id)
    used, total = await db.get_credits(uid)

    await ctx.info(f"Credits for {user_id}: {used}/{total}")

    return json.dumps({
        "used_count": used,
        "total_allowed": total,
        "remaining": total - used,
    })


@mcp.tool()
async def get_cached_research(
    name: str,
    company: str,
    email: Optional[str] = None,
    user_id: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """
    Retrieve previously cached OSINT research for a person without running
    the pipeline. Returns null if no cached data exists.

    Args:
        name: Full name of the person.
        company: Company the person is associated with.
        email: Email address (optional).
        user_id: UUID of the requesting user.

    Returns:
        JSON string with cached osint_data or null if not found.
    """
    person_key = compute_person_key(email, name, company)

    if not user_id:
        return json.dumps({"status": "error", "reason": "user_id is required"})

    db = _get_db()
    uid = uuid.UUID(user_id)
    existing = await db.get_person_research(uid, person_key)

    if existing and existing.osint_data:
        await ctx.info(f"Found cached data for {name}")
        return json.dumps({
            "status": "found",
            "person_key": person_key,
            "osint_data": existing.osint_data,
            "do_not_research": existing.do_not_research,
        })

    await ctx.info(f"No cached data for {name}")
    return json.dumps({
        "status": "not_found",
        "person_key": person_key,
        "osint_data": None,
    })


# =============================================================================
# RESOURCES — Data the LLM/agent can read
# =============================================================================


@mcp.resource("osint://credits/{user_id}")
async def get_credit_balance(user_id: str) -> str:
    """Read the OSINT credit balance for a user."""
    db = _get_db()
    uid = uuid.UUID(user_id)
    used, total = await db.get_credits(uid)
    return json.dumps({
        "user_id": user_id,
        "used_count": used,
        "total_allowed": total,
        "remaining": total - used,
    })


@mcp.resource("osint://person/{user_id}/{person_key}")
async def get_person_data(user_id: str, person_key: str) -> str:
    """Read cached OSINT data for a specific person."""
    db = _get_db()
    uid = uuid.UUID(user_id)
    existing = await db.get_person_research(uid, person_key)
    if existing:
        return json.dumps({
            "person_key": person_key,
            "osint_data": existing.osint_data,
            "credit_charged": existing.credit_charged,
            "do_not_research": existing.do_not_research,
            "created_at": existing.created_at.isoformat() if existing.created_at else None,
        })
    return json.dumps({"person_key": person_key, "status": "not_found"})


# =============================================================================
# PROMPTS — Reusable prompt templates for the LLM
# =============================================================================


@mcp.prompt()
def research_brief_prompt(name: str, company: str, context: str = "") -> str:
    """
    Generate a prompt template for creating a research brief from OSINT data.

    Args:
        name: The person's name.
        company: Their company.
        context: Additional context about why this research is needed.
    """
    return f"""Analyze the following OSINT research data and create a concise
meeting preparation brief for {name} from {company}.

{f"Context: {context}" if context else ""}

Focus on:
1. Professional background and current role
2. Key achievements and expertise areas
3. Company context and recent developments
4. Potential talking points and common ground
5. Any relevant recent activity or publications

Keep the brief actionable and focused on what would be most useful
for a meeting preparation context."""


if __name__ == "__main__":
    mcp.run()

