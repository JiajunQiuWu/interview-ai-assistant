from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

class SpeechTranscriptionError(Exception):
    """Raised when the local speech engine cannot process an audio file."""


def _create_model(
    model_name: str,
    device: str,
    compute_type: str,
) -> WhisperModel:
    try:
        from faster_whisper import WhisperModel
    except OSError as exc:
        raise SpeechTranscriptionError(
            "Windows no pudo cargar una biblioteca nativa de Faster-Whisper. "
            "Comprueba las directivas de Control de aplicaciones."
        ) from exc
    return WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )


def transcribe_file(
    audio_path: Path,
    model_name: str = "small",
    device: Literal["cpu", "cuda"] = "cpu",
) -> str:
    compute_type = "int8" if device == "cpu" else "float16"
    try:
        model = _create_model(model_name, device, compute_type)
        segments, _ = model.transcribe(
            str(audio_path),
            language="es",
            beam_size=5,
        )
        return "".join(segment.text for segment in segments).strip()
    except (OSError, RuntimeError, ValueError) as exc:
        raise SpeechTranscriptionError(
            f"Faster-Whisper no pudo transcribir el archivo: {exc}"
        ) from exc
