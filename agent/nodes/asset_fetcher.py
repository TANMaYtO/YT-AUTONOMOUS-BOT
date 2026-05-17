"""Node 4 — Asset Fetcher.

Generates TTS audio via Kokoro-ONNX and extracts word-level timestamps 
via OpenAI Whisper (tiny). Replaces Edge-TTS.

Writes to state:
    audio_segments, full_audio_path, full_audio_duration_ms
"""

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any, List

import soundfile as sf
import whisper
from kokoro_onnx import Kokoro
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
    before_sleep_log,
)

from agent.config import load_config
from agent.models import AudioSegment, WordTimestamp
from agent.state import validate_state_for_node

logger = logging.getLogger(__name__)
config = load_config()

# Module-level model initialisation (run once)
_KOKORO = None
_WHISPER = None


def _get_kokoro() -> Kokoro:
    global _KOKORO
    if _KOKORO is None:
        logger.info("[asset_fetcher] Loading Kokoro ONNX model...")
        _KOKORO = Kokoro(
            config["paths"]["kokoro_model"],
            config["paths"]["kokoro_voices"]
        )
    return _KOKORO


def _get_whisper():
    global _WHISPER
    if _WHISPER is None:
        logger.info("[asset_fetcher] Loading Whisper tiny model...")
        _WHISPER = whisper.load_model("tiny")
    return _WHISPER


def remove_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642"
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"
        u"\u3030"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)


def sanitize_line_for_tts(text: str) -> str:
    """Remove emojis and special chars before TTS."""
    text = remove_emojis(text)
    text = re.sub(r'[*_#`~]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type((RuntimeError, OSError, ValueError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _generate_line_audio(
    line_text: str,
    voice_name: str,
    output_wav_path: str,
) -> tuple[float, list[dict]]:
    """Generate audio via Kokoro and extract timestamps via Whisper."""
    loop = asyncio.get_event_loop()
    kokoro = _get_kokoro()
    whisper_model = _get_whisper()
    
    speed = config["pipeline"].get("tts_speed", 1.0)
    
    clean_text = sanitize_line_for_tts(line_text)

    # 1. Generate audio with Kokoro (CPU-bound)
    samples, sample_rate = await loop.run_in_executor(
        None,
        lambda: kokoro.create(
            text=clean_text,
            voice=voice_name,
            speed=speed,
            lang="en-us"
        )
    )

    # 2. Save directly to WAV
    sf.write(output_wav_path, samples, sample_rate)
    duration_ms = (len(samples) / sample_rate) * 1000

    # 3. Transcribe with Whisper for word timestamps
    result = await loop.run_in_executor(
        None,
        lambda: whisper_model.transcribe(
            output_wav_path,
            word_timestamps=True,
            language="en"
        )
    )

    # 4. Extract and validate word timestamps
    word_timestamps = []
    for segment in result["segments"]:
        for word_data in segment.get("words", []):
            start_ms = word_data["start"] * 1000
            end_ms = word_data["end"] * 1000
            dur_ms = end_ms - start_ms
            
            # Ensure negative durations are clamped
            if dur_ms < 50:
                dur_ms = 50
                
            word_timestamps.append({
                "word": word_data["word"].strip(),
                "offset_ms": start_ms,
                "duration_ms": dur_ms
            })

    # Fallback if whisper returned 0 words
    if not word_timestamps:
        words = line_text.split()
        if words:
            logger.warning(f"[asset_fetcher] Whisper found 0 words for line, using fallback. Text: {line_text}")
            chunk_duration = duration_ms / len(words)
            for i, word in enumerate(words):
                word_timestamps.append({
                    "word": word,
                    "offset_ms": i * chunk_duration,
                    "duration_ms": chunk_duration
                })

    if word_timestamps:
        logger.info(
            f"[asset_fetcher] Found {len(word_timestamps)} words. "
            f"First: '{word_timestamps[0]['word']}' ({word_timestamps[0]['offset_ms']:.0f}ms), "
            f"Last: '{word_timestamps[-1]['word']}' ({word_timestamps[-1]['offset_ms']:.0f}ms)"
        )

    return duration_ms, word_timestamps


async def generate_all_audio(
    state: dict[str, Any],
    voice_map: dict[str, str],
    temp_dir: Path,
) -> dict[str, Any]:
    """Node 4: Generate audio for the script."""
    logger.info("[asset_fetcher] Starting audio generation")
    
    if state.get("error"):
        return state

    validation_error = validate_state_for_node(state, "asset_fetcher")
    if validation_error:
        logger.error(f"[asset_fetcher] {validation_error}")
        return {**state, "error": validation_error, "failed_node": "asset_fetcher"}

    try:
        script = state["script"]
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        audio_segments: List[AudioSegment] = []
        filelist_path = temp_dir / "filelist.txt"
        
        start_time = time.perf_counter()
        
        cumulative_offset_ms = 0.0
        
        with open(filelist_path, "w", encoding="utf-8") as flist:
            for i, line in enumerate(script):
                char_name = line["character"]
                voice = voice_map.get(char_name, "am_puck")  # Fallback to default if missing
                
                logger.info(
                    f"[asset_fetcher] Generating audio for line {i}: "
                    f"'{line['line'][:50]}...' voice={voice}"
                )
                
                wav_path = temp_dir / f"line_{i:02d}.wav"
                
                line_start = time.perf_counter()
                
                duration_ms, raw_word_timestamps = await _generate_line_audio(
                    line_text=line["line"],
                    voice_name=voice,
                    output_wav_path=str(wav_path)
                )

                # Add cumulative offset to word timestamps
                for wt in raw_word_timestamps:
                    wt["offset_ms"] += cumulative_offset_ms

                word_objs = [WordTimestamp(**wt) for wt in raw_word_timestamps]
                
                seg = AudioSegment(
                    path=str(wav_path),
                    duration_ms=duration_ms,
                    character=char_name,
                    line_index=i,
                    word_timestamps=word_objs
                )
                audio_segments.append(seg)
                
                flist.write(f"file '{wav_path.name}'\n")
                
                cumulative_offset_ms += duration_ms
                
                line_elapsed = (time.perf_counter() - line_start) * 1000
                logger.info(
                    f"[asset_fetcher] Line {i} complete: {duration_ms:.0f}ms audio, "
                    f"{len(word_objs)} words, took {line_elapsed:.0f}ms"
                )

        total_audio_ms = sum(seg.duration_ms for seg in audio_segments)
        logger.info(
            f"[asset_fetcher] All {len(script)} lines generated. "
            f"Total duration: {total_audio_ms:.0f}ms ({total_audio_ms/1000:.1f}s)"
        )

        full_audio_path = temp_dir / "full_audio.wav"
        concat_cmd = (
            f'ffmpeg -f concat -safe 0 -i "{filelist_path}" '
            f'-c copy -y "{full_audio_path}"'
        )
        logger.info(f"[WAV concatenation] Running: {concat_cmd}")
        
        proc = await asyncio.create_subprocess_shell(
            concat_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg concatenation failed with code {proc.returncode}")

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"[asset_fetcher] Audio pipeline complete: {total_audio_ms:.0f}ms total, "
            f"{len(audio_segments)} segments, took {elapsed:.0f}ms"
        )

        return {
            **state,
            "audio_segments": [seg.model_dump() for seg in audio_segments],
            "full_audio_path": str(full_audio_path),
            "full_audio_duration_ms": total_audio_ms
        }

    except Exception as e:
        logger.error(f"[asset_fetcher] Pipeline failed: {e}")
        return {**state, "error": str(e), "failed_node": "asset_fetcher"}
