import csv
import math
import os
from enum import unique
from random import randint
import json
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.db.models import F, Q
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.urls import reverse
from django.utils.encoding import DjangoUnicodeDecodeError, smart_bytes, smart_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, permissions, serializers, status, viewsets
from rest_framework.decorators import permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from app import insertCompanyData
from app.response import ResponseBadRequest, ResponseOk
from app.util import custom_get_object, custom_get_pagination, custom_search
from app.custom_authentications import CustomAuthenticated
from company import serializers as company_serializers
from company.models import Company
from organization.models import Organization
from primary_data.models import Address, City, Country, State
from role.models import Role
from user import serializers as user_serializers
from user.models import Media, Profile, Token, User

from .models import (
    Company,
    Department,
    FeaturesEnabled,
    GPRRDocsAndPolicy,
    ServiceProviderCreds,
)
from .serializers import *
from .utils import department_dict, get_selected_fields, get_value


class GetAllCompany(APIView):
    """
    This GET function fetches all records from COMPANY model and return the data after serializing it.

    Args:
        None
    Body:
        None
    Returns:
        -Serialized COMPANY model data(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            company = Company.objects.all()
            serializer = CompanySerializer(company, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "All companies",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "company Does Not Exist",
                }
            )


class GetCompany(APIView):
    """
    This GET function fetches particular ID record from COMPANY model and return the data after serializing it.

    Args:
        pk(company_id)
    Body:
        None
    Returns:
        -Serialized COMPANY model data of particular ID(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, pk):
        try:
            company = custom_get_object(pk, Company)
            serializer = CompanySerializer(company)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get company successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "company Does Not Exist",
                }
            )


class GetCompanyByDomain(APIView):

    """
    This GET function fetches particular record by domain from COMPANY model and return the data after serializing it.

    Args:
        domain(company_domain)
    Body:
        None
    Returns:
        -Serialized COMPANY model data of particular record by domain(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        None
    Raises:
        None
    """

    permission_classes = []
    authentication_classes = []

    def get(self, request, domain):
        try:
            try:
                data = cache.get(request.get_full_path())
            except:
                data = None
            if data:
                return ResponseOk(
                    {
                        "data": data.get("data"),
                        "code": status.HTTP_200_OK,
                        "message": "get company successfully",
                    }
                )
            company = custom_get_object(domain, Company, "url_domain")
            serializer = CompanySerializer(company)
            resp = {
                "data": serializer.data,
                "code": status.HTTP_200_OK,
                "message": "get company successfully",
            }
            cache.set(request.get_full_path(), resp)
            return ResponseOk(resp)
        except Exception as e:
            return ResponseBadRequest({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": "company Does Not Exist", "error": str(e)})


class CreateCompany(APIView):

    """
    This POST function creates a COMPANY model records from the data passes in the body.

    Args:
       None
    Body:
        COMPANY model fields
    Returns:
        -serializer.data(HTTP_200_OK)
        -serializer.errors
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="company Create API",
        operation_summary="company Create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "company_name": openapi.Schema(type=openapi.TYPE_STRING),
                "url_domain": openapi.Schema(type=openapi.TYPE_STRING),
                "company_host": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        serializer = CompanySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()

            insertCompanyData.save_master_data(serializer.data["id"])
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Company created successfully",
                }
            )
        else:
            return Response(serializer.errors)


class UpdateCompany(APIView):
    """
    This PUT function updates particular record by ID from COMPANY model according to the company_id passed in url.

    Args:
        pk(company_id)
    Body:
        None
    Returns:
        -Serialized COMPANY model data of particular record by ID(HTTP_200_OK)
        -serializer.errors
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Update Company API",
        operation_summary="Update Company API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "company_name": openapi.Schema(type=openapi.TYPE_STRING),
                "url_domain": openapi.Schema(type=openapi.TYPE_STRING),
                "company_host": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def put(self, request, pk):
        try:
            company = custom_get_object(pk, Company)
            serializer = CompanySerializer(company, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "company updated successfully",
                    }
                )
            else:
                return Response(serializer.errors)
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "company Does Not Exist",
                }
            )


