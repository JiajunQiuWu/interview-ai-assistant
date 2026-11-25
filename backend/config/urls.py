from apps.api import views
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", views.health_check, name="health"),
    path("api/auth/csrf/", views.csrf_token, name="csrf-token"),
    path("api/auth/session/", views.session_status, name="session-status"),
    path("api/auth/login/", views.login_view, name="login"),
    path("api/auth/logout/", views.logout_view, name="logout"),
    path("api/categories/", views.CategoryListCreateView.as_view(), name="categories"),
    path(
        "api/categories/<int:pk>/",
        views.CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path("api/tags/", views.TagListCreateView.as_view(), name="tags"),
    path("api/tags/<int:pk>/", views.TagDetailView.as_view(), name="tag-detail"),
    path("api/questions/", views.QuestionListCreateView.as_view(), name="questions"),
    path(
        "api/questions/<int:pk>/",
        views.QuestionDetailView.as_view(),
        name="question-detail",
    ),
    path(
        "api/questions/<int:question_id>/answers/",
        views.AnswerListCreateView.as_view(),
        name="question-answers",
    ),
    path("api/answers/<int:pk>/", views.AnswerDetailView.as_view(), name="answer"),
    path(
        "api/questions/<int:question_id>/variants/",
        views.VariantListCreateView.as_view(),
        name="question-variants",
    ),
    path(
        "api/variants/<int:pk>/",
        views.VariantDetailView.as_view(),
        name="variant",
    ),
    path(
        "api/profile/",
        views.CandidateProfileView.as_view(),
        name="candidate-profile",
    ),
    path(
        "api/experiences/",
        views.ProfessionalExperienceListCreateView.as_view(),
        name="experiences",
    ),
    path(
        "api/experiences/<int:pk>/",
        views.ProfessionalExperienceDetailView.as_view(),
        name="experience-detail",
    ),
]
