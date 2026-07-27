"""
Thin wrapper around the Gemini API.

Uses Gemini's structured-output mode (response_schema) so we get back a
validated Pydantic object instead of hand-parsing free text — this is what
makes the "AI responses" in this project structured rather than plain Q&A.
"""

from typing import Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from src.config import api_key_configured, settings

T = TypeVar("T", bound=BaseModel)

_client: genai.Client | None = None


class GeminiNotConfiguredError(RuntimeError):
    """Raised when GEMINI_API_KEY is missing so the UI can show a clean message."""


def get_client() -> genai.Client:
    global _client
    if not api_key_configured():
        raise GeminiNotConfiguredError(
            "GEMINI_API_KEY is not set. Add it to a .env file "
            "(see .env) or your environment variables."
        )
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def generate_structured(
    prompt: str,
    schema: Type[T],
    system_instruction: str | None = None,
) -> T:
    """
    Call Gemini and parse the response straight into the given Pydantic model.
    """
    client = get_client()

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=settings.GEMINI_TEMPERATURE,
        system_instruction=system_instruction,
    )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=config,
    )

    # The SDK will populate .parsed when response_schema is a Pydantic model.
    # Fall back to manual validation from .text if .parsed isn't available,
    # which keeps this working even if the SDK's auto-parsing behavior changes.
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, schema):
        return parsed
    return schema.model_validate_json(response.text)
