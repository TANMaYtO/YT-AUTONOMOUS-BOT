"""Node 5 — Video Assembler.

Composites all assets into the final YouTube Shorts MP4 (1080x1920).

Layout:
    - Background gameplay footage fills 100% of the 1080x1920 frame
    - Character images appear as overlays ONLY when speaking
    - Character A: bottom-left (x=20, y=1100), 400x400px
    - Character B: bottom-right (x=660, y=1100), 400x400px
    - Subtitles: single word, centre-screen, burned in via Pass 2

Pipeline:
    1. Generate .ass subtitle file from 1-word timestamp chunks
       - Sanity check: zero/negative duration chunks merge forward
    2. FFmpeg Pass 1: background (full frame) + time-gated character
       overlays + audio → intermediate.mp4
    3. FFmpeg Pass 2: intermediate.mp4 + .ass subtitle burn-in
       → final.mp4
    4. ffprobe validation after every pass

Two-pass render is mandatory — prevents filter_complex conflicts
and keeps each pass debuggable independently.

Windows path escaping: all paths converted to forward slashes
before being passed to FFmpeg filter chains. This is the #1 cause
of FFmpeg failures on Windows — never skip this step.
"""

import logging
import time
from pathlib import Path
from typing import Any

from agent.state import validate_state_for_node
from agent.utils import (
    find_ffmpeg,
    probe_media,
    run_ffmpeg,
    to_ffmpeg_path,
    to_ffmpeg_filter_path,
)

logger = logging.getLogger(__name__)

# Character overlay constants
CHAR_IMG_SIZE = 400          # 400x400 square overlay
CHAR_A_X = 20               # 20px from left edge
CHAR_B_X = 1080 - 400 - 20  # 660 — 20px from right edge
CHAR_Y = 1100               # Safe zone — above YouTube UI chrome


# -------------------------------------------------------------------
# .ass timestamp formatting
# -------------------------------------------------------------------

def _ms_to_ass_timestamp(ms: float) -> str:
    """Convert milliseconds to .ass timestamp format H:MM:SS.cc.

    .ass uses centiseconds (hundredths of a second), NOT milliseconds.
    Example: 2310ms → '0:00:02.31'

    Args:
        ms: Time in milliseconds.

    Returns:
        Formatted timestamp string.
    """
    if ms < 0:
        ms = 0

    total_cs = int(ms / 10)  # centiseconds
    cs = total_cs % 100
    total_seconds = total_cs // 100
    seconds = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60

    return f"{hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"


# -------------------------------------------------------------------
# Subtitle generation
# -------------------------------------------------------------------

