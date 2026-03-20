import base64
from unittest.mock import patch, MagicMock
from tts import chars_to_words, generate


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


def test_generate_returns_audio_and_words():
    mock_response = MagicMock()
    mock_response.audio_base_64 = base64.b64encode(b"fake-audio").decode()
    mock_response.alignment = MagicMock()
    mock_response.alignment.characters = ["H", "i", " ", "y", "o"]
    mock_response.alignment.character_start_times_seconds = [0.0, 0.1, 0.2, 0.3, 0.4]
    mock_response.alignment.character_end_times_seconds = [0.1, 0.2, 0.3, 0.4, 0.5]

    mock_client = MagicMock()
    mock_client.text_to_speech.convert_with_timestamps.return_value = mock_response

    mock_voice = MagicMock()
    mock_voice.voice_id = "test-voice-id"
    mock_voice.name = "Rachel"
    mock_client.voices.get_all.return_value.voices = [mock_voice]

    with patch("tts.ElevenLabs", return_value=mock_client), \
         patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
        audio_bytes, words = generate("Hi yo", voice="Rachel")

    assert audio_bytes == b"fake-audio"
    assert len(words) == 2
    assert words[0]["word"] == "Hi"
    assert words[1]["word"] == "yo"
