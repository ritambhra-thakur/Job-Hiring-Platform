"""main URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from app import docusign_utils
from app.views import health_check, home
from video_interview.views import GoogleOAuthRedirect

schema_view = get_schema_view(
    openapi.Info(
        title="Infertalent API",
        description="API documentation for Infertalent",
        default_version="v1",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path(
        "swagger-docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
    path("users/", include("user.urls", namespace="user")),
    path("roles/", include("role.urls", namespace="role")),
    path("companies/", include("company.urls", namespace="company")),
    path("form/", include("form.urls", namespace="form")),
    path("primary_data/", include("primary_data.urls", namespace="primary_data")),
    path("scorecard/", include("scorecard.urls", namespace="scorecard")),
    path("stage/", include("stage.urls", namespace="stage")),
    path("referral/", include("referral.urls", namespace="referral")),
    path("email_template/", include("email_template.urls", namespace="email_template")),
    path("health-check/", health_check, name="health-check"),
    path("jobsite/", include("jobsite.urls", namespace="jobsite")),
    path("notification/", include("notification.urls", namespace="notification")),
    path("resume_parser/", include("resume_parser.urls", namespace="resume_parser")),
    path("organization/", include("organization.urls", namespace="organization")),
    path("url-shortener/", include("url_shortener.urls", namespace="url_shortener")),
    path("video-interview/", include("video_interview.urls", namespace="video_interview")),
    path("custom-reports/", include("custom_reports.urls", namespace="custom_reports")),
    path("scheduling/", include("scheduling.urls", namespace="scheduling")),
    # Document Signing & Oauth Redirects
    path("oauth/callback/1", GoogleOAuthRedirect),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("docusign/get-sign-url", docusign_utils.GetDocuSignURL.as_view()),
    path("docusign/callback/success", docusign_utils.DosuSignSuccess.as_view()),
]


if not settings.SERVE_FROM_S3:
    urlpatterns += [] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
