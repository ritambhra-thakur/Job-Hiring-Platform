from django.urls import path

from . import views

app_name = "video_interview"

urlpatterns = [
    path("api/v1/create-zoom-meeting/", views.CreateZoomMeetingView.as_view()),
    path("api/v1/get-mst-authurl/", views.GetMSTAuthUrl.as_view()),
    path("api/v1/get-meet-authurl/", views.GetGoogleAuthUrl.as_view()),
    path("api/v1/create-meet/", views.CreateCalendarEventForInterview.as_view()),
    path("api/v1/create-zoom-meet/", views.CreateZoomMeeting.as_view()),
]
