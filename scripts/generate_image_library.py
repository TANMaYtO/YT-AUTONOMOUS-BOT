"""One-time character image library generator.

Pre-generates 30 character images (5 characters × 6 expressions)
from Pollinations AI so the daily pipeline never depends on
external image generation at runtime.

Usage:
    python scripts/generate_image_library.py

Images are saved to assets/characters/{Name}/01.png → 06.png.
Idempotent — skips files that already exist AND pass validation.

Requires: httpx, rembg, Pillow (in requirements.txt)

NOTE: rembg downloads a ~170MB U2-Net model on first run.
"""

import asyncio
import logging
import sys
import io
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from PIL import Image
from rembg import remove as rembg_remove
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
    before_sleep_log,
)

# Ensure project root is on sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

# 400×400 square PNGs for overlay
IMG_WIDTH = 400
IMG_HEIGHT = 400

# Image format magic bytes
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"  # First 3 bytes of every JPEG

# Minimum acceptable file size (10 KB)
MIN_FILE_SIZE = 10 * 1024

# Rate limiting: seconds between each download
DOWNLOAD_DELAY_SEC = 3

# Characters with fixed seeds for deterministic generation
CHARACTERS: list[dict[str, Any]] = [
    {
        "name": "Nobita",
        "show": "Doraemon",
        "seed": 42,
        "base_prompt": (
            "Nobita Nobi from Doraemon anime, "
            "chibi style illustration, upper body portrait, "
            "transparent background, high quality PNG, "
            "anime art style, cute character design"
        ),
    },
    {
        "name": "Doraemon",
        "show": "Doraemon",
        "seed": 137,
        "base_prompt": (
            "Doraemon the blue robot cat from Doraemon anime, "
            "chibi style illustration, upper body portrait, "
            "transparent background, high quality PNG, "
            "anime art style, cute character design"
        ),
    },
    {
        "name": "LightYagami",
        "show": "Death Note",
        "seed": 256,
        "base_prompt": (
            "Light Yagami from Death Note anime, "
            "chibi style illustration, upper body portrait, "
            "transparent background, high quality PNG, "
            "anime art style, dramatic character design"
        ),
    },
    {
        "name": "Gojo",
        "show": "Jujutsu Kaisen",
        "seed": 512,
        "base_prompt": (
            "Gojo Satoru from Jujutsu Kaisen anime, "
            "chibi style illustration, upper body portrait, "
            "transparent background, high quality PNG, "
            "anime art style, cool character design with blindfold"
        ),
    },
    {
        "name": "Luffy",
        "show": "One Piece",
        "seed": 888,
        "base_prompt": (
            "Monkey D Luffy from One Piece anime, "
            "chibi style illustration, upper body portrait, "
            "transparent background, high quality PNG, "
            "anime art style, energetic character with straw hat"
        ),
    },
]

# 6 expressions per character
EXPRESSIONS: list[dict[str, str]] = [
    {"name": "neutral", "modifier": "neutral calm expression"},
    {"name": "happy", "modifier": "happy smiling excited expression"},
    {"name": "confused", "modifier": "confused puzzled questioning expression"},
    {"name": "shocked", "modifier": "shocked surprised wide eyes expression"},
    {"name": "angry", "modifier": "angry frustrated annoyed expression"},
    {"name": "thinking", "modifier": "thinking contemplating hand on chin expression"},
]


# -------------------------------------------------------------------
# Validation
# -------------------------------------------------------------------

def validate_image(file_path: Path) -> tuple[bool, str]:
    """Validate an image file: magic bytes (PNG or JPEG) + minimum size.

    Pollinations API returns JPEG regardless of prompt content.
    Both PNG and JPEG are valid — FFmpeg handles both identically.

    Args:
        file_path: Path to the image file.

    Returns:
        Tuple of (is_valid, reason).
    """
    if not file_path.exists():
        return False, "file does not exist"

    size = file_path.stat().st_size
    if size < MIN_FILE_SIZE:
        return False, f"too small ({size} bytes, need >={MIN_FILE_SIZE})"

    with open(file_path, "rb") as f:
        header = f.read(8)

    is_png = header[:len(PNG_MAGIC)] == PNG_MAGIC
    is_jpeg = header[:len(JPEG_MAGIC)] == JPEG_MAGIC

    if not (is_png or is_jpeg):
        return False, f"not PNG or JPEG: header={header[:8].hex()}"

    fmt = "PNG" if is_png else "JPEG"
    return True, f"OK {fmt} ({size:,} bytes)"


# -------------------------------------------------------------------
# Download
# -------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type((
        httpx.HTTPError,          # All HTTP errors (status, decode, etc.)
        httpx.TimeoutException,   # All timeouts (connect, read, pool)
        ConnectionError,          # OS-level connection failures
        RuntimeError,             # Our validation failures (corrupt PNG)
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def download_image(
    client: httpx.AsyncClient,
    prompt: str,
    seed: int,
    output_path: Path,
) -> Path:
    """Download a single image from Pollinations AI.

    Args:
        client: Reusable httpx async client.
        prompt: Full text prompt for image generation.
        seed: Fixed seed for deterministic output.
        output_path: Where to save the PNG.

    Returns:
        Path to the saved PNG.

    Raises:
        RuntimeError: If download fails validation.
    """
    encoded_prompt = quote(prompt, safe="")
    url = (
        f"{POLLINATIONS_URL.format(prompt=encoded_prompt)}"
        f"?width={IMG_WIDTH}"
        f"&height={IMG_HEIGHT}"
        f"&seed={seed}"
        f"&nologo=true"
    )

    logger.info(f"  Downloading: seed={seed}")
    logger.debug(f"  URL: {url}")

    response = await client.get(url)
    response.raise_for_status()

    # Verify we got image content, not an error page
    content_type = response.headers.get("content-type", "")
    if "image" not in content_type and len(response.content) < MIN_FILE_SIZE:
        raise RuntimeError(
            f"Response is not an image. "
            f"Content-Type: {content_type}, "
            f"Size: {len(response.content)} bytes"
        )

    # Remove background → transparent RGBA PNG
    logger.info("  Removing background...")
    raw_bytes = response.content
    cleaned_bytes = rembg_remove(raw_bytes)

    if not cleaned_bytes or len(cleaned_bytes) < 1000:
        raise RuntimeError(
            f"rembg returned empty/tiny result: "
            f"{len(cleaned_bytes) if cleaned_bytes else 0} bytes"
        )

    # Save cleaned RGBA PNG to disk
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(cleaned_bytes)

    # Validate
    is_valid, reason = validate_image(output_path)
    if not is_valid:
        # Delete invalid file so next run retries
        output_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Downloaded file failed validation: {reason}"
        )

    return output_path


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

