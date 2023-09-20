import collections
import math

from dal import autocomplete
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import F, Q
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, permissions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication

from app.response import ResponseBadRequest, ResponseNotFound, ResponseOk
from app.util import custom_get_object
from role.permissions import CUDModelPermissions, IsEmployeeUser, RolePermissions

from .models import *
from .serializers import *
from app.encryption import encrypt, decrypt


class KeySkillAutocomplete(autocomplete.Select2QuerySetView):
    """
    This GET function fetches all records from KEYSKILL model after filtering the data on the basis of q and return the data.

    Args:
        None
    Body:
        q
    Returns:
        data
    Authentication:
        JWT
    Raises:
        None
    """

    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return KeySkill.objects.none()

        qs = KeySkill.objects.all()

        if self.q:
            qs = qs.filter(skill__istartswith=self.q)

        return qs


class UniversityAutocomplete(autocomplete.Select2QuerySetView):
    """
    This GET function fetches all records from UNIVERSITY model after filtering the data on the basis of q and return the data.

    Args:
        None
    Body:
        q
    Returns:
        data
    Authentication:
        JWT
    Raises:
        None
    """

    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return University.objects.none()

        qs = University.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


class StateAutocomplete(autocomplete.Select2QuerySetView):
    """
    This GET function fetches all records from STATE model after filtering the data on the basis of q and country, return the data.

    Args:
        None
    Body:
        q
    Returns:
        data
    Authentication:
        JWT
    Raises:
        None
    """

    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return State.objects.none()

        qs = State.objects.none()

        country = self.forwarded.get("country", None)

        if country:
            qs = State.objects.all()
            qs = qs.filter(country=country)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class CityAutocomplete(autocomplete.Select2QuerySetView):
    """
    This GET function fetches all records from CITY model after filtering the data on the basis of q and state, return the data.

    Args:
        None
    Body:
        q
    Returns:
        data
    Authentication:
        JWT
    Raises:
        None
    """

    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return City.objects.none()

        qs = City.objects.none()

        state = self.forwarded.get("state", None)

        if state:
            qs = City.objects.all()
            qs = qs.filter(state=state)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


# Country API's


class GetAllCountry(APIView):
    """
    This GET function fetches all records from COUNTRY model after filtering the records on the basis of search text return the data after serializing it.

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

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
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

    ordering = ("id",)

    @swagger_auto_schema(manual_parameters=[search, page, perpage, sort_dir, sort_field])
    def get(self, request):
        try:
            data = request.GET
            query = data.get("search", "")

            page = data.get("page", 1)

            limit = data.get("perpage", settings.PAGE_SIZE)

            pages, skip = 1, 0

            sort_field = data.get("sort_field")

            sort_dir = data.get("sort_dir")

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            country = Country.objects.all()

            if query:
                country = country.filter(
                    Q(name__icontains=query)
                    | Q(capital__icontains=query)
                    | Q(phone_code__icontains=query)
                    | Q(iso2__icontains=query)
                    | Q(iso3__icontains=query)
                    | Q(currency__icontains=query)
                )

            count = country.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "name":
                        country = country.order_by("name")
                    elif sort_field == "capital":
                        country = country.order_by("capital")
                    elif sort_field == "id":
                        country = country.order_by("id")

                    else:
                        country = country.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "name":
                        country = country.order_by("-name")
                    elif sort_field == "capital":
                        country = country.order_by("-capital")
                    elif sort_field == "id":
                        country = country.order_by("-id")

                    else:
                        country = country.order_by("-id")
            else:
                country = country.order_by("-id")
            if page and limit:
                country = country[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if country:
                country = CountrySerializer(country, many=True).data

                return ResponseOk(
                    {
                        "data": country,
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


class CreateCountry(APIView):
    """
    This POST function creates a COUNTARY model records from the data passes in the body.

    Args:
       None
    Body:
        COUNTARY model fields
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
        operation_description="Country create API",
        operation_summary="Country create API",
        # request_body=openapi.Schema(
        #     type=openapi.TYPE_OBJECT,
        #     properties={
        #         "name": openapi.Schema(type=openapi.TYPE_STRING),
        #         "iso2": openapi.Schema(type=openapi.TYPE_STRING),
        #         "iso3": openapi.Schema(type=openapi.TYPE_STRING),
        #         "phone_code": openapi.Schema(type=openapi.TYPE_STRING),
        #         "capital": openapi.Schema(type=openapi.TYPE_STRING),
        #         "currency": openapi.Schema(type=openapi.TYPE_STRING),
        #         "description": openapi.Schema(type=openapi.TYPE_STRING),
        #         "description": openapi.Schema(type=openapi.TYPE_STRING),
        #     },
        # ),
        request_body=CountrySerializer,
    )
    def post(self, request):
        serializer = CountrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Country created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Country Does Not Exist",
                }
            )


