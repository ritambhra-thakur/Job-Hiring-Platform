import csv
import datetime

import pandas as pd
import pytz
from django.conf import settings
from django.db.models import Avg, CharField, F, Q
from django.db.models import Value as V
from django.db.models.functions import Cast, Concat
from django.http.response import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from jmespath import search
from pytz import timezone as pytz_tz
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication

from app.CSVWriter import CSVWriter
from app.encryption import decrypt, encrypt
from app.response import ResponseBadRequest, ResponseNotFound, ResponseOk
from app.SendinSES import send_scorecard_email
from app.util import (
    custom_get_object,
    custom_get_pagination,
    custom_search,
    generate_file_name,
    paginate_data,
)
from form import utils as form_utils
from form.models import (
    AppliedPosition,
    Form,
    OfferApproval,
    OfferLetter,
    UserSelectedField,
)
from form.serializers import (
    AppliedPositionListForManagerSerializer,
    AppliedPositionListSerializer,
)
from form.utils import get_complete_feedback
from stage.models import PositionStage
from user.models import User
from user.serializers import ScorecardProfileSerializer

from .models import *
from .serializers import *


class GetAllAttribute(APIView):
    """
    This GET function fetches all records from ATTRIBUTE model with pagination, searching and sorting, and return the data after serializing it.

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
            url_domain = ""
        try:
            att_obj = Attribute.objects.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            search_keys = []
            data = custom_get_pagination(request, att_obj, Attribute, AttributeSerializer, search_keys)
            return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateAttribute(APIView):
    """
    This POST function creates a ATTRIBUTE model records from the data passes in the body.

    Args:
       None
    Body:
        ATTRIBUTE model fields
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
        operation_description="ScoreCard create API",
        operation_summary="ScoreCard create API",
        request_body=AttributeSerializer,
    )
    @csrf_exempt
    def post(self, request):
        serializer = AttributeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Attribute created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Attribute is not valid",
                }
            )


class GetAttribute(APIView):
    """
    This GET function fetches particular ID record from ATTRIBUTE model and return the data after serializing it.

    Args:
        pk(attribute_id)
    Body:
        None
    Returns:
        -Serialized ATTRIBUTE model data of particular ID(HTTP_200_OK)
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
            attribute = custom_get_object(pk, Attribute)
            serializer = AttributeSerializer(attribute)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get Attribute successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " Attribute Not Exist",
                }
            )


class UpdateAttribute(APIView):
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

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Attribute update API",
        operation_summary="Attribute update API",
        request_body=AttributeSerializer,
    )
    def put(self, request, pk):
        try:
            attribute = custom_get_object(pk, Attribute)
            serializer = AttributeSerializer(attribute, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Attribute updated successfully",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Attribute Does Not Exist",
                }
            )


class DeleteAttribute(APIView):
    """
    This DETETE function delete particular record by ID from ATTRIBUTE model according to the attribute_id passed in url.

    Args:
        pk(attribute_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if attribute_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    @csrf_exempt
    def delete(self, request, pk):
        try:
            attribute = custom_get_object(pk, Attribute)
            attribute.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Attribute deleted successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Attribute Does Not Exist",
                }
            )


# Competency Crud API's
class GetAllCompetency(APIView):
    """
    This GET function fetches all records from COMPETENCY model with pagination, searching and sorting, and return the data after serializing it.

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
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search Competency",
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
            url_domain = ""
        try:
            competency_obj = Competency.objects.all()
            competency_obj = competency_obj.filter(Q(company__url_domain=url_domain) | Q(company=None))
            serach_keys = ["competency__icontains"]
            data = custom_get_pagination(request, competency_obj, Competency, CompetencyListSerializer, serach_keys)
            return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpCompetency(APIView):
    """
    This GET function fetches all records from COMPETENCY model with pagination, searching and sorting, and return the data after serializing it.

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
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search Competency",
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
            url_domain = ""
        try:
            competency_obj = Competency.objects.all()
            competency_obj = competency_obj.filter(Q(company__url_domain=url_domain) | Q(company=None))
            serach_keys = ["competency__icontains", "attribute__attribute_name"]
            data, meta = custom_search(request, competency_obj, serach_keys)
            resp_data = []
            for i in data:
                temp_data = {}
                temp_data["id"] = i.id
                temp_data["competency"] = i.competency
                temp_data["company"] = i.company.company_name
                temp_data["company_id"] = i.company.id
                temp_data["slug"] = i.slug
                temp_data["attribute"] = []
                for j in i.attribute.all():
                    t_data = {}
                    t_data["id"] = j.id
                    t_data["attribute_name"] = j.attribute_name
                    temp_data["attribute"].append(t_data)
                resp_data.append(temp_data)
            return ResponseOk(
                {
                    "data": resp_data,
                    "message": "competency fetched",
                    "meta": meta,
                }
            )
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateCompetency(APIView):
    """
    This POST function creates a COMPETENCY model records from the data passes in the body.

    Args:
       None
    Body:
        COMPETENCY model fields
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
        operation_description="Competency create API",
        operation_summary="Competency create API",
        request_body=CompetencySerializer,
    )
    @csrf_exempt
    def post(self, request):
        serializer = CompetencySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Competency created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Competency is not valid",
                }
            )


class GetCompetency(APIView):
    """
    This GET function fetches particular ID record from COMPETENCY model and return the data after serializing it.

    Args:
        pk(competency_id)
    Body:
        None
    Returns:
        -Serialized COMPETENCY model data of particular ID(HTTP_200_OK)
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
            competency = custom_get_object(pk, Competency)
            serializer = CompetencySerializer(competency)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get Competency successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " Competency Not Exist",
                }
            )


class UpdateCompetency(APIView):
    """
    This PUT function updates particular record by ID from COMPETENCY model according to the competency_id passed in url.

    Args:
        pk(competency_id)
    Body:
        None
    Returns:
        -Serialized COMPETENCY model data of particular record by ID(HTTP_200_OK)
        -serializer.errors
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Competency update API",
        operation_summary="Competency update API",
        request_body=CompetencySerializer,
    )
    def put(self, request, pk):
        try:
            competency = custom_get_object(pk, Competency)
            serializer = CompetencySerializer(competency, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Competency updated successfully",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Competency Does Not Exist",
                }
            )


class DeleteCompetency(APIView):
    """
    This DETETE function delete particular record by ID from COMPETENCY model according to the competency_id passed in url.

    Args:
        pk(competency_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if competency_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    @csrf_exempt
    def delete(self, request, pk):
        try:
            competency = custom_get_object(pk, Competency)
            competency.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Competency deleted successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Competency Does Not Exist",
                }
            )


# class GetAllPositionAttribute(APIView):
#     """
#     This GET function fetches all records from POSITIONATTRIBUTE model with pagination, searching and sorting, and return the data after serializing it.

#     Args:
#         None
#     Body:
#         -domain(mandatory)
#         -search(optional)
#         -page(optional)
#         -perpage(optional)
#         -sort_dir(optional)
#         -sort_field(optional)
#     Returns:
#         -Fetches all serialized data(HTTP_200_OK)
#         -Search query has no match(HTTP_400_BAD_REQUEST)
#         -Exception text(HTTP_400_BAD_REQUEST)
#     Authentication:
#         JWT
#     Raises:
#         None
#     """

#     permission_classes = [permissions.IsAuthenticated]
#     authentication_classes = [authentication.JWTAuthentication]
#     domain = openapi.Parameter(
#         "domain",
#         in_=openapi.IN_QUERY,
#         description="Enter company sub domain from url",
#         type=openapi.TYPE_STRING,
#     )
#     position = openapi.Parameter(
#         "position",
#         in_=openapi.IN_QUERY,
#         description="Enter position id",
#         type=openapi.TYPE_STRING,
#     )

#     page = openapi.Parameter(
#         "page",
#         in_=openapi.IN_QUERY,
#         description="page",
#         type=openapi.TYPE_STRING,
#     )
#     perpage = openapi.Parameter(
#         "perpage",
#         in_=openapi.IN_QUERY,
#         description="perpage",
#         type=openapi.TYPE_STRING,
#     )
#     sort_dir = openapi.Parameter(
#         "sort_dir",
#         in_=openapi.IN_QUERY,
#         description="asc or desc",
#         type=openapi.TYPE_STRING,
#     )
#     sort_field = openapi.Parameter(
#         "sort_field",
#         in_=openapi.IN_QUERY,
#         description="sort_field",
#         type=openapi.TYPE_STRING,
#     )

#     @swagger_auto_schema(
#         manual_parameters=[
#             domain,
#             position,
#             page,
#             perpage,
#             sort_dir,
#             sort_field,
#         ]
#     )
#     def get(self, request):
#         data = request.GET
#         if data.get("domain") is not None:
#             url_domain = data.get("domain")
#         else:
#             raise serializers.ValidationError("domain field required")
#         if data.get("position") is not None:
#             position = data.get("position")
#         else:
#             raise serializers.ValidationError("position id field required")
#         try:
#             position_attribute = PositionAttribute.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
#             position_attribute = position_attribute.filter(Q(position=position))
#             search_keys=[]
#             data=custom_get_pagination(request, position_attribute, PositionAttribute, PositionAttributeListSerializer, search_keys)
#             return ResponseOk(data)
#         except Exception as e:
#             return ResponseBadRequest({"debug": str(e)})

# class CreatePositionAttribute(APIView):
#     """
#     This POST function creates a POSITIONATTRIBUTE model records from the data passes in the body.

