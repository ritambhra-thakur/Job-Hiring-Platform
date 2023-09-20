from affinda import AffindaAPI, TokenCredential
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication

from resume_parser.serializers import AffindaSerializer

from .models import Affinda, AffindaSkill
from .serializers import *


class AffindaNER(APIView):
    """
    The POST function creates a Affinda model records which passes as body.
    Args:
        None
    Body:
        -Affinda model fields
    Returns:
        -data(HTTP_200_OK)
        -serializer.errors(HTTP_400_BAD_REQUEST)
    Authentication:
        None
    Raises:
        None

    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]
    parser_classes = (FormParser, MultiPartParser)

    @swagger_auto_schema(
        operation_description="Please upload a file here",
        request_body=AffindaSerializer,
    )
    @action(detail=False, methods=["post"])
    def post(self, request):
        if "file" in request.FILES:
            data = request.data
            token = settings.AFFINDA_KEY
            credential = TokenCredential(token=token)
            client = AffindaAPI(credential=credential)
            # client.create_job_description() ohXKYvlh
            serializer = AffindaSerializer(
                data=data,
            )
            if serializer.is_valid():
                data = serializer.save()
                file_path = Affinda.objects.get(id=int(data.id)).file
                url = "https://" + settings.AWS_S3_CUSTOM_DOMAIN + "/media/" + str(file_path)
                print(url)
                resume = client.create_resume(url=url)
                data = resume.as_dict()
                try:
                    if data["data"]["phone_numbers"][0].startswith("+"):
                        data["data"]["phone_numbers"][0] = data["data"]["phone_numbers"][0][0:13]
                    else:
                        data["data"]["phone_numbers"][0] = data["data"]["phone_numbers"][0][0:10]
                    data["data"]["phone_numbers"] = data["data"]["phone_numbers"][0:1]
                except Exception as e:
                    print(e)
                # Add the skills for later user
                if "data" in data and "skills" in data["data"]:
                    skills = data["data"]["skills"]
                    for skill in skills:
                        try:
                            AffindaSkill.objects.create(name=skill.get("name"))
                        except:
                            pass
                return Response(
                    {
                        "data": data,
                        "code": status.HTTP_200_OK,
                        "message": "Media created successfully",
                    }
                )
            else:
                return Response(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "serializer errors",
                    }
                )

        else:
            return Response({"message": "No file provided/Check the spelling of the key."})
