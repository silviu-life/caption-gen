from PIL import Image, ImageDraw, ImageFont


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
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
    y = padding

    for i, (text, word_width) in enumerate(zip(text_parts, word_widths)):
        color = highlight_rgb if i == highlight_index else (255, 255, 255)

        # Drop shadow
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
