"""Phase 2 end-to-end test runner.

Gemini-generated script → TTS audio → video assembly → metadata.

Pipeline:
    1. Load config + run startup checks + load .env
    2. Run idea_generator (picks topic + characters)
    3. Run script_writer (Gemini Flash generates script)
    4. Interactive pause — user reads script and approves
    5. Pick character images from library
    6. Run asset_fetcher (TTS audio generation)
    7. Run video_assembler (FFmpeg Pass 1 + Pass 2)
    8. Run metadata_generator (Gemini metadata)
    9. Print final results

Usage:
    python scripts/test_phase2.py
"""

import asyncio
import logging
import random
import sys
import io
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# NOTE: ProactorEventLoop (Windows default) is REQUIRED for
# asyncio.create_subprocess_exec() used by FFmpeg calls.
# Do NOT set WindowsSelectorEventLoopPolicy.

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Load .env BEFORE importing agent modules that use env vars
from dotenv import load_dotenv
load_dotenv(Path(_PROJECT_ROOT) / ".env")

# --- Project imports ---
from agent.config import load_config
from agent.startup_checks import check_ffmpeg_libass, check_disk_space
from agent.state import create_initial_state
from agent.nodes.idea_generator import generate_idea
from agent.nodes.script_writer import generate_script
from agent.nodes.asset_fetcher import generate_all_audio
from agent.nodes.video_assembler import assemble_video
from agent.nodes.metadata_generator import generate_metadata


def _pick_character_image(image_folder: str) -> str:
    """Pick a random image from a character's image folder.

    Args:
        image_folder: Path to character image folder
                      (e.g. "assets/characters/Nobita/").

    Returns:
        Absolute path string to a random PNG.
    """
    project_root = Path(__file__).resolve().parent.parent
    folder = project_root / image_folder

    if not folder.exists():
        raise FileNotFoundError(
            f"Character image folder not found: {folder}"
        )

    images = list(folder.glob("*.png"))
    if not images:
        raise FileNotFoundError(
            f"No PNG files in {folder}"
        )

    chosen = random.choice(images)
    return str(chosen.resolve())


