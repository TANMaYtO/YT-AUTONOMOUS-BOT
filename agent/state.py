"""LangGraph state schema for the YT Shorts pipeline.

This is the single source of truth for every field that flows through
the pipeline. Every node reads from and writes back to this state dict.

Field groups are annotated by which node is responsible for writing them.
All fields start as None (or empty) and are populated as the pipeline
progresses through nodes.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Nested structure types (used inside the state dict)
# ---------------------------------------------------------------------------
# These mirror the Pydantic models in models.py but as plain dicts/TypedDicts
# because LangGraph state must be serialisable and uses TypedDict, not Pydantic.
# Validation happens at node boundaries via models.py BEFORE writing to state.
# ---------------------------------------------------------------------------


class WordTimestampDict(TypedDict):
    """A word with timing data from edge-tts."""

    word: str
    offset_ms: float
    duration_ms: float


class AudioSegmentDict(TypedDict):
    """Audio file metadata for a single script line."""

    path: str
    duration_ms: float
    character: str
    line_index: int
    word_timestamps: list[WordTimestampDict]


class ScriptLineDict(TypedDict):
    """A single dialogue line in the script."""

    character: str
    line: str


# ---------------------------------------------------------------------------
# Main pipeline state — the spine of the entire system
# ---------------------------------------------------------------------------


class VideoState(TypedDict, total=False):
    """Complete LangGraph state for one pipeline run.

    Every node receives this dict and returns it with updates.
    Fields are grouped by the node that writes them.

    Using total=False so nodes can return partial updates —
    LangGraph merges them into the existing state automatically.
    """

    # ------------------------------------------------------------------
    # Pipeline metadata (set at initialisation, read by all nodes)
    # ------------------------------------------------------------------
    run_id: str                  # UUID4 — unique ID for this pipeline run
    created_at: str              # ISO 8601 — when the pipeline started

    # ------------------------------------------------------------------
    # Node 1 — Idea Generator (writes)
    # ------------------------------------------------------------------
    topic: str                   # The selected topic (e.g. "recursion")
    character_a: str             # Name of character A (the explainer)
    character_b: str             # Name of character B (the confused one)
    character_a_role: str        # "explainer"
    character_b_role: str        # "confused"
    character_a_voice: str       # edge-tts voice ID for character A
    character_b_voice: str       # edge-tts voice ID for character B
    character_a_image_folder: str  # Path to character A image folder
    character_b_image_folder: str  # Path to character B image folder
    trend_source: str            # "pytrends" | "fallback"

    # ------------------------------------------------------------------
    # Node 2 — Script Writer (writes)
    # Reads: topic, character_a, character_b, roles
    # ------------------------------------------------------------------
    script: list[ScriptLineDict]         # Validated dialogue lines
    script_line_count: int               # Number of lines in script
    script_duration_estimate_sec: float  # Rough estimate in seconds

    # ------------------------------------------------------------------
    # Node 3 — Image Picker (writes)
    # Reads: character_a, character_b
    # ------------------------------------------------------------------
    character_a_image: str       # Absolute path to character A image
    character_b_image: str       # Absolute path to character B image

    # ------------------------------------------------------------------
    # Node 4 — Asset Fetcher (writes)
    # Reads: script, character_a_image, character_b_image
    # ------------------------------------------------------------------
    audio_segments: list[AudioSegmentDict]  # One per script line, in order
    background_video: str                   # Path to background gameplay clip
    full_audio_path: str                    # Path to concatenated WAV
    full_audio_duration_ms: float           # Total audio duration in ms

    # ------------------------------------------------------------------
    # Node 5 — Video Assembler (writes)
    # Reads: audio_segments, full_audio_path, character_a_image,
    #        character_b_image, background_video, script
    # ------------------------------------------------------------------
    subtitle_file: str           # Path to generated .ass file
    intermediate_video: str      # Path to Pass 1 output (before subs)
    final_video: str             # Path to final .mp4 (after Pass 2)
    video_duration_sec: float    # Actual duration from ffprobe
    video_validated: bool        # True if ffprobe confirms valid output

    # ------------------------------------------------------------------
    # Node 6 — Metadata Generator (writes)
    # Reads: topic, character_a, character_b, script
    # ------------------------------------------------------------------
    title: str                   # YouTube title (under 60 chars + emojis)
    description: str             # 2-3 sentence description
    hashtags: list[str]          # e.g. ["#Shorts", "#Python", "#Coding"]
    tags: list[str]              # YouTube tags (different from hashtags)

    # ------------------------------------------------------------------
    # Node 7 — Queue Manager (writes)
    # Reads: final_video, title, description, hashtags, tags
    # ------------------------------------------------------------------
    queue_entry_id: str          # UUID of the queue.json entry
    scheduled_upload_time: str   # ISO 8601 datetime for upload

    # ------------------------------------------------------------------
    # Error handling (can be set by ANY node)
    # ------------------------------------------------------------------
    error: str | None            # Error message if a node failed
    failed_node: str | None      # Name of the node that failed


# ---------------------------------------------------------------------------
# State initialisation helper
# ---------------------------------------------------------------------------


def create_initial_state(run_id: str | None = None) -> dict[str, Any]:
    """Create a fresh pipeline state with metadata pre-filled.

    Args:
        run_id: Optional custom run ID. Auto-generated UUID4 if not provided.

    Returns:
        A dict matching the VideoState schema with all fields set to defaults.
    """
    return {
        # Pipeline metadata
        "run_id": run_id or str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        # Node 1
        "topic": "",
        "character_a": "",
        "character_b": "",
        "character_a_role": "",
        "character_b_role": "",
        "character_a_voice": "",
        "character_b_voice": "",
        "character_a_image_folder": "",
        "character_b_image_folder": "",
        "trend_source": "",
        # Node 2
        "script": [],
        "script_line_count": 0,
        "script_duration_estimate_sec": 0.0,
        # Node 3
        "character_a_image": "",
        "character_b_image": "",
        # Node 4
        "audio_segments": [],
        "background_video": "",
        "full_audio_path": "",
        "full_audio_duration_ms": 0.0,
        # Node 5
        "subtitle_file": "",
        "intermediate_video": "",
        "final_video": "",
        "video_duration_sec": 0.0,
        "video_validated": False,
        # Node 6
        "title": "",
        "description": "",
        "hashtags": [],
        "tags": [],
        # Node 7
        "queue_entry_id": "",
        "scheduled_upload_time": "",
        # Error handling
        "error": None,
        "failed_node": None,
    }


# ---------------------------------------------------------------------------
# State validation helpers (used at node boundaries)
# ---------------------------------------------------------------------------

# Required state keys that each node needs from upstream.
# If ANY key is missing or empty, the node should refuse to run.

NODE_REQUIRED_KEYS: dict[str, list[str]] = {
    "idea_generator": [],  # First node — needs nothing
    "script_writer": ["topic", "character_a", "character_b"],
    "image_picker": ["character_a", "character_b"],
    "asset_fetcher": [
        "script",
        "character_a_image",
        "character_b_image",
    ],
    "video_assembler": [
        "audio_segments",
        "full_audio_path",
        "character_a_image",
        "character_b_image",
        "background_video",
    ],
    "metadata_generator": [
        "topic",
        "character_a",
        "character_b",
        "script",
    ],
    "queue_manager": [
        "final_video",
        "title",
        "description",
        "hashtags",
    ],
}

# State keys that must be truthy (True) for a node to run.
# Separate from NODE_REQUIRED_KEYS to keep the boolean gate pattern
# extensible without special-casing field names in validation logic.

NODE_REQUIRED_TRUE: dict[str, list[str]] = {
    "queue_manager": ["video_validated"],
}


def validate_state_for_node(
    state: dict[str, Any], node_name: str
) -> str | None:
    """Check that all required upstream keys are present and non-empty.

    Args:
        state: The current pipeline state dict.
        node_name: The name of the node about to run.

    Returns:
        An error message string if validation fails, None if all good.
    """
    required = NODE_REQUIRED_KEYS.get(node_name, [])
    missing: list[str] = []

    for key in required:
        value = state.get(key)
        if value is None:
            missing.append(f"{key} is None")
        elif isinstance(value, str) and not value:
            missing.append(f"{key} is empty string")
        elif isinstance(value, list) and len(value) == 0:
            missing.append(f"{key} is empty list")

    # Check boolean gates — fields that must be True, not just present
    for key in NODE_REQUIRED_TRUE.get(node_name, []):
        if not state.get(key):
            missing.append(f"{key} is not True")

    if missing:
        return (
            f"[{node_name}] Missing required upstream state: "
            + ", ".join(missing)
        )
    return None
