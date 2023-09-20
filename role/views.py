import math
from urllib import request
from django.http.response import HttpResponse
from functools import reduce
import pandas as pd
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
import operator
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, permissions, serializers, status
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication
import csv
from app.CSVWriter import CSVWriter
from app.response import ResponseBadRequest, ResponseNotFound, ResponseOk
from app.util import (
    custom_get_object,
    custom_get_pagination,
    custom_search,
    generate_file_name,
)
from company.models import FeaturesEnabled
from form.models import UserSelectedField
from role.models import Access, Permission, Role, RoleList, RolePermission
from role.permissions import CUDModelPermissions, IsEmployeeUser
from role.serializers import (
    AccessSerializer,
    PermissionSerializer,
    RoleCreateUpdateSerializer,
    RoleListSerializer,
    RolePermissionSerializer,
    RoleSerializer,
)


# Create your views here.
class GetAllRole(APIView):
    """
    This GET function fetches all records from Role model
    after filtering on the basis of fields given in the body
    and return the data after serializing it.

    Args:
        None
    Body:
        - domain (mandatory)
        - page (optional)
        - perpage (optional)
        - search (optional)
        - role (optional)
    Returns:
        - Serialized Role model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        - serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]

    authentication_classes = [authentication.JWTAuthentication]
    queryset = Role.objects.all()
    page = openapi.Parameter(
        "page",
        in_=openapi.IN_QUERY,
        description="page",
        type=openapi.TYPE_STRING,
    )
    """parameter for pages"""
    perpage = openapi.Parameter(
        "perpage",
        in_=openapi.IN_QUERY,
        description="perpage",
        type=openapi.TYPE_STRING,
    )
    """Search bar"""
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by role_name on the basis of domain",
        type=openapi.TYPE_STRING,
    )
    role = openapi.Parameter(
        "role",
        in_=openapi.IN_QUERY,
        description="search by role_id on the basis of domain",
        type=openapi.TYPE_STRING,
    )

    """Decorator with parameter swagger auto schema"""

    @swagger_auto_schema(manual_parameters=[search, role, page, perpage])
    def get(self, request):
        data = request.GET
        try:
            if str(request.user) == "AnonymousUser" or request.user is None:
                role_obj = Role.objects.filter(Q(company=None)).exclude(slug__in=["superuser"])
            else:
                role_obj = Role.objects.filter(Q(company=request.user.user_company) | Q(company=None)).exclude(slug__in=["superuser"])
            if FeaturesEnabled.objects.filter(feature="recruiter", enabled=False, company__url_domain=request.headers.get("domain")):
                role_obj = role_obj.exclude(name="recruiter")
            role = data.get("role")
            if role is not None:
                role_obj = role_obj.filter(id=role)
            search_keys = ["name__icontains"]
            if data.get("export"):
                export = True
            else:
                export = False
            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                if selected_fields:
                    selected_fields = selected_fields.last().selected_fields
                else:
                    selected_fields = ["Role", "Access"]
                writer.writerow(selected_fields)
                for data in role_obj:
                    row = []
                    for field in selected_fields:
                        if field == "Role":
                            row.append(data.name.title())
                        else:
                            row.append(", ".join(x.access.action_name for x in data.permission_role.all()))
                    writer.writerow(row)
                response = HttpResponse(csv_response, content_type="text/csv")
                return response
            else:
                data = custom_get_pagination(request, role_obj, Role, RoleSerializer, search_keys)
                return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpRole(APIView):
    """
    This GET function fetches all records from Role model
    after filtering on the basis of fields given in the body
    and return the data after serializing it.

    Args:
        None
    Body:
        - domain (mandatory)
        - page (optional)
        - perpage (optional)
        - search (optional)
        - role (optional)
    Returns:
        - Serialized Role model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        - serializers.ValidationError("domain field required")
    """

    permission_classes = [permissions.IsAuthenticated]

    authentication_classes = [authentication.JWTAuthentication]
    queryset = Role.objects.all()
    page = openapi.Parameter(
        "page",
        in_=openapi.IN_QUERY,
        description="page",
        type=openapi.TYPE_STRING,
    )
    """parameter for pages"""
    perpage = openapi.Parameter(
        "perpage",
        in_=openapi.IN_QUERY,
        description="perpage",
        type=openapi.TYPE_STRING,
    )
    """Search bar"""
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by role_name on the basis of domain",
        type=openapi.TYPE_STRING,
    )
    role = openapi.Parameter(
        "role",
        in_=openapi.IN_QUERY,
        description="search by role_id on the basis of domain",
        type=openapi.TYPE_STRING,
    )

    """Decorator with parameter swagger auto schema"""

    @swagger_auto_schema(manual_parameters=[search, role, page, perpage])
    def get(self, request):
        data = request.GET
        try:
            if str(request.user) == "AnonymousUser" or request.user is None:
                role_obj = Role.objects.filter(Q(company=None)).exclude(slug__in=["superuser"])
            else:
                role_obj = Role.objects.filter(Q(company=request.user.user_company) | Q(company=None)).exclude(slug__in=["superuser"])
            if FeaturesEnabled.objects.filter(feature="recruiter", enabled=False, company__url_domain=request.headers.get("domain")):
                role_obj = role_obj.exclude(name="recruiter")
            role = data.get("role")
            if role is not None:
                role_obj = role_obj.filter(id=role)
            search_keys = ["name__icontains"]
            if data.get("export"):
                export = True
            else:
                export = False
            if data.get("id"):
                role_obj = role_obj.filter(id=int(data.get("id")))
            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                if selected_fields:
                    selected_fields = selected_fields.last().selected_fields
                else:
                    selected_fields = ["Role", "Access"]
                writer.writerow(selected_fields)
                for data in role_obj:
                    row = []
                    for field in selected_fields:
                        if field == "Role":
                            row.append(data.name.title())
                        else:
                            row.append(", ".join(x.access.action_name for x in data.permission_role.all()))
                    writer.writerow(row)
                response = HttpResponse(csv_response, content_type="text/csv")
                return response
            else:
                role_obj, meta = custom_search(request, role_obj, search_keys)
                data = []
                for i in role_obj:
                    temp_data = {}
                    temp_data["id"] = i.id
                    temp_data["name"] = i.name
                    temp_data["permission_role"] = []
                    for rp in i.permission_role.all():
                        permission = {}
                        access = {}
                        access["id"] = rp.access.id
                        access["access"] = rp.access.action_name
                        permission["access"] = access
                        permission["read"] = rp.read
                        permission["create"] = rp.create
                        permission["update"] = rp.update
                        permission["delete"] = rp.delete
                        temp_data["permission_role"].append(permission)
                    data.append(temp_data)
                return ResponseOk(
                    {
                        "data": data,
                        "message": "roles fetched",
                        "meta": meta,
                    }
                )
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllDummyRole(APIView):
    """
    This GET function fetches all records from Role model
    after filtering on the basis of fields given in the body
    and return the data after serializing it.

    Args:
        None
    Body:
        - domain (mandatory)
        - page (optional)
        - perpage (optional)
        - search (optional)
        - role (optional)
    Returns:
        - Serialized Role model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        - serializers.ValidationError("domain field required")
    """

    # permission_classes = [permissions.AllowAny]

    # authentication_classes = [authentication.JWTAuthentication]
    queryset = Role.objects.all()
    page = openapi.Parameter(
        "page",
        in_=openapi.IN_QUERY,
        description="page",
        type=openapi.TYPE_STRING,
    )
    """parameter for pages"""
    perpage = openapi.Parameter(
        "perpage",
        in_=openapi.IN_QUERY,
        description="perpage",
        type=openapi.TYPE_STRING,
    )
    """Search bar"""
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by role_name on the basis of domain",
        type=openapi.TYPE_STRING,
    )
    role = openapi.Parameter(
        "role",
        in_=openapi.IN_QUERY,
        description="search by role_id on the basis of domain",
        type=openapi.TYPE_STRING,
    )

    """Decorator with parameter swagger auto schema"""

    @swagger_auto_schema(manual_parameters=[search, role, page, perpage])
    def get(self, request):
        data = request.GET
        try:
            if str(request.user) == "AnonymousUser" or request.user is None:
                role_obj = Role.objects.filter(Q(company=None)).exclude(slug__in=["superuser"])
            else:
                role_obj = Role.objects.filter(Q(company=request.user.user_company) | Q(company=None)).exclude(slug__in=["superuser"])
            role = data.get("role")
            if role is not None:
                role_obj = role_obj.filter(id=role)
            search_keys = ["name__icontains"]
            data = custom_get_pagination(request, role_obj, Role, RoleSerializer, search_keys)
            return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateRole(APIView):
    """
    This POST function creates a Role record from the data
    passed in the body.

    Args:
        None
    Body:
        Role Model Fields
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
        operation_description="Role Create API",
        operation_summary="Role Create API",
        request_body=RoleCreateUpdateSerializer,
    )
    def post(self, request):
        serializer = RoleCreateUpdateSerializer(
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "role created successfully",
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


class GetRole(APIView):
    """
    This GET function fetches particular Role instance by ID,
    and return it after serializing it.

    Args:
        pk(role_id)
    Body:
        None
    Returns:
        - Serialized Role model data (HTTP_200_OK)
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
            role = custom_get_object(pk, Role)
            serializer = RoleSerializer(role)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get role successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Role Does Not Exist",
                }
            )


class DeleteRole(APIView):
    """
    This DELETE function Deletes a Role record according to the
    role_id passed in url.

    Args:
        pk(role_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) role_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            role = custom_get_object(pk, Role)
            role.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Role deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Role Does Not Exist",
                }
            )


