# caption-gen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that takes an image + text script, generates speech via ElevenLabs, and outputs a 1080x1920 TikTok-optimized video with word-by-word highlighted captions.

**Architecture:** Linear pipeline: validate inputs → ElevenLabs TTS (audio + character timestamps) → aggregate to word timestamps → group words into 3-5 word pages → render caption overlays with Pillow → composite video with MoviePy. Each pipeline stage is a separate module with a clean interface.

**Tech Stack:** Python 3.10+, ElevenLabs SDK, Pillow, MoviePy 2.x, NumPy, pytest

**Spec:** `docs/superpowers/specs/2026-03-20-caption-gen-design.md`

---

## File Structure

```
~/projects/caption-gen/
├── caption_gen.py       # CLI (argparse) + pipeline orchestration + word grouping
├── tts.py               # ElevenLabs TTS: generate audio + character-to-word timestamps
├── renderer.py          # Pillow: render caption overlay images (RGBA)
├── compositor.py        # MoviePy: composite background + caption clips + audio → MP4
├── requirements.txt     # Dependencies
├── fonts/
│   └── Oswald-Bold.ttf  # Bundled font (Google Fonts, OFL license)
└── tests/
    ├── test_tts.py
    ├── test_grouping.py
    ├── test_renderer.py
    ├── test_compositor.py
    └── test_integration.py
```

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `fonts/Oswald-Bold.ttf` (downloaded)
- Create: `tests/` directory

- [ ] **Step 1: Create requirements.txt**

```
moviepy>=2.0
Pillow>=10.0
numpy>=1.24
elevenlabs>=1.0
pytest>=7.0
```

- [ ] **Step 2: Download Oswald Bold font**

Run:
```bash
mkdir -p ~/projects/caption-gen/fonts
curl -L -o ~/projects/caption-gen/fonts/Oswald-Bold.ttf \
  "https://github.com/google/fonts/raw/main/ofl/oswald/static/Oswald-Bold.ttf"
```
Expected: File downloaded (~40-50 KB)

- [ ] **Step 3: Create tests directory**

Run:
```bash
mkdir -p ~/projects/caption-gen/tests
```

- [ ] **Step 4: Install dependencies**

Run:
```bash
cd ~/projects/caption-gen && pip install -r requirements.txt
```
Expected: All packages install successfully

- [ ] **Step 5: Commit**

```bash
cd ~/projects/caption-gen
git add requirements.txt fonts/Oswald-Bold.ttf
git commit -m "chore: add project dependencies and bundled Oswald Bold font"
```

---

### Task 2: TTS Module — ElevenLabs Audio + Word Timestamps

**Files:**
- Create: `tts.py`
- Create: `tests/test_tts.py`

The ElevenLabs `/with-timestamps` endpoint returns **character-level** timing:
```json
{
  "audio_base64": "...",
  "alignment": {
    "characters": ["T", "h", "i", "s", " ", "i", "s"],
    "character_start_times_seconds": [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3],
    "character_end_times_seconds": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35]
  }
}
```

We must aggregate characters into words. The `generate()` function returns `(audio_bytes, [{"word": str, "start": float, "end": float}, ...])`.

- [ ] **Step 1: Write failing tests for character-to-word aggregation**

```python
# tests/test_tts.py
from tts import chars_to_words


def test_single_word():
    chars = ["H", "i"]
    starts = [0.0, 0.05]
    ends = [0.05, 0.1]
    result = chars_to_words(chars, starts, ends)
    assert result == [{"word": "Hi", "start": 0.0, "end": 0.1}]


def test_two_words():
    chars = ["H", "i", " ", "y", "o"]
    starts = [0.0, 0.05, 0.1, 0.15, 0.2]
    ends = [0.05, 0.1, 0.15, 0.2, 0.25]
    result = chars_to_words(chars, starts, ends)
    assert result == [
        {"word": "Hi", "start": 0.0, "end": 0.1},
        {"word": "yo", "start": 0.15, "end": 0.25},
    ]


def test_multiple_spaces():
    chars = ["A", " ", " ", "B"]
    starts = [0.0, 0.1, 0.2, 0.3]
    ends = [0.1, 0.2, 0.3, 0.4]
    result = chars_to_words(chars, starts, ends)
    assert result == [
        {"word": "A", "start": 0.0, "end": 0.1},
        {"word": "B", "start": 0.3, "end": 0.4},
    ]


def test_punctuation_attached():
    chars = ["H", "i", ",", " ", "y", "o"]
    starts = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25]
    ends = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
    result = chars_to_words(chars, starts, ends)
    assert result == [
        {"word": "Hi,", "start": 0.0, "end": 0.15},
        {"word": "yo", "start": 0.2, "end": 0.3},
    ]


def test_empty_input():
    assert chars_to_words([], [], []) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_tts.py -v`
