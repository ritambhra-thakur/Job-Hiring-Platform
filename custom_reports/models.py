from django.db import models

from user.models import User


def get_json_default():
    return []


class CustomReport(models.Model):
    report_name = models.CharField(max_length=100)
    report_type = models.CharField(max_length=50)
    selected_fields = models.JSONField(default=get_json_default, help_text="List of selected fields name")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    updated_at = models.DateTimeField(auto_now=True)