class UpdateRole(APIView):
    """
    This PUT function updates a Role model record according to
    the role_id passed in url.

    Args:
        pk(role_id)
    Body:
        Role model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) role_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Role Update API",
        operation_summary="Role Update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "permissions": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description="enter permission id example ['1','2']",
                ),
            },
        ),
    )
    def put(self, request, pk):
        try:
            role = custom_get_object(pk, Role)
            serializer = RoleCreateUpdateSerializer(role, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "role updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Role Does Not Exist",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Role Does Not Exist",
                }
            )


class GetAllPermissionViews(APIView):
    """
    This GET function fetches all records from Permission model
    and return the data after serializing it.

    Args:
        None
    Body:
        None
    Returns:
        - Serialized Permission model data (HTTP_200_OK)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [
        permissions.AllowAny,
    ]

    def get(self, request, format=None):
        """
        Get All Permissions
        """

        permissions = Permission.objects.all()

        serializer = PermissionSerializer(permissions, many=True)
        return ResponseOk(
            {
                "data": serializer.data,
                "code": status.HTTP_200_OK,
                "message": "Permission Fetched Successfully",
            }
        )


# Access Crud API's
class GetAllAccess(APIView):
    """
    This GET function fetches all records from Access model
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
        - Serialized Access model data (HTTP_200_OK)
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
        description="search access by name",
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
        try:
            access_data = Access.objects.all()
            search_keys = ["action_name__icontains"]
            data = custom_get_pagination(request, access_data, Access, AccessSerializer, search_keys)
            return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAccess(APIView):
    """
    This GET function fetches particular Access instance by ID,
    and return it after serializing it.

    Args:
        pk(access_id)
    Body:
        None
    Returns:
        - Serialized Access model data (HTTP_200_OK)
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
            access_queryset = custom_get_object(pk, Access)
            serializer = AccessSerializer(access_queryset)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get access successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " access Not Exist",
                }
            )


