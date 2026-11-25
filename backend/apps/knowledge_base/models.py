import uuid

from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    exchange_key = models.UUIDField(
        "clave de intercambio",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    name = models.CharField("nombre", max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.name


class Question(models.Model):
    exchange_key = models.UUIDField(
        "clave de intercambio",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="questions",
        verbose_name="categoría",
    )
    question = models.TextField("pregunta")
    tags = models.ManyToManyField(
        "Tag",
        related_name="questions",
        verbose_name="etiquetas",
        blank=True,
    )
    professional_experiences = models.ManyToManyField(
        "ProfessionalExperience",
        related_name="questions",
        verbose_name="experiencias profesionales",
        blank=True,
    )
    created_at = models.DateTimeField("fecha de creación", auto_now_add=True)
    updated_at = models.DateTimeField("fecha de actualización", auto_now=True)

    class Meta:
        ordering = ["category__name", "question"]
        verbose_name = "pregunta"
        verbose_name_plural = "preguntas"

    def __str__(self):
        return self.question


class Answer(models.Model):
    exchange_key = models.UUIDField(
        "clave de intercambio",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="pregunta",
    )
    text = models.TextField("respuesta")

    class Meta:
        ordering = ["pk"]
        verbose_name = "respuesta"
        verbose_name_plural = "respuestas"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(text=""),
                name="answer_text_not_empty",
            )
        ]

    def __str__(self):
        return self.text


class QuestionVariant(models.Model):
    exchange_key = models.UUIDField(
        "clave de intercambio",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name="pregunta",
    )
    text = models.TextField("variante")

    class Meta:
        ordering = ["pk"]
        verbose_name = "variante de pregunta"
        verbose_name_plural = "variantes de pregunta"
        constraints = [
            models.UniqueConstraint(
                fields=["question", "text"],
                name="unique_variant_per_question",
            ),
            models.CheckConstraint(
                condition=~models.Q(text=""),
                name="variant_text_not_empty",
            ),
        ]

    def __str__(self):
        return self.text


class Tag(models.Model):
    exchange_key = models.UUIDField(
        "clave de intercambio",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    name = models.CharField("nombre", max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "etiqueta"
        verbose_name_plural = "etiquetas"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="tag_name_not_empty",
            )
        ]

    def __str__(self):
        return self.name


class ProfessionalExperience(models.Model):
    exchange_key = models.UUIDField(
        "clave de intercambio",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    position = models.CharField("cargo", max_length=150)
    company_or_project = models.CharField("empresa o proyecto", max_length=200)
    start_date = models.DateField("fecha de inicio", blank=True, null=True)
    end_date = models.DateField("fecha de fin", blank=True, null=True)
    responsibilities = models.TextField("responsabilidades")
    achievements = models.TextField("logros")

    class Meta:
        ordering = ["-start_date", "position"]
        verbose_name = "experiencia profesional"
        verbose_name_plural = "experiencias profesionales"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(end_date__isnull=True)
                    | models.Q(start_date__isnull=True)
                    | models.Q(end_date__gte=models.F("start_date"))
                ),
                name="experience_end_date_gte_start_date",
            )
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {
                    "end_date": (
                        "La fecha de fin no puede ser anterior a la fecha de inicio."
                    )
                }
            )

    def __str__(self):
        return f"{self.position} - {self.company_or_project}"


class CandidateProfile(models.Model):
    exchange_key = models.UUIDField(
        "clave de intercambio",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    is_singleton = models.BooleanField(default=True, editable=False, unique=True)
    name = models.CharField("nombre", max_length=150)
    professional_title = models.CharField(
        "titular profesional",
        max_length=200,
        blank=True,
    )
    summary = models.TextField("resumen", blank=True)
    location = models.CharField("ubicación", max_length=200, blank=True)
    linkedin_url = models.URLField("LinkedIn", max_length=500, blank=True)
    github_url = models.URLField("GitHub", max_length=500, blank=True)
    portfolio_url = models.URLField("portafolio", max_length=500, blank=True)

    class Meta:
        verbose_name = "perfil del candidato"
        verbose_name_plural = "perfil del candidato"

    def __str__(self):
        return self.name