class GetCountry(APIView):
    """
    This GET function fetches particular ID record from COUNTARY model and return the data after serializing it.

    Args:
        pk(country_id)
    Body:
        None
    Returns:
        -Serialized COUNTARY model data of particular ID(HTTP_200_OK)
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
            role = custom_get_object(pk, Country)
            serializer = CountrySerializer(role)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get Country successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Country Does Not Exist",
                }
            )


class UpdateCountry(APIView):
    """
    This PUT function updates particular record by ID from COUNTARY model according to the department_id passed in url.

    Args:
        pk(country_id)
    Body:
        None
    Returns:
        -Serialized COUNTARY model data of particular record by ID(HTTP_200_OK)
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
        operation_description="Country update API",
        operation_summary="Country update API",
        request_body=CountrySerializer,
    )
    def put(self, request, pk):
        try:
            country = custom_get_object(pk, Country)
            serializer = CountrySerializer(country, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Country updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Country Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Country Does Not Exist",
                }
            )


class DeleteCountry(APIView):
    """
    This DETETE function delete particular record by ID from COUNTARY model according to the department_id passed in url.

    Args:
        pk(country_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if country_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            country = custom_get_object(pk, Country)
            country.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Country deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Country Does Not Exist",
                }
            )


# State API's
class GetAllStates(APIView):
    """
    This GET function fetches all records from STATE model with pagination, searching and sorting, and return the data after serializing it.

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

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

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
    country_id = openapi.Parameter(
        "country_id",
        in_=openapi.IN_QUERY,
        description="country_id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            page,
            perpage,
            sort_dir,
            sort_field,
            country_id,
        ]
    )
    def get(self, request):
        try:
            data = request.GET

            if data.get("search"):
                query = data.get("search")
            else:
                query = ""

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

            country_id = data.get("country_id")

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            state = State.objects.all()

            if query:
                state = state.filter(Q(name__icontains=query) | Q(description__icontains=query))
            if country_id:
                state = state.filter(country=country_id)

            count = state.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "name":
                        state = state.order_by("name")
                    elif sort_field == "country":
                        state = state.order_by("country")
                    elif sort_field == "id":
                        state = state.order_by("id")
                    else:
                        state = state.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "name":
                        state = state.order_by("-name")
                    elif sort_field == "country":
                        state = state.order_by("-country")
                    elif sort_field == "id":
                        state = state.order_by("-id")

                    else:
                        state = state.order_by("-id")
            else:
                state = state.order_by("-id")

            if page and limit:
                state = state[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1
            if state:
                state = StateSerializer(state, many=True).data

                return ResponseOk(
                    {
                        "data": state,
                        "meta": {
                            "page": page,
                            "total_pages": pages,
                            "perpage": limit,
                            "sort_dir": sort_dir,
                            "sort_field": sort_field,
                            "total_records": count,
                            "country_id": country_id,
                        },
                    }
                )
            return ResponseBadRequest("Search query has no match")

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateState(APIView):
    """
    This POST function creates a STATE model records from the data passes in the body.

    Args:
       None
    Body:
        STATE model fields
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
        operation_description="State create API",
        operation_summary="State create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        serializer = StateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "State created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "State Does Not Exist",
                }
            )


class GetState(APIView):
    """
    This GET function fetches particular ID record from STATE model and return the data after serializing it.

    Args:
        pk(state_id)
    Body:
        None
    Returns:
        -Serialized STATE model data of particular ID(HTTP_200_OK)
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
            state = custom_get_object(pk, State)
            serializer = StateSerializer(state)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get State successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "State Does Not Exist",
                }
            )


