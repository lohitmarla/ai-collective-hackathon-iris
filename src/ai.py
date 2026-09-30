"""Optional Google Gemini intent expansion with a local-only fallback."""
import logging
import json
import os

logger = logging.getLogger(__name__)


def _get_api_key() -> str | None:
    """Read the Google AI Studio key from the environment or Streamlit secrets."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            api_key = None
    return api_key


def extract_search_terms(query: str) -> list[str]:
    """Ask Gemini for search keywords; return an empty expansion on any failure."""
    api_key = _get_api_key()
    if not api_key or not query.strip():
        return []
    try:
        from google import genai
        client = genai.Client(api_key=api_key, http_options={"timeout": 60000})
        response = client.interactions.create(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            input=(
                "Extract up to 6 short search keywords or topics from the student's "
                "request for campus resources. Return only comma-separated keywords. "
                "Do not answer the request or add facts.\n\n"
                f"Student request: {query[:500]}"
            ),
            generation_config={"thinking_level": "low", "max_output_tokens": 60},
            timeout=60,
        )
        text = response.output_text or ""
        return [part.strip() for part in text.split(",") if part.strip()][:6]
    except Exception as e:
        logger.warning("Gemini search-term extraction failed: %s", e)
        return []


def generate_conversational_reply(
    query: str,
    history: list[dict],
    matches: list[dict],
) -> str | None:
    """Answer a follow-up using only the current local matches as factual context."""
    api_key = _get_api_key()
    if not api_key:
        return None
    resource_by_id = {}
    for turn in history:
        for item in turn.get("matches", []):
            resource_by_id[item["resource"]["id"]] = item["resource"]
    for item in matches:
        resource_by_id[item["resource"]["id"]] = item["resource"]
    resources = [
        {
            "name": item["name"],
            "category": item["category"],
            "description": item["description"],
            "cost": item["cost"],
            "eligibility": item["eligibility"],
            "location": item["location"],
            "url": item["url"],
        }
        for item in list(resource_by_id.values())[:8]
    ]
    turns = "\n".join(
        f"{turn['role']}: {turn['content']}"
        for turn in history[-8:]
        if turn.get("role") in {"user", "assistant"}
    )
    prompt = (
        "You are StudentConnect CT, a friendly conversational guide to UConn Hartford "
        "student support and Connecticut events. Keep replies concise and answer "
        "follow-up questions using the conversation and resource records below. "
        "Treat the records as the only source for resource facts. Never invent hours, "
        "availability, costs, eligibility, or services; suggest checking the linked "
        "official page for changing details. If the request is unrelated, briefly say "
        "you specialize in UConn Hartford student resources and Connecticut events, "
        "then invite a related question. For current event listings, direct the user "
        "to the events options rather than inventing listings.\n\n"
        f"Recent conversation:\n{turns or '(start of conversation)'}\n\n"
        f"Matched local resources (may be empty):\n{json.dumps(resources, ensure_ascii=False)}\n\n"
        f"New user message:\n{query[:1000]}"
    )
    try:
        from google import genai
        client = genai.Client(api_key=api_key, http_options={"timeout": 60000})
        response = client.interactions.create(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            input=prompt,
            generation_config={"thinking_level": "low", "max_output_tokens": 300},
            timeout=60,
        )
        return (response.output_text or "").strip() or None
    except Exception as e:
        logger.warning("Gemini conversational reply failed: %s", e)
        return None
