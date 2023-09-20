from rest_framework import serializers

from custom_reports.models import CustomReport


class CustomReportSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = CustomReport