class DeleteCompany(APIView):
    """
    This DETETE function delete particular record by ID from COMPANY model according to the company_id passed in url.

    Args:
        pk(company_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if company_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, pk):
        try:
            company = custom_get_object(pk, Company)
            company.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Company deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "company Does Not Exist",
                }
            )


class GetAllDepartment(APIView):
    """
    This GET function fetches all records from DEPARTMENT model with pagination, searching and sorting, and return the data after serializing it.

    Args:
        None
    Body:
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

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
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
        try:
            data = request.GET
            if data.get("export"):
                export = True
            else:
                export = False
            department = Department.objects.filter(company=request.user.user_company)
            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                selected_fields = get_selected_fields(select_type, request.user.profile)
                writer.writerow(selected_fields)
                for data in department:
                    serializer_data = DepartmentSerializer(data).data
                    row = []
                    for field in selected_fields:
                        field = department_dict.get(field)
                        value = get_value(serializer_data, field)
                        try:
                            row.append(next(value, None))
                        except:
                            row.append(value)
                    writer.writerow(row)
                response = HttpResponse(csv_response, content_type="text/csv")
                return response
            else:
                search_keys = ["department_name__icontains"]
                data = custom_get_pagination(request, department, Department, DepartmentSerializer, search_keys)
                return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpDepartment(APIView):
    """
    This GET function fetches all records from DEPARTMENT model with pagination, searching and sorting, and return the data after serializing it.

    Args:
        None
    Body:
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

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
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

    @swagger_auto_schema(
        manual_parameters=[
            search,
            page,
            perpage,
        ]
    )
    def get(self, request):
        try:
            data = request.GET
            if data.get("export"):
                export = True
            else:
                export = False
            department = Department.objects.filter(company=request.user.user_company)
            if export:
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                fields = ["ID", "Department Name", "Description", "Created at"]
                writer.writerow(fields)
                for i in department:
                    row = []
                    row.append(i.id)
                    row.append(i.department_name)
                    row.append(i.description)
                    row.append(str(i.created_at))
                    writer.writerow(row)
                response = HttpResponse(csv_response, content_type="text/csv")
                return response
            else:
                search_keys = ["department_name__icontains"]
                data, meta = custom_search(request, department, search_keys)
                resp_data = []
                for i in data:
                    temp_data = {}
                    temp_data["id"] = i.id
                    temp_data["department_name"] = i.department_name
                    temp_data["description"] = i.description
                    temp_data["created_at"] = str(i.created_at)
                    resp_data.append(temp_data)
                return ResponseOk(
                    {
                        "data": resp_data,
                        "message": "departments fetched",
                        "meta": meta,
                    }
                )
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateDepartment(APIView):
    """
    This POST function creates a DEPARTMENT model records from the data passes in the body.

    Args:
       None
    Body:
        DEPARTMENT model fields
    Returns:
        -serializer.data(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Department Create API",
        operation_summary="Department Create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "department_name": openapi.Schema(type=openapi.TYPE_STRING),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        serializer = DepartmentSerializer(
            data=request.data,
        )
        if serializer.is_valid():
            obj = serializer.save()
            obj.company = request.user.user_company
            obj.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Department created successfully",
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


class GetDepartment(APIView):
    """
    This GET function fetches particular ID record from DEPARTMENT model and return the data after serializing it.

    Args:
        pk(department_id)
    Body:
        None
    Returns:
        -Serialized DEPARTMENT model data of particular ID(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Get Department API",
        operation_summary="Get Department API",
    )
    def get(self, request, pk):
        try:
            department = custom_get_object(pk, Department)
            serializer = DepartmentSerializer(department)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Get Department successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Department Does Not Exist",
                }
            )


class UpdateDepartment(APIView):
    """
    This PUT function updates particular record by ID from DEPARTMENT model according to the department_id passed in url.

    Args:
        pk(department_id)
    Body:
        None
    Returns:
        -Serialized DEPARTMENT model data of particular record by ID(HTTP_200_OK)
        -serializer.errors
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Update Department API",
        operation_summary="Update Department API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "department_name": openapi.Schema(type=openapi.TYPE_STRING),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def put(self, request, pk):
        try:
            department = custom_get_object(pk, Department)
            serializer = DepartmentSerializer(department, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Department updated successfully",
                    }
                )
            else:
                return Response(serializer.errors)
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Department Does Not Exist",
                }
            )


