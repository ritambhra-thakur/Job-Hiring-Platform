from django.db import models

from company.models import Company


def get_json_default():
    return {}


class WebhookTestData(models.Model):
    data = models.JSONField(default=get_json_default)
    msg = models.CharField(default="No Message", max_length=255, null=True, blank=True)
