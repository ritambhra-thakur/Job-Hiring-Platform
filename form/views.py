import calendar
import copy
import csv
import datetime
import json
import math
import os
import time
from ast import Pass
from code import interact
from datetime import date, timedelta
from itertools import chain
from multiprocessing import context
from operator import is_
from tkinter import E
from urllib import request
from xmlrpc.client import DateTime

import pandas as pd
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db.models import Avg, CharField, Count, Q
from django.db.models import Value as V
from django.db.models.functions import (
    Cast,
    Concat,
    ExtractDay,
    ExtractMonth,
    ExtractQuarter,
    ExtractWeek,
    ExtractYear,
    TruncDate,
    TruncMonth,
    TruncWeek,
    TruncYear,
)
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from pytz import timezone as pytz_tz
from rest_framework import filters, permissions, serializers
from rest_framework import status
from rest_framework import status as rest_status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication

import form.models as FormModel
import form.serializers as FormSerializer
import user
from app import choices
from app.CSVWriter import CSVWriter
from app.encryption import decrypt, encrypt
from app.memcache_stats import MemcachedStats
from app.response import ResponseBadRequest, ResponseNotFound, ResponseOk
from app.SendinSES import (
    fetch_dynamic_email_template,
    send_add_candidate_email,
    send_offer_approval_mail,
    send_postion_approval_mail,
    send_reminder_email,
)
from app.util import (
    FormDataSerializer,
    create_activity_log,
    custom_get_object,
    custom_get_pagination,
    download_csv,
    generate_file_name,
    generate_offer_id,
    generate_offer_pdf,
    get_all_applied_position,
    get_hiring_managers_form_data,
    get_members_form_data,
    next_end_date,
    paginate_data,
    search_data,
    send_instant_notification,
    send_reminder,
    sort_data,
)
from company.models import Company, FeaturesEnabled
from email_template.models import EmailTemplate
from form.models import FormData
from form.utils import get_complete_feedback
from main import settings
from notification.models import Notifications, NotificationType
from primary_data.models import (
    Country,
    Education,
    EducationType,
    Experience,
    University,
)
from primary_data.serializers import GetAddressSerializer
from role.models import Role
from scheduling.utils import get_calendly_link
from scorecard.models import PositionScoreCard
from stage.models import *
from url_shortener import utils as url_shortner_utils
from url_shortener.models import ShortURL
from user.models import ActivityLogs, Profile, Team, User
from user.serializers import ActivityLogsSerializer

from . import utils as form_utils
from .models import (
    ApplicantDocuments,
    AppliedPosition,
    CareerTemplate,
    OfferApproval,
    OfferLetter,
    OfferLetterTemplate,
    PositionApproval,
    Reason,
    ReasonType,
    UnapprovedAppliedPosition,
    UserSelectedField,
)
from .serializers import (
    AppliedPositionListSerializer,
    AppliedPositionSerializer,
    CareerTemplateSerializer,
    CreateReasonSerializer,
    GetOfferLetterSerializer,
    OfferLetterSerializer,
    OfferLetterTemplateGetSerializer,
    OfferLetterTemplateSerializer,
    OpAppliedPositionListSerializer,
    ReasonSerializer,
    ReasonTypeSerializer,
    UserSelectedFieldSerializer,
)

# Create your views here.


class GetAllForm(APIView):
    """
     This GET function fetches all records from FormModel model
     after filtering on the basis of 'form_name' and 'domain',
     and return the data after serializing it.

    Args:
        None
    Body:
        - form_name (optional)
    Returns:
        - Serialized FormModel model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        - serializers.ValidationError("domain field required")
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.Form.objects.all()
    form_name = openapi.Parameter(
        "form_name",
        in_=openapi.IN_QUERY,
        description="Enter form_name",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(operation_description="Form Data List API", manual_parameters=[form_name])
    def get(self, request):
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        try:
            data = cache.get(request.get_full_path() + "?domain=" + url_domain)
        except:
            data = None
        if data:
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "code": status.HTTP_200_OK,
                    "message": "form list by company",
                }
            )
        data = request.GET

        form_name = data.get("form_name", "")

        try:
            form = self.queryset.all().filter(company__url_domain=url_domain)

            if form_name:
                form = form.filter(Q(form_name__icontains=form_name))

            serializer = FormSerializer.FormSerializer(form, many=True)
            resp = {
                "data": serializer.data,
                "code": status.HTTP_200_OK,
                "message": "form list by company",
            }
            cache.set(request.get_full_path() + "?domain=" + url_domain, resp)
            return ResponseOk(resp)
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "form does not exist",
                }
            )


class GetForm(APIView):
    """
     This GET function fetches particular FormModel instance by ID,
     and return it after serializing it.

    Args:
        pk(form_id)
    Body:
        None
    Returns:
        - Serialized FormModel model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            form = custom_get_object(pk, FormModel.Form)
            serializer = FormSerializer.FormSerializer(form)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Get Form successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Form Does Not Exist",
                }
            )


class CreateForm(APIView):
    """
    This POST function creates a FormModel record from the data passed in the body.

    Args:
        None
    Body:
        FormModel Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Form Create API",
        operation_summary="Form Create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "form_name": openapi.Schema(type=openapi.TYPE_STRING),
                "company": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description=" enter company id (Company.id) field",
                ),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                "is_deleted": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
        ),
    )
    def post(self, request):
        serializer = FormSerializer.FormSerializer(
            data=request.data,
        )
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Form created successfully",
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


class UpdateForm(APIView):
    """
    This PUT function updates a FormModel record according to the form_model_id passed in url.

    Args:
        pk(form_model_id)
    Body:
        FormModel Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) form_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Form update API",
        operation_summary="Form update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "form_name": openapi.Schema(type=openapi.TYPE_STRING),
                "company": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description=" enter company id (Company.id) field",
                ),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                "is_deleted": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
        ),
    )
    def put(self, request, pk):
        try:
            data = request.data
            form = custom_get_object(pk, FormModel.Form)
            serializer = FormSerializer.FormSerializer(form, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "form updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "form Does Not Exist",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "form Does Not Exist",
                }
            )


class DeleteForm(APIView):
    """
     This DELETE function Deletes a FormModel record accroding to the form_model_id passed in url.

    Args:
        pk(form_model_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) form_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            form = custom_get_object(pk, FormModel.Form)
            form.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Form deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Form Does Not Exist",
                }
            )


class GetAllField(APIView):
    """
     This GET function fetches all records from Field model
     after filtering on the basis of 'domain', 'field_name' and 'form',
     and return the data after serializing it.

    Args:
        None
    Body:
        - domain (mandatory)
        - form (optional)
        - field_name(optional)
    Returns:
        - Serialized Field model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.Field.objects.all()
    form = openapi.Parameter(
        "form",
        in_=openapi.IN_QUERY,
        description="search form_id",
        type=openapi.TYPE_STRING,
    )
    field_name = openapi.Parameter(
        "field_name",
        in_=openapi.IN_QUERY,
        description="search field_name",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(operation_description="Form Data List API", operation_summary="Form Data List API", manual_parameters=[form, field_name])
    def get(self, request):
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        try:
            data = cache.get(request.get_full_path() + "?domain=" + url_domain)
        except:
            data = None
        if data:
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "code": status.HTTP_200_OK,
                    "message": "field list by company",
                }
            )
        data = request.GET
        if data.get("export"):
            export = True
        else:
            export = False
        try:
            data = request.GET
            field = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            if FeaturesEnabled.objects.filter(feature="recruiter", enabled=False, company__url_domain=url_domain):
                field = field.exclude(field_name="Recruiter")
            for i in field:
                print(i.field_name, i.form.id)
            form_id = data.get("form", "")

            field_name = data.get("field_name", "")

            if form_id:
                field = field.filter(form__id=int(form_id))
            if field_name:
                field = field.filter(Q(field_name__icontains=field_name))
            if field:
                # By default sourting is based on sort_order
                field = field.order_by("sort_order")
                if export:
                    data = download_csv(
                        request, field, ["field_name", "description", "slug", "field_type", "field_block", "sort_order", "is_mandatory"]
                    )
                    response = HttpResponse(data, content_type="text/csv")
                    return response
                else:
                    field = field.order_by("sort_order")
                    try:
                        if form_id:
                            form_obj = FormModel.Form.objects.get(id=form_id)
                            if form_obj.form_name == "Application Form":
                                field = field.order_by("id")
                    except Exception as e:
                        print(e)
                    field_data = []
                    for f in field:
                        temp_dict = {}
                        temp_dict["id"] = f.id
                        temp_dict["description"] = f.description
                        temp_dict["field_block"] = f.field_block
                        temp_dict["field_name"] = f.field_name
                        temp_dict["field_type"] = f.field_type.id
                        temp_dict["form"] = f.form.id
                        temp_dict["slug"] = f.slug
                        temp_dict["sort_order"] = f.sort_order
                        temp_dict["is_mandatory"] = f.is_mandatory
                        temp_dict["is_default"] = f.is_default
                        temp_dict["is_active"] = f.is_active
                        choices = FormModel.FieldChoice.objects.filter(field=f)
                        if choices:
                            choice_data = []
                            for choice in choices:
                                temp_choice = {}
                                temp_choice["choice_key"] = choice.choice_key
                                temp_choice["choice_value"] = choice.choice_value
                                temp_choice["sort_order"] = choice.sort_order
                                choice_data.append(temp_choice)
                            temp_dict["form_choices"] = choice_data
                        else:
                            temp_dict["form_choices"] = []
                        field_data.append(temp_dict)
                    resp = {
                        "data": field_data,
                        "code": status.HTTP_200_OK,
                        "message": "field list by company",
                    }
                    cache.set(request.get_full_path() + "?domain=" + url_domain, resp)
                    return ResponseOk(resp)
            else:
                return ResponseBadRequest("Search query has no match")
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "field does not exist",
                }
            )


class GetField(APIView):
    """
    This GET function fetches particular Field model instance by ID,
    and return it after serializing it.

    Args:
        pk(field_id)
    Body:
        None
    Returns:
        - Serialized Field model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) field Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            field = custom_get_object(pk, FormModel.Field)
            serializer = FormSerializer.FieldSerializer(field)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get field successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "field Does Not Exist",
                }
            )


class CreateField(APIView):

    """
    This POST function creates a Field Model record from the data passed in the body.

    Args:
        None
    Body:
        Field model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Field create API",
        operation_summary="Field create API",
        request_body=FormSerializer.FieldSerializer
        # request_body=openapi.Schema(
        #     type=openapi.TYPE_OBJECT,
        #     properties={
        #         "field_name": openapi.Schema(type=openapi.TYPE_STRING),
        #         "company": openapi.Schema(type=openapi.TYPE_INTEGER),
        #         "form": openapi.Schema(type=openapi.TYPE_INTEGER),
        #         "field_type": openapi.Schema(type=openapi.TYPE_INTEGER),
        #         "description": openapi.Schema(type=openapi.TYPE_STRING),
        #         "is_mandatory": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        #         "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        #         "is_deleted": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        #     },
        # ),
    )
    def post(self, request):
        try:
            mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
            for i in mem.keys():
                key = i.partition("/")[-1]
                try:
                    if key.startswith("form/field/api/v1/"):
                        cache.delete("/" + key)
                        continue
                except Exception as e:
                    pass
            if "field_block" in request.data:
                check_fields = FormModel.Field.objects.get(
                    form=request.data["form"], field_name=request.data["field_name"], field_block=request.data["field_block"]
                )
            else:
                check_fields = FormModel.Field.objects.get(
                    form=request.data["form"],
                    field_name=request.data["field_name"],
                )
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Field Already Exist",
                }
            )

        except:
            serializer = FormSerializer.FieldSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Field created successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Field is not valid",
                    }
                )


class UpdateField(APIView):
    """
     This PUT function updates a Field Model record according to the field_id passed in url.

    Args:
        pk(field_id)
    Body:
        Field Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) Field does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Field update API",
        operation_summary="Field update API",
        request_body=FormSerializer.FieldSerializer
        # request_body=openapi.Schema(
        #     type=openapi.TYPE_OBJECT,
        #     properties={
        #         "field_name": openapi.Schema(type=openapi.TYPE_STRING),
        #         "company": openapi.Schema(type=openapi.TYPE_INTEGER),
        #         "form": openapi.Schema(type=openapi.TYPE_INTEGER),
        #         "field_type": openapi.Schema(type=openapi.TYPE_INTEGER),
        #         "description": openapi.Schema(type=openapi.TYPE_STRING),
        #         "is_mandatory": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        #         "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        #         "is_deleted": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        #     },
        # ),
    )
    def put(self, request, pk):
        try:
            mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
            for i in mem.keys():
                key = i.partition("/")[-1]
                try:
                    if key.startswith("form/field/api/v1/"):
                        cache.delete("/" + key)
                        continue
                except Exception as e:
                    pass
            data = request.data
            field = custom_get_object(pk, FormModel.Field)
            serializer = FormSerializer.FieldSerializer(field, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Field updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Field Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Field Does Not Exist",
                }
            )


class DeleteField(APIView):
    """
     This DELETE function Deletes a Field Model record accroding to the field_id passed in url.

    Args:
        pk(field_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Field does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
            for i in mem.keys():
                key = i.partition("/")[-1]
                try:
                    if key.startswith("form/field/api/v1/"):
                        cache.delete("/" + key)
                        continue
                except Exception as e:
                    pass
            field = custom_get_object(pk, FormModel.Field)
            field.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Field deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Field Does Not Exist",
                }
            )


class GetAllFieldType(APIView):
    """
     This GET function fetches all records from FieldType model
     and return the data after serializing it.

    Args:
        None
    Body:
        None
    Returns:
        - Serialized FieldType model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FieldType Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    def get(self, request):
        try:
            field_type = FormModel.FieldType.objects.all()

            serializer = FormSerializer.FieldTypeSerializer(field_type, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "field_type list",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "field_type Does Not Exist",
                }
            )


class GetFieldType(APIView):
    """
     This GET function fetches particular FieldType model instance by ID,
     and return it after serializing it.

    Args:
        pk(field_type_id)
    Body:
        None
    Returns:
        - Serialized FieldType model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) field_type Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            field_type = custom_get_object(pk, FormModel.FieldType)
            serializer = FormSerializer.FieldTypeSerializer(field_type)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get field_type successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " field_type Not Exist",
                }
            )


class CreateFieldType(APIView):
    """
     This POST function creates a FieldType Model record from the data passed in the body.

    Args:
        None
    Body:
        FieldType model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Field_Type create API",
        operation_summary="Field_Type create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "field_type": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        serializer = FormSerializer.FieldTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Field_Type created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Field_Type is not valid",
                }
            )


class UpdateFieldType(APIView):
    """
     This PUT function updates a FieldType Model record according to the field_type_id passed in url.

    Args:
        pk(field_type_id)
    Body:
        FieldType Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) field_type does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Field_Type update API",
        operation_summary="Field_Type update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "field_type": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def put(self, request, pk):
        try:
            data = request.data
            field_type = custom_get_object(pk, FormModel.FieldType)
            serializer = FormSerializer.FieldTypeSerializer(field_type, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Field_Type updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Field_Type Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Field_Type Does Not Exist",
                }
            )


class DeleteFieldType(APIView):
    """
     This DELETE function Deletes a FieldType Model record accroding to the field_type_id passed in url.

    Args:
        pk(field_type_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) field_type does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            field_type = custom_get_object(pk, FormModel.FieldType)
            field_type.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Field_Type deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Field_Type Does Not Exist",
                }
            )


class GetAllFieldChoice(APIView):
    """
     This GET function fetches all records from Field Choice model
     and return the data after serializing it.

    Args:
        None
    Body:
        field_id(optional)
    Returns:
        - Serialized FieldType model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FieldType Does Not Exist
        - serializer.errors(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    field_id = openapi.Parameter(
        "field_id",
        in_=openapi.IN_QUERY,
        description="search field_id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[field_id])
    def get(self, request):
        data = request.GET
        if data.get("field_id"):
            field_id = data.get("field_id")
        else:
            field_id = ""

        try:
            field_choice = FormModel.FieldChoice.objects.all()

            if field_id:
                field_choice = field_choice.filter(Q(field_id=field_id))

            if field_choice:
                # by default order by sort_order
                field_choice = field_choice.order_by("sort_order")

                serializer = FormSerializer.FieldChoiceSerializer(field_choice, many=True)
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Field_choice list",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": "No Data Found",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Field_choice Does Not Exist",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Field_choice Does Not Exist",
                }
            )


class GetFieldChoice(APIView):
    """
     This GET function fetches particular Field Choice model instance by ID,
     and return it after serializing it.

    Args:
        pk(field_choice_id)
    Body:
        None
    Returns:
        - Serialized Field Choice model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) field_choice Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            field_choice = custom_get_object(pk, FormModel.FieldChoice)
            serializer = FormSerializer.FieldChoiceSerializer(field_choice)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get FieldChoice successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " FieldChoice Not Exist",
                }
            )


class CreateFieldChoice(APIView):
    """
    This POST function creates a Field Choice Model record from the data passed in the body.

    Args:
        None
    Body:
        Field Choice model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Field_Choice create API",
        operation_summary="Field_Choice create API",
        request_body=FormSerializer.FieldChoiceSerializer
        # request_body=openapi.Schema(
        #     type=openapi.TYPE_OBJECT,
        #     properties={
        #         "choice_key": openapi.Schema(type=openapi.TYPE_STRING),
        #         "choice_value": openapi.Schema(type=openapi.TYPE_STRING),
        #         "field": openapi.Schema(type=openapi.TYPE_INTEGER),
        #     },
        # ),
    )
    def post(self, request):
        serializer = FormSerializer.FieldChoiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Field_Choice created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Field_Choice is not valid",
                }
            )


class UpdateFieldChoice(APIView):
    """
    This PUT function updates a Field Choice Model record according to the field_type_id passed in url.

    Args:
        pk(field_choice_id)
    Body:
        Field Choice Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) field_choice does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Field_Choice update API",
        operation_summary="Field_Choice update API",
        request_body=FormSerializer.FieldChoiceSerializer
        # request_body=openapi.Schema(
        #     type=openapi.TYPE_OBJECT,
        #     properties={
        #         "choice_key": openapi.Schema(type=openapi.TYPE_STRING),
        #         "choice_value": openapi.Schema(type=openapi.TYPE_STRING),
        #         "field": openapi.Schema(type=openapi.TYPE_INTEGER),
        #     },
        # ),
    )
    def put(self, request, pk):
        try:
            data = request.data
            field_choice = custom_get_object(pk, FormModel.FieldChoice)
            serializer = FormSerializer.FieldChoiceSerializer(field_choice, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Field_Choice updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Field_Choice Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Field_Choice Does Not Exist",
                }
            )


class DeleteFieldChoice(APIView):
    """
    This DELETE function Deletes a Field Choice Model record accroding to the field_Choice_id passed in url.

    Args:
        pk(field_choice_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) field_choice does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            field_choice = custom_get_object(pk, FormModel.FieldChoice)
            field_choice.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "FieldChoice deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "FieldChoice Does Not Exist",
                }
            )


class GetAllFormData(APIView):
    """
    This GET function fetches all records from FormData model accrding
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - page(optional)
        - status(optional)
        - is_cloned(optional)
        - created_by_profile(optional)
        - search(optional)
        - country(optional)
        - job_category(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized FormData model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FormData Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    # queryset = FormModel.FormData.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )
    # TODO: implement selection drop down
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="filter form_data by status",
        type=openapi.TYPE_STRING,
    )
    is_cloned = openapi.Parameter(
        "is_cloned",
        in_=openapi.IN_QUERY,
        description="filter form_data by is_cloned",
        type=openapi.TYPE_BOOLEAN,
    )
    employee_visibility = openapi.Parameter(
        "employee_visibility",
        in_=openapi.IN_QUERY,
        description="filter form_data by employee_visibility",
        type=openapi.TYPE_BOOLEAN,
    )
    candidate_visibility = openapi.Parameter(
        "candidate_visibility",
        in_=openapi.IN_QUERY,
        description="filter form_data by candidate_visibility",
        type=openapi.TYPE_BOOLEAN,
    )
    created_by_profile = openapi.Parameter(
        "created_by_profile",
        in_=openapi.IN_QUERY,
        description="filter form_data by created_by_profile",
        type=openapi.TYPE_INTEGER,
    )
    profile_id = openapi.Parameter(
        "profile_id",
        in_=openapi.IN_QUERY,
        description="filter form_data by created_by_profile",
        type=openapi.TYPE_STRING,
    )
    country = openapi.Parameter(
        "country",
        in_=openapi.IN_QUERY,
        description="filter form_data by country id",
        type=openapi.TYPE_STRING,
    )
    job_category = openapi.Parameter(
        "job_category",
        in_=openapi.IN_QUERY,
        description="filter form_data by job_category id",
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
    own_data = openapi.Parameter(
        "own_data",
        in_=openapi.IN_QUERY,
        description="filter on the basis of own_data",
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
            search,
            status,
            is_cloned,
            profile_id,
            employee_visibility,
            candidate_visibility,
            country,
            job_category,
            page,
            perpage,
            sort_dir,
            sort_field,
            own_data,
            export,
        ]
    )
    def get(self, request):
        # try:
        #     data = cache.get(request.get_full_path())
        # except:
        #     data = None
        # if data and request.GET.get("candidate_visibility") is not "true":
        #     return ResponseOk(
        #         {
        #             "data": data.get("data"),
        #             "meta": data.get("meta"),
        #         }
        #     )
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        status = data.get("status", "")

        is_cloned = data.get("is_cloned", "")

        profile_id = data.get("profile_id", "")
        try:
            profile_id = int(decrypt(profile_id))
        except:
            pass
        employee_visibility = data.get("employee_visibility", "")

        candidate_visibility = data.get("candidate_visibility", "")

        search = data.get("search", "")

        country = data.get("country", "")

        job_category = data.get("job_category", "")

        own_data = data.get("own_data", None)

        if data.get("export"):
            export = True
        else:
            export = False
        created_by_profile = None
        if data.get("created_by_profile"):
            created_by_profile = data.get("created_by_profile")
        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        form_data = FormModel.FormData.objects.filter(company__url_domain=url_domain)
        if request.user.user_role.name == "recruiter" and own_data == "false":
            if status:
                if status == "closed":
                    form_data = form_data.filter(status__in=["closed", "canceled"])
                else:
                    form_data = form_data.filter(status=status)
            if is_cloned == "true":
                form_data = form_data.filter(Q(is_cloned=True))

            if is_cloned == "false":
                form_data = form_data.filter(Q(is_cloned=False))

            if employee_visibility == "false":
                form_data = form_data.filter(Q(employee_visibility=False))

            if employee_visibility == "true":
                form_data = form_data.filter(Q(employee_visibility=True))

            if candidate_visibility == "false":
                form_data = form_data.filter(Q(candidate_visibility=False))

            if candidate_visibility == "true":
                form_data = form_data.filter(Q(candidate_visibility=True))
            if created_by_profile:
                form_data = form_data.filter(created_by_profile__id=int(created_by_profile))

            if country:
                form_data = form_data.filter(Q(form_data__country__id=int(country)))
            if job_category:
                form_data = form_data.filter(Q(form_data__job_category__id=int(job_category)))
                applied_forms = AppliedPosition.objects.filter(
                    form_data__in=form_data.values_list("id", flat=True), applied_profile__id=request.user.profile.id
                ).values_list("form_data__id", flat=True)
                form_data = form_data.exclude(id__in=applied_forms)
            if search:
                try:
                    form_data = form_data.filter(show_id=int(search))
                except:
                    form_data = search_data(form_data, FormData, search, ["form_data__job_title__icontains", "form_data__show_id"])
        else:
            if status:
                if status == "closed":
                    form_data = form_data.filter(status__in=["closed", "canceled"])
                else:
                    form_data = form_data.filter(status=status)

            if is_cloned == "true":
                form_data = form_data.filter(Q(is_cloned=True))

            if is_cloned == "false":
                form_data = form_data.filter(Q(is_cloned=False))

            if employee_visibility == "false":
                form_data = form_data.filter(Q(employee_visibility=False))

            if employee_visibility == "true":
                form_data = form_data.filter(Q(employee_visibility=True))

            if candidate_visibility == "false":
                form_data = form_data.filter(Q(candidate_visibility=False))

            if candidate_visibility == "true":
                form_data = form_data.filter(Q(candidate_visibility=True))
            if created_by_profile:
                form_data = form_data.filter(created_by_profile__id=int(created_by_profile))

            if country:
                form_data = form_data.filter(Q(form_data__country__id=int(country)))
            if job_category:
                form_data = form_data.filter(Q(form_data__job_category__id=int(job_category)))
                applied_forms = AppliedPosition.objects.filter(
                    form_data__in=form_data.values_list("id", flat=True), applied_profile__id=request.user.profile.id
                ).values_list("form_data__id", flat=True)
                form_data = form_data.exclude(id__in=applied_forms)
            if profile_id:
                try:
                    profile_id = int(decrypt(profile_id))
                except:
                    pass
                pro_obj = Profile.objects.get(id=profile_id)
                if own_data == "true":
                    result_list = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                    if status:
                        if status == "closed":
                            form_data = form_data.filter(status__in=["closed", "canceled"])
                        else:
                            form_data = form_data.filter(status=status)
                else:
                    temp_form_data = form_data
                    own_form_data = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                    teams_obj, created = Team.objects.get_or_create(manager=pro_obj)
                    members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
                    members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
                    result_list = members_fd_obj | own_form_data
                    if status:
                        if status == "closed":
                            form_data = form_data.filter(status__in=["closed", "canceled"])
                        else:
                            form_data = form_data.filter(status=status)
                if status:
                    if status == "closed":
                        form_data = form_data.filter(status__in=["closed", "canceled"])
                    else:
                        form_data = form_data.filter(status=status)
                form_data = sort_data(result_list, sort_field, sort_dir)
            if search:
                try:
                    form_data = form_data.filter(show_id=int(search))
                except:
                    form_data = search_data(
                        form_data,
                        FormData,
                        search,
                        ["form_data__job_title__icontains", "form_data__job_description__icontains", "form_data__show_id"],
                    )
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
            if selected_fields:
                selected_fields = selected_fields.first().selected_fields
            else:
                selected_fields = ["Hiring Manager", "Position No", "Job Title", "Country", "Candidates Applied", "Status"]
            writer.writerow(selected_fields)
            for data in form_data:
                serialized_data = FormSerializer.FormDataSerializer(data, context={"request": request}).data
                row = []
                for field in selected_fields:
                    if field in ["Department", "Category", "Location", "Job Title", "Country", "Level", "Employment Type"]:
                        field = form_utils.position_dict.get(field)
                        try:
                            value = data.form_data.get(field)[0].get("label")
                        except Exception as e:
                            print(e)
                            value = None
                    elif field == "Position Name":
                        value = data.form_data.get("job_title")
                    else:
                        field = form_utils.position_dict.get(field)
                        value = form_utils.get_value(serialized_data, field)
                    try:
                        row.append(next(value, None))
                    except:
                        row.append(value)
                writer.writerow(row)
            return csv_response
        else:
            if request.GET.get("is_applied") == "false" and request.user.is_authenticated:
                filtered_form_data = []
                for i in form_data:
                    queryset_object = FormModel.AppliedPosition.objects.filter(form_data=i.id, applied_profile=request.user.profile.id)
                    if not queryset_object:
                        filtered_form_data.append(i.id)
                form_data = FormData.objects.filter(id__in=filtered_form_data)
            else:
                form_data = form_data
            form_data = form_data.order_by("-id")
            pagination_data = paginate_data(request, form_data, FormModel.FormData)
            form_data = pagination_data.get("paginate_data")
            if form_data:
                serializer = FormSerializer.FormDataListSerializer(form_data, many=True, context={"request": request}).data
                resp = {
                    "data": serializer,
                    "meta": {
                        "page": pagination_data.get("page"),
                        "total_pages": pagination_data.get("total_pages"),
                        "perpage": pagination_data.get("perpage"),
                        "sort_dir": sort_field,
                        "sort_field": sort_field,
                        "total_records": pagination_data.get("total_records"),
                    },
                }
                # cache.set(request.get_full_path(), resp)
                return ResponseOk(resp)

        return ResponseBadRequest(
            {
                "data": None,
                "message": "FormData Does Not Exist",
            }
        )


class GetAllOpFormData(APIView):
    """
    This GET function fetches all records from FormData model accrding
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - page(optional)
        - status(optional)
        - is_cloned(optional)
        - created_by_profile(optional)
        - search(optional)
        - country(optional)
        - job_category(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized FormData model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FormData Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    # queryset = FormModel.FormData.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )
    # TODO: implement selection drop down
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="filter form_data by status",
        type=openapi.TYPE_STRING,
    )
    profile_id = openapi.Parameter(
        "profile_id",
        in_=openapi.IN_QUERY,
        description="filter form_data by created_by_profile",
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
    own_data = openapi.Parameter(
        "own_data",
        in_=openapi.IN_QUERY,
        description="filter on the basis of own_data",
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
            search,
            status,
            profile_id,
            page,
            perpage,
            sort_dir,
            sort_field,
            own_data,
            export,
        ]
    )
    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data and request.GET.get("candidate_visibility") is not "true":
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        status = data.get("status", "")

        profile_id = data.get("profile_id", "")

        search = data.get("search", "")

        own_data = data.get("own_data", None)

        if data.get("export"):
            export = True
        else:
            export = False
        created_by_profile = None
        if data.get("created_by_profile"):
            created_by_profile = data.get("created_by_profile")
        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        form_data = FormModel.FormData.objects.filter(company__url_domain=url_domain)
        if request.user.user_role.name == "recruiter" and own_data == "false":
            if status:
                if status == "closed":
                    form_data = form_data.filter(status__in=["closed", "canceled"])
                else:
                    form_data = form_data.filter(status=status)
            if search:
                try:
                    form_data = form_data.filter(show_id=int(search))
                except:
                    form_data = search_data(form_data, FormData, search, ["form_data__job_title__icontains", "form_data__show_id"])
        else:
            if status:
                if status == "closed":
                    form_data = form_data.filter(status__in=["closed", "canceled"])
                else:
                    form_data = form_data.filter(status=status)

            if profile_id:
                try:
                    profile_id = int(decrypt(profile_id))
                except:
                    pass
                pro_obj = Profile.objects.get(id=profile_id)
                if own_data == "true":
                    result_list = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                    if status:
                        if status == "closed":
                            form_data = form_data.filter(status__in=["closed", "canceled"])
                        else:
                            form_data = form_data.filter(status=status)
                else:
                    temp_form_data = form_data
                    own_form_data = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                    teams_obj, created = Team.objects.get_or_create(manager=pro_obj)
                    members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
                    members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
                    result_list = members_fd_obj | own_form_data
                    if status:
                        if status == "closed":
                            form_data = form_data.filter(status__in=["closed", "canceled"])
                        else:
                            form_data = form_data.filter(status=status)
                if status:
                    if status == "closed":
                        form_data = form_data.filter(status__in=["closed", "canceled"])
                    else:
                        form_data = form_data.filter(status=status)
                form_data = sort_data(result_list, sort_field, sort_dir)
            if search:
                try:
                    form_data = form_data.filter(show_id=int(search))
                except:
                    form_data = search_data(
                        form_data,
                        FormData,
                        search,
                        ["form_data__job_title__icontains", "form_data__job_description__icontains", "form_data__show_id"],
                    )
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            fields = ["Position No", "Position Name", "Recruiter", "Location", "Candidates Applied", "Status"]
            writer.writerow(fields)
            for i in form_data:
                row = []
                row.append(i.show_id)
                row.append(i.form_data["job_title"])
                try:
                    user_obj = User.objects.get(email__iexact=i.recruiter, user_company=i.company)
                    row.append(user_obj.get_full_name())
                except:
                    row.append(i.recruiter)
                row.append(i.form_data["location"][0]["label"])
                # get candidates applied
                row.append(AppliedPosition.objects.filter(form_data=i).count())
                row.append(i.status)
                writer.writerow(row)
            return csv_response
        else:
            pagination_data = paginate_data(request, form_data, FormModel.FormData)
            form_data = pagination_data.get("paginate_data")
            data = []
            if form_data:
                for i in form_data:
                    temp_data = {}
                    temp_data["id"] = i.id
                    temp_data["position_id"] = i.id
                    temp_data["sposition_id"] = i.show_id
                    temp_data["position_no"] = i.id
                    temp_data["position_name"] = i.form_data["job_title"]
                    try:
                        user_obj = User.objects.get(email__iexact=i.recruiter, user_company=i.company)
                        temp_data["recruiter"] = user_obj.get_full_name()
                    except:
                        temp_data["recruiter"] = i.recruiter
                    try:
                        user_obj = User.objects.get(email__iexact=i.hiring_manager, user_company=i.company)
                        temp_data["hiring_manager"] = user_obj.get_full_name()
                    except:
                        temp_data["hiring_manager"] = i.hiring_manager
                    temp_data["status"] = i.status
                    temp_data["candidates_applied"] = AppliedPosition.objects.filter(form_data=i).count()
                    temp_data["location"] = i.form_data["location"][0]["label"]
                    try:
                        hire_obj = AppliedPosition.objects.filter(form_data=i, application_status="hired")
                        if hire_obj:
                            offer_obj = OfferLetter.objects.filter(offered_to=hire_obj[0])
                            if offer_obj:
                                temp_data["candidate_name"] = offer_obj[0].offered_to.applied_profile.user.get_full_name()
                        else:
                            temp_data["candidate_name"] = None
                    except:
                        temp_data["candidate_name"] = None
                    data.append(temp_data)
                resp = {
                    "data": data,
                    "meta": {
                        "page": pagination_data.get("page"),
                        "total_pages": pagination_data.get("total_pages"),
                        "perpage": pagination_data.get("perpage"),
                        "sort_dir": sort_field,
                        "sort_field": sort_field,
                        "total_records": pagination_data.get("total_records"),
                    },
                }
                cache.set(request.get_full_path(), resp)
                return ResponseOk(resp)

        return ResponseBadRequest(
            {
                "data": None,
                "message": "FormData Does Not Exist",
            }
        )


class GetAllOpPendingFormData(APIView):
    """
    This GET function fetches all records from FormData model accrding
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - page(optional)
        - status(optional)
        - search(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized FormData model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FormData Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    # queryset = FormModel.FormData.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )
    # TODO: implement selection drop down
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="filter form_data by status",
        type=openapi.TYPE_STRING,
    )
    profile_id = openapi.Parameter(
        "profile_id",
        in_=openapi.IN_QUERY,
        description="filter form_data by created_by_profile",
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
    own_data = openapi.Parameter(
        "own_data",
        in_=openapi.IN_QUERY,
        description="filter on the basis of own_data",
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
            search,
            status,
            profile_id,
            page,
            perpage,
            sort_dir,
            sort_field,
            own_data,
            export,
        ]
    )
    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data and request.GET.get("candidate_visibility") is not "true":
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        status = data.get("status", "")

        profile_id = data.get("profile_id", "")

        search = data.get("search", "")

        own_data = data.get("own_data", None)

        if data.get("export"):
            export = True
        else:
            export = False
        created_by_profile = None
        if data.get("created_by_profile"):
            created_by_profile = data.get("created_by_profile")
        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        form_data = FormModel.FormData.objects.filter(company__url_domain=url_domain)
        if request.user.user_role.name == "recruiter" and own_data == "false":
            if status:
                if status == "closed":
                    form_data = form_data.filter(status__in=["closed", "canceled"])
                else:
                    form_data = form_data.filter(status=status)
            if created_by_profile:
                form_data = form_data.filter(created_by_profile__id=int(created_by_profile))

            if search:
                try:
                    form_data = form_data.filter(show_id=int(search))
                except:
                    form_data = search_data(form_data, FormData, search, ["form_data__job_title__icontains", "form_data__show_id"])
        else:
            if status:
                if status == "closed":
                    form_data = form_data.filter(status__in=["closed", "canceled"])
                else:
                    form_data = form_data.filter(status=status)

            if created_by_profile:
                form_data = form_data.filter(created_by_profile__id=int(created_by_profile))

            if profile_id:
                try:
                    profile_id = int(decrypt(profile_id))
                except:
                    pass
                pro_obj = Profile.objects.get(id=profile_id)
                if own_data == "true":
                    result_list = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                    if status:
                        if status == "closed":
                            form_data = form_data.filter(status__in=["closed", "canceled"])
                        else:
                            form_data = form_data.filter(status=status)
                else:
                    temp_form_data = form_data
                    own_form_data = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                    teams_obj, created = Team.objects.get_or_create(manager=pro_obj)
                    members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
                    members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
                    result_list = members_fd_obj | own_form_data
                    if status:
                        if status == "closed":
                            form_data = form_data.filter(status__in=["closed", "canceled"])
                        else:
                            form_data = form_data.filter(status=status)
                if status:
                    if status == "closed":
                        form_data = form_data.filter(status__in=["closed", "canceled"])
                    else:
                        form_data = form_data.filter(status=status)
                form_data = sort_data(result_list, sort_field, sort_dir)
            if search:
                try:
                    form_data = form_data.filter(show_id=int(search))
                except:
                    form_data = search_data(
                        form_data,
                        FormData,
                        search,
                        ["form_data__job_title__icontains", "form_data__job_description__icontains", "form_data__show_id"],
                    )
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            fields = ["Position No", "Position Name", "Recruiter", "Location", "Current Approvers", "Status"]
            writer.writerow(fields)
            for i in form_data:
                row = []
                row.append(i.show_id)
                row.append(i.form_data["job_title"])
                try:
                    user_obj = User.objects.get(email__iexact=i.recruiter, user_company=i.company)
                    row.append(user_obj.get_full_name())
                except:
                    row.append(i.recruiter)
                row.append(i.form_data["location"][0]["label"])
                # get current approvers
                row.append(PositionApproval.objects.filter(position=i).values_list("profile__user__first_name", flat=True))
                row.append(i.status)
                writer.writerow(row)
            return csv_response
        else:
            pagination_data = paginate_data(request, form_data, FormModel.FormData)
            form_data = pagination_data.get("paginate_data")
            data = []
            if form_data:
                for i in form_data:
                    temp_data = {}
                    temp_data["id"] = i.id
                    temp_data["position_no"] = i.id
                    temp_data["sposition_id"] = i.show_id
                    temp_data["position_name"] = i.form_data["job_title"]
                    try:
                        user_obj = User.objects.get(email__iexact=i.hiring_manager, user_company=i.company)
                        temp_data["hiring_manager"] = user_obj.get_full_name()
                    except:
                        temp_data["hiring_manager"] = i.hiring_manager
                    try:
                        user_obj = User.objects.get(email__iexact=i.recruiter, user_company=i.company)
                        temp_data["recruiter"] = user_obj.get_full_name()
                    except:
                        temp_data["recruiter"] = i.recruiter
                    temp_data["status"] = i.status
                    temp_data["candidates_applied"] = AppliedPosition.objects.filter(form_data=i).count()
                    temp_data["location"] = i.form_data["location"][0]["label"]
                    temp_data["current_approvals"] = []
                    for pa in PositionApproval.objects.filter(position=i).order_by("sort_order"):
                        t_data = {}
                        t_data["approval_name"] = pa.profile.user.get_full_name()
                        t_data["is_approve"] = pa.is_approve
                        t_data["is_reject"] = pa.is_reject
                        t_data["profile_id"] = encrypt(pa.profile.id)
                        t_data["position"] = pa.position.id
                        t_data["id"] = pa.id
                        temp_data["current_approvals"].append(t_data)
                    data.append(temp_data)
                resp = {
                    "data": data,
                    "meta": {
                        "page": pagination_data.get("page"),
                        "total_pages": pagination_data.get("total_pages"),
                        "perpage": pagination_data.get("perpage"),
                        "sort_dir": sort_field,
                        "sort_field": sort_field,
                        "total_records": pagination_data.get("total_records"),
                    },
                }
                cache.set(request.get_full_path(), resp)
                return ResponseOk(resp)

        return ResponseBadRequest(
            {
                "data": None,
                "message": "FormData Does Not Exist",
            }
        )


class GetAllJobBoard(APIView):
    """
    This GET function fetches all records from FormData model accrding
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - page(optional)
        - status(optional)
        - is_cloned(optional)
        - created_by_profile(optional)
        - search(optional)
        - country(optional)
        - job_category(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized FormData model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FormData Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    # queryset = FormModel.FormData.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )
    # TODO: implement selection drop down
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="filter form_data by status",
        type=openapi.TYPE_STRING,
    )
    employee_visibility = openapi.Parameter(
        "employee_visibility",
        in_=openapi.IN_QUERY,
        description="filter form_data by employee_visibility",
        type=openapi.TYPE_BOOLEAN,
    )
    candidate_visibility = openapi.Parameter(
        "candidate_visibility",
        in_=openapi.IN_QUERY,
        description="filter form_data by candidate_visibility",
        type=openapi.TYPE_BOOLEAN,
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
    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export data or not",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            status,
            employee_visibility,
            candidate_visibility,
            page,
            perpage,
            export,
        ]
    )
    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data and request.GET.get("candidate_visibility") is not "true":
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        status = data.get("status", "")

        employee_visibility = data.get("employee_visibility", "")

        candidate_visibility = data.get("candidate_visibility", "")

        search = data.get("search", "")

        if data.get("export"):
            export = True
        else:
            export = False

        form_data = FormModel.FormData.objects.filter(company__url_domain=url_domain)

        if status:
            form_data = form_data.filter(status=status)

        if employee_visibility == "false":
            form_data = form_data.filter(Q(employee_visibility=False))

        if employee_visibility == "true":
            form_data = form_data.filter(Q(employee_visibility=True))

        if candidate_visibility == "false":
            form_data = form_data.filter(Q(candidate_visibility=False))

        if candidate_visibility == "true":
            form_data = form_data.filter(Q(candidate_visibility=True))

        if search:
            try:
                form_data = form_data.filter(show_id=int(search))
            except:
                form_data = search_data(
                    form_data,
                    FormData,
                    search,
                    [
                        "form_data__job_title__icontains",
                        "form_data__job_description__icontains",
                        "form_data__show_id",
                        "form_data__location__0__label__icontains",
                    ],
                )
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            fields = ["Position No", "Position Name", "Candidates Applied", "Location", "Status"]
            writer.writerow(fields)
            for data in form_data:
                row = []
                row.append(i.show_id)
                row.append(i.form_data["job_title"])
                row.append(AppliedPosition.objects.filter(form_data=i).count())
                row.append(i.form_data["location"][0]["label"])
                row.append(i.status)
                writer.writerow(row)
            return csv_response
        else:
            pagination_data = paginate_data(request, form_data, FormModel.FormData)
            form_data = pagination_data.get("paginate_data")
            if form_data:
                resp_data = []
                for i in form_data:
                    temp_data = {}
                    temp_data["id"] = i.id
                    temp_data["position_no"] = i.id
                    temp_data["sposition_id"] = i.show_id
                    temp_data["position_name"] = i.form_data["job_title"]
                    temp_data["candidates_applied"] = AppliedPosition.objects.filter(form_data=i).count()
                    temp_data["location"] = i.form_data["location"][0]["label"]
                    temp_data["status"] = i.status
                    resp_data.append(temp_data)
                resp = {
                    "data": resp_data,
                    "meta": {
                        "page": pagination_data.get("page"),
                        "total_pages": pagination_data.get("total_pages"),
                        "perpage": pagination_data.get("perpage"),
                        "total_records": pagination_data.get("total_records"),
                    },
                }
                cache.set(request.get_full_path(), resp)
                return ResponseOk(resp)

        return ResponseBadRequest(
            {
                "data": None,
                "message": "FormData Does Not Exist",
            }
        )


class GetAllOpJobPosting(APIView):
    """
    This GET function fetches all records from FormData model accrding
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - page(optional)
        - status(optional)
        - is_cloned(optional)
        - created_by_profile(optional)
        - search(optional)
        - country(optional)
        - job_category(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized FormData model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FormData Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    # queryset = FormModel.FormData.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )
    # TODO: implement selection drop down
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="filter form_data by status",
        type=openapi.TYPE_STRING,
    )
    profile_id = openapi.Parameter(
        "profile_id",
        in_=openapi.IN_QUERY,
        description="filter form_data by created_by_profile",
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
    own_data = openapi.Parameter(
        "own_data",
        in_=openapi.IN_QUERY,
        description="filter on the basis of own_data",
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
            search,
            status,
            profile_id,
            page,
            perpage,
            sort_dir,
            sort_field,
            own_data,
            export,
        ]
    )
    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data and request.GET.get("candidate_visibility") is not "true":
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        status = data.get("status", "")

        profile_id = data.get("profile_id", "")

        search = data.get("search", "")

        own_data = data.get("own_data", None)

        if data.get("export"):
            export = True
        else:
            export = False
        created_by_profile = None
        if data.get("created_by_profile"):
            created_by_profile = data.get("created_by_profile")
        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        form_data = FormModel.FormData.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
        if request.user.user_role.name == "recruiter" and own_data == "false":
            if status:
                if status == "closed":
                    form_data = form_data.filter(status__in=["closed", "canceled"])
                else:
                    form_data = form_data.filter(status=status)
            if search:
                try:
                    form_data = form_data.filter(show_id=int(search))
                except:
                    form_data = search_data(form_data, FormData, search, ["form_data__job_title__icontains", "form_data__show_id"])
        else:
            if status:
                if status == "closed":
                    form_data = form_data.filter(status__in=["closed", "canceled"])
                else:
                    form_data = form_data.filter(status=status)

            if profile_id:
                try:
                    profile_id = int(decrypt(profile_id))
                except:
                    pass
                pro_obj = Profile.objects.get(id=profile_id)
                if own_data == "true":
                    result_list = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                    if status:
                        if status == "closed":
                            form_data = form_data.filter(status__in=["closed", "canceled"])
                        else:
                            form_data = form_data.filter(status=status)
                else:
                    temp_form_data = form_data
                    own_form_data = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                    teams_obj, created = Team.objects.get_or_create(manager=pro_obj)
                    members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
                    members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
                    result_list = members_fd_obj | own_form_data
                    if status:
                        if status == "closed":
                            form_data = form_data.filter(status__in=["closed", "canceled"])
                        else:
                            form_data = form_data.filter(status=status)
                if status:
                    if status == "closed":
                        form_data = form_data.filter(status__in=["closed", "canceled"])
                    else:
                        form_data = form_data.filter(status=status)
                form_data = sort_data(result_list, sort_field, sort_dir)
            if search:
                try:
                    form_data = form_data.filter(show_id=int(search))
                except:
                    form_data = search_data(
                        form_data,
                        FormData,
                        search,
                        ["form_data__job_title__icontains", "form_data__job_description__icontains", "form_data__show_id"],
                    )
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            fields = ["Position No", "Position Name", "Location", "External Link", "Internal Link", "JD URL"]
            writer.writerow(fields)
            for i in form_data:
                row = []
                row.append(i.show_id)
                row.append(i.form_data["job_title"])
                row.append(i.form_data["location"][0]["label"])
                row.append(form_utils.get_candidate_visibility_link(i))
                row.append(form_utils.get_employee_visibility_link(i))
                if i.job_description:
                    row.append(i.job_description.url)
                else:
                    row.append(None)
                writer.writerow(row)
            return csv_response
        else:
            pagination_data = paginate_data(request, form_data, FormModel.FormData)
            form_data = pagination_data.get("paginate_data")
            data = []
            if form_data:
                for i in form_data:
                    temp_data = {}
                    temp_data["id"] = i.id
                    temp_data["position_no"] = i.id
                    temp_data["sposition_id"] = i.show_id
                    temp_data["position_name"] = i.form_data["job_title"]
                    temp_data["location"] = i.form_data["location"][0]["label"]
                    temp_data["candidate_visibility_link"] = form_utils.get_candidate_visibility_link(i)
                    temp_data["employee_visibility_link"] = form_utils.get_employee_visibility_link(i)
                    temp_data["candidate_visibility"] = i.candidate_visibility
                    temp_data["employee_visibility"] = i.employee_visibility
                    try:
                        user_obj = User.objects.get(email__iexact=i.hiring_manager, user_company=i.company)
                        temp_data["hiring_manager"] = user_obj.get_full_name()
                    except:
                        temp_data["hiring_manager"] = i.hiring_manager
                    try:
                        user_obj = User.objects.get(email__iexact=i.recruiter, user_company=i.company)
                        temp_data["recruiter"] = user_obj.get_full_name()
                    except:
                        temp_data["recruiter"] = i.recruiter
                    if i.job_description:
                        temp_data["jd_video"] = i.job_description.url
                    else:
                        temp_data["jd_video"] = None
                    data.append(temp_data)
                resp = {
                    "data": data,
                    "meta": {
                        "page": pagination_data.get("page"),
                        "total_pages": pagination_data.get("total_pages"),
                        "perpage": pagination_data.get("perpage"),
                        "sort_dir": sort_field,
                        "sort_field": sort_field,
                        "total_records": pagination_data.get("total_records"),
                    },
                }
                cache.set(request.get_full_path(), resp)
                return ResponseOk(resp)

        return ResponseBadRequest(
            {
                "data": None,
                "message": "FormData Does Not Exist",
            }
        )


class GetAllFormDataGuest(APIView):
    """
    This GET function fetches all records from FormData model accrding
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - page(optional)
        - status(optional)
        - is_cloned(optional)
        - created_by_profile(optional)
        - search(optional)
        - country(optional)
        - job_category(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized FormData model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FormData Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    authentication_classes = []
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )
    # TODO: implement selection drop down
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="filter form_data by status",
        type=openapi.TYPE_STRING,
    )
    is_cloned = openapi.Parameter(
        "is_cloned",
        in_=openapi.IN_QUERY,
        description="filter form_data by is_cloned",
        type=openapi.TYPE_BOOLEAN,
    )
    employee_visibility = openapi.Parameter(
        "employee_visibility",
        in_=openapi.IN_QUERY,
        description="filter form_data by employee_visibility",
        type=openapi.TYPE_BOOLEAN,
    )
    candidate_visibility = openapi.Parameter(
        "candidate_visibility",
        in_=openapi.IN_QUERY,
        description="filter form_data by candidate_visibility",
        type=openapi.TYPE_BOOLEAN,
    )

    created_by_profile = openapi.Parameter(
        "created_by_profile",
        in_=openapi.IN_QUERY,
        description="filter form_data by created_by_profile",
        type=openapi.TYPE_STRING,
    )
    country = openapi.Parameter(
        "country",
        in_=openapi.IN_QUERY,
        description="filter form_data by country id",
        type=openapi.TYPE_STRING,
    )
    job_category = openapi.Parameter(
        "job_category",
        in_=openapi.IN_QUERY,
        description="filter form_data by job_category id",
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
            status,
            is_cloned,
            created_by_profile,
            employee_visibility,
            candidate_visibility,
            country,
            job_category,
            page,
            perpage,
            sort_dir,
            sort_field,
        ]
    )
    def get(self, request):
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        page = data.get("page", 1)

        status = data.get("status", "")

        is_cloned = data.get("is_cloned", "")

        created_by_profile = data.get("created_by_profile", "")

        employee_visibility = data.get("employee_visibility", "")

        candidate_visibility = data.get("candidate_visibility", "")

        search = data.get("search", "")

        country = data.get("country", "")

        job_category = data.get("job_category", "")

        limit = data.get("perpage", settings.PAGE_SIZE)

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        try:
            form_data = FormModel.FormData.objects.filter(company__url_domain=url_domain)

            if status:
                form_data = form_data.filter(Q(status=status))

            if is_cloned == "true":
                form_data = form_data.filter(Q(is_cloned=True))

            if is_cloned == "false":
                form_data = form_data.filter(Q(is_cloned=False))

            if employee_visibility == "false":
                form_data = form_data.filter(Q(employee_visibility=False))

            if employee_visibility == "true":
                form_data = form_data.filter(Q(employee_visibility=True))

            if candidate_visibility == "false":
                form_data = form_data.filter(Q(candidate_visibility=False))

            if candidate_visibility == "true":
                form_data = form_data.filter(Q(candidate_visibility=True))

            if country:
                form_data = form_data.filter(Q(form_data__country__id=int(country)))
            if job_category:
                form_data = form_data.filter(Q(form_data__job_category__id=int(job_category)))
            if created_by_profile:
                form_data = form_data.filter(Q(created_by_profile=created_by_profile))
            if search:
                form_data = form_data.filter(Q(form_data__icontains=search)).distinct()

            count = form_data.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        form_data = form_data.order_by("created_at")
                    elif sort_field == "updated_at":
                        form_data = form_data.order_by("updated_at")
                    elif sort_field == "id":
                        form_data = form_data.order_by("id")

                    else:
                        form_data = form_data.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        form_data = form_data.order_by("-created_at")
                    elif sort_field == "updated_at":
                        form_data = form_data.order_by("-updated_at")
                    elif sort_field == "id":
                        form_data = form_data.order_by("-id")

                    else:
                        form_data = form_data.order_by("-id")
            else:
                form_data = form_data.order_by("-id")

            if page and limit:
                form_data = form_data[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if form_data:
                serializer = FormSerializer.FormDataListSerializer(form_data, many=True, context={"request": request}).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "message": "FormData Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetFormData(APIView):
    """
    This GET function fetches particular Form Data model instance by ID,
    and return it after serializing it.

    Args:
        pk(form_data_id)
    Body:
        None
    Returns:
        - Serialized Form Data model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) form_data Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            form_data = custom_get_object(pk, FormModel.FormData)
            serializer = FormSerializer.FormDataListSerializer(form_data, context={"request": request})
            data = serializer.data
            if AppliedPosition.objects.filter(form_data=form_data, application_status__in=["offer", "pending-offer", "approved"]):
                data["in_offer"] = True
            else:
                data["in_offer"] = False
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "get FormData successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": 400,
                    "message": " FormData Not Exist",
                }
            )


class CreateFormData(APIView):
    """
    This POST function creates a Form Data Model record from the data passed in the body.

    Args:
        None
    Body:
        Form Data model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="FormData Create API",
        operation_summary="FormData Create API",
        request_body=FormSerializer.FormDataSerializer,
    )
    def post(self, request):
        data = request.data
        data["created_by_profile"] = request.user.profile.id
        serializer = FormSerializer.FormDataSerializer(data=data)
        if serializer.is_valid():
            form_data_obj = serializer.save()
            history = form_data_obj.form_data.get("history", [])
            history.append(
                {"status": "draft", "date": date.today().strftime("%d %B, %Y"), "reason": "created", "changed_by": request.user.profile.id}
            )
            form_data_obj.form_data["history"] = history
            try:
                form_obj = Profile.objects.filter(id=serializer["created_by_profile"])
                data = {"user": request.user.id, "description": "{} Created a Job".format(form_obj.user.first_name), "type_id": 3}
                create_activity_log(data)
            except:
                pass
            # Create Default Stages
            count = 0
            # Default stages
            # stages = ["Resume Review", "Hiring Manager Review", "Offer", "Hired", "Background Check", "Document Check"]
            stages = Stage.objects.filter(company=form_data_obj.company, pipeline__pipeline_name="Hiring Stage").order_by("sort_order")
            stage_create = None
            for stage_obj in stages:
                try:
                    PositionStage.objects.create(position=form_data_obj, stage=stage_obj, sort_order=count, company=form_data_obj.company)
                    count += 1
                except Exception as e:
                    stage_create = str(e)
            data = serializer.data
            data["stage_create"] = stage_create
            form_data_obj.history = [{"date": str(datetime.datetime.now()), "status": "draft"}]
            form_data_obj.save()
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "FormData created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "FormData is not valid",
                }
            )


class UpdateFormData(APIView):
    """
    This PUT function updates a Form Data Model record according to the form_data_id passed in url.

    Args:
        pk(form_data_id)
    Body:
        Form Data Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) form_data does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="FormData update API",
        operation_summary="FormData update API",
        request_body=FormSerializer.FormDataSerializer
        # request_body=openapi.Schema(
        #     type=openapi.TYPE_OBJECT,
        #     properties={
        #         "form": openapi.Schema(type=openapi.TYPE_INTEGER),
        #         "company": openapi.Schema(type=openapi.TYPE_INTEGER),
        #         "form_data": openapi.Schema(
        #             type=openapi.TYPE_STRING,
        #             description="enter formdata as json example {'abc':'xyz'}",
        #         ),
        #         "profile": openapi.Schema(type=openapi.TYPE_INTEGER),
        #     },
        # ),
    )
    def put(self, request, pk):
        try:
            data = request.data
            form_data = custom_get_object(pk, FormModel.FormData)
            prev_status = None
            if form_data.status == data.get("status"):
                pass
            else:
                prev_status = form_data.status
            serializer = FormSerializer.FormDataSerializer(form_data, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Create link for candidate visibility if true
                candidate_visibility = data.get("candidate_visibility")
                if candidate_visibility is True:
                    domain_name = data.get("domain_name")
                    complete_url = "{}/guest/search-job-description/{}/".format(domain_name, form_data.id)
                    try:
                        url_obj = ShortURL.objects.filter(long_url=complete_url, internal=False)[0]
                    except:
                        short_url_tag = url_shortner_utils.short_url()
                        short_url = "{}/job/{}".format(domain_name, short_url_tag)
                        url_obj = ShortURL.objects.create(long_url=complete_url, short_url=short_url, internal=False)
                # create link for employee visibility if true
                employee_visibility = data.get("employee_visibility")
                if employee_visibility is True:
                    domain_name = data.get("domain_name")
                    complete_url = "{}/internal/internal-search-job-description/{}/".format(domain_name, form_data.id)
                    try:
                        url_obj = ShortURL.objects.filter(long_url=complete_url, internal=True)[0]
                    except:
                        short_url_tag = url_shortner_utils.short_url()
                        short_url = "{}/job/{}".format(domain_name, short_url_tag)
                        url_obj = ShortURL.objects.create(long_url=complete_url, short_url=short_url, internal=True)
                # Add history
                if prev_status:
                    history = form_data.form_data.get("history", [])
                    history.append(
                        {
                            "status": data.get("status"),
                            "date": date.today().strftime("%d %B, %Y"),
                            "reason": data.get("reason", None),
                            "changed_by": request.user.profile.id,
                        }
                    )
                    form_data.form_data["history"] = history
                    if request.data.get("status"):
                        form_data.history.append({"date": str(datetime.datetime.now().date()), "status": request.data.get("status")})

                    form_data.save()
                try:
                    form_obj = Profile.objects.filter(id=serializer["created_by_profile"])
                    data = {"user": request.user.id, "description": "{} Updated This Job".format(form_obj.user.first_name), "type_id": 3}
                    create_activity_log(data)
                except:
                    pass
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "FormData updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "FormData Not valid",
                    }
                )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "FormData Does Not Exist",
                }
            )


class AddJDFormData(APIView):
    def put(self, request, pk):
        try:
            data = request.data
            form_data = custom_get_object(pk, FormModel.FormData)
            prev_status = None
            if form_data.status == data.get("status"):
                pass
            else:
                prev_status = form_data.status
            try:
                form_data.job_description = request.FILES["jd"]
                form_data.save()
                form_obj = Profile.objects.filter(id=form_data.created_by_profile.id)
                data = {"user": request.user.id, "description": "{} Updated This Job".format(form_obj.user.first_name), "type_id": 3}
                create_activity_log(data)
            except:
                pass
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "FormData updated successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "FormData Does Not Exist",
                }
            )


class DeleteFormData(APIView):
    """
    This DELETE function Deletes a Form Data Model record accroding to the _id passed in url.

    Args:
        pk(form_data_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Form Data does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            form_data = custom_get_object(pk, FormModel.FormData)
            # form_data.score_card_position_attribute.all().delete()
            form_data.status = "canceled"
            form_data.save()
            # Send email to candidate
            context = {"company": form_data.company.company_name, "position": form_data.form_data["job_title"], "name": request.user.get_full_name()}
            body_msg = render_to_string("position_closed.html", context)
            emails = []
            if request.GET.get("rejection") == "true":
                objs = AppliedPosition.objects.filter(form_data=form_data)
                for i in objs:
                    emails.append(i.applied_profile.user.email)
                    i.application_status = "reject"
                    i.rejection_mail_sent = True
                    i.save()

            msg = EmailMultiAlternatives(
                "Position Closed - Thank You for Your Interest!",
                body_msg,
                "Position Closed - Thank You for Your Interest!",
                emails,
            )
            msg.content_subtype = "html"
            msg.send()
            form_data.history.append({"date": str(datetime.datetime.now().date()), "status": "canceled"})
            form_data.save()
            try:
                data = {"user": request.user.id, "description": "You Deleted a Job", "type_id": 3}
                create_activity_log(data)
            except:
                pass
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "FormData deleted Successfully",
                }
            )
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "FormData Does Not Exist",
                }
            )


class GetAllPositionApproval(APIView):
    """
    This GET function fetches all records from Position Approval model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - position(mandatory)
        - domain(mandatory)

    Returns:
        - Serialized Position Approval model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Position Approval Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.PositionApproval.objects.all()

    position = openapi.Parameter(
        "position",
        in_=openapi.IN_QUERY,
        description="enter position id",
        type=openapi.TYPE_STRING,
    )
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="enter profile id",
        type=openapi.TYPE_STRING,
    )
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="enter profile id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[position, profile, search])
    def get(self, request):
        data = request.GET
        position = data.get("position")
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        if data.get("is_approved") is not None:
            is_approve = data.get("is_approved")
            if is_approve == "all":
                is_approve = None
            elif is_approve == "true":
                is_approve = True
            else:
                is_approve = False
        else:
            is_approve = None
        if data.get("export"):
            export = True
        else:
            export = False
        profile = data.get("profile")
        try:
            profile = int(decrypt(profile))
        except:
            pass
        search = data.get("search", "")
        try:
            queryset_data = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None)).order_by("position", "sort_order")
            # queryset_data = queryset_data.filter(profile__user__id = request.user.id)
            if position:
                queryset_data = queryset_data.filter(position__id=int(position))
            if profile:
                queryset_data = queryset_data.filter(profile=profile)
            if is_approve:
                queryset_data = queryset_data.filter(is_approve=is_approve)
            elif is_approve is False:
                queryset_data = queryset_data.filter(is_approve=False).exclude(show=False)
            if search:
                queryset_data = queryset_data.annotate(
                    full_name=Concat("profile__user__first_name", V(" "), "profile__user__last_name"),
                    string_id=Cast("position__show_id", output_field=CharField(max_length=256)),
                ).filter(Q(full_name__icontains=search) | Q(position__form_data__job_title__icontains=search) | Q(string_id__icontains=search))
            if "type" in data and "activity" == data.get("type"):
                queryset = []
                for query in queryset_data:
                    if OfferLetter.objects.filter(offered_to__form_data=query.position).exclude(Q(is_decline=True) | Q(withdraw=True)):
                        queryset.append(query)
                queryset_data = queryset
            if "type" in data and "allPending" == data.get("type"):
                queryset_data = (
                    queryset_data.filter(Q(position__recruiter=request.user.email) | Q(position__hiring_manager=request.user.email))
                    .exclude(Q(is_approve=True) | Q(is_reject=True))
                    .order_by("position", "sort_order")
                    .distinct("position")
                )
            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                if selected_fields:
                    selected_fields = selected_fields.first().selected_fields
                else:
                    selected_fields = ["Hiring Manager", "Position No", "Job Title", "Country", "Candidates Applied", "Status"]
                writer.writerow(selected_fields)

                for data in queryset_data:
                    serializer_data = FormSerializer.PositionApprovalListSerializer(data).data
                    row = []
                    for field in selected_fields:
                        if field.lower() in ["department", "category", "location", "country", "level", "employment type"]:
                            field = form_utils.position_dict.get(field)
                            try:
                                value = data.position.form_data.get(field)[0].get("label")
                                if value is None:
                                    value = data.position.form_data.get(field).get("name")
                            except Exception as e:
                                print(e)
                                value = None
                        elif field in ["Position Name", "Job Title"]:
                            value = data.position.form_data.get("job_title")
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
                serializer = FormSerializer.PositionApprovalListSerializer(queryset_data, many=True)
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "positions list ",
                    }
                )
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "form does not exist",
                }
            )


class GetAllOpPositionApproval(APIView):
    """
    This GET function fetches all records from Position Approval model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - position(mandatory)
        - domain(mandatory)

    Returns:
        - Serialized Position Approval model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Position Approval Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.PositionApproval.objects.all()

    position = openapi.Parameter(
        "position",
        in_=openapi.IN_QUERY,
        description="enter position id",
        type=openapi.TYPE_STRING,
    )
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="enter profile id",
        type=openapi.TYPE_STRING,
    )
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[position, profile, search])
    def get(self, request):
        data = request.GET
        position = data.get("position")
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        if data.get("is_approved") is not None:
            is_approve = data.get("is_approved")
            if is_approve == "all":
                is_approve = None
            elif is_approve == "true":
                is_approve = True
            else:
                is_approve = False
        else:
            is_approve = None
        if data.get("export"):
            export = True
        else:
            export = False
        profile = data.get("profile")
        try:
            profile = int(decrypt(profile))
        except:
            pass
        search = data.get("search", "")
        try:
            queryset_data = self.queryset.all().filter(company__url_domain=url_domain).order_by("position", "sort_order")
            # queryset_data = queryset_data.filter(profile__user__id = request.user.id)
            if position:
                queryset_data = queryset_data.filter(position__id=int(position))
            if profile:
                queryset_data = queryset_data.filter(profile=profile)
            if is_approve:
                queryset_data = queryset_data.filter(is_approve=is_approve)
            elif is_approve is False:
                queryset_data = queryset_data.filter(is_approve=False).exclude(show=False)
            if search:
                queryset_data = queryset_data.annotate(
                    full_name=Concat("profile__user__first_name", V(" "), "profile__user__last_name"),
                    string_id=Cast("position__show_id", output_field=CharField(max_length=256)),
                ).filter(Q(full_name__icontains=search) | Q(position__form_data__job_title__icontains=search) | Q(string_id__icontains=search))
            if "type" in data and "activity" == data.get("type"):
                queryset = []
                for query in queryset_data:
                    if OfferLetter.objects.filter(offered_to__form_data=query.position).exclude(Q(is_decline=True) | Q(withdraw=True)):
                        queryset.append(query)
                queryset_data = queryset
            if "type" in data and "allPending" == data.get("type"):
                queryset_data = (
                    queryset_data.filter(Q(position__recruiter=request.user.email) | Q(position__hiring_manager=request.user.email))
                    .exclude(Q(is_approve=True) | Q(is_reject=True))
                    .order_by("position", "sort_order")
                    .distinct("position")
                )
            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                fields = ["Position No", "Position Name", "Hiring Manager", "Recruiter", "Location", "Department"]
                writer.writerow(fields)

                for i in queryset_data:
                    row = []
                    row.append(i.position.show_id)
                    row.append(i.position.form_data["job_title"])
                    try:
                        user_obj = User.objects.get(email__iexact=i.position.hiring_manager, user_company=i.position.company)
                        row.append(user_obj.get_full_name())
                    except:
                        row.append(i.position.hiring_manager)
                    try:
                        user_obj = User.objects.get(email__iexact=i.position.recruiter, user_company=i.position.company)
                        row.append(user_obj.get_full_name())
                    except:
                        row.append(i.position.recruiter)
                    row.append(i.position.form_data["location"][0]["label"])
                    try:
                        row.append(i.position.form_data["departments"][0]["label"])
                    except:
                        row.append(i.position.form_data.get("department", [{}])[0].get("label"))
                    writer.writerow(row)
                response = HttpResponse(csv_response, content_type="text/csv")
                return response
            else:
                data = []
                for i in queryset_data:
                    temp_data = {}
                    temp_data["id"] = i.id
                    temp_data["position_id"] = i.position.id
                    temp_data["sposition_id"] = i.position.show_id
                    temp_data["position_name"] = i.position.form_data["job_title"]
                    try:
                        user_obj = User.objects.get(email__iexact=i.position.hiring_manager, user_company=i.position.company)
                        temp_data["hiring_manager"] = user_obj.get_full_name()
                    except:
                        temp_data["hiring_manager"] = i.position.hiring_manager
                    try:
                        user_obj = User.objects.get(email__iexact=i.position.recruiter, user_company=i.position.company)
                        temp_data["recruiter"] = user_obj.get_full_name()
                    except:
                        temp_data["recruiter"] = i.position.recruiter
                    temp_data["location"] = i.position.form_data["location"][0]["label"]
                    try:
                        temp_data["department"] = i.position.form_data["departments"][0]["label"]
                    except:
                        temp_data["department"] = i.position.form_data.get("department", [{}])[0].get("label")
                    if "type" in request.GET and "allPending" == request.GET.get("type"):
                        temp_data["current_approvals"] = []
                        for pa in PositionApproval.objects.filter(position=i.position).order_by("sort_order"):
                            t_data = {}
                            t_data["approval_name"] = pa.profile.user.get_full_name()
                            t_data["is_approve"] = pa.is_approve
                            t_data["is_reject"] = pa.is_reject
                            t_data["id"] = pa.id
                            t_data["profile_id"] = encrypt(pa.profile.id)
                            t_data["profile_e_id"] = encrypt(pa.profile.id)
                            temp_data["current_approvals"].append(t_data)
                    temp_data["status"] = i.position.status
                    data.append(temp_data)
                return ResponseOk(
                    {
                        "data": data,
                        "code": status.HTTP_200_OK,
                        "message": "positions list ",
                    }
                )
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "form does not exist",
                }
            )


class GetAllPositionApprovalListing(APIView):
    """
    This GET function fetches all records from Position Approval model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - position(mandatory)
        - domain(mandatory)

    Returns:
        - Serialized Position Approval model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Position Approval Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.PositionApproval.objects.all().exclude(is_reject=True)

    position = openapi.Parameter(
        "position",
        in_=openapi.IN_QUERY,
        description="enter position id",
        type=openapi.TYPE_STRING,
    )
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="enter profile id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[position, profile])
    def get(self, request):
        data = request.GET

        position = data.get("position")

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        if data.get("is_approve") is not None:
            is_approve = data.get("is_approve")
            if is_approve == "true":
                is_approve = True
            else:
                is_approve = False
        else:
            is_approve = None
        profile = data.get("profile")
        try:
            profile = int(decrypt(profile))
        except:
            pass
        try:
            queryset_data = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            print(queryset_data)
            # queryset_data = queryset_data.filter(profile__user__id = request.user.id)
            if position:
                queryset_data = queryset_data.filter(position=position)

            if profile:
                queryset_data = queryset_data.filter(profile=profile)
            if is_approve:
                queryset_data = queryset_data.filter(is_approve=is_approve)
            serializer = FormSerializer.PositionApprovalListSerializer(queryset_data, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Get Positions list Sucessfully.",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Position List  Does Not Exist",
                }
            )


class GetPositionApproval(APIView):
    """
    This GET function fetches particular Position Approval model instance by ID,
    and return it after serializing it.

    Args:
        pk(position_approval_id)
    Body:
        None
    Returns:
        - Serialized Position Approval model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Position Approval Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            position = custom_get_object(pk, FormModel.PositionApproval)
            serializer = FormSerializer.PositionApprovalSerializer(position)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "position approval user get position successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "position approval user does Not Exist",
                }
            )


class CreatePositionApproval(APIView):
    """
    This POST function creates a Position Approval Model record from the data passed in the body.

    Args:
        None
    Body:
        Position Approval model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Position Create API",
        operation_summary="Position Create API",
        request_body=FormSerializer.CreatePositionApprovalSerializer,
    )
    def post(self, request):
        serializer = FormSerializer.CreatePositionApprovalSerializer(
            data=request.data,
        )
        if serializer.is_valid():
            obj = serializer.save()
            # Send notification
            if NotificationType.objects.filter(slug="position-approval-request", is_active=True) and obj.profile.user != request.user:
                send_instant_notification(
                    message="Hi {}, you have been assigned to approve position {}.".format(
                        obj.profile.user.get_full_name(), obj.position.form_data.get("job_title")
                    ),
                    user=obj.profile.user,
                    slug="/position-dashboard",
                    form_data=obj.position,
                    event_type="position-approval",
                )
            if obj.position.status == "active":
                obj.position.status = "draft"
                obj.position.save()
                obj.show = True
                obj.save()
            msg = 0
            for approval in PositionApproval.objects.filter(position=obj.position).order_by("sort_order"):
                approval.approval_type = obj.approval_type
                if approval.approval_type in ["All at once", "a-a-o"] and approval.is_reject == False and approval.is_approve == False:
                    approval.show = True

                    send_postion_approval_mail(approval)
                approval.save()
                if approval.is_approve:
                    continue
                elif approval.is_reject:
                    approval.show = False
                    approval.save()
                else:
                    if msg == 0:
                        approval.show = True
                        send_postion_approval_mail(approval)
                    else:
                        approval.show = False
                    approval.save()
                    if approval.approval_type in ["o-t-o", "one to one"]:
                        msg += 1
            try:
                data = {"user": request.user.id, "description": "You Approved a Position", "type_id": 1}
                create_activity_log(data)
            except:
                pass
            return ResponseOk(
                {
                    "data": serializer.data,
                    "msgg": msg,
                    "code": status.HTTP_200_OK,
                    "message": "Position approval created successfully",
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


class UpdatePositionApproval(APIView):
    """
    This PUT function updates a Position Approval Model record according to the form_data_id passed in url.

    Args:
        pk(position_approval_id)
    Body:
        Position Approval Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) Position Approval does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Position update API",
        operation_summary="Position update API",
        request_body=FormSerializer.CreatePositionApprovalSerializer,
    )
    def put(self, request, pk):
        try:
            data = request.data
            position = custom_get_object(pk, FormModel.PositionApproval)
            serializer = FormSerializer.CreatePositionApprovalSerializer(position, data=data)
            if serializer.is_valid():
                obj = serializer.save()
                total_approvals = PositionApproval.objects.filter(position=position.position).count()
                total_approved = PositionApproval.objects.filter(position=position.position, is_approve=True).count()
                if total_approved == total_approvals:
                    position.position.status = "active"
                    position.position.history.append({"date": str(datetime.datetime.now().date()), "status": "active"})
                    position.position.save()
                    position.position.save()
                elif obj.is_approve:
                    next_obj = PositionApproval.objects.filter(position=position.position).exclude(is_approve=True).order_by("sort_order").first()
                    next_obj.show = True
                    next_obj.save()
                    obj.show = False
                    obj.save()
                try:
                    data = {"user": request.user.id, "description": "You Updated a Approved Position", "type_id": 1}
                    create_activity_log(data)
                except:
                    pass
                # Send notification
                if request.data.get("is_approve"):  # and request.user.email not in [position.position.hiring_manager, position.position.recruiter]:
                    receiver_hr = [position.position.hiring_manager, position.position.recruiter]
                    if request.user.email in receiver_hr:
                        try:
                            receiver_hr.remove(request.user.email)
                        except:
                            pass
                    for i in receiver_hr:
                        try:
                            user_obj = User.objects.get(email=i, user_company=request.user.user_company)
                            send_instant_notification(
                                message="Hi, {} have approved a position approval for the position {}".format(
                                    request.user.get_full_name(), position.position.form_data["job_title"]
                                ),
                                user=user_obj,
                                form_data=position.position,
                            )
                        except Exception as e:
                            print(e)
                if request.data.get("is_reject"):  # and request.user.email not in [position.position.hiring_manager, position.position.recruiter]:
                    receiver_hr = [position.position.hiring_manager, position.position.recruiter]
                    if request.user.email in receiver_hr:
                        try:
                            receiver_hr.remove(request.user.email)
                        except:
                            pass
                    for i in receiver_hr:
                        try:
                            user_obj = User.objects.get(email=i, user_company=request.user.user_company)
                            send_instant_notification(
                                message="Hi, {} have rejected a position approval for the position {}".format(
                                    request.user.get_full_name(), position.position.form_data["job_title"]
                                ),
                                user=user_obj,
                                form_data=position.position,
                            )
                        except Exception as e:
                            print(e)
                Notifications.objects.filter(
                    event_type="position-approval", user=request.user, additional_info__form_data__id=position.position.id
                ).delete()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "form updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "form Does Not Exist",
                    }
                )
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "form Does Not Exist",
                }
            )


class DeletePositionApproval(APIView):
    """
    This DELETE function Deletes a Position Approval Model record accroding to the _id passed in url.

    Args:
        pk(position_approval_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Position Approval does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            positions = custom_get_object(pk, FormModel.PositionApproval)
            prev_order = positions.sort_order
            approvals = FormModel.PositionApproval.objects.filter(position=positions.position).order_by("sort_order")
            # Send notification
            if NotificationType.objects.filter(slug="position-approval-request", is_active=True):
                Notifications.objects.filter(
                    event_type="position-approval", user=positions.profile.user, additional_info__form_data__id=positions.position.id
                ).delete()
            positions.delete()

            count = 1
            for approval in approvals:
                approval.sort_order = count
                approval.save()
                count += 1
            total_approvals = PositionApproval.objects.filter(position=positions.position).count()
            total_approved = PositionApproval.objects.filter(position=positions.position, is_approve=True).count()
            if total_approved == total_approvals and total_approved > 0:
                positions.position.status = "active"
                positions.position.history.append({"date": str(datetime.datetime.now().date()), "status": "active"})
                positions.position.save()
                positions.position.save()
            try:
                next_app = approvals.get(sort_order=prev_order)
                next_app.show = True
                next_app.save()
            except:
                pass
            try:
                data = {"user": request.user.id, "description": "You Deleted a Approved Position", "type_id": 1}
                create_activity_log(data)
            except:
                pass
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "position deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "position Not Exist",
                }
            )


class GetAllOfferApproval(APIView):
    """
    This GET function fetches all records from OfferApproval model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - position(mandatory)
        - domain(mandatory)

    Returns:
        - Serialized OfferApproval model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Offer Does Not Exist
    Authentication:
        JWT
    Raises:
        - serializers.ValidationError("position field required")
        - serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.OfferApproval.objects.all()

    position = openapi.Parameter(
        "position",
        in_=openapi.IN_QUERY,
        description="enter position id",
        type=openapi.TYPE_STRING,
    )
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="enter profile id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[position, profile])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        else:
            data = request.GET

            position = data.get("position")

            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if data.get("search"):
                search = data.get("search")
            else:
                search = ""
            profile = data.get("profile")
            try:
                profile = int(decrypt(profile))
            except:
                pass
            try:
                queryset_data = self.queryset.all().filter(company__url_domain=url_domain).order_by("position", "sort_order")
                # queryset_data = queryset_data.filter(profile__user__id=request.user.id)
                if position:
                    queryset_data = queryset_data.filter(position__id=position)
                if profile:
                    queryset_data = queryset_data.filter(profile=profile)
                if data.get("is_approved") is not None:
                    is_approve = data.get("is_approved")
                    if is_approve == "all":
                        is_approve = None
                    elif is_approve == "true":
                        is_approve = True
                    else:
                        is_approve = False
                else:
                    is_approve = None
                if data.get("export"):
                    export = True
                else:
                    export = False
                if is_approve:
                    queryset_data = queryset_data.filter(is_approve=is_approve)
                elif is_approve is False:
                    queryset_data = queryset_data.filter(is_approve=is_approve).exclude(is_reject=True).exclude(show=False)
                if search:
                    queryset_data = queryset_data.annotate(
                        full_name=Concat("candidate__user__first_name", V(" "), "candidate__user__last_name"),
                        string_id=Cast("position__show_id", output_field=CharField(max_length=256)),
                    ).filter(Q(full_name__icontains=search) | Q(position__form_data__job_title__icontains=search) | Q(string_id__icontains=search))
                if "type" in data and "activity" == data.get("type"):
                    queryset = []
                    for query in queryset_data:
                        if OfferLetter.objects.filter(offered_to__form_data=query.position).exclude(Q(is_decline=True) | Q(withdraw=True)):
                            queryset.append(query)
                    queryset_data = queryset
                if "type" in data and "allPending" == data.get("type"):
                    queryset_data = (
                        queryset_data.filter(Q(position__recruiter=request.user.email) | Q(position__hiring_manager=request.user.email))
                        .exclude(Q(is_approve=True) | Q(is_reject=True))
                        .distinct("position")
                    )
                serializer = FormSerializer.OfferApprovalListSerializer(queryset_data, many=True)
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                    if selected_fields:
                        selected_fields = selected_fields.first().selected_fields
                    else:
                        selected_fields = ["Hiring Manager", "Position No", "Job Title", "Country", "Candidates Applied", "Status"]
                    writer.writerow(selected_fields)

                    for data in queryset_data:
                        serializer_data = FormSerializer.OfferApprovalListSerializer(data).data
                        row = []
                        for field in selected_fields:
                            if field.lower() in ["department", "category", "location", "country", "level", "employment type"]:
                                field = form_utils.position_dict.get(field)
                                try:
                                    value = data.position.form_data.get(field)[0].get("label")
                                    if value is None:
                                        value = data.position.form_data.get(field).get("name")
                                except Exception as e:
                                    print(e)
                                    value = None
                            elif field in ["Position Name", "Job Title"]:
                                value = data.position.form_data.get("job_title")
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
                            "code": status.HTTP_200_OK,
                            "message": "offer list ",
                        }
                    )
            except Exception as e:
                print(e)
                return ResponseBadRequest(
                    {
                        "data": None,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "form does not exist",
                    }
                )


class GetAllOpOfferApproval(APIView):
    """
    This GET function fetches all records from OfferApproval model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - position(mandatory)
        - domain(mandatory)

    Returns:
        - Serialized OfferApproval model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Offer Does Not Exist
    Authentication:
        JWT
    Raises:
        - serializers.ValidationError("position field required")
        - serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.OfferApproval.objects.all()

    position = openapi.Parameter(
        "position",
        in_=openapi.IN_QUERY,
        description="enter position id",
        type=openapi.TYPE_STRING,
    )
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="enter profile id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[position, profile])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        else:
            data = request.GET

            position = data.get("position")

            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if data.get("search"):
                search = data.get("search")
            else:
                search = ""
            profile = data.get("profile")
            try:
                profile = int(decrypt(profile))
            except:
                pass

            try:
                queryset_data = (
                    self.queryset.all()
                    .filter(Q(company__url_domain=url_domain) | Q(company=None))
                    .filter(position__status__in=["active", "hold", "draft"])
                    .order_by("position", "sort_order")
                )
                if position:
                    queryset_data = queryset_data.filter(position__id=position)
                if profile:
                    queryset_data = queryset_data.filter(profile=profile)
                if data.get("is_approved") is not None:
                    is_approve = data.get("is_approved")
                    if is_approve == "all":
                        is_approve = None
                    elif is_approve == "true":
                        is_approve = True
                    else:
                        is_approve = False
                else:
                    is_approve = None
                if data.get("export"):
                    export = True
                else:
                    export = False
                if is_approve:
                    queryset_data = queryset_data.filter(is_approve=is_approve)
                elif is_approve is False:
                    queryset_data = queryset_data.filter(is_approve=is_approve).exclude(is_reject=True).exclude(show=False)
                if search:
                    queryset_data = queryset_data.annotate(
                        full_name=Concat("candidate__user__first_name", V(" "), "candidate__user__last_name"),
                        string_id=Cast("position__show_id", output_field=CharField(max_length=256)),
                    ).filter(Q(full_name__icontains=search) | Q(position__form_data__job_title__icontains=search) | Q(string_id__icontains=search))
                if "type" in data and "activity" == data.get("type"):
                    queryset = []
                    for query in queryset_data:
                        if (
                            OfferLetter.objects.filter(offered_to__form_data=query.position)
                            .exclude(Q(is_decline=True) | Q(withdraw=True))
                            .exclude(offered_to__application_status="offer-rejected")
                        ):
                            queryset.append(query)
                    queryset_data = queryset
                if "type" in data and "allPending" == data.get("type"):
                    queryset_data = (
                        queryset_data.filter(Q(position__recruiter=request.user.email) | Q(position__hiring_manager=request.user.email))
                        .exclude(Q(is_approve=True) | Q(is_reject=True))
                        .distinct("position")
                    )
                    queryset = []
                    for query in queryset_data:
                        if OfferLetter.objects.filter(offered_to__form_data=query.position).exclude(Q(is_decline=True) | Q(withdraw=True)):
                            queryset.append(query)
                    queryset_data = queryset
                if export:
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    fields = [
                        "Position No",
                        "Position Name",
                        "Hiring Manager",
                        "Recruiter",
                        "Location",
                        "Candidate name",
                        "Start Date",
                        "Currency",
                        "Mobile number",
                        "Email ddress",
                        "Status",
                    ]
                    writer.writerow(fields)

                    for i in queryset_data:
                        row = []
                        row.append(i.position.show_id)
                        row.append(i.position.form_data["job_title"])
                        try:
                            user_obj = User.objects.get(email__iexact=i.position.hiring_manager, user_company=i.position.company)
                            row.append(user_obj.get_full_name())
                        except:
                            row.append(i.position.hiring_manager)
                        try:
                            user_obj = User.objects.get(email__iexact=i.position.recruiter, user_company=i.position.company)
                            row.append(user_obj.get_full_name())
                        except:
                            row.append(i.position.recruiter)
                        row.append(i.position.form_data["location"][0]["label"])
                        offer_letter = (
                            OfferLetter.objects.filter(offered_to__form_data=i.position)
                            .exclude(Q(is_decline=True) | Q(withdraw=True))
                            .order_by("id")
                            .last()
                        )
                        if offer_letter:
                            row.append(offer_letter.offered_to.applied_profile.user.get_full_name())
                            row.append(offer_letter.start_date)
                            row.append(offer_letter.currency)
                            row.append(offer_letter.offered_to.applied_profile.phone_no)
                            row.append(offer_letter.offered_to.applied_profile.user.email)
                        else:
                            row.append("Not offered")
                            row.append("Not offered")
                            row.append("Not offered")
                            row.append("Not offered")
                            row.append("Not offered")
                        row.append(i.position.status)
                        writer.writerow(row)
                    response = HttpResponse(csv_response, content_type="text/csv")
                    return response
                else:
                    data = []
                    for i in queryset_data:
                        temp_data = {}
                        temp_data["id"] = i.id
                        temp_data["position_id"] = i.position.id
                        temp_data["sposition_id"] = i.position.show_id
                        temp_data["position_name"] = i.position.form_data["job_title"]
                        offer_letter = (
                            OfferLetter.objects.filter(offered_to__form_data=i.position).exclude(Q(is_decline=True) | Q(withdraw=True)).last()
                        )
                        if offer_letter:
                            temp_data["candidate_name"] = offer_letter.offered_to.applied_profile.user.get_full_name()
                            temp_data["start_date"] = offer_letter.start_date
                            temp_data["currency"] = offer_letter.currency
                            temp_data["mobile"] = offer_letter.offered_to.applied_profile.phone_no
                            temp_data["email"] = offer_letter.offered_to.applied_profile.user.email
                            temp_data["offered_to"] = offer_letter.offered_to.id
                            temp_data["offer_id"] = offer_letter.id
                            temp_data["applied_profile"] = offer_letter.offered_to.id
                            temp_data["user_applied_id"] = encrypt(offer_letter.offered_to.applied_profile.id)
                            if offer_letter.offered_to.application_status in ["approved", "hired"]:
                                temp_data["status"] = "approved"
                            else:
                                temp_data["status"] = "draft"
                        else:
                            temp_data["candidate_name"] = "Not offered"
                            temp_data["start_date"] = "Not offered"
                            temp_data["currency"] = "Not offered"
                            temp_data["mobile"] = "Not offered"
                            temp_data["email"] = "Not offered"
                            temp_data["status"] = "draft"
                        try:
                            user_obj = User.objects.get(email__iexact=i.position.hiring_manager, user_company=i.position.company)
                            temp_data["hiring_manager"] = user_obj.get_full_name()
                        except:
                            temp_data["hiring_manager"] = i.position.hiring_manager
                        try:
                            user_obj = User.objects.get(email__iexact=i.position.recruiter, user_company=i.position.company)
                            temp_data["recruiter"] = user_obj.get_full_name()
                        except:
                            temp_data["recruiter"] = i.position.recruiter
                        temp_data["location"] = i.position.form_data["location"][0]["label"]
                        offer_approval_obj = OfferApproval.objects.filter(position=i.position).order_by("sort_order")
                        approval_data = []
                        for offer_approval in offer_approval_obj:
                            temp_dict = {}
                            temp_dict["approval_type"] = offer_approval.approval_type
                            temp_dict["id"] = offer_approval.id
                            temp_dict["is_approve"] = offer_approval.is_approve
                            temp_dict["is_reject"] = offer_approval.is_reject
                            temp_dict["position"] = offer_approval.position.id
                            temp_dict["slug"] = offer_approval.slug
                            temp_dict["sort_order"] = offer_approval.sort_order
                            temp_dict["profile"] = {}
                            temp_dict["profile"]["full_name"] = offer_approval.profile.user.get_full_name()
                            temp_dict["profile"]["id"] = offer_approval.profile.id
                            temp_dict["profile"]["e_id"] = encrypt(offer_approval.profile.id)
                            approval_data.append(temp_dict)
                        temp_data["offer_approval_details"] = approval_data
                        data.append(temp_data)
                    return ResponseOk(
                        {
                            "data": data,
                            "code": status.HTTP_200_OK,
                            "message": "offer list ",
                        }
                    )
            except Exception as e:
                print(e)
                return ResponseBadRequest(
                    {
                        "data": None,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "form does not exist",
                    }
                )


class GetOfferApproval(APIView):
    """
    This GET function fetches particular Offer Approval model instance by ID,
    and return it after serializing it.

    Args:
        pk(offer_approval_id)
    Body:
        None
    Returns:
        - Serialized Offer Approval model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) offer_approval Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            position = custom_get_object(pk, FormModel.OfferApproval)
            serializer = FormSerializer.OfferApprovalSerializer(position)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "offer approval user get successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "offer approval user does Not Exist",
                }
            )


class CreateOfferApproval(APIView):
    """
    This POST function creates a Offer Approval Model record from the data passed in the body.

    Args:
        None
    Body:
        Offer Approval model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Offer Create API",
        operation_summary="Offer Create API",
        request_body=FormSerializer.OfferApprovalSerializer,
    )
    def post(self, request):
        serializer = FormSerializer.OfferApprovalSerializer(
            data=request.data,
        )
        if serializer.is_valid():
            obj = serializer.save()
            if NotificationType.objects.filter(slug="offer-approval-request", is_active=True) and obj.profile.user != request.user:
                send_instant_notification(
                    message="Hi {}, you have been assigned to approve offer for the position {}.".format(
                        obj.profile.user.get_full_name(), obj.position.form_data["job_title"]
                    ),
                    user=obj.profile.user,
                    slug="/position-dashboard",
                    form_data=obj.position,
                    event_type="offer-approval",
                )
            try:
                data = {"user": request.user.id, "description": "You Approved an Offer", "type_id": 2}
                create_activity_log(data)
            except:
                pass
            msg = 0
            for approval in OfferApproval.objects.filter(position=obj.position).order_by("sort_order"):
                approval.approval_type = obj.approval_type
                if approval.approval_type in ["All at once", "a-a-o"] and approval.is_reject == False and approval.is_approve == False:
                    approval.show = True
                    send_offer_approval_mail(approval)
                approval.save()
                if approval.is_approve:
                    continue
                elif approval.is_reject:
                    approval.show = False
                    approval.save()
                else:
                    if msg == 0:
                        approval.show = True
                        send_offer_approval_mail(approval)
                    else:
                        approval.show = False
                    approval.save()
                    if approval.approval_type in ["o-t-o", "one to one"]:
                        msg += 1
            try:
                offer_letter = OfferLetter.objects.filter(offered_to__form_data=obj.position).last()
                offer_letter.offered_to.application_status = "offer"
                offer_letter.offered_to.save()
            except:
                pass
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Offer approval created successfully",
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


class UpdateOfferApproval(APIView):
    """
    This PUT function updates an Offer Approval Model record according to the id passed in url.

    Args:
        pk(offer_approval_id)
    Body:
        Offer Approval Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) offer_approval does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    is_hire = openapi.Parameter(
        "is_hire",
        in_=openapi.IN_QUERY,
        description="enter is_hire",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[is_hire],
        operation_description="Offer update API",
        operation_summary="Offer update API",
        request_body=FormSerializer.OfferApprovalSerializer,
    )
    def put(self, request, pk):
        data = request.GET
        is_hire = data.get("is_hire")
        offered_to = request.data.get("offered_to")
        try:
            data = request.data
            offer = custom_get_object(pk, FormModel.OfferApproval)
            serializer = FormSerializer.OfferApprovalSerializer(offer, data=data)
            if serializer.is_valid():
                offer_approval = serializer.save()
                # Check if all has approved
                total_approvals = OfferApproval.objects.filter(position=offer_approval.position).count()
                total_approved = OfferApproval.objects.filter(position=offer_approval.position, is_approve=True).count()
                if total_approved == total_approvals:
                    approved_applied_position = AppliedPosition.objects.get(id=int(offered_to))
                    approved_applied_position.application_status = "approved"
                    approved_applied_position.save()
                    try:
                        context = {}
                        offer_letter_obj = OfferLetter.objects.get(offered_to=approved_applied_position)
                        context["Candidate_Name"] = approved_applied_position.applied_profile.user.get_full_name()
                        context["Position_Name"] = approved_applied_position.form_data.form_data["job_title"]
                        context["Company_Name"] = approved_applied_position.company.company_name
                        context["start_date"] = str(offer_letter_obj.start_date)
                        context["CompanyLogin_Link"] = "https://{}.{}".format(approved_applied_position.company.url_domain, settings.DOMAIN_NAME)
                        from_email = settings.EMAIL_HOST_USER
                        body_msg = render_to_string("offer_send.html", context)
                        msg = EmailMultiAlternatives(
                            "Congratulations on Your Offer Letter",
                            body_msg,
                            "Congratulations on Your Offer Letter",
                            [approved_applied_position.applied_profile.user.email],
                        )
                        msg.content_subtype = "html"
                        msg.send()
                        offer_letter_obj.offer_created_mail = True
                        offer_letter_obj.save()
                    except Exception as e:
                        message = "email not sent. " + str(e)
                else:
                    next_obj = OfferApproval.objects.filter(position=offer.position).exclude(is_approve=True).order_by("sort_order").first()
                    next_obj.show = True
                    next_obj.save()
                    offer_approval.show = False
                    offer_approval.save()
                try:
                    data = {"user": request.user.id, "description": "You Updated an Approved Offer", "type_id": 2}
                    create_activity_log(data)
                except:
                    pass
                # Send notification
                if request.data.get("is_approve") and request.user.email not in [offer.position.hiring_manager, offer.position.recruiter]:
                    try:
                        hiring_manager = User.objects.get(email=offer.position.hiring_manager, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have approved an offer approval for the position {}".format(
                                request.user.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=hiring_manager,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                        recruiter = User.objects.get(email=offer.position.recruiter, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have approved an offer approval for the position {}".format(
                                request.user.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=recruiter,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except Exception as e:
                        print(e)
                elif request.data.get("is_approve") and request.user.email in [offer.position.hiring_manager]:
                    try:
                        recruiter = User.objects.get(email=offer.position.recruiter, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have approved an offer approval for the position {}".format(
                                request.user.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=recruiter,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except:
                        pass
                elif request.data.get("is_approve") and request.user.email in [offer.position.recruiter]:
                    try:
                        hiring_manager = User.objects.get(email=offer.position.hiring_manager, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have approved an offer approval for the position {}".format(
                                request.user.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=hiring_manager,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except:
                        pass
                if request.data.get("is_reject") and request.user.email not in [offer.position.hiring_manager, offer.position.recruiter]:
                    try:
                        hiring_manager = User.objects.get(email=offer.position.hiring_manager, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have rejected an offer approval for the position {}".format(
                                request.user.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=hiring_manager,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                        recruiter = User.objects.get(email=offer.position.recruiter, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have rejected an offer approval for the position {}".format(
                                request.user.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=recruiter,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except Exception as e:
                        pass
                elif request.data.get("is_reject") and request.user.email in [offer.position.hiring_manager]:
                    try:
                        recruiter = User.objects.get(email=offer.position.recruiter, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have rejected an offer approval for the position {}".format(
                                request.user.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=recruiter,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except:
                        pass
                elif request.data.get("is_reject") and request.user.email in [offer.position.recruiter]:
                    try:
                        hiring_manager = User.objects.get(email=offer.position.hiring_manager, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have rejected an offer approval for the position {}".format(
                                request.user.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=hiring_manager,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except:
                        pass
                Notifications.objects.filter(
                    event_type="offer-approval", user=request.user, additional_info__form_data__id=offer.position.id
                ).delete()
                try:
                    if int(is_hire) == 1:
                        to_email = offer.profile.user.email
                        first_name = offer.profile.user.first_name
                        company_name = offer.company.company_name
                        job_title = offer.position.form_data["job_title"]
                        from_email = settings.EMAIL_HOST_USER

                        body_msg = "Hi {}, you have been hired by {} to the job position of {}.".format(first_name, company_name, job_title)
                        context = {"body_msg": body_msg}
                        # add here
                        body_msg = render_to_string("offer.html", context)
                        msg = EmailMultiAlternatives("Email For Offer Approval<Don't Reply>", body_msg, from_email, [to_email])
                        msg.content_subtype = "html"
                        msg.send()
                except:
                    pass

                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "offer updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "offer Does Not Exist",
                    }
                )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "offer Does Not Exist",
                }
            )


class DeleteOfferApproval(APIView):
    """
    This DELETE function Deletes a Offer Approval Model record accroding to the id passed in url.

    Args:
        pk(offer_approval_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Offer Approval does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            offer = custom_get_object(pk, FormModel.OfferApproval)
            approvals = FormModel.OfferApproval.objects.filter(position=offer.position).order_by("sort_order")
            prev_order = offer.sort_order
            msg = None
            offer.delete()
            total_approvals = OfferApproval.objects.filter(position=offer.position).count()
            total_approved = OfferApproval.objects.filter(position=offer.position, is_approve=True).count()
            if total_approved == total_approvals:
                try:
                    offer_obj = OfferLetter.objects.filter(offered_to__form_data=offer.position).last()
                    offer_obj.offered_to.application_status = "approved"
                    offer_obj.offered_to.save()
                    try:
                        context = {}
                        context["Candidate_Name"] = offer_obj.offered_to.applied_profile.user.get_full_name()
                        context["Position_Name"] = offer_obj.offered_to.form_data.form_data["job_title"]
                        context["Company_Name"] = offer_obj.offered_to.company.company_name
                        context["start_date"] = str(offer_obj.start_date)
                        context["CompanyLogin_Link"] = "https://{}.{}".format(offer_obj.offered_to.company.url_domain, settings.DOMAIN_NAME)
                        from_email = settings.EMAIL_HOST_USER
                        body_msg = render_to_string("offer_send.html", context)
                        email_msg = EmailMultiAlternatives(
                            "Congratulations on Your Offer Letter",
                            body_msg,
                            "Congratulations on Your Offer Letter",
                            [offer_obj.offered_to.applied_profile.user.email],
                        )
                        email_msg.content_subtype = "html"
                        email_msg.send()
                        offer_obj.offer_created_mail = True
                        offer_obj.save()
                    except Exception as e:
                        message = "email not sent. " + str(e)
                except Exception as e:
                    msg = str(e)
            else:
                try:
                    offer_obj = OfferLetter.objects.filter(offered_to__form_data=offer.position).last()
                    offer_obj.offered_to.application_status = "offer"
                    offer_obj.offered_to.save()
                except Exception as e:
                    msg = str(e)
            if NotificationType.objects.filter(slug="offer-approval-request", is_active=True):
                Notifications.objects.filter(
                    event_type="offer-approval", user=offer.profile.user, additional_info__form_data__id=offer.position.id
                ).delete()
            count = 1
            for approval in approvals:
                approval.sort_order = count
                approval.save()
                count += 1
            try:
                next_app = approvals.get(sort_order=prev_order)
                next_app.show = True
                next_app.save()
            except:
                pass
            try:
                data = {"user": request.user.id, "description": "You Deleted an Approved Offer", "type_id": 2}
                create_activity_log(data)
            except:
                pass
            return ResponseOk({"data": None, "code": status.HTTP_200_OK, "message": "offer deleted SuccessFully", "msg": msg})
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "offer Not Exist",
                }
            )


class GetAllJobCategory(APIView):
    """
    This GET function fetches all records from Job Category model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - search(optional)
        - page(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized Job Category model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Job Category Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.JobCategory.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )
    match = openapi.Parameter(
        "match",
        in_=openapi.IN_QUERY,
        description="match",
        type=openapi.TYPE_STRING,
    )
    candidate_visibility = openapi.Parameter(
        "candidate_visibility",
        in_=openapi.IN_QUERY,
        description="candidate_visibility",
        type=openapi.TYPE_BOOLEAN,
    )
    employee_visibility = openapi.Parameter(
        "employee_visibility",
        in_=openapi.IN_QUERY,
        description="employee_visibility",
        type=openapi.TYPE_BOOLEAN,
    )
    category_list = openapi.Parameter(
        "category_list",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        description="enter category id example [1,2]",
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

    @swagger_auto_schema(manual_parameters=[search, candidate_visibility, employee_visibility, category_list, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        search = data.get("search", "")
        match = data.get("match", "")
        if data.get("export"):
            export = True
        else:
            export = False
        if data.get("category_list"):
            c_list = data.get("category_list")
            if isinstance(c_list, str):
                category_list = data.get("category_list").split(",")
            else:
                category_list = c_list
        else:
            category_list = None

        page = data.get("page", 1)

        limit = data.get("perpage", settings.PAGE_SIZE)

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        try:
            job_category_data = self.queryset.all().filter(Q(company__url_domain=url_domain))
            if category_list is not None:
                job_category_data = job_category_data.filter(id__in=category_list)

            if search:
                job_category_data = job_category_data.filter(Q(job_category__icontains=search))
            if match:
                job_category_data = job_category_data.filter(Q(job_category__iexact=match))

            # Filter out position created by logged in user

            count = job_category_data.count()
            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        job_category_data = job_category_data.order_by("created_at")
                    elif sort_field == "updated_at":
                        job_category_data = job_category_data.order_by("updated_at")
                    elif sort_field == "id":
                        job_category_data = job_category_data.order_by("id")

                    else:
                        job_category_data = job_category_data.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        job_category_data = job_category_data.order_by("-created_at")
                    elif sort_field == "updated_at":
                        job_category_data = job_category_data.order_by("-updated_at")
                    elif sort_field == "id":
                        job_category_data = job_category_data.order_by("-id")

                    else:
                        job_category_data = job_category_data.order_by("-id")
            else:
                job_category_data = job_category_data.order_by("-id")

            if count:
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    selected_fields = ["Job Category", "Description"]
                    writer.writerow(selected_fields)

                    # writer = csv.writer(data_resp, delimiter=",")
                    # writer.writerow(['Job Description', 'Description'])
                    for data in job_category_data:
                        serializer_data = FormSerializer.JobCategoryListSerializer(data, context={"request": request}).data
                        row = []
                        for field in selected_fields:
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
                    if page and limit:
                        job_category_data = job_category_data[skip : skip + limit]

                        pages = math.ceil(count / limit) if limit else 1
                    serializer = FormSerializer.JobCategoryListSerializer(job_category_data, many=True, context={"request": request}).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "job category Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpJobCategory(APIView):
    """
    This GET function fetches all records from Job Category model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - search(optional)
        - page(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized Job Category model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Job Category Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.JobCategory.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )
    match = openapi.Parameter(
        "match",
        in_=openapi.IN_QUERY,
        description="match",
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

    @swagger_auto_schema(manual_parameters=[search, page, perpage, match])
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        search = data.get("search", "")
        match = data.get("match", "")
        if data.get("export"):
            export = True
        else:
            export = False
        if data.get("category_list"):
            c_list = data.get("category_list")
            if isinstance(c_list, str):
                category_list = data.get("category_list").split(",")
            else:
                category_list = c_list
        else:
            category_list = None

        page = data.get("page", 1)

        limit = data.get("perpage", settings.PAGE_SIZE)

        pages, skip = 1, 0

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        try:
            job_category_data = self.queryset.all().filter(Q(company__url_domain=url_domain))
            if category_list is not None:
                job_category_data = job_category_data.filter(id__in=category_list)

            if search:
                job_category_data = job_category_data.filter(Q(job_category__icontains=search))
            if match:
                job_category_data = job_category_data.filter(Q(job_category__iexact=match))

            # Filter out position created by logged in user

            count = job_category_data.count()
            job_category_data = job_category_data.order_by("-id")

            if count:
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    fields = ["ID", "Job Category", "Description"]
                    writer.writerow(fields)
                    for data in job_category_data:
                        row = []
                        row.append(data.id)
                        row.append(data.job_category)
                        row.append(data.description)
                        writer.writerow(row)
                    response = HttpResponse(csv_response, content_type="text/csv")
                    return response
                else:
                    if page and limit:
                        job_category_data = job_category_data[skip : skip + limit]
                        pages = math.ceil(count / limit) if limit else 1
                    resp_data = []
                    for i in job_category_data:
                        temp_data = {}
                        temp_data["id"] = i.id
                        temp_data["job_category"] = i.job_category
                        temp_data["description"] = i.description
                        resp_data.append(temp_data)
                    return ResponseOk(
                        {
                            "data": resp_data,
                            "meta": {
                                "page": page,
                                "total_pages": pages,
                                "perpage": limit,
                                "total_records": count,
                            },
                        }
                    )

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "job category Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllJobCategoryGuest(APIView):
    """
    This GET function fetches all records from Job Category model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - search(optional)
        - page(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized Job Category model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Job Category Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    queryset = FormModel.JobCategory.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
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

    @swagger_auto_schema(manual_parameters=[search, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        if data.get("search"):
            search = data.get("search")
        else:
            search = ""

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

        try:
            job_category_data = self.queryset.all().filter(company__url_domain=url_domain)

            if search:
                job_category_data = job_category_data.filter(Q(job_category__icontains=search))

            count = job_category_data.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        job_category_data = job_category_data.order_by("created_at")
                    elif sort_field == "updated_at":
                        job_category_data = job_category_data.order_by("updated_at")
                    elif sort_field == "id":
                        job_category_data = job_category_data.order_by("id")

                    else:
                        job_category_data = job_category_data.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        job_category_data = job_category_data.order_by("-created_at")
                    elif sort_field == "updated_at":
                        job_category_data = job_category_data.order_by("-updated_at")
                    elif sort_field == "id":
                        job_category_data = job_category_data.order_by("-id")

                    else:
                        job_category_data = job_category_data.order_by("-id")
            else:
                job_category_data = job_category_data.order_by("-id")

            if page and limit:
                job_category_data = job_category_data[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if count:
                serializer = FormSerializer.JobCategoryListSerializer(job_category_data, many=True, context={"request": request}).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "job category Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetJobCategory(APIView):
    """
    This GET function fetches particular Job Category model instance by ID,
    and return it after serializing it.

    Args:
        pk(job_category_id)
    Body:
        None
    Returns:
        - Serialized Job Category model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Job Category Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            job_category = custom_get_object(pk, FormModel.JobCategory)
            serializer = FormSerializer.JobCategorySerializer(job_category)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get Job Category successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " Job Category Not Exist",
                }
            )


class CreateJobCategory(APIView):
    """
    This POST function creates a Job category Model record from the data passed in the body.

    Args:
        None
    Body:
        Job category model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="CreateJobCategory create API",
        operation_summary="CreateJobCategory create API",
        request_body=FormSerializer.JobCategorySerializer,
    )
    def post(self, request):
        serializer = FormSerializer.JobCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Job Category created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Job Category is not valid",
                }
            )


class UpdateJobCategory(APIView):
    """
    This PUT function updates an Job Category Model record according to the job_category_id passed in url.

    Args:
        pk(job_category_id)
    Body:
        Job Category Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) job_category does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="JobCategory update API", operation_summary="JobCategory update API", request_body=FormSerializer.JobCategorySerializer
    )
    def put(self, request, pk):
        try:
            data = request.data
            job_category_data = custom_get_object(pk, FormModel.JobCategory)
            serializer = FormSerializer.JobCategorySerializer(job_category_data, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "JobCategory updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "JobCategory Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "JobCategory Does Not Exist",
                }
            )


class DeleteJobCategory(APIView):
    """
    This DELETE function Deletes a Job Category Model record accroding to the id passed in url.

    Args:
        pk(job_category_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Job Category does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            form_data = custom_get_object(pk, FormModel.JobCategory)
            form_data.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "JobCategory deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "JobCategory Does Not Exist",
                }
            )


class GetAllJobLocation(APIView):
    """
    This GET function fetches all records from Job Location model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - search(optional)
        - page(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized Job Location model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Job Location Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.JobLocation.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )
    is_admin = openapi.Parameter(
        "is_admin",
        in_=openapi.IN_QUERY,
        description="is_admin",
        type=openapi.TYPE_BOOLEAN,
    )
    candidate_visibility = openapi.Parameter(
        "candidate_visibility",
        in_=openapi.IN_QUERY,
        description="candidate_visibility",
        type=openapi.TYPE_BOOLEAN,
    )
    employee_visibility = openapi.Parameter(
        "employee_visibility",
        in_=openapi.IN_QUERY,
        description="employee_visibility",
        type=openapi.TYPE_BOOLEAN,
    )
    country_list = openapi.Parameter(
        "country_list",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        description="enter country id example [1, 2]",
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
        manual_parameters=[search, is_admin, candidate_visibility, employee_visibility, country_list, page, perpage, sort_dir, sort_field]
    )
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        search = data.get("search", "")

        page = data.get("page", 1)

        if data.get("country_list"):
            c_list = data.get("country_list")
            if isinstance(c_list, str):
                country_list = c_list.split(",")
            else:
                country_list = c_list
        else:
            country_list = None

        limit = data.get("perpage", settings.PAGE_SIZE)
        if data.get("export"):
            export = True
        else:
            export = False

        is_admin = data.get("is_admin")
        employee_visibility = data.get("employee_visibility")
        candidate_visibility = data.get("candidate_visibility")

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit
        # url_domain = self.context["request"].GET["domain"]
        company_id = Company.objects.filter(url_domain=url_domain)[0].id

        form_obj = FormData.objects.filter(company=company_id, status="active")
        if candidate_visibility is not None:
            form_obj = form_obj.filter(candidate_visibility=candidate_visibility.capitalize())
        if employee_visibility is not None:
            form_obj = form_obj.filter(employee_visibility=employee_visibility.capitalize())
        country_ids = list(form_obj.values_list("form_data__country__id", flat=True))
        queryset = self.queryset.filter(Q(company__url_domain=url_domain) | Q(company=None))
        try:
            if is_admin == "false" or is_admin == None:
                queryset = queryset.filter(id__in=country_ids)
                if country_list is not None:
                    queryset = queryset.filter(id__in=country_list)
                if search:
                    # queryset = queryset.filter(Q(country__name__icontains=search) | Q(state__name__icontains=search)).distinct()
                    queryset = queryset.filter(
                        Q(state__name__icontains=search) | Q(country__name__icontains=search) | Q(city__name__icontains=search)
                    ).distinct()

            count = queryset.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if count:
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                    if selected_fields:
                        selected_fields = selected_fields.first().selected_fields
                    else:
                        selected_fields = ["Hiring Manager", "Position No", "Job Title", "Country", "Candidates Applied", "Status"]
                    writer.writerow(selected_fields)

                    for data in queryset:
                        serializer_data = FormSerializer.JobLocationListSerializer(data, context={"request": request}).data
                        row = []
                        for field in selected_fields:
                            if field.lower() in ["department", "category", "location", "country", "level", "employment type"]:
                                field = form_utils.position_dict.get(field)
                                try:
                                    value = data.position.form_data.get(field)[0].get("label")
                                    if value is None:
                                        value = data.position.form_data.get(field).get("name")
                                except Exception as e:
                                    print(e)
                                    value = None
                            elif field in ["Position Name", "Job Title"]:
                                value = data.position.form_data.get("job_title")
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
                    if page and limit:
                        queryset = queryset[skip : skip + limit]

                        pages = math.ceil(count / limit) if limit else 1
                    serializer = FormSerializer.JobLocationListSerializer(queryset, many=True, context={"request": request}).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "job Location Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpJobLocation(APIView):
    """
    This GET function fetches all records from Job Location model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - search(optional)
        - page(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized Job Location model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Job Location Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.JobLocation.objects.all()

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )
    is_admin = openapi.Parameter(
        "is_admin",
        in_=openapi.IN_QUERY,
        description="is_admin",
        type=openapi.TYPE_BOOLEAN,
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

    @swagger_auto_schema(manual_parameters=[search, is_admin, page, perpage])
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        search = data.get("search", "")

        page = data.get("page", 1)

        limit = data.get("perpage", settings.PAGE_SIZE)
        if data.get("export"):
            export = True
        else:
            export = False

        is_admin = data.get("is_admin")

        pages, skip = 1, 0

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit
        # url_domain = self.context["request"].GET["domain"]
        company_id = Company.objects.filter(url_domain=url_domain)[0].id

        form_obj = FormData.objects.filter(company=company_id, status="active")
        country_ids = list(form_obj.values_list("form_data__country__id", flat=True))
        queryset = self.queryset.filter(Q(company__url_domain=url_domain) | Q(company=None))
        try:
            if is_admin == "false" or is_admin == None:
                queryset = queryset.filter(id__in=country_ids)
            if search:
                queryset = queryset.filter(
                    Q(state__name__icontains=search) | Q(country__name__icontains=search) | Q(city__name__icontains=search)
                ).distinct()

            count = queryset.count()

            queryset = queryset.order_by("-id")

            if count:
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    fields = ["ID", "Country", "State", "City", "Created at"]
                    writer.writerow(fields)

                    for data in queryset:
                        row = []
                        row.append(data.id)
                        row.append(data.country.name)
                        states = data.state.all().values_list("name", flat=True)
                        row.append(states)
                        city = data.city.all().values_list("name", flat=True)
                        row.append(city)
                        row.append(str(data.created_at))
                        writer.writerow(row)
                    response = HttpResponse(csv_response, content_type="text/csv")
                    return response
                else:
                    if page and limit:
                        queryset = queryset[skip : skip + limit]

                        pages = math.ceil(count / limit) if limit else 1
                    resp_data = []
                    for i in queryset:
                        temp_data = {}
                        temp_data["id"] = i.id
                        temp_data["state"] = []
                        for j in i.state.all():
                            j_data = {}
                            j_data["id"] = j.id
                            j_data["name"] = j.name
                            temp_data["state"].append(j_data)
                        temp_data["city"] = []
                        for j in i.city.all():
                            j_data = {}
                            j_data["id"] = j.id
                            j_data["name"] = j.name
                            j_data["state"] = j.state.id
                            temp_data["city"].append(j_data)
                        temp_data["created_at"] = str(i.created_at)
                        temp_data["country"] = {"id": i.country.id, "name": i.country.name}
                        temp_data["company"] = i.company.company_name
                        if i.country_image:
                            temp_data["country_image"] = i.country_image.url
                        else:
                            temp_data["country_image"] = None
                        resp_data.append(temp_data)
                    return ResponseOk(
                        {
                            "data": resp_data,
                            "meta": {
                                "page": page,
                                "total_pages": pages,
                                "perpage": limit,
                                "total_records": count,
                            },
                        }
                    )

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "job Location Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllJobLocationGuest(APIView):
    """
    This GET function fetches all records from Job Location model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - search(optional)
        - page(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized Job Location model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Job Location Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    queryset = FormModel.JobLocation.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
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
    country_list = openapi.Parameter(
        "country_list",
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        description="enter country id example [1, 2]",
    )
    sort_field = openapi.Parameter(
        "sort_field",
        in_=openapi.IN_QUERY,
        description="sort_field",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[search, page, perpage, sort_dir, country_list, sort_field])
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        if data.get("search"):
            search = data.get("search")
        else:
            search = ""

        if data.get("page"):
            page = data.get("page")
        else:
            page = 1

        if data.get("country_list"):
            c_list = data.get("country_list")
            if isinstance(c_list, str):
                country_list = c_list.split(",")
            else:
                country_list = c_list
        else:
            country_list = None

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

        try:
            queryset = self.queryset.filter(company__url_domain=url_domain)
            if country_list is not None:
                queryset = queryset.filter(country__id__in=country_list)
            if search:
                # queryset = queryset.filter(Q(country__name__icontains=search) | Q(state__name__icontains=search)).distinct()
                queryset = queryset.filter(
                    Q(state__name__icontains=search) | Q(country__name__icontains=search) | Q(city__name__icontains=search)
                ).distinct()

            count = queryset.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if page and limit:
                queryset = queryset[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if count:
                serializer = FormSerializer.JobLocationListSerializer(queryset, many=True, context={"request": request}).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "job Location Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetJobLocation(APIView):
    """
    This GET function fetches particular Job Location model instance by ID,
    and return it after serializing it.

    Args:
        pk(job_location_id)
    Body:
        None
    Returns:
        - Serialized Job Location model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Job Location Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            queryset = custom_get_object(pk, FormModel.JobLocation)
            serializer = FormSerializer.JobLocationListSerializer(queryset, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get Job location successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " Job location Not Exist",
                }
            )


class CreateJobLocation(APIView):
    """
    This POST function creates a Job Location Model record from the data passed in the body.

    Args:
        None
    Body:
        Job Location model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="CreateJobLocation create API",
        operation_summary="CreateJobLocation create API",
        request_body=FormSerializer.JobLocationCreateSerializer,
    )
    def post(self, request):
        # from pprint import pprint

        # state_list = []
        # print("==============================")
        # state = request.data["state"]
        # sate_split = state.split(",")
        # for i in sate_split:
        #     print("----------")
        #     state_list.append(int(i))
        #     print(state_list)
        #     print("----------")
        # print("================================")
        # data = request.data.copy()
        # data["state"] = state_list
        # pprint(data)
        # data = request.data

        # country = data["country"]
        # company = data["company"]

        # # state = request.data["state"]
        # state = data["state"].split(",")
        # for i in range(0, len(state)):
        #     state[i] = int(state[i])

        # # city = request.data["city"]
        # city = data["city"].split(",")
        # for i in range(0, len(city)):
        #     city[i] = int(city[i])

        # print(state)
        # print(type(state))

        # print(type(state))
        # data["state"] = state
        # data["city"] = city

        # print(type(str(data["state"])))
        # print(list(request.data["state"]))
        # print(type(request.data["state"]))
        # print(country)
        # print(company)
        # print(state)
        # print(city)

        # print(data)

        # data_dict = {}
        # data_dict["country"] = country
        # data_dict["company"] = company
        # data_dict["state"] = state
        # data_dict["city"] = city
        # print(data_dict)

        # from django.http import QueryDict

        # query_dict = QueryDict({}, mutable=True)
        # query_dict.update(data_dict)
        # print(query_dict)
        data = {}
        for i in request.data:
            data[i] = request.data.get(i)
        cities = []
        dict_data = dict(request.data)
        for city in dict_data.get("city"):
            if city in ("undefined", "null", None):
                pass
            else:
                cities.append(city)
        data["city"] = cities

        states = []
        for state in dict_data.get("state"):
            if state in ("undefined", "null", None):
                pass
            else:
                states.append(state)
        data["state"] = states
        data["country_image"] = request.data.get("country_image")
        serializer = FormSerializer.JobLocationCreateSerializer(
            data=data,
        )
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Job Location created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Job Location is not valid",
                }
            )


class UpdateJobLocation(APIView):
    """
    This PUT function updates an Job Location Model record according to the id passed in url.

    Args:
        pk(job_location_id)
    Body:
        Job Location Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) job_location does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="JobLocation update API", operation_summary="JobLocation update API", request_body=FormSerializer.JobLocationSerializer
    )
    def put(self, request, pk):
        try:
            data = request.data
            queryset = custom_get_object(pk, FormModel.JobLocation)
            serializer = FormSerializer.JobLocationSerializer(queryset, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "JobLocation updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "JobLocation Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "JobLocation Does Not Exist",
                }
            )


class DeleteJobLocation(APIView):
    """
    This DELETE function Deletes a Job Location Model record accroding to the id passed in url.

    Args:
        pk(job_location_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Job Location does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            form_data = custom_get_object(pk, FormModel.JobLocation)
            form_data.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "JobLocation deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "JobLocation Does Not Exist",
                }
            )


class GetAllRecentViewJob(APIView):
    """
    This GET function fetches all records from Recent Job model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - form_data(optional)
        - profile(optional)
        - page(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized Recent Job model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Recent Job Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.RecentViewJob.objects.all()
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="profile id",
        type=openapi.TYPE_STRING,
    )
    form_data = openapi.Parameter(
        "form_data",
        in_=openapi.IN_QUERY,
        description="form_data id",
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

    @swagger_auto_schema(manual_parameters=[profile, form_data, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        form_data = data.get("form_data", "")

        profile = data.get("profile", "")

        try:
            profile = int(decrypt(profile))
        except:
            pass

        page = data.get("page", 1)

        limit = data.get("perpage", settings.PAGE_SIZE)

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        try:
            queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None))

            if form_data:
                queryset = queryset.filter(Q(form_data=form_data))

            if profile:
                queryset = queryset.filter(Q(profile=profile))

            count = queryset.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if page and limit:
                queryset = queryset[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if count:
                serializer = FormSerializer.RecentViewJobListSerializer(queryset, many=True).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Recent View Job Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetRecentViewJob(APIView):
    """
    This GET function fetches particular Recent Job model instance by ID,
    and return it after serializing it.

    Args:
        pk(recent_job_id)
    Body:
        None
    Returns:
        - Serialized Recent Job  model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Recent Job  Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            queryset = custom_get_object(pk, FormModel.RecentViewJob)
            serializer = FormSerializer.RecentViewJobSerializer(queryset)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get RecentViewJob location successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "message": " RecentViewJob Not Exist",
                    "code": status.HTTP_400_BAD_REQUEST,
                }
            )


class CreateRecentViewJob(APIView):
    """
    This POST function creates a Recent Job Model record from the data passed in the body.

    Args:
        None
    Body:
        Recent Job model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="CreateRecentViewJob create API",
        operation_summary="CreateRecentViewJob create API",
        request_body=FormSerializer.RecentViewJobSerializer,
    )
    def post(self, request):
        serializer = FormSerializer.RecentViewJobSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "RecentViewJob created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "RecentViewJob is not valid",
                }
            )


class UpdateRecentViewJob(APIView):
    """
    This PUT function updates Recent Job Model record according to the id passed in url.

    Args:
        pk(recent_job_id)
    Body:
        Recent Job Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) Recent job does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="RecentViewJob update API",
        operation_summary="RecentViewJob update API",
        request_body=FormSerializer.RecentViewJobSerializer,
    )
    def put(self, request, pk):
        try:
            data = request.data
            queryset = custom_get_object(pk, FormModel.RecentViewJob)
            serializer = FormSerializer.RecentViewJobSerializer(queryset, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "RecentViewJob updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "RecentViewJob Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "RecentViewJob Does Not Exist",
                }
            )


class DeleteRecentViewJob(APIView):
    """
    This DELETE function Deletes a Recent Job Model record accroding to the id passed in url.

    Args:
        pk(recent_job_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Recent Job does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            form_data = custom_get_object(pk, FormModel.RecentViewJob)
            form_data.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "RecentViewJob deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "RecentViewJob Does Not Exist",
                }
            )


class GetAllSavedPosition(APIView):
    """
    This GET function fetches all records from Saved Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - profile(optional)
        - page(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized Saved Position model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Saved Position Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.SavedPosition.objects.all()
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="profile id",
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

    @swagger_auto_schema(manual_parameters=[profile, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        # if data.get("form_data"):
        #     form_data = data.get("form_data")
        # else:
        #     form_data = ""

        if data.get("profile"):
            profile = data.get("profile")
            try:
                profile = int(decrypt(profile))
            except:
                pass
        else:
            raise serializers.ValidationError("profile id field required")

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

        try:
            queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None))

            # if form_data:
            #     queryset = queryset.filter(Q(form_data=form_data))

            if profile:
                queryset = queryset.filter(Q(profile=profile))

            print(queryset)
            count = queryset.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if page and limit:
                queryset = queryset[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if count:
                serializer = FormSerializer.RecentViewJobListSerializer(queryset, many=True).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Recent View Job Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetSavedPosition(APIView):
    """
    This GET function fetches particular Saved Position model instance by ID,
    and return it after serializing it.

    Args:
        pk(saved_position_id)
    Body:
        None
    Returns:
        - Serialized Saved Position model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Saved Position  Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            queryset = custom_get_object(pk, FormModel.SavedPosition)
            serializer = FormSerializer.SavedPositionSerializer(queryset)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get SavedPosition location successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "message": " SavedPosition Not Exist",
                    "code": status.HTTP_400_BAD_REQUEST,
                }
            )


class CreateSavedPosition(APIView):
    """
    This POST function creates a Saved Position Model record from the data passed in the body.

    Args:
        None
    Body:
        Saved Position model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="CreateSavedPosition create API",
        operation_summary="CreateSavedPosition create API",
        request_body=FormSerializer.SavedPositionSerializer,
    )
    def post(self, request):
        data = request.data
        data["profile"] = decrypt(request.data.get("profile"))
        serializer = FormSerializer.SavedPositionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "SavedPosition created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "SavedPosition is not valid",
                }
            )


class UpdateSavedPosition(APIView):
    """
    This PUT function updates Saved Position Model record according to the id passed in url.

    Args:
        pk(saved_position_id)
    Body:
        Saved Position Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) Saved Position does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="SavedPosition update API",
        operation_summary="SavedPosition update API",
        request_body=FormSerializer.SavedPositionSerializer,
    )
    def put(self, request, pk):
        try:
            data = request.data
            queryset = custom_get_object(pk, FormModel.SavedPosition)
            serializer = FormSerializer.SavedPositionSerializer(queryset, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "SavedPosition updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "SavedPosition Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "SavedPosition Does Not Exist",
                }
            )


class DeleteSavedPosition(APIView):
    """
    This DELETE function Deletes a Saved Position Model record accroding to the id passed in url.

    Args:
        pk(saved_position_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Saved Position does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            form_data = custom_get_object(pk, FormModel.SavedPosition)
            form_data.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "SavedPosition deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "SavedPosition Does Not Exist",
                }
            )


class GetAllPositionAlert(APIView):
    """
    This GET function fetches all records from All Position Alert model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - profile(optional)
        - page(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized All Position Model model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) All Position Model Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.PositionAlert.objects.all()
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="profile id",
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

    @swagger_auto_schema(manual_parameters=[profile, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        # if data.get("form_data"):
        #     form_data = data.get("form_data")
        # else:
        #     form_data = ""

        if data.get("profile"):
            profile = data.get("profile")
            try:
                profile = int(decrypt(profile))
            except:
                pass
        else:
            raise serializers.ValidationError("profile id field required")

        page = data.get("page", 1)

        limit = data.get("perpage", settings.PAGE_SIZE)

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        try:
            queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None))

            # if form_data:
            #     queryset = queryset.filter(Q(form_data=form_data))

            if profile:
                queryset = queryset.filter(Q(profile=profile))

            print(queryset)
            count = queryset.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if page and limit:
                queryset = queryset[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if count:
                serializer = FormSerializer.PositionAlertListSerializer(queryset, many=True).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Recent View Job Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetPositionAlert(APIView):
    """
    This GET function fetches particular Position Alert model instance by ID,
    and return it after serializing it.

    Args:
        pk(saved_position_id)
    Body:
        None
    Returns:
        - Serialized Position Alert model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Position Alert  Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            queryset = custom_get_object(pk, FormModel.PositionAlert)
            serializer = FormSerializer.PositionAlertSerializer(queryset)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get PositionAlert location successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "message": " PositionAlert Not Exist",
                    "code": status.HTTP_400_BAD_REQUEST,
                }
            )


class CreatePositionAlert(APIView):
    """
    This POST function creates a Position Alert Model record from the data passed in the body.

    Args:
        None
    Body:
        Position Alert model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="CreatePositionAlert create API",
        operation_summary="CreatePositionAlert create API",
        request_body=FormSerializer.PositionAlertSerializer,
    )
    def post(self, request):
        data = request.data
        data["profile"] = request.user.profile.id
        serializer = FormSerializer.PositionAlertSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "PositionAlert created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "PositionAlert is not valid",
                }
            )


class UpdatePositionAlert(APIView):
    """
    This PUT function updates Position Alert Model record according to the id passed in url.

    Args:
        pk(position_alert_id)
    Body:
        Position Alert Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) Position Alert does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="PositionAlert update API",
        operation_summary="PositionAlert update API",
        request_body=FormSerializer.PositionAlertSerializer,
    )
    def put(self, request, pk):
        try:
            data = request.data
            data["profile"] = request.user.profile.id
            queryset = custom_get_object(pk, FormModel.PositionAlert)
            serializer = FormSerializer.PositionAlertSerializer(queryset, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "PositionAlert updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "PositionAlert Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "PositionAlert Does Not Exist",
                }
            )


class DeletePositionAlert(APIView):
    """
    This DELETE function Deletes a Position Alert Model record according to the id passed in url.

    Args:
        pk(position_alert_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Position Alert does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get_object(self, pk):
        try:
            return FormModel.PositionAlert.objects.get(pk=pk)
        except FormModel.PositionAlert.DoesNotExist:
            raise ResponseNotFound()

    def delete(self, request, pk):
        try:
            form_data = custom_get_object(pk, FormModel.PositionAlert)
            form_data.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "PositionAlert deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "PositionAlert Does Not Exist",
                }
            )


class GetAllAppliedPosition(APIView):
    """
    This GET function fetches all records from Applied Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:class CreateFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = '__all__'
        - None (HTTP_400_BAD_REQUEST) Applied Position Model Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.AppliedPosition.objects.all()  # .filter(applied_profile__user__user_role__name__in=["candidate", "guest"])
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by candidate name and job title",
        type=openapi.TYPE_STRING,
    )
    applied_profile = openapi.Parameter(
        "applied_profile",
        in_=openapi.IN_QUERY,
        description="applied_profile id",
        type=openapi.TYPE_STRING,
    )
    application_status = openapi.Parameter(
        "application_status",
        in_=openapi.IN_QUERY,
        description="application_status",
        type=openapi.TYPE_STRING,
    )
    position_status = openapi.Parameter(
        "position_status",
        in_=openapi.IN_QUERY,
        description="position_status",
        type=openapi.TYPE_STRING,
    )
    position_stage_id = openapi.Parameter(
        "position_stage_id",
        in_=openapi.IN_QUERY,
        description="position_stage_id",
        type=openapi.TYPE_INTEGER,
    )
    form_data = openapi.Parameter(
        "form_data",
        in_=openapi.IN_QUERY,
        description="form_data id (Position id)",
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
    internal_employees = openapi.Parameter(
        "internal_employees",
        in_=openapi.IN_QUERY,
        description="internal_employees",
        type=openapi.TYPE_STRING,
    )
    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export data or not",
        type=openapi.TYPE_STRING,
    )
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="status",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            applied_profile,
            application_status,
            position_status,
            position_stage_id,
            form_data,
            page,
            perpage,
            sort_dir,
            sort_field,
            internal_employees,
            export,
            status,
        ]
    )
    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data:
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        # Search
        if data.get("search") is not None:
            search = data.get("search")
        else:
            search = ""

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        if data.get("form_data"):
            form_data = data.get("form_data")
        else:
            form_data = ""
        if data.get("status"):
            status = data.get("status")
        else:
            status = ""

        if data.get("applied_profile"):
            applied_profile = data.get("applied_profile")
            try:
                applied_profile = int(decrypt(applied_profile))
            except:
                pass
        else:
            applied_profile = ""

        if data.get("export"):
            export = True
        else:
            export = False

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        position_status = data.get("position_status")

        internal_employees = data.get("internal_employees")

        application_status = data.get("application_status")

        position_stage_id = data.get("position_stage_id")
        try:
            if request.user.user_role.name == "hiring manager":
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(company__url_domain=url_domain)
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    applied_position_list = get_all_applied_position(request.user.profile)
                    queryset = self.queryset.all().filter(company__url_domain=url_domain).filter(id__in=applied_position_list)
            else:
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(company__url_domain=url_domain)
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    queryset = self.queryset.all().filter(company__url_domain=url_domain)
            if position_status is not None:
                queryset = queryset.filter(Q(form_data__status=position_status))

            if form_data:
                queryset = queryset.filter(Q(form_data=form_data))

            if applied_profile:
                queryset = queryset.filter(Q(applied_profile=applied_profile))
                if request.user.profile.id == int(applied_profile) and request.user.profile.joined_date:
                    queryset = queryset.filter(created_at__gte=request.user.profile.joined_date)
            if status:
                queryset = queryset.filter(
                    form_data__status="active", application_status__in=["active", "offer", "pending", "hire", "kiv", "pending-offer"]
                )
            if internal_employees:
                queryset = (
                    queryset.exclude(Q(applied_profile__user__user_role__name__in=["candidate", "guest"]))
                    .filter(application_status__in=["active", "approved", "pending", "pending-offer", "offer-rejected"])
                    .filter(form_data__status="active")
                )
                #  .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))

            if application_status:
                queryset = queryset.filter(Q(application_status=application_status))

            if position_stage_id:
                queryset = queryset.filter(Q(data__position_stage_id=int(position_stage_id)))

            queryset = sort_data(queryset, sort_field, sort_dir)
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(Q(full_name__icontains=search) | Q(form_data__form_data__job_title__icontains=search) | Q(string_id__icontains=search))
            queryset = queryset.prefetch_related("form_data", "applied_profile")
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
                    context = {"own_id": request.user.profile.id}
                    serializer_data = FormSerializer.AppliedPositionListSerializer(data, context=context).data
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
                pagination_data = paginate_data(request, queryset, FormModel.AppliedPosition)
                queryset = pagination_data.get("paginate_data")
                if queryset:
                    context = {"own_id": request.user.profile.id}
                    serializer = FormSerializer.AppliedPositionListSerializer(queryset, many=True, context=context).data
                    resp = {
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
                    cache.set(request.get_full_path(), resp)
                    return ResponseOk(resp)

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": rest_status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class OpGetAllAppliedPosition(APIView):
    """
    This GET function fetches all records from Applied Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:class CreateFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = '__all__'
        - None (HTTP_400_BAD_REQUEST) Applied Position Model Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.AppliedPosition.objects.all()  # .filter(applied_profile__user__user_role__name__in=["candidate", "guest"])

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by candidate name and job title",
        type=openapi.TYPE_STRING,
    )
    applied_profile = openapi.Parameter(
        "applied_profile",
        in_=openapi.IN_QUERY,
        description="applied_profile id",
        type=openapi.TYPE_STRING,
    )
    application_status = openapi.Parameter(
        "application_status",
        in_=openapi.IN_QUERY,
        description="application_status",
        type=openapi.TYPE_STRING,
    )
    position_status = openapi.Parameter(
        "position_status",
        in_=openapi.IN_QUERY,
        description="position_status",
        type=openapi.TYPE_STRING,
    )
    position_stage_id = openapi.Parameter(
        "position_stage_id",
        in_=openapi.IN_QUERY,
        description="position_stage_id",
        type=openapi.TYPE_INTEGER,
    )
    form_data = openapi.Parameter(
        "form_data",
        in_=openapi.IN_QUERY,
        description="form_data id (Position id)",
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
    internal_employees = openapi.Parameter(
        "internal_employees",
        in_=openapi.IN_QUERY,
        description="internal_employees",
        type=openapi.TYPE_STRING,
    )
    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export data or not",
        type=openapi.TYPE_STRING,
    )
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="status",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            applied_profile,
            application_status,
            position_status,
            position_stage_id,
            form_data,
            page,
            perpage,
            sort_dir,
            sort_field,
            internal_employees,
            export,
            status,
        ]
    )
    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data:
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        # Search
        search = data.get("search", "")
        url_domain = request.headers.get("domain")

        form_data = data.get("form_data", "")
        status = data.get("status", "")

        applied_profile = data.get("applied_profile")
        try:
            applied_profile = int(decrypt(applied_profile))
        except:
            pass
        if data.get("export"):
            export = True
        else:
            export = False

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        position_status = data.get("position_status")

        internal_employees = data.get("internal_employees")

        application_status = data.get("application_status")

        position_stage_id = data.get("position_stage_id")
        try:
            if request.user.user_role.name == "hiring manager":
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(company__url_domain=url_domain)
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    applied_position_list = get_all_applied_position(request.user.profile)
                    queryset = self.queryset.all().filter(company__url_domain=url_domain).filter(id__in=applied_position_list)
            else:
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(company__url_domain=url_domain)
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    queryset = self.queryset.all().filter(company__url_domain=url_domain)
            if position_status is not None:
                queryset = queryset.filter(Q(form_data__status=position_status))

            if form_data:
                queryset = queryset.filter(Q(form_data=form_data))

            if applied_profile:
                queryset = queryset.filter(Q(applied_profile=applied_profile))
            if status:
                queryset = queryset.filter(
                    form_data__status="active", application_status__in=["active", "offer", "pending", "hire", "kiv", "pending-offer"]
                )
            if internal_employees:
                queryset = (
                    queryset.exclude(Q(applied_profile__user__user_role__name__in=["candidate", "guest"]))
                    .filter(application_status__in=["active", "approved", "pending", "pending-offer", "offer-rejected"])
                    .filter(form_data__status="active")
                )
                #  .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))

            if application_status:
                queryset = queryset.filter(Q(application_status=application_status))

            if position_stage_id:
                queryset = queryset.filter(Q(data__position_stage_id=int(position_stage_id)))

            queryset = sort_data(queryset, sort_field, sort_dir)
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(Q(full_name__icontains=search) | Q(form_data__form_data__job_title__icontains=search) | Q(string_id__icontains=search))
            queryset = queryset.prefetch_related("form_data", "applied_profile")
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
                    context = {"own_id": request.user.profile.id}
                    serializer_data = FormSerializer.OpAppliedPositionListSerializer(data, context=context).data
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
                pagination_data = paginate_data(request, queryset, FormModel.AppliedPosition)
                queryset = pagination_data.get("paginate_data")
                if queryset:
                    context = {"own_id": request.user.profile.id}
                    serializer = FormSerializer.OpAppliedPositionListSerializer(queryset, many=True, context=context).data
                    resp = {
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
                    cache.set(request.get_full_path(), resp)
                    return ResponseOk(resp)

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": rest_status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetOpMyApplications(APIView):
    """
    This GET function fetches all records from Applied Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:class CreateFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = '__all__'
        - None (HTTP_400_BAD_REQUEST) Applied Position Model Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.AppliedPosition.objects.all()  # .filter(applied_profile__user__user_role__name__in=["candidate", "guest"])
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by candidate name and job title",
        type=openapi.TYPE_STRING,
    )
    applied_profile = openapi.Parameter(
        "applied_profile",
        in_=openapi.IN_QUERY,
        description="applied_profile id",
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
    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export data or not",
        type=openapi.TYPE_STRING,
    )
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="status",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            applied_profile,
            page,
            perpage,
            export,
            status,
        ]
    )
    def get(self, request):
        url_domain = request.headers.get("domain")
        try:
            data = cache.get(request.get_full_path() + "?domain=" + url_domain)
        except:
            data = None
        if data:
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        # Search
        search = data.get("search", "")
        status = data.get("status", "")

        if data.get("export"):
            export = True
        else:
            export = False

        position_status = data.get("position_status")

        application_status = data.get("application_status")

        try:
            if request.user.user_role.name == "hiring manager":
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(company__url_domain=url_domain)
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    applied_position_list = get_all_applied_position(request.user.profile)
                    queryset = self.queryset.all().filter(company__url_domain=url_domain).filter(id__in=applied_position_list)
            else:
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(company__url_domain=url_domain)
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    queryset = self.queryset.all().filter(company__url_domain=url_domain)
            if request.user.profile.joined_date:
                queryset = queryset.filter(created_at__gte=request.user.profile.joined_date)
            if position_status is not None:
                queryset = queryset.filter(Q(form_data__status=position_status))

            if status:
                queryset = queryset.filter(
                    form_data__status="active", application_status__in=["active", "offer", "pending", "hire", "kiv", "pending-offer"]
                )
            if application_status:
                queryset = queryset.filter(Q(application_status=application_status))
            queryset = queryset.filter(applied_profile=request.user.profile)
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(Q(full_name__icontains=search) | Q(form_data__form_data__job_title__icontains=search) | Q(string_id__icontains=search))
            queryset = queryset.prefetch_related("form_data", "applied_profile")
            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                fields = []
                writer.writerow(fields)
                for i in queryset:
                    row = []
                    row.append(i.id)
                    row.append(i.form_data.form_data.get("job_title"))
                    row.append(i.form_data.form_data["location"][0]["label"])
                    row.append(str(i.created_at))
                    row.append(i.withdrawn)
                    writer.writerow(row)
                response = HttpResponse(csv_response, content_type="text/csv")
                return response
            else:
                pagination_data = paginate_data(request, queryset, FormModel.AppliedPosition)
                queryset = pagination_data.get("paginate_data")
                resp_data = []
                if queryset:
                    for i in queryset:
                        temp_data = {}
                        temp_data["id"] = i.id
                        temp_data["position_name"] = i.form_data.form_data.get("job_title")
                        temp_data["location"] = i.form_data.form_data["location"][0]["label"]
                        temp_data["job_title"] = i.form_data.form_data["job_title"]
                        temp_data["applied_date"] = str(i.created_at)
                        temp_data["withdrawn"] = i.withdrawn
                        temp_data["applicant_details"] = i.applicant_details
                        resp_data.append(temp_data)
                    resp = {
                        "data": resp_data,
                        "meta": {
                            "page": pagination_data.get("page"),
                            "total_pages": pagination_data.get("total_pages"),
                            "perpage": pagination_data.get("perpage"),
                            "total_records": pagination_data.get("total_records"),
                        },
                    }
                    cache.set(request.get_full_path() + "?domain=" + url_domain, resp)
                    return ResponseOk(resp)

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": rest_status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllWithdrawnPosition(APIView):
    """
    This GET function fetches all records from Withdrawn Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.AppliedPosition.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by candidate name and job title",
        type=openapi.TYPE_STRING,
    )
    applied_profile = openapi.Parameter(
        "applied_profile",
        in_=openapi.IN_QUERY,
        description="applied_profile id",
        type=openapi.TYPE_STRING,
    )
    application_status = openapi.Parameter(
        "application_status",
        in_=openapi.IN_QUERY,
        description="application_status",
        type=openapi.TYPE_STRING,
    )
    position_status = openapi.Parameter(
        "position_status",
        in_=openapi.IN_QUERY,
        description="position_status",
        type=openapi.TYPE_STRING,
    )
    position_stage_id = openapi.Parameter(
        "position_stage_id",
        in_=openapi.IN_QUERY,
        description="position_stage_id",
        type=openapi.TYPE_INTEGER,
    )
    form_data = openapi.Parameter(
        "form_data",
        in_=openapi.IN_QUERY,
        description="form_data id (Position id)",
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
    internal_employees = openapi.Parameter(
        "internal_employees",
        in_=openapi.IN_QUERY,
        description="internal_employees",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            applied_profile,
            application_status,
            position_status,
            position_stage_id,
            form_data,
            page,
            perpage,
            sort_dir,
            sort_field,
            internal_employees,
        ]
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        # Search
        if data.get("search") is not None:
            search = data.get("search")
        else:
            search = ""

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        if data.get("form_data"):
            form_data = data.get("form_data")
        else:
            form_data = ""

        if data.get("applied_profile"):
            applied_profile = data.get("applied_profile")
            try:
                applied_profile = int(decrypt(applied_profile))
            except:
                pass
        else:
            applied_profile = ""

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        position_status = data.get("position_status")

        internal_employees = data.get("internal_employees")

        application_status = data.get("application_status")

        position_stage_id = data.get("position_stage_id")
        try:
            queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None), withdrawn=True)
            if position_status is not None:
                queryset = queryset.filter(Q(form_data__status=position_status))

            if form_data:
                queryset = queryset.filter(Q(form_data=form_data))

            if applied_profile:
                queryset = queryset.filter(Q(applied_profile=applied_profile))

            if internal_employees:
                queryset = queryset.exclude(Q(applied_profile__user__user_role__name__in=["candidate", "guest"]))

            if application_status:
                queryset = queryset.filter(Q(application_status=application_status))

            if position_stage_id:
                queryset = queryset.filter(Q(data__position_stage_id=int(position_stage_id)))

            queryset = sort_data(queryset, sort_field, sort_dir)
            search_keys = [
                "applied_profile__user__first_name__icontains",
                "applied_profile__user__last_name__icontains",
                "applied_profile__user__middle_name__icontains",
            ]
            queryset = search_data(queryset, FormModel.AppliedPosition, search, search_keys)
            pagination_data = paginate_data(request, queryset, FormModel.AppliedPosition)
            queryset = pagination_data.get("paginate_data")
            if queryset:
                serializer = FormSerializer.AppliedPositionListSerializer(queryset, many=True).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAppliedPosition(APIView):
    """
    This GET function fetches particular Applied Position model instance by ID,
    and return it after serializing it.

    Args:
        pk(applied_position_id)
    Body:
        None
    Returns:
        - Serialized Applied Position model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Applied Position Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            queryset = custom_get_object(pk, FormModel.AppliedPosition)
            serializer = FormSerializer.AppliedPositionSerializer(queryset)
            data = serializer.data
            try:
                offerletter_obj = OfferLetter.objects.get(offered_to__id=data["id"])
                offer_letter_serializer = OfferLetterSerializer(offerletter_obj)
                data["offer_letter"] = offer_letter_serializer.data
                data["joining_date"] = data["offer_letter"].get("start_date", None)
            except:
                pass
            try:
                # add applicant documents
                applicant_docs = ApplicantDocuments.objects.filter(applied_position__id=data["id"])
                applied_docs_serializer = FormSerializer.GetApplicantDocumentsSerializer(applicant_docs, many=True)
                data["applicant_docs"] = applied_docs_serializer.data
            except Exception as e:
                print(e)
            # Get if candidate is in other position as hired
            if AppliedPosition.objects.filter(
                applied_profile=queryset.applied_profile, application_status__in=["offer", "pending-offer", "approved", "hired"]
            ).exclude(id=queryset.id):
                data["occupied"] = True
            else:
                data["occupied"] = False
            if AppliedPosition.objects.filter(form_data=queryset.form_data, application_status__in=["offer", "pending-offer", "approved"]):
                data["in_offer"] = True
            else:
                data["in_offer"] = False
            data["sposition_id"] = queryset.form_data.show_id

            # adding rejected-by in case of offer-rejected
            if data["application_status"] == "offer-rejected":
                data["data"]["rejected_by"] = (
                    data["applicant_details"]["first_name"] + " " + data["applicant_details"]["last_name"]
                    if data["applicant_details"]["last_name"]
                    else data["applicant_details"]["first_name"]
                )
                data["data"]["rejection"] = True

            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "AppliedPosition get successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "message": " AppliedPosition Not Exist",
                    "code": status.HTTP_400_BAD_REQUEST,
                }
            )


class ShareAppliedPosition(APIView):
    """
    This POST function creates a Applied Position Model record from the data passed in the body.

    Args:
        None
    Body:
        Applied Position model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="CreateAppliedPosition create API",
        operation_summary="CreateAppliedPosition create API",
        request_body=FormSerializer.AppliedPositionSerializer,
    )
    def post(self, request):
        data = request.data

        new_data = {}
        new_data["applicant_details"] = {}
        domain = request.headers.get("domain")
        if domain is None:
            return ResponseBadRequest(
                {
                    "data": "Please provide domain!",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Email already exists!",
                }
            )

        current_stage_id = Stage.objects.filter(company__url_domain=domain, stage_name="Resume Review")[0].id
        position_stage_id = PositionStage.objects.filter(
            company__url_domain=domain,
            stage__stage_name="Resume Review",
        )[0].id
        new_data["data"] = {"current_stage_id": current_stage_id, "position_stage_id": position_stage_id}
        new_data["form_data"] = request.data["form_data"]
        new_data["company"] = Company.objects.get(url_domain=domain).id
        # new_data["email"] = request.data["email"]

        new_data["applicant_details"]["first_name"] = request.data["first_name"]
        new_data["applicant_details"]["last_name"] = request.data["last_name"]

        new_data["applicant_details"]["phone_no"] = request.data["applicant_details"]["phone_no"]
        new_data["applicant_details"]["password"] = ""
        new_data["applicant_details"]["countrycode"] = ""

        new_data["applicant_details"]["city"] = [
            {
                "label": request.data["applicant_details"]["address"]["city"]["name"]
                if request.data["applicant_details"]["address"]["city"] is not None
                else "",
                "value": request.data["applicant_details"]["address"]["city"]["id"]
                if request.data["applicant_details"]["address"]["city"] is not None
                else "",
            }
        ]
        new_data["applicant_details"]["state"] = [
            {
                "label": request.data["applicant_details"]["address"]["state"]["name"]
                if request.data["applicant_details"]["address"]["state"] is not None
                else "",
                "value": request.data["applicant_details"]["address"]["state"]["id"]
                if request.data["applicant_details"]["address"]["state"] is not None
                else "",
            }
        ]
        new_data["applicant_details"]["country"] = [
            {
                "label": request.data["applicant_details"]["address"]["country"]["name"]
                if request.data["applicant_details"]["address"]["country"] is not None
                else "",
                "value": request.data["applicant_details"]["address"]["country"]["id"]
                if request.data["applicant_details"]["address"]["country"] is not None
                else "",
            }
        ]
        new_data["applicant_details"]["education_detail"] = [
            {
                "education_type": [{"id": request.data["applicant_details"]["education_details"][0]["education_type"]}],
                "university": [{"id": request.data["applicant_details"]["education_details"][0]["university"]}],
                "passing_out_year": "",
                "country": [{"id": request.data["applicant_details"]["education_details"][0]["country"]}],
            }
        ]
        new_data["applicant_details"]["is_converletter"] = "is_converletter"
        new_data["applicant_details"]["message"] = ""
        new_data["applicant_details"]["is_videointro"] = ""
        new_data["applicant_details"]["video_recording"] = ""
        new_data["applicant_details"]["skills"] = []
        new_data["applicant_details"]["hire_text"] = ""
        new_data["applicant_details"]["linkedin_url"] = ""
        new_data["applicant_details"]["college"] = ""
        new_data["applicant_details"]["location"] = ""
        new_data["applicant_details"]["github_url"] = ""
        new_data["applicant_details"]["personal_url"] = ""
        new_data["applicant_details"]["address"] = {"address_one": "", "address_two": "", "address_three": "", "country": "", "state": "", "city": ""}
        new_data["applicant_details"]["countrySearchData"] = ""
        new_data["applicant_details"]["stateSearchData"] = ""
        new_data["applicant_details"]["citySearchData"] = ""
        new_data["applicant_details"]["source"] = ""
        new_data["refereed_by_profile"] = {"key": "value"}
        new_data["applied_profile"] = request.data["applied_profile"]

        if AppliedPosition.objects.filter(applied_profile__id=new_data["applied_profile"], form_data__id=new_data.get("form_data")):
            return ResponseBadRequest(
                {
                    "data": "You have already applied for this position.",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "You have already applied for this position.",
                }
            )
        # if request.data.get("email") and User.objects.filter(email=request.data.get("email")):
        #     return ResponseBadRequest(
        #         {
        #             "data": "Email already exists!",
        #             "code": status.HTTP_400_BAD_REQUEST,
        #             "message": "Email already exists!",
        #         }
        #     )
        serializer = FormSerializer.AppliedPositionSerializer(data=new_data)
        if serializer.is_valid():
            applied_position = serializer.save()
            # Add experience
            experience_list = new_data.get("applicant_details", {}).get("experience_detail", [])
            for experience in experience_list:
                try:
                    country_obj = Country.objects.get(id=experience.get("country")[0].get("value", None))
                except:
                    country_obj = None
                try:
                    leave_date = experience.get("leave_date")
                    if not leave_date:
                        leave_date = None
                    Experience.objects.get_or_create(
                        profile=applied_position.applied_profile,
                        company_name=experience.get("company_name"),
                        role_and_responsibilities=experience.get("role_and_responsibilities"),
                        title=experience.get("title"),
                        country=country_obj,
                        join_date=experience.get("join_date"),
                        is_current_company=experience.get("is_current_company"),
                        leave_date=leave_date,
                    )
                except Exception as e:
                    print(e)
            # Add education
            education_list = new_data.get("applicant_details", {}).get("education_detail", [])
            for education in education_list:
                try:
                    country_obj = Country.objects.get(id=education.get("country")[0].get("value", None))
                except:
                    country_obj = None
                try:
                    education_type_obj = EducationType.objects.get(id=education.get("education_type")[0].get("id", None))
                except:
                    education_type_obj = None
                try:
                    university_obj = University.objects.get(id=education.get("university")[0].get("id", None))
                except:
                    university_obj = None
                try:
                    passing_out_year = education.get("passing_out_year")[0].get("value", None)
                except:
                    passing_out_year = datetime.datetime.now().year
                try:
                    leave_date = education.get("leave_date")
                    if not leave_date:
                        leave_date = None
                    Education.objects.get_or_create(
                        profile=applied_position.applied_profile,
                        education_type=education_type_obj,
                        university=university_obj,
                        passing_out_year=passing_out_year,
                        country=country_obj,
                    )
                except Exception as e:
                    print(e)
            # changing referral of user
            if new_data.get("applicant_details").get("refereed_by_profile") not in [None, "", " "]:
                applied_position.applied_profile.user_refereed_by = new_data.get("applicant_details").get("refereed_by_profile")
                applied_position.applied_profile.save()
                applied_position.refereed_by_profile = new_data.get("applicant_details").get("refereed_by_profile")
                applied_position.save()
            # Assigning first stage
            try:
                first_stage = PositionStage.objects.filter(
                    position=applied_position.form_data, stage__id=new_data.get("data").get("current_stage_id")
                )
                if first_stage:
                    first_stage = first_stage.first().stage.stage_name
                else:
                    first_stage = "Resume Review"
                history_details = applied_position.data.get("history_detail", [])
                history_details.append(
                    {
                        "date": date.today().strftime("%d %B, %Y"),
                        "name": first_stage,
                    }
                )
                applied_position.data["history_detail"] = history_details
                applied_position.save()
            except:
                pass

            context = {
                "candidate_name": applied_position.applied_profile.user.get_full_name(),
                "company_name": request.user.user_company.company_name,
                "position_name": applied_position.form_data.form_data.get("job_title", "Position"),
            }
            body_msg = render_to_string("candidate_ackno.html", context)
            content = fetch_dynamic_email_template(
                body_msg,
                [applied_position.applied_profile.user.email],
                applied_position_id=applied_position.id,
                subject="Thank You for Your Application - {}".format(applied_position.form_data.form_data.get("job_title", "Position")),
            )
            data = serializer.data
            data["is_applied"] = True
            mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
            for i in mem.keys():
                key = i.partition("/")[-1]
                try:
                    if key.startswith("form/form_data/api/v1/"):
                        cache.delete("/" + key)
                except Exception as e:
                    pass
            applied_position.save()
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "CreateAppliedPosition created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "CreateAppliedPosition is not valid",
                }
            )


class CreateAppliedPosition(APIView):
    """
    This POST function creates a Applied Position Model record from the data passed in the body.

    Args:
        None
    Body:
        Applied Position model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="CreateAppliedPosition create API",
        operation_summary="CreateAppliedPosition create API",
        request_body=FormSerializer.AppliedPositionSerializer,
    )
    def post(self, request):
        data = request.data
        data["applied_profile"] = request.user.profile.id
        if AppliedPosition.objects.filter(applied_profile__id=request.user.profile.id, form_data__id=request.data.get("form_data")):
            return ResponseBadRequest(
                {
                    "data": "You have already applied for this position.",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "You have already applied for this position.",
                }
            )
        if request.data.get("email") and User.objects.filter(email=request.data.get("email")):
            return ResponseBadRequest(
                {
                    "data": "Email already exists!",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Email already exists!",
                }
            )
        serializer = FormSerializer.AppliedPositionSerializer(data=data)
        if serializer.is_valid():
            applied_position = serializer.save()
            if request.data.get("candidate_approve"):
                hm_user = User.objects.get(email=applied_position.form_data.hiring_manager, user_company=applied_position.company)
                recruiter_user = User.objects.get(email=applied_position.form_data.recruiter, user_company=applied_position.company)
                candidate_name = "{} {}".format(
                    applied_position.applicant_details.get("first_name", ""), applied_position.applicant_details.get("last_name", "")
                )
                send_reminder(
                    "{} has accepted the consent for the position {}".format(candidate_name, applied_position.form_data.form_data.get("job_title")),
                    hm_user,
                    slug=None,
                    applied_position=None,
                    form_data=applied_position.form_data,
                )
                send_reminder(
                    "{} has accepted the consent for the position {}".format(candidate_name, applied_position.form_data.form_data.get("job_title")),
                    recruiter_user,
                    slug=None,
                    applied_position=None,
                    form_data=applied_position.form_data,
                )

            # Add experience
            experience_list = request.data.get("applicant_details", {}).get("experience_detail", [])
            for experience in experience_list:
                try:
                    country_obj = Country.objects.get(id=experience.get("country")[0].get("value", None))
                except:
                    country_obj = None
                try:
                    leave_date = experience.get("leave_date")
                    if not leave_date:
                        leave_date = None
                    Experience.objects.get_or_create(
                        profile=applied_position.applied_profile,
                        company_name=experience.get("company_name"),
                        role_and_responsibilities=experience.get("role_and_responsibilities"),
                        title=experience.get("title"),
                        country=country_obj,
                        join_date=experience.get("join_date"),
                        is_current_company=experience.get("is_current_company"),
                        leave_date=leave_date,
                    )
                except Exception as e:
                    print(e)
            # Add education
            education_list = request.data.get("applicant_details", {}).get("education_detail", [])
            for education in education_list:
                try:
                    country_obj = Country.objects.get(id=education.get("country")[0].get("value", None))
                except:
                    country_obj = None
                try:
                    education_type_obj = EducationType.objects.get(id=education.get("education_type")[0].get("id", None))
                except:
                    education_type_obj = None
                try:
                    university_obj = University.objects.get(id=education.get("university")[0].get("id", None))
                except:
                    university_obj = None
                try:
                    passing_out_year = education.get("passing_out_year")[0].get("value", None)
                except:
                    passing_out_year = datetime.datetime.now().year
                try:
                    leave_date = education.get("leave_date")
                    if not leave_date:
                        leave_date = None
                    Education.objects.get_or_create(
                        profile=applied_position.applied_profile,
                        education_type=education_type_obj,
                        university=university_obj,
                        passing_out_year=passing_out_year,
                        country=country_obj,
                    )
                except Exception as e:
                    print(e)
            # changing referral of user
            if request.data.get("applicant_details").get("refereed_by_profile") not in [None, "", " "]:
                applied_position.applied_profile.user_refereed_by = request.data.get("applicant_details").get("refereed_by_profile")
                applied_position.applied_profile.save()
                applied_position.refereed_by_profile = request.data.get("applicant_details").get("refereed_by_profile")
                applied_position.save()
            # Assigning first stage
            try:
                first_stage = PositionStage.objects.filter(
                    position=applied_position.form_data, stage__id=request.data.get("data").get("current_stage_id")
                )
                if first_stage:
                    first_stage = first_stage.first().stage.stage_name
                else:
                    first_stage = "Resume Review"
                history_details = applied_position.data.get("history_detail", [])
                history_details.append(
                    {
                        "date": date.today().strftime("%d %B, %Y"),
                        "name": first_stage,
                    }
                )
                applied_position.data["history_detail"] = history_details
                applied_position.save()
            except:
                pass
            try:
                # Referral Notitication
                # position_obj = Profile.objects.get(id=serializer.data["applied_profile"])
                # red_profile_id = position_obj.user_refereed_by.get('profile_id', None)
                # if red_profile_id == applied_position.refereed_by_profile.id:
                #     pass
                # else:
                #     # Send notification
                #     if NotificationType.objects.filter(slug='employee-referral-notification', is_active=True):
                #         send_instant_notification(
                #             message="Hi {}, you just got a new referral.".format(applied_position.refereed_by_profile.user.get_full_name()),
                #             user=applied_position.refereed_by_profile.user,
                # )
                data = {
                    "user": request.user.id,
                    "description": "{} Applied For This Position".format(applied_position.applied_profile.user.first_name),
                    "type_id": 4,
                    "applied_position": serializer.data["id"],
                }
                create_activity_log(data)
            except Exception as e:
                print(e)
            # Send acknowledgment email
            context = {
                "candidate_name": applied_position.applied_profile.user.get_full_name(),
                "company_name": request.user.user_company.company_name,
                "position_name": applied_position.form_data.form_data.get("job_title", "Position"),
            }
            body_msg = render_to_string("candidate_ackno.html", context)
            content = fetch_dynamic_email_template(
                body_msg,
                [applied_position.applied_profile.user.email],
                applied_position_id=applied_position.id,
                subject="Thank You for Your Application - {}".format(applied_position.form_data.form_data.get("job_title", "Position")),
            )
            data = serializer.data
            data["is_applied"] = True
            mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
            for i in mem.keys():
                key = i.partition("/")[-1]
                try:
                    if key.startswith("form/form_data/api/v1/"):
                        cache.delete("/" + key)
                except Exception as e:
                    pass
            applied_position.save()
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "CreateAppliedPosition created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "CreateAppliedPosition is not valid",
                }
            )


class RejectCandidateApplication(APIView):
    """
    This PUT function updates Applied Position Model record according to the id passed in url.

    Args:
        pk(applied_position_id)
    Body:
        Applied Position Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) Applied Position does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="AppliedPosition update API",
        operation_summary="AppliedPosition update API",
        request_body=FormSerializer.AppliedPositionSerializer,
    )
    def put(self, request, pk):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.data
            queryset = custom_get_object(pk, FormModel.AppliedPosition)
            db_json_field = queryset.data
            req_json_field = data.get("data")
            try:
                if req_json_field is not None:
                    for field in db_json_field:
                        if field not in req_json_field:
                            req_json_field[field] = db_json_field[field]
            except:
                None
            serializer = FormSerializer.AppliedPositionSerializer(queryset, data=data, partial=True)
            if serializer.is_valid():
                obj = serializer.save()
                if obj.application_status == "reject" and "rejected_at" not in obj.data:
                    obj.data["rejected_at"] = str(datetime.datetime.today().date())
                    obj.data["rejected_by"] = request.user.get_full_name()
                    obj.data["created_at"] = str(datetime.datetime.today().date())
                    send_instant_notification(
                        message="Hi {}, you have been rejected for the position {}".format(
                            obj.applied_profile.user.get_full_name(), obj.form_data.form_data["job_title"]
                        ),
                        user=obj.applied_profile.user,
                        applied_position=obj,
                    )
                    obj.save()
                    # send mail for rejection if yes selected
                    if request.data.get("rejection_mail_sent"):
                        to = [obj.applied_profile.user.email]
                        subject = "You status for the position {}!".format(obj.form_data.form_data["job_title"])
                        try:
                            email_template = EmailTemplate.objects.filter(template_name="Candidate Rejection Email").last()
                            content = email_template.description
                        except Exception as e:
                            print(e)
                            content = "You status for the position {}!".format(obj.form_data.form_data["job_title"])
                        content = fetch_dynamic_email_template(content, to, pk, subject=subject)
                    else:
                        pass
                # add reject activity
                # current_stage = obj.data["position_stage_id"]
                # stage_id = PositionStage.objects.get(id=current_stage)
                # stage_name = stage_id.stage.stage_name
                log_data = {
                    "user": request.user.id,
                    "description": "Candidate Rejected by {}.".format(request.user.get_full_name()),
                    "type_id": 4,
                    "applied_position": obj.id,
                }
                create_activity_log(log_data)
                return Response({"msg": "candidate updated"}, status=rest_status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg": "error occured", "error": str(e)}, status=rest_status.HTTP_400_BAD_REQUEST)


class UpdateAppliedPosition(APIView):
    """
    This PUT function updates Applied Position Model record according to the id passed in url.

    Args:
        pk(applied_position_id)
    Body:
        Applied Position Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) Applied Position does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="AppliedPosition update API",
        operation_summary="AppliedPosition update API",
        request_body=FormSerializer.AppliedPositionSerializer,
    )
    def put(self, request, pk):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.data
            history_data = copy.deepcopy(data)
            req_data = copy.deepcopy(request.data)
            queryset = custom_get_object(pk, FormModel.AppliedPosition)
            db_json_field = queryset.data
            req_json_field = data.get("data")
            try:
                if req_json_field is not None:
                    for field in db_json_field:
                        if field not in req_json_field:
                            req_json_field[field] = db_json_field[field]
            except:
                None
            old_stage = queryset.data.get("current_stage_id")
            print("testing changes")
            if "data" in request.data:
                if old_stage != request.data.get("data").get("current_stage_id"):
                    if request.user.email not in [queryset.form_data.hiring_manager, queryset.form_data.recruiter]:
                        return ResponseBadRequest(
                            {
                                "data": {"error": ["You are not authorized to move stage."]},
                                "code": status.HTTP_400_BAD_REQUEST,
                                "message": "You are not authorized to move stage.",
                            }
                        )
            if queryset.form_data.status in ["close", "closed"]:
                if queryset.application_status == "hired":
                    pass
                else:
                    return ResponseBadRequest(
                        {
                            "data": {"error": ["Position closed! Can not move stages."]},
                            "code": status.HTTP_400_BAD_REQUEST,
                            "message": "Position closed! Can't move stages!",
                        }
                    )
            applied_profile_str = data["applied_profile"]
            data["applied_profile"] = queryset.applied_profile.id
            serializer = FormSerializer.AppliedPositionSerializer(queryset, data=data, partial=True)
            if serializer.is_valid():
                obj = serializer.save()
                data["applied_profile"] = applied_profile_str
                try:
                    # check if candidate is moved to offer directly then send to pending offer
                    if old_stage != obj.data.get("current_stage_id"):
                        new_stage = Stage.objects.filter(id=obj.data.get("current_stage_id")).last()
                        current_stage = serializer.data["data"]["position_stage_id"]
                        stage_id = PositionStage.objects.get(id=current_stage)
                        stage_name = stage_id.stage.stage_name
                        if stage_name == "Offer" and obj.application_status not in ["reject", "rejected"]:
                            queryset.application_status = "pending-offer"
                            queryset.save()
                        # reset the active status at time of changing the stage if the current stage is lower thatn hired and offer
                        if new_stage:
                            offer_stage = PositionStage.objects.filter(stage__stage_name="Offer", position=stage_id.position)
                            if offer_stage.first() and new_stage.sort_order < offer_stage.first().sort_order:
                                queryset.application_status = "active"
                                queryset.save()
                            else:
                                hired_stage = PositionStage.objects.filter(stage__stage_name="Hired", position=stage_id.position)
                                if (
                                    hired_stage.first()
                                    and new_stage.sort_order < hired_stage.first().sort_order
                                    and new_stage.stage.stage_name != "Offer"
                                ):
                                    queryset.application_status = "active"
                                    queryset.save()
                        # if stage_name in [
                        #     "Resume Review",
                        #     "Hiring Manager Review",
                        #     "Interview",
                        #     "1st Interview"
                        #     "2nd Interview",
                        #     "Panel Discussion",
                        #     "HR Discussion",
                        #     "Final Interview",
                        # ]:
                        #     queryset.application_status = "active"
                        #     queryset.save()
                        log_data = {
                            "user": request.user.id,
                            "description": "Candidate Moved to {} by {}.".format(stage_name, request.user.get_full_name()),
                            "type_id": 4,
                            "applied_position": serializer.data["id"],
                        }
                        create_activity_log(log_data)
                except Exception as e:
                    print(e)
                # Replace interview link
                if "data" in req_data and "interview_schedule_data" in req_data["data"] and "email" in req_data["data"]["interview_schedule_data"]:
                    # try:
                    email_data = req_data["data"]["interview_schedule_data"]["email"]

                    from_email = settings.EMAIL_HOST_USER
                    to = email_data["to"]
                    # cc = email_data["cc"]
                    subject = email_data["subject"]
                    content = email_data["content"]
                    # Append the google meet link the content
                    if request.data.get("data").get("videoInterviewContent"):
                        splited_content = content.rpartition("Thank you")
                        merged_content = "{}<br>{}<br><br>".format(splited_content[0], request.data.get("data").get("videoInterviewContent"))
                        for content in splited_content[1:]:
                            merged_content += content
                    else:
                        merged_content = content
                    content = fetch_dynamic_email_template(merged_content, to, pk, subject=subject)
                # set interview and send mail about interview
                if (
                    "data" in req_data
                    and "interview_schedule_data" in req_data["data"]
                    and "candidate_data" in req_data["data"]["interview_schedule_data"]
                    and "email" in req_data["data"]["interview_schedule_data"]["candidate_data"]
                ):
                    interview_data = request.data["data"]["interview_schedule_data"]["candidate_data"]
                    interviewer_data = request.data["data"]["interview_schedule_data"]["Interviewer"]
                    email_data = interview_data.get("email")
                    subject = email_data["subject"]
                    to = email_data.get("to")
                    content = email_data.get("content")
                    # Append the google meet link the content
                    if request.data.get("data").get("videoInterviewContent"):
                        splited_content = content.rpartition("Thank you")
                        merged_content = "{}<br>{}<br><br>".format(splited_content[0], request.data.get("data").get("videoInterviewContent"))
                        if request.data.get("data").get("interview_schedule_data").get("date"):
                            pass
                        else:
                            for d in interviewer_data:
                                data = {}
                                data["domain"] = request.user.user_company.url_domain
                                data["email"] = d["email"]
                                res, link = get_calendly_link(data)
                                if res and link:
                                    link = link + "?utm_source={}".format(obj.id)
                                    merged_content += "Schedule you interview with {} using this <a href='{}' style='color:blue;text-decoration:underline'>link</a><br><br>".format(
                                        d["label"], link
                                    )
                                try:
                                    int(d["value"])
                                except:
                                    d["value"] = decrypt(d["value"])
                                try:
                                    int(d["value"])
                                except:
                                    d["profile_id"] = decrypt(d["profile_id"])
                        for content in splited_content[1:]:
                            merged_content += content
                    else:
                        merged_content = content
                    content = fetch_dynamic_email_template(merged_content, [to], pk, subject=subject)
                    obj.data["interview_schedule_data"] = interviewer_data
                updated_interview_list = []
                for schedule in obj.data.get("interview_schedule_data_list", []):
                    interviewers = []
                    for t_interviewer in schedule.get("Interviewer"):
                        try:
                            int(t_interviewer["value"])
                        except:
                            t_interviewer["value"] = decrypt(t_interviewer["value"])
                        try:
                            int(t_interviewer["profile_id"])
                        except:
                            t_interviewer["profile_id"] = decrypt(t_interviewer["profile_id"])
                        interviewers.append(t_interviewer)
                    schedule["Interviewer"] = interviewers
                    updated_interview_list.append(schedule)
                obj.data["interview_schedule_data_list"] = updated_interview_list
                obj.save()
                # Send notification to recruiter or hiring manager
                if "data" in history_data and "history_detail" in history_data["data"]:
                    history_detail = request.data["data"]["history_detail"]
                    prev_stage_name = history_detail[-2]["name"]
                    current_stage_name = history_detail[-1]["name"]
                    email = request.user.email
                    candidate_name = queryset.applied_profile.user.get_full_name()
                    if email == queryset.form_data.hiring_manager:
                        # send notification to requiter
                        recruiter_obj = User.objects.get(email=queryset.form_data.recruiter, user_company=queryset.company)
                        if NotificationType.objects.filter(slug="move-stages", is_active=True):
                            send_instant_notification(
                                message="{} moved to {} stage".format(candidate_name, current_stage_name),
                                user=recruiter_obj,
                                slug="/position-dashboard/candidate-view",
                                applied_position=queryset,
                            )
                    elif email == queryset.form_data.recruiter:
                        # send notification to hiring manager
                        hiring_manager_obj = User.objects.get(email=queryset.form_data.hiring_manager, user_company=queryset.company)
                        if NotificationType.objects.filter(slug="move-stages", is_active=True):
                            send_instant_notification(
                                message="{} moved to {} stage".format(candidate_name, current_stage_name),
                                user=hiring_manager_obj,
                                slug="/position-dashboard/candidate-view",
                                applied_position=queryset,
                            )
                # send mail
                try:
                    if (
                        "interview_cancelled" in obj.data
                        and "cancelled_mail_sent" not in obj.data
                        and obj.application_status not in ["reject", "rejected"]
                    ):
                        data = obj.data
                        # code to send mail
                        to = [obj.applied_profile.user.email]
                        subject = "Your interview has been cancelled!"
                        content = "We appreciate your effort and time which you took to apply for this job. But we are sorry to inform you that we wil not be moving forward with your application and thus decided to cancel the interview. We hope a better future for you. Thanks"
                        content = fetch_dynamic_email_template(content, to, pk, subject=subject)
                        data["cancelled_mail_sent"] = True
                        data["cancelled_by"] = request.user.get_full_name()
                        data["cancelled_time"] = str(datetime.datetime.now().date())
                        if "interview_schedule_data" in data:
                            data.pop("interview_schedule_data")

                        obj.application_status = "cancelled"
                        obj.data = data
                        obj.save()
                except Exception as e:
                    return ResponseBadRequest(
                        {
                            "data": str(e),
                            "code": status.HTTP_400_BAD_REQUEST,
                            "message": "AppliedPosition Not valid",
                        }
                    )
                if request.data.get("data", {}).get("interview_cancelled") == False and obj.application_status not in ["reject", "rejected"]:
                    obj.data["interview_cancelled"] = False
                    obj.data.pop("cancelled_by", None)
                    obj.data.pop("cancelled_mail_sent", None)
                    obj.data.pop("cancelled_time", None)
                    obj.application_status = "active"
                    obj.save()
                # add rejected date
                msg = None
                if obj.application_status == "reject" and "rejected_at" not in obj.data:
                    obj.data["rejected_at"] = str(datetime.datetime.today().date())
                    obj.data["rejected_by"] = request.user.get_full_name()
                    obj.data["created_at"] = str(datetime.datetime.today().date())
                    send_instant_notification(
                        message="Hi {}, you have been rejected for the position {}".format(
                            obj.applied_profile.user.get_full_name(), obj.form_data.form_data["job_title"]
                        ),
                        user=obj.applied_profile.user,
                        applied_position=obj,
                    )
                    obj.save()
                    # send mail for rejection if yes selected
                    if request.data.get("rejection_mail_sent"):
                        to = [obj.applied_profile.user.email]
                        subject = "You status for the position {}!".format(obj.form_data.form_data["job_title"])
                        try:
                            email_template = EmailTemplate.objects.filter(template_name="Candidate Rejection Email").last()
                            content = email_template.description
                        except Exception as e:
                            print(e)
                            content = "You status for the position {}!".format(obj.form_data.form_data["job_title"])
                        content = fetch_dynamic_email_template(content, to, pk, subject=subject)
                    else:
                        pass
                    try:  # maybe
                        applied_position_objs = AppliedPosition.objects.filter(application_status="active", form_data=obj.form_data)
                        if applied_position_objs:
                            serialized_data = AppliedPositionListSerializer(applied_position_objs, many=True).data
                            final_data = sorted(serialized_data, key=lambda d: d["average_scorecard_rating"], reverse=True)
                            top_rating = final_data[0]["average_scorecard_rating"]
                            for final in final_data:
                                if final["average_scorecard_rating"] == top_rating and top_rating > 0:
                                    applied_position_obj = AppliedPosition.objects.get(id=final["id"])
                                    applied_position_obj.application_status = "pending"
                                    applied_position_obj.save()

                            # tentative changes 14072023
                            # if final_data[0]["average_scorecard_rating"] > 0:
                            #     applied_position_obj = AppliedPosition.objects.get(id=final_data[0]["id"])
                            #     applied_position_obj.application_status = "pending"
                            #     applied_position_obj.save()
                            # if len(final_data) > 1 and final_data[1]["average_scorecard_rating"] > 0:
                            #     applied_position_obj = AppliedPosition.objects.get(id=final_data[1]["id"])
                            #     applied_position_obj.application_status = "pending"
                            #     applied_position_obj.save()
                    except Exception as e:
                        error = str(e)
                        msg = "Next candidate not moved to pending decison. " + error
                        pass
                    # send mail
                    # passs
                data = serializer.data
                data["msg"] = msg
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "AppliedPosition updated successfully",
                    }
                )
            else:
                print("-------------------------------------------------")
                print("here")
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "AppliedPosition Not valid",
                    }
                )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "AppliedPosition Not valid",
                }
            )

    # except:
    #     return ResponseBadRequest(
    #         {
    #             "data": None,
    #             "code": status.HTTP_400_BAD_REQUEST,
    #             "message": "AppliedPosition Does Not Exist",
    #         }
    #     )


class DeleteAppliedPosition(APIView):
    """
    This DELETE function Deletes a Applied Position Model record according to the id passed in url.

    Args:
        pk(applied_position_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Applied Position does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            object = custom_get_object(pk, FormModel.AppliedPosition)
            object.delete()
            try:
                position_obj = Profile.objects.get(user=request.user.id)
                app_name = position_obj.user.first_name
                data = {"user": request.user.id, "description": "{} deleted a job application".format(app_name), "type_id": 4}
                create_activity_log(data)
            except:
                pass
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "AppliedPosition deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "AppliedPosition Does Not Exist",
                }
            )


class JobLocationCSVExport(APIView):
    """
    This Get function filter a Job Locations on the basis of company_id and write a CSV from the filtered data and returs a CSV file.

    Args:
        None
    Body:
        - company_id
    Returns:
        - csv file
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, company_id):
        queryset = FormModel.JobLocation.objects.filter(company=company_id)

        queryset_df = pd.DataFrame(
            queryset.values(
                "id",
                "country__name",
                "state__name",
                "city__name",
            )
        )
        print(queryset_df)
        writer = CSVWriter(queryset_df)
        response = writer.convert_to_csv(filename=generate_file_name("Employee", "csv"))
        return response


class JobCategoryCSVExport(APIView):
    """
    This Get function filter a Job Category on the basis of company_id and write a CSV from the filtered data and returs a CSV file.

    Args:
        None
    Body:
        - company_id
    Returns:
        - csv file
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, company_id):
        queryset = FormModel.JobCategory.objects.filter(Q(company=company_id) | Q(company=None))

        queryset_df = pd.DataFrame(
            queryset.values(
                "id",
                "job_category",
                "description",
            )
        )
        writer = CSVWriter(queryset_df)
        response = writer.convert_to_csv(filename=generate_file_name("job_category", "csv"))
        return response


class GetAllReason(APIView):
    """
    This GET function fetches all records from Reason model
    after filtering on the basis of fields given in the body
    and return the data after serializing it.

    Args:
        None
    Body:
        - page (optional)
        - perpage (optional)
        - search (optional)
        - role (optional)
        - sort_field (optional)
        - sort_dir (optional)
    Returns:
        - Serialized Reason model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search access by reason",
        type=openapi.TYPE_STRING,
    )
    reason_type = openapi.Parameter(
        "reason_type",
        in_=openapi.IN_QUERY,
        description="enter reason_type",
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

    @swagger_auto_schema(manual_parameters=[reason_type, search, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET

        # Search
        search = data.get("search", "")

        url_domain = request.headers.get("domain")
        if data.get("export"):
            export = True
        else:
            export = False
        reason_type = data.get("reason_type")

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        # access filter
        try:
            query_data = Reason.objects.all().filter(company__url_domain=url_domain).distinct("reason")
            if reason_type is not None:
                query_data = query_data.filter(type__reason_name=reason_type)

            query_data = search_data(query_data, Reason, search)
            # query_data = sort_data(query_data, sort_field, sort_dir)
            # query_data = query_data.distinct("reason")
            if query_data:
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                    if selected_fields:
                        selected_fields = selected_fields.last().selected_fields
                    else:
                        selected_fields = ["Reasons", "Type"]
                    writer.writerow(selected_fields)
                    for data in query_data:
                        serializer_data = FormSerializer.ReasonSerializer(data).data
                        row = []
                        for field in selected_fields:
                            if field == "Reasons":
                                row.append(serializer_data["reason"])
                            else:
                                row.append(serializer_data["type"]["reason_name"])
                        writer.writerow(row)
                    response = HttpResponse(csv_response, content_type="text/csv")
                    return response
                else:
                    pagination_data = paginate_data(request, query_data, Reason)
                    query_data = pagination_data.get("paginate_data")
                    serializer = ReasonSerializer(query_data, many=True).data
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
                return ResponseBadRequest({"No Data Found"})
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpReason(APIView):
    """
    This GET function fetches all records from Reason model
    after filtering on the basis of fields given in the body
    and return the data after serializing it.

    Args:
        None
    Body:
        - page (optional)
        - perpage (optional)
        - search (optional)
        - role (optional)
        - sort_field (optional)
        - sort_dir (optional)
    Returns:
        - Serialized Reason model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search access by reason",
        type=openapi.TYPE_STRING,
    )
    reason_type = openapi.Parameter(
        "reason_type",
        in_=openapi.IN_QUERY,
        description="enter reason_type",
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

    @swagger_auto_schema(manual_parameters=[reason_type, search, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET

        # Search
        search = data.get("search", "")

        url_domain = request.headers.get("domain")
        if data.get("export"):
            export = True
        else:
            export = False
        reason_type = data.get("reason_type")

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        # access filter
        try:
            query_data = Reason.objects.all().filter(company__url_domain=url_domain).distinct("reason")
            if reason_type is not None:
                query_data = query_data.filter(type__reason_name=reason_type)

            query_data = search_data(query_data, Reason, search)
            # query_data = sort_data(query_data, sort_field, sort_dir)
            # query_data = query_data.distinct("reason")
            if query_data:
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    fields = []
                    writer.writerow(fields)
                    for i in query_data:
                        row = [i.type.reason_name]
                        row = [i.reason]
                        writer.writerow(row)
                    response = HttpResponse(csv_response, content_type="text/csv")
                    return response
                else:
                    pagination_data = paginate_data(request, query_data, Reason)
                    query_data = pagination_data.get("paginate_data")
                    data = []
                    for i in query_data:
                        temp_data = {}
                        temp_data["id"] = i.id
                        temp_data["reason"] = i.reason
                        temp_data["type"] = {}
                        temp_data["type"]["reason_name"] = i.type.reason_name
                        data.append(temp_data)
                    return ResponseOk(
                        {
                            "data": data,
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
                return ResponseBadRequest({"No Data Found"})
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateReason(APIView):
    """
    This POST function creates a Reason record from the data
    passed in the body.

    Args:
        None
    Body:
        Reason Model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(operation_description="Reason Create API", operation_summary="Reason Create API", request_body=ReasonSerializer)
    def post(self, request):
        serializer = CreateReasonSerializer(
            data=request.data,
        )
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Reasons Created Successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Something Went wrong",
                }
            )


class GetReason(APIView):
    """
    This GET function fetches particular Reason instance by ID,
    and return it after serializing it.

    Args:
        pk(reason_id)
    Body:
        None
    Returns:
        - Serialized Reason model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            reason = custom_get_object(pk, Reason)
            serializer = ReasonSerializer(reason)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get reason successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Reason Does Not Exist",
                }
            )


class DeleteReason(APIView):
    """
    This DELETE function Deletes a Reason record according to the
    reason_id passed in url.

    Args:
        pk(reason_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) reason_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            role = custom_get_object(pk, Reason)
            role.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Reason deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Reason Does Not Exist",
                }
            )


class UpdateReason(APIView):
    """
    This PUT function updates a Reason model record according to
    the reason_id passed in url.

    Args:
        pk(reason_id)
    Body:
        Reason model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) reason_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(operation_description="Reason Update API", operation_summary="Reason Update API", request_body=ReasonSerializer)
    def put(self, request, pk):
        try:
            reason = custom_get_object(pk, Reason)
            serializer = CreateReasonSerializer(reason, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Reason updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Reason Does Not Exist",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Reason Does Not Exist",
                }
            )


class ReasonCsvExport(APIView):
    """
    This GET function fetches all the data from REASON model and converts it into CSV file.

    Args:
        pk(reasaon_id)
    Body:
        None
    Returns:
        -HttpResponse
    Authentication:
        None
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="export.csv"'

        all_fields = Reason.objects.all()

        serializer = ReasonSerializer(all_fields, many=True)

        header = ReasonSerializer.Meta.fields

        writer = csv.DictWriter(response, fieldnames=header)

        writer.writeheader()
        for row in serializer.data:
            writer.writerow(row)

        return response


class GetAllReasonType(APIView):
    """
    This GET function fetches all records from ReasonType model and return the data after serializing it.

    Args:
        None
    Body:
        None
    Returns:
        -Ok(HTTP_200_OK)
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
        description="Enter search keyword in form_data ",
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
            page,
            perpage,
            sort_dir,
            sort_field,
        ]
    )
    def get(self, request):
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        try:
            queryset = ReasonType.objects.all()
            reason_obj = queryset.filter(Q(company__url_domain=url_domain) | Q(company=None))
            search_keys = ["reason_name__icontains"]
            data = custom_get_pagination(request, reason_obj, ReasonType, ReasonTypeSerializer, search_keys)
            return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetReasonType(APIView):
    """
    This GET function fetches particular ID record from ReasonType model and return the data after serializing it.

    Args:
        pk(reasontype_id)
    Body:
        None
    Returns:
        -Serialized ReasonType model data of particular ID(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            reason_type = custom_get_object(pk, ReasonType)
            serializer = ReasonTypeSerializer(reason_type)

            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Get ReasonType details successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "ReasonType Does Not Exist",
                }
            )


class CreateReasonType(APIView):
    """
    This POST function creates a ReasonType model records from the data passes in the body.

    Args:
    None
    Body:
        ReasonType model fields
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

    @swagger_auto_schema(
        operation_description="ReasonType Create API",
        operation_summary="ReasonType Create API",
        request_body=ReasonTypeSerializer,
    )
    def post(self, request):
        serializer = ReasonTypeSerializer(
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "ReasonType created successfully",
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


class UpdateReasonType(APIView):
    """
    This PUT function updates particular record by ID from ReasonType model according to the reasontype_id passed in url.

    Args:
        pk(reasontype_id)
    Body:
        None
    Returns:
        -Serialized ReasonType model data of particular record by ID(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="ReasonType update API",
        operation_summary="ReasonType update API",
        request_body=ReasonTypeSerializer,
    )
    def put(self, request, pk):
        try:
            data = request.data

            reason_name = custom_get_object(pk, ReasonType)
            serializer = ReasonTypeSerializer(reason_name, data=data)

            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "ReasonType updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "ReasonType Does Not Exist",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "ReasonType Does Not Exist",
                }
            )


class DeleteReasonType(APIView):
    """
    This DETETE function delete particular record by ID from ReasonType model according to the reasontype_id passed in url.

    Args:
        pk(reasontype_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if reasontype_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(Manual_parameters=ReasonType)
    def delete(self, request, pk, format=None):
        try:
            reason_type = custom_get_object(pk, ReasonType)
            reason_type.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "ReasonType deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "ReasonType Does Not Exist",
                }
            )


class CreateReminder(APIView):
    """
    This POST function creates a Reminder Model record from the data passed in the body.

    Args:
        None
    Body:
        Reminder model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="CreateReminder create API",
        operation_summary="CreateReminder create API",
        request_body=FormSerializer.ReminderSerializer,
    )
    def post(self, request):
        data = request.data
        sender_profile = data.get("sender_profile")
        try:
            sender_profile = decrypt(sender_profile)
        except:
            pass
        data["sender_profile"] = sender_profile
        serializer = FormSerializer.ReminderSerializer(data=data)
        if serializer.is_valid():
            obj = serializer.save()
            form_data = None
            subject = "You have a reminder"
            if obj.position:
                form_data = obj.position.position
                subject = "You have a reminder for position approval"
            if obj.offer:
                form_data = obj.offer.position
                subject = "You have a reminder for offer approval"
            applied_position = AppliedPosition.objects.filter(id=request.data.get("applied_position_id")).last()
            # Send notification and email
            send_reminder(obj.message, obj.reminder_to.user, slug="/position-dashboard", applied_position=applied_position, form_data=form_data)
            send_reminder_email(subject, obj.message, obj.reminder_to.user.email)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Reminder created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Reminder is not valid",
                }
            )


class GetAllReminder(APIView):
    """
    This GET function fetches all records from Reminder model
    after filtering on the basis of fields given in the body
    and return the data after serializing it.

    Args:
        None
    Body:
        - domain (mandatory)
        - form (optional)
        - field_name(optional)
    Returns:
        - Serialized Field model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    profile_id = openapi.Parameter(
        "profile_id",
        in_=openapi.IN_QUERY,
        description="Enter profile_id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[profile_id])
    def get(self, request):
        data = request.GET
        profile_id = data.get("profile_id")
        try:
            profile_id = int(decrypt(profile_id))
        except:
            pass
        try:
            queryset = FormModel.Reminder.objects.all()
            if profile_id:
                queryset = queryset.filter(reminder_to=profile_id)

            data = FormSerializer.GetReminderSerializer(queryset, many=True).data
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Reminder Fetched Successfully.",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Reminder Does Not Exist",
                }
            )


class GetAllInterviews(APIView):
    """
    This GET function fetches all the Scheduled Interviews.

    Args:
        None
    Body:
        None
    Returns:
        -HttpResponse
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="profile id",
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
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[profile, page, perpage, sort_dir, sort_field])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        profile = data.get("profile")

        try:
            profile = int(decrypt(profile))
        except:
            pass

        page = data.get("page", 1)

        search = data.get("search", "")

        limit = data.get("perpage", settings.PAGE_SIZE)

        if data.get("export"):
            export = True
        else:
            export = False

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit
        interviews_data = []
        try:
            queryset = AppliedPosition.objects.all().filter(company__url_domain=url_domain)
            queryset = (
                queryset.filter(data__has_key="interview_schedule_data_list")
                .filter(form_data__status="active")
                .exclude(application_status__in=["reject", "rejected", "offer-decline"])
            )
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=search)
                    | Q(applied_profile__user__email__icontains=search)
                    | Q(form_data__form_data__job_title__icontains=search)
                    | Q(string_id__icontains=search)
                )
            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if profile:
                queryset = queryset.filter(Q(profile=profile))
            # added code recently
            queryset = queryset.select_related("form_data", "applied_profile")
            serialized_interviews = AppliedPositionListSerializer(queryset, many=True).data
            resp_data = []
            for i in serialized_interviews:
                interviewer_list = []
                try:
                    stages = PositionStage.objects.filter(position__id=i["form_data"]["id"]).filter(stage__is_interview=True).order_by("sort_order")
                    for idx, inter in enumerate(i["data"].get("interview_schedule_data_list")):
                        inter_obj = inter["Interviewer"]
                        # get attributes
                        attributes = 0
                        try:
                            for competency in stages[idx].competency.all():
                                for att in competency.attribute.all():
                                    attributes += 1
                        except Exception as e:
                            print(e)
                        total_ratings = attributes * len(inter_obj)
                        if inter["date"] != "":
                            try:
                                # if "start_time" in inter:
                                #     tz = pytz_tz(inter.get("timezone", "Asia/Singapore"))
                                #     stringed_start_time = "{} {}".format(inter["date"], inter["start_time"])
                                #     obj_start_time = datetime.datetime.strptime(stringed_start_time, "%Y-%m-%d %I:%M %p")
                                # interview_time = tz.localize(
                                #     datetime.datetime(
                                #         obj_start_time.year, obj_start_time.month, obj_start_time.day, obj_start_time.hour, obj_start_time.minute
                                #     )
                                # )
                                # current_time = datetime.datetime.now(tz)
                                interviews = []
                                print(
                                    PositionScoreCard.objects.filter(
                                        position__id=i["form_data"]["id"], applied_profiles__id=i["applied_profile"]["id"]
                                    ).count()
                                )
                                if (
                                    total_ratings
                                    > PositionScoreCard.objects.filter(
                                        position__id=i["form_data"]["id"], applied_profiles__id=i["applied_profile"]["id"]
                                    ).count()
                                ):
                                    print("if")
                                    for single_inter in inter["Interviewer"]:
                                        if (
                                            PositionScoreCard.objects.filter(
                                                position__id=i["form_data"]["id"],
                                                interviewer_profile=single_inter["value"],
                                                applied_profiles__id=i["applied_profile"]["id"],
                                            ).count()
                                            < attributes
                                        ):
                                            single_inter["interview_done"] = False
                                        else:
                                            single_inter["interview_done"] = True
                                        if request.user.email in [i["form_data"]["hiring_manager"], i["form_data"]["recruiter"]]:
                                            interviews.append(single_inter)
                                        elif int(request.user.profile.id) in [single_inter["value"]]:
                                            interviews.append(single_inter)
                                if interviews:
                                    inter["Interviewer"] = interviews
                                    interviewer_list.append(inter)
                                else:
                                    inter["Interviewer"] = []
                                """
                                # if (
                                #     PositionScoreCard.objects.filter(
                                #         position__id=i["form_data"]["id"],
                                #         interviewer_profile=request.user.profile,
                                #         applied_profiles__id=i["applied_profile"]["id"],
                                #     ).count()
                                #     < total_ratings
                                # ):
                                #     temp_l = [x["value"] for x in inter["Interviewer"]]
                                #     if request.user.email in [i["form_data"]["hiring_manager"], i["form_data"]["recruiter"]]:
                                #         interviewer_list.append(inter)
                                #     elif int(request.user.profile.id) in temp_l:
                                #         interviewer_list.append(inter)
                                """
                            except Exception as e:
                                print(e)
                except Exception as e:
                    print(e)
                if interviewer_list:
                    i["data"]["interview_schedule_data_list"] = interviewer_list
                    resp_data.append(i)
            count = len(resp_data)
            if count:
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

                    for serializer_data in resp_data:
                        row = []
                        for field in selected_fields:
                            if field.lower() in ["department", "category", "location", "level", "employment type"]:
                                field = form_utils.position_dict.get(field)
                                try:
                                    value = serializer_data["form_data"]["form_data"].get(field)[0].get("label")
                                    if value is None:
                                        value = serializer_data["form_data"]["form_data"].get(field).get("name")
                                except Exception as e:
                                    value = None
                            elif field in ["Position Name", "Job Title"]:
                                value = data["form_data"]["form_data"].get("job_title")
                            elif field == "Country":
                                data["form_data"]["form_data"].get("country").get("name")
                            elif field == "Candidate Name":
                                value = serializer_data["applied_profile"]["user"]["first_name"]
                            elif field == "Interviewer":
                                try:
                                    value = serializer_data["data"]["interview_schedule_data"]["Interviewer"][0]["label"]
                                except:
                                    print(serializer_data["data"]["interview_schedule_data"])
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
                    if page and limit:
                        resp_data = resp_data[skip : skip + limit]

                        pages = math.ceil(count / limit) if limit else 1
                    serializer = resp_data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Interviews Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpInterviews(APIView):
    """
    This GET function fetches all the Scheduled Interviews.

    Args:
        None
    Body:
        None
    Returns:
        -HttpResponse
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="profile id",
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
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[profile, page, perpage, sort_dir, sort_field])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        profile = data.get("profile")

        try:
            profile = int(decrypt(profile))
        except:
            pass

        page = data.get("page", 1)

        search = data.get("search", "")

        limit = data.get("perpage", settings.PAGE_SIZE)

        if data.get("export"):
            export = True
        else:
            export = False

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit
        interviews_data = []
        try:
            queryset = AppliedPosition.objects.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            queryset = (
                queryset.filter(data__has_key="interview_schedule_data_list")
                .filter(form_data__status="active")
                .exclude(application_status__in=["reject", "rejected", "offer-decline"])
            )
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=search)
                    | Q(applied_profile__user__email__icontains=search)
                    | Q(form_data__form_data__job_title__icontains=search)
                    | Q(string_id__icontains=search)
                )
            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if profile:
                queryset = queryset.filter(Q(profile=profile))
            # added code recently
            queryset = queryset.select_related("form_data", "applied_profile")
            # serialized_interviews = AppliedPositionListSerializer(queryset, many=True).data
            resp_data = []
            for i in queryset:
                interviewer_list = []
                try:
                    stages = PositionStage.objects.filter(position__id=i.form_data.id).filter(stage__is_interview=True).order_by("sort_order")
                    for idx, inter in enumerate(i.data.get("interview_schedule_data_list")):
                        inter_obj = inter["Interviewer"]
                        # get attributes
                        attributes = 0
                        try:
                            for competency in stages[idx].competency.all():
                                for att in competency.attribute.all():
                                    attributes += 1
                        except Exception as e:
                            print(e)
                        total_ratings = attributes * len(inter_obj)
                        if inter["date"] != "":
                            try:
                                interviews = []
                                if (
                                    total_ratings
                                    > PositionScoreCard.objects.filter(position__id=i.form_data.id, applied_profiles__id=i.applied_profile.id).count()
                                ):
                                    for single_inter in inter["Interviewer"]:
                                        if (
                                            PositionScoreCard.objects.filter(
                                                position__id=i.form_data.id,
                                                interviewer_profile=single_inter["value"],
                                                applied_profiles__id=i.applied_profile.id,
                                            ).count()
                                            < attributes
                                        ):
                                            single_inter["interview_done"] = False
                                        else:
                                            single_inter["interview_done"] = True
                                        print(request.user.email, [i.form_data.hiring_manager, i.form_data.recruiter])
                                        if request.user.email in [i.form_data.hiring_manager, i.form_data.recruiter]:
                                            interviews.append(single_inter)
                                        elif int(request.user.profile.id) in [single_inter["value"]]:
                                            interviews.append(single_inter)
                                print(interviews)
                                if interviews:
                                    for j in interviews:
                                        try:
                                            j["profile_id"] = encrypt(j["profile_id"])
                                        except:
                                            pass

                                    inter["Interviewer"] = interviews
                                    interviewer_list.append(inter)
                                else:
                                    inter["Interviewer"] = []
                            except Exception as e:
                                print(e)
                except Exception as e:
                    print(e)
                if interviewer_list:
                    temp_data = {}
                    temp_data["applied_profile"] = i.id
                    temp_data["user_applied_id"] = encrypt(i.applied_profile.id)
                    temp_data["id"] = i.id
                    temp_data["position_id"] = i.form_data.id
                    temp_data["sposition_id"] = i.form_data.show_id
                    temp_data["position_no"] = i.form_data.id
                    temp_data["position_name"] = i.form_data.form_data.get("job_title")
                    temp_data["candidate_name"] = i.applied_profile.user.get_full_name()
                    try:
                        user_obj = User.objects.get(email__iexact=i.form_data.recruiter, user_company=i.form_data.company)
                        temp_data["recruiter"] = user_obj.get_full_name()
                    except:
                        temp_data["recruiter"] = i.form_data.recruiter
                    try:
                        user_obj = User.objects.get(email__iexact=i.form_data.hiring_manager, user_company=i.company)
                        temp_data["hiring_manager"] = user_obj.get_full_name()
                    except:
                        temp_data["hiring_manager"] = i.form_data.hiring_manager
                    temp_data["source"] = i.applicant_details.get("source")
                    temp_data["interviewer"] = interviewer_list
                    resp_data.append(temp_data)
            count = len(resp_data)
            if count:
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                    if selected_fields:
                        selected_fields = selected_fields.last().selected_fields
                    else:
                        selected_fields = ["Hiring Manager", "Position No", "Job Title"]
                    writer.writerow(selected_fields)

                    for serializer_data in resp_data:
                        row = []
                        row.append((serializer_data["sposition_id"]))
                        row.append((serializer_data["position_name"]))
                        row.append((serializer_data["source"]))
                        row.append((serializer_data["candidate_name"]))
                        row.append((serializer_data["interviewer"]))
                        writer.writerow(row)
                    response = HttpResponse(csv_response, content_type="text/csv")
                    return response
                else:
                    if page and limit:
                        resp_data = resp_data[skip : skip + limit]
                        pages = math.ceil(count / limit) if limit else 1
                    serializer = resp_data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Interviews Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetFilteredInterviews(APIView):
    """
    This GET function fetches all the Scheduled Interviews.

    Args:
        None
    Body:
        None
    Returns:
        -HttpResponse
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="profile id",
        type=openapi.TYPE_STRING,
    )
    start_date = openapi.Parameter(
        "start_date",
        in_=openapi.IN_QUERY,
        description="start_date",
        type=openapi.TYPE_STRING,
    )
    end_date = openapi.Parameter(
        "end_date",
        in_=openapi.IN_QUERY,
        description="end_date",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[profile, start_date, end_date])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        if data.get("start_date") is not None:
            start_date = data.get("start_date")
        else:
            raise serializers.ValidationError("start_date field required")

        if data.get("end_date") is not None:
            end_date = data.get("end_date")
        else:
            raise serializers.ValidationError("end_date field required")

        profile_obj = Profile.objects.get(user=request.user.id)
        profile = profile_obj.id
        result = {}

        try:
            queryset = AppliedPosition.objects.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            queryset = (
                queryset.filter(data__has_key="interview_schedule_data_list", form_data__status="active")
                .exclude(application_status__in=["cancelled"])
                .exclude(application_status__in=["reject", "rejected", "offer-decline"])
            )
            queryset = queryset.select_related("form_data", "applied_profile")
            st = start_date.split("-")
            end = end_date.split("-")
            start_date = date(int(st[0]), int(st[1]), int(st[2]))
            end_date = date(int(end[0]), int(end[1]), int(end[2]))
            for n in range(0, int((end_date - start_date).days) + 1):
                res_1 = []
                dt = str(start_date + timedelta(n))
                res = []
                for q in queryset:
                    for inter in q.data["interview_schedule_data_list"]:
                        if inter["date"] == dt:
                            if q not in res:
                                res.append(q)
                serialized_res = AppliedPositionListSerializer(res, many=True).data
                ser = serialized_res
                if profile is not None:
                    for i in ser:
                        # Get total attributes
                        new_inter = []
                        for inter in i["data"]["interview_schedule_data_list"]:
                            inter_obj = inter["Interviewer"]
                            try:
                                new_interviewers = []
                                for j in inter_obj:
                                    if int(profile) == j["value"]:
                                        new_interviewers.append(j)
                                inter["Interviewer"] = new_interviewers
                                if new_interviewers:
                                    new_inter.append(inter)
                            except Exception as e:
                                print(e)
                        if new_inter:
                            i["data"]["interview_schedule_data_list"] = new_inter
                            res_1.append(i)
                    result[dt] = res_1
                else:
                    result[dt] = ser
            count = queryset.count()
            if count:
                return ResponseOk(
                    {
                        "data": result,
                    }
                )
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Interviews Does Not Exist",
                }
            )
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetCandidateRatingReview(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    is_employee = openapi.Parameter(
        "is_employee",
        in_=openapi.IN_QUERY,
        description="Enter search keyword for candidate review rating",
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
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[is_employee, page, perpage, sort_dir, sort_field])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET

        if request.headers.get("domain") is not None:
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
        if data.get("export"):
            export = True
        else:
            export = False
        if data.get("search"):
            search = data.get("search")
        else:
            search = ""

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        is_employee = data.get("is_employee")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        try:
            queryset = (
                AppliedPosition.objects.filter(form_data__status="active")
                .filter(Q(company__url_domain=url_domain) | Q(company=None))
                .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
            ).exclude(application_status="reject")

            queryset_ids = []
            for ap in queryset.filter(form_data__status="active").exclude(application_status="reject"):
                last_stage = ap.data["history_detail"][-1]
                if last_stage["name"] in ["Resume Review"]:
                    queryset_ids.append(ap.id)
            queryset = AppliedPosition.objects.filter(id__in=queryset_ids)
            if is_employee is not None and is_employee == "true":
                queryset = queryset.exclude(Q(applied_profile__user__user_role__name__in=["candidate", "guest"]))
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=search)
                    | Q(applied_profile__user__email__icontains=search)
                    | Q(form_data__form_data__job_title__icontains=search)
                    | Q(string_id__icontains=search)
                )
            queryset = queryset.prefetch_related("form_data", "applied_profile")
            data = FormSerializer.ResumeReviewSerialzer(queryset, many=True).data
            count = queryset.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if page and limit:
                queryset = queryset[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if count:
                context = {"request": request}
                queryset = queryset.prefetch_related("form_data", "applied_profile")
                serializer_data = FormSerializer.ResumeReviewSerialzer(queryset, many=True, context=context).data
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                    if selected_fields:
                        selected_fields = selected_fields.last().selected_fields
                    else:
                        selected_fields = ["Position No", "Candidate Name", "Job Title", "Status"]
                    writer.writerow(selected_fields)

                    for data in queryset:
                        data = data.prefetch_related("form_data", "applied_profile")
                        serializer_data = FormSerializer.ResumeReviewSerialzer(data).data
                        row = []
                        for field in selected_fields:
                            if field.lower() in ["department", "category", "location", "level", "employment type"]:
                                field = form_utils.position_dict.get(field)
                                try:
                                    value = data.form_data.form_data.get(field)[0].get("label")
                                    if value is None:
                                        value = data.form_data.form_data.get(field).get("name")
                                except Exception as e:
                                    value = None
                            elif field in ["Position Name", "Job Title"]:
                                value = data.form_data.form_data.get("job_title")
                            elif field == "Country":
                                data.form_data.form_data.get("country").get("name")
                            elif field == "Candidate Name":
                                value = serializer_data["applied_profile"]["user"]["first_name"]
                            elif field == "Email":
                                value = serializer_data["applied_profile"]["user"]["email"]
                            elif field == "Interviewer":
                                try:
                                    value = serializer_data["data"]["interview_schedule_data"]["Interviewer"][0]["label"]
                                except:
                                    print(serializer_data["data"]["interview_schedule_data"])
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
                            "data": serializer_data,
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

            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Candidate Review Rating Fetched Successfully.",
                }
            )
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Candidate Review Rating Does Not Exist",
                }
            )


class GetOpCandidateRatingReview(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    is_employee = openapi.Parameter(
        "is_employee",
        in_=openapi.IN_QUERY,
        description="Enter search keyword for candidate review rating",
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
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[is_employee, page, perpage, sort_dir, sort_field])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET

        if request.headers.get("domain") is not None:
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
        if data.get("export"):
            export = True
        else:
            export = False
        if data.get("search"):
            search = data.get("search")
        else:
            search = ""

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        is_employee = data.get("is_employee")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        try:
            queryset = (
                AppliedPosition.objects.filter(form_data__status="active")
                .filter(Q(company__url_domain=url_domain) | Q(company=None))
                .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
            ).exclude(application_status="reject")

            queryset_ids = []
            for ap in queryset.filter(form_data__status="active").exclude(application_status="reject"):
                last_stage = ap.data["history_detail"][-1]
                if last_stage["name"] in ["Resume Review"]:
                    queryset_ids.append(ap.id)
            queryset = AppliedPosition.objects.filter(id__in=queryset_ids)
            if is_employee is not None and is_employee == "true":
                queryset = queryset.exclude(Q(applied_profile__user__user_role__name__in=["candidate", "guest"]))
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=search)
                    | Q(applied_profile__user__email__icontains=search)
                    | Q(form_data__form_data__job_title__icontains=search)
                    | Q(string_id__icontains=search)
                )
            queryset = queryset.prefetch_related("form_data", "applied_profile")
            # data = FormSerializer.ResumeReviewSerialzer(queryset, many=True).data
            count = queryset.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if page and limit:
                queryset = queryset[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if count:
                context = {"request": request}
                queryset = queryset.prefetch_related("form_data", "applied_profile")
                # serializer_data = FormSerializer.ResumeReviewSerialzer(queryset, many=True, context=context).data
                if export:
                    select_type = request.GET.get("select_type")
                    csv_response = HttpResponse(content_type="text/csv")
                    csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                    writer = csv.writer(csv_response)
                    fields = ["Position No", "Position Name", "Candidate Name", "Recruiter"]
                    writer.writerow(fields)

                    for i in queryset:
                        row = []
                        row.append(i.form_data.show_id)
                        row.append(i.form_data.form_data["job_title"])
                        row.append(i.applied_profile.user.get_full_name())
                        try:
                            user_obj = User.objects.get(email__iexact=i.form_data.recruiter, user_company=i.form_data.company)
                            row.append(user_obj.get_full_name())
                        except:
                            row.append(i.form_data.recruiter)
                        writer.writerow(row)
                    response = HttpResponse(csv_response, content_type="text/csv")
                    return response
                else:
                    data = []
                    for i in queryset:
                        temp_data = {}
                        temp_data["position_id"] = i.form_data.id
                        temp_data["sposition_id"] = i.form_data.show_id
                        temp_data["position_name"] = i.form_data.form_data["job_title"]
                        temp_data["candidate_name"] = i.applied_profile.user.get_full_name()
                        temp_data["applied_profile"] = i.id
                        temp_data["user_applied_id"] = encrypt(i.applied_profile.id)
                        try:
                            user_obj = User.objects.get(email__iexact=i.form_data.hiring_manager, user_company=i.form_data.company)
                            temp_data["hiring_manager"] = user_obj.get_full_name()
                        except:
                            temp_data["hiring_manager"] = i.form_data.hiring_manager
                        try:
                            user_obj = User.objects.get(email__iexact=i.form_data.recruiter, user_company=i.form_data.company)
                            temp_data["recruiter"] = user_obj.get_full_name()
                        except:
                            temp_data["recruiter"] = i.form_data.recruiter
                        data.append(temp_data)
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

            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Candidate Review Rating Fetched Successfully.",
                }
            )
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Candidate Review Rating Does Not Exist",
                }
            )


class GetOfferList(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        try:
            queryset = AppliedPosition.objects.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            queryset = queryset.filter(data__has_key="offer")
            data = FormSerializer.AppliedPositionRatingListSerializer(queryset, many=True).data

            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Offer Letter List Fetched Successfully.",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Offer Letter List Does Not Exist",
                }
            )


class GetDashboard(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    profile_id = openapi.Parameter(
        "profile_id",
        in_=openapi.IN_QUERY,
        description="filter form_data by created_by_profile",
        type=openapi.TYPE_STRING,
    )
    own_data = openapi.Parameter(
        "own_data",
        in_=openapi.IN_QUERY,
        description="filter on the basis of own_data",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[profile_id, own_data])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        if data.get("profile_id"):
            profile_id = data.get("profile_id")
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
        else:
            profile_id = None

        if data.get("own_data"):
            own_data = data.get("own_data")
        else:
            own_data = None

        # Internal Applicants
        internal_obj = AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None), form_data__status="active").filter(
            Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email)
        )
        internal_obj = internal_obj.exclude(Q(applied_profile__user__user_role__name__in=["candidate", "guest"])).filter(
            application_status__in=["active", "approved", "pending", "pending-offer", "offer-rejected"]
        )
        if profile_id:
            pro_obj = Profile.objects.get(id=profile_id)
        else:
            pro_obj = request.user.profile
        if request.user.user_role.name == "recruiter" and own_data == "false":
            all_status_position = FormData.objects.filter(company__url_domain=url_domain)
        else:
            if own_data == "true":
                all_status_position = FormData.objects.filter(company__url_domain=url_domain).filter(
                    Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email)
                )
            else:
                form_data = FormData.objects.filter(company__url_domain=url_domain)
                temp_form_data = form_data
                own_form_data = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                teams_obj, created = Team.objects.get_or_create(manager=pro_obj)
                members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
                members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
                all_status_position = members_fd_obj | own_form_data
        # Closed Position
        closed_obj = all_status_position.filter(status__in=["closed", "canceled"])

        # Pending Position
        pending_obj = all_status_position.filter(status="draft")

        # Logged In Interviews
        queryset = AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
        interviewers = queryset.filter(data__has_key="interview_schedule_data_list")
        active_interviewers = interviewers.filter(form_data__status="active").exclude(application_status__in=["reject", "rejected", "offer-decline"])
        res = request.user.profile.id
        # serialized_res = AppliedPositionListSerializer(active_interviewers, many=True).data
        count_interviewrs = 0
        logged_interviews = 0
        for i in active_interviewers:
            interviewer_list = []
            try:
                stages = PositionStage.objects.filter(position__id=i.form_data.id).filter(stage__is_interview=True).order_by("sort_order")
                for idx, stage_inter in enumerate(i.data.get("interview_schedule_data_list", [])):
                    inter_obj = stage_inter["Interviewer"]
                    # get attributes
                    attributes = 0
                    try:
                        for competency in stages[idx].competency.all():
                            for att in competency.attribute.all():
                                attributes += 1
                    except Exception as e:
                        print(e)
                    total_ratings = attributes * len(inter_obj)
                    if stage_inter["date"] != "":
                        try:
                            if "start_time" in stage_inter:
                                tz = pytz_tz(stage_inter.get("timezone", "Asia/Singapore"))
                                stringed_start_time = "{} {}".format(stage_inter["date"], stage_inter["start_time"])
                                obj_start_time = datetime.datetime.strptime(stringed_start_time, "%Y-%m-%d %I:%M %p")
                            interview_time = tz.localize(
                                datetime.datetime(
                                    obj_start_time.year, obj_start_time.month, obj_start_time.day, obj_start_time.hour, obj_start_time.minute
                                )
                            )
                            current_time = datetime.datetime.now(tz)
                            if (
                                interview_time.year >= current_time.year
                                and interview_time.month >= current_time.month
                                and interview_time.day >= current_time.day
                                and PositionScoreCard.objects.filter(
                                    position__id=i.form_data.id,
                                    interviewer_profile=request.user.profile,
                                    applied_profiles__id=i.applied_profile.id,
                                ).count()
                                < total_ratings
                            ):
                                temp_l = [x["value"] for x in stage_inter["Interviewer"]]
                                if int(res) in temp_l:
                                    logged_interviews += 1
                        except Exception as e:
                            print(e)
            except Exception as e:
                print(e)
        # CandidateReview
        queryset_obj = AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None)).filter(
            Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email)
        )
        canditate_review = 0
        for ap in queryset_obj.filter(form_data__status="active").exclude(application_status="reject"):
            last_stage = ap.data["history_detail"][-1]
            if last_stage["name"] in ["Resume Review"]:
                canditate_review += 1

        # PositionApprovalCount
        result = Profile.objects.get(user=request.user.id)
        queryset_obj = PositionApproval.objects.filter(Q(company__url_domain=url_domain) | Q(company=None)).filter(position__status="draft")
        position_approvals = (
            queryset_obj.filter(Q(position__recruiter=request.user.email) | Q(position__hiring_manager=request.user.email))
            .exclude(Q(is_approve=True) | Q(is_reject=True))
            .distinct("position")
            .count()
        )
        queryset_object = queryset_obj.exclude(is_approve=True).exclude(is_reject=True).exclude(show=False)
        queryset_obj = queryset_object.filter(profile=result.id).count()
        # OfferApprovalCount
        result_1 = Profile.objects.get(user=request.user.id)
        queryset_obj1 = (
            OfferApproval.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
            .filter(position__status__in=["active", "hold", "draft"])
            .distinct("position")
        )
        offer_approvals = queryset_obj1.filter(Q(position__recruiter=request.user.email) | Q(position__hiring_manager=request.user.email)).exclude(
            Q(is_approve=True) | Q(is_reject=True)
        )
        offer_approvals_count = 0
        for query in offer_approvals:
            if (
                OfferLetter.objects.filter(offered_to__form_data=query.position)
                .exclude(Q(is_decline=True) | Q(withdraw=True))
                .exclude(offered_to__application_status="offer-rejected")
            ):
                offer_approvals_count += 1
        queryset_obj2 = queryset_obj1.exclude(is_approve=True).exclude(is_reject=True).exclude(show=False)
        queryset_obj2 = queryset_obj2.filter(profile=result_1.id)
        queryset_obj2_list = []
        for query in queryset_obj2:
            if (
                OfferLetter.objects.filter(offered_to__form_data=query.position)
                .exclude(Q(is_decline=True) | Q(withdraw=True))
                .exclude(offered_to__application_status="offer-rejected")
            ):
                queryset_obj2_list.append(query)
        queryset_obj1 = len(queryset_obj2_list)
        # PositionApproval and OfferApproval Count

        approval = queryset_obj + queryset_obj1
        # Employee Referral
        queryset_data = AppliedPosition.objects.filter(form_data__company__url_domain=url_domain, form_data__status="active")
        if request.user.user_role.name in ["hiring manager", "recruiter"]:
            queryset_data = queryset_data.filter(
                Q(form_data__hiring_manager=request.user.email)
                | Q(form_data__recruiter=request.user.email)
                | Q(refereed_by_profile__name=request.user.get_full_name())
            )
        else:
            queryset_data = queryset_data.filter(
                Q(refereed_by_profile__name=request.user.get_full_name()) | Q(refereed_by_profile__value=request.user.profile.id)
            )

        # queryset_data = queryset_data.filter(Q(refereed_by_profile__isnull=False)).exclude(refereed_by_profile={})
        # referral_data = queryset_data.exclude(refereed_by_profile__name=[None, '', {'key': 'value'}])
        referral_data = queryset_data.exclude(refereed_by_profile__name=[None, "", {"key": "value"}])
        emp_ref_counts = 0
        for i in referral_data:
            try:
                ref_id = i.refereed_by_profile["value"]
                profile_obj = Profile.objects.get(id=ref_id)
                if profile_obj.user.user_role.name not in ["candidate", "guest"]:
                    emp_ref_counts += 1
            except Exception as e:
                print(e, i.id)
        # Job Posting
        job_posting_data = all_status_position.filter(status="active").filter(Q(candidate_visibility=True) | Q(employee_visibility=True))

        # Positions
        position_count = all_status_position.filter(status="active").count()

        # if is_recruiter == "true":
        #     own_open_count = own_obj.filter(status="active").count()
        #     own_pending_count = own_obj.filter(status="draft").count()
        #     own_closed_count = own_obj.filter(status="closed").count()
        # else:
        #     own_open_count = own_obj.filter(status="active", created_by_profile=profile_id).count()
        #     own_pending_count = own_obj.filter(status="draft", created_by_profile=profile_id).count()
        #     own_closed_count = own_obj.filter(status="closed", created_by_profile=profile_id).count()

        own_open_count = all_status_position.filter(status="active").count()
        own_pending_count = all_status_position.filter(status="draft").count()
        own_closed_count = all_status_position.filter(status__in=["closed", "canceled"]).count()
        hold_positions = all_status_position.filter(status="hold").count()
        open_count = all_status_position.filter(status="active").count()

        pending_interviewer_list = []
        applied_position_list = []
        all_applied_position_list = []

        try:
            interviewer_obj = Profile.objects.get(id=profile_id).user
        except User.DoesNotExist:
            return ResponseBadRequest(
                {
                    "data": data,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Entered Profile Not Found",
                }
            )

        application_obj = AppliedPosition.objects.filter(
            company=interviewer_obj.user_company.id, application_status="active", form_data__status="active"
        )
        # print(application_obj)
        # if request.user.user_role.name.lower() == "interviewer":
        #     pass
        # else:
        #     application_obj = application_obj.filter(
        #         Q(form_data__recruiter=interviewer_obj.email) | Q(form_data__hiring_manager=interviewer_obj.email)
        #     )
        # print(application_obj)
        for application in set(application_obj):
            for stage_interview in application.data.get("interview_schedule_data_list", []):
                try:
                    interviewer_ids = stage_interview["Interviewer"]
                except Exception as e:
                    interviewer_ids = []
                for interviewer in interviewer_ids:
                    try:
                        int_id = interviewer["profile_id"]
                    except Exception as e:
                        int_id = 0

                    if application.data.get("interview_cancelled", False) == False:
                        if "start_time" in stage_interview:
                            inter_timezone = stage_interview.get("timezone", "Asia/Singapore")
                            tz = pytz_tz(inter_timezone)
                            stringed_start_time = "{} {}".format(stage_interview["date"], stage_interview["start_time"])
                            obj_start_time = datetime.datetime.strptime(stringed_start_time, "%Y-%m-%d %I:%M %p")
                        interview_time = tz.localize(
                            datetime.datetime(
                                obj_start_time.year, obj_start_time.month, obj_start_time.day, obj_start_time.hour, obj_start_time.minute
                            )
                        )
                        current_time = datetime.datetime.now(tz)

                    # score_obj = PositionScoreCard.objects.filter(
                    #     position=application.form_data,
                    #     applied_profiles=application.applied_profile,
                    #     interviewer_profile__id=interviewer["profile_id"],
                    # )
                    # #
                    if get_complete_feedback(application, int_id) == False and application.data.get("interview_cancelled", False) == False:
                        if "start_time" in stage_interview:
                            inter_timezone = stage_interview.get("timezone", "Asia/Singapore")
                            tz = pytz_tz(inter_timezone)
                            stringed_start_time = "{} {}".format(stage_interview["date"], stage_interview["start_time"])
                            obj_start_time = datetime.datetime.strptime(stringed_start_time, "%Y-%m-%d %I:%M %p")
                        interview_time = tz.localize(
                            datetime.datetime(
                                obj_start_time.year, obj_start_time.month, obj_start_time.day, obj_start_time.hour, obj_start_time.minute
                            )
                        )
                        current_time = datetime.datetime.now(tz)
                        if current_time > interview_time + datetime.timedelta(minutes=1):
                            pending_interviewer_list.append(interviewer["profile_id"])
                            if int(profile_id) == int(int_id):
                                applied_position_list.append(application)
                            if request.user.email in [application.form_data.recruiter, application.form_data.hiring_manager]:
                                all_applied_position_list.append(application)

        pending_decision = (
            AppliedPosition.objects.filter(company=interviewer_obj.user_company.id, application_status__in=["pending", "kiv"])
            .filter(Q(form_data__hiring_manager=interviewer_obj.email) | Q(form_data__recruiter=interviewer_obj.email))
            .filter(form_data__status="active")
            .count()
        )
        pending_score_card_count = len(list(set(applied_position_list)))
        offer_count = 0
        offer_application_obj = (
            AppliedPosition.objects.filter(company=interviewer_obj.user_company.id, application_status__in=["pending-offer", "approved", "offer"])
            .filter(Q(form_data__hiring_manager=interviewer_obj.email) | Q(form_data__recruiter=interviewer_obj.email))
            .filter(form_data__status="active")
        )
        offer_count = offer_application_obj.count()

        # get new hires
        if request.user.user_role.name == "recruiter":
            new_hires = (
                OfferLetter.objects.filter(offered_to__company=request.user.user_company, accepted=True)
                .filter(has_joined=True, email_changed=False)
                .count()
            )
        else:
            new_hires = (
                OfferLetter.objects.filter(offered_to__company=interviewer_obj.user_company, accepted=True)
                .filter(Q(offered_to__form_data__hiring_manager=request.user.email) | Q(offered_to__form_data__recruiter=request.user.email))
                .filter(has_joined=True, email_changed=False)
                .count()
            )
        data = {}
        data["own_active_jobs"] = own_open_count
        data["pending_scorecard"] = pending_score_card_count
        data["all_applied_position_list"] = len(list(set(all_applied_position_list)))
        data["Positions"] = position_count
        data["Open_Positions"] = open_count
        data["own_pending_jobs"] = own_pending_count
        data["own_closed_jobs"] = own_closed_count
        data["Job_Posting"] = job_posting_data.count()
        data["Interviews"] = logged_interviews
        data["Employee_Referrals"] = emp_ref_counts
        data["Offer"] = offer_count
        data["Internal_Applicants"] = internal_obj.count()
        data["Closed_Position"] = closed_obj.count()
        data["Pending_Position"] = pending_obj.count()
        data["approvals"] = approval
        data["candidates_to_review"] = canditate_review
        data["interviews"] = logged_interviews
        data["logged_in_interviews"] = logged_interviews
        data["pending_decisions"] = pending_decision
        data["new_hires"] = new_hires
        data["hold_positions"] = hold_positions
        data["position_approvals"] = position_approvals
        data["offer_approvals"] = offer_approvals_count
        return ResponseOk(
            {
                "data": data,
                "code": status.HTTP_200_OK,
                "message": "Fetched Successfully.",
            }
        )


# class ActivityCount(APIView):
#     permission_classes = [permissions.IsAuthenticated]
#     authentication_classes = [authentication.JWTAuthentication]

#     domain = openapi.Parameter(
#         "domain",
#         in_=openapi.IN_QUERY,
#         description="Enter search keyword for count review",
#         type=openapi.TYPE_STRING,
#     )
#     @swagger_auto_schema(manual_parameters=[domain])
#     @csrf_exempt
#     def get(self, request):
#         data=request.GET
#         if data.get("domain") is not None:
#             url_domain = data.get("domain")
#         else:
#             raise serializers.ValidationError("domain field required")
#         queryset=AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
#         interviewers=queryset.filter(data__has_key="interview_schedule_data")
#         res=Profile.objects.get(user=request.user.id)
#         queryset=AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
#         logged_in_interviewers=interviewers.filter(data__interview_schedule_data__Interviewer=str(res.id))
#         queryset_obj = AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
#         canditate_review=queryset_obj
#         queryset_obj=PositionApproval.objects.filter(Q(company__url_domain=url_domain) | Q(company=None)).count()
#         queryset_obj1=OfferApproval.objects.filter(Q(company__url_domain=url_domain) | Q(company=None)).count()
#         approval=queryset_obj+queryset_obj1
#         data={}
#         data["approvals"]=approval
#         data["candidates_to_review"]=canditate_review.count()
#         data["interviews"]=interviewers.count()
#         data["logged_in_interviews"]=logged_in_interviewers.count()
#         data["pending_scorecard"]=0
#         data["pending_decisions"]=0
#         data["new_hires"]=0
#         return ResponseOk(
#                 {
#                     "data": data,
#                     "code": status.HTTP_200_OK,
#                     "message": "Fetched Successfully.",
#                 }
#             )


class GetJobBoardTemplate(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request):
        data = FormModel.JobBoardTemplate.objects.all()
        serializer = FormSerializer.JobBoardTemplateSerializer(data, many=True)
        return ResponseOk(
            {
                "data": serializer.data,
                "code": status.HTTP_200_OK,
                "message": "Job Board Template Get Successfully",
            }
        )


class GetInternalJobListing(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.FormData.objects.all()
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

    @swagger_auto_schema(manual_parameters=[page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
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

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        try:
            queryset = self.queryset.all().filter(company__url_domain=url_domain)

            queryset = queryset.filter(status="active", candidate_visibility=True)
            # print(queryset)
            count = queryset.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if page and limit:
                queryset = queryset[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if count:
                context = {"request": request}
                serializer = FormSerializer.FormDataListSerializer(queryset, many=True, context=context).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Internal Jobs Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetExternalJobListing(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.FormData.objects.all()
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

    @swagger_auto_schema(manual_parameters=[page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET

        if request.headers.get("domain") is not None:
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

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        try:
            queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None))

            queryset = queryset.filter(status="active", employee_visibility=True)
            count = queryset.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if page and limit:
                queryset = queryset[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if count:
                context = {"request": request}
                serializer = FormSerializer.FormDataListSerializer(queryset, many=True, context=context).data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "External Jobs Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetDataForNextCandidate(APIView):
    """
    This GET function fetches all records from Applied Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - status(optional)
        - form_data(optional)
        - profile(optional)
        - page(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized Applied Position Model model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Applied Position Model Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.AppliedPosition.objects.all()
    applied_profile = openapi.Parameter(
        "applied_profile",
        in_=openapi.IN_QUERY,
        description="applied_profile id(candidate id)",
        type=openapi.TYPE_STRING,
    )
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by candidate name and job title",
        type=openapi.TYPE_STRING,
    )
    form_data = openapi.Parameter(
        "form_data",
        in_=openapi.IN_QUERY,
        description="form_data id (Position id)",
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

    @swagger_auto_schema(manual_parameters=[applied_profile, search, form_data, page, perpage, sort_dir, sort_field])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        if data.get("form_data"):
            form_data = data.get("form_data")
        else:
            form_data = ""
        if data.get("search") is not None:
            search = data.get("search")
        else:
            search = ""
        if data.get("applied_profile"):
            applied_profile = data.get("applied_profile")
            try:
                applied_profile = int(decrypt(applied_profile))
            except:
                pass
        else:
            raise serializers.ValidationError("applied profile required")

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        try:
            queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            if form_data:
                queryset = queryset.filter(Q(form_data=form_data))

            queryset = sort_data(queryset, sort_field, sort_dir)
            search_keys = [
                "applied_profile__user__first_name__icontains",
                "applied_profile__user__last_name__icontains",
                "applied_profile__user__middle_name__icontains",
            ]
            queryset = search_data(queryset, FormModel.AppliedPosition, search, search_keys)
            pagination_data = paginate_data(request, queryset, FormModel.AppliedPosition)
            queryset = pagination_data.get("paginate_data")
            if queryset:
                # serializer = FormSerializer.AppliedPositionListSerializer(queryset, many=True).data

                count = 0
                for i in queryset:
                    if i.applied_profile.id == int(applied_profile):
                        count = count + 1
                        break
                    else:
                        count = count + 1
                try:
                    if count < queryset.count():
                        res = queryset[count]
                        res_data = {}
                        res_data["applied_profile"] = {}
                        res_data["applied_profile"]["id"] = res.applied_profile.id
                        res_data["id"] = res.id
                        res_data["sposition_id"] = res.form_data.id
                    else:
                        res_data = None
                except:
                    res_data = None

                previous_count = 0
                current_index = None
                for i in queryset:
                    if i.applied_profile.id == int(applied_profile):
                        previous_count = previous_count + 1
                        current_index = previous_count
                        break
                    else:
                        previous_count = previous_count + 1
                try:
                    if current_index - 2 > -1:
                        result = queryset[current_index - 2]
                        result_data = {}
                        result_data["applied_profile"] = {}
                        result_data["applied_profile"]["id"] = result.applied_profile.id
                        result_data["id"] = result.id
                        result_data["sposition_id"] = result.form_data.id
                    else:
                        result_data = None
                except:
                    result_data = None

                current_user = AppliedPosition.objects.get(applied_profile=applied_profile, form_data=form_data)
                current_user_data = FormSerializer.AppliedPositionListSerializer(current_user).data
                current_user_data["sposition_id"] = current_user.form_data.show_id
                return ResponseOk(
                    {
                        "data": res_data,
                        "previous_data": result_data,
                        "current_user": current_user_data,
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateJobDescriptionImage(APIView):
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="Job Description Image create API",
        operation_summary="Job Description Image create API",
        request_body=FormSerializer.JobDescriptionImagesSerializer,
    )
    def post(self, request):
        request.data["Image_file"] = request.data["upload"]
        ts = time.time_ns()
        name = ""
        url_name = request.data["Image_file"].name
        listed_url_name = url_name.rpartition(".")

        if listed_url_name[0]:
            name = "{}-{}{}{}".format(listed_url_name[0], str(ts), listed_url_name[1], listed_url_name[2])
        request.data["Image_file"].name = name
        serializer = FormSerializer.JobDescriptionImagesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            res = {}
            res["fileName"] = request.data["Image_file"].name
            res["uploaded"] = 1
            res["url"] = serializer.data["Image_file"]

            return Response(res)
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Job Description Image is not valid",
                }
            )


class GetResumeReviewList(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        try:
            queryset = AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
            stage_obj = Stage.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
            stage_data = stage_obj.filter(stage_name="Resume Review")[0]
            queryset_data = queryset.filter(data__current_stage_id=stage_data.id)
            data = FormSerializer.AppliedPositionRatingListSerializer(queryset_data, many=True).data

            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Resume Review List Fetched Successfully.",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Resume Review List Does Not Exist",
                }
            )


class GetCandidateActivityList(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    applied_position_id = openapi.Parameter(
        "applied_position_id",
        in_=openapi.IN_QUERY,
        description="Enter applied position id for get candidate activity list",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[applied_position_id])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET

        if data.get("applied_position_id") is not None:
            applied_position_id = data.get("applied_position_id")
        else:
            raise serializers.ValidationError("applied_position_id field required")

        try:
            # if applied_position_id is not None:
            queryset = ActivityLogs.objects.filter(applied_position=applied_position_id).order_by("id")
            data = ActivityLogsSerializer(queryset, many=True).data

            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Candidate Activity List Fetched Successfully.",
                }
            )
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Candidate Activity List Does Not Exist",
                }
            )


class SendInterviewSchedulewMail(APIView):
    applied_position_id = openapi.Parameter(
        "applied_position_id",
        in_=openapi.IN_QUERY,
        description="Enter applied position id for sending email",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[applied_position_id])
    def get(self, request, format=None):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        if data.get("applied_position_id") is not None:
            applied_position_id = data.get("applied_position_id")
        else:
            raise serializers.ValidationError("applied_position_id field required")

        applied_obj = AppliedPosition.objects.get(id=applied_position_id)
        to_email = applied_obj.applied_profile.profile.email
        first_name = applied_obj.applied_profile.profile.first_name
        date = applied_obj.data["interview_schedule_data"]["date"]
        start_time = applied_obj.data["interview_schedule_data"]["start_time"]
        end_time = applied_obj.data["interview_schedule_data"]["end_time"]
        from_email = settings.EMAIL_HOST_USER

        body_msg = "Hi {} your interview has been reschedule to {} from {} to {}. Please bring the resume copy and other documents.".format(
            first_name, date, start_time, end_time
        )
        context = {"body_msg": body_msg}
        body_msg = render_to_string("interview.html", context)
        msg = EmailMultiAlternatives("Email For Interview Schedule<Don't Reply>", body_msg, from_email, [to_email])
        msg.content_subtype = "html"
        msg.send()

        try:
            return ResponseOk(
                {
                    "data": None,
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


class PositionGraph(APIView):
    start_date = openapi.Parameter(
        "start_date",
        in_=openapi.IN_QUERY,
        description="Enter start_date",
        type=openapi.TYPE_STRING,
    )
    end_date = openapi.Parameter(
        "end_date",
        in_=openapi.IN_QUERY,
        description="Enter end_date",
        type=openapi.TYPE_STRING,
    )
    form_data_id = openapi.Parameter(
        "form_data_id",
        in_=openapi.IN_QUERY,
        description="Enter form_data_id",
        type=openapi.TYPE_STRING,
    )
    data_type = openapi.Parameter(
        "data_type",
        in_=openapi.IN_QUERY,
        description="Enter data_type",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[start_date, end_date, form_data_id, data_type])
    def get(self, request, format=None):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data:
            return ResponseOk(data)
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        if data.get("form_data_id") is not None:
            form_data_id = data.get("form_data_id")
        else:
            raise serializers.ValidationError("form_data_id field required")

        start_date = data.get("start_date")

        end_date = data.get("end_date")

        # data_type = data.get("data_type")

        if start_date is None and end_date is None:
            pos_obj = AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None)).filter(form_data=int(form_data_id))
            position_obj_total = (
                pos_obj.annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )

            position_obj_active = (
                pos_obj.filter(application_status__in=["active", "offer", "pending-offer", "hired", "pending", "approved", "kiv", "cancelled"])
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )
            position_obj_rejected = (
                pos_obj.filter(application_status__in=["reject", "offer-decline", "offer-rejected"])
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )
            position_obj_hold = (
                pos_obj.filter(application_status="hold")
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )
            position_obj_offer = (
                pos_obj.filter(application_status="offer")
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )

            position_obj_pending_offer = (
                pos_obj.filter(application_status="pending-offer")
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )

            position_obj_hired = (
                pos_obj.filter(application_status="hired")
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )

            position_obj_decline = (
                pos_obj.filter(application_status="offer-decline")
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )

        else:
            # if data_type == 1:
            #     position_obj_all = AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None)).filter(
            #         form_data=int(form_data_id)
            #     )
            #     # end_date = next_end_date(end_date)
            #     position_obj_total = (
            #         position_obj_all.filter(created_at__range=(start_date, end_date))
            #         .annotate(week=TruncWeek("created_at"))
            #         .values("week")
            #         .annotate(count=Count("id"))
            #         .values("week", "count")
            #         .order_by("week")
            #     )
            #     position_obj_active = (
            #         position_obj_all.filter(application_status="active", created_at__range=(start_date, end_date))
            #         .annotate(week=TruncWeek("created_at"))
            #         .values("week")
            #         .annotate(count=Count("id"))
            #         .values("week", "count")
            #         .order_by("week")
            #     )
            #     position_obj_rejected = (
            #         position_obj_all.filter(application_status="reject", created_at__range=(start_date, end_date))
            #         .annotate(week=TruncWeek("created_at"))
            #         .values("week")
            #         .annotate(count=Count("id"))
            #         .values("week", "count")
            #         .order_by("week")
            #     )
            #     position_obj_hold = (
            #         position_obj_all.filter(application_status="hold", created_at__range=(start_date, end_date))
            #         .annotate(week=TruncWeek("created_at"))
            #         .values("week")
            #         .annotate(count=Count("id"))
            #         .values("week", "count")
            #         .order_by("week")
            #     )
            # else:
            position_obj_all = AppliedPosition.objects.filter(Q(company__url_domain=url_domain) | Q(company=None)).filter(form_data=int(form_data_id))
            end_date = next_end_date(end_date)
            position_obj_total = (
                position_obj_all.filter(created_at__range=(start_date, end_date))
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )
            position_obj_active = (
                position_obj_all.filter(
                    application_status__in=["active", "offer", "pending-offer", "hired", "pending", "approved", "cancelled", "kiv"],
                    created_at__range=(start_date, end_date),
                )
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )
            position_obj_rejected = (
                position_obj_all.filter(
                    application_status__in=["reject", "offer-decline", "offer-rejected"], created_at__range=(start_date, end_date)
                )
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )
            position_obj_hold = (
                position_obj_all.filter(application_status="hold", created_at__range=(start_date, end_date))
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )
            position_obj_offer = (
                position_obj_all.filter(application_status="offer", created_at__range=(start_date, end_date))
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )
            position_obj_pending_offer = (
                position_obj_all.filter(application_status="pending-offer", created_at__range=(start_date, end_date))
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )
            position_obj_hired = (
                position_obj_all.filter(application_status="hired", created_at__range=(start_date, end_date))
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )
            position_obj_decline = (
                position_obj_all.filter(application_status="offer-decline", created_at__range=(start_date, end_date))
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .values("month", "count")
                .order_by("month")
            )

        data = {
            "total_applicants_count": 0,
            "active_applicants_count": 0,
            "rejected_applicants_count": 0,
            "hold_applicants_count": 0,
            "offer_applicats_count": 0,
            "pending_offer_applicats_count": 0,
            "hired_applicats_count": 0,
            "decline_applicats_count": 0,
        }

        for us in position_obj_total:
            us["month"] = str(int(str((us.pop("month")).date()).split("-")[1]))
            data["total_applicants_count"] += us["count"]

        for us in position_obj_active:
            us["month"] = str(int(str((us.pop("month")).date()).split("-")[1]))
            data["active_applicants_count"] += us["count"]

        for us in position_obj_rejected:
            us["month"] = str(int(str((us.pop("month")).date()).split("-")[1]))
            data["rejected_applicants_count"] += us["count"]

        for us in position_obj_hold:
            us["month"] = str(int(str((us.pop("month")).date()).split("-")[1]))
            data["hold_applicants_count"] += us["count"]

        for us in position_obj_offer:
            us["month"] = str(int(str((us.pop("month")).date()).split("-")[1]))
            data["offer_applicats_count"] += us["count"]
        for us in position_obj_pending_offer:
            us["month"] = str(int(str((us.pop("month")).date()).split("-")[1]))
            data["pending_offer_applicats_count"] += us["count"]
        for us in position_obj_hired:
            us["month"] = str(int(str((us.pop("month")).date()).split("-")[1]))
            data["hired_applicats_count"] += us["count"]
        for us in position_obj_decline:
            us["month"] = str(int(str((us.pop("month")).date()).split("-")[1]))
            data["decline_applicats_count"] += us["count"]
        resp = {
            "count": data,
            "total_applicants_count": position_obj_total,
            "active_applicants_count": position_obj_active,
            "rejected_applicants_count": position_obj_rejected,
            "hold_applicants_count": position_obj_hold,
            "code": status.HTTP_200_OK,
            "message": "Ok",
        }
        cache.set(request.get_full_path(), resp)
        return ResponseOk(resp)


class CreateApplicationDocument(APIView):
    """
    This POST function creates a Application Document Model record from the data passed in the body.

    Args:
        None
    Body:
        Application Document model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="Document Create API",
        request_body=FormSerializer.CreateApplicantDocumentsSerializer,
    )
    def post(self, request):
        try:
            # For multiple file uploads
            for file in request.FILES.getlist("doucument"):
                context = {"doucument": file, "applied_position": request.data.get("applied_position")}
                print(file)
                print(context)
                serializer = FormSerializer.CreateApplicantDocumentsSerializer(
                    data=context,
                )
                if serializer.is_valid():
                    serializer.save()
                else:
                    pass
            return ResponseOk(
                {
                    # "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Applicant Document created Successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "error",
                }
            )

    @swagger_auto_schema(
        operation_description="Document Delete API",
        operation_summary="Document Delete API",
        manual_parameters=[
            openapi.Parameter(
                "id",
                in_=openapi.IN_QUERY,
                description="id of the document",
                type=openapi.TYPE_STRING,
            )
        ],
    )
    def delete(self, request):
        try:
            data = request.GET
            applicant_doc_obj = ApplicantDocuments.objects.get(id=data.get("id"))
            applicant_doc_obj.delete()
            return ResponseOk(
                {
                    "code": status.HTTP_200_OK,
                    "message": "Applicant Document deleted Successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "error",
                }
            )


class GetAllApplicantDocuments(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.ApplicantDocuments.objects.all()

    applied_position_id = openapi.Parameter(
        "applied_position_id",
        in_=openapi.IN_QUERY,
        description="enter applied_position_id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[applied_position_id])
    def get(self, request):
        data = request.GET

        if data.get("applied_position_id") is not None:
            applied_position_id = data.get("applied_position_id")
        else:
            raise serializers.ValidationError("applied_position_id field required")
        try:
            if applied_position_id:
                queryset_data = ApplicantDocuments.objects.filter(applied_position=applied_position_id)

            serializer = FormSerializer.GetApplicantDocumentsSerializer(queryset_data, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Get Applicant Documents Successfully.",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Applicant Document does not Exist",
                }
            )


class SendEmailView(APIView):
    # parser_classes = [MultiPartParser]

    @swagger_auto_schema(
        operation_description="Send Email API",
        operation_summary="Send Email API",
        # request_body=TypeSerializer,
    )
    def post(self, request, format=None):
        data = request.data

        res = send_add_candidate_email(request.data["email"], request.data["title"], request.data["body"])
        print(res)
        return ResponseOk(
            {
                "data": None,
                "code": status.HTTP_200_OK,
                "message": "Mail Sent Successfully. ",
            }
        )


class SendEmailToPositionApprovers(APIView):
    def post(self, request, applied_position_id, format=None):
        data = request.GET
        to_email = []
        try:
            application_obj = AppliedPosition.objects.get(id=applied_position_id)
            to_email.append(application_obj.form_data.created_by_profile.user.email)
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does not exist",
                }
            )
        approver_emails = PositionApproval.objects.filter(position=application_obj.form_data.id).values_list("profile__user__email", flat=True)
        to_email.extend(approver_emails)
        print(to_email)

        from_email = settings.EMAIL_HOST_USER
        # context = {"link": body}
        body_msg = render_to_string("hire_email_to_position_approver.html")
        tittle = "Email Position Approval"

        msg = EmailMultiAlternatives(tittle, body_msg, from_email, to_email)
        msg.content_subtype = "html"
        msg.send()

        return ResponseOk(
            {
                "data": None,
                "code": status.HTTP_200_OK,
                "message": "Scorecard E-Mail Sent Successfully",
            }
        )


class SendEmailToCandidateView(APIView):
    def post(self, request, applied_position_id, format=None):
        data = request.data
        to_email = data.get("to")
        subject = data.get("subject")
        content = data.get("content")
        cc = data.get("cc")
        interviewer = data.get("interviewer")
        try:
            application_obj = AppliedPosition.objects.get(id=applied_position_id)
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does not exist",
                }
            )
        content = fetch_dynamic_email_template(content, [to_email], applied_position_id=application_obj.id, subject=subject, interviewers=interviewer)
        application_obj.rejection_mail_sent = True
        application_obj.save()
        return ResponseOk(
            {
                "data": None,
                "code": status.HTTP_200_OK,
                "message": "Scorecard E-Mail Sent Successfully",
            }
        )


class SendReminderEmail(APIView):
    def post(self, request, applied_position_id):
        data = request.data
        to_email = data.get("to")
        subject = data.get("subject")
        content = data.get("content")
        cc = data.get("cc")
        interviewer = data.get("interviewer")
        try:
            application_obj = AppliedPosition.objects.get(id=applied_position_id)
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does not exist",
                }
            )
        content = fetch_dynamic_email_template(content, [to_email], applied_position_id=application_obj.id, subject=subject)
        application_obj.rejection_mail_sent = True
        application_obj.save()
        return ResponseOk(
            {
                "data": None,
                "code": status.HTTP_200_OK,
                "message": "Reminder E-Mail Sent Successfully",
            }
        )


class UpdateAppliedPositionStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def post(self, request, applied_position_id, format=None):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            status = request.data["application_status"]
            applied_obj = AppliedPosition.objects.get(id=applied_position_id)
            if status == "pending-offer":
                if AppliedPosition.objects.filter(form_data=applied_obj.form_data, application_status__in=["offer", "pending-offer", "approved"]):
                    return ResponseBadRequest(
                        {
                            "data": "Another candidate is in offer stage.",
                            "code": 400,
                            "message": "Another candidate is in offer stage.",
                        }
                    )
                if AppliedPosition.objects.filter(
                    applied_profile=applied_obj.applied_profile, application_status__in=["offer", "pending-offer", "approved", "hired"]
                ).exclude(id=applied_obj.id):
                    return ResponseBadRequest(
                        {
                            "data": "This candidate is in Offer stage for other position.",
                            "code": 400,
                            "message": "This candidate is in Offer stage for other position.",
                        }
                    )
            applied_obj.application_status = status
            applied_obj.save()
            if applied_obj.application_status == "pending-offer":
                position_stage = PositionStage.objects.filter(position=applied_obj.form_data, stage__stage_name="Offer").last()
                current_id = applied_obj.data["current_stage_id"]
                history_dict = {
                    "id": current_id,
                    "name": "Offer",
                    "date": date.today().strftime("%d %B, %Y"),
                }
                applied_obj.data["current_stage_id"] = position_stage.stage.id
                applied_obj.data["history"].append(current_id)
                applied_obj.data["history_detail"].append(history_dict)
                applied_obj.save()
                offer_activitys = ActivityLogs.objects.filter(applied_position=applied_obj, description__icontains="offer")
                if offer_activitys:
                    offer_activity = offer_activitys.last()
                    offer_activity.description = "Candidate Moved to Offer by {}.".format(request.user.get_full_name())
                    offer_activity.save()
                else:
                    data = {
                        "user": request.user.id,
                        "description": "Candidate Moved to Offer by {}.".format(request.user.get_full_name()),
                        "type_id": 4,
                        "applied_position": applied_obj.id,
                    }
                    create_activity_log(data)
            return ResponseOk(
                {
                    "data": None,
                    "code": 200,
                    "message": "Status updated Successfully.",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": 400,
                    "message": "Something went wrong!",
                }
            )


class DeclineOffer(APIView):
    @swagger_auto_schema(
        operation_summary="Offer Letter Decline API",
        operation_description="""
                Offer letter decline API. id of the offer letter must be passed in body alogn with other data.
            """,
        request_body=OfferLetterSerializer,
    )
    def put(self, request):
        try:
            response = {}
            data = request.data.get("data")
            offer_letter = OfferLetter.objects.get(id=data.get("id"))
            # serializer = OfferLetterSerializer(offer_letter, data=data, partial=True)
            message = "Offer Letter updated"
            if "start_date" in data and len(data) == 3:
                form_data = offer_letter.offered_to.form_data
                form_data.status = "active"
                form_data.save()
                applied_position = offer_letter.offered_to
                applied_position.application_status = "approved"
                prev_stage = Stage.objects.filter(stage_name="Hired", company=applied_position.company).last()
                curr_stage = Stage.objects.filter(stage_name="Offer", company=applied_position.company).last()
                if curr_stage:
                    applied_position.data["current_stage_id"] = curr_stage.id
                if prev_stage:
                    history = applied_position.data.get("history", [])
                    history.append(prev_stage.id)
                    applied_position.data["history"] = history
                    history_details = applied_position.data.get("history_detail", [])
                    history_details.append(
                        {
                            "id": prev_stage.id,
                            "date": date.today().strftime("%d %B, %Y"),
                            "name": "Offer",
                        }
                    )
                    applied_position.data["history_detail"] = history_details
                if offer_letter.response_date is None:
                    offer_letter.response_date = date.today()
                offer_letter.accepted = False
                offer_letter.start_date_change = True
                offer_letter.save()
                applied_position.save()
                # Updates candidate status
                candidate_user_obj = applied_position.applied_profile.user
                try:
                    candidate_user_obj.user_company = applied_position.company
                    candidate_user_obj.user_role = Role.objects.filter(name="candidate").last()
                    candidate_user_obj.save()
                except Exception as e:
                    message = str(e)
                one = False
                for i in OfferApproval.objects.filter(position=offer_letter.offered_to.form_data).order_by("sort_order"):
                    i.is_approve = False
                    if one == False:
                        i.show = True
                    else:
                        i.show = False
                    if i.approval_type == "one to one":
                        one = True
                    i.save()
                offer_letter.withdraw = True
                offer_letter.start_date_change = False
                offer_letter.accepted = False
                offer_letter.is_decline = True
                offer_letter.offer_created_mail = False
                if offer_letter.response_date is None:
                    offer_letter.response_date = date.today()
                candidate_user_obj = offer_letter.offered_to.applied_profile.user
                try:
                    candidate_user_obj.user_role = Role.objects.filter(name="candidate").last()
                    candidate_user_obj.save()
                except Exception as e:
                    message = str(e)
                # Change to offer stage
                applied_position = offer_letter.offered_to
                prev_stage = Stage.objects.filter(stage_name="Hired", company=applied_position.company).last()
                curr_stage = Stage.objects.filter(stage_name="Offer", company=applied_position.company).last()
                if curr_stage:
                    applied_position.data["current_stage_id"] = curr_stage.id
                if prev_stage:
                    history = applied_position.data.get("history", [])
                    history.append(prev_stage.id)
                    applied_position.data["history"] = history
                    history_details = applied_position.data.get("history_detail", [])
                    history_details.append(
                        {
                            "id": prev_stage.id,
                            "date": date.today().strftime("%d %B, %Y"),
                            "name": "Offer",
                        }
                    )
                    applied_position.data["history_detail"] = history_details
                applied_position.save()
                offer_letter.offered_to.application_status = "offer-decline"
                offer_letter.offered_to.form_data.status = "active"
                form_data = offer_letter.offered_to.form_data
                try:
                    applied_position_objs = AppliedPosition.objects.filter(application_status="active", form_data=form_data)
                    if applied_position_objs:
                        serialized_data = AppliedPositionListSerializer(applied_position_objs, many=True).data
                        final_data = sorted(serialized_data, key=lambda d: d["average_scorecard_rating"], reverse=True)

                        top_rating = final_data[0]["average_scorecard_rating"]
                        for final in final_data:
                            if final["average_scorecard_rating"] == top_rating and top_rating > 0:
                                applied_position_obj = AppliedPosition.objects.get(id=final["id"])
                                applied_position_obj.application_status = "pending"
                                applied_position_obj.save()

                        # tentative changes 14072023
                        # if final_data[0]["average_scorecard_rating"] > 0:
                        #     applied_position_obj = AppliedPosition.objects.get(id=final_data[0]["id"])
                        #     applied_position_obj.application_status = "pending"
                        #     applied_position_obj.save()
                        # if len(final_data) > 1 and final_data[1]["average_scorecard_rating"] > 0:
                        #     applied_position_obj = AppliedPosition.objects.get(id=final_data[1]["id"])
                        #     applied_position_obj.application_status = "pending"
                        #     applied_position_obj.save()
                except Exception as e:
                    error = str(e)
                    error_msg = "Next candidate not moved to pending decison"
                    pass
                offer_letter.save()
                offer_letter.offered_to.save()
                offer_letter.offered_to.form_data.save()
                # Create or update activity

                data = {
                    "user": request.user.id,
                    "description": "Candidate is Decline by {}.".format(request.user.get_full_name()),
                    "type_id": 4,
                    "applied_position": offer_letter.offered_to.id,
                }
                create_activity_log(data)
                # offer_letter.delete()
                # return ResponseOk(
                #     {"data": serializer.data, "code": status.HTTP_200_OK, "message": message, "error": error, "error-msg": error_msg}
                # )
                return ResponseOk({"data": {"offer-declined": True}, "code": status.HTTP_200_OK, "message": "offer declined"})

        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "errors",
                }
            )


class OfferLetterView(APIView):
    """
    Creates and Updates an Offer Letter from HiringManager's dashboard.
    Args:
        None
    Body:
        OfferLetter models all fields.
    Authentication:
        JWT
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(operation_summary="Offer Letter Create API", request_body=OfferLetterSerializer)
    def post(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.data.get("data")
        data["offered_to"] = request.data.get("offered_to")
        data["offered_by_profile"] = request.user.profile.id
        serializer = OfferLetterSerializer(data=data)
        if serializer.is_valid():
            offer_letter_obj = serializer.save()
            offer_letter_obj.offered_to.application_status = "offer"
            offer_letter_obj.offered_to.save()
            one = False
            for i in OfferApproval.objects.filter(position=offer_letter_obj.offered_to.form_data).order_by("sort_order"):
                i.is_approve = False
                if one == False:
                    i.show = True
                    send_offer_approval_mail(i)
                else:
                    i.show = False
                if i.approval_type == "one to one":
                    one = True
                i.candidate = offer_letter_obj.offered_to.applied_profile
                i.save()
            # Send email to candidate about offer
            message = "Offer Letter created successfully"
            # try:
            #     context = {}
            #     context["Candidate_Name"] = offer_letter_obj.offered_to.applied_profile.user.get_full_name()
            #     context["Position_Name"] = offer_letter_obj.offered_to.form_data.form_data["job_title"]
            #     context["Company_Name"] = offer_letter_obj.offered_to.company.company_name
            #     context["start_date"] = str(offer_letter_obj.start_date)
            #     context["CompanyLogin_Link"] = "https://{}.{}".format(offer_letter_obj.offered_to.company.url_domain, settings.DOMAIN_NAME)
            #     from_email = settings.EMAIL_HOST_USER
            #     body_msg = render_to_string("offer_send.html", context)
            #     msg = EmailMultiAlternatives(
            #         "Congratulations on Your Offer Letter",
            #         body_msg,
            #         "Congratulations on Your Offer Letter",
            #         [offer_letter_obj.offered_to.applied_profile.user.email],
            #     )
            #     msg.content_subtype = "html"
            #     msg.send()
            # except Exception as e:
            #     message = "Offer Letter created successfully. But email not sent. " + str(e)
            # Change the application status to offer.
            # offer_letter_obj.offered_to.save()
            # applied_position = offer_letter_obj.offered_to
            # applied_position.data["current_stage_id"] = 175
            # history = applied_position.data.get("history", [])
            # history.append(175)
            # applied_position.data["history"] = history
            # history_details = applied_position.data.get("history_detail", [])
            # history_details.append(
            #     {
            #         "id": 175,
            #         "date": date.today().strftime("%d %B, %Y"),
            #         "name": "Offer",
            #     }
            # )
            # applied_position.data["history_detail"] = history_details
            # applied_position.save()
            # Create/Update activity
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": message,
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

    @swagger_auto_schema(
        operation_summary="Offer Letter Update API",
        operation_description="""
                Offer letter update API. id of the offer letter must be passed in body alogn with other data.
                This API also handles other operations like:
                1. offer decline - if is_decline: true is passed in the payload of the API the offer will be declined
            """,
        request_body=OfferLetterSerializer,
    )
    def put(self, request):
        try:
            response = {}
            data = request.data
            data["offered_by_profile"] = request.user.profile.id
            offer_letter_obj = OfferLetter.objects.get(id=request.data.get("id"))
            innfer_data = offer_letter_obj.data
            last_status = offer_letter_obj.offered_to.application_status
            data.pop("signed_file", None)
            serializer = OfferLetterSerializer(offer_letter_obj, data=data, partial=True)
            message = "Offer Letter updated"
            error = None
            error_msg = None
            if serializer.is_valid():
                offer_letter = serializer.save()
                # if offer_letter_obj.withdraw == False and offer_letter_obj.offer_created_mail == False:
                #     try:
                #         context = {}
                #         context["Candidate_Name"] = offer_letter_obj.offered_to.applied_profile.user.get_full_name()
                #         context["Position_Name"] = offer_letter_obj.offered_to.form_data.form_data["job_title"]
                #         context["Company_Name"] = offer_letter_obj.offered_to.company.company_name
                #         context["start_date"] = str(offer_letter_obj.start_date)
                #         context["CompanyLogin_Link"] = "https://{}.{}".format(offer_letter_obj.offered_to.company.url_domain, settings.DOMAIN_NAME)
                #         from_email = settings.EMAIL_HOST_USER
                #         body_msg = render_to_string("offer_send.html", context)
                #         msg = EmailMultiAlternatives(
                #             "Congratulations on Your Offer Letter",
                #             body_msg,
                #             "Congratulations on Your Offer Letter",
                #             [offer_letter_obj.offered_to.applied_profile.user.email],
                #         )
                #         msg.content_subtype = "html"
                #         msg.send()
                #         offer_letter_obj.offer_created_mail = True
                #         offer_letter_obj.save()
                #     except Exception as e:
                #         message = "Offer Letter updated successfully. But email not sent. " + str(e)
                if request.data.get("data"):
                    pass
                else:
                    offer_letter.data = innfer_data
                offer_letter.save()
                # Add the candidate to the approvals
                for i in OfferApproval.objects.filter(position=offer_letter.offered_to.form_data).order_by("sort_order"):
                    i.candidate = offer_letter.offered_to.applied_profile
                    i.save()
                # Check if offere is decline
                # Made new API can be commented from here once implemented on FE
                if "start_date" in data and len(data) == 3:
                    form_data = offer_letter.offered_to.form_data
                    form_data.status = "active"
                    form_data.save()
                    applied_position = offer_letter.offered_to
                    applied_position.application_status = "approved"
                    prev_stage = Stage.objects.filter(stage_name="Hired", company=applied_position.company).last()
                    curr_stage = Stage.objects.filter(stage_name="Offer", company=applied_position.company).last()
                    if curr_stage:
                        applied_position.data["current_stage_id"] = curr_stage.id
                    if prev_stage:
                        history = applied_position.data.get("history", [])
                        history.append(prev_stage.id)
                        applied_position.data["history"] = history
                        history_details = applied_position.data.get("history_detail", [])
                        history_details.append(
                            {
                                "id": prev_stage.id,
                                "date": date.today().strftime("%d %B, %Y"),
                                "name": "Offer",
                            }
                        )
                        applied_position.data["history_detail"] = history_details
                    if offer_letter.response_date is None:
                        offer_letter.response_date = date.today()
                    offer_letter.accepted = False
                    offer_letter.start_date_change = True
                    offer_letter.save()
                    applied_position.save()
                    # Updates candidate status - Not Needed as status is only being changed after email change
                    # candidate_user_obj = applied_position.applied_profile.user
                    # try:
                    #     candidate_user_obj.user_company = applied_position.company
                    #     candidate_user_obj.user_role = Role.objects.filter(name="candidate").last()
                    #     candidate_user_obj.save()
                    # except Exception as e:
                    #     message = str(e)
                    return ResponseOk(
                        {"data": serializer.data, "code": status.HTTP_200_OK, "message": "updated", "error": error, "error-msg": error_msg}
                    )
                if request.data.get("update"):
                    offer_letter.is_decline = False
                    offer_letter.save()
                if "is_decline" in data:
                    if offer_letter.is_decline:
                        one = False
                        for i in OfferApproval.objects.filter(position=offer_letter.offered_to.form_data).order_by("sort_order"):
                            i.is_approve = False
                            if one == False:
                                i.show = True
                            else:
                                i.show = False
                            if i.approval_type == "one to one":
                                one = True
                            i.save()
                        offer_letter.withdraw = True
                        offer_letter.start_date_change = False
                        offer_letter.accepted = False
                        offer_letter.is_decline = True
                        offer_letter.offer_created_mail = False
                        if offer_letter.response_date is None:
                            offer_letter.response_date = date.today()
                        candidate_user_obj = offer_letter.offered_to.applied_profile.user
                        # No need as we are not changing role when offer gets accepted
                        # try:
                        #     candidate_user_obj.user_role = Role.objects.filter(name="candidate").last()
                        #     candidate_user_obj.save()
                        # except Exception as e:
                        #     message = str(e)
                        # Change to offer stage
                        applied_position = offer_letter.offered_to
                        prev_stage = Stage.objects.filter(stage_name="Hired", company=applied_position.company).last()
                        curr_stage = Stage.objects.filter(stage_name="Offer", company=applied_position.company).last()
                        if curr_stage:
                            applied_position.data["current_stage_id"] = curr_stage.id
                        if prev_stage:
                            history = applied_position.data.get("history", [])
                            history.append(prev_stage.id)
                            applied_position.data["history"] = history
                            history_details = applied_position.data.get("history_detail", [])
                            history_details.append(
                                {
                                    "id": prev_stage.id,
                                    "date": date.today().strftime("%d %B, %Y"),
                                    "name": "Offer",
                                }
                            )
                            applied_position.data["history_detail"] = history_details
                        applied_position.save()
                        offer_letter.offered_to.application_status = "offer-decline"
                        offer_letter.offered_to.form_data.status = "active"
                        form_data = offer_letter.offered_to.form_data
                        try:
                            applied_position_objs = AppliedPosition.objects.filter(application_status="active", form_data=form_data)
                            if applied_position_objs:
                                serialized_data = AppliedPositionListSerializer(applied_position_objs, many=True).data
                                final_data = sorted(serialized_data, key=lambda d: d["average_scorecard_rating"], reverse=True)

                                top_rating = final_data[0]["average_scorecard_rating"]
                                for final in final_data:
                                    if final["average_scorecard_rating"] == top_rating and top_rating > 0:
                                        applied_position_obj = AppliedPosition.objects.get(id=final["id"])
                                        applied_position_obj.application_status = "pending"
                                        applied_position_obj.save()

                                # tentative changes 14072023
                                # if final_data[0]["average_scorecard_rating"] > 0:
                                #     applied_position_obj = AppliedPosition.objects.get(id=final_data[0]["id"])
                                #     applied_position_obj.application_status = "pending"
                                #     applied_position_obj.save()
                                # if len(final_data) > 1 and final_data[1]["average_scorecard_rating"] > 0:
                                #     applied_position_obj = AppliedPosition.objects.get(id=final_data[1]["id"])
                                #     applied_position_obj.application_status = "pending"
                                #     applied_position_obj.save()
                        except Exception as e:
                            error = str(e)
                            error_msg = "Next candidate not moved to pending decison"
                            pass
                        offer_letter.save()
                        offer_letter.offered_to.save()
                        offer_letter.offered_to.form_data.save()
                        # Create or update activity

                        data = {
                            "user": request.user.id,
                            "description": "Candidate is Decline by {}.".format(request.user.get_full_name()),
                            "type_id": 4,
                            "applied_position": offer_letter.offered_to.id,
                        }
                        create_activity_log(data)
                        # send rejection mail
                        if request.data.get("rejectionEmail") == "yes":
                            to = [offer_letter.offered_to.applied_profile.user.email]
                            subject = "You status for the position {}!".format(offer_letter.offered_to.form_data.form_data["job_title"])
                            try:
                                email_template = EmailTemplate.objects.filter(template_name="Candidate Rejection Email").last()
                                content = email_template.description
                            except Exception as e:
                                content = "You status for the position {}!".format(offer_letter.offered_to.form_data.form_data["job_title"])
                            content = fetch_dynamic_email_template(content, to, offer_letter.offered_to.id, subject=subject)
                        else:
                            pass
                        offer_letter.offered_to.data["rejected_at"] = str(datetime.datetime.today().date())
                        offer_letter.offered_to.data["rejected_by"] = request.user.get_full_name()
                        offer_letter.offered_to.data["created_at"] = str(datetime.datetime.today().date())
                        offer_letter.offered_to.data["reason"] = request.data.get("decline_reason")
                        offer_letter.offered_to.save()
                        # offer_letter.delete()
                        return ResponseOk(
                            {"data": serializer.data, "code": status.HTTP_200_OK, "message": message, "error": error, "error-msg": error_msg}
                        )
                    else:
                        if request.data.get("update"):
                            offer_letter.is_decline = False
                            offer_letter.save()
                            offer_letter.offered_to.application_status = "offer"
                            offer_letter.offered_to.save()
                if offer_letter.withdraw:
                    one = False
                    for i in OfferApproval.objects.filter(position=offer_letter.offered_to.form_data).order_by("sort_order"):
                        i.is_approve = False
                        if one == False:
                            i.show = True
                        else:
                            i.show = False
                        if i.approval_type == "one to one":
                            one = True
                        i.save()
                    offer_letter.response_date = None
                    offer_letter.offered_to.application_status = "pending-offer"
                    offer_letter.offered_to.save()
                    offer_letter.start_date_change = False
                    offer_letter.offer_created_mail = False
                    offer_letter.save()
                    # Send Mail to candidate about the same
                    context = {
                        "name": offer_letter.offered_to.applied_profile.user.get_full_name(),
                        "company": request.user.user_company.company_name,
                        "user_name": request.user.get_full_name(),
                    }
                    body_msg = render_to_string("recide_offer.html", context)
                    content = fetch_dynamic_email_template(
                        body_msg,
                        [offer_letter.offered_to.applied_profile.user.email],
                        applied_position_id=offer_letter.offered_to.id,
                        subject="Rescinding Offer Letter",
                    )
                    # send notification using sockets
                    send_instant_notification(
                        message="Hi {}, your offer letter is being withdrawn by the hiring manager, will be sending you the offer letter once again".format(
                            offer_letter.offered_to.applied_profile.user.get_full_name()
                        ),
                        user=offer_letter.offered_to.applied_profile.user,
                        applied_position=offer_letter.offered_to,
                    )
                    # add acticity log
                    log_data = {
                        "user": request.user.id,
                        "description": "Candidate offer withdrawn by {}.".format(request.user.get_full_name()),
                        "type_id": 4,
                        "applied_position": offer_letter.offered_to.id,
                    }
                    create_activity_log(log_data)
                    return Response({"msg": "Offer withdrawn"}, status=status.HTTP_200_OK)

                if offer_letter.accepted:
                    form_data = offer_letter.offered_to.form_data
                    form_data.status = "closed"
                    form_data.save()
                    applied_position = offer_letter.offered_to
                    applied_position.application_status = "hired"
                    # Remove candidate from Pending Decision
                    for ap in AppliedPosition.objects.filter(form_data=form_data, application_status="pending"):
                        ap.application_status = "active"
                        ap.save()
                    # Send notification to HM and Recruiter
                    try:
                        recruiter_obj = User.objects.get(
                            email=offer_letter.offered_to.form_data.recruiter, user_company=offer_letter.offered_to.company
                        )
                        send_instant_notification(
                            message="{} has accepted the offer for position.".format(offer_letter.offered_to.applied_profile.user.get_full_name()),
                            user=recruiter_obj,
                            applied_position=offer_letter.offered_to,
                        )
                    except:
                        pass
                    try:
                        hiring_manager_obj = User.objects.get(
                            email=offer_letter.offered_to.form_data.hiring_manager, user_company=offer_letter.offered_to.company
                        )
                        send_instant_notification(
                            message="{} has accepted the offer for position.".format(offer_letter.offered_to.applied_profile.user.get_full_name()),
                            user=hiring_manager_obj,
                            slug="/position-dashboard/candidate-view",
                            applied_position=offer_letter.offered_to,
                        )
                    except:
                        pass
                    prev_stage = Stage.objects.filter(stage_name="Offer", company=applied_position.company).last()
                    curr_stage = Stage.objects.filter(stage_name="Hired", company=applied_position.company).last()
                    if curr_stage:
                        applied_position.data["current_stage_id"] = curr_stage.id
                    if prev_stage:
                        history = applied_position.data.get("history", [])
                        history.append(prev_stage.id)
                        applied_position.data["history"] = history
                        history_details = applied_position.data.get("history_detail", [])
                        history_details.append(
                            {
                                "id": prev_stage.id,
                                "date": date.today().strftime("%d %B, %Y"),
                                "name": "Offer",
                            }
                        )
                        applied_position.data["history_detail"] = history_details
                    if offer_letter.response_date is None:
                        offer_letter.response_date = date.today()
                    applied_position.save()
                    # Updates candidate status
                    # candidate_user_obj = applied_position.applied_profile.user
                    # try:
                    #     candidate_user_obj.user_company = applied_position.company
                    #     candidate_user_obj.user_role = Role.objects.get(company=applied_position.company, name="employee")
                    #     candidate_user_obj.save()
                    # except Exception as e:
                    #     message = str(e)
                    # Create/update activity log
                    offer_activitys = ActivityLogs.objects.filter(applied_position=applied_position, description__icontains="offer")
                    if offer_activitys:
                        offer_activity = offer_activitys.last()
                        offer_activity.description = "Candidate accepted the offer and moved to Hired."
                        offer_activity.save()
                    else:
                        data = {
                            "user": request.user.id,
                            "description": "Candidate Accepted the Offer and Moved to Hired.",
                            "type_id": 4,
                            "applied_position": applied_position.id,
                        }
                        create_activity_log(data)
                elif offer_letter.accepted is not None and offer_letter.response_date is not None:
                    print("elif")
                    in_order = None
                    for i in OfferApproval.objects.filter(position=offer_letter.offered_to.form_data).order_by("sort_order"):
                        i.is_approve = False
                        if in_order is None and i.approval_type in ["o-t-o", "one to one"]:
                            i.show = True
                            in_order = True
                        if i.approval_type in ["All at once", "a-a-o"]:
                            i.show = True
                        i.save()
                    offer_letter.response_date = date.today()
                    offer_letter.offered_to.application_status = "offer-rejected"
                    offer_letter.start_date_change = False
                    offer_letter.save()
                    offer_letter.offered_to.save()
                    data = {
                        "user": request.user.id,
                        "description": "Candidate Rejected the Offer.",
                        "type_id": 4,
                        "applied_position": offer_letter.offered_to.id,
                    }
                    create_activity_log(data)
                    # Send offer reject notification
                    try:
                        hiring_manager = User.objects.get(
                            email=offer_letter.offered_to.form_data.hiring_manager, user_company=offer_letter.offered_to.company
                        )
                        send_instant_notification(
                            message="Hi, {} has rejected the offer for position {}.".format(
                                offer_letter.offered_to.applied_profile.user.get_full_name(),
                                offer_letter.offered_to.form_data.form_data.get("job_title"),
                            ),
                            user=hiring_manager,
                            slug="/position-dashboard",
                            form_data=offer_letter.offered_to.form_data,
                            event_type="position-approval",
                        )
                        recruiter = User.objects.get(email=offer_letter.offered_to.form_data.recruiter, user_company=offer_letter.offered_to.company)
                        send_instant_notification(
                            message="Hi, {} has rejected the offer for position {}.".format(
                                offer_letter.offered_to.applied_profile.user.get_full_name(),
                                offer_letter.offered_to.form_data.form_data.get("job_title"),
                            ),
                            user=recruiter,
                            slug="/position-dashboard",
                            form_data=offer_letter.offered_to.form_data,
                            event_type="position-approval",
                        )
                    except Exception as e:
                        print(e)
                    # Send next candidate to pending decision
                    try:
                        applied_position_objs = AppliedPosition.objects.filter(
                            application_status="active", form_data=offer_letter.offered_to.form_data
                        )
                        if applied_position_objs:
                            serialized_data = AppliedPositionListSerializer(applied_position_objs, many=True).data
                            final_data = sorted(serialized_data, key=lambda d: d["average_scorecard_rating"], reverse=True)
                            top_rating = final_data[0]["average_scorecard_rating"]
                            for final in final_data:
                                if final["average_scorecard_rating"] == top_rating and top_rating > 0:
                                    applied_position_obj = AppliedPosition.objects.get(id=final["id"])
                                    applied_position_obj.application_status = "pending"
                                    applied_position_obj.save()

                            # tentative changes 14072023
                            # if final_data[0]["average_scorecard_rating"] > 0:
                            #     applied_position_obj = AppliedPosition.objects.get(id=final_data[0]["id"])
                            #     applied_position_obj.application_status = "pending"
                            #     applied_position_obj.save()

                    except Exception as e:
                        error = str(e)
                        error_msg = "Next candidate not moved to pending decison"
                if request.data.get("withdraw") == False and (last_status in ["offer-rejected"] or request.data.get("update")):
                    offer_letter.offered_to.application_status = "offer"
                    offer_letter.offered_to.save()
                if request.data.get("update"):
                    offer_letter.is_decline = False
                    offer_letter.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
            else:
                print("else")
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "errors",
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


class GetSingleOffer(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, offer_id):
        try:
            offer_letter_obj = OfferLetter.objects.get(id=offer_id)
            serializer = GetOfferLetterSerializer(offer_letter_obj)
            data = serializer.data
            if data.get("data"):
                resp_data = data.get("data")
            else:
                resp_data = data
            return ResponseOk(
                {
                    "data": resp_data,
                    "code": status.HTTP_200_OK,
                    "message": "Offer Letter data",
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


class GetOfferLetters(APIView):
    """
    Return a list of Offer Letters for a candidate.
    It takes profile_id of the candidate
    Args:
        None
    Body:
        None
    Authentication:
        JWT
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, profile_id):
        try:
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
            offer_letter_objs = OfferLetter.objects.filter(
                offered_to__applied_profile__id=profile_id, withdraw=False, offered_to__application_status="approved"
            )
            serializer = OfferLetterSerializer(offer_letter_objs, many=True)
            data = []
            for ser in serializer.data:
                if ser["data"]:
                    ser["data"]["id"] = ser["id"]
                    data.append(ser["data"])
                else:
                    data.append(ser)
            if data:
                pass
            else:
                data = serializer.data
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Offer Letter data",
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


class GetOfferLetterPdf(APIView):

    """
    This API return the pdf of a letter offered to a candidate
    Args-
        id - id of the offer letter
    Body-
        None
    Return -
        Return a .pdf file with offer letter data in it.
    Auth-
        None as it provides a .pdf file directly
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, id):
        try:
            # generate context and call generate_offer_pdf
            offer_letter = OfferLetter.objects.get(id=id)
            # get location, offer template and all other details
            try:
                offer_template_obj = OfferLetterTemplate.objects.filter(
                    country__name=offer_letter.offered_to.form_data.form_data["country"]["name"],
                    company=offer_letter.offered_to.form_data.company,
                    status=True,
                )
                file_type = None
                for offer in offer_template_obj:
                    cur_file_type = offer.attached_letter.name.split(".")[-1]
                    print(file_type)
                    if cur_file_type == "pdf":
                        offer_template_obj = offer
                        file_type = cur_file_type
                        break

                if file_type is None:
                    a = 12 / 0  # deliberately going into exception

                if not offer_template_obj:
                    raise Http404
            except Exception as e:
                try:
                    offer_template_obj = OfferLetterTemplate.objects.filter(
                        offer_type__in=["Default", "Default Offer"], company=offer_letter.offered_to.form_data.company, status=True
                    ).last()
                    if not offer_template_obj:
                        raise Http404
                except Exception as e:
                    return ResponseBadRequest(
                        {
                            "message": "Admin needs to create an offer letter template from the offer template tab in the admin panel",
                        }
                    )
            file = offer_template_obj.attached_letter
            pdf_context = {}
            pdf_context["CandidateFullName"] = offer_letter.offered_to.applied_profile.user.get_full_name()
            pdf_context["CandidateFirstName"] = offer_letter.offered_to.applied_profile.user.first_name
            pdf_context["JobTitle"] = "{} (Business Title)".format(offer_letter.offered_to.form_data.form_data["job_title"])
            pdf_context["Location"] = offer_letter.offered_to.form_data.form_data["country"]["name"]
            pdf_context["HiringManagersTitle"] = offer_letter.reporting_manager
            pdf_context["StartDate"] = str(offer_letter.start_date)
            pdf_context["TotalTargetCompensation"] = str(offer_letter.target_compensation)
            pdf_context["Currency"] = str(offer_letter.currency)
            pdf_context["BonusAmount"] = str(offer_letter.bonus)
            pdf_context["ReportingManager"] = str(offer_letter.reporting_manager)
            pdf_context["OrganizationName"] = offer_letter.offered_to.form_data.company.company_name
            # Offer fields
            pdf_context["BasicSalary"] = offer_letter.basic_salary
            pdf_context["GuaranteeBonus"] = offer_letter.guarantee_bonus
            pdf_context["SignOnBonus"] = offer_letter.sign_on_bonus
            pdf_context["VisaRequired"] = offer_letter.visa_required
            pdf_context["RelocationBonus"] = offer_letter.relocation_bonus
            # get hiring manager name
            hiring_manager = "None"
            try:
                email = offer_letter.offered_to.form_data.hiring_manager
                hiring_manager = User.objects.get(email=email, user_company=offer_letter.offered_to.company).get_full_name()
            except:
                print("except 1")
            pdf_context["HiringManagerName"] = hiring_manager
            generate_offer_pdf(file, offer_letter.show_offer_id, pdf_context)
            file_path = "../Offer_{}.pdf".format(str(offer_letter.show_offer_id))
            if os.path.exists(file_path):
                with open(file_path, "rb") as fh:
                    response = HttpResponse(fh.read(), content_type="application/pdf")
                    response["Content-Disposition"] = "inline; filename=" + os.path.basename(file_path)
                    try:
                        os.remove(file_path)
                    except OSError:
                        print("E")
                    return response
            raise Http404
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "errors",
                }
            )


class GetOfferedToList(APIView):

    """
    Return a list of all Offer Letters given by the logged Hiring Manager.
    It takes profile_id of the logged Hiring Manager
    Args:
        None
    Body:
        None
    Authentication:
        JWT
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, profile_id):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
            offer_to_letter_objs = OfferLetter.objects.filter(offered_by_profile__id=profile_id)
            serializer = OfferLetterSerializer(offer_to_letter_objs, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Offer Letter data",
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


class GetOfferLetterListrecruiter(APIView):

    """
    Return a list of all Offer Letters in all the positioin that
    logged recruiter has approved.
    It takes profile_id of the logged Recruiter
    Args:
        None
    Body:
        None
    Authentication:
        JWT
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, profile_id):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
            approved_positions = FormData
            offer_to_letter_objs = OfferLetter.objects.filter(offered_by_profile__id=profile_id)
            serializer = OfferLetterSerializer(offer_to_letter_objs, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Offer Letter data",
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


# Offer Letter Templates Views
class OfferLetterTemplateView(APIView):

    """
    This  view Creates, Updates and Deletes an Offer Letter template.
    To create and update and offer letter following are required for creating
    and are option for editin in body
    Body-
        All the fields from OfferLetterTemplate except the offer_id
    Authentication-
        JWT
    Permission-
        IsAuthenticated for now, but it should be IsAdminUser.
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="This API Creates Offer Letter template",
        operation_summary="Offer Letter Template Create API",
        request_body=OfferLetterTemplateSerializer,
    )
    def post(self, request):
        try:
            data = request.data
            offer_id = generate_offer_id()
            data["offer_id"] = offer_id
            try:
                country_list = data.get("country")
                country_list = json.loads(country_list)
                data["country"] = country_list[0]["value"]
            except Exception as e:
                data["country"] = None
            try:
                state_list = data.get("state")
                state_list = json.loads(state_list)
                data["state"] = state_list["value"]
            except Exception as e:
                data["state"] = None
            try:
                city_list = data.get("city")
                city_list = json.loads(city_list)
                data["city"] = city_list["value"]
            except Exception as e:
                data["city"] = None
            try:
                job_category_list = data.get("job_category")
                job_category_list = json.loads(job_category_list)
                data["job_category"] = job_category_list["value"]
            except Exception as e:
                data["job_category"] = None
            try:
                employment_type_list = json.loads(data.get("employment_type"))
                data["employment_type"] = employment_type_list
            except Exception as e:
                data["employment_type"] = None
            employment_type = data.pop("employment_type")
            serializer = OfferLetterTemplateSerializer(data=data)
            if serializer.is_valid():
                obj = serializer.save()
                obj.company = request.user.user_company
                obj.employment_type = employment_type
                obj.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Offer Letter Template added!",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "errors",
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

    @swagger_auto_schema(
        operation_description="This API Updates Offer Letter template. Along with other data in payload it also needs ID of the offer letter template in the request body",
        operation_summary="Offer Letter Template Update API",
        request_body=OfferLetterTemplateSerializer,
    )
    def put(self, request):
        try:
            data = request.data.copy()
            offer_letter_template = OfferLetterTemplate.objects.get(id=data.get("id"))
            try:
                country_list = data.get("country")
                country_list = json.loads(country_list)
                data["country"] = int(country_list[0]["value"])
            except Exception as e:
                if offer_letter_template.country:
                    data["country"] = offer_letter_template.country.id
                else:
                    data["country"] = None

            try:
                state_list = data.get("state")
                state_list = json.loads(state_list)
                data["state"] = int(state_list["value"])
            except Exception as e:
                if offer_letter_template.state:
                    data["state"] = offer_letter_template.state.id
                else:
                    data["state"] = None
            try:
                city_list = data.get("city")
                city_list = json.loads(city_list)
                data["city"] = int(city_list["value"])
            except Exception as e:
                if offer_letter_template.city:
                    data["city"] = offer_letter_template.city.id
                else:
                    data["city"] = None
            try:
                job_category_list = data.get("job_category")
                job_category_list = json.loads(job_category_list)
                data["job_category"] = int(job_category_list["value"])
            except Exception as e:
                if offer_letter_template.job_category:
                    data["job_category"] = offer_letter_template.job_category
                else:
                    data["job_category"] = None
            try:
                employment_type_list = json.loads(data.get("employment_type"))
                data["employment_type"] = employment_type_list
            except Exception as e:
                if offer_letter_template.employment_type:
                    data["employment_type"] = offer_letter_template.employment_type
                else:
                    data["employment_type"] = None
            employment_type = data.pop("employment_type")
            print(employment_type)
            print(data)
            serializer = OfferLetterTemplateSerializer(offer_letter_template, data=data, partial=True)
            if serializer.is_valid():
                obj = serializer.save()
                obj.employment_type = employment_type
                obj.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Offer Letter Template updated!",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "errors",
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

    @swagger_auto_schema(
        operation_description="This API fetches all the data of Offer Letter template",
        operation_summary="Offer Letter Template Get API",
        manual_parameters=[openapi.Parameter("id", in_=openapi.IN_QUERY, description="id", type=openapi.TYPE_STRING, required=True)],
    )
    def get(self, request):
        try:
            data = request.GET
            offer_letter_template = OfferLetterTemplate.objects.get(id=data.get("id"))
            serializer = OfferLetterTemplateGetSerializer(offer_letter_template)
            data = serializer.data
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Offer Letter Template fetched!",
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

    @swagger_auto_schema(
        operation_description="This API deletes the data of Offer Letter template",
        operation_summary="Offer Letter Template Delete API",
        manual_parameters=[openapi.Parameter("id", in_=openapi.IN_QUERY, description="id", type=openapi.TYPE_STRING, required=True)],
    )
    def delete(self, request):
        try:
            data = request.GET
            offer_letter_template = OfferLetterTemplate.objects.get(id=data.get("id"))
            offer_letter_template.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Offer Letter Template deleted!",
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


class GetAllOfferLetterTempalte(APIView):
    """
    This API returns a list of all the OfferLetterTemplates.
    Body-
        None
    Authentication-
        JWT
    Permission-
        IsAuthenticated for now, but it should be IsAdminUser.
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="This API fetches list of all the data of Offer Letter template",
        operation_summary="Offer Letter Template Get All API",
        manual_parameters=[
            openapi.Parameter(
                "search",
                in_=openapi.IN_QUERY,
                description="search",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "export",
                in_=openapi.IN_QUERY,
                description="export",
                type=openapi.TYPE_BOOLEAN,
            ),
            openapi.Parameter(
                "select_type",
                in_=openapi.IN_QUERY,
                description="select_type",
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request):
        print(request.user.user_role.id)
        try:
            data = request.GET
            offer_letter_templates = OfferLetterTemplate.objects.filter(company=request.user.user_company)
            search = data.get("search")
            if data.get("export"):
                export = True
            else:
                export = False
            if search:
                offer_letter_templates = search_data(offer_letter_templates, OfferLetterTemplate, search)
            serializer = OfferLetterTemplateGetSerializer(offer_letter_templates, many=True)
            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                if selected_fields:
                    selected_fields = selected_fields.last().selected_fields
                else:
                    selected_fields = ["Offer Type", "Offer ID", "Country"]
                writer.writerow(selected_fields)
                for data in offer_letter_templates:
                    serializer_data = OfferLetterTemplateGetSerializer(data).data
                    row = []
                    for field in selected_fields:
                        if field.lower() in ["country"]:
                            value = serializer_data["country"][0]["name"]
                        elif field == "Entity":
                            value = "Template"
                        else:
                            field = form_utils.offer_type_dict.get(field)
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
                        "code": status.HTTP_200_OK,
                        "message": "Offer Letter Template list fetched!",
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


class UploadedSignedOfferLetter(APIView):
    """
    This API enables to uploaded the signed offer letter to user.
    -Parameters
        id - id of offerletter
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Upload Signed Offer Letter API",
        operation_summary="Upload Signed Offer Letter API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "file": openapi.Schema(type=openapi.TYPE_FILE),
            },
            required=["file"],
        ),
    )
    def post(self, request, id):
        try:
            offer_letter_obj = OfferLetter.objects.get(id=id)
            if "file" in request.FILES:
                offer_letter_obj.signed_file = request.FILES["file"]
                offer_letter_obj.save()
                return ResponseOk(
                    {
                        "data": None,
                        "code": status.HTTP_200_OK,
                        "message": "File saved!",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": "Please upload a file",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "errors",
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


class WithdrawAppliedPosition(APIView):
    """
    This API withdraws a candidate from an applied position
    Args -
        pk - pk of applied_position
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def post(self, request, pk):
        try:
            applied_position_obj = AppliedPosition.objects.get(id=pk)
            if applied_position_obj.applied_profile == request.user.profile:
                applied_position_obj.withdrawn = True
                applied_position_obj.save()
            serializer = AppliedPositionSerializer(applied_position_obj)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "withdrawn from the position",
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


class GetNewHires(APIView):
    """
    API used to get list of new hire on HM's dashboard.
    Args:
        export - True or False value
    Body:
        None
    Returns:
        -success message and list of new hires(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        operation_description="Get list of Hires for HM's dashboard",
        manual_parameters=[
            export,
        ],
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET
            if data.get("export"):
                export = True
            else:
                export = False
            search = data.get("search", "")
            user = request.user
            if user.user_role.name == "recruiter":
                new_hires = OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True).filter(
                    start_date__gte=datetime.datetime.today().date(), email_changed=False
                )
            else:
                new_hires = (
                    OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True)
                    .filter(Q(offered_to__form_data__recruiter=request.user.email) | Q(offered_to__form_data__hiring_manager=request.user.email))
                    .filter(start_date__gte=datetime.datetime.today().date(), email_changed=False)
                )
            if search:
                new_hires = new_hires.annotate(
                    full_name=Concat("offered_to__applied_profile__user__first_name", V(" "), "offered_to__applied_profile__user__last_name"),
                    string_id=Cast("offered_to__form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=search) | Q(offered_to__form_data__form_data__job_title__icontains=search) | Q(string_id__icontains=search)
                )
            serializer = OfferLetterSerializer(new_hires, many=True)
            data = serializer.data

            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                if selected_fields:
                    selected_fields = selected_fields.first().selected_fields
                else:
                    selected_fields = ["Hiring Manager", "Position No", "Job Title", "Country", "Candidates Applied", "Status"]
                writer.writerow(selected_fields)
                for data in new_hires:
                    serializer_data = OfferLetterSerializer(data).data
                    row = []
                    for field in selected_fields:
                        if field.lower() in ["department", "category", "location", "country", "level", "employment type"]:
                            field = form_utils.position_dict.get(field)
                            try:
                                value = data.offered_to.form_data.form_data.get(field)[0].get("label")
                                if value is None:
                                    value = data.offered_to.form_data.form_data.get(field).get("name")
                            except Exception as e:
                                value = None
                        elif field in ["Position Name", "Job Title"]:
                            value = data.offered_to.form_data.form_data.get("job_title")
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
                        "data": data,
                        "code": status.HTTP_200_OK,
                        "message": "new hires fetched successfully",
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


class GetOpNewHires(APIView):
    """
    API used to get list of optimized new hire on HM's dashboard.
    Args:
        export - True or False value
    Body:
        None
    Returns:
        -success message and list of new hires(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        operation_description="Get list of Hires for HM's dashboard",
        manual_parameters=[
            export,
        ],
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET
            if data.get("export"):
                export = True
            else:
                export = False
            search = data.get("search", "")
            user = request.user
            if user.user_role.name == "recruiter":
                # new_hires = OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True).filter(
                #     start_date__gte=datetime.datetime.today().date(), email_changed=False
                # )
                new_hires = OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True).filter(
                    has_joined=False, email_changed=False
                )
            else:
                # new_hires = (
                #     OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True)
                #     .filter(Q(offered_to__form_data__recruiter=request.user.email) | Q(offered_to__form_data__hiring_manager=request.user.email))
                #     .filter(start_date__gte=datetime.datetime.today().date(), email_changed=False)
                # )
                new_hires = (
                    OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True)
                    .filter(Q(offered_to__form_data__recruiter=request.user.email) | Q(offered_to__form_data__hiring_manager=request.user.email))
                    .filter(has_joined=False, email_changed=False)
                )
            if search:
                new_hires = new_hires.annotate(
                    full_name=Concat("offered_to__applied_profile__user__first_name", V(" "), "offered_to__applied_profile__user__last_name"),
                    string_id=Cast("offered_to__form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=search) | Q(offered_to__form_data__form_data__job_title__icontains=search) | Q(string_id__icontains=search)
                )
            # serializer = OfferLetterSerializer(new_hires, many=True)
            # data = serializer.data

            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                fields = ["Position No", "Position Name", "Candidate Name", "Location", "Department", "Start Date", "Offer TTC"]
                writer.writerow(fields)
                for i in new_hires:
                    row = []
                    row.append(i.offered_to.form_data.show_id)
                    row.append(i.offered_to.form_data.form_data["job_title"])
                    row.append(i.offered_to.applied_profile.user.get_full_name())
                    row.append(i.offered_to.form_data.form_data["location"][0]["label"])
                    row.append(i.offered_to.applied_profile.address.country.name)
                    try:
                        row.append(i.offered_to.form_data.form_data["departments"][0]["label"])
                    except:
                        row.append(i.offered_to.form_data.form_data.get("department", [{}])[0].get("label"))
                    row.append(i.start_date)
                    row.append(i.target_compensation)
                    writer.writerow(row)
                response = HttpResponse(csv_response, content_type="text/csv")
                return response
            else:
                data = []
                for i in new_hires:
                    temp_data = {}
                    temp_data["id"] = i.id
                    temp_data["position_id"] = i.offered_to.form_data.id
                    temp_data["sposition_id"] = i.offered_to.form_data.show_id
                    temp_data["position_name"] = i.offered_to.form_data.form_data["job_title"]
                    temp_data["candidate_name"] = i.offered_to.applied_profile.user.get_full_name()
                    temp_data["location"] = i.offered_to.form_data.form_data["location"][0]["label"]
                    temp_data["country"] = i.offered_to.applied_profile.address.country.name
                    try:
                        temp_data["department"] = i.offered_to.form_data.form_data["departments"][0]["label"]
                    except:
                        temp_data["department"] = i.offered_to.form_data.form_data.get("department", [{}])[0].get("label")
                    try:
                        user_obj = User.objects.get(email__iexact=i.offered_to.form_data.hiring_manager, user_company=i.offered_to.form_data.company)
                        temp_data["hiring_manager"] = user_obj.get_full_name()
                    except:
                        temp_data["hiring_manager"] = i.offered_to.form_data.hiring_manager
                    try:
                        user_obj = User.objects.get(email__iexact=i.offered_to.form_data.recruiter, user_company=i.offered_to.form_data.company)
                        temp_data["recruiter"] = user_obj.get_full_name()
                    except:
                        temp_data["recruiter"] = i.offered_to.form_data.recruiter
                    temp_data["start_date"] = i.start_date
                    temp_data["target_compensation"] = i.target_compensation
                    try:
                        temp_data["signed_file"] = i.signed_file.url
                    except:
                        temp_data["signed_file"] = None
                    temp_data["applied_profile"] = i.offered_to.id
                    temp_data["user_applied_id"] = encrypt(i.offered_to.applied_profile.id)
                    data.append(temp_data)
                return ResponseOk(
                    {
                        "data": data,
                        "code": status.HTTP_200_OK,
                        "message": "new hires fetched successfully",
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


class SendHireEmail(APIView):
    """
    This API send an email to newly hired candidate.
    -body
        to
        cc
        body
    -permissions
        IsAuthenticated
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def post(self, request, pk):
        try:
            email_data = request.data
            from_email = settings.EMAIL_HOST_USER
            to = [email_data["to"]]
            cc = [email_data["cc"]]
            subject = email_data["subject"]
            content = email_data["content"]
            content = fetch_dynamic_email_template(content, to, pk, subject)
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "email sent",
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


class CareerTemplateView(APIView):
    """
    This API creates, updates, deletes and gets a single Career Template
    Args-
        None
    Body-
        All the fields from the CareerTemplate Model. In PUT method id needs to be passed in the Payload
    Return-
        Serialized data from the CareerTemplateSerializer
    Authentication-
        JWT
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(operation_summary="Career Template Create API", request_body=CareerTemplateSerializer)
    def post(self, request):
        try:
            data = request.data
            templates = CareerTemplate.objects.filter(company__id=data.get("company"))
            if templates:
                serializer = CareerTemplateSerializer(templates.last(), data=data)
            else:
                serializer = CareerTemplateSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "template created",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "errors",
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

    @swagger_auto_schema(operation_summary="Career Template Update API", request_body=CareerTemplateSerializer)
    def put(self, request):
        try:
            data = request.data
            career_template_obj = CareerTemplate.objects.get(id=data.get("id"))
            serializer = CareerTemplateSerializer(career_template_obj, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "updated template",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "errors",
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

    @swagger_auto_schema(
        operation_summary="Career Template GET API",
        manual_parameters=[
            openapi.Parameter(
                "id",
                in_=openapi.IN_QUERY,
                description="id of the career template",
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request):
        try:
            data = request.GET
            career_template_obj = CareerTemplate.objects.get(id=data.get("id"))
            serializer = CareerTemplateSerializer(career_template_obj)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "updated template",
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


class GetAllCareerTemplateView(APIView):

    """
    This API return all the Career Template
    Args-
        is_internal - to filter career template based on the internal or external
    Body-
        None
    Return-
        Serialized data from the CareerTemplateSerializer
    Authentication-
        JWT
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Get All Career Template API",
        manual_parameters=[
            openapi.Parameter(
                "is_internal",
                in_=openapi.IN_QUERY,
                description="is_internal true or false for filtering career template",
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request):
        try:
            data = request.GET
            is_internal = None
            if data.get("is_internal") == "false":
                is_internal = False
            elif data.get("is_internal") == "true":
                is_internal = True
            career_template_obj = CareerTemplate.objects.all()
            if is_internal is not None:
                career_template_obj = career_template_obj.filter(is_internal=is_internal)
            serializer = CareerTemplateSerializer(career_template_obj, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "updated template",
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


class GetMacros(APIView):

    """
    It returns the list of all the macros
    used in the fetch_dynamic_email_template.
    If want to add some more, add it to choices.py in app module
    """

    def get(self, request):
        macros = choices.MACROS
        try:
            return ResponseOk(
                {
                    "data": macros,
                    "code": status.HTTP_200_OK,
                    "message": "updated template",
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


class GetInsights(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    """
    API to fetch different insights.
    Args:
        lable,
        values,
        office,
        positions,
        start_date,
        end_date,
        user_id,
    Body:
        None
    Returns:
        -success message with Insights(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    @swagger_auto_schema(
        operation_summary="Get Insights API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the department",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "office", in_=openapi.IN_QUERY, description="comma separated name of location/coutry", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "positions",
                in_=openapi.IN_QUERY,
                description="comma separated positions",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "user_id",
                in_=openapi.IN_QUERY,
                description="user_id",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "end_date",
                in_=openapi.IN_QUERY,
                description="end_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "start_date",
                in_=openapi.IN_QUERY,
                description="start_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "timeframe",
                in_=openapi.IN_QUERY,
                description="time frame of the chart i.e month, week, year etc.",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            response = {}
            days = 0
            count = 0
            start_date = None
            end_date = None
            url_domain = None
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if "lable" in data and "values" in data:
                departments = data.get("lable").split(",")
                values = data.get("values").split(",")
                complete_department_list = []
                for department, value in zip(departments, values):
                    temp = [{"label": department, "value": int(value)}]
                    complete_department_list.append(temp)
            else:
                complete_department_list = []
            if "office" in data:
                office = data.get("office").split(",")
            else:
                office = []
            if "positions" in data:
                positions = data.get("positions").split(",")
            else:
                positions = []
            if "user_id" in data:
                user_ids = data.get("user_id").split(",")
            else:
                user_ids = []
            if "end_date" in data:
                end_date = datetime.datetime.strptime(data.get("end_date"), "%Y-%m-%d").date()
            else:
                end_date = datetime.datetime.today().date()
            if "start_date" in data:
                start_date = datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
            else:
                start_date = datetime.datetime.today().date() - timedelta(30)
            if "timeframe" in data:
                timeframe = data.get("timeframe")
            else:
                timeframe = "month"
            # Get all form data of user and its team mebers
            temp_form_data = FormData.objects.filter(company__url_domain=url_domain)
            form_data = FormData.objects.filter(company__url_domain=url_domain).filter(
                Q(hiring_manager=request.user.email) | Q(recruiter=request.user.email)
            )
            teams_obj, created = Team.objects.get_or_create(manager=request.user.profile)
            members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
            members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
            form_data = members_fd_obj | form_data
            if complete_department_list:
                form_data = form_data.filter(form_data__department__in=complete_department_list)
            if office:
                form_data = form_data.filter(form_data__country__name__in=office)
            if positions:
                form_data = form_data.filter(id__in=positions)
            if user_ids:
                emails = list(Profile.objects.filter(id__in=user_ids).values_list("user__email", flat=True))
                form_data_id = list(form_data.filter(Q(hiring_manager__in=emails) | Q(recruiter__in=emails)).values_list("id", flat=True))
            else:
                form_data_id = []
            if form_data_id:
                form_data = form_data.filter(id__in=form_data_id)
            # Get Applied position of user and its team members
            applied_position_list = get_all_applied_position(request.user.profile)
            accepted_offers = OfferLetter.objects.filter(accepted=True, response_date__gte=start_date, response_date__lte=end_date).filter(
                offered_to__id__in=applied_position_list
            )
            offers_declines = OfferLetter.objects.filter(is_decline=True, response_date__gte=start_date, response_date__lte=end_date).filter(
                offered_to__id__in=applied_position_list
            )
            overall_applications = AppliedPosition.objects.filter(
                company__url_domain=url_domain, created_at__date__gte=start_date, created_at__date__lte=end_date
            ).filter(id__in=applied_position_list)
            if complete_department_list:
                accepted_offers = accepted_offers.filter(offered_to__form_data__form_data__department__in=complete_department_list)
                offers_declines = offers_declines.filter(offered_to__form_data__form_data__department__in=complete_department_list)
                overall_applications = overall_applications.filter(form_data__form_data__department__in=complete_department_list)
            if office:
                accepted_offers = accepted_offers.filter(offered_to__form_data__form_data__location__0__label__in=office)
                offers_declines = offers_declines.filter(offered_to__form_data__form_data__location__0__label__in=office)
                overall_applications = overall_applications.filter(form_data__form_data__location__0__label__in=office)
            if positions:
                accepted_offers = accepted_offers.filter(offered_to__form_data__id__in=positions)
                offers_declines = offers_declines.filter(offered_to__form_data__id__in=positions)
                overall_applications = overall_applications.filter(form_data__id__in=positions)
            if form_data_id:
                accepted_offers = accepted_offers.filter(offered_to__form_data__in__in=form_data_id)
                offers_declines = offers_declines.filter(offered_to__form_data__id__in=form_data_id)
                overall_applications = overall_applications.filter(form_data__id__in=form_data_id)
            source_of_hiring = (
                AppliedPosition.objects.filter(form_data__in=form_data, created_at__date__gte=start_date, created_at__date__lte=end_date)
                .filter(id__in=applied_position_list)
                .values("applicant_details__source")
                .annotate(total=Count("applicant_details__source"))
            )
            source_of_hiring_data = []
            no_source_dict = {}
            no_source_dict["source"] = "No Source"
            no_source_dict["count"] = 0
            for source in source_of_hiring:
                temp_dict = {}
                print(source["applicant_details__source"], "-------------")
                stringed_source = source["applicant_details__source"]
                if source["applicant_details__source"] == "" or source["applicant_details__source"].lower() == "no source":
                    no_source_dict["count"] = no_source_dict["count"] + source["total"]
                else:
                    temp_dict["source"] = source["applicant_details__source"]
                    temp_dict["count"] = source["total"]
                    source_of_hiring_data.append(temp_dict)
            source_of_hiring_data.append(no_source_dict)
            response["source_of_hiring"] = source_of_hiring_data
            company_hire_data_dict = {}
            company_hire_data = []
            for offer in accepted_offers:
                experiences = Experience.objects.filter(profile=offer.offered_to.applied_profile, is_current_company=True)
                if experiences:
                    last_exp = experiences[0]
                    try:
                        company_hire_data_dict[last_exp.company_name] += 1
                    except Exception as e:
                        company_hire_data_dict[last_exp.company_name] = 1
            for key, value in company_hire_data_dict.items():
                temp_dict = {}
                temp_dict["company"] = key
                temp_dict["count"] = value
                company_hire_data.append(temp_dict)
            response["company_hire_data"] = company_hire_data
            if timeframe == "month":
                timeframed_accepted_offers = (
                    accepted_offers.annotate(month=ExtractMonth("response_date")).values("month").annotate(total=Count("id")).order_by()
                )
                timeframed_accepted_offers_data = []
                for timeframed in timeframed_accepted_offers:
                    temp_dict = {}
                    temp_dict["month"] = calendar.month_name[timeframed["month"]]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_accepted_offers_data.append(temp_dict)
                timeframed_offers_declines = offers_declines.annotate(month=ExtractMonth("response_date")).values("month").annotate(total=Count("id"))
                timeframed_offers_declines_data = []
                for timeframed in timeframed_offers_declines:
                    temp_dict = {}
                    temp_dict["month"] = calendar.month_name[timeframed["month"]]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_offers_declines_data.append(temp_dict)
                timeframed_overall_applications = (
                    overall_applications.annotate(month=ExtractMonth("created_at")).values("month").annotate(total=Count("id"))
                )
                timeframed_overall_applications_data = []
                for timeframed in timeframed_overall_applications:
                    temp_dict = {}
                    temp_dict["month"] = calendar.month_name[timeframed["month"]]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_overall_applications_data.append(temp_dict)
                response["accept_offer_data"] = timeframed_accepted_offers_data
                response["offers_declines_data"] = timeframed_offers_declines_data
                response["overall_applications_data"] = timeframed_overall_applications_data
            elif timeframe == "quarter":
                timeframed_accepted_offers = (
                    accepted_offers.annotate(quarter=ExtractQuarter("response_date")).values("quarter").annotate(total=Count("id")).order_by()
                )
                timeframed_accepted_offers_data = []
                for timeframed in timeframed_accepted_offers:
                    temp_dict = {}
                    temp_dict["qaurter-number"] = timeframed["quarter"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_accepted_offers_data.append(temp_dict)
                timeframed_offers_declines = (
                    offers_declines.annotate(quarter=ExtractQuarter("response_date")).values("quarter").annotate(total=Count("id"))
                )
                timeframed_offers_declines_data = []
                for timeframed in timeframed_offers_declines:
                    temp_dict = {}
                    temp_dict["qaurter-number"] = timeframed["quarter"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_offers_declines_data.append(temp_dict)
                timeframed_overall_applications = (
                    overall_applications.annotate(quarter=ExtractQuarter("created_at")).values("quarter").annotate(total=Count("id"))
                )
                timeframed_overall_applications_data = []
                for timeframed in timeframed_overall_applications:
                    temp_dict = {}
                    temp_dict["qaurter-number"] = timeframed["quarter"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_overall_applications_data.append(temp_dict)
                response["accept_offer_data"] = timeframed_accepted_offers_data
                response["offers_declines_data"] = timeframed_offers_declines_data
                response["overall_applications_data"] = timeframed_overall_applications_data
            elif timeframe == "week":
                timeframed_accepted_offers = (
                    accepted_offers.annotate(week=ExtractWeek("response_date")).values("week").annotate(total=Count("id")).order_by()
                )
                timeframed_accepted_offers_data = []
                for timeframed in timeframed_accepted_offers:
                    temp_dict = {}
                    temp_dict["week-number"] = timeframed["week"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_accepted_offers_data.append(temp_dict)
                timeframed_offers_declines = offers_declines.annotate(week=ExtractWeek("response_date")).values("week").annotate(total=Count("id"))
                timeframed_offers_declines_data = []
                for timeframed in timeframed_offers_declines:
                    temp_dict = {}
                    temp_dict["week-number"] = timeframed["week"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_offers_declines_data.append(temp_dict)
                timeframed_overall_applications = (
                    overall_applications.annotate(week=ExtractWeek("created_at")).values("week").annotate(total=Count("id"))
                )
                timeframed_overall_applications_data = []
                for timeframed in timeframed_overall_applications:
                    temp_dict = {}
                    temp_dict["week-number"] = timeframed["week"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_overall_applications_data.append(temp_dict)
                response["accept_offer_data"] = timeframed_accepted_offers_data
                response["offers_declines_data"] = timeframed_offers_declines_data
                response["overall_applications_data"] = timeframed_overall_applications_data
            elif timeframe == "year":
                timeframed_accepted_offers = (
                    accepted_offers.annotate(year=ExtractYear("response_date")).values("year").annotate(total=Count("id")).order_by()
                )
                timeframed_accepted_offers_data = []
                for timeframed in timeframed_accepted_offers:
                    temp_dict = {}
                    temp_dict["year"] = timeframed["year"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_accepted_offers_data.append(temp_dict)
                timeframed_offers_declines = offers_declines.annotate(year=ExtractYear("response_date")).values("year").annotate(total=Count("id"))
                timeframed_offers_declines_data = []
                for timeframed in timeframed_offers_declines:
                    temp_dict = {}
                    temp_dict["year"] = timeframed["year"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_offers_declines_data.append(temp_dict)
                timeframed_overall_applications = (
                    overall_applications.annotate(year=ExtractYear("created_at")).values("year").annotate(total=Count("id"))
                )
                timeframed_overall_applications_data = []
                for timeframed in timeframed_overall_applications:
                    temp_dict = {}
                    temp_dict["year"] = timeframed["year"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_overall_applications_data.append(temp_dict)
                response["accept_offer_data"] = timeframed_accepted_offers_data
                response["offers_declines_data"] = timeframed_offers_declines_data
                response["overall_applications_data"] = timeframed_overall_applications_data
            elif timeframe == "day":
                timeframed_accepted_offers = (
                    accepted_offers.annotate(day=TruncDate("response_date")).values("day").annotate(total=Count("id")).order_by()
                )
                timeframed_accepted_offers_data = []
                for timeframed in timeframed_accepted_offers:
                    temp_dict = {}
                    temp_dict["day"] = timeframed["day"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_accepted_offers_data.append(temp_dict)
                timeframed_offers_declines = offers_declines.annotate(day=TruncDate("response_date")).values("day").annotate(total=Count("id"))
                timeframed_offers_declines_data = []
                for timeframed in timeframed_offers_declines:
                    temp_dict = {}
                    temp_dict["day"] = timeframed["day"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_offers_declines_data.append(temp_dict)
                timeframed_overall_applications = overall_applications.annotate(day=TruncDate("created_at")).values("day").annotate(total=Count("id"))
                timeframed_overall_applications_data = []
                for timeframed in timeframed_overall_applications:
                    temp_dict = {}
                    temp_dict["day"] = timeframed["day"]
                    temp_dict["count"] = timeframed["total"]
                    timeframed_overall_applications_data.append(temp_dict)
                response["accept_offer_data"] = timeframed_accepted_offers_data
                response["offers_declines_data"] = timeframed_offers_declines_data
                response["overall_applications_data"] = timeframed_overall_applications_data
            else:
                return ResponseOk({"data": {}, "code": status.HTTP_200_OK, "message": "No data"})
            reasons_offers_declines = offers_declines.values("decline_reason").annotate(total=Count("id"))
            reasons_offers_declines_data = []
            for timeframed in reasons_offers_declines:
                temp_dict = {}
                temp_dict["decline_reason"] = timeframed["decline_reason"]
                temp_dict["count"] = timeframed["total"]
                reasons_offers_declines_data.append(temp_dict)
            response["reasons_offers_declines_data"] = reasons_offers_declines_data

            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "Data Fetched",
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


class GetReviewToInterviewInsights(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    """
    API to fetch review to interview insights.
    Args:
        lable,
        values,
        office,
        positions,
        start_date,
        end_date,
        user_id,
    Body:
        None
    Returns:
        -success message with review to interview insights(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    @swagger_auto_schema(
        operation_summary="Get review to interview Insights API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the department",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "office", in_=openapi.IN_QUERY, description="comma separated name of location/coutry", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "positions",
                in_=openapi.IN_QUERY,
                description="comma separated positions",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "user_id",
                in_=openapi.IN_QUERY,
                description="user_id",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "end_date",
                in_=openapi.IN_QUERY,
                description="end_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "start_date",
                in_=openapi.IN_QUERY,
                description="start_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
    )
    def get(self, request):
        try:
            response = {}
            url_domain = None
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if "lable" in data and "values" in data:
                departments = data.get("lable").split(",")
                values = data.get("values").split(",")
                complete_department_list = []
                for department, value in zip(departments, values):
                    temp = [{"label": department, "value": int(value)}]
                    complete_department_list.append(temp)
            else:
                complete_department_list = None
            if "office" in data:
                office = data.get("office").split(",")
            else:
                office = []
            if "positions" in data:
                positions = data.get("positions").split(",")
            else:
                positions = []
            if "user_id" in data:
                user_ids = data.get("user_id")
            else:
                user_ids = []
            if "end_date" in data:
                end_date = datetime.datetime.strptime(data.get("end_date"), "%Y-%m-%d").date()
            else:
                end_date = datetime.datetime.today().date()
            if "start_date" in data:
                start_date = datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
            else:
                start_date = datetime.datetime.today().date() - timedelta(30)
            # Get Applied position of user and its team members
            applied_position_list = get_all_applied_position(request.user.profile)
            # Calculate candidates reviews to interview ratio
            applied_positions = AppliedPosition.objects.filter(
                company__url_domain=url_domain, created_at__date__gte=start_date, created_at__date__lte=end_date
            ).filter(id__in=applied_position_list)
            if user_ids:
                emails = list(Profile.objects.filter(id__in=user_ids).values_list("user__email", flat=True))
                form_data_id = list(FormData.objects.filter(Q(hiring_manager__in=emails) | Q(recruiter__in=emails)).values_list("id", flat=True))
            else:
                form_data_id = []
            if complete_department_list:
                applied_positions = applied_positions.filter(form_data__form_data__department__in=complete_department_list)
            if office:
                applied_positions = applied_positions.filter(form_data__form_data__location__0__label__in=office)
            if positions:
                applied_positions = applied_positions.filter(form_data__id__in=positions)
            if form_data_id:
                applied_positions = applied_positions.filter(form_data__id__in=form_data_id)
            resume_reviews_count = 0
            hm_review_count = 0
            tech_interview_count = 0
            final_interview_count = 0
            interview = 0
            for application in applied_positions:
                try:
                    current_stage = application.data["current_stage_id"]
                    stage_obj = Stage.objects.filter(id=current_stage).last()
                    if "resume review" in stage_obj.stage_name.lower():
                        resume_reviews_count += 1
                    if "hiring manager review" in stage_obj.stage_name.lower():
                        hm_review_count += 1
                    if "technical interview" in stage_obj.stage_name.lower():
                        tech_interview_count += 1
                    if "final interview" in stage_obj.stage_name.lower():
                        final_interview_count += 1
                    if "interview" in stage_obj.stage_name.lower():
                        interview += 1
                except Exception as e:
                    print(e)
            total = resume_reviews_count + hm_review_count + tech_interview_count + final_interview_count
            candidate_review_to_interview_data = {}
            candidate_review_to_interview_data["Resume_Reviews_Count"] = resume_reviews_count
            candidate_review_to_interview_data["HM_Review_Count"] = hm_review_count
            candidate_review_to_interview_data["Technical_Interview_Count"] = tech_interview_count
            candidate_review_to_interview_data["Final_Interview_Count"] = final_interview_count
            candidate_review_to_interview_data["Interview_Count"] = interview
            candidate_review_to_interview_data["ratio"] = {}
            if total:
                candidate_review_to_interview_data["ratio"]["Resume_Reviews_Count"] = round(resume_reviews_count / total, 2)
                candidate_review_to_interview_data["ratio"]["HM_Review_Count"] = round(hm_review_count / total, 2)
                candidate_review_to_interview_data["ratio"]["Technical_Interview_Count"] = round(tech_interview_count / total, 2)
                candidate_review_to_interview_data["ratio"]["Final_Interview_Count"] = round(final_interview_count / total, 2)
                candidate_review_to_interview_data["ratio"]["Interview_Count"] = round(interview / total, 2)
            else:
                candidate_review_to_interview_data["ratio"]["Resume_Reviews_Count"] = 0
                candidate_review_to_interview_data["ratio"]["HM_Review_Count"] = 0
                candidate_review_to_interview_data["ratio"]["Technical_Interview_Count"] = 0
                candidate_review_to_interview_data["ratio"]["Final_Interview_Count"] = 0
            response["candidate_review_to_interview"] = candidate_review_to_interview_data
            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "Data Fetched",
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


class GetAvgFileTime(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    """
    API to fetch average file time insights.
    Args:
        lable,
        values,
        office,
        positions,
        start_date,
        end_date,
        user_id,
    Body:
        None
    Returns:
        -success message with average file time insights(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    @swagger_auto_schema(
        operation_summary="Get average file time Insights API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the department",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "office", in_=openapi.IN_QUERY, description="comma separated name of location/coutry", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "positions",
                in_=openapi.IN_QUERY,
                description="comma separated positions",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "user_id",
                in_=openapi.IN_QUERY,
                description="user_id",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "end_date",
                in_=openapi.IN_QUERY,
                description="end_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "start_date",
                in_=openapi.IN_QUERY,
                description="start_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
    )
    def get(self, request):
        try:
            response = {}
            url_domain = None
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if "lable" in data and "values" in data:
                departments = data.get("lable").split(",")
                values = data.get("values").split(",")
                complete_department_list = []
                for department, value in zip(departments, values):
                    temp = [{"label": department, "value": int(value)}]
                    complete_department_list.append(temp)
            else:
                complete_department_list = []
            if "office" in data:
                office = data.get("office").split(",")
            else:
                office = []
            if "positions" in data:
                positions = data.get("positions").split(",")
            else:
                positions = []
            if "user_id" in data:
                user_ids = data.get("user_id")
            else:
                user_ids = []
            if "end_date" in data:
                end_date = datetime.datetime.strptime(data.get("end_date"), "%Y-%m-%d").date()
            else:
                end_date = datetime.datetime.today().date()
            if "start_date" in data:
                start_date = datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
            else:
                start_date = datetime.datetime.today().date() - timedelta(30)
            temp_form_data = FormData.objects.filter(status="closed", updated_at__date__gte=start_date, updated_at__date__lte=end_date)
            closed_position = temp_form_data.filter(Q(hiring_manager=request.user.email) | Q(recruiter=request.user.email))
            teams_obj, created = Team.objects.get_or_create(manager=request.user.profile)
            members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
            members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
            closed_position = members_fd_obj | closed_position
            if complete_department_list:
                closed_position = closed_position.filter(form_data__department__in=complete_department_list)
            if office:
                closed_position = closed_position.filter(form_data__country__name__in=office)
            if positions:
                closed_position = closed_position.filter(form_data__id__in=position)
            if user_ids:
                emails = list(Profile.objects.filter(id__in=user_ids).values_list("user__email", flat=True))
                form_data_id = list(
                    closed_position.objects.filter(Q(hiring_manager__in=emails) | Q(recruiter__in=emails)).values_list("id", flat=True)
                )
            else:
                form_data_id = []
            if form_data_id:
                closed_position = closed_position.filter(form_data__id__in=form_data_id)
            total_count = 0
            total_time = 0
            for position in closed_position:
                td = position.updated_at - position.created_at
                total_time += td.days
                total_count += 1
            if total_count:
                avg = round(total_time / total_count, 2)
            else:
                avg = 0
            response["avg-time-to-fill"] = avg
            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "Data Fetched",
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


class GetAvgTimeInStage(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    """
    API to fetch average time in stage insights.
    Args:
        lable,
        values,
        office,
        positions,
        start_date,
        end_date,
        user_id,
    Body:
        None
    Returns:
        -success message with average time in stage insights(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    @swagger_auto_schema(
        operation_summary="Get average time in stage insights API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the department",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "office", in_=openapi.IN_QUERY, description="comma separated name of location/coutry", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "positions",
                in_=openapi.IN_QUERY,
                description="comma separated positions",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "user_id",
                in_=openapi.IN_QUERY,
                description="user_id",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "end_date",
                in_=openapi.IN_QUERY,
                description="end_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "start_date",
                in_=openapi.IN_QUERY,
                description="start_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
    )
    def get(self, request):
        try:
            response = {}
            url_domain = None
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if "lable" in data and "values" in data:
                departments = data.get("lable").split(",")
                values = data.get("values").split(",")
                complete_department_list = []
                for department, value in zip(departments, values):
                    temp = [{"label": department, "value": int(value)}]
                    complete_department_list.append(temp)
            else:
                complete_department_list = []
            if "office" in data:
                office = data.get("office").split(",")
            else:
                office = []
            if "positions" in data:
                positions = data.get("positions").split(",")
            else:
                positions = []
            if "user_id" in data:
                user_ids = data.get("user_id")
            else:
                user_ids = []
            if "end_date" in data:
                end_date = datetime.datetime.strptime(data.get("end_date"), "%Y-%m-%d").date()
            else:
                end_date = datetime.datetime.today().date()
            if "start_date" in data:
                start_date = datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
            else:
                start_date = datetime.datetime.today().date() - timedelta(30)
            # Get Applied position of user and its team members
            applied_position_list = get_all_applied_position(request.user.profile)
            # Calculate candidates reviews to interview ratio
            applied_positions = AppliedPosition.objects.filter(
                company__url_domain=url_domain, created_at__date__gte=start_date, created_at__date__lte=end_date
            ).filter(id__in=applied_position_list)
            if complete_department_list:
                applied_positions = applied_positions.filter(form_data__form_data__department__in=complete_department_list)
            if office:
                applied_positions = applied_positions.filter(form_data__form_data__location__0__label__in=office)
            if positions:
                applied_positions = applied_positions.filter(form_data__id__in=positions)
            if user_ids:
                emails = list(Profile.objects.filter(id__in=user_ids).values_list("user__email", flat=True))
                form_data_id = list(FormData.objects.filter(Q(hiring_manager__in=emails) | Q(recruiter__in=emails)).values_list("id", flat=True))
            else:
                form_data_id = []
            if form_data_id:
                applied_positions = applied_positions.filter(form_data__id__in=form_data_id)
            total_days = 0
            total_stages = 0
            current_date = None
            for applied_position in applied_positions:
                if "history" in applied_position.data:
                    current_date = None
                    for history in applied_position.data["history_detail"]:
                        print(history)
                        try:
                            date = datetime.datetime.strptime(history["date"], "%d %B, %Y")
                        except:
                            date = datetime.datetime.strptime(history["date"], "%d %B,%Y")
                        if current_date is not None:
                            total_stages += 1
                            stage_diff = date - current_date
                            print(stage_diff.days)
                            total_days += stage_diff.days
                            current_date = date
                        else:
                            current_date = date
            if total_stages:
                avd_time_in_stage = round(total_days / total_stages, 2)
            else:
                avd_time_in_stage = 0
            response["avd-time-in-stage"] = avd_time_in_stage
            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "Data Fetched",
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


class GetCompaniesRejectedAfterReview(APIView):
    """
    API to fetch companies rejected after review insights.
    Args:
        lable,
        values,
        office,
        positions,
        start_date,
        end_date,
        user_id,
    Body:
        None
    Returns:
        -success message with companies rejected after review insights(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    @swagger_auto_schema(
        operation_summary="Get companies rejected after review insights API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the department",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "office", in_=openapi.IN_QUERY, description="comma separated name of location/coutry", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "positions",
                in_=openapi.IN_QUERY,
                description="comma separated positions",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "user_id",
                in_=openapi.IN_QUERY,
                description="user_id",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "end_date",
                in_=openapi.IN_QUERY,
                description="end_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "start_date",
                in_=openapi.IN_QUERY,
                description="start_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
    )
    def get(self, request):
        try:
            response = {}
            url_domain = None
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if "lable" in data and "values" in data:
                departments = data.get("lable").split(",")
                values = data.get("values").split(",")
                complete_department_list = []
                for department, value in zip(departments, values):
                    temp = [{"label": department, "value": int(value)}]
                    complete_department_list.append(temp)
            else:
                complete_department_list = []
            if "office" in data:
                office = data.get("office").split(",")
            else:
                office = []
            if "positions" in data:
                positions = data.get("positions").split(",")
            else:
                positions = []
            if "user_id" in data:
                user_ids = data.get("user_id")
            else:
                user_ids = []
            if "end_date" in data:
                end_date = datetime.datetime.strptime(data.get("end_date"), "%Y-%m-%d").date()
            else:
                end_date = datetime.datetime.today().date()
            if "start_date" in data:
                start_date = datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
            else:
                start_date = datetime.datetime.today().date() - timedelta(30)
            # Get Applied position of user and its team members
            applied_position_list = get_all_applied_position(request.user.profile)
            applied_positions = AppliedPosition.objects.filter(
                company__url_domain=url_domain, created_at__date__gte=start_date, created_at__date__lte=end_date, application_status="reject"
            ).filter(id__in=applied_position_list)
            if complete_department_list:
                applied_positions = applied_positions.filter(form_data__form_data__department__in=complete_department_list)
            if office:
                applied_positions = applied_positions.filter(form_data__form_data__location__0__label__in=office)
            if positions:
                applied_positions = applied_positions.filter(form_data__id__in=positions)
            if user_ids:
                emails = list(Profile.objects.filter(id__in=user_ids).values_list("user__email", flat=True))
                form_data_id = list(FormData.objects.filter(Q(hiring_manager__in=emails) | Q(recruiter__in=emails)).values_list("id", flat=True))
            else:
                form_data_id = []
            if form_data_id:
                applied_positions = applied_positions.filter(form_data__id__in=form_data_id)
            rejects_after_reviews_count = 0
            resume_stage_ids = list(Stage.objects.filter(stage_name__icontains="resume").values_list("id", flat=True))
            for application in applied_positions:
                if "history" in application.data:
                    history_list = application.data["history"]
                    if any(x in history_list for x in resume_stage_ids):
                        rejects_after_reviews_count += 1
            response["rejects_after_reviews_count"] = rejects_after_reviews_count
            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "Data Fetched",
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


class GetPipeLine(APIView):
    """
    API to fetch pipeline insights.
    Args:
        lable,
        values,
        office,
        positions,
        start_date,
        end_date,
        user_id,
    Body:
        None
    Returns:
        -success message with pipeline insights(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    @swagger_auto_schema(
        operation_summary="Get pipeline insights API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the department",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "office", in_=openapi.IN_QUERY, description="comma separated name of location/coutry", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "positions",
                in_=openapi.IN_QUERY,
                description="comma separated positions",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "user_id",
                in_=openapi.IN_QUERY,
                description="user_id",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "end_date",
                in_=openapi.IN_QUERY,
                description="end_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "start_date",
                in_=openapi.IN_QUERY,
                description="start_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
    )
    def get(self, request):
        try:
            response = {}
            url_domain = None
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if "lable" in data and "values" in data:
                departments = data.get("lable").split(",")
                values = data.get("values").split(",")
                complete_department_list = []
                for department, value in zip(departments, values):
                    temp = [{"label": department, "value": int(value)}]
                    complete_department_list.append(temp)
            else:
                complete_department_list = []
            if "office" in data:
                office = data.get("office").split(",")
            else:
                office = []
            if "positions" in data:
                positions = data.get("positions").split(",")
            else:
                positions = []
            if "user_id" in data:
                user_ids = data.get("user_id")
            else:
                user_ids = []
            if "end_date" in data:
                end_date = datetime.datetime.strptime(data.get("end_date"), "%Y-%m-%d").date()
            else:
                end_date = datetime.datetime.today().date()
            if "start_date" in data:
                start_date = datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
            else:
                start_date = datetime.datetime.today().date() - timedelta(30)
            # Get Applied position of user and its team members
            applied_position_list = get_all_applied_position(request.user.profile)
            applied_positions = AppliedPosition.objects.filter(
                company__url_domain=url_domain, created_at__date__gte=start_date, created_at__date__lte=end_date
            ).filter(id__in=applied_position_list)
            if complete_department_list:
                applied_positions = applied_positions.filter(form_data__form_data__department__in=complete_department_list)
            if office:
                applied_positions = applied_positions.filter(form_data__form_data__country__name__in=office)
            if positions:
                applied_positions = applied_positions.filter(form_data__id__in=positions)
            if user_ids:
                emails = list(Profile.objects.filter(id__in=user_ids).values_list("user__email", flat=True))
                form_data_id = list(FormData.objects.filter(Q(hiring_manager__in=emails) | Q(recruiter__in=emails)).values_list("id", flat=True))
            else:
                form_data_id = []
            if form_data_id:
                applied_positions = applied_positions.filter(form_data__id__in=form_data_id)
            pipe_line_data = []
            for applied_position in applied_positions:
                if "history_detail" in applied_position.data:
                    try:
                        current_stage = applied_position.data["current_stage_id"]
                        stage_obj = Stage.objects.filter(id=current_stage).last()
                        item = [item for item in pipe_line_data if item.get("name") == stage_obj.stage_name]
                        if item:
                            item = item[0]
                            pipe_line_data.remove(item)
                            item["count"] += 1
                            pipe_line_data.append(item)
                        else:
                            temp_item = {}
                            temp_item["name"] = stage_obj.stage_name
                            temp_item["count"] = 1
                            temp_item["order"] = stage_obj.sort_order
                            pipe_line_data.append(temp_item)
                    except Exception as e:
                        print(e)
            for stage in Stage.objects.filter(company__url_domain=url_domain, pipeline__pipeline_name="Hiring Stage").order_by("sort_order"):
                if stage.stage_name not in [x["name"] for x in pipe_line_data]:
                    temp_item = {}
                    temp_item["name"] = stage.stage_name
                    temp_item["count"] = 0
                    temp_item["order"] = stage.sort_order
                    pipe_line_data.append(temp_item)
            pipe_line_data = sorted(pipe_line_data, key=lambda d: d["order"])
            for i in pipe_line_data:
                response[i["name"]] = i["count"]
            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "Data Fetched",
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


class GetAvgTimeToHire(APIView):
    """
    API to fetch average time to hire insights.
    Args:
        lable,
        values,
        office,
        positions,
        start_date,
        end_date,
        user_id,
    Body:
        None
    Returns:
        -success message with average time to hire insights(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    @swagger_auto_schema(
        operation_summary="Get average time to hire insights API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the department",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "office", in_=openapi.IN_QUERY, description="comma separated name of location/coutry", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "positions",
                in_=openapi.IN_QUERY,
                description="comma separated positions",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "user_id",
                in_=openapi.IN_QUERY,
                description="user_id",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "end_date",
                in_=openapi.IN_QUERY,
                description="end_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "start_date",
                in_=openapi.IN_QUERY,
                description="start_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
    )
    def get(self, request):
        try:
            response = {}
            url_domain = None
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if "lable" in data and "values" in data:
                departments = data.get("lable").split(",")
                values = data.get("values").split(",")
                complete_department_list = []
                for department, value in zip(departments, values):
                    temp = [{"label": department, "value": int(value)}]
                    complete_department_list.append(temp)
            else:
                complete_department_list = []
            if "office" in data:
                office = data.get("office").split(",")
            else:
                office = []
            if "positions" in data:
                positions = data.get("positions").split(",")
            else:
                positions = []
            if "user_id" in data:
                user_ids = data.get("user_id")
            else:
                user_ids = []
            if "end_date" in data:
                end_date = datetime.datetime.strptime(data.get("end_date"), "%Y-%m-%d").date()
            else:
                end_date = datetime.datetime.today().date()
            if "start_date" in data:
                start_date = datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
            else:
                start_date = datetime.datetime.today().date() - timedelta(30)
            # Get Applied position of user and its team members
            applied_position_list = get_all_applied_position(request.user.profile)
            applied_positions = AppliedPosition.objects.filter(
                company__url_domain=url_domain, created_at__date__gte=start_date, created_at__date__lte=end_date, application_status="hired"
            ).filter(id__in=applied_position_list)
            if complete_department_list:
                applied_positions = applied_positions.filter(form_data__form_data__department__in=complete_department_list)
            if office:
                applied_positions = applied_positions.filter(form_data__form_data__country__name__in=office)
            if positions:
                applied_positions = applied_positions.filter(form_data__id__in=positions)
            if user_ids:
                emails = list(Profile.objects.filter(id__in=user_ids).values_list("user__email", flat=True))
                form_data_id = list(FormData.objects.filter(Q(hiring_manager__in=emails) | Q(recruiter__in=emails)).values_list("id", flat=True))
            else:
                form_data_id = []
            if form_data_id:
                applied_positions = applied_positions.filter(form_data__id__in=form_data_id)
            total_days = 0
            total_candidates = 0
            for applied_position in applied_positions:
                offer_letter_objs = OfferLetter.objects.filter(offered_to=applied_position)
                if offer_letter_objs:
                    offer_letter_obj = offer_letter_objs[0]
                    diff = offer_letter_obj.start_date - applied_position.created_at.date()
                    total_days += diff.days
                    total_candidates += 1
            if total_candidates:
                avd_time_to_file = round(total_days / total_candidates, 2)
            else:
                avd_time_to_file = 0
            response["avd-time-to-hire"] = avd_time_to_file

            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "Data Fetched",
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


class GetReviewToReject(APIView):
    """
    API to fetch review to reject insights.
    Args:
        lable,
        values,
        office,
        positions,
        start_date,
        end_date,
        user_id,
    Body:
        None
    Returns:
        -success message with review to reject insights(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    @swagger_auto_schema(
        operation_summary="Get review to reject insights API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the department",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "office", in_=openapi.IN_QUERY, description="comma separated name of location/coutry", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "positions",
                in_=openapi.IN_QUERY,
                description="comma separated positions",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "user_id",
                in_=openapi.IN_QUERY,
                description="user_id",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "end_date",
                in_=openapi.IN_QUERY,
                description="end_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "start_date",
                in_=openapi.IN_QUERY,
                description="start_date",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
    )
    def get(self, request):
        try:
            response = {}
            url_domain = None
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            if "lable" in data and "values" in data:
                departments = data.get("lable").split(",")
                values = data.get("values").split(",")
                complete_department_list = []
                for department, value in zip(departments, values):
                    temp = [{"label": department, "value": int(value)}]
                    complete_department_list.append(temp)
            else:
                complete_department_list = None
            if "office" in data:
                office = data.get("office").split(",")
            else:
                office = []
            if "positions" in data:
                positions = data.get("positions").split(",")
            else:
                positions = []
            if "user_id" in data:
                user_ids = data.get("user_id")
            else:
                user_ids = []
            if "end_date" in data:
                end_date = datetime.datetime.strptime(data.get("end_date"), "%Y-%m-%d").date()
            else:
                end_date = datetime.datetime.today().date()
            if "start_date" in data:
                start_date = datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
            else:
                start_date = datetime.datetime.today().date() - timedelta(30)
            # Get Applied position of user and its team members
            applied_position_list = get_all_applied_position(request.user.profile)
            # Calculate candidates reviews to interview ratio
            applied_positions = AppliedPosition.objects.filter(
                company__url_domain=url_domain, created_at__date__gte=start_date, created_at__date__lte=end_date
            ).filter(id__in=applied_position_list)
            if user_ids:
                emails = list(Profile.objects.filter(id__in=user_ids).values_list("user__email", flat=True))
                form_data_id = list(FormData.objects.filter(Q(hiring_manager__in=emails) | Q(recruiter__in=emails)).values_list("id", flat=True))
            else:
                form_data_id = []
            if complete_department_list:
                applied_positions = applied_positions.filter(form_data__form_data__department__in=complete_department_list)
            if office:
                applied_positions = applied_positions.filter(form_data__form_data__location__0__label__in=office)
            if positions:
                applied_positions = applied_positions.filter(form_data__id__in=positions)
            if form_data_id:
                applied_positions = applied_positions.filter(form_data__id__in=form_data_id)
            reject_after_review_count = 0
            for application in applied_positions:
                if "history" in application.data:
                    try:
                        history = application.data["history_detail"][-1]
                        if "resume" in history["name"].lower() or "review" in history["name"]:
                            if application.application_status == "reject":
                                reject_after_review_count += 1
                    except Exception as e:
                        print(e)
            candidate_review_to_reject_data = {}
            candidate_review_to_reject_data["count"] = reject_after_review_count
            response["candidate_review_to_reject"] = candidate_review_to_reject_data

            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "Data Fetched",
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


class GetAdvertisementFormData(APIView):
    """
    This GET function fetches all records from FormData model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - page(optional)
        - status(optional)
        - is_cloned(optional)
        - created_by_profile(optional)
        - search(optional)
        - country(optional)
        - job_category(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized FormData model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FormData Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    # queryset = FormModel.FormData.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )
    # TODO: implement selection drop down
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="filter form_data by status",
        type=openapi.TYPE_STRING,
    )
    is_cloned = openapi.Parameter(
        "is_cloned",
        in_=openapi.IN_QUERY,
        description="filter form_data by is_cloned",
        type=openapi.TYPE_BOOLEAN,
    )
    employee_visibility = openapi.Parameter(
        "employee_visibility",
        in_=openapi.IN_QUERY,
        description="filter form_data by employee_visibility",
        type=openapi.TYPE_BOOLEAN,
    )
    candidate_visibility = openapi.Parameter(
        "candidate_visibility",
        in_=openapi.IN_QUERY,
        description="filter form_data by candidate_visibility",
        type=openapi.TYPE_BOOLEAN,
    )
    profile_id = openapi.Parameter(
        "profile_id",
        in_=openapi.IN_QUERY,
        description="filter form_data by created_by_profile",
        type=openapi.TYPE_STRING,
    )
    country = openapi.Parameter(
        "country",
        in_=openapi.IN_QUERY,
        description="filter form_data by country id",
        type=openapi.TYPE_STRING,
    )
    job_category = openapi.Parameter(
        "job_category",
        in_=openapi.IN_QUERY,
        description="filter form_data by job_category id",
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
    own_data = openapi.Parameter(
        "own_data",
        in_=openapi.IN_QUERY,
        description="filter on the basis of own_data",
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
            search,
            status,
            is_cloned,
            profile_id,
            employee_visibility,
            candidate_visibility,
            country,
            job_category,
            page,
            perpage,
            sort_dir,
            sort_field,
            own_data,
            export,
        ]
    )
    def get(self, request):
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        if data.get("status"):
            status = data.get("status")
        else:
            status = ""

        if data.get("is_cloned"):
            is_cloned = data.get("is_cloned")
        else:
            is_cloned = ""

        if data.get("profile_id"):
            profile_id = data.get("profile_id")
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
        else:
            profile_id = ""

        if data.get("employee_visibility"):
            employee_visibility = data.get("employee_visibility")
        else:
            employee_visibility = ""

        if data.get("candidate_visibility"):
            candidate_visibility = data.get("candidate_visibility")
        else:
            candidate_visibility = ""

        if data.get("search"):
            search = data.get("search")
        else:
            search = ""

        if data.get("country"):
            country = data.get("country")
        else:
            country = ""

        if data.get("job_category"):
            job_category = data.get("job_category")
        else:
            job_category = ""

        if data.get("own_data"):
            own_data = data.get("own_data")
        else:
            own_data = None

        if data.get("export"):
            export = True
        else:
            export = False

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        form_data = FormModel.FormData.objects.filter(company__url_domain=url_domain).order_by("-id")
        if status:
            form_data = form_data.filter(status=status)

        if is_cloned == "true":
            form_data = form_data.filter(Q(is_cloned=True))

        if is_cloned == "false":
            form_data = form_data.filter(Q(is_cloned=False))

        if employee_visibility == "false":
            form_data = form_data.filter(Q(employee_visibility=False))

        if employee_visibility == "true":
            form_data = form_data.filter(Q(employee_visibility=True))

        if candidate_visibility == "false":
            form_data = form_data.filter(Q(candidate_visibility=False))

        if candidate_visibility == "true":
            form_data = form_data.filter(Q(candidate_visibility=True))
        if country:
            form_data = form_data.filter(Q(form_data__country__id=int(country)))
        if job_category:
            form_data = form_data.filter(Q(form_data__job_category__id=int(job_category)))
        if profile_id:
            pro_obj = Profile.objects.get(id=profile_id)
            temp_form_data = form_data
            own_form_data = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
            teams_obj, created = Team.objects.get_or_create(manager=pro_obj)
            members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
            members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
            result_list = members_fd_obj | own_form_data
            if status:
                result_list = result_list.filter(status=status)
            form_data = sort_data(result_list, sort_field, sort_dir)
            if status:
                result_list = result_list.filter(status=status)
            form_data = sort_data(result_list, sort_field, sort_dir)
        if search:
            try:
                form_data = form_data.filter(show_id=int(search))
            except:
                form_data = search_data(
                    form_data, FormData, search, ["form_data__job_title__icontains", "form_data__job_description__icontains", "form_data__show_id"]
                )
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
            if selected_fields:
                selected_fields = selected_fields.first().selected_fields
            else:
                selected_fields = ["Hiring Manager", "Position No", "Job Title", "Country", "Candidates Applied", "Status"]
            writer.writerow(selected_fields)

            for data in form_data:
                serializer_data = FormDataSerializer(data).data
                row = []
                for field in selected_fields:
                    if field.lower() in ["department", "category", "location", "country", "level", "employment type"]:
                        field = form_utils.position_dict.get(field)
                        try:
                            value = data.form_data.get(field)[0].get("label")
                            if value is None:
                                value = data.form_data.get(field).get("name")
                        except Exception as e:
                            value = None
                    elif field in ["Position Name", "Job Title"]:
                        value = data.form_data.get("job_title")
                    elif field == "Video JD":
                        value = data.job_description
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
            pagination_data = paginate_data(request, form_data, FormModel.FormData)
            form_data = pagination_data.get("paginate_data")
            if form_data:
                serializer = FormSerializer.FormDataListSerializer(form_data, many=True, context={"request": request}).data
                return ResponseOk(
                    {
                        "data": serializer,
                        "meta": {
                            "page": pagination_data.get("page"),
                            "total_pages": pagination_data.get("total_pages"),
                            "perpage": pagination_data.get("perpage"),
                            "sort_dir": sort_field,
                            "sort_field": sort_field,
                            "total_records": pagination_data.get("total_records"),
                        },
                    }
                )

        return ResponseBadRequest(
            {
                "data": None,
                "message": "FormData Does Not Exist",
            }
        )


class UserSelectedFieldsAPI(APIView):

    """
    API to GET, POST, or UPDATE the selected field of a user
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(operation_description="Create and Update API to add Selected Fields", request_body=UserSelectedFieldSerializer)
    def post(self, request):
        try:
            data = request.data
            profile = data.get("profile")
            try:
                profile = int(decrypt(profile))
            except:
                pass
            data["profile"] = profile
            try:
                obj = UserSelectedField.objects.get(profile__id=profile, select_type=data.get("select_type"))
                serializer = UserSelectedFieldSerializer(obj, data=request.data)
            except:
                serializer = UserSelectedFieldSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
            else:
                return ResponseBadRequest(
                    {
                        "data": None,
                        "error": serializer.errors,
                        "message": "data  not saced",
                    }
                )
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Data saved",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "error": str(e),
                    "message": "some error occured",
                }
            )

    @swagger_auto_schema(
        operation_description="Get API to fetch Selected Fields",
        manual_parameters=[],
    )
    def get(self, request):
        try:
            data = request.GET
            try:
                obj = UserSelectedField.objects.get(profile__id=request.user.profile.id, select_type=data.get("select_type"))
            except:
                if data.get("select_type") == "position":
                    selected_fields = ["Hiring Manager", "Recruiter", "Location", "Position No", "Candidates Applied", "Status", "Action"]
                    obj = UserSelectedField.objects.create(
                        profile=request.user.profile, select_type=data.get("select_type"), selected_fields=selected_fields
                    )
                else:
                    raise ValueError
            serializer = UserSelectedFieldSerializer(obj)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Data fetched",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "error": str(e),
                    "message": "selected fields not found",
                }
            )


class GetRemindersList(APIView):

    """
    API to GET offer approval, position approval and interview reminder
    of the logged in user.
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Get Reminders of User API",
        operation_summary="Get Reminders of User API",
        manual_parameters=[],
    )
    def get(self, request):
        try:
            data = request.GET
            response = []
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")
            # Ger offer approvals
            queryset_data = FormModel.OfferApproval.objects.filter(
                Q(company__url_domain=url_domain) | Q(company=None), profile=request.user.profile, is_approve=False, show=True, is_reject=False
            ).order_by("-updated_at")
            queryset = []
            for query in queryset_data:
                if (
                    OfferLetter.objects.filter(offered_to__form_data=query.position)
                    .exclude(Q(is_decline=True) | Q(withdraw=True))
                    .exclude(offered_to__application_status="offer-rejected")
                ):
                    queryset.append(query)
            if queryset:
                temp_dict = {}
                temp_dict["type"] = "offer-approval"
                diff = datetime.datetime.today().date() - queryset[0].updated_at.date()
                # temp_dict["msg"] = "You have {} Offer Approval pending from last {} day(s)".format(len(queryset), diff.days)
                temp_dict["msg"] = "You have {} Offer Approval pending".format(len(queryset))
                response.append(temp_dict)

            # # Get Position Approvals
            queryset_data = FormModel.PositionApproval.objects.filter(
                Q(company__url_domain=url_domain) | Q(company=None), profile__id=request.user.profile.id, is_approve=False, show=True, is_reject=False
            ).order_by("-updated_at")
            if queryset_data:
                temp_dict = {}
                temp_dict["type"] = "position-approval"
                diff = datetime.datetime.today().date() - queryset_data[0].updated_at.date()
                # temp_dict["msg"] = "You have {} Pending Approval pending from last {} day(s)".format(queryset_data.count(), diff.days)
                temp_dict["msg"] = "You have {} Pending Approval pending".format(queryset_data.count())
                response.append(temp_dict)

            # get interviews
            queryset = AppliedPosition.objects.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            queryset = queryset.filter(data__has_key="interview_schedule_data_list", form_data__status="active")
            start_date = datetime.datetime.today().date()
            end_date = datetime.datetime.today().date() + datetime.timedelta(days=7)
            result = {}
            count = 0
            today_interview = None
            for n in range(int((end_date - start_date).days) + 1):
                res_1 = []
                dt = str(start_date + timedelta(n))
                res = []
                for q in queryset:
                    for inter in q.data.get("interview_schedule_data_list", []):
                        if inter["date"] == dt:
                            if q not in res:
                                res.append(q)
                serialized_res = AppliedPositionListSerializer(res, many=True).data
                profile = request.user.profile.id
                if profile is not None:
                    for i in serialized_res:
                        stages = (
                            PositionStage.objects.filter(position__id=i["form_data"]["id"]).filter(stage__is_interview=True).order_by("sort_order")
                        )
                        for idx, inter in enumerate(i["data"]["interview_schedule_data_list"]):
                            inter_obj = inter["Interviewer"]
                            # get attributes
                            attributes = 0
                            try:
                                for competency in stages[idx].competency.all():
                                    for att in competency.attribute.all():
                                        attributes += 1
                            except Exception as e:
                                print(e)
                            # Get rating given
                            total_ratings_given = PositionScoreCard.objects.filter(
                                position=i["form_data"]["id"],
                                applied_profiles__id=i["applied_profile"]["id"],
                                interviewer_profile__id=request.user.profile.id,
                            ).count()
                            if attributes > total_ratings_given:
                                interviewer_list = []
                                try:
                                    new_interviewers = []
                                    for j in inter_obj:
                                        if int(profile) == j["value"]:
                                            new_interviewers.append(j)
                                    # i["data"]["interview_schedule_data"]["Interviewer"] = new_interviewers
                                    inter["Interviewer"] = new_interviewers
                                    if new_interviewers:
                                        res_1.append(i)
                                except Exception as e:
                                    print(e)
                    result[dt] = res_1
                    count = count + len(res_1)
                    if today_interview is None:
                        today_interview = len(res_1)
            if count:
                temp_dict = {}
                temp_dict["type"] = "interview"
                temp_dict["msg"] = "You have {} Interview today.".format(today_interview)
                response.append(temp_dict)

            queryset = (
                AppliedPosition.objects.filter(form_data__status="active")
                .filter(Q(company__url_domain=url_domain) | Q(company=None))
                .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                .order_by("created_at")
            )
            queryset_ids = []
            for ap in queryset.exclude(application_status="reject"):
                last_stage = ap.data["history_detail"][-1]
                if last_stage["name"] in ["Resume Review"]:
                    queryset_ids.append(ap.id)
            queryset = AppliedPosition.objects.filter(id__in=queryset_ids)
            if queryset:
                temp_dict = {}
                temp_dict["type"] = "resume-review"
                diff = datetime.datetime.today().date() - queryset[0].updated_at.date()
                # temp_dict["msg"] = "You have {} Resumes to Review from last {} day(s)".format(queryset.count(), diff.days)
                temp_dict["msg"] = "You have {} Resumes to Review".format(queryset.count())
                response.append(temp_dict)

            # Add Hiring Manager Review
            queryset = (
                AppliedPosition.objects.filter(form_data__status="active")
                .filter(Q(company__url_domain=url_domain) | Q(company=None))
                .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                .order_by("created_at")
            )
            queryset_ids = []
            for ap in queryset.exclude(application_status="reject"):
                last_stage = ap.data["history_detail"][-1]
                if last_stage["name"] in ["Hiring Manager Review"]:
                    queryset_ids.append(ap.id)
            queryset = AppliedPosition.objects.filter(id__in=queryset_ids)
            if queryset:
                temp_dict = {}
                temp_dict["type"] = "hiring-manager-review"
                diff = datetime.datetime.today().date() - queryset[0].updated_at.date()
                # temp_dict["msg"] = "You have {} Hiring Manager Review from last {} day(s)".format(queryset.count(), diff.days)
                temp_dict["msg"] = "You have {} Hiring Manager Review".format(queryset.count())
                response.append(temp_dict)

            # Get pending decision
            pk = request.user.profile.id
            pending_interviewer_list = []
            applied_position_list = []
            try:
                interviewer_obj = Profile.objects.get(id=pk).user
            except User.DoesNotExist:
                return ResponseBadRequest(
                    {
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Please specify the correct user ID",
                    }
                )

            application_obj = AppliedPosition.objects.filter(
                company=interviewer_obj.user_company.id, application_status__in=["pending", "kiv"], form_data__status="active"
            )
            for application in application_obj:
                if interviewer_obj.user_role.name in ["hiring manager", "recruiter"]:
                    if application.form_data.hiring_manager == interviewer_obj.email or application.form_data.recruiter == interviewer_obj.email:
                        # Return all applied position with status pending as the hiring manager has logged in
                        # check if hiringmanaer, recruiter logged in then return all the pending decision
                        applied_position_list = AppliedPosition.objects.filter(
                            company=interviewer_obj.user_company.id, application_status__in=["pending", "kiv"], form_data__status="active"
                        )
                        applied_position_list = applied_position_list.filter(
                            Q(form_data__recruiter=interviewer_obj.email) | Q(form_data__hiring_manager=interviewer_obj.email)
                        )
                        break
            applied_position_list = list(set(applied_position_list))
            if applied_position_list:
                temp_dict = {}
                temp_dict["type"] = "pending-decision"
                temp_dict["msg"] = "You have {} Pending Decision".format(len(applied_position_list))
                response.append(temp_dict)

            # # Get pending offer
            pending_interviewer_list = []
            applied_position_list = []
            try:
                interviewer_obj = Profile.objects.get(id=pk).user
            except User.DoesNotExist:
                return ResponseBadRequest(
                    {
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Please specify the correct user ID",
                    }
                )

            application_obj = AppliedPosition.objects.filter(
                company=interviewer_obj.user_company.id, application_status__in=["pending-offer", "offer", "approved", "offer-rejected"]
            )
            data = request.GET
            search = data.get("search")
            if search:
                application_obj = search_data(application_obj, AppliedPosition, search)
            for application in application_obj:
                if interviewer_obj.user_role.name in ["hiring manager", "recruiter"]:
                    if application.form_data.hiring_manager == interviewer_obj.email or application.form_data.recruiter == interviewer_obj.email:
                        # Return all applied position with status pending as the hiring manager has logged in
                        applied_position_list = AppliedPosition.objects.filter(
                            company=interviewer_obj.user_company.id, application_status__in=["pending-offer", "offer", "approved", "offer-rejected"]
                        ).exclude(form_data__status__in=["canceled", "closed", "draft"])
                        applied_position_list = applied_position_list.filter(
                            Q(form_data__recruiter=interviewer_obj.email) | Q(form_data__hiring_manager=interviewer_obj.email)
                        )
                        break
            applied_position_list = list(set(applied_position_list))
            if applied_position_list:
                temp_dict = {}
                temp_dict["type"] = "pending-offer"
                temp_dict["msg"] = "You have {} Pending Offer".format(len(applied_position_list))
                response.append(temp_dict)

            # adding position feedback
            applied_position_list = []
            application_obj = AppliedPosition.objects.filter(
                company=interviewer_obj.user_company.id, form_data__status="active", application_status="active"
            )
            for application in application_obj:
                for stage_interview in application.data.get("interview_schedule_data_list", []):
                    # get timezone
                    try:
                        interviewer_ids = stage_interview["Interviewer"]
                    except:
                        interviewer_ids = []

                    for interviewer in interviewer_ids:
                        try:
                            int_id = interviewer["profile_id"]
                        except:
                            int_id = 0
                        if int(pk) == int(int_id):
                            score_obj = PositionScoreCard.objects.filter(
                                position=application.form_data,
                                applied_profiles=application.applied_profile,
                                interviewer_profile__id=interviewer["profile_id"],
                            )
                            if len(score_obj) == 0 and application.data.get("interview_cancelled", False) == False:
                                pending_interviewer_list.append(interviewer["profile_id"])
                                if "start_time" in stage_interview:
                                    inter_timezone = stage_interview.get("timezone", "Asia/Singapore")
                                    tz = pytz_tz(inter_timezone)
                                    stringed_start_time = "{} {}".format(stage_interview["date"], stage_interview["start_time"])
                                    obj_start_time = datetime.datetime.strptime(stringed_start_time, "%Y-%m-%d %I:%M %p")
                                interview_time = tz.localize(
                                    datetime.datetime(
                                        obj_start_time.year, obj_start_time.month, obj_start_time.day, obj_start_time.hour, obj_start_time.minute
                                    )
                                )
                                current_time = datetime.datetime.now(tz)
                                if current_time > interview_time + datetime.timedelta(minutes=1):
                                    applied_position_list.append(application)
                            # else:
                            #     applied_position_list.append(application)
            applied_position_list = list(set(applied_position_list))
            if applied_position_list:
                temp_dict = {}
                temp_dict["type"] = "pending-feedback"
                temp_dict["msg"] = "You have {} Pending Feedback".format(len(applied_position_list))
                response.append(temp_dict)
            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "Data fetched",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "error": str(e),
                    "message": "selected fields not found",
                }
            )


class AdminGetNewHires(APIView):
    """
    API used to get list of new hire on Admin Panel.
    Args:
        export - True or False value
    Body:
        None
    Returns:
        -success message and list of new hires(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export",
        type=openapi.TYPE_STRING,
    )
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        operation_description="Get list of Hires for Admin Panel",
        manual_parameters=[
            export,
        ],
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET
            if data.get("export"):
                export = True
            else:
                export = False
            search = data.get("search", "")
            user = request.user
            # new_hires = OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True).filter(
            #     start_date__lt=datetime.datetime.today().date(), email_changed=False
            # )

            new_hires = OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True).filter(has_joined=True, email_changed=False)
            if search:
                new_hires = new_hires.annotate(
                    full_name=Concat("offered_to__applied_profile__user__first_name", V(" "), "offered_to__applied_profile__user__last_name"),
                    string_id=Cast("offered_to__form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=search)
                    | Q(offered_to__form_data__form_data__job_title__icontains=search)
                    | Q(string_id__icontains=search)
                    | Q(offered_to__applied_profile__user__email__icontains=search)
                )
            data = []
            for hire in new_hires:
                if hire.offered_to.applied_profile.user.user_role.name == "candidate":
                    temp_dict = {}
                    temp_dict["first_name"] = hire.offered_to.applied_profile.user.first_name
                    temp_dict["last_name"] = hire.offered_to.applied_profile.user.last_name
                    temp_dict["email"] = hire.offered_to.applied_profile.user.email
                    temp_dict["address"] = GetAddressSerializer(hire.offered_to.applied_profile.address).data
                    temp_dict["join_date"] = str(hire.start_date)
                    data.append(temp_dict)
            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                if selected_fields:
                    selected_fields = selected_fields.first().selected_fields
                else:
                    selected_fields = ["Hiring Manager", "Position No", "Job Title", "Country", "Candidates Applied", "Status"]
                writer.writerow(selected_fields)
                for data in new_hires:
                    serializer_data = OfferLetterSerializer(data).data
                    row = []
                    for field in selected_fields:
                        if field.lower() in ["department", "category", "location", "country", "level", "employment type"]:
                            field = form_utils.position_dict.get(field)
                            try:
                                value = data.offered_to.form_data.form_data.get(field)[0].get("label")
                                if value is None:
                                    value = data.offered_to.form_data.form_data.get(field).get("name")
                            except Exception as e:
                                value = None
                        elif field in ["Position Name", "Job Title"]:
                            value = data.offered_to.form_data.form_data.get("job_title")
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
                        "data": data,
                        "code": status.HTTP_200_OK,
                        "message": "new hires fetched successfully",
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


class GetAllFormDataClone(APIView):
    """
    This GET function fetches all records from FormData model according
    to the listed filters in body section and return the data
    after serializing it for clone position listing.

    Args:
        None
    Body:
        - domain(mandatory)

    Returns:
        - Serialized FormData model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FormData Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    # queryset = FormModel.FormData.objects.all()

    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data:
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        form_data = FormModel.FormData.objects.filter(company__url_domain=url_domain).order_by("-id")
        pro_obj = Profile.objects.get(id=request.user.profile.id)
        temp_form_data = form_data
        own_form_data = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
        teams_obj, created = Team.objects.get_or_create(manager=pro_obj)
        members_fd_list = get_hiring_managers_form_data(teams_obj, temp_form_data, [])
        members_fd_obj = FormData.objects.filter(id__in=members_fd_list).order_by("-id")
        result_list = members_fd_obj | own_form_data

        pagination_data = paginate_data(request, result_list, FormModel.FormData)
        form_data = pagination_data.get("paginate_data")
        if form_data:
            serializer = FormSerializer.FormDataListSerializer(form_data, many=True, context={"request": request}).data
            resp = {
                "data": serializer,
                "meta": {
                    "page": pagination_data.get("page"),
                    "total_pages": pagination_data.get("total_pages"),
                    "perpage": pagination_data.get("perpage"),
                    "total_records": pagination_data.get("total_records"),
                },
            }
            cache.set(request.get_full_path(), resp)
            return ResponseOk(resp)
        else:
            return ResponseBadRequest(
                {
                    "data": [],
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "No positions found!",
                }
            )


class UAAPView(APIView):
    """
    This POST function creates a Applied Position Model record from the data passed in the body.

    Args:
        None
    Body:
        Applied Position model Fields
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    @swagger_auto_schema(
        operation_description="UAAPView create API",
        operation_summary="UAAPView create API",
        request_body=FormSerializer.UnapprovedAppliedPositionSer,
    )
    def post(self, request):
        company_obj = Company.objects.get(id=request.data.get("company"))
        username = "{}_{}".format(request.data.get("email"), company_obj.url_domain)
        if User.objects.filter(username=username):
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Email already exists!",
                }
            )
        serializer = FormSerializer.UnapprovedAppliedPositionSer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            data = serializer.data
            # send email to candidate
            context = {}
            context["first_name"] = obj.applicant_details["first_name"]
            context["position_name"] = obj.form_data.form_data["job_title"]
            context["link"] = "https://{}.{}/candidate/applied_position/detail?form={}&email={}".format(
                obj.company.url_domain, settings.DOMAIN_NAME, obj.form_data.id, obj.email
            )
            context["company_name"] = obj.company.company_name
            to_email = obj.email
            body_msg = render_to_string("add_candidate.html", context)
            msg = EmailMultiAlternatives(
                "Congratulations you have been added to a position!", body_msg, "Congratulations you have been added to a position!", [to_email]
            )
            msg.content_subtype = "html"
            msg.send()
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Applied Position created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position is not valid",
                }
            )

    def get(self, request):
        try:
            data = request.GET
            queryset = UnapprovedAppliedPosition.objects.get(email=data.get("email"), form_data__id=data.get("form_data"))
            serializer = FormSerializer.UnapprovedAppliedPositionSer(queryset)
            data = serializer.data
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Applied Position get successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "message": " Applied Position Not Exist",
                    "code": status.HTTP_400_BAD_REQUEST,
                }
            )

    def delete(self, request):
        try:
            data = request.GET
            a = UnapprovedAppliedPosition.objects.get(email=data.get("email"), form_data__id=data.get("form_data"))
            hm_user = User.objects.get(email=a.form_data.hiring_manager, user_company=a.form_data.company)
            recruiter_user = User.objects.get(email=a.form_data.recruiter, user_company=a.form_data.company)
            candidate_name = "{} {}".format(a.applicant_details.get("first_name", ""), a.applicant_details.get("last_name", ""))
            send_reminder(
                "{} has rejected the consent for the position {}".format(candidate_name, a.form_data.form_data.get("job_title")),
                hm_user,
                slug=None,
                applied_position=None,
                form_data=a.form_data,
            )
            send_reminder(
                "{} has rejected the consent for the position {}".format(candidate_name, a.form_data.form_data.get("job_title")),
                recruiter_user,
                slug=None,
                applied_position=None,
                form_data=a.form_data,
            )
            a.delete()
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Applied Position deleted successfully.",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "message": " Applied Position Not Exist",
                    "code": status.HTTP_400_BAD_REQUEST,
                }
            )


class GetCandidateActiveApplication(APIView):
    """
    This functions returns the serialized data of all the applications that a candidate has applied.
    Args:
        pk - profile id of the candidate
    Body:
        None
    Returns:
        - serilized AppliedPosition data (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
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

    @swagger_auto_schema(manual_parameters=[page, perpage])
    def get(self, request, pk):
        try:
            try:
                pk = int(decrypt(pk))
            except:
                pass
            data = []
            ap_objs = AppliedPosition.objects.filter(
                applied_profile__id=pk,
                application_status__in=["active", "offer", "pending-offer", "approved", "hire", "hired"],
                form_data__status="active",
            )
            try:
                if "not_position_id" in request.GET:
                    ap_objs = ap_objs.exclude(form_data__id=int(request.GET.get("not_position_id")))
            except Exception as e:
                print(e)
            pagination_data = paginate_data(request, ap_objs, FormModel.AppliedPosition)
            ap_objs = pagination_data.get("paginate_data")

            for ap in ap_objs:
                temp_dict = {}
                temp_dict["job_title"] = ap.form_data.form_data["job_title"]
                temp_dict["position_id"] = ap.form_data.id
                temp_dict["sposition_id"] = ap.form_data.show_id
                # if ap.application_status in ["reject", "rejected", "calcel", "offer-decline", "offer-rejected"]:
                #     temp_dict["stage_name"] = "Rejected"
                # else:
                #     temp_dict["stage_name"] = "Resume Review"
                try:
                    temp_dict["stage_name"] = ap.data.get("history_detail")[-1]["name"]
                except:
                    temp_dict["stage_name"] = "Resume Review"
                data.append(temp_dict)
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Details fetched successfuly",
                    "meta": {
                        "page": pagination_data.get("page"),
                        "total_pages": pagination_data.get("total_pages"),
                        "perpage": pagination_data.get("perpage"),
                        "total_records": pagination_data.get("total_records"),
                    },
                }
            )
        except Exception as e:
            return ResponseBadRequest({"data": None, "message": " Applied Position Not Exist", "code": status.HTTP_400_BAD_REQUEST, "error": str(e)})


class GetNextInternalCandidate(APIView):
    """
    This GET function fetches the next, current and previous records from Applied Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:class CreateFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = '__all__'
        - None (HTTP_400_BAD_REQUEST) Applied Position Model Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.AppliedPosition.objects.all()  # .filter(applied_profile__user__user_role__name__in=["candidate", "guest"])
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by candidate name and job title",
        type=openapi.TYPE_STRING,
    )
    applied_profile = openapi.Parameter(
        "applied_profile",
        in_=openapi.IN_QUERY,
        description="applied_profile id",
        type=openapi.TYPE_STRING,
    )
    application_status = openapi.Parameter(
        "application_status",
        in_=openapi.IN_QUERY,
        description="application_status",
        type=openapi.TYPE_STRING,
    )
    position_status = openapi.Parameter(
        "position_status",
        in_=openapi.IN_QUERY,
        description="position_status",
        type=openapi.TYPE_STRING,
    )
    position_stage_id = openapi.Parameter(
        "position_stage_id",
        in_=openapi.IN_QUERY,
        description="position_stage_id",
        type=openapi.TYPE_INTEGER,
    )
    form_data = openapi.Parameter(
        "form_data",
        in_=openapi.IN_QUERY,
        description="form_data id (Position id)",
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
    internal_employees = openapi.Parameter(
        "internal_employees",
        in_=openapi.IN_QUERY,
        description="internal_employees",
        type=openapi.TYPE_STRING,
    )
    applied_position = openapi.Parameter(
        "applied_position",
        in_=openapi.IN_QUERY,
        description="applied_position data or not",
        type=openapi.TYPE_STRING,
    )
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="status",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            applied_profile,
            application_status,
            position_status,
            position_stage_id,
            form_data,
            page,
            perpage,
            sort_dir,
            sort_field,
            internal_employees,
            applied_position,
            status,
        ]
    )
    def get(self, request):
        data = cache.get(request.get_full_path())
        if data:
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        # Search
        if data.get("search") is not None:
            search = data.get("search")
        else:
            search = ""

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        if data.get("form_data"):
            form_data = data.get("form_data")
        else:
            form_data = ""
        if data.get("status"):
            status = data.get("status")
        else:
            status = ""

        if data.get("applied_profile"):
            applied_profile = data.get("applied_profile")
            try:
                applied_profile = int(decrypt(applied_profile))
            except:
                pass
        else:
            applied_profile = ""

        if data.get("applied_position"):
            applied_position = data.get("applied_position")
        else:
            applied_position = 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        position_status = data.get("position_status")

        internal_employees = data.get("internal_employees")

        application_status = data.get("application_status")

        position_stage_id = data.get("position_stage_id")
        try:
            if request.user.user_role.name == "hiring manager":
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(Q(company__url_domain=url_domain) | Q(company=None))
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    applied_position_list = get_all_applied_position(request.user.profile)
                    queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None)).filter(id__in=applied_position_list)
            else:
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(Q(company__url_domain=url_domain) | Q(company=None))
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            if position_status is not None:
                queryset = queryset.filter(Q(form_data__status=position_status))

            if form_data:
                queryset = queryset.filter(Q(form_data=form_data))

            if applied_profile:
                queryset = queryset.filter(Q(applied_profile=applied_profile))
            if status:
                queryset = queryset.filter(
                    form_data__status="active", application_status__in=["active", "offer", "pending", "hire", "kiv", "pending-offer"]
                )
            if internal_employees:
                queryset = (
                    queryset.exclude(Q(applied_profile__user__user_role__name__in=["candidate", "guest"]))
                    .filter(application_status__in=["active", "approved", "pending", "pending-offer", "offer-rejected"])
                    .filter(form_data__status="active")
                )
                #  .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))

            if application_status:
                queryset = queryset.filter(Q(application_status=application_status))

            if position_stage_id:
                queryset = queryset.filter(Q(data__position_stage_id=int(position_stage_id)))

            queryset = sort_data(queryset, sort_field, sort_dir)
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(Q(full_name__icontains=search) | Q(form_data__form_data__job_title__icontains=search) | Q(string_id__icontains=search))
            queryset = queryset.prefetch_related("form_data", "applied_profile")
            if queryset:
                next_obj = None
                prev_obj = None
                for idx, query in enumerate(queryset):
                    if query.id == int(applied_position):
                        try:
                            next_obj = queryset[idx + 1]
                            next_data = AppliedPositionListSerializer(next_obj).data
                        except:
                            next_data = None
                        try:
                            prev_obj = queryset[idx - 1]
                            prev_data = AppliedPositionListSerializer(prev_obj).data
                        except:
                            prev_data = None
                try:
                    curr_data = AppliedPositionListSerializer(queryset.get(id=int(applied_position))).data
                except Exception as e:
                    print(e)
                    curr_data = None
                resp = {
                    "data": next_data,
                    "previous_data": prev_data,
                    "current_user": curr_data,
                }
                # cache.set(request.get_full_path(), resp)
                return ResponseOk(resp)

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetReviewReNextCandidate(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    is_employee = openapi.Parameter(
        "is_employee",
        in_=openapi.IN_QUERY,
        description="Enter search keyword for candidate review rating",
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
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )
    applied_position = openapi.Parameter(
        "applied_position",
        in_=openapi.IN_QUERY,
        description="applied_position",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[is_employee, page, perpage, sort_dir, sort_field])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET

        if request.headers.get("domain") is not None:
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
        if data.get("applied_position"):
            applied_position = data.get("applied_position")
        else:
            applied_position = 0
        if data.get("search"):
            search = data.get("search")
        else:
            search = ""

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        is_employee = data.get("is_employee")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        try:
            queryset = (
                AppliedPosition.objects.filter(form_data__status="active")
                .filter(Q(company__url_domain=url_domain) | Q(company=None))
                .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
            ).exclude(application_status="reject")

            queryset_ids = []
            for ap in queryset.filter(form_data__status="active").exclude(application_status="reject"):
                last_stage = ap.data["history_detail"][-1]
                if last_stage["name"] in ["Resume Review"]:
                    queryset_ids.append(ap.id)
            queryset = AppliedPosition.objects.filter(id__in=queryset_ids)
            if is_employee is not None and is_employee == "true":
                queryset = queryset.exclude(Q(applied_profile__user__user_role__name__in=["candidate", "guest"]))
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=search)
                    | Q(applied_profile__user__email__icontains=search)
                    | Q(form_data__form_data__job_title__icontains=search)
                    | Q(string_id__icontains=search)
                )
            queryset = queryset.prefetch_related("form_data", "applied_profile")
            # data = FormSerializer.ResumeReviewSerialzer(queryset, many=True).data
            count = queryset.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")
            if count:
                queryset = queryset.prefetch_related("form_data", "applied_profile")
                next_obj = None
                prev_obj = None
                for idx, query in enumerate(queryset):
                    if query.id == int(applied_position):
                        try:
                            next_obj = queryset[idx + 1]
                            next_data = AppliedPositionListSerializer(next_obj).data
                        except:
                            next_data = None
                        try:
                            prev_obj = queryset[idx - 1]
                            prev_data = AppliedPositionListSerializer(prev_obj).data
                        except:
                            prev_data = None
                try:
                    curr_data = AppliedPositionListSerializer(queryset.get(id=int(applied_position))).data
                except:
                    curr_data = None
                return ResponseOk(
                    {
                        "data": next_data,
                        "previous_data": prev_data,
                        "current_user": curr_data,
                    }
                )
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Candidate Review Rating Fetched Successfully.",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Candidate Review Rating Does Not Exist",
                }
            )


class UndoCandidateStage(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def post(self, request, applied_position):
        try:
            ap_obj = AppliedPosition.objects.get(id=applied_position)
            stage_obj = Stage.objects.filter(id=ap_obj.data.get("current_stage_id", None)).first()
            if stage_obj and stage_obj.stage_name == "Offer":
                if AppliedPosition.objects.filter(form_data=ap_obj.form_data, application_status__in=["offer", "pending-offer", "approved"]):
                    return ResponseBadRequest(
                        {
                            "data": "Another candidate is in offer stage.",
                            "code": 400,
                            "message": "Another candidate is in offer stage.",
                        }
                    )
                if AppliedPosition.objects.filter(
                    applied_profile=ap_obj.applied_profile, application_status__in=["offer", "pending-offer", "approved", "hired"]
                ).exclude(id=ap_obj.id):
                    return ResponseBadRequest(
                        {
                            "data": "This candidate is in Offer stage for other position.",
                            "code": 400,
                            "message": "This candidate is in Offer stage for other position.",
                        }
                    )
            ap_obj.application_status = "active"
            if stage_obj and stage_obj.stage_name == "Offer":
                ap_obj.application_status = "pending-offer"
            ap_obj.data.pop("rejection", None)
            ap_obj.data.pop("rejected_at", None)
            ap_obj.data.pop("rejected_by", None)
            ap_obj.data.pop("reason", None)
            ap_obj.save()
            current_stage = ap_obj.data["position_stage_id"]
            stage_id = PositionStage.objects.get(id=current_stage)
            stage_name = stage_id.stage.stage_name
            log_data = {
                "user": request.user.id,
                "description": "Candidate Moved to {} by {}.".format(stage_name, request.user.get_full_name()),
                "type_id": 4,
                "applied_position": ap_obj.id,
            }
            create_activity_log(log_data)

            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Candidate Restored!",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": str(e),
                }
            )


class GetNextNewHire(APIView):
    """
    API used to get list of new hire on HM's dashboard.
    Args:
        export - True or False value
    Body:
        None
    Returns:
        -success message and list of new hires(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    applied_position = openapi.Parameter(
        "applied_position",
        in_=openapi.IN_QUERY,
        description="applied_position",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        operation_description="Get list of Hires for HM's dashboard",
        manual_parameters=[
            applied_position,
        ],
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET
            if data.get("applied_position"):
                applied_position = data.get("applied_position")
            else:
                applied_position = request.data.get("applied_position", 0)
            if data.get("search"):
                search = data.get("search")
            else:
                search = ""
            user = request.user
            if user.user_role.name == "recruiter":
                new_hires = OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True).filter(
                    start_date__gte=datetime.datetime.today().date(), email_changed=False
                )
            else:
                new_hires = (
                    OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True)
                    .filter(Q(offered_to__form_data__recruiter=request.user.email) | Q(offered_to__form_data__hiring_manager=request.user.email))
                    .filter(start_date__gte=datetime.datetime.today().date(), email_changed=False)
                )
            if search:
                new_hires = new_hires.annotate(
                    full_name=Concat("offered_to__applied_profile__user__first_name", V(" "), "offered_to__applied_profile__user__last_name"),
                    string_id=Cast("offered_to__form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=search) | Q(offered_to__form_data__form_data__job_title__icontains=search) | Q(string_id__icontains=search)
                )
            # serializer = OfferLetterSerializer(new_hires, many=True)
            # data = serializer.data
            next_obj = None
            prev_obj = None
            for idx, query in enumerate(new_hires):
                if query.offered_to.id == int(applied_position):
                    try:
                        next_obj = new_hires[idx + 1]
                        next_data = AppliedPositionListSerializer(next_obj.offered_to).data
                    except:
                        next_data = None
                    try:
                        prev_obj = new_hires[idx - 1]
                        prev_data = AppliedPositionListSerializer(prev_obj.offered_to).data
                    except:
                        prev_data = None
            try:
                curr_data = AppliedPositionListSerializer(new_hires.get(offered_to__id=int(applied_position))).data
            except:
                curr_data = None
            return ResponseOk(
                {
                    "data": next_data,
                    "previous_data": prev_data,
                    "current_user": curr_data,
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


class GetInternalApplicants(APIView):
    """
    This GET function fetches all records from Applied Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:class CreateFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = '__all__'
        - None (HTTP_400_BAD_REQUEST) Applied Position Model Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.AppliedPosition.objects.all()  # .filter(applied_profile__user__user_role__name__in=["candidate", "guest"])
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by candidate name and job title",
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
    internal_employees = openapi.Parameter(
        "internal_employees",
        in_=openapi.IN_QUERY,
        description="internal_employees",
        type=openapi.TYPE_STRING,
    )
    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export data or not",
        type=openapi.TYPE_STRING,
    )
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="status",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            page,
            perpage,
            sort_dir,
            sort_field,
            internal_employees,
            export,
            status,
        ]
    )
    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data:
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        # Search
        search = data.get("search", "")

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        form_data = data.get("form_data", "")

        if data.get("export"):
            export = True
        else:
            export = False

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        internal_employees = data.get("internal_employees")

        try:
            if request.user.user_role.name == "hiring manager":
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(Q(company__url_domain=url_domain) | Q(company=None))
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    applied_position_list = get_all_applied_position(request.user.profile)
                    queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None)).filter(id__in=applied_position_list)
            else:
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(Q(company__url_domain=url_domain) | Q(company=None))
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None))

            if form_data:
                queryset = queryset.filter(Q(form_data=form_data))

            if status:
                queryset = queryset.filter(
                    form_data__status="active", application_status__in=["active", "offer", "pending", "hire", "kiv", "pending-offer"]
                )
            if internal_employees:
                queryset = (
                    queryset.exclude(Q(applied_profile__user__user_role__name__in=["candidate", "guest"]))
                    .filter(application_status__in=["active", "approved", "pending", "pending-offer", "offer-rejected"])
                    .filter(form_data__status="active")
                )
                #  .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))

            queryset = sort_data(queryset, sort_field, sort_dir)
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(Q(full_name__icontains=search) | Q(form_data__form_data__job_title__icontains=search) | Q(string_id__icontains=search))
            queryset = queryset.prefetch_related("form_data", "applied_profile")
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
                    context = {"own_id": request.user.profile.id}
                    serializer_data = FormSerializer.InternalApplicantSerializer(data, context=context).data
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
                pagination_data = paginate_data(request, queryset, FormModel.AppliedPosition)
                queryset = pagination_data.get("paginate_data")
                if queryset:
                    context = {"own_id": request.user.profile.id}
                    serializer = FormSerializer.InternalApplicantSerializer(queryset, many=True, context=context).data
                    resp = {
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
                    cache.set(request.get_full_path(), resp)
                    return ResponseOk(resp)

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetOpInternalApplicants(APIView):
    """
    This GET function fetches all records from Applied Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:class CreateFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = '__all__'
        - None (HTTP_400_BAD_REQUEST) Applied Position Model Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = FormModel.AppliedPosition.objects.all()  # .filter(applied_profile__user__user_role__name__in=["candidate", "guest"])

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by candidate name and job title",
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
    internal_employees = openapi.Parameter(
        "internal_employees",
        in_=openapi.IN_QUERY,
        description="internal_employees",
        type=openapi.TYPE_STRING,
    )
    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export data or not",
        type=openapi.TYPE_STRING,
    )
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="status",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            page,
            perpage,
            sort_dir,
            sort_field,
            internal_employees,
            export,
            status,
        ]
    )
    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data:
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        # Search
        search = data.get("search", "")

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        form_data = data.get("form_data", "")

        if data.get("export"):
            export = True
        else:
            export = False

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        internal_employees = data.get("internal_employees")

        try:
            if request.user.user_role.name == "hiring manager":
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(Q(company__url_domain=url_domain) | Q(company=None))
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    applied_position_list = get_all_applied_position(request.user.profile)
                    queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None)).filter(id__in=applied_position_list)
            else:
                if data.get("own_data") == "true":
                    queryset = (
                        self.queryset.all()
                        .filter(Q(company__url_domain=url_domain) | Q(company=None))
                        .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))
                    )
                else:
                    queryset = self.queryset.all().filter(Q(company__url_domain=url_domain) | Q(company=None))

            if form_data:
                queryset = queryset.filter(Q(form_data=form_data))

            if status and isinstance(status, str):
                queryset = queryset.filter(
                    form_data__status="active", application_status__in=["active", "offer", "pending", "hire", "kiv", "pending-offer"]
                )
            if internal_employees:
                queryset = (
                    queryset.exclude(Q(applied_profile__user__user_role__name__in=["candidate", "guest"]))
                    .filter(application_status__in=["active", "approved", "pending", "pending-offer", "offer-rejected"])
                    .filter(form_data__status="active")
                )
                #  .filter(Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email))

            queryset = sort_data(queryset, sort_field, sort_dir)
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(Q(full_name__icontains=search) | Q(form_data__form_data__job_title__icontains=search) | Q(string_id__icontains=search))
            queryset = queryset.prefetch_related("form_data", "applied_profile")
            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                fields = ["Position no", "Position name", "Employee name", "Location", "Hiring stage"]
                writer.writerow(fields)
                for i in queryset:
                    context = {"own_id": request.user.profile.id}
                    row = []
                    row.append(i.form_data.show_id)
                    row.append(i.form_data.form_data.get("job_title"))
                    row.append(i.applied_profile.user.get_full_name())
                    row.append(i.form_data.form_data["location"][0]["label"])
                    try:
                        row.append(Stage.objects.get(id=i.data.get("current_stage_id")).stage_name)
                    except:
                        row.append("Resume Review")
                    writer.writerow(row)
                response = HttpResponse(csv_response, content_type="text/csv")
                return response
            else:
                pagination_data = paginate_data(request, queryset, FormModel.AppliedPosition)
                queryset = pagination_data.get("paginate_data")
                if queryset:
                    data = []
                    for i in queryset:
                        temp_data = {}
                        temp_data["applied_profile"] = i.id
                        temp_data["user_applied_id"] = i.applied_profile.id
                        temp_data["id"] = i.id
                        temp_data["position_id"] = i.form_data.id
                        temp_data["sposition_id"] = i.form_data.show_id
                        temp_data["position_no"] = i.form_data.id
                        temp_data["position_name"] = i.form_data.form_data.get("job_title")
                        temp_data["candidate_name"] = i.applied_profile.user.get_full_name()
                        temp_data["location"] = i.form_data.form_data["location"][0]["label"]
                        try:
                            user_obj = User.objects.get(email__iexact=i.form_data.hiring_manager, user_company=i.company)
                            temp_data["hiring_manager"] = user_obj.get_full_name()
                        except:
                            temp_data["hiring_manager"] = i.form_data.hiring_manager
                        try:
                            user_obj = User.objects.get(email__iexact=i.form_data.recruiter, user_company=i.company)
                            temp_data["recruiter"] = user_obj.get_full_name()
                        except:
                            temp_data["recruiter"] = i.form_data.recruiter
                        try:
                            temp_data["hiring_stage"] = Stage.objects.get(id=i.data.get("current_stage_id")).stage_name
                        except:
                            temp_data["hiring_stage"] = "Resume Review"
                        data.append(temp_data)
                    resp = {
                        "data": data,
                        "meta": {
                            "page": pagination_data.get("page"),
                            "total_pages": pagination_data.get("total_pages"),
                            "perpage": pagination_data.get("perpage"),
                            "sort_dir": sort_dir,
                            "sort_field": sort_field,
                            "total_records": pagination_data.get("total_records"),
                        },
                    }
                    cache.set(request.get_full_path(), resp)
                    return ResponseOk(resp)

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetOpAllInterviews(APIView):
    """
    This GET function fetches all the Scheduled Interviews with optimizations.

    Args:
        None
    Body:
        None
    Returns:
        -HttpResponse
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="profile id",
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
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[profile, page, perpage, sort_dir, sort_field])
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET

        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        profile = data.get("profile")

        try:
            profile = int(decrypt(profile))
        except:
            pass

        page = data.get("page", 1)

        search = data.get("search", "")

        limit = data.get("perpage", settings.PAGE_SIZE)

        if data.get("export"):
            export = True
        else:
            export = False

        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit
        interviews_data = []
        try:
            queryset = AppliedPosition.objects.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            queryset = (
                queryset.filter(data__has_key="interview_schedule_data_list")
                .filter(form_data__status="active")
                .exclude(application_status__in=["reject", "rejected", "offer-decline"])
            )
            if search:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=search)
                    | Q(applied_profile__user__email__icontains=search)
                    | Q(form_data__form_data__job_title__icontains=search)
                    | Q(string_id__icontains=search)
                )
            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("id")

                    else:
                        queryset = queryset.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "created_at":
                        queryset = queryset.order_by("-created_at")
                    elif sort_field == "updated_at":
                        queryset = queryset.order_by("-updated_at")
                    elif sort_field == "id":
                        queryset = queryset.order_by("-id")

                    else:
                        queryset = queryset.order_by("-id")
            else:
                queryset = queryset.order_by("-id")

            if profile:
                queryset = queryset.filter(Q(profile=profile))
            # added code recently
            queryset = queryset.select_related("form_data", "applied_profile")
            resp_data = []
            for i in queryset:
                temp_resp = {}
                interviewer_list = []
                try:
                    stages = PositionStage.objects.filter(position=i.form_data).filter(stage__is_interview=True).order_by("sort_order")
                    for idx, inter in enumerate(i.data.get("interview_schedule_data_list")):
                        inter_obj = inter["Interviewer"]
                        # get attributes
                        attributes = 0
                        try:
                            for competency in stages[idx].competency.all():
                                for att in competency.attribute.all():
                                    attributes += 1
                        except Exception as e:
                            print(e)
                        total_ratings = attributes * len(inter_obj)
                        if inter["date"] != "":
                            try:
                                interviews = []
                                for single_inter in inter["Interviewer"]:
                                    position_scorecard_obj = PositionScoreCard.objects.filter(
                                        position=i.form_data, interviewer_profile=single_inter["value"], applied_profiles=i.applied_profile
                                    )
                                    if position_scorecard_obj.count() < attributes:
                                        single_inter["interview_done"] = False
                                    else:
                                        single_inter["interview_done"] = True
                                    if request.user.email in [i.form_data.hiring_manager, i.form_data.recruiter]:
                                        interviews.append(single_inter)
                                    elif int(request.user.profile.id) in [single_inter["value"]]:
                                        interviews.append(single_inter)
                                    avg_rating = position_scorecard_obj.aggregate(Avg("rating"))["rating__avg"]
                                    if avg_rating:
                                        avg_rating = round(avg_rating, 1)
                                    single_inter["avg_rating"] = avg_rating
                                if interviews:
                                    interviewer_list.append(inter)
                            except Exception as e:
                                print(e)
                except Exception as e:
                    print(e)
                if interviewer_list:
                    temp_resp["position_id"] = i.form_data.id
                    temp_resp["position_name"] = i.form_data.form_data["job_title"]
                    temp_resp["candidate_name"] = i.applied_profile.user.get_full_name()
                    temp_resp["interviewer"] = interviews
                    resp_data.append(temp_resp)
            count = len(resp_data)
            if count:
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

                    for serializer_data in resp_data:
                        row = []
                        for field in selected_fields:
                            if field.lower() in ["department", "category", "location", "level", "employment type"]:
                                field = form_utils.position_dict.get(field)
                                try:
                                    value = serializer_data["form_data"]["form_data"].get(field)[0].get("label")
                                    if value is None:
                                        value = serializer_data["form_data"]["form_data"].get(field).get("name")
                                except Exception as e:
                                    value = None
                            elif field in ["Position Name", "Job Title"]:
                                value = data["form_data"]["form_data"].get("job_title")
                            elif field == "Country":
                                data["form_data"]["form_data"].get("country").get("name")
                            elif field == "Candidate Name":
                                value = serializer_data["applied_profile"]["user"]["first_name"]
                            elif field == "Interviewer":
                                try:
                                    value = serializer_data["data"]["interview_schedule_data"]["Interviewer"][0]["label"]
                                except:
                                    print(serializer_data["data"]["interview_schedule_data"])
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
                    if page and limit:
                        resp_data = resp_data[skip : skip + limit]

                        pages = math.ceil(count / limit) if limit else 1
                    serializer = resp_data
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Interviews Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpFormDataLeft(APIView):
    """
    This GET function fetches all records from FormData model accrding
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)
        - page(optional)
        - status(optional)
        - is_cloned(optional)
        - created_by_profile(optional)
        - search(optional)
        - country(optional)
        - job_category(optional)
        - perpage(optional)
        - sort_field(optional)
        - sort_dir(optional)

    Returns:
        - Serialized FormData model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) FormData Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    # queryset = FormModel.FormData.objects.all()
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )
    # TODO: implement selection drop down
    status = openapi.Parameter(
        "status",
        in_=openapi.IN_QUERY,
        description="filter form_data by status",
        type=openapi.TYPE_STRING,
    )
    profile_id = openapi.Parameter(
        "profile_id",
        in_=openapi.IN_QUERY,
        description="filter form_data by created_by_profile",
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
    own_data = openapi.Parameter(
        "own_data",
        in_=openapi.IN_QUERY,
        description="filter on the basis of own_data",
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
            search,
            status,
            profile_id,
            page,
            perpage,
            sort_dir,
            sort_field,
            own_data,
            export,
        ]
    )
    def get(self, request):
        try:
            data = cache.get(request.get_full_path())
        except:
            data = None
        if data and request.GET.get("candidate_visibility") is not "true":
            return ResponseOk(
                {
                    "data": data.get("data"),
                    "meta": data.get("meta"),
                }
            )
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        status = data.get("status", "")

        profile_id = data.get("profile_id", "")
        try:
            profile_id = int(decrypt(profile_id))
        except:
            pass
        search = data.get("search", "")

        own_data = data.get("own_data", None)

        if data.get("export"):
            export = True
        else:
            export = False
        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        form_data = FormModel.FormData.objects.filter(company__url_domain=url_domain)
        if request.user.user_role.name == "recruiter" and own_data == "false":
            if status:
                if status == "closed":
                    form_data = form_data.filter(status__in=["closed", "canceled"])
                else:
                    form_data = form_data.filter(status=status)
            if search:
                try:
                    form_data = form_data.filter(show_id=int(search))
                except:
                    form_data = search_data(form_data, FormData, search, ["form_data__job_title__icontains", "form_data__show_id"])
        else:
            if status:
                if status == "closed":
                    form_data = form_data.filter(status__in=["closed", "canceled"])
                else:
                    form_data = form_data.filter(status=status)

            if profile_id:
                pro_obj = Profile.objects.get(id=profile_id)
                if own_data == "true":
                    result_list = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                    if status:
                        if status == "closed":
                            form_data = form_data.filter(status__in=["closed", "canceled"])
                        else:
                            form_data = form_data.filter(status=status)
                else:
                    temp_form_data = form_data
                    own_form_data = form_data.filter(Q(hiring_manager=pro_obj.user.email) | Q(recruiter=pro_obj.user.email))
                    teams_obj, created = Team.objects.get_or_create(manager=pro_obj)
                    members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
                    members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
                    result_list = members_fd_obj | own_form_data
                    if status:
                        if status == "closed":
                            form_data = form_data.filter(status__in=["closed", "canceled"])
                        else:
                            form_data = form_data.filter(status=status)
                if status:
                    if status == "closed":
                        form_data = form_data.filter(status__in=["closed", "canceled"])
                    else:
                        form_data = form_data.filter(status=status)
                form_data = sort_data(result_list, sort_field, sort_dir)
            if search:
                try:
                    form_data = form_data.filter(show_id=int(search))
                except:
                    form_data = search_data(
                        form_data,
                        FormData,
                        search,
                        ["form_data__job_title__icontains", "form_data__job_description__icontains", "form_data__show_id"],
                    )
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            fields = [
                "Position No",
                "Position Name",
                "Hiring Manager",
                "Recruiter",
                "Department",
                "Location",
                "Candidates Applied",
                "Aging",
                "Status",
            ]
            writer.writerow(fields)
            for i in form_data:
                row = []
                row.append(i.show_id)
                row.append(i.form_data["job_title"])
                try:
                    user_obj = User.objects.get(email__iexact=i.hiring_manager, user_company=i.company)
                    row.append(user_obj.get_full_name())
                except:
                    row.append(i.hiring_manager)
                try:
                    user_obj = User.objects.get(email__iexact=i.recruiter, user_company=i.company)
                    row.append(user_obj.get_full_name())
                except:
                    row.append(i.recruiter)
                try:
                    row.append(i.form_data["departments"][0]["label"])
                except:
                    row.append(i.form_data.get("department", [{}])[0].get("label"))
                row.append(i.form_data["location"][0]["label"])
                # get candidates applied
                row.append(AppliedPosition.objects.filter(form_data=i).count())
                row.append(i.status)
                writer.writerow(row)
            return csv_response
        else:
            pagination_data = paginate_data(request, form_data, FormModel.FormData)
            form_data = pagination_data.get("paginate_data")
            data = []
            if form_data:
                for i in form_data:
                    temp_data = {}
                    temp_data["id"] = i.id
                    temp_data["position_no"] = i.id
                    temp_data["sposition_id"] = i.show_id
                    temp_data["position_name"] = i.form_data["job_title"]
                    try:
                        user_obj = User.objects.get(email__iexact=i.hiring_manager, user_company=i.company)
                        temp_data["hiring_manager"] = user_obj.get_full_name()
                    except:
                        temp_data["hiring_manager"] = i.hiring_manager
                    try:
                        user_obj = User.objects.get(email__iexact=i.recruiter, user_company=i.company)
                        temp_data["recruiter"] = user_obj.get_full_name()
                    except:
                        temp_data["recruiter"] = i.recruiter
                    temp_data["status"] = i.status
                    temp_data["candidates_applied"] = AppliedPosition.objects.filter(form_data=i).count()
                    temp_data["location"] = i.form_data["location"][0]["label"]
                    try:
                        temp_data["department"] = i.form_data["departments"][0]["label"]
                    except:
                        temp_data["department"] = i.form_data.get("department", [{}])[0].get("label")
                    try:
                        hire_obj = AppliedPosition.objects.filter(form_data=i, application_status="hired")
                        if hire_obj:
                            offer_obj = OfferLetter.objects.filter(offered_to=hire_obj[0])
                            if offer_obj:
                                temp_data["candidate_name"] = offer_obj[0].offered_to.applied_profile.user.get_full_name()
                        else:
                            temp_data["candidate_name"] = None
                    except:
                        temp_data["candidate_name"] = None
                    if status == "draft":
                        temp_data["current_approvals"] = []
                        for pa in PositionApproval.objects.filter(position=i).order_by("sort_order"):
                            t_data = {}
                            t_data["approval_name"] = pa.profile.user.get_full_name()
                            t_data["is_approve"] = pa.is_approve
                            t_data["is_reject"] = pa.is_reject
                            t_data["profile_id"] = encrypt(pa.profile.id)
                            t_data["position"] = pa.position.id
                            t_data["id"] = pa.id
                            temp_data["current_approvals"].append(t_data)
                    temp_data["days_in_status"] = form_utils.get_days_in_status(i)
                    data.append(temp_data)
                resp = {
                    "data": data,
                    "meta": {
                        "page": pagination_data.get("page"),
                        "total_pages": pagination_data.get("total_pages"),
                        "perpage": pagination_data.get("perpage"),
                        "sort_dir": sort_field,
                        "sort_field": sort_field,
                        "total_records": pagination_data.get("total_records"),
                    },
                }
                cache.set(request.get_full_path(), resp)
                return ResponseOk(resp)

        return ResponseBadRequest(
            {
                "data": None,
                "message": "FormData Does Not Exist",
            }
        )


class GetConfirmJoining(APIView):
    def put(self, request, pk):
        try:
            offer_letter = OfferLetter.objects.get(id=pk)
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Offer does not exist",
                }
            )
        if offer_letter.has_joined is True:
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Candidate already moved successfully.",
                }
            )
        offer_letter.has_joined = True
        offer_letter.save()
        return ResponseOk(
            {
                "data": None,
                "code": status.HTTP_200_OK,
                "message": "Candidate moved successfully.",
            }
        )


class AcceptCandidateJoiningonMail(APIView):

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        encoded_id = request.GET.get("encoded_id")
        if encoded_id:
            offer_letter_id = decrypt(encoded_id)
        else:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Please provide encoded ID",
                }
            )

        try:
            offer_letter = OfferLetter.objects.get(id=offer_letter_id)
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Offer does not exist",
                }
            )
        redirect_url = "https://{}.{}/hiring-manager/dashboard#newHiRes".format(offer_letter.offered_to.company.url_domain, settings.DOMAIN_NAME)
        if offer_letter.start_date == datetime.date.today():
            if offer_letter.has_joined is True:
                return redirect(redirect_url)
            else:
                offer_letter.has_joined = True
                offer_letter.save()
                return redirect(redirect_url)
        else:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Link Expired!",
                }
            )


class AcceptOfferApprovalEmail(APIView):
    """
    This PUT function updates an Offer Approval Model record according to the id passed in url.

    Args:
        pk(offer_approval_id)
    Body:
        Offer Approval Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) offer_approval does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = [authentication.JWTAuthentication]
    is_hire = openapi.Parameter(
        "is_hire",
        in_=openapi.IN_QUERY,
        description="enter is_hire",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[is_hire],
        operation_description="Offer update API",
        operation_summary="Offer update API",
        request_body=FormSerializer.OfferApprovalSerializer,
    )
    def get(self, request, offer_approval_id, applied_postion_id):
        data = {}
        offer_approval_id = decrypt(offer_approval_id)
        applied_postion_id = decrypt(applied_postion_id)
        data["is_approve"] = True
        data["is_hire"] = False
        data["offered_to"] = applied_postion_id
        is_hire = data.get("is_hire")
        offered_to = request.data.get("offered_to")
        try:
            data = request.data
            offer = custom_get_object(offer_approval_id, FormModel.OfferApproval)
            user_object = offer.profile.user
            serializer = FormSerializer.OfferApprovalSerializer(offer, data=data)
            if serializer.is_valid():
                offer_approval = serializer.save()
                # Check if all has approved
                total_approvals = OfferApproval.objects.filter(position=offer_approval.position).count()
                total_approved = OfferApproval.objects.filter(position=offer_approval.position, is_approve=True).count()
                if total_approved == total_approvals:
                    approved_applied_position = AppliedPosition.objects.get(id=int(offered_to))
                    approved_applied_position.application_status = "approved"
                    approved_applied_position.save()
                    try:
                        context = {}
                        offer_letter_obj = OfferLetter.objects.get(offered_to=approved_applied_position)
                        context["Candidate_Name"] = approved_applied_position.applied_profile.user.get_full_name()
                        context["Position_Name"] = approved_applied_position.form_data.form_data["job_title"]
                        context["Company_Name"] = approved_applied_position.company.company_name
                        context["start_date"] = str(offer_letter_obj.start_date)
                        context["CompanyLogin_Link"] = "https://{}.{}".format(approved_applied_position.company.url_domain, settings.DOMAIN_NAME)
                        from_email = settings.EMAIL_HOST_USER
                        body_msg = render_to_string("offer_send.html", context)
                        msg = EmailMultiAlternatives(
                            "Congratulations on Your Offer Letter",
                            body_msg,
                            "Congratulations on Your Offer Letter",
                            [approved_applied_position.applied_profile.user.email],
                        )
                        msg.content_subtype = "html"
                        msg.send()
                        offer_letter_obj.offer_created_mail = True
                        offer_letter_obj.save()
                    except Exception as e:
                        message = "email not sent. " + str(e)
                else:
                    next_obj = OfferApproval.objects.filter(position=offer.position).exclude(is_approve=True).order_by("sort_order").first()
                    next_obj.show = True
                    next_obj.save()
                    offer_approval.show = False
                    offer_approval.save()
                try:
                    data = {"user": user_object.id, "description": "You Updated an Approved Offer", "type_id": 2}
                    create_activity_log(data)
                except:
                    pass
                # Send notification
                if request.data.get("is_approve") and user_object.email not in [offer.position.hiring_manager, offer.position.recruiter]:
                    try:
                        hiring_manager = User.objects.get(email=offer.position.hiring_manager, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have approved an offer approval for the position {}".format(
                                user_object.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=hiring_manager,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                        recruiter = User.objects.get(email=offer.position.recruiter, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have approved an offer approval for the position {}".format(
                                user_object.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=recruiter,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except Exception as e:
                        print(e)
                elif request.data.get("is_approve") and user_object.email in [offer.position.hiring_manager]:
                    try:
                        recruiter = User.objects.get(email=offer.position.recruiter, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have approved an offer approval for the position {}".format(
                                user_object.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=recruiter,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except:
                        pass
                elif request.data.get("is_approve") and user_object.email in [offer.position.recruiter]:
                    try:
                        hiring_manager = User.objects.get(email=offer.position.hiring_manager, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have approved an offer approval for the position {}".format(
                                user_object.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=hiring_manager,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except:
                        pass
                if request.data.get("is_reject") and user_object.email not in [offer.position.hiring_manager, offer.position.recruiter]:
                    try:
                        hiring_manager = User.objects.get(email=offer.position.hiring_manager, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have rejected an offer approval for the position {}".format(
                                user_object.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=hiring_manager,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                        recruiter = User.objects.get(email=offer.position.recruiter, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have rejected an offer approval for the position {}".format(
                                user_object.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=recruiter,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except Exception as e:
                        pass
                elif request.data.get("is_reject") and user_object.email in [offer.position.hiring_manager]:
                    try:
                        recruiter = User.objects.get(email=offer.position.recruiter, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have rejected an offer approval for the position {}".format(
                                user_object.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=recruiter,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except:
                        pass
                elif request.data.get("is_reject") and user_object.email in [offer.position.recruiter]:
                    try:
                        hiring_manager = User.objects.get(email=offer.position.hiring_manager, user_company=offer.position.company)
                        send_instant_notification(
                            message="{} have rejected an offer approval for the position {}".format(
                                user_object.get_full_name(), offer.position.form_data["job_title"]
                            ),
                            user=hiring_manager,
                            slug="/position-dashboard",
                            form_data=offer.position,
                        )
                    except:
                        pass
                Notifications.objects.filter(event_type="offer-approval", user=user_object, additional_info__form_data__id=offer.position.id).delete()
                try:
                    if int(is_hire) == 1:
                        to_email = offer.profile.user.email
                        first_name = offer.profile.user.first_name
                        company_name = offer.company.company_name
                        job_title = offer.position.form_data["job_title"]
                        from_email = settings.EMAIL_HOST_USER

                        body_msg = "Hi {}, you have been hired by {} to the job position of {}.".format(first_name, company_name, job_title)
                        context = {"body_msg": body_msg}
                        # add here
                        body_msg = render_to_string("offer.html", context)
                        msg = EmailMultiAlternatives("Email For Offer Approval<Don't Reply>", body_msg, from_email, [to_email])
                        msg.content_subtype = "html"
                        msg.send()
                except:
                    pass
                redirect_url = "https://{}.{}/hiring-manager/dashboard#newHiRes".format(user_object.user_company.url_domain, settings.DOMAIN_NAME)
                return redirect(redirect_url)
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "offer Does Not Exist",
                    }
                )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "offer Does Not Exist",
                }
            )


class AcceptPositionApprovalEmail(APIView):
    """
    This PUT function updates a Position Approval Model record according to the form_data_id passed in url.

    Args:
        pk(position_approval_id)
    Body:
        Position Approval Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) Position Approval does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Position update API",
        operation_summary="Position update API",
        request_body=FormSerializer.CreatePositionApprovalSerializer,
    )
    def get(self, request, position_approval_id):
        position_approval_id = decrypt(position_approval_id)
        try:
            data = request.data
            data = {}
            data["is_approve"] = True
            position = custom_get_object(position_approval_id, FormModel.PositionApproval)
            user_object = position.profile.user
            serializer = FormSerializer.CreatePositionApprovalSerializer(position, data=data)
            if serializer.is_valid():
                obj = serializer.save()
                total_approvals = PositionApproval.objects.filter(position=position.position).count()
                total_approved = PositionApproval.objects.filter(position=position.position, is_approve=True).count()
                if total_approved == total_approvals:
                    position.position.status = "active"
                    position.position.history.append({"date": str(datetime.datetime.now().date()), "status": "active"})
                    position.position.save()
                    position.position.save()
                elif obj.is_approve:
                    next_obj = PositionApproval.objects.filter(position=position.position).exclude(is_approve=True).order_by("sort_order").first()
                    next_obj.show = True
                    next_obj.save()
                    obj.show = False
                    obj.save()
                try:
                    data = {"user": user_object.id, "description": "You Updated a Approved Position", "type_id": 1}
                    create_activity_log(data)
                except:
                    pass
                # Send notification
                if request.data.get("is_approve"):  # and user_object.email not in [position.position.hiring_manager, position.position.recruiter]:
                    receiver_hr = [position.position.hiring_manager, position.position.recruiter]
                    if user_object.email in receiver_hr:
                        try:
                            receiver_hr.remove(user_object.email)
                        except:
                            pass
                    for i in receiver_hr:
                        try:
                            user_obj = User.objects.get(email=i, user_company=user_object.user_company)
                            send_instant_notification(
                                message="Hi, {} have approved a position approval for the position {}".format(
                                    user_object.get_full_name(), position.position.form_data["job_title"]
                                ),
                                user=user_obj,
                                form_data=position.position,
                            )
                        except Exception as e:
                            print(e)
                if request.data.get("is_reject"):  # and user_object.email not in [position.position.hiring_manager, position.position.recruiter]:
                    receiver_hr = [position.position.hiring_manager, position.position.recruiter]
                    if user_object.email in receiver_hr:
                        try:
                            receiver_hr.remove(user_object.email)
                        except:
                            pass
                    for i in receiver_hr:
                        try:
                            user_obj = User.objects.get(email=i, user_company=user_object.user_company)
                            send_instant_notification(
                                message="Hi, {} have rejected a position approval for the position {}".format(
                                    user_object.get_full_name(), position.position.form_data["job_title"]
                                ),
                                user=user_obj,
                                form_data=position.position,
                            )
                        except Exception as e:
                            print(e)
                Notifications.objects.filter(
                    event_type="position-approval", user=user_object, additional_info__form_data__id=position.position.id
                ).delete()
                redirect_url = "https://{}.{}/hiring-manager/dashboard#newHiRes".format(user_object.user_company.url_domain, settings.DOMAIN_NAME)
                return redirect(redirect_url)
            else:
                redirect_url = "https://{}.{}/hiring-manager/dashboard#newHiRes".format(user_object.user_company.url_domain, settings.DOMAIN_NAME)
                return redirect(redirect_url)
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "form Does Not Exist",
                }
            )
