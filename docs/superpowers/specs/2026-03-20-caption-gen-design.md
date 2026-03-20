# caption-gen: Stylized Animated Caption Video Generator

## Overview

A Python CLI tool that takes a background image and a text script, generates speech audio via ElevenLabs TTS, and produces a vertical (1080x1920) video with stylized word-by-word animated captions optimized for TikTok.

## Inputs & Outputs

**Required inputs:**
- `--image`: Background image file (must be exactly 1080x1920 PNG/JPG)
- `--script`: Text file containing the narration script

**Optional inputs:**
- `--output`: Output video path (default: `./output.mp4`)
- `--highlight-color`: Hex color for the active word highlight (default: `#FFD700` gold)
- `--font-size`: Caption font size in pixels (default: `48`)
- `--voice`: ElevenLabs voice name (default: `"Rachel"`)

**Output:**
- MP4 video (H.264 + AAC), 1080x1920, with animated captions and generated audio

**API key:** `ELEVENLABS_API_KEY` environment variable

## Pipeline

```
Step 1: Validate inputs
  - Image must be exactly 1080x1920
  - Script file must exist and be non-empty
  - ELEVENLABS_API_KEY must be set

Step 2: Generate audio + word timestamps via ElevenLabs TTS
  - POST /v1/text-to-speech/{voice_id}/with-timestamps
  - Receive: audio bytes (MP3) + word-level alignment data (start + end per word)
  - Output: audio file + [{word, start, end}, ...]

Step 3: Group words into caption pages (3-5 words each)
  - New page when: word count hits 5, OR audio gap > 300ms between words
  - Minimum 2 words per page (a single word merges with the next group)
  - Each page: list of {word, start, end} entries

Step 4: Render caption overlays with Pillow
  - For each unique caption state (page + highlighted word), render a text overlay
  - Font: Oswald Bold, uppercase
  - Colors: white for inactive words, gold (#FFD700) for active word
  - Effects: 2px black outline stroke + drop shadow (4px offset, 50% opacity black)
  - Position: centered horizontally, ~40% from top (TikTok safe zone)
  - Only re-render when the highlighted word changes or a new page appears

Step 5: Composite video with MoviePy
  - Base layer: static background image (1080x1920)
  - Overlay layer: caption frames composited at correct timestamps
  - Audio track: generated TTS audio
  - Encoding: H.264 video + AAC audio
  - Output: MP4 file
```

## Caption Style

- **Animation type:** Word-by-word highlight. All words on the current page are visible; the currently-spoken word is highlighted in gold while others remain white.
- **Font:** Oswald Bold (bundled .ttf file, Google Fonts OFL license)
- **Text transform:** Uppercase
- **Text effects:** Black outline stroke (2px) + drop shadow (4px, rgba(0,0,0,0.5))
- **Highlight color:** Gold (#FFD700) by default, configurable via `--highlight-color`
- **Words per page:** 3-5, breaking at natural pauses. Minimum 2 words per page.
- **Position:** Centered horizontally, approximately 40% from top of frame. This avoids TikTok's UI overlays (bottom ~270px for username/description/nav, right ~100px for interaction buttons, top ~150px for status bar).

## ElevenLabs TTS Integration

- API endpoint: `POST /v1/text-to-speech/{voice_id}/with-timestamps`
- Returns: audio bytes (MP3) + alignment data with character/word-level start and end times
- Voice lookup: if `--voice` is a name (e.g., "Rachel"), look up the voice_id via the ElevenLabs voices API; if it's already a voice_id, use it directly
- Default voice: `"Rachel"`
- Requires: `ELEVENLABS_API_KEY` env var

The TTS module exposes:
```python
def generate(text: str, voice: str = "Rachel") -> tuple[bytes, list[dict]]:
    """Returns (audio_bytes, [{"word": str, "start": float, "end": float}, ...])"""
```

## Project Structure

```
~/projects/caption-gen/
├── caption_gen.py          # CLI entry point (argparse) + pipeline orchestration
├── tts.py                  # ElevenLabs TTS: audio generation + word timestamps
├── renderer.py             # Pillow text rendering (caption overlay generation)
├── compositor.py           # MoviePy video composition (image + captions + audio → MP4)
├── requirements.txt        # Python dependencies
└── fonts/
    └── Oswald-Bold.ttf     # Bundled font (OFL license)
```

## Dependencies

- `moviepy` — video composition, audio muxing, MP4 encoding
- `Pillow` — text rendering with font, stroke, shadow support
- `numpy` — array operations for frame handling
- `elevenlabs` — ElevenLabs Python SDK
- `requests` — HTTP requests (for voice lookup if not in SDK)
- `argparse` — CLI argument parsing (stdlib)

## Error Handling

- Image not 1080x1920: exit with clear error message stating required dimensions
- Missing `ELEVENLABS_API_KEY`: exit with message naming the required env var
- ElevenLabs API failure: exit with the API's error message
- Empty script: exit with error
- Invalid voice name: exit with error listing available voices

## Constraints

- ElevenLabs only — no other TTS providers
- No Whisper dependency — timestamps come directly from ElevenLabs
- Image must be exactly 1080x1920 — no resizing, cropping, or padding
- Single caption style (word-by-word highlight) — no multi-style support
- Font is bundled — no system font dependency
