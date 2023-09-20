import math

from django.conf import settings
from django.core.cache import cache
from django.db.models import F, Q
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication

from app.response import ResponseBadRequest, ResponseNotFound, ResponseOk
from app.util import custom_get_object
from app.encryption import decrypt
from .models import *
from .serializers import *

# Create your views here.


class GetAllPipeline(APIView):
    """
    This GET function fetches all records from Pipeline model
    after filtering on the basis of fields given in the body
    and return the data after serializing it.

    Args:
        None
    Body:
        - search (optional)
        - pipeline_name (optional)
        - domain (optional)
        - page (optional)
        - perpage (optional)
        - sort_field (optional)
        - sort_dir (optional)
    Returns:
        - Serialized Pipeline model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
        - Exception Text(HTTP_400_BAD_REQUEST)
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
        description="search by pipeline",
        type=openapi.TYPE_STRING,
    )
    pipeline_name = openapi.Parameter(
        "pipelinename",
        in_=openapi.IN_QUERY,
        description="pipelinename",
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
            pipeline_name,
            page,
            perpage,
            sort_dir,
            sort_field,
        ]
    )
    def get(self, request):
        try:
            data = request.GET
            search = data.get("search", "")

            pipeline_name = data.get("pipeline_name", "")

            url_domain = request.headers.get("domain", "")

            page = data.get("page", 1)

            limit = data.get("perpage", settings.PAGE_SIZE)

            pages, skip = 1, 0

            sort_field = data.get("sort_field")

            sort_dir = data.get("sort_dir")

            if page and limit:
                page = int(page)
                limit = int(limit)
                skip = (page - 1) * limit

            pipeline = Pipeline.objects.all().filter(Q(company__url_domain=url_domain) | Q(company=None))

            if search:
                pipeline = pipeline.filter(Q(pipeline_name__icontains=search))

            count = pipeline.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "pipeline_name":
                        pipeline = pipeline.order_by("pipeline_name")
                    elif sort_field == "company":
                        pipeline = pipeline.order_by("company")
                    elif sort_field == "id":
                        pipeline = pipeline.order_by("id")

                    else:
                        pipeline = pipeline.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "pipeline_name":
                        pipeline = pipeline.order_by("-pipeline_name")
                    elif sort_field == "company":
                        pipeline = pipeline.order_by("-company")
                    elif sort_field == "id":
                        pipeline = pipeline.order_by("-id")

                    else:
                        pipeline = pipeline.order_by("-id")
            else:
                pipeline = pipeline.order_by("-id")

            if page and limit:
                pipeline = pipeline[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if pipeline:
                pipeline = PipelineSerializer(pipeline, many=True).data

                return ResponseOk(
                    {
                        "data": pipeline,
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


class CreatePipeline(APIView):
    """
    This POST function creates a Pipeline Model record from the data passed in the body.

    Args:
        None
    Body:
        Pipeline model Fields
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
        operation_description="Pipeline create API",
        operation_summary="Pipeline create API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "pipeline_name": openapi.Schema(type=openapi.TYPE_STRING),
                "company": openapi.Schema(type=openapi.TYPE_INTEGER),
                "sort_order": openapi.Schema(type=openapi.TYPE_INTEGER),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                "is_deleted": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
        ),
    )

    # """
    # Post function created with decorator and pipelineserializer to check serializer
    # is valid or not with the help of model serializer fields
    # """

    @csrf_exempt
    def post(self, request):
        serializer = PipelineSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Pipeline created succesfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Pipeline is not valid",
                }
            )


