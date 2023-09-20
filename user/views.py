import base64
import csv
import datetime
import hashlib
import json
import math
import os
import profile
import random
import secrets
import string
import time
from collections import Counter
from multiprocessing import managers
from random import randint
from secrets import token_urlsafe
from tkinter import E
from types import TracebackType

import openpyxl
import pandas as pd
import requests
import requests as main_req
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives, send_mail
from django.db import IntegrityError
from django.db.models import CharField, F, Q
from django.db.models import Value as V
from django.db.models.functions import Cast, Concat
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import DjangoUnicodeDecodeError, smart_bytes, smart_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from geopy.geocoders import Nominatim
from ipware import get_client_ip
from rest_framework import filters, permissions, serializers, status, viewsets
from rest_framework.decorators import permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication
from rest_framework_simplejwt.tokens import RefreshToken

from app.choices import TOKEN_TYPE_CHOICES
from app.CSVWriter import CSVWriter
from app.encryption import decrypt, encrypt
from app.response import ResponseBadRequest, ResponseInternalServerError, ResponseOk
from app.SendinSES import (
    email_verification_success,
    send,
    send_custom_email,
    send_email_otp,
    send_reset_password_mail,
)
from app.util import (
    boolean_search,
    custom_get_object,
    generate_file_name,
    generate_otp,
    generate_password,
    get_team_member,
    get_user_object,
    new_password_matches_old_password,
    paginate_data,
    read_doc,
    read_pdf,
    send_instant_notification,
    sort_data,
    validate_email,
    validate_password,
    verify_device,
)
from company.models import Company, Department, FeaturesEnabled
from form import utils as form_utils
from form.models import (
    Answer,
    AppliedPosition,
    CustomQuestion,
    OfferLetter,
    UserSelectedField,
)
from form.serializers import (
    AnswerSerailizer,
    AppliedPositionListSerializer,
    CustomQuestionSerializer,
    OfferLetterSerializer,
)
from notification.models import NotificationType
from primary_data.models import Address, City, Country, State
from role.models import Role, RolePermission
from user import serializers as user_serializers
from user.models import (
    ActivityLogs,
    DeviceVerification,
    GDPRAcceptence,
    Media,
    MediaText,
    OktaState,
    Profile,
    Team,
    Token,
    User,
)

from .utils import get_manager


# Create your views here.
class LoginView(APIView):
    """
     This POST function is responsible for login flow of User.

    Args:
        None
    Body:
        - email(mandatory)
        - password(mandatory)
        - user_company(mandatory)
    Returns:
        - serializer.data (Login Successfull) (HTTP_200_OK)
        - Invalid Password and Email (HTTP_400_BAD_REQUEST)
        - Invalid Password (HTTP_400_BAD_REQUEST)
        - Invalid Email (HTTP_400_BAD_REQUEST)
        - user_company required (HTTP_400_BAD_REQUEST)
        - email is not verified (HTTP_400_BAD_REQUEST)
        - user not found (HTTP_400_BAD_REQUEST)
        - Incorrect password (HTTP_400_BAD_REQUEST)
        - Exception text(HTTP_400_BAD_REQUEST)

    Authentication:
        None
    Raises:
        None
    """

    # Loginview set by some Views, such as a ViewSet.

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="User login API",
        operation_summary="User login API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
                "user_company": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="enter company domain (Company.url_domain) field",
                ),
            },
        ),
    )
    @csrf_exempt  # it means that view does not need any token like csrf_token
    def post(self, request):
        """
        Login user api and all fields are mentioned below
        """
        client_ip, is_routable = get_client_ip(request)
        data = request.data  # request for data
        email = data.get("email")
        password = data.get("password")
        user_company = data.get("user_company")
        serializer = user_serializers.CandidateLoginDetailSerializer(data=data, many=True)

        """by the help of this function we will get to know that email and password
        is valid or not and if not validated bad request response will be
        shown to the user
        """
        if not validate_email(email) and not validate_password(password):
            return ResponseBadRequest(
                {
                    "data": {
                        "email": ["Invalid Email"],
                        "password": ["Password length should be 5-8 characters"],  # Password requirement will be shown in case of wrong password
                    },
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Serializer error",
                }
            )

        if not validate_email(email):
            return ResponseBadRequest(
                {
                    "data": {
                        "email": ["Invalid Email"],
                    },
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Serializer error",
                }
            )
        # check if user is recruiter and if recruiter module enabled
        try:
            # role_obj.exclude(name="recruiter")
            user_obj = User.objects.get(email=email, user_role__name="recruiter", user_company__url_domain=request.headers.get("domain"))
            if FeaturesEnabled.objects.filter(feature="recruiter", enabled=False, company__url_domain=request.headers.get("domain")):
                return ResponseBadRequest(
                    {
                        "data": {
                            "message": ["Recruiter module is disbaled"],
                        },
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Serializer error",
                    }
                )
        except:
            pass
        # Password requirment will be shown in case of wrong password
        if not validate_password(password):
            return ResponseBadRequest(
                {
                    "data": {
                        "password": ["Password length should be 5-8 characters"],
                    },
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Serializer error",
                }
            )
        """
        Created a function to check that user is registered
        or not to verify the user
        """

        # try:
        #     user_object = User.objects.get(email=email)
        #     if user_object.user_role.name.lower() == "guest":
        #         token = RefreshToken.for_user(user_object)  # token refresh through ajax
        #         if not Token.objects.filter(token_type="access_token", user_id=user_object.id).exists():
        #             Token.objects.create(
        #                 user_id=user_object.id,
        #                 token=str(token.access_token),
        #                 token_type="access_token",
        #             )
        #         else:
        #             Token.objects.filter(user_id=user_object.id, token_type="access_token").update(token=str(token.access_token))
        #         serializer = user_serializers.CandidateLoginDetailSerializer(user_object)
        #         # shows the all details of candidate login
        #         return ResponseOk(
        #             {
        #                 "data": serializer.data,
        #                 "access_token": str(token.access_token),
        #                 "refresh_token": str(token),
        #                 "code": status.HTTP_200_OK,
        #                 "message": "All Countries",
        #             }
        #         )
        # except Exception as e:
        #     return ResponseBadRequest({"debug": str(e)})

        if not user_company:
            return ResponseBadRequest(
                {
                    "data": {
                        "user_company": ["user_company required"],
                    },
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Serializer error",
                }
            )  # if not then an error will be shown

        username = str(data.get("email")) + "_" + str(data.get("user_company"))
        """ username is used to get and verify data from email address
        and user company"""

        # try:
        # try:
        user_object = User.objects.get(username__iexact=username)
        if user_object.user_company.url_domain == user_company:
            pass
        else:
            return ResponseBadRequest(
                {
                    "data": {
                        "email": ["This user does not belongs to this company!"],
                    },
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Serializer error",
                }
            )
        """ user object is created to get data from user and validate i
        it """
        if user_object.user_role.name == "guest":
            return ResponseBadRequest(
                {
                    "data": {
                        "password": ["You need to register with us, look like you are a guest user"],
                    },
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "guest user",
                }
            )
        if user_object.check_password(password):
            pass
        else:
            return ResponseBadRequest(
                {
                    "data": {
                        "email": ["Incorrect password"],
                    },
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Serializer error",
                }
            )
        if not user_object.is_active:
            if user_object.last_login is None:
                current_site = user_object.user_company.url_domain
                link = "/employee/create-profile/{}/".format(user_object.encoded_id)
                return ResponseBadRequest(
                    {
                        "redirect_link": link,
                        "data": {
                            "email": ["User is in-active"],
                        },
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "User is in-active.",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": {
                            "email": ["User is in-active"],
                        },
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "User is in-active.",
                    }
                )
            # except:
            #     return ResponseBadRequest(
            #         {
            #             "data": {
            #                 "email": ["user not found"],
            #             },
            #             "code": status.HTTP_400_BAD_REQUEST,
            #             "message": "Serializer error",
            #         }
            #     )

        """ password and other field will be validated, it will
            goes to form to verify the same """
        if user_object.check_password(password):
            if "is_employee" in request.data and request.data["is_employee"]:
                if user_object.user_role.name in ["hiring manager", "admin", "candidate"]:
                    return ResponseBadRequest(
                        {
                            "data": None,
                            "code": status.HTTP_400_BAD_REQUEST,
                            "message": "Please use employee credentials",
                        }
                    )
            token = RefreshToken.for_user(user_object)  # token refresh through ajax
            device = {
                "family": request.user_agent.device.family,
                "brand": request.user_agent.device.brand,
                "model": request.user_agent.device.model,
                "os": request.user_agent.os.family,
                "ip": client_ip,
            }
            if not Token.objects.filter(token_type="access_token", user_id=user_object.id).exists():
                tokens = Token.objects.create(user_id=user_object.id, token=str(token.access_token), token_type="access_token", device=device)
            else:
                # token = Token.objects.filter(user_id=user_object.id, token_type="access_token").update(token=str(token.access_token))
                tokens = Token.objects.filter(user_id=user_object.id, token_type="access_token").order_by("-id")

                """Uncomment from here - Sends OTP"""
                # if Token.objects.filter(user_id=user_object.id, token_type="access_token", device=device).count() < 1:
                #     otp = generate_otp()
                #     context = {
                #         "first_name": user_object.first_name,
                #         "support_email": "rs1837264@gmail.com",
                #         "yes_link": "https://{}/users/auth/api/v1/verify-device/{}".format(settings.BE_DOMAIN_NAME, otp),
                #         "no_link": "https://{}/users/auth/api/v1/verify-device/{}".format(settings.BE_DOMAIN_NAME, 0),
                #         "company_name": user_object.user_company.company_name,
                #     }
                #     DeviceVerification.objects.create(user=user_object, device=device, otp=otp)
                #     from_email = settings.EMAIL_HOST_USER
                #     to_email = user_object.email
                #     body_msg = render_to_string("device-verification.html", context)
                #     msg = EmailMultiAlternatives("Verify Your Email and Device", body_msg, "Verify Your Email and Device", [to_email])
                #     msg.content_subtype = "html"
                #     msg.send()
                #     resp_data = {}
                #     resp_data["otp_sent"] = True
                #     resp_data["user_id"] = user_object.id
                #     resp_data["msg"] = "Please verify this device. Check your email."
                #     return ResponseOk(
                #         {
                #             "data": resp_data,
                #             "code": status.HTTP_200_OK,
                #             "message": "Mail sent successfully.",
                #         }
                #     )

                # if Token.objects.filter(user_id=user_object.id, token_type="access_token", device=device).count() < 1:
                #     otp = generate_otp()
                #     context = {
                #         "first_name": user_object.first_name,
                #         "support_email": "rs1837264@gmail.com",
                #         "otp": otp,
                #         "company_name": user_object.user_company.company_name,
                #     }  # hardcoded for now
                #     DeviceVerification.objects.create(user=user_object, device=device, otp=otp)
                #     from_email = settings.EMAIL_HOST_USER
                #     to_email = user_object.email
                #     body_msg = render_to_string("device-verification.html", context)
                #     msg = EmailMultiAlternatives("Verify Your Email and Device", body_msg, "Verify Your Email and Device", [to_email])
                #     msg.content_subtype = "html"
                #     msg.send()
                #     resp_data = {}
                #     resp_data["otp_sent"] = True
                #     resp_data["user_id"] = user_object.id
                #     resp_data["msg"] = "Please verify this device. Check your email."
                #     return ResponseOk(
                #         {
                #             "data": resp_data,
                #             "code": status.HTTP_200_OK,
                #             "message": "All Countries",
                #         }
                #     )
                # else:
                #     pass
                """To here"""

                """Uncomment from here - Sends YES/NO"""
                # if Token.objects.filter(user_id=user_object.id, token_type="access_token", device=device).count() < 1:
                #     context = {
                #         "first_name": user_object.first_name,
                #         "support_email": "rs1837264@gmail.com",
                #         "company_name": user_object.user_company.company_name,
                #     }
                #     DeviceVerification.objects.create(user=user_object, device=device)
                #     from_email = settings.EMAIL_HOST_USER
                #     to_email = user_object.email
                #     body_msg = render_to_string("device-verification.html", context)
                #     msg = EmailMultiAlternatives("Verify Your Email and Device", body_msg, "Verify Your Email and Device", [to_email])
                #     msg.content_subtype = "html"
                #     msg.send()
                #     resp_data = {}
                #     resp_data["otp_sent"] = True
                #     resp_data["user_id"] = user_object.id
                #     resp_data["msg"] = "Please verify this device. Check your email."
                #     return ResponseOk(
                #         {
                #             "data": resp_data,
                #             "code": status.HTTP_200_OK,
                #             "message": "All Countries",
                #         }
                #     )
                # else:
                #     pass
                """To here"""

                tokens = tokens.first()
                # sort both device dict and compare
            serializer = user_serializers.CandidateLoginDetailSerializer(user_object)
            # shows the all details of candidate login
            return ResponseOk(
                {
                    "data": serializer.data,
                    "access_token": str(token.access_token),
                    "refresh_token": str(token),
                    "code": status.HTTP_200_OK,
                    "message": "login success",
                }
            )

            # return ResponseOk(
            #     {
            #         "result": "ok",
            #         "access_token": str(token.access_token),
            #         "refresh_token": str(token),
            #         "user_role_id": user_object.user_role_id,
            #         "user_role_slug": user_object.user_role.slug,
            #         "first_name": user_object.first_name,
            #         "last_name": user_object.last_name,
            #         "email_verified": user_object.email_verified,
            #         "email": user_object.email,
            #         "id": user_object.id,
            #         "avatar": "users/api/v1/avatar/{}/?c={}".format(
            #             user_object.id, randint(10000, 99999)
            #         ),
            #     }
            # )

        else:
            return ResponseBadRequest(
                {
                    "data": {
                        "password": ["Incorrect password"],
                    },
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Serializer error",
                }
            )

        # except Exception as e:
        #     return ResponseBadRequest({"debug": str(e)})


