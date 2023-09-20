from django.db import models

from company.models import Company


def get_json_default():
    return [{}]


# Create your models here.
class JobSites(models.Model):
    """
    JobSites Model class is created with fields to add Jobsite
    """

    job_site = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Enter Job Site",
    )
    job_ads_inventory = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Enter Job Ads Inventory",
    )
    resume_search_inventory = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Enter Search Inventory",
    )
    package_start_date = models.DateField(default=None, null=True, blank=True)
    package_end_date = models.DateField(default=None, null=True, blank=True)
    country = models.JSONField(default=get_json_default)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_site_company",
        help_text="Choose your company name",
    )
    is_active = models.BooleanField(default=True, help_text="Select your preferences")
    is_deleted = models.BooleanField(default=False, help_text="Select your preferences")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date and time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.job_site
