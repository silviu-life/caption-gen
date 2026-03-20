from PIL import Image, ImageDraw, ImageFont


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _split_into_lines(text_parts, word_widths, space_width, max_width):
    """Split words into lines that fit within max_width."""
    lines = []
    current_line = []
    current_width = 0

    for i, (text, w) in enumerate(zip(text_parts, word_widths)):
        added_width = w + (space_width if current_line else 0)
        if current_line and current_width + added_width > max_width:
            lines.append(current_line)
            current_line = [(i, text, w)]
            current_width = w
        else:
            current_line.append((i, text, w))
            current_width += added_width

    if current_line:
        lines.append(current_line)

    return lines


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

    ascent, descent = font.getmetrics()
    text_height = ascent + descent
    shadow_offset = 4
    stroke_width = 2
    padding = shadow_offset + stroke_width
    line_spacing = 8

    # Split into lines if text is too wide (with horizontal margin)
    h_margin = 40
    max_text_width = width - h_margin * 2
    lines = _split_into_lines(text_parts, word_widths, space_width, max_text_width)

    num_lines = len(lines)
    img_height = text_height * num_lines + line_spacing * (num_lines - 1) + padding * 2

    img = Image.new("RGBA", (width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = padding
    for line in lines:
        # Calculate line width for centering
        line_width = sum(w for _, _, w in line) + space_width * (len(line) - 1)
        x = (width - line_width) / 2

        for idx, text, word_width in line:
            color = highlight_rgb if idx == highlight_index else (255, 255, 255)

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

        y += text_height + line_spacing

    return img