class LogoutView(APIView):
    """
    This POST function logouts a user session.

    Args:
        None
    Body:
        None
    Returns:
        -Serialized COUNTRY model data(HTTP_200_OK)
        -Search query has no match(HTTP_400_BAD_REQUEST)
        -Exception text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Log the authenticated user out",
        operation_summary="Log the authenticated user out",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        serializer = user_serializers.LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SignUpView(APIView):
    """
    This POST function Sign up a particular User and saves required fields in Database..

    Args:
        None
    Body:
        - first_name(Mandatory)
        - middle_name(Mandatory)
        - email(Mandatory)
        - last_name(Mandatory)
        - phone_no(Mandatory)
        - password(Mandatory)
        - user_role(Mandatory)
        - user_company(Mandatory)
    Returns:
        - We have sent you a link to reset your password(HTTP_200_OK)
        - User created and OTP Send successfully(HTTP_200_OK)
        - Email Already Exist(HTTP_400_BAD_REQUEST)
        - serializer errors(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]  # allow any user
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="User Sign up API",
        operation_summary="User Sign up API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                "middle_name": openapi.Schema(type=openapi.TYPE_STRING),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "phone_no": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
                "user_role": openapi.Schema(type=openapi.TYPE_INTEGER, description="enter role id"),
                "user_company": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="enter company domain (Company.url_domain) field",
                ),
                "redirect_url": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="enter redirect url example: https://soft.infertalents.com",
                ),
            },
        ),
    )

    # which means no csrf_token is required in this decorator
    @csrf_exempt
    def post(self, request):
        """
        signup user with any role and send verification email
        """
        data = request.data
        serializer = user_serializers.CandidateSignUpSerializer(data=data)
        username = str(data.get("email")) + "_" + str(data.get("user_company"))
        data["username"] = username
        try:
            role_obj = Role.objects.get(id=data.get("user_role"))
        except Role.DoesNotExist:
            return ResponseBadRequest(
                {
                    "data": {"user_role": ["User Role Does Not Exists"]},
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Role Does not Exists",
                }
            )
        try:
            user_obj = User.objects.get(email=data.get("email"), user_role=role_obj, user_company__url_domain=data.get("user_company"))
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "User already exists.",
                }
            )
        except:
            pass
        try:
            usr_obj = User.objects.get(username=username)
            if usr_obj.user_role.name == "guest":
                return ResponseBadRequest(
                    {
                        "data": "Guest User",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "This is Guest User, please hit sign-up guest API",
                    }
                )
        except User.DoesNotExist:
            pass

        if data.get("redirect_url"):
            redirect_url = data.get("redirect_url")
        else:
            redirect_url = ""

        if User.objects.filter(username=username, email_verified=True).exists():
            return ResponseBadRequest(
                {
                    "data": {"email": ["Email Already Exist"]},
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Serializer error",
                }
            )
        else:
            if role_obj.name == "guest":
                if serializer.is_valid():
                    user_object = serializer.save()
                    user_object.is_active = True
                    user_object.save()
                    user_serializer = user_serializers.GetUserSerializer(user_object)

                    token = RefreshToken.for_user(user_object)  # token refresh through ajax
                    if not Token.objects.filter(token_type="access_token", user_id=user_object.id).exists():
                        Token.objects.create(
                            user_id=user_object.id,
                            token=str(token.access_token),
                            token_type="access_token",
                        )
                    else:
                        Token.objects.filter(user_id=user_object.id, token_type="access_token").update(token=str(token.access_token))
                    # shows the all details of candidate login
                    return ResponseOk(
                        {
                            "data": user_serializer.data,
                            "access_token": str(token.access_token),
                            "refresh_token": str(token),
                            "code": status.HTTP_200_OK,
                            "message": "Guest User Signed up Successfully.",
                        }
                    )

                else:
                    return ResponseBadRequest(
                        {
                            "data": serializer.errors,
                            "code": status.HTTP_400_BAD_REQUEST,
                            "message": "Serializer error",
                        }
                    )
            print(redirect_url)
            if redirect_url:
                if serializer.is_valid():
                    user_object = serializer.save()

                    user_object = User.objects.filter(id=user_object.id)[0]
                    user_object.is_active = True
                    user_object.email_verified = True
                    user_object.save()

                    uidb64 = urlsafe_base64_encode(smart_bytes(user_object.id))
                    token = PasswordResetTokenGenerator().make_token(user_object)
                    current_site = get_current_site(request=request).domain
                    relativeLink = reverse(
                        "user:forgot-password-confirm",
                        kwargs={"uidb64": uidb64, "token": token},
                    )

                    absurl = "https://" + current_site + relativeLink + "?redirect_url=" + redirect_url
                    email_body = "Hello, \n Use link below to reset your password  \n" + absurl

                    send_reset_password_mail(request, user_object.email, email_body)
                    return Response(
                        {"success": "We have sent you a link to reset your password"},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return ResponseBadRequest(
                        {
                            "data": serializer.errors,
                            "code": status.HTTP_400_BAD_REQUEST,
                            "message": "Serializer error",
                        }
                    )

            else:
                user_objs = User.objects.filter(username=username, email_verified=False)
                if user_objs:
                    user = user_objs[0]
                    user_serializer = user_serializers.GetUserSerializer(user)

                    token = RefreshToken.for_user(user)  # token refresh through ajax
                    if not Token.objects.filter(token_type="access_token", user_id=user.id).exists():
                        Token.objects.create(
                            user_id=user.id,
                            token=str(token.access_token),
                            token_type="access_token",
                        )
                    else:
                        Token.objects.filter(user_id=user.id, token_type="access_token").update(token=str(token.access_token))
                    # shows the all details of candidate login
                    return ResponseOk(
                        {
                            "data": user_serializer.data,
                            "access_token": str(token.access_token),
                            "refresh_token": str(token),
                            "code": status.HTTP_200_OK,
                            "message": "Guest User Signed up Successfully.",
                        }
                    )

                    # TODO: removed phone number validation (handle by React)
                    # if not validate_phone_number(data.get("phone_no")):
                    #     return ResponseBadRequest(
                    #         {
                    #             "data": {"phone_no": ["Invalid Phone Number"]},
                    #             "code": status.HTTP_400_BAD_REQUEST,
                    #             "message": "Serializer error",
                    #         }
                    #     )
                else:
                    if serializer.is_valid():
                        otp = generate_otp()
                        serializer.validated_data["email_otp"] = otp
                        user_object = serializer.save()
                        user_serializer = user_serializers.GetUserSerializer(user_object)
                        data = None
                        encoded_id = "".join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(10))
                        user_object.encoded_id = encoded_id
                        user_object.save()
                        if "is_employee" in request.data and request.data["is_employee"] is True:
                            password = generate_password()
                            user_object.set_password(password)
                            user_object.save()
                            current_site = user_object.user_company.url_domain
                            link = "https://{}.{}/employee/create-profile/{}/".format(current_site, settings.DOMAIN_NAME, encoded_id)
                            send_custom_email(
                                "Registration Link",
                                link,
                                user_object.email,
                                user_object.first_name,
                                company_name=user_object.user_company.company_name,
                                password=password,
                            )
                        else:
                            data = send_email_otp(
                                request,
                                str(user_object.email),
                                str(user_object.email_otp),
                                user_object.first_name,
                                user_object.user_company.company_name,
                            )
                        # if "is_candidate" in request.data and request.data["is_candidate"] is True:
                        #     current_site = user_object.user_company.url_domain
                        #     link = "https://{}.{}/candidate/create-profile/{}/".format(current_site, settings.DOMAIN_NAME, encoded_id)
                        #     send_custom_email(
                        #         "Registration Link",
                        #         link,
                        #         user_object.email,
                        #         user_object.first_name,
                        #         company_name=user_object.user_company.company_name,
                        #     )
                        if data == 1:
                            return ResponseOk(
                                {
                                    "data": user_serializer.data,
                                    "code": status.HTTP_200_OK,
                                    "message": "User created and OTP Send successfully",
                                }
                            )
                        else:
                            return ResponseOk(
                                {
                                    "data": user_serializer.data,
                                    "code": status.HTTP_200_OK,
                                    "message": "User created but OTP not successfully",
                                }
                            )
                    else:
                        return ResponseBadRequest(
                            {
                                "data": serializer.errors,
                                "code": status.HTTP_400_BAD_REQUEST,
                                "message": "Serializer error",
                            }
                        )


class SignUpGuestView(APIView):
    permission_classes = [permissions.AllowAny]  # allow any user
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="User Sign up API",
        operation_summary="User Sign up API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                "middle_name": openapi.Schema(type=openapi.TYPE_STRING),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "phone_no": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
                "user_role": openapi.Schema(type=openapi.TYPE_INTEGER, description="enter role id"),
                "user_company": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="enter company domain (Company.url_domain) field",
                ),
            },
        ),
    )
    @csrf_exempt
    def post(self, request):
        """
        Signup Guest with any role and send verification email
        """
        data = request.data
        # serializer = user_serializers.CandidateSignUpSerializer(data=data)
        username = str(data.get("email")) + "_" + str(data.get("user_company"))
        data["username"] = username
        try:
            usr_obj = User.objects.get(username=username)

        except User.DoesNotExist:
            return ResponseBadRequest(
                {
                    "data": {"user": ["User Does Not Exists"]},
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "User Does not Exists",
                }
            )

        if usr_obj.user_role.name == "guest":
            guest_role_id = usr_obj.user_role.id
            try:
                data["user_role"] = guest_role_id
                usr_obj = User.objects.get(username=username)

                serializer = user_serializers.CandidateSignUpSerializer(usr_obj, data=data)
                if serializer.is_valid():
                    serializer.save()

                    usr_obj.set_password(request.data["password"])
                    usr_obj.save()

                    otp = generate_otp()
                    usr_obj.email_otp = otp
                    usr_obj.save()

                    if usr_obj.first_name:
                        f_name = usr_obj.first_name
                    else:
                        f_name = "Guest"

                    data = send_email_otp(request, str(usr_obj.email), otp, f_name, data.get("user_company"))

                    token = RefreshToken.for_user(usr_obj)  # token refresh through ajax
                    if not Token.objects.filter(token_type="access_token", user_id=usr_obj.id).exists():
                        Token.objects.create(
                            user_id=usr_obj.id,
                            token=str(token.access_token),
                            token_type="access_token",
                        )
                    else:
                        Token.objects.filter(user_id=usr_obj.id, token_type="access_token").update(token=str(token.access_token))
                    serializer = user_serializers.CandidateLoginDetailSerializer(usr_obj)
                    # shows the all details of candidate login
                    return ResponseOk(
                        {
                            "data": serializer.data,
                            "access_token": str(token.access_token),
                            "refresh_token": str(token),
                            "code": status.HTTP_200_OK,
                            "message": "Guest User Signed up Successfully.",
                        }
                    )
                else:
                    return ResponseBadRequest(
                        {
                            "data": serializer.errors,
                            "code": status.HTTP_400_BAD_REQUEST,
                            "message": "Some Error Occured!",
                        }
                    )

            except User.DoesNotExist:
                return ResponseBadRequest(
                    {
                        "data": None,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Guest User Does not Exist.",
                    }
                )
        else:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "User's Role is not Guest!",
                }
            )


class GetProfileByEncodedId(APIView):
    """
    This GET function fetches particular ID record from ATTRIBUTE model and return the data after serializing it.

    Args:
        None
    Body:
        - encoded_id(Mandatory)
        - otp(Mandatory)
        - user_company(Mandatory)
    Returns:
        -Email Link Verification successfully(HTTP_200_OK)
        -Invalid Email(HTTP_400_BAD_REQUEST)
        -Email Link otp required(HTTP_400_BAD_REQUEST)
        -user_company domain required(HTTP_400_BAD_REQUEST)
        -You Entered Wrong OTP(HTTP_400_BAD_REQUEST)
        -User Does Not Exist(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    def get(self, request, id=None):
        try:
            if id:
                item = User.objects.get(encoded_id=id)
                token = RefreshToken.for_user(item)  # token refresh through ajax
                if not Token.objects.filter(token_type="access_token", user_id=item.id).exists():
                    Token.objects.create(
                        user_id=item.id,
                        token=str(token.access_token),
                        token_type="access_token",
                    )
                else:
                    Token.objects.filter(user_id=item.id, token_type="access_token").update(token=str(token.access_token))
                serializer = user_serializers.UserSerializer(item)
                data = serializer.data
                data["phone_no"] = item.profile.phone_no
                try:
                    data["country_code"] = item.profile.address.country.phone_code
                except:
                    data["country_code"] = "+1"
                return Response(
                    {
                        "status": "Get Encoded ID",
                        "data": data,
                        "access_token": str(token.access_token),
                        "refresh_token": str(token),
                    },
                    status=status.HTTP_200_OK,
                )
        except:
            return Response({"status": "Please Specify the required Encoded ID", "data": None}, status=status.HTTP_200_OK)


class UpdateProfileByEncodedId(APIView):
    """
    This PUT function updates particular record by ID from ATTRIBUTE model according to the attribute_id passed in url.

    Args:
        pk(attribute_id)
    Body:
        None
    Returns:
        -Serialized ATTRIBUTE model data of particular record by ID(HTTP_200_OK)
        -serializer.errors
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    @swagger_auto_schema(
        operation_description="EncodedId Update API",
        operation_summary="EncodedId Update API",
        request_body=user_serializers.UserUpdateSerializer,
    )
    def put(self, request, id=None, format=None):
        print(request.data)
        response = Response()
        try:
            user_obj = User.objects.get(encoded_id=id)
        except User.DoesNotExist:
            return Response({"data": None, "message": "Encoded ID Does not Exist", "status": 400}, status=400)
        serializer = user_serializers.UserUpdateSerializer(instance=user_obj, data=request.data, partial=True)

        serializer.is_valid(raise_exception=True)

        serializer.save()
        if "password" in request.data:
            user_obj.set_password(request.data["password"])
            user_obj.save()

        return Response({"data": serializer.data, "message": "OK", "status": 200}, status=200)


