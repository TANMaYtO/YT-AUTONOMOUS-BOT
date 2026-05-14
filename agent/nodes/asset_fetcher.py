"""Node 4 — Asset Fetcher (TTS audio generation).

Generates all audio assets needed for video assembly using edge-tts.

!! CRITICAL WARNING — edge-tts 7.x WordBoundary Bug !!
edge-tts 7.x defaults boundary parameter to "SentenceBoundary".
This gives ONLY sentence-level timestamps — one timestamp per
entire line. Subtitle timing will be completely wrong if you
don't pass boundary="WordBoundary" explicitly.

Verified 2026-04-25 on edge-tts 7.2.8.
!! END WARNING !!

Pipeline:
    1. For each script line: edge-tts → MP3 → immediate WAV convert
    2. Collect word-boundary timestamps from each line
    3. Calculate cumulative offsets across all lines
    4. Concatenate all WAVs into full_audio.wav via FFmpeg concat
    5. Validate full_audio.wav with ffprobe

All edge-tts calls wrapped in tenacity (3 attempts, exp backoff).
WAV used for all intermediate audio — never accumulate MP3s.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import edge_tts
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from agent.models import AudioSegment, WordTimestamp
from agent.state import validate_state_for_node
from agent.utils import (
    find_ffmpeg,
    probe_media,
    run_ffmpeg,
)

logger = logging.getLogger(__name__)

# edge-tts returns offsets in 100-nanosecond ticks (Microsoft units).
# Divide by 10_000 to convert to milliseconds.
_TICKS_TO_MS: float = 10_000.0


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception_type((
        ConnectionError,
        TimeoutError,
        OSError,
        RuntimeError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def generate_audio_for_line(
    line_text: str,
    voice: str,
    output_dir: Path,
    line_index: int,
) -> AudioSegment:
    """Generate TTS audio + word timestamps for a single script line.

    Args:
        line_text: The dialogue text to synthesise.
        voice: edge-tts voice ID (e.g. 'en-US-GuyNeural').
        output_dir: Directory to save audio files.
        line_index: Index of this line in the script (for filenames).

    Returns:
        Validated AudioSegment Pydantic model.

    Raises:
        RuntimeError: If audio generation or WAV conversion fails.
    """
    start_time = time.perf_counter()
    logger.info(
        f"[asset_fetcher] Generating audio for line {line_index}: "
        f"'{line_text[:50]}...' voice={voice}"
    )

    mp3_path = output_dir / f"line_{line_index:02d}.mp3"
    wav_path = output_dir / f"line_{line_index:02d}.wav"

    # --- Generate audio with edge-tts ---

    # CRITICAL: must pass boundary="WordBoundary" explicitly.
    # edge-tts 7.x defaults to SentenceBoundary which gives
    # line-level timestamps only — subtitle timing will be wrong.
    # Verified 2026-04-25 on edge-tts 7.2.8.
    comm = edge_tts.Communicate(
        line_text, voice, boundary="WordBoundary"
    )

    audio_data = bytearray()
    word_boundaries: list[dict[str, float | str]] = []

    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio_data.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            word_boundaries.append({
                "word": chunk.get("text", ""),
                "offset_ms": chunk.get("offset", 0) / _TICKS_TO_MS,
                "duration_ms": chunk.get("duration", 0) / _TICKS_TO_MS,
            })

    if not audio_data:
        raise RuntimeError(
            f"edge-tts returned no audio for line {line_index}: "
            f"'{line_text}'"
        )

    # Save raw MP3
    mp3_path.write_bytes(audio_data)
    logger.debug(
        f"[asset_fetcher] Line {line_index}: MP3 saved "
        f"({len(audio_data)} bytes), {len(word_boundaries)} word boundaries"
    )

    # --- Convert MP3 → WAV immediately (avoid frame-boundary gaps) ---
    ffmpeg = find_ffmpeg()
    await run_ffmpeg(
        [
            ffmpeg, "-i", str(mp3_path),
            "-acodec", "pcm_s16le",
            "-ar", "24000",
            "-ac", "1",
            "-y", str(wav_path),
        ],
        description=f"MP3→WAV line {line_index}",
    )

    # Delete MP3 — WAV is our intermediate format
    mp3_path.unlink(missing_ok=True)

    # --- Validate WAV output ---
    if not wav_path.exists():
        raise RuntimeError(
            f"WAV file not created for line {line_index}: {wav_path}"
        )

    wav_size = wav_path.stat().st_size
    if wav_size == 0:
        raise RuntimeError(
            f"WAV file is 0 bytes for line {line_index}: {wav_path}"
        )

    # Get duration from ffprobe
    probe = await probe_media(wav_path)
    duration_ms = float(probe["format"]["duration"]) * 1000.0

    # --- Build validated Pydantic model ---
    word_ts = [
        WordTimestamp(
            word=str(wb["word"]),
            offset_ms=float(wb["offset_ms"]),
            duration_ms=float(wb["duration_ms"]),
        )
        for wb in word_boundaries
    ]

    segment = AudioSegment(
        path=str(wav_path.resolve()),
        duration_ms=duration_ms,
        character="",  # Filled by caller
        line_index=line_index,
        word_timestamps=word_ts,
    )

    elapsed = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"[asset_fetcher] Line {line_index} complete: "
        f"{duration_ms:.0f}ms audio, {len(word_ts)} words, "
        f"took {elapsed:.0f}ms"
    )

    return segment


async def generate_all_audio(
    state: dict[str, Any],
    voice_map: dict[str, str],
    output_dir: Path,
) -> dict[str, Any]:
    """Generate TTS audio for all script lines and concatenate.

    Args:
        state: Current pipeline state (must have 'script' populated).
        voice_map: Maps character name → edge-tts voice ID.
        output_dir: Directory for all audio files.

    Returns:
        Updated state dict with audio_segments, full_audio_path,
        and full_audio_duration_ms populated.
    """
    logger.info("[asset_fetcher] Starting audio generation")
    start_time = time.perf_counter()

    # --- Validate upstream state ---
    if state.get("error"):
        logger.warning("[asset_fetcher] Upstream error detected, skipping")
        return state

    script = state.get("script", [])
    if not script:
        return {
            **state,
            "error": "No script lines in state",
            "failed_node": "asset_fetcher",
        }

    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Generate audio for each line ---
    segments: list[AudioSegment] = []

    for i, line_data in enumerate(script):
        character = line_data["character"]
        text = line_data["line"]
        voice = voice_map.get(character, "en-US-GuyNeural")

        try:
            segment = await generate_audio_for_line(
                line_text=text,
                voice=voice,
                output_dir=output_dir,
                line_index=i,
            )
            # Fill in the character name
            segment = segment.model_copy(update={"character": character})
            segments.append(segment)

        except Exception as e:
            logger.error(
                f"[asset_fetcher] Failed on line {i}: {e}"
            )
            return {
                **state,
                "error": f"Audio generation failed on line {i}: {e}",
                "failed_node": "asset_fetcher",
            }

    # --- Calculate cumulative offsets across lines ---
    # Each line's timestamps are relative to that line's start.
    # We need absolute offsets for the concatenated audio.
    cumulative_offset_ms: float = 0.0
    adjusted_segments: list[dict[str, Any]] = []

    for seg in segments:
        adjusted_words = []
        for wt in seg.word_timestamps:
            adjusted_words.append({
                "word": wt.word,
                "offset_ms": wt.offset_ms + cumulative_offset_ms,
                "duration_ms": wt.duration_ms,
            })

        adjusted_segments.append({
            "path": seg.path,
            "duration_ms": seg.duration_ms,
            "character": seg.character,
            "line_index": seg.line_index,
            "word_timestamps": adjusted_words,
        })

        cumulative_offset_ms += seg.duration_ms

    logger.info(
        f"[asset_fetcher] All {len(segments)} lines generated. "
        f"Total duration: {cumulative_offset_ms:.0f}ms "
        f"({cumulative_offset_ms / 1000:.1f}s)"
    )

    # --- Concatenate WAVs via FFmpeg concat demuxer ---
    full_audio_path = output_dir / "full_audio.wav"
    filelist_path = output_dir / "filelist.txt"

    # Write concat file list
    lines = []
    for seg in segments:
        # Use forward slashes and quote the path
        safe_path = str(Path(seg.path).name)
        lines.append(f"file '{safe_path}'")

    filelist_path.write_text("\n".join(lines), encoding="utf-8")

    ffmpeg = find_ffmpeg()
    await run_ffmpeg(
        [
            ffmpeg,
            "-f", "concat",
            "-safe", "0",
            "-i", str(filelist_path),
            "-c", "copy",
            "-y", str(full_audio_path),
        ],
        description="WAV concatenation",
    )

    # --- Validate concatenated audio ---
    if not full_audio_path.exists():
        return {
            **state,
            "error": "full_audio.wav was not created",
            "failed_node": "asset_fetcher",
        }

    probe = await probe_media(full_audio_path)
    full_duration_sec = float(probe["format"]["duration"])
    full_duration_ms = full_duration_sec * 1000.0

    stream_types = [
        s.get("codec_type") for s in probe.get("streams", [])
    ]
    if "audio" not in stream_types:
        return {
            **state,
            "error": "full_audio.wav has no audio stream",
            "failed_node": "asset_fetcher",
        }

    elapsed = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"[asset_fetcher] Audio pipeline complete: "
        f"{full_duration_ms:.0f}ms total, "
        f"{len(adjusted_segments)} segments, "
        f"took {elapsed:.0f}ms"
    )

    # --- Update state ---
    return {
        **state,
        "audio_segments": adjusted_segments,
        "full_audio_path": str(full_audio_path.resolve()),
        "full_audio_duration_ms": full_duration_ms,
    }
