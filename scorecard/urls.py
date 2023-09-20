from django.urls import path

from .views import *

app_name = "scorecard"

urlpatterns = [
    # Attribute
    path("attribute/api/v1/list/", GetAllAttribute.as_view()),
    path("attribute/api/v1/create/", CreateAttribute.as_view()),
    path("attribute/api/v1/get/<int:pk>/", GetAttribute.as_view()),
    path("attribute/api/v1/update/<int:pk>/", UpdateAttribute.as_view()),
    path("attribute/api/v1/delete/<int:pk>/", DeleteAttribute.as_view()),
    # Competency
    path("competency/api/v1/list/", GetAllCompetency.as_view()),
    path("competency/api/v1/op-list/", GetAllOpCompetency.as_view()),
    path("competency/api/v1/create/", CreateCompetency.as_view()),
    path("competency/api/v1/get/<int:pk>/", GetCompetency.as_view()),
    path("competency/api/v1/update/<int:pk>/", UpdateCompetency.as_view()),
    path("competency/api/v1/delete/<int:pk>/", DeleteCompetency.as_view()),
    # PositionAttribute
    # path("position_attribute/api/v1/list/", GetAllPositionAttribute.as_view()),
    # path("position_attribute/api/v1/create/", CreatePositionAttribute.as_view()),
    # path(
    #     "position_attribute/api/v1/get/<int:pk>/",
    #     GetPositionAttribute.as_view(),
    # ),
    # path(
    #     "position_attribute/api/v1/update/<int:pk>/",
    #     UpdatePositionAttribute.as_view(),
    # ),
    # path(
    #     "position_attribute/api/v1/delete/<int:pk>/",
    #     DeletePositionAttribute.as_view(),
    # ),
    # CSV Export
    path(
        "competency/api/v1/export/csv/<str:company_id>/",
        CompetencyCSVExport.as_view(),
    ),
    # PositionCompetencyAndAttribute
    path("Positioncompetencyattribute/api/v1/list/", GetAllPositionCompetencyAndAttribute.as_view()),
    path("Positioncompetencyattribute/api/v1/create/", CreatePositionCompetencyAndAttribute.as_view()),
    path("Positioncompetencyattribute/api/v1/get/<int:pk>/", GetPositionCompetencyAndAttribute.as_view()),
    path("Positioncompetencyattribute/api/v1/update/<int:pk>/", UpdatePositionCompetencyAndAttribute.as_view()),
    path("Positioncompetencyattribute/api/v1/delete/<int:pk>/", DeletePositionCompetencyAndAttribute.as_view()),
    # PostionScoreCard
    path("positionscorecard/api/v1/list/", GetAllPostionScoreCard.as_view()),
    path("positionscorecard/api/v1/pending/list/<str:pk>/", GetAllPendingPostionScoreCard.as_view()),
    path("positionscorecard/api/v1/pending/op-list/<str:pk>/", GetAllOpPendingPostionScoreCard.as_view()),
    path("positionscorecard/api/v1/pending/op-list-open/<str:pk>/", GetAllOpPendingPostionScoreCardOpen.as_view()),
    path("positionscorecard/api/v1/pending-decision/list/<str:pk>/", GetAllPendingDecision.as_view()),
    path("positionscorecard/api/v1/pending-decision/op-list/<str:pk>/", GetAllOpPendingDecision.as_view()),
    path("positionscorecard/api/v1/pending-offer/list/<str:pk>/", GetAllPendingOffer.as_view()),
    path("positionscorecard/api/v1/pending-offer/op-list/<str:pk>/", GetAllOpPendingOffer.as_view()),
    # Count
    path("positionscorecard/api/v1/All-pending-count/<str:pk>/", GetAllPendingCount.as_view()),
    # positionscorecard
    path("positionscorecard/api/v1/create/", CreatePositionScoreCard.as_view()),
    path("positionscorecard/api/v1/get/<int:pk>/", GetPostionScoreCard.as_view()),
    path("positionscorecard/api/v1/update/<int:pk>/", UpdatePositionScoreCard.as_view()),
    path("positionscorecard/api/v1/delete/<int:pk>/", DeletePostionScoreCard.as_view()),
    path("positionscorecard/api/v1/get-by-applied-position/<int:pk>/", GetScorecardByAppliedPosition.as_view()),
    #
    path("scorecardemail/api/v1/send/<int:interview_id>/", SendScorecardEmail.as_view()),
    # Overall Ratings
    path("OverallRating/api/v1/list/", GetAllRatings.as_view()),
    path("OverallRating/api/v1/create/", CreateRatings.as_view()),
    path("OverallRating/api/v1/get/<int:applied_position>/<str:interviwer>/<int:candidate>/", GetRatings.as_view()),
    path("OverallRating/api/v1/update/<int:applied_position>/<str:interviwer>/<int:candidate>/", UpdateRatings.as_view()),
    path("OverallRating/api/v1/delete/<int:pk>/", DeleteRatings.as_view()),
]