class OtpVerificationView(APIView):
    """
    This POST function takes OTP from request body and verifies accordingly.

    Args:
        None
    Body:
        - email(Mandatory)
        - otp(Mandatory)
        - user_company(Mandatory)
    Returns:
        -OTP Verification successfully(HTTP_200_OK)
        -Invalid Email(HTTP_400_BAD_REQUEST)
        -otp required(HTTP_400_BAD_REQUEST)
        -user_company domain required(HTTP_400_BAD_REQUEST)
        -You Entered Wrong OTP(HTTP_400_BAD_REQUEST)
        -User Does Not Exist(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="OTP verification api",
        operation_summary="OTP verification api",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "otp": openapi.Schema(type=openapi.TYPE_STRING),
                "user_company": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="enter company domain (Company.url_domain) field",
                ),
            },
        ),
    )
    def post(self, request):
        data = request.data
        email = data.get("email")
        otp = data.get("otp")
        user_company = data.get("user_company")

        if not validate_email(email):
            return ResponseBadRequest({"result": "error", "fields": {"username": "Invalid Email"}})

        if not otp:
            return ResponseBadRequest("otp required")

        if not user_company:
            return ResponseBadRequest("user_company domain required")

        try:
            user_object = get_user_object(user_company, email)
            if str(user_object.email_otp) == otp:
                user_object.is_active = True
                user_object.email_verified = True
                if user_object.user_role.name == "guest":
                    try:
                        candidate_role = Role.objects.get(name="candidate")
                        user_object.user_role = candidate_role
                    except Role.DoesNotExist:
                        None

                user_object.save()
                data = email_verification_success(
                    request,
                    str(user_object.email),
                )
                if data == 1:
                    return ResponseOk(
                        {
                            "data": None,
                            "code": status.HTTP_200_OK,
                            "message": "OTP Verification successfully",
                        }
                    )
                else:
                    return ResponseOk(
                        {
                            "data": None,
                            "code": status.HTTP_400_BAD_REQUEST,
                            "message": "Something Went Wrong!",
                        }
                    )

            else:
                return ResponseBadRequest(
                    {
                        "data": None,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "You Entered Wrong OTP",
                    }
                )
        except User.DoesNotExist:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "User Does Not Exist",
                }
            )


class ResendOtpView(APIView):
    """
    This POST function resends an OTP on specific email address.

    Args:
        None
    Body:
        - email(Mandatory)
        - user_company(Mandatory)
    Returns:
        -Otp Send SuccessFully(HTTP_200_OK)
        -User Email already verified(HTTP_400_BAD_REQUEST)
        -User Does Not Exist(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="Re send OTP",
        operation_summary="Re send OTP",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "user_company": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="enter company domain (Company.url_domain) field",
                ),
            },
        ),
    )
    def post(self, request):
        data = request.data
        email = data.get("email")
        user_company = data.get("user_company")
        user_object = get_user_object(user_company, email)
        if user_object is not None:
            if user_object.email_verified:
                return ResponseBadRequest(
                    {
                        "data": None,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "User Email already verified",
                    }
                )
            else:
                otp = generate_otp()
                user_object.email_otp = otp
                user_object.save()
                data = send_email_otp(request, str(user_object.email), otp, user_object.first_name, user_object.user_company.company_name)
                if data == 1:
                    return ResponseOk(
                        {
                            "data": None,
                            "code": status.HTTP_200_OK,
                            "message": "Otp Send SuccessFully",
                        }
                    )
                else:
                    return ResponseOk(
                        {
                            "data": None,
                            "code": status.HTTP_200_OK,
                            "message": "Otp not Send",
                        }
                    )
        else:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "User Does Not Exist",
                }
            )


class RequestPasswordResetEmailView(APIView):
    """
    This POST function sends an email for password reset purpose.

    Args:
        None
    Body:
        - email(Mandatory)
        - user_company(Mandatory)
        - redirect_url(Mandatory)
    Returns:
        -We have sent you a link to reset your password(HTTP_200_OK)
        -User Does Not Exist(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Password reset email",
        operation_summary="Password reset email",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "user_company": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="enter company domain (Company.url_domain) field",
                ),
                "redirect_url": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="enter redirect url example: https://soft.infrtalent.com",
                ),
            },
        ),
    )
    def post(self, request):
        data = request.data
        email = data.get("email")
        user_company = data.get("user_company")
        redirect_url = data.get("redirect_url")

        if User.objects.filter(email=email, user_company__url_domain=user_company).exists():
            user = User.objects.get(email=email, user_company__url_domain=user_company)
            if user.user_role.name != "guest":
                uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
                token = PasswordResetTokenGenerator().make_token(user)
                current_site = get_current_site(request=request).domain
                relativeLink = reverse(
                    "user:forgot-password-confirm",
                    kwargs={"uidb64": uidb64, "token": token},
                )

                absurl = "https://" + current_site + relativeLink + "?redirect_url=" + redirect_url
                # email_body = "Hello, \n Use link below to reset your password  \n" + absurl

                # send_reset_password_mail(request, user.email, email_body)
                context = {"link": absurl, "company": user.user_company.company_name}
                from_email = settings.EMAIL_HOST_USER
                body_msg = render_to_string("reset_password.html", context)
                msg = EmailMultiAlternatives(
                    "Reset your password",
                    body_msg,
                    "Reset your password",
                    [user.email],
                )
                msg.content_subtype = "html"
                msg.send()
                return Response(
                    {"success": "We have sent you a link to reset your password"},
                    status=status.HTTP_200_OK,
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": "Please register first. You are a guest user.",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Please register first. You are a guest user.",
                    }
                )
        else:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "User Does Not Exist",
                }
            )


class PasswordTokenCheckAPIView(APIView):
    """
    PasswordTokenCheckAPIView APIView class is created with permission, JWT Authentication and
    get function with decorators to check the password
    """

    serializer_class = user_serializers.SetNewPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, uidb64, token):
        redirect_url = request.GET.get("redirect_url")

        try:
            id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                return HttpResponsePermanentRedirect(redirect_url + "?token_valid=False")

            if redirect_url and len(redirect_url) > 3:
                return HttpResponsePermanentRedirect(redirect_url + "?token_valid=True&uidb64=" + uidb64 + "&token=" + token)
            else:
                return HttpResponsePermanentRedirect(redirect_url + "?token_valid=False")

        except DjangoUnicodeDecodeError as identifier:
            try:
                if not PasswordResetTokenGenerator().check_token(user):
                    return HttpResponsePermanentRedirect(redirect_url + "?token_valid=False")

            except UnboundLocalError as e:
                return Response(
                    {"error": "Token is not valid, please request a new one"},
                    status=status.HTTP_400_BAD_REQUEST,
                )


class SetNewPasswordAPIView(APIView):
    """
    This PATCH function Sets a new Password for particular user.

    Args:
        None
    Body:
        - password(Mandatory)
        - token(Mandatory)
        - uidb64(Mandatory)
    Returns:
        -Password reset success(HTTP_200_OK)
    Authentication:
        JWT
    Raises:
        Serializer error exception
    """

    serializer_class = user_serializers.SetNewPasswordSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Set new password",
        operation_summary="Set new password",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "password": openapi.Schema(type=openapi.TYPE_STRING),
                "token": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="token",
                ),
                "uidb64": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="uidb64",
                ),
            },
        ),
    )
    @csrf_exempt
    def patch(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"success": True, "message": "Password reset success"},
            status=status.HTTP_200_OK,
        )


class SetNewPasswordWithOldAPIView(APIView):
    """
    SetNewPasswordAPIView APIView class is created with permission, JWT Authentication and
    post function with decorators to set the new password with old password
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="User reset password API",
        operation_summary="User reset password API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "current_password": openapi.Schema(type=openapi.TYPE_STRING),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        """
        User Password Reset - From the Profile Settings.
        :param request:
        :param format:
        :return:
        """
        data = request.data
        user = request.user
        current_password = data.get("current_password")
        new_password = data.get("new_password")

        if not validate_password(current_password) and not validate_password(new_password):
            return ResponseBadRequest(
                (
                    {
                        "result": "error",
                        "fields": {
                            "current": "Invalid Current Password",
                            "newPassword": "Invalid New Password",
                        },
                    }
                )
            )
        if not validate_password(current_password):
            return ResponseBadRequest(
                (
                    {
                        "result": "error",
                        "fields": {"current": "Invalid Current Password"},
                    }
                )
            )
        if not validate_password(new_password):
            return ResponseBadRequest(
                (
                    {
                        "result": "error",
                        "fields": {"newPassword": "Invalid New Password"},
                    }
                )
            )
        if current_password == new_password or new_password_matches_old_password(new_password, user.password):
            return ResponseBadRequest(
                (
                    {
                        "result": "error",
                        "fields": {"newPassword": "New Password matches the old one"},
                    }
                )
            )
        if not new_password_matches_old_password(current_password, user.password):
            return ResponseBadRequest(
                (
                    {
                        "result": "error",
                        "fields": {
                            "current": "Incorrect Credentials",
                        },
                    }
                )
            )
        try:
            user.set_password(new_password)
            user.save()
            return ResponseOk()
        except Exception as e:
            return ResponseInternalServerError(str(e))


# @permission_classes([permissions.AllowAny])
class GetProfile(APIView):
    """
    This GET function fetches Profile Model instance by ID and return data after serializing it.

    Args:
        PK(profile_id)
    Body:
        None
    Returns:
        -Serialized Profile Model data(HTTP_200_OK)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Profile Get API",
        operation_summary="Profile Get API",
    )
    def get(self, request, pk):
        try:
            try:
                pk = decrypt(pk)
            except:
                pass
            profile = custom_get_object(pk, Profile)
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Profile Does not Exist!",
                }
            )
        serializer = user_serializers.GetProfileSerializer(profile)
        data = serializer.data
        try:
            if profile.address.country:
                if profile.address.country.phone_code.startswith("+"):
                    data["countrycode"] = profile.address.country.phone_code
                else:
                    data["countrycode"] = "+" + profile.address.country.phone_code
        except Exception as e:
            data["e"] = str(e)
        return Response(data)


