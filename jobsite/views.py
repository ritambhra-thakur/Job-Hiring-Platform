import csv

# Create your views here.
import math

import pandas as pd
from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, permissions, serializers, status
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication

from app.CSVWriter import CSVWriter
from app.response import ResponseBadRequest, ResponseNotFound, ResponseOk
from app.util import custom_get_object, custom_get_pagination, custom_search
from jobsite.models import JobSites

from .serializers import JobSitesSerializer


# Create your views here.
class GetAllJobSites(APIView):
    """
    This GET function fetches all records from JobSites model
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
        - Serialized Jobsite model data (HTTP_200_OK)
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
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )
    is_active = openapi.Parameter(
        "is_active",
        in_=openapi.IN_QUERY,
        description="filter form_data by is_active",
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

    @swagger_auto_schema(manual_parameters=[is_active, search, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        if data.get("export"):
            export = True
        else:
            export = False
        try:
            jobsite_obj = JobSites.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
            if export:
                response = HttpResponse(content_type="text/csv")
                response["Content-Disposition"] = 'attachment; filename="export.csv"'

                serializer = JobSitesSerializer(jobsite_obj, many=True)
                model_fields = JobSites._meta.fields
                header = [field.name for field in model_fields]
                print(header)
                writer = csv.DictWriter(response, fieldnames=header)

                writer.writeheader()
                for row in serializer.data:
                    writer.writerow(row)

                return response
            else:
                search_keys = ["job_site__icontains", "id__icontains"]
                data = custom_get_pagination(request, jobsite_obj, JobSites, JobSitesSerializer, search_keys)
                return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpJobSites(APIView):
    """
    This GET function fetches all records from JobSites model
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
        - Serialized Jobsite model data (HTTP_200_OK)
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
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )
    is_active = openapi.Parameter(
        "is_active",
        in_=openapi.IN_QUERY,
        description="filter form_data by is_active",
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

    @swagger_auto_schema(manual_parameters=[is_active, search, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        if data.get("export"):
            export = True
        else:
            export = False
        try:
            jobsite_obj = JobSites.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))
            if export:
                response = HttpResponse(content_type="text/csv")
                response["Content-Disposition"] = 'attachment; filename="export.csv"'

                serializer = JobSitesSerializer(jobsite_obj, many=True)
                model_fields = JobSites._meta.fields
                header = [field.name for field in model_fields]
                writer = csv.DictWriter(response, fieldnames=header)

                writer.writeheader()
                for row in serializer.data:
                    writer.writerow(row)

                return response
            else:
                search_keys = ["job_site__icontains", "id__icontains"]
                data, meta = custom_search(request, jobsite_obj, search_keys)
                resp_data = []
                for i in data:
                    temp_data = {}
                    temp_data["id"] = i.id
                    temp_data["job_site"] = i.job_site
                    temp_data["job_ads_inventory"] = i.job_ads_inventory
                    temp_data["resume_search_inventory"] = i.resume_search_inventory
                    temp_data["package_start_date"] = i.package_start_date
                    temp_data["package_end_date"] = i.package_end_date
                    temp_data["country"] = i.country
                    temp_data["is_active"] = i.is_active
                    temp_data["is_deleted"] = i.is_deleted
                    resp_data.append(temp_data)
                return ResponseOk(
                    {
                        "data": resp_data,
                        "message": "templates fetched",
                        "meta": meta,
                    }
                )
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateJobSites(APIView):
    """
    This POST function creates a JobSites record from the data
    passed in the body.

    Args:
        None
    Body:
        JobSites Model Fields
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

    @swagger_auto_schema(operation_description="JobSites Create API", operation_summary="JobSites Create API", request_body=JobSitesSerializer)
    def post(self, request):
        data = request.data.copy()
        if data.get("package_start_date"):
            pass
        else:
            data["package_start_date"] = None
        if data.get("package_end_date"):
            pass
        else:
            data["package_end_date"] = None
        serializer = JobSitesSerializer(
            data=data,
        )
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "JobSites Created Successfully",
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


class GetJobSites(APIView):
    """
    This GET function fetches particular JobSites instance by ID,
    and return it after serializing it.

    Args:
        pk(jobsite_id)
    Body:
        None
    Returns:
        - Serialized JobSites model data (HTTP_200_OK)
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
            job = custom_get_object(pk, JobSites)
            serializer = JobSitesSerializer(job)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Get Jobsites Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "JobSites Does Not Exist",
                }
            )


class DeleteJobSites(APIView):
    """
    This DELETE function Deletes a JobSites record according to the
    jobsite_id passed in url.

    Args:
        pk(jobsite_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) jobsite_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            job = custom_get_object(pk, JobSites)
            job.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "JobSites Deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "JobSites Does Not Exist",
                }
            )


class UpdateJobSites(APIView):
    """
    This PUT function updates a JobSites model record according to
    the jobsite_id passed in url.

    Args:
        pk(jobsite_id)
    Body:
        JobSites model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) jobsite_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(operation_description="JobSites Update API", operation_summary="JobSites Update API", request_body=JobSitesSerializer)
    def put(self, request, pk):
        try:
            job = custom_get_object(pk, JobSites)
            serializer = JobSitesSerializer(job, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "JobSites Updated Successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "JobSites Does Not Exist",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "JobSites Does Not Exist",
                }
            )


class JobSitesCsvExport(APIView):
    """
    This GET function fetches all the data from JobSites model and converts it into CSV file.

    Args:
        pk(jobsites_id)
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

        all_fields = JobSites.objects.all()

        serializer = JobSitesSerializer(all_fields, many=True)

        header = JobSitesSerializer.Meta.fields

        writer = csv.DictWriter(response, fieldnames=header)

        writer.writeheader()
        for row in serializer.data:
            writer.writerow(row)

        return response
