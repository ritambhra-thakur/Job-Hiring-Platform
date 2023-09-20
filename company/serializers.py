from dataclasses import field, fields

from pyexpat import model
from rest_framework import serializers

from .models import Company, Department, GPRRDocsAndPolicy


class CompanySerializer(serializers.ModelSerializer):
    """
    Class company serializer with all fields from  company model
    """

    class Meta:
        model = Company
        fields = "__all__"


class CompanyIdSerializer(serializers.ModelSerializer):
    """
    Class company serializer with id fields from  company model
    """

    class Meta:
        model = Company
        fields = ["id"]


class DepartmentSerializer(serializers.ModelSerializer):
    """
    class DepartmentSerializer is created with id, department_name, desription from
    company model
    """

    class Meta:
        model = Department
        fields = "__all__"


class DepartmentCsvSerializer(serializers.ModelSerializer):
    """
    DepartmentCSVSerializer class is created with user Model and added
    all fields from the DepartmentCSVSerializer
    """

    class Meta:
        model = Department
        fields = [
            "id",
            "department_name",
            "description",
        ]


class GPRRDocsAndPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = GPRRDocsAndPolicy
        fields = '__all__'