# TODO: Code cleanup Pending
@permission_classes([permissions.IsAuthenticated])
class UpdateProfile(APIView):
    """
    This PUT function updates particular record by ID from Profile model according to the profile_id passed in url.

    Args:
        pk(profile_id)
    Body:
        - Profile Model Fields(to be updated)
    Returns:
        -Serialized Profile model data of particular record by ID(HTTP_201_CREATED)
        -serializer.errors(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Profile Update API",
        operation_summary="Profile Update API",
        request_body=user_serializers.UpdateProfileProfileSerializer,
    )
    def put(self, request, pk, format=None):
        try:
            pk = decrypt(pk)
        except:
            pass
        profile = custom_get_object(pk, Profile)
        # Checking for Duplicate Employee ID  --Start

        if "employee_id" in request.data:
            user_obj = User.objects.get(id=request.data["user"])
            request.data.pop("user")

            existing_employee_id_count = (
                Profile.objects.filter(employee_id=request.data["employee_id"], user__user_company__id=user_obj.user_company.id)
                .exclude(user=user_obj.id)
                .count()
            )
            if existing_employee_id_count > 0:
                return ResponseBadRequest(
                    {
                        "data": None,
                        "code": status.HTTP_200_OK,
                        "message": "Profile with this Employee Code Already Exists!",
                    }
                )
        if "first_name" in request.data:
            profile.user.first_name = request.data["first_name"]
        if "last_name" in request.data:
            profile.user.first_name = request.data["last_name"]
        if "middle_name" in request.data:
            profile.user.first_name = request.data["middle_name"]
        if "user_role" in request.data:
            profile.user.first_name = request.data["user_role"]
        msg = "None"
        old_ref_by = profile.user_refereed_by
        new_ref_by = request.data.get("refereed_by_profile")
        if new_ref_by:
            try:
                first_name = new_ref_by.get("name").split()[0]
                if len(new_ref_by.get("name").split()) > 1:
                    last_name = new_ref_by.get("name").split()[-1]
                else:
                    last_name = ""
                refereed_by_obj = User.objects.get(first_name=first_name, last_name=last_name, user_company=profile.user.user_company)
                profile.user_refereed_by = new_ref_by
                profile.save()
                # Check if referral notification is true
                if NotificationType.objects.filter(slug="employee-referral-notification", is_active=True):
                    send_instant_notification(
                        message="Hi {}, you just got a new referral.".format(refereed_by_obj.user.get_full_name()),
                        user=refereed_by_obj.user,
                    )
            except Exception as e:
                msg = str(e)
        ser_data = request.data.copy()
        source = ser_data.pop("source", None)
        skill = ser_data.pop("skill", None)
        serializer = user_serializers.UpdateProfileProfileSerializer(profile, data=ser_data, partial=True)
        # Update first and last name as it is not getting updated with the serializer
        profile.user.first_name = request.data.get("first_name", profile.user.first_name)
        profile.user.last_name = request.data.get("last_name", profile.user.last_name)
        # if profile.user.user_role.name == "candidate":
        #     profile.was_candidate = True
        profile.user.save()
        profile.save()

        if serializer.is_valid():
            serializer.save()
            if "manager" in request.data:
                try:
                    manager_id = request.data.get("manager")
                    manager_profile = Profile.objects.get(id=int(manager_id))
                    team_obj, created = Team.objects.get_or_create(manager=manager_profile)
                    profile.members.clear()
                    team_obj.members.add(profile)
                    team_obj.save()
                    manager = {"id": manager_profile.id, "name": manager_profile.user.first_name}
                except Exception as e:
                    print(e)
                    manager = None
            else:
                manager = None
            data = serializer.data
            data["manager"] = manager
            if profile.department:
                data["department"] = {"id": profile.department.id, "name": profile.department.department_name}
            # Update user role if new
            message = "Profile updated successfully"
            try:
                if "user_role" in request.data:
                    user_role = int(request.data.get("user_role"))
                    if user_role is not profile.user.user_role.id:
                        role = Role.objects.get(id=user_role)
                        profile.user.user_role = role
                        profile.user.save()
            except Exception as e:
                message = "Profile updated successfully but {}".format(str(e))
            # Save other data
            if source and len(source) > 0:
                try:
                    profile.source = source[0]["label"]
                except:
                    profile.source = source
            if skill and len(skill) > 0:
                profile.skill.set(skill)
            profile.save()

            return ResponseOk({"data": data, "code": status.HTTP_200_OK, "message": message, "msg": msg})
        else:
            return ResponseBadRequest(
                {"data": serializer.errors, "code": status.HTTP_400_BAD_REQUEST, "message": "Profile Does Not Exist123", "msg": msg}
            )


class GetAllUser(APIView):
    """
    This GET function fetches all records from User model with pagination, searching and sorting, and return the data after serializing it.

    Args:
        None
    Body:
        -domain(mandatory)
        -employee_id(optional)
        -role_id(optional)
        -search(optional)
        -page(optional)
        -perpage(optional)
        -sort_dir(optional)
        -sort_field(optional)
    Returns:
        -Fetches all serialized data(HTTP_200_OK)
        -Search query has no match(HTTP_400_BAD_REQUEST)
        -Exception text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )
    employee_id = openapi.Parameter(
        "employee_id",
        in_=openapi.IN_QUERY,
        description="employee_id",
        type=openapi.TYPE_STRING,
    )
    page = openapi.Parameter(
        "page",
        in_=openapi.IN_QUERY,
        description="page",
        type=openapi.TYPE_STRING,
    )
    permission = openapi.Parameter(
        "permission",
        in_=openapi.IN_QUERY,
        description="permission",
        type=openapi.TYPE_STRING,
    )
    perpage = openapi.Parameter(
        "perpage",
        in_=openapi.IN_QUERY,
        description="perpage",
        type=openapi.TYPE_STRING,
    )
    sort_dir = openapi.Parameter(
        "sort_dir",
        in_=openapi.IN_QUERY,
        description="asc or desc",
        type=openapi.TYPE_STRING,
    )
    sort_field = openapi.Parameter(
        "sort_field",
        in_=openapi.IN_QUERY,
        description="sort_field",
        type=openapi.TYPE_STRING,
    )
    role_id = openapi.Parameter(
        "role_id",
        in_=openapi.IN_QUERY,
        description="role_id",
        type=openapi.TYPE_STRING,
    )
    exclude_role_list = openapi.Parameter(
        "exclude_role_list",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        description="enter role id's to be excluded, example: [1,2]",
    )
    is_hiring_manager = openapi.Parameter(
        "is_hiring_manager",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_STRING,
        description="Pass true if only hiring managers needs to be listed",
    )
    is_recruiter = openapi.Parameter(
        "is_recruiter",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_STRING,
        description="Pass true if only recuiters needs to be listed",
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            employee_id,
            page,
            permission,
            perpage,
            sort_dir,
            sort_field,
            role_id,
            exclude_role_list,
            is_hiring_manager,
            is_recruiter,
        ]
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET

            if request.headers.get("domain"):
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")

            role_id = data.get("role_id", "")

            query = data.get("search", "")

            employee_id = data.get("employee_id", "")

            match_employee_id = data.get("match_employee_id", "")

            page = data.get("page", 1)

            if data.get("is_active"):
                is_active = data.get("is_active")
                if is_active == "true":
                    active = True
                else:
                    active = False
            else:
                active = None

            limit = data.get("perpage", settings.PAGE_SIZE)
            if data.get("exclude_role_list"):
                ex_role_list = data.get("exclude_role_list")
                if isinstance(ex_role_list, str):
                    exclude_role_list = data.get("exclude_role_list").split(",")
                else:
                    exclude_role_list = ex_role_list
            else:
                exclude_role_list = None
            if data.get("is_hiring_manager"):
                is_hiring_manager = True
            else:
                is_hiring_manager = None

            if data.get("is_recruiter"):
                is_recruiter = True
            else:
                is_recruiter = None
            permission = data.get("permission")
            pages, skip = 1, 0

            sort_field = data.get("sort_field")

            sort_dir = data.get("sort_dir")

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            user = User.objects.all().filter(user_company__url_domain=url_domain).exclude(user_role__slug__in=["candidate", "superuser"])
            if role_id:
                user = user.filter(user_role=role_id)

            if employee_id:
                user = user.filter(profile__employee_id__icontains=employee_id)
            if match_employee_id:
                user = user.filter(profile__employee_id__iexact=match_employee_id)

            if exclude_role_list:
                user = user.exclude(user_role__in=exclude_role_list)
            if active:
                user = user.filter(is_active=active)
            if is_hiring_manager:
                user = user.filter(user_role__name="hiring manager")
            if is_recruiter:
                user = user.filter(user_role__name="recruiter")
            if query:
                user = user.annotate(full_name=Concat("first_name", V(" "), "last_name")).filter(
                    Q(full_name__icontains=query) | Q(email__icontains=query)
                )
            try:
                # to be removed
                if permission is not None:
                    role_list = RolePermission.objects.filter(access__action_name=permission).values_list("role")

                    user = user.filter(user_role__id__in=role_list)
                    if permission in ["Offer approver", "Position Approver"]:
                        user = user.exclude(user_role__name="employee")
            except Exception as e:
                print(e)

            count = user.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "name":
                        user = user.order_by("name")
                    elif sort_field == "capital":
                        user = user.order_by("capital")
                    elif sort_field == "id":
                        user = user.order_by("id")

                    else:
                        user = user.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "name":
                        user = user.order_by("-name")
                    elif sort_field == "capital":
                        user = user.order_by("-capital")
                    elif sort_field == "id":
                        user = user.order_by("-id")

                    else:
                        user = user.order_by("-id")
            else:
                user = user.order_by("-id")

            if page and limit:
                user = user[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if user:
                user = user.select_related("profile", "user_role", "profile__address", "profile__department")
                user = user.prefetch_related("profile__skill", "profile__education", "profile__media")
                serializer = user_serializers.GetUserSerializer(user, many=True)

                return ResponseOk(
                    {
                        "data": serializer.data,
                        "meta": {
                            "page": page,
                            "total_pages": pages,
                            "perpage": limit,
                            "sort_dir": sort_dir,
                            "sort_field": sort_field,
                            "total_records": count,
                        },
                    }
                )
            return ResponseBadRequest("Search query has no match")

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpUser(APIView):
    """
    This GET function fetches all records from User model with pagination, searching and sorting, and return the data after serializing it.

    Args:
        None
    Body:
        -domain(mandatory)
        -employee_id(optional)
        -role_id(optional)
        -search(optional)
        -page(optional)
        -perpage(optional)
        -sort_dir(optional)
        -sort_field(optional)
    Returns:
        -Fetches all serialized data(HTTP_200_OK)
        -Search query has no match(HTTP_400_BAD_REQUEST)
        -Exception text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )
    employee_id = openapi.Parameter(
        "employee_id",
        in_=openapi.IN_QUERY,
        description="employee_id",
        type=openapi.TYPE_STRING,
    )

    page = openapi.Parameter(
        "page",
        in_=openapi.IN_QUERY,
        description="page",
        type=openapi.TYPE_STRING,
    )
    perpage = openapi.Parameter(
        "perpage",
        in_=openapi.IN_QUERY,
        description="perpage",
        type=openapi.TYPE_STRING,
    )
    sort_dir = openapi.Parameter(
        "sort_dir",
        in_=openapi.IN_QUERY,
        description="asc or desc",
        type=openapi.TYPE_STRING,
    )
    sort_field = openapi.Parameter(
        "sort_field",
        in_=openapi.IN_QUERY,
        description="sort_field",
        type=openapi.TYPE_STRING,
    )
    exclude_role_list = openapi.Parameter(
        "exclude_role_list",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        description="enter role id's to be excluded, example: [1,2]",
    )
    role_id = openapi.Parameter(
        "role_id",
        in_=openapi.IN_QUERY,
        description="role_id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[search, employee_id, page, perpage, sort_dir, sort_field, exclude_role_list, role_id])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET
            if request.headers.get("domain"):
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")

            query = data.get("search", "")

            page = data.get("page", 1)

            role_id = data.get("role_id", "")

            if data.get("is_active"):
                is_active = data.get("is_active")
                if is_active == "true":
                    active = True
                else:
                    active = False
            else:
                active = None
            limit = data.get("perpage", settings.PAGE_SIZE)
            if data.get("exclude_role_list"):
                ex_role_list = data.get("exclude_role_list")
                if isinstance(ex_role_list, str):
                    exclude_role_list = data.get("exclude_role_list").split(",")
                else:
                    exclude_role_list = ex_role_list
            else:
                exclude_role_list = None
            pages, skip = 1, 0

            sort_field = data.get("sort_field")

            sort_dir = data.get("sort_dir")
            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit
            user = User.objects.filter(user_company__url_domain=url_domain).exclude(user_role__slug__in=["candidate", "superuser"])
            if FeaturesEnabled.objects.filter(feature="recruiter", enabled=False, company__url_domain=request.headers.get("domain")):
                user = user.exclude(user_role__slug="recruiter")
            if role_id:
                user = user.filter(user_role=role_id)
            if active:
                user = user.filter(is_active=active)
            if exclude_role_list:
                user = user.exclude(user_role__in=exclude_role_list)
            if query:
                user = user.annotate(full_name=Concat("first_name", V(" "), "last_name")).filter(
                    Q(full_name__icontains=query) | Q(email__icontains=query) | Q(profile__employee_id__icontains=query)
                )
            count = user.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "name":
                        user = user.order_by("name")
                    elif sort_field == "capital":
                        user = user.order_by("capital")
                    elif sort_field == "id":
                        user = user.order_by("id")

                    else:
                        user = user.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "name":
                        user = user.order_by("-name")
                    elif sort_field == "capital":
                        user = user.order_by("-capital")
                    elif sort_field == "id":
                        user = user.order_by("-id")

                    else:
                        user = user.order_by("-id")
            else:
                user = user.order_by("-id")

            if page and limit:
                user = user[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1
            if user:
                data = []
                for i in user:
                    try:
                        temp_data = {}
                        temp_data["profile_id"] = i.profile.id
                        temp_data["user_id"] = i.id
                        temp_data["linkedin_url"] = i.profile.linked_url
                        temp_data["employee_name"] = i.get_full_name()
                        temp_data["employee_id"] = i.profile.employee_id
                        try:
                            temp_data["user_role"] = i.user_role.name
                        except:
                            temp_data["user_role"] = None
                        try:
                            temp_data["country"] = i.profile.address.country.name
                        except:
                            temp_data["country"] = None
                        if i.profile.department:
                            temp_data["department"] = i.profile.department.department_name
                        else:
                            temp_data["department"] = None
                        temp_data["phone_number"] = i.profile.phone_no
                        temp_data["manager"] = get_manager(i.profile)
                        temp_data["email"] = i.email
                        temp_data["is_active"] = i.is_active
                        temp_data["first_name"] = i.first_name
                        data.append(temp_data)
                    except:
                        pass
                return ResponseOk(
                    {
                        "data": data,
                        "meta": {
                            "page": page,
                            "total_pages": pages,
                            "perpage": limit,
                            "sort_dir": sort_dir,
                            "sort_field": sort_field,
                            "total_records": count,
                        },
                    }
                )
            return ResponseBadRequest("Search query has no match")

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class OpGetAllUser(APIView):
    """
    This GET function fetches all records from User model with pagination, searching and sorting, and return the data after serializing it.

    Args:
        None
    Body:
        -domain(mandatory)
        -employee_id(optional)
        -role_id(optional)
        -search(optional)
        -page(optional)
        -perpage(optional)
        -sort_dir(optional)
        -sort_field(optional)
    Returns:
        -Fetches all serialized data(HTTP_200_OK)
        -Search query has no match(HTTP_400_BAD_REQUEST)
        -Exception text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )
    employee_id = openapi.Parameter(
        "employee_id",
        in_=openapi.IN_QUERY,
        description="employee_id",
        type=openapi.TYPE_STRING,
    )

    page = openapi.Parameter(
        "page",
        in_=openapi.IN_QUERY,
        description="page",
        type=openapi.TYPE_STRING,
    )
    permission = openapi.Parameter(
        "permission",
        in_=openapi.IN_QUERY,
        description="permission",
        type=openapi.TYPE_STRING,
    )
    perpage = openapi.Parameter(
        "perpage",
        in_=openapi.IN_QUERY,
        description="perpage",
        type=openapi.TYPE_STRING,
    )
    sort_dir = openapi.Parameter(
        "sort_dir",
        in_=openapi.IN_QUERY,
        description="asc or desc",
        type=openapi.TYPE_STRING,
    )
    sort_field = openapi.Parameter(
        "sort_field",
        in_=openapi.IN_QUERY,
        description="sort_field",
        type=openapi.TYPE_STRING,
    )
    role_id = openapi.Parameter(
        "role_id",
        in_=openapi.IN_QUERY,
        description="role_id",
        type=openapi.TYPE_STRING,
    )
    exclude_role_list = openapi.Parameter(
        "exclude_role_list",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        description="enter role id's to be excluded, example: [1,2]",
    )
    is_hiring_manager = openapi.Parameter(
        "is_hiring_manager",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_STRING,
        description="Pass true if only hiring managers needs to be listed",
    )
    is_recruiter = openapi.Parameter(
        "is_recruiter",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_STRING,
        description="Pass true if only recuiters needs to be listed",
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            employee_id,
            page,
            permission,
            perpage,
            sort_dir,
            sort_field,
            role_id,
            exclude_role_list,
            is_hiring_manager,
            is_recruiter,
        ]
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET

            url_domain = request.headers.get("domain")

            role_id = data.get("role_id", "")

            query = data.get("search", "")

            employee_id = data.get("employee_id", "")

            match_employee_id = data.get("match_employee_id", "")

            page = data.get("page", 1)

            if data.get("is_active"):
                is_active = data.get("is_active")
                if is_active == "true":
                    active = True
                else:
                    active = False
            else:
                active = None

            limit = data.get("perpage", settings.PAGE_SIZE)
            if data.get("exclude_role_list"):
                ex_role_list = data.get("exclude_role_list")
                if isinstance(ex_role_list, str):
                    exclude_role_list = data.get("exclude_role_list").split(",")
                else:
                    exclude_role_list = ex_role_list
            else:
                exclude_role_list = None
            if data.get("is_hiring_manager"):
                is_hiring_manager = True
            else:
                is_hiring_manager = None

            if data.get("is_recruiter"):
                is_recruiter = True
            else:
                is_recruiter = None
            permission = data.get("permission")
            pages, skip = 1, 0

            sort_field = data.get("sort_field")

            sort_dir = data.get("sort_dir")

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            user = User.objects.all().filter(user_company__url_domain=url_domain).exclude(user_role__slug__in=["candidate", "superuser"])
            if role_id:
                user = user.filter(user_role=role_id)

            if employee_id:
                user = user.filter(profile__employee_id__icontains=employee_id)
            if match_employee_id:
                user = user.filter(profile__employee_id__iexact=match_employee_id)

            if exclude_role_list:
                user = user.exclude(user_role__in=exclude_role_list)
            if active:
                user = user.filter(is_active=active)
            if is_hiring_manager:
                user = user.filter(user_role__name="hiring manager")
            if is_recruiter:
                user = user.filter(user_role__name="recruiter")
            if query:
                user = user.annotate(full_name=Concat("first_name", V(" "), "last_name")).filter(
                    Q(full_name__icontains=query) | Q(email__icontains=query)
                )
            try:
                # to be removed
                if permission is not None:
                    role_list = RolePermission.objects.filter(access__action_name=permission).values_list("role")

                    user = user.filter(user_role__id__in=role_list, is_active=True)
                    if permission in ["Offer approver", "Position Approver"]:
                        user = user.exclude(user_role__name="employee")
            except Exception as e:
                print(e)

            count = user.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "name":
                        user = user.order_by("name")
                    elif sort_field == "capital":
                        user = user.order_by("capital")
                    elif sort_field == "id":
                        user = user.order_by("id")

                    else:
                        user = user.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "name":
                        user = user.order_by("-name")
                    elif sort_field == "capital":
                        user = user.order_by("-capital")
                    elif sort_field == "id":
                        user = user.order_by("-id")

                    else:
                        user = user.order_by("-id")
            else:
                user = user.order_by("-id")

            if page and limit:
                user = user[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if user:
                # user = user.select_related("profile", "user_role", "profile__address", "profile__department")
                # user = user.prefetch_related("profile__skill", "profile__education", "profile__media")
                serializer = user_serializers.OpGetUserSerializer(user, many=True)

                return ResponseOk(
                    {
                        "data": serializer.data,
                        "meta": {
                            "page": page,
                            "total_pages": pages,
                            "perpage": limit,
                            "sort_dir": sort_dir,
                            "sort_field": sort_field,
                            "total_records": count,
                        },
                    }
                )
            return ResponseBadRequest("Search query has no match")

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetHMAndRecruiter(APIView):
    """
    This GET function fetches all HMs and Recruiters from User model with pagination return the data after serializing it.

    Body:
        None
    Args:
        -domain(mandatory)
        -is_hiring_manager(optional)
        -is_recruiter(optional)
    Returns:
        -Fetches all serialized data(HTTP_200_OK)
        -Search query has no match(HTTP_400_BAD_REQUEST)
        -Exception text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    page = openapi.Parameter(
        "page",
        in_=openapi.IN_QUERY,
        description="page",
        type=openapi.TYPE_STRING,
    )
    perpage = openapi.Parameter(
        "perpage",
        in_=openapi.IN_QUERY,
        description="perpage",
        type=openapi.TYPE_STRING,
    )
    is_hiring_manager = openapi.Parameter(
        "is_hiring_manager",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_STRING,
        description="Pass true if only hiring managers needs to be listed",
    )
    is_recruiter = openapi.Parameter(
        "is_recruiter",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_STRING,
        description="Pass true if only recuiters needs to be listed",
    )

    @swagger_auto_schema(
        manual_parameters=[
            page,
            perpage,
            is_hiring_manager,
            is_recruiter,
        ]
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET

            if request.headers.get("domain"):
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if data.get("page"):
                page = data.get("page")
            else:
                page = 1

            if data.get("perpage"):
                limit = data.get("perpage")
            else:
                limit = str(settings.PAGE_SIZE)
            if data.get("is_hiring_manager"):
                is_hiring_manager = True
            else:
                is_hiring_manager = None

            if data.get("is_recruiter"):
                is_recruiter = True
            else:
                is_recruiter = None
            pages, skip = 1, 0

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            user = User.objects.all().filter(user_company__url_domain=url_domain).exclude(user_role__slug__in=["candidate", "superuser"])
            if is_hiring_manager:
                user = user.filter(user_role__name="hiring manager")
            if is_recruiter:
                user = user.filter(user_role__name="recruiter")
            count = user.count()

            if page and limit:
                user = user[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if user:
                serializer = user_serializers.GetHMAndRecruiterSerializer(user, many=True)

                return ResponseOk(
                    {
                        "data": serializer.data,
                        "meta": {
                            "page": page,
                            "total_pages": pages,
                            "perpage": limit,
                            "total_records": count,
                        },
                    }
                )
            return ResponseBadRequest("Search query has no match")

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


@permission_classes([permissions.IsAuthenticated])
class UpdateUser(APIView):
    """
    This PUT function updates particular record by ID from User model according to the user_id passed in url.

    Args:
        pk(user_id)
    Body:
        None
    Returns:
        -Serialized User model data of particular record by ID(HTTP_200_OK)
        -serializer.errors
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        Http404
    """

    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="User Update API", operation_summary="User Update API", request_body=user_serializers.UserUpdateSerializer
    )
    def put(self, request, pk, format=None):
        user = custom_get_object(pk, User)
        serializer = user_serializers.UserUpdateSerializer(user, data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if request.data.get("password"):
                user.set_password(request.data.get("password"))
                print(user.is_active)
                user.save()
                print(user.is_active)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteUser(APIView):
    """
    This DETETE function delete particular record by ID from User model according to the user_id passed in url.

    Args:
        pk(user_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if user_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            user = custom_get_object(pk, User)
            try:
                user.profile.address.delete()
            except Exception as e:
                pass
            user.delete()

            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "User deleted Successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "User Does Not Exist",
                }
            )


