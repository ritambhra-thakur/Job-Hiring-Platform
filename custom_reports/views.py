from datetime import datetime, timedelta

from django.db.models import Q
from django.shortcuts import render
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions
from rest_framework import status as rep_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from app.response import ResponseBadRequest, ResponseOk
from app.util import get_all_applied_position, paginate_data
from custom_reports.models import CustomReport
from custom_reports.serializers import CustomReportSerializer
from form.models import AppliedPosition, FormData, OfferLetter
from form.serializers import (
    CustomReportCandidateDataSerializer,
    FormDataSerializer,
    HiringSourceSerializer,
    OfferLetterSerializer,
)
from scorecard.models import PositionCompetencyAndAttribute, PositionScoreCard
from stage.models import Stage
from user.models import Profile

from .utils import filter_applied_position, filter_forma_data, filter_offer_letter


class CustomReportView(APIView):
    """
    API Create, Update, Get and Delete Custom Reports.
    Args:
        None
    Body:
        All the fields from CustomReports table
    Returns:
        -success message(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create Custom Report API",
        operation_summary="Create Custom Report API",
        request_body=CustomReportSerializer,
    )
    def post(self, request):
        try:
            data = request.data
            data["user"] = request.user.id
            serializer = CustomReportSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": rep_status.HTTP_200_OK,
                        "message": "report created",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": rep_status.HTTP_400_BAD_REQUEST,
                        "message": "report not saved",
                    }
                )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "report not created",
                }
            )

    @swagger_auto_schema(
        operation_description="Get Custom Report API",
        operation_summary="Get Custom Report API",
        manual_parameters=[
            openapi.Parameter("id", in_=openapi.IN_QUERY, description="id of the custom report", type=openapi.TYPE_INTEGER, required=True),
        ],
    )
    def get(self, request):
        try:
            data = request.GET
            report = CustomReport.objects.get(id=data.get("id"))
            serializer = CustomReportSerializer(report)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": rep_status.HTTP_200_OK,
                    "message": "report updated",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "report does not exist",
                }
            )

    @swagger_auto_schema(
        operation_description="Update Custom Report API",
        operation_summary="Update Custom Report API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    title="id",
                    **{"maxLengh": 100, "minLength": 1},
                ),
                "report_name": openapi.Schema(type=openapi.TYPE_STRING, title="Report name", **{"maxLenght": 50, "minLength": 1}),
                "selected_fields": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), title="Selected fields"),
                "user": openapi.Schema(type=openapi.TYPE_INTEGER, title="User id"),
            },
            required=["id", "report_name", "selected_fields", "user"],
        ),
    )
    def put(self, request):
        try:
            data = request.data
            report = CustomReport.objects.get(id=data.get("id"))
            serializer = CustomReportSerializer(report, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": rep_status.HTTP_200_OK,
                        "message": "report updated",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": rep_status.HTTP_400_BAD_REQUEST,
                        "message": "report not saved",
                    }
                )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "report does not exist",
                }
            )

    @swagger_auto_schema(
        operation_description="Delete Custom Report API",
        operation_summary="Delete Custom Report API",
        manual_parameters=[
            openapi.Parameter("id", in_=openapi.IN_QUERY, description="id of the custom report", type=openapi.TYPE_INTEGER, required=True),
        ],
    )
    def delete(self, request):
        try:
            data = request.GET
            report = CustomReport.objects.get(id=data.get("id"))
            report.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": rep_status.HTTP_200_OK,
                    "message": "report deleted",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "report does not exist",
                }
            )


class GetAllReports(APIView):

    """
    API to list all the custom reports of the logged in user
    Args:
        report_type - Type of the report i.e position, offer stage etc. It is used to filter the report based on its type
    Body:
        None
    Returns:
        -success message with CustomReportsSerializer List(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get All Custom Report API",
        operation_summary="Get All Custom Report API",
        manual_parameters=[
            openapi.Parameter("report_type", in_=openapi.IN_QUERY, description="type of the custom report", type=openapi.TYPE_STRING, required=False),
        ],
    )
    def get(self, request):
        try:
            data = request.GET
            reports = CustomReport.objects.filter(user=request.user)
            if "report_type" in data:
                report_type = data.get("report_type")
                reports = reports.filter(report_type=report_type)
            serializer = CustomReportSerializer(reports, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": rep_status.HTTP_200_OK,
                    "message": "report updated",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "report does not exist",
                }
            )


