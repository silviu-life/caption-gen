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
    assert img_large.height > img_small.height
