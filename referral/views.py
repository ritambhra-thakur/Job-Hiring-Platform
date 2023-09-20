import csv
import imp
import math
from locale import currency

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.db.models import CharField, Q
from django.db.models import Value as V
from django.db.models.functions import Cast, Concat
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, permissions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication

from app.encryption import decrypt, encrypt
from app.response import ResponseBadRequest, ResponseNotFound, ResponseOk
from app.SendinSES import fetch_dynamic_email_template
from app.util import custom_get_object, custom_get_pagination
from form import utils as form_utils
from form.models import AppliedPosition, FormData, UserSelectedField
from form.serializers import (
    AppliedPositionListSerializer,
    AppliedPositionOpReferralSerializer,
    AppliedPositionReferralSerializer,
)
from referral import serializers as currency_serializers
from referral import serializers as referral_serializers
from stage.models import PositionStage, Stage
from user.models import Media, Profile, Token, User
from user.serializers import MediaSerializer

from .models import Currency, ReferralPolicy
from .serializers import (
    CsvReferralSerializer,
    CurrencySerializer,
    ReferralListSerializer,
    ReferralSerializer,
)

# Create your views here.


class GetAllReferral(APIView):
    """
    GetAllReferral class is created to get all the referral details
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
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
    export = openapi.Parameter(
        "export",
        in_=openapi.IN_QUERY,
        description="export",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[search, page, perpage, sort_dir, sort_field, export])
    def get(self, request):
        data = request.GET
        if request.headers.get("domain") is not None:
            url_domain = request.headers.get("domain")
        else:
            raise serializers.ValidationError("domain field required")
        export = data.get("export")
        try:
            queryset = ReferralPolicy.objects.all()
            referral_obj = queryset.filter(Q(company__url_domain=url_domain) | Q(company=None))
            search_keys = ["referral_name__icontains", "country__name", "state__name"]
            if export:
                select_type = request.GET.get("select_type")
                csv_response = HttpResponse(content_type="text/csv")
                csv_response["Content-Disposition"] = 'attachment; filename="export.csv"'
                writer = csv.writer(csv_response)
                selected_fields = UserSelectedField.objects.filter(profile=request.user.profile, select_type=select_type)
                if selected_fields:
                    selected_fields = selected_fields.last().selected_fields
                else:
                    selected_fields = ["Referral Name", "Country", "State", "Payout", "Attach Policy"]
                writer.writerow(selected_fields)
                for data in queryset:
                    serializer_data = ReferralSerializer(data).data
                    row = []
                    for field in selected_fields:
                        if field.lower() == "country":
                            value = data.country.name
                        elif field.lower() == "state":
                            value = data.state.name
                        elif field.lower() == "currency":
                            value = data.currency.currency_name
                        elif field.lower() == "job_categories":
                            temp = []
                            for job_category in data.job_categories.all():
                                temp.append(job_category.job_category)
                            value = temp
                        elif field.lower() == "positions":
                            temp = []
                            for position in data.positions.all():
                                temp.append(position.form_data["job_title"])
                            value = temp
                        else:
                            field = form_utils.referral_dict.get(field)
                            value = form_utils.get_value(serializer_data, field)
                        try:
                            row.append(next(value, None))
                        except:
                            row.append(value)
                    writer.writerow(row)
                response = HttpResponse(csv_response, content_type="text/csv")
                return response
            else:
                data = custom_get_pagination(request, referral_obj, ReferralPolicy, ReferralListSerializer, search_keys)
            return ResponseOk(data)
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetReferral(APIView):
    """
    GetReferral APIView class is created with permission, JWT Authentication and
    get_object function
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            referral = custom_get_object(pk, ReferralPolicy)
            serializer = ReferralSerializer(referral)

            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Get Referral details successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Refferar Does Not Exist",
                }
            )


