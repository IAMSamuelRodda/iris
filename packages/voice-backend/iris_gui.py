#!/usr/bin/env python3
"""
IRIS Local GUI - DearPyGui interface for the native voice client.

Features:
- Real-time waveform visualizer
- PTT button and VAD toggle
- Transcript display with conversation history
- Status indicators (STT, LLM, TTS)
- Configuration panel (model, voice settings)

Usage:
    python iris_local.py --gui
    python iris_gui.py  # Standalone

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                        IRIS Local GUI                           │
    ├──────────────────────────────┬──────────────────────────────────┤
    │                              │                                  │
    │   [Waveform Visualizer]      │   [Transcript Display]           │
    │   ████████░░░░░░░░░░░        │                                  │
    │                              │   User: Hello IRIS               │
    │   Status: Listening...       │   IRIS: Hello! How can I help?   │
    │                              │                                  │
    │   ┌─────────┐ ┌─────────┐    │   User: What's the status?       │
    │   │   PTT   │ │  VAD ◉  │    │   IRIS: All systems nominal.     │
    │   └─────────┘ └─────────┘    │                                  │
    │                              │                                  │
    ├──────────────────────────────┴──────────────────────────────────┤
    │  Config: Model [qwen2.5:7b ▾]  Voice [af_heart ▾]  Max Tokens   │
    └─────────────────────────────────────────────────────────────────┘
"""

import os
import sys
import time
import queue
import signal
import threading
import logging
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

# Voice styles module
from src.voice_styles import (
    VoiceStyleId,
    get_voice_style_names,
    get_style_id_from_name,
)

# Setup cuDNN before imports
def _setup_cudnn():
    try:
        import nvidia.cudnn
        cudnn_lib = os.path.join(os.path.dirname(nvidia.cudnn.__file__), "lib")
        if os.path.exists(cudnn_lib):
            import ctypes
            ctypes.CDLL(os.path.join(cudnn_lib, "libcudnn.so.9"), mode=ctypes.RTLD_GLOBAL)
    except:
        pass

_setup_cudnn()

import dearpygui.dearpygui as dpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ==============================================================================
# GUI State
# ==============================================================================

@dataclass
class GUIState:
    """Shared state between GUI and voice pipeline."""
    is_recording: bool = False
    is_processing: bool = False
    vad_enabled: bool = False
    vad_speech_detected: bool = False

    # Audio visualization
    waveform_data: np.ndarray = field(default_factory=lambda: np.zeros(512))

    # Status
    status_text: str = "Ready"
    stt_status: str = "idle"
    llm_status: str = "idle"
    tts_status: str = "idle"

    # Conversation
    messages: list = field(default_factory=list)

    # Config
    model: str = "qwen2.5:7b"
    voice: str = "af_heart"
    voice_style: VoiceStyleId = "normal"
    max_tokens: int = 150
    input_device: int | None = None
    output_device: int | None = None


# ==============================================================================
# GUI Components
# ==============================================================================

