# Video Generator Blaster

A **portable Windows GUI application** that takes **1 input video** and generates **N creative variations** optimised for **TikTok 9:16 (1080×1920)**.

Each variation is genuinely different: different hooks, text overlays, audio tracks, segment order, and intro/outro — making this a legitimate creative repurposing tool, not a spam utility.

---

## Features

- 🎬 **Reframe to 9:16** — Blur Background, Crop Center, or Fit + Padding modes
- 📝 **Randomised Text Overlays** — Hooks, Benefits, and CTA texts drawn from your list
- 🔀 **Segment Shuffling** — Split and re-order video segments per variation
- 🎤 **Text-to-Speech (TTS)** — Offline SAPI, OpenAI, Azure Speech, or ElevenLabs
- 🎵 **Background Music** — Pick a folder; each variation uses a random track
- 🎞️ **Intro / Outro Slides** — Solid-colour slides with overlay text
- ⚙️ **Config Persistence** — All settings auto-saved to `config.json`
- 📦 **Portable Build** — One-click PyInstaller `.exe` via `build_portable.bat`

---

## Screenshots

*(Screenshots will be added after first run)*

---

## Quick Start (Portable)

1. Download the latest release ZIP from the [Releases](../../releases) page.
2. Extract to any folder.
3. Place `ffmpeg.exe` and `ffprobe.exe` in `third_party/ffmpeg/`.
4. Run `VideoGeneratorBlaster.exe`.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Only needed for source install |
| FFmpeg | 6.x+ | Place in `third_party/ffmpeg/` or add to PATH |
| Windows | 10 / 11 | Required for Windows SAPI TTS; other features work cross-platform |

### Getting FFmpeg

Download the Windows build from https://www.gyan.dev/ffmpeg/builds/ (ffmpeg-release-essentials.zip).
Extract `ffmpeg.exe` and `ffprobe.exe` into:

```
Video-Generator-Blaster/
└── third_party/
    └── ffmpeg/
        ├── ffmpeg.exe
        └── ffprobe.exe
```

---

## Installation (Source)

```bash
git clone https://github.com/dirazerita-beep/Video-Generator-Blaster.git
cd Video-Generator-Blaster
pip install -r requirements.txt
python app/main.py
```

---

## Usage

### 1. Input / Output
- **Input Video** — Click *Browse…* to select an MP4/MOV/AVI/MKV file.
- **Output Folder** — Where the `variation_001.mp4`, `variation_002.mp4`, … files will be saved.
- **Number of Variations** — How many unique versions to produce (1–9999).

### 2. Reframe Mode
| Mode | Description |
|---|---|
| **Blur Background** | Original video centred on a blurred full-frame background (default) |
| **Crop Center** | Centre-crop to 9:16 |
| **Fit + Padding** | Fit inside 1080×1920 with black padding |

### 3. Text Overlays
- **Hook Texts** — Shown in the first 3 seconds of each variation (top of frame).
- **Benefit Texts** — Shown around 40% into the video duration.
- **CTA Texts** — Shown in the last 3 seconds.
- Enter one text per line; each variation picks a random entry.
- Adjust **Font Size**, **Font Color**, **Position**, and the **shadow/outline** toggle.

### 4. Segment Shuffling
- Enable to split the video into N equal segments and reassemble in a random order.
- Useful for creating structurally different edit rhythms.

### 5. Intro / Outro
- Solid-colour slides at the start and/or end of each variation.
- Duration can be 0–5 seconds each.
- Hook text is used for the intro; CTA text for the outro.

### 6. Audio / TTS

#### TTS Modes
| Mode | Description |
|---|---|
| **Disabled** | No TTS audio added |
| **Offline (Windows SAPI)** | Uses Windows built-in voices via pyttsx3 (no internet required) |
| **Online - OpenAI TTS** | Uses OpenAI's TTS API |
| **Online - Azure Speech** | Uses Azure Cognitive Services Speech |
| **Online - ElevenLabs** | Uses ElevenLabs voice cloning API |

Enter one TTS script per line in the *TTS Scripts* box. Each variation picks a script at random.

#### Background Music
- Select a folder containing `.mp3` or `.wav` files.
- Each variation picks a random track.
- Adjust **Music Volume** (0–100) and enable **Fade in/out** (2-second fades).

### 7. Generate
- Click **Generate Variations** to start.
- Monitor progress via the progress bar and log area.
- Click **Cancel** to stop after the current variation finishes.

---

## Building the Portable Version

Requirements: Python 3.11+, pip

```bat
build_portable.bat
```

The portable `.exe` and all dependencies will be in `dist\VideoGeneratorBlaster\`.

> **Note:** You still need to copy `ffmpeg.exe` and `ffprobe.exe` into
> `dist\VideoGeneratorBlaster\third_party\ffmpeg\` for the portable build.

---

## TTS Setup Guide

### Offline (Windows SAPI)
No setup required. Windows built-in voices are used automatically.
Additional voices can be installed via *Windows Settings -> Time & Language -> Speech*.

### OpenAI TTS
1. Create an account at https://platform.openai.com/
2. Generate an API key at https://platform.openai.com/api-keys
3. Paste the key into the *API Key* field in the app.
4. Select a voice (alloy, echo, fable, onyx, nova, shimmer) and model (tts-1 or tts-1-hd).

### Azure Cognitive Services Speech
1. Create an Azure account at https://azure.microsoft.com/
2. Create a *Speech* resource in the Azure portal.
3. Copy the subscription key and region.
4. Paste into the *API Key* and *Region* fields in the app.
5. Enter a voice name, e.g. `en-US-JennyNeural`.

### ElevenLabs
1. Create an account at https://elevenlabs.io/
2. Go to *Profile -> API Key* to get your key.
3. Find your Voice ID on the *Voices* page.
4. Paste both into the app.

---

## Project Structure

```
Video-Generator-Blaster/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── ui_main.py               # Main window (PySide6)
│   ├── worker.py                # QThread generation worker
│   ├── ffmpeg_runner.py         # FFmpeg wrapper
│   ├── variations.py            # Variation recipe generator
│   ├── presets.py               # TikTok 9:16 constants
│   └── tts/
│       ├── __init__.py
│       ├── base.py              # Abstract TTS interface
│       ├── sapi_tts.py          # Windows SAPI
│       ├── openai_tts.py        # OpenAI TTS
│       ├── azure_tts.py         # Azure Speech
│       └── elevenlabs_tts.py    # ElevenLabs
├── assets/
│   └── fonts/
├── third_party/
│   └── ffmpeg/                  # Place ffmpeg.exe + ffprobe.exe here
├── requirements.txt
├── build_portable.bat
└── README.md
```

---

## License

MIT License
