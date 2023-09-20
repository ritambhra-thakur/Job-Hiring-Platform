from django.urls import path

from organization import views as organization_view

from . import views

app_name = "organization"

urlpatterns = [
    path("api/v1/list/", organization_view.GetAllOrganization.as_view()),
    path("api/v1/get/<int:pk>/", organization_view.GetOrganization.as_view()),
    path("api/v1/create/", organization_view.CreateOrganization.as_view()),
    path("api/v1/update/<int:pk>/", organization_view.UpdateOrganization.as_view()),
    path("api/v1/delete/<int:pk>/", organization_view.DeleteOrganization.as_view()),
    path("api/v1/organization-export", organization_view.OrganizationCSVExport.as_view()),
]
