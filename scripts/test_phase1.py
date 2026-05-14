"""Phase 1 end-to-end test runner.

Hardcoded script in → working .mp4 out.
No Gemini, no Pollinations, no LangGraph.

Pipeline:
    1. Load config + run startup checks
    2. Generate placeholder assets (colored rectangles + black bg)
    3. Generate TTS audio for all 8 script lines
    4. Assemble video: subtitles → Pass 1 → Pass 2
    5. Validate final output with ffprobe
"""

import asyncio
import logging
import sys
import io
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path so 'agent' package is importable
# when running from scripts/ subdirectory.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# NOTE: Do NOT set WindowsSelectorEventLoopPolicy here.
# ProactorEventLoop (Windows default) is REQUIRED for
# asyncio.create_subprocess_exec() which we use for all
# FFmpeg calls. SelectorEventLoop throws NotImplementedError
# for subprocess operations on Windows.

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# --- Project imports ---
from agent.config import load_config
from agent.startup_checks import run_all_checks
from agent.state import create_initial_state
from agent.nodes.asset_fetcher import generate_all_audio
from agent.nodes.video_assembler import assemble_video
from agent.utils import find_ffmpeg, run_ffmpeg


# -------------------------------------------------------------------
# Hardcoded test data
# -------------------------------------------------------------------

TEST_SCRIPT: list[dict[str, str]] = [
    {"character": "Nobita", "line": "BRO WHAT EVEN IS AN API"},
    {"character": "Doraemon", "line": "okay so imagine you're ordering food"},
    {"character": "Nobita", "line": "okay and then what bro"},
    {"character": "Doraemon", "line": "the restaurant is the server"},
    {"character": "Nobita", "line": "wait so the waiter is the API"},
    {"character": "Doraemon", "line": "YES. finally. took you long enough"},
    {"character": "Nobita", "line": "this is actually lowkey genius though"},
    {"character": "Doraemon", "line": "it really is not but okay"},
]

VOICE_MAP: dict[str, str] = {
    "Nobita": "en-US-SteffanNeural",
    "Doraemon": "en-GB-ThomasNeural",
}


# -------------------------------------------------------------------
# Placeholder asset generation
# -------------------------------------------------------------------

async def create_placeholder_assets(
    temp_dir: Path,
    bg_dir: Path,
) -> dict[str, str]:
    """Generate placeholder images and background video via FFmpeg.

    Creates:
        - Blue rectangle (540x768) for character A (fallback only)
        - Red rectangle (540x768) for character B (fallback only)
        - Black video (1080x1920, 60s, 30fps) for background

    If real character images exist in assets/characters/{Name}/,
    those are used instead. Run generate_image_library.py first.

    Args:
        temp_dir: Directory for character placeholder images.
        bg_dir: Directory for background video.

    Returns:
        Dict with paths: character_a_image, character_b_image,
        background_video.
    """
    import random

    ffmpeg = find_ffmpeg()
    temp_dir.mkdir(parents=True, exist_ok=True)
    bg_dir.mkdir(parents=True, exist_ok=True)

    project_root = Path(__file__).resolve().parent.parent

    # --- Try to use real character images from library ---
    nobita_dir = project_root / "assets" / "characters" / "Nobita"
    doraemon_dir = project_root / "assets" / "characters" / "Doraemon"

    nobita_images = list(nobita_dir.glob("*.png")) if nobita_dir.exists() else []
    doraemon_images = list(doraemon_dir.glob("*.png")) if doraemon_dir.exists() else []

    if nobita_images and doraemon_images:
        char_a = random.choice(nobita_images)
        char_b = random.choice(doraemon_images)
        logger.info(
            f"Using real character images:\n"
            f"  Nobita:   {char_a.name}\n"
            f"  Doraemon: {char_b.name}"
        )
    else:
        logger.warning(
            "Character image library not found. "
            "Using colored placeholders.\n"
            "Run: python scripts/generate_image_library.py"
        )
        char_a = temp_dir / "char_a.png"
        char_b = temp_dir / "char_b.png"

        if not char_a.exists():
            logger.info("Creating placeholder: Character A (blue)")
            await run_ffmpeg(
                [
                    ffmpeg,
                    "-f", "lavfi",
                    "-i", "color=c=blue:size=400x400:rate=1",
                    "-frames:v", "1",
                    "-y", str(char_a),
                ],
                description="Placeholder char A",
            )

        if not char_b.exists():
            logger.info("Creating placeholder: Character B (red)")
            await run_ffmpeg(
                [
                    ffmpeg,
                    "-f", "lavfi",
                    "-i", "color=c=red:size=400x400:rate=1",
                    "-frames:v", "1",
                    "-y", str(char_b),
                ],
                description="Placeholder char B",
            )

    # Background — black video, 60 seconds
    bg_video = bg_dir / "test_bg.mp4"
    if not bg_video.exists():
        logger.info("Creating placeholder: Background (black, 60s)")
        await run_ffmpeg(
            [
                ffmpeg,
                "-f", "lavfi",
                "-i", "color=c=black:size=1080x1920:rate=30",
                "-t", "60",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-y", str(bg_video),
            ],
            description="Placeholder background",
        )

    logger.info(
        f"Assets ready:\n"
        f"  Char A: {char_a} ({char_a.stat().st_size:,} bytes)\n"
        f"  Char B: {char_b} ({char_b.stat().st_size:,} bytes)\n"
        f"  Background: {bg_video} ({bg_video.stat().st_size:,} bytes)"
    )

    return {
        "character_a_image": str(char_a.resolve()),
        "character_b_image": str(char_b.resolve()),
        "background_video": str(bg_video.resolve()),
    }