class GetPipeline(APIView):
    """
    This GET function fetches particular Pipepline model instance by ID,
    and return it after serializing it.

    Args:
        pk(pipeline_id)
    Body:
        None
    Returns:
        - Serialized Pipepline model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) pipeline_id Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            pipeline = custom_get_object(pk, Pipeline)
            serializer = PipelineSerializer(pipeline)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get Pipeline successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " Pipeline Not Exist",
                }
            )


class UpdatePipeline(APIView):
    """
    This PUT function updates a Pipeline Model record according
    to the pipeline_id passed in url.

    Args:
        pk(pipeline_id)
    Body:
        Pipeline Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) pipeline_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Pipeline update API",
        operation_summary="Pipeline update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "pipeline_name": openapi.Schema(type=openapi.TYPE_STRING),
                "company": openapi.Schema(type=openapi.TYPE_INTEGER),
                "sort_order": openapi.Schema(type=openapi.TYPE_INTEGER),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                "is_deleted": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
        ),
    )
    @csrf_exempt
    def put(self, request, pk):
        try:
            pipeline = custom_get_object(pk, Pipeline)
            serializer = PipelineSerializer(pipeline, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Pipeline updated successfully",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Pipeline Does Not Exist",
                }
            )


class DeletePipeline(APIView):
    """
    This DELETE function Deletes a Pipeline Model record accroding to the pipeline_id passed in url.

    Args:
        pk(pipeline_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) pipeline_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    @csrf_exempt
    def delete(self, request, pk):
        try:
            pipeline = custom_get_object(pk, Pipeline)
            pipeline.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Pipeline deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Pipeline Does Not Exist",
                }
            )


class GetAllStage(APIView):
    """
    This GET function fetches all records from Stage model
    after filtering on the basis of fields given in the body
    and return the data after serializing it.

    Args:
        None
    Body:
        - pipeline (optional)
        - stage_name (optional)
        - domain (optional)
        - page (optional)
        - perpage (optional)
        - sort_field (optional)
        - sort_dir (optional)
    Returns:
        - Serialized Pipeline model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
        - Exception Text(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]
    stage_name = openapi.Parameter(
        "stage_name",
        in_=openapi.IN_QUERY,
        description="stage_name",
        type=openapi.TYPE_STRING,
    )
    pipeline = openapi.Parameter(
        "pipeline",
        in_=openapi.IN_QUERY,
        description="pipeline",
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
        description="sort_field - sort_order",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[
            stage_name,
            pipeline,
            page,
            perpage,
            sort_dir,
            sort_field,
        ]
    )
    def get(self, request):
        try:
            data = request.GET

            if data.get("stage_name"):
                stage_name = data.get("stage_name")
            else:
                stage_name = ""

            if data.get("pipeline"):
                pipeline = data.get("pipeline")
            else:
                pipeline = ""

            if request.headers.get("domain"):
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

            stage = Stage.objects.all().filter(Q(company__url_domain=url_domain) | Q(company=None))
            if stage_name:
                stage = stage.filter(Q(stage_name__icontains=stage_name))
            if pipeline:
                stage = stage.filter(Q(pipeline=pipeline))
            count = stage.count()
            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "stage_name":
                        stage = stage.order_by("stage_name")
                    elif sort_field == "company":
                        stage = stage.order_by("company")
                    elif sort_field == "pipeline":
                        stage = stage.order_by("-pipeline")
                    elif sort_field == "id":
                        stage = stage.order_by("id")

                    else:
                        stage = stage.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "stage_name":
                        stage = stage.order_by("-stage_name")
                    elif sort_field == "company":
                        stage = stage.order_by("-company")
                    elif sort_field == "pipeline":
                        stage = stage.order_by("-pipeline")
                    elif sort_field == "id":
                        stage = stage.order_by("-id")

                    else:
                        stage = stage.order_by("-id")
            else:
                stage = stage.order_by("-id")
            stage = stage.order_by("sort_order")
            if page and limit:
                stage = stage[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1
            if stage:
                stage = StageSerializer(stage, many=True).data
                return ResponseOk(
                    {
                        "data": stage,
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


class CreateStage(APIView):
    """
    This POST function creates a Stage Model record from the
    data passed in the body.

    Args:
        None
    Body:
        Stage model Fields
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
        operation_description="Stage create API",
        operation_summary="Stage create API",
        request_body=StageSerializer,
    )
    @csrf_exempt
    def post(self, request):
        serializer = StageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Stage created succesfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Stage is not valid",
                }
            )


class GetStage(APIView):
    """
    This GET function fetches particular Stage model instance by ID,
    and return it after serializing it.

    Args:
        pk(stage_id)
    Body:
        None
    Returns:
        - Serialized Stage model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) stage_id Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            stage = custom_get_object(pk, Stage)
            serializer = StageSerializer(stage)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get Stage successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Stage Not Exist",
                }
            )