def generate_subtitle_file(
    audio_segments: list[dict[str, Any]],
    output_path: Path,
    config: dict[str, Any],
    character_a: str = "",
) -> Path:
    """Generate an .ass subtitle file from word-boundary timestamps.

    Groups words into N-word chunks (default 1), calculates absolute
    start/end times from cumulative offsets, and writes the .ass file.

    Per-character color coding:
        Character A → yellow {\\c&H00FFFF&}
        Character B → cyan   {\\c&H00FFFFE0&}

    Sanity check: any chunk with duration <= 0ms or start >= end
    is merged into the next chunk (not dropped silently).

    Args:
        audio_segments: List of AudioSegmentDict from state,
                        with cumulative word timestamps.
        output_path: Where to save the .ass file.
        config: Loaded config dict (uses 'subtitle' section).
        character_a: Name of character A (for color assignment).

    Returns:
        Path to the generated .ass file.
    """
    logger.info("[video_assembler] Generating .ass subtitle file")

    sub_config = config.get("subtitle", {})
    words_per_chunk = sub_config.get("words_per_chunk", 1)
    font = sub_config.get("font", "Arial")
    font_size = sub_config.get("font_size", 72)
    primary_color = sub_config.get("primary_color", "&H00FFFF00")
    outline_color = sub_config.get("outline_color", "&H00000000")
    outline_width = sub_config.get("outline_width", 5)
    bold = sub_config.get("bold", 1)
    alignment = sub_config.get("alignment", 5)
    margin_v = sub_config.get("margin_v", 0)

    # Per-character color overrides (ASS inline override tags)
    COLOR_A = r"{\c&H00FFFF&}"      # yellow for Character A
    COLOR_B = r"{\c&H00FFFFE0&}"    # cyan for Character B

    video_config = config.get("video", {})
    play_res_x = video_config.get("resolution_width", 1080)
    play_res_y = video_config.get("resolution_height", 1920)

    # --- Collect ALL words into a flat list with character ownership ---
    all_words: list[dict[str, Any]] = []
    for seg in audio_segments:
        char_name = seg.get("character", "")
        for wt in seg.get("word_timestamps", []):
            word_entry = dict(wt)
            word_entry["_character"] = char_name
            all_words.append(word_entry)

    if not all_words:
        logger.warning(
            "[video_assembler] No word timestamps found — "
            "subtitle file will be empty"
        )

    # --- Group into N-word chunks ---
    raw_chunks: list[list[dict[str, Any]]] = []
    for i in range(0, len(all_words), words_per_chunk):
        chunk = all_words[i : i + words_per_chunk]
        raw_chunks.append(chunk)

    # --- Calculate start/end for each chunk + sanity check ---
    dialogue_entries: list[dict[str, Any]] = []
    carry_words: list[dict[str, Any]] = []  # Words to merge forward

    for idx, chunk in enumerate(raw_chunks):
        # Prepend any carry-over words from a bad previous chunk
        if carry_words:
            chunk = carry_words + chunk
            carry_words = []

        chunk_start = chunk[0]["offset_ms"]
        last_word = chunk[-1]
        chunk_end = last_word["offset_ms"] + last_word["duration_ms"]
        chunk_duration = chunk_end - chunk_start
        chunk_text = " ".join(w["word"] for w in chunk).upper()

        # Determine character ownership (use first word's character)
        chunk_char = chunk[0].get("_character", "")

        # Sanity check: invalid duration → merge into next chunk
        if chunk_duration <= 0 or chunk_start >= chunk_end:
            logger.warning(
                f"[video_assembler] Subtitle chunk {idx} has "
                f"invalid duration ({chunk_duration:.0f}ms): "
                f"'{chunk_text}' — merging into next chunk"
            )
            carry_words = chunk
            continue

        dialogue_entries.append({
            "start": chunk_start,
            "end": chunk_end,
            "text": chunk_text,
            "character": chunk_char,
        })

    # If there are leftover carry words after the last chunk,
    # attach them to the previous entry by extending its end time
    if carry_words and dialogue_entries:
        last_entry = dialogue_entries[-1]
        last_word = carry_words[-1]
        extended_end = last_word["offset_ms"] + last_word["duration_ms"]
        extra_text = " ".join(w["word"] for w in carry_words).upper()
        last_entry["end"] = max(last_entry["end"], extended_end)
        last_entry["text"] += " " + extra_text
        logger.info(
            "[video_assembler] Merged trailing carry words "
            f"into last entry: '{last_entry['text']}'"
        )

    # --- Build .ass file content ---
    ass_header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {play_res_x}\n"
        f"PlayResY: {play_res_y}\n"
        "WrapStyle: 0\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, "
        "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, "
        "Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        f"Style: Default,{font},{font_size},{primary_color},"
        f"&H000000FF,{outline_color},&H00000000,"
        f"{bold},0,0,0,100,100,0,0,1,{outline_width},0,"
        f"{alignment},10,10,{margin_v},1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, "
        "MarginR, MarginV, Effect, Text\n"
    )

    dialogue_lines: list[str] = []
    for entry in dialogue_entries:
        start_ts = _ms_to_ass_timestamp(entry["start"])
        end_ts = _ms_to_ass_timestamp(entry["end"])
        # Apply per-character color override
        is_a = (entry.get("character", "") == character_a)
        color_tag = COLOR_A if is_a else COLOR_B
        text = f"{color_tag}{entry['text']}"
        dialogue_lines.append(
            f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}"
        )

    ass_content = ass_header + "\n".join(dialogue_lines) + "\n"

    # --- Write file ---
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ass_content, encoding="utf-8")

    # Calculate total duration covered by subtitles
    if dialogue_entries:
        first_start = dialogue_entries[0]["start"]
        last_end = dialogue_entries[-1]["end"]
        coverage_ms = last_end - first_start
    else:
        coverage_ms = 0

    logger.info(
        f"[video_assembler] Subtitle file written: {output_path}\n"
        f"  Entries: {len(dialogue_entries)}\n"
        f"  Coverage: {coverage_ms:.0f}ms "
        f"({coverage_ms / 1000:.1f}s)\n"
        f"  Words per chunk: {words_per_chunk}"
    )

    return output_path


