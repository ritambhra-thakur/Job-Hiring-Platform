from django.urls import path

from . import views

app_name = "notification"
urlpatterns = [ 
    path('', views.index, name='index'),
    path('<str:room_name>/<str:token>/', views.room, name='room'),
    path('notification/save/', views.save_notification, name='room'),

    path("api/v1/list/", views.GetAllNotifications.as_view()),
    path("api/v1/get/<int:pk>/", views.GetNotifications.as_view()),
    path("api/v1/create/", views.CreateNotifications.as_view()),
    path("api/v1/update/<int:pk>/", views.UpdateNotifications.as_view()),
    path("api/v1/delete/<int:pk>/", views.DeleteNotifications.as_view()),
    path("api/v1/notification-type/", views.NotificationTypeView.as_view()),
    path("api/v1/clear-notification/", views.ClearNotification.as_view()),
]
