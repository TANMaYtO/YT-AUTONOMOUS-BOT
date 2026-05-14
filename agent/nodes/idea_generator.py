"""Node 1 — Idea Generator.

Selects a topic and two characters for the next video.

Logic:
    1. Load history.json (last 30 entries)
    2. Weighted random topic pick (recently-used get 0.1 weight)
    3. Pick 1 confused + 1 explainer character, avoiding recent pairs
    4. Store selections in state (does NOT write to history.json)

Writes to state:
    topic, character_a, character_b, character_a_role,
    character_b_role, character_a_voice, character_b_voice,
    character_a_image_folder, character_b_image_folder,
    trend_source
"""

import json
import logging
import random
import time
from pathlib import Path
from typing import Any

from agent.models import CharacterConfig
from agent.state import validate_state_for_node

logger = logging.getLogger(__name__)

HISTORY_WINDOW = 30  # Only look at last N entries for weighting
MAX_PAIR_REROLLS = 5  # Max attempts to find a non-duplicate pair


def _load_history(history_path: Path) -> list[dict[str, Any]]:
    """Load history.json, creating it if it doesn't exist.

    Args:
        history_path: Path to history.json file.

    Returns:
        List of history entries (may be empty).
    """
    if not history_path.exists():
        logger.info(
            f"[idea_generator] history.json not found at "
            f"{history_path} — creating empty"
        )
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text("[]", encoding="utf-8")
        return []

    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            logger.warning(
                "[idea_generator] history.json is not a list — resetting"
            )
            return []
        return data
    except json.JSONDecodeError as e:
        logger.warning(
            f"[idea_generator] history.json parse error: {e} — resetting"
        )
        return []


def _pick_topic(
    topics: list[str],
    recent_history: list[dict[str, Any]],
) -> str:
    """Pick a topic using weighted random selection.

    Topics used in recent history get 0.1 weight.
    Topics not used recently get 1.0 weight.
    The immediately previous topic is hard-blocked.

    Args:
        topics: Full list of available topics from config.
        recent_history: Last N history entries.

    Returns:
        Selected topic string.
    """
    # Hard-block: never repeat the immediately previous topic
    last_topic = ""
    if recent_history:
        last_topic = recent_history[-1].get("topic", "")

    # Build weight map
    recent_topics = {
        entry.get("topic", "") for entry in recent_history
    }

    weights: list[float] = []
    eligible_topics: list[str] = []

    for topic in topics:
        if topic == last_topic:
            continue  # Hard block
        eligible_topics.append(topic)
        weight = 0.1 if topic in recent_topics else 1.0
        weights.append(weight)

    if not eligible_topics:
        # Fallback: all topics blocked (shouldn't happen with 50 topics)
        logger.warning(
            "[idea_generator] All topics blocked — "
            "picking random from full list"
        )
        eligible_topics = [t for t in topics if t != last_topic] or topics
        weights = [1.0] * len(eligible_topics)

    selected = random.choices(eligible_topics, weights=weights, k=1)[0]

    logger.info(
        f"[idea_generator] Topic selection:\n"
        f"  Eligible: {len(eligible_topics)}/{len(topics)}\n"
        f"  Recently used: {len(recent_topics)}\n"
        f"  Hard-blocked: '{last_topic}'\n"
        f"  Selected: '{selected}'"
    )

    return selected


def _pick_characters(
    characters: list[dict[str, Any]],
    recent_history: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Pick one confused + one explainer character.

    Avoids same pair as immediately previous run.
    Max 5 re-rolls then proceeds anyway.

    Args:
        characters: Character configs from config.yaml.
        recent_history: Last N history entries.

    Returns:
        Tuple of (confused_char, explainer_char) config dicts.
    """
    confused_chars = [
        c for c in characters if c.get("role") == "confused"
    ]
    explainer_chars = [
        c for c in characters if c.get("role") == "explainer"
    ]

    if not confused_chars or not explainer_chars:
        raise ValueError(
            "Config must have at least 1 confused and "
            "1 explainer character"
        )

    # Get the immediately previous pair
    last_pair: set[str] = set()
    if recent_history:
        last = recent_history[-1]
        last_pair = {
            last.get("character_a", ""),
            last.get("character_b", ""),
        }

    for attempt in range(MAX_PAIR_REROLLS):
        confused = random.choice(confused_chars)
        explainer = random.choice(explainer_chars)
        pair = {confused["name"], explainer["name"]}

        if pair != last_pair or attempt == MAX_PAIR_REROLLS - 1:
            if attempt > 0:
                logger.info(
                    f"[idea_generator] Character pair found "
                    f"after {attempt + 1} attempts"
                )
            break

    logger.info(
        f"[idea_generator] Character selection:\n"
        f"  Confused:  {confused['name']} ({confused['show']})\n"
        f"  Explainer: {explainer['name']} ({explainer['show']})\n"
        f"  Previous pair: {last_pair or 'none'}"
    )

    return confused, explainer


async def generate_idea(
    state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Node 1: Select topic and characters for the next video.

    Args:
        state: Current pipeline state dict.
        config: Loaded config dict.

    Returns:
        Updated state with topic, characters, and roles populated.
    """
    logger.info(
        f"[idea_generator] Starting — "
        f"state keys: {list(state.keys())}"
    )
    start_time = time.perf_counter()

    # --- Check upstream errors ---
    if state.get("error"):
        logger.warning(
            "[idea_generator] Upstream error detected, skipping"
        )
        return state

    # --- Validate state ---
    validation_error = validate_state_for_node(
        state, "idea_generator"
    )
    if validation_error:
        logger.error(f"[idea_generator] {validation_error}")
        return {
            **state,
            "error": validation_error,
            "failed_node": "idea_generator",
        }

    try:
        # --- Load config data ---
        topics = config.get("topics", [])
        characters = config.get("characters", [])

        if not topics:
            raise ValueError("No topics found in config")
        if not characters:
            raise ValueError("No characters found in config")

        # Validate character configs
        for char in characters:
            CharacterConfig(**char)

        # --- Load history ---
        project_root = Path(__file__).resolve().parent.parent.parent
        history_path = project_root / config.get(
            "paths", {}
        ).get("history", "history.json")
        history = _load_history(history_path)
        recent = history[-HISTORY_WINDOW:]

        # --- Pick topic ---
        topic = _pick_topic(topics, recent)

        # --- Pick characters ---
        confused, explainer = _pick_characters(characters, recent)

        # character_a = confused (asks dumb questions)
        # character_b = explainer (answers)
        elapsed = (time.perf_counter() - start_time) * 1000

        result = {
            **state,
            "topic": topic,
            "character_a": confused["name"],
            "character_b": explainer["name"],
            "character_a_role": confused["role"],
            "character_b_role": explainer["role"],
            "character_a_voice": confused["voice"],
            "character_b_voice": explainer["voice"],
            "character_a_image_folder": confused["image_folder"],
            "character_b_image_folder": explainer["image_folder"],
            "trend_source": "fallback",
        }

        logger.info(
            f"[idea_generator] Complete in {elapsed:.0f}ms — wrote:\n"
            f"  topic='{result['topic']}'\n"
            f"  character_a='{result['character_a']}' "
            f"(role={result['character_a_role']})\n"
            f"  character_b='{result['character_b']}' "
            f"(role={result['character_b_role']})\n"
            f"  trend_source='{result['trend_source']}'"
        )

        return result

    except Exception as e:
        logger.error(f"[idea_generator] Failed: {e}")
        return {
            **state,
            "error": f"Idea generation failed: {e}",
            "failed_node": "idea_generator",
        }