async def main() -> None:
    """Generate the complete character image library."""
    logger.info("=" * 60)
    logger.info("CHARACTER IMAGE LIBRARY GENERATOR")
    logger.info("=" * 60)
    logger.info(
        f"  Characters: {len(CHARACTERS)}\n"
        f"  Expressions: {len(EXPRESSIONS)}\n"
        f"  Total images: {len(CHARACTERS) * len(EXPRESSIONS)}\n"
        f"  Size: {IMG_WIDTH}×{IMG_HEIGHT}px PNG\n"
        f"  Rate limit: {DOWNLOAD_DELAY_SEC}s between downloads"
    )

    project_root = Path(_PROJECT_ROOT)
    chars_dir = project_root / "assets" / "characters"

    # Track results for final table
    results: list[dict[str, str]] = []

    total = len(CHARACTERS) * len(EXPRESSIONS)
    downloaded = 0
    skipped = 0
    failed = 0

    start_time = time.perf_counter()

    async with httpx.AsyncClient(timeout=60.0) as client:
        for char in CHARACTERS:
            char_name = char["name"]
            char_dir = chars_dir / char_name
            char_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"\n--- {char_name} ({char['show']}) ---")

            for expr_idx, expr in enumerate(EXPRESSIONS):
                file_num = expr_idx + 1
                file_path = char_dir / f"{file_num:02d}.png"
                seed = char["seed"] + expr_idx
                full_prompt = f"{char['base_prompt']}, {expr['modifier']}"

                # Check if file already exists and is valid
                is_valid, reason = validate_image(file_path)
                if is_valid:
                    logger.info(
                        f"  [{file_num}/6] {expr['name']:>10} — "
                        f"SKIP (already valid: {reason})"
                    )
                    results.append({
                        "character": char_name,
                        "expression": expr["name"],
                        "file": str(file_path.relative_to(project_root)),
                        "status": "SKIP",
                        "detail": reason,
                    })
                    skipped += 1
                    continue

                # Download
                logger.info(
                    f"  [{file_num}/6] {expr['name']:>10} — "
                    f"generating (seed={seed})..."
                )

                try:
                    await download_image(
                        client=client,
                        prompt=full_prompt,
                        seed=seed,
                        output_path=file_path,
                    )

                    # Re-validate after download
                    is_valid, reason = validate_image(file_path)
                    status = "PASS" if is_valid else "FAIL"
                    if is_valid:
                        downloaded += 1
                    else:
                        failed += 1

                    results.append({
                        "character": char_name,
                        "expression": expr["name"],
                        "file": str(file_path.relative_to(project_root)),
                        "status": status,
                        "detail": reason,
                    })

                    logger.info(
                        f"  [{file_num}/6] {expr['name']:>10} — "
                        f"{status}: {reason}"
                    )

                except Exception as e:
                    failed += 1
                    results.append({
                        "character": char_name,
                        "expression": expr["name"],
                        "file": str(file_path.relative_to(project_root)),
                        "status": "FAIL",
                        "detail": str(e)[:80],
                    })
                    logger.error(
                        f"  [{file_num}/6] {expr['name']:>10} — "
                        f"FAIL: {e}"
                    )

                # Rate limit — wait before next download
                logger.debug(
                    f"  Rate limit: sleeping {DOWNLOAD_DELAY_SEC}s..."
                )
                await asyncio.sleep(DOWNLOAD_DELAY_SEC)

    elapsed = time.perf_counter() - start_time

    # --- Final validation table ---
    logger.info("\n" + "=" * 60)
    logger.info("VALIDATION RESULTS")
    logger.info("=" * 60)
    logger.info(
        f"  {'Character':<15} {'Expression':<12} "
        f"{'Status':<6} {'Detail'}"
    )
    logger.info("-" * 60)

    for r in results:
        icon = "✅" if r["status"] in ("PASS", "SKIP") else "❌"
        logger.info(
            f"  {r['character']:<15} {r['expression']:<12} "
            f"{icon} {r['status']:<6} {r['detail']}"
        )

    logger.info("-" * 60)
    logger.info(
        f"  Total: {total} | "
        f"Downloaded: {downloaded} | "
        f"Skipped: {skipped} | "
        f"Failed: {failed}"
    )
    logger.info(f"  Elapsed: {elapsed:.0f}s")

    if failed > 0:
        logger.warning(
            f"\n  ⚠️  {failed} image(s) failed. "
            f"Re-run this script to retry failed downloads."
        )
    else:
        logger.info(
            "\n  ✅ All images validated. "
            "Character library is ready."
        )


if __name__ == "__main__":
    asyncio.run(main())
