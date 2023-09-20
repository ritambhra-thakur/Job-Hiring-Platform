from django.urls import path

from email_template import views as template_view

from . import views

app_name = "email_template"

urlpatterns = [
    path("api/v1/list/", template_view.GetAllEmailTemplates.as_view()),
    path("api/v1/op-list/", template_view.GetAllOpEmailTemplates.as_view()),
    path("api/v1/get/<int:pk>/", template_view.GetEmailTemplates.as_view()),
    path("api/v1/create/", template_view.CreateEmailTemplates.as_view()),
    path("api/v1/update/<int:pk>/", template_view.UpdateEmailTemplates.as_view()),
    path("api/v1/delete/<int:pk>/", template_view.DeleteEmailTemplates.as_view()),
    # Template Type
    path("api/v1/template-type/list/", template_view.GetAllTemplateType.as_view()),
]
