from apps.knowledge_base.models import (
    Answer,
    CandidateProfile,
    Category,
    ProfessionalExperience,
    Question,
    QuestionVariant,
    Tag,
)
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase


class LocalSessionApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        user_model = get_user_model()
        self.operator = user_model.objects.create_user(
            username="operator",
            password="local-test-password",
            is_staff=True,
        )
        self.regular_user = user_model.objects.create_user(
            username="regular",
            password="local-test-password",
            is_staff=False,
        )

    def csrf_token(self, port="5173"):
        response = self.client.get(
            "/api/auth/csrf/",
            HTTP_ORIGIN=f"http://127.0.0.1:{port}",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["csrfToken"]

    def test_health_is_public_and_protected_data_distinguishes_anonymous(self):
        health = self.client.get("/api/health/")
        questions = self.client.get("/api/questions/")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"status": "ok"})
        self.assertEqual(questions.status_code, 403)
        self.assertEqual(questions.json()["code"], "not_authenticated")

    def test_login_requires_csrf_and_creates_staff_session(self):
        rejected = self.client.post(
            "/api/auth/login/",
            {"username": "operator", "password": "local-test-password"},
            format="json",
            HTTP_ORIGIN="http://127.0.0.1:5173",
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json()["code"], "csrf_failed")

        token = self.csrf_token(port="5174")
        response = self.client.post(
            "/api/auth/login/",
            {"username": "operator", "password": "local-test-password"},
            format="json",
            HTTP_ORIGIN="http://127.0.0.1:5174",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(response.json()["user"]["username"], "operator")
        self.assertTrue(response.json()["user"]["is_operator"])
        self.assertNotEqual(response.json()["csrfToken"], token)
        self.assertTrue(self.client.get("/api/auth/session/").json()["authenticated"])

    def test_login_rejects_non_staff_without_creating_a_privileged_session(self):
        token = self.csrf_token()
        response = self.client.post(
            "/api/auth/login/",
            {"username": "regular", "password": "local-test-password"},
            format="json",
            HTTP_ORIGIN="http://127.0.0.1:5173",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "login_failed")
        self.assertFalse(self.client.get("/api/auth/session/").json()["authenticated"])

    def test_non_staff_session_has_no_access_to_personal_data(self):
        self.client.force_login(self.regular_user)

        response = self.client.get("/api/profile/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "permission_denied")

    def test_session_write_requires_csrf_and_accepts_both_vite_origins(self):
        self.client.force_login(self.operator)
        category = Category.objects.create(name="API test category")
        payload = {"question": "Pregunta API", "category_id": category.pk}

        rejected = self.client.post(
            "/api/questions/",
            payload,
            format="json",
            HTTP_ORIGIN="http://127.0.0.1:5173",
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json()["code"], "csrf_failed")
        self.assertEqual(Question.objects.count(), 0)

        token = self.csrf_token(port="5174")
        accepted = self.client.post(
            "/api/questions/",
            payload,
            format="json",
            HTTP_ORIGIN="http://127.0.0.1:5174",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(Question.objects.get().question, "Pregunta API")

    def test_untrusted_origin_is_rejected_with_csrf_code(self):
        self.client.force_login(self.operator)
        token = self.csrf_token()

        response = self.client.post(
            "/api/categories/",
            {"name": "Rejected origin"},
            format="json",
            HTTP_ORIGIN="http://evil.example",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "csrf_failed")
        self.assertFalse(Category.objects.filter(name="Rejected origin").exists())

    def test_question_relations_and_nested_answer_variant_crud(self):
        self.client.force_login(self.operator)
        token = self.csrf_token()
        category = Category.objects.create(name="Técnica API")
        tag = Tag.objects.create(name="Django API")
        experience = ProfessionalExperience.objects.create(
            position="Ingeniera",
            company_or_project="Proyecto local",
            responsibilities="Diseño",
            achievements="Entrega",
        )
        origin = {"HTTP_ORIGIN": "http://127.0.0.1:5173"}
        csrf = {"HTTP_X_CSRFTOKEN": token}

        created = self.client.post(
            "/api/questions/",
            {
                "question": "¿Cómo diseñas una API?",
                "category_id": category.pk,
                "tag_ids": [tag.pk],
                "professional_experience_ids": [experience.pk],
            },
            format="json",
            **origin,
            **csrf,
        )
        self.assertEqual(created.status_code, 201, created.content)
        question_id = created.json()["id"]
        question = Question.objects.get(pk=question_id)
        self.assertEqual(question.tags.get(), tag)
        self.assertEqual(question.professional_experiences.get(), experience)

        answer = self.client.post(
            f"/api/questions/{question_id}/answers/",
            {"text": "Primero analizaría los requisitos."},
            format="json",
            **origin,
            **csrf,
        )
        variant = self.client.post(
            f"/api/questions/{question_id}/variants/",
            {"text": "¿Cómo estructurarías el diseño de una API?"},
            format="json",
            **origin,
            **csrf,
        )
        self.assertEqual(answer.status_code, 201)
        self.assertEqual(variant.status_code, 201)

        listed = self.client.get("/api/questions/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            listed.json()["results"][0]["answers"][0]["text"],
            "Primero analizaría los requisitos.",
        )

        updated = self.client.patch(
            f"/api/answers/{answer.json()['id']}/",
            {"text": "Validaría los requisitos primero."},
            format="json",
            **origin,
            **csrf,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["text"], "Validaría los requisitos primero.")

        deleted = self.client.delete(
            f"/api/variants/{variant.json()['id']}/",
            **origin,
            **csrf,
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(QuestionVariant.objects.exists())
        self.assertEqual(Answer.objects.count(), 1)

    def test_invalid_question_relation_and_experience_dates_return_field_errors(self):
        self.client.force_login(self.operator)
        token = self.csrf_token()
        headers = {
            "HTTP_ORIGIN": "http://127.0.0.1:5173",
            "HTTP_X_CSRFTOKEN": token,
        }

        invalid_question = self.client.post(
            "/api/questions/",
            {"question": "Pregunta inválida", "category_id": 9999},
            format="json",
            **headers,
        )
        invalid_experience = self.client.post(
            "/api/experiences/",
            {
                "position": "Cargo",
                "company_or_project": "Proyecto",
                "start_date": "2024-06-01",
                "end_date": "2024-05-01",
                "responsibilities": "Responsabilidad",
                "achievements": "Logro",
            },
            format="json",
            **headers,
        )

        self.assertEqual(invalid_question.status_code, 400)
        self.assertEqual(invalid_question.json()["code"], "validation_error")
        self.assertIn("category_id", invalid_question.json()["errors"])
        self.assertEqual(invalid_experience.status_code, 400)
        self.assertIn("end_date", invalid_experience.json()["errors"])
        self.assertEqual(ProfessionalExperience.objects.count(), 0)

    def test_profile_and_experience_persist_and_relationships_can_be_updated(self):
        self.client.force_login(self.operator)
        token = self.csrf_token()
        headers = {
            "HTTP_ORIGIN": "http://127.0.0.1:5173",
            "HTTP_X_CSRFTOKEN": token,
        }
        category = Category.objects.create(name="Categoría de experiencia")
        question = Question.objects.create(
            category=category,
            question="Pregunta relacionada",
        )

        missing_profile = self.client.get("/api/profile/")
        created_profile = self.client.post(
            "/api/profile/",
            {
                "name": "Operadora",
                "professional_title": "Ingeniera de software",
            },
            format="json",
            **headers,
        )
        updated_profile = self.client.patch(
            "/api/profile/",
            {"location": "Madrid"},
            format="json",
            **headers,
        )
        created_experience = self.client.post(
            "/api/experiences/",
            {
                "position": "Ingeniera",
                "company_or_project": "Proyecto local",
                "start_date": "2022-01-01",
                "end_date": None,
                "responsibilities": "Diseño de sistemas",
                "achievements": "Puesta en producción",
                "question_ids": [question.pk],
            },
            format="json",
            **headers,
        )

        self.assertEqual(missing_profile.status_code, 404)
        self.assertEqual(created_profile.status_code, 201)
        self.assertEqual(updated_profile.status_code, 200)
        self.assertEqual(updated_profile.json()["location"], "Madrid")
        self.assertEqual(
            created_experience.status_code,
            201,
            created_experience.content,
        )
        self.assertEqual(created_experience.json()["questions"][0]["id"], question.pk)
        self.assertEqual(CandidateProfile.objects.get().location, "Madrid")
        experience_id = created_experience.json()["id"]
        refreshed = self.client.get(f"/api/experiences/{experience_id}/")
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(
            refreshed.json()["questions"][0]["question"],
            "Pregunta relacionada",
        )

        updated = self.client.patch(
            f"/api/experiences/{experience_id}/",
            {"achievements": "Logro actualizado"},
            format="json",
            **headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            ProfessionalExperience.objects.get(pk=experience_id).achievements,
            "Logro actualizado",
        )

    def test_logout_requires_csrf_and_ends_operator_session(self):
        self.client.force_login(self.operator)
        rejected = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
            HTTP_ORIGIN="http://127.0.0.1:5173",
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json()["code"], "csrf_failed")

        token = self.csrf_token()
        response = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
            HTTP_ORIGIN="http://127.0.0.1:5173",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(self.client.get("/api/auth/session/").json()["authenticated"])
