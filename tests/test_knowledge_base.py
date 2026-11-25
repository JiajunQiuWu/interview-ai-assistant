from datetime import date

from apps.knowledge_base.admin import (
    AnswerAdmin,
    CandidateProfileAdmin,
    ProfessionalExperienceAdmin,
    QuestionAdmin,
    QuestionVariantAdmin,
    TagAdmin,
)
from apps.knowledge_base.models import (
    Answer,
    CandidateProfile,
    Category,
    ProfessionalExperience,
    Question,
    QuestionVariant,
    Tag,
)
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse


class KnowledgeBaseTests(TestCase):
    def test_initial_categories_are_available(self):
        self.assertSetEqual(
            set(Category.objects.values_list("name", flat=True)),
            {"Recursos Humanos", "Manager", "Técnica"},
        )

    def test_question_can_be_saved_without_answers(self):
        category, _ = Category.objects.get_or_create(name="Técnica")

        question = Question.objects.create(
            category=category,
            question="¿Cómo resolverías este problema?",
        )

        self.assertEqual(question.answers.count(), 0)
        self.assertEqual(question.category, category)

    def test_question_admin_searches_relations_and_filters_by_category_and_tag(self):
        question_admin = QuestionAdmin(Question, admin.site)

        self.assertTrue(admin.site.is_registered(Category))
        self.assertTrue(admin.site.is_registered(Question))
        self.assertTrue(admin.site.is_registered(Answer))
        self.assertTrue(admin.site.is_registered(QuestionVariant))
        self.assertTrue(admin.site.is_registered(Tag))
        self.assertEqual(
            question_admin.search_fields,
            ("question", "answers__text", "variants__text", "tags__name"),
        )
        self.assertEqual(question_admin.list_filter, ("category", "tags"))
        self.assertEqual(
            tuple(inline.model for inline in question_admin.inlines),
            (Answer, QuestionVariant),
        )
        self.assertEqual(
            question_admin.filter_horizontal,
            ("professional_experiences", "tags"),
        )

    def test_related_search_returns_question_once_and_admin_permissions_are_enforced(
        self,
    ):
        category = Category.objects.get(name="Técnica")
        question = Question.objects.create(
            category=category,
            question="Pregunta para buscar coincidencias",
        )
        Answer.objects.create(question=question, text="needle answer one")
        Answer.objects.create(question=question, text="needle answer two")
        QuestionVariant.objects.create(question=question, text="needle variant one")
        QuestionVariant.objects.create(question=question, text="needle variant two")
        question.tags.add(
            Tag.objects.create(name="needle alpha"),
            Tag.objects.create(name="needle beta"),
        )

        user_model = get_user_model()
        staff_user = user_model.objects.create_user(
            username="staff-without-permissions",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(staff_user)
        question_url = reverse("admin:knowledge_base_question_changelist")
        self.assertEqual(self.client.get(question_url).status_code, 403)

        admin_user = user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        response = self.client.get(question_url, {"q": "needle"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["cl"].result_list), [question])
        change_response = self.client.get(
            reverse("admin:knowledge_base_question_change", args=[question.pk])
        )
        self.assertEqual(change_response.status_code, 200)
        self.assertEqual(len(change_response.context["inline_admin_formsets"]), 2)

    def test_related_models_are_registered_with_expected_search_fields(self):
        self.assertEqual(AnswerAdmin.search_fields, ("text", "question__question"))
        self.assertEqual(
            QuestionVariantAdmin.search_fields,
            ("text", "question__question"),
        )
        self.assertEqual(TagAdmin.search_fields, ("name",))

    def test_experience_end_date_cannot_precede_start_date(self):
        experience = ProfessionalExperience(
            position="Desarrolladora",
            company_or_project="Proyecto",
            start_date=date(2024, 5, 1),
            end_date=date(2024, 4, 30),
            responsibilities="Diseño de sistemas",
            achievements="Entrega del proyecto",
        )

        with self.assertRaises(ValidationError) as context:
            experience.full_clean()

        self.assertIn("end_date", context.exception.message_dict)

    def test_experience_relation_is_optional_and_many_to_many(self):
        category, _ = Category.objects.get_or_create(name="Técnica")
        questions = [
            Question.objects.create(category=category, question=f"Pregunta {index}")
            for index in range(2)
        ]
        experience = ProfessionalExperience.objects.create(
            position="Desarrolladora",
            company_or_project="Proyecto",
            responsibilities="Diseño de sistemas",
            achievements="Entrega del proyecto",
        )

        self.assertEqual(questions[0].professional_experiences.count(), 0)
        for question in questions:
            question.professional_experiences.add(experience)

        self.assertSetEqual(
            set(experience.questions.values_list("pk", flat=True)),
            {question.pk for question in questions},
        )

    def test_deleting_experience_preserves_linked_questions(self):
        category, _ = Category.objects.get_or_create(name="Técnica")
        question = Question.objects.create(
            category=category,
            question="¿Qué ejemplo compartirías?",
        )
        experience = ProfessionalExperience.objects.create(
            position="Desarrolladora",
            company_or_project="Proyecto",
            responsibilities="Diseño de sistemas",
            achievements="Entrega del proyecto",
        )
        question.professional_experiences.add(experience)

        experience.delete()

        self.assertTrue(Question.objects.filter(pk=question.pk).exists())
        self.assertEqual(question.professional_experiences.count(), 0)

    def test_experience_admin_searches_expected_fields(self):
        experience_admin = ProfessionalExperienceAdmin(
            ProfessionalExperience, admin.site
        )

        self.assertTrue(admin.site.is_registered(ProfessionalExperience))
        self.assertEqual(
            experience_admin.search_fields,
            ("position", "company_or_project", "achievements"),
        )
        self.assertIn(
            "professional_experiences",
            QuestionAdmin.filter_horizontal,
        )

    def test_candidate_profile_can_be_created_and_edited_in_admin_once(self):
        profile_admin = CandidateProfileAdmin(CandidateProfile, admin.site)
        self.assertTrue(admin.site.is_registered(CandidateProfile))
        self.assertEqual(
            profile_admin.list_display,
            ("name", "professional_title", "location"),
        )

        user_model = get_user_model()
        admin_user = user_model.objects.create_superuser(
            username="profile-admin",
            email="profile-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        add_url = reverse("admin:knowledge_base_candidateprofile_add")
        response = self.client.post(
            add_url,
            {
                "name": "Perfil de prueba",
                "professional_title": "",
                "summary": "",
                "location": "",
                "linkedin_url": "",
                "github_url": "",
                "portfolio_url": "",
                "_save": "Guardar",
            },
        )

        self.assertEqual(response.status_code, 302)
        profile = CandidateProfile.objects.get()
        self.assertEqual(profile.name, "Perfil de prueba")
        self.assertEqual(profile.professional_title, "")
        self.assertEqual(
            self.client.post(
                reverse(
                    "admin:knowledge_base_candidateprofile_change",
                    args=[profile.pk],
                ),
                {
                    "name": "Perfil actualizado",
                    "professional_title": "Ingeniera de software",
                    "summary": "Resumen profesional",
                    "location": "Madrid",
                    "linkedin_url": "https://linkedin.example/profile",
                    "github_url": "https://github.example/profile",
                    "portfolio_url": "",
                    "_save": "Guardar",
                },
            ).status_code,
            302,
        )
        profile.refresh_from_db()
        self.assertEqual(profile.name, "Perfil actualizado")
        self.assertEqual(profile.location, "Madrid")
        self.assertEqual(
            self.client.get(add_url).status_code,
            403,
        )

    def test_admin_creates_open_ended_experiences_and_links_multiple(self):
        category = Category.objects.get(name="Técnica")
        question = Question.objects.create(
            category=category,
            question="¿Cómo abordarías el reto?",
        )
        admin_user = get_user_model().objects.create_superuser(
            username="experience-admin",
            email="experience-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        add_url = reverse("admin:knowledge_base_professionalexperience_add")
        experiences = []
        for index in range(2):
            response = self.client.post(
                add_url,
                {
                    "position": f"Cargo {index}",
                    "company_or_project": f"Proyecto {index}",
                    "start_date": "2022-01-01",
                    "end_date": "",
                    "responsibilities": "Responsabilidad de prueba",
                    "achievements": "Logro de prueba",
                    "_save": "Guardar",
                },
            )
            self.assertEqual(response.status_code, 302)
            experiences.append(
                ProfessionalExperience.objects.get(position=f"Cargo {index}")
            )
        self.assertIsNone(experiences[0].end_date)

        change_url = reverse("admin:knowledge_base_question_change", args=[question.pk])
        change_response = self.client.get(change_url)
        self.assertEqual(change_response.status_code, 200)
        form_data = {
            "category": str(category.pk),
            "question": question.question,
            "tags": [],
            "professional_experiences": [str(item.pk) for item in experiences],
            "_save": "Guardar",
        }
        for inline_admin_formset in change_response.context["inline_admin_formsets"]:
            prefix = inline_admin_formset.formset.prefix
            form_data.update(
                {
                    f"{prefix}-TOTAL_FORMS": "0",
                    f"{prefix}-INITIAL_FORMS": "0",
                    f"{prefix}-MIN_NUM_FORMS": "0",
                    f"{prefix}-MAX_NUM_FORMS": "1000",
                }
            )
        response = self.client.post(change_url, form_data)

        self.assertEqual(response.status_code, 302)
        self.assertSetEqual(
            set(
                question.professional_experiences.values_list("pk", flat=True)
            ),
            {item.pk for item in experiences},
        )

    def test_question_related_data_and_tag_constraints(self):
        category = Category.objects.get(name="Técnica")
        question = Question.objects.create(
            category=category,
            question="Pregunta con varias respuestas",
        )
        first_answer = Answer.objects.create(question=question, text="Respuesta uno")
        second_answer = Answer.objects.create(question=question, text="Respuesta dos")
        variant = QuestionVariant.objects.create(
            question=question,
            text="Enunciado alternativo",
        )
        tag = Tag.objects.create(name="Python")
        question.tags.add(tag)

        self.assertSetEqual(
            set(question.answers.values_list("pk", flat=True)),
            {first_answer.pk, second_answer.pk},
        )
        self.assertEqual(question.variants.get(), variant)
        self.assertEqual(tag.questions.get(), question)

        duplicate_variant = QuestionVariant(
            question=question,
            text="Enunciado alternativo",
        )
        with self.assertRaises(ValidationError):
            duplicate_variant.full_clean()

    def test_deleting_question_cascades_answers_and_variants_but_keeps_tag(self):
        category = Category.objects.get(name="Técnica")
        question = Question.objects.create(
            category=category,
            question="Pregunta que se eliminará",
        )
        answer = Answer.objects.create(question=question, text="Respuesta")
        variant = QuestionVariant.objects.create(question=question, text="Variante")
        tag = Tag.objects.create(name="Conservar etiqueta")
        question.tags.add(tag)

        question.delete()

        self.assertFalse(Answer.objects.filter(pk=answer.pk).exists())
        self.assertFalse(QuestionVariant.objects.filter(pk=variant.pk).exists())
        self.assertTrue(Tag.objects.filter(pk=tag.pk).exists())

    def test_deleting_tag_preserves_question(self):
        category = Category.objects.get(name="Técnica")
        question = Question.objects.create(
            category=category,
            question="Pregunta con etiqueta",
        )
        tag = Tag.objects.create(name="Etiqueta eliminable")
        question.tags.add(tag)

        tag.delete()

        self.assertTrue(Question.objects.filter(pk=question.pk).exists())
        self.assertEqual(question.tags.count(), 0)


class LegacyAnswerDataMigrationTests(TransactionTestCase):
    def test_existing_question_answer_is_migrated_to_answer_model(self):
        migrate_from = [("knowledge_base", "0002_professionalexperience_and_more")]
        migrate_to = [("knowledge_base", "0004_exchange_keys")]
        executor = MigrationExecutor(connection)
        executor.migrate(migrate_from)

        old_apps = executor.loader.project_state(migrate_from).apps
        old_category = old_apps.get_model("knowledge_base", "Category")
        old_question = old_apps.get_model("knowledge_base", "Question")
        category = old_category.objects.create(name="Migración anterior")
        question = old_question.objects.create(
            category=category,
            question="Pregunta anterior",
            answer="Respuesta anterior",
        )
        question_id = question.pk

        try:
            executor = MigrationExecutor(connection)
            executor.migrate(migrate_to)
            migrated_apps = executor.loader.project_state(migrate_to).apps
            migrated_answer = migrated_apps.get_model("knowledge_base", "Answer")
            migrated_question = migrated_apps.get_model(
                "knowledge_base", "Question"
            ).objects.get(pk=question_id)

            self.assertEqual(
                list(
                    migrated_answer.objects.filter(question_id=question_id).values_list(
                        "text", flat=True
                    )
                ),
                ["Respuesta anterior"],
            )
            self.assertIsNotNone(migrated_question.exchange_key)
            self.assertIsNotNone(
                migrated_answer.objects.get(question_id=question_id).exchange_key
            )
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
