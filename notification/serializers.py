# from django.contrib.auth.models import Permission
from rest_framework import serializers

import primary_data.serializers as PrimaryDataSerializer

from .models import Notifications


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notifications
        fields = "__all__"
