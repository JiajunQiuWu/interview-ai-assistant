from django.contrib import admin

from apps.knowledge_base.models import (
    Answer,
    CandidateProfile,
    Category,
    ProfessionalExperience,
    Question,
    QuestionVariant,
    Tag,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "created_at", "updated_at")
    filter_horizontal = ("professional_experiences", "tags")
    list_filter = ("category", "tags")
    search_fields = (
        "question",
        "answers__text",
        "variants__text",
        "tags__name",
    )

    class AnswerInline(admin.TabularInline):
        model = Answer
        extra = 0

    class QuestionVariantInline(admin.TabularInline):
        model = QuestionVariant
        extra = 0

    inlines = (AnswerInline, QuestionVariantInline)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("text", "question")
    search_fields = ("text", "question__question")


@admin.register(QuestionVariant)
class QuestionVariantAdmin(admin.ModelAdmin):
    list_display = ("text", "question")
    search_fields = ("text", "question__question")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(ProfessionalExperience)
class ProfessionalExperienceAdmin(admin.ModelAdmin):
    list_display = ("position", "company_or_project", "start_date", "end_date")
    search_fields = ("position", "company_or_project", "achievements")


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "professional_title", "location")
    search_fields = ("name", "professional_title", "location")

    def has_add_permission(self, request):
        return not CandidateProfile.objects.exists()
