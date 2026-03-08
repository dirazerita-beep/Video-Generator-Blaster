"""FFmpeg wrapper for Video Generator Blaster.

Provides functions to probe, reframe, split, concat, overlay text,
add intro/outro, mix audio, and render full variations.
"""

import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FFmpeg binary resolution
# ---------------------------------------------------------------------------

def _find_ffmpeg() -> tuple[str, str]:
    """Locate ffmpeg and ffprobe binaries.

    Looks first in third_party/ffmpeg/ relative to the app directory,
    then falls back to the system PATH.

    Returns:
        Tuple of (ffmpeg_path, ffprobe_path).

    Raises:
        FileNotFoundError: If ffmpeg cannot be located.
    """
    # Resolve the third_party directory relative to this file
    here = pathlib.Path(__file__).parent.parent
    bundled_ffmpeg = here / "third_party" / "ffmpeg" / "ffmpeg.exe"
    bundled_ffprobe = here / "third_party" / "ffmpeg" / "ffprobe.exe"

    if bundled_ffmpeg.exists():
        return str(bundled_ffmpeg), str(bundled_ffprobe)

    # Fallback: system PATH
    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")

    if ffmpeg_bin is None:
        raise FileNotFoundError(
            "FFmpeg not found. Please place ffmpeg.exe and ffprobe.exe in "
            "the 'third_party/ffmpeg/' directory, or install FFmpeg and add "
            "it to your system PATH."
        )

    return ffmpeg_bin, ffprobe_bin or str(pathlib.Path(ffmpeg_bin).parent / "ffprobe")


FFMPEG_BIN: Optional[str] = None
FFPROBE_BIN: Optional[str] = None


def _get_ffmpeg() -> tuple[str, str]:
    """Lazily resolve and cache FFmpeg binaries."""
    global FFMPEG_BIN, FFPROBE_BIN
    if FFMPEG_BIN is None:
        FFMPEG_BIN, FFPROBE_BIN = _find_ffmpeg()
    return FFMPEG_BIN, FFPROBE_BIN


# ---------------------------------------------------------------------------
# Helper: run FFmpeg / FFprobe
# ---------------------------------------------------------------------------

def _run(
    cmd: list[str],
    cancel_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    total_frames: Optional[int] = None,
) -> tuple[int, str]:
    """Run a subprocess command, optionally tracking FFmpeg progress.

    Args:
        cmd: Command + arguments list.
        cancel_event: If set, the process is killed when the event is set.
        progress_callback: Called with a float 0.0–1.0 as frames are processed.
        total_frames: Expected total frame count (for progress calculation).

    Returns:
        Tuple of (return_code, stderr_text).
    """
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creation_flags,
    )

    stderr_lines: list[str] = []
    frame_re = re.compile(r"frame=\s*(\d+)")

    def _read_stderr():
        for line in proc.stderr:
            stderr_lines.append(line)
            if progress_callback and total_frames:
                m = frame_re.search(line)
                if m:
                    frames_done = int(m.group(1))
                    progress_callback(min(frames_done / total_frames, 1.0))

    stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
    stderr_thread.start()

    while proc.poll() is None:
        if cancel_event and cancel_event.is_set():
            proc.kill()
            break

    stderr_thread.join(timeout=5)
    return proc.returncode, "".join(stderr_lines)


# ---------------------------------------------------------------------------
# probe_video
# ---------------------------------------------------------------------------

def probe_video(input_path: str) -> dict:
    """Probe a video file and return metadata.

    Returns:
        Dict with keys: duration (float), width (int), height (int),
        fps (float), has_audio (bool), audio_codec (str).

    Raises:
        RuntimeError: If ffprobe fails.
    """
    _, ffprobe = _get_ffmpeg()
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        input_path,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    data = json.loads(result.stdout)
    info: dict = {
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "fps": 30.0,
        "has_audio": False,
        "audio_codec": "",
    }

    fmt = data.get("format", {})
    info["duration"] = float(fmt.get("duration", 0))

    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type", "")
        if codec_type == "video" and info["width"] == 0:
            info["width"] = int(stream.get("width", 0))
            info["height"] = int(stream.get("height", 0))
            # fps may be "30/1" or "30000/1001"
            fps_str = stream.get("r_frame_rate", "30/1")
            try:
                num, den = fps_str.split("/")
                info["fps"] = float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                info["fps"] = 30.0
            if not info["duration"]:
                info["duration"] = float(stream.get("duration", 0))
        elif codec_type == "audio" and not info["has_audio"]:
            info["has_audio"] = True
            info["audio_codec"] = stream.get("codec_name", "")

    return info