class CreateReferral(APIView):
    """
    CreateReferral APIView class is created with permission, JWT Authentication and
    post function with decorators
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="Referral Create API",
        request_body=referral_serializers.ReferralSerializer,
    )
    def post(self, request):
        data = request.data.copy()
        if "referral_name" not in data:
            return ResponseBadRequest(
                {
                    "data": "Name can not be blank",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Name can not be blank",
                }
            )
        if data.get("currency") == "undefined":
            data["currency"] = None
        serializer = referral_serializers.ReferralSerializer(
            data=data,
        )

        if serializer.is_valid():
            data = serializer.save()
            return ResponseOk(
                {
                    "data": "done",
                    "code": status.HTTP_200_OK,
                    "message": "Referral created successfully",
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


class UpdateReferral(APIView):
    """
    UpdateReferral APIView class is created with permission, JWT Authentication and
    get_object, put and swagger auto schema function with decorators
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="Referral update API",
        operation_summary="Referral update API",
        request_body=referral_serializers.ReferralSerializer,
    )
    def put(self, request, pk):
        try:
            data = request.data.copy()

            if data["referral_amount"].replace(" ", "") == "null":
                data["referral_amount"] = ""
            if data["referral_rate_start_date"].replace(" ", "") == "null":
                data["referral_rate_start_date"] = ""

            if "referral_name" not in data:
                return ResponseBadRequest(
                    {
                        "data": "Name can not be blank",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Name can not be blank",
                    }
                )
            if data.get("currency") == "undefined":
                data["currency"] = None
            referral = custom_get_object(pk, ReferralPolicy)
            serializer = referral_serializers.ReferralSerializer(referral, data=data)

            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "referral updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "referral Does Not Exist",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "referral Does Not Exist",
                }
            )


class DeleteReferral(APIView):
    """
    DeleteReferral APIView class is created with permission, JWT Authentication and
    get_object, delete function with decorators to delete the referral
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(Manual_parameters=ReferralPolicy)
    def delete(self, request, pk, format=None):
        try:
            referral = custom_get_object(pk, ReferralPolicy)
            referral.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Referral deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Referral Does Not Exist",
                }
            )


# for currency crud operations
class GetAllCurrency(APIView):
    """
    GetAllCurrency class is created to get the list of all currencies
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(manual_parameters=[])
    def get(self, request):
        # data = request.GET
        currency = Currency.objects.all().order_by("currency_name")
        serializer = CurrencySerializer(currency, many=True)
        from pprint import pprint

        pprint(serializer.data)
        return ResponseOk(
            {
                "data": serializer.data,
                "code": status.HTTP_200_OK,
                "message": "Currency List Fetched Successfully",
            }
        )


class GetCurrency(APIView):
    """
    GetCurrency APIView class is created with permission, JWT Authentication and
    get_object function
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            currency = custom_get_object(pk, Currency)
            serializer = CurrencySerializer(currency)

            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Get Currency details successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Currency Does Not Exist",
                }
            )


class CreateCurrency(APIView):
    """
    CreateCurrency APIView class is created with permission, JWT Authentication and
    post function with decorators
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    # parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="Currency Create API",
        operation_summary="Currency Create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "currency_name": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        serializer = CurrencySerializer(
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Currency created successfully",
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


class UpdateCurrency(APIView):
    """
    UpdateCurrency APIView class is created with permission, JWT Authentication and
    get_object, put and swagger auto schema function with decorators
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="Currency update API",
        operation_summary="Currency update API",
        request_body=currency_serializers.CurrencySerializer,
    )
    def put(self, request, pk):
        try:
            data = request.data

            currency = custom_get_object(pk, Currency)
            serializer = currency_serializers.CurrencySerializer(currency, data=data)

            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "currency updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "currency Does Not Exist",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "currency Does Not Exist",
                }
            )


class DeleteCurrency(APIView):
    """
    DeleteCurrency APIView class is created with permission, JWT Authentication and
    get_object, delete function with decorators to delete the currency
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(Manual_parameters=Currency)
    def delete(self, request, pk, format=None):
        try:
            currency = custom_get_object(pk, Currency)
            currency.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Currency deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Currency Does Not Exist",
                }
            )


class ReferralCsvExport(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, referral_id):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="export.csv"'

        all_fields = ReferralPolicy.objects.filter(referral_name=referral_id)

        serializer = referral_serializers.CsvReferralSerializer(all_fields, many=True)

        header = referral_serializers.CsvReferralSerializer.Meta.fields

        writer = csv.DictWriter(response, fieldnames=header)

        writer.writeheader()
        for row in serializer.data:
            writer.writerow(row)

        return response


