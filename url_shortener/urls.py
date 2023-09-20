from django.urls import path

from . import views

app_name = "url_shortener"

urlpatterns = [
    path("api/v1/create-short-url/", views.CreateShortURL.as_view()),
    path("api/v1/get-short-url/", views.GetCompleteURL.as_view()),
]