# ---------------------------------------------------------------------------
# reframe_video
# ---------------------------------------------------------------------------

def reframe_video(
    input_path: str,
    output_path: str,
    mode: str,
    target_w: int = 1080,
    target_h: int = 1920,
    cancel_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> bool:
    """Reframe a video to the target 9:16 resolution.

    Args:
        input_path: Source video path.
        output_path: Output video path.
        mode: One of 'blur', 'crop', 'fit'.
        target_w: Output width (default 1080).
        target_h: Output height (default 1920).
        cancel_event: Optional cancellation event.
        progress_callback: Optional progress callback (0.0–1.0).

    Returns:
        True on success.
    """
    ffmpeg, _ = _get_ffmpeg()
    info = probe_video(input_path)
    total_frames = int(info["fps"] * info["duration"]) or None

    if mode == "blur":
        # Background: scale to cover height, blur; foreground: scale to fit width
        vf = (
            f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},gblur=sigma=20[bg];"
            f"[0:v]scale={target_w}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"
        )
        vf_map = "[out]"
    elif mode == "crop":
        # Center crop to 9:16
        in_w, in_h = info["width"], info["height"]
        target_ratio = target_w / target_h
        if in_w / in_h > target_ratio:
            # wider than 9:16: crop sides
            crop_w = int(in_h * target_ratio)
            vf = f"crop={crop_w}:{in_h}:(iw-{crop_w})/2:0,scale={target_w}:{target_h}"
        else:
            # taller than 9:16: crop top/bottom
            crop_h = int(in_w / target_ratio)
            vf = f"crop={in_w}:{crop_h}:0:(ih-{crop_h})/2,scale={target_w}:{target_h}"
        vf_map = None
    elif mode == "fit":
        # Scale to fit inside target, pad with black
        vf = (
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black"
        )
        vf_map = None
    else:
        raise ValueError(f"Unknown reframe mode: {mode}")

    cmd = [ffmpeg, "-y", "-i", input_path]
    if vf_map:
        cmd += ["-filter_complex", vf, "-map", vf_map]
        # filter_complex mode: must explicitly map audio stream
        cmd += ["-map", "0:a?"] if info["has_audio"] else ["-an"]
    else:
        cmd += ["-vf", vf]
        # -vf mode: FFmpeg auto-selects all streams; only force -an when no audio

    cmd += [
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]

    rc, stderr = _run(cmd, cancel_event, progress_callback, total_frames)
    if rc != 0:
        logger.error("reframe_video failed (rc=%d): %s", rc, stderr[-2000:])
        return False
    return True


# ---------------------------------------------------------------------------
# split_segments
# ---------------------------------------------------------------------------

def split_segments(
    input_path: str,
    num_segments: int,
    temp_dir: str,
    cancel_event: Optional[threading.Event] = None,
) -> list[str]:
    """Split a video into equal-duration segments.

    Args:
        input_path: Source video path.
        num_segments: Number of segments to split into.
        temp_dir: Directory for temporary segment files.
        cancel_event: Optional cancellation event.

    Returns:
        List of segment file paths in order.
    """
    ffmpeg, _ = _get_ffmpeg()
    info = probe_video(input_path)
    duration = info["duration"]
    seg_dur = duration / num_segments

    segments = []
    for i in range(num_segments):
        start = i * seg_dur
        seg_path = os.path.join(temp_dir, f"segment_{i:03d}.mp4")
        cmd = [
            ffmpeg, "-y",
            "-ss", str(start),
            "-i", input_path,
            "-t", str(seg_dur),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            seg_path,
        ]
        rc, stderr = _run(cmd, cancel_event)
        if rc != 0:
            logger.error("split_segments failed for segment %d: %s", i, stderr[-2000:])
            raise RuntimeError(f"Failed to split segment {i}")
        segments.append(seg_path)

    return segments


# ---------------------------------------------------------------------------
# concat_segments
# ---------------------------------------------------------------------------

