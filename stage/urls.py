from django.urls import path

from stage import views

from .views import *

app_name = "stage"

urlpatterns = [
    # Pipeline
    path("pipeline/api/v1/list/", GetAllPipeline.as_view()),
    path("pipeline/api/v1/create/", CreatePipeline.as_view()),
    path("pipeline/api/v1/get/<int:pk>/", GetPipeline.as_view()),
    path("pipeline/api/v1/update/<int:pk>/", UpdatePipeline.as_view()),
    path("pipeline/api/v1/delete/<int:pk>/", DeletePipeline.as_view()),
    # Stage
    path("api/v1/list/", GetAllStage.as_view()),
    path("api/v1/create/", CreateStage.as_view()),
    path("api/v1/get/<int:pk>/", GetStage.as_view()),
    path("api/v1/update/<int:pk>/", UpdateStage.as_view()),
    path("api/v1/delete/<int:pk>/", DeleteStage.as_view()),
    # Position
    path("positionstage/api/v1/list/", GetAllPositionStage.as_view()),
    path("positionstage/api/v1/create/", CreatePositionStage.as_view()),
    path("positionstage/api/v1/get/<int:pk>/", GetPositionStage.as_view()),
    path("positionstage/api/v1/update/<int:pk>/", UpdatePositionStage.as_view()),
    path("positionstage/api/v1/delete/<int:pk>/", DeletePositionStage.as_view()),
    path("positionstage/api/v1/delete_by_position_id/<int:pk>/", DeleteStagesByPositionId.as_view()),
]
