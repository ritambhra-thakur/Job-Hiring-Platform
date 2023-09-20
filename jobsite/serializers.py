from pyexpat import model
from django.contrib.auth.models import Permission
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import JobSites


# TODO: Code clean up Pending
class JobSitesSerializer(serializers.ModelSerializer):
    """
    JobSitesSerializer class is created with JobSites Model and added
    fields from JobSitesSerializer Model
    """

    class Meta(object):
        model = JobSites
        fields = "__all__"

