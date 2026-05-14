"""Node 6 — Metadata Generator.

Calls Gemini Flash to generate YouTube Shorts metadata:
    - Catchy title (max 80 chars, with emojis)
    - 2-3 sentence description
    - Hashtags including #Shorts
    - YouTube tags

Uses response_mime_type="application/json" at API level.
Validates output against Pydantic VideoMetadata model.

Writes to state:
    title, description, hashtags, tags
"""

import json
import logging
import os
import re
import time
from typing import Any

from google import genai
from google.api_core import exceptions as google_exceptions
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from agent.models import VideoMetadata
from agent.state import validate_state_for_node

logger = logging.getLogger(__name__)


def _build_system_prompt() -> str:
    """Build the Gemini system prompt for metadata generation.

    Returns:
        System prompt string.
    """
    return (
        "You are a YouTube Shorts metadata writer. "
        "Generate viral metadata for a brainrot-style "
        "educational Short."
    )


def _build_user_prompt(
    character_a: str,
    character_b: str,
    topic: str,
    first_3_lines: str,
) -> str:
    """Build the Gemini user prompt for metadata generation.

    Args:
        character_a: Name of character A.
        character_b: Name of character B.
        topic: The video topic.
        first_3_lines: Preview of the first 3 script lines.

    Returns:
        User prompt string.
    """
    return (
        f"Video: {character_a} and {character_b} discuss "
        f"'{topic}' in brainrot style.\n"
        f"Script preview (first 3 lines): {first_3_lines}\n\n"
        "Generate metadata. Return ONLY JSON, no other text:\n"
        "{\n"
        '  "title": "...",\n'
        '  "description": "...",\n'
        '  "hashtags": ["#Shorts", ...]\n'
        "}"
    )


def _get_client() -> genai.Client:
    """Create and return a Gemini API client.

    Returns:
        Configured genai.Client instance.

    Raises:
        RuntimeError: If GEMINI_API_KEY is not set.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set in environment. "
            "Add it to .env file."
        )
    return genai.Client(api_key=api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=10, max=60),
    retry=retry_if_exception_type((
        json.JSONDecodeError,
        ConnectionError,
        TimeoutError,
        OSError,
        google_exceptions.GoogleAPIError,
        google_exceptions.ResourceExhausted,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_gemini(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Call Gemini Flash with retry logic.

    Args:
        system_prompt: System instruction for the model.
        user_prompt: User message with the task.

    Returns:
        Raw response text from Gemini.
    """
    client = _get_client()

    logger.info(
        f"[metadata_generator] Sending to Gemini — "
        f"~{len(user_prompt.split())} words in prompt"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config={
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
            "temperature": 0.7,
            "max_output_tokens": 4096,
        },
    )

    return response.text


async def generate_metadata(
    state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Node 6: Generate YouTube Shorts metadata via Gemini Flash.

    Args:
        state: Current pipeline state dict.
        config: Loaded config dict.

    Returns:
        Updated state with title, description, hashtags,
        and tags populated.
    """
    logger.info(
        f"[metadata_generator] Starting — "
        f"state keys: {list(state.keys())}"
    )
    start_time = time.perf_counter()

    # --- Check upstream errors ---
    if state.get("error"):
        logger.warning(
            "[metadata_generator] Upstream error detected, skipping"
        )
        return state

    # --- Validate state ---
    validation_error = validate_state_for_node(
        state, "metadata_generator"
    )
    if validation_error:
        logger.error(f"[metadata_generator] {validation_error}")
        return {
            **state,
            "error": validation_error,
            "failed_node": "metadata_generator",
        }

    try:
        character_a = state["character_a"]
        character_b = state["character_b"]
        topic = state["topic"]
        script = state.get("script", [])

        # Build first 3 lines preview
        preview_lines = script[:3]
        first_3_lines = " | ".join(
            f"{line['character']}: {line['line']}"
            for line in preview_lines
        )

        # --- Call Gemini ---
        system_prompt = _build_system_prompt()
        user_prompt = _build_user_prompt(
            character_a, character_b, topic, first_3_lines
        )

        raw_text = _call_gemini(system_prompt, user_prompt)
        # Strip trailing commas before ] or } (Gemini quirk)
        cleaned = re.sub(r",\s*([}\]])", r"\1", raw_text)
        raw_data = json.loads(cleaned)

        # --- Validate with Pydantic ---
        # Truncate title to 80 chars if over
        raw_title = raw_data.get("title", "")
        if len(raw_title) > 80:
            logger.warning(
                f"[metadata_generator] Title too long "
                f"({len(raw_title)} chars) — truncating to 80"
            )
            raw_data["title"] = raw_title[:77] + "..."

        try:
            metadata = VideoMetadata(**raw_data)
        except ValidationError as e:
            logger.error(
                f"[metadata_generator] Pydantic validation failed: {e}"
            )
            raise ValueError(
                f"Metadata validation failed: {e}"
            ) from e

        # Generate tags from hashtags (strip # prefix)
        tags = [
            tag.lstrip("#") for tag in metadata.hashtags
            if tag != "#Shorts"
        ]

        elapsed = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"[metadata_generator] Complete in {elapsed:.0f}ms — "
            f"wrote:\n"
            f"  Title: '{metadata.title}'\n"
            f"  Description: '{metadata.description[:80]}...'\n"
            f"  Hashtags: {metadata.hashtags}\n"
            f"  Tags: {tags}"
        )

        return {
            **state,
            "title": metadata.title,
            "description": metadata.description,
            "hashtags": metadata.hashtags,
            "tags": tags,
        }

    except Exception as e:
        logger.error(f"[metadata_generator] Failed: {e}")
        return {
            **state,
            "error": f"Metadata generation failed: {e}",
            "failed_node": "metadata_generator",
        }