class UpdateState(APIView):
    """
    This PUT function updates particular record by ID from STATE model according to the state_id passed in url.

    Args:
        pk(state_id)
    Body:
        None
    Returns:
        -Serialized STATE model data of particular record by ID(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="State update API",
        operation_summary="State update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def put(self, request, pk):
        try:
            state = custom_get_object(pk, State)
            serializer = StateSerializer(state, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "State updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "State Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "State Does Not Exist",
                }
            )


class DeleteState(APIView):
    """
    This DETETE function delete particular record by ID from STATE model according to the state_id passed in url.

    Args:
        pk(state_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if state_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            state = custom_get_object(pk, State)
            state.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "State deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "State Does Not Exist",
                }
            )


# City API's
class GetAllCities(APIView):
    """
    This GET function fetches all records from CITY model with pagination, searching and sorting, and return the data after serializing it.

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

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

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
    country_id = openapi.Parameter(
        "country_id",
        in_=openapi.IN_QUERY,
        description="country_id",
        type=openapi.TYPE_STRING,
    )
    state_id = openapi.Parameter(
        "state_id",
        in_=openapi.IN_QUERY,
        description="state_id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            search,
            page,
            perpage,
            sort_dir,
            sort_field,
            country_id,
            state_id,
        ]
    )
    def get(self, request):
        try:
            data = request.GET

            if data.get("search"):
                query = data.get("search")
            else:
                query = ""

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

            country_id = data.get("country_id")

            state_id = data.get("state_id")

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            city = City.objects.all()

            if query:
                city = city.filter(Q(name__icontains=query) | Q(description__icontains=query))
            if state_id:
                city = city.filter(state=state_id)

            if country_id:
                city = city.filter(country=country_id)

            count = city.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "name":
                        city = city.order_by("name")
                    elif sort_field == "country":
                        city = city.order_by("country")
                    elif sort_field == "id":
                        city = city.order_by("id")
                    else:
                        city = city.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "name":
                        city = city.order_by("-name")
                    elif sort_field == "country":
                        city = city.order_by("-country")
                    elif sort_field == "id":
                        city = city.order_by("-id")

                    else:
                        city = city.order_by("-id")
            else:
                city = city.order_by("-id")

            if page and limit:
                city = city[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1
            if city:
                city = CitySerializer(city, many=True).data

                return ResponseOk(
                    {
                        "data": city,
                        "meta": {
                            "page": page,
                            "total_pages": pages,
                            "perpage": limit,
                            "sort_dir": sort_dir,
                            "sort_field": sort_field,
                            "total_records": count,
                            "state_id": state_id,
                        },
                    }
                )
            return ResponseBadRequest("Search query has no match")
        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateCity(APIView):
    """
    This POST function creates a CITY model records from the data passes in the body.

    Args:
       None
    Body:
        CITY model fields
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
        operation_description="City create API",
        operation_summary="City create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "state": openapi.Schema(type=openapi.TYPE_INTEGER),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        serializer = CitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "City created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "City Does Not Exist",
                }
            )


class GetCity(APIView):
    """
    This GET function fetches particular ID record from CITY model and return the data after serializing it.

    Args:
        pk(city_id)
    Body:
        None
    Returns:
        -Serialized CITY model data of particular ID(HTTP_200_OK)
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
            state = custom_get_object(pk, City)
            serializer = CitySerializer(state)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get City successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "City Does Not Exist",
                }
            )


class UpdateCity(APIView):
    """
    This PUT function updates particular record by ID from CITY model according to the city_id passed in url.

    Args:
        pk(city_id)
    Body:
        None
    Returns:
        -Serialized CITY model data of particular record by ID(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="City update API",
        operation_summary="State update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "state": openapi.Schema(type=openapi.TYPE_INTEGER),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def put(self, request, pk):
        try:
            city = custom_get_object(pk, City)
            serializer = CitySerializer(city, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "City updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "City Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "City Does Not Exist",
                }
            )


