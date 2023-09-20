from dataclasses import fields

from rest_framework import serializers

from company.serializers import *

from .models import EmailTemplate, TemplateType


class EmailTemplatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = "__all__"


class TemplateTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateType
        fields = "__all__"
