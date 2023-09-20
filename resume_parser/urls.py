from django.urls import include, path

from . import views

app_name = "resume_parser"

urlpatterns = [
    path("affinda/", views.AffindaNER.as_view()),
]
