"""
Wraps the Groq client with retry/backoff and a JSON-mode helper.

Provides exponential backoff for resilience against rate limits
and transient network errors. Centralizes configuration logic.
"""
import json
import os
import time
from dotenv import load_dotenv
from groq import Groq
load_dotenv()
DEFAULT_MODEL = "openai/gpt-oss-120b"
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 2
class LLMError(RuntimeError):
    """Raised when the LLM call fails after all retries, or returns bad JSON."""
def _get_client() -> Groq:
    """
    Initialize and return a Groq client.
    
    Reads the API key from environment variables or Streamlit secrets.
    
    Returns:
        Groq: An authenticated Groq client instance.
        
    Raises:
        LLMError: If GROQ_API_KEY is not found.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            pass
    if not api_key:
        raise LLMError(
            "GROQ_API_KEY is not set. Add it to a .env file "
            "(see .env.example) before running the screener."
        )
    return Groq(api_key=api_key)
_client: Groq | None = None
def get_client() -> Groq:
    """
    Get the singleton instance of the Groq client.
    
    Returns:
        Groq: The authenticated Groq client.
    """
    global _client
    if _client is None:
        _client = _get_client()
    return _client
def call_json(system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """Call the chat completion endpoint in JSON mode and return parsed JSON.
    Retries on transient failures (rate limits, network errors, malformed
    JSON) with exponential backoff instead of crashing the whole batch.
    """
    client = get_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            last_error = exc
        except Exception as exc:
            last_error = exc
        if attempt < MAX_RETRIES:
            delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            time.sleep(delay)
    raise LLMError(f"LLM call failed after {MAX_RETRIES} attempts: {last_error}")
