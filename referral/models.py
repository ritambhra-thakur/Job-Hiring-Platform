import datetime
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify
from django_extensions.db.fields import AutoSlugField

from company.models import Company
from form.models import FormData, JobCategory
from primary_data.models import Country, State
from user.models import Media


class Currency(models.Model):
    """
    Currency class is created to add the currency of every country
    """

    currency_name = models.CharField(max_length=100, unique=True, help_text="Enter the name of Currency")
    slug = AutoSlugField(populate_from=["currency_name"])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "currency"

    def __str__(self):
        return self.currency_name


# Create your models here.
class ReferralPolicy(models.Model):
    """
    TODO: update this model with ReferralPolicy
    Referral class is created to check the referral details and fields
    added in it
    """

    referral_name = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=True,
        help_text="Enter Referral Name",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.RESTRICT,
        help_text="Choose your Country",
        null=True,
        blank=True,
        default=None,
    )
    state = models.ForeignKey(
        State,
        on_delete=models.RESTRICT,
        help_text="Enter your Region",
        null=True,
        blank=True,
        default=None,
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.RESTRICT,
        help_text="Company domain",
    )
    level = models.CharField(max_length=40, help_text="choose your level", null=True, blank=True, default=None)
    job_code = models.CharField(max_length=20, help_text="Enter job code", null=True, blank=True, default=None)
    position_tittle = models.CharField(max_length=30, help_text="Enter Position tittle", null=True, blank=True, default=None)
    positions = models.ManyToManyField(FormData, null=True, blank=True, default=None)
    job_categories = models.ManyToManyField(JobCategory, null=True, blank=True, default=None)
    currency = models.ForeignKey(Currency, on_delete=models.RESTRICT, help_text="Choose Currency type", null=True, blank=True, default=None)
    referral_amount = models.IntegerField(help_text="Enter Referral Amount", null=True, blank=True, default=None)
    referral_rate_start_date = models.DateField(blank=True, null=True, default=None)
    referral_rate_end_date = models.DateField(blank=True, null=True, default=None)
    country_payout_policy = models.CharField(max_length=1000, help_text="Enter Referral Policy", null=True, blank=True, default=None)
    attach_referral_policy_document = models.FileField(upload_to="media/", blank=True, null=True, help_text="Select file", default=None)

    is_approve = models.BooleanField(default=False)
    slug = AutoSlugField(
        populate_from=[
            "referral_name",
            "company",
            "country",
        ]
    )
    is_active = models.BooleanField(default=True, help_text="user is active")
    is_deleted = models.BooleanField(default=False, help_text="to delete the user")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.referral_name