#     Args:
#        None
#     Body:
#         POSITIONATTRIBUTE model fields
#     Returns:
#         -serializer.data(HTTP_200_OK)
#         -serializer.errors(HTTP_400_BAD_REQUEST)
#     Authentication:
#         JWT
#     Raises:
#         None
#     """
#     permission_classes = [permissions.IsAuthenticated]
#     authentication_classes = [authentication.JWTAuthentication]

#     @swagger_auto_schema(
#         operation_description="position create API",
#         operation_summary="position create API",
#         request_body=PositionAttributeSerializer,
#     )
#     @csrf_exempt
#     def post(self, request):
#         serializer = PositionAttributeSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return ResponseOk(
#                 {
#                     "data": serializer.data,
#                     "code": status.HTTP_200_OK,
#                     "message": "Position created successfully",
#                 }
#             )
#         else:
#             return ResponseBadRequest(
#                 {
#                     "data": serializer.errors,
#                     "code": status.HTTP_400_BAD_REQUEST,
#                     "message": "Competency is not valid",
#                 }
#             )


# class GetPositionAttribute(APIView):
#     """
#     This GET function fetches particular ID record from POSITIONATTRIBUTE model and return the data after serializing it.

#     Args:
#         pk(positionattribute_id)
#     Body:
#         None
#     Returns:
#         -Serialized POSITIONATTRIBUTE model data of particular ID(HTTP_200_OK)
#         -None(HTTP_400_BAD_REQUEST)
#     Authentication:
#         JWT
#     Raises:
#         None
#     """
#     permission_classes = [permissions.IsAuthenticated]
#     authentication_classes = [authentication.JWTAuthentication]

#     def get(self, request, pk):
#         try:
#             position = custom_get_object(pk, PositionAttribute)
#             serializer = PositionAttributeSerializer(position)
#             return ResponseOk(
#                 {
#                     "data": serializer.data,
#                     "code": status.HTTP_200_OK,
#                     "message": "get position successfully",
#                 }
#             )
#         except:
#             return ResponseBadRequest(
#                 {
#                     "data": None,
#                     "code": status.HTTP_400_BAD_REQUEST,
#                     "message": " position Not Exist",
#                 }
#             )


# class UpdatePositionAttribute(APIView):
#     """
#     This PUT function updates particular record by ID from POSITIONATTRIBUTE model according to the positionattribute_id passed in url.

#     Args:
#         pk(positionattribute_id)
#     Body:
#         None
#     Returns:
#         -Serialized POSITIONATTRIBUTE model data of particular record by ID(HTTP_200_OK)
#         -serializer.errors
#         -None(HTTP_400_BAD_REQUEST)
#     Authentication:
#         JWT
#     Raises:
#         None
#     """
#     permission_classes = [permissions.IsAuthenticated]
#     authentication_classes = [authentication.JWTAuthentication]

#     @swagger_auto_schema(
#         operation_description="Position update API",
#         operation_summary="Position update API",
#         request_body=PositionAttributeSerializer,
#     )
#     def put(self, request, pk):
#         try:
#             position = custom_get_object(pk, PositionAttribute)
#             serializer = PositionAttributeSerializer(position, data=request.data)
#             if serializer.is_valid():
#                 serializer.save()
#                 return ResponseOk(
#                     {
#                         "data": serializer.data,
#                         "code": status.HTTP_200_OK,
#                         "message": "Position updated successfully",
#                     }
#                 )
#         except:
#             return ResponseBadRequest(
#                 {
#                     "data": None,
#                     "code": status.HTTP_400_BAD_REQUEST,
#                     "message": "Position Does Not Exist",
#                 }
#             )


# class DeletePositionAttribute(APIView):
#     """
#     This DETETE function delete particular record by ID from POSITIONATTRIBUTE model according to the positionattribute_id passed in url.

#     Args:
#         pk(positionattribute_id)
#     Body:
#         None
#     Returns:
#         -None(HTTP_200_OK)
#         -None(HTTP_400_BAD_REQUEST)if positionattribute_id does not exist
#     Authentication:
#         JWT
#     Raises:
#         None
#     """

#     @csrf_exempt
#     def delete(self, request, pk):
#         try:
#             position = custom_get_object(pk, PositionAttribute)
#             position.delete()
#             return ResponseOk(
#                 {
#                     "data": None,
#                     "code": status.HTTP_200_OK,
#                     "message": "Position deleted successfully",
#                 }
#             )
#         except:
#             return ResponseBadRequest(
#                 {
#                     "data": None,
#                     "code": status.HTTP_400_BAD_REQUEST,
#                     "message": "Position Does Not Exist",
#                 }
#             )


class CompetencyCSVExport(APIView):
    """
    This GET function fetches all the data from COMPETENCY model and converts it into CSV file.

    Args:
        pk(competency_id)
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

    def get(self, request, company_id):
        queryset = Competency.objects.filter(Q(company=company_id) | Q(company=None))

        queryset_df = pd.DataFrame(
            queryset.values(
                "id",
                "competency",
                "attribute__attribute_name",
            )
        )

        writer = CSVWriter(queryset_df)
        response = writer.convert_to_csv(filename=generate_file_name("Employee", "csv"))
        return response


class GetAllPositionCompetencyAndAttribute(APIView):
    """
    This GET function fetches all records from PositionCompetencyAndAttribute model with pagination, searching and sorting, and return the data after serializing it.

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
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search_position_competency_attribute",
        type=openapi.TYPE_STRING,
    )
    position_id = openapi.Parameter(
        "position_id",
        in_=openapi.IN_QUERY,
        description="position_id",
        type=openapi.TYPE_INTEGER,
    )
    competency_id = openapi.Parameter(
        "competency_id",
        in_=openapi.IN_QUERY,
        description="competency_id",
        type=openapi.TYPE_INTEGER,
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

    @swagger_auto_schema(manual_parameters=[page, search, position_id, competency_id, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET
        url_domain = request.headers.get("domain", "")

        position_id = data.get("position_id")

        competency_id = data.get("competency_id")
        try:
            att_obj = PositionCompetencyAndAttribute.objects.filter(Q(position__company__url_domain=url_domain) | Q(position__company=None))
            if position_id is not None:
                att_obj = att_obj.filter(Q(position=position_id))
            if competency_id is not None:
                att_obj = att_obj.filter(Q(competency=competency_id))
            search_keys = ["position__form_data__icontains", "competency__competency__icontains"]
            data = custom_get_pagination(request, att_obj, PositionCompetencyAndAttribute, GetPositionCompetencyAndAttributeSerializer, search_keys)
            return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreatePositionCompetencyAndAttribute(APIView):
    """
    This POST function creates a PositionCompetencyAndAttribute model records from the data passes in the body.

    Args:
       None
    Body:
        PositionCompetencyAndAttribute model fields
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
        operation_description="Position competency And Attribute create API",
        operation_summary="Position competency And Attribute create API",
        request_body=PositionCompetencyAndAttributeSerializer,
    )
    @csrf_exempt
    def post(self, request):
        serializer = PositionCompetencyAndAttributeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Position competency And Attribute Created Successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Position competency And Attribute is not valid",
                }
            )


class GetPositionCompetencyAndAttribute(APIView):
    """
    This GET function fetches particular ID record from PositionCompetencyAndAttribute model and return the data after serializing it.

    Args:
        pk(positioncompetencyandattribute_id)
    Body:
        None
    Returns:
        -Serialized PositionCompetencyAndAttribute model data of particular ID(HTTP_200_OK)
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
            attribute = custom_get_object(pk, PositionCompetencyAndAttribute)
            serializer = GetPositionCompetencyAndAttributeSerializer(attribute)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Get Position competency And Attribute Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " Position competency And Attribute Not Exist",
                }
            )


class UpdatePositionCompetencyAndAttribute(APIView):
    """
    This PUT function updates particular record by ID from PositionCompetencyAndAttribute model according to the positioncompetencyattribute_id passed in url.

    Args:
        pk(positioncompetencyattribute_id)
    Body:
        None
    Returns:
        -Serialized PositionCompetencyAndAttribute model data of particular record by ID(HTTP_200_OK)
        -serializer.errors
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="PositionCompetencyAndAttribute update API",
        operation_summary="PositionCompetencyAndAttribute update API",
        request_body=PositionCompetencyAndAttributeSerializer,
    )
    def put(self, request, pk):
        try:
            attribute = custom_get_object(pk, PositionCompetencyAndAttribute)
            request.data["position"] = attribute.position.id
            serializer = PositionCompetencyAndAttributeSerializer(attribute, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Position competency And Attribute Updated Successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Position competency And Attribute Updated Successfully",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Position competency And Attribute Does Not Exist",
                }
            )


class DeletePositionCompetencyAndAttribute(APIView):
    """
    This DETETE function delete particular record by ID from PositionCompetencyAndAttribute model according to the positioncompetencyattribute_id passed in url.

    Args:
        pk(positioncompetencyattribute_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if positioncompetencyattribute_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    @csrf_exempt
    def delete(self, request, pk):
        try:
            att_obj = custom_get_object(pk, PositionCompetencyAndAttribute)
            att_obj.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Position competency And Attribute Deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Position competency And Attribute Does Not Exist",
                }
            )


