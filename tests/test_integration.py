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
    text = "This is a test of the caption generator"
    chars = list(text)
    starts = [i * 0.05 for i in range(len(chars))]
    ends = [(i + 1) * 0.05 for i in range(len(chars))]

    wav_bytes = _make_wav_bytes(duration=2.0)

    mock_response = MagicMock()
    mock_response.audio_base_64 = base64.b64encode(wav_bytes).decode()
    mock_response.alignment = MagicMock()
    mock_response.alignment.characters = chars
    mock_response.alignment.character_start_times_seconds = starts
    mock_response.alignment.character_end_times_seconds = ends

    return mock_response


def test_full_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "bg.png")
        script_path = os.path.join(tmpdir, "script.txt")
        audio_path = os.path.join(tmpdir, "audio.wav")
        output_path = os.path.join(tmpdir, "output.mp4")

        Image.new("RGB", (1080, 1920), (30, 30, 60)).save(img_path)
        script_text = "This is a test of the caption generator"
        with open(script_path, "w") as f:
            f.write(script_text)

        mock_client = MagicMock()
        mock_response = _mock_elevenlabs_response()
        mock_client.text_to_speech.convert_with_timestamps.return_value = mock_response

        mock_voice = MagicMock()
        mock_voice.voice_id = "test-id"
        mock_voice.name = "Rachel"
        mock_client.voices.get_all.return_value.voices = [mock_voice]

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
            with patch("tts.ElevenLabs", return_value=mock_client):
                text = validate_inputs(img_path, script_path)
                assert text == script_text

                audio_bytes, words = generate(text, voice="Rachel")
                assert len(words) == 8

                pages = group_words(words)
                assert len(pages) >= 1
                total_words = sum(len(p) for p in pages)
                assert total_words == 8

                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)

                compose_video(
                    image_path=img_path,
                    audio_path=audio_path,
                    pages=pages,
                    font_path=FONT_PATH,
                    output_path=output_path,
                )

                assert os.path.exists(output_path)
                assert os.path.getsize(output_path) > 0

                clip = VideoFileClip(output_path)
                assert clip.size == [1080, 1920]
                clip.close()
