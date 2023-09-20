from django.urls import path

from . import views

app_name = "scheduling"

urlpatterns = [
    path("api/v1/add-calendly-creds", views.AddCalendlyCreds.as_view()),
    path("api/v1/get-calendly-url", views.GetCalendlyLink.as_view()),
    path("api/v1/calendly-webhook", views.CalendlyWebHook.as_view()),
    path("api/v1/docusign-creds", views.AddDocusignCreds.as_view()),
    path("api/v1/zoom-creds", views.AddZoomCreds.as_view()),
]