class MediaList(APIView):
    """
    This GET function fetches all records from Media model with pagination, searching and sorting, and return the data after serializing it.

    Args:
        None
    Body:
        -search(optional)
        -profile_id(optional)
        -field_name(optional)
        -page(optional)
        -perpage(optional)
        -sort_dir(optional)
        -sort_field(optional)
    Returns:
        -Fetches all serialized data(HTTP_200_OK)
        -Search query has no match(HTTP_400_BAD_REQUEST)
        -Media does not exist(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )
    profile_id = openapi.Parameter(
        "profile_id",
        in_=openapi.IN_QUERY,
        description="profile_id",
        type=openapi.TYPE_STRING,
    )
    field_name = openapi.Parameter(
        "field_name",
        in_=openapi.IN_QUERY,
        description="field_name",
        type=openapi.TYPE_STRING,
    )
    page = openapi.Parameter(
        "page",
        in_=openapi.IN_QUERY,
        description="page",
        type=openapi.TYPE_STRING,
    )
    perpage = openapi.Parameter(
        "perpage",
        in_=openapi.IN_QUERY,
        description="perpage",
        type=openapi.TYPE_STRING,
    )
    sort_dir = openapi.Parameter(
        "sort_dir",
        in_=openapi.IN_QUERY,
        description="asc or desc",
        type=openapi.TYPE_STRING,
    )
    sort_field = openapi.Parameter(
        "sort_field",
        in_=openapi.IN_QUERY,
        description="sort_field",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            profile_id,
            field_name,
            page,
            perpage,
            sort_dir,
            sort_field,
        ]
    )
    def get(self, request):
        try:
            data = request.GET

            if data.get("search"):
                query = data.get("search")
            else:
                query = ""
            if data.get("field_name"):
                field_name = data.get("field_name")
            else:
                field_name = ""
            if data.get("profile_id"):
                profile_id = data.get("profile_id")
            else:
                profile_id = ""
            try:
                profile_id = decrypt(profile_id)
            except:
                pass
            if data.get("page"):
                page = data.get("page")
            else:
                page = 1

            if data.get("perpage"):
                limit = data.get("perpage")
            else:
                limit = str(settings.PAGE_SIZE)

            pages, skip = 1, 0

            sort_field = data.get("sort_field")

            sort_dir = data.get("sort_dir")

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            media = Media.objects.all()

            if query:
                media = media.filter(Q(media_file_name__icontains=query))

            if profile_id:
                media = media.filter(Q(profile=profile_id))

            if field_name:
                media = media.filter(Q(field_name=field_name))

            count = media.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "is_active":
                        media = media.order_by("is_active")
                    elif sort_field == "id":
                        media = media.order_by("id")
                    else:
                        media = media.order_by("id")

                elif sort_dir == "desc":
                    if sort_field == "is_active":
                        media = media.order_by("-is_active")
                    elif sort_field == "id":
                        media = media.order_by("-id")

                    else:
                        media = media.order_by("-id")
            else:
                media = media.order_by("-id")

            if page and limit:
                media = media[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

                serializer = user_serializers.MediaSerializer(media, many=True).data

                return ResponseOk(
                    {
                        "data": serializer,
                        "meta": {
                            "page": page,
                            "total_pages": pages,
                            "perpage": limit,
                            "sort_dir": sort_dir,
                            "sort_field": sort_field,
                            "total_records": count,
                        },
                    }
                )
            else:
                return ResponseBadRequest("Search query has no match")

        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Media does not exist",
                }
            )


class GetMedia(APIView):
    """
    This GET function fetches Media Model instance by ID and return data after serializing it.

    Args:
        PK(media_id)
    Body:
        None
    Returns:
        -Serialized Media Model data(HTTP_200_OK)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            media = custom_get_object(pk, Media)
            serializer = user_serializers.MediaSerializer(media)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get media successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "media Does Not Exist",
                }
            )


class GetMediaByProfile(APIView):
    """
    This GET function fetches Media Model instance by ID and return data after serializing it.

    Args:
        PK(media_id)
    Body:
        None
    Returns:
        -Serialized Media Model data(HTTP_200_OK)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            media_obj = Media.objects.filter(profile=pk)
            serializer = user_serializers.MediaSerializer(media_obj, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get media successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "media Does Not Exist",
                }
            )


class UpdateMedia(APIView):
    """
    This PUT function updates particular record by ID from Media model according to the media_id passed in url.

    Args:
        pk(media_id)
    Body:
        - Media Model Fields(to be updated)
    Returns:
        -Serialized Media model data of particular record by ID(HTTP_201_CREATED)
        -serializer.errors(HTTP_400_BAD_REQUEST)
        -Media Does Not Exist(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="Upload file...",
        request_body=user_serializers.MediaSerializer,
    )
    def put(self, request, pk):
        try:
            data = request.data
            data["profile"] = request.user.profile.id

            media = custom_get_object(pk, Media)
            serializer = user_serializers.MediaSerializer(media, data=data)

            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Media updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Media Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Media Does Not Exist",
                }
            )


class DeleteMedia(APIView):
    """
    This DETETE function delete particular record by ID from Media model according to the media_id passed in url.

    Args:
        pk(media_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST) if media_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            media = custom_get_object(pk, Media)
            media.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Media deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Media Does Not Exist",
                }
            )


class CreateMedia(APIView):
    """
    This POST function creates a Media model records from the data passes in the body.

    Args:
    None
    Body:
        Media model fields
    Returns:
        -serializer.data(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="Upload file...",
        request_body=user_serializers.MediaSerializer,
    )
    def post(self, request):
        data = request.data
        data["profile"] = request.user.profile.id
        try:
            media = request.data["media_file"]
            file_name = media.name
            splied_name = media.name.split(".")
            try:
                new_name = ".".join(x for x in splied_name[:-1])
                new_name = "{}{}.{}".format(new_name, str(time.time()).replace(".", ""), splied_name[-1])
            except Exception as e:
                print(e)
                new_name = file_name
            media.name = new_name
            request.data["media_file"] = media
            request.data["media_file_name"] = new_name
        except Exception as e:
            print(e, "------------")

        serializer = user_serializers.MediaSerializer(
            data=data,
        )
        if serializer.is_valid():
            obj = serializer.save()
            # create the media text to be used in boolean search
            if obj.media_file_name.endswith(("docx", "doc")):
                # get the content from doc file
                content = read_doc(obj.media_file)
            elif obj.media_file_name.endswith("pdf"):
                # get the doc from pdf file
                content = read_pdf(obj.media_file)
            else:
                content = ""
            MediaText.objects.create(media=obj, text=content, profile=obj.profile)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Media created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "serializer errors",
                }
            )


class UserCSVExport(APIView):
    """
    This GET function fetches all the data from USER model and converts it into CSV file.

    Args:
        pk(company_id)
    Body:
        None
    Returns:
        -HttpResponse
    Authentication:
        None
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = []

    def get(self, request, company_id):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="export.csv"'

        all_fields = User.objects.filter(user_company=company_id)
        serializer = user_serializers.CsvUserSerializer(all_fields, many=True)

        header = user_serializers.CsvUserSerializer.Meta.fields

        writer = csv.DictWriter(response, fieldnames=header)

        writer.writeheader()
        for row in serializer.data:
            writer.writerow(row)

        # TODO: export csv with panda dataframe
        # Data_set based on panda
        # import pandas as pd
        # # all_fields is django queryset object
        # pd_data = pd.DataFrame(all_fields.values("username", "email", "is_staff", "last_login", "is_superuser"))
        # writer = CSVWriter(pd_data)
        # response = writer.convert_to_csv(filename=generate_file_name("Users", "csv"))
        # return response

        return response


class EmployeeCSVExport(APIView):
    """
    This GET function fetches all the data from USER(Employee) model and converts it into CSV file.

    Args:
        pk(company_id)
    Body:
        None
    Returns:
        -HttpResponse
    Authentication:
        None
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, company):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        queryset = User.objects.filter(user_company__url_domain=company).exclude(user_role__name__in=["candidate", "guest"])

        queryset_df = pd.DataFrame(
            queryset.values(
                "id",
                "first_name",
                "last_name",
                "email",
                # profile
                "profile__phone_no",
                "profile__address__country__name",
                "profile__address__state__name",
                "profile__address__city__name",
                "profile__address__pin_code",
                "profile__experience_type",
                "profile__cover_letter",
                # TODO: profile__skill | many to many
                # "profile__skill__skill",
                # TODO: education | one to many
                # "profile__education__university__name",
                # "profile__education__education_type__name",
                # "profile__education__passing_out_year",
                # "profile__education__country__name",
                # TODO experience | one to many
                # "profile__experience__company_name",
                # "profile__experience__title",
                # "profile__experience__is_current_company",
                # "profile__experience__join_date",
                # "profile__experience__leave_date",
            )
        )

        # skill many to many data frame
        skill_df = pd.DataFrame(
            queryset.values(
                "id",
                "profile__skill__skill",
            )
        )

        # skill may to many data group by row
        skill_df = (
            skill_df.groupby(
                by=[
                    "id",
                ]
            )["profile__skill__skill"]
            .apply(lambda x: ", ".join(x.astype(str)))
            .reset_index()
        )

        # merge skill_df with queryset_df
        csv_df = queryset_df.merge(skill_df, how="inner")

        # rename colum in dataframe
        csv_df.rename(
            columns={
                "first_name": "FirstName",
                "last_name": "LastName",
                "email": "Email",
                # profile
                "profile__phone_no": "PhoneNo",
                "profile__address__country__name": "Country",
                "profile__address__state__name": "State",
                "profile__address__city__name": "City",
                "profile__address__pin_code": "PinCode",
                "profile__experience_type": "ExperienceType",
                "profile__cover_letter": "CoverLetter",
                "profile__skill__skill": "Skill",
                # education
                # "profile__education__university__name": "UniversityName",
                # "profile__education__education_type__name": "EducationType",
                # "profile__education__passing_out_year": "PassingOutYear",
                # "profile__education__country__name": "CountryName",
                # experience
                # "profile__experience__company_name": "CompanyName",
                # "profile__experience__title": "Title",
                # "profile__experience__is_current_company": "IsCurrentCompany",
                # "profile__experience__join_date": "JoinDate",
                # "profile__experience__leave_date": "LeaveDate",
            },
            inplace=True,
        )

        # Education data of User
        data_list = []
        for z in queryset.all():
            temp_dict = {}
            temp_dict["id"] = z.id
            education_count = 1
            try:
                for q in z.profile.education.all():
                    temp_dict[f"education_type_{education_count}"] = q.education_type.name
                    temp_dict[f"university_{education_count}"] = q.university.name
                    temp_dict[f"passing_out_year_{education_count}"] = q.passing_out_year
                    temp_dict[f"country_{education_count}"] = q.country.name
                    education_count = education_count + 1
            except Exception as e:
                print(e)
            education_count = 1
            data_list.append(temp_dict)
        education_df = pd.DataFrame(data_list)

        # merge csv_df with education_df
        csv_df = csv_df.merge(education_df, how="inner")

        writer = CSVWriter(csv_df)
        response = writer.convert_to_csv(filename=generate_file_name("Employee", "csv"))
        return response