class DeleteCity(APIView):
    """
    This DETETE function delete particular record by ID from CITY model according to the city_id passed in url.

    Args:
        pk(city_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if city_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            city = custom_get_object(pk, City)
            city.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "City deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "City Does Not Exist",
                }
            )


# university API's
class GetAllUniversities(APIView):
    """
    This GET function fetches all records from UNIVERSITY model with pagination, searching and sorting, and return the data after serializing it.

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

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    search = openapi.Parameter(
        "search",
        in_=openapi.IN_QUERY,
        description="search",
        type=openapi.TYPE_STRING,
    )
    country = openapi.Parameter(
        "country",
        in_=openapi.IN_QUERY,
        description="country",
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

    @swagger_auto_schema(manual_parameters=[search, country, page, perpage, sort_field, sort_dir])
    def get(self, request):
        try:
            data = request.GET

            if data.get("search"):
                query = data.get("search")
            else:
                query = ""

            if data.get("page"):
                page = data.get("page")
            else:
                page = 1

            if data.get("perpage"):
                limit = data.get("perpage")
            else:
                limit = str(settings.PAGE_SIZE)

            sort_field = data.get("sort_field")

            country = data.get("country")

            sort_dir = data.get("sort_dir")

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            university = University.objects.all()

            if query:
                university = university.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(web_page__icontains=query))
            if country:
                university = university.filter(country=int(country))

            count = university.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "name":
                        university = university.order_by("name")
                    elif sort_field == "country":
                        university = university.order_by("country")
                    elif sort_field == "id":
                        university = university.order_by("id")
                    elif sort_field == "domain":
                        university = university.order_by("domain")

                    else:
                        university = university.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "name":
                        university = university.order_by("-name")
                    elif sort_field == "country":
                        university = university.order_by("-country")
                    elif sort_field == "id":
                        university = university.order_by("-id")
                    elif sort_field == "domain":
                        university = university.order_by("-domain")

                    else:
                        university = university.order_by("-id")
            else:
                university = university.order_by("-id")

            if page and limit:
                university = university[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if university:
                university = UniversitySerializer(university, many=True).data

                return ResponseOk(
                    {
                        "data": university,
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


class CreateUniversity(APIView):
    """
    This POST function creates a UNIVERSITY model records from the data passes in the body.

    Args:
       None
    Body:
        UNIVERSITY model fields
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
        operation_description="City create API",
        operation_summary="City create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "web_page": openapi.Schema(type=openapi.TYPE_STRING),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        serializer = UniversitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "University created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "University Does Not Exist",
                }
            )


class GetUniversity(APIView):
    """
    This GET function fetches particular ID record from UNIVERSITY model and return the data after serializing it.

    Args:
        pk(university_id)
    Body:
        None
    Returns:
        -Serialized UNIVERSITY model data of particular ID(HTTP_200_OK)
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
            university = custom_get_object(pk, University)
            serializer = UniversitySerializer(university)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get University successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "University Does Not Exist",
                }
            )


class UpdateUniversity(APIView):
    """
    This PUT function updates particular record by ID from UNIVERSITY model according to the university_id passed in url.

    Args:
        pk(university_id)
    Body:
        None
    Returns:
        -Serialized UNIVERSITY model data of particular record by ID(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="City update API",
        operation_summary="State update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "web_page": openapi.Schema(type=openapi.TYPE_STRING),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def put(self, request, pk):
        try:
            university = custom_get_object(pk, University)
            serializer = UniversitySerializer(university, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "University updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "University Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "University Does Not Exist",
                }
            )


class DeleteUniversity(APIView):
    """
    This DETETE function delete particular record by ID from UNIVERSITY model according to the university_id passed in url.

    Args:
        pk(university_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if university_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            university = custom_get_object(pk, University)
            university.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "University deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "University Does Not Exist",
                }
            )


# KeySkill API's
class GetAllKeySkill(APIView):
    """
    This GET function fetches all records from KEYSKILL model with pagination, searching and sorting, and return the data after serializing it.

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

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
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

    name = openapi.Parameter(
        "name",
        in_=openapi.IN_QUERY,
        description="name",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(manual_parameters=[search, page, perpage, sort_dir, sort_field, name])
    def get(self, request):
        try:
            data = request.GET

            if data.get("search"):
                query = data.get("search")
            else:
                query = ""

            if data.get("page"):
                page = data.get("page")
            else:
                page = 1

            if data.get("perpage"):
                limit = data.get("perpage")
            else:
                limit = str(settings.PAGE_SIZE)

            name_field = data.get("name")

            pages, skip = 1, 0

            sort_field = data.get("sort_field")

            sort_dir = data.get("sort_dir")

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            keyskill = KeySkill.objects.all()

            if query:
                keyskill = keyskill.filter(Q(skill__icontains=query))

            if name_field:
                res = name_field.split(",")
                print(res)
                keyskill = keyskill.filter(skill__in=res)

            count = keyskill.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "skill":
                        keyskill = keyskill.order_by("skill")
                    elif sort_field == "id":
                        keyskill = keyskill.order_by("id")
                    else:
                        keyskill = keyskill.order_by("id")

                elif sort_dir == "desc":
                    if sort_field == "skill":
                        keyskill = keyskill.order_by("-skill")
                    elif sort_field == "id":
                        keyskill = keyskill.order_by("-id")

                    else:
                        keyskill = keyskill.order_by("-id")
            else:
                keyskill = keyskill.order_by("skill")

            if page and limit:
                keyskill = keyskill[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if keyskill:
                keyskill = KeySkillSerializer(keyskill, many=True).data

                return ResponseOk(
                    {
                        "data": keyskill,
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

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateKeySkill(APIView):
    """
    This POST function creates a KEYSKILL model records from the data passes in the body.

    Args:
       None
    Body:
        KEYSKILL model fields
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
        operation_description="KeySkill create API",
        operation_summary="KeySkill create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "skill": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        serializer = KeySkillSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "KeySkill created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "KeySkill Does Not Exist",
                }
            )


