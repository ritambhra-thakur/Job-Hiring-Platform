import imp
import math

from django.conf import settings
from django.db.models import F, Q
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, permissions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication

from app.response import ResponseBadRequest, ResponseNotFound, ResponseOk
from app.util import custom_get_object, custom_get_pagination, custom_search
from company.models import Company
from user.models import Media, Profile, Token, User

from .models import EmailTemplate, TemplateType
from .serializers import EmailTemplatesSerializer, TemplateTypeSerializer

# Create your views here


class GetAllEmailTemplates(APIView):
    """
    This GET function fetches all records from EMAILTEMPLATE model and return the data after serializing it.

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
            company = Company.objects.get(url_domain=url_domain)
        else:
            raise serializers.ValidationError("domain field required")
        try:
            queryset = EmailTemplate.objects.filter(Q(company=None) | Q(company=company))
            template_obj = queryset.filter(Q(company__url_domain=url_domain) | Q(company=None))
            search_keys = ["template_name__icontains", "template_type__icontains", "description__icontains"]
            data = custom_get_pagination(request, template_obj, EmailTemplate, EmailTemplatesSerializer, search_keys)
            for i in data.get("data"):
                i["description"] = i["description"].replace("InferTalents", company.company_name)
            return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpEmailTemplates(APIView):
    """
    This GET function fetches all records from EMAILTEMPLATE model and return the data after serializing it.

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
            company = Company.objects.get(url_domain=url_domain)
        else:
            raise serializers.ValidationError("domain field required")
        # try:
        #     queryset = EmailTemplate.objects.filter(Q(company=None) | Q(company=company))
        #     template_obj = queryset.filter(Q(company__url_domain=url_domain) | Q(company=None))
        #     search_keys = ["template_name__icontains", "template_type__icontains", "description__icontains"]
        #     data = custom_get_pagination(request, template_obj, EmailTemplate, EmailTemplatesSerializer, search_keys)
        #     for i in data.get("data"):
        #         i["description"] = i["description"].replace("InferTalents", company.company_name)
        #     return ResponseOk(data)
        # except Exception as e:
        #     return ResponseBadRequest({"debug": str(e)})
        try:
            queryset = EmailTemplate.objects.filter(Q(company=None) | Q(company=company))
            template_obj = queryset.filter(Q(company__url_domain=url_domain) | Q(company=None))
            search_keys = ["template_name__icontains", "template_type__icontains", "description__icontains"]
            queryset, meta = custom_search(request, template_obj, search_keys)
            data = []
            for i in queryset:
                temp_data = {}
                temp_data["id"] = i.id
                temp_data["template_name"] = i.template_name
                temp_data["is_active"] = i.is_active
                temp_data["description"] = i.description.replace("InferTalents", company.company_name)
                data.append(temp_data)
            return ResponseOk(
                {
                    "data": data,
                    "message": "templates fetched",
                    "meta": meta,
                }
            )
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetEmailTemplates(APIView):
    """
    This GET function fetches particular ID record from EMAILTEMPLATE model and return the data after serializing it.

    Args:
        pk(emailtemplate_id)
    Body:
        None
    Returns:
        -Serialized EMAILTEMPLATE model data of particular ID(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            email_templates = custom_get_object(pk, EmailTemplate)
            serializer = EmailTemplatesSerializer(email_templates)

            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Email_templates fetched successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Templates Does Not Exist",
                }
            )


class CreateEmailTemplates(APIView):
    """
    This POST function creates a EMAILTEMPLATE model records from the data passes in the body.

    Args:
       None
    Body:
        EMAILTEMPLATE model fields
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
        operation_description="Template Create API",
        operation_summary="Template Create API",
        request_body=EmailTemplatesSerializer,
    )
    def post(self, request):
        data = request.data
        data["company"] = request.user.user_company.id
        serializer = EmailTemplatesSerializer(
            data=data,
        )

        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Template created successfully",
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


class UpdateEmailTemplates(APIView):
    """
    This PUT function updates particular record by ID from EMAILTEMPLATE model according to the emailtemplate_id passed in url.

    Args:
        pk(emailtemplate_id)
    Body:
        None
    Returns:
        -Serialized EMAILTEMPLATE model data of particular record by ID(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="Template update API",
        operation_summary="Template update API",
        request_body=EmailTemplatesSerializer,
    )
    def put(self, request, pk):
        try:
            data = request.data

            email_templates = custom_get_object(pk, EmailTemplate)
            serializer = EmailTemplatesSerializer(email_templates, data=data)

            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Template updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Template Does Not Exist",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Template Does Not Exist",
                }
            )


class DeleteEmailTemplates(APIView):
    """
    This DETETE function delete particular record by ID from EMAILTEMPLATE model according to the emailtemplate_id passed in url.

    Args:
        pk(emailtemplate_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if emailtemplate_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(Manual_parameters=EmailTemplate)
    def delete(self, request, pk, format=None):
        try:
            emailtemplates = custom_get_object(pk, EmailTemplate)
            emailtemplates.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Templates deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Templates Does Not Exist",
                }
            )


class GetAllTemplateType(APIView):
    queryset = TemplateType.objects.all()

    # template_type = openapi.Parameter(
    #     "template_type",
    #     in_=openapi.IN_QUERY,
    #     description="template_type",
    #     type=openapi.TYPE_STRING,
    # )

    """Decorator with parameter swagger auto schema"""

    @swagger_auto_schema(manual_parameters=[])
    def get(self, request):
        data = request.GET
        if "template_type" in data:
            template_type_obj = TemplateType.objects.filter(template_type_name=data["template_type_name"])

        else:
            template_type_obj = TemplateType.objects.all()

        serializer = TemplateTypeSerializer(template_type_obj, many=True)
        return Response({"data": serializer.data, "message": "Template Type Fetched Successfully", "status": 200}, status=200)