class UpdateStage(APIView):
    """
    This PUT function updates a Stage Model record according
    to the stage_id passed in url.

    Args:
        pk(stage_id)
    Body:
        Stage Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) stage_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Stage update API",
        operation_summary="Stage update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "stage_name": openapi.Schema(type=openapi.TYPE_STRING),
                "company": openapi.Schema(type=openapi.TYPE_INTEGER),
                "pipeline": openapi.Schema(type=openapi.TYPE_INTEGER),
                "sort_order": openapi.Schema(type=openapi.TYPE_INTEGER),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                "is_deleted": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
        ),
    )
    def put(self, request, pk):
        try:
            stage = custom_get_object(pk, Stage)
            serializer = StageSerializer(stage, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Stage updated succesfully",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Stage Does Not Exist",
                }
            )


class DeleteStage(APIView):
    """
    This DELETE function Deletes a Stage Model record accroding to the stage_id passed in url.

    Args:
        pk(stage_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) stage_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    @csrf_exempt
    def delete(self, request, pk):
        try:
            stage = custom_get_object(pk, Stage)
            stage.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Stage deleted Successfully",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": str(e),
                }
            )


class GetAllPositionStage(APIView):
    """
    This GET function fetches all records from Stage Postion model
    after filtering on the basis of fields given in the body
    and return the data after serializing it.

    Args:
        None
    Body:
        - domain (mandatory)
        - search (optional)
        - position (optional)
        - page (optional)
        - perpage (optional)
        - sort_field (optional)
        - sort_dir (optional)
    Returns:
        - Serialized Stage Postion model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
        - Exception Text(HTTP_400_BAD_REQUEST)
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
        description="search by positionstage",
        type=openapi.TYPE_STRING,
    )
    position = openapi.Parameter(
        "position",
        in_=openapi.IN_QUERY,
        description="Enter position id",
        type=openapi.TYPE_STRING,
    )
    candidate_id = openapi.Parameter(
        "candidate_id",
        in_=openapi.IN_QUERY,
        description="Enter candidate_id",
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
            position,
            candidate_id,
            page,
            perpage,
            sort_dir,
            sort_field,
        ]
    )
    def get(self, request):
        try:
            # data = cache.get(request.get_full_path())
            # if data:
            #     return ResponseOk(
            #         {
            #             "data": data.get("data"),
            #             "meta": data.get("meta"),
            #         }
            #     )
            data = request.GET
            if data.get("search"):
                search = data.get("search")
            else:
                search = ""

            if request.headers.get("domain") is not None:
                url_domain = request.headers.get("domain")
            else:
                raise serializers.ValidationError("domain field required")

            if data.get("position") is not None:
                position = data.get("position")
            else:
                raise serializers.ValidationError("position field required")
            candidate_id = data.get("candidate_id")

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

            positions = PositionStage.objects.all().filter(Q(company__url_domain=url_domain) | Q(company=None))

            if search:
                positions = positions.filter(Q(positions_name__icontains=search))
            if position:
                positions = positions.filter(Q(position=position))

            count = positions.count()

            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    if sort_field == "sort_order":
                        positions = positions.order_by("sort_order")
                    elif sort_field == "company":
                        positions = positions.order_by("company")
                    elif sort_field == "id":
                        positions = positions.order_by("id")

                    else:
                        positions = positions.order_by("id")
                elif sort_dir == "desc":
                    if sort_field == "sort_order":
                        positions = positions.order_by("-sort_order")
                    elif sort_field == "company":
                        positions = positions.order_by("-company")
                    elif sort_field == "id":
                        positions = positions.order_by("-id")

                    else:
                        positions = positions.order_by("-id")
            else:
                positions = positions.order_by("-id")

            if page and limit:
                positions = positions[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            if positions:
                context = {"candidate_id": candidate_id}
                positions = PositionStageListSerializer(positions, many=True, context=context).data
                resp = {
                    "data": positions,
                    "meta": {
                        "page": page,
                        "total_pages": pages,
                        "perpage": limit,
                        "sort_dir": sort_dir,
                        "sort_field": sort_field,
                        "total_records": count,
                    },
                }
                # cache.set(request.get_full_path(), resp)
                return ResponseOk(resp)
            return ResponseBadRequest("Search query has no match")

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreatePositionStage(APIView):
    """
    This POST function creates a Stage Position Model record from the
    data passed in the body.

    Args:
        None
    Body:
        Stage Position model Fields
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
        operation_description="Position create API",
        operation_summary="Position create API",
        request_body=PositionStageSerializer,
    )

    # """
    # Post function created with decorator and positionstageserializer to check serializer
    # is valid or not with the help of model serializer fields
    # """

    @csrf_exempt
    def post(self, request):
        profiles = request.data.get("profiles")
        updated_profiles = []
        for i in profiles:
            try:
                int(i)
                updated_profiles.append(i)
            except:
                updated_profiles.append(decrypt(i))
        data = request.data
        data["profiles"] = updated_profiles
        serializer = PositionStageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Position created succesfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Position is not valid",
                }
            )


