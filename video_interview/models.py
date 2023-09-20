from django.db import models

from form.models import AppliedPosition


class MeetingData(models.Model):
    state = models.CharField(max_length=250)
    start_time = models.CharField(max_length=250)
    end_time = models.CharField(max_length=250)
    timezone = models.CharField(max_length=250)
    interview_title = models.CharField(max_length=250)
    candidate_email = models.CharField(max_length=250)
    applied_position = models.ForeignKey(AppliedPosition, on_delete=models.SET_NULL, null=True, blank=True, default=None)
