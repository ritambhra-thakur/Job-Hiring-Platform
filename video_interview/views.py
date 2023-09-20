# Testing New Auth FLow
import os
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import google.oauth2.credentials
import google_auth_oauthlib.flow
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from app.util import send_meeting_link
from form.models import AppliedPosition
from user.models import Profile

from .models import MeetingData
from .utils import create_zoom_meeting, createMeeting

SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ID = 43428


# Not used anymore
class CreateCalendarEventForInterview(APIView):
    @swagger_auto_schema(
        operation_description="Not used as of now - Create Google Calendar Event API",
        operation_summary="Not used as of now - Create Google Calendar Event API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={},
        ),
    )
    def post(self, request):
        try:
            code = request.data.get("code")
            state = request.data.get("state")
            start_time = request.data.get("startTime")
            end_time = request.data.get("endTime")
            timezone = request.data.get("timezone")
            innterview_title = request.data.get("title")
            candidate_email = request.data.get("candidate_email")
            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file("client_secret.json", scopes=SCOPES, state=state)
            # flow.redirect_uri = 'https://infertalent.com/oauth/callback/1'
            # flow.redirect_uri = "http://localhost:8080/oauth/callback/1"
            flow.redirect_uri = "https://{}/oauth/callback/1".format(settings.BE_DOMAIN_NAME)

            # authorization_response = request.build_absolute_uri()
            authorization_response = "https://infertalent.com/oauth/callback/1?state={}&code={}".format(state, code)
            flow.fetch_token(authorization_response=authorization_response)
            credentials = flow.credentials
            service = build("calendar", "v3", credentials=credentials)
            event = {
                "conferenceDataVersion": 1,
                "summary": innterview_title,
                "start": {
                    "dateTime": start_time + ":00",
                    "timeZone": timezone,
                },
                "end": {
                    "dateTime": end_time + ":00",
                    "timeZone": timezone,
                },
                "attendees": [
                    {"email": candidate_email},
                ],
                "conferenceData": {"createRequest": {"requestId": "sample123", "conferenceSolutionKey": {"type": "hangoutsMeet"}}},
            }
            event = service.events().insert(calendarId="primary", body=event, sendNotifications="true", conferenceDataVersion=1).execute()
            return Response({"msg": "Schedule Created!", "link": event.get("hangoutLink")}, status=drf_status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)