# -------------------------------------------------------------------
# Overlay window calculation
# -------------------------------------------------------------------

def _build_overlay_windows(
    audio_segments: list[dict[str, Any]],
    character_a: str,
    character_a_image: str,
    character_b_image: str,
) -> list[dict[str, Any]]:
    """Build time-gated overlay windows from audio segment data.

    Each window represents one line of dialogue where a character's
    image should be visible on screen.

    Args:
        audio_segments: Audio segments with cumulative timestamps.
        character_a: Name of character A (for matching).
        character_a_image: Path to character A image.
        character_b_image: Path to character B image.

    Returns:
        List of overlay window dicts with character, image_path,
        start_sec, end_sec, x, y.
    """
    windows: list[dict[str, Any]] = []

    # Reconstruct cumulative line offsets from word timestamps.
    # The first word's offset_ms in each segment IS the line start
    # (already cumulative from generate_all_audio).
    for seg in audio_segments:
        word_ts = seg.get("word_timestamps", [])
        if not word_ts:
            continue

        char_name = seg["character"]
        line_start_ms = word_ts[0]["offset_ms"]
        line_end_ms = line_start_ms + seg["duration_ms"]

        # Determine which character this is and set position
        is_char_a = (char_name == character_a)
        x = CHAR_A_X if is_char_a else CHAR_B_X
        image_path = character_a_image if is_char_a else character_b_image

        windows.append({
            "character": char_name,
            "image_path": image_path,
            "start_sec": line_start_ms / 1000.0,
            "end_sec": line_end_ms / 1000.0,
            "x": x,
            "y": CHAR_Y,
        })

    logger.info(
        f"[video_assembler] Built {len(windows)} overlay windows:"
    )
    for i, w in enumerate(windows):
        logger.info(
            f"  [{i}] {w['character']:>10} "
            f"{w['start_sec']:.2f}s → {w['end_sec']:.2f}s  "
            f"x={w['x']} y={w['y']}"
        )

    return windows


# -------------------------------------------------------------------
# FFmpeg Pass 1 — full-frame background + time-gated overlays
# -------------------------------------------------------------------