class FormDataReport(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    """
    API send the FormData Report
    Args:

    Body:
        None
    Returns:
        -success message with FormDataSerializer List(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    @swagger_auto_schema(
        operation_description="Get FormData Custom Report API. While adding query param make sure to use only one of the leble or leblw_net. The same will follow with other parameters like office, employment_type etc.",
        operation_summary="Get FormData Custom Report API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "lable_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the department",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "office", in_=openapi.IN_QUERY, description="comma separated name of the location/coutry", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "office_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "employment_type",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_type_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "salary_gte",
                in_=openapi.IN_QUERY,
                description="greater than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary_lte",
                in_=openapi.IN_QUERY,
                description="less than than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary",
                in_=openapi.IN_QUERY,
                description="equal to salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_gte",
                in_=openapi.IN_QUERY,
                description="greater than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_lte",
                in_=openapi.IN_QUERY,
                description="less than than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date",
                in_=openapi.IN_QUERY,
                description="equal to open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status",
                in_=openapi.IN_QUERY,
                description="status of the position equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status_net",
                in_=openapi.IN_QUERY,
                description="status of the position not equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
    )
    def get(self, request):
        try:
            data = request.GET
            # Filter based on the user
            if request.user.user_role.name in ["superadmin", "admin"]:
                form_data = FormData.objects.filter(company=request.user.user_company)
            else:
                form_data = FormData.objects.filter(Q(hiring_manager=request.user.email) | Q(recruiter=request.user.email))
            # Filter forms based on the params
            form_data = filter_forma_data(form_data, data)
            # Serialize data
            serializer = FormDataSerializer(form_data, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": rep_status.HTTP_200_OK,
                    "message": "report fetched",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "report does not exist",
                }
            )


class GetPipeLineReport(APIView):
    """
    API send the FormData Report
    Args:
        lable,
        lable_net,
        values,
        office,
        office_net,
        employment_type
        ...
    Body:
        None
    Returns:
        -success message with FormDataSerializer List(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        No
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Get PipeLine Custom Report API. While adding query param make sure to use only one of the leble or leblw_net. The same will follow with other parameters like office, employment_type etc.",
        operation_summary="Get PipeLine Custom Report API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "lable_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
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
                "office_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "employment_type",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_type_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "salary_gte",
                in_=openapi.IN_QUERY,
                description="greater than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary_lte",
                in_=openapi.IN_QUERY,
                description="less than than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary",
                in_=openapi.IN_QUERY,
                description="equal to salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_gte",
                in_=openapi.IN_QUERY,
                description="greater than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_lte",
                in_=openapi.IN_QUERY,
                description="less than than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date",
                in_=openapi.IN_QUERY,
                description="equal to open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status",
                in_=openapi.IN_QUERY,
                description="status of the position equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status_net",
                in_=openapi.IN_QUERY,
                description="status of the position not equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
    )
    def get(self, request):
        try:
            response = {}
            data = request.GET

            # Get Applied position of user and its team members
            applied_position_list = get_all_applied_position(request.user.profile)
            applied_positions = (
                AppliedPosition.objects.filter(company=request.user.user_company)
                .filter(id__in=applied_position_list)
                .filter(form_data__status="active")
            )

            # Apply all filters
            applied_positions = filter_applied_position(applied_positions, data)

            # Process the data and serialize it
            if applied_positions:
                serializer = CustomReportCandidateDataSerializer(applied_positions, many=True).data
                return ResponseOk({"data": serializer, "code": rep_status.HTTP_200_OK, "msg": "candidates fetched successfully"})
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "Data Does Not Exist",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "errors",
                }
            )


