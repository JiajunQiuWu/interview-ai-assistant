from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.transcriptions.models import AudioRecording, Transcription
from core.speech.transcriber import SpeechTranscriptionError, transcribe_file


class Command(BaseCommand):
    help = "Transcribe en español un archivo de audio local."

    def add_arguments(self, parser):
        parser.add_argument("audio_file", help="Ruta del archivo de audio.")
        parser.add_argument(
            "--model",
            default="small",
            help="Modelo Faster-Whisper o ruta local del modelo (por defecto: small).",
        )
        parser.add_argument(
            "--device",
            choices=("cpu", "cuda"),
            default="cpu",
            help="Dispositivo de inferencia (por defecto: cpu).",
        )

    def handle(self, *args, **options):
        audio_path = Path(options["audio_file"]).expanduser()
        if not audio_path.is_file():
            raise CommandError(f"No existe el archivo de audio: {audio_path}")
        audio_path = audio_path.resolve()

        try:
            text = transcribe_file(
                audio_path,
                model_name=options["model"],
                device=options["device"],
            )
        except SpeechTranscriptionError as exc:
            raise CommandError(str(exc)) from exc
        recording, _ = AudioRecording.objects.get_or_create(
            file_path=str(audio_path),
        )
        Transcription.objects.create(
            recording=recording,
            text=text,
            language="es",
            model_name=options["model"],
        )
        self.stdout.write(text)