async def assemble_pass_one(
    background_video: Path,
    character_a_image: Path,
    character_b_image: Path,
    full_audio_path: Path,
    output_path: Path,
    config: dict[str, Any],
    duration_sec: float,
    overlay_windows: list[dict[str, Any]],
) -> Path:
    """FFmpeg Pass 1: full-frame background + character overlays + audio.

    Layout (1080x1920 vertical):
        Full frame: background gameplay footage (looped)
        Character overlays: 400x400, appear ONLY when speaking
            Character A: bottom-left (x=20, y=1100)
            Character B: bottom-right (x=660, y=1100)
        Audio: dialogue + optional background music (mixed)

    The filter_complex is built dynamically — one overlay entry
    per line of dialogue, each time-gated with enable='between()'.

    Args:
        background_video: Path to background gameplay clip.
        character_a_image: Path to character A PNG.
        character_b_image: Path to character B PNG.
        full_audio_path: Path to concatenated full_audio.wav.
        output_path: Where to save intermediate.mp4.
        config: Loaded config dict.
        duration_sec: Target duration in seconds.
        overlay_windows: List of overlay timing windows.

    Returns:
        Path to intermediate.mp4.

    Raises:
        RuntimeError: If FFmpeg fails or output validation fails.
    """
    logger.info("[video_assembler] Starting Pass 1 (composite)")

    video_config = config.get("video", {})
    width = video_config.get("resolution_width", 1080)
    height = video_config.get("resolution_height", 1920)
    fps = video_config.get("fps", 30)

    ffmpeg_config = config.get("ffmpeg", {})
    video_codec = ffmpeg_config.get("intermediate_codec", "libx264")
    audio_codec = ffmpeg_config.get("audio_codec", "aac")

    ffmpeg = find_ffmpeg()

    # Convert paths to forward slashes for FFmpeg
    bg_path = to_ffmpeg_path(background_video)
    audio_path = to_ffmpeg_path(full_audio_path)
    out_path = to_ffmpeg_path(output_path)

    dur = f"{duration_sec:.2f}"

    # --- Check for background music ---
    project_root = Path(__file__).resolve().parent.parent.parent
    music_dir = project_root / "assets" / "music"
    music_file: Path | None = None

    if music_dir.exists():
        music_exts = (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac")
        for f in sorted(music_dir.iterdir()):
            if f.suffix.lower() in music_exts:
                music_file = f
                break

    has_music = music_file is not None
    if has_music:
        logger.info(
            f"[video_assembler] Background music found: {music_file.name}"
        )
        music_path = to_ffmpeg_path(music_file)
    else:
        logger.warning(
            "[video_assembler] No background music found in assets/music/"
        )

    # --- Build filter_complex dynamically ---
    # Inputs:
    #   [0] = background video (looped)
    #   [1] = character A image
    #   [2] = character B image
    #   [3] = dialogue audio
    #   [4] = background music (optional, looped)

    filter_parts: list[str] = []

    # Scale background to full 1080x1920
    filter_parts.append(
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,fps={fps}[bg]"
    )

    # Count how many times each character speaks.
    char_a_count = sum(
        1 for w in overlay_windows if w["x"] == CHAR_A_X
    )
    char_b_count = sum(
        1 for w in overlay_windows if w["x"] == CHAR_B_X
    )

    # Scale + split character A image
    if char_a_count == 1:
        filter_parts.append(
            f"[1:v]scale={CHAR_IMG_SIZE}:{CHAR_IMG_SIZE}[ca0]"
        )
    elif char_a_count > 1:
        ca_labels = "".join(f"[ca{i}]" for i in range(char_a_count))
        filter_parts.append(
            f"[1:v]scale={CHAR_IMG_SIZE}:{CHAR_IMG_SIZE},"
            f"split={char_a_count}{ca_labels}"
        )

    # Scale + split character B image
    if char_b_count == 1:
        filter_parts.append(
            f"[2:v]scale={CHAR_IMG_SIZE}:{CHAR_IMG_SIZE}[cb0]"
        )
    elif char_b_count > 1:
        cb_labels = "".join(f"[cb{i}]" for i in range(char_b_count))
        filter_parts.append(
            f"[2:v]scale={CHAR_IMG_SIZE}:{CHAR_IMG_SIZE},"
            f"split={char_b_count}{cb_labels}"
        )

    # Chain overlays — one per line of dialogue.
    prev_label = "bg"
    ca_idx = 0
    cb_idx = 0

    for i, window in enumerate(overlay_windows):
        is_char_a = (window["x"] == CHAR_A_X)
        if is_char_a:
            img_label = f"ca{ca_idx}"
            ca_idx += 1
        else:
            img_label = f"cb{cb_idx}"
            cb_idx += 1

        x = window["x"]
        y = window["y"]
        start = f"{window['start_sec']:.3f}"
        end = f"{window['end_sec']:.3f}"
        out_label = f"t{i}" if i < len(overlay_windows) - 1 else "v"

        filter_parts.append(
            f"[{prev_label}][{img_label}]overlay={x}:{y}:"
            f"enable='between(t,{start},{end})'[{out_label}]"
        )
        prev_label = out_label

    if not overlay_windows:
        filter_parts.append("[bg]null[v]")

    # Audio mixing: dialogue + optional background music
    # Input indices: [3]=dialogue, [4]=music (if present)
    audio_input_idx = 3
    if has_music:
        music_input_idx = 4
        filter_parts.append(
            f"[{audio_input_idx}:a][{music_input_idx}:a]"
            f"amix=inputs=2:duration=first:weights=1 0.1[aout]"
        )
        audio_map = "[aout]"
    else:
        audio_map = f"{audio_input_idx}:a"

    filter_complex = ";".join(filter_parts)

    # --- Build FFmpeg args ---
    args = [
        ffmpeg,
        "-stream_loop", "-1",
        "-i", bg_path,
        "-i", to_ffmpeg_path(character_a_image),
        "-i", to_ffmpeg_path(character_b_image),
        "-i", audio_path,
    ]

    # Add music input if found (looped)
    if has_music:
        args.extend(["-stream_loop", "-1", "-i", music_path])

    args.extend([
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", audio_map,
        "-t", dur,
        "-c:v", video_codec,
        "-preset", "fast",
        "-c:a", audio_codec,
        "-shortest",
        "-y", out_path,
    ])

    await run_ffmpeg(args, description="Pass 1 (composite)")

    # --- Validate intermediate output ---
    if not output_path.exists():
        raise RuntimeError(
            f"Pass 1 failed: intermediate file not created: {output_path}"
        )

    probe = await probe_media(output_path)
    inter_duration = float(probe["format"]["duration"])
    stream_types = [s.get("codec_type") for s in probe.get("streams", [])]

    logger.info(
        f"[video_assembler] Pass 1 complete:\n"
        f"  File: {output_path}\n"
        f"  Duration: {inter_duration:.1f}s\n"
        f"  Streams: {stream_types}"
    )

    if inter_duration < 1.0:
        raise RuntimeError(
            f"Pass 1 produced a suspiciously short file: "
            f"{inter_duration:.1f}s"
        )

    if "video" not in stream_types:
        raise RuntimeError("Pass 1 output has no video stream")

    if "audio" not in stream_types:
        raise RuntimeError("Pass 1 output has no audio stream")

    return output_path


# -------------------------------------------------------------------
# FFmpeg Pass 2 — subtitle burn-in
# -------------------------------------------------------------------

async def assemble_pass_two(
    intermediate_video: Path,
    subtitle_file: Path,
    output_path: Path,
    config: dict[str, Any],
) -> Path:
    """FFmpeg Pass 2: burn .ass subtitles onto intermediate video.

    Args:
        intermediate_video: Path to Pass 1 output.
        subtitle_file: Path to .ass subtitle file.
        output_path: Where to save final.mp4.
        config: Loaded config dict (uses 'ffmpeg' section).

    Returns:
        Path to final.mp4.

    Raises:
        RuntimeError: If FFmpeg fails or output validation fails.
    """
    logger.info("[video_assembler] Starting Pass 2 (subtitle burn-in)")

    ffmpeg_config = config.get("ffmpeg", {})
    video_codec = ffmpeg_config.get("final_codec", "libx264")

    ffmpeg = find_ffmpeg()

    # Convert paths to forward slashes — MANDATORY on Windows
    inter_path = to_ffmpeg_path(intermediate_video)
    out_path = to_ffmpeg_path(output_path)

    # Subtitle path for -vf ass= needs special handling on Windows.
    # FFmpeg's filter parser treats ':' as option separator, so
    # E:/path gets parsed as option 'E' with value '/path'.
    # Fix: escape the colon after the drive letter with backslash,
    # AND escape backslashes in the path.
    sub_str = str(subtitle_file).replace("\\", "/")
    if len(sub_str) >= 2 and sub_str[1] == ":":
        # E:/path → E\:/path (escaped colon for filter parser)
        sub_str = sub_str[0] + "\\:" + sub_str[2:]
    # Also escape any single quotes in the path
    sub_str = sub_str.replace("'", "'\\''")

    args = [
        ffmpeg,
        "-i", inter_path,
        "-vf", f"ass='{sub_str}'",
        "-c:v", video_codec,
        "-preset", "fast",
        "-c:a", "copy",
        "-y", out_path,
    ]

    await run_ffmpeg(args, description="Pass 2 (subtitles)")

    # --- Validate final output ---
    if not output_path.exists():
        raise RuntimeError(
            f"Pass 2 failed: final file not created: {output_path}"
        )

    probe = await probe_media(output_path)
    final_duration = float(probe["format"]["duration"])
    stream_types = [s.get("codec_type") for s in probe.get("streams", [])]

    logger.info(
        f"[video_assembler] Pass 2 complete:\n"
        f"  File: {output_path}\n"
        f"  Duration: {final_duration:.1f}s\n"
        f"  Streams: {stream_types}"
    )

    return output_path


# -------------------------------------------------------------------
# Video validation
# -------------------------------------------------------------------

async def validate_video(video_path: Path) -> tuple[bool, float]:
    """Validate a video file with ffprobe.

    Checks:
        - Duration > 5 seconds
        - Has at least one video stream
        - Has at least one audio stream

    Args:
        video_path: Path to the .mp4 file.

    Returns:
        Tuple of (is_valid, duration_sec).
    """
    try:
        probe = await probe_media(video_path)
    except RuntimeError as e:
        logger.error(f"[video_assembler] ffprobe failed: {e}")
        return False, 0.0

    duration = float(probe.get("format", {}).get("duration", 0))
    stream_types = [
        s.get("codec_type") for s in probe.get("streams", [])
    ]

    has_video = "video" in stream_types
    has_audio = "audio" in stream_types
    long_enough = duration > 5.0

    logger.info(
        f"[video_assembler] Video validation:\n"
        f"  File: {video_path}\n"
        f"  Duration: {duration:.1f}s (need >5s: "
        f"{'OK' if long_enough else 'FAIL'})\n"
        f"  Video stream: {'OK' if has_video else 'MISSING'}\n"
        f"  Audio stream: {'OK' if has_audio else 'MISSING'}"
    )

    is_valid = has_video and has_audio and long_enough
    return is_valid, duration


# -------------------------------------------------------------------
# Main node function
# -------------------------------------------------------------------

async def assemble_video(
    state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Full video assembly: subtitles → Pass 1 → Pass 2 → validate.

    Args:
        state: Pipeline state with audio_segments, full_audio_path,
               character images, and background_video populated.
        config: Loaded config dict.

    Returns:
        Updated state with subtitle_file, intermediate_video,
        final_video, video_duration_sec, and video_validated.
    """
    logger.info("[video_assembler] Starting video assembly")
    start_time = time.perf_counter()

    # --- Check upstream errors ---
    if state.get("error"):
        logger.warning(
            "[video_assembler] Upstream error detected, skipping"
        )
        return state

    # --- Validate required state ---
    validation_error = validate_state_for_node(state, "video_assembler")
    if validation_error:
        logger.error(f"[video_assembler] {validation_error}")
        return {
            **state,
            "error": validation_error,
            "failed_node": "video_assembler",
        }

    temp_dir = Path(state["full_audio_path"]).parent

    # --- Step 1: Generate subtitle file ---
    subtitle_path = temp_dir / "subtitles.ass"
    generate_subtitle_file(
        audio_segments=state["audio_segments"],
        output_path=subtitle_path,
        config=config,
        character_a=state["character_a"],
    )

    # --- Step 2: Build overlay windows ---
    overlay_windows = _build_overlay_windows(
        audio_segments=state["audio_segments"],
        character_a=state["character_a"],
        character_a_image=state["character_a_image"],
        character_b_image=state["character_b_image"],
    )

    # --- Step 3: Pass 1 (composite) ---
    intermediate_path = temp_dir / "intermediate.mp4"
    duration_sec = state["full_audio_duration_ms"] / 1000.0

    try:
        await assemble_pass_one(
            background_video=Path(state["background_video"]),
            character_a_image=Path(state["character_a_image"]),
            character_b_image=Path(state["character_b_image"]),
            full_audio_path=Path(state["full_audio_path"]),
            output_path=intermediate_path,
            config=config,
            duration_sec=duration_sec,
            overlay_windows=overlay_windows,
        )
    except RuntimeError as e:
        logger.error(f"[video_assembler] Pass 1 failed: {e}")
        return {
            **state,
            "error": f"Pass 1 failed: {e}",
            "failed_node": "video_assembler",
            "subtitle_file": str(subtitle_path.resolve()),
        }

    # --- Step 4: Pass 2 (subtitle burn-in) ---
    final_path = Path(
        config.get("paths", {}).get("output", "output/")
    ) / f"{state['run_id']}.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        await assemble_pass_two(
            intermediate_video=intermediate_path,
            subtitle_file=subtitle_path,
            output_path=final_path,
            config=config,
        )
    except RuntimeError as e:
        logger.error(f"[video_assembler] Pass 2 failed: {e}")
        return {
            **state,
            "error": f"Pass 2 failed: {e}",
            "failed_node": "video_assembler",
            "subtitle_file": str(subtitle_path.resolve()),
            "intermediate_video": str(intermediate_path.resolve()),
        }

    # --- Step 5: Final validation ---
    is_valid, final_duration = await validate_video(final_path)

    elapsed = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"[video_assembler] Assembly complete in {elapsed:.0f}ms\n"
        f"  Final video: {final_path}\n"
        f"  Duration: {final_duration:.1f}s\n"
        f"  Validated: {is_valid}"
    )

    result_state = {
        **state,
        "subtitle_file": str(subtitle_path.resolve()),
        "intermediate_video": str(intermediate_path.resolve()),
        "final_video": str(final_path.resolve()),
        "video_duration_sec": final_duration,
        "video_validated": is_valid,
    }

    if not is_valid:
        result_state["error"] = (
            f"Final video validation failed: "
            f"duration={final_duration:.1f}s, "
            f"expected >5s with video+audio streams"
        )
        result_state["failed_node"] = "video_assembler"

    return result_state
