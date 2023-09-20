from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models.fields import NullBooleanField
from django.utils.text import slugify
from django_extensions.db.fields import AutoSlugField

from company.models import Company
from form.models import AppliedPosition, FormData
from user.models import Profile


class Attribute(models.Model):
    """
    this model contains attribute created by site admin
    """

    attribute_name = models.CharField(max_length=150, null=True, blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attribute_company",
    )
    slug = AutoSlugField(populate_from=["attribute_name", "company"])

    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    # history = HistoricalRecords(table_name="attributes_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.attribute_name

    # update the slug field when UpdateAttributes API is hit.
    def save(self, *args, **kwargs):
        value = self.attribute_name[0:250] + "-" + str(self.company)
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)


class Competency(models.Model):
    """
    this model contains competency created by admin and group of attribute
    """

    competency = models.CharField(max_length=150, null=True, blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="competency_company",
    )
    attribute = models.ManyToManyField(
        Attribute,
        related_name="attribute",
        blank=True,
        help_text="group attribute to competency",
    )
    slug = AutoSlugField(populate_from=["competency", "company"])

    # history = HistoricalRecords(table_name="competency_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.competency

    def save(self, *args, **kwargs):
        value = self.competency[0:250] + "-" + str(self.company)
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)


# class PositionAttribute(models.Model):
#     """
#     model contains attribute list belongs to position
#     """

#     position = models.ForeignKey(FormData, on_delete=models.CASCADE, blank=True, null=True, related_name="score_card_position_attribute")
#     # attribute = models.ManyToManyField(Attribute, blank=True)
#     company = models.ForeignKey(
#         Company,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="position_attribute_company",
#     )
#     slug = AutoSlugField(populate_from=["position", "company"])
#     # history = HistoricalRecords(table_name="position_attribute_history")
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __unicode__(self):
#         return self.id

#     # update the slug field when UpdateScoreCard API is hit.
#     def save(self, *args, **kwargs):
#         value = str(self.position) + "-" + str(self.company)
#         self.slug = slugify(value, allow_unicode=True)
#         super().save(*args, **kwargs)


class PositionCompetencyAndAttribute(models.Model):
    """Position dashboard ScoreCard selection

    Args:
        models (_type_): _description_
    """

    position = models.ForeignKey(FormData, on_delete=models.CASCADE)
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE)
    attribute = models.ManyToManyField(Attribute, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.competency.competency


class PositionScoreCard(models.Model):
    """Scorecard rating from every single user

    Args:
        models (_type_): _description_
    """

    position = models.ForeignKey(FormData, on_delete=models.CASCADE)
    interviewer_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="position_scorecard_interviewer_profile",
        help_text="user profile list who are going to interviewing this position stage",
    )
    applied_profiles = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="position_scorecard_applied_profiles",
        help_text="user profile list who is applied to that specific position",
    )
    position_stage = models.ForeignKey("stage.stage", on_delete=models.CASCADE, blank=True, null=True)
    competency = models.ForeignKey(
        Competency,
        on_delete=models.CASCADE,
        blank=True,
        help_text="competency list to that specific position",
    )
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, blank=True)
    rating = models.IntegerField(help_text="Enter rating out of 5")
    comment = models.TextField(blank=True, null=True, help_text="scorecard comment")


class OverAllRatingDashboard(models.Model):
    """OverAllRatingDashboard

    Args:
        models (_type_): _description_
    """

    applied_position = models.ForeignKey(AppliedPosition, on_delete=models.CASCADE)
    interviewer_id = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="Candidate_position",
        help_text="Enter applied position",
    )
    candidate_id = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="candidate_id",
        help_text="Enter Candidate ID",
    )
    data = models.JSONField()
    is_active = models.BooleanField(default=True, help_text="   ")
    is_deleted = models.BooleanField(default=False, help_text="Check this box to delete the CandidatePositionDashboard")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date and time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")
