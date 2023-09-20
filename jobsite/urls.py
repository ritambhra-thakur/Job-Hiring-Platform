from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from jobsite import views

app_name = "jobsite"
urlpatterns = [
    # JobSites
    path("api/v1/list/", views.GetAllJobSites.as_view()),
    path("api/v1/op-list/", views.GetAllOpJobSites.as_view()),
    path("api/v1/create/", views.CreateJobSites.as_view()),
    path("api/v1/get/<int:pk>/", views.GetJobSites.as_view()),
    path("api/v1/update/<int:pk>/", views.UpdateJobSites.as_view()),
    path("api/v1/delete/<int:pk>/", views.DeleteJobSites.as_view()),
]