class CreatePositionScoreCard(APIView):
    """
    This POST function creates a PositionScoreCard model records from the data passes in the body.

    Args:
       None
    Body:
        PositionScoreCard model fields
    Returns:
        -serializer.data(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="PositionScoreCard create API",
        operation_summary="PositionScoreCard create API",
        request_body=PositionScoreCardSerializer,
    )
    @csrf_exempt
    def post(self, request):
        data = request.data
        try:
            data["interviewer_profile"] = decrypt(data["interviewer_profile"])
        except:
            pass
        serializer = PositionScoreCardSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            data = serializer.data
            # Update the status and also move it to Pending Decision
            try:
                position_scorecard_obj = PositionScoreCard.objects.get(id=data["id"])
                applied_position = AppliedPosition.objects.get(
                    form_data=position_scorecard_obj.position, applied_profile=position_scorecard_obj.applied_profiles
                )
                # Old Method - December 14
                # applied_positions_count = AppliedPosition.objects.filter(form_data=position_scorecard_obj.position).count()
                # total_ratings_given = PositionScoreCard.objects.filter(position=position_scorecard_obj.position).count()
                # # Calculating total number of attributes
                # # total_attributes = PositionCompetencyAndAttribute.objects.filter(position=position_scorecard_obj.position).count()
                # total_attributes = 0
                # for position_stage in PositionStage.objects.filter(position=position_scorecard_obj.position):
                #     competencies = position_stage.competency
                #     for competency in competencies.all():
                #         total_attributes += competency.attribute.all().count()
                # list_of_interviews = applied_position_obj.data["interview_schedule_data"]["Interviewer"]
                # ratings_needed_to_give = len(list_of_interviews) * applied_positions_count * total_attributes
                # top_rated = []
                # max_rating = 0
                # if total_ratings_given == ratings_needed_to_give:
                #     # All interviews and rating are done thus move one or more to Pending Decision
                #     applied_positions = AppliedPosition.objects.filter(form_data=position_scorecard_obj.position)
                #     for applied_position in applied_positions:
                #         ratings = PositionScoreCard.objects.filter(
                #             position=position_scorecard_obj.position, applied_profiles=applied_position.applied_profile
                #         ).aggregate(Avg("rating"))["rating__avg"]
                #         temp_dict = {}
                #         temp_dict['applied_position'] = applied_position
                #         temp_dict['ratings'] = ratings
                #         top_rated.append(temp_dict)
                # top_rated = sorted(top_rated, key=lambda d: d['ratings'], reverse=True)
                # # Loop to all the  two top rated candidates and mark them completed as to move them into Pennding Decision
                # range_count = None
                # if len(top_rated) > 2:
                #     range_count = 2
                # else:
                #     range_count = 1
                # for rated in top_rated[0:range_count]:
                #     applied_position = rated['applied_position']
                #     applied_position.application_status = "pending"
                #     applied_position.save()
                # End Old Method
                """
                Old Method - May 18
                applied_position_objs = []
                applied_profile = []
                for app_pos in AppliedPosition.objects.filter(
                    form_data=position_scorecard_obj.position, data__has_key="interview_schedule_data", application_status__in=["active", "pending"]
                ):
                    try:
                        app_pos.data["interview_schedule_data"]["Interviewer"]
                        applied_position_objs.append(app_pos)
                        applied_profile.append(app_pos.applied_profile)
                    except:
                        pass
                interviews_count = 0
                for app_pos in applied_position_objs:
                    list_of_interviews = app_pos.data["interview_schedule_data"]["Interviewer"]
                    interviews_count += len(list_of_interviews)
                total_ratings_given = PositionScoreCard.objects.filter(
                    position=position_scorecard_obj.position, applied_profiles__in=applied_profile
                ).count()
                # Calculating total number of attributes
                total_attributes = 0
                for position_stage in PositionStage.objects.filter(position=position_scorecard_obj.position):
                    competencies = position_stage.competency
                    for competency in competencies.all():
                        total_attributes += competency.attribute.all().count()
                ratings_needed_to_give = interviews_count * total_attributes
                """
                # Calculating total number of attributes
                total_attributes = 0
                total_ratings_per_candidate = 0
                interview_stages = 0
                for position_stage in PositionStage.objects.filter(position=position_scorecard_obj.position, stage__is_interview=True):
                    interview_stages += 1
                    interviewers = position_stage.profiles.all().count()
                    competencies = position_stage.competency
                    for competency in competencies.all():
                        total_attributes += competency.attribute.all().count()
                        total_ratings_per_candidate += interviewers * competency.attribute.all().count()
                # Get applied position who has got all ratings
                top_rated = []
                for app_pos in AppliedPosition.objects.filter(
                    form_data=position_scorecard_obj.position,
                    data__has_key="interview_schedule_data_list",
                    application_status__in=["active", "pending"],
                ):
                    ratings = PositionScoreCard.objects.filter(position=position_scorecard_obj.position, applied_profiles=app_pos.applied_profile)
                    if ratings.count() >= total_ratings_per_candidate:
                        ratings = ratings.aggregate(Avg("rating"))["rating__avg"]
                        temp_dict = {}
                        temp_dict["applied_position"] = app_pos
                        temp_dict["ratings"] = ratings
                        top_rated.append(temp_dict)
                top_rated = sorted(top_rated, key=lambda d: d["ratings"], reverse=True)

                # top_rated = []
                # if ratings_needed_to_give <= total_ratings_given:
                #     for applied_position in applied_position_objs:
                #         ratings = PositionScoreCard.objects.filter(
                #             position=position_scorecard_obj.position, applied_profiles=applied_position.applied_profile
                #         ).aggregate(Avg("rating"))["rating__avg"]
                #         temp_dict = {}
                #         temp_dict["applied_position"] = applied_position
                #         temp_dict["ratings"] = ratings
                #         top_rated.append(temp_dict)
                # top_rated = sorted(top_rated, key=lambda d: d["ratings"], reverse=True)
                # Loop to all the  two top rated candidates and mark them completed as to move them into Pennding Decision
                try:
                    if len(top_rated) > 0:
                        top_rating = top_rated[0]["ratings"]
                        for rated in top_rated:
                            if rated["ratings"] == top_rating and top_rating > 0:
                                applied_position = rated["applied_position"]
                                applied_position.application_status = "pending"
                                applied_position.save()
                            else:
                                applied_position = rated["applied_position"]
                                applied_position.application_status = "active"
                                applied_position.save()
                except:
                    pass

                # range_count = None
                # if len(top_rated) > 1:
                #     range_count = 2
                # else:
                #     range_count = 1
                # for rated in top_rated[0:range_count]:
                #     applied_position = rated["applied_position"]
                #     applied_position.application_status = "pending"
                #     applied_position.save()
                # for rated in top_rated[range_count:]:
                #     applied_position = rated["applied_position"]
                #     applied_position.application_status = "active"
                #     applied_position.save()
            except Exception as e:
                return ResponseBadRequest(
                    {
                        "data": str(e),
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "The postion score card is created Successfully! But error in changing the status.",
                    }
                )
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "The postion score card is created Successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "The postion score card does is not valid",
                }
            )


class GetAllPostionScoreCard(APIView):
    """
    This GET function fetches all records from PositionScoreCard model with pagination, searching and sorting, and returns the data after serializing it.

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
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        try:
            queryset = PositionScoreCard.objects.all()
            socrecard_obj = queryset.filter(Q(position__company__url_domain=url_domain) | Q(position__company=None))
            search_keys = []
            data = custom_get_pagination(request, queryset, socrecard_obj, PositionScoreCardSerializer, search_keys)
            return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetScorecardByAppliedPosition(APIView):
    def get(self, request, pk, format=None):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        pending_interviewer_list = []
        try:
            application_obj = AppliedPosition.objects.get(id=pk)
        except AppliedPosition.DoesNotExist:
            return ResponseBadRequest(
                {
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Profile Not Found",
                }
            )
        interviewer_ids = []
        try:
            for interview in application_obj.data["interview_schedule_data_list"]:
                for id in interview["Interviewer"]:
                    interviewer_ids.append(id)
        except:
            pass

        for interviewer in interviewer_ids:
            int_id = interviewer.get("profile_id", 0)
            score_obj = PositionScoreCard.objects.filter(
                position=application_obj.form_data, applied_profiles=application_obj.applied_profile.id, interviewer_profile=interviewer["profile_id"]
            )
            pending_interviewer_list.append(interviewer["profile_id"])

        profile_obj = Profile.objects.filter(id__in=pending_interviewer_list)
        context = {"applied_position_obj": application_obj}
        serializer = ScorecardProfileSerializer(profile_obj, many=True, context=context)
        return ResponseOk(
            {
                "data": serializer.data,
                "code": status.HTTP_200_OK,
                "message": "Scorecard Details Fetched Successfully.",
            }
        )


class GetAllPendingPostionScoreCard(APIView):
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk, format=None):
        timezone = request.META.get("HTTP_TIMEZONE")
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        pending_interviewer_list = []
        applied_position_list = []
        try:
            pk = int(decrypt(pk))
        except:
            pass
        try:
            interviewer_obj = Profile.objects.get(id=pk).user
        except Profile.DoesNotExist:
            return ResponseBadRequest(
                {
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Please specify the correct Profile ID",
                }
            )

        if data.get("export"):
            export = True
        else:
            export = False
        query = data.get("search", "")
        own_true = data.get("own_data", False)
        application_obj = AppliedPosition.objects.filter(
            company=interviewer_obj.user_company.id, application_status__in=["active", "pending"], form_data__status="active"
        )
        if query:
            application_obj = application_obj.annotate(
                full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name")
            ).filter(Q(full_name__icontains=query) | Q(applied_profile__user__email__icontains=query))
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
                    if own_true and application.data.get("interview_cancelled", False) == False:
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
                    elif pk == int_id and application.data.get("interview_cancelled", False) == False:
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
        context = {"pending_interviewer_ids": pending_interviewer_list, "own_id": pk}
        serializer = AppliedPositionListSerializer(applied_position_list, many=True, context=context)
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
            for data in applied_position_list:
                serializer_data = AppliedPositionListSerializer(data).data
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
            return Response(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Pending Scorecard Details fetched successfully.",
                },
                status=status.HTTP_200_OK,
            )


