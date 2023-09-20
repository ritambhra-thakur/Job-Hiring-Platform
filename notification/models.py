import json
from datetime import timedelta
from operator import mod

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.humanize.templatetags import humanize
from django.db import models

# Create your models here.
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from rest_framework import serializers

from user.models import User


def json_default():
    return {}


class ChatMessages(models.Model):
    """
    class EmailTemplate is created to add the email templates with template fields
    """

    group_name = models.CharField(max_length=100, null=True, blank=True)
    message = models.CharField(max_length=500, null=True, blank=True)
    socket_desc = models.CharField(max_length=500, null=True, blank=True)

    is_active = models.BooleanField(default=True, help_text="user is active")
    is_deleted = models.BooleanField(default=False, help_text="to delete the user")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.group_name


class Notifications(models.Model):
    """
    class EmailTemplate is created to add the email templates with template fields
    """

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="user_notifications")
    title = models.CharField(max_length=500, null=True, blank=True)
    body = models.CharField(max_length=500, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    event_type = models.CharField(max_length=255, default=None, null=True, blank=True)  # type of notification i.e offer approval, position approval
    redirect_slug = models.CharField(max_length=500, default=None, null=True, blank=True)
    additional_info = models.JSONField(default=json_default)
    is_active = models.BooleanField(default=True, help_text="user is active")
    is_deleted = models.BooleanField(default=False, help_text="to delete the user")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class NotificationType(models.Model):
    """
    Model to store all the different types of notifications.
    It also stores if the notification needs to be sent or not.
    """

    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)
    is_active = models.BooleanField()

    def __str__(self):
        return self.name


class NotificationSerializer(serializers.ModelSerializer):
    time_ago = serializers.SerializerMethodField(read_only=True)
    sposition_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Notifications
        fields = "__all__"

    def get_time_ago(self, obj):
        updated_at = obj.created_at + timedelta(minutes=23)
        return humanize.naturaltime(updated_at)

    def get_sposition_id(self, obj):
        if "form_data" in obj.additional_info and "show_id" in obj.additional_info["form_data"]:
            return obj.additional_info["form_data"]["show_id"]
        else:
            return None


@receiver(post_save, sender=Notifications)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        serializer = NotificationSerializer(instance)
        data = json.dumps(serializer.data)
        g_name = "chat_" + str(instance.user.id)
        async_to_sync(channel_layer.group_send)(
            g_name,
            {"type": "chat_message", "message": data},
        )
