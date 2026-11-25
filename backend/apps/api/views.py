import json

from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from apps.api.serializers import (
    AnswerCreateSerializer,
    AnswerSerializer,
    CandidateProfileSerializer,
    CategorySerializer,
    ProfessionalExperienceSerializer,
    QuestionSerializer,
    QuestionVariantCreateSerializer,
    QuestionVariantSerializer,
    TagSerializer,
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


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "El recurso entra en conflicto con los datos existentes."
    default_code = "conflict"


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "detail": "La comprobación CSRF ha fallado.",
            "code": "csrf_failed",
            "errors": {},
        },
        status=403,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})


@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_GET
def session_status(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"authenticated": False, "user": None})
    return JsonResponse(
        {
            "authenticated": True,
            "user": {
                "username": user.get_username(),
                "is_operator": bool(user.is_staff and user.is_active),
            },
        }
    )


def _read_login_payload(request):
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


@csrf_protect
@require_POST
def login_view(request):
    payload = _read_login_payload(request)
    if payload is None:
        return JsonResponse(
            {
                "detail": "El cuerpo de la petición debe ser un objeto JSON.",
                "code": "validation_error",
                "errors": {"non_field_errors": ["JSON no válido."]},
            },
            status=400,
        )

    username = payload.get("username")
    password = payload.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return JsonResponse(
            {
                "detail": "Indica usuario y contraseña.",
                "code": "validation_error",
                "errors": {
                    "username": ["Este campo es obligatorio."],
                    "password": ["Este campo es obligatorio."],
                },
            },
            status=400,
        )

    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_staff or not user.is_active:
        return JsonResponse(
            {
                "detail": "Las credenciales no son válidas para el operador local.",
                "code": "login_failed",
                "errors": {"non_field_errors": ["Usuario o contraseña incorrectos."]},
            },
            status=400,
        )

    login(request, user)
    csrf_token_value = get_token(request)
    return JsonResponse(
        {
            "authenticated": True,
            "user": {
                "username": user.get_username(),
                "is_operator": True,
            },
            "csrfToken": csrf_token_value,
        }
    )


@csrf_protect
@require_POST
def logout_view(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "detail": "Se requiere una sesión autenticada.",
                "code": "not_authenticated",
                "errors": {},
            },
            status=403,
        )
    if not request.user.is_staff or not request.user.is_active:
        return JsonResponse(
            {
                "detail": "El usuario no tiene permisos de operador.",
                "code": "permission_denied",
                "errors": {},
            },
            status=403,
        )
    logout(request)
    return HttpResponse(status=204)


class ProtectedListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]


class ProtectedDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]


class CategoryListCreateView(ProtectedListCreateView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CategoryDetailView(ProtectedDetailView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as exc:
            raise Conflict(
                "No se puede eliminar una categoría que tiene preguntas."
            ) from exc


class TagListCreateView(ProtectedListCreateView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class TagDetailView(ProtectedDetailView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class QuestionListCreateView(ProtectedListCreateView):
    serializer_class = QuestionSerializer

    def get_queryset(self):
        queryset = (
            Question.objects.select_related("category")
            .prefetch_related(
                "tags",
                "professional_experiences",
                "answers",
                "variants",
            )
            .order_by("category__name", "question", "pk")
        )
        params = self.request.query_params
        if params.get("category"):
            queryset = queryset.filter(category_id=params["category"])
        if params.get("tag"):
            queryset = queryset.filter(tags__pk=params["tag"])
        if params.get("professional_experience"):
            queryset = queryset.filter(
                professional_experiences__pk=params["professional_experience"]
            )
        if params.get("search"):
            term = params["search"]
            queryset = queryset.filter(
                Q(question__icontains=term)
                | Q(answers__text__icontains=term)
                | Q(variants__text__icontains=term)
                | Q(tags__name__icontains=term)
            ).distinct()
        return queryset

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise Conflict(
                "La pregunta entra en conflicto con datos existentes."
            ) from exc


class QuestionDetailView(ProtectedDetailView):
    queryset = (
        Question.objects.select_related("category")
        .prefetch_related(
            "tags",
            "professional_experiences",
            "answers",
            "variants",
        )
    )
    serializer_class = QuestionSerializer

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise Conflict(
                "La pregunta entra en conflicto con datos existentes."
            ) from exc


class AnswerListCreateView(ProtectedListCreateView):
    serializer_class = AnswerSerializer

    def get_queryset(self):
        return Answer.objects.filter(question_id=self.kwargs["question_id"])

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AnswerCreateSerializer
        return AnswerSerializer

    def perform_create(self, serializer):
        question = generics.get_object_or_404(
            Question,
            pk=self.kwargs["question_id"],
        )
        try:
            serializer.save(question=question)
        except IntegrityError as exc:
            raise Conflict("No se pudo guardar la respuesta.") from exc


class AnswerDetailView(ProtectedDetailView):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer


class VariantListCreateView(ProtectedListCreateView):
    serializer_class = QuestionVariantSerializer

    def get_queryset(self):
        return QuestionVariant.objects.filter(question_id=self.kwargs["question_id"])

    def get_serializer_class(self):
        if self.request.method == "POST":
            return QuestionVariantCreateSerializer
        return QuestionVariantSerializer

    def perform_create(self, serializer):
        question = generics.get_object_or_404(
            Question,
            pk=self.kwargs["question_id"],
        )
        try:
            serializer.save(question=question)
        except IntegrityError as exc:
            raise Conflict("Esta variante ya existe para la pregunta.") from exc


class VariantDetailView(ProtectedDetailView):
    queryset = QuestionVariant.objects.all()
    serializer_class = QuestionVariantSerializer


class CandidateProfileView(generics.GenericAPIView):
    serializer_class = CandidateProfileSerializer
    permission_classes = [IsAdminUser]

    def get(self, request):
        profile = CandidateProfile.objects.first()
        if profile is None:
            return Response(
                {
                    "detail": "Todavía no hay un perfil profesional.",
                    "code": "not_found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(self.get_serializer(profile).data)

    def post(self, request):
        if CandidateProfile.objects.exists():
            raise Conflict("Ya existe el perfil profesional único.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except IntegrityError as exc:
            raise Conflict("Ya existe el perfil profesional único.") from exc
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        profile = CandidateProfile.objects.first()
        if profile is None:
            return Response(
                {
                    "detail": "Todavía no hay un perfil profesional.",
                    "code": "not_found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProfessionalExperienceListCreateView(ProtectedListCreateView):
    serializer_class = ProfessionalExperienceSerializer

    def get_queryset(self):
        queryset = ProfessionalExperience.objects.prefetch_related("questions")
        params = self.request.query_params
        if params.get("question"):
            queryset = queryset.filter(questions__pk=params["question"])
        if params.get("current", "").lower() in {"true", "1"}:
            queryset = queryset.filter(end_date__isnull=True)
        if params.get("search"):
            term = params["search"]
            queryset = queryset.filter(
                Q(position__icontains=term)
                | Q(company_or_project__icontains=term)
                | Q(responsibilities__icontains=term)
                | Q(achievements__icontains=term)
            )
        return queryset.order_by("-start_date", "position", "pk").distinct()

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise Conflict(
                "La experiencia entra en conflicto con datos existentes."
            ) from exc


class ProfessionalExperienceDetailView(ProtectedDetailView):
    queryset = ProfessionalExperience.objects.prefetch_related("questions")
    serializer_class = ProfessionalExperienceSerializer

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise Conflict(
                "La experiencia entra en conflicto con datos existentes."
            ) from exc