class UserActivityView(APIView):
    def get(self, request, format=None):
        user_obj = ActivityLogs.objects.filter(user=request.user.id).order_by("-created_at")[:5]
        serializer = user_serializers.ActivityLogsSerializer(user_obj, many=True)
        return ResponseOk(
            {
                "data": serializer.data,
                "code": status.HTTP_200_OK,
                "message": "Activities Fetched Successfully.",
            }
        )


class CandidateSourceCount(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    position_id = openapi.Parameter(
        "position_id",
        in_=openapi.IN_QUERY,
        description="Enter position id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[position_id])
    def get(self, request):
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        position_id = data.get("position_id")
        queryset = AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
        ref_data = {}
        if position_id:
            queryset = queryset.filter(form_data=position_id)
            for query in queryset:
                source = query.applicant_details["source"]
                if source in ref_data:
                    ref_data[source] = ref_data[source] + 1
                else:
                    ref_data[source] = 1
            ref_data.pop("", None)
            ref_data.pop(None, None)
        else:
            queryset_obj = Profile.objects.filter(Q(user__user_company__url_domain=url_domain) | Q(user__user_company__url_domain=None))
            source_list = queryset_obj.values_list("source", flat=True)
            ref_data = Counter(source_list)
            ref_data.pop("", None)
            ref_data.pop(None, None)
        return ResponseOk(
            {
                "data": ref_data,
                "code": status.HTTP_200_OK,
                "message": "Candidate Source Count Fetched Successfully.",
            }
        )


class SendMail(APIView):
    email = openapi.Parameter(
        "email",
        in_=openapi.IN_QUERY,
        description="Enter email",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_STRING),
    )

    @swagger_auto_schema(manual_parameters=[email])
    def get(self, request, format=None):
        data = request.GET
        from_email = settings.EMAIL_HOST_USER
        to_email = data.get("email")
        otp = "".join(secrets.choice(string.digits) for i in range(4))
        context = {"otp": otp}
        body_msg = render_to_string("sendmail.html", context)
        msg = EmailMultiAlternatives("Email Verification<Don't Reply>", body_msg, from_email, [to_email])
        msg.content_subtype = "html"
        msg.send()
        data = {"otp": otp}
        try:
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Email Send Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Something wrong ",
                }
            )


class UpdateEmail(APIView):
    email = openapi.Parameter(
        "email",
        in_=openapi.IN_QUERY,
        description="Enter email",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_STRING),
    )

    @swagger_auto_schema(manual_parameters=[email])
    def get(self, request, format=None):
        data = request.GET
        email = data.get("email")
        try:
            user = User.objects.get(id=request.user.id)
            if user.email == email:
                return Response({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": "You can not Update with same Email."})
            try:
                user_obj = User.objects.get(email=email)
                return Response({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": "Email Already Exist."})
            except User.DoesNotExist:
                pass
            user.email = email
            user.username = email + "_" + request.user.user_company.url_domain
            user.save()
        except User.DoesNotExist:
            return Response({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": "RECORD_NOT_FOUND"})

        try:
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Email Updated Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Something wrong ",
                }
            )


class UserOffersList(APIView):
    """
    This API returns a list of all the Offer Letters that
    a candidate has received from all over the AppliedPosition
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Offer Letters List API for a User",
    )
    def get(self, request):
        try:
            profile = request.user.profile
            offer_letters = OfferLetter.objects.filter(offered_to__applied_profile=profile, offered_to__form_data__status="active")
            serializer = OfferLetterSerializer(offer_letters, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Offer letters fetched successfully!",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "error": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Something wrong ",
                }
            )


class TeamView(APIView):
    """
    This API is used to create, get and update a single Team.
    -Body
        name - name of the team
        manager - profile.id of the manager
        members - list
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Team create API for Hiring Manager and Rewruiter",
        operation_summary="Team Create API",
        request_body=user_serializers.TeamCreatUpdateSerializer,
    )
    def post(self, request):
        try:
            data = request.data
            print(data)
            serializer = user_serializers.TeamCreatUpdateSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "team added",
                    }
                )
            else:
                return ResponseBadRequest({"message": "error occured", "error": serializer.errors})
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e)})

    @swagger_auto_schema(
        operation_description="Team update API for Hiring Manager and Rewruiter. It required id of the team in the request body.",
        operation_summary="Team Update API",
        request_body=user_serializers.TeamCreatUpdateSerializer,
    )
    def put(self, request):
        try:
            data = request.data
            team_obj = Team.objects.get(id=data.get("id"))
            serializer = user_serializers.TeamCreatUpdateSerializer(team_obj, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "team updated",
                    }
                )
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e)})

    @swagger_auto_schema(
        operation_description="Team get API for Hiring Manager and Rewruiter. It required id of the team in the request body.",
        operation_summary="Team Get API",
        manual_parameters=[
            openapi.Parameter(
                "id",
                in_=openapi.IN_QUERY,
                description="id",
                type=openapi.TYPE_STRING,
            )
        ],
    )
    def get(self, request):
        try:
            if request.user.user_role.name in ["candidate", "employee"]:
                return ResponseBadRequest({"message": "invalid request"})
            data = request.GET
            team_obj = Team.objects.get(id=data.get("id"))
            serializer = user_serializers.TeamGetSerializer(team_obj)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "team added",
                }
            )
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e)})


class GetAllTeam(APIView):
    """
    This API is used to get all the Teams.
    -return
        A list of all the teams
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="API to get team and all its memebers.",
        operation_summary="All Team Members Get API",
        manual_parameters=[
            openapi.Parameter(
                "profile_id",
                in_=openapi.IN_QUERY,
                description="profile_id",
                type=openapi.TYPE_STRING,
            )
        ],
    )
    def get(self, request):
        try:
            if request.user.user_role.name in ["candidate", "employee"]:
                return ResponseBadRequest({"message": "invalid request"})
            data = request.GET
            response = {}
            profile_id = data.get("profile_id")
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
            if profile_id:
                profile_obj = Profile.objects.get(id=profile_id)
                teams_obj, created = Team.objects.get_or_create(manager=profile_obj)
                manager_serializer = user_serializers.CustomProfileSerializer(teams_obj.manager)
                response["manager"] = manager_serializer.data
                members = get_team_member(teams_obj)
                response["member"] = members
            else:
                response = {}
            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "team members fetched!",
                }
            )
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "No team member found!"})


class UpdateReferral(APIView):
    def put(self, request, pk):
        try:
            profile_obj = Profile.objects.get(id=pk)
            try:
                pk = decrypt(pk)
            except:
                pass
            if "refereed_by_profile" in request.data:
                ref_data = {"name": request.data.get("refereed_by_profile")}
                if "applied_position" in request.GET:
                    applied_position = request.GET.get("applied_position")
                    ap_obj = AppliedPosition.objects.get(id=int(applied_position))
                    ap_obj.refereed_by_profile = ref_data
                    ap_obj.save()
                else:
                    profile_obj.user_refereed_by = ref_data
                    profile_obj.save()
            return ResponseOk(
                {
                    "data": {"msg": "updated"},
                    "code": status.HTTP_200_OK,
                    "message": "team members fetched!",
                }
            )
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "No profile found!"})


class ImportBulkEmployee(APIView):
    """
    API used to import bulk employee from csv file.
    Args:
        domain - Domain of the company
    Body:
        file - csv file
    Returns:
        -success message(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Bulk employee upload API",
        operation_summary="Bulk employee upload API",
        manual_parameters=[],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "file": openapi.Schema(type=openapi.TYPE_FILE),
            },
            required=["file"],
        ),
    )
    def post(self, request):
        try:
            data = request.data
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            ser = user_serializers.ImportEmployeeFileSerializer(data=request.data)
            if ser.is_valid():
                obj = ser.save()
            else:
                raise serializers.ValidationError("file not read")
            file_data = None
            if obj.file.name.endswith(".csv"):
                csv_file = default_storage.open(obj.file.name, mode="r")
                # fp = open(obj.file.url, 'r')
                data = csv.reader(csv_file, delimiter=",")
                file_data = data
                next(data, None)
            elif obj.file.name.endswith(".xls") or obj.file.name.endswith(".xlsx"):
                df = pd.DataFrame(pd.read_excel(obj.file))
                data = df.values.tolist()
                file_data = data
            else:
                return ResponseBadRequest(
                    {
                        "data": "something went wrong",
                        "code": 400,
                        "message": str(error),
                    }
                )
            emails = []
            error = []
            file_data = []
            for row in data:
                file_data.append(row)
                try:
                    middle_name = row[2] if str(row[2]) != "nan" else None
                    user_role = Role.objects.get(company=company, name__iexact=row[4])
                    emails.append(row[0])
                    user = User(
                        username="{}_{}".format(row[0], url_domain),
                        email=row[0],
                        first_name=row[1],
                        middle_name=middle_name,
                        last_name=row[3],
                        user_role=user_role,
                        user_company=company,
                        is_active=False,
                    )
                    user.save()
                except Exception as e:
                    error.append(e)
                    print(e)
            duplicates = None
            # if users:
            #     try:
            #         User.objects.bulk_create(users)
            #     except IntegrityError:
            #         print("----")
            #         duplicates = "Some employee were not added as they appear to be duplicates."
            #         for obj in users:
            #             try:
            #                 obj.save()
            #             except:
            #                 continue
            # Create profile
            # csv_file = default_storage.open(file_name, mode="r")
            # data = csv.reader(csv_file, delimiter=",")
            # next(data, None)
            profiles = []
            for row in file_data:
                try:
                    user = User.objects.get(username="{}_{}".format(row[0], url_domain))
                    department = Department.objects.filter(department_name__iexact=row[5]).last()
                    encoded_id = "".join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(10))
                    user.encoded_id = encoded_id
                    password = generate_password()
                    user.set_password(password)
                    user.save()
                    current_site = user.user_company.url_domain
                    link = "https://{}.{}/employee/create-profile/{}/".format(current_site, settings.DOMAIN_NAME, encoded_id)
                    send_custom_email(
                        "Registration Link", link, user.email, user.first_name, company_name=user.user_company.company_name, password=password
                    )
                    country_obj = Country.objects.filter(name__iexact=row[7]).last()
                    state_obj = State.objects.filter(country=country_obj, name__iexact=row[8]).last()
                    city_obj = City.objects.filter(country=country_obj, state=state_obj, name__iexact=row[9]).last()
                    address_obj = Address.objects.create(country=country_obj, state=state_obj, city=city_obj)
                    address_obj.save()
                    profile = Profile(user=user, department=department, employee_id=row[6], phone_no=row[10], address=address_obj)
                    profiles.append(profile)
                except Exception as e:
                    error.append(str(e))
            if profiles:
                Profile.objects.bulk_create(profiles, ignore_conflicts=True)
                return ResponseOk(
                    {"data": None, "code": status.HTTP_200_OK, "toast-message": duplicates, "message": "employees added", "error": str(error)}
                )
            else:
                User.objects.filter(email__in=emails).delete()
            obj.delete()
            return ResponseBadRequest(
                {
                    "data": "something went wrong",
                    "code": 400,
                    "message": str(error),
                }
            )
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "employees not imported"})


class CandidateBooleanSearch(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    sort_dir = openapi.Parameter(
        "sort_dir",
        in_=openapi.IN_QUERY,
        description="asc or desc",
        type=openapi.TYPE_STRING,
    )
    sort_field = openapi.Parameter(
        "sort_field",
        in_=openapi.IN_QUERY,
        description="sort_field",
        type=openapi.TYPE_STRING,
    )
    export = openapi.Parameter("export", in_=openapi.IN_QUERY, description="export", type=openapi.TYPE_STRING)

    @swagger_auto_schema(
        operation_description="This API handles the boolean search for the candidates.",
        operation_summary="Boolean Search API",
        manual_parameters=[sort_field, sort_dir],
    )
    def get(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            if data.get("export"):
                export = True
            else:
                export = False
            sort_field = data.get("sort_field")
            sort_dir = data.get("sort_dir")
            search = data.get("query")
            queryset = boolean_search(search, company)
            if queryset:
                # applied_position = AppliedPosition.objects.filter(applied_profile__user__in=queryset)
                queryset = sort_data(queryset, sort_field, sort_dir)
                pagination_data = paginate_data(request, queryset, User)
                queryset = pagination_data.get("paginate_data")
                if queryset:
                    if export:
                        select_type = request.GET.get("select_type")
                        csv_response = HttpResponse(content_type="text/csv")
                        csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                        writer = csv.writer(csv_response)
                        selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                        if selected_fields:
                            selected_fields = selected_fields.last().selected_fields
                        else:
                            selected_fields = ["Hiring Manager", "Position No", "Job Title", "Country", "Status"]
                        writer.writerow(selected_fields)
                        for data in queryset:
                            serializer_data = AppliedPositionListSerializer(data).data
                            row = []
                            for field in selected_fields:
                                if field.lower() in ["department", "category", "location", "country", "level", "employment type"]:
                                    field = form_utils.position_dict.get(field)
                                    try:
                                        value = data.form_data.form_data.get(field).get("name")
                                        if value is None:
                                            value = data.form_data.form_data.get(field)[0].get("label")
                                    except Exception as e:
                                        value = None
                                elif field in ["Position Name", "Job Title"]:
                                    value = data.form_data.form_data.get("job_title")
                                elif field == "Candidate Name":
                                    value = serializer_data["applied_profile"]["user"]["first_name"]
                                elif field in ["My Skills", "my skills"]:
                                    value = serializer_data["applied_profile"]["skill"]
                                else:
                                    field = form_utils.position_dict.get(field)
                                    value = form_utils.get_value(serializer_data, field)
                                try:
                                    row.append(next(value, None))
                                except:
                                    row.append(value)
                            writer.writerow(row)
                        response = HttpResponse(csv_response, content_type="text/csv")
                        return response
                    else:
                        serializer = user_serializers.ExtendedGetUserSerializer(queryset, many=True).data
                        return ResponseOk(
                            {
                                "data": serializer,
                                "meta": {
                                    "page": pagination_data.get("page"),
                                    "total_pages": pagination_data.get("total_pages"),
                                    "perpage": pagination_data.get("perpage"),
                                    "sort_dir": sort_dir,
                                    "sort_field": sort_field,
                                    "total_records": pagination_data.get("total_records"),
                                },
                            }
                        )
            else:
                raise ValueError("Records not found")
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "data not fetched"})


