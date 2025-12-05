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
    max_tokens: int = 150
    input_device: int | None = None
    output_device: int | None = None


# ==============================================================================
# GUI Components
# ==============================================================================

class IrisGUI:
    """DearPyGui-based GUI for IRIS Local."""

    # Available models and voices
    MODELS = ["qwen2.5:7b", "mistral:7b", "llama3.1:8b", "phi3:mini"]
    VOICES = ["af_heart", "af_bella", "af_nicole", "am_adam", "am_michael"]

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

                # Right panel: Transcript
                with dpg.child_window(width=-1, height=400, tag="right_panel"):
                    self._create_transcript_section()

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
        """Create PTT button and VAD toggle."""
        dpg.add_spacer(height=20)
        dpg.add_separator()
        dpg.add_spacer(height=10)

        with dpg.group(horizontal=True):
            # PTT Button
            dpg.add_button(
                label="Push to Talk",
                width=150,
                height=50,
                tag="ptt_button",
                callback=self._on_ptt_click
            )

            dpg.add_spacer(width=20)

            # VAD Toggle
            with dpg.group():
                dpg.add_text("VAD Mode", color=self.COLOR_TEXT_DIM)
                dpg.add_checkbox(
                    label="Always Listening",
                    tag="vad_checkbox",
                    callback=self._on_vad_toggle
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

        # Scrollable transcript area
        with dpg.child_window(height=-1, tag="transcript_window", border=False):
            dpg.add_text("", tag="transcript_text", wrap=450)

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
        if not self.state.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _on_vad_toggle(self, sender, app_data):
        """Handle VAD checkbox toggle."""
        self.state.vad_enabled = app_data
        if self.on_vad_toggle:
            self.on_vad_toggle(app_data)

        if app_data:
            self._update_status("VAD: Listening...")
            self._start_vad_listening()
        else:
            self._update_status("Ready")
            self._stop_vad_listening()

    def _on_model_change(self, sender, app_data):
        """Handle model selection change."""
        self.state.model = app_data
        if self.iris:
            self.iris.config.ollama_model = app_data
            self._update_status(f"Model: {app_data}")

    def _on_voice_change(self, sender, app_data):
        """Handle voice selection change."""
        self.state.voice = app_data
        self._update_status(f"Voice: {app_data}")

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
        """Stop VAD-based listening."""
        self._vad_active = False
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

        # Audio buffer for speech detection
        audio_buffer = []
        is_speaking = False
        silence_samples = 0
        silence_threshold = int(0.5 * 16000)  # 0.5s silence to end
        min_samples = int(0.3 * 16000)  # Minimum 0.3s speech
        chunk_samples = 512

        # Start ffmpeg process for continuous capture
        cmd = [
            "ffmpeg",
            "-f", "pulse",
            "-i", "default",
            "-ar", "16000",
            "-ac", "1",
            "-f", "s16le",
            "-loglevel", "error",
            "pipe:1"
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bytes_per_chunk = chunk_samples * 2  # 16-bit = 2 bytes

        try:
            while self._vad_active and process.poll() is None:
                # Read chunk from ffmpeg
                data = process.stdout.read(bytes_per_chunk)
                if not data:
                    break

                # Convert to float32
                audio_int16 = np.frombuffer(data, dtype=np.int16)
                chunk = audio_int16.astype(np.float32) / 32768.0

                # Skip chunks that are too short for VAD (min 512 samples at 16kHz)
                if len(chunk) < 512:
                    continue

                # Update waveform display
                self._audio_queue.put(chunk)

                # Run VAD
                is_speech, confidence = self.iris.vad.is_speech(chunk)

                if is_speech:
                    if not is_speaking:
                        logger.info(f"[VAD] Speech detected (confidence: {confidence:.2f})")
                        is_speaking = True
                        audio_buffer = []
                        self._update_status("Listening...", self.COLOR_ACCENT)

                    audio_buffer.append(chunk)
                    silence_samples = 0
                else:
                    if is_speaking:
                        silence_samples += len(chunk)
                        audio_buffer.append(chunk)

                        if silence_samples >= silence_threshold:
                            # Speech ended - process it
                            is_speaking = False

                            if audio_buffer:
                                audio = np.concatenate(audio_buffer)

                                if len(audio) >= min_samples:
                                    duration = len(audio) / 16000
                                    logger.info(f"[VAD] Speech ended ({duration:.1f}s)")

                                    # Process in background
                                    threading.Thread(
                                        target=self._process_vad_audio,
                                        args=(audio,),
                                        daemon=True
                                    ).start()

                            audio_buffer = []
                            silence_samples = 0
                            self._update_status("VAD: Listening...", self.COLOR_SUCCESS)
        finally:
            process.terminate()
            process.wait()

    def _process_vad_audio(self, audio: np.ndarray):
        """Process audio captured by VAD with interruption support."""
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

                self.add_message("user", text)
                self._set_pipeline_status("stt", "done")
                self._set_pipeline_status("llm", "active")

                # Process with interruption enabled (uses new process_voice)
                # Note: We pass raw audio again since process_voice does its own STT
                # But we've already shown the user message, so just call LLM directly
                response = self.iris._call_llm(text)

                self._set_pipeline_status("llm", "done")
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

    def add_message(self, role: str, content: str):
        """Add a message to the transcript."""
        self.state.messages.append({"role": role, "content": content})
        self._update_transcript()

    def _update_transcript(self):
        """Update the transcript display."""
        lines = []
        for msg in self.state.messages[-20:]:  # Last 20 messages
            prefix = "You: " if msg["role"] == "user" else "IRIS: "
            lines.append(f"{prefix}{msg['content']}")

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
