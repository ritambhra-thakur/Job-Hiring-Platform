from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from user import views

app_name = "user"

urlpatterns = [
    # Auth
    path("auth/api/v1/login/", views.LoginView.as_view(), name="login"),
    path("auth/api/v1/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/api/v1/signup/", views.SignUpView.as_view(), name="signup"),
    path("auth/api/v1/signup-guest/", views.SignUpGuestView.as_view(), name="signup"),
    path("auth/api/v1/get-profile-by-encoded-id/<str:id>/", views.GetProfileByEncodedId.as_view(), name="GetProfileByEncodedId"),
    path("auth/api/v1/update-profile-by-encoded-id/<str:id>/", views.UpdateProfileByEncodedId.as_view(), name="GetProfileByEncodedId"),
    path(
        "auth/api/v1/otp_verification/",
        views.OtpVerificationView.as_view(),
        name="otp-verification",
    ),
    path(
        "auth/api/v1/resend_otp/",
        views.ResendOtpView.as_view(),
        name="resend-otp",
    ),
    path(
        "auth/api/v1/forgot-password-email/",
        views.RequestPasswordResetEmailView.as_view(),
        name="forgot-password-email",
    ),
    path(
        "auth/api/v1/forgot-password/<uidb64>/<token>/",
        views.PasswordTokenCheckAPIView.as_view(),
        name="forgot-password-confirm",
    ),
    path(
        "auth/api/v1/forgot-password-complete/",
        views.SetNewPasswordAPIView.as_view(),
        name="password-reset-complete",
    ),
    path(
        "auth/api/v1/password-reset/",
        views.SetNewPasswordWithOldAPIView.as_view(),
        name="password-reset",
    ),
    path(
        "auth/api/v1/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path("auth/api/v1/verify-device/<int:otp>", views.VerifyDeviceFromLink.as_view(), name="verify-device"),
    # Profile
    # path("profile/api/v1/list/", GetAllProflie.as_view()),
    # path("profile/api/v1/create/", CreateProfile.as_view()),
    # path("profile/api/v1/delete/<int:pk>/", DeleteProfile.as_view()),
    path("profile/api/v1/get/<str:pk>/", views.GetProfile.as_view()),
    path("profile/api/v1/update/<str:pk>/", views.UpdateProfile.as_view()),
    path("profile/api/v1/update-referral/<str:pk>/", views.UpdateReferral.as_view()),
    # User
    path("api/v1/list/", views.GetAllUser.as_view()),
    path("api/v1/op-list/", views.GetAllOpUser.as_view()),
    path("op-api/v1/list/", views.OpGetAllUser.as_view()),
    path("api/v1/list/candidate/", views.GetAllCandidate.as_view()),
    path("api/v1/list/hm-and-recruiter", views.GetHMAndRecruiter.as_view()),
    path("api/v1/update/<int:pk>/", views.UpdateUser.as_view()),
    path("api/v1/delete/<int:pk>/", views.DeleteUser.as_view()),
    # Media
    path("media/api/v1/list/", views.MediaList.as_view()),
    path("media/api/v1/create/", views.CreateMedia.as_view()),
    path("media/api/v1/get/<int:pk>/", views.GetMedia.as_view()),
    path("media/api/v1/get-by-profile/<int:pk>/", views.GetMediaByProfile.as_view()),
    path("media/api/v1/update/<int:pk>/", views.UpdateMedia.as_view()),
    path("media/api/v1/delete/<int:pk>/", views.DeleteMedia.as_view()),
    # CSV Export
    path(
        "user/api/v1/export/csv/<str:company_id>/",
        views.UserCSVExport.as_view(),
    ),
    # CSV Export
    path(
        "employee/api/v1/export/csv/<str:company>/",
        views.EmployeeCSVExport.as_view(),
    ),
    # User_Activity
    path("user_activity/api/v1/list/", views.UserActivityView.as_view()),
    # candidate_source_count
    path("candidate/api/v1/candidate_source_count/", views.CandidateSourceCount.as_view()),
    # send mail
    path("sendmail/api/v1/send_mail/", views.SendMail.as_view()),
    # Updated mail
    path("updatemail/api/v1/update_mail/", views.UpdateEmail.as_view()),
    # User offers
    path("user-offer/api/v1/list/", views.UserOffersList.as_view()),
    # Team
    path("team/api/v1/single-team/", views.TeamView.as_view(), name="single-team"),
    path("team/api/v1/all-team/", views.GetAllTeam.as_view(), name="all-team"),
    # Import employee
    path("import/api/v1/employee/", views.ImportBulkEmployee.as_view(), name="import-employee"),
    # Boolean Search
    path("search/api/v1/boolean-search", views.CandidateBooleanSearch.as_view(), name="boolean-search"),
    path("custom-question/api/v1/questions", views.CustomQuestionView.as_view(), name="custom-questions"),
    path("custom-question/api/v1/op-questions", views.CustomQuestionOpView.as_view(), name="op-custom-questions"),
    path("custom-question/api/v1/get-single-question/<int:pk>", views.GetSingleCustomQuestionView.as_view(), name="get-single-question"),
    path("custom-question/api/v1/answers", views.AnswerView.as_view(), name="answers"),
    path("weather/api/v1/get", views.GetUserWeater.as_view(), name="weather"),
    path("auth/api/v1/update-email", views.ChangeCandidateEmail.as_view(), name="update-email"),
    # path("auth/api/v1/get-okta-request", views.OktaGetReqURI.as_view(), name="okta-request"),
    # path("auth/api/v1/authorization-code/callback", views.OktaCallback, name="okta-callback"),
    path("api/v1/gdpr", views.GDPRAcceptanceView.as_view(), name="gdpr"),
    path("api/v1/gdpr-analytics", views.GetGDPRAnalytics.as_view(), name="gdpr-analytics"),
    # Linkedin Data
    # path("api/v1/get-linkedin-auth", views.GetLinkedinAuthURL.as_view(), name="get-linkedin-auth"),
    # path("api/v1/linkedin/callback", views.LinkedinCallback, name="linkedin-callback"),
    path("api/v1/verify-device", views.VerifyDevice.as_view(), name="verify-device"),
]