class CustomQuestionView(APIView):
    @swagger_auto_schema(
        operation_description="Custom Questions Create API. It also needs the domain field in request body.",
        operation_summary="Custom Questions Create API",
        request_body=CustomQuestionSerializer,
    )
    def post(self, request):
        try:
            data = request.data
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            data = request.data
            serializer = CustomQuestionSerializer(data=data)
            if serializer.is_valid():
                obj = serializer.save()
                obj.company = company
                if request.user.is_authenticated:
                    obj.created_by = request.user
                    obj.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "custom question created",
                    }
                )
            else:
                return ResponseBadRequest({"message": "error occured", "error": serializer.errors, "data": "question not created"})
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "question not created"})

    @swagger_auto_schema(
        operation_description="Custom Questions Update API. It also needs the domain field and id of the question in request body.",
        operation_summary="Custom Questions Update API",
        request_body=CustomQuestionSerializer,
    )
    def put(self, request):
        try:
            data = request.data
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            data = request.data
            obj = CustomQuestion.objects.get(id=data.get("id"))
            serializer = CustomQuestionSerializer(obj, data=data, partial=True)
            if serializer.is_valid():
                obj = serializer.save()
                if request.user.is_authenticated:
                    obj.company = company
                    obj.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "custom question updated",
                    }
                )
            else:
                return ResponseBadRequest({"message": "error occured", "error": serializer.errors, "data": "question not updated"})
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "question not updated"})

    @swagger_auto_schema(
        operation_description="Custom Questions Get API.",
        operation_summary="Custom Questions Get API",
        manual_parameters=[
            openapi.Parameter(
                "email",
                in_=openapi.IN_QUERY,
                description="email",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "position",
                in_=openapi.IN_QUERY,
                description="position",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "is_active",
                in_=openapi.IN_QUERY,
                description="is_active",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "type",
                in_=openapi.IN_QUERY,
                description="type",
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            if data.get("email") is not None:
                created_by_email = data.get("email")
            else:
                created_by_email = None
            if data.get("position") is not None:
                position = data.get("position")
            else:
                position = None
            position = [position]
            is_active = None
            if data.get("is_active") == "true":
                is_active = True
            is_admin = None
            if data.get("type") == "admin":
                is_admin = True
            if request.user.is_authenticated:
                if request.user.user_role.name == "candidate":
                    queryset = CustomQuestion.objects.filter(Q(company=company) | Q(created_by=request.user)).filter(
                        Q(created_by_email=None) | Q(created_by_email=created_by_email)
                    )
                else:
                    queryset = CustomQuestion.objects.filter(company=company)
            else:
                queryset = CustomQuestion.objects.filter(company=company).filter(Q(created_by_email=created_by_email) | Q(created_by_email=None))
            if is_active:
                queryset = queryset.filter(is_active=is_active)
            # if position and queryset.filter(position__in=position, created_by_email=None).count():
            if position:
                queryset = queryset.filter(position__in=position)
                own_questions = CustomQuestion.objects.filter(company=company, created_by_email=created_by_email, position__in=position)
                queryset = queryset | own_questions
            else:
                queryset = queryset.filter(position=None)
                own_questions = CustomQuestion.objects.filter(company=company, created_by_email=created_by_email, position__in=position)
                queryset = queryset | own_questions
            if is_admin:
                queryset = CustomQuestion.objects.filter(company=company, created_by_email=None)
            serializer = CustomQuestionSerializer(queryset.order_by("id"), many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "custom question fetched",
                }
            )
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "question not fetched"})

    @swagger_auto_schema(
        operation_description="Custom Questions Delete API. It also needs the domain field and id of the question in request body.",
        operation_summary="Custom Questions Delete API",
        manual_parameters=[
            openapi.Parameter("question", in_=openapi.IN_QUERY, description="question", type=openapi.TYPE_INTEGER, required=True),
        ],
    )
    def delete(self, request):
        try:
            data = request.GET
            question = data.get("question")
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            queryset = CustomQuestion.objects.get(id=question)
            queryset.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "custom question deleted",
                }
            )
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "question not found"})


class CustomQuestionOpView(APIView):
    def get(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            if data.get("email") is not None:
                created_by_email = data.get("email")
            else:
                created_by_email = None
            if data.get("position") is not None:
                position = data.get("position")
            else:
                position = None
            position = [position]
            is_active = None
            if data.get("is_active") == "true":
                is_active = True
            is_admin = None
            if data.get("type") == "admin":
                is_admin = True
            search = data.get("search", "")

            if request.user.is_authenticated:
                if request.user.user_role.name == "candidate":
                    queryset = CustomQuestion.objects.filter(Q(company=company) | Q(created_by=request.user)).filter(
                        Q(created_by_email=None) | Q(created_by_email=created_by_email)
                    )
                else:
                    queryset = CustomQuestion.objects.filter(company=company)
            else:
                queryset = CustomQuestion.objects.filter(company=company).filter(Q(created_by_email=created_by_email) | Q(created_by_email=None))
            if is_active:
                queryset = queryset.filter(is_active=is_active)
            if position and queryset.filter(position__in=position, created_by_email=None).count():
                queryset = queryset.filter(position__in=position)
                own_questions = CustomQuestion.objects.filter(company=company, created_by_email=created_by_email, position__in=position)
                queryset = queryset | own_questions
            else:
                queryset = queryset.filter(position=None)
                own_questions = CustomQuestion.objects.filter(company=company, created_by_email=created_by_email, position__in=position)
                queryset = queryset | own_questions
            if is_admin:
                queryset = CustomQuestion.objects.filter(company=company, created_by_email=None)
            if search:
                queryset = queryset.annotate(
                    string_id=Cast("id", output_field=CharField(max_length=256)),
                ).filter(Q(question__icontains=search) | Q(string_id__icontains=search))
            data = []
            for i in queryset:
                temp_data = {}
                temp_data["question_no"] = i.id
                temp_data["question"] = i.question
                temp_data["description"] = i.description
                temp_data["is_active"] = i.is_active
                temp_data["id"] = i.id
                data.append(temp_data)
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "custom question fetched",
                }
            )
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "question not fetched"})


class GetSingleCustomQuestionView(APIView):
    @swagger_auto_schema(
        operation_description="Custom Questions Get API.",
        operation_summary="Custom Questions Get API",
        manual_parameters=[
            openapi.Parameter(
                "email",
                in_=openapi.IN_QUERY,
                description="email",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "position",
                in_=openapi.IN_QUERY,
                description="position",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "is_active",
                in_=openapi.IN_QUERY,
                description="is_active",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "type",
                in_=openapi.IN_QUERY,
                description="type",
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request, pk):
        try:
            queryset = CustomQuestion.objects.get(id=pk)
            serializer = CustomQuestionSerializer(queryset)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "custom question fetched",
                }
            )
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "question not fetched"})


class AnswerView(APIView):
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Answer Create API. It also needs the domain field in request body.",
        operation_summary="Answer Create API",
        request_body=AnswerSerailizer,
    )
    def post(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            data = request.data
            data["user"] = request.user.id
            serializer = AnswerSerailizer(data=data)
            if serializer.is_valid():
                obj = serializer.save()
                if request.user.is_authenticated:
                    obj.user = request.user
                    obj.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "answers created",
                    }
                )
            else:
                return ResponseBadRequest({"message": "error occured", "error": serializer.errors, "data": "answer not created"})
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "answer not created"})

    @swagger_auto_schema(
        operation_description="Answer Update API. It also needs the domain field and id of the answer in request body.",
        operation_summary="Answer Update API",
        request_body=AnswerSerailizer,
    )
    def put(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            data = request.data
            data["user"] = request.user.id
            obj = Answer.objects.get(id=data.get("id"))
            serializer = AnswerSerailizer(obj, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "custom question created",
                    }
                )
            else:
                return ResponseBadRequest({"message": "error occured", "error": serializer.errors, "data": "answer updated"})
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "answer not updated"})

    @swagger_auto_schema(
        operation_description="Answer Get API. It sends multiple records of answers along with its question",
        operation_summary="Answer Get API",
        manual_parameters=[
            openapi.Parameter(
                "question",
                in_=openapi.IN_QUERY,
                description="question",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "email",
                in_=openapi.IN_QUERY,
                description="email",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "position",
                in_=openapi.IN_QUERY,
                description="position",
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            if data.get("question") is not None:
                question = int(data.get("question"))
                question = CustomQuestion.objects.get(id=question)
            else:
                raise serializers.ValidationError("question is required")
            if data.get("email") is not None:
                created_by_email = data.get("email")
            else:
                created_by_email = None
            if data.get("position") is not None:
                position = data.get("position")
            else:
                position = None

            queryset = Answer.objects.filter(created_by_email=created_by_email, question=question)
            if position:
                queryset = queryset.filter(position__id=position).last()
            else:
                queryset = queryset.last()
            if queryset:
                serializer = AnswerSerailizer(queryset)
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "answers fetched",
                    }
                )
            else:
                return ResponseBadRequest({"message": "User has not answered this question", "data": "answer not fetched"})
        except Exception as e:
            return ResponseBadRequest({"message": "error occured", "error": str(e), "data": "answer not fetched"})


class GetUserWeater(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Get User Weather API",
        operation_summary="Get User Weather API",
        manual_parameters=[
            openapi.Parameter(
                "lat",
                in_=openapi.IN_QUERY,
                description="lat",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "long",
                in_=openapi.IN_QUERY,
                description="long",
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data:
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Data fetched",
                }
            )
        data = request.GET
        lat = data.get("lat")
        long = data.get("long")
        # Get the location name
        try:
            geolocator = Nominatim(user_agent="user")
            location = geolocator.reverse("{}, {}".format(lat, long))
            location = str(location.address).split(", ")
            location_dict = {
                "city": location[0],
                "state": location[-3],
                "country": location[-1],
            }
        except:
            location_dict = {
                "city": "Not found",
                "state": "Not found",
                "country": "Not found",
            }
        # Using Open Meteo API
        # url = "https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}&hourly=temperature_2m,apparent_temperature,precipitation,rain,snowfall,cloudcover,visibility,windspeed_10m,winddirection_10m&daily=sunrise,sunset&timezone=auto&start_date={}&end_date={}&current_weather=true".format(lat, long, datetime.datetime.today().date(), datetime.datetime.today().date())
        # payload={}
        # headers = {}

        # response = main_req.request("GET", url, headers=headers, data=payload)

        # if response.status_code == 200:
        #     try:
        #         resp_data = response.json()
        #         time = resp_data['current_weather']['time']
        #         idx = resp_data['hourly']['time'].index(time)
        #         data = {}
        #         data['temperature'] = resp_data['hourly']['temperature_2m'][idx]
        #         data['feels_like'] = resp_data['hourly']['apparent_temperature'][idx]
        #         data['precipitation'] = resp_data['hourly']['precipitation'][idx]
        #         data['cloudcover'] = resp_data['hourly']['cloudcover'][idx]
        #         data['visibility'] = resp_data['hourly']['visibility'][idx]
        #         data['windspeed'] = resp_data['hourly']['windspeed_10m'][idx]
        #         data['winddirection'] = resp_data['hourly']['winddirection_10m'][idx]
        #         data['sunrise'] = resp_data['daily']['sunrise'][0]
        #         data['sunset'] = resp_data['daily']['sunset'][0]
        #         data['location'] = location_dict
        #         return ResponseOk(
        #             {
        #                 "data": data,
        #                 "code": status.HTTP_200_OK,
        #                 "message": "Data fetched",
        #             }
        #         )
        #     except Exception as e:
        #         return ResponseBadRequest(
        #             {
        #                 "data": None,
        #                 "error": str(e),
        #                 "message": "selected fields not found",
        #             }
        #         )
        url = "https://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&exclude=minutely,hourly,daily,alerts&appid={}&units=metric".format(
            lat, long, settings.OWAPI
        )
        payload = {}
        headers = {}
        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code == 200:
            resp_data = response.json()
            data = {}
            data["temperature"] = resp_data["main"]["temp"]
            data["feels_like"] = resp_data["main"]["feels_like"]
            data["temp_min"] = resp_data["main"]["temp_min"]
            data["temp_max"] = resp_data["main"]["temp_max"]
            data["windspeed"] = resp_data["wind"]["speed"]
            data["humidity"] = resp_data["main"]["humidity"]
            data["visibility"] = resp_data["visibility"]
            data["winddirection"] = resp_data["wind"]["deg"]
            timezone = resp_data["timezone"]
            sunrise_epoch = resp_data["sys"]["sunrise"]
            sunrset_epoch = resp_data["sys"]["sunset"]
            sunrise = datetime.datetime.fromtimestamp(sunrise_epoch) + datetime.timedelta(seconds=timezone)
            sunset = datetime.datetime.fromtimestamp(sunrset_epoch) + datetime.timedelta(seconds=timezone)
            data["sunrise"] = str(sunrise)
            data["sunset"] = str(sunset)
            data["location"] = location_dict
            try:
                data["icon"] = "https://openweathermap.org/img/wn/{}@2x.png".format(resp_data["weather"][0]["icon"])
                data["weather"] = resp_data["weather"][0]["main"]
            except Exception as e:
                data["icon"] = "https://openweathermap.org/img/wn/02d@2x.png"
                data["weather"] = "Clear"
            cache.set(request.get_full_path(), data)
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Data fetched",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": None,
                    "error": response.text(),
                    "message": "selected fields not found",
                }
            )


class ChangeCandidateEmail(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def put(self, request):
        try:
            if request.user.user_role.name in ["candidate", "employee"]:
                return ResponseBadRequest({"message": "invalid request"})
            data = request.data
            user_obj = User.objects.get(email=data.get("old_email"))
            user_obj.email = data.get("new_email")
            user_obj.username = "{}_{}".format(user_obj.email, request.user.user_company.url_domain)
            # Updates candidate status
            offer_obj = OfferLetter.objects.filter(offered_to__applied_profile__id=user_obj.profile.id).last()
            offer_obj.email_changed = True
            try:
                user_obj.user_company = offer_obj.offered_to.company
                user_obj.user_role = Role.objects.get(company=offer_obj.offered_to.company, name="employee")
                user_obj.profile.joined_date = datetime.datetime.now()
                user_obj.profile.save()
                user_obj.save()
            except Exception as e:
                message = str(e)
            offer_obj.save()
            user_obj.save()
            # user_obj.profile.was_candidate = False
            # user_obj.profile.save()
            # send mail for confirmation
            context = {}
            link = "https://{}.{}/".format(user_obj.user_company.url_domain, settings.DOMAIN_NAME)
            tittle = "Welcome aboard!"
            to_email = user_obj.email
            context["link"] = link
            context["employee_name"] = user_obj.get_full_name()
            context["company"] = user_obj.user_company.company_name
            body_msg = render_to_string("employee_confirm.html", context)
            msg = EmailMultiAlternatives(tittle, body_msg, tittle, [to_email])
            msg.content_subtype = "html"
            msg.send()
            # delete all the previous applied position
            # AppliedPosition.objects.filter(applied_profile=user_obj.profile).exclude(id=offer_obj.offered_to.id).delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "email updated",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "errors",
                }
            )