def concat_segments(
    segment_paths: list[str],
    output_path: str,
    cancel_event: Optional[threading.Event] = None,
) -> bool:
    """Concatenate video segments in given order using FFmpeg concat demuxer.

    Args:
        segment_paths: Ordered list of segment file paths.
        output_path: Output video path.
        cancel_event: Optional cancellation event.

    Returns:
        True on success.
    """
    ffmpeg, _ = _get_ffmpeg()

    # Write concat list file
    list_path = output_path + ".concat_list.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for seg in segment_paths:
            # FFmpeg concat list requires escaped single quotes
            escaped = seg.replace("'", "\\'")
            f.write(f"file '{escaped}'\n")

    cmd = [
        ffmpeg, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        output_path,
    ]
    rc, stderr = _run(cmd, cancel_event)
    try:
        os.remove(list_path)
    except OSError:
        pass

    if rc != 0:
        logger.error("concat_segments failed (rc=%d): %s", rc, stderr[-2000:])
        return False
    return True


# ---------------------------------------------------------------------------
# overlay_text
# ---------------------------------------------------------------------------

def overlay_text(
    input_path: str,
    output_path: str,
    text: str,
    position: str,
    font_size: int,
    color: str,
    start_time: float,
    duration: float,
    shadow: bool = True,
    cancel_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> bool:
    """Overlay text on a video for a specified time window.

    Args:
        input_path: Source video path.
        output_path: Output video path.
        text: Text string to display.
        position: 'Top', 'Center', or 'Bottom'.
        font_size: Font size in pixels.
        color: Text color (e.g. 'white', '#ffffff').
        start_time: When to start showing text (seconds).
        duration: How long to show text (seconds).
        shadow: Whether to add a drop shadow/outline.
        cancel_event: Optional cancellation event.
        progress_callback: Optional progress callback.

    Returns:
        True on success.
    """
    if not text:
        # Nothing to overlay; just copy
        shutil.copy2(input_path, output_path)
        return True

    ffmpeg, _ = _get_ffmpeg()
    info = probe_video(input_path)
    total_frames = int(info["fps"] * info["duration"]) or None

    # Sanitize text for FFmpeg drawtext (escape special chars)
    safe_text = _escape_drawtext(text)

    # Position
    if position == "Top":
        y_expr = "h*0.08"
    elif position == "Center":
        y_expr = "(h-text_h)/2"
    else:  # Bottom
        y_expr = "h*0.85"

    x_expr = "(w-text_w)/2"
    enable_expr = f"between(t,{start_time},{start_time + duration})"

    # Convert color to drawtext-compatible hex (strip #)
    dt_color = color.lstrip("#") if color.startswith("#") else color

    if shadow:
        drawtext = (
            f"drawtext=text='{safe_text}':fontsize={font_size}:fontcolor={dt_color}:"
            f"x={x_expr}:y={y_expr}:"
            f"shadowcolor=black@0.8:shadowx=2:shadowy=2:"
            f"borderw=2:bordercolor=black@0.6:"
            f"enable='{enable_expr}'"
        )
    else:
        drawtext = (
            f"drawtext=text='{safe_text}':fontsize={font_size}:fontcolor={dt_color}:"
            f"x={x_expr}:y={y_expr}:"
            f"enable='{enable_expr}'"
        )

    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-vf", drawtext,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "copy",
        output_path,
    ]
    rc, stderr = _run(cmd, cancel_event, progress_callback, total_frames)
    if rc != 0:
        logger.error("overlay_text failed (rc=%d): %s", rc, stderr[-2000:])
        return False
    return True


def _escape_drawtext(text: str) -> str:
    """Escape a string for use in FFmpeg drawtext filter."""
    # Escape backslash, colon, single quote, and special chars
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\u2019")  # Replace ' with right single quote
    text = text.replace(":", "\\:")
    text = text.replace("%", "\\%")
    text = text.replace("\n", " ")
    return text


# ---------------------------------------------------------------------------
# add_intro_outro
# ---------------------------------------------------------------------------