class GetPositionStage(APIView):
    """
    This GET function fetches particular Stage Position model instance by ID,
    and return it after serializing it.

    Args:
        pk(stage_position_id)
    Body:
        None
    Returns:
        - Serialized Stage Position model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) stage_position_id Does Not Exist
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            positions = custom_get_object(pk, PositionStage)
            serializer = PositionStageSerializer(positions)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "get positions successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": " positions Not Exist",
                }
            )


class UpdatePositionStage(APIView):
    """
    This PUT function updates a Stage Position Model record according
    to the stage_position_id passed in url.

    Args:
        pk(stage_position_id)
    Body:
        Stage Position Model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) stage_position_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Position update API",
        operation_summary="Position update API",
        request_body=PositionStageSerializer,
    )
    @csrf_exempt
    def put(self, request, pk):
        try:
            profiles = request.data.get("profiles")
            updated_profiles = []
            for i in profiles:
                try:
                    int(i)
                    updated_profiles.append(i)
                except:
                    updated_profiles.append(decrypt(i))
            data = request.data
            data["profiles"] = updated_profiles
            positions = custom_get_object(pk, PositionStage)
            serializer = PositionStageSerializer(positions, data=data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Position updated successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Position Does Not Exist",
                    }
                )
        except Exception as e:
            print(e)
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Position Does Not Exist",
                }
            )


class DeletePositionStage(APIView):
    """
    This DELETE function Deletes a Stage Position Model record accroding to the stage_position_id passed in url.

    Args:
        pk(stage_position_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) stage_position_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    @csrf_exempt
    def delete(self, request, pk):
        try:
            positions = custom_get_object(pk, PositionStage)
            positions.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Position deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Position Does Not Exist",
                }
            )


class DeleteStagesByPositionId(APIView):
    """
    This DELETE function deletes a Position Stage Model record accroding to the position_id passed in url.

    Args:
        pk(position_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) position_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    @csrf_exempt
    def delete(self, request, pk):
        try:
            positions = PositionStage.objects.filter(position=pk)
            positions.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Position Stage deleted Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Position Id Does Not Exist",
                }
            )