# class OktaGetReqURI(APIView):
#     def get(self, request):
#         app_state = secrets.token_urlsafe(64)
#         code_verifier = secrets.token_urlsafe(64)
#         hashed = hashlib.sha256(code_verifier.encode("ascii")).digest()
#         encoded = base64.urlsafe_b64encode(hashed)
#         code_challenge = encoded.decode("ascii").strip("=")
#         OktaState.objects.create(state=app_state, code_challenge=code_challenge)
#         print(app_state, code_challenge)
#         query_params = {
#             "client_id": settings.OKTA_OAUTH2_CLIENT_ID,
#             "redirect_uri": "http://127.0.0.1:8000/users/auth/api/v1/authorization-code/callback",
#             "scope": "openid email profile",
#             "state": app_state,
#             "code_challenge": code_challenge,
#             "code_challenge_method": "S256",
#             "response_type": "code",
#             "response_mode": "query",
#         }
#         request_uri = "{base_url}?{query_params}".format(
#             base_url=settings.OKTA_ORG_URL + "oauth2/default/v1/authorize", query_params=requests.compat.urlencode(query_params)
#         )
#         response = {"request_uri": request_uri, "msg": "success"}
#         return ResponseOk(
#             {
#                 "data": response,
#                 "code": status.HTTP_200_OK,
#             }
#         )


# def OktaCallback(request):
#     # try:
#     data = request.GET
#     headers = {"Content-Type": "application/x-www-form-urlencoded"}
#     code = data.get("code")
#     app_state = data.get("state")
#     okta_state = OktaState.objects.get(state=app_state)
#     query_params = {
#         "grant_type": "authorization_code",
#         "code": code,
#         "redirect_uri": "http://127.0.0.1:8000/users/auth/api/v1/authorization-code/callback",
#         "code_verifier": okta_state.code_challenge,
#     }
#     print(app_state, okta_state.code_challenge)
#     query_params = requests.compat.urlencode(query_params)
#     exchange = requests.post(
#         settings.OKTA_ORG_URL + "oauth2/default/v1/token",
#         headers=headers,
#         data=query_params,
#         auth=(settings.OKTA_OAUTH2_CLIENT_ID, settings.OKTA_OAUTH2_CLIENT_SECRET),
#     ).json()
#     print("here 1")
#     print(exchange)
#     if not exchange.get("token_type"):
#         return "Unsupported token type. Should be 'Bearer'.", 403
#     access_token = exchange["access_token"]
#     id_token = exchange["id_token"]
#     print("here")
#     userinfo_response = requests.get(settings.OKTA_ORG_URL + "oauth2/default/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"}).json()
#     unique_id = userinfo_response["sub"]
#     user_email = userinfo_response["email"]
#     user_name = userinfo_response["given_name"]

#     user = User(id_=unique_id, name=user_name, email=user_email)

#     if not User.get(unique_id):
#         User.create(unique_id, user_name, user_email)
#     return HttpResponse("Meeting not created. meeting data not found. State is {}".format(app_state))
#     # except Exception as e:
#     #     return HttpResponse("Something went wrong - {}".format(str(e)))


class GDPRAcceptanceView(APIView):
    """
    This API is used to mark the acceptance of the user to GDPR Docs. So that it can be used in its analytics
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="API Mark acceptance of GDPR by user. It works on basis of the authotized user",
        operation_summary="API to change acceptance to GDPR",
    )
    def post(self, request):
        try:
            data = request.data
            obj, created = GDPRAcceptence.objects.get_or_create(user=request.user)
            obj.accpted = True
            obj.save()
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "data saved",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "error occured",
                }
            )

    @swagger_auto_schema(
        operation_description="API Mark acceptance of GDPR to false. It works on basis of the authotized user",
        operation_summary="API to change acceptance to GDPR",
    )
    def delete(self, request):
        try:
            data = request.GET
            obj = GDPRAcceptence.objects.filter(user=request.user, accepted=True).delete()

            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "feature deleted successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "error occured",
                }
            )


class GetGDPRAnalytics(APIView):
    """
    API used to fetch the GDPR Analytics with time frame
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="API to fetch GDPR Analytics",
        operation_summary="API to fetch GDPR Analytics",
    )
    def get(self, request):
        try:
            total_counts = GDPRAcceptence.objects.all().count()
            today = datetime.datetime.now().date()
            threem_date = today - datetime.timedelta(days=90)
            threem_counts = GDPRAcceptence.objects.filter(created_at__gte=threem_date).count()
            sixm_date = today - datetime.timedelta(days=180)
            sixm_counts = GDPRAcceptence.objects.filter(created_at__gte=sixm_date).count()
            lasty_date = today - datetime.timedelta(days=365)
            lasty_counts = GDPRAcceptence.objects.filter(created_at__gte=lasty_date).count()
            data = {}
            data["threem_counts"] = threem_counts
            data["sixm_counts"] = sixm_counts
            data["lasty_counts"] = lasty_counts
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "feature deleted successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "error occured",
                }
            )


# class GetLinkedinAuthURL(APIView):
#     def get(self, request):
#         try:
#             url = "https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={}&redirect_uri={}&state=nostate&scope=r_liteprofile r_emailaddress w_member_social".format(
#                 settings.LINKEDIN_CLIENT_ID, settings.LINKEDIN_REDIRECT
#             )
#             data = {"url": url}
#             return ResponseOk(
#                 {
#                     "data": data,
#                     "code": status.HTTP_200_OK,
#                     "message": "feature deleted successfully",
#                 }
#             )
#         except Exception as e:
#             return ResponseBadRequest(
#                 {
#                     "data": str(e),
#                     "code": status.HTTP_400_BAD_REQUEST,
#                     "message": "error occured",
#                 }
#             )


# def LinkedinCallback(request):
#     try:
#         data = request.GET
#         code = data.get("code")
#         state = data.get("state")
#         url = "https://www.linkedin.com/oauth/v2/accessToken?code={}&grant_type=authorization_code&client_id={}&client_secret={}&redirect_uri={}".format(
#             code, settings.LINKEDIN_CLIENT_ID, settings.LINKEDIN_CLIENT_SECRET, settings.LINKEDIN_REDIRECT
#         )
#         payload = {}
#         headers = {}
#         linkedin_resp = requests.request("POST", url, headers=headers, data=payload)
#         resp = linkedin_resp.json()
#         if "access_token" in resp:
#             access_token = resp["access_token"]
#             url = "https://api.linkedin.com/v2/me"
#             payload = ""
#             headers = {
#                 "Authorization": "Bearer {}".format(access_token),
#             }
#             linkedin_resp = requests.request("GET", url, headers=headers, data=payload)
#             resp = linkedin_resp.json()
#             # if linkedin_resp.status_code == 200:
#             #     data = {}
#             # else:
#             #     pass
#             return HttpResponse("Data - {}".format(str(resp)))
#         else:
#             return HttpResponse("Not able to generate access token. See for more information - {}".format(resp))
#     except Exception as e:
#         print(e)
#         return HttpResponse("Something went wrong - {}".format(str(e)))


class VerifyDevice(APIView):
    def post(self, request):
        try:
            user_id = request.data.get("user_id")
            verification_obj = DeviceVerification.objects.filter(user__id=user_id).order_by("id").last()
            otp = request.data.get("otp")
            if verification_obj.otp == int(otp):
                # token = RefreshToken.for_user(verification_obj.user)
                # if not Token.objects.filter(token_type="access_token", user_id=user_id).exists():
                #     Token.objects.filter(user_id=user_id, token=str(token.access_token), token_type="access_token")
                # else:
                #     # token = Token.objects.filter(user_id=user_object.id, token_type="access_token").update(token=str(token.access_token))
                # token = Token.objects.filter(user_id=user_id, token_type="access_token")
                ref_token = RefreshToken.for_user(verification_obj.user)
                token = Token.objects.create(
                    user_id=user_id, token=str(ref_token.access_token), token_type="access_token", device=verification_obj.device
                )
                serializer = user_serializers.CandidateLoginDetailSerializer(verification_obj.user)
                verification_obj.delete()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "access_token": str(ref_token.access_token),
                        "refresh_token": str(ref_token),
                        "code": status.HTTP_200_OK,
                        "message": "All Countries",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": None,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "OTP did not matched!",
                    }
                )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "error": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "something went wrong!",
                }
            )


class VerifyDeviceFromLink(APIView):
    def get(self, request, opt):
        try:
            user_id = request.data.get("user_id")
            verification_obj = DeviceVerification.objects.filter(user__id=user_id).order_by("id").last()
            otp = request.data.get("otp")
            if verification_obj.otp == int(otp):
                ref_token = RefreshToken.for_user(verification_obj.user)
                token = Token.objects.create(
                    user_id=user_id, token=str(ref_token.access_token), token_type="access_token", device=verification_obj.device
                )
                serializer = user_serializers.CandidateLoginDetailSerializer(verification_obj.user)
                verification_obj.delete()
                verify_device("verified", user_id)
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "access_token": str(ref_token.access_token),
                        "refresh_token": str(ref_token),
                        "code": status.HTTP_200_OK,
                        "message": "All Countries",
                    }
                )
            elif opt != 0:
                verify_device("unverified", user_id)
                return ResponseBadRequest(
                    {
                        "data": None,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "OTP did not matched!",
                    }
                )
            else:
                verify_device("declined", user_id)
                return ResponseBadRequest(
                    {
                        "data": None,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "You declined the verification.",
                    }
                )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "error": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "something went wrong!",
                }
            )


class GetAllCandidate(APIView):
    """
    This GET function fetches candidate records from Usser model with pagination, searching and sorting, and return the data after serializing it.

    Args:
        None
    Body:
        -domain(mandatory)
        -search(optional)
        -page(optional)
        -perpage(optional)
        -sort_dir(optional)
        -sort_field(optional)
    Returns:
        -Fetches all serialized data(HTTP_200_OK)
        -Search query has no match(HTTP_400_BAD_REQUEST)
        -Exception text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    page = openapi.Parameter(
        "page",
        in_=openapi.IN_QUERY,
        description="page",
        type=openapi.TYPE_STRING,
    )
    perpage = openapi.Parameter(
        "perpage",
        in_=openapi.IN_QUERY,
        description="perpage",
        type=openapi.TYPE_STRING,
    )
    sort_dir = openapi.Parameter(
        "sort_dir",
        in_=openapi.IN_QUERY,
        description="asc or desc",
        type=openapi.TYPE_STRING,
    )
    sort_field = openapi.Parameter(
        "sort_field",
        in_=openapi.IN_QUERY,
        description="sort_field",
        type=openapi.TYPE_STRING,
    )
    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export data or not",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            page,
            perpage,
            sort_dir,
            sort_field,
            export,
        ]
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET

            if request.headers.get("domain"):
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            page = data.get("page", 1)
            limit = data.get("perpage", settings.PAGE_SIZE)
            if data.get("export"):
                export = True
            else:
                export = False
            sort_field = data.get("sort_field")

            sort_dir = data.get("sort_dir")

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            user = User.objects.all().filter(user_company__url_domain=url_domain).filter(user_role__name__in=["candidate"])
            if "position_status" in request.GET:
                user = user.filter(profile__applied_profile__application_status=request.GET.get("position_status"))
            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "name":
                        user = user.order_by("name")
                    elif sort_field == "capital":
                        user = user.order_by("capital")
                    elif sort_field == "id":
                        user = user.order_by("id")

                    else:
                        user = user.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "name":
                        user = user.order_by("-name")
                    elif sort_field == "capital":
                        user = user.order_by("-capital")
                    elif sort_field == "id":
                        user = user.order_by("-id")

                    else:
                        user = user.order_by("-id")
            else:
                user = user.order_by("-id")
            count = user.count()
            if page and limit:
                user = user[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1
            if user:
                user = user.select_related("profile", "user_role", "profile__address", "profile__department")
                user = user.prefetch_related("profile__skill", "profile__education", "profile__media")
                serializer = user_serializers.ExtendedGetUserSerializer(user, many=True)
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                    if selected_fields:
                        selected_fields = selected_fields.last().selected_fields
                    else:
                        selected_fields = ["Candidate Name", "Skill", "Location", "Action"]
                    writer.writerow(selected_fields)
                    for serializer_data in serializer.data:
                        row = []
                        for field in selected_fields:
                            if field.lower() in ["city", "country", "level", "skill"]:
                                field = form_utils.position_dict.get(field)
                                try:
                                    value = data.form_data.form_data.get(field).get("name")
                                    if value is None:
                                        value = data.form_data.form_data.get(field)[0].get("label")
                                except Exception as e:
                                    value = None
                            elif field == "Candidate Name":
                                value = (
                                    serializer_data["applied_profile"]["user"]["first_name"]
                                    + " "
                                    + str(serializer_data["applied_profile"]["user"]["last_name"])
                                )
                            elif field in ["My Skills", "my skills", "skills", "Skills"]:
                                value = serializer_data["applied_profile"]["skill"]
                            elif field.lower() == "location":
                                try:
                                    value = serializer_data["applied_profile"]["address"]["country"]["name"]
                                except:
                                    value = None
                            else:
                                field = form_utils.position_dict.get(field)
                                value = form_utils.get_value(serializer_data, field)
                            try:
                                row.append(next(value, None))
                            except:
                                row.append(value)
                        writer.writerow(row)
                    response = HttpResponse(csv_response, content_type="text/csv")
                    return response
                else:
                    return ResponseOk(
                        {
                            "data": serializer.data,
                            "meta": {
                                "page": page,
                                "total_pages": pages,
                                "perpage": limit,
                                "sort_dir": sort_dir,
                                "sort_field": sort_field,
                                "total_records": count,
                            },
                        }
                    )
            return ResponseBadRequest("Search query has no match")

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})
