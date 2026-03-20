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


def _get_voice_id(client: ElevenLabs, voice_name: str) -> str:
    """Look up voice_id by name. If voice_name looks like an ID, return it directly."""
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
