# 🤖 YT Autonomous Bot

> Fully autonomous YouTube Shorts pipeline — from AI-generated scripts to uploaded videos. Zero human input required.

An end-to-end autonomous agent that generates educational "brainrot" YouTube Shorts featuring anime characters explaining tech topics. Powered by **Gemini 2.5 Flash**, **Kokoro-ONNX TTS**, **Whisper**, and **FFmpeg**.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                     │
├────────┬────────┬────────┬────────┬────────┬───────┬────────┤
│ Node 1 │ Node 2 │ Node 3 │ Node 4 │ Node 5 │ Node 6│ Node 7 │
│  Idea  │ Script │ Image  │ Asset  │ Video  │ Meta- │ Queue  │
│  Gen   │ Writer │ Picker │ Fetcher│ Assembl│ data  │ Manager│
│        │        │        │        │        │       │        │
│ Topics │ Gemini │ Local  │ Kokoro │ 2-pass │ Gemini│ JSON   │
│   +    │ Flash  │ PNGs + │  TTS + │ FFmpeg │  SEO  │ Queue  │
│ History│        │ BG     │ Whisper│        │       │        │
└────────┴────────┴────────┴────────┴────────┴───────┴────────┘
                                                         │
                                                  ┌──────┴──────┐
                                                  │   YouTube   │
                                                  │  Uploader   │
                                                  └─────────────┘
```

### Pipeline Flow

| Node | Name | What it does |
|------|------|-------------|
| 1 | **Idea Generator** | Weighted random topic selection + character pairing from history |
| 2 | **Script Writer** | Gemini 2.5 Flash generates brainrot dialogue, Pydantic-validated |
| 3 | **Image Picker** | Selects character expression PNGs + background video |
| 4 | **Asset Fetcher** | Local Kokoro-ONNX TTS audio + Whisper forced alignment for timestamps |
| 5 | **Video Assembler** | 2-pass FFmpeg — character overlays, subtitles (.ass), background music |
| 6 | **Metadata Generator** | Gemini generates SEO-optimized title, description, hashtags |
| 7 | **Queue Manager** | Schedules the final generated asset into `queue.json` |

---

## 📁 Project Structure

```text
YT-AUTONOMOUS-BOT/
├── agent/                    # Core LangGraph pipeline logic
│   ├── nodes/                # LangGraph node implementations
│   ├── config.py             # YAML config loader
│   ├── models.py             # Pydantic models (ScriptLine, etc.)
│   ├── orchestrator.py       # LangGraph graph wiring
│   ├── run_generation.py     # Windows Task Scheduler daemon runner
│   ├── startup_checks.py     # Pre-flight environment validation
│   └── state.py              # Single-source-of-truth TypedDict
├── scripts/                  # Setup & test scripts
│   ├── generate_image_library.py  
│   └── test_phase3.py        # Autonomous end-to-end test
├── uploader/                 # YouTube upload module
│   ├── scheduler.py          # Upload scheduling logic
│   └── youtube_upload.py     # YouTube Data API v3 OAuth flow
├── models/                   # Local models (Kokoro ONNX, voices)
├── config.yaml               # Characters, topics, upload slots
├── requirements.txt          # Python dependencies
├── .env.template             # Environment variable template
└── README.md
```

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.10+**
- **FFmpeg** with `libass` support (for subtitle burn-in)
- **Google Gemini API key** ([Get one here](https://aistudio.google.com/apikey))

### 1. Clone & Setup

```bash
git clone https://github.com/TANMaYtO/YT-AUTONOMOUS-BOT.git
cd YT-AUTONOMOUS-BOT

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.template .env
# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=your_key_here
```

### 3. Download Kokoro Models

Save both required models to `models/kokoro/`:
- **ONNX Model:** [kokoro-v1.0.onnx](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx) (~310MB)
- **Voices Binary:** [voices-v1.0.bin](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin) (~8MB)

### 4. Setup Local Assets

Run the image generator to cache character UI overlays:
```bash
python scripts/generate_image_library.py
```
Place your dynamic background loop in `assets/backgrounds/` and background music in `assets/music/`.

### 5. Google OAuth Setup

To upload autonomously, the bot needs `credentials/google_oauth.json` (Desktop Client ID) from Google Cloud Console.
1. Download your OAuth Desktop App JSON and save it to `credentials/google_oauth.json`.
2. Run the one-time authentication flow:
```bash
python auth_flow.py
```
This performs a one-time browser login and caches the refresh tokens in `credentials/token.json`.

### 6. Test the Pipeline & Uploads

```bash
# Full end-to-end autonomous test (creates video, saves to output/ & queue.json, does NOT upload)
python scripts/test_phase3.py

# Test the YouTube Upload flow (reads queue, prompts for confirmation, uploads to YT)
python scripts/test_upload.py
```

### 7. Production Deployment (Task Scheduler)

Once tested, you can automate the entire daily lifecycle using Windows Task Scheduler:

```bash
# Automates the creation of 4 daily tasks (1 Generation run, 3 Upload runs)
python scripts/setup_task_scheduler.py
```
*Note: You will need to check the "Run whether user is logged on or not" option in the Windows Task Scheduler GUI for these tasks to run completely headless.*

---

## 🎭 Characters & TTS

We recently upgraded from Edge TTS to fully local **Kokoro-ONNX** for high-quality, expressive voices.

| Character | Anime | Role | Kokoro Voice ID |
|-----------|-------|------|-----------------|
| Nobita | Doraemon | Confused | am_puck |
| Luffy | One Piece | Confused | am_michael |
| Doraemon | Doraemon | Explainer | am_adam |
| Light Yagami | Death Note | Explainer | bm_lewis |
| Gojo | Jujutsu Kaisen | Explainer | am_fenrir |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Agent Orchestration** | LangGraph |
| **AI Script Generation** | Google Gemini 2.5 Flash |
| **Text-to-Speech** | Kokoro-ONNX (Local) |
| **Audio Alignment** | OpenAI Whisper (Tiny Model, FP32) |
| **Video Assembly** | FFmpeg (libx264, libass, amix) |
| **Data Validation** | Pydantic v2 |
| **Upload Flow** | YouTube Data API v3 |
| **Retry Logic** | Tenacity (exponential backoff) |

---

## 📋 Configuration

All pipeline settings are inside `config.yaml`:

- **50 tech topics** — weighted random selection, history-aware
- **5 anime characters** — with roles, voices, and image folders
- **3 daily upload slots** — configurable schedule
- **Video specs** — 1080×1920, 30fps, AAC audio

---

## 📝 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `TELEGRAM_BOT_TOKEN` | ❌ | Telegram bot for failure alerts |
| `TELEGRAM_CHAT_ID` | ❌ | Telegram chat for alerts |

---

## ⚠️ Notes

- Free-tier Gemini API has rate limits — the pipeline includes exponential backoff retry logic.
- The pipeline does not require internet connection for audio generation anymore, as Kokoro and Whisper are completely local.
- Videos are 1080×1920 vertical format optimized for YouTube Shorts.
- The `history.json` file prevents topic/character pair repetition across runs.

---

## 📄 License

MIT
