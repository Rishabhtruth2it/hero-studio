"""Stage 4 — assembly: captions, voiceover, music. Fully local, free, no API key.

Uses the static ffmpeg binary bundled by imageio-ffmpeg (no Homebrew needed)
and edge-tts (free, no key) for voiceover.
"""
import asyncio
import subprocess
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
DEFAULT_FONT = "/System/Library/Fonts/Helvetica.ttc"


def add_caption(
    video_path: str,
    text: str,
    output_path: str,
    font_path: str = DEFAULT_FONT,
    font_size: int = 56,
    position: str = "bottom",
) -> str:
    y = "h-th-80" if position == "bottom" else "80"
    escaped = text.replace(":", r"\:").replace("'", r"\'")
    drawtext = (
        f"drawtext=fontfile={font_path}:text='{escaped}':fontcolor=white:"
        f"fontsize={font_size}:borderw=3:bordercolor=black:x=(w-tw)/2:y={y}"
    )
    subprocess.run(
        [FFMPEG, "-y", "-i", video_path, "-vf", drawtext, "-c:a", "copy", output_path],
        check=True,
    )
    return output_path


def generate_voiceover(text: str, output_path: str, voice: str = "en-US-ChristopherNeural") -> str:
    import edge_tts

    async def _run():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    asyncio.run(_run())
    return output_path


def mux_audio(video_path: str, audio_path: str, output_path: str, music_volume: float = 0.3) -> str:
    """Replace/add an audio track, ducked to music_volume if it's background music."""
    subprocess.run(
        [
            FFMPEG, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", f"[1:a]volume={music_volume}[a1]",
            "-map", "0:v", "-map", "[a1]",
            "-c:v", "copy", "-shortest",
            output_path,
        ],
        check=True,
    )
    return output_path


def concat_clips(clip_paths: list[str], output_path: str) -> str:
    list_file = Path(output_path).with_suffix(".txt")
    list_file.write_text("\n".join(f"file '{Path(p).resolve()}'" for p in clip_paths))
    subprocess.run(
        [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", output_path],
        check=True,
    )
    list_file.unlink()
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Add a burned-in caption to a video")
    parser.add_argument("video")
    parser.add_argument("text")
    parser.add_argument("output")
    args = parser.parse_args()

    out = add_caption(args.video, args.text, args.output)
    print(f"Wrote {out}")
