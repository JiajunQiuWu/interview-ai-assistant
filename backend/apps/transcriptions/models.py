from pathlib import Path

from django.db import models


class AudioRecording(models.Model):
    file_path = models.CharField("ruta del archivo", max_length=1024, unique=True)
    created_at = models.DateTimeField("fecha de registro", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "grabación de audio"
        verbose_name_plural = "grabaciones de audio"

    def __str__(self):
        return Path(self.file_path).name


class Transcription(models.Model):
    recording = models.ForeignKey(
        AudioRecording,
        on_delete=models.CASCADE,
        related_name="transcriptions",
        verbose_name="grabación",
    )
    text = models.TextField("transcripción")
    language = models.CharField("idioma", max_length=10, default="es")
    model_name = models.CharField("modelo", max_length=512)
    created_at = models.DateTimeField("fecha de transcripción", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "transcripción"
        verbose_name_plural = "transcripciones"

    def __str__(self):
        return f"{self.recording}: {self.created_at:%Y-%m-%d %H:%M}"