Expected: FAIL — `ImportError: cannot import name 'chars_to_words' from 'tts'`

- [ ] **Step 3: Implement chars_to_words**

```python
# tts.py
import base64
import os

from elevenlabs import ElevenLabs


def chars_to_words(
    characters: list[str],
    start_times: list[float],
    end_times: list[float],
) -> list[dict]:
    """Aggregate character-level timestamps into word-level timestamps."""
    words = []
    current_word = ""
    word_start = None
    word_end = None

    for char, start, end in zip(characters, start_times, end_times):
        if char == " ":
            if current_word:
                words.append(
                    {"word": current_word, "start": word_start, "end": word_end}
                )
                current_word = ""
                word_start = None
                word_end = None
        else:
            if word_start is None:
                word_start = start
            current_word += char
            word_end = end

    if current_word:
        words.append({"word": current_word, "start": word_start, "end": word_end})

    return words
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_tts.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Write test for generate() with mocked API**

Add to `tests/test_tts.py`:

```python
from unittest.mock import patch, MagicMock
from tts import generate


def test_generate_returns_audio_and_words():
    mock_response = MagicMock()
    mock_response.audio_base64 = base64.b64encode(b"fake-audio").decode()
    mock_response.alignment = MagicMock()
    mock_response.alignment.characters = ["H", "i", " ", "y", "o"]
    mock_response.alignment.character_start_times_seconds = [0.0, 0.1, 0.2, 0.3, 0.4]
    mock_response.alignment.character_end_times_seconds = [0.1, 0.2, 0.3, 0.4, 0.5]

    mock_client = MagicMock()
    mock_client.text_to_speech.convert_with_timestamps.return_value = mock_response

    # Mock voice lookup
    mock_voice = MagicMock()
    mock_voice.voice_id = "test-voice-id"
    mock_voice.name = "Rachel"
    mock_client.voices.get_all.return_value.voices = [mock_voice]

    with patch("tts.ElevenLabs", return_value=mock_client):
        audio_bytes, words = generate("Hi yo", voice="Rachel")

    assert audio_bytes == b"fake-audio"
    assert len(words) == 2
    assert words[0]["word"] == "Hi"
    assert words[1]["word"] == "yo"


# Need this import at the top of the file
import base64
```

- [ ] **Step 6: Implement generate()**

Add to `tts.py`:

```python
def _get_voice_id(client: ElevenLabs, voice_name: str) -> str:
    """Look up voice_id by name. If voice_name looks like an ID, return it directly."""
    # If it looks like a voice ID (long alphanumeric string), use it directly
    if len(voice_name) > 15 and voice_name.isalnum():
        return voice_name

    response = client.voices.get_all()
    for voice in response.voices:
        if voice.name.lower() == voice_name.lower():
            return voice.voice_id

    available = [v.name for v in response.voices]
    raise ValueError(
        f"Voice '{voice_name}' not found. Available voices: {', '.join(available)}"
    )


