from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from user.models import User
from django.conf import settings


@require_http_methods(["GET"])
def health_check(request):
    return HttpResponse(status=200)


@require_http_methods(["GET"])
def home(request):
    context = {}

    # TODO: Will remove at code clean up
    # try:
    #     # foreign key query
    #     user = User.objects.filter(
    #         email="jignesh.kotadiya@softuvo.com",
    #         user_company__url_domain="inferq",
    #     ).exists()
    # except Exception as e:
    #     print(e)
    # return render(request, "home.html", context)
    return redirect("https://app.{}/sign_up".format(settings.DOMAIN_NAME))
