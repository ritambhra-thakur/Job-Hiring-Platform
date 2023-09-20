from django.db import models


# Create your models here.
class Affinda(models.Model):
    """
    Affinda class created in model and fields are added to upload media, media name, field name
    eith unicode functions
    """

    file = models.FileField(upload_to="media/", blank=True, null=True, help_text="Select file")
    file_name = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        help_text="Enter the file name",
    )
    field_name = models.CharField(max_length=250, blank=True, null=True, help_text="Enter field name")
    file_type = models.CharField(max_length=120, blank=True, null=True, help_text="Enter file type")
    is_active = models.BooleanField(default=True, help_text="Select your prefrences")
    is_deleted = models.BooleanField(default=False, help_text="Select your prefrences")
    can_delete = models.BooleanField(default=True, help_text="Select your prefrences")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Select your prefrences")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated time")

    # history = HistoricalRecords(table_name="media_history")

    def __unicode__(
        self,
    ):  # get a bunch of garbage that is not really informative.
        return self.id  # id will show who use this function


class AffindaSkill(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
