import datetime
import os

from django.db import models
from django.utils.text import slugify
from django_extensions.db.fields import AutoSlugField

from app.choices import FEATURE_CHOICES

# from simple_history.models import HistoricalRecords

# Create your models here.
# function for company logo


def get_default_options():
    return []


def upload_company_logo(instance, filename):
    """
    function created to upload the company logo with the help of instance split extention fields
    """
    extension = filename.split(".")[-1]  # filename
    new_name = str(datetime.datetime.now()).split(".")[0].replace(" ", "_")  # doubt
    new_name = new_name + "." + extension  # doubt
    return os.path.join("company_logo", str(instance.id), str(new_name))


class Company(models.Model):
    """
    company model class is created to add company name and details like domain,host,
    owner, active and created history
    """

    id = models.AutoField(primary_key=True, help_text="identity for company model")
    form_id = models.IntegerField(default=0)
    offer_id = models.IntegerField(default=0)
    company_name = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        unique=True,
        help_text="Enter Company Name",
        error_messages={"unique": "Company with this name already exist in the system, please use another name."},
    )
    url_domain = models.CharField(
        max_length=250,
        unique=True,
        help_text="Company Domain Name",
        error_messages={"unique": "Company with this url domain already exist in the system, please use another url domain."},
    )
    company_host = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Enter Host Name for infertalent product",
    )
    company_url = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        default=None,
        help_text="Enter the website link of the company",
    )
    slug = AutoSlugField(populate_from=["company_name"])  # company host

    logo = models.FileField(default=None, null=True, blank=True, upload_to=upload_company_logo)
    company_owner = models.ForeignKey(
        "user.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="company_owner",
        help_text="Enter the Company owner ",
    )

    industry = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        default=None,
        help_text="Enter the industry of the company",
    )
    no_of_emp = models.CharField(max_length=255, default=None, blank=True, null=True)
    tnc = models.TextField(default=None, null=True, blank=True)
    policy = models.TextField(default=None, null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="   ")  # model with true boolean field
    is_deleted = models.BooleanField(default=False, help_text="Check this box to delete the user")  # model with false boolean field

    # history = HistoricalRecords(table_name="company_history")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date and time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        value = self.company_name[0:250]
        self.slug = slugify(value, allow_unicode=True)
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            pass
            # create all the fields


class Department(models.Model):
    id = models.AutoField(primary_key=True, help_text="identity for department model")
    department_name = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Enter Department Name",
    )
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date and time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")


class GPRRDocsAndPolicy(models.Model):
    """
    Model to store the docs and policy contents mainly for voluntary disclosure
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    topic = models.TextField()
    options = models.JSONField(default=get_default_options, null=True, blank=True)
    option_type = models.CharField(max_length=250, default="options", null=True, blank=True)
    content = models.TextField(null=True, blank=True, default=None)


class FeaturesEnabled(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    feature = models.CharField(max_length=255, choices=FEATURE_CHOICES, default="---")
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return "{} - {}".format(self.company.company_name, self.feature)

    class Meta:
        verbose_name_plural = "Features"


class ServiceProviderCreds(models.Model):

    """
    Model to store the credentials of the different services app
    like Calendly, Google Calendar and all
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    calendly = models.JSONField(default=get_default_options, null=True, blank=True)
    docusign = models.JSONField(default=get_default_options, null=True, blank=True)
    zoom = models.JSONField(default=get_default_options, null=True, blank=True)
    from_email = models.JSONField(default=get_default_options, null=True, blank=True)
    # add more if needed
