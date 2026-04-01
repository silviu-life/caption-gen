import argparse
import os
import sys
import tempfile

from dotenv import load_dotenv
from PIL import Image

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


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

    with Image.open(image_path) as img:
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
    default_image = os.path.join(os.path.dirname(__file__), "images", "05_emerging_1080x1920.png")
    parser.add_argument("--image", default=default_image, help="Background image (1080x1920 PNG/JPG)")
    parser.add_argument("--script", required=True, help="Text file with narration script")
    parser.add_argument("--output", default=None, help="Output video path (default: output/<script-name>.mp4)")
    parser.add_argument("--voice", default="Theo Silk", help="ElevenLabs voice name (default: Theo Silk)")
    parser.add_argument("--highlight-color", default="#FFD700", help="Highlight color hex (default: #FFD700)")
    parser.add_argument("--font-size", type=int, default=48, help="Caption font size (default: 48)")

    args = parser.parse_args()

    if args.output is None:
        script_name = os.path.splitext(os.path.basename(args.script))[0]
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
        args.output = os.path.join(output_dir, f"{script_name}.mp4")

    script_text = validate_inputs(args.image, args.script)
    font_path = os.path.join(os.path.dirname(__file__), "fonts", "Oswald-Bold.ttf")

    from tts import generate

    print("Generating speech audio...")
    audio_bytes, words, char_count = generate(script_text, voice=args.voice)
    print(f"  Got {len(words)} words with timestamps")
    print(f"  ElevenLabs cost: {char_count} characters")
    cost_per_char = float(os.environ.get("ELEVENLABS_COST_PER_CHAR", "0.000198"))
    cost_usd = char_count * cost_per_char
    print(f"  Estimated cost: ${cost_usd:.4f}")

    pages = group_words(words)
    print(f"  Grouped into {len(pages)} caption pages")

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