def generate(text: str, voice: str = "Rachel") -> tuple[bytes, list[dict]]:
    """Generate speech audio and word-level timestamps via ElevenLabs.

    Returns (audio_bytes, [{"word": str, "start": float, "end": float}, ...])
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY environment variable is not set. "
            "Get your API key at https://elevenlabs.io"
        )

    client = ElevenLabs(api_key=api_key)
    voice_id = _get_voice_id(client, voice)

    result = client.text_to_speech.convert_with_timestamps(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    audio_bytes = base64.b64decode(result.audio_base64)

    words = chars_to_words(
        list(result.alignment.characters),
        list(result.alignment.character_start_times_seconds),
        list(result.alignment.character_end_times_seconds),
    )

    return audio_bytes, words
```

- [ ] **Step 7: Run all TTS tests**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_tts.py -v`
Expected: All 6 tests PASS

- [ ] **Step 8: Commit**

```bash
cd ~/projects/caption-gen
git add tts.py tests/test_tts.py
git commit -m "feat: add TTS module with ElevenLabs integration and character-to-word aggregation"
```

---

### Task 3: Word Grouping into Caption Pages

**Files:**
- Create: `tests/test_grouping.py`
- Modify: `caption_gen.py` (will be created with just the grouping function for now)

The grouping function lives in `caption_gen.py` since it's part of pipeline orchestration.

Rules:
- New page when word count reaches 5 OR audio gap > 300ms between words
- Minimum 2 words per page (1-word pages merge with the next group; trailing 1-word page merges backward)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_grouping.py
from caption_gen import group_words


def _w(word, start, end):
    """Helper to create word dicts."""
    return {"word": word, "start": start, "end": end}


def test_basic_grouping_under_max():
    words = [_w("a", 0, 0.2), _w("b", 0.3, 0.5), _w("c", 0.6, 0.8)]
    pages = group_words(words)
    assert len(pages) == 1
    assert len(pages[0]) == 3


def test_splits_at_max_words():
    words = [_w(f"w{i}", i * 0.3, i * 0.3 + 0.2) for i in range(8)]
    pages = group_words(words)
    assert len(pages[0]) == 5
    assert len(pages[1]) == 3


def test_splits_at_gap():
    words = [
        _w("a", 0.0, 0.2),
        _w("b", 0.3, 0.5),
        # gap of 0.5s > 0.3s threshold
        _w("c", 1.0, 1.2),
        _w("d", 1.3, 1.5),
    ]
    pages = group_words(words)
    assert len(pages) == 2
    assert [w["word"] for w in pages[0]] == ["a", "b"]
    assert [w["word"] for w in pages[1]] == ["c", "d"]


def test_single_word_does_not_split():
    """A gap after word 1 should NOT create a 1-word page."""
    words = [
        _w("a", 0.0, 0.2),
        # gap > 300ms
        _w("b", 0.8, 1.0),
        _w("c", 1.1, 1.3),
    ]
    pages = group_words(words)
    # "a" alone would be 1 word — should NOT split, merges with next
    assert len(pages) == 1
    assert len(pages[0]) == 3


def test_trailing_single_word_merges_backward():
    words = [
        _w("a", 0.0, 0.2),
        _w("b", 0.3, 0.5),
        _w("c", 0.6, 0.8),
        _w("d", 0.9, 1.1),
        _w("e", 1.2, 1.4),
        _w("f", 1.5, 1.7),
    ]
    pages = group_words(words)
    # Page 1: 5 words, trailing "f" merges backward → page 1 has 6 words
    assert len(pages) == 1
    total = sum(len(p) for p in pages)
    assert total == 6


def test_two_words():
    words = [_w("a", 0.0, 0.2), _w("b", 0.3, 0.5)]
    pages = group_words(words)
    assert len(pages) == 1
    assert len(pages[0]) == 2


def test_single_word_input():
    words = [_w("a", 0.0, 0.2)]
    pages = group_words(words)
    assert len(pages) == 1
    assert len(pages[0]) == 1


def test_empty_input():
    assert group_words([]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_grouping.py -v`
Expected: FAIL — `ImportError: cannot import name 'group_words'`

- [ ] **Step 3: Implement group_words**

Create `caption_gen.py` (with just the grouping function for now):

```python
# caption_gen.py


def group_words(
    words: list[dict],
    max_per_page: int = 5,
    gap_threshold: float = 0.3,
) -> list[list[dict]]:
    """Group words into caption pages of 3-5 words.

    Breaks at max_per_page words or at audio gaps > gap_threshold seconds.
    Ensures minimum 2 words per page (single words merge forward;
    trailing single words merge backward).
    """
    if not words:
        return []

    pages: list[list[dict]] = []
    current: list[dict] = []

    for i, word in enumerate(words):
        current.append(word)

        is_last = i == len(words) - 1
        at_max = len(current) >= max_per_page
        has_gap = not is_last and words[i + 1]["start"] - word["end"] > gap_threshold

        if is_last:
            pages.append(current)
            current = []
        elif at_max or has_gap:
            if len(current) >= 2:
                pages.append(current)
                current = []
            # else: only 1 word, don't break — let it merge with next words

    # Merge trailing single-word page backward
    if len(pages) > 1 and len(pages[-1]) == 1:
        single = pages.pop()
        pages[-1].extend(single)

    return pages
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_grouping.py -v`
Expected: All tests PASS. Fix `test_trailing_single_word_merges_backward` assertion if needed — after merging backward, the last page has 6 words, so `len(pages) == 1` with 6 words.

- [ ] **Step 5: Commit**

```bash
cd ~/projects/caption-gen
git add caption_gen.py tests/test_grouping.py
git commit -m "feat: add word grouping logic for caption pages"
```

---

### Task 4: Caption Renderer (Pillow)

**Files:**
- Create: `renderer.py`
- Create: `tests/test_renderer.py`

Renders RGBA overlay images (1080px wide) with styled caption text. For each caption state (page + which word is highlighted), produces a transparent PNG-like image that can be composited over the background.

**Style:** Oswald Bold, uppercase, white text, gold (#FFD700) highlight on active word, 2px black stroke, 4px drop shadow.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_renderer.py
import os
from renderer import render_caption

FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "fonts", "Oswald-Bold.ttf")


def _w(word, start=0.0, end=0.1):
    return {"word": word, "start": start, "end": end}


def test_returns_rgba_image():
    words = [_w("hello"), _w("world")]
    img = render_caption(words, highlight_index=0, font_path=FONT_PATH)
    assert img.mode == "RGBA"


def test_image_width_is_1080():
    words = [_w("hello"), _w("world")]
    img = render_caption(words, highlight_index=0, font_path=FONT_PATH)
    assert img.width == 1080


def test_image_is_not_fully_transparent():
    words = [_w("hello"), _w("world")]
    img = render_caption(words, highlight_index=0, font_path=FONT_PATH)
    # At least some pixels should have non-zero alpha
    alpha_channel = img.split()[3]
    assert alpha_channel.getextrema()[1] > 0


def test_different_highlight_produces_different_image():
    words = [_w("hello"), _w("world")]
    img1 = render_caption(words, highlight_index=0, font_path=FONT_PATH)
    img2 = render_caption(words, highlight_index=1, font_path=FONT_PATH)
    assert list(img1.getdata()) != list(img2.getdata())


def test_custom_highlight_color():
    words = [_w("hello"), _w("world")]
    img = render_caption(
        words, highlight_index=0, font_path=FONT_PATH, highlight_color="#FF0000"
    )
    assert img.mode == "RGBA"


def test_custom_font_size():
    words = [_w("hello"), _w("world")]
    img_small = render_caption(
        words, highlight_index=0, font_path=FONT_PATH, font_size=32
    )
    img_large = render_caption(
        words, highlight_index=0, font_path=FONT_PATH, font_size=64
    )
    # Larger font should produce a taller image
    assert img_large.height > img_small.height
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_renderer.py -v`
Expected: FAIL — `ImportError: cannot import name 'render_caption'`

- [ ] **Step 3: Implement render_caption**

```python
# renderer.py
from PIL import Image, ImageDraw, ImageFont


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def render_caption(
    words: list[dict],
    highlight_index: int,
    font_path: str,
    font_size: int = 48,
    highlight_color: str = "#FFD700",
    width: int = 1080,
) -> Image.Image:
    """Render a caption overlay as a transparent RGBA image.

    All words are shown in uppercase. The word at highlight_index is
    rendered in highlight_color; all others in white. Text has a 2px
    black stroke and a 4px drop shadow.

    Args:
        words: List of word dicts (only "word" key is used here).
        highlight_index: Index of the word to highlight.
        font_path: Path to the .ttf font file.
        font_size: Font size in pixels.
        highlight_color: Hex color for the highlighted word.
        width: Image width in pixels.

    Returns:
        RGBA PIL Image with transparent background and rendered text.
    """
    font = ImageFont.truetype(font_path, font_size)
    highlight_rgb = _hex_to_rgb(highlight_color)

    text_parts = [w["word"].upper() for w in words]
    space_width = font.getlength(" ")
    word_widths = [font.getlength(part) for part in text_parts]
    total_text_width = sum(word_widths) + space_width * (len(text_parts) - 1)

    ascent, descent = font.getmetrics()
    text_height = ascent + descent
    shadow_offset = 4
    stroke_width = 2
    padding = shadow_offset + stroke_width
    img_height = text_height + padding * 2

    img = Image.new("RGBA", (width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = (width - total_text_width) / 2
    y = padding  # top padding for stroke

    for i, (text, word_width) in enumerate(zip(text_parts, word_widths)):
        color = highlight_rgb if i == highlight_index else (255, 255, 255)

        # Drop shadow (offset, semi-transparent black)
        draw.text(
            (x + shadow_offset, y + shadow_offset),
            text,
            font=font,
            fill=(0, 0, 0, 128),
        )

        # Main text with stroke
        draw.text(
            (x, y),
            text,
            font=font,
            fill=color,
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0),
        )

        x += word_width + space_width

    return img
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_renderer.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/projects/caption-gen
git add renderer.py tests/test_renderer.py
git commit -m "feat: add Pillow caption renderer with highlight, stroke, and shadow"
```

---

### Task 5: Video Compositor (MoviePy)

**Files:**
- Create: `compositor.py`
- Create: `tests/test_compositor.py`

Takes the background image, audio bytes, caption pages, and a render function, then produces the final MP4 video using MoviePy 2.x.

**Caption timing logic:** Each word in each page becomes a clip. Its start time is `word["start"]`. Its end time is the next word's start (same page), the next page's first word start (last word in page), or the word's own end time (last word of last page). This ensures smooth transitions with no gaps.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_compositor.py
import os
import tempfile
import numpy as np
from PIL import Image
from compositor import compose_video


FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "fonts", "Oswald-Bold.ttf")


def _create_test_image(path):
    """Create a 1080x1920 solid blue test image."""
    img = Image.new("RGB", (1080, 1920), (0, 0, 128))
    img.save(path)


def _create_silent_audio(path, duration=1.0, sample_rate=44100):
    """Create a silent WAV file for testing."""
    import wave
    import struct

    n_frames = int(duration * sample_rate)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))


def test_compose_produces_mp4():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "bg.png")
        audio_path = os.path.join(tmpdir, "audio.wav")
        output_path = os.path.join(tmpdir, "output.mp4")

        _create_test_image(img_path)
        _create_silent_audio(audio_path, duration=1.0)

        pages = [
            [
                {"word": "hello", "start": 0.0, "end": 0.4},
                {"word": "world", "start": 0.5, "end": 0.9},
            ]
        ]

        compose_video(
            image_path=img_path,
            audio_path=audio_path,
            pages=pages,
            font_path=FONT_PATH,
            output_path=output_path,
        )

        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0


def test_compose_video_resolution():
    """Output video should be 1080x1920."""
    from moviepy import VideoFileClip

    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "bg.png")
        audio_path = os.path.join(tmpdir, "audio.wav")
        output_path = os.path.join(tmpdir, "output.mp4")

        _create_test_image(img_path)
        _create_silent_audio(audio_path, duration=1.0)

        pages = [
            [
                {"word": "test", "start": 0.0, "end": 0.5},
                {"word": "video", "start": 0.5, "end": 1.0},
            ]
        ]

        compose_video(
            image_path=img_path,
            audio_path=audio_path,
            pages=pages,
            font_path=FONT_PATH,
            output_path=output_path,
        )

        clip = VideoFileClip(output_path)
        assert clip.size == [1080, 1920]
        clip.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_compositor.py -v`
Expected: FAIL — `ImportError: cannot import name 'compose_video'`

- [ ] **Step 3: Implement compose_video**

```python
# compositor.py
import numpy as np
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip
from renderer import render_caption


def compose_video(
    image_path: str,
    audio_path: str,
    pages: list[list[dict]],
    font_path: str,
    output_path: str,
    font_size: int = 48,
    highlight_color: str = "#FFD700",
    fps: int = 24,
) -> None:
    """Composite background image + caption overlays + audio into an MP4 video.

    Args:
        image_path: Path to 1080x1920 background image.
        audio_path: Path to audio file.
        pages: List of caption pages (each page is a list of word dicts).
        font_path: Path to the .ttf font file.
        output_path: Where to write the output MP4.
        font_size: Caption font size.
        highlight_color: Hex color for highlighted word.
        fps: Video frame rate.
    """
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    bg = ImageClip(image_path).with_duration(duration)

    # TikTok safe zone: ~40% from top = 768px
    y_position = int(1920 * 0.4)

    caption_clips = []
    for page_idx, page in enumerate(pages):
        for word_idx in range(len(page)):
            # Render this caption state
            overlay_img = render_caption(
                words=page,
                highlight_index=word_idx,
                font_path=font_path,
                font_size=font_size,
                highlight_color=highlight_color,
            )
            overlay_array = np.array(overlay_img)

            # Determine timing
            start = page[word_idx]["start"]
            if word_idx + 1 < len(page):
                # Not last word in page: show until next word starts
                end = page[word_idx + 1]["start"]
            elif page_idx + 1 < len(pages):
                # Last word in page: show until next page's first word
                end = pages[page_idx + 1][0]["start"]
            else:
                # Last word of last page: show until word ends
                end = page[word_idx]["end"]

            clip_duration = end - start
            if clip_duration <= 0:
                continue

            clip = (
                ImageClip(overlay_array)
                .with_duration(clip_duration)
                .with_start(start)
                .with_position((0, y_position))
            )
            caption_clips.append(clip)

    video = CompositeVideoClip([bg] + caption_clips)
    video = video.with_audio(audio)
    video.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        logger=None,  # suppress moviepy progress bar in tests
    )

    audio.close()
    video.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_compositor.py -v`
Expected: All 2 tests PASS (may take a few seconds for video encoding)

- [ ] **Step 5: Commit**

```bash
cd ~/projects/caption-gen
git add compositor.py tests/test_compositor.py
git commit -m "feat: add MoviePy video compositor with timed caption overlays"
```

---

### Task 6: CLI Entry Point

**Files:**
- Modify: `caption_gen.py` (add CLI and pipeline orchestration)
- Create: `tests/test_caption_gen.py`

Wire up the full pipeline: parse args → validate → TTS → group → composite.

- [ ] **Step 1: Write failing tests for input validation**

```python
# tests/test_caption_gen.py
import os
import tempfile
import pytest
from unittest.mock import patch
from caption_gen import validate_inputs


def test_validate_missing_image():
    with pytest.raises(SystemExit, match="not found"):
        validate_inputs("/nonexistent.png", "/tmp/script.txt")


def test_validate_wrong_image_dimensions():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        from PIL import Image

        img = Image.new("RGB", (800, 600))
        img.save(f.name)
        with pytest.raises(SystemExit, match="1080x1920"):
            validate_inputs(f.name, "/tmp/script.txt")
        os.unlink(f.name)


def test_validate_empty_script():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "bg.png")
        script_path = os.path.join(tmpdir, "script.txt")

        from PIL import Image

        Image.new("RGB", (1080, 1920)).save(img_path)

        with open(script_path, "w") as f:
            f.write("")

        with pytest.raises(SystemExit, match="empty"):
            validate_inputs(img_path, script_path)


def test_validate_missing_api_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "bg.png")
        script_path = os.path.join(tmpdir, "script.txt")

        from PIL import Image

        Image.new("RGB", (1080, 1920)).save(img_path)

        with open(script_path, "w") as f:
            f.write("Hello world")

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="ELEVENLABS_API_KEY"):
                validate_inputs(img_path, script_path)


def test_validate_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "bg.png")
        script_path = os.path.join(tmpdir, "script.txt")

        from PIL import Image

        Image.new("RGB", (1080, 1920)).save(img_path)

        with open(script_path, "w") as f:
            f.write("Hello world")

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
            text = validate_inputs(img_path, script_path)
            assert text == "Hello world"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_caption_gen.py -v`
Expected: FAIL — `ImportError: cannot import name 'validate_inputs'`

- [ ] **Step 3: Implement validate_inputs and CLI**

Update `caption_gen.py` — add validation and the main CLI:

```python
# caption_gen.py
import argparse
import os
import sys
import tempfile

from PIL import Image


def group_words(
    words: list[dict],
    max_per_page: int = 5,
    gap_threshold: float = 0.3,
) -> list[list[dict]]:
    """Group words into caption pages of 3-5 words.

    Breaks at max_per_page words or at audio gaps > gap_threshold seconds.
    Ensures minimum 2 words per page (single words merge forward;
    trailing single words merge backward).
    """
    if not words:
        return []

    pages: list[list[dict]] = []
    current: list[dict] = []

    for i, word in enumerate(words):
        current.append(word)

        is_last = i == len(words) - 1
        at_max = len(current) >= max_per_page
        has_gap = not is_last and words[i + 1]["start"] - word["end"] > gap_threshold

        if is_last:
            pages.append(current)
            current = []
        elif at_max or has_gap:
            if len(current) >= 2:
                pages.append(current)
                current = []

    if len(pages) > 1 and len(pages[-1]) == 1:
        single = pages.pop()
        pages[-1].extend(single)

    return pages


def validate_inputs(image_path: str, script_path: str) -> str:
    """Validate all inputs and return the script text.

    Calls sys.exit() with a descriptive message on any validation failure.
    """
    if not os.path.isfile(image_path):
        sys.exit(f"Error: Image file not found: {image_path}")

    img = Image.open(image_path)
    if img.size != (1080, 1920):
        sys.exit(
            f"Error: Image must be exactly 1080x1920, got {img.size[0]}x{img.size[1]}"
        )

    if not os.path.isfile(script_path):
        sys.exit(f"Error: Script file not found: {script_path}")

    with open(script_path, "r") as f:
        text = f.read().strip()

    if not text:
        sys.exit("Error: Script file is empty")

    if not os.environ.get("ELEVENLABS_API_KEY"):
        sys.exit(
            "Error: ELEVENLABS_API_KEY environment variable is not set. "
            "Get your API key at https://elevenlabs.io"
        )

    return text


def main():
    parser = argparse.ArgumentParser(
        description="Generate TikTok-style captioned videos from an image and script"
    )
    parser.add_argument("--image", required=True, help="Background image (1080x1920 PNG/JPG)")
    parser.add_argument("--script", required=True, help="Text file with narration script")
    parser.add_argument("--output", default="./output.mp4", help="Output video path (default: ./output.mp4)")
    parser.add_argument("--voice", default="Rachel", help="ElevenLabs voice name (default: Rachel)")
    parser.add_argument("--highlight-color", default="#FFD700", help="Highlight color hex (default: #FFD700)")
    parser.add_argument("--font-size", type=int, default=48, help="Caption font size (default: 48)")

    args = parser.parse_args()

    # Step 1: Validate
    script_text = validate_inputs(args.image, args.script)
    font_path = os.path.join(os.path.dirname(__file__), "fonts", "Oswald-Bold.ttf")

    # Step 2: Generate audio + word timestamps
    from tts import generate

    print("Generating speech audio...")
    audio_bytes, words = generate(script_text, voice=args.voice)
    print(f"  Got {len(words)} words with timestamps")

    # Step 3: Group words into pages
    pages = group_words(words)
    print(f"  Grouped into {len(pages)} caption pages")

    # Step 4 & 5: Render + composite video
    # Save audio to temp file for MoviePy
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_bytes)
        audio_path = f.name

    try:
        from compositor import compose_video

        print("Compositing video...")
        compose_video(
            image_path=args.image,
            audio_path=audio_path,
            pages=pages,
            font_path=font_path,
            output_path=args.output,
            font_size=args.font_size,
            highlight_color=args.highlight_color,
        )
        print(f"Done! Video saved to: {args.output}")
    finally:
        os.unlink(audio_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_caption_gen.py tests/test_grouping.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/projects/caption-gen
git add caption_gen.py tests/test_caption_gen.py
git commit -m "feat: add CLI entry point with input validation and pipeline orchestration"
```

---

### Task 7: End-to-End Integration Test

**Files:**
- Create: `tests/test_integration.py`

Tests the full pipeline with a mocked ElevenLabs API to avoid requiring real API credentials in CI.

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
import base64
import os
import struct
import tempfile
import wave
from unittest.mock import patch, MagicMock

from PIL import Image
from moviepy import VideoFileClip

from caption_gen import group_words, validate_inputs
from tts import generate
from compositor import compose_video


FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "fonts", "Oswald-Bold.ttf")


def _make_wav_bytes(duration=2.0, sample_rate=44100):
    """Create WAV audio bytes (silence)."""
    import io

    n_frames = int(duration * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))
    return buf.getvalue()


def _mock_elevenlabs_response():
    """Create a mock ElevenLabs TTS response with realistic timing."""
    text = "This is a test of the caption generator"
    chars = list(text)
    # ~0.05s per character
    starts = [i * 0.05 for i in range(len(chars))]
    ends = [(i + 1) * 0.05 for i in range(len(chars))]

    wav_bytes = _make_wav_bytes(duration=2.0)

    mock_response = MagicMock()
    mock_response.audio_base64 = base64.b64encode(wav_bytes).decode()
    mock_response.alignment = MagicMock()
    mock_response.alignment.characters = chars
    mock_response.alignment.character_start_times_seconds = starts
    mock_response.alignment.character_end_times_seconds = ends

    return mock_response


def test_full_pipeline():
    """Test the complete pipeline: TTS → group → render → composite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test inputs
        img_path = os.path.join(tmpdir, "bg.png")
        script_path = os.path.join(tmpdir, "script.txt")
        audio_path = os.path.join(tmpdir, "audio.wav")
        output_path = os.path.join(tmpdir, "output.mp4")

        Image.new("RGB", (1080, 1920), (30, 30, 60)).save(img_path)
        script_text = "This is a test of the caption generator"
        with open(script_path, "w") as f:
            f.write(script_text)

        # Mock ElevenLabs
        mock_client = MagicMock()
        mock_response = _mock_elevenlabs_response()
        mock_client.text_to_speech.convert_with_timestamps.return_value = mock_response

        mock_voice = MagicMock()
        mock_voice.voice_id = "test-id"
        mock_voice.name = "Rachel"
        mock_client.voices.get_all.return_value.voices = [mock_voice]

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
            with patch("tts.ElevenLabs", return_value=mock_client):
                # Step 1: Validate
                text = validate_inputs(img_path, script_path)
                assert text == script_text

                # Step 2: TTS
                audio_bytes, words = generate(text, voice="Rachel")
                assert len(words) == 8  # "This is a test of the caption generator"

                # Step 3: Group
                pages = group_words(words)
                assert len(pages) >= 1
                total_words = sum(len(p) for p in pages)
                assert total_words == 8

                # Step 4 & 5: Save audio and composite
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)

                compose_video(
                    image_path=img_path,
                    audio_path=audio_path,
                    pages=pages,
                    font_path=FONT_PATH,
                    output_path=output_path,
                )

                # Verify output
                assert os.path.exists(output_path)
                assert os.path.getsize(output_path) > 0

                clip = VideoFileClip(output_path)
                assert clip.size == [1080, 1920]
                clip.close()
```

- [ ] **Step 2: Run the integration test**

Run: `cd ~/projects/caption-gen && python -m pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `cd ~/projects/caption-gen && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
cd ~/projects/caption-gen
git add tests/test_integration.py
git commit -m "test: add end-to-end integration test with mocked TTS"
```

---

## Usage

After implementation, the tool is used like:

```bash
export ELEVENLABS_API_KEY="your-key-here"

python caption_gen.py \
  --image background.png \
  --script script.txt \
  --output my_video.mp4 \
  --voice Rachel \
  --highlight-color "#FFD700" \
  --font-size 48
```