class GetCandidatesReport(APIView):
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
    queryset = AppliedPosition.objects.all()

    @swagger_auto_schema(
        operation_description="Get Candidate Custom Report API. While adding query param make sure to use only one of the leble or leblw_net. The same will follow with other parameters like office, employment_type etc.",
        operation_summary="Get Candidate Custom Report API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "lable_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
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
                "office_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "employment_type",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_type_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "salary_gte",
                in_=openapi.IN_QUERY,
                description="greater than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary_lte",
                in_=openapi.IN_QUERY,
                description="less than than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary",
                in_=openapi.IN_QUERY,
                description="equal to salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_gte",
                in_=openapi.IN_QUERY,
                description="greater than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_lte",
                in_=openapi.IN_QUERY,
                description="less than than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date",
                in_=openapi.IN_QUERY,
                description="equal to open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status",
                in_=openapi.IN_QUERY,
                description="status of the position equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status_net",
                in_=openapi.IN_QUERY,
                description="status of the position not equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
    )
    def get(self, request):
        try:
            data = request.GET

            # Filter based on the user
            if request.user.user_role.name == "hiring manager":
                applied_position_list = get_all_applied_position(request.user.profile)
                queryset = self.queryset.all().filter(company=request.user.user_company).filter(id__in=applied_position_list)
            else:
                queryset = self.queryset.all().filter(company=request.user.user_company)

            # Apply all filters
            queryset = filter_applied_position(queryset, data)

            # Serialize data
            if queryset:
                serializer = CustomReportCandidateDataSerializer(queryset, many=True).data
                return ResponseOk({"data": serializer, "code": rep_status.HTTP_200_OK, "msg": "candidates fetched successfully"})
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "Applied Position Does Not Exist",
                }
            )
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetNewHiresReport(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Get New Hires Custom Report API. While adding query param make sure to use only one of the leble or leblw_net. The same will follow with other parameters like office, employment_type etc.",
        operation_summary="Get New Hires Custom Report API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "lable_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
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
                "office_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "employment_type",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_type_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "salary_gte",
                in_=openapi.IN_QUERY,
                description="greater than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary_lte",
                in_=openapi.IN_QUERY,
                description="less than than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary",
                in_=openapi.IN_QUERY,
                description="equal to salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_gte",
                in_=openapi.IN_QUERY,
                description="greater than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_lte",
                in_=openapi.IN_QUERY,
                description="less than than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date",
                in_=openapi.IN_QUERY,
                description="equal to open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status",
                in_=openapi.IN_QUERY,
                description="status of the position equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status_net",
                in_=openapi.IN_QUERY,
                description="status of the position not equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET
            user = request.user

            # Get queryset
            if user.user_role.name == "admin":
                new_hires = OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True).filter(
                    start_date__lte=datetime.today().date(), email_changed=False
                )
            else:
                new_hires = (
                    OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True)
                    .filter(Q(offered_to__form_data__recruiter=request.user.email) | Q(offered_to__form_data__hiring_manager=request.user.email))
                    .filter(start_date__gte=datetime.today().date(), email_changed=False)
                )

            # Apply all filters
            queryset = filter_offer_letter(new_hires, data)

            serializer = OfferLetterSerializer(queryset, many=True)
            data = serializer.data
            return ResponseOk(
                {
                    "data": data,
                    "code": rep_status.HTTP_200_OK,
                    "message": "new hires fetched successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "errors",
                }
            )


