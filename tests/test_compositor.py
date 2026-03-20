import os
import tempfile
import numpy as np
from PIL import Image
from compositor import compose_video


FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "fonts", "Oswald-Bold.ttf")


def _create_test_image(path):
    img = Image.new("RGB", (1080, 1920), (0, 0, 128))
    img.save(path)


def _create_silent_audio(path, duration=1.0, sample_rate=44100):
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
