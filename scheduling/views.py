from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.http import HttpResponse, JsonResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from company.models import Company, ServiceProviderCreds
from form.models import AppliedPosition

from .models import WebhookTestData
from .utils import get_calendly_pat


class AddCalendlyCreds(APIView):

    """
    API used to add calendly details i.e Personal Access Token.
    Args:
        domain - Domain of the company
    Body:
        pat - Personal Access token
    Returns:
        -success message(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Add Calendly Credentials API",
        operation_summary="Add Calendly Credentials API",
        manual_parameters=[],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "pat": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        response = {}
        data = request.data
        if request.headers.get("domain") is not None:
            company = Company.objects.get(url_domain=request.headers.get("domain"))
        else:
            response["msg"] = "error"
            response["error"] = "domain is required"
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        try:
            creds, created = ServiceProviderCreds.objects.get_or_create(company=company)
            calendly_creds = {}
            calendly_creds["pat"] = data.get("pat")
        except:
            response["msg"] = "error"
            response["error"] = "no access token found. add one or enable calendly"
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        try:
            url = "https://api.calendly.com/users/me"

            headers = {"Content-Type": "application/json", "Authorization": "Bearer {}".format(data.get("pat"))}

            resp = requests.request("GET", url, headers=headers, data={})
            resp_data = resp.json()
            org_data = resp_data.get("resource")
            organization = org_data["current_organization"]
            calendly_creds["organization"] = organization
            creds.calendly = calendly_creds
            creds.save()
            response["msg"] = "success"
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            response["msg"] = "Wrong access token or no organization found."
            response["error"] = str(e)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class AddZoomCreds(APIView):

    """
    API used to add zoom details.
    Args:
        domain - Domain of the company
    Body:
        pat - Personal Access token
    Returns:
        -success message(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Add Zoom Credentials API",
        operation_summary="Add Zoom Credentials API",
        manual_parameters=[],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "client_id": openapi.Schema(type=openapi.TYPE_STRING),
                "account_id": openapi.Schema(type=openapi.TYPE_STRING),
                "client_secret": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        response = {}
        data = request.data
        if request.headers.get("domain") is not None:
            company = Company.objects.get(url_domain=request.headers.get("domain"))
        else:
            response["msg"] = "error"
            response["error"] = "domain is required"
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        try:
            creds, created = ServiceProviderCreds.objects.get_or_create(company=company)
            zoom_creds = {}
            zoom_creds["client_id"] = data.get("client_id")
            zoom_creds["account_id"] = data.get("account_id")
            zoom_creds["client_secret"] = data.get("client_secret")
            creds.zoom = zoom_creds
            creds.save()
            response["msg"] = "success"
            return Response(response, status=status.HTTP_200_OK)
        except:
            response["msg"] = "error"
            response["error"] = "no access token found. add one or enable calendly"
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class AddDocusignCreds(APIView):

    """
    API used to add docusign details.
    Args:
        domain - Domain of the company
    Body:
        user_id - Personal Access token
        account_id - Account Id from docusign Apps and Integration page
        integration_key - Integration Id of the App from docusign
        pem - pem content of the docusign account
    Returns:
        -success message(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Add Docusign Credentials API",
        operation_summary="Add Docusign Credentials API",
        manual_parameters=[],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING),
                "account_id": openapi.Schema(type=openapi.TYPE_STRING),
                "integration_key": openapi.Schema(type=openapi.TYPE_STRING),
                "pem": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        response = {}
        data = request.data
        if request.headers.get("domain") is not None:
            company = Company.objects.get(url_domain=request.headers.get("domain"))
        else:
            response["msg"] = "error"
            response["error"] = "domain is required"
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        try:
            creds, created = ServiceProviderCreds.objects.get_or_create(company=company)
            docusign_creds = {}
            docusign_creds["user_id"] = data.get("user_id")
            docusign_creds["account_id"] = data.get("account_id")
            docusign_creds["auth_id"] = data.get("integration_key")
            docusign_creds["pem"] = data.get("pem")
        except:
            response["msg"] = "error"
            response["error"] = "no access token found. add one or enable calendly"
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        try:
            creds.docusign = docusign_creds
            creds.save()
            response["msg"] = "success"
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            response["msg"] = "something went wrong"
            response["error"] = str(e)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetCalendlyLink(APIView):

    """
    API used to get calendly scheduling link of a specific user.
    Args:
        domain - Domain of the company
    Body:
        pat - Personal Access token
    Returns:
        -success message(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]

    email = openapi.Parameter(
        "email",
        in_=openapi.IN_QUERY,
        description="email",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        operation_description="Get Users Calendly Schedule Link API",
        operation_summary="Get Users Calendly Schedule Link API",
        manual_parameters=[email],
    )
    def get(self, request):
        response = {}
        data = request.GET
        if request.headers.get("domain") is not None:
            company = Company.objects.get(url_domain=request.headers.get("domain"))
        else:
            response["msg"] = "error"
            response["error"] = "domain is required"
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        try:
            creds = ServiceProviderCreds.objects.get(company=company)
            if creds.calendly:
                pat = creds.calendly.get("pat")
                if pat:
                    pass
                else:
                    response["msg"] = "error"
                    response["error"] = "no access token found. add one or enable calendly"
                    return Response(response, status=status.HTTP_400_BAD_REQUEST)
            else:
                response["msg"] = "error"
                response["error"] = "no access token found. add one or enable calendly"
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except:
            response["msg"] = "error"
            response["error"] = "no access token found. add one or enable calendly"
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        try:
            url = "https://api.calendly.com/organization_memberships"

            querystring = {"email": data.get("email"), "organization": creds.calendly.get("organization")}

            headers = {"Content-Type": "application/json", "Authorization": "Bearer {}".format(pat)}

            resp = requests.request("GET", url, headers=headers, params=querystring)
            resp_data = resp.json()
            users_data = resp_data.get("collection")
            if users_data:
                user = users_data[0]["user"]
                scheduling_url = user["scheduling_url"]
                response["scheduling_url"] = scheduling_url
                response["msg"] = "success"
                return Response(response, status=status.HTTP_200_OK)
            else:
                response["scheduling_url"] = None
                response["msg"] = "This interviewer is not in you calendly organization. Please invite him."
                return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            response["msg"] = "error"
            response["error"] = str(e)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class CalendlyWebHook(APIView):
    def post(self, request):
        try:
            data = request.data
            if "payload" in data:
                data = data.get("payload")
                print(data.get("tracking").get("utm_source"))
                email = data.get("email")
                applied_id = data.get("tracking").get("utm_source")
                print(applied_id)
                applied_obj = AppliedPosition.objects.get(id=int(applied_id))
                # Get PAT
                pat, creds = get_calendly_pat(applied_obj.company)
                if pat:
                    pass
                else:
                    WebhookTestData.objects.create(data=data, msg="creds not found")
                    return Response({"msg": "pat not found"}, status=status.HTTP_400_BAD_REQUEST)
                url = data.get("event")
                payload = {}
                headers = {
                    "Authorization": "Bearer {}".format(pat),
                }
                resp = requests.request("GET", url, headers=headers, data=payload)
                resp_data = resp.json()
                print(resp_data)
                data["resp"] = resp_data
                WebhookTestData.objects.create(data=data, msg="success")
                if "resource" in resp_data:
                    print("re")
                    print(resp_data["resource"])
                if "start_time" in resp_data:
                    print("st")
                    print(resp_data["start_date"])
                if "resource" in resp_data and "start_time" in resp_data["resource"]:
                    print("in resp")
                    temp_data = resp_data.get("resource")
                    splited_starttime = temp_data.get("start_time").split("T")
                    start_date = splited_starttime[0]
                    d = datetime.fromisoformat("2020-01-06T00:00:00.000Z"[:-1] + "+05:30")
                    ist_starttime = d + timedelta(minutes=330)
                    ist_endtime = d + timedelta(minutes=360)
                    interview_data = applied_obj.data.get("interview_schedule_data")
                    interview_data["date"] = str(start_date)
                    interview_data["start_time"] = ist_starttime.strftime("%-I:%M %p")
                    interview_data["end_time"] = ist_endtime.strftime("%-I:%M %p")
                    applied_obj.data["interview_schedule_data"] = interview_data
                    print(interview_data)
                    applied_obj.save()
                    print(applied_obj.data["interview_schedule_data"])
                    WebhookTestData.objects.create(data=data, msg="success")
            return Response({"msg": "accepted"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            temp_data = data
            temp_data["error"] = str(e)
            WebhookTestData.objects.create(data=temp_data, msg="error")
            return Response({"msg": "accepted"}, status=status.HTTP_200_OK)