class GetDepartmentReports(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    queryset = AppliedPosition.objects.all()

    @swagger_auto_schema(
        operation_description="Get Department Custom Report API. While adding query param make sure to use only one of the leble or leblw_net. The same will follow with other parameters like office, employment_type etc.",
        operation_summary="Get Department Custom Report API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "lable_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
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
                "office_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "employment_type",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_type_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "salary_gte",
                in_=openapi.IN_QUERY,
                description="greater than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary_lte",
                in_=openapi.IN_QUERY,
                description="less than than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary",
                in_=openapi.IN_QUERY,
                description="equal to salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_gte",
                in_=openapi.IN_QUERY,
                description="greater than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_lte",
                in_=openapi.IN_QUERY,
                description="less than than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date",
                in_=openapi.IN_QUERY,
                description="equal to open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status",
                in_=openapi.IN_QUERY,
                description="status of the position equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status_net",
                in_=openapi.IN_QUERY,
                description="status of the position not equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET

            # Get queryset
            if request.user.user_role.name == "hiring manager":
                applied_position_list = get_all_applied_position(request.user.profile)
                queryset = self.queryset.filter(company=request.user.user_company).filter(id__in=applied_position_list)
            else:
                queryset = self.queryset.filter(company=request.user.user_company)

            # Apply all filters
            queryset = filter_applied_position(queryset, data)

            serializer = CustomReportCandidateDataSerializer(queryset, many=True)
            data = serializer.data
            return ResponseOk(
                {
                    "data": data,
                    "code": rep_status.HTTP_200_OK,
                    "message": "new hires fetched successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "errors",
                }
            )


class GetOfferReport(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Get Offer Custom Report API. While adding query param make sure to use only one of the leble or leblw_net. The same will follow with other parameters like office, employment_type etc.",
        operation_summary="Get Offer Custom Report API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "lable_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
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
                "office_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "employment_type",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_type_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "salary_gte",
                in_=openapi.IN_QUERY,
                description="greater than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary_lte",
                in_=openapi.IN_QUERY,
                description="less than than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary",
                in_=openapi.IN_QUERY,
                description="equal to salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_gte",
                in_=openapi.IN_QUERY,
                description="greater than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_lte",
                in_=openapi.IN_QUERY,
                description="less than than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date",
                in_=openapi.IN_QUERY,
                description="equal to open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status",
                in_=openapi.IN_QUERY,
                description="status of the position equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status_net",
                in_=openapi.IN_QUERY,
                description="status of the position not equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET

            # Get queryset
            pending_interviewer_list = []
            applied_position_list = []
            interviewer_obj = request.user
            application_obj = AppliedPosition.objects.filter(
                company=interviewer_obj.user_company.id, application_status__in=["pending-offer", "offer", "approved", "offer-rejected"]
            )

            # Apply all filters
            queryset = filter_applied_position(application_obj, data)
            for application in queryset:
                try:
                    interviewer_ids = application.data["interview_schedule_data"]["Interviewer"]
                except:
                    interviewer_ids = []
                for interviewer in interviewer_ids:
                    try:
                        int_id = interviewer["profile_id"]
                    except:
                        int_id = 0
                    if request.user.profile.id == int_id:
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
                    )
                    applied_position_list = applied_position_list.filter(
                        Q(form_data__recruiter=interviewer_obj.email) | Q(form_data__hiring_manager=interviewer_obj.email)
                    )
            applied_position_list = list(set(applied_position_list))
            queryset = AppliedPosition.objects.filter()
            serializer = CustomReportCandidateDataSerializer(applied_position_list, many=True)
            data = serializer.data
            final_data = sorted(data, key=lambda d: d["average_scorecard_rating"], reverse=True)

            return ResponseOk(
                {
                    "data": final_data,
                    "code": rep_status.HTTP_200_OK,
                    "message": "new hires fetched successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "errors",
                }
            )


class GetHireSourceReport(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Get Hires Source Custom Report API. While adding query param make sure to use only one of the leble or leble_net. The same will follow with other parameters like office, employment_type etc.",
        operation_summary="Get Hires Source Custom Report API",
        manual_parameters=[
            openapi.Parameter(
                "lable", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "lable_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
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
                "office_net", in_=openapi.IN_QUERY, description="comma separated name of the department", type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "employment_type",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_type_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "employment_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the employment type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_net",
                in_=openapi.IN_QUERY,
                description="comma separated name of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "level_values",
                in_=openapi.IN_QUERY,
                description="comma separated id of the level",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "salary_gte",
                in_=openapi.IN_QUERY,
                description="greater than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary_lte",
                in_=openapi.IN_QUERY,
                description="less than than salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "salary",
                in_=openapi.IN_QUERY,
                description="equal to salary value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_gte",
                in_=openapi.IN_QUERY,
                description="greater than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date_lte",
                in_=openapi.IN_QUERY,
                description="less than than open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "open_date",
                in_=openapi.IN_QUERY,
                description="equal to open_date value",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status",
                in_=openapi.IN_QUERY,
                description="status of the position equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status_net",
                in_=openapi.IN_QUERY,
                description="status of the position not equal to",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
    )
    def get(self, request):
        if request.user.user_role.name in ["candidate", "employee"]:
            return ResponseBadRequest({"message": "invalid request"})
        try:
            data = request.GET
            user = request.user

            # Get queryset
            if user.user_role.name == "admin":
                new_hires = OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True).filter(
                    start_date__lte=datetime.today().date(), email_changed=False
                )
            else:
                new_hires = (
                    OfferLetter.objects.filter(offered_to__company=user.user_company, accepted=True)
                    .filter(Q(offered_to__form_data__recruiter=request.user.email) | Q(offered_to__form_data__hiring_manager=request.user.email))
                    .filter(start_date__gte=datetime.today().date(), email_changed=False)
                )

            # Apply all filters
            queryset = filter_offer_letter(new_hires, data)

            serializer = HiringSourceSerializer(queryset, many=True)
            data = serializer.data
            return ResponseOk(
                {
                    "data": data,
                    "code": rep_status.HTTP_200_OK,
                    "message": "new hires fetched successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": rep_status.HTTP_400_BAD_REQUEST,
                    "message": "errors",
                }
            )