class GetKeySkill(APIView):
    """
    This GET function fetches particular ID record from KEYSKILL model and return the data after serializing it.

    Args:
        pk(keyskill_id)
    Body:
        None
    Returns:
        -Serialized KEYSKILL model data of particular ID(HTTP_200_OK)
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
            keyskill = custom_get_object(pk, KeySkill)
            serializer = KeySkillSerializer(keyskill)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get KeySkill successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "KeySkill Does Not Exist",
                }
            )


class UpdateKeySkill(APIView):
    """
    This PUT function updates particular record by ID from KEYSKILL model according to the keyskill_id passed in url.

    Args:
        pk(keyskill_id)
    Body:
        None
    Returns:
        -Serialized KEYSKILL model data of particular record by ID(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="KeySkill update API",
        operation_summary="KeySkill update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "skill": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def put(self, request, pk):
        try:
            keyskill = custom_get_object(pk, KeySkill)
            serializer = KeySkillSerializer(keyskill, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "KeySkill updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "KeySkill Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "KeySkill Does Not Exist",
                }
            )


class DeleteKeySkill(APIView):
    """
    This DETETE function delete particular record by ID from KEYSKILL model according to the city_id passed in url.

    Args:
        pk(keyskill_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if keyskill_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            keyskill = custom_get_object(pk, KeySkill)
            keyskill.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "KeySkill deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "KeySkill Does Not Exist",
                }
            )


# Address API's
class GetAllAddress(APIView):
    """
    This GET function fetches all records from ADDRESS model and return the data after serializing it.

    Args:
        None
    Body:
        None
    Returns:
        -Serialized ADDRESS model data(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request):
        try:
            address = Address.objects.all()
            serializer = AddressSerializer(address, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "All Addresses",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Address Does Not Exist",
                }
            )


class CreateAddress(APIView):
    """
    This POST function creates a ADDRESS model records from the data passes in the body.

    Args:
       None
    Body:
        ADDRESS model fields
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
        operation_description="Address create API",
        operation_summary="Address create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "address_one": openapi.Schema(type=openapi.TYPE_STRING),
                "address_two": openapi.Schema(type=openapi.TYPE_STRING),
                "address_three": openapi.Schema(type=openapi.TYPE_STRING),
                "pin_code": openapi.Schema(type=openapi.TYPE_INTEGER),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "state": openapi.Schema(type=openapi.TYPE_INTEGER),
                "city": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
    )
    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Address created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Address Does Not Exist",
                }
            )


class GetAddress(APIView):
    """
    This GET function fetches particular ID record from ADDRESS model and return the data after serializing it.

    Args:
        pk(address_id)
    Body:
        None
    Returns:
        -Serialized ADDRESS model data of particular ID(HTTP_200_OK)
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
            role = custom_get_object(pk, Address)
            serializer = AddressSerializer(role)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get Address successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Address Does Not Exist",
                }
            )


