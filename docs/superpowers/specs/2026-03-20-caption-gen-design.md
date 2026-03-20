# caption-gen: Stylized Animated Caption Video Generator

## Overview

A Python CLI tool that takes a background image and a text script, generates speech audio via a configurable TTS provider, and produces a vertical (1080x1920) video with stylized word-by-word animated captions optimized for TikTok.

## Inputs & Outputs

**Required inputs:**
- `--image`: Background image file (must be exactly 1080x1920 PNG/JPG)
- `--script`: Text file containing the narration script
- `--tts`: TTS provider to use (`elevenlabs`, `openai`, or `google`)

**Optional inputs:**
- `--output`: Output video path (default: `./output.mp4`)
- `--highlight-color`: Hex color for the active word highlight (default: `#FFD700` gold)
- `--font-size`: Caption font size in pixels (default: `48`)
- `--voice`: Voice identifier for the TTS provider (default varies by provider, see TTS Providers section)

**Output:**
- MP4 video (H.264 + AAC), 1080x1920, with animated captions and generated audio

**API keys** are read from environment variables:
- `ELEVENLABS_API_KEY` for ElevenLabs
- `OPENAI_API_KEY` for OpenAI TTS
- `GOOGLE_APPLICATION_CREDENTIALS` for Google Cloud TTS

## Pipeline

```
Step 1: Validate inputs
  - Image must be exactly 1080x1920
  - Script file must exist and be non-empty
  - API key for chosen TTS provider must be set

Step 2: Generate audio + word timestamps via TTS
  - Send script text to chosen TTS provider API
  - Receive: audio bytes + word-level timestamps
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

## TTS Providers

Each provider is implemented as a module in `tts/` with a common interface:
```python
def generate(text: str, voice: str | None = None) -> tuple[bytes, list[dict]]:
    """Returns (audio_bytes, [{"word": str, "start": float, "end": float}, ...])"""
```

### ElevenLabs
- API: `POST /v1/text-to-speech/{voice_id}/with-timestamps`
- Returns: audio bytes (MP3) + word-level alignment data with start and end times per word
- Word timestamps included in `alignment` field of response
- Default voice: `"Rachel"` (voice_id looked up via API if name given)
- Requires: `ELEVENLABS_API_KEY` env var

### OpenAI TTS
- API: `client.audio.speech.create()` generates audio only — **no word-level timestamps are returned**
- **Fallback strategy:** After generating audio, use `faster-whisper` to transcribe the generated audio and extract word-level timestamps. Since the text is known, alignment is straightforward (the words will match closely). This is the only provider that requires Whisper.
- Default voice: `"alloy"`
- Requires: `OPENAI_API_KEY` env var
- Additional dependency: `faster-whisper` (only installed/used when OpenAI TTS is selected)

### Google Cloud TTS
- API: `texttospeech.synthesize_speech()` with `enable_time_pointing=["SSML_MARK"]`
- Uses SSML `<mark>` tags around each word to get timepoints
- **Note:** Timepoints provide word **start** times only, not end times. End times are derived by setting each word's `end` to the next word's `start`. The last word's `end` is set to the total audio duration.
- Default voice: `"en-US-Neural2-D"`
- Requires: `GOOGLE_APPLICATION_CREDENTIALS` env var pointing to service account JSON

## Project Structure

```
~/projects/caption-gen/
├── caption_gen.py          # CLI entry point (argparse) + pipeline orchestration
├── tts/
│   ├── __init__.py         # TTS provider interface + factory function
│   ├── elevenlabs.py       # ElevenLabs TTS implementation
│   ├── openai_tts.py       # OpenAI TTS implementation
│   └── google_tts.py       # Google Cloud TTS implementation
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
- `elevenlabs` — ElevenLabs Python SDK (for ElevenLabs TTS)
- `openai` — OpenAI Python SDK (for OpenAI TTS)
- `google-cloud-texttospeech` — Google Cloud TTS SDK
- `faster-whisper` — word-level timestamp extraction (only used with OpenAI TTS provider)
- `argparse` — CLI argument parsing (stdlib)

## Error Handling

- Image not 1080x1920: exit with clear error message stating required dimensions
- Missing API key: exit with message naming the required env var
- TTS API failure: exit with the provider's error message
- Empty script: exit with error
- Invalid audio format from TTS: exit with error

## Constraints

- Whisper is only used as a fallback for OpenAI TTS (which doesn't provide word-level timestamps natively)
- Image must be exactly 1080x1920 — no resizing, cropping, or padding
- Single caption style (word-by-word highlight) — no multi-style support
- Font is bundled — no system font dependency
