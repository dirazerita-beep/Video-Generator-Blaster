"""Main window UI for Video Generator Blaster (PySide6)."""

import json
import logging
import os
import pathlib
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app import presets
from app.variations import generate_recipes
from app.worker import GenerationWorker

logger = logging.getLogger(__name__)

CONFIG_PATH = pathlib.Path(__file__).parent.parent / presets.CONFIG_FILENAME


class MainWindow(QWidget):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Generator Blaster")
        self.setMinimumSize(900, 700)

        self._worker: Optional[GenerationWorker] = None
        self._font_color = presets.TEXT_COLOR_DEFAULT
        self._bg_color = presets.BG_COLOR_DEFAULT

        self._build_ui()
        self._load_config()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(4, 4, 4, 4)

        content_layout.addWidget(self._build_section_input_output())
        content_layout.addWidget(self._build_section_reframe())
        content_layout.addWidget(self._build_section_text_overlays())
        content_layout.addWidget(self._build_section_segments())
        content_layout.addWidget(self._build_section_intro_outro())
        content_layout.addWidget(self._build_section_audio())
        content_layout.addStretch()

        scroll.setWidget(content)
        root_layout.addWidget(scroll, stretch=1)
        root_layout.addWidget(self._build_section_generate())

    # ---- Section 1: Input / Output -----------------------------------

    def _build_section_input_output(self) -> QGroupBox:
        group = QGroupBox("1. Input / Output")
        layout = QVBoxLayout(group)

        # Input video row
        row = QHBoxLayout()
        row.addWidget(QLabel("Input Video:"))
        self.input_video_edit = QLineEdit()
        self.input_video_edit.setPlaceholderText("Select an MP4/MOV/AVI/MKV file…")
        row.addWidget(self.input_video_edit)
        btn_input = QPushButton("Browse…")
        btn_input.clicked.connect(self._browse_input_video)
        row.addWidget(btn_input)
        layout.addLayout(row)

        # Thumbnail
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedHeight(80)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.thumbnail_label)

        # Output folder row
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Output Folder:"))
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setPlaceholderText("Select output folder…")
        row2.addWidget(self.output_folder_edit)
        btn_out = QPushButton("Browse…")
        btn_out.clicked.connect(self._browse_output_folder)
        row2.addWidget(btn_out)
        layout.addLayout(row2)

        # Number of variations
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Number of Variations:"))
        self.variations_spin = QSpinBox()
        self.variations_spin.setRange(presets.VARIATIONS_MIN, presets.VARIATIONS_MAX)
        self.variations_spin.setValue(presets.VARIATIONS_DEFAULT)
        row3.addWidget(self.variations_spin)
        row3.addStretch()
        layout.addLayout(row3)

        return group

    # ---- Section 2: Reframe Mode -------------------------------------

    def _build_section_reframe(self) -> QGroupBox:
        from PySide6.QtWidgets import QButtonGroup, QRadioButton

        group = QGroupBox("2. Reframe Mode")
        layout = QHBoxLayout(group)

        self._reframe_group = QButtonGroup(self)
        self._reframe_radios: dict[str, QRadioButton] = {}

        for key, label in presets.REFRAME_MODES.items():
            rb = QRadioButton(label)
            self._reframe_radios[key] = rb
            self._reframe_group.addButton(rb)
            layout.addWidget(rb)

        self._reframe_radios["blur"].setChecked(True)
        layout.addStretch()
        return group

    # ---- Section 3: Text Overlays ------------------------------------

    def _build_section_text_overlays(self) -> QGroupBox:
        group = QGroupBox("3. Text Overlays")
        layout = QVBoxLayout(group)

        # Hook texts
        layout.addWidget(QLabel("Hook Texts (one per line):"))
        self.hooks_edit = QTextEdit()
        self.hooks_edit.setFixedHeight(70)
        self.hooks_edit.setPlaceholderText("e.g.\nYou won't believe this trick!\nDo you know this life hack?")
        layout.addWidget(self.hooks_edit)

        # Benefit texts
        layout.addWidget(QLabel("Benefit Texts (one per line):"))
        self.benefits_edit = QTextEdit()
        self.benefits_edit.setFixedHeight(70)
        self.benefits_edit.setPlaceholderText("e.g.\nSave 2 hours every day\nBoost your productivity instantly")
        layout.addWidget(self.benefits_edit)

        # CTA texts
        layout.addWidget(QLabel("CTA Texts (one per line):"))
        self.ctas_edit = QTextEdit()
        self.ctas_edit.setFixedHeight(70)
        self.ctas_edit.setPlaceholderText("e.g.\nFollow for more!\nComment below 👇")
        layout.addWidget(self.ctas_edit)

        # Font size, color, position row
        row = QHBoxLayout()
        row.addWidget(QLabel("Font Size:"))
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(presets.FONT_SIZE_MIN, presets.FONT_SIZE_MAX)
        self.font_size_slider.setValue(presets.FONT_SIZE_DEFAULT)
        self.font_size_slider.setFixedWidth(140)
        self.font_size_label = QLabel(str(presets.FONT_SIZE_DEFAULT))
        self.font_size_slider.valueChanged.connect(
            lambda v: self.font_size_label.setText(str(v))
        )
        row.addWidget(self.font_size_slider)
        row.addWidget(self.font_size_label)

        row.addSpacing(16)
        row.addWidget(QLabel("Font Color:"))
        self.font_color_btn = QPushButton()
        self.font_color_btn.setFixedWidth(60)
        self._update_color_button(self.font_color_btn, self._font_color)
        self.font_color_btn.clicked.connect(self._pick_font_color)
        row.addWidget(self.font_color_btn)

        row.addSpacing(16)
        row.addWidget(QLabel("Position:"))
        self.text_position_combo = QComboBox()
        self.text_position_combo.addItems(presets.TEXT_POSITIONS)
        self.text_position_combo.setCurrentText("Bottom")
        row.addWidget(self.text_position_combo)

        row.addSpacing(16)
        self.shadow_check = QCheckBox("Text shadow/outline")
        self.shadow_check.setChecked(True)
        row.addWidget(self.shadow_check)
        row.addStretch()
        layout.addLayout(row)

        return group

    # ---- Section 4: Segment Shuffling --------------------------------

    def _build_section_segments(self) -> QGroupBox:
        group = QGroupBox("4. Segment Shuffling")
        layout = QHBoxLayout(group)

        self.shuffle_check = QCheckBox("Enable segment shuffling")
        self.shuffle_check.setChecked(False)
        layout.addWidget(self.shuffle_check)

        layout.addSpacing(16)
        layout.addWidget(QLabel("Number of segments:"))
        self.segments_spin = QSpinBox()
        self.segments_spin.setRange(presets.SEGMENT_COUNT_MIN, presets.SEGMENT_COUNT_MAX)
        self.segments_spin.setValue(presets.SEGMENT_COUNT_DEFAULT)
        layout.addWidget(self.segments_spin)

        layout.addSpacing(16)
        note = QLabel("(Video is split into N segments and reassembled in random order)")
        note.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(note)
        layout.addStretch()
        return group

    # ---- Section 5: Intro / Outro ------------------------------------

    def _build_section_intro_outro(self) -> QGroupBox:
        group = QGroupBox("5. Intro / Outro")
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("Intro Duration (sec):"))
        self.intro_dur_spin = QDoubleSpinBox()
        self.intro_dur_spin.setRange(presets.INTRO_DUR_MIN, presets.INTRO_DUR_MAX)
        self.intro_dur_spin.setSingleStep(0.5)
        self.intro_dur_spin.setValue(presets.INTRO_DUR_DEFAULT)
        layout.addWidget(self.intro_dur_spin)

        layout.addSpacing(16)
        layout.addWidget(QLabel("Outro Duration (sec):"))
        self.outro_dur_spin = QDoubleSpinBox()
        self.outro_dur_spin.setRange(presets.INTRO_DUR_MIN, presets.INTRO_DUR_MAX)
        self.outro_dur_spin.setSingleStep(0.5)
        self.outro_dur_spin.setValue(presets.OUTRO_DUR_DEFAULT)
        layout.addWidget(self.outro_dur_spin)

        layout.addSpacing(16)
        layout.addWidget(QLabel("Background Color:"))
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedWidth(60)
        self._update_color_button(self.bg_color_btn, self._bg_color)
        self.bg_color_btn.clicked.connect(self._pick_bg_color)
        layout.addWidget(self.bg_color_btn)

        layout.addStretch()
        return group

    # ---- Section 6: Audio / TTS --------------------------------------

    def _build_section_audio(self) -> QGroupBox:
        group = QGroupBox("6. Audio / TTS")
        layout = QVBoxLayout(group)

        # TTS Mode row
        row = QHBoxLayout()
        row.addWidget(QLabel("TTS Mode:"))
        self.tts_mode_combo = QComboBox()
        for key, label in presets.TTS_MODES.items():
            self.tts_mode_combo.addItem(label, key)
        row.addWidget(self.tts_mode_combo)
        row.addStretch()
        layout.addLayout(row)

        # TTS scripts
        layout.addWidget(QLabel("TTS Scripts (one per line, each variation picks one randomly):"))
        self.tts_scripts_edit = QTextEdit()
        self.tts_scripts_edit.setFixedHeight(60)
        self.tts_scripts_edit.setPlaceholderText("e.g.\nThis changed my life!\nWatch until the end for the secret…")
        layout.addWidget(self.tts_scripts_edit)

        # SAPI options
        self.sapi_widget = self._build_sapi_options()
        layout.addWidget(self.sapi_widget)

        # OpenAI options
        self.openai_widget = self._build_openai_options()
        layout.addWidget(self.openai_widget)

        # Azure options
        self.azure_widget = self._build_azure_options()
        layout.addWidget(self.azure_widget)

        # ElevenLabs options
        self.elevenlabs_widget = self._build_elevenlabs_options()
        layout.addWidget(self.elevenlabs_widget)

        # TTS Volume
        row_tvol = QHBoxLayout()
        row_tvol.addWidget(QLabel("TTS Volume:"))
        self.tts_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.tts_vol_slider.setRange(0, 100)
        self.tts_vol_slider.setValue(presets.TTS_VOLUME_DEFAULT)
        self.tts_vol_slider.setFixedWidth(140)
        self.tts_vol_label = QLabel(str(presets.TTS_VOLUME_DEFAULT))
        self.tts_vol_slider.valueChanged.connect(
            lambda v: self.tts_vol_label.setText(str(v))
        )
        row_tvol.addWidget(self.tts_vol_slider)
        row_tvol.addWidget(self.tts_vol_label)
        row_tvol.addStretch()
        layout.addLayout(row_tvol)

        # Background Music
        layout.addWidget(QLabel("Background Music Folder:"))
        row_music = QHBoxLayout()
        self.music_folder_edit = QLineEdit()
        self.music_folder_edit.setPlaceholderText("Select folder with .mp3/.wav files…")
        row_music.addWidget(self.music_folder_edit)
        btn_music = QPushButton("Browse…")
        btn_music.clicked.connect(self._browse_music_folder)
        row_music.addWidget(btn_music)
        layout.addLayout(row_music)

        row_mvol = QHBoxLayout()
        row_mvol.addWidget(QLabel("Music Volume:"))
        self.music_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.music_vol_slider.setRange(0, 100)
        self.music_vol_slider.setValue(presets.MUSIC_VOLUME_DEFAULT)
        self.music_vol_slider.setFixedWidth(140)
        self.music_vol_label = QLabel(str(presets.MUSIC_VOLUME_DEFAULT))
        self.music_vol_slider.valueChanged.connect(
            lambda v: self.music_vol_label.setText(str(v))
        )
        row_mvol.addWidget(self.music_vol_slider)
        row_mvol.addWidget(self.music_vol_label)

        row_mvol.addSpacing(16)
        self.music_fade_check = QCheckBox("Fade in/out")
        self.music_fade_check.setChecked(True)
        row_mvol.addWidget(self.music_fade_check)
        row_mvol.addStretch()
        layout.addLayout(row_mvol)

        # Connect TTS mode change to visibility
        self.tts_mode_combo.currentIndexChanged.connect(self._update_tts_visibility)
        self._update_tts_visibility()

        return group

    def _build_sapi_options(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Voice:"))
        self.sapi_voice_combo = QComboBox()
        self.sapi_voice_combo.setMinimumWidth(220)
        self._populate_sapi_voices()
        layout.addWidget(self.sapi_voice_combo)
        layout.addSpacing(16)
        layout.addWidget(QLabel("Rate (wpm):"))
        self.sapi_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.sapi_rate_slider.setRange(50, 300)
        self.sapi_rate_slider.setValue(150)
        self.sapi_rate_slider.setFixedWidth(100)
        self.sapi_rate_label = QLabel("150")
        self.sapi_rate_slider.valueChanged.connect(
            lambda v: self.sapi_rate_label.setText(str(v))
        )
        layout.addWidget(self.sapi_rate_slider)
        layout.addWidget(self.sapi_rate_label)
        layout.addStretch()
        return w

    def _populate_sapi_voices(self) -> None:
        try:
            from app.tts.sapi_tts import SapiTTS
            voices = SapiTTS.get_available_voices()
            for v in voices:
                self.sapi_voice_combo.addItem(v["name"], v["id"])
        except Exception:
            self.sapi_voice_combo.addItem("Default", None)

    def _build_openai_options(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("API Key:"))
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_edit.setPlaceholderText("sk-…")
        self.openai_key_edit.setMinimumWidth(180)
        layout.addWidget(self.openai_key_edit)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Voice:"))
        self.openai_voice_combo = QComboBox()
        self.openai_voice_combo.addItems(presets.OPENAI_VOICES)
        layout.addWidget(self.openai_voice_combo)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Model:"))
        self.openai_model_combo = QComboBox()
        self.openai_model_combo.addItems(presets.OPENAI_MODELS)
        layout.addWidget(self.openai_model_combo)
        layout.addStretch()
        return w

    def _build_azure_options(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("API Key:"))
        self.azure_key_edit = QLineEdit()
        self.azure_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.azure_key_edit.setMinimumWidth(180)
        layout.addWidget(self.azure_key_edit)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Region:"))
        self.azure_region_edit = QLineEdit()
        self.azure_region_edit.setPlaceholderText("eastus")
        self.azure_region_edit.setFixedWidth(100)
        layout.addWidget(self.azure_region_edit)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Voice Name:"))
        self.azure_voice_edit = QLineEdit()
        self.azure_voice_edit.setPlaceholderText("en-US-JennyNeural")
        self.azure_voice_edit.setFixedWidth(160)
        layout.addWidget(self.azure_voice_edit)
        layout.addStretch()
        return w

    def _build_elevenlabs_options(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("API Key:"))
        self.elevenlabs_key_edit = QLineEdit()
        self.elevenlabs_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.elevenlabs_key_edit.setMinimumWidth(180)
        layout.addWidget(self.elevenlabs_key_edit)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Voice ID:"))
        self.elevenlabs_voice_edit = QLineEdit()
        self.elevenlabs_voice_edit.setFixedWidth(160)
        layout.addWidget(self.elevenlabs_voice_edit)
        layout.addStretch()
        return w

    def _update_tts_visibility(self) -> None:
        mode = self.tts_mode_combo.currentData()
        self.sapi_widget.setVisible(mode == "sapi")
        self.openai_widget.setVisible(mode == "openai")
        self.azure_widget.setVisible(mode == "azure")
        self.elevenlabs_widget.setVisible(mode == "elevenlabs")

    # ---- Section 7: Generate -----------------------------------------

    def _build_section_generate(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_row = QHBoxLayout()
        self.generate_btn = QPushButton("🚀 Generate Variations")
        self.generate_btn.setFixedHeight(44)
        font = self.generate_btn.font()
        font.setPointSize(13)
        font.setBold(True)
        self.generate_btn.setFont(font)
        self.generate_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(self.generate_btn, stretch=1)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(44)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addWidget(QLabel("Log:"))
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFixedHeight(120)
        layout.addWidget(self.log_edit)

        return w

    # ------------------------------------------------------------------
    # Color helpers
    # ------------------------------------------------------------------

    def _update_color_button(self, btn: QPushButton, color: str) -> None:
        """Set the background of a color-picker button."""
        btn.setStyleSheet(f"background-color: {color}; border: 1px solid #888;")
        btn.setText("")

    def _pick_font_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._font_color), self, "Pick Font Color")
        if color.isValid():
            self._font_color = color.name()
            self._update_color_button(self.font_color_btn, self._font_color)

    def _pick_bg_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._bg_color), self, "Pick Background Color")
        if color.isValid():
            self._bg_color = color.name()
            self._update_color_button(self.bg_color_btn, self._bg_color)

    # ------------------------------------------------------------------
    # File browsers
    # ------------------------------------------------------------------

    def _browse_input_video(self) -> None:
        exts = " ".join(f"*.{e}" for e in presets.VIDEO_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Input Video", "", f"Video Files ({exts})"
        )
        if path:
            self.input_video_edit.setText(path)
            self._load_thumbnail(path)

    def _browse_output_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_folder_edit.setText(path)

    def _browse_music_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if path:
            self.music_folder_edit.setText(path)

    def _load_thumbnail(self, video_path: str) -> None:
        """Try to extract a thumbnail from the video using FFmpeg."""
        try:
            from app.ffmpeg_runner import _get_ffmpeg
            import subprocess
            import sys
            import tempfile

            ffmpeg, _ = _get_ffmpeg()
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name

            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            subprocess.run(
                [ffmpeg, "-y", "-i", video_path, "-vframes", "1", "-ss", "0", tmp_path],
                capture_output=True,
                creationflags=flags,
                timeout=10,
            )
            if os.path.exists(tmp_path):
                pix = QPixmap(tmp_path)
                if not pix.isNull():
                    self.thumbnail_label.setPixmap(
                        pix.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)
                    )
                os.remove(tmp_path)
        except Exception as exc:
            logger.debug("Thumbnail extraction failed: %s", exc)

    # ------------------------------------------------------------------
    # Generate / Cancel
    # ------------------------------------------------------------------

    def _on_generate(self) -> None:
        if not self._validate_inputs():
            return

        self._save_config()

        input_video = self.input_video_edit.text().strip()
        output_folder = self.output_folder_edit.text().strip()
        n = self.variations_spin.value()

        # Collect text lists
        hooks = self._text_lines(self.hooks_edit)
        benefits = self._text_lines(self.benefits_edit)
        ctas = self._text_lines(self.ctas_edit)
        tts_scripts = self._text_lines(self.tts_scripts_edit)

        # Collect music files
        music_files = self._collect_music_files()

        # Segment settings
        shuffle_enabled = self.shuffle_check.isChecked()
        num_segments = self.segments_spin.value()

        # Generate recipes
        recipes = generate_recipes(
            n=n,
            hooks=hooks,
            benefits=benefits,
            ctas=ctas,
            tts_scripts=tts_scripts,
            music_files=music_files,
            num_segments=num_segments,
            shuffle_enabled=shuffle_enabled,
        )

        # Build settings dict
        settings = {
            "reframe_mode": self._get_reframe_mode(),
            "font_size": self.font_size_slider.value(),
            "font_color": self._font_color,
            "text_position": self.text_position_combo.currentText(),
            "text_shadow": self.shadow_check.isChecked(),
            "shuffle_enabled": shuffle_enabled,
            "num_segments": num_segments,
            "intro_dur": self.intro_dur_spin.value(),
            "outro_dur": self.outro_dur_spin.value(),
            "bg_color": self._bg_color,
            "tts_mode": self.tts_mode_combo.currentData(),
            "tts_vol": self.tts_vol_slider.value(),
            "music_vol": self.music_vol_slider.value(),
            "music_fade": self.music_fade_check.isChecked(),
        }

        tts_engine = self._build_tts_engine()

        params = {
            "input_video": input_video,
            "output_folder": output_folder,
            "num_variations": n,
            "recipes": recipes,
            "settings": settings,
            "tts_engine": tts_engine,
        }

        # Start worker
        self._worker = GenerationWorker(params, parent=self)
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self.generate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_edit.clear()

        self._worker.start()

    def _on_cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
        self.cancel_btn.setEnabled(False)

    def _on_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)

    def _on_log(self, message: str) -> None:
        self.log_edit.append(message)
        # Auto-scroll to bottom
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum()
        )

    def _on_finished(self) -> None:
        self.generate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(100)

    def _on_error(self, message: str) -> None:
        self.generate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        QMessageBox.critical(self, "Error", message)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_inputs(self) -> bool:
        input_video = self.input_video_edit.text().strip()
        if not input_video:
            QMessageBox.warning(self, "Validation", "Please select an input video.")
            return False
        if not os.path.isfile(input_video):
            QMessageBox.warning(self, "Validation", f"Input video not found:\n{input_video}")
            return False

        output_folder = self.output_folder_edit.text().strip()
        if not output_folder:
            QMessageBox.warning(self, "Validation", "Please select an output folder.")
            return False

        # Check FFmpeg availability
        try:
            from app.ffmpeg_runner import _get_ffmpeg
            _get_ffmpeg()
        except FileNotFoundError as exc:
            QMessageBox.critical(self, "FFmpeg Not Found", str(exc))
            return False

        return True

    def _get_reframe_mode(self) -> str:
        for key, rb in self._reframe_radios.items():
            if rb.isChecked():
                return key
        return "blur"

    def _text_lines(self, edit: QTextEdit) -> list[str]:
        """Return non-empty lines from a QTextEdit."""
        return [
            line.strip()
            for line in edit.toPlainText().splitlines()
            if line.strip()
        ]

    def _collect_music_files(self) -> list[str]:
        folder = self.music_folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            return []
        files = []
        for ext in presets.MUSIC_EXTENSIONS:
            for f in pathlib.Path(folder).glob(f"*.{ext}"):
                files.append(str(f))
        return files

    def _build_tts_engine(self):
        mode = self.tts_mode_combo.currentData()
        if mode == "disabled" or mode is None:
            return None
        try:
            if mode == "sapi":
                from app.tts.sapi_tts import SapiTTS
                voice_id = self.sapi_voice_combo.currentData()
                rate = self.sapi_rate_slider.value()
                return SapiTTS(voice_id=voice_id, rate=rate)
            elif mode == "openai":
                from app.tts.openai_tts import OpenAITTS
                return OpenAITTS(
                    api_key=self.openai_key_edit.text().strip(),
                    voice=self.openai_voice_combo.currentText(),
                    model=self.openai_model_combo.currentText(),
                )
            elif mode == "azure":
                from app.tts.azure_tts import AzureTTS
                return AzureTTS(
                    api_key=self.azure_key_edit.text().strip(),
                    region=self.azure_region_edit.text().strip(),
                    voice_name=self.azure_voice_edit.text().strip() or "en-US-JennyNeural",
                )
            elif mode == "elevenlabs":
                from app.tts.elevenlabs_tts import ElevenLabsTTS
                return ElevenLabsTTS(
                    api_key=self.elevenlabs_key_edit.text().strip(),
                    voice_id=self.elevenlabs_voice_edit.text().strip(),
                )
        except Exception as exc:
            logger.warning("Could not create TTS engine: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def _save_config(self) -> None:
        cfg = {
            "input_video": self.input_video_edit.text(),
            "output_folder": self.output_folder_edit.text(),
            "num_variations": self.variations_spin.value(),
            "reframe_mode": self._get_reframe_mode(),
            "hooks": self.hooks_edit.toPlainText(),
            "benefits": self.benefits_edit.toPlainText(),
            "ctas": self.ctas_edit.toPlainText(),
            "font_size": self.font_size_slider.value(),
            "font_color": self._font_color,
            "text_position": self.text_position_combo.currentText(),
            "text_shadow": self.shadow_check.isChecked(),
            "shuffle_enabled": self.shuffle_check.isChecked(),
            "num_segments": self.segments_spin.value(),
            "intro_dur": self.intro_dur_spin.value(),
            "outro_dur": self.outro_dur_spin.value(),
            "bg_color": self._bg_color,
            "tts_mode": self.tts_mode_combo.currentData(),
            "tts_scripts": self.tts_scripts_edit.toPlainText(),
            "sapi_rate": self.sapi_rate_slider.value(),
            "openai_key": self.openai_key_edit.text(),
            "openai_voice": self.openai_voice_combo.currentText(),
            "openai_model": self.openai_model_combo.currentText(),
            "azure_key": self.azure_key_edit.text(),
            "azure_region": self.azure_region_edit.text(),
            "azure_voice": self.azure_voice_edit.text(),
            "elevenlabs_key": self.elevenlabs_key_edit.text(),
            "elevenlabs_voice": self.elevenlabs_voice_edit.text(),
            "tts_vol": self.tts_vol_slider.value(),
            "music_folder": self.music_folder_edit.text(),
            "music_vol": self.music_vol_slider.value(),
            "music_fade": self.music_fade_check.isChecked(),
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except OSError as exc:
            logger.warning("Could not save config: %s", exc)

    def _load_config(self) -> None:
        if not CONFIG_PATH.exists():
            return
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as exc:
            logger.warning("Could not load config: %s", exc)
            return

        self.input_video_edit.setText(cfg.get("input_video", ""))
        self.output_folder_edit.setText(cfg.get("output_folder", ""))
        self.variations_spin.setValue(cfg.get("num_variations", presets.VARIATIONS_DEFAULT))

        mode = cfg.get("reframe_mode", "blur")
        if mode in self._reframe_radios:
            self._reframe_radios[mode].setChecked(True)

        self.hooks_edit.setPlainText(cfg.get("hooks", ""))
        self.benefits_edit.setPlainText(cfg.get("benefits", ""))
        self.ctas_edit.setPlainText(cfg.get("ctas", ""))
        self.font_size_slider.setValue(cfg.get("font_size", presets.FONT_SIZE_DEFAULT))

        self._font_color = cfg.get("font_color", presets.TEXT_COLOR_DEFAULT)
        self._update_color_button(self.font_color_btn, self._font_color)

        pos = cfg.get("text_position", "Bottom")
        if pos in presets.TEXT_POSITIONS:
            self.text_position_combo.setCurrentText(pos)

        self.shadow_check.setChecked(cfg.get("text_shadow", True))
        self.shuffle_check.setChecked(cfg.get("shuffle_enabled", False))
        self.segments_spin.setValue(cfg.get("num_segments", presets.SEGMENT_COUNT_DEFAULT))
        self.intro_dur_spin.setValue(cfg.get("intro_dur", presets.INTRO_DUR_DEFAULT))
        self.outro_dur_spin.setValue(cfg.get("outro_dur", presets.OUTRO_DUR_DEFAULT))

        self._bg_color = cfg.get("bg_color", presets.BG_COLOR_DEFAULT)
        self._update_color_button(self.bg_color_btn, self._bg_color)

        saved_mode = cfg.get("tts_mode", "disabled")
        for i in range(self.tts_mode_combo.count()):
            if self.tts_mode_combo.itemData(i) == saved_mode:
                self.tts_mode_combo.setCurrentIndex(i)
                break

        self.tts_scripts_edit.setPlainText(cfg.get("tts_scripts", ""))
        self.sapi_rate_slider.setValue(cfg.get("sapi_rate", 150))
        self.openai_key_edit.setText(cfg.get("openai_key", ""))

        ov = cfg.get("openai_voice", "alloy")
        if ov in presets.OPENAI_VOICES:
            self.openai_voice_combo.setCurrentText(ov)

        om = cfg.get("openai_model", "tts-1")
        if om in presets.OPENAI_MODELS:
            self.openai_model_combo.setCurrentText(om)

        self.azure_key_edit.setText(cfg.get("azure_key", ""))
        self.azure_region_edit.setText(cfg.get("azure_region", ""))
        self.azure_voice_edit.setText(cfg.get("azure_voice", ""))
        self.elevenlabs_key_edit.setText(cfg.get("elevenlabs_key", ""))
        self.elevenlabs_voice_edit.setText(cfg.get("elevenlabs_voice", ""))
        self.tts_vol_slider.setValue(cfg.get("tts_vol", presets.TTS_VOLUME_DEFAULT))
        self.music_folder_edit.setText(cfg.get("music_folder", ""))
        self.music_vol_slider.setValue(cfg.get("music_vol", presets.MUSIC_VOLUME_DEFAULT))
        self.music_fade_check.setChecked(cfg.get("music_fade", True))

        self._update_tts_visibility()
