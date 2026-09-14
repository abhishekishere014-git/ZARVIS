"""Pure standard-library energy/RMS Voice Activity Detector."""

import time
from jarvis.voice.audio.base import calculate_pcm_rms
from jarvis.voice.models import AudioChunk, VADResult
from jarvis.voice.vad.base import VADProvider


class EnergyVAD(VADProvider):
    """Voice Activity Detector based on adaptive RMS energy and hangover frames."""

    def __init__(
        self,
        energy_threshold: float = 500.0,
        adaptive_noise_floor: bool = True,
        noise_adaptation_rate: float = 0.05,
        hangover_frames: int = 4,
    ) -> None:
        self.energy_threshold = energy_threshold
        self.adaptive_noise_floor = adaptive_noise_floor
        self.noise_adaptation_rate = noise_adaptation_rate
        self.hangover_frames = hangover_frames

        self._noise_floor = 100.0
        self._hangover_counter = 0

    def reset(self) -> None:
        self._noise_floor = 100.0
        self._hangover_counter = 0

    def process_chunk(self, chunk: AudioChunk) -> VADResult:
        rms = calculate_pcm_rms(chunk.data)

        # Dynamic threshold: either static threshold or adaptive multiple of background noise
        active_threshold = self.energy_threshold
        if self.adaptive_noise_floor:
            active_threshold = max(self.energy_threshold, self._noise_floor * 2.5)

        raw_speech = rms >= active_threshold

        if raw_speech:
            self._hangover_counter = self.hangover_frames
            is_speech = True
        elif self._hangover_counter > 0:
            self._hangover_counter -= 1
            is_speech = True
        else:
            is_speech = False
            # Adapt noise floor slowly during confirmed silence
            if self.adaptive_noise_floor and rms > 10.0:
                self._noise_floor = (
                    (1.0 - self.noise_adaptation_rate) * self._noise_floor
                    + self.noise_adaptation_rate * rms
                )

        confidence = min(1.0, rms / max(1.0, active_threshold * 1.5)) if is_speech else 0.0

        return VADResult(
            is_speech=is_speech,
            confidence=confidence,
            energy=rms,
            timestamp=time.time(),
        )