class SendRefferalMail(APIView):
    link = openapi.Parameter(
        "link",
        in_=openapi.IN_QUERY,
        description="Enter link",
        type=openapi.TYPE_STRING,
    )
    emails = openapi.Parameter(
        "emails",
        in_=openapi.IN_QUERY,
        description="Enter email",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_STRING),
    )

    @swagger_auto_schema(manual_parameters=[link, emails])
    @csrf_exempt
    def post(self, request, format=None):
        data = request.data
        message = data.get("link")
        from_email = settings.EMAIL_HOST_USER
        if data.get("emails"):
            c_list = data.get("emails")
            if isinstance(c_list, str):
                email_list = data.get("emails").split(",")
            else:
                email_list = c_list
        else:
            email_list = None
        to_email = email_list
        try:
            form_data = FormData.objects.get(id=request.data.get("form_data"))
            position_name = form_data.form_data["job_title"]
        except:
            position_name = ""
        # context = {"link": message}
        # body_msg = render_to_string("refferal.html", context)

        # msg = EmailMultiAlternatives("Email Verification<Don't Reply>", body_msg, from_email, to_email)
        # msg.content_subtype = "html"
        # msg.send()
        link = request.data.get("link")
        company_name = None
        try:
            profile_id = int(decrypt(link.split("/")[-1]))
            print(profile_id, type(profile_id))
            profile_obj = Profile.objects.get(id=profile_id)
            company_name = profile_obj.user.user_company.company_name
        except Exception as e:
            print(e)
        subject = "Refer a Friend"
        to = email_list
        content = data.get("content")
        content = fetch_dynamic_email_template(
            content, to, subject=subject, company_name=company_name, employee_name=request.user.get_full_name(), position_name=position_name
        )

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