class CreateAccess(APIView):
    """
    This POST function creates a Access record from
    the data passed in the body.

    Args:
        None
    Body:
        All Access Model Fields
    Returns:
        - Serialized Access Model data (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Access create API",
        operation_summary="Access create API",
        request_body=AccessSerializer,
    )
    def post(self, request):
        serializer = AccessSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Access created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Access is not valid",
                }
            )


class UpdateAccess(APIView):
    """
    This PUT function updates a Access record according
    to the access_id passed in url.

    Args:
        pk(access_id)
    Body:
        Access Model Fields(to be updated)
    Returns:
        - Serialized Access Model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) access_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Access update API",
        operation_summary="Access update API",
        request_body=AccessSerializer,
    )
    def put(self, request, pk):
        try:
            queryset = custom_get_object(pk, Access)
            serializer = AccessSerializer(queryset, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Access updated successfully",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Access Does Not Exist",
                }
            )


class DeleteAccess(APIView):
    """
    This DELETE function Deletes a Access record
    according to the access_id passed in url.

    Args:
        pk(access_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) access_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            queryset = custom_get_object(pk, Access)
            queryset.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Access deleted successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Access Does Not Exist",
                }
            )


# Permission Crud API's
class GetAllRolePermission(APIView):
    """
    This GET function fetches all records from Role Permission model
    after filtering on the basis of given fields in body,
    and return the data after serializing it.

    Args:
        None
    Body:
        - page (optional)
        - perpage (optional)
        - role (optional)
        - sort_field (optional)
        - sort_dir (optional)
    Returns:
        - Serialized Role Permission model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    role = openapi.Parameter(
        "role",
        in_=openapi.IN_QUERY,
        description="filter user permission by role",
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

    @swagger_auto_schema(manual_parameters=[role, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET
        role = data.get("role")
        try:
            user_permission_queryset = RolePermission.objects.all()
            if role is not None:
                user_permission_queryset = user_permission_queryset.filter(Q(role=role))
            search_key = []
            data = custom_get_pagination(request, user_permission_queryset, RolePermission, RolePermissionSerializer, search_key)
            return ResponseOk(data)

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetRolePermission(APIView):
    """
    This GET function fetches particular Role Permission model instance by ID,
    and return it after serializing it.

    Args:
        pk(role_permission_id)
    Body:
        None
    Returns:
        - Serialized Role Permission data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Role Permission Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            user_permission_queryset = custom_get_object(pk, RolePermission)
            serializer = RolePermissionSerializer(user_permission_queryset)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get user permission successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " user permission Not Exist",
                }
            )


class CreateRolePermission(APIView):
    """
    This POST function creates a Role Permission Model record from
    the data passed in the body.

    Args:
        None
    Body:
        Role Permission model Fields
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
        operation_description="User Permission create API",
        operation_summary="User Permission create API",
        request_body=RolePermissionSerializer,
    )
    def post(self, request):
        serializer = RolePermissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "User Permission created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "User Permission is not valid",
                }
            )


