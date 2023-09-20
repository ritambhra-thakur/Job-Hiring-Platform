from rest_framework import status
from rest_framework.views import Response


EXCLUDED_APIs = (
    # User model
    "user.views.LoginView",
    "user.views.LogoutView",
    "user.views.SignUpView",
    "user.views.SignUpGuestView",
    "user.views.GetProfileByEncodedId",
    "user.views.UpdateProfileByEncodedId",
    "user.views.OtpVerificationView",
    "user.views.ResendOtpView",
    "user.views.RequestPasswordResetEmailView",
    "user.views.PasswordTokenCheckAPIView",
    "user.views.SetNewPasswordAPIView",
    "user.views.SetNewPasswordWithOldAPIView",
    "user.views.TokenRefreshView",
    "user.views.VerifyDeviceFromLink",
    "user.views.UpdateReferral",
    "user.views.MediaList",
    "user.views.CreateMedia",
    "user.views.GetMedia",
    "user.views.GetMediaByProfile",
    "user.views.UpdateMedia",
    "user.views.DeleteMedia",
    "user.views.UserActivityView",
    "user.views.SendMail",
    "user.views.UpdateEmail",
    "user.views.CustomQuestionView",
    "user.views.CustomQuestionOpView",
    "user.views.AnswerView",
    "user.views.VerifyDevice",
)


class DomainValidateMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # view_name = ".".join((view_func.__module__, view_func.__name__))
        # if view_name in EXCLUDED_APIs:
        #     return None
        # else:
        domain = request.headers.get("domain")
        try:
            if request.path.startswith("/admin"):
                return None
            if request.user.user_company.url_domain == domain:
                return None
            else:
                return Response({"msg": "Invalid user"}, status=status.HTTP_401_UNAUTHORIZED)
        except:
            return None
