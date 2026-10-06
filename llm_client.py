"""
Thin wrapper over the Groq SDK with basic exponential backoff retries.
Handles API key resolution natively (Streamlit secrets vs .env).
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
    pass


def _get_client() -> Groq:
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
    global _client
    if _client is None:
        _client = _get_client()
    return _client


def call_json(system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL) -> dict:
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
