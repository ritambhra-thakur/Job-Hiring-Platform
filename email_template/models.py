from django.db import models

from company.models import Company

# Create your models here.


class EmailTemplate(models.Model):
    """
    class EmailTemplate is created to add the email templates with template fields
    """

    template_name = models.CharField(max_length=30, unique=True, help_text="Enter the template name", null=True, blank=True)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=True, related_name="email_template_company", help_text="Choose your company name"
    )
    template_type = models.CharField(max_length=30, help_text="choose template type", null=True, blank=True)
    description = models.TextField(help_text="add description", null=True, blank=True)
    subject = models.TextField(help_text="Subject", null=True, blank=True)

    is_active = models.BooleanField(default=True, help_text="user is active")
    is_deleted = models.BooleanField(default=False, help_text="to delete the user")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.template_name


class TemplateType(models.Model):
    """
    class EmailTemplate is created to add the email templates with template fields
    """

    template_type_name = models.CharField(max_length=30, unique=True, help_text="Enter the template type name", null=True, blank=True)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=True, related_name="email_template_type_company", help_text="Choose your company name"
    )
    is_active = models.BooleanField(default=True, help_text="user is active")
    is_deleted = models.BooleanField(default=False, help_text="to delete the user")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.template_type_name