# -------------------------------------------------------------------
# Main test runner
# -------------------------------------------------------------------

async def main() -> None:
    """Run the full Phase 1 pipeline end to end."""
    logger.info("=" * 60)
    logger.info("PHASE 1 TEST — Hardcoded Script → Working .mp4")
    logger.info("=" * 60)

    # --- Step 1: Load config ---
    logger.info("\n--- Step 1: Loading config ---")
    config = load_config()

    # --- Step 2: Run startup checks ---
    # Skip env vars and credentials for Phase 1 — those are Phase 5.
    # Only check FFmpeg + disk space.
    logger.info("\n--- Step 2: Startup checks ---")
    from agent.startup_checks import check_ffmpeg_libass, check_disk_space
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

    # --- Step 3: Create placeholder assets ---
    logger.info("\n--- Step 3: Creating placeholder assets ---")
    project_root = Path(__file__).resolve().parent.parent
    temp_dir = project_root / "assets" / "temp"
    bg_dir = project_root / "assets" / "backgrounds"

    assets = await create_placeholder_assets(temp_dir, bg_dir)

    # --- Step 4: Initialize state with hardcoded data ---
    logger.info("\n--- Step 4: Initializing pipeline state ---")
    state = create_initial_state("phase1-test")
    state["topic"] = "What is an API?"
    state["character_a"] = "Nobita"
    state["character_b"] = "Doraemon"
    state["character_a_role"] = "confused"
    state["character_b_role"] = "explainer"
    state["trend_source"] = "fallback"
    state["script"] = TEST_SCRIPT
    state["script_line_count"] = len(TEST_SCRIPT)
    state["character_a_image"] = assets["character_a_image"]
    state["character_b_image"] = assets["character_b_image"]
    state["background_video"] = assets["background_video"]

    logger.info(
        f"  Run ID: {state['run_id']}\n"
        f"  Topic: {state['topic']}\n"
        f"  Characters: {state['character_a']} vs {state['character_b']}\n"
        f"  Script lines: {state['script_line_count']}"
    )

    # --- Step 5: Generate all audio ---
    logger.info("\n--- Step 5: Generating TTS audio ---")
    state = await generate_all_audio(state, VOICE_MAP, temp_dir)

    if state.get("error"):
        logger.error(f"Audio generation failed: {state['error']}")
        return

    logger.info(
        f"  Audio complete: {state['full_audio_duration_ms']:.0f}ms "
        f"({state['full_audio_duration_ms'] / 1000:.1f}s)"
    )

    # --- Step 6: Assemble video ---
    logger.info("\n--- Step 6: Assembling video ---")
    state = await assemble_video(state, config)

    # --- Step 7: Report results ---
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 1 TEST RESULTS")
    logger.info("=" * 60)

    logger.info(f"  Run ID:          {state['run_id']}")
    logger.info(
        f"  Audio duration:  "
        f"{state.get('full_audio_duration_ms', 0):.0f}ms"
    )

    sub_file = state.get("subtitle_file", "")
    if sub_file and Path(sub_file).exists():
        content = Path(sub_file).read_text(encoding="utf-8")
        sub_count = content.count("Dialogue:")
        logger.info(f"  Subtitle entries: {sub_count}")
    else:
        logger.info("  Subtitle entries: N/A")

    logger.info(f"  Intermediate:    {state.get('intermediate_video', 'N/A')}")
    logger.info(f"  Final video:     {state.get('final_video', 'N/A')}")
    logger.info(
        f"  Video duration:  {state.get('video_duration_sec', 0):.1f}s"
    )
    logger.info(f"  Video validated: {state.get('video_validated', False)}")

    if state.get("error"):
        logger.error(f"  ERROR: {state['error']}")
        logger.error(f"  Failed node: {state.get('failed_node', 'unknown')}")
    else:
        final_path = state.get("final_video", "")
        logger.info("")
        logger.info(f"  ✅ Phase 1 complete — video at: {final_path}")
        logger.info(
            "  Open it and verify: audio syncs, subtitles flash, "
            "characters visible, background present"
        )


if __name__ == "__main__":
    asyncio.run(main())