class UpdateAddress(APIView):
    """
    This PUT function updates particular record by ID from ADDRESS model according to the address_id passed in url.

    Args:
        pk(address_id)
    Body:
        None
    Returns:
        -Serialized ADDRESS model data of particular record by ID(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Address Create API",
        operation_summary="Address Create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "address_one": openapi.Schema(type=openapi.TYPE_STRING),
                "address_two": openapi.Schema(type=openapi.TYPE_STRING),
                "address_three": openapi.Schema(type=openapi.TYPE_STRING),
                "pin_code": openapi.Schema(type=openapi.TYPE_INTEGER),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "state": openapi.Schema(type=openapi.TYPE_INTEGER),
                "city": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
    )
    def put(self, request, pk):
        try:
            address = custom_get_object(pk, Address)
            serializer = AddressSerializer(address, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Address updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Address Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Address Does Not Exist",
                }
            )


class DeleteAddress(APIView):
    """
    This DETETE function delete particular record by ID from ADDRESS model according to the address_id passed in url.

    Args:
        pk(address_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if address_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            address = custom_get_object(pk, Address)
            address.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Address deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Address Does Not Exist",
                }
            )


# Education API's
class GetAllEducation(APIView):
    """
    This GET function fetches all records from EDUCATION model with pagination, searching and sorting, and return the data after serializing it.

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
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="search profile_id",
        type=openapi.TYPE_STRING,
    )
    user = openapi.Parameter(
        "user",
        in_=openapi.IN_QUERY,
        description="search user_id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            page,
            perpage,
            sort_dir,
            sort_field,
            profile,
            user,
        ]
    )
    def get(self, request):
        try:
            data = request.GET

            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                return ResponseBadRequest(
                    {
                        "error": "domain field required",
                    }
                )

            if data.get("profile"):
                profile_id = data.get("profile")
                try:
                    profile_id = int(decrypt(profile_id))
                except:
                    pass
            else:
                profile_id = ""

            if data.get("user"):
                user_id = data.get("user")
            else:
                user_id = ""

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

            education = Education.objects.all()

            if profile_id:
                education = education.filter(profile=profile_id)

            if user_id:
                education = education.filter(profile__user__id=user_id)

            if url_domain:
                education = education.filter(profile__user__user_company__url_domain=url_domain)

            count = education.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "profile":
                        education = education.order_by("profile")
                    if sort_field == "university":
                        education = education.order_by("university")
                    elif sort_field == "id":
                        education = education.order_by("id")
                    else:
                        education = education.order_by("id")

                elif sort_dir == "desc":
                    if sort_field == "profile":
                        education = education.order_by("-profile")
                    if sort_field == "university":
                        education = education.order_by("university")
                    elif sort_field == "id":
                        education = education.order_by("-id")

                    else:
                        education = education.order_by("-id")
            else:
                education = education.order_by("id")

            if page and limit:
                education = education[skip : skip + limit]
                pages = math.ceil(count / limit) if limit else 1
            if education:
                education = GetEducationSerializer(education, many=True).data

                return ResponseOk(
                    {
                        "data": education,
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


class CreateEducation(APIView):
    """
    This POST function creates a EDUCATION model records from the data passes in the body.

    Args:
       None
    Body:
        EDUCATION model fields
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
        operation_description="Education create API",
        operation_summary="Education create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "profile": openapi.Schema(type=openapi.TYPE_INTEGER),
                "university": openapi.Schema(type=openapi.TYPE_INTEGER),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "passing_out_year": openapi.Schema(type=openapi.TYPE_INTEGER),
                "education_type": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
    )
    def post(self, request):
        data = request.data
        data["profile"] = request.user.profile.id
        serializer = EducationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Education created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Education is not valid",
                }
            )


class GetEducation(APIView):
    """
    This GET function fetches particular ID record from EDUCATION model and return the data after serializing it.

    Args:
        pk(education_id)
    Body:
        None
    Returns:
        -Serialized EDUCATION model data of particular ID(HTTP_200_OK)
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
            education = custom_get_object(pk, Education)
            serializer = GetEducationSerializer(education)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get Education successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Education Does Not Exist",
                }
            )


class UpdateEducation(APIView):
    """
    This PUT function updates particular record by ID from EDUCATION model according to the education_id passed in url.

    Args:
        pk(education_id)
    Body:
        None
    Returns:
        -Serialized EDUCATION model data of particular record by ID(HTTP_200_OK)
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
        operation_description="Education update API",
        operation_summary="Education update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "profile": openapi.Schema(type=openapi.TYPE_INTEGER),
                "university": openapi.Schema(type=openapi.TYPE_INTEGER),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "passing_out_year": openapi.Schema(type=openapi.TYPE_INTEGER),
                "education_type": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
    )
    def put(self, request, pk):
        try:
            data = request.data
            data["profile"] = request.user.profile.id
            education = custom_get_object(pk, Education)
            serializer = EducationSerializer(education, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Education updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Education Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Education Does Not Exist",
                }
            )


