"""
LLM Client — Groq API wrapper (simulating local Ollama with llama-3.1-8b).
Handles retry, fallback, and structured output parsing.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

# Groq client — singleton
_client: Optional[Groq] = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def llm_generate(
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant.",
    temperature: float = 0.3,
    max_tokens: int = 4096,
    json_mode: bool = False,
    model: Optional[str] = None,
) -> str:
    """
    Generate a response from the LLM.
    Includes retry with exponential backoff.
    """
    client = get_groq_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    use_model = model or settings.groq_model
    kwargs: Dict[str, Any] = {
        "model": use_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    logger.info(f"[LLM] Sending prompt to Groq (Model: {use_model}):\nSystem: {system_prompt}\nUser: {prompt}")

    try:
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.info(
            f"[LLM] Generated {len(content)} chars "
            f"(tokens: {response.usage.total_tokens if response.usage else '?'})"
        )
        return content
    except Exception as e:
        logger.error(f"[LLM] Generation error: {e}")
        raise


def llm_generate_json(
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant. Always respond with valid JSON.",
    temperature: float = 0.2,
    max_tokens: int = 4096,
    model: Optional[str] = None,
) -> dict:
    """Generate structured JSON output from the LLM."""
    raw = llm_generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=True,
        model=model,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            return json.loads(match.group(1))
        # Last resort: try to find JSON object
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group(0))
        logger.error(f"[LLM] Failed to parse JSON: {raw[:200]}")
        raise ValueError("LLM response is not valid JSON")


def extract_attendees_with_llm(
    title: str,
    description: str,
    raw_attendees: list[dict],
    user_email: str
) -> list[dict]:
    """
    Use a fast secondary model (e.g. gemma2-9b-it) to extract structured attendees,
    inferring their company names and excluding the current user.
    """
    system_prompt = (
        "You are an expert data extraction assistant. "
        "Your task is to analyze a meeting's details (title, description, and raw participants list) "
        "and return a clean JSON array of external participants.\n\n"
        "Rules:\n"
        "1. Extract the name, email, and infer the company name for each participant. CRITICAL: Cross-reference the emails with the meeting description to find the person's real full name. Do not just use the email prefix if the name is available in the description.\n"
        "2. If a company name is not explicitly mentioned, infer it from the domain name in their email (e.g. user@acmecorp.com -> AcmeCorp) or from the meeting title/description. If it's a generic email (gmail, yahoo, etc.), leave the company as an empty string.\n"
        "3. EXCLUDE the user whose email matches the provided 'Account Holder Email'. Do not include them in the output.\n"
        "4. Return a JSON object with a single key 'attendees' containing an array of objects. Each object must have keys: 'name', 'email', 'company'.\n"
        "5. ONLY return JSON, no markdown, no conversational text."
    )
    
    prompt = (
        f"Account Holder Email: {user_email}\n\n"
        f"Meeting Title: {title}\n"
        f"Meeting Description: {description}\n\n"
        f"Raw Participants: {json.dumps(raw_attendees)}\n"
    )

    try:
        result = llm_generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=1024,
            model="llama-3.1-8b-instant" # A fast extraction model
        )
        attendees = result.get("attendees", [])
        
        # Add is_external flag explicitly
        clean_attendees = []
        for att in attendees:
            if att.get("email", "").lower() == user_email.lower():
                continue # Double check exclusion
            clean_attendees.append({
                "name": att.get("name", ""),
                "email": att.get("email", ""),
                "company": att.get("company", ""),
                "is_external": True
            })
        return clean_attendees
    except Exception as e:
        logger.error(f"[LLM] Failed to extract attendees via LLM: {e}")
        # Fallback to basic extraction
        fallback = []
        for att in raw_attendees:
            email = att.get("email", "")
            if email.lower() == user_email.lower():
                continue
            
            # Basic company inference from domain
            company = ""
            if email and "@" in email:
                domain = email.split("@")[1].lower()
                if domain not in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "me.com", "icloud.com"]:
                    company = domain.split(".")[0].capitalize()
                    
            fallback.append({
                "name": att.get("displayName", ""),
                "email": email,
                "company": company,
                "is_external": True
            })
        return fallback