class IrisGUI:
    """DearPyGui-based GUI for IRIS Local."""

    # Available models, voices, and styles
    MODELS = ["qwen2.5:7b", "mistral:7b", "llama3.1:8b", "phi3:mini"]
    VOICES = ["af_heart", "af_bella", "af_nicole", "am_adam", "am_michael"]
    VOICE_STYLES = get_voice_style_names()  # ["Normal - Balanced", "Formal - Professional", ...]

    @staticmethod
    def get_audio_devices():
        """Get available audio input and output devices."""
        import sounddevice as sd
        devices = sd.query_devices()

        input_devices = [("Default", None)]
        output_devices = [("Default", None)]

        for i, dev in enumerate(devices):
            name = f"{i}: {dev['name'][:30]}"
            if dev['max_input_channels'] > 0:
                input_devices.append((name, i))
            if dev['max_output_channels'] > 0:
                output_devices.append((name, i))

        return input_devices, output_devices

    # Colors (RGBA 0-255)
    COLOR_BG = (30, 30, 40, 255)
    COLOR_PRIMARY = (100, 149, 237, 255)  # Cornflower blue
    COLOR_ACCENT = (255, 165, 0, 255)     # Orange
    COLOR_SUCCESS = (50, 205, 50, 255)    # Lime green
    COLOR_ERROR = (220, 20, 60, 255)      # Crimson
    COLOR_TEXT = (220, 220, 230, 255)
    COLOR_TEXT_DIM = (150, 150, 160, 255)

    def __init__(self, iris_local=None):
        """
        Initialize the GUI.

        Args:
            iris_local: Optional IrisLocal instance. If None, creates one.
        """
        self.iris = iris_local
        self.state = GUIState()
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._running = False

        # VAD state
        self._vad_active = False
        self._vad_thread = None
        self._vad_audio_buffer = []  # Store audio during VAD recording
        self._vad_is_speaking = False  # Track if speech is in progress

        # Processing lock to prevent audio overlap
        self._processing_lock = threading.Lock()
        self._is_processing = False

        # Get available audio devices
        self.input_devices, self.output_devices = self.get_audio_devices()
        self.input_device_names = [d[0] for d in self.input_devices]
        self.output_device_names = [d[0] for d in self.output_devices]

        # Callbacks
        self.on_ptt_start: Callable[[], None] | None = None
        self.on_ptt_stop: Callable[[], None] | None = None
        self.on_vad_toggle: Callable[[bool], None] | None = None

    def _create_iris(self):
        """Create IrisLocal instance if needed."""
        if self.iris is None:
            from iris_local import IrisLocal, IrisConfig
            config = IrisConfig()
            config.ollama_model = self.state.model
            config.max_tokens = self.state.max_tokens
            self.iris = IrisLocal(config)
            self.iris.warmup()

    def setup(self):
        """Set up the DearPyGui context and windows."""
        dpg.create_context()

        # Configure viewport
        dpg.create_viewport(
            title="IRIS Local",
            width=900,
            height=600,
            min_width=600,
            min_height=400,
        )

        # Register fonts
        with dpg.font_registry():
            # Default font (would load custom font here)
            pass

        # Create main window
        with dpg.window(label="IRIS Local", tag="main_window"):
            # Top section: Waveform + Transcript
            with dpg.group(horizontal=True):
                # Left panel: Waveform and controls
                with dpg.child_window(width=350, height=400, tag="left_panel"):
                    self._create_waveform_section()
                    self._create_control_section()

                # Right panel: Transcript + Interruption Context
                with dpg.child_window(width=-1, height=400, tag="right_panel"):
                    self._create_transcript_section()
                    dpg.add_separator()
                    self._create_interruption_section()

            # Bottom section: Config
            dpg.add_separator()
            self._create_config_section()

        # Set up theme
        self._apply_theme()

        dpg.setup_dearpygui()
        dpg.show_viewport()

        # Set main window as primary
        dpg.set_primary_window("main_window", True)

    def _create_waveform_section(self):
        """Create the waveform visualizer."""
        dpg.add_text("Audio Input", color=self.COLOR_TEXT_DIM)

        # Waveform plot
        with dpg.plot(label="", height=150, width=-1, tag="waveform_plot",
                     no_title=True, no_menus=True, no_box_select=True,
                     no_mouse_pos=True):
            dpg.add_plot_axis(dpg.mvXAxis, label="", no_tick_labels=True,
                            no_tick_marks=True, tag="waveform_x")
            dpg.add_plot_axis(dpg.mvYAxis, label="", no_tick_labels=True,
                            no_tick_marks=True, tag="waveform_y")
            dpg.set_axis_limits("waveform_x", 0, 512)
            dpg.set_axis_limits("waveform_y", -1, 1)

            # Line series for waveform
            dpg.add_line_series(
                list(range(512)),
                [0] * 512,
                parent="waveform_y",
                tag="waveform_series"
            )

        # Status indicator
        dpg.add_spacer(height=5)
        with dpg.group(horizontal=True):
            dpg.add_text("Status:", color=self.COLOR_TEXT_DIM)
            dpg.add_text("Ready", tag="status_text", color=self.COLOR_SUCCESS)

    def _create_control_section(self):
        """Create PTT button and VAD toggle (mutually exclusive modes)."""
        dpg.add_spacer(height=20)
        dpg.add_separator()
        dpg.add_spacer(height=10)

        # Mode selector with combo box
        with dpg.group(horizontal=True):
            dpg.add_text("Input Mode:", color=self.COLOR_TEXT_DIM)
            dpg.add_spacer(width=10)
            dpg.add_combo(
                items=["Push to Talk", "Always Listening (VAD)"],
                default_value="Push to Talk",
                width=180,
                tag="input_mode_combo",
                callback=self._on_input_mode_change
            )

        dpg.add_spacer(height=10)

        # PTT Button (only active in PTT mode)
        dpg.add_button(
            label="🎤 Hold to Record",
            width=200,
            height=50,
            tag="ptt_button",
            callback=self._on_ptt_click
        )

        # Pipeline status indicators
        dpg.add_spacer(height=20)
        dpg.add_text("Pipeline Status:", color=self.COLOR_TEXT_DIM)

        with dpg.group(horizontal=True):
            self._create_status_indicator("STT", "stt_indicator")
            dpg.add_spacer(width=10)
            self._create_status_indicator("LLM", "llm_indicator")
            dpg.add_spacer(width=10)
            self._create_status_indicator("TTS", "tts_indicator")


    def _create_status_indicator(self, label: str, tag: str):
        """Create a status indicator dot with label."""
        with dpg.group(horizontal=True):
            # Status dot (using text as placeholder - would use drawlist for real dot)
            dpg.add_text("●", tag=f"{tag}_dot", color=self.COLOR_TEXT_DIM)
            dpg.add_text(label, color=self.COLOR_TEXT_DIM)

    def _create_transcript_section(self):
        """Create the conversation transcript display."""
        dpg.add_text("Conversation", color=self.COLOR_TEXT_DIM)

        # Scrollable transcript area (fixed height to leave room for interruption section)
        with dpg.child_window(height=250, tag="transcript_window", border=False):
            dpg.add_text("", tag="transcript_text", wrap=450)

    def _create_interruption_section(self):
        """Create the interruption context display."""
        dpg.add_text("Interruption Context", color=self.COLOR_TEXT_DIM)

        with dpg.child_window(height=-1, tag="interruption_window", border=False):
            # Header showing if there's an active interruption
            dpg.add_text("No interruption recorded", tag="interruption_status",
                        color=self.COLOR_TEXT_DIM)

            dpg.add_spacer(height=5)

            # Intended response (what LLM generated)
            with dpg.group(horizontal=True):
                dpg.add_text("Intended:", color=self.COLOR_ACCENT)
                dpg.add_text("—", tag="interruption_intended", wrap=380)

            # Spoken up to (what was actually said)
            with dpg.group(horizontal=True):
                dpg.add_text("Spoken:", color=self.COLOR_SUCCESS)
                dpg.add_text("—", tag="interruption_spoken", wrap=380)

            # User interruption (what user said to interrupt)
            with dpg.group(horizontal=True):
                dpg.add_text("User:", color=self.COLOR_PRIMARY)
                dpg.add_text("—", tag="interruption_user", wrap=380)

    def _create_config_section(self):
        """Create the configuration panel."""
        # First row: Model, Voice, Max Tokens
        with dpg.group(horizontal=True):
            dpg.add_text("Config:", color=self.COLOR_TEXT_DIM)
            dpg.add_spacer(width=10)

            # Model selector
            dpg.add_text("Model", color=self.COLOR_TEXT_DIM)
            dpg.add_combo(
                self.MODELS,
                default_value=self.state.model,
                width=120,
                tag="model_combo",
                callback=self._on_model_change
            )

            dpg.add_spacer(width=20)

            # Voice selector
            dpg.add_text("Voice", color=self.COLOR_TEXT_DIM)
            dpg.add_combo(
                self.VOICES,
                default_value=self.state.voice,
                width=100,
                tag="voice_combo",
                callback=self._on_voice_change
            )

            dpg.add_spacer(width=20)

            # Voice style selector
            dpg.add_text("Style", color=self.COLOR_TEXT_DIM)
            dpg.add_combo(
                self.VOICE_STYLES,
                default_value=self.VOICE_STYLES[0],  # Normal - Balanced
                width=150,
                tag="voice_style_combo",
                callback=self._on_voice_style_change
            )

            dpg.add_spacer(width=20)

            # Max tokens
            dpg.add_text("Max Tokens", color=self.COLOR_TEXT_DIM)
            dpg.add_input_int(
                default_value=self.state.max_tokens,
                width=80,
                min_value=50,
                max_value=500,
                tag="max_tokens_input",
                callback=self._on_max_tokens_change
            )

        # Second row: Audio devices
        dpg.add_spacer(height=5)
        with dpg.group(horizontal=True):
            dpg.add_text("Audio:", color=self.COLOR_TEXT_DIM)
            dpg.add_spacer(width=10)

            # Input device selector
            dpg.add_text("Input", color=self.COLOR_TEXT_DIM)
            dpg.add_combo(
                self.input_device_names,
                default_value=self.input_device_names[0],
                width=200,
                tag="input_device_combo",
                callback=self._on_input_device_change
            )

            dpg.add_spacer(width=20)

            # Output device selector
            dpg.add_text("Output", color=self.COLOR_TEXT_DIM)
            dpg.add_combo(
                self.output_device_names,
                default_value=self.output_device_names[0],
                width=200,
                tag="output_device_combo",
                callback=self._on_output_device_change
            )

        # Third row: Context window usage
        dpg.add_spacer(height=5)
        with dpg.group(horizontal=True):
            dpg.add_text("Context:", color=self.COLOR_TEXT_DIM)
            dpg.add_spacer(width=5)
            dpg.add_text("0 tokens (0/10 turns)", tag="context_stats", color=self.COLOR_ACCENT)

    def _apply_theme(self):
        """Apply the dark theme."""
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, self.COLOR_BG)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (40, 40, 50, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.COLOR_TEXT)
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.COLOR_PRIMARY)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (120, 169, 255, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (80, 129, 217, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (50, 50, 60, 255))
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, self.COLOR_ACCENT)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 10)

        dpg.bind_theme(global_theme)

        # PTT button theme (larger, more prominent)
        with dpg.theme() as ptt_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.COLOR_PRIMARY)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 10)

        dpg.bind_item_theme("ptt_button", ptt_theme)

    # ==========================================================================
    # Callbacks
    # ==========================================================================

    def _on_ptt_click(self, sender, app_data):
        """Handle PTT button click."""
        # Check if PTT mode is active (radio button value 0 = PTT)
        if self.state.vad_enabled:
            logger.debug("[PTT] Ignored - VAD mode is active")
            return

        # If IRIS is speaking, trigger an interrupt
        if self.iris and self.iris._is_speaking:
            logger.info("[PTT] Triggering interrupt during speech")
            self.iris._interrupt_requested = True
            self._update_status("Interrupting...", self.COLOR_ACCENT)
            return

        # Normal PTT toggle
        if not self.state.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _on_input_mode_change(self, sender, app_data):
        """Handle input mode combo change (PTT vs VAD)."""
        # app_data is the string value from combo
        vad_enabled = ("VAD" in app_data)
        self.state.vad_enabled = vad_enabled

        if self.on_vad_toggle:
            self.on_vad_toggle(vad_enabled)

        if vad_enabled:
            # Switch to VAD mode - disable PTT button
            self._update_status("VAD: Listening...", self.COLOR_SUCCESS)
            dpg.configure_item("ptt_button", enabled=False)
            dpg.configure_item("ptt_button", label="(VAD Active)")
            self._start_vad_listening()
        else:
            # Switch to PTT mode - enable PTT button
            self._update_status("Ready")
            dpg.configure_item("ptt_button", enabled=True)
            dpg.configure_item("ptt_button", label="🎤 Hold to Record")
            self._stop_vad_listening()

        logger.info(f"[GUI] Input mode changed to: {'VAD' if vad_enabled else 'PTT'}")

    def _on_model_change(self, sender, app_data):
        """Handle model selection change."""
        self.state.model = app_data
        if self.iris:
            self.iris.config.ollama_model = app_data
            self._update_status(f"Model: {app_data}")

    def _on_voice_change(self, sender, app_data):
        """Handle voice selection change."""
        self.state.voice = app_data
        if self.iris:
            self.iris.config.tts_voice = app_data
            # Update the TTS instance's current voice
            if self.iris._tts is not None:
                self.iris._tts.current_voice = app_data
        self._update_status(f"Voice: {app_data}")
        logger.info(f"[TTS] Voice changed to: {app_data}")

    def _on_voice_style_change(self, sender, app_data):
        """Handle voice style selection change."""
        # Convert display name to style ID
        style_id = get_style_id_from_name(app_data)
        self.state.voice_style = style_id
        if self.iris:
            self.iris.config.voice_style = style_id
        self._update_status(f"Style: {app_data}")
        logger.info(f"[LLM] Voice style changed to: {style_id}")

    def _on_max_tokens_change(self, sender, app_data):
        """Handle max tokens change."""
        self.state.max_tokens = app_data
        if self.iris:
            self.iris.config.max_tokens = app_data

    def _on_input_device_change(self, sender, app_data):
        """Handle input device selection change."""
        # Find the device index from the name
        for name, idx in self.input_devices:
            if name == app_data:
                self.state.input_device = idx
                if self.iris:
                    self.iris.config.input_device = idx
                device_str = f"Input: {app_data}"
                self._update_status(device_str)
                logger.info(f"[Audio] {device_str}")
                break

    def _on_output_device_change(self, sender, app_data):
        """Handle output device selection change."""
        # Find the device index from the name
        for name, idx in self.output_devices:
            if name == app_data:
                self.state.output_device = idx
                if self.iris:
                    self.iris.config.output_device = idx
                device_str = f"Output: {app_data}"
                self._update_status(device_str)
                logger.info(f"[Audio] {device_str}")
                break

    # ==========================================================================
    # Recording Control
    # ==========================================================================

    def _start_recording(self):
        """Start audio recording."""
        self.state.is_recording = True
        dpg.configure_item("ptt_button", label="Recording... (Click to Stop)")
        self._update_status("Recording...", self.COLOR_ERROR)
        self._set_pipeline_status("stt", "active")

        if self.on_ptt_start:
            self.on_ptt_start()

    def _stop_recording(self):
        """Stop audio recording and process."""
        self.state.is_recording = False
        dpg.configure_item("ptt_button", label="Push to Talk")
        self._update_status("Processing...", self.COLOR_ACCENT)

        if self.on_ptt_stop:
            self.on_ptt_stop()

    def _start_vad_listening(self):
        """Start VAD-based listening with ffmpeg audio capture."""
        if self._vad_thread is not None and self._vad_thread.is_alive():
            return  # Already running

        self._vad_active = True
        self._vad_thread = threading.Thread(target=self._vad_loop, daemon=True)
        self._vad_thread.start()
        logger.info("[VAD] Started always-listening mode")

    def _stop_vad_listening(self):
        """Stop VAD-based listening, flushing any buffered audio."""
        # Signal the loop to stop
        self._vad_active = False

        # Flush any buffered audio if speech was in progress
        if self._vad_is_speaking and self._vad_audio_buffer:
            audio = np.concatenate(self._vad_audio_buffer)
            min_samples = int(1.0 * 16000)  # Same threshold as in loop

            if len(audio) >= min_samples:
                duration = len(audio) / 16000
                logger.info(f"[VAD] Flushing buffered audio on stop ({duration:.1f}s)")

                # Process the buffered audio
                threading.Thread(
                    target=self._process_vad_audio,
                    args=(audio,),
                    daemon=True
                ).start()
            else:
                duration = len(audio) / 16000
                logger.debug(f"[VAD] Buffered audio too short ({duration:.1f}s), discarding")

        # Clear buffer state
        self._vad_audio_buffer = []
        self._vad_is_speaking = False

        if self._vad_thread is not None:
            self._vad_thread.join(timeout=1)
            self._vad_thread = None
        logger.info("[VAD] Stopped always-listening mode")

    def _vad_loop(self):
        """VAD listening loop using ffmpeg for audio capture."""
        import subprocess

        if self.iris is None:
            logger.error("[VAD] No IRIS instance available")
            return

        # Reset instance-level buffer state (used for flush on stop)
        self._vad_audio_buffer = []
        self._vad_is_speaking = False

        silence_samples = 0
        silence_threshold = int(0.5 * 16000)  # 0.5s silence to end
        min_samples = int(1.0 * 16000)  # Minimum 1.0s speech (filter short noises)
        chunk_samples = 512

        # Use configured audio source (same as PTT)
        audio_source = getattr(self.iris.config, 'pulse_source', 'default')
        logger.info(f"[VAD] Using audio source: {audio_source}")

        # Start ffmpeg process for continuous capture
        cmd = [
            "ffmpeg",
            "-f", "pulse",
            "-i", audio_source,
            "-ar", "16000",
            "-ac", "1",
            "-f", "s16le",
            "-loglevel", "error",
            "pipe:1"
        ]

        logger.info(f"[VAD] Starting ffmpeg: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bytes_per_chunk = chunk_samples * 2  # 16-bit = 2 bytes

        # Check if process started successfully
        import time
        time.sleep(0.1)
        if process.poll() is not None:
            stderr = process.stderr.read().decode()
            logger.error(f"[VAD] ffmpeg failed to start: {stderr}")
            return

        logger.info("[VAD] ffmpeg process started, entering loop")
        chunk_count = 0

        try:
            while self._vad_active and process.poll() is None:
                # Read chunk from ffmpeg
                data = process.stdout.read(bytes_per_chunk)
                if not data:
                    logger.warning("[VAD] No data from ffmpeg")
                    break

                chunk_count += 1
                if chunk_count == 1:
                    logger.info(f"[VAD] First audio chunk received ({len(data)} bytes)")
                elif chunk_count % 100 == 0:
                    logger.debug(f"[VAD] Processed {chunk_count} chunks")

                # Convert to float32
                audio_int16 = np.frombuffer(data, dtype=np.int16)
                chunk = audio_int16.astype(np.float32) / 32768.0

                # Skip chunks that are too short for VAD (min 512 samples at 16kHz)
                if len(chunk) < 512:
                    continue

                # Update waveform display BEFORE VAD check (so UI stays responsive)
                self._audio_queue.put(chunk)

                # Run VAD (with timeout protection)
                is_speech, confidence = self.iris.vad.is_speech(chunk)

                if is_speech:
                    if not self._vad_is_speaking:
                        logger.info(f"[VAD] Speech detected (confidence: {confidence:.2f})")
                        self._vad_is_speaking = True
                        self._vad_audio_buffer = []
                        self._update_status("Listening...", self.COLOR_ACCENT)

                    self._vad_audio_buffer.append(chunk)
                    silence_samples = 0
                else:
                    if self._vad_is_speaking:
                        silence_samples += len(chunk)
                        self._vad_audio_buffer.append(chunk)

                        if silence_samples >= silence_threshold:
                            # Speech ended - process it
                            self._vad_is_speaking = False

                            if self._vad_audio_buffer:
                                audio = np.concatenate(self._vad_audio_buffer)

                                if len(audio) >= min_samples:
                                    duration = len(audio) / 16000
                                    logger.info(f"[VAD] Speech ended ({duration:.1f}s)")

                                    # Process in background
                                    threading.Thread(
                                        target=self._process_vad_audio,
                                        args=(audio,),
                                        daemon=True
                                    ).start()
                                else:
                                    duration = len(audio) / 16000
                                    logger.debug(f"[VAD] Audio too short ({duration:.1f}s < 1.0s), ignoring")

                            self._vad_audio_buffer = []
                            silence_samples = 0
                            self._update_status("VAD: Listening...", self.COLOR_SUCCESS)
        finally:
            process.terminate()
            process.wait()

    def _process_vad_audio(self, audio: np.ndarray):
        """Process audio captured by VAD with interruption support."""
        # Acquire lock to prevent overlapping responses
        if not self._processing_lock.acquire(blocking=False):
            logger.info("[VAD] Already processing, queueing audio for later")
            # TODO: Could queue this audio instead of dropping
            return

        self._is_processing = True
        try:
            self._set_pipeline_status("stt", "active")
            self._update_status("Processing...", self.COLOR_ACCENT)

            # Use full pipeline with interruption support
            # First transcribe to show user message
            text = self.iris.transcribe(audio)
            if text.strip():
                # Fill in user_interruption if this was an interruption
                if self.iris._last_interruption:
                    self.iris._last_interruption.user_interruption = text
                    self._update_interruption_context()

                self.add_message("user", text)
                self._set_pipeline_status("stt", "done")
                self._set_pipeline_status("llm", "active")

                # Process with interruption enabled (uses new process_voice)
                # Note: We pass raw audio again since process_voice does its own STT
                # But we've already shown the user message, so just call LLM directly
                response = self.iris._call_llm(text)

                self._set_pipeline_status("llm", "done")
                self._update_context_stats()
                self._set_pipeline_status("tts", "active")

                self.add_message("assistant", response)

                # Speak with interruption monitoring
                self.iris._start_vad_monitor()
                self.iris._is_speaking = True
                try:
                    spoken_text = self.iris.speak(response)

                    # Check if we were interrupted
                    if self.iris._interrupt_requested and spoken_text != response:
                        from iris_local import InterruptionEvent
                        import time
                        self.iris._last_interruption = InterruptionEvent(
                            intended_response=response,
                            spoken_up_to=spoken_text,
                            user_interruption="",  # Will be filled by next STT
                            timestamp=time.time()
                        )
                        logger.info(f"[GUI] Interruption recorded. Spoken: \"{spoken_text[:50]}...\"")
                        self._update_status("Interrupted! Listening...", self.COLOR_ACCENT)
                        self._update_interruption_context()
                finally:
                    self.iris._is_speaking = False
                    self.iris._stop_vad_monitor()

                self._set_pipeline_status("tts", "done")
            else:
                self._update_status("No speech detected", self.COLOR_ERROR)

        except Exception as e:
            logger.exception("VAD processing error")
            self._update_status(f"Error: {e}", self.COLOR_ERROR)
        finally:
            # Release processing lock
            self._is_processing = False
            self._processing_lock.release()

            self._set_pipeline_status("stt", "idle")
            self._set_pipeline_status("llm", "idle")
            self._set_pipeline_status("tts", "idle")
            if self._vad_active:
                self._update_status("VAD: Listening...", self.COLOR_SUCCESS)

    # ==========================================================================
    # UI Updates
    # ==========================================================================

    def _update_status(self, text: str, color=None):
        """Update the status text."""
        self.state.status_text = text
        dpg.set_value("status_text", text)
        if color:
            dpg.configure_item("status_text", color=color)
        else:
            dpg.configure_item("status_text", color=self.COLOR_SUCCESS)

    def _set_pipeline_status(self, component: str, status: str):
        """Update a pipeline component status indicator."""
        tag = f"{component}_indicator_dot"
        if status == "active":
            dpg.configure_item(tag, color=self.COLOR_ACCENT)
        elif status == "done":
            dpg.configure_item(tag, color=self.COLOR_SUCCESS)
        elif status == "error":
            dpg.configure_item(tag, color=self.COLOR_ERROR)
        else:  # idle
            dpg.configure_item(tag, color=self.COLOR_TEXT_DIM)

    def _update_context_stats(self):
        """Update the context window usage display."""
        stats = self.iris.get_context_stats()
        text = f"{stats['session_tokens']:,} tokens ({stats['history_turns']}/{stats['max_history_turns']} turns)"
        dpg.set_value("context_stats", text)

    def _update_interruption_context(self):
        """Update the interruption context display."""
        if self.iris is None or self.iris._last_interruption is None:
            dpg.set_value("interruption_status", "No interruption recorded")
            dpg.configure_item("interruption_status", color=self.COLOR_TEXT_DIM)
            dpg.set_value("interruption_intended", "—")
            dpg.set_value("interruption_spoken", "—")
            dpg.set_value("interruption_user", "—")
            return

        event = self.iris._last_interruption

        # Update status
        import time
        age = time.time() - event.timestamp
        if age < 60:
            status = f"Interrupted {age:.0f}s ago"
        else:
            status = f"Interrupted {age/60:.0f}m ago"
        dpg.set_value("interruption_status", status)
        dpg.configure_item("interruption_status", color=self.COLOR_ACCENT)

        # Truncate long text for display
        def truncate(text: str, max_len: int = 100) -> str:
            if len(text) > max_len:
                return text[:max_len] + "..."
            return text

        # Update fields
        dpg.set_value("interruption_intended", truncate(event.intended_response))
        dpg.set_value("interruption_spoken", truncate(event.spoken_up_to) if event.spoken_up_to else "(nothing)")
        dpg.set_value("interruption_user", event.user_interruption if event.user_interruption else "(pending...)")

    def update_waveform(self, audio_data: np.ndarray):
        """Update the waveform display with new audio data."""
        # Resample to 512 points for display
        if len(audio_data) > 512:
            indices = np.linspace(0, len(audio_data) - 1, 512, dtype=int)
            display_data = audio_data[indices]
        else:
            display_data = np.pad(audio_data, (0, 512 - len(audio_data)))

        self.state.waveform_data = display_data
        dpg.set_value("waveform_series", [list(range(512)), display_data.tolist()])

    def add_message(self, role: str, content: str, msg_type: str = "message"):
        """
        Add a message to the transcript.

        Args:
            role: "user" or "assistant"
            content: Message content
            msg_type: "message" (default), "acknowledgment", "tool_call", "tool_result"
        """
        self.state.messages.append({
            "role": role,
            "content": content,
            "type": msg_type,
        })
        self._update_transcript()

    def add_activity(self, activity_type: str, content: str):
        """
        Add an activity indicator to the transcript (tool calls, searches, etc).

        Args:
            activity_type: "tool_call", "tool_result", "acknowledgment"
            content: Activity description
        """
        self.state.messages.append({
            "role": "system",
            "content": content,
            "type": activity_type,
        })
        self._update_transcript()

    def _update_transcript(self):
        """Update the transcript display with styled messages."""
        lines = []
        for msg in self.state.messages[-30:]:  # Last 30 messages (more for activity)
            msg_type = msg.get("type", "message")
            role = msg.get("role", "")
            content = msg.get("content", "")

            if msg_type == "acknowledgment":
                # Acknowledgments shown in italics/dimmed
                lines.append(f"  💭 {content}")
            elif msg_type == "tool_call":
                # Tool calls shown with tool icon
                lines.append(f"  🔧 {content}")
            elif msg_type == "tool_result":
                # Tool results shown with result icon
                lines.append(f"  📋 {content}")
            elif role == "user":
                lines.append(f"You: {content}")
            else:
                lines.append(f"IRIS: {content}")

        dpg.set_value("transcript_text", "\n\n".join(lines))

        # Scroll to bottom
        # dpg.set_y_scroll("transcript_window", dpg.get_y_scroll_max("transcript_window"))

    # ==========================================================================
    # Main Loop
    # ==========================================================================

    def run(self):
        """Run the GUI main loop with graceful shutdown on Ctrl+C."""
        self._running = True

        # Setup signal handler for graceful quit
        def signal_handler(signum, frame):
            logger.info("[GUI] Received shutdown signal")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Create IRIS instance if needed
        self._create_iris()

        try:
            while dpg.is_dearpygui_running() and self._running:
                # Process any pending updates
                self._process_updates()

                dpg.render_dearpygui_frame()
        except KeyboardInterrupt:
            logger.info("[GUI] Keyboard interrupt - shutting down")
        finally:
            self._stop_vad_listening()
            dpg.destroy_context()
            logger.info("[GUI] Shutdown complete")

    def _process_updates(self):
        """Process any pending UI updates."""
        # Process audio queue for waveform
        try:
            while True:
                audio = self._audio_queue.get_nowait()
                self.update_waveform(audio)
        except queue.Empty:
            pass

        # Periodically update interruption context (for time display)
        # Throttle to once per second
        current_time = time.time()
        if not hasattr(self, '_last_interruption_update'):
            self._last_interruption_update = 0
        if current_time - self._last_interruption_update >= 1.0:
            self._last_interruption_update = current_time
            if self.iris and self.iris._last_interruption:
                self._update_interruption_context()

    def stop(self):
        """Stop the GUI."""
        self._running = False
        self._stop_vad_listening()


# ==============================================================================
# Standalone Entry Point
# ==============================================================================

def main():
    """Run the GUI standalone."""
    gui = IrisGUI()
    gui.setup()
    gui.run()


if __name__ == "__main__":
    main()