async def main() -> None:
    """Run the full Phase 2 pipeline end to end."""
    logger.info("=" * 60)
    logger.info("PHASE 2 TEST — Gemini Script → Working .mp4")
    logger.info("=" * 60)

    # --- Step 1: Load config + checks ---
    logger.info("\n--- Step 1: Loading config ---")
    config = load_config()

    logger.info("\n--- Step 2: Startup checks ---")
    try:
        await check_ffmpeg_libass()
        logger.info("  ✓ FFmpeg + libass — PASS")
    except RuntimeError as e:
        logger.error(f"  ✗ FFmpeg + libass — FAIL: {e}")
        return

    check_disk_space(
        config.get("health_checks", {}).get("min_free_disk_gb", 2)
    )
    logger.info("  ✓ Disk space — checked")

    import os
    if not os.getenv("GEMINI_API_KEY"):
        logger.error(
            "  ✗ GEMINI_API_KEY not set. "
            "Add it to .env file."
        )
        return
    logger.info("  ✓ GEMINI_API_KEY — set")

    # --- Step 3: Initialize state ---
    logger.info("\n--- Step 3: Initializing state ---")
    state = create_initial_state("phase2-test")

    # --- Step 4: Run idea_generator (Node 1) ---
    logger.info("\n--- Step 4: Idea Generator (Node 1) ---")
    state = await generate_idea(state, config)

    if state.get("error"):
        logger.error(f"Idea generation failed: {state['error']}")
        return

    logger.info(
        f"\n  📋 Selected:\n"
        f"     Topic:    {state['topic']}\n"
        f"     Char A:   {state['character_a']} "
        f"({state['character_a_role']})\n"
        f"     Char B:   {state['character_b']} "
        f"({state['character_b_role']})\n"
        f"     Voices:   {state['character_a_voice']} / "
        f"{state['character_b_voice']}"
    )

    # --- Step 5: Run script_writer (Node 2) ---
    logger.info("\n--- Step 5: Script Writer (Node 2) ---")
    state = await generate_script(state, config)

    if state.get("error"):
        logger.error(f"Script generation failed: {state['error']}")
        return

    # --- Print the generated script ---
    logger.info("\n" + "=" * 60)
    logger.info("GENERATED SCRIPT")
    logger.info("=" * 60)
    logger.info(
        f"  Topic: {state['topic']}\n"
        f"  Lines: {state['script_line_count']}\n"
        f"  Est. duration: "
        f"{state['script_duration_estimate_sec']:.1f}s"
    )
    logger.info("-" * 60)

    for i, line in enumerate(state["script"]):
        char = line["character"]
        text = line["line"]
        logger.info(f"  [{i}] {char}: {text}")

    logger.info("-" * 60)

    # --- Interactive pause ---
    print("\n  Continue with this script? (y to proceed): ", end="")
    answer = input().strip().lower()
    if answer != "y":
        logger.info("Aborted by user.")
        return

    # --- Step 6: Pick character images ---
    logger.info("\n--- Step 6: Picking character images ---")
    try:
        char_a_image = _pick_character_image(
            state["character_a_image_folder"]
        )
        char_b_image = _pick_character_image(
            state["character_b_image_folder"]
        )
    except FileNotFoundError as e:
        logger.error(f"Image selection failed: {e}")
        return

    state["character_a_image"] = char_a_image
    state["character_b_image"] = char_b_image

    logger.info(
        f"  Char A image: {Path(char_a_image).name}\n"
        f"  Char B image: {Path(char_b_image).name}"
    )

    # --- Step 7: Set up background video ---
    project_root = Path(__file__).resolve().parent.parent
    bg_dir = project_root / "assets" / "backgrounds"
    bg_video = bg_dir / "test_bg.mp4"

    if not bg_video.exists():
        logger.error(
            f"Background video not found: {bg_video}\n"
            "Run test_phase1.py first to create it."
        )
        return

    state["background_video"] = str(bg_video.resolve())

    # --- Step 8: Generate TTS audio (Node 4) ---
    logger.info("\n--- Step 7: Asset Fetcher (Node 4) — TTS ---")
    temp_dir = project_root / "assets" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    voice_map = {
        state["character_a"]: state["character_a_voice"],
        state["character_b"]: state["character_b_voice"],
    }

    state = await generate_all_audio(state, voice_map, temp_dir)

    if state.get("error"):
        logger.error(f"Audio generation failed: {state['error']}")
        return

    logger.info(
        f"  Audio complete: "
        f"{state['full_audio_duration_ms']:.0f}ms "
        f"({state['full_audio_duration_ms'] / 1000:.1f}s)"
    )

    # --- Step 9: Assemble video (Node 5) ---
    logger.info("\n--- Step 8: Video Assembler (Node 5) ---")
    state = await assemble_video(state, config)

    if state.get("error"):
        logger.error(f"Video assembly failed: {state['error']}")
        return

    # --- Step 10: Generate metadata (Node 6) ---
    logger.info("\n--- Step 9: Metadata Generator (Node 6) ---")
    state = await generate_metadata(state, config)

    if state.get("error"):
        logger.error(
            f"Metadata generation failed: {state['error']}"
        )
        # Non-fatal — video is already done, log and continue

    # --- Step 11: Report results ---
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2 TEST RESULTS")
    logger.info("=" * 60)

    logger.info(f"  Run ID:          {state['run_id']}")
    logger.info(f"  Topic:           {state['topic']}")
    logger.info(
        f"  Characters:      {state['character_a']} vs "
        f"{state['character_b']}"
    )
    logger.info(
        f"  Script lines:    {state.get('script_line_count', 0)}"
    )
    logger.info(
        f"  Audio duration:  "
        f"{state.get('full_audio_duration_ms', 0):.0f}ms"
    )
    logger.info(
        f"  Video duration:  "
        f"{state.get('video_duration_sec', 0):.1f}s"
    )
    logger.info(
        f"  Video validated: "
        f"{state.get('video_validated', False)}"
    )
    logger.info(f"  Final video:     {state.get('final_video', 'N/A')}")

    # Metadata
    logger.info("")
    logger.info("  --- METADATA ---")
    logger.info(f"  Title:       {state.get('title', 'N/A')}")
    logger.info(f"  Description: {state.get('description', 'N/A')}")
    logger.info(f"  Hashtags:    {state.get('hashtags', [])}")
    logger.info(f"  Tags:        {state.get('tags', [])}")

    if state.get("error"):
        logger.error(f"\n  ERROR: {state['error']}")
        logger.error(
            f"  Failed node: {state.get('failed_node', 'unknown')}"
        )
    else:
        final_path = state.get("final_video", "")
        logger.info("")
        logger.info(
            f"  ✅ Phase 2 complete — video at: {final_path}"
        )


if __name__ == "__main__":
    asyncio.run(main())
