"""Node 2 — Script Writer.

Calls Gemini Flash API to generate a chaotic, funny, educational
dialogue script between two characters.

Input: topic, character_a, character_b, roles from state
Output: JSON array of {character, line} validated via ScriptLine model

Uses response_mime_type="application/json" at API level.
Validates output against Pydantic ScriptLine model — retries on
ValidationError.

Writes to state:
    script, script_line_count, script_duration_estimate_sec
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

from agent.models import ScriptLine
from agent.state import validate_state_for_node

logger = logging.getLogger(__name__)

# Words-per-second estimate for duration calculation
_WORDS_PER_SECOND = 2.5


def _build_system_prompt(
    character_a: str,
    character_a_role: str,
    character_b: str,
    character_b_role: str,
) -> str:
    """Build the Gemini system prompt for script generation.

    Args:
        character_a: Name of character A.
        character_a_role: Role of character A.
        character_b: Name of character B.
        character_b_role: Role of character B.

    Returns:
        System prompt string.
    """
    return (
        "You are a script writer for viral YouTube Shorts "
        "in brainrot style. Two characters have a chaotic, "
        "funny, exaggerated conversation about a topic. "
        "Rules:\n"
        "- Maximum 45 seconds when spoken (roughly 100-120 "
        "words total across all lines)\n"
        "- Use internet slang, caps for emphasis, emojis "
        "in dialogue are fine\n"
        f"- {character_a} is the {character_a_role} one\n"
        f"- {character_b} is the {character_b_role} one\n"
        "- Make it genuinely educational but wrapped in chaos\n"
        "- 8-12 lines total, alternating characters\n"
        f"- Start with {character_a} asking something dumb\n"
        "- End with a punchline"
    )


def _build_user_prompt(
    character_a: str,
    character_b: str,
    topic: str,
) -> str:
    """Build the Gemini user prompt for script generation.

    Args:
        character_a: Name of character A.
        character_b: Name of character B.
        topic: The topic to write about.

    Returns:
        User prompt string.
    """
    return (
        f"Write a script between {character_a} and {character_b} "
        f"about: {topic}\n\n"
        "Return ONLY a JSON array. No other text.\n"
        "Format:\n"
        "[\n"
        f'  {{"character": "{character_a}", "line": "..."}},\n'
        f'  {{"character": "{character_b}", "line": "..."}}\n'
        "]"
    )


def _build_strict_user_prompt(
    character_a: str,
    character_b: str,
    topic: str,
) -> str:
    """Build a stricter retry prompt after first validation failure.

    Args:
        character_a: Name of character A.
        character_b: Name of character B.
        topic: The topic to write about.

    Returns:
        Stricter user prompt string.
    """
    return (
        f"Write a script between {character_a} and {character_b} "
        f"about: {topic}\n\n"
        "STRICT RULES:\n"
        "- EXACTLY 10 lines, alternating between characters\n"
        "- Total word count MUST be between 80-140 words\n"
        f"- First line MUST be from {character_a}\n"
        f"- Lines MUST alternate: {character_a}, {character_b}, "
        f"{character_a}, {character_b}...\n"
        "- Return ONLY a JSON array. No other text.\n"
        "Format:\n"
        "[\n"
        f'  {{"character": "{character_a}", "line": "..."}},\n'
        f'  {{"character": "{character_b}", "line": "..."}}\n'
        "]"
    )


def _validate_script(
    raw_lines: list[dict[str, Any]],
    character_a: str,
    character_b: str,
) -> tuple[bool, str, list[ScriptLine]]:
    """Validate parsed script data against all quality checks.

    Args:
        raw_lines: Parsed JSON list of line dicts.
        character_a: Name of character A.
        character_b: Name of character B.

    Returns:
        Tuple of (is_valid, error_message, validated_lines).
    """
    # 1. Pydantic validation
    try:
        validated = [ScriptLine(**line) for line in raw_lines]
    except ValidationError as e:
        return False, f"Pydantic validation failed: {e}", []

    # 2. Line count check (8-14)
    if not (8 <= len(validated) <= 14):
        return (
            False,
            f"Line count {len(validated)} not in range 8-14",
            [],
        )

    # 3. Total word count check (60-180)
    total_words = sum(
        len(line.line.split()) for line in validated
    )
    if not (60 <= total_words <= 180):
        return (
            False,
            f"Total word count {total_words} not in range 60-180",
            [],
        )

    # 4. Characters alternate (no two consecutive same speaker)
    valid_names = {character_a, character_b}
    for i, line in enumerate(validated):
        if line.character not in valid_names:
            return (
                False,
                f"Line {i} has unknown character "
                f"'{line.character}'",
                [],
            )
        if i > 0 and line.character == validated[i - 1].character:
            return (
                False,
                f"Lines {i-1} and {i} have same character "
                f"'{line.character}' — must alternate",
                [],
            )

    return True, "", validated


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
        f"[script_writer] Sending to Gemini — "
        f"~{len(user_prompt.split())} words in prompt"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config={
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
            "temperature": 0.9,
            "max_output_tokens": 4096,
        },
    )

    return response.text


async def generate_script(
    state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Node 2: Generate a dialogue script via Gemini Flash.

    Args:
        state: Current pipeline state dict.
        config: Loaded config dict.

    Returns:
        Updated state with script, script_line_count, and
        script_duration_estimate_sec populated.
    """
    logger.info(
        f"[script_writer] Starting — "
        f"state keys: {list(state.keys())}"
    )
    start_time = time.perf_counter()

    # --- Check upstream errors ---
    if state.get("error"):
        logger.warning(
            "[script_writer] Upstream error detected, skipping"
        )
        return state

    # --- Validate state ---
    validation_error = validate_state_for_node(
        state, "script_writer"
    )
    if validation_error:
        logger.error(f"[script_writer] {validation_error}")
        return {
            **state,
            "error": validation_error,
            "failed_node": "script_writer",
        }

    try:
        character_a = state["character_a"]
        character_b = state["character_b"]
        character_a_role = state.get("character_a_role", "confused")
        character_b_role = state.get("character_b_role", "explainer")
        topic = state["topic"]

        system_prompt = _build_system_prompt(
            character_a, character_a_role,
            character_b, character_b_role,
        )

        # --- Attempt 1: Normal prompt ---
        user_prompt = _build_user_prompt(
            character_a, character_b, topic
        )

        raw_text = _call_gemini(system_prompt, user_prompt)
        cleaned = re.sub(r",\s*([}\]])", r"\1", raw_text)
        raw_lines = json.loads(cleaned)

        is_valid, error_msg, validated = _validate_script(
            raw_lines, character_a, character_b
        )

        # --- Attempt 2: Stricter prompt if first fails ---
        if not is_valid:
            logger.warning(
                f"[script_writer] First attempt failed validation: "
                f"{error_msg} — retrying with stricter prompt"
            )

            strict_prompt = _build_strict_user_prompt(
                character_a, character_b, topic
            )
            raw_text = _call_gemini(
                system_prompt, strict_prompt
            )
            cleaned = re.sub(r",\s*([}\]])", r"\1", raw_text)
            raw_lines = json.loads(cleaned)

            is_valid, error_msg, validated = _validate_script(
                raw_lines, character_a, character_b
            )

            if not is_valid:
                raise ValueError(
                    f"Script validation failed after 2 attempts: "
                    f"{error_msg}"
                )

        # --- Calculate metrics ---
        script_data = [
            {"character": line.character, "line": line.line}
            for line in validated
        ]
        total_words = sum(
            len(line.line.split()) for line in validated
        )
        duration_estimate = total_words / _WORDS_PER_SECOND

        elapsed = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"[script_writer] Complete in {elapsed:.0f}ms — wrote:\n"
            f"  Lines: {len(validated)}\n"
            f"  Words: {total_words}\n"
            f"  Est. duration: {duration_estimate:.1f}s"
        )

        # Log each line for debugging
        for i, line in enumerate(validated):
            logger.info(
                f"  [{i}] {line.character}: "
                f"'{line.line[:60]}...'"
                if len(line.line) > 60
                else f"  [{i}] {line.character}: '{line.line}'"
            )

        return {
            **state,
            "script": script_data,
            "script_line_count": len(validated),
            "script_duration_estimate_sec": duration_estimate,
        }

    except Exception as e:
        logger.error(f"[script_writer] Failed: {e}")
        return {
            **state,
            "error": f"Script generation failed: {e}",
            "failed_node": "script_writer",
        }
