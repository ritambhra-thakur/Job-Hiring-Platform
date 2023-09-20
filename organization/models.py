from django.db import models

from company.models import Company
from user.models import Profile, User

# Create your models here.


def get_default_dict():
    return {"country": "value", "city": "value"}


def get_default_list():
    return [{"address": ""}]


def get_default_list_addr():
    return [{"address": ""}]


def get_default_list_off():
    return [{"office_id_1": ""}]


def default_listed_dict():
    return [{"value": 101, "label": "India"}]


class Organization(models.Model):
    id = models.AutoField(primary_key=True, help_text="identity for organization model")
    organization_name = models.CharField(default="test", max_length=50)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    address = models.TextField(default="test")
    phone_no = models.CharField(
        max_length=20,
        default=None,
        null=True,
        blank=True,
        help_text="Enter your contact number",
    )
    email = models.CharField(max_length=50, null=True, blank=True, default="test")
    fax = models.CharField(max_length=50, default="test")

    country = models.JSONField(default=default_listed_dict)
    city = models.JSONField(default=get_default_dict)
    office = models.JSONField(default=get_default_dict)

    address_1 = models.JSONField(default=get_default_list_addr)
    office_id_1 = models.JSONField(default=get_default_list_off)

    primary_contact_1 = models.CharField(
        max_length=50,
        default=None,
        null=True,
        blank=True,
        help_text="Enter primary contact name",
    )
    secondary_contact_2 = models.CharField(
        max_length=50,
        default=None,
        null=True,
        blank=True,
        help_text="Enter secondary contact name",
    )
    total_employee = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date and time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")