class DeleteDepartment(APIView):
    """
    This DETETE function delete particular record by ID from DEPARTMENT model according to the department_id passed in url.

    Args:
        pk(department_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if department_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, pk):
        try:
            department = custom_get_object(pk, Department)
            department.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Department deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Department Does Not Exist",
                }
            )


class DepartmentCSVExport(APIView):
    """
    This GET function fetches all the data from department model and converts it into CSV file.

    Args:
        pk(department_id)
    Body:
        None
    Returns:
        -HttpResponse
    Authentication:
        None
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, department_id):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="export.csv"'

        all_fields = Department.objects.filter(department_name=department_id)
        serializer = company_serializers.DepartmentCsvSerializer(all_fields, many=True)

        header = company_serializers.DepartmentCsvSerializer.Meta.fields

        writer = csv.DictWriter(response, fieldnames=header)

        writer.writeheader()
        for row in serializer.data:
            writer.writerow(row)

        return response


class RequestDemoSignup(APIView):
    """
    This APIs does the required things to perform a Demo.
    It created a User and assigns him a company. Along with this, it also generated the required fields and relevant stages in db.
    It also sends a mail to respective support teams about the requested team.
    """

    @swagger_auto_schema(
        operation_summary="Company and User Signup API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "domain_name": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
                "phone_no": openapi.Schema(type=openapi.TYPE_STRING),
                "company_name": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        try:
            data = request.data.copy()
            data["url_domain"] = data.get("domain_name").lower()
            data["is_active"] = False
            try:
                user_obj = User.objects.get(email=data.get("email"))
                return ResponseBadRequest(
                    {
                        "data": {"email": ["Email address already exists. Please use another email."]},
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Email address already exists. Please use another email.",
                    }
                )
            except:
                pass
            # uncomment later
            # if any([x in data.get("email") for x in ["gmail", "yopmail", "outlook", "yahoo"]]):
            #     return ResponseBadRequest(
            #         {
            #             "data": {"email": ["Please your business email."]},
            #             "code": status.HTTP_400_BAD_REQUEST,
            #             "message": "Please your business email.",
            #         }
            #     )
            serializer = CompanySerializer(data=data)
            if serializer.is_valid():
                company_obj = serializer.save()

                try:
                    role = Role.objects.get(name="admin", company=company_obj)
                    username = str(data.get("email")) + "_" + str(data.get("domain_name"))
                    user_obj = User.objects.create(
                        username=username.lower(),
                        email=data.get("email").lower(),
                        first_name=data.get("name"),
                        user_company=company_obj,
                        user_role=role,
                    )
                    user_obj.set_password(data.get("password"))
                    user_obj.save()
                    profile_obj = Profile.objects.create(user=user_obj, phone_no=data.get("phone_no"))
                    # Add addressof the company
                    try:
                        country = json.loads(request.data.get("country", [{}]))
                        city = json.loads(request.data.get("city", {}))
                        country_obj = Country.objects.filter(name__iexact=country[0].get("label", None)).last()
                        city_obj = City.objects.filter(country=country_obj, name__iexact=city.get("label", None)).last()
                        address_obj = Address.objects.create(country=country_obj, state=None, city=city_obj)
                        address_obj.save()
                        profile_obj.address = address_obj
                        profile_obj.save()
                    except Exception as e:
                        print("Error assigning country to user. Errorr is: ", e)
                    company_obj.company_owner = user_obj
                    company_obj.save()
                except Exception as e:
                    company_obj.delete()
                    return ResponseBadRequest(
                        {
                            "data": str(e),
                            "code": status.HTTP_400_BAD_REQUEST,
                            "message": "Uable to create Company! Try again.",
                        }
                    )
                # Create Organization
                Organization.objects.create(
                    organization_name=request.data.get("company_name"),
                    company=company_obj,
                    phone_no=request.data.get("phone_no"),
                    email=request.data.get("email"),
                    country=request.data.get("country"),
                    city=request.data.get("city"),
                    primary_contact_1=request.data.get("phone_no"),
                )
                # Send confirmation mail to the the user
                to_email = None
                if company_obj.company_owner:
                    first_name = company_obj.company_owner.first_name
                    to_email = company_obj.company_owner.email
                else:
                    first_name = " "
                    to_email = "sample@mail.com"
                print(to_email)
                context = {
                    "first_name": first_name,
                    "company_name": company_obj.company_name,
                    "support_email": "sayhalo@infertalents.com",
                    "link": "https://{}.{}".format(company_obj.url_domain, settings.DOMAIN_NAME),
                }
                from_email = settings.EMAIL_HOST_USER
                body_msg = render_to_string("request-demo-confirmation.html", context)
                msg = EmailMultiAlternatives("Demo Confirmation<Don't Reply>", body_msg, from_email, [to_email])
                msg.content_subtype = "html"
                msg.send()

                # Send mail to support team
                context = {"first_name": "Support at Infertalent", "company_name": data.get("company_name"), "user_email": data.get("email")}
                from_email = settings.EMAIL_HOST_USER
                to_email = "sayhalo@infertalents.com"  # Support email hardcoded for now
                body_msg = render_to_string("request-demo-support.html", context)
                msg = EmailMultiAlternatives("Demo Confirmation<Don't Reply>", body_msg, from_email, [to_email])
                msg.content_subtype = "html"
                msg.send()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Company created successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Company not created",
                    }
                )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Company not created",
                }
            )


