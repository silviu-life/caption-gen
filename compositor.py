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
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    bg = ImageClip(image_path).with_duration(duration)

    # TikTok safe zone: ~40% from top = 768px
    y_position = int(1920 * 0.55)

    caption_clips = []
    for page_idx, page in enumerate(pages):
        for word_idx in range(len(page)):
            overlay_img = render_caption(
                words=page,
                highlight_index=word_idx,
                font_path=font_path,
                font_size=font_size,
                highlight_color=highlight_color,
            )
            overlay_array = np.array(overlay_img)

            start = page[word_idx]["start"]
            if word_idx + 1 < len(page):
                end = page[word_idx + 1]["start"]
            elif page_idx + 1 < len(pages):
                end = pages[page_idx + 1][0]["start"]
            else:
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
        logger=None,
    )

    audio.close()
    video.close()
