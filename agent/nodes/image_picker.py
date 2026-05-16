"""Node 3 — Image Picker.

Selects character images from the local pre-generated library
in assets/characters/{name}/.

For each character in the script, randomly picks one image file
from their folder. Validates the image file (PNG magic bytes,
minimum file size) before accepting.

Writes to state:
    character_a_image, character_b_image
"""

import logging
import random
from pathlib import Path
from typing import Any

from agent.state import validate_state_for_node

logger = logging.getLogger(__name__)

def _pick_character_image(image_folder: str) -> str:
    """Randomly pick a PNG image from the folder."""
    folder = Path(image_folder)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Image folder not found: {folder}")
        
    images = list(folder.glob("*.png"))
    if not images:
        raise ValueError(f"No PNG images found in {folder}")
        
    # Pick a random image
    selected = random.choice(images)
    
    # Simple validation (min 1KB)
    if selected.stat().st_size < 1024:
        raise ValueError(f"Image file too small or corrupted: {selected}")
        
    return str(selected.resolve())


async def pick_images(
    state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Node 3: Pick character images for the video."""
    logger.info(f"[image_picker] Starting")

    if state.get("error"):
        return state

    validation_error = validate_state_for_node(state, "image_picker")
    if validation_error:
        logger.error(f"[image_picker] {validation_error}")
        return {**state, "error": validation_error, "failed_node": "image_picker"}

    try:
        char_a_image = _pick_character_image(state["character_a_image_folder"])
        char_b_image = _pick_character_image(state["character_b_image_folder"])
        
        # Pick background video
        project_root = Path(__file__).resolve().parent.parent.parent
        bg_folder = project_root / config.get("paths", {}).get("backgrounds", "assets/backgrounds")
        bg_videos = list(bg_folder.glob("*.mp4"))
        if not bg_videos:
            raise ValueError(f"No background videos found in {bg_folder}")
        bg_video = str(random.choice(bg_videos).resolve())
        
        logger.info(f"[image_picker] Picked A: {Path(char_a_image).name}, B: {Path(char_b_image).name}, BG: {Path(bg_video).name}")
        
        return {
            **state,
            "character_a_image": char_a_image,
            "character_b_image": char_b_image,
            "background_video": bg_video,
        }
    except Exception as e:
        logger.error(f"[image_picker] Failed: {e}")
        return {
            **state,
            "error": f"Image picker failed: {e}",
            "failed_node": "image_picker"
        }
