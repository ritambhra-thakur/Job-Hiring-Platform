from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication
from rest_framework.response import Response
from app.util import download_csv, paginate_data, search_data, sort_data
from user.models import User
from app.response import ResponseBadRequest, ResponseOk
from .models import *
from .serializers import *
from django.http.response import HttpResponse


class GetOrganization(APIView):

    """
    This API returns the single object of an Organization
    Args-
        pk - pk of the Organization
    Return-
        It return a single object with the data of a single organization.
    """

    def get(self, request, pk, format=None):
        if id:
            item = Organization.objects.get(id=pk)
            print(item)
            serializer = OrganizationSerializer(item)
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

        items = Organization.objects.all()
        serializer = OrganizationSerializer(items, many=True)
        return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)


# class GetAllOrganization(APIView):

#     queryset = Organization.objects.all()
#     company = openapi.Parameter(
#         "company",
#         in_=openapi.IN_QUERY,
#         description="company",
#         type=openapi.TYPE_STRING,
#     )

#     """Decorator with parameter swagger auto schema"""

#     @swagger_auto_schema(manual_parameters=[company])
#     @csrf_exempt
#     def get(self, request):
#         data = request.GET
#         if data:
#             organization_obj = Organization.objects.filter(company=data["company"])
#         else:
#             organization_obj = Organization.objects.all()
#         serializer = GetOrganizationSerializer(organization_obj, many=True)
#         return Response({"data": serializer.data, "message": "Organization Fetched Successfully", "status": 200}, status=200)


class CreateOrganization(APIView):

    """
    This API creates an Organization
    Args-
        None
    Body-
        All fields from Organization model
    """

    @swagger_auto_schema(
        operation_description="Organization Create API", operation_summary="Organization Create API", request_body=OrganizationSerializer
    )
    def post(self, request, format=None):
        data = request.data
        serializer = OrganizationSerializer(
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return Response({"data": serializer.data, "message": "OK", "status": 200}, status=200)
        else:
            return Response({"data": serializer.errors, "message": "Some Error Occured", "status": 400}, status=400)


class UpdateOrganization(APIView):

    """
    This API edits an Organization
    Args-
        None
    Body-
        All or some fields from the Organization model
    """

    @swagger_auto_schema(
        operation_description="Organization Update API",
        operation_summary="Organization Update API",
        request_body=OrganizationSerializer,
    )
    def put(self, request, pk=None, format=None):
        data = request.data
        response = Response()
        try:
            todo_to_update = Organization.objects.get(id=pk)
        except Organization.DoesNotExist:
            response.data = {"message": "Organization Does not Exist", "data": None}
            return Response({"data": serializer.errors, "message": "Some Error Occured", "status": 400}, status=400)
        serializer = OrganizationSerializer(instance=todo_to_update, data=data, partial=True)

        serializer.is_valid(raise_exception=True)

        serializer.save()

        response.data = {"message": "Organization Updated Successfully", "data": serializer.data}

        return Response({"data": serializer.data, "message": "OK", "status": 200}, status=200)


class DeleteOrganization(APIView):

    """
    This API deletes an Organization
    Args-
        pk - pk of the organization
    """

    def delete(self, request, pk, format=None):
        try:
            todo_to_delete = Organization.objects.get(id=pk)
        except Organization.DoesNotExist:
            return Response({"data": None, "message": "Organization Does not Exist!", "status": 400}, status=400)

        todo_to_delete.delete()

        return Response({"data": None, "message": "Organization Deleted Successfully", "status": 200}, status=200)


class GetAllOrganization(APIView):
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

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    # queryset = FormModel.AppliedPosition.objects.all()

    sort_field = openapi.Parameter(
        "sort_field",
        in_=openapi.IN_QUERY,
        description="sort_field",
        type=openapi.TYPE_STRING,
    )

    sort_dir = openapi.Parameter(
        "sort_dir",
        in_=openapi.IN_QUERY,
        description="sort_dir",
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

    @swagger_auto_schema(manual_parameters=[sort_dir, sort_field, page, perpage])
    def get(self, request):
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        try:
            queryset = Organization.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))

            # queryset = sort_data(queryset, sort_field, sort_dir)
            # search_keys = []
            # queryset = search_data(queryset, Organization, search_keys)
            search = data.get("search")
            if search:
                queryset = search_data(queryset, Organization, search)
            pagination_data = paginate_data(request, queryset, Organization)
            queryset = pagination_data.get("paginate_data")
            if queryset:
                serializer = OrganizationSerializer(queryset, many=True).data

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
                    "message": "Organization Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class OrganizationCSVExport(APIView):

    """
    This GET function fetches all rorganization records and exports it into CSV

    Args:
        None
    Body:
        - domain(mandatory)

    Returns:
        - CSV File with all the data of organization
        - None (HTTP_400_BAD_REQUEST) Applied Position Model Does Not Exist
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        raise serializers.ValidationError("domain field required")
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    sort_field = openapi.Parameter(
        "sort_field",
        in_=openapi.IN_QUERY,
        description="sort_field",
        type=openapi.TYPE_STRING,
    )

    sort_dir = openapi.Parameter(
        "sort_dir",
        in_=openapi.IN_QUERY,
        description="sort_dir",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[sort_dir, sort_field])
    def get(self, request):
        data = request.GET
        try:
            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")

            sort_field = data.get("sort_field")

            sort_dir = data.get("sort_dir")

            try:
                queryset = Organization.objects.filter(Q(company__url_domain=url_domain) | Q(company=None))

                search = data.get("search")
                if search:
                    queryset = search_data(queryset, Organization, search)
                if queryset:
                    # Create the HttpResponse object with the appropriate CSV header.
                    data = download_csv(request, queryset)
                    response = HttpResponse(data, content_type="text/csv")
                    return response
                return ResponseBadRequest(
                    {
                        "data": None,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Organization Does Not Exist",
                    }
                )
            except Exception as e:
                return ResponseBadRequest({"debug": str(e)})
        except:
            pass