class GetAllOpPendingPostionScoreCard(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk, format=None):
        timezone = request.META.get("HTTP_TIMEZONE")
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        pending_interviewer_list = []
        applied_position_list = []
        try:
            pk = int(decrypt(pk))
        except:
            pass
        try:
            interviewer_obj = Profile.objects.get(id=pk).user
        except Profile.DoesNotExist:
            return ResponseBadRequest(
                {
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Please specify the correct Profile ID",
                }
            )

        if data.get("export"):
            export = True
        else:
            export = False
        query = data.get("search", "")
        own_true = data.get("own_data", False)
        application_obj = AppliedPosition.objects.filter(
            company=interviewer_obj.user_company.id, application_status__in=["active", "pending"], form_data__status="active"
        )
        if query:
            application_obj = application_obj.annotate(
                full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name")
            ).filter(Q(full_name__icontains=query) | Q(applied_profile__user__email__icontains=query))
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
                    if own_true and application.data.get("interview_cancelled", False) == False:
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
                    elif pk == int_id and application.data.get("interview_cancelled", False) == False:
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
        context = {"pending_interviewer_ids": pending_interviewer_list, "own_id": pk}
        # serializer = AppliedPositionListSerializer(applied_position_list, many=True, context=context)
        current_candidate = request.GET.get("current_candidate")
        next_candidate = {}
        prev_candidate = {}
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            fields = ["Position No", "Position Name", "Hiring Manager", "Recruiter", "Candidate Name", "Rating", "Status"]
            writer.writerow(fields)
            for i in applied_position_list:
                row = []
                row.append(i.form_data.show_id)
                row.append(i.form_data.form_data["job_title"])
                try:
                    user_obj = User.objects.get(email__iexact=i.form_data.hiring_manager, user_company=i.form_data.company)
                    row.append(user_obj.get_full_name())
                except:
                    row.append(i.form_data.hiring_manager)
                try:
                    user_obj = User.objects.get(email__iexact=i.form_data.recruiter, user_company=i.form_data.company)
                    row.append(user_obj.get_full_name())
                except:
                    row.append(i.form_data.recruiter)
                row.append(i.applied_profile.user.get_full_name())
                rating = PositionScoreCard.objects.filter(position=i.form_data, applied_profiles=i.applied_profile).aggregate(Avg("rating"))[
                    "rating__avg"
                ]
                if rating:
                    row.append(rating)
                else:
                    row.append(0)
                row.append(i.application_status)
                writer.writerow(row)
            response = HttpResponse(csv_response, content_type="text/csv")
            return response
        else:
            pagination_data = paginate_data(request, applied_position_list, AppliedPosition)
            applied_position_list = pagination_data.get("paginate_data")
            data = []
            next = None
            for count, i in enumerate(applied_position_list):
                temp_data = {}
                temp_data["applied_profile_id"] = i.applied_profile.id
                temp_data["id"] = i.id
                temp_data["position_id"] = i.form_data.id
                temp_data["sposition_id"] = i.form_data.show_id
                temp_data["position_no"] = i.form_data.id
                temp_data["position_name"] = i.form_data.form_data["job_title"]
                temp_data["candidate_name"] = i.applied_profile.user.get_full_name()
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
                temp_data["status"] = i.application_status
                temp_data["data"] = i.data
                rating = PositionScoreCard.objects.filter(position=i.form_data, applied_profiles=i.applied_profile).aggregate(Avg("rating"))[
                    "rating__avg"
                ]
                if rating:
                    temp_data["ratings"] = rating
                else:
                    temp_data["ratings"] = 0
                temp_data["feedback"] = get_complete_feedback(i, pk)
                data.append(temp_data)
                if current_candidate and (temp_data["id"] == int(current_candidate)):
                    try:
                        prev_candidate["id"] = data[-2]["id"]
                        prev_candidate["applied_profile"] = {}
                        prev_candidate["applied_profile"]["id"] = data[-2]["applied_profile_id"]
                        prev_candidate["form_data_id"] = data[-2]["position_id"]
                        prev_candidate["sposition_id"] = i.form_data.show_id
                    except Exception as e:
                        print(e)
                    next = True
                    continue
                if next:
                    try:
                        next_candidate["id"] = i.id
                        next_candidate["applied_profile"] = {}
                        next_candidate["applied_profile"]["id"] = i.applied_profile.id
                        next_candidate["form_data_id"] = i.form_data.id
                        next = None
                    except Exception as e:
                        print(e)
            current_can_data = None
            if current_candidate:
                data = next_candidate
                current_can_data = {}
                current_can_data["data"] = {}
                current_can_data["application_status"] = i.application_status
                current_can_data["data"]["history"] = i.data.get("history", [])
                current_can_data["data"]["history_detail"] = i.data.get("history_detail", [])
                current_can_data["data"]["rejected_by"] = i.data.get("rejected_by", None)
                current_can_data["data"]["reason"] = i.data.get("reason", "")
                current_can_data["data"]["current_stage_id"] = i.data.get("current_stage_id", 0)
                current_can_data["applied_profile"] = {}
                current_can_data["applied_profile"]["id"] = i.applied_profile.id
                current_can_data["form_data"] = {
                    "form_data": {"job_title": i.form_data.form_data.get("job_title")},
                    "id": i.form_data.id,
                    "sposition_id": i.form_data.show_id,
                }
                current_can_data["applicant_details"] = {"first_name": i.applicant_details.get("first_name")}
            return Response(
                {
                    "data": data,
                    "previous_data": prev_candidate,
                    "current_user": current_can_data,
                    "code": status.HTTP_200_OK,
                    "meta": {
                        "page": pagination_data.get("page"),
                        "total_pages": pagination_data.get("total_pages"),
                        "perpage": pagination_data.get("perpage"),
                        "total_records": pagination_data.get("total_records"),
                    },
                    "message": "Pending Scorecard Details fetched successfully.",
                },
                status=status.HTTP_200_OK,
            )


