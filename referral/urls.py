# from currency import views as currency_view
from django.urls import path

from referral import views as currency_view
from referral import views as referral_view

from .views import *

app_name = "refferal"

urlpatterns = [
    path("refferal_policy/api/v1/list/", referral_view.GetAllReferral.as_view()),
    path("refferal_policy/api/v1/get/<int:pk>/", referral_view.GetReferral.as_view()),
    path("refferal_policy/api/v1/create/", referral_view.CreateReferral.as_view()),
    path("refferal_policy/api/v1/update/<int:pk>/", referral_view.UpdateReferral.as_view()),
    path("refferal_policy/api/v1/delete/<int:pk>/", referral_view.DeleteReferral.as_view()),
    # Currency urls
    path("currency/api/v1/list/", currency_view.GetAllCurrency.as_view()),
    path("currency/api/v1/get/<int:pk>/", currency_view.GetCurrency.as_view()),
    path("currency/api/v1/create/", currency_view.CreateCurrency.as_view()),
    path("currency/api/v1/update/<int:pk>/", currency_view.UpdateCurrency.as_view()),
    path("currency/api/vi/delete/<int:pk>/", currency_view.DeleteCurrency.as_view()),
    # CsvExport
    path(
        "refferal_policy/api/v1/export/csv/<str:referral_id>/",
        referral_view.ReferralCsvExport.as_view(),
    ),
    # SendMail
    path("sendmail/api/v1/send_referral/", referral_view.SendRefferalMail.as_view()),
    path("sendmail/api/v1/send_interview_invetation_mail/", referral_view.SendInterviewInvitationMail.as_view()),
    # Referral_list
    path("referral_list/api/v1/list/", referral_view.GetAllReferralList.as_view()),
    path("referral_list/api/v1/op-list/", referral_view.GetAllOpReferralList.as_view()),
    # RecruiterReferralList
    path("recruiter/referral_list/api/v1/list/", referral_view.GetRecruiterByReferralList.as_view()),
    path("recruiter/op-referral_list/api/v1/list/", referral_view.GetOpRecruiterByReferralList.as_view()),
    path("next_candidate/api/v1/get", referral_view.GetNextRefCandidate.as_view()),
    path("prev_candidate/api/v1/get", referral_view.GetPrevRefCandidate.as_view()),
]