class UpdateRolePermission(APIView):
    """
    This PUT function updates a Role Permission Model record according to
    the role_permission_id passed in url.

    Args:
        pk(role_permission_id)
    Body:
        Role Permission Model Fields(to be updated)
    Returns:
        - Serialized Role Permission Model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Role Permission does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Role Permission update API",
        operation_summary="Role Permission update API",
        request_body=RolePermissionSerializer,
    )
    def put(self, request, pk):
        try:
            queryset = custom_get_object(pk, RolePermission)
            serializer = RolePermissionSerializer(queryset, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Role Permission updated successfully",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Role Permission Does Not Exist",
                }
            )


class DeleteRolePermission(APIView):
    """
    This DELETE function Deletes a Role Permission Model record according
    to the field_id passed in url.

    Args:
        pk(role_permission_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Role Permission does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.AllowAny]
    # authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            queryset = custom_get_object(pk, RolePermission)
            queryset.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "RolePermission deleted successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "RolePermission Does Not Exist",
                }
            )


class GetAllRoleList(APIView):
    """
    This GET function fetches all records from Role List model
    and return the data after serializing it.

    Args:
        None
    Body:
        - page(option)
        - perpage(option)
        - search(option)
    Returns:
        - Serialized Role List model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) Role List Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.AllowAny]
    # authentication_classes = [authentication.JWTAuthentication]
    page = openapi.Parameter(
        "page",
        in_=openapi.IN_QUERY,
        description="page",
        type=openapi.TYPE_STRING,
    )
    """parameter for pages"""
    perpage = openapi.Parameter(
        "perpage",
        in_=openapi.IN_QUERY,
        description="perpage",
        type=openapi.TYPE_STRING,
    )
    """Search bar"""
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search by role_name on the basis of domain",
        type=openapi.TYPE_STRING,
    )

    """Decorator with parameter swagger auto schema"""

    @swagger_auto_schema(manual_parameters=[search, page, perpage])
    def get(self, request):
        try:
            queryset = RoleList.objects.all()
            disabled_features = FeaturesEnabled.objects.filter(company__id=1, enabled=False).values_list("feature", flat=True)
            if disabled_features:
                query = reduce(operator.or_, (Q(role_name__iexact=x) for x in disabled_features))
                queryset = queryset.exclude(query)
            search_key = ["role_name__icontains"]
            data = custom_get_pagination(request, queryset, RoleList, RoleListSerializer, search_key)
            return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class RoleCSVExport(APIView):
    """
    This Get function filter a Roles on the basis
    of company_id and write a CSV from the filtered data and returs a CSV file.

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
        queryset = Role.objects.filter(Q(company=company_id) | Q(company=None)).exclude(slug__in=["candidate", "superuser"])

        queryset_df = pd.DataFrame(
            queryset.values(
                "id",
                "name",
                "company__company_name",
                "permission_role__access__action_name",
                "permission_role__read",
                "permission_role__create",
                "permission_role__update",
                "permission_role__delete",
            )
        )

        writer = CSVWriter(queryset_df)
        response = writer.convert_to_csv(filename=generate_file_name("Employee", "csv"))
        return response


