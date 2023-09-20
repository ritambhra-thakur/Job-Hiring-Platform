# Create your views here.
import math

from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication

from app.response import ResponseBadRequest, ResponseOk
from app.util import custom_get_object
from main import settings
from user.models import User

from .models import (
    ChatMessages,
    Notifications,
    NotificationSerializer,
    NotificationType,
)


def index(request):
    groups = ChatMessages.objects.all()
    dat = []
    res = []
    for group in groups:
        if group.group_name not in dat:
            dat.append(group.group_name)
            res.append(group)

    context = {"groups": res}

    return render(request, "notification/index.html", context)


def room(request, room_name, token):
    return render(request, "notification/room.html", {"room_name": room_name, "token": token})


def save_notification(request):
    if request.method == "POST":
        obj = Notifications()
        try:
            user_obj = User.objects.get(id=request.POST["user"])
        except User.DoesNotExist:
            print("--------------------------->> issue")
            return render(request, "notification/index.html")

        obj.user = user_obj
        obj.title = request.POST["title"]
        obj.body = request.POST["body"]
        obj.save()
        print("-------->> Message Saved Successfully.")

        return render(request, "notification/index.html")

    return {"message": "Only POST method is allowed"}


class GetAllNotifications(APIView):
    """
     This GET function fetches all records from Notifications model
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
        - Serialized notification model data (HTTP_200_OK)
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
    user_id = openapi.Parameter(
        "user_id",
        in_=openapi.IN_QUERY,
        description="filter notifications by user_id",
        type=openapi.TYPE_STRING,
    )
    # domain = openapi.Parameter(
    #     "domain",
    #     in_=openapi.IN_QUERY,
    #     description="Enter search keyword for search in form_data",
    #     type=openapi.TYPE_STRING,
    # )
    is_active = openapi.Parameter(
        "is_active",
        in_=openapi.IN_QUERY,
        description="filter notifications by is_active",
        type=openapi.TYPE_BOOLEAN,
    )
    is_read = openapi.Parameter(
        "is_read",
        in_=openapi.IN_QUERY,
        description="filter notifications by is_read",
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

    @swagger_auto_schema(manual_parameters=[is_active, is_read, user_id, search, page, perpage, sort_dir, sort_field])
    def get(self, request):
        data = request.GET

        # if data.get("domain") is not None:
        #     url_domain = data.get("domain")
        # else:
        #     raise serializers.ValidationError("domain field required")

        # is_active
        is_active = data.get("is_active")

        # Search
        search = data.get("search")

        is_read = data.get("is_read")

        # pagination
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

        # access filter
        try:
            notification_obj = Notifications.objects.filter(user=request.user, is_active=True)

            if is_active is not None:
                notification_obj = notification_obj.filter(is_active=is_active)

            if is_read is not None:
                notification_obj = notification_obj.filter(is_read=is_read)

            if search is not None:
                notification_obj = notification_obj.filter(Q(title__icontains=search) | Q(id__icontains=search) | Q(body__icontains=search))

            # count of entry's
            count = notification_obj.count()

            # sorting
            if sort_field is not None and sort_dir is not None:
                if sort_dir == "asc":
                    try:
                        notification_obj = notification_obj.order_by(sort_field)
                    except:
                        notification_obj = notification_obj.order_by("id")

                elif sort_dir == "desc":
                    try:
                        notification_obj = notification_obj.order_by(-sort_field)
                    except:
                        notification_obj = notification_obj.order_by("-id")
            else:
                notification_obj = notification_obj.order_by("-id")

            # pagination
            total_unread = notification_obj.filter(is_read=False).count()
            if page and limit:
                notification_obj = notification_obj[skip : skip + limit]

                pages = math.ceil(count / limit) if limit else 1

            # if data is present
            if notification_obj:
                serialized_data = NotificationSerializer(notification_obj, many=True).data
                return ResponseOk(
                    {
                        "data": serialized_data,
                        "meta": {
                            "page": page,
                            "total_pages": pages,
                            "perpage": limit,
                            "sort_dir": sort_dir,
                            "sort_field": sort_field,
                            "total_records": count,
                            "total_unread": total_unread,
                        },
                    }
                )
            else:
                return ResponseBadRequest("No Data Found")

        except Exception as e:
            return ResponseBadRequest({"debug": str(e)})


class CreateNotifications(APIView):
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Notification create API",
        operation_summary="Notification create API",
        request_body=NotificationSerializer,
    )
    def post(self, request):
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Notification created successfully",
                }
            )
        else:
            return ResponseBadRequest(
                {
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Notification is not valid",
                }
            )


class GetNotifications(APIView):
    """
     This GET function fetches particular Notifications instance by ID,
     and return it after serializing it.

    Args:
        pk(notification_id)
    Body:
        None
    Returns:
        - Serialized Notifications model data (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    def get(self, request, pk):
        try:
            notification_obj = custom_get_object(pk, Notifications)
            serializer = NotificationSerializer(notification_obj)
            return ResponseOk(
                {
                    "data": serializer.data,
                    "code": status.HTTP_200_OK,
                    "message": "Notification Fetched Successfully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Notification Does Not Exist",
                }
            )


class DeleteNotifications(APIView):
    """
     This DELETE function Deletes a Notifications record according to the
     notification_id passed in url.

    Args:
        pk(notification_id)
    Body:
        None
    Returns:
        - None (HTTP_200_OK)
        - None (HTTP_400_BAD_REQUEST) notification_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    def delete(self, request, pk):
        try:
            notification_obj = custom_get_object(pk, Notifications)
            notification_obj.delete()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Notification Deleted SuccessFully",
                }
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Notification Does Not Exist",
                }
            )


class UpdateNotifications(APIView):
    """
     This PUT function updates a Notifications model record according to
     the notification_id passed in url.

    Args:
        pk(notification_id)
    Body:
        Notifications model Fields(to be updated)
    Returns:
        - None (HTTP_200_OK)
        - serializer.errors (HTTP_400_BAD_REQUEST)
        - None (HTTP_400_BAD_REQUEST) notification_id does not exists
    Authentication:
        JWT
    Raises:
        None
    """

    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Update Notification API. It requires ID of the Notification in the Payload.",
        operation_summary="Update Notification API",
        request_body=NotificationSerializer,
    )
    def put(self, request, pk):
        try:
            notification_obj = custom_get_object(pk, Notifications)
            serializer = NotificationSerializer(notification_obj, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return ResponseOk(
                    {
                        "data": serializer.data,
                        "code": status.HTTP_200_OK,
                        "message": "Notification Updated Successfully",
                    }
                )
            else:
                return ResponseBadRequest(
                    {
                        "data": serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "Notification Does Not Exist",
                    }
                )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Notification Does Not Exist",
                }
            )


class NotificationTypeView(APIView):
    """
    This API list all the notification types with their relevant data. - GET Method
    It also provides a method to change the status of the notification - PUT Method
    Args:
        None
    Body:
        None - GET Methodd
        is_active - PUT Methodd
    Returns:
        - None (HTTP_200_OK)
        - (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    @swagger_auto_schema(
        operation_description="This API fetches all the types of notification that has to be send",
        operation_summary="Notification type Get API",
    )
    def get(self, request):
        try:
            id = request.data.get("id")
            notification_type_objs = NotificationType.objects.all().order_by("id")
            response = []
            for notifi_type in notification_type_objs:
                temp_dict = {}
                temp_dict["id"] = notifi_type.id
                temp_dict["name"] = notifi_type.name
                temp_dict["slug"] = notifi_type.slug
                temp_dict["is_active"] = notifi_type.is_active
                response.append(temp_dict)
            return ResponseOk(
                {
                    "data": response,
                    "code": status.HTTP_200_OK,
                    "message": "Notification Type Fetched",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Notification Type Does Not Exist",
                }
            )

    @swagger_auto_schema(
        operation_description="This API Updates the types of notifications",
        operation_summary="Notification type Update API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
        ),
    )
    def put(self, request):
        try:
            id = request.data.get("id")
            notification_type_obj = NotificationType.objects.get(id=id)
            notification_type_obj.is_active = request.data.get("is_active")
            notification_type_obj.save()
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Notification Type Updated",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Notification Type Does Not Exist",
                }
            )


class ClearNotification(APIView):
    """
    This API is used to clear the selected notification i.e to set them is_active=False
    Args:
        None
    Body:
        ids - ids of notifications
    Returns:
        - None (HTTP_200_OK)
        - (HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.JWTAuthentication]

    def post(self, request):
        try:
            ids = request.data.get("ids")
            for notification_id in ids:
                Notifications.objects.filter(id=notification_id, user=request.user).update(is_active=False)
            return ResponseOk(
                {
                    "data": None,
                    "code": status.HTTP_200_OK,
                    "message": "Notification Updated",
                }
            )
        except Exception as e:
            return ResponseBadRequest(
                {
                    "data": str(e),
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Notification Type Does Not Exist",
                }
            )
