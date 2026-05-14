# 🤖 YT Autonomous Bot

> Fully autonomous YouTube Shorts pipeline — from AI-generated scripts to uploaded videos. Zero human input required.

An end-to-end autonomous agent that generates educational "brainrot" YouTube Shorts featuring anime characters explaining tech topics. Powered by **Gemini 2.5 Flash**, **Edge TTS**, and **FFmpeg**.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   LangGraph Pipeline                │
├──────────┬──────────┬──────────┬──────────┬─────────┤
│  Node 1  │  Node 2  │  Node 4  │  Node 5  │ Node 6  │
│  Idea    │  Script  │  Asset   │  Video   │ Metadata│
│Generator │  Writer  │ Fetcher  │ Assembler│Generator│
│          │          │          │          │         │
│ Topics + │  Gemini  │ Edge TTS │ 2-pass   │ Gemini  │
│ History  │  Flash   │ Voices   │ FFmpeg   │ SEO     │
└──────────┴──────────┴──────────┴──────────┴─────────┘
                         │
                    ┌────┴────┐
                    │ Node 7  │
                    │ YouTube │
                    │Uploader │
                    └─────────┘
```

### Pipeline Flow

| Node | Name | What it does |
|------|------|-------------|
| 1 | **Idea Generator** | Weighted random topic selection + character pairing from history |
| 2 | **Script Writer** | Gemini 2.5 Flash generates brainrot dialogue, Pydantic-validated |
| 3 | **Image Picker** | Selects character expression PNGs from pre-generated library |
| 4 | **Asset Fetcher** | Edge TTS generates voice audio for each dialogue line |
| 5 | **Video Assembler** | 2-pass FFmpeg — character overlays, subtitles, background music |
| 6 | **Metadata Generator** | Gemini generates SEO-optimized title, description, hashtags |
| 7 | **Queue Manager** | Schedules and uploads to YouTube via Data API v3 |

---

## 📁 Project Structure

```
YT-AUTONOMOUS-BOT/
├── agent/                    # Core pipeline logic
│   ├── nodes/                # LangGraph node implementations
│   │   ├── idea_generator.py # Node 1: Topic + character selection
│   │   ├── script_writer.py  # Node 2: Gemini script generation
│   │   ├── image_picker.py   # Node 3: Character image selection
│   │   ├── asset_fetcher.py  # Node 4: TTS audio generation
│   │   ├── video_assembler.py# Node 5: FFmpeg video assembly
│   │   ├── metadata_generator.py # Node 6: SEO metadata
│   │   └── queue_manager.py  # Node 7: Upload queue
│   ├── config.py             # YAML config loader
│   ├── models.py             # Pydantic models (ScriptLine, etc.)
│   ├── orchestrator.py       # LangGraph graph wiring
│   ├── startup_checks.py     # Pre-flight validation
│   ├── state.py              # VideoState schema
│   └── utils.py              # Shared utilities
├── scripts/                  # Setup & test scripts
│   ├── generate_image_library.py  # One-time character image gen
│   ├── test_phase1.py        # Phase 1 test (TTS + FFmpeg)
│   └── test_phase2.py        # Phase 2 test (Gemini → video)
├── uploader/                 # YouTube upload module
│   ├── scheduler.py          # Upload scheduling
│   └── youtube_upload.py     # YouTube Data API v3
├── config.yaml               # Characters, topics, upload slots
├── requirements.txt          # Python dependencies
├── main.py                   # Entry point
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

### 3. Generate Character Images (One-time)

```bash
python scripts/generate_image_library.py
```

This generates 30 character expression PNGs (5 characters × 6 expressions) from [Pollinations AI](https://pollinations.ai) with background removal.

### 4. Add Background Assets

Place your assets in:
- `assets/backgrounds/` — Background video (`.mp4`)
- `assets/music/` — Background music (`.mp3`)

### 5. Run the Pipeline

```bash
# Interactive test (generates 1 video, pauses for script review)
python scripts/test_phase2.py

# Full autonomous mode
python main.py
```

---

## 🎭 Characters

| Character | Anime | Role | Voice |
|-----------|-------|------|-------|
| Nobita | Doraemon | Confused | en-US-SteffanNeural |
| Luffy | One Piece | Confused | en-AU-WilliamMultilingualNeural |
| Doraemon | Doraemon | Explainer | en-GB-ThomasNeural |
| Light Yagami | Death Note | Explainer | en-GB-RyanNeural |
| Gojo | Jujutsu Kaisen | Explainer | en-US-AndrewMultilingualNeural |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **AI Script Generation** | Google Gemini 2.5 Flash |
| **Text-to-Speech** | Edge TTS (Microsoft Neural voices) |
| **Video Assembly** | FFmpeg (libx264, libass, amix) |
| **Agent Orchestration** | LangGraph |
| **Data Validation** | Pydantic v2 |
| **Character Images** | Pollinations AI + rembg |
| **Retry Logic** | Tenacity (exponential backoff) |
| **Config** | YAML + python-dotenv |

---

## 📋 Configuration

All pipeline settings are in `config.yaml`:

- **50 tech topics** — weighted random selection, history-aware
- **5 anime characters** — with roles, voices, and image folders
- **3 daily upload slots** — configurable schedule
- **Video specs** — 1080×1920, 30fps, AAC audio

---

## 🧪 Testing

```bash
# Phase 1: Test TTS + FFmpeg only (no API key needed)
python scripts/test_phase1.py

# Phase 2: Full pipeline with Gemini (needs API key)
python scripts/test_phase2.py
```

---

## 📝 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `TELEGRAM_BOT_TOKEN` | ❌ | Telegram bot for failure alerts |
| `TELEGRAM_CHAT_ID` | ❌ | Telegram chat for alerts |

---

## ⚠️ Notes

- Free-tier Gemini API has rate limits — the pipeline includes exponential backoff retry logic
- Character images are generated once and cached locally — the daily pipeline never depends on Pollinations at runtime
- Videos are 1080×1920 vertical format optimized for YouTube Shorts
- The `history.json` file prevents topic/character pair repetition across runs

---

## 📄 License

MIT