class UpdateRoleAndAccess(APIView):
    """
    This PUT function updates a Role model record according to
    the role_id passed in url.

    Args:
        pk(role_id)
    Body:
        Role model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) role_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Role Update API",
        operation_summary="Role Update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "permissions": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description="enter permission id example ['1','2']",
                ),
            },
        ),
    )
    def put(self, request, pk):
        try:
            role = custom_get_object(pk, Role)
            permission_roles = role.permission_role.all().values_list("id", flat=True)
            serializer = RoleCreateUpdateSerializer(role, data=request.data, partial=True)
            access = request.data.get("access_ids")
            access_ids = [i["id"] for i in access]
            msg = "role updated successfully"
            # access = list(set(access) - set(permission_roles))
            if serializer.is_valid():
                obj = serializer.save()
                for role_permission in RolePermission.objects.filter(role=obj):
                    if role_permission.access.id in access_ids:
                        try:
                            permissions_list = access[access_ids.index(role_permission.access.id)].get("permissions", [])
                            print(permissions_list[0], permissions_list[1], permissions_list[2], permissions_list[3])
                            role_permission.read = permissions_list[0]
                            role_permission.create = permissions_list[1]
                            role_permission.update = permissions_list[2]
                            role_permission.delete = permissions_list[3]
                            print(role_permission.__dict__)
                            role_permission.save()
                        except Exception as e:
                            msg = str(e)
                    else:
                        RolePermission.objects.filter(id=role_permission.id).delete()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": msg,
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Role Does Not Exist",
                    }
                )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Role Does Not Exist",
                }
            )