class GDPRDocsView(APIView):
    """
    This API is for adding, updating and removing the GDPR documents mainly voluntary disclosure documents
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Create GDPR Docs/Content API",
        manual_parameters=[],
        request_body=GPRRDocsAndPolicySerializer,
    )
    def post(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            serializer = GPRRDocsAndPolicySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "docs created successfully",
                    }
                )
            else:
                return ResponseBadRequest({"message": "error occured", "error": serializer.errors, "data": None})
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "error occured",
                }
            )

    @swagger_auto_schema(
        operation_summary="Update GDPR Docs/Content API",
        operation_description="API for updating GDPR Docs",
        manual_parameters=[],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    title="id",
                ),
                "topic": openapi.Schema(type=openapi.TYPE_STRING, title="Topic", **{"minLength": 1}),
                "option_type": openapi.Schema(type=openapi.TYPE_STRING, title="Option Type", **{"maxLenght": 250, "minLength": 1}),
                "options": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), title="Option type"),
                "content": openapi.Schema(type=openapi.TYPE_STRING, title="Content of Doc"),
                "company": openapi.Schema(type=openapi.TYPE_INTEGER, title="Company"),
            },
            required=["id", "topic", "content", "company"],
        ),
    )
    def put(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            obj = GPRRDocsAndPolicy.objects.get(id=request.data.get("id"))
            serializer = GPRRDocsAndPolicySerializer(obj, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "docs updated successfully",
                    }
                )
            else:
                return ResponseBadRequest({"message": "error occured", "error": serializer.errors, "data": None})
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "error occured",
                }
            )

    @swagger_auto_schema(
        operation_summary="Get GDPR Docs/Contents API",
        operation_description="API for getting GDPR Docs",
        manual_parameters=[],
    )
    def get(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            objs = GPRRDocsAndPolicy.objects.filter(company=company)
            serializer = GPRRDocsAndPolicySerializer(objs, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "docs fetched successfully",
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


class FeaturesEnalbled(APIView):
    """
    API used to add calendly details i.e Personal Access Token.
    Args:
        feature - name of feature to get like calendly, docusign
    Body:
        None
    Returns:
        -success message with enabled as True/False(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Get if a feature is enabled API",
        operation_summary="Get if a feature is enabled API",
        manual_parameters=[
            openapi.Parameter(
                "feature",
                in_=openapi.IN_QUERY,
                description="feature",
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request):
        try:
            data = request.GET
            obj = FeaturesEnabled.objects.filter(company=request.user.user_company, feature=data.get("feature")).last()
            if obj:
                if obj.enabled:
                    data = {"enabled": True}
                else:
                    data = {"enabled": False}
            else:
                data = {"enabled": False}
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "feature fetched successfully",
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
        operation_description="Enable a feature API",
        operation_summary="Enable a feature API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "feature": openapi.Schema(type=openapi.TYPE_STRING),
                "enabled": openapi.Schema(type=openapi.TYPE_STRING),
            },
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
            obj, created = FeaturesEnabled.objects.get_or_create(company=request.user.user_company, feature=data.get("feature"))
            obj.enabled = True
            obj.save()
            data = {"enabled": True}
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "feature created successfully",
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
        operation_description="Disable a feature API",
        operation_summary="Disable a feature API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "feature": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def delete(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            obj = FeaturesEnabled.objects.filter(company=request.user.user_company, feature=data.get("feature")).last()
            obj.enabled = False
            obj.save()

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


class GetNoOfEmpList(APIView):

    """
    This API return a list of no of employee select fields which needs to be used on FE
    Args:
        feature - name of feature to get like calendly, docusign
    Body:
        None
    Returns:
        -success message with list of select fields(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    @swagger_auto_schema(
        operation_description="Returns a list of no of employees select fields",
        operation_summary="Returns a list of no of employees select fields",
        manual_parameters=[
            openapi.Parameter(
                "feature",
                in_=openapi.IN_QUERY,
                description="feature",
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request):
        try:
            options = ["0-100", "101-200", "201-300", "301-500", "501-1000", "1001-2000", "2001-5000", "5001-10000", "10000-20000", "20000+"]
            return ResponseOk(
                {
                    "data": {"options": options},
                    "code": status.HTTP_200_OK,
                    "message": "options fetched successfully",
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


class FromEmailView(APIView):
    """
    API used to add from email creds used for sending various email.
    Args:
        None
    Body:
        None
    Returns:
        -success message with enabled as True/False(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            data = request.data
            creds, created = ServiceProviderCreds.objects.get_or_create(company=request.user.user_company)
            creds.from_email = data
            creds.save()

            return ResponseOk(
                {
                    "data": "None",
                    "code": status.HTTP_200_OK,
                    "message": "creds added",
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

    # def get(self, request):
    #     try:
    #         data = request.data
    #         creds, created = ServiceProviderCreds.objects.get_or_create(company=request.user.user_company)

    #         creds.save()
    #         return ResponseOk(
    #             {
    #                 "data": "None",
    #                 "code": status.HTTP_200_OK,
    #                 "message": "creds added",
    #             }
    #         )
    #     except Exception as e:
    #         return ResponseBadRequest(
    #             {
    #                 "data": str(e),
    #                 "code": status.HTTP_400_BAD_REQUEST,
    #                 "message": "error occured",
    #             }
    #         )


class AddTNC(APIView):
    permission_classes = [CustomAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            company.tnc = request.data.get("tnc")
            company.save()
            return ResponseOk(
                {
                    "data": "None",
                    "code": status.HTTP_200_OK,
                    "message": "TNC added",
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

    def get(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            tnc = company.tnc
            response = {"tnc": tnc}
            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "TNC fetched",
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


class AddPolicy(APIView):
    permission_classes = [CustomAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            company.policy = request.data.get("policy")
            company.save()
            return ResponseOk(
                {
                    "data": "None",
                    "code": status.HTTP_200_OK,
                    "message": "policy added",
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

    def get(self, request):
        try:
            data = request.GET
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
                company = Company.objects.get(url_domain=url_domain)
            else:
                raise serializers.ValidationError("domain field required")
            policy = company.policy
            response = {"policy": policy}
            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "policy fetched",
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