class DeleteEducation(APIView):
    """
    This DETETE function delete particular record by ID from EDUCATION model according to the education_id passed in url.

    Args:
        pk(education_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if education_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            education = custom_get_object(pk, Education)
            education.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Education deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Education Does Not Exist",
                }
            )


# Education API's
class GetAllExperience(APIView):
    """
    This GET function fetches all records from EXPERIENCE model with pagination, searching and sorting, and return the data after serializing it.

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
    profile = openapi.Parameter(
        "profile",
        in_=openapi.IN_QUERY,
        description="search profile_id",
        type=openapi.TYPE_STRING,
    )
    user = openapi.Parameter(
        "user",
        in_=openapi.IN_QUERY,
        description="search user_id",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            page,
            perpage,
            sort_dir,
            sort_field,
            profile,
            user,
        ]
    )
    def get(self, request):
        try:
            data = request.GET

            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                return ResponseBadRequest(
                    {
                        "error": "domain field required",
                    }
                )

            if data.get("profile"):
                profile_id = data.get("profile")
                try:
                    profile_id = int(decrypt(profile_id))
                except:
                    pass
            else:
                profile_id = ""

            if data.get("user"):
                user_id = data.get("user")
            else:
                user_id = ""

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

            experience = Experience.objects.all()

            if profile_id:
                experience = experience.filter(profile=profile_id)

            if user_id:
                experience = experience.filter(profile__user__id=user_id)

            if url_domain:
                experience = experience.filter(profile__user__user_company__url_domain=url_domain)

            count = experience.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "profile":
                        experience = experience.order_by("profile")
                    elif sort_field == "company_name":
                        experience = experience.order_by("company_name")
                    elif sort_field == "join_date":
                        experience = experience.order_by("join_date")
                    elif sort_field == "id":
                        experience = experience.order_by("id")
                    else:
                        experience = experience.order_by("id")

                elif sort_dir == "desc":
                    if sort_field == "profile":
                        experience = experience.order_by("-profile")
                    elif sort_field == "company_name":
                        experience = experience.order_by("-company_name")
                    elif sort_field == "join_date":
                        experience = experience.order_by("-join_date")
                    elif sort_field == "id":
                        experience = experience.order_by("-id")

                    else:
                        experience = experience.order_by("-id")
            else:
                experience = experience.order_by("-join_date")

            if page and limit:
                experience = experience[skip : skip + limit]
                pages = math.ceil(count / limit) if limit else 1
            if experience:
                experience = GetExperienceSerializer(experience, many=True).data

                return ResponseOk(
                    {
                        "data": experience,
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
            return ResponseOk("Search query has no match")

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateExperience(APIView):
    """
    This POST function creates a EXPERIENCE model records from the data passes in the body.

    Args:
       None
    Body:
        EXPERIENCE model fields
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
        operation_description="Experience create API",
        operation_summary="Experience create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "profile": openapi.Schema(type=openapi.TYPE_INTEGER),
                "company_name": openapi.Schema(type=openapi.TYPE_STRING),
                "title": openapi.Schema(type=openapi.TYPE_STRING),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "role_and_responsibilities": openapi.Schema(type=openapi.TYPE_STRING),
                "skill": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description="enter skill id example ['1','2']",
                ),
                "is_current_company": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                "join_date": openapi.Schema(type=openapi.TYPE_STRING, format=settings.FORMAT_DATE),
                "leave_date": openapi.Schema(type=openapi.TYPE_STRING, format=settings.FORMAT_DATE),
            },
        ),
    )
    def post(self, request):
        data = request.data
        data["profile"] = request.user.profile.id
        serializer = ExperienceSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Experience created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Experience is not valid",
                }
            )


class GetExperience(APIView):
    """
    This GET function fetches particular ID record from EXPERIENCE model and return the data after serializing it.

    Args:
        pk(experience_id)
    Body:
        None
    Returns:
        -Serialized EXPERIENCE model data of particular ID(HTTP_200_OK)
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
            experience = custom_get_object(pk, Experience)
            serializer = GetExperienceSerializer(experience)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get Experience successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Experience Does Not Exist",
                }
            )