def add_intro_outro(
    input_path: str,
    output_path: str,
    intro_text: str,
    outro_text: str,
    intro_dur: float,
    outro_dur: float,
    bg_color: str,
    font_size: int,
    color: str,
    cancel_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> bool:
    """Add solid-color intro and/or outro slides to a video.

    Args:
        input_path: Source video path.
        output_path: Output video path.
        intro_text: Text shown on intro slide (may be empty).
        outro_text: Text shown on outro slide (may be empty).
        intro_dur: Intro duration in seconds (0 = no intro).
        outro_dur: Outro duration in seconds (0 = no outro).
        bg_color: Background color hex (e.g. '#000000').
        font_size: Font size for intro/outro text.
        color: Text color.
        cancel_event: Optional cancellation event.
        progress_callback: Optional progress callback.

    Returns:
        True on success.
    """
    if intro_dur <= 0 and outro_dur <= 0:
        shutil.copy2(input_path, output_path)
        return True

    ffmpeg, _ = _get_ffmpeg()
    info = probe_video(input_path)
    w, h = 1080, 1920
    fps = info["fps"]

    # Convert bg_color from hex to rgb
    bg_r, bg_g, bg_b = _hex_to_rgb(bg_color)
    bg_rgb = f"0x{bg_r:02X}{bg_g:02X}{bg_b:02X}"

    dt_color = color.lstrip("#") if color.startswith("#") else color
    parts: list[str] = []  # ordered segments (file paths)

    # Work in a temp dir next to output
    temp_dir = output_path + "_io_temp"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        inputs = []
        filter_parts = []
        concat_inputs = []
        idx = 0

        if intro_dur > 0:
            intro_path = os.path.join(temp_dir, "intro_slide.mp4")
            _create_solid_slide(
                ffmpeg, intro_path, intro_text, intro_dur, w, h, fps,
                bg_rgb, dt_color, font_size, cancel_event,
            )
            inputs.append(intro_path)
            idx += 1

        inputs.append(input_path)
        idx += 1

        if outro_dur > 0:
            outro_path = os.path.join(temp_dir, "outro_slide.mp4")
            _create_solid_slide(
                ffmpeg, outro_path, outro_text, outro_dur, w, h, fps,
                bg_rgb, dt_color, font_size, cancel_event,
            )
            inputs.append(outro_path)
            idx += 1

        # Concat all parts
        ok = concat_segments(inputs, output_path, cancel_event)
        return ok

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string (#RRGGBB or #RGB) to (r, g, b)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


def _create_solid_slide(
    ffmpeg: str,
    output_path: str,
    text: str,
    duration: float,
    w: int,
    h: int,
    fps: float,
    bg_rgb: str,
    text_color: str,
    font_size: int,
    cancel_event: Optional[threading.Event],
) -> None:
    """Create a solid-color video slide with optional centered text."""
    safe_text = _escape_drawtext(text) if text else ""

    if safe_text:
        drawtext = (
            f"drawtext=text='{safe_text}':fontsize={font_size}:fontcolor={text_color}:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"shadowcolor=black@0.8:shadowx=2:shadowy=2:"
            f"borderw=2:bordercolor=black@0.6"
        )
        vf = f"color=c={bg_rgb}:size={w}x{h}:rate={fps:.3f},format=yuv420p,{drawtext}"
    else:
        vf = f"color=c={bg_rgb}:size={w}x{h}:rate={fps:.3f},format=yuv420p"

    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", vf,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    rc, stderr = _run(cmd, cancel_event)
    if rc != 0:
        raise RuntimeError(f"Failed to create slide: {stderr[-1000:]}")


# ---------------------------------------------------------------------------
# mix_audio
# ---------------------------------------------------------------------------

def mix_audio(
    video_path: str,
    tts_path: Optional[str],
    music_path: Optional[str],
    output_path: str,
    tts_vol: float,
    music_vol: float,
    fade_in: bool,
    fade_out: bool,
    fade_dur: float = 2.0,
    cancel_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> bool:
    """Mix TTS and/or background music with a video's audio track.

    Args:
        video_path: Input video path.
        tts_path: Path to TTS audio file (or None).
        music_path: Path to background music file (or None).
        output_path: Output video path.
        tts_vol: TTS volume (0–100).
        music_vol: Music volume (0–100).
        fade_in: Apply fade-in to music.
        fade_out: Apply fade-out to music.
        fade_dur: Fade duration in seconds.
        cancel_event: Optional cancellation event.
        progress_callback: Optional progress callback.

    Returns:
        True on success.
    """
    if tts_path is None and music_path is None:
        shutil.copy2(video_path, output_path)
        return True

    ffmpeg, _ = _get_ffmpeg()
    info = probe_video(video_path)
    duration = info["duration"]
    total_frames = int(info["fps"] * duration) or None

    tts_scale = tts_vol / 100.0
    music_scale = music_vol / 100.0

    # Build filter graph
    inputs = ["-i", video_path]
    filter_parts = []
    mix_inputs = []

    stream_idx = 1  # 0 is video

    if info["has_audio"]:
        # Scale original video audio
        filter_parts.append(f"[0:a]volume=1.0[orig_a]")
        mix_inputs.append("[orig_a]")

    if tts_path:
        inputs += ["-i", tts_path]
        filter_parts.append(f"[{stream_idx}:a]volume={tts_scale:.3f}[tts_a]")
        mix_inputs.append("[tts_a]")
        stream_idx += 1

    if music_path:
        inputs += ["-i", music_path]
        # Loop music to fill video duration, apply fade
        fade_filter = f"[{stream_idx}:a]aloop=loop=-1:size=2e+09,atrim=duration={duration}"
        if fade_in:
            fade_filter += f",afade=t=in:st=0:d={fade_dur}"
        if fade_out:
            fade_start = max(0.0, duration - fade_dur)
            fade_filter += f",afade=t=out:st={fade_start:.3f}:d={fade_dur}"
        fade_filter += f",volume={music_scale:.3f}[music_a]"
        filter_parts.append(fade_filter)
        mix_inputs.append("[music_a]")
        stream_idx += 1

    # Final amix
    n_mix = len(mix_inputs)
    filter_parts.append(f"{''.join(mix_inputs)}amix=inputs={n_mix}:duration=first:dropout_transition=3[final_a]")

    filter_graph = ";".join(filter_parts)

    cmd = [ffmpeg, "-y"] + inputs + [
        "-filter_complex", filter_graph,
        "-map", "0:v",
        "-map", "[final_a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_path,
    ]

    rc, stderr = _run(cmd, cancel_event, progress_callback, total_frames)
    if rc != 0:
        logger.error("mix_audio failed (rc=%d): %s", rc, stderr[-2000:])
        return False
    return True


# ---------------------------------------------------------------------------
# render_variation
# ---------------------------------------------------------------------------

def render_variation(
    recipe: dict,
    input_video: str,
    output_path: str,
    settings: dict,
    progress_callback: Optional[Callable[[float], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    tts_engine=None,
) -> bool:
    """Orchestrate all processing steps for a single variation.

    Args:
        recipe: Recipe dict from variations.generate_recipes().
        input_video: Path to source video.
        output_path: Final output path for this variation.
        settings: UI settings dict with keys:
            - reframe_mode: 'blur' | 'crop' | 'fit'
            - font_size: int
            - font_color: str
            - text_position: str
            - text_shadow: bool
            - shuffle_enabled: bool
            - num_segments: int
            - intro_dur: float
            - outro_dur: float
            - bg_color: str
            - tts_mode: str
            - tts_vol: int
            - music_vol: int
            - music_fade: bool
        progress_callback: Called with 0.0–1.0 to report progress.
        cancel_event: Optional cancellation event.
        tts_engine: Initialized TTS engine instance (or None).

    Returns:
        True on success, False on failure.
    """
    temp_dir = os.path.join(os.path.dirname(output_path), "temp")
    os.makedirs(temp_dir, exist_ok=True)

    def _step_progress(step: int, n_steps: int, local: float) -> None:
        if progress_callback:
            progress_callback((step + local) / n_steps)

    def _cancelled() -> bool:
        return bool(cancel_event and cancel_event.is_set())

    n_steps = 6  # reframe, shuffle, overlays, intro/outro, tts, audio
    step = 0

    try:
        # Step 1: Reframe
        reframed = os.path.join(temp_dir, "01_reframed.mp4")
        if _cancelled():
            return False
        ok = reframe_video(
            input_video, reframed,
            mode=settings.get("reframe_mode", "blur"),
            cancel_event=cancel_event,
            progress_callback=lambda p: _step_progress(step, n_steps, p),
        )
        if not ok or _cancelled():
            return False
        step += 1

        # Step 2: Segment shuffle (optional)
        current = reframed
        if settings.get("shuffle_enabled", False):
            num_segs = settings.get("num_segments", 4)
            segment_order = recipe.get("segment_order", list(range(num_segs)))
            segments = split_segments(current, num_segs, temp_dir, cancel_event)
            if _cancelled():
                return False
            ordered = [segments[i] for i in segment_order if i < len(segments)]
            shuffled = os.path.join(temp_dir, "02_shuffled.mp4")
            ok = concat_segments(ordered, shuffled, cancel_event)
            if not ok or _cancelled():
                return False
            current = shuffled
        step += 1

        # Step 3: Text overlays
        info = probe_video(current)
        vid_dur = info["duration"]
        text_steps = []

        hook_text = recipe.get("hook_text", "")
        benefit_text = recipe.get("benefit_text", "")
        cta_text = recipe.get("cta_text", "")

        from app.presets import (
            HOOK_DISPLAY_DURATION,
            BENEFIT_START_RATIO,
            BENEFIT_DISPLAY_DURATION,
            CTA_SECONDS_BEFORE_END,
            CTA_DISPLAY_DURATION,
        )

        if hook_text:
            text_steps.append((hook_text, 0.0, HOOK_DISPLAY_DURATION))
        if benefit_text:
            b_start = vid_dur * BENEFIT_START_RATIO
            text_steps.append((benefit_text, b_start, BENEFIT_DISPLAY_DURATION))
        if cta_text:
            c_start = max(0.0, vid_dur - CTA_SECONDS_BEFORE_END)
            text_steps.append((cta_text, c_start, CTA_DISPLAY_DURATION))

        for i, (txt, t_start, t_dur) in enumerate(text_steps):
            if _cancelled():
                return False
            out_txt = os.path.join(temp_dir, f"03_text_{i:02d}.mp4")
            ok = overlay_text(
                current, out_txt,
                text=txt,
                position=settings.get("text_position", "Bottom"),
                font_size=settings.get("font_size", 36),
                color=settings.get("font_color", "white"),
                start_time=t_start,
                duration=t_dur,
                shadow=settings.get("text_shadow", True),
                cancel_event=cancel_event,
                progress_callback=lambda p: _step_progress(step, n_steps, p),
            )
            if not ok or _cancelled():
                return False
            current = out_txt
        step += 1

        # Step 4: Intro / Outro
        intro_dur = settings.get("intro_dur", 1.5)
        outro_dur = settings.get("outro_dur", 1.5)
        if intro_dur > 0 or outro_dur > 0:
            io_out = os.path.join(temp_dir, "04_intro_outro.mp4")
            ok = add_intro_outro(
                current, io_out,
                intro_text=recipe.get("intro_text", ""),
                outro_text=recipe.get("outro_text", ""),
                intro_dur=intro_dur,
                outro_dur=outro_dur,
                bg_color=settings.get("bg_color", "#000000"),
                font_size=settings.get("font_size", 36),
                color=settings.get("font_color", "white"),
                cancel_event=cancel_event,
                progress_callback=lambda p: _step_progress(step, n_steps, p),
            )
            if not ok or _cancelled():
                return False
            current = io_out
        step += 1

        # Step 5: TTS generation
        tts_audio = None
        tts_script = recipe.get("tts_script")
        if tts_engine and tts_script:
            tts_out = os.path.join(temp_dir, "05_tts.wav")
            success = tts_engine.generate(tts_script, tts_out)
            if success and os.path.exists(tts_out):
                tts_audio = tts_out
        step += 1

        # Step 6: Audio mix
        music_file = recipe.get("music_file")
        tts_vol = settings.get("tts_vol", 80)
        music_vol = settings.get("music_vol", 30)
        music_fade = settings.get("music_fade", True)

        if tts_audio or music_file:
            audio_out = os.path.join(temp_dir, "06_audio.mp4")
            ok = mix_audio(
                current, tts_audio, music_file,
                audio_out,
                tts_vol=tts_vol,
                music_vol=music_vol,
                fade_in=music_fade,
                fade_out=music_fade,
                cancel_event=cancel_event,
                progress_callback=lambda p: _step_progress(step, n_steps, p),
            )
            if not ok or _cancelled():
                return False
            current = audio_out
        step += 1

        # Final copy to output path
        shutil.copy2(current, output_path)
        return True

    except Exception as exc:
        logger.error("render_variation error: %s", exc, exc_info=True)
        return False
