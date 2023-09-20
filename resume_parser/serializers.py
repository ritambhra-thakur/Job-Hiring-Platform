
from rest_framework import serializers

from .models import Affinda


class AffindaSerializer(serializers.ModelSerializer):
    """
    AffindaSerializer class is created with Affinda Model and added
    all field from AffindaSerializer Model
    """

    class Meta:
        model = Affinda
        fields = "__all__"
        read_only_fields = ('file_name','field_name','file_type','is_active', 'is_deleted', "can_delete", "created_at", "updated_at")
        extra_kwargs = {
            "file": {'write_only': True}
        }



