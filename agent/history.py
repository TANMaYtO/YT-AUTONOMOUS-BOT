import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = PROJECT_ROOT / "history.json"

def load_history(max_entries: int = 30) -> list[dict]:
    """Load last N entries from history.json.
    Returns empty list if file doesn't exist.
    """
    if not HISTORY_PATH.exists():
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data[-max_entries:] if data else []
    except json.JSONDecodeError:
        return []

def save_history_entry(entry: dict) -> None:
    """Append a new entry to history.json.
    Keeps only the last 200 entries total (trim older ones).
    Uses atomic write-then-rename pattern.
    """
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
        
    data.append(entry)
    
    # Trim to 200
    if len(data) > 200:
        data = data[-200:]
        
    temp_file = HISTORY_PATH.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_file, HISTORY_PATH)

def is_duplicate(
    topic: str,
    character_a: str,
    character_b: str,
    last_n: int = 30
) -> bool:
    """Check if this exact combo appeared in last N runs.
    Checks: same topic AND same character pair
    Character pair is order-independent.
    """
    history = load_history(last_n)
    pair_set = {character_a, character_b}
    
    for entry in history:
        if entry.get("topic") == topic:
            entry_pair = {entry.get("character_a"), entry.get("character_b")}
            if pair_set == entry_pair:
                return True
    return False

def get_used_topics(last_n: int = 30) -> list[str]:
    """Return list of topics used in last N runs.
    Used by idea_generator for weighted selection.
    """
    history = load_history(last_n)
    return [entry["topic"] for entry in history if "topic" in entry]

def get_used_pairs(last_n: int = 30) -> list[tuple]:
    """Return list of (char_a, char_b) pairs used in last N runs.
    Used by idea_generator for weighted character selection.
    """
    history = load_history(last_n)
    pairs = []
    for entry in history:
        a = entry.get("character_a")
        b = entry.get("character_b")
        if a and b:
            pairs.append(tuple(sorted([a, b])))
    return pairs
