from django.contrib.auth.models import Permission
from django.db import models
from django.utils.text import slugify
from django_extensions.db.fields import AutoSlugField

from company.models import Company

# from simple_history.models import HistoricalRecords


# Create your models here.
class Role(models.Model):
    """
    Role model class is created to add role,
    active and created history and save function
    """

    name = models.CharField(max_length=50, help_text="Enter your role here")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="company",
        help_text="Choose your company name",
    )
    slug = AutoSlugField(populate_from=["name", "company"])
    permission = models.ManyToManyField(Permission, blank=True, help_text="Choose your permission field from above and ")
    can_delete = models.BooleanField(default=True, help_text="Select your preferences")
    is_active = models.BooleanField(default=True, help_text="Select your preferences")
    is_deleted = models.BooleanField(default=False, help_text="Select your preferences")

    # history = HistoricalRecords(table_name="roles_history")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date and time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.name

    # update the slug field when UpdateRole API is hit.
    def save(self, *args, **kwargs):
        value = self.name[0:250] + "-" + str(self.company)
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)


class Access(models.Model):
    """
    user action to relevent to infertalent product
    """

    action_name = models.CharField(max_length=250)

    is_active = models.BooleanField(default=True, help_text="Select your preferences")
    is_deleted = models.BooleanField(default=False, help_text="Select your preferences")

    # history = HistoricalRecords(table_name="access_history")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date and time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.action_name


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="permission_role",
        help_text="user role on infertalent product",
    )
    access = models.ForeignKey(
        Access,
        on_delete=models.CASCADE,
        related_name="permission_access",
        help_text="user action relevent to infertalent product",
    )
    read = models.BooleanField(default=False, help_text="role has permission to read specific action")
    create = models.BooleanField(default=False, help_text="role has permission to write specific action")
    update = models.BooleanField(
        default=False,
        help_text="role has permission to update specific action",
    )
    delete = models.BooleanField(
        default=False,
        help_text="role has permission to delete specific action",
    )
    # history = HistoricalRecords(table_name="role_permission_history")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date and time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")


class RoleList(models.Model):
    role_name = models.CharField(max_length=250)
    # history = HistoricalRecords(table_name="role_list_history")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created date and time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")
