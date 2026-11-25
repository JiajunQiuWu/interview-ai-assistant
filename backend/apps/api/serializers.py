from rest_framework import serializers

from apps.knowledge_base.models import (
    Answer,
    CandidateProfile,
    Category,
    ProfessionalExperience,
    Question,
    QuestionVariant,
    Tag,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name")


class ExperienceSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalExperience
        fields = ("id", "position", "company_or_project")


class AnswerSerializer(serializers.ModelSerializer):
    question_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Answer
        fields = ("id", "question_id", "text")


class AnswerCreateSerializer(serializers.ModelSerializer):
    question_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Answer
        fields = ("id", "question_id", "text")


class UniqueVariantTextMixin:
    def validate_text(self, value):
        question_id = (
            self.instance.question_id
            if self.instance is not None
            else self.context["view"].kwargs["question_id"]
        )
        duplicates = QuestionVariant.objects.filter(
            question_id=question_id,
            text=value,
        )
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                "Esta variante ya existe para la pregunta."
            )
        return value


class QuestionVariantSerializer(UniqueVariantTextMixin, serializers.ModelSerializer):
    question_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = QuestionVariant
        fields = ("id", "question_id", "text")


class QuestionVariantCreateSerializer(
    UniqueVariantTextMixin,
    serializers.ModelSerializer,
):
    question_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = QuestionVariant
        fields = ("id", "question_id", "text")


class QuestionSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
    )
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source="tags",
        many=True,
        write_only=True,
        required=False,
    )
    professional_experiences = ExperienceSummarySerializer(
        many=True,
        read_only=True,
    )
    professional_experience_ids = serializers.PrimaryKeyRelatedField(
        queryset=ProfessionalExperience.objects.all(),
        source="professional_experiences",
        many=True,
        write_only=True,
        required=False,
    )
    answers = AnswerSerializer(many=True, read_only=True)
    variants = QuestionVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "question",
            "category",
            "category_id",
            "tags",
            "tag_ids",
            "professional_experiences",
            "professional_experience_ids",
            "answers",
            "variants",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class QuestionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ("id", "question")


class ProfessionalExperienceSerializer(serializers.ModelSerializer):
    questions = QuestionSummarySerializer(many=True, read_only=True)
    question_ids = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.all(),
        source="questions",
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = ProfessionalExperience
        fields = (
            "id",
            "position",
            "company_or_project",
            "start_date",
            "end_date",
            "responsibilities",
            "achievements",
            "questions",
            "question_ids",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "La fecha de fin no puede ser anterior a la de inicio."}
            )
        return attrs


class CandidateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateProfile
        fields = (
            "id",
            "name",
            "professional_title",
            "summary",
            "location",
            "linkedin_url",
            "github_url",
            "portfolio_url",
        )
        read_only_fields = ("id",)