class CreateZoomMeetingView(APIView):

    """
    Not used as of now - API used to create zoom meeting.
    Args:
        domain - Domain of the company
    Body:
        topic - Topic/title of the meeting
        start_date - start date of the meeting in zoom specific format
        start_time - start time of the meeting in zoom specific format
    Returns:
        -success message with meeting_link(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Not used as of now - Create Zoom Meeting API",
        operation_summary="Not used as of now - Create Zoom Meeting API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "topic": openapi.Schema(type=openapi.TYPE_STRING),
                "start_date": openapi.Schema(type=openapi.TYPE_STRING),
                "start_time": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        try:
            data = request.data
            response = {}
            try:
                meeting_url = createMeeting(data.get("topic"), data.get("start_date"), data.get("start_time"))
                response["msg"] = "success"
                response["meeting_link"] = meeting_url
                return Response(response, status=drf_status.HTTP_201_CREATED)
            except Exception as e:
                response["msg"] = "error"
                response["error"] = str(e)
                return Response(response, status=drf_status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)


class GetMSTAuthUrl(APIView):
    def get(self, request):
        try:
            endpoint = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?response_type=code"
            redirect_url = "https://infertalent.com/auth/redirect-url/teams"
            response_mode = "query"
            scope = "OnlineMeetings.ReadWrite.All"
            client_id = settings.MST_CLIENT_ID
            url = endpoint + "&redirect_url={}&response_mode={}&scope={}&client_id={}".format(redirect_url, response_mode, scope, client_id)
            response = {}
            response["url"] = url
            return Response(response, status=drf_status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"msg": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)


class GetGoogleAuthUrl(APIView):

    """
    API used to add calendly details i.e Personal Access Token.
    Args:
        domain - Domain of the company
    Body:
        applied_position_id - applied_id of the applied position
        startTime - start time of the meeting
        endTime - end time of the meeting
        timezone - timezone
        title - title
        candidate_email - email of the candidate
    Returns:
        -success message with auth url(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Get Google Authorization URL API",
        operation_summary="Get Google Authorization URL API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "applied_position_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "startTime": openapi.Schema(type=openapi.TYPE_STRING),
                "endTime": openapi.Schema(type=openapi.TYPE_STRING),
                "timezone": openapi.Schema(type=openapi.TYPE_STRING),
                "title": openapi.Schema(type=openapi.TYPE_STRING),
                "candidate_email": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        try:
            cred_path = os.path.abspath(os.path.join(settings.BASE_DIR, "client_secret.json"))
            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(cred_path, scopes=SCOPES)
            # flow.redirect_uri = 'http://localhost:8080/oauth/callback/1'
            flow.redirect_uri = "https://{}/oauth/callback/1".format(settings.BE_DOMAIN_NAME)
            authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
            response = {}
            response["msg"] = "success"
            response["url"] = authorization_url
            response["state"] = state
            parsed_url = urlparse(authorization_url)
            state = parse_qs(parsed_url.query)["state"][0]
            date = request.data.get("date")
            # get applied position
            applied_position = AppliedPosition.objects.filter(id=request.data.get("applied_position_id")).last()
            # Create meeting data for later use
            MeetingData.objects.create(
                state=state,
                start_time="{}T{}".format(date, request.data.get("startTime")),
                end_time="{}T{}".format(date, request.data.get("endTime")),
                timezone=request.data.get("timezone"),
                interview_title=request.data.get("title"),
                candidate_email=request.data.get("candidate_email"),
                applied_position=applied_position,
            )
            return Response(response, status=drf_status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)


def GoogleOAuthRedirect(request):
    try:
        data = request.GET
        code = data.get("code")
        state = data.get("state")
        scope = data.get("scope")
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file("client_secret.json", scopes=SCOPES, state=state)
        # flow.redirect_uri = 'http://localhost:8080/oauth/callback/1'
        flow.redirect_uri = "https://{}/oauth/callback/1".format(settings.BE_DOMAIN_NAME)

        # authorization_response = request.build_absolute_uri()
        # building demo url to extract auth resp
        authorization_response = "https://infertalent.com/oauth/callback/1?state={}&code={}".format(state, code)
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        service = build("calendar", "v3", credentials=credentials)
        meeting_data = MeetingData.objects.filter(state=state).last()
        if meeting_data:
            event = {
                "conferenceDataVersion": 1,
                "summary": meeting_data.interview_title,
                "start": {
                    "dateTime": meeting_data.start_time + ":00",
                    "timeZone": meeting_data.timezone,
                },
                "end": {
                    "dateTime": meeting_data.end_time + ":00",
                    "timeZone": meeting_data.timezone,
                },
                "attendees": [
                    {"email": meeting_data.candidate_email},
                ],
                "conferenceData": {"createRequest": {"requestId": "sample123", "conferenceSolutionKey": {"type": "hangoutsMeet"}}},
            }
            event = service.events().insert(calendarId="primary", body=event, sendNotifications="true", conferenceDataVersion=1).execute()
            link = event.get("hangoutLink")
            sent = send_meeting_link(link, state)
            if sent:
                applied_position = meeting_data.applied_position
                applied_position.data["meeting_link"] = link
                applied_position.save()
                return render(request, "meeting_created.html")
            else:
                HttpResponse("Meeting not created. meeting data not found. State is {}".format(state))
        else:
            return HttpResponse("Meeting not created. meeting data not found. State is {}".format(state))
    except Exception as e:
        return HttpResponse("Something went wrong - {}".format(str(e)))


class CreateZoomMeeting(APIView):
    def post(self, request):
        try:
            title = request.data.get("title")
            start_date = request.data.get("start_time")
            start_time = request.data.get("start_time")
            start_time = "{}T{}:00Z".format(start_date, start_time)
            htm_id = request.data.get("htm_id")
            htm = Profile.objects.get(id=htm_id).user
            attendees = request.data.get("attendees")
            data = create_zoom_meeting(htm, title, start_time, attendees)
            return Response(data, status=drf_status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg": "some error coccured", "error": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)