class GetAllOpPendingPostionScoreCardOpen(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk, format=None):
        timezone = request.META.get("HTTP_TIMEZONE")
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        pending_interviewer_list = []
        applied_position_list = []
        try:
            pk = int(decrypt(pk))
        except:
            pass
        try:
            interviewer_obj = Profile.objects.get(id=pk).user
        except Profile.DoesNotExist:
            return ResponseBadRequest(
                {
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Please specify the correct Profile ID",
                }
            )

        if data.get("export"):
            export = True
        else:
            export = False
        query = data.get("search", "")
        own_true = data.get("own_data", False)
        application_obj = AppliedPosition.objects.filter(
            company=interviewer_obj.user_company.id, application_status__in=["active", "pending"], form_data__status="active"
        ).filter(Q(form_data__recruiter=interviewer_obj.email) | Q(form_data__hiring_manager=interviewer_obj.email))
        if query:
            application_obj = application_obj.annotate(
                full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name")
            ).filter(Q(full_name__icontains=query) | Q(applied_profile__user__email__icontains=query))
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
                    if own_true and application.data.get("interview_cancelled", False) == False:
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
                    elif pk == int_id and application.data.get("interview_cancelled", False) == False:
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

        applied_position_list = list(set(applied_position_list))
        context = {"pending_interviewer_ids": pending_interviewer_list, "own_id": pk}
        current_candidate = request.GET.get("current_candidate")
        next_candidate = {}
        prev_candidate = {}
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            fields = ["Position No", "Position Name", "Hiring Manager", "Recruiter", "Candidate Name", "Rating", "Status"]
            writer.writerow(fields)

            for i in applied_position_list:
                row = []
                row.append(i.form_data.show_id)
                row.append(i.form_data.form_data["job_title"])
                try:
                    user_obj = User.objects.get(email__iexact=i.form_data.hiring_manager, user_company=i.form_data.company)
                    row.append(user_obj.get_full_name())
                except:
                    row.append(i.form_data.hiring_manager)
                try:
                    user_obj = User.objects.get(email__iexact=i.form_data.recruiter, user_company=i.form_data.company)
                    row.append(user_obj.get_full_name())
                except:
                    row.append(i.form_data.recruiter)
                row.append(i.applied_profile.user.get_full_name())
                rating = PositionScoreCard.objects.filter(position=i.form_data, applied_profiles=i.applied_profile).aggregate(Avg("rating"))[
                    "rating__avg"
                ]
                if rating:
                    row.append(rating)
                else:
                    row.append(0)
                row.append(i.application_status)
                writer.writerow(row)
            response = HttpResponse(csv_response, content_type="text/csv")
            return response
        else:
            pagination_data = paginate_data(request, applied_position_list, AppliedPosition)
            applied_position_list = pagination_data.get("paginate_data")
            data = []
            next = None
            for count, i in enumerate(applied_position_list):
                temp_data = {}
                temp_data["applied_profile_id"] = i.applied_profile.id
                temp_data["id"] = i.id
                temp_data["position_id"] = i.form_data.id
                temp_data["sposition_id"] = i.form_data.show_id
                temp_data["position_no"] = i.form_data.id
                temp_data["position_name"] = i.form_data.form_data["job_title"]
                temp_data["candidate_name"] = i.applied_profile.user.get_full_name()
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
                temp_data["status"] = i.application_status
                temp_data["data"] = i.data
                rating = PositionScoreCard.objects.filter(position=i.form_data, applied_profiles=i.applied_profile).aggregate(Avg("rating"))[
                    "rating__avg"
                ]
                ratings_data = []
                for inter in i.data.get("interview_schedule_data_list"):
                    if inter["date"] != "":
                        try:
                            interviews = []
                            for single_inter in inter["Interviewer"]:
                                ratings = PositionScoreCard.objects.filter(
                                    position__id=i.form_data.id,
                                    interviewer_profile=single_inter["value"],
                                    applied_profiles__id=i.applied_profile.id,
                                ).aggregate(Avg("rating"))["rating__avg"]
                                single_inter["ratings"] = ratings
                                if ratings:
                                    single_inter["interview_done"] = True
                                else:
                                    single_inter["interview_done"] = False
                                try:
                                    single_inter["eprofile_id"] = encrypt(single_inter["profile_id"])
                                except:
                                    pass
                                if request.user.email in [i.form_data.hiring_manager, i.form_data.recruiter]:
                                    ratings_data.append(single_inter)
                                elif int(request.user.profile.id) in single_inter["value"]:
                                    ratings_data.append(single_inter)
                        except Exception as e:
                            print(e, "---")
                if rating:
                    temp_data["ratings"] = rating
                else:
                    temp_data["ratings"] = 0
                temp_data["ratings_data"] = ratings_data
                temp_data["location"] = i.form_data.form_data["location"][0]["label"]
                data.append(temp_data)
                if current_candidate and (temp_data["id"] == int(current_candidate)):
                    try:
                        prev_candidate["id"] = data[-2]["id"]
                        prev_candidate["applied_profile"] = {}
                        prev_candidate["applied_profile"]["id"] = data[-2]["applied_profile_id"]
                        prev_candidate["form_data_id"] = data[-2]["position_id"]
                        prev_candidate["sposition_id"] = data[-2]["sposition_id"]
                    except Exception as e:
                        print(e)
                    next = True
                    continue
                if next:
                    try:
                        next_candidate["id"] = i.id
                        next_candidate["applied_profile"] = {}
                        next_candidate["applied_profile"]["id"] = i.applied_profile.id
                        next_candidate["form_data_id"] = i.form_data.id
                        next_candidate["sposition_id"] = i.form_data.show_id
                        next = None
                    except Exception as e:
                        print(e)
            current_can_data = None
            if current_candidate:
                data = next_candidate
                current_can_data = {}
                current_can_data["data"] = {}
                current_can_data["application_status"] = i.application_status
                current_can_data["data"]["history"] = i.data.get("history", [])
                current_can_data["data"]["history_detail"] = i.data.get("history_detail", [])
                current_can_data["data"]["rejected_by"] = i.data.get("rejected_by", None)
                current_can_data["data"]["reason"] = i.data.get("reason", "")
                current_can_data["data"]["current_stage_id"] = i.data.get("current_stage_id", 0)
                current_can_data["applied_profile"] = {}
                current_can_data["applied_profile"]["id"] = i.applied_profile.id
                current_can_data["form_data"] = {
                    "form_data": {"job_title": i.form_data.form_data.get("job_title")},
                    "id": i.form_data.id,
                    "sposition_id": i.form_data.show_id,
                }
                current_can_data["applicant_details"] = {"first_name": i.applicant_details.get("first_name")}
            return Response(
                {
                    "data": data,
                    "previous_data": prev_candidate,
                    "current_user": current_can_data,
                    "code": status.HTTP_200_OK,
                    "meta": {
                        "page": pagination_data.get("page"),
                        "total_pages": pagination_data.get("total_pages"),
                        "perpage": pagination_data.get("perpage"),
                        "total_records": pagination_data.get("total_records"),
                    },
                    "message": "Pending Scorecard Details fetched successfully.",
                },
                status=status.HTTP_200_OK,
            )


class GetPostionScoreCard(APIView):
    """
    This GET function fetches particular ID record from PositionScoreCard model and return the data after serializing it.

    Args:
        pk(positionscorecard_id)
    Body:
        None
    Returns:
        -Serialized PositionScoreCard model data of particular ID(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)
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
            scorecard = PositionScoreCard.objects.get(id=pk)
            serializer = ListPositionScoreCardSerializer(scorecard)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": f"Got the postion score card {pk} successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "The postion score card does not exist",
                }
            )


class UpdatePositionScoreCard(APIView):
    """
    This PUT function updates particular record by ID from PositionScoreCard model according to the competency_id passed in url.

    Args:
        pk(positionscorecard_id)
    Body:
        None
    Returns:
        -Serialized PositionScoreCard model data of particular record by ID(HTTP_200_OK)
        -serializer.errors
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="PositionScoreCard create API",
        operation_summary="PositionScoreCard create API",
        request_body=PositionScoreCardSerializer,
    )
    def put(self, request, pk):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            scorecard = PositionScoreCard.objects.get(id=pk)
            data = request.data
            try:
                data["interviewer_profile"] = decrypt(data["interviewer_profile"])
            except:
                pass
            serializer = PositionScoreCardSerializer(scorecard, data=data)
            if serializer.is_valid():
                serializer.save()
                data = serializer.data
                try:
                    position_scorecard_obj = PositionScoreCard.objects.get(id=data["id"])
                    applied_position = AppliedPosition.objects.get(
                        form_data=position_scorecard_obj.position, applied_profile=position_scorecard_obj.applied_profiles
                    )
                    # Old Method - December 14
                    # applied_positions_count = AppliedPosition.objects.filter(form_data=position_scorecard_obj.position).count()
                    # total_ratings_given = PositionScoreCard.objects.filter(position=position_scorecard_obj.position).count()
                    # # Calculating total number of attributes
                    # # total_attributes = PositionCompetencyAndAttribute.objects.filter(position=position_scorecard_obj.position).count()
                    # total_attributes = 0
                    # for position_stage in PositionStage.objects.filter(position=position_scorecard_obj.position):
                    #     competencies = position_stage.competency
                    #     for competency in competencies.all():
                    #         total_attributes += competency.attribute.all().count()
                    # list_of_interviews = applied_position_obj.data["interview_schedule_data"]["Interviewer"]
                    # ratings_needed_to_give = len(list_of_interviews) * applied_positions_count * total_attributes
                    # top_rated = []
                    # max_rating = 0
                    # if total_ratings_given == ratings_needed_to_give:
                    #     # All interviews and rating are done thus move one or more to Pending Decision
                    #     applied_positions = AppliedPosition.objects.filter(form_data=position_scorecard_obj.position)
                    #     for applied_position in applied_positions:
                    #         ratings = PositionScoreCard.objects.filter(
                    #             position=position_scorecard_obj.position, applied_profiles=applied_position.applied_profile
                    #         ).aggregate(Avg("rating"))["rating__avg"]
                    #         temp_dict = {}
                    #         temp_dict['applied_position'] = applied_position
                    #         temp_dict['ratings'] = ratings
                    #         top_rated.append(temp_dict)
                    # top_rated = sorted(top_rated, key=lambda d: d['ratings'], reverse=True)
                    # # Loop to all the  two top rated candidates and mark them completed as to move them into Pennding Decision
                    # range_count = None
                    # if len(top_rated) > 2:
                    #     range_count = 2
                    # else:
                    #     range_count = 1
                    # for rated in top_rated[0:range_count]:
                    #     applied_position = rated['applied_position']
                    #     applied_position.application_status = "pending"
                    #     applied_position.save()
                    # End Old Method
                    """
                    Old Method - May 18
                    applied_position_objs = []
                    applied_profile = []
                    for app_pos in AppliedPosition.objects.filter(
                        form_data=position_scorecard_obj.position,
                        data__has_key="interview_schedule_data",
                        application_status__in=["active", "pending"],
                    ):
                        try:
                            app_pos.data["interview_schedule_data"]["Interviewer"]
                            applied_position_objs.append(app_pos)
                            applied_profile.append(app_pos.applied_profile)
                        except:
                            pass
                    interviews_count = 0
                    for app_pos in applied_position_objs:
                        list_of_interviews = app_pos.data["interview_schedule_data"]["Interviewer"]
                        interviews_count += len(list_of_interviews)
                    total_ratings_given = PositionScoreCard.objects.filter(
                        position=position_scorecard_obj.position, applied_profiles__in=applied_profile
                    ).count()
                    # Calculating total number of attributes
                    total_attributes = 0
                    for position_stage in PositionStage.objects.filter(position=position_scorecard_obj.position):
                        competencies = position_stage.competency
                        for competency in competencies.all():
                            total_attributes += competency.attribute.all().count()
                    ratings_needed_to_give = interviews_count * total_attributes
                    """
                    # Calculating total number of attributes
                    total_attributes = 0
                    total_ratings_per_candidate = 0
                    interview_stages = 0
                    for position_stage in PositionStage.objects.filter(position=position_scorecard_obj.position, stage__is_interview=True):
                        interview_stages += 1
                        interviewers = position_stage.profiles.all().count()
                        competencies = position_stage.competency
                        for competency in competencies.all():
                            total_attributes += competency.attribute.all().count()
                            total_ratings_per_candidate += interviewers * competency.attribute.all().count()
                    # Get applied position who has got all ratings
                    top_rated = []
                    for app_pos in AppliedPosition.objects.filter(
                        form_data=position_scorecard_obj.position,
                        data__has_key="interview_schedule_data_list",
                        application_status__in=["active", "pending"],
                    ):
                        ratings = PositionScoreCard.objects.filter(position=position_scorecard_obj.position, applied_profiles=app_pos.applied_profile)
                        if ratings.count() >= total_ratings_per_candidate:
                            ratings = ratings.aggregate(Avg("rating"))["rating__avg"]
                            temp_dict = {}
                            temp_dict["applied_position"] = app_pos
                            temp_dict["ratings"] = ratings
                            top_rated.append(temp_dict)
                    top_rated = sorted(top_rated, key=lambda d: d["ratings"], reverse=True)
                    # top_rated = []
                    # if ratings_needed_to_give <= total_ratings_given:
                    #     for applied_position in applied_position_objs:
                    #         ratings = PositionScoreCard.objects.filter(
                    #             position=position_scorecard_obj.position, applied_profiles=applied_position.applied_profile
                    #         ).aggregate(Avg("rating"))["rating__avg"]
                    #         temp_dict = {}
                    #         temp_dict["applied_position"] = applied_position
                    #         temp_dict["ratings"] = ratings
                    #         top_rated.append(temp_dict)
                    # top_rated = sorted(top_rated, key=lambda d: d["ratings"], reverse=True)
                    # Loop to all the  two top rated candidates and mark them completed as to move them into Pennding Decision

                    try:
                        if len(top_rated) > 0:
                            top_rating = top_rated[0]["ratings"]
                            for rated in top_rated:
                                if rated["ratings"] == top_rating and top_rating > 0:
                                    applied_position = rated["applied_position"]
                                    applied_position.application_status = "pending"
                                    applied_position.save()
                                else:
                                    applied_position = rated["applied_position"]
                                    applied_position.application_status = "active"
                                    applied_position.save()
                    except:
                        pass

                    # range_count = None
                    # if len(top_rated) > 1:
                    #     range_count = 2
                    # else:
                    #     range_count = 1
                    # for rated in top_rated[0:range_count]:
                    #     applied_position = rated["applied_position"]
                    #     applied_position.application_status = "pending"
                    #     applied_position.save()
                    # for rated in top_rated[range_count:]:
                    #     applied_position = rated["applied_position"]
                    #     applied_position.application_status = "active"
                    #     applied_position.save()
                except Exception as e:
                    return ResponseBadRequest(
                        {
                            "data": str(e),
                            "code": status.HTTP_400_BAD_REQUEST,
                            "message": "The postion score card is created Successfully! But error in changing the status.",
                        }
                    )
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "The position score card is updated Successfully",
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
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "The postion score card does not exist",
                }
            )