class GetAllReferralList(APIView):
    """
    This GET function fetches all records from All Applied Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)

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
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[search])
    def get(self, request):
        data = request.GET

        if data.get("search"):
            query = data.get("search")
        else:
            query = ""

        if data.get("profile_id"):
            profile_id = data.get("profile_id")
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
        else:
            profile_id = ""

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
        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        referral_search = AppliedPosition.objects.all()
        try:
            queryset = AppliedPosition.objects.filter(form_data__company__url_domain=url_domain, form_data__status="active")
            queryset = queryset.filter(Q(refereed_by_profile__isnull=False)).exclude(refereed_by_profile={})
            if request.user.user_role.name in ["hiring manager", "recruiter"]:
                queryset = queryset.filter(
                    Q(form_data__hiring_manager=request.user.email)
                    | Q(form_data__recruiter=request.user.email)
                    | Q(refereed_by_profile__name=request.user.get_full_name())
                )
            else:
                queryset = queryset.filter(
                    Q(refereed_by_profile__name=request.user.get_full_name()) | Q(refereed_by_profile__value=request.user.profile.id)
                )
            queryset = queryset.exclude(refereed_by_profile__name=[None, "", {"key": "value"}])
            if query:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name")
                ).filter(
                    Q(full_name__icontains=query)
                    | Q(form_data__form_data__job_title__icontains=query)
                    | Q(refereed_by_profile__name__icontains=query)
                )
            # if profile_id:
            #     try:
            #         temp_obj = Profile.objects.get(id=profile_id)
            #         queryset = queryset.filter(refereed_by_profile__name__icontains=temp_obj.user.get_full_name())
            #     except Exception as e:
            #         print(e)
            ids = []
            for i in queryset:
                try:
                    ref_id = i.refereed_by_profile["value"]
                    profile_obj = Profile.objects.get(id=ref_id)
                    print(profile_obj.user.user_role.name)
                    if profile_obj.user.user_role.name not in ["candidate", "guest"]:
                        ids.append(i.id)
                except:
                    pass
            queryset = AppliedPosition.objects.filter(id__in=ids)
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
                    fields = ["Candidate Name", "Position No", "Position Name", "Status"]
                    writer.writerow(fields)
                    for data in queryset:
                        try:
                            row = []
                            row.append(i.applied_profile.user.get_full_name())
                            row.append(i.form_data.show_id)
                            row.append(i.form_data.form_data.get("job_title"))
                            stage_id = i.data["position_stage_id"]
                            stage = PositionStage.objects.get(id=stage_id)
                            row.append(stage.stage.stage_name)
                            writer.writerow(row)
                        except:
                            pass
                    response = HttpResponse(csv_response, content_type="text/csv")
                    return response
                else:
                    if page and limit:
                        queryset = queryset[skip : skip + limit]

                        pages = math.ceil(count / limit) if limit else 1
                    data = []
                    for i in queryset:
                        try:
                            temp_data = {}
                            temp_data["candidate_name"] = i.applied_profile.user.get_full_name()
                            temp_data["position_no"] = i.form_data.id
                            temp_data["sposition_id"] = i.form_data.show_id
                            temp_data["position_name"] = i.form_data.form_data.get("job_title")
                            stage_id = i.data["position_stage_id"]
                            stage = PositionStage.objects.get(id=stage_id)
                            temp_data["status"] = stage.stage.stage_name
                            temp_data["user_applied_id"] = i.applied_profile.id
                            temp_data["applied_profile_id"] = i.id
                            temp_data["id"] = i.id
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

            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Referral List Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetAllOpReferralList(APIView):
    """
    This GET function fetches all records from All Applied Position model according
    to the listed filters in body section and return the data
    after serializing it.

    Args:
        None
    Body:
        - domain(mandatory)

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

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[search])
    def get(self, request):
        data = request.GET

        if data.get("search"):
            query = data.get("search")
        else:
            query = ""

        if data.get("profile_id"):
            profile_id = data.get("profile_id")
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
        else:
            profile_id = ""

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
        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        referral_search = AppliedPosition.objects.all()
        try:
            queryset = AppliedPosition.objects.filter(form_data__company__url_domain=url_domain, form_data__status="active")
            queryset = queryset.filter(Q(refereed_by_profile__isnull=False)).exclude(refereed_by_profile={})
            if request.user.user_role.name in ["hiring manager", "recruiter"]:
                queryset = queryset.filter(
                    Q(form_data__hiring_manager=request.user.email)
                    | Q(form_data__recruiter=request.user.email)
                    | Q(refereed_by_profile__name=request.user.get_full_name())
                )
            else:
                queryset = queryset.filter(
                    Q(refereed_by_profile__name=request.user.get_full_name()) | Q(refereed_by_profile__value=request.user.profile.id)
                )
            queryset = queryset.exclude(refereed_by_profile__name=[None, "", {"key": "value"}])
            if query:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name"),
                    string_id=Cast("form_data__show_id", output_field=CharField(max_length=256)),
                ).filter(
                    Q(full_name__icontains=query)
                    | Q(form_data__form_data__job_title__icontains=query)
                    | Q(refereed_by_profile__name__icontains=query)
                    | Q(string_id__icontains=query)
                )
            ids = []
            for i in queryset:
                try:
                    ref_id = i.refereed_by_profile["value"]
                    profile_obj = Profile.objects.get(id=ref_id)
                    if profile_obj.user.user_role.name not in ["candidate", "guest"]:
                        ids.append(i.id)
                except:
                    pass
            queryset = AppliedPosition.objects.filter(id__in=ids)
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
                    fields = ["Position No", "Position Name", "Candidate Name", "Location", "Referred By", "Hiring Stage"]

                    writer.writerow(fields)
                    for i in queryset:
                        row = []
                        row.append(i.form_data.show_id)
                        row.append(i.form_data.form_data.get("job_title"))
                        row.append(i.applied_profile.user.get_full_name())
                        row.append(i.form_data.form_data["location"][0]["label"])
                        row.append(i.refereed_by_profile.get("name"))
                        try:
                            hiring_stage = Stage.objects.get(id=i.data.get("current_stage_id")).stage_name
                        except:
                            hiring_stage = "Resume Review"
                        row.append(hiring_stage)
                        writer.writerow(row)
                    response = HttpResponse(csv_response, content_type="text/csv")
                    return response
                else:
                    if page and limit:
                        resp_data = []
                        for i in queryset:
                            temp_data = {}
                            temp_data["applied_profile"] = i.id
                            temp_data["user_applied_id"] = i.applied_profile.id
                            temp_data["id"] = i.id
                            temp_data["position_id"] = i.form_data.id
                            temp_data["sposition_id"] = i.form_data.show_id
                            temp_data["position_no"] = i.form_data.id
                            temp_data["position_name"] = i.form_data.form_data.get("job_title")
                            temp_data["location"] = i.form_data.form_data["location"][0]["label"]
                            temp_data["candidate_name"] = i.applied_profile.user.get_full_name()
                            temp_data["refereed_by_profile"] = i.refereed_by_profile.get("name")
                            temp_data["source"] = i.applicant_details.get("source")
                            try:
                                temp_data["hiring_stage"] = Stage.objects.get(id=i.data.get("current_stage_id")).stage_name
                            except:
                                temp_data["hiring_stage"] = "Resume Review"
                            resp_data.append(temp_data)
                        queryset = resp_data[skip : skip + limit]

                        pages = math.ceil(count / limit) if limit else 1
                    return ResponseOk(
                        {
                            "data": queryset,
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
                    "message": "Referral List Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetNextRefCandidate(APIView):
    """
    This GET function fetches the next candidate in the candidate referral list.
    Args:
        form_data,
        applied_profile
    Body:
        - domain(mandatory)

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
    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[search])
    def get(self, request):
        data = request.GET

        if data.get("search"):
            query = data.get("search")
        else:
            query = ""

        if data.get("profile_id"):
            profile_id = data.get("profile_id")
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
        else:
            profile_id = ""

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
        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        referral_search = AppliedPosition.objects.all()
        try:
            queryset = AppliedPosition.objects.filter(form_data__company__url_domain=url_domain, form_data__status="active")
            queryset = queryset.filter(Q(refereed_by_profile__isnull=False)).exclude(refereed_by_profile={})
            if request.user.user_role.name in ["hiring manager", "recruiter"]:
                queryset = queryset.filter(
                    Q(form_data__hiring_manager=request.user.email)
                    | Q(form_data__recruiter=request.user.email)
                    | Q(refereed_by_profile__name=request.user.get_full_name())
                )
            else:
                queryset = queryset.filter(
                    Q(refereed_by_profile__name=request.user.get_full_name()) | Q(refereed_by_profile__value=request.user.profile.id)
                )
            queryset = queryset.exclude(refereed_by_profile__name=[None, "", {"key": "value"}])
            if query:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name")
                ).filter(
                    Q(full_name__icontains=query)
                    | Q(form_data__form_data__job_title__icontains=query)
                    | Q(refereed_by_profile__name__icontains=query)
                )
            ids = []
            for i in queryset:
                try:
                    ref_id = i.refereed_by_profile["value"]
                    profile_obj = Profile.objects.get(id=ref_id)
                    if profile_obj.user.user_role.name not in ["candidate", "guest"]:
                        ids.append(i.id)
                except:
                    pass
            queryset = AppliedPosition.objects.filter(id__in=ids)
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
            else:
                return ResponseBadRequest({"msg": "no next candidate found"})
            return ResponseOk(
                {
                    "data": next_data,
                    "current_user": curr_data,
                    "previous_data": prev_data,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "data fetched successfully",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetPrevRefCandidate(APIView):
    """
    This GET function fetches the previous candidate in the candidate referral list dashboard.
    Args:
        form_data,
        applied_profile
    Body:
        - domain(mandatory)
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

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="Enter search keyword in form_data ",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[search])
    def get(self, request):
        data = request.GET

        if data.get("search"):
            query = data.get("search")
        else:
            query = ""

        if data.get("profile_id"):
            profile_id = data.get("profile_id")
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
        else:
            profile_id = ""

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
        if data.get("form_data"):
            form_data = data.get("form_data")
        else:
            form_data = 0
        if data.get("form_data"):
            applied_position = data.get("applied_position")
        else:
            applied_position = 0
        pages, skip = 1, 0

        sort_field = data.get("sort_field")

        sort_dir = data.get("sort_dir")

        if page and limit:
            page = int(page)
            limit = int(limit)
            skip = (page - 1) * limit

        referral_search = AppliedPosition.objects.all()
        try:
            queryset = AppliedPosition.objects.filter(form_data__company__url_domain=url_domain, form_data__status="active")
            queryset = queryset.filter(Q(refereed_by_profile__isnull=False)).exclude(refereed_by_profile={})
            if request.user.user_role.name in ["hiring manager", "recruiter"]:
                queryset = queryset.filter(
                    Q(form_data__hiring_manager=request.user.email)
                    | Q(form_data__recruiter=request.user.email)
                    | Q(refereed_by_profile__name=request.user.get_full_name())
                )
            else:
                queryset = queryset.filter(
                    Q(refereed_by_profile__name=request.user.get_full_name()) | Q(refereed_by_profile__value=request.user.profile.id)
                )
            queryset = queryset.exclude(refereed_by_profile__name=[None, "", {"key": "value"}])
            if query:
                queryset = queryset.annotate(
                    full_name=Concat("applied_profile__user__first_name", V(" "), "applied_profile__user__last_name")
                ).filter(
                    Q(full_name__icontains=query)
                    | Q(form_data__form_data__job_title__icontains=query)
                    | Q(refereed_by_profile__name__icontains=query)
                )
            ids = []
            for i in queryset:
                try:
                    ref_id = i.refereed_by_profile["value"]
                    profile_obj = Profile.objects.get(id=ref_id)
                    print(profile_obj.user.user_role.name)
                    if profile_obj.user.user_role.name not in ["candidate", "guest"]:
                        ids.append(i.id)
                except:
                    pass
            queryset = AppliedPosition.objects.filter(id__in=ids)
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
                prev_obj = None
                for idx, query in enumerate(queryset):
                    if query.id == applied_position:
                        try:
                            prev_obj = queryset[idx - 1]
                        except:
                            return ResponseBadRequest({"msg": "no previous candidate found"})
                if prev_obj:
                    serializer = AppliedPositionReferralSerializer(prev_obj).data
                    return ResponseOk({"data": serializer, "msg": "Previous candidate fetched"})
                else:
                    return ResponseBadRequest({"msg": "no next candidate found"})
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Referral List Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetRecruiterByReferralList(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(manual_parameters=[])
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
            queryset = AppliedPosition.objects.filter(form_data__company__url_domain=url_domain).filter(
                Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email)
            )
            queryset = queryset.filter(Q(refereed_by_profile__isnull=False)).exclude(refereed_by_profile={})
            # queryset = queryset.filter(refereed_by_profile__user__user_company__url_domain=url_domain)
            # if request.user.user_role.name == "hiring manager":
            #     queryset = queryset.filter(
            #         Q(form_data__hiring_manager=request.user.email) | Q(form_data__created_by_profile=request.user.profile)
            #     )
            # else:
            #     queryset = queryset.filter(refereed_by_profile__name=request.user.get_full_name())
            queryset = queryset.exclude(refereed_by_profile__name=[None, "", {"key": "value"}])
            ids = []
            for i in queryset:
                try:
                    ref_id = i.refereed_by_profile["value"]
                    profile_obj = Profile.objects.get(id=ref_id)
                    if profile_obj.user.user_role.name not in ["candidate", "guest"]:
                        ids.append(i.id)
                except:
                    pass
            queryset = AppliedPosition.objects.filter(id__in=ids)
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
                serializer = AppliedPositionReferralSerializer(queryset, many=True).data
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
                    "message": "Referral List Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class GetOpRecruiterByReferralList(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(manual_parameters=[])
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
            queryset = AppliedPosition.objects.filter(form_data__company__url_domain=url_domain).filter(
                Q(form_data__hiring_manager=request.user.email) | Q(form_data__recruiter=request.user.email)
            )
            queryset = queryset.filter(Q(refereed_by_profile__isnull=False)).exclude(refereed_by_profile={})
            queryset = queryset.exclude(refereed_by_profile__name=[None, "", {"key": "value"}])
            ids = []
            for i in queryset:
                try:
                    ref_id = i.refereed_by_profile["value"]
                    profile_obj = Profile.objects.get(id=ref_id)
                    if profile_obj.user.user_role.name not in ["candidate", "guest"]:
                        ids.append(i.id)
                except:
                    pass
            queryset = AppliedPosition.objects.filter(id__in=ids)
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
                serializer = AppliedPositionOpReferralSerializer(queryset, many=True).data
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
                    "message": "Referral List Does Not Exist",
                }
            )

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class SendInterviewInvitationMail(APIView):
    to_cc = openapi.Parameter(
        "to_cc",
        in_=openapi.IN_QUERY,
        description="Enter to_cc",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_STRING),
    )
    to_emails = openapi.Parameter(
        "to_emails",
        in_=openapi.IN_QUERY,
        description="Enter to_emails",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_STRING),
    )

    @swagger_auto_schema(manual_parameters=[to_cc, to_emails])
    def get(self, request, format=None):
        data = request.GET

        from_email = settings.EMAIL_HOST_USER
        if data.get("to_emails"):
            c_list = data.get("to_emails")
            if isinstance(c_list, str):
                to_email_list = data.get("to_emails").split(",")
            else:
                to_email_list = c_list
        else:
            to_email_list = None

        if data.get("to_cc"):
            c_list = data.get("to_cc")
            if isinstance(c_list, str):
                cc_email_list = data.get("to_cc").split(",")
            else:
                cc_email_list = c_list
        else:
            cc_email_list = None

        body_msg = render_to_string("refferal.html")

        msg = EmailMultiAlternatives("Email Verification<Don't Reply>", body_msg, from_email, to_email_list, cc=cc_email_list)
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
