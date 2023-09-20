from rest_framework import serializers

from form.serializers import FormDataSerializer, GetFormDataSerializer
from user.serializers import GetProfileSerializer
from app.encryption import encrypt
from .models import *


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = "__all__"
        read_only_fields = [
            "slug",
        ]


class AttributeListSerializer(serializers.ModelSerializer):
    competency = serializers.SerializerMethodField()

    def get_competency(self, obj):
        return str(obj.attribute.all()[0])

    class Meta:
        model = Attribute
        fields = "__all__"
        read_only_fields = [
            "slug",
        ]


class CompetencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Competency
        fields = "__all__"
        read_only_fields = [
            "slug",
        ]


class CompetencyListSerializer(serializers.ModelSerializer):
    attribute = AttributeSerializer(many=True, read_only=True)

    class Meta:
        model = Competency
        fields = "__all__"
        read_only_fields = [
            "slug",
        ]


# class PositionAttributeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PositionAttribute
#         fields = "__all__"
#         read_only_fields = [
#             "slug",
#         ]


# class PositionAttributeListSerializer(serializers.ModelSerializer):
#     attribute = AttributeListSerializer(read_only=True, many=True)

#     class Meta:
#         model = PositionAttribute
#         fields = "__all__"
#         read_only_fields = [
#             "slug",
#         ]


class PositionCompetencyAndAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionCompetencyAndAttribute
        fields = "__all__"


class GetPositionCompetencyAndAttributeSerializer(serializers.ModelSerializer):
    # position = FormDataSerializer(read_only=True)
    competency = CompetencySerializer(read_only=True)
    attribute = AttributeSerializer(read_only=True, many=True)

    class Meta:
        model = PositionCompetencyAndAttribute
        fields = "__all__"


class PositionScoreCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionScoreCard
        fields = "__all__"


class ListPositionScoreCardSerializer(serializers.ModelSerializer):
    position = GetFormDataSerializer()
    interviewer_profile = GetProfileSerializer()
    applied_profiles = GetProfileSerializer()
    competency = CompetencyListSerializer()
    attribute = AttributeListSerializer()

    class Meta:
        model = PositionScoreCard
        fields = "__all__"


class OverAllRatingDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverAllRatingDashboard
        fields = "__all__"