class DeletePostionScoreCard(APIView):
    """
    This DETETE function deletes the particular record by ID from PositionScoreCard model according to the competency_id passed in url.

    Args:
        pk(positionscorecard_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if positionscorecard_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    @csrf_exempt
    def delete(self, request, pk):
        try:
            scorecard = PositionScoreCard.objects.get(id=pk)
            scorecard.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "The postion score card is deleted successfully",
                }
            )
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "The postion scorecard does not exist",
                }
            )


class SendScorecardEmail(APIView):
    # parser_classes = [MultiPartParser]
    candidate_id = openapi.Parameter(
        "candidate_id",
        in_=openapi.IN_QUERY,
        description="candidate_id",
        type=openapi.TYPE_STRING,
    )
    position_id = openapi.Parameter(
        "position_id",
        in_=openapi.IN_QUERY,
        description="position_id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[candidate_id, position_id])
    def post(self, request, interview_id, format=None):
        data = request.GET
        try:
            interview_id = int(decrypt(interview_id))
        except:
            pass
        try:
            user_obj = Profile.objects.get(id=interview_id).user
            # user_obj = User.objects.get(id=interview_id)
        except User.DoesNotExist:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "User Does Not Exist",
                }
            )

        to_email = user_obj.email
        print(to_email)
        candidate_id = data["candidate_id"]
        position_id = data["position_id"]
        link = "https://infer.softuvo.click/interviewer/scorecardsubmit/" + str(candidate_id) + "/" + str(position_id)
        res = send_scorecard_email(to_email, "Please share the rating in the Scorecard", link)
        print(res)
        return ResponseOk(
            {
                "data": None,
                "code": status.HTTP_200_OK,
                "message": "Scorecard eMail Sent Successfully",
            }
        )


class GetAllPendingDecision(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk, format=None):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        if data.get("export"):
            export = True
        else:
            export = False
        if data.get("search"):
            search = data.get("search")
        else:
            search = ""
        pending_interviewer_list = []
        applied_position_list = []
        try:
            pk = int(decrypt(pk))
        except:
            pass
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
        if search:
            application_obj = application_obj.annotate(
                full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
            ).filter(
                Q(full_name__icontains=search)
                | Q(applied_profile__user__email__icontains=search)
                | Q(form_data__form_data__job_title__icontains=search)
                | Q(string_id__icontains=search)
            )
        for application in application_obj:
            try:
                interviewer_ids = application.data["interview_schedule_data"]["Interviewer"]
            except:
                interviewer_ids = []
            for interviewer in interviewer_ids:
                try:
                    int_id = interviewer["profile_id"]
                except:
                    int_id = 0
                if pk == int_id:
                    pending_interviewer_list.append(interviewer["profile_id"])
                    applied_position_list.append(application)
            if application.form_data.hiring_manager == interviewer_obj.email or application.form_data.recruiter == interviewer_obj.email:
                # Return all applied position with status pending as the hiring manager has logged in
                # check if hiringmanaer, recruiter logged in then return all the pending decision
                applied_position_list = AppliedPosition.objects.filter(
                    company=interviewer_obj.user_company.id, application_status__in=["pending", "kiv"], form_data__status="active"
                )
                applied_position_list = applied_position_list.filter(
                    Q(form_data__recruiter=interviewer_obj.email) | Q(form_data__hiring_manager=interviewer_obj.email)
                )
                if search:
                    applied_position_list = applied_position_list.annotate(
                        full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                        string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                    ).filter(
                        Q(full_name__icontains=search)
                        | Q(applied_profile__user__email__icontains=search)
                        | Q(form_data__form_data__job_title__icontains=search)
                        | Q(string_id__icontains=search)
                    )
                break
        applied_position_list = list(set(applied_position_list))
        context = {"pending_interviewer_ids": pending_interviewer_list, "own_id": pk}
        serializer = AppliedPositionListForManagerSerializer(applied_position_list, many=True, context=context)
        data = serializer.data
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
            for data in applied_position_list:
                serializer_data = AppliedPositionListSerializer(data).data
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
            final_data = sorted(data, key=lambda d: d["average_scorecard_rating"], reverse=True)
            return ResponseOk(
                {
                    "data": final_data,
                    "code": status.HTTP_200_OK,
                    "message": "Pending Decision Details fetched successfully.",
                }
            )


class GetAllOpPendingDecision(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk, format=None):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        if data.get("export"):
            export = True
        else:
            export = False
        if data.get("search"):
            search = data.get("search")
        else:
            search = ""
        pending_interviewer_list = []
        applied_position_list = []
        try:
            pk = int(decrypt(pk))
        except:
            pass
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
        if search:
            application_obj = application_obj.annotate(
                full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
            ).filter(
                Q(full_name__icontains=search)
                | Q(applied_profile__user__email__icontains=search)
                | Q(form_data__form_data__job_title__icontains=search)
                | Q(string_id__icontains=search)
            )
        for application in application_obj:
            try:
                interviewer_ids = application.data["interview_schedule_data"]["Interviewer"]
            except:
                interviewer_ids = []
            for interviewer in interviewer_ids:
                try:
                    int_id = interviewer["profile_id"]
                except:
                    int_id = 0
                if pk == int_id:
                    pending_interviewer_list.append(interviewer["profile_id"])
                    applied_position_list.append(application)
            if application.form_data.hiring_manager == interviewer_obj.email or application.form_data.recruiter == interviewer_obj.email:
                # Return all applied position with status pending as the hiring manager has logged in
                # check if hiringmanaer, recruiter logged in then return all the pending decision
                applied_position_list = AppliedPosition.objects.filter(
                    company=interviewer_obj.user_company.id, application_status__in=["pending", "kiv"], form_data__status="active"
                )
                applied_position_list = applied_position_list.filter(
                    Q(form_data__recruiter=interviewer_obj.email) | Q(form_data__hiring_manager=interviewer_obj.email)
                )
                if search:
                    applied_position_list = applied_position_list.annotate(
                        full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                        string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                    ).filter(
                        Q(full_name__icontains=search)
                        | Q(applied_profile__user__email__icontains=search)
                        | Q(form_data__form_data__job_title__icontains=search)
                        | Q(string_id__icontains=search)
                    )
                break
        applied_position_list = list(set(applied_position_list))
        context = {"pending_interviewer_ids": pending_interviewer_list, "own_id": pk}
        # serializer = AppliedPositionListForManagerSerializer(applied_position_list, many=True, context=context)
        # data = serializer.data
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            fields = ["Position No", "Position Name", "Recruiter", "Candidate Name", "Rating", "Status"]
            writer.writerow(fields)
            for i in applied_position_list:
                row = []
                row.append(i.form_data.show_id)
                row.append(i.form_data.form_data["job_title"])
                try:
                    user_obj = User.objects.get(email__iexact=i.form_data.recruiter, user_company=i.form_data.company)
                    row.append(user_obj.get_full_name())
                except:
                    row.append(i.form_data.recruiter)
                row.append(i.applied_profile.user.get_full_name())
                rating = PositionScoreCard.objects.filter(position=i.form_data, applied_profiles=i.applied_profile).aggregate(Avg("rating"))[
                    "rating__avg"
                ]
                row.append(rating)
                row.append(i.application_status)
                writer.writerow(row)
            response = HttpResponse(csv_response, content_type="text/csv")
            return response
        else:
            # final_data = sorted(data, key=lambda d: d["average_scorecard_rating"], reverse=True)
            data = []
            for i in applied_position_list:
                temp_data = {}
                temp_data["applied_profile_id"] = i.applied_profile.id
                temp_data["id"] = i.id
                temp_data["form_data"] = i.form_data.form_data
                temp_data["sposition_id"] = i.form_data.show_id
                temp_data["position_id"] = i.form_data.id
                temp_data["position_no"] = i.form_data.id
                temp_data["position_name"] = i.form_data.form_data["job_title"]
                temp_data["candidate_name"] = i.applied_profile.user.get_full_name()
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
                temp_data["location"] = i.form_data.form_data["location"][0]["label"]
                temp_data["status"] = i.application_status
                temp_data["data"] = i.data
                rating = PositionScoreCard.objects.filter(position=i.form_data, applied_profiles=i.applied_profile).aggregate(Avg("rating"))[
                    "rating__avg"
                ]
                if rating:
                    temp_data["ratings"] = rating
                else:
                    temp_data["ratings"] = 0
                if i.data.get("interview_schedule_data_list", []):
                    temp_data["data"] = {"interview_schedule_data": i.data.get("interview_schedule_data_list", [])[-1]}
                data.append(temp_data)
            final_data = sorted(data, key=lambda d: d["ratings"], reverse=True)
            return ResponseOk(
                {
                    "data": final_data,
                    "code": status.HTTP_200_OK,
                    "message": "Pending Decision Details fetched successfully.",
                }
            )


class GetAllPendingOffer(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk, format=None):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        if data.get("export"):
            export = True
        else:
            export = False
        pending_interviewer_list = []
        applied_position_list = []
        try:
            pk = int(decrypt(pk))
        except:
            pass
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
        application_obj = application_obj.exclude(form_data__status__in=["canceled", "closed", "draft"])
        data = request.GET
        search = data.get("search")
        if search:
            application_obj = application_obj.annotate(
                full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
            ).filter(
                Q(full_name__icontains=search)
                | Q(applied_profile__user__email__icontains=search)
                | Q(form_data__form_data__job_title__icontains=search)
                | Q(string_id__icontains=search)
            )
        for application in application_obj:
            try:
                interviewer_ids = application.data["interview_schedule_data"]["Interviewer"]
            except:
                interviewer_ids = []
            for interviewer in interviewer_ids:
                try:
                    int_id = interviewer["profile_id"]
                except:
                    int_id = 0
                if pk == int_id:
                    score_obj = PositionScoreCard.objects.filter(
                        position=application.form_data,
                        applied_profiles=application.applied_profile.id,
                        interviewer_profile=interviewer["profile_id"],
                    )
                    if len(score_obj) == 0:
                        pending_interviewer_list.append(interviewer["profile_id"])
                        applied_position_list.append(application)
            if application.form_data.hiring_manager == interviewer_obj.email or application.form_data.recruiter == interviewer_obj.email:
                # Return all applied position with status pending as the hiring manager has logged in
                applied_position_list = AppliedPosition.objects.filter(
                    company=interviewer_obj.user_company.id, application_status__in=["pending-offer", "offer", "approved", "offer-rejected"]
                ).exclude(form_data__status__in=["canceled", "closed", "draft"])
                applied_position_list = applied_position_list.filter(
                    Q(form_data__recruiter=interviewer_obj.email) | Q(form_data__hiring_manager=interviewer_obj.email)
                )
                if search:
                    applied_position_list = applied_position_list.annotate(
                        full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                        string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                    ).filter(
                        Q(full_name__icontains=search)
                        | Q(applied_profile__user__email__icontains=search)
                        | Q(form_data__form_data__job_title__icontains=search)
                        | Q(string_id__icontains=search)
                    )
                break
        applied_position_list = list(set(applied_position_list))
        context = {"pending_interviewer_ids": pending_interviewer_list, "own_id": pk}
        serializer = AppliedPositionListSerializer(applied_position_list, many=True, context=context)
        data = serializer.data
        final_data = sorted(data, key=lambda d: d["average_scorecard_rating"], reverse=True)
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
            for data in applied_position_list:
                serializer_data = AppliedPositionListSerializer(data).data
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
            is_hiring_manager = False
            if request.user.user_role.name == "hiring manager":
                is_hiring_manager = True
            return ResponseOk(
                {
                    "data": final_data,
                    "is_hiring_manager": is_hiring_manager,
                    "code": status.HTTP_200_OK,
                    "message": "Pending Offer Details fetched successfully.",
                }
            )


class GetAllOpPendingOffer(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk, format=None):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        data = request.GET
        if data.get("export"):
            export = True
        else:
            export = False
        pending_interviewer_list = []
        applied_position_list = []
        try:
            pk = int(decrypt(pk))
        except:
            pass
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
            company=interviewer_obj.user_company.id, application_status__in=["pending-offer", "offer", "approved"]
        )
        application_obj = application_obj.exclude(form_data__status__in=["canceled", "closed", "draft"])
        data = request.GET
        search = data.get("search")
        if search:
            application_obj = application_obj.annotate(
                full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
            ).filter(
                Q(full_name__icontains=search)
                | Q(applied_profile__user__email__icontains=search)
                | Q(form_data__form_data__job_title__icontains=search)
                | Q(string_id__icontains=search)
            )
        for application in application_obj:
            try:
                interviewer_ids = application.data["interview_schedule_data"]["Interviewer"]
            except:
                interviewer_ids = []
            for interviewer in interviewer_ids:
                try:
                    int_id = interviewer["profile_id"]
                except:
                    int_id = 0
                if pk == int_id:
                    score_obj = PositionScoreCard.objects.filter(
                        position=application.form_data,
                        applied_profiles=application.applied_profile.id,
                        interviewer_profile=interviewer["profile_id"],
                    )
                    if len(score_obj) == 0:
                        pending_interviewer_list.append(interviewer["profile_id"])
                        applied_position_list.append(application)
            if application.form_data.hiring_manager == interviewer_obj.email or application.form_data.recruiter == interviewer_obj.email:
                # Return all applied position with status pending as the hiring manager has logged in
                applied_position_list = AppliedPosition.objects.filter(
                    company=interviewer_obj.user_company.id, application_status__in=["pending-offer", "offer", "approved"]
                ).exclude(form_data__status__in=["canceled", "closed", "draft"])
                applied_position_list = applied_position_list.filter(
                    Q(form_data__recruiter=interviewer_obj.email) | Q(form_data__hiring_manager=interviewer_obj.email)
                )
                if search:
                    applied_position_list = applied_position_list.annotate(
                        full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                        string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                    ).filter(
                        Q(full_name__icontains=search)
                        | Q(applied_profile__user__email__icontains=search)
                        | Q(form_data__form_data__job_title__icontains=search)
                        | Q(string_id__icontains=search)
                    )
                break
        applied_position_list = list(set(applied_position_list))
        context = {"pending_interviewer_ids": pending_interviewer_list, "own_id": pk}
        if export:
            select_type = request.GET.get("select_type")
            csv_response = HttpResponse(content_type="text/csv")
            csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
            writer = csv.writer(csv_response)
            fields = ["Position No", "Position Name", "Candidate Name", "Recruiter", "Mobile No", "Email address", "Location", "Status"]
            writer.writerow(fields)
            for i in applied_position_list:
                row = []
                row.append(i.form_data.show_id)
                row.append(i.form_data.form_data["job_title"])
                try:
                    user_obj = User.objects.get(email__iexact=i.form_data.recruiter, user_company=i.form_data.company)
                    row.append(user_obj.get_full_name())
                except:
                    row.append(i.form_data.recruiter)
                row.append(i.applied_profile.phone_no)
                row.append(i.applied_profile.user.email)
                row.append(i.form_data.form_data["location"][0]["label"])
                row.append(i.application_status)
                writer.writerow(row)
            response = HttpResponse(csv_response, content_type="text/csv")
            return response
        else:
            is_hiring_manager = False
            if request.user.user_role.name == "hiring manager":
                is_hiring_manager = True
            data = []
            print(len(applied_position_list))
            for i in applied_position_list:
                temp_data = {}
                temp_data["applied_profile_id"] = i.id
                temp_data["user_applied_id"] = i.applied_profile.id
                temp_data["application_status"] = i.application_status
                temp_data["id"] = i.id
                temp_data["position_id"] = i.form_data.id
                temp_data["sposition_id"] = i.form_data.show_id
                temp_data["position_no"] = i.form_data.id
                temp_data["position_name"] = i.form_data.form_data["job_title"]
                temp_data["candidate_name"] = i.applied_profile.user.get_full_name()
                temp_data["mobile_no"] = i.applied_profile.phone_no
                temp_data["email"] = i.applied_profile.user.email
                temp_data["location"] = i.form_data.form_data["location"][0]["label"]
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
                temp_data["status"] = i.application_status
                temp_data["data"] = {}
                temp_data["data"]["current_stage_id"] = i.data.get("current_stage_id", None)
                rating = PositionScoreCard.objects.filter(position=i.form_data, applied_profiles=i.applied_profile).aggregate(Avg("rating"))[
                    "rating__avg"
                ]
                if rating:
                    temp_data["ratings"] = round(rating, 1)
                else:
                    temp_data["ratings"] = 0
                # get offer
                try:
                    offer_obj = OfferLetter.objects.filter(offered_to=i).last()
                    temp_data["offer_letter"] = {}
                    temp_data["offer_letter"]["id"] = offer_obj.id
                    temp_data["offer_letter"]["withdraw"] = offer_obj.withdraw
                except:
                    pass
                # get approvals
                try:
                    temp_data["offer_approval_details"] = []
                    for approval in OfferApproval.objects.filter(position=i.form_data).order_by("sort_order"):
                        t_data = {}
                        t_data["id"] = approval.id
                        t_data["first_name"] = approval.profile.user.first_name
                        t_data["profile_id"] = approval.profile.id
                        t_data["eprofile_id"] = encrypt(approval.profile.id)
                        t_data["is_approve"] = approval.is_approve
                        t_data["is_reject"] = approval.is_reject
                        temp_data["offer_approval_details"].append(t_data)
                except:
                    temp_data["offer_approval_details"] = []
                data.append(temp_data)
            final_data = sorted(data, key=lambda d: d["ratings"], reverse=True)
            return ResponseOk(
                {
                    "data": final_data,
                    "is_hiring_manager": is_hiring_manager,
                    "code": status.HTTP_200_OK,
                    "message": "Pending Offer Details fetched successfully.",
                }
            )


class GetAllPendingCount(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk, format=None):
        pending_interviewer_list = []
        applied_position_list = []
        try:
            pk = int(decrypt(pk))
        except:
            pass
        try:
            interviewer_obj = Profile.objects.get(id=pk).user
        except Profile.DoesNotExist:
            return ResponseBadRequest(
                {
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Please specify the correct Profile ID",
                }
            )

        application_obj = AppliedPosition.objects.filter(company=interviewer_obj.user_company.id)
        for application in application_obj:
            try:
                interviewer_ids = application.data["interview_schedule_data"]["Interviewer"]
            except:
                interviewer_ids = []

            for interviewer in interviewer_ids:
                try:
                    int_id = interviewer["profile_id"]
                except:
                    int_id = 0
                if pk == int_id:
                    pending_interviewer_list.append(interviewer["profile_id"])
                    applied_position_list.append(application)

        pending_scorecard_count = len(list(set(applied_position_list)))

        pending_interviewer_list = []
        applied_position_list = []

        application_obj = AppliedPosition.objects.filter(company=interviewer_obj.user_company.id, application_status="pending")
        for application in application_obj:
            try:
                interviewer_ids = application.data["interview_schedule_data"]["Interviewer"]
            except:
                interviewer_ids = []
            is_logged_interviewer = False
            for interviewer in interviewer_ids:
                try:
                    int_id = interviewer["profile_id"]
                except:
                    int_id = 0
                if pk == int_id:
                    pending_interviewer_list.append(interviewer["profile_id"])
                    applied_position_list.append(application)
                if not is_logged_interviewer:
                    applied_position_list.append(application)

        pending_decision_count = len(list(set(applied_position_list)))
        # get pending decision count - here 5 is hiring manager
        if interviewer_obj.user_role.name == "hiring manager":
            pending_decision_count = AppliedPosition.objects.filter(company=interviewer_obj.user_company.id, application_status="pending").count()
        pending_interviewer_list = []
        applied_position_list = []

        application_obj = AppliedPosition.objects.filter(
            company=interviewer_obj.user_company.id, application_status__in=["pending-offer", "offer", "approved"]
        )
        for application in application_obj:
            try:
                interviewer_ids = application.data["interview_schedule_data"]["Interviewer"]
            except:
                interviewer_ids = []

            for interviewer in interviewer_ids:
                try:
                    int_id = interviewer["profile_id"]
                except:
                    int_id = 0
                if pk == int_id:
                    pending_interviewer_list.append(interviewer["profile_id"])
                    applied_position_list.append(application)
        pending_offer_count = len(list(set(applied_position_list)))
        # get offer count - here 5 is hiring manager
        if interviewer_obj.user_role.name == "hiring manager":
            pending_offer_count = AppliedPosition.objects.filter(
                company=interviewer_obj.user_company.id, application_status__in=["pending-offer", "offer", "approved"]
            ).count()
        result = {
            "pending_scorecard_count": pending_scorecard_count,
            "pending_decision_count": pending_decision_count,
            "pending_offer_count": pending_offer_count,
        }

        return ResponseOk(
            {
                "data": result,
                "code": status.HTTP_200_OK,
                "message": "Count Details fetched successfully.",
            }
        )


class GetRatings(APIView):
    def get(self, request, applied_position, interviwer, candidate, format=None):
        # if request.user.user_role.name in ['candidate', 'employee']:
        #     return ResponseBadRequest({"message": 'invalid request'})
        try:
            interviwer = int(decrypt(interviwer))
        except:
            pass
        try:
            item = OverAllRatingDashboard.objects.filter(applied_position=applied_position, interviewer_id=interviwer, candidate_id=candidate).last()
            serializer = OverAllRatingDashboardSerializer(item)
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            items = OverAllRatingDashboard.objects.all()
            serializer = OverAllRatingDashboardSerializer(items, many=True)
            return Response({"status": "success", "data": serializer.data, "debug": str(e)}, status=status.HTTP_200_OK)


class GetAllRatings(APIView):
    queryset = OverAllRatingDashboard.objects.all()
    applied_position = openapi.Parameter(
        "applied_position",
        in_=openapi.IN_QUERY,
        description="applied_position",
        type=openapi.TYPE_STRING,
    )

    interviewer_profile = openapi.Parameter(
        "interviewer_profile",
        in_=openapi.IN_QUERY,
        description="interviewer_profile",
        type=openapi.TYPE_STRING,
    )

    """Decorator with parameter swagger auto schema"""

    @swagger_auto_schema(manual_parameters=[applied_position, interviewer_profile])
    @csrf_exempt
    def post(self, request):
        # if request.user.user_role.name in ['candidate', 'employee']:
        #     return ResponseBadRequest({"message": 'invalid request'})
        data = request.GET
        try:
            data["interviewer_profile"] = int(decrypt(data.get("interviewer_profile")))
        except:
            pass
        if "interviewer_profile" in data and "applied_position" in data:
            rating_obj = OverAllRatingDashboard.objects.filter(interviewer_id=data["interviewer_profile"], applied_position=data["applied_position"])
        elif "interviewer_profile" in data:
            rating_obj = OverAllRatingDashboard.objects.filter(interviewer_id=data["interviewer_profile"])

        elif "applied_position" in data:
            rating_obj = OverAllRatingDashboard.objects.filter(applied_position=data["applied_position"])

        else:
            rating_obj = OverAllRatingDashboard.objects.all()

        serializer = OverAllRatingDashboardSerializer(rating_obj, many=True)
        return Response({"data": serializer.data, "message": "Rating Dashboard Fetched Successfully", "status": 200}, status=200)


class CreateRatings(APIView):
    @swagger_auto_schema(
        operation_description="Rating Dashboard Create API",
        operation_summary="Rating Dashboard Create API",
        request_body=OverAllRatingDashboardSerializer,
    )
    def post(self, request, format=None):
        # if request.user.user_role.name in ['candidate', 'employee']:
        #     return ResponseBadRequest({"message": 'invalid request'})
        data = request.data
        try:
            data["interviewer_id"] = int(decrypt(data.get("interviewer_id")))
        except:
            pass
        serializer = OverAllRatingDashboardSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response({"data": serializer.data, "message": "OK", "status": 200}, status=200)
        else:
            return Response({"data": serializer.errors, "message": "Some Error Occured", "status": 400}, status=400)


class UpdateRatings(APIView):
    @swagger_auto_schema(
        operation_description="Rating Dashboard Update API",
        operation_summary="Rating Dashboard Update API",
        request_body=OverAllRatingDashboardSerializer,
    )
    def put(self, request, applied_position, interviwer, candidate, format=None):
        # if request.user.user_role.name in ['candidate', 'employee']:
        #     return ResponseBadRequest({"message": 'invalid request'})
        data = request.data
        try:
            data["interviewer_id"] = int(decrypt(data.get("interviewer_id")))
        except Exception as e:
            print(e)
        try:
            interviwer = int(decrypt(interviwer))
        except Exception as e:
            print(e)
        response = Response()
        try:
            todo_to_update = OverAllRatingDashboard.objects.filter(
                applied_position=applied_position, interviewer_id=interviwer, candidate_id=candidate
            ).last()
        except OverAllRatingDashboard.DoesNotExist:
            response.data = {"message": "Rating Dashboard Does not Exist", "data": None}
            return Response({"data": serializer.errors, "message": "Some Error Occured", "status": 400}, status=400)
        serializer = OverAllRatingDashboardSerializer(instance=todo_to_update, data=data, partial=True)

        serializer.is_valid(raise_exception=True)

        serializer.save()
        response.data = {"message": "Rating Dashboard Updated Successfully", "data": serializer.data}

        return Response({"data": serializer.data, "message": "OK", "status": 200}, status=200)


class DeleteRatings(APIView):
    def delete(self, request, pk, format=None):
        todo_to_delete = OverAllRatingDashboard.objects.get(pk=pk)

        todo_to_delete.delete()

        return Response({"message": "Rating Dashboard Deleted Successfully"})
