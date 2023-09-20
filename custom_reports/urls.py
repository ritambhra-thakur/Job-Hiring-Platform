from django.urls import path

from . import views

app_name = "custom_reports"

urlpatterns = [
    path("api/v1/custom-reports/", views.CustomReportView.as_view()),
    path("api/v1/all-custom-reports/", views.GetAllReports.as_view()),
    path("api/v1/form-data-reports/", views.FormDataReport.as_view()),
    path("api/v1/get-pipeline-reports/", views.GetPipeLineReport.as_view()),
    path("api/v1/get-candidate-reports/", views.GetCandidatesReport.as_view()),
    path("api/v1/get-new-hire-reports/", views.GetNewHiresReport.as_view()),
    path("api/v1/get-department-reports/", views.GetDepartmentReports.as_view()),
    path("api/v1/get-offer-reports/", views.GetOfferReport.as_view()),
    path("api/v1/get-hire-source-reports/", views.GetHireSourceReport.as_view()),
]
