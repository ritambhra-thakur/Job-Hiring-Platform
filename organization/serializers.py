from email.mime import application

from msrest import Serializer
from rest_framework import serializers

import primary_data.models as PrimaryDataModels
from app.util import encryption
from form.models import AppliedPosition
from user.models import User
from user.serializers import *

from .models import Organization


# TODO: Code clean up Pending
class OrganizationSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"

    def get_total_hired(self, obj):
        hired_count = 0
        for org in obj.office:
            hired_count = AppliedPosition.objects.filter(
                application_status="hired", company=obj.company, form_data__form_data__location=org.country
            ).count()
        return hired_count

    def get_company_name(self, obj):
        return obj.company.company_name


class GetOrganizationSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField(read_only=True)
    # org_employee_id = serializers.SerializerMethodField(read_only=True)
    # country = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"

    def get_total_hired(self, obj):
        hired_count = AppliedPosition.objects.filter(application_status="hired", company=obj.company).count()
        return hired_count

    def get_company_name(self, obj):
        return obj.company.company_name

    # def get_country(self, obj):
    #     try:
    #         country_obj = PrimaryDataModels.Country.objects.get(name=obj.country)
    #         return [{"label": obj.country, "value": country_obj.id}]
    #     except:
    #         return []

    # def get_org_employee_id(self, obj):
    #     if obj.org_employee_id.id:
    #         return [{"label":obj.org_employee_id.first_name, "value": obj.org_employee_id.id}]
    #     else:
    #         return []
