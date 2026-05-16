"""Test Kokoro voices and Whisper timestamps without running the full pipeline."""
import asyncio
import os
import soundfile as sf
import whisper
from kokoro_onnx import Kokoro
from pathlib import Path
from agent.config import load_config

async def run_voice_test():
    print("=== KOKORO + WHISPER VOICE TEST ===")
    config = load_config()
    temp_dir = Path(config["paths"]["temp"])
    temp_dir.mkdir(parents=True, exist_ok=True)

    print("\nLoading Kokoro ONNX model...")
    kokoro = Kokoro(
        config["paths"]["kokoro_model"],
        config["paths"]["kokoro_voices"]
    )
    
    print("Loading Whisper Tiny model...")
    whisper_model = whisper.load_model("tiny")
    
    test_text = "Hey bro what even is an API though"
    loop = asyncio.get_event_loop()

    results = []
    
    for char in config["characters"]:
        name = char["name"]
        voice = char["voice"]
        print(f"\n--- Testing {name} ({voice}) ---")
        
        # 1. Generate Kokoro audio
        print("Generating audio...")
        samples, sample_rate = await loop.run_in_executor(
            None,
            lambda: kokoro.create(text=test_text, voice=voice, speed=1.0, lang="en-us")
        )
        
        wav_path = temp_dir / f"voice_test_{name}.wav"
        sf.write(wav_path, samples, sample_rate)
        duration_ms = (len(samples) / sample_rate) * 1000
        
        # 2. Extract Whisper Timestamps
        print("Extracting timestamps...")
        whisper_res = await loop.run_in_executor(
            None,
            lambda: whisper_model.transcribe(str(wav_path), word_timestamps=True, language="en")
        )
        
        words = []
        for segment in whisper_res["segments"]:
            for word_data in segment.get("words", []):
                words.append({
                    "word": word_data["word"].strip(),
                    "offset_ms": word_data["start"] * 1000,
                    "duration_ms": (word_data["end"] - word_data["start"]) * 1000
                })
        
        print(f"Result: {duration_ms:.0f}ms duration | {len(words)} words detected")
        for w in words:
            print(f"  - '{w['word']}' at {w['offset_ms']:.0f}ms (dur: {w['duration_ms']:.0f}ms)")
            
        results.append({
            "name": name,
            "voice": voice,
            "duration_ms": duration_ms,
            "words": len(words)
        })

    print("\n=== TEST SUMMARY ===")
    for r in results:
        print(f"{r['name']:<15} | {r['voice']:<12} | {r['duration_ms']:<6.0f}ms | {r['words']} words")

if __name__ == "__main__":
    asyncio.run(run_voice_test())
