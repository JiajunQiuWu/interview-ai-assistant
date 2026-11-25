from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import call, patch
from wave import open as open_wave

from apps.transcriptions.models import AudioRecording, Transcription
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from core.speech.transcriber import SpeechTranscriptionError, transcribe_file


class TranscriberTests(SimpleTestCase):
    @patch("core.speech.transcriber._create_model")
    def test_transcribes_in_spanish_and_joins_segments(self, create_model):
        model = create_model.return_value
        model.transcribe.return_value = (
            iter(
                [
                    SimpleNamespace(text=" Hola"),
                    SimpleNamespace(text=" mundo."),
                ]
            ),
            SimpleNamespace(language="es"),
        )

        result = transcribe_file(
            Path("audio.wav"),
            model_name="tiny",
            device="cpu",
        )

        self.assertEqual(result, "Hola mundo.")
        create_model.assert_called_once_with("tiny", "cpu", "int8")
        model.transcribe.assert_called_once_with(
            "audio.wav",
            language="es",
            beam_size=5,
        )


class TranscribeAudioCommandTests(TestCase):
    @patch(
        "apps.transcriptions.management.commands.transcribe_audio.transcribe_file",
        return_value="Esta es una prueba local.",
    )
    def test_command_persists_transcription_linked_to_audio(self, transcribe_mock):
        with TemporaryDirectory() as directory:
            audio_path = Path(directory) / "interview.wav"
            with open_wave(str(audio_path), "wb") as audio_file:
                audio_file.setnchannels(1)
                audio_file.setsampwidth(2)
                audio_file.setframerate(16000)
                audio_file.writeframes(b"\x00\x00" * 1600)

            for _ in range(2):
                output = StringIO()
                call_command(
                    "transcribe_audio",
                    str(audio_path),
                    model="tiny",
                    device="cpu",
                    stdout=output,
                )
                self.assertEqual(output.getvalue(), "Esta es una prueba local.\n")

        transcribe_mock.assert_has_calls(
            [
                call(
                    audio_path.resolve(),
                    model_name="tiny",
                    device="cpu",
                ),
                call(
                    audio_path.resolve(),
                    model_name="tiny",
                    device="cpu",
                ),
            ],
        )
        self.assertEqual(Transcription.objects.count(), 2)
        transcription = Transcription.objects.order_by("pk")[0]
        self.assertEqual(transcription.text, "Esta es una prueba local.")
        self.assertEqual(transcription.language, "es")
        self.assertEqual(transcription.model_name, "tiny")
        self.assertEqual(
            transcription.recording.file_path,
            str(audio_path.resolve()),
        )
        self.assertEqual(AudioRecording.objects.count(), 1)

    @patch(
        "apps.transcriptions.management.commands.transcribe_audio.transcribe_file",
        side_effect=SpeechTranscriptionError("biblioteca nativa bloqueada"),
    )
    def test_command_reports_a_local_engine_error(self, transcribe_mock):
        with TemporaryDirectory() as directory:
            audio_path = Path(directory) / "interview.wav"
            with open_wave(str(audio_path), "wb") as audio_file:
                audio_file.setnchannels(1)
                audio_file.setsampwidth(2)
                audio_file.setframerate(16000)
                audio_file.writeframes(b"\x00\x00" * 1600)

            with self.assertRaisesMessage(
                CommandError,
                "biblioteca nativa bloqueada",
            ):
                call_command(
                    "transcribe_audio",
                    str(audio_path),
                    stdout=None,
                )

        transcribe_mock.assert_called_once()
        self.assertEqual(AudioRecording.objects.count(), 0)
        self.assertEqual(Transcription.objects.count(), 0)

    @patch(
        "apps.transcriptions.management.commands.transcribe_audio.transcribe_file"
    )
    def test_command_reports_a_missing_audio_file(self, transcribe_mock):
        with self.assertRaisesMessage(
            CommandError,
            "No existe el archivo de audio:",
        ):
            call_command(
                "transcribe_audio",
                "missing-audio.wav",
                stdout=None,
            )

        transcribe_mock.assert_not_called()
        self.assertEqual(AudioRecording.objects.count(), 0)
        self.assertEqual(Transcription.objects.count(), 0)