class UpdateExperience(APIView):
    """
    This PUT function updates particular record by ID from EXPERIENCE model according to the experience_id passed in url.

    Args:
        pk(experience_id)
    Body:
        None
    Returns:
        -Serialized EXPERIENCE model data of particular record by ID(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Experience update API",
        operation_summary="Experience update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "profile": openapi.Schema(type=openapi.TYPE_INTEGER),
                "company_name": openapi.Schema(type=openapi.TYPE_STRING),
                "title": openapi.Schema(type=openapi.TYPE_STRING),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "role_and_responsibilities": openapi.Schema(type=openapi.TYPE_STRING),
                "skill": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description="enter skill id example ['1','2']",
                ),
                "is_current_company": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                "join_date": openapi.Schema(type=openapi.TYPE_STRING, format=settings.FORMAT_DATE),
                "leave_date": openapi.Schema(type=openapi.TYPE_STRING, format=settings.FORMAT_DATE),
            },
        ),
    )
    def put(self, request, pk):
        try:
            data = request.data
            data["profile"] = request.user.profile.id
            experience = custom_get_object(pk, Experience)
            serializer = ExperienceSerializer(experience, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Experience updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Experience Not valid",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Experience Does Not Exist",
                }
            )


class DeleteExperience(APIView):
    """
    This DETETE function delete particular record by ID from EXPERIENCE model according to the experience_id passed in url.

    Args:
        pk(experience_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if experience_id does not exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            experience = custom_get_object(pk, Experience)
            experience.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Experience deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Experience Does Not Exist",
                }
            )


class GetAllEducationType(APIView):
    """
    This GET function fetches all records from EDUCATIONTYPE model and return the data after serializing it.

    Args:
        None
    Body:
        None
    Returns:
        -Serialized EDUCATIONTYPE model data(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    def get(self, request):
        try:
            education_type = EducationType.objects.all()
            serializer = EducationTypeSerializer(education_type, many=True)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "EducationType list",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "EducationType does not exist",
                }
            )


class GetEducationType(APIView):
    """
    This GET function fetches particular ID record from EDUCATIONTYPE model and return the data after serializing it.

    Args:
        pk(educationtype_id)
    Body:
        None
    Returns:
        -Serialized EDUCATIONTYPE model data of particular ID(HTTP_200_OK)
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
            education_type = custom_get_object(pk, EducationType)
            serializer = EducationTypeSerializer(education_type)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get EducationType successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " EducationType Not Exist",
                }
            )


class CreateEducationType(APIView):
    """
    This POST function creates a EDUCATIONTYPE model records from the data passes in the body.

    Args:
       None
    Body:
        EDUCATIONTYPE model fields
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
        operation_description="EducationType create API",
        operation_summary="EducationType create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        serializer = EducationTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "EducationType created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "EducationType is not valid",
                }
            )


class UpdateEducationType(APIView):
    """
    This PUT function updates particular record by ID from EDUCATIONTYPE model according to the educationtype_id passed in url.

    Args:
        pk(educationtype_id)
    Body:
        None
    Returns:
        -Serialized EDUCATIONTYPE model data of particular record by ID(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="EducationType update API",
        operation_summary="EducationType update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def put(self, request, pk):
        try:
            education_type = custom_get_object(pk, EducationType)

            serializer = EducationTypeSerializer(education_type, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "EducationType updated successfully",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "EducationType Does Not Exist",
                }
            )


class DeleteEducationType(APIView):
    """
    This DETETE function delete particular record by ID from EDUCATIONTYPE model according to the educationtype_id passed in url.

    Args:
        pk(educationtype_id)
    Body:
        None
    Returns:
        -None(HTTP_200_OK)
        -None(HTTP_400_BAD_REQUEST)if educationtype_id does not exist
    Authentication:
        None
    Raises:
        None
    """

    def delete(self, request, pk):
        try:
            education_type = custom_get_object(pk, EducationType)
            education_type.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "EducationType deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "EducationType Does Not Exist",
                }
            )


class ListIndustried(APIView):
    def get(self, request):
        try:
            data = []
            for i in Industry.objects.all().order_by("name"):
                data.append(i.name)
            return ResponseOk(
                {
                    "data": data,
                    "code": status.HTTP_200_OK,
                    "message": "Industries fetched Successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Industries Not Fetched",
                }
            )
