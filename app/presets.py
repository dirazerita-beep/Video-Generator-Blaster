"""TikTok 9:16 preset constants, font sizes, and color definitions."""

# Target resolution for TikTok
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920

# Aspect ratio
ASPECT_RATIO = TARGET_WIDTH / TARGET_HEIGHT  # ~0.5625 (9:16)

# Default font sizes
FONT_SIZE_MIN = 16
FONT_SIZE_MAX = 72
FONT_SIZE_DEFAULT = 36

# Default text color (white)
TEXT_COLOR_DEFAULT = "white"

# Default intro/outro background color
BG_COLOR_DEFAULT = "#000000"

# Default intro/outro durations
INTRO_DUR_DEFAULT = 1.5
OUTRO_DUR_DEFAULT = 1.5
INTRO_DUR_MIN = 0.0
INTRO_DUR_MAX = 5.0

# Default audio volumes (0–100)
TTS_VOLUME_DEFAULT = 80
MUSIC_VOLUME_DEFAULT = 30

# Default segment count for shuffling
SEGMENT_COUNT_DEFAULT = 4
SEGMENT_COUNT_MIN = 2
SEGMENT_COUNT_MAX = 10

# Fade duration for music (seconds)
MUSIC_FADE_DURATION = 2.0

# Number of variations bounds
VARIATIONS_MIN = 1
VARIATIONS_MAX = 9999
VARIATIONS_DEFAULT = 10

# Text positions
TEXT_POSITIONS = ["Top", "Center", "Bottom"]

# Reframe modes
REFRAME_MODES = {
    "blur": "Blur Background",
    "crop": "Crop Center",
    "fit": "Fit + Padding",
}

# TTS modes
TTS_MODES = {
    "disabled": "Disabled",
    "sapi": "Offline (Windows SAPI)",
    "openai": "Online - OpenAI TTS",
    "azure": "Online - Azure Speech",
    "elevenlabs": "Online - ElevenLabs",
}

# OpenAI TTS voices and models
OPENAI_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
OPENAI_MODELS = ["tts-1", "tts-1-hd"]

# Hook text display duration (seconds)
HOOK_DISPLAY_DURATION = 3.0

# Benefit text display: starts at 40% of video duration
BENEFIT_START_RATIO = 0.4
BENEFIT_DISPLAY_DURATION = 3.0

# CTA text display: starts 3 seconds before end
CTA_SECONDS_BEFORE_END = 3.0
CTA_DISPLAY_DURATION = 3.0

# Supported video extensions
VIDEO_EXTENSIONS = ["mp4", "mov", "avi", "mkv"]

# Supported music extensions
MUSIC_EXTENSIONS = ["mp3", "wav"]

# Output filename template
OUTPUT_FILENAME_TEMPLATE = "variation_{:03d}.mp4"

# Config file name
CONFIG_FILENAME = "config.json"

# Temp directory name inside output folder
TEMP_DIR_NAME = "temp"
