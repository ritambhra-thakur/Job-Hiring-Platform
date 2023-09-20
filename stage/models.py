from operator import imod

from django.db import models
from django.utils.text import slugify
from django_extensions.db.fields import AutoSlugField

from company.models import Company
from form.models import FormData
from scorecard.models import PositionCompetencyAndAttribute
from user.models import Profile

# from simple_history.models import HistoricalRecords


# Create your models here.
class Pipeline(models.Model):
    """
    Pipeline model is group of Hiring Stages
    to that specific company
    """

    pipeline_name = models.CharField(max_length=150, help_text="Enter name of your pipeline")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="company_pipeline",
        help_text="Choose your Country name",
    )
    # TODO: Update all slug field with company
    slug = AutoSlugField(populate_from=["pipeline_name", "company"])
    sort_order = models.IntegerField(default=1, help_text="Sort by")
    description = models.TextField(blank=True, null=True, help_text="Add description")
    is_active = models.BooleanField(default=True, help_text="Select your preferences")
    is_deleted = models.BooleanField(default=False, help_text="Select your preferences")

    # history = HistoricalRecords(table_name="pipeline_history")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created datetime")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated datetime")

    def __str__(self):
        return self.pipeline_name

    # update the slug field when UpdatePipeline API is hit.
    def save(self, *args, **kwargs):
        value = self.pipeline_name[0:250] + "-" + str(self.company)
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)


class Stage(models.Model):
    """
    Stage model class is created to add sort order, desc, pipeline with fields
    """

    stage_name = models.CharField(max_length=150, help_text="Enter stage name")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="stage_pipeline",
        help_text="Choose your Country name",
    )
    # TODO: Update all slug field with company
    slug = AutoSlugField(populate_from=["stage_name", "company"])
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="stage_pipeline",
        help_text="Choose type of pipeline",
    )
    is_interview = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=1, help_text="Sort by")
    description = models.TextField(blank=True, null=True, help_text="Add description")
    is_mandatory = models.BooleanField(default=False, help_text="Select your preferences")
    is_active = models.BooleanField(default=True, help_text="Select your preferences")
    is_deleted = models.BooleanField(default=False, help_text="Select your preferences")

    # history = HistoricalRecords(table_name="stage_history")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.stage_name

    # update the slug field when UpdateStage API is hit.

    # save function is created to save the stage model fields
    def save(self, *args, **kwargs):
        value = self.stage_name[0:250] + "-" + str(self.company)
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)


class PositionStage(models.Model):
    """
    model contains data related to jobpost stage details
    """

    position = models.ForeignKey(FormData, on_delete=models.CASCADE)
    stage = models.ForeignKey(
        Stage,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="job_stage_pipeline",
        help_text="stage for specific job",
    )
    sort_order = models.IntegerField(default=1, help_text="Sort by")

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="stage_pipeline_company",
        help_text="Choose your Country name",
    )

    profiles = models.ManyToManyField(
        Profile,
        related_name="positing_stage_profiles",
        blank=True,
        help_text="user profile list who are going to interviewing this position stage",
    )

    competency = models.ManyToManyField(
        PositionCompetencyAndAttribute,
        related_name="positing_stage_competency",
        blank=True,
        help_text="attributes list to that specific position",
    )
    slug = AutoSlugField(populate_from=["position", "company", "stage"])

    # history = HistoricalRecords(table_name="job_stage_pipeline_history")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")
