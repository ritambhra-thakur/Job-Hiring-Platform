from django.shortcuts import render
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import ShortURL
from .serializers import ShortURLSerializer
from .utils import short_url


class CreateShortURL(APIView):

    """
    API used to Creat short url for an open position.
    Args:
        None
    Body:
        pat - Personal Access token
    Returns:
        -success message(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Create ShortURL API",
        operation_summary="Create ShortURL API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "domain": openapi.Schema(type=openapi.TYPE_STRING),
                "internal": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
        ),
    )
    def post(self, request):
        response = {}
        try:
            data = request.data
            short_string = short_url()
            shorted_url = "{}/job/{}".format(request.headers.get("domain"), short_string)
            data["short_url"] = shorted_url
            serializer = ShortURLSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                response["message"] = "url shorted"
                response["data"] = serializer.data
                return Response(response, status=status.HTTP_201_CREATED)
            else:
                response["message"] = "url not shorted"
                response["error"] = serializer.errors
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response["message"] = "error occured"
            response["error"] = str(e)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetCompleteURL(APIView):

    """
    API used to Get Complete url for an open position.
    Args:
        domain - Domain of the company
    Body:
        pat - Personal Access token
    Returns:
        -Serialized data of table ShortURL(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [JWTAuthentication]

    short_url = openapi.Parameter(
        "short_url",
        in_=openapi.IN_QUERY,
        description="short_url",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        operation_description="Create ShortURL API",
        operation_summary="Create ShortURL API",
        manual_parameters=[
            short_url,
        ],
    )
    def get(self, request):
        response = {}
        try:
            data = request.GET
            short_url = data.get("short_url")
            short_url_obj = ShortURL.objects.get(short_url=short_url)
            serializer = ShortURLSerializer(short_url_obj)
            response["message"] = "short url fetched"
            response["data"] = serializer.data
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            response["message"] = "error occured"
            response["error"] = str(e)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
