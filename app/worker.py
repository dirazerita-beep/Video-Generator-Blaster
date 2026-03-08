"""QThread worker for Video Generator Blaster.

Runs the variation generation loop in a background thread,
keeping the GUI responsive.
"""

import logging
import os
import pathlib
import shutil
import threading

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class GenerationWorker(QThread):
    """Worker thread that generates video variations.

    Signals:
        progress(int): Emits overall progress 0–100.
        log(str): Emits a human-readable status message.
        finished(): Emitted when all variations are done (or cancelled).
        error(str): Emitted when a fatal error occurs.
    """

    progress = Signal(int)
    log = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, params: dict, parent=None):
        """Initialize the worker.

        Args:
            params: Dict containing all generation parameters:
                - input_video (str)
                - output_folder (str)
                - num_variations (int)
                - recipes (list[dict]) from variations.generate_recipes()
                - settings (dict) for ffmpeg_runner.render_variation()
                - tts_engine (BaseTTS instance or None)
        """
        super().__init__(parent)
        self.params = params
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Request cancellation of the generation loop."""
        self._cancel_event.set()
        self.log.emit("⏹ Cancellation requested…")

    def run(self) -> None:
        """Main worker logic executed in the background thread."""
        from app.ffmpeg_runner import render_variation
        from app.presets import OUTPUT_FILENAME_TEMPLATE, TEMP_DIR_NAME

        input_video: str = self.params["input_video"]
        output_folder: str = self.params["output_folder"]
        recipes: list = self.params["recipes"]
        settings: dict = self.params["settings"]
        tts_engine = self.params.get("tts_engine")

        n = len(recipes)
        self.log.emit(f"🚀 Starting generation of {n} variation(s)…")

        # Ensure output folder exists
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as exc:
            self.error.emit(f"Cannot create output folder: {exc}")
            return

        # Temp dir inside output folder
        temp_dir = os.path.join(output_folder, TEMP_DIR_NAME)
        os.makedirs(temp_dir, exist_ok=True)

        successes = 0
        failures = 0

        for i, recipe in enumerate(recipes):
            if self._cancel_event.is_set():
                self.log.emit("⏹ Generation cancelled.")
                break

            output_filename = OUTPUT_FILENAME_TEMPLATE.format(i + 1)
            output_path = os.path.join(output_folder, output_filename)

            self.log.emit(f"[{i+1}/{n}] Rendering {output_filename}…")

            def _variation_progress(p: float, idx: int = i) -> None:
                overall = int(((idx + p) / n) * 100)
                self.progress.emit(overall)

            try:
                ok = render_variation(
                    recipe=recipe,
                    input_video=input_video,
                    output_path=output_path,
                    settings=settings,
                    progress_callback=_variation_progress,
                    cancel_event=self._cancel_event,
                    tts_engine=tts_engine,
                )
            except Exception as exc:
                logger.error("Variation %d raised exception: %s", i + 1, exc, exc_info=True)
                ok = False

            if self._cancel_event.is_set():
                self.log.emit("⏹ Generation cancelled.")
                break

            if ok:
                successes += 1
                self.log.emit(f"  ✅ {output_filename} done.")
            else:
                failures += 1
                self.log.emit(f"  ❌ {output_filename} failed.")

            self.progress.emit(int(((i + 1) / n) * 100))

        # Clean up temp dir
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

        self.log.emit(
            f"✔ Finished: {successes} succeeded, {failures} failed out of {n} total."
        )
        self.progress.emit(100)
        self.finished.emit()
