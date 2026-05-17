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

import itertools
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
    pass # Replaced by integrated logic in generate_idea


def _pick_characters(
    characters: list[dict[str, Any]],
    recent_history: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    pass # Replaced by integrated logic in generate_idea


async def generate_idea(
    state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Node 1: Select topic and characters for the next video."""
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
        from agent.trends import get_trending_topics
        from agent.history import is_duplicate, get_used_topics, get_used_pairs
        import itertools
        import random
        config_topics = config.get("topics", [])
        trending_topics = await get_trending_topics(config, config_topics)
        trend_source = "pytrends" if trending_topics else "fallback"
        
        all_topics = trending_topics + config_topics
        used_topics = get_used_topics(30)
        
        # Weighted topic selection
        topic_weights = []
        for t in all_topics:
            if t in trending_topics:
                topic_weights.append(1.5)
            elif t in used_topics:
                topic_weights.append(0.1)
            else:
                topic_weights.append(1.0)
                
        characters = config["characters"]
        char_names = [c["name"] for c in characters]
        
        # Weighted character selection
        all_pairs = list(itertools.combinations(char_names, 2))
        used_pairs = get_used_pairs(30)
        
        pair_weights = []
        for p in all_pairs:
            if tuple(sorted(p)) in used_pairs:
                pair_weights.append(0.1)
            else:
                pair_weights.append(1.0)
                
        selected_topic = None
        char_a, char_b = None, None
        
        for attempt in range(6):
            selected_topic = random.choices(all_topics, weights=topic_weights, k=1)[0]
            selected_pair = random.choices(all_pairs, weights=pair_weights, k=1)[0]
            char_a, char_b = selected_pair
            
            # Randomize order
            if random.random() > 0.5:
                char_a, char_b = char_b, char_a
                
            if not is_duplicate(selected_topic, char_a, char_b):
                break
                
            if attempt == 5:
                logger.warning("Could not avoid duplicate after 5 attempts — proceeding")

        # Match the selected names back to their config dicts
        char_a_data = next(c for c in characters if c["name"] == char_a)
        char_b_data = next(c for c in characters if c["name"] == char_b)
        
        elapsed = (time.perf_counter() - start_time) * 1000

        result = {
            **state,
            "topic": selected_topic,
            "character_a": char_a,
            "character_b": char_b,
            "character_a_role": char_a_data["role"],
            "character_b_role": char_b_data["role"],
            "character_a_voice": char_a_data["voice"],
            "character_b_voice": char_b_data["voice"],
            "character_a_image_folder": char_a_data["image_folder"],
            "character_b_image_folder": char_b_data["image_folder"],
            "trend_source": trend_source,
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
