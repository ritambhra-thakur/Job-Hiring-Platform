from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "company"

urlpatterns = [
    path("api/v1/list/", views.GetAllCompany.as_view()),
    # path("api/v1/get/<int:pk>/", views.GetCompany.as_view()),
    path(
        "api/v1/get-by-domain/<slug:domain>/",
        views.GetCompanyByDomain.as_view(),
    ),
    # path("api/v1/create/", views.CreateCompany.as_view()),
    # path("api/v1/update/<int:pk>/", views.UpdateCompany.as_view()),
    # path("api/v1/delete/<int:pk>/", views.DeleteCompany.as_view()),
    # Department
    path("department/api/v1/list/", views.GetAllDepartment.as_view()),
    path("department/api/v1/op-list/", views.GetAllOpDepartment.as_view()),
    path("department/api/v1/create/", views.CreateDepartment.as_view()),
    path("department/api/v1/get/<int:pk>/", views.GetDepartment.as_view()),
    path("department/api/v1/update/<int:pk>/", views.UpdateDepartment.as_view()),
    path("department/api/v1/delete/<int:pk>/", views.DeleteDepartment.as_view()),
    # ExportCsv-Department
    path(
        "department/api/v1/export/csv/<str:department_id>/",
        views.DepartmentCSVExport.as_view(),
    ),
    # Request Demo
    path(
        "request-demo/api/v1/signup/",
        views.RequestDemoSignup.as_view(),
    ),
    path(
        "gdpr-docs/api/v1/disclosure/",
        views.GDPRDocsView.as_view(),
    ),
    path(
        "api/v1/enable-feature/",
        views.FeaturesEnalbled.as_view(),
    ),
    path(
        "api/v1/get-noofemp-list/",
        views.GetNoOfEmpList.as_view(),
    ),
    path(
        "api/v1/policy/",
        views.AddPolicy.as_view(),
    ),
    path(
        "api/v1/tnc/",
        views.AddTNC.as_view(),
    ),
]
