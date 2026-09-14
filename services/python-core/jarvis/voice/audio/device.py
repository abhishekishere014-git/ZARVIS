"""Audio device enumeration and hardware management."""

import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from jarvis.voice.errors import AudioDeviceError

logger = logging.getLogger("jarvis.voice.audio.device")


class AudioDeviceInfo(BaseModel):
    """Information regarding a physical or virtual audio endpoint."""
    id: int
    name: str
    max_input_channels: int = 0
    max_output_channels: int = 0
    default_sample_rate: int = 16000
    is_default_input: bool = False
    is_default_output: bool = False


class AudioDeviceManager:
    """Manages audio input and output device discovery and selection."""

    def __init__(self) -> None:
        self._sounddevice = None
        self._initialized = False
        self._probe_backend()

    def _probe_backend(self) -> None:
        """Attempts to import native sounddevice backend if installed."""
        try:
            import sounddevice as sd  # type: ignore
            self._sounddevice = sd
            self._initialized = True
        except (ImportError, OSError):
            self._sounddevice = None
            self._initialized = False

    @property
    def has_hardware_backend(self) -> bool:
        """Returns True if a physical host audio driver is available."""
        return self._sounddevice is not None

    def list_input_devices(self) -> List[AudioDeviceInfo]:
        """Lists available audio input devices (microphones)."""
        devices: List[AudioDeviceInfo] = []
        if not self._sounddevice:
            # Provide standard virtual input device
            return [
                AudioDeviceInfo(
                    id=0,
                    name="Virtual Microphone (Default)",
                    max_input_channels=1,
                    default_sample_rate=16000,
                    is_default_input=True,
                )
            ]

        try:
            device_list = self._sounddevice.query_devices()
            default_in = self._sounddevice.default.device[0]
            for idx, dev in enumerate(device_list):
                if dev.get("max_input_channels", 0) > 0:
                    devices.append(
                        AudioDeviceInfo(
                            id=idx,
                            name=str(dev.get("name", f"Device {idx}")),
                            max_input_channels=int(dev.get("max_input_channels", 1)),
                            default_sample_rate=int(dev.get("default_samplerate", 16000)),
                            is_default_input=(idx == default_in),
                        )
                    )
        except Exception as exc:
            logger.warning("Failed to query hardware input devices: %s", exc)
            return [
                AudioDeviceInfo(
                    id=0,
                    name="Virtual Fallback Microphone",
                    max_input_channels=1,
                    is_default_input=True,
                )
            ]
        return devices

    def list_output_devices(self) -> List[AudioDeviceInfo]:
        """Lists available audio output devices (speakers/headphones)."""
        devices: List[AudioDeviceInfo] = []
        if not self._sounddevice:
            return [
                AudioDeviceInfo(
                    id=0,
                    name="Virtual Speaker (Default)",
                    max_output_channels=2,
                    default_sample_rate=16000,
                    is_default_output=True,
                )
            ]

        try:
            device_list = self._sounddevice.query_devices()
            default_out = self._sounddevice.default.device[1]
            for idx, dev in enumerate(device_list):
                if dev.get("max_output_channels", 0) > 0:
                    devices.append(
                        AudioDeviceInfo(
                            id=idx,
                            name=str(dev.get("name", f"Device {idx}")),
                            max_output_channels=int(dev.get("max_output_channels", 2)),
                            default_sample_rate=int(dev.get("default_samplerate", 16000)),
                            is_default_output=(idx == default_out),
                        )
                    )
        except Exception as exc:
            logger.warning("Failed to query hardware output devices: %s", exc)
            return [
                AudioDeviceInfo(
                    id=0,
                    name="Virtual Fallback Speaker",
                    max_output_channels=2,
                    is_default_output=True,
                )
            ]
        return devices

    def get_default_input_device(self) -> AudioDeviceInfo:
        """Returns the default recording device."""
        inputs = self.list_input_devices()
        for dev in inputs:
            if dev.is_default_input:
                return dev
        return inputs[0] if inputs else AudioDeviceInfo(id=0, name="Default Input")

    def get_default_output_device(self) -> AudioDeviceInfo:
        """Returns the default playback device."""
        outputs = self.list_output_devices()
        for dev in outputs:
            if dev.is_default_output:
                return dev
        return outputs[0] if outputs else AudioDeviceInfo(id=0, name="Default Output")
