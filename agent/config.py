"""Configuration loader for the YT Shorts Agent.

Loads config.yaml, validates all character entries against
CharacterConfig Pydantic model, and verifies all path entries
exist as directories. Hard-fails at startup with clear error
messages — never silently mid-pipeline.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from agent.models import CharacterConfig

logger = logging.getLogger(__name__)

# Root of the project — config.yaml lives here
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Sections that MUST exist in config.yaml
REQUIRED_SECTIONS: list[str] = [
    "pipeline",
    "characters",
    "topics",
    "video",
    "subtitle",
    "paths",
    "ffmpeg",
    "health_checks",
]


def load_config(
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Load and validate config.yaml.

    Args:
        config_path: Optional custom path to config file.
                     Defaults to PROJECT_ROOT / config.yaml.

    Returns:
        Validated config dict with all sections populated.

    Raises:
        FileNotFoundError: If config.yaml does not exist.
        ValueError: If any required section is missing,
                    any character entry is invalid, or
                    any path directory does not exist.
    """
    path = config_path or (PROJECT_ROOT / "config.yaml")

    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            f"Run /init-config to generate a fresh config.yaml."
        )

    raw = path.read_text(encoding="utf-8")
    config: dict[str, Any] = yaml.safe_load(raw)

    if config is None:
        raise ValueError(f"Config file is empty: {path}")

    _validate_required_sections(config)
    _validate_characters(config["characters"])
    _validate_topics(config["topics"])
    _validate_paths(config["paths"])

    char_count = len(config["characters"])
    topic_count = len(config["topics"])
    slot_count = len(config["pipeline"]["upload_slots"])

    logger.info(
        f"Config loaded: {char_count} characters, "
        f"{topic_count} topics, {slot_count} upload slots"
    )

    return config


def _validate_required_sections(config: dict[str, Any]) -> None:
    """Verify all required top-level sections exist in config."""
    missing = [s for s in REQUIRED_SECTIONS if s not in config]
    if missing:
        raise ValueError(
            f"Config missing required sections: {', '.join(missing)}\n"
            f"Required: {REQUIRED_SECTIONS}"
        )


def _validate_characters(
    characters: list[dict[str, Any]],
) -> None:
    """Validate every character entry against CharacterConfig model."""
    if not characters:
        raise ValueError(
            "Config 'characters' section is empty. "
            "At least 2 characters are required."
        )

    if len(characters) < 2:
        raise ValueError(
            f"Config has {len(characters)} character(s). "
            f"At least 2 are required (one explainer, one confused)."
        )

    errors: list[str] = []
    roles_found: set[str] = set()

    for i, char_data in enumerate(characters):
        try:
            char = CharacterConfig(**char_data)
            roles_found.add(char.role)
            logger.debug(
                f"  Character {i + 1}: {char.name} "
                f"({char.show}) role={char.role}"
            )
        except ValidationError as e:
            errors.append(
                f"Character entry {i + 1}: {e.error_count()} error(s)\n"
                f"  Data: {char_data}\n"
                f"  Errors: {e}"
            )

    if errors:
        joined = "\n".join(errors)
        raise ValueError(
            f"Invalid character entries in config:\n{joined}"
        )

    if "explainer" not in roles_found:
        raise ValueError(
            "Config has no character with role='explainer'. "
            "At least one explainer is required."
        )

    if "confused" not in roles_found:
        raise ValueError(
            "Config has no character with role='confused'. "
            "At least one confused character is required."
        )


def _validate_topics(topics: list[str]) -> None:
    """Verify topics list is non-empty and contains strings."""
    if not topics:
        raise ValueError(
            "Config 'topics' section is empty. "
            "At least 1 topic is required."
        )

    empty_indices = [
        i + 1 for i, t in enumerate(topics)
        if not isinstance(t, str) or not t.strip()
    ]

    if empty_indices:
        raise ValueError(
            f"Config has empty/invalid topics at positions: "
            f"{empty_indices}"
        )


def _validate_paths(paths: dict[str, str]) -> None:
    """Verify all directory paths exist. File paths are skipped."""
    required_dirs = [
        "backgrounds",
        "music",
        "temp",
        "output",
        "archive",
        "logs",
        "characters",
        "credentials",
    ]

    missing: list[str] = []

    for key in required_dirs:
        if key not in paths:
            missing.append(f"'{key}' key missing from paths section")
            continue

        dir_path = PROJECT_ROOT / paths[key]
        if not dir_path.is_dir():
            missing.append(
                f"'{key}' directory does not exist: {dir_path}"
            )

    if missing:
        joined = "\n  ".join(missing)
        raise ValueError(
            f"Config path validation failed:\n  {joined}\n"
            f"Run /setup-env to create missing directories."
        )
