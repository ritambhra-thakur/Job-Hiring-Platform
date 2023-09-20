from rest_framework import serializers

from form.models import AppliedPosition
from form.serializers import FormDataListSerializer, GetFormDataSerializer
from scorecard.serializers import *
from user.serializers import ProfileScoreCardSerializer, ProfileSerializer

from .models import *


class PipelineSerializer(serializers.ModelSerializer):
    """
    PipelineSerializer class is created with Pipeline Model and added
    all field from PipelineSerializer Model
    """

    class Meta:
        model = Pipeline
        fields = "__all__"


class StageSerializer(serializers.ModelSerializer):
    """
    StageSerializer class is created with Stage Model and added
    all field from StageSerializer Model
    """

    isDragDisabled = serializers.SerializerMethodField()

    class Meta:
        model = Stage
        fields = "__all__"

    def get_isDragDisabled(self, obj):
        if obj.is_mandatory is True and obj.pipeline.pipeline_name == "Hiring Stage":
            return True
        else:
            return False


class PositionStageSerializer(serializers.ModelSerializer):
    """
    PositionStageSerializer class is created with PositionStage Model and added
    all field from PositionStageSerializer Model
    """

    class Meta:
        model = PositionStage
        fields = "__all__"


class PositionStageListSerializer(serializers.ModelSerializer):
    """
    PositionStageSerializer class is created with PositionStage Model and added
    all field from PositionStageSerializer Model
    """

    profiles = serializers.SerializerMethodField()
    competency = GetPositionCompetencyAndAttributeSerializer(read_only=True, many=True)
    position = FormDataSerializer(read_only=True)
    stage = StageSerializer(read_only=True)
    position_stage_count = serializers.SerializerMethodField()

    class Meta:
        model = PositionStage
        fields = "__all__"

    def get_position_stage_count(self, obj):
        position_count = AppliedPosition.objects.filter(data__position_stage_id=obj.id).count()
        return position_count

    def get_profiles(self, obj):
        ids = obj.profiles.all().values_list("id")
        candidate_id = self.context.get("candidate_id")
        position_id = obj.position.id
        position_stage_id = obj.stage.id
        context = {"candidate_id": candidate_id, "position_id": position_id, "position_stage_id": position_stage_id}
        data = Profile.objects.filter(id__in=ids)
        data = data.prefetch_related("user")
        return ProfileScoreCardSerializer(data, many=True, context=context).data
